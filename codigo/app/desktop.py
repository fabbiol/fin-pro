"""Aplicativo de desktop: janela própria (Microsoft Edge WebView2) + ícone na bandeja do Windows.

* o servidor roda numa thread deste mesmo processo;
* fechar a janela (X) apenas a esconde — o ícone perto do relógio reabre, e os lembretes de vencimento
  continuam funcionando (configurável em Configurações → Aplicativo);
* ``--bandeja`` inicia só com o ícone (usado ao ligar o computador, se preferir).
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import logging
import os
import shutil
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from . import config, janela, preferencias

log = logging.getLogger("leitor_boletos.desktop")

TITULO = "Fin Pro"
ID_APP = "LeitorDeBoletos.Aplicativo"
ICONE_ICO = config.WEB_DIR / "icons" / "app.ico"
ICONE_PNG = config.WEB_DIR / "icons" / "icone-192.png"


def disponivel() -> bool:
    try:
        import webview  # noqa: F401
    except Exception:
        return False
    return True


def _definir_id_do_app() -> None:
    """Faz a barra de tarefas mostrar o ícone do Fin Pro (e não o do Python)."""
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APP)
        except Exception:
            pass


def _impressao_da_interface() -> str:
    """Identifica a versão das telas (nome, tamanho e data de cada arquivo em web/)."""
    impressao = hashlib.sha256()
    for arquivo in sorted(config.WEB_DIR.rglob("*")):
        if arquivo.is_file():
            estado = arquivo.stat()
            impressao.update(f"{arquivo.relative_to(config.WEB_DIR).as_posix()}|{estado.st_size}|{estado.st_mtime_ns}\n".encode())
    return impressao.hexdigest()


def limpar_cache_se_atualizado(pasta_webview: Path) -> bool:
    """O WebView2 guarda HTML/JS/CSS em cache e pode continuar mostrando telas antigas depois de uma atualização.

    Quando os arquivos de web/ mudam, apaga só o cache de arquivos (tema e preferências do navegador são mantidos).
    """
    pasta_webview = Path(pasta_webview)
    marca = pasta_webview / "versao_interface.txt"
    atual = _impressao_da_interface()
    try:
        if marca.read_text(encoding="utf-8").strip() == atual:
            return False
    except OSError:
        pass
    for relativo in ("EBWebView/Default/Cache", "EBWebView/Default/Code Cache", "EBWebView/Default/Service Worker"):
        shutil.rmtree(pasta_webview / relativo, ignore_errors=True)
    pasta_webview.mkdir(parents=True, exist_ok=True)
    marca.write_text(atual, encoding="utf-8")
    return True


class Aplicativo:
    def __init__(self, iniciar_na_bandeja: bool = False):
        self.iniciar_na_bandeja = iniciar_na_bandeja
        self.saindo = False
        self.servidor: uvicorn.Server | None = None
        self.thread_servidor: threading.Thread | None = None
        self.janela = None
        self.icone = None
        self.url = f"http://127.0.0.1:{config.PORT}/"

    # ------------------------------------------------------------------ servidor

    def iniciar_servidor(self) -> None:
        from .main import app

        self.servidor = uvicorn.Server(uvicorn.Config(app, host=config.HOST, port=config.PORT, log_level="info"))
        self.thread_servidor = threading.Thread(target=self.servidor.run, name="servidor", daemon=True)
        self.thread_servidor.start()
        limite = time.monotonic() + 90
        while not self.servidor.started:
            if not self.thread_servidor.is_alive():
                raise RuntimeError(f"O servidor não iniciou (a porta {config.PORT} pode estar em uso).")
            if time.monotonic() > limite:
                raise RuntimeError("Tempo esgotado ao iniciar o servidor.")
            time.sleep(0.05)

    def parar_servidor(self) -> None:
        if self.servidor:
            self.servidor.should_exit = True
        if self.thread_servidor:
            self.thread_servidor.join(timeout=15)

    # ------------------------------------------------------------------ bandeja

    def criar_icone(self) -> bool:
        try:
            import pystray
            from PIL import Image
        except Exception:
            log.warning("pystray indisponível: sem ícone na bandeja")
            return False

        def abrir(rota):
            return lambda _icone, _item: threading.Thread(target=self.mostrar, args=(rota,), daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem("Abrir o Fin Pro", abrir(None), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ler boletos", abrir("ler")),
            pystray.MenuItem("Boletos lançados", abrir("boletos")),
            pystray.MenuItem("Pagamentos Pix", abrir("pix")),
            pystray.MenuItem("Análise de gastos", abrir("gastos")),
            pystray.MenuItem("Notificações", abrir("notificacoes")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda _icone, _item: threading.Thread(target=self.sair, daemon=True).start()),
        )
        pronto = threading.Event()

        def rodar():
            # No Windows o ícone precisa ser criado na mesma thread que processa as mensagens dele
            try:
                self.icone = pystray.Icon("leitor_boletos", Image.open(ICONE_PNG), TITULO, menu)
            finally:
                pronto.set()
            self.icone.run()

        threading.Thread(target=rodar, name="bandeja", daemon=True).start()
        pronto.wait(10)
        return self.icone is not None

    def avisar(self, mensagem: str) -> None:
        try:
            self.icone.notify(mensagem, TITULO)
        except Exception:
            log.debug("Aviso da bandeja indisponível", exc_info=True)

    # ------------------------------------------------------------------ janela

    def criar_janela(self) -> None:
        import webview

        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
        self.janela = webview.create_window(
            TITULO, self.url, width=1380, height=880, min_size=(980, 640),
            hidden=self.iniciar_na_bandeja and self.icone is not None,
            text_select=True, background_color="#0b1b1f",
        )
        self.janela.events.closing += self._ao_fechar

    def _ao_fechar(self):
        if self.saindo:
            return True
        if self.icone is None or not preferencias.ler().get("fechar_para_bandeja", True):
            self.saindo = True
            return True
        # Esconde numa thread: o fechamento está sendo tratado na thread da interface
        threading.Thread(target=self._esconder, daemon=True).start()
        return False

    def _esconder(self) -> None:
        self.janela.hide()
        prefs = preferencias.ler()
        if not prefs["aviso_bandeja_mostrado"]:
            preferencias.atualizar({"aviso_bandeja_mostrado": True})
            self.avisar("Continua aberto aqui na bandeja, cuidando dos lembretes de vencimento. "
                        "Para encerrar, clique com o botão direito no ícone e escolha Sair.")

    def _hwnd(self) -> int:
        if os.name != "nt":
            return 0
        user32 = ctypes.windll.user32
        hwnd = 0
        while True:
            hwnd = user32.FindWindowExW(None, hwnd, None, TITULO)
            if not hwnd:
                return 0
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                return hwnd

    def mostrar(self, rota: str | None = None) -> None:
        j = self.janela
        if j is None:
            return
        if rota:
            try:
                j.evaluate_js(f"location.hash = {json.dumps('#/' + rota)}")
            except Exception:
                log.debug("Não foi possível navegar para %s", rota, exc_info=True)
        j.show()
        hwnd = self._hwnd()
        if not hwnd:
            return
        # Chamadas diretas da API do Windows (via ctypes, que libera o GIL). Não usar ``janela.on_top``:
        # o pywebview altera TopMost fora da thread da interface e trava o processo inteiro.
        user32 = ctypes.windll.user32
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        topo, normal = -1, -2  # HWND_TOPMOST, HWND_NOTOPMOST
        opcoes = 0x0001 | 0x0002 | 0x0040 | 0x4000  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
        # "Sobe" a janela por cima de todas e devolve ao normal: aparece na frente mesmo quando o Windows
        # bloqueia a troca de foco para programas em segundo plano
        user32.SetWindowPos(hwnd, topo, 0, 0, 0, 0, opcoes)
        user32.SetWindowPos(hwnd, normal, 0, 0, 0, 0, opcoes)
        user32.SetForegroundWindow(hwnd)

    def sair(self) -> None:
        self.saindo = True
        if self.janela is not None:
            self.janela.destroy()


def executar(iniciar_na_bandeja: bool = False) -> None:
    _definir_id_do_app()
    aplicativo = Aplicativo(iniciar_na_bandeja)
    aplicativo.iniciar_servidor()
    janela.registrar(aplicativo.mostrar, aplicativo.sair)
    try:
        import webview

        pasta_webview = config.DADOS_DIR / "webview"
        try:
            if limpar_cache_se_atualizado(pasta_webview):
                log.info("Telas atualizadas: cache da janela limpo")
        except Exception:
            log.exception("Não foi possível limpar o cache da janela")
        aplicativo.criar_icone()
        aplicativo.criar_janela()
        webview.start(private_mode=False, storage_path=str(pasta_webview), icon=str(ICONE_ICO))
    except Exception:
        log.exception("Não foi possível abrir a janela do aplicativo; usando o navegador")
        janela.desregistrar()
        if aplicativo.icone is not None:
            aplicativo.icone.stop()
            aplicativo.icone = None
        webbrowser.open(aplicativo.url)
        try:
            while aplicativo.thread_servidor.is_alive():
                aplicativo.thread_servidor.join(1)
        except KeyboardInterrupt:
            pass
    finally:
        janela.desregistrar()
        if aplicativo.icone is not None:
            aplicativo.icone.stop()
        aplicativo.parar_servidor()

"""Inicia o sistema.

    python -m app              abre o aplicativo (janela própria + ícone na bandeja)
    python -m app --bandeja    inicia só com o ícone na bandeja (ao ligar o computador)
    python -m app --navegador  modo antigo: servidor + página no navegador
"""

import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser


def _preparar_saida_sem_console() -> None:
    """Com pythonw (atalho, inicialização com o Windows) não há console: registra a saída em arquivo."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    from . import config, registro_log

    arquivo = registro_log.ArquivoRotativo(config.DADOS_DIR / "leitor.log")  # até 2 MB por arquivo, 5 antigos
    registro_log.saida_atual = arquivo
    sys.stdout = sys.stdout or arquivo
    sys.stderr = sys.stderr or arquivo


_preparar_saida_sem_console()

import uvicorn  # noqa: E402

from . import __version__, config  # noqa: E402


def _ja_em_execucao(host: str, porta: int) -> bool:
    alvo = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conexao:
        conexao.settimeout(0.5)
        return conexao.connect_ex((alvo, porta)) == 0


def _mostrar_instancia_existente(abrir_navegador: bool) -> None:
    """Já está aberto: traz a janela do aplicativo para a frente (ou abre o navegador, no modo antigo)."""
    try:
        requisicao = urllib.request.Request(
            f"http://127.0.0.1:{config.PORT}/api/app/mostrar", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            if json.loads(resposta.read().decode("utf-8")).get("modo_app"):
                return
    except Exception:
        pass
    if abrir_navegador:
        webbrowser.open(config.URL_APP)


def main() -> None:
    argumentos = set(sys.argv[1:])
    na_bandeja = "--bandeja" in argumentos
    modo_navegador = "--navegador" in argumentos or os.getenv("LEITOR_MODO", "").lower() == "navegador"
    abrir_navegador = os.getenv("LEITOR_ABRIR_NAVEGADOR", "1") != "0"

    if _ja_em_execucao(config.HOST, config.PORT):
        print(f"\n  O Fin Pro já está em execução em {config.URL_APP}.")
        if not na_bandeja:
            _mostrar_instancia_existente(abrir_navegador)
        return

    if not modo_navegador and sys.platform == "darwin":
        # pywebview + Python 3.14 no macOS 26 aborta o processo (SIGTRAP no NSApplication).
        modo_navegador = True

    if not modo_navegador:
        from . import desktop

        if desktop.disponivel():
            print(f"\n  Fin Pro v{__version__} (aplicativo)")
            desktop.executar(iniciar_na_bandeja=na_bandeja)
            return
        print("  Componente de janela (pywebview) indisponível: abrindo no navegador.")

    url = config.URL_APP
    print(f"\n  Fin Pro v{__version__}")
    print(f"  Acesse: {url}")
    print(f"  Planilha: {config.PLANILHA_PATH}")
    if config.HOST == "0.0.0.0":
        print("  Rede local liberada: use o IP deste computador no celular para fotografar boletos.")
        if not config.SENHA_ACESSO:
            print("  ATENÇÃO: acesso pela rede sem senha. Defina LEITOR_SENHA_ACESSO no arquivo .env.")
    print("  Para encerrar, feche esta janela ou pressione Ctrl+C.\n")
    if abrir_navegador and not na_bandeja:
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, log_level="info")


if __name__ == "__main__":
    main()

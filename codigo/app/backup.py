"""Backup TOTAL para fora do computador (pasta do OneDrive, Google Drive, Dropbox, pen drive ou HD externo).

Uma vez por dia, depois do horário escolhido, o sistema copia para ``<pasta escolhida>/Leitor de Boletos - Backup``
**tudo o que é preciso para reerguer o Fin Pro em outro computador**:

* ``planilha/``       — uma cópia por dia de cada banco de dados (``boletos``, ``empresas``, ``diesel``) e de cada planilha;
* ``arquivos/``       — PDFs, fotos, comprovantes, cupons, canhotos, cheques e notas (só copia o que é novo ou mudou);
* ``configuracoes/``  — **todos** os arquivos de configuração da pasta de dados (lembretes, usuários, bots, preços…)
  e o ``.env``;
* ``codigo/``         — o **código-fonte** inteiro do sistema (espelho da pasta do sistema, sem o ambiente Python);
* ``versoes/``        — o **histórico completo de versões** (``finpro.bundle``, do git) e ``VERSAO.txt``;
* ``pacotes/``        — de tempos em tempos, **tudo isso num único arquivo .zip** (para pen drive ou para guardar);
* ``manifesto.json``  — a lista de tudo o que há no backup, com tamanho e impressão digital (SHA-256) de cada arquivo;
* ``LEIA-ME.txt``, ``RESTAURAR.bat`` e ``restaurar_backup.py`` — como (e com o quê) restaurar.

Depois de cada backup o sistema **confere** o que copiou (os bancos abrem? está tudo lá?). A conferência completa,
que relê cada arquivo e compara a impressão digital, é feita pelo botão "Verificar backup".

A pasta do OneDrive/Google Drive é sincronizada com a nuvem pelo próprio programa deles: se o computador
quebrar, os dados continuam na conta. Se o backup falhar, atrasar ou não passar na conferência, o sistema avisa na tela.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import string
import threading
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger(__name__)

# O nome da pasta de backup continua o antigo de propósito: as cópias já feitas no Drive ficam no mesmo lugar.
NOME_PASTA = "Leitor de Boletos - Backup"
# Configurações que sempre existiram (mantido por compatibilidade); hoje TODO *.json da pasta de dados é copiado.
CONFIGURACOES = ("notificacoes.json", "usuarios.json", "admin.json", "rede.json", "importacao_modelos.json", "backup.json",
                 "entrada.json", "gravacao_pendente.json")
INTERVALO_VERIFICACAO = 300
ESPERA_APOS_FALHA = timedelta(minutes=30)
ESPERA_APOS_FALHA_PACOTE = timedelta(hours=6)
DIAS_PARA_ALERTA = 2
RE_COPIA = re.compile(r"^(?:boletos|empresas|diesel)-(\d{4}-\d{2}-\d{2})\.(xlsx|db)$")
RE_PACOTE = re.compile(r"^Fin Pro - backup completo (\d{4}-\d{2}-\d{2})_(\d{4})\.zip$")
# O que NÃO é código: ambiente Python (reinstalável), caches, o repositório (vai no bundle) e as pastas de dados.
PASTAS_FORA_DO_CODIGO = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "node_modules", NOME_PASTA}
SUFIXOS_FORA_DO_CODIGO = {".pyc", ".pyo", ".tmp", ".parcial"}
PACOTES = {"nunca": None, "semanal": 7, "mensal": 30}  # de quantos em quantos dias sai o pacote .zip
SECOES = ("planilha", "arquivos", "configuracoes", "codigo", "versoes")
NOME_BUNDLE = "finpro.bundle"
BLOCO = 1024 * 1024

LEIA_ME = """BACKUP COMPLETO DO FIN PRO
==========================

Esta pasta é criada e atualizada automaticamente pelo Fin Pro (uma vez por dia). Ela tem TUDO o que é preciso para
colocar o sistema para funcionar de novo em outro computador:

  planilha\\         uma cópia por dia de cada banco de dados (boletos, empresas, diesel) e de cada planilha Excel
  arquivos\\         PDFs e fotos dos boletos, comprovantes, cupons do caixa, canhotos do diesel, cheques e notas
  configuracoes\\    lembretes, usuários, bots do Telegram, preços, e o arquivo .env
  codigo\\           o código-fonte completo do sistema (o programa em si)
  versoes\\          o histórico de todas as versões do sistema (finpro.bundle) e a versão deste backup (VERSAO.txt)
  pacotes\\          tudo isto num único arquivo .zip, gerado de tempos em tempos
  manifesto.json    a lista de tudo o que há aqui, para conferir se nada se perdeu ou se corrompeu

ATENÇÃO: a pasta "configuracoes" guarda os tokens dos bots e as senhas de e-mail. Mantenha este backup num lugar
de confiança (a sua conta do OneDrive/Google Drive, ou um pen drive guardado).

COMO RESTAURAR EM OUTRO COMPUTADOR (jeito fácil)
1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/), marcando "Add python.exe to PATH".
2. Dê dois cliques em RESTAURAR.bat (nesta pasta) e escolha onde o sistema vai ficar.
   Ele copia o código, os bancos de dados mais recentes, os arquivos e as configurações para o lugar certo.
3. Na pasta escolhida, dê dois cliques em iniciar.bat. Na primeira vez ele instala o que falta (alguns minutos).

COMO RESTAURAR À MÃO (se preferir)
1. Copie a pasta "codigo" inteira para onde o sistema vai ficar (ex.: Documentos\\Fin Pro).
2. Dentro dela, crie a pasta "dados".
3. Em "planilha", pegue a cópia mais recente de cada banco e copie para "dados" com estes nomes:
      boletos-DATA.db  -> dados\\boletos.db       empresas-DATA.db -> dados\\empresas.db
      diesel-DATA.db   -> dados\\diesel.db
   (as planilhas Excel são refeitas sozinhas; as cópias .xlsx daqui abrem direto no Excel.)
4. Copie a pasta "arquivos" inteira para dentro de "dados".
5. Copie os arquivos .json de "configuracoes" para dentro de "dados", e o ".env" para a pasta do sistema.
6. Dê dois cliques em iniciar.bat.

HISTÓRICO DE VERSÕES
O arquivo versoes\\finpro.bundle tem todas as versões do código. Com o git instalado:
      git clone versoes\\finpro.bundle "Fin Pro - codigo"
recria o repositório com todas as versões (o RESTAURAR.bat já faz isso sozinho quando o git está instalado).

IMPORTANTE AO RESTAURAR
Só ligue os bots do Telegram no computador novo depois de desligar o antigo: dois sistemas com o mesmo bot
disputam as mensagens.
"""

RESTAURAR_BAT = """@echo off
chcp 65001 >nul
title Restaurar o Fin Pro
echo.
echo  RESTAURAR O FIN PRO A PARTIR DESTE BACKUP
echo  -----------------------------------------
echo  Copia o codigo, os bancos de dados, os arquivos e as configuracoes
echo  para uma pasta nova. Nada e apagado deste backup.
echo.
set "DESTINO=%USERPROFILE%\\Documents\\Fin Pro"
set /p "DESTINO=Onde o sistema vai ficar (ENTER = %DESTINO%): "
echo.
py -3 "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"
if errorlevel 9009 python "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"
echo.
pause
"""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(BLOCO), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _tamanho_legivel(tamanho: int) -> str:
    valor = float(tamanho)
    for unidade in ("bytes", "KB", "MB", "GB"):
        if valor < 1024 or unidade == "GB":
            return f"{valor:.0f} {unidade}" if unidade == "bytes" else f"{valor:.1f} {unidade}".replace(".", ",")
        valor /= 1024
    return f"{tamanho} bytes"


def sugerir_pastas(base_usuario: Path | None = None) -> list[dict]:
    """Pastas prováveis para o backup: nuvem (OneDrive, Google Drive, Dropbox) e unidades removíveis."""
    base_usuario = base_usuario or Path.home()
    candidatos: list[tuple[str, Path]] = []
    for variavel, nome in (("OneDriveCommercial", "OneDrive da empresa"), ("OneDriveConsumer", "OneDrive"), ("OneDrive", "OneDrive")):
        if os.environ.get(variavel):
            candidatos.append((nome, Path(os.environ[variavel])))
    for pasta in ("Google Drive", "My Drive", "Meu Drive", "Dropbox", "iCloudDrive"):
        candidatos.append(("Dropbox" if pasta == "Dropbox" else "iCloud" if pasta == "iCloudDrive" else "Google Drive",
                           base_usuario / pasta))
    if os.name == "nt":
        for letra in string.ascii_uppercase[3:]:
            raiz = Path(f"{letra}:\\")
            for sub in ("My Drive", "Meu Drive"):
                candidatos.append(("Google Drive", raiz / sub))
            try:
                import ctypes

                if ctypes.windll.kernel32.GetDriveTypeW(f"{letra}:\\") == 2 and raiz.exists():  # 2 = removível
                    candidatos.append((f"Pen drive / HD externo ({letra}:)", raiz))
            except Exception:
                pass
    vistos, saida = set(), []
    for nome, caminho in candidatos:
        try:
            if caminho.is_dir() and str(caminho).lower() not in vistos:
                vistos.add(str(caminho).lower())
                saida.append({"nome": nome, "pasta": str(caminho)})
        except OSError:
            continue
    return saida


class GerenciadorBackup:
    def __init__(self, caminho_config: Path, pasta_dados: Path, planilha: Path, pasta_arquivos: Path, copiar_banco=None,
                 extras: list[dict] | None = None, pasta_codigo: Path | None = None, informar_versao=None,
                 gerar_bundle=None, verificar_bundle=None):
        """``copiar_banco(destino)`` faz uma cópia consistente do banco de dados (SQLite).

        ``extras``: outros bancos/planilhas a copiar, como ``[{"nome": "empresas", "planilha": Path, "copiar_banco": fn}]``.
        ``pasta_codigo``: a pasta do sistema (código-fonte); sem ela, o backup leva só os dados.
        ``informar_versao()`` → texto do ``VERSAO.txt``; ``gerar_bundle(destino)`` grava o histórico de versões;
        ``verificar_bundle(arquivo)`` confere esse arquivo.
        """
        self.copiar_banco = copiar_banco
        self.extras = list(extras or [])
        self.caminho = Path(caminho_config)
        self.pasta_dados = Path(pasta_dados)
        self.planilha = Path(planilha)
        self.pasta_arquivos = Path(pasta_arquivos)
        self.pasta_codigo = Path(pasta_codigo) if pasta_codigo else None
        self.informar_versao = informar_versao
        self.gerar_bundle = gerar_bundle
        self.verificar_bundle = verificar_bundle
        self._lock = threading.RLock()
        self._executando = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._estado = self._ler()

    # ------------------------------------------------------------------ configuração

    def _ler(self) -> dict:
        estado = {"ativo": False, "pasta": "", "horario": "12:30", "manter_dias": 30, "configurado_em": None,
                  "ultimo": None, "ultimo_sucesso": None,
                  "codigo": True,  # levar também o código-fonte e o histórico de versões
                  "pacote": "semanal", "manter_pacotes": 4, "ultimo_pacote": None,  # tudo num .zip, de tempos em tempos
                  "falha_pacote": None, "verificacao": None}
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
            estado.update({k: v for k, v in salvo.items() if k in estado})
        except (OSError, json.JSONDecodeError):
            pass
        if estado["pacote"] not in PACOTES:
            estado["pacote"] = "semanal"
        return estado

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    def validar_pasta(self, pasta: str) -> Path:
        texto = (pasta or "").strip().strip('"')
        if not texto:
            raise ValueError("Escolha a pasta onde o backup será guardado.")
        destino = Path(texto).expanduser()
        if not destino.is_absolute():
            raise ValueError("Informe o caminho completo da pasta (ex.: C:\\Users\\voce\\OneDrive).")
        if not destino.is_dir():
            raise ValueError("Pasta não encontrada. Confira o caminho ou conecte o pen drive/HD externo.")
        dados = self.pasta_dados.resolve()
        resolvido = destino.resolve()
        if resolvido == dados or dados in resolvido.parents:
            raise ValueError("O backup precisa ficar fora da pasta de dados do sistema (senão se perde junto com ela).")
        teste = destino / f".teste-leitor-{os.getpid()}.tmp"
        try:
            teste.write_text("ok", encoding="utf-8")
            teste.unlink()
        except OSError as exc:
            raise ValueError("Sem permissão para gravar nesta pasta.") from exc
        return destino

    def configurar(self, *, ativo: bool | None = None, pasta: str | None = None, horario: str | None = None,
                   manter_dias: int | None = None, codigo: bool | None = None, pacote: str | None = None,
                   manter_pacotes: int | None = None) -> dict:
        with self._lock:
            novo = dict(self._estado)
            if pasta is not None:
                novo["pasta"] = str(self.validar_pasta(pasta))
            if horario is not None:
                try:
                    novo["horario"] = datetime.strptime(horario.strip(), "%H:%M").strftime("%H:%M")
                except ValueError as exc:
                    raise ValueError("Horário inválido. Use o formato HH:MM.") from exc
            if manter_dias is not None:
                if not 3 <= int(manter_dias) <= 365:
                    raise ValueError("Guarde de 3 a 365 dias de cópias da planilha.")
                novo["manter_dias"] = int(manter_dias)
            if codigo is not None:
                novo["codigo"] = bool(codigo)
            if pacote is not None:
                if pacote not in PACOTES:
                    raise ValueError("Escolha quando gerar o pacote completo: nunca, semanal ou mensal.")
                novo["pacote"] = pacote
            if manter_pacotes is not None:
                if not 1 <= int(manter_pacotes) <= 24:
                    raise ValueError("Guarde de 1 a 24 pacotes completos.")
                novo["manter_pacotes"] = int(manter_pacotes)
            if ativo is not None:
                if ativo and not novo["pasta"]:
                    raise ValueError("Escolha a pasta do backup antes de ligar.")
                if ativo and not novo["ativo"]:
                    novo["configurado_em"] = _agora()
                novo["ativo"] = bool(ativo)
            self._estado = novo
            self._gravar()
        return self.status()

    # ------------------------------------------------------------------ situação

    def status(self, agora: datetime | None = None) -> dict:
        agora = agora or datetime.now()
        with self._lock:
            estado = dict(self._estado)
        sucesso = estado.get("ultimo_sucesso")
        referencia = sucesso or estado.get("configurado_em")
        dias = None
        if sucesso:
            dias = (agora.date() - datetime.fromisoformat(sucesso).date()).days
        atrasado = False
        if estado["ativo"] and referencia:
            atrasado = agora - datetime.fromisoformat(referencia) > timedelta(days=DIAS_PARA_ALERTA)
        if estado["ativo"] and estado["pasta"] and not Path(estado["pasta"]).is_dir():
            atrasado = True
        situacao = ("desligado" if not estado["ativo"] else "atrasado" if atrasado
                    else "erro" if (estado.get("ultimo") or {}).get("ok") is False else "ok" if sucesso else "aguardando")
        verificacao = estado.get("verificacao") or {}
        return {**estado, "situacao": situacao, "dias_sem_backup": dias, "destino": self._destino(estado),
                "executando": self._executando.locked(), "com_codigo": bool(self.pasta_codigo and estado["codigo"]),
                "verificado": verificacao.get("ok"), "problemas": [i for i in verificacao.get("itens") or [] if not i["ok"]]}

    @staticmethod
    def _destino(estado: dict) -> str | None:
        return str(Path(estado["pasta"]) / NOME_PASTA) if estado.get("pasta") else None

    def _raiz(self) -> Path:
        with self._lock:
            pasta = self._estado["pasta"]
        if not pasta:
            raise ValueError("Escolha a pasta do backup.")
        return self.validar_pasta(pasta) / NOME_PASTA

    # ------------------------------------------------------------------ execução

    def executar(self) -> dict:
        """Faz o backup agora. Devolve o resultado (também guardado em ``ultimo``)."""
        if not self._executando.acquire(blocking=False):
            return {"ok": False, "erro": "Um backup já está em andamento."}
        inicio = time.time()
        try:
            with self._lock:
                estado = dict(self._estado)
            try:
                raiz = self._raiz()
                resultado = self._copiar(raiz, int(estado["manter_dias"]))
                resultado.update(ok=True, quando=_agora(), segundos=round(time.time() - inicio, 1))
                log.info("Backup concluído em %s (%d arquivo(s) novo(s), %d do código)", raiz,
                         resultado["arquivos_copiados"], resultado["codigo_copiados"])
            except Exception as exc:
                log.warning("Backup falhou: %s", exc)
                mensagem = str(exc) if isinstance(exc, ValueError) else f"Falha ao copiar: {exc}"
                resultado = {"ok": False, "quando": _agora(), "erro": mensagem}
            with self._lock:
                self._estado["ultimo"] = resultado
                if resultado["ok"]:
                    self._estado["ultimo_sucesso"] = resultado["quando"]
                self._gravar()
            if resultado["ok"]:
                try:  # confere o que acabou de copiar (rápido); um problema aqui aparece na tela, não derruba o backup
                    self._verificar(completa=False)
                except Exception:
                    log.exception("Falha ao conferir o backup")
            return resultado
        finally:
            self._executando.release()

    def _copiar(self, raiz: Path, manter_dias: int) -> dict:
        with self._lock:
            levar_codigo = bool(self._estado.get("codigo", True))
        (raiz / "planilha").mkdir(parents=True, exist_ok=True)
        planilhas = 0
        bancos = [{"nome": "boletos", "planilha": self.planilha, "copiar_banco": self.copiar_banco}, *self.extras]
        for base in bancos:
            arquivo = Path(base.get("planilha") or "")
            if arquivo and arquivo.exists():
                destino = raiz / "planilha" / f"{base['nome']}-{date.today():%Y-%m-%d}.xlsx"
                temporario = destino.with_suffix(".tmp")
                shutil.copy2(arquivo, temporario)  # funciona mesmo com a planilha aberta no Excel
                os.replace(temporario, destino)
                planilhas += 1
            if base.get("copiar_banco"):
                base["copiar_banco"](raiz / "planilha" / f"{base['nome']}-{date.today():%Y-%m-%d}.db")
        if planilhas or self.copiar_banco:
            limite = date.today() - timedelta(days=manter_dias)
            for antiga in (raiz / "planilha").iterdir():
                encontrado = RE_COPIA.match(antiga.name)
                if encontrado and date.fromisoformat(encontrado.group(1)) < limite:
                    antiga.unlink(missing_ok=True)

        copiados = 0
        if self.pasta_arquivos.is_dir():
            (raiz / "arquivos").mkdir(exist_ok=True)
            for origem in self.pasta_arquivos.iterdir():
                if origem.is_file() and self._copiar_se_mudou(origem, raiz / "arquivos" / origem.name):
                    copiados += 1

        (raiz / "configuracoes").mkdir(exist_ok=True)
        configuracoes = 0
        for origem in self._arquivos_de_configuracao():
            shutil.copy2(origem, raiz / "configuracoes" / origem.name)
            configuracoes += 1

        codigo = {"copiados": 0, "total": 0, "removidos": 0}
        historico = False
        if self.pasta_codigo and levar_codigo:
            codigo = self._espelhar_codigo(raiz / "codigo", raiz)
            historico = self._guardar_versoes(raiz / "versoes")
            self._escrever_restaurador(raiz)
        (raiz / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")
        manifesto = self._escrever_manifesto(raiz)
        total = sum(1 for _ in (raiz / "arquivos").iterdir()) if (raiz / "arquivos").is_dir() else 0
        return {"destino": str(raiz), "planilhas": planilhas, "arquivos_copiados": copiados, "arquivos_total": total,
                "configuracoes": configuracoes, "codigo_copiados": codigo["copiados"], "codigo_total": codigo["total"],
                "codigo_removidos": codigo["removidos"], "historico_de_versoes": historico,
                "itens": manifesto["totais"]["arquivos"], "tamanho": manifesto["totais"]["tamanho"],
                "tamanho_legivel": _tamanho_legivel(manifesto["totais"]["tamanho"])}

    @staticmethod
    def _copiar_se_mudou(origem: Path, destino: Path) -> bool:
        info = origem.stat()
        if destino.exists():
            atual = destino.stat()
            if atual.st_size == info.st_size and int(atual.st_mtime) >= int(info.st_mtime):
                return False
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)
        return True

    def _arquivos_de_configuracao(self) -> list[Path]:
        """Todo ``*.json`` da pasta de dados (cada módulo novo entra sozinho) e o ``.env`` da pasta do sistema."""
        lista = sorted(p for p in self.pasta_dados.glob("*.json") if p.is_file()) if self.pasta_dados.is_dir() else []
        if self.pasta_codigo and (self.pasta_codigo / ".env").is_file():
            lista.append(self.pasta_codigo / ".env")
        return lista

    # ------------------------------------------------------------------ código-fonte e versões

    def _arquivos_do_codigo(self, raiz_backup: Path | None = None) -> list[Path]:
        """Arquivos que formam o sistema: tudo da pasta do sistema, menos ambiente Python, caches, dados e o próprio backup."""
        if not self.pasta_codigo or not self.pasta_codigo.is_dir():
            return []
        fora = {self.pasta_dados.resolve()}
        if raiz_backup is not None:
            fora |= {raiz_backup.resolve(), raiz_backup.parent.resolve()} - {self.pasta_codigo.resolve()}
        lista: list[Path] = []
        for pasta, subpastas, arquivos in os.walk(self.pasta_codigo):
            atual = Path(pasta)
            subpastas[:] = sorted(s for s in subpastas if s not in PASTAS_FORA_DO_CODIGO and not s.lower().startswith("dados")
                                  and (atual / s).resolve() not in fora)
            for nome in sorted(arquivos):
                if Path(nome).suffix.lower() in SUFIXOS_FORA_DO_CODIGO or nome == ".env" or nome.startswith("~$"):
                    continue  # o .env vai junto com as configurações
                lista.append(atual / nome)
        return lista

    def _espelhar_codigo(self, destino: Path, raiz_backup: Path) -> dict:
        """Deixa ``codigo/`` igual à pasta do sistema: copia o que mudou e remove o que não existe mais."""
        destino.mkdir(parents=True, exist_ok=True)
        esperados: set[Path] = set()
        copiados = 0
        for origem in self._arquivos_do_codigo(raiz_backup):
            relativo = origem.relative_to(self.pasta_codigo)
            esperados.add(relativo)
            if self._copiar_se_mudou(origem, destino / relativo):
                copiados += 1
        removidos = 0
        for pasta, _subpastas, arquivos in os.walk(destino, topdown=False):
            atual = Path(pasta)
            for nome in arquivos:
                if (atual / nome).relative_to(destino) not in esperados:
                    (atual / nome).unlink(missing_ok=True)
                    removidos += 1
            if atual != destino and not any(atual.iterdir()):
                atual.rmdir()
        return {"copiados": copiados, "total": len(esperados), "removidos": removidos}

    def _guardar_versoes(self, destino: Path) -> bool:
        """``versoes/finpro.bundle`` (todo o histórico do git) e ``VERSAO.txt`` (qual versão este backup tem)."""
        destino.mkdir(parents=True, exist_ok=True)
        if self.informar_versao:
            try:
                (destino / "VERSAO.txt").write_text(self.informar_versao(), encoding="utf-8")
            except Exception:
                log.exception("Não foi possível registrar a versão no backup")
        if not self.gerar_bundle:
            return False
        try:
            return bool(self.gerar_bundle(destino / NOME_BUNDLE))
        except Exception:
            log.exception("Não foi possível guardar o histórico de versões no backup")
            return False

    def _escrever_restaurador(self, raiz: Path) -> None:
        (raiz / "RESTAURAR.bat").write_text(RESTAURAR_BAT, encoding="utf-8", newline="\r\n")
        origem = self.pasta_codigo / "ferramentas" / "restaurar_backup.py" if self.pasta_codigo else None
        if origem and origem.is_file():
            shutil.copy2(origem, raiz / "restaurar_backup.py")

    # ------------------------------------------------------------------ manifesto

    @staticmethod
    def _arquivos_do_backup(raiz: Path):
        for secao in SECOES:
            pasta = raiz / secao
            if not pasta.is_dir():
                continue
            for caminho in sorted(pasta.rglob("*")):
                if caminho.is_file() and caminho.suffix not in (".tmp", ".parcial"):
                    yield caminho

    def _escrever_manifesto(self, raiz: Path) -> dict:
        """Lista tudo o que há no backup com tamanho e SHA-256 (reaproveita a impressão digital do que não mudou)."""
        anterior: dict = {}
        try:
            anterior = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8")).get("arquivos") or {}
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        arquivos: dict[str, dict] = {}
        por_secao = {secao: {"arquivos": 0, "tamanho": 0} for secao in SECOES}
        for caminho in self._arquivos_do_backup(raiz):
            relativo = caminho.relative_to(raiz).as_posix()
            info = caminho.stat()
            antigo = anterior.get(relativo) or {}
            if antigo.get("tamanho") == info.st_size and antigo.get("mtime") == info.st_mtime_ns and antigo.get("sha256"):
                impressao = antigo["sha256"]
            else:
                impressao = _sha256(caminho)
            arquivos[relativo] = {"tamanho": info.st_size, "mtime": info.st_mtime_ns, "sha256": impressao}
            secao = por_secao[relativo.split("/", 1)[0]]
            secao["arquivos"] += 1
            secao["tamanho"] += info.st_size
        manifesto = {
            "gerado_em": _agora(),
            "versao": (self.informar_versao() or "").splitlines()[0] if self.informar_versao else "",
            "totais": {"arquivos": len(arquivos), "tamanho": sum(a["tamanho"] for a in arquivos.values()), "secoes": por_secao},
            "arquivos": arquivos,
        }
        temporario = raiz / "manifesto.tmp"
        temporario.write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporario, raiz / "manifesto.json")
        return manifesto

    # ------------------------------------------------------------------ pacote completo (.zip)

    def pacotes(self, raiz: Path | None = None) -> list[dict]:
        """Os pacotes .zip guardados, do mais novo para o mais antigo."""
        try:
            pasta = (raiz or self._raiz()) / "pacotes"
        except ValueError:
            return []
        if not pasta.is_dir():
            return []
        lista = [{"arquivo": p.name, "caminho": str(p), "tamanho": p.stat().st_size,
                  "tamanho_legivel": _tamanho_legivel(p.stat().st_size),
                  "quando": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")}
                 for p in pasta.iterdir() if p.is_file() and RE_PACOTE.match(p.name)]
        return sorted(lista, key=lambda p: p["arquivo"], reverse=True)

    def gerar_pacote(self, agora: datetime | None = None) -> dict:
        """Atualiza o backup e guarda **tudo num único arquivo .zip** (código, versões, bancos, arquivos e configurações).

        Leva a cópia mais recente de cada banco e planilha (não os 30 dias). O .zip é conferido depois de gravado.
        """
        agora = agora or datetime.now()
        backup = self.executar()
        if not backup["ok"]:
            return backup
        if not self._executando.acquire(blocking=False):
            return {"ok": False, "erro": "Um backup já está em andamento."}
        try:
            raiz = self._raiz()
            pasta = raiz / "pacotes"
            pasta.mkdir(exist_ok=True)
            destino = pasta / f"Fin Pro - backup completo {agora:%Y-%m-%d_%H%M}.zip"
            temporario = destino.with_suffix(".parcial")
            recentes = self._copias_mais_recentes(raiz)
            quantidade = 0
            with zipfile.ZipFile(temporario, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as pacote:
                for caminho in self._arquivos_do_backup(raiz):
                    relativo = caminho.relative_to(raiz)
                    if relativo.parts[0] == "planilha" and RE_COPIA.match(caminho.name) and caminho not in recentes:
                        continue  # só a cópia mais recente de cada banco/planilha
                    pacote.write(caminho, relativo.as_posix())
                    quantidade += 1
                for nome in ("manifesto.json", "LEIA-ME.txt", "RESTAURAR.bat", "restaurar_backup.py"):
                    if (raiz / nome).is_file():
                        pacote.write(raiz / nome, nome)
            with zipfile.ZipFile(temporario) as pacote:
                corrompido = pacote.testzip()
            if corrompido:
                temporario.unlink(missing_ok=True)
                raise ValueError(f"O pacote ficou corrompido ao gravar ({corrompido}). Tente de novo.")
            os.replace(temporario, destino)
            with self._lock:
                manter = int(self._estado.get("manter_pacotes") or 4)
            for antigo in self.pacotes(raiz)[manter:]:
                Path(antigo["caminho"]).unlink(missing_ok=True)
            resultado = {"ok": True, "quando": _agora(), "arquivo": destino.name, "caminho": str(destino),
                         "tamanho": destino.stat().st_size, "tamanho_legivel": _tamanho_legivel(destino.stat().st_size),
                         "arquivos": quantidade}
            log.info("Pacote completo gerado: %s (%s)", destino.name, resultado["tamanho_legivel"])
        except Exception as exc:
            log.warning("Não foi possível gerar o pacote completo: %s", exc)
            resultado = {"ok": False, "quando": _agora(),
                         "erro": str(exc) if isinstance(exc, ValueError) else f"Falha ao gerar o pacote: {exc}"}
        finally:
            self._executando.release()
        with self._lock:
            if resultado["ok"]:
                self._estado["ultimo_pacote"] = resultado
            self._estado["falha_pacote"] = None if resultado["ok"] else resultado["quando"]
            self._gravar()
        return resultado

    @staticmethod
    def _copias_mais_recentes(raiz: Path) -> set[Path]:
        """A cópia de data mais nova de cada banco e de cada planilha."""
        melhores: dict[tuple[str, str], Path] = {}
        pasta = raiz / "planilha"
        for caminho in pasta.iterdir() if pasta.is_dir() else []:
            if RE_COPIA.match(caminho.name):
                chave = (caminho.name.split("-", 1)[0], caminho.suffix)
                if chave not in melhores or caminho.name > melhores[chave].name:
                    melhores[chave] = caminho
        return set(melhores.values())

    def pacote_devido(self, agora: datetime | None = None) -> bool:
        """Já passou o intervalo (semanal ou mensal) desde o último pacote .zip?"""
        agora = agora or datetime.now()
        with self._lock:
            estado = dict(self._estado)
        dias = PACOTES.get(estado.get("pacote") or "semanal")
        if not estado["ativo"] or not estado["pasta"] or dias is None:
            return False
        falha = estado.get("falha_pacote")
        if falha and agora - datetime.fromisoformat(falha) < ESPERA_APOS_FALHA_PACOTE:
            return False  # não fica tentando sem parar
        ultimo = (estado.get("ultimo_pacote") or {}).get("quando")
        return not ultimo or agora - datetime.fromisoformat(ultimo) >= timedelta(days=dias)

    # ------------------------------------------------------------------ conferência

    def verificar(self, completa: bool = True) -> dict:
        """Confere o backup. ``completa``: relê cada arquivo e compara a impressão digital com o manifesto."""
        if not self._executando.acquire(blocking=False):
            return {"ok": False, "quando": _agora(), "itens": [{"nome": "Backup", "ok": False,
                                                                "detalhe": "Um backup está em andamento; tente em instantes."}]}
        try:
            return self._verificar(completa)
        finally:
            self._executando.release()

    def _verificar(self, completa: bool) -> dict:
        itens: list[dict] = []

        def item(nome: str, ok: bool, detalhe: str) -> None:
            itens.append({"nome": nome, "ok": bool(ok), "detalhe": detalhe})

        try:
            raiz = self._raiz()
        except ValueError as exc:
            resultado = {"ok": False, "quando": _agora(), "completa": completa, "itens": [
                {"nome": "Pasta do backup", "ok": False, "detalhe": str(exc)}]}
            with self._lock:
                self._estado["verificacao"] = resultado
                self._gravar()
            return resultado
        with self._lock:
            levar_codigo = bool(self._estado.get("codigo", True)) and bool(self.pasta_codigo)

        # bancos de dados: a cópia mais recente abre e está íntegra?
        recentes = sorted(c for c in self._copias_mais_recentes(raiz) if c.suffix == ".db")
        esperados = sum(1 for base in [{"copiar_banco": self.copiar_banco}, *self.extras] if base.get("copiar_banco"))
        for copia in recentes:
            conexao = None
            try:
                conexao = sqlite3.connect(f"file:{quote(copia.as_posix(), safe='/:')}?mode=ro", uri=True)
                integro = conexao.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                registros = conexao.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
                item(f"Banco {copia.name}", integro, f"{registros} registro(s), íntegro" if integro else "o arquivo está corrompido")
            except sqlite3.Error as exc:
                item(f"Banco {copia.name}", False, f"não abre: {exc}")
            finally:
                if conexao is not None:  # sempre fecha: um arquivo aberto impediria o próximo backup de substituí-lo
                    conexao.close()
        if esperados and len(recentes) < esperados:
            item("Bancos de dados", False, f"{len(recentes)} de {esperados} banco(s) no backup")

        # arquivos (PDFs, fotos, comprovantes): todos estão lá, com o mesmo tamanho?
        if self.pasta_arquivos.is_dir():
            origem = {p.name: p.stat().st_size for p in self.pasta_arquivos.iterdir() if p.is_file()}
            faltando = [n for n, tamanho in origem.items()
                        if not (raiz / "arquivos" / n).is_file() or (raiz / "arquivos" / n).stat().st_size != tamanho]
            item("Boletos, comprovantes e fotos", not faltando,
                 f"{len(origem)} arquivo(s) no backup" if not faltando else f"{len(faltando)} de {len(origem)} arquivo(s) faltando ou diferentes")

        # configurações
        faltando = [p.name for p in self._arquivos_de_configuracao() if not (raiz / "configuracoes" / p.name).is_file()]
        item("Configurações", not faltando, "todas no backup" if not faltando else f"faltando: {', '.join(faltando)}")

        # código-fonte e histórico de versões
        if levar_codigo:
            codigo = self._arquivos_do_codigo(raiz)
            faltando = [o for o in codigo if not (raiz / "codigo" / o.relative_to(self.pasta_codigo)).is_file()
                        or (raiz / "codigo" / o.relative_to(self.pasta_codigo)).stat().st_size != o.stat().st_size]
            item("Código-fonte", bool(codigo) and not faltando,
                 f"{len(codigo)} arquivo(s) no backup" if codigo and not faltando
                 else f"{len(faltando)} de {len(codigo)} arquivo(s) faltando ou diferentes")
            if self.gerar_bundle:
                bundle = raiz / "versoes" / NOME_BUNDLE
                if not bundle.is_file():
                    item("Histórico de versões", False, "o arquivo finpro.bundle não está no backup")
                elif self.verificar_bundle and completa:
                    integro = bool(self.verificar_bundle(bundle))
                    item("Histórico de versões", integro, "completo e íntegro" if integro else "o arquivo finpro.bundle está corrompido")
                else:
                    item("Histórico de versões", bundle.stat().st_size > 0, _tamanho_legivel(bundle.stat().st_size))

        # impressão digital de cada arquivo (só na conferência completa)
        if completa:
            try:
                manifesto = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))["arquivos"]
                diferentes = [nome for nome, dados in manifesto.items()
                              if not (raiz / nome).is_file() or _sha256(raiz / nome) != dados["sha256"]]
                item("Impressão digital dos arquivos", not diferentes,
                     f"{len(manifesto)} arquivo(s) conferido(s) um a um" if not diferentes
                     else f"{len(diferentes)} arquivo(s) alterado(s) ou corrompido(s): {', '.join(diferentes[:5])}")
            except (OSError, json.JSONDecodeError, KeyError) as exc:
                item("Impressão digital dos arquivos", False, f"não foi possível ler o manifesto: {exc}")
            pacotes = self.pacotes(raiz)
            if pacotes:
                try:
                    with zipfile.ZipFile(pacotes[0]["caminho"]) as pacote:
                        ruim = pacote.testzip()
                    item(f"Pacote {pacotes[0]['arquivo']}", ruim is None,
                         f"íntegro ({pacotes[0]['tamanho_legivel']})" if ruim is None else f"arquivo corrompido dentro do pacote: {ruim}")
                except (OSError, zipfile.BadZipFile) as exc:
                    item(f"Pacote {pacotes[0]['arquivo']}", False, f"não abre: {exc}")

        resultado = {"ok": all(i["ok"] for i in itens), "quando": _agora(), "completa": completa, "itens": itens}
        with self._lock:
            self._estado["verificacao"] = resultado
            self._gravar()
        if not resultado["ok"]:
            log.warning("O backup não passou na conferência: %s",
                        "; ".join(f"{i['nome']}: {i['detalhe']}" for i in itens if not i["ok"]))
        return resultado

    # ------------------------------------------------------------------ agendador

    def deve_executar(self, agora: datetime | None = None) -> bool:
        agora = agora or datetime.now()
        with self._lock:
            estado = dict(self._estado)
        if not estado["ativo"] or not estado["pasta"]:
            return False
        if estado.get("ultimo_sucesso") and datetime.fromisoformat(estado["ultimo_sucesso"]).date() >= agora.date():
            return False
        ultimo = estado.get("ultimo") or {}
        if ultimo.get("ok") is False and agora - datetime.fromisoformat(ultimo["quando"]) < ESPERA_APOS_FALHA:
            return False
        horario = datetime.strptime(estado["horario"], "%H:%M").time()
        atrasado = not estado.get("ultimo_sucesso") or agora.date() - datetime.fromisoformat(estado["ultimo_sucesso"]).date() > timedelta(days=1)
        return agora.time() >= horario or atrasado  # se o computador ficou desligado, faz assim que abrir

    def rodar_agendado(self, agora: datetime | None = None) -> None:
        """Uma passada do agendador: o backup do dia e, quando for a vez, o pacote .zip."""
        if self.deve_executar(agora):
            resultado = self.gerar_pacote(agora) if self.pacote_devido(agora) else self.executar()
            if not resultado.get("ok"):
                return
        elif self.pacote_devido(agora) and (self.status(agora)["situacao"] == "ok"):
            self.gerar_pacote(agora)  # backup do dia já feito, mas o pacote da semana ainda não

    def iniciar_agendador(self, espera_inicial: float = 60) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            if self._parar.wait(espera_inicial):
                return
            while True:
                try:
                    self.rodar_agendado()
                except Exception:
                    log.exception("Falha no agendador de backup")
                if self._parar.wait(INTERVALO_VERIFICACAO):
                    return

        self._thread = threading.Thread(target=laco, name="agendador-backup", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

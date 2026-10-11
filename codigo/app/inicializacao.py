"""Iniciar o Fin Pro junto com o Windows.

Cria um pequeno script na pasta "Inicializar" do usuário que abre o aplicativo (janela própria) quando
o computador é ligado — ou apenas o ícone na bandeja, se preferir iniciar minimizado. Assim o agendador
de lembretes funciona mesmo que o sistema não seja aberto manualmente.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import config
from .config import BASE_DIR

NOME_ARQUIVO = f"{config.NOME_APP}.vbs"
NOMES_ANTIGOS = ("Leitor de Boletos.vbs",)  # de antes da troca de nome
ARGUMENTO_BANDEJA = "--bandeja"


def pasta_inicializar() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if os.name != "nt" or not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _pythonw() -> Path:
    candidato = Path(sys.executable).with_name("pythonw.exe")
    return candidato if candidato.exists() else Path(sys.executable)


def _limpar_antigos(pasta: Path | None) -> None:
    """O script com o nome antigo sai de cena (senão o aplicativo abriria duas vezes)."""
    for antigo in NOMES_ANTIGOS if pasta else ():
        (pasta / antigo).unlink(missing_ok=True)


def status(pasta: Path | None = None) -> dict:
    pasta = pasta or pasta_inicializar()
    if pasta and not (pasta / NOME_ARQUIVO).exists() and any((pasta / a).exists() for a in NOMES_ANTIGOS):
        ativar(pasta)  # já estava ligado com o nome antigo: refaz com o nome novo
    arquivo = pasta / NOME_ARQUIVO if pasta else None
    ativo = bool(arquivo and arquivo.exists())
    minimizado = False
    if ativo:
        try:
            minimizado = ARGUMENTO_BANDEJA in arquivo.read_text(encoding="utf-16")
        except (OSError, UnicodeError):
            minimizado = False
    return {"disponivel": pasta is not None, "ativo": ativo, "minimizado": minimizado}


def ativar(pasta: Path | None = None, minimizado: bool = False) -> dict:
    pasta = pasta or pasta_inicializar()
    if pasta is None:
        raise RuntimeError("Disponível apenas no Windows.")
    pasta.mkdir(parents=True, exist_ok=True)
    argumentos = f"-m app {ARGUMENTO_BANDEJA}" if minimizado else "-m app"
    script = (
        'Set shell = CreateObject("WScript.Shell")\r\n'
        'shell.Environment("Process")("LEITOR_ABRIR_NAVEGADOR") = "0"\r\n'
        f'shell.CurrentDirectory = "{BASE_DIR}"\r\n'
        f'shell.Run """{_pythonw()}"" {argumentos}", 0, False\r\n'
    )
    # UTF-16 com BOM: o WScript lê corretamente caminhos com acentos (ex.: C:\Users\Fábio)
    (pasta / NOME_ARQUIVO).write_text(script, encoding="utf-16", newline="")
    _limpar_antigos(pasta)
    return {"disponivel": True, "ativo": True, "minimizado": minimizado}


def desativar(pasta: Path | None = None) -> dict:
    pasta = pasta or pasta_inicializar()
    if pasta is not None:
        (pasta / NOME_ARQUIVO).unlink(missing_ok=True)
        _limpar_antigos(pasta)
    return status(pasta)

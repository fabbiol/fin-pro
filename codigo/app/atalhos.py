"""Atalhos do aplicativo na Área de Trabalho e no Menu Iniciar (Windows)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from . import config
from .config import BASE_DIR

NOME = config.NOME_APP
NOMES_ANTIGOS = ("Leitor de Boletos",)  # atalhos de antes da troca de nome: são apagados ao criar os novos
ICONE = BASE_DIR / "web" / "icons" / "app.ico"

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$shell = New-Object -ComObject WScript.Shell
$criados = @()
foreach ($pasta in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
  $caminho = Join-Path $pasta ($env:LEITOR_NOME + '.lnk')
  $atalho = $shell.CreateShortcut($caminho)
  $atalho.TargetPath = $env:LEITOR_ALVO
  $atalho.Arguments = '-m app'
  $atalho.WorkingDirectory = $env:LEITOR_DIR
  $atalho.IconLocation = $env:LEITOR_ICONE
  $atalho.Description = 'Fin Pro - boletos, Pix e lembretes de vencimento'
  $atalho.Save()
  $criados += $caminho
}
ConvertTo-Json -InputObject @($criados) -Compress
"""


def pythonw() -> Path:
    candidato = Path(sys.executable).with_name("pythonw.exe")
    return candidato if candidato.exists() else Path(sys.executable)


def _pastas_de_atalho() -> list[Path]:
    perfil = Path(os.environ.get("USERPROFILE", Path.home()))
    pastas = [perfil / "Desktop", perfil / "OneDrive" / "Desktop", perfil / "OneDrive" / "Área de Trabalho"]
    if os.environ.get("APPDATA"):
        pastas.append(Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return pastas


def _caminhos_provaveis(nome: str = "") -> list[Path]:
    return [pasta / f"{nome or NOME}.lnk" for pasta in _pastas_de_atalho()]


def remover_antigos() -> list[str]:
    """Apaga os atalhos com o nome antigo do aplicativo (para não ficarem dois ícones iguais)."""
    removidos = []
    for antigo in NOMES_ANTIGOS:
        for caminho in _caminhos_provaveis(antigo):
            try:
                if caminho.exists():
                    caminho.unlink()
                    removidos.append(str(caminho))
            except OSError:
                pass
    return removidos


def status() -> dict:
    existentes = [str(c) for c in _caminhos_provaveis() if c.exists()]
    return {"disponivel": os.name == "nt", "criados": existentes}


def criar_atalhos() -> list[str]:
    if os.name != "nt":
        raise RuntimeError("Atalhos disponíveis apenas no Windows.")
    ambiente = {**os.environ, "LEITOR_NOME": NOME, "LEITOR_ALVO": str(pythonw()), "LEITOR_DIR": str(BASE_DIR),
                "LEITOR_ICONE": str(ICONE)}
    resultado = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT],
        env=ambiente, capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    saida = resultado.stdout.decode("utf-8", errors="replace").strip()
    if resultado.returncode != 0:
        erro = resultado.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise RuntimeError("Não foi possível criar os atalhos" + (f": {erro[0]}" if erro else "."))
    criados = json.loads(saida) if saida else []
    remover_antigos()
    return criados if isinstance(criados, list) else [criados]

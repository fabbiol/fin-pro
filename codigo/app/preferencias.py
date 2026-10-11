"""Preferências do aplicativo de desktop (dados/app.json)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import config

PADRAO = {
    "fechar_para_bandeja": True,  # o X esconde a janela; os lembretes continuam funcionando
    "minimizado_ao_iniciar": False,  # ao ligar o computador, abre só o ícone na bandeja
    "aviso_bandeja_mostrado": False,
}
_lock = threading.Lock()


def _caminho(caminho: Path | None) -> Path:
    return Path(caminho) if caminho else config.DADOS_DIR / "app.json"


def ler(caminho: Path | None = None) -> dict:
    arquivo = _caminho(caminho)
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        dados = {}
    return {chave: type(padrao)(dados.get(chave, padrao)) for chave, padrao in PADRAO.items()}


def atualizar(alteracoes: dict, caminho: Path | None = None) -> dict:
    arquivo = _caminho(caminho)
    with _lock:
        atuais = ler(arquivo)
        atuais.update({k: bool(v) for k, v in alteracoes.items() if k in PADRAO and v is not None})
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        temporario = arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(atuais, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, arquivo)
    return atuais

"""Preço que a empresa paga no litro de cada combustível (tabela de referência).

Vale para o canhoto que não traz o preço: o abastecimento sai com o valor = litros × preço daqui. Quando o canhoto
ou a compra trazem o preço, vale o que veio neles. Fica em ``dados/diesel_precos.json``.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime

from .. import config
from .modelos import COMBUSTIVEIS

_lock = threading.Lock()


def _caminho():
    return config.DADOS_DIR / "diesel_precos.json"


def ler() -> dict[str, dict]:
    """{combustível: {"preco": 6.75, "atualizado_em": "...", "por": "Fábio"}}"""
    try:
        salvo = json.loads(_caminho().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {c: v for c, v in salvo.items() if isinstance(v, dict) and float(v.get("preco") or 0) > 0}


def preco(combustivel: str) -> float:
    return float((ler().get(combustivel) or {}).get("preco") or 0)


def salvar(novos: dict[str, float], usuario: str = "") -> dict[str, dict]:
    with _lock:
        atuais = ler()
        for combustivel, valor in novos.items():
            if combustivel not in COMBUSTIVEIS:
                raise ValueError(f"Combustível desconhecido: {combustivel}.")
            valor = round(float(valor or 0), 4)
            if valor < 0 or valor > 100:
                raise ValueError(f"Preço inválido para {combustivel}.")
            if valor:
                atuais[combustivel] = {"preco": valor, "atualizado_em": datetime.now().isoformat(timespec="seconds"),
                                       "por": usuario}
            else:
                atuais.pop(combustivel, None)
        caminho = _caminho()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(atuais, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporario, caminho)
        return atuais


def publico() -> list[dict]:
    precos = ler()
    return [{"combustivel": c, "preco": (precos.get(c) or {}).get("preco"),
             "atualizado_em": (precos.get(c) or {}).get("atualizado_em"), "por": (precos.get(c) or {}).get("por") or ""}
            for c in COMBUSTIVEIS]

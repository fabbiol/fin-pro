"""Configuração do módulo Empresas: dados da minha empresa, dia do fechamento e o bot de notas fiscais."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
from datetime import datetime, time
from pathlib import Path

from .modelos import DIA_FECHAMENTO_PADRAO

MASCARA = "••••••••"

PADRAO = {
    "minha_empresa": {"nome": "", "cnpj": ""},
    "dia_fechamento": DIA_FECHAMENTO_PADRAO,
    "fechamento_automatico": True,
    "hora_envio": "08:00",
    "ultimo_fechamento": "",  # AAAA-MM já enviado
    "bot": {"ativo": False, "token": "", "offset": 0, "destinatarios": [], "chats": {},
            "ultima_verificacao": None, "ultimo_erro": None},
}


def _hora(texto: str) -> time:
    try:
        h, m = str(texto or "08:00").split(":")[:2]
        return time(max(0, min(23, int(h))), max(0, min(59, int(m))))
    except (TypeError, ValueError):
        return time(8, 0)


def normalizar_destinatarios(lista) -> list[dict]:
    """Pessoas e grupos que falam com o bot de notas: ``[{"chat_id": "123", "nome": "Almir", "empresa": ""}]``."""
    saida, vistos = [], set()
    for item in lista or []:
        if isinstance(item, str):
            item = {"chat_id": item}
        if not isinstance(item, dict):
            continue
        chat_id = re.sub(r"[^\d-]", "", str(item.get("chat_id") or ""))
        if not chat_id or chat_id in vistos:
            continue
        vistos.add(chat_id)
        saida.append({"chat_id": chat_id, "nome": str(item.get("nome") or "")[:60],
                      "empresa": str(item.get("empresa") or "")[:60], "ativo": bool(item.get("ativo", True))})
    return saida[:50]


class ConfigEmpresas:
    """Arquivo ``dados/empresas.json``: quem sou eu, quando fecho o mês e o bot que recebe as notas."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._lock = threading.RLock()
        self._estado = self._ler()

    def _ler(self) -> dict:
        estado = copy.deepcopy(PADRAO)
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return estado
        if isinstance(salvo.get("minha_empresa"), dict):
            estado["minha_empresa"].update({k: str(v or "") for k, v in salvo["minha_empresa"].items()
                                            if k in estado["minha_empresa"]})
        if isinstance(salvo.get("bot"), dict):
            estado["bot"].update({k: v for k, v in salvo["bot"].items() if k in estado["bot"]})
        estado["bot"]["destinatarios"] = normalizar_destinatarios(estado["bot"].get("destinatarios"))
        estado["bot"]["chats"] = estado["bot"].get("chats") if isinstance(estado["bot"].get("chats"), dict) else {}
        for campo in ("dia_fechamento", "fechamento_automatico", "hora_envio", "ultimo_fechamento"):
            if campo in salvo and salvo[campo] is not None:
                estado[campo] = salvo[campo]
        estado["dia_fechamento"] = max(1, min(28, int(estado["dia_fechamento"] or DIA_FECHAMENTO_PADRAO)))
        return estado

    def gravar(self) -> None:
        with self._lock:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.caminho.with_suffix(".tmp")
            temporario.write_text(json.dumps(self._estado, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ leitura

    @property
    def minha_empresa(self) -> dict:
        with self._lock:
            return dict(self._estado["minha_empresa"])

    @property
    def dia_fechamento(self) -> int:
        with self._lock:
            return int(self._estado["dia_fechamento"])

    @property
    def hora_envio(self) -> time:
        with self._lock:
            return _hora(self._estado["hora_envio"])

    def bot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._estado["bot"])

    def token(self) -> str:
        with self._lock:
            return (self._estado["bot"].get("token") or "").strip()

    def destinatarios(self) -> list[dict]:
        with self._lock:
            return [d for d in self._estado["bot"]["destinatarios"] if d.get("ativo", True)]

    def publica(self) -> dict:
        with self._lock:
            estado = copy.deepcopy(self._estado)
        bot = estado["bot"]
        bot["token"] = MASCARA if bot.get("token") else ""
        bot.pop("offset", None)
        bot["chats"] = list(bot.get("chats", {}).values())
        return estado

    # ------------------------------------------------------------------ escrita

    def atualizar(self, novo: dict) -> dict:
        with self._lock:
            estado = copy.deepcopy(self._estado)
            empresa = novo.get("minha_empresa")
            if isinstance(empresa, dict):
                for campo in ("nome", "cnpj"):
                    if empresa.get(campo) is not None:
                        estado["minha_empresa"][campo] = str(empresa[campo]).strip()[:120]
            if novo.get("dia_fechamento") is not None:
                dia = int(novo["dia_fechamento"])
                if not 1 <= dia <= 28:
                    raise ValueError("O dia do fechamento deve ficar entre 1 e 28.")
                estado["dia_fechamento"] = dia
            if novo.get("fechamento_automatico") is not None:
                estado["fechamento_automatico"] = bool(novo["fechamento_automatico"])
            if novo.get("hora_envio"):
                estado["hora_envio"] = _hora(novo["hora_envio"]).strftime("%H:%M")
            bot = novo.get("bot")
            if isinstance(bot, dict):
                if bot.get("token") is not None and bot["token"] != MASCARA:
                    estado["bot"]["token"] = str(bot["token"]).strip()[:200]
                    estado["bot"]["ultimo_erro"] = None
                if bot.get("ativo") is not None:
                    estado["bot"]["ativo"] = bool(bot["ativo"])
                    estado["bot"]["ultimo_erro"] = None
                if bot.get("destinatarios") is not None:
                    estado["bot"]["destinatarios"] = normalizar_destinatarios(bot["destinatarios"])
            if estado["bot"]["ativo"] and not estado["bot"]["token"]:
                raise ValueError("Informe o token do bot de notas fiscais (crie um bot no @BotFather).")
            self._estado = estado
            self.gravar()
        return self.publica()

    def registrar_envio(self, competencia: str) -> None:
        with self._lock:
            self._estado["ultimo_fechamento"] = competencia
            self.gravar()

    def registrar_bot(self, **campos) -> None:
        with self._lock:
            self._estado["bot"].update(campos)
            self.gravar()

    def lembrar_chat(self, chat: dict) -> None:
        chat_id = str(chat.get("id") or "")
        if not chat_id:
            return
        nome = (chat.get("title") or " ".join(p for p in (chat.get("first_name"), chat.get("last_name")) if p)
                or chat.get("username") or chat_id)
        with self._lock:
            chats = self._estado["bot"]["chats"]
            chats[chat_id] = {"chat_id": chat_id, "nome": nome, "usuario": chat.get("username") or "",
                              "tipo": chat.get("type") or "private", "quando": datetime.now().isoformat(timespec="seconds")}
            if len(chats) > 60:
                for antigo in sorted(chats.values(), key=lambda c: c["quando"])[:len(chats) - 60]:
                    chats.pop(antigo["chat_id"], None)
            self.gravar()

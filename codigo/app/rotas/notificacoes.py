"""Notificações de vencimento: sininho, lembretes, canais (Windows, Telegram, e-mail) e testes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import config
from .. import contexto as ctx
from ..notificacoes import canais
from ..notificacoes.servico import MASCARA
from .comum import erro

router = APIRouter()


class RegraEntrada(BaseModel):
    id: str | None = Field(None, max_length=32)
    tipo: Literal["vencimento", "antes", "vencidos"]
    dias: int = Field(0, ge=0, le=365)
    horarios: list[str] = Field(..., min_length=1, max_length=12)
    canais: list[Literal["windows", "telegram", "email"]] = Field(default_factory=lambda: ["windows", "telegram", "email"])
    ativo: bool = True


class ResumoEntrada(BaseModel):
    ativo: bool | None = None
    horario: str | None = Field(None, max_length=5)
    canais: list[Literal["windows", "telegram", "email"]] | None = None


class ConfigNotificacoesEntrada(BaseModel):
    ativo: bool | None = None
    resumos: dict[Literal["segunda", "sexta"], ResumoEntrada] | None = None
    dias_semana: list[int] | None = Field(None, max_length=7)
    regras: list[RegraEntrada] | None = Field(None, max_length=20)
    windows: dict | None = None
    telegram: dict | None = None
    email: dict | None = None


class TesteCanalEntrada(BaseModel):
    canal: Literal["windows", "telegram", "email"]


class DetectarTelegramEntrada(BaseModel):
    token: str | None = None


class ChavesAvisoEntrada(BaseModel):
    chaves: list[str] = Field(default_factory=list, max_length=1000)


class ChaveAvisoEntrada(BaseModel):
    chave: str = Field(..., max_length=200)


class TesteTelegramEntrada(BaseModel):
    chat_id: str = Field(..., max_length=40)
    token: str | None = Field(None, max_length=200)


@router.get("/api/notificacoes")
def obter_notificacoes():
    alertas = ctx.notificacoes.alertas()
    return {
        "alertas": alertas,
        "nao_vistos": sum(1 for a in alertas if not a["visto"]),
        "janela_dias": ctx.notificacoes.janela_dias(),
        "agenda": ctx.notificacoes.agenda(),
        "config": ctx.notificacoes.config_publica(),
        "historico": ctx.notificacoes.historico(),
        "automaticas": config.NOTIFICACOES_AUTOMATICAS,
    }


@router.post("/api/notificacoes/vistos")
def marcar_avisos_vistos(entrada: ChavesAvisoEntrada):
    """Avisos do sininho que já foram vistos: saem da contagem até a situação do boleto mudar."""
    return {"marcados": ctx.notificacoes.marcar_vistos(entrada.chaves)}


@router.post("/api/notificacoes/dispensar")
def dispensar_aviso(entrada: ChaveAvisoEntrada):
    return {"dispensado": ctx.notificacoes.dispensar(entrada.chave)}


@router.post("/api/notificacoes/restaurar")
def restaurar_avisos():
    return {"restaurados": ctx.notificacoes.restaurar_dispensados()}


@router.put("/api/notificacoes/config")
def salvar_config_notificacoes(entrada: ConfigNotificacoesEntrada):
    try:
        return ctx.notificacoes.atualizar_config(entrada.model_dump(exclude_none=True))
    except ValueError as exc:
        raise erro(422, "config_invalida", str(exc)) from exc


@router.post("/api/notificacoes/testar")
def testar_notificacao(entrada: TesteCanalEntrada):
    return ctx.notificacoes.testar(entrada.canal)


@router.post("/api/notificacoes/enviar-agora")
def enviar_notificacoes_agora():
    return ctx.notificacoes.enviar_agora()


@router.get("/api/notificacoes/resumo/{tipo}")
def previa_resumo(tipo: Literal["segunda", "sexta"]):
    """Como o resumo da semana ficaria se fosse enviado agora."""
    return ctx.notificacoes.previa_resumo(tipo)


@router.post("/api/notificacoes/resumo/{tipo}/enviar")
def enviar_resumo(tipo: Literal["segunda", "sexta"]):
    return ctx.notificacoes.enviar_resumo(tipo)


@router.post("/api/notificacoes/telegram/detectar")
def detectar_chat_telegram(entrada: DetectarTelegramEntrada):
    token = entrada.token if entrada.token and entrada.token != MASCARA else ctx.notificacoes.segredo("telegram", "token")
    if not token:
        raise erro(422, "token_ausente", "Informe o token do bot do Telegram.")
    try:
        encontrados = canais.procurar_chats_telegram(token)
    except canais.ErroCanal as exc:
        raise erro(502, "telegram_falhou", str(exc)) from exc
    if ctx.caixa_entrada is not None:
        # Com o recebimento de boletos pelo Telegram ligado, o sistema já leu as mensagens: junta as que ele guardou
        conhecidos = {c["chat_id"] for c in encontrados["chats"]}
        encontrados["chats"] += [{k: c[k] for k in ("chat_id", "nome", "tipo", "usuario")}
                                 for c in ctx.caixa_entrada.chats_recentes() if c["chat_id"] not in conhecidos]
    primeiro = encontrados["chats"][0] if encontrados["chats"] else {}
    return {**encontrados, "chat_id": primeiro.get("chat_id"), "nome": primeiro.get("nome")}


@router.post("/api/notificacoes/telegram/testar")
def testar_destinatario_telegram(entrada: TesteTelegramEntrada):
    """Envia uma mensagem de teste para uma única pessoa ou grupo."""
    token = entrada.token if entrada.token and entrada.token != MASCARA else None
    try:
        ctx.notificacoes.testar_destinatario_telegram(entrada.chat_id.strip(), token)
    except canais.ErroCanal as exc:
        raise erro(502, "telegram_falhou", str(exc)) from exc
    return {"ok": True}

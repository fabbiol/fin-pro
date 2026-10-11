"""Caixa de entrada: boletos recebidos por e-mail e Telegram, aguardando conferência na tela Ler boletos."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .. import contexto as ctx
from .comum import SOMENTE_ADMIN, autor, erro

router = APIRouter()


class ConfigEntrada(BaseModel):
    email: dict | None = None
    telegram: dict | None = None


class VerificarEntrada(BaseModel):
    canal: Literal["email", "telegram"]


class AssociarEntrada(BaseModel):
    aba: Literal["boletos", "pix"]
    id: int = Field(..., gt=0)


class DescartarEntrada(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=300)


def _caixa():
    if ctx.caixa_entrada is None:
        raise erro(503, "indisponivel", "A caixa de entrada ainda está iniciando.")
    return ctx.caixa_entrada


@router.get("/api/entrada")
def listar_entrada(concluidos: bool = False):
    caixa = _caixa()
    return {"itens": caixa.listar(concluidos), "pendentes": caixa.contagem(), "config": caixa.config_publica()}


@router.get("/api/entrada/{id_}")
def obter_item(id_: str):
    item = _caixa().obter(id_)
    if not item:
        raise erro(404, "nao_encontrado", "Este arquivo não está mais na caixa de entrada.")
    item.pop("hash", None)
    return item


@router.post("/api/entrada/descartar")
def descartar_itens(entrada: DescartarEntrada):
    caixa = _caixa()
    return {"descartados": sum(1 for id_ in entrada.ids if caixa.descartar(id_)), "pendentes": caixa.contagem()}


@router.put("/api/entrada/config", dependencies=SOMENTE_ADMIN)
def configurar_entrada(entrada: ConfigEntrada):
    try:
        return _caixa().configurar(entrada.model_dump(exclude_none=True))
    except ValueError as exc:
        raise erro(422, "config_invalida", str(exc)) from exc


@router.post("/api/entrada/verificar")
def verificar_agora(entrada: VerificarEntrada, request: Request):
    try:
        resultado = _caixa().verificar_agora(entrada.canal)
    except ValueError as exc:
        raise erro(422, "verificacao_falhou", str(exc)) from exc
    return {**resultado, **listar_entrada()}


@router.post("/api/entrada/{id_}/registrar")
def registrar_comprovante(id_: str, entrada: AssociarEntrada, request: Request):
    """Comprovante que ficou em dúvida: registra o pagamento no lançamento escolhido."""
    caixa = _caixa()
    try:
        item = caixa.associar(id_, entrada.aba, entrada.id, autor(request))
    except ValueError as exc:
        raise erro(409, "comprovante_indisponivel", str(exc)) from exc
    return {"item": item, "pendentes": caixa.contagem()}

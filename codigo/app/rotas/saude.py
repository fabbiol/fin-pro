"""Saúde do sistema: diagnóstico e ações rápidas (atualizar a planilha agora, limpar logs)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from .. import config, registro_log, saude
from .. import contexto as ctx
from .comum import erro, somente_local

router = APIRouter()


@router.get("/api/saude")
def diagnostico():
    return saude.diagnostico()


@router.post("/api/saude/atualizar-planilha")
def atualizar_planilha():
    if not hasattr(ctx.planilha, "exportar"):
        raise erro(409, "nao_suportado", "Esta versão grava direto na planilha.")
    if not ctx.planilha.exportar():
        raise erro(423, "planilha_aberta", "A planilha está aberta no Excel. Feche o arquivo e tente de novo.")
    return saude.diagnostico()


@router.post("/api/saude/limpar-logs")
def limpar_logs(request: Request):
    somente_local(request, precisa_startfile=False)
    liberados = registro_log.limpar(config.DADOS_DIR / "leitor.log")
    return {"liberados": liberados, **saude.diagnostico()}

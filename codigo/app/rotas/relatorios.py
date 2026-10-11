"""Central de relatórios: o relatório geral do mês (cada parte conforme as permissões de quem entrou) e o Excel."""

from __future__ import annotations

from fastapi import APIRouter, Request

from .. import acesso, fechamento, relatorio_geral
from .comum import XLSX, anexo, erro

router = APIRouter()


def _montar(request: Request, mes: str | None) -> dict:
    try:
        inicio = fechamento.ler_mes(mes)
    except ValueError as exc:
        raise erro(422, "mes_invalido", str(exc)) from exc
    return relatorio_geral.montar(inicio, lambda permissao: acesso.pode(request, permissao))


@router.get("/api/relatorio-geral")
def relatorio_do_mes(request: Request, mes: str | None = None):
    return _montar(request, mes)


@router.get("/api/relatorio-geral/arquivo")
def baixar_relatorio_do_mes(request: Request, mes: str | None = None):
    dados = _montar(request, mes)
    return anexo(relatorio_geral.gerar_xlsx(dados), XLSX, f"relatorio-geral-{dados['mes']}.xlsx")

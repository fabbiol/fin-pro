"""Centros de custo e análise de gastos (boletos + Pix)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .. import fechamento, servicos
from ..arquivos import RepositorioArquivos
from .. import contexto as ctx
from .comum import XLSX, anexo, autor, erro

router = APIRouter()


class CentroEntrada(BaseModel):
    nome: str = Field(..., min_length=1, max_length=60)
    descricao: str = Field("", max_length=200)
    ativo: bool = True


class CentroEdicao(CentroEntrada):
    nome_anterior: str = Field(..., min_length=1, max_length=60)


@router.get("/api/centros")
def listar_centros():
    uso: dict[str, dict] = {}
    for origem, repo in (("boletos", ctx.repositorio), ("pix", ctx.repositorio_pix), ("dinheiro", ctx.repositorio_caixa)):
        for r in repo.listar():
            nome = (r.get("centro_custo") or "").strip()
            if not nome or r.get("status") == "Cancelado" or (origem == "dinheiro" and r.get("movimento") != "Saída"):
                continue
            item = uso.setdefault(nome.lower(), {"nome": nome, "boletos": 0, "pix": 0, "dinheiro": 0, "total": 0.0})
            item[origem] += 1
            item["total"] += float(r.get("valor") or 0)
    centros = ctx.planilha.listar_centros()
    conhecidos = {c["nome"].lower() for c in centros}
    centros += [{"nome": u["nome"], "descricao": "", "ativo": True} for chave, u in uso.items() if chave not in conhecidos]
    saida = []
    for centro in centros:
        u = uso.get(centro["nome"].lower(), {})
        saida.append({**centro, "boletos": u.get("boletos", 0), "pix": u.get("pix", 0), "dinheiro": u.get("dinheiro", 0),
                      "total": round(u.get("total", 0.0), 2)})
    saida.sort(key=lambda c: (not c["ativo"], c["nome"].lower()))
    return {"centros": saida}


@router.post("/api/centros", status_code=201)
def criar_centro(entrada: CentroEntrada, request: Request):
    try:
        return ctx.planilha.salvar_centro(entrada.nome, entrada.descricao, entrada.ativo, usuario=autor(request))
    except ValueError as exc:
        raise erro(422, "centro_invalido", str(exc)) from exc


@router.put("/api/centros")
def editar_centro(entrada: CentroEdicao, request: Request):
    try:
        return ctx.planilha.salvar_centro(entrada.nome, entrada.descricao, entrada.ativo, nome_anterior=entrada.nome_anterior,
                                      usuario=autor(request))
    except ValueError as exc:
        raise erro(422, "centro_invalido", str(exc)) from exc


CampoDataGastos = Literal["vencimento", "data_pagamento", "data_lancamento"]
ROTULO_CAMPO_DATA = {"vencimento": "vencimento", "data_pagamento": "pagamento", "data_lancamento": "lançamento"}


@router.get("/api/gastos")
def analise_gastos(
    de: date | None = None,
    ate: date | None = None,
    campo_data: CampoDataGastos = "vencimento",
    situacao: Literal["todos", "pagos", "pendentes"] = "todos",
    tipo: Literal["todos", "boleto", "pix", "dinheiro"] = "todos",
):
    from ..caixa.servico import saidas_para_gastos

    return servicos.analise_gastos(ctx.repositorio.listar(), ctx.repositorio_pix.listar(), saidas_para_gastos(),
                                   de=de, ate=ate, campo_data=campo_data, situacao_filtro=situacao, tipo=tipo)


@router.get("/api/gastos/exportar")
def exportar_gastos(
    de: date | None = None,
    ate: date | None = None,
    campo_data: CampoDataGastos = "vencimento",
    situacao: Literal["todos", "pagos", "pendentes"] = "todos",
    tipo: Literal["todos", "boleto", "pix", "dinheiro"] = "todos",
):
    analise = analise_gastos(de, ate, campo_data, situacao, tipo)
    periodo = (f"{de:%d/%m/%Y} a {ate:%d/%m/%Y}" if de and ate else f"desde {de:%d/%m/%Y}" if de
               else f"até {ate:%d/%m/%Y}" if ate else "todo o período")
    descricao = (f"{periodo} (data de {ROTULO_CAMPO_DATA[campo_data]}) · "
                 f"{ {'todos': 'boletos, Pix e dinheiro', 'boleto': 'somente boletos', 'pix': 'somente Pix', 'dinheiro': 'somente dinheiro (caixa)'}[tipo] } · "
                 f"{ {'todos': 'pagos e pendentes', 'pagos': 'somente pagos', 'pendentes': 'somente pendentes'}[situacao] }")
    return anexo(servicos.gerar_xlsx_analise(analise, descricao), XLSX, f"gastos-{date.today():%Y-%m-%d}.xlsx")


# --------------------------------------------------------------------------- fechamento do mês (para o contador)

BaseFechamento = Literal["vencimento", "pagamento"]


def _fechamento(mes: str | None, base: str) -> dict:
    try:
        inicio = fechamento.ler_mes(mes)
    except ValueError as exc:
        raise erro(422, "mes_invalido", str(exc)) from exc
    from ..caixa.servico import saidas_para_gastos

    return fechamento.montar(ctx.repositorio.listar(), ctx.repositorio_pix.listar(), inicio, base,
                             caixa=saidas_para_gastos())


@router.get("/api/relatorios/fechamento")
def fechamento_do_mes(mes: str | None = None, base: BaseFechamento = "vencimento"):
    return _fechamento(mes, base)


@router.get("/api/relatorios/fechamento/arquivo")
def baixar_fechamento(mes: str | None = None, base: BaseFechamento = "vencimento",
                      formato: Literal["xlsx", "pdf", "zip"] = "pdf"):
    dados = _fechamento(mes, base)
    nome = f"fechamento-{dados['mes']}{'-pagamentos' if base == 'pagamento' else ''}"
    if formato == "xlsx":
        return anexo(fechamento.gerar_xlsx(dados), XLSX, f"{nome}.xlsx")
    if formato == "pdf":
        return anexo(fechamento.gerar_pdf(dados), "application/pdf", f"{nome}.pdf")

    def comprovante(item: dict):
        return ctx.arquivos.caminho_original(RepositorioArquivos.id_de_caminho(item["comprovante"]) or "")

    return anexo(fechamento.gerar_zip(dados, comprovante), "application/zip", f"{nome}.zip")

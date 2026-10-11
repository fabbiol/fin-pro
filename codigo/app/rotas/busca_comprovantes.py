"""Central de comprovantes: busca com filtros em todas as partes do sistema e download em ZIP."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, Request

from .. import acesso, busca_comprovantes
from .comum import anexo, erro

router = APIRouter()

Situacao = Literal["com", "sem", "todos"]
Ordem = Literal["data", "valor", "nome"]
Direcao = Literal["asc", "desc"]


def _buscar(request: Request, q: str, tipos: str, de: date | None, ate: date | None, valor: str,
            valor_min: float | None, valor_max: float | None, numero: str, centro: str, pessoa: str,
            comprovante: str, ordenar: str, direcao: str) -> list[dict]:
    escolhidos = [t.strip() for t in (tipos or "").split(",") if t.strip()]
    desconhecidos = [t for t in escolhidos if t not in busca_comprovantes.TIPOS]
    if desconhecidos:
        raise erro(422, "tipo_invalido", f"Tipo de comprovante desconhecido: {', '.join(desconhecidos)}.")
    return busca_comprovantes.buscar(
        lambda permissao: acesso.pode(request, permissao), q=q, tipos=escolhidos or None, de=de, ate=ate, valor=valor,
        valor_min=valor_min, valor_max=valor_max, numero=numero, centro=centro, pessoa=pessoa,
        comprovante=comprovante, ordenar=ordenar, direcao=direcao)


@router.get("/api/comprovantes/busca")
def buscar_comprovantes(
    request: Request,
    q: str = Query("", max_length=200), tipos: str = Query("", max_length=200),
    de: date | None = None, ate: date | None = None, valor: str = Query("", max_length=30),
    valor_min: float | None = Query(None, ge=0), valor_max: float | None = Query(None, ge=0),
    numero: str = Query("", max_length=80), centro: str = Query("", max_length=60), pessoa: str = Query("", max_length=60),
    comprovante: Situacao = "com", ordenar: Ordem = "data", direcao: Direcao = "desc",
    pagina: int = Query(1, ge=1), por_pagina: int = Query(100, ge=10, le=500),
):
    itens = _buscar(request, q, tipos, de, ate, valor, valor_min, valor_max, numero, centro, pessoa, comprovante,
                    ordenar, direcao)
    inicio = (pagina - 1) * por_pagina
    return {
        "itens": [busca_comprovantes.serializar(i) for i in itens[inicio:inicio + por_pagina]],
        "total": len(itens), "pagina": pagina, "por_pagina": por_pagina,
        "resumo": busca_comprovantes.resumo(itens),
        "tipos": [{"tipo": t, "rotulo": busca_comprovantes.TIPOS[t]}
                  for t in busca_comprovantes.tipos_permitidos(lambda p: acesso.pode(request, p))],
    }


@router.get("/api/comprovantes/busca/zip")
def baixar_comprovantes(
    request: Request,
    q: str = Query("", max_length=200), tipos: str = Query("", max_length=200),
    de: date | None = None, ate: date | None = None, valor: str = Query("", max_length=30),
    valor_min: float | None = Query(None, ge=0), valor_max: float | None = Query(None, ge=0),
    numero: str = Query("", max_length=80), centro: str = Query("", max_length=60), pessoa: str = Query("", max_length=60),
    ordenar: Ordem = "data", direcao: Direcao = "desc",
):
    itens = _buscar(request, q, tipos, de, ate, valor, valor_min, valor_max, numero, centro, pessoa, "com",
                    ordenar, direcao)
    conteudo, quantidade = busca_comprovantes.gerar_zip(itens)
    if not quantidade:
        raise erro(404, "sem_comprovantes", "Nenhum comprovante com arquivo nestes filtros.")
    return anexo(conteudo, "application/zip", f"comprovantes-{date.today().isoformat()}.zip")

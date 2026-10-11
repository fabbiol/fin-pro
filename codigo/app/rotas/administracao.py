"""Senha de administrador e importação de boletos de outros sistemas (área restrita)."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .. import acesso, admin, importacao
from .. import contexto as ctx
from .comum import SOMENTE_ADMIN, XLSX, anexo, autor, erro, ip, somente_local
from .leitura import ler_upload

log = logging.getLogger("leitor_boletos")
router = APIRouter()


# --------------------------------------------------------------------------- senha de administrador


class SenhaAdminEntrada(BaseModel):
    senha: str = Field(..., max_length=200)
    confirmacao: str = Field(..., max_length=200)
    senha_atual: str | None = Field(None, max_length=200)


class EntrarAdminEntrada(BaseModel):
    senha: str = Field(..., max_length=200)


def _resposta_admin(request: Request, token: str | None = None) -> JSONResponse:
    estado = ctx.administrador.status(token or request.cookies.get(admin.COOKIE), ip(request))
    resposta = JSONResponse({**estado, "local": acesso.requisicao_local(request)})
    if token:
        resposta.set_cookie(admin.COOKIE, token, httponly=True, samesite="strict")
    return resposta


def _bloqueado(segundos: int) -> HTTPException:
    return erro(429, "bloqueado", f"Muitas senhas erradas. Tente de novo em {max(1, round(segundos / 60))} minuto(s).")


@router.get("/api/admin")
def estado_admin(request: Request):
    return _resposta_admin(request)


@router.post("/api/admin/senha")
def definir_senha_admin(entrada: SenhaAdminEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    endereco = ip(request)
    if ctx.administrador.senha_definida:
        restante = ctx.administrador.segundos_bloqueado(endereco)
        if restante:
            raise _bloqueado(restante)
        if not ctx.administrador.verificar(entrada.senha_atual or ""):
            ctx.administrador.registrar_falha(endereco)
            raise erro(403, "senha_incorreta", "A senha de administrador atual está incorreta.")
    if entrada.senha != entrada.confirmacao:
        raise erro(422, "senhas_diferentes", "As duas senhas não são iguais.")
    try:
        ctx.administrador.definir_senha(entrada.senha)
    except ValueError as exc:
        raise erro(422, "senha_fraca", str(exc)) from exc
    log.info("Senha de administrador %s", "trocada" if entrada.senha_atual else "criada")
    token, _ = ctx.administrador.entrar(entrada.senha, endereco)
    return _resposta_admin(request, token)


@router.post("/api/admin/entrar")
async def entrar_admin(entrada: EntrarAdminEntrada, request: Request):
    if not ctx.administrador.senha_definida:
        raise erro(409, "admin_sem_senha", "A senha de administrador ainda não foi criada. Crie-a no computador, em Configurações.")
    endereco = ip(request)
    token, bloqueio = await asyncio.to_thread(ctx.administrador.entrar, entrada.senha, endereco)
    if not token:
        await asyncio.sleep(0.8)  # atrasa tentativas automáticas
        if bloqueio:
            raise _bloqueado(bloqueio)
        log.warning("Senha de administrador incorreta (aparelho %s)", endereco)
        raise erro(401, "senha_incorreta", "Senha de administrador incorreta.")
    return _resposta_admin(request, token)


@router.post("/api/admin/sair")
def sair_admin(request: Request):
    ctx.administrador.sair(request.cookies.get(admin.COOKIE))
    resposta = JSONResponse({**ctx.administrador.status(None, ip(request)), "local": acesso.requisicao_local(request)})
    resposta.delete_cookie(admin.COOKIE)
    return resposta


# --------------------------------------------------------------------------- importação de outros sistemas (restrita)


class ConfigImportacao(BaseModel):
    aba: str | None = Field(None, max_length=200)
    linha_cabecalho: int | None = Field(None, ge=0, le=1_000_000)
    mapeamento: dict[str, int | None] | None = None
    centro_custo: str = Field("", max_length=60)
    status: Literal["Pendente", "Pago"] = "Pendente"


class ImportarEntrada(ConfigImportacao):
    indices: list[int] = Field(..., min_length=1, max_length=importacao.MAX_LINHAS)


def _montar_importacao(id_: str, cfg: ConfigImportacao):
    try:
        formato, abas = ctx.importacoes.planilhas(id_)
        nome = ctx.importacoes.nome(id_)
    except KeyError as exc:
        raise erro(404, "importacao_nao_encontrada", "O arquivo desta importação não está mais disponível. Envie-o novamente.") from exc
    except importacao.ErroImportacao as exc:
        raise erro(422, "importacao_invalida", str(exc)) from exc
    tabela = importacao.montar_tabela(abas, cfg.aba, cfg.linha_cabecalho)
    salvo = False
    if cfg.mapeamento is None:
        mapeamento = ctx.modelos_importacao.obter(tabela["colunas"]) if tabela["linha_cabecalho"] else None
        salvo = mapeamento is not None
        mapeamento = mapeamento or importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"])
    else:
        mapeamento = importacao.validar_mapeamento(cfg.mapeamento, len(tabela["colunas"]))
    itens = importacao.preparar(tabela, mapeamento, existentes=ctx.repositorio.listar(),
                                centro_padrao=re.sub(r"\s+", " ", cfg.centro_custo).strip(), status_padrao=cfg.status,
                                nome_arquivo=nome)
    return nome, formato, tabela, mapeamento, salvo, itens


def _resposta_importacao(id_: str, cfg: ConfigImportacao) -> dict:
    nome, formato, tabela, mapeamento, salvo, itens = _montar_importacao(id_, cfg)
    return {
        "id": id_,
        "arquivo": nome,
        "formato": importacao.FORMATOS.get(formato, formato),
        "abas": tabela["abas"],
        "aba": tabela["aba"],
        "linha_cabecalho": tabela["linha_cabecalho"],
        "opcoes_cabecalho": [{"linha": n, "texto": t} for n, t in tabela["opcoes_cabecalho"]],
        "colunas": importacao.descrever_colunas(tabela),
        "campos": importacao.CAMPOS,
        "mapeamento": mapeamento,
        "mapeamento_salvo": salvo,
        "truncado": tabela["truncado"],
        "itens": [importacao.serializar_item(i) for i in itens],
        "resumo": importacao.resumir(itens),
    }


@router.get("/api/importacao/modelo.xlsx", dependencies=SOMENTE_ADMIN)
def modelo_importacao():
    return anexo(importacao.gerar_modelo(), XLSX, "modelo-importacao-boletos.xlsx")


@router.post("/api/importacao", status_code=201, dependencies=SOMENTE_ADMIN)
def enviar_importacao(arquivo: UploadFile = File(...)):
    """Recebe a planilha exportada do outro sistema e devolve colunas sugeridas e a prévia dos boletos."""
    dados = ler_upload(arquivo)
    id_ = ctx.importacoes.salvar(dados, arquivo.filename or "importacao")
    try:
        return _resposta_importacao(id_, ConfigImportacao())
    except HTTPException:
        ctx.importacoes.remover(id_)
        raise


@router.post("/api/importacao/{id_}/previa", dependencies=SOMENTE_ADMIN)
def previa_importacao(id_: str, entrada: ConfigImportacao):
    return _resposta_importacao(id_, entrada)


@router.post("/api/importacao/{id_}/importar", dependencies=SOMENTE_ADMIN)
def importar_boletos(id_: str, entrada: ImportarEntrada, request: Request):
    nome, _, tabela, mapeamento, _, itens = _montar_importacao(id_, entrada)
    escolhidos = set(entrada.indices)
    selecionados = [i for i in itens if i["indice"] in escolhidos and i["estado"] != "erro"]
    if not selecionados:
        raise erro(422, "nada_para_importar", "Nenhum boleto válido foi selecionado para importar.")
    registros, pendente = ctx.repositorio.adicionar_lote([i["dados"] for i in selecionados], usuario=autor(request))
    if tabela["linha_cabecalho"]:
        ctx.modelos_importacao.salvar(tabela["colunas"], mapeamento)
    log.info("%d boleto(s) importado(s) de %s%s", len(registros), nome, " [aguardando gravação]" if pendente else "")
    return {
        "importados": len(registros),
        "ignorados": len(escolhidos) - len(selecionados),
        "pendente_gravacao": pendente,
        "valor_total": round(sum(i["dados"]["valor"] or 0 for i in selecionados), 2),
    }

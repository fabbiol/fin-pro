"""Usuários do escritório: entrar/sair, trocar a própria senha e cadastro (restrito ao administrador)."""

from __future__ import annotations

import asyncio
import logging

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .. import acesso, usuarios
from .. import contexto as ctx
from ..rede import descrever_aparelho
from .comum import SOMENTE_ADMIN, erro, ip

log = logging.getLogger("leitor_boletos")
router = APIRouter()


class EntrarEntrada(BaseModel):
    login: str = Field(..., max_length=80)
    senha: str = Field(..., max_length=200)


class TrocarSenhaEntrada(BaseModel):
    senha_atual: str = Field(..., max_length=200)
    senha: str = Field(..., max_length=200)
    confirmacao: str = Field(..., max_length=200)


class UsuarioNovo(BaseModel):
    nome: str = Field(..., max_length=60)
    login: str = Field("", max_length=40)
    senha: str = Field(..., max_length=200)
    perfil: Literal["administrador", "comum"] = "comum"
    permissoes: list[str] | None = None


class UsuarioEdicao(BaseModel):
    nome: str | None = Field(None, max_length=60)
    ativo: bool | None = None
    senha: str | None = Field(None, max_length=200)
    perfil: Literal["administrador", "comum"] | None = None
    permissoes: list[str] | None = None


class ConfigUsuariosEntrada(BaseModel):
    exigir_login_no_computador: bool | None = None
    pedir_login_ao_abrir: bool | None = None


def _falha(exc: usuarios.ErroUsuario):
    return erro(422, "usuario_invalido", str(exc))


@router.post("/api/usuarios/entrar")
async def entrar(entrada: EntrarEntrada, request: Request):
    token, usuario, bloqueio = await asyncio.to_thread(
        ctx.usuarios.entrar, entrada.login, entrada.senha, ip(request),
        descrever_aparelho(request.headers.get("user-agent")), acesso.requisicao_local(request))
    if not token:
        await asyncio.sleep(0.8)  # atrasa tentativas automáticas
        if bloqueio:
            raise erro(429, "bloqueado", f"Muitas tentativas erradas. Tente de novo em {max(1, round(bloqueio / 60))} minuto(s).")
        log.warning("Login recusado para %r (aparelho %s)", entrada.login[:40], ip(request))
        raise erro(401, "login_incorreto", "Usuário ou senha incorretos.")
    log.info("%s entrou no sistema (aparelho %s)", usuario["nome"], ip(request))
    resposta = JSONResponse({"usuario": usuario})
    resposta.set_cookie(usuarios.COOKIE, token, max_age=usuarios.VALIDADE_SESSAO, httponly=True, samesite="lax")
    return resposta


@router.post("/api/usuarios/sair")
def sair(request: Request):
    ctx.usuarios.sair(request.cookies.get(usuarios.COOKIE))
    resposta = JSONResponse({"ok": True})
    resposta.delete_cookie(usuarios.COOKIE)
    return resposta


@router.get("/api/usuarios/eu")
def quem_sou(request: Request):
    return acesso.estado(request)


@router.post("/api/usuarios/minha-senha")
def trocar_minha_senha(entrada: TrocarSenhaEntrada, request: Request):
    if entrada.senha != entrada.confirmacao:
        raise erro(422, "senhas_diferentes", "As duas senhas novas não são iguais.")
    try:
        ctx.usuarios.trocar_propria_senha(request.cookies.get(usuarios.COOKIE), entrada.senha_atual, entrada.senha)
    except usuarios.ErroUsuario as exc:
        raise _falha(exc) from exc
    return {"ok": True}


# --------------------------------------------------------------------------- cadastro (administrador)


def _lista() -> dict:
    return {"usuarios": ctx.usuarios.listar(), "exigir_login_no_computador": ctx.usuarios.exigir_login_no_computador,
            "pedir_login_ao_abrir": ctx.usuarios.pedir_login_ao_abrir, "em_uso": ctx.usuarios.em_uso,
            "tem_administrador": ctx.usuarios.tem_administrador,
            "permissoes": [{"chave": chave, "rotulo": rotulo} for chave, rotulo in usuarios.PERMISSOES.items()]}


@router.get("/api/usuarios", dependencies=SOMENTE_ADMIN)
def listar_usuarios():
    return _lista()


@router.post("/api/usuarios", status_code=201, dependencies=SOMENTE_ADMIN)
def criar_usuario(entrada: UsuarioNovo):
    try:
        criado = ctx.usuarios.criar(entrada.nome, entrada.login, entrada.senha, entrada.perfil, entrada.permissoes)
    except usuarios.ErroUsuario as exc:
        raise _falha(exc) from exc
    log.info("Usuário %s (%s) cadastrado como %s", criado["nome"], criado["login"], criado["perfil"])
    return {**_lista(), "criado": criado}


@router.put("/api/usuarios/config", dependencies=SOMENTE_ADMIN)
def configurar_usuarios(entrada: ConfigUsuariosEntrada):
    if entrada.exigir_login_no_computador is not None:
        ctx.usuarios.definir_exigir_login_no_computador(entrada.exigir_login_no_computador)
    if entrada.pedir_login_ao_abrir is not None:
        ctx.usuarios.definir_pedir_login_ao_abrir(entrada.pedir_login_ao_abrir)
    return _lista()


@router.put("/api/usuarios/{id_}", dependencies=SOMENTE_ADMIN)
def alterar_usuario(id_: str, entrada: UsuarioEdicao):
    try:
        ctx.usuarios.alterar(id_, nome=entrada.nome, ativo=entrada.ativo, senha=entrada.senha or None,
                             perfil=entrada.perfil, permissoes=entrada.permissoes)
    except usuarios.ErroUsuario as exc:
        raise _falha(exc) from exc
    return _lista()


@router.delete("/api/usuarios/{id_}", status_code=204, dependencies=SOMENTE_ADMIN)
def excluir_usuario(id_: str):
    try:
        ctx.usuarios.excluir(id_)
    except usuarios.ErroUsuario as exc:
        raise _falha(exc) from exc
    return Response(status_code=204)

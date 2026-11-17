"""Funções usadas por várias rotas: erros padronizados, restrições de acesso e downloads."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response

from .. import acesso, admin, cost_center
from .. import contexto as ctx

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def erro(status: int, codigo: str, mensagem: str, **extra) -> HTTPException:
    return HTTPException(status_code=status, detail={"codigo": codigo, "mensagem": mensagem, **extra})


def somente_local(request: Request, precisa_startfile: bool = True) -> None:
    if not acesso.requisicao_local(request):
        raise erro(403, "somente_local", "Disponível apenas no computador onde o sistema está rodando.")
    if precisa_startfile and not hasattr(os, "startfile"):
        raise erro(501, "nao_suportado", "Disponível apenas no Windows.")


def anexo(conteudo: bytes, tipo: str, nome: str) -> Response:
    return Response(conteudo, media_type=tipo, headers={"Content-Disposition": f'attachment; filename="{nome}"'})


def ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def autor(request: Request) -> str:
    """Quem está fazendo a alteração: o usuário que entrou, ou "Computador principal" (usado no Histórico)."""
    return getattr(request.state, "usuario_nome", "") or ""


def concluir_caixa_de_entrada(arquivo_ids) -> None:
    """Boletos e Pix que chegaram por e-mail ou Telegram saem da caixa de entrada quando são lançados."""
    from .. import contexto

    if contexto.caixa_entrada is not None:
        contexto.caixa_entrada.marcar_lancados({i for i in arquivo_ids if i})


def limpar_centro(dados: dict, atual: dict | None = None) -> None:
    """Arruma o centro de custo que vai ser gravado. Com o valor dividido entre vários centros, a soma tem de dar o
    valor do lançamento (``atual``: o registro que está sendo editado, para conferir quando só um dos dois muda)."""
    texto = dados["centro_custo"] if "centro_custo" in dados else (atual or {}).get("centro_custo")
    if "centro_custo" not in dados and len(cost_center.split_parts(texto)) < 2:
        return
    try:
        limpo = cost_center.validate(texto, dados["valor"] if "valor" in dados else (atual or {}).get("valor"))
    except ValueError as exc:
        raise erro(422, "centro_invalido", str(exc)) from exc
    if "centro_custo" in dados:
        dados["centro_custo"] = limpo


def exigir_admin(request: Request) -> None:
    """Funções restritas: usuário com perfil de administrador, ou a sessão aberta com a senha de administrador."""
    if acesso.eh_administrador(request):
        return
    if getattr(request.state, "usuario", None):
        raise erro(403, "sem_permissao", "Só o administrador pode fazer isso. Peça ao administrador do Fin Pro.")
    if not ctx.administrador.senha_definida:
        raise erro(403, "admin_sem_senha", "Função restrita: crie a senha de administrador em Configurações.")
    if not ctx.administrador.autorizado(request.cookies.get(admin.COOKIE)):
        raise erro(403, "admin_necessario", "Área restrita: digite a senha de administrador em Configurações.")


SOMENTE_ADMIN = [Depends(exigir_admin)]

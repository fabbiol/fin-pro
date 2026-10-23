"""API das transferências de clientes: a entrada da integração com a Operações (só com o token) e a tela."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.datastructures import UploadFile

from .. import config
from .. import contexto as ctx
from ..arquivos import RepositorioArquivos
from ..planilha import RegistroNaoEncontrado
from ..transferencias import servico
from .comum import erro

log = logging.getLogger(__name__)
router = APIRouter(tags=["transferencias"])


def _falha(status: int, mensagem: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"ok": False, "erro": mensagem}, **extra)


@router.post("/api/integracao/operacoes/notas")
async def receber_nota_da_operacoes(request: Request):
    """A Operações manda a nota paga por Pix ou TED/DOC. Sem login: vale só o token (``OPERACOES_TOKEN``).

    O token é conferido antes de ler o corpo, e nunca vai para o log.
    """
    esperado = config.operacoes_token()
    if not esperado:
        return _falha(503, "Integração com a Operações desligada: falta OPERACOES_TOKEN no Fin Pro.")
    tipo, _, recebido = request.headers.get("authorization", "").partition(" ")
    if tipo.lower() != "bearer" or not hmac.compare_digest(recebido.strip().encode(), esperado.encode()):
        return _falha(401, "Token inválido.", headers={"WWW-Authenticate": "Bearer"})
    try:
        async with request.form(max_files=1, max_fields=30) as formulario:
            dados = servico.validar(formulario)
            arquivo = formulario.get("arquivo")
            pdf, nome = None, ""
            if isinstance(arquivo, UploadFile):
                pdf, nome = await arquivo.read(servico.MAX_PDF + 1), arquivo.filename or ""
                servico.validar_pdf(pdf)
            elif arquivo:
                raise servico.ErroTransferencia("O arquivo deve ser um PDF.")
    except servico.ErroTransferencia as exc:
        return _falha(422, str(exc))
    except Exception:  # corpo que não é um formulário válido
        return _falha(422, "Envie os dados como multipart/form-data.")
    registro, criada = servico.receber(dados, pdf, nome)
    log.info("Nota %s (ordem %s da Operações) %s", registro["nota"], registro["origem_id"], "criada" if criada else "atualizada")
    return JSONResponse(status_code=201 if criada else 200,
                        content={"ok": True, "id": registro["id"], "situacao": "criada" if criada else "atualizada"})


@router.get("/api/transferencias")
def listar(empresa: str = "", situacao: str = "", q: str = ""):
    return servico.listar(empresa, situacao, q)


@router.get("/api/transferencias/{id_}/pdf")
def abrir_pdf(id_: int):
    try:
        registro = ctx.transferencias.obter(id_)
    except RegistroNaoEncontrado:
        raise erro(404, "nao_encontrado", "Transferência não encontrada.") from None
    caminho = ctx.arquivos.caminho_original(RepositorioArquivos.id_de_caminho(registro.get("arquivo")) or "")
    if caminho is None:
        raise erro(404, "arquivo_nao_encontrado", "Esta nota chegou sem o PDF.")
    return FileResponse(caminho, media_type="application/pdf", filename=registro.get("arquivo_nome") or f"NF {registro['nota']}.pdf",
                        content_disposition_type="inline")

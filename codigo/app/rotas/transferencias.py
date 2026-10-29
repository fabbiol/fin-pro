"""API das transferências de clientes: a entrada da integração com a Operações (só com o token), a tela, o ligar
pagamento (comprovante Pix/TED ligado a uma ou mais notas) e a conciliação com os Pix recebidos no Bradesco."""

from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, File, Request
from fastapi import UploadFile as Upload
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile

from .. import config
from .. import contexto as ctx
from ..arquivos import RepositorioArquivos
from ..planilha import RegistroNaoEncontrado
from ..transferencias import servico
from .comprovantes import _validar as validar_comprovante
from .comum import autor, erro
from .leitura import ler_upload, visualizar_arquivo

log = logging.getLogger(__name__)
router = APIRouter(tags=["transferencias"])


class LigarEntrada(BaseModel):
    """O que o dono conferiu na tela (valor e data podem ter sido corrigidos à mão)."""
    ids: list[int] = Field(..., min_length=1, max_length=500)
    arquivo: str = Field(..., max_length=40)
    valor: float | str | None = None
    data: str | None = Field(None, max_length=10)
    pagador: str | None = Field(None, max_length=200)
    documento_pagador: str | None = Field(None, max_length=30)
    id_transacao: str | None = Field(None, max_length=120)
    observacao: str | None = Field(None, max_length=500)


class ConsultaEntrada(BaseModel):
    """Período da consulta ao Bradesco (datas AAAA-MM-DD)."""
    inicio: str = Field(..., max_length=10)
    fim: str = Field(..., max_length=10)


class LigarPixEntrada(BaseModel):
    """Notas e Pix (endToEndId) que o dono confirmou. Valor, data e pagador vêm da consulta ao banco."""
    ids: list[int] = Field(..., min_length=1, max_length=500)
    pix: list[Annotated[str, Field(max_length=40)]] = Field(..., min_length=1, max_length=20)
    observacao: str | None = Field(None, max_length=500)


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


@router.delete("/api/transferencias/{id_}", status_code=204)
def excluir_nota(id_: int, request: Request):
    """Exclui a nota que aguarda pagamento (ex.: mandada por engano). Nota paga não sai: desfaça o pagamento antes."""
    try:
        nota = servico.excluir(id_, autor(request))
    except servico.ErroPagamento as exc:
        raise erro(exc.status, exc.codigo, str(exc)) from None
    log.info("Nota %s (ordem %s da Operações) excluída (%s)", nota["nota"], nota["origem_id"], autor(request))
    return Response(status_code=204)


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


@router.post("/api/transferencias/{id_}/cartao")
def anexar_cartao(id_: int, request: Request, arquivo: Upload = File(...)):
    """Foto do comprovante da parte paga no cartão (opcional, só para consulta: não muda a situação da nota)."""
    dados = ler_upload(arquivo)
    validar_comprovante(dados)
    try:
        registro = servico.anexar_cartao(id_, dados, arquivo.filename or "", autor(request))
    except RegistroNaoEncontrado:
        raise erro(404, "nao_encontrado", "Transferência não encontrada.") from None
    log.info("Comprovante do cartão anexado à nota %s (%s)", registro["nota"], autor(request))
    return registro


@router.get("/api/transferencias/{id_}/cartao")
def abrir_cartao(id_: int):
    try:
        registro = ctx.transferencias.obter(id_)
    except RegistroNaoEncontrado:
        raise erro(404, "nao_encontrado", "Transferência não encontrada.") from None
    arquivo_id = RepositorioArquivos.id_de_caminho(registro.get("comprovante_cartao"))
    if not arquivo_id:
        raise erro(404, "sem_comprovante", "Esta nota ainda não tem o comprovante do cartão.")
    return visualizar_arquivo(arquivo_id)


# --------------------------------------------------------------------------- ligar o pagamento à nota


@router.post("/api/transferencias/pagamentos/ler")
def ler_comprovante(arquivo: Upload = File(...)):
    """Guarda o comprovante e devolve o que foi lido, para o dono conferir. Ainda não liga nada."""
    dados = ler_upload(arquivo)
    validar_comprovante(dados)
    meta = ctx.arquivos.salvar(dados, arquivo.filename or "comprovante")
    lido = servico.ler_comprovante(dados)
    repetido = servico.pagamento_com_id(lido["id_transacao"] or "")
    return {**lido, "arquivo": meta["id"], "arquivo_nome": meta["nome"], "ja_usado": repetido["id"] if repetido else None}


def _pagamento(funcao, *args):
    try:
        pagamento, notas = funcao(*args)
    except servico.ErroPagamento as exc:
        raise erro(exc.status, exc.codigo, str(exc)) from None
    return {"pagamento": pagamento, "transferencias": notas}


@router.post("/api/transferencias/pagamentos", status_code=201)
def ligar_pagamento(entrada: LigarEntrada, request: Request):
    resposta = _pagamento(servico.ligar, entrada.ids, entrada.arquivo, entrada.model_dump(), autor(request))
    log.info("Pagamento %s ligado às notas %s (%s)", resposta["pagamento"]["id"], resposta["pagamento"]["notas"], autor(request))
    return resposta


@router.get("/api/transferencias/pagamentos/{id_}/comprovante")
def abrir_comprovante(id_: int):
    arquivo_id = servico.comprovante_do_pagamento(id_)
    if not arquivo_id:
        raise erro(404, "sem_comprovante", "Comprovante não encontrado.")
    return visualizar_arquivo(arquivo_id)


@router.post("/api/transferencias/pagamentos/{id_}/desfazer")
def desfazer_pagamento(id_: int, request: Request):
    """As notas voltam a Aguardando pagamento; o pagamento fica guardado como desfeito (com o comprovante)."""
    resposta = _pagamento(servico.desfazer, id_, autor(request))
    log.info("Pagamento %s desfeito (%s)", id_, autor(request))
    return resposta


# --------------------------------------------------------------------------- Pix recebidos no Bradesco (API Pix)


@router.get("/api/transferencias/bradesco")
def situacao_bradesco():
    """Se a consulta está ligada (ou por que não está), o período padrão e a última consulta já conciliada."""
    return servico.situacao_bradesco()


@router.post("/api/transferencias/bradesco/consultar")
def consultar_bradesco(entrada: ConsultaEntrada, request: Request):
    """Busca os Pix recebidos no Bradesco e sugere as notas. Não liga nada: cada sugestão é confirmada na tela."""
    try:
        resposta = servico.consultar_bradesco(entrada.inicio, entrada.fim)
    except servico.ErroPagamento as exc:
        log.warning("Consulta dos Pix no Bradesco não deu certo (%s): %s", exc.codigo, exc)
        raise erro(exc.status, exc.codigo, str(exc)) from None
    log.info("Pix do Bradesco consultados de %s a %s: %s Pix (%s)", entrada.inicio, entrada.fim,
             resposta["consulta"]["total"], autor(request))
    return resposta


@router.post("/api/transferencias/pagamentos/pix", status_code=201)
def ligar_pix(entrada: LigarPixEntrada, request: Request):
    resposta = _pagamento(servico.ligar_pix, entrada.ids, entrada.pix, entrada.observacao or "", autor(request))
    log.info("Pix %s ligados às notas %s no pagamento %s (%s)", resposta["pagamento"]["id_transacao"],
             resposta["pagamento"]["notas"], resposta["pagamento"]["id"], autor(request))
    return resposta

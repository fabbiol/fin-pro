"""Pagamentos Pix: lançamento por chave, Copia e Cola ou QR code, pagamento, QR code e exportação."""

from __future__ import annotations

import io
import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import config, servicos
from ..arquivos import RepositorioArquivos
from .. import contexto as ctx
from ..pix import ErroPix, gerar_copia_e_cola, ler_copia_e_cola, ler_pix_de_arquivo, normalizar_chave
from ..planilha import COLUNAS_PIX
from ..servico_leitura import com_duplicado, pix_existente
from .boletos import CampoData, Status, StatusEntrada, dados_do_status, pagina_de, situacoes
from .comum import XLSX, anexo, autor, concluir_caixa_de_entrada, erro, limpar_centro
from .leitura import ler_upload, visualizar_arquivo

log = logging.getLogger("leitor_boletos")
router = APIRouter()

CampoOrdemPix = Literal["id", "data_lancamento", "vencimento", "valor", "recebedor", "tipo_chave", "status",
                        "data_pagamento", "centro_custo"]


class PixBase(BaseModel):
    recebedor: str | None = Field(None, max_length=250)
    tipo_chave: Literal["cpf_cnpj", "celular", "email", "aleatoria"] | None = None
    chave: str | None = Field(None, max_length=120)
    valor: float | None = Field(None, ge=0, le=1e11)
    vencimento: date | None = None
    centro_custo: str | None = Field(None, max_length=60)
    descricao: str | None = Field(None, max_length=500)
    status: Status | None = None
    data_pagamento: date | None = None
    txid: str | None = Field(None, max_length=40)
    copia_e_cola: str | None = Field(None, max_length=1500)
    observacoes: str | None = Field(None, max_length=1000)
    valor_pago: float | None = Field(None, ge=0, le=1e11)
    juros_multa: float | None = Field(None, ge=0, le=1e11)
    desconto: float | None = Field(None, ge=0, le=1e11)


class PixNovo(PixBase):
    arquivo_id: str | None = None
    permitir_duplicado: bool = False


class PixCodigoEntrada(BaseModel):
    texto: str = Field(..., max_length=1500)


def preparar_pix(entrada: PixBase, existente: dict | None = None) -> dict:
    """Valida chave, Copia e Cola e valor de um Pix (novo ou editado) e devolve os dados a gravar."""
    novo = existente is None
    dados = entrada.model_dump(exclude={"arquivo_id", "permitir_duplicado"}, exclude_none=novo, exclude_unset=not novo)

    copia = (dados.get("copia_e_cola") or "").strip()
    lido = None
    if copia:
        try:
            lido = ler_copia_e_cola(copia)
        except ErroPix as exc:
            raise erro(422, "copia_e_cola_invalido", str(exc)) from exc
        if not lido["crc_valido"]:
            raise erro(422, "copia_e_cola_invalido",
                       "O Pix Copia e Cola está incompleto ou foi alterado (o código de verificação não confere).")
        dados["copia_e_cola"] = lido["copia_e_cola"]
        for campo in ("tipo_chave", "chave", "recebedor", "txid", "descricao"):
            if not dados.get(campo) and lido.get(campo):
                dados[campo] = lido[campo]
        if not dados.get("valor") and lido.get("valor"):
            dados["valor"] = lido["valor"]
    elif "copia_e_cola" in dados:
        dados["copia_e_cola"] = ""

    if novo or "tipo_chave" in dados or "chave" in dados:
        tipo = dados.get("tipo_chave") if "tipo_chave" in dados else (existente or {}).get("tipo_chave")
        chave = (dados.get("chave") if "chave" in dados else (existente or {}).get("chave")) or ""
        copia_atual = dados.get("copia_e_cola") if "copia_e_cola" in dados else (existente or {}).get("copia_e_cola")
        if not chave.strip() or not tipo:
            if not copia_atual:  # Pix dinâmico (QR de cobrança) pode não trazer a chave
                raise erro(422, "chave_obrigatoria", "Informe o tipo da chave e a chave Pix.")
        else:
            try:
                dados["chave"] = normalizar_chave(tipo, chave)
                dados["tipo_chave"] = tipo
            except ErroPix as exc:
                if not copia_atual:
                    raise erro(422, "chave_invalida", str(exc)) from exc

    if novo and not dados.get("valor"):
        raise erro(422, "valor_obrigatorio", "Informe o valor do Pix.")
    if dados.get("status") == "Pago" and not dados.get("data_pagamento"):
        dados["data_pagamento"] = date.today()
    if not novo and dados.get("status") in ("Pendente", "Cancelado"):
        dados.update(data_pagamento=None, valor_pago=None, juros_multa=None, desconto=None)
    if not novo:
        for campo in ("recebedor", "descricao", "observacoes", "centro_custo", "txid", "chave"):
            if campo in dados and dados[campo] is None:
                dados[campo] = ""
    for campo in ("recebedor", "descricao", "observacoes", "txid"):
        if isinstance(dados.get(campo), str):
            dados[campo] = dados[campo].strip()
    limpar_centro(dados)
    return dados


def filtrados_pix(q: str, situacao: str, campo_data: str, de: date | None, ate: date | None, ordenar: str, direcao: str,
                  centro: str = ""):
    registros = servicos.filtrar(ctx.repositorio_pix.listar(), q=q, situacoes=situacoes(situacao), campo_data=campo_data,
                                 de=de, ate=ate, centro=centro, campos_busca=servicos.CAMPOS_BUSCA_PIX,
                                 campos_digitos=servicos.CAMPOS_DIGITOS_PIX)
    return servicos.ordenar(registros, ordenar, direcao)


@router.get("/api/pix")
def listar_pix(
    q: str = "",
    situacao: str = "",
    campo_data: CampoData = "vencimento",
    de: date | None = None,
    ate: date | None = None,
    centro: str = "",
    ordenar: CampoOrdemPix = "vencimento",
    direcao: Literal["asc", "desc"] = "asc",
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=0, le=1000),
):
    registros = filtrados_pix(q, situacao, campo_data, de, ate, ordenar, direcao, centro)
    return pagina_de(registros, pagina, por_pagina, servicos.serializar_pix)


@router.get("/api/pix/exportar")
def exportar_pix(
    formato: Literal["csv", "xlsx"] = "xlsx",
    q: str = "",
    situacao: str = "",
    campo_data: CampoData = "vencimento",
    de: date | None = None,
    ate: date | None = None,
    centro: str = "",
    ordenar: CampoOrdemPix = "vencimento",
    direcao: Literal["asc", "desc"] = "asc",
):
    registros = filtrados_pix(q, situacao, campo_data, de, ate, ordenar, direcao, centro)
    nome = f"pix-{date.today():%Y-%m-%d}"
    if formato == "csv":
        return anexo(servicos.gerar_csv(registros, colunas=COLUNAS_PIX), "text/csv; charset=utf-8", f"{nome}.csv")
    return anexo(servicos.gerar_xlsx(registros, colunas=COLUNAS_PIX, titulo_aba="Pix"), XLSX, f"{nome}.xlsx")


@router.post("/api/pix/ler-codigo")
def ler_codigo_pix(entrada: PixCodigoEntrada):
    try:
        return com_duplicado(ler_copia_e_cola(entrada.texto))
    except ErroPix as exc:
        raise erro(422, "copia_e_cola_invalido", str(exc)) from exc


@router.post("/api/pix/ler-arquivo")
def ler_arquivo_pix(arquivo: UploadFile = File(...)):
    """Procura QR codes Pix numa foto, print ou PDF."""
    dados = ler_upload(arquivo)
    try:
        encontrados = ler_pix_de_arquivo(dados, max_paginas=config.MAX_PAGINAS_PDF)
    except Exception as exc:
        log.exception("Falha ao ler QR code Pix")
        raise erro(422, "leitura_falhou", "Não foi possível ler este arquivo. Envie um PDF ou uma imagem.") from exc
    meta = ctx.arquivos.salvar(dados, arquivo.filename or "pix") if encontrados else None
    return {"pix": [com_duplicado(p) for p in encontrados], "arquivo": meta}


@router.post("/api/pix", status_code=201)
def lancar_pix(entrada: PixNovo, request: Request):
    dados = preparar_pix(entrada)
    if not entrada.permitir_duplicado:
        existente = pix_existente(dados)
        if existente:
            referencia = f"ID {existente['id']}" if existente["id"] > 0 else "aguardando gravação"
            raise erro(409, "duplicado", f"Este Pix já foi lançado ({referencia}).", registro=servicos.serializar_pix(existente))
    if entrada.arquivo_id:
        meta = ctx.arquivos.meta(entrada.arquivo_id)
        if meta:
            dados["arquivo"] = ctx.arquivos.caminho_relativo(entrada.arquivo_id)
            dados["arquivo_nome"] = meta["nome"]
    registro, pendente = ctx.repositorio_pix.adicionar(dados, usuario=autor(request))
    concluir_caixa_de_entrada([entrada.arquivo_id])
    log.info("Pix %s lançado%s (%s)", registro["id"], " [aguardando gravação]" if pendente else "", registro.get("recebedor"))
    return servicos.serializar_pix(registro)


@router.get("/api/pix/{id_}")
def obter_pix(id_: int):
    return servicos.serializar_pix(ctx.repositorio_pix.obter(id_))


@router.put("/api/pix/{id_}")
def editar_pix(id_: int, entrada: PixBase, request: Request):
    existente = ctx.repositorio_pix.obter(id_)
    registro, _ = ctx.repositorio_pix.atualizar(id_, preparar_pix(entrada, existente), usuario=autor(request))
    return servicos.serializar_pix(registro)


@router.patch("/api/pix/{id_}/status")
def alterar_status_pix(id_: int, entrada: StatusEntrada, request: Request):
    registro, _ = ctx.repositorio_pix.atualizar(id_, dados_do_status(entrada), usuario=autor(request))
    return servicos.serializar_pix(registro)


@router.delete("/api/pix/{id_}", status_code=204)
def excluir_pix(id_: int, request: Request):
    ctx.repositorio_pix.excluir(id_, usuario=autor(request))
    return Response(status_code=204)


@router.get("/api/pix/{id_}/arquivo")
def arquivo_do_pix(id_: int):
    registro = ctx.repositorio_pix.obter(id_)
    arquivo_id = RepositorioArquivos.id_de_caminho(registro.get("arquivo"))
    return visualizar_arquivo(arquivo_id or "")


@router.get("/api/pix/{id_}/historico")
def historico_do_pix(id_: int):
    registro = ctx.repositorio_pix.obter(id_)
    return {"eventos": ctx.planilha.historico_do_registro(id_, "pix", registro.get("data_lancamento")) if id_ > 0 else []}


def _copia_e_cola_do_registro(registro: dict) -> tuple[str, bool]:
    if registro.get("copia_e_cola"):
        return registro["copia_e_cola"], False
    try:
        return gerar_copia_e_cola(registro.get("tipo_chave"), registro.get("chave"), registro.get("valor"),
                                  registro.get("recebedor") or "", txid=registro.get("txid") or "",
                                  descricao=registro.get("descricao") or ""), True
    except ErroPix as exc:
        raise erro(422, "chave_invalida", f"Não foi possível gerar o Pix Copia e Cola: {exc}") from exc


@router.get("/api/pix/{id_}/copia-e-cola")
def copia_e_cola_pix(id_: int):
    codigo, gerado = _copia_e_cola_do_registro(ctx.repositorio_pix.obter(id_))
    return {"copia_e_cola": codigo, "gerado": gerado}


@router.get("/api/pix/{id_}/qrcode.svg")
def qrcode_pix(id_: int):
    import segno

    codigo, _ = _copia_e_cola_do_registro(ctx.repositorio_pix.obter(id_))
    buffer = io.BytesIO()
    segno.make(codigo, error="m").save(buffer, kind="svg", scale=6, border=2, dark="#0b1b1f", light="#ffffff", xmldecl=False)
    return Response(buffer.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})

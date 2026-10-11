"""API do módulo Empresas: cadastro, notas fiscais, cheques, recebimentos, fechamento e bot de notas."""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, File, Query, Request, UploadFile
from pydantic import BaseModel, Field

from .. import config
from .. import contexto as ctx
from ..empresas import leitura, relatorio, servico
from ..empresas.modelos import FORMAS_RECEBIMENTO, STATUS_CHEQUE, STATUS_NOTA
from .comum import XLSX, anexo, autor, erro

log = logging.getLogger("leitor_boletos.empresas")
router = APIRouter(prefix="/api", tags=["empresas"])
PDF = "application/pdf"


def _erro_regra(exc: Exception):
    return erro(422, "regra_empresas", str(exc))


class EmpresaEntrada(BaseModel):
    nome: str | None = Field(None, max_length=80)
    razao_social: str | None = Field(None, max_length=120)
    cnpj: str | None = Field(None, max_length=20)
    apelidos: str | None = Field(None, max_length=200)
    dia_fechamento: int | None = Field(None, ge=1, le=28)
    contato: str | None = Field(None, max_length=80)
    telefone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=120)
    chat_telegram: str | None = Field(None, max_length=20)
    status: Literal["Ativa", "Inativa"] | None = None
    observacoes: str | None = Field(None, max_length=500)


class ItemNota(BaseModel):
    data: date | None = None
    material: str | None = Field(None, max_length=80)
    unidade: str | None = Field(None, max_length=10)
    quantidade: float | None = Field(None, ge=0, le=1e9)
    valor_unitario: float | None = Field(None, ge=0, le=1e9)
    valor_total: float | None = Field(None, ge=0, le=1e11)
    numero_nf: str | None = Field(None, max_length=15)
    pedido: str | None = Field(None, max_length=15)
    observacoes: str | None = Field(None, max_length=200)


class NotasNovas(BaseModel):
    empresa: str = Field(..., max_length=80)
    competencia: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    itens: list[ItemNota] = Field(..., min_length=1, max_length=200)


class NotaEdicao(ItemNota):
    empresa: str | None = Field(None, max_length=80)
    competencia: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    status: str | None = None
    valor_recebido: float | None = Field(None, ge=0, le=1e11)
    data_recebimento: date | None = None
    todas_da_nota: bool = False  # aplicar a mudança de fechamento a todas as linhas da mesma NF


class ChequeEntrada(BaseModel):
    empresa: str | None = Field(None, max_length=80)
    numero: str | None = Field(None, max_length=20)
    vencimento: date | None = None
    valor: float | None = Field(None, ge=0, le=1e11)
    banco: str | None = Field(None, max_length=60)
    agencia: str | None = Field(None, max_length=12)
    coop: str | None = Field(None, max_length=12)
    conta: str | None = Field(None, max_length=20)
    emitente: str | None = Field(None, max_length=80)
    pedidos: str | None = Field(None, max_length=200)
    notas: str | None = Field(None, max_length=200)
    status: str | None = None
    data_deposito: date | None = None
    cmc7: str | None = Field(None, max_length=40)
    observacoes: str | None = Field(None, max_length=300)


class RecebimentoEntrada(BaseModel):
    empresa: str | None = Field(None, max_length=80)
    forma: str | None = None
    valor: float = Field(..., gt=0, le=1e11)
    data: date | None = None
    hora: str | None = Field(None, max_length=5)
    pagador: str | None = Field(None, max_length=120)
    id_transacao: str | None = Field(None, max_length=120)
    notas: str | None = Field(None, max_length=300)
    pedidos: str | None = Field(None, max_length=300)
    cheque_id: int | None = None
    observacoes: str | None = Field(None, max_length=300)
    arquivo_id: str | None = None


class ConfirmacaoEntrada(BaseModel):
    tipo: Literal["nota", "cheque", "comprovante"]
    dados: dict


class ImportacaoFechamento(BaseModel):
    empresa: str = Field(..., max_length=80)
    competencia: str | None = Field(None, pattern=r"^\d{4}-\d{2}$")
    linhas: list[ItemNota] = Field(..., min_length=1, max_length=400)


class ConfigEntrada(BaseModel):
    minha_empresa: dict | None = None
    dia_fechamento: int | None = Field(None, ge=1, le=28)
    fechamento_automatico: bool | None = None
    hora_envio: str | None = Field(None, max_length=5)
    bot: dict | None = None


def _arquivo_do_id(arquivo_id: str | None) -> dict | None:
    if not arquivo_id:
        return None
    meta = ctx.arquivos.meta(arquivo_id)
    if not meta:
        return None
    return {"caminho": ctx.arquivos.caminho_relativo(arquivo_id) or "", "nome": meta["nome"]}


# --------------------------------------------------------------------------- empresas


@router.get("/empresas")
def listar_empresas(competencia: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    return {"empresas": servico.resumo_empresas(competencia=competencia or ""),
            "cadastro": servico.empresas(),
            "config": ctx.empresas_config.publica()}


@router.post("/empresas", status_code=201)
def criar_empresa(entrada: EmpresaEntrada, request: Request):
    try:
        return servico.salvar_empresa(entrada.model_dump(exclude_none=True), autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.put("/empresas/{id_}")
def editar_empresa(id_: int, entrada: EmpresaEntrada, request: Request):
    try:
        return servico.salvar_empresa(entrada.model_dump(exclude_unset=True), autor(request), id_)
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.delete("/empresas/{id_}", status_code=204)
def excluir_empresa(id_: int, request: Request):
    try:
        servico.excluir_empresa(id_, autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


# --------------------------------------------------------------------------- fechamento


@router.get("/empresas/{id_}/fechamento")
def obter_fechamento(id_: int, competencia: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    empresa = servico.obter_empresa(id_)
    try:
        return servico.fechamento(empresa["nome"], competencia or "")
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.get("/empresas/{id_}/fechamento/arquivo")
def baixar_fechamento(id_: int, formato: Literal["xlsx", "pdf"] = "xlsx",
                      competencia: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    empresa = servico.obter_empresa(id_)
    f = servico.fechamento(empresa["nome"], competencia or "")
    minha = ctx.empresas_config.minha_empresa
    if formato == "pdf":
        return anexo(relatorio.gerar_pdf(f, minha), PDF, relatorio.nome_do_arquivo(f, "pdf"))
    return anexo(relatorio.gerar_xlsx(f, minha), XLSX, relatorio.nome_do_arquivo(f, "xlsx"))


@router.post("/empresas/fechamento/enviar")
def enviar_fechamentos(request: Request):
    """Manda agora, pelo bot de notas, o fechamento de todas as empresas (o envio automático é no dia 20)."""
    resultado = ctx.empresas_entrada.enviar_fechamentos(forcar=True)
    log.info("Fechamentos enviados manualmente por %s: %s", autor(request) or "computador principal", resultado)
    return resultado


# --------------------------------------------------------------------------- notas fiscais


@router.get("/notas")
def listar_notas(empresa: str = "", competencia: str = "", status: str = "", limite: int = Query(500, ge=1, le=2000)):
    notas = ctx.empresas.listar("notas")
    if empresa:
        notas = [n for n in notas if servico.normalizar(n.get("empresa")) == servico.normalizar(empresa)]
    if competencia:
        notas = [n for n in notas if n.get("competencia") == competencia]
    if status:
        notas = [n for n in notas if n.get("status") == status]
    notas.sort(key=lambda n: (str(n.get("data") or ""), n["id"]), reverse=True)
    return {"notas": notas[:limite], "total": len(notas)}


@router.post("/notas", status_code=201)
def lancar_notas(entrada: NotasNovas, request: Request):
    try:
        criadas = servico.lancar_notas(entrada.empresa, [i.model_dump() for i in entrada.itens], autor(request),
                                       competencia=entrada.competencia or "")
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc
    return {"notas": criadas}


@router.put("/notas/{id_}")
def editar_nota(id_: int, entrada: NotaEdicao, request: Request):
    dados = entrada.model_dump(exclude_unset=True)
    todas_da_nota = bool(dados.pop("todas_da_nota", False))
    if dados.get("status") and dados["status"] not in STATUS_NOTA:
        raise erro(422, "status_invalido", "Situação inválida para a nota fiscal.")
    try:
        nota = servico.atualizar_nota(id_, dados, autor(request))
        movidas = (servico.mover_nota_fiscal(nota["empresa"], nota["numero_nf"], dados["competencia"], autor(request))
                   if todas_da_nota and dados.get("competencia") else [])
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc
    return {**nota, "linhas_movidas": len(movidas) + (1 if dados.get("competencia") else 0)}


@router.delete("/notas/{id_}", status_code=204)
def excluir_nota(id_: int, request: Request):
    servico.excluir_nota(id_, autor(request))


# --------------------------------------------------------------------------- cheques


@router.get("/cheques")
def listar_cheques(empresa: str = "", status: str = ""):
    return {"cheques": servico.cheques(empresa, status)}


@router.post("/cheques", status_code=201)
def lancar_cheque(entrada: ChequeEntrada, request: Request):
    dados = entrada.model_dump(exclude_none=True)
    if dados.get("status") and dados["status"] not in STATUS_CHEQUE:
        raise erro(422, "status_invalido", "Situação inválida para o cheque.")
    try:
        return servico.lancar_cheque(dados, autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.put("/cheques/{id_}")
def editar_cheque(id_: int, entrada: ChequeEntrada, request: Request):
    try:
        return servico.atualizar_cheque(id_, entrada.model_dump(exclude_unset=True), autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.delete("/cheques/{id_}", status_code=204)
def excluir_cheque(id_: int, request: Request):
    servico.excluir_cheque(id_, autor(request))


# --------------------------------------------------------------------------- recebimentos


@router.get("/recebimentos")
def listar_recebimentos(empresa: str = "", limite: int = Query(300, ge=1, le=2000)):
    lista = ctx.empresas.listar("recebimentos")
    if empresa:
        lista = [r for r in lista if servico.normalizar(r.get("empresa")) == servico.normalizar(empresa)]
    lista.sort(key=lambda r: (str(r.get("data") or ""), r["id"]), reverse=True)
    return {"recebimentos": lista[:limite], "total": len(lista)}


@router.post("/recebimentos", status_code=201)
def registrar_recebimento(entrada: RecebimentoEntrada, request: Request):
    dados = entrada.model_dump(exclude_none=True)
    if dados.get("forma") and dados["forma"] not in FORMAS_RECEBIMENTO:
        raise erro(422, "forma_invalida", "Forma de recebimento inválida.")
    try:
        if entrada.cheque_id:  # comprovante do depósito de um cheque em carteira: compensa o cheque e baixa as notas
            cheque = servico.banco().obter(entrada.cheque_id, "cheques")
            return servico.compensar_cheque(cheque, autor(request), entrada.data, _arquivo_do_id(entrada.arquivo_id))
        return servico.registrar_recebimento(dados, autor(request), _arquivo_do_id(entrada.arquivo_id))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.post("/recebimentos/{id_}/cancelar")
def cancelar_recebimento(id_: int, request: Request):
    try:
        return servico.cancelar_recebimento(id_, autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


# --------------------------------------------------------------------------- caixa de entrada do bot de notas


@router.get("/empresas/entrada")
def listar_entrada(incluir_concluidos: bool = False):
    return {"itens": ctx.empresas_entrada.listar(incluir_concluidos),
            "pendentes": ctx.empresas_entrada.contagem(),
            "bot": ctx.empresas_config.publica()["bot"]}


@router.post("/empresas/entrada/verificar")
def verificar_entrada():
    try:
        return ctx.empresas_entrada.verificar_agora()
    except ValueError as exc:
        raise erro(422, "bot_notas", str(exc)) from exc


@router.post("/empresas/entrada/{id_}/confirmar")
def confirmar_entrada(id_: str, entrada: ConfirmacaoEntrada, request: Request):
    try:
        return ctx.empresas_entrada.confirmar(id_, entrada.tipo, entrada.dados, autor(request))
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc


@router.post("/empresas/entrada/{id_}/descartar")
def descartar_entrada(id_: str):
    if not ctx.empresas_entrada.descartar(id_):
        raise erro(404, "nao_encontrado", "Este arquivo não está mais aguardando conferência.")
    return {"ok": True}


# --------------------------------------------------------------------------- leitura de arquivos pela tela


@router.post("/empresas/analisar")
async def analisar_arquivo(arquivo: UploadFile = File(...)):
    """Lê uma nota fiscal, um cheque, um comprovante ou o print de um fechamento enviado pela tela."""
    dados = await arquivo.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(dados) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise erro(413, "arquivo_grande", f"Arquivo maior que {config.MAX_UPLOAD_MB} MB.")
    try:
        analise = leitura.analisar(dados, arquivo.filename or "arquivo")
    except Exception as exc:
        log.exception("Falha ao ler o arquivo %s", arquivo.filename)
        raise erro(422, "leitura_falhou", f"Não foi possível ler o arquivo: {exc}") from exc
    meta = ctx.arquivos.salvar(dados, arquivo.filename or "arquivo")
    publico = leitura.publico(analise)
    empresa = None
    if publico["tipo"] == "nota":
        destinatario = (publico["dados"].get("destinatario") or {})
        empresa = servico.identificar_empresa(cnpj=destinatario.get("cnpj") or "", nome=destinatario.get("nome") or "")
    elif publico["tipo"] in ("cheque", "comprovante", "fechamento"):
        alvo = publico["dados"].get("empresa") or ""
        empresa = servico.identificar_empresa(nome=alvo, texto=analise.get("texto") or "")
    return {**publico, "arquivo": {"id": meta["id"], "nome": meta["nome"]},
            "empresa": (empresa or {}).get("nome") or ""}


@router.post("/empresas/arquivo", status_code=201)
async def guardar_arquivo(arquivo: UploadFile = File(...)):
    """Guarda um comprovante escolhido na tela (ex.: o depósito de um cheque) sem lê-lo; devolve o id para o lançamento."""
    dados = await arquivo.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(dados) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise erro(413, "arquivo_grande", f"Arquivo maior que {config.MAX_UPLOAD_MB} MB.")
    if not dados:
        raise erro(422, "arquivo_vazio", "O arquivo está vazio.")
    meta = ctx.arquivos.salvar(dados, arquivo.filename or "comprovante")
    return {"id": meta["id"], "nome": meta["nome"]}


@router.post("/empresas/importar-fechamento", status_code=201)
def importar_fechamento(entrada: ImportacaoFechamento, request: Request):
    """Parte 5: traz para o sistema o fechamento que já estava em andamento (lido de um print ou digitado)."""
    try:
        criadas = servico.lancar_notas(entrada.empresa, [i.model_dump() for i in entrada.linhas], autor(request),
                                       competencia=entrada.competencia or "")
    except servico.ErroEmpresas as exc:
        raise _erro_regra(exc) from exc
    return {"notas": criadas, "quantidade": len(criadas)}


# --------------------------------------------------------------------------- configuração


@router.get("/empresas/config")
def obter_config():
    return ctx.empresas_config.publica()


@router.post("/empresas/config")
def salvar_config(entrada: ConfigEntrada):
    try:
        return ctx.empresas_config.atualizar(entrada.model_dump(exclude_none=True))
    except ValueError as exc:
        raise erro(422, "config_invalida", str(exc)) from exc


@router.get("/empresas/config/chats")
def chats_do_bot():
    """Pessoas e grupos que falaram com o bot de notas (para cadastrar sem digitar o chat ID)."""
    from ..notificacoes import canais

    token = ctx.empresas_config.token()
    if not token:
        raise erro(422, "sem_token", "Informe o token do bot de notas fiscais.")
    try:
        return canais.procurar_chats_telegram(token)
    except canais.ErroCanal as exc:
        raise erro(422, "telegram", str(exc)) from exc

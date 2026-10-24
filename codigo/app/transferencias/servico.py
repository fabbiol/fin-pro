"""Transferências de clientes: recebe a nota mandada pela Operações, lista para a tela e liga o pagamento à nota.

* Cada nota vem com o número da ordem na Operações (``origem_id``). Se a mesma ordem chegar de novo (reenvio, nota
  corrigida), a linha existente é **atualizada** — nunca duplica, e a situação e o pagamento não mudam.
* Toda nota nova entra como **Aguardando pagamento**. Vira **Pago** quando alguém liga um comprovante (Pix/TED) a ela:
  um pagamento pode cobrir várias notas. Desfazer o pagamento volta as notas; o pagamento fica guardado como desfeito.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from datetime import date, datetime

from .. import comprovante
from .. import contexto as ctx
from ..arquivos import RepositorioArquivos
from ..boleto.extrator import ler_arquivo
from .modelos import AGUARDANDO, ATIVO, DESFEITO, FORMAS, PAGO, STATUS_TRANSFERENCIA

MAX_PDF = 10 * 1024 * 1024
USUARIO = "Operações"  # quem aparece como "Enviada por" e no Histórico
_lock = threading.Lock()  # a mesma ordem chegando duas vezes, ou dois cliques em "Ligar", não viram duas linhas


class ErroTransferencia(ValueError):
    """Dado recebido inválido (mensagem já pronta para devolver à Operações ou à tela)."""


class ErroPagamento(ValueError):
    """Não deu para ligar ou desfazer o pagamento: ``status`` e ``codigo`` vão na resposta para a tela."""

    def __init__(self, status: int, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.status, self.codigo = status, codigo


def _texto(campos, nome: str, limite: int, obrigatorio: bool = False) -> str:
    valor = re.sub(r"\s+", " ", str(campos.get(nome) or "")).strip()
    if obrigatorio and not valor:
        raise ErroTransferencia(f"Campo obrigatório: {nome}.")
    if len(valor) > limite:
        raise ErroTransferencia(f"O campo {nome} passa de {limite} caracteres.")
    return valor


def documento(valor, campo: str = "documento") -> str:
    """CPF ou CNPJ só com os dígitos (aceita com pontuação). Vazio é aceito."""
    texto = str(valor or "").strip()
    digitos = re.sub(r"\D", "", texto)
    if texto and (len(digitos) not in (11, 14) or re.search(r"[^\d.\-/\s]", texto)):
        raise ErroTransferencia(f"{campo} deve ser um CPF (11 dígitos) ou CNPJ (14 dígitos).")
    return digitos


def validar(campos) -> dict:
    """Confere os campos do formulário da Operações e devolve os dados prontos para gravar."""
    origem = str(campos.get("origem_id") or "").strip()
    if not re.fullmatch(r"\d{1,15}", origem) or int(origem) <= 0:
        raise ErroTransferencia("origem_id deve ser um número inteiro positivo.")
    forma = str(campos.get("forma") or "").strip()
    if forma not in FORMAS:
        raise ErroTransferencia("forma deve ser pix ou transferencia.")
    valor = str(campos.get("valor") or "").strip()
    if valor and not re.fullmatch(r"\d{1,12}(\.\d{1,4})?", valor):
        raise ErroTransferencia("valor deve ser um número com ponto decimal, ex.: 1234.56.")
    emitida = str(campos.get("emitida_em") or "").strip()
    if emitida:
        formato = "%Y-%m-%d %H:%M:%S" if len(emitida) > 10 else "%Y-%m-%d"
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?", emitida):
                raise ValueError
            datetime.strptime(emitida, formato)
        except ValueError:
            raise ErroTransferencia("emitida_em deve ser AAAA-MM-DD ou AAAA-MM-DD HH:MM:SS.") from None
    chave = re.sub(r"\s", "", str(campos.get("chave") or ""))
    if chave and not re.fullmatch(r"\d{44}", chave):
        raise ErroTransferencia("chave deve ter 44 dígitos.")
    return {"origem_id": int(origem), "nota": _texto(campos, "nota", 30, True), "pedido": _texto(campos, "pedido", 30),
            "empresa": _texto(campos, "empresa", 120, True), "documento": documento(campos.get("documento")),
            "valor": float(valor) if valor else None, "material": _texto(campos, "material", 120), "emitida_em": emitida,
            "forma": forma, "chave": chave}


def validar_pdf(conteudo: bytes) -> None:
    if len(conteudo) > MAX_PDF:
        raise ErroTransferencia("O PDF passa de 10 MB.")
    if not conteudo.startswith(b"%PDF"):
        raise ErroTransferencia("O arquivo deve ser um PDF.")


def receber(dados: dict, pdf: bytes | None = None, nome_pdf: str = "") -> tuple[dict, bool]:
    """Cria a linha ou, se essa ordem da Operações já chegou antes, atualiza os dados (e o PDF, se veio outro).

    Devolve ``(registro, criada)``. A situação (Aguardando pagamento / Pago) e o pagamento não mudam num reenvio.
    """
    banco = ctx.transferencias
    with _lock:
        existente = next((r for r in banco.listar() if r.get("origem_id") == dados["origem_id"]), None)
        anterior = None
        if pdf is not None:
            meta = ctx.arquivos.salvar(pdf, nome_pdf or f"NF {dados['nota']}.pdf")
            dados = {**dados, "arquivo": ctx.arquivos.caminho_relativo(meta["id"]), "arquivo_nome": meta["nome"]}
            anterior = RepositorioArquivos.id_de_caminho((existente or {}).get("arquivo"))
        if existente is None:
            registro = banco.adicionar({**dados, "status": AGUARDANDO}, usuario=USUARIO)
        else:
            registro = banco.atualizar(existente["id"], dados, usuario=USUARIO)
        if anterior:
            ctx.arquivos.remover(anterior)  # o PDF trocado não fica perdido na pasta de arquivos
    return registro, existente is None


def _normalizar(texto) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().casefold()


def _publico(pagamento: dict, notas: list[str]) -> dict:
    """O pagamento como a tela recebe."""
    data_pagamento = pagamento.get("data_pagamento")
    ligado_em = pagamento.get("data_lancamento")
    return {"id": pagamento["id"], "valor": pagamento.get("valor"),
            "data": data_pagamento.isoformat() if isinstance(data_pagamento, date) else data_pagamento,
            "pagador": pagamento.get("pagador") or "", "documento_pagador": pagamento.get("documento_pagador") or "",
            "id_transacao": pagamento.get("id_transacao") or "", "observacao": pagamento.get("observacao") or "",
            "notas": notas, "comprovante": bool(pagamento.get("comprovante")), "ligado_por": pagamento.get("lancado_por") or "",
            "ligado_em": ligado_em.isoformat() if isinstance(ligado_em, datetime) else ligado_em,
            "desfeito": pagamento.get("status") == DESFEITO}


def listar(empresa: str = "", situacao: str = "", busca: str = "") -> dict:
    """Linhas da tela, das mais novas para as mais antigas, com os filtros de empresa, situação e busca pela nota."""
    todas = ctx.transferencias.listar()
    notas_por_pagamento: dict[int, list[str]] = {}
    for r in todas:
        if r.get("pagamento_id"):
            notas_por_pagamento.setdefault(r["pagamento_id"], []).append(r["nota"])
    pagamentos = {p["id"]: _publico(p, notas_por_pagamento.get(p["id"], []))
                  for p in ctx.transferencias.listar("pagamentos") if p["id"] in notas_por_pagamento}
    linhas = [{**r, "pagamento": pagamentos.get(r.get("pagamento_id"))} for r in todas]
    if empresa:
        linhas = [r for r in linhas if _normalizar(r.get("empresa")) == _normalizar(empresa)]
    if situacao:
        linhas = [r for r in linhas if r.get("status") == situacao]
    if busca.strip():
        linhas = [r for r in linhas if _normalizar(busca) in _normalizar(r.get("nota"))]
    linhas.sort(key=lambda r: (r.get("emitida_em") or "", r["id"]), reverse=True)
    return {"transferencias": linhas, "total": len(linhas), "valor": round(sum(r.get("valor") or 0 for r in linhas), 2),
            "empresas": sorted({r["empresa"] for r in todas if r.get("empresa")}, key=_normalizar),
            "situacoes": list(STATUS_TRANSFERENCIA), "formas": FORMAS}


# --------------------------------------------------------------------------- ligar o pagamento à nota


def _mesmo_id(a: str, b: str) -> bool:
    return bool(a) and re.sub(r"\s", "", a).casefold() == re.sub(r"\s", "", b or "").casefold()


def pagamento_com_id(id_transacao: str) -> dict | None:
    """Pagamento ativo que já usa esse ID da transação (o mesmo comprovante não paga duas vezes)."""
    return next((p for p in ctx.transferencias.listar("pagamentos")
                 if p.get("status") == ATIVO and _mesmo_id(id_transacao, p.get("id_transacao"))), None)


def ler_comprovante(dados: bytes) -> dict:
    """O que deu para ler do comprovante (para o dono conferir). Campos não lidos vêm ``None``."""
    try:
        texto = ler_arquivo(dados, max_paginas=3).get("texto") or ""
    except Exception:
        texto = ""  # PDF protegido ou foto ilegível: o dono preenche à mão
    extraido = comprovante.extrair(texto)
    data_pagamento = extraido.get("data_pagamento")
    return {"valor": extraido.get("valor_pago"), "data": data_pagamento.isoformat() if data_pagamento else None,
            **comprovante.pagador(texto)}


def _valores(entrada: dict) -> dict:
    """Confere o que o dono confirmou na tela."""
    try:
        valor = round(float(entrada.get("valor")), 2)
    except (TypeError, ValueError):
        valor = 0
    if valor <= 0:
        raise ErroPagamento(422, "valor_invalido", "Informe o valor pago.")
    try:
        data_pagamento = date.fromisoformat(str(entrada.get("data") or ""))
    except ValueError:
        raise ErroPagamento(422, "data_invalida", "Informe a data do pagamento.") from None
    try:
        documento_pagador = documento(entrada.get("documento_pagador"), "O CNPJ/CPF do pagador")
    except ErroTransferencia as exc:
        raise ErroPagamento(422, "documento_invalido", str(exc)) from None
    textos = {}
    for campo, limite in (("pagador", 120), ("id_transacao", 80), ("observacao", 300)):
        textos[campo] = re.sub(r"\s+", " ", str(entrada.get(campo) or "")).strip()[:limite]
    return {"valor": valor, "data_pagamento": data_pagamento, "documento_pagador": documento_pagador, **textos}


def ligar(ids: list[int], arquivo_id: str, entrada: dict, usuario: str) -> tuple[dict, list[dict]]:
    """Grava o pagamento e passa as notas para Pago, tudo de uma vez. Devolve ``(pagamento, notas)``."""
    valores = _valores(entrada)
    meta = ctx.arquivos.meta(arquivo_id)
    if not meta:
        raise ErroPagamento(404, "arquivo_nao_encontrado", "O arquivo do comprovante não está mais disponível. Envie-o de novo.")
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise ErroPagamento(422, "sem_notas", "Marque pelo menos uma nota.")
    banco = ctx.transferencias
    with _lock:
        por_id = {r["id"]: r for r in banco.listar()}
        faltando = [i for i in ids if i not in por_id]
        if faltando:
            raise ErroPagamento(404, "nota_nao_encontrada", "Nota não encontrada. Atualize a tela e tente de novo.")
        pagas = [por_id[i]["nota"] for i in ids if por_id[i].get("status") != AGUARDANDO]
        if pagas:
            raise ErroPagamento(409, "nota_ja_paga", f"A nota {', '.join(pagas)} já está paga.")
        repetido = pagamento_com_id(valores["id_transacao"])
        if repetido:
            raise ErroPagamento(409, "comprovante_repetido",
                                f"Este comprovante (mesmo ID da transação) já foi ligado no pagamento nº {repetido['id']}.")
        notas = [por_id[i]["nota"] for i in ids]
        # mesmo cálculo do banco para o próximo número; o _lock garante que ninguém grava no meio
        proximo = max((p["id"] for p in banco.listar("pagamentos")), default=0) + 1
        resultados = banco.aplicar_lote(
            [{"tipo": "adicionar", "aba": "pagamentos", "usuario": usuario,
              "dados": {**valores, "notas": ", ".join(notas), "status": ATIVO,
                        "comprovante": ctx.arquivos.caminho_relativo(arquivo_id), "comprovante_nome": meta["nome"]}}]
            + [{"tipo": "atualizar", "id": i, "usuario": usuario, "dados": {"status": PAGO, "pagamento_id": proximo}}
               for i in ids])
    return _publico(resultados[0]["registro"], notas), [r["registro"] for r in resultados[1:]]


def desfazer(pagamento_id: int, usuario: str) -> tuple[dict, list[dict]]:
    """As notas do pagamento voltam a Aguardando pagamento; o pagamento (e o comprovante) fica guardado como desfeito."""
    banco = ctx.transferencias
    with _lock:
        pagamento = next((p for p in banco.listar("pagamentos") if p["id"] == pagamento_id), None)
        if pagamento is None:
            raise ErroPagamento(404, "pagamento_nao_encontrado", "Pagamento não encontrado.")
        if pagamento.get("status") == DESFEITO:
            raise ErroPagamento(409, "pagamento_ja_desfeito", "Este pagamento já foi desfeito.")
        notas = [r for r in banco.listar() if r.get("pagamento_id") == pagamento_id]
        resultados = banco.aplicar_lote(
            [{"tipo": "atualizar", "aba": "pagamentos", "id": pagamento_id, "usuario": usuario,
              "dados": {"status": DESFEITO, "desfeito_por": usuario,
                        "desfeito_em": datetime.now().isoformat(sep=" ", timespec="minutes")}}]
            + [{"tipo": "atualizar", "id": r["id"], "usuario": usuario, "dados": {"status": AGUARDANDO, "pagamento_id": None}}
               for r in notas])
    return _publico(resultados[0]["registro"], [r["nota"] for r in notas]), [r["registro"] for r in resultados[1:]]


def comprovante_do_pagamento(pagamento_id: int) -> str | None:
    """Id do arquivo do comprovante (também de pagamento desfeito, que fica no histórico)."""
    pagamento = next((p for p in ctx.transferencias.listar("pagamentos") if p["id"] == pagamento_id), None)
    return RepositorioArquivos.id_de_caminho((pagamento or {}).get("comprovante"))

"""Transferências de clientes: recebe a nota mandada pela Operações e lista para a tela.

* Cada nota vem com o número da ordem na Operações (``origem_id``). Se a mesma ordem chegar de novo (reenvio, nota
  corrigida), a linha existente é **atualizada** — nunca duplica.
* Toda nota nova entra como **Aguardando pagamento**. A baixa (``Pago``) pelo extrato do banco é o próximo passo.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from datetime import datetime

from .. import contexto as ctx
from ..arquivos import RepositorioArquivos
from .modelos import AGUARDANDO, FORMAS, STATUS_TRANSFERENCIA

MAX_PDF = 10 * 1024 * 1024
USUARIO = "Operações"  # quem aparece como "Enviada por" e no Histórico
_lock = threading.Lock()  # a mesma ordem chegando duas vezes ao mesmo tempo não vira duas linhas


class ErroTransferencia(ValueError):
    """Dado recebido inválido (mensagem já pronta para devolver à Operações)."""


def _texto(campos, nome: str, limite: int, obrigatorio: bool = False) -> str:
    valor = re.sub(r"\s+", " ", str(campos.get(nome) or "")).strip()
    if obrigatorio and not valor:
        raise ErroTransferencia(f"Campo obrigatório: {nome}.")
    if len(valor) > limite:
        raise ErroTransferencia(f"O campo {nome} passa de {limite} caracteres.")
    return valor


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
            "empresa": _texto(campos, "empresa", 120, True), "valor": float(valor) if valor else None,
            "material": _texto(campos, "material", 120), "emitida_em": emitida, "forma": forma, "chave": chave}


def validar_pdf(conteudo: bytes) -> None:
    if len(conteudo) > MAX_PDF:
        raise ErroTransferencia("O PDF passa de 10 MB.")
    if not conteudo.startswith(b"%PDF"):
        raise ErroTransferencia("O arquivo deve ser um PDF.")


def receber(dados: dict, pdf: bytes | None = None, nome_pdf: str = "") -> tuple[dict, bool]:
    """Cria a linha ou, se essa ordem da Operações já chegou antes, atualiza os dados (e o PDF, se veio outro).

    Devolve ``(registro, criada)``. A situação (Aguardando pagamento / Pago) não muda num reenvio.
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


def listar(empresa: str = "", situacao: str = "", busca: str = "") -> dict:
    """Linhas da tela, das mais novas para as mais antigas, com os filtros de empresa, situação e busca pela nota."""
    todas = ctx.transferencias.listar()
    linhas = todas
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

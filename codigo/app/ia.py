"""Leitura assistida por IA (Claude, com visão) — opcional.

Ativada quando ``ANTHROPIC_API_KEY`` está definida no arquivo ``.env``. Usada para fotos
difíceis (desfocadas, amassadas, com reflexo) em que o OCR local não encontra tudo.
O resultado nunca é aceito às cegas: a linha digitável passa pela validação dos DVs.
"""

from __future__ import annotations

import base64
import io
import json
import logging

from . import config
from .boleto.leitores import abrir_imagem, eh_pdf

log = logging.getLogger(__name__)


class ErroIA(RuntimeError):
    pass


CAMPOS = ("linha_digitavel", "beneficiario", "documento_beneficiario", "numero_documento", "vencimento", "valor", "observacoes")

ESQUEMA = {
    "type": "object",
    "properties": {
        "linha_digitavel": {"type": "string", "description": "Somente dígitos; vazio se ilegível"},
        "beneficiario": {"type": "string"},
        "documento_beneficiario": {"type": "string"},
        "numero_documento": {"type": "string"},
        "vencimento": {"type": "string", "description": "AAAA-MM-DD ou vazio"},
        "valor": {"type": "string", "description": "Número com ponto decimal, ex.: 1500.75, ou vazio"},
        "observacoes": {"type": "string"},
    },
    "required": list(CAMPOS),
    "additionalProperties": False,
}

INSTRUCOES = """Você está lendo um boleto brasileiro (PDF ou foto). Transcreva exatamente o que está impresso:

- linha_digitavel: a linha digitável (47 dígitos em boletos bancários; 48 em contas de consumo e tributos, que começam com 8). Retorne somente os dígitos. Se só houver o número do código de barras (44 dígitos), use-o.
- beneficiario: nome ou razão social de quem recebe o pagamento (campo "Beneficiário" ou "Cedente"), sem CPF/CNPJ. Não confunda com o Pagador.
- documento_beneficiario: CPF ou CNPJ do beneficiário, formatado (ex.: 12.345.678/0001-95).
- numero_documento: o campo "Nº do Documento" (não confundir com "Nosso Número").
- vencimento: a data de vencimento no formato AAAA-MM-DD.
- valor: o valor do documento, com ponto como separador decimal (ex.: 1500.75).
- observacoes: no máximo uma frase curta sobre algo que atrapalhou a leitura; vazio se nada.

Use string vazia para qualquer campo que não esteja legível. Nunca invente ou complete dígitos que você não consegue ver."""


def disponivel() -> bool:
    if not config.ia_configurada():
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _bloco_arquivo(dados: bytes) -> dict:
    if eh_pdf(dados):
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": base64.standard_b64encode(dados).decode()},
        }
    imagem = abrir_imagem(dados)
    imagem.thumbnail((2200, 2200))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=90)
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(buffer.getvalue()).decode()},
    }


def extrair(dados: bytes, pagina: int = 0) -> dict:
    if not disponivel():
        raise ErroIA("IA não configurada. Defina ANTHROPIC_API_KEY no arquivo .env e reinicie o sistema.")

    import anthropic

    pedido = INSTRUCOES
    if pagina:
        pedido += f"\n\nO arquivo pode conter vários boletos: extraia o da página {pagina + 1}."

    cliente = anthropic.Anthropic(timeout=180.0, max_retries=2)
    try:
        resposta = cliente.beta.messages.create(
            model=config.IA_MODELO,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=[{"role": "user", "content": [_bloco_arquivo(dados), {"type": "text", "text": pedido}]}],
        )
    except anthropic.AuthenticationError as exc:
        raise ErroIA("Chave da API Anthropic inválida. Verifique ANTHROPIC_API_KEY no arquivo .env.") from exc
    except anthropic.RateLimitError as exc:
        raise ErroIA("Limite de uso da API atingido. Aguarde alguns instantes e tente novamente.") from exc
    except anthropic.BadRequestError as exc:
        raise ErroIA(f"A API recusou a solicitação: {exc.message}") from exc
    except anthropic.APIStatusError as exc:
        raise ErroIA(f"Erro na API Anthropic (HTTP {exc.status_code}). Tente novamente.") from exc
    except anthropic.APIConnectionError as exc:
        raise ErroIA("Sem conexão com a API Anthropic. Verifique a internet.") from exc

    if resposta.stop_reason == "refusal":
        raise ErroIA("A IA não pôde processar este arquivo.")

    texto = "".join(bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text")
    try:
        dados_ia = json.loads(texto)
    except json.JSONDecodeError as exc:
        log.warning("Resposta inesperada da IA: %s", texto[:500])
        raise ErroIA("A IA respondeu em um formato inesperado. Tente novamente.") from exc
    return {campo: str(dados_ia.get(campo) or "") for campo in CAMPOS}

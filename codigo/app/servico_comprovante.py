"""Registro de pagamentos a partir de comprovantes (tela Ler boletos, anexo manual, e-mail e bot do Telegram)."""

from __future__ import annotations

import logging
from datetime import date

from . import comprovante, servicos
from . import contexto as ctx
from .boleto.extrator import ler_arquivo
from .planilha import RegistroNaoEncontrado

log = logging.getLogger("leitor_boletos")
ABAS = {"boletos": "repositorio", "pix": "repositorio_pix"}


def repositorio(aba: str):
    if aba not in ABAS:
        raise RegistroNaoEncontrado(aba)
    return getattr(ctx, ABAS[aba])


def analisar_texto(texto: str, codigos: list[str] | None = None, forcar: bool = False) -> dict | None:
    """Se o texto for de um comprovante, devolve o que foi lido, os lançamentos possíveis e o escolhido (se claro)."""
    if not forcar and not comprovante.eh_comprovante(texto):
        return None
    extraido = comprovante.extrair(texto, codigos)
    lista = comprovante.candidatos(extraido, ctx.repositorio.listar(), ctx.repositorio_pix.listar())
    escolhido = None if extraido["agendado"] else comprovante.escolher(lista)
    return {"extraido": comprovante.publico(extraido), "candidatos": lista, "sugerido": escolhido}


def analisar_resultado(resultado: dict) -> dict | None:
    texto = resultado.get("texto") or ""
    codigos = [b["codigo"]["codigo_barras"] for b in resultado.get("boletos") or []
               if (b.get("codigo") or {}).get("valido") and b["codigo"].get("codigo_barras")]
    return analisar_texto(texto, codigos)


def registrar(aba: str, id_: int, extraido: dict, usuario: str, arquivo_id: str | None = None) -> dict:
    """Marca o lançamento como pago com os valores do comprovante e anexa o arquivo."""
    repo = repositorio(aba)
    registro = repo.obter(id_)
    alteracoes = comprovante.dados_de_pagamento(extraido, registro)
    if arquivo_id:
        meta = ctx.arquivos.meta(arquivo_id)
        if meta:
            alteracoes.update(comprovante=ctx.arquivos.caminho_relativo(arquivo_id), comprovante_nome=meta["nome"])
    atualizado, _ = repo.atualizar(id_, alteracoes, usuario=usuario)
    log.info("Pagamento registrado por comprovante: %s %s (%s)", aba, id_, usuario)
    return atualizado


def desfazer(aba: str, id_: int, usuario: str) -> dict:
    atualizado, _ = repositorio(aba).atualizar(id_, {"status": "Pendente", "data_pagamento": None, "valor_pago": None,
                                                     "juros_multa": None, "desconto": None, "comprovante": "",
                                                     "comprovante_nome": ""}, usuario=usuario)
    return atualizado


def valores_do_arquivo(dados: bytes) -> dict | None:
    """Lê um comprovante anexado à mão (o lançamento já é conhecido): só extrai valores e data."""
    try:
        resultado = ler_arquivo(dados, max_paginas=3)
    except Exception:
        return None
    analise = analisar_resultado(resultado) or analisar_texto(resultado.get("texto") or "", forcar=True)
    return analise["extraido"] if analise else None


def serializar(aba: str, registro: dict) -> dict:
    return servicos.serializar(registro) if aba == "boletos" else servicos.serializar_pix(registro)


def resumo_pagamento(aba: str, registro: dict) -> dict:
    """Para mensagens (Telegram) e para a tela: o que foi pago, juros, desconto e atraso."""
    vencimento = registro.get("vencimento")
    pagamento = registro.get("data_pagamento")
    if isinstance(vencimento, str):
        vencimento = date.fromisoformat(vencimento[:10])
    if isinstance(pagamento, str):
        pagamento = date.fromisoformat(pagamento[:10])
    atraso = (pagamento - vencimento).days if vencimento and pagamento else None
    return {
        "aba": aba, "id": registro.get("id"),
        "nome": (registro.get("recebedor") if aba == "pix" else registro.get("beneficiario")) or "",
        "valor": registro.get("valor"), "valor_pago": registro.get("valor_pago") or registro.get("valor"),
        "juros_multa": registro.get("juros_multa") or 0, "desconto": registro.get("desconto") or 0,
        "vencimento": vencimento.isoformat() if vencimento else None,
        "data_pagamento": pagamento.isoformat() if pagamento else None,
        "dias_atraso": atraso if atraso and atraso > 0 else 0,
    }

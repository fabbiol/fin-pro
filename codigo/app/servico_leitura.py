"""Leitura de um arquivo enviado (boletos, ou Pix quando não há boleto), usada pela tela e pela caixa de entrada."""

from __future__ import annotations

import logging

from . import config, ia, servicos
from .boleto.extrator import ler_arquivo, mesclar_ia
from . import contexto as ctx
from .pix import ler_pix_de_arquivo

log = logging.getLogger("leitor_boletos")


def pix_existente(pix: dict) -> dict | None:
    """Pix já lançado com o mesmo Copia e Cola (ou mesma chave + identificador TXID)."""
    copia = pix.get("copia_e_cola")
    txid = pix.get("txid")
    for registro in ctx.repositorio_pix.listar():
        if registro.get("status") == "Cancelado":
            continue
        if copia and registro.get("copia_e_cola") == copia:
            return registro
        if txid and registro.get("txid") == txid and registro.get("chave") == pix.get("chave"):
            return registro
    return None


def com_duplicado(pix: dict) -> dict:
    existente = pix_existente(pix)
    return {**pix, "duplicado": servicos.serializar_pix(existente) if existente else None}


def processar_leitura(dados: bytes, nome: str, ao_progresso=None) -> dict:
    """Lê o arquivo, guarda o original e (se configurado) completa com IA. Lança ErroLeitura."""
    resultado = ler_arquivo(dados, planilha=ctx.repositorio, max_paginas=config.MAX_PAGINAS_PDF, ao_progresso=ao_progresso)
    meta = ctx.arquivos.salvar(dados, nome or "arquivo")
    resultado["pix"] = []

    # Comprovante de pagamento: não é um boleto a lançar, e sim o pagamento de um lançamento que já existe
    from .servico_comprovante import analisar_resultado

    analise = analisar_resultado(resultado)
    resultado.pop("texto", None)
    if analise:
        resultado.update(comprovante=analise, boletos_do_comprovante=resultado["boletos"], boletos=[], arquivo=meta)
        return resultado

    if not resultado["boletos"]:
        # Sem boleto: pode ser uma cobrança por Pix (QR code ou "Pix Copia e Cola" no documento)
        try:
            resultado["pix"] = [com_duplicado(p) for p in ler_pix_de_arquivo(dados, max_paginas=config.MAX_PAGINAS_PDF)]
        except Exception:
            log.exception("Falha ao procurar QR code Pix em %s", nome)

    if config.IA_AUTOMATICA and ia.disponivel() and not resultado["pix"]:
        alvos = [(i, b) for i, b in enumerate(resultado["boletos"]) if b["confianca"] < 0.8] or (
            [(None, {"campos": {}, "pagina": 0})] if not resultado["boletos"] else []
        )
        for indice, boleto in alvos:
            try:
                dados_ia = ia.extrair(dados, boleto["pagina"])
            except ia.ErroIA as exc:
                resultado["avisos"].append(f"IA: {exc}")
                break
            novo = mesclar_ia(boleto["campos"], dados_ia, planilha=ctx.repositorio, pagina=boleto["pagina"])
            novo["ia_usada"] = True
            if indice is None:
                resultado["boletos"].append(novo)
            else:
                resultado["boletos"][indice] = novo

    resultado["arquivo"] = meta
    return resultado

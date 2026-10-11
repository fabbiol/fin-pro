"""Leitura do cupom fiscal ou da nota de uma compra paga em dinheiro: valor, data, hora e onde foi.

O valor certo é o **a pagar** (ou o total) — nunca o dinheiro entregue nem o troco, que também aparecem no cupom.
"""

from __future__ import annotations

import re
from datetime import date

from ..boleto.texto import extrair_data, normalizar
from ..empresas.leitura import (
    RE_CNPJ_SOLTO, _linhas, _nome_de_empresa, _valores_do_texto, eh_xml, ler_xml_nota, texto_do_arquivo,
)

# Do mais confiável para o menos: "Valor a pagar R$ 179,70" é o que saiu do caixa
ROTULOS_TOTAL = (r"valor a pagar", r"total a pagar", r"valor total", r"total geral", r"total da (nota|compra|venda)",
                 r"total\s*r\$", r"\btotal\b")
NAO_E_TOTAL = ("troco", "dinheiro", "valor pago", "valor recebido", "recebido", "desconto", "acrescimo", "tributo",
               "imposto", "12.741", "12741", "itens", "qtd", "quantidade")
CABECALHOS = ("documento auxiliar", "cupom", "nfc-e", "nfce", "nota fiscal", "consumidor", "extrato", "sat ",
              "cnpj", "inscricao", "ie:", "endereco", "danfe", "emissao", "via ")


def valor_total(texto: str) -> float | None:
    linhas = _linhas(texto)
    for rotulo in ROTULOS_TOTAL:
        for i, linha in enumerate(linhas):
            normal = normalizar(linha)
            m = re.search(rotulo, normal)
            if not m or any(palavra in normal for palavra in NAO_E_TOTAL):
                continue
            valores = _valores_do_texto(linha[m.start():])
            if not valores and i + 1 < len(linhas):  # valor na linha de baixo (cupom em duas colunas)
                valores = _valores_do_texto(linhas[i + 1])
            if valores:
                return valores[-1]
    valores = []
    for linha in linhas:  # sem rótulo legível: o maior valor, ignorando troco e dinheiro entregue
        if not any(palavra in normalizar(linha) for palavra in NAO_E_TOTAL):
            valores += _valores_do_texto(linha)
    return max(valores) if valores else None


def estabelecimento(texto: str) -> str:
    """Nome da loja: a primeira linha com cara de nome, antes do CNPJ, que não é cabeçalho do cupom."""
    for linha in _linhas(texto)[:12]:
        normal = normalizar(linha)
        if any(c in normal for c in CABECALHOS) or len(re.findall(r"[A-Za-zÀ-ÿ]", linha)) < 4:
            continue
        nome = _nome_de_empresa(linha)
        if nome:
            return nome[:80]
    return ""


def analisar_texto(texto: str, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    datas = [d for d in (extrair_data(m.group(0)) for m in re.finditer(r"\d{2}\s?/\s?\d{2}\s?/\s?\d{2,4}", texto or ""))
             if d and d <= hoje]
    hora = ""
    m = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::\d{2})?(?!\d)", texto or "")
    if m:
        hora = f"{int(m.group(1)):02d}:{m.group(2)}"
    cnpj = next((re.sub(r"\D", "", c.group(0)) for c in RE_CNPJ_SOLTO.finditer(texto or "")), "")
    return {"valor": valor_total(texto), "data": max(datas) if datas else None, "hora": hora,
            "local": estabelecimento(texto), "cnpj": cnpj}


def analisar(dados: bytes, nome_arquivo: str = "") -> dict:
    """Lê a foto ou o PDF do cupom (ou o XML da nota). Gira a foto quando a primeira leitura não acha o valor."""
    if eh_xml(dados) or (nome_arquivo or "").lower().endswith(".xml"):
        nota = ler_xml_nota(dados)
        if nota:
            return {"valor": nota.get("valor_total"), "data": nota.get("data"), "hora": "",
                    "local": (nota.get("emitente") or {}).get("nome") or "", "cnpj": (nota.get("emitente") or {}).get("cnpj") or ""}
    texto = texto_do_arquivo(dados)
    lido = analisar_texto(texto)
    if not lido["valor"]:
        girado = texto_do_arquivo(dados, girando=True)
        lido = {**analisar_texto(girado), **{k: v for k, v in lido.items() if v}}
    return lido

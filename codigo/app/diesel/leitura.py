"""Leitura dos arquivos do diesel: o **comprovante de pagamento** da compra no posto ou o **canhoto** de um
abastecimento (também o "pedido" / documento não fiscal que o posto entrega).

Um canhoto pode ter **várias linhas** — ex.: 200 L de Diesel comum e 200 L de Diesel S10 no mesmo pedido, para
máquinas diferentes. Cada linha sai com o **combustível**, os litros, o preço por litro e o total.

Foto de canhoto sai com o OCR torto ("200006" no lugar de "200,000", "7.450" parecendo milhar). Por isso cada linha
é conferida pela conta **litros × preço = total**, e o que não bate é acertado pelos **totais do rodapé**
("Quantidade de itens" e "Valor total"). Tudo passa por conferência antes de lançar.
"""

from __future__ import annotations

import re
from datetime import date
from itertools import permutations

from ..boleto.texto import extrair_data, normalizar
from ..caixa.leitura import estabelecimento, valor_total
from ..empresas.leitura import _linhas, _valores_do_texto, texto_do_arquivo

LIMITE_CANHOTO = 600.0  # acima disso, em litros, é compra (o estoque da semana), não o abastecimento de uma máquina
PRECO_MINIMO, PRECO_MAXIMO = 2.0, 15.0  # faixa de preço do litro (separa o preço dos litros e do total)

SINAIS_COMPRA = ("comprovante de pagamento", "comprovante de transferencia", "pix", "transferencia", "ted", "boleto",
                 "pagamento efetuado", "pagamento realizado", "valor pago", "favorecido", "recebedor", "debito",
                 "autenticacao", "id da transacao")
SINAIS_CANHOTO = ("canhoto", "abastecimento", "requisicao", "frentista", "bomba", "bico", "placa", "motorista",
                  "hodometro", "horimetro", "odometro", "km", "frota", "veiculo", "prefixo", "assinatura",
                  "documento nao fiscal", "pedido", "cond. pagto", "vendedor")
PARADAS = ("totais", "quantidade de itens", "quantidade de rtens", "qusntidade", "valor total bruto", "valor total liquido",
           "valor desconto", "credito troca", "subtotal", "forma de pagamento", "dados do cliente", "cliente:")

RE_LITROS = [
    re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,3})?|\d+(?:[.,]\d{1,3})?)\s*(?:l\b|lt\b|lts\b|litros?\b)", re.I),
    re.compile(r"(?:litros?|lts?|qtd|quantidade|qtde|volume)\s*[:=.\-]?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,3})?|\d+(?:[.,]\d{1,3})?)", re.I),
]
RE_PRECO = re.compile(r"(?:pre[cç]o|valor|vl\.?|r\$)\s*(?:unit[aá]rio|unit\.?|/\s*l(?:itro)?|por litro|litro)\s*[:=]?\s*"
                      r"(?:r\$)?\s*(\d{1,2}[.,]\d{2,3})", re.I)
RE_PLACA = re.compile(r"\b([A-Z]{3})[\s-]?(\d[A-Z0-9]\d{2})\b")
RE_MEDIDOR = re.compile(r"(?:km|hod[oô]metro|od[oô]metro|hor[ií]metro|hr|horas?)\s*[:=.\-]?\s*(\d{1,3}(?:\.\d{3})+(?:,\d)?|\d+(?:[.,]\d)?)",
                        re.I)
RE_TOKEN = re.compile(r"(?<![\w.,])\d[\d.,]*\d(?![\w])|(?<![\w.,])\d(?![\w.,])")
RE_PEDIDO = re.compile(r"(?:pedido|requisi[cç][aã]o|canhoto|cupom|documento)\s*n?\S{0,2}\s*[:.]?\s*(\d{4,12})", re.I)


# --------------------------------------------------------------------------- números e combustível


def _numero(texto: str) -> float | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", texto):
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _leituras(token: str) -> list[float]:
    """Os jeitos possíveis de ler um número do OCR: "7.450" = 7450 ou 7,45; "200006" = 200006 ou 200,006;
    "2.840.000" = 2840000 ou 2.840,000."""
    token = token.strip(".,")
    opcoes = []
    normal = _numero(token)
    if normal is not None:
        opcoes.append(normal)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", token):  # último ponto no lugar da vírgula
        inteiro, _, decimais = token.rpartition(".")
        opcoes.append(float(inteiro.replace(".", "") + "." + decimais))
    if re.fullmatch(r"\d{4,}", token):  # vírgula que o OCR comeu: "200006" → 200,006
        opcoes.append(float(token[:-3] + "." + token[-3:]))
    return list(dict.fromkeys(round(o, 4) for o in opcoes))


def _tokens(texto: str) -> list[str]:
    """Números do texto, sem os códigos de produto ("000005"), que não são litros, preço nem total."""
    return [t for t in RE_TOKEN.findall(texto or "") if not re.fullmatch(r"0\d{3,}", t)]


def combustivel_do_texto(texto: str) -> str:
    """Qual combustível: "DIESEL S10", "DIESELS10", "S-10", "DIESEL COMUM", "S500", "GASOLINA", "ARLA"…
    Diesel sem dizer qual devolve "" (quem confere escolhe, ou vale o da máquina)."""
    junto = re.sub(r"[\s\-_.]", "", normalizar(texto))
    if "arla" in junto:
        return "Arla 32"
    if "s10" in junto:
        return "Diesel S10"
    if "s500" in junto or "dieselcomum" in junto or ("diesel" in junto and "comum" in junto):
        return "Diesel comum"
    if "gasolina" in junto:
        return "Gasolina"
    if "etanol" in junto or "alcool" in junto:
        return "Etanol"
    return ""


def eh_linha_de_produto(linha: str) -> bool:
    normal = re.sub(r"[\s\-_.]", "", normalizar(linha))
    return any(p in normal for p in ("diesel", "s10", "s500", "gasolina", "etanol", "alcool", "arla"))


# --------------------------------------------------------------------------- linhas do canhoto


def _melhor_trio(tokens: list[str]) -> dict | None:
    """Acha litros, preço e total entre os números de uma linha: o preço fica na faixa do litro e a conta tem que bater."""
    candidatos = [(i, v) for i, t in enumerate(tokens) for v in _leituras(t)]
    precos = [(i, v) for i, v in candidatos  # o preço do litro sempre tem casas decimais ("6,750", "7.450")
              if PRECO_MINIMO <= v <= PRECO_MAXIMO and re.search(r"[.,]\d", tokens[i])]
    melhor = None
    for (ip, preco) in precos:
        outros = [(i, v) for i, v in candidatos if i != ip and v > 0]
        for (iq, q), (it, t) in permutations(outros, 2):
            if iq == it or q > 60000:
                continue
            erro = abs(q * preco - t) / t if t else 1
            if melhor is None or erro < melhor["erro"]:
                melhor = {"litros": q, "preco_litro": preco, "valor": t, "erro": erro}
    if melhor and melhor["erro"] <= 0.015:
        melhor["litros"] = round(melhor["valor"] / melhor["preco_litro"], 2)  # o total costuma sair mais certo
        melhor["conferido"] = True
        return melhor
    if precos:  # a conta não bateu: fica com o preço e o maior número como total (acertado pelos totais, se der)
        preco = precos[0][1]
        resto = [v for i, v in candidatos if i != precos[0][0] and v > preco * 5]
        if resto:
            total = max(resto)
            return {"litros": round(total / preco, 2), "preco_litro": preco, "valor": total, "erro": 1.0, "conferido": False}
    litros = [v for i, v in candidatos if 1 <= v <= 60000]
    return {"litros": litros[0], "preco_litro": None, "valor": None, "erro": 1.0, "conferido": False} if litros else None


def _total_do_rodape(linhas: list[str], rotulos: tuple[str, ...], alvo: float | None) -> float | None:
    """Valor do rodapé ("Quantidade de itens 400.000", "Valor Total Líquido 2.840.000") — o jeito de ler que chega
    mais perto da soma das linhas."""
    for linha in linhas:
        normal = normalizar(linha)
        if not any(r in normal for r in rotulos):
            continue
        leituras = [v for t in _tokens(linha) for v in _leituras(t)]
        if not leituras:
            continue
        if not alvo:
            return leituras[-1]
        return min(leituras, key=lambda v: abs(v - alvo))
    return None


def itens_do_canhoto(texto: str) -> list[dict]:
    """Cada combustível do canhoto: {"combustivel", "descricao", "litros", "preco_litro", "valor", "conferido"}."""
    linhas = _linhas(texto)
    itens = []
    for i, linha in enumerate(linhas):
        if not eh_linha_de_produto(linha) or any(p in normalizar(linha) for p in PARADAS):
            continue
        descricao = re.sub(r"^\s*(?:produto|descri[cç][aã]o)?\s*[:\-]?\s*\d{0,8}\s*", "", linha).strip()[:60]
        tokens = _tokens(re.sub(r"s\s*-?\s*(10|500)\b", "", descricao, flags=re.I))
        for seguinte in linhas[i + 1:i + 4]:  # os números podem estar nas linhas de baixo
            if eh_linha_de_produto(seguinte) or any(p in normalizar(seguinte) for p in PARADAS):
                break
            tokens += [t for t in _tokens(seguinte)]
            if len(tokens) >= 3 and _melhor_trio(tokens) and _melhor_trio(tokens).get("conferido"):
                break
        trio = _melhor_trio(tokens) or {}
        itens.append({"combustivel": combustivel_do_texto(linha), "descricao": re.sub(r"[\d.,\s]+$", "", descricao).strip(),
                      "litros": trio.get("litros"), "preco_litro": trio.get("preco_litro"), "valor": trio.get("valor"),
                      "conferido": bool(trio.get("conferido"))})
    itens = [i for i in itens if i["litros"] or i["valor"]]
    if not itens:
        return []
    # acerta pelo rodapé a linha cuja conta não bateu
    soma_valor = sum(i["valor"] or 0 for i in itens)
    total_valor = _total_do_rodape(linhas, ("valor total liquido", "valor total bruto", "total liquido", "valor total"),
                                   soma_valor)
    duvidosas = [i for i in itens if not i["conferido"]]
    if total_valor and len(duvidosas) == 1 and duvidosas[0]["preco_litro"]:
        outra = sum(i["valor"] or 0 for i in itens if i is not duvidosas[0])
        restante = round(total_valor - outra, 2)
        if restante > 0:
            duvidosas[0].update(valor=restante, litros=round(restante / duvidosas[0]["preco_litro"], 2), conferido=True)
    for item in itens:
        for campo, casas in (("litros", 2), ("valor", 2), ("preco_litro", 3)):
            if item[campo] is not None:
                item[campo] = round(item[campo], casas)
    return itens[:10]


# --------------------------------------------------------------------------- classificação e leitura


def litros_do_texto(texto: str) -> float | None:
    for padrao in RE_LITROS:
        for m in padrao.finditer(texto or ""):
            valor = _numero(m.group(1))
            if valor and 1 <= valor <= 60000:
                return round(valor, 2)
    return None


def classificar(texto: str, legenda: str = "", litros: float | None = None) -> str:
    """``compra``, ``canhoto`` ou "" (não deu para saber: o bot pergunta)."""
    pedido = normalizar(legenda)
    if re.search(r"\bcompra|\bpag(o|amento|uei)|\bcomprovante\b", pedido):
        return "compra"
    if re.search(r"\bcanhoto|\babasteci|\babastecimento", pedido):
        return "canhoto"
    normal = normalizar(texto)
    compra = sum(1 for s in SINAIS_COMPRA if s in normal)
    canhoto = sum(1 for s in SINAIS_CANHOTO if re.search(rf"\b{re.escape(s)}\b", normal))
    if litros:
        if litros >= LIMITE_CANHOTO:
            compra += 2
        else:
            canhoto += 2
    if compra >= 2 and compra > canhoto:
        return "compra"
    if canhoto >= 2 and canhoto > compra:
        return "canhoto"
    return ""


RUIDO_DO_BANCO = ("telefone", "ouvidoria", "sac ", "sac-", "site", "atendimento", "fale conosco", "0800", "deficiente",
                  "reclamac", "cancelamento", "servico de", "apoio ao cliente", "alo ")
RE_FAVORECIDO = re.compile(r"^\s*(?:nome|favorecido|recebedor|benefici[aá]rio|destinat[aá]rio|para|pago a)\s*[:\-]\s*(.{3,})$", re.I)


def _nossa_empresa() -> str:
    try:
        from .. import contexto

        return normalizar((contexto.empresas_config.minha_empresa or {}).get("nome") or "")
    except Exception:
        return ""


def _posto(texto: str, tipo: str) -> str:
    """Nome do posto: a linha com "posto"; no comprovante, quem recebeu o pagamento; senão, o nome do cupom.

    Nunca uma linha de telefone/SAC do banco, nem a própria empresa (que aparece como quem pagou).
    """
    linhas = _linhas(texto)
    nossa = _nossa_empresa()

    def aceitavel(nome: str) -> bool:
        normal = normalizar(nome)
        return (len(re.findall(r"[a-z]", normal)) >= 4 and not any(r in normal for r in RUIDO_DO_BANCO)
                and not (nossa and (nossa in normal or normal in nossa)) and "prospera" not in normal)

    for linha in linhas[:12]:
        if re.search(r"\bposto\b", normalizar(linha)) and aceitavel(linha):
            return re.sub(r"\s+", " ", linha).strip()[:80]
    if tipo == "compra":
        for linha in linhas:
            m = RE_FAVORECIDO.match(linha)
            if m and aceitavel(m.group(1)):
                return re.sub(r"\s+", " ", m.group(1)).strip(" .")[:80]
    nome = estabelecimento(texto) if texto else ""
    return nome if nome and aceitavel(nome) else ""


def analisar_texto(texto: str, legenda: str = "", hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    conjunto = f"{texto}\n{legenda}"
    itens = itens_do_canhoto(texto)
    litros = litros_do_texto(legenda) or (round(sum(i["litros"] or 0 for i in itens), 2) if itens else None) \
        or litros_do_texto(texto)
    datas = [d for d in (extrair_data(m.group(0)) for m in re.finditer(r"\d{2}\s?/\s?\d{2}\s?/\s?\d{2,4}", texto or ""))
             if d and d <= hoje]
    hora = ""
    m = re.search(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?:[:.\s]\d{2})?(?!\d)", texto or "")
    if m and datas:
        hora = f"{int(m.group(1)):02d}:{m.group(2)}"
    preco = None
    m = RE_PRECO.search(conjunto)
    if m:
        preco = _numero(m.group(1))
    valor = round(sum(i["valor"] or 0 for i in itens), 2) if itens and all(i["valor"] for i in itens) else None
    if not valor:
        valor = valor_total(texto) if texto else None
        if valor and litros and valor <= litros:  # o "total" achado era a quantidade de litros
            valor = None
    if not valor and litros and preco:
        valor = round(litros * preco, 2)
    placa = ""
    m = RE_PLACA.search((conjunto or "").upper())
    if m:
        placa = f"{m.group(1)}-{m.group(2)}"
    medidor = None
    m = RE_MEDIDOR.search(conjunto)
    if m:
        medidor = _numero(m.group(1)) or None
    documento = ""
    m = RE_PEDIDO.search(texto or "")
    if m:
        documento = m.group(1)
    tipo = classificar(texto, legenda, litros)
    if tipo == "compra":  # comprovante de Pix/TED/boleto: o valor é o "valor pago" (no cupom, é o troco que se ignora)
        from ..comprovante import extrair as extrair_pagamento

        pagamento = extrair_pagamento(texto or "")
        valor = pagamento.get("valor_pago") or valor
        if pagamento.get("data_pagamento"):
            datas = [pagamento["data_pagamento"]]
    combustivel = combustivel_do_texto(conjunto) if not itens else (itens[0]["combustivel"] if len(itens) == 1 else "")
    if not itens and (litros or valor):  # canhoto simples, sem a linha do produto legível
        itens = [{"combustivel": combustivel, "descricao": "", "litros": litros, "preco_litro": preco, "valor": valor,
                  "conferido": bool(litros and preco and valor)}]
    posto = _posto(texto, tipo)
    return {
        "tipo": tipo,
        "litros": litros,
        "valor": round(valor, 2) if valor else None,
        "preco_litro": preco if preco else (itens[0]["preco_litro"] if len(itens) == 1 else None),
        "combustivel": combustivel,
        "itens": itens,
        "data": max(datas) if datas else None,
        "hora": hora,
        "posto": posto,
        "documento": documento,
        "placa": placa,
        "medidor": medidor,
        "valores": _valores_do_texto(texto or "")[:5],
    }


def analisar(dados: bytes, nome_arquivo: str = "", legenda: str = "") -> dict:
    """Lê a foto ou o PDF. Gira a foto quando a primeira leitura não acha nem litros nem valor."""
    texto = texto_do_arquivo(dados)
    lido = analisar_texto(texto, legenda)
    if not (lido["litros"] or lido["valor"]):
        girado = texto_do_arquivo(dados, girando=True)
        outro = analisar_texto(girado, legenda)
        lido = {**outro, **{k: v for k, v in lido.items() if v and k != "tipo"}}
        lido["tipo"] = outro["tipo"] or lido.get("tipo") or ""
    return lido

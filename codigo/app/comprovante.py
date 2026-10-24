"""Comprovantes de pagamento: reconhece o comprovante, lê o que foi pago e descobre de qual boleto ou Pix ele é.

1. **É comprovante?** Procura sinais como "comprovante", "valor pago", "data do pagamento", "autenticação",
   "ID da transação" — e sinais de boleto ("local de pagamento", "nosso número"...) para não confundir.
2. **O que foi pago:** valor pago, valor do documento, juros/multa, desconto, data do pagamento, vencimento,
   beneficiário/recebedor, CPF/CNPJ, chave Pix e a linha digitável (quando o banco imprime).
3. **De qual lançamento é:** pontua cada boleto e Pix — linha digitável igual resolve na hora; senão pesa valor,
   CNPJ, nome, vencimento e a data do pagamento. Só registra sozinho quando a escolha é clara; se houver dúvida
   (ex.: parcelas iguais), deixa para alguém escolher.

Juros e desconto: quando o comprovante informa, usa o informado; se o valor pago for diferente do valor do
boleto, a diferença vira juros/multa (pago a mais) ou desconto (pago a menos).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from .boleto.codigo import somente_digitos
from .boleto.texto import RE_CNPJ, RE_CPF, RE_DATA, cnpj_valido, encontrar_codigos, extrair_data, normalizar

RE_MOEDA_OU_ZERO = re.compile(r"(?<![\d,])(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(?!\d)")

SINAIS_COMPROVANTE = (
    "comprovante", "valor pago", "total pago", "pagamento efetuado", "pagamento realizado", "pagamento concluido",
    "transacao efetuada", "transacao realizada", "transacao concluida", "operacao realizada", "data do pagamento",
    "data de pagamento", "data do debito", "data da transacao", "data da operacao", "autenticacao", "id da transacao",
    "id/transacao", "e2e", "end to end", "transferencia realizada", "transferencia enviada", "pix enviado",
    "pix realizado", "pago em", "debitado", "codigo de autenticacao", "numero de controle",
)
SINAIS_BOLETO = (
    "local de pagamento", "pagavel em", "pagavel preferencialmente", "ficha de compensacao", "recibo do pagador",
    "recibo do sacado", "nosso numero", "uso do banco", "especie doc", "data do processamento", "instrucoes",
    "sacador/avalista", "ate o vencimento",
)
PALAVRAS_GENERICAS = {"ltda", "me", "epp", "sa", "s/a", "eireli", "comercio", "comercial", "servicos", "industria",
                      "de", "da", "do", "dos", "das", "e", "cia", "empresa", "grupo", "brasil", "the"}

ROTULO_VALOR_PAGO = r"valor (total )?pago|total pago|valor do pagamento|valor debitado|valor cobrado|valor total|" \
                    r"valor da transferencia|valor do pix|valor da transacao|valor transferido|\(=\)"
ROTULO_VALOR_DOCUMENTO = r"valor (original )?do (documento|boleto|titulo)|valor original|valor nominal|valor do titulo"
ROTULO_JUROS = r"juros|multa|mora|encargos|acrescimo|\(\+\)"
ROTULO_DESCONTO = r"desconto|abatimento|bonificacao|\(-\)"
ROTULO_DATA_PAGAMENTO = (r"data d[oea] (pagamento|debito|transacao|operacao|transferencia|efetivacao|pix)|pago em|"
                         r"realizad[oa] em|efetuad[oa] em|debitado em|data/hora|data e hora|horario")
ROTULO_VENCIMENTO = r"vencimento"
ROTULO_NOME = r"beneficiario( final)?|favorecido|recebedor|destinatario|nome do recebedor|cedente|razao social|^para\b|^destino\b"
ROTULO_CHAVE = r"chave( pix)?\b"
LIMITE_CONFIANCA = 75
MARGEM_CONFIANCA = 20


def _linhas(texto: str) -> list[str]:
    return [re.sub(r"[ \t]+", " ", l).strip() for l in (texto or "").splitlines() if l.strip()]


def _valor(texto: str) -> float | None:
    m = RE_MOEDA_OU_ZERO.search(texto or "")
    return round(float(f"{m.group(1).replace('.', '')}.{m.group(2)}"), 2) if m else None


def _poucas_letras(texto: str) -> bool:
    return len(re.findall(r"[A-Za-zÀ-ÿ]", texto.replace("R$", ""))) <= 3


def _apos_rotulo(linhas: list[str], padrao: str, extrair, janela: int = 2):
    """Valor que vem depois do rótulo: na mesma linha ou nas linhas logo abaixo (leiautes em duas colunas)."""
    for i, linha in enumerate(linhas):
        normal = normalizar(linha)
        m = re.search(padrao, normal)
        if not m:
            continue
        achado = extrair(linha[m.end():])
        if achado not in (None, ""):
            return achado
        for j in range(1, janela + 1):
            if i + j >= len(linhas):
                break
            seguinte = linhas[i + j]
            if extrair in (_valor, extrair_data) and not _poucas_letras(seguinte):
                break
            achado = extrair(seguinte)
            if achado not in (None, ""):
                return achado
    return None


RE_SO_ROTULO = re.compile(r"^(nome|cpf|cnpj|cpf/cnpj|instituicao|banco|agencia|conta|chave( pix)?|dados|tipo|documento|"
                          r"beneficiario|favorecido|recebedor|destino|para)\W*$")


def _nome(texto: str) -> str | None:
    texto = (texto or "").rsplit(":", 1)[-1] if ":" in (texto or "") else (texto or "")
    texto = re.sub(r"^[\s:\-–]+", "", texto)
    if RE_SO_ROTULO.match(normalizar(texto.strip())):
        return None
    texto = RE_CNPJ.sub("", RE_CPF.sub("", texto)).strip(" :-–|")
    if len(re.findall(r"[A-Za-zÀ-ÿ]", texto)) < 3 or re.search(r"\d{4,}", texto):
        return None
    return texto[:80]


def eh_comprovante(texto: str) -> bool:
    normal = normalizar(texto or "")
    sinais = sum(1 for s in SINAIS_COMPROVANTE if s in normal)
    boleto = sum(1 for s in SINAIS_BOLETO if s in normal)
    return sinais >= 2 and sinais > boleto


def extrair(texto: str, codigos: list[str] | None = None, hoje: date | None = None) -> dict:
    """Dados do pagamento a partir do texto do comprovante. Valores em float, datas em ``date``."""
    hoje = hoje or date.today()
    linhas = _linhas(texto)
    normal = normalizar(texto or "")
    codigos = set(codigos or []) | {c.resultado.codigo_barras for c in encontrar_codigos(texto or "") if c.resultado.valido}

    valor_pago = _apos_rotulo(linhas, ROTULO_VALOR_PAGO, _valor)
    valor_documento = _apos_rotulo(linhas, ROTULO_VALOR_DOCUMENTO, _valor)
    juros = desconto = None
    for linha in linhas:
        n = normalizar(linha)
        if re.search(ROTULO_JUROS, n) and not re.search(ROTULO_VALOR_PAGO, n.replace("(+)", "")):
            v = _valor(linha)
            juros = round((juros or 0) + v, 2) if v is not None else juros
        elif re.search(ROTULO_DESCONTO, n):
            v = _valor(linha)
            desconto = round((desconto or 0) + v, 2) if v is not None else desconto
    if valor_pago is None:
        valor_pago = _apos_rotulo(linhas, r"^valor\b|\bvalor:", _valor)
    if valor_pago is None:
        valores = {_valor(m.group(0)) for m in RE_MOEDA_OU_ZERO.finditer(texto or "")} - {None, 0.0}
        if len(valores) == 1:
            valor_pago = valores.pop()

    data_pagamento = _apos_rotulo(linhas, ROTULO_DATA_PAGAMENTO, extrair_data)
    vencimento = _apos_rotulo(linhas, ROTULO_VENCIMENTO, extrair_data)
    if data_pagamento is None:
        datas = []
        for m in RE_DATA.finditer(texto or ""):
            d = extrair_data(m.group(0))
            if d and d <= hoje and d != vencimento:
                datas.append(d)
        data_pagamento = max(datas) if datas else None

    documentos = set()
    for m in list(RE_CNPJ.finditer(texto or "")) + list(RE_CPF.finditer(texto or "")):
        documentos.add(somente_digitos(m.group(0)))
    for m in re.finditer(r"(?<!\d)\d{14}(?!\d)", texto or ""):
        if cnpj_valido(m.group(0)):
            documentos.add(m.group(0))

    pix = bool(re.search(r"\bpix\b", normal))
    return {
        "tipo": "pix" if pix and not codigos else "boleto",
        "codigos": sorted(codigos),
        "valor_pago": valor_pago,
        "valor_documento": valor_documento,
        "juros_multa": juros,
        "desconto": desconto,
        "data_pagamento": data_pagamento,
        "vencimento": vencimento,
        "beneficiario": _apos_rotulo(linhas, ROTULO_NOME, _nome, janela=2),
        "documentos": sorted(documentos),
        "chave_pix": _apos_rotulo(linhas, ROTULO_CHAVE, lambda t: t.strip(" :-")[:80] or None, janela=1) if pix else None,
        "agendado": bool(re.search(r"agendad|agendamento", normal)) and not re.search(r"efetuad|realizad|conclu", normal),
        "texto_normalizado": normal,
    }


ROTULO_PAGADOR = r"pagador|remetente|quem pagou|^pago por\b|^origem\b|^de\b"
ROTULO_ID_TRANSACAO = (r"id d[ae] transacao|id/transacao|identificador|end to end|end-to-end|\be2e\b|"
                       r"codigo d[ae] (transacao|autenticacao)|autenticacao|numero de controle")
RE_E2E = re.compile(r"\bE\d{20}[A-Za-z0-9]{11}\b")  # ID de um Pix (end-to-end), com ou sem rótulo


def _id_transacao(texto: str) -> str | None:
    m = re.search(r"[A-Za-z0-9][A-Za-z0-9.\-/]{5,}", texto or "")
    return m.group(0)[:80] if m and re.search(r"\d", m.group(0)) else None


def pagador(texto: str) -> dict:
    """Quem pagou (nome e CPF/CNPJ do bloco do pagador) e o ID da transação, para ligar o comprovante a uma nota."""
    linhas = _linhas(texto)
    documento = None
    for i, linha in enumerate(linhas):
        if not re.search(ROTULO_PAGADOR, normalizar(linha)):
            continue
        for seguinte in linhas[i:i + 6]:  # o CPF/CNPJ vem logo abaixo do nome, antes do bloco de quem recebeu
            if seguinte is not linha and re.search(ROTULO_NOME, normalizar(seguinte)):
                break
            m = RE_CNPJ.search(seguinte) or RE_CPF.search(seguinte)
            if m:
                documento = somente_digitos(m.group(0))
                break
        break
    e2e = RE_E2E.search(texto or "")
    return {"pagador": _apos_rotulo(linhas, ROTULO_PAGADOR, _nome, janela=2), "documento_pagador": documento,
            "id_transacao": _apos_rotulo(linhas, ROTULO_ID_TRANSACAO, _id_transacao, janela=1) or (e2e.group(0) if e2e else None)}


# --------------------------------------------------------------------------- de qual lançamento é


def _palavras(nome: str) -> set[str]:
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode("ascii").lower()
    return {p for p in re.findall(r"[a-z0-9]+", sem_acento) if len(p) >= 3 and p not in PALAVRAS_GENERICAS}


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return date.fromisoformat(valor[:10])
        except ValueError:
            return None
    return None


def pontuar(extraido: dict, registro: dict, aba: str) -> tuple[int, list[str]]:
    if registro.get("status") == "Cancelado":
        return -999, []
    pontos, motivos = 0, []
    valor = float(registro.get("valor") or 0)
    pago = extraido.get("valor_pago")
    documento_extraido = extraido.get("valor_documento")
    if pago is not None and documento_extraido is None:
        documento_extraido = round(pago - (extraido.get("juros_multa") or 0) + (extraido.get("desconto") or 0), 2)

    if aba == "boletos" and registro.get("codigo_barras") and registro["codigo_barras"] in extraido.get("codigos", []):
        pontos += 100
        motivos.append("linha digitável igual")
    if valor:
        if documento_extraido is not None and abs(documento_extraido - valor) <= 0.01:
            pontos += 40
            motivos.append("mesmo valor")
        elif pago is not None and abs(pago - valor) <= 0.01:
            pontos += 40
            motivos.append("mesmo valor")
        elif pago is not None and valor < pago <= valor * 1.3:
            pontos += 15
            motivos.append("valor com acréscimo")

    docs = set(extraido.get("documentos") or [])
    doc_registro = somente_digitos(registro.get("documento_beneficiario") if aba == "boletos" else registro.get("chave"))
    if doc_registro and len(doc_registro) in (11, 14) and doc_registro in docs:
        pontos += 35
        motivos.append("mesmo CPF/CNPJ")

    if aba == "pix" and registro.get("chave"):
        chave = str(registro["chave"]).lower()
        texto = extraido.get("texto_normalizado") or ""
        if chave in texto or (somente_digitos(chave) and len(somente_digitos(chave)) >= 8
                              and somente_digitos(chave)[-8:] in somente_digitos(texto)):
            pontos += 45
            motivos.append("mesma chave Pix")

    nome = registro.get("recebedor") if aba == "pix" else registro.get("beneficiario")
    palavras_registro = _palavras(nome)
    if palavras_registro:
        alvo = _palavras(extraido.get("beneficiario") or "") or _palavras(extraido.get("texto_normalizado") or "")
        proporcao = len(palavras_registro & alvo) / len(palavras_registro)
        if proporcao >= 0.5:
            pontos += 25
            motivos.append("mesmo beneficiário")
        elif proporcao >= 0.3:
            pontos += 10

    vencimento = _data(registro.get("vencimento"))
    if vencimento and extraido.get("vencimento") and _data(extraido["vencimento"]) == vencimento:
        pontos += 25
        motivos.append("mesmo vencimento")
    pagamento = _data(extraido.get("data_pagamento"))
    if vencimento and pagamento:
        dias = (pagamento - vencimento).days
        if -45 <= dias <= 60:
            pontos += max(0, 10 - abs(dias) // 4)  # a parcela mais próxima da data do pagamento pesa mais
        else:
            pontos -= 25

    if extraido.get("tipo") == "pix" and aba == "boletos" and "linha digitável igual" not in motivos:
        pontos -= 15
    if extraido.get("codigos") and aba == "pix":
        pontos -= 30
    if registro.get("status") == "Pago":
        pontos -= 40 if registro.get("comprovante") else 10
    return pontos, motivos


def candidatos(extraido: dict, boletos: list[dict], pix: list[dict], limite: int = 6) -> list[dict]:
    lista = []
    for aba, registros in (("boletos", boletos), ("pix", pix)):
        for registro in registros:
            if registro.get("id") is None or registro["id"] < 0:
                continue
            pontos, motivos = pontuar(extraido, registro, aba)
            if pontos >= 30:
                lista.append({"aba": aba, "id": registro["id"], "pontos": pontos, "motivos": motivos,
                              "nome": (registro.get("recebedor") if aba == "pix" else registro.get("beneficiario")) or "",
                              "valor": registro.get("valor"), "vencimento": registro.get("vencimento"),
                              "status": registro.get("status"), "tem_comprovante": bool(registro.get("comprovante"))})
    lista.sort(key=lambda c: (-c["pontos"], str(c["vencimento"] or "")))
    return lista[:limite]


def escolher(lista: list[dict]) -> dict | None:
    """O candidato só é aceito sozinho quando se destaca dos demais."""
    if not lista or lista[0]["pontos"] < LIMITE_CONFIANCA:
        return None
    if len(lista) > 1 and lista[0]["pontos"] - lista[1]["pontos"] < MARGEM_CONFIANCA:
        return None
    return lista[0]


def dados_de_pagamento(extraido: dict, registro: dict, hoje: date | None = None) -> dict:
    """Alterações a gravar no lançamento: pago, data, valor pago, juros/multa e desconto."""
    valor = round(float(registro.get("valor") or 0), 2)
    pago = extraido.get("valor_pago")
    pago = round(float(pago), 2) if pago is not None else valor
    diferenca = round(pago - valor, 2) if valor else 0.0
    juros = diferenca if diferenca > 0 else round(float(extraido.get("juros_multa") or 0), 2) if not valor else 0.0
    desconto = -diferenca if diferenca < 0 else round(float(extraido.get("desconto") or 0), 2) if not valor else 0.0
    return {
        "status": "Pago",
        "data_pagamento": _data(extraido.get("data_pagamento")) or hoje or date.today(),
        "valor_pago": pago or None,
        "juros_multa": juros,
        "desconto": desconto,
    }


def publico(extraido: dict) -> dict:
    return {k: v for k, v in extraido.items() if k != "texto_normalizado"}

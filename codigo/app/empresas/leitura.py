"""Leitura dos arquivos que chegam pelo bot de notas: nota fiscal, cheque, comprovante e print do fechamento.

O sistema descobre sozinho **o que é** cada arquivo e tira dele o que interessa:

* **Nota fiscal** — o XML da NF-e é lido campo a campo (jeito mais confiável); o DANFE em PDF ou foto é lido
  pelo texto, item por item (material, unidade, quantidade, valor unitário e total), junto com o número da
  nota, a data, o destinatário e o número do pedido;
* **Cheque** — a linha CMC7 (os números impressos no rodapé) dá banco, agência, conta e número do cheque;
  cooperativa, valor, data e pedidos vêm dos rótulos e da legenda enviada junto no Telegram;
* **Comprovante** de Pix, TED ou depósito — valor, data, hora, pagador, identificador da transação e os
  números das notas fiscais citadas;
* **Print do fechamento** — a tabela do fechamento usado hoje, linha por linha (usado para começar a operar
  com o que já está em andamento).
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

from ..boleto.leitores import abrir_imagem, eh_pdf, ler_pdf, texto_de_segmentos
from ..boleto.ocr import motor_ocr
from ..boleto.texto import RE_CNPJ, extrair_data, normalizar

log = logging.getLogger("leitor_boletos.empresas")

MAX_PAGINAS = 5
UNIDADES = ("M3", "M³", "MC", "TON", "TN", "KG", "UN", "UND", "PC", "PÇ", "SC", "LT", "L", "MT", "M", "CX", "H", "HR")
RE_UNIDADE = re.compile(r"\b(M\s?3|M³|MC|TON|TN|KG|UND?|PC|PÇ|SC|LT|MT|CX|HR?|L|M)\b", re.I)
RE_NUMERO = re.compile(r"(?<![\d,.])(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\d])")
RE_NF = re.compile(r"\b(?:nfe?|nf-?e|nota\s*fiscal|nota|cupom)\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,9})", re.I)
RE_PEDIDO = re.compile(r"\b(?:pedido|ped\.?|pdd|oc)\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,9})", re.I)
RE_CMC7 = re.compile(r"(?<!\d)(\d{8})\D{0,4}(\d{10})\D{0,4}(\d{12})(?!\d)")
RE_CMC7_CORRIDO = re.compile(r"(?<!\d)(\d{30})(?!\d)")
# Comprovante do banco de um depósito de cheque(s): traz a CMC-7 do cheque, mas não é a foto do cheque
RE_DEPOSITO_DE_CHEQUE = re.compile(r"deposito[^.\n]{0,40}cheque|cheques?\s+depositad|comprovante de deposito|"
                                   r"valor do deposito|deposito (em|com) cheque")

BANCOS = {
    "001": "Banco do Brasil", "003": "Banco da Amazônia", "004": "Banco do Nordeste", "021": "Banestes",
    "033": "Santander", "037": "Banpará", "041": "Banrisul", "047": "Banese", "070": "BRB", "077": "Banco Inter",
    "085": "Ailos", "097": "Credisis", "099": "Uniprime", "104": "Caixa Econômica Federal", "133": "Cresol",
    "136": "Unicred", "212": "Banco Original", "237": "Bradesco", "246": "ABC Brasil", "260": "Nubank",
    "290": "PagBank", "318": "Banco BMG", "336": "C6 Bank", "341": "Itaú", "356": "Real", "389": "Mercantil",
    "399": "HSBC", "422": "Safra", "604": "Banco Industrial", "633": "Rendimento", "637": "Sofisa",
    "652": "Itaú Unibanco", "655": "Votorantim", "745": "Citibank", "748": "Sicredi", "756": "Sicoob",
}

SINAIS_NOTA = ("danfe", "documento auxiliar da nota fiscal", "nota fiscal eletronica", "chave de acesso",
               "natureza da operacao", "dados do produto", "destinatario/remetente", "valor total da nota",
               "protocolo de autorizacao", "inscricao estadual")
SINAIS_CHEQUE = ("compensavel", "compense", "cheque", "pague por este cheque", "quantia de", "ordem de",
                 "banco cooperativo", "acima ou a sua ordem", "c1", "bom para")
SINAIS_COMPROVANTE = ("comprovante", "transferencia", "pix", "ted", "doc", "deposito", "valor pago",
                      "id da transacao", "autenticacao", "e2e", "recibo")
SINAIS_FECHAMENTO = ("fechamento", "valor uni", "valor total", "n pedido", "nota fical", "nota fiscal", "material")


# --------------------------------------------------------------------------- texto do arquivo


def texto_do_arquivo(dados: bytes, max_paginas: int = MAX_PAGINAS, girando: bool = False) -> str:
    """Texto de um PDF (camada de texto) ou de uma imagem/scan (OCR).

    ``girando=True``: lê a mesma página nas quatro orientações e junta tudo. Foto de cheque quase sempre está
    deitada ou de cabeça para baixo, e cada giro revela um pedaço (o "bom para" à mão, os pedidos do verso...).
    """
    if eh_pdf(dados):
        paginas, _ = ler_pdf(dados, max_paginas=max_paginas, escala_maxima=6.0 if girando else 3.0,
                             lado_render=3500 if girando else 3000)
        partes = []
        for pagina in paginas:
            texto = pagina.texto or ""
            se_precisa_ocr = sum(c.isalnum() for c in texto) < 60
            if (girando or se_precisa_ocr) and pagina.imagem is not None and motor_ocr.disponivel:
                lido = _ocr_em_todas_as_orientacoes(pagina.imagem, pagina.indice) if girando \
                    else texto_de_segmentos(motor_ocr.reconhecer(pagina.imagem, pagina.indice))
                texto = f"{texto}\n{lido}" if texto and girando else lido
            partes.append(texto)
        return "\n".join(partes)
    if not motor_ocr.disponivel:
        return ""
    imagem = abrir_imagem(dados)
    if girando:
        return _ocr_em_todas_as_orientacoes(imagem, 0)
    return texto_de_segmentos(motor_ocr.reconhecer(imagem, 0))


def _ocr_em_todas_as_orientacoes(imagem, indice: int) -> str:
    """Lê a imagem de pé, deitada para os dois lados e de cabeça para baixo, e junta as linhas (sem repetir)."""
    linhas: dict[str, None] = {}
    for angulo in (0, 90, 180, 270):
        girada = imagem.rotate(angulo, expand=True, fillcolor="white") if angulo else imagem
        for linha in texto_de_segmentos(motor_ocr.reconhecer(girada, indice)).splitlines():
            if linha.strip():
                linhas.setdefault(linha.strip(), None)
    return "\n".join(linhas)


def eh_xml(dados: bytes) -> bool:
    inicio = dados[:400].lstrip()
    return inicio.startswith(b"<?xml") or inicio.startswith(b"<nfeProc") or inicio.startswith(b"<NFe")


# --------------------------------------------------------------------------- classificação


def _pontos(normal: str, sinais) -> int:
    return sum(1 for s in sinais if s in normal)


def eh_deposito_de_cheque(normal: str) -> bool:
    """``normal``: texto já normalizado (sem acento, minúsculo)."""
    return bool(RE_DEPOSITO_DE_CHEQUE.search(normal))


def classificar(texto: str, nome_arquivo: str = "", legenda: str = "") -> str:
    """O que é o arquivo: ``nota``, ``cheque``, ``comprovante``, ``fechamento`` ou "" (não reconhecido)."""
    normal = normalizar(f"{texto}\n{nome_arquivo}\n{legenda}")
    nota = _pontos(normal, SINAIS_NOTA)
    cheque = _pontos(normal, SINAIS_CHEQUE) + (2 if RE_CMC7.search(texto or "") or RE_CMC7_CORRIDO.search(texto or "") else 0)
    comprovante = _pontos(normal, SINAIS_COMPROVANTE)
    fechamento = _pontos(normal, SINAIS_FECHAMENTO) + (2 if "fechamento" in normal else 0)
    if "danfe" in normal or "documento auxiliar da nota fiscal" in normal:
        nota += 3
    if "comprovante" in normal and nota < 3:
        comprovante += 2
    if eh_deposito_de_cheque(normal):  # é o comprovante do depósito, não o cheque em si
        return "comprovante"
    placar = {"nota": nota, "cheque": cheque, "comprovante": comprovante, "fechamento": fechamento}
    melhor = max(placar, key=lambda k: placar[k])
    return melhor if placar[melhor] >= 2 else ""


# --------------------------------------------------------------------------- números soltos


def _numero(texto: str) -> float | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    limpo = texto.replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") > 1:
        limpo = limpo.replace(".", "")
    try:
        return float(limpo)
    except ValueError:
        return None


def _sequencia(padrao: re.Pattern, texto: str) -> list[str]:
    """Números que vêm depois do rótulo, inclusive os da mesma lista ("NF 6859, 6869 e 6870")."""
    encontrados: list[str] = []
    for m in padrao.finditer(texto or ""):
        encontrados.append(m.group(1))
        resto = (texto or "")[m.end():m.end() + 80]
        while True:
            seguinte = re.match(r"[\s,;/]+(?:e\s+)?(\d{1,9})", resto)
            if not seguinte:
                break
            encontrados.append(seguinte.group(1))
            resto = resto[seguinte.end():]
    return [n.lstrip("0") or n for n in dict.fromkeys(encontrados)]


def numeros_de_nf(texto: str) -> list[str]:
    """Números de nota fiscal citados no texto (ex.: "NF 6859 e 6869", "notas 6859/6869")."""
    return _sequencia(RE_NF, texto)


def numeros_de_pedido(texto: str) -> list[str]:
    return _sequencia(RE_PEDIDO, texto)


# --------------------------------------------------------------------------- nota fiscal (XML)


def _sem_ns(tag: str) -> str:
    return tag.split("}")[-1]


def _achar(no, caminho: str):
    """Busca por nomes de tag, ignorando o namespace da NF-e."""
    atual = [no]
    for parte in caminho.split("/"):
        seguinte = []
        for elemento in atual:
            seguinte += [f for f in elemento if _sem_ns(f.tag) == parte]
        atual = seguinte
        if not atual:
            return []
    return atual


def _texto(no, caminho: str, padrao: str = "") -> str:
    achados = _achar(no, caminho)
    return (achados[0].text or "").strip() if achados else padrao


def ler_xml_nota(dados: bytes) -> dict | None:
    """Lê o XML de uma NF-e: emitente, destinatário, itens e pedidos."""
    try:
        raiz = ET.fromstring(dados)
    except ET.ParseError:
        return None
    nfe = _achar(raiz, "NFe/infNFe") or _achar(raiz, "infNFe")
    if not nfe:
        nfe = [raiz] if _sem_ns(raiz.tag) == "infNFe" else []
    if not nfe:
        return None
    info = nfe[0]
    emissao = _texto(info, "ide/dhEmi") or _texto(info, "ide/dEmi")
    try:
        data = date.fromisoformat(emissao[:10]) if emissao else None
    except ValueError:
        data = None
    itens = []
    for det in _achar(info, "det"):
        prod = _achar(det, "prod")
        if not prod:
            continue
        p = prod[0]
        itens.append({
            "material": _texto(p, "xProd"),
            "unidade": (_texto(p, "uCom") or "").upper()[:10],
            "quantidade": _numero(_texto(p, "qCom")) or 0,
            "valor_unitario": _numero(_texto(p, "vUnCom")) or 0,
            "valor_total": _numero(_texto(p, "vProd")) or 0,
            "pedido": re.sub(r"\D", "", _texto(p, "xPed"))[:9],
        })
    complementares = _texto(info, "infAdic/infCpl")
    pedidos = [i["pedido"] for i in itens if i["pedido"]] or numeros_de_pedido(complementares)
    return {
        "origem": "xml",
        "numero_nf": (_texto(info, "ide/nNF") or "").lstrip("0"),
        "serie": _texto(info, "ide/serie"),
        "data": data,
        "emitente": {"nome": _texto(info, "emit/xNome"), "cnpj": _texto(info, "emit/CNPJ")},
        "destinatario": {"nome": _texto(info, "dest/xNome"),
                         "cnpj": _texto(info, "dest/CNPJ") or _texto(info, "dest/CPF")},
        "valor_total": _numero(_texto(info, "total/ICMSTot/vNF")) or round(sum(i["valor_total"] for i in itens), 2),
        "itens": itens,
        "pedidos": list(dict.fromkeys(pedidos)),
        "observacoes": complementares[:300],
        "confianca": 1.0,
    }


# --------------------------------------------------------------------------- nota fiscal (DANFE em PDF ou foto)


def _linhas(texto: str) -> list[str]:
    return [re.sub(r"[ \t]+", " ", l).strip() for l in (texto or "").splitlines() if l.strip()]


def _rotulo(linhas: list[str], padrao: str, janela: int = 2) -> str:
    """Conteúdo que vem depois de um rótulo (na mesma linha ou logo abaixo, como no DANFE)."""
    for i, linha in enumerate(linhas):
        m = re.search(padrao, normalizar(linha))
        if not m:
            continue
        resto = linha[m.end():].strip(" :.-")
        if resto:
            return resto
        for j in range(1, janela + 1):
            if i + j < len(linhas) and linhas[i + j].strip():
                return linhas[i + j].strip()
    return ""


def _itens_do_texto(texto: str) -> list[dict]:
    """Itens do DANFE: depois da unidade vêm quantidade, valor unitário e valor total."""
    itens = []
    for linha in _linhas(texto):
        if len(linha) < 12 or normalizar(linha).startswith(("codigo", "descricao", "dados do produto")):
            continue
        m = RE_UNIDADE.search(linha)
        if not m:
            continue
        depois = linha[m.end():]
        numeros = [n for n in (_numero(x.group(1)) for x in RE_NUMERO.finditer(depois)) if n is not None]
        if len(numeros) < 3:
            continue
        quantidade, unitario, total = numeros[0], numeros[1], numeros[2]
        if not quantidade or not total or abs(quantidade * unitario - total) > max(0.05, total * 0.02):
            continue
        descricao = linha[:m.start()].strip(" .-")
        descricao = re.sub(r"^[\d.\-]{1,14}\s+", "", descricao)  # código do produto na frente da descrição
        descricao = re.sub(r"\s+\d{8}(\s+\d{2,4})*$", "", descricao)  # NCM/CST/CFOP no fim
        if len(re.findall(r"[A-Za-zÀ-ÿ]", descricao)) < 2:
            descricao = ""  # sobrou só número: o nome do material vai ser conferido na tela
        itens.append({
            "material": descricao[:80],
            "unidade": m.group(1).upper().replace(" ", "").replace("M3", "M³"),
            "quantidade": round(quantidade, 4),
            "valor_unitario": round(unitario, 4),
            "valor_total": round(total, 2),
            "pedido": "",
        })
    return itens


RE_SO_ROTULO = re.compile(r"^(nome|razao social|nome/razao social|cnpj|cpf|cnpj/cpf|endereco|municipio|uf|fone|fax|"
                          r"bairro|distrito|cep|inscricao estadual|data da emissao|data de emissao|destinatario.*|"
                          r"identificacao do emitente|natureza da operacao|hora de saida|data de saida)\W*$")


def _bloco_do_destinatario(linhas: list[str]) -> list[str]:
    for i, linha in enumerate(linhas):
        if "destinatario" in normalizar(linha):
            return linhas[i + 1:i + 12]
    return []


def _nome_de_empresa(linha: str) -> str:
    """Nome de empresa numa linha do DANFE (sem o CNPJ colado e sem confundir com o rótulo)."""
    limpo = re.sub(r"\s*\d{2}\.?\d{3}\.?\d{3}\s?/\s?\d{4}-?\d{2}.*$", "", linha or "").strip(" :-|")
    if RE_SO_ROTULO.match(normalizar(limpo)) or len(re.findall(r"[A-Za-z\u00c0-\u00ff]", limpo)) < 5:
        return ""
    return limpo[:80]


def _numero_pela_chave(texto: str) -> str:
    """Chave de acesso da NF-e (44 dígitos): as posições 26 a 34 são o número da nota — sem chance de erro."""
    for m in re.finditer(r"(?<!\d)((?:\d[\s.\-]{0,2}){44})(?!\d)", texto or ""):
        chave = re.sub(r"\D", "", m.group(1))
        if len(chave) != 44:
            continue
        numero = chave[25:34].lstrip("0")
        if numero:
            return numero
    return ""


def extrair_nota(texto: str) -> dict:
    """Dados de um DANFE lido em PDF ou foto (melhor esforço: a tela mostra tudo para conferência)."""
    linhas = _linhas(texto)
    numero_nf = _numero_pela_chave(texto)
    if not numero_nf:
        m = re.search(r"n[ºo°.]?\s*[:\-]?\s*((?:\d{1,3}[. ]){0,3}\d{1,9})\s*(?:serie|série)", normalizar(texto))
        if m:
            numero_nf = re.sub(r"\D", "", m.group(1))[-9:]
    if not numero_nf:
        candidatos = [n for n in numeros_de_nf(texto) if len(n) <= 9]
        numero_nf = candidatos[0] if candidatos else ""
    data = extrair_data(_rotulo(linhas, r"data (de |da )?emissao")) or None
    if not data:
        datas = [extrair_data(l) for l in linhas if re.search(r"\d{2}/\d{2}/\d{4}", l)]
        data = next((d for d in datas if d), None)

    documentos = [re.sub(r"\D", "", m.group(0)) for m in RE_CNPJ.finditer(texto or "")]
    bloco = _bloco_do_destinatario(linhas)
    destinatario_nome = next((n for n in (_nome_de_empresa(l) for l in bloco) if n), "")
    doc_destinatario = [re.sub(r"\D", "", m.group(0)) for l in bloco for m in RE_CNPJ.finditer(l)] or documentos[1:2]
    if not destinatario_nome:
        destinatario_nome = _nome_de_empresa(_rotulo(linhas, r"^(nome/razao social|destinatario|cliente)\b"))

    itens = _itens_do_texto(texto)
    total = _numero(_rotulo(linhas, r"valor total da nota")) or round(sum(i["valor_total"] for i in itens), 2)
    pedidos = numeros_de_pedido(texto)
    return {
        "origem": "texto",
        "numero_nf": (numero_nf or "").lstrip("0"),
        "serie": "",
        "data": data,
        "emitente": {"nome": (linhas[0] if linhas else "")[:80], "cnpj": documentos[0] if documentos else ""},
        "destinatario": {"nome": (destinatario_nome or "")[:80], "cnpj": doc_destinatario[0] if doc_destinatario else ""},
        "valor_total": total,
        "itens": itens,
        "pedidos": pedidos,
        "observacoes": "",
        "confianca": 0.9 if itens and numero_nf and total else 0.5 if itens or numero_nf else 0.2,
    }


# --------------------------------------------------------------------------- cheque

RE_MOEDA_TOLERANTE = re.compile(r"(?<![\d,.])(\d{1,3}(?:[.\s]\d{3})*|\d+)[.,](\d{2})(?![\d])")
# O OCR troca letras por números em texto à mão: "24lo9126" é "24/09/26"
CONFUSOES_OCR = str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1", "S": "5", "s": "5", "B": "8", "Z": "2"})


def _valores_do_texto(texto: str) -> list[float]:
    """Valores em reais aceitando o ponto como separador decimal (o OCR troca a vírgula do cheque)."""
    achados = []
    for m in RE_MOEDA_TOLERANTE.finditer(texto or ""):
        inteiro = re.sub(r"[.\s]", "", m.group(1))
        try:
            achados.append(round(float(f"{inteiro}.{m.group(2)}"), 2))
        except ValueError:
            continue
    return achados


def _data_escrita_a_mao(trecho: str, hoje: date | None = None) -> date | None:
    """Data escrita à mão (ex.: "Bom p/ 24/09/26") lida de um trecho com ruído de OCR.

    Testa as combinações dia/mês/ano do trecho, pulando até um caractere perdido entre elas, e fica com a data
    que faz sentido para um cheque: de 3 meses atrás até 18 meses à frente, a mais próxima de hoje.
    """
    hoje = hoje or date.today()
    digitos = re.sub(r"\D", "", (trecho or "").translate(CONFUSOES_OCR))
    if len(digitos) < 6:
        return None
    candidatas = []
    for inicio in range(min(len(digitos) - 5, 6)):
        for salto1 in (0, 1):
            for salto2 in (0, 1):
                meio = inicio + 2 + salto1
                fim = meio + 2 + salto2
                for tamanho in (2, 4):
                    pedaco = digitos[fim:fim + tamanho]
                    if len(pedaco) < tamanho:
                        continue
                    try:
                        ano = int(pedaco)
                        achada = date(ano + 2000 if ano < 100 else ano, int(digitos[meio:meio + 2]),
                                      int(digitos[inicio:inicio + 2]))
                    except ValueError:
                        continue
                    if timedelta(days=-90) <= achada - hoje <= timedelta(days=550):
                        candidatas.append((abs((achada - hoje).days), achada))
    return min(candidatas)[1] if candidatas else None


def _perto_do_rotulo(texto: str, rotulo: str, padrao: str) -> str:
    """Valor que aparece **antes ou depois** do rótulo (o OCR de cheque inverte a ordem com frequência)."""
    for linha in _linhas(texto):
        normal = normalizar(linha)
        for m in re.finditer(rotulo, normal):
            depois = re.match(rf"[^\d]{{0,8}}({padrao})", linha[m.end():])
            if depois:
                return depois.group(1)
            antes = re.search(rf"({padrao})[^\d]{{0,8}}$", linha[:m.start()])
            if antes:
                return antes.group(1)
    return ""


def ler_cmc7(texto: str) -> dict:
    """Números impressos no rodapé do cheque (CMC7): banco, agência, conta e número do cheque.

    Leiaute (padrão Febraban): campo 1 (8) = banco (3) + agência (4) + dígito; campo 2 (10) = compensação (3) +
    número do cheque (6) + tipificação (1); campo 3 (12) = dígito + conta corrente (10) + dígito.
    Ex.: ``74880585 0180006165 400000989483`` = Sicredi, agência 8058, cheque 616, conta 98948.
    """
    todos = ler_todos_cmc7(texto)
    return todos[0] if todos else {}


def _campos_cmc7(campo1: str, campo2: str, campo3: str) -> dict:
    banco = campo1[:3]
    return {
        "cmc7": f"{campo1}{campo2}{campo3}",
        "banco_codigo": banco,
        "banco": BANCOS.get(banco, f"Banco {banco}"),
        "agencia": campo1[3:7],
        "numero": campo2[3:9].lstrip("0") or campo2[3:9],
        "conta": campo3[1:11].lstrip("0") or campo3[1:11],
    }


def ler_todos_cmc7(texto: str) -> list[dict]:
    """Todas as linhas CMC-7 do texto (um depósito pode ter vários cheques), sem repetir."""
    limpo = re.sub(r"[^\d<:;.\s]", "", texto or "")
    achados = [_campos_cmc7(*m.groups()) for m in RE_CMC7.finditer(limpo)]
    if not achados:
        achados = [_campos_cmc7(i[:8], i[8:18], i[18:])
                   for i in (m.group(1) for m in RE_CMC7_CORRIDO.finditer(re.sub(r"[^\d\n]", "", limpo)))]
    return list({c["cmc7"]: c for c in achados}.values())


def extrair_cheque(texto: str, legenda: str = "") -> dict:
    """Tudo o que dá para ler de um cheque escaneado, somado ao que veio escrito na mensagem.

    A linha CMC7 (os números do rodapé) resolve banco, agência, conta e número quando aparece. Como em foto ela
    quase nunca sai inteira, cada campo também é procurado pelo rótulo impresso — o valor pode estar **antes ou
    depois** do rótulo, porque o OCR lê as caixinhas do cheque fora de ordem.
    """
    conjunto = f"{texto}\n{legenda}"
    normal = normalizar(conjunto)
    dados = ler_cmc7(texto)

    dados["coop"] = dados.get("coop") or _perto_do_rotulo(conjunto, r"\bcoop(erativa)?\b", r"\d{3,6}")
    if not dados.get("agencia"):
        dados["agencia"] = _perto_do_rotulo(conjunto, r"\bag(encia)?\b", r"\d{3,6}")
    if not dados.get("conta"):
        conta = _perto_do_rotulo(conjunto, r"\bconta\b|\bc/c\b", r"[\d][\d .-]{3,14}")
        dados["conta"] = re.sub(r"\D", "", conta)[:12]
    if not dados.get("numero"):
        numero_cheque = _perto_do_rotulo(conjunto, r"\bcheque\s*n|\bn[uú]mero do cheque", r"[\d][\d ]{3,10}")
        dados["numero"] = (re.sub(r"\D", "", numero_cheque).lstrip("0") or "")[:10]
    if not dados.get("banco"):
        codigo = _perto_do_rotulo(conjunto, r"\bbanco\b", r"\d{3}")
        for chave, nome in BANCOS.items():
            if normalizar(nome) in normal or chave == codigo:
                dados.update(banco=nome, banco_codigo=chave)
                break

    # valor: o cheque imprime entre "#", e o OCR costuma trocar a vírgula por ponto ("#4.287.60#")
    entre_cerquilhas = [valor for m in re.finditer(r"#\s*([\d.,\s]+?)\s*[#*]", conjunto)
                        for valor in _valores_do_texto(m.group(1))]
    valores = entre_cerquilhas or _valores_do_texto(conjunto)
    valor = max(valores) if valores else None

    # "bom para": a data do depósito, escrita à mão no canto do cheque
    vencimento = None
    for m in re.finditer(r"\b[bp]om\s*p|bom para|data (de |do )?deposito|deposit(ar|o) em", normal):
        vencimento = _data_escrita_a_mao(conjunto[m.end():m.end() + 40])
        if vencimento:
            break
    if not vencimento:  # o cheque também traz a data por extenso, e a legenda pode dizer "bom para 24/09"
        for pedaco in re.findall(r"\d{1,2}\s?[/.\-]\s?\d{1,2}\s?[/.\-]?\s?\d{0,4}", conjunto):
            vencimento = _data_escrita_a_mao(pedaco) or vencimento
            if vencimento:
                break

    documentos = [re.sub(r"\D", "", m.group(0)) for m in RE_CNPJ_SOLTO.finditer(conjunto)]
    emitente = _emitente_do_cheque(conjunto)
    pedidos = list(dict.fromkeys(numeros_de_pedido(conjunto) + _numeros_em_sequencia(conjunto)))
    completos = sum(1 for v in (dados.get("numero"), dados.get("conta"), valor, vencimento) if v)
    return {
        **dados,
        "valor": round(valor, 2) if valor else None,
        "vencimento": vencimento,
        "emitente": emitente,
        "documentos": documentos,
        "pedidos": pedidos,
        "notas": numeros_de_nf(conjunto),
        "confianca": round(min(1.0, 0.25 * completos + (0.2 if dados.get("cmc7") else 0)), 2),
    }


DISTANCIA_ENTRE_PEDIDOS = 200  # pedidos do mesmo cliente saem numerados de perto
RE_CNPJ_SOLTO = re.compile(r"(?<!\d)\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-–\s]?\d{2}(?!\d)")
RE_RAZAO_SOCIAL = re.compile(r"([A-ZÀ-Ý][A-Za-zÀ-ý&.\-]{1,20}(?:\s+[A-Za-zÀ-ý&.\-]{1,20}){0,5}\s+"
                             r"(?:LTDA|EIRELI|EPP|S/?A|ME)\b)", re.I)
PALAVRAS_DE_BANCO = ("banco", "sicredi", "sicoob", "coop", "credito", "cred ", "caixa", "bradesco", "itau",
                     "santander", "cliente bancario")


def _emitente_do_cheque(texto: str) -> str:
    """Nome de quem assinou o cheque: o nome de empresa que mais aparece e não é do banco."""
    contagem: dict[str, int] = {}
    for linha in _linhas(texto):
        for m in RE_RAZAO_SOCIAL.finditer(linha):
            nome = re.sub(r"\s+", " ", m.group(1)).strip(" .-")
            if len(nome) < 8 or any(p in normalizar(nome) for p in PALAVRAS_DE_BANCO):
                continue
            contagem[nome] = contagem.get(nome, 0) + 1
    if not contagem:
        return ""
    return max(contagem.items(), key=lambda item: (item[1], len(item[0])))[0][:80]


def _numeros_em_sequencia(texto: str) -> list[str]:
    """Lista de pedidos escrita à mão no verso: "7200-7201-7219-7245-7255" em uma ou várias linhas.

    O cheque também tem números soltos (conta, cooperativa, endereço). Como os pedidos de um mesmo cliente saem
    em sequência, fica só o maior grupo de números próximos entre si — o resto é descartado.
    """
    candidatos: list[int] = []
    for linha in _linhas(texto):
        numeros = [int(n) for n in re.findall(r"(?<!\d)(\d{4})(?!\d)", linha)]
        if len(numeros) >= 2:
            candidatos += [n for n in numeros if not 1900 <= n <= 2100]  # anos não são pedidos
    if len(candidatos) < 3:
        return []
    grupos: list[list[int]] = [[]]
    for numero in sorted(set(candidatos)):
        if grupos[-1] and numero - grupos[-1][-1] > DISTANCIA_ENTRE_PEDIDOS:
            grupos.append([])
        grupos[-1].append(numero)
    maior = max(grupos, key=len)
    return [str(n) for n in maior] if len(maior) >= 3 else []


# --------------------------------------------------------------------------- comprovante de recebimento


def extrair_comprovante(texto: str, legenda: str = "") -> dict:
    """Comprovante de Pix, TED ou depósito: valor, data, hora, pagador, identificador e notas citadas."""
    from .. import comprovante as comprovante_pagamento

    conjunto = f"{texto}\n{legenda}"
    lido = comprovante_pagamento.extrair(texto or "")
    normal = normalizar(conjunto)
    forma = "Pix" if "pix" in normal else "TED" if re.search(r"\bted\b|transferencia", normal) else \
        "Depósito" if "deposito" in normal else "Cheque" if "cheque" in normal else "Pix"
    hora = ""
    m = re.search(r"(\d{1,2}):(\d{2})(?::\d{2})?", conjunto)
    if m:
        hora = f"{int(m.group(1)):02d}:{m.group(2)}"
    identificador = ""
    for padrao in (r"(?:id|identificador|autentica[cç][aã]o|e2e|controle)[^\w]{0,12}([A-Za-z0-9]{8,40})",
                   r"\b(E\d{8,}[A-Za-z0-9]{6,})\b"):
        m = re.search(padrao, conjunto, re.I)
        if m:
            identificador = m.group(1)
            break
    valor = lido.get("valor_pago")
    deposito_de_cheque = eh_deposito_de_cheque(normal)
    if valor is None and deposito_de_cheque:
        rotulado = _perto_do_rotulo(conjunto, r"valor (do|total do)? ?deposito", r"\d{1,3}(?:\.\d{3})*,\d{2}")
        valor = _numero(rotulado) if rotulado else None
    if valor is None:
        valores = [v for v in (_numero(x.group(1)) for x in re.finditer(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})", conjunto)) if v]
        if not valores and deposito_de_cheque:
            valores = _valores_do_texto(conjunto)
        valor = max(valores) if valores else None
    data = lido.get("data_pagamento")
    if data is None and deposito_de_cheque:
        rotulada = _perto_do_rotulo(conjunto, r"\bdata\b", r"\d{2}/\d{2}/\d{4}")
        data = extrair_data(rotulada) if rotulada else None
    if deposito_de_cheque:
        forma = "Cheque"
        transacao = re.search(r"n\.?\s*trans\.?\s*:?\s*(\d{3,12})", conjunto, re.I)
        identificador = identificador or (transacao.group(1) if transacao else "")
    return {
        "deposito_cheque": deposito_de_cheque,
        "cheques": ler_todos_cmc7(texto) if deposito_de_cheque else [],
        "forma": forma,
        "valor": round(float(valor), 2) if valor else None,
        "data": data,
        "hora": hora,
        "pagador": _pagador(texto) or "",
        "id_transacao": identificador,
        "notas": numeros_de_nf(conjunto),
        "pedidos": numeros_de_pedido(conjunto),
        "documentos": lido.get("documentos") or [],
        "agendado": bool(lido.get("agendado")),
        "confianca": 0.9 if valor and data else 0.6 if valor else 0.3,
    }


def _pagador(texto: str) -> str:
    linhas = _linhas(texto)
    nome = _rotulo(linhas, r"\b(pagador|origem|de:|remetente|debitado de|quem pagou|cliente)\b", janela=2)
    nome = re.sub(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", "", nome)
    nome = re.sub(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", "", nome).strip(" :-|")
    return nome[:80] if len(re.findall(r"[A-Za-zÀ-ÿ]", nome)) >= 3 else ""


# --------------------------------------------------------------------------- print do fechamento (Parte 5)


RE_LINHA_FECHAMENTO = re.compile(
    r"^(?P<data>\d{1,2}\s?/\s?\d{1,2}\s?/\s?\d{2,4})\s+(?P<material>.+?)\s+(?P<unidade>M\s?[3³]|MC|TON|TN|KG|UND?|PC|SC|LT|CX)\s+"
    r"(?P<quantidade>[\d.,]+)\s+(?P<unitario>[\d.,]+)\s+R?\$?\s*(?P<total>[\d.,]+)\s+(?P<nf>\d{2,9})\s+(?P<pedido>\d{2,9})\s*$",
    re.I)


def ler_fechamento(texto: str) -> dict:
    """Lê o print (ou o texto colado) de um fechamento já existente, linha por linha."""
    linhas_lidas, ignoradas = [], []
    empresa = ""
    for bruta in _linhas(texto):
        linha = bruta.replace("|", " ")
        linha = re.sub(r"\s+", " ", linha).strip()
        normal = normalizar(linha)
        if not empresa and normal.startswith("fechamento"):
            empresa = re.sub(r"^fechamento\s*[:\-]?\s*", "", linha, flags=re.I).strip()[:60]
            continue
        m = RE_LINHA_FECHAMENTO.match(linha)
        if not m:
            if re.match(r"^\d{1,2}\s?/\s?\d{1,2}\s?/\s?\d{2,4}\b", linha):
                ignoradas.append(bruta)
            continue
        data = extrair_data(m.group("data"))
        quantidade = _numero(m.group("quantidade")) or 0
        unitario = _numero(m.group("unitario")) or 0
        total = _numero(m.group("total")) or 0
        if not total and quantidade and unitario:
            total = round(quantidade * unitario, 2)
        if not total:
            ignoradas.append(bruta)
            continue
        linhas_lidas.append({
            "data": data,
            "material": m.group("material").strip(" .-")[:80],
            "unidade": m.group("unidade").upper().replace(" ", "").replace("M3", "M³"),
            "quantidade": round(quantidade, 4) or None,
            "valor_unitario": round(unitario, 4) or None,
            "valor_total": round(total, 2),
            "numero_nf": m.group("nf").lstrip("0"),
            "pedido": m.group("pedido").lstrip("0"),
        })
    return {
        "empresa": empresa,
        "linhas": linhas_lidas,
        "ignoradas": ignoradas[:20],
        "total": round(sum(l["valor_total"] for l in linhas_lidas), 2),
    }


# --------------------------------------------------------------------------- entrada única


def analisar(dados: bytes, nome_arquivo: str = "", legenda: str = "") -> dict:
    """Lê um arquivo recebido e devolve ``{"tipo": ..., "dados": {...}, "texto": ...}``."""
    if eh_xml(dados) or (nome_arquivo or "").lower().endswith(".xml"):
        nota = ler_xml_nota(dados)
        if nota:
            return {"tipo": "nota", "dados": nota, "texto": ""}
    texto = texto_do_arquivo(dados)
    tipo = classificar(texto, nome_arquivo, legenda)
    if tipo == "cheque" or not tipo:
        # Cheque é foto: quase sempre está deitado, e o "bom para" e os pedidos do verso só saem girando a imagem
        detalhado = texto_do_arquivo(dados, girando=True)
        if len(detalhado) > len(texto) * 0.8:
            texto = detalhado
            tipo = classificar(texto, nome_arquivo, legenda) or tipo
    if tipo == "nota":
        return {"tipo": "nota", "dados": extrair_nota(texto), "texto": texto}
    if tipo == "cheque":
        return {"tipo": "cheque", "dados": extrair_cheque(texto, legenda), "texto": texto}
    if tipo == "comprovante":
        lido = extrair_comprovante(texto, legenda)
        if not (lido.get("valor") and lido.get("data")):
            # foto do comprovante tirada deitada: a data e o valor só saem lendo a imagem girada
            detalhado = texto_do_arquivo(dados, girando=True)
            if len(detalhado) > len(texto) * 0.8:
                outro = extrair_comprovante(detalhado, legenda)
                if sum(bool(outro.get(c)) for c in ("valor", "data")) >= sum(bool(lido.get(c)) for c in ("valor", "data")):
                    texto, lido = detalhado, outro
        return {"tipo": "comprovante", "dados": lido, "texto": texto}
    if tipo == "fechamento":
        return {"tipo": "fechamento", "dados": ler_fechamento(texto), "texto": texto}
    return {"tipo": "", "dados": {}, "texto": texto}


def publico(analise: dict) -> dict:
    """Formato devolvido para a tela (datas em texto, sem o texto bruto do arquivo)."""
    def converter(valor):
        if isinstance(valor, (date, datetime)):
            return valor.isoformat()[:10]
        if isinstance(valor, dict):
            return {k: converter(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [converter(v) for v in valor]
        return valor

    return {"tipo": analise.get("tipo") or "", "dados": converter(analise.get("dados") or {})}

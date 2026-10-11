"""Pix: tipos de chave, validação, leitura e geração do "Pix Copia e Cola" (BR Code, padrão EMV QRCPS do Banco Central)."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

from .boleto.texto import cnpj_valido

TIPOS_CHAVE = {"cpf_cnpj": "CNPJ/CPF", "celular": "Celular", "email": "E-mail", "aleatoria": "Aleatória"}
RE_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
RE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
RE_COPIA_E_COLA = re.compile(r"000201[\x20-\x7E]*?6304[0-9A-Fa-f]{4}")


class ErroPix(ValueError):
    pass


def _digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


def cpf_valido(digitos: str) -> bool:
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * (posicao + 1 - i) for i in range(posicao))
        if (soma * 10) % 11 % 10 != int(digitos[posicao]):
            return False
    return True


# --------------------------------------------------------------------------- chaves


def normalizar_chave(tipo: str, chave: str) -> str:
    """Valida a chave conforme o tipo e devolve no formato usado pelo Pix (sem máscara)."""
    chave = (chave or "").strip()
    if tipo == "cpf_cnpj":
        digitos = _digitos(chave)
        if len(digitos) == 11:
            if not cpf_valido(digitos):
                raise ErroPix("CPF inválido: confira os números digitados.")
            return digitos
        if len(digitos) == 14:
            if not cnpj_valido(digitos):
                raise ErroPix("CNPJ inválido: confira os números digitados.")
            return digitos
        raise ErroPix("Informe um CPF (11 dígitos) ou um CNPJ (14 dígitos).")
    if tipo == "celular":
        digitos = _digitos(chave)
        if len(digitos) == 13 and digitos.startswith("55"):
            digitos = digitos[2:]
        if len(digitos) != 11 or digitos[0] == "0" or digitos[2] != "9":
            raise ErroPix("Informe o celular com DDD, por exemplo (65) 99999-9999.")
        return "+55" + digitos
    if tipo == "email":
        email = chave.lower()
        if len(email) > 77 or not RE_EMAIL.match(email):
            raise ErroPix("E-mail inválido.")
        return email
    if tipo == "aleatoria":
        if not RE_UUID.match(chave):
            raise ErroPix("Chave aleatória inválida. Ela tem o formato 123e4567-e89b-12d3-a456-426614174000.")
        return chave.lower()
    raise ErroPix("Tipo de chave inválido.")


def formatar_chave(tipo: str | None, chave: str | None) -> str:
    chave = chave or ""
    digitos = _digitos(chave)
    if tipo == "cpf_cnpj" and len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    if tipo == "cpf_cnpj" and len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    if tipo == "celular":
        if len(digitos) == 13 and digitos.startswith("55"):
            digitos = digitos[2:]
        if len(digitos) == 11:
            return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    return chave


def inferir_tipo(chave: str | None) -> str | None:
    chave = (chave or "").strip()
    if not chave:
        return None
    if "@" in chave:
        return "email"
    if RE_UUID.match(chave):
        return "aleatoria"
    digitos = _digitos(chave)
    if chave.startswith("+55") or (len(digitos) == 13 and digitos.startswith("55")):
        return "celular"
    if len(digitos) == 14 and cnpj_valido(digitos):
        return "cpf_cnpj"
    if len(digitos) == 11 and cpf_valido(digitos):
        return "cpf_cnpj"
    if len(digitos) == 11:
        return "celular"
    return None


# --------------------------------------------------------------------------- BR Code (Copia e Cola)


def crc16(payload: str) -> str:
    """CRC-16/CCITT-FALSE, usado no campo 63 do BR Code."""
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _tlv(texto: str) -> dict[str, str]:
    campos, i = {}, 0
    while i + 4 <= len(texto):
        identificador, tamanho = texto[i:i + 2], texto[i + 2:i + 4]
        if not tamanho.isdigit():
            raise ErroPix("Código Pix malformado.")
        valor = texto[i + 4:i + 4 + int(tamanho)]
        if len(valor) != int(tamanho):
            raise ErroPix("Código Pix incompleto.")
        campos[identificador] = valor
        i += 4 + int(tamanho)
    return campos


def ler_copia_e_cola(texto: str) -> dict:
    """Interpreta um "Pix Copia e Cola" e devolve chave, tipo, valor, recebedor, TXID etc."""
    payload = re.sub(r"[\r\n]", "", (texto or "").strip())
    if not payload.startswith("000201"):
        raise ErroPix("Isto não parece um Pix Copia e Cola (ele começa com 000201).")
    crc_valido = len(payload) > 8 and payload[-8:-4] == "6304" and crc16(payload[:-4]) == payload[-4:].upper()
    campos = _tlv(payload)

    conta = None
    for identificador in (f"{n:02d}" for n in range(26, 52)):
        if identificador in campos:
            try:
                sub = _tlv(campos[identificador])
            except ErroPix:
                continue
            if sub.get("00", "").lower() == "br.gov.bcb.pix":
                conta = sub
                break
    if conta is None:
        raise ErroPix("Este código não é de Pix (falta o identificador br.gov.bcb.pix).")

    chave_bruta = conta.get("01", "")
    tipo = inferir_tipo(chave_bruta)
    chave = chave_bruta
    if tipo:
        try:
            chave = normalizar_chave(tipo, chave_bruta)
        except ErroPix:
            tipo = None

    valor = None
    if campos.get("54"):
        try:
            valor = float(Decimal(campos["54"]))
        except InvalidOperation:
            valor = None
    adicionais = {}
    if campos.get("62"):
        try:
            adicionais = _tlv(campos["62"])
        except ErroPix:
            adicionais = {}
    txid = adicionais.get("05", "")

    return {
        "tipo_chave": tipo,
        "chave": chave,
        "chave_formatada": formatar_chave(tipo, chave),
        "valor": valor,
        "recebedor": campos.get("59", "").strip(),
        "cidade": campos.get("60", "").strip(),
        "txid": "" if txid == "***" else txid,
        "descricao": conta.get("02", ""),
        "dinamico": "25" in conta,
        "crc_valido": crc_valido,
        "copia_e_cola": payload,
    }


def _ascii(texto: str | None, limite: int) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip()[:limite]


def gerar_copia_e_cola(tipo: str, chave: str, valor: float | None = None, recebedor: str = "",
                       cidade: str = "BRASIL", txid: str = "", descricao: str = "") -> str:
    """Gera um Pix Copia e Cola estático (o banco confirma o recebedor pela chave na hora de pagar)."""
    def campo(identificador: str, conteudo: str) -> str:
        return f"{identificador}{len(conteudo):02d}{conteudo}"

    conta = campo("00", "br.gov.bcb.pix") + campo("01", normalizar_chave(tipo, chave))
    texto_descricao = _ascii(descricao, 40)
    if texto_descricao and len(conta) + len(texto_descricao) + 4 <= 99:
        conta += campo("02", texto_descricao)
    payload = campo("00", "01") + campo("26", conta) + campo("52", "0000") + campo("53", "986")
    if valor:
        payload += campo("54", f"{Decimal(str(valor)):.2f}")
    payload += campo("58", "BR")
    payload += campo("59", _ascii(recebedor, 25).upper() or "RECEBEDOR")
    payload += campo("60", _ascii(cidade, 15).upper() or "BRASIL")
    identificador = re.sub(r"[^A-Za-z0-9]", "", txid or "")[:25] or "***"
    payload += campo("62", campo("05", identificador)) + "6304"
    return payload + crc16(payload)


# --------------------------------------------------------------------------- arquivos (QR code)


def _qr_codes(imagem) -> list[str]:
    try:
        import zxingcpp
    except ImportError:  # pragma: no cover
        return []
    from PIL import ImageOps

    cinza = ImageOps.grayscale(imagem)
    for variante in (cinza, ImageOps.autocontrast(cinza, cutoff=2)):
        try:
            resultados = zxingcpp.read_barcodes(variante, formats=zxingcpp.BarcodeFormat.QRCode)
        except Exception:
            continue
        textos = [r.text for r in resultados if r.text.startswith("000201")]
        if textos:
            return textos
    return []


def ler_pix_de_arquivo(dados: bytes, max_paginas: int = 10) -> list[dict]:
    """Procura QR codes Pix (e textos "Copia e Cola") numa imagem ou PDF."""
    from .boleto.leitores import DocumentoPDF, abrir_imagem, eh_pdf

    candidatos: list[str] = []
    if eh_pdf(dados):
        documento = DocumentoPDF(dados)
        for pagina in documento.paginas(max_paginas):
            candidatos += _qr_codes(pagina.imagem)
            candidatos += RE_COPIA_E_COLA.findall(re.sub(r"\s*\n\s*", "", pagina.texto))
    else:
        candidatos += _qr_codes(abrir_imagem(dados))

    encontrados, vistos = [], set()
    for texto in candidatos:
        try:
            pix = ler_copia_e_cola(texto)
        except ErroPix:
            continue
        if pix["copia_e_cola"] not in vistos:
            vistos.add(pix["copia_e_cola"])
            encontrados.append(pix)
    return encontrados

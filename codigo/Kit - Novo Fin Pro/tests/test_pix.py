"""Pix: validação das chaves e leitura/geração do Copia e Cola (inclusive por QR code em imagem)."""

import io

import pytest
import segno

from app.pix import (
    ErroPix,
    crc16,
    formatar_chave,
    gerar_copia_e_cola,
    inferir_tipo,
    ler_copia_e_cola,
    ler_pix_de_arquivo,
    normalizar_chave,
)


def test_validacao_das_chaves():
    assert normalizar_chave("cpf_cnpj", "123.456.789-09") == "12345678909"
    assert normalizar_chave("cpf_cnpj", "02.359.273/0001-52") == "02359273000152"
    with pytest.raises(ErroPix):
        normalizar_chave("cpf_cnpj", "123.456.789-00")
    assert normalizar_chave("celular", "(65) 99603-5105") == "+5565996035105"
    assert normalizar_chave("celular", "+55 65 99603-5105") == "+5565996035105"
    with pytest.raises(ErroPix):
        normalizar_chave("celular", "(65) 3241-4400")  # fixo, não é celular
    assert normalizar_chave("email", "Flavio@E-ConnectCon.com.br") == "flavio@e-connectcon.com.br"
    with pytest.raises(ErroPix):
        normalizar_chave("email", "sem-arroba.com")
    assert normalizar_chave("aleatoria", "123E4567-E89B-12D3-A456-426614174000") == "123e4567-e89b-12d3-a456-426614174000"
    assert formatar_chave("cpf_cnpj", "02359273000152") == "02.359.273/0001-52"
    assert formatar_chave("celular", "+5565996035105") == "(65) 99603-5105"
    assert inferir_tipo("+5565996035105") == "celular" and inferir_tipo("a@b.com") == "email"
    assert inferir_tipo("02359273000152") == "cpf_cnpj"


def test_gera_e_le_pix_copia_e_cola():
    payload = gerar_copia_e_cola("cpf_cnpj", "02.359.273/0001-52", 360.0, "Hiper JN Comércio de Materiais", "Mirassol D'Oeste",
                                 txid="NF672362", descricao="Pedido 2.295.455")
    assert payload.startswith("000201") and crc16(payload[:-4]) == payload[-4:]
    lido = ler_copia_e_cola(payload)
    assert lido["crc_valido"] and lido["tipo_chave"] == "cpf_cnpj" and lido["chave"] == "02359273000152"
    assert lido["valor"] == 360.0 and lido["recebedor"] == "HIPER JN COMERCIO DE MATE"  # nome limitado a 25 caracteres (padrão EMV)
    assert lido["txid"] == "NF672362" and lido["descricao"] == "Pedido 2.295.455"
    alterado = payload[:-1] + ("0" if payload[-1] != "0" else "1")
    assert not ler_copia_e_cola(alterado)["crc_valido"]
    with pytest.raises(ErroPix):
        ler_copia_e_cola("34191.09123 34567.812341")


def test_le_pix_de_uma_imagem_com_qr_code():
    payload = gerar_copia_e_cola("email", "financeiro@empresa.com.br", 125.5, "Empresa Teste")
    buffer = io.BytesIO()
    segno.make(payload, error="m").save(buffer, kind="png", scale=8, border=4)
    encontrados = ler_pix_de_arquivo(buffer.getvalue())
    assert len(encontrados) == 1
    assert encontrados[0]["chave"] == "financeiro@empresa.com.br" and encontrados[0]["valor"] == 125.5

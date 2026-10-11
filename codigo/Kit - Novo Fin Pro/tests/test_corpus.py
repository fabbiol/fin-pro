"""Regressão sobre o corpus variado: PDFs de layouts diferentes, guias, carnê, scan e fotos de papel."""

from decimal import Decimal
from pathlib import Path

import pytest

import corpus as C
from app.boleto.codigo import formatar_linha
from app.boleto.extrator import ler_arquivo
from app.boleto.texto import normalizar


@pytest.fixture(scope="module")
def pasta(tmp_path_factory):
    return tmp_path_factory.mktemp("corpus")


def _ler(caminho: Path) -> list[dict]:
    resultado = ler_arquivo(caminho.read_bytes())
    return [{k: v["valor"] for k, v in b["campos"].items()} | {"_boleto": b} for b in resultado["boletos"]]


def _confere_codigo(campos: dict, esperado: dict):
    assert campos["linha_digitavel"] == formatar_linha(esperado["linha"])
    assert campos["vencimento"] == esperado["vencimento"].isoformat()
    assert Decimal(str(campos["valor"])) == esperado["valor"]


def test_bancario_com_rotulos_na_mesma_linha(pasta):
    esperado = C.bancario_rotulos_inline(pasta / "inline.pdf")
    (campos,) = _ler(pasta / "inline.pdf")
    _confere_codigo(campos, esperado)
    assert campos["beneficiario"] == esperado["beneficiario"]
    assert campos["documento_beneficiario"] == esperado["cnpj"]
    assert campos["numero_documento"] == esperado["documento"]


def test_conta_de_consumo_sem_rotulo_beneficiario(pasta):
    esperado = C.conta_de_energia(pasta / "energia.pdf")
    (campos,) = _ler(pasta / "energia.pdf")
    _confere_codigo(campos, esperado)
    assert esperado["beneficiario_contem"] in campos["beneficiario"]
    assert campos["documento_beneficiario"] == "07.047.251/0001-70"
    assert "004.512.887" in campos["numero_documento"]


def test_guia_das_beneficiario_e_orgao_arrecadador(pasta):
    esperado = C.guia_das(pasta / "das.pdf")
    (campos,) = _ler(pasta / "das.pdf")
    _confere_codigo(campos, esperado)
    assert "Simples Nacional" in campos["beneficiario"]
    assert "documento_beneficiario" not in campos  # o CNPJ impresso é do contribuinte
    assert campos["numero_documento"] == esperado["documento"]


def test_carne_com_tres_boletos_na_pagina(pasta):
    esperados = C.carne_tres_boletos(pasta / "carne.pdf")
    lidos = _ler(pasta / "carne.pdf")
    assert len(lidos) == 3
    for campos, esperado in zip(lidos, esperados):
        _confere_codigo(campos, esperado)
        assert campos["numero_documento"] == esperado["documento"]
        assert campos["beneficiario"] == esperado["beneficiario"]


def test_pdf_escaneado_sem_texto(pasta):
    esperado = C.bancario_rotulos_inline(pasta / "base_scan.pdf")
    C.pdf_escaneado(pasta / "base_scan.pdf", pasta / "escaneado.pdf")
    (campos,) = _ler(pasta / "escaneado.pdf")
    _confere_codigo(campos, esperado)
    assert "sorriso feliz" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == esperado["documento"]


def test_pdf_escaneado_deitado(pasta, boleto_pdf):
    """Caso real: folha escaneada girada 90° dentro da página do PDF."""
    origem, linha = boleto_pdf
    C.pdf_escaneado(origem, pasta / "deitado.pdf", rotacao=90)
    (campos,) = _ler(pasta / "deitado.pdf")
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert "exemplo de servicos" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == "NF-2026/0457"


def test_foto_de_papel_com_perspectiva(pasta, boleto_pdf):
    origem, linha = boleto_pdf
    C.foto_de_papel(origem, pasta / "foto.jpg")
    (campos,) = _ler(pasta / "foto.jpg")
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert "exemplo de servicos" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == "NF-2026/0457"


def test_foto_de_conta_de_consumo(pasta):
    esperado = C.conta_de_energia(pasta / "energia2.pdf")
    C.foto_de_papel(pasta / "energia2.pdf", pasta / "foto_energia.jpg", angulo=-8)
    (campos,) = _ler(pasta / "foto_energia.jpg")
    _confere_codigo(campos, esperado)

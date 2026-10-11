"""Testes ponta a ponta da API com boletos gerados (PDF com texto e foto girada via OCR)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.boleto.codigo import formatar_linha
from app.main import app
from conftest import VALOR, VENCIMENTO


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _enviar(cliente, caminho, tipo):
    with open(caminho, "rb") as f:
        resp = cliente.post("/api/leituras", files={"arquivo": (caminho.name, f, tipo)})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_status(cliente):
    dados = cliente.get("/api/status").json()
    assert dados["ocr"] is True and "planilha" in dados


def test_fluxo_pdf_lancamento_duplicidade_e_consultas(cliente, boleto_pdf):
    caminho, linha = boleto_pdf
    leitura = _enviar(cliente, caminho, "application/pdf")
    assert leitura["tipo_arquivo"] == "pdf" and len(leitura["boletos"]) == 1
    boleto = leitura["boletos"][0]
    campos = {k: v["valor"] for k, v in boleto["campos"].items()}
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert campos["beneficiario"] == "EMPRESA EXEMPLO DE SERVIÇOS LTDA"
    assert campos["documento_beneficiario"] == "12.345.678/0001-95"
    assert campos["numero_documento"] == "NF-2026/0457"
    assert campos["vencimento"] == VENCIMENTO.isoformat()
    assert campos["valor"] == float(VALOR)
    assert boleto["campos"]["linha_digitavel"]["fonte"] == "codigo_barras"
    assert boleto["confianca"] >= 0.9
    assert boleto["duplicado"] is None
    assert cliente.get(f"/api/arquivos/{leitura['arquivo']['id']}").status_code == 200

    payload = {**{k: campos[k] for k in ("linha_digitavel", "beneficiario", "documento_beneficiario",
                                          "numero_documento", "vencimento", "valor")},
               "arquivo_id": leitura["arquivo"]["id"]}
    criado = cliente.post("/api/boletos", json=payload)
    assert criado.status_code == 201, criado.text
    registro = criado.json()
    assert registro["id"] >= 1 and registro["data_lancamento"] and registro["situacao"] == "a_vencer"
    assert registro["arquivo"].startswith("arquivos/")

    duplicado = cliente.post("/api/boletos", json=payload)
    assert duplicado.status_code == 409 and duplicado.json()["detail"]["codigo"] == "duplicado"

    releitura = _enviar(cliente, caminho, "application/pdf")
    assert releitura["boletos"][0]["duplicado"]["id"] == registro["id"]

    lista = cliente.get("/api/boletos", params={"q": "exemplo servicos"}).json()
    assert lista["total"] == 1 and lista["resumo"]["valor_pendente"] == float(VALOR)
    assert cliente.get("/api/boletos", params={"situacao": "pago"}).json()["total"] == 0

    pago = cliente.patch(f"/api/boletos/{registro['id']}/status", json={"status": "Pago"}).json()
    assert pago["status"] == "Pago" and pago["data_pagamento"] == date.today().isoformat()

    editado = cliente.put(f"/api/boletos/{registro['id']}", json={"observacoes": "Pago via app"}).json()
    assert editado["observacoes"] == "Pago via app" and editado["beneficiario"] == campos["beneficiario"]

    painel = cliente.get("/api/painel").json()
    assert painel["indicadores"]["pagos_mes_qtd"] >= 1 and len(painel["serie_mensal"]) == 12

    assert cliente.get("/api/exportar", params={"formato": "csv"}).content.startswith("﻿".encode())
    assert cliente.get("/api/exportar", params={"formato": "xlsx"}).status_code == 200
    assert cliente.get(f"/api/boletos/{registro['id']}/arquivo").status_code == 200

    assert cliente.delete(f"/api/boletos/{registro['id']}").status_code == 204
    assert cliente.get(f"/api/boletos/{registro['id']}").status_code == 404


def test_linha_digitada(cliente, boleto_pdf):
    _, linha = boleto_pdf
    ok = cliente.post("/api/leituras/linha", json={"linha": linha}).json()
    assert ok["codigo"]["valido"] and ok["campos"]["valor"]["valor"] == float(VALOR)

    errada = linha[:5] + str((int(linha[5]) + 1) % 10) + linha[6:]
    invalida = cliente.post("/api/leituras/linha", json={"linha": errada}).json()
    assert not invalida["codigo"]["valido"]
    assert formatar_linha(linha) in invalida["sugestoes_linha"]

    assert cliente.post("/api/leituras/linha", json={"linha": "123"}).status_code == 422
    resp = cliente.post("/api/boletos", json={"linha_digitavel": errada, "valor": 1})
    assert resp.status_code == 422 and resp.json()["detail"]["codigo"] == "linha_invalida"


def test_foto_girada_com_ocr(cliente, boleto_foto):
    caminho, linha = boleto_foto
    leitura = _enviar(cliente, caminho, "image/jpeg")
    assert leitura["ocr_usado"]
    boleto = leitura["boletos"][0]
    campos = {k: v["valor"] for k, v in boleto["campos"].items()}
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert campos["vencimento"] == VENCIMENTO.isoformat()
    assert campos["valor"] == float(VALOR)
    assert campos["beneficiario"] == "EMPRESA EXEMPLO DE SERVIÇOS LTDA"
    assert campos["numero_documento"] == "NF-2026/0457"


def test_arquivo_invalido(cliente):
    resp = cliente.post("/api/leituras", files={"arquivo": ("x.txt", b"nao sou boleto", "text/plain")})
    assert resp.status_code == 422

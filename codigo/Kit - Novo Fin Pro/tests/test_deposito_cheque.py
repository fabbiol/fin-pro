"""Comprovante de depósito de cheque (banco): não é a foto do cheque — acha o cheque pela CMC-7 e dá a baixa."""

from datetime import date

import pytest

from app import contexto
from app.empresas import leitura, servico
from test_empresas_bot import _pdf, banco_limpo, caixa  # noqa: F401 - fixtures

# OCR real do comprovante do Bradesco (foto tirada deitada, lida girando): depósito do cheque 616 da Jose Pazete
DEPOSITO_BRADESCO = """237 Agencia: 1454 Maquina: 57699 09303 4.287,60 (*) Prazo maximo de bloqueio, contado em dias
Deposito em Conta-Corrente em Cheque(s) Quantidade de cheques depositados: CMC-7 74880585 0180006165 400000989483 Titular: PROSPERA IND.COMERCIO E SERVICOS Sujeito a conferencia.
bradesco Favorecido: Banco: 237 Conta: 0013669-7 Valor do deposito: Um dia util.
Banco: 237 Agencia: 1454 Maquina: 57699
Data: 24/09/2026 Hora: 16:24 N.Trans: 09303
Valor do deposito: 4.287,60
Quantidade de cheques depositados: 01
CMC-7 74880585 0180006165 400000989483
Titular: PROSPERA IND.COMERCIO E SERVICOS
"""


def test_cmc7_nas_posicoes_certas():
    lido = leitura.ler_cmc7("CMC-7 74880585 0180006165 400000989483")
    assert lido["banco"] == "Sicredi" and lido["agencia"] == "8058"
    assert lido["numero"] == "616" and lido["conta"] == "98948"  # não "180006" / "4000009894"


def test_comprovante_de_deposito_nao_e_cheque():
    assert leitura.classificar(DEPOSITO_BRADESCO) == "comprovante"
    dados = leitura.extrair_comprovante(DEPOSITO_BRADESCO)
    assert dados["deposito_cheque"] and dados["forma"] == "Cheque"
    assert [c["numero"] for c in dados["cheques"]] == ["616"]
    assert dados["valor"] == 4287.60 and dados["data"] == date(2026, 9, 24) and dados["hora"] == "16:24"
    assert dados["id_transacao"] == "09303"


@pytest.fixture
def pazete():
    empresa = servico.salvar_empresa({"nome": "Jose Pazete Ltda (Imapal)", "cnpj": "39.285.595/0001-04"}, "Fábio")
    servico.lancar_notas(empresa["nome"], [{"data": date(2026, 9, 10), "material": "Brita 01", "unidade": "M³",
                                            "quantidade": 27, "valor_unitario": 158.80, "numero_nf": "7100",
                                            "pedido": "7200"}], "Fábio")
    cheques = {}
    for numero, bom_para in (("616", date(2026, 9, 24)), ("617", date(2026, 9, 30))):
        cheques[numero] = servico.lancar_cheque({"empresa": empresa["nome"], "numero": numero, "vencimento": bom_para,
                                                 "valor": 4287.60, "banco": "Sicredi", "pedidos": "7200"}, "Fábio")
    return cheques


def test_bot_da_baixa_no_cheque_depositado(caixa, pazete, monkeypatch):  # noqa: F811
    monkeypatch.setattr("app.empresas.leitura.texto_do_arquivo", lambda *a, **k: DEPOSITO_BRADESCO)
    item = caixa.receber(_pdf("comprovante"), "foto-20260924-162601.jpg")

    assert item["tipo"] == "comprovante" and item["estado"] == "lancado"
    assert "cheque nº 616" in item["resumo"] and "compensado em 24/09/2026" in item["resumo"]
    cheques = {c["numero"]: c for c in contexto.empresas.listar("cheques")}
    assert cheques["616"]["status"] == "Compensado" and cheques["616"]["data_deposito"] == date(2026, 9, 24)
    assert cheques["617"]["status"] == "Em carteira"  # o outro cheque de mesmo valor não é tocado
    assert len(cheques) == 2  # nenhum cheque novo foi criado nem excluído
    recebimento = contexto.empresas.listar("recebimentos")[0]
    assert recebimento["forma"] == "Cheque" and recebimento["cheque_id"] == pazete["616"]["id"]
    assert recebimento["arquivo"]  # o comprovante fica guardado no recebimento
    assert contexto.empresas.listar("notas")[0]["status"] == "Recebido"


def test_cheque_nao_encontrado_fica_para_conferir(caixa, pazete, monkeypatch):  # noqa: F811
    outro = DEPOSITO_BRADESCO.replace("0180006165", "0180009995")  # cheque 999: não está em carteira
    monkeypatch.setattr("app.empresas.leitura.texto_do_arquivo", lambda *a, **k: outro)
    item = caixa.receber(_pdf("comprovante"), "deposito.jpg")

    assert item["estado"] == "pendente" and "nº 999" in item["resumo"]
    assert {c["status"] for c in contexto.empresas.listar("cheques")} == {"Em carteira"}

    # na conferência, alguém escolhe o cheque certo: ele é compensado com este comprovante
    caixa.confirmar(item["id"], "comprovante", {"cheque_id": pazete["617"]["id"], "data": "2026-09-24",
                                               "valor": 4287.60}, "Fábio")
    cheque = contexto.empresas.obter(pazete["617"]["id"], "cheques")
    assert cheque["status"] == "Compensado" and cheque["data_deposito"] == date(2026, 9, 24)
    assert contexto.empresas.listar("recebimentos")[0]["arquivo"]


def test_depositei_pela_tela_com_comprovante(pazete):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        enviado = cliente.post("/api/empresas/arquivo", files={"arquivo": ("deposito.pdf", _pdf("deposito"), "application/pdf")})
        assert enviado.status_code == 201
        resposta = cliente.post("/api/recebimentos", json={"valor": 4287.60, "data": "2026-09-24", "forma": "Cheque",
                                                           "cheque_id": pazete["616"]["id"], "arquivo_id": enviado.json()["id"]})
        assert resposta.status_code == 201, resposta.text
    cheque = contexto.empresas.obter(pazete["616"]["id"], "cheques")
    assert cheque["status"] == "Compensado"
    assert contexto.empresas.listar("recebimentos")[0]["arquivo"].endswith(".pdf")

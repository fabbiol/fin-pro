"""Mais de um centro de custo no mesmo boleto ou Pix: o valor dividido entre os centros."""

import re
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import contexto, cost_center

from gerar_boleto_exemplo import montar_codigo
from test_pix_centros_api import cliente  # noqa: F401

DIVIDIDO = "Energia R$ 600,00 + Frota R$ 400,00"


def test_texto_da_divisao():
    assert cost_center.split_parts(DIVIDIDO) == [("Energia", 600.0), ("Frota", 400.0)]
    assert cost_center.split_parts("Energia") == [] and cost_center.names("Energia") == ["Energia"] and cost_center.names("") == []
    assert cost_center.names(DIVIDIDO) == ["Energia", "Frota"]
    # nome com "+" continua sendo um centro só; valor com ponto de milhar
    assert cost_center.split_parts("Britador + Peneira") == []
    assert cost_center.split_parts("Britador + Peneira R$ 1.234,56 + Frota R$ 0,44") == [("Britador + Peneira", 1234.56), ("Frota", 0.44)]
    assert cost_center.validate("  Energia  R$ 600,00 + Frota R$ 400,00 ", 1000) == DIVIDIDO
    assert cost_center.validate("Energia R$ 600,00", 600) == "Energia"  # uma parte só é o próprio centro
    assert cost_center.rename(DIVIDIDO, "frota", "Caminhões") == "Energia R$ 600,00 + Caminhões R$ 400,00"
    assert cost_center.rename("Frota", "frota", "Caminhões") == "Caminhões" and cost_center.rename(DIVIDIDO, "Obra", "X") is None


def test_reparte_na_proporcao_e_a_soma_sempre_fecha():
    assert cost_center.allocate(DIVIDIDO, 1000) == [("Energia", 600.0), ("Frota", 400.0)]
    assert cost_center.allocate(DIVIDIDO, 1100) == [("Energia", 660.0), ("Frota", 440.0)]  # pago com juros
    assert cost_center.allocate("Energia", 1100) == [("Energia", 1100)] and cost_center.allocate("", 50) == [("", 50)]
    tercos = cost_center.allocate("A R$ 1,00 + B R$ 1,00 + C R$ 1,00", 100)
    assert tercos == [("A", 33.33), ("B", 33.33), ("C", 33.34)] and round(sum(v for _, v in tercos), 2) == 100


@pytest.mark.parametrize("texto, valor, trecho", [
    ("Energia R$ 600,00 + Frota R$ 300,00", 1000, "soma R$ 900,00"),
    ("Energia R$ 600,00 + energia R$ 400,00", 1000, "mais de uma vez"),
    ("Energia R$ 1.000,00 + Frota R$ 0,00", 1000, 'valor de "Frota"'),
    (DIVIDIDO, None, "Informe o valor"),
    ("x" * 61, 10, "até 60"),
    (" + ".join(f"C{i} R$ 1,00" for i in range(11)), 11, "até 10"),
])
def test_divisao_errada_e_recusada(texto, valor, trecho):
    with pytest.raises(ValueError, match=re.escape(trecho)):
        cost_center.validate(texto, valor)


def _boleto(cliente, valor, centro):
    vencimento = date.today() + timedelta(days=5)
    _, linha = montar_codigo("237", vencimento, Decimal(str(valor)), str(int(valor))[0] * 25)
    return cliente.post("/api/boletos", json={"linha_digitavel": linha, "beneficiario": "Fornecedor", "valor": valor,
                                              "vencimento": vencimento.isoformat(), "centro_custo": centro})


def test_boleto_e_pix_divididos_entre_centros(cliente):
    boleto = _boleto(cliente, 1000.0, "Energia  R$ 600,00 + Frota R$ 400,00")
    assert boleto.status_code == 201, boleto.text
    assert boleto.json()["centro_custo"] == DIVIDIDO
    hoje = date.today().isoformat()
    pix = cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "a@b.com", "valor": 300, "recebedor": "Oficina",
                                         "vencimento": hoje, "centro_custo": "Frota R$ 100,00 + Obra Nova R$ 200,00"})
    assert pix.status_code == 201, pix.text
    cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "c@d.com", "valor": 50, "vencimento": hoje, "centro_custo": "Energia"})

    # os centros da divisão são cadastrados e cada um conta a sua parte
    centros = {c["nome"]: c for c in cliente.get("/api/centros").json()["centros"]}
    assert centros["Obra Nova"]["pix"] == 1 and centros["Obra Nova"]["total"] == 200
    assert centros["Frota"]["boletos"] == 1 and centros["Frota"]["pix"] == 1 and centros["Frota"]["total"] == 500
    assert centros["Energia"]["total"] == 650 and DIVIDIDO not in centros

    # o filtro por centro acha o lançamento em cada um dos centros dele
    assert cliente.get("/api/boletos", params={"centro": "frota"}).json()["total"] == 1
    assert cliente.get("/api/boletos", params={"centro": "energia"}).json()["total"] == 1
    assert cliente.get("/api/boletos", params={"centro": "Obra Nova"}).json()["total"] == 0
    assert cliente.get("/api/boletos", params={"centro": "__sem__"}).json()["total"] == 0
    assert cliente.get("/api/pix", params={"centro": "frota"}).json()["total"] == 1

    # análise de gastos: cada centro com a sua parte, e o total não muda
    analise = cliente.get("/api/gastos").json()
    por_centro = {c["centro"]: c for c in analise["centros"]}
    assert analise["total"] == 1350 and round(sum(c["total"] for c in analise["centros"]), 2) == 1350
    assert por_centro["Energia"]["total"] == 650 and por_centro["Frota"]["total"] == 500 and por_centro["Obra Nova"]["total"] == 200
    assert por_centro["Frota"]["boletos"] == 400 and por_centro["Frota"]["pix"] == 100 and por_centro["Frota"]["quantidade"] == 2
    assert round(sum(sum(m["centros"].values()) for m in analise["serie_mensal"]), 2) == 1350

    # renomear um centro troca o nome também dentro da divisão
    assert cliente.put("/api/centros", json={"nome_anterior": "Frota", "nome": "Caminhões"}).status_code == 200
    assert cliente.get(f"/api/boletos/{boleto.json()['id']}").json()["centro_custo"] == "Energia R$ 600,00 + Caminhões R$ 400,00"
    assert cliente.get("/api/pix", params={"centro": "caminhões"}).json()["total"] == 1


def test_divisao_tem_de_somar_o_valor_ao_lancar_e_ao_editar(cliente):
    recusado = _boleto(cliente, 1000.0, "Energia R$ 600,00 + Frota R$ 300,00")
    assert recusado.status_code == 422 and "soma R$ 900,00" in recusado.json()["detail"]["mensagem"]
    boleto = _boleto(cliente, 1000.0, DIVIDIDO).json()
    # mudar só o centro, só o valor ou os dois: a soma continua tendo de bater
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"centro_custo": "Energia R$ 500,00 + Frota R$ 400,00"}).status_code == 422
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"valor": 1200}).json()["detail"]["codigo"] == "centro_invalido"
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"valor": 1200, "centro_custo": "Energia R$ 800,00 + Frota R$ 400,00"}).status_code == 200
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"observacoes": "sem mexer no centro"}).status_code == 200
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"centro_custo": "Energia"}).json()["centro_custo"] == "Energia"
    assert cliente.put(f"/api/boletos/{boleto['id']}", json={"valor": 900}).status_code == 200  # um centro só: valor livre

    pix = cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "a@b.com", "valor": 300,
                                         "centro_custo": "Frota R$ 100,00 + Obra R$ 200,00"}).json()
    assert cliente.put(f"/api/pix/{pix['id']}", json={"valor": 350}).status_code == 422
    assert cliente.put(f"/api/pix/{pix['id']}", json={"valor": 350, "centro_custo": "Frota R$ 150,00 + Obra R$ 200,00"}).status_code == 200


def test_fechamento_do_mes_reparte_o_pago_com_juros(cliente):
    boleto = _boleto(cliente, 1000.0, DIVIDIDO).json()
    # pago com R$ 100 de juros: cada centro leva a sua proporção do que saiu de fato
    cliente.put(f"/api/boletos/{boleto['id']}", json={"status": "Pago", "valor_pago": 1100, "juros_multa": 100,
                                                      "data_pagamento": date.today().isoformat()})
    mes = (date.today() + timedelta(days=5)).strftime("%Y-%m")
    fechamento = cliente.get("/api/relatorios/fechamento", params={"mes": mes}).json()
    por_centro = {c["centro_custo"]: c for c in fechamento["por_centro"]}
    assert por_centro["Energia"]["pago"] == 660 and por_centro["Frota"]["pago"] == 440
    assert round(sum(c["total"] for c in fechamento["por_centro"]), 2) == 1100
    analise = cliente.get("/api/gastos").json()
    assert {c["centro"]: c["total"] for c in analise["centros"]} == {"Energia": 660, "Frota": 440}
    assert contexto.planilha.exportar()  # a planilha Excel mostra a divisão na coluna Centro de Custo

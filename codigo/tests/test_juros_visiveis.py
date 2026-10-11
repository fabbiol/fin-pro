"""Juros e multas pagos aparecem nos totais das listas, no Painel e em Gastos."""

from datetime import date, datetime

from app import servicos

HOJE = date(2026, 9, 24)


def _boleto(id_, valor, juros=0.0, status="Pago", pago=date(2026, 9, 21), venc=date(2026, 9, 10)):
    return {"id": id_, "beneficiario": f"Fornecedor {id_}", "valor": valor, "status": status, "vencimento": venc,
            "data_pagamento": pago if status == "Pago" else None, "valor_pago": valor + juros if status == "Pago" else None,
            "juros_multa": juros, "centro_custo": "Manutenção", "data_lancamento": datetime(2026, 9, 1, 8, 0)}


REGISTROS = [_boleto(1, 900, 56.70), _boleto(2, 900, 30.60), _boleto(3, 210, 0.0), _boleto(4, 500, status="Pendente"),
             {**_boleto(5, 300, 12.0), "status": "Cancelado"}]


def test_resumo_da_lista_soma_os_juros_dos_pagos():
    r = servicos.resumir(REGISTROS, HOJE)
    assert r["juros_multa"] == 87.30 and r["pagos_com_juros"] == 2


def test_painel_mostra_os_juros_pagos_no_mes():
    k = servicos.painel(REGISTROS, HOJE)["indicadores"]
    assert k["juros_mes_valor"] == 87.30 and k["juros_mes_qtd"] == 2


def test_gastos_mostra_os_juros_do_periodo():
    d = servicos.analise_gastos(REGISTROS, [], hoje=HOJE)
    assert d["juros_multa"] == 87.30 and d["pagos_com_juros"] == 2

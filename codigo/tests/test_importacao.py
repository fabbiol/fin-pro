"""Importação de boletos exportados de outros sistemas (CSV, Excel e ".xls" em HTML)."""

import io
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app import admin, contexto, importacao, main
from app.banco import BancoBoletos
from app.fila_gravacao import FilaGravacao
from app.repositorio import RepositorioBoletos
from gerar_boleto_exemplo import montar_codigo

VENC = date.today() + timedelta(days=10)


def _linha(valor: str, campo_livre: str, vencimento: date = VENC) -> str:
    return montar_codigo("237", vencimento, Decimal(valor), campo_livre)[1]


def _csv() -> bytes:
    venc = f"{VENC:%d/%m/%Y}"
    linhas = [
        "Relatório de contas a pagar;;;;;;;",
        "Fornecedor;CNPJ;Nº Documento;Vencto;Valor Título;Linha Digitável;Situação;C. Custo",
        f"Posto Central Ltda;02359273000152;NF 1001;{venc};150,00;{_linha('150.00', '1' * 25)};Em aberto;Combustível e Veículos",
        f"Energia MT;;FAT-77;{venc};R$ 1.234,56;;Liquidado;",
        f"Loja X;;123;{venc};99,00;12345;Em aberto;",
        f"Oficina Y;;OS-9;{venc};85,00;{_linha('80.00', '2' * 25)};Em aberto;",
        f"Posto Central Ltda;02359273000152;NF 1001;{venc};150,00;{_linha('150.00', '1' * 25)};Em aberto;",
        ";;;;1.619,56;;;",
    ]
    return "\n".join(linhas).encode("cp1252")


def test_conversao_de_valores_datas_e_situacao():
    assert importacao.ler_valor("1.234,56") == 1234.56
    assert importacao.ler_valor("R$ 1,234.56") == 1234.56
    assert importacao.ler_valor("360,00") == 360.0
    assert importacao.ler_valor("(10,50)") == 10.5
    assert importacao.ler_valor("1.500") == 1500.0
    assert importacao.ler_valor(1500) == 1500.0
    assert importacao.ler_valor("abc") is None
    assert importacao.ler_data("15/09/2026") == date(2026, 9, 15)
    assert importacao.ler_data("15.09.26") == date(2026, 9, 15)
    assert importacao.ler_data("2026-09-15 00:00:00") == date(2026, 9, 15)
    assert importacao.ler_data("15-set-2026") == date(2026, 9, 15)
    assert importacao.ler_data(datetime(2026, 9, 15, 10, 30)) == date(2026, 9, 15)
    assert importacao.ler_data(46280) == date(1899, 12, 30) + timedelta(days=46280)
    assert importacao.ler_status("Liquidado") == "Pago"
    assert importacao.ler_status("Em aberto", "Pago") == "Pendente"
    assert importacao.ler_status("A pagar") == "Pendente"
    assert importacao.ler_status("Cancelado") == "Cancelado"
    assert importacao.ler_status("", "Pago") == "Pago"


def test_reconhece_colunas_e_confere_as_linhas_de_um_csv():
    formato, abas = importacao.ler_planilhas(_csv(), "contas.csv")
    tabela = importacao.montar_tabela(abas)
    assert formato == "csv" and tabela["linha_cabecalho"] == 2
    mapa = importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"])
    assert mapa == {"linha_digitavel": 5, "beneficiario": 0, "documento_beneficiario": 1, "numero_documento": 2,
                    "vencimento": 3, "valor": 4, "status": 6, "data_pagamento": None, "centro_custo": 7, "observacoes": None}

    itens = importacao.preparar(tabela, mapa, existentes=[], nome_arquivo="contas.csv")
    assert [i["estado"] for i in itens] == ["pronto", "aviso", "erro", "aviso", "repetido"]  # linha de total ignorada
    posto, energia, loja, oficina, repetido = itens
    assert posto["dados"]["documento_beneficiario"] == "02.359.273/0001-52" and posto["dados"]["codigo_barras"]
    assert posto["dados"]["centro_custo"] == "Combustível e Veículos" and posto["dados"]["vencimento"] == VENC
    assert energia["dados"]["status"] == "Pago" and energia["dados"]["valor"] == 1234.56 and energia["dados"]["data_pagamento"] == VENC
    assert "5 dígitos" in loja["mensagens"][0]
    assert any("diferente do código" in m for m in oficina["mensagens"]) and oficina["dados"]["valor"] == 85.0
    assert "linha 3" in repetido["mensagens"][0]


def test_planilha_excel_com_titulo_acima_das_colunas():
    wb = Workbook()
    ws = wb.active
    ws.title = "Contas a Pagar"
    ws.append(["Empresa Exemplo"])
    ws.append([None])
    ws.append(["Data de Vencimento", "Favorecido", "Valor", "Código de Barras", "Centro de Custo", "Data Pagamento"])
    barras = montar_codigo("001", date(2026, 10, 1), Decimal("250.40"), "5" * 25)[0]
    ws.append([datetime(2026, 10, 1), "Fornecedor A", 250.4, barras, "Obras", None])
    ws.append([datetime(2026, 10, 5), "Fornecedor B", 99.9, None, None, datetime(2026, 10, 4)])
    wb.create_sheet("Resumo").append(["Total", 350.3])
    buffer = io.BytesIO()
    wb.save(buffer)

    formato, abas = importacao.ler_planilhas(buffer.getvalue(), "contas.xlsx")
    tabela = importacao.montar_tabela(abas)
    assert formato == "xlsx" and tabela["aba"] == "Contas a Pagar" and tabela["linha_cabecalho"] == 3
    mapa = importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"])
    assert (mapa["vencimento"], mapa["beneficiario"], mapa["valor"], mapa["linha_digitavel"], mapa["centro_custo"],
            mapa["data_pagamento"]) == (0, 1, 2, 3, 4, 5)
    a, b = importacao.preparar(tabela, mapa, existentes=[])
    assert a["estado"] == "pronto" and a["dados"]["linha_digitavel"].startswith("0019") and a["dados"]["vencimento"] == date(2026, 10, 1)
    assert b["dados"]["status"] == "Pago" and b["dados"]["data_pagamento"] == date(2026, 10, 4)


def test_xls_gerado_em_html_por_outros_sistemas():
    html = ("<html><body><table><tr><th>Beneficiário</th><th>Vencimento</th><th>Valor</th></tr>"
            "<tr><td>Água &amp; Esgoto</td><td>20/10/2026</td><td>45,90</td></tr></table></body></html>").encode("cp1252")
    formato, abas = importacao.ler_planilhas(html, "relatorio.xls")
    tabela = importacao.montar_tabela(abas)
    [item] = importacao.preparar(tabela, importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"]), existentes=[])
    assert formato == "html" and item["dados"]["beneficiario"] == "Água & Esgoto" and item["dados"]["valor"] == 45.9
    with pytest.raises(importacao.ErroImportacao):
        importacao.ler_planilhas(b"%PDF-1.7 ...", "boleto.pdf")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "importacoes", importacao.ArmazemImportacoes(tmp_path / "importacoes"))
    monkeypatch.setattr(contexto, "modelos_importacao", importacao.ModelosMapeamento(tmp_path / "modelos.json"))
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app) as c:
        yield c


def test_importacao_pela_api(cliente):
    envio = {"arquivo": ("contas.csv", _csv(), "text/csv")}
    assert cliente.post("/api/importacao", files=envio).json()["detail"]["codigo"] == "admin_sem_senha"
    assert cliente.post("/api/admin/senha", json={"senha": "senha-admin", "confirmacao": "senha-admin"}).json()["autorizado"]
    resposta = cliente.post("/api/importacao", files={"arquivo": ("contas.csv", _csv(), "text/csv")})
    assert resposta.status_code == 201, resposta.text
    sessao = resposta.json()
    assert sessao["resumo"]["pronto"] == 1 and sessao["resumo"]["erro"] == 1 and not sessao["mapeamento_salvo"]
    validos = [i["indice"] for i in sessao["itens"] if i["estado"] in ("pronto", "aviso")]
    corpo = {"aba": sessao["aba"], "linha_cabecalho": sessao["linha_cabecalho"], "mapeamento": sessao["mapeamento"],
             "centro_custo": "Administrativo", "indices": validos + [2]}  # a linha com erro é ignorada
    feito = cliente.post(f"/api/importacao/{sessao['id']}/importar", json=corpo).json()
    assert feito["importados"] == 3 and feito["ignorados"] == 1 and not feito["pendente_gravacao"]

    boletos = cliente.get("/api/boletos", params={"por_pagina": 0}).json()["itens"]
    assert {b["beneficiario"] for b in boletos} == {"Posto Central Ltda", "Energia MT", "Oficina Y"}
    assert {b["centro_custo"] for b in boletos} == {"Combustível e Veículos", "Administrativo"}
    assert contexto.planilha.exportar()  # o Excel é gerado a partir do banco
    aba = load_workbook(contexto.planilha.caminho)["Boletos"]
    coluna = [c.value for c in aba[1]].index("Nome do Arquivo Original") + 1
    assert aba.cell(row=2, column=coluna).value == "Importado de contas.csv"

    # Segunda importação do mesmo arquivo: colunas lembradas e boletos marcados como já lançados
    sessao2 = cliente.post("/api/importacao", files={"arquivo": ("contas.csv", _csv(), "text/csv")}).json()
    assert sessao2["mapeamento_salvo"] and sessao2["resumo"]["duplicado"] == 4 and sessao2["resumo"]["pronto"] == 0
    previa = cliente.post(f"/api/importacao/{sessao2['id']}/previa", json={"mapeamento": {**sessao2["mapeamento"], "centro_custo": None}})
    assert previa.json()["mapeamento"]["centro_custo"] is None

    assert cliente.post("/api/importacao/" + "0" * 32 + "/previa", json={}).status_code == 404
    assert cliente.post("/api/importacao", files={"arquivo": ("boleto.pdf", b"%PDF-1.7", "application/pdf")}).status_code == 422
    modelo = cliente.get("/api/importacao/modelo.xlsx")
    assert modelo.status_code == 200 and load_workbook(io.BytesIO(modelo.content)).active["A1"].value == "Linha digitável"

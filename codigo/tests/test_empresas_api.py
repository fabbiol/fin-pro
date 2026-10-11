"""API do módulo Empresas: cadastro, notas, cheques, recebimentos, fechamento e importação do print."""

import pytest
from fastapi.testclient import TestClient

from app import contexto
from app.main import app
from test_empresas_bot import _pdf
from test_empresas_leitura import PRINT_FECHAMENTO, XML_NFE


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    from app.banco import BancoBoletos
    from app.empresas.configuracao import ConfigEmpresas
    from app.empresas.modelos import ABAS_EMPRESAS

    banco = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                         abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    monkeypatch.setattr(contexto, "empresas", banco)
    monkeypatch.setattr(contexto, "empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))
    with TestClient(app) as c:
        yield c
    banco.parar()


def _empresa(cliente, nome="Imapal", **extra):
    resposta = cliente.post("/api/empresas", json={"nome": nome, "cnpj": "12.345.678/0001-95", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _nota(cliente, empresa="Imapal", nf="6859", data="2026-08-03", valor=1905.60):
    return cliente.post("/api/notas", json={"empresa": empresa, "itens": [
        {"data": data, "material": "Brita 01", "unidade": "M³", "quantidade": 12, "valor_unitario": 158.80,
         "valor_total": valor, "numero_nf": nf, "pedido": "7043"}]})


def test_cadastro_de_empresa_e_resumo(cliente):
    empresa = _empresa(cliente)
    _nota(cliente)

    dados = cliente.get("/api/empresas").json()
    assert [e["nome"] for e in dados["empresas"]] == ["Imapal"]
    assert dados["empresas"][0]["em_aberto"] == 1905.6
    assert dados["config"]["dia_fechamento"] == 20

    assert cliente.post("/api/empresas", json={"nome": "imapal"}).status_code == 422
    assert cliente.put(f"/api/empresas/{empresa['id']}", json={"status": "Inativa"}).json()["status"] == "Inativa"
    assert cliente.delete(f"/api/empresas/{empresa['id']}").status_code == 422  # já tem lançamentos


def test_fechamento_em_json_excel_e_pdf(cliente):
    empresa = _empresa(cliente)
    _nota(cliente)
    cliente.post("/api/empresas/config", json={"minha_empresa": {"nome": "Prospera", "cnpj": "03.880.985/0001-85"}})

    fechamento = cliente.get(f"/api/empresas/{empresa['id']}/fechamento?competencia=2026-08").json()
    assert fechamento["totais"]["total"] == 1905.6 and fechamento["inicio"] == "2026-07-21"
    assert fechamento["linhas"][0]["numero_nf"] == "6859"

    xlsx = cliente.get(f"/api/empresas/{empresa['id']}/fechamento/arquivo?competencia=2026-08")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    assert "fechamento-imapal-2026-08.xlsx" in xlsx.headers["content-disposition"]
    pdf = cliente.get(f"/api/empresas/{empresa['id']}/fechamento/arquivo?formato=pdf&competencia=2026-08")
    assert pdf.content[:4] == b"%PDF"


def test_mover_a_nota_para_outro_fechamento(cliente):
    """A NF chegou depois do dia 20: dá para mandá-la para o fechamento seguinte, com todas as suas linhas."""
    _empresa(cliente)
    cliente.post("/api/notas", json={"empresa": "Imapal", "itens": [
        {"data": "2026-09-15", "material": "Brita 01", "unidade": "M³", "quantidade": 12, "valor_unitario": 158.80,
         "numero_nf": "7120", "pedido": "7300"},
        {"data": "2026-09-15", "material": "Pedrisco", "unidade": "M³", "quantidade": 5, "valor_unitario": 100,
         "numero_nf": "7120", "pedido": "7300"},
    ]})
    notas = cliente.get("/api/notas").json()["notas"]
    assert {n["competencia"] for n in notas} == {"2026-09"}  # pela data, entrou no fechamento de setembro

    movida = cliente.put(f"/api/notas/{notas[0]['id']}", json={"competencia": "2026-10", "todas_da_nota": True}).json()
    assert movida["linhas_movidas"] == 2
    assert {n["competencia"] for n in cliente.get("/api/notas").json()["notas"]} == {"2026-10"}

    empresa_id = cliente.get("/api/empresas").json()["cadastro"][0]["id"]
    setembro = cliente.get(f"/api/empresas/{empresa_id}/fechamento?competencia=2026-09").json()
    outubro = cliente.get(f"/api/empresas/{empresa_id}/fechamento?competencia=2026-10").json()
    assert setembro["totais"]["total"] == 0 and outubro["totais"]["total"] == 2405.60


def test_recebimento_da_baixa_e_pode_ser_cancelado(cliente):
    _empresa(cliente)
    _nota(cliente)

    recebimento = cliente.post("/api/recebimentos", json={"empresa": "Imapal", "forma": "Pix", "valor": 1905.60,
                                                          "data": "2026-08-20", "notas": "6859"}).json()
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Recebido"

    cliente.post(f"/api/recebimentos/{recebimento['id']}/cancelar")
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Em aberto"
    assert cliente.get("/api/recebimentos").json()["recebimentos"][0]["status"] == "Cancelado"


def test_cheque_pela_api_prende_e_solta_as_notas(cliente):
    _empresa(cliente)
    _nota(cliente)

    cheque = cliente.post("/api/cheques", json={"empresa": "Imapal", "numero": "123", "valor": 1905.60,
                                                "vencimento": "2026-09-10", "pedidos": "7043",
                                                "banco": "Sicredi", "coop": "3003"}).json()
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Em cheque"

    cliente.put(f"/api/cheques/{cheque['id']}", json={"status": "Compensado", "data_deposito": "2026-09-10"})
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Recebido"
    assert cliente.get("/api/cheques?status=Compensado").json()["cheques"][0]["id"] == cheque["id"]


def test_analisar_arquivo_e_importar_print_do_fechamento(cliente):
    _empresa(cliente)
    xml = cliente.post("/api/empresas/analisar", files={"arquivo": ("nfe.xml", XML_NFE.encode("utf-8"), "text/xml")}).json()
    assert xml["tipo"] == "nota" and xml["empresa"] == "Imapal" and xml["dados"]["numero_nf"] == "6859"

    lido = cliente.post("/api/empresas/analisar",
                        files={"arquivo": ("print.pdf", _pdf(PRINT_FECHAMENTO), "application/pdf")}).json()
    assert lido["tipo"] == "fechamento" and len(lido["dados"]["linhas"]) == 5

    importado = cliente.post("/api/empresas/importar-fechamento",
                             json={"empresa": "Imapal", "linhas": lido["dados"]["linhas"]}).json()
    assert importado["quantidade"] == 5
    fechamento = cliente.get("/api/empresas/1/fechamento?competencia=2026-08").json()
    assert fechamento["totais"]["total"] == 9528.0 and fechamento["totais"]["quantidade"] == 5


def test_conferencia_da_caixa_de_entrada_do_bot(cliente):
    _empresa(cliente)
    item = contexto.empresas_entrada.receber(_pdf(PRINT_FECHAMENTO), "print.pdf")
    entrada = cliente.get("/api/empresas/entrada").json()
    assert entrada["pendentes"] >= 1 and any(i["id"] == item["id"] for i in entrada["itens"])

    assert cliente.post(f"/api/empresas/entrada/{item['id']}/descartar").json() == {"ok": True}
    assert cliente.post(f"/api/empresas/entrada/{item['id']}/descartar").status_code == 404


def test_config_do_bot_de_notas_esconde_o_token(cliente):
    salvo = cliente.post("/api/empresas/config", json={"dia_fechamento": 15, "bot": {"token": "123:abc"}}).json()
    assert salvo["dia_fechamento"] == 15 and salvo["bot"]["token"] == "••••••••"
    assert cliente.post("/api/empresas/config", json={"dia_fechamento": 40}).status_code == 422
    assert contexto.empresas_config.token() == "123:abc"

"""Leitura em segundo plano, lançamento em lote, gravação pendente e senha de acesso."""

import time
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app, planilha
from app.planilha import PlanilhaBloqueadaError
from conftest import VALOR
from gerar_boleto_exemplo import montar_codigo


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _aguardar(cliente, tarefa):
    for _ in range(240):
        if tarefa["status"] in ("concluida", "erro"):
            return tarefa
        time.sleep(0.25)
        tarefa = cliente.get(f"/api/leituras/tarefas/{tarefa['id']}").json()
    raise AssertionError("a leitura não terminou")


def test_leitura_em_segundo_plano_com_progresso(cliente, boleto_pdf):
    caminho, _ = boleto_pdf
    with open(caminho, "rb") as f:
        resposta = cliente.post("/api/leituras/tarefas", files={"arquivo": ("b.pdf", f, "application/pdf")})
    assert resposta.status_code == 202
    tarefa = _aguardar(cliente, resposta.json())
    assert tarefa["status"] == "concluida" and tarefa["percentual"] == 100 and tarefa["paginas"] == 1
    assert tarefa["resultado"]["boletos"][0]["campos"]["valor"]["valor"] == float(VALOR)
    assert cliente.get("/api/leituras/tarefas/nao-existe").status_code == 404


def test_tarefa_com_arquivo_invalido(cliente):
    tarefa = cliente.post("/api/leituras/tarefas", files={"arquivo": ("x.txt", b"nada", "text/plain")}).json()
    tarefa = _aguardar(cliente, tarefa)
    assert tarefa["status"] == "erro" and tarefa["erro"]["codigo"] == "leitura_falhou"


def test_lancamento_em_lote(cliente):
    _, linha_a = montar_codigo("237", date.today() + timedelta(days=10), Decimal("10.00"), "1" * 25)
    _, linha_b = montar_codigo("237", date.today() + timedelta(days=11), Decimal("20.00"), "2" * 25)
    resposta = cliente.post("/api/boletos/lote", json={"boletos": [
        {"linha_digitavel": linha_a, "beneficiario": "Lote A", "valor": 10},
        {"linha_digitavel": linha_b, "beneficiario": "Lote B", "valor": 20},
        {"linha_digitavel": linha_a, "beneficiario": "Repetido no lote"},
        {"linha_digitavel": "123", "valor": 1},
    ]}).json()
    assert [c["indice"] for c in resposta["criados"]] == [0, 1]
    assert {e["indice"]: e["codigo"] for e in resposta["erros"]} == {2: "duplicado", 3: "linha_invalida"}
    assert resposta["pendente_gravacao"] is False
    for criado in resposta["criados"]:
        assert cliente.delete(f"/api/boletos/{criado['registro']['id']}").status_code == 204


def test_planilha_aberta_no_excel_nao_segura_lancamentos(cliente, monkeypatch):
    """Com o banco de dados, o lançamento é gravado na hora; a planilha Excel é atualizada quando for fechada."""
    def travada():
        raise PlanilhaBloqueadaError("A planilha está aberta em outro programa (ex.: Excel).")

    monkeypatch.setattr(planilha.excel, "_verificar_gravavel", travada)
    criado = cliente.post("/api/boletos", json={"beneficiario": "Com Excel aberto", "valor": 3, "ignorar_validacao": True}).json()
    assert criado["id"] > 0 and not criado.get("pendente_gravacao")
    assert cliente.get("/api/gravacao").json()["pendentes"] == 0
    assert planilha.exportar() is False and planilha.exportacao["excel_aberto"]

    monkeypatch.undo()
    assert planilha.exportar() and not planilha.exportacao["excel_aberto"]
    cliente.delete(f"/api/boletos/{criado['id']}")


def test_senha_de_acesso_para_aparelhos_da_rede(monkeypatch):
    monkeypatch.setattr(config, "SENHA_ACESSO", "segredo123")
    with TestClient(app, client=("192.168.0.50", 50000)) as remoto:
        assert remoto.get("/api/boletos").status_code == 401
        estado = remoto.get("/api/acesso/estado").json()
        assert estado["protegido"] and not estado["autorizado"] and not estado["local"]
        assert remoto.post("/api/acesso", json={"senha": "errada"}).status_code == 401
        assert remoto.post("/api/acesso", json={"senha": "segredo123"}).status_code == 200
        assert remoto.get("/api/boletos").status_code == 200
    with TestClient(app) as local:
        assert local.get("/api/boletos").status_code == 200

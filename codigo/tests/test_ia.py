"""Integração com IA usando um cliente Anthropic simulado (sem rede)."""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import ia
from app.boleto.codigo import formatar_linha
from app.main import app
from conftest import VALOR, VENCIMENTO


class ClienteFalso:
    ultima_chamada: dict = {}
    resposta: dict = {}
    stop_reason = "end_turn"

    def __init__(self, **kwargs):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._criar))

    def _criar(self, **kwargs):
        ClienteFalso.ultima_chamada = kwargs
        bloco = SimpleNamespace(type="text", text=json.dumps(ClienteFalso.resposta))
        return SimpleNamespace(stop_reason=ClienteFalso.stop_reason, content=[bloco])


@pytest.fixture()
def ia_simulada(monkeypatch):
    import anthropic

    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    monkeypatch.setattr(anthropic, "Anthropic", ClienteFalso)
    ClienteFalso.stop_reason = "end_turn"
    return ClienteFalso


def test_extrair_monta_pedido_e_le_json(ia_simulada, boleto_pdf):
    ia_simulada.resposta = {"linha_digitavel": "123", "beneficiario": "X", "documento_beneficiario": "",
                            "numero_documento": "", "vencimento": "", "valor": "", "observacoes": ""}
    dados = ia.extrair(boleto_pdf[0].read_bytes())
    assert dados["beneficiario"] == "X"
    chamada = ia_simulada.ultima_chamada
    assert chamada["model"] == "claude-opus-5"
    assert chamada["output_config"]["format"]["type"] == "json_schema"
    assert chamada["fallbacks"] == "default"
    assert chamada["messages"][0]["content"][0]["type"] == "document"


def test_recusa_vira_erro(ia_simulada, boleto_pdf):
    ia_simulada.stop_reason = "refusal"
    with pytest.raises(ia.ErroIA):
        ia.extrair(boleto_pdf[0].read_bytes())


def test_endpoint_mescla_e_valida_linha_da_ia(ia_simulada, boleto_pdf):
    caminho, linha = boleto_pdf
    # A IA erra um dígito: o sistema deve corrigir pelos DVs em vez de aceitar às cegas
    errada = linha[:15] + str((int(linha[15]) + 1) % 10) + linha[16:]
    ia_simulada.resposta = {
        "linha_digitavel": errada, "beneficiario": "Empresa Exemplo de Serviços Ltda",
        "documento_beneficiario": "12.345.678/0001-95", "numero_documento": "NF-2026/0457",
        "vencimento": VENCIMENTO.isoformat(), "valor": str(VALOR), "observacoes": "",
    }
    with TestClient(app) as cliente:
        with open(caminho, "rb") as f:
            leitura = cliente.post("/api/leituras", files={"arquivo": ("b.pdf", f, "application/pdf")}).json()
        resp = cliente.post(f"/api/leituras/{leitura['arquivo']['id']}/ia", json={"campos": {}, "pagina": 0})
    assert resp.status_code == 200, resp.text
    boleto = resp.json()
    assert boleto["ia_usada"]
    campos = boleto["campos"]
    assert campos["beneficiario"]["fonte"] == "ia"
    assert campos["valor"]["valor"] == float(VALOR)
    # O boleto de exemplo vence "hoje + 26 dias": conforme a data, um dígito errado tem uma ou várias correções possíveis
    codigo = boleto["codigo"] or {}
    if campos.get("linha_digitavel", {}).get("valor") == formatar_linha(linha):
        assert codigo["valido"]  # corrigida sozinha pelos dígitos verificadores
    elif not codigo.get("corrigido"):
        # correção ambígua: a linha errada da IA não é aceita e a certa aparece entre as sugestões
        assert not codigo.get("valido")
        assert formatar_linha(linha) in boleto["sugestoes_linha"]

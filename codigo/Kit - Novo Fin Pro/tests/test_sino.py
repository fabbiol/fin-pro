"""Sininho: avisos vistos saem da contagem; dispensados saem da lista; voltam quando a situação muda."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import main
from app.notificacoes.servico import ServicoNotificacoes


class FonteFalsa:
    def __init__(self, registros):
        self.registros = registros

    def listar(self):
        return [dict(r) for r in self.registros]


def test_avisos_vistos_dispensados_e_mudanca_de_situacao(tmp_path):
    hoje = date.today()
    fonte = FonteFalsa([
        {"id": 1, "beneficiario": "Fornecedor A", "valor": 10.0, "vencimento": hoje + timedelta(days=1), "status": "Pendente"},
        {"id": 2, "beneficiario": "Fornecedor B", "valor": 20.0, "vencimento": hoje, "status": "Pendente"},
    ])
    servico = ServicoNotificacoes(fonte, tmp_path / "notificacoes.json", "http://localhost:8000")

    alertas = servico.alertas()
    assert len(alertas) == 2 and not any(a["visto"] or a["dispensado"] for a in alertas)
    assert servico.marcar_vistos([a["chave"] for a in alertas] + ["aviso-inexistente"]) == 2
    assert all(a["visto"] for a in servico.alertas())

    chave_b = next(a["chave"] for a in servico.alertas() if a["id"] == 2)
    assert servico.dispensar(chave_b)
    assert [a["id"] for a in servico.alertas() if a["dispensado"]] == [2]

    # Guardado em arquivo: continua valendo depois de reiniciar o sistema
    reaberto = ServicoNotificacoes(fonte, tmp_path / "notificacoes.json", "http://localhost:8000")
    assert all(a["visto"] for a in reaberto.alertas())

    # O boleto 1 passa de "vence amanhã" para "vence hoje": volta a contar como aviso novo
    fonte.registros[0]["vencimento"] = hoje
    assert [a["id"] for a in servico.alertas() if not a["visto"]] == [1]

    assert servico.restaurar_dispensados() == 1
    assert not any(a["dispensado"] for a in servico.alertas())


def test_api_do_sininho():
    with TestClient(main.app) as cliente:
        dados = cliente.get("/api/notificacoes").json()
        assert "nao_vistos" in dados and all("chave" in a and "visto" in a for a in dados["alertas"])
        assert cliente.post("/api/notificacoes/vistos", json={"chaves": [a["chave"] for a in dados["alertas"]]}).status_code == 200
        assert cliente.get("/api/notificacoes").json()["nao_vistos"] == 0
        assert cliente.post("/api/notificacoes/dispensar", json={"chave": "inexistente"}).json() == {"dispensado": False}
        assert cliente.post("/api/notificacoes/restaurar").status_code == 200

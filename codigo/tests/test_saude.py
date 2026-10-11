"""Tela Saúde do sistema: diagnóstico sempre responde e aponta o que precisa de atenção."""

from fastapi.testclient import TestClient

from app import contexto, main


def test_diagnostico_e_acoes(monkeypatch):
    with TestClient(main.app) as cliente:
        dados = cliente.get("/api/saude").json()
        chaves = {i["chave"] for i in dados["itens"]}
        assert {"banco", "notificacoes", "backup", "entrada", "fila", "leitura", "disco", "rede"} <= chaves
        assert dados["situacao"] in ("ok", "aviso", "erro") and all(i["resumo"] for i in dados["itens"])
        backup = next(i for i in dados["itens"] if i["chave"] == "backup")
        assert backup["situacao"] == "desligado"

        assert cliente.post("/api/saude/atualizar-planilha").status_code == 200
        assert "liberados" in cliente.post("/api/saude/limpar-logs").json()

        # Um diagnóstico que falha não derruba os outros
        monkeypatch.setattr(contexto.backup, "status", lambda: 1 / 0)
        itens = cliente.get("/api/saude").json()["itens"]
        assert itens[0]["situacao"] == "erro" and "Não foi possível verificar" in itens[0]["resumo"]

"""Tela Saúde do sistema: diagnóstico sempre responde e aponta o que precisa de atenção."""

from fastapi.testclient import TestClient

from app import contexto, main, saude


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


class _Notificacoes:
    def __init__(self, ativos, ultimo):
        self.ativos, self.ultimo = ativos, ultimo

    def config_publica(self):
        return {"ativo": True, **{c: {"ativo": c in self.ativos} for c in ("windows", "telegram", "email")}}

    def historico(self, _quantidade):
        return [self.ultimo]


def test_falha_de_canal_ja_desligado_nao_aparece(monkeypatch):
    """Na VPS a notificação do Windows falhou e foi desligada: a falha antiga não fica aparecendo na Saúde."""
    ultimo = {"quando": "2026-10-12T15:30:00", "canais": {"windows": "erro: Notificações da área de trabalho estão "
                                                                     "disponíveis apenas no Windows.", "telegram": "ok"}}
    monkeypatch.setattr(contexto, "notificacoes", _Notificacoes({"telegram"}, ultimo))
    item = saude._notificacoes()
    assert item["situacao"] == "ok" and "Telegram" in item["resumo"]

    monkeypatch.setattr(contexto, "notificacoes", _Notificacoes({"telegram", "windows"}, ultimo))
    item = saude._notificacoes()
    assert item["situacao"] == "aviso" and "windows" in item["resumo"]

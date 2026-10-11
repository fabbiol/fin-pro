"""Senha de administrador: protege a importação de boletos, inclusive contra acesso direto à API."""

import pytest
from fastapi.testclient import TestClient

from app import admin, contexto, importacao, main


@pytest.fixture
def app_protegido(tmp_path, monkeypatch):
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    monkeypatch.setattr(contexto, "importacoes", importacao.ArmazemImportacoes(tmp_path / "importacoes"))
    return main.app


def test_importacao_so_abre_com_a_senha_de_administrador(app_protegido, tmp_path):
    with TestClient(app_protegido, client=("192.168.0.77", 50000)) as outro_aparelho:
        # Um aparelho da rede não consegue criar a senha nem usar a importação
        assert outro_aparelho.post("/api/admin/senha", json={"senha": "invasor123", "confirmacao": "invasor123"}).status_code in (401, 403)
        assert outro_aparelho.get("/api/importacao/modelo.xlsx").status_code in (401, 403)
    assert not contexto.administrador.senha_definida

    with TestClient(app_protegido, client=("127.0.0.1", 50000)) as computador:
        assert computador.get("/api/importacao/modelo.xlsx").json()["detail"]["codigo"] == "admin_sem_senha"
        assert computador.post("/api/admin/senha", json={"senha": "123", "confirmacao": "123"}).status_code == 422
        criada = computador.post("/api/admin/senha", json={"senha": "senha-do-dono", "confirmacao": "senha-do-dono"})
        assert criada.status_code == 200 and criada.json()["autorizado"]
        assert computador.get("/api/importacao/modelo.xlsx").status_code == 200
        assert computador.post("/api/importacao/" + "0" * 32 + "/previa", json={}).status_code == 404  # passou pela senha

        computador.post("/api/admin/sair")
        assert computador.get("/api/importacao/modelo.xlsx").json()["detail"]["codigo"] == "admin_necessario"
        assert computador.post("/api/importacao/" + "0" * 32 + "/importar", json={"indices": [0]}).status_code == 403
        assert computador.post("/api/admin/entrar", json={"senha": "senha-errada"}).status_code == 401
        assert computador.post("/api/admin/entrar", json={"senha": "senha-do-dono"}).status_code == 200
        assert computador.get("/api/admin").json()["autorizado"]

        # Trocar a senha exige a atual
        sem_atual = computador.post("/api/admin/senha", json={"senha": "nova-senha", "confirmacao": "nova-senha"})
        assert sem_atual.status_code == 403
        trocada = computador.post("/api/admin/senha", json={"senha": "nova-senha", "confirmacao": "nova-senha", "senha_atual": "senha-do-dono"})
        assert trocada.status_code == 200

    conteudo = (tmp_path / "admin.json").read_text(encoding="utf-8")
    assert "senha-do-dono" not in conteudo and "nova-senha" not in conteudo


def test_bloqueio_por_tentativas_e_fim_das_sessoes(tmp_path):
    gerenciador = admin.GerenciadorAdmin(tmp_path / "admin.json")
    gerenciador.definir_senha("senha-certa")
    for _ in range(admin.MAX_TENTATIVAS):
        assert gerenciador.entrar("errada", "10.0.0.9")[0] is None
    token, bloqueio = gerenciador.entrar("senha-certa", "10.0.0.9")
    assert token is None and bloqueio > 0  # nem a senha certa entra durante o bloqueio

    token, _ = gerenciador.entrar("senha-certa", "10.0.0.10")
    assert gerenciador.autorizado(token) and not gerenciador.autorizado("token-inventado")
    gerenciador.definir_senha("outra-senha")
    assert not gerenciador.autorizado(token)  # trocar a senha bloqueia quem estava liberado
    assert admin.GerenciadorAdmin(tmp_path / "admin.json").verificar("outra-senha")

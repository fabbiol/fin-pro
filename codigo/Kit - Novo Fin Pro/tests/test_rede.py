"""Acesso pelo celular: senha com hash, servidor de rede liga/desliga, login, bloqueio, sair e QR code."""

import json
import socket
import urllib.request

import pytest
from fastapi.testclient import TestClient

from app import acesso, config
from app.main import app, rede
from app.rede import GerenciadorRede, descobrir_enderecos, descrever_aparelho


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_senha_guardada_com_hash_e_troca_invalida_sessoes(tmp_path):
    gerenciador = GerenciadorRede(app, tmp_path / "rede.json", 0)
    with pytest.raises(ValueError):
        gerenciador.definir_senha("123")
    gerenciador.definir_senha("minha-senha")
    assert "minha-senha" not in (tmp_path / "rede.json").read_text(encoding="utf-8")
    assert gerenciador.verificar_senha("minha-senha") and not gerenciador.verificar_senha("outra")
    token = gerenciador.token_sessao()
    gerenciador.definir_senha("nova-senha-1")
    assert gerenciador.token_sessao() != token
    assert GerenciadorRede(app, tmp_path / "rede.json", 0).verificar_senha("nova-senha-1")


def test_liga_e_desliga_o_servidor_da_rede_sem_reiniciar(tmp_path):
    porta = _porta_livre()
    # 127.0.0.2 simula o endereço de rede sem abrir nada de verdade para o Wi-Fi
    gerenciador = GerenciadorRede(app, tmp_path / "rede.json", porta, descobrir=lambda: ["127.0.0.2"])
    with pytest.raises(ValueError):
        gerenciador.ativar()  # sem senha
    gerenciador.definir_senha("minha-senha")
    status = gerenciador.ativar()
    try:
        assert status["rodando"] and status["urls"] == [f"http://127.0.0.2:{porta}"]
        with urllib.request.urlopen(f"http://127.0.0.2:{porta}/api/acesso/estado", timeout=5) as resposta:
            assert "autorizado" in json.loads(resposta.read())
        assert GerenciadorRede(app, tmp_path / "rede.json", porta).ativo  # lembra que estava ligado
    finally:
        status = gerenciador.desativar()
    assert not gerenciador.rodando and not status["ativo"]
    with pytest.raises(OSError):
        urllib.request.urlopen(f"http://127.0.0.2:{porta}/api/acesso/estado", timeout=2)


def test_login_do_celular_bloqueio_sair_e_permissoes(monkeypatch):
    monkeypatch.setattr(config, "SENHA_ACESSO", "")
    monkeypatch.setattr(rede, "_estado", dict(rede._estado))
    acesso._falhas.clear()

    with TestClient(app, client=("127.0.0.1", 50000)) as computador:
        assert computador.post("/api/rede/senha", json={"senha": "celular123", "confirmacao": "outra123"}).status_code == 422
        assert computador.post("/api/rede/senha", json={"senha": "123", "confirmacao": "123"}).status_code == 422
        estado = computador.post("/api/rede/senha", json={"senha": "celular123", "confirmacao": "celular123"}).json()
        assert estado["senha_definida"] and estado["local"]

    with TestClient(app, client=("192.168.0.77", 50000)) as intruso:
        assert intruso.get("/api/boletos").status_code == 401
        assert intruso.post("/api/rede/senha", json={"senha": "hackeado1", "confirmacao": "hackeado1"}).status_code == 401
        for _ in range(5):
            assert intruso.post("/api/acesso", json={"senha": "errada"}).status_code in (401, 429)
        assert intruso.post("/api/acesso", json={"senha": "celular123"}).status_code == 429  # bloqueado

    with TestClient(app, client=("192.168.0.78", 50000)) as celular:
        assert celular.post("/api/acesso", json={"senha": "celular123"}).status_code == 200
        assert celular.get("/api/boletos").status_code == 200
        status = celular.get("/api/rede").json()
        assert status["local"] is False
        assert any(a["ip"] == "192.168.0.78" for a in status["acessos"])
        assert celular.post("/api/rede/ativar", json={"ativo": True}).status_code == 403  # só no computador
        celular.post("/api/acesso/sair")
        assert celular.get("/api/boletos").status_code == 401
    acesso._falhas.clear()


def test_qrcode_do_endereco(monkeypatch):
    monkeypatch.setattr(rede, "status", lambda: {"urls": ["http://192.168.0.10:8000"]})
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/rede/qrcode.svg")
    assert resposta.status_code == 200 and resposta.text.lstrip().startswith("<svg")


def test_utilitarios_de_rede():
    assert all(isinstance(ip, str) for ip in descobrir_enderecos())
    agente = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36"
    assert descrever_aparelho(agente) == "Android · Chrome"

"""Telegram para várias pessoas e grupos do escritório."""

import json

from app.notificacoes import canais, servico as modulo_servico
from app.notificacoes.servico import MASCARA, ServicoNotificacoes


class FonteVazia:
    def listar(self):
        return []


def _servico(tmp_path):
    return ServicoNotificacoes(FonteVazia(), tmp_path / "notificacoes.json", "http://localhost:8000")


def test_configuracao_antiga_com_um_chat_vira_lista(tmp_path):
    (tmp_path / "notificacoes.json").write_text(
        json.dumps({"telegram": {"ativo": True, "token": "123:abc", "chat_id": "42"}}), encoding="utf-8")
    publica = _servico(tmp_path).config_publica()["telegram"]
    assert publica["destinatarios"] == [{"chat_id": "42", "nome": "Principal", "tipo": "privado", "ativo": True}]
    assert publica["token"] == MASCARA


def test_salva_destinatarios_sem_repetidos_nem_invalidos(tmp_path):
    servico = _servico(tmp_path)
    publica = servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "destinatarios": [
        {"chat_id": "111", "nome": "  Fábio  "},
        {"chat_id": "111", "nome": "Repetido"},
        {"chat_id": "-100222", "nome": "Escritório", "ativo": True},
        {"chat_id": "abc", "nome": "Inválido"},
        {"chat_id": "333", "nome": "", "ativo": False},
    ]}})["telegram"]
    assert [(d["chat_id"], d["nome"], d["tipo"], d["ativo"]) for d in publica["destinatarios"]] == [
        ("111", "Fábio", "privado", True), ("-100222", "Escritório", "grupo", True), ("333", "Sem nome", "privado", False)]
    assert publica["chat_id"] == "111"


def test_envia_para_todos_os_ativos_e_informa_quem_nao_recebeu(tmp_path, monkeypatch):
    servico = _servico(tmp_path)
    servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "destinatarios": [
        {"chat_id": "1", "nome": "Fábio"}, {"chat_id": "2", "nome": "Maria"},
        {"chat_id": "3", "nome": "João", "ativo": False}, {"chat_id": "-4", "nome": "Grupo Escritório"}]}})
    enviados = []

    def enviar(token, chat_id, texto):
        enviados.append(chat_id)
        if chat_id == "2":
            raise canais.ErroCanal("Telegram: a pessoa ainda não enviou /start para o bot ou bloqueou o bot.")

    monkeypatch.setattr(modulo_servico.canais, "enviar_telegram", enviar)
    resultado = servico.testar("telegram")
    assert enviados == ["1", "2", "-4"]  # João está desligado
    assert resultado["canais"]["telegram"].startswith("erro: enviado para 2 de 3; não receberam: Maria (a pessoa ainda não enviou /start")

    enviados.clear()
    servico.testar_destinatario_telegram("1")
    assert enviados == ["1"]


def test_procura_pessoas_e_grupos_que_falaram_com_o_bot(monkeypatch):
    respostas = {
        "getMe": {"username": "boletos_escritorio_bot", "first_name": "Boletos"},
        "getUpdates": [
            {"message": {"chat": {"id": 1, "type": "private", "first_name": "Fábio", "username": "fabio"}, "text": "/start"}},
            {"my_chat_member": {"chat": {"id": -100, "type": "supergroup", "title": "Escritório"},
                                "new_chat_member": {"status": "member"}}},
            {"message": {"chat": {"id": 2, "type": "private", "first_name": "Maria", "last_name": "Souza"}, "text": "/start"}},
            {"my_chat_member": {"chat": {"id": -200, "type": "group", "title": "Grupo antigo"},
                                "new_chat_member": {"status": "left"}}},
            {"message": {"chat": {"id": 1, "type": "private", "first_name": "Fábio"}, "text": "oi"}},
        ],
    }
    monkeypatch.setattr(canais, "_telegram", lambda token, metodo, dados=None: respostas[metodo])
    encontrados = canais.procurar_chats_telegram("123:abc")
    assert encontrados["bot"]["usuario"] == "boletos_escritorio_bot"
    assert [(c["chat_id"], c["nome"], c["tipo"]) for c in encontrados["chats"]] == [
        ("1", "Fábio", "privado"), ("2", "Maria Souza", "privado"), ("-100", "Escritório", "grupo")]

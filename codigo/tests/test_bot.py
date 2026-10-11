"""Comandos do bot do Telegram (/vencidos, /hoje, /semana, /buscar, /previsao, /resumo)."""

from datetime import date, timedelta

import pytest

from app import bot, contexto, entrada
from app.banco import BancoBoletos
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.repositorio import RepositorioBoletos

HOJE = date(2026, 9, 17)


@pytest.fixture
def dados(tmp_path, monkeypatch):
    banco = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx")
    banco.migrar()
    fila = FilaGravacao(banco, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(banco, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(banco, fila, "pix"))
    banco.adicionar({"beneficiario": "CLA AUTO PECAS", "valor": 270.35, "vencimento": HOJE - timedelta(days=4),
                     "linha_digitavel": "34191.09123 34567.812341 56789.012301 2 15820000015000", "centro_custo": "Oficina"})
    banco.adicionar({"beneficiario": "Energisa", "valor": 487.32, "vencimento": HOJE})
    banco.adicionar({"beneficiario": "Aluguel", "valor": 2000, "vencimento": HOJE + timedelta(days=5)})
    banco.adicionar({"beneficiario": "Já pago", "valor": 50, "vencimento": HOJE - timedelta(days=1), "status": "Pago",
                     "data_pagamento": HOJE, "valor_pago": 55.0, "juros_multa": 5.0})
    banco.adicionar({"recebedor": "Magno Alves", "tipo_chave": "email", "chave": "magno@email.com", "valor": 1600,
                     "vencimento": HOJE - timedelta(days=1)}, "pix")
    return banco


def test_comandos_listam_com_linha_digitavel_e_pix_copia_e_cola(dados):
    vencidos = "\n".join(bot.responder("/vencidos", hoje=HOJE))
    assert "Em atraso</b> — 2 lançamento(s), R$ 1.870,35" in vencidos
    # só os números: tocar no <code> copia a linha pronta para colar no banco (sem pontos nem espaços)
    assert "<code>34191091233456781234156789012301215820000015000</code>" in vencidos
    assert "4 dias de atraso" in vencidos and "Magno Alves" in vencidos and "Copia e Cola: <code>000201" in vencidos
    assert "Já pago" not in vencidos

    assert "Energisa" in bot.responder("/hoje@boletos_bot", hoje=HOJE)[0]
    semana = bot.responder("/semana", hoje=HOJE)[0]
    assert "Energisa" in semana and "Aluguel" in semana and "CLA" not in semana
    assert "CLA AUTO PECAS" in bot.responder("/buscar cla auto", hoje=HOJE)[0]
    assert "Nenhum boleto" in bot.responder("/buscar inexistente", hoje=HOJE)[0]

    previsao = bot.responder("/previsao", hoje=HOJE)[0]
    assert "Em atraso: R$ 1.870,35 (2)" in previsao and "Próximos 7 dias: <b>R$ 2.487,32</b>" in previsao
    resumo = bot.responder("/resumo", hoje=HOJE)[0]
    assert "Pago neste mês: <b>R$ 55,00</b> (1) · juros/multas R$ 5,00" in resumo
    assert "/vencidos" in bot.responder("/start", "Almir", hoje=HOJE)[0]
    assert "Não conheço" in bot.responder("/xyz", hoje=HOJE)[0]
    assert bot.responder("bom dia", hoje=HOJE) is None


def test_listas_grandes_sao_divididas(dados):
    for n in range(60):
        dados.adicionar({"beneficiario": f"Fornecedor {n} " + "X" * 40, "valor": 10, "vencimento": HOJE - timedelta(days=2),
                         "linha_digitavel": "34191.09123 34567.812341 56789.012301 2 15820000015000"})
    mensagens = bot.responder("/vencidos", hoje=HOJE)
    assert len(mensagens) > 1 and all(len(m) <= 4096 for m in mensagens)
    assert "… e mais" in mensagens[-1]


def test_bot_responde_so_para_cadastrados(tmp_path, monkeypatch, dados):
    enviados, chamadas = [], []
    atualizacoes = [
        {"update_id": 1, "message": {"chat": {"id": 42, "type": "private"}, "from": {"first_name": "Almir"}, "text": "/vencidos"}},
        {"update_id": 2, "message": {"chat": {"id": 99, "type": "private"}, "from": {"first_name": "Estranho"}, "text": "/vencidos"}},
    ]

    def telegram_falso(token, metodo, dados_pedido=None):
        chamadas.append(metodo)
        if metodo == "getUpdates":
            return atualizacoes if not (dados_pedido or {}).get("offset") else []
        if metodo == "sendMessage":
            enviados.append((dados_pedido["chat_id"], dados_pedido["text"]))
        return {}

    monkeypatch.setattr(canais, "_telegram", telegram_falso)
    monkeypatch.setattr(canais, "enviar_telegram", lambda token, chat_id, texto: enviados.append((chat_id, texto)))
    caixa = entrada.CaixaEntrada(tmp_path / "entrada.json", lambda d, n: {}, lambda d, n: {}, lambda: ("123:abc", [{"chat_id": "42", "nome": "Almir"}]),
                                 comandos=bot)
    caixa.verificar_telegram()
    caixa.verificar_telegram()
    assert chamadas.count("setMyCommands") == 1
    assert any(chat == "42" and "Em atraso" in texto for chat, texto in enviados)
    assert any(chat == "99" and "peça ao responsável" in texto for chat, texto in enviados)
    assert not any(chat == "99" and "CLA" in texto for chat, texto in enviados)

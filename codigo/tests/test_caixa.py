"""Caixa: entradas e saídas em dinheiro, períodos, relatórios, leitura do cupom, bot do caixa e aba Gastos."""

from datetime import date

import pytest

from app import contexto, servicos
from app.banco import BancoBoletos
from app.caixa import leitura, servico
from app.caixa.bot import BotCaixa
from app.fila_gravacao import FilaGravacao
from app.repositorio import RepositorioBoletos

CUPOM = """POSTO SAO JORGE LTDA
CNPJ: 12.345.678/0001-95 IE: 123456789
AV BRASIL, 100 - MIRASSOL SP
DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETRONICA
001 GASOLINA COMUM 30,000 L 5,99 179,70
Qtde. total de itens 1
Valor total R$ 179,70
Desconto R$ 0,00
Valor a Pagar R$ 179,70
FORMA DE PAGAMENTO VALOR PAGO
Dinheiro 200,00
Troco R$ 20,30
Valor aprox. dos tributos R$ 45,00 (Lei 12.741)
Emissao: 21/09/2026 14:35:10
"""


@pytest.fixture(autouse=True)
def banco(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    planilha.garantir()
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "repositorio_caixa", RepositorioBoletos(planilha, fila, "caixa"))
    yield planilha
    planilha.parar()


def _saida(valor, dia, centro="Combustível e Veículos", local="Posto São Jorge", pessoa="Almir", descricao="gasolina"):
    return servico.lancar({"movimento": "Saída", "valor": valor, "data": dia, "centro_custo": centro, "local": local,
                           "pessoa": pessoa, "descricao": descricao}, "Fábio")


def _entrada(valor, dia, descricao="Pedido 7043 - brita"):
    return servico.lancar({"movimento": "Entrada", "valor": valor, "data": dia, "descricao": descricao}, "Fábio")


# --------------------------------------------------------------------------- períodos


def test_periodos_dia_semana_mes_e_ano():
    ref = date(2026, 9, 22)  # terça-feira
    assert servico.periodo("dia", ref)[:2] == (ref, ref)
    assert servico.periodo("semana", ref)[:2] == (date(2026, 9, 21), date(2026, 9, 27))
    assert servico.periodo("mes", ref)[:2] == (date(2026, 9, 1), date(2026, 9, 30))
    assert servico.periodo("ano", ref)[:2] == (date(2026, 1, 1), date(2026, 12, 31))
    assert servico.periodo("mes", date(2026, 12, 5))[1] == date(2026, 12, 31)
    assert servico.deslocar("mes", date(2026, 1, 15), -1) == date(2025, 12, 1)
    assert servico.deslocar("semana", ref, 1) == date(2026, 9, 29)
    with pytest.raises(servico.ErroCaixa):
        servico.periodo("hora", ref)


# --------------------------------------------------------------------------- lançamentos e resumo


def test_lanca_entrada_e_saida_e_valida():
    entrada = _entrada(500, date(2026, 9, 21))
    assert entrada["movimento"] == "Entrada" and entrada["status"] == "Confirmado" and entrada["lancado_por"] == "Fábio"
    saida = servico.lancar({"movimento": "saida", "valor": "45.9", "data": "2026-09-21"}, "Almir")
    assert saida["movimento"] == "Saída" and saida["valor"] == 45.9
    with pytest.raises(servico.ErroCaixa):
        servico.lancar({"movimento": "Entrada", "valor": 0})
    with pytest.raises(servico.ErroCaixa):
        servico.lancar({"movimento": "Talvez", "valor": 10})


def test_resumo_do_periodo_com_saldo_e_onde_mais_se_gastou():
    _entrada(1000, date(2026, 8, 30))  # mês anterior: vira saldo inicial
    _entrada(500, date(2026, 9, 10))
    _entrada(300, date(2026, 9, 15), "Pedido 7120 - pedrisco")
    _saida(179.70, date(2026, 9, 21))
    _saida(120.30, date(2026, 9, 22), centro="Obras", local="Loja do Zé", pessoa="Bia", descricao="cimento")
    _saida(50, date(2026, 9, 22), local="Posto São Jorge")
    cancelada = _saida(999, date(2026, 9, 22))
    servico.cancelar(cancelada["id"], "Fábio")

    r = servico.resumo("mes", date(2026, 9, 22))
    assert r["periodo"]["rotulo"] == "setembro de 2026"
    assert r["entradas"] == {"total": 800.0, "quantidade": 2, "media": 400.0,
                             "maior": {"valor": 500.0, "descricao": "Pedido 7043 - brita", "data": date(2026, 9, 10)}}
    assert r["saidas"]["total"] == 350.0 and r["saidas"]["quantidade"] == 3  # a cancelada não conta
    assert r["saldo_periodo"] == 450.0
    assert r["saldo_inicial"] == 1000.0 and r["saldo_caixa"] == 1450.0
    assert [(c["nome"], c["total"]) for c in r["por_centro"]] == [("Combustível e Veículos", 229.7), ("Obras", 120.3)]
    assert r["por_local"][0] == {"nome": "Posto São Jorge", "total": 229.7, "quantidade": 2, "percentual": 65.6}
    assert {p["nome"] for p in r["por_pessoa"]} == {"Almir", "Bia"}
    assert len(r["serie"]) == 30 and next(s for s in r["serie"] if s["rotulo"] == "22/09")["saidas"] == 170.3


def test_filtro_por_dia_semana_e_ano():
    _saida(10, date(2026, 9, 20))  # domingo, semana anterior
    _saida(20, date(2026, 9, 21))
    _saida(30, date(2026, 9, 22))
    assert servico.resumo("dia", date(2026, 9, 22))["saidas"]["total"] == 30
    assert servico.resumo("semana", date(2026, 9, 22))["saidas"]["total"] == 50
    ano = servico.resumo("ano", date(2026, 9, 22))
    assert ano["saidas"]["total"] == 60 and len(ano["serie"]) == 12


# --------------------------------------------------------------------------- aba Gastos


def test_gastos_em_dinheiro_entram_na_analise_de_gastos():
    _saida(179.70, date(2026, 9, 21))
    _entrada(500, date(2026, 9, 21))  # entrada não é gasto
    analise = servicos.analise_gastos([], [], servico.saidas_para_gastos(), de=date(2026, 9, 1), ate=date(2026, 9, 30))
    assert analise["total"] == 179.7 and analise["total_dinheiro"] == 179.7
    assert analise["centros"][0]["centro"] == "Combustível e Veículos" and analise["centros"][0]["dinheiro"] == 179.7
    assert analise["maiores"][0]["nome"] == "Posto São Jorge"
    so_boletos = servicos.analise_gastos([], [], servico.saidas_para_gastos(), tipo="boleto")
    assert so_boletos["total"] == 0


def test_gastos_em_dinheiro_entram_no_fechamento_do_mes():
    from app import fechamento

    _saida(179.70, date(2026, 9, 21))
    f = fechamento.montar([], [], date(2026, 9, 1), caixa=servico.saidas_para_gastos())
    assert f["totais"]["pago"] == 179.7 and f["totais"]["dinheiro"] == 1
    assert f["pagos"][0]["tipo"] == "Dinheiro" and f["pagos"][0]["nome"] == "Posto São Jorge"


# --------------------------------------------------------------------------- leitura do cupom


def test_le_o_valor_a_pagar_e_nao_o_troco():
    lido = leitura.analisar_texto(CUPOM, hoje=date(2026, 9, 22))
    assert lido["valor"] == 179.70  # não 200,00 (dinheiro entregue) nem 20,30 (troco)
    assert lido["data"] == date(2026, 9, 21) and lido["hora"] == "14:35"
    assert lido["local"] == "POSTO SAO JORGE LTDA" and lido["cnpj"] == "12345678000195"


def test_recibo_simples_sem_rotulo():
    assert leitura.valor_total("Recibo\nRecebi de Prospera a quantia de R$ 85,00\nreferente a frete") == 85.0
    assert leitura.valor_total("sem valor nenhum") is None


# --------------------------------------------------------------------------- bot do caixa


class Telegram:
    """Telegram de mentira: guarda o que o bot mandou e entrega as mensagens que o teste quiser."""

    def __init__(self):
        self.enviadas = []
        self.fila = []

    def __call__(self, token, metodo, dados=None):
        if metodo == "getUpdates":
            fila, self.fila = self.fila, []
            return fila
        if metodo == "sendMessage":
            self.enviadas.append(dados)
        return {}

    def ultima(self):
        return self.enviadas[-1]

    def botoes(self):
        teclado = (self.ultima().get("reply_markup") or {}).get("inline_keyboard") or []
        return [b for linha in teclado for b in linha]


@pytest.fixture
def bot(tmp_path, monkeypatch):
    telegram = Telegram()
    monkeypatch.setattr("app.notificacoes.canais._telegram", telegram)
    monkeypatch.setattr("app.notificacoes.canais.baixar_arquivo_telegram", lambda token, file_id: f"foto {file_id}".encode())
    centros = ["Administrativo", "Combustível e Veículos", "Obras"]

    def criar_centro(nome, usuario):
        centros.append(nome)
        return nome

    caixa = BotCaixa(tmp_path / "caixa_bot.json",
                     lambda dados, nome: {"id": "a1", "nome": nome, "caminho": "arquivos/a1.jpg"},
                     lambda: {"111": "Almir", "222": "Fábio"},  # vindos dos bots de boletos e de notas
                     lambda: list(centros), criar_centro,
                     ler=lambda dados, nome: leitura.analisar_texto(CUPOM, hoje=date(2026, 9, 22)))
    caixa.configurar({"token": "123:abc", "ativo": True})
    caixa.telegram = telegram
    caixa.lista_centros = centros
    return caixa


def _foto(chat="111", arquivo="f1"):
    return {"update_id": 1, "message": {"chat": {"id": int(chat)}, "from": {"first_name": "Almir"},
                                        "photo": [{"file_id": arquivo, "file_size": 1000}]}}


def _texto(texto, chat="111"):
    return {"update_id": 2, "message": {"chat": {"id": int(chat)}, "from": {"first_name": "Almir"}, "text": texto}}


def _clique(dado, chat="111"):
    return {"update_id": 3, "callback_query": {"id": "cb", "data": dado,
                                               "message": {"message_id": 9, "chat": {"id": int(chat)}}}}


def _receber(bot, *atualizacoes):
    bot.telegram.fila = list(atualizacoes)
    bot.verificar()


def test_foto_do_cupom_vira_conversa_e_fica_pronta_para_revisar(bot):
    _receber(bot, _foto())
    pergunta = bot.telegram.ultima()["text"]
    assert "R$ 179,70" in pergunta and "Onde foi gasto?" in pergunta

    _receber(bot, _texto("gasolina da caminhonete"))
    assert "Qual o centro de custo?" in bot.telegram.ultima()["text"]
    botoes = bot.telegram.botoes()
    assert [b["text"] for b in botoes] == ["Administrativo", "Combustível e Veículos", "Obras",
                                            "➕ Cadastrar um novo centro de custo"]

    _receber(bot, _clique("cc:1"))
    assert "Anotado" in bot.telegram.ultima()["text"]
    item = bot.listar()[0]
    assert item["estado"] == "pendente" and bot.contagem() == 1
    assert item["dados"] == {"movimento": "Saída", "valor": 179.7, "data": "2026-09-21", "hora": "14:35",
                             "descricao": "gasolina da caminhonete", "local": "POSTO SAO JORGE LTDA",
                             "centro_custo": "Combustível e Veículos", "pessoa": "Almir"}


def test_revisar_na_tela_lanca_no_caixa_com_o_comprovante(bot):
    _receber(bot, _foto(), _texto("gasolina"), _clique("cc:1"))
    item = bot.listar()[0]
    lancado = bot.confirmar(item["id"], {"valor": 180.0}, "Fábio")  # ajustou o valor na revisão
    assert lancado["estado"] == "lancado" and bot.contagem() == 0
    registro = contexto.repositorio_caixa.listar()[0]
    assert registro["valor"] == 180.0 and registro["movimento"] == "Saída"
    assert registro["centro_custo"] == "Combustível e Veículos" and registro["arquivo"] == "arquivos/a1.jpg"
    assert registro["lancado_por"] == "Fábio"


def test_cadastrar_um_centro_de_custo_novo_pelo_bot(bot):
    _receber(bot, _foto(), _texto("peças do trator"), _clique("cc:novo"))
    assert "nome do novo centro" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("Manutenção de máquinas"))
    assert "Manutenção de máquinas" in bot.lista_centros
    assert bot.listar()[0]["dados"]["centro_custo"] == "Manutenção de máquinas"


def test_digitar_o_nome_do_centro_tambem_funciona(bot):
    _receber(bot, _foto(), _texto("cimento"), _texto("obras"))
    assert bot.listar()[0]["dados"]["centro_custo"] == "Obras"

    _receber(bot, _foto(arquivo="f2"), _texto("lanche"), _texto("Cozinha"))
    assert "Não achei" in bot.telegram.ultima()["text"]
    _receber(bot, _clique("cc:criar"))
    assert "Cozinha" in bot.lista_centros and bot.contagem() == 2


def test_pergunta_o_valor_quando_nao_consegue_ler(bot):
    bot.ler = lambda dados, nome: {"valor": None, "local": ""}
    _receber(bot, _foto())
    assert "Qual foi o valor?" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("quarenta"))
    assert "Não entendi o valor" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("45,90"))
    assert "Onde foi gasto?" in bot.telegram.ultima()["text"]
    assert bot.listar()[0]["dados"]["valor"] == 45.9


def test_quem_nao_esta_nos_outros_bots_e_recusado(bot):
    _receber(bot, _foto(chat="999"))
    assert "Só usa quem já está cadastrado" in bot.telegram.ultima()["text"]
    assert bot.listar() == []


def test_cancelar_desiste_do_gasto(bot):
    _receber(bot, _foto(), _texto("/cancelar"))
    assert "cancelei" in bot.telegram.ultima()["text"]
    assert bot.listar() == []


def test_a_mesma_foto_nao_entra_duas_vezes(bot):
    _receber(bot, _foto())
    _receber(bot, _foto())
    assert "já tinha sido enviado" in bot.telegram.ultima()["text"]
    assert len(bot.listar()) == 1


# --------------------------------------------------------------------------- API


def test_api_do_caixa_e_gastos_em_dinheiro():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        criada = cliente.post("/api/caixa", json={"movimento": "Saída", "valor": 179.70, "data": "2026-09-21",
                                                  "descricao": "gasolina", "local": "Posto São Jorge",
                                                  "centro_custo": "Combustível e Veículos"})
        assert criada.status_code == 201, criada.text
        cliente.post("/api/caixa", json={"movimento": "Entrada", "valor": 500, "data": "2026-09-21",
                                         "descricao": "Pedido 7043"})
        assert cliente.post("/api/caixa", json={"movimento": "Entrada", "valor": 0}).status_code == 422

        resumo = cliente.get("/api/caixa?periodo=semana&data=2026-09-22").json()
        assert resumo["entradas"]["total"] == 500 and resumo["saidas"]["total"] == 179.7
        assert resumo["periodo"]["inicio"] == "2026-09-21" and resumo["saldo_periodo"] == 320.3

        excel = cliente.get("/api/caixa/relatorio/arquivo?periodo=mes&data=2026-09-22")
        assert excel.status_code == 200 and excel.content[:2] == b"PK"

        gastos = cliente.get("/api/gastos?tipo=dinheiro").json()
        assert gastos["total_dinheiro"] == 179.7 and gastos["total"] == 179.7
        centros = {c["nome"]: c for c in cliente.get("/api/centros").json()["centros"]}
        assert centros["Combustível e Veículos"]["dinheiro"] == 1

        id_ = criada.json()["id"]
        assert cliente.post(f"/api/caixa/{id_}/cancelar").json()["status"] == "Cancelado"
        assert cliente.get("/api/caixa?periodo=semana&data=2026-09-22").json()["saidas"]["total"] == 0
        assert cliente.get(f"/api/caixa/{id_}/historico").json()["eventos"][0]["acao"] == "Cancelamento"

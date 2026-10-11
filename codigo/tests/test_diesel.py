"""Diesel: compras, abastecimentos, saldo, médias por máquina, relatórios, leitura dos canhotos e o bot do diesel."""

from datetime import date, datetime

import pytest

from app import contexto
from app.banco import BancoBoletos
from app.diesel import leitura, servico
from app.diesel.bot import BotDiesel
from app.diesel.modelos import ABAS_DIESEL
from app.notificacoes import canais

SEGUNDA = date(2026, 9, 21)

CANHOTO = """AUTO POSTO RODOVIA LTDA
CNPJ 12.345.678/0001-95
REQUISICAO DE ABASTECIMENTO
DATA: 28/09/2026 10:42
PLACA: ABC-1D23  KM: 152.340
PRODUTO: OLEO DIESEL S10
QTD: 185,40 L
PRECO UNIT: 5,899
TOTAL R$ 1.093,67
ASSINATURA MOTORISTA
"""

COMPROVANTE_COMPRA = """Comprovante de transferencia Pix
Valor pago R$ 5.990,00
Data 22/09/2026 09:15
Favorecido AUTO POSTO RODOVIA LTDA
ID da transacao E12345678202609221215abcdef
"""


@pytest.fixture(autouse=True)
def banco(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DADOS_DIR", tmp_path)  # a tabela de preços fica na pasta do teste
    diesel = BancoBoletos(tmp_path / "diesel.db", tmp_path / "diesel.xlsx", tmp_path / "backups",
                          abas=ABAS_DIESEL, centros=False, nome_backup="diesel")
    diesel.garantir()
    monkeypatch.setattr(contexto, "diesel", diesel)
    yield diesel
    diesel.parar()


@pytest.fixture
def frota():
    servico.salvar_maquina({"nome": "Escavadeira PC200", "tipo": "Máquina"}, "Fábio")  # horímetro
    servico.salvar_maquina({"nome": "Caminhão Volvo", "tipo": "Caminhão", "placa": "abc-1d23"}, "Fábio")  # km
    servico.salvar_maquina({"nome": "Gerador", "tipo": "Gerador", "medidor": ""}, "Fábio")


# --------------------------------------------------------------------------- serviço


def test_saldo_compras_menos_abastecimentos(frota):
    servico.lancar_compra({"data": date(2026, 9, 15), "valor": 5900}, "Fábio")  # sem litros: 1.000 L padrão
    compra = servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "valor": 5990}, "Fábio")
    assert compra["preco_litro"] == 5.99
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Escavadeira PC200", "litros": 180}, "Almir")
    cancelado = servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Gerador", "litros": 50}, "Almir")
    servico.cancelar("abastecimentos", cancelado["id"])
    saldo = servico.saldo()
    assert saldo["comprado"] == 2000 and saldo["abastecido"] == 180 and saldo["litros"] == 1820
    assert saldo["ultima_compra"]["litros"] == 1000 and saldo["ultima_compra"]["usados_desde"] == 180
    # em reais: o que foi pago − os abastecimentos (sem preço na tabela, vale o preço médio das compras: R$ 5,945)
    assert (saldo["pago"], saldo["gasto"], saldo["valor"]) == (11890, 1070.1, 10819.9)


def test_consumo_pelo_horimetro_e_pelo_km(frota):
    for dia, litros, horas in ((21, 150, 1000), (23, 160, 1011), (25, 170, 1022)):
        servico.lancar_abastecimento({"data": date(2026, 9, dia), "maquina": "Escavadeira PC200", "litros": litros,
                                      "medidor": horas}, "Almir")
    for dia, litros, km in ((21, 200, 150000), (24, 180, 150720)):
        servico.lancar_abastecimento({"data": date(2026, 9, dia), "maquina": "caminhão volvo", "litros": litros,
                                      "medidor": km}, "Almir")
    r = servico.resumo("semana", SEGUNDA)
    por_nome = {m["maquina"]: m for m in r["por_maquina"]}
    # 22 horas trabalhadas com 330 L (o 1º abastecimento só marca o início) = 15 L/h
    assert por_nome["Escavadeira PC200"]["consumo"]["rotulo"] == "15.0 L/h".replace(".", ",")
    assert por_nome["Caminhão Volvo"]["consumo"]["rotulo"] == "4,0 km/L"  # 720 km com 180 L
    assert por_nome["Escavadeira PC200"]["litros"] == 480 and por_nome["Escavadeira PC200"]["abastecimentos"] == 3
    assert r["abastecido"]["litros"] == 860 and r["sem_abastecimento"] == ["Gerador"]


def test_periodos_semana_quinzena_e_mes():
    assert servico.periodo("quinzena", date(2026, 9, 10))[:2] == (date(2026, 9, 1), date(2026, 9, 15))
    assert servico.periodo("quinzena", date(2026, 9, 29))[:2] == (date(2026, 9, 16), date(2026, 9, 30))
    assert servico.periodo("quinzena", date(2026, 2, 20))[:2] == (date(2026, 2, 16), date(2026, 2, 28))
    assert servico.deslocar("quinzena", date(2026, 9, 1), -1) == date(2026, 8, 16)
    assert servico.deslocar("quinzena", date(2026, 9, 16), 1) == date(2026, 10, 1)
    assert servico.periodo("semana", date(2026, 9, 24))[:2] == (SEGUNDA, date(2026, 9, 27))


def test_maquina_pela_placa_e_renomear_leva_os_abastecimentos(frota):
    assert servico.maquina_por_nome("ABC1D23")["nome"] == "Caminhão Volvo"
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Caminhão Volvo", "litros": 100}, "Almir")
    volvo = servico.maquina_por_nome("Caminhão Volvo")
    servico.salvar_maquina({"nome": "Caminhão Volvo FH"}, "Fábio", volvo["id"])
    assert servico.abastecimentos()[0]["maquina"] == "Caminhão Volvo FH"
    with pytest.raises(servico.ErroDiesel):
        servico.salvar_maquina({"nome": "gerador"}, "Fábio")  # repetida


def test_texto_do_relatorio(frota):
    servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "valor": 5990}, "Fábio")
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Gerador", "litros": 60}, "Almir")
    texto = servico.texto_relatorio("semana", SEGUNDA)
    assert "Relatório semanal" in texto and "Comprado: <b>1.000 L</b>" in texto and "Gerador: 60 L (100%)" in texto
    assert "Saldo no fim do período: <b>R$ 5.630,60</b>" in texto  # R$ 5.990 − 60 L × R$ 5,99


# --------------------------------------------------------------------------- leitura


def test_le_o_canhoto():
    lido = leitura.analisar_texto(CANHOTO, hoje=date(2026, 9, 29))
    assert lido["tipo"] == "canhoto" and lido["litros"] == 185.40
    assert lido["valor"] == 1093.67 and lido["preco_litro"] == 5.899
    assert lido["data"] == date(2026, 9, 28) and lido["hora"] == "10:42"
    assert lido["placa"] == "ABC-1D23" and lido["medidor"] == 152340


def test_le_o_comprovante_da_compra_e_a_legenda_decide():
    lido = leitura.analisar_texto(COMPROVANTE_COMPRA, hoje=date(2026, 9, 29))
    assert lido["tipo"] == "compra" and lido["valor"] == 5990.00 and lido["litros"] is None
    assert leitura.analisar_texto("foto borrada", "canhoto escavadeira 120 litros")["tipo"] == "canhoto"
    assert leitura.analisar_texto("foto borrada", "canhoto escavadeira 120 litros")["litros"] == 120
    assert leitura.analisar_texto("foto borrada")["tipo"] == ""  # não sabe: o bot pergunta


# --------------------------------------------------------------------------- bot


@pytest.fixture
def bot(tmp_path, monkeypatch, frota):
    enviados = []

    def telegram(token, metodo, dados=None):
        enviados.append((metodo, dados or {}))
        return {"message_id": 1} if metodo.startswith("send") else True

    monkeypatch.setattr(canais, "_telegram", telegram)
    pessoas = {"100": "Fábio", "200": "Almir"}
    leituras = {}
    b = BotDiesel(tmp_path / "diesel_bot.json",
                  lambda dados, nome: {"id": "a1", "nome": nome, "caminho": "arquivos/a1.jpg"},
                  lambda: pessoas, ler=lambda dados, nome, legenda: dict(leituras.get(dados, {})))
    b.configurar({"token": "123:abc", "gestores": ["100"]})
    b.enviados, b.leituras = enviados, leituras
    return b


def _textos(enviados, chat_id):
    return [d.get("text") or d.get("caption") or "" for m, d in enviados if str(d.get("chat_id")) == chat_id]


def test_canhoto_vai_para_o_responsavel_escolher_a_maquina(bot):
    servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "valor": 5990}, "Fábio")
    bot.leituras[b"foto1"] = {"tipo": "canhoto", "litros": 180.0, "data": date(2026, 9, 28), "posto": "Posto Rodovia"}
    bot._nova_foto("200", "Almir", b"foto1", "canhoto.jpg", file_id="F1", foto=True)

    # o Almir fica sabendo que foi para o Fábio; o Fábio recebe a foto com as máquinas em botões
    assert "Mandei para Fábio" in _textos(bot.enviados, "200")[-1]
    metodo, pergunta = next((m, d) for m, d in bot.enviados if d.get("chat_id") == "100")
    assert metodo == "sendPhoto" and pergunta["photo"] == "F1" and "De qual máquina?" in pergunta["caption"]
    item = bot.listar()[0]
    assert item["estado"] == "aguardando"
    opcoes = [b["text"] for linha in pergunta["reply_markup"]["inline_keyboard"] for b in linha]
    assert "Escavadeira PC200" in opcoes and "➕ Nova máquina" in opcoes

    # o Fábio toca na escavadeira: pede o horímetro, ele manda, e o abastecimento é lançado
    indice = bot._item(item["id"])["opcoes"].index("Escavadeira PC200")
    bot._botao("100", f"maq:{item['id']}:{indice}", "cb1", 5)
    assert "qual o horímetro" in _textos(bot.enviados, "100")[-1]
    bot._texto("100", "4.520")
    abastecimento = servico.abastecimentos()[0]
    assert abastecimento["maquina"] == "Escavadeira PC200" and abastecimento["litros"] == 180
    assert abastecimento["medidor"] == 4520 and abastecimento["pessoa"] == "Almir"
    resposta = _textos(bot.enviados, "100")[-1]
    assert "180 L</b> de Diesel S10 em <b>Escavadeira PC200" in resposta and "Saldo do diesel: R$ 4.911,80" in resposta  # R$ 5.990 − 180 L × R$ 5,99
    assert "Média de <b>Escavadeira PC200" in resposta
    assert "Seu canhoto foi lançado: 180 L em Escavadeira PC200" in _textos(bot.enviados, "200")[-1]
    assert bot.listar() == []


def test_canhoto_sem_litros_pergunta_e_placa_marca_a_maquina(bot):
    bot.leituras[b"foto2"] = {"tipo": "canhoto", "litros": None, "placa": "ABC-1D23"}
    bot._nova_foto("100", "Fábio", b"foto2", "canhoto.jpg")
    assert "Quantos litros" in _textos(bot.enviados, "100")[-1]
    bot._texto("100", "210,5")
    pergunta = _textos(bot.enviados, "100")[-1]
    assert "210,5 L" in pergunta
    botoes = [b["text"] for m, d in bot.enviados if d.get("reply_markup") for linha in d["reply_markup"]["inline_keyboard"] for b in linha]
    assert "✔ Caminhão Volvo" in botoes  # achou pela placa: vem marcada e em primeiro


def test_nova_maquina_pelo_telegram_e_saldo_baixo(bot):
    servico.lancar_compra({"data": SEGUNDA, "litros": 200, "valor": 1200}, "Fábio")
    bot.leituras[b"foto3"] = {"tipo": "canhoto", "litros": 120.0}
    bot._nova_foto("100", "Fábio", b"foto3", "canhoto.jpg")
    item = bot.listar()[0]
    bot._botao("100", f"nova:{item['id']}", "cb", 1)
    bot._texto("100", "Pá carregadeira 924")
    assert servico.maquina_por_nome("Pá carregadeira 924")["medidor"] == "horas"
    bot._botao("100", f"pular:{item['id']}", "cb", 2)
    resposta = _textos(bot.enviados, "100")[-1]
    # R$ 1.200 pagos − 120 L × R$ 6,00 = R$ 480, abaixo do aviso padrão de R$ 1.000
    assert "Pá carregadeira 924" in resposta and "Diesel acabando:</b> restam só R$ 480,00" in resposta


def test_compra_pelo_bot_com_botao_de_1000_litros(bot):
    bot.leituras[b"comp"] = {"tipo": "compra", "litros": None, "valor": 5990.0, "posto": "Posto Rodovia"}
    bot._nova_foto("200", "Almir", b"comp", "comprovante.pdf")
    item = bot.listar()[0]
    assert "Quantos litros foram comprados" in _textos(bot.enviados, "200")[-1]
    bot._botao("200", f"lit:{item['id']}:1000", "cb", 3)
    compra = servico.compras()[0]
    assert compra["litros"] == 1000 and compra["valor"] == 5990 and compra["arquivo"] == "arquivos/a1.jpg"
    assert "Compra registrada" in _textos(bot.enviados, "200")[-1]
    assert "Enviado por Almir" in _textos(bot.enviados, "100")[-1]  # o responsável também fica sabendo


def test_arquivo_sem_tipo_pergunta_e_repetido_e_recusado(bot):
    bot.leituras[b"x"] = {"tipo": "", "litros": 90.0}
    bot._nova_foto("200", "Almir", b"x", "foto.jpg")
    assert "O que é?" in _textos(bot.enviados, "200")[-1]
    item = bot.listar()[0]
    bot._botao("200", f"tipo:{item['id']}:canhoto", "cb", 1)
    assert "De qual máquina?" in _textos(bot.enviados, "100")[-1]
    bot._nova_foto("200", "Almir", b"x", "foto.jpg")
    assert "já tinha sido enviado" in _textos(bot.enviados, "200")[-1]


def test_conferencia_na_tela(bot):
    bot.leituras[b"y"] = {"tipo": "canhoto", "litros": 75.0}
    bot._nova_foto("200", "Almir", b"y", "foto.jpg")
    item = bot.listar()[0]
    bot.confirmar(item["id"], {"maquina": "Gerador"}, "Fábio")
    assert servico.abastecimentos()[0]["maquina"] == "Gerador" and bot.contagem() == 0


def test_relatorios_automaticos(bot):
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Gerador", "litros": 60}, "Almir")
    assert bot.relatorios_devidos(datetime(2026, 9, 28, 6, 0)) == []  # antes das 07:00
    assert bot.relatorios_devidos(datetime(2026, 9, 28, 7, 30)) == [("semana", date(2026, 9, 21))]
    assert [t for t, _ in bot.relatorios_devidos(datetime(2026, 10, 1, 8, 0))] == ["quinzena", "mes"]
    assert bot.enviar_relatorios(datetime(2026, 9, 28, 7, 30)) == ["semana"]
    assert "Relatório semanal" in _textos(bot.enviados, "100")[-1] and "Gerador: 60 L" in _textos(bot.enviados, "100")[-1]
    assert bot.enviar_relatorios(datetime(2026, 9, 28, 9, 0)) == []  # não repete


def test_api_do_diesel(bot, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(contexto, "diesel_bot", bot)
    with TestClient(app) as cliente:
        assert cliente.post("/api/diesel/compras", json={"litros": 1000, "valor": 5990, "data": "2026-09-21"}).status_code == 201
        assert cliente.post("/api/diesel/abastecimentos",
                            json={"maquina": "Gerador", "litros": 40, "data": "2026-09-22"}).status_code == 201
        resumo = cliente.get("/api/diesel", params={"periodo": "semana", "data": "2026-09-22"}).json()
        assert resumo["abastecido"]["litros"] == 40 and resumo["saldo"]["valor"] == 5990 - 40 * 5.99
        assert resumo["alerta_valor"] == servico.ALERTA_PADRAO
        maquinas = cliente.get("/api/diesel/maquinas").json()["maquinas"]
        gerador = next(m for m in maquinas if m["nome"] == "Gerador")
        assert cliente.put(f"/api/diesel/maquinas/{gerador['id']}", json={"placa": "GER-01"}).json()["placa"] == "GER-01"
        abastecimento = servico.abastecimentos()[0]
        editado = cliente.put(f"/api/diesel/abastecimentos/{abastecimento['id']}", json={"litros": 45})
        assert editado.status_code == 200 and editado.json()["litros"] == 45
        excel = cliente.get("/api/diesel/relatorio/arquivo", params={"periodo": "quinzena", "data": "2026-09-22"})
        assert excel.status_code == 200 and excel.headers["content-type"].startswith("application/vnd.openxmlformats")
        assert cliente.post("/api/diesel/relatorio/enviar", params={"periodo": "semana"}).json() == {"enviado": 1}


# --------------------------------------------------------------------------- combustíveis, preços e canhoto com várias linhas

# OCR real de um pedido do posto (foto): dois combustíveis e números tortos ("200006", "1.496,000", "7.450")
CANHOTO_DOIS_COMBUSTIVEIS = """Documenta Não Fiscal
POSTO CITY 2
Detalhes do Pedida
Pedido NE 8695073 3 Dats. 29/8972026 16.09 45
Cond. Pagto.:102-30 DIAS
Dados do Cliente
Produtos
Código Descrição Vr Total
Refesencia Qta. Vir. Unit
000004 DIESELCOMUM
200006 6,750 1.350,000
000005 DIESELS10 1.496,000
210,000 7.450
Totais
Qusntidade de Rtens 400.000
Valor Total Bruto.. 2.840.000
Valor Desconto. 0,000
Valor Total Líquido 2.840.000
Placa! Ko
"""


def test_le_as_duas_linhas_do_canhoto_e_acerta_pelo_rodape():
    lido = leitura.analisar_texto(CANHOTO_DOIS_COMBUSTIVEIS, hoje=date(2026, 9, 29))
    assert lido["tipo"] == "canhoto" and lido["posto"] == "POSTO CITY 2" and lido["documento"] == "8695073"
    comum, s10 = lido["itens"]
    assert (comum["combustivel"], comum["litros"], comum["preco_litro"], comum["valor"]) == ("Diesel comum", 200, 6.75, 1350)
    assert (s10["combustivel"], s10["litros"], s10["preco_litro"], s10["valor"]) == ("Diesel S10", 200, 7.45, 1490)
    assert lido["litros"] == 400 and lido["valor"] == 2840


def test_reconhece_o_combustivel():
    assert leitura.combustivel_do_texto("OLEO DIESEL S-10") == "Diesel S10"
    assert leitura.combustivel_do_texto("DIESEL S500 COMUM") == "Diesel comum"
    assert leitura.combustivel_do_texto("ARLA 32 GRANEL") == "Arla 32"
    assert leitura.combustivel_do_texto("GASOLINA ADITIVADA") == "Gasolina"
    assert leitura.combustivel_do_texto("OLEO DIESEL") == ""  # não diz qual: vale o da máquina


def test_preco_da_tabela_e_saldo_por_combustivel(frota):
    from app.diesel import precos

    precos.salvar({"Diesel S10": 7.45, "Diesel comum": 6.75}, "Fábio")
    servico.salvar_maquina({"nome": "Pá carregadeira", "combustivel": "Diesel comum"}, "Fábio")
    servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "combustivel": "Diesel S10"}, "Fábio")
    assert servico.compras()[0]["valor"] == 7450  # sem valor no comprovante: litros × preço da tabela
    a = servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Pá carregadeira", "litros": 100}, "Almir")
    assert a["combustivel"] == "Diesel comum" and a["preco_litro"] == 6.75 and a["valor"] == 675  # o da máquina
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Caminhão Volvo", "litros": 150}, "Almir")
    s = servico.saldo()
    # a compra da semana vale para qualquer diesel: 1.000 − 100 (comum) − 150 (S10)
    assert s["litros"] == 750 and s["ultima_compra"]["usados_desde"] == 250
    assert {c["combustivel"]: c["abastecido"] for c in s["por_combustivel"]} == {"Diesel S10": 150, "Diesel comum": 100}
    # em reais: R$ 7.450 pagos − R$ 675 (comum) − R$ 1.117,50 (S10)
    assert s["valor"] == 5657.5
    assert {e["combustivel"]: e["litros"] for e in s["equivalente"]} == {"Diesel S10": 759.4, "Diesel comum": 838.1}
    assert "Saldo do diesel: R$ 5.657,50" in servico.texto_saldo(s) and "759,4 L de Diesel S10" in servico.texto_saldo(s)
    r = servico.resumo("semana", SEGUNDA)
    assert r["abastecido"]["custo"] == 675 + 150 * 7.45
    assert {c["combustivel"]: c["abastecido"] for c in r["por_combustivel"]} == {"Diesel S10": 150, "Diesel comum": 100}
    editado = servico.atualizar("abastecimentos", a["id"], {"preco_litro": 7.0})
    assert editado["valor"] == 700  # mudou o preço: refaz o total


def test_lancar_canhoto_com_duas_linhas(frota):
    registros = servico.lancar_canhoto(
        [{"combustivel": "Diesel comum", "litros": 200, "preco_litro": 6.75, "valor": 1350, "maquina": "Escavadeira PC200"},
         {"combustivel": "Diesel S10", "litros": 200, "preco_litro": 7.45, "valor": 1490, "maquina": "Caminhão Volvo"}],
        {"data": date(2026, 9, 29), "posto": "Posto City 2", "documento": "0695073"}, "Fábio")
    assert [(r["maquina"], r["combustivel"], r["valor"], r["documento"]) for r in registros] == [
        ("Escavadeira PC200", "Diesel comum", 1350, "0695073"), ("Caminhão Volvo", "Diesel S10", 1490, "0695073")]
    with pytest.raises(servico.ErroDiesel, match="linha 2"):
        servico.lancar_canhoto([{"litros": 10, "maquina": "Gerador"}, {"litros": 20}], {}, "Fábio")


def test_bot_pergunta_a_maquina_de_cada_linha(bot):
    servico.salvar_maquina({"nome": "Pá carregadeira", "combustivel": "Diesel comum"}, "Fábio")
    bot.leituras[b"pedido"] = leitura.analisar_texto(CANHOTO_DOIS_COMBUSTIVEIS, hoje=date(2026, 9, 29))
    bot._nova_foto("200", "Almir", b"pedido", "pedido.jpg", file_id="F9", foto=True)
    pergunta = next(d for m, d in bot.enviados if d.get("chat_id") == "100")
    assert "1) Diesel comum · 200 L × R$ 6,75 = R$ 1.350,00" in pergunta["caption"]
    assert "Linha 1 de 2" in pergunta["caption"] and "Total: 400 L · R$ 2.840,00" in pergunta["caption"]
    item = bot._item(bot.listar()[0]["id"])
    assert item["opcoes"][0] == "Pá carregadeira"  # quem usa Diesel comum vem primeiro

    bot._botao("100", f"maq:{item['id']}:0", "cb", 1)
    bot._botao("100", f"pular:{item['id']}", "cb", 2)  # sem horímetro
    assert "Linha 2 de 2" in _textos(bot.enviados, "100")[-1]
    volvo = item["opcoes"].index("Caminhão Volvo")
    bot._botao("100", f"maq:{item['id']}:{volvo}", "cb", 3)
    bot._texto("100", "152.340")
    lancados = sorted(servico.abastecimentos(), key=lambda a: a["id"])
    assert [(a["maquina"], a["combustivel"], a["litros"], a["valor"]) for a in lancados] == [
        ("Pá carregadeira", "Diesel comum", 200, 1350), ("Caminhão Volvo", "Diesel S10", 200, 1490)]
    assert lancados[1]["medidor"] == 152340 and all(a["documento"] == "8695073" for a in lancados)
    resposta = _textos(bot.enviados, "100")[-1]
    assert "200 L</b> de Diesel comum em <b>Pá carregadeira" in resposta and "Média de <b>Caminhão Volvo" in resposta


def test_api_le_o_arquivo_e_lanca_pela_tela(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr("app.diesel.leitura.texto_do_arquivo", lambda *a, **k: CANHOTO_DOIS_COMBUSTIVEIS)
    with TestClient(app) as cliente:
        lido = cliente.post("/api/diesel/analisar", files={"arquivo": ("pedido.jpg", b"foto", "image/jpeg")}).json()
        assert lido["tipo"] == "canhoto" and len(lido["itens"]) == 2 and lido["arquivo"]["id"]
        corpo = {"data": "2026-09-29", "posto": lido["posto"], "documento": lido["documento"], "arquivo_id": lido["arquivo"]["id"],
                 "itens": [{**i, "maquina": m} for i, m in zip(lido["itens"], ("Gerador", "Caminhão Volvo"))]}
        resposta = cliente.post("/api/diesel/canhoto", json=corpo)
        assert resposta.status_code == 201, resposta.text
        assert [r["maquina"] for r in resposta.json()["abastecimentos"]] == ["Gerador", "Caminhão Volvo"]
        assert all(r["arquivo"] for r in resposta.json()["abastecimentos"])
        precos = cliente.post("/api/diesel/precos", json={"precos": {"Diesel S10": 7.45}}).json()
        assert next(p for p in precos["precos"] if p["combustivel"] == "Diesel S10")["preco"] == 7.45


COMPROVANTE_BRADESCO = """Demais telefones
consulte o site
Fale Conosco
Ouvidoria 0800 727 9933 Atendimento de segunda a sexta-feira, das 8h às 18h, exceto feriados.
Alô Bradesco
SAC - Serviço de
Apoio ao Cliente
Instituição Origem: BANCO BRADESCO S.A.
Debitado da: Conta-corrente
Identificação: E60746948202609282321C19664uyVck
Descrição: 1000 litros de diesel
Valor: R$ 7.000,00
Dados da Transferência
Instituição Destino: COOP SICREDI SUDOESTE MT/PA
Nome: PEREIRA DA SILVA & FERREIRA DA SILVA LTDA EM RECUPERACAO ...
Dados de quem
recebeu
Empresa: PROSPERA SERV COM E REPRESENTACAO LTDA
Data da operação: 28/09/2026 - 20h21
"""


def test_comprovante_do_banco_tira_o_posto_de_quem_recebeu():
    lido = leitura.analisar_texto(COMPROVANTE_BRADESCO, hoje=date(2026, 9, 29))
    assert lido["tipo"] == "compra" and lido["litros"] == 1000 and lido["valor"] == 7000
    assert lido["posto"] == "PEREIRA DA SILVA & FERREIRA DA SILVA LTDA EM RECUPERACAO"  # não "Demais telefones"


def test_saldo_em_reais_com_s10_e_comum_no_mesmo_canhoto(frota):
    """A semana: 1.000 L pagos no preço do S10 (R$ 7.450) e o canhoto do Posto City com 200 L de cada combustível."""
    servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "valor": 7450, "combustivel": "Diesel S10"}, "Fábio")
    servico.lancar_canhoto([{"combustivel": "Diesel comum", "litros": 200, "preco_litro": 6.75, "maquina": "Escavadeira PC200"},
                            {"combustivel": "Diesel S10", "litros": 200, "preco_litro": 7.45, "maquina": "Caminhão Volvo"}],
                           {"data": SEGUNDA, "posto": "POSTO CITY 2"}, "Fábio")
    s = servico.saldo()
    assert (s["pago"], s["gasto"], s["valor"]) == (7450, 2840, 4610)
    assert s["ultima_compra"]["gasto_desde"] == 2840
    r = servico.resumo("semana", SEGUNDA)
    por_nome = {m["maquina"]: m for m in r["por_maquina"]}
    assert por_nome["Escavadeira PC200"]["custo"] == 1350 and por_nome["Caminhão Volvo"]["custo"] == 1490
    assert "R$ 4.610,00" in servico.texto_relatorio("semana", SEGUNDA)

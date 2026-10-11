"""Bot de notas fiscais: recebimento pelo Telegram, baixa automática, conferência, comandos e envio do fechamento."""

import io
from datetime import date

import pytest

from app import contexto
from app.empresas import bot, servico
from app.empresas.entrada import CaixaNotas
from test_empresas_leitura import CHEQUE, CHEQUE_FOTO, COMPROVANTE_PIX, PRINT_FECHAMENTO, XML_NFE


def _pdf(texto: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    folha = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    for linha in texto.splitlines():
        folha.drawString(40, y, linha)
        y -= 18
    folha.save()
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def banco_limpo(tmp_path, monkeypatch):
    from app.banco import BancoBoletos
    from app.empresas.configuracao import ConfigEmpresas
    from app.empresas.modelos import ABAS_EMPRESAS

    banco = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                         abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    monkeypatch.setattr(contexto, "empresas", banco)
    monkeypatch.setattr(contexto, "empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))
    yield banco
    banco.parar()


@pytest.fixture
def caixa(tmp_path):
    arquivos = []

    def salvar(dados, nome):
        arquivos.append(nome)
        return {"id": f"a{len(arquivos)}", "nome": nome, "caminho": f"arquivos/a{len(arquivos)}.pdf"}

    return CaixaNotas(tmp_path / "entrada_notas.json", contexto.empresas_config, salvar, comandos=bot)


@pytest.fixture
def imapal():
    return servico.salvar_empresa({"nome": "Imapal", "cnpj": "12.345.678/0001-95"}, "Fábio")


# --------------------------------------------------------------------------- notas fiscais


def test_nota_em_xml_e_lancada_sozinha_no_fechamento_da_empresa(caixa, imapal):
    item = caixa.receber(XML_NFE.encode("utf-8"), "nfe-6859.xml", remetente="Almir")

    assert item["estado"] == "lancado" and item["empresa"] == "Imapal"
    notas = contexto.empresas.listar("notas")
    assert [(n["numero_nf"], n["material"], n["valor_total"], n["pedido"]) for n in notas] == [
        ("6859", "BRITA 01", 1905.6, "7043"), ("6859", "PEDRISCO", 500.0, "7043")]
    assert notas[0]["arquivo"] == "arquivos/a1.pdf"
    resposta = caixa.mensagem_resposta(item)
    assert "NF 6859 lançada para Imapal" in resposta and "Falta receber" in resposta


def test_a_mesma_nota_nao_entra_duas_vezes(caixa, imapal):
    caixa.receber(XML_NFE.encode("utf-8"), "nfe-6859.xml")
    item = caixa.receber(XML_NFE.encode("utf-8") + b"<!-- reenvio -->", "nfe-6859-copia.xml")
    assert item["estado"] == "ja_lancado" and "já estava lançada" in item["resumo"]
    assert len(contexto.empresas.listar("notas")) == 2  # os dois itens da primeira nota


def test_empresa_nova_e_cadastrada_sozinha_ao_receber_a_nota(caixa):
    item = caixa.receber(XML_NFE.encode("utf-8"), "nfe.xml")
    assert item["estado"] == "lancado"
    empresa = servico.empresas()[0]
    assert empresa["nome"] == "IMAPAL CONSTRUCOES LTDA" and empresa["cnpj"] == "12.345.678/0001-95"


# --------------------------------------------------------------------------- comprovantes e cheques


def test_comprovante_de_pix_da_baixa_e_responde_quanto_falta(caixa, imapal):
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 3), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 5), "material": "Pedrisco", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6869", "pedido": "7053"}],
                         "Fábio")

    item = caixa.receber(_pdf(COMPROVANTE_PIX), "comprovante.pdf", legenda="NF 6859 e 6869")

    assert item["estado"] == "lancado" and item["empresa"] == "Imapal"
    notas = {n["numero_nf"]: n for n in contexto.empresas.listar("notas")}
    assert notas["6859"]["status"] == "Recebido" and notas["6869"]["status"] == "Em aberto"
    resposta = caixa.mensagem_resposta(item)
    assert "R$ 1.905,60" in resposta and "NF 6859" in resposta


def test_cheque_escaneado_fica_guardado_com_os_dados_do_cmc7(caixa, imapal):
    item = caixa.receber(_pdf(CHEQUE), "cheque.pdf", legenda="Cheque da Imapal, pedido 7043")

    assert item["estado"] == "lancado"
    cheque = contexto.empresas.listar("cheques")[0]
    assert cheque["empresa"] == "Imapal" and cheque["valor"] == 1905.60
    assert cheque["banco"] == "Sicredi" and cheque["agencia"] == "0710" and cheque["coop"] == "3003"
    assert cheque["vencimento"] == date(2026, 9, 10) and cheque["status"] == "Em carteira"
    assert "Cheque de Imapal guardado" in caixa.mensagem_resposta(item)


def test_cheque_fotografado_e_reconhecido_pelo_cnpj_e_prende_os_pedidos(caixa, monkeypatch):
    """Foto de cheque como o escritório manda: sem legenda, o sistema descobre tudo sozinho."""
    pazete = servico.salvar_empresa({"nome": "Jose Pazete Ltda (Imapal)", "cnpj": "39.285.595/0001-04"}, "Fábio")
    for pedido, nf in (("7200", "7100"), ("7245", "7101"), ("9999", "7102")):
        servico.lancar_notas("Jose Pazete Ltda (Imapal)",
                             [{"data": date(2026, 9, 10), "material": "Brita 01", "unidade": "M³", "quantidade": 12,
                               "valor_unitario": 158.80, "numero_nf": nf, "pedido": pedido}], "Fábio")

    # o arquivo já chega lido (o OCR de verdade roda no leitor; aqui entra o texto que ele devolve)
    monkeypatch.setattr("app.empresas.leitura.texto_do_arquivo", lambda *a, **k: CHEQUE_FOTO)
    item = caixa.receber(_pdf("foto do cheque"), "Comp. (1).pdf")

    assert item["tipo"] == "cheque" and item["estado"] == "lancado"
    cheque = contexto.empresas.listar("cheques")[0]
    assert cheque["empresa"] == pazete["nome"]  # descoberta pelo CNPJ impresso no cheque
    assert cheque["valor"] == 4287.60 and cheque["vencimento"] == date(2026, 9, 24)
    assert cheque["banco"] == "Sicredi" and cheque["coop"] == "8058" and cheque["numero"] == "616"
    assert "7200" in cheque["pedidos"] and "7310" in cheque["pedidos"]

    presas = {n["pedido"]: n["status"] for n in contexto.empresas.listar("notas")}
    assert presas["7200"] == "Em cheque" and presas["7245"] == "Em cheque"
    assert presas["9999"] == "Em aberto"  # pedido que não está no cheque continua em aberto
    assert "Cheque de Jose Pazete" in caixa.mensagem_resposta(item)


def test_comprovante_de_deposito_compensa_o_cheque_do_mesmo_valor(caixa, imapal):
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 3), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")
    cheque = servico.lancar_cheque({"empresa": "Imapal", "numero": "123", "valor": 1905.60,
                                    "vencimento": date(2026, 9, 10), "pedidos": "7043"}, "Fábio")
    assert contexto.empresas.listar("notas")[0]["status"] == "Em cheque"

    item = caixa.receber(_pdf(COMPROVANTE_PIX.replace("Pix", "Depósito")), "deposito.pdf", legenda="Depósito do cheque da Imapal")

    assert item["estado"] == "lancado" and "compensado" in item["resumo"]
    assert contexto.empresas.obter(cheque["id"], "cheques")["status"] == "Compensado"
    assert contexto.empresas.listar("notas")[0]["status"] == "Recebido"
    assert len(contexto.empresas.listar("recebimentos")) == 1


def test_comprovante_sem_empresa_espera_conferencia(caixa):
    item = caixa.receber(_pdf(COMPROVANTE_PIX), "comprovante.pdf")
    assert item["estado"] == "pendente" and caixa.contagem() == 1
    assert "Confira no Fin Pro" in caixa.mensagem_resposta(item)


def test_print_do_fechamento_fica_para_importar(caixa):
    item = caixa.receber(_pdf(PRINT_FECHAMENTO), "fechamento.pdf")
    assert item["tipo"] == "fechamento" and item["estado"] == "pendente"
    assert len(item["analise"]["linhas"]) == 5


def test_arquivo_desconhecido_vira_erro_com_explicacao(caixa):
    item = caixa.receber(_pdf("Lista de compras\nPão, leite e café"), "lista.pdf")
    assert item["estado"] == "erro" and "não reconheci" in caixa.mensagem_resposta(item).lower()


# --------------------------------------------------------------------------- conferência na tela


def test_conferencia_lanca_o_que_o_robo_nao_teve_certeza(caixa):
    item = caixa.receber(_pdf(COMPROVANTE_PIX), "comprovante.pdf")  # empresa ainda não cadastrada
    assert item["estado"] == "pendente"
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 3), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")

    confirmado = caixa.confirmar(item["id"], "comprovante",
                                 {"empresa": "Imapal", "valor": 1905.60, "data": "2026-08-20", "notas": "6859"}, "Fábio")
    assert confirmado["estado"] == "lancado" and caixa.contagem() == 0
    assert contexto.empresas.listar("notas")[0]["status"] == "Recebido"
    assert contexto.empresas.listar("recebimentos")[0]["arquivo"].startswith("arquivos/")


def test_dinheiro_que_chega_antes_da_nota_vira_credito_e_baixa_sozinho(caixa, imapal):
    item = caixa.receber(_pdf(COMPROVANTE_PIX), "comprovante.pdf")
    assert item["estado"] == "lancado" and "crédito" in caixa.mensagem_resposta(item)
    assert servico.credito_da_empresa("Imapal") == 1905.60

    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 25), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")
    assert contexto.empresas.listar("notas")[0]["status"] == "Recebido"
    assert servico.credito_da_empresa("Imapal") == 0.0


def test_descartar_tira_da_conferencia(caixa):
    item = caixa.receber(_pdf(PRINT_FECHAMENTO), "fechamento.pdf")
    assert caixa.descartar(item["id"]) and caixa.contagem() == 0
    assert caixa.descartar(item["id"]) is False


def test_varias_pessoas_podem_mandar_arquivos_para_o_bot():
    """O bot de notas aceita arquivos de todo mundo que estiver liberado — não só de uma pessoa."""
    cfg = contexto.empresas_config
    cfg.atualizar({"bot": {"token": "123:abc", "ativo": True, "destinatarios": [
        {"chat_id": "7418774049", "nome": "Ryann"},
        {"chat_id": "8740493975", "nome": "Almir"},
        {"chat_id": "-1002222", "nome": "Grupo do escritório"},
        {"chat_id": "555", "nome": "Saiu da empresa", "ativo": False},
    ]}})
    assert [d["nome"] for d in cfg.destinatarios()] == ["Ryann", "Almir", "Grupo do escritório"]

    publica = cfg.publica()["bot"]
    assert publica["token"] == "••••••••" and len(publica["destinatarios"]) == 4

    cfg.lembrar_chat({"id": 999, "first_name": "Bia", "type": "private"})  # falou com o bot, ainda não liberada
    esperando = [c for c in cfg.publica()["bot"]["chats"] if c["chat_id"] not in {d["chat_id"] for d in cfg.destinatarios()}]
    assert [c["nome"] for c in esperando] == ["Bia"]


# --------------------------------------------------------------------------- comandos


def test_comandos_respondem_fechamento_empresas_e_cheques(imapal):
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 3), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")
    servico.lancar_cheque({"empresa": "Imapal", "numero": "123", "valor": 500, "vencimento": date(2026, 9, 25)}, "Fábio")

    assert bot.responder("bom dia") is None
    assert "/fechamento" in bot.responder("/ajuda", "Fábio")[0]

    fechamento = "\n".join(bot.responder("/fechamento imapal", hoje=date(2026, 8, 18)))
    assert "Fechamento Imapal" in fechamento and "R$ 1.905,60" in fechamento and "NF 6859" in fechamento

    empresas = "\n".join(bot.responder("/empresas", hoje=date(2026, 8, 18)))
    assert "Imapal" in empresas and "falta R$ 1.905,60" in empresas

    cheques = "\n".join(bot.responder("/cheques", hoje=date(2026, 8, 18)))
    assert "Cheque 123" in cheques and "R$ 500,00" in cheques

    assert "não encontrei a empresa" in bot.responder("/fechamento outra")[0].lower()


# --------------------------------------------------------------------------- envio do fechamento (dia 20)


def test_envio_automatico_do_fechamento_no_dia_20(caixa, imapal, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.notificacoes.canais.enviar_telegram",
                        lambda token, chat, texto: enviados.append((chat, texto)))
    contexto.empresas_config.atualizar({"bot": {"token": "123:abc", "ativo": True,
                                                "destinatarios": [{"chat_id": "555", "nome": "Fábio"}]}})
    servico.lancar_notas("Imapal", [{"data": date(2026, 8, 3), "material": "Brita 01", "unidade": "M³",
                                     "quantidade": 12, "valor_unitario": 158.80, "numero_nf": "6859", "pedido": "7043"}],
                         "Fábio")

    assert caixa.enviar_fechamentos(date(2026, 8, 18))["enviados"] == 0  # ainda não é dia 20
    resultado = caixa.enviar_fechamentos(date(2026, 8, 20))
    assert resultado["enviados"] == 1 and resultado["competencia"] == "2026-08"
    assert "Fechamento Imapal" in enviados[0][1] and "Falta receber" in enviados[0][1]

    assert caixa.enviar_fechamentos(date(2026, 8, 20))["enviados"] == 0  # não manda duas vezes
    assert caixa.enviar_fechamentos(date(2026, 8, 20), forcar=True)["enviados"] == 1

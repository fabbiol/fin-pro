"""Resumos da semana: segunda (o que vence) e sexta (o que foi pago), agendamento, envio e API."""

from datetime import date, datetime, time

import pytest

from app import contexto, resumo_semanal
from app.banco import BancoBoletos
from app.caixa import servico as caixa
from app.empresas import servico as empresas
from app.empresas.configuracao import ConfigEmpresas
from app.empresas.modelos import ABAS_EMPRESAS
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.notificacoes.servico import ServicoNotificacoes
from app.repositorio import RepositorioBoletos

SEGUNDA = date(2026, 9, 21)
SEXTA = date(2026, 9, 25)


@pytest.fixture(autouse=True)
def bancos(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    planilha.garantir()
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    banco_empresas = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                                  abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    for nome, valor in (("planilha", planilha), ("fila", fila), ("repositorio", RepositorioBoletos(planilha, fila)),
                        ("repositorio_pix", RepositorioBoletos(planilha, fila, "pix")),
                        ("repositorio_caixa", RepositorioBoletos(planilha, fila, "caixa")),
                        ("empresas", banco_empresas), ("empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))):
        monkeypatch.setattr(contexto, nome, valor)
    yield planilha
    planilha.parar()
    banco_empresas.parar()


def _boleto(planilha, nome, venc, valor, status="Pendente", pago=None, centro=""):
    dados = {"beneficiario": nome, "vencimento": venc, "valor": valor, "status": status, "centro_custo": centro}
    if pago:
        dados["data_pagamento"] = pago
    return planilha.adicionar(dados)


def _pix(planilha, nome, venc, valor, status="Pendente", pago=None):
    dados = {"recebedor": nome, "vencimento": venc, "valor": valor, "status": status}
    if pago:
        dados["data_pagamento"] = pago
    return planilha.adicionar(dados, "pix")


def test_resumo_de_segunda_lista_o_que_vence_na_semana(bancos):
    _boleto(bancos, "ENERGISA", date(2026, 9, 23), 2054.95)
    _boleto(bancos, "MAXIMA PARAFUSOS", date(2026, 9, 27), 1940.75)
    _boleto(bancos, "Fora da semana", date(2026, 9, 29), 999)
    _boleto(bancos, "Atrasado LTDA", date(2026, 9, 18), 50)
    _boleto(bancos, "Já pago", date(2026, 9, 22), 70, status="Pago", pago=date(2026, 9, 20))
    _pix(bancos, "Transportes Rodrigues", date(2026, 9, 21), 1978.31)
    empresas.lancar_cheque({"empresa": "Jose Pazete", "numero": "616", "vencimento": date(2026, 9, 24), "valor": 4287.60})
    caixa.lancar({"movimento": "Entrada", "valor": 500, "data": date(2026, 9, 20), "descricao": "Pedido 7043"})

    dados = resumo_semanal.coletar("segunda", SEGUNDA)
    assert [i["nome"] for i in dados["a_pagar"]] == ["Transportes Rodrigues", "ENERGISA", "MAXIMA PARAFUSOS"]
    assert [i["nome"] for i in dados["vencidos"]] == ["Atrasado LTDA"]
    assert dados["empresas"]["cheques"][0]["valor"] == 4287.60
    assert dados["caixa"]["saldo"] == 500

    m = resumo_semanal.mensagem(dados, "http://x")
    assert m.titulo == "Semana: 3 pagamentos · R$ 5.974,01"
    for trecho in ("ENERGISA", "Transportes Rodrigues (Pix)", "qua 23/09", "Atrasado LTDA", "Jose Pazete · nº 616",
                   "R$ 4.287,60", "Saldo em caixa: R$ 500,00"):
        assert trecho in m.texto, trecho
    assert "Fora da semana" not in m.texto and "Já pago" not in m.texto
    assert "<b>" in m.telegram and len(m.itens) == 1


def test_resumo_de_sexta_soma_o_que_foi_pago(bancos):
    _boleto(bancos, "ENERGISA", date(2026, 9, 23), 2054.95, "Pago", date(2026, 9, 23), centro="Energia")
    bancos.atualizar(_boleto(bancos, "MAXIMA", date(2026, 9, 22), 1000, "Pago", date(2026, 9, 22), centro="Manutenção")["id"],
                     {"valor_pago": 1012.50, "juros_multa": 12.50})
    _boleto(bancos, "Pago semana passada", date(2026, 9, 18), 300, "Pago", date(2026, 9, 18))
    _boleto(bancos, "Semana que vem", date(2026, 9, 30), 800)
    _boleto(bancos, "Vence no sábado", date(2026, 9, 26), 120)
    _pix(bancos, "Transportes Rodrigues", date(2026, 9, 21), 1978.31, "Pago", date(2026, 9, 21))
    caixa.lancar({"movimento": "Saída", "valor": 179.70, "data": date(2026, 9, 24), "local": "Posto",
                  "centro_custo": "Combustível"})
    caixa.lancar({"movimento": "Entrada", "valor": 300, "data": date(2026, 9, 24), "descricao": "Pedido 7100"})
    empresas.registrar_recebimento({"empresa": "Imapal", "valor": 1500, "forma": "Pix", "data": date(2026, 9, 23)})

    dados = resumo_semanal.coletar("sexta", SEXTA)
    assert dados["boletos"] == {"quantidade": 2, "total": 3067.45}
    assert dados["pix"] == {"quantidade": 1, "total": 1978.31}
    assert dados["caixa"]["saidas"]["total"] == 179.70
    assert dados["total_saiu"] == round(3067.45 + 1978.31 + 179.70, 2)
    assert dados["total_recebido"] == 1800
    assert dados["centros"][0] == ("Energia", 2054.95)

    m = resumo_semanal.mensagem(dados, "http://x")
    assert dados["juros"]["boletos"] == 12.50 and dados["juros"]["lista"][0]["nome"] == "MAXIMA"
    for trecho in ("Boletos: 2 pagos — R$ 3.067,45 (juros/multa R$ 12,50)", "Juros e multas pagos — R$ 12,50",
                   "MAXIMA — juros/multa R$ 12,50", "Pix: 1 pago — R$ 1.978,31", "Saídas do caixa (dinheiro): 1 lançamento",
                   "Recebido das empresas (Pix): R$ 1.500,00", "Ainda nesta semana (até 27/09): 1 pagamento — R$ 120,00",
                   "Semana que vem (28/09 a 04/10): 1 pagamento — R$ 800,00"):
        assert trecho in m.texto, trecho
    assert "Pago semana passada" not in m.texto
    assert m.titulo == "Semana: pago R$ 5.225,46"


def test_semana_vazia_nao_quebra(bancos):
    assert "Nada vence nesta semana." in resumo_semanal.mensagem(resumo_semanal.coletar("segunda", SEGUNDA), "http://x").texto
    assert "Nenhum juro ou multa pago" in resumo_semanal.mensagem(resumo_semanal.coletar("sexta", SEXTA), "http://x").texto
    assert "Semana fechada" in resumo_semanal.mensagem(resumo_semanal.coletar("sexta", SEXTA), "http://x").texto


# --------------------------------------------------------------------------- agendamento


@pytest.fixture()
def servico(tmp_path, monkeypatch, bancos):
    enviados = []
    monkeypatch.setattr(canais, "enviar_windows", lambda titulo, corpo, url=None, url_pago=None: enviados.append(titulo))
    montar = lambda tipo, hoje: resumo_semanal.mensagem(resumo_semanal.coletar(tipo, hoje), "http://x")  # noqa: E731
    s = ServicoNotificacoes(contexto.repositorio, tmp_path / "notificacoes.json", "http://x", montar_resumo=montar)
    s.atualizar_config({"regras": [], "resumos": {"segunda": {"canais": ["windows"]}, "sexta": {"canais": ["windows"]}}})
    return s, enviados


def _as(dia, hora):
    return datetime.combine(dia, time.fromisoformat(hora))


def test_resumo_sai_uma_vez_no_dia_e_no_horario(servico):
    s, enviados = servico
    assert s.verificar(_as(SEGUNDA, "07:59")) is None
    assert s.verificar(_as(SEGUNDA, "08:00"))["enviado"]
    assert s.verificar(_as(SEGUNDA, "08:01")) is None  # não repete
    assert s.verificar(_as(date(2026, 9, 22), "17:00")) is None  # terça: nada
    assert s.verificar(_as(SEXTA, "16:59")) is None
    assert s.verificar(_as(SEXTA, "18:30"))["enviado"]  # abriu depois do horário: envia assim que abrir
    assert enviados == ["Semana: 0 pagamentos · R$ 0,00", "Semana: pago R$ 0,00"]
    assert s.config_publica()["resumos"]["sexta"]["ultimo_envio"] == SEXTA.isoformat()
    assert [h["tipo"] for h in s.historico()] == ["resumo", "resumo"]


def test_resumo_desligado_ou_sem_canal(servico):
    s, enviados = servico
    s.atualizar_config({"resumos": {"segunda": {"ativo": False}, "sexta": {"canais": []}}})
    assert s.verificar(_as(SEGUNDA, "09:00")) is None
    assert s.verificar(_as(SEXTA, "18:00")) is None
    assert s.enviar_resumo("sexta")["motivo"]
    s.atualizar_config({"resumos": {"sexta": {"canais": ["windows"], "horario": "12:30"}}})
    assert s.config_publica()["resumos"]["sexta"]["horario"] == "12:30"
    assert s.enviar_resumo("sexta")["enviado"] and enviados
    with pytest.raises(ValueError):
        s.atualizar_config({"resumos": {"sexta": {"horario": "25:99"}}})


def test_api_de_previa_e_envio(servico, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    s, enviados = servico
    monkeypatch.setattr(contexto, "notificacoes", s)
    with TestClient(app) as cliente:
        previa = cliente.get("/api/notificacoes/resumo/segunda").json()
        assert previa["titulo"].startswith("Semana:") and "<h2" in previa["html"]
        assert cliente.post("/api/notificacoes/resumo/sexta/enviar").json()["enviado"]
        assert cliente.get("/api/notificacoes/resumo/domingo").status_code == 422
        cfg = cliente.put("/api/notificacoes/config", json={"resumos": {"segunda": {"horario": "07:30"}}}).json()
        assert cfg["resumos"]["segunda"]["horario"] == "07:30"

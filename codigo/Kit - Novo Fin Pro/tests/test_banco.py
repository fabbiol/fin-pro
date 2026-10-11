"""Banco de dados SQLite com a planilha Excel gerada automaticamente (e edições do Excel trazidas de volta)."""

import sqlite3
from datetime import date

import pytest

from app.banco import USUARIO_EXCEL, BancoBoletos
from app.planilha import PlanilhaBloqueadaError, PlanilhaBoletos, RegistroNaoEncontrado


@pytest.fixture
def planilha_antiga(tmp_path):
    p = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    p.adicionar({"beneficiario": "Energisa", "valor": 487.32, "vencimento": date(2026, 9, 25), "centro_custo": "Energia"}, usuario="Ana")
    p.adicionar({"beneficiario": "Papelaria", "valor": 100, "status": "Pago", "data_pagamento": date(2026, 9, 1)}, usuario="Ana")
    p.adicionar({"recebedor": "João Frete", "tipo_chave": "email", "chave": "joao@frete.com", "valor": 250.5}, "pix", "Bia")
    p.atualizar(1, {"observacoes": "conta de setembro"}, usuario="Ana")
    return p


def test_primeira_abertura_importa_a_planilha_existente(tmp_path, planilha_antiga):
    banco = BancoBoletos(tmp_path / "boletos.db", planilha_antiga.caminho, tmp_path / "backups")
    assert banco.vazio and banco.migrar() and not banco.vazio
    for aba in ("boletos", "pix"):
        assert banco.listar(aba) == planilha_antiga.listar(aba)
    assert banco.obter(1)["observacoes"] == "conta de setembro" and banco.obter(2)["pago_por"] == "Ana"
    eventos = banco.historico_do_registro(1, "boletos")
    assert [(e["acao"], e["usuario"]) for e in eventos] == [("Edição", "Ana"), ("Lançamento", "Ana")]
    assert banco.historico_do_registro(1, "pix")[0]["acao"] == "Lançamento"
    assert "Energia" in {c["nome"] for c in banco.listar_centros()}
    assert banco.migrar() is False  # não importa duas vezes


def test_grava_no_banco_e_gera_a_planilha(tmp_path, planilha_antiga):
    banco = BancoBoletos(tmp_path / "boletos.db", planilha_antiga.caminho, tmp_path / "backups")
    banco.migrar()
    novo = banco.adicionar({"beneficiario": "Aluguel", "valor": 2000, "vencimento": date(2026, 10, 5), "centro_custo": "Sede"}, usuario="Fábio")
    assert novo["id"] == 3 and novo["lancado_por"] == "Fábio"
    pago = banco.atualizar(3, {"status": "Pago", "data_pagamento": date(2026, 10, 4), "valor_pago": 2000.0}, usuario="Almir")
    assert pago["pago_por"] == "Almir" and banco.exportacao["pendente"]
    banco.excluir(2, usuario="Fábio")
    with pytest.raises(RegistroNaoEncontrado):
        banco.obter(2)
    assert banco.adicionar({"beneficiario": "Depois da exclusão", "valor": 1})["id"] == 4
    assert "Sede" in {c["nome"] for c in banco.listar_centros()}

    assert banco.exportar() and not banco.exportacao["pendente"]
    lida = PlanilhaBoletos(planilha_antiga.caminho)
    assert [(r["id"], r["beneficiario"], r["status"], r["valor_pago"]) for r in lida.listar()] == [
        (1, "Energisa", "Pendente", None), (3, "Aluguel", "Pago", 2000.0), (4, "Depois da exclusão", "Pendente", None)]
    assert lida.listar("pix")[0]["recebedor"] == "João Frete"
    assert [e["acao"] for e in lida.historico_do_registro(3, "boletos")] == ["Pagamento", "Lançamento"]

    banco.salvar_centro("Sede Nova", nome_anterior="Sede", usuario="Fábio")
    assert banco.obter(3)["centro_custo"] == "Sede Nova"

    copia = tmp_path / "copia.db"
    banco.copiar_banco(copia)
    assert sqlite3.connect(copia).execute("SELECT COUNT(*) FROM registros").fetchone()[0] == 4


def test_planilha_aberta_no_excel_nao_trava_lancamentos(tmp_path, planilha_antiga, monkeypatch):
    banco = BancoBoletos(tmp_path / "boletos.db", planilha_antiga.caminho)
    banco.migrar()

    def aberta():
        raise PlanilhaBloqueadaError("aberta no Excel")

    monkeypatch.setattr(banco.excel, "_verificar_gravavel", aberta)
    registro = banco.adicionar({"beneficiario": "Com Excel aberto", "valor": 5})
    assert registro["id"] == 3  # gravado na hora, com ID definitivo
    assert banco.exportar() is False and banco.exportacao["excel_aberto"] and banco.exportacao["pendente"]
    monkeypatch.undo()
    assert banco.exportar() and not banco.exportacao["excel_aberto"]
    assert any(r["beneficiario"] == "Com Excel aberto" for r in PlanilhaBoletos(planilha_antiga.caminho).listar())


def test_edicao_no_excel_volta_para_o_sistema_sem_desfazer_o_que_o_sistema_gravou(tmp_path, planilha_antiga):
    banco = BancoBoletos(tmp_path / "boletos.db", planilha_antiga.caminho)
    banco.migrar()
    banco.exportar()

    # Enquanto a planilha estava aberta, o bot registrou o pagamento do boleto 1 no sistema...
    banco.atualizar(1, {"status": "Pago", "data_pagamento": date(2026, 9, 20)}, usuario="Almir (Telegram)")
    # ...e alguém mudou no Excel o centro de custo do boleto 1 e a observação do Pix 1, e salvou
    excel = PlanilhaBoletos(planilha_antiga.caminho)
    excel.atualizar(1, {"centro_custo": "Administrativo"})
    excel.atualizar(1, {"observacoes": "pago em dinheiro"}, "pix")

    assert banco.importar_edicoes_do_excel() == 2
    boleto = banco.obter(1)
    assert (boleto["centro_custo"], boleto["status"], boleto["pago_por"]) == ("Administrativo", "Pago", "Almir (Telegram)")
    assert banco.obter(1, "pix")["observacoes"] == "pago em dinheiro"
    assert banco.historico_do_registro(1, "boletos")[0]["usuario"] == USUARIO_EXCEL
    assert banco.importar_edicoes_do_excel() == 0  # o mesmo arquivo não é importado de novo

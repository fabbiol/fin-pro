"""Versão de demonstração: dados de exemplo completos e nenhum envio para fora."""

from datetime import date

import pytest

from app import contexto, demonstracao
from app.banco import BancoBoletos
from app.empresas.configuracao import ConfigEmpresas
from app.diesel.modelos import ABAS_DIESEL
from app.empresas.modelos import ABAS_EMPRESAS
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.notificacoes.servico import ServicoNotificacoes
from app.repositorio import FonteLembretes, RepositorioBoletos
from app.usuarios import GerenciadorUsuarios

HOJE = date(2026, 9, 22)


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    empresas = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                            abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    diesel = BancoBoletos(tmp_path / "diesel.db", tmp_path / "diesel.xlsx", tmp_path / "backups",
                          abas=ABAS_DIESEL, centros=False, nome_backup="diesel")
    boletos, pix = RepositorioBoletos(planilha, fila), RepositorioBoletos(planilha, fila, "pix")
    monkeypatch.setattr(contexto.config, "DADOS_DIR", tmp_path)
    for nome, valor in (("planilha", planilha), ("fila", fila), ("repositorio", boletos), ("repositorio_pix", pix),
                        ("repositorio_caixa", RepositorioBoletos(planilha, fila, "caixa")), ("empresas", empresas),
                        ("diesel", diesel),
                        ("empresas_config", ConfigEmpresas(tmp_path / "empresas.json")),
                        ("usuarios", GerenciadorUsuarios(tmp_path / "usuarios.json")),
                        ("notificacoes", ServicoNotificacoes(FonteLembretes(boletos, pix),
                                                             tmp_path / "notificacoes.json", "http://x"))):
        monkeypatch.setattr(contexto, nome, valor)
    yield tmp_path
    planilha.parar()
    empresas.parar()
    diesel.parar()


def test_dados_de_exemplo_cobrem_todas_as_telas(ambiente):
    resumo = demonstracao.montar_dados(HOJE)
    assert all(resumo[chave] > 0 for chave in ("boletos", "pix", "caixa", "notas", "cheques", "recebimentos", "empresas",
                                               "abastecimentos"))
    from app.diesel import servico as diesel

    semana = diesel.resumo("mes", HOJE)
    assert semana["comprado"]["litros"] >= 1000 and semana["por_maquina"] and diesel.saldo()["comprado"] == 9 * 1050 and len(diesel.saldo()["por_combustivel"]) == 2
    assert diesel.saldo()["litros"] == round(diesel.saldo()["comprado"] - diesel.saldo()["abastecido"], 2)
    assert any(m["consumo"]["rotulo"] for m in semana["por_maquina"])  # com horímetro/km, o consumo aparece

    lancamentos = contexto.repositorio.listar()
    situacoes = {r["status"] for r in lancamentos}
    assert {"Pago", "Pendente"} <= situacoes
    assert any(r["status"] == "Pendente" and r["vencimento"] < HOJE for r in lancamentos)  # atrasados para os lembretes
    assert any(float(r.get("juros_multa") or 0) > 0 for r in lancamentos)  # juros pagos aparecem no resumo de sexta
    assert all(r.get("centro_custo") for r in lancamentos)
    assert contexto.repositorio_caixa.listar() and contexto.empresas.listar("notas")

    # o fechamento em aberto de cada empresa tem lançamentos para mostrar
    from app.empresas import servico as empresas

    for empresa in empresas.empresas():
        assert empresas.fechamento(empresa["nome"], hoje=HOJE)["totais"]["quantidade"] > 0


def test_usuarios_e_bots_ja_vem_configurados(ambiente):
    demonstracao.configurar(HOJE)
    logins = {u["login"] for u in contexto.usuarios.listar()}
    assert {"demo", "almir", "juliana"} == logins
    assert not contexto.usuarios.pedir_login_ao_abrir  # a demonstração abre direto
    config = contexto.notificacoes.config_publica()
    assert config["telegram"]["ativo"] and len(config["telegram"]["destinatarios"]) == 3
    assert config["resumos"]["segunda"]["ativo"] and config["resumos"]["sexta"]["horario"] == "17:00"
    assert contexto.empresas_config.publica()["bot"]["ativo"]
    assert (ambiente / "caixa_bot.json").exists() and (ambiente / "diesel_bot.json").exists()


def test_na_demonstracao_nada_e_enviado_para_fora(monkeypatch):
    monkeypatch.setattr(canais.config, "DEMONSTRACAO", True)
    with pytest.raises(canais.ErroCanal, match="demonstração"):
        canais.enviar_telegram("token", "1", "oi")
    with pytest.raises(canais.ErroCanal, match="demonstração"):
        canais.enviar_email({"servidor": "smtp.x", "porta": 587}, "assunto", "texto", "<p>html</p>")

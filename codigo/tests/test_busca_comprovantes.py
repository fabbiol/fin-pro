"""Central de comprovantes: busca em todas as partes, filtros, permissões e ZIP."""

import io
import zipfile
from datetime import date

import pytest

from app import busca_comprovantes as busca
from app import contexto
from app.arquivos import RepositorioArquivos
from app.banco import BancoBoletos
from app.caixa import servico as caixa
from app.empresas import servico as empresas
from app.empresas.configuracao import ConfigEmpresas
from app.empresas.modelos import ABAS_EMPRESAS
from app.fila_gravacao import FilaGravacao
from app.repositorio import RepositorioBoletos


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    planilha.garantir()
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    banco_empresas = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                                  abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    arquivos = RepositorioArquivos(tmp_path / "arquivos")
    for nome, valor in (("planilha", planilha), ("fila", fila), ("repositorio", RepositorioBoletos(planilha, fila)),
                        ("repositorio_pix", RepositorioBoletos(planilha, fila, "pix")),
                        ("repositorio_caixa", RepositorioBoletos(planilha, fila, "caixa")),
                        ("empresas", banco_empresas), ("empresas_config", ConfigEmpresas(tmp_path / "empresas.json")),
                        ("arquivos", arquivos)):
        monkeypatch.setattr(contexto, nome, valor)
    yield arquivos
    planilha.parar()
    banco_empresas.parar()


def _arquivo(arquivos, nome):
    meta = arquivos.salvar(b"%PDF-1.4 comprovante " + nome.encode(), nome)
    return {"caminho": arquivos.caminho_relativo(meta["id"]), "nome": nome}


@pytest.fixture
def dados(ambiente):
    arq = ambiente
    comp = _arquivo(arq, "comprovante-importcate.pdf")
    contexto.planilha.adicionar({"beneficiario": "IMPORCATE COM DE PECAS", "valor": 900, "vencimento": date(2026, 7, 20),
                                 "status": "Pago", "data_pagamento": date(2026, 9, 21), "valor_pago": 956.70,
                                 "juros_multa": 56.70, "numero_documento": "2.715.287", "centro_custo": "Manutenção",
                                 "comprovante": comp["caminho"], "comprovante_nome": comp["nome"]}, usuario="Almir")
    contexto.planilha.adicionar({"beneficiario": "BERTASSO E CIA", "valor": 210, "vencimento": date(2026, 9, 16),
                                 "status": "Pago", "data_pagamento": date(2026, 9, 16)})  # pago sem comprovante
    contexto.planilha.adicionar({"beneficiario": "ENERGISA", "valor": 500, "vencimento": date(2026, 10, 1)})  # pendente
    pix = _arquivo(arq, "pix-magno.pdf")
    contexto.planilha.adicionar({"recebedor": "Magno Alves", "valor": 1600, "vencimento": date(2026, 9, 16),
                                 "status": "Pago", "data_pagamento": date(2026, 9, 16), "comprovante": pix["caminho"],
                                 "comprovante_nome": pix["nome"]}, "pix")
    empresas.lancar_cheque({"empresa": "Jose Pazete", "numero": "616", "vencimento": date(2026, 9, 24), "valor": 4287.60,
                            "pedidos": "7200, 7201", "banco": "Sicredi"}, "Fábio", arquivo=_arquivo(arq, "cheque.pdf"))
    empresas.registrar_recebimento({"empresa": "Imapal", "valor": 1500, "forma": "Pix", "data": date(2026, 9, 23),
                                    "id_transacao": "E123456789"}, "Fábio", arquivo=_arquivo(arq, "recebido.pdf"))
    empresas.lancar_notas("Imapal", [
        {"data": date(2026, 9, 10), "material": "Brita 01", "unidade": "M³", "quantidade": 10, "valor_unitario": 100,
         "numero_nf": "7120", "pedido": "7043"},
        {"data": date(2026, 9, 10), "material": "Pedrisco", "unidade": "M³", "quantidade": 5, "valor_unitario": 80,
         "numero_nf": "7120", "pedido": "7044"}], "Fábio", arquivo=_arquivo(arq, "NF-7120.pdf"))
    caixa.lancar({"movimento": "Saída", "valor": 179.70, "data": date(2026, 9, 22), "local": "Posto São Jorge",
                  "centro_custo": "Combustível"}, "Fábio", arquivo=_arquivo(arq, "cupom.pdf"))


def test_junta_comprovantes_de_todas_as_partes(dados):
    itens = busca.buscar()
    assert {i["tipo"] for i in itens} == {"boleto", "pix", "cheque", "recebimento", "nota", "caixa"}
    assert all(i["comprovante_id"] for i in itens)  # padrão: só o que tem comprovante
    nota = next(i for i in itens if i["tipo"] == "nota")
    assert nota["valor"] == 1400 and nota["numero"] == "7120" and "7043" in nota["detalhe"]  # duas linhas = uma nota
    assert itens[0]["data"] >= itens[-1]["data"]  # mais recentes primeiro


def test_filtros_por_nome_valor_data_e_numero(dados):
    assert [i["nome"] for i in busca.buscar(q="imporcate")] == ["IMPORCATE COM DE PECAS"]
    assert [i["tipo"] for i in busca.buscar(valor="956,70")] == ["boleto"]  # valor pago (com juros) também encontra
    assert [i["tipo"] for i in busca.buscar(valor="900")] == ["boleto"]
    assert [i["numero"] for i in busca.buscar(numero="616")] == ["616"]  # número do cheque
    assert [i["tipo"] for i in busca.buscar(numero="7201")] == ["cheque"]  # pedido no verso do cheque
    assert [i["tipo"] for i in busca.buscar(numero="E123456789")] == ["recebimento"]
    assert [i["tipo"] for i in busca.buscar(numero="2715287")] == ["boleto"]  # sem pontos também acha
    setembro = busca.buscar(de=date(2026, 9, 20), ate=date(2026, 9, 30))
    assert {i["tipo"] for i in setembro} == {"boleto", "cheque", "recebimento", "caixa"}
    assert [i["tipo"] for i in busca.buscar(tipos=["cheque", "pix"], ordenar="valor")] == ["cheque", "pix"]
    assert [i["nome"] for i in busca.buscar(centro="manutenção")] == ["IMPORCATE COM DE PECAS"]
    assert [i["nome"] for i in busca.buscar(pessoa="almir")] == ["IMPORCATE COM DE PECAS"]
    assert {i["tipo"] for i in busca.buscar(valor_min=1500)} == {"pix", "cheque", "recebimento"}


def test_pagos_sem_comprovante(dados):
    caixa.lancar({"movimento": "Entrada", "valor": 800, "data": date(2026, 9, 22), "descricao": "Pedido 7050"}, "Fábio")
    caixa.lancar({"movimento": "Saída", "valor": 45, "data": date(2026, 9, 22), "local": "Mercado"}, "Fábio")
    sem = busca.buscar(comprovante="sem")
    # o pendente (ENERGISA) e a entrada do caixa (venda à vista não tem cupom) não entram
    assert sorted(i["nome"] for i in sem) == ["BERTASSO E CIA", "Mercado"]


def test_numero_curto_nao_procura_dentro_da_linha_digitavel(dados):
    contexto.planilha.adicionar({"beneficiario": "OUTRO", "valor": 10, "status": "Pago", "data_pagamento": date(2026, 9, 1),
                                 "linha_digitavel": "00190.00009 02565.728009 00266.840172 1 15990000033699",
                                 "comprovante": busca.buscar(tipos=["pix"])[0]["comprovante_id"]})
    assert [i["tipo"] for i in busca.buscar(numero="616")] == ["cheque"]
    assert [i["nome"] for i in busca.buscar(numero="02565728009")] == ["OUTRO"]  # trecho grande da linha acha


def test_permissoes_escondem_empresas_e_caixa(dados):
    tipos = {i["tipo"] for i in busca.buscar(lambda p: False)}
    assert tipos == {"boleto", "pix"}
    assert busca.buscar(lambda p: False, tipos=["cheque"]) == []


def test_zip_com_os_comprovantes_filtrados(dados):
    conteudo, quantidade = busca.gerar_zip(busca.buscar(tipos=["boleto", "cheque"]))
    assert quantidade == 2
    nomes = zipfile.ZipFile(io.BytesIO(conteudo)).namelist()
    assert "Boleto/2026-09-21 - Boleto - IMPORCATE COM DE PECAS - n2.715.287 - R$ 956,70.pdf" in nomes
    assert any(n.startswith("Cheque/") and "n616" in n for n in nomes)


def test_api_busca_e_zip(dados):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        resposta = cliente.get("/api/comprovantes/busca", params={"tipos": "boleto,pix", "q": "magno"}).json()
        assert resposta["total"] == 1 and resposta["itens"][0]["comprovante_pdf"] is True
        assert {t["tipo"] for t in resposta["tipos"]} == set(busca.TIPOS)
        assert cliente.get("/api/comprovantes/busca", params={"tipos": "xyz"}).status_code == 422
        zipado = cliente.get("/api/comprovantes/busca/zip", params={"tipos": "cheque"})
        assert zipado.status_code == 200 and zipado.headers["content-type"] == "application/zip"
        assert cliente.get("/api/comprovantes/busca/zip", params={"q": "nada-disso"}).status_code == 404

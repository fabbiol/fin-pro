"""Comprovantes de pagamento: reconhecer, achar o boleto/Pix, registrar pago com juros e desconto (tela, anexo e bot)."""

import io
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import comprovante, contexto, entrada, main
from app.arquivos import RepositorioArquivos
from app.boleto.codigo import formatar_linha
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

ITAU = """Banco Itaú - Comprovante de pagamento de boleto
Nome do pagador: ESCRITORIO MODELO LTDA
Beneficiário:
CLA AUTO PECAS MIRASSOL LTDA
CPF/CNPJ do beneficiário: 12.345.678/0001-95
Código de barras: {linha}
Data de vencimento: {vencimento}
Valor do documento: R$ 270,35
(-) Desconto/abatimento: R$ 0,00
(+) Juros/Multa: R$ 5,40
(=) Valor pago: R$ 275,75
Data de pagamento: {pagamento}
Autenticação: 3F2A.99B1.0C44"""

PIX = """Comprovante de transferência
Pix enviado
{pagamento} - 07:42:10
Valor
R$ 1.250,00
Destino
Nome
Magno Alves Vaillant
Chave Pix
magno@email.com
ID da transação: E18236120202609171042s0123456789"""


def _registro(id_, **dados):
    base = {"id": id_, "status": "Pendente", "valor": 270.35, "beneficiario": "CLA AUTO PECAS MIRASSOL LTDA",
            "documento_beneficiario": "12.345.678/0001-95", "vencimento": date(2026, 10, 10), "codigo_barras": ""}
    return {**base, **dados}


def test_reconhece_comprovantes_e_nao_confunde_com_boleto():
    assert comprovante.eh_comprovante(ITAU.format(linha="", vencimento="10/10/2026", pagamento="15/10/2026"))
    assert comprovante.eh_comprovante(PIX.format(pagamento="17/09/2026"))
    assert not comprovante.eh_comprovante("Local de pagamento: pagável em qualquer banco até o vencimento\n"
                                          "Nosso número 123\nRecibo do pagador\nValor do documento 100,00\nPagador: Fulano")
    e = comprovante.extrair(ITAU.format(linha="", vencimento="10/10/2026", pagamento="15/10/2026"), hoje=date(2026, 10, 20))
    assert (e["valor_pago"], e["valor_documento"], e["juros_multa"], e["desconto"]) == (275.75, 270.35, 5.4, 0.0)
    assert (e["data_pagamento"], e["vencimento"]) == (date(2026, 10, 15), date(2026, 10, 10))
    assert e["beneficiario"] == "CLA AUTO PECAS MIRASSOL LTDA" and e["documentos"] == ["12345678000195"]
    p = comprovante.extrair(PIX.format(pagamento="17/09/2026"), hoje=date(2026, 9, 20))
    assert (p["tipo"], p["valor_pago"], p["beneficiario"], p["chave_pix"]) == ("pix", 1250.0, "Magno Alves Vaillant", "magno@email.com")
    assert comprovante.extrair("Comprovante de agendamento\nPagamento agendado para 20/10/2026\nValor: R$ 10,00")["agendado"]


def test_escolhe_o_lancamento_so_quando_tem_certeza():
    texto = ITAU.format(linha="", vencimento="10/11/2026", pagamento="12/11/2026")
    parcelas = [_registro(1, vencimento=date(2026, 10, 10)), _registro(2, vencimento=date(2026, 11, 10), valor=270.35),
                _registro(3, vencimento=date(2026, 12, 10))]
    extraido = comprovante.extrair(texto, hoje=date(2026, 11, 20))
    lista = comprovante.candidatos(extraido, parcelas, [])
    assert lista[0]["id"] == 2 and comprovante.escolher(lista)["id"] == 2  # o vencimento impresso desempata as parcelas

    sem_vencimento = comprovante.extrair(texto.replace("Data de vencimento: 10/11/2026\n", ""), hoje=date(2026, 11, 20))
    lista = comprovante.candidatos(sem_vencimento, [_registro(1, vencimento=date(2026, 11, 5)),
                                                    _registro(2, vencimento=date(2026, 11, 10))], [])
    assert comprovante.escolher(lista) is None  # duas parcelas iguais e próximas: pergunta

    com_codigo = comprovante.extrair(texto, ["1" * 44], hoje=date(2026, 11, 20))
    lista = comprovante.candidatos(com_codigo, [_registro(1, codigo_barras="1" * 44, vencimento=date(2026, 12, 10)),
                                               _registro(2, vencimento=date(2026, 11, 10))], [])
    assert comprovante.escolher(lista)["id"] == 1  # linha digitável igual resolve

    pix = comprovante.extrair(PIX.format(pagamento="17/09/2026"), hoje=date(2026, 9, 20))
    lista = comprovante.candidatos(pix, parcelas, [{"id": 7, "status": "Pendente", "valor": 1250.0, "recebedor": "Magno Alves Vaillant",
                                                    "tipo_chave": "email", "chave": "magno@email.com", "vencimento": date(2026, 9, 17)}])
    assert comprovante.escolher(lista) == lista[0] and (lista[0]["aba"], lista[0]["id"]) == ("pix", 7)


def test_juros_e_desconto_pelo_valor_pago():
    registro = {"valor": 270.35}
    assert comprovante.dados_de_pagamento({"valor_pago": 275.75, "data_pagamento": "2026-10-15"}, registro) == {
        "status": "Pago", "data_pagamento": date(2026, 10, 15), "valor_pago": 275.75, "juros_multa": 5.4, "desconto": 0.0}
    com_desconto = comprovante.dados_de_pagamento({"valor_pago": 260.0}, registro)
    assert (com_desconto["juros_multa"], com_desconto["desconto"]) == (0.0, 10.35)
    assert comprovante.dados_de_pagamento({}, registro)["valor_pago"] == 270.35


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


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    arquivos = RepositorioArquivos(tmp_path / "arquivos")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", arquivos)
    with TestClient(main.app) as cliente:
        yield cliente, planilha


def _lancar(cliente, linha):
    from conftest import VALOR, VENCIMENTO

    resposta = cliente.post("/api/boletos", json={"linha_digitavel": linha, "beneficiario": "Empresa Exemplo de Serviços Ltda",
                                                  "documento_beneficiario": "12.345.678/0001-95", "valor": float(VALOR),
                                                  "vencimento": VENCIMENTO.isoformat()})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_comprovante_enviado_na_tela_registra_o_pagamento(sistema, boleto_pdf):
    cliente, _ = sistema
    from conftest import VALOR, VENCIMENTO

    _, linha = boleto_pdf
    boleto = _lancar(cliente, linha)
    pagamento = VENCIMENTO + timedelta(days=3)
    texto = (ITAU.replace("CLA AUTO PECAS MIRASSOL LTDA", "EMPRESA EXEMPLO DE SERVICOS LTDA")
             .replace("R$ 270,35", f"R$ {VALOR:.2f}".replace(".", ","))
             .replace("R$ 275,75", f"R$ {VALOR + 12:.2f}".replace(".", ","))
             .replace("R$ 5,40", "R$ 12,00")
             .format(linha=formatar_linha(linha), vencimento=f"{VENCIMENTO:%d/%m/%Y}", pagamento=f"{pagamento:%d/%m/%Y}"))
    lido = cliente.post("/api/leituras", files={"arquivo": ("comprovante.pdf", _pdf(texto), "application/pdf")}).json()
    analise = lido["comprovante"]
    assert not lido["boletos"] and analise["sugerido"]["id"] == boleto["id"]
    assert "linha digitável igual" in analise["sugerido"]["motivos"]

    registrado = cliente.post("/api/comprovantes/registrar", json={
        "aba": "boletos", "id": boleto["id"], "arquivo_id": lido["arquivo"]["id"], "extraido": analise["extraido"]}).json()
    r = registrado["registro"]
    assert (r["status"], r["data_pagamento"], r["valor_pago"], r["juros_multa"]) == ("Pago", pagamento.isoformat(), float(VALOR) + 12, 12.0)
    assert r["comprovante_nome"] == "comprovante.pdf" and registrado["pagamento"]["dias_atraso"] == 3
    assert cliente.get(f"/api/boletos/{boleto['id']}/historico").json()["eventos"][0]["acao"] == "Pagamento"

    fechamento = cliente.get("/api/relatorios/fechamento", params={"mes": f"{VENCIMENTO:%Y-%m}"}).json()["totais"]
    assert (fechamento["pago"], fechamento["juros_multa"], fechamento["pagos_com_atraso"]) == (float(VALOR) + 12, 12.0, 1)

    desfeito = cliente.post(f"/api/boletos/{boleto['id']}/desfazer-pagamento").json()
    assert desfeito["status"] == "Pendente" and not desfeito["valor_pago"] and not desfeito["comprovante"]


def test_anexar_comprovante_marca_como_pago_com_os_valores(sistema, boleto_pdf):
    cliente, _ = sistema
    from conftest import VALOR

    _, linha = boleto_pdf
    boleto = _lancar(cliente, linha)
    texto = f"Comprovante de pagamento\nValor do documento: R$ {VALOR:.2f}\n(-) Desconto: R$ 5,00\n(=) Valor pago: R$ {VALOR - 5:.2f}\nData do pagamento: 01/09/2026\nAutenticação: XYZ"
    texto = texto.replace(f"{VALOR:.2f}", f"{VALOR:.2f}".replace(".", ",")).replace(f"{VALOR - 5:.2f}", f"{VALOR - 5:.2f}".replace(".", ","))
    r = cliente.post(f"/api/boletos/{boleto['id']}/comprovante", files={"arquivo": ("pix.pdf", _pdf(texto), "application/pdf")}).json()
    assert (r["status"], r["data_pagamento"], r["valor_pago"], r["desconto"]) == ("Pago", "2026-09-01", float(VALOR) - 5, 5.0)


def test_caixa_de_entrada_registra_comprovante_e_responde(tmp_path):
    registrados = []

    def processar(dados, nome):
        texto = dados.decode()
        if "Comprovante" in texto:
            extraido = comprovante.publico(comprovante.extrair(texto, hoje=date(2026, 11, 20)))
            candidatos = [{"aba": "boletos", "id": 2, "nome": "CLA", "pontos": 100}] if "certo" in nome else \
                         [{"aba": "boletos", "id": 2, "pontos": 60}, {"aba": "boletos", "id": 3, "pontos": 58}]
            return {"boletos": [], "pix": [], "arquivo": {"id": "a" * 32},
                    "comprovante": {"extraido": extraido, "candidatos": candidatos, "sugerido": comprovante.escolher(candidatos)}}
        return {"boletos": [{"duplicado": {"id": 80}}, {"duplicado": {"id": 81}}], "pix": [], "arquivo": {"id": "b" * 32}}

    def registrar(aba, id_, extraido, usuario, arquivo_id):
        registrados.append((aba, id_, usuario, arquivo_id))
        return {"aba": aba, "id": id_, "nome": "CLA AUTO PECAS", "valor": 270.35, "valor_pago": 275.75, "juros_multa": 5.4,
                "desconto": 0, "vencimento": "2026-11-10", "data_pagamento": "2026-11-12", "dias_atraso": 2}

    caixa = entrada.CaixaEntrada(tmp_path / "entrada.json", processar, lambda d, n: {"id": "c" * 32}, lambda: ("", []), registrar)
    texto = ITAU.format(linha="", vencimento="10/11/2026", pagamento="12/11/2026").encode()
    pago = caixa.receber(texto, "comprovante-certo.pdf", "telegram", "Almir", usuario="Almir Ribeiro (Telegram)")
    assert pago["estado"] == "pago" and registrados == [("boletos", 2, "Almir Ribeiro (Telegram)", "a" * 32)]
    mensagem = caixa._mensagem_resposta(pago)
    assert "Pagamento registrado: CLA AUTO PECAS" in mensagem and "Juros/multa: R$ 5,40 (2 dia(s) de atraso)" in mensagem
    assert caixa.contagem() == 0

    duvida = caixa.receber(texto + b" ", "comprovante.pdf", "telegram", "Almir")
    assert duvida["estado"] == "pendente" and "mais de um boleto parecido" in caixa._mensagem_resposta(duvida)
    listado = caixa.listar()[0]
    assert listado["tipo"] == "comprovante" and len(listado["candidatos"]) == 2 and listado["extraido"]["valor_pago"] == 275.75
    assert caixa.associar(duvida["id"], "boletos", 3, "Fábio")["estado"] == "pago"
    with pytest.raises(ValueError):
        caixa.associar(duvida["id"], "boletos", 3, "Fábio")

    ja = caixa.receber(b"boletos repetidos", "boletos.pdf", "email", "Fornecedor")
    assert ja["estado"] == "ja_lancado" and "já estava lançado" in caixa._mensagem_resposta(ja) and caixa.contagem() == 0

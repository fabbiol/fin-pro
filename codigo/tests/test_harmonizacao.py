"""Nome do beneficiário pelo CPF/CNPJ: histórico da planilha e consenso dentro do arquivo."""

from app.banco import BancoBoletos
from app.boleto.extrator import harmonizar_beneficiarios

CNPJ = "02.359.273/0001-52"


def _boleto(nome, fonte="ocr", confianca=0.93, cnpj=CNPJ):
    campos = {
        "linha_digitavel": {"valor": "x", "fonte": "codigo_barras", "confianca": 0.99},
        "vencimento": {"valor": "2026-10-01", "fonte": "codigo_barras", "confianca": 0.99},
        "valor": {"valor": 10.0, "fonte": "codigo_barras", "confianca": 0.99},
        "documento_beneficiario": {"valor": cnpj, "fonte": fonte, "confianca": 0.85},
    }
    alertas = []
    if nome:
        campos["beneficiario"] = {"valor": nome, "fonte": fonte, "confianca": confianca}
    else:
        alertas.append({"nivel": "aviso", "mensagem": "Beneficiário não encontrado", "codigo": "ausente_beneficiario"})
    return {"campos": campos, "alertas": alertas, "confianca": 0.0}


def test_consenso_no_mesmo_arquivo_corrige_leitura_ruim():
    boletos = [
        _boleto("HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA", confianca=0.934),
        _boleto("NIPER 3N-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA", confianca=0.889),
        _boleto("HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA", confianca=0.938),
        _boleto("OUTRA EMPRESA LTDA", cnpj="45.262.202/0001-40"),
    ]
    harmonizar_beneficiarios(boletos)
    nomes = [b["campos"]["beneficiario"]["valor"] for b in boletos]
    assert nomes[:3] == ["HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA"] * 3
    assert nomes[3] == "OUTRA EMPRESA LTDA"
    assert any(a["codigo"] == "beneficiario_consenso" for a in boletos[1]["alertas"])


def test_historico_da_planilha_prevalece_e_preenche_ausente(tmp_path):
    planilha = BancoBoletos(tmp_path / "b.db", tmp_path / "b.xlsx")
    planilha.adicionar({"beneficiario": "Hiper JN Materiais para Construção", "documento_beneficiario": CNPJ})
    boletos = [_boleto("NIPER 3N-COMERCIO LTDA"), _boleto(None)]
    harmonizar_beneficiarios(boletos, planilha)
    for b in boletos:
        assert b["campos"]["beneficiario"] == {"valor": "Hiper JN Materiais para Construção", "fonte": "historico", "confianca": 0.97}
        assert not any(a["codigo"] == "ausente_beneficiario" for a in b["alertas"])
        assert b["confianca"] == 0.97

import os
import sys
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

# Isola os dados dos testes antes de importar a aplicação
os.environ["LEITOR_DADOS_DIR"] = tempfile.mkdtemp(prefix="leitor-boletos-testes-")
os.environ["LEITOR_IA_AUTOMATICA"] = "0"
os.environ["LEITOR_NOTIFICACOES_AUTOMATICAS"] = "0"
os.environ["LEITOR_BACKUP_AUTOMATICO"] = "0"

from gerar_boleto_exemplo import gerar_imagem_do_pdf, gerar_pdf  # noqa: E402

VENCIMENTO = date.today() + timedelta(days=26)
VALOR = Decimal("1500.75")


@pytest.fixture(scope="session")
def pasta_exemplos(tmp_path_factory):
    return tmp_path_factory.mktemp("exemplos")


@pytest.fixture(scope="session")
def boleto_pdf(pasta_exemplos):
    caminho = pasta_exemplos / "boleto.pdf"
    linha = gerar_pdf(caminho, beneficiario="EMPRESA EXEMPLO DE SERVIÇOS LTDA", cnpj="12.345.678/0001-95",
                      documento="NF-2026/0457", vencimento=VENCIMENTO, valor=VALOR)
    return caminho, linha


@pytest.fixture(scope="session")
def boleto_foto(boleto_pdf, pasta_exemplos):
    caminho = pasta_exemplos / "boleto.jpg"
    gerar_imagem_do_pdf(boleto_pdf[0], caminho, rotacao=90)
    return caminho, boleto_pdf[1]

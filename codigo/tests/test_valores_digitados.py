"""Valores digitados: "1.500" é mil e quinhentos (não R$ 1,50) nas telas, na busca, na leitura e na planilha Excel."""

import json
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest

from app.boleto.extrator import _converter_campo
from app.busca_comprovantes import _valor_pesquisado
from app.planilha import ABAS, PlanilhaBoletos

WEB = Path(__file__).resolve().parent.parent / "web" / "js" / "ui.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="precisa do Node para rodar o JavaScript da tela")
def test_tela_le_ponto_de_milhar():
    script = (f"import {{ parseValor }} from {json.dumps(WEB.as_uri())};"
              "const casos = ['1.500', '12.000', '1.500,50', '2.5', '0.500', '30', 'R$ 2.000', ''];"
              "console.log(JSON.stringify([...casos.map((c) => parseValor(c)), parseValor('7.450', { milhar: false })]));")
    saida = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True)
    assert json.loads(saida.stdout) == [1500, 12000, 1500.5, 2.5, 0.5, 30, 2000, None, 7.45]


def test_busca_de_comprovante_pelo_valor():
    assert _valor_pesquisado("1.500") == 1500.0
    assert _valor_pesquisado("R$ 2.000") == 2000.0
    assert _valor_pesquisado("1.500,50") == 1500.5
    assert _valor_pesquisado("2.5") == 2.5


def test_valor_conferido_na_leitura_do_boleto():
    assert _converter_campo("valor", "1.500") == Decimal("1500")
    assert _converter_campo("valor", "R$ 1.234,56") == Decimal("1234.56")
    assert _converter_campo("valor", "956.70") == Decimal("956.70")


def test_valor_digitado_como_texto_no_excel(tmp_path):
    p = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    ler = lambda chave, valor: p._converter_leitura(chave, valor, ABAS["boletos"])  # noqa: E731
    assert ler("valor", "1234.56") == 1234.56  # antes virava 123456,00
    assert ler("valor", "1.234,56") == 1234.56
    assert ler("valor", "1.500") == 1500.0
    assert ler("litros", "50.5") == 50.5  # antes virava 505
    assert ler("litros", "1.234,5") == 1234.5

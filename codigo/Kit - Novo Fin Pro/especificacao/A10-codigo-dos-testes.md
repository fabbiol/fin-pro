# Anexo A10 — Código completo dos testes

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

O código **completo** de cada teste automatizado. É o contrato executável: entradas reais (inclusive textos de OCR de documentos reais), resultados esperados e casos de borda. Uma nova versão que passa nestes testes faz o mesmo que a atual. Os arquivos de apoio (`conftest.py`, `corpus.py`, `gerar_boleto_exemplo.py`) vêm primeiro.

## `tests/conftest.py` (43 linhas)

```python
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
```

## `tests/corpus.py` (232 linhas)

```python
"""Corpus sintético e variado de boletos para testar a robustez da leitura.

Cobre layouts e situações comuns do dia a dia:
* bancário com rótulos na mesma linha ("Beneficiário: ...");
* conta de consumo (arrecadação, 48 dígitos) sem rótulo "Beneficiário";
* guia de tributo (DAS);
* carnê com 3 boletos na mesma página;
* PDF escaneado (só imagem, levemente torto e com ruído);
* foto de boleto em papel (perspectiva, sombra, desfoque e compressão JPEG).

Cada gerador devolve os valores esperados, usados pelos testes.
"""

from __future__ import annotations

import io
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from reportlab.graphics.barcode.common import I2of5
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.boleto.codigo import _dv_arrecadacao, barras_para_linha_arrecadacao, formatar_linha
from gerar_boleto_exemplo import montar_codigo


def _brl(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_arrecadacao(segmento: str, identificador: str, valor: Decimal, empresa: str, livre: str) -> tuple[str, str]:
    sem_dv = "8" + segmento + identificador + f"{int(valor * 100):011d}" + empresa + livre
    assert len(sem_dv) == 43, len(sem_dv)
    dv = _dv_arrecadacao(sem_dv, identificador)
    barras = sem_dv[:3] + str(dv) + sem_dv[3:]
    return barras, barras_para_linha_arrecadacao(barras)


def _barras(c: canvas.Canvas, barras: str, x: float, y: float, largura_barra=0.33 * mm, altura=13 * mm):
    I2of5(barras, barWidth=largura_barra, ratio=3, barHeight=altura, checksum=0, bearers=0, quiet=0).drawOn(c, x, y)


# --------------------------------------------------------------------------- PDFs digitais


def bancario_rotulos_inline(destino: Path) -> dict:
    venc = date.today() + timedelta(days=12)
    valor = Decimal("389.40")
    barras, linha = montar_codigo("237", venc, valor, "3381" + "09" + "00001234567" + "0" + "1234567")
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, h - 25 * mm, "Bradesco | 237-2 |")
    c.setFont("Courier-Bold", 11.5)
    c.drawString(x + 55 * mm, h - 25 * mm, formatar_linha(linha))
    c.setFont("Helvetica", 9.5)
    linhas = [
        f"Beneficiário: CLÍNICA ODONTOLÓGICA SORRISO FELIZ LTDA - CNPJ: 98.765.432/0001-10",
        "Endereço: Av. Brasil, 1500 - Centro - Curitiba/PR",
        f"Vencimento: {venc:%d/%m/%Y}",
        "Nº Documento: 2026-000781",
        "Nosso Número: 09/00001234567-P",
        f"Valor do Documento: R$ {_brl(valor)}",
        "Pagador: MARIA DA SILVA - CPF: 111.444.777-35",
        "Instruções: Não receber após 30 dias do vencimento.",
    ]
    y = h - 40 * mm
    for texto in linhas:
        c.drawString(x, y, texto)
        y -= 7 * mm
    _barras(c, barras, x, y - 20 * mm)
    c.save()
    return {"linha": linha, "beneficiario": "CLÍNICA ODONTOLÓGICA SORRISO FELIZ LTDA", "cnpj": "98.765.432/0001-10",
            "documento": "2026-000781", "vencimento": venc, "valor": valor}


def conta_de_energia(destino: Path) -> dict:
    venc = date.today() + timedelta(days=9)
    valor = Decimal("245.90")
    barras, linha = montar_arrecadacao("3", "8", valor, "0048", "0" * 3 + "123456789" + "0" * 13)
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x, h - 25 * mm, "LUZ DO VALE DISTRIBUIDORA DE ENERGIA S.A.")
    c.setFont("Helvetica", 8.5)
    c.drawString(x, h - 31 * mm, "CNPJ 07.047.251/0001-70 · Rua da Energia, 100 · Belo Horizonte/MG")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, h - 45 * mm, "CONTA DE ENERGIA ELÉTRICA")
    c.setFont("Helvetica", 9)
    campos = [("Cliente", "JOÃO PEREIRA"), ("Nº da Instalação", "3001234567"), ("Nota Fiscal Nº", "NF 004.512.887"),
              ("Mês de referência", "09/2026"), ("Vencimento", f"{venc:%d/%m/%Y}"), ("Total a pagar", f"R$ {_brl(valor)}")]
    y = h - 55 * mm
    for rotulo, valor_txt in campos:
        c.setFont("Helvetica", 8)
        c.drawString(x, y, rotulo)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y - 5 * mm, valor_txt)
        y -= 13 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, 70 * mm, formatar_linha(linha))
    _barras(c, barras, x, 50 * mm)
    c.save()
    return {"linha": linha, "vencimento": venc, "valor": valor, "tipo": "arrecadacao", "beneficiario_contem": "LUZ DO VALE"}


def guia_das(destino: Path) -> dict:
    venc = date.today() + timedelta(days=20)
    valor = Decimal("1234.56")
    barras, linha = montar_arrecadacao("5", "8", valor, "0328", "0" * 3 + "07202612345678901" + "00000")
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    x = 15 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, h - 22 * mm, "Documento de Arrecadação do Simples Nacional")
    c.setFont("Helvetica", 9)
    c.drawString(x, h - 30 * mm, "CNPJ: 12.345.678/0001-95   Razão Social: PADARIA PÃO QUENTE LTDA")
    c.drawString(x, h - 40 * mm, "Período de Apuração: Setembro/2026")
    c.drawString(x, h - 47 * mm, f"Pagar este documento até: {venc:%d/%m/%Y}")
    c.drawString(x, h - 54 * mm, "Número do Documento: 07.20.26262.1234567-8")
    c.drawString(x, h - 61 * mm, f"Valor Total do Documento: {_brl(valor)}")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, h - 80 * mm, formatar_linha(linha))
    _barras(c, barras, x, h - 100 * mm)
    c.save()
    return {"linha": linha, "vencimento": venc, "valor": valor, "documento": "07.20.26262.1234567-8",
            "beneficiario_contem": "Simples Nacional"}


def carne_tres_boletos(destino: Path) -> list[dict]:
    esperados = []
    c = canvas.Canvas(str(destino), pagesize=A4)
    w, h = A4
    altura_boleto = h / 3
    for i in range(3):
        venc = date.today() + timedelta(days=30 * (i + 1))
        valor = Decimal("150.00") + i * Decimal("10.50")
        barras, linha = montar_codigo("756", venc, valor, "1" + "4321" + "02" + f"{1234567 + i:07d}" + "001" + "00000000")
        topo = h - i * altura_boleto - 12 * mm
        x = 12 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, topo, "SICOOB | 756-0 |")
        c.setFont("Helvetica-Bold", 10.5)
        c.drawRightString(w - 12 * mm, topo, formatar_linha(linha))
        c.setFont("Helvetica", 6.5)
        c.drawString(x, topo - 7 * mm, "Beneficiário")
        c.drawString(x + 125 * mm, topo - 7 * mm, "Vencimento")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, topo - 11 * mm, "ESCOLA APRENDER MAIS LTDA")
        c.drawString(x + 125 * mm, topo - 11 * mm, f"{venc:%d/%m/%Y}")
        c.setFont("Helvetica", 6.5)
        c.drawString(x, topo - 17 * mm, "Nº do Documento")
        c.drawString(x + 125 * mm, topo - 17 * mm, "Valor do Documento")
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, topo - 21 * mm, f"MENS-{i + 1:02d}/2026")
        c.drawString(x + 125 * mm, topo - 21 * mm, _brl(valor))
        _barras(c, barras, x, topo - 45 * mm, altura=11 * mm)
        c.setDash(3, 2)
        c.line(8 * mm, h - (i + 1) * altura_boleto, w - 8 * mm, h - (i + 1) * altura_boleto)
        c.setDash()
        esperados.append({"linha": linha, "vencimento": venc, "valor": valor, "documento": f"MENS-{i + 1:02d}/2026",
                          "beneficiario": "ESCOLA APRENDER MAIS LTDA"})
    c.save()
    return esperados


# --------------------------------------------------------------------------- papel


def _renderizar(pdf: Path, escala: float) -> Image.Image:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[0].render(scale=escala).to_pil().convert("RGB")
    finally:
        doc.close()


def pdf_escaneado(origem_pdf: Path, destino: Path, semente: int = 7, rotacao: int = 0) -> None:
    """Simula um boleto de papel passado no scanner e salvo como PDF (sem camada de texto).

    ``rotacao=90`` reproduz o caso real de folha escaneada deitada.
    """
    rng = np.random.default_rng(semente)
    img = _renderizar(origem_pdf, 150 / 72).convert("L")
    img = img.rotate(1.3, expand=False, fillcolor=250, resample=Image.BICUBIC)
    if rotacao:
        img = img.rotate(rotacao, expand=True, fillcolor=250)
    matriz = np.array(img).astype(np.float32)
    matriz += rng.normal(0, 9, matriz.shape)
    matriz = matriz * 0.93 + 12
    img = Image.fromarray(np.clip(matriz, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=70)
    Image.open(buffer).convert("RGB").save(destino, "PDF", resolution=150)


def foto_de_papel(origem_pdf: Path, destino: Path, semente: int = 3, angulo: float = 6.0) -> None:
    """Simula foto de celular: papel sobre mesa, perspectiva, sombra, desfoque e JPEG."""
    import cv2

    random.seed(semente)
    papel = np.array(_renderizar(origem_pdf, 2.4))
    ph, pw = papel.shape[:2]
    W, H = int(pw * 1.35), int(ph * 1.25)
    fundo = np.zeros((H, W, 3), np.uint8)
    fundo[:] = (92, 70, 52)
    ruido = np.random.default_rng(semente).integers(0, 25, (H, W, 1), dtype=np.uint8)
    fundo = cv2.add(fundo, np.repeat(ruido, 3, axis=2))

    origem = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    mx, my = W * 0.14, H * 0.1
    destino_pts = np.float32([
        [mx + 40, my], [W - mx + 10, my + 60], [W - mx - 60, H - my], [mx - 20, H - my - 40],
    ])
    matriz = cv2.getPerspectiveTransform(origem, destino_pts)
    rot = cv2.getRotationMatrix2D((W / 2, H / 2), angulo, 1.0)
    matriz = np.vstack([rot, [0, 0, 1]]) @ matriz
    quadro = cv2.warpPerspective(papel, matriz, (W, H), borderMode=cv2.BORDER_TRANSPARENT, dst=fundo.copy())

    gradiente = np.tile(np.linspace(0.78, 1.05, W, dtype=np.float32), (H, 1))[..., None]
    quadro = np.clip(quadro.astype(np.float32) * gradiente, 0, 255).astype(np.uint8)
    quadro = cv2.GaussianBlur(quadro, (3, 3), 0.9)
    Image.fromarray(quadro).resize((W * 3 // 4, H * 3 // 4), Image.LANCZOS).save(destino, "JPEG", quality=72)
```

## `tests/gerar_boleto_exemplo.py` (166 linhas)

```python
"""Gera boletos de exemplo (PDF e imagem) com dígitos verificadores válidos.

Uso:  python tests/gerar_boleto_exemplo.py [pasta_destino]
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.graphics.barcode.common import I2of5  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from app.boleto.codigo import barras_para_linha_bancario, fator_por_data, formatar_linha, modulo11_bancario  # noqa: E402


def montar_codigo(banco: str, vencimento: date, valor: Decimal, campo_livre: str) -> tuple[str, str]:
    assert len(campo_livre) == 25
    fator = f"{fator_por_data(vencimento):04d}"
    valor_txt = f"{int(valor * 100):010d}"
    sem_dv = banco + "9" + fator + valor_txt + campo_livre
    dv = modulo11_bancario(sem_dv)
    barras = sem_dv[:4] + str(dv) + sem_dv[4:]
    return barras, barras_para_linha_bancario(barras)


def _rotulo(c: canvas.Canvas, x: float, y: float, texto: str):
    c.setFont("Helvetica", 6.5)
    c.drawString(x + 1.5 * mm, y - 3 * mm, texto)


def _valor(c: canvas.Canvas, x: float, y: float, texto: str, direita: float | None = None, tamanho: float = 9):
    c.setFont("Helvetica-Bold", tamanho)
    if direita is not None:
        c.drawRightString(direita - 2 * mm, y - 7.5 * mm, texto)
    else:
        c.drawString(x + 1.5 * mm, y - 7.5 * mm, texto)


def gerar_pdf(destino: Path, *, beneficiario: str, cnpj: str, documento: str, vencimento: date,
              valor: Decimal, banco: str = "341", campo_livre: str = "1091234567812345678901230") -> str:
    barras, linha = montar_codigo(banco, vencimento, valor, campo_livre)
    c = canvas.Canvas(str(destino), pagesize=A4)
    largura, altura = A4
    esq, dirx = 12 * mm, largura - 12 * mm
    col_dir = dirx - 48 * mm
    venc_txt = vencimento.strftime("%d/%m/%Y")
    valor_txt = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # ---- Recibo do pagador
    topo = altura - 20 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(esq, topo, "Banco Itaú S.A.  | 341-7 |")
    c.setFont("Helvetica", 8)
    c.drawRightString(dirx, topo, "RECIBO DO PAGADOR")
    y = topo - 4 * mm
    c.rect(esq, y - 10 * mm, dirx - esq, 10 * mm)
    _rotulo(c, esq, y, "Beneficiário")
    _valor(c, esq, y, f"{beneficiario} - CNPJ {cnpj}")
    c.line(col_dir, y, col_dir, y - 10 * mm)
    _rotulo(c, col_dir, y, "Vencimento")
    _valor(c, col_dir, y, venc_txt, direita=dirx)
    y -= 10 * mm
    c.rect(esq, y - 10 * mm, dirx - esq, 10 * mm)
    _rotulo(c, esq, y, "Nº do Documento")
    _valor(c, esq, y, documento)
    c.line(col_dir, y, col_dir, y - 10 * mm)
    _rotulo(c, col_dir, y, "Valor do Documento")
    _valor(c, col_dir, y, valor_txt, direita=dirx)

    # ---- Ficha de compensação
    c.setDash(3, 2)
    c.line(esq, altura - 62 * mm, dirx, altura - 62 * mm)
    c.setDash()
    topo = altura - 75 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(esq, topo, "Banco Itaú S.A.  | 341-7 |")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(dirx, topo, formatar_linha(linha))
    y = topo - 3 * mm
    linhas = [
        ("Local de pagamento", "PAGÁVEL EM QUALQUER BANCO ATÉ O VENCIMENTO", "Vencimento", venc_txt),
        ("Beneficiário", f"{beneficiario}   CNPJ: {cnpj}", "Agência/Código do Beneficiário", "1234/56789-0"),
    ]
    for rot1, val1, rot2, val2 in linhas:
        c.rect(esq, y - 10 * mm, dirx - esq, 10 * mm)
        _rotulo(c, esq, y, rot1)
        _valor(c, esq, y, val1, tamanho=8.5)
        c.line(col_dir, y, col_dir, y - 10 * mm)
        _rotulo(c, col_dir, y, rot2)
        _valor(c, col_dir, y, val2, direita=dirx)
        y -= 10 * mm

    c.rect(esq, y - 10 * mm, dirx - esq, 10 * mm)
    colunas = [("Data do Documento", date.today().strftime("%d/%m/%Y")), ("Nº do Documento", documento),
               ("Espécie Doc.", "DM"), ("Aceite", "N"), ("Data Processamento", date.today().strftime("%d/%m/%Y"))]
    largura_col = (col_dir - esq) / len(colunas)
    for i, (rot, val) in enumerate(colunas):
        x = esq + i * largura_col
        if i:
            c.line(x, y, x, y - 10 * mm)
        _rotulo(c, x, y, rot)
        _valor(c, x, y, val, tamanho=8.5)
    c.line(col_dir, y, col_dir, y - 10 * mm)
    _rotulo(c, col_dir, y, "Nosso Número")
    _valor(c, col_dir, y, "109/12345678-9", direita=dirx)
    y -= 10 * mm

    c.rect(esq, y - 10 * mm, dirx - esq, 10 * mm)
    _rotulo(c, esq, y, "Uso do Banco")
    _rotulo(c, esq + 40 * mm, y, "Carteira")
    _valor(c, esq + 40 * mm, y, "109", tamanho=8.5)
    _rotulo(c, esq + 70 * mm, y, "Espécie")
    _valor(c, esq + 70 * mm, y, "R$", tamanho=8.5)
    c.line(col_dir, y, col_dir, y - 10 * mm)
    _rotulo(c, col_dir, y, "(=) Valor do Documento")
    _valor(c, col_dir, y, valor_txt, direita=dirx)
    y -= 10 * mm

    c.rect(esq, y - 22 * mm, dirx - esq, 22 * mm)
    _rotulo(c, esq, y, "Instruções (texto de responsabilidade do beneficiário)")
    c.setFont("Helvetica", 8)
    c.drawString(esq + 2 * mm, y - 9 * mm, "Após o vencimento cobrar multa de 2% e juros de 1% ao mês.")
    _rotulo(c, col_dir, y, "(-) Desconto / Abatimento")
    y -= 22 * mm

    c.rect(esq, y - 14 * mm, dirx - esq, 14 * mm)
    _rotulo(c, esq, y, "Pagador")
    c.setFont("Helvetica", 8.5)
    c.drawString(esq + 2 * mm, y - 8 * mm, "FULANO DE TAL - CPF: 123.456.789-09 - Rua Exemplo, 100 - São Paulo/SP")
    y -= 18 * mm

    codigo = I2of5(barras, barWidth=0.33 * mm, ratio=3, barHeight=13 * mm, checksum=0, bearers=0, quiet=0)
    codigo.drawOn(c, esq, y - 13 * mm)
    c.setFont("Helvetica", 7)
    c.drawRightString(dirx, y - 16 * mm, "Autenticação mecânica - Ficha de Compensação")
    c.showPage()
    c.save()
    return linha


def gerar_imagem_do_pdf(pdf: Path, destino: Path, escala: float = 2.2, rotacao: int = 0):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    img = doc[0].render(scale=escala).to_pil().convert("RGB")
    doc.close()
    if rotacao:
        img = img.rotate(rotacao, expand=True, fillcolor="white")
    img.save(destino, quality=90)


if __name__ == "__main__":
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "exemplos"
    pasta.mkdir(parents=True, exist_ok=True)
    pdf = pasta / "boleto_exemplo.pdf"
    linha = gerar_pdf(pdf, beneficiario="EMPRESA EXEMPLO DE SERVIÇOS LTDA", cnpj="12.345.678/0001-95",
                      documento="NF-2026/0457", vencimento=date(2026, 10, 10), valor=Decimal("1500.75"))
    gerar_imagem_do_pdf(pdf, pasta / "boleto_exemplo_foto.jpg")
    print("Gerado:", pdf, formatar_linha(linha))
```

## `tests/test_admin.py` (60 linhas)

```python
"""Senha de administrador: protege a importação de boletos, inclusive contra acesso direto à API."""

import pytest
from fastapi.testclient import TestClient

from app import admin, contexto, importacao, main


@pytest.fixture
def app_protegido(tmp_path, monkeypatch):
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    monkeypatch.setattr(contexto, "importacoes", importacao.ArmazemImportacoes(tmp_path / "importacoes"))
    return main.app


def test_importacao_so_abre_com_a_senha_de_administrador(app_protegido, tmp_path):
    with TestClient(app_protegido, client=("192.168.0.77", 50000)) as outro_aparelho:
        # Um aparelho da rede não consegue criar a senha nem usar a importação
        assert outro_aparelho.post("/api/admin/senha", json={"senha": "invasor123", "confirmacao": "invasor123"}).status_code in (401, 403)
        assert outro_aparelho.get("/api/importacao/modelo.xlsx").status_code in (401, 403)
    assert not contexto.administrador.senha_definida

    with TestClient(app_protegido, client=("127.0.0.1", 50000)) as computador:
        assert computador.get("/api/importacao/modelo.xlsx").json()["detail"]["codigo"] == "admin_sem_senha"
        assert computador.post("/api/admin/senha", json={"senha": "123", "confirmacao": "123"}).status_code == 422
        criada = computador.post("/api/admin/senha", json={"senha": "senha-do-dono", "confirmacao": "senha-do-dono"})
        assert criada.status_code == 200 and criada.json()["autorizado"]
        assert computador.get("/api/importacao/modelo.xlsx").status_code == 200
        assert computador.post("/api/importacao/" + "0" * 32 + "/previa", json={}).status_code == 404  # passou pela senha

        computador.post("/api/admin/sair")
        assert computador.get("/api/importacao/modelo.xlsx").json()["detail"]["codigo"] == "admin_necessario"
        assert computador.post("/api/importacao/" + "0" * 32 + "/importar", json={"indices": [0]}).status_code == 403
        assert computador.post("/api/admin/entrar", json={"senha": "senha-errada"}).status_code == 401
        assert computador.post("/api/admin/entrar", json={"senha": "senha-do-dono"}).status_code == 200
        assert computador.get("/api/admin").json()["autorizado"]

        # Trocar a senha exige a atual
        sem_atual = computador.post("/api/admin/senha", json={"senha": "nova-senha", "confirmacao": "nova-senha"})
        assert sem_atual.status_code == 403
        trocada = computador.post("/api/admin/senha", json={"senha": "nova-senha", "confirmacao": "nova-senha", "senha_atual": "senha-do-dono"})
        assert trocada.status_code == 200

    conteudo = (tmp_path / "admin.json").read_text(encoding="utf-8")
    assert "senha-do-dono" not in conteudo and "nova-senha" not in conteudo


def test_bloqueio_por_tentativas_e_fim_das_sessoes(tmp_path):
    gerenciador = admin.GerenciadorAdmin(tmp_path / "admin.json")
    gerenciador.definir_senha("senha-certa")
    for _ in range(admin.MAX_TENTATIVAS):
        assert gerenciador.entrar("errada", "10.0.0.9")[0] is None
    token, bloqueio = gerenciador.entrar("senha-certa", "10.0.0.9")
    assert token is None and bloqueio > 0  # nem a senha certa entra durante o bloqueio

    token, _ = gerenciador.entrar("senha-certa", "10.0.0.10")
    assert gerenciador.autorizado(token) and not gerenciador.autorizado("token-inventado")
    gerenciador.definir_senha("outra-senha")
    assert not gerenciador.autorizado(token)  # trocar a senha bloqueia quem estava liberado
    assert admin.GerenciadorAdmin(tmp_path / "admin.json").verificar("outra-senha")
```

## `tests/test_api.py` (114 linhas)

```python
"""Testes ponta a ponta da API com boletos gerados (PDF com texto e foto girada via OCR)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.boleto.codigo import formatar_linha
from app.main import app
from conftest import VALOR, VENCIMENTO


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _enviar(cliente, caminho, tipo):
    with open(caminho, "rb") as f:
        resp = cliente.post("/api/leituras", files={"arquivo": (caminho.name, f, tipo)})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_status(cliente):
    dados = cliente.get("/api/status").json()
    assert dados["ocr"] is True and "planilha" in dados


def test_fluxo_pdf_lancamento_duplicidade_e_consultas(cliente, boleto_pdf):
    caminho, linha = boleto_pdf
    leitura = _enviar(cliente, caminho, "application/pdf")
    assert leitura["tipo_arquivo"] == "pdf" and len(leitura["boletos"]) == 1
    boleto = leitura["boletos"][0]
    campos = {k: v["valor"] for k, v in boleto["campos"].items()}
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert campos["beneficiario"] == "EMPRESA EXEMPLO DE SERVIÇOS LTDA"
    assert campos["documento_beneficiario"] == "12.345.678/0001-95"
    assert campos["numero_documento"] == "NF-2026/0457"
    assert campos["vencimento"] == VENCIMENTO.isoformat()
    assert campos["valor"] == float(VALOR)
    assert boleto["campos"]["linha_digitavel"]["fonte"] == "codigo_barras"
    assert boleto["confianca"] >= 0.9
    assert boleto["duplicado"] is None
    assert cliente.get(f"/api/arquivos/{leitura['arquivo']['id']}").status_code == 200

    payload = {**{k: campos[k] for k in ("linha_digitavel", "beneficiario", "documento_beneficiario",
                                          "numero_documento", "vencimento", "valor")},
               "arquivo_id": leitura["arquivo"]["id"]}
    criado = cliente.post("/api/boletos", json=payload)
    assert criado.status_code == 201, criado.text
    registro = criado.json()
    assert registro["id"] >= 1 and registro["data_lancamento"] and registro["situacao"] == "a_vencer"
    assert registro["arquivo"].startswith("arquivos/")

    duplicado = cliente.post("/api/boletos", json=payload)
    assert duplicado.status_code == 409 and duplicado.json()["detail"]["codigo"] == "duplicado"

    releitura = _enviar(cliente, caminho, "application/pdf")
    assert releitura["boletos"][0]["duplicado"]["id"] == registro["id"]

    lista = cliente.get("/api/boletos", params={"q": "exemplo servicos"}).json()
    assert lista["total"] == 1 and lista["resumo"]["valor_pendente"] == float(VALOR)
    assert cliente.get("/api/boletos", params={"situacao": "pago"}).json()["total"] == 0

    pago = cliente.patch(f"/api/boletos/{registro['id']}/status", json={"status": "Pago"}).json()
    assert pago["status"] == "Pago" and pago["data_pagamento"] == date.today().isoformat()

    editado = cliente.put(f"/api/boletos/{registro['id']}", json={"observacoes": "Pago via app"}).json()
    assert editado["observacoes"] == "Pago via app" and editado["beneficiario"] == campos["beneficiario"]

    painel = cliente.get("/api/painel").json()
    assert painel["indicadores"]["pagos_mes_qtd"] >= 1 and len(painel["serie_mensal"]) == 12

    assert cliente.get("/api/exportar", params={"formato": "csv"}).content.startswith("﻿".encode())
    assert cliente.get("/api/exportar", params={"formato": "xlsx"}).status_code == 200
    assert cliente.get(f"/api/boletos/{registro['id']}/arquivo").status_code == 200

    assert cliente.delete(f"/api/boletos/{registro['id']}").status_code == 204
    assert cliente.get(f"/api/boletos/{registro['id']}").status_code == 404


def test_linha_digitada(cliente, boleto_pdf):
    _, linha = boleto_pdf
    ok = cliente.post("/api/leituras/linha", json={"linha": linha}).json()
    assert ok["codigo"]["valido"] and ok["campos"]["valor"]["valor"] == float(VALOR)

    errada = linha[:5] + str((int(linha[5]) + 1) % 10) + linha[6:]
    invalida = cliente.post("/api/leituras/linha", json={"linha": errada}).json()
    assert not invalida["codigo"]["valido"]
    assert formatar_linha(linha) in invalida["sugestoes_linha"]

    assert cliente.post("/api/leituras/linha", json={"linha": "123"}).status_code == 422
    resp = cliente.post("/api/boletos", json={"linha_digitavel": errada, "valor": 1})
    assert resp.status_code == 422 and resp.json()["detail"]["codigo"] == "linha_invalida"


def test_foto_girada_com_ocr(cliente, boleto_foto):
    caminho, linha = boleto_foto
    leitura = _enviar(cliente, caminho, "image/jpeg")
    assert leitura["ocr_usado"]
    boleto = leitura["boletos"][0]
    campos = {k: v["valor"] for k, v in boleto["campos"].items()}
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert campos["vencimento"] == VENCIMENTO.isoformat()
    assert campos["valor"] == float(VALOR)
    assert campos["beneficiario"] == "EMPRESA EXEMPLO DE SERVIÇOS LTDA"
    assert campos["numero_documento"] == "NF-2026/0457"


def test_arquivo_invalido(cliente):
    resp = cliente.post("/api/leituras", files={"arquivo": ("x.txt", b"nao sou boleto", "text/plain")})
    assert resp.status_code == 422
```

## `tests/test_api_melhorias.py` (91 linhas)

```python
"""Leitura em segundo plano, lançamento em lote, gravação pendente e senha de acesso."""

import time
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app, planilha
from app.planilha import PlanilhaBloqueadaError
from conftest import VALOR
from gerar_boleto_exemplo import montar_codigo


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def _aguardar(cliente, tarefa):
    for _ in range(240):
        if tarefa["status"] in ("concluida", "erro"):
            return tarefa
        time.sleep(0.25)
        tarefa = cliente.get(f"/api/leituras/tarefas/{tarefa['id']}").json()
    raise AssertionError("a leitura não terminou")


def test_leitura_em_segundo_plano_com_progresso(cliente, boleto_pdf):
    caminho, _ = boleto_pdf
    with open(caminho, "rb") as f:
        resposta = cliente.post("/api/leituras/tarefas", files={"arquivo": ("b.pdf", f, "application/pdf")})
    assert resposta.status_code == 202
    tarefa = _aguardar(cliente, resposta.json())
    assert tarefa["status"] == "concluida" and tarefa["percentual"] == 100 and tarefa["paginas"] == 1
    assert tarefa["resultado"]["boletos"][0]["campos"]["valor"]["valor"] == float(VALOR)
    assert cliente.get("/api/leituras/tarefas/nao-existe").status_code == 404


def test_tarefa_com_arquivo_invalido(cliente):
    tarefa = cliente.post("/api/leituras/tarefas", files={"arquivo": ("x.txt", b"nada", "text/plain")}).json()
    tarefa = _aguardar(cliente, tarefa)
    assert tarefa["status"] == "erro" and tarefa["erro"]["codigo"] == "leitura_falhou"


def test_lancamento_em_lote(cliente):
    _, linha_a = montar_codigo("237", date.today() + timedelta(days=10), Decimal("10.00"), "1" * 25)
    _, linha_b = montar_codigo("237", date.today() + timedelta(days=11), Decimal("20.00"), "2" * 25)
    resposta = cliente.post("/api/boletos/lote", json={"boletos": [
        {"linha_digitavel": linha_a, "beneficiario": "Lote A", "valor": 10},
        {"linha_digitavel": linha_b, "beneficiario": "Lote B", "valor": 20},
        {"linha_digitavel": linha_a, "beneficiario": "Repetido no lote"},
        {"linha_digitavel": "123", "valor": 1},
    ]}).json()
    assert [c["indice"] for c in resposta["criados"]] == [0, 1]
    assert {e["indice"]: e["codigo"] for e in resposta["erros"]} == {2: "duplicado", 3: "linha_invalida"}
    assert resposta["pendente_gravacao"] is False
    for criado in resposta["criados"]:
        assert cliente.delete(f"/api/boletos/{criado['registro']['id']}").status_code == 204


def test_planilha_aberta_no_excel_nao_segura_lancamentos(cliente, monkeypatch):
    """Com o banco de dados, o lançamento é gravado na hora; a planilha Excel é atualizada quando for fechada."""
    def travada():
        raise PlanilhaBloqueadaError("A planilha está aberta em outro programa (ex.: Excel).")

    monkeypatch.setattr(planilha.excel, "_verificar_gravavel", travada)
    criado = cliente.post("/api/boletos", json={"beneficiario": "Com Excel aberto", "valor": 3, "ignorar_validacao": True}).json()
    assert criado["id"] > 0 and not criado.get("pendente_gravacao")
    assert cliente.get("/api/gravacao").json()["pendentes"] == 0
    assert planilha.exportar() is False and planilha.exportacao["excel_aberto"]

    monkeypatch.undo()
    assert planilha.exportar() and not planilha.exportacao["excel_aberto"]
    cliente.delete(f"/api/boletos/{criado['id']}")


def test_senha_de_acesso_para_aparelhos_da_rede(monkeypatch):
    monkeypatch.setattr(config, "SENHA_ACESSO", "segredo123")
    with TestClient(app, client=("192.168.0.50", 50000)) as remoto:
        assert remoto.get("/api/boletos").status_code == 401
        estado = remoto.get("/api/acesso/estado").json()
        assert estado["protegido"] and not estado["autorizado"] and not estado["local"]
        assert remoto.post("/api/acesso", json={"senha": "errada"}).status_code == 401
        assert remoto.post("/api/acesso", json={"senha": "segredo123"}).status_code == 200
        assert remoto.get("/api/boletos").status_code == 200
    with TestClient(app) as local:
        assert local.get("/api/boletos").status_code == 200
```

## `tests/test_backup.py` (318 linhas)

```python
"""Backup automático para fora do computador (OneDrive, Google Drive, pen drive)."""

import os
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import admin, backup, contexto, main


@pytest.fixture
def ambiente(tmp_path):
    dados = tmp_path / "dados"
    (dados / "arquivos").mkdir(parents=True)
    (dados / "boletos.xlsx").write_bytes(b"planilha")
    (dados / "arquivos" / "a1.pdf").write_bytes(b"%PDF boleto")
    (dados / "notificacoes.json").write_text("{}", encoding="utf-8")
    nuvem = tmp_path / "OneDrive"
    nuvem.mkdir()
    gerenciador = backup.GerenciadorBackup(dados / "backup.json", dados, dados / "boletos.xlsx", dados / "arquivos")
    return gerenciador, dados, nuvem


def test_copia_planilha_arquivos_e_configuracoes(ambiente):
    gerenciador, dados, nuvem = ambiente
    with pytest.raises(ValueError):
        gerenciador.configurar(ativo=True)  # sem pasta
    with pytest.raises(ValueError):
        gerenciador.configurar(pasta=str(dados / "arquivos"))  # dentro da pasta de dados não protege nada
    with pytest.raises(ValueError):
        gerenciador.configurar(pasta=str(nuvem / "nao-existe"))
    status = gerenciador.configurar(pasta=str(nuvem), ativo=True, horario="12:30")
    assert status["situacao"] == "aguardando" and gerenciador.deve_executar()  # o primeiro backup sai na hora

    resultado = gerenciador.executar()
    raiz = nuvem / backup.NOME_PASTA
    assert resultado["ok"] and resultado["arquivos_copiados"] == 1
    assert (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.xlsx").read_bytes() == b"planilha"
    assert (raiz / "arquivos" / "a1.pdf").exists() and (raiz / "configuracoes" / "notificacoes.json").exists()
    assert (raiz / "LEIA-ME.txt").exists()
    assert gerenciador.status()["situacao"] == "ok" and not gerenciador.deve_executar()

    # Só copia o que mudou; cópias antigas da planilha são apagadas depois de N dias
    antiga = raiz / "planilha" / f"boletos-{date.today() - timedelta(days=40):%Y-%m-%d}.xlsx"
    antiga.write_bytes(b"velha")
    (raiz / "planilha" / "outro-arquivo.xlsx").write_bytes(b"do usuario")
    (dados / "arquivos" / "b2.jpg").write_bytes(b"foto")
    segundo = gerenciador.executar()
    assert segundo["arquivos_copiados"] == 1 and segundo["arquivos_total"] == 2
    assert not antiga.exists() and (raiz / "planilha" / "outro-arquivo.xlsx").exists()


def test_avisa_quando_o_backup_atrasa_ou_falha(ambiente):
    gerenciador, _, nuvem = ambiente
    gerenciador.configurar(pasta=str(nuvem), ativo=True)
    gerenciador._estado["configurado_em"] = (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds")
    assert gerenciador.status()["situacao"] == "atrasado"

    gerenciador._estado["pasta"] = str(nuvem / "pen-drive-removido")
    resultado = gerenciador.executar()
    assert not resultado["ok"] and "não encontrada" in resultado["erro"]
    assert not gerenciador.deve_executar()  # espera antes de tentar de novo

    ontem = datetime.now() - timedelta(days=1)
    gerenciador._estado.update(pasta=str(nuvem), ultimo={"ok": False, "quando": ontem.isoformat()},
                               ultimo_sucesso=ontem.isoformat(timespec="seconds"), horario="00:00")
    assert gerenciador.deve_executar(datetime.now())


def test_api_do_backup_exige_administrador(ambiente, monkeypatch, tmp_path):
    gerenciador, _, nuvem = ambiente
    monkeypatch.setattr(contexto, "backup", gerenciador)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        assert computador.get("/api/backup").json()["situacao"] == "desligado"
        assert computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True}).status_code == 403
        computador.post("/api/admin/senha", json={"senha": "senha-adm", "confirmacao": "senha-adm"})
        ligado = computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True})
        assert ligado.status_code == 200 and ligado.json()["ativo"]
        assert computador.post("/api/backup/agora").json()["situacao"] == "ok"
        assert computador.get("/api/status").json()["backup"]["situacao"] == "ok"
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        contexto_rede = rede.get("/api/backup").json()
        assert "pasta" not in contexto_rede or contexto_rede.get("detail")
        assert rede.post("/api/backup/agora").status_code in (401, 403)


def test_sugere_pastas_de_nuvem(tmp_path, monkeypatch):
    (tmp_path / "Dropbox").mkdir()
    onedrive = tmp_path / "OneDrive - Empresa"
    onedrive.mkdir()
    monkeypatch.setenv("OneDriveCommercial", str(onedrive))
    nomes = {s["nome"]: s["pasta"] for s in backup.sugerir_pastas(tmp_path)}
    assert nomes["OneDrive da empresa"] == str(onedrive) and nomes["Dropbox"] == str(tmp_path / "Dropbox")
    assert os.path.isdir(nomes["Dropbox"])


# --------------------------------------------------------------------------- backup TOTAL (código, versões, pacote, restauração)

import importlib.util  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import sqlite3  # noqa: E402
import subprocess  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402

from app import versao  # noqa: E402
from app.banco import BancoBoletos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TEM_GIT = shutil.which("git") is not None


def _restaurador():
    spec = importlib.util.spec_from_file_location("restaurar_backup", RAIZ / "ferramentas" / "restaurar_backup.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def sistema(tmp_path):
    """Um Fin Pro em miniatura: pasta do sistema com código, repositório, banco de verdade, arquivos e configurações."""
    pasta = tmp_path / "Fin Pro"
    for relativo, conteudo in (("app/__init__.py", '__version__ = "9.9.9"\n'), ("app/servico.py", "def soma(a, b):\n    return a + b\n"),
                               ("web/index.html", "<h1>Fin Pro</h1>\n"), ("iniciar.bat", "@echo off\r\n"),
                               (".env", "LEITOR_SENHA_ACESSO=segredo\n"), (".venv/Lib/pacote.py", "pesado\n"),
                               ("app/__pycache__/servico.cpython-312.pyc", "cache\n"), ("dados_demo/boletos.db", "demo\n")):
        arquivo = pasta / relativo
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding="utf-8")
    (pasta / "ferramentas").mkdir()
    shutil.copy2(RAIZ / "ferramentas" / "restaurar_backup.py", pasta / "ferramentas" / "restaurar_backup.py")
    dados = pasta / "dados"
    (dados / "arquivos").mkdir(parents=True)
    (dados / "arquivos" / "a1.pdf").write_bytes(b"%PDF comprovante de pagamento")
    for nome in ("notificacoes.json", "diesel_bot.json", "empresas.json", "diesel_precos.json"):  # módulos novos também
        (dados / nome).write_text(json.dumps({"de": nome}), encoding="utf-8")
    banco = BancoBoletos(dados / "boletos.db", dados / "boletos.xlsx")
    banco.garantir()
    banco.adicionar({"beneficiario": "Energisa", "valor": 480.5, "vencimento": date(2026, 10, 20)}, usuario="Fábio")
    banco.exportar()
    if TEM_GIT:
        for comando in (["init", "-q", "-b", "main"], ["config", "user.name", "Teste"], ["config", "user.email", "t@exemplo.com"],
                        ["config", "commit.gpgsign", "false"], ["add", "app/__init__.py", "app/servico.py", "web", "iniciar.bat"],
                        ["commit", "-q", "-m", "v9.9.9"], ["tag", "-a", "v9.9.9", "-m", "v9.9.9"]):
            subprocess.run(["git", *comando], cwd=pasta, check=True, capture_output=True)
    nuvem = tmp_path / "OneDrive"
    nuvem.mkdir()
    gerenciador = backup.GerenciadorBackup(
        dados / "backup.json", dados, dados / "boletos.xlsx", dados / "arquivos", copiar_banco=banco.copiar_banco,
        pasta_codigo=pasta, informar_versao=lambda: "Fin Pro v9.9.9\nPonto do repositório: abc1234\n",
        gerar_bundle=lambda destino: versao.gerar_bundle(destino, raiz=pasta),
        verificar_bundle=lambda arquivo: versao.verificar_bundle(arquivo, raiz=pasta))
    gerenciador.configurar(pasta=str(nuvem), ativo=True)
    yield gerenciador, pasta, nuvem / backup.NOME_PASTA
    banco.parar()


def test_backup_total_leva_codigo_versoes_e_todas_as_configuracoes(sistema):
    gerenciador, pasta, raiz = sistema
    resultado = gerenciador.executar()
    assert resultado["ok"] and resultado["codigo_total"] == resultado["codigo_copiados"] == 5 and resultado["tamanho"] > 0
    # o código-fonte vai inteiro; ambiente Python, caches e pastas de dados ficam de fora
    assert (raiz / "codigo" / "app" / "servico.py").read_text(encoding="utf-8").startswith("def soma")
    assert (raiz / "codigo" / "ferramentas" / "restaurar_backup.py").exists()
    for fora in (".venv", "dados", "dados_demo", "app/__pycache__", ".git", ".env"):
        assert not (raiz / "codigo" / fora).exists(), fora
    # todas as configurações (inclusive as dos módulos novos) e o .env
    for nome in ("notificacoes.json", "diesel_bot.json", "empresas.json", "diesel_precos.json", "backup.json", ".env"):
        assert (raiz / "configuracoes" / nome).is_file(), nome
    # bancos, arquivos, versão e o restaurador
    assert (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.db").stat().st_size > 0
    assert (raiz / "arquivos" / "a1.pdf").exists()
    assert (raiz / "versoes" / "VERSAO.txt").read_text(encoding="utf-8").startswith("Fin Pro v9.9.9")
    assert (raiz / "RESTAURAR.bat").exists() and (raiz / "restaurar_backup.py").exists()
    assert "RESTAURAR" in (raiz / "LEIA-ME.txt").read_text(encoding="utf-8")
    assert resultado["historico_de_versoes"] is TEM_GIT and (raiz / "versoes" / "finpro.bundle").exists() is TEM_GIT
    # manifesto com a impressão digital de cada arquivo
    manifesto = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))
    assert manifesto["versao"] == "Fin Pro v9.9.9"
    assert manifesto["totais"]["arquivos"] == len(manifesto["arquivos"]) == resultado["itens"]
    assert manifesto["arquivos"]["codigo/app/servico.py"]["sha256"] == backup._sha256(pasta / "app" / "servico.py")
    assert manifesto["totais"]["secoes"]["codigo"]["arquivos"] == 5
    # conferido sozinho depois do backup
    status = gerenciador.status()
    assert status["verificado"] is True and status["problemas"] == [] and status["com_codigo"]

    # o espelho do código acompanha: arquivo alterado é recopiado e arquivo apagado sai do backup
    (pasta / "app" / "servico.py").write_text("def soma(a, b):\n    return b + a  # mudou de verdade\n", encoding="utf-8")
    (pasta / "web" / "index.html").unlink()
    segundo = gerenciador.executar()
    assert (segundo["codigo_copiados"], segundo["codigo_removidos"], segundo["codigo_total"]) == (1, 1, 4)
    assert not (raiz / "codigo" / "web").exists()
    assert "mudou" in (raiz / "codigo" / "app" / "servico.py").read_text(encoding="utf-8")

    # dá para levar só os dados
    gerenciador.configurar(codigo=False)
    assert not gerenciador.status()["com_codigo"] and gerenciador.executar()["codigo_total"] == 0


def test_pacote_completo_em_zip_e_conferencia(sistema):
    gerenciador, pasta, raiz = sistema
    agora = datetime.now()
    assert gerenciador.pacote_devido(agora)  # nunca foi gerado
    pacote = gerenciador.gerar_pacote(agora)
    assert pacote["ok"] and pacote["arquivo"] == f"Fin Pro - backup completo {agora:%Y-%m-%d_%H%M}.zip"
    with zipfile.ZipFile(pacote["caminho"]) as arquivo:
        nomes = set(arquivo.namelist())
        assert arquivo.testzip() is None
    assert {"codigo/app/servico.py", "arquivos/a1.pdf", "configuracoes/diesel_bot.json", "configuracoes/.env", "manifesto.json",
            "LEIA-ME.txt", "RESTAURAR.bat", "restaurar_backup.py", f"planilha/boletos-{date.today():%Y-%m-%d}.db"} <= nomes
    assert ("versoes/finpro.bundle" in nomes) is TEM_GIT and not any(n.startswith("pacotes/") for n in nomes)
    assert not gerenciador.pacote_devido(agora) and gerenciador.pacote_devido(agora + timedelta(days=8))
    assert gerenciador.status()["ultimo_pacote"]["arquivo"] == pacote["arquivo"]

    # guarda só os N mais recentes; "nunca" desliga o pacote automático
    gerenciador.configurar(manter_pacotes=1)
    segundo = gerenciador.gerar_pacote(agora + timedelta(minutes=3))
    assert [p["arquivo"] for p in gerenciador.pacotes()] == [segundo["arquivo"]]
    gerenciador.configurar(pacote="nunca")
    assert not gerenciador.pacote_devido(agora + timedelta(days=90))
    with pytest.raises(ValueError):
        gerenciador.configurar(pacote="diario")

    # conferência completa: tudo certo…
    conferencia = gerenciador.verificar(completa=True)
    assert conferencia["ok"], conferencia
    assert {"Código-fonte", "Configurações", "Impressão digital dos arquivos"} <= {i["nome"] for i in conferencia["itens"]}
    # …até um comprovante ser trocado no backup por outro do mesmo tamanho (só a impressão digital percebe)
    alvo = raiz / "arquivos" / "a1.pdf"
    alvo.write_bytes(b"%PDF comprovante de pagament0")
    ruim = gerenciador.verificar(completa=True)
    assert not ruim["ok"] and [i["nome"] for i in ruim["itens"] if not i["ok"]] == ["Impressão digital dos arquivos"]
    assert gerenciador.status()["verificado"] is False and gerenciador.status()["problemas"]
    # …ou um banco de dados chegar corrompido
    (raiz / "planilha" / f"boletos-{date.today():%Y-%m-%d}.db").write_bytes(b"isto nao e um banco")
    assert any(i["nome"].startswith("Banco boletos") and not i["ok"] for i in gerenciador.verificar(completa=False)["itens"])
    # o backup seguinte recopia o que estava errado e a conferência volta a passar
    alvo.unlink()
    assert gerenciador.executar()["ok"]
    assert gerenciador.verificar(completa=True)["ok"]


def test_restaura_tudo_em_outro_computador(sistema, tmp_path):
    gerenciador, pasta, raiz = sistema
    pacote = gerenciador.gerar_pacote()
    restaurador = _restaurador()

    novo = tmp_path / "computador novo" / "Fin Pro"
    resumo = restaurador.restaurar_de(raiz, novo)
    assert resumo["codigo"] == 5 and resumo["arquivos"] == 1 and resumo["configuracoes"] >= 6
    assert (novo / "app" / "servico.py").read_text(encoding="utf-8") == (pasta / "app" / "servico.py").read_text(encoding="utf-8")
    assert (novo / "iniciar.bat").exists() and (novo / ".env").read_text(encoding="utf-8").startswith("LEITOR_SENHA_ACESSO")
    assert (novo / "dados" / "arquivos" / "a1.pdf").read_bytes() == b"%PDF comprovante de pagamento"
    assert json.loads((novo / "dados" / "diesel_bot.json").read_text(encoding="utf-8")) == {"de": "diesel_bot.json"}
    conexao = sqlite3.connect(novo / "dados" / "boletos.db")
    (registro,) = [json.loads(linha[0]) for linha in conexao.execute("SELECT dados FROM registros WHERE aba = 'boletos'")]
    conexao.close()
    assert registro["beneficiario"] == "Energisa" and registro["valor"] == 480.5
    if TEM_GIT:  # o histórico de versões volta junto, e o código restaurado bate com a última versão guardada
        def saida(*argumentos):
            return subprocess.run(["git", *argumentos], cwd=novo, capture_output=True, text=True, check=True).stdout

        assert "v9.9.9" in saida("tag")
        assert saida("status", "--porcelain", "--", "app/servico.py", "app/__init__.py", "web", "iniciar.bat") == ""
        assert not (novo / "versoes-do-backup").exists()

    # não apaga dados existentes por engano; com --forcar, guarda os de antes numa pasta à parte
    (novo / "dados" / "arquivos" / "novo-depois.pdf").write_bytes(b"lancado depois")
    with pytest.raises(restaurador.ErroRestauracao):
        restaurador.restaurar_de(raiz, novo)
    forcado = restaurador.restaurar_de(raiz, novo, forcar=True)
    assert (Path(forcado["dados_anteriores"]) / "arquivos" / "novo-depois.pdf").exists()
    assert not (novo / "dados" / "arquivos" / "novo-depois.pdf").exists() and (novo / "dados" / "boletos.db").exists()

    # a partir do pacote .zip dá o mesmo resultado; pasta que não é backup é recusada
    do_zip = tmp_path / "pelo zip"
    assert restaurador.main([pacote["caminho"], str(do_zip)]) == 0
    assert (do_zip / "app" / "servico.py").exists() and (do_zip / "dados" / "boletos.db").stat().st_size > 0
    assert restaurador.main([str(tmp_path / "computador novo"), str(tmp_path / "x")]) == 1
    assert restaurador.main([str(raiz)]) == 2  # faltou o destino: mostra a ajuda


def test_agendador_faz_o_backup_do_dia_e_o_pacote_da_semana(sistema):
    gerenciador, _, raiz = sistema
    gerenciador.rodar_agendado()  # primeiro dia: backup + pacote
    assert gerenciador.status()["situacao"] == "ok" and len(gerenciador.pacotes()) == 1
    gerenciador.rodar_agendado()  # mesmo dia: nada a fazer
    assert len(gerenciador.pacotes()) == 1
    ontem = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    gerenciador._estado.update(ultimo_sucesso=ontem, horario="00:00")
    gerenciador.rodar_agendado()  # dia seguinte: só o backup (o pacote é semanal)
    assert gerenciador.status()["dias_sem_backup"] == 0 and len(gerenciador.pacotes()) == 1


def test_api_do_pacote_e_da_conferencia(ambiente, monkeypatch, tmp_path):
    gerenciador, _, nuvem = ambiente
    monkeypatch.setattr(contexto, "backup", gerenciador)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        assert computador.post("/api/backup/pacote").status_code == 422  # backup ainda sem pasta
        computador.post("/api/admin/senha", json={"senha": "senha-adm", "confirmacao": "senha-adm"})
        ligado = computador.put("/api/backup/config", json={"pasta": str(nuvem), "ativo": True, "pacote": "mensal",
                                                            "manter_pacotes": 2})
        assert ligado.json()["pacote"] == "mensal" and ligado.json()["manter_pacotes"] == 2 and ligado.json()["pacotes"] == []
        assert computador.put("/api/backup/config", json={"pacote": "todo-dia"}).status_code == 422
        com_pacote = computador.post("/api/backup/pacote").json()
        assert len(com_pacote["pacotes"]) == 1 and com_pacote["pacotes"][0]["caminho"].endswith(".zip")
        conferido = computador.post("/api/backup/verificar").json()
        assert conferido["verificado"] is True and conferido["verificacao"]["completa"] is True
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        assert rede.post("/api/backup/pacote").status_code in (401, 403)
        assert rede.post("/api/backup/verificar").status_code in (401, 403)
        visto = rede.get("/api/backup").json()
        assert "caminho" not in json.dumps(visto.get("pacotes") or []) and "caminho" not in (visto.get("ultimo_pacote") or {})
```

## `tests/test_banco.py` (96 linhas)

```python
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
```

## `tests/test_bot.py` (90 linhas)

```python
"""Comandos do bot do Telegram (/vencidos, /hoje, /semana, /buscar, /previsao, /resumo)."""

from datetime import date, timedelta

import pytest

from app import bot, contexto, entrada
from app.banco import BancoBoletos
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.repositorio import RepositorioBoletos

HOJE = date(2026, 9, 17)


@pytest.fixture
def dados(tmp_path, monkeypatch):
    banco = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx")
    banco.migrar()
    fila = FilaGravacao(banco, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(banco, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(banco, fila, "pix"))
    banco.adicionar({"beneficiario": "CLA AUTO PECAS", "valor": 270.35, "vencimento": HOJE - timedelta(days=4),
                     "linha_digitavel": "34191.09123 34567.812341 56789.012301 2 15820000015000", "centro_custo": "Oficina"})
    banco.adicionar({"beneficiario": "Energisa", "valor": 487.32, "vencimento": HOJE})
    banco.adicionar({"beneficiario": "Aluguel", "valor": 2000, "vencimento": HOJE + timedelta(days=5)})
    banco.adicionar({"beneficiario": "Já pago", "valor": 50, "vencimento": HOJE - timedelta(days=1), "status": "Pago",
                     "data_pagamento": HOJE, "valor_pago": 55.0, "juros_multa": 5.0})
    banco.adicionar({"recebedor": "Magno Alves", "tipo_chave": "email", "chave": "magno@email.com", "valor": 1600,
                     "vencimento": HOJE - timedelta(days=1)}, "pix")
    return banco


def test_comandos_listam_com_linha_digitavel_e_pix_copia_e_cola(dados):
    vencidos = "\n".join(bot.responder("/vencidos", hoje=HOJE))
    assert "Em atraso</b> — 2 lançamento(s), R$ 1.870,35" in vencidos
    # só os números: tocar no <code> copia a linha pronta para colar no banco (sem pontos nem espaços)
    assert "<code>34191091233456781234156789012301215820000015000</code>" in vencidos
    assert "4 dias de atraso" in vencidos and "Magno Alves" in vencidos and "Copia e Cola: <code>000201" in vencidos
    assert "Já pago" not in vencidos

    assert "Energisa" in bot.responder("/hoje@boletos_bot", hoje=HOJE)[0]
    semana = bot.responder("/semana", hoje=HOJE)[0]
    assert "Energisa" in semana and "Aluguel" in semana and "CLA" not in semana
    assert "CLA AUTO PECAS" in bot.responder("/buscar cla auto", hoje=HOJE)[0]
    assert "Nenhum boleto" in bot.responder("/buscar inexistente", hoje=HOJE)[0]

    previsao = bot.responder("/previsao", hoje=HOJE)[0]
    assert "Em atraso: R$ 1.870,35 (2)" in previsao and "Próximos 7 dias: <b>R$ 2.487,32</b>" in previsao
    resumo = bot.responder("/resumo", hoje=HOJE)[0]
    assert "Pago neste mês: <b>R$ 55,00</b> (1) · juros/multas R$ 5,00" in resumo
    assert "/vencidos" in bot.responder("/start", "Almir", hoje=HOJE)[0]
    assert "Não conheço" in bot.responder("/xyz", hoje=HOJE)[0]
    assert bot.responder("bom dia", hoje=HOJE) is None


def test_listas_grandes_sao_divididas(dados):
    for n in range(60):
        dados.adicionar({"beneficiario": f"Fornecedor {n} " + "X" * 40, "valor": 10, "vencimento": HOJE - timedelta(days=2),
                         "linha_digitavel": "34191.09123 34567.812341 56789.012301 2 15820000015000"})
    mensagens = bot.responder("/vencidos", hoje=HOJE)
    assert len(mensagens) > 1 and all(len(m) <= 4096 for m in mensagens)
    assert "… e mais" in mensagens[-1]


def test_bot_responde_so_para_cadastrados(tmp_path, monkeypatch, dados):
    enviados, chamadas = [], []
    atualizacoes = [
        {"update_id": 1, "message": {"chat": {"id": 42, "type": "private"}, "from": {"first_name": "Almir"}, "text": "/vencidos"}},
        {"update_id": 2, "message": {"chat": {"id": 99, "type": "private"}, "from": {"first_name": "Estranho"}, "text": "/vencidos"}},
    ]

    def telegram_falso(token, metodo, dados_pedido=None):
        chamadas.append(metodo)
        if metodo == "getUpdates":
            return atualizacoes if not (dados_pedido or {}).get("offset") else []
        if metodo == "sendMessage":
            enviados.append((dados_pedido["chat_id"], dados_pedido["text"]))
        return {}

    monkeypatch.setattr(canais, "_telegram", telegram_falso)
    monkeypatch.setattr(canais, "enviar_telegram", lambda token, chat_id, texto: enviados.append((chat_id, texto)))
    caixa = entrada.CaixaEntrada(tmp_path / "entrada.json", lambda d, n: {}, lambda d, n: {}, lambda: ("123:abc", [{"chat_id": "42", "nome": "Almir"}]),
                                 comandos=bot)
    caixa.verificar_telegram()
    caixa.verificar_telegram()
    assert chamadas.count("setMyCommands") == 1
    assert any(chat == "42" and "Em atraso" in texto for chat, texto in enviados)
    assert any(chat == "99" and "peça ao responsável" in texto for chat, texto in enviados)
    assert not any(chat == "99" and "CLA" in texto for chat, texto in enviados)
```

## `tests/test_busca_comprovantes.py` (140 linhas)

```python
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
```

## `tests/test_caixa.py` (333 linhas)

```python
"""Caixa: entradas e saídas em dinheiro, períodos, relatórios, leitura do cupom, bot do caixa e aba Gastos."""

from datetime import date

import pytest

from app import contexto, servicos
from app.banco import BancoBoletos
from app.caixa import leitura, servico
from app.caixa.bot import BotCaixa
from app.fila_gravacao import FilaGravacao
from app.repositorio import RepositorioBoletos

CUPOM = """POSTO SAO JORGE LTDA
CNPJ: 12.345.678/0001-95 IE: 123456789
AV BRASIL, 100 - MIRASSOL SP
DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETRONICA
001 GASOLINA COMUM 30,000 L 5,99 179,70
Qtde. total de itens 1
Valor total R$ 179,70
Desconto R$ 0,00
Valor a Pagar R$ 179,70
FORMA DE PAGAMENTO VALOR PAGO
Dinheiro 200,00
Troco R$ 20,30
Valor aprox. dos tributos R$ 45,00 (Lei 12.741)
Emissao: 21/09/2026 14:35:10
"""


@pytest.fixture(autouse=True)
def banco(tmp_path, monkeypatch):
    planilha = BancoBoletos(tmp_path / "boletos.db", tmp_path / "boletos.xlsx", tmp_path / "backups")
    planilha.garantir()
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "repositorio_caixa", RepositorioBoletos(planilha, fila, "caixa"))
    yield planilha
    planilha.parar()


def _saida(valor, dia, centro="Combustível e Veículos", local="Posto São Jorge", pessoa="Almir", descricao="gasolina"):
    return servico.lancar({"movimento": "Saída", "valor": valor, "data": dia, "centro_custo": centro, "local": local,
                           "pessoa": pessoa, "descricao": descricao}, "Fábio")


def _entrada(valor, dia, descricao="Pedido 7043 - brita"):
    return servico.lancar({"movimento": "Entrada", "valor": valor, "data": dia, "descricao": descricao}, "Fábio")


# --------------------------------------------------------------------------- períodos


def test_periodos_dia_semana_mes_e_ano():
    ref = date(2026, 9, 22)  # terça-feira
    assert servico.periodo("dia", ref)[:2] == (ref, ref)
    assert servico.periodo("semana", ref)[:2] == (date(2026, 9, 21), date(2026, 9, 27))
    assert servico.periodo("mes", ref)[:2] == (date(2026, 9, 1), date(2026, 9, 30))
    assert servico.periodo("ano", ref)[:2] == (date(2026, 1, 1), date(2026, 12, 31))
    assert servico.periodo("mes", date(2026, 12, 5))[1] == date(2026, 12, 31)
    assert servico.deslocar("mes", date(2026, 1, 15), -1) == date(2025, 12, 1)
    assert servico.deslocar("semana", ref, 1) == date(2026, 9, 29)
    with pytest.raises(servico.ErroCaixa):
        servico.periodo("hora", ref)


# --------------------------------------------------------------------------- lançamentos e resumo


def test_lanca_entrada_e_saida_e_valida():
    entrada = _entrada(500, date(2026, 9, 21))
    assert entrada["movimento"] == "Entrada" and entrada["status"] == "Confirmado" and entrada["lancado_por"] == "Fábio"
    saida = servico.lancar({"movimento": "saida", "valor": "45.9", "data": "2026-09-21"}, "Almir")
    assert saida["movimento"] == "Saída" and saida["valor"] == 45.9
    with pytest.raises(servico.ErroCaixa):
        servico.lancar({"movimento": "Entrada", "valor": 0})
    with pytest.raises(servico.ErroCaixa):
        servico.lancar({"movimento": "Talvez", "valor": 10})


def test_resumo_do_periodo_com_saldo_e_onde_mais_se_gastou():
    _entrada(1000, date(2026, 8, 30))  # mês anterior: vira saldo inicial
    _entrada(500, date(2026, 9, 10))
    _entrada(300, date(2026, 9, 15), "Pedido 7120 - pedrisco")
    _saida(179.70, date(2026, 9, 21))
    _saida(120.30, date(2026, 9, 22), centro="Obras", local="Loja do Zé", pessoa="Bia", descricao="cimento")
    _saida(50, date(2026, 9, 22), local="Posto São Jorge")
    cancelada = _saida(999, date(2026, 9, 22))
    servico.cancelar(cancelada["id"], "Fábio")

    r = servico.resumo("mes", date(2026, 9, 22))
    assert r["periodo"]["rotulo"] == "setembro de 2026"
    assert r["entradas"] == {"total": 800.0, "quantidade": 2, "media": 400.0,
                             "maior": {"valor": 500.0, "descricao": "Pedido 7043 - brita", "data": date(2026, 9, 10)}}
    assert r["saidas"]["total"] == 350.0 and r["saidas"]["quantidade"] == 3  # a cancelada não conta
    assert r["saldo_periodo"] == 450.0
    assert r["saldo_inicial"] == 1000.0 and r["saldo_caixa"] == 1450.0
    assert [(c["nome"], c["total"]) for c in r["por_centro"]] == [("Combustível e Veículos", 229.7), ("Obras", 120.3)]
    assert r["por_local"][0] == {"nome": "Posto São Jorge", "total": 229.7, "quantidade": 2, "percentual": 65.6}
    assert {p["nome"] for p in r["por_pessoa"]} == {"Almir", "Bia"}
    assert len(r["serie"]) == 30 and next(s for s in r["serie"] if s["rotulo"] == "22/09")["saidas"] == 170.3


def test_filtro_por_dia_semana_e_ano():
    _saida(10, date(2026, 9, 20))  # domingo, semana anterior
    _saida(20, date(2026, 9, 21))
    _saida(30, date(2026, 9, 22))
    assert servico.resumo("dia", date(2026, 9, 22))["saidas"]["total"] == 30
    assert servico.resumo("semana", date(2026, 9, 22))["saidas"]["total"] == 50
    ano = servico.resumo("ano", date(2026, 9, 22))
    assert ano["saidas"]["total"] == 60 and len(ano["serie"]) == 12


# --------------------------------------------------------------------------- aba Gastos


def test_gastos_em_dinheiro_entram_na_analise_de_gastos():
    _saida(179.70, date(2026, 9, 21))
    _entrada(500, date(2026, 9, 21))  # entrada não é gasto
    analise = servicos.analise_gastos([], [], servico.saidas_para_gastos(), de=date(2026, 9, 1), ate=date(2026, 9, 30))
    assert analise["total"] == 179.7 and analise["total_dinheiro"] == 179.7
    assert analise["centros"][0]["centro"] == "Combustível e Veículos" and analise["centros"][0]["dinheiro"] == 179.7
    assert analise["maiores"][0]["nome"] == "Posto São Jorge"
    so_boletos = servicos.analise_gastos([], [], servico.saidas_para_gastos(), tipo="boleto")
    assert so_boletos["total"] == 0


def test_gastos_em_dinheiro_entram_no_fechamento_do_mes():
    from app import fechamento

    _saida(179.70, date(2026, 9, 21))
    f = fechamento.montar([], [], date(2026, 9, 1), caixa=servico.saidas_para_gastos())
    assert f["totais"]["pago"] == 179.7 and f["totais"]["dinheiro"] == 1
    assert f["pagos"][0]["tipo"] == "Dinheiro" and f["pagos"][0]["nome"] == "Posto São Jorge"


# --------------------------------------------------------------------------- leitura do cupom


def test_le_o_valor_a_pagar_e_nao_o_troco():
    lido = leitura.analisar_texto(CUPOM, hoje=date(2026, 9, 22))
    assert lido["valor"] == 179.70  # não 200,00 (dinheiro entregue) nem 20,30 (troco)
    assert lido["data"] == date(2026, 9, 21) and lido["hora"] == "14:35"
    assert lido["local"] == "POSTO SAO JORGE LTDA" and lido["cnpj"] == "12345678000195"


def test_recibo_simples_sem_rotulo():
    assert leitura.valor_total("Recibo\nRecebi de Prospera a quantia de R$ 85,00\nreferente a frete") == 85.0
    assert leitura.valor_total("sem valor nenhum") is None


# --------------------------------------------------------------------------- bot do caixa


class Telegram:
    """Telegram de mentira: guarda o que o bot mandou e entrega as mensagens que o teste quiser."""

    def __init__(self):
        self.enviadas = []
        self.fila = []

    def __call__(self, token, metodo, dados=None):
        if metodo == "getUpdates":
            fila, self.fila = self.fila, []
            return fila
        if metodo == "sendMessage":
            self.enviadas.append(dados)
        return {}

    def ultima(self):
        return self.enviadas[-1]

    def botoes(self):
        teclado = (self.ultima().get("reply_markup") or {}).get("inline_keyboard") or []
        return [b for linha in teclado for b in linha]


@pytest.fixture
def bot(tmp_path, monkeypatch):
    telegram = Telegram()
    monkeypatch.setattr("app.notificacoes.canais._telegram", telegram)
    monkeypatch.setattr("app.notificacoes.canais.baixar_arquivo_telegram", lambda token, file_id: f"foto {file_id}".encode())
    centros = ["Administrativo", "Combustível e Veículos", "Obras"]

    def criar_centro(nome, usuario):
        centros.append(nome)
        return nome

    caixa = BotCaixa(tmp_path / "caixa_bot.json",
                     lambda dados, nome: {"id": "a1", "nome": nome, "caminho": "arquivos/a1.jpg"},
                     lambda: {"111": "Almir", "222": "Fábio"},  # vindos dos bots de boletos e de notas
                     lambda: list(centros), criar_centro,
                     ler=lambda dados, nome: leitura.analisar_texto(CUPOM, hoje=date(2026, 9, 22)))
    caixa.configurar({"token": "123:abc", "ativo": True})
    caixa.telegram = telegram
    caixa.lista_centros = centros
    return caixa


def _foto(chat="111", arquivo="f1"):
    return {"update_id": 1, "message": {"chat": {"id": int(chat)}, "from": {"first_name": "Almir"},
                                        "photo": [{"file_id": arquivo, "file_size": 1000}]}}


def _texto(texto, chat="111"):
    return {"update_id": 2, "message": {"chat": {"id": int(chat)}, "from": {"first_name": "Almir"}, "text": texto}}


def _clique(dado, chat="111"):
    return {"update_id": 3, "callback_query": {"id": "cb", "data": dado,
                                               "message": {"message_id": 9, "chat": {"id": int(chat)}}}}


def _receber(bot, *atualizacoes):
    bot.telegram.fila = list(atualizacoes)
    bot.verificar()


def test_foto_do_cupom_vira_conversa_e_fica_pronta_para_revisar(bot):
    _receber(bot, _foto())
    pergunta = bot.telegram.ultima()["text"]
    assert "R$ 179,70" in pergunta and "Onde foi gasto?" in pergunta

    _receber(bot, _texto("gasolina da caminhonete"))
    assert "Qual o centro de custo?" in bot.telegram.ultima()["text"]
    botoes = bot.telegram.botoes()
    assert [b["text"] for b in botoes] == ["Administrativo", "Combustível e Veículos", "Obras",
                                            "➕ Cadastrar um novo centro de custo"]

    _receber(bot, _clique("cc:1"))
    assert "Anotado" in bot.telegram.ultima()["text"]
    item = bot.listar()[0]
    assert item["estado"] == "pendente" and bot.contagem() == 1
    assert item["dados"] == {"movimento": "Saída", "valor": 179.7, "data": "2026-09-21", "hora": "14:35",
                             "descricao": "gasolina da caminhonete", "local": "POSTO SAO JORGE LTDA",
                             "centro_custo": "Combustível e Veículos", "pessoa": "Almir"}


def test_revisar_na_tela_lanca_no_caixa_com_o_comprovante(bot):
    _receber(bot, _foto(), _texto("gasolina"), _clique("cc:1"))
    item = bot.listar()[0]
    lancado = bot.confirmar(item["id"], {"valor": 180.0}, "Fábio")  # ajustou o valor na revisão
    assert lancado["estado"] == "lancado" and bot.contagem() == 0
    registro = contexto.repositorio_caixa.listar()[0]
    assert registro["valor"] == 180.0 and registro["movimento"] == "Saída"
    assert registro["centro_custo"] == "Combustível e Veículos" and registro["arquivo"] == "arquivos/a1.jpg"
    assert registro["lancado_por"] == "Fábio"


def test_cadastrar_um_centro_de_custo_novo_pelo_bot(bot):
    _receber(bot, _foto(), _texto("peças do trator"), _clique("cc:novo"))
    assert "nome do novo centro" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("Manutenção de máquinas"))
    assert "Manutenção de máquinas" in bot.lista_centros
    assert bot.listar()[0]["dados"]["centro_custo"] == "Manutenção de máquinas"


def test_digitar_o_nome_do_centro_tambem_funciona(bot):
    _receber(bot, _foto(), _texto("cimento"), _texto("obras"))
    assert bot.listar()[0]["dados"]["centro_custo"] == "Obras"

    _receber(bot, _foto(arquivo="f2"), _texto("lanche"), _texto("Cozinha"))
    assert "Não achei" in bot.telegram.ultima()["text"]
    _receber(bot, _clique("cc:criar"))
    assert "Cozinha" in bot.lista_centros and bot.contagem() == 2


def test_pergunta_o_valor_quando_nao_consegue_ler(bot):
    bot.ler = lambda dados, nome: {"valor": None, "local": ""}
    _receber(bot, _foto())
    assert "Qual foi o valor?" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("quarenta"))
    assert "Não entendi o valor" in bot.telegram.ultima()["text"]
    _receber(bot, _texto("45,90"))
    assert "Onde foi gasto?" in bot.telegram.ultima()["text"]
    assert bot.listar()[0]["dados"]["valor"] == 45.9


def test_quem_nao_esta_nos_outros_bots_e_recusado(bot):
    _receber(bot, _foto(chat="999"))
    assert "Só usa quem já está cadastrado" in bot.telegram.ultima()["text"]
    assert bot.listar() == []


def test_cancelar_desiste_do_gasto(bot):
    _receber(bot, _foto(), _texto("/cancelar"))
    assert "cancelei" in bot.telegram.ultima()["text"]
    assert bot.listar() == []


def test_a_mesma_foto_nao_entra_duas_vezes(bot):
    _receber(bot, _foto())
    _receber(bot, _foto())
    assert "já tinha sido enviado" in bot.telegram.ultima()["text"]
    assert len(bot.listar()) == 1


# --------------------------------------------------------------------------- API


def test_api_do_caixa_e_gastos_em_dinheiro():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        criada = cliente.post("/api/caixa", json={"movimento": "Saída", "valor": 179.70, "data": "2026-09-21",
                                                  "descricao": "gasolina", "local": "Posto São Jorge",
                                                  "centro_custo": "Combustível e Veículos"})
        assert criada.status_code == 201, criada.text
        cliente.post("/api/caixa", json={"movimento": "Entrada", "valor": 500, "data": "2026-09-21",
                                         "descricao": "Pedido 7043"})
        assert cliente.post("/api/caixa", json={"movimento": "Entrada", "valor": 0}).status_code == 422

        resumo = cliente.get("/api/caixa?periodo=semana&data=2026-09-22").json()
        assert resumo["entradas"]["total"] == 500 and resumo["saidas"]["total"] == 179.7
        assert resumo["periodo"]["inicio"] == "2026-09-21" and resumo["saldo_periodo"] == 320.3

        excel = cliente.get("/api/caixa/relatorio/arquivo?periodo=mes&data=2026-09-22")
        assert excel.status_code == 200 and excel.content[:2] == b"PK"

        gastos = cliente.get("/api/gastos?tipo=dinheiro").json()
        assert gastos["total_dinheiro"] == 179.7 and gastos["total"] == 179.7
        centros = {c["nome"]: c for c in cliente.get("/api/centros").json()["centros"]}
        assert centros["Combustível e Veículos"]["dinheiro"] == 1

        id_ = criada.json()["id"]
        assert cliente.post(f"/api/caixa/{id_}/cancelar").json()["status"] == "Cancelado"
        assert cliente.get("/api/caixa?periodo=semana&data=2026-09-22").json()["saidas"]["total"] == 0
        assert cliente.get(f"/api/caixa/{id_}/historico").json()["eventos"][0]["acao"] == "Cancelamento"
```

## `tests/test_codigo.py` (108 linhas)

```python
from datetime import date
from decimal import Decimal

from app.boleto.codigo import (
    ARRECADACAO,
    BANCARIO,
    _dv_arrecadacao,
    analisar,
    barras_para_linha_arrecadacao,
    barras_para_linha_bancario,
    candidatos_correcao,
    data_por_fator,
    fator_por_data,
    formatar_linha,
    linha_para_barras_bancario,
    tentar_corrigir,
)

# Exemplo público de boleto do Banco do Brasil (R$ 1,00, vencimento 31/12/2007)
LINHA_BB = "00190500954014481606906809350314337370000000100"


def test_boleto_bancario_real_valido():
    r = analisar(LINHA_BB, referencia=date(2008, 1, 1))
    assert r.valido and r.erros == []
    assert r.tipo == BANCARIO
    assert r.banco_nome == "Banco do Brasil"
    assert r.valor == Decimal("1.00")
    assert r.vencimento == date(2007, 12, 31)
    assert len(r.codigo_barras) == 44


def test_conversao_linha_barras_ida_e_volta():
    barras = linha_para_barras_bancario(LINHA_BB)
    assert barras_para_linha_bancario(barras) == LINHA_BB
    assert analisar(barras, referencia=date(2008, 1, 1)).linha_digitavel == LINHA_BB


def test_detecta_digito_verificador_invalido():
    errada = LINHA_BB[:9] + str((int(LINHA_BB[9]) + 1) % 10) + LINHA_BB[10:]
    r = analisar(errada)
    assert not r.valido
    assert any("campo 1" in e for e in r.erros)


def test_correcao_de_um_digito():
    errada = LINHA_BB[:12] + str((int(LINHA_BB[12]) + 4) % 10) + LINHA_BB[13:]
    candidatos = candidatos_correcao(errada, date(2008, 1, 1), limite=20)
    assert LINHA_BB in [c.linha_digitavel for c in candidatos]
    assert all(c.valido and c.corrigido for c in candidatos)
    corrigido = tentar_corrigir(errada, date(2008, 1, 1))
    assert corrigido is None or corrigido.linha_digitavel == LINHA_BB


def test_correcao_de_dois_digitos_em_campos_diferentes():
    errada = list(LINHA_BB)
    errada[3] = str((int(errada[3]) + 5) % 10)   # campo 1
    errada[14] = str((int(errada[14]) + 3) % 10)  # campo 2
    candidatos = candidatos_correcao("".join(errada), date(2008, 1, 1), limite=50)
    assert LINHA_BB in [c.linha_digitavel for c in candidatos]


def test_correcao_prioriza_confusoes_tipicas_de_ocr():
    # 8 lido como 3 no campo 3: a correção 3→8 deve aparecer entre as primeiras
    pos = 23
    assert LINHA_BB[pos] == "8"
    errada = LINHA_BB[:pos] + "3" + LINHA_BB[pos + 1:]
    candidatos = candidatos_correcao(errada, date(2008, 1, 1), limite=50)
    linhas = [c.linha_digitavel for c in candidatos]
    assert LINHA_BB in linhas[:3]


def test_fator_de_vencimento_novo_ciclo():
    assert data_por_fator(9999, date(2025, 1, 1)) == date(2025, 2, 21)
    assert data_por_fator(1000, date(2026, 9, 14)) == date(2025, 2, 22)
    assert data_por_fator(1000, date(2001, 1, 1)) == date(2000, 7, 3)
    for d in (date(2024, 5, 10), date(2025, 2, 22), date(2027, 1, 31)):
        assert data_por_fator(fator_por_data(d), d) == d


def _barras_arrecadacao(identificador: str) -> str:
    sem_dv = "8" + "3" + identificador + "00000012345" + "0048" + "0" * 7 + "20261015" + "1234567890"
    assert len(sem_dv) == 43
    dv = _dv_arrecadacao(sem_dv, identificador)
    return sem_dv[:3] + str(dv) + sem_dv[3:]


def test_arrecadacao_modulo_10_e_11():
    for identificador in ("6", "8"):
        barras = _barras_arrecadacao(identificador)
        linha = barras_para_linha_arrecadacao(barras)
        r = analisar(linha, referencia=date(2026, 9, 1))
        assert r.valido, r.erros
        assert r.tipo == ARRECADACAO
        assert r.segmento == "Energia elétrica e gás"
        assert r.valor == Decimal("123.45")
        assert r.vencimento == date(2026, 10, 15) and r.vencimento_estimado
        assert analisar(barras).linha_digitavel == linha


def test_formatacao():
    assert formatar_linha(LINHA_BB) == "00190.50095 40144.816069 06809.350314 3 37370000000100"
    linha48 = barras_para_linha_arrecadacao(_barras_arrecadacao("6"))
    assert formatar_linha(linha48).count("-") == 4


def test_tamanho_invalido():
    assert analisar("123") is None
```

## `tests/test_comprovante.py` (212 linhas)

```python
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
```

## `tests/test_corpus.py` (99 linhas)

```python
"""Regressão sobre o corpus variado: PDFs de layouts diferentes, guias, carnê, scan e fotos de papel."""

from decimal import Decimal
from pathlib import Path

import pytest

import corpus as C
from app.boleto.codigo import formatar_linha
from app.boleto.extrator import ler_arquivo
from app.boleto.texto import normalizar


@pytest.fixture(scope="module")
def pasta(tmp_path_factory):
    return tmp_path_factory.mktemp("corpus")


def _ler(caminho: Path) -> list[dict]:
    resultado = ler_arquivo(caminho.read_bytes())
    return [{k: v["valor"] for k, v in b["campos"].items()} | {"_boleto": b} for b in resultado["boletos"]]


def _confere_codigo(campos: dict, esperado: dict):
    assert campos["linha_digitavel"] == formatar_linha(esperado["linha"])
    assert campos["vencimento"] == esperado["vencimento"].isoformat()
    assert Decimal(str(campos["valor"])) == esperado["valor"]


def test_bancario_com_rotulos_na_mesma_linha(pasta):
    esperado = C.bancario_rotulos_inline(pasta / "inline.pdf")
    (campos,) = _ler(pasta / "inline.pdf")
    _confere_codigo(campos, esperado)
    assert campos["beneficiario"] == esperado["beneficiario"]
    assert campos["documento_beneficiario"] == esperado["cnpj"]
    assert campos["numero_documento"] == esperado["documento"]


def test_conta_de_consumo_sem_rotulo_beneficiario(pasta):
    esperado = C.conta_de_energia(pasta / "energia.pdf")
    (campos,) = _ler(pasta / "energia.pdf")
    _confere_codigo(campos, esperado)
    assert esperado["beneficiario_contem"] in campos["beneficiario"]
    assert campos["documento_beneficiario"] == "07.047.251/0001-70"
    assert "004.512.887" in campos["numero_documento"]


def test_guia_das_beneficiario_e_orgao_arrecadador(pasta):
    esperado = C.guia_das(pasta / "das.pdf")
    (campos,) = _ler(pasta / "das.pdf")
    _confere_codigo(campos, esperado)
    assert "Simples Nacional" in campos["beneficiario"]
    assert "documento_beneficiario" not in campos  # o CNPJ impresso é do contribuinte
    assert campos["numero_documento"] == esperado["documento"]


def test_carne_com_tres_boletos_na_pagina(pasta):
    esperados = C.carne_tres_boletos(pasta / "carne.pdf")
    lidos = _ler(pasta / "carne.pdf")
    assert len(lidos) == 3
    for campos, esperado in zip(lidos, esperados):
        _confere_codigo(campos, esperado)
        assert campos["numero_documento"] == esperado["documento"]
        assert campos["beneficiario"] == esperado["beneficiario"]


def test_pdf_escaneado_sem_texto(pasta):
    esperado = C.bancario_rotulos_inline(pasta / "base_scan.pdf")
    C.pdf_escaneado(pasta / "base_scan.pdf", pasta / "escaneado.pdf")
    (campos,) = _ler(pasta / "escaneado.pdf")
    _confere_codigo(campos, esperado)
    assert "sorriso feliz" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == esperado["documento"]


def test_pdf_escaneado_deitado(pasta, boleto_pdf):
    """Caso real: folha escaneada girada 90° dentro da página do PDF."""
    origem, linha = boleto_pdf
    C.pdf_escaneado(origem, pasta / "deitado.pdf", rotacao=90)
    (campos,) = _ler(pasta / "deitado.pdf")
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert "exemplo de servicos" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == "NF-2026/0457"


def test_foto_de_papel_com_perspectiva(pasta, boleto_pdf):
    origem, linha = boleto_pdf
    C.foto_de_papel(origem, pasta / "foto.jpg")
    (campos,) = _ler(pasta / "foto.jpg")
    assert campos["linha_digitavel"] == formatar_linha(linha)
    assert "exemplo de servicos" in normalizar(campos["beneficiario"])
    assert campos["numero_documento"] == "NF-2026/0457"


def test_foto_de_conta_de_consumo(pasta):
    esperado = C.conta_de_energia(pasta / "energia2.pdf")
    C.foto_de_papel(pasta / "energia2.pdf", pasta / "foto_energia.jpg", angulo=-8)
    (campos,) = _ler(pasta / "foto_energia.jpg")
    _confere_codigo(campos, esperado)
```

## `tests/test_demonstracao.py` (88 linhas)

```python
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
```

## `tests/test_deposito_cheque.py` (97 linhas)

```python
"""Comprovante de depósito de cheque (banco): não é a foto do cheque — acha o cheque pela CMC-7 e dá a baixa."""

from datetime import date

import pytest

from app import contexto
from app.empresas import leitura, servico
from test_empresas_bot import _pdf, banco_limpo, caixa  # noqa: F401 - fixtures

# OCR real do comprovante do Bradesco (foto tirada deitada, lida girando): depósito do cheque 616 da Jose Pazete
DEPOSITO_BRADESCO = """237 Agencia: 1454 Maquina: 57699 09303 4.287,60 (*) Prazo maximo de bloqueio, contado em dias
Deposito em Conta-Corrente em Cheque(s) Quantidade de cheques depositados: CMC-7 74880585 0180006165 400000989483 Titular: PROSPERA IND.COMERCIO E SERVICOS Sujeito a conferencia.
bradesco Favorecido: Banco: 237 Conta: 0013669-7 Valor do deposito: Um dia util.
Banco: 237 Agencia: 1454 Maquina: 57699
Data: 24/09/2026 Hora: 16:24 N.Trans: 09303
Valor do deposito: 4.287,60
Quantidade de cheques depositados: 01
CMC-7 74880585 0180006165 400000989483
Titular: PROSPERA IND.COMERCIO E SERVICOS
"""


def test_cmc7_nas_posicoes_certas():
    lido = leitura.ler_cmc7("CMC-7 74880585 0180006165 400000989483")
    assert lido["banco"] == "Sicredi" and lido["agencia"] == "8058"
    assert lido["numero"] == "616" and lido["conta"] == "98948"  # não "180006" / "4000009894"


def test_comprovante_de_deposito_nao_e_cheque():
    assert leitura.classificar(DEPOSITO_BRADESCO) == "comprovante"
    dados = leitura.extrair_comprovante(DEPOSITO_BRADESCO)
    assert dados["deposito_cheque"] and dados["forma"] == "Cheque"
    assert [c["numero"] for c in dados["cheques"]] == ["616"]
    assert dados["valor"] == 4287.60 and dados["data"] == date(2026, 9, 24) and dados["hora"] == "16:24"
    assert dados["id_transacao"] == "09303"


@pytest.fixture
def pazete():
    empresa = servico.salvar_empresa({"nome": "Jose Pazete Ltda (Imapal)", "cnpj": "39.285.595/0001-04"}, "Fábio")
    servico.lancar_notas(empresa["nome"], [{"data": date(2026, 9, 10), "material": "Brita 01", "unidade": "M³",
                                            "quantidade": 27, "valor_unitario": 158.80, "numero_nf": "7100",
                                            "pedido": "7200"}], "Fábio")
    cheques = {}
    for numero, bom_para in (("616", date(2026, 9, 24)), ("617", date(2026, 9, 30))):
        cheques[numero] = servico.lancar_cheque({"empresa": empresa["nome"], "numero": numero, "vencimento": bom_para,
                                                 "valor": 4287.60, "banco": "Sicredi", "pedidos": "7200"}, "Fábio")
    return cheques


def test_bot_da_baixa_no_cheque_depositado(caixa, pazete, monkeypatch):  # noqa: F811
    monkeypatch.setattr("app.empresas.leitura.texto_do_arquivo", lambda *a, **k: DEPOSITO_BRADESCO)
    item = caixa.receber(_pdf("comprovante"), "foto-20260924-162601.jpg")

    assert item["tipo"] == "comprovante" and item["estado"] == "lancado"
    assert "cheque nº 616" in item["resumo"] and "compensado em 24/09/2026" in item["resumo"]
    cheques = {c["numero"]: c for c in contexto.empresas.listar("cheques")}
    assert cheques["616"]["status"] == "Compensado" and cheques["616"]["data_deposito"] == date(2026, 9, 24)
    assert cheques["617"]["status"] == "Em carteira"  # o outro cheque de mesmo valor não é tocado
    assert len(cheques) == 2  # nenhum cheque novo foi criado nem excluído
    recebimento = contexto.empresas.listar("recebimentos")[0]
    assert recebimento["forma"] == "Cheque" and recebimento["cheque_id"] == pazete["616"]["id"]
    assert recebimento["arquivo"]  # o comprovante fica guardado no recebimento
    assert contexto.empresas.listar("notas")[0]["status"] == "Recebido"


def test_cheque_nao_encontrado_fica_para_conferir(caixa, pazete, monkeypatch):  # noqa: F811
    outro = DEPOSITO_BRADESCO.replace("0180006165", "0180009995")  # cheque 999: não está em carteira
    monkeypatch.setattr("app.empresas.leitura.texto_do_arquivo", lambda *a, **k: outro)
    item = caixa.receber(_pdf("comprovante"), "deposito.jpg")

    assert item["estado"] == "pendente" and "nº 999" in item["resumo"]
    assert {c["status"] for c in contexto.empresas.listar("cheques")} == {"Em carteira"}

    # na conferência, alguém escolhe o cheque certo: ele é compensado com este comprovante
    caixa.confirmar(item["id"], "comprovante", {"cheque_id": pazete["617"]["id"], "data": "2026-09-24",
                                               "valor": 4287.60}, "Fábio")
    cheque = contexto.empresas.obter(pazete["617"]["id"], "cheques")
    assert cheque["status"] == "Compensado" and cheque["data_deposito"] == date(2026, 9, 24)
    assert contexto.empresas.listar("recebimentos")[0]["arquivo"]


def test_depositei_pela_tela_com_comprovante(pazete):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        enviado = cliente.post("/api/empresas/arquivo", files={"arquivo": ("deposito.pdf", _pdf("deposito"), "application/pdf")})
        assert enviado.status_code == 201
        resposta = cliente.post("/api/recebimentos", json={"valor": 4287.60, "data": "2026-09-24", "forma": "Cheque",
                                                           "cheque_id": pazete["616"]["id"], "arquivo_id": enviado.json()["id"]})
        assert resposta.status_code == 201, resposta.text
    cheque = contexto.empresas.obter(pazete["616"]["id"], "cheques")
    assert cheque["status"] == "Compensado"
    assert contexto.empresas.listar("recebimentos")[0]["arquivo"].endswith(".pdf")
```

## `tests/test_desktop_cache.py` (35 linhas)

```python
"""Depois de uma atualização, a janela do aplicativo não pode continuar mostrando telas antigas do cache."""

import os
import time

from app import desktop


def test_limpa_cache_da_janela_somente_quando_as_telas_mudam(tmp_path, monkeypatch):
    web = tmp_path / "web"
    (web / "js").mkdir(parents=True)
    tela = web / "js" / "configuracoes.js"
    tela.write_text("// versão antiga", encoding="utf-8")
    monkeypatch.setattr(desktop.config, "WEB_DIR", web)

    pasta = tmp_path / "webview"
    cache = pasta / "EBWebView" / "Default" / "Cache" / "Cache_Data"
    preferencias = pasta / "EBWebView" / "Default" / "Local Storage"
    cache.mkdir(parents=True)
    preferencias.mkdir(parents=True)
    (cache / "f_000007").write_text("configuracoes.js antigo", encoding="utf-8")

    assert desktop.limpar_cache_se_atualizado(pasta)  # primeira abertura com a marca de versão: limpa
    assert not cache.exists() and preferencias.exists()  # tema e preferências continuam

    cache.mkdir(parents=True)
    (cache / "f_000001").write_text("cache novo", encoding="utf-8")
    assert not desktop.limpar_cache_se_atualizado(pasta)  # nada mudou: mantém o cache
    assert (cache / "f_000001").exists()

    tela.write_text("// versão nova com o cartão de importação", encoding="utf-8")
    futuro = time.time() + 5
    os.utime(tela, (futuro, futuro))
    assert desktop.limpar_cache_se_atualizado(pasta)  # telas atualizadas: limpa de novo
    assert not cache.exists()
```

## `tests/test_diesel.py` (441 linhas)

```python
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
```

## `tests/test_diesel_relatorio.py` (152 linhas)

```python
"""Relatório do diesel em três níveis (simples, detalhado e completo): contas, textos do Telegram, API e Excel."""

import io
from datetime import date

import pytest
from openpyxl import load_workbook

from app import contexto
from app.banco import BancoBoletos
from app.diesel import precos, relatorio, servico
from app.diesel.bot import BotDiesel
from app.diesel.modelos import ABAS_DIESEL
from app.notificacoes import canais

SEGUNDA = date(2026, 9, 21)  # semana de 21 a 27/09
QUARTA = date(2026, 9, 23)


@pytest.fixture(autouse=True)
def banco(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DADOS_DIR", tmp_path)
    diesel = BancoBoletos(tmp_path / "diesel.db", tmp_path / "diesel.xlsx", tmp_path / "backups",
                          abas=ABAS_DIESEL, centros=False, nome_backup="diesel")
    diesel.garantir()
    monkeypatch.setattr(contexto, "diesel", diesel)
    yield diesel
    diesel.parar()


@pytest.fixture
def semana():
    """Uma semana com S10 e comum, histórico de 90 dias antes e um caminhão que gastou muito acima do normal."""
    precos.salvar({"Diesel S10": 7.45, "Diesel comum": 6.75}, "Fábio")
    servico.salvar_maquina({"nome": "Escavadeira", "tipo": "Máquina", "combustivel": "Diesel comum"}, "Fábio")  # horas
    servico.salvar_maquina({"nome": "Caminhão", "tipo": "Caminhão", "combustivel": "Diesel S10"}, "Fábio")  # km
    servico.salvar_maquina({"nome": "Gerador", "tipo": "Gerador", "combustivel": "Diesel comum"}, "Fábio")
    servico.lancar_compra({"data": SEGUNDA, "litros": 1000, "valor": 7450, "combustivel": "Diesel S10"}, "Fábio")
    # histórico: o caminhão já abastecia desde agosto (o "normal" dele é ~4,8 L/dia)
    servico.lancar_abastecimento({"data": date(2026, 8, 10), "maquina": "Caminhão", "litros": 100, "medidor": 140000}, "Almir")
    # semana anterior: escavadeira 150 L, caminhão 100 L
    servico.lancar_abastecimento({"data": date(2026, 9, 15), "maquina": "Escavadeira", "litros": 150, "medidor": 1000}, "Almir")
    servico.lancar_abastecimento({"data": date(2026, 9, 16), "maquina": "Caminhão", "litros": 100, "medidor": 150000}, "Almir")
    # esta semana
    servico.lancar_abastecimento({"data": SEGUNDA, "maquina": "Escavadeira", "litros": 160, "medidor": 1020,
                                  "posto": "Posto City", "pessoa": "Marcos"}, "Almir")
    servico.lancar_abastecimento({"data": QUARTA, "maquina": "Caminhão", "litros": 200, "medidor": 150800,
                                  "posto": "Posto City", "pessoa": "Juliana"}, "Almir")
    servico.lancar_abastecimento({"data": QUARTA, "maquina": "Caminhão", "litros": 100, "posto": "Auto Posto",
                                  "pessoa": "Juliana"}, "Almir")  # sem km


def test_analise_compara_mostra_trechos_e_pontos_de_atencao(semana):
    r = relatorio.analise("semana", SEGUNDA, alerta_valor=1000, hoje=date(2026, 9, 25))
    assert r["abastecido"]["custo"] == 160 * 6.75 + 300 * 7.45
    assert r["anterior"]["custo"] == 150 * 6.75 + 100 * 7.45 and r["variacao"]["litros"] == 84.0  # 460 L contra 250 L
    caminhao = next(m for m in r["por_maquina"] if m["maquina"] == "Caminhão")
    assert caminhao["litros_anterior"] == 100 and caminhao["variacao"] == 200.0
    assert caminhao["media_normal"] == 4.76 and caminhao["acima_do_normal"] > 0  # 60 L/dia contra 4,76 L/dia
    # o trecho: 800 km desde a leitura anterior, com 200 L = 4 km/L; a escavadeira: 20 h com 160 L = 8 L/h
    trechos = {a["maquina"]: a["trecho"] for a in r["abastecimentos"] if a.get("trecho")}
    assert trechos["Caminhão"]["rodado"] == 800 and trechos["Caminhão"]["rotulo"] == "4.0 km/L".replace(".", ",")
    assert trechos["Escavadeira"]["rotulo"] == "8.0 L/h".replace(".", ",")
    textos = " ".join(a["texto"] for a in r["alertas"])
    assert "Caminhão consumiu" in textos and "sem horímetro/km: Caminhão (1)" in textos and "Gerador" in textos
    assert [d["rotulo"] for d in r["serie"]][:3] == ["seg 21", "ter 22", "qua 23"]
    assert r["serie"][2]["por_combustivel"] == {"Diesel S10": 2235.0}
    assert [p["nome"] for p in r["por_posto"]] == ["Posto City", "Auto Posto"]
    assert r["por_pessoa"][0]["nome"] == "Juliana" and r["por_pessoa"][0]["litros"] == 300
    assert r["previsao"]["saldo"] == 7450 - 150 * 6.75 - 200 * 7.45 - 160 * 6.75 - 300 * 7.45
    escavadeira = next(m for m in r["por_maquina"] if m["maquina"] == "Escavadeira")
    assert escavadeira["media_normal"] == 0 and not escavadeira["acima_do_normal"]  # só 6 dias de histórico: sem "normal"
    assert r["previsao"]["dias"] > 0


def test_periodo_passado_nao_tem_previsao(semana):
    r = relatorio.analise("semana", SEGUNDA, hoje=date(2026, 10, 20))
    assert r["previsao"] is None and r["periodo_atual"] is False


def test_tres_niveis_de_texto(semana):
    hoje = date(2026, 9, 25)
    simples = relatorio.texto("semana", SEGUNDA, "simples", 1000, hoje)
    assert "Relatório semanal" in simples and "Abastecido: <b>R$ 3.315,00</b>" in simples
    assert "• Caminhão: 300 L · R$ 2.235,00" in simples and "dá para ~" in simples
    assert "ponto(s) de atenção" in simples and "Pontos de atenção" not in simples
    detalhado = relatorio.texto("semana", SEGUNDA, "detalhado", 1000, hoje)
    assert "Pontos de atenção" in detalhado and "Comparado com" in detalhado and "Por máquina" in detalhado
    completo = relatorio.texto("semana", SEGUNDA, "completo", 1000, hoje)
    assert "<b>Abastecimentos</b>" in completo and "23/09 Caminhão: 200 L" in completo and "4,0 km/L" in completo
    assert "<b>Por posto</b>" in completo and "<b>Quem abasteceu</b>" in completo
    assert len(simples) < len(detalhado) < len(completo)
    assert relatorio.texto("semana", SEGUNDA, "qualquer", 1000, hoje) == simples  # nível desconhecido: simples


def test_texto_longo_e_cortado_para_o_telegram():
    texto = "\n".join(f"linha {n} " + "x" * 60 for n in range(200))
    cortado = relatorio._limitar(texto)
    assert len(cortado) <= relatorio.LIMITE_TELEGRAM and cortado.endswith("(continua no Excel: Diesel → Relatórios)")


@pytest.fixture
def bot(tmp_path, monkeypatch):
    enviados = []

    def telegram(token, metodo, dados=None):
        enviados.append((metodo, dados or {}))
        return {"message_id": 1} if metodo.startswith("send") else True

    monkeypatch.setattr(canais, "_telegram", telegram)
    b = BotDiesel(tmp_path / "diesel_bot.json", lambda dados, nome: {"id": "a1", "nome": nome, "caminho": "arquivos/a1.jpg"},
                  lambda: {"100": "Fábio"}, ler=lambda dados, nome, legenda: {})
    b.configurar({"token": "123:abc", "gestores": ["100"]})
    b.enviados = enviados
    return b


def test_comando_do_bot_e_nivel_dos_automaticos(bot, semana):
    bot._comando("100", "/relatorio mes completo", "Fábio")
    assert "Relatório mensal" in bot.enviados[-1][1]["text"] and "Pontos de atenção" in bot.enviados[-1][1]["text"]
    bot._comando("100", "/relatorio", "Fábio")
    assert "Relatório semanal" in bot.enviados[-1][1]["text"] and "Pontos de atenção" not in bot.enviados[-1][1]["text"]
    assert bot.nivel_relatorio() == "simples"
    bot.configurar({"nivel_relatorio": "detalhado"})
    assert bot.nivel_relatorio() == "detalhado" and bot.config_publica()["nivel_relatorio"] == "detalhado"
    bot.configurar({"nivel_relatorio": "invalido"})
    assert bot.nivel_relatorio() == "detalhado"


def test_api_do_relatorio_e_excel_completo(bot, semana, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(contexto, "diesel_bot", bot)
    with TestClient(app) as cliente:
        r = cliente.get("/api/diesel/relatorio", params={"periodo": "semana", "data": "2026-09-23"}).json()
        assert {"serie", "por_posto", "por_pessoa", "alertas", "anterior", "variacao", "previsao", "precos"} <= set(r)
        assert r["alerta_valor"] == servico.ALERTA_PADRAO
        texto = cliente.get("/api/diesel/relatorio/texto", params={"periodo": "semana", "data": "2026-09-23",
                                                                   "nivel": "completo"}).json()["texto"]
        assert "<b>Abastecimentos</b>" in texto
        excel = cliente.get("/api/diesel/relatorio/arquivo", params={"periodo": "semana", "data": "2026-09-23"})
        wb = load_workbook(io.BytesIO(excel.content))
        assert wb.sheetnames == ["Resumo", "Máquinas", "Por dia", "Combustíveis", "Por posto", "Por pessoa",
                                 "Abastecimentos", "Compras", "Pontos de atenção"]
        assert wb["Resumo"]["B3"].value == 3315
        enviado = cliente.post("/api/diesel/relatorio/enviar", params={"periodo": "semana", "data": "2026-09-23",
                                                                       "nivel": "detalhado"})
        assert enviado.json() == {"enviado": 1} and "Pontos de atenção" in bot.enviados[-1][1]["text"]
```

## `tests/test_empresas.py` (211 linhas)

```python
"""Módulo Empresas: cadastro, fechamento por período, baixa automática, cheques e relatório."""

from datetime import date, datetime

import pytest

from app import contexto
from app.empresas import relatorio, servico


@pytest.fixture(autouse=True)
def banco_limpo(tmp_path, monkeypatch):
    """Cada teste usa um banco de empresas só dele."""
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
def imapal():
    return servico.salvar_empresa({"nome": "Imapal", "cnpj": "12.345.678/0001-95", "apelidos": "Imapal Construções"},
                                  "Fábio")


def _itens(nf, pedido, data, material="Brita 01", quantidade=12, unitario=158.80):
    return [{"data": data, "material": material, "unidade": "M³", "quantidade": quantidade,
             "valor_unitario": unitario, "numero_nf": nf, "pedido": pedido}]


# --------------------------------------------------------------------------- período e cadastro


def test_a_nota_entra_no_fechamento_pelo_dia_20():
    assert servico.competencia_de(date(2026, 7, 29), 20) == "2026-08"
    assert servico.competencia_de(date(2026, 8, 17), 20) == "2026-08"
    assert servico.competencia_de(date(2026, 8, 21), 20) == "2026-09"
    assert servico.competencia_de(date(2026, 12, 29), 20) == "2027-01"
    assert servico.periodo("2026-08", 20) == (date(2026, 7, 21), date(2026, 8, 20))
    assert servico.periodo("2026-01", 20) == (date(2025, 12, 21), date(2026, 1, 20))


def test_identifica_a_empresa_por_cnpj_nome_ou_apelido(imapal):
    assert servico.identificar_empresa(cnpj="12345678000195")["id"] == imapal["id"]
    assert servico.identificar_empresa(nome="IMAPAL")["id"] == imapal["id"]
    assert servico.identificar_empresa(nome="Imapal Construções Ltda")["id"] == imapal["id"]
    assert servico.identificar_empresa(texto="Cheque da imapal, pedido 7043")["id"] == imapal["id"]
    assert servico.identificar_empresa(nome="Outra Empresa") is None


def test_nao_deixa_cadastrar_duas_empresas_com_o_mesmo_nome(imapal):
    with pytest.raises(servico.ErroEmpresas):
        servico.salvar_empresa({"nome": "imapal"}, "Fábio")


def test_renomear_a_empresa_leva_junto_as_notas(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 10)), "Fábio")
    servico.salvar_empresa({"nome": "Imapal Materiais"}, "Fábio", imapal["id"])
    assert {n["empresa"] for n in contexto.empresas.listar("notas")} == {"Imapal Materiais"}


# --------------------------------------------------------------------------- fechamento


def test_fechamento_junta_as_notas_do_periodo(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 7, 29)), "Fábio")
    servico.lancar_notas("Imapal", _itens("6951", "7139", date(2026, 8, 14), "Pedrisco"), "Fábio")
    servico.lancar_notas("Imapal", _itens("7001", "7200", date(2026, 8, 25)), "Fábio")  # já é do próximo

    f = servico.fechamento("Imapal", "2026-08", hoje=date(2026, 8, 18))
    assert f["inicio"] == date(2026, 7, 21) and f["fim"] == date(2026, 8, 20)
    assert [l["numero_nf"] for l in f["linhas"]] == ["6859", "6951"]
    assert f["totais"]["total"] == 3811.2 and f["totais"]["falta"] == 3811.2
    assert servico.fechamento("Imapal", "2026-09")["totais"]["total"] == 1905.6


def test_valor_total_sai_da_quantidade_vezes_o_unitario(imapal):
    nota = servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")[0]
    assert nota["valor_total"] == 1905.6 and nota["status"] == "Em aberto"


# --------------------------------------------------------------------------- baixa automática


def test_comprovante_com_o_numero_da_nf_da_baixa_so_naquela_nota(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    servico.lancar_notas("Imapal", _itens("6869", "7053", date(2026, 8, 5)), "Fábio")

    recebimento = servico.registrar_recebimento(
        {"empresa": "Imapal", "forma": "Pix", "valor": 1905.60, "data": date(2026, 8, 20), "notas": "6869",
         "pagador": "IMAPAL LTDA", "id_transacao": "E12345678202608201200"}, "Fábio")

    notas = {n["numero_nf"]: n for n in contexto.empresas.listar("notas")}
    assert notas["6869"]["status"] == "Recebido" and notas["6869"]["valor_recebido"] == 1905.6
    assert notas["6859"]["status"] == "Em aberto"
    assert recebimento["aplicacoes"].startswith("#2 NF 6869: R$ 1.905,60")
    assert servico.fechamento("Imapal", "2026-08")["totais"]["falta"] == 1905.6


def test_pagamento_parcial_deixa_a_nota_parcial_e_mostra_quanto_falta(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    servico.registrar_recebimento({"empresa": "Imapal", "valor": 900, "data": date(2026, 8, 10), "notas": "6859"}, "Ana")

    nota = contexto.empresas.listar("notas")[0]
    assert nota["status"] == "Parcial" and nota["valor_recebido"] == 900
    assert servico.fechamento("Imapal", "2026-08")["totais"] == {
        "quantidade": 1, "total": 1905.6, "recebido": 900.0, "falta": 1005.6, "em_cheque": 0.0, "notas": 1}


def test_sem_numero_de_nf_o_valor_baixa_as_notas_mais_antigas(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    servico.lancar_notas("Imapal", _itens("6869", "7053", date(2026, 8, 5)), "Fábio")
    recebimento = servico.registrar_recebimento({"empresa": "Imapal", "valor": 2500, "data": date(2026, 8, 20)}, "Ana")

    notas = {n["numero_nf"]: n for n in contexto.empresas.listar("notas")}
    assert notas["6859"]["status"] == "Recebido"
    assert notas["6869"]["status"] == "Parcial" and notas["6869"]["valor_recebido"] == 594.4
    assert recebimento["sobra"] == 0


def test_sobra_vira_credito_e_cancelar_devolve_tudo(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    recebimento = servico.registrar_recebimento({"empresa": "Imapal", "valor": 2000, "data": date(2026, 8, 20)}, "Ana")
    assert recebimento["sobra"] == 94.4 and "sobra (crédito)" in recebimento["aplicacoes"]

    servico.cancelar_recebimento(recebimento["id"], "Ana")
    nota = contexto.empresas.listar("notas")[0]
    assert nota["status"] == "Em aberto" and not nota["valor_recebido"]
    assert contexto.empresas.obter(recebimento["id"], "recebimentos")["status"] == "Cancelado"


def test_recebimento_descobre_a_empresa_pelo_numero_da_nota(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    recebimento = servico.registrar_recebimento({"valor": 1905.60, "notas": "6859", "data": date(2026, 8, 21)}, "Ana")
    assert recebimento["empresa"] == "Imapal"


# --------------------------------------------------------------------------- cheques


def test_cheque_prende_as_notas_do_pedido_e_libera_ao_compensar(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    cheque = servico.lancar_cheque({"empresa": "Imapal", "numero": "000123", "vencimento": date(2026, 9, 10),
                                    "valor": 1905.60, "banco": "Sicredi", "agencia": "0710", "coop": "3003",
                                    "conta": "12345", "pedidos": "7043"}, "Fábio")
    nota = contexto.empresas.listar("notas")[0]
    assert nota["status"] == "Em cheque" and nota["cheque_id"] == cheque["id"]
    assert servico.fechamento("Imapal", "2026-08")["totais"]["em_cheque"] == 1905.6

    servico.atualizar_cheque(cheque["id"], {"status": "Compensado", "data_deposito": date(2026, 9, 10)}, "Fábio")
    nota = contexto.empresas.listar("notas")[0]
    assert nota["status"] == "Recebido" and nota["valor_recebido"] == 1905.6
    recebimento = contexto.empresas.listar("recebimentos")[0]
    assert recebimento["forma"] == "Cheque" and recebimento["cheque_id"] == cheque["id"]


def test_cheque_devolvido_solta_as_notas(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 8, 3)), "Fábio")
    cheque = servico.lancar_cheque({"empresa": "Imapal", "valor": 1905.60, "vencimento": date(2026, 9, 10),
                                    "pedidos": "7043"}, "Fábio")
    servico.atualizar_cheque(cheque["id"], {"status": "Devolvido"}, "Fábio")
    assert contexto.empresas.listar("notas")[0]["status"] == "Em aberto"


def test_cheques_a_depositar_viram_avisos_de_vencimento(imapal):
    servico.lancar_cheque({"empresa": "Imapal", "numero": "123", "valor": 500, "vencimento": date(2026, 9, 19)}, "Fábio")
    alertas = servico.alertas_de_cheques(hoje=date(2026, 9, 18), dias_antes=3)
    assert alertas[0]["tipo_pagamento"] == "cheque" and alertas[0]["valor"] == 500
    assert "Imapal" in alertas[0]["beneficiario"]
    assert servico.alertas_de_cheques(hoje=date(2026, 9, 1), dias_antes=3) == []


# --------------------------------------------------------------------------- relatório


def test_relatorio_sai_no_formato_da_planilha_usada_hoje(imapal):
    from io import BytesIO

    from openpyxl import load_workbook

    for nf, pedido, dia, material in (("6859", "7043", 29, "Brita 01"), ("6869", "7053", 30, "Pedrisco")):
        servico.lancar_notas("Imapal", _itens(nf, pedido, date(2026, 7, dia), material), "Fábio")
    f = servico.fechamento("Imapal", "2026-08", hoje=date(2026, 8, 18))
    conteudo = relatorio.gerar_xlsx(f, {"nome": "Prospera Industria E Serviços LTDA", "cnpj": "03.880.985/0001-85"})

    ws = load_workbook(BytesIO(conteudo)).active
    assert ws["A1"].value == "Prospera Industria E Serviços LTDA 03.880.985/0001-85"
    assert ws["A2"].value == "Fechamento Imapal"
    assert [c.value for c in ws[5]] == ["DATA", "MATERIAL", "UNIDADE", "QUANT.", "VALOR UNI.", "VALOR TOTAL",
                                        "NOTA FISCAL", "Nº PEDIDO"]
    assert [ws.cell(row=6, column=c).value for c in (1, 2, 3, 4, 6, 7, 8)] == [
        datetime(2026, 7, 29), "Brita 01", "M³", 12, 1905.6, "6859", "7043"]
    assert relatorio.nome_do_arquivo(f, "pdf") == "fechamento-imapal-2026-08.pdf"
    assert len(relatorio.gerar_pdf(f, {"nome": "Prospera", "cnpj": "03.880.985/0001-85"})) > 1000


def test_resumo_das_empresas_mostra_atraso_e_cheques(imapal):
    servico.lancar_notas("Imapal", _itens("6859", "7043", date(2026, 7, 10)), "Fábio")  # fechamento de julho
    servico.lancar_notas("Imapal", _itens("6951", "7139", date(2026, 8, 14)), "Fábio")
    servico.lancar_cheque({"empresa": "Imapal", "valor": 300, "vencimento": date(2026, 9, 5)}, "Fábio")

    resumo = servico.resumo_empresas(hoje=date(2026, 8, 18))[0]
    assert resumo["nome"] == "Imapal" and resumo["competencia"] == "2026-08"
    assert resumo["em_aberto"] == 3811.2 and resumo["atrasado"] == 1905.6
    assert resumo["cheques"] == {"quantidade": 1, "valor": 300.0}
```

## `tests/test_empresas_api.py` (148 linhas)

```python
"""API do módulo Empresas: cadastro, notas, cheques, recebimentos, fechamento e importação do print."""

import pytest
from fastapi.testclient import TestClient

from app import contexto
from app.main import app
from test_empresas_bot import _pdf
from test_empresas_leitura import PRINT_FECHAMENTO, XML_NFE


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    from app.banco import BancoBoletos
    from app.empresas.configuracao import ConfigEmpresas
    from app.empresas.modelos import ABAS_EMPRESAS

    banco = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                         abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    monkeypatch.setattr(contexto, "empresas", banco)
    monkeypatch.setattr(contexto, "empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))
    with TestClient(app) as c:
        yield c
    banco.parar()


def _empresa(cliente, nome="Imapal", **extra):
    resposta = cliente.post("/api/empresas", json={"nome": nome, "cnpj": "12.345.678/0001-95", **extra})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _nota(cliente, empresa="Imapal", nf="6859", data="2026-08-03", valor=1905.60):
    return cliente.post("/api/notas", json={"empresa": empresa, "itens": [
        {"data": data, "material": "Brita 01", "unidade": "M³", "quantidade": 12, "valor_unitario": 158.80,
         "valor_total": valor, "numero_nf": nf, "pedido": "7043"}]})


def test_cadastro_de_empresa_e_resumo(cliente):
    empresa = _empresa(cliente)
    _nota(cliente)

    dados = cliente.get("/api/empresas").json()
    assert [e["nome"] for e in dados["empresas"]] == ["Imapal"]
    assert dados["empresas"][0]["em_aberto"] == 1905.6
    assert dados["config"]["dia_fechamento"] == 20

    assert cliente.post("/api/empresas", json={"nome": "imapal"}).status_code == 422
    assert cliente.put(f"/api/empresas/{empresa['id']}", json={"status": "Inativa"}).json()["status"] == "Inativa"
    assert cliente.delete(f"/api/empresas/{empresa['id']}").status_code == 422  # já tem lançamentos


def test_fechamento_em_json_excel_e_pdf(cliente):
    empresa = _empresa(cliente)
    _nota(cliente)
    cliente.post("/api/empresas/config", json={"minha_empresa": {"nome": "Prospera", "cnpj": "03.880.985/0001-85"}})

    fechamento = cliente.get(f"/api/empresas/{empresa['id']}/fechamento?competencia=2026-08").json()
    assert fechamento["totais"]["total"] == 1905.6 and fechamento["inicio"] == "2026-07-21"
    assert fechamento["linhas"][0]["numero_nf"] == "6859"

    xlsx = cliente.get(f"/api/empresas/{empresa['id']}/fechamento/arquivo?competencia=2026-08")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    assert "fechamento-imapal-2026-08.xlsx" in xlsx.headers["content-disposition"]
    pdf = cliente.get(f"/api/empresas/{empresa['id']}/fechamento/arquivo?formato=pdf&competencia=2026-08")
    assert pdf.content[:4] == b"%PDF"


def test_mover_a_nota_para_outro_fechamento(cliente):
    """A NF chegou depois do dia 20: dá para mandá-la para o fechamento seguinte, com todas as suas linhas."""
    _empresa(cliente)
    cliente.post("/api/notas", json={"empresa": "Imapal", "itens": [
        {"data": "2026-09-15", "material": "Brita 01", "unidade": "M³", "quantidade": 12, "valor_unitario": 158.80,
         "numero_nf": "7120", "pedido": "7300"},
        {"data": "2026-09-15", "material": "Pedrisco", "unidade": "M³", "quantidade": 5, "valor_unitario": 100,
         "numero_nf": "7120", "pedido": "7300"},
    ]})
    notas = cliente.get("/api/notas").json()["notas"]
    assert {n["competencia"] for n in notas} == {"2026-09"}  # pela data, entrou no fechamento de setembro

    movida = cliente.put(f"/api/notas/{notas[0]['id']}", json={"competencia": "2026-10", "todas_da_nota": True}).json()
    assert movida["linhas_movidas"] == 2
    assert {n["competencia"] for n in cliente.get("/api/notas").json()["notas"]} == {"2026-10"}

    empresa_id = cliente.get("/api/empresas").json()["cadastro"][0]["id"]
    setembro = cliente.get(f"/api/empresas/{empresa_id}/fechamento?competencia=2026-09").json()
    outubro = cliente.get(f"/api/empresas/{empresa_id}/fechamento?competencia=2026-10").json()
    assert setembro["totais"]["total"] == 0 and outubro["totais"]["total"] == 2405.60


def test_recebimento_da_baixa_e_pode_ser_cancelado(cliente):
    _empresa(cliente)
    _nota(cliente)

    recebimento = cliente.post("/api/recebimentos", json={"empresa": "Imapal", "forma": "Pix", "valor": 1905.60,
                                                          "data": "2026-08-20", "notas": "6859"}).json()
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Recebido"

    cliente.post(f"/api/recebimentos/{recebimento['id']}/cancelar")
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Em aberto"
    assert cliente.get("/api/recebimentos").json()["recebimentos"][0]["status"] == "Cancelado"


def test_cheque_pela_api_prende_e_solta_as_notas(cliente):
    _empresa(cliente)
    _nota(cliente)

    cheque = cliente.post("/api/cheques", json={"empresa": "Imapal", "numero": "123", "valor": 1905.60,
                                                "vencimento": "2026-09-10", "pedidos": "7043",
                                                "banco": "Sicredi", "coop": "3003"}).json()
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Em cheque"

    cliente.put(f"/api/cheques/{cheque['id']}", json={"status": "Compensado", "data_deposito": "2026-09-10"})
    assert cliente.get("/api/notas").json()["notas"][0]["status"] == "Recebido"
    assert cliente.get("/api/cheques?status=Compensado").json()["cheques"][0]["id"] == cheque["id"]


def test_analisar_arquivo_e_importar_print_do_fechamento(cliente):
    _empresa(cliente)
    xml = cliente.post("/api/empresas/analisar", files={"arquivo": ("nfe.xml", XML_NFE.encode("utf-8"), "text/xml")}).json()
    assert xml["tipo"] == "nota" and xml["empresa"] == "Imapal" and xml["dados"]["numero_nf"] == "6859"

    lido = cliente.post("/api/empresas/analisar",
                        files={"arquivo": ("print.pdf", _pdf(PRINT_FECHAMENTO), "application/pdf")}).json()
    assert lido["tipo"] == "fechamento" and len(lido["dados"]["linhas"]) == 5

    importado = cliente.post("/api/empresas/importar-fechamento",
                             json={"empresa": "Imapal", "linhas": lido["dados"]["linhas"]}).json()
    assert importado["quantidade"] == 5
    fechamento = cliente.get("/api/empresas/1/fechamento?competencia=2026-08").json()
    assert fechamento["totais"]["total"] == 9528.0 and fechamento["totais"]["quantidade"] == 5


def test_conferencia_da_caixa_de_entrada_do_bot(cliente):
    _empresa(cliente)
    item = contexto.empresas_entrada.receber(_pdf(PRINT_FECHAMENTO), "print.pdf")
    entrada = cliente.get("/api/empresas/entrada").json()
    assert entrada["pendentes"] >= 1 and any(i["id"] == item["id"] for i in entrada["itens"])

    assert cliente.post(f"/api/empresas/entrada/{item['id']}/descartar").json() == {"ok": True}
    assert cliente.post(f"/api/empresas/entrada/{item['id']}/descartar").status_code == 404


def test_config_do_bot_de_notas_esconde_o_token(cliente):
    salvo = cliente.post("/api/empresas/config", json={"dia_fechamento": 15, "bot": {"token": "123:abc"}}).json()
    assert salvo["dia_fechamento"] == 15 and salvo["bot"]["token"] == "••••••••"
    assert cliente.post("/api/empresas/config", json={"dia_fechamento": 40}).status_code == 422
    assert contexto.empresas_config.token() == "123:abc"
```

## `tests/test_empresas_bot.py` (273 linhas)

```python
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
```

## `tests/test_empresas_leitura.py` (272 linhas)

```python
"""Leitura dos arquivos do bot de notas: NF-e (XML e DANFE), cheque, comprovante e print do fechamento."""

from datetime import date

from app.empresas import leitura

XML_NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
 <NFe><infNFe Id="NFe35260803880985000185550010000068591000068591" versao="4.00">
  <ide><cUF>35</cUF><nNF>6859</nNF><serie>1</serie><dhEmi>2026-07-29T10:12:00-03:00</dhEmi></ide>
  <emit><CNPJ>03880985000185</CNPJ><xNome>PROSPERA INDUSTRIA E SERVICOS LTDA</xNome></emit>
  <dest><CNPJ>12345678000195</CNPJ><xNome>IMAPAL CONSTRUCOES LTDA</xNome></dest>
  <det nItem="1"><prod><cProd>101</cProd><xProd>BRITA 01</xProd><NCM>25171000</NCM><uCom>M3</uCom>
    <qCom>12.0000</qCom><vUnCom>158.8000000000</vUnCom><vProd>1905.60</vProd><xPed>7043</xPed></prod></det>
  <det nItem="2"><prod><cProd>102</cProd><xProd>PEDRISCO</xProd><uCom>M3</uCom>
    <qCom>5.0000</qCom><vUnCom>100.0000000000</vUnCom><vProd>500.00</vProd><xPed>7043</xPed></prod></det>
  <total><ICMSTot><vNF>2405.60</vNF></ICMSTot></total>
  <infAdic><infCpl>Pedido 7043 - entrega na obra</infCpl></infAdic>
 </infNFe></NFe>
</nfeProc>"""

DANFE = """PROSPERA INDUSTRIA E SERVICOS LTDA
DANFE
DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRONICA
0 - ENTRADA
1 - SAIDA
Nº 000.006.859 SERIE 1
CHAVE DE ACESSO
3526 0803 8809 8500 0185 5500 1000 0068 5910 0006 8591
NATUREZA DA OPERACAO
VENDA DE MERCADORIA
DESTINATARIO/REMETENTE
NOME/RAZAO SOCIAL
IMAPAL CONSTRUCOES LTDA 12.345.678/0001-95
DATA DA EMISSAO
29/07/2026
DADOS DO PRODUTO / SERVICOS
CODIGO DESCRICAO DO PRODUTO NCM CST CFOP UNID QUANT VALOR UNIT VALOR TOTAL
101 BRITA 01 25171000 000 5102 M3 12,0000 158,80 1.905,60
102 PEDRISCO 25171000 000 5102 M3 5,0000 100,00 500,00
CALCULO DO IMPOSTO
VALOR TOTAL DA NOTA
2.405,60
DADOS ADICIONAIS
Pedido 7043
"""

CHEQUE = """BANCO COOPERATIVO SICREDI S.A.
COOP 3003 AG 0710 C1
PAGUE POR ESTE CHEQUE A QUANTIA DE R$ 1.905,60
A IMAPAL CONSTRUCOES LTDA OU A SUA ORDEM
MIRASSOL 10 DE AGOSTO DE 2026
COMPENSAVEL EM SAO JOSE DO RIO PRETO
BOM PARA 10/09/2026
<74807101< 0180001235: 000004567898>
"""

# OCR real de uma foto de cheque Sicredi (frente e verso, lida nas quatro orientações): é assim que chega
# pelo bot — texto embaralhado, "Bom p/" quase ilegível e os pedidos escritos à mão no verso.
CHEQUE_FOTO = """SICREDI BIOMAS cheque a quantia de Pague por este 018 Comp.
06 48 AV. SERGIPE, 1202 33.022.690/0011–00 AMAZONAS – SICREDI BIOMAS Sicredi
PAC S.J. QUATRO MARCOS - MT CONFECÇÃO: 0812025 NOROESTE DE MATO GROSSO ACREE COOP DE CRED POUP E INVEST DO 748 Banco
PrespeneIndus tra buabre mily 8058 Coop
6
CHEQUE ESPECIAL 62
9894-8 Conta n°
392855950001-04 8
PPmP 2426 CLIENTE BANCARIO DESDE 11 12020 JOSE PAZETE CIA LTDA Lomenerolemsenvdcos A00 Série
duesentos pubnta gete pear a pessenta centavos 000616 Cheque n°
elembro 8
1105108 4.287.60#
2036 ou à sua ordem e centavos acima
Comp. Banco Coop C1 Conta n° C2 Série Cheque n° C3 4.287.60#
018 748 8058 6 9 9894-8 7. A00 0006 16 5
cheque a quantia de Pague por este Buatre mil dugentos retento gete preare pesento cntavos
e centavos acima
PrespereIndustre Comenetoaservcos ou à sua ordem
SicrediCHEQUE ESECIAL 18itembre de 2006
COOP DE CRED POUP E INVEST DO
NOROESTE DE MATOGROSSOACREE JOSE PAZETE CIA LTDA
AMAZONAS – SICREDI BIOMAS 392855950001-04
33.022.690/0011–00
SICREDI BIOMAS 1105108
AV. SERGIPE, 1202 CLIENTE BANCARIO DESDE 11 12020
PAC S.J. QUATRO MARCOS - MTCONFECÇÃO: 0812025
Pom p) 24/0926
e centavos acima ou à sua ordem 9000
#09t8c de 1105108 Pom p) 24lo9126
8 5
Cheque n° 0006 16 JOSE PAZETE CIA LTDA CLIENTE BANCARIO DESDE 11 12020
Série A00 392855950001-04
8
Conta n° 9894-8
0 prul onpomg CHEQUE ESPECIAL
do03 8058 COOP DE CRED POUP E INVEST DO NOROESTE DE MATOGROSSO ACREE
Banco 748 AMAZONAS – SICREDI BIOMAS 33.022.690/0011–00 SICREDI BIOMAS AV. SERGIPE, 1202
duos 018
Pom P) 2409126 i"n y m
1105108 CLIENTE BANCARIO DESDE 11 12020 AV. SERGIPE, 1202
SICREDI BIOMAS
33.022.690/0011–00
392855950001-04 AMAZONAS – SICREDI BIOMAS
JOSE PAZETE CIA LTDA NOROESTE DE MATOGROSSOACREE
COOP DE CRED POUP E INVEST DO
de CHEQUE ESPECIAL
2006
ou à sua ordem arohanet
e centavos acima
gele auymp ap eueno e an
2.87.60± S 0006 16 A00 7. 9894-8 6 9 8058 748 018
R$ Conta n° 10 do03 duoo
13689-2 996)
08%t
1 Peddos= 7200-7201-7219-7245-7255
7301- 7310- 7307
1966 Reddos: 7200-7201-7219-7245-7255
2280 - 7301 - 7310- 7307
13689-2
sst-Sht-6/8t-10Ct-005t=spp toet -OIEt-1oet
08%t
1966 13689-7
toet -01Et-10et- 08tt 996)
ss ōt -Sht -b/ot - 10Ct -00st =spp"""

COMPROVANTE_PIX = """Comprovante de transferência Pix
Valor R$ 1.905,60
Data do pagamento 20/08/2026 14:35
Pagador
IMAPAL CONSTRUCOES LTDA
12.345.678/0001-95
Recebedor
PROSPERA INDUSTRIA E SERVICOS LTDA
ID da transação E1234567820260820143500123456
Descrição NF 6859 e 6869
"""

PRINT_FECHAMENTO = """Prospera Industria E Serviços LTDA 03.880.985/0001-85
Fechamento Imapal
DATA MATERIAL UNIDADE QAUNT. VALOR UNI. VALOR TOTAL NOTA FICAL N PEDIDO
29/07/2026 Brita 01 M³ 12 158,8 R$ 1.905,60 6859 7043
30/07/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6869 7053
10/08/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6822 7110
14/08/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6951 7139
17/08/2026 Brita 01 M³ 12 158,8 R$ 1.905,60 6958 7147
R$ 9.528,00
"""


# --------------------------------------------------------------------------- nota fiscal


def test_le_a_nota_fiscal_pelo_xml():
    nota = leitura.ler_xml_nota(XML_NFE.encode("utf-8"))
    assert nota["numero_nf"] == "6859" and nota["data"] == date(2026, 7, 29)
    assert nota["destinatario"] == {"nome": "IMAPAL CONSTRUCOES LTDA", "cnpj": "12345678000195"}
    assert nota["emitente"]["cnpj"] == "03880985000185"
    assert nota["valor_total"] == 2405.60 and nota["pedidos"] == ["7043"]
    assert nota["itens"][0] == {"material": "BRITA 01", "unidade": "M3", "quantidade": 12.0,
                                "valor_unitario": 158.8, "valor_total": 1905.6, "pedido": "7043"}
    assert nota["confianca"] == 1.0


def test_le_o_danfe_pelo_texto():
    assert leitura.classificar(DANFE) == "nota"
    nota = leitura.extrair_nota(DANFE)
    assert nota["numero_nf"] == "6859" and nota["data"] == date(2026, 7, 29)
    assert "IMAPAL" in nota["destinatario"]["nome"] and nota["destinatario"]["cnpj"] == "12345678000195"
    assert nota["valor_total"] == 2405.60 and nota["pedidos"] == ["7043"]
    assert [(i["material"], i["unidade"], i["quantidade"], i["valor_total"]) for i in nota["itens"]] == [
        ("BRITA 01", "M³", 12.0, 1905.6), ("PEDRISCO", "M³", 5.0, 500.0)]


def test_numero_da_nota_sai_da_chave_de_acesso():
    """No DANFE fotografado o número impresso às vezes sai errado; a chave de acesso não deixa dúvida."""
    chave = "35260803880985000185" + "55" + "001" + "000007120" + "1" + "12345678" + "9"
    grupos = " ".join(chave[i:i + 4] for i in range(0, 44, 4))
    texto = f"DANFE\nCHAVE DE ACESSO\n{grupos}\nNº 2.000.000.000.201 SERIE 1"
    assert leitura._numero_pela_chave(texto) == "7120"
    assert leitura.extrair_nota(texto)["numero_nf"] == "7120"
    assert leitura._numero_pela_chave("sem chave nenhuma") == ""


def test_analisar_reconhece_o_xml_sem_precisar_de_ocr():
    analise = leitura.analisar(XML_NFE.encode("utf-8"), "nfe-6859.xml")
    assert analise["tipo"] == "nota" and analise["dados"]["numero_nf"] == "6859"
    assert leitura.publico(analise)["dados"]["data"] == "2026-07-29"


# --------------------------------------------------------------------------- cheque


def test_le_o_cheque_pela_linha_cmc7_e_pelos_rotulos():
    assert leitura.classificar(CHEQUE) == "cheque"
    cheque = leitura.extrair_cheque(CHEQUE, legenda="Cheque da Imapal, pedido 7043")
    assert cheque["banco"] == "Sicredi" and cheque["agencia"] == "0710"
    assert cheque["numero"] == "123" and cheque["conta"] == "456789"
    assert cheque["coop"] == "3003"
    assert cheque["valor"] == 1905.60 and cheque["vencimento"] == date(2026, 9, 10)
    assert cheque["pedidos"] == ["7043"]


def test_le_a_foto_de_um_cheque_de_verdade():
    """Frente e verso fotografados: valor, "bom para" à mão, dados da conta e os pedidos do verso."""
    assert leitura.classificar(CHEQUE_FOTO) == "cheque"
    cheque = leitura.extrair_cheque(CHEQUE_FOTO)

    assert cheque["valor"] == 4287.60
    assert cheque["vencimento"] == date(2026, 9, 24)  # "Bom p/ 24/09/26" escrito no canto
    assert cheque["banco"] == "Sicredi" and cheque["coop"] == "8058"
    assert cheque["conta"] == "98948" and cheque["numero"] == "616"
    assert cheque["emitente"] == "JOSE PAZETE CIA LTDA"
    assert "39285595000104" in cheque["documentos"]  # CNPJ de quem assinou
    assert cheque["pedidos"] == ["7200", "7201", "7219", "7245", "7255", "7301", "7307", "7310"]
    assert cheque["confianca"] >= 0.9


def test_data_escrita_a_mao_aceita_ruido_do_ocr():
    from datetime import date as tipo_data

    hoje = tipo_data(2026, 9, 18)
    assert leitura._data_escrita_a_mao("Bom p/ 24/09/26", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("Pom p) 24lo9126", hoje) == date(2026, 9, 24)  # "/" virou "l", "0" virou "o"
    assert leitura._data_escrita_a_mao("Pom P) 2409126", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("24/09/2026", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("nada de data aqui", hoje) is None
    assert leitura._data_escrita_a_mao("01/01/2019", hoje) is None  # fora da janela de um cheque


def test_numeros_soltos_do_cheque_nao_viram_pedidos():
    """Conta, cooperativa e endereço não podem ser confundidos com a lista de pedidos do verso."""
    frente = "018 748 8058 6 9 9894-8 7. A00 0006 16 5\nAV. SERGIPE, 1202 33.022.690/0011-00"
    assert leitura._numeros_em_sequencia(frente) == []
    verso = "Peddos= 7200-7201-7219-7245-7255\n7301- 7310- 7307"
    assert leitura._numeros_em_sequencia(verso) == ["7200", "7201", "7219", "7245", "7255", "7301", "7307", "7310"]


def test_cmc7_fora_de_ordem_nao_quebra():
    assert leitura.ler_cmc7("sem numeros aqui") == {}
    assert leitura.ler_cmc7("748071010000123019000045678908")["banco_codigo"] == "748"


# --------------------------------------------------------------------------- comprovante


def test_le_o_comprovante_de_pix_com_as_notas_citadas():
    assert leitura.classificar(COMPROVANTE_PIX) == "comprovante"
    dados = leitura.extrair_comprovante(COMPROVANTE_PIX)
    assert dados["forma"] == "Pix" and dados["valor"] == 1905.60
    assert dados["data"] == date(2026, 8, 20) and dados["hora"] == "14:35"
    assert dados["notas"] == ["6859", "6869"]
    assert dados["id_transacao"].startswith("E1234567820260820")
    assert "IMAPAL" in dados["pagador"]


def test_numeros_de_nf_e_pedido_na_legenda():
    assert leitura.numeros_de_nf("Pagamento das NF 6859, 6869 e 6870") == ["6859", "6869", "6870"]
    assert leitura.numeros_de_pedido("cheque do pedido 7043 e 7053") == ["7043", "7053"]
    assert leitura.numeros_de_nf("sem nada aqui") == []


# --------------------------------------------------------------------------- print do fechamento (Parte 5)


def test_le_o_print_do_fechamento_linha_por_linha():
    assert leitura.classificar(PRINT_FECHAMENTO) == "fechamento"
    lido = leitura.ler_fechamento(PRINT_FECHAMENTO)
    assert lido["empresa"] == "Imapal"
    assert len(lido["linhas"]) == 5 and lido["total"] == 9528.00
    assert lido["linhas"][0] == {"data": date(2026, 7, 29), "material": "Brita 01", "unidade": "M³",
                                 "quantidade": 12.0, "valor_unitario": 158.8, "valor_total": 1905.6,
                                 "numero_nf": "6859", "pedido": "7043"}
    assert lido["linhas"][-1]["numero_nf"] == "6958"
```

## `tests/test_entrada.py` (204 linhas)

```python
"""Caixa de entrada: boletos recebidos por e-mail (IMAP) e pelo bot do Telegram (sem acessar a internet)."""

from datetime import date, timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from app import admin, contexto, entrada, main
from app.arquivos import RepositorioArquivos
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

PDF = b"%PDF-1.4 boleto de teste " + b"x" * 200
FOTO = b"\xff\xd8\xff" + b"f" * 30_000


def _email(remetente, assunto, anexos):
    msg = EmailMessage()
    msg["From"] = remetente
    msg["Subject"] = assunto
    msg.set_content("Segue o boleto.")
    for nome, dados, tipo in anexos:
        principal, sub = tipo.split("/")
        msg.add_attachment(dados, maintype=principal, subtype=sub, filename=nome)
    return msg.as_bytes()


class ImapFalso:
    def __init__(self, mensagens, validade="777"):
        self.mensagens = mensagens  # {uid: bytes}
        self.validade = validade
        self.buscas = []
        self.fetches = []

    def login(self, usuario, senha):
        if senha != "senha-de-app":
            import imaplib
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")

    def select(self, pasta, readonly=False):
        assert readonly  # nunca altera a caixa de e-mail
        return "OK", [b"3"]

    def response(self, nome):
        return nome, [self.validade.encode()]

    def uid(self, comando, argumento, criterio):
        if comando == "SEARCH":
            self.buscas.append(criterio)
            if criterio.startswith("SINCE"):
                uids = sorted(self.mensagens)
            elif criterio == "UID *":
                uids = [max(self.mensagens)] if self.mensagens else []
            else:
                inicio = int(criterio.split()[1].split(":")[0])
                uids = [u for u in sorted(self.mensagens) if u >= inicio] or [max(self.mensagens)]
            return "OK", [" ".join(map(str, uids)).encode()]
        assert "PEEK" in criterio  # só lê: não marca o e-mail como lido
        uid = int(argumento)
        self.fetches.append(uid)
        return "OK", [(f"{uid} (BODY[] {{1}}".encode(), self.mensagens[uid]), b")"]

    def logout(self):
        pass


def _caixa(tmp_path, lidos, destinatarios=()):
    def processar(dados, nome):
        lidos.append(nome)
        if dados.startswith(b"ilegivel"):
            raise ValueError("Não foi possível ler o arquivo.")
        return {"boletos": [{"campos": {"beneficiario": {"valor": "Energia SA"}, "valor": {"valor": 321.5},
                                        "vencimento": {"valor": date(2026, 10, 5)}}, "duplicado": None}],
                "pix": [], "arquivo": {"id": f"{len(lidos):032x}"}}

    return entrada.CaixaEntrada(tmp_path / "entrada.json", processar, lambda dados, nome: {"id": "f" * 32},
                                lambda: ("123:abc", [{"chat_id": c, "nome": "Pessoa"} for c in destinatarios]))


def test_anexos_do_email_ignora_logotipos_e_textos():
    bruto = _email("Energia SA <contas@energia.com.br>", "=?utf-8?q?Fatura_de_Setembro?=", [
        ("fatura.pdf", PDF, "application/pdf"), ("logo.png", b"\x89PNG" + b"l" * 500, "image/png"),
        ("foto-boleto.jpg", FOTO, "image/jpeg"), ("notas.txt", b"texto", "text/plain")])
    info, anexos = entrada.anexos_do_email(bruto)
    assert info["endereco"] == "contas@energia.com.br" and info["remetente"] == "Energia SA"
    assert [nome for nome, _ in anexos] == ["fatura.pdf", "foto-boleto.jpg"]
    assert entrada.remetente_permitido("contas@energia.com.br", "energia.com.br; outro@x.com")
    assert not entrada.remetente_permitido("golpe@energia.com.br.falso.net", "energia.com.br")
    assert entrada.remetente_permitido("qualquer@um.com", "")


def test_email_le_anexos_sem_alterar_a_caixa_e_sem_repetir(tmp_path):
    lidos = []
    caixa = _caixa(tmp_path, lidos)
    with pytest.raises(ValueError):
        caixa.configurar({"email": {"ativo": True}})  # falta servidor, e-mail e senha
    caixa.configurar({"email": {"ativo": True, "servidor": "imap.gmail.com", "usuario": "boletos@empresa.com",
                                "senha": "senha-de-app", "remetentes": "energia.com.br"}})
    assert caixa.config_publica()["email"]["senha"] == entrada.MASCARA

    imap = ImapFalso({
        10: _email("contas@energia.com.br", "Fatura", [("fatura.pdf", PDF, "application/pdf")]),
        11: _email("spam@propaganda.com", "Promoção", [("oferta.pdf", b"%PDF oferta" + b"y" * 50, "application/pdf")]),
        12: _email("contas@energia.com.br", "Reenvio", [("fatura-copia.pdf", PDF, "application/pdf"),
                                                        ("ruim.pdf", b"ilegivel %PDF", "application/pdf")]),
    })
    resultado = caixa.verificar_email(conectar=lambda cfg: imap)
    assert imap.buscas[0].startswith("SINCE")
    assert resultado["recebidos"] == 2 and lidos == ["fatura.pdf", "ruim.pdf"]  # remetente filtrado; cópia idêntica ignorada
    itens = caixa.listar()
    assert {i["estado"] for i in itens} == {"pendente", "erro"}
    pendente = next(i for i in itens if i["estado"] == "pendente")
    assert pendente["origem"] == "email" and pendente["resumo"]["beneficiario"] == "Energia SA"
    assert caixa.arquivos_em_uso() == {pendente["arquivo_id"], "f" * 32}

    imap.mensagens[13] = _email("contas@energia.com.br", "Nova", [("nova.pdf", PDF + b"2", "application/pdf")])
    assert caixa.verificar_email(conectar=lambda cfg: imap)["recebidos"] == 1
    assert imap.buscas[-1] == "UID 13:*"

    assert caixa.marcar_lancados({pendente["arquivo_id"]}) == 1
    assert caixa.contagem() == 2
    with pytest.raises(ValueError, match="senha de app"):
        caixa.configurar({"email": {"senha": "errada"}})
        caixa.verificar_email(conectar=lambda cfg: imap)
    assert "senha de app" in caixa.config_publica()["email"]["ultimo_erro"]


def test_primeira_verificacao_sem_emails_recentes_comeca_do_ultimo(tmp_path):
    caixa = _caixa(tmp_path, [])
    caixa.configurar({"email": {"servidor": "imap.x.com", "usuario": "a@x.com", "senha": "senha-de-app"}})
    imap = ImapFalso({5: b""})
    imap.uid = lambda comando, _c, criterio: ("OK", [b""]) if criterio.startswith("SINCE") else ("OK", [b"5"])
    caixa.verificar_email(conectar=lambda cfg: imap)
    assert caixa._estado["email"]["ultimo_uid"] == 5


def test_telegram_recebe_so_de_pessoas_cadastradas_e_responde(tmp_path, monkeypatch):
    chamadas = []
    atualizacoes = [
        {"update_id": 1, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"}, "from": {"first_name": "Maria"},
                                      "document": {"file_id": "doc1", "file_name": "boleto.pdf", "mime_type": "application/pdf"}}},
        {"update_id": 2, "message": {"chat": {"id": 99, "type": "private", "first_name": "Estranho"},
                                      "photo": [{"file_id": "p1", "file_size": 100}, {"file_id": "p2", "file_size": 900}]}},
        {"update_id": 3, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"}, "text": "/start"}},
        {"update_id": 4, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"},
                                      "photo": [{"file_id": "p3", "file_size": 50}, {"file_id": "p4", "file_size": 5000}]}},
    ]

    def telegram_falso(token, metodo, dados=None):
        chamadas.append((metodo, dados))
        return atualizacoes if metodo == "getUpdates" and not dados.get("offset") else [] if metodo == "getUpdates" else {}

    baixados = []
    monkeypatch.setattr(canais, "_telegram", telegram_falso)
    monkeypatch.setattr(canais, "baixar_arquivo_telegram", lambda token, file_id: baixados.append(file_id) or f"arquivo {file_id}".encode())
    caixa = _caixa(tmp_path, [], destinatarios=["42"])
    assert caixa.verificar_telegram()["recebidos"] == 2
    assert baixados == ["doc1", "p4"]  # a foto do desconhecido não é baixada; da Maria, a maior resolução
    respostas = {(d["chat_id"], d["text"][:20]) for m, d in chamadas if m == "sendMessage"}
    assert ("99", "Este bot só recebe b") in respostas and ("42", "Boleto recebido: Ene") in respostas
    assert caixa._estado["telegram"]["offset"] == 5
    assert {c["chat_id"] for c in caixa.chats_recentes()} == {"42", "99"}
    assert {i["remetente"] for i in caixa.listar()} == {"Maria"}

    caixa.verificar_telegram()
    assert chamadas[-1] == ("getUpdates", {"limit": 50, "timeout": 0, "offset": 5})


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    arquivos = RepositorioArquivos(tmp_path / "arquivos")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "arquivos", arquivos)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    caixa = entrada.CaixaEntrada(tmp_path / "entrada.json", lambda dados, nome: {"boletos": [{}], "pix": [], "arquivo": arquivos.salvar(dados, nome)},
                                 arquivos.salvar, lambda: ("", []))
    monkeypatch.setattr(contexto, "caixa_entrada", caixa)
    with TestClient(main.app) as c:
        yield c, caixa


def test_api_da_caixa_de_entrada(cliente):
    c, caixa = cliente
    item = caixa.receber(PDF, "boleto.pdf", "email", "Energia SA", "Fatura")
    outro = caixa.receber(PDF + b"b", "outro.pdf", "telegram", "Maria")
    dados = c.get("/api/entrada").json()
    assert dados["pendentes"] == 2 and "senha" not in str(dados["itens"])
    assert c.get(f"/api/entrada/{item['id']}").json()["resultado"]["arquivo"]["id"] == item["arquivo_id"]

    # Lançar o boleto revisado tira o arquivo da caixa de entrada
    lancado = c.post("/api/boletos", json={"beneficiario": "Energia SA", "valor": 10, "arquivo_id": item["arquivo_id"],
                                           "vencimento": (date.today() + timedelta(days=3)).isoformat(), "ignorar_validacao": True})
    assert lancado.status_code == 201 and lancado.json()["arquivo_nome"] == "boleto.pdf"
    assert [i["id"] for i in c.get("/api/entrada").json()["itens"]] == [outro["id"]]
    assert c.post("/api/entrada/descartar", json={"ids": [outro["id"]]}).json() == {"descartados": 1, "pendentes": 0}

    assert c.put("/api/entrada/config", json={"telegram": {"ativo": True}}).status_code == 403
    assert c.post("/api/entrada/verificar", json={"canal": "telegram"}).json()["detail"]["codigo"] == "verificacao_falhou"
```

## `tests/test_fechamento.py` (95 linhas)

```python
"""Fechamento do mês para o contador (Excel, PDF e ZIP com comprovantes)."""

import io
import zipfile
from datetime import date, timedelta

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import contexto, fechamento, main
from app.arquivos import RepositorioArquivos
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

SETEMBRO = date(2026, 9, 1)
HOJE = date(2026, 9, 17)


def _boletos():
    return [
        {"id": 1, "beneficiario": "Energisa", "valor": 480.5, "vencimento": date(2026, 9, 10), "status": "Pago",
         "data_pagamento": date(2026, 9, 9), "centro_custo": "Energia", "pago_por": "Maria", "comprovante": "arquivos/x.pdf"},
        {"id": 2, "beneficiario": "Papelaria", "valor": 100, "vencimento": date(2026, 9, 12), "status": "Pendente", "centro_custo": ""},
        {"id": 3, "beneficiario": "Aluguel", "valor": 2000, "vencimento": date(2026, 9, 30), "status": "Pendente", "centro_custo": "Administrativo"},
        {"id": 4, "beneficiario": "Cancelado", "valor": 50, "vencimento": date(2026, 9, 5), "status": "Cancelado"},
        {"id": 5, "beneficiario": "Agosto pago em setembro", "valor": 70, "vencimento": date(2026, 8, 31), "status": "Pago",
         "data_pagamento": date(2026, 9, 1), "centro_custo": "Energia"},
        {"id": -1, "beneficiario": "Aguardando gravação", "valor": 1, "vencimento": date(2026, 9, 2), "status": "Pendente"},
    ]


def test_totais_por_vencimento_e_por_pagamento():
    pix = [{"id": 1, "recebedor": "João Frete", "valor": 150, "vencimento": date(2026, 9, 20), "status": "Pago",
            "data_pagamento": date(2026, 9, 16), "tipo_chave": "celular", "chave": "+5565999990000", "centro_custo": "Obras"}]
    f = fechamento.montar(_boletos(), pix, SETEMBRO, "vencimento", hoje=HOJE)
    t = f["totais"]
    assert (t["total"], t["pago"], t["em_aberto"], t["atrasado"]) == (2730.5, 630.5, 2100.0, 100.0)
    assert (t["quantidade"], t["boletos"], t["pix"], t["cancelados"], t["com_comprovante"], t["sem_comprovante"]) == (4, 3, 1, 1, 1, 1)
    assert [c["centro_custo"] for c in f["por_centro"]] == ["Administrativo", "Energia", "Obras", fechamento.SEM_CENTRO]
    assert f["titulo"] == "setembro de 2026"

    pagamentos = fechamento.montar(_boletos(), pix, SETEMBRO, "pagamento", hoje=HOJE)
    assert [i["nome"] for i in pagamentos["pagos"]] == ["Agosto pago em setembro", "Energisa", "João Frete"]
    assert pagamentos["totais"]["em_aberto"] == 0

    with open_xlsx(fechamento.gerar_xlsx(f)) as wb:
        assert wb.sheetnames == ["Resumo", "Pagos", "Em aberto", "Cancelados"]
        assert wb["Resumo"]["B5"].value == 630.5
    pdf = fechamento.gerar_pdf(f)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500


class open_xlsx:
    def __init__(self, dados):
        self.wb = load_workbook(io.BytesIO(dados))

    def __enter__(self):
        return self.wb

    def __exit__(self, *_):
        self.wb.close()


def test_zip_para_o_contador_com_comprovantes(tmp_path):
    comprovante = tmp_path / "x.pdf"
    comprovante.write_bytes(b"%PDF comprovante")
    f = fechamento.montar(_boletos(), [], SETEMBRO, "vencimento", hoje=HOJE)
    dados = fechamento.gerar_zip(f, lambda item: comprovante if item["comprovante"] else None)
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        nomes = z.namelist()
        assert {"fechamento-2026-09.pdf", "fechamento-2026-09.xlsx", "comprovantes/2026-09-09_Energisa_480,50.pdf"} <= set(nomes)
        assert "Agosto" not in " ".join(nomes)
    sem = fechamento.montar(_boletos(), [], SETEMBRO, "pagamento", hoje=HOJE)
    with zipfile.ZipFile(io.BytesIO(fechamento.gerar_zip(sem, lambda item: None))) as z:
        assert "Agosto pago em setembro" in z.read("comprovantes/SEM-COMPROVANTE.txt").decode("utf-8")


def test_api_do_fechamento(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    hoje = date.today()
    planilha.adicionar({"beneficiario": "Internet", "valor": 99.9, "vencimento": hoje.replace(day=1) + timedelta(days=3),
                        "status": "Pago", "data_pagamento": hoje}, usuario="Ana")
    with TestClient(main.app) as c:
        dados = c.get("/api/relatorios/fechamento").json()
        assert dados["mes"] == hoje.strftime("%Y-%m") and dados["totais"]["pago"] == 99.9 and dados["pagos"][0]["pago_por"] == "Ana"
        assert c.get("/api/relatorios/fechamento", params={"mes": "2026-13"}).status_code == 422
        for formato, tipo in (("pdf", "application/pdf"), ("xlsx", "spreadsheet"), ("zip", "application/zip")):
            resposta = c.get("/api/relatorios/fechamento/arquivo", params={"formato": formato})
            assert resposta.status_code == 200 and tipo in resposta.headers["content-type"]
            assert f"fechamento-{hoje:%Y-%m}.{formato}" in resposta.headers["content-disposition"]
```

## `tests/test_gravacao.py` (65 linhas)

```python
"""Fila de gravação: planilha aberta no Excel não perde lançamentos nem alterações."""

from datetime import date

from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBloqueadaError, PlanilhaBoletos
from app.repositorio import RepositorioBoletos


class Trava:
    """Simula a planilha aberta no Excel enquanto ``ativa`` for verdadeiro."""

    def __init__(self, planilha: PlanilhaBoletos, monkeypatch):
        self.ativa = True
        original = planilha._verificar_gravavel

        def verificar():
            if self.ativa:
                raise PlanilhaBloqueadaError("A planilha está aberta em outro programa (ex.: Excel).")
            original()

        monkeypatch.setattr(planilha, "_verificar_gravavel", verificar)


def _montar(tmp_path):
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    return planilha, fila, RepositorioBoletos(planilha, fila)


def test_lancamentos_e_alteracoes_aguardam_e_sao_gravados_ao_fechar_o_excel(tmp_path, monkeypatch):
    planilha, fila, repositorio = _montar(tmp_path)
    repositorio.adicionar({"beneficiario": "Já gravado", "valor": 5})
    trava = Trava(planilha, monkeypatch)

    registro, pendente = repositorio.adicionar({"beneficiario": "Novo", "valor": 10, "vencimento": date(2026, 10, 1),
                                                "codigo_barras": "123"})
    assert pendente and registro["id"] == -1 and registro["pendente_gravacao"]
    assert repositorio.buscar_por_codigo("123")[0]["id"] == -1  # duplicidade considera a fila

    repositorio.atualizar(-1, {"observacoes": "editado antes de gravar"})
    atualizado, pendente = repositorio.atualizar(1, {"status": "Pago"})
    assert pendente and atualizado["status"] == "Pago"
    assert {r["id"] for r in repositorio.listar()} == {1, -1}

    assert fila.processar()["bloqueada"] and fila.pendentes == 2
    assert FilaGravacao(planilha, tmp_path / "fila.json").pendentes == 2  # sobrevive a reinício do sistema

    trava.ativa = False
    resultado = fila.processar()
    assert resultado["gravados"] == 2 and resultado["ids"] == {-1: 2} and fila.pendentes == 0
    registros = {r["id"]: r for r in planilha.listar()}
    assert registros[1]["status"] == "Pago"
    assert registros[2]["beneficiario"] == "Novo"
    assert registros[2]["observacoes"] == "editado antes de gravar"
    assert registros[2]["vencimento"] == date(2026, 10, 1)


def test_cancelar_lancamento_que_aguarda_gravacao(tmp_path, monkeypatch):
    planilha, fila, repositorio = _montar(tmp_path)
    planilha.garantir()
    Trava(planilha, monkeypatch)
    registro, _ = repositorio.adicionar({"beneficiario": "X"})
    repositorio.excluir(registro["id"])
    assert fila.pendentes == 0 and repositorio.listar() == []
```

## `tests/test_harmonizacao.py` (46 linhas)

```python
"""Nome do beneficiário pelo CPF/CNPJ: histórico da planilha e consenso dentro do arquivo."""

from app.boleto.extrator import harmonizar_beneficiarios
from app.planilha import PlanilhaBoletos

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
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    planilha.adicionar({"beneficiario": "Hiper JN Materiais para Construção", "documento_beneficiario": CNPJ})
    boletos = [_boleto("NIPER 3N-COMERCIO LTDA"), _boleto(None)]
    harmonizar_beneficiarios(boletos, planilha)
    for b in boletos:
        assert b["campos"]["beneficiario"] == {"valor": "Hiper JN Materiais para Construção", "fonte": "historico", "confianca": 0.97}
        assert not any(a["codigo"] == "ausente_beneficiario" for a in b["alertas"])
        assert b["confianca"] == 0.97
```

## `tests/test_ia.py` (83 linhas)

```python
"""Integração com IA usando um cliente Anthropic simulado (sem rede)."""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import ia
from app.boleto.codigo import formatar_linha
from app.main import app
from conftest import VALOR, VENCIMENTO


class ClienteFalso:
    ultima_chamada: dict = {}
    resposta: dict = {}
    stop_reason = "end_turn"

    def __init__(self, **kwargs):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._criar))

    def _criar(self, **kwargs):
        ClienteFalso.ultima_chamada = kwargs
        bloco = SimpleNamespace(type="text", text=json.dumps(ClienteFalso.resposta))
        return SimpleNamespace(stop_reason=ClienteFalso.stop_reason, content=[bloco])


@pytest.fixture()
def ia_simulada(monkeypatch):
    import anthropic

    monkeypatch.setenv("ANTHROPIC_API_KEY", "teste")
    monkeypatch.setattr(anthropic, "Anthropic", ClienteFalso)
    ClienteFalso.stop_reason = "end_turn"
    return ClienteFalso


def test_extrair_monta_pedido_e_le_json(ia_simulada, boleto_pdf):
    ia_simulada.resposta = {"linha_digitavel": "123", "beneficiario": "X", "documento_beneficiario": "",
                            "numero_documento": "", "vencimento": "", "valor": "", "observacoes": ""}
    dados = ia.extrair(boleto_pdf[0].read_bytes())
    assert dados["beneficiario"] == "X"
    chamada = ia_simulada.ultima_chamada
    assert chamada["model"] == "claude-opus-5"
    assert chamada["output_config"]["format"]["type"] == "json_schema"
    assert chamada["fallbacks"] == "default"
    assert chamada["messages"][0]["content"][0]["type"] == "document"


def test_recusa_vira_erro(ia_simulada, boleto_pdf):
    ia_simulada.stop_reason = "refusal"
    with pytest.raises(ia.ErroIA):
        ia.extrair(boleto_pdf[0].read_bytes())


def test_endpoint_mescla_e_valida_linha_da_ia(ia_simulada, boleto_pdf):
    caminho, linha = boleto_pdf
    # A IA erra um dígito: o sistema deve corrigir pelos DVs em vez de aceitar às cegas
    errada = linha[:15] + str((int(linha[15]) + 1) % 10) + linha[16:]
    ia_simulada.resposta = {
        "linha_digitavel": errada, "beneficiario": "Empresa Exemplo de Serviços Ltda",
        "documento_beneficiario": "12.345.678/0001-95", "numero_documento": "NF-2026/0457",
        "vencimento": VENCIMENTO.isoformat(), "valor": str(VALOR), "observacoes": "",
    }
    with TestClient(app) as cliente:
        with open(caminho, "rb") as f:
            leitura = cliente.post("/api/leituras", files={"arquivo": ("b.pdf", f, "application/pdf")}).json()
        resp = cliente.post(f"/api/leituras/{leitura['arquivo']['id']}/ia", json={"campos": {}, "pagina": 0})
    assert resp.status_code == 200, resp.text
    boleto = resp.json()
    assert boleto["ia_usada"]
    campos = boleto["campos"]
    assert campos["beneficiario"]["fonte"] == "ia"
    assert campos["valor"]["valor"] == float(VALOR)
    # O boleto de exemplo vence "hoje + 26 dias": conforme a data, um dígito errado tem uma ou várias correções possíveis
    codigo = boleto["codigo"] or {}
    if campos.get("linha_digitavel", {}).get("valor") == formatar_linha(linha):
        assert codigo["valido"]  # corrigida sozinha pelos dígitos verificadores
    elif not codigo.get("corrigido"):
        # correção ambígua: a linha errada da IA não é aceita e a certa aparece entre as sugestões
        assert not codigo.get("valido")
        assert formatar_linha(linha) in boleto["sugestoes_linha"]
```

## `tests/test_importacao.py` (160 linhas)

```python
"""Importação de boletos exportados de outros sistemas (CSV, Excel e ".xls" em HTML)."""

import io
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app import admin, contexto, importacao, main
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos
from gerar_boleto_exemplo import montar_codigo

VENC = date.today() + timedelta(days=10)


def _linha(valor: str, campo_livre: str, vencimento: date = VENC) -> str:
    return montar_codigo("237", vencimento, Decimal(valor), campo_livre)[1]


def _csv() -> bytes:
    venc = f"{VENC:%d/%m/%Y}"
    linhas = [
        "Relatório de contas a pagar;;;;;;;",
        "Fornecedor;CNPJ;Nº Documento;Vencto;Valor Título;Linha Digitável;Situação;C. Custo",
        f"Posto Central Ltda;02359273000152;NF 1001;{venc};150,00;{_linha('150.00', '1' * 25)};Em aberto;Combustível e Veículos",
        f"Energia MT;;FAT-77;{venc};R$ 1.234,56;;Liquidado;",
        f"Loja X;;123;{venc};99,00;12345;Em aberto;",
        f"Oficina Y;;OS-9;{venc};85,00;{_linha('80.00', '2' * 25)};Em aberto;",
        f"Posto Central Ltda;02359273000152;NF 1001;{venc};150,00;{_linha('150.00', '1' * 25)};Em aberto;",
        ";;;;1.619,56;;;",
    ]
    return "\n".join(linhas).encode("cp1252")


def test_conversao_de_valores_datas_e_situacao():
    assert importacao.ler_valor("1.234,56") == 1234.56
    assert importacao.ler_valor("R$ 1,234.56") == 1234.56
    assert importacao.ler_valor("360,00") == 360.0
    assert importacao.ler_valor("(10,50)") == 10.5
    assert importacao.ler_valor("1.500") == 1500.0
    assert importacao.ler_valor(1500) == 1500.0
    assert importacao.ler_valor("abc") is None
    assert importacao.ler_data("15/09/2026") == date(2026, 9, 15)
    assert importacao.ler_data("15.09.26") == date(2026, 9, 15)
    assert importacao.ler_data("2026-09-15 00:00:00") == date(2026, 9, 15)
    assert importacao.ler_data("15-set-2026") == date(2026, 9, 15)
    assert importacao.ler_data(datetime(2026, 9, 15, 10, 30)) == date(2026, 9, 15)
    assert importacao.ler_data(46280) == date(1899, 12, 30) + timedelta(days=46280)
    assert importacao.ler_status("Liquidado") == "Pago"
    assert importacao.ler_status("Em aberto", "Pago") == "Pendente"
    assert importacao.ler_status("A pagar") == "Pendente"
    assert importacao.ler_status("Cancelado") == "Cancelado"
    assert importacao.ler_status("", "Pago") == "Pago"


def test_reconhece_colunas_e_confere_as_linhas_de_um_csv():
    formato, abas = importacao.ler_planilhas(_csv(), "contas.csv")
    tabela = importacao.montar_tabela(abas)
    assert formato == "csv" and tabela["linha_cabecalho"] == 2
    mapa = importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"])
    assert mapa == {"linha_digitavel": 5, "beneficiario": 0, "documento_beneficiario": 1, "numero_documento": 2,
                    "vencimento": 3, "valor": 4, "status": 6, "data_pagamento": None, "centro_custo": 7, "observacoes": None}

    itens = importacao.preparar(tabela, mapa, existentes=[], nome_arquivo="contas.csv")
    assert [i["estado"] for i in itens] == ["pronto", "aviso", "erro", "aviso", "repetido"]  # linha de total ignorada
    posto, energia, loja, oficina, repetido = itens
    assert posto["dados"]["documento_beneficiario"] == "02.359.273/0001-52" and posto["dados"]["codigo_barras"]
    assert posto["dados"]["centro_custo"] == "Combustível e Veículos" and posto["dados"]["vencimento"] == VENC
    assert energia["dados"]["status"] == "Pago" and energia["dados"]["valor"] == 1234.56 and energia["dados"]["data_pagamento"] == VENC
    assert "5 dígitos" in loja["mensagens"][0]
    assert any("diferente do código" in m for m in oficina["mensagens"]) and oficina["dados"]["valor"] == 85.0
    assert "linha 3" in repetido["mensagens"][0]


def test_planilha_excel_com_titulo_acima_das_colunas():
    wb = Workbook()
    ws = wb.active
    ws.title = "Contas a Pagar"
    ws.append(["Empresa Exemplo"])
    ws.append([None])
    ws.append(["Data de Vencimento", "Favorecido", "Valor", "Código de Barras", "Centro de Custo", "Data Pagamento"])
    barras = montar_codigo("001", date(2026, 10, 1), Decimal("250.40"), "5" * 25)[0]
    ws.append([datetime(2026, 10, 1), "Fornecedor A", 250.4, barras, "Obras", None])
    ws.append([datetime(2026, 10, 5), "Fornecedor B", 99.9, None, None, datetime(2026, 10, 4)])
    wb.create_sheet("Resumo").append(["Total", 350.3])
    buffer = io.BytesIO()
    wb.save(buffer)

    formato, abas = importacao.ler_planilhas(buffer.getvalue(), "contas.xlsx")
    tabela = importacao.montar_tabela(abas)
    assert formato == "xlsx" and tabela["aba"] == "Contas a Pagar" and tabela["linha_cabecalho"] == 3
    mapa = importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"])
    assert (mapa["vencimento"], mapa["beneficiario"], mapa["valor"], mapa["linha_digitavel"], mapa["centro_custo"],
            mapa["data_pagamento"]) == (0, 1, 2, 3, 4, 5)
    a, b = importacao.preparar(tabela, mapa, existentes=[])
    assert a["estado"] == "pronto" and a["dados"]["linha_digitavel"].startswith("0019") and a["dados"]["vencimento"] == date(2026, 10, 1)
    assert b["dados"]["status"] == "Pago" and b["dados"]["data_pagamento"] == date(2026, 10, 4)


def test_xls_gerado_em_html_por_outros_sistemas():
    html = ("<html><body><table><tr><th>Beneficiário</th><th>Vencimento</th><th>Valor</th></tr>"
            "<tr><td>Água &amp; Esgoto</td><td>20/10/2026</td><td>45,90</td></tr></table></body></html>").encode("cp1252")
    formato, abas = importacao.ler_planilhas(html, "relatorio.xls")
    tabela = importacao.montar_tabela(abas)
    [item] = importacao.preparar(tabela, importacao.sugerir_mapeamento(tabela["colunas"], tabela["linhas"]), existentes=[])
    assert formato == "html" and item["dados"]["beneficiario"] == "Água & Esgoto" and item["dados"]["valor"] == 45.9
    with pytest.raises(importacao.ErroImportacao):
        importacao.ler_planilhas(b"%PDF-1.7 ...", "boleto.pdf")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "importacoes", importacao.ArmazemImportacoes(tmp_path / "importacoes"))
    monkeypatch.setattr(contexto, "modelos_importacao", importacao.ModelosMapeamento(tmp_path / "modelos.json"))
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    with TestClient(main.app) as c:
        yield c


def test_importacao_pela_api(cliente):
    envio = {"arquivo": ("contas.csv", _csv(), "text/csv")}
    assert cliente.post("/api/importacao", files=envio).json()["detail"]["codigo"] == "admin_sem_senha"
    assert cliente.post("/api/admin/senha", json={"senha": "senha-admin", "confirmacao": "senha-admin"}).json()["autorizado"]
    resposta = cliente.post("/api/importacao", files={"arquivo": ("contas.csv", _csv(), "text/csv")})
    assert resposta.status_code == 201, resposta.text
    sessao = resposta.json()
    assert sessao["resumo"]["pronto"] == 1 and sessao["resumo"]["erro"] == 1 and not sessao["mapeamento_salvo"]
    validos = [i["indice"] for i in sessao["itens"] if i["estado"] in ("pronto", "aviso")]
    corpo = {"aba": sessao["aba"], "linha_cabecalho": sessao["linha_cabecalho"], "mapeamento": sessao["mapeamento"],
             "centro_custo": "Administrativo", "indices": validos + [2]}  # a linha com erro é ignorada
    feito = cliente.post(f"/api/importacao/{sessao['id']}/importar", json=corpo).json()
    assert feito["importados"] == 3 and feito["ignorados"] == 1 and not feito["pendente_gravacao"]

    boletos = cliente.get("/api/boletos", params={"por_pagina": 0}).json()["itens"]
    assert {b["beneficiario"] for b in boletos} == {"Posto Central Ltda", "Energia MT", "Oficina Y"}
    assert {b["centro_custo"] for b in boletos} == {"Combustível e Veículos", "Administrativo"}
    aba = load_workbook(contexto.planilha.caminho)["Boletos"]
    coluna = [c.value for c in aba[1]].index("Nome do Arquivo Original") + 1
    assert aba.cell(row=2, column=coluna).value == "Importado de contas.csv"

    # Segunda importação do mesmo arquivo: colunas lembradas e boletos marcados como já lançados
    sessao2 = cliente.post("/api/importacao", files={"arquivo": ("contas.csv", _csv(), "text/csv")}).json()
    assert sessao2["mapeamento_salvo"] and sessao2["resumo"]["duplicado"] == 4 and sessao2["resumo"]["pronto"] == 0
    previa = cliente.post(f"/api/importacao/{sessao2['id']}/previa", json={"mapeamento": {**sessao2["mapeamento"], "centro_custo": None}})
    assert previa.json()["mapeamento"]["centro_custo"] is None

    assert cliente.post("/api/importacao/" + "0" * 32 + "/previa", json={}).status_code == 404
    assert cliente.post("/api/importacao", files={"arquivo": ("boleto.pdf", b"%PDF-1.7", "application/pdf")}).status_code == 422
    modelo = cliente.get("/api/importacao/modelo.xlsx")
    assert modelo.status_code == 200 and load_workbook(io.BytesIO(modelo.content)).active["A1"].value == "Linha digitável"
```

## `tests/test_juros_visiveis.py` (32 linhas)

```python
"""Juros e multas pagos aparecem nos totais das listas, no Painel e em Gastos."""

from datetime import date, datetime

from app import servicos

HOJE = date(2026, 9, 24)


def _boleto(id_, valor, juros=0.0, status="Pago", pago=date(2026, 9, 21), venc=date(2026, 9, 10)):
    return {"id": id_, "beneficiario": f"Fornecedor {id_}", "valor": valor, "status": status, "vencimento": venc,
            "data_pagamento": pago if status == "Pago" else None, "valor_pago": valor + juros if status == "Pago" else None,
            "juros_multa": juros, "centro_custo": "Manutenção", "data_lancamento": datetime(2026, 9, 1, 8, 0)}


REGISTROS = [_boleto(1, 900, 56.70), _boleto(2, 900, 30.60), _boleto(3, 210, 0.0), _boleto(4, 500, status="Pendente"),
             {**_boleto(5, 300, 12.0), "status": "Cancelado"}]


def test_resumo_da_lista_soma_os_juros_dos_pagos():
    r = servicos.resumir(REGISTROS, HOJE)
    assert r["juros_multa"] == 87.30 and r["pagos_com_juros"] == 2


def test_painel_mostra_os_juros_pagos_no_mes():
    k = servicos.painel(REGISTROS, HOJE)["indicadores"]
    assert k["juros_mes_valor"] == 87.30 and k["juros_mes_qtd"] == 2


def test_gastos_mostra_os_juros_do_periodo():
    d = servicos.analise_gastos(REGISTROS, [], hoje=HOJE)
    assert d["juros_multa"] == 87.30 and d["pagos_com_juros"] == 2
```

## `tests/test_notificacoes.py` (213 linhas)

```python
"""Lembretes de vencimento: regras, mensagens, agendador (dia do vencimento 3x), agenda, configuração e API."""

import json
from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from app import inicializacao
from app.notificacoes import canais
from app.notificacoes.regras import alertas_da_regra, montar_alertas, montar_mensagem
from app.notificacoes.servico import MASCARA, ServicoNotificacoes
from app.planilha import PlanilhaBoletos

SEGUNDA = date(2026, 9, 14)
HOJE = date.today()


def _registro(id_, dias, status="Pendente", nome=None, valor=100.0):
    return {"id": id_, "beneficiario": nome or f"Empresa {id_}", "vencimento": SEGUNDA + timedelta(days=dias),
            "valor": valor, "status": status, "numero_documento": f"DOC{id_}", "linha_digitavel": "0019 0500"}


def _as(hora: str) -> datetime:
    return datetime.combine(HOJE, time.fromisoformat(hora))


# --------------------------------------------------------------------------- regras e mensagens


def test_regras_de_alerta():
    registros = [_registro(1, 3), _registro(2, -2), _registro(3, 0), _registro(4, 1), _registro(5, 9),
                 _registro(6, 0, status="Pago"), {**_registro(7, 0), "vencimento": None}, _registro(8, -40)]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencimento"})] == [3]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "antes", "dias": 3})] == [1]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencidos", "dias": 30})] == [2]
    assert [a["id"] for a in alertas_da_regra(registros, SEGUNDA, {"tipo": "vencidos", "dias": 0})] == [8, 2]
    assert montar_alertas([_registro(9, 5)], SEGUNDA, dias_antes=5)[0]["fim_de_semana"]


def test_mensagem_lista_os_boletos_e_numero_do_lembrete():
    alertas = montar_alertas([_registro(1, 1, nome="HIPER <JN>"), _registro(2, -1)], SEGUNDA, 3)
    mensagem = montar_mensagem(alertas, SEGUNDA, "http://localhost:8000")
    assert mensagem.titulo == "1 boleto a vencer e 1 vencido"
    assert "HIPER <JN>" in mensagem.texto and "HIPER &lt;JN&gt;" in mensagem.telegram
    hoje = [{**montar_alertas([_registro(3, 0)], SEGUNDA, 0)[0], "lembrete": "2/3"}]
    unico = montar_mensagem(hoje, SEGUNDA, "http://x")
    assert unico.titulo == "Boleto vence hoje · lembrete 2/3"
    assert unico.itens[0][2] == 3  # id do boleto (botão "Já paguei")


# --------------------------------------------------------------------------- agendador


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    enviados = []
    monkeypatch.setattr(canais, "enviar_windows",
                        lambda titulo, corpo, url=None, url_pago=None: enviados.append((titulo, corpo, url_pago)))
    servico = ServicoNotificacoes(planilha, tmp_path / "notificacoes.json", "http://localhost:8000")
    return planilha, servico, enviados


def _somente_dia_do_vencimento(servico, horarios=("08:00", "12:00", "16:00")):
    servico.atualizar_config({"regras": [{"tipo": "vencimento", "horarios": list(horarios), "canais": ["windows"]}]})


def test_tres_lembretes_no_dia_do_vencimento(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    boleto = planilha.adicionar({"beneficiario": "HIPER JN", "vencimento": HOJE, "valor": 360})
    planilha.adicionar({"beneficiario": "Outro", "vencimento": HOJE + timedelta(days=1), "valor": 10})

    assert servico.verificar(_as("07:59")) is None
    assert servico.verificar(_as("08:00"))["quantidade"] == 1
    assert enviados[-1][0] == "Boleto vence hoje · lembrete 1/3"
    assert enviados[-1][2] == f"http://localhost:8000/#/boletos?pagar={boleto['id']}"
    assert servico.verificar(_as("09:30")) is None  # mesmo horário já avisado
    assert servico.verificar(_as("12:01"))["quantidade"] == 1
    assert enviados[-1][0].endswith("lembrete 2/3")
    assert servico.verificar(_as("16:00"))["quantidade"] == 1
    assert enviados[-1][0].endswith("lembrete 3/3")
    assert servico.verificar(_as("20:00")) is None
    assert len(enviados) == 3


def test_pago_encerra_os_lembretes(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    boleto = planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 1})
    servico.verificar(_as("08:05"))
    planilha.atualizar(boleto["id"], {"status": "Pago"})
    assert servico.verificar(_as("12:05")) is None
    assert len(enviados) == 1


def test_sistema_ligado_tarde_envia_so_o_horario_mais_recente(ambiente):
    planilha, servico, enviados = ambiente
    _somente_dia_do_vencimento(servico)
    planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 1})
    resultado = servico.verificar(_as("15:00"))
    assert resultado["quantidade"] == 1 and len(enviados) == 1 and enviados[0][0].endswith("lembrete 2/3")
    assert servico.verificar(_as("15:30")) is None
    servico.verificar(_as("16:00"))
    assert enviados[-1][0].endswith("lembrete 3/3")


def test_regras_antes_vencidos_canais_e_dias_da_semana(ambiente):
    planilha, servico, enviados = ambiente
    servico.atualizar_config({"regras": [
        {"tipo": "antes", "dias": 2, "horarios": ["09:00"], "canais": ["windows"]},
        {"tipo": "vencidos", "dias": 0, "horarios": ["10:00"], "canais": ["telegram"]},  # Telegram desligado
    ]})
    planilha.adicionar({"beneficiario": "Daqui 2 dias", "vencimento": HOJE + timedelta(days=2), "valor": 1})
    planilha.adicionar({"beneficiario": "Vencido", "vencimento": HOJE - timedelta(days=4), "valor": 1})
    resultado = servico.verificar(_as("11:00"))
    assert resultado["quantidade"] == 1 and "Daqui 2 dias" in enviados[0][1]

    outros_dias = [d for d in range(7) if d != HOJE.weekday()]
    servico.atualizar_config({"dias_semana": outros_dias, "regras": [{"tipo": "antes", "dias": 1, "horarios": ["09:00"], "canais": ["windows"]}]})
    planilha.adicionar({"beneficiario": "Amanhã", "vencimento": HOJE + timedelta(days=1), "valor": 1})
    assert servico.verificar(_as("12:00")) is None


def test_falha_em_todos_os_canais_tenta_de_novo_depois(ambiente, monkeypatch):
    planilha, servico, _ = ambiente
    _somente_dia_do_vencimento(servico, ["08:00"])
    planilha.adicionar({"beneficiario": "A", "vencimento": HOJE, "valor": 10})

    def falhar(*_args, **_kwargs):
        raise canais.ErroCanal("sem permissão")

    monkeypatch.setattr(canais, "enviar_windows", falhar)
    resultado = servico.verificar(_as("09:00"))
    assert not resultado["enviado"] and resultado["canais"]["windows"].startswith("erro")
    assert servico.verificar(_as("09:10")) is None
    assert servico.verificar(_as("09:16")) is not None


def test_agenda_mostra_os_proximos_lembretes(ambiente):
    planilha, servico, _ = ambiente
    _somente_dia_do_vencimento(servico)
    planilha.adicionar({"beneficiario": "Amanhã", "vencimento": HOJE + timedelta(days=1), "valor": 50})
    agenda = servico.agenda(_as("10:00"))
    assert [item["quando"][11:] for item in agenda] == ["08:00", "12:00", "16:00"]
    assert agenda[1]["lembrete"] == "2/3" and agenda[0]["boletos"][0]["beneficiario"] == "Amanhã"


# --------------------------------------------------------------------------- configuração


def test_configuracao_valida_regras_e_mascara_segredos(ambiente):
    _, servico, _ = ambiente
    publica = servico.config_publica()
    assert publica["regras"][0]["horarios"] == ["08:00", "12:00", "16:00"]  # padrão: 3x no dia
    publica = servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "chat_id": "42"}})
    assert publica["telegram"]["token"] == MASCARA
    servico.atualizar_config({"telegram": {"token": MASCARA}})
    assert servico.segredo("telegram", "token") == "123:abc"

    salvo = servico.atualizar_config({"regras": [{"tipo": "vencimento", "horarios": ["16:00", "8:00", "08:00"], "canais": ["windows"]}]})
    assert salvo["regras"][0]["horarios"] == ["08:00", "16:00"]
    for invalida in ({"tipo": "vencimento", "horarios": ["25:00"]}, {"tipo": "vencimento", "horarios": []},
                     {"tipo": "antes", "dias": 0, "horarios": ["09:00"]}):
        with pytest.raises(ValueError):
            servico.atualizar_config({"regras": [invalida]})
    with pytest.raises(ValueError):
        servico.atualizar_config({"dias_semana": []})


def test_migra_configuracao_da_versao_anterior(tmp_path):
    caminho = tmp_path / "notificacoes.json"
    caminho.write_text(json.dumps({"ativo": True, "horario": "07:30", "dias_antes": 5, "avisar_vencidos": False,
                                   "windows": {"ativo": True}}), encoding="utf-8")
    servico = ServicoNotificacoes(PlanilhaBoletos(tmp_path / "b.xlsx"), caminho, "http://x")
    regras = {r["id"]: r for r in servico.config_publica()["regras"]}
    assert regras["vencimento"]["horarios"] == ["07:30", "12:00", "16:00"]
    assert regras["antecedencia"]["dias"] == 5 and regras["antecedencia"]["horarios"] == ["07:30"]
    assert regras["vencidos"]["ativo"] is False


def test_enviar_agora_e_teste(ambiente):
    planilha, servico, enviados = ambiente
    assert servico.enviar_agora()["enviado"] is False
    for i in range(5):
        planilha.adicionar({"beneficiario": f"E{i}", "vencimento": HOJE, "valor": 1})
    assert servico.enviar_agora()["enviado"] and len(enviados) == 1  # mais de 3: uma notificação-resumo
    assert servico.testar("windows")["canais"] == {"windows": "ok"}


def test_inicializacao_com_windows(tmp_path):
    assert inicializacao.ativar(tmp_path)["ativo"]
    conteudo = (tmp_path / inicializacao.NOME_ARQUIVO).read_text(encoding="utf-16")
    assert "-m app" in conteudo and "LEITOR_ABRIR_NAVEGADOR" in conteudo
    assert "--bandeja" not in conteudo and "\r\n\r\n" not in conteudo
    assert inicializacao.ativar(tmp_path, minimizado=True)["minimizado"]
    assert not inicializacao.desativar(tmp_path)["ativo"]


def test_api_de_notificacoes(monkeypatch):
    from app.main import app

    monkeypatch.setattr(canais, "enviar_windows", lambda *a, **k: None)
    with TestClient(app) as cliente:
        dados = cliente.get("/api/notificacoes").json()
        assert {"alertas", "agenda", "config", "historico", "janela_dias"} <= dados.keys()
        regras = [{"tipo": "vencimento", "horarios": ["07:00", "11:00", "17:30"], "canais": ["windows"]}]
        assert cliente.put("/api/notificacoes/config", json={"regras": [{"tipo": "vencimento", "horarios": ["99:00"]}]}).status_code == 422
        salvo = cliente.put("/api/notificacoes/config", json={"regras": regras, "email": {"senha": "segredo"}}).json()
        assert salvo["regras"][0]["horarios"] == ["07:00", "11:00", "17:30"] and salvo["email"]["senha"] == MASCARA
        assert cliente.post("/api/notificacoes/testar", json={"canal": "windows"}).json()["enviado"]
        assert "ativo" in cliente.get("/api/sistema/inicializacao").json()
```

## `tests/test_permissoes.py` (197 linhas)

```python
"""Administrador por usuário, permissões por pessoa e login pedido toda vez que o aplicativo abre."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import acesso, admin, contexto, main, usuarios
from app.arquivos import RepositorioArquivos
from app.banco import BancoBoletos
from app.empresas.configuracao import ConfigEmpresas
from app.empresas.modelos import ABAS_EMPRESAS
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    gerenciador = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json")
    empresas = BancoBoletos(tmp_path / "empresas.db", tmp_path / "fechamentos.xlsx", tmp_path / "backups",
                            abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
    original = contexto.usuarios
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    monkeypatch.setattr(contexto, "usuarios", gerenciador)
    monkeypatch.setattr(contexto, "empresas", empresas)
    monkeypatch.setattr(contexto, "empresas_config", ConfigEmpresas(tmp_path / "empresas.json"))
    acesso.configurar_usuarios(gerenciador)
    yield gerenciador
    acesso.configurar_usuarios(original)
    empresas.parar()


def _entrar(cliente, login, senha):
    resposta = cliente.post("/api/usuarios/entrar", json={"login": login, "senha": senha})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["usuario"]


def _boleto(cliente):
    return cliente.post("/api/boletos", json={"beneficiario": "Papelaria", "valor": 50,
                                              "vencimento": (date.today() + timedelta(days=5)).isoformat(),
                                              "ignorar_validacao": True})


# --------------------------------------------------------------------------- administrador


def test_administrador_entra_e_cadastra_sem_a_senha_de_administrador(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        assert celular.get("/api/usuarios").status_code == 401  # ainda não entrou
        usuario = _entrar(celular, "fabio", "senha-do-dono")
        assert usuario["perfil"] == "administrador" and "config" in usuario["permissoes"]

        assert celular.get("/api/usuarios").status_code == 200
        criado = celular.post("/api/usuarios", json={"nome": "Almir", "login": "almir", "senha": "almir-2026",
                                                     "permissoes": ["lancar", "pagar"]})
        assert criado.status_code == 201
        assert criado.json()["criado"]["perfil"] == "comum"
        assert criado.json()["criado"]["permissoes"] == ["lancar", "pagar"]
        assert _boleto(celular).status_code == 201  # administrador pode tudo


def test_nao_deixa_ficar_sem_administrador(sistema):
    admin_id = sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")["id"]
    with pytest.raises(usuarios.ErroUsuario):
        sistema.alterar(admin_id, perfil="comum")
    with pytest.raises(usuarios.ErroUsuario):
        sistema.alterar(admin_id, ativo=False)
    with pytest.raises(usuarios.ErroUsuario):
        sistema.excluir(admin_id)

    outro = sistema.criar("Ana", "ana", "ana-2026", "administrador")["id"]
    sistema.alterar(admin_id, perfil="comum")  # agora tem outro administrador
    assert sistema.listar()[0]["perfil"] in ("administrador", "comum")
    assert sistema.tem_administrador and sistema.publico(sistema._obter(outro))["perfil"] == "administrador"


# --------------------------------------------------------------------------- permissões


def test_usuario_comum_so_faz_o_que_foi_liberado(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Almir", "almir", "almir-2026", "comum", ["lancar", "pagar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "almir", "almir-2026")

        # pode lançar e dar baixa
        boleto = _boleto(celular)
        assert boleto.status_code == 201
        id_ = boleto.json()["id"]
        assert celular.patch(f"/api/boletos/{id_}/status", json={"status": "Pago"}).status_code == 200

        # não pode editar nem excluir
        assert celular.put(f"/api/boletos/{id_}", json={"observacoes": "teste"}).status_code == 403
        excluir = celular.delete(f"/api/boletos/{id_}")
        assert excluir.status_code == 403 and excluir.json()["detail"]["codigo"] == "sem_permissao"

        # telas restritas
        assert celular.get("/api/gastos").status_code == 403
        assert celular.get("/api/empresas").status_code == 403
        assert celular.put("/api/notificacoes/config", json={"ativo": True}).status_code == 403
        assert celular.put("/api/backup/config", json={"ativo": False}).status_code == 403

        # o que é de todo mundo continua funcionando
        assert celular.get("/api/boletos").status_code == 200
        assert celular.get("/api/painel").status_code == 200
        assert celular.post("/api/notificacoes/dispensar", json={"chave": "x"}).status_code == 200

        # e não gerencia usuários
        recusado = celular.post("/api/usuarios", json={"nome": "Outro", "senha": "123456"})
        assert recusado.status_code == 403 and "administrador" in recusado.json()["detail"]["mensagem"]


def test_permissoes_extras_liberam_as_telas(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Bia", "bia", "bia-2026", "comum", ["gastos", "empresas", "editar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "bia", "bia-2026")
        assert celular.get("/api/gastos").status_code == 200
        assert celular.get("/api/empresas").status_code == 200
        assert celular.post("/api/empresas", json={"nome": "Imapal"}).status_code == 201
        assert _boleto(celular).status_code == 403  # não pode lançar


def test_estado_do_acesso_mostra_perfil_e_permissoes(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.criar("Almir", "almir", "almir-2026", "comum", ["lancar"])

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        _entrar(celular, "almir", "almir-2026")
        estado = celular.get("/api/acesso/estado").json()
        assert estado["usuario"]["perfil"] == "comum" and estado["usuario"]["permissoes"] == ["lancar"]
        assert estado["administrador"] is False and estado["tem_administrador"] is True


def test_usuarios_antigos_continuam_podendo_o_que_podiam(tmp_path):
    """Arquivo criado antes das permissões: ninguém perde acesso de uma hora para outra."""
    import json

    caminho = tmp_path / "usuarios.json"
    caminho.write_text(json.dumps({"usuarios": [{"id": "abc", "nome": "Almir", "login": "almir", "ativo": True,
                                                 "senha_hash": "x", "sal": "00"}]}), encoding="utf-8")
    gerenciador = usuarios.GerenciadorUsuarios(caminho)
    almir = gerenciador.listar()[0]
    assert almir["perfil"] == "comum"
    assert almir["permissoes"] == list(usuarios.PERMISSOES)  # tudo, menos gerenciar usuários


# --------------------------------------------------------------------------- login ao abrir o aplicativo


def test_ao_abrir_o_aplicativo_so_o_computador_precisa_entrar_de_novo(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)

    token_computador, _, _ = sistema.entrar("fabio", "senha-do-dono", "127.0.0.1", "janela", local=True)
    token_celular, _, _ = sistema.entrar("fabio", "senha-do-dono", "192.168.0.50", "celular", local=False)

    assert sistema.encerrar_sessoes_do_computador() == 1  # o aplicativo abriu de novo
    assert sistema.usuario_da_sessao(token_computador) is None
    assert sistema.usuario_da_sessao(token_celular)["login"] == "fabio"  # o celular continua conectado


def test_login_pedido_toda_vez_que_o_aplicativo_abre(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)
    assert sistema.exigir_login_no_computador and sistema.pedir_login_ao_abrir

    with TestClient(main.app, client=("127.0.0.1", 50000)) as computador:  # aplicativo aberto
        assert computador.get("/api/boletos").status_code == 401  # pede login mesmo no computador
        _entrar(computador, "fabio", "senha-do-dono")
        assert computador.get("/api/boletos").status_code == 200

    with TestClient(main.app, client=("127.0.0.1", 50000)):  # fechou e abriu de novo
        pass
    with TestClient(main.app, client=("127.0.0.1", 50000)) as depois:
        depois.cookies.update(computador.cookies)
        assert depois.get("/api/boletos").status_code == 401  # a sessão de antes não vale mais


def test_desligar_o_login_no_computador_desliga_o_pedido_ao_abrir(sistema):
    sistema.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    sistema.definir_pedir_login_ao_abrir(True)
    sistema.definir_exigir_login_no_computador(False)
    assert not sistema.pedir_login_ao_abrir and not sistema.exigir_login_no_computador
```

## `tests/test_pix.py` (59 linhas)

```python
"""Pix: validação das chaves e leitura/geração do Copia e Cola (inclusive por QR code em imagem)."""

import io

import pytest
import segno

from app.pix import (
    ErroPix,
    crc16,
    formatar_chave,
    gerar_copia_e_cola,
    inferir_tipo,
    ler_copia_e_cola,
    ler_pix_de_arquivo,
    normalizar_chave,
)


def test_validacao_das_chaves():
    assert normalizar_chave("cpf_cnpj", "123.456.789-09") == "12345678909"
    assert normalizar_chave("cpf_cnpj", "02.359.273/0001-52") == "02359273000152"
    with pytest.raises(ErroPix):
        normalizar_chave("cpf_cnpj", "123.456.789-00")
    assert normalizar_chave("celular", "(65) 99603-5105") == "+5565996035105"
    assert normalizar_chave("celular", "+55 65 99603-5105") == "+5565996035105"
    with pytest.raises(ErroPix):
        normalizar_chave("celular", "(65) 3241-4400")  # fixo, não é celular
    assert normalizar_chave("email", "Flavio@E-ConnectCon.com.br") == "flavio@e-connectcon.com.br"
    with pytest.raises(ErroPix):
        normalizar_chave("email", "sem-arroba.com")
    assert normalizar_chave("aleatoria", "123E4567-E89B-12D3-A456-426614174000") == "123e4567-e89b-12d3-a456-426614174000"
    assert formatar_chave("cpf_cnpj", "02359273000152") == "02.359.273/0001-52"
    assert formatar_chave("celular", "+5565996035105") == "(65) 99603-5105"
    assert inferir_tipo("+5565996035105") == "celular" and inferir_tipo("a@b.com") == "email"
    assert inferir_tipo("02359273000152") == "cpf_cnpj"


def test_gera_e_le_pix_copia_e_cola():
    payload = gerar_copia_e_cola("cpf_cnpj", "02.359.273/0001-52", 360.0, "Hiper JN Comércio de Materiais", "Mirassol D'Oeste",
                                 txid="NF672362", descricao="Pedido 2.295.455")
    assert payload.startswith("000201") and crc16(payload[:-4]) == payload[-4:]
    lido = ler_copia_e_cola(payload)
    assert lido["crc_valido"] and lido["tipo_chave"] == "cpf_cnpj" and lido["chave"] == "02359273000152"
    assert lido["valor"] == 360.0 and lido["recebedor"] == "HIPER JN COMERCIO DE MATE"  # nome limitado a 25 caracteres (padrão EMV)
    assert lido["txid"] == "NF672362" and lido["descricao"] == "Pedido 2.295.455"
    alterado = payload[:-1] + ("0" if payload[-1] != "0" else "1")
    assert not ler_copia_e_cola(alterado)["crc_valido"]
    with pytest.raises(ErroPix):
        ler_copia_e_cola("34191.09123 34567.812341")


def test_le_pix_de_uma_imagem_com_qr_code():
    payload = gerar_copia_e_cola("email", "financeiro@empresa.com.br", 125.5, "Empresa Teste")
    buffer = io.BytesIO()
    segno.make(payload, error="m").save(buffer, kind="png", scale=8, border=4)
    encontrados = ler_pix_de_arquivo(buffer.getvalue())
    assert len(encontrados) == 1
    assert encontrados[0]["chave"] == "financeiro@empresa.com.br" and encontrados[0]["valor"] == 125.5
```

## `tests/test_pix_centros_api.py` (211 linhas)

```python
"""Pix, centros de custo, análise de gastos e endpoints do aplicativo de desktop."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import contexto, janela, main
from app.fila_gravacao import FilaGravacao
from app.pix import gerar_copia_e_cola
from app.planilha import PlanilhaBoletos
from app.repositorio import FonteLembretes, RepositorioBoletos
from app.servicos import analise_gastos

from gerar_boleto_exemplo import montar_codigo


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(main.preferencias.config, "DADOS_DIR", tmp_path)
    with TestClient(main.app) as c:
        yield c


def test_lanca_edita_e_lista_pix(cliente):
    amanha = (date.today() + timedelta(days=1)).isoformat()
    r = cliente.post("/api/pix", json={"tipo_chave": "celular", "chave": "(65) 99603-5105", "valor": 250.5,
                                      "recebedor": "João Serviços", "vencimento": amanha, "centro_custo": "Manutenção"})
    assert r.status_code == 201, r.text
    pix = r.json()
    assert pix["chave"] == "+5565996035105" and pix["chave_formatada"] == "(65) 99603-5105"
    assert pix["tipo_chave_rotulo"] == "Celular" and pix["situacao"] == "a_vencer"

    assert cliente.post("/api/pix", json={"tipo_chave": "cpf_cnpj", "chave": "111.111.111-11", "valor": 10}).status_code == 422
    assert cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "a@b.com"}).json()["detail"]["codigo"] == "valor_obrigatorio"

    editado = cliente.put(f"/api/pix/{pix['id']}", json={"tipo_chave": "email", "chave": "Financeiro@Empresa.com.br"}).json()
    assert editado["chave"] == "financeiro@empresa.com.br" and editado["valor"] == 250.5
    pago = cliente.patch(f"/api/pix/{pix['id']}/status", json={"status": "Pago"}).json()
    assert pago["data_pagamento"] == date.today().isoformat()

    lista = cliente.get("/api/pix", params={"q": "joao", "centro": "manutenção"}).json()
    assert lista["total"] == 1 and lista["resumo"]["valor_pago"] == 250.5
    copia = cliente.get(f"/api/pix/{pix['id']}/copia-e-cola").json()
    assert copia["gerado"] and copia["copia_e_cola"].startswith("000201")
    assert cliente.get(f"/api/pix/{pix['id']}/qrcode.svg").headers["content-type"].startswith("image/svg")
    assert cliente.get("/api/pix/exportar", params={"formato": "xlsx"}).status_code == 200

    wb = load_workbook(contexto.planilha.caminho)
    assert wb["Pix"]["C2"].value == "João Serviços" and wb["Pix"]["D2"].value == "E-mail"
    assert any(l[1] == "Lançamento (Pix)" for l in wb["Histórico"].iter_rows(values_only=True))
    assert cliente.delete(f"/api/pix/{pix['id']}").status_code == 204


def test_pix_copia_e_cola_e_duplicado(cliente):
    codigo = gerar_copia_e_cola("cpf_cnpj", "02.359.273/0001-52", 360, "Hiper JN", txid="NF672362")
    lido = cliente.post("/api/pix/ler-codigo", json={"texto": codigo}).json()
    assert lido["tipo_chave"] == "cpf_cnpj" and lido["valor"] == 360 and lido["duplicado"] is None
    r = cliente.post("/api/pix", json={"copia_e_cola": codigo})
    assert r.status_code == 201 and r.json()["recebedor"] == "HIPER JN" and r.json()["txid"] == "NF672362"
    assert cliente.post("/api/pix", json={"copia_e_cola": codigo}).status_code == 409
    assert cliente.post("/api/pix/ler-codigo", json={"texto": codigo}).json()["duplicado"]["id"] == r.json()["id"]
    alterado = codigo[:-1] + ("0" if codigo[-1] != "0" else "1")
    assert cliente.post("/api/pix", json={"copia_e_cola": alterado}).json()["detail"]["codigo"] == "copia_e_cola_invalido"


def test_centros_de_custo_e_renomear(cliente):
    centros = cliente.get("/api/centros").json()["centros"]
    assert any(c["nome"] == "Combustível e Veículos" for c in centros)

    _, linha = montar_codigo("001", date.today() + timedelta(days=5), Decimal("150.00"), "3" * 25)
    boleto = cliente.post("/api/boletos", json={"linha_digitavel": linha, "beneficiario": "Posto Central", "valor": 150.0,
                                               "centro_custo": "  Frota   Pesada "}).json()
    assert boleto["centro_custo"] == "Frota Pesada"
    centros = {c["nome"]: c for c in cliente.get("/api/centros").json()["centros"]}
    assert centros["Frota Pesada"]["boletos"] == 1 and centros["Frota Pesada"]["total"] == 150.0  # criado automaticamente

    assert cliente.post("/api/centros", json={"nome": "frota pesada"}).status_code == 422  # já existe
    r = cliente.put("/api/centros", json={"nome_anterior": "Frota Pesada", "nome": "Veículos Pesados", "descricao": "Caminhões"})
    assert r.status_code == 200, r.text
    assert cliente.get(f"/api/boletos/{boleto['id']}").json()["centro_custo"] == "Veículos Pesados"
    assert cliente.get("/api/boletos", params={"centro": "veículos pesados"}).json()["total"] == 1
    assert cliente.get("/api/boletos", params={"centro": "__sem__"}).json()["total"] == 0

    cliente.put("/api/centros", json={"nome_anterior": "Outros", "nome": "Outros", "ativo": False})
    assert not {c["nome"]: c for c in cliente.get("/api/centros").json()["centros"]}["Outros"]["ativo"]


def test_analise_de_gastos(cliente):
    hoje = date.today()
    for valor, centro in ((100.0, "Obras"), (300.0, "Obras"), (50.0, "")):
        _, linha = montar_codigo("237", hoje + timedelta(days=int(valor)), Decimal(str(valor)), str(int(valor))[0] * 25)
        cliente.post("/api/boletos", json={"linha_digitavel": linha, "beneficiario": f"Fornecedor {valor}", "valor": valor, "centro_custo": centro})
    cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "a@b.com", "valor": 80, "centro_custo": "Obras",
                                   "vencimento": hoje.isoformat(), "status": "Pago"})
    analise = cliente.get("/api/gastos").json()
    assert analise["total"] == 530.0 and analise["total_pix"] == 80.0 and analise["sem_centro"] == 50.0
    obras = analise["centros"][0]
    assert obras["centro"] == "Obras" and obras["total"] == 480.0 and obras["pix"] == 80.0 and obras["percentual"] == 90.6
    assert cliente.get("/api/gastos", params={"situacao": "pagos"}).json()["total"] == 80.0
    assert cliente.get("/api/gastos", params={"tipo": "boleto"}).json()["total"] == 450.0
    exportado = cliente.get("/api/gastos/exportar")
    assert exportado.status_code == 200 and exportado.content[:2] == b"PK"


def test_analise_por_mes_agrupa_centros_menores():
    hoje = date(2026, 9, 14)
    boletos = [{"id": i, "valor": 10.0 * (i + 1), "vencimento": hoje, "status": "Pendente", "centro_custo": f"C{i}"} for i in range(8)]
    analise = analise_gastos(boletos, [], hoje=hoje)
    assert len(analise["series"]) == 7 and analise["series"][-1] == "Outros centros"
    assert analise["serie_mensal"][0]["centros"]["Outros centros"] == 30.0  # C0 (10) + C1 (20)


def test_notificacoes_incluem_pix(tmp_path):
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "f.json")
    pix = RepositorioBoletos(planilha, fila, "pix")
    pix.adicionar({"recebedor": "Maria", "tipo_chave": "celular", "chave": "+5565996035105", "valor": 90.0,
                   "vencimento": date.today()})
    fonte = FonteLembretes(RepositorioBoletos(planilha, fila), pix)
    [registro] = fonte.listar()
    assert registro["id"] == "pix-1" and registro["chave_pix"] == "(65) 99603-5105"
    from app.notificacoes.regras import montar_alertas, montar_mensagem

    alertas = montar_alertas(fonte.listar(), date.today())
    mensagem = montar_mensagem(alertas, date.today(), "http://localhost:8000")
    assert mensagem.titulo == "Pix vence hoje" and "Chave Pix: (65) 99603-5105" in mensagem.texto


def test_migra_planilha_antiga(tmp_path):
    from openpyxl import Workbook

    caminho = tmp_path / "antiga.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Boletos"
    ws.append(["ID", "Data de Lançamento", "Beneficiário", "Valor (R$)", "Status"])
    ws.append([1, None, "Antigo", 10.0, "Pendente"])
    wb.create_sheet("Histórico")
    wb.save(caminho)
    planilha = PlanilhaBoletos(caminho)
    assert planilha.migrar()
    nomes = load_workbook(caminho).sheetnames
    assert nomes == ["Boletos", "Pix", "Centros de Custo", "Histórico"]
    assert not planilha.migrar()
    assert planilha.listar()[0]["centro_custo"] == "" and planilha.listar("pix") == []


def test_endpoints_do_aplicativo(cliente, monkeypatch):
    estado = cliente.get("/api/app").json()
    assert estado["modo_app"] is False and estado["preferencias"]["fechar_para_bandeja"] is True
    assert cliente.post("/api/app/mostrar", json={"rota": "pix"}).json() == {"modo_app": False}
    assert cliente.get("/api/app/abrir", params={"rota": "boletos?pagar=3"}, follow_redirects=False).headers["location"] == "/#/boletos?pagar=3"

    rotas = []
    janela.registrar(rotas.append)
    try:
        assert cliente.post("/api/app/mostrar", json={"rota": "pix?pagar=2"}).json() == {"modo_app": True}
        assert cliente.post("/api/app/mostrar", json={"rota": "javascript:alert(1)"}).json() == {"modo_app": True}
        assert "foi aberto" in cliente.get("/api/app/abrir", params={"rota": "gastos"}).text
        assert rotas == ["pix?pagar=2", None, "gastos"]
        assert main._link_notificacao("pix?pagar=2").endswith("/api/app/abrir?rota=pix%3Fpagar%3D2")
    finally:
        janela.desregistrar()

    prefs = cliente.put("/api/app/preferencias", json={"fechar_para_bandeja": False}).json()["preferencias"]
    assert prefs["fechar_para_bandeja"] is False


def test_painel_mostra_boletos_e_pix_vencidos(cliente):
    hoje = date.today()
    for dias, nome in ((-20, "Pix antigo"), (-3, "Pix recente"), (5, "Pix futuro")):
        r = cliente.post("/api/pix", json={"tipo_chave": "email", "chave": "financeiro@fornecedor.com", "valor": 100 + dias,
                                          "recebedor": nome, "vencimento": (hoje + timedelta(days=dias)).isoformat()})
        assert r.status_code == 201, r.text
    for dias in range(-12, -4):  # mais de 6 boletos vencidos: todos aparecem
        cliente.post("/api/boletos", json={"beneficiario": f"Fornecedor {dias}", "valor": 50, "ignorar_validacao": True,
                                           "vencimento": (hoje + timedelta(days=dias)).isoformat()})
    painel = cliente.get("/api/painel").json()
    k = painel["indicadores"]
    assert (k["vencidos_qtd"], k["vencidos_pix_qtd"], k["vencidos_boletos_qtd"]) == (10, 2, 8)
    vencidos = painel["vencidos"]
    assert len(vencidos) == 10 and vencidos[0]["beneficiario"] == "Pix antigo" and vencidos[0]["tipo_pagamento"] == "pix"
    assert {v["beneficiario"] for v in vencidos if v["tipo_pagamento"] == "pix"} == {"Pix antigo", "Pix recente"}
    assert any(p["beneficiario"] == "Pix futuro" for p in painel["proximos"])


def test_previsao_de_saidas_por_semana(cliente):
    from app.servicos import previsao_saidas

    hoje = date(2026, 9, 17)
    boletos = [{"id": 1, "status": "Pendente", "valor": 100, "vencimento": date(2026, 9, 10), "beneficiario": "Atrasado"},
               {"id": 2, "status": "Pendente", "valor": 200, "vencimento": date(2026, 9, 17), "beneficiario": "Hoje"},
               {"id": 3, "status": "Pendente", "valor": 300, "vencimento": date(2026, 9, 24), "beneficiario": "Semana 2"},
               {"id": 4, "status": "Pago", "valor": 999, "vencimento": date(2026, 9, 18)},
               {"id": 5, "status": "Pendente", "valor": 50, "vencimento": None}]
    pix = [{"id": 1, "status": "Pendente", "valor": 25.5, "vencimento": date(2026, 9, 23), "recebedor": "Frete"}]
    p = previsao_saidas(boletos, pix, hoje, semanas=4)
    assert [s["total"] for s in p["semanas"]] == [225.5, 300.0, 0.0, 0.0]
    assert p["semanas"][0]["pix"] == 25.5 and [i["nome"] for i in p["semanas"][0]["itens"]] == ["Hoje", "Frete"]
    assert (p["em_atraso"]["total"], p["sem_vencimento"]["quantidade"]) == (100.0, 1)
    assert p["totais"] == {"7_dias": 225.5, "30_dias": 525.5, "periodo": 525.5, "com_atraso": 625.5}
    assert cliente.get("/api/previsao", params={"semanas": 12}).json()["semanas"].__len__() == 12
```

## `tests/test_planilha.py` (84 linhas)

```python
from datetime import date, datetime

from openpyxl import load_workbook

from app.planilha import PlanilhaBoletos, RegistroNaoEncontrado


def test_ciclo_completo(tmp_path):
    p = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    a = p.adicionar({"linha_digitavel": "1", "codigo_barras": "ABC", "beneficiario": "Fornecedor A",
                     "vencimento": date(2026, 10, 1), "valor": 99.9, "tipo": "bancario"})
    b = p.adicionar({"beneficiario": "Fornecedor B", "valor": 10.0})
    assert (a["id"], b["id"]) == (1, 2)
    assert isinstance(a["data_lancamento"], datetime)

    registros = p.listar()
    assert [r["beneficiario"] for r in registros] == ["Fornecedor A", "Fornecedor B"]
    assert registros[0]["tipo"] == "bancario" and registros[0]["vencimento"] == date(2026, 10, 1)

    atualizado = p.atualizar(1, {"status": "Pago", "data_pagamento": date(2026, 9, 30)})
    assert atualizado["status"] == "Pago" and atualizado["data_pagamento"] == date(2026, 9, 30)
    assert p.buscar_por_codigo("ABC")[0]["id"] == 1

    p.excluir(2)
    assert [r["id"] for r in p.listar()] == [1]
    assert p.adicionar({"beneficiario": "C"})["id"] == 2

    try:
        p.obter(99)
    except RegistroNaoEncontrado:
        pass
    else:
        raise AssertionError("esperava RegistroNaoEncontrado")

    wb = load_workbook(tmp_path / "boletos.xlsx")
    assert wb.sheetnames == ["Boletos", "Pix", "Caixa", "Resumo", "Centros de Custo", "Histórico"]
    cabecalho = [c.value for c in wb["Boletos"][1]]
    assert "Data de Lançamento" in cabecalho and "Linha Digitável" in cabecalho
    assert (tmp_path / "backups").exists()


def test_lote_em_uma_gravacao_e_aba_historico(tmp_path):
    p = PlanilhaBoletos(tmp_path / "b.xlsx")
    criados = p.adicionar_lote([{"beneficiario": "A", "valor": 1}, {"beneficiario": "B", "valor": 2}])
    assert [c["id"] for c in criados] == [1, 2]

    resultados = p.aplicar_lote([
        {"tipo": "atualizar", "id": 1, "dados": {"status": "Pago", "data_pagamento": date(2026, 9, 14)}},
        {"tipo": "excluir", "id": 2},
        {"tipo": "atualizar", "id": 99, "dados": {"status": "Pago"}},
        {"tipo": "adicionar", "dados": {"beneficiario": "C"}},
    ])
    assert [r["ok"] for r in resultados] == [True, True, False, True]
    assert resultados[3]["registro"]["id"] == 3
    assert [(r["id"], r["beneficiario"], r["status"]) for r in p.listar()] == [(1, "A", "Pago"), (3, "C", "Pendente")]

    historico = list(load_workbook(tmp_path / "b.xlsx")["Histórico"].iter_rows(min_row=2, values_only=True))
    assert [h[1] for h in historico] == ["Lançamento", "Lançamento", "Pagamento", "Exclusão", "Lançamento"]
    assert "Status: Pendente → Pago" in historico[2][6]


def test_ignora_status_desconhecido_e_linhas_vazias(tmp_path):
    caminho = tmp_path / "b.xlsx"
    p = PlanilhaBoletos(caminho)
    p.adicionar({"beneficiario": "X"})
    wb = load_workbook(caminho)
    ws = wb["Boletos"]
    ws.cell(row=2, column=12, value="qualquer")
    ws.cell(row=5, column=5, value=None)
    wb.save(caminho)
    assert p.listar()[0]["status"] == "Pendente"


def test_voltar_para_pendente_apaga_a_data_de_pagamento_gravada(tmp_path):
    """Regressão: apagar um campo precisa limpar a célula (antes a data de pagamento antiga ficava na planilha)."""
    from datetime import date as _date

    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    registro = planilha.adicionar({"beneficiario": "Fornecedor", "valor": 10, "status": "Pago", "data_pagamento": _date.today()},
                                  usuario="Ana")
    assert planilha.obter(registro["id"])["pago_por"] == "Ana"
    planilha.atualizar(registro["id"], {"status": "Pendente", "data_pagamento": None}, usuario="Ana")
    relido = planilha.obter(registro["id"])
    assert relido["data_pagamento"] is None and relido["pago_por"] == ""
```

## `tests/test_rede.py` (94 linhas)

```python
"""Acesso pelo celular: senha com hash, servidor de rede liga/desliga, login, bloqueio, sair e QR code."""

import json
import socket
import urllib.request

import pytest
from fastapi.testclient import TestClient

from app import acesso, config
from app.main import app, rede
from app.rede import GerenciadorRede, descobrir_enderecos, descrever_aparelho


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_senha_guardada_com_hash_e_troca_invalida_sessoes(tmp_path):
    gerenciador = GerenciadorRede(app, tmp_path / "rede.json", 0)
    with pytest.raises(ValueError):
        gerenciador.definir_senha("123")
    gerenciador.definir_senha("minha-senha")
    assert "minha-senha" not in (tmp_path / "rede.json").read_text(encoding="utf-8")
    assert gerenciador.verificar_senha("minha-senha") and not gerenciador.verificar_senha("outra")
    token = gerenciador.token_sessao()
    gerenciador.definir_senha("nova-senha-1")
    assert gerenciador.token_sessao() != token
    assert GerenciadorRede(app, tmp_path / "rede.json", 0).verificar_senha("nova-senha-1")


def test_liga_e_desliga_o_servidor_da_rede_sem_reiniciar(tmp_path):
    porta = _porta_livre()
    # 127.0.0.2 simula o endereço de rede sem abrir nada de verdade para o Wi-Fi
    gerenciador = GerenciadorRede(app, tmp_path / "rede.json", porta, descobrir=lambda: ["127.0.0.2"])
    with pytest.raises(ValueError):
        gerenciador.ativar()  # sem senha
    gerenciador.definir_senha("minha-senha")
    status = gerenciador.ativar()
    try:
        assert status["rodando"] and status["urls"] == [f"http://127.0.0.2:{porta}"]
        with urllib.request.urlopen(f"http://127.0.0.2:{porta}/api/acesso/estado", timeout=5) as resposta:
            assert "autorizado" in json.loads(resposta.read())
        assert GerenciadorRede(app, tmp_path / "rede.json", porta).ativo  # lembra que estava ligado
    finally:
        status = gerenciador.desativar()
    assert not gerenciador.rodando and not status["ativo"]
    with pytest.raises(OSError):
        urllib.request.urlopen(f"http://127.0.0.2:{porta}/api/acesso/estado", timeout=2)


def test_login_do_celular_bloqueio_sair_e_permissoes(monkeypatch):
    monkeypatch.setattr(config, "SENHA_ACESSO", "")
    monkeypatch.setattr(rede, "_estado", dict(rede._estado))
    acesso._falhas.clear()

    with TestClient(app, client=("127.0.0.1", 50000)) as computador:
        assert computador.post("/api/rede/senha", json={"senha": "celular123", "confirmacao": "outra123"}).status_code == 422
        assert computador.post("/api/rede/senha", json={"senha": "123", "confirmacao": "123"}).status_code == 422
        estado = computador.post("/api/rede/senha", json={"senha": "celular123", "confirmacao": "celular123"}).json()
        assert estado["senha_definida"] and estado["local"]

    with TestClient(app, client=("192.168.0.77", 50000)) as intruso:
        assert intruso.get("/api/boletos").status_code == 401
        assert intruso.post("/api/rede/senha", json={"senha": "hackeado1", "confirmacao": "hackeado1"}).status_code == 401
        for _ in range(5):
            assert intruso.post("/api/acesso", json={"senha": "errada"}).status_code in (401, 429)
        assert intruso.post("/api/acesso", json={"senha": "celular123"}).status_code == 429  # bloqueado

    with TestClient(app, client=("192.168.0.78", 50000)) as celular:
        assert celular.post("/api/acesso", json={"senha": "celular123"}).status_code == 200
        assert celular.get("/api/boletos").status_code == 200
        status = celular.get("/api/rede").json()
        assert status["local"] is False
        assert any(a["ip"] == "192.168.0.78" for a in status["acessos"])
        assert celular.post("/api/rede/ativar", json={"ativo": True}).status_code == 403  # só no computador
        celular.post("/api/acesso/sair")
        assert celular.get("/api/boletos").status_code == 401
    acesso._falhas.clear()


def test_qrcode_do_endereco(monkeypatch):
    monkeypatch.setattr(rede, "status", lambda: {"urls": ["http://192.168.0.10:8000"]})
    with TestClient(app) as cliente:
        resposta = cliente.get("/api/rede/qrcode.svg")
    assert resposta.status_code == 200 and resposta.text.lstrip().startswith("<svg")


def test_utilitarios_de_rede():
    assert all(isinstance(ip, str) for ip in descobrir_enderecos())
    agente = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36"
    assert descrever_aparelho(agente) == "Android · Chrome"
```

## `tests/test_registro_log.py` (16 linhas)

```python
"""O arquivo de log gira quando fica grande e guarda só alguns arquivos antigos."""

from app import registro_log


def test_log_gira_e_limita_arquivos(tmp_path):
    caminho = tmp_path / "leitor.log"
    saida = registro_log.ArquivoRotativo(caminho, tamanho_maximo=200, antigos=2)
    for n in range(40):
        saida.write(f"linha {n:03d} " + "x" * 20 + "\n")
    arquivos = registro_log.arquivos_de_log(caminho)
    assert [a.name for a in arquivos] == ["leitor.log", "leitor.log.1", "leitor.log.2"]
    assert all(a.stat().st_size <= 260 for a in arquivos)
    assert "linha 039" in caminho.read_text(encoding="utf-8")
    assert saida.limpar_antigos() > 0
    assert [a.name for a in registro_log.arquivos_de_log(caminho)] == ["leitor.log"] and caminho.stat().st_size == 0
```

## `tests/test_relatorio_geral.py` (102 linhas)

```python
"""Relatório geral do mês (menu Relatórios): pagos, juros e multas, últimos 12 meses e as partes de cada módulo."""

import io
from datetime import date, timedelta

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import contexto, main, relatorio_geral
from app.arquivos import RepositorioArquivos
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

SETEMBRO = date(2026, 9, 1)
HOJE = date(2026, 9, 24)


class _Repo:
    def __init__(self, registros):
        self.registros = registros

    def listar(self):
        return list(self.registros)


def _boleto(id_, valor, juros=0.0, pago=date(2026, 9, 21), venc=date(2026, 9, 10), status="Pago"):
    return {"id": id_, "beneficiario": f"Fornecedor {id_}", "valor": valor, "status": status, "vencimento": venc,
            "data_pagamento": pago if status == "Pago" else None, "valor_pago": valor + juros if status == "Pago" else None,
            "juros_multa": juros, "centro_custo": "Manutenção"}


def _preparar(monkeypatch):
    boletos = [_boleto(1, 900, 56.70), _boleto(2, 210), _boleto(3, 500, status="Pendente", venc=date(2026, 9, 30)),
               _boleto(4, 300, 9.90, pago=date(2026, 8, 12), venc=date(2026, 8, 5))]
    pix = [{"id": 1, "recebedor": "João Frete", "valor": 150, "vencimento": date(2026, 9, 18), "status": "Pago",
            "data_pagamento": date(2026, 9, 18), "valor_pago": 150, "centro_custo": "Fretes"}]
    monkeypatch.setattr(contexto, "repositorio", _Repo(boletos))
    monkeypatch.setattr(contexto, "repositorio_pix", _Repo(pix))
    monkeypatch.setattr("app.caixa.servico.saidas_para_gastos", lambda: [])


def test_pagos_juros_e_historico_do_mes(monkeypatch):
    _preparar(monkeypatch)
    r = relatorio_geral.montar(SETEMBRO, lambda p: p == "gastos", HOJE)
    c = r["contas"]
    assert (c["pago"], c["quantidade_pagos"], c["juros_multa"]) == (1316.7, 3, 56.7)
    assert c["por_tipo"]["Boleto"] == {"valor": 1166.7, "quantidade": 2} and c["por_tipo"]["Pix"]["valor"] == 150
    assert [j["nome"] for j in c["juros"]] == ["Fornecedor 1"]
    assert c["vencimento"]["em_aberto"] == 500
    assert len(r["historico"]) == 12 and r["historico"][-1]["mes"] == "2026-09"
    assert r["historico"][-2]["juros_multa"] == 9.9
    assert (r["titulo"], r["anterior"], r["seguinte"]) == ("setembro de 2026", "2026-08", "2026-10")
    assert "caixa" not in r and "diesel" not in r and "empresas" not in r  # sem a permissão, a parte não aparece


def test_sem_permissao_de_gastos_nao_mostra_os_pagamentos(monkeypatch):
    _preparar(monkeypatch)
    r = relatorio_geral.montar(SETEMBRO, lambda p: False, HOJE)
    assert "contas" not in r and "historico" not in r and "previsao" in r


def test_uma_parte_com_erro_nao_derruba_o_relatorio(monkeypatch):
    _preparar(monkeypatch)

    def quebra(*_):
        raise RuntimeError("banco do diesel indisponível")

    monkeypatch.setattr(relatorio_geral, "_diesel", quebra)
    r = relatorio_geral.montar(SETEMBRO, lambda p: p in ("gastos", "diesel"), HOJE)
    assert r["diesel"] == {"erro": "banco do diesel indisponível"} and r["contas"]["pago"] == 1316.7


def test_excel_tem_resumo_juros_e_12_meses(monkeypatch):
    _preparar(monkeypatch)
    r = relatorio_geral.montar(SETEMBRO, lambda p: p == "gastos", HOJE)
    wb = load_workbook(io.BytesIO(relatorio_geral.gerar_xlsx(r)))
    assert wb.sheetnames == ["Resumo", "Juros e multas", "Últimos 12 meses"]
    assert wb["Resumo"]["B5"].value == 1316.7
    assert wb["Juros e multas"]["B5"].value == "Fornecedor 1" and wb["Juros e multas"]["G5"].value == 56.7
    assert wb["Últimos 12 meses"]["A16"].value == "setembro de 2026"


def test_api_do_relatorio_geral(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    hoje = date.today()
    planilha.adicionar({"beneficiario": "Internet", "valor": 99.9, "vencimento": hoje.replace(day=1) + timedelta(days=3),
                        "status": "Pago", "data_pagamento": hoje, "valor_pago": 104.9, "juros_multa": 5}, usuario="Ana")
    with TestClient(main.app) as c:
        dados = c.get("/api/relatorio-geral").json()
        assert dados["mes"] == hoje.strftime("%Y-%m")
        assert dados["contas"]["pago"] == 104.9 and dados["contas"]["juros_multa"] == 5
        for parte in ("caixa", "diesel", "empresas"):
            assert parte in dados and "erro" not in dados[parte], dados.get(parte)
        assert c.get("/api/relatorio-geral", params={"mes": "2026-13"}).status_code == 422
        resposta = c.get("/api/relatorio-geral/arquivo")
        assert resposta.status_code == 200 and "spreadsheet" in resposta.headers["content-type"]
        assert f"relatorio-geral-{hoje:%Y-%m}.xlsx" in resposta.headers["content-disposition"]
```

## `tests/test_resumo_semanal.py` (172 linhas)

```python
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
```

## `tests/test_saude.py` (23 linhas)

```python
"""Tela Saúde do sistema: diagnóstico sempre responde e aponta o que precisa de atenção."""

from fastapi.testclient import TestClient

from app import contexto, main


def test_diagnostico_e_acoes(monkeypatch):
    with TestClient(main.app) as cliente:
        dados = cliente.get("/api/saude").json()
        chaves = {i["chave"] for i in dados["itens"]}
        assert {"banco", "notificacoes", "backup", "entrada", "fila", "leitura", "disco", "rede"} <= chaves
        assert dados["situacao"] in ("ok", "aviso", "erro") and all(i["resumo"] for i in dados["itens"])
        backup = next(i for i in dados["itens"] if i["chave"] == "backup")
        assert backup["situacao"] == "desligado"

        assert cliente.post("/api/saude/atualizar-planilha").status_code == 200
        assert "liberados" in cliente.post("/api/saude/limpar-logs").json()

        # Um diagnóstico que falha não derruba os outros
        monkeypatch.setattr(contexto.backup, "status", lambda: 1 / 0)
        itens = cliente.get("/api/saude").json()["itens"]
        assert itens[0]["situacao"] == "erro" and "Não foi possível verificar" in itens[0]["resumo"]
```

## `tests/test_sino.py` (55 linhas)

```python
"""Sininho: avisos vistos saem da contagem; dispensados saem da lista; voltam quando a situação muda."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import main
from app.notificacoes.servico import ServicoNotificacoes


class FonteFalsa:
    def __init__(self, registros):
        self.registros = registros

    def listar(self):
        return [dict(r) for r in self.registros]


def test_avisos_vistos_dispensados_e_mudanca_de_situacao(tmp_path):
    hoje = date.today()
    fonte = FonteFalsa([
        {"id": 1, "beneficiario": "Fornecedor A", "valor": 10.0, "vencimento": hoje + timedelta(days=1), "status": "Pendente"},
        {"id": 2, "beneficiario": "Fornecedor B", "valor": 20.0, "vencimento": hoje, "status": "Pendente"},
    ])
    servico = ServicoNotificacoes(fonte, tmp_path / "notificacoes.json", "http://localhost:8000")

    alertas = servico.alertas()
    assert len(alertas) == 2 and not any(a["visto"] or a["dispensado"] for a in alertas)
    assert servico.marcar_vistos([a["chave"] for a in alertas] + ["aviso-inexistente"]) == 2
    assert all(a["visto"] for a in servico.alertas())

    chave_b = next(a["chave"] for a in servico.alertas() if a["id"] == 2)
    assert servico.dispensar(chave_b)
    assert [a["id"] for a in servico.alertas() if a["dispensado"]] == [2]

    # Guardado em arquivo: continua valendo depois de reiniciar o sistema
    reaberto = ServicoNotificacoes(fonte, tmp_path / "notificacoes.json", "http://localhost:8000")
    assert all(a["visto"] for a in reaberto.alertas())

    # O boleto 1 passa de "vence amanhã" para "vence hoje": volta a contar como aviso novo
    fonte.registros[0]["vencimento"] = hoje
    assert [a["id"] for a in servico.alertas() if not a["visto"]] == [1]

    assert servico.restaurar_dispensados() == 1
    assert not any(a["dispensado"] for a in servico.alertas())


def test_api_do_sininho():
    with TestClient(main.app) as cliente:
        dados = cliente.get("/api/notificacoes").json()
        assert "nao_vistos" in dados and all("chave" in a and "visto" in a for a in dados["alertas"])
        assert cliente.post("/api/notificacoes/vistos", json={"chaves": [a["chave"] for a in dados["alertas"]]}).status_code == 200
        assert cliente.get("/api/notificacoes").json()["nao_vistos"] == 0
        assert cliente.post("/api/notificacoes/dispensar", json={"chave": "inexistente"}).json() == {"dispensado": False}
        assert cliente.post("/api/notificacoes/restaurar").status_code == 200
```

## `tests/test_telas.py` (205 linhas)

```python
"""Testes das telas no navegador (Playwright + Edge já instalado no Windows).

Sobem o sistema numa porta livre, com dados temporários, e conferem os caminhos principais:
abrir todas as telas sem erro no console, ler um boleto, dar baixa por comprovante e ver o fechamento.

Se o Playwright ou o Edge não estiverem disponíveis, os testes são pulados (o restante da suíte continua valendo).
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
pytest.importorskip("playwright", reason="Playwright não instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from gerar_boleto_exemplo import gerar_pdf  # noqa: E402


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def sistema():
    """Sobe o Fin Pro com uma pasta de dados vazia e devolve (url, pasta)."""
    pasta = Path(tempfile.mkdtemp(prefix="leitor-telas-"))
    porta = _porta_livre()
    ambiente = {**os.environ, "LEITOR_DADOS_DIR": str(pasta), "LEITOR_PORT": str(porta),
                "LEITOR_NOTIFICACOES_AUTOMATICAS": "0", "LEITOR_BACKUP_AUTOMATICO": "0", "LEITOR_ABRIR_NAVEGADOR": "0"}
    processo = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(porta)],
                                cwd=RAIZ, env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{porta}"
    for _ in range(120):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                break
        time.sleep(0.5)
    else:
        processo.terminate()
        pytest.fail("o servidor não subiu")
    yield url, pasta
    processo.terminate()
    processo.wait(timeout=30)


@pytest.fixture(scope="module")
def pagina(sistema):
    url, _ = sistema
    try:
        navegador = sync_playwright().start()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Playwright indisponível: {exc}")
    try:
        edge = navegador.chromium.launch(channel="msedge")
    except Exception as exc:  # pragma: no cover
        navegador.stop()
        pytest.skip(f"Microsoft Edge indisponível: {exc}")
    pagina = edge.new_page(viewport={"width": 1400, "height": 1000})
    pagina.erros = []
    pagina.on("console", lambda m: pagina.erros.append(m.text) if m.type == "error" else None)
    pagina.on("pageerror", lambda e: pagina.erros.append(str(e)))
    pagina.goto(url, wait_until="networkidle")
    yield pagina
    edge.close()
    navegador.stop()


def _texto(pagina, seletor: str) -> str:
    """Texto da tela com o espaço fixo do "R$ 1,00" trocado por espaço normal (facilita as comparações)."""
    return pagina.inner_text(seletor).replace(" ", " ")


def _ir(pagina, rota: str):
    pagina.evaluate("(r) => { location.hash = r; }", f"#/{rota}")
    pagina.wait_for_timeout(900)


def test_todas_as_telas_abrem_sem_erro(pagina):
    telas = {
        "painel": "Nenhum boleto lançado ainda", "ler": "Arraste os boletos", "boletos": "Exportar", "pix": "Novo pagamento Pix",
        "gastos": "Análise de gastos", "notificacoes": "Avisos de vencimento", "config?aba=geral": "Recursos de leitura",
        "config?aba=usuarios": "Usuários do escritório", "config?aba=integracoes": "Backup fora do computador",
        "config?aba=saude": "Banco de dados e planilha", "empresas?aba=fechamentos": "Falta receber",
        "empresas?aba=cheques": "Em carteira", "empresas?aba=bot": "Bot de notas fiscais",
        "comprovantes": "Baixar comprovantes", "comprovantes?tipo=cheque": "Pagos sem comprovante",
        "caixa": "Saldo em caixa", "caixa?aba=relatorios": "Onde mais se gastou", "caixa?aba=conferencia": "Nada para revisar",
        "caixa?aba=bot": "Bot do caixa",
        "diesel": "Saldo do diesel", "diesel?aba=maquinas": "Nenhuma máquina cadastrada",
        "diesel?aba=relatorios": "Relatório semanal", "diesel?aba=conferencia": "Nada para conferir",
        "diesel?aba=bot": "Quem escolhe a máquina",
    }
    for rota, texto in telas.items():
        _ir(pagina, rota)
        assert texto in _texto(pagina, "#view"), f"a tela {rota} não mostrou “{texto}”"
    assert not pagina.erros, pagina.erros


def test_ler_boleto_lancar_e_dar_baixa_por_comprovante(pagina, sistema, tmp_path_factory):
    from app.boleto.codigo import formatar_linha
    from test_comprovante import ITAU, _pdf

    url, _ = sistema
    pasta = tmp_path_factory.mktemp("arquivos")
    vencimento = date.today() - timedelta(days=3)
    caminho = pasta / "boleto.pdf"
    linha = gerar_pdf(caminho, beneficiario="CLA AUTO PECAS MIRASSOL LTDA", cnpj="12.345.678/0001-95", documento="NF-1",
                      vencimento=vencimento, valor=Decimal("270.35"))

    _ir(pagina, "ler")
    pagina.set_input_files("#entrada-arquivos", str(caminho))
    pagina.wait_for_selector("[data-acao=lancar]", timeout=60_000)
    assert pagina.locator("[data-campo=beneficiario]").first.input_value() == "CLA AUTO PECAS MIRASSOL LTDA"
    pagina.click("[data-acao=lancar]")
    pagina.wait_for_selector("text=Lançado na planilha", timeout=20_000)

    comprovante = pasta / "comprovante.pdf"
    texto = ITAU.replace("R$ 5,40", "R$ 8,10").replace("R$ 275,75", "R$ 278,45").format(
        linha=formatar_linha(linha), vencimento=f"{vencimento:%d/%m/%Y}", pagamento=f"{date.today():%d/%m/%Y}")
    comprovante.write_bytes(_pdf(texto))
    pagina.set_input_files("#entrada-arquivos", str(comprovante))
    pagina.wait_for_selector("text=Pagamento registrado", timeout=60_000)
    assert "juros/multa R$ 8,10" in _texto(pagina, "#lista-fila")

    _ir(pagina, "boletos")
    linhas = _texto(pagina, "#tabela")
    assert "CLA AUTO PECAS" in linhas and "Pago" in linhas

    _ir(pagina, f"gastos?aba=fechamento")
    pagina.wait_for_selector("text=Juros e multas", timeout=20_000)
    resumo = _texto(pagina, "#f-resultado")
    assert "R$ 278,45" in resumo and "R$ 8,10" in resumo
    assert not pagina.erros, pagina.erros


def test_painel_mostra_previsao_e_vencidos(pagina):
    pagina.evaluate("""async () => {
      const venc = new Date(Date.now() - 5 * 86400000).toISOString().slice(0, 10);
      await fetch("/api/boletos", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ beneficiario: "Fornecedor Atrasado", valor: 1500, vencimento: venc, ignorar_validacao: true }) });
      await fetch("/api/pix", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo_chave: "email", chave: "a@b.com", valor: 250, recebedor: "Pix Atrasado", vencimento: venc }) });
    }""")
    _ir(pagina, "boletos")
    _ir(pagina, "painel")
    texto = _texto(pagina, "#view")
    assert "Previsão de saídas" in texto and "Vencidos (2)" in texto and "Pix Atrasado" in texto
    assert "1 boleto e 1 Pix em atraso" in texto and "R$ 1.750,00" in texto
    pagina.click(".prev-linha.atraso")
    pagina.wait_for_selector(".modal", timeout=10_000)
    assert "Fornecedor Atrasado" in _texto(pagina, ".modal")
    pagina.keyboard.press("Escape")
    assert not pagina.erros, pagina.erros


def test_empresas_importa_o_print_do_fechamento_e_da_baixa(pagina, sistema, tmp_path_factory):
    """Parte 5 do módulo Empresas: começar a operar com o fechamento que já estava em andamento."""
    from test_empresas_bot import _pdf
    from test_empresas_leitura import PRINT_FECHAMENTO

    pagina.evaluate("""async () => {
      await fetch("/api/empresas", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: "Imapal", cnpj: "12.345.678/0001-95" }) });
      await fetch("/api/empresas/config", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ minha_empresa: { nome: "Prospera Industria E Serviços LTDA", cnpj: "03.880.985/0001-85" } }) });
    }""")
    caminho = tmp_path_factory.mktemp("empresas") / "print-fechamento.pdf"
    caminho.write_bytes(_pdf(PRINT_FECHAMENTO))

    _ir(pagina, "empresas?aba=conferencia")
    pagina.set_input_files("#emp-arquivo", str(caminho))
    pagina.wait_for_selector("text=Importar fechamento já em andamento", timeout=60_000)
    assert "R$ 9.528,00" in _texto(pagina, ".modal")
    pagina.select_option(".modal #if-empresa", "Imapal")
    pagina.click(".modal [data-salvar]")
    pagina.wait_for_selector("text=linha(s) importada(s)", timeout=20_000)

    pagina.wait_for_selector(".tabela-fechamento", timeout=20_000)  # abre sozinho no fechamento importado
    fechamento = _texto(pagina, "#emp-fechamento")
    assert "Prospera Industria E Serviços LTDA 03.880.985/0001-85" in fechamento
    assert "agosto de 2026" in fechamento
    assert "Fechamento Imapal" in fechamento and "6859" in fechamento and "Brita 01" in fechamento
    assert "R$ 9.528,00" in fechamento

    # comprovante de Pix recebido: baixa automática da NF citada
    pagina.evaluate("""async () => {
      await fetch("/api/recebimentos", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa: "Imapal", forma: "Pix", valor: 1905.6, notas: "6859" }) });
    }""")
    _ir(pagina, "empresas?aba=notas")  # sai e volta para a tela desenhar de novo
    _ir(pagina, "empresas?aba=fechamentos&empresa=1&competencia=2026-08")
    pagina.wait_for_selector(".tabela-fechamento", timeout=20_000)
    resumo = _texto(pagina, ".fechamento-resumo")
    assert "R$ 1.905,60" in resumo and "R$ 7.622,40" in resumo  # já recebido e o que falta
    assert not pagina.erros, pagina.erros
```

## `tests/test_telegram_destinatarios.py` (79 linhas)

```python
"""Telegram para várias pessoas e grupos do escritório."""

import json

from app.notificacoes import canais, servico as modulo_servico
from app.notificacoes.servico import MASCARA, ServicoNotificacoes


class FonteVazia:
    def listar(self):
        return []


def _servico(tmp_path):
    return ServicoNotificacoes(FonteVazia(), tmp_path / "notificacoes.json", "http://localhost:8000")


def test_configuracao_antiga_com_um_chat_vira_lista(tmp_path):
    (tmp_path / "notificacoes.json").write_text(
        json.dumps({"telegram": {"ativo": True, "token": "123:abc", "chat_id": "42"}}), encoding="utf-8")
    publica = _servico(tmp_path).config_publica()["telegram"]
    assert publica["destinatarios"] == [{"chat_id": "42", "nome": "Principal", "tipo": "privado", "ativo": True}]
    assert publica["token"] == MASCARA


def test_salva_destinatarios_sem_repetidos_nem_invalidos(tmp_path):
    servico = _servico(tmp_path)
    publica = servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "destinatarios": [
        {"chat_id": "111", "nome": "  Fábio  "},
        {"chat_id": "111", "nome": "Repetido"},
        {"chat_id": "-100222", "nome": "Escritório", "ativo": True},
        {"chat_id": "abc", "nome": "Inválido"},
        {"chat_id": "333", "nome": "", "ativo": False},
    ]}})["telegram"]
    assert [(d["chat_id"], d["nome"], d["tipo"], d["ativo"]) for d in publica["destinatarios"]] == [
        ("111", "Fábio", "privado", True), ("-100222", "Escritório", "grupo", True), ("333", "Sem nome", "privado", False)]
    assert publica["chat_id"] == "111"


def test_envia_para_todos_os_ativos_e_informa_quem_nao_recebeu(tmp_path, monkeypatch):
    servico = _servico(tmp_path)
    servico.atualizar_config({"telegram": {"ativo": True, "token": "123:abc", "destinatarios": [
        {"chat_id": "1", "nome": "Fábio"}, {"chat_id": "2", "nome": "Maria"},
        {"chat_id": "3", "nome": "João", "ativo": False}, {"chat_id": "-4", "nome": "Grupo Escritório"}]}})
    enviados = []

    def enviar(token, chat_id, texto):
        enviados.append(chat_id)
        if chat_id == "2":
            raise canais.ErroCanal("Telegram: a pessoa ainda não enviou /start para o bot ou bloqueou o bot.")

    monkeypatch.setattr(modulo_servico.canais, "enviar_telegram", enviar)
    resultado = servico.testar("telegram")
    assert enviados == ["1", "2", "-4"]  # João está desligado
    assert resultado["canais"]["telegram"].startswith("erro: enviado para 2 de 3; não receberam: Maria (a pessoa ainda não enviou /start")

    enviados.clear()
    servico.testar_destinatario_telegram("1")
    assert enviados == ["1"]


def test_procura_pessoas_e_grupos_que_falaram_com_o_bot(monkeypatch):
    respostas = {
        "getMe": {"username": "boletos_escritorio_bot", "first_name": "Boletos"},
        "getUpdates": [
            {"message": {"chat": {"id": 1, "type": "private", "first_name": "Fábio", "username": "fabio"}, "text": "/start"}},
            {"my_chat_member": {"chat": {"id": -100, "type": "supergroup", "title": "Escritório"},
                                "new_chat_member": {"status": "member"}}},
            {"message": {"chat": {"id": 2, "type": "private", "first_name": "Maria", "last_name": "Souza"}, "text": "/start"}},
            {"my_chat_member": {"chat": {"id": -200, "type": "group", "title": "Grupo antigo"},
                                "new_chat_member": {"status": "left"}}},
            {"message": {"chat": {"id": 1, "type": "private", "first_name": "Fábio"}, "text": "oi"}},
        ],
    }
    monkeypatch.setattr(canais, "_telegram", lambda token, metodo, dados=None: respostas[metodo])
    encontrados = canais.procurar_chats_telegram("123:abc")
    assert encontrados["bot"]["usuario"] == "boletos_escritorio_bot"
    assert [(c["chat_id"], c["nome"], c["tipo"]) for c in encontrados["chats"]] == [
        ("1", "Fábio", "privado"), ("2", "Maria Souza", "privado"), ("-100", "Escritório", "grupo")]
```

## `tests/test_texto.py` (103 linhas)

```python
from datetime import date
from decimal import Decimal

from app.boleto.texto import (
    Segmento,
    encontrar_codigos,
    extrair_beneficiario,
    extrair_campos,
    extrair_cpf_cnpj,
    extrair_data,
    extrair_documento,
    extrair_valor,
    segmentar_palavras,
)


def test_extratores_basicos():
    assert extrair_data("Vencimento 05/11/2026") == date(2026, 11, 5)
    assert extrair_data("31/02/2026") is None
    assert extrair_valor("R$ 12.345,67") == Decimal("12345.67")
    assert extrair_valor("0,00") is None
    assert extrair_cpf_cnpj("CNPJ 12345678000195") == "12.345.678/0001-95"
    assert extrair_documento("10/10/2026 NF-123/A") == "NF-123/A"
    assert extrair_beneficiario("Agência/Código do Beneficiário") is None
    assert extrair_beneficiario("ACME LTDA - CNPJ: 12.345.678/0001-95") == "ACME LTDA"


def test_limpeza_do_beneficiario_casos_reais():
    assert extrair_beneficiario(
        "CLA AUTO PECAS MIRASSOL LTDA - 45262202000140 - AV. PRESIDENTE TANCREDO NEVES, 4543 - MIRASSOL D OESTE"
    ) == "CLA AUTO PECAS MIRASSOL LTDA"
    assert extrair_beneficiario("HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA. CNPJ/CPF: 02.359.273/0001-52") \
        == "HIPER JN-COMERCIO DE MATERIAIS P/CONSTRUCAO LTDA"
    assert extrair_beneficiario("AVENIDA PRESIDENTE TANCREDO NEVES AO LADO DO POSTO MIRASSOL II") is None
    assert extrair_beneficiario("RODOVIA BR-070 - LADO PAR 1474 SANTO ANTONIO") is None
    assert extrair_beneficiario("LOJA BOA VISTA LTDA Agência/Código do Beneficiário") == "LOJA BOA VISTA LTDA"
    assert extrair_beneficiario("COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA") \
        == "COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA"


def test_frases_com_a_palavra_beneficiario_nao_viram_nome():
    assert extrair_beneficiario("Qualquer dúvida sobre este boleto, contate o beneficiário") is None
    assert extrair_beneficiario("Após o vencimento cobrar multa de 2%") is None
    assert extrair_beneficiario("(-) Desconto/Abatimento") is None


def test_nome_em_duas_linhas_e_instrucoes_com_beneficiario():
    segmentos = [
        _seg("Beneficiário", 40, 70, 90, 78),
        _seg("COMLUC COMERCIO DE LUBRIFICANTES E", 40, 80, 220, 90),
        _seg("COMBUSTIVEIS LTDA", 40, 91, 130, 101),
        _seg("Instruções (Texto de Responsabilidade do Beneficiário)", 40, 200, 300, 208),
        _seg("(-) Desconto/Abatimento", 430, 200, 520, 208),
        _seg("Após o vencimento cobrar multa de 2%", 40, 210, 260, 220),
    ]
    campos = extrair_campos(segmentos, "\n".join(s.texto for s in segmentos), altura_pagina=842)
    assert campos["beneficiario"].valor == "COMLUC COMERCIO DE LUBRIFICANTES E COMBUSTIVEIS LTDA"


def test_datas_por_extenso_ligaduras_e_guias():
    from app.boleto.texto import corrigir_ligaduras, identificar_guia

    assert extrair_data("Vencimento: 10 de outubro de 2026") == date(2026, 10, 10)
    assert extrair_data("VENC 05/NOV/2026") == date(2026, 11, 5)
    assert corrigir_ligaduras("Beneﬁciário") == "Beneficiário"
    assert "Simples Nacional" in identificar_guia("DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL")
    assert identificar_guia("DARF - Documento de Arrecadação de Receitas Federais").startswith("Receita Federal")
    assert identificar_guia("Conta de água - Saneamento") is None


def test_linha_com_ruido_de_ocr():
    texto = "Pague até o vencimento\n0O19O.50095 40144.816069 06809.350314 3 37370000000100\n"
    codigos = encontrar_codigos(texto, date(2008, 1, 1))
    assert len(codigos) == 1 and codigos[0].resultado.valido


def test_segmentacao_de_ocr_sem_espacos():
    assert segmentar_palavras("EMPRESAEXEMPLODESERVICOSLTDA") == "EMPRESA EXEMPLO DE SERVICOS LTDA"
    assert segmentar_palavras("BANDEIRANTESCOMERCIOLTDA") == "BANDEIRANTES COMERCIO LTDA"
    assert segmentar_palavras("Empresa Normal Ltda") == "Empresa Normal Ltda"
    assert segmentar_palavras("MESA") == "MESA"


def _seg(texto, x0, y0, x1, y1):
    return Segmento(texto, x0, y0, x1, y1)


def test_campos_por_posicao_rotulo_acima_e_valor_a_direita():
    segmentos = [
        _seg("Beneficiário", 40, 70, 90, 78),
        _seg("LOJA DO BAIRRO LTDA", 40, 80, 200, 90),
        _seg("Vencimento", 430, 70, 470, 78),
        _seg("15/12/2026", 510, 80, 560, 90),  # alinhado à direita
        _seg("Nº do Documento", 40, 100, 110, 108),
        _seg("000123-4", 40, 110, 90, 120),
        _seg("Valor do Documento", 430, 100, 500, 108),
        _seg("89,90", 530, 110, 560, 120),
    ]
    campos = extrair_campos(segmentos, "\n".join(s.texto for s in segmentos), altura_pagina=842)
    assert campos["beneficiario"].valor == "LOJA DO BAIRRO LTDA"
    assert campos["vencimento"].valor == date(2026, 12, 15)
    assert campos["numero_documento"].valor == "000123-4"
    assert campos["valor"].valor == Decimal("89.90")
```

## `tests/test_usuarios.py` (133 linhas)

```python
"""Usuários do escritório: login por pessoa, quem lançou/pagou, comprovante e histórico de cada boleto."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import acesso, admin, contexto, main, usuarios
from app.arquivos import RepositorioArquivos
from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx", tmp_path / "backups")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    gerenciador = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json")
    original = contexto.usuarios
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "fila", fila)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "repositorio_pix", RepositorioBoletos(planilha, fila, "pix"))
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    monkeypatch.setattr(contexto, "usuarios", gerenciador)
    acesso.configurar_usuarios(gerenciador)
    yield planilha, gerenciador
    acesso.configurar_usuarios(original)


def _boleto(cliente, beneficiario="Papelaria Central"):
    resposta = cliente.post("/api/boletos", json={
        "beneficiario": beneficiario, "valor": 89.9, "vencimento": (date.today() + timedelta(days=5)).isoformat(),
        "ignorar_validacao": True})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_login_por_pessoa_registra_quem_lancou_pagou_e_anexou(sistema):
    planilha, gerenciador = sistema
    with TestClient(main.app, client=("127.0.0.1", 50000)) as computador:
        # Sem usuários cadastrados: funciona como antes, e o computador aparece como autor
        assert _boleto(computador)["lancado_por"] == "Computador principal"

        # Só o administrador cadastra usuários
        assert computador.post("/api/usuarios", json={"nome": "Maria", "senha": "123456"}).status_code == 403
        computador.post("/api/admin/senha", json={"senha": "senha-do-dono", "confirmacao": "senha-do-dono"})
        assert computador.post("/api/usuarios", json={"nome": "Maria", "senha": "123"}).status_code == 422
        criado = computador.post("/api/usuarios", json={"nome": "Maria Souza", "login": "Maria", "senha": "maria-2026"})
        assert criado.status_code == 201 and criado.json()["criado"]["login"] == "maria"
        assert computador.post("/api/usuarios", json={"nome": "Outra Maria", "login": "maria", "senha": "123456"}).status_code == 422
        id_maria = criado.json()["criado"]["id"]
        assert "senha_hash" not in str(computador.get("/api/usuarios").json())

    with TestClient(main.app, client=("192.168.0.50", 50000)) as celular:
        estado = celular.get("/api/acesso/estado").json()
        assert estado["usuarios"] and not estado["autorizado"]
        assert celular.get("/api/boletos").json()["detail"]["codigo"] == "login_necessario"
        assert celular.post("/api/usuarios/entrar", json={"login": "maria", "senha": "errada"}).status_code == 401
        assert celular.post("/api/usuarios/entrar", json={"login": "ninguem", "senha": "errada"}).status_code == 401
        entrou = celular.post("/api/usuarios/entrar", json={"login": " Maria ", "senha": "maria-2026"})
        assert entrou.status_code == 200 and entrou.json()["usuario"]["nome"] == "Maria Souza"
        assert celular.get("/api/acesso/estado").json()["usuario"]["nome"] == "Maria Souza"

        boleto = _boleto(celular, "Energia Elétrica")
        assert boleto["lancado_por"] == "Maria Souza" and not boleto["pago_por"]
        pago = celular.patch(f"/api/boletos/{boleto['id']}/status", json={"status": "Pago"}).json()
        assert pago["pago_por"] == "Maria Souza"

        # Comprovante é opcional, aceita PDF ou foto e pode ser visto e removido
        assert celular.post(f"/api/boletos/{boleto['id']}/comprovante",
                            files={"arquivo": ("nota.txt", b"texto qualquer", "text/plain")}).status_code == 422
        anexado = celular.post(f"/api/boletos/{boleto['id']}/comprovante",
                               files={"arquivo": ("comprovante.pdf", PDF, "application/pdf")})
        assert anexado.status_code == 200 and anexado.json()["comprovante_nome"] == "comprovante.pdf"
        assert celular.get(f"/api/boletos/{boleto['id']}/comprovante").headers["content-type"] == "application/pdf"

        eventos = celular.get(f"/api/boletos/{boleto['id']}/historico").json()["eventos"]
        assert [(e["acao"], e["usuario"]) for e in eventos] == [
            ("Comprovante", "Maria Souza"), ("Pagamento", "Maria Souza"), ("Lançamento", "Maria Souza")]
        assert eventos[0]["detalhes"] == "Comprovante anexado: comprovante.pdf"

        # Voltar para pendente limpa o "Pago por"
        assert celular.patch(f"/api/boletos/{boleto['id']}/status", json={"status": "Pendente"}).json()["pago_por"] in ("", None)
        assert celular.delete(f"/api/boletos/{boleto['id']}/comprovante").status_code == 204
        assert celular.get(f"/api/boletos/{boleto['id']}/comprovante").status_code == 404

    wb = load_workbook(planilha.caminho)
    historico = wb["Histórico"]
    assert historico.cell(row=1, column=8).value == "Usuário"
    assert {historico.cell(row=r, column=8).value for r in range(2, historico.max_row + 1)} >= {"Computador principal", "Maria Souza"}
    cabecalho = [c.value for c in wb["Boletos"][1]]
    assert {"Lançado por", "Pago por", "Comprovante"} <= set(cabecalho)

    # Desativar a pessoa desconecta os aparelhos dela
    gerenciador.alterar(id_maria, ativo=False)
    assert not gerenciador.em_uso
    assert gerenciador.usuario_da_sessao(entrou.cookies.get(usuarios.COOKIE)) is None


def test_exigir_login_tambem_no_computador(sistema):
    _, gerenciador = sistema
    gerenciador.criar("Fábio", "fabio", "senha-fabio")
    with TestClient(main.app, client=("127.0.0.1", 50000)) as computador:
        assert computador.get("/api/boletos").status_code == 200  # padrão: o computador não pede login
        gerenciador.definir_exigir_login_no_computador(True)
        assert computador.get("/api/boletos").json()["detail"]["codigo"] == "login_necessario"
        assert computador.get("/api/admin").status_code == 200  # a área de administrador continua acessível
        assert computador.post("/api/usuarios/entrar", json={"login": "fabio", "senha": "senha-fabio"}).status_code == 200
        assert computador.get("/api/boletos").status_code == 200
        assert computador.post("/api/usuarios/minha-senha", json={"senha_atual": "errada", "senha": "nova-senha",
                                                                   "confirmacao": "nova-senha"}).status_code == 422
        assert computador.post("/api/usuarios/minha-senha", json={"senha_atual": "senha-fabio", "senha": "nova-senha",
                                                                   "confirmacao": "nova-senha"}).status_code == 200
        computador.post("/api/usuarios/sair")
        assert computador.get("/api/boletos").status_code == 401


def test_bloqueio_apos_senhas_erradas(tmp_path):
    gerenciador = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json")
    gerenciador.criar("Ana", "ana", "senha-ana")
    for _ in range(usuarios.MAX_TENTATIVAS):
        assert gerenciador.entrar("ana", "errada", "10.0.0.9")[0] is None
    token, _, bloqueio = gerenciador.entrar("ana", "senha-ana", "10.0.0.9")
    assert token is None and bloqueio > 0
    token, usuario, _ = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json").entrar("ana", "senha-ana", "10.0.0.9")
    assert token and usuario["nome"] == "Ana"
    assert "senha-ana" not in (tmp_path / "usuarios.json").read_text(encoding="utf-8")
```

## `tests/test_versao.py` (149 linhas)

```python
"""Controle de versão: número, histórico (VERSOES.md), guardar uma versão nova, voltar a uma antiga e a API."""

import importlib.util
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main, versao

RAIZ = Path(__file__).resolve().parent.parent
precisa_do_git = pytest.mark.skipif(shutil.which("git") is None, reason="git não instalado")


def _ferramenta():
    spec = importlib.util.spec_from_file_location("ferramenta_versao", RAIZ / "ferramentas" / "versao.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _git(pasta: Path, *argumentos: str) -> str:
    return subprocess.run(["git", *argumentos], cwd=pasta, capture_output=True, text=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def sistema(tmp_path):
    """Uma pasta de sistema em miniatura, com repositório e a versão 1.0.0 guardada."""
    pasta = tmp_path / "sistema"
    (pasta / "app").mkdir(parents=True)
    (pasta / "app" / "__init__.py").write_text('"""Sistema."""\n\n__version__ = "1.0.0"\n', encoding="utf-8")
    (pasta / "VERSOES.md").write_text("# Histórico de versões\n\n> explicação\n\n## v1.0.0 — 01/10/2026 — Primeira\n- nasceu\n",
                                      encoding="utf-8")
    (pasta / "codigo.txt").write_text("versão um\n", encoding="utf-8")
    (pasta / ".gitignore").write_text("dados/\n", encoding="utf-8")
    (pasta / "dados").mkdir()
    (pasta / "dados" / "boletos.db").write_bytes(b"dados reais")
    if shutil.which("git"):
        _git(pasta, "init", "-q", "-b", "main")
        _git(pasta, "config", "user.name", "Teste")
        _git(pasta, "config", "user.email", "teste@exemplo.com")
        _git(pasta, "config", "commit.gpgsign", "false")
        _git(pasta, "add", "-A")
        _git(pasta, "commit", "-q", "-m", "v1.0.0 — Primeira")
        _git(pasta, "tag", "-a", "v1.0.0", "-m", "v1.0.0 — Primeira")
    return pasta


def test_proxima_versao_por_tipo():
    assert versao.proxima("1.9.0", "correcao") == "1.9.1"
    assert versao.proxima("1.9.1", "melhoria") == "1.10.0"
    assert versao.proxima("1.10.3", "grande") == "2.0.0"
    with pytest.raises(versao.ErroVersao):
        versao.proxima("1.9", "melhoria")
    with pytest.raises(versao.ErroVersao):
        versao.proxima("1.9.0", "enorme")


def test_historico_e_registro_no_topo(sistema):
    assert versao.historico(sistema) == [{"versao": "1.0.0", "data": "2026-10-01", "titulo": "Primeira", "itens": ["nasceu"]}]
    versao.registrar("1.1.0", "  Relatórios   novos ", ["um", " dois  itens ", ""], date(2026, 10, 10), raiz=sistema)
    lista = versao.historico(sistema)
    assert [v["versao"] for v in lista] == ["1.1.0", "1.0.0"]
    assert lista[0] == {"versao": "1.1.0", "data": "2026-10-10", "titulo": "Relatórios novos", "itens": ["um", "dois itens"]}
    texto = (sistema / "VERSOES.md").read_text(encoding="utf-8")
    assert texto.startswith("# Histórico de versões\n\n> explicação\n\n## v1.1.0 — 10/10/2026 — Relatórios novos\n- um\n")
    with pytest.raises(versao.ErroVersao):
        versao.registrar("1.1.0", "Repetida", raiz=sistema)
    versao.definir_versao("1.1.0", sistema)
    assert versao.versao_atual(sistema) == "1.1.0" and '"""Sistema."""' in (sistema / "app" / "__init__.py").read_text(encoding="utf-8")


@precisa_do_git
def test_guardar_versao_nova(sistema, capsys):
    ferramenta = _ferramenta()
    assert ferramenta.main(["nova", "Nada mudou", "--sem-testes"], raiz=sistema) == 0  # sem alterações: não cria versão
    assert versao.versao_atual(sistema) == "1.0.0"

    (sistema / "codigo.txt").write_text("versão dois\n", encoding="utf-8")
    (sistema / "novo.txt").write_text("arquivo novo\n", encoding="utf-8")
    assert sorted(versao.alteracoes_pendentes(sistema)) == ["codigo.txt", "novo.txt"]
    assert ferramenta.main(["nova", "Relatório novo", "-m", "tela de relatórios", "--sem-testes"], raiz=sistema) == 0
    assert versao.versao_atual(sistema) == "1.1.0" and versao.alteracoes_pendentes(sistema) == []
    assert [e["etiqueta"] for e in versao.etiquetas(sistema)] == ["v1.1.0", "v1.0.0"]
    assert versao.historico(sistema)[0]["itens"] == ["tela de relatórios"]
    assert "v1.1.0 — Relatório novo" in _git(sistema, "log", "-1", "--format=%s")
    estado = versao.repositorio(sistema)
    assert estado["disponivel"] and estado["pendentes"] == 0 and estado["versoes_guardadas"] == 2

    assert ferramenta.main(["nova", "Ajuste", "--tipo", "correcao", "--sem-testes"], raiz=sistema) == 0  # nada mudou
    (sistema / "codigo.txt").write_text("versão dois e meio\n", encoding="utf-8")
    assert ferramenta.main(["nova", "Ajuste", "--tipo", "correcao", "--sem-testes"], raiz=sistema) == 0
    assert versao.versao_atual(sistema) == "1.1.1"
    assert ferramenta.main(["listar"], raiz=sistema) == 0 and "v1.1.1" in capsys.readouterr().out


@precisa_do_git
def test_voltar_para_uma_versao_antiga_sem_perder_nada(sistema):
    ferramenta = _ferramenta()
    (sistema / "codigo.txt").write_text("versão dois\n", encoding="utf-8")
    (sistema / "novo.txt").write_text("arquivo novo\n", encoding="utf-8")
    ferramenta.main(["nova", "Relatório novo", "--sem-testes"], raiz=sistema)

    (sistema / "codigo.txt").write_text("rascunho\n", encoding="utf-8")
    assert ferramenta.main(["voltar", "v1.0.0"], raiz=sistema) == 1  # há alterações não guardadas: não volta
    assert (sistema / "codigo.txt").read_text(encoding="utf-8") == "rascunho\n"
    _git(sistema, "checkout", "-q", "--", "codigo.txt")
    assert ferramenta.main(["voltar", "v7.7.7"], raiz=sistema) == 1  # versão que não existe

    assert ferramenta.main(["voltar", "v1.0.0"], raiz=sistema) == 0
    assert (sistema / "codigo.txt").read_text(encoding="utf-8") == "versão um\n"
    assert not (sistema / "novo.txt").exists()  # arquivo criado depois da v1.0.0 sai
    assert (sistema / "dados" / "boletos.db").read_bytes() == b"dados reais"  # os dados nunca são tocados
    assert versao.versao_atual(sistema) == "1.1.1"  # voltar vira uma versão nova
    lista = versao.historico(sistema)
    assert [v["versao"] for v in lista] == ["1.1.1", "1.1.0", "1.0.0"] and "Voltou para a versão v1.0.0" in lista[0]["titulo"]
    assert versao.alteracoes_pendentes(sistema) == []

    assert ferramenta.main(["voltar", "v1.1.0"], raiz=sistema) == 0  # e dá para desfazer a volta
    assert (sistema / "novo.txt").read_text(encoding="utf-8") == "arquivo novo\n"
    assert versao.versao_atual(sistema) == "1.1.2"


@precisa_do_git
def test_historico_completo_num_arquivo_para_o_backup(sistema, tmp_path):
    destino = tmp_path / "backup" / "versoes" / "finpro.bundle"
    assert versao.gerar_bundle(destino, raiz=sistema) and destino.stat().st_size > 0
    assert versao.verificar_bundle(destino, raiz=sistema)
    copia = tmp_path / "outro-computador"
    _git(tmp_path, "clone", "-q", str(destino), str(copia))
    assert (copia / "codigo.txt").read_text(encoding="utf-8") == "versão um\n" and "v1.0.0" in _git(copia, "tag")
    sem_repositorio = tmp_path / "pasta-comum"
    sem_repositorio.mkdir()
    assert not versao.gerar_bundle(tmp_path / "x.bundle", raiz=sem_repositorio)
    assert versao.repositorio(sem_repositorio) == {"disponivel": False, "commit": None, "commit_data": None, "pendentes": 0,
                                                 "arquivos_pendentes": [], "versoes_guardadas": 0}


def test_api_da_versao():
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        dados = computador.get("/api/versao").json()
        assert dados["versao"] == versao.versao_atual() == computador.get("/api/status").json()["versao"]
        assert dados["historico"] and dados["historico"][0]["versao"] and "arquivos_pendentes" in dados
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        resposta = rede.get("/api/versao")
        assert resposta.status_code in (200, 401) and "arquivos_pendentes" not in resposta.json()
```

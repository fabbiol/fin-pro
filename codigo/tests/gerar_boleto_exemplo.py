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

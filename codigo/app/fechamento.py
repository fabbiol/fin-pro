"""Fechamento do mês para o contador: resumo, gastos por centro de custo, pagos e em aberto (boletos + Pix).

* base **vencimento** — tudo o que vence no mês (pagos, em aberto e cancelados);
* base **pagamento** — o que foi efetivamente pago no mês (pela data de pagamento).

Nos pagos, o valor efetivamente pago (com juros/multa ou desconto, lidos do comprovante) é o que entra nos totais.

Sai em Excel, em PDF ou num ZIP com os dois arquivos e os comprovantes de pagamento anexados.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .pix import formatar_chave

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
         "dezembro"]
SEM_CENTRO = "Sem centro de custo"
MOEDA = '"R$" #,##0.00'
COR = "0F3D3E"


def ler_mes(texto: str | None, hoje: date | None = None) -> date:
    hoje = hoje or date.today()
    if not texto:
        return hoje.replace(day=1)
    encontrado = re.fullmatch(r"(\d{4})-(\d{2})", texto.strip())
    if not encontrado or not 1 <= int(encontrado.group(2)) <= 12:
        raise ValueError("Mês inválido. Use o formato AAAA-MM.")
    return date(int(encontrado.group(1)), int(encontrado.group(2)), 1)


def _no_mes(valor, mes: date) -> bool:
    if isinstance(valor, datetime):
        valor = valor.date()
    return isinstance(valor, date) and valor.year == mes.year and valor.month == mes.month


def _item(registro: dict, tipo: str, hoje: date) -> dict:
    pix = tipo == "Pix"
    vencimento = registro.get("vencimento")
    status = registro.get("status") or "Pendente"
    valor = round(float(registro.get("valor") or 0), 2)
    pago = status == "Pago"
    valor_pago = round(float(registro.get("valor_pago") or 0), 2) or valor if pago else None
    data_pagamento = registro.get("data_pagamento")
    atraso = (data_pagamento - vencimento).days if pago and isinstance(data_pagamento, date) and isinstance(vencimento, date) else 0
    return {
        "tipo": tipo,
        "id": registro.get("id"),
        "nome": (registro.get("recebedor") if pix else registro.get("beneficiario")) or "Não informado",
        "documento": (formatar_chave(registro.get("tipo_chave"), registro.get("chave")) if pix
                      else registro.get("numero_documento") or registro.get("documento_beneficiario") or ""),
        "vencimento": vencimento,
        "valor": valor,
        "valor_pago": valor_pago,
        "juros_multa": round(float(registro.get("juros_multa") or 0), 2) if pago else 0.0,
        "desconto": round(float(registro.get("desconto") or 0), 2) if pago else 0.0,
        "dias_atraso": max(0, atraso),
        "status": status,
        "atrasado": status == "Pendente" and isinstance(vencimento, date) and vencimento < hoje,
        "data_pagamento": registro.get("data_pagamento"),
        "centro_custo": (registro.get("centro_custo") or "").strip() or SEM_CENTRO,
        "pago_por": registro.get("pago_por") or "",
        "comprovante": registro.get("comprovante") or "",
        "comprovante_nome": registro.get("comprovante_nome") or "",
        "linha_digitavel": "" if pix else registro.get("linha_digitavel") or "",
    }


def montar(boletos: list[dict], pix: list[dict], mes: date, base: str = "vencimento", hoje: date | None = None,
           caixa: list[dict] | None = None) -> dict:
    """``caixa``: saídas em dinheiro (já pagas na data da saída), no formato de ``caixa.servico.saidas_para_gastos``."""
    hoje = hoje or date.today()
    campo = "data_pagamento" if base == "pagamento" else "vencimento"
    itens = []
    for tipo, registros in (("Boleto", boletos), ("Pix", pix), ("Dinheiro", caixa or [])):
        for registro in registros:
            if registro.get("id") is None or registro["id"] < 0 or not _no_mes(registro.get(campo), mes):
                continue
            if base == "pagamento" and registro.get("status") != "Pago":
                continue
            itens.append(_item(registro, tipo, hoje))
    itens.sort(key=lambda i: (i[campo] or date.max, i["nome"].lower()))

    pagos = [i for i in itens if i["status"] == "Pago"]
    abertos = [i for i in itens if i["status"] == "Pendente"]
    cancelados = [i for i in itens if i["status"] == "Cancelado"]
    centros: dict[str, dict] = defaultdict(lambda: {"pago": 0.0, "em_aberto": 0.0, "quantidade": 0})
    for i in pagos + abertos:
        centro = centros[i["centro_custo"]]
        if i["status"] == "Pago":
            centro["pago"] += i["valor_pago"]
        else:
            centro["em_aberto"] += i["valor"]
        centro["quantidade"] += 1
    por_centro = sorted(({"centro_custo": nome, "pago": round(v["pago"], 2), "em_aberto": round(v["em_aberto"], 2),
                          "total": round(v["pago"] + v["em_aberto"], 2), "quantidade": v["quantidade"]}
                         for nome, v in centros.items()), key=lambda c: -c["total"])
    soma = lambda lista, campo="valor": round(sum(i[campo] or 0 for i in lista), 2)  # noqa: E731
    return {
        "mes": mes.strftime("%Y-%m"),
        "titulo": f"{MESES[mes.month - 1]} de {mes.year}",
        "base": base,
        "gerado_em": datetime.now().replace(microsecond=0),
        "totais": {
            "quantidade": len(pagos) + len(abertos),
            "total": round(soma(pagos, "valor_pago") + soma(abertos), 2),
            "pago": soma(pagos, "valor_pago"),
            "valor_documentos_pagos": soma(pagos),
            "juros_multa": soma(pagos, "juros_multa"),
            "desconto": soma(pagos, "desconto"),
            "pagos_com_atraso": sum(1 for i in pagos if i["dias_atraso"]),
            "em_aberto": soma(abertos),
            "atrasado": soma([i for i in abertos if i["atrasado"]]),
            "quantidade_atrasados": sum(1 for i in abertos if i["atrasado"]),
            "cancelados": len(cancelados),
            "boletos": sum(1 for i in pagos + abertos if i["tipo"] == "Boleto"),
            "pix": sum(1 for i in pagos + abertos if i["tipo"] == "Pix"),
            "dinheiro": sum(1 for i in pagos + abertos if i["tipo"] == "Dinheiro"),
            "com_comprovante": sum(1 for i in pagos if i["comprovante"]),
            "sem_comprovante": sum(1 for i in pagos if not i["comprovante"]),
        },
        "por_centro": por_centro,
        "pagos": pagos,
        "em_aberto": abertos,
        "cancelados": cancelados,
    }


def _descricao_base(f: dict) -> str:
    return ("Pagamentos feitos no mês (pela data de pagamento)" if f["base"] == "pagamento"
            else "Boletos e Pix com vencimento no mês")


def _data(valor) -> str:
    return valor.strftime("%d/%m/%Y") if isinstance(valor, (date, datetime)) else ""


def _moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --------------------------------------------------------------------------- Excel


def _cabecalho(ws, linha: int, titulos: list[tuple[str, int]]) -> None:
    for coluna, (titulo, largura) in enumerate(titulos, start=1):
        celula = ws.cell(row=linha, column=coluna, value=titulo)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=COR)
        celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        largura_atual = ws.column_dimensions[get_column_letter(coluna)].width or 0
        ws.column_dimensions[get_column_letter(coluna)].width = max(largura, largura_atual)


def _aba_lancamentos(wb, titulo: str, itens: list[dict], pagos: bool) -> None:
    ws = wb.create_sheet(titulo)
    colunas = [("Tipo", 8), ("Vencimento", 12), ("Beneficiário / Recebedor", 38), ("Documento / Chave", 24),
               ("Centro de Custo", 24), ("Valor (R$)", 14)]
    colunas += ([("Valor Pago (R$)", 14), ("Juros/Multa (R$)", 14), ("Desconto (R$)", 13), ("Pago em", 12),
                 ("Dias de atraso", 10), ("Pago por", 20), ("Comprovante", 14)] if pagos else [("Situação", 12)])
    _cabecalho(ws, 1, colunas)
    for n, i in enumerate(itens, start=2):
        valores = [i["tipo"], i["vencimento"], i["nome"], i["documento"], i["centro_custo"], i["valor"]]
        valores += ([i["valor_pago"], i["juros_multa"], i["desconto"], i["data_pagamento"], i["dias_atraso"] or None,
                     i["pago_por"], "Anexado" if i["comprovante"] else "Não anexado"] if pagos
                    else ["Atrasado" if i["atrasado"] else "A vencer"])
        for coluna, valor in enumerate(valores, start=1):
            celula = ws.cell(row=n, column=coluna, value=valor if valor != "" else None)
            if isinstance(valor, date):
                celula.number_format = "dd/mm/yyyy"
        for coluna in (6, 7, 8, 9) if pagos else (6,):
            ws.cell(row=n, column=coluna).number_format = MOEDA
    total = len(itens) + 2
    ws.cell(row=total, column=5, value="Total").font = Font(bold=True)
    for coluna in (6, 7, 8, 9) if pagos else (6,):
        letra = get_column_letter(coluna)
        celula = ws.cell(row=total, column=coluna, value=f"=SUM({letra}2:{letra}{max(total - 1, 2)})")
        celula.font = Font(bold=True)
        celula.number_format = MOEDA
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(colunas))}{max(len(itens) + 1, 1)}"


def gerar_xlsx(f: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = f"Fechamento de {f['titulo']}"
    ws["A1"].font = Font(bold=True, size=16, color=COR)
    ws["A2"] = f"{_descricao_base(f)} · gerado em {f['gerado_em']:%d/%m/%Y %H:%M} pelo Fin Pro"
    ws["A2"].font = Font(color="666666")
    t = f["totais"]
    linhas = [("Total do mês", t["total"], True), ("Pago", t["pago"], True),
              ("   valor dos documentos pagos", t["valor_documentos_pagos"], True), ("   juros e multas pagos", t["juros_multa"], True),
              ("   descontos obtidos", t["desconto"], True), ("Pagos com atraso", t["pagos_com_atraso"], False),
              ("Em aberto", t["em_aberto"], True),
              ("Em atraso", t["atrasado"], True), ("Lançamentos (boletos + Pix)", t["quantidade"], False),
              ("Boletos", t["boletos"], False), ("Pix", t["pix"], False), ("Pagos com comprovante", t["com_comprovante"], False),
              ("Pagos sem comprovante", t["sem_comprovante"], False), ("Cancelados (fora dos totais)", t["cancelados"], False)]
    for n, (rotulo, valor, moeda) in enumerate(linhas, start=4):
        ws.cell(row=n, column=1, value=rotulo)
        celula = ws.cell(row=n, column=2, value=valor)
        celula.font = Font(bold=True)
        if moeda:
            celula.number_format = MOEDA
    inicio = len(linhas) + 6
    ws.cell(row=inicio - 1, column=1, value="Por centro de custo").font = Font(bold=True, size=13, color=COR)
    _cabecalho(ws, inicio, [("Centro de Custo", 34), ("Pago", 16), ("Em aberto", 16), ("Total", 16), ("Lançamentos", 13)])
    for n, c in enumerate(f["por_centro"], start=inicio + 1):
        for coluna, valor in enumerate((c["centro_custo"], c["pago"], c["em_aberto"], c["total"], c["quantidade"]), start=1):
            celula = ws.cell(row=n, column=coluna, value=valor)
            if 2 <= coluna <= 4:
                celula.number_format = MOEDA
    _aba_lancamentos(wb, "Pagos", f["pagos"], pagos=True)
    if f["base"] == "vencimento":
        _aba_lancamentos(wb, "Em aberto", f["em_aberto"], pagos=False)
        if f["cancelados"]:
            _aba_lancamentos(wb, "Cancelados", f["cancelados"], pagos=False)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------- PDF


def gerar_pdf(f: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    cor = colors.HexColor("#0F3D3E")
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=estilos["Title"], alignment=0, textColor=cor, fontSize=18, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=estilos["Normal"], textColor=colors.HexColor("#555555"), fontSize=9)
    secao = ParagraphStyle("secao", parent=estilos["Heading2"], textColor=cor, fontSize=12, spaceBefore=10, spaceAfter=4)
    celula = ParagraphStyle("celula", parent=estilos["Normal"], fontSize=8, leading=10)

    def tabela(cabecalho, linhas, larguras, alinhar_direita=(), total=None):
        dados = [cabecalho] + [[Paragraph(str(v), celula) if isinstance(v, str) and len(v) > 22 else v for v in l] for l in linhas]
        if total:
            dados.append(total)
        t = Table(dados, colWidths=[w * mm for w in larguras], repeatRows=1, hAlign="LEFT")
        estilo = [("BACKGROUND", (0, 0), (-1, 0), cor), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                  ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DDE0")),
                  ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F7")])]
        estilo += [("ALIGN", (c, 0), (c, -1), "RIGHT") for c in alinhar_direita]
        if total:
            estilo += [("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7F0F0"))]
        t.setStyle(TableStyle(estilo))
        return t

    t = f["totais"]
    elementos = [
        Paragraph(f"Fechamento de {f['titulo']}", titulo),
        Paragraph(f"{_descricao_base(f)} · gerado em {f['gerado_em']:%d/%m/%Y %H:%M} pelo Fin Pro", sub),
        Spacer(1, 8),
        tabela(["Total do mês", "Pago", "Juros e multas", "Descontos", "Em aberto", "Em atraso", "Lançamentos", "Comprovantes"],
               [[_moeda(t["total"]), _moeda(t["pago"]), _moeda(t["juros_multa"]), _moeda(t["desconto"]), _moeda(t["em_aberto"]),
                 _moeda(t["atrasado"]), f"{t['quantidade']} ({t['boletos']} bol., {t['pix']} Pix)",
                 f"{t['com_comprovante']} de {t['com_comprovante'] + t['sem_comprovante']}"]],
               [34, 34, 32, 30, 34, 30, 45, 34]),
        Paragraph("Por centro de custo", secao),
        tabela(["Centro de custo", "Pago", "Em aberto", "Total", "Lançamentos"],
               [[c["centro_custo"], _moeda(c["pago"]), _moeda(c["em_aberto"]), _moeda(c["total"]), c["quantidade"]]
                for c in f["por_centro"]] or [["Nenhum lançamento", "", "", "", ""]],
               [113, 40, 40, 40, 40], alinhar_direita=(1, 2, 3, 4),
               total=["Total", _moeda(t["pago"]), _moeda(t["em_aberto"]), _moeda(t["total"]), t["quantidade"]]),
        Paragraph(f"Pagos ({len(f['pagos'])})", secao),
        tabela(["Venc.", "Beneficiário / Recebedor", "Centro de custo", "Valor", "Juros/multa", "Desconto", "Valor pago",
                "Pago em", "Atraso", "Pago por", "Compr."],
               [[_data(i["vencimento"]), i["nome"], i["centro_custo"], _moeda(i["valor"]), _moeda(i["juros_multa"]) if i["juros_multa"] else "",
                 _moeda(i["desconto"]) if i["desconto"] else "", _moeda(i["valor_pago"]), _data(i["data_pagamento"]),
                 f"{i['dias_atraso']} d" if i["dias_atraso"] else "", i["pago_por"], "Sim" if i["comprovante"] else "Não"]
                for i in f["pagos"]] or [["", "Nenhum pagamento", "", "", "", "", "", "", "", "", ""]],
               [20, 55, 34, 24, 22, 20, 24, 20, 13, 30, 11], alinhar_direita=(3, 4, 5, 6, 8),
               total=["", "Total pago", "", _moeda(t["valor_documentos_pagos"]), _moeda(t["juros_multa"]), _moeda(t["desconto"]),
                      _moeda(t["pago"]), "", "", "", ""]),
    ]
    if f["base"] == "vencimento":
        elementos += [
            Paragraph(f"Em aberto ({len(f['em_aberto'])})", secao),
            tabela(["Venc.", "Beneficiário / Recebedor", "Documento", "Centro de custo", "Valor", "Situação"],
                   [[_data(i["vencimento"]), i["nome"], i["documento"], i["centro_custo"], _moeda(i["valor"]),
                     "Atrasado" if i["atrasado"] else "A vencer"] for i in f["em_aberto"]] or [["", "Nada em aberto", "", "", "", ""]],
                   [22, 90, 45, 60, 30, 26], alinhar_direita=(4,), total=["", "Total em aberto", "", "", _moeda(t["em_aberto"]), ""]),
        ]
    buffer = io.BytesIO()

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawRightString(doc.pagesize[0] - 12 * mm, 8 * mm, f"Fechamento de {f['titulo']} · página {doc.page}")
        canvas.restoreState()

    documento = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                                  bottomMargin=14 * mm, title=f"Fechamento de {f['titulo']}", author="Fin Pro")
    documento.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()


# --------------------------------------------------------------------------- ZIP para o contador


def _nome_arquivo(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", sem_acento).strip("-")[:40] or "sem-nome"


def gerar_zip(f: dict, caminho_comprovante) -> bytes:
    """``caminho_comprovante(item)`` devolve o Path do comprovante anexado (ou None)."""
    buffer = io.BytesIO()
    nome_base = f"fechamento-{f['mes']}"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
        arquivo_zip.writestr(f"{nome_base}.pdf", gerar_pdf(f))
        arquivo_zip.writestr(f"{nome_base}.xlsx", gerar_xlsx(f))
        usados = set()
        faltando = []
        for i in f["pagos"]:
            caminho = caminho_comprovante(i) if i["comprovante"] else None
            if not caminho or not Path(caminho).exists():
                faltando.append(i)
                continue
            data = i["data_pagamento"] or i["vencimento"]
            nome = f"{data:%Y-%m-%d}_{_nome_arquivo(i['nome'])}_{i['valor']:.2f}".replace(".", ",")
            while nome in usados:
                nome += "_2"
            usados.add(nome)
            arquivo_zip.write(caminho, f"comprovantes/{nome}{Path(caminho).suffix.lower()}")
        if faltando:
            linhas = [f"{_data(i['data_pagamento'])}  {i['nome']}  {_moeda(i['valor'])}" for i in faltando]
            arquivo_zip.writestr("comprovantes/SEM-COMPROVANTE.txt",
                                 "Pagamentos do mês sem comprovante anexado no Fin Pro:\r\n\r\n" + "\r\n".join(linhas))
    return buffer.getvalue()

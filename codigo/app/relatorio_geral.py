"""Relatório geral do mês: junta numa tela só o que foi pago (boletos, Pix e dinheiro), os juros e multas, o caixa,
o diesel, as empresas e a previsão de saídas.

Cada parte só entra para quem tem a permissão daquela tela (``pode("gastos")``, ``pode("caixa")``…). O Excel traz o
resumo, a lista de juros e multas pagos e a comparação dos últimos 12 meses.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Callable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import contexto as ctx
from . import fechamento, servicos

log = logging.getLogger(__name__)

MESES_HISTORICO = 12
MOEDA = '"R$" #,##0.00'
COR = "0F3D3E"


def mes_vizinho(mes: date, passos: int) -> date:
    total = mes.year * 12 + mes.month - 1 + passos
    return date(total // 12, total % 12 + 1, 1)


def _soma(itens: list[dict], campo: str) -> float:
    return round(sum(float(i.get(campo) or 0) for i in itens), 2)


def _contas(boletos: list[dict], pix: list[dict], caixa: list[dict], mes: date, hoje: date) -> dict:
    """O que foi pago no mês (pela data de pagamento), o que vence no mês e os juros e multas pagos."""
    pagos = fechamento.montar(boletos, pix, mes, "pagamento", hoje, caixa=caixa)
    vence = fechamento.montar(boletos, pix, mes, "vencimento", hoje, caixa=caixa)
    por_tipo = {tipo: {"valor": _soma([i for i in pagos["pagos"] if i["tipo"] == tipo], "valor_pago"),
                       "quantidade": sum(1 for i in pagos["pagos"] if i["tipo"] == tipo)}
                for tipo in ("Boleto", "Pix", "Dinheiro")}
    juros = sorted((i for i in pagos["pagos"] if i["juros_multa"]), key=lambda i: (-i["juros_multa"], i["nome"].lower()))
    return {
        "pago": pagos["totais"]["pago"],
        "quantidade_pagos": len(pagos["pagos"]),
        "por_tipo": por_tipo,
        "juros_multa": pagos["totais"]["juros_multa"],
        "desconto": pagos["totais"]["desconto"],
        "pagos_com_atraso": pagos["totais"]["pagos_com_atraso"],
        "sem_comprovante": pagos["totais"]["sem_comprovante"],
        "por_centro": pagos["por_centro"][:8],
        "juros": [{k: i[k] for k in ("tipo", "id", "nome", "documento", "vencimento", "data_pagamento", "valor",
                                     "valor_pago", "juros_multa", "dias_atraso", "centro_custo", "pago_por")}
                  for i in juros],
        "vencimento": {k: vence["totais"][k] for k in ("total", "pago", "em_aberto", "atrasado", "quantidade_atrasados",
                                                       "quantidade")},
    }


def _historico(boletos: list[dict], pix: list[dict], caixa: list[dict], mes: date, hoje: date) -> list[dict]:
    """Os últimos 12 meses lado a lado (até o mês escolhido): quanto foi pago e quanto foi de juros."""
    saida = []
    for passo in range(MESES_HISTORICO - 1, -1, -1):
        atual = mes_vizinho(mes, -passo)
        f = fechamento.montar(boletos, pix, atual, "pagamento", hoje, caixa=caixa)
        tipo = lambda t: _soma([i for i in f["pagos"] if i["tipo"] == t], "valor_pago")  # noqa: E731
        saida.append({"mes": f["mes"], "titulo": f["titulo"], "boletos": tipo("Boleto"), "pix": tipo("Pix"),
                      "dinheiro": tipo("Dinheiro"), "pago": f["totais"]["pago"], "juros_multa": f["totais"]["juros_multa"],
                      "desconto": f["totais"]["desconto"], "quantidade": len(f["pagos"]),
                      "pagos_com_atraso": f["totais"]["pagos_com_atraso"]})
    return saida


def _caixa(mes: date) -> dict:
    from .caixa import servico

    r = servico.resumo("mes", mes)
    return {"entradas": {k: r["entradas"][k] for k in ("total", "quantidade")},
            "saidas": {k: r["saidas"][k] for k in ("total", "quantidade")},
            "saldo_periodo": r["saldo_periodo"], "saldo_caixa": r["saldo_caixa"],
            "saidas_periodo_anterior": r["saidas_periodo_anterior"], "por_centro": r["por_centro"][:5]}


def _diesel(mes: date) -> dict:
    from .diesel import servico

    r = servico.resumo("mes", mes)
    return {"comprado": r["comprado"], "abastecido": {k: r["abastecido"][k] for k in ("litros", "quantidade", "custo")},
            "preco_medio": r["preco_medio"], "saldo": (r.get("saldo") or {}).get("valor"),
            "por_maquina": [{"maquina": m["maquina"], "litros": m["litros"], "abastecimentos": m.get("abastecimentos"),
                             "custo": m.get("custo")} for m in r["por_maquina"][:5]]}


def _empresas(mes: date) -> dict:
    from .empresas import servico

    competencia = mes.strftime("%Y-%m")
    linhas = servico.resumo_empresas(competencia=competencia)
    soma = lambda chave: round(sum(float(e["fechamento"].get(chave) or 0) for e in linhas), 2)  # noqa: E731
    recebimentos = [r for r in servico.listar("recebimentos") if r.get("status") != "Cancelado"
                    and fechamento._no_mes(r.get("data"), mes)]
    cheques = servico.cheques(status="Em carteira")
    return {
        "competencia": competencia,
        "faturado": soma("total"), "recebido_do_fechamento": soma("recebido"), "falta": soma("falta"),
        "em_aberto": round(sum(e["em_aberto"] for e in linhas), 2),
        "recebido_no_mes": round(sum(float(r.get("valor") or 0) for r in recebimentos), 2),
        "recebimentos_no_mes": len(recebimentos),
        "cheques": {"quantidade": len(cheques), "valor": round(sum(float(c.get("valor") or 0) for c in cheques), 2)},
        "empresas": [{"id": e["id"], "nome": e["nome"], "total": e["fechamento"]["total"], "falta": e["fechamento"]["falta"],
                      "em_aberto": e["em_aberto"]} for e in linhas if e["fechamento"]["total"] or e["em_aberto"]][:8],
    }


def _parte(nome: str, funcao, *args):
    """Uma parte com problema (ex.: banco de outro módulo indisponível) não derruba o relatório inteiro."""
    try:
        return funcao(*args)
    except Exception as exc:  # noqa: BLE001
        log.exception("Relatório geral: falha ao montar %s", nome)
        return {"erro": str(exc) or exc.__class__.__name__}


def montar(mes: date, pode: Callable[[str], bool], hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    saida: dict = {
        "mes": mes.strftime("%Y-%m"),
        "titulo": f"{fechamento.MESES[mes.month - 1]} de {mes.year}",
        "anterior": mes_vizinho(mes, -1).strftime("%Y-%m"),
        "seguinte": mes_vizinho(mes, 1).strftime("%Y-%m"),
        "gerado_em": datetime.now().replace(microsecond=0),
    }
    boletos = ctx.repositorio.listar()
    pix = ctx.repositorio_pix.listar()
    if pode("gastos"):
        from .caixa.servico import saidas_para_gastos

        caixa = _parte("saídas do caixa", saidas_para_gastos)
        caixa = caixa if isinstance(caixa, list) else []
        saida["contas"] = _parte("contas", _contas, boletos, pix, caixa, mes, hoje)
        saida["historico"] = _parte("histórico", _historico, boletos, pix, caixa, mes, hoje)
    previsao = servicos.previsao_saidas(boletos, pix, hoje, semanas=5)
    saida["previsao"] = {"em_atraso": {k: previsao["em_atraso"][k] for k in ("total", "quantidade")},
                         **{k: previsao["totais"][k] for k in ("7_dias", "30_dias")}}
    if pode("caixa"):
        saida["caixa"] = _parte("caixa", _caixa, mes)
    if pode("diesel"):
        saida["diesel"] = _parte("diesel", _diesel, mes)
    if pode("empresas"):
        saida["empresas"] = _parte("empresas", _empresas, mes)
    return saida


# --------------------------------------------------------------------------- Excel


def _cabecalho(ws, linha: int, titulos: list[tuple[str, int]]) -> None:
    for coluna, (titulo, largura) in enumerate(titulos, start=1):
        celula = ws.cell(row=linha, column=coluna, value=titulo)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=COR)
        celula.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(coluna)].width = largura


def _titulo(ws, texto: str, subtitulo: str) -> None:
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=14, color=COR)
    ws["A2"] = subtitulo
    ws["A2"].font = Font(italic=True, color="666666")


def gerar_xlsx(r: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    _titulo(ws, f"Relatório geral · {r['titulo']}", f"Gerado em {r['gerado_em']:%d/%m/%Y %H:%M}")
    _cabecalho(ws, 4, [("Indicador", 46), ("Valor", 20), ("Detalhe", 34)])
    linhas: list[tuple[str, object, str, bool]] = []  # (indicador, valor, detalhe, é moeda)
    contas = r.get("contas") or {}
    if contas and "erro" not in contas:
        linhas += [
            ("Pago no mês (boletos, Pix e dinheiro)", contas["pago"], f"{contas['quantidade_pagos']} pagamento(s)", True),
            ("  · Boletos", contas["por_tipo"]["Boleto"]["valor"], f"{contas['por_tipo']['Boleto']['quantidade']} pago(s)", True),
            ("  · Pix", contas["por_tipo"]["Pix"]["valor"], f"{contas['por_tipo']['Pix']['quantidade']} pago(s)", True),
            ("  · Dinheiro (caixa)", contas["por_tipo"]["Dinheiro"]["valor"],
             f"{contas['por_tipo']['Dinheiro']['quantidade']} saída(s)", True),
            ("Juros e multas pagos", contas["juros_multa"], f"{contas['pagos_com_atraso']} pago(s) com atraso", True),
            ("Descontos", contas["desconto"], "", True),
            ("Vence no mês (total)", contas["vencimento"]["total"], f"{contas['vencimento']['quantidade']} lançamento(s)", True),
            ("Ainda em aberto do mês", contas["vencimento"]["em_aberto"], "", True),
            ("Em atraso", contas["vencimento"]["atrasado"], f"{contas['vencimento']['quantidade_atrasados']} lançamento(s)", True),
        ]
    previsao = r.get("previsao") or {}
    if previsao:
        linhas += [("A pagar nos próximos 7 dias (a partir de hoje)", previsao["7_dias"], "", True),
                   ("A pagar nos próximos 30 dias (a partir de hoje)", previsao["30_dias"], "", True)]
    caixa = r.get("caixa") or {}
    if caixa and "erro" not in caixa:
        linhas += [("Caixa · entradas", caixa["entradas"]["total"], f"{caixa['entradas']['quantidade']} entrada(s)", True),
                   ("Caixa · saídas", caixa["saidas"]["total"], f"{caixa['saidas']['quantidade']} saída(s)", True),
                   ("Caixa · saldo no fim do mês", caixa["saldo_caixa"], "", True)]
    diesel = r.get("diesel") or {}
    if diesel and "erro" not in diesel:
        linhas += [("Diesel · comprado (litros)", diesel["comprado"]["litros"], f"{diesel['comprado']['quantidade']} compra(s)", False),
                   ("Diesel · valor das compras", diesel["comprado"]["valor"], "", True),
                   ("Diesel · abastecido (litros)", diesel["abastecido"]["litros"],
                    f"{diesel['abastecido']['quantidade']} abastecimento(s)", False),
                   ("Diesel · custo dos abastecimentos", diesel["abastecido"]["custo"], "", True),
                   ("Diesel · saldo no posto (fim do mês)", diesel["saldo"], "", True)]
    empresas = r.get("empresas") or {}
    if empresas and "erro" not in empresas:
        linhas += [("Empresas · faturado no fechamento", empresas["faturado"], "", True),
                   ("Empresas · falta receber do fechamento", empresas["falta"], "", True),
                   ("Empresas · recebido no mês", empresas["recebido_no_mes"], f"{empresas['recebimentos_no_mes']} recebimento(s)", True),
                   ("Empresas · cheques em carteira", empresas["cheques"]["valor"], f"{empresas['cheques']['quantidade']} cheque(s)", True)]
    for n, (indicador, valor, detalhe, moeda) in enumerate(linhas, start=5):
        ws.cell(row=n, column=1, value=indicador)
        celula = ws.cell(row=n, column=2, value=valor)
        celula.number_format = MOEDA if moeda else '#,##0.0 "L"'
        ws.cell(row=n, column=3, value=detalhe)

    if contas and "erro" not in contas:
        wj = wb.create_sheet("Juros e multas")
        _titulo(wj, f"Juros e multas pagos · {r['titulo']}", f"Total: R$ {contas['juros_multa']:,.2f}".replace(",", "X")
                .replace(".", ",").replace("X", "."))
        _cabecalho(wj, 4, [("Tipo", 10), ("Beneficiário / recebedor", 40), ("Vencimento", 13), ("Pago em", 13),
                           ("Dias de atraso", 14), ("Valor do documento", 18), ("Juros/multa", 15), ("Valor pago", 15),
                           ("Centro de custo", 24), ("Pago por", 18)])
        for n, i in enumerate(contas["juros"], start=5):
            valores = [i["tipo"], i["nome"], i["vencimento"], i["data_pagamento"], i["dias_atraso"], i["valor"],
                       i["juros_multa"], i["valor_pago"], i["centro_custo"], i["pago_por"]]
            for coluna, valor in enumerate(valores, start=1):
                celula = wj.cell(row=n, column=coluna, value=valor)
                if coluna in (3, 4):
                    celula.number_format = "DD/MM/YYYY"
                elif coluna in (6, 7, 8):
                    celula.number_format = MOEDA

    if r.get("historico") and "erro" not in r["historico"]:
        wh = wb.create_sheet("Últimos 12 meses")
        _titulo(wh, "Pagamentos dos últimos 12 meses", "Pela data de pagamento")
        _cabecalho(wh, 4, [("Mês", 20), ("Boletos", 16), ("Pix", 16), ("Dinheiro", 16), ("Total pago", 16),
                           ("Juros/multa", 15), ("Descontos", 14), ("Pagamentos", 12), ("Com atraso", 12)])
        for n, h in enumerate(r["historico"], start=5):
            valores = [h["titulo"], h["boletos"], h["pix"], h["dinheiro"], h["pago"], h["juros_multa"], h["desconto"],
                       h["quantidade"], h["pagos_com_atraso"]]
            for coluna, valor in enumerate(valores, start=1):
                celula = wh.cell(row=n, column=coluna, value=valor)
                if 2 <= coluna <= 7:
                    celula.number_format = MOEDA
    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()

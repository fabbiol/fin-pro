"""Quais boletos devem ser avisados e como as mensagens são escritas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape

DIAS_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
ORDEM_CATEGORIA = {"vencido": 0, "hoje": 1, "amanha": 2, "proximos": 3}
EMOJI_CATEGORIA = {"vencido": "🔴", "hoje": "🟠", "amanha": "🟡", "proximos": "🔵"}
LIMITE_TELEGRAM = 3900


def brl(valor: float) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def chave_alerta(alerta: dict) -> str:
    """Identifica um aviso: o mesmo boleto é avisado de novo quando muda de categoria (ex.: amanhã → hoje)."""
    return f"{alerta['id']}|{alerta['vencimento']}|{alerta['categoria']}"


def montar_alertas(registros: list[dict], hoje: date, dias_antes: int = 3, incluir_vencidos: bool = True) -> list[dict]:
    """Boletos pendentes que vencem até ``dias_antes`` dias (e, opcionalmente, os já vencidos)."""
    limite = hoje + timedelta(days=max(0, dias_antes))
    alertas = []
    for r in registros:
        if r.get("status") != "Pendente":
            continue
        vencimento = r.get("vencimento")
        if not isinstance(vencimento, date) or vencimento > limite:
            continue
        dias = (vencimento - hoje).days
        if dias < 0 and not incluir_vencidos:
            continue
        categoria = "vencido" if dias < 0 else "hoje" if dias == 0 else "amanha" if dias == 1 else "proximos"
        alertas.append({
            "id": r["id"],
            "beneficiario": r.get("beneficiario") or "Beneficiário não informado",
            "numero_documento": r.get("numero_documento") or "",
            "valor": float(r.get("valor") or 0),
            "vencimento": vencimento.isoformat(),
            "dias": dias,
            "categoria": categoria,
            "fim_de_semana": dias >= 0 and vencimento.weekday() >= 5,
            "linha_digitavel": r.get("linha_digitavel") or "",
            "linha_digitos": re.sub(r"\D", "", r.get("linha_digitavel") or ""),
            "tipo_pagamento": r.get("tipo_pagamento") or "boleto",
            "chave_pix": r.get("chave_pix") or "",
        })
    alertas.sort(key=lambda a: (ORDEM_CATEGORIA[a["categoria"]], a["vencimento"], -a["valor"]))
    return alertas


def descrever_prazo(alerta: dict) -> str:
    vencimento = date.fromisoformat(alerta["vencimento"])
    dias = alerta["dias"]
    if dias < 0:
        texto = f"venceu há {-dias} dia{'s' if dias < -1 else ''} ({vencimento:%d/%m})"
    elif dias == 0:
        texto = "vence hoje"
    elif dias == 1:
        texto = f"vence amanhã ({vencimento:%d/%m})"
    else:
        texto = f"vence em {dias} dias ({DIAS_SEMANA[vencimento.weekday()]}, {vencimento:%d/%m})"
    if alerta.get("fim_de_semana"):
        texto += " · cai no fim de semana, pode ser pago no próximo dia útil"
    return texto


def alertas_da_regra(registros: list[dict], hoje: date, regra: dict) -> list[dict]:
    """Boletos atendidos por um lembrete.

    * ``vencimento``: vencem hoje;
    * ``antes``: vencem exatamente daqui a ``dias`` dias;
    * ``vencidos``: já venceram (há no máximo ``dias`` dias; 0 = sem limite).
    """
    tipo = regra.get("tipo")
    dias = int(regra.get("dias") or 0)
    if tipo == "vencidos":
        vencidos = [a for a in montar_alertas(registros, hoje, 0, True) if a["categoria"] == "vencido"]
        return [a for a in vencidos if dias == 0 or -a["dias"] <= dias]
    alvo = 0 if tipo == "vencimento" else max(1, dias)
    return [a for a in montar_alertas(registros, hoje, alvo, False) if a["dias"] == alvo]


def _titulo_individual(alerta: dict) -> str:
    if alerta.get("tipo_pagamento") == "cheque":  # cheque pré-datado: é para depositar, não para pagar
        titulo = {
            "vencido": "Cheque para depositar (passou da data)",
            "hoje": "Cheque para depositar hoje",
            "amanha": "Cheque para depositar amanhã",
        }.get(alerta["categoria"], f"Cheque para depositar em {alerta['dias']} dias")
        return titulo + (f" · lembrete {alerta['lembrete']}" if alerta.get("lembrete") else "")
    base = "Pix" if alerta.get("tipo_pagamento") == "pix" else "Boleto"
    titulo = {
        "vencido": f"{base} vencido",
        "hoje": f"{base} vence hoje",
        "amanha": f"{base} vence amanhã",
    }.get(alerta["categoria"], f"{base} vence em {alerta['dias']} dias")
    if alerta.get("lembrete"):
        titulo += f" · lembrete {alerta['lembrete']}"
    return titulo


@dataclass
class Mensagem:
    titulo: str
    resumo: str  # texto curto (notificação do Windows com vários boletos)
    texto: str  # e-mail em texto puro
    html: str  # e-mail em HTML
    telegram: str  # HTML aceito pelo Telegram
    itens: list[tuple[str, str, int | None]] = field(default_factory=list)  # (título, corpo, id do boleto)


def montar_mensagem(alertas: list[dict], hoje: date, url_app: str) -> Mensagem:
    a_vencer = [a for a in alertas if a["categoria"] != "vencido"]
    vencidos = [a for a in alertas if a["categoria"] == "vencido"]
    if len(alertas) == 1:
        titulo = _titulo_individual(alertas[0])
    else:
        partes = []
        if a_vencer:
            partes.append(f"{len(a_vencer)} boleto{'s' if len(a_vencer) > 1 else ''} a vencer")
        if vencidos:
            partes.append(f"{len(vencidos)} vencido{'s' if len(vencidos) > 1 else ''}")
        titulo = " e ".join(partes)
    total = sum(a["valor"] for a in alertas)
    link = f"{url_app}/#/boletos?situacao=pendente"

    def documento(a):
        return f" · Doc. {a['numero_documento']}" if a["numero_documento"] else ""

    itens = [(_titulo_individual(a), f"{a['beneficiario']} · {brl(a['valor'])} · {descrever_prazo(a)}", a["id"]) for a in alertas]

    resumo = "\n".join(f"{a['beneficiario']} · {brl(a['valor'])} · {descrever_prazo(a)}" for a in alertas[:3])
    if len(alertas) > 3:
        resumo += f"\n+ {len(alertas) - 3} outro(s) · total {brl(total)}"

    linhas_texto = []
    for a in alertas:
        linha = f"• {a['beneficiario']} — {brl(a['valor'])} — {descrever_prazo(a)}{documento(a)}"
        if a["linha_digitos"]:
            linha += f"\n  Linha digitável: {a['linha_digitos']}"
        elif a.get("chave_pix"):
            linha += f"\n  Chave Pix: {a['chave_pix']}"
        linhas_texto.append(linha)
    texto = f"{titulo}\n\n" + "\n".join(linhas_texto) + f"\n\nTotal: {brl(total)}\nAbrir o Fin Pro: {link}\n"

    linhas_html = []
    for a in alertas:
        cor = "#c3302a" if a["categoria"] == "vencido" else "#a86200" if a["categoria"] in ("hoje", "amanha") else "#4a5a66"
        codigo = a["linha_digitos"] or (f"Chave Pix: {a['chave_pix']}" if a.get("chave_pix") else "")
        linha_dig = (f"<div style='font-family:Consolas,monospace;font-size:12px;color:#4a5a66;margin-top:4px'>"
                     f"{escape(codigo)}</div>") if codigo else ""
        linhas_html.append(
            "<tr><td style='padding:10px 8px;border-bottom:1px solid #e2e8ec'>"
            f"<strong>{escape(a['beneficiario'])}</strong><br>"
            f"<span style='color:{cor}'>{escape(descrever_prazo(a))}</span>"
            f"<span style='color:#7d8b95'>{escape(documento(a))}</span>{linha_dig}</td>"
            "<td style='padding:10px 8px;border-bottom:1px solid #e2e8ec;text-align:right;white-space:nowrap'>"
            f"<strong>{brl(a['valor'])}</strong></td></tr>"
        )
    html = (
        "<div style='font-family:Segoe UI,Arial,sans-serif;max-width:640px;color:#0e1a22'>"
        f"<h2 style='color:#0d7a64;margin:0 0 14px'>🔔 {escape(titulo)}</h2>"
        f"<table style='width:100%;border-collapse:collapse;font-size:14px'>{''.join(linhas_html)}"
        "<tr><td style='padding:10px 8px'><strong>Total</strong></td>"
        f"<td style='padding:10px 8px;text-align:right'><strong>{brl(total)}</strong></td></tr></table>"
        f"<p style='margin-top:18px'><a href='{escape(link)}' style='color:#0d7a64'>Abrir o Fin Pro</a></p>"
        "<p style='color:#7d8b95;font-size:12px'>Aviso automático do Fin Pro.</p></div>"
    )

    cabecalho = f"🔔 <b>{escape(titulo)}</b>\n"
    rodape = f"\n<b>Total:</b> {brl(total)}"
    blocos = []
    for a in alertas:
        bloco = (f"\n{EMOJI_CATEGORIA[a['categoria']]} <b>{escape(a['beneficiario'])}</b> — {brl(a['valor'])}\n"
                 f"{escape(descrever_prazo(a))}{escape(documento(a))}")
        if a["linha_digitos"]:
            # <code>: tocar na mensagem do Telegram copia exatamente isto — por isso, só os números
            bloco += f"\n<code>{escape(a['linha_digitos'])}</code>"
        elif a.get("chave_pix"):
            bloco += f"\nChave Pix: <code>{escape(a['chave_pix'])}</code>"
        blocos.append(bloco)
    telegram = cabecalho
    for i, bloco in enumerate(blocos):
        if len(telegram) + len(bloco) + len(rodape) > LIMITE_TELEGRAM:
            telegram += f"\n\n… e mais {len(blocos) - i} boleto(s)."
            break
        telegram += bloco + "\n"
    telegram += rodape

    return Mensagem(titulo, resumo, texto, html, telegram, itens)


def mensagem_teste(url_app: str) -> Mensagem:
    titulo = "Teste do Fin Pro"
    corpo = "As notificações estão funcionando. Você será avisado sobre os boletos a vencer."
    html = (f"<div style='font-family:Segoe UI,Arial,sans-serif'><h2 style='color:#0d7a64'>🔔 {titulo}</h2>"
            f"<p>{corpo}</p><p><a href='{escape(url_app)}'>Abrir o Fin Pro</a></p></div>")
    return Mensagem(titulo, corpo, f"{titulo}\n\n{corpo}\n", html, f"🔔 <b>{titulo}</b>\n{corpo}", [(titulo, corpo, None)])

"""Resumos da semana enviados pelos canais das notificações (Telegram, e-mail e Windows).

* **Segunda-feira** — o que vence na semana: boletos e Pix a pagar, o que já está vencido, cheques a depositar,
  fechamentos das empresas que caem na semana e o saldo do caixa.
* **Sexta-feira** — o que a semana movimentou: quanto foi pago em boletos e Pix, as entradas e saídas do caixa,
  o que foi recebido das empresas, onde mais se gastou e o que ficou para a semana que vem.

``coletar(tipo, hoje)`` junta os números (lê os repositórios do ``contexto``) e ``mensagem(dados, url)`` escreve o
texto em cada formato. As duas partes são separadas para o texto poder ser testado sem banco de dados.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from html import escape

from . import contexto as ctx
from .notificacoes.regras import DIAS_SEMANA, LIMITE_TELEGRAM, Mensagem, brl

log = logging.getLogger(__name__)

TIPOS = ("segunda", "sexta")
DIA_DO_TIPO = {"segunda": 0, "sexta": 4}
LIMITE_ITENS = 12  # quantos boletos/Pix/cheques aparecem por nome (o resto entra só no total)
DIAS_CURTOS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor.strip()[:10])
        except ValueError:
            return None
    return None


def _num(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _pago(r: dict) -> float:
    """Quanto saiu de fato: o valor pago (com juros ou desconto) ou, sem ele, o valor do boleto."""
    return _num(r.get("valor_pago")) or _num(r.get("valor"))


def _bloco(itens: list[dict], valor=None) -> dict:
    valor = valor or (lambda i: _num(i.get("valor")))
    return {"quantidade": len(itens), "total": round(sum(valor(i) for i in itens), 2)}


def semana(hoje: date) -> tuple[date, date]:
    """Segunda e domingo da semana de ``hoje``."""
    inicio = hoje - timedelta(days=hoje.weekday())
    return inicio, inicio + timedelta(days=6)


# --------------------------------------------------------------------------- coleta


def _a_pagar() -> list[dict]:
    """Boletos e Pix pendentes, num formato só (nome, vencimento, valor, tipo)."""
    itens = []
    for r in ctx.repositorio.listar():
        if r.get("status") == "Pendente":
            itens.append({"nome": r.get("beneficiario") or "Beneficiário não informado", "vencimento": _data(r.get("vencimento")),
                          "valor": _num(r.get("valor")), "tipo": "boleto"})
    for r in ctx.repositorio_pix.listar():
        if r.get("status") == "Pendente":
            itens.append({"nome": r.get("recebedor") or "Recebedor não informado", "vencimento": _data(r.get("vencimento")),
                          "valor": _num(r.get("valor")), "tipo": "pix"})
    return itens


def _pagos_entre(repositorio, inicio: date, fim: date, campo_nome: str) -> list[dict]:
    saida = []
    for r in repositorio.listar():
        quando = _data(r.get("data_pagamento"))
        if r.get("status") == "Pago" and quando and inicio <= quando <= fim:
            vencimento = _data(r.get("vencimento"))
            saida.append({"nome": r.get(campo_nome) or "", "valor": _pago(r), "data": quando,
                          "centro": (r.get("centro_custo") or "").strip(),
                          "juros": round(_num(r.get("juros_multa")), 2), "desconto": round(_num(r.get("desconto")), 2),
                          "dias_atraso": (quando - vencimento).days if vencimento and quando > vencimento else 0})
    return saida


def _empresas(inicio: date, fim: date, hoje: date) -> dict:
    """Cheques a depositar, fechamentos da semana e o que as empresas ainda devem (nunca derruba o resumo)."""
    from .empresas import servico as emp

    saida = {"cheques": [], "fechamentos": [], "a_receber": 0.0, "atrasado": 0.0, "recebido": [], "depositados": []}
    try:
        for c in emp.cheques(status="Em carteira"):
            vencimento = _data(c.get("vencimento"))
            if vencimento and vencimento <= fim:
                saida["cheques"].append({"nome": c.get("empresa") or "Cliente", "numero": c.get("numero") or "",
                                         "vencimento": vencimento, "valor": _num(c.get("valor"))})
        for e in emp.resumo_empresas(hoje):
            if e.get("status") == "Inativa" and not e["em_aberto"]:
                continue
            saida["a_receber"] += e["em_aberto"]
            saida["atrasado"] += e["atrasado"]
            fim_fechamento = _data(e["periodo"]["fim"])
            if fim_fechamento and inicio <= fim_fechamento <= fim:
                saida["fechamentos"].append({"nome": e["nome"], "dia": fim_fechamento,
                                             "total": e["fechamento"]["total"], "falta": e["fechamento"]["falta"]})
        for r in emp.listar("recebimentos"):
            quando = _data(r.get("data"))
            if r.get("status") != "Cancelado" and quando and inicio <= quando <= fim:
                saida["recebido"].append({"nome": r.get("empresa") or "", "forma": r.get("forma") or "",
                                          "valor": _num(r.get("valor"))})
        for c in emp.cheques():
            quando = _data(c.get("data_deposito"))
            if c.get("status") in ("Depositado", "Compensado") and quando and inicio <= quando <= fim:
                saida["depositados"].append({"nome": c.get("empresa") or "", "numero": c.get("numero") or "",
                                             "valor": _num(c.get("valor"))})
    except Exception:
        log.exception("Resumo da semana: falha ao ler as empresas")
    saida["cheques"].sort(key=lambda c: c["vencimento"])
    saida["a_receber"] = round(saida["a_receber"], 2)
    saida["atrasado"] = round(saida["atrasado"], 2)
    return saida


def _caixa(inicio: date, fim: date) -> dict:
    from .caixa import servico as caixa

    try:
        lancamentos = caixa.listar(inicio, fim)
        entradas = [r for r in lancamentos if r.get("movimento") == "Entrada"]
        saidas = [r for r in lancamentos if r.get("movimento") == "Saída"]
        return {"entradas": _bloco(entradas), "saidas": _bloco(saidas), "saldo": caixa.saldo_ate(fim),
                "lista_saidas": [{"nome": r.get("local") or r.get("descricao") or "", "valor": _num(r.get("valor")),
                                  "centro": (r.get("centro_custo") or "").strip()} for r in saidas]}
    except Exception:
        log.exception("Resumo da semana: falha ao ler o caixa")
        return {"entradas": _bloco([]), "saidas": _bloco([]), "saldo": 0.0, "lista_saidas": []}


def coletar(tipo: str, hoje: date | None = None) -> dict:
    hoje = hoje or date.today()
    inicio, fim = semana(hoje)
    pendentes = _a_pagar()
    vencidos = sorted([i for i in pendentes if i["vencimento"] and i["vencimento"] < hoje], key=lambda i: i["vencimento"])
    dados = {"tipo": tipo, "hoje": hoje, "inicio": inicio, "fim": fim, "vencidos": vencidos}

    if tipo == "segunda":
        na_semana = sorted([i for i in pendentes if i["vencimento"] and hoje <= i["vencimento"] <= fim],
                           key=lambda i: (i["vencimento"], i["nome"].lower()))
        dados.update(a_pagar=na_semana, empresas=_empresas(inicio, fim, hoje), caixa=_caixa(inicio, fim))
        return dados

    # sexta: da segunda até hoje (se for enviado no sábado ou domingo, a semana inteira)
    ate = max(hoje, inicio)
    boletos = _pagos_entre(ctx.repositorio, inicio, ate, "beneficiario")
    pix = _pagos_entre(ctx.repositorio_pix, inicio, ate, "recebedor")
    caixa = _caixa(inicio, ate)
    centros: dict[str, float] = {}
    for item in [*boletos, *pix, *caixa["lista_saidas"]]:
        nome = item["centro"] or "Sem centro de custo"
        centros[nome] = centros.get(nome, 0.0) + item["valor"]
    proxima_inicio = fim + timedelta(days=1)
    proxima_fim = proxima_inicio + timedelta(days=6)
    dados.update(
        ate=ate,
        boletos=_bloco(boletos), pix=_bloco(pix), caixa=caixa,
        juros={"boletos": round(sum(b["juros"] for b in boletos), 2), "pix": round(sum(p["juros"] for p in pix), 2),
               "desconto": round(sum(i["desconto"] for i in [*boletos, *pix]), 2),
               "lista": sorted([{**i, "tipo": tipo} for tipo, lista in (("boleto", boletos), ("pix", pix))
                                for i in lista if i["juros"] > 0], key=lambda i: -i["juros"])},
        maiores=sorted([*[{**b, "tipo": "boleto"} for b in boletos], *[{**p, "tipo": "pix"} for p in pix]],
                       key=lambda i: -i["valor"])[:5],
        centros=sorted(centros.items(), key=lambda c: -c[1])[:5],
        empresas=_empresas(inicio, ate, hoje),
        resto_da_semana=sorted([i for i in pendentes if i["vencimento"] and hoje <= i["vencimento"] <= fim],
                               key=lambda i: (i["vencimento"], i["nome"].lower())),
        proxima_semana=sorted([i for i in pendentes if i["vencimento"] and proxima_inicio <= i["vencimento"] <= proxima_fim],
                              key=lambda i: (i["vencimento"], i["nome"].lower())),
        proxima=(proxima_inicio, proxima_fim),
    )
    dados["total_saiu"] = round(dados["boletos"]["total"] + dados["pix"]["total"] + caixa["saidas"]["total"], 2)
    dados["total_recebido"] = round(sum(r["valor"] for r in dados["empresas"]["recebido"]) + caixa["entradas"]["total"], 2)
    return dados


# --------------------------------------------------------------------------- texto


def _dia(d: date) -> str:
    return f"{DIAS_CURTOS[d.weekday()]} {d:%d/%m}"


def _qtd(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


class _Texto:
    """Monta a mesma mensagem em texto puro, HTML do e-mail e HTML do Telegram."""

    def __init__(self, titulo: str):
        self.titulo = titulo
        self.secoes: list[tuple[str, list[str], str]] = []  # (título, linhas, total)

    def secao(self, titulo: str, linhas: list[str], total: str = "") -> None:
        self.secoes.append((titulo, linhas, total))

    def telegram(self, rodape: str) -> str:
        partes = [f"<b>{escape(self.titulo)}</b>"]
        for titulo, linhas, total in self.secoes:
            bloco = f"\n<b>{escape(titulo)}</b>" + (f" — <b>{escape(total)}</b>" if total else "")
            bloco += "".join(f"\n{escape(l)}" for l in linhas)
            if len("\n".join(partes)) + len(bloco) + len(rodape) > LIMITE_TELEGRAM:
                partes.append("\n… (mensagem resumida; veja o resto no sistema)")
                break
            partes.append(bloco)
        return "\n".join(partes) + f"\n\n{rodape}"

    def texto(self, link: str) -> str:
        corpo = [self.titulo, ""]
        for titulo, linhas, total in self.secoes:
            corpo.append(f"{titulo}{f' — {total}' if total else ''}")
            corpo += [f"  {l}" for l in linhas]
            corpo.append("")
        return "\n".join(corpo) + f"Abrir o Fin Pro: {link}\n"

    def html(self, link: str) -> str:
        blocos = []
        for titulo, linhas, total in self.secoes:
            itens = "".join(f"<li style='margin:2px 0'>{escape(l)}</li>" for l in linhas)
            blocos.append(f"<h3 style='margin:18px 0 6px;font-size:15px'>{escape(titulo)}"
                          + (f" <span style='color:#0d7a64'>— {escape(total)}</span>" if total else "") + "</h3>"
                          + (f"<ul style='margin:0;padding-left:18px;color:#33434d'>{itens}</ul>" if itens else ""))
        return ("<div style='font-family:Segoe UI,Arial,sans-serif;max-width:640px;color:#0e1a22;font-size:14px'>"
                f"<h2 style='color:#0d7a64;margin:0 0 8px'>{escape(self.titulo)}</h2>{''.join(blocos)}"
                f"<p style='margin-top:18px'><a href='{escape(link)}' style='color:#0d7a64'>Abrir o Fin Pro</a></p>"
                "<p style='color:#7d8b95;font-size:12px'>Resumo automático do Fin Pro.</p></div>")


def _linhas_a_pagar(itens: list[dict]) -> list[str]:
    linhas = [f"• {_dia(i['vencimento'])} · {i['nome']}{' (Pix)' if i['tipo'] == 'pix' else ''} — {brl(i['valor'])}"
              for i in itens[:LIMITE_ITENS]]
    if len(itens) > LIMITE_ITENS:
        linhas.append(f"… e mais {len(itens) - LIMITE_ITENS} ({brl(sum(i['valor'] for i in itens[LIMITE_ITENS:]))})")
    return linhas


def _linha_cheque(c: dict, hoje: date) -> str:
    numero = f" · nº {c['numero']}" if c["numero"] else ""
    atrasado = " (já pode depositar)" if c["vencimento"] < hoje else ""
    return f"• {_dia(c['vencimento'])} · {c['nome']}{numero} — {brl(c['valor'])}{atrasado}"


def _mensagem_segunda(d: dict, link: str) -> Mensagem:
    t = _Texto(f"📅 Resumo da semana · {d['inicio']:%d/%m} a {d['fim']:%d/%m}")
    a_pagar = d["a_pagar"]
    boletos = [i for i in a_pagar if i["tipo"] == "boleto"]
    pix = [i for i in a_pagar if i["tipo"] == "pix"]
    total = sum(i["valor"] for i in a_pagar)
    if a_pagar:
        partes = [p for p in (_qtd(len(boletos), "boleto", "boletos") if boletos else "",
                              _qtd(len(pix), "Pix", "Pix") if pix else "") if p]
        t.secao(f"💸 A pagar nesta semana ({' e '.join(partes)})", _linhas_a_pagar(a_pagar), brl(total))
    else:
        t.secao("💸 A pagar nesta semana", ["Nada vence nesta semana."])
    if d["vencidos"]:
        t.secao(f"🔴 Já vencidos, ainda em aberto ({len(d['vencidos'])})", _linhas_a_pagar(d["vencidos"]),
                brl(sum(i["valor"] for i in d["vencidos"])))
    emp = d["empresas"]
    if emp["cheques"]:
        t.secao(f"🧾 Cheques a depositar ({len(emp['cheques'])})",
                [_linha_cheque(c, d["hoje"]) for c in emp["cheques"][:LIMITE_ITENS]],
                brl(sum(c["valor"] for c in emp["cheques"])))
    if emp["fechamentos"]:
        t.secao("🏢 Fechamentos das empresas nesta semana",
                [f"• {_dia(f['dia'])} · {f['nome']} — {brl(f['total'])}"
                 + (f" (falta receber {brl(f['falta'])})" if f["falta"] > 0 else "") for f in emp["fechamentos"]])
    if emp["a_receber"] > 0:
        linhas = [f"Total em aberto das empresas: {brl(emp['a_receber'])}"]
        if emp["atrasado"] > 0:
            linhas.append(f"De fechamentos anteriores (atrasado): {brl(emp['atrasado'])}")
        t.secao("💰 A receber", linhas)
    t.secao("💵 Caixa", [f"Saldo em caixa: {brl(d['caixa']['saldo'])}"])

    titulo = f"Semana: {_qtd(len(a_pagar), 'pagamento', 'pagamentos')} · {brl(total)}"
    resumo = f"{brl(total)} a pagar nesta semana"
    if d["vencidos"]:
        resumo += f" · {len(d['vencidos'])} vencido(s)"
    if emp["cheques"]:
        resumo += f" · {len(emp['cheques'])} cheque(s) a depositar"
    return Mensagem(titulo, resumo, t.texto(link), t.html(link), t.telegram(f"<b>Total da semana:</b> {brl(total)}"),
                    [(titulo, resumo, None)])


def _mensagem_sexta(d: dict, link: str) -> Mensagem:
    t = _Texto(f"✅ Fechamento da semana · {d['inicio']:%d/%m} a {d['ate']:%d/%m}")
    caixa = d["caixa"]
    juros = d["juros"]
    com_juros = lambda valor: f" (juros/multa {brl(valor)})" if valor else ""  # noqa: E731
    t.secao("💸 O que foi pago", [
        f"Boletos: {_qtd(d['boletos']['quantidade'], 'pago', 'pagos')} — {brl(d['boletos']['total'])}{com_juros(juros['boletos'])}",
        f"Pix: {_qtd(d['pix']['quantidade'], 'pago', 'pagos')} — {brl(d['pix']['total'])}{com_juros(juros['pix'])}",
        f"Saídas do caixa (dinheiro): {_qtd(caixa['saidas']['quantidade'], 'lançamento', 'lançamentos')} — "
        f"{brl(caixa['saidas']['total'])}",
    ], brl(d["total_saiu"]))
    total_juros = round(juros["boletos"] + juros["pix"], 2)
    linhas_juros = [f"• {i['nome']}{' (Pix)' if i['tipo'] == 'pix' else ''} — juros/multa {brl(i['juros'])}"
                    + (f" · pago com {i['dias_atraso']} dia(s) de atraso" if i["dias_atraso"] else "")
                    for i in juros["lista"][:LIMITE_ITENS]]
    if juros["desconto"]:
        linhas_juros.append(f"Descontos na semana: {brl(juros['desconto'])}")
    t.secao("⚠️ Juros e multas pagos", linhas_juros or ["Nenhum juro ou multa pago nesta semana. 👍"], brl(total_juros))
    if d["maiores"]:
        t.secao("🔝 Maiores pagamentos", [f"• {i['nome']}{' (Pix)' if i['tipo'] == 'pix' else ''} — {brl(i['valor'])}"
                                          for i in d["maiores"]])
    if d["centros"]:
        t.secao("📊 Onde mais se gastou (centro de custo)", [f"• {nome} — {brl(valor)}" for nome, valor in d["centros"]])
    emp = d["empresas"]
    entradas = [f"Entradas no caixa: {_qtd(caixa['entradas']['quantidade'], 'lançamento', 'lançamentos')} — "
                f"{brl(caixa['entradas']['total'])}"]
    formas: dict[str, float] = {}
    for r in emp["recebido"]:
        formas[r["forma"] or "Outros"] = formas.get(r["forma"] or "Outros", 0.0) + r["valor"]
    entradas += [f"Recebido das empresas ({forma}): {brl(valor)}" for forma, valor in sorted(formas.items())]
    if emp["depositados"]:
        entradas.append(f"Cheques depositados: {len(emp['depositados'])} — "
                        f"{brl(sum(c['valor'] for c in emp['depositados']))}")
    t.secao("💰 O que entrou", entradas, brl(d["total_recebido"]))
    t.secao("💵 Caixa", [f"Saldo em caixa hoje: {brl(caixa['saldo'])}"])

    pendencias = []
    if d["vencidos"]:
        pendencias.append(f"🔴 Vencidos em aberto: {len(d['vencidos'])} — {brl(sum(i['valor'] for i in d['vencidos']))}")
    resto = d["resto_da_semana"]
    if resto:
        pendencias.append(f"🟠 Ainda nesta semana (até {d['fim']:%d/%m}): {_qtd(len(resto), 'pagamento', 'pagamentos')} — "
                          f"{brl(sum(i['valor'] for i in resto))}")
    semana_que_vem = d["proxima_semana"]
    if semana_que_vem:
        pendencias.append(f"📅 Semana que vem ({d['proxima'][0]:%d/%m} a {d['proxima'][1]:%d/%m}): "
                          f"{_qtd(len(semana_que_vem), 'pagamento', 'pagamentos')} — {brl(sum(i['valor'] for i in semana_que_vem))}")
    if emp["cheques"]:
        pendencias.append(f"🧾 Cheques a depositar: {len(emp['cheques'])} — {brl(sum(c['valor'] for c in emp['cheques']))}")
    t.secao("⏭️ O que ficou pendente", pendencias or ["Nada pendente. Semana fechada! 🎉"])

    titulo = f"Semana: pago {brl(d['total_saiu'])}"
    resumo = (f"Boletos {brl(d['boletos']['total'])} · Pix {brl(d['pix']['total'])} · "
              f"Caixa {brl(caixa['saidas']['total'])}" + (f" · juros {brl(total_juros)}" if total_juros else ""))
    return Mensagem(titulo, resumo, t.texto(link), t.html(link),
                    t.telegram(f"<b>Total pago na semana:</b> {brl(d['total_saiu'])}"), [(titulo, resumo, None)])


def mensagem(dados: dict, url_app: str) -> Mensagem:
    link = f"{url_app.rstrip('/')}/#/painel"
    return _mensagem_segunda(dados, link) if dados["tipo"] == "segunda" else _mensagem_sexta(dados, link)


def nome_do_dia(tipo: str) -> str:
    return DIAS_SEMANA[DIA_DO_TIPO[tipo]]

"""Relatório do diesel em três níveis — **simples**, **detalhado** e **completo** — na tela, no Telegram e no Excel.

* **simples**: quanto foi abastecido (R$ e litros), o saldo no posto e quanto tempo ele dura, e quanto cada máquina gastou;
* **detalhado**: + comparação com o período anterior, pontos de atenção, consumo (L/h, km/L), combustíveis e compras;
* **completo**: + cada abastecimento com o consumo do trecho (desde o abastecimento anterior), por dia, por posto e
  por pessoa.

A base é ``servico.resumo``; aqui entram as contas que só o relatório usa.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from html import escape

from . import servico
from .servico import combustivel_de, litros_br, moeda, valor_do_abastecimento

NIVEIS = ("simples", "detalhado", "completo")
NIVEL_PADRAO = "simples"
# consumo por dia acima da média dos 90 dias anteriores que vira ponto de atenção (numa semana o consumo varia mais)
ACIMA_DO_NORMAL = {"semana": 1.5, "quinzena": 1.4, "mes": 1.3, "ano": 1.3}
HISTORICO_MINIMO = 14  # dias de histórico da máquina para existir um "normal"
LITROS_MINIMOS_ALERTA = 50.0  # abaixo disso a variação não diz nada
DIAS_RITMO = 30  # o ritmo de gasto (para a previsão do saldo) é o dos últimos 30 dias
LIMITE_TELEGRAM = 3900  # a mensagem do Telegram aceita até 4.096 caracteres
DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
TITULOS = {"semana": "semanal", "quinzena": "quinzenal", "mes": "mensal", "ano": "anual"}
ANTERIOR = {"semana": "à semana anterior", "quinzena": "à quinzena anterior", "mes": "ao mês anterior",
            "ano": "ao ano anterior"}


def nivel_valido(nivel: str | None) -> str:
    return nivel if nivel in NIVEIS else NIVEL_PADRAO


def _num(valor) -> float:
    return servico._num(valor)


def variacao(atual: float, antes: float) -> float | None:
    """Variação em %; ``None`` quando não há com o que comparar."""
    if not antes:
        return None
    return round((atual - antes) / antes * 100, 1)


def texto_variacao(pct: float | None) -> str:
    if pct is None:
        return "sem comparação"
    if abs(pct) < 0.5:
        return "igual"
    return f"{'+' if pct > 0 else '−'}{abs(pct):.0f}%".replace(".", ",")


# --------------------------------------------------------------------------- partes do relatório


def _serie(tipo: str, inicio: date, fim: date, lista: list[dict]) -> list[dict]:
    """Por dia (semana, quinzena, mês) ou por mês (ano): litros e R$ de cada combustível."""
    def novo(rotulo: str, dia: date) -> dict:
        return {"rotulo": rotulo, "inicio": dia, "litros": 0.0, "valor": 0.0, "abastecimentos": 0,
                "por_combustivel": defaultdict(float)}

    if tipo == "ano":
        grupos = {m: novo(MESES_CURTOS[m - 1], date(inicio.year, m, 1)) for m in range(1, 13)}
        chave = lambda d: d.month  # noqa: E731
    else:
        grupos = {}
        dia = inicio
        while dia <= fim:
            rotulo = f"{DIAS_SEMANA[dia.weekday()]} {dia.day:02d}" if tipo == "semana" else f"{dia:%d/%m}"
            grupos[dia] = novo(rotulo, dia)
            dia += timedelta(days=1)
        chave = lambda d: d  # noqa: E731
    for a in lista:
        dia = servico._data(a.get("data"))
        grupo = grupos.get(chave(dia)) if dia else None
        if not grupo:
            continue
        valor = valor_do_abastecimento(a, fim)
        grupo["litros"] += _num(a.get("litros"))
        grupo["valor"] += valor
        grupo["abastecimentos"] += 1
        grupo["por_combustivel"][combustivel_de(a)] += valor
    saida = []
    for g in grupos.values():
        saida.append({**g, "litros": round(g["litros"], 2), "valor": round(g["valor"], 2),
                      "por_combustivel": {c: round(v, 2) for c, v in g["por_combustivel"].items()}})
    return saida


def _agrupar(lista: list[dict], chave, fim: date) -> list[dict]:
    grupos: dict[str, dict] = {}
    for a in lista:
        nome = chave(a) or "Não informado"
        g = grupos.setdefault(servico.normalizar(nome), {"nome": nome, "litros": 0.0, "valor": 0.0, "abastecimentos": 0})
        g["litros"] += _num(a.get("litros"))
        g["valor"] += valor_do_abastecimento(a, fim)
        g["abastecimentos"] += 1
    total = sum(g["valor"] for g in grupos.values())
    return sorted(({**g, "litros": round(g["litros"], 2), "valor": round(g["valor"], 2),
                    "percentual": round(g["valor"] / total * 100, 1) if total else 0.0} for g in grupos.values()),
                  key=lambda g: -g["valor"])


def _trechos(lista: list[dict], fim: date, cadastro: dict[str, dict]) -> dict[int, dict]:
    """Consumo de cada abastecimento com horímetro/km: o que rodou desde o abastecimento anterior da mesma máquina.

    Pelo método do tanque cheio: os litros deste abastecimento repõem o que foi gasto no trecho.
    """
    saida: dict[int, dict] = {}
    historicos: dict[str, list[dict]] = {}
    for a in lista:
        if not _num(a.get("medidor")):
            continue
        nome = a.get("maquina") or ""
        if nome not in historicos:
            historicos[nome] = sorted((h for h in servico.abastecimentos(maquina=nome, fim=fim) if _num(h.get("medidor"))),
                                      key=lambda h: (_num(h["medidor"]), h["id"]))
        anteriores = [h for h in historicos[nome] if _num(h["medidor"]) < _num(a["medidor"]) and h["id"] != a["id"]]
        if not anteriores:
            continue
        antes = anteriores[-1]
        rodado = round(_num(a["medidor"]) - _num(antes["medidor"]), 1)
        litros = _num(a.get("litros"))
        medidor = (cadastro.get(servico.normalizar(nome)) or {}).get("medidor") or ""
        if rodado <= 0 or litros <= 0 or medidor not in ("horas", "km"):
            continue
        consumo = round(litros / rodado, 2) if medidor == "horas" else round(rodado / litros, 2)
        unidade = "L/h" if medidor == "horas" else "km/L"
        saida[a["id"]] = {"anterior": _num(antes["medidor"]), "data_anterior": servico._data(antes.get("data")),
                          "rodado": rodado, "unidade_rodado": "h" if medidor == "horas" else "km",
                          "consumo": consumo, "rotulo": f"{str(consumo).replace('.', ',')} {unidade}"}
    return saida


def _media_anterior(nome: str, inicio: date, dias: int = 90) -> float:
    """Litros por dia da máquina nos ``dias`` antes do período (a referência do "normal").

    Conta só os dias desde o primeiro abastecimento da máquina (quem começou a lançar há 3 semanas não tem 90 dias
    de histórico); com menos de ``HISTORICO_MINIMO`` dias não há "normal" para comparar.
    """
    todos = servico.abastecimentos(fim=inicio - timedelta(days=1), maquina=nome)
    if not todos:
        return 0.0
    primeiro = min(servico._data(a.get("data")) for a in todos if a.get("data"))
    desde = max(inicio - timedelta(days=dias), primeiro)
    cobertos = (inicio - desde).days
    if cobertos < HISTORICO_MINIMO:
        return 0.0
    lista = [a for a in todos if servico._data(a.get("data")) >= desde]
    return round(sum(_num(a.get("litros")) for a in lista) / cobertos, 2)


def _previsao(fim: date, hoje: date) -> dict | None:
    """Quanto o saldo de hoje dura no ritmo dos últimos 30 dias (só quando o período inclui hoje)."""
    atual = servico.saldo()
    lista = servico.abastecimentos(hoje - timedelta(days=DIAS_RITMO - 1), hoje)
    gasto = sum(valor_do_abastecimento(a) for a in lista)
    por_dia = round(gasto / DIAS_RITMO, 2)
    if atual["valor"] <= 0 or not por_dia:
        return {"saldo": atual["valor"], "por_dia": por_dia, "dias": 0 if atual["valor"] <= 0 else None,
                "acaba_em": hoje if atual["valor"] <= 0 else None}
    dias = int(atual["valor"] // por_dia)
    return {"saldo": atual["valor"], "por_dia": por_dia, "dias": dias, "acaba_em": hoje + timedelta(days=dias)}


def _alertas(r: dict, cadastro: dict[str, dict], alerta_valor: float | None, hoje: date) -> list[dict]:
    """Pontos de atenção do período, do mais grave para o menos grave."""
    alertas: list[dict] = []
    saldo = r["saldo"]
    if saldo["valor"] < 0:
        alertas.append({"nivel": "erro", "texto": f"Saldo negativo ({moeda(saldo['valor'])}): foi abastecido mais do que "
                                                  "foi pago. Falta lançar alguma compra?"})
    elif alerta_valor and saldo["pago"] and saldo["valor"] <= alerta_valor and r["periodo"]["fim"] >= hoje:
        alertas.append({"nivel": "aviso", "texto": f"Saldo baixo: restam {moeda(saldo['valor'])} no posto."})
    for m in r["por_maquina"]:
        if m["acima_do_normal"]:
            alertas.append({"nivel": "aviso", "maquina": m["maquina"],
                            "texto": f"{m['maquina']} consumiu {m['acima_do_normal']:.0f}% acima do normal "
                                     f"({litros_br(m['por_dia'])}/dia contra {litros_br(m['media_normal'])}/dia de costume, pela média "
                                     "dos até 90 dias anteriores)."})
    sem_medidor = defaultdict(int)
    for a in r["abastecimentos"]:
        maquina = cadastro.get(servico.normalizar(a.get("maquina")))
        if maquina and maquina.get("medidor") in ("horas", "km") and not _num(a.get("medidor")):
            sem_medidor[maquina["nome"]] += 1
    if sem_medidor:
        lista = ", ".join(f"{nome} ({n})" for nome, n in sorted(sem_medidor.items(), key=lambda x: -x[1]))
        alertas.append({"nivel": "info", "texto": f"Abastecimentos sem horímetro/km: {lista}. Sem a leitura não dá para "
                                                  "calcular o consumo real (L/h ou km/L)."})
    sem_preco = [a for a in r["abastecimentos"] if not _num(a.get("valor")) and not _num(a.get("preco_litro"))]
    if sem_preco:
        alertas.append({"nivel": "info", "texto": f"{len(sem_preco)} abastecimento(s) sem preço: o valor foi estimado pelo "
                                                  "preço da tabela."})
    if r["sem_abastecimento"]:
        alertas.append({"nivel": "info", "texto": f"Sem abastecimento no período: {', '.join(r['sem_abastecimento'])}."})
    return alertas


def analise(tipo: str = "semana", referencia: date | None = None, alerta_valor: float | None = None,
            hoje: date | None = None) -> dict:
    """O resumo do período com tudo o que o relatório detalhado e o completo mostram."""
    hoje = hoje or date.today()
    r = servico.resumo(tipo, referencia)
    inicio, fim = r["periodo"]["inicio"], r["periodo"]["fim"]
    ant_inicio, ant_fim, ant_rotulo = servico.periodo(tipo, r["periodo"]["anterior"])
    anteriores = servico.abastecimentos(ant_inicio, ant_fim)
    cadastro = {servico.normalizar(m["nome"]): m for m in servico.maquinas()}

    antes_por_maquina: dict[str, dict] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0})
    for a in anteriores:
        g = antes_por_maquina[a.get("maquina") or servico.SEM_MAQUINA]
        g["litros"] += _num(a.get("litros"))
        g["valor"] += valor_do_abastecimento(a, ant_fim)
    for m in r["por_maquina"]:
        antes = antes_por_maquina.get(m["maquina"], {"litros": 0.0, "valor": 0.0})
        m["litros_anterior"] = round(antes["litros"], 2)
        m["custo_anterior"] = round(antes["valor"], 2)
        m["variacao"] = variacao(m["litros"], antes["litros"])
        m["custo_por_litro"] = round(m["custo"] / m["litros"], 3) if m["litros"] else 0.0
        normal = _media_anterior(m["maquina"], inicio)
        m["media_normal"] = normal
        excesso = (m["por_dia"] / normal - 1) * 100 if normal else 0
        m["acima_do_normal"] = round(excesso, 0) if (normal and m["litros"] >= LITROS_MINIMOS_ALERTA
                                                    and m["por_dia"] >= normal * ACIMA_DO_NORMAL[tipo]) else 0

    custo_anterior = round(sum(valor_do_abastecimento(a, ant_fim) for a in anteriores), 2)
    litros_anterior = round(sum(_num(a.get("litros")) for a in anteriores), 2)
    trechos = _trechos(r["abastecimentos"], fim, cadastro)
    for a in r["abastecimentos"]:
        a["custo"] = valor_do_abastecimento(a, fim)
        a["trecho"] = trechos.get(a["id"])
        maquina = cadastro.get(servico.normalizar(a.get("maquina"))) or {}
        a["medidor_tipo"] = maquina.get("medidor") or ""
    r.update({
        "nivel_padrao": NIVEL_PADRAO,
        "anterior": {"rotulo": ant_rotulo, "inicio": ant_inicio, "fim": ant_fim, "litros": litros_anterior,
                     "custo": custo_anterior, "abastecimentos": len(anteriores)},
        "variacao": {"litros": variacao(r["abastecido"]["litros"], litros_anterior),
                     "custo": variacao(r["abastecido"]["custo"], custo_anterior)},
        "serie": _serie(tipo, inicio, fim, r["abastecimentos"]),
        "por_posto": _agrupar(r["abastecimentos"], lambda a: (a.get("posto") or "").strip(), fim),
        "por_pessoa": _agrupar(r["abastecimentos"], lambda a: (a.get("pessoa") or "").strip(), fim),
        "previsao": _previsao(fim, hoje) if inicio <= hoje <= fim else None,
        "periodo_atual": inicio <= hoje <= fim,
    })
    r["alertas"] = _alertas(r, cadastro, alerta_valor, hoje)
    return r


# --------------------------------------------------------------------------- texto (Telegram)


def _limitar(texto: str, limite: int = LIMITE_TELEGRAM) -> str:
    """Corta numa quebra de linha para caber numa mensagem do Telegram."""
    if len(texto) <= limite:
        return texto
    corte = texto.rfind("\n", 0, limite - 80)
    return texto[:corte if corte > 0 else limite - 80] + "\n\n… (continua no Excel: Diesel → Relatórios)"


def _linha_saldo(r: dict) -> list[str]:
    previsao = r.get("previsao")
    if previsao:
        dura = ""
        if previsao["dias"] is not None and previsao["saldo"] > 0:
            dura = f" · dá para ~{previsao['dias']} dia(s) no ritmo atual"
        return [f"🛢️ Saldo no posto: <b>{moeda(previsao['saldo'])}</b>{dura}"]
    return [f"🛢️ Saldo no fim do período: <b>{moeda(r['saldo']['valor'])}</b>"]


def _texto_simples(r: dict) -> str:
    tipo = r["periodo"]["tipo"]
    linhas = [f"⛽ <b>Relatório {TITULOS[tipo]} do diesel</b>", r["periodo"]["rotulo"].capitalize(), "",
              f"💸 Abastecido: <b>{moeda(r['abastecido']['custo'])}</b> · {litros_br(r['abastecido']['litros'])} · "
              f"{r['abastecido']['quantidade']} abastecimento(s)"]
    if r["variacao"]["custo"] is not None:
        linhas.append(f"📈 {texto_variacao(r['variacao']['custo'])} em relação {ANTERIOR[tipo]} "
                      f"({moeda(r['anterior']['custo'])})")
    linhas += _linha_saldo(r)
    if r["comprado"]["quantidade"]:
        linhas.append(f"🛒 Comprado: {moeda(r['comprado']['valor'])} ({litros_br(r['comprado']['litros'])})")
    if r["por_maquina"]:
        linhas += ["", "<b>Por máquina</b>"]
        for m in r["por_maquina"][:8]:
            linhas.append(f"• {escape(m['maquina'])}: {litros_br(m['litros'])} · {moeda(m['custo'])}")
        if len(r["por_maquina"]) > 8:
            linhas.append(f"… e mais {len(r['por_maquina']) - 8} máquina(s)")
    else:
        linhas += ["", "Nenhum abastecimento no período."]
    atencao = [a for a in r["alertas"] if a["nivel"] in ("erro", "aviso")]
    if atencao:
        linhas += ["", f"⚠️ {len(atencao)} ponto(s) de atenção — mande /relatorio {_comando(tipo)} detalhado"]
    return "\n".join(linhas)


def _comando(tipo: str) -> str:
    return {"semana": "semana", "quinzena": "quinzena", "mes": "mes", "ano": "ano"}[tipo]


def _texto_detalhado(r: dict, referencia: date | None) -> str:
    tipo = r["periodo"]["tipo"]
    linhas = [servico.texto_relatorio(tipo, referencia)]
    extra = []
    if r["variacao"]["litros"] is not None:
        extra.append(f"📈 Comparado com {r['anterior']['rotulo']}: litros {texto_variacao(r['variacao']['litros'])} · "
                     f"valor {texto_variacao(r['variacao']['custo'])}")
    previsao = r.get("previsao")
    if previsao and previsao["dias"] is not None and previsao["saldo"] > 0:
        extra.append(f"⏳ No ritmo dos últimos 30 dias ({moeda(previsao['por_dia'])}/dia), o saldo dura ~{previsao['dias']} "
                     f"dia(s), até {previsao['acaba_em']:%d/%m}.")
    if extra:
        linhas += ["", *extra]
    if r["alertas"]:
        icones = {"erro": "🔴", "aviso": "⚠️", "info": "ℹ️"}
        linhas += ["", "<b>Pontos de atenção</b>", *(f"{icones[a['nivel']]} {escape(a['texto'])}" for a in r["alertas"])]
    return "\n".join(linhas)


def _texto_completo(r: dict, referencia: date | None) -> str:
    linhas = [_texto_detalhado(r, referencia)]
    if len(r["por_posto"]) > 1:
        linhas += ["", "<b>Por posto</b>", *(f"• {escape(p['nome'])}: {litros_br(p['litros'])} · {moeda(p['valor'])}"
                                            for p in r["por_posto"])]
    if r["por_pessoa"] and any(p["nome"] != "Não informado" for p in r["por_pessoa"]):
        linhas += ["", "<b>Quem abasteceu</b>", *(f"• {escape(p['nome'])}: {p['abastecimentos']}x · {litros_br(p['litros'])}"
                                                 for p in r["por_pessoa"])]
    if r["abastecimentos"]:
        linhas += ["", "<b>Abastecimentos</b>"]
        for a in sorted(r["abastecimentos"], key=lambda a: (str(a.get("data")), a.get("hora") or "")):
            dia = servico._data(a.get("data"))
            trecho = f" · {a['trecho']['rotulo']}" if a.get("trecho") else ""
            linhas.append(f"{dia:%d/%m} {escape(a.get('maquina') or '')}: {litros_br(a.get('litros'))} "
                          f"{escape(combustivel_de(a))} · {moeda(a['custo'])}{trecho}")
    return "\n".join(linhas)


def texto(tipo: str = "semana", referencia: date | None = None, nivel: str = NIVEL_PADRAO,
          alerta_valor: float | None = None, hoje: date | None = None) -> str:
    r = analise(tipo, referencia, alerta_valor, hoje)
    nivel = nivel_valido(nivel)
    if nivel == "simples":
        return _limitar(_texto_simples(r))
    if nivel == "detalhado":
        return _limitar(_texto_detalhado(r, referencia))
    return _limitar(_texto_completo(r, referencia))

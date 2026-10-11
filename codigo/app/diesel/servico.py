"""Diesel: o estoque de litros (compras no posto) e o que cada máquina abasteceu (canhotos).

* **Saldo** = litros comprados − litros abastecidos (só o que não foi cancelado).
* **Média de cada máquina** no período: litros, abastecimentos, litros por dia e, quando os canhotos trazem o
  horímetro ou o km, o consumo de verdade: **litros por hora** (máquinas) ou **km por litro** (caminhões).
* **Relatórios** por semana, quinzena (1–15 e 16–fim do mês), mês ou ano.
* **Combustível** em cada compra, abastecimento e máquina (Diesel S10, Diesel comum, Gasolina…). O saldo é um só —
  os litros comprados na semana servem para qualquer combustível que o posto entregar —, e por combustível sai o quanto
  foi abastecido de cada um. O custo de cada abastecimento é o preço do canhoto; sem ele, o da tabela de preços.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta

from .. import contexto as ctx
from . import precos
from .modelos import (
    COMBUSTIVEIS, COMBUSTIVEL_PADRAO, LITROS_POR_COMPRA, MEDIDORES, STATUS_ABASTECIMENTO, STATUS_COMPRA, STATUS_MAQUINA,
    TIPOS_MAQUINA,
)

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
PERIODOS = ("semana", "quinzena", "mes", "ano")
SEM_MAQUINA = "Sem máquina"
ALERTA_PADRAO = 1000.0  # avisa quando o saldo fica abaixo disso (R$)


class ErroDiesel(ValueError):
    """Erro de regra (mensagem já pronta para a pessoa ler)."""


def banco():
    return ctx.diesel


def normalizar(texto) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


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


def numero_br(valor) -> str:
    texto = f"{_num(valor):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto[:-2] if texto.endswith(",0") else texto


def litros_br(valor) -> str:
    return numero_br(valor) + " L"


def moeda(valor) -> str:
    return "R$ " + f"{_num(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def combustivel_de(registro: dict) -> str:
    """Combustível do lançamento (os antigos, sem combustível, contam como o padrão)."""
    return registro.get("combustivel") or COMBUSTIVEL_PADRAO


def _combustivel(valor, maquina: dict | None = None) -> str:
    if valor in COMBUSTIVEIS:
        return valor
    return (maquina or {}).get("combustivel") or COMBUSTIVEL_PADRAO


def numero_digitado(texto: str) -> float | None:
    """Número digitado no Telegram ou na tela: "1.000", "180,5", "180.5", "1000 L"."""
    limpo = (texto or "").replace(" ", "")
    m = re.search(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?", limpo)
    if not m:
        return None
    bruto = m.group(0)
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", bruto):
        bruto = bruto.replace(".", "").replace(",", ".")
    else:
        bruto = bruto.replace(",", ".")
    valor = round(float(bruto), 3)
    return valor if valor > 0 else None


# --------------------------------------------------------------------------- períodos


def periodo(tipo: str, referencia: date | None = None) -> tuple[date, date, str]:
    """Primeiro e último dia do período e o nome dele. Quinzena: 1 a 15 e 16 ao fim do mês."""
    ref = referencia or date.today()
    fim_do_mes = date(ref.year + (ref.month == 12), ref.month % 12 + 1, 1) - timedelta(days=1)
    if tipo == "semana":
        inicio = ref - timedelta(days=ref.weekday())
        fim = inicio + timedelta(days=6)
        return inicio, fim, f"semana de {inicio:%d/%m} a {fim:%d/%m/%Y}"
    if tipo == "quinzena":
        if ref.day <= 15:
            return ref.replace(day=1), ref.replace(day=15), f"1ª quinzena de {MESES[ref.month - 1]} de {ref.year}"
        return ref.replace(day=16), fim_do_mes, f"2ª quinzena de {MESES[ref.month - 1]} de {ref.year}"
    if tipo == "mes":
        return ref.replace(day=1), fim_do_mes, f"{MESES[ref.month - 1]} de {ref.year}"
    if tipo == "ano":
        return date(ref.year, 1, 1), date(ref.year, 12, 31), str(ref.year)
    raise ErroDiesel("Período inválido: use semana, quinzena, mês ou ano.")


def deslocar(tipo: str, referencia: date, passos: int) -> date:
    """Data de referência do período anterior (passos < 0) ou seguinte (passos > 0)."""
    if tipo == "semana":
        return referencia + timedelta(weeks=passos)
    if tipo == "quinzena":
        inicio, _, _ = periodo("quinzena", referencia)
        for _ in range(abs(passos)):
            if passos > 0:
                inicio = periodo("quinzena", periodo("quinzena", inicio)[1] + timedelta(days=1))[0]
            else:
                inicio = periodo("quinzena", inicio - timedelta(days=1))[0]
        return inicio
    if tipo == "ano":
        return date(referencia.year + passos, 1, 1)
    total = referencia.year * 12 + referencia.month - 1 + passos
    return date(total // 12, total % 12 + 1, 1)


# --------------------------------------------------------------------------- máquinas


def maquinas(incluir_inativas: bool = True) -> list[dict]:
    lista = banco().listar("maquinas")
    if not incluir_inativas:
        lista = [m for m in lista if m.get("status") != "Inativa"]
    return sorted(lista, key=lambda m: normalizar(m.get("nome")))


def maquina_por_nome(nome: str) -> dict | None:
    alvo = normalizar(nome)
    if not alvo:
        return None
    for m in maquinas():
        if normalizar(m.get("nome")) == alvo or (m.get("placa") and normalizar(m["placa"]).replace("-", "") == alvo.replace("-", "")):
            return m
    return None


def salvar_maquina(dados: dict, usuario: str = "", id_: int | None = None) -> dict:
    nome = re.sub(r"\s+", " ", str(dados.get("nome") or "")).strip()[:60]
    atual = banco().obter(int(id_), "maquinas") if id_ else None
    if not nome and not atual:
        raise ErroDiesel("Informe o nome da máquina (ex.: Escavadeira PC200, Caminhão Volvo ABC-1D23).")
    if nome:
        repetida = maquina_por_nome(nome)
        if repetida and (not atual or repetida["id"] != atual["id"]):
            raise ErroDiesel(f"Já existe uma máquina chamada “{repetida['nome']}”.")
    limpos = {}
    if nome:
        limpos["nome"] = nome
    if dados.get("tipo") is not None:
        limpos["tipo"] = dados["tipo"] if dados["tipo"] in TIPOS_MAQUINA else "Outro"
    if dados.get("placa") is not None:
        limpos["placa"] = str(dados["placa"]).strip().upper()[:16]
    if dados.get("medidor") is not None:
        limpos["medidor"] = dados["medidor"] if dados["medidor"] in MEDIDORES else ""
    if dados.get("combustivel") is not None:
        limpos["combustivel"] = dados["combustivel"] if dados["combustivel"] in COMBUSTIVEIS else ""
    if dados.get("status") is not None:
        limpos["status"] = dados["status"] if dados["status"] in STATUS_MAQUINA else "Ativa"
    if dados.get("observacoes") is not None:
        limpos["observacoes"] = str(dados["observacoes"])[:300]
    if atual:
        if nome and nome != atual.get("nome"):  # renomear leva junto os abastecimentos antigos
            operacoes = [{"tipo": "atualizar", "aba": "abastecimentos", "id": a["id"], "usuario": usuario,
                          "dados": {"maquina": nome}}
                         for a in banco().listar("abastecimentos") if normalizar(a.get("maquina")) == normalizar(atual["nome"])]
            if operacoes:
                banco().aplicar_lote(operacoes)
        return banco().atualizar(atual["id"], limpos, "maquinas", usuario)
    limpos.setdefault("tipo", "Máquina")
    limpos.setdefault("medidor", "horas" if limpos["tipo"] in ("Máquina", "Gerador") else "km"
                      if limpos["tipo"] in ("Caminhão", "Veículo") else "")
    limpos.setdefault("status", "Ativa")
    limpos.setdefault("combustivel", COMBUSTIVEL_PADRAO)
    return banco().adicionar(limpos, "maquinas", usuario)


def garantir_maquina(nome: str, usuario: str = "") -> dict:
    return maquina_por_nome(nome) or salvar_maquina({"nome": nome}, usuario)


# --------------------------------------------------------------------------- compras e abastecimentos


def _listar(aba: str, inicio: date | None = None, fim: date | None = None, cancelados: bool = False) -> list[dict]:
    cancelado = "Cancelada" if aba == "compras" else "Cancelado"
    saida = []
    for r in banco().listar(aba):
        if not cancelados and r.get("status") == cancelado:
            continue
        quando = _data(r.get("data"))
        if (inicio and (not quando or quando < inicio)) or (fim and (not quando or quando > fim)):
            continue
        saida.append(r)
    return sorted(saida, key=lambda r: (_data(r.get("data")) or date.min, r.get("hora") or "", r["id"]), reverse=True)


def compras(inicio: date | None = None, fim: date | None = None, cancelados: bool = False,
            combustivel: str = "") -> list[dict]:
    lista = _listar("compras", inicio, fim, cancelados)
    return [c for c in lista if combustivel_de(c) == combustivel] if combustivel else lista


def abastecimentos(inicio: date | None = None, fim: date | None = None, cancelados: bool = False,
                   maquina: str = "", combustivel: str = "") -> list[dict]:
    lista = _listar("abastecimentos", inicio, fim, cancelados)
    if maquina:
        lista = [a for a in lista if normalizar(a.get("maquina")) == normalizar(maquina)]
    if combustivel:
        lista = [a for a in lista if combustivel_de(a) == combustivel]
    return lista


def _arquivo(arquivo: dict | None) -> dict:
    return {"arquivo": (arquivo or {}).get("caminho") or "", "arquivo_nome": (arquivo or {}).get("nome") or ""}


def lancar_compra(dados: dict, usuario: str = "", arquivo: dict | None = None) -> dict:
    """Compra no posto: soma os litros ao estoque. Sem os litros, vale a compra semanal padrão de 1.000 L."""
    litros = _num(dados.get("litros")) or LITROS_POR_COMPRA
    valor = round(_num(dados.get("valor")), 2)
    if litros <= 0:
        raise ErroDiesel("Informe quantos litros foram comprados.")
    combustivel = _combustivel(dados.get("combustivel"))
    preco = _num(dados.get("preco_litro")) or (round(valor / litros, 4) if valor else precos.preco(combustivel))
    return banco().adicionar({
        "data": _data(dados.get("data")) or date.today(),
        "posto": str(dados.get("posto") or "").strip()[:80],
        "combustivel": combustivel,
        "litros": round(litros, 2),
        "valor": valor or (round(preco * litros, 2) if preco else None),
        "preco_litro": round(preco, 4) or None,
        "forma": str(dados.get("forma") or "").strip()[:20],
        "documento": str(dados.get("documento") or "").strip()[:30],
        "status": "Confirmada",
        "observacoes": str(dados.get("observacoes") or "")[:300],
        **_arquivo(arquivo),
    }, "compras", usuario)


def lancar_abastecimento(dados: dict, usuario: str = "", arquivo: dict | None = None) -> dict:
    """Canhoto de uma máquina: tira os litros do estoque e entra na média dela."""
    litros = _num(dados.get("litros"))
    if litros <= 0:
        raise ErroDiesel("Informe quantos litros foram abastecidos.")
    nome = str(dados.get("maquina") or "").strip()
    if not nome:
        raise ErroDiesel("Escolha a máquina que foi abastecida.")
    maquina = garantir_maquina(nome, usuario)
    medidor = _num(dados.get("medidor")) or None
    combustivel = _combustivel(dados.get("combustivel"), maquina)
    valor = round(_num(dados.get("valor")), 2)
    # o preço do litro: o do canhoto; sem ele, a conta do total; sem os dois, o da tabela de preços
    preco = _num(dados.get("preco_litro")) or (round(valor / litros, 4) if valor else precos.preco(combustivel))
    return banco().adicionar({
        "data": _data(dados.get("data")) or date.today(),
        "hora": str(dados.get("hora") or "")[:5],
        "maquina": maquina["nome"],
        "combustivel": combustivel,
        "litros": round(litros, 2),
        "preco_litro": round(preco, 4) or None,
        "valor": valor or (round(preco * litros, 2) if preco else None),
        "medidor": round(medidor, 1) if medidor else None,
        "posto": str(dados.get("posto") or "").strip()[:80],
        "documento": str(dados.get("documento") or "").strip()[:30],
        "pessoa": str(dados.get("pessoa") or "").strip()[:60],
        "status": "Confirmado",
        "observacoes": str(dados.get("observacoes") or "")[:300],
        **_arquivo(arquivo),
    }, "abastecimentos", usuario)


def lancar_canhoto(itens: list[dict], comum: dict, usuario: str = "", arquivo: dict | None = None) -> list[dict]:
    """Um canhoto com uma ou mais linhas (ex.: Diesel comum para a pá e S10 para o caminhão): um abastecimento por linha.

    ``comum``: o que vale para todas as linhas (data, hora, posto, nº do pedido, quem abasteceu).
    """
    validos = [i for i in itens if _num(i.get("litros")) > 0]
    if not validos:
        raise ErroDiesel("Informe os litros de pelo menos uma linha do canhoto.")
    faltando = [str(n + 1) for n, i in enumerate(validos) if not str(i.get("maquina") or "").strip()]
    if faltando:
        raise ErroDiesel(f"Escolha a máquina da linha {', '.join(faltando)} do canhoto.")
    return [lancar_abastecimento({**comum, **{k: v for k, v in item.items() if v not in (None, "")}}, usuario, arquivo)
            for item in validos]


EDITAVEIS = {"compras": ("data", "posto", "combustivel", "litros", "valor", "preco_litro", "forma", "documento",
                         "observacoes"),
             "abastecimentos": ("data", "hora", "maquina", "combustivel", "litros", "preco_litro", "valor", "medidor",
                                "posto", "documento", "pessoa", "observacoes")}


def atualizar(aba: str, id_: int, dados: dict, usuario: str = "") -> dict:
    limpos = {k: v for k, v in dados.items() if k in EDITAVEIS[aba]}
    if "maquina" in limpos:
        limpos["maquina"] = garantir_maquina(limpos["maquina"], usuario)["nome"]
    for campo in ("litros", "medidor", "valor", "preco_litro"):
        if campo in limpos:
            limpos[campo] = _num(limpos[campo]) or None
    if "litros" in limpos and not limpos["litros"]:
        raise ErroDiesel("Informe os litros.")
    if "combustivel" in limpos:
        limpos["combustivel"] = _combustivel(limpos["combustivel"])
    if ("litros" in limpos or "preco_litro" in limpos) and "valor" not in limpos:  # mudou litros ou preço: refaz o total
        atual = banco().obter(int(id_), aba)
        litros = limpos.get("litros") or _num(atual.get("litros"))
        preco = limpos.get("preco_litro") if "preco_litro" in limpos else _num(atual.get("preco_litro"))
        if litros and preco:
            limpos["valor"] = round(litros * preco, 2)
    return banco().atualizar(int(id_), limpos, aba, usuario)


def cancelar(aba: str, id_: int, usuario: str = "") -> dict:
    status = STATUS_COMPRA[1] if aba == "compras" else STATUS_ABASTECIMENTO[1]
    return banco().atualizar(int(id_), {"status": status}, aba, usuario)


# --------------------------------------------------------------------------- saldo e médias


def _preco_referencia(combustivel: str, ate: date | None = None) -> float:
    """Preço do litro para pôr valor num lançamento sem valor: o da tabela de preços; sem ele, o médio das compras."""
    return precos.preco(combustivel) or preco_medio(fim=ate, combustivel=combustivel)


def valor_da_compra(compra: dict, ate: date | None = None) -> float:
    """O que foi pago na compra: o valor do comprovante ou, sem ele, litros × preço."""
    valor = _num(compra.get("valor"))
    if valor:
        return valor
    preco = _num(compra.get("preco_litro")) or _preco_referencia(combustivel_de(compra), ate)
    return round(_num(compra.get("litros")) * preco, 2)


def valor_do_abastecimento(abastecimento: dict, ate: date | None = None) -> float:
    """Quanto o abastecimento tirou do saldo: o valor do canhoto ou, sem ele, litros × preço daquele combustível."""
    valor = _num(abastecimento.get("valor"))
    if valor:
        return valor
    preco = _num(abastecimento.get("preco_litro")) or _preco_referencia(combustivel_de(abastecimento), ate)
    return round(_num(abastecimento.get("litros")) * preco, 2)


def saldo(ate: date | None = None) -> dict:
    """Saldo em reais: o que foi pago nas compras − o valor de cada abastecimento (até a data, se informada).

    A compra da semana (ex.: 1.000 L) é um crédito no posto que serve para S10 e para o comum, e cada um tem o seu
    preço. Por isso o saldo é em dinheiro: cada abastecimento desconta litros × preço do combustível que foi
    abastecido. Em ``equivalente`` fica quantos litros de cada combustível o saldo ainda compra (pelo preço atual).
    """
    lista_compras = compras(fim=ate)
    lista_abast = abastecimentos(fim=ate)
    pago = round(sum(valor_da_compra(c, ate) for c in lista_compras), 2)
    gasto = round(sum(valor_do_abastecimento(a, ate) for a in lista_abast), 2)
    restante = round(pago - gasto, 2)
    comprado = sum(_num(c.get("litros")) for c in lista_compras)
    usado = sum(_num(a.get("litros")) for a in lista_abast)
    por_combustivel = []
    for combustivel in COMBUSTIVEIS:
        deste = [a for a in lista_abast if combustivel_de(a) == combustivel]
        litros_comprados = sum(_num(c.get("litros")) for c in lista_compras if combustivel_de(c) == combustivel)
        if litros_comprados or deste:
            por_combustivel.append({"combustivel": combustivel, "comprado": round(litros_comprados, 2),
                                    "abastecido": round(sum(_num(a.get("litros")) for a in deste), 2),
                                    "valor_abastecido": round(sum(valor_do_abastecimento(a, ate) for a in deste), 2)})
    usados = [c["combustivel"] for c in por_combustivel if c["abastecido"]] or [COMBUSTIVEL_PADRAO]
    equivalente = []
    for combustivel in dict.fromkeys([*usados, *(p["combustivel"] for p in precos.publico() if p.get("preco"))]):
        preco = _preco_referencia(combustivel, ate)
        if preco:
            equivalente.append({"combustivel": combustivel, "preco": round(preco, 4),
                                "litros": round(max(restante, 0) / preco, 1)})
    ultima = lista_compras[0] if lista_compras else None
    desde = abastecimentos(_data(ultima["data"]), ate) if ultima else []
    if ultima:  # S10 e comum comprados no mesmo dia contam como uma compra só
        do_dia = [c for c in lista_compras if _data(c.get("data")) == _data(ultima["data"])]
        ultima = {**ultima, "litros": sum(_num(c.get("litros")) for c in do_dia),
                  "valor": round(sum(valor_da_compra(c, ate) for c in do_dia), 2)}
    return {
        "valor": restante,
        "pago": pago,
        "gasto": gasto,
        "equivalente": equivalente,
        "litros": round(comprado - usado, 2),
        "comprado": round(comprado, 2),
        "abastecido": round(usado, 2),
        "por_combustivel": por_combustivel,
        "ultima_compra": ({"id": ultima["id"], "data": _data(ultima["data"]), "litros": _num(ultima.get("litros")),
                           "valor": valor_da_compra(ultima, ate), "combustivel": combustivel_de(ultima),
                           "posto": ultima.get("posto") or "",
                           "usados_desde": round(sum(_num(a.get("litros")) for a in desde), 2),
                           "gasto_desde": round(sum(valor_do_abastecimento(a, ate) for a in desde), 2)}
                          if ultima else None),
    }


def preco_medio(inicio: date | None = None, fim: date | None = None, combustivel: str = "") -> float:
    """Preço médio do litro nas compras do período (sem compra no período, o da última compra; sem compra nenhuma,
    o da tabela de preços)."""
    lista = [c for c in compras(inicio, fim, combustivel=combustivel) if _num(c.get("valor")) and _num(c.get("litros"))] \
        or [c for c in compras(fim=fim, combustivel=combustivel) if _num(c.get("valor")) and _num(c.get("litros"))][:1]
    litros = sum(_num(c["litros"]) for c in lista)
    if litros:
        return round(sum(_num(c["valor"]) for c in lista) / litros, 4)
    return precos.preco(combustivel) if combustivel else 0.0


def custo(abastecimento: dict, precos_medios: dict[str, float]) -> float:
    """Quanto custou o abastecimento: o valor do canhoto ou, sem ele, litros × preço daquele combustível (o da
    tabela de preços; sem ele, o médio das compras)."""
    valor = _num(abastecimento.get("valor"))
    if valor:
        return valor
    combustivel = combustivel_de(abastecimento)
    preco = _num(abastecimento.get("preco_litro")) or precos.preco(combustivel) or precos_medios.get(combustivel, 0)
    return round(_num(abastecimento.get("litros")) * preco, 2)


def consumo(maquina: dict | None, lista: list[dict]) -> dict:
    """Consumo pelas leituras do horímetro/km: litros usados entre a primeira e a última leitura.

    O primeiro abastecimento com leitura só marca o ponto de partida; os litros dele não entram na conta.
    """
    com_leitura = sorted((a for a in lista if _num(a.get("medidor"))), key=lambda a: (_num(a["medidor"]), a["id"]))
    medidor = (maquina or {}).get("medidor") or ""
    if len(com_leitura) < 2 or medidor not in ("horas", "km"):
        return {"tipo": medidor, "valor": None, "rotulo": ""}
    rodado = _num(com_leitura[-1]["medidor"]) - _num(com_leitura[0]["medidor"])
    litros = sum(_num(a["litros"]) for a in com_leitura[1:])
    if rodado <= 0 or litros <= 0:
        return {"tipo": medidor, "valor": None, "rotulo": ""}
    if medidor == "horas":
        valor = round(litros / rodado, 2)
        return {"tipo": "horas", "valor": valor, "rotulo": f"{str(valor).replace('.', ',')} L/h", "rodado": rodado}
    valor = round(rodado / litros, 2)
    return {"tipo": "km", "valor": valor, "rotulo": f"{str(valor).replace('.', ',')} km/L", "rodado": rodado}


def media_da_maquina(nome: str, fim: date | None = None, dias: int = 30) -> dict:
    """Média dos últimos ``dias`` (padrão 30): litros por dia, por semana e o consumo pelo horímetro/km."""
    fim = fim or date.today()
    inicio = fim - timedelta(days=dias - 1)
    maquina = maquina_por_nome(nome)
    lista = abastecimentos(inicio, fim, maquina=nome)
    total = sum(_num(a.get("litros")) for a in lista)
    historico = abastecimentos(maquina=nome, fim=fim)
    return {"maquina": (maquina or {}).get("nome") or nome, "dias": dias, "litros": round(total, 2),
            "abastecimentos": len(lista), "por_dia": round(total / dias, 2), "por_semana": round(total / dias * 7, 2),
            "por_abastecimento": round(total / len(lista), 2) if lista else 0.0,
            "consumo": consumo(maquina, historico[:30])}


def resumo(tipo: str = "semana", referencia: date | None = None) -> dict:
    """Tudo de um período: compras, abastecimentos, saldo e a tabela por máquina (o relatório)."""
    inicio, fim, rotulo = periodo(tipo, referencia)
    lista_compras = compras(inicio, fim)
    lista_abast = abastecimentos(inicio, fim)
    preco = preco_medio(inicio, fim)
    usados = sorted({combustivel_de(r) for r in [*lista_compras, *lista_abast]}, key=lambda c: COMBUSTIVEIS.index(c)
                    if c in COMBUSTIVEIS else 99)
    precos_medios = {c: preco_medio(inicio, fim, c) for c in usados}
    dias = (min(fim, max(date.today(), inicio)) - inicio).days + 1
    cadastro = {normalizar(m["nome"]): m for m in maquinas()}
    grupos: dict[str, list[dict]] = {}
    for a in lista_abast:
        grupos.setdefault(a.get("maquina") or SEM_MAQUINA, []).append(a)
    total_abastecido = sum(_num(a.get("litros")) for a in lista_abast)
    por_maquina = []
    for nome, itens in grupos.items():
        maquina = cadastro.get(normalizar(nome))
        litros = sum(_num(a.get("litros")) for a in itens)
        historico = abastecimentos(maquina=nome, fim=fim)[:30]
        por_maquina.append({
            "maquina": nome, "tipo": (maquina or {}).get("tipo") or "", "placa": (maquina or {}).get("placa") or "",
            "litros": round(litros, 2), "abastecimentos": len(itens),
            "percentual": round(litros / total_abastecido * 100, 1) if total_abastecido else 0.0,
            "por_dia": round(litros / dias, 2), "por_abastecimento": round(litros / len(itens), 2),
            "custo": round(sum(custo(a, precos_medios) for a in itens), 2), "consumo": consumo(maquina, historico),
            "combustiveis": sorted({combustivel_de(a) for a in itens}),
            "ultimo": max((_data(a.get("data")) for a in itens if a.get("data")), default=None),
        })
    por_maquina.sort(key=lambda m: -m["litros"])
    sem_uso = [m["nome"] for m in maquinas(incluir_inativas=False) if m["nome"] not in grupos]
    atual = saldo(fim)
    por_combustivel = []
    for combustivel in usados:
        comprados = [c for c in lista_compras if combustivel_de(c) == combustivel]
        abastecidos = [a for a in lista_abast if combustivel_de(a) == combustivel]
        litros_abast = sum(_num(a.get("litros")) for a in abastecidos)
        por_combustivel.append({
            "combustivel": combustivel,
            "comprado": round(sum(_num(c.get("litros")) for c in comprados), 2),
            "valor_comprado": round(sum(valor_da_compra(c, fim) for c in comprados), 2),
            "abastecido": round(litros_abast, 2), "abastecimentos": len(abastecidos),
            "custo": round(sum(custo(a, precos_medios) for a in abastecidos), 2),
            "preco_medio": precos_medios.get(combustivel) or 0.0,
        })
    return {
        "periodo": {"tipo": tipo, "inicio": inicio, "fim": fim, "rotulo": rotulo, "dias": dias,
                    "anterior": deslocar(tipo, inicio, -1), "seguinte": deslocar(tipo, inicio, 1)},
        "comprado": {"litros": round(sum(_num(c.get("litros")) for c in lista_compras), 2),
                     "valor": round(sum(valor_da_compra(c, fim) for c in lista_compras), 2),
                     "quantidade": len(lista_compras)},
        "abastecido": {"litros": round(total_abastecido, 2), "quantidade": len(lista_abast),
                       "custo": round(sum(custo(a, precos_medios) for a in lista_abast), 2),
                       "por_dia": round(total_abastecido / dias, 2)},
        "preco_medio": preco,
        "por_combustivel": por_combustivel,
        "saldo": atual,
        "por_maquina": por_maquina,
        "sem_abastecimento": sem_uso,
        "compras": lista_compras,
        "abastecimentos": lista_abast,
    }


# --------------------------------------------------------------------------- textos (Telegram)


def texto_equivalente(atual: dict) -> str:
    """Ex.: "≈ 520 L de Diesel S10 ou 574 L de Diesel comum"."""
    partes = [f"{litros_br(e['litros'])} de {e['combustivel']}" for e in atual.get("equivalente") or []]
    return f"≈ {' ou '.join(partes)}" if partes and atual["valor"] > 0 else ""


def texto_saldo(atual: dict | None = None) -> str:
    atual = atual or saldo()
    linhas = [f"🛢️ <b>Saldo do diesel: {moeda(atual['valor'])}</b>"]
    equivalente = texto_equivalente(atual)
    if equivalente:
        linhas.append(equivalente)
    ultima = atual.get("ultima_compra")
    if ultima:
        linhas.append(f"Última compra: {moeda(ultima['valor'])} em {ultima['data']:%d/%m} · "
                      f"abastecido desde então: {moeda(ultima['gasto_desde'])}")
    return "\n".join(linhas)


def texto_media(nome: str) -> str:
    m = media_da_maquina(nome)
    partes = [f"📊 Média de <b>{m['maquina']}</b> (últimos {m['dias']} dias): {litros_br(m['por_semana'])}/semana · "
              f"{litros_br(m['por_dia'])}/dia · {m['abastecimentos']} abastecimento(s)"]
    if m["consumo"]["rotulo"]:
        partes.append(f"Consumo pelo {'horímetro' if m['consumo']['tipo'] == 'horas' else 'km'}: <b>{m['consumo']['rotulo']}</b>")
    return "\n".join(partes)


def texto_relatorio(tipo: str = "semana", referencia: date | None = None) -> str:
    r = resumo(tipo, referencia)
    titulo = {"semana": "semanal", "quinzena": "quinzenal", "mes": "mensal", "ano": "anual"}[tipo]
    linhas = [f"⛽ <b>Relatório {titulo} do diesel</b>", r["periodo"]["rotulo"].capitalize(), "",
              f"Comprado: <b>{litros_br(r['comprado']['litros'])}</b> ({r['comprado']['quantidade']} compra(s) · "
              f"{moeda(r['comprado']['valor'])})",
              f"Abastecido: <b>{litros_br(r['abastecido']['litros'])}</b> ({r['abastecido']['quantidade']} canhoto(s)"
              f"{' · ≈ ' + moeda(r['abastecido']['custo']) if r['abastecido']['custo'] else ''})",
              f"Saldo no fim do período: <b>{moeda(r['saldo']['valor'])}</b>"]
    if len(r["por_combustivel"]) > 1:
        linhas += ["", "<b>Por combustível</b>"]
        for c in r["por_combustivel"]:
            linhas.append(f"• {c['combustivel']}: {litros_br(c['abastecido'])} abastecidos"
                          f"{' · ' + moeda(c['custo']) if c['custo'] else ''}")
    elif r["preco_medio"]:
        linhas.append(f"Preço médio: {moeda(r['preco_medio'])}/L")
    if r["por_maquina"]:
        linhas += ["", "<b>Por máquina</b>"]
        for m in r["por_maquina"][:20]:
            consumo_txt = f" · {m['consumo']['rotulo']}" if m["consumo"]["rotulo"] else ""
            linhas.append(f"• {m['maquina']}: {litros_br(m['litros'])} ({m['percentual']:.0f}%)"
                          f"{' · ' + moeda(m['custo']) if m['custo'] else ''} · "
                          f"{m['abastecimentos']}x · {litros_br(m['por_dia'])}/dia{consumo_txt}")
    else:
        linhas += ["", "Nenhum abastecimento no período."]
    if r["sem_abastecimento"]:
        linhas += ["", f"Sem abastecimento: {', '.join(r['sem_abastecimento'][:10])}"]
    return "\n".join(linhas)

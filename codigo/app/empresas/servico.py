"""Regras do módulo Empresas: cadastro, fechamento por período, baixa automática e cheques.

**Fechamento** — cada empresa fecha no dia 20 (ou no dia escolhido). O fechamento de agosto, por exemplo, vai
de 21/07 até 20/08: a nota entra no fechamento pelo dia em que foi emitida.

**Baixa automática** — um recebimento (Pix, TED, depósito ou cheque compensado) é dividido entre as notas
fiscais citadas no comprovante, da mais antiga para a mais nova. Quando o valor não cobre tudo, a nota fica
"Parcial" e o fechamento mostra quanto ainda falta. O que sobra fica registrado como crédito da empresa.

**Cheques** — ao receber um cheque pré-datado, as notas dos pedidos citados ficam "Em cheque" (o dinheiro
ainda não entrou). Quando o cheque é compensado (ou chega o comprovante do depósito), vira um recebimento e
as notas são baixadas.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime, timedelta

from .. import contexto as ctx
from ..planilha import RegistroNaoEncontrado
from .modelos import DIA_FECHAMENTO_PADRAO, STATUS_CHEQUE, STATUS_NOTA

log = logging.getLogger("leitor_boletos.empresas")

TOLERANCIA = 0.01
ABERTAS = ("Em aberto", "Em cheque", "Parcial")


class ErroEmpresas(ValueError):
    """Erro de regra de negócio (mensagem já pronta para a pessoa ler)."""


# --------------------------------------------------------------------------- utilidades


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def digitos(texto) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def numero(texto) -> str:
    """Número de NF ou pedido sem zeros à esquerda, para comparar ``006859`` com ``6859``."""
    so_digitos = digitos(texto)
    return so_digitos.lstrip("0") or so_digitos


def lista_de_numeros(valor) -> list[str]:
    if isinstance(valor, (list, tuple, set)):
        itens = list(valor)
    else:
        itens = re.split(r"[^\d]+", str(valor or ""))
    return [n for n in (numero(i) for i in itens) if n]


def texto_de_numeros(valores) -> str:
    return ", ".join(dict.fromkeys(lista_de_numeros(valores)))


def moeda(valor) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor[:10])
        except ValueError:
            return None
    return None


def _valor(dados: dict, chave: str) -> float:
    try:
        return round(float(dados.get(chave) or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def banco():
    return ctx.empresas


def configuracao():
    return ctx.empresas_config


def listar(aba: str) -> list[dict]:
    return banco().listar(aba)


# --------------------------------------------------------------------------- período do fechamento


def dia_fechamento(empresa: dict | None = None) -> int:
    dia = (empresa or {}).get("dia_fechamento")
    try:
        dia = int(dia)
    except (TypeError, ValueError):
        dia = 0
    if not 1 <= dia <= 28:
        try:
            dia = configuracao().dia_fechamento
        except Exception:
            dia = DIA_FECHAMENTO_PADRAO
    return dia


def competencia_de(data: date, dia: int) -> str:
    """Em qual fechamento a nota entra: até o dia do fechamento, no mês dela; depois, no mês seguinte."""
    if data.day <= dia:
        return f"{data:%Y-%m}"
    seguinte = date(data.year + (data.month == 12), (data.month % 12) + 1, 1)
    return f"{seguinte:%Y-%m}"


def periodo(competencia: str, dia: int) -> tuple[date, date]:
    """Primeiro e último dia do fechamento (ex.: 2026-08 com dia 20 → 21/07/2026 a 20/08/2026)."""
    ano, mes = (int(p) for p in competencia.split("-")[:2])
    fim = date(ano, mes, dia)
    anterior = date(ano - (mes == 1), 12 if mes == 1 else mes - 1, dia)
    return anterior + timedelta(days=1), fim


def competencia_atual(dia: int, hoje: date | None = None) -> str:
    return competencia_de(hoje or date.today(), dia)


def competencia_anterior(competencia: str) -> str:
    ano, mes = (int(p) for p in competencia.split("-")[:2])
    return f"{ano - (mes == 1)}-{12 if mes == 1 else mes - 1:02d}"


def titulo_competencia(competencia: str) -> str:
    meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
             "novembro", "dezembro"]
    ano, mes = (int(p) for p in competencia.split("-")[:2])
    return f"{meses[mes - 1]} de {ano}"


# --------------------------------------------------------------------------- empresas


def empresas(incluir_inativas: bool = True) -> list[dict]:
    lista = listar("empresas")
    return [e for e in lista if incluir_inativas or e.get("status") != "Inativa"]


def obter_empresa(id_: int) -> dict:
    return banco().obter(int(id_), "empresas")


def empresa_por_nome(nome: str) -> dict | None:
    alvo = normalizar(nome)
    if not alvo:
        return None
    for empresa in empresas():
        if normalizar(empresa.get("nome")) == alvo:
            return empresa
    return None


def _nomes_da_empresa(empresa: dict) -> list[str]:
    nomes = [empresa.get("nome") or "", empresa.get("razao_social") or ""]
    nomes += re.split(r"[;,|]", empresa.get("apelidos") or "")
    return [normalizar(n) for n in nomes if normalizar(n)]


def identificar_empresa(*, cnpj: str = "", nome: str = "", texto: str = "") -> dict | None:
    """Descobre de qual empresa é um documento: primeiro pelo CNPJ, depois pelo nome ou pelos apelidos."""
    cadastradas = empresas()
    documento = digitos(cnpj)
    if len(documento) == 14:
        for empresa in cadastradas:
            if digitos(empresa.get("cnpj")) == documento:
                return empresa
    alvo = normalizar(nome)
    if alvo:
        for empresa in cadastradas:
            if any(n == alvo for n in _nomes_da_empresa(empresa)):
                return empresa
        for empresa in cadastradas:
            if any(n and (n in alvo or alvo in n) and len(n) >= 4 for n in _nomes_da_empresa(empresa)):
                return empresa
    conteudo = normalizar(texto)
    if conteudo:
        documentos = {digitos(m) for m in re.findall(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", texto or "")}
        for empresa in cadastradas:
            if digitos(empresa.get("cnpj")) and digitos(empresa.get("cnpj")) in documentos:
                return empresa
        melhor = None
        for empresa in cadastradas:
            for n in _nomes_da_empresa(empresa):
                if len(n) >= 4 and n in conteudo and (melhor is None or len(n) > melhor[0]):
                    melhor = (len(n), empresa)
        if melhor:
            return melhor[1]
    return None


def salvar_empresa(dados: dict, usuario: str = "", id_: int | None = None) -> dict:
    nome = re.sub(r"\s+", " ", str(dados.get("nome") or "")).strip()
    if id_ is None and not nome:
        raise ErroEmpresas("Informe o nome da empresa.")
    if nome:
        existente = empresa_por_nome(nome)
        if existente and existente["id"] != id_:
            raise ErroEmpresas(f"Já existe uma empresa chamada “{nome}”.")
    documento = digitos(dados.get("cnpj"))
    if documento and len(documento) not in (11, 14):
        raise ErroEmpresas("CNPJ inválido. Use 14 dígitos (ou 11, para CPF).")
    limpos = {k: v for k, v in dados.items() if k in ctx.empresas.abas["empresas"].editaveis}
    if nome:
        limpos["nome"] = nome
    if "dia_fechamento" in limpos and limpos["dia_fechamento"] not in (None, ""):
        dia = int(limpos["dia_fechamento"])
        if not 1 <= dia <= 28:
            raise ErroEmpresas("O dia do fechamento deve ficar entre 1 e 28.")
        limpos["dia_fechamento"] = dia
    if id_ is None:
        limpos.setdefault("status", "Ativa")
        return banco().adicionar(limpos, "empresas", usuario)
    anterior = obter_empresa(id_)
    atualizada = banco().atualizar(int(id_), limpos, "empresas", usuario)
    if nome and normalizar(anterior.get("nome")) != normalizar(nome):
        renomear_empresa(anterior["nome"], nome, usuario)
    return atualizada


def renomear_empresa(antes: str, depois: str, usuario: str = "") -> int:
    """A empresa é guardada pelo nome nas notas, cheques e recebimentos: renomear atualiza todos."""
    operacoes = []
    for aba in ("notas", "cheques", "recebimentos"):
        for registro in listar(aba):
            if normalizar(registro.get("empresa")) == normalizar(antes):
                operacoes.append({"tipo": "atualizar", "aba": aba, "id": registro["id"],
                                  "dados": {"empresa": depois}, "usuario": usuario})
    if operacoes:
        banco().aplicar_lote(operacoes)
    return len(operacoes)


def excluir_empresa(id_: int, usuario: str = "") -> None:
    empresa = obter_empresa(id_)
    for aba in ("notas", "cheques", "recebimentos"):
        if any(normalizar(r.get("empresa")) == normalizar(empresa["nome"]) for r in listar(aba)):
            raise ErroEmpresas("Esta empresa já tem lançamentos. Marque como inativa em vez de excluir.")
    banco().excluir(int(id_), "empresas", usuario)


def garantir_empresa(nome: str, cnpj: str = "", usuario: str = "") -> dict:
    """Empresa do documento recebido: usa a cadastrada ou cadastra uma nova com o nome lido."""
    encontrada = identificar_empresa(cnpj=cnpj, nome=nome)
    if encontrada:
        if cnpj and not digitos(encontrada.get("cnpj")):
            banco().atualizar(encontrada["id"], {"cnpj": formatar_cnpj(cnpj)}, "empresas", usuario)
        return encontrada
    nome = re.sub(r"\s+", " ", nome or "").strip()[:60] or "Empresa não identificada"
    return salvar_empresa({"nome": nome, "cnpj": formatar_cnpj(cnpj), "status": "Ativa"}, usuario)


def formatar_cnpj(valor: str) -> str:
    d = digitos(valor)
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return str(valor or "").strip()


# --------------------------------------------------------------------------- notas fiscais


def notas_da_empresa(empresa: str, competencia: str = "", somente_abertas: bool = False) -> list[dict]:
    alvo = normalizar(empresa)
    saida = []
    for nota in listar("notas"):
        if normalizar(nota.get("empresa")) != alvo or nota.get("status") == "Cancelado":
            continue
        if competencia and nota.get("competencia") != competencia:
            continue
        if somente_abertas and nota.get("status") not in ABERTAS:
            continue
        saida.append(nota)
    return sorted(saida, key=lambda n: (_data(n.get("data")) or date.max, n["id"]))


def notas_por_numero(numero_nf: str, empresa: str = "") -> list[dict]:
    alvo = numero(numero_nf)
    return [n for n in listar("notas") if numero(n.get("numero_nf")) == alvo and n.get("status") != "Cancelado"
            and (not empresa or normalizar(n.get("empresa")) == normalizar(empresa))]


def lancar_notas(empresa: str, itens: list[dict], usuario: str = "", arquivo: dict | None = None,
                 competencia: str = "") -> list[dict]:
    """Lança as linhas de uma nota fiscal (uma por material) no fechamento da empresa."""
    cadastro = empresa_por_nome(empresa) or garantir_empresa(empresa, usuario=usuario)
    dia = dia_fechamento(cadastro)
    operacoes = []
    for item in itens:
        data = _data(item.get("data")) or date.today()
        quantidade = float(item.get("quantidade") or 0)
        unitario = round(float(item.get("valor_unitario") or 0), 4)
        total = round(float(item.get("valor_total") or 0), 2) or round(quantidade * unitario, 2)
        if not total:
            continue
        if not unitario and quantidade:
            unitario = round(total / quantidade, 4)
        operacoes.append({"tipo": "adicionar", "aba": "notas", "usuario": usuario, "dados": {
            "data": data,
            "empresa": cadastro["nome"],
            "material": str(item.get("material") or "").strip()[:80],
            "unidade": str(item.get("unidade") or "").strip()[:10],
            "quantidade": quantidade or None,
            "valor_unitario": unitario or None,
            "valor_total": total,
            "numero_nf": numero(item.get("numero_nf")),
            "pedido": numero(item.get("pedido")),
            "competencia": competencia or competencia_de(data, dia),
            "status": "Em aberto",
            "valor_recebido": None,
            "observacoes": str(item.get("observacoes") or "")[:200],
            "arquivo": (arquivo or {}).get("caminho") or "",
            "arquivo_nome": (arquivo or {}).get("nome") or "",
        }})
    if not operacoes:
        raise ErroEmpresas("Nenhum item da nota fiscal tinha valor. Confira os dados e lance de novo.")
    criadas = [r["registro"] for r in banco().aplicar_lote(operacoes) if r.get("ok")]
    if credito_da_empresa(cadastro["nome"]) > TOLERANCIA:
        aplicar_creditos(cadastro["nome"], usuario)
        criadas = [banco().obter(n["id"], "notas") for n in criadas]
    return criadas


def atualizar_nota(id_: int, dados: dict, usuario: str = "") -> dict:
    nota = banco().obter(int(id_), "notas")
    limpos = {k: v for k, v in dados.items() if k in ctx.empresas.abas["notas"].editaveis}
    if "status" in limpos and limpos["status"] not in STATUS_NOTA:
        raise ErroEmpresas("Situação inválida para a nota fiscal.")
    if limpos.get("data") and not limpos.get("competencia"):
        limpos["competencia"] = competencia_de(_data(limpos["data"]), dia_fechamento(empresa_por_nome(nota["empresa"])))
    for campo in ("numero_nf", "pedido"):
        if campo in limpos:
            limpos[campo] = numero(limpos[campo])
    if limpos.get("quantidade") and limpos.get("valor_unitario") and not limpos.get("valor_total"):
        limpos["valor_total"] = round(float(limpos["quantidade"]) * float(limpos["valor_unitario"]), 2)
    return banco().atualizar(int(id_), limpos, "notas", usuario)


def mover_nota_fiscal(empresa: str, numero_nf: str, competencia: str, usuario: str = "") -> list[dict]:
    """Leva todas as linhas de uma nota fiscal para outro fechamento (ex.: a NF chegou depois do dia 20)."""
    if not re.fullmatch(r"\d{4}-\d{2}", competencia or ""):
        raise ErroEmpresas("Escolha o fechamento no formato AAAA-MM.")
    alvo = numero(numero_nf)
    operacoes = [{"tipo": "atualizar", "aba": "notas", "id": n["id"], "usuario": usuario,
                  "dados": {"competencia": competencia}}
                 for n in notas_da_empresa(empresa) if numero(n.get("numero_nf")) == alvo
                 and n.get("competencia") != competencia]
    if not operacoes:
        return []
    return [r["registro"] for r in banco().aplicar_lote(operacoes) if r.get("ok")]


def excluir_nota(id_: int, usuario: str = "") -> None:
    banco().excluir(int(id_), "notas", usuario)


# --------------------------------------------------------------------------- baixa automática


def _restante(nota: dict) -> float:
    return round(_valor(nota, "valor_total") - _valor(nota, "valor_recebido"), 2)


def _candidatas(empresa: str, numeros_nf: list[str], pedidos: list[str]) -> list[dict]:
    """Notas que o recebimento pode baixar: as citadas no comprovante ou, sem citação, as mais antigas em aberto."""
    abertas = [n for n in notas_da_empresa(empresa, somente_abertas=True) if _restante(n) > TOLERANCIA]
    if numeros_nf:
        escolhidas = [n for n in abertas if numero(n.get("numero_nf")) in numeros_nf]
        if escolhidas:
            return escolhidas
    if pedidos:
        escolhidas = [n for n in abertas if numero(n.get("pedido")) in pedidos]
        if escolhidas:
            return escolhidas
    return abertas


def _aplicar(empresa: str, valor: float, numeros_nf: list[str], pedidos: list[str], data: date,
             usuario: str, cheque_id: int | None = None) -> tuple[list[dict], float]:
    """Divide o valor recebido entre as notas, da mais antiga para a mais nova. Devolve (baixas, sobra)."""
    restante = round(float(valor or 0), 2)
    baixas, operacoes = [], []
    for nota in _candidatas(empresa, numeros_nf, pedidos):
        if restante <= TOLERANCIA:
            break
        parte = min(_restante(nota), restante)
        if parte <= 0:
            continue
        recebido = round(_valor(nota, "valor_recebido") + parte, 2)
        quitada = recebido >= _valor(nota, "valor_total") - TOLERANCIA
        operacoes.append({"tipo": "atualizar", "aba": "notas", "id": nota["id"], "usuario": usuario, "dados": {
            "valor_recebido": recebido,
            "status": "Recebido" if quitada else "Parcial",
            "data_recebimento": data,
            **({"cheque_id": cheque_id} if cheque_id else {}),
        }})
        baixas.append({"id": nota["id"], "numero_nf": nota.get("numero_nf") or "", "valor": round(parte, 2),
                       "quitada": quitada, "material": nota.get("material") or ""})
        restante = round(restante - parte, 2)
    if operacoes:
        banco().aplicar_lote(operacoes)
    return baixas, max(restante, 0.0)


def texto_das_baixas(baixas: list[dict], sobra: float = 0.0) -> str:
    partes = [f"#{b['id']} NF {b['numero_nf'] or '—'}: {moeda(b['valor'])}" for b in baixas]
    if sobra > TOLERANCIA:
        partes.append(f"sobra (crédito): {moeda(sobra)}")
    return "; ".join(partes)


def _baixas_do_texto(texto: str) -> list[tuple[int, float]]:
    saida = []
    for id_, valor in re.findall(r"#(\d+)[^:;]*:\s*R\$\s*([\d.]+,\d{2})", texto or ""):
        saida.append((int(id_), float(valor.replace(".", "").replace(",", "."))))
    return saida


def sobra_do_recebimento(recebimento: dict) -> float:
    """Quanto deste recebimento ainda não baixou nota nenhuma (crédito da empresa)."""
    if recebimento.get("status") == "Cancelado":
        return 0.0
    aplicado = sum(valor for _, valor in _baixas_do_texto(recebimento.get("aplicacoes")))
    return round(_valor(recebimento, "valor") - aplicado, 2)


def credito_da_empresa(empresa: str) -> float:
    return round(sum(sobra_do_recebimento(r) for r in listar("recebimentos")
                     if normalizar(r.get("empresa")) == normalizar(empresa)), 2)


def aplicar_creditos(empresa: str, usuario: str = "") -> list[dict]:
    """Dinheiro que chegou antes da nota: assim que a nota é lançada, o crédito baixa sozinho."""
    baixas_feitas = []
    for recebimento in sorted(listar("recebimentos"), key=lambda r: (str(r.get("data") or ""), r["id"])):
        if normalizar(recebimento.get("empresa")) != normalizar(empresa):
            continue
        sobra = sobra_do_recebimento(recebimento)
        if sobra <= TOLERANCIA:
            continue
        baixas, resto = _aplicar(empresa, sobra, lista_de_numeros(recebimento.get("notas")),
                                 lista_de_numeros(recebimento.get("pedidos")),
                                 _data(recebimento.get("data")) or date.today(), usuario,
                                 recebimento.get("cheque_id") or None)
        if not baixas:
            continue
        anterior = re.sub(r";?\s*sobra \(crédito\):[^;]*", "", recebimento.get("aplicacoes") or "").strip("; ")
        texto = "; ".join(p for p in (anterior, texto_das_baixas(baixas, resto)) if p)
        banco().atualizar(recebimento["id"], {"aplicacoes": texto[:500]}, "recebimentos", usuario)
        baixas_feitas += baixas
    return baixas_feitas


def registrar_recebimento(dados: dict, usuario: str = "", arquivo: dict | None = None) -> dict:
    """Registra um Pix/TED/depósito/cheque recebido e dá baixa nas notas fiscais citadas."""
    valor = round(float(dados.get("valor") or 0), 2)
    if valor <= 0:
        raise ErroEmpresas("Informe o valor recebido.")
    numeros_nf = lista_de_numeros(dados.get("notas"))
    pedidos = lista_de_numeros(dados.get("pedidos"))
    nome = str(dados.get("empresa") or "").strip()
    if not nome:
        nome = _empresa_pelas_notas(numeros_nf, pedidos)
    if not nome:
        raise ErroEmpresas("Não dá para saber de qual empresa é este recebimento. Informe a empresa.")
    cadastro = empresa_por_nome(nome) or garantir_empresa(nome, usuario=usuario)
    data = _data(dados.get("data")) or date.today()
    forma = str(dados.get("forma") or "Pix").strip() or "Pix"
    cheque_id = int(dados["cheque_id"]) if str(dados.get("cheque_id") or "").strip().isdigit() else None
    baixas, sobra = _aplicar(cadastro["nome"], valor, numeros_nf, pedidos, data, usuario, cheque_id)
    registro = banco().adicionar({
        "data": data,
        "hora": str(dados.get("hora") or "")[:5],
        "empresa": cadastro["nome"],
        "forma": forma,
        "valor": valor,
        "pagador": str(dados.get("pagador") or "")[:120],
        "id_transacao": str(dados.get("id_transacao") or "")[:120],
        "notas": texto_de_numeros(numeros_nf) or texto_de_numeros([b["numero_nf"] for b in baixas]),
        "pedidos": texto_de_numeros(pedidos),
        "cheque_id": cheque_id,
        "aplicacoes": texto_das_baixas(baixas, sobra),
        "status": "Confirmado",
        "observacoes": str(dados.get("observacoes") or "")[:300],
        "arquivo": (arquivo or {}).get("caminho") or "",
        "arquivo_nome": (arquivo or {}).get("nome") or "",
    }, "recebimentos", usuario)
    registro["baixas"] = baixas
    registro["sobra"] = sobra
    log.info("Recebimento de %s: %s (%d nota(s) baixada(s))", cadastro["nome"], moeda(valor), len(baixas))
    return registro


def _empresa_pelas_notas(numeros_nf: list[str], pedidos: list[str]) -> str:
    for nota in listar("notas"):
        if nota.get("status") == "Cancelado":
            continue
        if numero(nota.get("numero_nf")) in numeros_nf or (pedidos and numero(nota.get("pedido")) in pedidos):
            return nota.get("empresa") or ""
    return ""


def cancelar_recebimento(id_: int, usuario: str = "") -> dict:
    """Desfaz a baixa: devolve os valores às notas e marca o recebimento como cancelado."""
    recebimento = banco().obter(int(id_), "recebimentos")
    if recebimento.get("status") == "Cancelado":
        return recebimento
    operacoes = []
    for nota_id, valor in _baixas_do_texto(recebimento.get("aplicacoes")):
        try:
            nota = banco().obter(nota_id, "notas")
        except RegistroNaoEncontrado:
            continue
        recebido = round(max(0.0, _valor(nota, "valor_recebido") - valor), 2)
        operacoes.append({"tipo": "atualizar", "aba": "notas", "id": nota_id, "usuario": usuario, "dados": {
            "valor_recebido": recebido or None,
            "status": "Em aberto" if recebido <= TOLERANCIA else "Parcial",
            "data_recebimento": None if recebido <= TOLERANCIA else nota.get("data_recebimento"),
        }})
    if operacoes:
        banco().aplicar_lote(operacoes)
    return banco().atualizar(int(id_), {"status": "Cancelado"}, "recebimentos", usuario)


# --------------------------------------------------------------------------- cheques


def cheques(empresa: str = "", status: str = "") -> list[dict]:
    lista = listar("cheques")
    if empresa:
        lista = [c for c in lista if normalizar(c.get("empresa")) == normalizar(empresa)]
    if status:
        lista = [c for c in lista if c.get("status") == status]
    return sorted(lista, key=lambda c: (_data(c.get("vencimento")) or date.max, c["id"]))


def lancar_cheque(dados: dict, usuario: str = "", arquivo: dict | None = None) -> dict:
    """Guarda um cheque pré-datado e marca como "Em cheque" as notas dos pedidos citados."""
    valor = round(float(dados.get("valor") or 0), 2)
    if valor <= 0:
        raise ErroEmpresas("Informe o valor do cheque.")
    pedidos = lista_de_numeros(dados.get("pedidos"))
    numeros_nf = lista_de_numeros(dados.get("notas"))
    nome = str(dados.get("empresa") or "").strip() or _empresa_pelas_notas(numeros_nf, pedidos)
    if not nome:
        raise ErroEmpresas("Não dá para saber de qual empresa é este cheque. Informe a empresa ou os pedidos.")
    cadastro = empresa_por_nome(nome) or garantir_empresa(nome, usuario=usuario)
    vencimento = _data(dados.get("vencimento"))
    registro = banco().adicionar({
        "empresa": cadastro["nome"],
        "numero": str(dados.get("numero") or "").strip()[:20],
        "vencimento": vencimento,
        "valor": valor,
        "banco": str(dados.get("banco") or "").strip()[:60],
        "agencia": str(dados.get("agencia") or "").strip()[:12],
        "coop": str(dados.get("coop") or "").strip()[:12],
        "conta": str(dados.get("conta") or "").strip()[:20],
        "emitente": str(dados.get("emitente") or "").strip()[:80],
        "pedidos": texto_de_numeros(pedidos),
        "notas": texto_de_numeros(numeros_nf),
        "status": str(dados.get("status") or "Em carteira"),
        "cmc7": str(dados.get("cmc7") or "").strip()[:40],
        "observacoes": str(dados.get("observacoes") or "")[:300],
        "arquivo": (arquivo or {}).get("caminho") or "",
        "arquivo_nome": (arquivo or {}).get("nome") or "",
    }, "cheques", usuario)
    vincular_notas_ao_cheque(registro, usuario)
    return registro


def vincular_notas_ao_cheque(cheque: dict, usuario: str = "") -> list[dict]:
    """Notas dos pedidos/NFs do cheque ficam "Em cheque": o pagamento está garantido, mas ainda não entrou."""
    numeros_nf = lista_de_numeros(cheque.get("notas"))
    pedidos = lista_de_numeros(cheque.get("pedidos"))
    if not numeros_nf and not pedidos:
        return []
    operacoes = []
    for nota in notas_da_empresa(cheque.get("empresa") or "", somente_abertas=True):
        if numero(nota.get("numero_nf")) in numeros_nf or numero(nota.get("pedido")) in pedidos:
            if nota.get("status") == "Em aberto":
                operacoes.append({"tipo": "atualizar", "aba": "notas", "id": nota["id"], "usuario": usuario,
                                  "dados": {"status": "Em cheque", "cheque_id": cheque["id"]}})
    return [r["registro"] for r in banco().aplicar_lote(operacoes) if r.get("ok")] if operacoes else []


def atualizar_cheque(id_: int, dados: dict, usuario: str = "") -> dict:
    cheque = banco().obter(int(id_), "cheques")
    limpos = {k: v for k, v in dados.items() if k in ctx.empresas.abas["cheques"].editaveis}
    if limpos.get("status") and limpos["status"] not in STATUS_CHEQUE:
        raise ErroEmpresas("Situação inválida para o cheque.")
    for campo in ("pedidos", "notas"):
        if campo in limpos:
            limpos[campo] = texto_de_numeros(limpos[campo])
    novo_status = limpos.get("status")
    atualizado = banco().atualizar(int(id_), limpos, "cheques", usuario)
    if novo_status == "Compensado" and cheque.get("status") != "Compensado":
        compensar_cheque(atualizado, usuario, _data(limpos.get("data_deposito")))
    elif novo_status in ("Devolvido", "Cancelado") and cheque.get("status") != novo_status:
        soltar_notas_do_cheque(atualizado, usuario)
    elif novo_status == "Em carteira":
        vincular_notas_ao_cheque(atualizado, usuario)
    return banco().obter(int(id_), "cheques")


def compensar_cheque(cheque: dict, usuario: str = "", data: date | None = None, arquivo: dict | None = None) -> dict:
    """Cheque compensado (ou depósito comprovado): vira um recebimento e dá baixa nas notas.

    ``arquivo``: o comprovante do depósito, guardado no recebimento (aparece na central de comprovantes).
    """
    ja = [r for r in listar("recebimentos") if r.get("cheque_id") == cheque["id"] and r.get("status") != "Cancelado"]
    if ja:
        return ja[0]
    quando = data or _data(cheque.get("data_deposito")) or _data(cheque.get("vencimento")) or date.today()
    notas_vinculadas = [n for n in listar("notas") if n.get("cheque_id") == cheque["id"]]
    for nota in notas_vinculadas:  # "Em cheque" volta a ser "Em aberto" para a baixa poder ser aplicada
        if nota.get("status") == "Em cheque":
            banco().atualizar(nota["id"], {"status": "Em aberto"}, "notas", usuario)
    recebimento = registrar_recebimento({
        "empresa": cheque.get("empresa"),
        "forma": "Cheque",
        "valor": cheque.get("valor"),
        "data": quando,
        "pagador": cheque.get("emitente") or cheque.get("empresa"),
        "notas": cheque.get("notas") or texto_de_numeros([n.get("numero_nf") for n in notas_vinculadas]),
        "pedidos": cheque.get("pedidos"),
        "cheque_id": cheque["id"],
        "observacoes": f"Cheque {cheque.get('numero') or ''} · {cheque.get('banco') or ''}".strip(" ·"),
    }, usuario, arquivo)
    banco().atualizar(cheque["id"], {"status": "Compensado", "data_deposito": quando}, "cheques", usuario)
    return recebimento


def soltar_notas_do_cheque(cheque: dict, usuario: str = "") -> None:
    operacoes = [{"tipo": "atualizar", "aba": "notas", "id": n["id"], "usuario": usuario,
                  "dados": {"status": "Em aberto", "cheque_id": None}}
                 for n in listar("notas") if n.get("cheque_id") == cheque["id"] and n.get("status") == "Em cheque"]
    if operacoes:
        banco().aplicar_lote(operacoes)


def excluir_cheque(id_: int, usuario: str = "") -> None:
    cheque = banco().obter(int(id_), "cheques")
    soltar_notas_do_cheque(cheque, usuario)
    banco().excluir(int(id_), "cheques", usuario)


def cheque_parecido(dados: dict) -> dict | None:
    """Evita cadastrar o mesmo cheque duas vezes (mesmo número e valor, ou mesma linha CMC7)."""
    cmc7 = digitos(dados.get("cmc7"))
    numero_cheque = digitos(dados.get("numero"))
    valor = round(float(dados.get("valor") or 0), 2)
    for cheque in listar("cheques"):
        if cheque.get("status") == "Cancelado":
            continue
        if cmc7 and digitos(cheque.get("cmc7")) == cmc7:
            return cheque
        if numero_cheque and digitos(cheque.get("numero")) == numero_cheque and abs(_valor(cheque, "valor") - valor) < TOLERANCIA:
            return cheque
    return None


def cheque_do_comprovante(empresa: str, valor, texto: str = "") -> dict | None:
    """Comprovante de depósito de um cheque que está em carteira: mesmo valor (ou número citado)."""
    alvo = round(float(valor or 0), 2)
    if alvo <= 0:
        return None
    em_carteira = cheques(empresa, "Em carteira")
    citados = lista_de_numeros(texto)
    pelo_numero = [c for c in em_carteira if c.get("numero") and numero(c["numero"]) in citados
                   and abs(_valor(c, "valor") - alvo) <= TOLERANCIA]
    if len(pelo_numero) == 1:
        return pelo_numero[0]
    pelo_valor = [c for c in em_carteira if abs(_valor(c, "valor") - alvo) <= TOLERANCIA]
    return pelo_valor[0] if len(pelo_valor) == 1 else None


def cheques_do_deposito(dados: dict) -> list[dict]:
    """Os cheques em carteira que aparecem num comprovante de depósito (pela linha CMC-7 ou pelo número).

    Só devolve a lista quando **todos** os cheques do comprovante foram achados — e, com um cheque só, quando o
    valor bate. Sem CMC-7 legível, cai no valor: um único cheque em carteira com aquele valor.
    """
    em_carteira = cheques(status="Em carteira")
    alvo = round(float(dados.get("valor") or 0), 2)
    achados: list[dict] = []
    for lido in dados.get("cheques") or []:
        cmc7 = digitos(lido.get("cmc7"))
        numero_lido = numero(lido.get("numero"))
        candidato = next((c for c in em_carteira if cmc7 and digitos(c.get("cmc7")) == cmc7), None)
        if candidato is None and numero_lido:
            mesmos = [c for c in em_carteira if numero(c.get("numero")) == numero_lido and c not in achados]
            if len(mesmos) > 1 and alvo:
                mesmos = [c for c in mesmos if abs(_valor(c, "valor") - alvo) <= TOLERANCIA] or mesmos
            candidato = mesmos[0] if len(mesmos) == 1 else None
        if candidato is None:
            return []
        if candidato not in achados:
            achados.append(candidato)
    if achados:
        total = round(sum(_valor(c, "valor") for c in achados), 2)
        return achados if not alvo or abs(total - alvo) <= TOLERANCIA else []
    pelo_valor = [c for c in em_carteira if alvo and abs(_valor(c, "valor") - alvo) <= TOLERANCIA]
    return pelo_valor if len(pelo_valor) == 1 else []


def cheques_a_depositar(hoje: date | None = None, dias: int = 0) -> list[dict]:
    hoje = hoje or date.today()
    limite = hoje + timedelta(days=dias) if dias else None
    saida = []
    for cheque in cheques(status="Em carteira"):
        vencimento = _data(cheque.get("vencimento"))
        if not vencimento or (limite and vencimento > limite):
            continue
        saida.append(cheque)
    return saida


# --------------------------------------------------------------------------- fechamento


def fechamento(empresa: str, competencia: str = "", hoje: date | None = None) -> dict:
    """Fechamento de uma empresa: as linhas do período, o total, o que já foi recebido e quanto falta."""
    hoje = hoje or date.today()
    cadastro = empresa_por_nome(empresa)
    if not cadastro:
        raise ErroEmpresas(f"Empresa “{empresa}” não encontrada.")
    dia = dia_fechamento(cadastro)
    competencia = competencia or competencia_atual(dia, hoje)
    inicio, fim = periodo(competencia, dia)
    linhas = notas_da_empresa(cadastro["nome"], competencia)
    total = round(sum(_valor(n, "valor_total") for n in linhas), 2)
    recebido = round(sum(_valor(n, "valor_recebido") for n in linhas), 2)
    em_cheque = round(sum(_restante(n) for n in linhas if n.get("status") == "Em cheque"), 2)
    recebimentos = [r for r in listar("recebimentos")
                    if normalizar(r.get("empresa")) == normalizar(cadastro["nome"]) and r.get("status") != "Cancelado"
                    and inicio <= (_data(r.get("data")) or date.min) <= fim]
    return {
        "empresa": cadastro["nome"],
        "empresa_id": cadastro["id"],
        "cnpj": cadastro.get("cnpj") or "",
        "competencia": competencia,
        "titulo": titulo_competencia(competencia),
        "dia_fechamento": dia,
        "inicio": inicio,
        "fim": fim,
        "fechado": hoje > fim,
        "gerado_em": datetime.now().replace(microsecond=0),
        "linhas": linhas,
        "recebimentos": sorted(recebimentos, key=lambda r: (_data(r.get("data")) or date.max, r["id"])),
        "cheques": [c for c in cheques(cadastro["nome"]) if c.get("status") in ("Em carteira", "Depositado")],
        "totais": {
            "quantidade": len(linhas),
            "total": total,
            "recebido": recebido,
            "falta": round(total - recebido, 2),
            "em_cheque": em_cheque,
            "notas": len({numero(n.get("numero_nf")) for n in linhas if n.get("numero_nf")}),
        },
    }


def resumo_empresas(hoje: date | None = None, competencia: str = "") -> list[dict]:
    """Uma linha por empresa: fechamento atual, quanto falta receber e o que está em atraso."""
    hoje = hoje or date.today()
    saida = []
    for empresa in empresas():
        dia = dia_fechamento(empresa)
        atual = competencia or competencia_atual(dia, hoje)
        f = fechamento(empresa["nome"], atual, hoje)
        abertas = [n for n in notas_da_empresa(empresa["nome"], somente_abertas=True)]
        em_aberto_total = round(sum(_restante(n) for n in abertas), 2)
        anteriores = round(sum(_restante(n) for n in abertas if (n.get("competencia") or "") < atual), 2)
        cheques_empresa = [c for c in cheques(empresa["nome"], "Em carteira")]
        saida.append({
            "id": empresa["id"],
            "nome": empresa["nome"],
            "cnpj": empresa.get("cnpj") or "",
            "status": empresa.get("status") or "Ativa",
            "dia_fechamento": dia,
            "competencia": atual,
            "periodo": {"inicio": f["inicio"].isoformat(), "fim": f["fim"].isoformat()},
            "fechamento": f["totais"],
            "em_aberto": em_aberto_total,
            "atrasado": anteriores,
            "cheques": {"quantidade": len(cheques_empresa),
                        "valor": round(sum(_valor(c, "valor") for c in cheques_empresa), 2)},
        })
    return sorted(saida, key=lambda e: (-e["em_aberto"], e["nome"].lower()))


def alertas_de_cheques(hoje: date | None = None, dias_antes: int = 3) -> list[dict]:
    """Cheques a depositar no formato dos avisos de vencimento (Windows, Telegram e e-mail)."""
    hoje = hoje or date.today()
    limite = hoje + timedelta(days=max(0, dias_antes))
    saida = []
    for cheque in cheques(status="Em carteira"):
        vencimento = _data(cheque.get("vencimento"))
        if not vencimento or vencimento > limite:
            continue
        saida.append({
            "id": f"cheque-{cheque['id']}",
            "beneficiario": f"Cheque de {cheque.get('empresa') or 'cliente'}"
                            + (f" · nº {cheque['numero']}" if cheque.get("numero") else ""),
            "vencimento": vencimento,
            "valor": _valor(cheque, "valor"),
            "status": "Pendente",
            "numero_documento": cheque.get("numero") or "",
            "linha_digitavel": "",
            "tipo_pagamento": "cheque",
            "chave_pix": "",
        })
    return saida

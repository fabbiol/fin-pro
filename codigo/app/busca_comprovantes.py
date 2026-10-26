"""Central de comprovantes: acha o comprovante de qualquer lançamento (boletos, Pix, cheques, recebimentos das
empresas, caixa e notas fiscais) com filtros por nome, valor, data, número (cheque, NF, documento, pedido,
ID da transação), centro de custo e pessoa — e baixa tudo o que foi filtrado num ZIP.

Cada lançamento vira um item no mesmo formato. ``comprovante_id`` é o arquivo que prova o pagamento/recebimento
(o comprovante do boleto ou Pix, a foto do cheque, o comprovante do Pix recebido, o cupom do caixa, a nota fiscal);
``original_id`` é o arquivo do próprio boleto/cobrança, quando existe.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from datetime import date, datetime

from . import contexto as ctx
from .arquivos import RepositorioArquivos

TIPOS = {
    "boleto": "Boleto",
    "pix": "Pix",
    "cheque": "Cheque",
    "recebimento": "Recebimento",
    "caixa": "Caixa (dinheiro)",
    "nota": "Nota fiscal",
    "diesel": "Diesel",
}
PERMISSAO_DO_TIPO = {"cheque": "empresas", "recebimento": "empresas", "nota": "empresas", "caixa": "caixa",
                     "diesel": "diesel"}
LIMITE_ZIP = 500


def _normal(texto) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def _digitos(texto) -> str:
    return re.sub(r"\D", "", str(texto or ""))


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
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _id(caminho) -> str | None:
    return RepositorioArquivos.id_de_caminho(caminho)


def _item(tipo: str, registro: dict, **campos) -> dict:
    item = {
        "tipo": tipo, "tipo_rotulo": TIPOS[tipo], "id": registro.get("id"),
        "nome": "", "valor": 0.0, "valor_pago": None, "juros_multa": 0.0, "data": None, "vencimento": None,
        "numero": "", "detalhe": "", "centro_custo": (registro.get("centro_custo") or "").strip(),
        "pessoa": "", "situacao": registro.get("status") or "", "comprovante_id": None, "comprovante_nome": "",
        "original_id": None, "original_nome": "", "busca": "", "linha": "",
    }
    item.update(campos)
    item["chave"] = f"{tipo}-{item['id']}"
    return item


# --------------------------------------------------------------------------- cada parte do sistema


def _boletos() -> list[dict]:
    saida = []
    for r in ctx.repositorio.listar():
        if r.get("id") is None or r["id"] < 0:
            continue
        saida.append(_item(
            "boleto", r, nome=r.get("beneficiario") or "", valor=_num(r.get("valor")),
            valor_pago=_num(r.get("valor_pago")) or None, juros_multa=_num(r.get("juros_multa")),
            data=_data(r.get("data_pagamento")) or _data(r.get("vencimento")), vencimento=_data(r.get("vencimento")),
            numero=r.get("numero_documento") or "", detalhe=r.get("emissor") or "",
            pessoa=r.get("pago_por") or r.get("lancado_por") or "",
            comprovante_id=_id(r.get("comprovante")), comprovante_nome=r.get("comprovante_nome") or "",
            original_id=_id(r.get("arquivo")), original_nome=r.get("arquivo_nome") or "",
            busca=" ".join(str(r.get(c) or "") for c in ("documento_beneficiario", "observacoes")),
            linha=_digitos(r.get("linha_digitavel")),
        ))
    return saida


def _pix() -> list[dict]:
    saida = []
    for r in ctx.repositorio_pix.listar():
        if r.get("id") is None or r["id"] < 0:
            continue
        saida.append(_item(
            "pix", r, nome=r.get("recebedor") or "", valor=_num(r.get("valor")),
            valor_pago=_num(r.get("valor_pago")) or None, juros_multa=_num(r.get("juros_multa")),
            data=_data(r.get("data_pagamento")) or _data(r.get("vencimento")), vencimento=_data(r.get("vencimento")),
            numero=r.get("txid") or "", detalhe=r.get("descricao") or "",
            pessoa=r.get("pago_por") or r.get("lancado_por") or "",
            comprovante_id=_id(r.get("comprovante")), comprovante_nome=r.get("comprovante_nome") or "",
            original_id=_id(r.get("arquivo")), original_nome=r.get("arquivo_nome") or "",
            busca=" ".join(str(r.get(c) or "") for c in ("chave", "observacoes")),
        ))
    return saida


def _caixa() -> list[dict]:
    saida = []
    for r in ctx.repositorio_caixa.listar():
        if r.get("id") is None or r["id"] < 0:
            continue
        saida.append(_item(
            "caixa", r, nome=r.get("local") or r.get("descricao") or r.get("movimento") or "",
            valor=_num(r.get("valor")), data=_data(r.get("data")), movimento=r.get("movimento") or "",
            detalhe=f"{r.get('movimento') or ''} · {r.get('descricao') or ''}".strip(" ·"),
            pessoa=r.get("pessoa") or r.get("lancado_por") or "",
            comprovante_id=_id(r.get("arquivo")), comprovante_nome=r.get("arquivo_nome") or "",
            busca=str(r.get("observacoes") or ""),
        ))
    return saida


def _cheques() -> list[dict]:
    saida = []
    for r in ctx.empresas.listar("cheques"):
        saida.append(_item(
            "cheque", r, nome=r.get("empresa") or r.get("emitente") or "", valor=_num(r.get("valor")),
            data=_data(r.get("data_deposito")) or _data(r.get("vencimento")), vencimento=_data(r.get("vencimento")),
            numero=r.get("numero") or "",
            detalhe=" · ".join(p for p in (r.get("banco"), f"pedidos {r['pedidos']}" if r.get("pedidos") else "",
                                           f"NF {r['notas']}" if r.get("notas") else "") if p),
            pessoa=r.get("lancado_por") or "",
            comprovante_id=_id(r.get("arquivo")), comprovante_nome=r.get("arquivo_nome") or "",
            busca=" ".join(str(r.get(c) or "") for c in ("emitente", "pedidos", "notas", "agencia", "conta", "cmc7",
                                                         "observacoes")),
        ))
    return saida


def _recebimentos() -> list[dict]:
    saida = []
    for r in ctx.empresas.listar("recebimentos"):
        saida.append(_item(
            "recebimento", r, nome=r.get("empresa") or r.get("pagador") or "", valor=_num(r.get("valor")),
            data=_data(r.get("data")), numero=r.get("id_transacao") or "",
            detalhe=" · ".join(p for p in (r.get("forma"), r.get("pagador"),
                                           f"NF {r['notas']}" if r.get("notas") else "",
                                           f"pedidos {r['pedidos']}" if r.get("pedidos") else "") if p),
            pessoa=r.get("lancado_por") or "",
            comprovante_id=_id(r.get("arquivo")), comprovante_nome=r.get("arquivo_nome") or "",
            busca=" ".join(str(r.get(c) or "") for c in ("pagador", "notas", "pedidos", "observacoes")),
        ))
    return saida


def _notas() -> list[dict]:
    """Uma nota fiscal pode ter várias linhas (um material por linha): vira um item só, com o total da nota."""
    grupos: dict[tuple, dict] = {}
    for r in ctx.empresas.listar("notas"):
        chave = (_normal(r.get("empresa")), str(r.get("numero_nf") or f"linha-{r['id']}"))
        item = grupos.get(chave)
        if item is None:
            item = grupos[chave] = _item(
                "nota", r, nome=r.get("empresa") or "", data=_data(r.get("data")),
                numero=str(r.get("numero_nf") or ""), pessoa=r.get("lancado_por") or "",
                comprovante_id=_id(r.get("arquivo")), comprovante_nome=r.get("arquivo_nome") or "",
            )
            item["_materiais"], item["_pedidos"] = [], []
        item["valor"] = round(item["valor"] + _num(r.get("valor_total")), 2)
        item["comprovante_id"] = item["comprovante_id"] or _id(r.get("arquivo"))
        if r.get("material"):
            item["_materiais"].append(str(r["material"]))
        if r.get("pedido"):
            item["_pedidos"].append(str(r["pedido"]))
    saida = []
    for item in grupos.values():
        materiais, pedidos = item.pop("_materiais"), item.pop("_pedidos")
        item["detalhe"] = " · ".join(p for p in (", ".join(dict.fromkeys(materiais)),
                                                 f"pedidos {', '.join(dict.fromkeys(pedidos))}" if pedidos else "") if p)
        item["busca"] = " ".join(pedidos + materiais)
        saida.append(item)
    return saida


def _diesel() -> list[dict]:
    """Comprovantes da compra no posto e os canhotos dos abastecimentos."""
    saida = []
    for aba in ("compras", "abastecimentos"):
        for r in ctx.diesel.listar(aba):
            compra = aba == "compras"
            litros = f"{float(r.get('litros') or 0):,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " L"
            item = _item(
                "diesel", r, nome=(r.get("posto") or "Compra de diesel") if compra else (r.get("maquina") or ""),
                valor=_num(r.get("valor")), data=_data(r.get("data")),
                numero=(r.get("documento") or "") if compra else "",
                detalhe=f"{'Compra' if compra else 'Abastecimento'} · {litros}"
                        + (f" · horímetro/km {r['medidor']}" if not compra and r.get("medidor") else ""),
                pessoa=r.get("pessoa") or r.get("lancado_por") or "",
                comprovante_id=_id(r.get("arquivo")), comprovante_nome=r.get("arquivo_nome") or "",
                busca=" ".join(str(r.get(c) or "") for c in ("posto", "forma", "observacoes")),
            )
            item["situacao"] = "Cancelado" if r.get("status") in ("Cancelada", "Cancelado") else "Confirmado"
            item["chave"] = f"diesel-{aba}-{r['id']}"
            saida.append(item)
    return saida


FONTES = {"boleto": _boletos, "pix": _pix, "caixa": _caixa, "cheque": _cheques, "recebimento": _recebimentos,
          "nota": _notas, "diesel": _diesel}


# --------------------------------------------------------------------------- busca


def tipos_permitidos(pode) -> list[str]:
    """``pode(permissao)``: a pessoa que está buscando pode ver essa parte do sistema?"""
    return [t for t in TIPOS if t not in PERMISSAO_DO_TIPO or pode(PERMISSAO_DO_TIPO[t])]


def _valor_pesquisado(texto: str) -> float | None:
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto or re.fullmatch(r"[1-9]\d{0,2}(\.\d{3})+", texto):  # "1.500" é mil e quinhentos
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return None


def _na_linha(digitos: str, item: dict) -> bool:
    """Linha digitável só entra na busca com um trecho grande (8+ dígitos): números curtos achariam boletos por acaso."""
    return len(digitos) >= 8 and digitos in item["linha"]


def buscar(pode=lambda _p: True, *, q: str = "", tipos: list[str] | None = None, de: date | None = None,
           ate: date | None = None, valor: str = "", valor_min: float | None = None, valor_max: float | None = None,
           numero: str = "", centro: str = "", pessoa: str = "", comprovante: str = "com",
           ordenar: str = "data", direcao: str = "desc") -> list[dict]:
    permitidos = tipos_permitidos(pode)
    escolhidos = [t for t in (tipos or permitidos) if t in permitidos]
    itens: list[dict] = []
    for tipo in escolhidos:
        itens += FONTES[tipo]()

    termos = _normal(q).split()
    numero_normal, numero_digitos = _normal(numero), _digitos(numero)
    valor_exato = _valor_pesquisado(valor)
    centro_normal, pessoa_normal = _normal(centro), _normal(pessoa)

    saida = []
    for item in itens:
        if item["situacao"] == "Cancelado" and comprovante != "todos":
            continue
        tem = bool(item["comprovante_id"])
        if comprovante == "com" and not tem:
            continue
        if comprovante == "sem":
            # "sem comprovante" só faz sentido para o que já foi pago (no caixa, as saídas: entrada não tem cupom)
            if tem or (item["tipo"] in ("boleto", "pix") and item["situacao"] != "Pago")                     or item.get("movimento") == "Entrada":
                continue
        if de and (not item["data"] or item["data"] < de):
            continue
        if ate and (not item["data"] or item["data"] > ate):
            continue
        valores = [v for v in (item["valor"], item["valor_pago"]) if v]
        if valor_exato is not None and not any(abs(v - valor_exato) < 0.01 for v in valores):
            continue
        if valor_min is not None and not any(v >= valor_min for v in valores):
            continue
        if valor_max is not None and not any(v <= valor_max for v in valores):
            continue
        if centro_normal and _normal(item["centro_custo"]) != centro_normal:
            continue
        if pessoa_normal and pessoa_normal not in _normal(item["pessoa"]):
            continue
        texto_numeros = f"{item['numero']} {item['detalhe']} {item['busca']}"
        if numero_normal and numero_normal not in _normal(texto_numeros)                 and not (numero_digitos and numero_digitos in _digitos(item["numero"]))                 and not _na_linha(numero_digitos, item):
            continue
        if termos:
            alvo = _normal(" ".join(str(item[c] or "") for c in ("nome", "numero", "detalhe", "busca", "centro_custo",
                                                                  "pessoa", "tipo_rotulo", "comprovante_nome")))
            if not all(t in alvo or _na_linha(_digitos(t), item) for t in termos):
                continue
        saida.append(item)

    reverso = direcao != "asc"
    if ordenar == "valor":
        saida.sort(key=lambda i: i["valor"], reverse=reverso)
    elif ordenar == "nome":
        saida.sort(key=lambda i: _normal(i["nome"]), reverse=reverso)
    else:
        saida.sort(key=lambda i: (i["data"] or date.min, i["tipo"], i["id"] or 0), reverse=reverso)
    return saida


def resumo(itens: list[dict]) -> dict:
    por_tipo: dict[str, dict] = {}
    for item in itens:
        bloco = por_tipo.setdefault(item["tipo"], {"tipo": item["tipo"], "rotulo": item["tipo_rotulo"],
                                                   "quantidade": 0, "valor": 0.0})
        bloco["quantidade"] += 1
        bloco["valor"] = round(bloco["valor"] + (item["valor_pago"] or item["valor"]), 2)
    return {"quantidade": len(itens), "com_arquivo": sum(1 for i in itens if i["comprovante_id"]),
            "valor": round(sum(i["valor_pago"] or i["valor"] for i in itens), 2),
            "por_tipo": [por_tipo[t] for t in TIPOS if t in por_tipo]}


def serializar(item: dict) -> dict:
    saida = {k: v for k, v in item.items() if k not in ("busca", "linha")}
    for campo in ("data", "vencimento"):
        saida[campo] = item[campo].isoformat() if item[campo] else None
    meta = ctx.arquivos.meta(item["comprovante_id"]) if item["comprovante_id"] else None
    saida["comprovante_pdf"] = bool(meta and meta.get("tipo") == "pdf")  # a tela mostra PDF num quadro e foto como imagem
    if item["comprovante_id"] and not meta:
        saida["comprovante_id"] = None  # o arquivo sumiu da pasta: não oferece um link quebrado
    return saida


# --------------------------------------------------------------------------- ZIP


def _nome_arquivo(item: dict, extensao: str) -> str:
    valor = f"{item['valor_pago'] or item['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    partes = [item["data"].isoformat() if item["data"] else "sem-data", item["tipo_rotulo"], item["nome"] or "sem nome"]
    if item["numero"]:
        partes.append(f"n{item['numero']}")
    partes.append(f"R$ {valor}")
    nome = " - ".join(partes)
    nome = re.sub(r'[\\/:*?"<>|\r\n]+', " ", nome)
    return re.sub(r"\s+", " ", nome).strip()[:150] + extensao


def gerar_zip(itens: list[dict]) -> tuple[bytes, int]:
    """ZIP com os comprovantes dos itens (nomes com data, tipo, nome, número e valor). Devolve o ZIP e quantos entraram."""
    memoria = io.BytesIO()
    usados: set[str] = set()
    colocados = 0
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zipado:
        for item in itens:
            if colocados >= LIMITE_ZIP:
                break
            caminho = ctx.arquivos.caminho_original(item["comprovante_id"]) if item["comprovante_id"] else None
            if not caminho:
                continue
            extensao = ".jpg" if caminho.suffix.lower() == ".img" else caminho.suffix.lower()
            nome = _nome_arquivo(item, extensao)
            base = nome[: -len(extensao)]
            contador = 2
            while nome.lower() in usados:
                nome = f"{base} ({contador}){extensao}"
                contador += 1
            usados.add(nome.lower())
            zipado.write(caminho, f"{item['tipo_rotulo']}/{nome}")
            colocados += 1
    return memoria.getvalue(), colocados

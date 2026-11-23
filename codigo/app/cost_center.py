"""Centro de custo de um lançamento: um nome só ou o valor dividido entre vários centros.

A divisão fica no próprio campo ``centro_custo``, num texto que a planilha, as telas e os relatórios mostram como está:
``"Energia R$ 600,00 + Frota R$ 400,00"``. Um nome sozinho, o caso comum, continua igual.
"""

from __future__ import annotations

import re

MAX_NAME = 60
MAX_PARTS = 10
_PART = re.compile(r"(.+?) R\$ ?(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2})(?: \+ |$)")


def _clean(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _format(parts: list[tuple[str, float]]) -> str:
    return " + ".join(f"{name} R$ {money(share)}" for name, share in parts)


def split_parts(text) -> list[tuple[str, float]]:
    """As partes de um centro de custo dividido: ``[(nome, valor), ...]``. Um nome sozinho (ou vazio) devolve ``[]``."""
    text = _clean(text)
    parts, position = [], 0
    for match in _PART.finditer(text):
        if match.start() != position:
            return []
        parts.append((match.group(1).strip(), float(match.group(2).replace(".", "").replace(",", "."))))
        position = match.end()
    return parts if position == len(text) else []


def names(text) -> list[str]:
    """Os centros de custo de um lançamento: nenhum, um ou vários."""
    text = _clean(text)
    return [name for name, _ in split_parts(text)] or ([text] if text else [])


def allocate(text, total: float) -> list[tuple[str, float]]:
    """``total`` repartido entre os centros, na proporção da divisão: ``[(nome, valor), ...]`` (nome ``""`` = sem centro).

    A soma dá sempre ``total`` (os centavos que sobram ficam na última parte). Serve para o valor pago com juros ou
    desconto e para uma divisão que ficou diferente do valor (ex.: valor mudado direto na planilha).
    """
    parts = split_parts(text)
    weight = sum(share for _, share in parts)
    if len(parts) < 2 or weight <= 0:
        return [(parts[0][0] if parts else _clean(text), total)]
    shares, used = [], 0.0
    for name, share in parts[:-1]:
        amount = round(total * share / weight, 2)
        shares.append((name, amount))
        used += amount
    return [*shares, (parts[-1][0], round(total - used, 2))]


def validate(text, value=None) -> str:
    """O centro de custo pronto para gravar. Numa divisão, cada centro aparece uma vez, com valor, e a soma é o valor do
    lançamento; fora disso levanta ``ValueError`` com a explicação."""
    text = _clean(text)
    parts = split_parts(text)
    if not parts:
        if len(text) > MAX_NAME:
            raise ValueError(f"O nome do centro de custo tem até {MAX_NAME} caracteres.")
        return text
    if len(parts) > MAX_PARTS:
        raise ValueError(f"Divida o valor em até {MAX_PARTS} centros de custo.")
    seen = set()
    for name, share in parts:
        if len(name) > MAX_NAME:
            raise ValueError(f"O nome do centro de custo tem até {MAX_NAME} caracteres.")
        if share <= 0:
            raise ValueError(f'Informe o valor de "{name}" na divisão por centro de custo.')
        if name.lower() in seen:
            raise ValueError(f'O centro de custo "{name}" aparece mais de uma vez na divisão.')
        seen.add(name.lower())
    if len(parts) == 1:
        return parts[0][0]
    if not value:
        raise ValueError("Informe o valor antes de dividir entre centros de custo.")
    total = round(sum(share for _, share in parts), 2)
    if abs(total - round(float(value), 2)) >= 0.005:
        raise ValueError(f"A divisão por centro de custo soma R$ {money(total)}, mas o valor é R$ {money(float(value))}. "
                         "Refaça a divisão.")
    return _format(parts)


def rename(text, old: str, new: str) -> str | None:
    """O centro de custo com ``old`` trocado por ``new``; ``None`` quando o lançamento não usa ``old``."""
    text, old = _clean(text), _clean(old).lower()
    parts = split_parts(text)
    if not parts:
        return new if text and text.lower() == old else None
    if not any(name.lower() == old for name, _ in parts):
        return None
    return _format([(new if name.lower() == old else name, share) for name, share in parts])

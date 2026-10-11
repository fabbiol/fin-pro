"""Linha digitável e código de barras de boletos (padrões FEBRABAN).

Suporta os dois tipos de boleto usados no Brasil:

* **Bancário (cobrança)** — linha digitável com 47 dígitos, código de barras com 44.
* **Arrecadação (concessionárias, tributos, convênios)** — linha com 48 dígitos
  (4 blocos de 11 + DV), código de barras com 44 começando por ``8``.

Inclui validação de todos os dígitos verificadores, conversão entre os formatos,
decodificação de banco/valor/vencimento e correção automática de um dígito
lido errado (útil para OCR).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import product
from datetime import date, timedelta
from decimal import Decimal

from .bancos import SEGMENTOS_ARRECADACAO, nome_banco

# O fator de vencimento chegou a 9999 em 21/02/2025 e reiniciou em 1000 no dia 22/02/2025.
BASE_FATOR_ORIGINAL = date(1997, 10, 7)
BASE_FATOR_NOVO_CICLO = date(2025, 2, 22) - timedelta(days=1000)

BANCARIO = "bancario"
ARRECADACAO = "arrecadacao"


def somente_digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


# --------------------------------------------------------------------------- módulos


def modulo10(numero: str) -> int:
    soma, peso = 0, 2
    for digito in reversed(numero):
        produto = int(digito) * peso
        soma += produto // 10 + produto % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def _soma_modulo11(numero: str) -> int:
    soma, peso = 0, 2
    for digito in reversed(numero):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    return soma


def modulo11_bancario(numero: str) -> int:
    dv = 11 - _soma_modulo11(numero) % 11
    return 1 if dv in (0, 10, 11) else dv


def modulo11_arrecadacao(numero: str) -> int:
    resto = _soma_modulo11(numero) % 11
    return 0 if resto in (0, 1) else 11 - resto


def _dv_arrecadacao(numero: str, identificador: str) -> int:
    return modulo10(numero) if identificador in ("6", "7") else modulo11_arrecadacao(numero)


# --------------------------------------------------------------------------- conversões


def linha_para_barras_bancario(linha: str) -> str:
    return linha[0:4] + linha[32] + linha[33:47] + linha[4:9] + linha[10:20] + linha[21:31]


def barras_para_linha_bancario(barras: str) -> str:
    campo1 = barras[0:4] + barras[19:24]
    campo2 = barras[24:34]
    campo3 = barras[34:44]
    return (
        campo1 + str(modulo10(campo1))
        + campo2 + str(modulo10(campo2))
        + campo3 + str(modulo10(campo3))
        + barras[4]
        + barras[5:19]
    )


def linha_para_barras_arrecadacao(linha: str) -> str:
    return linha[0:11] + linha[12:23] + linha[24:35] + linha[36:47]


def barras_para_linha_arrecadacao(barras: str) -> str:
    identificador = barras[2]
    blocos = [barras[i:i + 11] for i in range(0, 44, 11)]
    return "".join(b + str(_dv_arrecadacao(b, identificador)) for b in blocos)


def formatar_linha(linha: str) -> str:
    """Formata a linha digitável como aparece impressa no boleto."""
    d = somente_digitos(linha)
    if len(d) == 47:
        return f"{d[0:5]}.{d[5:10]} {d[10:15]}.{d[15:21]} {d[21:26]}.{d[26:32]} {d[32]} {d[33:47]}"
    if len(d) == 48:
        return " ".join(f"{d[i:i + 11]}-{d[i + 11]}" for i in range(0, 48, 12))
    return d


# --------------------------------------------------------------------------- vencimento


def data_por_fator(fator: int, referencia: date | None = None) -> date | None:
    """Converte o fator de vencimento em data, escolhendo o ciclo mais próximo da referência."""
    if fator < 1000:
        return None
    referencia = referencia or date.today()
    candidatas = [BASE_FATOR_ORIGINAL + timedelta(days=fator), BASE_FATOR_NOVO_CICLO + timedelta(days=fator)]
    return min(candidatas, key=lambda d: abs((d - referencia).days))


def fator_por_data(vencimento: date) -> int:
    base = BASE_FATOR_NOVO_CICLO if vencimento >= date(2025, 2, 22) else BASE_FATOR_ORIGINAL
    return (vencimento - base).days


def _data_no_campo_livre(barras: str, referencia: date) -> date | None:
    """Convênios costumam (sem obrigatoriedade) gravar o vencimento como AAAAMMDD no campo livre."""
    livre = barras[19:44]
    for i in range(len(livre) - 7):
        trecho = livre[i:i + 8]
        try:
            candidata = date(int(trecho[0:4]), int(trecho[4:6]), int(trecho[6:8]))
        except ValueError:
            continue
        if abs((candidata - referencia).days) <= 3 * 366:
            return candidata
    return None


# --------------------------------------------------------------------------- análise


@dataclass
class ResultadoCodigo:
    tipo: str
    linha_digitavel: str
    codigo_barras: str
    valido: bool
    erros: list[str] = field(default_factory=list)
    banco_codigo: str | None = None
    banco_nome: str | None = None
    segmento: str | None = None
    valor: Decimal | None = None
    vencimento: date | None = None
    vencimento_estimado: bool = False
    fator_vencimento: int | None = None
    corrigido: bool = False

    @property
    def linha_formatada(self) -> str:
        return formatar_linha(self.linha_digitavel)

    @property
    def emissor(self) -> str:
        return self.banco_nome or self.segmento or ""

    def para_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "linha_digitavel": self.linha_digitavel,
            "linha_formatada": self.linha_formatada,
            "codigo_barras": self.codigo_barras,
            "valido": self.valido,
            "erros": self.erros,
            "banco_codigo": self.banco_codigo,
            "banco_nome": self.banco_nome,
            "segmento": self.segmento,
            "emissor": self.emissor,
            "valor": float(self.valor) if self.valor is not None else None,
            "vencimento": self.vencimento.isoformat() if self.vencimento else None,
            "vencimento_estimado": self.vencimento_estimado,
            "fator_vencimento": self.fator_vencimento,
            "corrigido": self.corrigido,
        }


def _analisar_bancario(linha: str | None, barras: str, referencia: date) -> ResultadoCodigo:
    erros: list[str] = []
    if linha is None:
        linha = barras_para_linha_bancario(barras)
    else:
        campos = [(linha[0:9], linha[9]), (linha[10:20], linha[20]), (linha[21:31], linha[31])]
        for i, (corpo, dv) in enumerate(campos, start=1):
            if modulo10(corpo) != int(dv):
                erros.append(f"Dígito verificador do campo {i} inválido")

    dv_geral = modulo11_bancario(barras[:4] + barras[5:])
    if dv_geral != int(barras[4]):
        erros.append("Dígito verificador geral inválido")
    if barras[3] != "9":
        erros.append("Código de moeda diferente de Real (9)")

    fator = int(barras[5:9])
    codigo_banco = barras[0:3]
    return ResultadoCodigo(
        tipo=BANCARIO,
        linha_digitavel=linha,
        codigo_barras=barras,
        valido=not erros,
        erros=erros,
        banco_codigo=codigo_banco,
        banco_nome=nome_banco(codigo_banco),
        valor=Decimal(int(barras[9:19])) / 100,
        vencimento=data_por_fator(fator, referencia),
        fator_vencimento=fator,
    )


def _analisar_arrecadacao(linha: str | None, barras: str, referencia: date) -> ResultadoCodigo:
    erros: list[str] = []
    identificador = barras[2]
    if identificador not in "6789":
        erros.append("Identificador de valor inválido (3º dígito deve ser 6, 7, 8 ou 9)")
        identificador = "6"

    if linha is None:
        linha = barras_para_linha_arrecadacao(barras)
    else:
        for i in range(4):
            bloco, dv = linha[i * 12:i * 12 + 11], linha[i * 12 + 11]
            if _dv_arrecadacao(bloco, identificador) != int(dv):
                erros.append(f"Dígito verificador do bloco {i + 1} inválido")

    if _dv_arrecadacao(barras[:3] + barras[4:], identificador) != int(barras[3]):
        erros.append("Dígito verificador geral inválido")

    valor_real = identificador in ("6", "8")
    vencimento = _data_no_campo_livre(barras, referencia)
    return ResultadoCodigo(
        tipo=ARRECADACAO,
        linha_digitavel=linha,
        codigo_barras=barras,
        valido=not erros,
        erros=erros,
        segmento=SEGMENTOS_ARRECADACAO.get(barras[1], f"Segmento {barras[1]}"),
        valor=Decimal(int(barras[4:15])) / 100 if valor_real else None,
        vencimento=vencimento,
        vencimento_estimado=vencimento is not None,
    )


def analisar(codigo: str, referencia: date | None = None) -> ResultadoCodigo | None:
    """Analisa uma linha digitável (47/48 dígitos) ou código de barras (44 dígitos).

    Retorna ``None`` quando a quantidade de dígitos não corresponde a nenhum formato.
    """
    d = somente_digitos(codigo)
    referencia = referencia or date.today()
    if len(d) == 44:
        if d[0] == "8":
            return _analisar_arrecadacao(None, d, referencia)
        return _analisar_bancario(None, d, referencia)
    if len(d) == 47:
        return _analisar_bancario(d, linha_para_barras_bancario(d), referencia)
    if len(d) == 48 and d[0] == "8":
        return _analisar_arrecadacao(d, linha_para_barras_arrecadacao(d), referencia)
    return None


# Pares de dígitos que o OCR costuma confundir (usados para ordenar as correções possíveis)
_CONFUSOES_OCR = {frozenset(p) for p in (
    ("0", "8"), ("3", "8"), ("5", "6"), ("6", "8"), ("1", "7"), ("4", "9"), ("0", "6"),
    ("0", "9"), ("5", "8"), ("2", "7"), ("1", "4"), ("3", "5"), ("8", "9"),
)}


def _variacoes_um_digito(trecho: str, valido) -> list[str]:
    saida = []
    for pos in range(len(trecho)):
        for novo in "0123456789":
            if novo != trecho[pos]:
                tentativa = trecho[:pos] + novo + trecho[pos + 1:]
                if valido(tentativa):
                    saida.append(tentativa)
    return saida


def _plausibilidade(original: str, corrigido: str) -> tuple[int, int]:
    trocas = [(a, b) for a, b in zip(original, corrigido) if a != b]
    return len(trocas), sum(0 if frozenset(t) in _CONFUSOES_OCR else 1 for t in trocas)


def candidatos_correcao(codigo: str, referencia: date | None = None, limite: int = 6) -> list[ResultadoCodigo]:
    """Linhas válidas próximas da informada, das mais para as menos prováveis.

    Cada campo da linha digitável tem seu próprio dígito verificador, então é possível
    corrigir **um dígito por campo** (vários erros em campos diferentes) e confirmar pelo DV
    geral. Quando todos os campos conferem, procura um erro no DV geral/fator/valor.
    """
    d = somente_digitos(codigo)
    if len(d) not in (47, 48):
        return []
    atual = analisar(d, referencia)
    if atual is None or atual.valido:
        return []

    if len(d) == 47:
        blocos = [(0, 10), (10, 21), (21, 32)]
        valido_bloco = lambda t: modulo10(t[:-1]) == int(t[-1])  # noqa: E731
        cauda = (32, 47)  # DV geral + fator + valor: só o DV geral protege
    else:
        identificador = d[2] if d[2] in "6789" else None
        if identificador is None:
            blocos = []
            valido_bloco = None
        else:
            blocos = [(0, 12), (12, 24), (24, 36), (36, 48)]
            valido_bloco = lambda t: _dv_arrecadacao(t[:11], identificador) == int(t[11])  # noqa: E731
        cauda = None

    candidatos: dict[str, ResultadoCodigo] = {}

    def registrar(linha: str):
        if linha in candidatos:
            return
        r = analisar(linha, referencia)
        if r and r.valido:
            r.corrigido = True
            candidatos[linha] = r

    if blocos:
        opcoes = []
        falhos = 0
        for a, b in blocos:
            trecho = d[a:b]
            if valido_bloco(trecho):
                opcoes.append([trecho])
            else:
                falhos += 1
                opcoes.append(_variacoes_um_digito(trecho, valido_bloco))
        if falhos <= 3:
            prefixos = ["".join(c) for c in product(*opcoes)] if all(opcoes) else []
            resto = d[blocos[-1][1]:]
            for prefixo in prefixos:
                registrar(prefixo + resto)
            if not candidatos and cauda and falhos <= 1:
                inicio, fim = cauda
                for prefixo in prefixos or [d[:inicio]]:
                    base = prefixo + resto
                    for pos in range(inicio, fim):
                        for novo in "0123456789":
                            if novo != base[pos]:
                                registrar(base[:pos] + novo + base[pos + 1:])
    else:
        # Identificador de valor ilegível: força bruta de um dígito
        for pos in range(len(d)):
            for novo in "0123456789":
                if novo != d[pos]:
                    registrar(d[:pos] + novo + d[pos + 1:])

    ordenados = sorted(candidatos.items(), key=lambda item: _plausibilidade(d, item[0]))
    return [r for _, r in ordenados[:limite]]


def tentar_corrigir(codigo: str, referencia: date | None = None) -> ResultadoCodigo | None:
    """Retorna a linha válida (corrigida se preciso) apenas quando a correção é única."""
    atual = analisar(codigo, referencia)
    if atual is None:
        return None
    if atual.valido:
        return atual
    candidatos = candidatos_correcao(codigo, referencia, limite=2)
    return candidatos[0] if len(candidatos) == 1 else None

from datetime import date
from decimal import Decimal

from app.boleto.codigo import (
    ARRECADACAO,
    BANCARIO,
    _dv_arrecadacao,
    analisar,
    barras_para_linha_arrecadacao,
    barras_para_linha_bancario,
    candidatos_correcao,
    data_por_fator,
    fator_por_data,
    formatar_linha,
    linha_para_barras_bancario,
    tentar_corrigir,
)

# Exemplo público de boleto do Banco do Brasil (R$ 1,00, vencimento 31/12/2007)
LINHA_BB = "00190500954014481606906809350314337370000000100"


def test_boleto_bancario_real_valido():
    r = analisar(LINHA_BB, referencia=date(2008, 1, 1))
    assert r.valido and r.erros == []
    assert r.tipo == BANCARIO
    assert r.banco_nome == "Banco do Brasil"
    assert r.valor == Decimal("1.00")
    assert r.vencimento == date(2007, 12, 31)
    assert len(r.codigo_barras) == 44


def test_conversao_linha_barras_ida_e_volta():
    barras = linha_para_barras_bancario(LINHA_BB)
    assert barras_para_linha_bancario(barras) == LINHA_BB
    assert analisar(barras, referencia=date(2008, 1, 1)).linha_digitavel == LINHA_BB


def test_detecta_digito_verificador_invalido():
    errada = LINHA_BB[:9] + str((int(LINHA_BB[9]) + 1) % 10) + LINHA_BB[10:]
    r = analisar(errada)
    assert not r.valido
    assert any("campo 1" in e for e in r.erros)


def test_correcao_de_um_digito():
    errada = LINHA_BB[:12] + str((int(LINHA_BB[12]) + 4) % 10) + LINHA_BB[13:]
    candidatos = candidatos_correcao(errada, date(2008, 1, 1), limite=20)
    assert LINHA_BB in [c.linha_digitavel for c in candidatos]
    assert all(c.valido and c.corrigido for c in candidatos)
    corrigido = tentar_corrigir(errada, date(2008, 1, 1))
    assert corrigido is None or corrigido.linha_digitavel == LINHA_BB


def test_correcao_de_dois_digitos_em_campos_diferentes():
    errada = list(LINHA_BB)
    errada[3] = str((int(errada[3]) + 5) % 10)   # campo 1
    errada[14] = str((int(errada[14]) + 3) % 10)  # campo 2
    candidatos = candidatos_correcao("".join(errada), date(2008, 1, 1), limite=50)
    assert LINHA_BB in [c.linha_digitavel for c in candidatos]


def test_correcao_prioriza_confusoes_tipicas_de_ocr():
    # 8 lido como 3 no campo 3: a correção 3→8 deve aparecer entre as primeiras
    pos = 23
    assert LINHA_BB[pos] == "8"
    errada = LINHA_BB[:pos] + "3" + LINHA_BB[pos + 1:]
    candidatos = candidatos_correcao(errada, date(2008, 1, 1), limite=50)
    linhas = [c.linha_digitavel for c in candidatos]
    assert LINHA_BB in linhas[:3]


def test_fator_de_vencimento_novo_ciclo():
    assert data_por_fator(9999, date(2025, 1, 1)) == date(2025, 2, 21)
    assert data_por_fator(1000, date(2026, 9, 14)) == date(2025, 2, 22)
    assert data_por_fator(1000, date(2001, 1, 1)) == date(2000, 7, 3)
    for d in (date(2024, 5, 10), date(2025, 2, 22), date(2027, 1, 31)):
        assert data_por_fator(fator_por_data(d), d) == d


def _barras_arrecadacao(identificador: str) -> str:
    sem_dv = "8" + "3" + identificador + "00000012345" + "0048" + "0" * 7 + "20261015" + "1234567890"
    assert len(sem_dv) == 43
    dv = _dv_arrecadacao(sem_dv, identificador)
    return sem_dv[:3] + str(dv) + sem_dv[3:]


def test_arrecadacao_modulo_10_e_11():
    for identificador in ("6", "8"):
        barras = _barras_arrecadacao(identificador)
        linha = barras_para_linha_arrecadacao(barras)
        r = analisar(linha, referencia=date(2026, 9, 1))
        assert r.valido, r.erros
        assert r.tipo == ARRECADACAO
        assert r.segmento == "Energia elétrica e gás"
        assert r.valor == Decimal("123.45")
        assert r.vencimento == date(2026, 10, 15) and r.vencimento_estimado
        assert analisar(barras).linha_digitavel == linha


def test_formatacao():
    assert formatar_linha(LINHA_BB) == "00190.50095 40144.816069 06809.350314 3 37370000000100"
    linha48 = barras_para_linha_arrecadacao(_barras_arrecadacao("6"))
    assert formatar_linha(linha48).count("-") == 4


def test_tamanho_invalido():
    assert analisar("123") is None

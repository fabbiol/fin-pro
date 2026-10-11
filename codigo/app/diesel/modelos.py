"""Abas do banco de dados do diesel (máquinas, compras e abastecimentos).

Mesma estrutura das outras partes do sistema: banco SQLite, planilha Excel gerada sozinha (``dados/diesel.xlsx``),
histórico de quem fez cada alteração e backup diário.
"""

from __future__ import annotations

from ..planilha import Coluna, DefinicaoAba

COR_MAQUINAS = "3F4A56"
COR_COMPRAS = "0E6B5C"
COR_ABASTECIMENTOS = "B45309"

TIPOS_MAQUINA = ("Caminhão", "Máquina", "Veículo", "Gerador", "Outro")
MEDIDORES = ("horas", "km", "")  # horímetro, hodômetro ou nenhum
STATUS_MAQUINA = ("Ativa", "Inativa")
STATUS_COMPRA = ("Confirmada", "Cancelada")
STATUS_ABASTECIMENTO = ("Confirmado", "Cancelado")
LITROS_POR_COMPRA = 1000.0  # compra semanal padrão (botão rápido do bot)
COMBUSTIVEIS = ("Diesel S10", "Diesel comum", "Gasolina", "Etanol", "Arla 32")
COMBUSTIVEL_PADRAO = "Diesel S10"  # lançamentos sem combustível (os antigos, ou quando o canhoto não diz)

LITROS = '#,##0.00 "L"'
MOEDA = '"R$" #,##0.00'

COLUNAS_MAQUINAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("nome", "Máquina", 30),
    Coluna("tipo", "Tipo", 12),
    Coluna("placa", "Placa / Prefixo", 16, "@"),
    Coluna("medidor", "Medidor (horas/km)", 16),
    Coluna("combustivel", "Combustível", 14),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 34),
    Coluna("data_lancamento", "Cadastrada em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Cadastrada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_COMPRAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data", "Data", 12, "dd/mm/yyyy"),
    Coluna("posto", "Posto", 30),
    Coluna("combustivel", "Combustível", 14),
    Coluna("litros", "Litros", 12, LITROS),
    Coluna("valor", "Valor (R$)", 15, MOEDA),
    Coluna("preco_litro", "Preço por Litro (R$)", 16, '"R$" #,##0.000'),
    Coluna("forma", "Forma de Pagamento", 16),
    Coluna("documento", "Nota / Cupom", 16, "@"),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Comprovante", 28),
    Coluna("arquivo_nome", "Nome do Comprovante", 30),
    Coluna("data_lancamento", "Lançada em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Lançada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_ABASTECIMENTOS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data", "Data", 12, "dd/mm/yyyy"),
    Coluna("hora", "Hora", 8, "@"),
    Coluna("maquina", "Máquina", 28),
    Coluna("combustivel", "Combustível", 14),
    Coluna("litros", "Litros", 12, LITROS),
    Coluna("preco_litro", "Preço por Litro (R$)", 16, '"R$" #,##0.000'),
    Coluna("valor", "Valor (R$)", 14, MOEDA),
    Coluna("medidor", "Horímetro / Km", 14, "#,##0.0"),
    Coluna("posto", "Posto", 24),
    Coluna("documento", "Pedido / Canhoto", 16, "@"),
    Coluna("pessoa", "Quem Abasteceu", 20),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Canhoto", 28),
    Coluna("arquivo_nome", "Nome do Canhoto", 30),
    Coluna("data_lancamento", "Lançado em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Lançado por", 20),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

_TEXTOS_COMUNS = frozenset({"observacoes", "arquivo", "arquivo_nome", "lancado_por"})

ABAS_DIESEL: dict[str, DefinicaoAba] = {
    "maquinas": DefinicaoAba(
        "maquinas", "Máquinas", tuple(COLUNAS_MAQUINAS),
        frozenset({"nome", "tipo", "placa", "medidor", "combustivel", "status", "observacoes"}),
        "nome", frozenset({"nome", "tipo", "placa", "medidor", "combustivel"}) | _TEXTOS_COMUNS, COR_MAQUINAS, " (Máquina)",
        STATUS_MAQUINA, "", "", "Inativa",
    ),
    "compras": DefinicaoAba(
        "compras", "Compras de Diesel", tuple(COLUNAS_COMPRAS),
        frozenset({"data", "posto", "combustivel", "litros", "valor", "preco_litro", "forma", "documento", "status",
                   "observacoes", "arquivo", "arquivo_nome"}),
        "posto", frozenset({"posto", "combustivel", "forma", "documento"}) | _TEXTOS_COMUNS, COR_COMPRAS, " (Compra de diesel)",
        STATUS_COMPRA, "data", "", "Cancelada",
    ),
    "abastecimentos": DefinicaoAba(
        "abastecimentos", "Abastecimentos", tuple(COLUNAS_ABASTECIMENTOS),
        frozenset({"data", "hora", "maquina", "combustivel", "litros", "preco_litro", "valor", "medidor", "posto",
                   "documento", "pessoa", "status", "observacoes", "arquivo", "arquivo_nome"}),
        "maquina", frozenset({"hora", "maquina", "combustivel", "posto", "documento", "pessoa"}) | _TEXTOS_COMUNS, COR_ABASTECIMENTOS,
        " (Abastecimento)", STATUS_ABASTECIMENTO, "data", "", "Cancelado",
    ),
}

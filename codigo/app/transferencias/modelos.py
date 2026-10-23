"""Aba do banco de dados das transferências de clientes (notas enviadas pela Operações).

Mesma estrutura das outras partes do sistema: banco SQLite próprio (``dados/transferencias.db``), planilha Excel gerada
sozinha (``dados/transferencias.xlsx``), histórico de cada alteração e backup diário.
"""

from __future__ import annotations

from ..planilha import Coluna, DefinicaoAba

COR_TRANSFERENCIAS = "155E75"

FORMAS = {"pix": "Pix", "transferencia": "TED/DOC"}  # o que a Operações manda -> o que a tela mostra
AGUARDANDO = "Aguardando pagamento"
PAGO = "Pago"  # para a baixa pelo extrato do banco (próximo passo)
STATUS_TRANSFERENCIA = (AGUARDANDO, PAGO)

COLUNAS_TRANSFERENCIAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("origem_id", "Nº na Operações", 14, "0"),
    Coluna("nota", "Nota", 12, "@"),
    Coluna("pedido", "Pedido", 12, "@"),
    Coluna("empresa", "Empresa", 30),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("material", "Material", 24),
    Coluna("emitida_em", "Emitida em", 19, "@"),
    Coluna("forma", "Forma", 14),
    Coluna("chave", "Chave de Acesso", 48, "@"),
    Coluna("status", "Situação", 22),
    Coluna("arquivo", "PDF da Nota", 28),
    Coluna("arquivo_nome", "Nome do PDF", 30),
    Coluna("data_lancamento", "Recebida em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Enviada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

ABAS_TRANSFERENCIAS: dict[str, DefinicaoAba] = {
    "transferencias": DefinicaoAba(
        "transferencias", "Transferências", tuple(COLUNAS_TRANSFERENCIAS),
        frozenset({"origem_id", "nota", "pedido", "empresa", "valor", "material", "emitida_em", "forma", "chave", "status",
                   "arquivo", "arquivo_nome"}),
        "empresa", frozenset({"nota", "pedido", "empresa", "material", "emitida_em", "forma", "chave", "arquivo",
                              "arquivo_nome", "lancado_por"}),
        COR_TRANSFERENCIAS, " (Transferência)", STATUS_TRANSFERENCIA, "", PAGO, "",
    ),
}

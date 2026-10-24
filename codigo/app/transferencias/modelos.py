"""Abas do banco de dados das transferências de clientes (notas enviadas pela Operações e os pagamentos ligados a elas).

Mesma estrutura das outras partes do sistema: banco SQLite próprio (``dados/transferencias.db``), planilha Excel gerada
sozinha (``dados/transferencias.xlsx``), histórico de cada alteração e backup diário.
"""

from __future__ import annotations

from ..planilha import Coluna, DefinicaoAba

COR_TRANSFERENCIAS = "155E75"

FORMAS = {"pix": "Pix", "transferencia": "TED/DOC"}  # o que a Operações manda -> o que a tela mostra
AGUARDANDO = "Aguardando pagamento"
PAGO = "Pago"  # quando alguém liga um comprovante à nota (e, no próximo passo, pela leitura do extrato do banco)
STATUS_TRANSFERENCIA = (AGUARDANDO, PAGO)
ATIVO, DESFEITO = "Ativo", "Desfeito"  # um pagamento desfeito fica guardado, com o comprovante, só para o histórico

COLUNAS_TRANSFERENCIAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("origem_id", "Nº na Operações", 14, "0"),
    Coluna("nota", "Nota", 12, "@"),
    Coluna("pedido", "Pedido", 12, "@"),
    Coluna("empresa", "Empresa", 30),
    Coluna("documento", "CNPJ/CPF", 18, "@"),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("material", "Material", 24),
    Coluna("emitida_em", "Emitida em", 19, "@"),
    Coluna("forma", "Forma", 14),
    Coluna("chave", "Chave de Acesso", 48, "@"),
    Coluna("status", "Situação", 22),
    Coluna("pagamento_id", "Nº do Pagamento", 14, "0"),
    Coluna("arquivo", "PDF da Nota", 28),
    Coluna("arquivo_nome", "Nome do PDF", 30),
    Coluna("data_lancamento", "Recebida em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Enviada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

# Pagamento ligado à mão: um comprovante (Pix ou TED) que cobre uma ou mais notas
COLUNAS_PAGAMENTOS: list[Coluna] = [
    Coluna("id", "Nº do Pagamento", 14, "0"),
    Coluna("notas", "Notas", 24, "@"),
    Coluna("valor", "Valor Pago (R$)", 15, '"R$" #,##0.00'),
    Coluna("data_pagamento", "Data do Pagamento", 16, "dd/mm/yyyy"),
    Coluna("pagador", "Pagador", 30),
    Coluna("documento_pagador", "CNPJ/CPF do Pagador", 18, "@"),
    Coluna("id_transacao", "ID da Transação", 36, "@"),
    Coluna("observacao", "Observação", 30),
    Coluna("status", "Situação", 12),
    Coluna("comprovante", "Comprovante", 28),
    Coluna("comprovante_nome", "Nome do Comprovante", 30),
    Coluna("data_lancamento", "Ligado em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Ligado por", 20),
    Coluna("desfeito_em", "Desfeito em", 19, "@"),
    Coluna("desfeito_por", "Desfeito por", 20),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

ABAS_TRANSFERENCIAS: dict[str, DefinicaoAba] = {
    "transferencias": DefinicaoAba(
        "transferencias", "Transferências", tuple(COLUNAS_TRANSFERENCIAS),
        frozenset({"origem_id", "nota", "pedido", "empresa", "documento", "valor", "material", "emitida_em", "forma",
                   "chave", "status", "pagamento_id", "arquivo", "arquivo_nome"}),
        "empresa", frozenset({"nota", "pedido", "empresa", "documento", "material", "emitida_em", "forma", "chave",
                              "arquivo", "arquivo_nome", "lancado_por"}),
        COR_TRANSFERENCIAS, " (Transferência)", STATUS_TRANSFERENCIA, "", PAGO, "",
    ),
    "pagamentos": DefinicaoAba(
        "pagamentos", "Pagamentos", tuple(COLUNAS_PAGAMENTOS),
        frozenset({"notas", "valor", "data_pagamento", "pagador", "documento_pagador", "id_transacao", "observacao",
                   "status", "comprovante", "comprovante_nome", "desfeito_em", "desfeito_por"}),
        "pagador", frozenset({"notas", "pagador", "documento_pagador", "id_transacao", "observacao", "comprovante",
                              "comprovante_nome", "lancado_por", "desfeito_em", "desfeito_por"}),
        COR_TRANSFERENCIAS, " (Pagamento de transferência)", (ATIVO, DESFEITO), "data_pagamento", ATIVO, DESFEITO,
    ),
}

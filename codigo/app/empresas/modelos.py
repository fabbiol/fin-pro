"""Abas do banco de dados do módulo Empresas (empresas, notas fiscais, cheques e recebimentos).

Usa a mesma estrutura das abas de boletos e Pix (``app/planilha.py``), então tudo o que já existe vale aqui:
banco SQLite, planilha Excel gerada automaticamente (``dados/fechamentos.xlsx``), histórico de quem fez cada
alteração, backup diário e edição pela própria planilha.
"""

from __future__ import annotations

from ..planilha import Coluna, DefinicaoAba

COR_EMPRESAS = "1F5FA8"
COR_NOTAS = "0F3D3E"
COR_CHEQUES = "6B3FA0"
COR_RECEBIMENTOS = "1B7F4B"

DIA_FECHAMENTO_PADRAO = 20

STATUS_EMPRESA = ("Ativa", "Inativa")
STATUS_NOTA = ("Em aberto", "Em cheque", "Parcial", "Recebido", "Cancelado")
STATUS_CHEQUE = ("Em carteira", "Depositado", "Compensado", "Devolvido", "Cancelado")
STATUS_RECEBIMENTO = ("Confirmado", "Cancelado")
FORMAS_RECEBIMENTO = ("Pix", "TED", "Depósito", "Cheque", "Dinheiro", "Outro")
UNIDADES = ("M³", "TON", "UN", "KG", "L", "H", "SC", "PC")

COLUNAS_EMPRESAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("nome", "Empresa", 30),
    Coluna("razao_social", "Razão Social", 40),
    Coluna("cnpj", "CNPJ", 20, "@"),
    Coluna("apelidos", "Outros nomes (para o robô reconhecer)", 40),
    Coluna("dia_fechamento", "Dia do Fechamento", 17, "0"),
    Coluna("contato", "Contato", 24),
    Coluna("telefone", "Telefone", 18, "@"),
    Coluna("email", "E-mail", 28),
    Coluna("chat_telegram", "Chat do Telegram", 18, "@"),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 34),
    Coluna("data_lancamento", "Cadastrada em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Cadastrada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_NOTAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data", "Data", 12, "dd/mm/yyyy"),
    Coluna("empresa", "Empresa", 28),
    Coluna("material", "Material", 28),
    Coluna("unidade", "Unidade", 10),
    Coluna("quantidade", "Quantidade", 12, "#,##0.###"),
    Coluna("valor_unitario", "Valor Unitário (R$)", 17, '"R$" #,##0.00'),
    Coluna("valor_total", "Valor Total (R$)", 16, '"R$" #,##0.00'),
    Coluna("numero_nf", "Nota Fiscal", 13, "@"),
    Coluna("pedido", "Nº do Pedido", 14, "@"),
    Coluna("competencia", "Fechamento", 12, "@"),
    Coluna("status", "Situação", 12),
    Coluna("valor_recebido", "Valor Recebido (R$)", 17, '"R$" #,##0.00'),
    Coluna("data_recebimento", "Recebido em", 13, "dd/mm/yyyy"),
    Coluna("cheque_id", "Cheque (ID)", 11, "0"),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Arquivo", 28),
    Coluna("arquivo_nome", "Nome do Arquivo Original", 30),
    Coluna("data_lancamento", "Lançada em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Lançada por", 20),
    Coluna("atualizado_em", "Atualizada em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_CHEQUES: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("empresa", "Empresa", 28),
    Coluna("numero", "Nº do Cheque", 14, "@"),
    Coluna("vencimento", "Bom para", 12, "dd/mm/yyyy"),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("banco", "Banco", 24),
    Coluna("agencia", "Agência", 11, "@"),
    Coluna("coop", "Cooperativa", 13, "@"),
    Coluna("conta", "Conta", 16, "@"),
    Coluna("emitente", "Emitente", 30),
    Coluna("pedidos", "Pedidos", 22, "@"),
    Coluna("notas", "Notas Fiscais", 22, "@"),
    Coluna("status", "Situação", 13),
    Coluna("data_deposito", "Depositado em", 14, "dd/mm/yyyy"),
    Coluna("cmc7", "CMC7 (linha do cheque)", 34, "@"),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Arquivo", 28),
    Coluna("arquivo_nome", "Nome do Arquivo Original", 30),
    Coluna("data_lancamento", "Lançado em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Lançado por", 20),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_RECEBIMENTOS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data", "Data", 12, "dd/mm/yyyy"),
    Coluna("hora", "Hora", 9, "@"),
    Coluna("empresa", "Empresa", 28),
    Coluna("forma", "Forma", 12),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("pagador", "Pagador", 32),
    Coluna("id_transacao", "ID da Transação", 34, "@"),
    Coluna("notas", "Notas Fiscais", 24, "@"),
    Coluna("pedidos", "Pedidos", 22, "@"),
    Coluna("cheque_id", "Cheque (ID)", 11, "0"),
    Coluna("aplicacoes", "Baixas (nota: valor)", 40),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Comprovante", 28),
    Coluna("arquivo_nome", "Nome do Comprovante", 30),
    Coluna("data_lancamento", "Registrado em", 19, "dd/mm/yyyy hh:mm"),
    Coluna("lancado_por", "Registrado por", 20),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

_TEXTOS_COMUNS = frozenset({"observacoes", "arquivo", "arquivo_nome", "lancado_por"})

ABAS_EMPRESAS: dict[str, DefinicaoAba] = {
    "empresas": DefinicaoAba(
        "empresas", "Empresas", tuple(COLUNAS_EMPRESAS),
        frozenset({"nome", "razao_social", "cnpj", "apelidos", "dia_fechamento", "contato", "telefone", "email",
                   "chat_telegram", "status", "observacoes"}),
        "nome", frozenset({"nome", "razao_social", "cnpj", "apelidos", "contato", "telefone", "email", "chat_telegram"})
        | _TEXTOS_COMUNS, COR_EMPRESAS, " (Empresa)", STATUS_EMPRESA, "", "", "Inativa",
    ),
    "notas": DefinicaoAba(
        "notas", "Notas Fiscais", tuple(COLUNAS_NOTAS),
        frozenset({"data", "empresa", "material", "unidade", "quantidade", "valor_unitario", "valor_total", "numero_nf",
                   "pedido", "competencia", "status", "valor_recebido", "data_recebimento", "cheque_id", "observacoes",
                   "arquivo", "arquivo_nome"}),
        "empresa", frozenset({"empresa", "material", "unidade", "numero_nf", "pedido", "competencia"}) | _TEXTOS_COMUNS,
        COR_NOTAS, " (NF)", STATUS_NOTA, "data", "Recebido", "Cancelado",
    ),
    "cheques": DefinicaoAba(
        "cheques", "Cheques", tuple(COLUNAS_CHEQUES),
        frozenset({"empresa", "numero", "vencimento", "valor", "banco", "agencia", "coop", "conta", "emitente",
                   "pedidos", "notas", "status", "data_deposito", "cmc7", "observacoes", "arquivo", "arquivo_nome"}),
        "empresa", frozenset({"empresa", "numero", "banco", "agencia", "coop", "conta", "emitente", "pedidos", "notas",
                              "cmc7"}) | _TEXTOS_COMUNS,
        COR_CHEQUES, " (Cheque)", STATUS_CHEQUE, "vencimento", "Compensado", "Cancelado",
    ),
    "recebimentos": DefinicaoAba(
        "recebimentos", "Recebimentos", tuple(COLUNAS_RECEBIMENTOS),
        frozenset({"data", "hora", "empresa", "forma", "valor", "pagador", "id_transacao", "notas", "pedidos",
                   "cheque_id", "aplicacoes", "status", "observacoes", "arquivo", "arquivo_nome"}),
        "empresa", frozenset({"empresa", "forma", "pagador", "id_transacao", "notas", "pedidos", "hora", "aplicacoes"})
        | _TEXTOS_COMUNS, COR_RECEBIMENTOS, " (Recebimento)", STATUS_RECEBIMENTO, "data", "Confirmado", "Cancelado",
    ),
}

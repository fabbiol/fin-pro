# Anexo A2 — Modelo de dados (todas as tabelas e campos)

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Todas as tabelas seguem o mesmo mecanismo (`app/banco.py`): cada registro é guardado no SQLite como JSON, com `id` sequencial por aba, e a planilha Excel é gerada a partir dessas definições (ordem das colunas, título, largura e formato). *Editável* = o campo pode ser alterado depois de lançado (campo fora da lista é ignorado na gravação). *Texto* = vazio vira `""` em vez de nulo.

## boletos.db / boletos.xlsx

### Aba `boletos` — planilha "Boletos"

- Situações válidas: `Pendente`, `Pago`, `Cancelado` (padrão `Pendente`; verde = `Pago`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `vencimento` · nome no histórico: `beneficiario`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data_lancamento` | Data de Lançamento | dd/mm/yyyy hh:mm | 19 |  |  |
| `linha_digitavel` | Linha Digitável | @ | 58 | sim |  |
| `codigo_barras` | Código de Barras | @ | 48 | sim |  |
| `beneficiario` | Beneficiário |  | 42 | sim | sim |
| `documento_beneficiario` | CPF/CNPJ Beneficiário | @ | 21 | sim |  |
| `numero_documento` | Nº do Documento | @ | 18 | sim | sim |
| `vencimento` | Vencimento | dd/mm/yyyy | 13 | sim |  |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `emissor` | Banco / Segmento |  | 26 | sim |  |
| `tipo` | Tipo |  | 13 | sim |  |
| `status` | Status |  | 12 | sim |  |
| `data_pagamento` | Data de Pagamento | dd/mm/yyyy | 17 | sim |  |
| `valor_pago` | Valor Pago (R$) | "R$" #,##0.00 | 15 | sim |  |
| `juros_multa` | Juros/Multa (R$) | "R$" #,##0.00 | 15 | sim |  |
| `desconto` | Desconto (R$) | "R$" #,##0.00 | 14 | sim |  |
| `observacoes` | Observações |  | 34 | sim | sim |
| `centro_custo` | Centro de Custo |  | 26 | sim | sim |
| `arquivo` | Arquivo |  | 30 | sim |  |
| `arquivo_nome` | Nome do Arquivo Original |  | 32 | sim |  |
| `lancado_por` | Lançado por |  | 20 |  | sim |
| `pago_por` | Pago por |  | 20 |  | sim |
| `comprovante` | Comprovante |  | 30 | sim | sim |
| `comprovante_nome` | Nome do Comprovante |  | 30 | sim | sim |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `pix` — planilha "Pix"

- Situações válidas: `Pendente`, `Pago`, `Cancelado` (padrão `Pendente`; verde = `Pago`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `vencimento` · nome no histórico: `recebedor`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data_lancamento` | Data de Lançamento | dd/mm/yyyy hh:mm | 19 |  |  |
| `recebedor` | Recebedor |  | 38 | sim | sim |
| `tipo_chave` | Tipo da Chave |  | 14 | sim |  |
| `chave` | Chave Pix | @ | 38 | sim |  |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `vencimento` | Data Prevista | dd/mm/yyyy | 14 | sim |  |
| `centro_custo` | Centro de Custo |  | 26 | sim | sim |
| `descricao` | Descrição |  | 36 | sim | sim |
| `status` | Status |  | 12 | sim |  |
| `data_pagamento` | Data de Pagamento | dd/mm/yyyy | 17 | sim |  |
| `valor_pago` | Valor Pago (R$) | "R$" #,##0.00 | 15 | sim |  |
| `juros_multa` | Juros/Multa (R$) | "R$" #,##0.00 | 15 | sim |  |
| `desconto` | Desconto (R$) | "R$" #,##0.00 | 14 | sim |  |
| `txid` | Identificador (TXID) | @ | 24 | sim | sim |
| `copia_e_cola` | Pix Copia e Cola | @ | 40 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Arquivo |  | 28 | sim |  |
| `arquivo_nome` | Nome do Arquivo Original |  | 30 | sim |  |
| `lancado_por` | Lançado por |  | 20 |  | sim |
| `pago_por` | Pago por |  | 20 |  | sim |
| `comprovante` | Comprovante |  | 28 | sim | sim |
| `comprovante_nome` | Nome do Comprovante |  | 30 | sim | sim |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `caixa` — planilha "Caixa"

- Situações válidas: `Confirmado`, `Cancelado` (padrão `Confirmado`; verde = `—`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `data` · nome no histórico: `descricao`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data` | Data | dd/mm/yyyy | 12 | sim |  |
| `hora` | Hora | @ | 8 | sim | sim |
| `movimento` | Entrada/Saída |  | 13 | sim | sim |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `descricao` | O que foi pedido / comprado |  | 40 | sim | sim |
| `local` | Onde foi gasto |  | 30 | sim | sim |
| `centro_custo` | Centro de Custo |  | 26 | sim | sim |
| `pessoa` | Quem |  | 20 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Comprovante |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Comprovante |  | 30 | sim | sim |
| `lancado_por` | Lançado por |  | 20 |  | sim |
| `data_lancamento` | Data de Lançamento | dd/mm/yyyy hh:mm | 19 |  |  |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

## empresas.db / fechamentos.xlsx

### Aba `empresas` — planilha "Empresas"

- Situações válidas: `Ativa`, `Inativa` (padrão `Ativa`; verde = `—`; riscado = `Inativa`)
- Data de referência (atraso e histórico): `` · nome no histórico: `nome`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `nome` | Empresa |  | 30 | sim | sim |
| `razao_social` | Razão Social |  | 40 | sim | sim |
| `cnpj` | CNPJ | @ | 20 | sim | sim |
| `apelidos` | Outros nomes (para o robô reconhecer) |  | 40 | sim | sim |
| `dia_fechamento` | Dia do Fechamento | 0 | 17 | sim |  |
| `contato` | Contato |  | 24 | sim | sim |
| `telefone` | Telefone | @ | 18 | sim | sim |
| `email` | E-mail |  | 28 | sim | sim |
| `chat_telegram` | Chat do Telegram | @ | 18 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 34 | sim | sim |
| `data_lancamento` | Cadastrada em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Cadastrada por |  | 20 |  | sim |
| `atualizado_em` | Atualizada em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `notas` — planilha "Notas Fiscais"

- Situações válidas: `Em aberto`, `Em cheque`, `Parcial`, `Recebido`, `Cancelado` (padrão `Em aberto`; verde = `Recebido`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `data` · nome no histórico: `empresa`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data` | Data | dd/mm/yyyy | 12 | sim |  |
| `empresa` | Empresa |  | 28 | sim | sim |
| `material` | Material |  | 28 | sim | sim |
| `unidade` | Unidade |  | 10 | sim | sim |
| `quantidade` | Quantidade | #,##0.### | 12 | sim |  |
| `valor_unitario` | Valor Unitário (R$) | "R$" #,##0.00 | 17 | sim |  |
| `valor_total` | Valor Total (R$) | "R$" #,##0.00 | 16 | sim |  |
| `numero_nf` | Nota Fiscal | @ | 13 | sim | sim |
| `pedido` | Nº do Pedido | @ | 14 | sim | sim |
| `competencia` | Fechamento | @ | 12 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `valor_recebido` | Valor Recebido (R$) | "R$" #,##0.00 | 17 | sim |  |
| `data_recebimento` | Recebido em | dd/mm/yyyy | 13 | sim |  |
| `cheque_id` | Cheque (ID) | 0 | 11 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Arquivo |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Arquivo Original |  | 30 | sim | sim |
| `data_lancamento` | Lançada em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Lançada por |  | 20 |  | sim |
| `atualizado_em` | Atualizada em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `cheques` — planilha "Cheques"

- Situações válidas: `Em carteira`, `Depositado`, `Compensado`, `Devolvido`, `Cancelado` (padrão `Em carteira`; verde = `Compensado`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `vencimento` · nome no histórico: `empresa`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `empresa` | Empresa |  | 28 | sim | sim |
| `numero` | Nº do Cheque | @ | 14 | sim | sim |
| `vencimento` | Bom para | dd/mm/yyyy | 12 | sim |  |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `banco` | Banco |  | 24 | sim | sim |
| `agencia` | Agência | @ | 11 | sim | sim |
| `coop` | Cooperativa | @ | 13 | sim | sim |
| `conta` | Conta | @ | 16 | sim | sim |
| `emitente` | Emitente |  | 30 | sim | sim |
| `pedidos` | Pedidos | @ | 22 | sim | sim |
| `notas` | Notas Fiscais | @ | 22 | sim | sim |
| `status` | Situação |  | 13 | sim |  |
| `data_deposito` | Depositado em | dd/mm/yyyy | 14 | sim |  |
| `cmc7` | CMC7 (linha do cheque) | @ | 34 | sim | sim |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Arquivo |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Arquivo Original |  | 30 | sim | sim |
| `data_lancamento` | Lançado em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Lançado por |  | 20 |  | sim |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `recebimentos` — planilha "Recebimentos"

- Situações válidas: `Confirmado`, `Cancelado` (padrão `Confirmado`; verde = `Confirmado`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `data` · nome no histórico: `empresa`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data` | Data | dd/mm/yyyy | 12 | sim |  |
| `hora` | Hora | @ | 9 | sim | sim |
| `empresa` | Empresa |  | 28 | sim | sim |
| `forma` | Forma |  | 12 | sim | sim |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `pagador` | Pagador |  | 32 | sim | sim |
| `id_transacao` | ID da Transação | @ | 34 | sim | sim |
| `notas` | Notas Fiscais | @ | 24 | sim | sim |
| `pedidos` | Pedidos | @ | 22 | sim | sim |
| `cheque_id` | Cheque (ID) | 0 | 11 | sim |  |
| `aplicacoes` | Baixas (nota: valor) |  | 40 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Comprovante |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Comprovante |  | 30 | sim | sim |
| `data_lancamento` | Registrado em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Registrado por |  | 20 |  | sim |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

## diesel.db / diesel.xlsx

### Aba `maquinas` — planilha "Máquinas"

- Situações válidas: `Ativa`, `Inativa` (padrão `Ativa`; verde = `—`; riscado = `Inativa`)
- Data de referência (atraso e histórico): `` · nome no histórico: `nome`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `nome` | Máquina |  | 30 | sim | sim |
| `tipo` | Tipo |  | 12 | sim | sim |
| `placa` | Placa / Prefixo | @ | 16 | sim | sim |
| `medidor` | Medidor (horas/km) |  | 16 | sim | sim |
| `combustivel` | Combustível |  | 14 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 34 | sim | sim |
| `data_lancamento` | Cadastrada em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Cadastrada por |  | 20 |  | sim |
| `atualizado_em` | Atualizada em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `compras` — planilha "Compras de Diesel"

- Situações válidas: `Confirmada`, `Cancelada` (padrão `Confirmada`; verde = `—`; riscado = `Cancelada`)
- Data de referência (atraso e histórico): `data` · nome no histórico: `posto`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data` | Data | dd/mm/yyyy | 12 | sim |  |
| `posto` | Posto |  | 30 | sim | sim |
| `combustivel` | Combustível |  | 14 | sim | sim |
| `litros` | Litros | #,##0.00 "L" | 12 | sim |  |
| `valor` | Valor (R$) | "R$" #,##0.00 | 15 | sim |  |
| `preco_litro` | Preço por Litro (R$) | "R$" #,##0.000 | 16 | sim |  |
| `forma` | Forma de Pagamento |  | 16 | sim | sim |
| `documento` | Nota / Cupom | @ | 16 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Comprovante |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Comprovante |  | 30 | sim | sim |
| `data_lancamento` | Lançada em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Lançada por |  | 20 |  | sim |
| `atualizado_em` | Atualizada em | dd/mm/yyyy hh:mm | 19 |  |  |

### Aba `abastecimentos` — planilha "Abastecimentos"

- Situações válidas: `Confirmado`, `Cancelado` (padrão `Confirmado`; verde = `—`; riscado = `Cancelado`)
- Data de referência (atraso e histórico): `data` · nome no histórico: `maquina`

| Campo | Título na planilha | Formato | Largura | Editável | Texto |
|---|---|---|---|---|---|
| `id` | ID | 0 | 7 |  |  |
| `data` | Data | dd/mm/yyyy | 12 | sim |  |
| `hora` | Hora | @ | 8 | sim | sim |
| `maquina` | Máquina |  | 28 | sim | sim |
| `combustivel` | Combustível |  | 14 | sim | sim |
| `litros` | Litros | #,##0.00 "L" | 12 | sim |  |
| `preco_litro` | Preço por Litro (R$) | "R$" #,##0.000 | 16 | sim |  |
| `valor` | Valor (R$) | "R$" #,##0.00 | 14 | sim |  |
| `medidor` | Horímetro / Km | #,##0.0 | 14 | sim |  |
| `posto` | Posto |  | 24 | sim | sim |
| `documento` | Pedido / Canhoto | @ | 16 | sim | sim |
| `pessoa` | Quem Abasteceu |  | 20 | sim | sim |
| `status` | Situação |  | 12 | sim |  |
| `observacoes` | Observações |  | 30 | sim | sim |
| `arquivo` | Canhoto |  | 28 | sim | sim |
| `arquivo_nome` | Nome do Canhoto |  | 30 | sim | sim |
| `data_lancamento` | Lançado em | dd/mm/yyyy hh:mm | 19 |  |  |
| `lancado_por` | Lançado por |  | 20 |  | sim |
| `atualizado_em` | Atualizado em | dd/mm/yyyy hh:mm | 19 |  |  |

- `planilha.STATUS_VALIDOS` = `Cancelado`, `Pago`, `Pendente`
- `planilha.CAMPOS_DATA` = `data`, `data_deposito`, `data_fechamento`, `data_pagamento`, `data_recebimento`, `vencimento`
- `planilha.CAMPOS_DATA_HORA` = `atualizado_em`, `data_hora`, `data_lancamento`
- `planilha.CAMPOS_NUMERO` = `litros`, `medidor`, `preco_litro`, `quantidade`
- `planilha.CAMPOS_MOEDA` = `desconto`, `juros_multa`, `valor`, `valor_pago`, `valor_recebido`, `valor_total`, `valor_unitario`
- `planilha.CAMPOS_COMPROVANTE` = `comprovante`, `comprovante_nome`
- `planilha.CAMPOS_PAGAMENTO` = `desconto`, `juros_multa`, `valor_pago`
- `empresas.modelos.COR_EMPRESAS` = `1F5FA8`
- `empresas.modelos.COR_NOTAS` = `0F3D3E`
- `empresas.modelos.COR_CHEQUES` = `6B3FA0`
- `empresas.modelos.COR_RECEBIMENTOS` = `1B7F4B`
- `empresas.modelos.DIA_FECHAMENTO_PADRAO` = `20`
- `empresas.modelos.STATUS_EMPRESA` = `['Ativa', 'Inativa']`
- `empresas.modelos.STATUS_NOTA` = `['Em aberto', 'Em cheque', 'Parcial', 'Recebido', 'Cancelado']`
- `empresas.modelos.STATUS_CHEQUE` = `['Em carteira', 'Depositado', 'Compensado', 'Devolvido', 'Cancelado']`
- `empresas.modelos.STATUS_RECEBIMENTO` = `['Confirmado', 'Cancelado']`
- `empresas.modelos.FORMAS_RECEBIMENTO` = `['Pix', 'TED', 'Depósito', 'Cheque', 'Dinheiro', 'Outro']`
- `empresas.modelos.UNIDADES` = `['M³', 'TON', 'UN', 'KG', 'L', 'H', 'SC', 'PC']`
- `empresas.modelos.COLUNAS_EMPRESAS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='nome', titulo='Empresa', largura=30, formato=None), Coluna(chave='razao_social', titulo='Razão Social', largura=40, formato=None), Coluna(chave='cnpj', titulo='CNPJ', largura=20, formato='@'), Coluna(chave='apelidos', titulo='Outros nomes (para o robô reconhecer)', largura=40, formato=None), Coluna(chave='dia_fechamento', titulo='Dia do Fechamento', largura=17, formato='0'), Coluna(chave='contato', titulo='Contato', largura=24, formato=None), Coluna(chave='telefone', titulo='Telefone', largura=18, formato='@'), Coluna(chave='email', titulo='E-mail', largura=28, formato=None), Coluna(chave='chat_telegram', titulo='Chat do Telegram', largura=18, formato='@'), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='observacoes', titulo='Observações', largura=34, formato=None), Coluna(chave='data_lancamento', titulo='Cadastrada em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Cadastrada por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizada em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `empresas.modelos.COLUNAS_NOTAS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='data', titulo='Data', largura=12, formato='dd/mm/yyyy'), Coluna(chave='empresa', titulo='Empresa', largura=28, formato=None), Coluna(chave='material', titulo='Material', largura=28, formato=None), Coluna(chave='unidade', titulo='Unidade', largura=10, formato=None), Coluna(chave='quantidade', titulo='Quantidade', largura=12, formato='#,##0.###'), Coluna(chave='valor_unitario', titulo='Valor Unitário (R$)', largura=17, formato='"R$" #,##0.00'), Coluna(chave='valor_total', titulo='Valor Total (R$)', largura=16, formato='"R$" #,##0.00'), Coluna(chave='numero_nf', titulo='Nota Fiscal', largura=13, formato='@'), Coluna(chave='pedido', titulo='Nº do Pedido', largura=14, formato='@'), Coluna(chave='competencia', titulo='Fechamento', largura=12, formato='@'), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='valor_recebido', titulo='Valor Recebido (R$)', largura=17, formato='"R$" #,##0.00'), Coluna(chave='data_recebimento', titulo='Recebido em', largura=13, formato='dd/mm/yyyy'), Coluna(chave='cheque_id', titulo='Cheque (ID)', largura=11, formato='0'), Coluna(chave='observacoes', titulo='Observações', largura=30, formato=None), Coluna(chave='arquivo', titulo='Arquivo', largura=28, formato=None), Coluna(chave='arquivo_nome', titulo='Nome do Arquivo Original', largura=30, formato=None), Coluna(chave='data_lancamento', titulo='Lançada em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Lançada por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizada em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `empresas.modelos.COLUNAS_CHEQUES` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='empresa', titulo='Empresa', largura=28, formato=None), Coluna(chave='numero', titulo='Nº do Cheque', largura=14, formato='@'), Coluna(chave='vencimento', titulo='Bom para', largura=12, formato='dd/mm/yyyy'), Coluna(chave='valor', titulo='Valor (R$)', largura=15, formato='"R$" #,##0.00'), Coluna(chave='banco', titulo='Banco', largura=24, formato=None), Coluna(chave='agencia', titulo='Agência', largura=11, formato='@'), Coluna(chave='coop', titulo='Cooperativa', largura=13, formato='@'), Coluna(chave='conta', titulo='Conta', largura=16, formato='@'), Coluna(chave='emitente', titulo='Emitente', largura=30, formato=None), Coluna(chave='pedidos', titulo='Pedidos', largura=22, formato='@'), Coluna(chave='notas', titulo='Notas Fiscais', largura=22, formato='@'), Coluna(chave='status', titulo='Situação', largura=13, formato=None), Coluna(chave='data_deposito', titulo='Depositado em', largura=14, formato='dd/mm/yyyy'), Coluna(chave='cmc7', titulo='CMC7 (linha do cheque)', largura=34, formato='@'), Coluna(chave='observacoes', titulo='Observações', largura=30, formato=None), Coluna(chave='arquivo', titulo='Arquivo', largura=28, formato=None), Coluna(chave='arquivo_nome', titulo='Nome do Arquivo Original', largura=30, formato=None), Coluna(chave='data_lancamento', titulo='Lançado em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Lançado por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizado em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `empresas.modelos.COLUNAS_RECEBIMENTOS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='data', titulo='Data', largura=12, formato='dd/mm/yyyy'), Coluna(chave='hora', titulo='Hora', largura=9, formato='@'), Coluna(chave='empresa', titulo='Empresa', largura=28, formato=None), Coluna(chave='forma', titulo='Forma', largura=12, formato=None), Coluna(chave='valor', titulo='Valor (R$)', largura=15, formato='"R$" #,##0.00'), Coluna(chave='pagador', titulo='Pagador', largura=32, formato=None), Coluna(chave='id_transacao', titulo='ID da Transação', largura=34, formato='@'), Coluna(chave='notas', titulo='Notas Fiscais', largura=24, formato='@'), Coluna(chave='pedidos', titulo='Pedidos', largura=22, formato='@'), Coluna(chave='cheque_id', titulo='Cheque (ID)', largura=11, formato='0'), Coluna(chave='aplicacoes', titulo='Baixas (nota: valor)', largura=40, formato=None), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='observacoes', titulo='Observações', largura=30, formato=None), Coluna(chave='arquivo', titulo='Comprovante', largura=28, formato=None), Coluna(chave='arquivo_nome', titulo='Nome do Comprovante', largura=30, formato=None), Coluna(chave='data_lancamento', titulo='Registrado em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Registrado por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizado em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `empresas.modelos._TEXTOS_COMUNS` = `['arquivo', 'arquivo_nome', 'lancado_por', 'observacoes']`
- `diesel.modelos.COR_MAQUINAS` = `3F4A56`
- `diesel.modelos.COR_COMPRAS` = `0E6B5C`
- `diesel.modelos.COR_ABASTECIMENTOS` = `B45309`
- `diesel.modelos.TIPOS_MAQUINA` = `['Caminhão', 'Máquina', 'Veículo', 'Gerador', 'Outro']`
- `diesel.modelos.MEDIDORES` = `['horas', 'km', '']`
- `diesel.modelos.STATUS_MAQUINA` = `['Ativa', 'Inativa']`
- `diesel.modelos.STATUS_COMPRA` = `['Confirmada', 'Cancelada']`
- `diesel.modelos.STATUS_ABASTECIMENTO` = `['Confirmado', 'Cancelado']`
- `diesel.modelos.LITROS_POR_COMPRA` = `1000.0`
- `diesel.modelos.COMBUSTIVEIS` = `['Diesel S10', 'Diesel comum', 'Gasolina', 'Etanol', 'Arla 32']`
- `diesel.modelos.COMBUSTIVEL_PADRAO` = `Diesel S10`
- `diesel.modelos.LITROS` = `#,##0.00 "L"`
- `diesel.modelos.MOEDA` = `"R$" #,##0.00`
- `diesel.modelos.COLUNAS_MAQUINAS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='nome', titulo='Máquina', largura=30, formato=None), Coluna(chave='tipo', titulo='Tipo', largura=12, formato=None), Coluna(chave='placa', titulo='Placa / Prefixo', largura=16, formato='@'), Coluna(chave='medidor', titulo='Medidor (horas/km)', largura=16, formato=None), Coluna(chave='combustivel', titulo='Combustível', largura=14, formato=None), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='observacoes', titulo='Observações', largura=34, formato=None), Coluna(chave='data_lancamento', titulo='Cadastrada em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Cadastrada por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizada em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `diesel.modelos.COLUNAS_COMPRAS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='data', titulo='Data', largura=12, formato='dd/mm/yyyy'), Coluna(chave='posto', titulo='Posto', largura=30, formato=None), Coluna(chave='combustivel', titulo='Combustível', largura=14, formato=None), Coluna(chave='litros', titulo='Litros', largura=12, formato='#,##0.00 "L"'), Coluna(chave='valor', titulo='Valor (R$)', largura=15, formato='"R$" #,##0.00'), Coluna(chave='preco_litro', titulo='Preço por Litro (R$)', largura=16, formato='"R$" #,##0.000'), Coluna(chave='forma', titulo='Forma de Pagamento', largura=16, formato=None), Coluna(chave='documento', titulo='Nota / Cupom', largura=16, formato='@'), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='observacoes', titulo='Observações', largura=30, formato=None), Coluna(chave='arquivo', titulo='Comprovante', largura=28, formato=None), Coluna(chave='arquivo_nome', titulo='Nome do Comprovante', largura=30, formato=None), Coluna(chave='data_lancamento', titulo='Lançada em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Lançada por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizada em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `diesel.modelos.COLUNAS_ABASTECIMENTOS` = `[Coluna(chave='id', titulo='ID', largura=7, formato='0'), Coluna(chave='data', titulo='Data', largura=12, formato='dd/mm/yyyy'), Coluna(chave='hora', titulo='Hora', largura=8, formato='@'), Coluna(chave='maquina', titulo='Máquina', largura=28, formato=None), Coluna(chave='combustivel', titulo='Combustível', largura=14, formato=None), Coluna(chave='litros', titulo='Litros', largura=12, formato='#,##0.00 "L"'), Coluna(chave='preco_litro', titulo='Preço por Litro (R$)', largura=16, formato='"R$" #,##0.000'), Coluna(chave='valor', titulo='Valor (R$)', largura=14, formato='"R$" #,##0.00'), Coluna(chave='medidor', titulo='Horímetro / Km', largura=14, formato='#,##0.0'), Coluna(chave='posto', titulo='Posto', largura=24, formato=None), Coluna(chave='documento', titulo='Pedido / Canhoto', largura=16, formato='@'), Coluna(chave='pessoa', titulo='Quem Abasteceu', largura=20, formato=None), Coluna(chave='status', titulo='Situação', largura=12, formato=None), Coluna(chave='observacoes', titulo='Observações', largura=30, formato=None), Coluna(chave='arquivo', titulo='Canhoto', largura=28, formato=None), Coluna(chave='arquivo_nome', titulo='Nome do Canhoto', largura=30, formato=None), Coluna(chave='data_lancamento', titulo='Lançado em', largura=19, formato='dd/mm/yyyy hh:mm'), Coluna(chave='lancado_por', titulo='Lançado por', largura=20, formato=None), Coluna(chave='atualizado_em', titulo='Atualizado em', largura=19, formato='dd/mm/yyyy hh:mm')]`
- `diesel.modelos._TEXTOS_COMUNS` = `['arquivo', 'arquivo_nome', 'lancado_por', 'observacoes']`

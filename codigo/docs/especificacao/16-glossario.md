# 16 — Glossário (termos do negócio e do sistema)

| Termo | Significado no Fin Pro |
|---|---|
| **Abastecimento** | Uma retirada de combustível para uma máquina (uma linha do canhoto). Desconta do saldo do diesel o valor litros × preço |
| **Agendamento** | Comprovante de um pagamento marcado para o futuro; **não** dá baixa |
| **Arrecadação (boleto de)** | Conta de consumo, tributo ou convênio: linha de 48 dígitos começando com 8, quatro blocos de 11 + DV |
| **Baixa** | Marcar um lançamento como pago (contas a pagar) ou uma nota como recebida (empresas) |
| **Bancário (boleto)** | Boleto de cobrança: linha digitável de 47 dígitos, código de barras de 44 |
| **Beneficiário** | Quem recebe o pagamento do boleto (fornecedor). Em guias de tributo, o órgão arrecadador |
| **Bom para** | Data escrita à mão no cheque pré-datado: a partir dela o cheque pode ser depositado |
| **BR Code / Pix Copia e Cola** | Texto padrão EMV do Banco Central que representa uma cobrança Pix (começa com `000201`, termina com CRC16) |
| **Canhoto** | Pedido/comprovante do posto entregue a cada retirada de combustível; pode ter várias linhas |
| **Carnê** | PDF com vários boletos (um por página ou vários na página) |
| **Centro de custo** | Onde o dinheiro foi gasto (obra, setor, veículo…); base da análise de gastos |
| **Cheque em carteira** | Cheque pré-datado recebido e ainda não depositado |
| **CMC-7** | Linha de números magnéticos no rodapé do cheque: banco, agência, compensação, número do cheque e conta |
| **Código de barras (ITF)** | Barras do boleto, 44 dígitos no padrão Intercalado 2 de 5 |
| **Competência** | O fechamento a que uma nota pertence (`AAAA-MM`). Com dia 20, a competência de agosto vai de 21/07 a 20/08 |
| **Compensar (cheque)** | Registrar que o cheque foi depositado e o dinheiro entrou: vira recebimento e baixa as notas |
| **Comprovante** | Recibo do banco que prova um pagamento (boleto/Pix) ou um recebimento (empresas) |
| **Conferência** | Fila na tela com o que os bots não conseguiram lançar sozinhos; alguém revisa e lança |
| **Confiança** | Nota de 0 a 1 de quanto o sistema tem certeza de um campo lido; abaixo do limite o campo fica amarelo |
| **Consumo (L/h, km/L)** | Litros por hora de horímetro (máquinas) ou km por litro (caminhões), pelo método do tanque cheio |
| **Crédito da empresa** | Dinheiro recebido que ainda não baixou nenhuma nota (chegou antes da nota) |
| **DANFE** | Documento auxiliar (PDF/papel) da nota fiscal eletrônica |
| **Depósito de cheque (comprovante)** | Recibo do banco do depósito de um cheque; traz a CMC-7 do cheque depositado |
| **DV (dígito verificador)** | Dígito calculado (módulo 10 ou 11) que confirma se os outros foram lidos certo |
| **Editáveis** | Campos de uma aba que podem ser gravados/alterados; os outros são ignorados |
| **Fator de vencimento** | 4 dígitos do código de barras = dias desde uma data-base (ciclo reiniciado em 22/02/2025) |
| **Fechamento (empresas)** | Relatório mensal do que cada cliente comprou a prazo e quanto falta pagar; sai no dia do fechamento |
| **Fechamento do mês (contador)** | Relatório mensal das contas a pagar (pagos, em aberto, juros, por centro), com pacote ZIP |
| **Gestor (diesel)** | Pessoa que escolhe a máquina de cada canhoto no Telegram ("quem escolhe a máquina") |
| **Histórico** | Registro de cada lançamento, alteração, pagamento e exclusão, com data e usuário |
| **Horímetro / hodômetro** | Contador de horas da máquina / de km do veículo, informado no abastecimento |
| **Juros/multa** | Diferença paga a mais em relação ao valor do documento (ou o informado no comprovante) |
| **Lançamento** | Um registro no sistema (boleto, Pix, saída do caixa, nota, cheque…) |
| **Linha digitável** | Os 47/48 números impressos do boleto; o sistema copia **só os dígitos** |
| **Long polling** | Forma dos bots perguntarem ao Telegram por mensagens novas de tempos em tempos (`getUpdates`) |
| **Modo scanner** | Tratamento de foto: recorta o papel e corrige a perspectiva |
| **OCR** | Reconhecimento de texto em imagem (RapidOCR, local) |
| **Pedido** | Número do pedido de venda do cliente (empresas) ou do canhoto do posto (diesel) |
| **Pix** | Pagamento instantâneo; no Fin Pro, um "a pagar" com chave, valor e data prevista |
| **Previsão de saídas** | Quanto vai sair nas próximas semanas (boletos e Pix pendentes) |
| **Recebimento** | Dinheiro recebido de uma empresa (Pix, TED, depósito ou cheque compensado) |
| **Resumo da semana** | Mensagem de segunda (o que vence) e de sexta (o que foi pago) |
| **Saldo do diesel** | Pago nas compras − valor dos abastecimentos, em reais |
| **Saldo em caixa** | Todas as entradas − todas as saídas em dinheiro até a data |
| **Sininho** | Painel de avisos de vencimento no topo da tela |
| **Situação** | Estado calculado: pago, cancelado, vencido, vence hoje, a vencer, pendente |
| **Trecho (consumo do)** | Consumo entre o abastecimento atual e o anterior da mesma máquina |
| **TXID** | Identificador da transação dentro do Pix Copia e Cola |
| **Versão de demonstração** | Cópia do sistema com dados de exemplo (porta 8010), sem envio externo |

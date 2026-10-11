# Histórico de versões do Fin Pro

> Cada versão é um ponto guardado do sistema, com tudo o que mudou. Dá para ver, comparar e voltar a qualquer uma.
> Este arquivo é atualizado pela ferramenta `ferramentas/versao.py` (não precisa editar à mão).
> Numeração: **X.Y.Z** — X muda em reformulações grandes, Y em funções novas, Z em correções.

## v1.9.0 — 10/10/2026 — Controle de versão e backup total
- Controle de versão do código: cada versão fica guardada com número, data e a lista do que mudou (`VERSOES.md`); dá para comparar e voltar a qualquer uma sem tocar nos dados (`versoes.bat`).
- Cartão **Versão do sistema** em Configurações → Geral: versão em uso, histórico e alterações ainda não guardadas.
- Backup total: além dos bancos, planilhas e comprovantes, leva todas as configurações, o código-fonte e o histórico de versões.
- Pacote completo num único arquivo .zip (semanal ou mensal, ou pelo botão), guardando os últimos 4.
- Conferência do backup: bancos íntegros, nenhum comprovante faltando e cada arquivo igual ao que foi copiado (botão **Verificar backup**); falha aparece na Saúde do sistema.
- Restauração do sistema inteiro em outro computador com dois cliques (`RESTAURAR.bat`), a partir da pasta do backup ou de um pacote .zip.
- Documentação, especificação técnica e kit atualizados; 273 testes.

## v1.8.0 — 07/10/2026 — Documentação completa, especificação técnica e kit de reconstrução
- Manual de uso do sistema inteiro (`DOCUMENTACAO_FIN_PRO.md`).
- Especificação técnica em 27 documentos, com anexos gerados do próprio código.
- Kit para reconstruir o Fin Pro do zero em outra conversa.
- Início do controle de versão: este é o primeiro ponto guardado.

## v1.7.0 — 06/10/2026 — Diesel em reais, relatório em três níveis e relatório geral
- Saldo do diesel passou a ser em reais (compras pagas menos o valor de cada abastecimento).
- Relatório do diesel em três níveis: Simples, Detalhado e Completo, na tela, no Telegram e no Excel.
- Pontos de atenção do diesel, comparação com o período anterior e consumo de cada trecho.
- Relatório geral do mês (central de Relatórios), com juros, últimos 12 meses, caixa, diesel e empresas.

## v1.6.0 — 29/09/2026 — Controle de diesel
- Módulo Diesel: compras no posto, abastecimentos por máquina, médias e consumo (L/h e km/L).
- Bot do diesel no Telegram, com relatórios automáticos semanal, quinzenal e mensal.
- Preço do litro, reconhecimento do combustível, envio de canhoto pela tela e canhoto com dois combustíveis.
- Correção do saldo do diesel e do nome do posto lido no comprovante.

## v1.5.0 — 24/09/2026 — Juros à vista, central de comprovantes e depósito de cheque
- Juros e multas visíveis nas listas, no calendário, no Painel e em Gastos.
- Menu Comprovantes: busca com filtros em todas as partes do sistema e download em ZIP.
- Comprovante de depósito de cheque reconhecido; leitura do número do cheque corrigida.

## v1.4.0 — 22/09/2026 — Caixa, resumos da semana, nome Fin Pro e demonstração
- Módulo Caixa (entradas e saídas em dinheiro), com relatórios e bot do caixa.
- Resumos de segunda (o que vence) e de sexta (o que foi pago, com juros).
- Nome do sistema mudou para Fin Pro; linha digitável copiada só com números.
- Versão de demonstração para mostrar a clientes.

## v1.3.0 — 18/09/2026 — Empresas, cheques e permissões
- Módulo Empresas: notas fiscais, cheques pré-datados, recebimentos e fechamento no dia 20.
- Bot de notas fiscais, baixa automática e importação do fechamento em andamento.
- Administrador, perfis e permissões por pessoa; login ao abrir o aplicativo.
- Leitura do cheque com "bom para" e pedidos do verso; escolha do fechamento de cada nota.

## v1.2.0 — 17/09/2026 — Backup, usuários, comprovantes e banco de dados
- Backup fora do computador, login por pessoa e histórico de quem fez o quê.
- Baixa automática pelo comprovante, com valor pago, juros e desconto.
- Boletos recebidos por e-mail e Telegram; comandos no bot.
- Fechamento do mês para o contador; previsão de saídas; Saúde do sistema.
- Dados em banco SQLite, com a planilha Excel gerada automaticamente.

## v1.1.0 — 16/09/2026 — Importação, administrador e avisos para várias pessoas
- Importar boletos de outro sistema, em área protegida por senha de administrador.
- Sininho com avisos vistos e dispensados.
- Avisos do Telegram para várias pessoas e grupos.

## v1.0.0 — 14/09/2026 — Leitor de boletos
- Leitura de boletos em PDF e foto (código de barras, texto e OCR) com planilha como banco de dados.
- Lembretes de vencimento no Windows, Telegram e e-mail, com horários configuráveis.
- Aplicativo de desktop que inicia com o Windows; acesso pelo celular na rede.
- Centros de custo, análise de gastos e Pagamentos Pix.

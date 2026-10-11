# 15 — Recomendações para a próxima versão (o "Fin Pro melhor")

O sistema atual cresceu por pedidos, um módulo de cada vez. Funciona e está testado, mas carrega decisões que fizeram
sentido no caminho e que uma versão nova pode fazer melhor **desde o primeiro dia**. Aqui estão, por prioridade, com o
motivo e o cuidado para não perder nada do que já funciona.

## 15.1 Arquitetura e dados (fazer desde o início)

| # | Hoje | Na nova versão | Por quê |
|---|---|---|---|
| 1 | Cada registro guardado como **JSON** numa tabela única (`registros`) | **Tabelas com colunas tipadas e índices** (boletos, pix, caixa, empresas, notas, cheques, recebimentos, máquinas, compras, abastecimentos, centros, histórico) | Consultas rápidas com milhares de registros, integridade (chave estrangeira), relatórios em SQL |
| 2 | Sem migrações versionadas (colunas novas tratadas no código) | **Migrações** (ex.: Alembic) com versão do esquema | Atualizar sem quebrar dados antigos (lição #25) |
| 3 | Notas/cheques/recebimentos ligados à empresa **pelo nome** | Ligar por **id** (chave estrangeira); nome só para exibir | Renomear não precisa reescrever registros; sem ambiguidade |
| 4 | Dinheiro em `float` | **Centavos inteiros** ou `Decimal` no banco | Sem erro de arredondamento em somas |
| 5 | `aplicacoes` do recebimento como **texto** ("#12 NF 6859: R$ …") | Tabela **baixas** (recebimento_id, nota_id, valor) | Desfazer e calcular crédito sem interpretar texto |
| 6 | Fila de gravação (legado da planilha como banco) | Remover; o banco nunca fica bloqueado | Menos código e menos estados ("aguardando gravação") |
| 7 | Excel gerado a cada alteração + edição no Excel volta para o banco | Manter **exportação** sob demanda/agendada; se a edição no Excel continuar necessária, manter o mecanismo de snapshot (capítulo 02) | É uma função que o usuário usa; manter, mas isolada |
| 8 | SQLite (ótimo num computador) | SQLite continua bom num servidor só; **PostgreSQL** se houver vários servidores | Escolha pela forma de hospedar |
| 9 | Configuração e estado em vários JSON | Tabelas de configuração no banco (com histórico) | Backup, auditoria e migração num lugar só |

## 15.2 Segurança

| # | Na nova versão |
|---|---|
| 10 | **Login obrigatório para todos** quando online; sem exceção de "computador principal" atrás de proxy (capítulo 09 e 11). |
| 11 | **Segredos criptografados** (tokens dos bots, senhas de e-mail): chave fora do banco (variável de ambiente ou cofre do sistema — DPAPI no Windows); o backup leva o segredo cifrado. |
| 12 | HTTPS obrigatório, cookies `Secure` + `HttpOnly` + `SameSite`, proteção CSRF nas rotas de escrita, limite de requisições por IP. |
| 13 | Permissões **por ação e por módulo** num lugar só (hoje a tabela por caminho + checagens dentro de algumas rotas). Ex.: decorator `@exige("pagar")` em cada rota. |
| 14 | Registro de auditoria imutável (o histórico atual já existe — manter e incluir login/logout e mudanças de configuração). |

## 15.3 Bots e integrações

| # | Na nova versão |
|---|---|
| 15 | **Um motor de bot genérico** (receber, autorizar, baixar arquivo, deduplicar, conversa com máquina de estados, conferência) e os 4 bots como configurações dele — hoje são 4 implementações parecidas. |
| 16 | **Webhook** do Telegram na versão online (resposta imediata e sem disputa de `getUpdates`); polling só no modo local. |
| 17 | Canal de notificação **Web Push** (PWA) para substituir o toast do Windows na versão online. |
| 18 | Integrações que o usuário já quis/aprovaria: **extrato bancário (OFX)** para baixa automática e conciliação; **alerta de boleto adulterado** (banco/CNPJ diferente do histórico do fornecedor); **contas fixas** do mês ("a conta de luz ainda não chegou"). |

## 15.4 Leitura de documentos

| # | Na nova versão |
|---|---|
| 19 | **Pipeline plugável** por tipo de documento (boleto, comprovante, NF, cheque, depósito, cupom, canhoto) com a mesma interface: `reconhecer(texto) → pontos`, `extrair(texto) → campos+confiança`. Hoje cada módulo tem o seu classificador. |
| 20 | **Banco de amostras reais anonimizadas** + teste de regressão que mede a taxa de acerto por campo (meta e alarme se cair). |
| 21 | IA como **reserva** com orçamento (ex.: só quando a confiança < 0,8; limite mensal em R$), sempre validada pelas regras (DVs, contas que fecham). |
| 22 | Guardar o **texto lido** (OCR) junto do arquivo para reprocessar sem refazer o OCR quando as regras melhorarem. |

## 15.5 Front-end

| # | Na nova versão |
|---|---|
| 23 | Roteador e serviços globais em módulos separados (hoje `app.js` concentra roteador, sininho, contadores, login, arrastar/colar). |
| 24 | Componentes reutilizáveis (tabela com filtros, formulário com validação, seletor de período, cartões de números), já que quase toda tela repete esses padrões. |
| 25 | Tipagem (TypeScript ou JSDoc com checagem) para os formatos da API (anexo A7 dá os formatos). |
| 26 | Testes de tela por tela (Playwright) — hoje há 4 testes de tela; cada fluxo do capítulo 13 deveria ter um. |
| 27 | Acessibilidade e celular como requisito de cada tela (já existe, manter). |

## 15.6 Operação

| # | Na nova versão |
|---|---|
| 28 | Fuso horário explícito (`America/Sao_Paulo`) em todo cálculo de data. |
| 29 | Logs estruturados (JSON) e alerta quando um serviço de fundo para (hoje a tela Saúde mostra, mas ninguém é avisado). |
| 30 | Instalação reproduzível (Docker ou script) e atualização com um comando; versão do sistema visível. |
| 31 | Backup externo testado com **restauração automática de teste** (um backup que nunca foi restaurado não é backup). |

## 15.7 Funções pedidas ou sugeridas que ainda não existem

| Função | Situação |
|---|---|
| **Horas extras** | Citada pelo usuário junto com o caixa; falta a regra (quem, valor da hora, 50%/100%, onde entra) |
| **Diesel em Gastos** | Decidir se as compras de diesel contam em Gastos (evitar contar duas vezes se o posto é pago por boleto/Pix) |
| **Sugestão automática de centro de custo** | ~72 boletos sem centro; sugerir pelo fornecedor (histórico) e preencher em lote |
| **Fluxo de caixa futuro** | Somar o que vai entrar (cheques, fechamentos) ao que vai sair (previsão) |
| **Fornecedores que mais geram juros** | Ranking mensal de juros por fornecedor |
| **Enviar o fechamento para a empresa** | PDF por e-mail/Telegram depois de aprovado |
| **Conferência do caixa no fim do dia** | Informar o dinheiro na gaveta e comparar com o saldo |
| **Responsável e aprovação de pagamento** | Avisos para quem paga; só pagar o que foi aprovado |
| **Cadastro de fornecedores** | CNPJ → razão social e centro de custo habitual |
| **Menu Relatórios** | Pronto; falta registrar a rota no roteador (capítulo 10) |

## 15.8 O que NÃO mudar (o usuário depende disso)

- Planilhas Excel geradas com o mesmo formato (o escritório e o contador usam).
- Fechamento das empresas **no formato da planilha da Prospera**.
- Copiar a linha digitável **só com números**; juros visíveis em todo lugar.
- Nada lançado às cegas: o que o robô não tem certeza vai para **conferência**.
- Bots com os mesmos comandos (as pessoas já se acostumaram).
- Saldo do diesel **em reais**; relatório do diesel abrindo no nível **Simples**.
- Versão de demonstração separada, sem envio externo.

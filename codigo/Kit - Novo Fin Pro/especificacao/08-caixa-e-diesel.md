# 08 — Caixa (dinheiro) e Diesel

## Parte A — Caixa

Módulos: `app/caixa/servico.py` (regras e relatórios), `caixa/leitura.py` (cupom), `caixa/bot.py` (capítulo 06);
rotas `rotas/caixa.py` (prefixo `/api/caixa`, permissão `caixa`). Os lançamentos ficam na aba **`caixa`** do
`boletos.db` (mesma planilha `boletos.xlsx`, aba "Caixa"); campos em A2.

### A.1 Lançamento
- `movimento`: **Entrada** ou **Saída** (`MOVIMENTOS_CAIXA`); `valor` > 0; `data` e `hora`; `descricao` (entrada = "O
  que foi pedido"; saída = o que foi comprado); `local` (onde foi gasto); `centro_custo`; `pessoa` (quem gastou);
  `arquivo` (foto do cupom); situação `Confirmado`/`Cancelado` (cancelar mantém no histórico).
- Rotas: `GET /api/caixa?periodo=dia|semana|mes|ano&data=AAAA-MM-DD` (resumo), `POST` (lançar), `PUT /{id}`,
  `POST /{id}/cancelar`, `GET /{id}/historico`, `GET /relatorio/arquivo` (Excel), conferência e configuração do bot.

### A.2 Períodos e saldos
- Dia; **semana de segunda a domingo**; mês; ano. `deslocar` anda para o período anterior/seguinte (setas ‹ ›).
- **Saldo do período** = entradas − saídas do período.
- **Saldo em caixa** (`saldo_ate(fim)`) = **todas** as entradas − **todas** as saídas até o fim do período (e o saldo
  inicial = o mesmo cálculo até o dia anterior ao início).

### A.3 Relatório (`resumo`)
`entradas` e `saidas` (total, quantidade, média, maior), `saldo_periodo`, `saldo_caixa`, `saldo_inicial`,
`saidas_periodo_anterior` (comparação), `por_centro`, `por_local` (top 10, "onde mais se gastou"), `por_pessoa`,
`entradas_por_pedido` (top 10), `serie` (por dia; por mês no ano) e `lancamentos`. Cada grupo traz nome, total,
quantidade e %. Excel: resumo + todos os lançamentos.

### A.4 Integração com Gastos
`saidas_para_gastos()` transforma cada saída confirmada num "pago" com: `valor`, `centro_custo`, `vencimento` =
`data_pagamento` = data da saída, `beneficiario` = local (ou descrição), `comprovante` = foto do cupom, `pago_por` =
pessoa. Entra na Análise de gastos (tipo **dinheiro**), no Fechamento do mês (tipo **Dinheiro**, com o cupom no ZIP),
no relatório geral e no resumo de sexta.

### A.5 Leitura do cupom (`caixa/leitura.py`)
Valor = rótulos **a pagar / total** (nunca "dinheiro", "valor recebido" nem "troco"); data, hora, loja (cabeçalho).

---

## Parte B — Diesel

Módulos: `app/diesel/` — `modelos.py` (abas `maquinas`, `compras`, `abastecimentos`), `servico.py` (saldo, médias,
resumo, textos), `leitura.py` (comprovante de compra e canhoto), `precos.py` (`diesel_precos.json`), `bot.py`,
`relatorio.py` (três níveis); rotas `rotas/diesel.py` (prefixo `/api/diesel`, permissão `diesel`). Banco próprio
`diesel.db` + `diesel.xlsx`. Campos em A2.

### B.1 Conceito
A empresa compra **~1.000 L por semana** no posto (um crédito pago adiantado) e retira **Diesel S10** e **Diesel comum**
(S500) para as máquinas, cada um com o seu preço. Cada retirada gera um **canhoto** (pedido do posto) que pode ter
**várias linhas** (combustíveis diferentes para máquinas diferentes).

### B.2 Cadastros
- **Máquina**: nome (único), tipo (`Caminhão`, `Máquina`, `Veículo`, `Gerador`, `Outro`), placa/prefixo, **medidor**
  (`horas` = horímetro, `km` = hodômetro, `""`; padrão deduzido do tipo: Máquina e Gerador → horas, os outros → km),
  **combustível que usa**, situação (`Ativa`/`Inativa`), observações. `garantir_maquina` cria na hora pelo nome.
- **Combustíveis** (`COMBUSTIVEIS`): Diesel S10 (padrão), Diesel comum, Gasolina, Etanol, Arla 32.
- **Preços** (`precos.py`): `{combustivel: {preco, atualizado_em, por}}`; `GET/POST /api/diesel/precos`.

### B.3 Lançamentos
- **Compra** (`lancar_compra`): litros (padrão `LITROS_POR_COMPRA` = 1.000), valor, combustível,
  `preco_litro` = informado → valor/litros → tabela; `valor` = informado ou litros × preço; posto, forma, documento,
  arquivo. Situação `Confirmada`/`Cancelada`.
- **Abastecimento** (`lancar_abastecimento`): máquina (obrigatória), litros > 0, combustível (informado → o da máquina →
  S10), `preco_litro` = do canhoto → valor/litros → **tabela**, `valor` = litros × preço, medidor (horímetro/km), data,
  hora, posto, documento (nº do pedido), pessoa, arquivo.
- **Canhoto** (`lancar_canhoto(itens, comum, arquivo)`): um abastecimento por linha com litros > 0 (cada linha precisa de
  máquina); `comum` = data, hora, posto, pedido, quem abasteceu; a mesma foto anexada em todas.
- `atualizar`: mudar litros ou preço recalcula o valor. Rotas: `POST /compras`, `/abastecimentos`, `/canhoto`,
  `PUT /{aba}/{id}`, `POST /{aba}/{id}/cancelar`, `GET /{aba}/{id}/historico`, máquinas
  (`GET/POST /maquinas`, `PUT /maquinas/{id}` — declaradas **antes** de `/{aba}/{id}` para não serem capturadas).

### B.4 Saldo — em reais (`servico.saldo`)
```
valor_da_compra(c)        = c.valor  ou  litros × (c.preco_litro ou preço de referência)
valor_do_abastecimento(a) = a.valor  ou  litros × (a.preco_litro ou preço de referência)
preço de referência(comb) = tabela de preços; sem tabela, preço médio das compras daquele combustível
saldo.valor  = Σ valor_da_compra − Σ valor_do_abastecimento            (todas as compras e abastecimentos até a data)
equivalente  = para cada combustível usado (e os da tabela): saldo.valor ÷ preço → "≈ 884 L de S10 · 976 L de comum"
ultima_compra = compras do dia da última compra somadas (S10 e comum no mesmo dia = uma compra): valor, litros,
                gasto_desde (abastecimentos a partir daquela data)
```
Também devolve `litros` (comprado − abastecido, informativo), `pago`, `gasto`, `por_combustivel` (comprado, abastecido e
valor abastecido por combustível). Exemplo real: R$ 7.450 pagos − 200 L × 6,75 − 200 L × 7,45 = **R$ 4.610,00**.
*(Histórico: começou em litros por combustível; em 29/09 virou um saldo único em litros; em 06/10, em reais.)*

**Aviso de saldo baixo**: `alerta_valor` (padrão **R$ 1.000**, em Diesel → Bot do diesel); configurações antigas com
`alerta_litros` passam a usar o padrão em reais.

### B.5 Médias e consumo
- `media_da_maquina(nome, dias=30)`: litros no período, abastecimentos, por dia, **por semana**, por abastecimento.
- `consumo(maquina, abastecimentos)` (método do **tanque cheio**): ordena as leituras de medidor; rodado = última −
  primeira; litros = soma **sem** o primeiro abastecimento (ele só marca o ponto de partida); `horas` → **L/h** =
  litros ÷ horas; `km` → **km/L** = km ÷ litros. Precisa de 2+ leituras.
- `custo(a, precos_medios)`: valor do canhoto → litros × (preço da linha → tabela → médio do período).

### B.6 Períodos e resumo (`servico.resumo`)
Semana (segunda a domingo), **quinzena** (1–15 e 16–fim do mês), mês, ano. `resumo` devolve: período (com anterior/
seguinte e dias decorridos), comprado (litros, valor, quantidade), abastecido (litros, quantidade, custo, por dia),
preço médio, `por_combustivel` (comprado, valor comprado, abastecido, abastecimentos, custo, preço médio), `saldo`
(no fim do período), `por_maquina` (litros, %, abastecimentos, por dia, por abastecimento, **custo**, consumo,
combustíveis, último), `sem_abastecimento` (máquinas ativas paradas), compras e abastecimentos.

### B.7 Leitura dos arquivos (`diesel/leitura.py`)
**Classificar** compra × canhoto: a legenda manda ("compra/pago/comprovante" × "canhoto/abasteci"); senão pontos por
sinais (`SINAIS_COMPRA`: comprovante de pagamento/transferência, pix, ted, boleto…; `SINAIS_CANHOTO`: canhoto,
abastecimento, requisição, frentista, bomba, bico, placa, motorista…) e pelos litros (≥ **600 L** = compra; menos =
canhoto). Empate: o bot pergunta.

**Combustível** (`combustivel_do_texto`, texto sem espaços/hífens): arla → Arla 32; s10 → S10; s500/"diesel comum" →
comum; gasolina; etanol/álcool; "diesel" sozinho → "" (vale o da máquina).

**Canhoto com várias linhas** (`itens_do_canhoto`) — o algoritmo que acerta fotos tortas:
1. separa as **linhas de produto** (citam diesel/s10/s500/gasolina/etanol/arla) até as palavras de rodapé (totais,
   quantidade de itens, valor total bruto/líquido…); números de cada linha **sem códigos de produto** (`0\d{3,}`, ex.
   "000005");
2. cada número tem **leituras alternativas** (`_leituras`): normal; "7.450" → 7450 **ou** 7,450 (ponto no lugar da
   vírgula); "200006" → 200006 **ou** 200,006 (vírgula que o OCR comeu);
3. `_melhor_trio`: o **preço** precisa ter casas decimais e ficar entre **R$ 2 e R$ 15**; entre todas as combinações
   (litros, total) escolhe a de menor erro em `litros × preço ≈ total`; aceita com erro ≤ 1,5% e recalcula
   `litros = total ÷ preço`;
4. a linha que não fechou é **acertada pelos totais do rodapé** ("Quantidade de itens" = soma dos litros; "Valor
   total" = soma dos valores);
5. resultado real (Posto City 2): `200006 6,750 1.350,000` e `1.496,000 210,000 7.450` → 200 L × 6,75 = 1.350 e
   200 L × 7,45 = 1.490; rodapé 400 L e R$ 2.840.

Outros campos: data, hora, placa (`AAA-1A23`), medidor (km/hodômetro/horímetro), **pedido** (pedido/requisição/canhoto/
cupom/documento + 4–12 dígitos), posto. **Posto da compra** (`_posto`): no comprovante do banco, o **favorecido**
(nome/favorecido/recebedor/beneficiário/destinatário/para/pago a), descartando linhas de ruído do banco (telefone,
ouvidoria, SAC, 0800, "demais telefones"…) e o nome da própria empresa (configuração de Empresas e "Prospera").
Compra: valor pago pelo leitor de comprovantes (capítulo 04).

**Pela tela** (`POST /api/diesel/analisar`): guarda o arquivo, lê e devolve o formulário preenchido (linhas, máquina
sugerida pela placa, arquivo) para conferir e lançar (`POST /api/diesel/canhoto` ou `/compras`). Arrastar o arquivo
para a tela do Diesel faz o mesmo (evento `arquivos:soltos`, capítulo 10).

### B.8 Relatório em três níveis (`diesel/relatorio.py`)
`analise(tipo, referencia, alerta_valor)` = `resumo` + :
- `anterior` (rótulo, litros, custo, abastecimentos do período anterior) e `variacao` (litros e custo em %);
- por máquina: litros e custo anteriores, variação, R$/L, `media_normal` (litros/dia nos até 90 dias antes do período,
  contando só os dias desde o 1º abastecimento da máquina; sem "normal" com menos de **14 dias** de histórico) e
  `acima_do_normal` (% quando litros/dia ≥ normal × **1,5** na semana, **1,4** na quinzena, **1,3** no mês/ano, e o
  período tem ≥ 50 L);
- `serie` (por dia, ou por mês no ano: litros, valor, abastecimentos, valor por combustível); `por_posto`, `por_pessoa`;
- cada abastecimento ganha `custo`, `medidor_tipo` e `trecho` (leitura anterior da mesma máquina, data, rodado, consumo
  do trecho = litros ÷ horas ou km ÷ litros);
- `previsao` (só no período que contém hoje): saldo atual ÷ gasto médio diário dos últimos 30 dias → dias e data em
  que acaba;
- `alertas` (erro/aviso/info): saldo negativo ("falta lançar compra?"), saldo abaixo do limite, máquina acima do normal,
  abastecimentos sem horímetro/km em máquinas com medidor, abastecimentos sem preço, máquinas sem abastecimento.

Textos (`texto(tipo, ref, nivel)`): **simples** (abastecido em R$/L, variação, saldo + dias, comprado, R$ e litros por
máquina, contagem de pontos de atenção), **detalhado** (o relatório clássico + comparação + previsão + pontos de
atenção), **completo** (+ por posto, por pessoa, cada abastecimento com o trecho). Cortado em 3.900 caracteres para o
Telegram ("… continua no Excel").

Rotas: `GET /api/diesel/relatorio` (análise completa para a tela), `GET /relatorio/texto?nivel=`,
`POST /relatorio/enviar?nivel=` (gestores), `GET /relatorio/arquivo` (Excel **sempre completo**: Resumo, Máquinas, Por
dia/mês, Combustíveis, Por posto, Por pessoa, Abastecimentos com trecho, Compras, Pontos de atenção).

### B.9 Bot do diesel — comandos e automáticos
`/saldo` (saldo em R$ + litros equivalentes + última compra), `/medias` (cada máquina ativa), `/relatorio [semana|
quinzena|mes|ano] [simples|detalhado|completo]`, `/maquinas`, `/cancelar`, `/ajuda`.
Automáticos (`relatorios_devidos`): depois do `hora_relatorio` (padrão 07:00) — **semanal** toda segunda (semana
anterior), **quinzenal** nos dias 1 e 16 (quinzena que terminou), **mensal** no dia 1 (mês anterior); uma vez por
período (`enviados`); no nível `nivel_relatorio` (padrão simples). Configuração em `diesel_bot.json` (A3).

### B.10 Testes de referência
`test_diesel.py` (saldo em R$, canhoto real com dois combustíveis, comprovante Bradesco, fluxo do bot com várias linhas,
API), `test_diesel_relatorio.py` (níveis, trechos, normal, previsão, Excel), `test_caixa.py`.

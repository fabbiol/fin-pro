# 04 — Comprovantes de pagamento e baixa automática

Módulos: `app/comprovante.py` (regras puras, sem banco), `app/servico_comprovante.py` (lê o banco e grava),
`app/rotas/comprovantes.py`, `app/entrada.py` (e-mail/Telegram), tela Ler boletos (`web/js/views/leitura/comprovante.js`).

## 4.1 Onde um comprovante entra

| Entrada | Caminho no código |
|---|---|
| Tela Ler boletos (arrastar/escolher/colar) | `processar_leitura` → `analisar_resultado` (ver 03) |
| Anexar no lançamento (relógio → Anexar comprovante) | `POST /api/boletos/{id}/comprovante` → `valores_do_arquivo` (já sabe qual é o lançamento; só extrai valores) |
| Bot do Telegram / e-mail | `CaixaEntrada` → `processar_leitura` → se comprovante e `sugerido` claro, registra na hora e responde |
| Registrar escolhendo o lançamento | `POST /api/comprovantes/registrar` ou `POST /api/entrada/{id}/registrar` |
| Desfazer | `POST /api/boletos/{id}/desfazer-pagamento` (e o equivalente do Pix) |

## 4.2 É comprovante? (`eh_comprovante`)

Conta, no texto normalizado (sem acento, minúsculo):
- **sinais de comprovante** (`SINAIS_COMPROVANTE`): comprovante, valor pago, total pago, pagamento efetuado/realizado/
  concluído, transação efetuada/realizada/concluída, operação realizada, data do pagamento/de pagamento/do débito/da
  transação/da operação, autenticação, id da transação, id/transação, e2e, end to end, transferência realizada/enviada,
  pix enviado/realizado, pago em, debitado, código de autenticação, número de controle;
- **sinais de boleto** (`SINAIS_BOLETO`): local de pagamento, pagável em, pagável preferencialmente, ficha de
  compensação, recibo do pagador/sacado, nosso número, uso do banco, espécie doc, data do processamento, instruções,
  sacador/avalista, até o vencimento.

**É comprovante** se `sinais ≥ 2` **e** `sinais > sinais_de_boleto`.

## 4.3 O que se extrai (`extrair`)

Trabalha linha a linha; `_apos_rotulo` procura o valor depois do rótulo na mesma linha ou até 2 linhas abaixo
(leiautes em duas colunas), parando se a linha seguinte tiver muitas letras.

| Campo | Rótulos |
|---|---|
| `valor_pago` | valor (total) pago, total pago, valor do pagamento, valor debitado, valor cobrado, valor total, valor da transferência/do pix/da transação, valor transferido, `(=)`; senão `valor:`; senão o único valor monetário diferente de zero do texto |
| `valor_documento` | valor (original) do documento/boleto/título, valor original, valor nominal |
| `juros_multa` | soma das linhas com juros/multa/mora/encargos/acréscimo/`(+)` |
| `desconto` | soma das linhas com desconto/abatimento/bonificação/`(-)` |
| `data_pagamento` | data do pagamento/débito/transação/operação/transferência/efetivação/pix, pago em, realizado/efetuado/debitado em, data/hora, horário; senão a **maior data ≤ hoje** que não seja o vencimento |
| `vencimento` | vencimento |
| `beneficiario` | beneficiário (final), favorecido, recebedor, destinatário, nome do recebedor, cedente, razão social, "para", "destino" (descarta linhas que são só rótulo, CPF/CNPJ e textos com 4+ dígitos seguidos) |
| `documentos` | todos os CPF/CNPJ (com máscara, ou 14 dígitos com DV de CNPJ válido) |
| `codigos` | códigos de barras válidos do arquivo + linhas digitáveis achadas no texto |
| `chave_pix` | depois de "chave (pix)", só se o texto fala de Pix |
| `tipo` | `pix` se fala de Pix e não há código de barras; senão `boleto` |
| `agendado` | fala de agendado/agendamento **e não** de efetuado/realizado/concluído → **não dá baixa** |

## 4.4 De qual lançamento é (`pontuar`, `candidatos`, `escolher`)

Para cada boleto e Pix com id positivo, soma pontos:

| Critério | Pontos |
|---|---|
| Lançamento cancelado | −999 (fora) |
| Boleto com o **mesmo código de barras** | **+100** |
| Valor do documento (ou pago − juros + desconto) = valor do lançamento (±0,01) | +40 |
| Senão, valor pago = valor do lançamento | +40 |
| Senão, valor pago entre o valor e +30% (pagou com acréscimo) | +15 |
| Mesmo CPF/CNPJ (boleto: CNPJ do beneficiário; Pix: chave numérica) | +35 |
| Pix: a chave aparece no texto (ou os últimos 8 dígitos) | +45 |
| Nome: ≥ 50% das palavras significativas do lançamento aparecem no comprovante | +25 (≥ 30%: +10) |
| Mesmo vencimento | +25 |
| Data do pagamento entre 45 dias antes e 60 depois do vencimento | +(10 − \|dias\|/4), mín. 0 |
| … fora dessa janela | −25 |
| Comprovante de Pix tentando casar com boleto (sem linha igual) | −15 |
| Comprovante com código de barras tentando casar com Pix | −30 |
| Lançamento já pago | −40 se já tem comprovante; −10 se não |

Palavras significativas: ≥ 3 letras, sem acento, sem as genéricas (ltda, me, epp, sa, comércio, serviços, indústria,
de/da/do, cia, empresa, grupo, brasil…).

`candidatos`: os com **≥ 30 pontos**, ordenados por pontos (desempate pelo vencimento mais antigo), até 6.
`escolher`: aceita sozinho **só** se o primeiro tem **≥ 75 pontos** (`LIMITE_CONFIANCA`) **e** está **≥ 20 pontos** à
frente do segundo (`MARGEM_CONFIANCA`). Senão, a tela/o bot mostra os candidatos para alguém escolher.

## 4.5 O que é gravado (`dados_de_pagamento` + `servico_comprovante.registrar`)

```python
pago = valor_pago do comprovante (ou o valor do lançamento se não leu)
diferenca = pago − valor
juros_multa = diferenca se > 0            (se o lançamento não tem valor: o juros lido)
desconto    = −diferenca se < 0           (se o lançamento não tem valor: o desconto lido)
→ {"status": "Pago", "data_pagamento": data do comprovante (ou hoje), "valor_pago": pago,
   "juros_multa": ..., "desconto": ..., "comprovante": "arquivos/<id>.<ext>", "comprovante_nome": nome}
```
`pago_por` = usuário que registrou (automático pelo banco). **Desfazer**: volta para Pendente e limpa data, valor pago,
juros, desconto e comprovante.

`resumo_pagamento` (mensagem do bot e da tela): nome, valor, valor pago, juros, desconto, vencimento, data do
pagamento e **dias de atraso**:

> ✅ Pagamento registrado: CLA AUTO PECAS MIRASSOL LTDA · Valor do boleto: R$ 270,35 · Valor pago: R$ 275,75 em
> 15/10/2026 · Juros/multa: R$ 5,40 (5 dia(s) de atraso)

## 4.6 Juros visíveis no sistema inteiro

Os campos `valor_pago`, `juros_multa` e `desconto` (de `planilha.CAMPOS_PAGAMENTO`) alimentam:
- `servicos.resumir` (resumo da lista de boletos/Pix): `juros_multa`, `pagos_com_juros`;
- `servicos.painel`: `juros_mes_valor`, `juros_mes_qtd` ("Pagos no mês");
- `servicos.analise_gastos`: `juros_multa`, `pagos_com_juros`;
- calendário, fechamento do mês, relatório geral, resumo de sexta-feira.

## 4.7 Testes de referência
`test_comprovante.py` (Itaú, Bradesco, Pix, agendamento, empate entre parcelas), `test_juros_visiveis.py`,
`test_entrada.py` (bot e e-mail), `test_telas.py` (baixa pela tela).

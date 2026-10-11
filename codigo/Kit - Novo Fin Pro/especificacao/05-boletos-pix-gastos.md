# 05 — Boletos, Pix, painel, gastos, fechamento, relatórios e comprovantes

Módulos: `app/servicos.py`, `app/pix.py`, `app/importacao.py`, `app/fechamento.py`, `app/relatorio_geral.py`,
`app/busca_comprovantes.py`; rotas `boletos.py`, `pix.py`, `gastos.py`, `relatorios.py`, `busca_comprovantes.py`,
`comprovantes.py`, `sistema.py` (painel/previsão/exportar). Campos exatos das abas em **A2**; rotas em **A1**.

## 5.1 Situação de um lançamento (`servicos.situacao`) — usada em todo o sistema

```python
"Pago"      → "pago"
"Cancelado" → "cancelado"
sem vencimento → "pendente"
vencimento < hoje → "vencido"   |   == hoje → "vence_hoje"   |   > hoje → "a_vencer"
```
O filtro `situacao=pendente` aceita também vencido, vence_hoje e a_vencer.

## 5.2 Listas de boletos e Pix

`servicos.filtrar(registros, q, situacoes, campo_data, de, ate, centro, campos_busca, campos_digitos)`:
- **busca**: todas as palavras (normalizadas) devem aparecer nos campos de busca
  (boletos: beneficiário, nº doc, CPF/CNPJ, observações, emissor, linha, centro; Pix: recebedor, chave, descrição,
  observações, centro, txid); se não achar e o termo tiver ≥ 4 dígitos, procura nos dígitos da linha/código (ou chave);
- **centro** `__sem__` = sem centro de custo; **período** por `vencimento` ou `data_lancamento`.

`ordenar(campo, direcao)`; paginação na rota. `resumir`: quantidade, valor total, pendente, pago, vencido,
`juros_multa`, `pagos_com_juros` (cancelados não contam).

`serializar` (boleto) e `serializar_pix` acrescentam `situacao` e formatam datas. **Copiar linha digitável** no front
copia `linha_digitavel` **só com dígitos**. Exportação: `GET /api/exportar?formato=xlsx|csv|planilha` (planilha = o
arquivo `.xlsx` inteiro).

Lançar: `POST /api/boletos` (um) e `POST /api/boletos/lote` (até 300 numa única gravação). Situação:
`PATCH /api/boletos/{id}/status` (`status`, `data_pagamento`). Editar: `PUT /api/boletos/{id}` (com
`ignorar_validacao` para salvar uma linha que não passa nos DVs). As **ações em lote da tela** (marcar pagos/pendentes,
cancelar, centro de custo, excluir) chamam essas rotas para cada lançamento selecionado.

Histórico e comprovante de um lançamento: `GET /api/boletos/{id}/historico`, `POST|GET|DELETE /api/boletos/{id}/comprovante`
(rotas em `rotas/comprovantes.py`; equivalentes em `/api/pix/{id}/...`).

## 5.3 Pix (`app/pix.py`)

**Tipos de chave** (`TIPOS_CHAVE`): `cpf_cnpj` (CNPJ/CPF), `celular`, `email`, `aleatoria`.

`normalizar_chave(tipo, chave)` (formato guardado):
- CPF (11) / CNPJ (14) com DVs válidos → só dígitos;
- celular: 11 dígitos (DDD sem 0, 3º dígito 9), aceita `55` na frente → `+55DDNNNNNNNNN`;
- e-mail: minúsculo, até 77 caracteres, regex simples;
- aleatória: UUID.
`formatar_chave` (tela): CPF `000.000.000-00`, CNPJ `00.000.000/0000-00`, celular `(65) 99999-9999`.
`inferir_tipo(chave)`: @ → e-mail; UUID → aleatória; +55/13 dígitos → celular; CNPJ/CPF válido → cpf_cnpj; 11 dígitos → celular.

**BR Code ("Pix Copia e Cola", padrão EMV QRCPS do Banco Central)** — formato TLV (`ID` 2 dígitos + `tamanho` 2 dígitos + valor):
```
00 02 "01"                                  formato
26 nn [00 "br.gov.bcb.pix" | 01 chave | 02 descrição (até 40, se couber em 99)]   conta (IDs 26–51)
52 04 "0000"   53 03 "986" (BRL)   54 nn valor "123.45" (opcional)
58 02 "BR"     59 nn recebedor (ASCII, maiúsculo, até 25)   60 nn cidade (até 15)
62 nn [05 nn txid (alfanumérico até 25, "***" se vazio)]
63 04 CRC16   ← CRC-16/CCITT-FALSE (polinômio 0x1021, inicial 0xFFFF) sobre tudo até "6304", em hexadecimal maiúsculo
```
`ler_copia_e_cola` valida o início `000201`, o CRC, acha a conta `br.gov.bcb.pix` entre os IDs 26–51, extrai chave,
tipo, valor, recebedor, cidade, txid, descrição, se é dinâmico (`25` na conta). `gerar_copia_e_cola` gera o estático
(botão "QR code e Pix Copia e Cola" da lista: `GET /api/pix/{id}/qrcode.svg` e `/copia-e-cola`).

Arquivos: `ler_pix_de_arquivo` procura QR (`zxing` QRCode, original e com contraste) e textos `000201…6304XXXX` no PDF.
**Duplicado**: mesmo Copia e Cola, ou mesma chave + mesmo txid (não cancelado).
Colar um Copia e Cola em qualquer tela (`Ctrl+V`) abre a aba Pix já preenchida (`POST /api/pix/ler-codigo`).

## 5.4 Importar boletos de outro sistema (`app/importacao.py`, área do administrador)

1. `POST /api/importacao` (arquivo) → lê `.xlsx/.xlsm` (openpyxl), `.xls` (xlrd), `.xls` que na verdade é HTML
   (html.parser), CSV/TXT (decodifica utf-8-sig ou cp1252, descobre o separador). Até 5000 linhas e 80 colunas; procura
   o cabeçalho nas 30 primeiras linhas. Guarda o arquivo por 24 h em `dados/importacoes`.
2. Reconhece as colunas pelos **apelidos** (nomes normalizados) e descarta pelas palavras de **exclusão**:

| Campo | Apelidos (exemplos) | Exclui se tiver |
|---|---|---|
| linha_digitavel | linha digitável, código de barras, cod barras, barras, representação numérica, ld, barcode | nosso |
| beneficiario | beneficiário, cedente, fornecedor, favorecido, credor, razão social, emitente, empresa, nome | sacado, pagador, cpf, cnpj, banco, conta |
| documento_beneficiario | cpf cnpj, cnpj, cpf, cnpj do fornecedor | número, nosso |
| numero_documento | nº do documento, documento, doc, nota fiscal, nf, título, duplicata, fatura | cpf, cnpj, nosso, banco |
| vencimento | vencimento, dt venc, vencto, vencimento original | pagamento, pagto |
| valor | valor, valor do documento/título, valor original, a pagar, líquido, total, vlr | juros, multa, desconto, abatimento, acréscimo, pago, mora, encargos |
| status | status, situação, estado, pago, quitado | valor, data, dt |
| data_pagamento | data de pagamento, dt pagto, data da baixa, pago em, liquidação | valor, vencimento, forma, banco, conta, vlr |
| centro_custo | centro de custo, cc, departamento, setor, obra, projeto, unidade, filial | — |
| observacoes | observações, obs, histórico, descrição, complemento, memo | — |

3. `POST /api/importacao/{id}/previa` (aba, linha do cabeçalho, mapeamento, centro e situação padrão) → valida cada
   linha: DVs da linha digitável, valor e vencimento **conferidos com o código de barras**, boleto **já lançado** e
   **repetido no arquivo**; linhas de total ignoradas; datas `AAAA-MM-DD`, `dd/mm/aaaa`, `dd/mmm/aaaa`; situações
   "pago/liquidado/baixado" (ou data de pagamento) → Pago.
4. `POST /api/importacao/{id}/importar` (com os índices escolhidos) → grava tudo numa única operação.
5. O mapeamento fica salvo em `importacao_modelos.json` (reaplicado quando as colunas forem as mesmas).
   `GET /api/importacao/modelo.xlsx` = planilha modelo.

## 5.5 Painel (`servicos.painel`, `GET /api/painel`)

Soma boletos **e** Pix (cancelados fora):
- indicadores: `pendentes` (qtd/valor), `vencidos` (qtd/valor, separando boletos e Pix), `proximos7` (vence em até 7
  dias, sem os vencidos), `pagos_mes` (pela **data de pagamento** no mês corrente), `juros_mes` (juros dos pagos do mês),
  `lancados_mes`, `total_qtd`;
- `serie_mensal`: 12 meses (5 antes, o atual, 6 depois) por mês de vencimento: pago, vencido, a vencer;
- `vencidos` (todos, do mais antigo), `proximos` (8), `top_beneficiarios` (6), `recentes` (6).

**Previsão de saídas** (`previsao_saidas`, `GET /api/previsao?semanas=8`): semana 1 = hoje até hoje+6; pendentes por
semana (total, boletos, Pix, itens), `em_atraso` à parte, `sem_vencimento`, totais de 7 e 30 dias.

## 5.6 Análise de gastos (`servicos.analise_gastos`, `GET /api/gastos`)

Entradas: boletos, Pix e as **saídas do caixa** (`caixa.servico.saidas_para_gastos`: cada saída vira um "pago" na data
da saída, com o cupom como comprovante). Filtros: período, `campo_data` (vencimento/pagamento/lançamento),
`situacao` (todos/pagos/pendentes), `tipo` (todos/boleto/pix/dinheiro).
Saída: total, quantidade, totais por tipo, `juros_multa` e `pagos_com_juros`, `sem_centro`; `centros` (total,
boletos, Pix, dinheiro, pagos, pendentes, %); `serie_mensal` empilhada pelos 6 maiores centros + "Outros centros";
`maiores` (10 beneficiários). Excel: `GET /api/gastos/exportar`.

## 5.7 Fechamento do mês para o contador (`app/fechamento.py`, `GET /api/relatorios/fechamento`)

`montar(boletos, pix, mes, base, caixa)`:
- **base `vencimento`**: tudo que vence no mês (pagos, em aberto e cancelados);
- **base `pagamento`**: só o que foi pago no mês (pela data de pagamento).
- Cada item: tipo (Boleto/Pix/Dinheiro), nome, documento (nº doc, ou a chave Pix formatada), vencimento, valor,
  `valor_pago` (o pago ou o valor), `juros_multa`, `desconto`, `dias_atraso` (pagamento − vencimento), situação,
  `atrasado`, centro, pago por, comprovante.
- Totais: total (= pago + em aberto), pago, valor dos documentos pagos, juros e multas, descontos, pagos com atraso, em
  aberto, em atraso (qtd/valor), cancelados, quantidade por tipo, com/sem comprovante. `por_centro` ordenado pelo total.
- Arquivos (`/arquivo?formato=`): **xlsx** (abas Resumo, Pagos, Em aberto, Cancelados), **pdf** (reportlab), **zip**
  (`fechamento-AAAA-MM.pdf`, `.xlsx`, `comprovantes/AAAA-MM-DD_<nome>_<valor>.<ext>` e `comprovantes/SEM-COMPROVANTE.txt`
  com os pagos sem comprovante).

## 5.8 Central de Relatórios (`app/relatorio_geral.py`, `GET /api/relatorio-geral?mes=AAAA-MM`)

Cada parte só entra se quem pede tem a permissão (`acesso.pode`): `contas` e `historico` (gastos), `caixa`, `diesel`,
`empresas`; `previsao` para todos. Uma parte com erro vira `{"erro": "..."}` sem derrubar as outras.
- `contas`: pagos no mês (base pagamento) com `por_tipo` (Boleto/Pix/Dinheiro), juros, descontos, pagos com atraso,
  sem comprovante, `por_centro` (8), lista de **juros e multas** (ordenada pelo juro), e os totais da base vencimento;
- `historico`: 12 meses até o escolhido (boletos, Pix, dinheiro, total, juros, descontos, quantidade, com atraso);
- `caixa`: entradas, saídas, saldo do mês, saldo em caixa, top 5 centros; `diesel`: comprado, abastecido, custo,
  saldo no posto (R$), top 5 máquinas; `empresas`: faturado, recebido do fechamento, falta, em aberto, recebido no mês,
  cheques em carteira, top 8 empresas.
- Excel `/api/relatorio-geral/arquivo`: abas Resumo, Juros e multas, Últimos 12 meses.
- **Situação atual**: API e tela (`web/js/views/relatorios.js`) prontas e testadas; o item de menu depende de
  registrar a rota `relatorios` no roteador `web/js/app.js` (capítulo 10).

## 5.9 Central de comprovantes (`app/busca_comprovantes.py`, `GET /api/comprovantes/busca`)

Cada fonte vira um **item padronizado**: `tipo` (boleto, pix, cheque, recebimento, caixa, nota, diesel), id, nome, número,
detalhe, data, vencimento, valor, valor pago, situação, centro, pessoa, `comprovante_id` (o arquivo que prova) e
`original_id` (o boleto/cobrança), mais `linha` (dígitos da linha) e `busca` (texto extra).
Tipos de Empresas exigem a permissão `empresas`, caixa `caixa`, diesel `diesel`.

Filtros (`buscar`): `q` (todas as palavras em nome/número/detalhe/busca/centro/pessoa/tipo/nome do arquivo, ou trecho da
linha digitável com **≥ 8 dígitos**), `tipos`, `de/ate`, `valor` (exato, compara valor e valor pago), `valor_min/max`,
`numero`, `centro`, `pessoa`, `comprovante` (`com` | `sem` = pagos sem arquivo, sem contar entradas do caixa | `todos`),
`ordenar` (data/valor/nome), `direcao`. `resumo`: quantidade, com arquivo, valor, por tipo.
ZIP (`/zip`, até 500 arquivos): pasta por tipo, nome `AAAA-MM-DD - Tipo - Nome - nNúmero - R$ 1.234,56.ext`
(sem caracteres inválidos, até 150, numerado se repetir).

## 5.10 Testes de referência
`test_api.py`, `test_api_melhorias.py`, `test_pix.py`, `test_pix_centros_api.py`, `test_importacao.py`,
`test_fechamento.py`, `test_relatorio_geral.py`, `test_busca_comprovantes.py`, `test_juros_visiveis.py`.

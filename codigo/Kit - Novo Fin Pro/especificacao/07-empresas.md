# 07 — Empresas (vendas a prazo): notas, cheques, recebimentos e fechamento

Módulos: `app/empresas/` — `modelos.py` (abas), `servico.py` (regras), `leitura.py` (o que é cada arquivo),
`entrada.py` (bot de notas e envio do fechamento), `bot.py` (comandos), `relatorio.py` (Excel/PDF no formato da
Prospera), `configuracao.py` (`empresas.json`); rotas `rotas/empresas.py`. Banco próprio `empresas.db` +
`fechamentos.xlsx`. Campos: anexo **A2** (abas `empresas`, `notas`, `cheques`, `recebimentos`).

> Ponto de modelagem importante: notas, cheques e recebimentos guardam a **empresa pelo nome** (não por id).
> Por isso renomear uma empresa atualiza todos os registros (`renomear_empresa`), e excluir só é permitido sem
> lançamentos (senão, marcar como Inativa).

## 7.1 Situações

| Registro | Situações |
|---|---|
| Nota (uma linha por material) | `Em aberto`, `Em cheque`, `Parcial`, `Recebido`, `Cancelado` (abertas = Em aberto, Em cheque, Parcial) |
| Cheque | `Em carteira`, `Depositado`, `Compensado`, `Devolvido`, `Cancelado` |
| Recebimento | `Confirmado`, `Cancelado` |
| Empresa | `Ativa`, `Inativa` |

Valores exatos em A2 (`STATUS_NOTA`, `STATUS_CHEQUE`…). Tolerância de dinheiro: R$ 0,01.

## 7.2 Fechamento por competência

- Dia do fechamento: o da empresa (1–28) ou o padrão da configuração (`DIA_FECHAMENTO_PADRAO` = 20).
- `competencia_de(data, dia)`: até o dia do fechamento → mês da data; depois → mês seguinte (`AAAA-MM`).
- `periodo("2026-08", 20)` = **21/07/2026 a 20/08/2026**.
- Cada nota guarda `competencia`, que pode ser **mudada à mão** (`mover_nota_fiscal` move todas as linhas da mesma NF —
  ex.: NF 7120 chegou depois e vai para setembro/outubro).
- `fechamento(empresa, competencia)`: linhas da competência, total, recebido, **falta**, em cheque, número de NFs,
  recebimentos do período, cheques em carteira/depositados, `fechado` (hoje > fim).
- `resumo_empresas(competencia)`: um cartão por empresa (total, recebido, falta, em aberto total, atrasado de
  competências anteriores, cheques em carteira). **Com um mês escolhido, mostra só aquele mês.**
- Relatório (`relatorio.py`): Excel e PDF com cabeçalho "Prospera Industria E Serviços LTDA 03.880.985/0001-85" (vem da
  configuração "minha empresa"), título "Fechamento <Empresa>", colunas DATA, MATERIAL, UNIDADE, QUANT., VALOR UNI.,
  VALOR TOTAL, NOTA FISCAL, Nº PEDIDO e total no rodapé.
- No **dia do fechamento** de cada empresa, o bot de notas envia o resumo aos destinatários (uma vez por competência).

## 7.3 Identificar a empresa (`identificar_empresa`)

1. CNPJ (14 dígitos) igual ao cadastrado; 2. nome, razão social ou **apelido** (campo `apelidos`, separado por `;`, `,`
ou `|`) igual (normalizado); 3. contido (≥ 4 letras); 4. no texto: CNPJ citado, ou o nome mais longo que aparece.
`garantir_empresa` cadastra uma nova com o nome lido quando não acha.

## 7.4 Notas fiscais

- **XML da NF-e** (`ler_xml_nota`, confiança 1,0): `ide/nNF` (sem zeros), `ide/serie`, `ide/dhEmi|dEmi`, `emit` e `dest`
  (nome, CNPJ/CPF), itens `det/prod` (`xProd`, `uCom`, `qCom`, `vUnCom`, `vProd`, `xPed`), total `ICMSTot/vNF`, pedidos
  (dos itens ou de `infAdic/infCpl`).
- **DANFE em PDF/foto** (`extrair_nota`): itens linha a linha — depois da **unidade** (M³, MC, TON, KG, UN, PC, SC, LT,
  L, M, CX, H…) vêm quantidade, unitário e total, aceitos se `quantidade × unitário ≈ total` (±2%); descrição sem código
  do produto e sem NCM/CST/CFOP; nº da NF (ou pela chave de acesso), data, destinatário, pedido.
- `lancar_notas(empresa, itens, competencia)`: uma linha por material (total = quantidade × unitário quando faltar),
  número da NF e pedido sem zeros, competência automática; ao lançar, **aplica créditos** existentes da empresa.
- Bot: NF já lançada → "já estava lançada"; lança sozinho só se tem itens, nº, materiais com nome, destinatário e
  confiança ≥ 0,8; senão vai para a Conferência.

## 7.5 Cheques pré-datados

**Leitura da foto** (`extrair_cheque`, a foto é lida **nas 4 orientações** e as linhas são juntadas):
- **CMC-7** (rodapé): três campos `(\d{8}) (\d{10}) (\d{12})` (ou 30 dígitos corridos).
  Campo 1 = banco (3) + agência (4) + DV; campo 2 = compensação (3) + **número do cheque (6)** + tipificação (1);
  campo 3 = DV + **conta (10)** + DV. Ex.: `74880585 0180006165 400000989483` = Sicredi (748), agência 8058, cheque 616,
  conta 98948. `numero = campo2[3:9]`, `conta = campo3[1:11]` (sem zeros à esquerda). Tabela de bancos em `BANCOS`.
- Sem CMC-7: cada campo pelo rótulo, **antes ou depois** dele (o OCR embaralha as caixinhas): coop(erativa), ag(ência),
  conta/c/c, cheque nº, banco (código ou nome).
- **Valor**: o que está entre `#…#` (o OCR troca vírgula por ponto: `#4.287.60#`), senão o maior valor do texto.
- **"Bom para"** (data do depósito, escrita à mão no canto inferior direito): depois de "bom p/", "bom para", "data do
  depósito", "depositar em"; `_data_escrita_a_mao` testa as combinações dia/mês/ano (com até 1 caractere perdido entre
  eles, confusões O→0, l/I→1, S→5, B→8, Z→2) e fica com a data **de 3 meses atrás a 18 meses à frente** mais próxima de
  hoje; senão, qualquer data do cheque ou da legenda ("bom para 24/09").
- **Emitente**: a razão social (… LTDA/EIRELI/EPP/SA/ME) que mais aparece e não é de banco.
- **Pedidos do verso**: números de 4 dígitos em linhas com 2+ números (anos fora), agrupados por proximidade
  (diferença ≤ 200) — fica o maior grupo com 3+ (ex.: `7200-7201-7219-7245-7255`), mais os citados como "pedido N".
- Confiança = 0,25 × (número, conta, valor, data presentes) + 0,2 se há CMC-7.

**Regras**:
- `cheque_parecido`: mesmo CMC-7, ou mesmo número e valor → não cadastra de novo.
- `lancar_cheque`: guarda e **vincula** as notas abertas dos pedidos/NFs citados → `Em cheque` (com `cheque_id`).
- O cheque entra nos **avisos de vencimento** ("Cheque para depositar hoje").
- `compensar_cheque(cheque, data, arquivo)`: notas "Em cheque" voltam a "Em aberto", cria um **recebimento** (forma
  Cheque, valor do cheque, NFs/pedidos do cheque, `cheque_id`, comprovante anexado) que dá a baixa, e o cheque vira
  `Compensado` com `data_deposito`. Idempotente (se já existe recebimento do cheque, devolve o mesmo).
- Devolvido/Cancelado → solta as notas (`Em aberto`). Botão **Depositei** na tela = compensar com data (+ comprovante opcional).

## 7.6 Recebimentos e baixa automática

`registrar_recebimento(dados)`: valor > 0; empresa informada ou descoberta pelas NFs/pedidos; forma (Pix, TED, Depósito,
Cheque); `_aplicar` divide o valor entre as **notas candidatas** — as NFs citadas; senão os pedidos citados; senão
**todas as abertas** — da **mais antiga para a mais nova**:
```
para cada nota: parte = min(restante da nota, restante do dinheiro)
                valor_recebido += parte; status = "Recebido" se quitou (±0,01) senão "Parcial"; data_recebimento
```
O recebimento guarda `aplicacoes` como texto `#<id> NF <n>: R$ x; …; sobra (crédito): R$ y` — esse texto é a fonte
para **desfazer** (`cancelar_recebimento` devolve cada parte às notas) e para calcular a **sobra**.
**Crédito da empresa** = soma das sobras; quando uma nota nova é lançada, `aplicar_creditos` usa as sobras (do
recebimento mais antigo) e reescreve as `aplicacoes`.

## 7.7 Comprovantes de recebimento (`extrair_comprovante`)

Usa o leitor de comprovantes de pagamento (capítulo 04) e acrescenta: forma (Pix/TED/Depósito/Cheque), hora, pagador
(rótulos pagador/origem/de:/remetente/debitado de/cliente), id da transação (id/identificador/autenticação/e2e/controle
ou `E` + dígitos), NFs e pedidos citados (no texto e na **legenda** da mensagem: "NF 6859, 6869"), agendamento.
Foto sem valor/data → relê girando a imagem.

**Depósito de cheque** (`RE_DEPOSITO_DE_CHEQUE`: "depósito … cheque", "cheques depositados", "comprovante de depósito",
"valor do depósito", "depósito em/com cheque"): classificado como **comprovante** (não como cheque, mesmo trazendo a
CMC-7); lê todas as CMC-7, o valor ("valor do depósito"), a data ("data") e o "N.Trans". `cheques_do_deposito`: acha cada
cheque em carteira pela CMC-7 ou pelo número (desempatando pelo valor); só aceita se **todos** forem achados e a soma
bater com o valor do depósito; sem CMC-7, um único cheque em carteira com aquele valor. Compensa os cheques achados.
*(Correção de 24/09: antes, o comprovante do depósito era lido como um cheque novo e o sistema baixava o cheque errado.)*

Comprovante comum (Pix/TED): se o valor bate com um cheque em carteira da empresa (pelo número citado ou valor único),
compensa o cheque; senão registra o recebimento e baixa as notas.

## 7.8 Print do fechamento em andamento (início da operação)

`ler_fechamento(texto)`: linha "Fechamento <Empresa>" dá a empresa; cada linha `data material unidade quantidade
unitário total NF pedido` vira uma nota (total = quantidade × unitário se faltar). A tela de Conferência mostra as linhas
para conferir/desmarcar, escolher a empresa e importar (`POST /api/empresas/importar-fechamento`).

## 7.9 Classificação do arquivo (`classificar`)

Pontos por sinais: **nota** (danfe, documento auxiliar, chave de acesso, natureza da operação, destinatário/remetente,
valor total da nota, protocolo de autorização, inscrição estadual; +3 se DANFE), **cheque** (compensável, pague por
este cheque, quantia de, à sua ordem, bom para, cooperativo…; +2 se há CMC-7), **comprovante** (comprovante,
transferência, pix, ted, depósito, valor pago, id da transação, autenticação, e2e, recibo; +2 se "comprovante" e não é
nota), **fechamento** (fechamento, valor uni, valor total, nº pedido, nota fiscal, material; +2 se "fechamento").
Depósito de cheque → sempre `comprovante`. Vence o maior placar se ≥ 2. Cheques e não reconhecidos são relidos girando.

## 7.10 O que o bot de notas faz sozinho × Conferência

| Arquivo | Sozinho quando… | Senão |
|---|---|---|
| Nota | itens, nº, materiais, destinatário e confiança ≥ 0,8 (e a NF não foi lançada) | Conferência |
| Cheque | valor, empresa e "bom para" (e não é repetido) | Conferência (dica: legenda "pedido 7043, bom para 12/10") |
| Depósito de cheque | todos os cheques achados e soma confere | Conferência ("escolha o cheque") |
| Comprovante | valor e empresa; não é agendamento | Conferência ("escreva na legenda NF 6859, 6869") |
| Print de fechamento | — | sempre Conferência (importar) |

## 7.11 Testes de referência
`test_empresas.py`, `test_empresas_api.py`, `test_empresas_bot.py`, `test_empresas_leitura.py` (inclui o cheque real
`Comp. (1).pdf` e a CMC-7), `test_deposito_cheque.py` (comprovante Bradesco, cheque 616, R$ 4.287,60).

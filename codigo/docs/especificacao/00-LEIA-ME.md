# Fin Pro — Especificação técnica para reconstrução

> Este conjunto de documentos descreve o Fin Pro **por dentro**, com detalhe suficiente para uma pessoa (ou uma IA)
> reconstruí-lo do zero com todas as funções atuais. O manual de uso (o que cada tela faz, do ponto de vista de quem
> usa) é o arquivo [`DOCUMENTACAO_FIN_PRO.md`](../../DOCUMENTACAO_FIN_PRO.md) na raiz do projeto. **Os dois se
> complementam**: o manual diz *o quê*; esta especificação diz *como*.

## Como os documentos estão organizados

| Arquivo | Conteúdo | Origem |
|---|---|---|
| [01-arquitetura.md](01-arquitetura.md) | Tecnologias, processos, threads, inicialização, pastas, objetos compartilhados | escrito à mão |
| [02-motor-de-dados.md](02-motor-de-dados.md) | Banco SQLite + planilha Excel sincronizada, histórico, centros de custo, arquivos, fila | escrito à mão |
| [03-leitura-de-boletos.md](03-leitura-de-boletos.md) | FEBRABAN (DVs, fator de vencimento, conversões), código de barras, OCR, extração espacial, confiança, alertas | escrito à mão |
| [04-comprovantes-e-baixa.md](04-comprovantes-e-baixa.md) | Reconhecer comprovante, extrair, pontuar candidatos, decidir, gravar juros/desconto | escrito à mão |
| [05-boletos-pix-gastos.md](05-boletos-pix-gastos.md) | Regras de boletos, Pix (BR Code/CRC16), importação, painel, previsão, gastos, fechamento do mês, relatórios, busca de comprovantes | escrito à mão |
| [06-notificacoes-e-bots.md](06-notificacoes-e-bots.md) | Lembretes, canais, sininho, resumos semanais, os 4 bots, caixa de entrada por e-mail/Telegram | escrito à mão |
| [07-empresas.md](07-empresas.md) | Fechamento por competência, NF-e/DANFE, cheque (CMC-7, "bom para", pedidos), baixa automática, créditos, depósito de cheque | escrito à mão |
| [08-caixa-e-diesel.md](08-caixa-e-diesel.md) | Caixa (saldos, relatórios, bot) e Diesel (saldo em R$, canhoto multi-linha, trio litros×preço=total, bot, relatório em 3 níveis) | escrito à mão |
| [09-acesso-e-seguranca.md](09-acesso-e-seguranca.md) | Rede, senha de acesso, usuários, permissões por rota, administrador, hashes, bloqueios | escrito à mão |
| [10-front-end-e-desktop.md](10-front-end-e-desktop.md) | SPA sem build, roteador, telas, eventos globais, tema, aplicativo de desktop, bandeja, cache do WebView2 | escrito à mão |
| [11-backup-rede-demonstracao.md](11-backup-rede-demonstracao.md) | Backup total (dados, comprovantes, código e versões), restauração, acesso pelo celular, saúde, logs, demonstração, controle de versão | escrito à mão |
| [12-plano-de-reconstrucao.md](12-plano-de-reconstrucao.md) | **Roteiro passo a passo** para reconstruir, com critérios de aceite de cada etapa | escrito à mão |
| [13-fluxos-ponta-a-ponta.md](13-fluxos-ponta-a-ponta.md) | 8 fluxos completos em diagramas (quem chama quem, em que ordem): leitura, comprovante pelo Telegram, lembrete, nota fiscal, cheque até o depósito, canhoto do diesel, edição no Excel, login/permissão | escrito à mão |
| [14-licoes-aprendidas.md](14-licoes-aprendidas.md) | **46 erros reais** que já aconteceram, com causa, correção e a regra para não repetir | escrito à mão |
| [15-melhorias-para-a-proxima-versao.md](15-melhorias-para-a-proxima-versao.md) | O que fazer melhor numa versão nova (dados, segurança, bots, leitura, telas, operação), funções pendentes e **o que não pode mudar** | escrito à mão |
| [16-glossario.md](16-glossario.md) | Termos do negócio e do sistema (competência, CMC-7, bom para, canhoto, fator de vencimento…) | escrito à mão |
| [A1-api.md](A1-api.md) | **Todas as rotas da API** (método, caminho, permissão, parâmetros, corpo) | gerado do código |
| [A2-modelo-de-dados.md](A2-modelo-de-dados.md) | **Todas as tabelas e campos** (formato, editável, situações) | gerado do código |
| [A3-configuracoes.md](A3-configuracoes.md) | Variáveis de ambiente, permissões, formato dos arquivos de configuração | gerado do código |
| [A4-mapa-do-codigo.md](A4-mapa-do-codigo.md) | **Cada módulo Python**: constantes, classes, funções (assinatura + descrição) | gerado do código |
| [A5-front-end.md](A5-front-end.md) | Cada arquivo do front-end e o que exporta; variáveis de cor | gerado do código |
| [A6-testes.md](A6-testes.md) | Cada teste automatizado e o que ele garante | gerado do código |
| [A7-respostas-da-api.md](A7-respostas-da-api.md) | **Resposta real** de cada rota GET (formato exato dos campos), gerada sobre uma cópia dos dados de demonstração | gerado do código |
| [A8-constantes.md](A8-constantes.md) | **Todas as constantes por extenso**: listas de palavras-sinal, expressões regulares, limites, pesos | gerado do código |
| [A9-telas-e-chamadas.md](A9-telas-e-chamadas.md) | Por arquivo de tela: rotas chamadas, ações dos botões, eventos, armazenamento local | gerado do código |
| [A10-codigo-dos-testes.md](A10-codigo-dos-testes.md) | **Código completo dos 273 testes** (o contrato executável, com textos reais de OCR) | gerado do código |

## Manter atualizado

Os anexos `A1` a `A10` são gerados pelo próprio código. Depois de qualquer mudança no sistema:

```bash
.venv\Scripts\python ferramentas\gerar_especificacao.py
```

O gerador usa uma pasta de dados temporária e **nunca lê nem altera** a pasta `dados` (nem senhas, nem tokens); as
respostas de exemplo (A7) saem de uma **cópia** da pasta de demonstração, com o envio externo bloqueado.
Os capítulos `01` a `16` são escritos à mão: atualize o capítulo do módulo que mudou e, se corrigir um erro,
acrescente uma linha em `14-licoes-aprendidas.md`.

## Para reconstruir

1. Leia o [manual de uso](../../DOCUMENTACAO_FIN_PRO.md) inteiro: ele é o "contrato" do que o usuário espera.
2. Leia **`14-licoes-aprendidas.md`** (os erros que já aconteceram) e **`15-melhorias-para-a-proxima-versao.md`**
   (o que fazer melhor e o que não pode mudar) **antes de escrever código**.
3. Leia `16-glossario.md`, `01-arquitetura.md`, `02-motor-de-dados.md` e `13-fluxos-ponta-a-ponta.md`.
4. Siga o [`12-plano-de-reconstrucao.md`](12-plano-de-reconstrucao.md), etapa por etapa. Cada etapa diz o que
   construir, quais capítulos consultar, quais anexos usar como referência exata e quais testes provam que a etapa
   está pronta.
5. Referências exatas durante o trabalho: campos (A2), rotas (A1), formato das respostas (A7), números mágicos e
   expressões regulares (A8), o que cada tela chama (A9), funções (A4).
6. Os testes são a melhor garantia: copie o código do **A10** (ou a pasta `tests/`) para o novo projeto — um sistema que
   passa nos mesmos testes faz o mesmo que o atual.

## O que guardar junto para reconstruir sem o código atual

A especificação descreve **todo o comportamento**, com as fórmulas e regras que importam escritas por extenso. Mesmo
assim, três coisas tornam a reconstrução muito mais segura e devem ser guardadas junto (num backup fora do computador):

1. **A pasta `tests/`** — os 273 testes são o contrato executável: um sistema novo que passa neles faz o mesmo que o
   atual. O código completo deles também está no anexo **A10**, então a especificação sozinha já o carrega.
2. **Amostras reais anonimizadas** — os boletos, o cheque, os comprovantes e o canhoto usados para calibrar a leitura
   (capítulo 12, "Estimativa total").
3. **Uma cópia do código atual** — mesmo que a ideia seja reescrever, ele serve de referência para qualquer dúvida.

Como a especificação agora inclui o código dos testes (A10), as respostas reais da API (A7) e todas as constantes
(A8), um desenvolvedor (ou uma IA) consegue reconstruir o Fin Pro do zero com todas as funções **só com esta pasta**.
As amostras reais de documentos continuam recomendadas para calibrar a leitura de fotos de outros bancos e postos.

## Números do sistema atual (07/10/2026)

| Item | Quantidade |
|---|---|
| Código Python (`app/`) | ~22.100 linhas em 87 módulos |
| Front-end (`web/`) | ~13.300 linhas (JS, CSS, HTML) |
| Rotas da API | 177 |
| Testes automatizados | 273 (incluindo os testes das telas no navegador) |
| Bancos de dados | 3 (boletos, empresas, diesel) |
| Bots do Telegram | 4 (boletos, notas, caixa, diesel) |

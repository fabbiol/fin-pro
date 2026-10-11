# 12 — Plano de reconstrução passo a passo

> Siga as etapas **na ordem**: cada uma depende das anteriores. Em cada etapa: o que construir, onde está a
> especificação, a referência exata (anexos) e o **critério de aceite** (os testes que precisam passar — copie os testes
> da pasta `tests/` do sistema atual para o novo projeto; eles são o contrato).
>
> Regra de ouro: **o teste do sistema atual é a definição do comportamento**. Se o texto deste documento e um teste
> discordarem, vale o teste.

## Antes de tudo — ler (meio dia)
- `14-licoes-aprendidas.md` (46 erros reais) e `15-melhorias-para-a-proxima-versao.md` (decisões melhores para a versão
  nova e **o que não pode mudar**). Decida já as melhorias de arquitetura da seção 15.1 (tabelas tipadas, migrações,
  empresa por id, dinheiro em centavos): elas mudam a forma de construir as etapas 1, 11 e 13.
- `16-glossario.md` e `13-fluxos-ponta-a-ponta.md`.

## Etapa 0 — Preparação (meio dia)
- Python 3.10+, Windows 10/11 (ou Ubuntu para a versão online); criar `.venv`; `requirements.txt` (capítulo 01, 1.2).
- Estrutura de pastas (01, 1.3); `app/config.py` com todas as variáveis (A3); `iniciar.bat`.
- `tests/conftest.py` isolando os dados (`LEITOR_DADOS_DIR` temporário, automáticos desligados) e o gerador de boletos de
  exemplo (`tests/gerar_boleto_exemplo.py`, `tests/corpus.py`).
- Copie o código dos testes do anexo **A10** para `tests/` (um arquivo por seção). Eles vão falhar até cada etapa ficar
  pronta — é o esperado.
- **Aceite**: `pytest` roda (mesmo sem testes passando).

## Etapa 1 — Motor de dados (1–2 dias)
- `planilha.py` (`Coluna`, `DefinicaoAba`, abas `boletos`, `pix`, `caixa` exatamente como em A2; formatação; histórico),
  `banco.py` (capítulo 02 inteiro), `repositorio.py`, `fila_gravacao.py`, `arquivos.py`.
- **Aceite**: `test_banco.py`, `test_planilha.py`, `test_gravacao.py`.

## Etapa 2 — Leitura de boletos (3–5 dias, a parte mais difícil)
- `boleto/codigo.py` (capítulo 03, 3.2 — copie as fórmulas), `bancos.py`, `leitores.py` (PDF, imagens, código de barras),
  `ocr.py` (RapidOCR latino + cache), `imagem.py` (modo scanner), `texto.py` (rótulos e busca espacial — 3.7),
  `extrator.py` (consolidar, confiança, alertas, harmonizar — 3.8), `tarefas.py`, `servico_leitura.py`.
- **Aceite**: `test_codigo.py` (10), `test_texto.py` (8), `test_corpus.py` (8), `test_harmonizacao.py`, `test_ia.py`.

## Etapa 3 — API base, boletos, Pix e centros (2–3 dias)
- `main.py` (lifespan, middlewares, erros — 01, 1.6/1.7), `contexto.py`, `rotas/comum.py`, `rotas/leitura.py`,
  `rotas/boletos.py`, `rotas/pix.py`, `pix.py` (BR Code, CRC16 — 05, 5.3), `servicos.py` (situação, filtros, resumo,
  exportação — 05, 5.1/5.2), centros de custo. Rotas e corpos exatos em **A1**.
- **Aceite**: `test_api.py`, `test_api_melhorias.py`, `test_pix.py`, `test_pix_centros_api.py`.

## Etapa 4 — Front-end base (3–4 dias)
- `index.html`, `app.css` (variáveis A5, tema claro/escuro), `api.js`, `ui.js`, `estado.js`, `icons.js`, `centros.js`,
  `grafico.js`, `detalhes.js`, roteador `app.js` (10.3), telas **Painel**, **Ler boletos**, **Boletos lançados**
  (lista + calendário), **Pagamentos Pix** (10.5).
- Comportamentos obrigatórios: copiar linha só com dígitos; campos de baixa confiança em amarelo; arrastar/colar em
  qualquer tela; progresso da leitura; juros visíveis nas listas.
- **Aceite**: abrir cada tela sem erro no console; `test_telas.py` (parte de leitura e painel).

## Etapa 5 — Comprovantes e baixa automática (1–2 dias)
- `comprovante.py` (capítulo 04 — sinais, extração, pontuação, limites 75/20), `servico_comprovante.py`,
  `rotas/comprovantes.py`, tela de comprovante em Ler boletos, anexar no Histórico, Desfazer.
- **Aceite**: `test_comprovante.py`, `test_juros_visiveis.py`, `test_telas.py` (baixa por comprovante).

## Etapa 6 — Painel, previsão, gastos, fechamento do mês (2 dias)
- `servicos.painel`, `previsao_saidas`, `analise_gastos` (05, 5.5/5.6), `fechamento.py` (Excel, PDF, ZIP — 5.7),
  `rotas/gastos.py`, tela Gastos (3 abas).
- **Aceite**: `test_fechamento.py`.

## Etapa 7 — Notificações e sininho (2–3 dias)
- `notificacoes/regras.py`, `canais.py` (Windows/Telegram/e-mail), `servico.py` (agendador, sininho, agenda,
  histórico — capítulo 06), `rotas/notificacoes.py`, tela Notificações, sininho na casca.
- **Aceite**: `test_notificacoes.py` (13), `test_sino.py`, `test_telegram_destinatarios.py`.

## Etapa 8 — Usuários, permissões e área de administrador (2 dias)
- `admin.py`, `usuarios.py`, `acesso.py` (tabela de permissões 9.3), `rotas/usuarios.py`, `rotas/administracao.py`,
  login na casca, menu filtrado por `pode()`.
- **Aceite**: `test_admin.py`, `test_usuarios.py`, `test_permissoes.py`.

## Etapa 9 — Integrações: importação, caixa de entrada, bot dos boletos, backup, rede, saúde, logs (3–4 dias)
- `importacao.py` (05, 5.4), `entrada.py` + `bot.py` (06, 6.8), `backup.py` (backup total, pacote .zip e
  conferência — 11.1), `ferramentas/restaurar_backup.py`, `rede.py`, `saude.py`, `registro_log.py` (capítulo 11),
  `versao.py` + `ferramentas/versao.py` + `versoes.bat` + `VERSOES.md` (controle de versão — 11.6), telas de
  Configurações (4 abas, com os cartões **Backup total** e **Versão do sistema**).
- **Aceite**: `test_importacao.py`, `test_entrada.py`, `test_bot.py`, `test_backup.py`, `test_versao.py`,
  `test_rede.py`, `test_saude.py`, `test_registro_log.py`.

## Etapa 10 — Aplicativo de desktop (1 dia)
- `desktop.py`, `janela.py`, `preferencias.py`, `inicializacao.py`, `atalhos.py`, `__main__.py` (10.7, 01.4).
- **Aceite**: `test_desktop_cache.py`; abrir pelo atalho, fechar para a bandeja, notificação clicável.

## Etapa 11 — Empresas (4–5 dias)
- `empresas/modelos.py` (A2), `configuracao.py`, `servico.py` (competência, baixa, créditos, cheques — capítulo 07),
  `leitura.py` (NF-e XML/DANFE, CMC-7, "bom para", pedidos do verso, comprovante, depósito de cheque, print),
  `relatorio.py` (formato Prospera), `entrada.py` (bot de notas, envio no dia do fechamento), `bot.py`,
  `rotas/empresas.py`, tela Empresas (6 abas). Cheques entram nos lembretes (`FonteLembretes`).
- **Aceite**: `test_empresas.py` (16), `test_empresas_api.py`, `test_empresas_bot.py` (16), `test_empresas_leitura.py`
  (12), `test_deposito_cheque.py`.

## Etapa 12 — Caixa (2 dias)
- Aba `caixa`, `caixa/servico.py`, `caixa/leitura.py`, `caixa/bot.py` (conversa por etapas), `rotas/caixa.py`, tela
  Caixa; integração com Gastos e Fechamento (`saidas_para_gastos`).
- **Aceite**: `test_caixa.py` (17).

## Etapa 13 — Diesel (4–5 dias)
- `diesel/modelos.py`, `precos.py`, `servico.py` (saldo em R$, médias, consumo, resumo — capítulo 08 B.4–B.6),
  `leitura.py` (classificação, combustível, `_leituras`, `_melhor_trio`, rodapé, posto — B.7), `bot.py` (protocolo dos
  botões — 06, 6.11), `relatorio.py` (três níveis — B.8), `rotas/diesel.py` (máquinas antes de `/{aba}/{id}`), tela
  Diesel (5 abas).
- **Aceite**: `test_diesel.py` (23), `test_diesel_relatorio.py` (6).

## Etapa 14 — Resumos, central de comprovantes e relatório geral (2 dias)
- `resumo_semanal.py` (6.6), `busca_comprovantes.py` (5.9) + tela Comprovantes, `relatorio_geral.py` (5.8) + tela
  Relatórios (registrada no roteador).
- **Aceite**: `test_resumo_semanal.py`, `test_busca_comprovantes.py`, `test_relatorio_geral.py`.

## Etapa 15 — Demonstração e documentação (1 dia)
- `demonstracao.py` + `demonstracao.bat` (11.5); README; manual de uso; `ferramentas/gerar_especificacao.py`.
- **Aceite**: `test_demonstracao.py`; **suíte completa verde**: `.venv\Scripts\python -m pytest` → 273 testes.

## Estimativa total
Cerca de **35 a 45 dias de trabalho** para uma pessoa experiente reconstruir com a mesma qualidade, partindo desta
especificação e dos testes. As etapas 2 (leitura), 11 (empresas) e 13 (diesel) concentram o risco: foram calibradas com
**documentos reais** (boletos do HIPER JN, BOL. NF 134668, cheque Sicredi `Comp. (1).pdf`, comprovante Bradesco de
depósito, canhoto do Posto City 2). Guarde amostras reais anonimizadas para testar.

## Checklist final de paridade com o sistema atual
- [ ] 177 rotas da API (A1) respondendo com os mesmos campos.
- [ ] 3 bancos com as mesmas abas e campos (A2), planilhas geradas e edições do Excel trazidas de volta.
- [ ] Leitura: bancário e arrecadação, fator nos dois ciclos, correção de dígitos, fotos tortas, PDFs escaneados, guias.
- [ ] Comprovantes: baixa automática só com escolha clara (≥ 75 e margem 20), juros e desconto gravados.
- [ ] Lembretes 3× no dia, antes, vencidos; Windows/Telegram/e-mail; sininho com visto/dispensado; resumos seg/sex.
- [ ] 4 bots (boletos, notas, caixa, diesel) com os mesmos comandos e botões.
- [ ] Empresas: competência dia 20, NF-e, cheque (CMC-7, bom para, pedidos), baixa com crédito, depósito de cheque.
- [ ] Caixa com saldos e relatórios, entrando em Gastos e no fechamento.
- [ ] Diesel com saldo em R$, canhoto multi-linha, consumo L/h e km/L, relatório Simples/Detalhado/Completo.
- [ ] Usuários, permissões por rota, administrador, rede com senha, backup externo, saúde, demonstração.
- [ ] Os 273 testes passando.

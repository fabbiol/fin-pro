# Decisões já tomadas (não pergunte de novo)

Estas decisões foram tomadas pelo dono e por quem construiu o Fin Pro original. Elas existem para que você trabalhe
sem interromper ninguém. Se algo não estiver aqui, decida pela ordem de autoridade do `CLAUDE.md` e anote em
`PROGRESSO.md`.

## Produto
- Nome: **Fin Pro**. Idioma de tudo (telas, mensagens, código, comentários): **português do Brasil**.
- Usuário: escritório da **Prospera Industria E Serviços LTDA (CNPJ 03.880.985/0001-85)**; pessoas: Fábio (dono,
  administrador), Almir e outros. Use esses dados só como **padrão de configuração** (cabeçalho do fechamento das
  empresas), nunca para enviar nada.
- O comportamento deve ser **igual ao do Fin Pro atual** (o manual e os testes descrevem). Melhorias só na Fase 2.

## Tecnologia (obrigatória — os testes dependem disso)
- **Python 3.10+**, **FastAPI**, **SQLite**, **openpyxl**, **pypdfium2**, **zxing-cpp**, **RapidOCR**, **OpenCV**,
  **reportlab**, **pywebview + pystray** (desktop), front-end **HTML + CSS + JavaScript em módulos ES, sem build**.
  Lista exata em `requirements.txt`.
- **Mesma estrutura de pacotes e mesmos nomes públicos** do original (`app/…` conforme o anexo A4): os testes importam
  `app.banco`, `app.diesel.servico`, `app.empresas.leitura` etc. Os detalhes internos de cada função são livres.
- Mesmas rotas da API (A1), mesmos campos (A2), mesmos nomes de arquivos em `dados/` (A3), mesmas constantes (A8).
- Dados em `dados/` (variável `LEITOR_DADOS_DIR`), porta 8000; demonstração em `dados_demo/`, porta 8010.

## Fases
- **Fase 1 (obrigatória): paridade.** Construir tudo até os 273 testes passarem e todas as telas existirem —
  incluindo o menu **Relatórios** registrado no roteador (no original ele ficou pronto mas fora do menu).
  Sem "melhorias" que mudem comportamento.
- **Fase 2 (opcional, só depois da Fase 1 completa):** melhorias do capítulo 15 que **não quebram nenhum teste**.
  Já aprovadas para fazer, se der:
  1. roteador do front-end organizado em módulos (rotas, sininho, contadores, login, arrastar/colar separados);
  2. fuso horário explícito `America/Sao_Paulo` nos cálculos de data;
  3. motor de bot genérico **por dentro** (os 4 bots continuam com os mesmos comandos, botões e mensagens);
  4. logs mais claros e um alerta na tela Saúde quando um serviço de fundo para.
  **Não fazer na Fase 2** (exigem mudar testes ou o formato dos dados; ficam como sugestão para o dono):
  trocar o banco para tabelas tipadas, dinheiro em centavos, empresa por id, criptografar segredos, webhooks, versão
  online. Anote-as em `PROGRESSO.md` → "Sugestões para o dono".

## Regras de negócio que confundem (já decididas)
- Saldo do diesel **em reais** (compras pagas − valor dos abastecimentos), não em litros.
- Relatório do diesel abre em **Simples** (níveis Simples/Detalhado/Completo).
- Fechamento das empresas: **dia 20**, período de 21 do mês anterior a 20 do mês.
- Linha digitável sempre copiada **só com números**.
- Juros e multas **visíveis** nas listas, calendário, Painel, Gastos e resumo de sexta.
- Baixa automática por comprovante **só** com ≥ 75 pontos e 20 de vantagem; senão, conferência.
- Nada é lançado às cegas: o que o robô não tem certeza vai para a **Conferência**.
- Compras de diesel **não** entram em Gastos (decisão pendente do dono; manter fora).
- Horas extras: **não construir** (o dono ainda não definiu as regras).

## Segurança
- Nunca usar tokens, senhas ou contas reais. Telegram, e-mail e IA ficam **desligados** até o dono configurar pela tela.
- A versão de demonstração (`LEITOR_DEMO=1`) bloqueia qualquer envio externo.
- Senhas só em hash (PBKDF2-SHA256, 200.000 iterações), como no original.

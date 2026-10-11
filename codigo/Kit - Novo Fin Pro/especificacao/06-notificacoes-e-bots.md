# 06 — Notificações, sininho, resumos semanais, bots e caixa de entrada

Módulos: `app/notificacoes/` (`regras.py`, `canais.py`, `servico.py`), `app/resumo_semanal.py`, `app/entrada.py`,
`app/bot.py`, `app/empresas/entrada.py` + `empresas/bot.py`, `app/caixa/bot.py`, `app/diesel/bot.py`;
rotas `notificacoes.py`, `entrada.py`. Formato do `notificacoes.json` de fábrica: anexo **A3**.

## 6.1 Fonte dos avisos

`FonteLembretes` junta numa lista única (cada item com `tipo_pagamento`):
- boletos pendentes (`boleto`), Pix pendentes (`pix`, data prevista como vencimento),
- **cheques em carteira** a depositar (`cheque`, vindos de `empresas.servico.alertas_de_cheques`) — título
  "Cheque para depositar hoje/amanhã/em N dias/(passou da data)".

`montar_alertas(registros, hoje, dias_antes, incluir_vencidos)`: só `status == "Pendente"`; categoria `vencido`
(dias < 0), `hoje`, `amanha`, `proximos`; `fim_de_semana` (vence sábado/domingo → "pode ser pago no próximo dia útil");
`linha_digitos` = **linha digitável só com dígitos**; ordenado por categoria, vencimento, maior valor.

## 6.2 Lembretes (regras)

```json
{"id":"vencimento","tipo":"vencimento","dias":0,"horarios":["08:00","12:00","16:00"],"canais":["windows","telegram","email"],"ativo":true}
{"id":"vespera","tipo":"antes","dias":1,...}   {"id":"antecedencia","tipo":"antes","dias":3,...}
{"id":"vencidos","tipo":"vencidos","dias":30,...}      (0 = sem limite)
```
- Tipos: `vencimento` (vence hoje), `antes` (vence exatamente daqui a N dias, 1–60), `vencidos` (venceu há no máximo N
  dias, 0–365). Até 20 lembretes, 12 horários cada (`HH:MM`). `dias_semana` (0 = segunda … 6 = domingo).
- **Agendador** (a cada 60 s, `_verificar_lembretes`): para cada regra ativa, pega o **horário mais recente já passado**
  (não acumula os perdidos); chave de envio `regra|horário|id|vencimento` — cada lançamento é avisado **uma vez por
  horário por dia** (lista `notificados` do dia); agrupa por canal numa única mensagem; título traz "lembrete 2/3".
  Se o envio falhar, espera 15 min (`ultima_falha`). Pagos param de ser avisados (deixam de ser pendentes).
- `agenda(7 dias)`: a tela mostra os próximos lembretes previstos. `enviar_agora` envia já (teste de verdade).

## 6.3 Mensagem (`regras.montar_mensagem`)

Gera 4 formatos de uma vez: `resumo` (toast com até 3 itens + total), `texto` (e-mail texto), `html` (e-mail com
tabela e cores: vencido vermelho, hoje/amanhã laranja), `telegram` (HTML do Telegram: emoji por categoria 🔴🟠🟡🔵,
nome, valor, prazo, nº doc, **linha digitável em `<code>`** — tocar copia só os números — ou a chave Pix; corta em
3900 caracteres com "… e mais N"). Link "Abrir o Fin Pro" → `#/boletos?situacao=pendente`.

## 6.4 Canais (`canais.py`, só biblioteca padrão)

| Canal | Implementação |
|---|---|
| **Windows** | PowerShell com WinRT `ToastNotificationManager`; o XML do toast vai por variável de ambiente (`LEITOR_TOAST_XML`) para não quebrar com aspas/acentos; AppId do PowerShell; botões abrir (link para `/api/app/abrir?rota=…`, traz a janela) e **"Já paguei"** (marca pago) |
| **Telegram** | `_telegram(token, metodo, dados)`: `POST https://api.telegram.org/bot<token>/<metodo>` com JSON (urllib, timeout); erros mapeados em mensagens amigáveis (token inválido, bot bloqueado, chat não encontrado…). `enviar_telegram` (`sendMessage`, `parse_mode=HTML`); `procurar_chats_telegram` (pessoas e grupos que falaram com o bot nas últimas 24 h, inclusive `my_chat_member` de grupos); `baixar_arquivo_telegram` (`getFile` + download) |
| **E-mail** | `smtplib` com STARTTLS ou SSL; provedores pré-definidos (Gmail, Outlook, Yahoo); **senha de app**; vários destinatários |

Versão de demonstração: `_recusar_na_demonstracao` bloqueia Telegram e e-mail quando `LEITOR_DEMO=1`.
Tokens e senhas nunca voltam para a tela: aparecem como `••••••••` (`MASCARA`).

## 6.5 Sininho

`alertas()` = vencidos (se houver lembrete de vencidos ativo) + os que vencem dentro da **janela** (o maior "dias antes"
dos lembretes ativos, mínimo 1). Cada aviso tem `chave = id|vencimento|categoria`:
- `POST /api/notificacoes/vistos` (marca vários como vistos), `/dispensar` (some), `/restaurar` (volta os dispensados);
- como a chave inclui a **categoria**, o aviso volta a contar como novo quando muda de "amanhã" para "hoje";
- chaves de lançamentos pagos ou que mudaram são descartadas automaticamente.

## 6.6 Resumos da semana (`resumo_semanal.py`)

Config: `{"segunda": {"ativo", "horario": "08:00", "canais": ["telegram","email"]}, "sexta": {"…","17:00"}}` e
`ultimo_envio`. Saem **uma vez no dia** a partir do horário (se o computador estava desligado, saem ao abrir).
`coletar(tipo, hoje)` junta os números e `mensagem(dados, url)` escreve (separados para testar sem banco).
- **Segunda** (semana corrente): a pagar na semana (boletos e Pix), vencidos em aberto, cheques a depositar, fechamentos
  das empresas que caem na semana, quanto as empresas devem, saldo do caixa.
- **Sexta** (segunda a sexta): pago em boletos, Pix e **saídas do caixa**, maiores pagamentos, **juros e multas** (quais
  e com quantos dias de atraso), descontos, onde mais se gastou, o que entrou (caixa e recebimentos das empresas), o que
  ficou pendente (vencidos, resto da semana, semana que vem, cheques).
- `GET /api/notificacoes/resumo/{segunda|sexta}` (prévia com `html`), `POST .../enviar`.

## 6.7 Padrão comum dos bots

Todos os bots seguem o mesmo esqueleto (vale reproduzir como uma classe base):
- estado num JSON (`config` + `itens` + `conversas`), gravação atômica, `Lock`;
- thread com **long polling**: `getUpdates(offset, timeout)` a cada N segundos; `offset` salvo; processa `message`
  (texto, foto, documento) e `callback_query` (botões); `answerCallbackQuery` para tirar o "carregando";
- **quem pode usar**: lista de pessoas/grupos (`chat_id`); outros são recusados com uma explicação;
- arquivo recebido: baixa (`getFile`), calcula o **hash** (arquivo repetido é avisado e ignorado), guarda em
  `ctx.arquivos`, lê, cria um **item** com `estado` (`conversa`, `aguardando`, `pendente`, `erro`, `lancado`,
  `descartado`, `ja_lancado`…) e responde;
- o que o robô não resolve sozinho vai para a **Conferência** da tela (`GET .../bot/entrada`, `POST .../{id}/lancar`,
  `.../descartar`); contador no menu;
- itens concluídos ficam 30 dias e são limpos; arquivos de itens abertos não são apagados pela limpeza.
- `setMyCommands` registra os comandos no menu "/" do Telegram; `/start` e `/ajuda` explicam o uso.

## 6.8 Bot dos boletos + caixa de entrada (`entrada.py`, `bot.py`)

- **E-mail (IMAP)** a cada 300 s: `BODY.PEEK` (não marca como lido, não apaga), controla `UIDVALIDITY` e o último UID;
  na primeira vez olha 7 dias; filtro opcional de remetentes; lê anexos PDF/imagem.
- **Telegram** a cada 45 s: aceita arquivos das pessoas de Notificações → Telegram (token do bot das notificações).
- Cada arquivo passa por `processar_leitura`: **boleto** → item pendente para revisar e lançar (nunca lança sozinho);
  **comprovante** com escolha clara → registra o pagamento e responde com o resumo (juros, atraso); com dúvida → fica
  pendente com os candidatos; **boleto já lançado** → "Este boleto já estava lançado" e sai da caixa.
- Comandos (`bot.py`): `/vencidos`, `/hoje`, `/semana`, `/previsao`, `/resumo`, `/buscar <nome>`, `/ajuda` — listas com
  a linha digitável (só dígitos) e o Pix Copia e Cola prontos para copiar.
- Rotas: `/api/entrada` (lista, contador), `/{id}` (revisar), `/descartar`, `/verificar`, `/config` (área de
  administrador), `/{id}/registrar` (comprovante escolhendo o lançamento).

## 6.9 Bot de notas (`empresas/entrada.py`, `empresas/bot.py`) — ver capítulo 07

Polling 45 s. Quem pode enviar: lista própria (você, Almir…). Classifica o arquivo (nota, cheque, comprovante, depósito de
cheque, print de fechamento) e age. No **dia do fechamento** de cada empresa envia o fechamento. Comandos:
`/fechamento <empresa>`, `/empresas`, `/cheques`, `/notas <empresa>`, `/ajuda`.

## 6.10 Bot do caixa (`caixa/bot.py`) — conversa por etapas

Pessoas: as dos bots de boletos e de notas. Polling 20 s. Para cada foto:
1. lê o cupom (`caixa/leitura.py`: valor **a pagar/total**, nunca dinheiro entregue nem troco; data, hora, loja);
2. etapa `valor` (se não leu) → `onde` ("Onde foi gasto?", botão `onde:lido` com o nome da loja) → `centro`
   (centros ativos como botões `cc:<índice>` + `cc:novo`) → `novo_centro` → `confirmar_novo` (`cc:criar` / `cc:lista`);
3. item `pendente` na **Caixa → Conferência**, já preenchido, para Lançar ou Revisar.
Comandos: `/resumo` (hoje e mês), `/cancelar`, `/ajuda`.

## 6.11 Bot do diesel (`diesel/bot.py`) — protocolo dos botões

Pessoas: as dos outros bots. **Gestores** ("quem escolhe a máquina"); sem gestor, quem mandou decide. Polling 20 s.
| Botão (`callback_data`) | Efeito |
|---|---|
| `tipo:<item>:compra` / `tipo:<item>:canhoto` | quando a leitura não decidiu o tipo |
| `lit:<item>:1000` | atalho de 1.000 L na compra |
| `maq:<item>:<índice>` | máquina da **linha atual** do canhoto (máquinas do combustível da linha primeiro; a da placa vem com ✔) |
| `comb:<item>:<i>` | escolhe o combustível de uma linha que não diz qual |
| `nova:<item>` | cadastrar máquina nova (próxima mensagem = nome; medidor deduzido do tipo) |
| `corr:<item>` | corrigir os litros |
| `pular:<item>` | pular o horímetro/km |
| `desc:<item>` | descartar |
Fluxo do canhoto: as linhas lidas ficam em `respostas.linhas` com `atual`; para cada linha pergunta "Linha i de N —
<combustível> · <litros>: de qual máquina?", depois o medidor; ao terminar, `servico.lancar_canhoto` e envia aos
gestores: cada linha lançada, **saldo em R$**, média de cada máquina e, se abaixo do limite, "⚠️ Diesel acabando:
restam só R$ X". Quem mandou é avisado. Relatórios automáticos e comandos: capítulo 08.

## 6.12 Testes de referência
`test_notificacoes.py`, `test_sino.py`, `test_resumo_semanal.py`, `test_telegram_destinatarios.py`, `test_bot.py`,
`test_entrada.py`, `test_empresas_bot.py`, `test_caixa.py`, `test_diesel.py`, `test_diesel_relatorio.py`.

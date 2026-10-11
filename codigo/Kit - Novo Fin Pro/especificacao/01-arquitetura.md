# 01 — Arquitetura

## 1.1 Visão em uma frase

Um **servidor HTTP local em Python (FastAPI)** que guarda os dados em **SQLite** (com planilhas Excel geradas
automaticamente), lê documentos com **código de barras + texto do PDF + OCR local**, conversa com o **Telegram** e o
**e-mail**, e serve uma **interface web sem etapa de build** (HTML + JavaScript em módulos ES + CSS), aberta numa
**janela própria do Windows** (WebView2) com ícone na bandeja.

```
┌──────────────────────────── processo único (python -m app) ─────────────────────────────┐
│                                                                                         │
│  desktop.py ── janela pywebview (WebView2) ──► http://127.0.0.1:8000  ◄── navegador/celular│
│      │         ícone na bandeja (pystray)                │                                │
│      ▼                                                   ▼                                │
│  uvicorn (thread) ─► FastAPI app (main.py) ─► middleware de acesso ─► rotas/*.py          │
│                                     │                                                    │
│            contexto.py (objetos únicos): bancos, repositórios, serviços, bots            │
│                                     │                                                    │
│   threads de fundo: sincronização Excel (×3) · fila de gravação · agendador de lembretes │
│   · caixa de entrada (IMAP 5 min / Telegram 45 s) · bot de notas (45 s) · bot do caixa   │
│   (20 s) · bot do diesel (20 s) · backup diário · vigia da rede (60 s) · aquecer OCR      │
│                                     │                                                    │
│   dados/  boletos.db · empresas.db · diesel.db · *.xlsx · arquivos/ · *.json · backups/  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Tecnologias e por que cada uma

| Camada | Biblioteca (versão mínima) | Uso |
|---|---|---|
| Servidor | `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `python-multipart`, `python-dotenv` | API, upload de arquivos, `.env` |
| Banco | `sqlite3` (biblioteca padrão) | Fonte da verdade, modo WAL |
| Planilhas | `openpyxl>=3.1`, `xlrd>=2.0.1` | Gerar `.xlsx`; ler `.xls` na importação |
| PDF | `pypdfium2>=4.30` | Texto com posição de cada caractere + renderização das páginas em imagem |
| Código de barras | `zxing-cpp>=2.2` | ITF (boleto) e QR code (Pix) |
| Imagens | `pillow>=10.4`, `pillow-heif>=0.18`, `numpy`, `opencv-python>=4.10` | Abrir JPG/PNG/WEBP/HEIC, modo scanner (perspectiva) |
| OCR | `rapidocr>=3.4` (modelo latino PP-OCRv5), `rapidocr_onnxruntime>=1.3` (reserva) | Texto de fotos e PDFs escaneados, 100% local |
| PDF de relatórios | `reportlab>=4` | Fechamento do mês e das empresas em PDF |
| QR do celular | `segno>=1.6` | QR code do endereço na tela "Acesso pelo celular" |
| Desktop | `pywebview>=5.3`, `pystray>=0.19` | Janela WebView2 e ícone na bandeja |
| IA (opcional) | `anthropic>=1.0` | Leitura assistida de fotos difíceis |
| Testes | `pytest>=8`, `httpx>=0.27`, `playwright>=1.40` | Unidade, API e telas (usa o Edge instalado) |

Requisito: **Python 3.10+** no Windows 10/11. Canais externos: Telegram Bot API (HTTPS via `urllib`), SMTP
(`smtplib`) e IMAP (`imaplib`), todos da biblioteca padrão. Notificação do Windows: PowerShell + WinRT (toast XML).

## 1.3 Pastas do projeto

```
Leitor_de_Boletos/
  iniciar.bat              cria .venv, instala requirements e abre (pythonw -m app)
  demonstracao.bat         versão de demonstração (porta 8010, dados_demo)
  requirements.txt
  .env / .env.example      variáveis (ver A3)
  app/                     back-end (ver A4 — mapa completo)
    __main__.py            ponto de entrada: app | --bandeja | --navegador
    main.py                cria a FastAPI, middlewares, lifespan (liga/desliga serviços), inclui rotas
    contexto.py            objetos únicos compartilhados (bancos, repositórios, serviços)
    config.py              variáveis e caminhos
    banco.py               BancoBoletos: SQLite + planilha sincronizada (usado 3 vezes)
    planilha.py            formato das abas (DefinicaoAba, Coluna), histórico, leitura/escrita do Excel
    repositorio.py         RepositorioBoletos (banco + fila) e FonteLembretes
    fila_gravacao.py       fila de gravação quando o Excel está aberto (legado da era planilha)
    boleto/                leitura de boletos (codigo, texto, leitores, ocr, imagem, extrator, bancos)
    comprovante.py         reconhecer/extrair comprovantes e achar o lançamento
    servico_leitura.py     leitura de arquivo (boleto → Pix → comprovante) usada pela tela e pelos bots
    servico_comprovante.py registrar pagamento a partir de comprovante
    servicos.py            filtros, resumo de listas, painel, previsão, análise de gastos, exportações
    fechamento.py          fechamento do mês (Excel, PDF, ZIP)
    relatorio_geral.py     relatório geral do mês (central de Relatórios)
    busca_comprovantes.py  central de comprovantes
    pix.py                 chaves, BR Code (Copia e Cola), CRC16, QR
    importacao.py          importar boletos de outro sistema
    notificacoes/          regras, canais, serviço (agendador), resumos via resumo_semanal.py
    entrada.py             caixa de entrada: e-mail (IMAP) e Telegram dos boletos
    bot.py                 comandos do bot dos boletos
    empresas/              modelos, servico, leitura, relatorio, entrada (bot de notas), bot, configuracao
    caixa/                 servico, leitura (cupom), bot
    diesel/                modelos, servico, leitura (canhoto), precos, bot, relatorio (3 níveis)
    usuarios.py, admin.py, acesso.py, rede.py   acesso e segurança
    backup.py, saude.py, registro_log.py, tarefas.py, arquivos.py
    desktop.py, janela.py, preferencias.py, inicializacao.py, atalhos.py
    demonstracao.py        monta dados de exemplo
    rotas/                 uma rota por assunto (ver A1)
  web/                     front-end (ver A5 e capítulo 10)
    index.html, css/app.css, js/app.js (roteador), js/*.js (apoio), js/views/<tela>/...
  tests/                   273 testes (ver A6) + gerador de boletos de exemplo + corpus
  ferramentas/gerar_especificacao.py
  dados/                   dados reais (NUNCA versionar)
  dados_demo/              dados da demonstração
```

## 1.4 Ponto de entrada e modos de execução (`app/__main__.py`)

1. Sem console (pythonw): a saída vai para `dados/leitor.log` (`ArquivoRotativo`, 2 MB × 5).
2. Se a porta já está ocupada (outra instância): chama `POST /api/app/mostrar` para trazer a janela e sai.
3. Modo **aplicativo** (padrão): `desktop.executar()` → servidor uvicorn numa thread + janela pywebview + bandeja.
   `--bandeja` inicia só o ícone (usado no "iniciar com o Windows minimizado").
4. Modo **navegador** (`--navegador` ou `LEITOR_MODO=navegador`, ou sem pywebview): `uvicorn.run` e abre o navegador.
5. Demonstração: `python -m app.demonstracao` define `LEITOR_DADOS_DIR=dados_demo`, `LEITOR_PORT=8010`,
   `LEITOR_DEMO=1` antes de importar a aplicação.

## 1.5 Objetos compartilhados (`app/contexto.py`)

Criados **uma vez** na importação. As rotas e serviços acessam sempre por `ctx.<nome>` **no momento da chamada**
(nunca `from contexto import x`), para os testes poderem trocar por versões temporárias (`monkeypatch`).

| Objeto | Classe | Conteúdo |
|---|---|---|
| `planilha` | `BancoBoletos(boletos.db, boletos.xlsx, backups)` | abas `boletos`, `pix`, `caixa` + centros + histórico |
| `fila` | `FilaGravacao` | gravações pendentes (`gravacao_pendente.json`) |
| `repositorio`, `repositorio_pix`, `repositorio_caixa` | `RepositorioBoletos(planilha, fila, aba)` | acesso por aba, inclui pendentes da fila |
| `arquivos` | `RepositorioArquivos(dados/arquivos)` | originais + prévia JPEG, id hexadecimal de 32 caracteres |
| `importacoes`, `modelos_importacao` | importação | arquivos em análise e mapeamentos salvos |
| `administrador` | `GerenciadorAdmin(admin.json)` | senha de administrador |
| `usuarios` | `GerenciadorUsuarios(usuarios.json)` | usuários, sessões |
| `tarefas` | `GerenciadorTarefas(max_paralelo=2)` | leituras em segundo plano |
| `empresas` | `BancoBoletos(empresas.db, fechamentos.xlsx, abas=ABAS_EMPRESAS, centros=False)` | empresas, notas, cheques, recebimentos |
| `empresas_config` | `ConfigEmpresas(empresas.json)` | minha empresa, dia do fechamento, bot de notas |
| `diesel` | `BancoBoletos(diesel.db, diesel.xlsx, abas=ABAS_DIESEL, centros=False)` | máquinas, compras, abastecimentos |
| `notificacoes` | `ServicoNotificacoes(FonteLembretes(repositorio, repositorio_pix, cheques), …)` | lembretes, canais, resumos |
| `backup` | `GerenciadorBackup(…, extras=[empresas, diesel], pasta_codigo=BASE_DIR, informar_versao, gerar_bundle, verificar_bundle)` | backup total: 3 bancos, arquivos, configurações, código-fonte e histórico de versões (11.1) |
| `caixa_entrada`, `empresas_entrada`, `caixa_bot`, `diesel_bot`, `rede` | criados em `main.py` | bots, caixa de entrada, acesso pela rede |

## 1.6 Ciclo de vida do servidor (`main.lifespan`)

Ao iniciar, nesta ordem:
1. Se "pedir login ao abrir" está ligado: encerra as sessões deste computador.
2. `repositorio.garantir()` (migra a planilha antiga para o banco, se for a primeira vez) e `planilha.migrar()`.
3. `empresas.garantir()` e `diesel.garantir()` (cria bancos/planilhas).
4. Limpa arquivos temporários não referenciados há mais de `LEITOR_DIAS_ARQUIVOS_TEMP` dias (varre `arquivo` e
   `comprovante` de todas as abas dos 3 bancos e os arquivos em uso nas caixas de entrada/bots).
5. Conclui itens da caixa de entrada cujos boletos já foram lançados.
6. Aquece o OCR numa thread (carrega os modelos).
7. Inicia: fila de gravação; sincronização Excel dos 3 bancos; (se `NOTIFICACOES_AUTOMATICAS`) bot de notas, bot do
   caixa, bot do diesel, caixa de entrada, agendador de lembretes; (se `BACKUP_AUTOMATICO`) backup; acesso pela rede.

Ao encerrar, para tudo na ordem inversa e grava a planilha pendente.

## 1.7 Middlewares e erros

- `acesso.middleware`: autenticação e permissão por rota (capítulo 09).
- `_sem_cache_na_interface`: arquivos fora de `/api/` com `Cache-Control: no-store, must-revalidate`
  (o WebView2 reaproveitava telas antigas).
- `PlanilhaBloqueadaError` → HTTP **423** `{"codigo":"planilha_bloqueada"}`.
- `RegistroNaoEncontrado` → HTTP **404** `{"codigo":"nao_encontrado"}`.
- Erros de regra (`ErroEmpresas`, `ErroDiesel`, `ErroCaixa`, `ErroPix`…) viram **422** com mensagem pronta para a pessoa ler.
- Formato de erro padrão de todas as rotas: `{"detail": {"codigo": "...", "mensagem": "..."}}` (`rotas/comum.erro`).
- Downloads: `rotas/comum.anexo(conteudo, tipo, nome)` com `Content-Disposition` UTF-8.

## 1.8 Threads e intervalos

| Thread | Intervalo | Onde |
|---|---|---|
| Sincronização Excel (×3) | espera alteração ou 15 s; agrupa 1,5 s | `banco.BancoBoletos.iniciar_sincronizacao` |
| Agendador de lembretes e resumos | 60 s (espera inicial 20 s) | `notificacoes/servico.py` |
| Caixa de entrada | e-mail 300 s, Telegram 45 s | `entrada.py` |
| Bot de notas | 45 s (+ envio do fechamento no dia) | `empresas/entrada.py` |
| Bot do caixa | 20 s | `caixa/bot.py` |
| Bot do diesel | 20 s (+ relatórios automáticos) | `diesel/bot.py` |
| Backup externo | verifica periodicamente; 1×/dia após o horário | `backup.py` |
| Vigia da rede | 60 s | `rede.py` |
| Leituras | pool de 2 | `tarefas.py` |

Todos os bots usam **long polling** do Telegram (`getUpdates` com `offset` guardado no JSON do bot), nunca webhook —
por isso **dois sistemas com o mesmo token disputam as mensagens** (cuidado ao migrar para a nuvem).

## 1.9 Convenções de código

- Tudo em **português** (nomes, mensagens, comentários), mensagens de erro prontas para o usuário final.
- Datas: `date`/`datetime` em Python; ISO (`AAAA-MM-DD`) na API; `dd/mm/aaaa` na tela e nas mensagens.
- Dinheiro: `float` com 2 casas no banco; `Decimal` na leitura do código de barras; formato `R$ 1.234,56`.
- Números de NF/pedido/cheque comparados **sem zeros à esquerda** (`006859` = `6859`).
- Textos comparados **normalizados** (sem acento, minúsculos, espaços simples).
- Cada módulo começa com uma docstring explicando *o que faz e por quê* (o anexo A4 reproduz todas).

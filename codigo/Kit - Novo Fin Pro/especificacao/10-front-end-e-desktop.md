# 10 — Front-end (telas) e aplicativo de desktop

Arquivos: `web/index.html`, `web/css/app.css`, `web/js/*.js`, `web/js/views/<tela>/…`, `web/manifest.json`,
`web/icons/`. Lista completa com o que cada arquivo exporta: anexo **A5**. Back-end do desktop: `app/desktop.py`,
`app/janela.py`, `app/preferencias.py`, `app/inicializacao.py`, `app/atalhos.py`.

## 10.1 Princípios

- **Sem etapa de build**: HTML + CSS + JavaScript em **módulos ES** nativos, servidos pelo próprio FastAPI
  (`StaticFiles`). Nada de npm/webpack. Ícones SVG inline (`icons.js`, função `icone(nome, tamanho)`).
- **SPA com roteamento por hash** (`#/painel`, `#/boletos?situacao=pendente`, `#/diesel?aba=relatorios`…).
- Cada tela é um módulo com `export async function montar(el, params)` e `export function desmontar()`
  (remove os ouvintes de eventos). `params` é um `URLSearchParams` do hash.
- Estado de cada tela num objeto exportado (`tela`, em `estado.js` da pasta da tela), compartilhado pelos submódulos;
  telas grandes divididas por assunto (montagem, lista, formulários, eventos…).
- Tudo responsivo (largura de celular sem rolagem lateral), tema claro/escuro por variáveis CSS.

## 10.2 Casca (`index.html`)

- Script inline aplica o tema antes de desenhar (`localStorage.tema` ou `prefers-color-scheme`) em
  `document.documentElement.dataset.theme` (evita "piscar").
- `aside.sidebar`: marca, menu (`<a href="#/rota" data-rota="rota">` com ícone `data-icone` e contadores
  `data-contador-ler`, `-entrada`, `-caixa`, `-diesel`, `-empresas`, `-notif`), status do sistema (planilha, OCR, IA,
  backup, usuário conectado, selo de demonstração), botão de tema.
- Topo: botão de menu (celular), título e subtítulo da página, **sininho** (`#btn-sino`, `#sino-badge`,
  `#painel-sino`), atalho "Ler boletos".
- `#aviso-gravacao` (planilha aguardando gravação), `main#view` (onde a tela é montada), sobreposição de "soltar
  arquivo", `#toasts`, `#modais`. Fontes Inter e JetBrains Mono (Google Fonts).

## 10.3 Roteador e serviços globais (`web/js/app.js`)

O `app.js` é a casca da aplicação (o único arquivo não reproduzido no anexo A5). Responsabilidades, como implementadas
hoje:
1. **Tabela de rotas** `rota → {módulo da tela, título, subtítulo, permissão}`: `painel`, `ler`, `boletos`, `pix`,
   `comprovantes`, `caixa` (caixa), `diesel` (diesel), `gastos` (gastos), `empresas` (empresas), `notificacoes`,
   `config`. Ao mudar o hash: `desmontar()` da tela anterior, `montar()` da nova, marca o link ativo, atualiza o título.
   **Para ligar a central de Relatórios**: importar `./views/relatorios.js`, acrescentar a rota `relatorios`
   (título "Relatórios", sem permissão própria — cada quadro já é filtrado pelo servidor) e o link no menu, logo abaixo de
   Gastos: `<a href="#/relatorios" data-rota="relatorios"><span data-icone="relatorio"></span>Relatórios</a>`.
2. **Acesso**: ao abrir, `GET /api/acesso/estado` em `estado.acesso`; esconde do menu as telas sem permissão (`pode`);
   tela de login (usuário e senha, ou senha da rede) quando o servidor responde 401 (evento `acesso:necessario`
   disparado por `api.js`); troca da própria senha e "sair" no menu lateral.
3. **Status** (`GET /api/status` em `estado.status`): versão, OCR, IA, HEIC, planilha, gravação pendente, demonstração.
4. **Contadores do menu** (atualizados periodicamente): arquivos na caixa de entrada, conferências do caixa, diesel e
   empresas (as telas também emitem `diesel:contagem` etc.), avisos do sininho.
5. **Sininho**: `GET /api/notificacoes` (traz os avisos com `chave`, `visto`, `dispensado`), lista por categoria, marcar como visto ao abrir (`POST /api/notificacoes/vistos`), dispensar, restaurar.
6. **Arrastar e soltar arquivos em qualquer tela**: mostra a sobreposição com o texto de `document.body.dataset.soltar`
   (a tela pode trocar, ex.: "Solte para ler o canhoto ou o comprovante"); ao soltar, dispara o evento **cancelável**
   `arquivos:soltos` (com os arquivos em `detail`); se nenhuma tela chamar `preventDefault()`, leva os arquivos para
   **Ler boletos**.
7. **Colar (`Ctrl+V`)**: imagem → Ler boletos; texto que é linha digitável → leitura da linha; texto que é Pix Copia e
   Cola → tela Pix preenchida.
8. **Atalhos**: `Alt+1…7` (Painel, Ler, Boletos, Pix, Gastos, Notificações, Configurações), `/` (busca da tela),
   `Esc` (fecha modal).
9. **Tema** (botão; salvo em `localStorage.tema`).

## 10.4 Módulos de apoio

| Arquivo | Conteúdo |
|---|---|
| `api.js` | `api.get/post/put/patch/del`; erros viram `ApiError(status, detalhe)` com `codigo`; 401 de acesso dispara `acesso:necessario`; `enviarArquivo` (síncrono) e `criarLeitura` (tarefa) com **progresso de upload** via XHR; `enviarPara(url, arquivo)`; `urlExportar(params)` |
| `ui.js` | `esc` (escapar HTML — **sempre** usar ao interpolar dados), `brl`, `numeroBR`, `compacto`, `parseValor`, `dataBR`, `dataHoraBR`, `hojeISO`, `isoDeData`, `debounce`, `mensagemErro`, `toast` (com ação, ex.: Desfazer), `copiar`, `abrirModal`, `confirmar`, `pedirTexto`, `seloSituacao`, `seloFonte`, `SITUACOES`, `FONTES` |
| `estado.js` | `estado` (status, acesso), `pode(permissao)` (sem usuário logado = pode tudo), `ehAdministrador()` |
| `centros.js` | cache dos centros de custo, `<select>` com "Sem centro" e "+ Novo centro", criação na hora, `escolherCentro` (modal) |
| `detalhes.js` | modal **Histórico e comprovante** de boleto/Pix (eventos, ver/anexar/remover comprovante) |
| `admin.js` | estado e senha da área restrita |
| `grafico.js` | gráficos SVG próprios (sem biblioteca): `montarGrafico` (pago/vencido/a vencer por mês) e `montarGraficoSeries` (barras empilhadas com dica ao passar o mouse) |
| `icons.js` | ícones SVG e `icone(nome, tamanho)` |

## 10.5 Telas (pasta `web/js/views/`)

| Tela | Arquivos | Destaques |
|---|---|---|
| Painel | `painel.js` | cartões com link, previsão de saídas (clicar na semana), gráfico, listas |
| Ler boletos | `leitura/` (`montagem`, `fila`, `render`, `lancamento`, `comprovante`, `caixa`, `eventos`, `estado`) | fila de arquivos com progresso por tarefa (`GET /api/leituras/tarefas/{id}` em polling), cartões de revisão com campos amarelos, sugestões de linha, IA, "Lançar como Pix", comprovante com candidatos e Desfazer, **Recebidos por e-mail e Telegram** |
| Boletos lançados | `boletos/` (`lista`, `calendario`, `edicao`, `montagem`, `estado`) | filtros, resumo com juros, seleção em lote, calendário mensal, copiar linha **só dígitos** |
| Pagamentos Pix | `pix/` (`lista`, `formulario`, `chaves`, `montagem`, `estado`) | máscaras e validação de chave, Copia e Cola, QR |
| Comprovantes | `comprovantes.js` | filtros, chips de tipo, visualizador com setas, ZIP, "Pagos sem comprovante" + Anexar |
| Caixa | `caixa/` (`movimento`, `relatorios`, `conferencia`, `configbot`, `montagem`, `estado`) | abas Movimento/Relatórios/Conferência/Bot |
| Diesel | `diesel/` (`painel`, `relatorios`, `maquinas`, `formularios`, `conferencia`, `configbot`, `montagem`, `estado`) | saldo em R$, formulário de canhoto com várias linhas (litros × preço = total automático), relatório **Simples/Detalhado/Completo** (lembrado em `localStorage` `finpro.diesel.nivel`) com filtros por máquina e combustível; a tela reage a `arquivos:soltos` |
| Gastos | `gastos.js` | Análise, Fechamento do mês, Centros de custo |
| Relatórios | `relatorios.js` | relatório geral do mês e atalhos para todos os relatórios (aguardando a rota no `app.js`) |
| Empresas | `empresas/` (`fechamentos`, `notas`, `cheques`, `recebimentos`, `conferencia`, `configbot`, `comum`, `montagem`, `estado`) | fechamento no formato Prospera, mover NF de fechamento, **Depositei**, recebimento com "Cheque depositado" |
| Notificações | `notificacoes.js` | lembretes (horários e canais), canais, resumos (Ver como fica / Enviar agora), agenda, histórico |
| Configurações | `configuracoes/` (`aplicativo`, `usuarios`, `rede`, `importacao`, `backup`, `entrada`, `saude`, `eventos`, `tela`, `index`) | abas Geral, Usuários e acesso, Backup e recebimento, Saúde |

## 10.6 Estilos (`app.css`)

Variáveis em `:root` (tema claro) e `[data-theme=dark]` (escuro): `--fundo`, `--superficie(-2/-3)`, `--borda(-forte)`,
`--texto(-2/-3)`, `--marca` (#0d7a64) e variações, `--ok`, `--aviso`, `--erro`, `--info` (+ `-suave`), `--raio`, fontes.
Componentes reutilizáveis: `.card`, `.btn` (`-primario`, `-fantasma`, `-sm`), `.btn-icone`, `.chip` (ok/erro/aviso/info),
`.resumo-lista`/`.resumo-item` (cartões de números), `.tabela`/`.tabela-wrap` (no celular vira lista usando `data-rotulo`),
`.alternar-modo`/`.sub-abas`, `.barra-filtros`/`.filtros-linha`, `.alerta`, `.vazio`, `.esqueleto` (carregando),
`.caixa-barras` (barras horizontais). Valores no anexo A5.

## 10.7 Aplicativo de desktop (`app/desktop.py`)

- `pywebview` com o motor **WebView2** (Edge) — janela própria "Fin Pro", ícone `web/icons/app.ico`; `pystray` para o
  ícone na bandeja (abrir telas, sair). AppUserModelID próprio (notificações agrupadas).
- O servidor uvicorn roda numa **thread** do mesmo processo.
- **Fechar (X) esconde** na bandeja (lembretes continuam) — preferência `fechar_para_bandeja` em `dados/app.json`;
  `minimizado_ao_iniciar`; aviso na primeira vez.
- `janela.py`: ponte para a API trazer a janela para a frente (`/api/app/mostrar`, `/api/app/abrir?rota=` usado pelas
  notificações) e encerrar (`POST /api/app/sair` — reinício limpo usado nas atualizações).
- **Cache do WebView2**: guarda HTML/JS/CSS e mostrava telas antigas depois de atualizar. Solução dupla:
  (1) `Cache-Control: no-store` nas telas; (2) ao abrir, compara uma impressão dos arquivos de `web/` com
  `dados/webview/versao_interface.txt` e, se mudou, apaga só o cache de arquivos (mantém preferências).
- `inicializacao.py`: script na pasta Inicializar do Windows (abrir o app ou só a bandeja ao ligar o computador).
- `atalhos.py`: atalhos na Área de Trabalho e no Menu Iniciar (remove os de nome antigo "Leitor de Boletos").
- PWA: `manifest.json` + ícones permitem "Instalar" pelo Chrome/Edge (útil na versão online).

## 10.8 Testes de tela
`tests/test_telas.py` (Playwright com o Edge instalado): abre todas as telas, lê um boleto, dá baixa por comprovante,
confere o painel; `test_desktop_cache.py` (limpeza do cache do WebView2).

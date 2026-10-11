# Anexo A5 — Front-end (arquivos, telas e estilos)

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Front-end sem etapa de build: `web/index.html` carrega `web/js/app.js` como módulo ES; cada tela é um módulo em `web/js/views/` que exporta `montar(el, params)` e, opcionalmente, `desmontar()`. Estilos em `web/css/app.css` (variáveis de cor em `:root`, tema escuro em `[data-theme=dark]`).

| Arquivo | Linhas | O que faz | Exporta |
|---|---|---|---|
| `web/css/app.css` | 1771 | ========================================================================== |  |
| `web/index.html` | 89 |  |  |
| `web/js/admin.js` | 52 | Senha de administrador: libera as áreas restritas (importação de boletos). A conferência é feita no servidor. | estadoAdmin, bloquearAdmin, pedirSenhaAdmin |
| `web/js/api.js` | 99 | Cliente da API do servidor. | ApiError, api |
| `web/js/app.js` | — | Roteador e casca da aplicação (descrito no capítulo 10) | — |
| `web/js/centros.js` | 108 | Centros de custo ("onde foi gasto"): lista compartilhada entre as telas, opções de seleção e cadastro rápido. | NOVO_CENTRO, SEM_CENTRO, carregarCentros, invalidarCentros, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro, escolherCentro |
| `web/js/detalhes.js` | 134 | Janela "Histórico e comprovante" de um boleto ou Pix: quem lançou, quem pagou, comprovante e todas as alterações. | anexarComprovante, abrirDetalhes |
| `web/js/estado.js` | 16 | Estado compartilhado entre as telas. | estado, pode, ehAdministrador |
| `web/js/grafico.js` | 153 | Gráfico de barras empilhadas (SVG) com tooltip. | montarGrafico, montarGraficoSeries, LEGENDA_GRAFICO |
| `web/js/icons.js` | 83 | Ícones SVG em linha (traço), no estilo "outline". | icone, hidratarIcones |
| `web/js/ui.js` | 230 | Utilitários de interface: formatação, toasts, modais e selos. | esc, MESES, brl, numeroBR, compacto, parseValor, dataBR, dataHoraBR, hojeISO, isoDeData, tamanhoArquivo, uid, debounce, mensagemErro, toast, copiar, abrirModal, confirmar, pedirTexto, SITUACOES, seloSituacao, FONTES, seloFonte |
| `web/js/views/boletos/calendario.js` | 163 | Boletos lançados · calendário de vencimentos. | intervaloDaGrade, carregarCalendario, resumoDoMes, renderizarCalendario, aoClicarCalendario, abrirDia |
| `web/js/views/boletos/edicao.js` | 97 | Boletos lançados · edição de um boleto. | abrirEdicao |
| `web/js/views/boletos/estado.js` | 35 | Boletos lançados · estado compartilhado pelos módulos da tela (filtros, seleção e modo de exibição). | filtros, CHIPS, COLUNAS, NOMES_MES, DIAS_CAL, selecionados, inicioDoMes, tela |
| `web/js/views/boletos/index.js` | 2 | Boletos lançados: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/boletos/lista.js` | 320 | Boletos lançados · lista, paginação e ações em lote. | carregar, renderizarResumo, cabecalho, linha, renderizarTabela, renderizarPaginacao, renderizarAcoesLote, aoMarcar, aoPaginar, alterarStatus, confirmarPagamento, executarAcao, aoClicarTabela, aoAcaoLote |
| `web/js/views/boletos/montagem.js` | 212 | Boletos lançados · montagem da tela, filtros e eventos. | montar, desmontar, recarregarExterno, sincronizarControles, atalhoBusca, fecharMenuFora, ligarEventos, aplicarPeriodoRapido |
| `web/js/views/caixa/conferencia.js` | 86 | Caixa · conferência do que chegou pelo bot do caixa: tudo preenchido, só revisar e lançar. | carregarConferencia, htmlConferencia, revisarItem, lancarItem, descartarItem |
| `web/js/views/caixa/configbot.js` | 68 | Caixa · configuração do bot do caixa (token e quem pode usar — vem dos outros dois bots). | htmlBotCaixa, salvarBotCaixa, verificarBotCaixa |
| `web/js/views/caixa/estado.js` | 20 | Caixa · estado compartilhado pelos módulos da tela. | ABAS, PERIODOS, tela |
| `web/js/views/caixa/index.js` | 2 | Caixa: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/caixa/montagem.js` | 125 | Caixa · montagem da tela em abas, escolha do período (dia, semana, mês, ano) e eventos. | montar, desmontar |
| `web/js/views/caixa/movimento.js` | 175 | Caixa · movimento do período: totais, lançamentos e o formulário de entrada/saída. | htmlKpis, htmlMovimento, formularioLancamento, editarLancamento, cancelarLancamento, historicoLancamento |
| `web/js/views/caixa/relatorios.js` | 54 | Caixa · relatórios do período: onde mais se gastou, centros de custo, pessoas, pedidos e a evolução. | htmlRelatorios, desenharGraficos |
| `web/js/views/comprovantes.js` | 386 | Tela: Comprovantes — acha o comprovante de boletos, Pix, cheques, recebimentos, caixa e notas fiscais. | montar, desmontar |
| `web/js/views/configuracoes/aplicativo.js` | 65 | Configurações · Aplicativo no computador. | opcaoAplicativo, htmlAplicativo, atualizarAplicativo, alterarAplicativo |
| `web/js/views/configuracoes/backup.js` | 201 | Configurações · Backup total fora do computador: dados, comprovantes, configurações, código-fonte e versões. | SITUACAO_BACKUP, htmlBackup, atualizarBackup, carregarStatusLateral, acaoBackup, salvarBackup |
| `web/js/views/configuracoes/entrada.js` | 115 | Configurações · Receber boletos e comprovantes por e-mail e Telegram. | PROVEDORES_IMAP, linhaVerificacao, htmlEntrada, atualizarEntrada, acaoEntrada, salvarEmail |
| `web/js/views/configuracoes/eventos.js` | 153 | Configurações · Cliques, alterações e formulários da tela de Configurações. | aoClicar, aoAlterar, aoEnviar |
| `web/js/views/configuracoes/importacao.js` | 136 | Configurações · Importação de boletos e senha de administrador (área restrita). | htmlImportacao, atualizarAdmin, acaoAdmin, criarSenhaAdmin, trocarSenhaAdmin |
| `web/js/views/configuracoes/index.js` | 176 | Tela: Configurações, em abas — Geral (com a versão do sistema) · Usuários e acesso · Backup e recebimento · Saúde do sistema. | montar, desmontar |
| `web/js/views/configuracoes/rede.js` | 100 | Configurações · Acesso pelo celular (rede Wi-Fi). | textoSituacao, htmlRede, atualizarRede |
| `web/js/views/configuracoes/saude.js` | 96 | Configurações · Saúde do sistema: o que roda sozinho está funcionando? (atualiza a cada 30 segundos) | htmlSaude, carregarSaude, iniciarSaude, pararSaude, aoClicarSaude |
| `web/js/views/configuracoes/tela.js` | 2 | Estado compartilhado pelos cartões da tela de Configurações. | tela |
| `web/js/views/configuracoes/usuarios.js` | 184 | Configurações · Usuários do escritório (área restrita). | htmlUsuarios, atualizarUsuarios, acaoUsuario, criarUsuario |
| `web/js/views/configuracoes/versao.js` | 50 | Configurações · Versão do sistema: qual versão está em uso, o que mudou em cada uma e se há algo ainda não guardado. | htmlVersao |
| `web/js/views/diesel/conferencia.js` | 76 | Diesel · conferência do que chegou pelo bot: canhotos esperando a máquina e compras para conferir. | carregarConferencia, htmlConferencia, conferir, descartar |
| `web/js/views/diesel/configbot.js` | 105 | Diesel · configuração do bot do diesel: token, quem escolhe a máquina, relatórios automáticos e alerta de saldo. | htmlBotDiesel, salvarBotDiesel, verificarBotDiesel |
| `web/js/views/diesel/estado.js` | 29 | Diesel · estado compartilhado pelos módulos da tela. | ABAS, PERIODOS, TIPOS_MAQUINA, COMBUSTIVEIS, MEDIDORES, tela, litros, numero |
| `web/js/views/diesel/formularios.js` | 462 | Diesel · formulários: canhoto (uma ou mais linhas de combustível), compra, abastecimento, máquina e preços. | carregarMaquinas, carregarPrecos, formularioCanhoto, formularioCompra, formularioAbastecimento, formularioMaquina, formularioPrecos, lerArquivo |
| `web/js/views/diesel/index.js` | 2 | Diesel: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/diesel/maquinas.js` | 39 | Diesel · máquinas: cadastro e a média de cada uma (últimos 30 dias). | htmlMaquinas |
| `web/js/views/diesel/montagem.js` | 177 | Diesel · montagem da tela em abas, escolha do período (semana, quinzena, mês, ano) e eventos. | montar, desmontar |
| `web/js/views/diesel/painel.js` | 139 | Diesel · painel do período: saldo, comprado x abastecido, consumo por máquina e os lançamentos. | htmlKpis, barrasMaquinas, htmlPainel, editar, cancelar, historico |
| `web/js/views/diesel/relatorios.js` | 358 | Diesel · relatório do período (semana, quinzena, mês ou ano) em três níveis: | NIVEIS, relatorio, escolherNivel, htmlRelatorios, desenharGraficoDiesel, enviarRelatorio |
| `web/js/views/empresas/cheques.js` | 162 | Empresas e fechamentos · cheques pré-datados (guardar, avisar o vencimento e dar baixa ao compensar). | htmlCheques, formularioCheque, abrirCheque, compensarCheque |
| `web/js/views/empresas/comum.js` | 76 | Empresas e fechamentos · funções usadas pelos vários módulos da tela. | SITUACOES, selo, opcoesEmpresa, opcoes, opcoesCompetencia, tituloCompetencia, numero, tentar, deuCerto, carregarDados, vazio |
| `web/js/views/empresas/conferencia.js` | 193 | Empresas e fechamentos · conferência do que o bot de notas recebeu e importação do print do fechamento. | htmlConferencia, conferir, descartarItem, enviarArquivo, importarFechamento |
| `web/js/views/empresas/configbot.js` | 192 | Empresas e fechamentos · minha empresa, dia do fechamento e o bot de notas fiscais. | htmlBot, aoEnviarFormulario, verificarBot, procurarChats, liberarChat, trazerDosAvisos, removerDestinatario, adicionarChat |
| `web/js/views/empresas/estado.js` | 28 | Empresas e fechamentos · estado compartilhado pelos módulos da tela. | ABAS, STATUS_NOTA, STATUS_CHEQUE, FORMAS, UNIDADES, tela |
| `web/js/views/empresas/fechamentos.js` | 213 | Empresas e fechamentos · cartões das empresas e o fechamento no formato da planilha usada hoje. | htmlFechamentos, abrirFechamento, htmlTabelaFechamento, formularioEmpresa, enviarFechamentos |
| `web/js/views/empresas/index.js` | 2 | Empresas e fechamentos: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/empresas/montagem.js` | 139 | Empresas e fechamentos · montagem da tela em abas e eventos. | montar, desmontar, receberArquivos |
| `web/js/views/empresas/notas.js` | 207 | Empresas e fechamentos · notas fiscais lançadas (lista, lançamento manual e edição). | htmlNotas, formularioNota, editarNota |
| `web/js/views/empresas/recebimentos.js` | 142 | Empresas e fechamentos · recebimentos (Pix, TED, depósito e cheque) com a baixa das notas. | htmlRecebimentos, formularioRecebimento, cancelarRecebimento |
| `web/js/views/gastos.js` | 485 | Tela: Gastos — quanto foi gasto em cada centro de custo (boletos + Pix) e cadastro dos centros de custo. | montar, desmontar |
| `web/js/views/importar.js` | 464 | Tela: Importar boletos de outro sistema (Excel, CSV ou TXT) — envio, colunas, prévia e importação. | montar, desmontar, receberArquivo |
| `web/js/views/leitura/caixa.js` | 127 | Ler boletos · caixa de entrada (boletos e comprovantes recebidos por e-mail e Telegram). | carregarCaixa, resumoRecebido, renderizarCaixa, revisarRecebido, aoClicarCaixa |
| `web/js/views/leitura/comprovante.js` | 98 | Ler boletos · comprovantes de pagamento lidos na tela. | rotuloCandidato, htmlEscolhaLancamento, textoPagamento, htmlComprovante, registrarComprovante, desfazerComprovante |
| `web/js/views/leitura/estado.js` | 9 | Ler boletos · estado compartilhado pelos módulos da tela (fila de arquivos e referências da tela aberta). | fila, MAX_PARALELO, EXTENSOES, ORIGENS, tela, abertosDaCaixa |
| `web/js/views/leitura/eventos.js` | 236 | Ler boletos · digitação, cliques e análise com IA. | aoDigitar, aoAlterar, aoClicar, ampliar, reanalisarLinha, camposParaIA, analisarComIA, analisarArquivoComIA |
| `web/js/views/leitura/fila.js` | 168 | Ler boletos · fila de arquivos e boletos em revisão. | enfileirar, analisarTexto, processarFila, processar, marcarRepetidosNaFila, novoBoleto, formularioDe, localizar, boletosEmRevisao, prontoParaLancar, atualizarContadorNav |
| `web/js/views/leitura/index.js` | 4 | Ler boletos: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/leitura/lancamento.js` | 145 | Ler boletos · lançamento dos boletos na planilha. | montarPayload, lancar, lancarTodos |
| `web/js/views/leitura/montagem.js` | 147 | Ler boletos · montagem da tela, eventos principais e acompanhamento das leituras. | montar, desmontar, textoCronometro, atualizarCronometros, acompanharTarefa, ligarEventos |
| `web/js/views/leitura/render.js` | 280 | Ler boletos · desenho da fila, dos arquivos e dos boletos em revisão. | renderizarFila, atualizarItem, atualizarProgresso, atualizarBoleto, atualizarBarra, htmlEstadoItem, htmlItem, htmlSemBoletos, htmlPixEncontrados, campoTexto, htmlBoleto |
| `web/js/views/notificacoes.js` | 716 | Tela: Notificações — lembretes configuráveis (dia do vencimento, antes, vencidos), canais, agenda e histórico. | montar, desmontar |
| `web/js/views/painel.js` | 226 | Tela: Painel (indicadores, gráfico e listas rápidas). | montar, desmontar |
| `web/js/views/pix/chaves.js` | 109 | Pagamentos Pix · validação e formatação das chaves Pix. | TIPOS_CHAVE, RE_EMAIL, RE_UUID, digitos, cpfValido, cnpjValido, aplicarMolde, numerosCelular, mascarar, formatarChave, validarChave, inferirTipo |
| `web/js/views/pix/estado.js` | 7 | Pagamentos Pix · estado compartilhado pelos módulos da tela. | CHIPS, COLUNAS, filtros, tela |
| `web/js/views/pix/formulario.js` | 317 | Pagamentos Pix · formulário de lançamento de Pix (tela e janela). | criarFormulario, avisarLido, abrirFormularioPix |
| `web/js/views/pix/index.js` | 4 | Pagamentos Pix: ponto de entrada (a tela é dividida em módulos nesta pasta). |  |
| `web/js/views/pix/lista.js` | 253 | Pagamentos Pix · lista de Pix lançados, pagamento e QR code. | carregar, renderizarResumo, cabecalho, linha, renderizarTabela, renderizarPaginacao, alterarStatus, confirmarPagamento, abrirQr, aoClicarTabela |
| `web/js/views/pix/montagem.js` | 237 | Pagamentos Pix · montagem da tela, leitura de QR code e Copia e Cola. | montar, desmontar, receberCopiaECola, lerArquivos, recarregarExterno, fecharMenuFora, sincronizarChips, ligarEventos, lerCodigoDaCaixa, processarArquivo, escolherPix |
| `web/js/views/relatorios.js` | 302 | Tela: Relatórios — o relatório geral do mês e o caminho para todos os relatórios do sistema, num lugar só. | montar, desmontar |
| `web/manifest.json` | 51 |  |  |
| `web/sw.js` | 4 | Service worker mínimo: permite instalar o Fin Pro como aplicativo. |  |

## Variáveis de cor e medidas (tema claro, `:root`)

| Variável | Valor |
|---|---|
| `--fonte` | `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` |
| `--mono` | `"JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace` |
| `--raio` | `14px` |
| `--raio-md` | `10px` |
| `--raio-sm` | `7px` |
| `--fundo` | `#f3f5f7` |
| `--superficie` | `#ffffff` |
| `--superficie-2` | `#f7f9fa` |
| `--superficie-3` | `#eef2f4` |
| `--borda` | `#e2e8ec` |
| `--borda-forte` | `#cbd5dc` |
| `--texto` | `#0e1a22` |
| `--texto-2` | `#4a5a66` |
| `--texto-3` | `#7d8b95` |
| `--marca` | `#0d7a64` |
| `--marca-forte` | `#09624f` |
| `--marca-suave` | `#e2f3ee` |
| `--marca-tinta` | `#065443` |
| `--ok` | `#12844a` |
| `--ok-suave` | `#e3f4e9` |
| `--aviso` | `#a86200` |
| `--aviso-suave` | `#fff2d9` |
| `--erro` | `#c3302a` |
| `--erro-suave` | `#fdebea` |
| `--info` | `#2a62c7` |
| `--info-suave` | `#e8effc` |
| `--ia` | `#7a4fd6` |
| `--ia-suave` | `#f0eafd` |
| `--sombra-sm` | `0 1px 2px rgba(16, 24, 40, .06)` |
| `--sombra` | `0 1px 2px rgba(16, 24, 40, .05), 0 10px 30px -18px rgba(16, 24, 40, .22)` |
| `--sombra-lg` | `0 30px 70px -24px rgba(16, 24, 40, .45)` |
| `--lateral` | `#0b1b1f` |
| `--lateral-2` | `#12282d` |
| `--lateral-texto` | `#9fb3b9` |
| `--lateral-ativo` | `#ffffff` |

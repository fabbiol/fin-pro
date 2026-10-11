# Anexo A9 — Telas: chamadas à API, ações, eventos e armazenamento

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Para cada arquivo do front-end: as **rotas da API** que ele chama (método e caminho — `${…}` são partes variáveis), os links de download, as **ações** dos botões (`data-acao`), os **eventos** que emite e escuta e as chaves de **armazenamento local**. Serve para conferir que cada botão da nova versão chama a rota certa.

## `web/js/admin.js`

- **API:** `GET /api/admin` · `POST /api/admin/entrar` · `POST /api/admin/sair`

## `web/js/api.js`

- **Links/downloads:** `/api/exportar` · `/api/leituras` · `/api/leituras/tarefas`
- **Emite:** `acesso:necessario`

## `web/js/centros.js`

- **API:** `GET /api/centros` · `POST /api/centros`

## `web/js/detalhes.js`

- **API:** `DELETE /api/${tipo}/${r.id}/comprovante` · `GET /api/${tipo}/${r.id}` · `GET /api/${tipo}/${r.id}/historico` · `POST (arquivo) /api/${tipo}/${id}/comprovante`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/boletos/calendario.js`

- **API:** `GET /api/boletos`
- **Ações:** `copiar` · `editar`

## `web/js/views/boletos/edicao.js`

- **API:** `PUT /api/boletos/${r.id}`
- **Links/downloads:** `/api/boletos/`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/boletos/estado.js`

- **Armazenamento local:** `"boletos_modo"`

## `web/js/views/boletos/lista.js`

- **API:** `DELETE /api/boletos/${id}` · `GET /api/boletos` · `GET /api/boletos/${id}` · `PATCH /api/boletos/${id}/status` · `PUT /api/boletos/${id}`
- **Links/downloads:** `/api/boletos/`
- **Ações:** `copiar` · `detalhes` · `editar` · `excluir` · `limpar-filtros` · `pago` · `pendente`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/boletos/montagem.js`

- **API:** `POST /api/planilha/abrir`
- **Escuta:** `boletos:atualizar`
- **Armazenamento local:** `"boletos_modo"`

## `web/js/views/caixa/conferencia.js`

- **API:** `GET /api/caixa/bot/entrada` · `POST /api/caixa/bot/entrada/${id}/descartar` · `POST /api/caixa/bot/entrada/${id}/lancar`
- **Links/downloads:** `/api/arquivos/` · `/api/caixa/bot/entrada/`
- **Ações:** `descartar-caixa` · `lancar-caixa` · `revisar-caixa`
- **Emite:** `caixa:atualizar`

## `web/js/views/caixa/configbot.js`

- **API:** `POST /api/caixa/bot/config` · `POST /api/caixa/bot/verificar`
- **Ações:** `verificar-bot-caixa`
- **Emite:** `caixa:atualizar`

## `web/js/views/caixa/montagem.js`

- **API:** `GET /api/caixa?periodo=${tela.periodo}&data=${tela.data}`
- **Links/downloads:** `/api/caixa` · `/api/caixa/relatorio/arquivo`
- **Ações:** `nova-entrada` · `nova-saida`
- **Emite:** `caixa:contagem`
- **Escuta:** `caixa:atualizar`

## `web/js/views/caixa/movimento.js`

- **API:** `GET /api/caixa/${id}/historico` · `POST /api/caixa` · `POST /api/caixa/${id}/cancelar` · `PUT /api/caixa/${r.id}`
- **Links/downloads:** `/api/caixa/`
- **Ações:** `cancelar-caixa` · `editar-caixa` · `historico-caixa`
- **Emite:** `caixa:atualizar`

## `web/js/views/comprovantes.js`

- **API:** `GET /api/comprovantes/busca`
- **Links/downloads:** `/api/arquivos/` · `/api/comprovantes/busca/zip`
- **Ações:** `limpar` · `mais-filtros`

## `web/js/views/configuracoes/aplicativo.js`

- **API:** `GET /api/app` · `POST /api/sistema/inicializacao` · `PUT /api/app/preferencias`

## `web/js/views/configuracoes/backup.js`

- **API:** `GET /api/admin` · `GET /api/backup` · `POST /api/backup/${acao}` · `POST /api/backup/agora` · `POST /api/backup/escolher-pasta` · `PUT /api/backup/config`
- **Links/downloads:** `/api/backup/`
- **Emite:** `status:atualizar`

## `web/js/views/configuracoes/entrada.js`

- **API:** `GET /api/admin` · `GET /api/entrada` · `POST /api/entrada/verificar` · `PUT /api/entrada/config`
- **Emite:** `entrada:contagem`

## `web/js/views/configuracoes/eventos.js`

- **API:** `POST /api/app/atalhos` · `POST /api/planilha/abrir` · `POST /api/planilha/abrir-pasta` · `POST /api/rede/ativar` · `POST /api/rede/senha` · `PUT /api/entrada/config` · `PUT /api/usuarios/config`
- **Emite:** `acesso:sair`

## `web/js/views/configuracoes/importacao.js`

- **API:** `GET /api/admin` · `POST /api/admin/senha`

## `web/js/views/configuracoes/index.js`

- **API:** `GET /api/acesso/estado` · `GET /api/admin` · `GET /api/app` · `GET /api/backup` · `GET /api/entrada` · `GET /api/rede` · `GET /api/saude` · `GET /api/status` · `GET /api/usuarios` · `GET /api/versao`
- **Links/downloads:** `/api/exportar`
- **Ações:** `abrir` · `pasta`

## `web/js/views/configuracoes/rede.js`

- **API:** `GET /api/rede`
- **Links/downloads:** `/api/rede/qrcode.svg`
- **Ações:** `sair`

## `web/js/views/configuracoes/saude.js`

- **API:** `GET /api/saude` · `POST /api/saude/atualizar-planilha` · `POST /api/saude/limpar-logs`

## `web/js/views/configuracoes/usuarios.js`

- **API:** `DELETE /api/usuarios/${id}` · `GET /api/admin` · `GET /api/usuarios` · `POST /api/usuarios` · `PUT /api/usuarios/${id}`
- **Links/downloads:** `/api/usuarios/`

## `web/js/views/diesel/conferencia.js`

- **API:** `GET /api/diesel/bot/entrada` · `POST /api/diesel/bot/entrada/${id}/descartar` · `POST /api/diesel/bot/entrada/${id}/lancar`
- **Links/downloads:** `/api/arquivos/` · `/api/diesel/bot/entrada/`
- **Ações:** `conferir-canhoto` · `conferir-compra` · `descartar-diesel`
- **Emite:** `diesel:atualizar`

## `web/js/views/diesel/configbot.js`

- **API:** `POST /api/diesel/bot/config` · `POST /api/diesel/bot/verificar`
- **Ações:** `verificar-bot-diesel`
- **Emite:** `diesel:atualizar`

## `web/js/views/diesel/formularios.js`

- **API:** `GET /api/diesel/maquinas` · `GET /api/diesel/precos` · `POST (arquivo) /api/diesel/analisar` · `POST (arquivo) /api/diesel/arquivo` · `POST /api/diesel/canhoto` · `POST /api/diesel/compras` · `POST /api/diesel/maquinas` · `POST /api/diesel/precos` · `PUT /api/diesel/abastecimentos/${r.id}` · `PUT /api/diesel/compras/${r.id}` · `PUT /api/diesel/maquinas/${m.id}`
- **Links/downloads:** `/api/arquivos/` · `/api/diesel/abastecimentos/` · `/api/diesel/compras/` · `/api/diesel/maquinas/`
- **Emite:** `change` · `diesel:atualizar` · `input`

## `web/js/views/diesel/maquinas.js`

- **Ações:** `editar-maquina` · `nova-maquina`

## `web/js/views/diesel/montagem.js`

- **API:** `GET ${caminho}?periodo=${tela.periodo}&data=${tela.data}`
- **Links/downloads:** `/api/diesel` · `/api/diesel/relatorio` · `/api/diesel/relatorio/arquivo`
- **Ações:** `cancelar-diesel` · `conferir-canhoto` · `conferir-compra` · `descartar-diesel` · `editar-diesel` · `editar-maquina` · `enviar-relatorio-diesel` · `historico-diesel` · `limpar-filtro-diesel` · `nivel-relatorio` · `nova-compra` · `nova-maquina` · `novo-abastecimento` · `precos-diesel` · `verificar-bot-diesel`
- **Emite:** `diesel:contagem`
- **Escuta:** `arquivos:soltos` · `diesel:atualizar`

## `web/js/views/diesel/painel.js`

- **API:** `GET /api/diesel/${aba}/${id}/historico` · `POST /api/diesel/${aba}/${id}/cancelar`
- **Links/downloads:** `/api/diesel/`
- **Ações:** `cancelar-diesel` · `editar-diesel` · `historico-diesel` · `precos-diesel`
- **Emite:** `diesel:atualizar`

## `web/js/views/diesel/relatorios.js`

- **API:** `POST /api/diesel/relatorio/enviar?periodo=${tela.periodo}&data=${tela.data}&nivel=${relatorio.nivel}`
- **Links/downloads:** `/api/diesel/relatorio/enviar`
- **Ações:** `enviar-relatorio-diesel` · `limpar-filtro-diesel` · `nivel-relatorio`
- **Armazenamento local:** `CHAVE_NIVEL`

## `web/js/views/empresas/cheques.js`

- **API:** `DELETE /api/cheques/${c.id}` · `GET /api/cheques` · `POST (arquivo) /api/empresas/arquivo` · `POST /api/cheques` · `POST /api/recebimentos` · `PUT /api/cheques/${c.id}`
- **Links/downloads:** `/api/cheques/`
- **Ações:** `compensar-cheque` · `editar-cheque` · `novo-cheque`
- **Emite:** `empresas:atualizar`

## `web/js/views/empresas/comum.js`

- **API:** `GET /api/empresas${mes}`
- **Links/downloads:** `/api/empresas`

## `web/js/views/empresas/conferencia.js`

- **API:** `GET /api/empresas/entrada` · `POST (arquivo) /api/empresas/analisar` · `POST /api/empresas/entrada/${id}/confirmar` · `POST /api/empresas/entrada/${id}/descartar` · `POST /api/empresas/entrada/${itemId}/descartar` · `POST /api/empresas/importar-fechamento`
- **Links/downloads:** `/api/arquivos/` · `/api/empresas/entrada/`
- **Ações:** `conferir` · `descartar-item` · `enviar-arquivo`
- **Emite:** `empresas:atualizar`

## `web/js/views/empresas/configbot.js`

- **API:** `GET /api/empresas/config/chats` · `GET /api/notificacoes` · `POST /api/empresas/config` · `POST /api/empresas/entrada/verificar`
- **Ações:** `adicionar-chat` · `liberar-chat` · `procurar-chats` · `remover-destinatario` · `trazer-avisos` · `verificar-bot`
- **Emite:** `empresas:atualizar`

## `web/js/views/empresas/fechamentos.js`

- **API:** `DELETE /api/empresas/${e.id}` · `POST /api/empresas` · `POST /api/empresas/fechamento/enviar` · `PUT /api/empresas/${e.id}`
- **Links/downloads:** `/api/empresas/`
- **Ações:** `editar-empresa` · `editar-nota` · `enviar-fechamentos` · `nova-empresa` · `ver-fechamento`
- **Emite:** `empresas:atualizar`

## `web/js/views/empresas/montagem.js`

- **Escuta:** `empresas:atualizar`

## `web/js/views/empresas/notas.js`

- **API:** `DELETE /api/notas/${nota.id}` · `GET /api/notas?limite=2000` · `GET /api/notas?limite=500` · `POST /api/notas` · `PUT /api/notas/${nota.id}`
- **Links/downloads:** `/api/notas/`
- **Ações:** `editar-nota` · `nova-nota`
- **Emite:** `empresas:atualizar`

## `web/js/views/empresas/recebimentos.js`

- **API:** `GET /api/cheques` · `GET /api/recebimentos` · `POST /api/recebimentos` · `POST /api/recebimentos/${id}/cancelar`
- **Links/downloads:** `/api/recebimentos/`
- **Ações:** `cancelar-recebimento` · `novo-recebimento`
- **Emite:** `empresas:atualizar`

## `web/js/views/gastos.js`

- **API:** `GET /api/gastos` · `GET /api/relatorios/fechamento` · `POST /api/centros` · `PUT /api/centros`
- **Links/downloads:** `/api/gastos/exportar` · `/api/relatorios/fechamento/arquivo`
- **Ações:** `12m` · `3m` · `ano` · `mes` · `tudo`

## `web/js/views/importar.js`

- **API:** `POST (arquivo) /api/importacao` · `POST /api/importacao/${sessao.id}/importar` · `POST /api/importacao/${sessao.id}/previa`
- **Links/downloads:** `/api/importacao/` · `/api/importacao/modelo.xlsx`
- **Ações:** `aba` · `status`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/leitura/caixa.js`

- **API:** `GET /api/entrada` · `GET /api/entrada/${id}` · `POST /api/entrada/${id}/registrar` · `POST /api/entrada/descartar`
- **Links/downloads:** `/api/arquivos/` · `/api/entrada/`
- **Emite:** `avisos:atualizar` · `entrada:contagem`

## `web/js/views/leitura/comprovante.js`

- **API:** `POST /api/${p.aba}/${p.id}/desfazer-pagamento` · `POST /api/comprovantes/registrar`
- **Ações:** `desfazer-comprovante` · `ler-como-boleto` · `registrar-comprovante`
- **Emite:** `avisos:atualizar`

## `web/js/views/leitura/eventos.js`

- **API:** `POST /api/leituras/${boleto.arquivoMeta.id}/ia` · `POST /api/leituras/${item.resultado.arquivo.id}/ia` · `POST /api/leituras/linha`
- **Links/downloads:** `/api/arquivos/` · `/api/leituras/`
- **Ações:** `ampliar` · `centro-todos` · `copiar-linha` · `descartar` · `desfazer-comprovante` · `ia` · `ia-arquivo` · `lancar` · `lancar-pix` · `lancar-todos` · `ler-como-boleto` · `limpar-concluidos` · `preencher-manual` · `registrar-comprovante` · `remover-item` · `sugestao` · `tentar-novamente`

## `web/js/views/leitura/fila.js`

- **API:** `POST /api/leituras/linha`
- **Emite:** `input`

## `web/js/views/leitura/lancamento.js`

- **API:** `POST /api/boletos` · `POST /api/boletos/lote`
- **Emite:** `gravacao:atualizar`

## `web/js/views/leitura/montagem.js`

- **API:** `GET /api/leituras/tarefas/${tarefaId}`
- **Links/downloads:** `/api/leituras/tarefas/`

## `web/js/views/leitura/render.js`

- **Links/downloads:** `/api/arquivos/`
- **Ações:** `aguardando` · `ampliar` · `centro-todos` · `copiar-linha` · `descartar` · `enviando` · `erro` · `ia` · `ia-arquivo` · `lancar` · `lancar-pix` · `lancar-todos` · `lendo` · `limpar-concluidos` · `preencher-manual` · `remover-item` · `sugestao` · `tentar-novamente`

## `web/js/views/notificacoes.js`

- **API:** `GET /api/notificacoes` · `GET /api/notificacoes/resumo/${d.resumoPrevia}` · `GET /api/sistema/inicializacao` · `POST /api/notificacoes/enviar-agora` · `POST /api/notificacoes/resumo/${d.resumoEnviar}/enviar` · `POST /api/notificacoes/telegram/detectar` · `POST /api/notificacoes/telegram/testar` · `POST /api/notificacoes/testar` · `POST /api/sistema/inicializacao` · `PUT /api/notificacoes/config`
- **Links/downloads:** `/api/notificacoes/resumo/`
- **Ações:** `adicionar-chat` · `copiar-link-bot` · `enviar-agora` · `procurar-telegram`
- **Emite:** `avisos:atualizar`

## `web/js/views/painel.js`

- **API:** `GET /api/painel` · `GET /api/previsao` · `PATCH /api/${tipo}/${id}/status`
- **Ações:** `copiar` · `pagar`
- **Emite:** `avisos:atualizar`

## `web/js/views/pix/formulario.js`

- **API:** `POST /api/pix` · `POST /api/pix/ler-codigo` · `PUT /api/pix/${registro.id}`
- **Links/downloads:** `/api/pix/`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/pix/lista.js`

- **API:** `DELETE /api/pix/${id}` · `GET /api/pix` · `GET /api/pix/${id}` · `GET /api/pix/${r.id}/copia-e-cola` · `PATCH /api/pix/${id}/status`
- **Links/downloads:** `/api/pix/`
- **Ações:** `copiar-chave` · `detalhes` · `editar` · `excluir` · `limpar-filtros` · `pago` · `pendente` · `qr`
- **Emite:** `avisos:atualizar` · `gravacao:atualizar`

## `web/js/views/pix/montagem.js`

- **API:** `POST (arquivo) /api/pix/ler-arquivo`
- **Links/downloads:** `/api/pix/exportar`
- **Ações:** `enviar-qr` · `ler-codigo`
- **Escuta:** `pix:atualizar`

## `web/js/views/relatorios.js`

- **API:** `GET /api/notificacoes/resumo/${tipo}` · `GET /api/relatorio-geral`
- **Links/downloads:** `/api/caixa/relatorio/arquivo` · `/api/diesel/relatorio/arquivo` · `/api/notificacoes/resumo/` · `/api/relatorio-geral/arquivo` · `/api/relatorios/fechamento/arquivo`

# Anexo A1 — API (todas as rotas)

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Total: **180 rotas**. *Permissão* é a exigida pelo controle de acesso (`acesso.permissao_da_rota`): `—` = basta ter entrado (ou estar no computador principal); `admin` = só administrador.

## administracao

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/admin` | — | estado admin | — |
| `POST` | `/api/admin/senha` | — | definir senha admin | corpo **SenhaAdminEntrada**: `senha`: str (max_length=200); `confirmacao`: str (max_length=200); `senha_atual`: str \| None = None (max_length=200) |
| `POST` | `/api/admin/entrar` | — | entrar admin | corpo **EntrarAdminEntrada**: `senha`: str (max_length=200) |
| `POST` | `/api/admin/sair` | — | sair admin | — |
| `GET` | `/api/importacao/modelo.xlsx` | — | modelo importacao | — |
| `POST` | `/api/importacao` | config | Recebe a planilha exportada do outro sistema e devolve colunas sugeridas e a prévia dos boletos. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/importacao/{id_}/previa` | config | previa importacao | `id_` (caminho)<br>corpo **ConfigImportacao**: `aba`: str \| None = None (max_length=200); `linha_cabecalho`: int \| None = None (ge=0, le=1000000); `mapeamento`: dict[str, int \| None] \| None = None; `centro_custo`: str = '' (max_length=60); `status`: Literal = 'Pendente' |
| `POST` | `/api/importacao/{id_}/importar` | config | importar boletos | `id_` (caminho)<br>corpo **ImportarEntrada**: `aba`: str \| None = None (max_length=200); `linha_cabecalho`: int \| None = None (ge=0, le=1000000); `mapeamento`: dict[str, int \| None] \| None = None; `centro_custo`: str = '' (max_length=60); `status`: Literal = 'Pendente'; `indices`: list (min_length=1, max_length=5000) |

## backup

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/backup` | — | situacao backup | — |
| `PUT` | `/api/backup/config` | config | configurar backup | corpo **ConfigBackupEntrada**: `ativo`: bool \| None = None; `pasta`: str \| None = None (max_length=500); `horario`: str \| None = None (max_length=5); `manter_dias`: int \| None = None (ge=3, le=365); `codigo`: bool \| None = None; `pacote`: Optional = None; `manter_pacotes`: int \| None = None (ge=1, le=24) |
| `POST` | `/api/backup/agora` | config | fazer backup agora | — |
| `POST` | `/api/backup/pacote` | config | Atualiza o backup e guarda tudo (código, versões, bancos, arquivos e configurações) num único arquivo .zip. | — |
| `POST` | `/api/backup/verificar` | config | Confere o backup inteiro: os bancos abrem, nada falta e cada arquivo bate com a impressão digital guardada. | — |
| `POST` | `/api/backup/escolher-pasta` | config | Abre a janela do Windows para escolher a pasta (só no computador onde o sistema está instalado). | — |

## boletos

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/boletos` | — | listar boletos | `q` = ''<br>`situacao` = ''<br>`campo_data` = 'vencimento'<br>`de` = None<br>`ate` = None<br>`centro` = ''<br>`ordenar` = 'vencimento'<br>`direcao` = 'asc'<br>`pagina` = 1<br>`por_pagina` = 25 |
| `GET` | `/api/boletos/{id_}` | — | obter boleto | `id_` (caminho) |
| `POST` | `/api/boletos` | lancar | lancar boleto | corpo **BoletoNovo**: `linha_digitavel`: str \| None = None (max_length=200); `beneficiario`: str \| None = None (max_length=250); `documento_beneficiario`: str \| None = None (max_length=30); `numero_documento`: str \| None = None (max_length=60); `vencimento`: datetime.date \| None = None; `valor`: float \| None = None (ge=0, le=100000000000.0); `status`: Optional = None; `data_pagamento`: datetime.date \| None = None; `observacoes`: str \| None = None (max_length=1000); `centro_custo`: str \| None = None (max_length=60); `valor_pago`: float \| None = None (ge=0, le=100000000000.0); `juros_multa`: float \| None = None (ge=0, le=100000000000.0); `desconto`: float \| None = None (ge=0, le=100000000000.0); `arquivo_id`: str \| None = None; `permitir_duplicado`: bool = False; `ignorar_validacao`: bool = False |
| `POST` | `/api/boletos/lote` | lancar | Lança vários boletos numa única gravação da planilha. | corpo **LoteEntrada**: `boletos`: list (min_length=1, max_length=300) |
| `PUT` | `/api/boletos/{id_}` | editar | editar boleto | `id_` (caminho)<br>corpo **BoletoEdicao**: `linha_digitavel`: str \| None = None (max_length=200); `beneficiario`: str \| None = None (max_length=250); `documento_beneficiario`: str \| None = None (max_length=30); `numero_documento`: str \| None = None (max_length=60); `vencimento`: datetime.date \| None = None; `valor`: float \| None = None (ge=0, le=100000000000.0); `status`: Optional = None; `data_pagamento`: datetime.date \| None = None; `observacoes`: str \| None = None (max_length=1000); `centro_custo`: str \| None = None (max_length=60); `valor_pago`: float \| None = None (ge=0, le=100000000000.0); `juros_multa`: float \| None = None (ge=0, le=100000000000.0); `desconto`: float \| None = None (ge=0, le=100000000000.0); `ignorar_validacao`: bool = False |
| `PATCH` | `/api/boletos/{id_}/status` | pagar | alterar status | `id_` (caminho)<br>corpo **StatusEntrada**: `status`: Literal; `data_pagamento`: datetime.date \| None = None |
| `DELETE` | `/api/boletos/{id_}` | editar | excluir boleto | `id_` (caminho) |
| `GET` | `/api/boletos/{id_}/arquivo` | — | arquivo do boleto | `id_` (caminho) |
| `GET` | `/api/boletos/{id_}/historico` | — | Quem lançou, editou, pagou ou anexou comprovante neste boleto, e quando. | `id_` (caminho) |
| `GET` | `/api/exportar` | — | exportar | `formato` = 'xlsx'<br>`q` = ''<br>`situacao` = ''<br>`campo_data` = 'vencimento'<br>`de` = None<br>`ate` = None<br>`centro` = ''<br>`ordenar` = 'vencimento'<br>`direcao` = 'asc' |

## busca_comprovantes

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/comprovantes/busca` | — | buscar comprovantes | `q` = ''<br>`tipos` = ''<br>`de` = None<br>`ate` = None<br>`valor` = ''<br>`valor_min` = None<br>`valor_max` = None<br>`numero` = ''<br>`centro` = ''<br>`pessoa` = ''<br>`comprovante` = 'com'<br>`ordenar` = 'data'<br>`direcao` = 'desc'<br>`pagina` = 1<br>`por_pagina` = 100 |
| `GET` | `/api/comprovantes/busca/zip` | — | baixar comprovantes | `q` = ''<br>`tipos` = ''<br>`de` = None<br>`ate` = None<br>`valor` = ''<br>`valor_min` = None<br>`valor_max` = None<br>`numero` = ''<br>`centro` = ''<br>`pessoa` = ''<br>`ordenar` = 'data'<br>`direcao` = 'desc' |

## caixa

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/caixa` | caixa | resumo | `periodo` = 'mes'<br>`data` = None |
| `POST` | `/api/caixa` | caixa | lancar | corpo **LancamentoEntrada**: `movimento`: Optional = None; `valor`: float \| None = None (gt=0, le=10000000000.0); `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `descricao`: str \| None = None (max_length=200); `local`: str \| None = None (max_length=120); `centro_custo`: str \| None = None (max_length=60); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300) |
| `PUT` | `/api/caixa/{id_}` | caixa | editar | `id_` (caminho)<br>corpo **LancamentoEntrada**: `movimento`: Optional = None; `valor`: float \| None = None (gt=0, le=10000000000.0); `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `descricao`: str \| None = None (max_length=200); `local`: str \| None = None (max_length=120); `centro_custo`: str \| None = None (max_length=60); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300) |
| `POST` | `/api/caixa/{id_}/cancelar` | caixa | cancelar | `id_` (caminho) |
| `GET` | `/api/caixa/{id_}/historico` | caixa | historico | `id_` (caminho) |
| `GET` | `/api/caixa/relatorio/arquivo` | caixa | Excel do período: resumo, onde mais se gastou e todos os lançamentos. | `periodo` = 'mes'<br>`data` = None |
| `GET` | `/api/caixa/bot/entrada` | caixa | conferencia | `incluir_concluidos` = False |
| `POST` | `/api/caixa/bot/entrada/{id_}/lancar` | caixa | lancar da conferencia | `id_` (caminho)<br>corpo **ConfirmacaoCaixa**: `movimento`: Optional = None; `valor`: float \| None = None (gt=0, le=10000000000.0); `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `descricao`: str \| None = None (max_length=200); `local`: str \| None = None (max_length=120); `centro_custo`: str \| None = None (max_length=60); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300) |
| `POST` | `/api/caixa/bot/entrada/{id_}/descartar` | caixa | descartar da conferencia | `id_` (caminho) |
| `GET` | `/api/caixa/bot/config` | caixa | obter config bot | — |
| `POST` | `/api/caixa/bot/config` | caixa | salvar config bot | corpo **ConfigBotCaixa**: `token`: str \| None = None (max_length=200); `ativo`: bool \| None = None |
| `POST` | `/api/caixa/bot/verificar` | caixa | verificar bot | — |

## comprovantes

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `POST` | `/api/comprovantes/registrar` | pagar | registrar pagamento | corpo **RegistrarEntrada**: `aba`: Literal; `id`: int (gt=0); `arquivo_id`: str \| None = None (max_length=40); `extraido`: dict = PydanticUndefined |
| `POST` | `/api/boletos/{id_}/comprovante` | pagar | anexar comprovante boletos | `id_` (caminho)<br>`arquivo` (arquivo/formulário) |
| `GET` | `/api/boletos/{id_}/comprovante` | — | ver comprovante boletos | `id_` (caminho) |
| `DELETE` | `/api/boletos/{id_}/comprovante` | pagar | remover comprovante boletos | `id_` (caminho) |
| `POST` | `/api/boletos/{id_}/desfazer-pagamento` | pagar | Desfaz um pagamento registrado por engano: volta para pendente e tira o comprovante. | `id_` (caminho) |
| `POST` | `/api/pix/{id_}/comprovante` | pagar | anexar comprovante pix | `id_` (caminho)<br>`arquivo` (arquivo/formulário) |
| `GET` | `/api/pix/{id_}/comprovante` | — | ver comprovante pix | `id_` (caminho) |
| `DELETE` | `/api/pix/{id_}/comprovante` | pagar | remover comprovante pix | `id_` (caminho) |
| `POST` | `/api/pix/{id_}/desfazer-pagamento` | pagar | Desfaz um pagamento registrado por engano: volta para pendente e tira o comprovante. | `id_` (caminho) |

## diesel

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/diesel` | diesel | resumo | `periodo` = 'semana'<br>`data` = None |
| `POST` | `/api/diesel/arquivo` | diesel | Guarda o comprovante ou o canhoto escolhido na tela; devolve o id para o lançamento. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/diesel/analisar` | diesel | Lê o canhoto ou o comprovante enviado pela tela (sem passar pelo bot): combustíveis, litros, preços e totais. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/diesel/canhoto` | diesel | Canhoto com uma ou mais linhas (combustíveis diferentes, máquinas diferentes): um abastecimento por linha. | corpo **CanhotoEntrada**: `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `posto`: str \| None = None (max_length=80); `documento`: str \| None = None (max_length=30); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None; `itens`: list (min_length=1, max_length=10) |
| `GET` | `/api/diesel/precos` | diesel | obter precos | — |
| `POST` | `/api/diesel/precos` | diesel | salvar precos | corpo **PrecosEntrada**: `precos`: dict |
| `POST` | `/api/diesel/compras` | diesel | lancar compra | corpo **CompraEntrada**: `data`: datetime.date \| None = None; `posto`: str \| None = None (max_length=80); `combustivel`: Optional = None; `litros`: float \| None = None (gt=0, le=1000000.0); `valor`: float \| None = None (ge=0, le=1000000000.0); `preco_litro`: float \| None = None (ge=0, le=1000); `forma`: str \| None = None (max_length=20); `documento`: str \| None = None (max_length=30); `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None |
| `POST` | `/api/diesel/abastecimentos` | diesel | lancar abastecimento | corpo **AbastecimentoEntrada**: `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `maquina`: str \| None = None (max_length=60); `combustivel`: Optional = None; `litros`: float \| None = None (gt=0, le=100000.0); `preco_litro`: float \| None = None (ge=0, le=1000); `valor`: float \| None = None (ge=0, le=100000000.0); `medidor`: float \| None = None (ge=0, le=100000000.0); `posto`: str \| None = None (max_length=80); `documento`: str \| None = None (max_length=30); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None |
| `GET` | `/api/diesel/maquinas` | diesel | listar maquinas | — |
| `POST` | `/api/diesel/maquinas` | diesel | criar maquina | corpo **MaquinaEntrada**: `nome`: str \| None = None (max_length=60); `tipo`: Optional = None; `placa`: str \| None = None (max_length=16); `medidor`: Optional = None; `combustivel`: Union = None; `status`: Optional = None; `observacoes`: str \| None = None (max_length=300) |
| `PUT` | `/api/diesel/maquinas/{id_}` | diesel | editar maquina | `id_` (caminho)<br>corpo **MaquinaEntrada**: `nome`: str \| None = None (max_length=60); `tipo`: Optional = None; `placa`: str \| None = None (max_length=16); `medidor`: Optional = None; `combustivel`: Union = None; `status`: Optional = None; `observacoes`: str \| None = None (max_length=300) |
| `PUT` | `/api/diesel/{aba}/{id_}` | diesel | editar | `aba` (caminho)<br>`id_` (caminho)<br>corpo **EdicaoEntrada**: `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `maquina`: str \| None = None (max_length=60); `combustivel`: Optional = None; `litros`: float \| None = None (gt=0, le=100000.0); `preco_litro`: float \| None = None (ge=0, le=1000); `valor`: float \| None = None (ge=0, le=100000000.0); `medidor`: float \| None = None (ge=0, le=100000000.0); `posto`: str \| None = None (max_length=80); `documento`: str \| None = None (max_length=30); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None; `forma`: str \| None = None (max_length=20) |
| `POST` | `/api/diesel/{aba}/{id_}/cancelar` | diesel | cancelar | `aba` (caminho)<br>`id_` (caminho) |
| `GET` | `/api/diesel/{aba}/{id_}/historico` | diesel | historico | `aba` (caminho)<br>`id_` (caminho) |
| `GET` | `/api/diesel/relatorio` | diesel | O relatório do período com tudo o que os três níveis (simples, detalhado e completo) mostram. | `periodo` = 'semana'<br>`data` = None |
| `GET` | `/api/diesel/relatorio/arquivo` | diesel | Excel do período, sempre completo: resumo, máquinas, comparação, por dia, combustíveis, postos, pessoas, abastecimentos (com o consumo de cada trecho), compras e os pontos de atenção. | `periodo` = 'semana'<br>`data` = None |
| `GET` | `/api/diesel/relatorio/texto` | diesel | relatorio texto | `periodo` = 'semana'<br>`data` = None<br>`nivel` = 'simples' |
| `POST` | `/api/diesel/relatorio/enviar` | diesel | Manda agora o relatório (no nível escolhido) pelo bot do diesel para os responsáveis. | `periodo` = 'semana'<br>`data` = None<br>`nivel` = 'simples' |
| `GET` | `/api/diesel/bot/entrada` | diesel | conferencia | `incluir_concluidos` = False |
| `POST` | `/api/diesel/bot/entrada/{id_}/lancar` | diesel | lancar da conferencia | `id_` (caminho)<br>corpo **ConfirmacaoEntrada**: `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `maquina`: str \| None = None (max_length=60); `combustivel`: Optional = None; `litros`: float \| None = None (gt=0, le=100000.0); `preco_litro`: float \| None = None (ge=0, le=1000); `valor`: float \| None = None (ge=0, le=100000000.0); `medidor`: float \| None = None (ge=0, le=100000000.0); `posto`: str \| None = None (max_length=80); `documento`: str \| None = None (max_length=30); `pessoa`: str \| None = None (max_length=60); `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None; `forma`: str \| None = None (max_length=20); `tipo`: Optional = None; `itens`: list[LinhaCanhoto] \| None = None (max_length=10) |
| `POST` | `/api/diesel/bot/entrada/{id_}/descartar` | diesel | descartar da conferencia | `id_` (caminho) |
| `GET` | `/api/diesel/bot/config` | diesel | obter config bot | — |
| `POST` | `/api/diesel/bot/config` | diesel | salvar config bot | corpo **ConfigBotDiesel**: `token`: str \| None = None (max_length=200); `ativo`: bool \| None = None; `gestores`: list[str] \| None = None (max_length=50); `alerta_valor`: float \| None = None (ge=0, le=10000000); `hora_relatorio`: str \| None = None (pattern=^\d{2}:\d{2}$); `relatorios`: dict[Literal['semana', 'quinzena', 'mes'], bool] \| None = None; `nivel_relatorio`: Optional = None |
| `POST` | `/api/diesel/bot/verificar` | diesel | verificar bot | — |

## empresas

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/empresas` | empresas | listar empresas | `competencia` = None |
| `POST` | `/api/empresas` | empresas | criar empresa | corpo **EmpresaEntrada**: `nome`: str \| None = None (max_length=80); `razao_social`: str \| None = None (max_length=120); `cnpj`: str \| None = None (max_length=20); `apelidos`: str \| None = None (max_length=200); `dia_fechamento`: int \| None = None (ge=1, le=28); `contato`: str \| None = None (max_length=80); `telefone`: str \| None = None (max_length=20); `email`: str \| None = None (max_length=120); `chat_telegram`: str \| None = None (max_length=20); `status`: Optional = None; `observacoes`: str \| None = None (max_length=500) |
| `PUT` | `/api/empresas/{id_}` | empresas | editar empresa | `id_` (caminho)<br>corpo **EmpresaEntrada**: `nome`: str \| None = None (max_length=80); `razao_social`: str \| None = None (max_length=120); `cnpj`: str \| None = None (max_length=20); `apelidos`: str \| None = None (max_length=200); `dia_fechamento`: int \| None = None (ge=1, le=28); `contato`: str \| None = None (max_length=80); `telefone`: str \| None = None (max_length=20); `email`: str \| None = None (max_length=120); `chat_telegram`: str \| None = None (max_length=20); `status`: Optional = None; `observacoes`: str \| None = None (max_length=500) |
| `DELETE` | `/api/empresas/{id_}` | empresas | excluir empresa | `id_` (caminho) |
| `GET` | `/api/empresas/{id_}/fechamento` | empresas | obter fechamento | `id_` (caminho)<br>`competencia` = None |
| `GET` | `/api/empresas/{id_}/fechamento/arquivo` | empresas | baixar fechamento | `id_` (caminho)<br>`formato` = 'xlsx'<br>`competencia` = None |
| `POST` | `/api/empresas/fechamento/enviar` | empresas | Manda agora, pelo bot de notas, o fechamento de todas as empresas (o envio automático é no dia 20). | — |
| `GET` | `/api/notas` | empresas | listar notas | `empresa` = ''<br>`competencia` = ''<br>`status` = ''<br>`limite` = 500 |
| `POST` | `/api/notas` | empresas | lancar notas | corpo **NotasNovas**: `empresa`: str (max_length=80); `competencia`: str \| None = None (pattern=^\d{4}-\d{2}$); `itens`: list (min_length=1, max_length=200) |
| `PUT` | `/api/notas/{id_}` | empresas | editar nota | `id_` (caminho)<br>corpo **NotaEdicao**: `data`: datetime.date \| None = None; `material`: str \| None = None (max_length=80); `unidade`: str \| None = None (max_length=10); `quantidade`: float \| None = None (ge=0, le=1000000000.0); `valor_unitario`: float \| None = None (ge=0, le=1000000000.0); `valor_total`: float \| None = None (ge=0, le=100000000000.0); `numero_nf`: str \| None = None (max_length=15); `pedido`: str \| None = None (max_length=15); `observacoes`: str \| None = None (max_length=200); `empresa`: str \| None = None (max_length=80); `competencia`: str \| None = None (pattern=^\d{4}-\d{2}$); `status`: str \| None = None; `valor_recebido`: float \| None = None (ge=0, le=100000000000.0); `data_recebimento`: datetime.date \| None = None; `todas_da_nota`: bool = False |
| `DELETE` | `/api/notas/{id_}` | empresas | excluir nota | `id_` (caminho) |
| `GET` | `/api/cheques` | empresas | listar cheques | `empresa` = ''<br>`status` = '' |
| `POST` | `/api/cheques` | empresas | lancar cheque | corpo **ChequeEntrada**: `empresa`: str \| None = None (max_length=80); `numero`: str \| None = None (max_length=20); `vencimento`: datetime.date \| None = None; `valor`: float \| None = None (ge=0, le=100000000000.0); `banco`: str \| None = None (max_length=60); `agencia`: str \| None = None (max_length=12); `coop`: str \| None = None (max_length=12); `conta`: str \| None = None (max_length=20); `emitente`: str \| None = None (max_length=80); `pedidos`: str \| None = None (max_length=200); `notas`: str \| None = None (max_length=200); `status`: str \| None = None; `data_deposito`: datetime.date \| None = None; `cmc7`: str \| None = None (max_length=40); `observacoes`: str \| None = None (max_length=300) |
| `PUT` | `/api/cheques/{id_}` | empresas | editar cheque | `id_` (caminho)<br>corpo **ChequeEntrada**: `empresa`: str \| None = None (max_length=80); `numero`: str \| None = None (max_length=20); `vencimento`: datetime.date \| None = None; `valor`: float \| None = None (ge=0, le=100000000000.0); `banco`: str \| None = None (max_length=60); `agencia`: str \| None = None (max_length=12); `coop`: str \| None = None (max_length=12); `conta`: str \| None = None (max_length=20); `emitente`: str \| None = None (max_length=80); `pedidos`: str \| None = None (max_length=200); `notas`: str \| None = None (max_length=200); `status`: str \| None = None; `data_deposito`: datetime.date \| None = None; `cmc7`: str \| None = None (max_length=40); `observacoes`: str \| None = None (max_length=300) |
| `DELETE` | `/api/cheques/{id_}` | empresas | excluir cheque | `id_` (caminho) |
| `GET` | `/api/recebimentos` | empresas | listar recebimentos | `empresa` = ''<br>`limite` = 300 |
| `POST` | `/api/recebimentos` | empresas | registrar recebimento | corpo **RecebimentoEntrada**: `empresa`: str \| None = None (max_length=80); `forma`: str \| None = None; `valor`: float (gt=0, le=100000000000.0); `data`: datetime.date \| None = None; `hora`: str \| None = None (max_length=5); `pagador`: str \| None = None (max_length=120); `id_transacao`: str \| None = None (max_length=120); `notas`: str \| None = None (max_length=300); `pedidos`: str \| None = None (max_length=300); `cheque_id`: int \| None = None; `observacoes`: str \| None = None (max_length=300); `arquivo_id`: str \| None = None |
| `POST` | `/api/recebimentos/{id_}/cancelar` | empresas | cancelar recebimento | `id_` (caminho) |
| `GET` | `/api/empresas/entrada` | empresas | listar entrada | `incluir_concluidos` = False |
| `POST` | `/api/empresas/entrada/verificar` | empresas | verificar entrada | — |
| `POST` | `/api/empresas/entrada/{id_}/confirmar` | empresas | confirmar entrada | `id_` (caminho)<br>corpo **ConfirmacaoEntrada**: `tipo`: Literal; `dados`: dict |
| `POST` | `/api/empresas/entrada/{id_}/descartar` | empresas | descartar entrada | `id_` (caminho) |
| `POST` | `/api/empresas/analisar` | empresas | Lê uma nota fiscal, um cheque, um comprovante ou o print de um fechamento enviado pela tela. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/empresas/arquivo` | empresas | Guarda um comprovante escolhido na tela (ex.: o depósito de um cheque) sem lê-lo; devolve o id para o lançamento. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/empresas/importar-fechamento` | empresas | Parte 5: traz para o sistema o fechamento que já estava em andamento (lido de um print ou digitado). | corpo **ImportacaoFechamento**: `empresa`: str (max_length=80); `competencia`: str \| None = None (pattern=^\d{4}-\d{2}$); `linhas`: list (min_length=1, max_length=400) |
| `GET` | `/api/empresas/config` | empresas | obter config | — |
| `POST` | `/api/empresas/config` | empresas | salvar config | corpo **ConfigEntrada**: `minha_empresa`: dict \| None = None; `dia_fechamento`: int \| None = None (ge=1, le=28); `fechamento_automatico`: bool \| None = None; `hora_envio`: str \| None = None (max_length=5); `bot`: dict \| None = None |
| `GET` | `/api/empresas/config/chats` | empresas | Pessoas e grupos que falaram com o bot de notas (para cadastrar sem digitar o chat ID). | — |

## entrada

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/entrada` | — | listar entrada | `concluidos` = False |
| `GET` | `/api/entrada/{id_}` | — | obter item | `id_` (caminho) |
| `POST` | `/api/entrada/descartar` | lancar | descartar itens | corpo **DescartarEntrada**: `ids`: list (min_length=1, max_length=300) |
| `PUT` | `/api/entrada/config` | config | configurar entrada | corpo **ConfigEntrada**: `email`: dict \| None = None; `telegram`: dict \| None = None |
| `POST` | `/api/entrada/verificar` | lancar | verificar agora | corpo **VerificarEntrada**: `canal`: Literal |
| `POST` | `/api/entrada/{id_}/registrar` | pagar | Comprovante que ficou em dúvida: registra o pagamento no lançamento escolhido. | `id_` (caminho)<br>corpo **AssociarEntrada**: `aba`: Literal; `id`: int (gt=0) |

## gastos

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/centros` | — | listar centros | — |
| `POST` | `/api/centros` | lancar | criar centro | corpo **CentroEntrada**: `nome`: str (min_length=1, max_length=60); `descricao`: str = '' (max_length=200); `ativo`: bool = True |
| `PUT` | `/api/centros` | lancar | editar centro | corpo **CentroEdicao**: `nome`: str (min_length=1, max_length=60); `descricao`: str = '' (max_length=200); `ativo`: bool = True; `nome_anterior`: str (min_length=1, max_length=60) |
| `GET` | `/api/gastos` | gastos | analise gastos | `de` = None<br>`ate` = None<br>`campo_data` = 'vencimento'<br>`situacao` = 'todos'<br>`tipo` = 'todos' |
| `GET` | `/api/gastos/exportar` | gastos | exportar gastos | `de` = None<br>`ate` = None<br>`campo_data` = 'vencimento'<br>`situacao` = 'todos'<br>`tipo` = 'todos' |
| `GET` | `/api/relatorios/fechamento` | gastos | fechamento do mes | `mes` = None<br>`base` = 'vencimento' |
| `GET` | `/api/relatorios/fechamento/arquivo` | gastos | baixar fechamento | `mes` = None<br>`base` = 'vencimento'<br>`formato` = 'pdf' |

## leitura

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `POST` | `/api/leituras` | lancar | criar leitura | `arquivo` (arquivo/formulário) |
| `POST` | `/api/leituras/tarefas` | lancar | Leitura em segundo plano: responde na hora com o id da tarefa para acompanhar o progresso. | `arquivo` (arquivo/formulário) |
| `GET` | `/api/leituras/tarefas/{tarefa_id}` | — | acompanhar tarefa | `tarefa_id` (caminho) |
| `POST` | `/api/leituras/linha` | lancar | analisar linha | corpo **LinhaEntrada**: `linha`: str (max_length=200) |
| `POST` | `/api/leituras/{arquivo_id}/ia` | lancar | analisar com ia | `arquivo_id` (caminho)<br>corpo **PedidoIA**: `campos`: dict = PydanticUndefined; `pagina`: int = 0 (ge=0) |
| `GET` | `/api/arquivos/{arquivo_id}` | — | visualizar arquivo | `arquivo_id` (caminho) |

## notificacoes

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/notificacoes` | — | obter notificacoes | — |
| `POST` | `/api/notificacoes/vistos` | — | Avisos do sininho que já foram vistos: saem da contagem até a situação do boleto mudar. | corpo **ChavesAvisoEntrada**: `chaves`: list = PydanticUndefined (max_length=1000) |
| `POST` | `/api/notificacoes/dispensar` | — | dispensar aviso | corpo **ChaveAvisoEntrada**: `chave`: str (max_length=200) |
| `POST` | `/api/notificacoes/restaurar` | — | restaurar avisos | — |
| `PUT` | `/api/notificacoes/config` | notificacoes | salvar config notificacoes | corpo **ConfigNotificacoesEntrada**: `ativo`: bool \| None = None; `resumos`: dict[Literal['segunda', 'sexta'], ResumoEntrada] \| None = None; `dias_semana`: list[int] \| None = None (max_length=7); `regras`: list[RegraEntrada] \| None = None (max_length=20); `windows`: dict \| None = None; `telegram`: dict \| None = None; `email`: dict \| None = None |
| `POST` | `/api/notificacoes/testar` | notificacoes | testar notificacao | corpo **TesteCanalEntrada**: `canal`: Literal |
| `POST` | `/api/notificacoes/enviar-agora` | notificacoes | enviar notificacoes agora | — |
| `GET` | `/api/notificacoes/resumo/{tipo}` | — | Como o resumo da semana ficaria se fosse enviado agora. | `tipo` (caminho) |
| `POST` | `/api/notificacoes/resumo/{tipo}/enviar` | notificacoes | enviar resumo | `tipo` (caminho) |
| `POST` | `/api/notificacoes/telegram/detectar` | notificacoes | detectar chat telegram | corpo **DetectarTelegramEntrada**: `token`: str \| None = None |
| `POST` | `/api/notificacoes/telegram/testar` | notificacoes | Envia uma mensagem de teste para uma única pessoa ou grupo. | corpo **TesteTelegramEntrada**: `chat_id`: str (max_length=40); `token`: str \| None = None (max_length=200) |

## pix

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/pix` | — | listar pix | `q` = ''<br>`situacao` = ''<br>`campo_data` = 'vencimento'<br>`de` = None<br>`ate` = None<br>`centro` = ''<br>`ordenar` = 'vencimento'<br>`direcao` = 'asc'<br>`pagina` = 1<br>`por_pagina` = 25 |
| `GET` | `/api/pix/exportar` | — | exportar pix | `formato` = 'xlsx'<br>`q` = ''<br>`situacao` = ''<br>`campo_data` = 'vencimento'<br>`de` = None<br>`ate` = None<br>`centro` = ''<br>`ordenar` = 'vencimento'<br>`direcao` = 'asc' |
| `POST` | `/api/pix/ler-codigo` | lancar | ler codigo pix | corpo **PixCodigoEntrada**: `texto`: str (max_length=1500) |
| `POST` | `/api/pix/ler-arquivo` | lancar | Procura QR codes Pix numa foto, print ou PDF. | `arquivo` (arquivo/formulário) |
| `POST` | `/api/pix` | lancar | lancar pix | corpo **PixNovo**: `recebedor`: str \| None = None (max_length=250); `tipo_chave`: Optional = None; `chave`: str \| None = None (max_length=120); `valor`: float \| None = None (ge=0, le=100000000000.0); `vencimento`: datetime.date \| None = None; `centro_custo`: str \| None = None (max_length=60); `descricao`: str \| None = None (max_length=500); `status`: Optional = None; `data_pagamento`: datetime.date \| None = None; `txid`: str \| None = None (max_length=40); `copia_e_cola`: str \| None = None (max_length=1500); `observacoes`: str \| None = None (max_length=1000); `valor_pago`: float \| None = None (ge=0, le=100000000000.0); `juros_multa`: float \| None = None (ge=0, le=100000000000.0); `desconto`: float \| None = None (ge=0, le=100000000000.0); `arquivo_id`: str \| None = None; `permitir_duplicado`: bool = False |
| `GET` | `/api/pix/{id_}` | — | obter pix | `id_` (caminho) |
| `PUT` | `/api/pix/{id_}` | editar | editar pix | `id_` (caminho)<br>corpo **PixBase**: `recebedor`: str \| None = None (max_length=250); `tipo_chave`: Optional = None; `chave`: str \| None = None (max_length=120); `valor`: float \| None = None (ge=0, le=100000000000.0); `vencimento`: datetime.date \| None = None; `centro_custo`: str \| None = None (max_length=60); `descricao`: str \| None = None (max_length=500); `status`: Optional = None; `data_pagamento`: datetime.date \| None = None; `txid`: str \| None = None (max_length=40); `copia_e_cola`: str \| None = None (max_length=1500); `observacoes`: str \| None = None (max_length=1000); `valor_pago`: float \| None = None (ge=0, le=100000000000.0); `juros_multa`: float \| None = None (ge=0, le=100000000000.0); `desconto`: float \| None = None (ge=0, le=100000000000.0) |
| `PATCH` | `/api/pix/{id_}/status` | pagar | alterar status pix | `id_` (caminho)<br>corpo **StatusEntrada**: `status`: Literal; `data_pagamento`: datetime.date \| None = None |
| `DELETE` | `/api/pix/{id_}` | editar | excluir pix | `id_` (caminho) |
| `GET` | `/api/pix/{id_}/arquivo` | — | arquivo do pix | `id_` (caminho) |
| `GET` | `/api/pix/{id_}/historico` | — | historico do pix | `id_` (caminho) |
| `GET` | `/api/pix/{id_}/copia-e-cola` | — | copia e cola pix | `id_` (caminho) |
| `GET` | `/api/pix/{id_}/qrcode.svg` | — | qrcode pix | `id_` (caminho) |

## relatorios

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/relatorio-geral` | — | relatorio do mes | `mes` = None |
| `GET` | `/api/relatorio-geral/arquivo` | — | baixar relatorio do mes | `mes` = None |

## saude

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/saude` | — | diagnostico | — |
| `POST` | `/api/saude/atualizar-planilha` | config | atualizar planilha | — |
| `POST` | `/api/saude/limpar-logs` | config | limpar logs | — |

## sistema

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `GET` | `/api/status` | — | obter status | — |
| `GET` | `/api/versao` | — | Versão em uso, histórico do que mudou em cada versão e se há alterações ainda não guardadas. | — |
| `GET` | `/api/acesso/estado` | — | estado acesso | — |
| `POST` | `/api/acesso` | — | entrar | corpo **SenhaEntrada**: `senha`: str (max_length=200) |
| `POST` | `/api/acesso/sair` | — | sair | — |
| `GET` | `/api/gravacao` | — | status gravacao | — |
| `POST` | `/api/gravacao/tentar` | — | tentar gravacao | — |
| `DELETE` | `/api/gravacao/{op_id}` | — | cancelar gravacao | `op_id` (caminho) |
| `GET` | `/api/painel` | — | obter painel | — |
| `GET` | `/api/previsao` | — | Quanto vai sair nas próximas semanas (boletos e Pix pendentes) e o que já está em atraso. | `semanas` = 8 |
| `POST` | `/api/planilha/abrir` | — | abrir planilha | — |
| `POST` | `/api/planilha/abrir-pasta` | — | abrir pasta | — |
| `GET` | `/api/sistema/inicializacao` | — | obter inicializacao | — |
| `POST` | `/api/sistema/inicializacao` | config | alterar inicializacao | corpo **InicializacaoEntrada**: `ativo`: bool; `minimizado`: bool \| None = None |
| `GET` | `/api/app` | — | status aplicativo | — |
| `PUT` | `/api/app/preferencias` | — | salvar preferencias | corpo **PreferenciasEntrada**: `fechar_para_bandeja`: bool \| None = None; `minimizado_ao_iniciar`: bool \| None = None |
| `POST` | `/api/app/atalhos` | — | criar atalhos | — |
| `POST` | `/api/app/mostrar` | — | mostrar aplicativo | `entrada` (arquivo/formulário) |
| `GET` | `/api/app/abrir` | — | Destino dos cliques nas notificações: traz a janela do aplicativo para a frente. | `rota` = '' |
| `POST` | `/api/app/sair` | — | sair do aplicativo | — |
| `GET` | `/api/rede` | — | status rede | — |
| `POST` | `/api/rede/senha` | config | definir senha rede | corpo **SenhaRedeEntrada**: `senha`: str (max_length=200); `confirmacao`: str (max_length=200) |
| `POST` | `/api/rede/ativar` | config | ativar rede | corpo **AtivarRedeEntrada**: `ativo`: bool |
| `GET` | `/api/rede/qrcode.svg` | — | qrcode rede | `url` = None |

## usuarios

| Método | Caminho | Permissão | O que faz | Parâmetros |
|---|---|---|---|---|
| `POST` | `/api/usuarios/entrar` | admin | entrar | corpo **EntrarEntrada**: `login`: str (max_length=80); `senha`: str (max_length=200) |
| `POST` | `/api/usuarios/sair` | admin | sair | — |
| `GET` | `/api/usuarios/eu` | — | quem sou | — |
| `POST` | `/api/usuarios/minha-senha` | — | trocar minha senha | corpo **TrocarSenhaEntrada**: `senha_atual`: str (max_length=200); `senha`: str (max_length=200); `confirmacao`: str (max_length=200) |
| `GET` | `/api/usuarios` | — | listar usuarios | — |
| `POST` | `/api/usuarios` | admin | criar usuario | corpo **UsuarioNovo**: `nome`: str (max_length=60); `login`: str = '' (max_length=40); `senha`: str (max_length=200); `perfil`: Literal = 'comum'; `permissoes`: list[str] \| None = None |
| `PUT` | `/api/usuarios/config` | admin | configurar usuarios | corpo **ConfigUsuariosEntrada**: `exigir_login_no_computador`: bool \| None = None; `pedir_login_ao_abrir`: bool \| None = None |
| `PUT` | `/api/usuarios/{id_}` | admin | alterar usuario | `id_` (caminho)<br>corpo **UsuarioEdicao**: `nome`: str \| None = None (max_length=60); `ativo`: bool \| None = None; `senha`: str \| None = None (max_length=200); `perfil`: Optional = None; `permissoes`: list[str] \| None = None |
| `DELETE` | `/api/usuarios/{id_}` | admin | excluir usuario | `id_` (caminho) |

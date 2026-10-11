# Anexo A4 — Mapa do código (back-end Python)

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Para cada módulo: a descrição (docstring), as constantes, as classes (com os métodos) e as funções, com a assinatura completa e a primeira frase da descrição. É o "índice" do código para reconstruir cada peça.

| Módulo | Linhas |
|---|---|
| `app/__init__.py` | 4 |
| `app/__main__.py` | 93 |
| `app/acesso.py` | 220 |
| `app/admin.py` | 134 |
| `app/arquivos.py` | 113 |
| `app/atalhos.py` | 89 |
| `app/backup.py` | 781 |
| `app/banco.py` | 613 |
| `app/boleto/__init__.py` | 0 |
| `app/boleto/bancos.py` | 72 |
| `app/boleto/codigo.py` | 374 |
| `app/boleto/extrator.py` | 714 |
| `app/boleto/imagem.py` | 108 |
| `app/boleto/leitores.py` | 263 |
| `app/boleto/ocr.py` | 111 |
| `app/boleto/texto.py` | 697 |
| `app/bot.py` | 166 |
| `app/busca_comprovantes.py` | 371 |
| `app/caixa/__init__.py` | 8 |
| `app/caixa/bot.py` | 550 |
| `app/caixa/leitura.py` | 82 |
| `app/caixa/servico.py` | 246 |
| `app/comprovante.py` | 306 |
| `app/config.py` | 48 |
| `app/contexto.py` | 87 |
| `app/demonstracao.py` | 449 |
| `app/desktop.py` | 268 |
| `app/diesel/__init__.py` | 2 |
| `app/diesel/bot.py` | 878 |
| `app/diesel/leitura.py` | 340 |
| `app/diesel/modelos.py` | 105 |
| `app/diesel/precos.py` | 63 |
| `app/diesel/relatorio.py` | 350 |
| `app/diesel/servico.py` | 602 |
| `app/empresas/__init__.py` | 17 |
| `app/empresas/bot.py` | 142 |
| `app/empresas/configuracao.py` | 183 |
| `app/empresas/entrada.py` | 536 |
| `app/empresas/leitura.py` | 747 |
| `app/empresas/modelos.py` | 147 |
| `app/empresas/relatorio.py` | 239 |
| `app/empresas/servico.py` | 833 |
| `app/entrada.py` | 655 |
| `app/fechamento.py` | 351 |
| `app/fila_gravacao.py` | 256 |
| `app/ia.py` | 121 |
| `app/importacao.py` | 763 |
| `app/inicializacao.py` | 78 |
| `app/janela.py` | 49 |
| `app/main.py` | 243 |
| `app/notificacoes/__init__.py` | 1 |
| `app/notificacoes/canais.py` | 207 |
| `app/notificacoes/regras.py` | 204 |
| `app/notificacoes/servico.py` | 670 |
| `app/pix.py` | 262 |
| `app/planilha.py` | 910 |
| `app/preferencias.py` | 42 |
| `app/rede.py` | 279 |
| `app/registro_log.py` | 94 |
| `app/relatorio_geral.py` | 257 |
| `app/repositorio.py` | 122 |
| `app/resumo_semanal.py` | 366 |
| `app/rotas/__init__.py` | 1 |
| `app/rotas/administracao.py` | 193 |
| `app/rotas/backup.py` | 111 |
| `app/rotas/boletos.py` | 263 |
| `app/rotas/busca_comprovantes.py` | 69 |
| `app/rotas/caixa.py` | 179 |
| `app/rotas/comprovantes.py` | 105 |
| `app/rotas/comum.py` | 66 |
| `app/rotas/diesel.py` | 429 |
| `app/rotas/empresas.py` | 416 |
| `app/rotas/entrada.py` | 86 |
| `app/rotas/gastos.py` | 138 |
| `app/rotas/leitura.py` | 100 |
| `app/rotas/notificacoes.py` | 150 |
| `app/rotas/pix.py` | 259 |
| `app/rotas/relatorios.py` | 29 |
| `app/rotas/saude.py` | 32 |
| `app/rotas/sistema.py` | 288 |
| `app/rotas/usuarios.py` | 150 |
| `app/saude.py` | 267 |
| `app/servico_comprovante.py` | 92 |
| `app/servico_leitura.py` | 74 |
| `app/servicos.py` | 566 |
| `app/tarefas.py` | 133 |
| `app/usuarios.py` | 339 |
| `app/versao.py` | 229 |

## `app/__init__.py`

> Fin Pro — sistema financeiro do escritório: boletos, Pix, caixa, diesel, gastos, empresas e avisos.


## `app/__main__.py`

> Inicia o sistema.
> 
> python -m app              abre o aplicativo (janela própria + ícone na bandeja)
> python -m app --bandeja    inicia só com o ícone na bandeja (ao ligar o computador)
> python -m app --navegador  modo antigo: servidor + página no navegador

- `_preparar_saida_sem_console() -> None` — Com pythonw (atalho, inicialização com o Windows) não há console: registra a saída em arquivo.
- `_ja_em_execucao(host: str, porta: int) -> bool`
- `_mostrar_instancia_existente(abrir_navegador: bool) -> None` — Já está aberto: traz a janela do aplicativo para a frente (ou abre o navegador, no modo antigo).
- `main() -> None`

## `app/acesso.py`

> Controle de acesso de aparelhos da rede (ex.: celular no Wi-Fi).
> 
> No próprio computador o acesso é livre. Para outros aparelhos, a senha pode vir do arquivo ``.env``
> (``LEITOR_SENHA_ACESSO``) ou da tela de Configurações (guardada com hash pelo GerenciadorRede).
> Depois de entrar, o aparelho recebe um cookie válido por 30 dias. Após 5 senhas erradas, o endereço
> fica bloqueado por 5 minutos.
> 
> Com usuários cadastrados (``app/usuarios.py``), a senha única deixa de valer: cada pessoa entra com o próprio
> login e o nome dela fica em ``request.state.usuario_nome`` (vai para o Histórico da planilha). No próprio
> computador o login só é pedido se o administrador ligar essa opção.
> 
> Cada pessoa só usa o que o administrador liberou: aqui fica a tabela que diz qual **permissão** cada rota da API
> exige (ver ``PERMISSOES`` em ``app/usuarios.py``). Quem entrou sem a permissão recebe 403 com uma explicação.

**Constantes:** `COOKIE` = `'leitor_acesso'` · `ESCRITA` = `{'POST', 'PUT', 'PATCH', 'DELETE'}` · `SEM_PERMISSAO` = `{'/api/notificacoes/vistos', '/api/notificacoes/dispensar', '/api/notificacoes/restaurar', '/api/usuarios/minha-senha', '/api/usuarios/eu'}` · `ENDERECOS_LOCAIS` = `{'127.0.0.1', '::1', 'localhost', 'testclient'}` · `ROTAS_LIVRES` = `{'/api/acesso', '/api/acesso/estado', '/api/acesso/sair', '/api/usuarios/entrar', '/api/usuarios/sair'}` · `NOME_COMPUTADOR` = `'Computador principal'` · `NOME_REDE` = `'Acesso pela rede'` · `VALIDADE_COOKIE` = `30 * 24 * 3600` · `MAX_TENTATIVAS` = `5` · `BLOQUEIO_SEGUNDOS` = `300`

- `configurar(gerenciador) -> None`
- `configurar_usuarios(gerenciador) -> None`
- `usuario_do_cookie(request: Request) -> dict \| None`
- `login_necessario(request: Request) -> bool` — Com usuários cadastrados: a rede sempre pede login; o computador só se o administrador exigir.
- `requisicao_local(request: Request) -> bool`
- `permissao_da_rota(metodo: str, caminho: str) -> str \| None` — Permissão exigida por uma rota da API. ``None`` = liberada para quem já entrou; ``admin`` = só administrador.
- `pode(request: Request, permissao: str) -> bool` — Quem não entrou com usuário (computador principal) continua podendo tudo, como antes.
- `eh_administrador(request: Request) -> bool`
- `protegido() -> bool`
- `_token() -> str \| None`
- `autorizado(request: Request) -> bool`
- `segundos_bloqueado(ip: str) -> int`
- `estado(request: Request) -> dict`
- `async entrar(senha: str, ip: str) -> tuple[bool, str \| None, int]` — Devolve (ok, token do cookie, segundos de bloqueio).
- `async middleware(request: Request, call_next)`

## `app/admin.py`

> Senha de administrador: protege as funções sensíveis (importação de boletos de outros sistemas).
> 
> * a senha só pode ser criada e trocada no computador onde o sistema está instalado (trocar exige a atual);
> * é guardada com PBKDF2 em ``dados/admin.json`` — nunca em texto;
> * após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos;
> * entrar abre uma sessão de 20 minutos (renovada a cada uso) num cookie HttpOnly; trocar a senha ou
>   clicar em "Bloquear" encerra as sessões.
> 
> Esqueceu a senha? No computador, feche o sistema, apague ``dados/admin.json`` e crie uma nova.

**Constantes:** `COOKIE` = `'leitor_admin'` · `TAMANHO_MINIMO` = `6` · `ITERACOES` = `200000` · `MAX_TENTATIVAS` = `5` · `BLOQUEIO_SEGUNDOS` = `300` · `DURACAO_SESSAO` = `20 * 60`

- **classe `GerenciadorAdmin`**
  - `__init__(self, caminho: Path)`
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `senha_definida(self) -> bool`
  - `_hash(senha: str, sal: bytes) -> str`
  - `definir_senha(self, nova: str) -> None`
  - `verificar(self, senha: str) -> bool`
  - `segundos_bloqueado(self, ip: str) -> int`
  - `registrar_falha(self, ip: str) -> None`
  - `entrar(self, senha: str, ip: str) -> tuple[str \| None, int]` — Devolve (token da sessão ou None, segundos de bloqueio).
  - `autorizado(self, token: str \| None) -> bool`
  - `sair(self, token: str \| None) -> None`
  - `status(self, token: str \| None, ip: str) -> dict`

## `app/arquivos.py`

> Armazenamento dos arquivos enviados (original + prévia JPEG para exibir no navegador).

**Constantes:** `RE_ID` = `re.compile('^[0-9a-f]{32}$')`

- **classe `RepositorioArquivos`**
  - `__init__(self, pasta: Path)`
  - `salvar(self, dados: bytes, nome_original: str) -> dict`
  - `meta(self, arquivo_id: str) -> dict \| None`
  - `caminho_original(self, arquivo_id: str) -> Path \| None`
  - `visualizacao(self, arquivo_id: str) -> tuple[Path, str, str] \| None`
  - `caminho_relativo(self, arquivo_id: str) -> str \| None`
  - `id_de_caminho(caminho_relativo: str \| None) -> str \| None`
  - `remover(self, arquivo_id: str) -> None`
  - `limpar_nao_referenciados(self, referenciados: set[str], dias: int) -> int` — Apaga arquivos enviados há mais de ``dias`` que nunca foram lançados na planilha.

## `app/atalhos.py`

> Atalhos do aplicativo na Área de Trabalho e no Menu Iniciar (Windows).

**Constantes:** `NOME` = `config.NOME_APP` · `NOMES_ANTIGOS` = `('Leitor de Boletos',)` · `ICONE` = `BASE_DIR / 'web' / 'icons' / 'app.ico'` · `_SCRIPT` = `"\n$ErrorActionPreference = 'Stop'\n[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n$shell = New-Object -ComObject WScript.Shell\n$criados = @()\nf…`

- `pythonw() -> Path`
- `_pastas_de_atalho() -> list[Path]`
- `_caminhos_provaveis(nome: str='') -> list[Path]`
- `remover_antigos() -> list[str]` — Apaga os atalhos com o nome antigo do aplicativo (para não ficarem dois ícones iguais).
- `status() -> dict`
- `criar_atalhos() -> list[str]`

## `app/backup.py`

> Backup TOTAL para fora do computador (pasta do OneDrive, Google Drive, Dropbox, pen drive ou HD externo).
> 
> Uma vez por dia, depois do horário escolhido, o sistema copia para ``<pasta escolhida>/Leitor de Boletos - Backup``
> **tudo o que é preciso para reerguer o Fin Pro em outro computador**:
> 
> * ``planilha/``       — uma cópia por dia de cada banco de dados (``boletos``, ``empresas``, ``diesel``) e de cada planilha;
> * ``arquivos/``       — PDFs, fotos, comprovantes, cupons, canhotos, cheques e notas (só copia o que é novo ou mudou);
> * ``configuracoes/``  — **todos** os arquivos de configuração da pasta de dados (lembretes, usuários, bots, preços…)
>   e o ``.env``;
> * ``codigo/``         — o **código-fonte** inteiro do sistema (espelho da pasta do sistema, sem o ambiente Python);
> * ``versoes/``        — o **histórico completo de versões** (``finpro.bundle``, do git) e ``VERSAO.txt``;
> * ``pacotes/``        — de tempos em tempos, **tudo isso num único arquivo .zip** (para pen drive ou para guardar);
> * ``manifesto.json``  — a lista de tudo o que há no backup, com tamanho e impressão digital (SHA-256) de cada arquivo;
> * ``LEIA-ME.txt``, ``RESTAURAR.bat`` e ``restaurar_backup.py`` — como (e com o quê) restaurar.
> 
> Depois de cada backup o sistema **confere** o que copiou (os bancos abrem? está tudo lá?). A conferência completa,
> que relê cada arquivo e compara a impressão digital, é feita pelo botão "Verificar backup".
> 
> A pasta do OneDrive/Google Drive é sincronizada com a nuvem pelo próprio programa deles: se o computador
> quebrar, os dados continuam na conta. Se o backup falhar, atrasar ou não passar na conferência, o sistema avisa na tela.

**Constantes:** `NOME_PASTA` = `'Leitor de Boletos - Backup'` · `CONFIGURACOES` = `('notificacoes.json', 'usuarios.json', 'admin.json', 'rede.json', 'importacao_modelos.json', 'backup.json', 'entrada.json', 'gravacao_pendente.json')` · `INTERVALO_VERIFICACAO` = `300` · `ESPERA_APOS_FALHA` = `timedelta(minutes=30)` · `ESPERA_APOS_FALHA_PACOTE` = `timedelta(hours=6)` · `DIAS_PARA_ALERTA` = `2` · `RE_COPIA` = `re.compile('^(?:boletos\|empresas\|diesel)-(\\d{4}-\\d{2}-\\d{2})\\.(xlsx\|db)$')` · `RE_PACOTE` = `re.compile('^Fin Pro - backup completo (\\d{4}-\\d{2}-\\d{2})_(\\d{4})\\.zip$')` · `PASTAS_FORA_DO_CODIGO` = `{'.venv', 'venv', '__pycache__', '.pytest_cache', '.git', 'node_modules', NOME_PASTA}` · `SUFIXOS_FORA_DO_CODIGO` = `{'.pyc', '.pyo', '.tmp', '.parcial'}` · `PACOTES` = `{'nunca': None, 'semanal': 7, 'mensal': 30}` · `SECOES` = `('planilha', 'arquivos', 'configuracoes', 'codigo', 'versoes')` · `NOME_BUNDLE` = `'finpro.bundle'` · `BLOCO` = `1024 * 1024` · `LEIA_ME` = `'BACKUP COMPLETO DO FIN PRO\n==========================\n\nEsta pasta é criada e atualizada automaticamente pelo Fin Pro (uma vez por dia). Ela tem TUDO o qu…` · `RESTAURAR_BAT` = `'@echo off\nchcp 65001 >nul\ntitle Restaurar o Fin Pro\necho.\necho  RESTAURAR O FIN PRO A PARTIR DESTE BACKUP\necho  ---------------------------------------…`

- `_agora() -> str`
- `_sha256(caminho: Path) -> str`
- `_tamanho_legivel(tamanho: int) -> str`
- `sugerir_pastas(base_usuario: Path \| None=None) -> list[dict]` — Pastas prováveis para o backup: nuvem (OneDrive, Google Drive, Dropbox) e unidades removíveis.
- **classe `GerenciadorBackup`**
  - `__init__(self, caminho_config: Path, pasta_dados: Path, planilha: Path, pasta_arquivos: Path, copiar_banco=None, extras: list[dict] \| None=None, pasta_codigo: Path \| None=None, informar_versao=None, gerar_bundle=None, verificar_bundle=None)` — ``copiar_banco(destino)`` faz uma cópia consistente do banco de dados (SQLite).
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `validar_pasta(self, pasta: str) -> Path`
  - `configurar(self, *, ativo: bool \| None=None, pasta: str \| None=None, horario: str \| None=None, manter_dias: int \| None=None, codigo: bool \| None=None, pacote: str \| None=None, manter_pacotes: int \| None=None) -> dict`
  - `status(self, agora: datetime \| None=None) -> dict`
  - `_destino(estado: dict) -> str \| None`
  - `_raiz(self) -> Path`
  - `executar(self) -> dict` — Faz o backup agora. Devolve o resultado (também guardado em ``ultimo``).
  - `_copiar(self, raiz: Path, manter_dias: int) -> dict`
  - `_copiar_se_mudou(origem: Path, destino: Path) -> bool`
  - `_arquivos_de_configuracao(self) -> list[Path]` — Todo ``*.json`` da pasta de dados (cada módulo novo entra sozinho) e o ``.env`` da pasta do sistema.
  - `_arquivos_do_codigo(self, raiz_backup: Path \| None=None) -> list[Path]` — Arquivos que formam o sistema: tudo da pasta do sistema, menos ambiente Python, caches, dados e o próprio backup.
  - `_espelhar_codigo(self, destino: Path, raiz_backup: Path) -> dict` — Deixa ``codigo/`` igual à pasta do sistema: copia o que mudou e remove o que não existe mais.
  - `_guardar_versoes(self, destino: Path) -> bool` — ``versoes/finpro.bundle`` (todo o histórico do git) e ``VERSAO.txt`` (qual versão este backup tem).
  - `_escrever_restaurador(self, raiz: Path) -> None`
  - `_arquivos_do_backup(raiz: Path)`
  - `_escrever_manifesto(self, raiz: Path) -> dict` — Lista tudo o que há no backup com tamanho e SHA-256 (reaproveita a impressão digital do que não mudou).
  - `pacotes(self, raiz: Path \| None=None) -> list[dict]` — Os pacotes .zip guardados, do mais novo para o mais antigo.
  - `gerar_pacote(self, agora: datetime \| None=None) -> dict` — Atualiza o backup e guarda **tudo num único arquivo .zip** (código, versões, bancos, arquivos e configurações).
  - `_copias_mais_recentes(raiz: Path) -> set[Path]` — A cópia de data mais nova de cada banco e de cada planilha.
  - `pacote_devido(self, agora: datetime \| None=None) -> bool` — Já passou o intervalo (semanal ou mensal) desde o último pacote .zip?
  - `verificar(self, completa: bool=True) -> dict` — Confere o backup. ``completa``: relê cada arquivo e compara a impressão digital com o manifesto.
  - `_verificar(self, completa: bool) -> dict`
  - `deve_executar(self, agora: datetime \| None=None) -> bool`
  - `rodar_agendado(self, agora: datetime \| None=None) -> None` — Uma passada do agendador: o backup do dia e, quando for a vez, o pacote .zip.
  - `iniciar_agendador(self, espera_inicial: float=60) -> None`
  - `parar(self) -> None`

## `app/banco.py`

> Banco de dados (SQLite) dos boletos, Pix, centros de custo e histórico — com a planilha Excel sempre atualizada.
> 
> Por que: a planilha era o banco de dados, e cada alteração reescrevia o arquivo Excel inteiro (lento conforme cresce,
> e travado quando alguém deixava o arquivo aberto no Excel). Agora:
> 
> * os dados ficam em ``dados/boletos.db`` (SQLite: rápido, gravações seguras, várias pessoas ao mesmo tempo);
> * a planilha ``boletos.xlsx`` continua existindo, no mesmo formato, e é **gerada automaticamente** poucos segundos
>   depois de cada alteração. Se estiver aberta no Excel, é atualizada assim que o arquivo for fechado — os
>   lançamentos nunca ficam esperando;
> * **edições feitas no Excel** (ex.: mudar o status ou o centro de custo de um boleto e salvar) são trazidas para o
>   sistema. Só os campos que a pessoa mudou no Excel são aplicados, então nada que o sistema gravou nesse meio-tempo
>   (um pagamento pelo bot, por exemplo) é desfeito. Para lançar ou excluir, use o sistema;
> * na primeira vez, tudo o que está na planilha é importado para o banco, com os mesmos IDs e o histórico.
> 
> A classe tem a mesma interface de ``PlanilhaBoletos`` (listar, obter, aplicar_lote, histórico, centros...).

**Constantes:** `ESPERA_EXPORTACAO` = `1.5` · `INTERVALO_VERIFICACAO` = `15` · `USUARIO_EXCEL` = `'Planilha Excel (edição manual)'`

- `_para_banco(registro: dict) -> str`
- `_do_banco(texto: str) -> dict`
- `_normalizar(registro: dict, definicao) -> dict` — Mesmo formato que a leitura da planilha devolve (textos vazios como "", valores com 2 casas).
- `_igual(a, b) -> bool`
- **classe `BancoBoletos`**
  - `__init__(self, caminho_banco: Path, caminho_planilha: Path, pasta_backup: Path \| None=None, abas: dict \| None=None, centros: bool=True, nome_backup: str='boletos')` — ``abas``: conjunto de abas (padrão: Boletos e Pix). ``centros``: usar a aba Centros de Custo e o Resumo.
  - `_conexao(self)`
  - `_criar_tabelas(self) -> None`
  - `_meta(self, c, chave: str, valor=None, gravar: bool=False)`
  - `_mudou(self) -> None`
  - `vazio(self) -> bool`
  - `garantir(self) -> None`
  - `migrar(self) -> bool` — Na primeira vez, importa a planilha existente (boletos, Pix, centros e histórico). Depois, traz edições do Excel.
  - `_ler_historico_da_planilha(self) -> list[tuple]`
  - `listar(self, aba: str='') -> list[dict]`
  - `obter(self, id_: int, aba: str='') -> dict`
  - `buscar_por_codigo(self, codigo_barras: str) -> list[dict]`
  - `nomes_por_documento(self) -> dict[str, str]`
  - `listar_centros(self) -> list[dict]`
  - `historico_do_registro(self, id_: int, aba: str='', desde: datetime \| None=None) -> list[dict]`
  - `contagens(self) -> dict`
  - `aplicar_lote(self, operacoes: list[dict]) -> list[dict]` — Mesmo contrato de ``PlanilhaBoletos.aplicar_lote``, numa única transação do banco.
  - `adicionar(self, dados: dict, aba: str='', usuario: str='') -> dict`
  - `adicionar_lote(self, lista: list[dict], aba: str='', usuario: str='') -> list[dict]`
  - `atualizar(self, id_: int, alteracoes: dict, aba: str='', usuario: str='') -> dict`
  - `excluir(self, id_: int, aba: str='', usuario: str='') -> None`
  - `salvar_centro(self, nome: str, descricao: str='', ativo: bool=True, nome_anterior: str \| None=None, usuario: str='') -> dict`
  - `_montar_planilha(self) -> Workbook`
  - `exportar(self) -> bool` — Gera a planilha Excel a partir do banco. Devolve False se o arquivo estiver aberto no Excel (tenta de novo depois).
  - `exportar_agora(self) -> bool`
  - `_salvar_snapshot(self) -> None` — Guarda o que foi escrito na planilha e a data do arquivo: base para saber o que alguém mudou no Excel.
  - `importar_edicoes_do_excel(self) -> int` — Se a planilha foi salva por alguém no Excel, aplica no banco os campos que a pessoa alterou.
  - `_backup_diario_banco(self) -> None`
  - `copiar_banco(self, destino: Path) -> None` — Cópia consistente do banco (mesmo com o sistema gravando), para backup.
  - `status(self) -> dict`
  - `iniciar_sincronizacao(self) -> None`
  - `parar(self) -> None`

## `app/boleto/__init__.py`


## `app/boleto/bancos.py`

> Tabelas de referência: bancos (código COMPE) e segmentos de arrecadação.

**Constantes:** `BANCOS` = `{'001': 'Banco do Brasil', '003': 'Banco da Amazônia', '004': 'Banco do Nordeste', '021': 'Banestes', '025': 'Banco Alfa', '033': 'Santander', '037': 'Banpar…` · `SEGMENTOS_ARRECADACAO` = `{'1': 'Prefeituras', '2': 'Saneamento', '3': 'Energia elétrica e gás', '4': 'Telecomunicações', '5': 'Órgãos governamentais', '6': 'Carnês e assemelhados', '…`

- `nome_banco(codigo: str) -> str`

## `app/boleto/codigo.py`

> Linha digitável e código de barras de boletos (padrões FEBRABAN).
> 
> Suporta os dois tipos de boleto usados no Brasil:
> 
> * **Bancário (cobrança)** — linha digitável com 47 dígitos, código de barras com 44.
> * **Arrecadação (concessionárias, tributos, convênios)** — linha com 48 dígitos
>   (4 blocos de 11 + DV), código de barras com 44 começando por ``8``.
> 
> Inclui validação de todos os dígitos verificadores, conversão entre os formatos,
> decodificação de banco/valor/vencimento e correção automática de um dígito
> lido errado (útil para OCR).

**Constantes:** `BASE_FATOR_ORIGINAL` = `date(1997, 10, 7)` · `BASE_FATOR_NOVO_CICLO` = `date(2025, 2, 22) - timedelta(days=1000)` · `BANCARIO` = `'bancario'` · `ARRECADACAO` = `'arrecadacao'` · `_CONFUSOES_OCR` = `{frozenset(p) for p in (('0', '8'), ('3', '8'), ('5', '6'), ('6', '8'), ('1', '7'), ('4', '9'), ('0', '6'), ('0', '9'), ('5', '8'), ('2', '7'), ('1', '4'), (…`

- `somente_digitos(texto: str \| None) -> str`
- `modulo10(numero: str) -> int`
- `_soma_modulo11(numero: str) -> int`
- `modulo11_bancario(numero: str) -> int`
- `modulo11_arrecadacao(numero: str) -> int`
- `_dv_arrecadacao(numero: str, identificador: str) -> int`
- `linha_para_barras_bancario(linha: str) -> str`
- `barras_para_linha_bancario(barras: str) -> str`
- `linha_para_barras_arrecadacao(linha: str) -> str`
- `barras_para_linha_arrecadacao(barras: str) -> str`
- `formatar_linha(linha: str) -> str` — Formata a linha digitável como aparece impressa no boleto.
- `data_por_fator(fator: int, referencia: date \| None=None) -> date \| None` — Converte o fator de vencimento em data, escolhendo o ciclo mais próximo da referência.
- `fator_por_data(vencimento: date) -> int`
- `_data_no_campo_livre(barras: str, referencia: date) -> date \| None` — Convênios costumam (sem obrigatoriedade) gravar o vencimento como AAAAMMDD no campo livre.
- **classe `ResultadoCodigo`**
  - `linha_formatada(self) -> str`
  - `emissor(self) -> str`
  - `para_dict(self) -> dict`
- `_analisar_bancario(linha: str \| None, barras: str, referencia: date) -> ResultadoCodigo`
- `_analisar_arrecadacao(linha: str \| None, barras: str, referencia: date) -> ResultadoCodigo`
- `analisar(codigo: str, referencia: date \| None=None) -> ResultadoCodigo \| None` — Analisa uma linha digitável (47/48 dígitos) ou código de barras (44 dígitos).
- `_variacoes_um_digito(trecho: str, valido) -> list[str]`
- `_plausibilidade(original: str, corrigido: str) -> tuple[int, int]`
- `candidatos_correcao(codigo: str, referencia: date \| None=None, limite: int=6) -> list[ResultadoCodigo]` — Linhas válidas próximas da informada, das mais para as menos prováveis.
- `tentar_corrigir(codigo: str, referencia: date \| None=None) -> ResultadoCodigo \| None` — Retorna a linha válida (corrigida se preciso) apenas quando a correção é única.

## `app/boleto/extrator.py`

> Orquestra a leitura: arquivo → códigos + campos → boletos consolidados, com fonte, confiança e alertas.
> 
> Ordem de confiança por campo:
> * Linha digitável / código de barras: código de barras da imagem > texto do PDF > OCR > IA.
> * Vencimento e valor: decodificados do código (exatos) — o impresso serve para conferência.
> * Beneficiário, CPF/CNPJ e nº do documento: texto do PDF > OCR > IA.
> 
> Tratamentos especiais:
> * Fotos de papel: recorte e correção de perspectiva ("modo scanner"), rotação pelo código de barras.
> * PDFs escaneados com camada de texto ruim: OCR complementar para preencher o que faltar.
> * Guias de tributos (DAS, DARF, GPS...): beneficiário é o órgão arrecadador.
> * Contas de consumo sem rótulo "Beneficiário": nome em destaque no cabeçalho.

**Constantes:** `CAMPOS_DOCUMENTO` = `('beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor')` · `ORDEM_CAMPOS` = `('linha_digitavel', 'codigo_barras', 'beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor')` · `_PESO_NIVEL` = `{'erro': 0, 'aviso': 1, 'info': 2}`

- **classe `ErroLeitura`** — Arquivo ilegível ou em formato não suportado.
- **classe `Campo`**
  - `para_dict(self) -> dict`
- `_alerta(nivel: str, mensagem: str, codigo: str \| None=None) -> dict`
- `_brl(valor) -> str`
- `_data_br(d: date) -> str`
- `_decimal(valor) -> Decimal \| None`
- `consolidar(codigo: ResultadoCodigo \| None, *, campos_doc: dict[str, Campo], referencia: date, fonte_codigo: str='codigo_barras', confianca_codigo: float=0.99, planilha=None, sugestoes: list[ResultadoCodigo] \| None=None, alertas: list[dict] \| None=None, pagina: int=0) -> dict` — Combina o código decodificado com os campos lidos do documento e gera alertas.
- `_campos_de_texto(campos: dict[str, CampoTexto], fonte: str) -> dict[str, Campo]`
- `_texto_pdf_util(pagina: PaginaLida) -> bool`
- `_pontuacao_ocr(segmentos) -> float`
- `_texto_vertical(segmentos) -> bool` — A maioria das linhas de texto está na vertical (página girada 90°)?
- `_qualidade_layout(segmentos, altura: float) -> tuple[int, float]`
- `_ocr_pagina(pagina: PaginaLida, tentar_rotacoes: bool) -> None`
- `_ocr_complementar(pagina: PaginaLida) -> SimpleNamespace`
- `_completar_emissor(campos_doc: dict[str, Campo], codigo: ResultadoCodigo \| None, segmentos, texto: str, altura: float, fonte: str) -> None` — Beneficiário de guias de tributos e de contas de consumo sem rótulo.
- `_desempatar(sugestoes: list[ResultadoCodigo], campos_doc: dict[str, Campo]) -> ResultadoCodigo \| None` — Escolhe entre correções possíveis usando o valor/vencimento impressos.
- `_codigos_da_pagina(barras, codigos_texto, altura: float, fonte_texto: str) -> dict[str, dict]`
- `_recalcular_confianca(boleto: dict) -> None`
- `harmonizar_beneficiarios(boletos: list[dict], planilha=None) -> None` — Mesmo CPF/CNPJ → mesmo nome de beneficiário.
- `ler_arquivo(dados: bytes, *, planilha=None, referencia: date \| None=None, max_paginas: int=30, ao_progresso=None) -> dict` — Lê um PDF ou imagem e devolve os boletos encontrados.
- `analisar_linha_digitada(linha: str, *, planilha=None, referencia: date \| None=None) -> dict`
- `_converter_campo(nome: str, valor) -> Any`
- `mesclar_ia(campos_atuais: dict, dados_ia: dict, *, planilha=None, referencia: date \| None=None, pagina: int=0) -> dict` — Completa/confirma os campos atuais com o que a IA leu, sem confiar cegamente nela.

## `app/boleto/imagem.py`

> Tratamento de fotos de boletos em papel: recorte do papel e correção de perspectiva ("modo scanner").

- `_ordenar_cantos(pontos: np.ndarray) -> np.ndarray` — Ordena 4 pontos como superior-esquerdo, superior-direito, inferior-direito, inferior-esquerdo.
- `_contorno_do_papel(cinza: np.ndarray) -> np.ndarray \| None`
- `endireitar_documento(imagem: Image.Image) -> tuple[Image.Image, bool]` — Recorta o papel da foto e corrige a perspectiva. Devolve (imagem, corrigiu?).
- `melhorar_para_ocr(imagem: Image.Image) -> Image.Image` — Uniformiza a iluminação (remove sombras suaves) mantendo a imagem em tons de cinza.

## `app/boleto/leitores.py`

> Leitura de arquivos: PDF (texto posicionado + renderização), imagens e código de barras.

**Constantes:** `LADO_MAXIMO_IMAGEM` = `3200`

- `eh_pdf(dados: bytes) -> bool`
- **classe `PaginaLida`**
- `_segmentos_textpage(textpage, altura_pagina: float, indice: int) -> list[Segmento]`
- `_cobertura_de_imagens(pagina, largura: float, altura: float) -> float` — Fração da página ocupada por imagens (≈1 em PDFs escaneados).
- **classe `DocumentoPDF`** — PDF aberto para leitura página a página.
  - `__init__(self, dados: bytes)`
  - `_ler_pagina(self, indice: int, escala_maxima: float, lado_render: int) -> PaginaLida`
  - `paginas(self, max_paginas: int=30, escala_maxima: float=3.0, lado_render: int=3000)`
  - `fechar(self) -> None`
- `ler_pdf(dados: bytes, max_paginas: int=30, escala_maxima: float=3.0, lado_render: int=3000) -> tuple[list[PaginaLida], int]` — Lê até ``max_paginas`` páginas de uma vez. Devolve (páginas lidas, total de páginas do PDF).
- `abrir_imagem(dados: bytes) -> Image.Image`
- **classe `LeituraBarras`**
- `_variantes_para_barras(imagem: Image.Image)`
- `ler_codigos_barras(imagem: Image.Image) -> list[LeituraBarras]` — Decodifica códigos ITF (Interleaved 2 of 5) de 44 dígitos com dígitos verificadores válidos.
- `texto_de_segmentos(segmentos: list[Segmento]) -> str`

## `app/boleto/ocr.py`

> OCR local.
> 
> Usa o RapidOCR 3 com o modelo de reconhecimento **latino** (PP-OCRv5), que lê acentos e
> espaços do português. Os modelos são baixados uma única vez na primeira execução. Sem
> internet nesse momento, cai automaticamente para o modelo básico do ``rapidocr_onnxruntime``.
> 
> Os resultados ficam em cache pelo conteúdo da imagem: reenviar o mesmo arquivo (ou a mesma
> página em outra rotação já testada) não repete o OCR, que é a etapa mais lenta da leitura.

**Constantes:** `TAMANHO_CACHE` = `64`

- **classe `MotorOCR`**
  - `__init__(self)`
  - `disponivel(self) -> bool`
  - `modelo(self) -> str \| None`
  - `carregar(self)`
  - `_carregar(self)`
  - `_reconhecer_bruto(self, rgb: np.ndarray) -> list[tuple]`
  - `reconhecer(self, imagem: Image.Image, pagina: int=0) -> list[Segmento]`

## `app/boleto/texto.py`

> Extração de campos do boleto a partir de texto posicionado (camada de texto do PDF ou OCR).
> 
> Boletos seguem um leiaute de "ficha": rótulos pequenos (Beneficiário, Vencimento,
> Nº do Documento, Valor do Documento...) com o valor ao lado ou logo abaixo.
> A busca é espacial — para cada rótulo procuramos o valor no mesmo trecho, à direita
> ou abaixo — com expressões regulares no texto corrido como plano B.

**Constantes:** `_MAPA_ESPECIAL` = `{'º': 'o', '°': 'o', 'ª': 'a', '–': '-', '—': '-', '‐': '-'}` · `_LIGADURAS` = `str.maketrans({'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', '\xa0': ' ', '\xad': ''})` · `RE_DATA` = `re.compile('(?<!\\d)(\\d{2})\\s?[/.\\-]\\s?(\\d{2})\\s?[/.\\-]\\s?(\\d{4}\|\\d{2})(?!\\d)')` · `RE_MOEDA` = `re.compile('(?<![\\d,])(\\d{1,3}(?:\\.\\d{3})+\|\\d+),(\\d{2})(?!\\d)')` · `RE_CNPJ` = `re.compile('(?<!\\d)\\d{2}\\.?\\d{3}\\.?\\d{3}\\s?/\\s?\\d{4}\\s?-?\\s?\\d{2}(?!\\d)')` · `RE_CPF` = `re.compile('(?<!\\d)\\d{3}\\.\\d{3}\\.\\d{3}-?\\d{2}(?!\\d)')` · `_MESES_TEXTO` = `{m: i for i, m in enumerate(('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'), 1)}` · `_RE_DATA_EXTENSO` = `re.compile('(?<!\\d)(\\d{1,2})\\s*(?:/\|-\|\\.\|de)?\\s*(jan\|fev\|mar\|abr\|mai\|jun\|jul\|ago\|set\|out\|nov\|dez)[a-z]*\\.?\\s*(?:/\|-\|\\.\|de)?\\s*(\\d{4})(?!\\d)')` · `RE_CNPJ_SEM_FORMATO` = `re.compile('(?<!\\d)\\d{14}(?!\\d)')` · `_PALAVRAS_ROTULO` = `re.compile('agencia\|codigo\|vencimento\|local de pagamento\|pagavel\|nosso numero\|data d[oe]\|especie\|aceite\|carteira\|pagador\|sacado\|instruc\|valor\|bene\\w{2,6}rio…` · `_PREPOSICOES` = `{'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'ao', 'aos', 'com', 'para', 'em', 'no', 'na', 'pelo', 'pela'}` · `_CONECTORES_NOME` = `{'e', 'de', 'da', 'do', 'dos', 'das', '&'}` · `_RE_ENDERECO` = `re.compile('(?:^\|[\\s,\\-–])(av\\.?\|avenida\|rua\|r\\.\|rodovia\|rod\\.\|estrada\|alameda\|travessa\|praca\|br-?\\d{2,3}\|cep)(?=[\\s.:,]\|$)')` · `_VOCABULARIO` = `set('\nEMPRESA EMPRESAS EXEMPLO COMERCIO COMERCIAL SERVICOS SERVICO INDUSTRIA INDUSTRIAL INDUSTRIAS CONSTRUCOES CONSTRUCAO\nCONSTRUTORA ENGENHARIA TECNOLOGIA…` · `_SUFIXOS` = `{'LTDA', 'ME', 'EPP', 'SA', 'EIRELI', 'MEI', 'CIA'}` · `_CONECTORES` = `{'DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'EM'}` · `_RE_TRECHO_NUMERICO` = `re.compile('[0-9OoIl\|SBZ](?:[0-9OoIl\|SBZ.\\- \\t]){38,}[0-9OoIl\|SBZ]')` · `_TRADUCAO_OCR` = `str.maketrans({'O': '0', 'o': '0', 'I': '1', 'l': '1', '\|': '1', 'S': '5', 'B': '8', 'Z': '2'})` · `ROTULOS_BENEFICIARIO` = `[_Rotulo(re.compile('\\bbene\\w{2,6}rio\\b\|\\bcedente\\b'), excluir_antes=re.compile('(agencia\|codigo\|cod\\.?\|cpf\|cnpj\|endereco\|sacador\|avalista)[^a-z]*(d[oe…` · `ROTULOS_VENCIMENTO` = `[_Rotulo(re.compile('\\bvenc(imento\|to)?\\b\\.?')), _Rotulo(re.compile('\\bpag(ar\|avel\|amento)\\b[a-z\\s]{0,25}?\\bate\\b'), prioridade=1), _Rotulo(re.compil…` · `ROTULOS_DOCUMENTO` = `[_Rotulo(re.compile('\\b(n\|no\|nr\|nro\|num\|numero)\\s*[.:]?\\s*(d[oea]\\s*)?doc(umento\|to)?\\b\\.?')), _Rotulo(re.compile('\\bseu\\s+numero\\b\|\\bn\\.?\\s*(o\\…` · `_EXCLUIR_VALOR` = `re.compile('desconto\|abatimento\|mora\|multa\|juros\|acrescimo\|deduc\|outros\|encargo')` · `ROTULOS_VALOR` = `[_Rotulo(re.compile('valor\\s*(d[oe]\\s*)?documento'), excluir_segmento=_EXCLUIR_VALOR), _Rotulo(re.compile('valor\\s+cobrado\|valor\\s+a\\s+pagar\|total\\s+a\…` · `_FALLBACK` = `{'vencimento': (re.compile('(?:venc\\w*\|pagar[a-z\\s]{0,25}ate)\\W{0,20}(\\d{2}/\\d{2}/\\d{4})', re.S), extrair_data), 'valor': (re.compile('valor\\s*(?:d[oe…` · `_GUIAS` = `[('documento de arrecadacao do simples nacional\|simples nacional\|\\bdas[-\\s]?mei\\b', 'Receita Federal - Simples Nacional (DAS)'), ('\\bdarf\\b\|documento de…` · `_NAO_E_NOME` = `re.compile('\\bbanco\\b\|recibo\|ficha\|compensacao\|pagavel\|autenticacao\|\\bconta\\b\|fatura\|segunda via\|\\b2a via\\b\|documento de arrecadacao\|boleto\|nota fiscal…` · `_NOMES_BANCOS` = `{normalizar(nome).split(' (')[0] for nome in BANCOS.values()}`

- **classe `Segmento`** — Trecho de texto com caixa delimitadora (origem no canto superior esquerdo).
  - `altura(self) -> float`
  - `cy(self) -> float`
- **classe `CampoTexto`**
- **classe `CodigoEncontrado`**
- `normalizar(texto: str) -> str` — Minúsculas e sem acentos, preservando o comprimento (índices batem com o original).
- `corrigir_ligaduras(texto: str) -> str` — PDFs costumam trazer ligaduras tipográficas ("Beneﬁciário") e espaços especiais.
- `extrair_data(texto: str) -> date \| None`
- `extrair_valor(texto: str) -> Decimal \| None`
- `cnpj_valido(digitos: str) -> bool`
- `extrair_cpf_cnpj(texto: str) -> str \| None`
- `extrair_documento(texto: str) -> str \| None`
- `_letras(texto: str) -> int`
- `_posicao_documento(texto: str) -> tuple[int, int] \| None` — Posição do primeiro CPF/CNPJ (formatado ou CNPJ válido sem pontuação) no texto.
- `extrair_beneficiario(texto: str) -> str \| None`
- `segmentar_palavras(texto: str) -> str` — Reinsere espaços em trechos longos sem espaço, se isso formar palavras conhecidas.
- `_codigos_no_trecho(trecho: str, referencia: date \| None) -> list[CodigoEncontrado]`
- `encontrar_codigos(texto: str, referencia: date \| None=None) -> list[CodigoEncontrado]` — Procura linhas digitáveis/códigos de barras no texto (tolerando ruído de OCR).
- `encontrar_codigos_segmentos(segmentos: list[Segmento], referencia: date \| None=None) -> list[CodigoEncontrado]` — Como ``encontrar_codigos``, mas registra a posição vertical de cada código.
- `agrupar_linhas(segmentos: list[Segmento]) -> list[list[Segmento]]` — Agrupa segmentos em linhas visuais (mesma página e sobreposição vertical).
- **classe `_Rotulo`**
- `_sobrepoe_vertical(a: Segmento, b: Segmento) -> bool`
- `_buscar_campo(segmentos: list[Segmento], rotulos: list[_Rotulo], extrair: Callable[[str], object \| None], y_ref: float \| None=None, altura_pagina: float \| None=None) -> tuple[CampoTexto \| None, Segmento \| None]`
- `extrair_campos(segmentos: list[Segmento], texto: str, y_ref: float \| None=None, altura_pagina: float \| None=None) -> dict[str, CampoTexto]` — Extrai beneficiário, CPF/CNPJ, nº do documento, vencimento e valor.
- `identificar_guia(texto: str) -> str \| None` — Reconhece guias de tributos, cujo "beneficiário" é o órgão arrecadador (não a empresa do texto).
- `nome_no_cabecalho(segmentos: list[Segmento], altura_pagina: float \| None) -> tuple[CampoTexto \| None, str \| None]` — Nome em destaque (fonte maior) no topo da página e CNPJ próximo — típico de contas de consumo.

## `app/bot.py`

> Comandos do bot do Telegram: quem paga consulta pelo celular o que vence e já copia a linha digitável ou o Pix.
> 
> Só respondem as pessoas e grupos cadastrados em Notificações → Telegram (e com o recebimento pelo Telegram ligado).
> 
> /vencidos  — boletos e Pix em atraso
> /hoje      — o que vence hoje
> /semana    — o que vence nos próximos 7 dias
> /previsao  — quanto vai sair nas próximas semanas
> /buscar    — procura um boleto ou Pix pendente pelo nome (ex.: /buscar energisa)
> /resumo    — totais: em atraso, 7 dias, 30 dias e pagos no mês
> /ajuda     — lista dos comandos

**Constantes:** `COMANDOS` = `[('vencidos', 'Boletos e Pix em atraso'), ('hoje', 'O que vence hoje'), ('semana', 'O que vence nos próximos 7 dias'), ('previsao', 'Quanto vai sair nas próx…` · `LIMITE_MENSAGEM` = `3800` · `MAX_ITENS` = `40`

- `_moeda(valor) -> str`
- `_pendentes(hoje: date) -> list[dict]`
- `_quando(venc, hoje: date) -> str`
- `_item(r: dict, hoje: date) -> str`
- `_lista(titulo: str, itens: list[dict], hoje: date, vazio: str) -> list[str]`
- `ajuda(nome: str='') -> str`
- `responder(texto: str, nome: str='', hoje: date \| None=None) -> list[str] \| None` — Resposta (em HTML do Telegram) para uma mensagem de texto. None quando não é um comando.

## `app/busca_comprovantes.py`

> Central de comprovantes: acha o comprovante de qualquer lançamento (boletos, Pix, cheques, recebimentos das
> empresas, caixa e notas fiscais) com filtros por nome, valor, data, número (cheque, NF, documento, pedido,
> ID da transação), centro de custo e pessoa — e baixa tudo o que foi filtrado num ZIP.
> 
> Cada lançamento vira um item no mesmo formato. ``comprovante_id`` é o arquivo que prova o pagamento/recebimento
> (o comprovante do boleto ou Pix, a foto do cheque, o comprovante do Pix recebido, o cupom do caixa, a nota fiscal);
> ``original_id`` é o arquivo do próprio boleto/cobrança, quando existe.

**Constantes:** `TIPOS` = `{'boleto': 'Boleto', 'pix': 'Pix', 'cheque': 'Cheque', 'recebimento': 'Recebimento', 'caixa': 'Caixa (dinheiro)', 'nota': 'Nota fiscal', 'diesel': 'Diesel'}` · `PERMISSAO_DO_TIPO` = `{'cheque': 'empresas', 'recebimento': 'empresas', 'nota': 'empresas', 'caixa': 'caixa', 'diesel': 'diesel'}` · `LIMITE_ZIP` = `500` · `FONTES` = `{'boleto': _boletos, 'pix': _pix, 'caixa': _caixa, 'cheque': _cheques, 'recebimento': _recebimentos, 'nota': _notas, 'diesel': _diesel}`

- `_normal(texto) -> str`
- `_digitos(texto) -> str`
- `_data(valor) -> date \| None`
- `_num(valor) -> float`
- `_id(caminho) -> str \| None`
- `_item(tipo: str, registro: dict, **campos) -> dict`
- `_boletos() -> list[dict]`
- `_pix() -> list[dict]`
- `_caixa() -> list[dict]`
- `_cheques() -> list[dict]`
- `_recebimentos() -> list[dict]`
- `_notas() -> list[dict]` — Uma nota fiscal pode ter várias linhas (um material por linha): vira um item só, com o total da nota.
- `_diesel() -> list[dict]` — Comprovantes da compra no posto e os canhotos dos abastecimentos.
- `tipos_permitidos(pode) -> list[str]` — ``pode(permissao)``: a pessoa que está buscando pode ver essa parte do sistema?
- `_valor_pesquisado(texto: str) -> float \| None`
- `_na_linha(digitos: str, item: dict) -> bool` — Linha digitável só entra na busca com um trecho grande (8+ dígitos): números curtos achariam boletos por acaso.
- `buscar(pode=lambda _p: True, *, q: str='', tipos: list[str] \| None=None, de: date \| None=None, ate: date \| None=None, valor: str='', valor_min: float \| None=None, valor_max: float \| None=None, numero: str='', centro: str='', pessoa: str='', comprovante: str='com', ordenar: str='data', direcao: str='desc') -> list[dict]`
- `resumo(itens: list[dict]) -> dict`
- `serializar(item: dict) -> dict`
- `_nome_arquivo(item: dict, extensao: str) -> str`
- `gerar_zip(itens: list[dict]) -> tuple[bytes, int]` — ZIP com os comprovantes dos itens (nomes com data, tipo, nome, número e valor). Devolve o ZIP e quantos entraram.

## `app/caixa/__init__.py`

> Caixa: o dinheiro vivo que entra (o que foi pedido) e que sai (onde foi gasto e em qual centro de custo).
> 
> * os lançamentos ficam no mesmo banco dos boletos e Pix (aba **Caixa** da planilha), com histórico e backup;
> * entradas e saídas podem ser vistas por **dia, semana, mês ou ano**, com relatórios de onde mais se gastou;
> * as saídas entram na análise da aba **Gastos**, junto com boletos e Pix;
> * um **bot do Telegram só para o caixa** recebe a foto do cupom ou da nota, pergunta onde foi gasto e o centro de
>   custo, e deixa tudo preenchido no sistema para alguém revisar e lançar.


## `app/caixa/bot.py`

> Bot do caixa (Telegram): recebe a foto do cupom ou da nota de uma compra paga em dinheiro.
> 
> É um terceiro bot, só para o caixa. Quem pode usar são as mesmas pessoas e grupos já cadastrados no bot dos
> boletos e no bot de notas — a lista vem de lá, sem cadastrar de novo.
> 
> A cada foto, o bot conversa:
> 
> 1. lê o **valor** (e a data e a loja) do cupom; se não conseguir, pergunta o valor;
> 2. pergunta **onde foi gasto** (ex.: "gasolina da caminhonete");
> 3. mostra os **centros de custo** da aba Gastos como botões — e um botão para **cadastrar um novo**;
> 4. deixa tudo preenchido no Fin Pro (Caixa → Conferência) para alguém revisar e lançar.

**Constantes:** `MASCARA` = `'••••••••'` · `INTERVALO` = `20` · `TAMANHO_MAXIMO` = `20 * 1024 * 1024` · `EXTENSOES` = `('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.xml')` · `MAX_ITENS` = `300` · `DIAS_MANTER_CONCLUIDOS` = `30` · `COMANDOS` = `[('ajuda', 'Como mandar um gasto do caixa'), ('resumo', 'Entradas e saídas de hoje e do mês'), ('cancelar', 'Desistir do gasto que está sendo informado')]` · `PADRAO` = `{'config': {'ativo': False, 'token': '', 'offset': 0, 'ultima_verificacao': None, 'ultimo_erro': None}, 'itens': [], 'conversas': {}}`

- `_agora() -> str`
- `_moeda(valor) -> str`
- `_valor_digitado(texto: str) -> float \| None`
- **classe `BotCaixa`**
  - `__init__(self, caminho: Path, salvar_arquivo: Callable[[bytes, str], dict], pessoas: Callable[[], dict], centros: Callable[[], list[str]], criar_centro: Callable[[str, str], str], ler: Callable[[bytes, str], dict] \| None=None)` — ``pessoas()`` → {chat_id: nome} (quem já está nos outros bots); ``centros()`` → nomes dos centros de custo; ``criar_centro(nome, usuario)`` cadastra um centro novo; ``ler(dados, nome)`` lê valor, data e loja do cupom.
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `token(self) -> str`
  - `config_publica(self) -> dict`
  - `configurar(self, novo: dict) -> dict`
  - `dados_preenchidos(item: dict) -> dict` — O lançamento já montado, do jeito que vai para o caixa (a tela só revisa e lança).
  - `_publico(self, item: dict) -> dict`
  - `listar(self, incluir_concluidos: bool=False) -> list[dict]`
  - `contagem(self) -> int`
  - `arquivos_em_uso(self) -> set[str]`
  - `_item(self, id_: str) -> dict \| None`
  - `descartar(self, id_: str) -> bool`
  - `confirmar(self, id_: str, dados: dict, usuario: str) -> dict` — Alguém revisou na tela e mandou lançar no caixa.
  - `_encerrar_conversa_do_item(self, item: dict) -> None`
  - `_limpar_antigos(self) -> None`
  - `_enviar(self, chat_id: str, texto: str, botoes: list[list[dict]] \| None=None) -> None`
  - `_responder_botao(self, callback_id: str, chat_id: str, message_id, texto: str='') -> None`
  - `_registrar_comandos(self) -> None`
  - `_perguntar_onde(self, chat_id: str, item: dict) -> None`
  - `_perguntar_centro(self, chat_id: str, conversa: dict) -> None`
  - `_finalizar(self, chat_id: str, item: dict) -> None`
  - `_nova_foto(self, chat_id: str, remetente: str, dados: bytes, nome_arquivo: str) -> None`
  - `_texto(self, chat_id: str, texto: str) -> None`
  - `_criar_centro(self, chat_id: str, conversa: dict, item: dict, nome: str) -> None`
  - `_botao(self, chat_id: str, dado: str, callback_id: str, message_id) -> None`
  - `_comando(self, chat_id: str, texto: str, nome: str) -> None`
  - `_arquivo(mensagem: dict) -> tuple[str, str, int] \| None`
  - `verificar(self) -> dict`
  - `_tratar(self, atualizacao: dict, autorizados: dict) -> int`
  - `verificar_agora(self) -> dict`
  - `iniciar_agendador(self, espera_inicial: float=25) -> None`
  - `parar(self) -> None`

## `app/caixa/leitura.py`

> Leitura do cupom fiscal ou da nota de uma compra paga em dinheiro: valor, data, hora e onde foi.
> 
> O valor certo é o **a pagar** (ou o total) — nunca o dinheiro entregue nem o troco, que também aparecem no cupom.

**Constantes:** `ROTULOS_TOTAL` = `('valor a pagar', 'total a pagar', 'valor total', 'total geral', 'total da (nota\|compra\|venda)', 'total\\s*r\\$', '\\btotal\\b')` · `NAO_E_TOTAL` = `('troco', 'dinheiro', 'valor pago', 'valor recebido', 'recebido', 'desconto', 'acrescimo', 'tributo', 'imposto', '12.741', '12741', 'itens', 'qtd', 'quantida…` · `CABECALHOS` = `('documento auxiliar', 'cupom', 'nfc-e', 'nfce', 'nota fiscal', 'consumidor', 'extrato', 'sat ', 'cnpj', 'inscricao', 'ie:', 'endereco', 'danfe', 'emissao', …`

- `valor_total(texto: str) -> float \| None`
- `estabelecimento(texto: str) -> str` — Nome da loja: a primeira linha com cara de nome, antes do CNPJ, que não é cabeçalho do cupom.
- `analisar_texto(texto: str, hoje: date \| None=None) -> dict`
- `analisar(dados: bytes, nome_arquivo: str='') -> dict` — Lê a foto ou o PDF do cupom (ou o XML da nota). Gira a foto quando a primeira leitura não acha o valor.

## `app/caixa/servico.py`

> Regras do caixa: lançamentos, períodos (dia, semana, mês e ano) e relatórios.

**Constantes:** `PERIODOS` = `('dia', 'semana', 'mes', 'ano')` · `MESES` = `['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']` · `DIAS` = `['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']` · `SEM_CENTRO` = `'Sem centro de custo'`

- **classe `ErroCaixa`** — Erro de regra (mensagem já pronta para a pessoa ler).
- `moeda(valor) -> str`
- `_normal(texto: str) -> str`
- `_data(valor) -> date \| None`
- `repositorio()`
- `periodo(tipo: str, referencia: date \| None=None) -> tuple[date, date, str]` — Primeiro e último dia do período e o nome dele (ex.: "semana de 21/09 a 27/09/2026").
- `deslocar(tipo: str, referencia: date, passos: int) -> date` — Data de referência do período anterior (passos < 0) ou seguinte (passos > 0).
- `listar(inicio: date \| None=None, fim: date \| None=None, movimento: str='', incluir_cancelados: bool=False) -> list[dict]`
- `_limpar(dados: dict, novo: bool) -> dict`
- `lancar(dados: dict, usuario: str='', arquivo: dict \| None=None) -> dict`
- `atualizar(id_: int, dados: dict, usuario: str='') -> dict`
- `cancelar(id_: int, usuario: str='') -> dict`
- `_soma(lista: list[dict]) -> float`
- `_bloco(lista: list[dict]) -> dict`
- `saldo_ate(dia: date) -> float` — Quanto deveria haver no caixa ao fim do dia (todas as entradas menos todas as saídas até lá).
- `_agrupar(lista: list[dict], chave) -> list[dict]`
- `_serie(lista: list[dict], tipo: str, inicio: date, fim: date) -> list[dict]` — Entradas e saídas por dia (dia, semana e mês) ou por mês (ano), com os períodos vazios também.
- `resumo(tipo: str='mes', referencia: date \| None=None) -> dict` — Tudo o que a tela do caixa mostra para um período: totais, saldo, onde mais se gastou e a evolução.
- `saidas_para_gastos() -> list[dict]` — Saídas do caixa no formato da análise de gastos (dinheiro já gasto: conta como pago na data da saída).

## `app/comprovante.py`

> Comprovantes de pagamento: reconhece o comprovante, lê o que foi pago e descobre de qual boleto ou Pix ele é.
> 
> 1. **É comprovante?** Procura sinais como "comprovante", "valor pago", "data do pagamento", "autenticação",
>    "ID da transação" — e sinais de boleto ("local de pagamento", "nosso número"...) para não confundir.
> 2. **O que foi pago:** valor pago, valor do documento, juros/multa, desconto, data do pagamento, vencimento,
>    beneficiário/recebedor, CPF/CNPJ, chave Pix e a linha digitável (quando o banco imprime).
> 3. **De qual lançamento é:** pontua cada boleto e Pix — linha digitável igual resolve na hora; senão pesa valor,
>    CNPJ, nome, vencimento e a data do pagamento. Só registra sozinho quando a escolha é clara; se houver dúvida
>    (ex.: parcelas iguais), deixa para alguém escolher.
> 
> Juros e desconto: quando o comprovante informa, usa o informado; se o valor pago for diferente do valor do
> boleto, a diferença vira juros/multa (pago a mais) ou desconto (pago a menos).

**Constantes:** `RE_MOEDA_OU_ZERO` = `re.compile('(?<![\\d,])(\\d{1,3}(?:\\.\\d{3})+\|\\d+),(\\d{2})(?!\\d)')` · `SINAIS_COMPROVANTE` = `('comprovante', 'valor pago', 'total pago', 'pagamento efetuado', 'pagamento realizado', 'pagamento concluido', 'transacao efetuada', 'transacao realizada', …` · `SINAIS_BOLETO` = `('local de pagamento', 'pagavel em', 'pagavel preferencialmente', 'ficha de compensacao', 'recibo do pagador', 'recibo do sacado', 'nosso numero', 'uso do ba…` · `PALAVRAS_GENERICAS` = `{'ltda', 'me', 'epp', 'sa', 's/a', 'eireli', 'comercio', 'comercial', 'servicos', 'industria', 'de', 'da', 'do', 'dos', 'das', 'e', 'cia', 'empresa', 'grupo'…` · `ROTULO_VALOR_PAGO` = `'valor (total )?pago\|total pago\|valor do pagamento\|valor debitado\|valor cobrado\|valor total\|valor da transferencia\|valor do pix\|valor da transacao\|valor tran…` · `ROTULO_VALOR_DOCUMENTO` = `'valor (original )?do (documento\|boleto\|titulo)\|valor original\|valor nominal\|valor do titulo'` · `ROTULO_JUROS` = `'juros\|multa\|mora\|encargos\|acrescimo\|\\(\\+\\)'` · `ROTULO_DESCONTO` = `'desconto\|abatimento\|bonificacao\|\\(-\\)'` · `ROTULO_DATA_PAGAMENTO` = `'data d[oea] (pagamento\|debito\|transacao\|operacao\|transferencia\|efetivacao\|pix)\|pago em\|realizad[oa] em\|efetuad[oa] em\|debitado em\|data/hora\|data e hora\|hora…` · `ROTULO_VENCIMENTO` = `'vencimento'` · `ROTULO_NOME` = `'beneficiario( final)?\|favorecido\|recebedor\|destinatario\|nome do recebedor\|cedente\|razao social\|^para\\b\|^destino\\b'` · `ROTULO_CHAVE` = `'chave( pix)?\\b'` · `LIMITE_CONFIANCA` = `75` · `MARGEM_CONFIANCA` = `20` · `RE_SO_ROTULO` = `re.compile('^(nome\|cpf\|cnpj\|cpf/cnpj\|instituicao\|banco\|agencia\|conta\|chave( pix)?\|dados\|tipo\|documento\|beneficiario\|favorecido\|recebedor\|destino\|para)\\W*$')`

- `_linhas(texto: str) -> list[str]`
- `_valor(texto: str) -> float \| None`
- `_poucas_letras(texto: str) -> bool`
- `_apos_rotulo(linhas: list[str], padrao: str, extrair, janela: int=2)` — Valor que vem depois do rótulo: na mesma linha ou nas linhas logo abaixo (leiautes em duas colunas).
- `_nome(texto: str) -> str \| None`
- `eh_comprovante(texto: str) -> bool`
- `extrair(texto: str, codigos: list[str] \| None=None, hoje: date \| None=None) -> dict` — Dados do pagamento a partir do texto do comprovante. Valores em float, datas em ``date``.
- `_palavras(nome: str) -> set[str]`
- `_data(valor) -> date \| None`
- `pontuar(extraido: dict, registro: dict, aba: str) -> tuple[int, list[str]]`
- `candidatos(extraido: dict, boletos: list[dict], pix: list[dict], limite: int=6) -> list[dict]`
- `escolher(lista: list[dict]) -> dict \| None` — O candidato só é aceito sozinho quando se destaca dos demais.
- `dados_de_pagamento(extraido: dict, registro: dict, hoje: date \| None=None) -> dict` — Alterações a gravar no lançamento: pago, data, valor pago, juros/multa e desconto.
- `publico(extraido: dict) -> dict`

## `app/config.py`

> Configurações lidas do ambiente (arquivo .env opcional na raiz do projeto).

**Constantes:** `BASE_DIR` = `Path(__file__).resolve().parent.parent` · `NOME_APP` = `os.getenv('LEITOR_NOME_APP', 'Fin Pro')` · `DEMONSTRACAO` = `_bool('LEITOR_DEMO', False)` · `DADOS_DIR` = `Path(os.getenv('LEITOR_DADOS_DIR') or BASE_DIR / 'dados')` · `PLANILHA_PATH` = `Path(os.getenv('LEITOR_PLANILHA') or DADOS_DIR / 'boletos.xlsx')` · `FECHAMENTOS_PATH` = `Path(os.getenv('LEITOR_FECHAMENTOS') or PLANILHA_PATH.parent / 'fechamentos.xlsx')` · `DIESEL_PATH` = `Path(os.getenv('LEITOR_DIESEL') or PLANILHA_PATH.parent / 'diesel.xlsx')` · `ARQUIVOS_DIR` = `DADOS_DIR / 'arquivos'` · `BACKUPS_DIR` = `DADOS_DIR / 'backups'` · `WEB_DIR` = `BASE_DIR / 'web'` · `HOST` = `os.getenv('LEITOR_HOST', '127.0.0.1')` · `PORT` = `int(os.getenv('LEITOR_PORT', '8000'))` · `MAX_UPLOAD_MB` = `int(os.getenv('LEITOR_MAX_UPLOAD_MB', '100'))` · `MAX_PAGINAS_PDF` = `int(os.getenv('LEITOR_MAX_PAGINAS_PDF', '30'))` · `DIAS_MANTER_ARQUIVOS_NAO_LANCADOS` = `int(os.getenv('LEITOR_DIAS_ARQUIVOS_TEMP', '2'))` · `URL_APP` = `os.getenv('LEITOR_URL') or f'http://{('localhost' if HOST in ('0.0.0.0', '127.0.0.1', '::') else HOST)}:{PORT}'` · `NOTIFICACOES_AUTOMATICAS` = `_bool('LEITOR_NOTIFICACOES_AUTOMATICAS', True)` · `BACKUP_AUTOMATICO` = `_bool('LEITOR_BACKUP_AUTOMATICO', True)` · `SENHA_ACESSO` = `(os.getenv('LEITOR_SENHA_ACESSO') or '').strip()` · `IA_MODELO` = `os.getenv('LEITOR_IA_MODELO', 'claude-opus-5')` · `IA_AUTOMATICA` = `_bool('LEITOR_IA_AUTOMATICA', False)`

- `_bool(nome: str, padrao: bool=False) -> bool`
- `ia_configurada() -> bool`

## `app/contexto.py`

> Objetos compartilhados pela aplicação (planilha, repositórios, serviços), criados uma única vez.
> 
> Os módulos de rotas (``app/rotas``) importam daqui, em vez de cada um criar a sua própria cópia.

- `link_notificacao(rota: str) -> str` — Link aberto ao clicar numa notificação do Windows: no modo aplicativo, traz a janela para a frente.
- `_cheques_a_depositar() -> list[dict]` — Cheques pré-datados entram nos mesmos avisos de vencimento dos boletos e Pix.
- `_resumo_da_semana(tipo: str, hoje)` — Resumo de segunda (o que vence na semana) ou de sexta (o que foi pago), com boletos, Pix, caixa e empresas.

## `app/demonstracao.py`

> Versão de demonstração: uma cópia completa do sistema com dados de exemplo, para mostrar a clientes.
> 
> Roda na pasta ``dados_demo`` (nunca toca nos dados reais) e numa porta própria, então pode ficar aberta ao
> mesmo tempo que o sistema de verdade. Com ``LEITOR_DEMO=1``, nada é enviado para fora: Telegram e e-mail
> ficam visíveis e configurados na tela, mas o envio é bloqueado.
> 
>     python -m app.demonstracao              prepara os dados (se a pasta estiver vazia) e abre
>     python -m app.demonstracao --refazer    apaga tudo e monta os dados de novo
>     python -m app.demonstracao --dados      só prepara os dados, sem abrir
> 
> O atalho para o dia a dia é o ``demonstracao.bat``, na pasta do projeto.

**Constantes:** `PORTA_PADRAO` = `'8010'` · `CENTROS` = `[('Combustível e Veículos', 'Diesel, gasolina, pneus e manutenção da frota'), ('Manutenção', 'Peças, oficina e serviços de manutenção'), ('Materiais', 'Mater…` · `FORNECEDORES` = `[('ENERGISA SUL SUDESTE', '09.095.183/0001-40', 'Energia e Água', 'Banco do Brasil'), ('POSTO SAO JORGE LTDA', '12.345.678/0001-95', 'Combustível e Veículos'…` · `RECEBEDORES_PIX` = `[('Mecânica do Zé', 'cnpj', '12.987.654/0001-70', 'Manutenção', 'Troca de óleo do caminhão'), ('Maria da Limpeza', 'celular', '+5517999887766', 'Escritório',…` · `GASTOS_CAIXA` = `[('Posto São Jorge', 'Combustível e Veículos', 'gasolina da caminhonete', 180.0, 320.0), ('Mercado Bom Preço', 'Escritório', 'café, açúcar e copos', 45.0, 13…` · `EMPRESAS_CLIENTES` = `[('Imapal Construções', '12.345.678/0001-95', 'Imapal, Imapal Construcoes', 'Brita 01', 'M³', 158.8), ('Jose Pazete & Cia', '39.285.595/0001-04', 'Pazete, Jo…` · `PESSOAS` = `['Fábio', 'Almir', 'Marcos', 'Juliana']` · `MAQUINAS_DIESEL` = `[('Escavadeira PC200', 'Máquina', '', 'horas', 'Diesel comum', (150, 210), 9), ('Pá carregadeira 924K', 'Máquina', '', 'horas', 'Diesel comum', (110, 160), 8…` · `COMPRAS_SEMANAIS` = `(('Diesel S10', 550, 7.45), ('Diesel comum', 500, 6.75))`

- `_ambiente() -> Path` — Variáveis de ambiente da demonstração (antes de importar o resto do sistema).
- `_digitos_linha(semente: random.Random) -> str` — Linha digitável de exemplo (só para a demonstração: os dígitos são sorteados).
- `_formatar_linha(digitos: str) -> str`
- `_dinheiro(sorteio: random.Random, minimo: float, maximo: float) -> float`
- `_moeda(valor: float) -> str`
- `_fonte(tamanho: int)`
- `_arquivo_exemplo(titulo: str, linhas: list[tuple[str, str]], nome: str, cor: str='#0d7a64') -> dict` — Imagem de um comprovante de exemplo (só para a demonstração), guardada como os arquivos de verdade.
- `montar_dados(hoje: date \| None=None, semente: int=20260922) -> dict` — Cria boletos, Pix, caixa, empresas, usuários e configurações de exemplo. Devolve o que foi criado.
- `_diesel_de_exemplo(hoje: date, sorteio: random.Random) -> int` — Oito semanas de diesel: 1.000 L comprados toda segunda (S10 e comum) e os canhotos de cada máquina.
- `configurar(hoje: date \| None=None) -> None` — Usuários, lembretes, resumos da semana e bots — tudo ligado, como num cliente de verdade.
- `preparar(pasta: Path, refazer: bool=False) -> dict \| None` — Monta os dados de exemplo se ainda não existirem (ou de novo, com ``refazer``).
- `main() -> None`

## `app/desktop.py`

> Aplicativo de desktop: janela própria (Microsoft Edge WebView2) + ícone na bandeja do Windows.
> 
> * o servidor roda numa thread deste mesmo processo;
> * fechar a janela (X) apenas a esconde — o ícone perto do relógio reabre, e os lembretes de vencimento
>   continuam funcionando (configurável em Configurações → Aplicativo);
> * ``--bandeja`` inicia só com o ícone (usado ao ligar o computador, se preferir).

**Constantes:** `TITULO` = `'Fin Pro'` · `ID_APP` = `'LeitorDeBoletos.Aplicativo'` · `ICONE_ICO` = `config.WEB_DIR / 'icons' / 'app.ico'` · `ICONE_PNG` = `config.WEB_DIR / 'icons' / 'icone-192.png'`

- `disponivel() -> bool`
- `_definir_id_do_app() -> None` — Faz a barra de tarefas mostrar o ícone do Fin Pro (e não o do Python).
- `_impressao_da_interface() -> str` — Identifica a versão das telas (nome, tamanho e data de cada arquivo em web/).
- `limpar_cache_se_atualizado(pasta_webview: Path) -> bool` — O WebView2 guarda HTML/JS/CSS em cache e pode continuar mostrando telas antigas depois de uma atualização.
- **classe `Aplicativo`**
  - `__init__(self, iniciar_na_bandeja: bool=False)`
  - `iniciar_servidor(self) -> None`
  - `parar_servidor(self) -> None`
  - `criar_icone(self) -> bool`
  - `avisar(self, mensagem: str) -> None`
  - `criar_janela(self) -> None`
  - `_ao_fechar(self)`
  - `_esconder(self) -> None`
  - `_hwnd(self) -> int`
  - `mostrar(self, rota: str \| None=None) -> None`
  - `sair(self) -> None`
- `executar(iniciar_na_bandeja: bool=False) -> None`

## `app/diesel/__init__.py`

> Controle de diesel: compras no posto (o estoque de litros), abastecimentos de cada máquina (os canhotos),
> saldo, média de consumo por máquina, relatórios semanal/quinzenal/mensal e o bot do diesel no Telegram.


## `app/diesel/bot.py`

> Bot do diesel (Telegram): comprovantes da compra no posto e canhotos dos abastecimentos.
> 
> Quem pode mandar arquivos são as pessoas e grupos já cadastrados nos outros bots. Quem **decide a máquina** é
> o responsável (ou os responsáveis) escolhido na tela do bot — se ninguém foi escolhido, quem mandou decide.
> 
> * **Canhoto** → o bot lê cada linha (combustível, litros, preço do litro e total) e manda a foto para o
>   responsável. Para **cada linha** ele escolhe a máquina — um mesmo pedido pode ter Diesel comum para a pá e S10 para
>   o caminhão — e informa o horímetro/km, se quiser. Os litros saem do saldo e o bot responde com o saldo e a média
>   de cada máquina. Quem mandou o canhoto é avisado.
> * **Comprovante da compra** → lê valor, litros e combustível (botão rápido de 1.000 L) e soma ao saldo.
> * **Relatórios** semanal (segunda), quinzenal (dias 1 e 16) e mensal (dia 1) chegam sozinhos para o responsável.

**Constantes:** `MASCARA` = `'••••••••'` · `INTERVALO` = `20` · `TAMANHO_MAXIMO` = `20 * 1024 * 1024` · `EXTENSOES` = `('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic')` · `MAX_ITENS` = `400` · `DIAS_MANTER_CONCLUIDOS` = `30` · `ABERTOS` = `('conversa', 'aguardando', 'pendente', 'erro')` · `COMANDOS` = `[('saldo', 'Quanto diesel ainda tem'), ('medias', 'Média de consumo de cada máquina'), ('relatorio', 'Relatório da semana (ou: /relatorio mes, /relatorio mes…` · `PADRAO` = `{'config': {'ativo': False, 'token': '', 'offset': 0, 'ultima_verificacao': None, 'ultimo_erro': None, 'gestores': [], 'alerta_valor': servico.ALERTA_PADRAO,…` · `CAMPOS_DA_LINHA` = `('combustivel', 'litros', 'preco_litro', 'valor', 'maquina', 'medidor')`

- `_agora() -> str`
- `descrever_linha(linha: dict) -> str` — "Diesel S10 · 200 L × R$ 7,450 = R$ 1.490,00" (o que der para mostrar).
- **classe `BotDiesel`**
  - `__init__(self, caminho: Path, salvar_arquivo: Callable[[bytes, str], dict], pessoas: Callable[[], dict], ler: Callable[[bytes, str, str], dict] \| None=None)` — ``pessoas()`` → {chat_id: nome}; ``ler(dados, nome, legenda)`` lê as linhas, a data, o posto e a placa.
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `token(self) -> str`
  - `gestores(self) -> list[str]` — Quem escolhe a máquina dos canhotos (só vale quem ainda está nos outros bots).
  - `config_publica(self) -> dict`
  - `configurar(self, novo: dict) -> dict`
  - `linhas(item: dict) -> list[dict]` — As linhas do canhoto (uma por combustível), com o que já foi respondido. Cria na primeira vez.
  - `_linha_atual(self, item: dict) -> dict`
  - `dados_preenchidos(self, item: dict) -> dict`
  - `_publico(self, item: dict) -> dict`
  - `listar(self, incluir_concluidos: bool=False) -> list[dict]`
  - `contagem(self) -> int`
  - `arquivos_em_uso(self) -> set[str]`
  - `_item(self, id_: str) -> dict \| None`
  - `descartar(self, id_: str) -> bool`
  - `confirmar(self, id_: str, dados: dict, usuario: str) -> dict` — Alguém conferiu na tela e mandou lançar (a compra ou o canhoto, com uma ou mais linhas).
  - `_lancar(self, item: dict, tipo: str, dados: dict, usuario: str) -> dict`
  - `_encerrar_conversas(self, item: dict) -> None`
  - `_limpar_antigos(self) -> None`
  - `_enviar(self, chat_id: str, texto: str, botoes: list[list[dict]] \| None=None) -> None`
  - `_enviar_arquivo(self, chat_id: str, item: dict, legenda: str, botoes: list[list[dict]]) -> None` — Manda a foto do canhoto (ou o PDF) de volta, com a pergunta; sem o arquivo, só a mensagem.
  - `_responder_botao(self, callback_id: str, chat_id: str, message_id, texto: str='') -> None`
  - `_registrar_comandos(self) -> None`
  - `_responsaveis(self, item: dict) -> list[str]`
  - `_conversa(self, chat_id: str, item: dict, etapa: str) -> None`
  - `_perguntar_tipo(self, chat_id: str, item: dict) -> None`
  - `_perguntar_litros(self, chat_id: str, item: dict) -> None`
  - `_botoes_maquinas(self, item: dict) -> list[list[dict]]`
  - `_maquina_lida(item: dict) -> str` — Máquina reconhecida pela placa do canhoto ou pelo nome escrito na mensagem.
  - `_pergunta_da_linha(self, item: dict) -> str`
  - `_mandar_para_responsavel(self, item: dict) -> None` — O canhoto vai para o responsável escolher a máquina de cada linha (e quem mandou fica sabendo).
  - `_proxima_linha(self, chat_id: str, item: dict) -> None` — Depois de uma linha resolvida: pergunta a próxima ou lança o canhoto.
  - `_concluir_canhoto(self, chat_id: str, item: dict, usuario: str) -> None`
  - `_alerta_saldo(self, atual: dict) -> str`
  - `_alerta_configurado(self) -> float` — Limite do aviso em R$. Configurações antigas tinham o limite em litros: valem o padrão em reais.
  - `nivel_relatorio(self) -> str`
  - `alerta_valor(self) -> float`
  - `_concluir_compra(self, chat_id: str, item: dict, usuario: str) -> None`
  - `_seguir(self, chat_id: str, item: dict) -> None` — Próximo passo depois de saber o tipo e os litros.
  - `_tem_litros(self, item: dict) -> bool`
  - `_nova_foto(self, chat_id: str, remetente: str, dados: bytes, nome_arquivo: str, legenda: str='', file_id: str='', foto: bool=False) -> None`
  - `_texto(self, chat_id: str, texto: str) -> None`
  - `_escolheu_maquina(self, chat_id: str, item: dict, nome: str) -> None`
  - `_botao(self, chat_id: str, dado: str, callback_id: str, message_id) -> None`
  - `_comando(self, chat_id: str, texto: str, nome: str) -> None`
  - `_arquivo(mensagem: dict) -> tuple[str, str, int, bool] \| None`
  - `verificar(self) -> dict`
  - `_tratar(self, atualizacao: dict, autorizados: dict) -> int`
  - `relatorios_devidos(self, agora: datetime \| None=None) -> list[tuple[str, date]]` — Relatórios que já deviam ter saído hoje: (tipo, data de referência do período fechado).
  - `enviar_relatorios(self, agora: datetime \| None=None) -> list[str]`
  - `verificar_agora(self) -> dict`
  - `iniciar_agendador(self, espera_inicial: float=30) -> None`
  - `parar(self) -> None`

## `app/diesel/leitura.py`

> Leitura dos arquivos do diesel: o **comprovante de pagamento** da compra no posto ou o **canhoto** de um
> abastecimento (também o "pedido" / documento não fiscal que o posto entrega).
> 
> Um canhoto pode ter **várias linhas** — ex.: 200 L de Diesel comum e 200 L de Diesel S10 no mesmo pedido, para
> máquinas diferentes. Cada linha sai com o **combustível**, os litros, o preço por litro e o total.
> 
> Foto de canhoto sai com o OCR torto ("200006" no lugar de "200,000", "7.450" parecendo milhar). Por isso cada linha
> é conferida pela conta **litros × preço = total**, e o que não bate é acertado pelos **totais do rodapé**
> ("Quantidade de itens" e "Valor total"). Tudo passa por conferência antes de lançar.

**Constantes:** `LIMITE_CANHOTO` = `600.0` · `SINAIS_COMPRA` = `('comprovante de pagamento', 'comprovante de transferencia', 'pix', 'transferencia', 'ted', 'boleto', 'pagamento efetuado', 'pagamento realizado', 'valor pag…` · `SINAIS_CANHOTO` = `('canhoto', 'abastecimento', 'requisicao', 'frentista', 'bomba', 'bico', 'placa', 'motorista', 'hodometro', 'horimetro', 'odometro', 'km', 'frota', 'veiculo'…` · `PARADAS` = `('totais', 'quantidade de itens', 'quantidade de rtens', 'qusntidade', 'valor total bruto', 'valor total liquido', 'valor desconto', 'credito troca', 'subtot…` · `RE_LITROS` = `[re.compile('(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{1,3})?\|\\d+(?:[.,]\\d{1,3})?)\\s*(?:l\\b\|lt\\b\|lts\\b\|litros?\\b)', re.I), re.compile('(?:litros?\|lts?\|qtd\|quanti…` · `RE_PRECO` = `re.compile('(?:pre[cç]o\|valor\|vl\\.?\|r\\$)\\s*(?:unit[aá]rio\|unit\\.?\|/\\s*l(?:itro)?\|por litro\|litro)\\s*[:=]?\\s*(?:r\\$)?\\s*(\\d{1,2}[.,]\\d{2,3})', re.I)` · `RE_PLACA` = `re.compile('\\b([A-Z]{3})[\\s-]?(\\d[A-Z0-9]\\d{2})\\b')` · `RE_MEDIDOR` = `re.compile('(?:km\|hod[oô]metro\|od[oô]metro\|hor[ií]metro\|hr\|horas?)\\s*[:=.\\-]?\\s*(\\d{1,3}(?:\\.\\d{3})+(?:,\\d)?\|\\d+(?:[.,]\\d)?)', re.I)` · `RE_TOKEN` = `re.compile('(?<![\\w.,])\\d[\\d.,]*\\d(?![\\w])\|(?<![\\w.,])\\d(?![\\w.,])')` · `RE_PEDIDO` = `re.compile('(?:pedido\|requisi[cç][aã]o\|canhoto\|cupom\|documento)\\s*n?\\S{0,2}\\s*[:.]?\\s*(\\d{4,12})', re.I)` · `RUIDO_DO_BANCO` = `('telefone', 'ouvidoria', 'sac ', 'sac-', 'site', 'atendimento', 'fale conosco', '0800', 'deficiente', 'reclamac', 'cancelamento', 'servico de', 'apoio ao cl…` · `RE_FAVORECIDO` = `re.compile('^\\s*(?:nome\|favorecido\|recebedor\|benefici[aá]rio\|destinat[aá]rio\|para\|pago a)\\s*[:\\-]\\s*(.{3,})$', re.I)`

- `_numero(texto: str) -> float \| None`
- `_leituras(token: str) -> list[float]` — Os jeitos possíveis de ler um número do OCR: "7.450" = 7450 ou 7,45; "200006" = 200006 ou 200,006; "2.840.000" = 2840000 ou 2.840,000.
- `_tokens(texto: str) -> list[str]` — Números do texto, sem os códigos de produto ("000005"), que não são litros, preço nem total.
- `combustivel_do_texto(texto: str) -> str` — Qual combustível: "DIESEL S10", "DIESELS10", "S-10", "DIESEL COMUM", "S500", "GASOLINA", "ARLA"… Diesel sem dizer qual devolve "" (quem confere escolhe, ou vale o da máquina).
- `eh_linha_de_produto(linha: str) -> bool`
- `_melhor_trio(tokens: list[str]) -> dict \| None` — Acha litros, preço e total entre os números de uma linha: o preço fica na faixa do litro e a conta tem que bater.
- `_total_do_rodape(linhas: list[str], rotulos: tuple[str, ...], alvo: float \| None) -> float \| None` — Valor do rodapé ("Quantidade de itens 400.000", "Valor Total Líquido 2.840.000") — o jeito de ler que chega mais perto da soma das linhas.
- `itens_do_canhoto(texto: str) -> list[dict]` — Cada combustível do canhoto: {"combustivel", "descricao", "litros", "preco_litro", "valor", "conferido"}.
- `litros_do_texto(texto: str) -> float \| None`
- `classificar(texto: str, legenda: str='', litros: float \| None=None) -> str` — ``compra``, ``canhoto`` ou "" (não deu para saber: o bot pergunta).
- `_nossa_empresa() -> str`
- `_posto(texto: str, tipo: str) -> str` — Nome do posto: a linha com "posto"; no comprovante, quem recebeu o pagamento; senão, o nome do cupom.
- `analisar_texto(texto: str, legenda: str='', hoje: date \| None=None) -> dict`
- `analisar(dados: bytes, nome_arquivo: str='', legenda: str='') -> dict` — Lê a foto ou o PDF. Gira a foto quando a primeira leitura não acha nem litros nem valor.

## `app/diesel/modelos.py`

> Abas do banco de dados do diesel (máquinas, compras e abastecimentos).
> 
> Mesma estrutura das outras partes do sistema: banco SQLite, planilha Excel gerada sozinha (``dados/diesel.xlsx``),
> histórico de quem fez cada alteração e backup diário.

**Constantes:** `COR_MAQUINAS` = `'3F4A56'` · `COR_COMPRAS` = `'0E6B5C'` · `COR_ABASTECIMENTOS` = `'B45309'` · `TIPOS_MAQUINA` = `('Caminhão', 'Máquina', 'Veículo', 'Gerador', 'Outro')` · `MEDIDORES` = `('horas', 'km', '')` · `STATUS_MAQUINA` = `('Ativa', 'Inativa')` · `STATUS_COMPRA` = `('Confirmada', 'Cancelada')` · `STATUS_ABASTECIMENTO` = `('Confirmado', 'Cancelado')` · `LITROS_POR_COMPRA` = `1000.0` · `COMBUSTIVEIS` = `('Diesel S10', 'Diesel comum', 'Gasolina', 'Etanol', 'Arla 32')` · `COMBUSTIVEL_PADRAO` = `'Diesel S10'` · `LITROS` = `'#,##0.00 "L"'` · `MOEDA` = `'"R$" #,##0.00'` · `COLUNAS_MAQUINAS` = `[Coluna('id', 'ID', 7, '0'), Coluna('nome', 'Máquina', 30), Coluna('tipo', 'Tipo', 12), Coluna('placa', 'Placa / Prefixo', 16, '@'), Coluna('medidor', 'Medid…` · `COLUNAS_COMPRAS` = `[Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('posto', 'Posto', 30), Coluna('combustivel', 'Combustível', 14), Coluna('litros…` · `COLUNAS_ABASTECIMENTOS` = `[Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 8, '@'), Coluna('maquina', 'Máquina', 28), Coluna('combustivel'…` · `_TEXTOS_COMUNS` = `frozenset({'observacoes', 'arquivo', 'arquivo_nome', 'lancado_por'})` · `ABAS_DIESEL` = `{'maquinas': DefinicaoAba('maquinas', 'Máquinas', tuple(COLUNAS_MAQUINAS), frozenset({'nome', 'tipo', 'placa', 'medidor', 'combustivel', 'status', 'observaco…`


## `app/diesel/precos.py`

> Preço que a empresa paga no litro de cada combustível (tabela de referência).
> 
> Vale para o canhoto que não traz o preço: o abastecimento sai com o valor = litros × preço daqui. Quando o canhoto
> ou a compra trazem o preço, vale o que veio neles. Fica em ``dados/diesel_precos.json``.

- `_caminho()`
- `ler() -> dict[str, dict]` — {combustível: {"preco": 6.75, "atualizado_em": "...", "por": "Fábio"}}
- `preco(combustivel: str) -> float`
- `salvar(novos: dict[str, float], usuario: str='') -> dict[str, dict]`
- `publico() -> list[dict]`

## `app/diesel/relatorio.py`

> Relatório do diesel em três níveis — **simples**, **detalhado** e **completo** — na tela, no Telegram e no Excel.
> 
> * **simples**: quanto foi abastecido (R$ e litros), o saldo no posto e quanto tempo ele dura, e quanto cada máquina gastou;
> * **detalhado**: + comparação com o período anterior, pontos de atenção, consumo (L/h, km/L), combustíveis e compras;
> * **completo**: + cada abastecimento com o consumo do trecho (desde o abastecimento anterior), por dia, por posto e
>   por pessoa.
> 
> A base é ``servico.resumo``; aqui entram as contas que só o relatório usa.

**Constantes:** `NIVEIS` = `('simples', 'detalhado', 'completo')` · `NIVEL_PADRAO` = `'simples'` · `ACIMA_DO_NORMAL` = `{'semana': 1.5, 'quinzena': 1.4, 'mes': 1.3, 'ano': 1.3}` · `HISTORICO_MINIMO` = `14` · `LITROS_MINIMOS_ALERTA` = `50.0` · `DIAS_RITMO` = `30` · `LIMITE_TELEGRAM` = `3900` · `DIAS_SEMANA` = `('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')` · `MESES_CURTOS` = `('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez')` · `TITULOS` = `{'semana': 'semanal', 'quinzena': 'quinzenal', 'mes': 'mensal', 'ano': 'anual'}` · `ANTERIOR` = `{'semana': 'à semana anterior', 'quinzena': 'à quinzena anterior', 'mes': 'ao mês anterior', 'ano': 'ao ano anterior'}`

- `nivel_valido(nivel: str \| None) -> str`
- `_num(valor) -> float`
- `variacao(atual: float, antes: float) -> float \| None` — Variação em %; ``None`` quando não há com o que comparar.
- `texto_variacao(pct: float \| None) -> str`
- `_serie(tipo: str, inicio: date, fim: date, lista: list[dict]) -> list[dict]` — Por dia (semana, quinzena, mês) ou por mês (ano): litros e R$ de cada combustível.
- `_agrupar(lista: list[dict], chave, fim: date) -> list[dict]`
- `_trechos(lista: list[dict], fim: date, cadastro: dict[str, dict]) -> dict[int, dict]` — Consumo de cada abastecimento com horímetro/km: o que rodou desde o abastecimento anterior da mesma máquina.
- `_media_anterior(nome: str, inicio: date, dias: int=90) -> float` — Litros por dia da máquina nos ``dias`` antes do período (a referência do "normal").
- `_previsao(fim: date, hoje: date) -> dict \| None` — Quanto o saldo de hoje dura no ritmo dos últimos 30 dias (só quando o período inclui hoje).
- `_alertas(r: dict, cadastro: dict[str, dict], alerta_valor: float \| None, hoje: date) -> list[dict]` — Pontos de atenção do período, do mais grave para o menos grave.
- `analise(tipo: str='semana', referencia: date \| None=None, alerta_valor: float \| None=None, hoje: date \| None=None) -> dict` — O resumo do período com tudo o que o relatório detalhado e o completo mostram.
- `_limitar(texto: str, limite: int=LIMITE_TELEGRAM) -> str` — Corta numa quebra de linha para caber numa mensagem do Telegram.
- `_linha_saldo(r: dict) -> list[str]`
- `_texto_simples(r: dict) -> str`
- `_comando(tipo: str) -> str`
- `_texto_detalhado(r: dict, referencia: date \| None) -> str`
- `_texto_completo(r: dict, referencia: date \| None) -> str`
- `texto(tipo: str='semana', referencia: date \| None=None, nivel: str=NIVEL_PADRAO, alerta_valor: float \| None=None, hoje: date \| None=None) -> str`

## `app/diesel/servico.py`

> Diesel: o estoque de litros (compras no posto) e o que cada máquina abasteceu (canhotos).
> 
> * **Saldo** = litros comprados − litros abastecidos (só o que não foi cancelado).
> * **Média de cada máquina** no período: litros, abastecimentos, litros por dia e, quando os canhotos trazem o
>   horímetro ou o km, o consumo de verdade: **litros por hora** (máquinas) ou **km por litro** (caminhões).
> * **Relatórios** por semana, quinzena (1–15 e 16–fim do mês), mês ou ano.
> * **Combustível** em cada compra, abastecimento e máquina (Diesel S10, Diesel comum, Gasolina…). O saldo é um só —
>   os litros comprados na semana servem para qualquer combustível que o posto entregar —, e por combustível sai o quanto
>   foi abastecido de cada um. O custo de cada abastecimento é o preço do canhoto; sem ele, o da tabela de preços.

**Constantes:** `MESES` = `('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')` · `PERIODOS` = `('semana', 'quinzena', 'mes', 'ano')` · `SEM_MAQUINA` = `'Sem máquina'` · `ALERTA_PADRAO` = `1000.0` · `EDITAVEIS` = `{'compras': ('data', 'posto', 'combustivel', 'litros', 'valor', 'preco_litro', 'forma', 'documento', 'observacoes'), 'abastecimentos': ('data', 'hora', 'maqu…`

- **classe `ErroDiesel`** — Erro de regra (mensagem já pronta para a pessoa ler).
- `banco()`
- `normalizar(texto) -> str`
- `_data(valor) -> date \| None`
- `_num(valor) -> float`
- `numero_br(valor) -> str`
- `litros_br(valor) -> str`
- `moeda(valor) -> str`
- `combustivel_de(registro: dict) -> str` — Combustível do lançamento (os antigos, sem combustível, contam como o padrão).
- `_combustivel(valor, maquina: dict \| None=None) -> str`
- `numero_digitado(texto: str) -> float \| None` — Número digitado no Telegram ou na tela: "1.000", "180,5", "180.5", "1000 L".
- `periodo(tipo: str, referencia: date \| None=None) -> tuple[date, date, str]` — Primeiro e último dia do período e o nome dele. Quinzena: 1 a 15 e 16 ao fim do mês.
- `deslocar(tipo: str, referencia: date, passos: int) -> date` — Data de referência do período anterior (passos < 0) ou seguinte (passos > 0).
- `maquinas(incluir_inativas: bool=True) -> list[dict]`
- `maquina_por_nome(nome: str) -> dict \| None`
- `salvar_maquina(dados: dict, usuario: str='', id_: int \| None=None) -> dict`
- `garantir_maquina(nome: str, usuario: str='') -> dict`
- `_listar(aba: str, inicio: date \| None=None, fim: date \| None=None, cancelados: bool=False) -> list[dict]`
- `compras(inicio: date \| None=None, fim: date \| None=None, cancelados: bool=False, combustivel: str='') -> list[dict]`
- `abastecimentos(inicio: date \| None=None, fim: date \| None=None, cancelados: bool=False, maquina: str='', combustivel: str='') -> list[dict]`
- `_arquivo(arquivo: dict \| None) -> dict`
- `lancar_compra(dados: dict, usuario: str='', arquivo: dict \| None=None) -> dict` — Compra no posto: soma os litros ao estoque. Sem os litros, vale a compra semanal padrão de 1.000 L.
- `lancar_abastecimento(dados: dict, usuario: str='', arquivo: dict \| None=None) -> dict` — Canhoto de uma máquina: tira os litros do estoque e entra na média dela.
- `lancar_canhoto(itens: list[dict], comum: dict, usuario: str='', arquivo: dict \| None=None) -> list[dict]` — Um canhoto com uma ou mais linhas (ex.: Diesel comum para a pá e S10 para o caminhão): um abastecimento por linha.
- `atualizar(aba: str, id_: int, dados: dict, usuario: str='') -> dict`
- `cancelar(aba: str, id_: int, usuario: str='') -> dict`
- `_preco_referencia(combustivel: str, ate: date \| None=None) -> float` — Preço do litro para pôr valor num lançamento sem valor: o da tabela de preços; sem ele, o médio das compras.
- `valor_da_compra(compra: dict, ate: date \| None=None) -> float` — O que foi pago na compra: o valor do comprovante ou, sem ele, litros × preço.
- `valor_do_abastecimento(abastecimento: dict, ate: date \| None=None) -> float` — Quanto o abastecimento tirou do saldo: o valor do canhoto ou, sem ele, litros × preço daquele combustível.
- `saldo(ate: date \| None=None) -> dict` — Saldo em reais: o que foi pago nas compras − o valor de cada abastecimento (até a data, se informada).
- `preco_medio(inicio: date \| None=None, fim: date \| None=None, combustivel: str='') -> float` — Preço médio do litro nas compras do período (sem compra no período, o da última compra; sem compra nenhuma, o da tabela de preços).
- `custo(abastecimento: dict, precos_medios: dict[str, float]) -> float` — Quanto custou o abastecimento: o valor do canhoto ou, sem ele, litros × preço daquele combustível (o da tabela de preços; sem ele, o médio das compras).
- `consumo(maquina: dict \| None, lista: list[dict]) -> dict` — Consumo pelas leituras do horímetro/km: litros usados entre a primeira e a última leitura.
- `media_da_maquina(nome: str, fim: date \| None=None, dias: int=30) -> dict` — Média dos últimos ``dias`` (padrão 30): litros por dia, por semana e o consumo pelo horímetro/km.
- `resumo(tipo: str='semana', referencia: date \| None=None) -> dict` — Tudo de um período: compras, abastecimentos, saldo e a tabela por máquina (o relatório).
- `texto_equivalente(atual: dict) -> str` — Ex.: "≈ 520 L de Diesel S10 ou 574 L de Diesel comum".
- `texto_saldo(atual: dict \| None=None) -> str`
- `texto_media(nome: str) -> str`
- `texto_relatorio(tipo: str='semana', referencia: date \| None=None) -> str`

## `app/empresas/__init__.py`

> Módulo Empresas: controle do que os clientes têm a pagar (vendas a prazo) e o fechamento de cada um.
> 
> Enquanto o restante do sistema cuida do que a empresa **paga** (boletos e Pix), este módulo cuida do que ela
> **recebe**:
> 
> * **Notas fiscais** — cada item vendido a prazo vira uma linha do fechamento da empresa (data, material,
>   unidade, quantidade, valor unitário, valor total, número da NF e número do pedido);
> * **Cheques pré-datados** — guardados com banco, agência, cooperativa, número, valor e a data do depósito,
>   com aviso de vencimento no mesmo modelo dos boletos;
> * **Recebimentos** — Pix, TED, depósitos e cheques compensados, que dão **baixa automática** nas notas
>   fiscais citadas no comprovante;
> * **Fechamento** — todo dia 20 (ou no dia configurado) o sistema fecha o período de cada empresa e gera o
>   relatório no formato usado hoje, mostrando o total, o que já foi recebido e quanto falta.
> 
> Tudo chega pelo **bot de notas fiscais** do Telegram (um bot só para isso), que reconhece sozinho se o
> arquivo é uma nota fiscal, um cheque ou um comprovante.


## `app/empresas/bot.py`

> Comandos do bot de notas fiscais: consultar fechamentos, saldos e cheques pelo celular.
> 
> /fechamento — fechamento da empresa (total, recebido e quanto falta)
> /empresas   — todas as empresas com o que falta receber
> /cheques    — cheques pré-datados a depositar
> /notas      — notas em aberto de uma empresa
> /ajuda      — lista dos comandos

**Constantes:** `COMANDOS` = `[('fechamento', 'Fechamento da empresa (ex.: /fechamento imapal)'), ('empresas', 'Todas as empresas e quanto falta receber'), ('cheques', 'Cheques pré-datado…` · `LIMITE_MENSAGEM` = `3800`

- `_moeda(valor) -> str`
- `_empresa_do_texto(argumento: str) -> dict \| None`
- `ajuda(nome: str='') -> str`
- `_partir(linhas: list[str]) -> list[str]`
- `_linha_empresa(e: dict) -> str`
- `responder(texto: str, nome: str='', hoje: date \| None=None) -> list[str] \| None` — Resposta (HTML do Telegram) a uma mensagem de texto. None quando não é um comando.

## `app/empresas/configuracao.py`

> Configuração do módulo Empresas: dados da minha empresa, dia do fechamento e o bot de notas fiscais.

**Constantes:** `MASCARA` = `'••••••••'` · `PADRAO` = `{'minha_empresa': {'nome': '', 'cnpj': ''}, 'dia_fechamento': DIA_FECHAMENTO_PADRAO, 'fechamento_automatico': True, 'hora_envio': '08:00', 'ultimo_fechamento…`

- `_hora(texto: str) -> time`
- `normalizar_destinatarios(lista) -> list[dict]` — Pessoas e grupos que falam com o bot de notas: ``[{"chat_id": "123", "nome": "Almir", "empresa": ""}]``.
- **classe `ConfigEmpresas`** — Arquivo ``dados/empresas.json``: quem sou eu, quando fecho o mês e o bot que recebe as notas.
  - `__init__(self, caminho: Path)`
  - `_ler(self) -> dict`
  - `gravar(self) -> None`
  - `minha_empresa(self) -> dict`
  - `dia_fechamento(self) -> int`
  - `hora_envio(self) -> time`
  - `bot(self) -> dict`
  - `token(self) -> str`
  - `destinatarios(self) -> list[dict]`
  - `publica(self) -> dict`
  - `atualizar(self, novo: dict) -> dict`
  - `registrar_envio(self, competencia: str) -> None`
  - `registrar_bot(self, **campos) -> None`
  - `lembrar_chat(self, chat: dict) -> None`

## `app/empresas/entrada.py`

> Bot de notas fiscais: recebe pelo Telegram as notas, os cheques e os comprovantes dos clientes.
> 
> É um bot **separado** do bot dos boletos (outro token, criado no @BotFather só para isto). Ao receber um
> arquivo, o sistema descobre se é nota fiscal, cheque ou comprovante:
> 
> * **nota fiscal** — lança as linhas no fechamento da empresa e responde com o total do fechamento;
> * **cheque** — guarda banco, agência, cooperativa, número, valor e a data do depósito, e passa a avisar do
>   vencimento; as notas dos pedidos citados ficam "em cheque";
> * **comprovante** de Pix, TED ou depósito — dá baixa nas notas fiscais citadas e responde quanto falta.
> 
> O que não dá para reconhecer com segurança fica na tela **Empresas → Conferência**, para alguém confirmar.
> Todo dia 20 (ou no dia escolhido) o bot envia o fechamento de cada empresa.

**Constantes:** `INTERVALO` = `45` · `TAMANHO_MAXIMO` = `20 * 1024 * 1024` · `EXTENSOES` = `('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.xml')` · `MAX_ITENS` = `300` · `DIAS_MANTER_CONCLUIDOS` = `30`

- `_agora() -> str`
- `numeros_citados(dados: dict) -> list[str]` — Números de NF e de pedido lidos no comprovante (ajudam a achar o cheque certo).
- **classe `CaixaNotas`**
  - `__init__(self, caminho: Path, config, salvar_arquivo: Callable[[bytes, str], dict], comandos=None)` — ``salvar_arquivo(dados, nome)`` guarda o arquivo e devolve ``{"id", "nome", "caminho"}``.
  - `_ler(self) -> list[dict]`
  - `_gravar(self) -> None`
  - `_limpar_antigos(self) -> None`
  - `_publico(item: dict) -> dict`
  - `listar(self, incluir_concluidos: bool=False) -> list[dict]`
  - `obter(self, id_: str) -> dict \| None`
  - `contagem(self) -> int`
  - `arquivos_em_uso(self) -> set[str]`
  - `descartar(self, id_: str) -> bool`
  - `receber(self, dados: bytes, nome: str, origem: str='telegram', remetente: str='', legenda: str='', usuario: str='') -> dict \| None` — Lê o arquivo, decide o que fazer e devolve o item (None se o arquivo já tinha chegado antes).
  - `_tratar(self, item: dict, analise: dict, usuario: str) -> None`
  - `_tratar_nota(self, item: dict, dados: dict, usuario: str) -> None`
  - `_tratar_cheque(self, item: dict, dados: dict, usuario: str) -> None`
  - `_empresa_do_cheque(dados: dict, legenda: str) -> dict \| None` — De quem é o cheque: pelo CNPJ impresso, pelo nome de quem assinou ou pelo que veio na legenda.
  - `_tratar_deposito_de_cheque(self, item: dict, dados: dict, usuario: str) -> None` — Comprovante do banco de um depósito de cheque: acha o cheque pela CMC-7, compensa e baixa as notas.
  - `_tratar_comprovante(self, item: dict, dados: dict, usuario: str) -> None`
  - `confirmar(self, id_: str, tipo: str, dados: dict, usuario: str) -> dict` — Alguém conferiu na tela o que o robô leu e mandou lançar.
  - `_responder(self, token: str, chat_id: str, texto: str) -> None`
  - `_registrar_comandos(self, token: str) -> None`
  - `_arquivo_da_mensagem(mensagem: dict) -> tuple[str, str, int] \| None`
  - `mensagem_resposta(self, item: dict \| None) -> str`
  - `verificar(self) -> dict` — Lê as mensagens novas do bot de notas (arquivos e comandos).
  - `_responder_comando(self, token: str, chat_id: str, mensagem: dict, cadastrados: dict) -> None`
  - `enviar_fechamentos(self, hoje: date \| None=None, forcar: bool=False) -> dict` — No dia do fechamento, manda o resumo de cada empresa para quem está cadastrado no bot.
  - `verificar_agora(self) -> dict`
  - `iniciar_agendador(self, espera_inicial: float=35) -> None`
  - `parar(self) -> None`

## `app/empresas/leitura.py`

> Leitura dos arquivos que chegam pelo bot de notas: nota fiscal, cheque, comprovante e print do fechamento.
> 
> O sistema descobre sozinho **o que é** cada arquivo e tira dele o que interessa:
> 
> * **Nota fiscal** — o XML da NF-e é lido campo a campo (jeito mais confiável); o DANFE em PDF ou foto é lido
>   pelo texto, item por item (material, unidade, quantidade, valor unitário e total), junto com o número da
>   nota, a data, o destinatário e o número do pedido;
> * **Cheque** — a linha CMC7 (os números impressos no rodapé) dá banco, agência, conta e número do cheque;
>   cooperativa, valor, data e pedidos vêm dos rótulos e da legenda enviada junto no Telegram;
> * **Comprovante** de Pix, TED ou depósito — valor, data, hora, pagador, identificador da transação e os
>   números das notas fiscais citadas;
> * **Print do fechamento** — a tabela do fechamento usado hoje, linha por linha (usado para começar a operar
>   com o que já está em andamento).

**Constantes:** `MAX_PAGINAS` = `5` · `UNIDADES` = `('M3', 'M³', 'MC', 'TON', 'TN', 'KG', 'UN', 'UND', 'PC', 'PÇ', 'SC', 'LT', 'L', 'MT', 'M', 'CX', 'H', 'HR')` · `RE_UNIDADE` = `re.compile('\\b(M\\s?3\|M³\|MC\|TON\|TN\|KG\|UND?\|PC\|PÇ\|SC\|LT\|MT\|CX\|HR?\|L\|M)\\b', re.I)` · `RE_NUMERO` = `re.compile('(?<![\\d,.])(\\d{1,3}(?:\\.\\d{3})*(?:,\\d+)?\|\\d+(?:[.,]\\d+)?)(?![\\d])')` · `RE_NF` = `re.compile('\\b(?:nfe?\|nf-?e\|nota\\s*fiscal\|nota\|cupom)\\s*(?:n[ºo°.]?\\s*)?[:\\-]?\\s*(\\d{1,9})', re.I)` · `RE_PEDIDO` = `re.compile('\\b(?:pedido\|ped\\.?\|pdd\|oc)\\s*(?:n[ºo°.]?\\s*)?[:\\-]?\\s*(\\d{1,9})', re.I)` · `RE_CMC7` = `re.compile('(?<!\\d)(\\d{8})\\D{0,4}(\\d{10})\\D{0,4}(\\d{12})(?!\\d)')` · `RE_CMC7_CORRIDO` = `re.compile('(?<!\\d)(\\d{30})(?!\\d)')` · `RE_DEPOSITO_DE_CHEQUE` = `re.compile('deposito[^.\\n]{0,40}cheque\|cheques?\\s+depositad\|comprovante de deposito\|valor do deposito\|deposito (em\|com) cheque')` · `BANCOS` = `{'001': 'Banco do Brasil', '003': 'Banco da Amazônia', '004': 'Banco do Nordeste', '021': 'Banestes', '033': 'Santander', '037': 'Banpará', '041': 'Banrisul'…` · `SINAIS_NOTA` = `('danfe', 'documento auxiliar da nota fiscal', 'nota fiscal eletronica', 'chave de acesso', 'natureza da operacao', 'dados do produto', 'destinatario/remeten…` · `SINAIS_CHEQUE` = `('compensavel', 'compense', 'cheque', 'pague por este cheque', 'quantia de', 'ordem de', 'banco cooperativo', 'acima ou a sua ordem', 'c1', 'bom para')` · `SINAIS_COMPROVANTE` = `('comprovante', 'transferencia', 'pix', 'ted', 'doc', 'deposito', 'valor pago', 'id da transacao', 'autenticacao', 'e2e', 'recibo')` · `SINAIS_FECHAMENTO` = `('fechamento', 'valor uni', 'valor total', 'n pedido', 'nota fical', 'nota fiscal', 'material')` · `RE_SO_ROTULO` = `re.compile('^(nome\|razao social\|nome/razao social\|cnpj\|cpf\|cnpj/cpf\|endereco\|municipio\|uf\|fone\|fax\|bairro\|distrito\|cep\|inscricao estadual\|data da emissao\|dat…` · `RE_MOEDA_TOLERANTE` = `re.compile('(?<![\\d,.])(\\d{1,3}(?:[.\\s]\\d{3})*\|\\d+)[.,](\\d{2})(?![\\d])')` · `CONFUSOES_OCR` = `str.maketrans({'o': '0', 'O': '0', 'l': '1', 'I': '1', 'S': '5', 's': '5', 'B': '8', 'Z': '2'})` · `DISTANCIA_ENTRE_PEDIDOS` = `200` · `RE_CNPJ_SOLTO` = `re.compile('(?<!\\d)\\d{2}[.\\s]?\\d{3}[.\\s]?\\d{3}[/\\s]?\\d{4}[-–\\s]?\\d{2}(?!\\d)')` · `RE_RAZAO_SOCIAL` = `re.compile('([A-ZÀ-Ý][A-Za-zÀ-ý&.\\-]{1,20}(?:\\s+[A-Za-zÀ-ý&.\\-]{1,20}){0,5}\\s+(?:LTDA\|EIRELI\|EPP\|S/?A\|ME)\\b)', re.I)` · `PALAVRAS_DE_BANCO` = `('banco', 'sicredi', 'sicoob', 'coop', 'credito', 'cred ', 'caixa', 'bradesco', 'itau', 'santander', 'cliente bancario')` · `RE_LINHA_FECHAMENTO` = `re.compile('^(?P<data>\\d{1,2}\\s?/\\s?\\d{1,2}\\s?/\\s?\\d{2,4})\\s+(?P<material>.+?)\\s+(?P<unidade>M\\s?[3³]\|MC\|TON\|TN\|KG\|UND?\|PC\|SC\|LT\|CX)\\s+(?P<quantid…`

- `texto_do_arquivo(dados: bytes, max_paginas: int=MAX_PAGINAS, girando: bool=False) -> str` — Texto de um PDF (camada de texto) ou de uma imagem/scan (OCR).
- `_ocr_em_todas_as_orientacoes(imagem, indice: int) -> str` — Lê a imagem de pé, deitada para os dois lados e de cabeça para baixo, e junta as linhas (sem repetir).
- `eh_xml(dados: bytes) -> bool`
- `_pontos(normal: str, sinais) -> int`
- `eh_deposito_de_cheque(normal: str) -> bool` — ``normal``: texto já normalizado (sem acento, minúsculo).
- `classificar(texto: str, nome_arquivo: str='', legenda: str='') -> str` — O que é o arquivo: ``nota``, ``cheque``, ``comprovante``, ``fechamento`` ou "" (não reconhecido).
- `_numero(texto: str) -> float \| None`
- `_sequencia(padrao: re.Pattern, texto: str) -> list[str]` — Números que vêm depois do rótulo, inclusive os da mesma lista ("NF 6859, 6869 e 6870").
- `numeros_de_nf(texto: str) -> list[str]` — Números de nota fiscal citados no texto (ex.: "NF 6859 e 6869", "notas 6859/6869").
- `numeros_de_pedido(texto: str) -> list[str]`
- `_sem_ns(tag: str) -> str`
- `_achar(no, caminho: str)` — Busca por nomes de tag, ignorando o namespace da NF-e.
- `_texto(no, caminho: str, padrao: str='') -> str`
- `ler_xml_nota(dados: bytes) -> dict \| None` — Lê o XML de uma NF-e: emitente, destinatário, itens e pedidos.
- `_linhas(texto: str) -> list[str]`
- `_rotulo(linhas: list[str], padrao: str, janela: int=2) -> str` — Conteúdo que vem depois de um rótulo (na mesma linha ou logo abaixo, como no DANFE).
- `_itens_do_texto(texto: str) -> list[dict]` — Itens do DANFE: depois da unidade vêm quantidade, valor unitário e valor total.
- `_bloco_do_destinatario(linhas: list[str]) -> list[str]`
- `_nome_de_empresa(linha: str) -> str` — Nome de empresa numa linha do DANFE (sem o CNPJ colado e sem confundir com o rótulo).
- `_numero_pela_chave(texto: str) -> str` — Chave de acesso da NF-e (44 dígitos): as posições 26 a 34 são o número da nota — sem chance de erro.
- `extrair_nota(texto: str) -> dict` — Dados de um DANFE lido em PDF ou foto (melhor esforço: a tela mostra tudo para conferência).
- `_valores_do_texto(texto: str) -> list[float]` — Valores em reais aceitando o ponto como separador decimal (o OCR troca a vírgula do cheque).
- `_data_escrita_a_mao(trecho: str, hoje: date \| None=None) -> date \| None` — Data escrita à mão (ex.: "Bom p/ 24/09/26") lida de um trecho com ruído de OCR.
- `_perto_do_rotulo(texto: str, rotulo: str, padrao: str) -> str` — Valor que aparece **antes ou depois** do rótulo (o OCR de cheque inverte a ordem com frequência).
- `ler_cmc7(texto: str) -> dict` — Números impressos no rodapé do cheque (CMC7): banco, agência, conta e número do cheque.
- `_campos_cmc7(campo1: str, campo2: str, campo3: str) -> dict`
- `ler_todos_cmc7(texto: str) -> list[dict]` — Todas as linhas CMC-7 do texto (um depósito pode ter vários cheques), sem repetir.
- `extrair_cheque(texto: str, legenda: str='') -> dict` — Tudo o que dá para ler de um cheque escaneado, somado ao que veio escrito na mensagem.
- `_emitente_do_cheque(texto: str) -> str` — Nome de quem assinou o cheque: o nome de empresa que mais aparece e não é do banco.
- `_numeros_em_sequencia(texto: str) -> list[str]` — Lista de pedidos escrita à mão no verso: "7200-7201-7219-7245-7255" em uma ou várias linhas.
- `extrair_comprovante(texto: str, legenda: str='') -> dict` — Comprovante de Pix, TED ou depósito: valor, data, hora, pagador, identificador e notas citadas.
- `_pagador(texto: str) -> str`
- `ler_fechamento(texto: str) -> dict` — Lê o print (ou o texto colado) de um fechamento já existente, linha por linha.
- `analisar(dados: bytes, nome_arquivo: str='', legenda: str='') -> dict` — Lê um arquivo recebido e devolve ``{"tipo": ..., "dados": {...}, "texto": ...}``.
- `publico(analise: dict) -> dict` — Formato devolvido para a tela (datas em texto, sem o texto bruto do arquivo).

## `app/empresas/modelos.py`

> Abas do banco de dados do módulo Empresas (empresas, notas fiscais, cheques e recebimentos).
> 
> Usa a mesma estrutura das abas de boletos e Pix (``app/planilha.py``), então tudo o que já existe vale aqui:
> banco SQLite, planilha Excel gerada automaticamente (``dados/fechamentos.xlsx``), histórico de quem fez cada
> alteração, backup diário e edição pela própria planilha.

**Constantes:** `COR_EMPRESAS` = `'1F5FA8'` · `COR_NOTAS` = `'0F3D3E'` · `COR_CHEQUES` = `'6B3FA0'` · `COR_RECEBIMENTOS` = `'1B7F4B'` · `DIA_FECHAMENTO_PADRAO` = `20` · `STATUS_EMPRESA` = `('Ativa', 'Inativa')` · `STATUS_NOTA` = `('Em aberto', 'Em cheque', 'Parcial', 'Recebido', 'Cancelado')` · `STATUS_CHEQUE` = `('Em carteira', 'Depositado', 'Compensado', 'Devolvido', 'Cancelado')` · `STATUS_RECEBIMENTO` = `('Confirmado', 'Cancelado')` · `FORMAS_RECEBIMENTO` = `('Pix', 'TED', 'Depósito', 'Cheque', 'Dinheiro', 'Outro')` · `UNIDADES` = `('M³', 'TON', 'UN', 'KG', 'L', 'H', 'SC', 'PC')` · `COLUNAS_EMPRESAS` = `[Coluna('id', 'ID', 7, '0'), Coluna('nome', 'Empresa', 30), Coluna('razao_social', 'Razão Social', 40), Coluna('cnpj', 'CNPJ', 20, '@'), Coluna('apelidos', '…` · `COLUNAS_NOTAS` = `[Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('empresa', 'Empresa', 28), Coluna('material', 'Material', 28), Coluna('unidade'…` · `COLUNAS_CHEQUES` = `[Coluna('id', 'ID', 7, '0'), Coluna('empresa', 'Empresa', 28), Coluna('numero', 'Nº do Cheque', 14, '@'), Coluna('vencimento', 'Bom para', 12, 'dd/mm/yyyy'),…` · `COLUNAS_RECEBIMENTOS` = `[Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 9, '@'), Coluna('empresa', 'Empresa', 28), Coluna('forma', 'For…` · `_TEXTOS_COMUNS` = `frozenset({'observacoes', 'arquivo', 'arquivo_nome', 'lancado_por'})` · `ABAS_EMPRESAS` = `{'empresas': DefinicaoAba('empresas', 'Empresas', tuple(COLUNAS_EMPRESAS), frozenset({'nome', 'razao_social', 'cnpj', 'apelidos', 'dia_fechamento', 'contato'…`


## `app/empresas/relatorio.py`

> Relatório de fechamento de uma empresa, no mesmo formato da planilha usada hoje.
> 
> Cabeçalho com a minha empresa e o CNPJ, "Fechamento <Empresa>" e as colunas DATA, MATERIAL, UNIDADE, QUANT.,
> VALOR UNI., VALOR TOTAL, NOTA FISCAL e Nº PEDIDO, com o total no rodapé. Abaixo da tabela, o que já foi
> recebido e quanto ainda falta. Sai em Excel e em PDF; o texto curto vai pelo Telegram.

**Constantes:** `COLUNAS` = `[('DATA', 13), ('MATERIAL', 26), ('UNIDADE', 11), ('QUANT.', 10), ('VALOR UNI.', 13), ('VALOR TOTAL', 15), ('NOTA FISCAL', 13), ('Nº PEDIDO', 12)]` · `VERDE` = `'E2EFDA'` · `VERDE_FORTE` = `'C6E0B4'` · `AZUL` = `'1F4E79'` · `MOEDA` = `'"R$" #,##0.00'` · `LINHAS_EM_BRANCO` = `7`

- `_moeda(valor) -> str`
- `_data(valor) -> str`
- `cabecalho_minha_empresa(minha_empresa: dict) -> str`
- `nome_do_arquivo(f: dict, extensao: str) -> str`
- `gerar_xlsx(f: dict, minha_empresa: dict \| None=None) -> bytes`
- `gerar_pdf(f: dict, minha_empresa: dict \| None=None) -> bytes`
- `resumo_telegram(f: dict, minha_empresa: dict \| None=None) -> str`

## `app/empresas/servico.py`

> Regras do módulo Empresas: cadastro, fechamento por período, baixa automática e cheques.
> 
> **Fechamento** — cada empresa fecha no dia 20 (ou no dia escolhido). O fechamento de agosto, por exemplo, vai
> de 21/07 até 20/08: a nota entra no fechamento pelo dia em que foi emitida.
> 
> **Baixa automática** — um recebimento (Pix, TED, depósito ou cheque compensado) é dividido entre as notas
> fiscais citadas no comprovante, da mais antiga para a mais nova. Quando o valor não cobre tudo, a nota fica
> "Parcial" e o fechamento mostra quanto ainda falta. O que sobra fica registrado como crédito da empresa.
> 
> **Cheques** — ao receber um cheque pré-datado, as notas dos pedidos citados ficam "Em cheque" (o dinheiro
> ainda não entrou). Quando o cheque é compensado (ou chega o comprovante do depósito), vira um recebimento e
> as notas são baixadas.

**Constantes:** `TOLERANCIA` = `0.01` · `ABERTAS` = `('Em aberto', 'Em cheque', 'Parcial')`

- **classe `ErroEmpresas`** — Erro de regra de negócio (mensagem já pronta para a pessoa ler).
- `normalizar(texto: str) -> str`
- `digitos(texto) -> str`
- `numero(texto) -> str` — Número de NF ou pedido sem zeros à esquerda, para comparar ``006859`` com ``6859``.
- `lista_de_numeros(valor) -> list[str]`
- `texto_de_numeros(valores) -> str`
- `moeda(valor) -> str`
- `_data(valor) -> date \| None`
- `_valor(dados: dict, chave: str) -> float`
- `banco()`
- `configuracao()`
- `listar(aba: str) -> list[dict]`
- `dia_fechamento(empresa: dict \| None=None) -> int`
- `competencia_de(data: date, dia: int) -> str` — Em qual fechamento a nota entra: até o dia do fechamento, no mês dela; depois, no mês seguinte.
- `periodo(competencia: str, dia: int) -> tuple[date, date]` — Primeiro e último dia do fechamento (ex.: 2026-08 com dia 20 → 21/07/2026 a 20/08/2026).
- `competencia_atual(dia: int, hoje: date \| None=None) -> str`
- `competencia_anterior(competencia: str) -> str`
- `titulo_competencia(competencia: str) -> str`
- `empresas(incluir_inativas: bool=True) -> list[dict]`
- `obter_empresa(id_: int) -> dict`
- `empresa_por_nome(nome: str) -> dict \| None`
- `_nomes_da_empresa(empresa: dict) -> list[str]`
- `identificar_empresa(*, cnpj: str='', nome: str='', texto: str='') -> dict \| None` — Descobre de qual empresa é um documento: primeiro pelo CNPJ, depois pelo nome ou pelos apelidos.
- `salvar_empresa(dados: dict, usuario: str='', id_: int \| None=None) -> dict`
- `renomear_empresa(antes: str, depois: str, usuario: str='') -> int` — A empresa é guardada pelo nome nas notas, cheques e recebimentos: renomear atualiza todos.
- `excluir_empresa(id_: int, usuario: str='') -> None`
- `garantir_empresa(nome: str, cnpj: str='', usuario: str='') -> dict` — Empresa do documento recebido: usa a cadastrada ou cadastra uma nova com o nome lido.
- `formatar_cnpj(valor: str) -> str`
- `notas_da_empresa(empresa: str, competencia: str='', somente_abertas: bool=False) -> list[dict]`
- `notas_por_numero(numero_nf: str, empresa: str='') -> list[dict]`
- `lancar_notas(empresa: str, itens: list[dict], usuario: str='', arquivo: dict \| None=None, competencia: str='') -> list[dict]` — Lança as linhas de uma nota fiscal (uma por material) no fechamento da empresa.
- `atualizar_nota(id_: int, dados: dict, usuario: str='') -> dict`
- `mover_nota_fiscal(empresa: str, numero_nf: str, competencia: str, usuario: str='') -> list[dict]` — Leva todas as linhas de uma nota fiscal para outro fechamento (ex.: a NF chegou depois do dia 20).
- `excluir_nota(id_: int, usuario: str='') -> None`
- `_restante(nota: dict) -> float`
- `_candidatas(empresa: str, numeros_nf: list[str], pedidos: list[str]) -> list[dict]` — Notas que o recebimento pode baixar: as citadas no comprovante ou, sem citação, as mais antigas em aberto.
- `_aplicar(empresa: str, valor: float, numeros_nf: list[str], pedidos: list[str], data: date, usuario: str, cheque_id: int \| None=None) -> tuple[list[dict], float]` — Divide o valor recebido entre as notas, da mais antiga para a mais nova. Devolve (baixas, sobra).
- `texto_das_baixas(baixas: list[dict], sobra: float=0.0) -> str`
- `_baixas_do_texto(texto: str) -> list[tuple[int, float]]`
- `sobra_do_recebimento(recebimento: dict) -> float` — Quanto deste recebimento ainda não baixou nota nenhuma (crédito da empresa).
- `credito_da_empresa(empresa: str) -> float`
- `aplicar_creditos(empresa: str, usuario: str='') -> list[dict]` — Dinheiro que chegou antes da nota: assim que a nota é lançada, o crédito baixa sozinho.
- `registrar_recebimento(dados: dict, usuario: str='', arquivo: dict \| None=None) -> dict` — Registra um Pix/TED/depósito/cheque recebido e dá baixa nas notas fiscais citadas.
- `_empresa_pelas_notas(numeros_nf: list[str], pedidos: list[str]) -> str`
- `cancelar_recebimento(id_: int, usuario: str='') -> dict` — Desfaz a baixa: devolve os valores às notas e marca o recebimento como cancelado.
- `cheques(empresa: str='', status: str='') -> list[dict]`
- `lancar_cheque(dados: dict, usuario: str='', arquivo: dict \| None=None) -> dict` — Guarda um cheque pré-datado e marca como "Em cheque" as notas dos pedidos citados.
- `vincular_notas_ao_cheque(cheque: dict, usuario: str='') -> list[dict]` — Notas dos pedidos/NFs do cheque ficam "Em cheque": o pagamento está garantido, mas ainda não entrou.
- `atualizar_cheque(id_: int, dados: dict, usuario: str='') -> dict`
- `compensar_cheque(cheque: dict, usuario: str='', data: date \| None=None, arquivo: dict \| None=None) -> dict` — Cheque compensado (ou depósito comprovado): vira um recebimento e dá baixa nas notas.
- `soltar_notas_do_cheque(cheque: dict, usuario: str='') -> None`
- `excluir_cheque(id_: int, usuario: str='') -> None`
- `cheque_parecido(dados: dict) -> dict \| None` — Evita cadastrar o mesmo cheque duas vezes (mesmo número e valor, ou mesma linha CMC7).
- `cheque_do_comprovante(empresa: str, valor, texto: str='') -> dict \| None` — Comprovante de depósito de um cheque que está em carteira: mesmo valor (ou número citado).
- `cheques_do_deposito(dados: dict) -> list[dict]` — Os cheques em carteira que aparecem num comprovante de depósito (pela linha CMC-7 ou pelo número).
- `cheques_a_depositar(hoje: date \| None=None, dias: int=0) -> list[dict]`
- `fechamento(empresa: str, competencia: str='', hoje: date \| None=None) -> dict` — Fechamento de uma empresa: as linhas do período, o total, o que já foi recebido e quanto falta.
- `resumo_empresas(hoje: date \| None=None, competencia: str='') -> list[dict]` — Uma linha por empresa: fechamento atual, quanto falta receber e o que está em atraso.
- `alertas_de_cheques(hoje: date \| None=None, dias_antes: int=3) -> list[dict]` — Cheques a depositar no formato dos avisos de vencimento (Windows, Telegram e e-mail).

## `app/entrada.py`

> Caixa de entrada: boletos que chegam sozinhos por e-mail e pelo bot do Telegram.
> 
> * **E-mail** — o sistema confere, a cada 5 minutos, uma caixa de e-mail (IMAP) e lê os PDFs e fotos anexados.
>   As mensagens não são apagadas nem marcadas como lidas. Na primeira vez, olha os e-mails dos últimos 7 dias.
>   Dá para aceitar só alguns remetentes (ex.: ``fornecedor.com.br, contas@empresa.com``).
> * **Telegram** — as pessoas cadastradas em Notificações → Telegram podem encaminhar a foto ou o PDF do boleto
>   para o bot. O bot responde com o que conseguiu ler. Arquivos de pessoas não cadastradas são recusados.
> 
> Boletos não são lançados sem conferência: cada boleto lido fica na caixa de entrada (tela Ler boletos) até alguém
> revisar e lançar, ou descartar. O mesmo arquivo recebido duas vezes é ignorado, e boletos que já estavam lançados
> saem sozinhos da caixa.
> 
> **Comprovantes de pagamento** são tratados na hora: o sistema descobre de qual boleto ou Pix é, marca como pago
> com o valor pago, juros/multa e desconto, e anexa o comprovante. Quando não dá para ter certeza (ex.: parcelas
> iguais), o comprovante fica na caixa de entrada para alguém escolher o lançamento.

**Constantes:** `MASCARA` = `'••••••••'` · `INTERVALO_EMAIL` = `300` · `INTERVALO_TELEGRAM` = `45` · `DIAS_PRIMEIRA_LEITURA` = `7` · `MAX_EMAILS_POR_VEZ` = `40` · `MAX_ITENS` = `300` · `DIAS_MANTER_CONCLUIDOS` = `30` · `TAMANHO_MINIMO_IMAGEM` = `15000` · `TAMANHO_MAXIMO` = `20 * 1024 * 1024` · `EXTENSOES` = `('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.bmp', '.tif', '.tiff')` · `PADRAO` = `{'itens': [], 'email': {'ativo': False, 'servidor': '', 'porta': 993, 'usuario': '', 'senha': '', 'pasta': 'INBOX', 'remetentes': '', 'uidvalidity': None, 'u…`

- `_moeda(valor) -> str`
- `_data_br(valor) -> str`
- `_agora() -> str`
- `_texto_cabecalho(valor) -> str`
- `remetente_permitido(endereco: str, filtro: str) -> bool`
- `anexos_do_email(bruto: bytes) -> tuple[dict, list[tuple[str, bytes]]]` — Cabeçalho resumido e anexos úteis (PDF e imagens) de uma mensagem.
- `resumo_da_leitura(resultado: dict \| None) -> dict` — O que foi lido (para mostrar na lista e responder no Telegram).
- **classe `CaixaEntrada`**
  - `__init__(self, caminho: Path, processar: Callable[[bytes, str], dict], salvar_arquivo: Callable[[bytes, str], dict], telegram: Callable[[], tuple[str, list[dict]]], registrar_pagamento: Callable[..., dict] \| None=None, comandos=None)` — ``processar`` lê um arquivo (como a tela Ler boletos); ``salvar_arquivo`` guarda arquivos que não puderam ser lidos; ``telegram`` devolve (token do bot, pessoas cadastradas); ``registrar_pagamento(aba, id, extraido, usuario, arquivo_id)`` marca um lançamento como pago a partir de um comprovante e devolve o resumo.
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `config_publica(self) -> dict`
  - `configurar(self, novo: dict) -> dict`
  - `_publico(item: dict) -> dict`
  - `listar(self, incluir_concluidos: bool=False) -> list[dict]`
  - `obter(self, id_: str) -> dict \| None`
  - `contagem(self) -> int`
  - `arquivos_em_uso(self) -> set[str]`
  - `_concluir(self, filtro, estado_novo: str) -> int`
  - `descartar(self, id_: str) -> bool`
  - `marcar_lancados(self, arquivo_ids: set[str]) -> int`
  - `_limpar_antigos(self) -> None`
  - `receber(self, dados: bytes, nome: str, origem: str, remetente: str='', assunto: str='', usuario: str='') -> dict \| None` — Lê um arquivo recebido e o coloca na caixa de entrada. Devolve o item, ou None se já tinha chegado antes.
  - `_ja_lancado(resultado: dict \| None) -> bool` — Todos os boletos/Pix do arquivo já estão na planilha: não há nada para conferir.
  - `_registrar_comprovante(self, item: dict, usuario: str) -> None`
  - `associar(self, id_: str, aba: str, registro_id: int, usuario: str) -> dict` — Comprovante que ficou em dúvida: alguém escolheu de qual lançamento ele é.
  - `concluir_ja_lancados(self) -> int` — Arquivos que chegaram antes desta regra e cujos boletos já estavam todos lançados.
  - `verificar_email(self, conectar=None) -> dict` — Confere a caixa de e-mail. ``conectar`` permite substituir o IMAP nos testes.
  - `_conectar_imap(cfg: dict)`
  - `_registrar_email(self, erro: str \| None=None, **campos) -> None`
  - `chats_recentes(self) -> list[dict]`
  - `_lembrar_chat(self, chat: dict) -> None`
  - `verificar_telegram(self) -> dict`
  - `_responder_comando(self, token: str, chat_id: str, mensagem: dict, cadastrados: dict) -> None`
  - `_registrar_comandos(self, token: str) -> None` — Mostra os comandos no menu "/" do Telegram (uma vez por execução).
  - `_arquivo_da_mensagem(mensagem: dict) -> tuple[str, str, int] \| None`
  - `_mensagem_resposta(item: dict \| None) -> str`
  - `_mensagem_comprovante(item: dict) -> str`
  - `_responder(token: str, chat_id: str, texto: str) -> None`
  - `_registrar_telegram(self, erro: str \| None=None) -> None`
  - `verificar_agora(self, canal: str) -> dict`
  - `iniciar_agendador(self, espera_inicial: float=30) -> None`
  - `parar(self) -> None`

## `app/fechamento.py`

> Fechamento do mês para o contador: resumo, gastos por centro de custo, pagos e em aberto (boletos + Pix).
> 
> * base **vencimento** — tudo o que vence no mês (pagos, em aberto e cancelados);
> * base **pagamento** — o que foi efetivamente pago no mês (pela data de pagamento).
> 
> Nos pagos, o valor efetivamente pago (com juros/multa ou desconto, lidos do comprovante) é o que entra nos totais.
> 
> Sai em Excel, em PDF ou num ZIP com os dois arquivos e os comprovantes de pagamento anexados.

**Constantes:** `MESES` = `['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']` · `SEM_CENTRO` = `'Sem centro de custo'` · `MOEDA` = `'"R$" #,##0.00'` · `COR` = `'0F3D3E'`

- `ler_mes(texto: str \| None, hoje: date \| None=None) -> date`
- `_no_mes(valor, mes: date) -> bool`
- `_item(registro: dict, tipo: str, hoje: date) -> dict`
- `montar(boletos: list[dict], pix: list[dict], mes: date, base: str='vencimento', hoje: date \| None=None, caixa: list[dict] \| None=None) -> dict` — ``caixa``: saídas em dinheiro (já pagas na data da saída), no formato de ``caixa.servico.saidas_para_gastos``.
- `_descricao_base(f: dict) -> str`
- `_data(valor) -> str`
- `_moeda(valor: float) -> str`
- `_cabecalho(ws, linha: int, titulos: list[tuple[str, int]]) -> None`
- `_aba_lancamentos(wb, titulo: str, itens: list[dict], pagos: bool) -> None`
- `gerar_xlsx(f: dict) -> bytes`
- `gerar_pdf(f: dict) -> bytes`
- `_nome_arquivo(texto: str) -> str`
- `gerar_zip(f: dict, caminho_comprovante) -> bytes` — ``caminho_comprovante(item)`` devolve o Path do comprovante anexado (ou None).

## `app/fila_gravacao.py`

> Fila de gravação na planilha.
> 
> Quando a planilha está aberta no Excel (arquivo bloqueado), lançamentos e alterações — de boletos e de
> Pix — não se perdem: ficam guardados em ``dados/gravacao_pendente.json`` e são gravados automaticamente,
> todos de uma vez, assim que o arquivo for fechado. Enquanto isso aparecem nas listas, no painel e nas
> notificações, marcados como "aguardando gravação".
> 
> Lançamentos ainda não gravados recebem IDs provisórios negativos (-1, -2...). Alterações feitas neles
> são aplicadas no próprio lançamento pendente; excluí-los simplesmente cancela o lançamento.

**Constantes:** `INTERVALO_TENTATIVAS` = `15`

- `_para_json(dados: dict, aba: str) -> dict`
- `_de_json(dados: dict) -> dict`
- `_agora() -> str`
- `_aba(operacao: dict) -> str`
- **classe `FilaGravacao`**
  - `__init__(self, planilha, caminho: Path, intervalo: int=INTERVALO_TENTATIVAS)`
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `pendentes(self) -> int`
  - `_operacao_de_adicao(self, id_provisorio: int, aba: str) -> dict \| None`
  - `enfileirar_adicao(self, dados: dict, aba: str='boletos', usuario: str='') -> dict`
  - `enfileirar_atualizacao(self, id_: int, dados: dict, aba: str='boletos', usuario: str='') -> None`
  - `cancelar(self, op_id: str) -> bool`
  - `cancelar_provisorio(self, id_provisorio: int, aba: str='boletos') -> None`
  - `_registro_provisorio(operacao: dict) -> dict`
  - `registro_provisorio(self, id_provisorio: int, aba: str='boletos') -> dict`
  - `sobrepor(self, registros: list[dict], aba: str='boletos') -> list[dict]` — Registros da planilha + alterações e lançamentos que ainda aguardam gravação.
  - `processar(self) -> dict \| None` — Tenta gravar tudo o que está pendente numa única abertura da planilha.
  - `status(self) -> dict`
  - `iniciar_agendador(self) -> None`
  - `parar(self) -> None`

## `app/ia.py`

> Leitura assistida por IA (Claude, com visão) — opcional.
> 
> Ativada quando ``ANTHROPIC_API_KEY`` está definida no arquivo ``.env``. Usada para fotos
> difíceis (desfocadas, amassadas, com reflexo) em que o OCR local não encontra tudo.
> O resultado nunca é aceito às cegas: a linha digitável passa pela validação dos DVs.

**Constantes:** `CAMPOS` = `('linha_digitavel', 'beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor', 'observacoes')` · `ESQUEMA` = `{'type': 'object', 'properties': {'linha_digitavel': {'type': 'string', 'description': 'Somente dígitos; vazio se ilegível'}, 'beneficiario': {'type': 'strin…` · `INSTRUCOES` = `'Você está lendo um boleto brasileiro (PDF ou foto). Transcreva exatamente o que está impresso:\n\n- linha_digitavel: a linha digitável (47 dígitos em boleto…`

- **classe `ErroIA`**
- `disponivel() -> bool`
- `_bloco_arquivo(dados: bytes) -> dict`
- `extrair(dados: bytes, pagina: int=0) -> dict`

## `app/importacao.py`

> Importação de boletos exportados de outros sistemas (ERP, financeiro, contas a pagar).
> 
> Aceita Excel (.xlsx/.xlsm e .xls — inclusive o ".xls" em HTML que muitos sistemas geram), CSV e TXT.
> As colunas são reconhecidas pelo nome, com os sinônimos mais comuns ("Fornecedor", "Vencto", "Valor Título"...),
> e o usuário confere o mapeamento antes de importar. Cada linha é validada (linha digitável, valor, vencimento)
> e comparada com a planilha para não lançar o mesmo boleto duas vezes. O mapeamento escolhido fica salvo e é
> reaproveitado na próxima importação de um arquivo com as mesmas colunas.

**Constantes:** `MAX_LINHAS` = `5000` · `MAX_COLUNAS` = `80` · `LINHAS_BUSCA_CABECALHO` = `30` · `HORAS_GUARDAR_ARQUIVOS` = `24` · `CAMPOS` = `[{'chave': 'linha_digitavel', 'rotulo': 'Linha digitável / código de barras'}, {'chave': 'beneficiario', 'rotulo': 'Beneficiário / fornecedor'}, {'chave': 'd…` · `CHAVES_CAMPOS` = `[c['chave'] for c in CAMPOS]` · `APELIDOS` = `{'linha_digitavel': ['linha digitavel', 'codigo de barras', 'codigo barras', 'cod barras', 'cod de barras', 'barras', 'linha', 'codigo do boleto', 'represent…` · `EXCLUIR` = `{'linha_digitavel': {'nosso'}, 'beneficiario': {'sacado', 'pagador', 'cpf', 'cnpj', 'banco', 'conta'}, 'documento_beneficiario': {'numero', 'nosso'}, 'numero…` · `MESES` = `{'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}` · `FORMATOS` = `{'xlsx': 'Excel', 'xls': 'Excel 97-2003', 'html': 'Excel (HTML)', 'csv': 'CSV / texto'}` · `RE_DATA_ISO` = `re.compile('^\\s*(\\d{4})-(\\d{1,2})-(\\d{1,2})')` · `RE_DATA_BR` = `re.compile('^\\s*(\\d{1,2})[/.\\-](\\d{1,2})[/.\\-](\\d{2,4})(?:[\\sT]\|$)')` · `RE_DATA_MES` = `re.compile('^\\s*(\\d{1,2})[/\\-\\s]+(?:de\\s+)?([a-z]{3})[a-z]*[/\\-\\s]+(?:de\\s+)?(\\d{2,4})')`

- **classe `ErroImportacao`**
- `_vazio(valor) -> bool`
- `texto(valor) -> str`
- `normalizar_titulo(valor) -> str`
- `ler_data(valor) -> date \| None`
- `ler_valor(valor) -> float \| None`
- `ler_status(valor, padrao: str='Pendente') -> str`
- `formatar_documento(valor: str) -> str`
- `_brl(valor: float) -> str`
- `_com_dados(valores) -> bool`
- `_ler_xlsx(dados: bytes) -> OrderedDict`
- `_ler_xls(dados: bytes) -> OrderedDict`
- **classe `_LeitorTabelasHtml`**
  - `__init__(self)`
  - `handle_starttag(self, tag, attrs)`
  - `handle_data(self, data)`
  - `handle_endtag(self, tag)`
- `_decodificar(dados: bytes) -> str`
- `_ler_html(dados: bytes) -> OrderedDict`
- `_ler_texto(dados: bytes) -> OrderedDict`
- `ler_planilhas(dados: bytes, nome: str='') -> tuple[str, OrderedDict]` — Lê o arquivo e devolve (formato, {aba: [(número da linha, [valores])]}).
- `_pontuar(campo: str, titulo_norm: str) -> int`
- `_reconhecidos(valores) -> int`
- `_parece_dado(valor) -> bool`
- `detectar_cabecalho(linhas) -> tuple[int, int]` — (número da linha dos títulos ou 0 se não houver, quantidade de títulos reconhecidos).
- `montar_tabela(abas: OrderedDict, aba: str \| None=None, linha_cabecalho: int \| None=None) -> dict`
- `descrever_colunas(tabela: dict) -> list[dict]`
- `sugerir_mapeamento(colunas: list[str], linhas) -> dict[str, int \| None]`
- `validar_mapeamento(mapeamento: dict, largura: int) -> dict[str, int \| None]`
- `_chave_sem_codigo(beneficiario, numero_documento, valor, vencimento) -> str \| None`
- `preparar(tabela: dict, mapeamento: dict, *, existentes: list[dict], centro_padrao: str='', status_padrao: str='Pendente', nome_arquivo: str='', hoje: date \| None=None) -> list[dict]` — Converte as linhas do arquivo em boletos, com estado: pronto, aviso, erro, duplicado ou repetido.
- `serializar_item(item: dict) -> dict`
- `resumir(itens: list[dict]) -> dict`
- **classe `ArmazemImportacoes`** — Guarda por algumas horas o arquivo enviado, para a prévia e a importação sem reenviar.
  - `__init__(self, pasta: Path, horas: int=HORAS_GUARDAR_ARQUIVOS)`
  - `_caminhos(self, id_: str) -> tuple[Path, Path]`
  - `salvar(self, dados: bytes, nome: str) -> str`
  - `nome(self, id_: str) -> str`
  - `planilhas(self, id_: str) -> tuple[str, OrderedDict]`
  - `remover(self, id_: str) -> None`
  - `limpar(self) -> int`
- **classe `ModelosMapeamento`** — Lembra quais colunas foram usadas em cada tipo de arquivo (identificado pelos títulos das colunas).
  - `__init__(self, caminho: Path, limite: int=50)`
  - `_assinatura(colunas: list[str]) -> str`
  - `_ler(self) -> dict`
  - `obter(self, colunas: list[str]) -> dict[str, int \| None] \| None`
  - `salvar(self, colunas: list[str], mapeamento: dict) -> None`
- `gerar_modelo() -> bytes` — Planilha modelo para quem pode escolher as colunas exportadas pelo outro sistema.

## `app/inicializacao.py`

> Iniciar o Fin Pro junto com o Windows.
> 
> Cria um pequeno script na pasta "Inicializar" do usuário que abre o aplicativo (janela própria) quando
> o computador é ligado — ou apenas o ícone na bandeja, se preferir iniciar minimizado. Assim o agendador
> de lembretes funciona mesmo que o sistema não seja aberto manualmente.

**Constantes:** `NOME_ARQUIVO` = `f'{config.NOME_APP}.vbs'` · `NOMES_ANTIGOS` = `('Leitor de Boletos.vbs',)` · `ARGUMENTO_BANDEJA` = `'--bandeja'`

- `pasta_inicializar() -> Path \| None`
- `_pythonw() -> Path`
- `_limpar_antigos(pasta: Path \| None) -> None` — O script com o nome antigo sai de cena (senão o aplicativo abriria duas vezes).
- `status(pasta: Path \| None=None) -> dict`
- `ativar(pasta: Path \| None=None, minimizado: bool=False) -> dict`
- `desativar(pasta: Path \| None=None) -> dict`

## `app/janela.py`

> Ponte entre o servidor e a janela do aplicativo.
> 
> Quando o sistema roda como aplicativo de desktop, ``app.desktop`` registra aqui as funções que mostram a
> janela e encerram o aplicativo. A API usa isso para trazer a janela para a frente (ao clicar numa
> notificação, abrir o atalho de novo com o app já aberto etc.). No modo navegador nada é registrado.

- `registrar(mostrar: Callable[[str \| None], None], encerrar: Callable[[], None] \| None=None) -> None`
- `desregistrar() -> None`
- `ativa() -> bool`
- `mostrar(rota: str \| None=None) -> bool`
- `encerrar() -> bool`

## `app/main.py`

> Aplicação HTTP (FastAPI): junta as rotas de ``app/rotas``, inicia os serviços e serve o front-end.

- `_aquecer_ocr() -> None`
- `_limpar_temporarios() -> None`
- `_telegram_da_caixa_de_entrada() -> tuple[str, list[dict]]`
- `_ler_arquivo_recebido(dados: bytes, nome: str) -> dict`
- `_registrar_pagamento_recebido(aba: str, id_: int, extraido: dict, usuario: str, arquivo_id: str \| None) -> dict`
- `_guardar_arquivo_do_cliente(dados: bytes, nome: str) -> dict` — Guarda a nota fiscal, o cheque ou o comprovante recebido e devolve o caminho usado na planilha.
- `_pessoas_dos_outros_bots() -> dict[str, str]` — Quem pode usar o bot do caixa: as mesmas pessoas e grupos do bot dos boletos e do bot de notas.
- `_centros_ativos() -> list[str]`
- `_criar_centro(nome: str, usuario: str) -> str`
- `async lifespan(_app: FastAPI)`
- `async _sem_cache_na_interface(request: Request, call_next)` — Telas (HTML/JS/CSS) nunca ficam em cache: depois de uma atualização, o app nunca mostra arquivos antigos.
- `async _planilha_bloqueada(_request: Request, exc: PlanilhaBloqueadaError)`
- `async _nao_encontrado(request: Request, _exc: RegistroNaoEncontrado)`

## `app/notificacoes/__init__.py`

> Notificações de boletos a vencer (Windows, Telegram e e-mail).


## `app/notificacoes/canais.py`

> Canais de envio: notificação do Windows, Telegram e e-mail (somente biblioteca padrão).

**Constantes:** `_SCRIPT_TOAST` = `"\n$ErrorActionPreference = 'Stop'\n[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] \| Out-Null\n[…` · `TIPOS_CHAT` = `{'private': 'privado', 'group': 'grupo', 'supergroup': 'grupo', 'channel': 'canal'}`

- **classe `ErroCanal`**
- `enviar_windows(titulo: str, mensagem: str, url: str \| None=None, url_pago: str \| None=None) -> None`
- `_recusar_na_demonstracao(canal: str) -> None`
- `_telegram(token: str, metodo: str, dados: dict \| None=None)`
- `enviar_telegram(token: str, chat_id: str, html: str) -> None`
- `detectar_chat_telegram(token: str) -> dict` — Descobre o chat a partir da última mensagem enviada ao bot (o usuário manda /start).
- `procurar_chats_telegram(token: str) -> dict` — Pessoas e grupos que falaram com o bot (enviaram /start ou adicionaram o bot a um grupo).
- `baixar_arquivo_telegram(token: str, file_id: str) -> bytes` — Baixa um arquivo enviado ao bot (fotos e documentos de até 20 MB).
- `enviar_email(cfg: dict, assunto: str, texto: str, html: str) -> None`

## `app/notificacoes/regras.py`

> Quais boletos devem ser avisados e como as mensagens são escritas.

**Constantes:** `DIAS_SEMANA` = `('segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo')` · `ORDEM_CATEGORIA` = `{'vencido': 0, 'hoje': 1, 'amanha': 2, 'proximos': 3}` · `EMOJI_CATEGORIA` = `{'vencido': '🔴', 'hoje': '🟠', 'amanha': '🟡', 'proximos': '🔵'}` · `LIMITE_TELEGRAM` = `3900`

- `brl(valor: float) -> str`
- `chave_alerta(alerta: dict) -> str` — Identifica um aviso: o mesmo boleto é avisado de novo quando muda de categoria (ex.: amanhã → hoje).
- `montar_alertas(registros: list[dict], hoje: date, dias_antes: int=3, incluir_vencidos: bool=True) -> list[dict]` — Boletos pendentes que vencem até ``dias_antes`` dias (e, opcionalmente, os já vencidos).
- `descrever_prazo(alerta: dict) -> str`
- `alertas_da_regra(registros: list[dict], hoje: date, regra: dict) -> list[dict]` — Boletos atendidos por um lembrete.
- `_titulo_individual(alerta: dict) -> str`
- **classe `Mensagem`**
- `montar_mensagem(alertas: list[dict], hoje: date, url_app: str) -> Mensagem`
- `mensagem_teste(url_app: str) -> Mensagem`

## `app/notificacoes/servico.py`

> Serviço de notificações: lembretes configuráveis, envio pelos canais, agenda, histórico e agendador.
> 
> Lembretes (regras):
> * ``vencimento`` — no dia do vencimento, em quantos horários o usuário quiser (padrão: 08:00, 12:00 e 16:00);
> * ``antes`` — N dias antes do vencimento;
> * ``vencidos`` — depois de vencido, por até N dias (0 = enquanto não for pago).
> 
> Cada lembrete tem seus horários e canais. O agendador confere a cada minuto: quando um horário é
> atingido, avisa os boletos pendentes daquele lembrete (cada boleto uma vez por horário). Se o sistema
> estava desligado e vários horários passaram, envia só o mais recente. Boletos pagos param de ser avisados.
> 
> Resumos da semana (``resumos``): na segunda, o que vence na semana; na sexta, o que foi pago. Cada um tem o seu
> horário e os seus canais e é enviado uma vez no dia (se o sistema abrir depois do horário, sai assim que abrir).
> 
> O estado fica em ``dados/notificacoes.json``.

**Constantes:** `MASCARA` = `'••••••••'` · `CANAIS` = `('windows', 'telegram', 'email')` · `TIPOS_REGRA` = `('vencimento', 'antes', 'vencidos')` · `INTERVALO_VERIFICACAO` = `60` · `ESPERA_APOS_FALHA` = `timedelta(minutes=15)` · `LIMITE_REGRAS` = `20` · `LIMITE_HORARIOS` = `12` · `_SEGREDOS` = `{('telegram', 'token'), ('email', 'senha')}` · `REGRAS_PADRAO` = `[{'id': 'vencimento', 'tipo': 'vencimento', 'dias': 0, 'horarios': ['08:00', '12:00', '16:00'], 'canais': list(CANAIS), 'ativo': True}, {'id': 'vespera', 'ti…` · `TIPOS_RESUMO` = `('segunda', 'sexta')` · `DIA_RESUMO` = `{'segunda': 0, 'sexta': 4}` · `RESUMOS_PADRAO` = `{'segunda': {'ativo': True, 'horario': '08:00', 'canais': ['telegram', 'email']}, 'sexta': {'ativo': True, 'horario': '17:00', 'canais': ['telegram', 'email']}}` · `PADRAO` = `{'ativo': True, 'resumos': RESUMOS_PADRAO, 'dias_semana': [0, 1, 2, 3, 4, 5, 6], 'regras': REGRAS_PADRAO, 'windows': {'ativo': True}, 'telegram': {'ativo': F…` · `RE_CHAT_TELEGRAM` = `re.compile('^-?\\d{1,20}$')` · `LIMITE_DESTINATARIOS` = `50`

- `_hora(texto: str) -> time`
- `normalizar_regras(regras) -> list[dict]`
- `normalizar_resumos(resumos, atuais: dict \| None=None) -> dict`
- `normalizar_destinatarios(lista, chat_id_antigo: str='') -> list[dict]` — Pessoas e grupos que recebem pelo Telegram: [{chat_id, nome, tipo, ativo}], sem repetidos.
- `_migrar_config_antiga(salvo: dict) -> list[dict]` — Converte a configuração da versão anterior (um horário + antecedência) em lembretes.
- **classe `ServicoNotificacoes`**
  - `__init__(self, planilha, caminho: Path, url_app: str, montar_link=None, montar_resumo=None)` — ``montar_resumo(tipo, hoje)`` devolve a ``Mensagem`` do resumo da semana (None = sem resumos).
  - `_ler(self) -> dict`
  - `_gravar(self, estado: dict) -> None`
  - `config_publica(self) -> dict`
  - `segredo(self, canal: str, campo: str) -> str`
  - `atualizar_config(self, novo: dict) -> dict`
  - `historico(self, limite: int=30) -> list[dict]`
  - `_janela(estado: dict) -> int`
  - `janela_dias(self) -> int`
  - `_alertas_do_estado(self, estado: dict, hoje: date \| None=None) -> list[dict]`
  - `alertas(self, hoje: date \| None=None) -> list[dict]` — Boletos para o sininho: vencidos (se houver lembrete de vencidos) e os que vencem na janela dos lembretes.
  - `_alterar_sino(self, alterar)` — Aplica uma alteração nos avisos vistos/dispensados, descartando os que não existem mais (pagos, mudaram de situação).
  - `marcar_vistos(self, chaves: list[str]) -> int`
  - `dispensar(self, chave: str) -> bool`
  - `restaurar_dispensados(self) -> int`
  - `agenda(self, agora: datetime \| None=None, dias: int=7, limite: int=40) -> list[dict]` — Próximos lembretes previstos com os boletos atuais (para conferir a configuração).
  - `_enviar_canal(self, canal: str, estado: dict, mensagem: Mensagem) -> None`
  - `_disparar(self, estado: dict, envios: dict[str, list[dict]], tipo: str, hoje: date, mensagem_fixa: Mensagem \| None=None) -> dict`
  - `_canais_ativos(estado: dict) -> list[str]`
  - `enviar_agora(self, hoje: date \| None=None) -> dict` — Envia agora os avisos atuais (vencidos e a vencer na janela dos lembretes) pelos canais ativos.
  - `testar_destinatario_telegram(self, chat_id: str, token: str \| None=None) -> None` — Mensagem de teste para uma única pessoa ou grupo (confere se ela vai receber os avisos).
  - `testar(self, canal: str) -> dict`
  - `_mensagem_resumo(self, tipo: str, hoje: date) -> Mensagem`
  - `previa_resumo(self, tipo: str, hoje: date \| None=None) -> dict`
  - `enviar_resumo(self, tipo: str, hoje: date \| None=None) -> dict` — Envia agora o resumo pelos canais escolhidos para ele (os que estiverem ligados).
  - `_verificar_resumos(self, agora: datetime) -> dict \| None`
  - `verificar(self, agora: datetime \| None=None) -> dict \| None` — Chamado pelo agendador a cada minuto. Devolve o resultado quando algo foi enviado (ou tentado).
  - `_verificar_lembretes(self, agora: datetime) -> dict \| None`
  - `iniciar_agendador(self, espera_inicial: float=20) -> None`
  - `parar(self) -> None`

## `app/pix.py`

> Pix: tipos de chave, validação, leitura e geração do "Pix Copia e Cola" (BR Code, padrão EMV QRCPS do Banco Central).

**Constantes:** `TIPOS_CHAVE` = `{'cpf_cnpj': 'CNPJ/CPF', 'celular': 'Celular', 'email': 'E-mail', 'aleatoria': 'Aleatória'}` · `RE_EMAIL` = `re.compile('^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$')` · `RE_UUID` = `re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)` · `RE_COPIA_E_COLA` = `re.compile('000201[\\x20-\\x7E]*?6304[0-9A-Fa-f]{4}')`

- **classe `ErroPix`**
- `_digitos(texto: str \| None) -> str`
- `cpf_valido(digitos: str) -> bool`
- `normalizar_chave(tipo: str, chave: str) -> str` — Valida a chave conforme o tipo e devolve no formato usado pelo Pix (sem máscara).
- `formatar_chave(tipo: str \| None, chave: str \| None) -> str`
- `inferir_tipo(chave: str \| None) -> str \| None`
- `crc16(payload: str) -> str` — CRC-16/CCITT-FALSE, usado no campo 63 do BR Code.
- `_tlv(texto: str) -> dict[str, str]`
- `ler_copia_e_cola(texto: str) -> dict` — Interpreta um "Pix Copia e Cola" e devolve chave, tipo, valor, recebedor, TXID etc.
- `_ascii(texto: str \| None, limite: int) -> str`
- `gerar_copia_e_cola(tipo: str, chave: str, valor: float \| None=None, recebedor: str='', cidade: str='BRASIL', txid: str='', descricao: str='') -> str` — Gera um Pix Copia e Cola estático (o banco confirma o recebedor pela chave na hora de pagar).
- `_qr_codes(imagem) -> list[str]`
- `ler_pix_de_arquivo(dados: bytes, max_paginas: int=10) -> list[dict]` — Procura QR codes Pix (e textos "Copia e Cola") numa imagem ou PDF.

## `app/planilha.py`

> Planilha Excel (.xlsx) usada como banco de dados.
> 
> Abas:
> * **Boletos** — um boleto por linha, com filtros, validação de status e destaque de vencidos/pagos;
> * **Pix** — pagamentos por Pix (tipo e chave, valor, recebedor, data prevista...);
> * **Resumo** — fórmulas que o Excel recalcula ao abrir (totais, vencidos...);
> * **Centros de Custo** — onde cada gasto foi feito (usado na análise de gastos);
> * **Histórico** — registro de cada lançamento, edição, pagamento, comprovante e exclusão, com o usuário que fez.
> 
> Gravações são atômicas (salva em arquivo temporário e substitui), agrupadas em lote e com backup diário.
> Se a planilha estiver aberta no Excel, a gravação falha com ``PlanilhaBloqueadaError`` — a fila de
> gravação guarda as operações e grava quando o arquivo for fechado.

**Constantes:** `ABA_BOLETOS` = `'Boletos'` · `ABA_PIX` = `'Pix'` · `ABA_RESUMO` = `'Resumo'` · `ABA_CENTROS` = `'Centros de Custo'` · `ABA_HISTORICO` = `'Histórico'` · `ABA_CAIXA` = `'Caixa'` · `COLUNAS_HISTORICO` = `[('Data/Hora', 18), ('Ação', 18), ('ID', 7), ('Beneficiário / Recebedor', 40), ('Vencimento', 13), ('Valor (R$)', 14), ('Detalhes', 60), ('Usuário', 22)]` · `STATUS_VALIDOS` = `('Pendente', 'Pago', 'Cancelado')` · `TIPOS` = `{'bancario': 'Bancário', 'arrecadacao': 'Arrecadação'}` · `TIPOS_CHAVE` = `{'cpf_cnpj': 'CNPJ/CPF', 'celular': 'Celular', 'email': 'E-mail', 'aleatoria': 'Aleatória'}` · `ROTULOS` = `{'tipo': TIPOS, 'tipo_chave': TIPOS_CHAVE}` · `LINHAS_FORMATADAS` = `20000` · `BACKUPS_MANTIDOS` = `30` · `COR_CABECALHO` = `'0F3D3E'` · `COR_FAIXA` = `'F3F7F7'` · `CENTROS_PADRAO` = `[('Administrativo', 'Escritório, contabilidade, bancos e despesas gerais'), ('Produção', 'Matéria-prima, insumos e serviços da produção'), ('Obras', 'Materia…` · `COLUNAS` = `[Coluna('id', 'ID', 7, '0'), Coluna('data_lancamento', 'Data de Lançamento', 19, 'dd/mm/yyyy hh:mm'), Coluna('linha_digitavel', 'Linha Digitável', 58, '@'), …` · `COLUNAS_PIX` = `[Coluna('id', 'ID', 7, '0'), Coluna('data_lancamento', 'Data de Lançamento', 19, 'dd/mm/yyyy hh:mm'), Coluna('recebedor', 'Recebedor', 38), Coluna('tipo_chav…` · `CAMPOS_DATA` = `{'vencimento', 'data_pagamento', 'data', 'data_deposito', 'data_recebimento', 'data_fechamento'}` · `CAMPOS_DATA_HORA` = `{'data_lancamento', 'atualizado_em', 'data_hora'}` · `CAMPOS_NUMERO` = `{'quantidade', 'litros', 'medidor', 'preco_litro'}` · `COLUNAS_CAIXA` = `[Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 8, '@'), Coluna('movimento', 'Entrada/Saída', 13), Coluna('valo…` · `MOVIMENTOS_CAIXA` = `('Entrada', 'Saída')` · `CAMPOS_AUTORIA` = `frozenset({'lancado_por', 'pago_por'})` · `CAMPOS_COMPROVANTE` = `frozenset({'comprovante', 'comprovante_nome'})` · `TEXTOS_COMUNS` = `CAMPOS_AUTORIA \| CAMPOS_COMPROVANTE` · `CAMPOS_PAGAMENTO` = `frozenset({'valor_pago', 'juros_multa', 'desconto'})` · `CAMPOS_MOEDA` = `{'valor', 'valor_unitario', 'valor_total', 'valor_recebido'} \| CAMPOS_PAGAMENTO` · `ABAS` = `{'boletos': DefinicaoAba('boletos', ABA_BOLETOS, tuple(COLUNAS), frozenset({'linha_digitavel', 'codigo_barras', 'beneficiario', 'documento_beneficiario', 'nu…` · `COLUNA_POR_CHAVE` = `ABAS['boletos'].por_chave` · `CAMPOS_EDITAVEIS` = `set(ABAS['boletos'].editaveis)`

- **classe `Coluna`**
- **classe `DefinicaoAba`**
  - `por_chave(self) -> dict[str, Coluna]`
  - `status_padrao(self) -> str`
  - `tem(self, chave: str) -> bool`
  - `letra(self, chave: str) -> str`
- **classe `PlanilhaBloqueadaError`** — A planilha está aberta/bloqueada por outro programa.
- **classe `RegistroNaoEncontrado`**
- `_letra(chave: str) -> str`
- `_estilizar_cabecalho(celula, cor: str) -> None`
- **classe `PlanilhaBoletos`**
  - `__init__(self, caminho: Path, pasta_backup: Path \| None=None, abas: dict[str, DefinicaoAba] \| None=None, extras: bool=True)` — ``abas``: conjunto de abas da planilha (padrão: Boletos e Pix). ``extras``: criar Resumo e Centros de Custo.
  - `garantir(self) -> None`
  - `migrar(self) -> bool` — Planilhas criadas por versões anteriores ganham as abas Pix e Centros de Custo e a coluna Centro de Custo.
  - `_formatar_aba(self, ws, definicao: DefinicaoAba) -> None`
  - `_criar_resumo(self, wb) -> None`
  - `_garantir_centros(wb)`
  - `_converter_leitura(chave: str, valor, definicao: DefinicaoAba \| None=None)`
  - `_ler_registros(self, wb, definicao: DefinicaoAba) -> list[dict]`
  - `_ler_com_cache(self, chave_cache: str, leitor) -> list`
  - `listar(self, aba: str='boletos') -> list[dict]`
  - `obter(self, id_: int, aba: str='boletos') -> dict`
  - `buscar_por_codigo(self, codigo_barras: str) -> list[dict]`
  - `nomes_por_documento(self) -> dict[str, str]` — CPF/CNPJ (somente dígitos) → nome de beneficiário usado no lançamento mais recente.
  - `listar_centros(self) -> list[dict]`
  - `_verificar_gravavel(self) -> None`
  - `_abrir_para_escrita(self)`
  - `_preparar_aba(self, wb, definicao: DefinicaoAba)`
  - `_garantir_colunas(ws, definicao: DefinicaoAba \| None=None) -> dict[str, int]`
  - `_indice_linhas(ws, mapa: dict[str, int]) -> dict[int, int]` — ID → número da linha (leitura em bloco, bem mais rápida que célula a célula).
  - `_ler_linha(self, ws, mapa: dict[str, int], linha: int, definicao: DefinicaoAba \| None=None) -> dict`
  - `_garantir_historico(wb)`
  - `_registrar_historico(ws, quando: datetime, acao: str, registro: dict, detalhes: str='', campo_nome: str='beneficiario', usuario: str='', campo_data: str='vencimento', campo_valor: str='valor') -> None`
  - `_descrever_alteracoes(antes: dict, dados: dict, definicao: DefinicaoAba \| None=None) -> tuple[str, str]`
  - `_escrever(ws, linha: int, mapa: dict[str, int], dados: dict, definicao: DefinicaoAba \| None=None) -> None`
  - `aplicar_lote(self, operacoes: list[dict]) -> list[dict]` — Aplica várias operações abrindo e salvando a planilha uma única vez.
  - `adicionar(self, dados: dict, aba: str='boletos', usuario: str='') -> dict`
  - `adicionar_lote(self, lista: list[dict], aba: str='boletos', usuario: str='') -> list[dict]`
  - `atualizar(self, id_: int, alteracoes: dict, aba: str='boletos', usuario: str='') -> dict`
  - `excluir(self, id_: int, aba: str='boletos', usuario: str='') -> None`
  - `historico_do_registro(self, id_: int, aba: str='boletos', desde: datetime \| None=None) -> list[dict]` — Eventos da aba Histórico de um boleto ou Pix, do mais recente para o mais antigo.
  - `salvar_centro(self, nome: str, descricao: str='', ativo: bool=True, nome_anterior: str \| None=None, usuario: str='') -> dict` — Cria ou altera um centro de custo. Renomear atualiza os boletos e Pix que já usavam o nome antigo.
  - `_salvar(self, wb, backup: bool=True) -> None`
  - `_backup_diario(self) -> None`

## `app/preferencias.py`

> Preferências do aplicativo de desktop (dados/app.json).

**Constantes:** `PADRAO` = `{'fechar_para_bandeja': True, 'minimizado_ao_iniciar': False, 'aviso_bandeja_mostrado': False}`

- `_caminho(caminho: Path \| None) -> Path`
- `ler(caminho: Path \| None=None) -> dict`
- `atualizar(alteracoes: dict, caminho: Path \| None=None) -> dict`

## `app/rede.py`

> Acesso pelo celular (rede local / Wi-Fi), ligado e desligado pela tela de Configurações.
> 
> O servidor principal continua ouvindo só em 127.0.0.1 (este computador). Ao liberar o acesso pela rede,
> um segundo servidor — no mesmo processo e servindo a mesma aplicação — passa a ouvir nos endereços da
> rede local (ex.: 192.168.0.10:8000). Desligar fecha esse acesso na hora, sem reiniciar o sistema.
> 
> * A senha é obrigatória e fica guardada como hash PBKDF2 (nunca em texto) em ``dados/rede.json``.
> * Trocar a senha desconecta os aparelhos que já tinham entrado.
> * Um vigia confere a cada minuto se o endereço do computador mudou (ex.: roteador reiniciou) e reabre o acesso.

**Constantes:** `ITERACOES_HASH` = `200000` · `TAMANHO_MINIMO_SENHA` = `6` · `INTERVALO_VIGIA` = `60` · `MAX_ACESSOS_REGISTRADOS` = `30`

- `_faixa_privada(ip: str) -> bool`
- `descobrir_enderecos() -> list[str]` — Endereços IPv4 privados deste computador; o da interface principal vem primeiro.
- `descrever_aparelho(agente: str \| None) -> str`
- **classe `GerenciadorRede`**
  - `__init__(self, app, caminho: Path, porta: int, *, descobrir: Callable[[], list[str]]=descobrir_enderecos, rede_via_env: bool=False, senha_externa: Callable[[], bool]=lambda: False)`
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `ativo(self) -> bool`
  - `senha_definida(self) -> bool`
  - `definir_senha(self, senha: str) -> None`
  - `verificar_senha(self, senha: str) -> bool`
  - `token_sessao(self) -> str`
  - `registrar_acesso(self, ip: str, agente: str \| None) -> None`
  - `rodando(self) -> bool`
  - `status(self) -> dict`
  - `ativar(self) -> dict`
  - `desativar(self) -> dict`
  - `iniciar_se_ativo(self) -> None`
  - `parar(self) -> None`
  - `iniciar_servidor(self) -> None`
  - `parar_servidor(self) -> None`
  - `_iniciar_vigia(self) -> None`

## `app/registro_log.py`

> Arquivo de log com limite de tamanho: ``dados/leitor.log`` nunca cresce sem parar.
> 
> Quando passa de 2 MB, o arquivo atual vira ``leitor.log.1`` (o ``.1`` vira ``.2``...) e um novo começa.
> São guardados no máximo 5 arquivos antigos (cerca de 12 MB no total). Também é possível limpar pela tela
> Saúde do sistema.

**Constantes:** `TAMANHO_MAXIMO` = `2 * 1024 * 1024` · `ARQUIVOS_ANTIGOS` = `5`

- `arquivos_de_log(caminho: Path) -> list[Path]`
- **classe `ArquivoRotativo`** — Objeto de arquivo (write/flush) usado como saída do programa quando não há console (pythonw).
  - `__init__(self, caminho: Path, tamanho_maximo: int=TAMANHO_MAXIMO, antigos: int=ARQUIVOS_ANTIGOS)`
  - `_girar_se_preciso(self) -> None`
  - `write(self, texto: str) -> int`
  - `flush(self) -> None`
  - `isatty(self) -> bool`
  - `limpar_antigos(self) -> int` — Apaga os arquivos antigos (.1 a .5) e esvazia o atual. Devolve quantos bytes foram liberados.
- `limpar(caminho: Path) -> int` — Limpa os logs mesmo quando o programa roda com console (sem ArquivoRotativo).

## `app/relatorio_geral.py`

> Relatório geral do mês: junta numa tela só o que foi pago (boletos, Pix e dinheiro), os juros e multas, o caixa,
> o diesel, as empresas e a previsão de saídas.
> 
> Cada parte só entra para quem tem a permissão daquela tela (``pode("gastos")``, ``pode("caixa")``…). O Excel traz o
> resumo, a lista de juros e multas pagos e a comparação dos últimos 12 meses.

**Constantes:** `MESES_HISTORICO` = `12` · `MOEDA` = `'"R$" #,##0.00'` · `COR` = `'0F3D3E'`

- `mes_vizinho(mes: date, passos: int) -> date`
- `_soma(itens: list[dict], campo: str) -> float`
- `_contas(boletos: list[dict], pix: list[dict], caixa: list[dict], mes: date, hoje: date) -> dict` — O que foi pago no mês (pela data de pagamento), o que vence no mês e os juros e multas pagos.
- `_historico(boletos: list[dict], pix: list[dict], caixa: list[dict], mes: date, hoje: date) -> list[dict]` — Os últimos 12 meses lado a lado (até o mês escolhido): quanto foi pago e quanto foi de juros.
- `_caixa(mes: date) -> dict`
- `_diesel(mes: date) -> dict`
- `_empresas(mes: date) -> dict`
- `_parte(nome: str, funcao, *args)` — Uma parte com problema (ex.: banco de outro módulo indisponível) não derruba o relatório inteiro.
- `montar(mes: date, pode: Callable[[str], bool], hoje: date \| None=None) -> dict`
- `_cabecalho(ws, linha: int, titulos: list[tuple[str, int]]) -> None`
- `_titulo(ws, texto: str, subtitulo: str) -> None`
- `gerar_xlsx(r: dict) -> bytes`

## `app/repositorio.py`

> Acesso aos registros (boletos ou Pix): planilha + fila de gravação (quando a planilha está aberta no Excel).
> 
> Todo o restante da aplicação (API, painel, análise, notificações) usa estas classes, então lançamentos que
> ainda aguardam gravação aparecem em todos os lugares como se já estivessem na planilha.

- **classe `RepositorioBoletos`** — Repositório de uma aba da planilha (``boletos`` por padrão; ``pix`` para pagamentos por Pix).
  - `__init__(self, planilha: PlanilhaBoletos, fila: FilaGravacao, aba: str='boletos')`
  - `garantir(self) -> None`
  - `listar(self) -> list[dict]`
  - `obter(self, id_: int) -> dict`
  - `buscar_por_codigo(self, codigo_barras: str) -> list[dict]`
  - `nomes_por_documento(self) -> dict[str, str]`
  - `status_gravacao(self) -> dict`
  - `_descarregar_fila(self) -> None` — Mantém a ordem: antes de gravar algo novo, tenta gravar o que já estava na fila.
  - `adicionar_lote(self, lista: list[dict], usuario: str='') -> tuple[list[dict], bool]` — Devolve (registros, ficou_pendente). Com a planilha bloqueada, os lançamentos vão para a fila.
  - `adicionar(self, dados: dict, usuario: str='') -> tuple[dict, bool]`
  - `atualizar(self, id_: int, dados: dict, usuario: str='') -> tuple[dict, bool]`
  - `excluir(self, id_: int, usuario: str='') -> None` — Exclusão exige a planilha livre (é irreversível); lançamentos pendentes são apenas cancelados.
- **classe `FonteLembretes`** — Boletos + Pix no formato usado pelas notificações de vencimento.
  - `__init__(self, boletos: RepositorioBoletos, pix: RepositorioBoletos, extras=None)` — ``extras()`` devolve outros lembretes já no formato dos alertas (ex.: cheques a depositar).
  - `listar(self) -> list[dict]`
  - `nomes_por_documento(self) -> dict[str, str]`

## `app/resumo_semanal.py`

> Resumos da semana enviados pelos canais das notificações (Telegram, e-mail e Windows).
> 
> * **Segunda-feira** — o que vence na semana: boletos e Pix a pagar, o que já está vencido, cheques a depositar,
>   fechamentos das empresas que caem na semana e o saldo do caixa.
> * **Sexta-feira** — o que a semana movimentou: quanto foi pago em boletos e Pix, as entradas e saídas do caixa,
>   o que foi recebido das empresas, onde mais se gastou e o que ficou para a semana que vem.
> 
> ``coletar(tipo, hoje)`` junta os números (lê os repositórios do ``contexto``) e ``mensagem(dados, url)`` escreve o
> texto em cada formato. As duas partes são separadas para o texto poder ser testado sem banco de dados.

**Constantes:** `TIPOS` = `('segunda', 'sexta')` · `DIA_DO_TIPO` = `{'segunda': 0, 'sexta': 4}` · `LIMITE_ITENS` = `12` · `DIAS_CURTOS` = `('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')`

- `_data(valor) -> date \| None`
- `_num(valor) -> float`
- `_pago(r: dict) -> float` — Quanto saiu de fato: o valor pago (com juros ou desconto) ou, sem ele, o valor do boleto.
- `_bloco(itens: list[dict], valor=None) -> dict`
- `semana(hoje: date) -> tuple[date, date]` — Segunda e domingo da semana de ``hoje``.
- `_a_pagar() -> list[dict]` — Boletos e Pix pendentes, num formato só (nome, vencimento, valor, tipo).
- `_pagos_entre(repositorio, inicio: date, fim: date, campo_nome: str) -> list[dict]`
- `_empresas(inicio: date, fim: date, hoje: date) -> dict` — Cheques a depositar, fechamentos da semana e o que as empresas ainda devem (nunca derruba o resumo).
- `_caixa(inicio: date, fim: date) -> dict`
- `coletar(tipo: str, hoje: date \| None=None) -> dict`
- `_dia(d: date) -> str`
- `_qtd(n: int, singular: str, plural: str) -> str`
- **classe `_Texto`** — Monta a mesma mensagem em texto puro, HTML do e-mail e HTML do Telegram.
  - `__init__(self, titulo: str)`
  - `secao(self, titulo: str, linhas: list[str], total: str='') -> None`
  - `telegram(self, rodape: str) -> str`
  - `texto(self, link: str) -> str`
  - `html(self, link: str) -> str`
- `_linhas_a_pagar(itens: list[dict]) -> list[str]`
- `_linha_cheque(c: dict, hoje: date) -> str`
- `_mensagem_segunda(d: dict, link: str) -> Mensagem`
- `_mensagem_sexta(d: dict, link: str) -> Mensagem`
- `mensagem(dados: dict, url_app: str) -> Mensagem`
- `nome_do_dia(tipo: str) -> str`

## `app/rotas/__init__.py`

> Rotas da API, separadas por assunto. ``app.main`` junta todas numa única aplicação.


## `app/rotas/administracao.py`

> Senha de administrador e importação de boletos de outros sistemas (área restrita).

- **classe `SenhaAdminEntrada`**
- **classe `EntrarAdminEntrada`**
- `_resposta_admin(request: Request, token: str \| None=None) -> JSONResponse`
- `_bloqueado(segundos: int) -> HTTPException`
- `get('/api/admin')` → `estado_admin(request: Request)`
- `post('/api/admin/senha')` → `definir_senha_admin(entrada: SenhaAdminEntrada, request: Request)`
- `post('/api/admin/entrar')` → `async entrar_admin(entrada: EntrarAdminEntrada, request: Request)`
- `post('/api/admin/sair')` → `sair_admin(request: Request)`
- **classe `ConfigImportacao`**
- **classe `ImportarEntrada`**
- `_montar_importacao(id_: str, cfg: ConfigImportacao)`
- `_resposta_importacao(id_: str, cfg: ConfigImportacao) -> dict`
- `get('/api/importacao/modelo.xlsx', dependencies=SOMENTE_ADMIN)` → `modelo_importacao()`
- `post('/api/importacao', status_code=201, dependencies=SOMENTE_ADMIN)` → `enviar_importacao(arquivo: UploadFile=File(...))` — Recebe a planilha exportada do outro sistema e devolve colunas sugeridas e a prévia dos boletos.
- `post('/api/importacao/{id_}/previa', dependencies=SOMENTE_ADMIN)` → `previa_importacao(id_: str, entrada: ConfigImportacao)`
- `post('/api/importacao/{id_}/importar', dependencies=SOMENTE_ADMIN)` → `importar_boletos(id_: str, entrada: ImportarEntrada, request: Request)`

## `app/rotas/backup.py`

> Backup total para fora do computador: situação, configuração (administrador), "fazer backup agora",
> pacote completo em .zip e conferência do backup.

- **classe `ConfigBackupEntrada`**
- `_publico(request: Request, status: dict) -> dict` — Aparelhos da rede veem a situação, mas não o caminho das pastas deste computador.
- `get('/api/backup')` → `situacao_backup(request: Request)`
- `put('/api/backup/config')` → `configurar_backup(entrada: ConfigBackupEntrada, request: Request)`
- `post('/api/backup/agora')` → `fazer_backup_agora(request: Request)`
- `post('/api/backup/pacote')` → `gerar_pacote_completo(request: Request)` — Atualiza o backup e guarda tudo (código, versões, bancos, arquivos e configurações) num único arquivo .zip.
- `post('/api/backup/verificar')` → `verificar_backup(request: Request)` — Confere o backup inteiro: os bancos abrem, nada falta e cada arquivo bate com a impressão digital guardada.
- `post('/api/backup/escolher-pasta')` → `escolher_pasta(request: Request)` — Abre a janela do Windows para escolher a pasta (só no computador onde o sistema está instalado).

## `app/rotas/boletos.py`

> Boletos lançados: lista, lançamento, edição, pagamento, exclusão, histórico e exportação.

**Constantes:** `SEM_PAGAMENTO` = `{'data_pagamento': None, 'valor_pago': None, 'juros_multa': None, 'desconto': None}`

- **classe `BoletoBase`**
- **classe `BoletoNovo`**
- **classe `LoteEntrada`**
- **classe `BoletoEdicao`**
- **classe `StatusEntrada`**
- `dados_da_linha(linha: str \| None, ignorar_validacao: bool) -> dict`
- `dados_do_status(entrada: StatusEntrada) -> dict`
- `situacoes(situacao: str) -> set[str] \| None`
- `pagina_de(registros: list[dict], pagina: int, por_pagina: int, serializar) -> dict`
- `filtrados(q: str, situacao: str, campo_data: str, de: date \| None, ate: date \| None, ordenar: str, direcao: str, centro: str='')`
- `get('/api/boletos')` → `listar_boletos(q: str='', situacao: str='', campo_data: CampoData='vencimento', de: date \| None=None, ate: date \| None=None, centro: str='', ordenar: CampoOrdem='vencimento', direcao: Literal['asc', 'desc']='asc', pagina: int=Query(1, ge=1), por_pagina: int=Query(25, ge=0, le=1000))`
- `get('/api/boletos/{id_}')` → `obter_boleto(id_: int)`
- `preparar_novo(entrada: BoletoNovo) -> dict` — Valida um lançamento e devolve os dados a gravar (lança HTTPException).
- `post('/api/boletos', status_code=201)` → `lancar_boleto(entrada: BoletoNovo, request: Request)`
- `post('/api/boletos/lote')` → `lancar_lote(entrada: LoteEntrada, request: Request)` — Lança vários boletos numa única gravação da planilha.
- `put('/api/boletos/{id_}')` → `editar_boleto(id_: int, entrada: BoletoEdicao, request: Request)`
- `patch('/api/boletos/{id_}/status')` → `alterar_status(id_: int, entrada: StatusEntrada, request: Request)`
- `delete('/api/boletos/{id_}', status_code=204)` → `excluir_boleto(id_: int, request: Request)`
- `get('/api/boletos/{id_}/arquivo')` → `arquivo_do_boleto(id_: int)`
- `get('/api/boletos/{id_}/historico')` → `historico_do_boleto(id_: int)` — Quem lançou, editou, pagou ou anexou comprovante neste boleto, e quando.
- `get('/api/exportar')` → `exportar(formato: Literal['csv', 'xlsx', 'planilha']='xlsx', q: str='', situacao: str='', campo_data: CampoData='vencimento', de: date \| None=None, ate: date \| None=None, centro: str='', ordenar: CampoOrdem='vencimento', direcao: Literal['asc', 'desc']='asc')`

## `app/rotas/busca_comprovantes.py`

> Central de comprovantes: busca com filtros em todas as partes do sistema e download em ZIP.

- `_buscar(request: Request, q: str, tipos: str, de: date \| None, ate: date \| None, valor: str, valor_min: float \| None, valor_max: float \| None, numero: str, centro: str, pessoa: str, comprovante: str, ordenar: str, direcao: str) -> list[dict]`
- `get('/api/comprovantes/busca')` → `buscar_comprovantes(request: Request, q: str=Query('', max_length=200), tipos: str=Query('', max_length=200), de: date \| None=None, ate: date \| None=None, valor: str=Query('', max_length=30), valor_min: float \| None=Query(None, ge=0), valor_max: float \| None=Query(None, ge=0), numero: str=Query('', max_length=80), centro: str=Query('', max_length=60), pessoa: str=Query('', max_length=60), comprovante: Situacao='com', ordenar: Ordem='data', direcao: Direcao='desc', pagina: int=Query(1, ge=1), por_pagina: int=Query(100, ge=10, le=500))`
- `get('/api/comprovantes/busca/zip')` → `baixar_comprovantes(request: Request, q: str=Query('', max_length=200), tipos: str=Query('', max_length=200), de: date \| None=None, ate: date \| None=None, valor: str=Query('', max_length=30), valor_min: float \| None=Query(None, ge=0), valor_max: float \| None=Query(None, ge=0), numero: str=Query('', max_length=80), centro: str=Query('', max_length=60), pessoa: str=Query('', max_length=60), ordenar: Ordem='data', direcao: Direcao='desc')`

## `app/rotas/caixa.py`

> API do caixa: lançamentos de entrada e saída, resumo por período, relatório em Excel e o bot do caixa.

- **classe `LancamentoEntrada`**
- **classe `ConfirmacaoCaixa`**
- **classe `ConfigBotCaixa`**
- `_falha(exc: Exception)`
- `get('')` → `resumo(periodo: Periodo='mes', data: date \| None=None)`
- `post('', status_code=201)` → `lancar(entrada: LancamentoEntrada, request: Request)`
- `put('/{id_}')` → `editar(id_: int, entrada: LancamentoEntrada, request: Request)`
- `post('/{id_}/cancelar')` → `cancelar(id_: int, request: Request)`
- `get('/{id_}/historico')` → `historico(id_: int)`
- `get('/relatorio/arquivo')` → `relatorio_excel(periodo: Periodo='mes', data: date \| None=None)` — Excel do período: resumo, onde mais se gastou e todos os lançamentos.
- `get('/bot/entrada')` → `conferencia(incluir_concluidos: bool=False)`
- `post('/bot/entrada/{id_}/lancar', status_code=201)` → `lancar_da_conferencia(id_: str, entrada: ConfirmacaoCaixa, request: Request)`
- `post('/bot/entrada/{id_}/descartar')` → `descartar_da_conferencia(id_: str)`
- `get('/bot/config')` → `obter_config_bot()`
- `post('/bot/config')` → `salvar_config_bot(entrada: ConfigBotCaixa)`
- `post('/bot/verificar')` → `verificar_bot()`

## `app/rotas/comprovantes.py`

> Comprovante de pagamento (PDF ou foto): anexar, ver, remover e registrar o pagamento a partir do comprovante.
> 
> Ao anexar, o sistema lê o comprovante: marca o lançamento como pago e guarda valor pago, juros/multa e desconto.
> Um comprovante enviado em Ler boletos (ou por e-mail/Telegram) é associado sozinho ao boleto ou Pix certo.

**Constantes:** `TIPOS` = `('boletos', 'pix')`

- **classe `RegistrarEntrada`**
- `_validar(dados: bytes) -> None`
- `_extraido_valido(extraido: dict) -> dict` — Aceita da tela só os campos do pagamento, já convertidos.
- `post('/api/comprovantes/registrar')` → `registrar_pagamento(entrada: RegistrarEntrada, request: Request)`
- `anexar(tipo: str, id_: int, arquivo: UploadFile, usuario: str) -> dict`

## `app/rotas/comum.py`

> Funções usadas por várias rotas: erros padronizados, restrições de acesso e downloads.

**Constantes:** `XLSX` = `'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'` · `SOMENTE_ADMIN` = `[Depends(exigir_admin)]`

- `erro(status: int, codigo: str, mensagem: str, **extra) -> HTTPException`
- `somente_local(request: Request, precisa_startfile: bool=True) -> None`
- `anexo(conteudo: bytes, tipo: str, nome: str) -> Response`
- `ip(request: Request) -> str`
- `autor(request: Request) -> str` — Quem está fazendo a alteração: o usuário que entrou, ou "Computador principal" (usado no Histórico).
- `concluir_caixa_de_entrada(arquivo_ids) -> None` — Boletos e Pix que chegaram por e-mail ou Telegram saem da caixa de entrada quando são lançados.
- `limpar_centro(dados: dict) -> None`
- `exigir_admin(request: Request) -> None` — Funções restritas: usuário com perfil de administrador, ou a sessão aberta com a senha de administrador.

## `app/rotas/diesel.py`

> API do diesel: máquinas, compras, abastecimentos, saldo, relatórios (tela, Excel e Telegram) e o bot do diesel.

**Constantes:** `MOEDA` = `'"R$" #,##0.00'` · `LITROS` = `'#,##0.0 "L"'`

- **classe `MaquinaEntrada`**
- **classe `CompraEntrada`**
- **classe `AbastecimentoEntrada`**
- **classe `EdicaoEntrada`** — Editar uma compra ou um abastecimento (cada aba aproveita só os seus campos).
- **classe `LinhaCanhoto`** — Uma linha do canhoto: um combustível para uma máquina.
- **classe `CanhotoEntrada`** — Canhoto lançado pela tela: o que vale para todas as linhas + as linhas.
- **classe `ConfirmacaoEntrada`**
- **classe `PrecosEntrada`**
- **classe `ConfigBotDiesel`**
- `_falha(exc: Exception)`
- `_arquivo(arquivo_id: str \| None) -> dict \| None`
- `get('')` → `resumo(periodo: Periodo='semana', data: date \| None=None)`
- `post('/arquivo', status_code=201)` → `async guardar_arquivo(arquivo: UploadFile=File(...))` — Guarda o comprovante ou o canhoto escolhido na tela; devolve o id para o lançamento.
- `post('/analisar')` → `async analisar_arquivo(arquivo: UploadFile=File(...))` — Lê o canhoto ou o comprovante enviado pela tela (sem passar pelo bot): combustíveis, litros, preços e totais.
- `post('/canhoto', status_code=201)` → `lancar_canhoto(entrada: CanhotoEntrada, request: Request)` — Canhoto com uma ou mais linhas (combustíveis diferentes, máquinas diferentes): um abastecimento por linha.
- `get('/precos')` → `obter_precos()`
- `post('/precos')` → `salvar_precos(entrada: PrecosEntrada, request: Request)`
- `post('/compras', status_code=201)` → `lancar_compra(entrada: CompraEntrada, request: Request)`
- `post('/abastecimentos', status_code=201)` → `lancar_abastecimento(entrada: AbastecimentoEntrada, request: Request)`
- `get('/maquinas')` → `listar_maquinas()`
- `post('/maquinas', status_code=201)` → `criar_maquina(entrada: MaquinaEntrada, request: Request)`
- `put('/maquinas/{id_}')` → `editar_maquina(id_: int, entrada: MaquinaEntrada, request: Request)`
- `put('/{aba}/{id_}')` → `editar(aba: Aba, id_: int, entrada: EdicaoEntrada, request: Request)`
- `post('/{aba}/{id_}/cancelar')` → `cancelar(aba: Aba, id_: int, request: Request)`
- `get('/{aba}/{id_}/historico')` → `historico(aba: Aba, id_: int)`
- `_alerta_valor() -> float`
- `get('/relatorio')` → `relatorio(periodo: Periodo='semana', data: date \| None=None)` — O relatório do período com tudo o que os três níveis (simples, detalhado e completo) mostram.
- `get('/relatorio/arquivo')` → `relatorio_excel(periodo: Periodo='semana', data: date \| None=None)` — Excel do período, sempre completo: resumo, máquinas, comparação, por dia, combustíveis, postos, pessoas, abastecimentos (com o consumo de cada trecho), compras e os pontos de atenção.
- `get('/relatorio/texto')` → `relatorio_texto(periodo: Periodo='semana', data: date \| None=None, nivel: Nivel='simples')`
- `post('/relatorio/enviar')` → `enviar_relatorio(periodo: Periodo='semana', data: date \| None=None, nivel: Nivel='simples')` — Manda agora o relatório (no nível escolhido) pelo bot do diesel para os responsáveis.
- `get('/bot/entrada')` → `conferencia(incluir_concluidos: bool=False)`
- `post('/bot/entrada/{id_}/lancar', status_code=201)` → `lancar_da_conferencia(id_: str, entrada: ConfirmacaoEntrada, request: Request)`
- `post('/bot/entrada/{id_}/descartar')` → `descartar_da_conferencia(id_: str)`
- `get('/bot/config')` → `obter_config_bot()`
- `post('/bot/config')` → `salvar_config_bot(entrada: ConfigBotDiesel)`
- `post('/bot/verificar')` → `verificar_bot()`

## `app/rotas/empresas.py`

> API do módulo Empresas: cadastro, notas fiscais, cheques, recebimentos, fechamento e bot de notas.

**Constantes:** `PDF` = `'application/pdf'`

- `_erro_regra(exc: Exception)`
- **classe `EmpresaEntrada`**
- **classe `ItemNota`**
- **classe `NotasNovas`**
- **classe `NotaEdicao`**
- **classe `ChequeEntrada`**
- **classe `RecebimentoEntrada`**
- **classe `ConfirmacaoEntrada`**
- **classe `ImportacaoFechamento`**
- **classe `ConfigEntrada`**
- `_arquivo_do_id(arquivo_id: str \| None) -> dict \| None`
- `get('/empresas')` → `listar_empresas(competencia: str \| None=Query(None, pattern='^\\d{4}-\\d{2}$'))`
- `post('/empresas', status_code=201)` → `criar_empresa(entrada: EmpresaEntrada, request: Request)`
- `put('/empresas/{id_}')` → `editar_empresa(id_: int, entrada: EmpresaEntrada, request: Request)`
- `delete('/empresas/{id_}', status_code=204)` → `excluir_empresa(id_: int, request: Request)`
- `get('/empresas/{id_}/fechamento')` → `obter_fechamento(id_: int, competencia: str \| None=Query(None, pattern='^\\d{4}-\\d{2}$'))`
- `get('/empresas/{id_}/fechamento/arquivo')` → `baixar_fechamento(id_: int, formato: Literal['xlsx', 'pdf']='xlsx', competencia: str \| None=Query(None, pattern='^\\d{4}-\\d{2}$'))`
- `post('/empresas/fechamento/enviar')` → `enviar_fechamentos(request: Request)` — Manda agora, pelo bot de notas, o fechamento de todas as empresas (o envio automático é no dia 20).
- `get('/notas')` → `listar_notas(empresa: str='', competencia: str='', status: str='', limite: int=Query(500, ge=1, le=2000))`
- `post('/notas', status_code=201)` → `lancar_notas(entrada: NotasNovas, request: Request)`
- `put('/notas/{id_}')` → `editar_nota(id_: int, entrada: NotaEdicao, request: Request)`
- `delete('/notas/{id_}', status_code=204)` → `excluir_nota(id_: int, request: Request)`
- `get('/cheques')` → `listar_cheques(empresa: str='', status: str='')`
- `post('/cheques', status_code=201)` → `lancar_cheque(entrada: ChequeEntrada, request: Request)`
- `put('/cheques/{id_}')` → `editar_cheque(id_: int, entrada: ChequeEntrada, request: Request)`
- `delete('/cheques/{id_}', status_code=204)` → `excluir_cheque(id_: int, request: Request)`
- `get('/recebimentos')` → `listar_recebimentos(empresa: str='', limite: int=Query(300, ge=1, le=2000))`
- `post('/recebimentos', status_code=201)` → `registrar_recebimento(entrada: RecebimentoEntrada, request: Request)`
- `post('/recebimentos/{id_}/cancelar')` → `cancelar_recebimento(id_: int, request: Request)`
- `get('/empresas/entrada')` → `listar_entrada(incluir_concluidos: bool=False)`
- `post('/empresas/entrada/verificar')` → `verificar_entrada()`
- `post('/empresas/entrada/{id_}/confirmar')` → `confirmar_entrada(id_: str, entrada: ConfirmacaoEntrada, request: Request)`
- `post('/empresas/entrada/{id_}/descartar')` → `descartar_entrada(id_: str)`
- `post('/empresas/analisar')` → `async analisar_arquivo(arquivo: UploadFile=File(...))` — Lê uma nota fiscal, um cheque, um comprovante ou o print de um fechamento enviado pela tela.
- `post('/empresas/arquivo', status_code=201)` → `async guardar_arquivo(arquivo: UploadFile=File(...))` — Guarda um comprovante escolhido na tela (ex.: o depósito de um cheque) sem lê-lo; devolve o id para o lançamento.
- `post('/empresas/importar-fechamento', status_code=201)` → `importar_fechamento(entrada: ImportacaoFechamento, request: Request)` — Parte 5: traz para o sistema o fechamento que já estava em andamento (lido de um print ou digitado).
- `get('/empresas/config')` → `obter_config()`
- `post('/empresas/config')` → `salvar_config(entrada: ConfigEntrada)`
- `get('/empresas/config/chats')` → `chats_do_bot()` — Pessoas e grupos que falaram com o bot de notas (para cadastrar sem digitar o chat ID).

## `app/rotas/entrada.py`

> Caixa de entrada: boletos recebidos por e-mail e Telegram, aguardando conferência na tela Ler boletos.

- **classe `ConfigEntrada`**
- **classe `VerificarEntrada`**
- **classe `AssociarEntrada`**
- **classe `DescartarEntrada`**
- `_caixa()`
- `get('/api/entrada')` → `listar_entrada(concluidos: bool=False)`
- `get('/api/entrada/{id_}')` → `obter_item(id_: str)`
- `post('/api/entrada/descartar')` → `descartar_itens(entrada: DescartarEntrada)`
- `put('/api/entrada/config', dependencies=SOMENTE_ADMIN)` → `configurar_entrada(entrada: ConfigEntrada)`
- `post('/api/entrada/verificar')` → `verificar_agora(entrada: VerificarEntrada, request: Request)`
- `post('/api/entrada/{id_}/registrar')` → `registrar_comprovante(id_: str, entrada: AssociarEntrada, request: Request)` — Comprovante que ficou em dúvida: registra o pagamento no lançamento escolhido.

## `app/rotas/gastos.py`

> Centros de custo e análise de gastos (boletos + Pix).

**Constantes:** `ROTULO_CAMPO_DATA` = `{'vencimento': 'vencimento', 'data_pagamento': 'pagamento', 'data_lancamento': 'lançamento'}`

- **classe `CentroEntrada`**
- **classe `CentroEdicao`**
- `get('/api/centros')` → `listar_centros()`
- `post('/api/centros', status_code=201)` → `criar_centro(entrada: CentroEntrada, request: Request)`
- `put('/api/centros')` → `editar_centro(entrada: CentroEdicao, request: Request)`
- `get('/api/gastos')` → `analise_gastos(de: date \| None=None, ate: date \| None=None, campo_data: CampoDataGastos='vencimento', situacao: Literal['todos', 'pagos', 'pendentes']='todos', tipo: Literal['todos', 'boleto', 'pix', 'dinheiro']='todos')`
- `get('/api/gastos/exportar')` → `exportar_gastos(de: date \| None=None, ate: date \| None=None, campo_data: CampoDataGastos='vencimento', situacao: Literal['todos', 'pagos', 'pendentes']='todos', tipo: Literal['todos', 'boleto', 'pix', 'dinheiro']='todos')`
- `_fechamento(mes: str \| None, base: str) -> dict`
- `get('/api/relatorios/fechamento')` → `fechamento_do_mes(mes: str \| None=None, base: BaseFechamento='vencimento')`
- `get('/api/relatorios/fechamento/arquivo')` → `baixar_fechamento(mes: str \| None=None, base: BaseFechamento='vencimento', formato: Literal['xlsx', 'pdf', 'zip']='pdf')`

## `app/rotas/leitura.py`

> Leitura de arquivos (PDF e fotos), da linha digitável e análise com IA.

- **classe `LinhaEntrada`**
- **classe `PedidoIA`**
- `ler_upload(arquivo: UploadFile) -> bytes`
- `post('/api/leituras')` → `criar_leitura(arquivo: UploadFile=File(...))`
- `post('/api/leituras/tarefas', status_code=202)` → `criar_tarefa_leitura(arquivo: UploadFile=File(...))` — Leitura em segundo plano: responde na hora com o id da tarefa para acompanhar o progresso.
- `get('/api/leituras/tarefas/{tarefa_id}')` → `acompanhar_tarefa(tarefa_id: str)`
- `post('/api/leituras/linha')` → `analisar_linha(entrada: LinhaEntrada)`
- `post('/api/leituras/{arquivo_id}/ia')` → `analisar_com_ia(arquivo_id: str, pedido: PedidoIA)`
- `get('/api/arquivos/{arquivo_id}')` → `visualizar_arquivo(arquivo_id: str)`

## `app/rotas/notificacoes.py`

> Notificações de vencimento: sininho, lembretes, canais (Windows, Telegram, e-mail) e testes.

- **classe `RegraEntrada`**
- **classe `ResumoEntrada`**
- **classe `ConfigNotificacoesEntrada`**
- **classe `TesteCanalEntrada`**
- **classe `DetectarTelegramEntrada`**
- **classe `ChavesAvisoEntrada`**
- **classe `ChaveAvisoEntrada`**
- **classe `TesteTelegramEntrada`**
- `get('/api/notificacoes')` → `obter_notificacoes()`
- `post('/api/notificacoes/vistos')` → `marcar_avisos_vistos(entrada: ChavesAvisoEntrada)` — Avisos do sininho que já foram vistos: saem da contagem até a situação do boleto mudar.
- `post('/api/notificacoes/dispensar')` → `dispensar_aviso(entrada: ChaveAvisoEntrada)`
- `post('/api/notificacoes/restaurar')` → `restaurar_avisos()`
- `put('/api/notificacoes/config')` → `salvar_config_notificacoes(entrada: ConfigNotificacoesEntrada)`
- `post('/api/notificacoes/testar')` → `testar_notificacao(entrada: TesteCanalEntrada)`
- `post('/api/notificacoes/enviar-agora')` → `enviar_notificacoes_agora()`
- `get('/api/notificacoes/resumo/{tipo}')` → `previa_resumo(tipo: Literal['segunda', 'sexta'])` — Como o resumo da semana ficaria se fosse enviado agora.
- `post('/api/notificacoes/resumo/{tipo}/enviar')` → `enviar_resumo(tipo: Literal['segunda', 'sexta'])`
- `post('/api/notificacoes/telegram/detectar')` → `detectar_chat_telegram(entrada: DetectarTelegramEntrada)`
- `post('/api/notificacoes/telegram/testar')` → `testar_destinatario_telegram(entrada: TesteTelegramEntrada)` — Envia uma mensagem de teste para uma única pessoa ou grupo.

## `app/rotas/pix.py`

> Pagamentos Pix: lançamento por chave, Copia e Cola ou QR code, pagamento, QR code e exportação.

- **classe `PixBase`**
- **classe `PixNovo`**
- **classe `PixCodigoEntrada`**
- `preparar_pix(entrada: PixBase, existente: dict \| None=None) -> dict` — Valida chave, Copia e Cola e valor de um Pix (novo ou editado) e devolve os dados a gravar.
- `filtrados_pix(q: str, situacao: str, campo_data: str, de: date \| None, ate: date \| None, ordenar: str, direcao: str, centro: str='')`
- `get('/api/pix')` → `listar_pix(q: str='', situacao: str='', campo_data: CampoData='vencimento', de: date \| None=None, ate: date \| None=None, centro: str='', ordenar: CampoOrdemPix='vencimento', direcao: Literal['asc', 'desc']='asc', pagina: int=Query(1, ge=1), por_pagina: int=Query(25, ge=0, le=1000))`
- `get('/api/pix/exportar')` → `exportar_pix(formato: Literal['csv', 'xlsx']='xlsx', q: str='', situacao: str='', campo_data: CampoData='vencimento', de: date \| None=None, ate: date \| None=None, centro: str='', ordenar: CampoOrdemPix='vencimento', direcao: Literal['asc', 'desc']='asc')`
- `post('/api/pix/ler-codigo')` → `ler_codigo_pix(entrada: PixCodigoEntrada)`
- `post('/api/pix/ler-arquivo')` → `ler_arquivo_pix(arquivo: UploadFile=File(...))` — Procura QR codes Pix numa foto, print ou PDF.
- `post('/api/pix', status_code=201)` → `lancar_pix(entrada: PixNovo, request: Request)`
- `get('/api/pix/{id_}')` → `obter_pix(id_: int)`
- `put('/api/pix/{id_}')` → `editar_pix(id_: int, entrada: PixBase, request: Request)`
- `patch('/api/pix/{id_}/status')` → `alterar_status_pix(id_: int, entrada: StatusEntrada, request: Request)`
- `delete('/api/pix/{id_}', status_code=204)` → `excluir_pix(id_: int, request: Request)`
- `get('/api/pix/{id_}/arquivo')` → `arquivo_do_pix(id_: int)`
- `get('/api/pix/{id_}/historico')` → `historico_do_pix(id_: int)`
- `_copia_e_cola_do_registro(registro: dict) -> tuple[str, bool]`
- `get('/api/pix/{id_}/copia-e-cola')` → `copia_e_cola_pix(id_: int)`
- `get('/api/pix/{id_}/qrcode.svg')` → `qrcode_pix(id_: int)`

## `app/rotas/relatorios.py`

> Central de relatórios: o relatório geral do mês (cada parte conforme as permissões de quem entrou) e o Excel.

- `_montar(request: Request, mes: str \| None) -> dict`
- `get('/api/relatorio-geral')` → `relatorio_do_mes(request: Request, mes: str \| None=None)`
- `get('/api/relatorio-geral/arquivo')` → `baixar_relatorio_do_mes(request: Request, mes: str \| None=None)`

## `app/rotas/saude.py`

> Saúde do sistema: diagnóstico e ações rápidas (atualizar a planilha agora, limpar logs).

- `get('/api/saude')` → `diagnostico()`
- `post('/api/saude/atualizar-planilha')` → `atualizar_planilha()`
- `post('/api/saude/limpar-logs')` → `limpar_logs(request: Request)`

## `app/rotas/sistema.py`

> Situação do sistema, acesso pela rede, gravação pendente, planilha, painel e aplicativo de desktop.

**Constantes:** `RE_ROTA` = `re.compile('^[a-z]+(\\?[A-Za-z0-9_=&%.,\\-]*)?$')`

- **classe `SenhaEntrada`**
- `get('/api/status')` → `obter_status()`
- `get('/api/versao')` → `obter_versao(request: Request)` — Versão em uso, histórico do que mudou em cada versão e se há alterações ainda não guardadas.
- `get('/api/acesso/estado')` → `estado_acesso(request: Request)`
- `post('/api/acesso')` → `async entrar(entrada: SenhaEntrada, request: Request)`
- `post('/api/acesso/sair')` → `sair()`
- `get('/api/gravacao')` → `status_gravacao()`
- `post('/api/gravacao/tentar')` → `tentar_gravacao()`
- `delete('/api/gravacao/{op_id}', status_code=204)` → `cancelar_gravacao(op_id: str)`
- `get('/api/painel')` → `obter_painel()`
- `get('/api/previsao')` → `previsao_de_saidas(semanas: int=Query(8, ge=1, le=26))` — Quanto vai sair nas próximas semanas (boletos e Pix pendentes) e o que já está em atraso.
- `post('/api/planilha/abrir')` → `abrir_planilha(request: Request)`
- `post('/api/planilha/abrir-pasta')` → `abrir_pasta(request: Request)`
- **classe `InicializacaoEntrada`**
- **classe `PreferenciasEntrada`**
- **classe `MostrarEntrada`**
- `_rota_valida(rota: str \| None) -> str \| None`
- `get('/api/sistema/inicializacao')` → `obter_inicializacao()`
- `post('/api/sistema/inicializacao')` → `alterar_inicializacao(entrada: InicializacaoEntrada, request: Request)`
- `get('/api/app')` → `status_aplicativo(request: Request)`
- `put('/api/app/preferencias')` → `salvar_preferencias(entrada: PreferenciasEntrada, request: Request)`
- `post('/api/app/atalhos')` → `criar_atalhos(request: Request)`
- `post('/api/app/mostrar')` → `mostrar_aplicativo(request: Request, entrada: MostrarEntrada \| None=None)`
- `get('/api/app/abrir')` → `abrir_pelo_link(request: Request, rota: str='')` — Destino dos cliques nas notificações: traz a janela do aplicativo para a frente.
- `post('/api/app/sair')` → `sair_do_aplicativo(request: Request)`
- **classe `SenhaRedeEntrada`**
- **classe `AtivarRedeEntrada`**
- `get('/api/rede')` → `status_rede(request: Request)`
- `post('/api/rede/senha')` → `definir_senha_rede(entrada: SenhaRedeEntrada, request: Request)`
- `post('/api/rede/ativar')` → `ativar_rede(entrada: AtivarRedeEntrada, request: Request)`
- `get('/api/rede/qrcode.svg')` → `qrcode_rede(url: str \| None=None)`

## `app/rotas/usuarios.py`

> Usuários do escritório: entrar/sair, trocar a própria senha e cadastro (restrito ao administrador).

- **classe `EntrarEntrada`**
- **classe `TrocarSenhaEntrada`**
- **classe `UsuarioNovo`**
- **classe `UsuarioEdicao`**
- **classe `ConfigUsuariosEntrada`**
- `_falha(exc: usuarios.ErroUsuario)`
- `post('/api/usuarios/entrar')` → `async entrar(entrada: EntrarEntrada, request: Request)`
- `post('/api/usuarios/sair')` → `sair(request: Request)`
- `get('/api/usuarios/eu')` → `quem_sou(request: Request)`
- `post('/api/usuarios/minha-senha')` → `trocar_minha_senha(entrada: TrocarSenhaEntrada, request: Request)`
- `_lista() -> dict`
- `get('/api/usuarios', dependencies=SOMENTE_ADMIN)` → `listar_usuarios()`
- `post('/api/usuarios', status_code=201, dependencies=SOMENTE_ADMIN)` → `criar_usuario(entrada: UsuarioNovo)`
- `put('/api/usuarios/config', dependencies=SOMENTE_ADMIN)` → `configurar_usuarios(entrada: ConfigUsuariosEntrada)`
- `put('/api/usuarios/{id_}', dependencies=SOMENTE_ADMIN)` → `alterar_usuario(id_: str, entrada: UsuarioEdicao)`
- `delete('/api/usuarios/{id_}', status_code=204, dependencies=SOMENTE_ADMIN)` → `excluir_usuario(id_: str)`

## `app/saude.py`

> Saúde do sistema: um diagnóstico de tudo o que roda sozinho (e do que precisa de atenção).
> 
> Cada item tem ``situacao`` — ``ok``, ``aviso``, ``erro`` ou ``desligado`` — e um resumo em linguagem simples.

**Constantes:** `INICIADO_EM` = `datetime.now()` · `ORDEM` = `{'erro': 0, 'aviso': 1, 'ok': 2, 'desligado': 3}` · `NOMES_CANAIS` = `{'windows': 'Windows', 'telegram': 'Telegram', 'email': 'e-mail'}`

- `_vivo(objeto) -> bool`
- `_tamanho(caminho: Path) -> int`
- `_item(chave: str, titulo: str, situacao: str, resumo: str, **detalhes) -> dict`
- `_data_hora(texto) -> str`
- `_banco() -> dict`
- `_empresas() -> dict` — Banco das empresas (notas, cheques e recebimentos) e o bot de notas fiscais.
- `_caixa() -> dict` — Bot do caixa: cupons de gastos em dinheiro.
- `_diesel() -> dict` — Bot do diesel: canhotos dos abastecimentos e comprovantes das compras.
- `_notificacoes() -> dict`
- `_backup() -> dict`
- `_entrada() -> dict`
- `_fila() -> dict`
- `_leitura() -> dict`
- `_disco() -> dict`
- `_rede() -> dict`
- `diagnostico() -> dict`

## `app/servico_comprovante.py`

> Registro de pagamentos a partir de comprovantes (tela Ler boletos, anexo manual, e-mail e bot do Telegram).

**Constantes:** `ABAS` = `{'boletos': 'repositorio', 'pix': 'repositorio_pix'}`

- `repositorio(aba: str)`
- `analisar_texto(texto: str, codigos: list[str] \| None=None, forcar: bool=False) -> dict \| None` — Se o texto for de um comprovante, devolve o que foi lido, os lançamentos possíveis e o escolhido (se claro).
- `analisar_resultado(resultado: dict) -> dict \| None`
- `registrar(aba: str, id_: int, extraido: dict, usuario: str, arquivo_id: str \| None=None) -> dict` — Marca o lançamento como pago com os valores do comprovante e anexa o arquivo.
- `desfazer(aba: str, id_: int, usuario: str) -> dict`
- `valores_do_arquivo(dados: bytes) -> dict \| None` — Lê um comprovante anexado à mão (o lançamento já é conhecido): só extrai valores e data.
- `serializar(aba: str, registro: dict) -> dict`
- `resumo_pagamento(aba: str, registro: dict) -> dict` — Para mensagens (Telegram) e para a tela: o que foi pago, juros, desconto e atraso.

## `app/servico_leitura.py`

> Leitura de um arquivo enviado (boletos, ou Pix quando não há boleto), usada pela tela e pela caixa de entrada.

- `pix_existente(pix: dict) -> dict \| None` — Pix já lançado com o mesmo Copia e Cola (ou mesma chave + identificador TXID).
- `com_duplicado(pix: dict) -> dict`
- `processar_leitura(dados: bytes, nome: str, ao_progresso=None) -> dict` — Lê o arquivo, guarda o original e (se configurado) completa com IA. Lança ErroLeitura.

## `app/servicos.py`

> Regras de consulta sobre os registros da planilha: filtros, ordenação, painel, análise de gastos e exportação.

**Constantes:** `MESES` = `['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']` · `SITUACOES` = `('vencido', 'vence_hoje', 'a_vencer', 'pendente', 'pago', 'cancelado')` · `SEM_CENTRO` = `'Sem centro de custo'` · `OUTROS_CENTROS` = `'Outros centros'` · `CAMPOS_BUSCA_BOLETOS` = `('beneficiario', 'numero_documento', 'documento_beneficiario', 'observacoes', 'emissor', 'linha_digitavel', 'centro_custo')` · `CAMPOS_DIGITOS_BOLETOS` = `('codigo_barras', 'linha_digitavel')` · `CAMPOS_BUSCA_PIX` = `('recebedor', 'chave', 'descricao', 'observacoes', 'centro_custo', 'txid')` · `CAMPOS_DIGITOS_PIX` = `('chave',)` · `_ROTULO_SITUACAO` = `{'vencido': 'Vencido', 'vence_hoje': 'Vence hoje', 'a_vencer': 'A vencer', 'pendente': 'Pendente', 'pago': 'Pago', 'cancelado': 'Cancelado'}`

- `situacao(registro: dict, hoje: date) -> str`
- `serializar(registro: dict, hoje: date \| None=None) -> dict`
- `serializar_pix(registro: dict, hoje: date \| None=None) -> dict`
- `_valor(registro: dict) -> float`
- `_juros(registro: dict) -> float`
- `filtrar(registros: list[dict], *, q: str='', situacoes: set[str] \| None=None, campo_data: str='vencimento', de: date \| None=None, ate: date \| None=None, hoje: date \| None=None, centro: str='', campos_busca: tuple[str, ...]=CAMPOS_BUSCA_BOLETOS, campos_digitos: tuple[str, ...]=CAMPOS_DIGITOS_BOLETOS) -> list[dict]`
- `ordenar(registros: list[dict], campo: str='vencimento', direcao: str='asc') -> list[dict]`
- `resumir(registros: list[dict], hoje: date \| None=None) -> dict`
- `_inicio_mes(d: date, deslocamento: int=0) -> date`
- `painel(registros: list[dict], hoje: date \| None=None, pix: list[dict] \| None=None) -> dict` — Indicadores, gráfico e listas do Painel, somando boletos e Pix (os Pix vêm marcados com ``tipo_pagamento``).
- `analise_gastos(boletos: list[dict], pix: list[dict], caixa: list[dict] \| None=None, *, de: date \| None=None, ate: date \| None=None, campo_data: str='vencimento', situacao_filtro: str='todos', tipo: str='todos', hoje: date \| None=None) -> dict` — Quanto foi gasto em cada centro de custo (boletos + Pix + dinheiro do caixa), por mês e por beneficiário.
- `_valor_exportacao(chave: str, valor)`
- `gerar_csv(registros: list[dict], hoje: date \| None=None, colunas=COLUNAS) -> bytes`
- `_cabecalho(ws, titulos: list[str], larguras: list[int]) -> None`
- `gerar_xlsx(registros: list[dict], hoje: date \| None=None, colunas=COLUNAS, titulo_aba: str='Boletos') -> bytes`
- `gerar_xlsx_analise(analise: dict, descricao_filtros: str) -> bytes`
- `previsao_saidas(boletos: list[dict], pix: list[dict], hoje: date \| None=None, semanas: int=8) -> dict` — Quanto vai sair nas próximas semanas (boletos e Pix pendentes), com o que já está em atraso à parte.

## `app/tarefas.py`

> Leituras em segundo plano com progresso.
> 
> PDFs escaneados podem levar dezenas de segundos. Em vez de segurar a requisição HTTP, a leitura
> vira uma tarefa: o navegador recebe um id na hora e acompanha a página e a etapa em andamento.

**Constantes:** `DESCRICOES` = `{'na_fila': 'Na fila', 'iniciando': 'Preparando o arquivo', 'codigo_barras': 'Lendo o código de barras', 'ocr': 'Reconhecendo o texto (OCR)', 'concluindo': '…` · `_PESO_ETAPA` = `{'iniciando': 0.0, 'codigo_barras': 0.15, 'ocr': 0.35, 'concluindo': 1.0}`

- **classe `ErroTarefa`**
  - `__init__(self, codigo: str, mensagem: str)`
- **classe `Tarefa`**
  - `percentual(self) -> int`
  - `para_dict(self) -> dict`
- **classe `GerenciadorTarefas`**
  - `__init__(self, max_paralelo: int=2, validade_segundos: int=3600)`
  - `criar(self, nome: str, funcao: Callable[[Callable[..., None]], dict]) -> Tarefa` — ``funcao(ao_progresso)`` executa a leitura e devolve o resultado.
  - `obter(self, tarefa_id: str) -> Tarefa \| None`
  - `_limpar(self) -> None`
  - `encerrar(self) -> None`

## `app/usuarios.py`

> Usuários do escritório: cada pessoa entra com o próprio login, e o sistema registra quem fez cada alteração.
> 
> * cada pessoa tem um **perfil**: *administrador* (pode tudo, inclusive cadastrar usuários) ou *comum*, com as
>   **permissões** que o administrador marcar (lançar, dar baixa, editar, gastos, empresas, avisos, configurações);
> * os usuários são cadastrados pelo administrador (entrando com o próprio usuário, ou pela senha de administrador);
> * dá para pedir o login **toda vez que o aplicativo abre**: as sessões deste computador são encerradas ao iniciar;
> * senhas guardadas com PBKDF2 em ``dados/usuarios.json`` — nunca em texto;
> * ao entrar, o aparelho recebe um cookie válido por 30 dias; no arquivo fica só o hash do token;
> * desativar um usuário, trocar a senha dele ou excluí-lo desconecta os aparelhos dessa pessoa;
> * após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos.
> 
> Enquanto não houver usuários cadastrados, o sistema funciona como antes (senha única de acesso pela rede).

**Constantes:** `COOKIE` = `'leitor_usuario'` · `VALIDADE_SESSAO` = `30 * 24 * 3600` · `ITERACOES` = `200000` · `TAMANHO_MINIMO_SENHA` = `6` · `MAX_TENTATIVAS` = `5` · `BLOQUEIO_SEGUNDOS` = `300` · `LIMITE_USUARIOS` = `100` · `RE_LOGIN` = `re.compile('^[a-z0-9._-]{2,40}$')` · `PERFIS` = `('administrador', 'comum')` · `PERMISSOES` = `{'lancar': 'Lançar boletos e Pix (ler arquivos e cadastrar)', 'pagar': 'Dar baixa: marcar como pago e anexar comprovante', 'editar': 'Editar e excluir lançam…` · `PERMISSOES_PADRAO` = `('lancar', 'pagar')`

- `normalizar_permissoes(valores) -> list[str]`
- **classe `ErroUsuario`**
- `normalizar_login(texto: str) -> str`
- `_hash_senha(senha: str, sal: bytes) -> str`
- `_hash_token(token: str) -> str`
- `_agora() -> str`
- **classe `GerenciadorUsuarios`**
  - `__init__(self, caminho: Path)`
  - `_ler(self) -> dict`
  - `_gravar(self) -> None`
  - `publico(usuario: dict) -> dict`
  - `pode(usuario: dict \| None, permissao: str) -> bool` — O usuário tem essa permissão? (administrador pode tudo; sem usuário, quem manda é o acesso do aparelho).
  - `listar(self) -> list[dict]`
  - `tem_administrador(self) -> bool`
  - `em_uso(self) -> bool` — Há pelo menos um usuário ativo: o sistema passa a pedir login por pessoa.
  - `exigir_login_no_computador(self) -> bool`
  - `pedir_login_ao_abrir(self) -> bool`
  - `_obter(self, id_: str) -> dict`
  - `_validar_senha(senha: str) -> None`
  - `_definir_senha(usuario: dict, senha: str) -> None`
  - `_encerrar_sessoes(self, id_: str) -> None`
  - `_ultimo_administrador(self, usuario: dict) -> bool` — Este é o único administrador ativo? (não dá para ficar sem ninguém que possa gerenciar o sistema)
  - `criar(self, nome: str, login: str, senha: str, perfil: str='comum', permissoes=None) -> dict`
  - `alterar(self, id_: str, *, nome: str \| None=None, ativo: bool \| None=None, senha: str \| None=None, perfil: str \| None=None, permissoes=None) -> dict`
  - `excluir(self, id_: str) -> None`
  - `definir_exigir_login_no_computador(self, ativo: bool) -> None`
  - `definir_pedir_login_ao_abrir(self, ativo: bool) -> None` — Ligado: ao abrir o aplicativo, quem usa este computador entra de novo com usuário e senha.
  - `encerrar_sessoes_do_computador(self) -> int` — Chamado quando o aplicativo abre: as sessões abertas neste computador são encerradas.
  - `segundos_bloqueado(self, ip: str) -> int`
  - `entrar(self, login: str, senha: str, ip: str, aparelho: str='', local: bool=False) -> tuple[str \| None, dict \| None, int]` — Devolve (token, usuário, segundos de bloqueio).
  - `usuario_da_sessao(self, token: str \| None) -> dict \| None`
  - `sair(self, token: str \| None) -> None`
  - `trocar_propria_senha(self, token: str \| None, atual: str, nova: str) -> None`

## `app/versao.py`

> Controle de versão do Fin Pro: qual versão está rodando, o histórico do que mudou e o repositório (git).
> 
> * O número da versão fica em ``app/__init__.py`` (``__version__``) e o histórico, em ``VERSOES.md`` — os dois são
>   atualizados pela ferramenta ``ferramentas/versao.py`` cada vez que uma versão nova é guardada.
> * Cada versão guardada é um *commit* com uma etiqueta (``v1.9.0``) no repositório git da pasta do sistema. Só o
>   código entra no repositório: os dados (pasta ``dados``) e as senhas (``.env``) ficam de fora — quem cuida deles é o
>   backup, que também leva o código e o histórico de versões (``gerar_bundle``).
> * Sem o git instalado o sistema funciona igual; só não mostra as informações do repositório.

**Constantes:** `ARQUIVO_HISTORICO` = `'VERSOES.md'` · `ARQUIVO_VERSAO` = `Path('app') / '__init__.py'` · `RE_VERSAO` = `re.compile('^(\\d+)\\.(\\d+)\\.(\\d+)$')` · `RE_TITULO` = `re.compile('^## v(\\d+\\.\\d+\\.\\d+) — (\\d{2})/(\\d{2})/(\\d{4}) — (.+?)\\s*$')` · `RE_LINHA_VERSAO` = `re.compile('^__version__\\s*=\\s*"[^"]*"\\s*$', re.M)` · `TIPOS` = `{'correcao': 2, 'melhoria': 1, 'grande': 0}` · `VALIDADE_CACHE` = `30` · `TEMPO_GIT` = `20`

- **classe `ErroVersao`** — Erro com mensagem pronta para a pessoa ler.
- `versao_atual(raiz: Path \| None=None) -> str` — O número gravado em ``app/__init__.py`` (lido do arquivo, para valer logo depois de uma versão nova).
- `proxima(versao: str, tipo: str='melhoria') -> str` — ``correcao``: 1.9.0 → 1.9.1 · ``melhoria``: 1.9.1 → 1.10.0 · ``grande``: 1.10.0 → 2.0.0.
- `historico(raiz: Path \| None=None) -> list[dict]` — As versões de ``VERSOES.md``, da mais nova para a mais antiga: versão, data, título e o que mudou.
- `registrar(versao: str, titulo: str, itens: list[str] \| None=None, quando: date \| None=None, raiz: Path \| None=None) -> None` — Acrescenta a versão no topo do histórico (``VERSOES.md``).
- `definir_versao(versao: str, raiz: Path \| None=None) -> None` — Grava o número novo em ``app/__init__.py``.
- `git(*argumentos: str, raiz: Path \| None=None, tempo: int=TEMPO_GIT, checar: bool=False) -> str \| None` — Roda o git na pasta do sistema e devolve a saída — ou ``None`` se não houver git, repositório ou der erro.
- `tem_repositorio(raiz: Path \| None=None) -> bool`
- `alteracoes_pendentes(raiz: Path \| None=None) -> list[str]` — Arquivos do código alterados, novos ou apagados desde a última versão guardada.
- `etiquetas(raiz: Path \| None=None) -> list[dict]` — As versões guardadas no repositório (etiquetas ``vX.Y.Z``), da mais nova para a mais antiga.
- `repositorio(raiz: Path \| None=None) -> dict` — Como está o repositório: se existe, o ponto atual e quantos arquivos mudaram desde a última versão.
- `situacao(usar_cache: bool=True) -> dict` — O que a tela mostra: versão em uso, histórico e o estado do repositório.
- `resumo() -> dict` — Versão e ponto do repositório, para carimbar o backup.
- `gerar_bundle(destino: Path, raiz: Path \| None=None) -> bool` — Guarda **todo** o histórico de versões num único arquivo (``git bundle``), que o backup leva junto.
- `verificar_bundle(arquivo: Path, raiz: Path \| None=None) -> bool` — O arquivo do histórico está inteiro? (``git bundle verify``)
- `carimbo(quando: datetime \| None=None) -> str` — Texto curto para ``VERSAO.txt`` do backup.

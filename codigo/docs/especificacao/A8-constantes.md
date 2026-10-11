# Anexo A8 — Constantes, listas de palavras e expressões regulares (por extenso)

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Todas as constantes de nível de módulo (nomes em MAIÚSCULAS) do back-end, **sem cortes**: listas de palavras-sinal, expressões regulares, limites, pesos e tabelas. São os "números mágicos" que calibram o sistema — copie-os exatamente na nova versão.

## `app/acesso.py`

```python
COOKIE = 'leitor_acesso'

ESCRITA = {'POST', 'PUT', 'PATCH', 'DELETE'}

SEM_PERMISSAO = {'/api/notificacoes/vistos', '/api/notificacoes/dispensar', '/api/notificacoes/restaurar', '/api/usuarios/minha-senha', '/api/usuarios/eu'}

ENDERECOS_LOCAIS = {'127.0.0.1', '::1', 'localhost', 'testclient'}

ROTAS_LIVRES = {'/api/acesso', '/api/acesso/estado', '/api/acesso/sair', '/api/usuarios/entrar', '/api/usuarios/sair'}

NOME_COMPUTADOR = 'Computador principal'

NOME_REDE = 'Acesso pela rede'

VALIDADE_COOKIE = 30 * 24 * 3600

MAX_TENTATIVAS = 5

BLOQUEIO_SEGUNDOS = 300
```

## `app/admin.py`

```python
COOKIE = 'leitor_admin'

TAMANHO_MINIMO = 6

ITERACOES = 200000

MAX_TENTATIVAS = 5

BLOQUEIO_SEGUNDOS = 300

DURACAO_SESSAO = 20 * 60
```

## `app/arquivos.py`

```python
RE_ID = re.compile('^[0-9a-f]{32}$')
```

## `app/atalhos.py`

```python
NOME = config.NOME_APP

NOMES_ANTIGOS = ('Leitor de Boletos',)

ICONE = BASE_DIR / 'web' / 'icons' / 'app.ico'

_SCRIPT = "\n$ErrorActionPreference = 'Stop'\n[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n$shell = New-Object -ComObject WScript.Shell\n$criados = @()\nforeach ($pasta in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {\n  $caminho = Join-Path $pasta ($env:LEITOR_NOME + '.lnk')\n  $atalho = $shell.CreateShortcut($caminho)\n  $atalho.TargetPath = $env:LEITOR_ALVO\n  $atalho.Arguments = '-m app'\n  $atalho.WorkingDirectory = $env:LEITOR_DIR\n  $atalho.IconLocation = $env:LEITOR_ICONE\n  $atalho.Description = 'Fin Pro - boletos, Pix e lembretes de vencimento'\n  $atalho.Save()\n  $criados += $caminho\n}\nConvertTo-Json -InputObject @($criados) -Compress\n"
```

## `app/backup.py`

```python
NOME_PASTA = 'Leitor de Boletos - Backup'

CONFIGURACOES = ('notificacoes.json', 'usuarios.json', 'admin.json', 'rede.json', 'importacao_modelos.json', 'backup.json', 'entrada.json', 'gravacao_pendente.json')

INTERVALO_VERIFICACAO = 300

ESPERA_APOS_FALHA = timedelta(minutes=30)

ESPERA_APOS_FALHA_PACOTE = timedelta(hours=6)

DIAS_PARA_ALERTA = 2

RE_COPIA = re.compile('^(?:boletos|empresas|diesel)-(\\d{4}-\\d{2}-\\d{2})\\.(xlsx|db)$')

RE_PACOTE = re.compile('^Fin Pro - backup completo (\\d{4}-\\d{2}-\\d{2})_(\\d{4})\\.zip$')

PASTAS_FORA_DO_CODIGO = {'.venv', 'venv', '__pycache__', '.pytest_cache', '.git', 'node_modules', NOME_PASTA}

SUFIXOS_FORA_DO_CODIGO = {'.pyc', '.pyo', '.tmp', '.parcial'}

PACOTES = {'nunca': None, 'semanal': 7, 'mensal': 30}

SECOES = ('planilha', 'arquivos', 'configuracoes', 'codigo', 'versoes')

NOME_BUNDLE = 'finpro.bundle'

BLOCO = 1024 * 1024

LEIA_ME = 'BACKUP COMPLETO DO FIN PRO\n==========================\n\nEsta pasta é criada e atualizada automaticamente pelo Fin Pro (uma vez por dia). Ela tem TUDO o que é preciso para\ncolocar o sistema para funcionar de novo em outro computador:\n\n  planilha\\         uma cópia por dia de cada banco de dados (boletos, empresas, diesel) e de cada planilha Excel\n  arquivos\\         PDFs e fotos dos boletos, comprovantes, cupons do caixa, canhotos do diesel, cheques e notas\n  configuracoes\\    lembretes, usuários, bots do Telegram, preços, e o arquivo .env\n  codigo\\           o código-fonte completo do sistema (o programa em si)\n  versoes\\          o histórico de todas as versões do sistema (finpro.bundle) e a versão deste backup (VERSAO.txt)\n  pacotes\\          tudo isto num único arquivo .zip, gerado de tempos em tempos\n  manifesto.json    a lista de tudo o que há aqui, para conferir se nada se perdeu ou se corrompeu\n\nATENÇÃO: a pasta "configuracoes" guarda os tokens dos bots e as senhas de e-mail. Mantenha este backup num lugar\nde confiança (a sua conta do OneDrive/Google Drive, ou um pen drive guardado).\n\nCOMO RESTAURAR EM OUTRO COMPUTADOR (jeito fácil)\n1. Instale o Python 3.10 ou mais novo (https://www.python.org/downloads/), marcando "Add python.exe to PATH".\n2. Dê dois cliques em RESTAURAR.bat (nesta pasta) e escolha onde o sistema vai ficar.\n   Ele copia o código, os bancos de dados mais recentes, os arquivos e as configurações para o lugar certo.\n3. Na pasta escolhida, dê dois cliques em iniciar.bat. Na primeira vez ele instala o que falta (alguns minutos).\n\nCOMO RESTAURAR À MÃO (se preferir)\n1. Copie a pasta "codigo" inteira para onde o sistema vai ficar (ex.: Documentos\\Fin Pro).\n2. Dentro dela, crie a pasta "dados".\n3. Em "planilha", pegue a cópia mais recente de cada banco e copie para "dados" com estes nomes:\n      boletos-DATA.db  -> dados\\boletos.db       empresas-DATA.db -> dados\\empresas.db\n      diesel-DATA.db   -> dados\\diesel.db\n   (as planilhas Excel são refeitas sozinhas; as cópias .xlsx daqui abrem direto no Excel.)\n4. Copie a pasta "arquivos" inteira para dentro de "dados".\n5. Copie os arquivos .json de "configuracoes" para dentro de "dados", e o ".env" para a pasta do sistema.\n6. Dê dois cliques em iniciar.bat.\n\nHISTÓRICO DE VERSÕES\nO arquivo versoes\\finpro.bundle tem todas as versões do código. Com o git instalado:\n      git clone versoes\\finpro.bundle "Fin Pro - codigo"\nrecria o repositório com todas as versões (o RESTAURAR.bat já faz isso sozinho quando o git está instalado).\n\nIMPORTANTE AO RESTAURAR\nSó ligue os bots do Telegram no computador novo depois de desligar o antigo: dois sistemas com o mesmo bot\ndisputam as mensagens.\n'

RESTAURAR_BAT = '@echo off\nchcp 65001 >nul\ntitle Restaurar o Fin Pro\necho.\necho  RESTAURAR O FIN PRO A PARTIR DESTE BACKUP\necho  -----------------------------------------\necho  Copia o codigo, os bancos de dados, os arquivos e as configuracoes\necho  para uma pasta nova. Nada e apagado deste backup.\necho.\nset "DESTINO=%USERPROFILE%\\Documents\\Fin Pro"\nset /p "DESTINO=Onde o sistema vai ficar (ENTER = %DESTINO%): "\necho.\npy -3 "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"\nif errorlevel 9009 python "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"\necho.\npause\n'
```

## `app/banco.py`

```python
ESPERA_EXPORTACAO = 1.5

INTERVALO_VERIFICACAO = 15

USUARIO_EXCEL = 'Planilha Excel (edição manual)'
```

## `app/boleto/bancos.py`

```python
BANCOS = {'001': 'Banco do Brasil', '003': 'Banco da Amazônia', '004': 'Banco do Nordeste', '021': 'Banestes', '025': 'Banco Alfa', '033': 'Santander', '037': 'Banpará', '041': 'Banrisul', '047': 'Banese', '070': 'BRB - Banco de Brasília', '077': 'Banco Inter', '085': 'Ailos', '097': 'Credisis', '099': 'Uniprime', '104': 'Caixa Econômica Federal', '121': 'Agibank', '133': 'Cresol', '136': 'Unicred', '197': 'Stone', '208': 'BTG Pactual', '212': 'Banco Original', '218': 'Banco BS2', '237': 'Bradesco', '246': 'Banco ABC Brasil', '260': 'Nubank', '274': 'Money Plus', '290': 'PagBank', '318': 'Banco BMG', '323': 'Mercado Pago', '329': 'QI SCD', '332': 'Acesso Soluções de Pagamento', '336': 'C6 Bank', '341': 'Itaú Unibanco', '348': 'Banco XP', '364': 'Efí (Gerencianet)', '380': 'PicPay', '389': 'Banco Mercantil do Brasil', '403': 'Cora', '422': 'Banco Safra', '461': 'Asaas', '623': 'Banco Pan', '633': 'Banco Rendimento', '634': 'Banco Triângulo (Tribanco)', '637': 'Banco Sofisa', '643': 'Banco Pine', '655': 'Banco Votorantim (BV)', '707': 'Banco Daycoval', '739': 'Cetelem', '743': 'Banco Semear', '745': 'Citibank', '746': 'Banco Modal', '748': 'Sicredi', '756': 'Sicoob'}

SEGMENTOS_ARRECADACAO = {'1': 'Prefeituras', '2': 'Saneamento', '3': 'Energia elétrica e gás', '4': 'Telecomunicações', '5': 'Órgãos governamentais', '6': 'Carnês e assemelhados', '7': 'Multas de trânsito', '9': 'Uso exclusivo do banco'}
```

## `app/boleto/codigo.py`

```python
BASE_FATOR_ORIGINAL = date(1997, 10, 7)

BASE_FATOR_NOVO_CICLO = date(2025, 2, 22) - timedelta(days=1000)

BANCARIO = 'bancario'

ARRECADACAO = 'arrecadacao'

_CONFUSOES_OCR = {frozenset(p) for p in (('0', '8'), ('3', '8'), ('5', '6'), ('6', '8'), ('1', '7'), ('4', '9'), ('0', '6'), ('0', '9'), ('5', '8'), ('2', '7'), ('1', '4'), ('3', '5'), ('8', '9'))}
```

## `app/boleto/extrator.py`

```python
CAMPOS_DOCUMENTO = ('beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor')

ORDEM_CAMPOS = ('linha_digitavel', 'codigo_barras', 'beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor')

_PESO_NIVEL = {'erro': 0, 'aviso': 1, 'info': 2}
```

## `app/boleto/leitores.py`

```python
LADO_MAXIMO_IMAGEM = 3200
```

## `app/boleto/ocr.py`

```python
TAMANHO_CACHE = 64
```

## `app/boleto/texto.py`

```python
_MAPA_ESPECIAL = {'º': 'o', '°': 'o', 'ª': 'a', '–': '-', '—': '-', '‐': '-'}

_LIGADURAS = str.maketrans({'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', '\xa0': ' ', '\xad': ''})

RE_DATA = re.compile('(?<!\\d)(\\d{2})\\s?[/.\\-]\\s?(\\d{2})\\s?[/.\\-]\\s?(\\d{4}|\\d{2})(?!\\d)')

RE_MOEDA = re.compile('(?<![\\d,])(\\d{1,3}(?:\\.\\d{3})+|\\d+),(\\d{2})(?!\\d)')

RE_CNPJ = re.compile('(?<!\\d)\\d{2}\\.?\\d{3}\\.?\\d{3}\\s?/\\s?\\d{4}\\s?-?\\s?\\d{2}(?!\\d)')

RE_CPF = re.compile('(?<!\\d)\\d{3}\\.\\d{3}\\.\\d{3}-?\\d{2}(?!\\d)')

_MESES_TEXTO = {m: i for i, m in enumerate(('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'), 1)}

_RE_DATA_EXTENSO = re.compile('(?<!\\d)(\\d{1,2})\\s*(?:/|-|\\.|de)?\\s*(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\\.?\\s*(?:/|-|\\.|de)?\\s*(\\d{4})(?!\\d)')

RE_CNPJ_SEM_FORMATO = re.compile('(?<!\\d)\\d{14}(?!\\d)')

_PALAVRAS_ROTULO = re.compile('agencia|codigo|vencimento|local de pagamento|pagavel|nosso numero|data d[oe]|especie|aceite|carteira|pagador|sacado|instruc|valor|bene\\w{2,6}rio|cedente|documento|autenticacao|ficha de compensacao|recibo|uso do banco|quantidade|processamento|sacador|avalista|mora|multa|desconto|abatimento|deduc|acrescimo|cobrado|juros')

_PREPOSICOES = {'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'ao', 'aos', 'com', 'para', 'em', 'no', 'na', 'pelo', 'pela'}

_CONECTORES_NOME = {'e', 'de', 'da', 'do', 'dos', 'das', '&'}

_RE_ENDERECO = re.compile('(?:^|[\\s,\\-–])(av\\.?|avenida|rua|r\\.|rodovia|rod\\.|estrada|alameda|travessa|praca|br-?\\d{2,3}|cep)(?=[\\s.:,]|$)')

_VOCABULARIO = set('\nEMPRESA EMPRESAS EXEMPLO COMERCIO COMERCIAL SERVICOS SERVICO INDUSTRIA INDUSTRIAL INDUSTRIAS CONSTRUCOES CONSTRUCAO\nCONSTRUTORA ENGENHARIA TECNOLOGIA TECNOLOGIAS SOLUCOES DISTRIBUIDORA DISTRIBUICAO ALIMENTOS TRANSPORTES TRANSPORTE\nLOGISTICA ADMINISTRADORA ADMINISTRACAO CONDOMINIO EDIFICIO RESIDENCIAL ASSOCIACAO ESCOLA COLEGIO CLINICA HOSPITAL\nSAUDE SEGUROS SEGURADORA TELECOMUNICACOES TELECOM ENERGIA ELETRICA ELETRICIDADE SANEAMENTO AGUA ESGOTO BANCO CARTOES\nCREDITO FINANCEIRA FINANCEIRO IMOBILIARIA IMOVEIS EMPREENDIMENTOS PARTICIPACOES CONSULTORIA CONTABILIDADE CONTABIL\nADVOCACIA ADVOGADOS ASSOCIADOS INFORMATICA SISTEMAS INTERNET PROVEDOR EDUCACAO EDUCACIONAL ENSINO CURSOS ACADEMIA\nFARMACIA DROGARIA MATERIAIS AUTO PECAS VEICULOS MOTOS POSTO COMBUSTIVEIS MERCADO SUPERMERCADO SUPERMERCADOS ATACADO\nVAREJO MODAS CONFECCOES CALCADOS MOVEIS ELETRONICOS GRAFICA EDITORA COMUNICACAO PUBLICIDADE MARKETING EVENTOS TURISMO\nVIAGENS HOTEL RESTAURANTE LANCHONETE PADARIA BEBIDAS IMPORTACAO EXPORTACAO NACIONAL BRASIL BRASILEIRA BRASILEIRO\nGRUPO HOLDING COMPANHIA SOCIEDADE COOPERATIVA SINDICATO FEDERACAO INSTITUTO FUNDACAO UNIVERSIDADE FACULDADE CENTRO\nPRESTACAO MANUTENCAO LIMPEZA SEGURANCA VIGILANCIA MEDICINA MEDICOS ODONTOLOGIA LABORATORIO DIAGNOSTICOS PLANO PLANOS\nVIDA PREVIDENCIA PAGAMENTOS PAGAMENTO INSTITUICAO NEGOCIOS CIDADE MUNICIPAL MUNICIPIO PREFEITURA ESTADO GOVERNO\nSECRETARIA FAZENDA RECEITA FEDERAL ESTADUAL AGRICOLA AGRO PRODUTOS EQUIPAMENTOS MAQUINAS INTERNACIONAL PAULISTA\nPAULO CARIOCA MINEIRA GAUCHA NORDESTE SUL NORTE LESTE OESTE CENTRAL TELEFONICA TELEFONIA MOVEL DIGITAL CLUBE ESPORTE\nLOCACAO LOCADORA TRANSPORTADORA ARMAZENS COMERCIALIZADORA REPRESENTACOES REPRESENTACAO SEGURO CAPITALIZACAO GAS\n'.split())

_SUFIXOS = {'LTDA', 'ME', 'EPP', 'SA', 'EIRELI', 'MEI', 'CIA'}

_CONECTORES = {'DE', 'DA', 'DO', 'DOS', 'DAS', 'E', 'EM'}

_RE_TRECHO_NUMERICO = re.compile('[0-9OoIl|SBZ](?:[0-9OoIl|SBZ.\\- \\t]){38,}[0-9OoIl|SBZ]')

_TRADUCAO_OCR = str.maketrans({'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1', 'S': '5', 'B': '8', 'Z': '2'})

ROTULOS_BENEFICIARIO = [_Rotulo(re.compile('\\bbene\\w{2,6}rio\\b|\\bcedente\\b'), excluir_antes=re.compile('(agencia|codigo|cod\\.?|cpf|cnpj|endereco|sacador|avalista)[^a-z]*(d[oe]\\s*)?$'), excluir_depois=re.compile('^\\s*final')), _Rotulo(re.compile('\\bfavorecido\\b|\\braz[aã]o social\\b'), prioridade=1)]

ROTULOS_VENCIMENTO = [_Rotulo(re.compile('\\bvenc(imento|to)?\\b\\.?')), _Rotulo(re.compile('\\bpag(ar|avel|amento)\\b[a-z\\s]{0,25}?\\bate\\b'), prioridade=1), _Rotulo(re.compile('\\bdata\\s+limite\\b|\\bvalido\\s+ate\\b'), prioridade=2)]

ROTULOS_DOCUMENTO = [_Rotulo(re.compile('\\b(n|no|nr|nro|num|numero)\\s*[.:]?\\s*(d[oea]\\s*)?doc(umento|to)?\\b\\.?')), _Rotulo(re.compile('\\bseu\\s+numero\\b|\\bn\\.?\\s*(o\\s*)?fatura\\b|\\bnumero\\s+da\\s+fatura\\b'), prioridade=1), _Rotulo(re.compile('\\bnota\\s+fiscal(\\s+(n|no|numero)\\b\\.?)?|\\b(n|no|numero)\\s*[.:]?\\s*(da\\s+)?nota\\s+fiscal\\b|\\bfatura\\s+(n|no)\\b'), prioridade=2)]

_EXCLUIR_VALOR = re.compile('desconto|abatimento|mora|multa|juros|acrescimo|deduc|outros|encargo')

ROTULOS_VALOR = [_Rotulo(re.compile('valor\\s*(d[oe]\\s*)?documento'), excluir_segmento=_EXCLUIR_VALOR), _Rotulo(re.compile('valor\\s+cobrado|valor\\s+a\\s+pagar|total\\s+a\\s+pagar|valor\\s+total'), prioridade=1, excluir_segmento=_EXCLUIR_VALOR), _Rotulo(re.compile('\\bvalor\\b'), prioridade=2, excluir_segmento=_EXCLUIR_VALOR)]

_FALLBACK = {'vencimento': (re.compile('(?:venc\\w*|pagar[a-z\\s]{0,25}ate)\\W{0,20}(\\d{2}/\\d{2}/\\d{4})', re.S), extrair_data), 'valor': (re.compile('valor\\s*(?:d[oe]\\s*)?(?:documento|cobrado|a pagar|total)\\W{0,30}([\\d.]+,\\d{2})', re.S), extrair_valor), 'numero_documento': (re.compile('(?:n|no|nro|num|numero)\\.?\\s*(?:d[oe]\\s*)?doc\\w*\\W{0,15}([A-Za-z0-9][\\w\\-/.]*)', re.S), extrair_documento), 'beneficiario': (re.compile('(?:bene\\w{2,6}rio|cedente)\\s*[:\\-]?\\s*([^\\n]{3,120})'), extrair_beneficiario)}

_GUIAS = [('documento de arrecadacao do simples nacional|simples nacional|\\bdas[-\\s]?mei\\b', 'Receita Federal - Simples Nacional (DAS)'), ('\\bdarf\\b|documento de arrecadacao de receitas federais', 'Receita Federal (DARF)'), ('guia da previdencia social|\\bgps\\b[\\s\\S]{0,40}\\binss\\b', 'INSS - Guia da Previdência Social (GPS)'), ('fgts digital|guia do fgts|guia de recolhimento do fgts|\\bgrf\\b[\\s\\S]{0,30}fgts', 'FGTS - Caixa Econômica Federal'), ('\\bdetran\\b|licenciamento anual', 'DETRAN'), ('\\bipva\\b', 'IPVA - Secretaria da Fazenda Estadual'), ('\\biptu\\b', 'IPTU - Prefeitura Municipal'), ('documento de arrecadacao estadual|\\bdae\\b|\\bgare\\b|\\bdarj\\b', 'Secretaria da Fazenda Estadual'), ('\\biss\\b[\\s\\S]{0,30}prefeitura|\\bnfs-?e\\b[\\s\\S]{0,40}prefeitura', 'Prefeitura Municipal (ISS)')]

_NAO_E_NOME = re.compile('\\bbanco\\b|recibo|ficha|compensacao|pagavel|autenticacao|\\bconta\\b|fatura|segunda via|\\b2a via\\b|documento de arrecadacao|boleto|nota fiscal|pagador|cliente|vencimento|linha digitavel|www\\.|https?:|@|\\b\\d{3}-[\\dx]\\b|\\bdanfe\\b|\\bcomprovante\\b')

_NOMES_BANCOS = {normalizar(nome).split(' (')[0] for nome in BANCOS.values()}
```

## `app/bot.py`

```python
COMANDOS = [('vencidos', 'Boletos e Pix em atraso'), ('hoje', 'O que vence hoje'), ('semana', 'O que vence nos próximos 7 dias'), ('previsao', 'Quanto vai sair nas próximas semanas'), ('buscar', 'Procurar pelo nome (ex.: /buscar energisa)'), ('resumo', 'Totais: atraso, 7 dias, 30 dias e pagos no mês'), ('ajuda', 'Lista dos comandos')]

LIMITE_MENSAGEM = 3800

MAX_ITENS = 40
```

## `app/busca_comprovantes.py`

```python
TIPOS = {'boleto': 'Boleto', 'pix': 'Pix', 'cheque': 'Cheque', 'recebimento': 'Recebimento', 'caixa': 'Caixa (dinheiro)', 'nota': 'Nota fiscal', 'diesel': 'Diesel'}

PERMISSAO_DO_TIPO = {'cheque': 'empresas', 'recebimento': 'empresas', 'nota': 'empresas', 'caixa': 'caixa', 'diesel': 'diesel'}

LIMITE_ZIP = 500

FONTES = {'boleto': _boletos, 'pix': _pix, 'caixa': _caixa, 'cheque': _cheques, 'recebimento': _recebimentos, 'nota': _notas, 'diesel': _diesel}
```

## `app/caixa/bot.py`

```python
MASCARA = '••••••••'

INTERVALO = 20

TAMANHO_MAXIMO = 20 * 1024 * 1024

EXTENSOES = ('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.xml')

MAX_ITENS = 300

DIAS_MANTER_CONCLUIDOS = 30

COMANDOS = [('ajuda', 'Como mandar um gasto do caixa'), ('resumo', 'Entradas e saídas de hoje e do mês'), ('cancelar', 'Desistir do gasto que está sendo informado')]

PADRAO = {'config': {'ativo': False, 'token': '', 'offset': 0, 'ultima_verificacao': None, 'ultimo_erro': None}, 'itens': [], 'conversas': {}}
```

## `app/caixa/leitura.py`

```python
ROTULOS_TOTAL = ('valor a pagar', 'total a pagar', 'valor total', 'total geral', 'total da (nota|compra|venda)', 'total\\s*r\\$', '\\btotal\\b')

NAO_E_TOTAL = ('troco', 'dinheiro', 'valor pago', 'valor recebido', 'recebido', 'desconto', 'acrescimo', 'tributo', 'imposto', '12.741', '12741', 'itens', 'qtd', 'quantidade')

CABECALHOS = ('documento auxiliar', 'cupom', 'nfc-e', 'nfce', 'nota fiscal', 'consumidor', 'extrato', 'sat ', 'cnpj', 'inscricao', 'ie:', 'endereco', 'danfe', 'emissao', 'via ')
```

## `app/caixa/servico.py`

```python
PERIODOS = ('dia', 'semana', 'mes', 'ano')

MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']

SEM_CENTRO = 'Sem centro de custo'
```

## `app/comprovante.py`

```python
RE_MOEDA_OU_ZERO = re.compile('(?<![\\d,])(\\d{1,3}(?:\\.\\d{3})+|\\d+),(\\d{2})(?!\\d)')

SINAIS_COMPROVANTE = ('comprovante', 'valor pago', 'total pago', 'pagamento efetuado', 'pagamento realizado', 'pagamento concluido', 'transacao efetuada', 'transacao realizada', 'transacao concluida', 'operacao realizada', 'data do pagamento', 'data de pagamento', 'data do debito', 'data da transacao', 'data da operacao', 'autenticacao', 'id da transacao', 'id/transacao', 'e2e', 'end to end', 'transferencia realizada', 'transferencia enviada', 'pix enviado', 'pix realizado', 'pago em', 'debitado', 'codigo de autenticacao', 'numero de controle')

SINAIS_BOLETO = ('local de pagamento', 'pagavel em', 'pagavel preferencialmente', 'ficha de compensacao', 'recibo do pagador', 'recibo do sacado', 'nosso numero', 'uso do banco', 'especie doc', 'data do processamento', 'instrucoes', 'sacador/avalista', 'ate o vencimento')

PALAVRAS_GENERICAS = {'ltda', 'me', 'epp', 'sa', 's/a', 'eireli', 'comercio', 'comercial', 'servicos', 'industria', 'de', 'da', 'do', 'dos', 'das', 'e', 'cia', 'empresa', 'grupo', 'brasil', 'the'}

ROTULO_VALOR_PAGO = 'valor (total )?pago|total pago|valor do pagamento|valor debitado|valor cobrado|valor total|valor da transferencia|valor do pix|valor da transacao|valor transferido|\\(=\\)'

ROTULO_VALOR_DOCUMENTO = 'valor (original )?do (documento|boleto|titulo)|valor original|valor nominal|valor do titulo'

ROTULO_JUROS = 'juros|multa|mora|encargos|acrescimo|\\(\\+\\)'

ROTULO_DESCONTO = 'desconto|abatimento|bonificacao|\\(-\\)'

ROTULO_DATA_PAGAMENTO = 'data d[oea] (pagamento|debito|transacao|operacao|transferencia|efetivacao|pix)|pago em|realizad[oa] em|efetuad[oa] em|debitado em|data/hora|data e hora|horario'

ROTULO_VENCIMENTO = 'vencimento'

ROTULO_NOME = 'beneficiario( final)?|favorecido|recebedor|destinatario|nome do recebedor|cedente|razao social|^para\\b|^destino\\b'

ROTULO_CHAVE = 'chave( pix)?\\b'

LIMITE_CONFIANCA = 75

MARGEM_CONFIANCA = 20

RE_SO_ROTULO = re.compile('^(nome|cpf|cnpj|cpf/cnpj|instituicao|banco|agencia|conta|chave( pix)?|dados|tipo|documento|beneficiario|favorecido|recebedor|destino|para)\\W*$')
```

## `app/config.py`

```python
BASE_DIR = Path(__file__).resolve().parent.parent

NOME_APP = os.getenv('LEITOR_NOME_APP', 'Fin Pro')

DEMONSTRACAO = _bool('LEITOR_DEMO', False)

DADOS_DIR = Path(os.getenv('LEITOR_DADOS_DIR') or BASE_DIR / 'dados')

PLANILHA_PATH = Path(os.getenv('LEITOR_PLANILHA') or DADOS_DIR / 'boletos.xlsx')

FECHAMENTOS_PATH = Path(os.getenv('LEITOR_FECHAMENTOS') or PLANILHA_PATH.parent / 'fechamentos.xlsx')

DIESEL_PATH = Path(os.getenv('LEITOR_DIESEL') or PLANILHA_PATH.parent / 'diesel.xlsx')

ARQUIVOS_DIR = DADOS_DIR / 'arquivos'

BACKUPS_DIR = DADOS_DIR / 'backups'

WEB_DIR = BASE_DIR / 'web'

HOST = os.getenv('LEITOR_HOST', '127.0.0.1')

PORT = int(os.getenv('LEITOR_PORT', '8000'))

MAX_UPLOAD_MB = int(os.getenv('LEITOR_MAX_UPLOAD_MB', '100'))

MAX_PAGINAS_PDF = int(os.getenv('LEITOR_MAX_PAGINAS_PDF', '30'))

DIAS_MANTER_ARQUIVOS_NAO_LANCADOS = int(os.getenv('LEITOR_DIAS_ARQUIVOS_TEMP', '2'))

URL_APP = os.getenv('LEITOR_URL') or f'http://{('localhost' if HOST in ('0.0.0.0', '127.0.0.1', '::') else HOST)}:{PORT}'

NOTIFICACOES_AUTOMATICAS = _bool('LEITOR_NOTIFICACOES_AUTOMATICAS', True)

BACKUP_AUTOMATICO = _bool('LEITOR_BACKUP_AUTOMATICO', True)

SENHA_ACESSO = (os.getenv('LEITOR_SENHA_ACESSO') or '').strip()

IA_MODELO = os.getenv('LEITOR_IA_MODELO', 'claude-opus-5')

IA_AUTOMATICA = _bool('LEITOR_IA_AUTOMATICA', False)
```

## `app/demonstracao.py`

```python
PORTA_PADRAO = '8010'

CENTROS = [('Combustível e Veículos', 'Diesel, gasolina, pneus e manutenção da frota'), ('Manutenção', 'Peças, oficina e serviços de manutenção'), ('Materiais', 'Materiais de produção e insumos'), ('Energia e Água', 'Contas de consumo'), ('Escritório', 'Papelaria, internet, telefone e sistemas'), ('Impostos e Taxas', 'Tributos e taxas'), ('Fretes', 'Transporte e entregas')]

FORNECEDORES = [('ENERGISA SUL SUDESTE', '09.095.183/0001-40', 'Energia e Água', 'Banco do Brasil'), ('POSTO SAO JORGE LTDA', '12.345.678/0001-95', 'Combustível e Veículos', 'Bradesco'), ('MAXIMA PARAFUSOS LTDA', '18.765.432/0001-21', 'Manutenção', 'Itaú'), ('TRANSPORTES RODRIGUES ME', '22.334.556/0001-09', 'Fretes', 'Sicredi'), ('COMERCIAL DE FERRO E ACO', '31.222.111/0001-77', 'Materiais', 'Santander'), ('SANEAMENTO MUNICIPAL', '05.111.222/0001-13', 'Energia e Água', 'Caixa'), ('PAPELARIA CENTRAL', '41.999.888/0001-55', 'Escritório', 'Banco do Brasil'), ('OFICINA DIESEL MIRASSOL', '27.888.777/0001-30', 'Manutenção', 'Bradesco'), ('PREFEITURA MUNICIPAL - ISS', '45.123.987/0001-10', 'Impostos e Taxas', 'Caixa'), ('DISTRIBUIDORA DE LUBRIFICANTES', '33.444.555/0001-66', 'Combustível e Veículos', 'Itaú')]

RECEBEDORES_PIX = [('Mecânica do Zé', 'cnpj', '12.987.654/0001-70', 'Manutenção', 'Troca de óleo do caminhão'), ('Maria da Limpeza', 'celular', '+5517999887766', 'Escritório', 'Serviços de limpeza'), ('Serralheria Aço Forte', 'cnpj', '44.555.666/0001-01', 'Manutenção', 'Conserto da caçamba'), ('Contabilidade Silva', 'email', 'contato@contabilidadesilva.com.br', 'Escritório', 'Honorários do mês'), ('Frete Expresso', 'aleatoria', 'b3f1c2de-77aa-4c31-9f55-0a1b2c3d4e5f', 'Fretes', 'Entrega urgente de peças')]

GASTOS_CAIXA = [('Posto São Jorge', 'Combustível e Veículos', 'gasolina da caminhonete', 180.0, 320.0), ('Mercado Bom Preço', 'Escritório', 'café, açúcar e copos', 45.0, 130.0), ('Casa do Parafuso', 'Manutenção', 'parafusos e arruelas', 60.0, 240.0), ('Papelaria Central', 'Escritório', 'toner e papel A4', 90.0, 260.0), ('Borracharia do Tião', 'Combustível e Veículos', 'conserto de pneu', 70.0, 200.0), ('Lanchonete da Praça', 'Escritório', 'almoço da equipe', 50.0, 150.0)]

EMPRESAS_CLIENTES = [('Imapal Construções', '12.345.678/0001-95', 'Imapal, Imapal Construcoes', 'Brita 01', 'M³', 158.8), ('Jose Pazete & Cia', '39.285.595/0001-04', 'Pazete, Jose Pazete', 'Pedrisco Comercial', 'M³', 142.5), ('Terraplanagem Souza', '07.654.321/0001-88', 'Souza, Terraplanagem Souza', 'Rachão', 'M³', 96.4)]

PESSOAS = ['Fábio', 'Almir', 'Marcos', 'Juliana']

MAQUINAS_DIESEL = [('Escavadeira PC200', 'Máquina', '', 'horas', 'Diesel comum', (150, 210), 9), ('Pá carregadeira 924K', 'Máquina', '', 'horas', 'Diesel comum', (110, 160), 8), ('Caminhão Volvo FMX', 'Caminhão', 'ABC-1D23', 'km', 'Diesel S10', (180, 260), 180), ('Caminhão Scania P360', 'Caminhão', 'DEF-2G34', 'km', 'Diesel S10', (170, 240), 160), ('Gerador 80 kVA', 'Gerador', '', 'horas', 'Diesel comum', (40, 70), 6)]

COMPRAS_SEMANAIS = (('Diesel S10', 550, 7.45), ('Diesel comum', 500, 6.75))
```

## `app/desktop.py`

```python
TITULO = 'Fin Pro'

ID_APP = 'LeitorDeBoletos.Aplicativo'

ICONE_ICO = config.WEB_DIR / 'icons' / 'app.ico'

ICONE_PNG = config.WEB_DIR / 'icons' / 'icone-192.png'
```

## `app/diesel/bot.py`

```python
MASCARA = '••••••••'

INTERVALO = 20

TAMANHO_MAXIMO = 20 * 1024 * 1024

EXTENSOES = ('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic')

MAX_ITENS = 400

DIAS_MANTER_CONCLUIDOS = 30

ABERTOS = ('conversa', 'aguardando', 'pendente', 'erro')

COMANDOS = [('saldo', 'Quanto diesel ainda tem'), ('medias', 'Média de consumo de cada máquina'), ('relatorio', 'Relatório da semana (ou: /relatorio mes, /relatorio mes detalhado, … completo)'), ('maquinas', 'Máquinas cadastradas'), ('cancelar', 'Desistir do que está sendo informado'), ('ajuda', 'Como usar o bot do diesel')]

PADRAO = {'config': {'ativo': False, 'token': '', 'offset': 0, 'ultima_verificacao': None, 'ultimo_erro': None, 'gestores': [], 'alerta_valor': servico.ALERTA_PADRAO, 'hora_relatorio': '07:00', 'relatorios': {'semana': True, 'quinzena': True, 'mes': True}, 'nivel_relatorio': 'simples', 'enviados': {}}, 'itens': [], 'conversas': {}}

CAMPOS_DA_LINHA = ('combustivel', 'litros', 'preco_litro', 'valor', 'maquina', 'medidor')
```

## `app/diesel/leitura.py`

```python
LIMITE_CANHOTO = 600.0

SINAIS_COMPRA = ('comprovante de pagamento', 'comprovante de transferencia', 'pix', 'transferencia', 'ted', 'boleto', 'pagamento efetuado', 'pagamento realizado', 'valor pago', 'favorecido', 'recebedor', 'debito', 'autenticacao', 'id da transacao')

SINAIS_CANHOTO = ('canhoto', 'abastecimento', 'requisicao', 'frentista', 'bomba', 'bico', 'placa', 'motorista', 'hodometro', 'horimetro', 'odometro', 'km', 'frota', 'veiculo', 'prefixo', 'assinatura', 'documento nao fiscal', 'pedido', 'cond. pagto', 'vendedor')

PARADAS = ('totais', 'quantidade de itens', 'quantidade de rtens', 'qusntidade', 'valor total bruto', 'valor total liquido', 'valor desconto', 'credito troca', 'subtotal', 'forma de pagamento', 'dados do cliente', 'cliente:')

RE_LITROS = [re.compile('(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{1,3})?|\\d+(?:[.,]\\d{1,3})?)\\s*(?:l\\b|lt\\b|lts\\b|litros?\\b)', re.I), re.compile('(?:litros?|lts?|qtd|quantidade|qtde|volume)\\s*[:=.\\-]?\\s*(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{1,3})?|\\d+(?:[.,]\\d{1,3})?)', re.I)]

RE_PRECO = re.compile('(?:pre[cç]o|valor|vl\\.?|r\\$)\\s*(?:unit[aá]rio|unit\\.?|/\\s*l(?:itro)?|por litro|litro)\\s*[:=]?\\s*(?:r\\$)?\\s*(\\d{1,2}[.,]\\d{2,3})', re.I)

RE_PLACA = re.compile('\\b([A-Z]{3})[\\s-]?(\\d[A-Z0-9]\\d{2})\\b')

RE_MEDIDOR = re.compile('(?:km|hod[oô]metro|od[oô]metro|hor[ií]metro|hr|horas?)\\s*[:=.\\-]?\\s*(\\d{1,3}(?:\\.\\d{3})+(?:,\\d)?|\\d+(?:[.,]\\d)?)', re.I)

RE_TOKEN = re.compile('(?<![\\w.,])\\d[\\d.,]*\\d(?![\\w])|(?<![\\w.,])\\d(?![\\w.,])')

RE_PEDIDO = re.compile('(?:pedido|requisi[cç][aã]o|canhoto|cupom|documento)\\s*n?\\S{0,2}\\s*[:.]?\\s*(\\d{4,12})', re.I)

RUIDO_DO_BANCO = ('telefone', 'ouvidoria', 'sac ', 'sac-', 'site', 'atendimento', 'fale conosco', '0800', 'deficiente', 'reclamac', 'cancelamento', 'servico de', 'apoio ao cliente', 'alo ')

RE_FAVORECIDO = re.compile('^\\s*(?:nome|favorecido|recebedor|benefici[aá]rio|destinat[aá]rio|para|pago a)\\s*[:\\-]\\s*(.{3,})$', re.I)
```

## `app/diesel/modelos.py`

```python
COR_MAQUINAS = '3F4A56'

COR_COMPRAS = '0E6B5C'

COR_ABASTECIMENTOS = 'B45309'

TIPOS_MAQUINA = ('Caminhão', 'Máquina', 'Veículo', 'Gerador', 'Outro')

MEDIDORES = ('horas', 'km', '')

STATUS_MAQUINA = ('Ativa', 'Inativa')

STATUS_COMPRA = ('Confirmada', 'Cancelada')

STATUS_ABASTECIMENTO = ('Confirmado', 'Cancelado')

LITROS_POR_COMPRA = 1000.0

COMBUSTIVEIS = ('Diesel S10', 'Diesel comum', 'Gasolina', 'Etanol', 'Arla 32')

COMBUSTIVEL_PADRAO = 'Diesel S10'

LITROS = '#,##0.00 "L"'

MOEDA = '"R$" #,##0.00'

COLUNAS_MAQUINAS = [Coluna('id', 'ID', 7, '0'), Coluna('nome', 'Máquina', 30), Coluna('tipo', 'Tipo', 12), Coluna('placa', 'Placa / Prefixo', 16, '@'), Coluna('medidor', 'Medidor (horas/km)', 16), Coluna('combustivel', 'Combustível', 14), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 34), Coluna('data_lancamento', 'Cadastrada em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Cadastrada por', 20), Coluna('atualizado_em', 'Atualizada em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_COMPRAS = [Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('posto', 'Posto', 30), Coluna('combustivel', 'Combustível', 14), Coluna('litros', 'Litros', 12, LITROS), Coluna('valor', 'Valor (R$)', 15, MOEDA), Coluna('preco_litro', 'Preço por Litro (R$)', 16, '"R$" #,##0.000'), Coluna('forma', 'Forma de Pagamento', 16), Coluna('documento', 'Nota / Cupom', 16, '@'), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Comprovante', 28), Coluna('arquivo_nome', 'Nome do Comprovante', 30), Coluna('data_lancamento', 'Lançada em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Lançada por', 20), Coluna('atualizado_em', 'Atualizada em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_ABASTECIMENTOS = [Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 8, '@'), Coluna('maquina', 'Máquina', 28), Coluna('combustivel', 'Combustível', 14), Coluna('litros', 'Litros', 12, LITROS), Coluna('preco_litro', 'Preço por Litro (R$)', 16, '"R$" #,##0.000'), Coluna('valor', 'Valor (R$)', 14, MOEDA), Coluna('medidor', 'Horímetro / Km', 14, '#,##0.0'), Coluna('posto', 'Posto', 24), Coluna('documento', 'Pedido / Canhoto', 16, '@'), Coluna('pessoa', 'Quem Abasteceu', 20), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Canhoto', 28), Coluna('arquivo_nome', 'Nome do Canhoto', 30), Coluna('data_lancamento', 'Lançado em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Lançado por', 20), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

_TEXTOS_COMUNS = frozenset({'observacoes', 'arquivo', 'arquivo_nome', 'lancado_por'})

ABAS_DIESEL = {'maquinas': DefinicaoAba('maquinas', 'Máquinas', tuple(COLUNAS_MAQUINAS), frozenset({'nome', 'tipo', 'placa', 'medidor', 'combustivel', 'status', 'observacoes'}), 'nome', frozenset({'nome', 'tipo', 'placa', 'medidor', 'combustivel'}) | _TEXTOS_COMUNS, COR_MAQUINAS, ' (Máquina)', STATUS_MAQUINA, '', '', 'Inativa'), 'compras': DefinicaoAba('compras', 'Compras de Diesel', tuple(COLUNAS_COMPRAS), frozenset({'data', 'posto', 'combustivel', 'litros', 'valor', 'preco_litro', 'forma', 'documento', 'status', 'observacoes', 'arquivo', 'arquivo_nome'}), 'posto', frozenset({'posto', 'combustivel', 'forma', 'documento'}) | _TEXTOS_COMUNS, COR_COMPRAS, ' (Compra de diesel)', STATUS_COMPRA, 'data', '', 'Cancelada'), 'abastecimentos': DefinicaoAba('abastecimentos', 'Abastecimentos', tuple(COLUNAS_ABASTECIMENTOS), frozenset({'data', 'hora', 'maquina', 'combustivel', 'litros', 'preco_litro', 'valor', 'medidor', 'posto', 'documento', 'pessoa', 'status', 'observacoes', 'arquivo', 'arquivo_nome'}), 'maquina', frozenset({'hora', 'maquina', 'combustivel', 'posto', 'documento', 'pessoa'}) | _TEXTOS_COMUNS, COR_ABASTECIMENTOS, ' (Abastecimento)', STATUS_ABASTECIMENTO, 'data', '', 'Cancelado')}
```

## `app/diesel/relatorio.py`

```python
NIVEIS = ('simples', 'detalhado', 'completo')

NIVEL_PADRAO = 'simples'

ACIMA_DO_NORMAL = {'semana': 1.5, 'quinzena': 1.4, 'mes': 1.3, 'ano': 1.3}

HISTORICO_MINIMO = 14

LITROS_MINIMOS_ALERTA = 50.0

DIAS_RITMO = 30

LIMITE_TELEGRAM = 3900

DIAS_SEMANA = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')

MESES_CURTOS = ('jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez')

TITULOS = {'semana': 'semanal', 'quinzena': 'quinzenal', 'mes': 'mensal', 'ano': 'anual'}

ANTERIOR = {'semana': 'à semana anterior', 'quinzena': 'à quinzena anterior', 'mes': 'ao mês anterior', 'ano': 'ao ano anterior'}
```

## `app/diesel/servico.py`

```python
MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')

PERIODOS = ('semana', 'quinzena', 'mes', 'ano')

SEM_MAQUINA = 'Sem máquina'

ALERTA_PADRAO = 1000.0

EDITAVEIS = {'compras': ('data', 'posto', 'combustivel', 'litros', 'valor', 'preco_litro', 'forma', 'documento', 'observacoes'), 'abastecimentos': ('data', 'hora', 'maquina', 'combustivel', 'litros', 'preco_litro', 'valor', 'medidor', 'posto', 'documento', 'pessoa', 'observacoes')}
```

## `app/empresas/bot.py`

```python
COMANDOS = [('fechamento', 'Fechamento da empresa (ex.: /fechamento imapal)'), ('empresas', 'Todas as empresas e quanto falta receber'), ('cheques', 'Cheques pré-datados a depositar'), ('notas', 'Notas em aberto de uma empresa (ex.: /notas imapal)'), ('ajuda', 'Lista dos comandos')]

LIMITE_MENSAGEM = 3800
```

## `app/empresas/configuracao.py`

```python
MASCARA = '••••••••'

PADRAO = {'minha_empresa': {'nome': '', 'cnpj': ''}, 'dia_fechamento': DIA_FECHAMENTO_PADRAO, 'fechamento_automatico': True, 'hora_envio': '08:00', 'ultimo_fechamento': '', 'bot': {'ativo': False, 'token': '', 'offset': 0, 'destinatarios': [], 'chats': {}, 'ultima_verificacao': None, 'ultimo_erro': None}}
```

## `app/empresas/entrada.py`

```python
INTERVALO = 45

TAMANHO_MAXIMO = 20 * 1024 * 1024

EXTENSOES = ('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.xml')

MAX_ITENS = 300

DIAS_MANTER_CONCLUIDOS = 30
```

## `app/empresas/leitura.py`

```python
MAX_PAGINAS = 5

UNIDADES = ('M3', 'M³', 'MC', 'TON', 'TN', 'KG', 'UN', 'UND', 'PC', 'PÇ', 'SC', 'LT', 'L', 'MT', 'M', 'CX', 'H', 'HR')

RE_UNIDADE = re.compile('\\b(M\\s?3|M³|MC|TON|TN|KG|UND?|PC|PÇ|SC|LT|MT|CX|HR?|L|M)\\b', re.I)

RE_NUMERO = re.compile('(?<![\\d,.])(\\d{1,3}(?:\\.\\d{3})*(?:,\\d+)?|\\d+(?:[.,]\\d+)?)(?![\\d])')

RE_NF = re.compile('\\b(?:nfe?|nf-?e|nota\\s*fiscal|nota|cupom)\\s*(?:n[ºo°.]?\\s*)?[:\\-]?\\s*(\\d{1,9})', re.I)

RE_PEDIDO = re.compile('\\b(?:pedido|ped\\.?|pdd|oc)\\s*(?:n[ºo°.]?\\s*)?[:\\-]?\\s*(\\d{1,9})', re.I)

RE_CMC7 = re.compile('(?<!\\d)(\\d{8})\\D{0,4}(\\d{10})\\D{0,4}(\\d{12})(?!\\d)')

RE_CMC7_CORRIDO = re.compile('(?<!\\d)(\\d{30})(?!\\d)')

RE_DEPOSITO_DE_CHEQUE = re.compile('deposito[^.\\n]{0,40}cheque|cheques?\\s+depositad|comprovante de deposito|valor do deposito|deposito (em|com) cheque')

BANCOS = {'001': 'Banco do Brasil', '003': 'Banco da Amazônia', '004': 'Banco do Nordeste', '021': 'Banestes', '033': 'Santander', '037': 'Banpará', '041': 'Banrisul', '047': 'Banese', '070': 'BRB', '077': 'Banco Inter', '085': 'Ailos', '097': 'Credisis', '099': 'Uniprime', '104': 'Caixa Econômica Federal', '133': 'Cresol', '136': 'Unicred', '212': 'Banco Original', '237': 'Bradesco', '246': 'ABC Brasil', '260': 'Nubank', '290': 'PagBank', '318': 'Banco BMG', '336': 'C6 Bank', '341': 'Itaú', '356': 'Real', '389': 'Mercantil', '399': 'HSBC', '422': 'Safra', '604': 'Banco Industrial', '633': 'Rendimento', '637': 'Sofisa', '652': 'Itaú Unibanco', '655': 'Votorantim', '745': 'Citibank', '748': 'Sicredi', '756': 'Sicoob'}

SINAIS_NOTA = ('danfe', 'documento auxiliar da nota fiscal', 'nota fiscal eletronica', 'chave de acesso', 'natureza da operacao', 'dados do produto', 'destinatario/remetente', 'valor total da nota', 'protocolo de autorizacao', 'inscricao estadual')

SINAIS_CHEQUE = ('compensavel', 'compense', 'cheque', 'pague por este cheque', 'quantia de', 'ordem de', 'banco cooperativo', 'acima ou a sua ordem', 'c1', 'bom para')

SINAIS_COMPROVANTE = ('comprovante', 'transferencia', 'pix', 'ted', 'doc', 'deposito', 'valor pago', 'id da transacao', 'autenticacao', 'e2e', 'recibo')

SINAIS_FECHAMENTO = ('fechamento', 'valor uni', 'valor total', 'n pedido', 'nota fical', 'nota fiscal', 'material')

RE_SO_ROTULO = re.compile('^(nome|razao social|nome/razao social|cnpj|cpf|cnpj/cpf|endereco|municipio|uf|fone|fax|bairro|distrito|cep|inscricao estadual|data da emissao|data de emissao|destinatario.*|identificacao do emitente|natureza da operacao|hora de saida|data de saida)\\W*$')

RE_MOEDA_TOLERANTE = re.compile('(?<![\\d,.])(\\d{1,3}(?:[.\\s]\\d{3})*|\\d+)[.,](\\d{2})(?![\\d])')

CONFUSOES_OCR = str.maketrans({'o': '0', 'O': '0', 'l': '1', 'I': '1', 'S': '5', 's': '5', 'B': '8', 'Z': '2'})

DISTANCIA_ENTRE_PEDIDOS = 200

RE_CNPJ_SOLTO = re.compile('(?<!\\d)\\d{2}[.\\s]?\\d{3}[.\\s]?\\d{3}[/\\s]?\\d{4}[-–\\s]?\\d{2}(?!\\d)')

RE_RAZAO_SOCIAL = re.compile('([A-ZÀ-Ý][A-Za-zÀ-ý&.\\-]{1,20}(?:\\s+[A-Za-zÀ-ý&.\\-]{1,20}){0,5}\\s+(?:LTDA|EIRELI|EPP|S/?A|ME)\\b)', re.I)

PALAVRAS_DE_BANCO = ('banco', 'sicredi', 'sicoob', 'coop', 'credito', 'cred ', 'caixa', 'bradesco', 'itau', 'santander', 'cliente bancario')

RE_LINHA_FECHAMENTO = re.compile('^(?P<data>\\d{1,2}\\s?/\\s?\\d{1,2}\\s?/\\s?\\d{2,4})\\s+(?P<material>.+?)\\s+(?P<unidade>M\\s?[3³]|MC|TON|TN|KG|UND?|PC|SC|LT|CX)\\s+(?P<quantidade>[\\d.,]+)\\s+(?P<unitario>[\\d.,]+)\\s+R?\\$?\\s*(?P<total>[\\d.,]+)\\s+(?P<nf>\\d{2,9})\\s+(?P<pedido>\\d{2,9})\\s*$', re.I)
```

## `app/empresas/modelos.py`

```python
COR_EMPRESAS = '1F5FA8'

COR_NOTAS = '0F3D3E'

COR_CHEQUES = '6B3FA0'

COR_RECEBIMENTOS = '1B7F4B'

DIA_FECHAMENTO_PADRAO = 20

STATUS_EMPRESA = ('Ativa', 'Inativa')

STATUS_NOTA = ('Em aberto', 'Em cheque', 'Parcial', 'Recebido', 'Cancelado')

STATUS_CHEQUE = ('Em carteira', 'Depositado', 'Compensado', 'Devolvido', 'Cancelado')

STATUS_RECEBIMENTO = ('Confirmado', 'Cancelado')

FORMAS_RECEBIMENTO = ('Pix', 'TED', 'Depósito', 'Cheque', 'Dinheiro', 'Outro')

UNIDADES = ('M³', 'TON', 'UN', 'KG', 'L', 'H', 'SC', 'PC')

COLUNAS_EMPRESAS = [Coluna('id', 'ID', 7, '0'), Coluna('nome', 'Empresa', 30), Coluna('razao_social', 'Razão Social', 40), Coluna('cnpj', 'CNPJ', 20, '@'), Coluna('apelidos', 'Outros nomes (para o robô reconhecer)', 40), Coluna('dia_fechamento', 'Dia do Fechamento', 17, '0'), Coluna('contato', 'Contato', 24), Coluna('telefone', 'Telefone', 18, '@'), Coluna('email', 'E-mail', 28), Coluna('chat_telegram', 'Chat do Telegram', 18, '@'), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 34), Coluna('data_lancamento', 'Cadastrada em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Cadastrada por', 20), Coluna('atualizado_em', 'Atualizada em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_NOTAS = [Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('empresa', 'Empresa', 28), Coluna('material', 'Material', 28), Coluna('unidade', 'Unidade', 10), Coluna('quantidade', 'Quantidade', 12, '#,##0.###'), Coluna('valor_unitario', 'Valor Unitário (R$)', 17, '"R$" #,##0.00'), Coluna('valor_total', 'Valor Total (R$)', 16, '"R$" #,##0.00'), Coluna('numero_nf', 'Nota Fiscal', 13, '@'), Coluna('pedido', 'Nº do Pedido', 14, '@'), Coluna('competencia', 'Fechamento', 12, '@'), Coluna('status', 'Situação', 12), Coluna('valor_recebido', 'Valor Recebido (R$)', 17, '"R$" #,##0.00'), Coluna('data_recebimento', 'Recebido em', 13, 'dd/mm/yyyy'), Coluna('cheque_id', 'Cheque (ID)', 11, '0'), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Arquivo', 28), Coluna('arquivo_nome', 'Nome do Arquivo Original', 30), Coluna('data_lancamento', 'Lançada em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Lançada por', 20), Coluna('atualizado_em', 'Atualizada em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_CHEQUES = [Coluna('id', 'ID', 7, '0'), Coluna('empresa', 'Empresa', 28), Coluna('numero', 'Nº do Cheque', 14, '@'), Coluna('vencimento', 'Bom para', 12, 'dd/mm/yyyy'), Coluna('valor', 'Valor (R$)', 15, '"R$" #,##0.00'), Coluna('banco', 'Banco', 24), Coluna('agencia', 'Agência', 11, '@'), Coluna('coop', 'Cooperativa', 13, '@'), Coluna('conta', 'Conta', 16, '@'), Coluna('emitente', 'Emitente', 30), Coluna('pedidos', 'Pedidos', 22, '@'), Coluna('notas', 'Notas Fiscais', 22, '@'), Coluna('status', 'Situação', 13), Coluna('data_deposito', 'Depositado em', 14, 'dd/mm/yyyy'), Coluna('cmc7', 'CMC7 (linha do cheque)', 34, '@'), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Arquivo', 28), Coluna('arquivo_nome', 'Nome do Arquivo Original', 30), Coluna('data_lancamento', 'Lançado em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Lançado por', 20), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_RECEBIMENTOS = [Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 9, '@'), Coluna('empresa', 'Empresa', 28), Coluna('forma', 'Forma', 12), Coluna('valor', 'Valor (R$)', 15, '"R$" #,##0.00'), Coluna('pagador', 'Pagador', 32), Coluna('id_transacao', 'ID da Transação', 34, '@'), Coluna('notas', 'Notas Fiscais', 24, '@'), Coluna('pedidos', 'Pedidos', 22, '@'), Coluna('cheque_id', 'Cheque (ID)', 11, '0'), Coluna('aplicacoes', 'Baixas (nota: valor)', 40), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Comprovante', 28), Coluna('arquivo_nome', 'Nome do Comprovante', 30), Coluna('data_lancamento', 'Registrado em', 19, 'dd/mm/yyyy hh:mm'), Coluna('lancado_por', 'Registrado por', 20), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

_TEXTOS_COMUNS = frozenset({'observacoes', 'arquivo', 'arquivo_nome', 'lancado_por'})

ABAS_EMPRESAS = {'empresas': DefinicaoAba('empresas', 'Empresas', tuple(COLUNAS_EMPRESAS), frozenset({'nome', 'razao_social', 'cnpj', 'apelidos', 'dia_fechamento', 'contato', 'telefone', 'email', 'chat_telegram', 'status', 'observacoes'}), 'nome', frozenset({'nome', 'razao_social', 'cnpj', 'apelidos', 'contato', 'telefone', 'email', 'chat_telegram'}) | _TEXTOS_COMUNS, COR_EMPRESAS, ' (Empresa)', STATUS_EMPRESA, '', '', 'Inativa'), 'notas': DefinicaoAba('notas', 'Notas Fiscais', tuple(COLUNAS_NOTAS), frozenset({'data', 'empresa', 'material', 'unidade', 'quantidade', 'valor_unitario', 'valor_total', 'numero_nf', 'pedido', 'competencia', 'status', 'valor_recebido', 'data_recebimento', 'cheque_id', 'observacoes', 'arquivo', 'arquivo_nome'}), 'empresa', frozenset({'empresa', 'material', 'unidade', 'numero_nf', 'pedido', 'competencia'}) | _TEXTOS_COMUNS, COR_NOTAS, ' (NF)', STATUS_NOTA, 'data', 'Recebido', 'Cancelado'), 'cheques': DefinicaoAba('cheques', 'Cheques', tuple(COLUNAS_CHEQUES), frozenset({'empresa', 'numero', 'vencimento', 'valor', 'banco', 'agencia', 'coop', 'conta', 'emitente', 'pedidos', 'notas', 'status', 'data_deposito', 'cmc7', 'observacoes', 'arquivo', 'arquivo_nome'}), 'empresa', frozenset({'empresa', 'numero', 'banco', 'agencia', 'coop', 'conta', 'emitente', 'pedidos', 'notas', 'cmc7'}) | _TEXTOS_COMUNS, COR_CHEQUES, ' (Cheque)', STATUS_CHEQUE, 'vencimento', 'Compensado', 'Cancelado'), 'recebimentos': DefinicaoAba('recebimentos', 'Recebimentos', tuple(COLUNAS_RECEBIMENTOS), frozenset({'data', 'hora', 'empresa', 'forma', 'valor', 'pagador', 'id_transacao', 'notas', 'pedidos', 'cheque_id', 'aplicacoes', 'status', 'observacoes', 'arquivo', 'arquivo_nome'}), 'empresa', frozenset({'empresa', 'forma', 'pagador', 'id_transacao', 'notas', 'pedidos', 'hora', 'aplicacoes'}) | _TEXTOS_COMUNS, COR_RECEBIMENTOS, ' (Recebimento)', STATUS_RECEBIMENTO, 'data', 'Confirmado', 'Cancelado')}
```

## `app/empresas/relatorio.py`

```python
COLUNAS = [('DATA', 13), ('MATERIAL', 26), ('UNIDADE', 11), ('QUANT.', 10), ('VALOR UNI.', 13), ('VALOR TOTAL', 15), ('NOTA FISCAL', 13), ('Nº PEDIDO', 12)]

VERDE = 'E2EFDA'

VERDE_FORTE = 'C6E0B4'

AZUL = '1F4E79'

MOEDA = '"R$" #,##0.00'

LINHAS_EM_BRANCO = 7
```

## `app/empresas/servico.py`

```python
TOLERANCIA = 0.01

ABERTAS = ('Em aberto', 'Em cheque', 'Parcial')
```

## `app/entrada.py`

```python
MASCARA = '••••••••'

INTERVALO_EMAIL = 300

INTERVALO_TELEGRAM = 45

DIAS_PRIMEIRA_LEITURA = 7

MAX_EMAILS_POR_VEZ = 40

MAX_ITENS = 300

DIAS_MANTER_CONCLUIDOS = 30

TAMANHO_MINIMO_IMAGEM = 15000

TAMANHO_MAXIMO = 20 * 1024 * 1024

EXTENSOES = ('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.bmp', '.tif', '.tiff')

PADRAO = {'itens': [], 'email': {'ativo': False, 'servidor': '', 'porta': 993, 'usuario': '', 'senha': '', 'pasta': 'INBOX', 'remetentes': '', 'uidvalidity': None, 'ultimo_uid': None, 'ultima_verificacao': None, 'ultimo_erro': None}, 'telegram': {'ativo': False, 'offset': None, 'ultima_verificacao': None, 'ultimo_erro': None, 'chats': {}}}
```

## `app/fechamento.py`

```python
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

SEM_CENTRO = 'Sem centro de custo'

MOEDA = '"R$" #,##0.00'

COR = '0F3D3E'
```

## `app/fila_gravacao.py`

```python
INTERVALO_TENTATIVAS = 15
```

## `app/ia.py`

```python
CAMPOS = ('linha_digitavel', 'beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor', 'observacoes')

ESQUEMA = {'type': 'object', 'properties': {'linha_digitavel': {'type': 'string', 'description': 'Somente dígitos; vazio se ilegível'}, 'beneficiario': {'type': 'string'}, 'documento_beneficiario': {'type': 'string'}, 'numero_documento': {'type': 'string'}, 'vencimento': {'type': 'string', 'description': 'AAAA-MM-DD ou vazio'}, 'valor': {'type': 'string', 'description': 'Número com ponto decimal, ex.: 1500.75, ou vazio'}, 'observacoes': {'type': 'string'}}, 'required': list(CAMPOS), 'additionalProperties': False}

INSTRUCOES = 'Você está lendo um boleto brasileiro (PDF ou foto). Transcreva exatamente o que está impresso:\n\n- linha_digitavel: a linha digitável (47 dígitos em boletos bancários; 48 em contas de consumo e tributos, que começam com 8). Retorne somente os dígitos. Se só houver o número do código de barras (44 dígitos), use-o.\n- beneficiario: nome ou razão social de quem recebe o pagamento (campo "Beneficiário" ou "Cedente"), sem CPF/CNPJ. Não confunda com o Pagador.\n- documento_beneficiario: CPF ou CNPJ do beneficiário, formatado (ex.: 12.345.678/0001-95).\n- numero_documento: o campo "Nº do Documento" (não confundir com "Nosso Número").\n- vencimento: a data de vencimento no formato AAAA-MM-DD.\n- valor: o valor do documento, com ponto como separador decimal (ex.: 1500.75).\n- observacoes: no máximo uma frase curta sobre algo que atrapalhou a leitura; vazio se nada.\n\nUse string vazia para qualquer campo que não esteja legível. Nunca invente ou complete dígitos que você não consegue ver.'
```

## `app/importacao.py`

```python
MAX_LINHAS = 5000

MAX_COLUNAS = 80

LINHAS_BUSCA_CABECALHO = 30

HORAS_GUARDAR_ARQUIVOS = 24

CAMPOS = [{'chave': 'linha_digitavel', 'rotulo': 'Linha digitável / código de barras'}, {'chave': 'beneficiario', 'rotulo': 'Beneficiário / fornecedor'}, {'chave': 'documento_beneficiario', 'rotulo': 'CPF/CNPJ do beneficiário'}, {'chave': 'numero_documento', 'rotulo': 'Nº do documento'}, {'chave': 'vencimento', 'rotulo': 'Vencimento'}, {'chave': 'valor', 'rotulo': 'Valor'}, {'chave': 'status', 'rotulo': 'Situação (pago / em aberto)'}, {'chave': 'data_pagamento', 'rotulo': 'Data de pagamento'}, {'chave': 'centro_custo', 'rotulo': 'Centro de custo'}, {'chave': 'observacoes', 'rotulo': 'Observações'}]

CHAVES_CAMPOS = [c['chave'] for c in CAMPOS]

APELIDOS = {'linha_digitavel': ['linha digitavel', 'codigo de barras', 'codigo barras', 'cod barras', 'cod de barras', 'barras', 'linha', 'codigo do boleto', 'representacao numerica', 'ld', 'barcode', 'linha digitavel boleto'], 'beneficiario': ['beneficiario', 'nome do beneficiario', 'cedente', 'fornecedor', 'nome do fornecedor', 'nome fornecedor', 'favorecido', 'credor', 'razao social', 'emitente', 'empresa', 'sacador avalista', 'nome'], 'documento_beneficiario': ['cpf cnpj', 'cnpj cpf', 'cnpj', 'cpf', 'cnpj do beneficiario', 'cnpj fornecedor', 'cnpj do fornecedor', 'documento do beneficiario', 'cpf cnpj fornecedor'], 'numero_documento': ['numero do documento', 'numero documento', 'n do documento', 'no do documento', 'n documento', 'no documento', 'num documento', 'nro documento', 'documento', 'doc', 'nota fiscal', 'nf', 'numero nf', 'titulo', 'numero do titulo', 'duplicata', 'fatura'], 'vencimento': ['vencimento', 'data de vencimento', 'data vencimento', 'dt vencimento', 'dt venc', 'data venc', 'venc', 'vencto', 'dt vencto', 'vencimento original'], 'valor': ['valor', 'valor do documento', 'valor documento', 'valor do titulo', 'valor titulo', 'valor original', 'valor a pagar', 'valor boleto', 'valor do boleto', 'valor liquido', 'valor total', 'vlr', 'vlr documento', 'vl documento', 'vlr titulo', 'vl titulo', 'total'], 'status': ['status', 'situacao', 'situacao do titulo', 'estado', 'pago', 'quitado'], 'data_pagamento': ['data de pagamento', 'data pagamento', 'dt pagamento', 'dt pagto', 'data pagto', 'pagamento', 'data da baixa', 'data baixa', 'dt baixa', 'baixa', 'pago em', 'data liquidacao', 'liquidacao'], 'centro_custo': ['centro de custo', 'centro custo', 'c custo', 'cc', 'departamento', 'setor', 'obra', 'projeto', 'unidade', 'filial'], 'observacoes': ['observacoes', 'observacao', 'obs', 'historico', 'descricao', 'complemento', 'memo']}

EXCLUIR = {'linha_digitavel': {'nosso'}, 'beneficiario': {'sacado', 'pagador', 'cpf', 'cnpj', 'banco', 'conta'}, 'documento_beneficiario': {'numero', 'nosso'}, 'numero_documento': {'cpf', 'cnpj', 'nosso', 'banco'}, 'vencimento': {'pagamento', 'pagto'}, 'valor': {'juros', 'multa', 'desconto', 'abatimento', 'acrescimo', 'acrescimos', 'pago', 'mora', 'encargos'}, 'status': {'valor', 'data', 'dt'}, 'data_pagamento': {'valor', 'vencimento', 'forma', 'banco', 'conta', 'vlr'}}

MESES = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}

FORMATOS = {'xlsx': 'Excel', 'xls': 'Excel 97-2003', 'html': 'Excel (HTML)', 'csv': 'CSV / texto'}

RE_DATA_ISO = re.compile('^\\s*(\\d{4})-(\\d{1,2})-(\\d{1,2})')

RE_DATA_BR = re.compile('^\\s*(\\d{1,2})[/.\\-](\\d{1,2})[/.\\-](\\d{2,4})(?:[\\sT]|$)')

RE_DATA_MES = re.compile('^\\s*(\\d{1,2})[/\\-\\s]+(?:de\\s+)?([a-z]{3})[a-z]*[/\\-\\s]+(?:de\\s+)?(\\d{2,4})')
```

## `app/inicializacao.py`

```python
NOME_ARQUIVO = f'{config.NOME_APP}.vbs'

NOMES_ANTIGOS = ('Leitor de Boletos.vbs',)

ARGUMENTO_BANDEJA = '--bandeja'
```

## `app/notificacoes/canais.py`

```python
_SCRIPT_TOAST = "\n$ErrorActionPreference = 'Stop'\n[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n$xml.LoadXml($env:LEITOR_TOAST_XML)\n$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)\n$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'\n[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)\n"

TIPOS_CHAT = {'private': 'privado', 'group': 'grupo', 'supergroup': 'grupo', 'channel': 'canal'}
```

## `app/notificacoes/regras.py`

```python
DIAS_SEMANA = ('segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo')

ORDEM_CATEGORIA = {'vencido': 0, 'hoje': 1, 'amanha': 2, 'proximos': 3}

EMOJI_CATEGORIA = {'vencido': '🔴', 'hoje': '🟠', 'amanha': '🟡', 'proximos': '🔵'}

LIMITE_TELEGRAM = 3900
```

## `app/notificacoes/servico.py`

```python
MASCARA = '••••••••'

CANAIS = ('windows', 'telegram', 'email')

TIPOS_REGRA = ('vencimento', 'antes', 'vencidos')

INTERVALO_VERIFICACAO = 60

ESPERA_APOS_FALHA = timedelta(minutes=15)

LIMITE_REGRAS = 20

LIMITE_HORARIOS = 12

_SEGREDOS = {('telegram', 'token'), ('email', 'senha')}

REGRAS_PADRAO = [{'id': 'vencimento', 'tipo': 'vencimento', 'dias': 0, 'horarios': ['08:00', '12:00', '16:00'], 'canais': list(CANAIS), 'ativo': True}, {'id': 'vespera', 'tipo': 'antes', 'dias': 1, 'horarios': ['09:00'], 'canais': list(CANAIS), 'ativo': True}, {'id': 'antecedencia', 'tipo': 'antes', 'dias': 3, 'horarios': ['09:00'], 'canais': list(CANAIS), 'ativo': True}, {'id': 'vencidos', 'tipo': 'vencidos', 'dias': 30, 'horarios': ['09:00'], 'canais': list(CANAIS), 'ativo': True}]

TIPOS_RESUMO = ('segunda', 'sexta')

DIA_RESUMO = {'segunda': 0, 'sexta': 4}

RESUMOS_PADRAO = {'segunda': {'ativo': True, 'horario': '08:00', 'canais': ['telegram', 'email']}, 'sexta': {'ativo': True, 'horario': '17:00', 'canais': ['telegram', 'email']}}

PADRAO = {'ativo': True, 'resumos': RESUMOS_PADRAO, 'dias_semana': [0, 1, 2, 3, 4, 5, 6], 'regras': REGRAS_PADRAO, 'windows': {'ativo': True}, 'telegram': {'ativo': False, 'token': '', 'chat_id': '', 'destinatarios': []}, 'email': {'ativo': False, 'servidor': '', 'porta': 587, 'seguranca': 'starttls', 'usuario': '', 'senha': '', 'remetente': '', 'destinatarios': ''}}

RE_CHAT_TELEGRAM = re.compile('^-?\\d{1,20}$')

LIMITE_DESTINATARIOS = 50
```

## `app/pix.py`

```python
TIPOS_CHAVE = {'cpf_cnpj': 'CNPJ/CPF', 'celular': 'Celular', 'email': 'E-mail', 'aleatoria': 'Aleatória'}

RE_EMAIL = re.compile('^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$')

RE_UUID = re.compile('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

RE_COPIA_E_COLA = re.compile('000201[\\x20-\\x7E]*?6304[0-9A-Fa-f]{4}')
```

## `app/planilha.py`

```python
ABA_BOLETOS = 'Boletos'

ABA_PIX = 'Pix'

ABA_RESUMO = 'Resumo'

ABA_CENTROS = 'Centros de Custo'

ABA_HISTORICO = 'Histórico'

ABA_CAIXA = 'Caixa'

COLUNAS_HISTORICO = [('Data/Hora', 18), ('Ação', 18), ('ID', 7), ('Beneficiário / Recebedor', 40), ('Vencimento', 13), ('Valor (R$)', 14), ('Detalhes', 60), ('Usuário', 22)]

STATUS_VALIDOS = ('Pendente', 'Pago', 'Cancelado')

TIPOS = {'bancario': 'Bancário', 'arrecadacao': 'Arrecadação'}

TIPOS_CHAVE = {'cpf_cnpj': 'CNPJ/CPF', 'celular': 'Celular', 'email': 'E-mail', 'aleatoria': 'Aleatória'}

ROTULOS = {'tipo': TIPOS, 'tipo_chave': TIPOS_CHAVE}

LINHAS_FORMATADAS = 20000

BACKUPS_MANTIDOS = 30

COR_CABECALHO = '0F3D3E'

COR_FAIXA = 'F3F7F7'

CENTROS_PADRAO = [('Administrativo', 'Escritório, contabilidade, bancos e despesas gerais'), ('Produção', 'Matéria-prima, insumos e serviços da produção'), ('Obras', 'Materiais e serviços aplicados em obras'), ('Combustível e Veículos', 'Combustível, lubrificantes, peças e manutenção da frota'), ('Manutenção', 'Máquinas, equipamentos e instalações'), ('Impostos e Taxas', 'Tributos, guias e taxas'), ('Energia, Água e Telefone', 'Contas de consumo'), ('Pessoal', 'Salários, benefícios e encargos'), ('Outros', '')]

COLUNAS = [Coluna('id', 'ID', 7, '0'), Coluna('data_lancamento', 'Data de Lançamento', 19, 'dd/mm/yyyy hh:mm'), Coluna('linha_digitavel', 'Linha Digitável', 58, '@'), Coluna('codigo_barras', 'Código de Barras', 48, '@'), Coluna('beneficiario', 'Beneficiário', 42), Coluna('documento_beneficiario', 'CPF/CNPJ Beneficiário', 21, '@'), Coluna('numero_documento', 'Nº do Documento', 18, '@'), Coluna('vencimento', 'Vencimento', 13, 'dd/mm/yyyy'), Coluna('valor', 'Valor (R$)', 15, '"R$" #,##0.00'), Coluna('emissor', 'Banco / Segmento', 26), Coluna('tipo', 'Tipo', 13), Coluna('status', 'Status', 12), Coluna('data_pagamento', 'Data de Pagamento', 17, 'dd/mm/yyyy'), Coluna('valor_pago', 'Valor Pago (R$)', 15, '"R$" #,##0.00'), Coluna('juros_multa', 'Juros/Multa (R$)', 15, '"R$" #,##0.00'), Coluna('desconto', 'Desconto (R$)', 14, '"R$" #,##0.00'), Coluna('observacoes', 'Observações', 34), Coluna('centro_custo', 'Centro de Custo', 26), Coluna('arquivo', 'Arquivo', 30), Coluna('arquivo_nome', 'Nome do Arquivo Original', 32), Coluna('lancado_por', 'Lançado por', 20), Coluna('pago_por', 'Pago por', 20), Coluna('comprovante', 'Comprovante', 30), Coluna('comprovante_nome', 'Nome do Comprovante', 30), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

COLUNAS_PIX = [Coluna('id', 'ID', 7, '0'), Coluna('data_lancamento', 'Data de Lançamento', 19, 'dd/mm/yyyy hh:mm'), Coluna('recebedor', 'Recebedor', 38), Coluna('tipo_chave', 'Tipo da Chave', 14), Coluna('chave', 'Chave Pix', 38, '@'), Coluna('valor', 'Valor (R$)', 15, '"R$" #,##0.00'), Coluna('vencimento', 'Data Prevista', 14, 'dd/mm/yyyy'), Coluna('centro_custo', 'Centro de Custo', 26), Coluna('descricao', 'Descrição', 36), Coluna('status', 'Status', 12), Coluna('data_pagamento', 'Data de Pagamento', 17, 'dd/mm/yyyy'), Coluna('valor_pago', 'Valor Pago (R$)', 15, '"R$" #,##0.00'), Coluna('juros_multa', 'Juros/Multa (R$)', 15, '"R$" #,##0.00'), Coluna('desconto', 'Desconto (R$)', 14, '"R$" #,##0.00'), Coluna('txid', 'Identificador (TXID)', 24, '@'), Coluna('copia_e_cola', 'Pix Copia e Cola', 40, '@'), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Arquivo', 28), Coluna('arquivo_nome', 'Nome do Arquivo Original', 30), Coluna('lancado_por', 'Lançado por', 20), Coluna('pago_por', 'Pago por', 20), Coluna('comprovante', 'Comprovante', 28), Coluna('comprovante_nome', 'Nome do Comprovante', 30), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

CAMPOS_DATA = {'vencimento', 'data_pagamento', 'data', 'data_deposito', 'data_recebimento', 'data_fechamento'}

CAMPOS_DATA_HORA = {'data_lancamento', 'atualizado_em', 'data_hora'}

CAMPOS_NUMERO = {'quantidade', 'litros', 'medidor', 'preco_litro'}

COLUNAS_CAIXA = [Coluna('id', 'ID', 7, '0'), Coluna('data', 'Data', 12, 'dd/mm/yyyy'), Coluna('hora', 'Hora', 8, '@'), Coluna('movimento', 'Entrada/Saída', 13), Coluna('valor', 'Valor (R$)', 15, '"R$" #,##0.00'), Coluna('descricao', 'O que foi pedido / comprado', 40), Coluna('local', 'Onde foi gasto', 30), Coluna('centro_custo', 'Centro de Custo', 26), Coluna('pessoa', 'Quem', 20), Coluna('status', 'Situação', 12), Coluna('observacoes', 'Observações', 30), Coluna('arquivo', 'Comprovante', 28), Coluna('arquivo_nome', 'Nome do Comprovante', 30), Coluna('lancado_por', 'Lançado por', 20), Coluna('data_lancamento', 'Data de Lançamento', 19, 'dd/mm/yyyy hh:mm'), Coluna('atualizado_em', 'Atualizado em', 19, 'dd/mm/yyyy hh:mm')]

MOVIMENTOS_CAIXA = ('Entrada', 'Saída')

CAMPOS_AUTORIA = frozenset({'lancado_por', 'pago_por'})

CAMPOS_COMPROVANTE = frozenset({'comprovante', 'comprovante_nome'})

TEXTOS_COMUNS = CAMPOS_AUTORIA | CAMPOS_COMPROVANTE

CAMPOS_PAGAMENTO = frozenset({'valor_pago', 'juros_multa', 'desconto'})

CAMPOS_MOEDA = {'valor', 'valor_unitario', 'valor_total', 'valor_recebido'} | CAMPOS_PAGAMENTO

ABAS = {'boletos': DefinicaoAba('boletos', ABA_BOLETOS, tuple(COLUNAS), frozenset({'linha_digitavel', 'codigo_barras', 'beneficiario', 'documento_beneficiario', 'numero_documento', 'vencimento', 'valor', 'emissor', 'tipo', 'status', 'data_pagamento', 'observacoes', 'centro_custo', 'arquivo', 'arquivo_nome'}) | CAMPOS_COMPROVANTE | CAMPOS_PAGAMENTO, 'beneficiario', frozenset({'beneficiario', 'observacoes', 'numero_documento', 'centro_custo'}) | TEXTOS_COMUNS, COR_CABECALHO, ''), 'pix': DefinicaoAba('pix', ABA_PIX, tuple(COLUNAS_PIX), frozenset({'recebedor', 'tipo_chave', 'chave', 'valor', 'vencimento', 'centro_custo', 'descricao', 'status', 'data_pagamento', 'txid', 'copia_e_cola', 'observacoes', 'arquivo', 'arquivo_nome'}) | CAMPOS_COMPROVANTE | CAMPOS_PAGAMENTO, 'recebedor', frozenset({'recebedor', 'descricao', 'observacoes', 'centro_custo', 'txid'}) | TEXTOS_COMUNS, '1F5FA8', ' (Pix)')}

COLUNA_POR_CHAVE = ABAS['boletos'].por_chave

CAMPOS_EDITAVEIS = set(ABAS['boletos'].editaveis)
```

## `app/preferencias.py`

```python
PADRAO = {'fechar_para_bandeja': True, 'minimizado_ao_iniciar': False, 'aviso_bandeja_mostrado': False}
```

## `app/rede.py`

```python
ITERACOES_HASH = 200000

TAMANHO_MINIMO_SENHA = 6

INTERVALO_VIGIA = 60

MAX_ACESSOS_REGISTRADOS = 30
```

## `app/registro_log.py`

```python
TAMANHO_MAXIMO = 2 * 1024 * 1024

ARQUIVOS_ANTIGOS = 5
```

## `app/relatorio_geral.py`

```python
MESES_HISTORICO = 12

MOEDA = '"R$" #,##0.00'

COR = '0F3D3E'
```

## `app/resumo_semanal.py`

```python
TIPOS = ('segunda', 'sexta')

DIA_DO_TIPO = {'segunda': 0, 'sexta': 4}

LIMITE_ITENS = 12

DIAS_CURTOS = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')
```

## `app/rotas/boletos.py`

```python
SEM_PAGAMENTO = {'data_pagamento': None, 'valor_pago': None, 'juros_multa': None, 'desconto': None}
```

## `app/rotas/comprovantes.py`

```python
TIPOS = ('boletos', 'pix')
```

## `app/rotas/comum.py`

```python
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

SOMENTE_ADMIN = [Depends(exigir_admin)]
```

## `app/rotas/diesel.py`

```python
MOEDA = '"R$" #,##0.00'

LITROS = '#,##0.0 "L"'
```

## `app/rotas/empresas.py`

```python
PDF = 'application/pdf'
```

## `app/rotas/gastos.py`

```python
ROTULO_CAMPO_DATA = {'vencimento': 'vencimento', 'data_pagamento': 'pagamento', 'data_lancamento': 'lançamento'}
```

## `app/rotas/sistema.py`

```python
RE_ROTA = re.compile('^[a-z]+(\\?[A-Za-z0-9_=&%.,\\-]*)?$')
```

## `app/saude.py`

```python
INICIADO_EM = datetime.now()

ORDEM = {'erro': 0, 'aviso': 1, 'ok': 2, 'desligado': 3}

NOMES_CANAIS = {'windows': 'Windows', 'telegram': 'Telegram', 'email': 'e-mail'}
```

## `app/servico_comprovante.py`

```python
ABAS = {'boletos': 'repositorio', 'pix': 'repositorio_pix'}
```

## `app/servicos.py`

```python
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

SITUACOES = ('vencido', 'vence_hoje', 'a_vencer', 'pendente', 'pago', 'cancelado')

SEM_CENTRO = 'Sem centro de custo'

OUTROS_CENTROS = 'Outros centros'

CAMPOS_BUSCA_BOLETOS = ('beneficiario', 'numero_documento', 'documento_beneficiario', 'observacoes', 'emissor', 'linha_digitavel', 'centro_custo')

CAMPOS_DIGITOS_BOLETOS = ('codigo_barras', 'linha_digitavel')

CAMPOS_BUSCA_PIX = ('recebedor', 'chave', 'descricao', 'observacoes', 'centro_custo', 'txid')

CAMPOS_DIGITOS_PIX = ('chave',)

_ROTULO_SITUACAO = {'vencido': 'Vencido', 'vence_hoje': 'Vence hoje', 'a_vencer': 'A vencer', 'pendente': 'Pendente', 'pago': 'Pago', 'cancelado': 'Cancelado'}
```

## `app/tarefas.py`

```python
DESCRICOES = {'na_fila': 'Na fila', 'iniciando': 'Preparando o arquivo', 'codigo_barras': 'Lendo o código de barras', 'ocr': 'Reconhecendo o texto (OCR)', 'concluindo': 'Conferindo os dados', 'concluida': 'Concluída', 'erro': 'Falhou'}

_PESO_ETAPA = {'iniciando': 0.0, 'codigo_barras': 0.15, 'ocr': 0.35, 'concluindo': 1.0}
```

## `app/usuarios.py`

```python
COOKIE = 'leitor_usuario'

VALIDADE_SESSAO = 30 * 24 * 3600

ITERACOES = 200000

TAMANHO_MINIMO_SENHA = 6

MAX_TENTATIVAS = 5

BLOQUEIO_SEGUNDOS = 300

LIMITE_USUARIOS = 100

RE_LOGIN = re.compile('^[a-z0-9._-]{2,40}$')

PERFIS = ('administrador', 'comum')

PERMISSOES = {'lancar': 'Lançar boletos e Pix (ler arquivos e cadastrar)', 'pagar': 'Dar baixa: marcar como pago e anexar comprovante', 'editar': 'Editar e excluir lançamentos', 'gastos': 'Ver os gastos e gerar o fechamento do mês', 'empresas': 'Empresas: notas fiscais, cheques e recebimentos', 'caixa': 'Caixa: entradas e saídas em dinheiro', 'diesel': 'Diesel: compras, abastecimentos das máquinas e relatórios', 'notificacoes': 'Configurar os avisos de vencimento', 'config': 'Configurações do sistema (backup, bots, importação, rede)'}

PERMISSOES_PADRAO = ('lancar', 'pagar')
```

## `app/versao.py`

```python
ARQUIVO_HISTORICO = 'VERSOES.md'

ARQUIVO_VERSAO = Path('app') / '__init__.py'

RE_VERSAO = re.compile('^(\\d+)\\.(\\d+)\\.(\\d+)$')

RE_TITULO = re.compile('^## v(\\d+\\.\\d+\\.\\d+) — (\\d{2})/(\\d{2})/(\\d{4}) — (.+?)\\s*$')

RE_LINHA_VERSAO = re.compile('^__version__\\s*=\\s*"[^"]*"\\s*$', re.M)

TIPOS = {'correcao': 2, 'melhoria': 1, 'grande': 0}

VALIDADE_CACHE = 30

TEMPO_GIT = 20
```

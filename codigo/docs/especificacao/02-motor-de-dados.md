# 02 — Motor de dados (banco SQLite + planilha Excel)

Os três bancos do sistema (`boletos.db`, `empresas.db`, `diesel.db`) usam **a mesma classe**, `BancoBoletos`
(`app/banco.py`). O que muda entre eles é só o dicionário de **abas** (`DefinicaoAba`) passado na criação. Isso
permite acrescentar um módulo novo (como foi feito com Empresas e Diesel) apenas declarando as abas.

## 2.1 Histórico da decisão

1. **Começo (14/09)**: a planilha `boletos.xlsx` *era* o banco de dados (openpyxl), com gravação atômica (arquivo
   temporário + `os.replace`) e uma **fila** para quando o arquivo estava aberto no Excel.
2. **17/09**: ficou lento e travava com o Excel aberto. Virou SQLite, mas **a planilha continuou existindo** no mesmo
   formato, gerada automaticamente — e edições feitas à mão no Excel voltam para o banco.

## 2.2 Definição de uma aba (`app/planilha.py`)

```python
@dataclass(frozen=True)
class Coluna:
    chave: str          # nome do campo no registro (ex.: "valor")
    titulo: str         # cabeçalho na planilha (ex.: "Valor (R$)")
    largura: int        # largura da coluna no Excel
    formato: str | None # formato do Excel ("dd/mm/yyyy", '"R$" #,##0.00', "@" = texto...)

@dataclass(frozen=True)
class DefinicaoAba:
    chave: str                     # "boletos", "pix", "caixa", "notas", "abastecimentos"...
    nome: str                      # nome da aba na planilha
    colunas: tuple[Coluna, ...]    # ordem das colunas = ordem dos campos
    editaveis: frozenset[str]      # SÓ estes campos são gravados (o resto da entrada é ignorado!)
    campo_nome: str                # quem recebe (usado no Histórico): "beneficiario", "recebedor", "empresa"...
    textos: frozenset[str]         # campos que viram "" quando vazios
    cor: str                       # cor do cabeçalho
    sufixo_acao: str               # " (Pix)", " (Caixa)"... no texto do Histórico
    status_validos: tuple = ("Pendente", "Pago", "Cancelado")   # o primeiro é o padrão
    campo_data: str = "vencimento" # data de referência (atraso e Histórico)
    status_ok: str = "Pago"        # pintado de verde ("" = nenhum)
    status_cancelado: str = "Cancelado"  # riscado ("" = nenhum)
```

> **Armadilha real já vivida:** um campo que não está em `editaveis` é **descartado silenciosamente** ao gravar.
> Quando o diesel ganhou anexos, `arquivo`/`arquivo_nome` não estavam em `editaveis` e os arquivos sumiam.

Todas as abas, colunas, formatos e `editaveis` reais estão no anexo **A2**.

Conjuntos globais em `planilha.py` controlam a conversão de tipos: `CAMPOS_DATA` (viram `date`), `CAMPOS_DATA_HORA`
(viram `datetime`), `CAMPOS_MOEDA` (2 casas), `CAMPOS_NUMERO`. Ao criar uma aba nova com campos de data ou dinheiro,
**acrescente-os nesses conjuntos**.

## 2.3 Tabelas do SQLite (iguais nos 3 bancos)

```sql
PRAGMA journal_mode=WAL;
CREATE TABLE registros (aba TEXT NOT NULL, id INTEGER NOT NULL, dados TEXT NOT NULL, PRIMARY KEY (aba, id));
CREATE TABLE historico (seq INTEGER PRIMARY KEY AUTOINCREMENT, quando TEXT, acao TEXT, registro_id INTEGER,
                        nome TEXT, vencimento TEXT, valor REAL, detalhes TEXT, usuario TEXT);
CREATE INDEX historico_registro ON historico (registro_id);
CREATE TABLE centros (nome TEXT PRIMARY KEY COLLATE NOCASE, descricao TEXT, ativo INTEGER, criado_em TEXT, ordem INTEGER);
CREATE TABLE exportado (aba TEXT NOT NULL, id INTEGER NOT NULL, dados TEXT NOT NULL, PRIMARY KEY (aba, id));
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);   -- importado_em, planilha_mtime
```

- `registros.dados` é o registro inteiro em **JSON** (datas em ISO). Ao ler, `_do_banco` converte de volta os campos
  de `CAMPOS_DATA`/`CAMPOS_DATA_HORA`.
- `id` é **sequencial por aba** (`MAX(id)+1`), começando em 1.
- `exportado` guarda **o que foi escrito na planilha** na última exportação (base para detectar edições no Excel).
- Conexão nova por operação (`sqlite3.connect(timeout=30)`), commit/rollback automático, e um `RLock` por banco.

## 2.4 Escrita: `aplicar_lote(operacoes)` — a única porta de gravação

Tudo passa por aqui, numa **única transação**: `adicionar`, `adicionar_lote`, `atualizar`, `excluir` são atalhos.

```python
operacoes = [
  {"tipo": "adicionar", "aba": "boletos", "dados": {...}, "usuario": "Fábio"},
  {"tipo": "atualizar", "aba": "pix", "id": 7, "dados": {"status": "Pago"}, "usuario": "Almir"},
  {"tipo": "excluir",   "aba": "caixa", "id": 3, "usuario": "Fábio"},
]
→ [{"ok": True, "registro": {...}}, {"ok": False, "erro": "nao_encontrado"}, ...]
```

Regras aplicadas em cada operação:
1. `dados` é filtrado por `definicao.editaveis`.
2. **adicionar**: cria o registro com todas as colunas (`None`), aplica `dados`, define `id`, `data_lancamento`,
   `atualizado_em` (= agora, sem segundos), `lancado_por` (= usuário); `status` vazio vira o padrão da aba;
   `pago_por` = usuário se já entra como "Pago". Normaliza (`_normalizar`: textos vazios = "", moeda com 2 casas,
   status inválido = padrão). Grava histórico **"Lançamento"** (+ sufixo) com a linha digitável ou a chave Pix.
3. **atualizar**: lê o atual, se o status mudou ajusta `pago_por` (usuário se virou "Pago", senão vazio), atualiza
   `atualizado_em`, mescla, normaliza, grava e registra no histórico **a descrição das mudanças**
   (`PlanilhaBoletos._descrever_alteracoes`, ex.: `Status: Pendente → Pago`).
4. **excluir**: apaga e registra **"Exclusão"**.
5. Se o registro tem `centro_custo` novo, o centro é **criado automaticamente** (quando o banco usa centros).
6. No fim: `_mudou()` — invalida o cache, marca exportação pendente e acorda a thread de sincronização.

## 2.5 Leitura

- `listar(aba)` devolve todos os registros normalizados (com cache por versão).
- `obter(id, aba)` → registro ou `RegistroNaoEncontrado`.
- `buscar_por_codigo(codigo_barras)` → boletos com o mesmo código (duplicidade).
- `nomes_por_documento()` → `{cpf/cnpj: nome}` dos boletos lançados (harmonizar beneficiários).
- `historico_do_registro(id, aba, desde)` → eventos de um lançamento (tela "Histórico e comprovante").
- `listar_centros()`, `contagens()`, `status()`.

## 2.6 Centros de custo

Tabela `centros` (só em `boletos.db`). `salvar_centro(nome, descricao, ativo, nome_anterior, usuario)`:
- nome obrigatório, até 60 caracteres, único sem diferenciar maiúsculas;
- **renomear** atualiza o `centro_custo` de **todos** os registros de todas as abas e registra no histórico
  "Renomeado de X para Y (N lançamento(s) atualizado(s))";
- desativar não apaga (some das listas de escolha). Centros padrão em `planilha.CENTROS_PADRAO`.

## 2.7 Planilha gerada (exportação)

`exportar()`:
1. Primeiro **importa edições feitas no Excel** (2.8).
2. Monta um `Workbook`: uma aba por `DefinicaoAba` (cabeçalho colorido, larguras, formatos, filtros, congelar
   cabeçalho, atrasados destacados, pagos em verde, cancelados riscados, link clicável para o arquivo original); se o
   banco usa centros: abas **Resumo** (com fórmulas: pendentes, vencidos, próximos 7 dias, pagos — boletos e Pix) e
   **Centros de Custo**; sempre a aba **Histórico** (data/hora, ação, ID, nome, vencimento, valor, detalhes, usuário).
3. Grava num temporário e substitui (`os.replace`) — se o Excel está com o arquivo aberto, levanta
   `PlanilhaBloqueadaError`, marca `excel_aberto=True` e tenta de novo depois (nada se perde: o banco já tem tudo).
4. Salva o **snapshot** (`exportado`) e o `mtime` da planilha em `meta.planilha_mtime`.
5. Faz o backup diário do banco (`<nome>-AAAA-MM-DD.db` em `dados/backups`, mantém `BACKUPS_MANTIDOS` = 30).

Thread de sincronização: espera alteração (ou 15 s), aguarda 1,5 s para juntar alterações seguidas, exporta se
pendente; se não, verifica se o Excel foi editado. No encerramento, exporta o que estiver pendente.

## 2.8 Edições feitas à mão no Excel (`importar_edicoes_do_excel`)

Se o `mtime` da planilha mudou desde a última exportação, alguém salvou o arquivo no Excel. Para cada linha:
- compara com o **snapshot** (o que o sistema tinha escrito) e com o **banco atual**;
- aplica só os campos **editáveis** que a pessoa mudou (diferentes do snapshot **e** do atual);
- grava com o usuário **"Planilha Excel (edição manual)"**.

Assim, um pagamento feito pelo bot enquanto a planilha estava aberta **não é desfeito**. Lançar e excluir só pelo sistema.

## 2.9 Migração inicial

`garantir()`: se `meta.importado_em` não existe, `migrar()` lê a planilha antiga (se houver) com os mesmos IDs, os
centros e o histórico, e grava no banco. Depois cria a planilha se ela não existir.

## 2.10 Repositório e fila de gravação (`repositorio.py`, `fila_gravacao.py`)

`RepositorioBoletos(planilha, fila, aba)` é o que o resto do sistema usa (`ctx.repositorio`, `_pix`, `_caixa`):
`listar`, `obter`, `adicionar`, `atualizar`, `excluir`, `aplicar_lote`, `buscar_por_codigo`.

A **fila** vem da época em que a planilha era o banco: se a gravação falhar por arquivo bloqueado, a operação fica em
`dados/gravacao_pendente.json` com **ID provisório negativo** (-1, -2…), aparece em todas as listas marcada como
"Aguardando gravação" e é gravada sozinha depois. Com o SQLite isso praticamente não acontece mais, mas a interface e
as regras continuam (IDs negativos são ignorados em painel, fechamento, comprovantes e lembretes).

`FonteLembretes(repositorio, repositorio_pix, cheques)` junta boletos + Pix + cheques a depositar numa lista única
para o serviço de notificações (cada item com `tipo_pagamento` = boleto/pix/cheque).

## 2.11 Arquivos enviados (`arquivos.py`)

`RepositorioArquivos(dados/arquivos)`:
- `salvar(bytes, nome)` → id `uuid4().hex` (32 hexadecimais); grava `<id>.pdf` ou `<id>.<ext>` (`.img` se a extensão
  for estranha), uma **prévia** `<id>.previa.jpg` (máx. 2000 px, qualidade 85) para imagens, e `<id>.json` com
  `{id, nome, extensao, tipo: pdf|imagem, tamanho, enviado_em}`;
- os registros guardam o caminho relativo `arquivos/<id>.<ext>` nos campos `arquivo`/`comprovante`;
- `id_de_caminho(caminho)` recupera o id; `visualizacao(id)` devolve a prévia (imagem) ou o PDF;
- `limpar_nao_referenciados(ids, dias)` apaga o que ninguém usa há mais de N dias (feito ao iniciar).

## 2.12 Arquivos JSON de configuração e estado

Cada serviço guarda o próprio estado num JSON em `dados/`, com **gravação atômica** (temporário + `os.replace`) e um
`threading.Lock`. Formatos de fábrica no anexo **A3**. Tokens e senhas de canais ficam nesses arquivos; senhas de
pessoas, só em hash.

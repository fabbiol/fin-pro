"""Gera os anexos técnicos da especificação do Fin Pro a partir do próprio código.

    .venv\\Scripts\\python ferramentas\\gerar_especificacao.py

Escreve em ``docs/especificacao/``:

* ``A1-api.md``                — todas as rotas da API (método, caminho, permissão, parâmetros, corpo e descrição);
* ``A2-modelo-de-dados.md``    — cada aba/tabela dos bancos (colunas, formatos, editáveis, situações);
* ``A3-configuracoes.md``      — variáveis de ambiente, permissões e o formato padrão dos arquivos de configuração;
* ``A4-mapa-do-codigo.md``     — cada módulo Python: o que faz, constantes, classes e funções (assinatura e descrição);
* ``A5-front-end.md``          — cada arquivo do front-end: o que faz e as funções exportadas;
* ``A6-testes.md``             — cada teste automatizado e o que ele garante;
* ``A7-respostas-da-api.md``   — exemplo real da resposta de cada rota GET (rodando sobre uma CÓPIA de ``dados_demo``);
* ``A8-constantes.md``         — todas as constantes de todos os módulos, por extenso (listas de palavras, regex, limites);
* ``A9-telas-e-chamadas.md``   — por arquivo do front-end: rotas da API chamadas, ações (data-acao), eventos e armazenamento;
* ``A10-codigo-dos-testes.md`` — o código completo dos testes (o contrato executável do sistema).

Roda com uma pasta de dados temporária: nunca lê nem altera a pasta ``dados`` (as amostras do A7 usam uma cópia da
pasta de demonstração, com o envio externo bloqueado).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "especificacao"
sys.path.insert(0, str(RAIZ))

# isola os dados antes de importar a aplicação (como nos testes); "--amostras <pasta>" = cópia dos dados de demonstração
MODO_AMOSTRAS = "--amostras" in sys.argv
if MODO_AMOSTRAS:
    os.environ["LEITOR_DADOS_DIR"] = sys.argv[sys.argv.index("--amostras") + 1]
    os.environ["LEITOR_DEMO"] = "1"  # nada sai para o Telegram nem para o e-mail
else:
    os.environ["LEITOR_DADOS_DIR"] = tempfile.mkdtemp(prefix="finpro-especificacao-")
os.environ["LEITOR_IA_AUTOMATICA"] = "0"
os.environ["LEITOR_NOTIFICACOES_AUTOMATICAS"] = "0"
os.environ["LEITOR_BACKUP_AUTOMATICO"] = "0"

CABECALHO = "> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em {quando}. Não edite à mão: rode o gerador.\n\n"
# arquivos que este gerador não lê (o roteador do front-end é descrito à mão no capítulo 10)
FRONT_IGNORADOS = {"web/js/app.js"}


def _md(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ").strip()


def _primeira_frase(doc: str | None) -> str:
    if not doc:
        return ""
    texto = " ".join(linha.strip() for linha in inspect.cleandoc(doc).split("\n\n")[0].splitlines())
    return texto


def _escrever(nome: str, titulo: str, corpo: str) -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    quando = datetime.now().strftime("%d/%m/%Y %H:%M")
    (DESTINO / nome).write_text(f"# {titulo}\n\n{CABECALHO.format(quando=quando)}{corpo.rstrip()}\n", encoding="utf-8")
    print(f"  {nome}")


# --------------------------------------------------------------------------- A1 · API


def _tipo(anotacao) -> str:
    texto = getattr(anotacao, "__name__", None) or str(anotacao)
    texto = texto.replace("typing.", "").replace("<class '", "").replace("'>", "")
    return re.sub(r"\b(app|pydantic|datetime|fastapi)\.[\w.]*\.", "", texto)


def _campos_modelo(modelo) -> list[str]:
    linhas = []
    for nome, campo in getattr(modelo, "model_fields", {}).items():
        restricoes = []
        for meta in campo.metadata:
            for chave in ("gt", "ge", "lt", "le", "min_length", "max_length", "pattern"):
                valor = getattr(meta, chave, None)
                if valor is not None:
                    restricoes.append(f"{chave}={valor}")
        padrao = "" if campo.is_required() else f" = {campo.default!r}"
        linhas.append(f"`{nome}`: {_md(_tipo(campo.annotation))}{padrao}{' (' + ', '.join(restricoes) + ')' if restricoes else ''}")
    return linhas


def gerar_api() -> None:
    from fastapi.routing import APIRoute

    from app import acesso
    from app.main import app

    def todas(rotas):  # FastAPI 0.14x guarda os routers incluídos dentro de um invólucro (original_router)
        for r in rotas:
            if hasattr(r, "original_router"):
                yield from todas(r.original_router.routes)
            else:
                yield r

    grupos: dict[str, list[str]] = {}
    total = 0
    for rota in todas(app.routes):
        if not isinstance(rota, APIRoute):
            continue
        total += 1
        modulo = rota.endpoint.__module__.replace("app.rotas.", "").replace("app.", "")
        for metodo in sorted(rota.methods - {"HEAD"}):
            try:
                permissao = acesso.permissao_da_rota(metodo, rota.path) or "—"
            except Exception:  # noqa: BLE001
                permissao = "?"
            parametros = []
            for p in rota.dependant.path_params:
                parametros.append(f"`{p.name}` (caminho)")
            for p in rota.dependant.query_params:
                info = p.field_info
                obrigatorio = info.is_required() if hasattr(info, "is_required") else getattr(p, "required", False)
                padrao = "" if obrigatorio else f" = {info.default!r}"
                parametros.append(f"`{p.name}`{padrao}")
            for p in rota.dependant.body_params:
                tipo = getattr(p.field_info, "annotation", None) or getattr(p, "type_", None)
                if hasattr(tipo, "model_fields"):
                    parametros.append(f"corpo **{tipo.__name__}**: " + "; ".join(_campos_modelo(tipo)))
                else:
                    parametros.append(f"`{p.name}` (arquivo/formulário)")
            descricao = _primeira_frase(rota.endpoint.__doc__) or rota.name.replace("_", " ")
            grupos.setdefault(modulo, []).append(
                f"| `{metodo}` | `{rota.path}` | {permissao} | {_md(descricao)} | {'<br>'.join(parametros) if parametros else '—'} |")
    corpo = [f"Total: **{total} rotas**. *Permissão* é a exigida pelo controle de acesso "
             "(`acesso.permissao_da_rota`): `—` = basta ter entrado (ou estar no computador principal); `admin` = só "
             "administrador.\n"]
    for modulo in sorted(grupos):
        corpo.append(f"## {modulo}\n\n| Método | Caminho | Permissão | O que faz | Parâmetros |\n|---|---|---|---|---|")
        corpo.extend(grupos[modulo])
        corpo.append("")
    _escrever("A1-api.md", "Anexo A1 — API (todas as rotas)", "\n".join(corpo))


# --------------------------------------------------------------------------- A2 · modelo de dados


def gerar_dados() -> None:
    from app import planilha
    from app.diesel.modelos import ABAS_DIESEL
    from app.empresas.modelos import ABAS_EMPRESAS

    corpo = ["Todas as tabelas seguem o mesmo mecanismo (`app/banco.py`): cada registro é guardado no SQLite como JSON, "
             "com `id` sequencial por aba, e a planilha Excel é gerada a partir dessas definições (ordem das colunas, "
             "título, largura e formato). *Editável* = o campo pode ser alterado depois de lançado (campo fora da lista "
             "é ignorado na gravação). *Texto* = vazio vira `\"\"` em vez de nulo.\n"]
    bancos = (("boletos.db / boletos.xlsx", planilha.ABAS), ("empresas.db / fechamentos.xlsx", ABAS_EMPRESAS),
              ("diesel.db / diesel.xlsx", ABAS_DIESEL))
    for banco, abas in bancos:
        corpo.append(f"## {banco}\n")
        for chave, aba in abas.items():
            corpo.append(f"### Aba `{chave}` — planilha \"{aba.nome}\"\n")
            corpo.append(f"- Situações válidas: {', '.join(f'`{s}`' for s in aba.status_validos)} "
                         f"(padrão `{aba.status_padrao}`; verde = `{aba.status_ok or '—'}`; riscado = `{aba.status_cancelado or '—'}`)")
            corpo.append(f"- Data de referência (atraso e histórico): `{aba.campo_data}` · nome no histórico: `{aba.campo_nome}`\n")
            corpo.append("| Campo | Título na planilha | Formato | Largura | Editável | Texto |\n|---|---|---|---|---|---|")
            for c in aba.colunas:
                corpo.append(f"| `{c.chave}` | {_md(c.titulo)} | {_md(c.formato or '')} | {c.largura} | "
                             f"{'sim' if c.chave in aba.editaveis else ''} | {'sim' if c.chave in aba.textos else ''} |")
            corpo.append("")
    for nome in ("STATUS_VALIDOS", "CAMPOS_DATA", "CAMPOS_DATA_HORA", "CAMPOS_NUMERO", "CAMPOS_MOEDA", "CAMPOS_COMPROVANTE",
                 "CAMPOS_PAGAMENTO"):
        valor = getattr(planilha, nome, None)
        if valor is not None:
            corpo.append(f"- `planilha.{nome}` = {', '.join(f'`{v}`' for v in sorted(valor))}")
    for modulo in ("app.empresas.modelos", "app.diesel.modelos"):
        m = importlib.import_module(modulo)
        for nome, valor in vars(m).items():
            if nome.isupper() and isinstance(valor, (tuple, list, frozenset, set, str, int, float)) and not nome.startswith("ABAS"):
                if isinstance(valor, (set, frozenset)):
                    valor = sorted(valor)
                corpo.append(f"- `{modulo.replace('app.', '')}.{nome}` = `{_md(valor if isinstance(valor, (str, int, float)) else list(valor))}`")
    _escrever("A2-modelo-de-dados.md", "Anexo A2 — Modelo de dados (todas as tabelas e campos)", "\n".join(corpo))


# --------------------------------------------------------------------------- A3 · configurações


def _json(valor) -> str:
    def padrao(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, (set, frozenset, tuple)):
            return list(o)
        return str(o)
    return json.dumps(valor, ensure_ascii=False, indent=2, default=padrao)


def gerar_configuracoes() -> None:
    from app import config, usuarios

    corpo = ["## Variáveis de ambiente (`.env`)\n", "| Variável | Padrão | Lida em |\n|---|---|---|"]
    vistos = set()
    for arquivo in sorted((RAIZ / "app").rglob("*.py")):
        texto = arquivo.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:os\.getenv|os\.environ\.get|_bool|_int)\(\s*"([A-Z_]+)"(?:\s*,\s*([^)]*))?\)', texto):
            nome, padrao = m.group(1), (m.group(2) or "").strip()
            if (nome, arquivo) in vistos:
                continue
            vistos.add((nome, arquivo))
            corpo.append(f"| `{nome}` | {_md(padrao) or '—'} | `{arquivo.relative_to(RAIZ).as_posix()}` |")
    corpo += ["", "## Valores calculados em `app/config.py`\n", "| Nome | Valor (nesta geração) |\n|---|---|"]
    for nome, valor in vars(config).items():
        if nome.isupper():
            texto = str(valor).replace(os.environ["LEITOR_DADOS_DIR"], "<dados>").replace(str(RAIZ), "<projeto>")
            corpo.append(f"| `{nome}` | `{_md(texto)}` |")
    corpo += ["", "## Permissões (`app/usuarios.py`)\n", "| Chave | Descrição |\n|---|---|"]
    corpo += [f"| `{k}` | {_md(v)} |" for k, v in usuarios.PERMISSOES.items()]
    corpo.append(f"\nPermissões de um usuário novo: {', '.join(f'`{p}`' for p in usuarios.PERMISSOES_PADRAO)}.\n")
    corpo.append("## Formato padrão dos arquivos de configuração (`dados/*.json`)\n")
    corpo.append("Valores de fábrica, criados na primeira execução. Tokens e senhas ficam vazios aqui.\n")
    for modulo in ("app.notificacoes.servico", "app.entrada", "app.empresas.configuracao", "app.caixa.bot", "app.diesel.bot",
                   "app.preferencias", "app.backup", "app.rede", "app.usuarios", "app.admin"):
        try:
            m = importlib.import_module(modulo)
        except Exception as exc:  # noqa: BLE001
            corpo.append(f"- `{modulo}`: não importou ({exc})")
            continue
        for nome, valor in vars(m).items():
            if re.fullmatch(r"(PADRAO\w*|REGRAS_PADRAO|CONFIG_PADRAO)", nome) and isinstance(valor, (dict, list)):
                corpo.append(f"### `{modulo.replace('app.', '')}.{nome}`\n\n```json\n{_json(valor)}\n```\n")
    _escrever("A3-configuracoes.md", "Anexo A3 — Variáveis, permissões e arquivos de configuração", "\n".join(corpo))


# --------------------------------------------------------------------------- A4 · mapa do código


def _assinatura(no: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    try:
        args = ast.unparse(no.args)
    except Exception:  # noqa: BLE001
        args = "…"
    retorno = f" -> {ast.unparse(no.returns)}" if no.returns is not None else ""
    return f"{'async ' if isinstance(no, ast.AsyncFunctionDef) else ''}{no.name}({args}){retorno}"


def gerar_mapa() -> None:
    corpo = ["Para cada módulo: a descrição (docstring), as constantes, as classes (com os métodos) e as funções, com a "
             "assinatura completa e a primeira frase da descrição. É o \"índice\" do código para reconstruir cada peça.\n"]
    arquivos = sorted(p for p in (RAIZ / "app").rglob("*.py") if "__pycache__" not in p.parts)
    corpo.append("| Módulo | Linhas |\n|---|---|")
    corpo += [f"| `{p.relative_to(RAIZ).as_posix()}` | {len(p.read_text(encoding='utf-8').splitlines())} |" for p in arquivos]
    corpo.append("")
    for arquivo in arquivos:
        fonte = arquivo.read_text(encoding="utf-8")
        arvore = ast.parse(fonte)
        rel = arquivo.relative_to(RAIZ).as_posix()
        corpo.append(f"## `{rel}`\n")
        doc = ast.get_docstring(arvore)
        if doc:
            corpo.append("> " + "\n> ".join(inspect.cleandoc(doc).splitlines()) + "\n")
        constantes = []
        for no in arvore.body:
            alvo = None
            if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
                alvo, valor = no.targets[0].id, no.value
            elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name) and no.value is not None:
                alvo, valor = no.target.id, no.value
            if alvo and alvo.isupper():
                texto = ast.unparse(valor)
                constantes.append(f"`{alvo}` = `{_md(texto if len(texto) <= 160 else texto[:157] + '…')}`")
        if constantes:
            corpo.append("**Constantes:** " + " · ".join(constantes) + "\n")
        for no in arvore.body:
            if isinstance(no, ast.ClassDef):
                corpo.append(f"- **classe `{no.name}`**" + (f" — {_md(_primeira_frase(ast.get_docstring(no)))}" if ast.get_docstring(no) else ""))
                for metodo in no.body:
                    if isinstance(metodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        descricao = _primeira_frase(ast.get_docstring(metodo))
                        corpo.append(f"  - `{_md(_assinatura(metodo))}`" + (f" — {_md(descricao)}" if descricao else ""))
            elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                rotas = [ast.unparse(d) for d in no.decorator_list if "router." in ast.unparse(d)]
                descricao = _primeira_frase(ast.get_docstring(no))
                prefixo = f"`{_md(rotas[0].replace('router.', ''))}` → " if rotas else ""
                corpo.append(f"- {prefixo}`{_md(_assinatura(no))}`" + (f" — {_md(descricao)}" if descricao else ""))
        corpo.append("")
    _escrever("A4-mapa-do-codigo.md", "Anexo A4 — Mapa do código (back-end Python)", "\n".join(corpo))


# --------------------------------------------------------------------------- A5 · front-end


def gerar_front() -> None:
    corpo = ["Front-end sem etapa de build: `web/index.html` carrega `web/js/app.js` como módulo ES; cada tela é um módulo em "
             "`web/js/views/` que exporta `montar(el, params)` e, opcionalmente, `desmontar()`. Estilos em `web/css/app.css` "
             "(variáveis de cor em `:root`, tema escuro em `[data-theme=dark]`).\n"]
    arquivos = sorted(p for p in (RAIZ / "web").rglob("*") if p.suffix in (".js", ".css", ".html", ".json", ".webmanifest"))
    corpo.append("| Arquivo | Linhas | O que faz | Exporta |\n|---|---|---|---|")
    for arquivo in arquivos:
        rel = arquivo.relative_to(RAIZ).as_posix()
        if rel in FRONT_IGNORADOS:
            corpo.append(f"| `{rel}` | — | Roteador e casca da aplicação (descrito no capítulo 10) | — |")
            continue
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        linhas = texto.splitlines()
        descricao = ""
        if linhas and linhas[0].lstrip().startswith(("//", "/*", "<!--")):
            descricao = re.sub(r"^\s*(//|/\*+|<!--)\s*|\s*(\*/|-->)\s*$", "", linhas[0])
        exporta = re.findall(r"export\s+(?:async\s+)?(?:function\*?|const|let|class)\s+(\w+)", texto)
        corpo.append(f"| `{rel}` | {len(linhas)} | {_md(descricao)} | {_md(', '.join(exporta))} |")
    tokens = re.findall(r"^\s*(--[\w-]+):\s*([^;]+);", (RAIZ / "web/css/app.css").read_text(encoding="utf-8"), re.M)
    vistos = {}
    for nome, valor in tokens:
        vistos.setdefault(nome, valor.strip())
    corpo += ["", "## Variáveis de cor e medidas (tema claro, `:root`)\n", "| Variável | Valor |\n|---|---|"]
    corpo += [f"| `{n}` | `{_md(v)}` |" for n, v in vistos.items()]
    _escrever("A5-front-end.md", "Anexo A5 — Front-end (arquivos, telas e estilos)", "\n".join(corpo))


# --------------------------------------------------------------------------- A6 · testes


def gerar_testes() -> None:
    corpo = []
    total = 0
    for arquivo in sorted((RAIZ / "tests").glob("test_*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        testes = [n for n in ast.walk(arvore) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]
        total += len(testes)
        doc = ast.get_docstring(arvore)
        corpo.append(f"## `{arquivo.name}` ({len(testes)})\n" + (f"\n> {_primeira_frase(doc)}\n" if doc else ""))
        for t in testes:
            descricao = _primeira_frase(ast.get_docstring(t)) or t.name[5:].replace("_", " ")
            corpo.append(f"- `{t.name}` — {_md(descricao)}")
        corpo.append("")
    _escrever("A6-testes.md", "Anexo A6 — Testes automatizados",
              f"Total: **{total} testes** em `tests/`. Rodar: `.venv\\Scripts\\python -m pytest`.\n\n" + "\n".join(corpo))


# --------------------------------------------------------------------------- A7 · respostas da API (amostras)

PARAMETROS_DE_EXEMPLO = {"id_": "1", "aba": "abastecimentos", "tipo": "segunda"}
ROTAS_PULADAS = ("/api/app/abrir", "/api/leituras/tarefas/", "/api/arquivos/")
CHAVES_SECRETAS = re.compile(r"token|senha|segredo|\bsal\b|hash", re.I)


def _resumir_json(valor, profundidade: int = 0):
    """Encurta a resposta: listas com 2 itens, textos com 80 caracteres, segredos mascarados."""
    if profundidade > 6:
        return "…"
    if isinstance(valor, dict):
        return {k: ("••••" if CHAVES_SECRETAS.search(k) and isinstance(v, str) and v else _resumir_json(v, profundidade + 1))
                for k, v in valor.items()}
    if isinstance(valor, list):
        itens = [_resumir_json(v, profundidade + 1) for v in valor[:2]]
        if len(valor) > 2:
            itens.append(f"… mais {len(valor) - 2} item(ns)")
        return itens
    if isinstance(valor, str) and len(valor) > 80:
        return valor[:77] + "…"
    return valor


def gerar_respostas() -> None:
    """Roda dentro do processo ``--amostras`` (dados = cópia da demonstração)."""
    from fastapi.routing import APIRoute
    from fastapi.testclient import TestClient

    from app.main import app

    def todas(rotas):
        for r in rotas:
            if hasattr(r, "original_router"):
                yield from todas(r.original_router.routes)
            else:
                yield r

    corpo = ["Resposta **real** de cada rota `GET` da API, obtida rodando o sistema sobre uma **cópia dos dados de "
             "demonstração** (nada sai para fora). Listas foram cortadas em 2 itens e textos em 80 caracteres; tokens e "
             "senhas aparecem como `••••`. Use como referência do **formato** de cada resposta (nomes e tipos dos campos).\n"]
    with TestClient(app) as cliente:
        for rota in todas(app.routes):
            if not isinstance(rota, APIRoute) or "GET" not in rota.methods or not rota.path.startswith("/api/"):
                continue
            if any(rota.path.startswith(p) for p in ROTAS_PULADAS):
                continue
            caminho = rota.path
            faltou = False
            for nome in re.findall(r"{(\w+)}", caminho):
                if nome not in PARAMETROS_DE_EXEMPLO:
                    faltou = True
                    break
                caminho = caminho.replace("{" + nome + "}", PARAMETROS_DE_EXEMPLO[nome])
            if faltou:
                continue
            try:
                resposta = cliente.get(caminho)
            except Exception as exc:  # noqa: BLE001
                corpo.append(f"## `GET {rota.path}`\n\nNão foi possível chamar: `{exc}`\n")
                continue
            tipo = resposta.headers.get("content-type", "")
            corpo.append(f"## `GET {rota.path}`\n\nChamado como `{caminho}` → HTTP {resposta.status_code} · `{tipo.split(';')[0]}`\n")
            if "json" in tipo:
                corpo.append("```json\n" + _json(_resumir_json(resposta.json())) + "\n```\n")
            else:
                corpo.append(f"(arquivo/conteúdo não JSON, {len(resposta.content)} bytes)\n")
    _escrever("A7-respostas-da-api.md", "Anexo A7 — Exemplos reais de resposta da API", "\n".join(corpo))


def gerar_amostras_em_copia() -> None:
    """Copia ``dados_demo`` para uma pasta temporária e roda este gerador em modo ``--amostras`` sobre a cópia."""
    import shutil
    import subprocess

    origem = RAIZ / "dados_demo"
    if not origem.exists():
        print("  A7 pulado: a pasta dados_demo não existe (rode demonstracao.bat uma vez)")
        return
    copia = Path(tempfile.mkdtemp(prefix="finpro-amostras-"))
    try:
        shutil.copytree(origem, copia, dirs_exist_ok=True, ignore=shutil.ignore_patterns("backups", "webview", "*.log"))
        subprocess.run([sys.executable, __file__, "--amostras", str(copia)], check=True, cwd=RAIZ)
    finally:
        shutil.rmtree(copia, ignore_errors=True)


# --------------------------------------------------------------------------- A8 · constantes por extenso


def gerar_constantes() -> None:
    corpo = ["Todas as constantes de nível de módulo (nomes em MAIÚSCULAS) do back-end, **sem cortes**: listas de "
             "palavras-sinal, expressões regulares, limites, pesos e tabelas. São os \"números mágicos\" que calibram o "
             "sistema — copie-os exatamente na nova versão.\n"]
    for arquivo in sorted(p for p in (RAIZ / "app").rglob("*.py") if "__pycache__" not in p.parts):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        blocos = []
        for no in arvore.body:
            alvo = valor = None
            if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
                alvo, valor = no.targets[0].id, no.value
            elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name) and no.value is not None:
                alvo, valor = no.target.id, no.value
            if alvo and alvo.lstrip("_").isupper() and len(alvo.strip("_")) > 1:
                blocos.append(f"{alvo} = {ast.unparse(valor)}")
        if blocos:
            corpo.append(f"## `{arquivo.relative_to(RAIZ).as_posix()}`\n\n```python\n" + "\n\n".join(blocos) + "\n```\n")
    _escrever("A8-constantes.md", "Anexo A8 — Constantes, listas de palavras e expressões regulares (por extenso)",
              "\n".join(corpo))


# --------------------------------------------------------------------------- A9 · telas e chamadas

RE_CHAMADA_API = re.compile(r"api\.(get|post|put|patch|del|enviarPara|enviarArquivo|criarLeitura)\(\s*([`\"'])([^`\"']*)\2")
RE_LINK_API = re.compile(r"[\"'`(](/api/[^\"'`)\s?$]+)")
RE_ACAO = re.compile(r"data-acao=\"([a-z0-9-]+)\"")
RE_CASE = re.compile(r"case\s+\"([a-z0-9-]+)\"")
RE_EVENTO_EMITIDO = re.compile(r"dispatchEvent\(new\s+(?:Custom)?Event\(\"([^\"]+)\"")
RE_EVENTO_OUVIDO = re.compile(r"addEventListener\(\"([a-z]+:[a-z:]+)\"")
RE_ARMAZENAMENTO = re.compile(r"localStorage\.(?:getItem|setItem)\(\s*([A-Z_]+|\"[^\"]+\")")
METODOS_JS = {"get": "GET", "post": "POST", "put": "PUT", "patch": "PATCH", "del": "DELETE"}


def gerar_telas() -> None:
    corpo = ["Para cada arquivo do front-end: as **rotas da API** que ele chama (método e caminho — `${…}` são partes "
             "variáveis), os links de download, as **ações** dos botões (`data-acao`), os **eventos** que emite e escuta e as "
             "chaves de **armazenamento local**. Serve para conferir que cada botão da nova versão chama a rota certa.\n"]
    for arquivo in sorted((RAIZ / "web" / "js").rglob("*.js")):
        rel = arquivo.relative_to(RAIZ).as_posix()
        if rel in FRONT_IGNORADOS:
            continue
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        chamadas = sorted({f"{METODOS_JS.get(m.group(1), 'POST (arquivo)')} {m.group(3)}" for m in RE_CHAMADA_API.finditer(texto)})
        caminhos_chamados = {c.split(" ", 2)[-1] for c in chamadas}
        links = sorted({m.group(1) for m in RE_LINK_API.finditer(texto)} - caminhos_chamados)
        acoes = sorted(set(RE_ACAO.findall(texto)) | set(RE_CASE.findall(texto)))
        emitidos = sorted(set(RE_EVENTO_EMITIDO.findall(texto)))
        ouvidos = sorted(set(RE_EVENTO_OUVIDO.findall(texto)))
        chaves = sorted(set(RE_ARMAZENAMENTO.findall(texto)))
        if not (chamadas or links or acoes or emitidos or ouvidos or chaves):
            continue
        corpo.append(f"## `{rel}`\n")
        for rotulo, itens in (("API", chamadas), ("Links/downloads", links), ("Ações", acoes), ("Emite", emitidos),
                              ("Escuta", ouvidos), ("Armazenamento local", chaves)):
            if itens:
                corpo.append(f"- **{rotulo}:** " + " · ".join(f"`{i}`" for i in itens))
        corpo.append("")
    _escrever("A9-telas-e-chamadas.md", "Anexo A9 — Telas: chamadas à API, ações, eventos e armazenamento", "\n".join(corpo))


# --------------------------------------------------------------------------- A10 · código dos testes


def gerar_codigo_testes() -> None:
    corpo = ["O código **completo** de cada teste automatizado. É o contrato executável: entradas reais (inclusive textos de "
             "OCR de documentos reais), resultados esperados e casos de borda. Uma nova versão que passa nestes testes faz "
             "o mesmo que a atual. Os arquivos de apoio (`conftest.py`, `corpus.py`, `gerar_boleto_exemplo.py`) vêm primeiro.\n"]
    apoio = [RAIZ / "tests" / n for n in ("conftest.py", "corpus.py", "gerar_boleto_exemplo.py")]
    for arquivo in [*[a for a in apoio if a.exists()], *sorted((RAIZ / "tests").glob("test_*.py"))]:
        codigo = arquivo.read_text(encoding="utf-8")
        corpo.append(f"## `tests/{arquivo.name}` ({len(codigo.splitlines())} linhas)\n\n```python\n{codigo.rstrip()}\n```\n")
    _escrever("A10-codigo-dos-testes.md", "Anexo A10 — Código completo dos testes", "\n".join(corpo))


if __name__ == "__main__":
    if MODO_AMOSTRAS:
        gerar_respostas()
        sys.exit(0)
    print(f"Gerando em {DESTINO}:")
    for passo in (gerar_api, gerar_dados, gerar_configuracoes, gerar_mapa, gerar_front, gerar_testes,
                  gerar_amostras_em_copia, gerar_constantes, gerar_telas, gerar_codigo_testes):
        passo()

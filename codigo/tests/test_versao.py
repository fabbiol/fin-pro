"""Controle de versão: número, histórico (VERSOES.md), guardar uma versão nova, voltar a uma antiga e a API."""

import importlib.util
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main, versao

RAIZ = Path(__file__).resolve().parent.parent
precisa_do_git = pytest.mark.skipif(shutil.which("git") is None, reason="git não instalado")


def _ferramenta():
    spec = importlib.util.spec_from_file_location("ferramenta_versao", RAIZ / "ferramentas" / "versao.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _git(pasta: Path, *argumentos: str) -> str:
    return subprocess.run(["git", *argumentos], cwd=pasta, capture_output=True, text=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def sistema(tmp_path):
    """Uma pasta de sistema em miniatura, com repositório e a versão 1.0.0 guardada."""
    pasta = tmp_path / "sistema"
    (pasta / "app").mkdir(parents=True)
    (pasta / "app" / "__init__.py").write_text('"""Sistema."""\n\n__version__ = "1.0.0"\n', encoding="utf-8")
    (pasta / "VERSOES.md").write_text("# Histórico de versões\n\n> explicação\n\n## v1.0.0 — 01/10/2026 — Primeira\n- nasceu\n",
                                      encoding="utf-8")
    (pasta / "codigo.txt").write_text("versão um\n", encoding="utf-8")
    (pasta / ".gitignore").write_text("dados/\n", encoding="utf-8")
    (pasta / "dados").mkdir()
    (pasta / "dados" / "boletos.db").write_bytes(b"dados reais")
    if shutil.which("git"):
        _git(pasta, "init", "-q", "-b", "main")
        _git(pasta, "config", "user.name", "Teste")
        _git(pasta, "config", "user.email", "teste@exemplo.com")
        _git(pasta, "config", "commit.gpgsign", "false")
        _git(pasta, "add", "-A")
        _git(pasta, "commit", "-q", "-m", "v1.0.0 — Primeira")
        _git(pasta, "tag", "-a", "v1.0.0", "-m", "v1.0.0 — Primeira")
    return pasta


def test_proxima_versao_por_tipo():
    assert versao.proxima("1.9.0", "correcao") == "1.9.1"
    assert versao.proxima("1.9.1", "melhoria") == "1.10.0"
    assert versao.proxima("1.10.3", "grande") == "2.0.0"
    with pytest.raises(versao.ErroVersao):
        versao.proxima("1.9", "melhoria")
    with pytest.raises(versao.ErroVersao):
        versao.proxima("1.9.0", "enorme")


def test_historico_e_registro_no_topo(sistema):
    assert versao.historico(sistema) == [{"versao": "1.0.0", "data": "2026-10-01", "titulo": "Primeira", "itens": ["nasceu"]}]
    versao.registrar("1.1.0", "  Relatórios   novos ", ["um", " dois  itens ", ""], date(2026, 10, 10), raiz=sistema)
    lista = versao.historico(sistema)
    assert [v["versao"] for v in lista] == ["1.1.0", "1.0.0"]
    assert lista[0] == {"versao": "1.1.0", "data": "2026-10-10", "titulo": "Relatórios novos", "itens": ["um", "dois itens"]}
    texto = (sistema / "VERSOES.md").read_text(encoding="utf-8")
    assert texto.startswith("# Histórico de versões\n\n> explicação\n\n## v1.1.0 — 10/10/2026 — Relatórios novos\n- um\n")
    with pytest.raises(versao.ErroVersao):
        versao.registrar("1.1.0", "Repetida", raiz=sistema)
    versao.definir_versao("1.1.0", sistema)
    assert versao.versao_atual(sistema) == "1.1.0" and '"""Sistema."""' in (sistema / "app" / "__init__.py").read_text(encoding="utf-8")


@precisa_do_git
def test_guardar_versao_nova(sistema, capsys):
    ferramenta = _ferramenta()
    assert ferramenta.main(["nova", "Nada mudou", "--sem-testes"], raiz=sistema) == 0  # sem alterações: não cria versão
    assert versao.versao_atual(sistema) == "1.0.0"

    (sistema / "codigo.txt").write_text("versão dois\n", encoding="utf-8")
    (sistema / "novo.txt").write_text("arquivo novo\n", encoding="utf-8")
    assert sorted(versao.alteracoes_pendentes(sistema)) == ["codigo.txt", "novo.txt"]
    assert ferramenta.main(["nova", "Relatório novo", "-m", "tela de relatórios", "--sem-testes"], raiz=sistema) == 0
    assert versao.versao_atual(sistema) == "1.1.0" and versao.alteracoes_pendentes(sistema) == []
    assert [e["etiqueta"] for e in versao.etiquetas(sistema)] == ["v1.1.0", "v1.0.0"]
    assert versao.historico(sistema)[0]["itens"] == ["tela de relatórios"]
    assert "v1.1.0 — Relatório novo" in _git(sistema, "log", "-1", "--format=%s")
    estado = versao.repositorio(sistema)
    assert estado["disponivel"] and estado["pendentes"] == 0 and estado["versoes_guardadas"] == 2

    assert ferramenta.main(["nova", "Ajuste", "--tipo", "correcao", "--sem-testes"], raiz=sistema) == 0  # nada mudou
    (sistema / "codigo.txt").write_text("versão dois e meio\n", encoding="utf-8")
    assert ferramenta.main(["nova", "Ajuste", "--tipo", "correcao", "--sem-testes"], raiz=sistema) == 0
    assert versao.versao_atual(sistema) == "1.1.1"
    assert ferramenta.main(["listar"], raiz=sistema) == 0 and "v1.1.1" in capsys.readouterr().out


@precisa_do_git
def test_voltar_para_uma_versao_antiga_sem_perder_nada(sistema):
    ferramenta = _ferramenta()
    (sistema / "codigo.txt").write_text("versão dois\n", encoding="utf-8")
    (sistema / "novo.txt").write_text("arquivo novo\n", encoding="utf-8")
    ferramenta.main(["nova", "Relatório novo", "--sem-testes"], raiz=sistema)

    (sistema / "codigo.txt").write_text("rascunho\n", encoding="utf-8")
    assert ferramenta.main(["voltar", "v1.0.0"], raiz=sistema) == 1  # há alterações não guardadas: não volta
    assert (sistema / "codigo.txt").read_text(encoding="utf-8") == "rascunho\n"
    _git(sistema, "checkout", "-q", "--", "codigo.txt")
    assert ferramenta.main(["voltar", "v7.7.7"], raiz=sistema) == 1  # versão que não existe

    assert ferramenta.main(["voltar", "v1.0.0"], raiz=sistema) == 0
    assert (sistema / "codigo.txt").read_text(encoding="utf-8") == "versão um\n"
    assert not (sistema / "novo.txt").exists()  # arquivo criado depois da v1.0.0 sai
    assert (sistema / "dados" / "boletos.db").read_bytes() == b"dados reais"  # os dados nunca são tocados
    assert versao.versao_atual(sistema) == "1.1.1"  # voltar vira uma versão nova
    lista = versao.historico(sistema)
    assert [v["versao"] for v in lista] == ["1.1.1", "1.1.0", "1.0.0"] and "Voltou para a versão v1.0.0" in lista[0]["titulo"]
    assert versao.alteracoes_pendentes(sistema) == []

    assert ferramenta.main(["voltar", "v1.1.0"], raiz=sistema) == 0  # e dá para desfazer a volta
    assert (sistema / "novo.txt").read_text(encoding="utf-8") == "arquivo novo\n"
    assert versao.versao_atual(sistema) == "1.1.2"


@precisa_do_git
def test_historico_completo_num_arquivo_para_o_backup(sistema, tmp_path):
    destino = tmp_path / "backup" / "versoes" / "finpro.bundle"
    assert versao.gerar_bundle(destino, raiz=sistema) and destino.stat().st_size > 0
    assert versao.verificar_bundle(destino, raiz=sistema)
    copia = tmp_path / "outro-computador"
    _git(tmp_path, "clone", "-q", str(destino), str(copia))
    assert (copia / "codigo.txt").read_text(encoding="utf-8") == "versão um\n" and "v1.0.0" in _git(copia, "tag")
    sem_repositorio = tmp_path / "pasta-comum"
    sem_repositorio.mkdir()
    assert not versao.gerar_bundle(tmp_path / "x.bundle", raiz=sem_repositorio)
    assert versao.repositorio(sem_repositorio) == {"disponivel": False, "commit": None, "commit_data": None, "pendentes": 0,
                                                 "arquivos_pendentes": [], "versoes_guardadas": 0}


def test_api_da_versao():
    with TestClient(main.app, client=("127.0.0.1", 5000)) as computador:
        dados = computador.get("/api/versao").json()
        assert dados["versao"] == versao.versao_atual() == computador.get("/api/status").json()["versao"]
        assert dados["historico"] and dados["historico"][0]["versao"] and "arquivos_pendentes" in dados
    with TestClient(main.app, client=("192.168.0.9", 5000)) as rede:
        resposta = rede.get("/api/versao")
        assert resposta.status_code in (200, 401) and "arquivos_pendentes" not in resposta.json()

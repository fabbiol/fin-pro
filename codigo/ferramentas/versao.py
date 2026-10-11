"""Controle de versão do Fin Pro — guardar, listar, comparar e voltar versões.

    python ferramentas/versao.py                         como está agora (versão, o que mudou e ainda não foi guardado)
    python ferramentas/versao.py nova "Título" -m "o que mudou" -m "outra mudança"
                                                         guarda uma versão nova (roda os testes antes)
        --tipo correcao | melhoria | grande              qual número aumenta (padrão: melhoria → 1.9.0 vira 1.10.0)
        --sem-testes                                     não roda os testes antes de guardar
    python ferramentas/versao.py listar                  todas as versões guardadas
    python ferramentas/versao.py comparar v1.8.0 [v1.9.0]  o que mudou entre duas versões (ou até agora)
    python ferramentas/versao.py voltar v1.8.0           deixa o CÓDIGO igual ao daquela versão, como uma versão nova

Só o código tem versões. Os dados (pasta ``dados``) nunca são alterados por esta ferramenta: quem os protege é o backup.
"Voltar" não apaga nada: cria uma versão nova com o código antigo, então sempre dá para desfazer.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app import versao as v  # noqa: E402  (só usa a biblioteca padrão)


def _saida_utf8() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _exigir_repositorio(raiz: Path) -> None:
    if not v.tem_repositorio(raiz):
        raise v.ErroVersao("Esta pasta ainda não tem controle de versão (git). Rode: git init -b main")


def _rodar_testes(raiz: Path) -> bool:
    print("Rodando os testes antes de guardar a versão (alguns minutos)…")
    comando = [sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider", "--ignore=tests/test_telas.py"]
    return subprocess.run(comando, cwd=raiz).returncode == 0


def situacao(raiz: Path) -> int:
    atual = v.versao_atual(raiz)
    print(f"Fin Pro v{atual}")
    if not v.tem_repositorio(raiz):
        print("Sem controle de versão nesta pasta.")
        return 0
    pendentes = v.alteracoes_pendentes(raiz)
    if pendentes:
        print(f"\n{len(pendentes)} arquivo(s) alterado(s) desde a última versão guardada:")
        for arquivo in pendentes[:40]:
            print(f"  • {arquivo}")
        if len(pendentes) > 40:
            print(f"  … e mais {len(pendentes) - 40}")
        print('\nPara guardar: python ferramentas/versao.py nova "Título" -m "o que mudou"')
    else:
        print("Tudo guardado: nenhuma alteração desde a última versão.")
    print("\nÚltimas versões:")
    for item in v.historico(raiz)[:6]:
        print(f"  v{item['versao']}  {item['data']}  {item['titulo']}")
    return 0


def nova(raiz: Path, titulo: str, itens: list[str], tipo: str, sem_testes: bool, coautor: str = "") -> int:
    _exigir_repositorio(raiz)
    if not v.alteracoes_pendentes(raiz):
        print("Nada mudou desde a última versão guardada: não há o que guardar.")
        return 0
    if not sem_testes and not _rodar_testes(raiz):
        print("\nOs testes falharam: a versão NÃO foi guardada. Corrija e tente de novo (ou use --sem-testes).")
        return 1
    numero = v.proxima(v.versao_atual(raiz), tipo)
    v.registrar(numero, titulo, itens, raiz=raiz)
    v.definir_versao(numero, raiz)
    mensagem = f"v{numero} — {titulo.strip()}"
    corpo = "\n".join(f"- {i.strip()}" for i in itens if i.strip())
    rodape = f"\n\nCo-Authored-By: {coautor}" if coautor else ""
    v.git("add", "-A", raiz=raiz, checar=True)
    v.git("commit", "-q", "-m", mensagem + (f"\n\n{corpo}" if corpo else "") + rodape, raiz=raiz, checar=True)
    v.git("tag", "-a", f"v{numero}", "-m", mensagem, raiz=raiz, checar=True)
    print(f"\nVersão v{numero} guardada: {titulo.strip()}")
    print("Feche e abra o Fin Pro para ele mostrar o número novo.")
    return 0


def listar(raiz: Path) -> int:
    _exigir_repositorio(raiz)
    lista = v.etiquetas(raiz)
    if not lista:
        print("Nenhuma versão guardada ainda.")
        return 0
    atual = f"v{v.versao_atual(raiz)}"
    for item in lista:
        marca = "→" if item["etiqueta"] == atual else " "
        print(f"{marca} {item['etiqueta']:<9} {item['data'][:10]}  {item['titulo']}")
    return 0


def comparar(raiz: Path, de: str, ate: str | None) -> int:
    _exigir_repositorio(raiz)
    argumentos = ["diff", "--stat", de] + ([ate] if ate else [])
    print(v.git(*argumentos, raiz=raiz, checar=True) or "Nenhuma diferença.")
    return 0


def voltar(raiz: Path, etiqueta: str, coautor: str = "") -> int:
    """Deixa o código igual ao da versão escolhida e guarda isso como uma versão nova (nada é apagado do histórico)."""
    _exigir_repositorio(raiz)
    if etiqueta not in {e["etiqueta"] for e in v.etiquetas(raiz)}:
        raise v.ErroVersao(f"Não existe a versão {etiqueta}. Veja as versões com: python ferramentas/versao.py listar")
    if v.alteracoes_pendentes(raiz):
        raise v.ErroVersao("Há alterações ainda não guardadas. Guarde-as primeiro (comando 'nova') para não perdê-las.")
    atual = v.versao_atual(raiz)
    if etiqueta == f"v{atual}":
        print(f"O sistema já está na versão {etiqueta}.")
        return 0
    historico_completo = (raiz / v.ARQUIVO_HISTORICO).read_text(encoding="utf-8")
    # arquivos do código voltam a ser exatamente os daquela versão (os criados depois dela são removidos)
    v.git("restore", f"--source={etiqueta}", "--staged", "--worktree", "--", ".", raiz=raiz, checar=True)
    (raiz / v.ARQUIVO_HISTORICO).write_text(historico_completo, encoding="utf-8", newline="\n")  # o histórico não volta no tempo
    numero = v.proxima(atual, "correcao")
    titulo = f"Voltou para a versão {etiqueta}"
    v.registrar(numero, titulo, [f"O código ficou igual ao da versão {etiqueta}. A versão v{atual} continua guardada."],
                raiz=raiz)
    v.definir_versao(numero, raiz)
    rodape = f"\n\nCo-Authored-By: {coautor}" if coautor else ""
    v.git("add", "-A", raiz=raiz, checar=True)
    v.git("commit", "-q", "-m", f"v{numero} — {titulo}{rodape}", raiz=raiz, checar=True)
    v.git("tag", "-a", f"v{numero}", "-m", f"v{numero} — {titulo}", raiz=raiz, checar=True)
    print(f"Pronto: o código voltou para a {etiqueta} (guardado como v{numero}).")
    print(f"Os dados não foram alterados. Para desfazer: python ferramentas/versao.py voltar v{atual}")
    print("Feche e abra o Fin Pro para usar o código desta versão.")
    return 0


def main(argumentos: list[str] | None = None, raiz: Path | None = None) -> int:
    _saida_utf8()
    raiz = raiz or RAIZ
    leitor = argparse.ArgumentParser(description="Controle de versão do Fin Pro")
    comandos = leitor.add_subparsers(dest="comando")
    comandos.add_parser("situacao", help="como está agora")
    p_nova = comandos.add_parser("nova", help="guarda uma versão nova")
    p_nova.add_argument("titulo")
    p_nova.add_argument("-m", "--mudanca", action="append", default=[], help="o que mudou (pode repetir)")
    p_nova.add_argument("--tipo", choices=list(v.TIPOS), default="melhoria")
    p_nova.add_argument("--sem-testes", action="store_true")
    p_nova.add_argument("--coautor", default="", help='ex.: "Nome <email>"')
    comandos.add_parser("listar", help="todas as versões guardadas")
    p_comparar = comandos.add_parser("comparar", help="o que mudou entre duas versões")
    p_comparar.add_argument("de")
    p_comparar.add_argument("ate", nargs="?")
    p_voltar = comandos.add_parser("voltar", help="volta o código para uma versão")
    p_voltar.add_argument("etiqueta")
    p_voltar.add_argument("--coautor", default="")
    escolha = leitor.parse_args(argumentos)
    try:
        if escolha.comando == "nova":
            return nova(raiz, escolha.titulo, escolha.mudanca, escolha.tipo, escolha.sem_testes, escolha.coautor)
        if escolha.comando == "listar":
            return listar(raiz)
        if escolha.comando == "comparar":
            return comparar(raiz, escolha.de, escolha.ate)
        if escolha.comando == "voltar":
            return voltar(raiz, escolha.etiqueta, escolha.coautor)
        return situacao(raiz)
    except v.ErroVersao as exc:
        print(f"Não foi possível: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Restaura o Fin Pro inteiro a partir de um backup — código, bancos de dados, arquivos, configurações e versões.

    python restaurar_backup.py <backup> <destino> [--forcar] [--sem-codigo]

    <backup>   a pasta "Leitor de Boletos - Backup" (ou um pacote "Fin Pro - backup completo ....zip")
    <destino>  a pasta onde o sistema vai ficar (é criada; ex.: C:\\Users\\voce\\Documents\\Fin Pro)

O que ele faz:
  1. copia o código-fonte (pasta ``codigo``) para o destino;
  2. coloca em ``destino/dados`` a cópia mais recente de cada banco (boletos, empresas, diesel), a pasta ``arquivos``
     (boletos, comprovantes, cupons, canhotos…) e as configurações; o ``.env`` volta para a pasta do sistema;
  3. se o git estiver instalado, recria o histórico de versões a partir de ``versoes/finpro.bundle``.

Nada é apagado do backup. Se o destino já tiver dados (``dados/boletos.db``), ele para — a menos que você use
``--forcar`` (aí os dados existentes são guardados antes numa pasta ``dados - antes da restauração``).

Usa só a biblioteca padrão do Python, para rodar num computador novo antes de instalar qualquer coisa.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

RE_COPIA = re.compile(r"^(boletos|empresas|diesel)-(\d{4}-\d{2}-\d{2})\.db$")
NOME_BUNDLE = "finpro.bundle"


class ErroRestauracao(RuntimeError):
    """Mensagem pronta para a pessoa ler."""


def _saida_utf8() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _copiar_arvore(origem: Path, destino: Path) -> int:
    quantidade = 0
    for caminho in sorted(origem.rglob("*")):
        if caminho.is_file():
            alvo = destino / caminho.relative_to(origem)
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(caminho, alvo)
            quantidade += 1
    return quantidade


def bancos_mais_recentes(backup: Path) -> dict[str, Path]:
    """De cada banco (boletos, empresas, diesel), a cópia de data mais nova."""
    melhores: dict[str, Path] = {}
    pasta = backup / "planilha"
    for caminho in pasta.iterdir() if pasta.is_dir() else []:
        encontrado = RE_COPIA.match(caminho.name)
        if encontrado and (encontrado.group(1) not in melhores or caminho.name > melhores[encontrado.group(1)].name):
            melhores[encontrado.group(1)] = caminho
    return melhores


def _git(*argumentos: str, pasta: Path) -> bool:
    try:
        return subprocess.run(["git", *argumentos], cwd=pasta, capture_output=True, timeout=180).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def restaurar_versoes(backup: Path, destino: Path) -> str:
    """Recria o repositório (todas as versões) na pasta restaurada. Devolve o que aconteceu, em uma frase."""
    bundle = backup / "versoes" / NOME_BUNDLE
    if not bundle.is_file():
        return "este backup não tem histórico de versões"
    guardado = destino / "versoes-do-backup" / NOME_BUNDLE
    guardado.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundle, guardado)
    if (destino / ".git").exists():
        return "a pasta já tinha um repositório; o histórico do backup ficou em versoes-do-backup"
    if not _git("--version", pasta=destino):
        return ("o git não está instalado: o histórico ficou guardado em versoes-do-backup\\finpro.bundle "
                "(instale o git e rode o restaurador de novo, se quiser as versões)")
    if not (_git("init", "-q", "-b", "main", pasta=destino)
            and _git("fetch", "-q", "--update-head-ok", str(guardado), "+refs/heads/*:refs/heads/*",
                     "+refs/tags/*:refs/tags/*", pasta=destino)):
        shutil.rmtree(destino / ".git", ignore_errors=True)
        return "não foi possível ler o histórico (o arquivo ficou em versoes-do-backup)"
    _git("symbolic-ref", "HEAD", "refs/heads/main", pasta=destino)
    _git("reset", "-q", pasta=destino)  # o índice passa a apontar para a última versão; os arquivos já estão no lugar
    shutil.rmtree(guardado.parent, ignore_errors=True)
    return "histórico de versões restaurado (git)"


def restaurar(backup: Path, destino: Path, forcar: bool = False, sem_codigo: bool = False) -> dict:
    """Restaura o backup (pasta) em ``destino``. Devolve um resumo do que foi copiado."""
    backup, destino = Path(backup), Path(destino)
    if not backup.is_dir():
        raise ErroRestauracao(f"Não encontrei a pasta do backup: {backup}")
    bancos = bancos_mais_recentes(backup)
    tem_codigo = (backup / "codigo").is_dir() and not sem_codigo
    if not bancos and not tem_codigo and not (backup / "arquivos").is_dir():
        raise ErroRestauracao("Esta pasta não parece um backup do Fin Pro (não tem 'planilha', 'arquivos' nem 'codigo').")
    try:
        if destino.resolve() == backup.resolve() or backup.resolve() in destino.resolve().parents:
            raise ErroRestauracao("Escolha um destino fora da pasta do backup.")
    except OSError:
        pass

    dados = destino / "dados"
    guardado = None
    if any((dados / f"{nome}.db").exists() for nome in ("boletos", "empresas", "diesel")):
        if not forcar:
            raise ErroRestauracao(
                f"A pasta {dados} já tem dados do Fin Pro. Para não apagar nada por engano, a restauração parou.\n"
                "Escolha outra pasta de destino, ou use --forcar (os dados atuais são guardados antes numa pasta à parte).")
        guardado = destino / f"dados - antes da restauração {datetime.now():%Y-%m-%d %H%M%S}"
        shutil.move(str(dados), str(guardado))

    resumo = {"destino": str(destino), "codigo": 0, "bancos": [], "arquivos": 0, "configuracoes": 0, "versoes": "",
              "dados_anteriores": str(guardado) if guardado else None}
    destino.mkdir(parents=True, exist_ok=True)
    if tem_codigo:
        resumo["codigo"] = _copiar_arvore(backup / "codigo", destino)
    dados.mkdir(parents=True, exist_ok=True)
    for nome, copia in sorted(bancos.items()):
        shutil.copy2(copia, dados / f"{nome}.db")
        resumo["bancos"].append(f"{nome}.db (cópia de {RE_COPIA.match(copia.name).group(2)})")
    if (backup / "arquivos").is_dir():
        resumo["arquivos"] = _copiar_arvore(backup / "arquivos", dados / "arquivos")
    configuracoes = backup / "configuracoes"
    for caminho in sorted(configuracoes.iterdir()) if configuracoes.is_dir() else []:
        if caminho.is_file():
            shutil.copy2(caminho, destino / ".env" if caminho.name == ".env" else dados / caminho.name)
            resumo["configuracoes"] += 1
    if tem_codigo:
        resumo["versoes"] = restaurar_versoes(backup, destino)
    return resumo


def restaurar_de(origem: Path, destino: Path, forcar: bool = False, sem_codigo: bool = False) -> dict:
    """Aceita a pasta do backup ou um pacote .zip (que é aberto numa pasta temporária)."""
    origem = Path(origem)
    if origem.is_file() and origem.suffix.lower() == ".zip":
        with zipfile.ZipFile(origem) as pacote:
            if pacote.testzip() is not None:
                raise ErroRestauracao("O pacote .zip está corrompido. Use outro pacote ou a pasta do backup.")
            with tempfile.TemporaryDirectory(prefix="finpro-restaurar-") as temporaria:
                pacote.extractall(temporaria)
                return restaurar(Path(temporaria), destino, forcar, sem_codigo)
    return restaurar(origem, destino, forcar, sem_codigo)


def main(argumentos: list[str] | None = None) -> int:
    _saida_utf8()
    argumentos = list(sys.argv[1:] if argumentos is None else argumentos)
    opcoes = {a for a in argumentos if a.startswith("--")}
    posicionais = [a for a in argumentos if not a.startswith("--")]
    if len(posicionais) != 2 or opcoes - {"--forcar", "--sem-codigo"}:
        print(__doc__)
        return 2
    origem, destino = Path(posicionais[0].strip('"')), Path(posicionais[1].strip('"'))
    try:
        resumo = restaurar_de(origem, destino, "--forcar" in opcoes, "--sem-codigo" in opcoes)
    except ErroRestauracao as exc:
        print(f"\nNÃO RESTAURADO: {exc}")
        return 1
    print(f"\nFin Pro restaurado em: {resumo['destino']}")
    print(f"  Código-fonte:     {resumo['codigo']} arquivo(s)")
    print(f"  Bancos de dados:  {', '.join(resumo['bancos']) or 'nenhum no backup'}")
    print(f"  Arquivos:         {resumo['arquivos']} (boletos, comprovantes, fotos…)")
    print(f"  Configurações:    {resumo['configuracoes']} arquivo(s)")
    if resumo["versoes"]:
        print(f"  Versões:          {resumo['versoes']}")
    if resumo["dados_anteriores"]:
        print(f"  Os dados que estavam lá foram guardados em: {resumo['dados_anteriores']}")
    print("\nPróximos passos:")
    print("  1. Na pasta restaurada, dê dois cliques em iniciar.bat (na primeira vez ele instala o que falta).")
    print("  2. Só ligue os bots do Telegram aqui depois de desligar o Fin Pro do computador antigo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

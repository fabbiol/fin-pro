"""Arquivo de log com limite de tamanho: ``dados/leitor.log`` nunca cresce sem parar.

Quando passa de 2 MB, o arquivo atual vira ``leitor.log.1`` (o ``.1`` vira ``.2``...) e um novo começa.
São guardados no máximo 5 arquivos antigos (cerca de 12 MB no total). Também é possível limpar pela tela
Saúde do sistema.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

TAMANHO_MAXIMO = 2 * 1024 * 1024
ARQUIVOS_ANTIGOS = 5


def arquivos_de_log(caminho: Path) -> list[Path]:
    caminho = Path(caminho)
    return [p for p in [caminho, *(caminho.with_name(f"{caminho.name}.{n}") for n in range(1, ARQUIVOS_ANTIGOS + 1))] if p.exists()]


class ArquivoRotativo:
    """Objeto de arquivo (write/flush) usado como saída do programa quando não há console (pythonw)."""

    def __init__(self, caminho: Path, tamanho_maximo: int = TAMANHO_MAXIMO, antigos: int = ARQUIVOS_ANTIGOS):
        self.caminho = Path(caminho)
        self.tamanho_maximo = tamanho_maximo
        self.antigos = antigos
        self._lock = threading.Lock()
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._arquivo = open(self.caminho, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        self._girar_se_preciso()

    def _girar_se_preciso(self) -> None:
        try:
            if self._arquivo.tell() < self.tamanho_maximo:
                return
        except (OSError, ValueError):
            return
        self._arquivo.close()
        for n in range(self.antigos, 0, -1):
            origem = self.caminho if n == 1 else self.caminho.with_name(f"{self.caminho.name}.{n - 1}")
            destino = self.caminho.with_name(f"{self.caminho.name}.{n}")
            try:
                if origem.exists():
                    os.replace(origem, destino)
            except OSError:
                pass
        self._arquivo = open(self.caminho, "a", encoding="utf-8", buffering=1)  # noqa: SIM115

    def write(self, texto: str) -> int:
        with self._lock:
            escrito = self._arquivo.write(texto)
            if "\n" in texto:
                self._girar_se_preciso()
            return escrito

    def flush(self) -> None:
        with self._lock:
            self._arquivo.flush()

    def isatty(self) -> bool:
        return False

    def limpar_antigos(self) -> int:
        """Apaga os arquivos antigos (.1 a .5) e esvazia o atual. Devolve quantos bytes foram liberados."""
        with self._lock:
            liberados = 0
            for antigo in arquivos_de_log(self.caminho)[1:]:
                liberados += antigo.stat().st_size
                antigo.unlink(missing_ok=True)
            self._arquivo.flush()
            liberados += self._arquivo.tell()
            self._arquivo.seek(0)
            self._arquivo.truncate()
            return liberados


saida_atual: ArquivoRotativo | None = None


def limpar(caminho: Path) -> int:
    """Limpa os logs mesmo quando o programa roda com console (sem ArquivoRotativo)."""
    if saida_atual is not None and saida_atual.caminho == Path(caminho):
        return saida_atual.limpar_antigos()
    liberados = 0
    for arquivo in arquivos_de_log(caminho):
        liberados += arquivo.stat().st_size
        if arquivo == Path(caminho):
            arquivo.write_text("", encoding="utf-8")
        else:
            arquivo.unlink(missing_ok=True)
    return liberados

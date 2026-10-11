"""Ponte entre o servidor e a janela do aplicativo.

Quando o sistema roda como aplicativo de desktop, ``app.desktop`` registra aqui as funções que mostram a
janela e encerram o aplicativo. A API usa isso para trazer a janela para a frente (ao clicar numa
notificação, abrir o atalho de novo com o app já aberto etc.). No modo navegador nada é registrado.
"""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_mostrar: Callable[[str | None], None] | None = None
_encerrar: Callable[[], None] | None = None


def registrar(mostrar: Callable[[str | None], None], encerrar: Callable[[], None] | None = None) -> None:
    global _mostrar, _encerrar
    with _lock:
        _mostrar, _encerrar = mostrar, encerrar


def desregistrar() -> None:
    global _mostrar, _encerrar
    with _lock:
        _mostrar = _encerrar = None


def ativa() -> bool:
    return _mostrar is not None


def mostrar(rota: str | None = None) -> bool:
    with _lock:
        funcao = _mostrar
    if funcao is None:
        return False
    funcao(rota)
    return True


def encerrar() -> bool:
    with _lock:
        funcao = _encerrar
    if funcao is None:
        return False
    threading.Timer(0.3, funcao).start()  # deixa a resposta HTTP sair antes de fechar
    return True

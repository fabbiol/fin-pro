"""Leituras em segundo plano com progresso.

PDFs escaneados podem levar dezenas de segundos. Em vez de segurar a requisição HTTP, a leitura
vira uma tarefa: o navegador recebe um id na hora e acompanha a página e a etapa em andamento.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

log = logging.getLogger(__name__)

DESCRICOES = {
    "na_fila": "Na fila",
    "iniciando": "Preparando o arquivo",
    "codigo_barras": "Lendo o código de barras",
    "ocr": "Reconhecendo o texto (OCR)",
    "concluindo": "Conferindo os dados",
    "concluida": "Concluída",
    "erro": "Falhou",
}
_PESO_ETAPA = {"iniciando": 0.0, "codigo_barras": 0.15, "ocr": 0.35, "concluindo": 1.0}


class ErroTarefa(RuntimeError):
    def __init__(self, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo


@dataclass
class Tarefa:
    id: str
    nome: str
    status: str = "na_fila"  # na_fila | processando | concluida | erro
    etapa: str = "na_fila"
    pagina: int = 0
    paginas: int = 0
    resultado: dict | None = None
    erro: dict | None = None
    criada_em: float = field(default_factory=time.time)
    atualizada_em: float = field(default_factory=time.time)

    @property
    def percentual(self) -> int:
        if self.status == "concluida":
            return 100
        if not self.paginas:
            return 0
        feito = max(0, self.pagina - 1) + _PESO_ETAPA.get(self.etapa, 0.0)
        return max(1, min(99, round(feito / self.paginas * 100)))

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "status": self.status,
            "etapa": self.etapa,
            "descricao": DESCRICOES.get(self.etapa, self.etapa),
            "pagina": self.pagina,
            "paginas": self.paginas,
            "percentual": self.percentual,
            "segundos": round(time.time() - self.criada_em, 1),
            "resultado": self.resultado,
            "erro": self.erro,
        }


class GerenciadorTarefas:
    def __init__(self, max_paralelo: int = 2, validade_segundos: int = 3600):
        self._max_paralelo = max_paralelo
        self._executor: ThreadPoolExecutor | None = None
        self._tarefas: dict[str, Tarefa] = {}
        self._lock = threading.Lock()
        self._validade = validade_segundos

    def criar(self, nome: str, funcao: Callable[[Callable[..., None]], dict]) -> Tarefa:
        """``funcao(ao_progresso)`` executa a leitura e devolve o resultado."""
        tarefa = Tarefa(uuid.uuid4().hex, nome)
        with self._lock:
            self._limpar()
            self._tarefas[tarefa.id] = tarefa

        def ao_progresso(pagina: int | None = None, paginas: int | None = None, etapa: str | None = None, **_):
            if pagina is not None:
                tarefa.pagina = pagina
            if paginas is not None:
                tarefa.paginas = paginas
            if etapa:
                tarefa.etapa = etapa
            tarefa.atualizada_em = time.time()

        def executar():
            tarefa.status = "processando"
            tarefa.etapa = "iniciando"
            try:
                tarefa.resultado = funcao(ao_progresso)
                tarefa.status = tarefa.etapa = "concluida"
            except ErroTarefa as exc:
                tarefa.erro = {"codigo": exc.codigo, "mensagem": str(exc)}
                tarefa.status = tarefa.etapa = "erro"
            except Exception:
                log.exception("Falha inesperada na leitura de %s", nome)
                tarefa.erro = {"codigo": "erro_interno", "mensagem": "Falha inesperada ao ler o arquivo. Tente novamente."}
                tarefa.status = tarefa.etapa = "erro"
            tarefa.atualizada_em = time.time()

        with self._lock:
            if self._executor is None:  # criado sob demanda (e recriado se o servidor reiniciar)
                self._executor = ThreadPoolExecutor(max_workers=self._max_paralelo, thread_name_prefix="leitura")
            self._executor.submit(executar)
        return tarefa

    def obter(self, tarefa_id: str) -> Tarefa | None:
        with self._lock:
            return self._tarefas.get(tarefa_id)

    def _limpar(self) -> None:
        limite = time.time() - self._validade
        for chave in [k for k, t in self._tarefas.items() if t.status in ("concluida", "erro") and t.atualizada_em < limite]:
            del self._tarefas[chave]

    def encerrar(self) -> None:
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None

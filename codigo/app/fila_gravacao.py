"""Fila de gravação na planilha.

Quando a planilha está aberta no Excel (arquivo bloqueado), lançamentos e alterações — de boletos e de
Pix — não se perdem: ficam guardados em ``dados/gravacao_pendente.json`` e são gravados automaticamente,
todos de uma vez, assim que o arquivo for fechado. Enquanto isso aparecem nas listas, no painel e nas
notificações, marcados como "aguardando gravação".

Lançamentos ainda não gravados recebem IDs provisórios negativos (-1, -2...). Alterações feitas neles
são aplicadas no próprio lançamento pendente; excluí-los simplesmente cancela o lançamento.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import date, datetime
from pathlib import Path

from .planilha import ABAS, CAMPOS_DATA, PlanilhaBloqueadaError, RegistroNaoEncontrado

log = logging.getLogger(__name__)

INTERVALO_TENTATIVAS = 15


def _para_json(dados: dict, aba: str) -> dict:
    editaveis = ABAS[aba].editaveis
    return {chave: valor.isoformat() if isinstance(valor, (date, datetime)) else valor
            for chave, valor in dados.items() if chave in editaveis}


def _de_json(dados: dict) -> dict:
    saida = dict(dados)
    for chave in CAMPOS_DATA:
        if isinstance(saida.get(chave), str):
            try:
                saida[chave] = date.fromisoformat(saida[chave][:10]) if saida[chave] else None
            except ValueError:
                saida[chave] = None
    return saida


def _agora() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _aba(operacao: dict) -> str:
    return operacao.get("aba") or "boletos"


class FilaGravacao:
    def __init__(self, planilha, caminho: Path, intervalo: int = INTERVALO_TENTATIVAS):
        self.planilha = planilha
        self.caminho = Path(caminho)
        self.intervalo = intervalo
        self._lock = threading.RLock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        estado = self._ler()
        self._operacoes: list[dict] = estado.get("operacoes", [])
        self._sequencia = int(estado.get("sequencia", 0))
        self.ultima_tentativa: str | None = estado.get("ultima_tentativa")
        self.ultimo_erro: str | None = estado.get("ultimo_erro")
        self.ultimo_resultado: dict | None = estado.get("ultimo_resultado")

    # ------------------------------------------------------------------ persistência

    def _ler(self) -> dict:
        if not self.caminho.exists():
            return {}
        try:
            return json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            log.exception("Arquivo da fila de gravação ilegível")
            return {}

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps({
            "operacoes": self._operacoes,
            "sequencia": self._sequencia,
            "ultima_tentativa": self.ultima_tentativa,
            "ultimo_erro": self.ultimo_erro,
            "ultimo_resultado": self.ultimo_resultado,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ operações

    @property
    def pendentes(self) -> int:
        with self._lock:
            return len(self._operacoes)

    def _operacao_de_adicao(self, id_provisorio: int, aba: str) -> dict | None:
        return next((o for o in self._operacoes
                     if o["tipo"] == "adicionar" and o["id"] == id_provisorio and _aba(o) == aba), None)

    def enfileirar_adicao(self, dados: dict, aba: str = "boletos", usuario: str = "") -> dict:
        with self._lock:
            self._sequencia += 1
            operacao = {"op_id": uuid.uuid4().hex[:12], "tipo": "adicionar", "aba": aba, "id": -self._sequencia,
                        "dados": _para_json(dados, aba), "criado_em": _agora(), "usuario": usuario}
            self._operacoes.append(operacao)
            self._gravar()
            return self._registro_provisorio(operacao)

    def enfileirar_atualizacao(self, id_: int, dados: dict, aba: str = "boletos", usuario: str = "") -> None:
        with self._lock:
            novos = _para_json(dados, aba)
            if id_ < 0:
                operacao = self._operacao_de_adicao(id_, aba)
                if operacao is None:
                    raise RegistroNaoEncontrado(id_)
                operacao["dados"].update(novos)
            else:
                existente = next((o for o in self._operacoes
                                  if o["tipo"] == "atualizar" and o["id"] == id_ and _aba(o) == aba), None)
                if existente:
                    existente["dados"].update(novos)
                    existente["usuario"] = usuario or existente.get("usuario", "")
                else:
                    self._operacoes.append({"op_id": uuid.uuid4().hex[:12], "tipo": "atualizar", "aba": aba, "id": id_,
                                            "dados": novos, "criado_em": _agora(), "usuario": usuario})
            self._gravar()

    def cancelar(self, op_id: str) -> bool:
        with self._lock:
            antes = len(self._operacoes)
            self._operacoes = [o for o in self._operacoes if o["op_id"] != op_id]
            if len(self._operacoes) != antes:
                self._gravar()
                return True
            return False

    def cancelar_provisorio(self, id_provisorio: int, aba: str = "boletos") -> None:
        with self._lock:
            operacao = self._operacao_de_adicao(id_provisorio, aba)
            if operacao is None:
                raise RegistroNaoEncontrado(id_provisorio)
            self.cancelar(operacao["op_id"])

    # ------------------------------------------------------------------ leitura combinada

    @staticmethod
    def _registro_provisorio(operacao: dict) -> dict:
        definicao = ABAS[_aba(operacao)]
        criado = datetime.fromisoformat(operacao["criado_em"])
        registro = {c.chave: None for c in definicao.colunas}
        registro.update(_de_json(operacao["dados"]))
        registro.update(id=operacao["id"], data_lancamento=criado, atualizado_em=criado, lancado_por=operacao.get("usuario") or "",
                        pendente_gravacao=True, operacao_pendente=operacao["op_id"])
        registro["status"] = registro.get("status") or "Pendente"
        for chave in definicao.textos:
            registro[chave] = registro.get(chave) or ""
        return registro

    def registro_provisorio(self, id_provisorio: int, aba: str = "boletos") -> dict:
        with self._lock:
            operacao = self._operacao_de_adicao(id_provisorio, aba)
            if operacao is None:
                raise RegistroNaoEncontrado(id_provisorio)
            return self._registro_provisorio(operacao)

    def sobrepor(self, registros: list[dict], aba: str = "boletos") -> list[dict]:
        """Registros da planilha + alterações e lançamentos que ainda aguardam gravação."""
        with self._lock:
            operacoes = [dict(o, dados=dict(o["dados"])) for o in self._operacoes if _aba(o) == aba]
        if not operacoes:
            return registros
        por_id = {r["id"]: r for r in registros}
        for operacao in operacoes:
            if operacao["tipo"] == "atualizar" and operacao["id"] in por_id:
                por_id[operacao["id"]] = {**por_id[operacao["id"]], **_de_json(operacao["dados"]),
                                          "pendente_gravacao": True, "operacao_pendente": operacao["op_id"]}
        combinados = list(por_id.values())
        combinados.extend(self._registro_provisorio(o) for o in operacoes if o["tipo"] == "adicionar")
        return combinados

    # ------------------------------------------------------------------ gravação

    def processar(self) -> dict | None:
        """Tenta gravar tudo o que está pendente numa única abertura da planilha."""
        with self._lock:
            if not self._operacoes:
                return None
            operacoes = list(self._operacoes)
            self.ultima_tentativa = _agora()
            try:
                resultados = self.planilha.aplicar_lote([
                    {"tipo": o["tipo"], "aba": _aba(o), "id": o["id"] if o["tipo"] != "adicionar" else None,
                     "dados": _de_json(o["dados"]), "usuario": o.get("usuario") or ""}
                    for o in operacoes
                ])
            except PlanilhaBloqueadaError as exc:
                self.ultimo_erro = str(exc)
                self._gravar()
                return {"gravados": 0, "bloqueada": True}
            except Exception as exc:
                log.exception("Falha ao gravar a fila na planilha")
                self.ultimo_erro = f"Falha ao gravar na planilha: {exc}"
                self._gravar()
                return {"gravados": 0, "bloqueada": False, "erro": str(exc)}

            falhas = [{"op_id": o["op_id"], "tipo": o["tipo"], "aba": _aba(o), "id": o["id"]}
                      for o, r in zip(operacoes, resultados) if not r.get("ok")]
            ids = {o["id"]: r["registro"]["id"] for o, r in zip(operacoes, resultados)
                   if r.get("ok") and o["tipo"] == "adicionar"}
            gravados = len(operacoes) - len(falhas)
            self._operacoes = []
            self.ultimo_erro = None
            self.ultimo_resultado = {"quando": _agora(), "gravados": gravados, "falhas": len(falhas)}
            self._gravar()
            log.info("Fila de gravação: %d operação(ões) gravada(s) na planilha", gravados)
            return {"gravados": gravados, "bloqueada": False, "falhas": falhas, "ids": ids}

    def status(self) -> dict:
        with self._lock:
            return {
                "pendentes": len(self._operacoes),
                "bloqueada": bool(self._operacoes and self.ultimo_erro),
                "ultima_tentativa": self.ultima_tentativa,
                "ultimo_erro": self.ultimo_erro if self._operacoes else None,
                "ultimo_resultado": self.ultimo_resultado,
                "itens": [{
                    "op_id": o["op_id"], "tipo": o["tipo"], "aba": _aba(o), "id": o["id"], "criado_em": o["criado_em"],
                    "beneficiario": o["dados"].get("beneficiario") or o["dados"].get("recebedor"),
                    "valor": o["dados"].get("valor"), "vencimento": o["dados"].get("vencimento"),
                    "status": o["dados"].get("status"),
                } for o in self._operacoes],
            }

    # ------------------------------------------------------------------ agendador

    def iniciar_agendador(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            while not self._parar.wait(self.intervalo):
                try:
                    if self.pendentes:
                        self.processar()
                except Exception:
                    log.exception("Falha na fila de gravação")

        self._thread = threading.Thread(target=laco, name="fila-gravacao", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

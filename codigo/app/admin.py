"""Senha de administrador: protege as funções sensíveis (importação de boletos de outros sistemas).

* a senha só pode ser criada e trocada no computador onde o sistema está instalado (trocar exige a atual);
* é guardada com PBKDF2 em ``dados/admin.json`` — nunca em texto;
* após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos;
* entrar abre uma sessão de 20 minutos (renovada a cada uso) num cookie HttpOnly; trocar a senha ou
  clicar em "Bloquear" encerra as sessões.

Esqueceu a senha? No computador, feche o sistema, apague ``dados/admin.json`` e crie uma nova.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path

COOKIE = "leitor_admin"
TAMANHO_MINIMO = 6
ITERACOES = 200_000
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 300
DURACAO_SESSAO = 20 * 60


class GerenciadorAdmin:
    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self._lock = threading.Lock()
        self._sessoes: dict[str, float] = {}
        self._falhas: dict[str, list[float]] = {}
        self._estado = self._ler()

    # ------------------------------------------------------------------ senha

    def _ler(self) -> dict:
        try:
            return json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    @property
    def senha_definida(self) -> bool:
        return bool(self._estado.get("senha_hash"))

    @staticmethod
    def _hash(senha: str, sal: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", (senha or "").encode("utf-8"), sal, ITERACOES).hex()

    def definir_senha(self, nova: str) -> None:
        if len(nova or "") < TAMANHO_MINIMO:
            raise ValueError(f"A senha de administrador precisa ter pelo menos {TAMANHO_MINIMO} caracteres.")
        sal = secrets.token_bytes(16)
        calculado = self._hash(nova, sal)
        with self._lock:
            self._estado = {"senha_hash": calculado, "sal": sal.hex(), "definida_em": datetime.now().isoformat(timespec="seconds")}
            self._gravar()
            self._sessoes.clear()  # trocar a senha bloqueia todos os aparelhos liberados

    def verificar(self, senha: str) -> bool:
        with self._lock:
            estado = dict(self._estado)
        if not estado.get("senha_hash"):
            return False
        return hmac.compare_digest(self._hash(senha, bytes.fromhex(estado["sal"])), estado["senha_hash"])

    # ------------------------------------------------------------------ tentativas

    def segundos_bloqueado(self, ip: str) -> int:
        agora = time.time()
        with self._lock:
            recentes = [t for t in self._falhas.get(ip, []) if agora - t < BLOQUEIO_SEGUNDOS]
            self._falhas[ip] = recentes
            if len(recentes) >= MAX_TENTATIVAS:
                return max(1, int(BLOQUEIO_SEGUNDOS - (agora - recentes[-MAX_TENTATIVAS])))
        return 0

    def registrar_falha(self, ip: str) -> None:
        with self._lock:
            self._falhas.setdefault(ip, []).append(time.time())

    # ------------------------------------------------------------------ sessões

    def entrar(self, senha: str, ip: str) -> tuple[str | None, int]:
        """Devolve (token da sessão ou None, segundos de bloqueio)."""
        restante = self.segundos_bloqueado(ip)
        if restante:
            return None, restante
        if not self.verificar(senha):
            self.registrar_falha(ip)
            return None, self.segundos_bloqueado(ip)
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._falhas.pop(ip, None)
            self._sessoes[token] = time.time() + DURACAO_SESSAO
        return token, 0

    def autorizado(self, token: str | None) -> bool:
        if not token or not self.senha_definida:
            return False
        agora = time.time()
        with self._lock:
            for chave, expira in list(self._sessoes.items()):
                if expira < agora:
                    del self._sessoes[chave]
            if token not in self._sessoes:
                return False
            self._sessoes[token] = agora + DURACAO_SESSAO
            return True

    def sair(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessoes.pop(token, None)

    def status(self, token: str | None, ip: str) -> dict:
        return {
            "senha_definida": self.senha_definida,
            "autorizado": self.autorizado(token),
            "bloqueado_segundos": self.segundos_bloqueado(ip),
            "minutos_sessao": DURACAO_SESSAO // 60,
        }

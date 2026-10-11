"""Acesso pelo celular (rede local / Wi-Fi), ligado e desligado pela tela de Configurações.

O servidor principal continua ouvindo só em 127.0.0.1 (este computador). Ao liberar o acesso pela rede,
um segundo servidor — no mesmo processo e servindo a mesma aplicação — passa a ouvir nos endereços da
rede local (ex.: 192.168.0.10:8000). Desligar fecha esse acesso na hora, sem reiniciar o sistema.

* A senha é obrigatória e fica guardada como hash PBKDF2 (nunca em texto) em ``dados/rede.json``.
* Trocar a senha desconecta os aparelhos que já tinham entrado.
* Um vigia confere a cada minuto se o endereço do computador mudou (ex.: roteador reiniciou) e reabre o acesso.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import uvicorn

log = logging.getLogger(__name__)

ITERACOES_HASH = 200_000
TAMANHO_MINIMO_SENHA = 6
INTERVALO_VIGIA = 60
MAX_ACESSOS_REGISTRADOS = 30


def _faixa_privada(ip: str) -> bool:
    partes = ip.split(".")
    if len(partes) != 4 or not all(p.isdigit() for p in partes):
        return False
    a, b = int(partes[0]), int(partes[1])
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def descobrir_enderecos() -> list[str]:
    """Endereços IPv4 privados deste computador; o da interface principal vem primeiro."""
    enderecos: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonda:
            sonda.connect(("8.8.8.8", 80))  # UDP "connect" não envia nada: só descobre a interface de saída
            principal = sonda.getsockname()[0]
            if _faixa_privada(principal):
                enderecos.append(principal)
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if _faixa_privada(ip) and ip not in enderecos:
                enderecos.append(ip)
    except OSError:
        pass
    return enderecos


def descrever_aparelho(agente: str | None) -> str:
    agente = agente or ""
    sistema = next((nome for chave, nome in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                                               ("Windows", "Windows"), ("Mac OS", "Mac"), ("Linux", "Linux")) if chave in agente), "Aparelho")
    navegador = next((nome for chave, nome in (("SamsungBrowser", "Samsung Internet"), ("Edg/", "Edge"), ("OPR/", "Opera"),
                                                 ("Firefox", "Firefox"), ("CriOS", "Chrome"), ("Chrome", "Chrome"),
                                                 ("Safari", "Safari")) if chave in agente), "navegador")
    return f"{sistema} · {navegador}"


class GerenciadorRede:
    def __init__(self, app, caminho: Path, porta: int, *, descobrir: Callable[[], list[str]] = descobrir_enderecos,
                 rede_via_env: bool = False, senha_externa: Callable[[], bool] = lambda: False):
        self.app = app
        self.caminho = Path(caminho)
        self.porta = porta
        self.via_env = rede_via_env
        self._descobrir = descobrir
        self._senha_externa = senha_externa
        self._lock = threading.RLock()
        self._servidor: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._sockets: list[socket.socket] = []
        self._enderecos_ativos: list[str] = []
        self._acessos: dict[str, dict] = {}
        self._parar_vigia = threading.Event()
        self._vigia: threading.Thread | None = None
        self.erro: str | None = None
        self._estado = self._ler()

    # ------------------------------------------------------------------ estado e senha

    def _ler(self) -> dict:
        estado = {"ativo": False, "senha_hash": "", "sal": "", "segredo": ""}
        if self.caminho.exists():
            try:
                salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
                estado.update({k: v for k, v in salvo.items() if k in estado})
            except (OSError, json.JSONDecodeError):
                log.warning("Configuração de rede ilegível; acesso pela rede desligado")
        return estado

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, indent=2), encoding="utf-8")
        os.replace(temporario, self.caminho)

    @property
    def ativo(self) -> bool:
        return bool(self._estado["ativo"])

    @property
    def senha_definida(self) -> bool:
        return bool(self._estado["senha_hash"])

    def definir_senha(self, senha: str) -> None:
        if len(senha or "") < TAMANHO_MINIMO_SENHA:
            raise ValueError(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
        sal = secrets.token_bytes(16)
        calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES_HASH)
        with self._lock:
            self._estado.update(senha_hash=calculado.hex(), sal=sal.hex(), segredo=secrets.token_hex(32))
            self._gravar()

    def verificar_senha(self, senha: str) -> bool:
        with self._lock:
            if not self.senha_definida:
                return False
            sal, esperado = bytes.fromhex(self._estado["sal"]), self._estado["senha_hash"]
        calculado = hashlib.pbkdf2_hmac("sha256", (senha or "").encode("utf-8"), sal, ITERACOES_HASH)
        return hmac.compare_digest(calculado.hex(), esperado)

    def token_sessao(self) -> str:
        return hmac.new(bytes.fromhex(self._estado["segredo"]), b"sessao-rede", hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------ acessos

    def registrar_acesso(self, ip: str, agente: str | None) -> None:
        with self._lock:
            self._acessos[ip] = {"ip": ip, "aparelho": descrever_aparelho(agente), "ultimo": datetime.now().isoformat(timespec="seconds")}
            if len(self._acessos) > MAX_ACESSOS_REGISTRADOS:
                mais_antigo = min(self._acessos.values(), key=lambda a: a["ultimo"])
                del self._acessos[mais_antigo["ip"]]

    # ------------------------------------------------------------------ status

    @property
    def rodando(self) -> bool:
        return bool(self._servidor and self._thread and self._thread.is_alive() and self._servidor.started)

    def status(self) -> dict:
        rodando = self.rodando
        enderecos = list(self._enderecos_ativos) if rodando else self._descobrir()
        return {
            "ativo": self.ativo or self.via_env,
            "via_env": self.via_env,
            "rodando": rodando or self.via_env,
            "porta": self.porta,
            "enderecos": enderecos,
            "urls": [f"http://{ip}:{self.porta}" for ip in enderecos],
            "senha_definida": self.senha_definida,
            "erro": self.erro if self.ativo and not rodando else None,
            "acessos": sorted(self._acessos.values(), key=lambda a: a["ultimo"], reverse=True),
        }

    # ------------------------------------------------------------------ ligar / desligar

    def ativar(self) -> dict:
        if self.via_env:
            raise ValueError("O acesso pela rede já está liberado pelo arquivo .env (LEITOR_HOST=0.0.0.0).")
        if not (self.senha_definida or self._senha_externa()):
            raise ValueError("Defina uma senha antes de liberar o acesso pela rede.")
        with self._lock:
            self._estado["ativo"] = True
            self._gravar()
        self.iniciar_servidor()
        self._iniciar_vigia()
        return self.status()

    def desativar(self) -> dict:
        with self._lock:
            self._estado["ativo"] = False
            self._gravar()
        self._parar_vigia.set()
        self.parar_servidor()
        self.erro = None
        return self.status()

    def iniciar_se_ativo(self) -> None:
        if self.ativo and not self.via_env:
            self.iniciar_servidor()
            self._iniciar_vigia()

    def parar(self) -> None:
        self._parar_vigia.set()
        self.parar_servidor()

    def iniciar_servidor(self) -> None:
        with self._lock:
            if self.rodando:
                return
            enderecos = self._descobrir()
            if not enderecos:
                self.erro = "Nenhuma rede local encontrada. Conecte o computador ao Wi-Fi ou ao cabo de rede."
                return
            sockets = []
            for ip in enderecos:
                conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    conexao.bind((ip, self.porta))
                    conexao.listen(128)
                    sockets.append(conexao)
                except OSError as exc:
                    conexao.close()
                    log.warning("Não foi possível abrir %s:%s (%s)", ip, self.porta, exc)
            if not sockets:
                self.erro = f"A porta {self.porta} está em uso por outro programa na rede."
                return

            servidor = uvicorn.Server(uvicorn.Config(self.app, lifespan="off", log_level="warning", access_log=False))
            thread = threading.Thread(target=servidor.run, kwargs={"sockets": sockets}, name="servidor-rede", daemon=True)
            thread.start()
            for _ in range(50):
                if servidor.started or not thread.is_alive():
                    break
                time.sleep(0.1)
            if not servidor.started:
                servidor.should_exit = True
                for conexao in sockets:
                    conexao.close()
                self.erro = "Não foi possível iniciar o acesso pela rede."
                return
            self._servidor, self._thread, self._sockets = servidor, thread, sockets
            self._enderecos_ativos = [s.getsockname()[0] for s in sockets]
            self.erro = None
            log.info("Acesso pela rede liberado: %s", ", ".join(f"http://{ip}:{self.porta}" for ip in self._enderecos_ativos))

    def parar_servidor(self) -> None:
        with self._lock:
            servidor, thread, sockets = self._servidor, self._thread, self._sockets
            self._servidor, self._thread, self._sockets, self._enderecos_ativos = None, None, [], []
        if servidor:
            servidor.should_exit = True
        if thread:
            thread.join(timeout=5)
        for conexao in sockets:
            try:
                conexao.close()
            except OSError:
                pass
        if servidor:
            log.info("Acesso pela rede fechado")

    def _iniciar_vigia(self) -> None:
        if self._vigia and self._vigia.is_alive():
            return
        self._parar_vigia.clear()

        def laco():
            while not self._parar_vigia.wait(INTERVALO_VIGIA):
                try:
                    if not self.ativo:
                        return
                    atuais = set(self._descobrir())
                    if not self.rodando or atuais != set(self._enderecos_ativos):
                        log.info("Endereço de rede mudou (%s); reabrindo o acesso", ", ".join(sorted(atuais)) or "sem rede")
                        self.parar_servidor()
                        self.iniciar_servidor()
                except Exception:
                    log.exception("Falha ao vigiar o acesso pela rede")

        self._vigia = threading.Thread(target=laco, name="vigia-rede", daemon=True)
        self._vigia.start()

"""Backup total para fora do computador: situação, configuração (administrador), "fazer backup agora",
pacote completo em .zip e conferência do backup."""

from __future__ import annotations

import threading
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .. import acesso, backup
from .. import contexto as ctx
from .comum import erro, exigir_admin, somente_local

router = APIRouter()


class ConfigBackupEntrada(BaseModel):
    ativo: bool | None = None
    pasta: str | None = Field(None, max_length=500)
    horario: str | None = Field(None, max_length=5)
    manter_dias: int | None = Field(None, ge=3, le=365)
    codigo: bool | None = None
    pacote: Literal["nunca", "semanal", "mensal"] | None = None
    manter_pacotes: int | None = Field(None, ge=1, le=24)


def _publico(request: Request, status: dict) -> dict:
    """Aparelhos da rede veem a situação, mas não o caminho das pastas deste computador."""
    if acesso.requisicao_local(request):
        return status
    sem_caminhos = lambda d, *fora: {k: v for k, v in (d or {}).items() if k not in fora} or None  # noqa: E731
    return {k: v for k, v in status.items() if k not in ("pasta", "destino")} | {
        "ultimo": sem_caminhos(status.get("ultimo"), "destino"),
        "ultimo_pacote": sem_caminhos(status.get("ultimo_pacote"), "caminho")}


@router.get("/api/backup")
def situacao_backup(request: Request):
    status = ctx.backup.status()
    local = acesso.requisicao_local(request)
    pacotes = [{k: v for k, v in p.items() if local or k != "caminho"} for p in ctx.backup.pacotes()] if status["ativo"] else []
    return {**_publico(request, status), "local": local, "sugestoes": backup.sugerir_pastas() if local else [],
            "pacotes": pacotes}


@router.put("/api/backup/config")
def configurar_backup(entrada: ConfigBackupEntrada, request: Request):
    somente_local(request, precisa_startfile=False)
    exigir_admin(request)
    try:
        ctx.backup.configurar(**entrada.model_dump(exclude_none=True))
    except ValueError as exc:
        raise erro(422, "backup_invalido", str(exc)) from exc
    return situacao_backup(request)


@router.post("/api/backup/agora")
def fazer_backup_agora(request: Request):
    somente_local(request, precisa_startfile=False)
    resultado = ctx.backup.executar()
    if not resultado["ok"]:
        raise erro(422, "backup_falhou", resultado["erro"])
    return situacao_backup(request)


@router.post("/api/backup/pacote")
def gerar_pacote_completo(request: Request):
    """Atualiza o backup e guarda tudo (código, versões, bancos, arquivos e configurações) num único arquivo .zip."""
    somente_local(request, precisa_startfile=False)
    resultado = ctx.backup.gerar_pacote()
    if not resultado["ok"]:
        raise erro(422, "pacote_falhou", resultado["erro"])
    return situacao_backup(request)


@router.post("/api/backup/verificar")
def verificar_backup(request: Request):
    """Confere o backup inteiro: os bancos abrem, nada falta e cada arquivo bate com a impressão digital guardada."""
    somente_local(request, precisa_startfile=False)
    ctx.backup.verificar(completa=True)
    return situacao_backup(request)


@router.post("/api/backup/escolher-pasta")
def escolher_pasta(request: Request):
    """Abre a janela do Windows para escolher a pasta (só no computador onde o sistema está instalado)."""
    somente_local(request, precisa_startfile=False)
    exigir_admin(request)
    escolhida: dict = {}

    def abrir():
        try:
            import tkinter
            from tkinter import filedialog

            janela = tkinter.Tk()
            janela.withdraw()
            janela.attributes("-topmost", True)
            escolhida["pasta"] = filedialog.askdirectory(parent=janela, title="Escolha a pasta do backup (ex.: OneDrive)")
            janela.destroy()
        except Exception as exc:  # sem interface gráfica disponível
            escolhida["erro"] = str(exc)

    thread = threading.Thread(target=abrir, name="escolher-pasta-backup", daemon=True)
    thread.start()
    thread.join(timeout=600)
    if escolhida.get("erro"):
        raise erro(501, "sem_janela", "Não foi possível abrir a janela de pastas. Digite o caminho da pasta.")
    return {"pasta": escolhida.get("pasta") or ""}

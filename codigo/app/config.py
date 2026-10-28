"""Configurações lidas do ambiente (arquivo .env opcional na raiz do projeto)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


NOME_APP = os.getenv("LEITOR_NOME_APP", "Fin Pro")
DEMONSTRACAO = _bool("LEITOR_DEMO", False)  # versão de demonstração: dados de exemplo, nada é enviado para fora

DADOS_DIR = Path(os.getenv("LEITOR_DADOS_DIR") or BASE_DIR / "dados")
PLANILHA_PATH = Path(os.getenv("LEITOR_PLANILHA") or DADOS_DIR / "boletos.xlsx")
FECHAMENTOS_PATH = Path(os.getenv("LEITOR_FECHAMENTOS") or PLANILHA_PATH.parent / "fechamentos.xlsx")
DIESEL_PATH = Path(os.getenv("LEITOR_DIESEL") or PLANILHA_PATH.parent / "diesel.xlsx")
TRANSFERENCIAS_PATH = PLANILHA_PATH.parent / "transferencias.xlsx"
ARQUIVOS_DIR = DADOS_DIR / "arquivos"
BACKUPS_DIR = DADOS_DIR / "backups"
WEB_DIR = BASE_DIR / "web"

HOST = os.getenv("LEITOR_HOST", "127.0.0.1")
PORT = int(os.getenv("LEITOR_PORT", "8000"))
MAX_UPLOAD_MB = int(os.getenv("LEITOR_MAX_UPLOAD_MB", "100"))
MAX_PAGINAS_PDF = int(os.getenv("LEITOR_MAX_PAGINAS_PDF", "30"))
DIAS_MANTER_ARQUIVOS_NAO_LANCADOS = int(os.getenv("LEITOR_DIAS_ARQUIVOS_TEMP", "2"))

URL_APP = os.getenv("LEITOR_URL") or f"http://{'localhost' if HOST in ('0.0.0.0', '127.0.0.1', '::') else HOST}:{PORT}"
NOTIFICACOES_AUTOMATICAS = _bool("LEITOR_NOTIFICACOES_AUTOMATICAS", True)
BACKUP_AUTOMATICO = _bool("LEITOR_BACKUP_AUTOMATICO", True)
# Pasta do backup total quando a configurada não existe (na VPS: o volume /backup do docker-compose)
BACKUP_PASTA = (os.getenv("LEITOR_BACKUP_PASTA") or "").strip()
SENHA_ACESSO = (os.getenv("LEITOR_SENHA_ACESSO") or "").strip()

IA_MODELO = os.getenv("LEITOR_IA_MODELO", "claude-opus-5")
IA_AUTOMATICA = _bool("LEITOR_IA_AUTOMATICA", False)


def operacoes_token() -> str:
    """Token que a Operações (sistema da pedreira) usa para mandar as notas. Vazio = integração desligada."""
    return (os.getenv("OPERACOES_TOKEN") or "").strip()


def bradesco_pix() -> dict[str, str]:
    """API Pix do Bradesco (aba Transferências de clientes), lida a cada uso. Faltando credencial ou certificado, a
    consulta dos Pix recebidos fica desligada. Os valores ficam no Ambiente do EasyPanel; os certificados, numa pasta
    da VPS montada como somente leitura."""
    return {nome: (os.getenv(f"BRADESCO_{nome.upper()}") or "").strip()
            for nome in ("ambiente", "client_id", "client_secret", "cert", "key", "host", "token_path")}


def ia_configurada() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))

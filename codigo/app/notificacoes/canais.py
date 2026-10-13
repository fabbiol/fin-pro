"""Canais de envio: notificação do Windows, Telegram e e-mail (somente biblioteca padrão)."""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import subprocess
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape

from .. import config


# A notificação da área de trabalho só existe no Windows (na VPS o sistema roda em Linux)
WINDOWS = os.name == "nt"


class ErroCanal(RuntimeError):
    pass


# --------------------------------------------------------------------------- Windows

# Usa a API nativa de notificações do Windows 10/11 via PowerShell (nada a instalar).
# O XML vai por variável de ambiente para não haver problema com aspas e acentos.
_SCRIPT_TOAST = r"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($env:LEITOR_TOAST_XML)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
"""


def enviar_windows(titulo: str, mensagem: str, url: str | None = None, url_pago: str | None = None) -> None:
    if os.name != "nt":
        raise ErroCanal("Notificações da área de trabalho estão disponíveis apenas no Windows.")
    if url:
        destino = escape(url, quote=True)
        abertura = f' activationType="protocol" launch="{destino}" scenario="reminder"'
        pago = (f'<action content="Já paguei" activationType="protocol" arguments="{escape(url_pago, quote=True)}"/>'
                if url_pago else "")
        acoes = (f'<actions><action content="Abrir boletos" activationType="protocol" arguments="{destino}"/>{pago}'
                 '<action content="Fechar" activationType="system" arguments="dismiss"/></actions>')
    else:
        abertura, acoes = "", ""
    xml = (
        f"<toast{abertura}><visual><binding template=\"ToastGeneric\">"
        f"<text>{escape(titulo)}</text><text>{escape(mensagem)}</text>"
        "<text placement=\"attribution\">Fin Pro</text>"
        f"</binding></visual>{acoes}<audio src=\"ms-winsoundevent:Notification.Reminder\"/></toast>"
    )
    try:
        resultado = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_TOAST],
            env={**os.environ, "LEITOR_TOAST_XML": xml},
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ErroCanal(f"Não foi possível exibir a notificação do Windows: {exc}") from exc
    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "").strip().splitlines()
        raise ErroCanal("Falha ao exibir a notificação do Windows" + (f": {detalhe[0][:200]}" if detalhe else "."))


# --------------------------------------------------------------------------- Telegram


def _recusar_na_demonstracao(canal: str) -> None:
    if config.DEMONSTRACAO:
        raise ErroCanal(f"Versão de demonstração: o envio por {canal} fica desligado (nada sai deste computador).")


def _telegram(token: str, metodo: str, dados: dict | None = None):
    _recusar_na_demonstracao("Telegram")
    requisicao = urllib.request.Request(
        f"https://api.telegram.org/bot{token.strip()}/{metodo}",
        data=json.dumps(dados or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            corpo = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            corpo = json.loads(exc.read().decode("utf-8"))
        except Exception:
            raise ErroCanal(f"O Telegram respondeu com erro HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ErroCanal("Sem conexão com o Telegram. Verifique a internet.") from exc
    if not corpo.get("ok"):
        descricao = corpo.get("description", "erro desconhecido")
        if "Unauthorized" in descricao:
            descricao = "token do bot inválido"
        elif "chat not found" in descricao:
            descricao = "chat não encontrado — a pessoa precisa enviar /start para o bot"
        elif "kicked" in descricao or "not a member" in descricao:
            descricao = "o bot foi removido do grupo"
        elif "blocked" in descricao or "can't initiate" in descricao or "Forbidden" in descricao:
            descricao = "a pessoa ainda não enviou /start para o bot ou bloqueou o bot"
        raise ErroCanal(f"Telegram: {descricao}.")
    return corpo["result"]


def enviar_telegram(token: str, chat_id: str, html: str) -> None:
    _telegram(token, "sendMessage", {"chat_id": chat_id, "text": html, "parse_mode": "HTML", "disable_web_page_preview": True})


def detectar_chat_telegram(token: str) -> dict:
    """Descobre o chat a partir da última mensagem enviada ao bot (o usuário manda /start)."""
    atualizacoes = _telegram(token, "getUpdates", {"limit": 50, "timeout": 0})
    for atualizacao in reversed(atualizacoes):
        conteudo = atualizacao.get("message") or atualizacao.get("channel_post") or atualizacao.get("my_chat_member") or {}
        chat = conteudo.get("chat")
        if chat:
            nome = chat.get("first_name") or chat.get("title") or chat.get("username") or ""
            return {"chat_id": str(chat["id"]), "nome": nome}
    raise ErroCanal("Nenhuma mensagem encontrada. Abra o seu bot no Telegram, envie /start e tente de novo.")


TIPOS_CHAT = {"private": "privado", "group": "grupo", "supergroup": "grupo", "channel": "canal"}


def procurar_chats_telegram(token: str) -> dict:
    """Pessoas e grupos que falaram com o bot (enviaram /start ou adicionaram o bot a um grupo).

    O Telegram guarda essas mensagens por 24 horas. Devolve os dados do bot (para compartilhar o link) e os chats,
    do mais recente para o mais antigo, ignorando grupos de onde o bot foi removido e pessoas que o bloquearam.
    """
    bot = _telegram(token, "getMe")
    atualizacoes = _telegram(token, "getUpdates", {"limit": 100, "timeout": 0})
    chats: dict[str, dict | None] = {}
    for atualizacao in reversed(atualizacoes):
        for chave in ("message", "edited_message", "channel_post", "my_chat_member", "chat_member"):
            conteudo = atualizacao.get(chave)
            if not isinstance(conteudo, dict) or not isinstance(conteudo.get("chat"), dict):
                continue
            chat = conteudo["chat"]
            chat_id = str(chat.get("id", ""))
            if not chat_id or chat_id in chats:
                continue
            if chave == "my_chat_member" and (conteudo.get("new_chat_member") or {}).get("status") in ("left", "kicked"):
                chats[chat_id] = None  # o bot saiu do grupo ou foi bloqueado: não sugerir
                continue
            nome = (chat.get("title") or " ".join(p for p in (chat.get("first_name"), chat.get("last_name")) if p)
                    or chat.get("username") or chat_id)
            chats[chat_id] = {"chat_id": chat_id, "nome": nome, "tipo": TIPOS_CHAT.get(chat.get("type"), "privado"),
                              "usuario": chat.get("username") or ""}
    return {
        "bot": {"usuario": bot.get("username") or "", "nome": bot.get("first_name") or ""},
        "chats": [c for c in chats.values() if c],
    }


def baixar_arquivo_telegram(token: str, file_id: str) -> bytes:
    """Baixa um arquivo enviado ao bot (fotos e documentos de até 20 MB)."""
    caminho = _telegram(token, "getFile", {"file_id": file_id}).get("file_path")
    if not caminho:
        raise ErroCanal("Telegram: arquivo indisponível.")
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{token.strip()}/{caminho}", timeout=60) as resposta:
            return resposta.read(20 * 1024 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ErroCanal("Sem conexão com o Telegram para baixar o arquivo.") from exc


# --------------------------------------------------------------------------- e-mail


def enviar_email(cfg: dict, assunto: str, texto: str, html: str) -> None:
    _recusar_na_demonstracao("e-mail")
    servidor = (cfg.get("servidor") or "").strip()
    destinatarios = [d.strip() for d in re.split(r"[;,]", cfg.get("destinatarios") or "") if d.strip()]
    if not servidor or not destinatarios:
        raise ErroCanal("Informe o servidor SMTP e pelo menos um destinatário.")
    remetente = (cfg.get("remetente") or cfg.get("usuario") or "").strip()
    if not remetente:
        raise ErroCanal("Informe o e-mail remetente.")

    mensagem = EmailMessage()
    mensagem["Subject"] = f"[Boletos] {assunto}"
    mensagem["From"] = remetente
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype="html")

    porta = int(cfg.get("porta") or 587)
    seguranca = cfg.get("seguranca") or "starttls"
    contexto = ssl.create_default_context()
    try:
        cliente = (smtplib.SMTP_SSL(servidor, porta, timeout=30, context=contexto) if seguranca == "ssl"
                   else smtplib.SMTP(servidor, porta, timeout=30))
        with cliente:
            if seguranca == "starttls":
                cliente.starttls(context=contexto)
            if cfg.get("usuario"):
                cliente.login(cfg["usuario"], cfg.get("senha") or "")
            cliente.send_message(mensagem)
    except smtplib.SMTPAuthenticationError as exc:
        raise ErroCanal("Usuário ou senha do e-mail recusados. No Gmail e no Outlook use uma senha de app.") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise ErroCanal(f"Falha ao enviar o e-mail: {exc}") from exc

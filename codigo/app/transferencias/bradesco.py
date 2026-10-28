"""API Pix do Bradesco: consulta os Pix recebidos na conta, para a conciliação com as notas da Operações.

Mesmo caminho do projeto de referência em PHP: conexão com o certificado da empresa (mTLS), token OAuth2 em
``client_credentials`` (Basic com o Client ID e o Client Secret) e ``GET /v2/pix?inicio=&fim=`` (padrão do Banco Central),
página por página. Começa no sandbox (``BRADESCO_AMBIENTE=sandbox``, o padrão); em produção, ``producao``.

O certificado e a chave vêm do Ambiente do EasyPanel: ``BRADESCO_CERT`` e ``BRADESCO_KEY`` com o texto PEM colado (o
EasyPanel pode juntar as linhas; o texto é arrumado aqui) ou com o caminho de um arquivo.

Segurança: credenciais só nas variáveis de ambiente (nunca no código, na tela ou no log); o token fica só na memória;
o Client Secret é tirado de qualquer mensagem de erro do banco antes de mostrar; mensagem nenhuma repete o valor do
certificado ou da chave; o texto colado só vai para um arquivo temporário (só o dono lê) enquanto o ssl o carrega.
"""

from __future__ import annotations

import os
import re
import shutil
import ssl
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import certifi
import httpx

from .. import config

AMBIENTES = {  # host e caminho do token de cada ambiente (dá para trocar com BRADESCO_HOST e BRADESCO_TOKEN_PATH)
    "sandbox": ("openapisandbox.prebanco.com.br", "/auth/server/oauth/token"),
    "producao": ("qrpix.bradesco.com.br", "/v2/oauth/token"),
}
ROTULOS = {"sandbox": "Sandbox (teste)", "producao": "Produção"}
MAX_PAGINAS = 50  # 100 Pix por página: até 5.000 Pix numa consulta
TIMEOUT = httpx.Timeout(60, connect=20)

_tokens: dict[tuple[str, str], tuple[str, float]] = {}  # (host, client id) -> (token, expira em)
_lock = threading.Lock()
_transporte: httpx.BaseTransport | None = None  # nos testes: o banco simulado (httpx.MockTransport)
_PEM = re.compile(r"-----BEGIN ([A-Z0-9 ]+)-----(.*?)-----END \1-----", re.S)
PEM_ESPERADO = {"cert": ("CERTIFICATE-----", "o certificado", "inteiro"), "key": ("PRIVATE KEY-----", "a chave", "inteira")}


class ErroBradesco(RuntimeError):
    """A consulta não deu certo: a mensagem já vem pronta para a tela, sem segredo."""


@dataclass(frozen=True)
class Configuracao:
    ambiente: str
    host: str
    token_path: str
    client_id: str
    client_secret: str = field(repr=False)
    cert: str = field(repr=False)  # texto PEM ou caminho do arquivo
    key: str = field(repr=False)


def pem(texto: str) -> str:
    """O certificado ou a chave colados no Ambiente, de volta ao formato PEM. O EasyPanel pode juntar as linhas (ou
    trocá-las por \\n): o que está entre o BEGIN e o END é refeito em linhas de 64 caracteres. Sem bloco, devolve ""."""
    blocos = []
    for tipo, corpo in _PEM.findall(texto.replace("\\n", "\n")):
        corpo = re.sub(r"\s", "", corpo)
        linhas = "".join(corpo[i:i + 64] + "\n" for i in range(0, len(corpo), 64))
        blocos.append(f"-----BEGIN {tipo}-----\n{linhas}-----END {tipo}-----\n")
    return "".join(blocos)


def configuracao() -> tuple[Configuracao | None, str]:
    """``(configuração, "")`` com tudo pronto, ou ``(None, motivo)`` dizendo o que falta para ligar a consulta."""
    valores = config.bradesco_pix()
    ambiente = valores["ambiente"].lower() or "sandbox"
    if ambiente not in AMBIENTES:
        return None, "Consulta ao Bradesco desligada: BRADESCO_AMBIENTE deve ser sandbox ou producao."
    faltando = [f"BRADESCO_{nome.upper()}" for nome in ("client_id", "client_secret", "cert", "key") if not valores[nome]]
    if faltando:
        return None, f"Consulta ao Bradesco desligada: falta {', '.join(faltando)} no Ambiente do EasyPanel."
    for nome, (esperado, o_que, inteiro) in PEM_ESPERADO.items():
        # o valor nunca entra na mensagem: pode ser a chave colada pela metade
        if "-----BEGIN" in valores[nome]:
            valores[nome] = pem(valores[nome])
            if esperado not in valores[nome]:
                return None, (f"Consulta ao Bradesco desligada: BRADESCO_{nome.upper()} não tem {o_que} {inteiro}. Cole o "
                              "texto do arquivo todo, de -----BEGIN até -----END, entre aspas simples.")
        elif not Path(valores[nome]).is_file():
            return None, (f"Consulta ao Bradesco desligada: BRADESCO_{nome.upper()} deve ter {o_que} (o texto do arquivo, "
                          "de -----BEGIN até -----END, entre aspas simples) ou o caminho de um arquivo que exista.")
    host, token_path = AMBIENTES[ambiente]
    host = re.sub(r"^https?://", "", valores["host"]).rstrip("/") or host
    return Configuracao(ambiente, host, valores["token_path"] or token_path, valores["client_id"],
                        valores["client_secret"], valores["cert"], valores["key"]), ""


def _arquivo(pasta: str, nome: str, valor: str) -> str:
    """O caminho para o ssl ler: o próprio valor, ou o texto PEM gravado na pasta temporária (só o dono lê)."""
    if "-----BEGIN" not in valor:
        return valor
    caminho = os.path.join(pasta, nome)
    with os.fdopen(os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as arquivo:
        arquivo.write(valor)
    return caminho


def _cliente(cfg: Configuracao) -> httpx.Client:
    if _transporte is not None:
        return httpx.Client(base_url=f"https://{cfg.host}", transport=_transporte, timeout=TIMEOUT)
    contexto = ssl.create_default_context(cafile=certifi.where())
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    pasta = None
    try:
        pasta = tempfile.mkdtemp(prefix="finpro-bradesco-")  # o ssl só lê de arquivo; a pasta some logo depois
        # chave com senha: dá erro em vez de o OpenSSL parar esperando alguém digitar a senha no terminal
        contexto.load_cert_chain(_arquivo(pasta, "cert.pem", cfg.cert), _arquivo(pasta, "key.pem", cfg.key),
                                 password=lambda: b"")
    except (ssl.SSLError, OSError):
        raise ErroBradesco("O certificado ou a chave do Bradesco não puderam ser lidos. Confira BRADESCO_CERT e "
                           "BRADESCO_KEY: o texto inteiro de cada arquivo, de -----BEGIN até -----END, e a chave sem "
                           "senha.") from None
    finally:
        if pasta:
            shutil.rmtree(pasta, ignore_errors=True)
    return httpx.Client(base_url=f"https://{cfg.host}", verify=contexto, timeout=TIMEOUT)


def _detalhe(resposta: httpx.Response, cfg: Configuracao) -> str:
    """O que o banco disse do erro, curto e sem o Client Secret."""
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = resposta.text
    if isinstance(corpo, dict):
        corpo = next((corpo[c] for c in ("error_description", "mensagem", "message", "detail", "title", "error")
                      if corpo.get(c)), "")
    texto = re.sub(r"\s+", " ", str(corpo or "")).strip()[:200]
    return texto.replace(cfg.client_secret, "[oculto]")


def _rotulo(cfg: Configuracao) -> str:
    return "produção" if cfg.ambiente == "producao" else "sandbox"


def _pedir(http: httpx.Client, cfg: Configuracao, metodo: str, caminho: str, **kwargs) -> httpx.Response:
    try:
        return http.request(metodo, caminho, **kwargs)
    except httpx.HTTPError as exc:
        raise ErroBradesco(f"Não foi possível falar com o Bradesco ({_rotulo(cfg)}, {cfg.host}): "
                           f"{type(exc).__name__}.") from None


def _token(http: httpx.Client, cfg: Configuracao) -> str:
    chave = (cfg.host, cfg.client_id)
    with _lock:
        guardado = _tokens.get(chave)
    if guardado and guardado[1] > time.monotonic() + 30:
        return guardado[0]
    resposta = _pedir(http, cfg, "POST", cfg.token_path, data={"grant_type": "client_credentials"},
                      auth=(cfg.client_id, cfg.client_secret), headers={"Accept": "application/json"})
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {}
    token = corpo.get("access_token") if isinstance(corpo, dict) else None
    if resposta.status_code != 200 or not isinstance(token, str) or not token:
        corpo = corpo if isinstance(corpo, dict) else {}
        if str(corpo.get("code") or "") == "99":
            mensagem = "O Bradesco recebeu o certificado, mas não aceitou o pedido de token desta credencial."
        elif corpo.get("error") == "invalid_client":
            mensagem = (f"O Bradesco recusou o Client ID e o Client Secret ({_rotulo(cfg)}). Confira se são o par da "
                        "credencial deste certificado.")
        else:
            mensagem = f"O Bradesco não entregou o token de acesso ({_rotulo(cfg)}, HTTP {resposta.status_code})."
        detalhe = _detalhe(resposta, cfg)
        raise ErroBradesco(f"{mensagem} {detalhe}".strip() if detalhe and detalhe not in mensagem else mensagem)
    try:
        validade = max(60, int(corpo.get("expires_in") or 3600))
    except (TypeError, ValueError):
        validade = 3600
    with _lock:
        _tokens[chave] = (token, time.monotonic() + validade)
    return token


def _rfc3339(momento: datetime) -> str:
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _horario_local(texto) -> datetime | None:
    """Horário do Pix (RFC 3339, em geral UTC) no fuso do sistema, sem fuso (como o resto do Fin Pro)."""
    texto = re.sub(r"\.\d+", "", str(texto or "").strip()).replace("Z", "+00:00")
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone().replace(tzinfo=None)


def _valor(texto) -> float | None:
    try:
        return round(float(texto), 2)
    except (TypeError, ValueError):
        return None


def normalizar(item: dict) -> dict | None:
    """Um Pix da resposta do banco no formato do Fin Pro. Sem endToEndId ou sem valor, é ignorado."""
    if not isinstance(item, dict):
        return None
    e2e = str(item.get("endToEndId") or "").strip()
    valor = _valor(item.get("valor"))
    if not e2e or valor is None:
        return None
    pagador = item.get("pagador") if isinstance(item.get("pagador"), dict) else {}
    devolvido = sum(_valor(d.get("valor")) or 0 for d in item.get("devolucoes") or []
                    if isinstance(d, dict) and d.get("status") != "NAO_REALIZADO")
    horario = _horario_local(item.get("horario"))
    return {"e2e": e2e, "txid": str(item.get("txid") or ""), "valor": valor, "devolvido": round(devolvido, 2),
            "horario": horario.isoformat() if horario else "",
            "pagador": re.sub(r"\s+", " ", str(pagador.get("nome") or "")).strip()[:120],
            # CNPJ pode ter letras desde jul/2026
            "documento": re.sub(r"[^0-9A-Z]", "", str(pagador.get("cnpj") or pagador.get("cpf") or "").upper()),
            "info": re.sub(r"\s+", " ", str(item.get("infoPagador") or "")).strip()[:140]}


def listar_pix(inicio: datetime, fim: datetime) -> list[dict]:
    """Pix recebidos entre ``inicio`` e ``fim`` (com fuso), já normalizados. Erro vira ``ErroBradesco``."""
    cfg, motivo = configuracao()
    if cfg is None:
        raise ErroBradesco(motivo)
    with _cliente(cfg) as http:
        recebidos: list = []
        parametros = {"inicio": _rfc3339(inicio), "fim": _rfc3339(fim)}
        pagina = 0
        while True:
            resposta = None
            for tentativa in range(2):  # token recusado (vencido antes da hora): pede outro uma vez
                cabecalhos = {"Authorization": f"Bearer {_token(http, cfg)}", "Accept": "application/json"}
                resposta = _pedir(http, cfg, "GET", "/v2/pix", params=parametros, headers=cabecalhos)
                if resposta.status_code != 401 or tentativa:
                    break
                with _lock:
                    _tokens.pop((cfg.host, cfg.client_id), None)
            if resposta.status_code != 200:
                detalhe = _detalhe(resposta, cfg)
                raise ErroBradesco(f"O Bradesco recusou a consulta dos Pix recebidos (HTTP {resposta.status_code})."
                                   + (f" {detalhe}" if detalhe else ""))
            try:
                corpo = resposta.json()
            except ValueError:
                raise ErroBradesco("O Bradesco respondeu a consulta dos Pix num formato inesperado.") from None
            if not isinstance(corpo, dict):
                raise ErroBradesco("O Bradesco respondeu a consulta dos Pix num formato inesperado.")
            recebidos.extend(corpo.get("pix") or [])
            paginacao = (corpo.get("parametros") or {}).get("paginacao") or {}
            try:
                paginas = int(paginacao.get("quantidadeDePaginas") or 1)
            except (TypeError, ValueError):
                paginas = 1
            pagina += 1
            if pagina >= min(paginas, MAX_PAGINAS):
                break
            parametros = {**parametros, "paginacao.paginaAtual": pagina,
                          "paginacao.itensPorPagina": paginacao.get("itensPorPagina") or 100}
    return [p for p in map(normalizar, recebidos) if p]

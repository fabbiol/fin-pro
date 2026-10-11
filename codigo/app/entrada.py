"""Caixa de entrada: boletos que chegam sozinhos por e-mail e pelo bot do Telegram.

* **E-mail** — o sistema confere, a cada 5 minutos, uma caixa de e-mail (IMAP) e lê os PDFs e fotos anexados.
  As mensagens não são apagadas nem marcadas como lidas. Na primeira vez, olha os e-mails dos últimos 7 dias.
  Dá para aceitar só alguns remetentes (ex.: ``fornecedor.com.br, contas@empresa.com``).
* **Telegram** — as pessoas cadastradas em Notificações → Telegram podem encaminhar a foto ou o PDF do boleto
  para o bot. O bot responde com o que conseguiu ler. Arquivos de pessoas não cadastradas são recusados.

Boletos não são lançados sem conferência: cada boleto lido fica na caixa de entrada (tela Ler boletos) até alguém
revisar e lançar, ou descartar. O mesmo arquivo recebido duas vezes é ignorado, e boletos que já estavam lançados
saem sozinhos da caixa.

**Comprovantes de pagamento** são tratados na hora: o sistema descobre de qual boleto ou Pix é, marca como pago
com o valor pago, juros/multa e desconto, e anexa o comprovante. Quando não dá para ter certeza (ex.: parcelas
iguais), o comprovante fica na caixa de entrada para alguém escolher o lançamento.
"""

from __future__ import annotations

import copy
import email
import hashlib
import imaplib
import json
import logging
import os
import re
import ssl
import threading
import uuid
from datetime import date, datetime, timedelta
from email.header import decode_header, make_header
from email.policy import default as politica_padrao
from email.utils import parseaddr
from pathlib import Path
from typing import Callable

from fastapi.encoders import jsonable_encoder

from .notificacoes import canais

log = logging.getLogger(__name__)

MASCARA = "••••••••"
INTERVALO_EMAIL = 300
INTERVALO_TELEGRAM = 45
DIAS_PRIMEIRA_LEITURA = 7
MAX_EMAILS_POR_VEZ = 40
MAX_ITENS = 300
DIAS_MANTER_CONCLUIDOS = 30
TAMANHO_MINIMO_IMAGEM = 15_000  # logotipos e assinaturas de e-mail costumam ser menores
TAMANHO_MAXIMO = 20 * 1024 * 1024
EXTENSOES = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff")

PADRAO = {
    "itens": [],
    "email": {"ativo": False, "servidor": "", "porta": 993, "usuario": "", "senha": "", "pasta": "INBOX", "remetentes": "",
              "uidvalidity": None, "ultimo_uid": None, "ultima_verificacao": None, "ultimo_erro": None},
    "telegram": {"ativo": False, "offset": None, "ultima_verificacao": None, "ultimo_erro": None, "chats": {}},
}


def _moeda(valor) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(valor) -> str:
    return datetime.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y") if valor else ""


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _texto_cabecalho(valor) -> str:
    try:
        return str(make_header(decode_header(str(valor or "")))).strip()
    except Exception:
        return str(valor or "").strip()


def remetente_permitido(endereco: str, filtro: str) -> bool:
    regras = [r.strip().lower().lstrip("@") for r in re.split(r"[;,\s]+", filtro or "") if r.strip()]
    if not regras:
        return True
    endereco = (endereco or "").lower()
    return any(endereco == r or endereco.endswith("@" + r) or endereco.endswith("." + r) for r in regras)


def anexos_do_email(bruto: bytes) -> tuple[dict, list[tuple[str, bytes]]]:
    """Cabeçalho resumido e anexos úteis (PDF e imagens) de uma mensagem."""
    mensagem = email.message_from_bytes(bruto, policy=politica_padrao)
    nome, endereco = parseaddr(str(mensagem.get("From", "")))
    info = {"remetente": _texto_cabecalho(nome) or endereco, "endereco": endereco.lower(),
            "assunto": _texto_cabecalho(mensagem.get("Subject"))[:200]}
    anexos = []
    for parte in mensagem.walk():
        if parte.is_multipart():
            continue
        tipo = parte.get_content_type()
        arquivo = _texto_cabecalho(parte.get_filename() or "")
        eh_pdf = tipo == "application/pdf" or arquivo.lower().endswith(".pdf")
        eh_imagem = tipo.startswith("image/") or arquivo.lower().endswith(EXTENSOES[1:])
        if not (eh_pdf or eh_imagem):
            continue
        try:
            dados = parte.get_payload(decode=True) or b""
        except Exception:
            continue
        if not dados or len(dados) > TAMANHO_MAXIMO or (eh_imagem and not eh_pdf and len(dados) < TAMANHO_MINIMO_IMAGEM):
            continue
        anexos.append((arquivo or ("boleto.pdf" if eh_pdf else "imagem.jpg"), dados))
    return info, anexos


def resumo_da_leitura(resultado: dict | None) -> dict:
    """O que foi lido (para mostrar na lista e responder no Telegram)."""
    if not resultado:
        return {"boletos": 0, "pix": 0}
    analise = resultado.get("comprovante")
    if analise:
        extraido = analise.get("extraido") or {}
        sugerido = analise.get("sugerido") or {}
        return {"boletos": 0, "pix": 0, "comprovante": True, "valor_pago": extraido.get("valor_pago"),
                "data_pagamento": extraido.get("data_pagamento"), "agendado": bool(extraido.get("agendado")),
                "beneficiario": sugerido.get("nome") or extraido.get("beneficiario"),
                "candidatos": len(analise.get("candidatos") or [])}
    boletos = resultado.get("boletos") or []
    pix = resultado.get("pix") or []
    primeiro = {}
    if boletos:
        campos = boletos[0].get("campos") or {}
        primeiro = {chave: (campos.get(chave) or {}).get("valor") for chave in ("beneficiario", "valor", "vencimento")}
        primeiro["duplicado"] = bool(boletos[0].get("duplicado"))
    elif pix:
        primeiro = {"beneficiario": pix[0].get("recebedor"), "valor": pix[0].get("valor"), "vencimento": None,
                    "duplicado": bool(pix[0].get("duplicado"))}
    return {"boletos": len(boletos), "pix": len(pix), **primeiro}


class CaixaEntrada:
    def __init__(self, caminho: Path, processar: Callable[[bytes, str], dict], salvar_arquivo: Callable[[bytes, str], dict],
                 telegram: Callable[[], tuple[str, list[dict]]], registrar_pagamento: Callable[..., dict] | None = None,
                 comandos=None):
        """``processar`` lê um arquivo (como a tela Ler boletos); ``salvar_arquivo`` guarda arquivos que não puderam
        ser lidos; ``telegram`` devolve (token do bot, pessoas cadastradas); ``registrar_pagamento(aba, id, extraido,
        usuario, arquivo_id)`` marca um lançamento como pago a partir de um comprovante e devolve o resumo."""
        self.registrar_pagamento = registrar_pagamento
        # ``comandos``: módulo com ``responder(texto, nome)`` e ``COMANDOS`` (app.bot) — consultas pelo Telegram
        self.comandos = comandos
        self._comandos_registrados: str | None = None
        self.caminho = Path(caminho)
        self.processar = processar
        self.salvar_arquivo = salvar_arquivo
        self.dados_telegram = telegram
        self._lock = threading.RLock()
        self._verificando = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._estado = self._ler()

    # ------------------------------------------------------------------ persistência

    def _ler(self) -> dict:
        estado = copy.deepcopy(PADRAO)
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return estado
        if isinstance(salvo.get("itens"), list):
            estado["itens"] = [i for i in salvo["itens"] if isinstance(i, dict) and i.get("id")]
        for canal in ("email", "telegram"):
            if isinstance(salvo.get(canal), dict):
                estado[canal].update({k: v for k, v in salvo[canal].items() if k in estado[canal]})
        return estado

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ configuração

    def config_publica(self) -> dict:
        with self._lock:
            email_cfg = {k: v for k, v in self._estado["email"].items() if k not in ("uidvalidity", "ultimo_uid")}
            telegram = {k: v for k, v in self._estado["telegram"].items() if k not in ("offset", "chats")}
        email_cfg["senha"] = MASCARA if email_cfg["senha"] else ""
        return {"email": email_cfg, "telegram": telegram}

    def configurar(self, novo: dict) -> dict:
        with self._lock:
            estado = copy.deepcopy(self._estado)
            dados = novo.get("email")
            if isinstance(dados, dict):
                cfg = estado["email"]
                servidor_antes = (cfg["servidor"], cfg["usuario"], cfg["pasta"])
                for campo in ("ativo", "servidor", "porta", "usuario", "senha", "pasta", "remetentes"):
                    if campo not in dados or dados[campo] is None:
                        continue
                    valor = dados[campo]
                    if campo == "senha" and valor == MASCARA:
                        continue
                    if campo == "porta":
                        valor = int(valor or 993)
                        if not 1 <= valor <= 65535:
                            raise ValueError("Porta inválida.")
                    elif campo == "ativo":
                        valor = bool(valor)
                    else:
                        valor = str(valor).strip()[:300]
                    cfg[campo] = valor
                cfg["pasta"] = cfg["pasta"] or "INBOX"
                if cfg["ativo"] and not (cfg["servidor"] and cfg["usuario"] and cfg["senha"]):
                    raise ValueError("Para receber boletos por e-mail, informe o servidor IMAP, o e-mail e a senha.")
                if (cfg["servidor"], cfg["usuario"], cfg["pasta"]) != servidor_antes:
                    cfg.update(uidvalidity=None, ultimo_uid=None)  # outra caixa: recomeça pelos últimos 7 dias
                cfg["ultimo_erro"] = None
            dados = novo.get("telegram")
            if isinstance(dados, dict) and dados.get("ativo") is not None:
                estado["telegram"]["ativo"] = bool(dados["ativo"])
                estado["telegram"]["ultimo_erro"] = None
            self._estado = estado
            self._gravar()
        return self.config_publica()

    # ------------------------------------------------------------------ itens

    @staticmethod
    def _publico(item: dict) -> dict:
        publico = {chave: item.get(chave) for chave in ("id", "origem", "remetente", "assunto", "recebido_em", "nome_arquivo",
                                                        "arquivo_id", "estado", "erro", "resumo", "concluido_em", "tipo",
                                                        "pagamento")}
        analise = (item.get("resultado") or {}).get("comprovante")
        if analise and item.get("estado") == "pendente":
            publico["candidatos"] = analise.get("candidatos") or []
            publico["extraido"] = analise.get("extraido") or {}
        return publico

    def listar(self, incluir_concluidos: bool = False) -> list[dict]:
        with self._lock:
            itens = [i for i in self._estado["itens"] if incluir_concluidos or i["estado"] in ("pendente", "erro")]
            return [self._publico(i) for i in sorted(itens, key=lambda i: i["recebido_em"], reverse=True)]

    def obter(self, id_: str) -> dict | None:
        with self._lock:
            item = next((i for i in self._estado["itens"] if i["id"] == id_), None)
            return copy.deepcopy(item) if item else None

    def contagem(self) -> int:
        with self._lock:
            return sum(1 for i in self._estado["itens"] if i["estado"] in ("pendente", "erro"))

    def arquivos_em_uso(self) -> set[str]:
        with self._lock:
            return {i["arquivo_id"] for i in self._estado["itens"] if i.get("arquivo_id") and i["estado"] in ("pendente", "erro")}

    def _concluir(self, filtro, estado_novo: str) -> int:
        with self._lock:
            alterados = 0
            for item in self._estado["itens"]:
                if item["estado"] in ("pendente", "erro") and filtro(item):
                    item.update(estado=estado_novo, concluido_em=_agora())
                    alterados += 1
            if alterados:
                self._gravar()
            return alterados

    def descartar(self, id_: str) -> bool:
        return bool(self._concluir(lambda i: i["id"] == id_, "descartado"))

    def marcar_lancados(self, arquivo_ids: set[str]) -> int:
        return self._concluir(lambda i: i.get("arquivo_id") in arquivo_ids, "lancado") if arquivo_ids else 0

    def _limpar_antigos(self) -> None:
        limite = (datetime.now() - timedelta(days=DIAS_MANTER_CONCLUIDOS)).isoformat()
        itens = [i for i in self._estado["itens"] if i["estado"] in ("pendente", "erro") or (i.get("concluido_em") or "") > limite]
        self._estado["itens"] = sorted(itens, key=lambda i: i["recebido_em"], reverse=True)[:MAX_ITENS]

    def receber(self, dados: bytes, nome: str, origem: str, remetente: str = "", assunto: str = "",
                usuario: str = "") -> dict | None:
        """Lê um arquivo recebido e o coloca na caixa de entrada. Devolve o item, ou None se já tinha chegado antes."""
        impressao = hashlib.sha256(dados).hexdigest()
        with self._lock:
            if any(i.get("hash") == impressao for i in self._estado["itens"]):
                return None
        item = {"id": uuid.uuid4().hex[:12], "origem": origem, "remetente": (remetente or "")[:120], "assunto": (assunto or "")[:200],
                "recebido_em": _agora(), "nome_arquivo": Path(nome or "arquivo").name[:120], "hash": impressao,
                "estado": "pendente", "erro": None, "resultado": None, "arquivo_id": None, "concluido_em": None}
        try:
            resultado = jsonable_encoder(self.processar(dados, item["nome_arquivo"]))
            item.update(resultado=resultado, arquivo_id=(resultado.get("arquivo") or {}).get("id"))
            if resultado.get("comprovante"):
                item["tipo"] = "comprovante"
                self._registrar_comprovante(item, usuario or remetente)
            elif not resultado.get("boletos") and not resultado.get("pix"):
                item.update(estado="erro", erro="Nenhum boleto ou Pix encontrado no arquivo.")
            elif self._ja_lancado(resultado):
                item.update(estado="ja_lancado", concluido_em=_agora())
        except Exception as exc:
            log.warning("Não foi possível ler %s recebido por %s: %s", nome, origem, exc)
            try:
                item["arquivo_id"] = self.salvar_arquivo(dados, item["nome_arquivo"])["id"]
            except Exception:
                log.exception("Falha ao guardar arquivo recebido")
            item.update(estado="erro", erro=str(exc)[:300] or "Não foi possível ler o arquivo.")
        item["resumo"] = resumo_da_leitura(item["resultado"])
        with self._lock:
            self._estado["itens"].append(item)
            self._limpar_antigos()
            self._gravar()
        log.info("Recebido por %s: %s (%s)", origem, item["nome_arquivo"], item["estado"])
        return item

    @staticmethod
    def _ja_lancado(resultado: dict | None) -> bool:
        """Todos os boletos/Pix do arquivo já estão na planilha: não há nada para conferir."""
        documentos = [*((resultado or {}).get("boletos") or []), *((resultado or {}).get("pix") or [])]
        return bool(documentos) and all(d.get("duplicado") for d in documentos)

    def _registrar_comprovante(self, item: dict, usuario: str) -> None:
        analise = item["resultado"]["comprovante"]
        sugerido = analise.get("sugerido")
        if not sugerido or not self.registrar_pagamento:
            return
        try:
            pagamento = self.registrar_pagamento(sugerido["aba"], sugerido["id"], analise["extraido"], usuario, item["arquivo_id"])
        except Exception as exc:
            log.warning("Não foi possível registrar o pagamento do comprovante %s: %s", item["nome_arquivo"], exc)
            return
        item.update(estado="pago", pagamento=pagamento, concluido_em=_agora())

    def associar(self, id_: str, aba: str, registro_id: int, usuario: str) -> dict:
        """Comprovante que ficou em dúvida: alguém escolheu de qual lançamento ele é."""
        with self._lock:
            item = next((i for i in self._estado["itens"] if i["id"] == id_), None)
        if not item or item.get("tipo") != "comprovante" or item["estado"] != "pendente":
            raise ValueError("Este comprovante não está mais aguardando na caixa de entrada.")
        extraido = item["resultado"]["comprovante"].get("extraido") or {}
        pagamento = self.registrar_pagamento(aba, registro_id, extraido, usuario, item["arquivo_id"])
        with self._lock:
            item.update(estado="pago", pagamento=pagamento, concluido_em=_agora())
            self._gravar()
        return self._publico(item)

    def concluir_ja_lancados(self) -> int:
        """Arquivos que chegaram antes desta regra e cujos boletos já estavam todos lançados."""
        return self._concluir(lambda i: i["estado"] == "pendente" and i.get("tipo") != "comprovante" and self._ja_lancado(i.get("resultado")),
                              "ja_lancado")

    # ------------------------------------------------------------------ e-mail

    def verificar_email(self, conectar=None) -> dict:
        """Confere a caixa de e-mail. ``conectar`` permite substituir o IMAP nos testes."""
        with self._lock:
            cfg = dict(self._estado["email"])
        if not (cfg["servidor"] and cfg["usuario"] and cfg["senha"]):
            raise ValueError("Informe o servidor IMAP, o e-mail e a senha.")
        recebidos = 0
        try:
            conexao = (conectar or self._conectar_imap)(cfg)
            try:
                conexao.login(cfg["usuario"], cfg["senha"])
                tipo, _ = conexao.select(cfg["pasta"] or "INBOX", readonly=True)
                if tipo != "OK":
                    raise ValueError(f'Pasta "{cfg["pasta"]}" não encontrada na caixa de e-mail.')
                validade = (conexao.response("UIDVALIDITY")[1] or [None])[0]
                validade = validade.decode() if isinstance(validade, bytes) else validade
                ultimo = cfg["ultimo_uid"] if cfg["uidvalidity"] == validade else None
                if ultimo is None:
                    desde = (date.today() - timedelta(days=DIAS_PRIMEIRA_LEITURA)).strftime("%d-%b-%Y")
                    _, resposta = conexao.uid("SEARCH", None, f"SINCE {desde}")
                else:
                    _, resposta = conexao.uid("SEARCH", None, f"UID {int(ultimo) + 1}:*")
                uids = sorted({int(u) for u in (resposta[0] or b"").split() if u.isdigit()})
                uids = [u for u in uids if ultimo is None or u > int(ultimo)][:MAX_EMAILS_POR_VEZ]
                maior = int(ultimo) if ultimo is not None else 0
                if ultimo is None and not uids:  # nenhum e-mail recente: guarda o último UID para começar dele
                    _, topo = conexao.uid("SEARCH", None, "UID *")
                    maior = max([int(u) for u in (topo[0] or b"").split() if u.isdigit()] or [0])
                for uid in uids:
                    _, partes = conexao.uid("FETCH", str(uid), "(BODY.PEEK[])")
                    bruto = next((p[1] for p in partes if isinstance(p, tuple) and len(p) > 1), None)
                    maior = max(maior, uid)
                    if not bruto:
                        continue
                    info, anexos = anexos_do_email(bruto)
                    if not remetente_permitido(info["endereco"], cfg["remetentes"]):
                        continue
                    for nome, dados in anexos:
                        remetente = info["remetente"] or info["endereco"]
                        if self.receber(dados, nome, "email", remetente, info["assunto"], f"{remetente} (e-mail)"):
                            recebidos += 1
            finally:
                try:
                    conexao.logout()
                except Exception:
                    pass
        except imaplib.IMAP4.error as exc:
            texto = str(exc)
            if "AUTH" in texto.upper() or "LOGIN" in texto.upper() or "credentials" in texto.lower():
                texto = ("E-mail ou senha recusados. No Gmail e no Outlook, ative o IMAP e use uma senha de app "
                         "(não a senha normal).")
            self._registrar_email(erro=texto)
            raise ValueError(texto) from exc
        except (OSError, ssl.SSLError) as exc:
            texto = f"Não foi possível conectar ao servidor de e-mail ({exc})."
            self._registrar_email(erro=texto)
            raise ValueError(texto) from exc
        except ValueError as exc:
            self._registrar_email(erro=str(exc))
            raise
        self._registrar_email(uidvalidity=validade, ultimo_uid=maior)
        return {"recebidos": recebidos, "emails_verificados": len(uids)}

    @staticmethod
    def _conectar_imap(cfg: dict):
        return imaplib.IMAP4_SSL(cfg["servidor"], int(cfg["porta"] or 993), ssl_context=ssl.create_default_context(), timeout=60)

    def _registrar_email(self, erro: str | None = None, **campos) -> None:
        with self._lock:
            self._estado["email"].update(ultima_verificacao=_agora(), ultimo_erro=erro, **campos)
            self._gravar()

    # ------------------------------------------------------------------ Telegram

    def chats_recentes(self) -> list[dict]:
        with self._lock:
            chats = list(self._estado["telegram"]["chats"].values())
        return sorted(chats, key=lambda c: c.get("quando") or "", reverse=True)

    def _lembrar_chat(self, chat: dict) -> None:
        chat_id = str(chat.get("id", ""))
        if not chat_id:
            return
        nome = (chat.get("title") or " ".join(p for p in (chat.get("first_name"), chat.get("last_name")) if p)
                or chat.get("username") or chat_id)
        chats = self._estado["telegram"]["chats"]
        chats[chat_id] = {"chat_id": chat_id, "nome": nome, "tipo": canais.TIPOS_CHAT.get(chat.get("type"), "privado"),
                          "usuario": chat.get("username") or "", "quando": _agora()}
        if len(chats) > 100:
            for antigo in sorted(chats.values(), key=lambda c: c["quando"])[:len(chats) - 100]:
                chats.pop(antigo["chat_id"], None)

    def verificar_telegram(self) -> dict:
        token, destinatarios = self.dados_telegram()
        if not token:
            raise ValueError("Configure o bot do Telegram em Notificações.")
        with self._lock:
            offset = self._estado["telegram"]["offset"]
        cadastrados = {d["chat_id"]: d.get("nome") or "" for d in destinatarios}
        self._registrar_comandos(token)
        pedido = {"limit": 50, "timeout": 0}
        if offset:
            pedido["offset"] = offset
        try:
            atualizacoes = canais._telegram(token, "getUpdates", pedido)
        except canais.ErroCanal as exc:
            self._registrar_telegram(erro=str(exc))
            raise ValueError(str(exc)) from exc
        recebidos = 0
        for atualizacao in atualizacoes:
            with self._lock:
                self._estado["telegram"]["offset"] = int(atualizacao.get("update_id", 0)) + 1
            conteudo = atualizacao.get("message") or atualizacao.get("channel_post") or atualizacao.get("my_chat_member") or {}
            chat = conteudo.get("chat") or {}
            if not chat:
                continue
            if atualizacao.get("my_chat_member") and (conteudo.get("new_chat_member") or {}).get("status") in ("left", "kicked"):
                with self._lock:
                    self._estado["telegram"]["chats"].pop(str(chat.get("id")), None)
                continue
            with self._lock:
                self._lembrar_chat(chat)
            arquivo = self._arquivo_da_mensagem(conteudo)
            chat_id = str(chat.get("id"))
            if not arquivo:
                self._responder_comando(token, chat_id, conteudo, cadastrados)
                continue
            if chat_id not in cadastrados:
                self._responder(token, chat_id, "Este bot só recebe boletos de quem está cadastrado no Fin Pro. "
                                                "Peça ao responsável para incluir você em Notificações → Telegram.")
                continue
            file_id, nome, tamanho = arquivo
            if tamanho and tamanho > TAMANHO_MAXIMO:
                self._responder(token, chat_id, "Arquivo grande demais (máximo 20 MB).")
                continue
            try:
                dados = canais.baixar_arquivo_telegram(token, file_id)
            except canais.ErroCanal as exc:
                self._responder(token, chat_id, f"Não consegui baixar o arquivo: {exc}")
                continue
            remetente = " ".join(p for p in ((conteudo.get("from") or {}).get("first_name"), (conteudo.get("from") or {}).get("last_name")) if p)
            with self._lock:
                nome_chat = self._estado["telegram"]["chats"].get(chat_id, {}).get("nome")
            quem = cadastrados.get(chat_id) or remetente or nome_chat or chat_id
            item = self.receber(dados, nome, "telegram", remetente or nome_chat or chat_id, conteudo.get("caption") or "",
                                f"{quem} (Telegram)")
            self._responder(token, chat_id, self._mensagem_resposta(item))
            recebidos += 1 if item else 0
        self._registrar_telegram()
        return {"recebidos": recebidos}

    def _responder_comando(self, token: str, chat_id: str, mensagem: dict, cadastrados: dict) -> None:
        texto = (mensagem.get("text") or "").strip()
        if not texto.startswith("/") or not self.comandos:
            return
        if chat_id not in cadastrados:
            self._responder(token, chat_id, "Olá! Este é o bot do Fin Pro do escritório. Para consultar boletos e "
                                            "receber avisos, peça ao responsável para incluir você em Notificações → Telegram.")
            return
        nome = (mensagem.get("from") or {}).get("first_name") or cadastrados.get(chat_id) or ""
        try:
            respostas = self.comandos.responder(texto, nome) or []
        except Exception:
            log.exception("Falha ao responder o comando %s no Telegram", texto[:30])
            respostas = ["Não consegui consultar agora. Tente de novo em instantes."]
        for resposta in respostas:
            try:
                canais.enviar_telegram(token, chat_id, resposta)
            except canais.ErroCanal as exc:
                log.warning("Não foi possível responder no Telegram: %s", exc)
                break

    def _registrar_comandos(self, token: str) -> None:
        """Mostra os comandos no menu "/" do Telegram (uma vez por execução)."""
        if not self.comandos or self._comandos_registrados == token:
            return
        try:
            canais._telegram(token, "setMyCommands", {"commands": [{"command": c, "description": d} for c, d in self.comandos.COMANDOS]})
            self._comandos_registrados = token
        except canais.ErroCanal as exc:
            log.warning("Não foi possível registrar os comandos do bot: %s", exc)

    @staticmethod
    def _arquivo_da_mensagem(mensagem: dict) -> tuple[str, str, int] | None:
        documento = mensagem.get("document")
        if isinstance(documento, dict):
            nome = documento.get("file_name") or "arquivo"
            tipo = documento.get("mime_type") or ""
            if tipo == "application/pdf" or tipo.startswith("image/") or nome.lower().endswith(EXTENSOES):
                return documento["file_id"], nome, int(documento.get("file_size") or 0)
            return None
        fotos = mensagem.get("photo")
        if isinstance(fotos, list) and fotos:
            maior = max(fotos, key=lambda f: int(f.get("file_size") or 0) or int(f.get("width", 0)) * int(f.get("height", 0)))
            return maior["file_id"], f"foto-telegram-{datetime.now():%Y%m%d-%H%M%S}.jpg", int(maior.get("file_size") or 0)
        return None

    @staticmethod
    def _mensagem_resposta(item: dict | None) -> str:
        if item is None:
            return "Este arquivo já tinha sido recebido antes."
        if item.get("tipo") == "comprovante":
            return CaixaEntrada._mensagem_comprovante(item)
        if item["estado"] == "ja_lancado":
            return "Este boleto já estava lançado no Fin Pro. Não precisa fazer nada."
        if item["estado"] == "erro":
            return ("Recebi o arquivo, mas não encontrei um boleto nele. Ele ficou na caixa de entrada do Fin Pro "
                    "para alguém conferir. Dica: envie como arquivo (PDF) ou uma foto nítida do código de barras.")
        r = item["resumo"]
        partes = [r.get("beneficiario") or "beneficiário não identificado"]
        if r.get("valor"):
            partes.append("R$ " + f"{float(r['valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if r.get("vencimento"):
            partes.append("vence " + datetime.fromisoformat(str(r["vencimento"])[:10]).strftime("%d/%m/%Y"))
        aviso = " Atenção: parece que este boleto já foi lançado." if r.get("duplicado") else ""
        tipo = "Pix" if r.get("pix") and not r.get("boletos") else "Boleto"
        return f"{tipo} recebido: {' · '.join(partes)}.{aviso} Está na caixa de entrada do Fin Pro aguardando conferência."

    @staticmethod
    def _mensagem_comprovante(item: dict) -> str:
        p = item.get("pagamento")
        if item["estado"] == "pago" and p:
            linhas = [
                f"✅ Pagamento registrado: {p.get('nome') or 'lançamento'}",
                f"Vencimento: {_data_br(p.get('vencimento'))}" if p.get("vencimento") else "",
                f"Valor do {'Pix' if p.get('aba') == 'pix' else 'boleto'}: {_moeda(p.get('valor'))}",
                f"Valor pago: {_moeda(p.get('valor_pago'))} em {_data_br(p.get('data_pagamento'))}",
            ]
            if p.get("juros_multa"):
                atraso = f" ({p['dias_atraso']} dia(s) de atraso)" if p.get("dias_atraso") else ""
                linhas.append(f"Juros/multa: {_moeda(p['juros_multa'])}{atraso}")
            if p.get("desconto"):
                linhas.append(f"Desconto: {_moeda(p['desconto'])}")
            if not p.get("juros_multa") and not p.get("desconto"):
                linhas.append("Pago sem juros." if not p.get("dias_atraso") else f"Pago com {p['dias_atraso']} dia(s) de atraso, sem juros.")
            linhas.append("O comprovante foi anexado no Fin Pro.")
            return "\n".join(l for l in linhas if l)
        r = item.get("resumo") or {}
        if r.get("agendado"):
            return ("Este comprovante é de um AGENDAMENTO, não de um pagamento efetuado. Envie o comprovante "
                    "depois que o pagamento for realizado. Ele ficou no Fin Pro para conferência.")
        valor = f" de {_moeda(r['valor_pago'])}" if r.get("valor_pago") else ""
        data = f" pago em {_data_br(r['data_pagamento'])}" if r.get("data_pagamento") else ""
        duvida = ("há mais de um boleto parecido (por exemplo, parcelas do mesmo valor)" if (r.get("candidatos") or 0) > 1
                  else "não encontrei o boleto ou Pix correspondente")
        return (f"Recebi o comprovante{valor}{data}, mas {duvida}. Ele ficou no Fin Pro para alguém "
                "escolher o lançamento certo.")

    @staticmethod
    def _responder(token: str, chat_id: str, texto: str) -> None:
        try:
            canais._telegram(token, "sendMessage", {"chat_id": chat_id, "text": texto})
        except canais.ErroCanal as exc:
            log.warning("Não foi possível responder no Telegram: %s", exc)

    def _registrar_telegram(self, erro: str | None = None) -> None:
        with self._lock:
            self._estado["telegram"].update(ultima_verificacao=_agora(), ultimo_erro=erro)
            self._gravar()

    # ------------------------------------------------------------------ agendador

    def verificar_agora(self, canal: str) -> dict:
        if not self._verificando.acquire(timeout=120):
            raise ValueError("Uma verificação já está em andamento. Tente de novo em instantes.")
        try:
            return self.verificar_email() if canal == "email" else self.verificar_telegram()
        finally:
            self._verificando.release()

    def iniciar_agendador(self, espera_inicial: float = 30) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            if self._parar.wait(espera_inicial):
                return
            ultimo_email = 0.0
            while True:
                with self._lock:
                    email_ativo = self._estado["email"]["ativo"]
                    telegram_ativo = self._estado["telegram"]["ativo"]
                for canal, ativo in (("telegram", telegram_ativo), ("email", email_ativo)):
                    if not ativo or (canal == "email" and datetime.now().timestamp() - ultimo_email < INTERVALO_EMAIL):
                        continue
                    if canal == "email":
                        ultimo_email = datetime.now().timestamp()
                    try:
                        self.verificar_agora(canal)
                    except ValueError as exc:
                        log.warning("Caixa de entrada (%s): %s", canal, exc)
                    except Exception:
                        log.exception("Falha ao verificar a caixa de entrada (%s)", canal)
                if self._parar.wait(INTERVALO_TELEGRAM):
                    return

        self._thread = threading.Thread(target=laco, name="caixa-entrada", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

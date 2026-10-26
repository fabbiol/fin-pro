"""Bot do caixa (Telegram): recebe a foto do cupom ou da nota de uma compra paga em dinheiro.

É um terceiro bot, só para o caixa. Quem pode usar são as mesmas pessoas e grupos já cadastrados no bot dos
boletos e no bot de notas — a lista vem de lá, sem cadastrar de novo.

A cada foto, o bot conversa:

1. lê o **valor** (e a data e a loja) do cupom; se não conseguir, pergunta o valor;
2. pergunta **onde foi gasto** (ex.: "gasolina da caminhonete");
3. mostra os **centros de custo** da aba Gastos como botões — e um botão para **cadastrar um novo**;
4. deixa tudo preenchido no Fin Pro (Caixa → Conferência) para alguém revisar e lançar.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Callable

from ..notificacoes import canais

log = logging.getLogger("leitor_boletos.caixa")

MASCARA = "••••••••"
INTERVALO = 20
TAMANHO_MAXIMO = 20 * 1024 * 1024
EXTENSOES = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".xml")
MAX_ITENS = 300
DIAS_MANTER_CONCLUIDOS = 30
COMANDOS = [("ajuda", "Como mandar um gasto do caixa"), ("resumo", "Entradas e saídas de hoje e do mês"),
            ("cancelar", "Desistir do gasto que está sendo informado")]
PADRAO = {"config": {"ativo": False, "token": "", "offset": 0, "ultima_verificacao": None, "ultimo_erro": None},
          "itens": [], "conversas": {}}


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _moeda(valor) -> str:
    return "R$ " + f"{float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _valor_digitado(texto: str) -> float | None:
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:[,.](\d{1,2}))?", (texto or "").replace(" ", ""))
    if not m:
        return None
    inteiro = m.group(1).replace(".", "")
    centavos = (m.group(2) or "0").ljust(2, "0")
    valor = round(float(f"{inteiro}.{centavos}"), 2)
    return valor if valor > 0 else None


class BotCaixa:
    def __init__(self, caminho: Path, salvar_arquivo: Callable[[bytes, str], dict], pessoas: Callable[[], dict],
                 centros: Callable[[], list[str]], criar_centro: Callable[[str, str], str],
                 ler: Callable[[bytes, str], dict] | None = None):
        """``pessoas()`` → {chat_id: nome} (quem já está nos outros bots); ``centros()`` → nomes dos centros de custo;
        ``criar_centro(nome, usuario)`` cadastra um centro novo; ``ler(dados, nome)`` lê valor, data e loja do cupom."""
        self.caminho = Path(caminho)
        self.salvar_arquivo = salvar_arquivo
        self.pessoas = pessoas
        self.centros = centros
        self.criar_centro = criar_centro
        if ler is None:
            from .leitura import analisar as ler
        self.ler = ler
        self._lock = threading.RLock()
        self._lancando: set[str] = set()  # itens sendo lançados agora (não vai para o arquivo)
        self._verificando = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._comandos_registrados: str | None = None
        self._estado = self._ler()

    # ------------------------------------------------------------------ persistência

    def _ler(self) -> dict:
        estado = copy.deepcopy(PADRAO)
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return estado
        if isinstance(salvo.get("config"), dict):
            estado["config"].update({k: v for k, v in salvo["config"].items() if k in estado["config"]})
        if isinstance(salvo.get("itens"), list):
            estado["itens"] = [i for i in salvo["itens"] if isinstance(i, dict) and i.get("id")]
        if isinstance(salvo.get("conversas"), dict):
            estado["conversas"] = salvo["conversas"]
        return estado

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(self._estado, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(temporario, self.caminho)

    # ------------------------------------------------------------------ configuração

    def token(self) -> str:
        with self._lock:
            return (self._estado["config"].get("token") or "").strip()

    def config_publica(self) -> dict:
        with self._lock:
            cfg = dict(self._estado["config"])
        cfg["token"] = MASCARA if cfg.get("token") else ""
        cfg.pop("offset", None)
        cfg["pessoas"] = [{"chat_id": c, "nome": n} for c, n in self.pessoas().items()]
        return cfg

    def configurar(self, novo: dict) -> dict:
        with self._lock:
            cfg = self._estado["config"]
            if novo.get("token") is not None and novo["token"] != MASCARA:
                cfg["token"] = str(novo["token"]).strip()[:200]
                cfg["ultimo_erro"] = None
            if novo.get("ativo") is not None:
                cfg["ativo"] = bool(novo["ativo"])
            if cfg["ativo"] and not cfg["token"]:
                raise ValueError("Informe o token do bot do caixa (crie um bot no @BotFather).")
            self._gravar()
        return self.config_publica()

    # ------------------------------------------------------------------ itens (conferência na tela)

    @staticmethod
    def dados_preenchidos(item: dict) -> dict:
        """O lançamento já montado, do jeito que vai para o caixa (a tela só revisa e lança)."""
        lido = item.get("lido") or {}
        respostas = item.get("respostas") or {}
        return {"movimento": "Saída", "valor": lido.get("valor"), "data": lido.get("data") or item["recebido_em"][:10],
                "hora": lido.get("hora") or item["recebido_em"][11:16], "descricao": respostas.get("onde") or "",
                "local": lido.get("local") or "", "centro_custo": respostas.get("centro") or "",
                "pessoa": item.get("remetente") or ""}

    def _publico(self, item: dict) -> dict:
        publico = {k: item.get(k) for k in ("id", "chat_id", "remetente", "recebido_em", "nome_arquivo", "arquivo_id",
                                            "estado", "erro", "concluido_em", "criado")}
        publico["dados"] = self.dados_preenchidos(item)
        return publico

    def listar(self, incluir_concluidos: bool = False) -> list[dict]:
        with self._lock:
            itens = [i for i in self._estado["itens"]
                     if incluir_concluidos or i["estado"] in ("pendente", "conversa", "erro")]
            return [self._publico(i) for i in sorted(itens, key=lambda i: i["recebido_em"], reverse=True)]

    def contagem(self) -> int:
        with self._lock:
            return sum(1 for i in self._estado["itens"] if i["estado"] in ("pendente", "erro"))

    def arquivos_em_uso(self) -> set[str]:
        with self._lock:
            return {i["arquivo_id"] for i in self._estado["itens"]
                    if i.get("arquivo_id") and i["estado"] in ("pendente", "conversa", "erro")}

    def _item(self, id_: str) -> dict | None:
        return next((i for i in self._estado["itens"] if i["id"] == id_), None)

    def descartar(self, id_: str) -> bool:
        with self._lock:
            item = self._item(id_)
            if not item or item["estado"] not in ("pendente", "conversa", "erro"):
                return False
            item.update(estado="descartado", concluido_em=_agora())
            self._encerrar_conversa_do_item(item)
            self._gravar()
            return True

    def confirmar(self, id_: str, dados: dict, usuario: str) -> dict:
        """Alguém revisou na tela e mandou lançar no caixa."""
        from . import servico

        with self._lock:
            item = self._item(id_)
            if not item or item["estado"] not in ("pendente", "conversa", "erro"):
                raise servico.ErroCaixa("Este comprovante não está mais esperando revisão.")
            # Dois cliques em "Lançar" (ou duas pessoas ao mesmo tempo): só o primeiro lança.
            if id_ in self._lancando:
                raise servico.ErroCaixa("Este comprovante já está sendo lançado.")
            self._lancando.add(id_)
            arquivo = copy.deepcopy(item.get("arquivo"))
        try:
            registro = servico.lancar({**self.dados_preenchidos(item), **dados}, usuario, arquivo)
        finally:
            with self._lock:
                self._lancando.discard(id_)
        with self._lock:
            item.update(estado="lancado", concluido_em=_agora(), criado=registro["id"], erro=None)
            self._encerrar_conversa_do_item(item)
            self._gravar()
            return self._publico(item)

    def _encerrar_conversa_do_item(self, item: dict) -> None:
        conversas = self._estado["conversas"]
        for chat_id, conversa in list(conversas.items()):
            if conversa.get("item_id") == item["id"]:
                conversas.pop(chat_id, None)

    def _limpar_antigos(self) -> None:
        limite = (datetime.now() - timedelta(days=DIAS_MANTER_CONCLUIDOS)).isoformat()
        itens = [i for i in self._estado["itens"]
                 if i["estado"] in ("pendente", "conversa", "erro") or (i.get("concluido_em") or "") > limite]
        self._estado["itens"] = sorted(itens, key=lambda i: i["recebido_em"], reverse=True)[:MAX_ITENS]

    # ------------------------------------------------------------------ Telegram: envio

    def _enviar(self, chat_id: str, texto: str, botoes: list[list[dict]] | None = None) -> None:
        dados = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": True}
        if botoes:
            dados["reply_markup"] = {"inline_keyboard": botoes}
        try:
            canais._telegram(self.token(), "sendMessage", dados)
        except canais.ErroCanal as exc:
            log.warning("Bot do caixa: não foi possível responder: %s", exc)

    def _responder_botao(self, callback_id: str, chat_id: str, message_id, texto: str = "") -> None:
        try:
            canais._telegram(self.token(), "answerCallbackQuery", {"callback_query_id": callback_id, "text": texto[:190]})
            if message_id:  # tira os botões da pergunta já respondida (evita dois toques)
                canais._telegram(self.token(), "editMessageReplyMarkup",
                                 {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
        except canais.ErroCanal as exc:
            log.warning("Bot do caixa: falha ao responder o botão: %s", exc)

    def _registrar_comandos(self) -> None:
        token = self.token()
        if self._comandos_registrados == token:
            return
        try:
            canais._telegram(token, "setMyCommands", {"commands": [{"command": c, "description": d} for c, d in COMANDOS]})
            self._comandos_registrados = token
        except canais.ErroCanal as exc:
            log.warning("Bot do caixa: não foi possível registrar os comandos: %s", exc)

    # ------------------------------------------------------------------ conversa

    def _perguntar_onde(self, chat_id: str, item: dict) -> None:
        lido = item.get("lido") or {}
        partes = [f"💵 <b>{_moeda(lido['valor'])}</b>" if lido.get("valor") else "💵 Valor lido",
                  f"{date.fromisoformat(str(lido['data'])[:10]):%d/%m/%Y}" if lido.get("data") else "",
                  escape(lido.get("local") or "")]
        botoes = ([[{"text": f"✔ {lido['local'][:40]}", "callback_data": f"onde:lido@{item['id']}"}]] if lido.get("local") else None)
        self._enviar(chat_id, " · ".join(p for p in partes if p) + "\n\n<b>Onde foi gasto?</b>\n"
                     "Responda com uma frase (ex.: <i>gasolina da caminhonete</i>, <i>almoço da equipe da obra</i>).",
                     botoes)

    def _perguntar_centro(self, chat_id: str, conversa: dict) -> None:
        centros = self.centros()
        conversa["centros"] = centros[:40]
        botoes, linha = [], []
        for indice, nome in enumerate(conversa["centros"]):
            linha.append({"text": nome[:30], "callback_data": f"cc:{indice}@{conversa['item_id']}"})
            if len(linha) == 2:
                botoes.append(linha)
                linha = []
        if linha:
            botoes.append(linha)
        botoes.append([{"text": "➕ Cadastrar um novo centro de custo", "callback_data": f"cc:novo@{conversa['item_id']}"}])
        self._enviar(chat_id, "<b>Qual o centro de custo?</b>\nToque em uma opção (são os mesmos da aba Gastos).", botoes)

    def _finalizar(self, chat_id: str, item: dict) -> None:
        item["estado"] = "pendente"
        self._estado["conversas"].pop(chat_id, None)
        d = self.dados_preenchidos(item)
        self._enviar(chat_id, f"✅ <b>Anotado!</b> Saída de <b>{_moeda(d['valor'])}</b>\n"
                     f"{escape(d['descricao'] or 'sem descrição')} · {escape(d['centro_custo'] or 'sem centro de custo')}\n\n"
                     "Está no Fin Pro (Caixa → Conferência) para revisar e lançar.")

    def _nova_foto(self, chat_id: str, remetente: str, dados: bytes, nome_arquivo: str) -> None:
        impressao = hashlib.sha256(dados).hexdigest()
        with self._lock:
            if any(i.get("hash") == impressao and i["estado"] != "descartado" for i in self._estado["itens"]):
                self._enviar(chat_id, "Este comprovante já tinha sido enviado antes.")
                return
            aberta = self._estado["conversas"].pop(chat_id, None)
            if aberta:  # mandou outra foto no meio da conversa: a anterior fica para revisar do jeito que está
                anterior = self._item(aberta.get("item_id"))
                if anterior and anterior["estado"] == "conversa":
                    anterior["estado"] = "pendente"
        item = {"id": uuid.uuid4().hex[:12], "chat_id": chat_id, "remetente": remetente[:60], "recebido_em": _agora(),
                "hash": impressao, "nome_arquivo": Path(nome_arquivo or "comprovante").name[:120], "estado": "conversa",
                "erro": None, "lido": {}, "respostas": {}, "arquivo_id": None, "arquivo": None, "concluido_em": None,
                "criado": None}
        try:
            meta = self.salvar_arquivo(dados, item["nome_arquivo"])
            item.update(arquivo_id=meta.get("id"), arquivo={"caminho": meta.get("caminho") or "", "nome": meta.get("nome") or ""})
            lido = self.ler(dados, item["nome_arquivo"]) or {}
            item["lido"] = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in lido.items()}
        except Exception as exc:
            log.exception("Bot do caixa: não foi possível ler %s", nome_arquivo)
            item["erro"] = str(exc)[:200]
        conversa = {"item_id": item["id"], "etapa": "onde" if item["lido"].get("valor") else "valor"}
        with self._lock:
            self._estado["itens"].append(item)
            self._estado["conversas"][chat_id] = conversa
            self._limpar_antigos()
            self._gravar()
        if conversa["etapa"] == "valor":
            self._enviar(chat_id, "💵 Recebi o comprovante, mas não consegui ler o valor.\n<b>Qual foi o valor?</b> "
                                  "(ex.: 45,90)")
        else:
            self._perguntar_onde(chat_id, item)

    def _texto(self, chat_id: str, texto: str) -> None:
        with self._lock:
            conversa = self._estado["conversas"].get(chat_id)
            item = self._item(conversa["item_id"]) if conversa else None
        if not conversa or not item:
            self._enviar(chat_id, "Mande a <b>foto do cupom ou da nota</b> do gasto que eu anoto no caixa. "
                                  "Use /ajuda para ver como funciona.")
            return
        etapa = conversa["etapa"]
        if etapa == "valor":
            valor = _valor_digitado(texto)
            if not valor:
                self._enviar(chat_id, "Não entendi o valor. Mande só o número, por exemplo: <b>45,90</b>")
                return
            with self._lock:
                item["lido"]["valor"] = valor
                conversa["etapa"] = "onde"
                self._gravar()
            self._perguntar_onde(chat_id, item)
        elif etapa == "onde":
            with self._lock:
                item["respostas"]["onde"] = texto.strip()[:200]
                conversa["etapa"] = "centro"
                self._gravar()
            self._perguntar_centro(chat_id, conversa)
        elif etapa == "novo_centro":
            self._criar_centro(chat_id, conversa, item, texto)
        elif etapa in ("centro", "confirmar_novo"):
            escolhido = next((c for c in self.centros() if c.strip().lower() == texto.strip().lower()), None)
            if escolhido:
                with self._lock:
                    item["respostas"]["centro"] = escolhido
                    self._finalizar(chat_id, item)
                    self._gravar()
                return
            with self._lock:
                conversa.update(etapa="confirmar_novo", novo_nome=texto.strip()[:60])
                self._gravar()
            self._enviar(chat_id, f"Não achei o centro de custo “{escape(texto.strip()[:60])}”.",
                         [[{"text": f"➕ Cadastrar “{texto.strip()[:28]}”", "callback_data": f"cc:criar@{item['id']}"}],
                          [{"text": "📋 Escolher da lista", "callback_data": f"cc:lista@{item['id']}"}]])

    def _criar_centro(self, chat_id: str, conversa: dict, item: dict, nome: str) -> None:
        nome = re.sub(r"\s+", " ", nome or "").strip()[:60]
        if len(nome) < 2:
            self._enviar(chat_id, "Digite o nome do novo centro de custo (ex.: <i>Manutenção da frota</i>).")
            return
        try:
            criado = self.criar_centro(nome, f"{item.get('remetente') or 'Bot do caixa'} (Telegram)")
        except ValueError as exc:
            self._enviar(chat_id, f"Não consegui cadastrar: {escape(str(exc))}")
            return
        with self._lock:
            item["respostas"]["centro"] = criado
            item["respostas"]["centro_novo"] = True
            self._finalizar(chat_id, item)
            self._gravar()

    def _botao(self, chat_id: str, dado: str, callback_id: str, message_id) -> None:
        with self._lock:
            conversa = self._estado["conversas"].get(chat_id)
            item = self._item(conversa["item_id"]) if conversa else None
        # O botão leva o id do comprovante: um botão de uma conversa antiga não responde pela atual.
        dado, _, dono = dado.partition("@")
        if not conversa or not item or (dono and dono != item["id"]):
            self._responder_botao(callback_id, chat_id, message_id, "Esta pergunta já foi respondida.")
            return
        self._responder_botao(callback_id, chat_id, message_id)
        if dado == "onde:lido":
            with self._lock:
                item["respostas"]["onde"] = (item.get("lido") or {}).get("local") or ""
                conversa["etapa"] = "centro"
                self._gravar()
            self._perguntar_centro(chat_id, conversa)
        elif dado == "cc:novo":
            with self._lock:
                conversa["etapa"] = "novo_centro"
                self._gravar()
            self._enviar(chat_id, "<b>Qual o nome do novo centro de custo?</b>")
        elif dado == "cc:criar":
            self._criar_centro(chat_id, conversa, item, conversa.get("novo_nome") or "")
        elif dado == "cc:lista":
            with self._lock:
                conversa["etapa"] = "centro"
                self._gravar()
            self._perguntar_centro(chat_id, conversa)
        elif dado.startswith("cc:"):
            try:
                escolhido = conversa.get("centros", [])[int(dado[3:])]
            except (ValueError, IndexError):
                self._perguntar_centro(chat_id, conversa)
                return
            with self._lock:
                item["respostas"]["centro"] = escolhido
                self._finalizar(chat_id, item)
                self._gravar()

    def _comando(self, chat_id: str, texto: str, nome: str) -> None:
        comando = re.match(r"^/(\w+)", texto).group(1).lower()
        if comando in ("start", "ajuda", "help"):
            self._enviar(chat_id, f"Olá{', ' + escape(nome) if nome else ''}! Eu sou o <b>bot do caixa</b>.\n\n"
                                  "Pagou algo em dinheiro? Mande a <b>foto do cupom ou da nota</b>. Eu leio o valor, "
                                  "pergunto onde foi gasto e o centro de custo, e deixo pronto no Fin Pro.\n\n"
                                  "/resumo — entradas e saídas de hoje e do mês\n/cancelar — desistir do gasto atual")
        elif comando == "cancelar":
            with self._lock:
                conversa = self._estado["conversas"].pop(chat_id, None)
                item = self._item(conversa["item_id"]) if conversa else None
                if item and item["estado"] == "conversa":
                    item.update(estado="descartado", concluido_em=_agora())
                self._gravar()
            self._enviar(chat_id, "Tudo bem, cancelei." if conversa else "Não havia nenhum gasto sendo informado.")
        elif comando == "resumo":
            from . import servico

            dia, mes = servico.resumo("dia"), servico.resumo("mes")
            self._enviar(chat_id, "\n".join([
                "<b>Caixa</b>",
                f"Hoje: entradas {_moeda(dia['entradas']['total'])} · saídas {_moeda(dia['saidas']['total'])}",
                f"{mes['periodo']['rotulo'].capitalize()}: entradas {_moeda(mes['entradas']['total'])} · "
                f"saídas {_moeda(mes['saidas']['total'])}",
                f"Saldo em caixa: <b>{_moeda(mes['saldo_caixa'])}</b>"]))
        else:
            self._enviar(chat_id, "Não conheço esse comando. Use /ajuda.")

    # ------------------------------------------------------------------ Telegram: recebimento

    @staticmethod
    def _arquivo(mensagem: dict) -> tuple[str, str, int] | None:
        documento = mensagem.get("document")
        if isinstance(documento, dict):
            nome = documento.get("file_name") or "comprovante"
            tipo = documento.get("mime_type") or ""
            if tipo == "application/pdf" or tipo.startswith("image/") or nome.lower().endswith(EXTENSOES):
                return documento["file_id"], nome, int(documento.get("file_size") or 0)
            return None
        fotos = mensagem.get("photo")
        if isinstance(fotos, list) and fotos:
            maior = max(fotos, key=lambda f: int(f.get("file_size") or 0) or int(f.get("width", 0)) * int(f.get("height", 0)))
            return maior["file_id"], f"cupom-{datetime.now():%Y%m%d-%H%M%S}.jpg", int(maior.get("file_size") or 0)
        return None

    def verificar(self) -> dict:
        token = self.token()
        if not token:
            raise ValueError("Informe o token do bot do caixa.")
        self._registrar_comandos()
        with self._lock:
            offset = self._estado["config"].get("offset")
        pedido = {"limit": 50, "timeout": 0, "allowed_updates": ["message", "callback_query"]}
        if offset:
            pedido["offset"] = offset
        try:
            atualizacoes = canais._telegram(token, "getUpdates", pedido)
        except canais.ErroCanal as exc:
            with self._lock:
                self._estado["config"].update(ultima_verificacao=_agora(), ultimo_erro=str(exc))
                self._gravar()
            raise ValueError(str(exc)) from exc
        autorizados = self.pessoas()
        recebidos = 0
        for atualizacao in atualizacoes:
            with self._lock:
                self._estado["config"]["offset"] = int(atualizacao.get("update_id", 0)) + 1
            try:
                recebidos += self._tratar(atualizacao, autorizados)
            except Exception:
                log.exception("Bot do caixa: falha ao tratar uma mensagem")
        with self._lock:
            self._estado["config"].update(ultima_verificacao=_agora(), ultimo_erro=None)
            self._gravar()
        return {"recebidos": recebidos}

    def _tratar(self, atualizacao: dict, autorizados: dict) -> int:
        clique = atualizacao.get("callback_query")
        if clique:
            chat_id = str(((clique.get("message") or {}).get("chat") or {}).get("id") or "")
            if chat_id in autorizados:
                self._botao(chat_id, clique.get("data") or "", clique.get("id"), (clique.get("message") or {}).get("message_id"))
            return 0
        mensagem = atualizacao.get("message") or {}
        chat_id = str((mensagem.get("chat") or {}).get("id") or "")
        if not chat_id:
            return 0
        de = mensagem.get("from") or {}
        nome = autorizados.get(chat_id) or " ".join(p for p in (de.get("first_name"), de.get("last_name")) if p)
        if chat_id not in autorizados:
            self._enviar(chat_id, "Este bot é do caixa do escritório. Só usa quem já está cadastrado no bot dos "
                                  "boletos ou no bot de notas — peça ao responsável para incluir você.")
            return 0
        texto = (mensagem.get("text") or "").strip()
        if texto.startswith("/"):
            self._comando(chat_id, texto, de.get("first_name") or nome)
            return 0
        arquivo = self._arquivo(mensagem)
        if arquivo:
            file_id, nome_arquivo, tamanho = arquivo
            if tamanho and tamanho > TAMANHO_MAXIMO:
                self._enviar(chat_id, "Arquivo grande demais (máximo 20 MB).")
                return 0
            try:
                dados = canais.baixar_arquivo_telegram(self.token(), file_id)
            except canais.ErroCanal as exc:
                self._enviar(chat_id, f"Não consegui baixar o arquivo: {escape(str(exc))}")
                return 0
            self._nova_foto(chat_id, nome or chat_id, dados, nome_arquivo)
            return 1
        if texto:
            self._texto(chat_id, texto)
        return 0

    # ------------------------------------------------------------------ agendador

    def verificar_agora(self) -> dict:
        if not self._verificando.acquire(timeout=120):
            raise ValueError("Uma verificação já está em andamento. Tente de novo em instantes.")
        try:
            return self.verificar()
        finally:
            self._verificando.release()

    def iniciar_agendador(self, espera_inicial: float = 25) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            if self._parar.wait(espera_inicial):
                return
            while True:
                try:
                    with self._lock:
                        ativo = self._estado["config"].get("ativo")
                    if ativo and self.token():
                        self.verificar_agora()
                except ValueError as exc:
                    log.warning("Bot do caixa: %s", exc)
                except Exception:
                    log.exception("Falha ao verificar o bot do caixa")
                if self._parar.wait(INTERVALO):
                    return

        self._thread = threading.Thread(target=laco, name="bot-caixa", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

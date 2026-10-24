"""Bot do diesel (Telegram): comprovantes da compra no posto e canhotos dos abastecimentos.

Quem pode mandar arquivos são as pessoas e grupos já cadastrados nos outros bots. Quem **decide a máquina** é
o responsável (ou os responsáveis) escolhido na tela do bot — se ninguém foi escolhido, quem mandou decide.

* **Canhoto** → o bot lê cada linha (combustível, litros, preço do litro e total) e manda a foto para o
  responsável. Para **cada linha** ele escolhe a máquina — um mesmo pedido pode ter Diesel comum para a pá e S10 para
  o caminhão — e informa o horímetro/km, se quiser. Os litros saem do saldo e o bot responde com o saldo e a média
  de cada máquina. Quem mandou o canhoto é avisado.
* **Comprovante da compra** → lê valor, litros e combustível (botão rápido de 1.000 L) e soma ao saldo.
* **Relatórios** semanal (segunda), quinzenal (dias 1 e 16) e mensal (dia 1) chegam sozinhos para o responsável.
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
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from typing import Callable

from ..notificacoes import canais
from . import relatorio, servico
from .modelos import COMBUSTIVEIS, LITROS_POR_COMPRA

log = logging.getLogger("leitor_boletos.diesel")

MASCARA = "••••••••"
INTERVALO = 20
TAMANHO_MAXIMO = 20 * 1024 * 1024
EXTENSOES = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic")
MAX_ITENS = 400
DIAS_MANTER_CONCLUIDOS = 30
ABERTOS = ("conversa", "aguardando", "pendente", "erro")
COMANDOS = [("saldo", "Quanto diesel ainda tem"), ("medias", "Média de consumo de cada máquina"),
            ("relatorio", "Relatório da semana (ou: /relatorio mes, /relatorio mes detalhado, … completo)"),
            ("maquinas", "Máquinas cadastradas"), ("cancelar", "Desistir do que está sendo informado"),
            ("ajuda", "Como usar o bot do diesel")]
PADRAO = {"config": {"ativo": False, "token": "", "offset": 0, "ultima_verificacao": None, "ultimo_erro": None,
                     "gestores": [], "alerta_valor": servico.ALERTA_PADRAO, "hora_relatorio": "07:00",
                     "relatorios": {"semana": True, "quinzena": True, "mes": True}, "nivel_relatorio": "simples",
                     "enviados": {}},
          "itens": [], "conversas": {}}
CAMPOS_DA_LINHA = ("combustivel", "litros", "preco_litro", "valor", "maquina", "medidor")


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def descrever_linha(linha: dict) -> str:
    """"Diesel S10 · 200 L × R$ 7,450 = R$ 1.490,00" (o que der para mostrar)."""
    partes = [linha.get("combustivel") or "Combustível não identificado",
              servico.litros_br(linha["litros"]) if linha.get("litros") else "litros não lidos"]
    texto = " · ".join(partes)
    if linha.get("preco_litro"):
        texto += f" × {servico.moeda(linha['preco_litro'])}"
    if linha.get("valor"):
        texto += f" = {servico.moeda(linha['valor'])}"
    return texto


class BotDiesel:
    def __init__(self, caminho: Path, salvar_arquivo: Callable[[bytes, str], dict], pessoas: Callable[[], dict],
                 ler: Callable[[bytes, str, str], dict] | None = None):
        """``pessoas()`` → {chat_id: nome}; ``ler(dados, nome, legenda)`` lê as linhas, a data, o posto e a placa."""
        self.caminho = Path(caminho)
        self.salvar_arquivo = salvar_arquivo
        self.pessoas = pessoas
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

    def gestores(self) -> list[str]:
        """Quem escolhe a máquina dos canhotos (só vale quem ainda está nos outros bots)."""
        with self._lock:
            escolhidos = [str(c) for c in self._estado["config"].get("gestores") or []]
        pessoas = self.pessoas()
        return [c for c in escolhidos if c in pessoas]

    def config_publica(self) -> dict:
        with self._lock:
            cfg = copy.deepcopy(self._estado["config"])
        cfg["token"] = MASCARA if cfg.get("token") else ""
        cfg.pop("offset", None)
        cfg.pop("alerta_litros", None)  # limite antigo, em litros
        cfg["alerta_valor"] = self._alerta_configurado() if "alerta_valor" not in cfg else cfg["alerta_valor"]
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
            if isinstance(novo.get("gestores"), list):
                cfg["gestores"] = list(dict.fromkeys(str(c) for c in novo["gestores"] if re.fullmatch(r"-?\d{1,20}", str(c))))
            if novo.get("alerta_valor") is not None:
                cfg["alerta_valor"] = max(0.0, float(novo["alerta_valor"]))
            if novo.get("nivel_relatorio") in relatorio.NIVEIS:
                cfg["nivel_relatorio"] = novo["nivel_relatorio"]
            if novo.get("hora_relatorio"):
                h, m = str(novo["hora_relatorio"]).split(":")[:2]
                cfg["hora_relatorio"] = time(int(h), int(m)).strftime("%H:%M")
            if isinstance(novo.get("relatorios"), dict):
                for tipo in ("semana", "quinzena", "mes"):
                    if tipo in novo["relatorios"]:
                        cfg["relatorios"][tipo] = bool(novo["relatorios"][tipo])
            if cfg["ativo"] and not cfg["token"]:
                raise ValueError("Informe o token do bot do diesel (crie um bot no @BotFather).")
            self._gravar()
        return self.config_publica()

    # ------------------------------------------------------------------ linhas do canhoto

    @staticmethod
    def linhas(item: dict) -> list[dict]:
        """As linhas do canhoto (uma por combustível), com o que já foi respondido. Cria na primeira vez."""
        respostas = item.setdefault("respostas", {})
        if not respostas.get("linhas"):
            lido = item.get("lido") or {}
            itens = [i for i in (lido.get("itens") or []) if i.get("litros") or i.get("valor")]
            if not itens:
                itens = [{"combustivel": lido.get("combustivel") or "", "litros": lido.get("litros"),
                          "preco_litro": lido.get("preco_litro"), "valor": lido.get("valor")}]
            respostas["linhas"] = [{c: i.get(c) for c in CAMPOS_DA_LINHA} for i in itens]
            if len(respostas["linhas"]) == 1 and lido.get("medidor"):
                respostas["linhas"][0]["medidor"] = lido["medidor"]
            respostas["atual"] = 0
        return respostas["linhas"]

    def _linha_atual(self, item: dict) -> dict:
        linhas = self.linhas(item)
        return linhas[min(item["respostas"].get("atual", 0), len(linhas) - 1)]

    # ------------------------------------------------------------------ itens (conferência na tela)

    def dados_preenchidos(self, item: dict) -> dict:
        lido = item.get("lido") or {}
        linhas = self.linhas(copy.deepcopy(item))
        primeira = linhas[0] if linhas else {}
        return {"tipo": item.get("tipo") or "", "itens": linhas,
                "litros": round(sum(servico._num(l.get("litros")) for l in linhas), 2) or None,
                "valor": round(sum(servico._num(l.get("valor")) for l in linhas), 2) or None,
                "preco_litro": primeira.get("preco_litro"), "combustivel": primeira.get("combustivel") or "",
                "data": lido.get("data") or item["recebido_em"][:10], "hora": lido.get("hora") or item["recebido_em"][11:16],
                "posto": lido.get("posto") or "", "documento": lido.get("documento") or "",
                "maquina": primeira.get("maquina") or "", "medidor": primeira.get("medidor"),
                "placa": lido.get("placa") or "", "pessoa": item.get("remetente") or ""}

    def _publico(self, item: dict) -> dict:
        publico = {k: item.get(k) for k in ("id", "chat_id", "remetente", "recebido_em", "nome_arquivo", "arquivo_id",
                                            "estado", "erro", "concluido_em", "criado", "tipo")}
        publico["dados"] = self.dados_preenchidos(item)
        return publico

    def listar(self, incluir_concluidos: bool = False) -> list[dict]:
        with self._lock:
            itens = [i for i in self._estado["itens"] if incluir_concluidos or i["estado"] in ABERTOS]
            return [self._publico(i) for i in sorted(itens, key=lambda i: i["recebido_em"], reverse=True)]

    def contagem(self) -> int:
        with self._lock:
            return sum(1 for i in self._estado["itens"] if i["estado"] in ("aguardando", "pendente", "erro"))

    def arquivos_em_uso(self) -> set[str]:
        with self._lock:
            return {i["arquivo_id"] for i in self._estado["itens"] if i.get("arquivo_id") and i["estado"] in ABERTOS}

    def _item(self, id_: str) -> dict | None:
        return next((i for i in self._estado["itens"] if i["id"] == id_), None)

    def descartar(self, id_: str) -> bool:
        with self._lock:
            item = self._item(id_)
            if not item or item["estado"] not in ABERTOS:
                return False
            item.update(estado="descartado", concluido_em=_agora())
            self._encerrar_conversas(item)
            self._gravar()
            return True

    def confirmar(self, id_: str, dados: dict, usuario: str) -> dict:
        """Alguém conferiu na tela e mandou lançar (a compra ou o canhoto, com uma ou mais linhas)."""
        with self._lock:
            item = self._item(id_)
            if not item or item["estado"] not in ABERTOS:
                raise servico.ErroDiesel("Este arquivo não está mais esperando conferência.")
            base = self.dados_preenchidos(item)
        tipo = dados.get("tipo") or base["tipo"]
        if tipo not in ("compra", "canhoto"):
            raise servico.ErroDiesel("Escolha se é a compra do diesel ou um canhoto de abastecimento.")
        juntos = {**base, **{k: v for k, v in dados.items() if v not in (None, "")}}
        if "itens" not in dados:  # a tela mandou uma linha só (os campos soltos)
            juntos["itens"] = [{c: juntos.get(c) for c in CAMPOS_DA_LINHA}]
        return self._lancar(item, tipo, juntos, usuario)

    def _lancar(self, item: dict, tipo: str, dados: dict, usuario: str) -> dict:
        # A tela e o Telegram ao mesmo tempo (ou dois cliques): só o primeiro lança.
        with self._lock:
            if item["estado"] not in ABERTOS or item["id"] in self._lancando:
                raise servico.ErroDiesel("Este arquivo já foi lançado ou está sendo lançado agora.")
            self._lancando.add(item["id"])
        try:
            return self._gravar_lancamento(item, tipo, dados, usuario)
        finally:
            with self._lock:
                self._lancando.discard(item["id"])

    def _gravar_lancamento(self, item: dict, tipo: str, dados: dict, usuario: str) -> dict:
        arquivo = copy.deepcopy(item.get("arquivo"))
        comum = {k: dados.get(k) for k in ("data", "hora", "posto", "documento", "pessoa", "forma") if dados.get(k)}
        linhas = dados.get("itens") or [{c: dados.get(c) for c in CAMPOS_DA_LINHA}]
        if tipo == "compra":
            registros = [servico.lancar_compra({**comum, **{k: v for k, v in l.items() if v not in (None, "")}}, usuario,
                                               arquivo) for l in linhas if servico._num(l.get("litros")) or len(linhas) == 1]
            aba = "compras"
        else:
            registros = servico.lancar_canhoto(linhas, comum, usuario, arquivo)
            aba = "abastecimentos"
        with self._lock:
            item.update(estado="lancado", tipo=tipo, concluido_em=_agora(), erro=None,
                        criado={"aba": aba, "id": registros[0]["id"], "ids": [r["id"] for r in registros]})
            self._encerrar_conversas(item)
            self._gravar()
            publico = self._publico(item)
        publico["registros"] = registros
        return publico

    def _encerrar_conversas(self, item: dict) -> None:
        for chat_id, conversa in list(self._estado["conversas"].items()):
            if conversa.get("item_id") == item["id"]:
                self._estado["conversas"].pop(chat_id, None)

    def _limpar_antigos(self) -> None:
        limite = (datetime.now() - timedelta(days=DIAS_MANTER_CONCLUIDOS)).isoformat()
        itens = [i for i in self._estado["itens"] if i["estado"] in ABERTOS or (i.get("concluido_em") or "") > limite]
        self._estado["itens"] = sorted(itens, key=lambda i: i["recebido_em"], reverse=True)[:MAX_ITENS]

    # ------------------------------------------------------------------ Telegram: envio

    def _enviar(self, chat_id: str, texto: str, botoes: list[list[dict]] | None = None) -> None:
        dados = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": True}
        if botoes:
            dados["reply_markup"] = {"inline_keyboard": botoes}
        try:
            canais._telegram(self.token(), "sendMessage", dados)
        except canais.ErroCanal as exc:
            log.warning("Bot do diesel: não foi possível enviar para %s: %s", chat_id, exc)

    def _enviar_arquivo(self, chat_id: str, item: dict, legenda: str, botoes: list[list[dict]]) -> None:
        """Manda a foto do canhoto (ou o PDF) de volta, com a pergunta; sem o arquivo, só a mensagem."""
        if item.get("file_id"):
            metodo, campo = ("sendPhoto", "photo") if item.get("foto") else ("sendDocument", "document")
            try:
                canais._telegram(self.token(), metodo, {"chat_id": chat_id, campo: item["file_id"], "caption": legenda[:1000],
                                                        "parse_mode": "HTML", "reply_markup": {"inline_keyboard": botoes}})
                return
            except canais.ErroCanal as exc:
                log.warning("Bot do diesel: não foi possível reenviar o canhoto: %s", exc)
        self._enviar(chat_id, legenda, botoes)

    def _responder_botao(self, callback_id: str, chat_id: str, message_id, texto: str = "") -> None:
        try:
            canais._telegram(self.token(), "answerCallbackQuery", {"callback_query_id": callback_id, "text": texto[:190]})
            if message_id:
                canais._telegram(self.token(), "editMessageReplyMarkup",
                                 {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}})
        except canais.ErroCanal as exc:
            log.warning("Bot do diesel: falha ao responder o botão: %s", exc)

    def _registrar_comandos(self) -> None:
        token = self.token()
        if self._comandos_registrados == token:
            return
        try:
            canais._telegram(token, "setMyCommands", {"commands": [{"command": c, "description": d} for c, d in COMANDOS]})
            self._comandos_registrados = token
        except canais.ErroCanal as exc:
            log.warning("Bot do diesel: não foi possível registrar os comandos: %s", exc)

    # ------------------------------------------------------------------ conversa

    def _responsaveis(self, item: dict) -> list[str]:
        return self.gestores() or [item["chat_id"]]

    def _conversa(self, chat_id: str, item: dict, etapa: str) -> None:
        self._estado["conversas"][chat_id] = {"item_id": item["id"], "etapa": etapa}

    def _perguntar_tipo(self, chat_id: str, item: dict) -> None:
        self._enviar(chat_id, "Recebi o arquivo. <b>O que é?</b>", [
            [{"text": "🛢️ Comprovante da compra do diesel", "callback_data": f"tipo:{item['id']}:compra"}],
            [{"text": "⛽ Canhoto de abastecimento", "callback_data": f"tipo:{item['id']}:canhoto"}]])

    def _perguntar_litros(self, chat_id: str, item: dict) -> None:
        if item["tipo"] == "compra":
            self._enviar(chat_id, "🛢️ Comprovante da compra recebido. <b>Quantos litros foram comprados?</b>",
                         [[{"text": f"{servico.litros_br(LITROS_POR_COMPRA)}", "callback_data": f"lit:{item['id']}:{int(LITROS_POR_COMPRA)}"}]])
        else:
            self._enviar(chat_id, "⛽ Canhoto recebido, mas não consegui ler os litros.\n"
                                  "<b>Quantos litros foram abastecidos?</b> (ex.: 180)")

    def _botoes_maquinas(self, item: dict) -> list[list[dict]]:
        linha = self._linha_atual(item)
        combustivel = linha.get("combustivel") or ""
        ativas = servico.maquinas(incluir_inativas=False)
        # as máquinas que usam o combustível da linha vêm primeiro
        ativas.sort(key=lambda m: (bool(combustivel) and m.get("combustivel") not in ("", combustivel), servico.normalizar(m["nome"])))
        nomes = [m["nome"] for m in ativas]
        lida = self._maquina_lida(item)
        if lida and lida in nomes:
            nomes.remove(lida)
            nomes.insert(0, lida)
        item["opcoes"] = nomes[:40]
        botoes, fila = [], []
        for indice, nome in enumerate(item["opcoes"]):
            fila.append({"text": (f"✔ {nome}" if nome == lida else nome)[:32], "callback_data": f"maq:{item['id']}:{indice}"})
            if len(fila) == 2:
                botoes.append(fila)
                fila = []
        if fila:
            botoes.append(fila)
        botoes.append([{"text": "➕ Nova máquina", "callback_data": f"nova:{item['id']}"},
                       {"text": "✏️ Corrigir litros", "callback_data": f"corr:{item['id']}"}])
        if not combustivel:
            botoes.append([{"text": f"⛽ {c}", "callback_data": f"comb:{item['id']}:{i}"} for i, c in enumerate(COMBUSTIVEIS[:3])])
        botoes.append([{"text": "🗑 Descartar", "callback_data": f"desc:{item['id']}"}])
        return botoes

    @staticmethod
    def _maquina_lida(item: dict) -> str:
        """Máquina reconhecida pela placa do canhoto ou pelo nome escrito na mensagem."""
        lido = item.get("lido") or {}
        if lido.get("placa"):
            achada = servico.maquina_por_nome(lido["placa"])
            if achada:
                return achada["nome"]
        legenda = servico.normalizar(item.get("legenda"))
        if legenda:
            for m in servico.maquinas(incluir_inativas=False):
                if servico.normalizar(m["nome"]) in legenda or (m.get("placa") and servico.normalizar(m["placa"]) in legenda):
                    return m["nome"]
        return ""

    def _pergunta_da_linha(self, item: dict) -> str:
        linhas = self.linhas(item)
        atual = item["respostas"].get("atual", 0)
        if len(linhas) == 1:
            return "<b>De qual máquina?</b>"
        return f"<b>Linha {atual + 1} de {len(linhas)} — {escape(descrever_linha(linhas[atual]))}: de qual máquina?</b>"

    def _mandar_para_responsavel(self, item: dict) -> None:
        """O canhoto vai para o responsável escolher a máquina de cada linha (e quem mandou fica sabendo)."""
        dados = self.dados_preenchidos(item)
        linhas = self.linhas(item)
        item["estado"] = "aguardando"
        cabecalho = [f"⛽ <b>Canhoto de {escape(item.get('remetente') or 'alguém')}</b>"]
        detalhes = [escape(dados["posto"]) if dados.get("posto") else "",
                    date.fromisoformat(str(dados["data"])[:10]).strftime("%d/%m/%Y") if dados.get("data") else "",
                    f"pedido {escape(dados['documento'])}" if dados.get("documento") else "",
                    f"placa {escape(dados['placa'])}" if dados.get("placa") else ""]
        if any(detalhes):
            cabecalho.append(" · ".join(d for d in detalhes if d))
        if len(linhas) > 1:
            cabecalho += [f"{n + 1}) {escape(descrever_linha(l))}" for n, l in enumerate(linhas)]
            cabecalho.append(f"<b>Total: {servico.litros_br(dados['litros'])}"
                             f"{' · ' + servico.moeda(dados['valor']) if dados.get('valor') else ''}</b>")
        else:
            cabecalho.append(f"<b>{escape(descrever_linha(linhas[0]))}</b>")
        legenda = "\n".join(cabecalho) + "\n\n" + self._pergunta_da_linha(item)
        botoes = self._botoes_maquinas(item)
        responsaveis = self._responsaveis(item)
        for chat_id in responsaveis:
            self._enviar_arquivo(chat_id, item, legenda, botoes)
        if item["chat_id"] not in responsaveis:
            nomes = self.pessoas()
            self._enviar(item["chat_id"], f"⛽ Canhoto de <b>{servico.litros_br(dados['litros'])}</b> recebido. Mandei para "
                                          f"{escape(', '.join(nomes.get(c, 'o responsável') for c in responsaveis))} "
                                          "escolher a máquina.")

    def _proxima_linha(self, chat_id: str, item: dict) -> None:
        """Depois de uma linha resolvida: pergunta a próxima ou lança o canhoto."""
        linhas = self.linhas(item)
        pendente = next((n for n, l in enumerate(linhas) if not l.get("maquina")), None)
        if pendente is None:
            self._concluir_canhoto(chat_id, item, f"{self.pessoas().get(chat_id, 'Responsável')} (Telegram)")
            return
        with self._lock:
            item["respostas"]["atual"] = pendente
            self._gravar()
        self._enviar(chat_id, self._pergunta_da_linha(item), self._botoes_maquinas(item))

    def _concluir_canhoto(self, chat_id: str, item: dict, usuario: str) -> None:
        dados = self.dados_preenchidos(item)
        try:
            resultado = self._lancar(item, "canhoto", dados, usuario)
        except servico.ErroDiesel as exc:
            self._enviar(chat_id, f"Não consegui lançar: {escape(str(exc))}")
            return
        registros = resultado["registros"]
        atual = servico.saldo()
        linhas = []
        for r in registros:
            maquina = servico.maquina_por_nome(r["maquina"]) or {}
            leitura = ""
            if r.get("medidor"):
                leitura = f" · {'km' if maquina.get('medidor') == 'km' else 'horímetro'} {servico.numero_br(r['medidor'])}"
            linhas.append(f"✅ <b>{servico.litros_br(r['litros'])}</b> de {escape(r.get('combustivel') or '')} em "
                          f"<b>{escape(r['maquina'])}</b>{leitura}{' · ' + servico.moeda(r['valor']) if r.get('valor') else ''}")
        medias = [servico.texto_media(nome) for nome in dict.fromkeys(r["maquina"] for r in registros)]
        mensagem = "\n".join(linhas) + f"\n\n{servico.texto_saldo(atual)}\n\n" + "\n\n".join(medias)
        alerta = self._alerta_saldo(atual)
        for destino in self._responsaveis(item):
            self._enviar(destino, mensagem + alerta)
        if item["chat_id"] not in self._responsaveis(item):
            onde = ", ".join(f"{servico.litros_br(r['litros'])} em {escape(r['maquina'])}" for r in registros)
            self._enviar(item["chat_id"], f"✅ Seu canhoto foi lançado: {onde}.")

    def _alerta_saldo(self, atual: dict) -> str:
        with self._lock:
            limite = self._alerta_configurado()
        if limite and atual["pago"] and atual["valor"] <= limite:
            return f"\n\n⚠️ <b>Diesel acabando:</b> restam só {servico.moeda(atual['valor'])}."
        return ""

    def _alerta_configurado(self) -> float:
        """Limite do aviso em R$. Configurações antigas tinham o limite em litros: valem o padrão em reais."""
        valor = self._estado["config"].get("alerta_valor")
        return float(servico.ALERTA_PADRAO if valor is None else valor)

    def nivel_relatorio(self) -> str:
        with self._lock:
            return relatorio.nivel_valido(self._estado["config"].get("nivel_relatorio"))

    def alerta_valor(self) -> float:
        with self._lock:
            return self._alerta_configurado()

    def _concluir_compra(self, chat_id: str, item: dict, usuario: str) -> None:
        dados = self.dados_preenchidos(item)
        try:
            resultado = self._lancar(item, "compra", dados, usuario)
        except servico.ErroDiesel as exc:
            self._enviar(chat_id, f"Não consegui lançar a compra: {escape(str(exc))}")
            return
        partes = []
        for r in resultado["registros"]:
            preco = f" (R$ {r['preco_litro']:.3f}/L)".replace(".", ",") if r.get("preco_litro") else ""
            partes.append(f"🛢️ <b>Compra registrada:</b> {servico.litros_br(r['litros'])} de {escape(r.get('combustivel') or '')}"
                          f"{' por ' + servico.moeda(r['valor']) if r.get('valor') else ''}{preco}")
        mensagem = "\n".join(partes) + (f" · {escape(dados['posto'])}" if dados.get("posto") else "") + \
            f"\n\n{servico.texto_saldo()}"
        for destino in dict.fromkeys([chat_id, *self.gestores()]):
            self._enviar(destino, mensagem if destino == chat_id else
                         f"{mensagem}\n\n<i>Enviado por {escape(item.get('remetente') or 'alguém')}.</i>")

    def _seguir(self, chat_id: str, item: dict) -> None:
        """Próximo passo depois de saber o tipo e os litros."""
        if item["tipo"] == "compra":
            self._concluir_compra(chat_id, item, f"{item.get('remetente') or 'Bot do diesel'} (Telegram)")
        else:
            self._mandar_para_responsavel(item)

    def _tem_litros(self, item: dict) -> bool:
        return any(servico._num(l.get("litros")) for l in self.linhas(item))

    def _nova_foto(self, chat_id: str, remetente: str, dados: bytes, nome_arquivo: str, legenda: str = "",
                   file_id: str = "", foto: bool = False) -> None:
        impressao = hashlib.sha256(dados).hexdigest()
        with self._lock:
            if any(i.get("hash") == impressao and i["estado"] != "descartado" for i in self._estado["itens"]):
                self._enviar(chat_id, "Este arquivo já tinha sido enviado antes.")
                return
            self._estado["conversas"].pop(chat_id, None)
        item = {"id": uuid.uuid4().hex[:12], "chat_id": chat_id, "remetente": remetente[:60], "recebido_em": _agora(),
                "hash": impressao, "nome_arquivo": Path(nome_arquivo or "canhoto").name[:120], "legenda": legenda[:300],
                "estado": "conversa", "tipo": "", "erro": None, "lido": {}, "respostas": {}, "arquivo_id": None,
                "arquivo": None, "concluido_em": None, "criado": None, "file_id": file_id, "foto": foto, "opcoes": []}
        try:
            meta = self.salvar_arquivo(dados, item["nome_arquivo"])
            item.update(arquivo_id=meta.get("id"), arquivo={"caminho": meta.get("caminho") or "", "nome": meta.get("nome") or ""})
            lido = self.ler(dados, item["nome_arquivo"], legenda) or {}
            item["lido"] = json.loads(json.dumps(lido, default=lambda v: v.isoformat() if isinstance(v, date) else str(v)))
            item["tipo"] = lido.get("tipo") or ""
        except Exception as exc:
            log.exception("Bot do diesel: não foi possível ler %s", nome_arquivo)
            item["erro"] = str(exc)[:200]
        with self._lock:
            self._estado["itens"].append(item)
            self._limpar_antigos()
            if not item["tipo"]:
                self._conversa(chat_id, item, "tipo")
            elif not self._tem_litros(item):
                self._conversa(chat_id, item, "litros")
            self._gravar()
        if not item["tipo"]:
            self._perguntar_tipo(chat_id, item)
        elif not self._tem_litros(item):
            self._perguntar_litros(chat_id, item)
        else:
            with self._lock:
                self._seguir(chat_id, item)
                self._gravar()

    def _texto(self, chat_id: str, texto: str) -> None:
        with self._lock:
            conversa = self._estado["conversas"].get(chat_id)
            item = self._item(conversa["item_id"]) if conversa else None
        if not conversa or not item or item["estado"] not in ABERTOS:
            self._enviar(chat_id, "Mande a <b>foto do canhoto</b> do abastecimento ou o <b>comprovante da compra</b> "
                                  "do diesel. Use /ajuda para ver como funciona.")
            return
        etapa = conversa["etapa"]
        if etapa in ("litros", "corrigir"):
            litros = servico.numero_digitado(texto)
            if not litros:
                self._enviar(chat_id, "Não entendi. Mande só o número de litros, por exemplo: <b>180</b>")
                return
            with self._lock:
                linha = self._linha_atual(item)
                linha["litros"] = litros
                if linha.get("preco_litro"):
                    linha["valor"] = round(litros * servico._num(linha["preco_litro"]), 2)
                self._estado["conversas"].pop(chat_id, None)
                if etapa == "corrigir":  # o responsável corrigiu: volta a pergunta da máquina
                    self._enviar(chat_id, f"Litros corrigidos: <b>{escape(descrever_linha(linha))}</b>\n\n"
                                          f"{self._pergunta_da_linha(item)}", self._botoes_maquinas(item))
                else:
                    self._seguir(chat_id, item)
                self._gravar()
        elif etapa == "nova_maquina":
            nome = re.sub(r"\s+", " ", texto).strip()[:60]
            if len(nome) < 2:
                self._enviar(chat_id, "Digite o nome da máquina (ex.: <i>Escavadeira PC200</i>, <i>Caminhão Volvo ABC-1D23</i>).")
                return
            tipo = "Caminhão" if re.search(r"caminh|carreta|truck|[A-Z]{3}-?\d[A-Z0-9]\d{2}", nome, re.I) else "Máquina"
            combustivel = self._linha_atual(item).get("combustivel") or None
            try:
                maquina = servico.maquina_por_nome(nome) or servico.salvar_maquina(
                    {"nome": nome, "tipo": tipo, "combustivel": combustivel},
                    f"{self.pessoas().get(chat_id, 'Responsável')} (Telegram)")
            except servico.ErroDiesel as exc:
                self._enviar(chat_id, f"Não consegui cadastrar: {escape(str(exc))}")
                return
            self._escolheu_maquina(chat_id, item, maquina["nome"])
        elif etapa == "medidor":
            leitura = servico.numero_digitado(texto)
            if not leitura:
                self._enviar(chat_id, "Mande só o número (ex.: <b>4520</b>) ou toque em Pular.")
                return
            with self._lock:
                self._linha_atual(item)["medidor"] = leitura
                self._estado["conversas"].pop(chat_id, None)
                self._gravar()
            self._proxima_linha(chat_id, item)

    def _escolheu_maquina(self, chat_id: str, item: dict, nome: str) -> None:
        maquina = servico.maquina_por_nome(nome) or {}
        with self._lock:
            linha = self._linha_atual(item)
            linha["maquina"] = maquina.get("nome") or nome
            if not linha.get("combustivel") and maquina.get("combustivel"):
                linha["combustivel"] = maquina["combustivel"]
            self._estado["conversas"].pop(chat_id, None)
            precisa = maquina.get("medidor") in ("horas", "km") and not linha.get("medidor")
            if precisa:
                self._conversa(chat_id, item, "medidor")
            self._gravar()
        if precisa:
            qual = "o horímetro" if maquina["medidor"] == "horas" else "o km (hodômetro)"
            self._enviar(chat_id, f"<b>{escape(maquina['nome'])}</b>: qual {qual} no abastecimento?\n"
                                  "Mande o número — é o que calcula o consumo de verdade.",
                         [[{"text": "Pular", "callback_data": f"pular:{item['id']}"}]])
            return
        self._proxima_linha(chat_id, item)

    def _botao(self, chat_id: str, dado: str, callback_id: str, message_id) -> None:
        partes = dado.split(":")
        with self._lock:
            item = self._item(partes[1]) if len(partes) > 1 else None
        if not item or item["estado"] not in ABERTOS:
            self._responder_botao(callback_id, chat_id, message_id, "Este arquivo já foi resolvido.")
            return
        self._responder_botao(callback_id, chat_id, message_id)
        acao = partes[0]
        if acao == "tipo" and len(partes) == 3:
            with self._lock:
                item["tipo"] = "compra" if partes[2] == "compra" else "canhoto"
                self._estado["conversas"].pop(chat_id, None)
                sem_litros = not self._tem_litros(item)
                if sem_litros:
                    self._conversa(chat_id, item, "litros")
                self._gravar()
            if sem_litros:
                self._perguntar_litros(chat_id, item)
            else:
                with self._lock:
                    self._seguir(chat_id, item)
                    self._gravar()
        elif acao == "lit" and len(partes) == 3:
            with self._lock:
                self._linha_atual(item)["litros"] = float(partes[2])
                self._estado["conversas"].pop(chat_id, None)
                self._seguir(chat_id, item)
                self._gravar()
        elif acao == "maq" and len(partes) == 3:
            try:
                nome = item.get("opcoes", [])[int(partes[2])]
            except (ValueError, IndexError):
                self._enviar(chat_id, self._pergunta_da_linha(item), self._botoes_maquinas(item))
                return
            self._escolheu_maquina(chat_id, item, nome)
        elif acao == "comb" and len(partes) == 3:
            try:
                combustivel = COMBUSTIVEIS[int(partes[2])]
            except (ValueError, IndexError):
                return
            with self._lock:
                self._linha_atual(item)["combustivel"] = combustivel
                self._gravar()
            self._enviar(chat_id, f"Combustível: <b>{combustivel}</b>.\n\n{self._pergunta_da_linha(item)}",
                         self._botoes_maquinas(item))
        elif acao == "nova":
            with self._lock:
                self._conversa(chat_id, item, "nova_maquina")
                self._gravar()
            self._enviar(chat_id, "<b>Qual o nome da máquina?</b> (ex.: <i>Pá carregadeira 924</i>, <i>Caminhão ABC-1D23</i>)")
        elif acao == "corr":
            with self._lock:
                self._conversa(chat_id, item, "corrigir")
                self._gravar()
            self._enviar(chat_id, "<b>Quantos litros foram abastecidos?</b>")
        elif acao == "pular":
            with self._lock:
                self._estado["conversas"].pop(chat_id, None)
            self._proxima_linha(chat_id, item)
        elif acao == "desc":
            self.descartar(item["id"])
            self._enviar(chat_id, "Canhoto descartado.")

    def _comando(self, chat_id: str, texto: str, nome: str) -> None:
        partes = texto.split()
        comando = re.match(r"^/(\w+)", partes[0]).group(1).lower()
        if comando in ("start", "ajuda", "help"):
            self._enviar(chat_id, f"Olá{', ' + escape(nome) if nome else ''}! Eu sou o <b>bot do diesel</b>.\n\n"
                                  "⛽ Mande a <b>foto do canhoto</b> de cada abastecimento: eu leio os combustíveis e os "
                                  "litros, e o responsável escolhe a máquina.\n🛢️ Mande o <b>comprovante da compra</b> no "
                                  "posto: os litros entram no saldo.\n\n/saldo — quanto diesel ainda tem\n"
                                  "/medias — consumo de cada máquina\n/relatorio — relatório da semana "
                                  "(ou /relatorio quinzena, /relatorio mes, /relatorio ano). Para mais detalhes, "
                                  "acrescente <i>detalhado</i> ou <i>completo</i>: /relatorio mes completo\n"
                                  "/maquinas — máquinas cadastradas\n"
                                  "/cancelar — desistir do que está sendo informado")
        elif comando == "saldo":
            self._enviar(chat_id, servico.texto_saldo())
        elif comando in ("medias", "media"):
            ativas = [m["nome"] for m in servico.maquinas(incluir_inativas=False)]
            if not ativas:
                self._enviar(chat_id, "Nenhuma máquina cadastrada ainda.")
                return
            self._enviar(chat_id, "\n\n".join(servico.texto_media(n) for n in ativas[:15]))
        elif comando == "relatorio":
            palavras = [p.lower() for p in partes[1:]]
            tipos = {"semana": "semana", "semanal": "semana", "quinzena": "quinzena", "quinzenal": "quinzena",
                     "mes": "mes", "mensal": "mes", "mês": "mes", "ano": "ano", "anual": "ano"}
            tipo = next((tipos[p] for p in palavras if p in tipos), "semana")
            nivel = next((p for p in palavras if p in relatorio.NIVEIS), "simples")
            self._enviar(chat_id, relatorio.texto(tipo, nivel=nivel, alerta_valor=self.alerta_valor()))
        elif comando == "maquinas":
            lista = servico.maquinas(incluir_inativas=False)
            self._enviar(chat_id, "<b>Máquinas</b>\n" + "\n".join(
                f"• {escape(m['nome'])}{' · ' + escape(m['placa']) if m.get('placa') else ''}"
                f"{' · ' + escape(m['combustivel']) if m.get('combustivel') else ''}" for m in lista)
                if lista else "Nenhuma máquina cadastrada ainda. Cadastre no Fin Pro ou pelo botão “Nova máquina”.")
        elif comando == "cancelar":
            with self._lock:
                conversa = self._estado["conversas"].pop(chat_id, None)
                self._gravar()
            self._enviar(chat_id, "Tudo bem, cancelei. O arquivo fica na Conferência do Fin Pro." if conversa
                         else "Não havia nada sendo informado.")
        else:
            self._enviar(chat_id, "Não conheço esse comando. Use /ajuda.")

    # ------------------------------------------------------------------ Telegram: recebimento

    @staticmethod
    def _arquivo(mensagem: dict) -> tuple[str, str, int, bool] | None:
        documento = mensagem.get("document")
        if isinstance(documento, dict):
            nome = documento.get("file_name") or "canhoto"
            tipo = documento.get("mime_type") or ""
            if tipo == "application/pdf" or tipo.startswith("image/") or nome.lower().endswith(EXTENSOES):
                return documento["file_id"], nome, int(documento.get("file_size") or 0), False
            return None
        fotos = mensagem.get("photo")
        if isinstance(fotos, list) and fotos:
            maior = max(fotos, key=lambda f: int(f.get("file_size") or 0) or int(f.get("width", 0)) * int(f.get("height", 0)))
            return maior["file_id"], f"diesel-{datetime.now():%Y%m%d-%H%M%S}.jpg", int(maior.get("file_size") or 0), True
        return None

    def verificar(self) -> dict:
        token = self.token()
        if not token:
            raise ValueError("Informe o token do bot do diesel.")
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
                log.exception("Bot do diesel: falha ao tratar uma mensagem")
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
            self._enviar(chat_id, "Este bot é do controle de diesel do escritório. Só usa quem já está cadastrado no "
                                  "bot dos boletos ou no bot de notas — peça ao responsável para incluir você.")
            return 0
        texto = (mensagem.get("text") or "").strip()
        if texto.startswith("/"):
            self._comando(chat_id, texto, de.get("first_name") or nome)
            return 0
        arquivo = self._arquivo(mensagem)
        if arquivo:
            file_id, nome_arquivo, tamanho, foto = arquivo
            if tamanho and tamanho > TAMANHO_MAXIMO:
                self._enviar(chat_id, "Arquivo grande demais (máximo 20 MB).")
                return 0
            try:
                dados = canais.baixar_arquivo_telegram(self.token(), file_id)
            except canais.ErroCanal as exc:
                self._enviar(chat_id, f"Não consegui baixar o arquivo: {escape(str(exc))}")
                return 0
            self._nova_foto(chat_id, nome or chat_id, dados, nome_arquivo, (mensagem.get("caption") or "").strip(),
                            file_id, foto)
            return 1
        if texto:
            self._texto(chat_id, texto)
        return 0

    # ------------------------------------------------------------------ relatórios automáticos

    def relatorios_devidos(self, agora: datetime | None = None) -> list[tuple[str, date]]:
        """Relatórios que já deviam ter saído hoje: (tipo, data de referência do período fechado)."""
        agora = agora or datetime.now()
        with self._lock:
            cfg = self._estado["config"]
            hora = cfg.get("hora_relatorio") or "07:00"
            ligados = cfg.get("relatorios") or {}
            enviados = cfg.get("enviados") or {}
        h, m = (int(x) for x in hora.split(":")[:2])
        if agora.time() < time(h, m):
            return []
        hoje = agora.date()
        devidos = []
        if ligados.get("semana") and hoje.weekday() == 0:
            devidos.append(("semana", hoje - timedelta(days=7)))
        if ligados.get("quinzena") and hoje.day in (1, 16):
            devidos.append(("quinzena", hoje - timedelta(days=1)))
        if ligados.get("mes") and hoje.day == 1:
            devidos.append(("mes", hoje - timedelta(days=1)))
        return [(tipo, ref) for tipo, ref in devidos
                if enviados.get(tipo) != servico.periodo(tipo, ref)[0].isoformat()]

    def enviar_relatorios(self, agora: datetime | None = None) -> list[str]:
        destinos = self.gestores()
        if not destinos or not self.token():
            return []
        enviados = []
        for tipo, referencia in self.relatorios_devidos(agora):
            texto = relatorio.texto(tipo, referencia, self.nivel_relatorio(), self.alerta_valor())
            for chat_id in destinos:
                self._enviar(chat_id, texto)
            with self._lock:
                self._estado["config"].setdefault("enviados", {})[tipo] = servico.periodo(tipo, referencia)[0].isoformat()
                self._gravar()
            enviados.append(tipo)
        return enviados

    # ------------------------------------------------------------------ agendador

    def verificar_agora(self) -> dict:
        if not self._verificando.acquire(timeout=120):
            raise ValueError("Uma verificação já está em andamento. Tente de novo em instantes.")
        try:
            return self.verificar()
        finally:
            self._verificando.release()

    def iniciar_agendador(self, espera_inicial: float = 30) -> None:
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
                        self.enviar_relatorios()
                except ValueError as exc:
                    log.warning("Bot do diesel: %s", exc)
                except Exception:
                    log.exception("Falha ao verificar o bot do diesel")
                if self._parar.wait(INTERVALO):
                    return

        self._thread = threading.Thread(target=laco, name="bot-diesel", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

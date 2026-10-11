"""Bot de notas fiscais: recebe pelo Telegram as notas, os cheques e os comprovantes dos clientes.

É um bot **separado** do bot dos boletos (outro token, criado no @BotFather só para isto). Ao receber um
arquivo, o sistema descobre se é nota fiscal, cheque ou comprovante:

* **nota fiscal** — lança as linhas no fechamento da empresa e responde com o total do fechamento;
* **cheque** — guarda banco, agência, cooperativa, número, valor e a data do depósito, e passa a avisar do
  vencimento; as notas dos pedidos citados ficam "em cheque";
* **comprovante** de Pix, TED ou depósito — dá baixa nas notas fiscais citadas e responde quanto falta.

O que não dá para reconhecer com segurança fica na tela **Empresas → Conferência**, para alguém confirmar.
Todo dia 20 (ou no dia escolhido) o bot envia o fechamento de cada empresa.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from ..notificacoes import canais
from . import leitura, servico
from .relatorio import resumo_telegram

log = logging.getLogger("leitor_boletos.empresas")

INTERVALO = 45
TAMANHO_MAXIMO = 20 * 1024 * 1024
EXTENSOES = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".xml")
MAX_ITENS = 300
DIAS_MANTER_CONCLUIDOS = 30


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def numeros_citados(dados: dict) -> list[str]:
    """Números de NF e de pedido lidos no comprovante (ajudam a achar o cheque certo)."""
    return [str(n) for n in (dados.get("notas") or []) + (dados.get("pedidos") or [])]


class CaixaNotas:
    def __init__(self, caminho: Path, config, salvar_arquivo: Callable[[bytes, str], dict], comandos=None):
        """``salvar_arquivo(dados, nome)`` guarda o arquivo e devolve ``{"id", "nome", "caminho"}``."""
        self.caminho = Path(caminho)
        self.config = config
        self.salvar_arquivo = salvar_arquivo
        self.comandos = comandos
        self._comandos_registrados: str | None = None
        self._lock = threading.RLock()
        self._verificando = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._itens = self._ler()

    # ------------------------------------------------------------------ persistência

    def _ler(self) -> list[dict]:
        try:
            salvo = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        itens = salvo.get("itens") if isinstance(salvo, dict) else salvo
        return [i for i in itens if isinstance(i, dict) and i.get("id")] if isinstance(itens, list) else []

    def _gravar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps({"itens": self._itens}, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temporario, self.caminho)

    def _limpar_antigos(self) -> None:
        limite = (datetime.now() - timedelta(days=DIAS_MANTER_CONCLUIDOS)).isoformat()
        itens = [i for i in self._itens if i["estado"] in ("pendente", "erro") or (i.get("concluido_em") or "") > limite]
        self._itens = sorted(itens, key=lambda i: i["recebido_em"], reverse=True)[:MAX_ITENS]

    # ------------------------------------------------------------------ itens

    @staticmethod
    def _publico(item: dict) -> dict:
        return {chave: item.get(chave) for chave in
                ("id", "origem", "remetente", "legenda", "recebido_em", "nome_arquivo", "arquivo_id", "estado", "erro",
                 "tipo", "resumo", "analise", "empresa", "concluido_em", "criados")}

    def listar(self, incluir_concluidos: bool = False) -> list[dict]:
        with self._lock:
            itens = [i for i in self._itens if incluir_concluidos or i["estado"] in ("pendente", "erro")]
            return [self._publico(i) for i in sorted(itens, key=lambda i: i["recebido_em"], reverse=True)]

    def obter(self, id_: str) -> dict | None:
        with self._lock:
            item = next((i for i in self._itens if i["id"] == id_), None)
            return copy.deepcopy(item) if item else None

    def contagem(self) -> int:
        with self._lock:
            return sum(1 for i in self._itens if i["estado"] in ("pendente", "erro"))

    def arquivos_em_uso(self) -> set[str]:
        with self._lock:
            return {i["arquivo_id"] for i in self._itens if i.get("arquivo_id") and i["estado"] in ("pendente", "erro")}

    def descartar(self, id_: str) -> bool:
        with self._lock:
            item = next((i for i in self._itens if i["id"] == id_), None)
            if not item or item["estado"] not in ("pendente", "erro"):
                return False
            item.update(estado="descartado", concluido_em=_agora())
            self._gravar()
            return True

    # ------------------------------------------------------------------ recebimento

    def receber(self, dados: bytes, nome: str, origem: str = "telegram", remetente: str = "", legenda: str = "",
                usuario: str = "") -> dict | None:
        """Lê o arquivo, decide o que fazer e devolve o item (None se o arquivo já tinha chegado antes)."""
        impressao = hashlib.sha256(dados).hexdigest()
        with self._lock:
            if any(i.get("hash") == impressao for i in self._itens):
                return None
        item = {"id": uuid.uuid4().hex[:12], "origem": origem, "remetente": (remetente or "")[:120],
                "legenda": (legenda or "")[:300], "recebido_em": _agora(), "hash": impressao,
                "nome_arquivo": Path(nome or "arquivo").name[:120], "estado": "pendente", "erro": None,
                "tipo": "", "analise": None, "empresa": "", "arquivo_id": None, "concluido_em": None,
                "criados": [], "resumo": ""}
        try:
            meta = self.salvar_arquivo(dados, item["nome_arquivo"])
            item["arquivo_id"] = meta.get("id")
            item["arquivo"] = {"caminho": meta.get("caminho") or "", "nome": meta.get("nome") or item["nome_arquivo"]}
            analise = leitura.analisar(dados, item["nome_arquivo"], legenda)
            item["tipo"] = analise["tipo"]
            item["analise"] = leitura.publico(analise)["dados"]
            self._tratar(item, analise, usuario or remetente)
        except Exception as exc:
            log.exception("Falha ao ler o arquivo %s recebido no bot de notas", nome)
            item.update(estado="erro", erro=str(exc)[:300] or "Não foi possível ler o arquivo.")
        with self._lock:
            self._itens.append(item)
            self._limpar_antigos()
            self._gravar()
        log.info("Bot de notas: %s (%s/%s)", item["nome_arquivo"], item["tipo"] or "não reconhecido", item["estado"])
        return item

    # ------------------------------------------------------------------ o que fazer com cada tipo

    def _tratar(self, item: dict, analise: dict, usuario: str) -> None:
        tipo = analise["tipo"]
        dados = analise["dados"]
        if tipo == "nota":
            self._tratar_nota(item, dados, usuario)
        elif tipo == "cheque":
            self._tratar_cheque(item, dados, usuario)
        elif tipo == "comprovante":
            self._tratar_comprovante(item, dados, usuario)
        elif tipo == "fechamento":
            item["resumo"] = (f"Print de fechamento com {len(dados.get('linhas') or [])} linha(s), "
                              f"{servico.moeda(dados.get('total'))}. Confira e importe no Fin Pro.")
        else:
            item.update(estado="erro", erro="Não reconheci o arquivo (não parece nota fiscal, cheque nem comprovante).")

    def _tratar_nota(self, item: dict, dados: dict, usuario: str) -> None:
        destinatario = dados.get("destinatario") or {}
        empresa = servico.identificar_empresa(cnpj=destinatario.get("cnpj") or "", nome=destinatario.get("nome") or "")
        item["empresa"] = (empresa or {}).get("nome") or destinatario.get("nome") or ""
        itens = dados.get("itens") or []
        numero_nf = servico.numero(dados.get("numero_nf"))
        ja_lancada = servico.notas_por_numero(numero_nf, item["empresa"]) if numero_nf else []
        if ja_lancada:
            item.update(estado="ja_lancado", concluido_em=_agora(),
                        resumo=f"A nota {numero_nf} já estava lançada no fechamento de {item['empresa']}.")
            return
        materiais_ok = all((i.get("material") or "").strip() for i in itens)
        pronta = (bool(itens) and bool(numero_nf) and materiais_ok
                  and bool(destinatario.get("nome") or empresa) and dados.get("confianca", 0) >= 0.8)
        if not pronta:
            falta = "o nome do material" if itens and not materiais_ok else "os dados"
            item["resumo"] = f"Nota fiscal recebida: confira {falta} no Fin Pro antes de lançar."
            return
        nome_empresa = (empresa or {}).get("nome") or destinatario.get("nome")
        if not empresa:
            empresa = servico.garantir_empresa(nome_empresa, destinatario.get("cnpj") or "", usuario)
            nome_empresa = empresa["nome"]
            item["empresa"] = nome_empresa
        pedidos = dados.get("pedidos") or []
        linhas = [{**i, "numero_nf": numero_nf, "data": dados.get("data"),
                   "pedido": i.get("pedido") or (pedidos[0] if pedidos else "")} for i in itens]
        criadas = servico.lancar_notas(nome_empresa, linhas, usuario, item.get("arquivo"))
        f = servico.fechamento(nome_empresa)
        item.update(estado="lancado", concluido_em=_agora(), criados=[{"aba": "notas", "id": n["id"]} for n in criadas],
                    resumo=f"NF {numero_nf} lançada para {nome_empresa}: {servico.moeda(dados.get('valor_total'))}.",
                    fechamento={"empresa": nome_empresa, "total": f["totais"]["total"], "falta": f["totais"]["falta"],
                                "competencia": f["competencia"]})

    def _tratar_cheque(self, item: dict, dados: dict, usuario: str) -> None:
        pedidos = dados.get("pedidos") or []
        notas = dados.get("notas") or []
        empresa = self._empresa_do_cheque(dados, item.get("legenda") or "")
        nome_empresa = (empresa or {}).get("nome") or servico._empresa_pelas_notas(
            servico.lista_de_numeros(notas), servico.lista_de_numeros(pedidos))
        item["empresa"] = nome_empresa
        parecido = servico.cheque_parecido(dados)
        if parecido:
            item.update(estado="ja_lancado", concluido_em=_agora(),
                        resumo=f"Este cheque já estava cadastrado (#{parecido['id']}, {servico.moeda(parecido.get('valor'))}).")
            return
        if not (dados.get("valor") and nome_empresa and dados.get("vencimento")):
            item["resumo"] = ("Cheque recebido: confira valor, data do depósito e empresa no Fin Pro. "
                              "Dica: escreva na legenda “pedido 7043, bom para 12/10”.")
            return
        cheque = servico.lancar_cheque({**dados, "empresa": nome_empresa}, usuario, item.get("arquivo"))
        item.update(estado="lancado", concluido_em=_agora(), criados=[{"aba": "cheques", "id": cheque["id"]}],
                    resumo=f"Cheque de {nome_empresa} guardado: {servico.moeda(cheque.get('valor'))}, "
                           f"bom para {cheque['vencimento']:%d/%m/%Y}." if cheque.get("vencimento") else "Cheque guardado.")

    @staticmethod
    def _empresa_do_cheque(dados: dict, legenda: str) -> dict | None:
        """De quem é o cheque: pelo CNPJ impresso, pelo nome de quem assinou ou pelo que veio na legenda."""
        for documento in dados.get("documentos") or []:
            empresa = servico.identificar_empresa(cnpj=documento)
            if empresa:
                return empresa
        return servico.identificar_empresa(nome=dados.get("emitente") or "", texto=f"{legenda} {dados.get('emitente') or ''}")

    def _tratar_deposito_de_cheque(self, item: dict, dados: dict, usuario: str) -> None:
        """Comprovante do banco de um depósito de cheque: acha o cheque pela CMC-7, compensa e baixa as notas.

        Quem aparece no comprovante é a própria empresa (o titular da conta), então a empresa do cliente vem do cheque.
        """
        numeros = [c.get("numero") for c in dados.get("cheques") or [] if c.get("numero")]
        achados = servico.cheques_do_deposito(dados)
        if not achados:
            quais = f"nº {', '.join(numeros)}" if numeros else f"de {servico.moeda(dados.get('valor'))}"
            item["resumo"] = (f"Comprovante de depósito de cheque recebido, mas não achei o cheque {quais} em carteira. "
                              "Confira no Fin Pro e escolha o cheque.")
            return
        quando = servico._data(dados.get("data"))
        recebimentos = [servico.compensar_cheque(c, usuario, quando, item.get("arquivo")) for c in achados]
        empresas = list(dict.fromkeys(c.get("empresa") or "" for c in achados))
        item["empresa"] = ", ".join(e for e in empresas if e)
        baixas = [b for r in recebimentos for b in (r.get("baixas") or [])]
        f = servico.fechamento(empresas[0]) if empresas and empresas[0] else None
        descricao = ", ".join(f"nº {c.get('numero') or c['id']}" for c in achados)
        item.update(estado="lancado", concluido_em=_agora(),
                    criados=[{"aba": "recebimentos", "id": r["id"]} for r in recebimentos],
                    resumo=f"Depósito registrado: cheque {descricao} de {item['empresa']} "
                           f"({servico.moeda(sum(servico._valor(c, 'valor') for c in achados))}) compensado"
                           f"{' em ' + format(quando, '%d/%m/%Y') if quando else ''}.",
                    pagamento={"valor": round(sum(servico._valor(c, "valor") for c in achados), 2), "baixas": baixas,
                               "sobra": 0, "empresa": item["empresa"],
                               "falta": f["totais"]["falta"] if f else 0, "total": f["totais"]["total"] if f else 0})

    def _tratar_comprovante(self, item: dict, dados: dict, usuario: str) -> None:
        if dados.get("deposito_cheque"):
            self._tratar_deposito_de_cheque(item, dados, usuario)
            return
        numeros_nf = servico.lista_de_numeros(dados.get("notas"))
        pedidos = servico.lista_de_numeros(dados.get("pedidos"))
        empresa = servico.identificar_empresa(texto=f"{item.get('legenda') or ''} {dados.get('pagador') or ''}")
        nome_empresa = (empresa or {}).get("nome") or servico._empresa_pelas_notas(numeros_nf, pedidos)
        item["empresa"] = nome_empresa
        if dados.get("agendado"):
            item["resumo"] = "Este comprovante é de um agendamento: mande de novo quando o pagamento for efetivado."
            return
        if not (dados.get("valor") and nome_empresa):
            item["resumo"] = ("Comprovante recebido: não consegui saber de qual empresa ou de quais notas é. "
                              "Confira no Fin Pro (ou escreva na legenda “NF 6859, 6869”).")
            return
        cheque = servico.cheque_do_comprovante(nome_empresa, dados.get("valor"),
                                               f"{item.get('legenda') or ''} {' '.join(numeros_citados(dados))}")
        if cheque:  # comprovante do depósito de um cheque pré-datado: compensa o cheque e baixa as notas dele
            recebimento = servico.compensar_cheque(cheque, usuario, servico._data(dados.get("data")))
            item["resumo_cheque"] = f"Cheque {cheque.get('numero') or ''} de {nome_empresa} compensado."
        else:
            recebimento = servico.registrar_recebimento({**dados, "empresa": nome_empresa}, usuario, item.get("arquivo"))
        f = servico.fechamento(nome_empresa)
        item.update(estado="lancado", concluido_em=_agora(),
                    criados=[{"aba": "recebimentos", "id": recebimento["id"]}],
                    resumo=item.get("resumo_cheque")
                           or f"Recebimento de {servico.moeda(recebimento.get('valor'))} baixado em "
                              f"{len(recebimento.get('baixas') or [])} nota(s) de {nome_empresa}.",
                    pagamento={"valor": recebimento.get("valor"), "baixas": recebimento.get("baixas") or [],
                               "sobra": recebimento.get("sobra") or 0, "empresa": nome_empresa,
                               "falta": f["totais"]["falta"], "total": f["totais"]["total"]})

    # ------------------------------------------------------------------ conferência na tela

    def confirmar(self, id_: str, tipo: str, dados: dict, usuario: str) -> dict:
        """Alguém conferiu na tela o que o robô leu e mandou lançar."""
        item = self.obter(id_)
        if not item or item["estado"] not in ("pendente", "erro"):
            raise servico.ErroEmpresas("Este arquivo não está mais aguardando conferência.")
        arquivo = item.get("arquivo")
        if tipo == "nota":
            empresa = dados.get("empresa") or item.get("empresa")
            criados = servico.lancar_notas(empresa, dados.get("itens") or [], usuario, arquivo,
                                           dados.get("competencia") or "")
            criados = [{"aba": "notas", "id": n["id"]} for n in criados]
        elif tipo == "cheque":
            cheque = servico.lancar_cheque({**dados}, usuario, arquivo)
            criados = [{"aba": "cheques", "id": cheque["id"]}]
        elif tipo == "comprovante" and str(dados.get("cheque_id") or "").isdigit():
            cheque = servico.banco().obter(int(dados["cheque_id"]), "cheques")
            recebimento = servico.compensar_cheque(cheque, usuario, servico._data(dados.get("data")), arquivo)
            criados = [{"aba": "recebimentos", "id": recebimento["id"]}]
        elif tipo == "comprovante":
            recebimento = servico.registrar_recebimento({**dados}, usuario, arquivo)
            criados = [{"aba": "recebimentos", "id": recebimento["id"]}]
        else:
            raise servico.ErroEmpresas("Escolha se o arquivo é nota fiscal, cheque ou comprovante.")
        with self._lock:
            guardado = next((i for i in self._itens if i["id"] == id_), None)
            if guardado:
                guardado.update(estado="lancado", concluido_em=_agora(), criados=criados, tipo=tipo,
                                empresa=dados.get("empresa") or guardado.get("empresa"), erro=None)
                self._gravar()
            return self._publico(guardado or item)

    # ------------------------------------------------------------------ Telegram

    def _responder(self, token: str, chat_id: str, texto: str) -> None:
        try:
            canais.enviar_telegram(token, chat_id, texto)
        except canais.ErroCanal as exc:
            log.warning("Bot de notas: não foi possível responder no Telegram: %s", exc)

    def _registrar_comandos(self, token: str) -> None:
        if not self.comandos or self._comandos_registrados == token:
            return
        try:
            canais._telegram(token, "setMyCommands",
                             {"commands": [{"command": c, "description": d} for c, d in self.comandos.COMANDOS]})
            self._comandos_registrados = token
        except canais.ErroCanal as exc:
            log.warning("Bot de notas: não foi possível registrar os comandos: %s", exc)

    @staticmethod
    def _arquivo_da_mensagem(mensagem: dict) -> tuple[str, str, int] | None:
        documento = mensagem.get("document")
        if isinstance(documento, dict):
            nome = documento.get("file_name") or "arquivo"
            tipo = documento.get("mime_type") or ""
            if tipo in ("application/pdf", "text/xml", "application/xml") or tipo.startswith("image/") \
                    or nome.lower().endswith(EXTENSOES):
                return documento["file_id"], nome, int(documento.get("file_size") or 0)
            return None
        fotos = mensagem.get("photo")
        if isinstance(fotos, list) and fotos:
            maior = max(fotos, key=lambda f: int(f.get("file_size") or 0) or int(f.get("width", 0)) * int(f.get("height", 0)))
            return maior["file_id"], f"foto-{datetime.now():%Y%m%d-%H%M%S}.jpg", int(maior.get("file_size") or 0)
        return None

    def mensagem_resposta(self, item: dict | None) -> str:
        if item is None:
            return "Este arquivo já tinha sido enviado antes."
        if item["estado"] == "erro":
            return ("Recebi o arquivo, mas não reconheci o que é. Ele ficou no Fin Pro para conferência.\n"
                    "Mande a nota fiscal (XML, PDF ou foto), o cheque escaneado ou o comprovante do pagamento.")
        if item["estado"] == "ja_lancado":
            return f"ℹ️ {item['resumo']}"
        if item["estado"] == "lancado" and item.get("fechamento"):
            f = item["fechamento"]
            return (f"✅ {item['resumo']}\n\nFechamento de {f['empresa']} ({f['competencia']}): "
                    f"<b>{servico.moeda(f['total'])}</b>\nFalta receber: <b>{servico.moeda(f['falta'])}</b>")
        if item["estado"] == "lancado" and item.get("pagamento"):
            p = item["pagamento"]
            linhas = [f"✅ Recebimento de <b>{servico.moeda(p['valor'])}</b> registrado para {p['empresa']}."]
            for baixa in p["baixas"][:10]:
                marca = "quitada" if baixa["quitada"] else "parcial"
                linhas.append(f"• NF {baixa['numero_nf'] or '—'}: {servico.moeda(baixa['valor'])} ({marca})")
            if p["sobra"] > 0.01 and not p["baixas"]:
                linhas.append("Ainda não há nota em aberto: o valor ficou como crédito e baixa sozinho "
                              "quando a nota chegar.")
            elif p["sobra"] > 0.01:
                linhas.append(f"Sobrou {servico.moeda(p['sobra'])} como crédito da empresa.")
            linhas.append(f"\nFechamento: {servico.moeda(p['total'])} · falta <b>{servico.moeda(p['falta'])}</b>")
            return "\n".join(linhas)
        if item["estado"] == "lancado":
            return f"✅ {item['resumo']}"
        return f"📥 {item['resumo'] or 'Arquivo recebido. Confira no Fin Pro.'}"

    def verificar(self) -> dict:
        """Lê as mensagens novas do bot de notas (arquivos e comandos)."""
        token = self.config.token()
        if not token:
            raise ValueError("Informe o token do bot de notas fiscais.")
        bot = self.config.bot()
        cadastrados = {d["chat_id"]: d.get("nome") or "" for d in self.config.destinatarios()}
        self._registrar_comandos(token)
        pedido = {"limit": 50, "timeout": 0}
        if bot.get("offset"):
            pedido["offset"] = bot["offset"]
        try:
            atualizacoes = canais._telegram(token, "getUpdates", pedido)
        except canais.ErroCanal as exc:
            self.config.registrar_bot(ultima_verificacao=_agora(), ultimo_erro=str(exc))
            raise ValueError(str(exc)) from exc
        recebidos = 0
        for atualizacao in atualizacoes:
            self.config.registrar_bot(offset=int(atualizacao.get("update_id", 0)) + 1)
            conteudo = atualizacao.get("message") or atualizacao.get("channel_post") or {}
            chat = conteudo.get("chat") or {}
            if not chat:
                continue
            self.config.lembrar_chat(chat)
            chat_id = str(chat.get("id"))
            arquivo = self._arquivo_da_mensagem(conteudo)
            if not arquivo:
                self._responder_comando(token, chat_id, conteudo, cadastrados)
                continue
            if chat_id not in cadastrados:
                self._responder(token, chat_id, "Este bot só recebe notas fiscais de quem está cadastrado. "
                                                "Peça ao responsável para incluir você em Empresas → Bot de notas.")
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
            de = (conteudo.get("from") or {})
            remetente = " ".join(p for p in (de.get("first_name"), de.get("last_name")) if p)
            quem = cadastrados.get(chat_id) or remetente or chat_id
            item = self.receber(dados, nome, "telegram", remetente or chat_id, conteudo.get("caption") or "",
                                f"{quem} (Bot de notas)")
            self._responder(token, chat_id, self.mensagem_resposta(item))
            recebidos += 1 if item else 0
        self.config.registrar_bot(ultima_verificacao=_agora(), ultimo_erro=None)
        return {"recebidos": recebidos}

    def _responder_comando(self, token: str, chat_id: str, mensagem: dict, cadastrados: dict) -> None:
        texto = (mensagem.get("text") or "").strip()
        if not texto.startswith("/") or not self.comandos:
            return
        if chat_id not in cadastrados:
            self._responder(token, chat_id, "Olá! Este é o bot de notas fiscais do escritório. Peça ao responsável "
                                            "para incluir você em Empresas → Bot de notas.")
            return
        nome = (mensagem.get("from") or {}).get("first_name") or cadastrados.get(chat_id) or ""
        try:
            respostas = self.comandos.responder(texto, nome) or []
        except Exception:
            log.exception("Bot de notas: falha ao responder %s", texto[:30])
            respostas = ["Não consegui consultar agora. Tente de novo em instantes."]
        for resposta in respostas:
            self._responder(token, chat_id, resposta)

    # ------------------------------------------------------------------ envio do fechamento

    def enviar_fechamentos(self, hoje: date | None = None, forcar: bool = False) -> dict:
        """No dia do fechamento, manda o resumo de cada empresa para quem está cadastrado no bot."""
        hoje = hoje or date.today()
        dia = self.config.dia_fechamento
        competencia = servico.competencia_de(hoje, dia)
        if not forcar and hoje.day != dia:
            return {"enviados": 0, "motivo": "fora do dia do fechamento"}
        with self._lock:
            ja_enviado = self.config.publica().get("ultimo_fechamento")
        if not forcar and ja_enviado == competencia:
            return {"enviados": 0, "motivo": "já enviado"}
        token = self.config.token()
        destinatarios = self.config.destinatarios()
        if not token or not destinatarios:
            return {"enviados": 0, "motivo": "bot sem token ou sem destinatários"}
        mensagens = []
        for empresa in servico.empresas():
            if empresa.get("status") == "Inativa":
                continue
            f = servico.fechamento(empresa["nome"], servico.competencia_de(hoje, servico.dia_fechamento(empresa)), hoje)
            if not f["linhas"]:
                continue
            mensagens.append(resumo_telegram(f))
        if not mensagens:
            self.config.registrar_envio(competencia)
            return {"enviados": 0, "motivo": "nenhum fechamento com lançamentos"}
        cabecalho = f"📊 <b>Fechamento de {servico.titulo_competencia(competencia)}</b>\n"
        enviados = 0
        for destinatario in destinatarios:
            try:
                canais.enviar_telegram(token, destinatario["chat_id"], cabecalho + "\n\n".join(mensagens)[:3800])
                enviados += 1
            except canais.ErroCanal as exc:
                log.warning("Bot de notas: falha ao enviar o fechamento para %s: %s", destinatario["chat_id"], exc)
        self.config.registrar_envio(competencia)
        return {"enviados": enviados, "empresas": len(mensagens), "competencia": competencia}

    # ------------------------------------------------------------------ agendador

    def verificar_agora(self) -> dict:
        if not self._verificando.acquire(timeout=120):
            raise ValueError("Uma verificação já está em andamento. Tente de novo em instantes.")
        try:
            return self.verificar()
        finally:
            self._verificando.release()

    def iniciar_agendador(self, espera_inicial: float = 35) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()

        def laco():
            if self._parar.wait(espera_inicial):
                return
            while True:
                try:
                    if self.config.bot().get("ativo") and self.config.token():
                        self.verificar_agora()
                except ValueError as exc:
                    log.warning("Bot de notas: %s", exc)
                except Exception:
                    log.exception("Falha ao verificar o bot de notas")
                try:
                    agora = datetime.now()
                    if self.config.publica().get("fechamento_automatico") and agora.time() >= self.config.hora_envio:
                        self.enviar_fechamentos(agora.date())
                except Exception:
                    log.exception("Falha ao enviar os fechamentos")
                if self._parar.wait(INTERVALO):
                    return

        self._thread = threading.Thread(target=laco, name="bot-notas", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()

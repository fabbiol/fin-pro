"""Comandos do bot de notas fiscais: consultar fechamentos, saldos e cheques pelo celular.

/fechamento — fechamento da empresa (total, recebido e quanto falta)
/empresas   — todas as empresas com o que falta receber
/cheques    — cheques pré-datados a depositar
/notas      — notas em aberto de uma empresa
/ajuda      — lista dos comandos
"""

from __future__ import annotations

import html
import re
from datetime import date

from . import servico
from .relatorio import resumo_telegram

COMANDOS = [
    ("fechamento", "Fechamento da empresa (ex.: /fechamento imapal)"),
    ("empresas", "Todas as empresas e quanto falta receber"),
    ("cheques", "Cheques pré-datados a depositar"),
    ("notas", "Notas em aberto de uma empresa (ex.: /notas imapal)"),
    ("ajuda", "Lista dos comandos"),
]
LIMITE_MENSAGEM = 3800


def _moeda(valor) -> str:
    return servico.moeda(valor)


def _empresa_do_texto(argumento: str) -> dict | None:
    if not argumento:
        return None
    return servico.identificar_empresa(nome=argumento, texto=argumento)


def ajuda(nome: str = "") -> str:
    saudacao = f"Olá{', ' + html.escape(nome) if nome else ''}! " if nome is not None else ""
    return (f"{saudacao}Eu sou o bot de <b>notas fiscais e fechamentos</b>.\n\n"
            + "\n".join(f"/{c} — {d}" for c, d in COMANDOS)
            + "\n\nVocê pode me mandar:\n"
              "• a <b>nota fiscal</b> (XML, PDF ou foto) — eu lanço no fechamento da empresa;\n"
              "• o <b>cheque escaneado</b> com o número do pedido na legenda — eu guardo e aviso o vencimento;\n"
              "• o <b>comprovante</b> de Pix, TED ou depósito com o número das NFs — eu dou baixa sozinho.")


def _partir(linhas: list[str]) -> list[str]:
    mensagens, atual = [], ""
    for bloco in linhas:
        if len(atual) + len(bloco) + 2 > LIMITE_MENSAGEM:
            mensagens.append(atual)
            atual = ""
        atual += bloco + "\n"
    mensagens.append(atual or "Nada a mostrar.")
    return mensagens


def _linha_empresa(e: dict) -> str:
    marca = "🔴" if e["atrasado"] > 0.01 else "🟠" if e["em_aberto"] > 0.01 else "🟢"
    partes = [f"{marca} <b>{html.escape(e['nome'])}</b> — falta {_moeda(e['em_aberto'])}",
              f"Fechamento atual: {_moeda(e['fechamento']['total'])} ({e['fechamento']['quantidade']} lançamento(s))"]
    if e["atrasado"] > 0.01:
        partes.append(f"De fechamentos anteriores: {_moeda(e['atrasado'])}")
    if e["cheques"]["quantidade"]:
        partes.append(f"Cheques em carteira: {e['cheques']['quantidade']} · {_moeda(e['cheques']['valor'])}")
    return "\n".join(partes)


def responder(texto: str, nome: str = "", hoje: date | None = None) -> list[str] | None:
    """Resposta (HTML do Telegram) a uma mensagem de texto. None quando não é um comando."""
    hoje = hoje or date.today()
    m = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)$", (texto or "").strip(), re.S)
    if not m:
        return None
    comando, argumento = m.group(1).lower(), m.group(2).strip()
    comando = {"start": "ajuda", "help": "ajuda", "saldo": "empresas", "clientes": "empresas",
               "nf": "notas", "fechamentos": "fechamento"}.get(comando, comando)

    if comando == "ajuda":
        return [ajuda(nome)]

    if comando == "empresas":
        resumo = [e for e in servico.resumo_empresas(hoje) if e["status"] != "Inativa"]
        if not resumo:
            return ["Nenhuma empresa cadastrada ainda. Mande uma nota fiscal que eu cadastro a empresa sozinho."]
        total = sum(e["em_aberto"] for e in resumo)
        cabecalho = f"<b>Empresas</b> — falta receber {_moeda(total)}\n"
        return _partir([cabecalho] + [_linha_empresa(e) + "\n" for e in resumo])

    if comando == "fechamento":
        empresa = _empresa_do_texto(argumento)
        if not empresa:
            if argumento:
                return [f"Não encontrei a empresa “{html.escape(argumento)}”. Use /empresas para ver a lista."]
            resumo = [e for e in servico.resumo_empresas(hoje) if e["status"] != "Inativa"]
            return _partir(["<b>Fechamentos em andamento</b>\n"] +
                           [f"• <b>{html.escape(e['nome'])}</b> — {_moeda(e['fechamento']['total'])} "
                            f"(falta {_moeda(e['fechamento']['falta'])})" for e in resumo] +
                           ["\nUse /fechamento <nome da empresa> para ver as notas."])
        f = servico.fechamento(empresa["nome"], hoje=hoje)
        linhas = [resumo_telegram(f), ""]
        for item in f["linhas"][:30]:
            data = item.get("data")
            linhas.append(f"{data:%d/%m} · {html.escape(str(item.get('material') or ''))} · "
                          f"{_moeda(item.get('valor_total'))} · NF {item.get('numero_nf') or '—'}")
        if len(f["linhas"]) > 30:
            linhas.append(f"… e mais {len(f['linhas']) - 30} lançamento(s).")
        return _partir(linhas)

    if comando == "cheques":
        lista = servico.cheques(status="Em carteira")
        if not lista:
            return ["Nenhum cheque em carteira. 🎉"]
        total = sum(float(c.get("valor") or 0) for c in lista)
        linhas = [f"<b>Cheques a depositar</b> — {len(lista)} cheque(s), {_moeda(total)}\n"]
        for c in lista:
            vencimento = c.get("vencimento")
            quando = f"{vencimento:%d/%m/%Y}" if isinstance(vencimento, date) else "sem data"
            atraso = " ⚠️ passou da data" if isinstance(vencimento, date) and vencimento < hoje else ""
            linhas.append(f"🧾 <b>{html.escape(c.get('empresa') or '')}</b> — {_moeda(c.get('valor'))}\n"
                          f"Cheque {c.get('numero') or '—'} · {html.escape(c.get('banco') or '')} · bom para {quando}{atraso}\n")
        return _partir(linhas)

    if comando == "notas":
        empresa = _empresa_do_texto(argumento)
        if not empresa:
            return ["Diga a empresa. Exemplo: /notas imapal"]
        abertas = [n for n in servico.notas_da_empresa(empresa["nome"], somente_abertas=True)]
        if not abertas:
            return [f"<b>{html.escape(empresa['nome'])}</b> está sem notas em aberto. ✅"]
        total = sum(float(n.get("valor_total") or 0) - float(n.get("valor_recebido") or 0) for n in abertas)
        linhas = [f"<b>Notas em aberto · {html.escape(empresa['nome'])}</b> — {_moeda(total)}\n"]
        for n in abertas[:40]:
            data = n.get("data")
            situacao = {"Em cheque": " · em cheque", "Parcial": " · parcial"}.get(n.get("status"), "")
            linhas.append(f"{data:%d/%m} · NF {n.get('numero_nf') or '—'} · {html.escape(str(n.get('material') or ''))} · "
                          f"{_moeda(float(n.get('valor_total') or 0) - float(n.get('valor_recebido') or 0))}{situacao}")
        return _partir(linhas)

    return [f"Não conheço o comando /{html.escape(comando)}.\n\n" + ajuda(None)]

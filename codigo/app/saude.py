"""Saúde do sistema: um diagnóstico de tudo o que roda sozinho (e do que precisa de atenção).

Cada item tem ``situacao`` — ``ok``, ``aviso``, ``erro`` ou ``desligado`` — e um resumo em linguagem simples.
"""

from __future__ import annotations

import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import __version__, config, ia, registro_log
from . import contexto as ctx
from .boleto.leitores import motor_ocr

INICIADO_EM = datetime.now()
ORDEM = {"erro": 0, "aviso": 1, "ok": 2, "desligado": 3}
NOMES_CANAIS = {"windows": "Windows", "telegram": "Telegram", "email": "e-mail"}


def _vivo(objeto) -> bool:
    thread = getattr(objeto, "_thread", None)
    return bool(thread and thread.is_alive())


def _tamanho(caminho: Path) -> int:
    caminho = Path(caminho)
    if caminho.is_file():
        return caminho.stat().st_size
    if not caminho.is_dir():
        return 0
    return sum(p.stat().st_size for p in caminho.rglob("*") if p.is_file())


def _item(chave: str, titulo: str, situacao: str, resumo: str, **detalhes) -> dict:
    return {"chave": chave, "titulo": titulo, "situacao": situacao, "resumo": resumo, "detalhes": detalhes}


def _data_hora(texto) -> str:
    try:
        return datetime.fromisoformat(str(texto)).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return "—"


def _banco() -> dict:
    planilha = ctx.planilha
    if not hasattr(planilha, "status"):
        return _item("banco", "Banco de dados e planilha", "aviso", "Usando a planilha como banco de dados (modo antigo).")
    s = planilha.status()
    if s["erro"]:
        return _item("banco", "Banco de dados e planilha", "erro", f"A planilha Excel não pôde ser gerada: {s['erro']}", **s)
    if s["excel_aberto"]:
        return _item("banco", "Banco de dados e planilha", "aviso",
                     "A planilha está aberta no Excel: os dados estão salvos no banco e a planilha será atualizada quando for fechada.", **s)
    resumo = f"{s['boletos']} boletos, {s['pix']} Pix e {s['historico']} registros de histórico."
    if s["ultima"]:
        resumo += f" Planilha Excel atualizada em {_data_hora(s['ultima'])}."
    return _item("banco", "Banco de dados e planilha", "ok", resumo, **s)


def _empresas() -> dict:
    """Banco das empresas (notas, cheques e recebimentos) e o bot de notas fiscais."""
    banco = ctx.empresas
    caixa = ctx.empresas_entrada
    s = banco.status()
    bot = ctx.empresas_config.publica()["bot"]
    detalhes = {**s, "bot_ativo": bool(bot.get("ativo")), "destinatarios": len(bot.get("destinatarios") or []),
                "pendentes": caixa.contagem() if caixa else 0, "agendador": _vivo(caixa) if caixa else False,
                "ultima_verificacao": bot.get("ultima_verificacao")}
    contagem = (f"{s.get('empresas', 0)} empresa(s), {s.get('notas', 0)} linha(s) de nota fiscal, "
                f"{s.get('cheques', 0)} cheque(s) e {s.get('recebimentos', 0)} recebimento(s).")
    if s["erro"]:
        return _item("empresas", "Empresas e fechamentos", "erro", f"A planilha de fechamentos não pôde ser gerada: {s['erro']}",
                     **detalhes)
    if bot.get("ativo") and bot.get("ultimo_erro"):
        return _item("empresas", "Empresas e fechamentos", "erro", f"Bot de notas: {bot['ultimo_erro']}", **detalhes)
    if bot.get("ativo") and config.NOTIFICACOES_AUTOMATICAS and caixa and not _vivo(caixa):
        return _item("empresas", "Empresas e fechamentos", "erro",
                     "A verificação automática do bot de notas parou. Reinicie o sistema.", **detalhes)
    pendentes = f" {detalhes['pendentes']} arquivo(s) aguardando conferência." if detalhes["pendentes"] else ""
    if not bot.get("ativo"):
        return _item("empresas", "Empresas e fechamentos", "desligado",
                     f"Bot de notas desligado. {contagem}{pendentes}", **detalhes)
    if not detalhes["destinatarios"]:
        return _item("empresas", "Empresas e fechamentos", "aviso",
                     f"Bot de notas ligado, mas sem ninguém cadastrado para enviar arquivos. {contagem}", **detalhes)
    return _item("empresas", "Empresas e fechamentos", "ok",
                 f"Bot de notas recebendo de {detalhes['destinatarios']} pessoa(s)/grupo(s). {contagem}{pendentes}", **detalhes)


def _caixa() -> dict:
    """Bot do caixa: cupons de gastos em dinheiro."""
    bot = ctx.caixa_bot
    if bot is None:
        return _item("caixa", "Bot do caixa", "desligado", "Indisponível.")
    cfg = bot.config_publica()
    detalhes = {"ativo": bool(cfg.get("ativo")), "pessoas": len(cfg.get("pessoas") or []), "pendentes": bot.contagem(),
                "agendador": _vivo(bot), "ultima_verificacao": cfg.get("ultima_verificacao")}
    pendentes = f" {detalhes['pendentes']} comprovante(s) esperando revisão." if detalhes["pendentes"] else ""
    if not cfg.get("ativo"):
        return _item("caixa", "Bot do caixa", "desligado", f"Bot do caixa desligado.{pendentes}", **detalhes)
    if cfg.get("ultimo_erro"):
        return _item("caixa", "Bot do caixa", "erro", f"Bot do caixa: {cfg['ultimo_erro']}", **detalhes)
    if config.NOTIFICACOES_AUTOMATICAS and not _vivo(bot):
        return _item("caixa", "Bot do caixa", "erro", "A verificação automática do bot do caixa parou. Reinicie o sistema.",
                     **detalhes)
    if not detalhes["pessoas"]:
        return _item("caixa", "Bot do caixa", "aviso", "Ninguém pode usar ainda: cadastre as pessoas no bot dos boletos "
                                                       "ou no bot de notas.", **detalhes)
    return _item("caixa", "Bot do caixa", "ok", f"Recebendo de {detalhes['pessoas']} pessoa(s)/grupo(s).{pendentes}",
                 **detalhes)


def _diesel() -> dict:
    """Bot do diesel: canhotos dos abastecimentos e comprovantes das compras."""
    bot = ctx.diesel_bot
    if bot is None:
        return _item("diesel", "Bot do diesel", "desligado", "Indisponível.")
    cfg = bot.config_publica()
    detalhes = {"ativo": bool(cfg.get("ativo")), "responsaveis": len(bot.gestores()), "pendentes": bot.contagem(),
                "agendador": _vivo(bot), "ultima_verificacao": cfg.get("ultima_verificacao")}
    pendentes = f" {detalhes['pendentes']} canhoto(s) esperando a máquina." if detalhes["pendentes"] else ""
    if not cfg.get("ativo"):
        return _item("diesel", "Bot do diesel", "desligado", f"Bot do diesel desligado.{pendentes}", **detalhes)
    if cfg.get("ultimo_erro"):
        return _item("diesel", "Bot do diesel", "erro", f"Bot do diesel: {cfg['ultimo_erro']}", **detalhes)
    if config.NOTIFICACOES_AUTOMATICAS and not _vivo(bot):
        return _item("diesel", "Bot do diesel", "erro", "A verificação automática do bot do diesel parou. Reinicie o sistema.",
                     **detalhes)
    if not detalhes["responsaveis"]:
        return _item("diesel", "Bot do diesel", "aviso", "Ninguém escolhido para decidir a máquina dos canhotos: "
                                                          "quem manda o canhoto decide.", **detalhes)
    return _item("diesel", "Bot do diesel", "ok", f"Funcionando.{pendentes}", **detalhes)


def _notificacoes() -> dict:
    servico = ctx.notificacoes
    config_publica = servico.config_publica()
    historico = servico.historico(1)
    ultimo = historico[0] if historico else None
    canais = [nome for nome in ("windows", "telegram", "email") if config_publica[nome].get("ativo")]
    detalhes = {"canais": canais, "agendador": _vivo(servico), "ultimo": ultimo}
    if not config_publica["ativo"] or not canais:
        return _item("notificacoes", "Lembretes de vencimento", "desligado", "Os lembretes estão desligados.", **detalhes)
    if config.NOTIFICACOES_AUTOMATICAS and not _vivo(servico):
        return _item("notificacoes", "Lembretes de vencimento", "erro", "O envio automático de lembretes parou. Reinicie o sistema.", **detalhes)
    if ultimo and any(str(r).startswith("erro") for r in (ultimo.get("canais") or {}).values()):
        falhas = ", ".join(f"{c}: {r.removeprefix('erro: ')}" for c, r in ultimo["canais"].items() if str(r).startswith("erro"))
        return _item("notificacoes", "Lembretes de vencimento", "aviso", f"No último envio ({_data_hora(ultimo['quando'])}) houve falha — {falhas}", **detalhes)
    resumo = f"Ativos por {', '.join(NOMES_CANAIS.get(c, c) for c in canais)}."
    if ultimo:
        resumo += f" Último envio: {_data_hora(ultimo['quando'])}."
    return _item("notificacoes", "Lembretes de vencimento", "ok", resumo, **detalhes)


def _backup() -> dict:
    s = ctx.backup.status()
    textos = {
        "desligado": ("desligado", "O backup fora do computador está desligado. Recomendado ligar (aba Backup e recebimento)."),
        "aguardando": ("aviso", "Backup ligado, aguardando a primeira cópia."),
        "atrasado": ("erro", f"Backup atrasado: {s.get('dias_sem_backup') or 'vários'} dia(s) sem cópia."),
        "erro": ("erro", f"O último backup falhou: {(s.get('ultimo') or {}).get('erro') or 'erro desconhecido'}"),
        "ok": ("ok", f"Último backup em {_data_hora(s.get('ultimo_sucesso'))}."),
    }
    situacao, resumo = textos.get(s["situacao"], ("aviso", s["situacao"]))
    if situacao == "ok":
        ultimo = s.get("ultimo") or {}
        partes = ["dados e comprovantes"] + (["código-fonte"] if s.get("com_codigo") else []) + (
            ["histórico de versões"] if ultimo.get("historico_de_versoes") else [])
        resumo += f" Leva {', '.join(partes)}" + (f" ({ultimo['tamanho_legivel']})." if ultimo.get("tamanho_legivel") else ".")
        if s.get("verificado") is False:  # copiou, mas a conferência achou problema
            problemas = "; ".join(f"{p['nome']}: {p['detalhe']}" for p in s.get("problemas") or [])
            situacao, resumo = "erro", f"O backup foi feito, mas não passou na conferência — {problemas}"
        elif not s.get("com_codigo"):
            situacao, resumo = "aviso", resumo + " O código-fonte não está incluído (ligue em Backup e recebimento)."
    return _item("backup", "Backup total fora do computador", situacao, resumo, agendador=_vivo(ctx.backup),
                 pasta=s.get("destino"), ultimo=s.get("ultimo"), verificacao=s.get("verificacao"),
                 ultimo_pacote=s.get("ultimo_pacote"))


def _entrada() -> dict:
    caixa = ctx.caixa_entrada
    if caixa is None:
        return _item("entrada", "Recebimento por e-mail e Telegram", "desligado", "Indisponível.")
    cfg = caixa.config_publica()
    ativos = [nome for nome in ("email", "telegram") if cfg[nome]["ativo"]]
    detalhes = {"email": cfg["email"], "telegram": cfg["telegram"], "pendentes": caixa.contagem(), "agendador": _vivo(caixa)}
    detalhes["email"] = {k: v for k, v in cfg["email"].items() if k != "senha"}
    if not ativos:
        return _item("entrada", "Recebimento por e-mail e Telegram", "desligado", "Nenhum canal de recebimento ligado.", **detalhes)
    erros = [f"{nome}: {cfg[nome]['ultimo_erro']}" for nome in ativos if cfg[nome].get("ultimo_erro")]
    if erros:
        return _item("entrada", "Recebimento por e-mail e Telegram", "erro", " · ".join(erros), **detalhes)
    if config.NOTIFICACOES_AUTOMATICAS and not _vivo(caixa):
        return _item("entrada", "Recebimento por e-mail e Telegram", "erro", "A verificação automática parou. Reinicie o sistema.", **detalhes)
    atrasados = []
    for nome in ativos:
        ultima = cfg[nome].get("ultima_verificacao")
        limite = timedelta(minutes=20 if nome == "email" else 10)
        if not ultima or datetime.now() - datetime.fromisoformat(ultima) > limite:
            atrasados.append(nome)
    pendentes = f" {detalhes['pendentes']} arquivo(s) aguardando conferência." if detalhes["pendentes"] else ""
    if atrasados and time.time() - INICIADO_EM.timestamp() > 600:
        return _item("entrada", "Recebimento por e-mail e Telegram", "aviso",
                     f"Sem verificação recente em: {', '.join(atrasados)}.{pendentes}", **detalhes)
    return _item("entrada", "Recebimento por e-mail e Telegram", "ok",
                 f"Recebendo por {', '.join(NOMES_CANAIS.get(c, c) for c in ativos)}.{pendentes}", **detalhes)


def _fila() -> dict:
    s = ctx.fila.status()
    if s["pendentes"]:
        return _item("fila", "Gravações pendentes", "aviso", f"{s['pendentes']} alteração(ões) aguardando gravação.", **s)
    return _item("fila", "Gravações pendentes", "ok", "Nenhuma alteração pendente.", pendentes=0)


def _leitura() -> dict:
    ocr = motor_ocr.disponivel
    ia_ok = ia.disponivel()
    resumo = f"OCR {'ativo' if ocr else 'indisponível'}{f' ({motor_ocr.modelo})' if ocr and motor_ocr.modelo else ''} · IA {'ativa' if ia_ok else 'desativada'}."
    return _item("leitura", "Leitura de boletos", "ok" if ocr else "aviso", resumo, ocr=ocr, ia=ia_ok)


def _disco() -> dict:
    uso = shutil.disk_usage(config.DADOS_DIR)
    livre_gb = uso.free / 1024 ** 3
    tamanhos = {"arquivos": _tamanho(config.ARQUIVOS_DIR), "backups": _tamanho(config.BACKUPS_DIR),
                "logs": sum(p.stat().st_size for p in registro_log.arquivos_de_log(config.DADOS_DIR / "leitor.log")),
                "total": _tamanho(config.DADOS_DIR)}
    situacao = "erro" if livre_gb < 1 else "aviso" if livre_gb < 5 else "ok"
    resumo = (f"{livre_gb:.1f} GB livres no disco. Pasta de dados: {tamanhos['total'] / 1024 ** 2:.1f} MB "
              f"(arquivos {tamanhos['arquivos'] / 1024 ** 2:.1f} MB, logs {tamanhos['logs'] / 1024 ** 2:.1f} MB).")
    return _item("disco", "Espaço em disco e logs", situacao, resumo, livre=uso.free, **tamanhos)


def _rede() -> dict:
    if ctx.rede is None:
        return _item("rede", "Acesso pelo celular", "desligado", "Indisponível.")
    s = ctx.rede.status()
    if not s["ativo"]:
        return _item("rede", "Acesso pelo celular", "desligado", "Acesso pela rede desligado.", **s)
    if s.get("erro"):
        return _item("rede", "Acesso pelo celular", "erro", s["erro"], **s)
    return _item("rede", "Acesso pelo celular", "ok", f"Liberado em {', '.join(s['urls'][:2])}.", enderecos=s["urls"])


def diagnostico() -> dict:
    itens = []
    for verificar in (_banco, _empresas, _caixa, _diesel, _notificacoes, _backup, _entrada, _fila, _leitura, _disco, _rede):
        try:
            itens.append(verificar())
        except Exception as exc:  # um diagnóstico com problema não pode derrubar a tela inteira
            itens.append(_item(verificar.__name__.strip("_"), verificar.__name__.strip("_").capitalize(), "erro",
                               f"Não foi possível verificar: {exc}"))
    piores = [i["situacao"] for i in itens if i["situacao"] in ("erro", "aviso")]
    geral = "erro" if "erro" in piores else "aviso" if piores else "ok"
    segundos = int((datetime.now() - INICIADO_EM).total_seconds())
    return {
        "situacao": geral,
        "versao": __version__,
        "iniciado_em": INICIADO_EM.isoformat(timespec="seconds"),
        "em_execucao_ha": f"{segundos // 86400}d {segundos % 86400 // 3600}h {segundos % 3600 // 60}min",
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        "itens": sorted(itens, key=lambda i: ORDEM.get(i["situacao"], 9)),
    }

"""Transferências de clientes: recebe a nota mandada pela Operações, lista para a tela e liga o pagamento à nota.

* Cada nota vem com o número da ordem na Operações (``origem_id``). Se a mesma ordem chegar de novo (reenvio, nota
  corrigida), a linha existente é **atualizada** — nunca duplica, e a situação e o pagamento não mudam.
* Toda nota nova entra como **Aguardando pagamento**. Vira **Pago** quando alguém liga um comprovante (Pix/TED) a ela,
  ou confirma um Pix recebido no Bradesco (API Pix): um pagamento pode cobrir várias notas e juntar vários Pix.
  Desfazer o pagamento volta as notas; o pagamento fica guardado como desfeito.
* O mesmo Pix (endToEndId) ou o mesmo comprovante (ID da transação) nunca paga duas vezes.
* Nota mandada por engano pode ser excluída enquanto aguarda pagamento (fica no Histórico). Se a Operações mandar a
  mesma ordem de novo, ela volta como nota nova.
* A conciliação com o Bradesco só **sugere**: nada vira Pago sem alguém confirmar.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from datetime import date, datetime, timedelta
from itertools import combinations

from .. import comprovante
from .. import contexto as ctx
from ..arquivos import RepositorioArquivos
from ..boleto.extrator import ler_arquivo
from . import bradesco
from .modelos import AGUARDANDO, ATIVO, DESFEITO, FORMAS, ORIGEM_COMPROVANTE, ORIGEM_PIX, PAGO, STATUS_TRANSFERENCIA

MAX_PDF = 10 * 1024 * 1024
USUARIO = "Operações"  # quem aparece como "Enviada por" e no Histórico
_lock = threading.Lock()  # a mesma ordem chegando duas vezes, ou dois cliques em "Ligar", não viram duas linhas


class ErroTransferencia(ValueError):
    """Dado recebido inválido (mensagem já pronta para devolver à Operações ou à tela)."""


class ErroPagamento(ValueError):
    """Não deu para fazer o que a tela pediu (ligar, desfazer, excluir): ``status`` e ``codigo`` vão na resposta."""

    def __init__(self, status: int, codigo: str, mensagem: str):
        super().__init__(mensagem)
        self.status, self.codigo = status, codigo


def _texto(campos, nome: str, limite: int, obrigatorio: bool = False) -> str:
    valor = re.sub(r"\s+", " ", str(campos.get(nome) or "")).strip()
    if obrigatorio and not valor:
        raise ErroTransferencia(f"Campo obrigatório: {nome}.")
    if len(valor) > limite:
        raise ErroTransferencia(f"O campo {nome} passa de {limite} caracteres.")
    return valor


def documento(valor, campo: str = "documento") -> str:
    """CPF ou CNPJ sem a pontuação (aceita com pontuação). Vazio é aceito.
    Desde jul/2026 o CNPJ pode ter letras nas 12 primeiras posições (12.ABC.345/01DE-35)."""
    texto = str(valor or "").strip().upper()
    limpo = re.sub(r"[.\-/\s]", "", texto)
    if texto and not re.fullmatch(r"\d{11}|[0-9A-Z]{12}\d{2}", limpo):
        raise ErroTransferencia(f"{campo} deve ser um CPF (11 dígitos) ou CNPJ (14 caracteres).")
    return limpo


def validar(campos) -> dict:
    """Confere os campos do formulário da Operações e devolve os dados prontos para gravar."""
    origem = str(campos.get("origem_id") or "").strip()
    if not re.fullmatch(r"\d{1,15}", origem) or int(origem) <= 0:
        raise ErroTransferencia("origem_id deve ser um número inteiro positivo.")
    forma = str(campos.get("forma") or "").strip()
    if forma not in FORMAS:
        raise ErroTransferencia("forma deve ser pix ou transferencia.")
    valor = str(campos.get("valor") or "").strip()
    if valor and not re.fullmatch(r"\d{1,12}(\.\d{1,4})?", valor):
        raise ErroTransferencia("valor deve ser um número com ponto decimal, ex.: 1234.56.")
    emitida = str(campos.get("emitida_em") or "").strip()
    if emitida:
        formato = "%Y-%m-%d %H:%M:%S" if len(emitida) > 10 else "%Y-%m-%d"
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?", emitida):
                raise ValueError
            datetime.strptime(emitida, formato)
        except ValueError:
            raise ErroTransferencia("emitida_em deve ser AAAA-MM-DD ou AAAA-MM-DD HH:MM:SS.") from None
    chave = re.sub(r"\s", "", str(campos.get("chave") or ""))
    if chave and not re.fullmatch(r"\d{44}", chave):
        raise ErroTransferencia("chave deve ter 44 dígitos.")
    return {"origem_id": int(origem), "nota": _texto(campos, "nota", 30, True), "pedido": _texto(campos, "pedido", 30),
            "empresa": _texto(campos, "empresa", 120, True), "documento": documento(campos.get("documento")),
            "valor": float(valor) if valor else None, "material": _texto(campos, "material", 120), "emitida_em": emitida,
            "forma": forma, "chave": chave}


def validar_pdf(conteudo: bytes) -> None:
    if len(conteudo) > MAX_PDF:
        raise ErroTransferencia("O PDF passa de 10 MB.")
    if not conteudo.startswith(b"%PDF"):
        raise ErroTransferencia("O arquivo deve ser um PDF.")


def receber(dados: dict, pdf: bytes | None = None, nome_pdf: str = "") -> tuple[dict, bool]:
    """Cria a linha ou, se essa ordem da Operações já chegou antes, atualiza os dados (e o PDF, se veio outro).

    Devolve ``(registro, criada)``. A situação (Aguardando pagamento / Pago) e o pagamento não mudam num reenvio.
    """
    banco = ctx.transferencias
    with _lock:
        existente = next((r for r in banco.listar() if r.get("origem_id") == dados["origem_id"]), None)
        anterior = None
        if pdf is not None:
            meta = ctx.arquivos.salvar(pdf, nome_pdf or f"NF {dados['nota']}.pdf")
            dados = {**dados, "arquivo": ctx.arquivos.caminho_relativo(meta["id"]), "arquivo_nome": meta["nome"]}
            anterior = RepositorioArquivos.id_de_caminho((existente or {}).get("arquivo"))
        if existente is None:
            registro = banco.adicionar({**dados, "status": AGUARDANDO}, usuario=USUARIO)
        else:
            registro = banco.atualizar(existente["id"], dados, usuario=USUARIO)
        if anterior:
            ctx.arquivos.remover(anterior)  # o PDF trocado não fica perdido na pasta de arquivos
    return registro, existente is None


def excluir(id_: int, usuario: str) -> dict:
    """Exclui a nota que aguarda pagamento e devolve como ela era. Nota paga não sai: desfaça o pagamento antes.
    O PDF da nota fica até a limpeza automática dos arquivos sem uso, como nas outras telas."""
    banco = ctx.transferencias
    with _lock:
        nota = next((r for r in banco.listar() if r["id"] == id_), None)
        if nota is None:
            raise ErroPagamento(404, "nota_nao_encontrada", "Nota não encontrada. Atualize a tela e tente de novo.")
        if nota.get("status") != AGUARDANDO or nota.get("pagamento_id"):
            raise ErroPagamento(409, "nota_paga", f"A nota {nota['nota']} está paga. Desfaça o pagamento antes de excluir.")
        banco.excluir(id_, usuario=usuario)
    return nota


def _normalizar(texto) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().casefold()


def _publico(pagamento: dict, notas: list[str]) -> dict:
    """O pagamento como a tela recebe."""
    data_pagamento = pagamento.get("data_pagamento")
    ligado_em = pagamento.get("data_lancamento")
    return {"id": pagamento["id"], "valor": pagamento.get("valor"),
            "data": data_pagamento.isoformat() if isinstance(data_pagamento, date) else data_pagamento,
            "pagador": pagamento.get("pagador") or "", "documento_pagador": pagamento.get("documento_pagador") or "",
            "id_transacao": pagamento.get("id_transacao") or "", "observacao": pagamento.get("observacao") or "",
            "origem": pagamento.get("origem") or ORIGEM_COMPROVANTE,
            "notas": notas, "comprovante": bool(pagamento.get("comprovante")), "ligado_por": pagamento.get("lancado_por") or "",
            "ligado_em": ligado_em.isoformat() if isinstance(ligado_em, datetime) else ligado_em,
            "desfeito": pagamento.get("status") == DESFEITO}


def listar(empresa: str = "", situacao: str = "", busca: str = "") -> dict:
    """Linhas da tela, das mais novas para as mais antigas, com os filtros de empresa, situação e busca pela nota."""
    todas = ctx.transferencias.listar()
    notas_por_pagamento: dict[int, list[str]] = {}
    for r in todas:
        if r.get("pagamento_id"):
            notas_por_pagamento.setdefault(r["pagamento_id"], []).append(r["nota"])
    pagamentos = {p["id"]: _publico(p, notas_por_pagamento.get(p["id"], []))
                  for p in ctx.transferencias.listar("pagamentos") if p["id"] in notas_por_pagamento}
    linhas = [{**r, "pagamento": pagamentos.get(r.get("pagamento_id"))} for r in todas]
    if empresa:
        linhas = [r for r in linhas if _normalizar(r.get("empresa")) == _normalizar(empresa)]
    if situacao:
        linhas = [r for r in linhas if r.get("status") == situacao]
    if busca.strip():
        linhas = [r for r in linhas if _normalizar(busca) in _normalizar(r.get("nota"))]
    linhas.sort(key=lambda r: (r.get("emitida_em") or "", r["id"]), reverse=True)
    return {"transferencias": linhas, "total": len(linhas), "valor": round(sum(r.get("valor") or 0 for r in linhas), 2),
            "empresas": sorted({r["empresa"] for r in todas if r.get("empresa")}, key=_normalizar),
            "situacoes": list(STATUS_TRANSFERENCIA), "formas": FORMAS}


# --------------------------------------------------------------------------- ligar o pagamento à nota


def _chave_id(texto) -> str:
    return re.sub(r"\s", "", str(texto or "")).casefold()


def _ids(id_transacao) -> set[str]:
    """IDs de um pagamento (com vários Pix, os endToEndId vêm separados por vírgula), sem espaço nem maiúscula."""
    return {_chave_id(parte) for parte in str(id_transacao or "").split(",")} - {""}


def pagamento_com_id(id_transacao: str) -> dict | None:
    """Pagamento ativo que já usa algum desses IDs (o mesmo comprovante ou o mesmo Pix não paga duas vezes)."""
    procurados = _ids(id_transacao)
    if not procurados:
        return None
    return next((p for p in ctx.transferencias.listar("pagamentos")
                 if p.get("status") == ATIVO and procurados & _ids(p.get("id_transacao"))), None)


def ler_comprovante(dados: bytes) -> dict:
    """O que deu para ler do comprovante (para o dono conferir). Campos não lidos vêm ``None``."""
    try:
        texto = ler_arquivo(dados, max_paginas=3).get("texto") or ""
    except Exception:
        texto = ""  # PDF protegido ou foto ilegível: o dono preenche à mão
    extraido = comprovante.extrair(texto)
    data_pagamento = extraido.get("data_pagamento")
    return {"valor": extraido.get("valor_pago"), "data": data_pagamento.isoformat() if data_pagamento else None,
            **comprovante.pagador(texto)}


def _valores(entrada: dict) -> dict:
    """Confere o que o dono confirmou na tela."""
    try:
        valor = round(float(entrada.get("valor")), 2)
    except (TypeError, ValueError):
        valor = 0
    if valor <= 0:
        raise ErroPagamento(422, "valor_invalido", "Informe o valor pago.")
    try:
        data_pagamento = date.fromisoformat(str(entrada.get("data") or ""))
    except ValueError:
        raise ErroPagamento(422, "data_invalida", "Informe a data do pagamento.") from None
    try:
        documento_pagador = documento(entrada.get("documento_pagador"), "O CNPJ/CPF do pagador")
    except ErroTransferencia as exc:
        raise ErroPagamento(422, "documento_invalido", str(exc)) from None
    textos = {}
    for campo, limite in (("pagador", 120), ("id_transacao", 80), ("observacao", 300)):
        textos[campo] = re.sub(r"\s+", " ", str(entrada.get(campo) or "")).strip()[:limite]
    return {"valor": valor, "data_pagamento": data_pagamento, "documento_pagador": documento_pagador, **textos}


def ligar(ids: list[int], arquivo_id: str, entrada: dict, usuario: str) -> tuple[dict, list[dict]]:
    """Liga o comprovante enviado à mão às notas. Devolve ``(pagamento, notas)``."""
    valores = _valores(entrada)
    meta = ctx.arquivos.meta(arquivo_id)
    if not meta:
        raise ErroPagamento(404, "arquivo_nao_encontrado", "O arquivo do comprovante não está mais disponível. Envie-o de novo.")
    return _gravar(ids, {**valores, "origem": ORIGEM_COMPROVANTE, "comprovante": ctx.arquivos.caminho_relativo(arquivo_id),
                         "comprovante_nome": meta["nome"]}, usuario)


def _gravar(ids: list[int], dados: dict, usuario: str) -> tuple[dict, list[dict]]:
    """Grava o pagamento e passa as notas para Pago, tudo de uma vez. Devolve ``(pagamento, notas)``."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise ErroPagamento(422, "sem_notas", "Marque pelo menos uma nota.")
    banco = ctx.transferencias
    with _lock:
        por_id = {r["id"]: r for r in banco.listar()}
        faltando = [i for i in ids if i not in por_id]
        if faltando:
            raise ErroPagamento(404, "nota_nao_encontrada", "Nota não encontrada. Atualize a tela e tente de novo.")
        pagas = [por_id[i]["nota"] for i in ids if por_id[i].get("status") != AGUARDANDO]
        if pagas:
            raise ErroPagamento(409, "nota_ja_paga", f"A nota {', '.join(pagas)} já está paga.")
        repetido = pagamento_com_id(dados["id_transacao"])
        if repetido:
            o_que = "Este Pix (mesmo endToEndId)" if dados["origem"] == ORIGEM_PIX else "Este comprovante (mesmo ID da transação)"
            raise ErroPagamento(409, "comprovante_repetido", f"{o_que} já foi ligado no pagamento nº {repetido['id']}.")
        notas = [por_id[i]["nota"] for i in ids]
        # mesmo cálculo do banco para o próximo número; o _lock garante que ninguém grava no meio
        proximo = max((p["id"] for p in banco.listar("pagamentos")), default=0) + 1
        resultados = banco.aplicar_lote(
            [{"tipo": "adicionar", "aba": "pagamentos", "usuario": usuario,
              "dados": {**dados, "notas": ", ".join(notas), "status": ATIVO}}]
            + [{"tipo": "atualizar", "id": i, "usuario": usuario, "dados": {"status": PAGO, "pagamento_id": proximo}}
               for i in ids])
    return _publico(resultados[0]["registro"], notas), [r["registro"] for r in resultados[1:]]


def desfazer(pagamento_id: int, usuario: str) -> tuple[dict, list[dict]]:
    """As notas do pagamento voltam a Aguardando pagamento; o pagamento (e o comprovante) fica guardado como desfeito."""
    banco = ctx.transferencias
    with _lock:
        pagamento = next((p for p in banco.listar("pagamentos") if p["id"] == pagamento_id), None)
        if pagamento is None:
            raise ErroPagamento(404, "pagamento_nao_encontrado", "Pagamento não encontrado.")
        if pagamento.get("status") == DESFEITO:
            raise ErroPagamento(409, "pagamento_ja_desfeito", "Este pagamento já foi desfeito.")
        notas = [r for r in banco.listar() if r.get("pagamento_id") == pagamento_id]
        resultados = banco.aplicar_lote(
            [{"tipo": "atualizar", "aba": "pagamentos", "id": pagamento_id, "usuario": usuario,
              "dados": {"status": DESFEITO, "desfeito_por": usuario,
                        "desfeito_em": datetime.now().isoformat(sep=" ", timespec="minutes")}}]
            + [{"tipo": "atualizar", "id": r["id"], "usuario": usuario, "dados": {"status": AGUARDANDO, "pagamento_id": None}}
               for r in notas])
    return _publico(resultados[0]["registro"], [r["nota"] for r in notas]), [r["registro"] for r in resultados[1:]]


def comprovante_do_pagamento(pagamento_id: int) -> str | None:
    """Id do arquivo do comprovante (também de pagamento desfeito, que fica no histórico)."""
    pagamento = next((p for p in ctx.transferencias.listar("pagamentos") if p["id"] == pagamento_id), None)
    return RepositorioArquivos.id_de_caminho((pagamento or {}).get("comprovante"))


# --------------------------------------------------------------------------- Pix recebidos no Bradesco (API Pix)

DIAS_CONSULTA = 7  # período padrão: os últimos 7 dias, como no projeto de referência
MAX_DIAS_CONSULTA = 31
PERIODO_SANDBOX = (date(2024, 10, 2), date(2024, 10, 3))  # dias com Pix de exemplo no sandbox do Bradesco
MAX_COMBINACAO = 6  # até 6 notas (ou 6 Pix) somadas para fechar um valor
MAX_ITENS_COMBINACAO = 15  # com mais itens em aberto do mesmo pagador, só o valor igual e a soma de tudo são tentados
_consulta: dict | None = None  # última consulta ao banco: confirmar só aceita Pix que o próprio servidor consultou


def _centavos(valor) -> int:
    return round((valor or 0) * 100)


def _liquido(pix: dict) -> float:
    """O que ficou do Pix depois das devoluções ao pagador."""
    return round(pix["valor"] - (pix.get("devolvido") or 0), 2)


def _nota_publica(r: dict) -> dict:
    return {"id": r["id"], "nota": r.get("nota") or "", "empresa": r.get("empresa") or "", "documento": r.get("documento") or "",
            "valor": r.get("valor"), "emitida_em": r.get("emitida_em") or "", "forma": r.get("forma") or ""}


def _combinacoes(itens: list[dict], alvo: int, valor) -> list[tuple]:
    """Grupos de 2 a ``MAX_COMBINACAO`` itens que somam o alvo (em centavos). Para no segundo: já é ambíguo."""
    achados: list[tuple] = []
    if len(itens) > MAX_ITENS_COMBINACAO:
        return achados
    for tamanho in range(2, min(MAX_COMBINACAO, len(itens)) + 1):
        for grupo in combinations(itens, tamanho):
            if sum(_centavos(valor(i)) for i in grupo) == alvo:
                achados.append(grupo)
                if len(achados) > 1:
                    return achados
    return achados


def _casar(pix: list[dict], notas: list[dict]) -> tuple[list[tuple[list, list]], list[dict]]:
    """Grupos exatos entre os Pix e as notas de um mesmo pagador. Devolve ``(grupos, Pix que sobraram)``."""
    grupos: list[tuple[list, list]] = []

    def tirar(usados_pix, usadas_notas):
        grupos.append((list(usados_pix), list(usadas_notas)))
        pix[:] = [p for p in pix if p not in usados_pix]
        notas[:] = [n for n in notas if n not in usadas_notas]

    # 1) mesmo valor: tantos Pix quanto notas com aquele valor (2 Pix e 1 nota iguais = ambíguo, fica para conferir)
    for valor in sorted({_centavos(_liquido(p)) for p in pix}):
        mesmos_pix = [p for p in pix if _centavos(_liquido(p)) == valor]
        mesmas_notas = [n for n in notas if _centavos(n["valor"]) == valor]
        if len(mesmos_pix) == len(mesmas_notas):
            for p, n in zip(mesmos_pix, mesmas_notas, strict=True):
                tirar([p], [n])
    # 2) um Pix paga várias notas (uma combinação só)
    for p in list(pix):
        alvo = _centavos(_liquido(p))
        if sum(_centavos(_liquido(o)) == alvo for o in pix) == 1:
            achados = _combinacoes(notas, alvo, lambda n: n["valor"])
            if len(achados) == 1:
                tirar([p], achados[0])
    # 3) vários Pix pagam uma nota (uma combinação só)
    for n in list(notas):
        alvo = _centavos(n["valor"])
        if sum(_centavos(o["valor"]) == alvo for o in notas) == 1:
            achados = _combinacoes(pix, alvo, _liquido)
            if len(achados) == 1:
                tirar(achados[0], [n])
    # 4) vários Pix pagam várias notas: o que sobrou fecha certinho
    if pix and notas and sum(_centavos(_liquido(p)) for p in pix) == sum(_centavos(n["valor"]) for n in notas):
        tirar(list(pix), list(notas))
    return grupos, pix


def _candidatas(pix: dict, notas: list[dict]) -> tuple[str, list[dict]]:
    """Notas que podem ser deste Pix sem correspondência exata, e o porquê de ficar para conferir."""
    valor, documento_pix = _centavos(_liquido(pix)), pix["documento"]
    if valor <= 0:
        return "Devolvido ao pagador: não paga nenhuma nota.", []
    # do mesmo cliente, as de valor igual primeiro; de outra filial ou de outro cliente, só as de valor igual
    mesmo_documento = sorted((n for n in notas if documento_pix and n["documento"] == documento_pix),
                             key=lambda n: _centavos(n["valor"]) != valor)
    mesmo_valor = [n for n in notas if _centavos(n["valor"]) == valor and n not in mesmo_documento]
    mesma_raiz = [n for n in mesmo_valor if len(documento_pix) == 14 and len(n["documento"]) == 14
                  and n["documento"][:8] == documento_pix[:8]]
    mesmo_valor = [n for n in mesmo_valor if n not in mesma_raiz]
    candidatas = (mesmo_documento + mesma_raiz + mesmo_valor)[:10]
    if pix.get("devolvido"):
        motivo = "Teve devolução ao pagador: confira o valor que sobrou."
    elif any(_centavos(n["valor"]) == valor for n in mesmo_documento):
        motivo = "Este cliente tem mais de um Pix ou nota com o mesmo valor: escolha qual nota este Pix paga."
    elif mesmo_documento:
        motivo = "O CNPJ/CPF bate com notas em aberto, mas o valor não fecha certinho."
    elif mesma_raiz:
        motivo = "Mesma empresa (raiz do CNPJ), mas outra filial."
    elif mesmo_valor and not documento_pix:
        motivo = "O Pix veio sem o CNPJ/CPF de quem pagou; o valor bate."
    elif mesmo_valor and not any(n["documento"] for n in mesmo_valor):
        motivo = "O valor bate, mas a nota não tem o CNPJ/CPF do cliente."
    else:
        motivo = "O valor bate, mas quem pagou tem outro CNPJ/CPF."
    return motivo, candidatas


def conciliar(pix: list[dict], notas: list[dict], usados: dict[str, int]) -> dict:
    """Junta os Pix recebidos com as notas Aguardando pagamento, pelo CNPJ/CPF de quem pagou e pelo valor exato.

    ``sugestoes``: grupos que fecham certinho (1 Pix e 1 nota, 1 Pix e várias notas, vários Pix e 1 nota, vários e
    vários); ``conferir``: Pix com alguma nota possível, mas sem correspondência exata (com o motivo); ``sem_nota``: Pix
    sem nenhuma nota parecida; ``ligados``: Pix que já pagaram (``usados``: ID -> nº do pagamento). Nada é gravado aqui.
    """
    ligados, livres = [], []
    for p in sorted(pix, key=lambda p: (p["horario"], p["e2e"])):
        pagamento = usados.get(_chave_id(p["e2e"]))
        if pagamento:
            ligados.append({**p, "pagamento_id": pagamento})
        else:
            livres.append(p)
    abertas = sorted((_nota_publica(n) for n in notas), key=lambda n: (n["emitida_em"], n["id"]))
    por_pagador: dict[str, list[dict]] = {}
    restantes = []
    for p in livres:
        if p["documento"] and not p.get("devolvido"):
            por_pagador.setdefault(p["documento"], []).append(p)
        else:
            restantes.append(p)
    sugestoes, tomadas = [], set()
    for documento_pix, lista in por_pagador.items():
        grupos, sobra = _casar(lista, [n for n in abertas if n["documento"] == documento_pix and n["valor"]])
        for grupo_pix, grupo_notas in grupos:
            sugestoes.append({"pix": grupo_pix, "notas": grupo_notas,
                              "valor": round(sum(_liquido(p) for p in grupo_pix), 2)})
            tomadas.update(n["id"] for n in grupo_notas)
        restantes += sobra
    livres_notas = [n for n in abertas if n["id"] not in tomadas]
    conferir, sem_nota = [], []
    for p in sorted(restantes, key=lambda p: (p["horario"], p["e2e"])):
        motivo, candidatas = _candidatas(p, livres_notas)
        if candidatas or p.get("devolvido"):
            conferir.append({"pix": p, "motivo": motivo, "candidatas": candidatas})
        else:
            sem_nota.append(p)
    sugestoes.sort(key=lambda s: (s["pix"][0]["horario"], s["pix"][0]["e2e"]))
    return {"sugestoes": sugestoes, "conferir": conferir, "sem_nota": sem_nota, "ligados": ligados}


def _resultado(consulta: dict) -> dict:
    """A última consulta ao banco conciliada com as notas e os pagamentos de agora."""
    notas = [r for r in ctx.transferencias.listar() if r.get("status") == AGUARDANDO]
    usados = {chave: p["id"] for p in ctx.transferencias.listar("pagamentos") if p.get("status") == ATIVO
              for chave in _ids(p.get("id_transacao"))}
    return {"consultado_em": consulta["consultado_em"], "inicio": consulta["inicio"], "fim": consulta["fim"],
            "total": len(consulta["pix"]), **conciliar(list(consulta["pix"].values()), notas, usados)}


def situacao_bradesco() -> dict:
    """Se a consulta ao Bradesco está ligada (ou o motivo de não estar), o período padrão e a última consulta."""
    cfg, motivo = bradesco.configuracao()
    hoje = date.today()
    inicio, fim = PERIODO_SANDBOX if cfg and cfg.ambiente == "sandbox" else (hoje - timedelta(days=DIAS_CONSULTA), hoje)
    consulta = _consulta if cfg and _consulta and _consulta["ambiente"] == cfg.ambiente else None
    return {"ligado": cfg is not None, "motivo": motivo, "ambiente": cfg.ambiente if cfg else "",
            "ambiente_nome": bradesco.ROTULOS[cfg.ambiente] if cfg else "", "inicio": inicio.isoformat(),
            "fim": fim.isoformat(), "consulta": _resultado(consulta) if consulta else None}


def consultar_bradesco(inicio: str, fim: str) -> dict:
    """Busca no Bradesco os Pix recebidos no período (datas AAAA-MM-DD, no fuso do sistema) e devolve a conciliação."""
    global _consulta
    try:
        primeiro, ultimo = date.fromisoformat(inicio), date.fromisoformat(fim)
    except (TypeError, ValueError):
        raise ErroPagamento(422, "data_invalida", "Informe as datas do período (de e até).") from None
    if ultimo < primeiro:
        raise ErroPagamento(422, "periodo_invalido", "A data final vem antes da inicial.")
    if primeiro > date.today():
        raise ErroPagamento(422, "periodo_invalido", "A data inicial não pode ser depois de hoje.")
    if (ultimo - primeiro).days >= MAX_DIAS_CONSULTA:
        raise ErroPagamento(422, "periodo_longo", f"Escolha um período de até {MAX_DIAS_CONSULTA} dias.")
    cfg, motivo = bradesco.configuracao()
    if cfg is None:
        raise ErroPagamento(503, "bradesco_desligado", motivo)
    comeco = datetime.combine(primeiro, datetime.min.time()).astimezone()
    final = min(datetime.combine(ultimo + timedelta(days=1), datetime.min.time()).astimezone() - timedelta(seconds=1),
                datetime.now().astimezone())
    try:
        pix = bradesco.listar_pix(comeco, final)
    except bradesco.ErroBradesco as exc:
        raise ErroPagamento(502, "bradesco_falhou", str(exc)) from None
    _consulta = {"ambiente": cfg.ambiente, "inicio": primeiro.isoformat(), "fim": ultimo.isoformat(),
                 "consultado_em": datetime.now().isoformat(timespec="seconds"),
                 "pix": {_chave_id(p["e2e"]): p for p in pix}}
    return situacao_bradesco()


def ligar_pix(ids: list[int], e2es: list[str], observacao: str, usuario: str) -> tuple[dict, list[dict]]:
    """Liga um ou mais Pix da última consulta ao Bradesco às notas. Valor, data e pagador vêm do banco, não da tela."""
    chaves = list(dict.fromkeys(c for c in map(_chave_id, e2es) if c))
    if not chaves:
        raise ErroPagamento(422, "sem_pix", "Marque pelo menos um Pix.")
    consultados = (_consulta or {}).get("pix") or {}
    if any(c not in consultados for c in chaves):
        raise ErroPagamento(409, "pix_nao_consultado",
                            "Este Pix não está na última consulta ao Bradesco. Clique em Buscar Pix e tente de novo.")
    pix = [consultados[c] for c in chaves]
    if any(_liquido(p) <= 0 for p in pix):
        raise ErroPagamento(409, "pix_devolvido", "Este Pix foi devolvido ao pagador e não paga nenhuma nota.")
    documentos = {p["documento"] for p in pix if p["documento"]}
    horarios = [p["horario"] for p in pix if p["horario"]]
    dados = {"valor": round(sum(_liquido(p) for p in pix), 2),
             "data_pagamento": datetime.fromisoformat(max(horarios)).date() if horarios else date.today(),
             "pagador": "; ".join(dict.fromkeys(p["pagador"] for p in pix if p["pagador"]))[:120],
             "documento_pagador": documentos.pop() if len(documentos) == 1 else "",
             "id_transacao": ", ".join(p["e2e"] for p in pix), "origem": ORIGEM_PIX,
             "observacao": re.sub(r"\s+", " ", str(observacao or "")).strip()[:300]}
    return _gravar(ids, dados, usuario)

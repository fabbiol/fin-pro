"""Orquestra a leitura: arquivo → códigos + campos → boletos consolidados, com fonte, confiança e alertas.

Ordem de confiança por campo:
* Linha digitável / código de barras: código de barras da imagem > texto do PDF > OCR > IA.
* Vencimento e valor: decodificados do código (exatos) — o impresso serve para conferência.
* Beneficiário, CPF/CNPJ e nº do documento: texto do PDF > OCR > IA.

Tratamentos especiais:
* Fotos de papel: recorte e correção de perspectiva ("modo scanner"), rotação pelo código de barras.
* PDFs escaneados com camada de texto ruim: OCR complementar para preencher o que faltar.
* Guias de tributos (DAS, DARF, GPS...): beneficiário é o órgão arrecadador.
* Contas de consumo sem rótulo "Beneficiário": nome em destaque no cabeçalho.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any

from .codigo import (
    ARRECADACAO,
    BANCARIO,
    ResultadoCodigo,
    analisar,
    candidatos_correcao,
    data_por_fator,
    somente_digitos,
    tentar_corrigir,
)
from .imagem import endireitar_documento, melhorar_para_ocr
from .leitores import DocumentoPDF, PaginaLida, abrir_imagem, eh_pdf, ler_codigos_barras, motor_ocr, texto_de_segmentos
from .texto import (
    CampoTexto,
    encontrar_codigos,
    encontrar_codigos_segmentos,
    extrair_campos,
    extrair_data,
    identificar_guia,
    nome_no_cabecalho,
    normalizar,
    segmentar_palavras,
)

log = logging.getLogger(__name__)

CAMPOS_DOCUMENTO = ("beneficiario", "documento_beneficiario", "numero_documento", "vencimento", "valor")
ORDEM_CAMPOS = ("linha_digitavel", "codigo_barras", "beneficiario", "documento_beneficiario", "numero_documento", "vencimento", "valor")
_PESO_NIVEL = {"erro": 0, "aviso": 1, "info": 2}


class ErroLeitura(ValueError):
    """Arquivo ilegível ou em formato não suportado."""


@dataclass
class Campo:
    valor: Any
    fonte: str
    confianca: float

    def para_dict(self) -> dict:
        valor = self.valor
        if isinstance(valor, (date, datetime)):
            valor = valor.isoformat()
        elif isinstance(valor, Decimal):
            valor = float(valor)
        return {"valor": valor, "fonte": self.fonte, "confianca": round(float(self.confianca), 3)}


def _alerta(nivel: str, mensagem: str, codigo: str | None = None) -> dict:
    return {"nivel": nivel, "mensagem": mensagem, "codigo": codigo}


def _brl(valor) -> str:
    texto = f"{Decimal(str(valor)):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _decimal(valor) -> Decimal | None:
    if valor in (None, ""):
        return None
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


# --------------------------------------------------------------------------- consolidação


def consolidar(
    codigo: ResultadoCodigo | None,
    *,
    campos_doc: dict[str, Campo],
    referencia: date,
    fonte_codigo: str = "codigo_barras",
    confianca_codigo: float = 0.99,
    planilha=None,
    sugestoes: list[ResultadoCodigo] | None = None,
    alertas: list[dict] | None = None,
    pagina: int = 0,
) -> dict:
    """Combina o código decodificado com os campos lidos do documento e gera alertas."""
    alertas = list(alertas or [])
    campos: dict[str, Campo] = {}
    hoje = date.today()

    if codigo is not None:
        conf = confianca_codigo if codigo.valido else 0.3
        campos["linha_digitavel"] = Campo(codigo.linha_formatada, fonte_codigo, conf)
        campos["codigo_barras"] = Campo(codigo.codigo_barras, fonte_codigo, conf)
        if not codigo.valido:
            alertas.append(_alerta("erro", "Linha digitável inválida: " + "; ".join(codigo.erros) + ".", "linha_invalida"))
        if codigo.corrigido:
            alertas.append(_alerta(
                "aviso",
                "Dígito(s) da linha digitável corrigido(s) automaticamente com base nos dígitos verificadores. Confira com o boleto.",
                "linha_corrigida",
            ))
    else:
        alertas.append(_alerta(
            "erro",
            "Não foi possível ler a linha digitável nem o código de barras. Digite-a manualmente ou tente a análise com IA.",
            "sem_codigo",
        ))

    codigo_ok = codigo is not None and codigo.valido

    # ---- vencimento
    venc_doc = campos_doc.get("vencimento")
    venc_doc_data = venc_doc.valor if venc_doc and isinstance(venc_doc.valor, date) else None
    if codigo_ok and codigo.tipo == BANCARIO and codigo.fator_vencimento and codigo.vencimento:
        venc_codigo = codigo.vencimento
        if venc_doc_data and venc_doc_data != venc_codigo:
            # O fator reiniciou em 2025: se o impresso casar com o outro ciclo, ele desempata.
            alternativa = data_por_fator(codigo.fator_vencimento, venc_doc_data)
            if alternativa == venc_doc_data:
                venc_codigo = alternativa
        confere = venc_doc_data is None or venc_doc_data == venc_codigo
        campos["vencimento"] = Campo(venc_codigo, "codigo_barras", 0.99 if confere else 0.9)
        if not confere:
            alertas.append(_alerta(
                "aviso",
                f"Vencimento impresso ({_data_br(venc_doc_data)}) difere do vencimento do código de barras "
                f"({_data_br(venc_codigo)}). Foi usado o do código.",
                "vencimento_divergente",
            ))
    elif venc_doc_data:
        campos["vencimento"] = venc_doc
    elif codigo_ok and codigo.vencimento:
        campos["vencimento"] = Campo(codigo.vencimento, "codigo_barras", 0.5)
        alertas.append(_alerta(
            "aviso", "Vencimento estimado a partir do código de barras da concessionária. Confira.", "vencimento_estimado"
        ))

    # ---- valor
    valor_doc = campos_doc.get("valor")
    valor_doc_dec = _decimal(valor_doc.valor) if valor_doc else None
    if codigo_ok and codigo.valor and codigo.valor > 0:
        confere = valor_doc_dec is None or valor_doc_dec == codigo.valor
        campos["valor"] = Campo(codigo.valor, "codigo_barras", 0.99 if confere else 0.92)
        if not confere:
            alertas.append(_alerta(
                "aviso",
                f"Valor impresso ({_brl(valor_doc_dec)}) difere do valor do código de barras ({_brl(codigo.valor)}). "
                "Foi usado o do código.",
                "valor_divergente",
            ))
    elif valor_doc_dec is not None:
        campos["valor"] = Campo(valor_doc_dec, valor_doc.fonte, valor_doc.confianca)
        if codigo_ok and codigo.tipo == BANCARIO:
            alertas.append(_alerta("info", "O código de barras não traz valor; foi usado o valor impresso no boleto.", "valor_do_documento"))
    elif codigo_ok and codigo.tipo == ARRECADACAO and codigo.valor is None:
        alertas.append(_alerta("info", "Este código usa valor de referência (não monetário). Informe o valor.", "valor_referencia"))

    for nome in ("beneficiario", "documento_beneficiario", "numero_documento"):
        if nome in campos_doc and campos_doc[nome].valor not in (None, ""):
            campos[nome] = campos_doc[nome]

    for nome, rotulo in (("beneficiario", "Beneficiário"), ("numero_documento", "Nº do documento"),
                         ("vencimento", "Vencimento"), ("valor", "Valor")):
        if nome not in campos:
            alertas.append(_alerta("aviso", f"{rotulo} não encontrado — preencha manualmente.", f"ausente_{nome}"))

    venc = campos.get("vencimento")
    if venc and isinstance(venc.valor, date):
        dias = (venc.valor - hoje).days
        if dias < 0:
            alertas.append(_alerta("aviso", f"Boleto vencido há {-dias} dia(s) ({_data_br(venc.valor)}).", "vencido"))
        elif dias == 0:
            alertas.append(_alerta("info", "Este boleto vence hoje.", "vence_hoje"))
        elif dias <= 3:
            alertas.append(_alerta("info", f"Vence em {dias} dia(s).", "vence_em_breve"))

    duplicado = None
    if planilha is not None and codigo_ok:
        try:
            existentes = planilha.buscar_por_codigo(codigo.codigo_barras)
        except Exception:  # planilha indisponível não deve impedir a leitura
            log.exception("Falha ao verificar duplicidade")
            existentes = []
        if existentes:
            e = existentes[0]
            lancado = e.get("data_lancamento")
            quando = lancado.strftime("%d/%m/%Y %H:%M") if isinstance(lancado, datetime) else "data desconhecida"
            duplicado = {"id": e["id"], "data_lancamento": lancado.isoformat() if isinstance(lancado, datetime) else None,
                         "status": e.get("status")}
            alertas.append(_alerta("erro", f"Este boleto já foi lançado na planilha (ID {e['id']}, em {quando}).", "duplicado"))

    essenciais = ("linha_digitavel", "vencimento", "valor", "beneficiario")
    confianca = min(campos[k].confianca if k in campos else 0.0 for k in essenciais)
    alertas.sort(key=lambda a: _PESO_NIVEL.get(a["nivel"], 3))

    return {
        "pagina": pagina,
        "campos": {k: campos[k].para_dict() for k in ORDEM_CAMPOS if k in campos},
        "codigo": codigo.para_dict() if codigo else None,
        "tipo": codigo.tipo if codigo else None,
        "emissor": codigo.emissor if codigo else "",
        "sugestoes_linha": [s.linha_formatada for s in (sugestoes or [])],
        "alertas": alertas,
        "duplicado": duplicado,
        "confianca": round(confianca, 3),
    }


# --------------------------------------------------------------------------- apoio à leitura


def _campos_de_texto(campos: dict[str, CampoTexto], fonte: str) -> dict[str, Campo]:
    resultado = {}
    for nome, c in campos.items():
        valor, confianca = c.valor, c.confianca
        if fonte == "ocr" and nome == "beneficiario" and isinstance(valor, str):
            segmentado = segmentar_palavras(valor)
            if segmentado != valor:
                confianca = min(confianca, 0.78)  # nome reconstruído: pedir conferência
            valor = segmentado
        resultado[nome] = Campo(valor, fonte, confianca)
    return resultado


def _texto_pdf_util(pagina: PaginaLida) -> bool:
    if sum(ch.isalnum() for ch in pagina.texto) < 40:
        return False
    norm = normalizar(pagina.texto)
    return any(p in norm for p in ("venc", "benefici", "cedente", "valor", "pagador", "pagar", "total"))


def _pontuacao_ocr(segmentos) -> float:
    return sum(sum(ch.isalnum() for ch in s.texto) * s.confianca for s in segmentos)


def _texto_vertical(segmentos) -> bool:
    """A maioria das linhas de texto está na vertical (página girada 90°)?"""
    linhas = [s for s in segmentos if len(s.texto.replace(" ", "")) >= 4]
    if len(linhas) < 5:
        return False
    verticais = sum(1 for s in linhas if (s.y1 - s.y0) > 1.5 * (s.x1 - s.x0))
    return verticais / len(linhas) > 0.5


def _qualidade_layout(segmentos, altura: float) -> tuple[int, float]:
    campos = extrair_campos(segmentos, texto_de_segmentos(segmentos), None, altura)
    return len(campos), _pontuacao_ocr(segmentos)


def _ocr_pagina(pagina: PaginaLida, tentar_rotacoes: bool) -> None:
    imagem = pagina.imagem
    segmentos = motor_ocr.reconhecer(imagem, pagina.indice)
    pontos = _pontuacao_ocr(segmentos)

    if tentar_rotacoes and _texto_vertical(segmentos):
        # Sem código de barras para orientar: testa os dois sentidos e fica com o que forma o leiaute de boleto
        melhor = (_qualidade_layout(segmentos, imagem.height), segmentos, imagem)
        for angulo in (90, 270):
            girada = imagem.rotate(angulo, expand=True, fillcolor="white")
            tentativa = motor_ocr.reconhecer(girada, pagina.indice)
            qualidade = _qualidade_layout(tentativa, girada.height)
            if qualidade > melhor[0]:
                melhor = (qualidade, tentativa, girada)
        _, segmentos, imagem = melhor
        pontos = _pontuacao_ocr(segmentos)

    if tentar_rotacoes and pontos < 80:
        for angulo in (90, 270, 180):
            girada = imagem.rotate(angulo, expand=True, fillcolor="white")
            tentativa = motor_ocr.reconhecer(girada, pagina.indice)
            if _pontuacao_ocr(tentativa) > pontos * 1.3:
                imagem, segmentos, pontos = girada, tentativa, _pontuacao_ocr(tentativa)

    if pontos < 250:
        # Pouco texto reconhecido: tenta de novo com iluminação uniformizada (sombras, papel amarelado)
        tratada = melhorar_para_ocr(imagem)
        tentativa = motor_ocr.reconhecer(tratada, pagina.indice)
        if _pontuacao_ocr(tentativa) > pontos * 1.15:
            segmentos = tentativa

    pagina.imagem = imagem
    pagina.segmentos = segmentos
    pagina.texto = texto_de_segmentos(segmentos)
    pagina.origem_texto = "ocr"
    pagina.largura, pagina.altura = imagem.size


def _ocr_complementar(pagina: PaginaLida) -> SimpleNamespace:
    segmentos = motor_ocr.reconhecer(pagina.imagem, pagina.indice)
    return SimpleNamespace(segmentos=segmentos, texto=texto_de_segmentos(segmentos), altura=pagina.imagem.height)


def _completar_emissor(campos_doc: dict[str, Campo], codigo: ResultadoCodigo | None, segmentos, texto: str,
                       altura: float, fonte: str) -> None:
    """Beneficiário de guias de tributos e de contas de consumo sem rótulo."""
    if codigo is None or codigo.tipo == ARRECADACAO:
        guia = identificar_guia(texto)
        if guia:
            # Em guias, CNPJ e razão social impressos são do contribuinte (quem paga)
            campos_doc["beneficiario"] = Campo(guia, fonte, 0.9)
            campos_doc.pop("documento_beneficiario", None)
            return
    if "beneficiario" in campos_doc:
        return
    nome, documento = nome_no_cabecalho(segmentos, altura)
    if nome:
        confianca = nome.confianca if codigo is None or codigo.tipo == ARRECADACAO else min(nome.confianca, 0.5)
        campos_doc["beneficiario"] = Campo(nome.valor, fonte, confianca)
        if documento and "documento_beneficiario" not in campos_doc:
            campos_doc["documento_beneficiario"] = Campo(documento, fonte, 0.6)


def _desempatar(sugestoes: list[ResultadoCodigo], campos_doc: dict[str, Campo]) -> ResultadoCodigo | None:
    """Escolhe entre correções possíveis usando o valor/vencimento impressos."""
    if not sugestoes:
        return None
    valor = _decimal(campos_doc["valor"].valor) if "valor" in campos_doc else None
    venc = campos_doc["vencimento"].valor if "vencimento" in campos_doc else None
    if valor is None and venc is None:
        return sugestoes[0] if len(sugestoes) == 1 else None
    filtradas = [
        s for s in sugestoes
        if (valor is None or s.valor is None or s.valor == valor)
        and (venc is None or s.vencimento is None or s.vencimento == venc)
    ]
    return filtradas[0] if len(filtradas) == 1 else None


def _codigos_da_pagina(barras, codigos_texto, altura: float, fonte_texto: str) -> dict[str, dict]:
    encontrados: dict[str, dict] = {}
    for leitura in barras:
        r = analisar(leitura.digitos)
        if r and r.valido:
            encontrados.setdefault(r.codigo_barras, {
                "resultado": r, "fonte": "codigo_barras", "confianca": 0.99, "y": leitura.y_centro * altura,
            })
    for c in codigos_texto:
        if not c.resultado.valido:
            continue
        chave = c.resultado.codigo_barras
        if chave in encontrados:
            encontrados[chave]["confianca"] = 0.995  # código de barras e texto concordam
            continue
        encontrados[chave] = {
            "resultado": c.resultado, "fonte": fonte_texto,
            "confianca": 0.97 if fonte_texto == "texto" else 0.9, "y": c.y,
        }
    return encontrados


def _recalcular_confianca(boleto: dict) -> None:
    campos = boleto["campos"]
    boleto["confianca"] = round(min(
        (campos[k]["confianca"] if k in campos else 0.0) for k in ("linha_digitavel", "vencimento", "valor", "beneficiario")
    ), 3)


def harmonizar_beneficiarios(boletos: list[dict], planilha=None) -> None:
    """Mesmo CPF/CNPJ → mesmo nome de beneficiário.

    1. Se o documento já foi lançado, usa o nome gravado na planilha (já conferido pelo usuário).
    2. Senão, entre boletos do mesmo arquivo, prevalece o nome mais confiável/frequente
       (corrige leituras ruins de OCR como "NIPER 3N" em uma das páginas).
    """
    historico: dict[str, str] = {}
    if planilha is not None:
        try:
            historico = planilha.nomes_por_documento()
        except Exception:
            log.exception("Falha ao consultar nomes de beneficiários na planilha")

    grupos: dict[str, list[dict]] = defaultdict(list)
    for boleto in boletos:
        documento = somente_digitos((boleto["campos"].get("documento_beneficiario") or {}).get("valor"))
        if len(documento) in (11, 14):
            grupos[documento].append(boleto)

    for documento, grupo in grupos.items():
        nome_historico = historico.get(documento)
        if nome_historico:
            for boleto in grupo:
                atual = boleto["campos"].get("beneficiario")
                if atual and normalizar(atual["valor"]).strip() == normalizar(nome_historico).strip():
                    continue
                lido = f' (lido no documento: "{atual["valor"]}")' if atual else ""
                boleto["campos"]["beneficiario"] = {"valor": nome_historico, "fonte": "historico", "confianca": 0.97}
                boleto["alertas"] = [a for a in boleto["alertas"] if a["codigo"] != "ausente_beneficiario"]
                boleto["alertas"].append(_alerta(
                    "info", f"Beneficiário preenchido conforme lançamentos anteriores deste CPF/CNPJ{lido}.", "beneficiario_historico",
                ))
                _recalcular_confianca(boleto)
            continue

        pesos: dict[str, float] = defaultdict(float)
        originais: dict[str, str] = {}
        for boleto in grupo:
            atual = boleto["campos"].get("beneficiario")
            if atual:
                chave = normalizar(atual["valor"]).strip()
                pesos[chave] += atual["confianca"]
                originais.setdefault(chave, atual["valor"])
        if len(pesos) < 2:
            continue
        vencedor = max(pesos, key=pesos.get)
        for boleto in grupo:
            atual = boleto["campos"].get("beneficiario")
            if atual and normalizar(atual["valor"]).strip() == vencedor:
                continue
            boleto["campos"]["beneficiario"] = {
                "valor": originais[vencedor], "fonte": atual["fonte"] if atual else "ocr", "confianca": 0.9,
            }
            if atual:
                boleto["alertas"].append(_alerta(
                    "info", f'Nome ajustado para coincidir com os outros boletos do mesmo CNPJ (lido: "{atual["valor"]}").',
                    "beneficiario_consenso",
                ))
            _recalcular_confianca(boleto)


# --------------------------------------------------------------------------- leitura de arquivos


def ler_arquivo(dados: bytes, *, planilha=None, referencia: date | None = None, max_paginas: int = 30,
                ao_progresso=None) -> dict:
    """Lê um PDF ou imagem e devolve os boletos encontrados.

    ``ao_progresso(pagina=, paginas=, etapa=)`` é chamado ao longo da leitura (usado pela barra de progresso).
    """
    inicio = time.perf_counter()
    referencia = referencia or date.today()
    progresso = ao_progresso or (lambda **_: None)

    if eh_pdf(dados):
        tipo_arquivo = "pdf"
        try:
            documento = DocumentoPDF(dados)
        except Exception as exc:
            raise ErroLeitura("Não foi possível abrir o PDF (arquivo corrompido ou protegido por senha).") from exc
        quantidade = min(documento.total, max_paginas)
        if not quantidade:
            documento.fechar()
            raise ErroLeitura("O PDF não tem páginas.")
        paginas = documento.paginas(max_paginas)  # renderiza uma página por vez
        if documento.total > quantidade:
            aviso_paginas = (f"O PDF tem {documento.total} páginas; foram lidas as {quantidade} primeiras "
                             "(ajuste LEITOR_MAX_PAGINAS_PDF no .env para ler mais).")
        else:
            aviso_paginas = None
    else:
        tipo_arquivo = "imagem"
        try:
            imagem = abrir_imagem(dados)
        except Exception as exc:
            raise ErroLeitura("Formato não suportado. Envie PDF, JPG, PNG, WEBP ou HEIC.") from exc
        paginas = iter([PaginaLida(0, imagem.width, imagem.height, [], "", "ocr", imagem)])
        quantidade = 1
        aviso_paginas = None
    progresso(pagina=0, paginas=quantidade, etapa="iniciando")

    boletos: list[dict] = []
    sem_codigo: list[tuple[int, dict]] = []
    avisos: list[str] = [aviso_paginas] if aviso_paginas else []
    tratamentos: set[str] = set()
    textos: list[str] = []  # texto de todas as páginas (usado para reconhecer comprovantes de pagamento)
    ocr_usado = False
    ocr_disponivel = motor_ocr.disponivel

    for pagina in paginas:
        progresso(pagina=pagina.indice + 1, paginas=quantidade, etapa="codigo_barras")
        # ---- imagem: modo scanner + código de barras
        barras = []
        if pagina.imagem is not None:
            original = pagina.imagem
            if tipo_arquivo == "imagem":
                endireitada, corrigiu = endireitar_documento(original)
                if corrigiu:
                    pagina.imagem = endireitada
                    pagina.largura, pagina.altura = endireitada.size
            barras = ler_codigos_barras(pagina.imagem)
            if not barras and pagina.imagem is not original:
                barras = ler_codigos_barras(original)
                if barras:
                    pagina.imagem = original
                    pagina.largura, pagina.altura = original.size
            if pagina.imagem is not original:
                tratamentos.add("perspectiva")
            # Boleto deitado/de cabeça para baixo (fotos e scans): endireita pela orientação do código de barras
            texto_vem_da_imagem = tipo_arquivo == "imagem" or pagina.escaneada or not _texto_pdf_util(pagina)
            if texto_vem_da_imagem and barras and barras[0].orientacao % 360:
                pagina.imagem = pagina.imagem.rotate(barras[0].orientacao, expand=True, fillcolor="white")
                if tipo_arquivo == "imagem":
                    pagina.largura, pagina.altura = pagina.imagem.size
                barras = ler_codigos_barras(pagina.imagem) or barras
                tratamentos.add("rotacao")

        # ---- texto: camada do PDF ou OCR
        if tipo_arquivo == "imagem" or not _texto_pdf_util(pagina):
            if ocr_disponivel:
                progresso(pagina=pagina.indice + 1, paginas=quantidade, etapa="ocr")
                _ocr_pagina(pagina, tentar_rotacoes=not barras)
                ocr_usado = True
            else:
                avisos.append("OCR indisponível: apenas o código de barras pôde ser lido desta página.")

        fonte_texto = "texto" if pagina.origem_texto == "pdf" else "ocr"
        textos.append(pagina.texto or "")
        codigos_texto = encontrar_codigos_segmentos(pagina.segmentos, referencia) if pagina.segmentos else []
        if not any(c.resultado.valido for c in codigos_texto) and pagina.texto:
            codigos_texto += [c for c in encontrar_codigos(pagina.texto, referencia) if c.resultado.valido]
        encontrados = _codigos_da_pagina(barras, codigos_texto, pagina.altura, fonte_texto)

        # ---- PDF escaneado com camada de texto (OCR do scanner): complementa com o nosso OCR
        complemento = None
        if pagina.origem_texto == "pdf" and pagina.escaneada and ocr_disponivel and pagina.imagem is not None:
            campos_teste = extrair_campos(pagina.segmentos, pagina.texto, None, pagina.altura)
            if not encontrados or not {"beneficiario", "numero_documento", "vencimento", "valor"} <= campos_teste.keys():
                progresso(pagina=pagina.indice + 1, paginas=quantidade, etapa="ocr")
                complemento = _ocr_complementar(pagina)
                ocr_usado = True
                if not encontrados:
                    codigos_ocr = encontrar_codigos_segmentos(complemento.segmentos, referencia)
                    for chave, item in _codigos_da_pagina([], codigos_ocr, complemento.altura, "ocr").items():
                        if item["y"] is not None:
                            item["y"] *= pagina.altura / complemento.altura
                        encontrados[chave] = item
                    codigos_texto += [c for c in codigos_ocr if not c.resultado.valido]

        def campos_para(y_ref: float | None, codigo: ResultadoCodigo | None) -> dict[str, Campo]:
            campos = _campos_de_texto(extrair_campos(pagina.segmentos, pagina.texto, y_ref, pagina.altura), fonte_texto)
            if complemento is not None:
                y_ocr = y_ref * complemento.altura / pagina.altura if y_ref is not None else None
                extras = _campos_de_texto(extrair_campos(complemento.segmentos, complemento.texto, y_ocr, complemento.altura), "ocr")
                for nome, campo in extras.items():
                    campos.setdefault(nome, campo)
            if y_ref is None:
                segs, texto, altura, fonte = (
                    (complemento.segmentos, pagina.texto + "\n" + complemento.texto, complemento.altura, "ocr")
                    if complemento is not None else (pagina.segmentos, pagina.texto, pagina.altura, fonte_texto)
                )
                _completar_emissor(campos, codigo, segs, texto, altura, fonte)
            return campos

        multiplos = len(encontrados) > 1
        if encontrados:
            for item in sorted(encontrados.values(), key=lambda i: i["y"] if i["y"] is not None else 0):
                boletos.append(consolidar(
                    item["resultado"], campos_doc=campos_para(item["y"] if multiplos else None, item["resultado"]),
                    referencia=referencia, fonte_codigo=item["fonte"], confianca_codigo=item["confianca"],
                    planilha=planilha, pagina=pagina.indice,
                ))
            continue

        invalidos = [c for c in codigos_texto if not c.resultado.valido]
        if invalidos:
            invalido = invalidos[0]
            campos_doc = campos_para(None, invalido.resultado)
            escolhido = _desempatar(invalido.sugestoes, campos_doc)
            if escolhido is not None:
                boletos.append(consolidar(
                    escolhido, campos_doc=campos_doc, referencia=referencia, fonte_codigo=fonte_texto,
                    confianca_codigo=0.75, planilha=planilha, pagina=pagina.indice,
                ))
            else:
                boletos.append(consolidar(
                    invalido.resultado, campos_doc=campos_doc, referencia=referencia, fonte_codigo=fonte_texto,
                    planilha=planilha, sugestoes=invalido.sugestoes, pagina=pagina.indice,
                ))
        else:
            campos_doc = campos_para(None, None)
            if {"vencimento", "valor", "numero_documento"} & campos_doc.keys():
                sem_codigo.append((len(campos_doc), consolidar(
                    None, campos_doc=campos_doc, referencia=referencia, planilha=planilha, pagina=pagina.indice,
                )))

    if not boletos and sem_codigo:
        boletos.append(max(sem_codigo, key=lambda item: item[0])[1])

    progresso(pagina=quantidade, paginas=quantidade, etapa="concluindo")
    harmonizar_beneficiarios(boletos, planilha)

    return {
        "tipo_arquivo": tipo_arquivo,
        "paginas": quantidade,
        "boletos": boletos,
        "ocr_usado": ocr_usado,
        "ocr_modelo": motor_ocr.modelo if ocr_usado else None,
        "tratamentos": sorted(tratamentos),
        "avisos": sorted(set(avisos)),
        "tempo_ms": int((time.perf_counter() - inicio) * 1000),
        "texto": "\n".join(textos),
    }


def analisar_linha_digitada(linha: str, *, planilha=None, referencia: date | None = None) -> dict:
    referencia = referencia or date.today()
    digitos = somente_digitos(linha)
    resultado = analisar(digitos, referencia)
    if resultado is None:
        raise ErroLeitura(
            f"A linha digitável deve ter 47 dígitos (boleto bancário) ou 48 (contas e tributos); "
            f"o código de barras tem 44. Foram informados {len(digitos)} dígitos."
        )
    sugestoes = candidatos_correcao(digitos, referencia) if not resultado.valido else []
    return consolidar(
        resultado, campos_doc={}, referencia=referencia, fonte_codigo="manual",
        confianca_codigo=1.0, planilha=planilha, sugestoes=sugestoes,
    )


# --------------------------------------------------------------------------- mescla com IA


def _converter_campo(nome: str, valor) -> Any:
    if valor in (None, ""):
        return None
    if nome == "vencimento":
        if isinstance(valor, date):
            return valor
        texto = str(valor).strip()
        try:
            return date.fromisoformat(texto[:10])
        except ValueError:
            return extrair_data(texto)
    if nome == "valor":
        texto = str(valor).strip().replace("R$", "").strip()
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        numero = _decimal(texto)
        return numero if numero is not None and numero > 0 else None
    texto = str(valor).strip()
    return texto or None


def mesclar_ia(campos_atuais: dict, dados_ia: dict, *, planilha=None, referencia: date | None = None, pagina: int = 0) -> dict:
    """Completa/confirma os campos atuais com o que a IA leu, sem confiar cegamente nela.

    A linha digitável da IA só é aceita se passar em todos os dígitos verificadores.
    """
    referencia = referencia or date.today()
    alertas: list[dict] = []

    campos_doc: dict[str, Campo] = {}
    for nome in CAMPOS_DOCUMENTO:
        atual = campos_atuais.get(nome) or {}
        if atual.get("fonte") == "codigo_barras":
            continue  # recalculado a partir do código
        valor = _converter_campo(nome, atual.get("valor"))
        if valor is not None:
            campos_doc[nome] = Campo(valor, atual.get("fonte") or "manual", float(atual.get("confianca") or 1.0))

    linha_atual = campos_atuais.get("linha_digitavel") or {}
    codigo = analisar(linha_atual.get("valor") or "", referencia)
    fonte_codigo = linha_atual.get("fonte") or "manual"
    confianca_codigo = float(linha_atual.get("confianca") or 1.0)

    linha_ia = somente_digitos(dados_ia.get("linha_digitavel"))
    codigo_ia = tentar_corrigir(linha_ia, referencia) if linha_ia else None
    if codigo is None or not codigo.valido:
        if codigo_ia is not None:
            codigo, fonte_codigo, confianca_codigo = codigo_ia, "ia", 0.75 if codigo_ia.corrigido else 0.88
    elif codigo_ia is not None and codigo_ia.codigo_barras != codigo.codigo_barras:
        alertas.append(_alerta("aviso", f"A IA leu uma linha digitável diferente: {codigo_ia.linha_formatada}.", "ia_linha_divergente"))

    for nome in CAMPOS_DOCUMENTO:
        valor_ia = _converter_campo(nome, dados_ia.get(nome))
        if valor_ia is None:
            continue
        atual = campos_doc.get(nome)
        if atual is None or atual.confianca < 0.8:
            campos_doc[nome] = Campo(valor_ia, "ia", 0.85)
        elif str(atual.valor).strip().lower() != str(valor_ia).strip().lower() and nome not in ("vencimento", "valor"):
            alertas.append(_alerta("info", f"A IA sugeriu outro valor para {nome.replace('_', ' ')}: {valor_ia}.", f"ia_sugestao_{nome}"))

    observacao = str(dados_ia.get("observacoes") or "").strip()
    if observacao:
        alertas.append(_alerta("info", f"Observação da IA: {observacao}", "ia_observacao"))

    sugestoes = []
    if codigo is None and linha_ia:
        sugestoes = candidatos_correcao(linha_ia, referencia)
    elif codigo is not None and not codigo.valido:
        sugestoes = candidatos_correcao(codigo.linha_digitavel, referencia)
    return consolidar(
        codigo, campos_doc=campos_doc, referencia=referencia, fonte_codigo=fonte_codigo,
        confianca_codigo=confianca_codigo, planilha=planilha, sugestoes=sugestoes, alertas=alertas, pagina=pagina,
    )

"""Leitura de arquivos: PDF (texto posicionado + renderização), imagens e código de barras."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .codigo import analisar
from .ocr import motor_ocr  # noqa: F401  (reexportado para o restante da aplicação)
from .texto import Segmento, agrupar_linhas, corrigir_ligaduras

log = logging.getLogger(__name__)

LADO_MAXIMO_IMAGEM = 3200

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    SUPORTA_HEIC = True
except Exception:  # pragma: no cover - dependência opcional
    SUPORTA_HEIC = False


# --------------------------------------------------------------------------- tipos de arquivo


def eh_pdf(dados: bytes) -> bool:
    return dados[:1024].lstrip().startswith(b"%PDF")


# --------------------------------------------------------------------------- PDF


@dataclass
class PaginaLida:
    indice: int
    largura: float
    altura: float
    segmentos: list[Segmento] = field(default_factory=list)
    texto: str = ""
    origem_texto: str = "pdf"  # "pdf" | "ocr"
    imagem: Image.Image | None = None
    escaneada: bool = False  # PDF cuja página é basicamente uma imagem (scan)


def _segmentos_textpage(textpage, altura_pagina: float, indice: int) -> list[Segmento]:
    import pypdfium2.raw as pdfium_c

    segmentos: list[Segmento] = []
    atual: dict | None = None
    ultimo: tuple[float, float, float, float] | None = None
    espaco_pendente = False

    def fechar():
        nonlocal atual, ultimo
        if atual and atual["texto"].strip():
            segmentos.append(Segmento(atual["texto"].strip(), atual["x0"], atual["y0"], atual["x1"], atual["y1"], indice))
        atual, ultimo = None, None

    for i in range(textpage.count_chars()):
        codigo = pdfium_c.FPDFText_GetUnicode(textpage.raw, i)
        ch = chr(codigo) if codigo else ""
        if ch in ("\r", "\n", "\x02"):
            fechar()
            espaco_pendente = False
            continue
        if not ch.strip():
            espaco_pendente = True
            continue

        esq, base, dir_, topo = textpage.get_charbox(i, loose=True)
        x0, x1 = esq, dir_
        y0, y1 = altura_pagina - topo, altura_pagina - base
        h = max(y1 - y0, 1.0)

        if atual is not None and ultimo is not None:
            ux0, uy0, ux1, uy1 = ultimo
            uh = max(uy1 - uy0, 1.0)
            ref_h = max(h, uh)
            mesma_linha = abs((y0 + y1) / 2 - (uy0 + uy1) / 2) < ref_h * 0.6
            distancia = x0 - ux1
            if not mesma_linha or distancia > ref_h * 1.1 or distancia < -ref_h * 2:
                fechar()
            elif espaco_pendente or distancia > ref_h * 0.28:
                atual["texto"] += " "

        if atual is None:
            atual = {"texto": "", "x0": x0, "y0": y0, "x1": x1, "y1": y1}
        atual["texto"] += corrigir_ligaduras(ch)
        atual["x0"], atual["y0"] = min(atual["x0"], x0), min(atual["y0"], y0)
        atual["x1"], atual["y1"] = max(atual["x1"], x1), max(atual["y1"], y1)
        ultimo = (x0, y0, x1, y1)
        espaco_pendente = False

    fechar()
    return segmentos


def _cobertura_de_imagens(pagina, largura: float, altura: float) -> float:
    """Fração da página ocupada por imagens (≈1 em PDFs escaneados)."""
    import pypdfium2.raw as pdfium_c

    area = 0.0
    try:
        for objeto in pagina.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=3):
            esq, base, dir_, topo = objeto.get_pos()
            area += max(0.0, dir_ - esq) * max(0.0, topo - base)
    except Exception:  # pragma: no cover - PDFs malformados
        log.debug("Não foi possível inspecionar as imagens da página", exc_info=True)
        return 0.0
    return min(1.0, area / max(largura * altura, 1.0))


class DocumentoPDF:
    """PDF aberto para leitura página a página.

    As páginas são renderizadas sob demanda (uma por vez), então um PDF escaneado de 30 páginas
    não ocupa centenas de MB de memória. A resolução é ajustada ao tamanho da página: um A4
    digital sai a ~216 dpi, e scans com páginas gigantes não viram imagens de 8000 px.
    """

    def __init__(self, dados: bytes):
        import pypdfium2 as pdfium

        self._documento = pdfium.PdfDocument(dados)
        self.total = len(self._documento)
        self._fechado = False

    def _ler_pagina(self, indice: int, escala_maxima: float, lado_render: int) -> PaginaLida:
        pagina = self._documento[indice]
        try:
            largura, altura = pagina.get_size()
            textpage = pagina.get_textpage()
            try:
                texto = corrigir_ligaduras(textpage.get_text_range() or "")
                segmentos = _segmentos_textpage(textpage, altura, indice)
            finally:
                textpage.close()
            escaneada = _cobertura_de_imagens(pagina, largura, altura) > 0.5
            escala = min(escala_maxima, lado_render / max(largura, altura, 1.0))
            imagem = pagina.render(scale=escala).to_pil().convert("RGB")
        finally:
            pagina.close()
        return PaginaLida(indice, largura, altura, segmentos, texto, "pdf", imagem, escaneada)

    def paginas(self, max_paginas: int = 30, escala_maxima: float = 3.0, lado_render: int = 3000):
        try:
            for indice in range(min(self.total, max_paginas)):
                yield self._ler_pagina(indice, escala_maxima, lado_render)
        finally:
            self.fechar()

    def fechar(self) -> None:
        if not self._fechado:
            self._fechado = True
            self._documento.close()


def ler_pdf(dados: bytes, max_paginas: int = 30, escala_maxima: float = 3.0, lado_render: int = 3000) -> tuple[list[PaginaLida], int]:
    """Lê até ``max_paginas`` páginas de uma vez. Devolve (páginas lidas, total de páginas do PDF)."""
    documento = DocumentoPDF(dados)
    total = documento.total
    return list(documento.paginas(max_paginas, escala_maxima, lado_render)), total


# --------------------------------------------------------------------------- imagens


def abrir_imagem(dados: bytes) -> Image.Image:
    imagem = Image.open(io.BytesIO(dados))
    imagem = ImageOps.exif_transpose(imagem)
    if imagem.mode in ("RGBA", "LA", "P"):
        fundo = Image.new("RGB", imagem.size, "white")
        convertida = imagem.convert("RGBA")
        fundo.paste(convertida, mask=convertida.split()[-1])
        imagem = fundo
    imagem = imagem.convert("RGB")
    maior = max(imagem.size)
    if maior > LADO_MAXIMO_IMAGEM:
        fator = LADO_MAXIMO_IMAGEM / maior
        imagem = imagem.resize((round(imagem.width * fator), round(imagem.height * fator)), Image.LANCZOS)
    return imagem


# --------------------------------------------------------------------------- código de barras


@dataclass
class LeituraBarras:
    digitos: str
    orientacao: int
    y_centro: float  # posição vertical relativa (0 a 1) na imagem


def _variantes_para_barras(imagem: Image.Image):
    cinza = ImageOps.grayscale(imagem)
    yield "original", cinza, {}
    yield "contraste", ImageOps.autocontrast(cinza, cutoff=2), {}
    yield "nitidez", cinza.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2)), {}
    try:
        import zxingcpp

        for nome in ("GlobalHistogram", "FixedThreshold"):
            binarizador = getattr(zxingcpp.Binarizer, nome, None)
            if binarizador is not None:
                yield f"binarizador-{nome}", cinza, {"binarizer": binarizador}
    except ImportError:  # pragma: no cover
        pass
    if max(cinza.size) < 2400:
        yield "ampliada", cinza.resize((cinza.width * 2, cinza.height * 2), Image.LANCZOS), {}
    if max(cinza.size) > 1800:
        yield "reduzida", cinza.resize((cinza.width // 2, cinza.height // 2), Image.LANCZOS), {}
    try:
        import cv2

        matriz = np.array(cinza)
        binaria = cv2.adaptiveThreshold(matriz, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
        yield "binarizada", Image.fromarray(binaria), {}
        # Fotos tremidas: fechamento horizontal reforça as barras verticais
        fechada = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, np.ones((5, 1), np.uint8))
        yield "barras-reforcadas", Image.fromarray(fechada), {}
    except Exception:  # pragma: no cover
        pass


def ler_codigos_barras(imagem: Image.Image) -> list[LeituraBarras]:
    """Decodifica códigos ITF (Interleaved 2 of 5) de 44 dígitos com dígitos verificadores válidos."""
    try:
        import zxingcpp
    except ImportError:  # pragma: no cover
        log.warning("zxing-cpp não instalado: leitura de código de barras desativada")
        return []

    encontrados: dict[str, LeituraBarras] = {}
    for nome, variante, opcoes in _variantes_para_barras(imagem):
        try:
            resultados = zxingcpp.read_barcodes(variante, formats=zxingcpp.BarcodeFormat.ITF, **opcoes)
        except Exception as exc:  # pragma: no cover
            log.debug("Falha no zxing (%s): %s", nome, exc)
            continue
        for r in resultados:
            texto = "".join(ch for ch in r.text if ch.isdigit())
            if len(texto) != 44 or texto in encontrados:
                continue
            decodificado = analisar(texto)
            if decodificado is None or not decodificado.valido:
                continue  # ITF não tem checksum próprio: descarta leituras parciais/erradas
            pos = r.position
            ys = [pos.top_left.y, pos.top_right.y, pos.bottom_left.y, pos.bottom_right.y]
            encontrados[texto] = LeituraBarras(texto, int(r.orientation), (sum(ys) / 4) / max(variante.height, 1))
        if encontrados:
            log.debug("Código de barras lido na variante %s", nome)
            break
    return list(encontrados.values())


def texto_de_segmentos(segmentos: list[Segmento]) -> str:
    return "\n".join(" ".join(s.texto for s in linha) for linha in agrupar_linhas(segmentos))

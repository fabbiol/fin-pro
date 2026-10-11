"""Tratamento de fotos de boletos em papel: recorte do papel e correção de perspectiva ("modo scanner")."""

from __future__ import annotations

import logging

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


def _ordenar_cantos(pontos: np.ndarray) -> np.ndarray:
    """Ordena 4 pontos como superior-esquerdo, superior-direito, inferior-direito, inferior-esquerdo."""
    soma = pontos.sum(axis=1)
    diferenca = np.diff(pontos, axis=1).ravel()
    return np.array([
        pontos[np.argmin(soma)],
        pontos[np.argmin(diferenca)],
        pontos[np.argmax(soma)],
        pontos[np.argmax(diferenca)],
    ], dtype=np.float32)


def _contorno_do_papel(cinza: np.ndarray) -> np.ndarray | None:
    import cv2

    area_total = cinza.shape[0] * cinza.shape[1]
    suave = cv2.GaussianBlur(cinza, (5, 5), 0)
    candidatos = []

    # 1) Papel claro sobre fundo mais escuro (limiar de Otsu)
    _, binaria = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, np.ones((17, 17), np.uint8))
    candidatos.append(binaria)

    # 2) Bordas (fundo claro ou pouco contraste)
    bordas = cv2.Canny(suave, 40, 120)
    bordas = cv2.dilate(bordas, np.ones((5, 5), np.uint8), iterations=2)
    candidatos.append(bordas)

    for mascara in candidatos:
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            continue
        maior = max(contornos, key=cv2.contourArea)
        proporcao = cv2.contourArea(maior) / area_total
        if not 0.2 <= proporcao <= 0.96:
            continue
        perimetro = cv2.arcLength(maior, True)
        aproximado = cv2.approxPolyDP(maior, 0.02 * perimetro, True)
        if len(aproximado) == 4 and cv2.isContourConvex(aproximado):
            return aproximado.reshape(4, 2).astype(np.float32)
        caixa = cv2.boxPoints(cv2.minAreaRect(maior))
        if cv2.contourArea(caixa) / area_total <= 0.96:
            return caixa.astype(np.float32)
    return None


def endireitar_documento(imagem: Image.Image) -> tuple[Image.Image, bool]:
    """Recorta o papel da foto e corrige a perspectiva. Devolve (imagem, corrigiu?)."""
    try:
        import cv2
    except ImportError:  # pragma: no cover
        return imagem, False

    rgb = np.array(imagem.convert("RGB"))
    altura, largura = rgb.shape[:2]
    escala = min(1.0, 1000 / max(altura, largura))
    pequena = cv2.resize(rgb, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA) if escala < 1 else rgb
    cinza = cv2.cvtColor(pequena, cv2.COLOR_RGB2GRAY)

    # Se as bordas da foto já são claras como papel, provavelmente é um scan/recorte: não mexe.
    borda = np.concatenate([cinza[:8].ravel(), cinza[-8:].ravel(), cinza[:, :8].ravel(), cinza[:, -8:].ravel()])
    if np.median(borda) > 200:
        return imagem, False

    cantos = _contorno_do_papel(cinza)
    if cantos is None:
        return imagem, False

    cantos = _ordenar_cantos(cantos / escala)
    (se, sd, id_, ie) = cantos
    nova_largura = int(max(np.linalg.norm(sd - se), np.linalg.norm(id_ - ie)))
    nova_altura = int(max(np.linalg.norm(ie - se), np.linalg.norm(id_ - sd)))
    if nova_largura < 300 or nova_altura < 300:
        return imagem, False
    proporcao = nova_largura / nova_altura
    if not 0.25 <= proporcao <= 4:
        return imagem, False

    destino = np.array([[0, 0], [nova_largura - 1, 0], [nova_largura - 1, nova_altura - 1], [0, nova_altura - 1]], dtype=np.float32)
    matriz = cv2.getPerspectiveTransform(cantos, destino)
    corrigida = cv2.warpPerspective(rgb, matriz, (nova_largura, nova_altura), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(corrigida), True


def melhorar_para_ocr(imagem: Image.Image) -> Image.Image:
    """Uniformiza a iluminação (remove sombras suaves) mantendo a imagem em tons de cinza."""
    try:
        import cv2
    except ImportError:  # pragma: no cover
        return imagem
    cinza = cv2.cvtColor(np.array(imagem.convert("RGB")), cv2.COLOR_RGB2GRAY)
    fundo = cv2.medianBlur(cv2.dilate(cinza, np.ones((7, 7), np.uint8)), 31)
    normalizada = cv2.divide(cinza, fundo, scale=255)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return Image.fromarray(clahe.apply(normalizada)).convert("RGB")

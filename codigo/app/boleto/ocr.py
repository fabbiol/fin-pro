"""OCR local.

Usa o RapidOCR 3 com o modelo de reconhecimento **latino** (PP-OCRv5), que lê acentos e
espaços do português. Os modelos são baixados uma única vez na primeira execução. Sem
internet nesse momento, cai automaticamente para o modelo básico do ``rapidocr_onnxruntime``.

Os resultados ficam em cache pelo conteúdo da imagem: reenviar o mesmo arquivo (ou a mesma
página em outra rotação já testada) não repete o OCR, que é a etapa mais lenta da leitura.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict

import numpy as np
from PIL import Image

from .texto import Segmento

log = logging.getLogger(__name__)

TAMANHO_CACHE = 64


class MotorOCR:
    def __init__(self):
        self._motor = None
        self._tipo: str | None = None
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, list[tuple]] = OrderedDict()
        self.erro: str | None = None
        self.acertos_cache = 0

    @property
    def disponivel(self) -> bool:
        for modulo in ("rapidocr", "rapidocr_onnxruntime"):
            try:
                __import__(modulo)
                return True
            except Exception as exc:  # pragma: no cover - depende do ambiente
                self.erro = str(exc)
        return False

    @property
    def modelo(self) -> str | None:
        return {"latino": "RapidOCR PP-OCRv5 (latino)", "basico": "RapidOCR básico"}.get(self._tipo)

    def carregar(self):
        with self._lock:
            return self._carregar()

    def _carregar(self):
        if self._motor is not None:
            return self._motor
        try:
            from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

            self._motor = RapidOCR(params={
                "Rec.lang_type": LangRec.LATIN,
                "Rec.ocr_version": OCRVersion.PPOCRV5,
                "Rec.model_type": ModelType.MOBILE,
                "Global.log_level": "error",
            })
            self._tipo = "latino"
        except Exception as exc:
            log.warning("Modelo de OCR latino indisponível (%s). Usando o modelo básico.", exc)
            from rapidocr_onnxruntime import RapidOCR

            self._motor = RapidOCR()
            self._tipo = "basico"
        log.info("OCR carregado: %s", self.modelo)
        return self._motor

    def _reconhecer_bruto(self, rgb: np.ndarray) -> list[tuple]:
        motor = self._carregar()
        if self._tipo == "latino":
            resultado = motor(rgb)
            itens = list(zip(resultado.boxes, resultado.txts, resultado.scores)) if resultado.txts else []
        else:
            bruto, _ = motor(rgb[:, :, ::-1].copy())
            itens = [(caixa, texto, conf) for caixa, texto, conf in (bruto or [])]
        saida = []
        for caixa, texto, confianca in itens:
            texto = str(texto).strip()
            if not texto:
                continue
            xs = [float(p[0]) for p in caixa]
            ys = [float(p[1]) for p in caixa]
            saida.append((texto, min(xs), min(ys), max(xs), max(ys), float(confianca)))
        return saida

    def reconhecer(self, imagem: Image.Image, pagina: int = 0) -> list[Segmento]:
        rgb = np.ascontiguousarray(np.array(imagem.convert("RGB")))
        chave = hashlib.blake2b(rgb.tobytes(), digest_size=16).hexdigest() + f"-{rgb.shape[0]}x{rgb.shape[1]}"
        with self._lock:
            if chave in self._cache:
                self._cache.move_to_end(chave)
                self.acertos_cache += 1
                brutos = self._cache[chave]
            else:
                brutos = self._reconhecer_bruto(rgb)
                self._cache[chave] = brutos
                while len(self._cache) > TAMANHO_CACHE:
                    self._cache.popitem(last=False)
        return [Segmento(texto, x0, y0, x1, y1, pagina, conf) for texto, x0, y0, x1, y1, conf in brutos]


motor_ocr = MotorOCR()

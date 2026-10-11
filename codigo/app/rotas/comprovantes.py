"""Comprovante de pagamento (PDF ou foto): anexar, ver, remover e registrar o pagamento a partir do comprovante.

Ao anexar, o sistema lê o comprovante: marca o lançamento como pago e guarda valor pago, juros/multa e desconto.
Um comprovante enviado em Ler boletos (ou por e-mail/Telegram) é associado sozinho ao boleto ou Pix certo.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import contexto as ctx
from .. import servico_comprovante
from ..arquivos import RepositorioArquivos
from ..boleto.leitores import abrir_imagem, eh_pdf
from .comum import autor, erro
from .leitura import ler_upload, visualizar_arquivo

router = APIRouter()
TIPOS = ("boletos", "pix")


class RegistrarEntrada(BaseModel):
    aba: Literal["boletos", "pix"]
    id: int = Field(..., gt=0)
    arquivo_id: str | None = Field(None, max_length=40)
    extraido: dict = Field(default_factory=dict)


def _validar(dados: bytes) -> None:
    if eh_pdf(dados):
        return
    try:
        abrir_imagem(dados)
    except Exception as exc:
        raise erro(422, "comprovante_invalido", "Envie o comprovante em PDF ou como foto (JPG, PNG, HEIC...).") from exc


def _extraido_valido(extraido: dict) -> dict:
    """Aceita da tela só os campos do pagamento, já convertidos."""
    saida = {}
    for campo in ("valor_pago", "juros_multa", "desconto"):
        try:
            saida[campo] = round(float(extraido[campo]), 2) if extraido.get(campo) not in (None, "") else None
        except (TypeError, ValueError):
            saida[campo] = None
    saida["data_pagamento"] = extraido.get("data_pagamento") if isinstance(extraido.get("data_pagamento"), str) else None
    return saida


@router.post("/api/comprovantes/registrar")
def registrar_pagamento(entrada: RegistrarEntrada, request: Request):
    if entrada.arquivo_id and not ctx.arquivos.meta(entrada.arquivo_id):
        raise erro(404, "arquivo_nao_encontrado", "O arquivo do comprovante não está mais disponível. Envie-o de novo.")
    registro = servico_comprovante.registrar(entrada.aba, entrada.id, _extraido_valido(entrada.extraido), autor(request),
                                             entrada.arquivo_id)
    return {"registro": servico_comprovante.serializar(entrada.aba, registro),
            "pagamento": servico_comprovante.resumo_pagamento(entrada.aba, registro)}


def anexar(tipo: str, id_: int, arquivo: UploadFile, usuario: str) -> dict:
    repo = servico_comprovante.repositorio(tipo)
    registro = repo.obter(id_)
    dados = ler_upload(arquivo)
    _validar(dados)
    meta = ctx.arquivos.salvar(dados, arquivo.filename or "comprovante")
    extraido = servico_comprovante.valores_do_arquivo(dados)
    if registro.get("status") != "Pago" or (extraido and extraido.get("valor_pago") and not registro.get("valor_pago")):
        # O comprovante é deste lançamento: registra o pagamento com o que foi lido (valor pago, juros, data)
        return servico_comprovante.registrar(tipo, id_, extraido or {}, usuario, meta["id"])
    atualizado, _ = repo.atualizar(id_, {"comprovante": ctx.arquivos.caminho_relativo(meta["id"]), "comprovante_nome": meta["nome"]},
                                   usuario=usuario)
    return atualizado


for _tipo in TIPOS:
    def _rotas(tipo: str) -> None:
        @router.post(f"/api/{tipo}/{{id_}}/comprovante", name=f"anexar_comprovante_{tipo}")
        def anexar_comprovante(id_: int, request: Request, arquivo: UploadFile = File(...)):
            return servico_comprovante.serializar(tipo, anexar(tipo, id_, arquivo, autor(request)))

        @router.get(f"/api/{tipo}/{{id_}}/comprovante", name=f"ver_comprovante_{tipo}")
        def ver_comprovante(id_: int):
            arquivo_id = RepositorioArquivos.id_de_caminho(servico_comprovante.repositorio(tipo).obter(id_).get("comprovante"))
            if not arquivo_id:
                raise erro(404, "sem_comprovante", "Nenhum comprovante foi anexado.")
            return visualizar_arquivo(arquivo_id)

        @router.delete(f"/api/{tipo}/{{id_}}/comprovante", status_code=204, name=f"remover_comprovante_{tipo}")
        def remover_comprovante(id_: int, request: Request):
            repo = servico_comprovante.repositorio(tipo)
            if not repo.obter(id_).get("comprovante"):
                raise erro(404, "sem_comprovante", "Nenhum comprovante foi anexado.")
            repo.atualizar(id_, {"comprovante": "", "comprovante_nome": ""}, usuario=autor(request))
            return Response(status_code=204)

        @router.post(f"/api/{tipo}/{{id_}}/desfazer-pagamento", name=f"desfazer_pagamento_{tipo}")
        def desfazer_pagamento(id_: int, request: Request):
            """Desfaz um pagamento registrado por engano: volta para pendente e tira o comprovante."""
            return servico_comprovante.serializar(tipo, servico_comprovante.desfazer(tipo, id_, autor(request)))

    _rotas(_tipo)

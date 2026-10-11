"""Acesso aos registros (boletos ou Pix): planilha + fila de gravação (quando a planilha está aberta no Excel).

Todo o restante da aplicação (API, painel, análise, notificações) usa estas classes, então lançamentos que
ainda aguardam gravação aparecem em todos os lugares como se já estivessem na planilha.
"""

from __future__ import annotations

from .fila_gravacao import FilaGravacao
from .pix import formatar_chave
from .planilha import PlanilhaBloqueadaError, PlanilhaBoletos, RegistroNaoEncontrado


class RepositorioBoletos:
    """Repositório de uma aba da planilha (``boletos`` por padrão; ``pix`` para pagamentos por Pix)."""

    def __init__(self, planilha: PlanilhaBoletos, fila: FilaGravacao, aba: str = "boletos"):
        self.planilha = planilha
        self.fila = fila
        self.aba = aba

    # ------------------------------------------------------------------ leitura

    def garantir(self) -> None:
        self.planilha.garantir()

    def listar(self) -> list[dict]:
        return self.fila.sobrepor(self.planilha.listar(self.aba), self.aba)

    def obter(self, id_: int) -> dict:
        for registro in self.listar():
            if registro["id"] == id_:
                return registro
        raise RegistroNaoEncontrado(id_)

    def buscar_por_codigo(self, codigo_barras: str) -> list[dict]:
        if not codigo_barras:
            return []
        return [r for r in self.listar() if r.get("codigo_barras") == codigo_barras and r.get("status") != "Cancelado"]

    def nomes_por_documento(self) -> dict[str, str]:
        return self.planilha.nomes_por_documento()

    def status_gravacao(self) -> dict:
        return self.fila.status()

    # ------------------------------------------------------------------ escrita

    def _descarregar_fila(self) -> None:
        """Mantém a ordem: antes de gravar algo novo, tenta gravar o que já estava na fila."""
        if self.fila.pendentes:
            self.fila.processar()

    def adicionar_lote(self, lista: list[dict], usuario: str = "") -> tuple[list[dict], bool]:
        """Devolve (registros, ficou_pendente). Com a planilha bloqueada, os lançamentos vão para a fila.

        ``usuario`` é quem fez a alteração (vai para as colunas "Lançado por"/"Pago por" e para o Histórico).
        """
        self._descarregar_fila()
        if not self.fila.pendentes:
            try:
                return self.planilha.adicionar_lote(lista, self.aba, usuario), False
            except PlanilhaBloqueadaError:
                pass
        return [self.fila.enfileirar_adicao(dados, self.aba, usuario) for dados in lista], True

    def adicionar(self, dados: dict, usuario: str = "") -> tuple[dict, bool]:
        registros, pendente = self.adicionar_lote([dados], usuario)
        return registros[0], pendente

    def atualizar(self, id_: int, dados: dict, usuario: str = "") -> tuple[dict, bool]:
        if id_ < 0:
            self.fila.enfileirar_atualizacao(id_, dados, self.aba, usuario)
            return self.fila.registro_provisorio(id_, self.aba), True
        self._descarregar_fila()
        if not self.fila.pendentes:
            try:
                return self.planilha.atualizar(id_, dados, self.aba, usuario), False
            except PlanilhaBloqueadaError:
                pass
        self.planilha.obter(id_, self.aba)  # garante que existe
        self.fila.enfileirar_atualizacao(id_, dados, self.aba, usuario)
        return self.obter(id_), True

    def excluir(self, id_: int, usuario: str = "") -> None:
        """Exclusão exige a planilha livre (é irreversível); lançamentos pendentes são apenas cancelados."""
        if id_ < 0:
            self.fila.cancelar_provisorio(id_, self.aba)
            return
        self._descarregar_fila()
        self.planilha.excluir(id_, self.aba, usuario)


class FonteLembretes:
    """Boletos + Pix no formato usado pelas notificações de vencimento."""

    def __init__(self, boletos: RepositorioBoletos, pix: RepositorioBoletos, extras=None):
        """``extras()`` devolve outros lembretes já no formato dos alertas (ex.: cheques a depositar)."""
        self.boletos = boletos
        self.pix = pix
        self.extras = extras

    def listar(self) -> list[dict]:
        registros = list(self.boletos.listar())
        for p in self.pix.listar():
            registros.append({
                "id": f"pix-{p['id']}",
                "beneficiario": p.get("recebedor") or "Recebedor não informado",
                "vencimento": p.get("vencimento"),
                "valor": p.get("valor"),
                "status": p.get("status"),
                "numero_documento": "",
                "linha_digitavel": "",
                "tipo_pagamento": "pix",
                "chave_pix": formatar_chave(p.get("tipo_chave"), p.get("chave")),
            })
        if self.extras:
            registros += list(self.extras() or [])
        return registros

    def nomes_por_documento(self) -> dict[str, str]:
        return self.boletos.nomes_por_documento()

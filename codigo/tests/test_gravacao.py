"""Fila de gravação: planilha aberta no Excel não perde lançamentos nem alterações."""

from datetime import date

from app.fila_gravacao import FilaGravacao
from app.planilha import PlanilhaBloqueadaError, PlanilhaBoletos
from app.repositorio import RepositorioBoletos


class Trava:
    """Simula a planilha aberta no Excel enquanto ``ativa`` for verdadeiro."""

    def __init__(self, planilha: PlanilhaBoletos, monkeypatch):
        self.ativa = True
        original = planilha._verificar_gravavel

        def verificar():
            if self.ativa:
                raise PlanilhaBloqueadaError("A planilha está aberta em outro programa (ex.: Excel).")
            original()

        monkeypatch.setattr(planilha, "_verificar_gravavel", verificar)


def _montar(tmp_path):
    planilha = PlanilhaBoletos(tmp_path / "b.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    return planilha, fila, RepositorioBoletos(planilha, fila)


def test_lancamentos_e_alteracoes_aguardam_e_sao_gravados_ao_fechar_o_excel(tmp_path, monkeypatch):
    planilha, fila, repositorio = _montar(tmp_path)
    repositorio.adicionar({"beneficiario": "Já gravado", "valor": 5})
    trava = Trava(planilha, monkeypatch)

    registro, pendente = repositorio.adicionar({"beneficiario": "Novo", "valor": 10, "vencimento": date(2026, 10, 1),
                                                "codigo_barras": "123"})
    assert pendente and registro["id"] == -1 and registro["pendente_gravacao"]
    assert repositorio.buscar_por_codigo("123")[0]["id"] == -1  # duplicidade considera a fila

    repositorio.atualizar(-1, {"observacoes": "editado antes de gravar"})
    atualizado, pendente = repositorio.atualizar(1, {"status": "Pago"})
    assert pendente and atualizado["status"] == "Pago"
    assert {r["id"] for r in repositorio.listar()} == {1, -1}

    assert fila.processar()["bloqueada"] and fila.pendentes == 2
    assert FilaGravacao(planilha, tmp_path / "fila.json").pendentes == 2  # sobrevive a reinício do sistema

    trava.ativa = False
    resultado = fila.processar()
    assert resultado["gravados"] == 2 and resultado["ids"] == {-1: 2} and fila.pendentes == 0
    registros = {r["id"]: r for r in planilha.listar()}
    assert registros[1]["status"] == "Pago"
    assert registros[2]["beneficiario"] == "Novo"
    assert registros[2]["observacoes"] == "editado antes de gravar"
    assert registros[2]["vencimento"] == date(2026, 10, 1)


def test_cancelar_lancamento_que_aguarda_gravacao(tmp_path, monkeypatch):
    planilha, fila, repositorio = _montar(tmp_path)
    planilha.garantir()
    Trava(planilha, monkeypatch)
    registro, _ = repositorio.adicionar({"beneficiario": "X"})
    repositorio.excluir(registro["id"])
    assert fila.pendentes == 0 and repositorio.listar() == []

"""Transferências de clientes: a entrada da integração com a Operações (só com o token) e a tela da lista."""

import pytest
from fastapi.testclient import TestClient

from app import acesso, contexto, main, usuarios
from app.arquivos import RepositorioArquivos
from app.banco import BancoBoletos
from app.transferencias.modelos import ABAS_TRANSFERENCIAS

TOKEN = "token-falso-dos-testes"
ROTA = "/api/integracao/operacoes/notas"
PDF = b"%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
CELULAR = ("203.0.113.9", 50000)  # aparelho de fora (a Operações chega pela internet)


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    """Banco, arquivos e usuários só do teste; usuários cadastrados = a rede sempre pede login."""
    banco = BancoBoletos(tmp_path / "transferencias.db", tmp_path / "transferencias.xlsx", tmp_path / "backups",
                         abas=ABAS_TRANSFERENCIAS, centros=False, nome_backup="transferencias")
    gerenciador = usuarios.GerenciadorUsuarios(tmp_path / "usuarios.json")
    original = contexto.usuarios
    monkeypatch.setattr(contexto, "transferencias", banco)
    monkeypatch.setattr(contexto, "arquivos", RepositorioArquivos(tmp_path / "arquivos"))
    monkeypatch.setattr(contexto, "usuarios", gerenciador)
    monkeypatch.setenv("OPERACOES_TOKEN", TOKEN)
    acesso.configurar_usuarios(gerenciador)
    gerenciador.criar("Fábio", "fabio", "senha-do-dono", "administrador")
    yield gerenciador
    acesso.configurar_usuarios(original)
    banco.parar()


@pytest.fixture
def operacoes(sistema):
    with TestClient(main.app, client=CELULAR) as cliente:
        yield cliente


def _campos(**troca):
    campos = {"origem_id": "321", "nota": "6859", "pedido": "7043", "empresa": "Imapal", "valor": "1905.60",
              "material": "Brita 01", "emitida_em": "2026-10-23 14:05:00", "forma": "pix", "chave": "5" * 44}
    campos.update(troca)
    return {k: v for k, v in campos.items() if v is not None}


def _enviar(cliente, token=TOKEN, pdf=PDF, **troca):
    cabecalhos = {"Authorization": f"Bearer {token}"} if token is not None else {}
    arquivos = {"arquivo": ("NF 6859.pdf", pdf, "application/pdf")} if pdf is not None else None
    return cliente.post(ROTA, data=_campos(**troca), files=arquivos, headers=cabecalhos)


def _entrar(cliente, login, senha):
    assert cliente.post("/api/usuarios/entrar", json={"login": login, "senha": senha}).status_code == 200


# --------------------------------------------------------------------------- token


def test_sem_a_variavel_a_integracao_fica_desligada(operacoes, monkeypatch):
    monkeypatch.delenv("OPERACOES_TOKEN")
    resposta = _enviar(operacoes)
    assert resposta.status_code == 503 and resposta.json()["ok"] is False


@pytest.mark.parametrize("cabecalho", [None, "Bearer token-errado", f"Basic {TOKEN}", "Bearer ", TOKEN])
def test_token_ausente_ou_errado_recebe_401(operacoes, cabecalho):
    cabecalhos = {"Authorization": cabecalho} if cabecalho is not None else {}
    resposta = operacoes.post(ROTA, data=_campos(), headers=cabecalhos)
    assert resposta.status_code == 401 and resposta.json() == {"ok": False, "erro": "Token inválido."}
    assert contexto.transferencias.listar() == []


def test_a_excecao_do_login_vale_so_para_esta_rota(operacoes):
    """Sem login, a rede continua barrada em todo o resto, inclusive em outros métodos e caminhos parecidos."""
    cabecalho = {"Authorization": f"Bearer {TOKEN}"}
    assert operacoes.get(ROTA, headers=cabecalho).status_code == 401
    assert operacoes.post(ROTA + "/x", data=_campos(), headers=cabecalho).status_code == 401
    assert operacoes.get("/api/transferencias", headers=cabecalho).status_code == 401
    assert operacoes.get("/api/boletos", headers=cabecalho).status_code == 401


# --------------------------------------------------------------------------- campos


@pytest.mark.parametrize("troca, trecho", [
    ({"origem_id": None}, "origem_id"), ({"origem_id": "0"}, "origem_id"), ({"origem_id": "12a"}, "origem_id"),
    ({"origem_id": "-3"}, "origem_id"), ({"nota": None}, "nota"), ({"nota": "  "}, "nota"),
    ({"empresa": None}, "empresa"), ({"forma": "boleto"}, "forma"), ({"forma": None}, "forma"),
    ({"valor": "1.905,60"}, "valor"), ({"valor": "abc"}, "valor"), ({"emitida_em": "23/10/2026"}, "emitida_em"),
    ({"emitida_em": "2026-02-30"}, "emitida_em"), ({"chave": "123"}, "chave"),
])
def test_campos_obrigatorios_ou_invalidos_recebem_422(operacoes, troca, trecho):
    resposta = _enviar(operacoes, **troca)
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["ok"] is False and trecho in resposta.json()["erro"]
    assert contexto.transferencias.listar() == []


def test_arquivo_que_nao_e_pdf_recebe_422(operacoes):
    resposta = _enviar(operacoes, pdf=b"\x89PNG\r\n\x1a\n imagem")
    assert resposta.status_code == 422 and "PDF" in resposta.json()["erro"]
    grande = PDF + b"0" * (10 * 1024 * 1024)
    resposta = _enviar(operacoes, pdf=grande)
    assert resposta.status_code == 422 and "10 MB" in resposta.json()["erro"]
    assert contexto.transferencias.listar() == []


# --------------------------------------------------------------------------- criação e reenvio


def test_cria_e_reenvio_atualiza_sem_duplicar(operacoes):
    criada = _enviar(operacoes)
    assert criada.status_code == 201, criada.text
    assert criada.json() == {"ok": True, "id": 1, "situacao": "criada"}
    [linha] = contexto.transferencias.listar()
    assert linha["origem_id"] == 321 and linha["nota"] == "6859" and linha["valor"] == 1905.6
    assert linha["forma"] == "pix" and linha["status"] == "Aguardando pagamento" and linha["lancado_por"] == "Operações"
    primeiro_pdf = RepositorioArquivos.id_de_caminho(linha["arquivo"])
    assert contexto.arquivos.caminho_original(primeiro_pdf).read_bytes() == PDF

    novo_pdf = PDF + b"% corrigida\n"
    reenvio = _enviar(operacoes, pdf=novo_pdf, valor="2000.00", forma="transferencia", nota="6860")
    assert reenvio.status_code == 200, reenvio.text
    assert reenvio.json() == {"ok": True, "id": 1, "situacao": "atualizada"}
    [linha] = contexto.transferencias.listar()
    assert linha["valor"] == 2000.0 and linha["forma"] == "transferencia" and linha["nota"] == "6860"
    assert contexto.arquivos.caminho_original(RepositorioArquivos.id_de_caminho(linha["arquivo"])).read_bytes() == novo_pdf
    assert contexto.arquivos.caminho_original(primeiro_pdf) is None  # o PDF antigo não fica perdido

    sem_pdf = _enviar(operacoes, pdf=None, material="Pó de brita")  # reenvio sem PDF mantém o que já tinha
    assert sem_pdf.status_code == 200
    [linha] = contexto.transferencias.listar()
    assert linha["material"] == "Pó de brita" and linha["arquivo"]


def test_campos_opcionais_vazios(operacoes):
    resposta = _enviar(operacoes, pdf=None, valor="", chave="", pedido="", material="", emitida_em="2026-10-23")
    assert resposta.status_code == 201, resposta.text
    [linha] = contexto.transferencias.listar()
    assert linha["valor"] is None and linha["arquivo"] == "" and linha["emitida_em"] == "2026-10-23"


# --------------------------------------------------------------------------- tela


def test_lista_com_filtros_e_busca_pela_nota(sistema):
    with TestClient(main.app) as computador:
        _enviar(computador, origem_id="1", nota="100", empresa="Imapal")
        _enviar(computador, origem_id="2", nota="200", empresa="Construtora Sol", forma="transferencia")
        _enviar(computador, origem_id="3", nota="1001", empresa="Imapal")
        contexto.transferencias.atualizar(3, {"status": "Pago"})

        tudo = computador.get("/api/transferencias").json()
        assert tudo["total"] == 3 and tudo["empresas"] == ["Construtora Sol", "Imapal"]
        assert tudo["situacoes"] == ["Aguardando pagamento", "Pago"]

        def notas(**params):
            return [t["nota"] for t in computador.get("/api/transferencias", params=params).json()["transferencias"]]

        assert sorted(notas(empresa="imapal")) == ["100", "1001"]
        assert notas(situacao="Aguardando pagamento") == ["200", "100"]  # mais novas primeiro
        assert sorted(notas(q="100")) == ["100", "1001"]
        assert notas(empresa="Imapal", situacao="Pago") == ["1001"]


def test_pdf_so_para_quem_entrou_com_permissao(sistema, operacoes):
    assert _enviar(operacoes).status_code == 201
    assert _enviar(operacoes, origem_id="9", pdf=None).status_code == 201
    sistema.criar("Almir", "almir", "almir-2026", permissoes=["lancar"])
    sistema.criar("Rosa", "rosa", "rosa-2026", permissoes=["transferencias"])

    with TestClient(main.app, client=CELULAR) as celular:
        assert celular.get("/api/transferencias/1/pdf").status_code == 401  # não entrou
        assert celular.get("/api/transferencias").status_code == 401
        _entrar(celular, "almir", "almir-2026")
        negado = celular.get("/api/transferencias/1/pdf")
        assert negado.status_code == 403 and negado.json()["detail"]["permissao"] == "transferencias"
        assert celular.get("/api/transferencias").status_code == 403

    with TestClient(main.app, client=CELULAR) as celular:
        _entrar(celular, "rosa", "rosa-2026")
        pdf = celular.get("/api/transferencias/1/pdf")
        assert pdf.status_code == 200 and pdf.content == PDF
        assert pdf.headers["content-type"] == "application/pdf" and pdf.headers["content-disposition"].startswith("inline")
        assert celular.get("/api/transferencias/2/pdf").status_code == 404  # chegou sem PDF
        assert celular.get("/api/transferencias/99/pdf").status_code == 404
        assert celular.get("/api/transferencias").json()["total"] == 2

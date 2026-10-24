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


# --------------------------------------------------------------------------- CNPJ/CPF do cliente


@pytest.mark.parametrize("enviado, guardado", [("12.345.678/0001-95", "12345678000195"), ("12345678909", "12345678909"),
                                               ("", ""), (None, "")])
def test_documento_do_cliente_guardado_so_com_digitos(operacoes, enviado, guardado):
    assert _enviar(operacoes, documento=enviado).status_code == 201
    assert contexto.transferencias.listar()[0]["documento"] == guardado


@pytest.mark.parametrize("documento", ["123", "1234567890123", "123456789012345", "12A45678909"])
def test_documento_invalido_recebe_422(operacoes, documento):
    resposta = _enviar(operacoes, documento=documento)
    assert resposta.status_code == 422 and "documento" in resposta.json()["erro"]
    assert contexto.transferencias.listar() == []


# --------------------------------------------------------------------------- ligar o pagamento à nota

COMPROVANTE = """Comprovante de transferência
Pix enviado
23/10/2026 - 14:05:10
Valor
R$ 3.811,20
Origem
Nome
Construtora Sol Ltda
CNPJ
12.345.678/0001-95
Destino
Nome
Pedreira Prospera
ID da transação: E18236120202610231405s0123456789"""


def _pdf_texto(texto: str) -> bytes:
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    folha = canvas.Canvas(buffer, pagesize=A4)
    for i, linha in enumerate(texto.splitlines()):
        folha.drawString(40, 800 - 18 * i, linha)
    folha.save()
    return buffer.getvalue()


@pytest.fixture
def tela(sistema):
    """O computador principal (sem login) com três notas aguardando pagamento."""
    with TestClient(main.app) as computador:
        for origem, nota in (("1", "100"), ("2", "200"), ("3", "300")):
            assert _enviar(computador, origem_id=origem, nota=nota, valor="1905.60").status_code == 201
        yield computador


def _ler(cliente, texto=COMPROVANTE):
    resposta = cliente.post("/api/transferencias/pagamentos/ler",
                            files={"arquivo": ("comprovante.pdf", _pdf_texto(texto), "application/pdf")})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _ligar(cliente, ids, arquivo, **troca):
    corpo = {"ids": ids, "arquivo": arquivo, "valor": 3811.20, "data": "2026-10-23", "pagador": "Construtora Sol Ltda",
             "documento_pagador": "12.345.678/0001-95", "id_transacao": "E18236120202610231405s0123456789",
             "observacao": "Pago pelo sócio"}
    corpo.update(troca)
    return cliente.post("/api/transferencias/pagamentos", json=corpo)


def _linhas(cliente):
    return {t["nota"]: t for t in cliente.get("/api/transferencias").json()["transferencias"]}


def test_le_o_comprovante_sem_ligar_nada(tela):
    lido = _ler(tela)
    assert (lido["valor"], lido["data"]) == (3811.2, "2026-10-23")
    assert (lido["pagador"], lido["documento_pagador"]) == ("Construtora Sol Ltda", "12345678000195")
    assert lido["id_transacao"] == "E18236120202610231405s0123456789" and lido["ja_usado"] is None
    assert contexto.arquivos.meta(lido["arquivo"])["nome"] == "comprovante.pdf"
    assert all(t["status"] == "Aguardando pagamento" for t in _linhas(tela).values())
    foto = tela.post("/api/transferencias/pagamentos/ler", files={"arquivo": ("x.txt", b"texto qualquer", "text/plain")})
    assert foto.status_code == 422 and foto.json()["detail"]["codigo"] == "comprovante_invalido"


def test_liga_varias_notas_a_um_pagamento_e_abre_o_comprovante(tela):
    lido = _ler(tela)
    resposta = _ligar(tela, [1, 2, 2], lido["arquivo"])
    assert resposta.status_code == 201, resposta.text
    pagamento = resposta.json()["pagamento"]
    assert pagamento["id"] == 1 and pagamento["notas"] == ["100", "200"] and pagamento["valor"] == 3811.2
    assert pagamento["documento_pagador"] == "12345678000195" and pagamento["observacao"] == "Pago pelo sócio"
    assert pagamento["ligado_por"] == "Computador principal" and pagamento["comprovante"] and not pagamento["desfeito"]
    assert [t["status"] for t in resposta.json()["transferencias"]] == ["Pago", "Pago"]

    linhas = _linhas(tela)
    assert linhas["100"]["pagamento"] == linhas["200"]["pagamento"] == pagamento
    assert linhas["100"]["pagamento_id"] == 1 and linhas["300"]["pagamento"] is None
    assert linhas["300"]["status"] == "Aguardando pagamento"

    aberto = tela.get("/api/transferencias/pagamentos/1/comprovante")
    assert aberto.status_code == 200 and aberto.headers["content-type"] == "application/pdf"
    assert aberto.content.startswith(b"%PDF")
    assert tela.get("/api/transferencias/pagamentos/9/comprovante").status_code == 404


def test_liga_uma_nota(tela):
    resposta = _ligar(tela, [3], _ler(tela)["arquivo"], valor="1905.60", id_transacao="", documento_pagador="")
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["pagamento"]["notas"] == ["300"] and _linhas(tela)["300"]["status"] == "Pago"


def test_recusa_nota_paga_inexistente_e_comprovante_repetido(tela):
    arquivo = _ler(tela)["arquivo"]
    assert _ligar(tela, [1], arquivo).status_code == 201

    paga = _ligar(tela, [1, 2], arquivo, id_transacao="OUTRO123456")
    assert paga.status_code == 409 and paga.json()["detail"]["codigo"] == "nota_ja_paga"
    assert "100" in paga.json()["detail"]["mensagem"]

    repetido = _ligar(tela, [2], arquivo, id_transacao=" e18236120202610231405S0123456789 ")
    assert repetido.status_code == 409 and repetido.json()["detail"]["codigo"] == "comprovante_repetido"
    assert _ler(tela)["ja_usado"] == 1  # a tela já avisa ao ler o mesmo comprovante

    sumida = _ligar(tela, [2, 99], arquivo, id_transacao="OUTRO123456")
    assert sumida.status_code == 404 and sumida.json()["detail"]["codigo"] == "nota_nao_encontrada"

    sem_arquivo = _ligar(tela, [2], "0" * 32, id_transacao="OUTRO123456")
    assert sem_arquivo.status_code == 404 and sem_arquivo.json()["detail"]["codigo"] == "arquivo_nao_encontrado"

    for troca, codigo in (({"valor": 0}, "valor_invalido"), ({"valor": "abc"}, "valor_invalido"),
                          ({"data": "23/10/2026"}, "data_invalida"), ({"documento_pagador": "123"}, "documento_invalido")):
        invalido = _ligar(tela, [2], arquivo, id_transacao="OUTRO123456", **troca)
        assert invalido.status_code == 422 and invalido.json()["detail"]["codigo"] == codigo
    assert _ligar(tela, [], arquivo).status_code == 422
    assert _linhas(tela)["200"]["status"] == "Aguardando pagamento"  # nada pela metade
    assert len(contexto.transferencias.listar("pagamentos")) == 1


def test_desfazer_volta_as_notas_e_guarda_o_pagamento(tela):
    arquivo = _ler(tela)["arquivo"]
    assert _ligar(tela, [1, 2], arquivo).status_code == 201

    desfeito = tela.post("/api/transferencias/pagamentos/1/desfazer")
    assert desfeito.status_code == 200, desfeito.text
    assert desfeito.json()["pagamento"]["desfeito"] is True
    assert [t["status"] for t in desfeito.json()["transferencias"]] == ["Aguardando pagamento"] * 2
    linhas = _linhas(tela)
    assert linhas["100"]["pagamento"] is None and linhas["100"]["pagamento_id"] is None

    [guardado] = contexto.transferencias.listar("pagamentos")
    assert guardado["status"] == "Desfeito" and guardado["desfeito_por"] == "Computador principal"
    assert tela.get("/api/transferencias/pagamentos/1/comprovante").status_code == 200  # o comprovante fica no histórico
    de_novo = tela.post("/api/transferencias/pagamentos/1/desfazer")
    assert de_novo.status_code == 409 and de_novo.json()["detail"]["codigo"] == "pagamento_ja_desfeito"
    assert tela.post("/api/transferencias/pagamentos/9/desfazer").status_code == 404

    # o mesmo comprovante pode ser ligado de novo, agora às notas certas
    religado = _ligar(tela, [2, 3], arquivo)
    assert religado.status_code == 201 and religado.json()["pagamento"]["id"] == 2


def test_reenvio_da_operacoes_nao_muda_o_pagamento(tela):
    assert _ligar(tela, [1], _ler(tela)["arquivo"]).status_code == 201
    reenvio = _enviar(tela, origem_id="1", nota="100", valor="2000.00", documento="12345678909")
    assert reenvio.status_code == 200
    linha = _linhas(tela)["100"]
    assert linha["status"] == "Pago" and linha["pagamento_id"] == 1 and linha["documento"] == "12345678909"


def test_ligar_so_com_login_e_permissao(sistema, tela):
    arquivo = _ler(tela)["arquivo"]
    sistema.criar("Almir", "almir", "almir-2026", permissoes=["lancar", "pagar"])
    sistema.criar("Rosa", "rosa", "rosa-2026", permissoes=["transferencias"])
    pdf = {"arquivo": ("c.pdf", _pdf_texto(COMPROVANTE), "application/pdf")}

    with TestClient(main.app, client=CELULAR) as celular:
        assert celular.post("/api/transferencias/pagamentos/ler", files=pdf).status_code == 401
        assert _ligar(celular, [1], arquivo).status_code == 401
        _entrar(celular, "almir", "almir-2026")
        for resposta in (celular.post("/api/transferencias/pagamentos/ler", files=pdf), _ligar(celular, [1], arquivo),
                         celular.post("/api/transferencias/pagamentos/1/desfazer"),
                         celular.get("/api/transferencias/pagamentos/1/comprovante")):
            assert resposta.status_code == 403 and resposta.json()["detail"]["permissao"] == "transferencias"

    with TestClient(main.app, client=CELULAR) as celular:
        _entrar(celular, "rosa", "rosa-2026")
        ligado = _ligar(celular, [1], arquivo)
        assert ligado.status_code == 201 and ligado.json()["pagamento"]["ligado_por"] == "Rosa"
        assert celular.get("/api/transferencias/pagamentos/1/comprovante").status_code == 200
        assert celular.post("/api/transferencias/pagamentos/1/desfazer").status_code == 200
    assert len(contexto.transferencias.listar("pagamentos")) == 1

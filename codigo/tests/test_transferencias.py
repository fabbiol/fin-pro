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
                                               ("12.ABC.345/01DE-35", "12ABC34501DE35"), ("", ""), (None, "")])
def test_documento_do_cliente_guardado_so_com_digitos(operacoes, enviado, guardado):
    assert _enviar(operacoes, documento=enviado).status_code == 201
    assert contexto.transferencias.listar()[0]["documento"] == guardado


@pytest.mark.parametrize("documento", ["123", "1234567890123", "123456789012345", "12A45678909", "12ABC34501DEAB"])
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


# --------------------------------------------------------------------------- Pix recebidos no Bradesco (banco simulado)

import base64  # noqa: E402
import os  # noqa: E402
import ssl  # noqa: E402
from datetime import date, datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import httpx  # noqa: E402

from app.transferencias import bradesco, servico  # noqa: E402

CLIENT_ID, CLIENT_SECRET = "id-falso-dos-testes", "segredo-falso-dos-testes"
SOL, LUA = "12345678000195", "98765432000110"  # CNPJs só de teste
E2E = [f"E00000000202610231405{i:011d}" for i in range(10)]
VARIAVEIS_BRADESCO = ("AMBIENTE", "CLIENT_ID", "CLIENT_SECRET", "CERT", "KEY", "HOST", "TOKEN_PATH")


def _pix_banco(e2e, valor, documento=SOL, nome="Construtora Sol Ltda", horario="2026-10-23T18:05:10.123Z", devolvido=None):
    """Um Pix como a API do Bradesco devolve (padrão do Banco Central)."""
    item = {"endToEndId": e2e, "txid": "", "valor": f"{valor:.2f}", "horario": horario, "infoPagador": "NF"}
    if documento:
        item["pagador"] = {"cnpj" if len(documento) == 14 else "cpf": documento, "nome": nome}
    if devolvido:
        item["devolucoes"] = [{"id": "D1", "valor": f"{devolvido:.2f}", "status": "DEVOLVIDO"}]
    return item


class BancoFalso:
    """Simula o Bradesco: o token (confere o Basic com o Client ID e o Client Secret) e o GET /v2/pix com páginas."""

    def __init__(self):
        self.pix, self.por_pagina, self.tokens = [], 100, 0
        self.consultas, self.hosts, self.erro_pix = [], set(), None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.hosts.add(request.url.host)
        if request.url.path in ("/auth/server/oauth/token", "/v2/oauth/token"):
            esperado = "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
            if request.method != "POST" or request.headers.get("authorization") != esperado:
                return httpx.Response(401, json={"error": "invalid_client", "error_description": "Client inválido"})
            assert request.content == b"grant_type=client_credentials"
            self.tokens += 1
            return httpx.Response(200, json={"access_token": f"token-{self.tokens}", "token_type": "Bearer", "expires_in": 3600})
        if request.url.path == "/v2/pix":
            if request.headers.get("authorization") != f"Bearer token-{self.tokens}":
                return httpx.Response(401, json={"mensagem": "Token expirado"})
            if self.erro_pix is not None:
                return self.erro_pix
            parametros = dict(request.url.params)
            self.consultas.append(parametros)
            pagina = int(parametros.get("paginacao.paginaAtual", 0))
            paginas = max(1, -(-len(self.pix) // self.por_pagina))
            return httpx.Response(200, json={
                "parametros": {"inicio": parametros["inicio"], "fim": parametros["fim"],
                               "paginacao": {"paginaAtual": pagina, "itensPorPagina": self.por_pagina,
                                             "quantidadeDePaginas": paginas, "quantidadeTotalDeItens": len(self.pix)}},
                "pix": self.pix[pagina * self.por_pagina:(pagina + 1) * self.por_pagina]})
        return httpx.Response(404)


def _ligar_bradesco(monkeypatch, pasta, **troca):
    for nome in VARIAVEIS_BRADESCO:
        monkeypatch.delenv(f"BRADESCO_{nome}", raising=False)
    for nome in ("cert", "key"):
        (pasta / f"{nome}.pem").write_text("arquivo falso dos testes")
    variaveis = {"CLIENT_ID": CLIENT_ID, "CLIENT_SECRET": CLIENT_SECRET, "CERT": str(pasta / "cert.pem"),
                 "KEY": str(pasta / "key.pem"), **troca}
    for nome, valor in variaveis.items():
        monkeypatch.setenv(f"BRADESCO_{nome}", valor)


@pytest.fixture
def banco_pix(sistema, tmp_path, monkeypatch):
    """Credenciais falsas e o Bradesco simulado no lugar da rede; token e última consulta zerados."""
    _ligar_bradesco(monkeypatch, tmp_path)
    falso = BancoFalso()
    monkeypatch.setattr(bradesco, "_transporte", httpx.MockTransport(falso))
    monkeypatch.setattr(bradesco, "_tokens", {})
    monkeypatch.setattr(servico, "_consulta", None)
    return falso


def _consultar(cliente, inicio="2026-10-20", fim="2026-10-23"):
    resposta = cliente.post("/api/transferencias/bradesco/consultar", json={"inicio": inicio, "fim": fim})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["consulta"]


def _ligar_pix(cliente, ids, pix, **extra):
    return cliente.post("/api/transferencias/pagamentos/pix", json={"ids": ids, "pix": pix, **extra})


# ---- a conciliação (função pura: Pix + notas aguardando -> sugestões)


def _p(i, valor, documento=SOL, **extra):
    return bradesco.normalizar(_pix_banco(E2E[i], valor, documento, **extra))


def _n(id_, valor, documento=SOL):
    return {"id": id_, "nota": str(100 * id_), "empresa": "Cliente", "documento": documento, "valor": valor,
            "emitida_em": f"2026-10-{10 + id_:02d}", "forma": "pix"}


def _grupos(resultado):
    return sorted((tuple(sorted(E2E.index(p["e2e"]) for p in s["pix"])), tuple(n["id"] for n in s["notas"]))
                  for s in resultado["sugestoes"])


def test_conciliacao_acha_um_e_varios_pix_para_uma_e_varias_notas():
    a, b, c, d = "11111111000191", "22222222000191", "33333333000191", "44444444000191"
    pix = [_p(0, 1905.60, a), _p(1, 3811.20, b), _p(2, 1000.00, c), _p(3, 905.60, c), _p(4, 500, d), _p(5, 700, d)]
    notas = [_n(1, 1905.60, a), _n(2, 1905.60, b), _n(3, 1905.60, b), _n(4, 1905.60, c), _n(5, 600, d), _n(6, 600, d)]
    resultado = servico.conciliar(pix, notas, {})
    assert _grupos(resultado) == [((0,), (1,)),  # 1 Pix -> 1 nota
                                  ((1,), (2, 3)),  # 1 Pix -> 2 notas
                                  ((2, 3), (4,)),  # 2 Pix -> 1 nota
                                  ((4, 5), (5, 6))]  # 2 Pix -> 2 notas (a soma fecha)
    assert [s["valor"] for s in resultado["sugestoes"]] == [1905.6, 3811.2, 1905.6, 1200.0]
    assert resultado["conferir"] == resultado["sem_nota"] == resultado["ligados"] == []


def test_conciliacao_sem_correspondencia_exata_fica_para_conferir():
    matriz, filial, outro = "88888888000191", "88888888000272", "55555555000191"
    pix = [_p(0, 1905.60), _p(1, 1905.60),  # dois Pix iguais e uma nota: qual paga?
           _p(2, 500, LUA),  # o CNPJ bate, o valor não
           _p(3, 800, matriz),  # mesma empresa, outra filial
           _p(4, 300, ""),  # Pix sem o CNPJ/CPF de quem pagou
           _p(5, 250, outro),  # a nota não tem o CNPJ/CPF
           _p(6, 777, "12345678909"),  # valor bate com nota de outro cliente
           _p(7, 999, outro),  # nada parecido
           _p(8, 1000, devolvido=1000)]  # devolvido ao pagador
    notas = [_n(1, 1905.60), _n(2, 450, LUA), _n(3, 800, filial), _n(4, 300, "66666666000191"), _n(5, 250, ""),
             _n(6, 777, "77777777000191")]
    resultado = servico.conciliar(pix, notas, {})
    assert resultado["sugestoes"] == []
    conferir = {E2E.index(c["pix"]["e2e"]): (c["motivo"], [n["id"] for n in c["candidatas"]]) for c in resultado["conferir"]}
    assert conferir[0][1] == conferir[1][1] == [1] and "mesmo valor" in conferir[0][0]
    assert conferir[2] == ("O CNPJ/CPF bate com notas em aberto, mas o valor não fecha certinho.", [2])
    assert conferir[3] == ("Mesma empresa (raiz do CNPJ), mas outra filial.", [3])
    assert conferir[4] == ("O Pix veio sem o CNPJ/CPF de quem pagou; o valor bate.", [4])
    assert conferir[5] == ("O valor bate, mas a nota não tem o CNPJ/CPF do cliente.", [5])
    assert conferir[6] == ("O valor bate, mas quem pagou tem outro CNPJ/CPF.", [6])
    assert conferir[8] == ("Devolvido ao pagador: não paga nenhuma nota.", [])
    assert [p["e2e"] for p in resultado["sem_nota"]] == [E2E[7]]


def test_conciliacao_nao_sugere_pix_ja_ligado_e_usa_o_que_sobrou_da_devolucao():
    pix = [_p(0, 100), _p(1, 300, devolvido=100)]
    resultado = servico.conciliar(pix, [_n(1, 100), _n(2, 200)], {E2E[0].casefold(): 7})
    assert [(p["e2e"], p["pagamento_id"]) for p in resultado["ligados"]] == [(E2E[0], 7)]
    assert resultado["sugestoes"] == []  # o Pix com devolução não é sugerido sozinho
    [conferir] = resultado["conferir"]
    assert conferir["motivo"].startswith("Teve devolução") and [n["id"] for n in conferir["candidatas"]] == [2, 1]


# ---- o cliente da API (token, certificado, páginas, erros)


def test_sem_as_variaveis_a_consulta_fica_desligada_e_explica(sistema, tmp_path, monkeypatch):
    for nome in VARIAVEIS_BRADESCO:
        monkeypatch.delenv(f"BRADESCO_{nome}", raising=False)
    with TestClient(main.app) as computador:
        situacao = computador.get("/api/transferencias/bradesco").json()
        assert situacao["ligado"] is False and situacao["consulta"] is None
        assert "BRADESCO_CLIENT_ID" in situacao["motivo"] and "EasyPanel" in situacao["motivo"]
        desligada = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": "2026-10-20", "fim": "2026-10-23"})
        assert desligada.status_code == 503 and desligada.json()["detail"]["codigo"] == "bradesco_desligado"

        _ligar_bradesco(monkeypatch, tmp_path, CERT=str(tmp_path / "nao-existe.crt"))
        motivo = computador.get("/api/transferencias/bradesco").json()["motivo"]
        assert "BRADESCO_CERT" in motivo and "-----BEGIN" in motivo and CLIENT_SECRET not in motivo
        assert "nao-existe.crt" not in motivo  # o valor da variável nunca entra na mensagem

        monkeypatch.setenv("BRADESCO_AMBIENTE", "homologacao")
        assert "BRADESCO_AMBIENTE" in computador.get("/api/transferencias/bradesco").json()["motivo"]
        assert computador.get("/api/transferencias").status_code == 200  # o resto da tela continua funcionando


def test_certificado_que_nao_abre_explica_sem_mostrar_segredo(sistema, tmp_path, monkeypatch):
    _ligar_bradesco(monkeypatch, tmp_path)
    monkeypatch.setattr(bradesco, "_transporte", None)  # caminho real: o certificado é lido antes de qualquer conexão
    with TestClient(main.app) as computador:
        situacao = computador.get("/api/transferencias/bradesco").json()
        assert situacao["ligado"] is True and situacao["ambiente"] == "sandbox"
        resposta = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": "2024-10-02", "fim": "2024-10-03"})
    assert resposta.status_code == 502 and resposta.json()["detail"]["codigo"] == "bradesco_falhou"
    assert "certificado" in resposta.json()["detail"]["mensagem"] and CLIENT_SECRET not in resposta.text


# Texto no formato PEM, só para os testes (não é um certificado nem uma chave de verdade)
CORPO = "QUJD" * 40
CERT_PEM = f"-----BEGIN CERTIFICATE-----\n{CORPO[:64]}\n{CORPO[64:128]}\n{CORPO[128:]}\n-----END CERTIFICATE-----\n"
CHAVE_PEM = CERT_PEM.replace("CERTIFICATE", "PRIVATE KEY")


@pytest.mark.parametrize("colado", [CERT_PEM, CERT_PEM.replace("\n", "\r\n"), CERT_PEM.replace("\n", " "),
                                    CERT_PEM.replace("\n", ""), CERT_PEM.replace("\n", "\\n"), f"'{CERT_PEM}'",
                                    f"Bag Attributes\n    localKeyID: 01\n{CERT_PEM}"])
def test_texto_colado_no_easypanel_volta_ao_formato_pem(colado):
    """O EasyPanel pode juntar as linhas, trocar por \\n ou deixar as aspas: o PEM é refeito do mesmo jeito."""
    assert bradesco.pem(colado) == CERT_PEM
    assert bradesco.pem(f"{CERT_PEM} {CERT_PEM}") == CERT_PEM * 2  # certificado com a cadeia
    assert bradesco.pem("-----BEGIN CERTIFICATE----- sem o fim") == ""


def test_certificado_e_chave_colados_no_ambiente(monkeypatch):
    for nome in VARIAVEIS_BRADESCO:
        monkeypatch.delenv(f"BRADESCO_{nome}", raising=False)
    monkeypatch.setenv("BRADESCO_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("BRADESCO_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setenv("BRADESCO_CERT", CERT_PEM.replace("\n", " "))  # o EasyPanel juntou as linhas
    monkeypatch.setenv("BRADESCO_KEY", CHAVE_PEM)
    cfg, motivo = bradesco.configuracao()
    assert motivo == "" and (cfg.cert, cfg.key) == (CERT_PEM, CHAVE_PEM)
    assert CORPO not in repr(cfg) and CLIENT_SECRET not in repr(cfg)

    lidos = {}

    def carregar(contexto, certfile, keyfile=None, password=None):
        for nome, caminho in (("cert", certfile), ("key", keyfile)):
            lidos[nome] = (Path(caminho).read_text(), Path(caminho).stat().st_mode & 0o777)
        lidos["pasta"], lidos["senha"] = Path(certfile).parent, password()

    monkeypatch.setattr(ssl.SSLContext, "load_cert_chain", carregar)
    monkeypatch.setattr(bradesco, "_transporte", None)
    bradesco._cliente(cfg).close()
    assert (lidos["cert"][0], lidos["key"][0], lidos["senha"]) == (CERT_PEM, CHAVE_PEM, b"")
    if os.name != "nt":  # no Windows não há permissão de arquivo nesse formato
        assert lidos["cert"][1] == lidos["key"][1] == 0o600
    assert not lidos["pasta"].exists()  # o arquivo temporário some logo depois de carregar

    monkeypatch.setenv("BRADESCO_KEY", CHAVE_PEM[:60])  # colou pela metade
    cfg, motivo = bradesco.configuracao()
    assert cfg is None and "BRADESCO_KEY" in motivo and "a chave inteira" in motivo
    assert CORPO[:20] not in motivo  # o que foi colado nunca aparece na tela


def test_consulta_pede_o_token_uma_vez_e_le_todas_as_paginas(banco_pix):
    banco_pix.por_pagina = 2
    banco_pix.pix = [_pix_banco(E2E[i], 10 + i) for i in range(3)]
    with TestClient(main.app) as computador:
        situacao = computador.get("/api/transferencias/bradesco").json()
        assert situacao["ligado"] and situacao["ambiente_nome"] == "Sandbox (teste)"
        assert (situacao["inicio"], situacao["fim"]) == ("2024-10-02", "2024-10-03")  # dias com Pix de exemplo no sandbox
        consulta = _consultar(computador)
        assert consulta["total"] == 3 and len(consulta["sem_nota"]) == 3
        _consultar(computador)
    assert banco_pix.tokens == 1 and banco_pix.hosts == {"openapisandbox.prebanco.com.br"}
    primeira, segunda = banco_pix.consultas[:2]
    assert set(primeira) == {"inicio", "fim"}  # a primeira página vai como no projeto de referência
    assert segunda["paginacao.paginaAtual"] == "1" and segunda["paginacao.itensPorPagina"] == "2"
    inicio = datetime.fromisoformat(primeira["inicio"].replace("Z", "+00:00"))
    assert primeira["inicio"].endswith(".000Z") and inicio == datetime(2026, 10, 20).astimezone().astimezone(timezone.utc)
    horario = consulta["sem_nota"][0]["horario"]  # horário do Pix no fuso do sistema
    assert horario == datetime(2026, 10, 23, 18, 5, 10, tzinfo=timezone.utc).astimezone().replace(tzinfo=None).isoformat()


def test_token_recusado_pede_outro_uma_vez(banco_pix):
    bradesco._tokens[("openapisandbox.prebanco.com.br", CLIENT_ID)] = ("token-velho", float("inf"))
    with TestClient(main.app) as computador:
        assert _consultar(computador)["total"] == 0
    assert banco_pix.tokens == 1


def test_producao_usa_o_host_e_o_token_de_producao(banco_pix, monkeypatch):
    monkeypatch.setenv("BRADESCO_AMBIENTE", "producao")
    with TestClient(main.app) as computador:
        situacao = computador.get("/api/transferencias/bradesco").json()
        assert situacao["ambiente_nome"] == "Produção" and situacao["fim"] == date.today().isoformat()
        _consultar(computador)
    assert banco_pix.hosts == {"qrpix.bradesco.com.br"}


@pytest.mark.parametrize("periodo, codigo", [(("2026-10-23", "2026-10-20"), "periodo_invalido"),
                                             (("2026-09-01", "2026-10-23"), "periodo_longo"),
                                             (("2999-01-01", "2999-01-02"), "periodo_invalido"),
                                             (("23/10/2026", "2026-10-23"), "data_invalida")])
def test_periodo_invalido_recebe_422(banco_pix, periodo, codigo):
    with TestClient(main.app) as computador:
        inicio, fim = periodo
        resposta = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": inicio, "fim": fim})
    assert resposta.status_code == 422 and resposta.json()["detail"]["codigo"] == codigo
    assert banco_pix.consultas == []


def test_erros_do_banco_viram_mensagem_sem_o_segredo(banco_pix, monkeypatch):
    with TestClient(main.app) as computador:
        monkeypatch.setenv("BRADESCO_CLIENT_SECRET", "segredo-errado-dos-testes")
        recusado = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": "2026-10-20", "fim": "2026-10-23"})
        assert recusado.status_code == 502 and "recusou o Client ID e o Client Secret" in recusado.json()["detail"]["mensagem"]
        assert "segredo-errado" not in recusado.text

        monkeypatch.setenv("BRADESCO_CLIENT_SECRET", CLIENT_SECRET)
        banco_pix.erro_pix = httpx.Response(500, json={"mensagem": f"Falha interna {CLIENT_SECRET}"})
        falhou = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": "2026-10-20", "fim": "2026-10-23"})
        mensagem = falhou.json()["detail"]["mensagem"]
        assert falhou.status_code == 502 and "HTTP 500" in mensagem and "[oculto]" in mensagem
        assert CLIENT_SECRET not in falhou.text

        def sem_rede(request):
            raise httpx.ConnectError("sem rede", request=request)

        monkeypatch.setattr(bradesco, "_transporte", httpx.MockTransport(sem_rede))
        fora = computador.post("/api/transferencias/bradesco/consultar", json={"inicio": "2026-10-20", "fim": "2026-10-23"})
        assert fora.status_code == 502 and "Não foi possível falar com o Bradesco" in fora.json()["detail"]["mensagem"]
        assert computador.get("/api/transferencias/bradesco").json()["consulta"] is None  # nada pela metade


# ---- confirmar: o Pix vira o pagamento da nota (com um clique), sem pagar duas vezes


@pytest.fixture
def notas_e_pix(banco_pix):
    """Três notas aguardando e os Pix do Bradesco: um bate com a nota 100, dois somam a 200, um é de outro CNPJ."""
    with TestClient(main.app) as computador:
        for origem, nota, valor, documento in (("1", "100", "1905.60", SOL), ("2", "200", "1000.00", SOL),
                                               ("3", "300", "2000.00", LUA)):
            assert _enviar(computador, origem_id=origem, nota=nota, valor=valor, documento=documento).status_code == 201
        banco_pix.pix = [_pix_banco(E2E[1], 1905.60), _pix_banco(E2E[2], 600, horario="2026-10-24T02:30:00Z"),
                         _pix_banco(E2E[3], 400), _pix_banco(E2E[4], 2000, "11222333000181", "Outro Pagador")]
        yield computador


def test_mostra_as_sugestoes_e_nada_vira_pago_sozinho(notas_e_pix):
    consulta = _consultar(notas_e_pix)
    assert _grupos(consulta) == [((1,), (1,)), ((2, 3), (2,))]
    [conferir] = consulta["conferir"]
    assert conferir["pix"]["e2e"] == E2E[4] and [n["nota"] for n in conferir["candidatas"]] == ["300"]
    assert all(t["status"] == "Aguardando pagamento" for t in _linhas(notas_e_pix).values())
    assert contexto.transferencias.listar("pagamentos") == []
    assert notas_e_pix.get("/api/transferencias/bradesco").json()["consulta"] == consulta  # a última consulta fica na tela


def test_confirma_a_sugestao_e_o_pix_vira_o_pagamento(notas_e_pix):
    _consultar(notas_e_pix)
    resposta = _ligar_pix(notas_e_pix, [1], [E2E[1]])
    assert resposta.status_code == 201, resposta.text
    pagamento = resposta.json()["pagamento"]
    assert pagamento["origem"] == "API Pix Bradesco" and pagamento["id_transacao"] == E2E[1]
    dia = datetime(2026, 10, 23, 18, 5, 10, tzinfo=timezone.utc).astimezone().date().isoformat()  # no fuso do sistema
    assert (pagamento["valor"], pagamento["data"], pagamento["pagador"]) == (1905.6, dia, "Construtora Sol Ltda")
    assert pagamento["documento_pagador"] == SOL and pagamento["comprovante"] is False and pagamento["notas"] == ["100"]
    assert _linhas(notas_e_pix)["100"]["status"] == "Pago"

    # vários Pix numa nota: os endToEndId ficam juntos no ID da transação; a data é a do último Pix
    varios = _ligar_pix(notas_e_pix, [2], [E2E[2], E2E[3]], observacao="Pagou em duas vezes")
    assert varios.status_code == 201, varios.text
    pagamento = varios.json()["pagamento"]
    assert pagamento["id_transacao"] == f"{E2E[2]}, {E2E[3]}" and pagamento["valor"] == 1000.0
    assert pagamento["observacao"] == "Pagou em duas vezes"
    assert pagamento["data"] == datetime(2026, 10, 24, 2, 30, tzinfo=timezone.utc).astimezone().date().isoformat()
    [guardado] = [p for p in contexto.transferencias.listar("pagamentos") if p["id"] == 2]
    assert guardado["origem"] == "API Pix Bradesco" and guardado["comprovante"] == ""

    consulta = notas_e_pix.get("/api/transferencias/bradesco").json()["consulta"]
    assert consulta["sugestoes"] == [] and [(p["e2e"], p["pagamento_id"]) for p in consulta["ligados"]] == [
        (E2E[1], 1), (E2E[3], 2), (E2E[2], 2)]

    # o mesmo Pix não paga outra nota
    repetido = _ligar_pix(notas_e_pix, [3], [E2E[1]])
    assert repetido.status_code == 409 and repetido.json()["detail"]["codigo"] == "comprovante_repetido"
    assert "Este Pix" in repetido.json()["detail"]["mensagem"] and _linhas(notas_e_pix)["300"]["status"] == "Aguardando pagamento"

    # o caso de conferir: a pessoa decide e liga mesmo com outro CNPJ
    assert _ligar_pix(notas_e_pix, [3], [E2E[4]]).status_code == 201


def test_pix_fora_da_consulta_devolvido_ou_nota_paga_e_recusado(notas_e_pix, banco_pix):
    banco_pix.pix.append(_pix_banco(E2E[5], 300, devolvido=300))
    _consultar(notas_e_pix)
    fora = _ligar_pix(notas_e_pix, [1], ["E99999999202610231405999999999"])
    assert fora.status_code == 409 and fora.json()["detail"]["codigo"] == "pix_nao_consultado"
    devolvido = _ligar_pix(notas_e_pix, [1], [E2E[5]])
    assert devolvido.status_code == 409 and devolvido.json()["detail"]["codigo"] == "pix_devolvido"
    assert _ligar_pix(notas_e_pix, [1], []).status_code == 422
    assert _ligar_pix(notas_e_pix, [], [E2E[1]]).status_code == 422
    # valor e pagador vêm do banco: o que a tela mandar a mais é ignorado
    assert _ligar_pix(notas_e_pix, [1], [E2E[1]], valor=1, pagador="Outro").json()["pagamento"]["valor"] == 1905.6
    pago = _ligar_pix(notas_e_pix, [1], [E2E[2]])
    assert pago.status_code == 409 and pago.json()["detail"]["codigo"] == "nota_ja_paga"


def test_o_mesmo_pix_nao_paga_pela_api_e_pelo_comprovante(notas_e_pix, banco_pix):
    id_comprovante = "E18236120202610231405s0123456789"  # o ID que está no comprovante dos testes
    banco_pix.pix = [_pix_banco(id_comprovante.upper(), 3811.20), _pix_banco(E2E[1], 1905.60)]
    _consultar(notas_e_pix)
    assert _ligar_pix(notas_e_pix, [1], [E2E[1]]).status_code == 201

    # comprovante enviado à mão com o mesmo ID de um Pix já confirmado pela API
    lido = _ler(notas_e_pix, COMPROVANTE.replace(id_comprovante, E2E[1]))
    assert lido["ja_usado"] == 1
    manual = _ligar(notas_e_pix, [2], lido["arquivo"], id_transacao=E2E[1])
    assert manual.status_code == 409 and manual.json()["detail"]["codigo"] == "comprovante_repetido"

    # e o contrário: ligado à mão pelo comprovante, o Pix aparece como já ligado e a API não liga de novo
    assert _ligar(notas_e_pix, [2], _ler(notas_e_pix)["arquivo"]).status_code == 201
    consulta = notas_e_pix.get("/api/transferencias/bradesco").json()["consulta"]
    assert [(p["e2e"], p["pagamento_id"]) for p in consulta["ligados"]] == [(E2E[1], 1), (id_comprovante.upper(), 2)]
    assert _ligar_pix(notas_e_pix, [3], [id_comprovante.upper()]).status_code == 409


def test_desfazer_devolve_o_pix_para_as_sugestoes(notas_e_pix):
    _consultar(notas_e_pix)
    assert _ligar_pix(notas_e_pix, [2], [E2E[2], E2E[3]]).status_code == 201
    assert notas_e_pix.post("/api/transferencias/pagamentos/1/desfazer").status_code == 200
    consulta = notas_e_pix.get("/api/transferencias/bradesco").json()["consulta"]
    assert _grupos(consulta) == [((1,), (1,)), ((2, 3), (2,))] and consulta["ligados"] == []
    assert _ligar_pix(notas_e_pix, [2], [E2E[2], E2E[3]]).status_code == 201


def test_bradesco_so_com_login_e_permissao(sistema, notas_e_pix):
    _consultar(notas_e_pix)
    sistema.criar("Almir", "almir", "almir-2026", permissoes=["lancar", "pagar"])
    rotas = (("get", "/api/transferencias/bradesco", None),
             ("post", "/api/transferencias/bradesco/consultar", {"inicio": "2026-10-20", "fim": "2026-10-23"}),
             ("post", "/api/transferencias/pagamentos/pix", {"ids": [1], "pix": [E2E[1]]}))
    with TestClient(main.app, client=CELULAR) as celular:
        for metodo, rota, corpo in rotas:
            assert getattr(celular, metodo)(rota, **({"json": corpo} if corpo else {})).status_code == 401
        _entrar(celular, "almir", "almir-2026")
        for metodo, rota, corpo in rotas:
            negado = getattr(celular, metodo)(rota, **({"json": corpo} if corpo else {}))
            assert negado.status_code == 403 and negado.json()["detail"]["permissao"] == "transferencias"
    assert _linhas(notas_e_pix)["100"]["status"] == "Aguardando pagamento"


# --------------------------------------------------------------------------- nota paga em mais de uma forma

PIX_E_CARTAO = '[{"forma": "pix", "valor": "1000.00"}, {"forma": "cartao", "valor": "905.60"}]'


def test_nota_com_pix_e_cartao_espera_so_o_pix(operacoes):
    assert _enviar(operacoes, pagamentos=PIX_E_CARTAO).status_code == 201
    [registro] = contexto.transferencias.listar()
    assert registro["formas"] == "Pix R$ 1.000,00 + Cartão R$ 905,60" and registro["valor_receber"] == 1000.0
    assert registro["valor"] == 1905.6
    assert _enviar(operacoes).status_code == 200  # reenvio já com uma forma só: volta a esperar a nota toda
    [registro] = contexto.transferencias.listar()
    assert registro["formas"] == "" and not registro["valor_receber"]


@pytest.mark.parametrize("pagamentos, trecho", [
    ('[{"forma": "pix", "valor": "1000.00"}, {"forma": "cartao", "valor": "900.00"}]', "não bate"),
    ('[{"forma": "dinheiro", "valor": "1000.00"}, {"forma": "cartao", "valor": "905.60"}]', "Pix ou TED"),
    ('[{"forma": "pix", "valor": "1000.00"}, {"forma": "pix", "valor": "905.60"}]', "duas vezes"),
    ('[{"forma": "pix", "valor": "1905.60"}]', "de 2 a 4"),
    ('[{"forma": "vale", "valor": "1000.00"}, {"forma": "pix", "valor": "905.60"}]', "desconhecida"),
    ("pix e cartão", "lista JSON"),
])
def test_formas_de_pagamento_invalidas_recebem_422(operacoes, pagamentos, trecho):
    resposta = _enviar(operacoes, pagamentos=pagamentos)
    assert resposta.status_code == 422 and trecho in resposta.json()["erro"], resposta.json()
    assert contexto.transferencias.listar() == []


def test_conciliacao_procura_so_a_parte_em_pix():
    nota = {**_n(1, 1905.60), "formas": "Pix R$ 1.000,00 + Cartão R$ 905,60", "valor_receber": 1000.0}
    resultado = servico.conciliar([_p(0, 1000.00)], [nota], {})
    assert _grupos(resultado) == [((0,), (1,))] and resultado["sugestoes"][0]["notas"][0]["valor_nota"] == 1905.6


def test_comprovante_do_cartao_fica_guardado_na_nota(tela):
    assert _enviar(tela, origem_id="9", nota="900", pagamentos=PIX_E_CARTAO).status_code == 201
    nota = _linhas(tela)["900"]
    assert tela.get(f"/api/transferencias/{nota['id']}/cartao").status_code == 404
    resposta = tela.post(f"/api/transferencias/{nota['id']}/cartao", files={"arquivo": ("cartao.pdf", _pdf_texto("Cartao de credito"), "application/pdf")})
    assert resposta.status_code == 200, resposta.text
    nota = _linhas(tela)["900"]
    assert nota["comprovante_cartao_nome"] == "cartao.pdf" and nota["status"] == "Aguardando pagamento"
    assert tela.get(f"/api/transferencias/{nota['id']}/cartao").status_code == 200

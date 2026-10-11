"""Caixa de entrada: boletos recebidos por e-mail (IMAP) e pelo bot do Telegram (sem acessar a internet)."""

from datetime import date, timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from app import admin, contexto, entrada, main
from app.arquivos import RepositorioArquivos
from app.fila_gravacao import FilaGravacao
from app.notificacoes import canais
from app.planilha import PlanilhaBoletos
from app.repositorio import RepositorioBoletos

PDF = b"%PDF-1.4 boleto de teste " + b"x" * 200
FOTO = b"\xff\xd8\xff" + b"f" * 30_000


def _email(remetente, assunto, anexos):
    msg = EmailMessage()
    msg["From"] = remetente
    msg["Subject"] = assunto
    msg.set_content("Segue o boleto.")
    for nome, dados, tipo in anexos:
        principal, sub = tipo.split("/")
        msg.add_attachment(dados, maintype=principal, subtype=sub, filename=nome)
    return msg.as_bytes()


class ImapFalso:
    def __init__(self, mensagens, validade="777"):
        self.mensagens = mensagens  # {uid: bytes}
        self.validade = validade
        self.buscas = []
        self.fetches = []

    def login(self, usuario, senha):
        if senha != "senha-de-app":
            import imaplib
            raise imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")

    def select(self, pasta, readonly=False):
        assert readonly  # nunca altera a caixa de e-mail
        return "OK", [b"3"]

    def response(self, nome):
        return nome, [self.validade.encode()]

    def uid(self, comando, argumento, criterio):
        if comando == "SEARCH":
            self.buscas.append(criterio)
            if criterio.startswith("SINCE"):
                uids = sorted(self.mensagens)
            elif criterio == "UID *":
                uids = [max(self.mensagens)] if self.mensagens else []
            else:
                inicio = int(criterio.split()[1].split(":")[0])
                uids = [u for u in sorted(self.mensagens) if u >= inicio] or [max(self.mensagens)]
            return "OK", [" ".join(map(str, uids)).encode()]
        assert "PEEK" in criterio  # só lê: não marca o e-mail como lido
        uid = int(argumento)
        self.fetches.append(uid)
        return "OK", [(f"{uid} (BODY[] {{1}}".encode(), self.mensagens[uid]), b")"]

    def logout(self):
        pass


def _caixa(tmp_path, lidos, destinatarios=()):
    def processar(dados, nome):
        lidos.append(nome)
        if dados.startswith(b"ilegivel"):
            raise ValueError("Não foi possível ler o arquivo.")
        return {"boletos": [{"campos": {"beneficiario": {"valor": "Energia SA"}, "valor": {"valor": 321.5},
                                        "vencimento": {"valor": date(2026, 10, 5)}}, "duplicado": None}],
                "pix": [], "arquivo": {"id": f"{len(lidos):032x}"}}

    return entrada.CaixaEntrada(tmp_path / "entrada.json", processar, lambda dados, nome: {"id": "f" * 32},
                                lambda: ("123:abc", [{"chat_id": c, "nome": "Pessoa"} for c in destinatarios]))


def test_anexos_do_email_ignora_logotipos_e_textos():
    bruto = _email("Energia SA <contas@energia.com.br>", "=?utf-8?q?Fatura_de_Setembro?=", [
        ("fatura.pdf", PDF, "application/pdf"), ("logo.png", b"\x89PNG" + b"l" * 500, "image/png"),
        ("foto-boleto.jpg", FOTO, "image/jpeg"), ("notas.txt", b"texto", "text/plain")])
    info, anexos = entrada.anexos_do_email(bruto)
    assert info["endereco"] == "contas@energia.com.br" and info["remetente"] == "Energia SA"
    assert [nome for nome, _ in anexos] == ["fatura.pdf", "foto-boleto.jpg"]
    assert entrada.remetente_permitido("contas@energia.com.br", "energia.com.br; outro@x.com")
    assert not entrada.remetente_permitido("golpe@energia.com.br.falso.net", "energia.com.br")
    assert entrada.remetente_permitido("qualquer@um.com", "")


def test_email_le_anexos_sem_alterar_a_caixa_e_sem_repetir(tmp_path):
    lidos = []
    caixa = _caixa(tmp_path, lidos)
    with pytest.raises(ValueError):
        caixa.configurar({"email": {"ativo": True}})  # falta servidor, e-mail e senha
    caixa.configurar({"email": {"ativo": True, "servidor": "imap.gmail.com", "usuario": "boletos@empresa.com",
                                "senha": "senha-de-app", "remetentes": "energia.com.br"}})
    assert caixa.config_publica()["email"]["senha"] == entrada.MASCARA

    imap = ImapFalso({
        10: _email("contas@energia.com.br", "Fatura", [("fatura.pdf", PDF, "application/pdf")]),
        11: _email("spam@propaganda.com", "Promoção", [("oferta.pdf", b"%PDF oferta" + b"y" * 50, "application/pdf")]),
        12: _email("contas@energia.com.br", "Reenvio", [("fatura-copia.pdf", PDF, "application/pdf"),
                                                        ("ruim.pdf", b"ilegivel %PDF", "application/pdf")]),
    })
    resultado = caixa.verificar_email(conectar=lambda cfg: imap)
    assert imap.buscas[0].startswith("SINCE")
    assert resultado["recebidos"] == 2 and lidos == ["fatura.pdf", "ruim.pdf"]  # remetente filtrado; cópia idêntica ignorada
    itens = caixa.listar()
    assert {i["estado"] for i in itens} == {"pendente", "erro"}
    pendente = next(i for i in itens if i["estado"] == "pendente")
    assert pendente["origem"] == "email" and pendente["resumo"]["beneficiario"] == "Energia SA"
    assert caixa.arquivos_em_uso() == {pendente["arquivo_id"], "f" * 32}

    imap.mensagens[13] = _email("contas@energia.com.br", "Nova", [("nova.pdf", PDF + b"2", "application/pdf")])
    assert caixa.verificar_email(conectar=lambda cfg: imap)["recebidos"] == 1
    assert imap.buscas[-1] == "UID 13:*"

    assert caixa.marcar_lancados({pendente["arquivo_id"]}) == 1
    assert caixa.contagem() == 2
    with pytest.raises(ValueError, match="senha de app"):
        caixa.configurar({"email": {"senha": "errada"}})
        caixa.verificar_email(conectar=lambda cfg: imap)
    assert "senha de app" in caixa.config_publica()["email"]["ultimo_erro"]


def test_primeira_verificacao_sem_emails_recentes_comeca_do_ultimo(tmp_path):
    caixa = _caixa(tmp_path, [])
    caixa.configurar({"email": {"servidor": "imap.x.com", "usuario": "a@x.com", "senha": "senha-de-app"}})
    imap = ImapFalso({5: b""})
    imap.uid = lambda comando, _c, criterio: ("OK", [b""]) if criterio.startswith("SINCE") else ("OK", [b"5"])
    caixa.verificar_email(conectar=lambda cfg: imap)
    assert caixa._estado["email"]["ultimo_uid"] == 5


def test_telegram_recebe_so_de_pessoas_cadastradas_e_responde(tmp_path, monkeypatch):
    chamadas = []
    atualizacoes = [
        {"update_id": 1, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"}, "from": {"first_name": "Maria"},
                                      "document": {"file_id": "doc1", "file_name": "boleto.pdf", "mime_type": "application/pdf"}}},
        {"update_id": 2, "message": {"chat": {"id": 99, "type": "private", "first_name": "Estranho"},
                                      "photo": [{"file_id": "p1", "file_size": 100}, {"file_id": "p2", "file_size": 900}]}},
        {"update_id": 3, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"}, "text": "/start"}},
        {"update_id": 4, "message": {"chat": {"id": 42, "type": "private", "first_name": "Maria"},
                                      "photo": [{"file_id": "p3", "file_size": 50}, {"file_id": "p4", "file_size": 5000}]}},
    ]

    def telegram_falso(token, metodo, dados=None):
        chamadas.append((metodo, dados))
        return atualizacoes if metodo == "getUpdates" and not dados.get("offset") else [] if metodo == "getUpdates" else {}

    baixados = []
    monkeypatch.setattr(canais, "_telegram", telegram_falso)
    monkeypatch.setattr(canais, "baixar_arquivo_telegram", lambda token, file_id: baixados.append(file_id) or f"arquivo {file_id}".encode())
    caixa = _caixa(tmp_path, [], destinatarios=["42"])
    assert caixa.verificar_telegram()["recebidos"] == 2
    assert baixados == ["doc1", "p4"]  # a foto do desconhecido não é baixada; da Maria, a maior resolução
    respostas = {(d["chat_id"], d["text"][:20]) for m, d in chamadas if m == "sendMessage"}
    assert ("99", "Este bot só recebe b") in respostas and ("42", "Boleto recebido: Ene") in respostas
    assert caixa._estado["telegram"]["offset"] == 5
    assert {c["chat_id"] for c in caixa.chats_recentes()} == {"42", "99"}
    assert {i["remetente"] for i in caixa.listar()} == {"Maria"}

    caixa.verificar_telegram()
    assert chamadas[-1] == ("getUpdates", {"limit": 50, "timeout": 0, "offset": 5})


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    planilha = PlanilhaBoletos(tmp_path / "boletos.xlsx")
    fila = FilaGravacao(planilha, tmp_path / "fila.json")
    arquivos = RepositorioArquivos(tmp_path / "arquivos")
    monkeypatch.setattr(contexto, "planilha", planilha)
    monkeypatch.setattr(contexto, "repositorio", RepositorioBoletos(planilha, fila))
    monkeypatch.setattr(contexto, "arquivos", arquivos)
    monkeypatch.setattr(contexto, "administrador", admin.GerenciadorAdmin(tmp_path / "admin.json"))
    caixa = entrada.CaixaEntrada(tmp_path / "entrada.json", lambda dados, nome: {"boletos": [{}], "pix": [], "arquivo": arquivos.salvar(dados, nome)},
                                 arquivos.salvar, lambda: ("", []))
    monkeypatch.setattr(contexto, "caixa_entrada", caixa)
    with TestClient(main.app) as c:
        yield c, caixa


def test_api_da_caixa_de_entrada(cliente):
    c, caixa = cliente
    item = caixa.receber(PDF, "boleto.pdf", "email", "Energia SA", "Fatura")
    outro = caixa.receber(PDF + b"b", "outro.pdf", "telegram", "Maria")
    dados = c.get("/api/entrada").json()
    assert dados["pendentes"] == 2 and "senha" not in str(dados["itens"])
    assert c.get(f"/api/entrada/{item['id']}").json()["resultado"]["arquivo"]["id"] == item["arquivo_id"]

    # Lançar o boleto revisado tira o arquivo da caixa de entrada
    lancado = c.post("/api/boletos", json={"beneficiario": "Energia SA", "valor": 10, "arquivo_id": item["arquivo_id"],
                                           "vencimento": (date.today() + timedelta(days=3)).isoformat(), "ignorar_validacao": True})
    assert lancado.status_code == 201 and lancado.json()["arquivo_nome"] == "boleto.pdf"
    assert [i["id"] for i in c.get("/api/entrada").json()["itens"]] == [outro["id"]]
    assert c.post("/api/entrada/descartar", json={"ids": [outro["id"]]}).json() == {"descartados": 1, "pendentes": 0}

    assert c.put("/api/entrada/config", json={"telegram": {"ativo": True}}).status_code == 403
    assert c.post("/api/entrada/verificar", json={"canal": "telegram"}).json()["detail"]["codigo"] == "verificacao_falhou"

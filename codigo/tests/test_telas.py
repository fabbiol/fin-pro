"""Testes das telas no navegador (Playwright + Edge já instalado no Windows).

Sobem o sistema numa porta livre, com dados temporários, e conferem os caminhos principais:
abrir todas as telas sem erro no console, ler um boleto, dar baixa por comprovante e ver o fechamento.

Se o Playwright ou o Edge não estiverem disponíveis, os testes são pulados (o restante da suíte continua valendo).
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
TOKEN_OPERACOES = "token-dos-testes-de-tela"  # a Operações manda as notas das Transferências com este token
pytest.importorskip("playwright", reason="Playwright não instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from gerar_boleto_exemplo import gerar_pdf  # noqa: E402


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def sistema():
    """Sobe o Fin Pro com uma pasta de dados vazia e devolve (url, pasta)."""
    pasta = Path(tempfile.mkdtemp(prefix="leitor-telas-"))
    porta = _porta_livre()
    ambiente = {**os.environ, "LEITOR_DADOS_DIR": str(pasta), "LEITOR_PORT": str(porta),
                "LEITOR_NOTIFICACOES_AUTOMATICAS": "0", "LEITOR_BACKUP_AUTOMATICO": "0", "LEITOR_ABRIR_NAVEGADOR": "0",
                "OPERACOES_TOKEN": TOKEN_OPERACOES}
    processo = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(porta)],
                                cwd=RAIZ, env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{porta}"
    for _ in range(120):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", porta)) == 0:
                break
        time.sleep(0.5)
    else:
        processo.terminate()
        pytest.fail("o servidor não subiu")
    yield url, pasta
    processo.terminate()
    processo.wait(timeout=30)


@pytest.fixture(scope="module")
def pagina(sistema):
    url, _ = sistema
    try:
        navegador = sync_playwright().start()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Playwright indisponível: {exc}")
    try:
        edge = navegador.chromium.launch(channel="msedge")
    except Exception as exc:  # pragma: no cover
        navegador.stop()
        pytest.skip(f"Microsoft Edge indisponível: {exc}")
    pagina = edge.new_page(viewport={"width": 1400, "height": 1000})
    pagina.erros = []
    pagina.on("console", lambda m: pagina.erros.append(m.text) if m.type == "error" else None)
    pagina.on("pageerror", lambda e: pagina.erros.append(str(e)))
    pagina.goto(url, wait_until="networkidle")
    yield pagina
    edge.close()
    navegador.stop()


def _texto(pagina, seletor: str) -> str:
    """Texto da tela com o espaço fixo do "R$ 1,00" trocado por espaço normal (facilita as comparações)."""
    return pagina.inner_text(seletor).replace(" ", " ")


def _ir(pagina, rota: str):
    pagina.evaluate("(r) => { location.hash = r; }", f"#/{rota}")
    pagina.wait_for_timeout(900)


def test_todas_as_telas_abrem_sem_erro(pagina):
    telas = {
        "painel": "Nenhum boleto lançado ainda", "ler": "Arraste os boletos", "boletos": "Exportar", "pix": "Novo pagamento Pix",
        "gastos": "Análise de gastos", "notificacoes": "Avisos de vencimento", "config?aba=geral": "Recursos de leitura",
        "config?aba=usuarios": "Usuários do escritório", "config?aba=integracoes": "Backup fora do computador",
        "config?aba=saude": "Banco de dados e planilha", "empresas?aba=fechamentos": "Falta receber",
        "empresas?aba=cheques": "Em carteira", "empresas?aba=bot": "Bot de notas fiscais",
        "comprovantes": "Baixar comprovantes", "comprovantes?tipo=cheque": "Pagos sem comprovante",
        "caixa": "Saldo em caixa", "caixa?aba=relatorios": "Onde mais se gastou", "caixa?aba=conferencia": "Nada para revisar",
        "caixa?aba=bot": "Bot do caixa",
        "diesel": "Saldo do diesel", "diesel?aba=maquinas": "Nenhuma máquina cadastrada",
        "diesel?aba=relatorios": "Relatório semanal", "diesel?aba=conferencia": "Nada para conferir",
        "diesel?aba=bot": "Quem escolhe a máquina", "transferencias": "Valor somado",
    }
    for rota, texto in telas.items():
        _ir(pagina, rota)
        assert texto in _texto(pagina, "#view"), f"a tela {rota} não mostrou “{texto}”"
    assert not pagina.erros, pagina.erros


def test_ler_boleto_lancar_e_dar_baixa_por_comprovante(pagina, sistema, tmp_path_factory):
    from app.boleto.codigo import formatar_linha
    from test_comprovante import ITAU, _pdf

    url, _ = sistema
    pasta = tmp_path_factory.mktemp("arquivos")
    vencimento = date.today() - timedelta(days=3)
    caminho = pasta / "boleto.pdf"
    linha = gerar_pdf(caminho, beneficiario="CLA AUTO PECAS MIRASSOL LTDA", cnpj="12.345.678/0001-95", documento="NF-1",
                      vencimento=vencimento, valor=Decimal("270.35"))

    _ir(pagina, "ler")
    pagina.set_input_files("#entrada-arquivos", str(caminho))
    pagina.wait_for_selector("[data-acao=lancar]", timeout=60_000)
    assert pagina.locator("[data-campo=beneficiario]").first.input_value() == "CLA AUTO PECAS MIRASSOL LTDA"
    pagina.click("[data-acao=lancar]")
    pagina.wait_for_selector("text=Lançado na planilha", timeout=20_000)

    comprovante = pasta / "comprovante.pdf"
    texto = ITAU.replace("R$ 5,40", "R$ 8,10").replace("R$ 275,75", "R$ 278,45").format(
        linha=formatar_linha(linha), vencimento=f"{vencimento:%d/%m/%Y}", pagamento=f"{date.today():%d/%m/%Y}")
    comprovante.write_bytes(_pdf(texto))
    pagina.set_input_files("#entrada-arquivos", str(comprovante))
    pagina.wait_for_selector("text=Pagamento registrado", timeout=60_000)
    assert "juros/multa R$ 8,10" in _texto(pagina, "#lista-fila")

    _ir(pagina, "boletos")
    linhas = _texto(pagina, "#tabela")
    assert "CLA AUTO PECAS" in linhas and "Pago" in linhas

    _ir(pagina, f"gastos?aba=fechamento")
    pagina.wait_for_selector("text=Juros e multas", timeout=20_000)
    resumo = _texto(pagina, "#f-resultado")
    assert "R$ 278,45" in resumo and "R$ 8,10" in resumo
    assert not pagina.erros, pagina.erros


def test_painel_mostra_previsao_e_vencidos(pagina):
    pagina.evaluate("""async () => {
      const venc = new Date(Date.now() - 5 * 86400000).toISOString().slice(0, 10);
      await fetch("/api/boletos", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ beneficiario: "Fornecedor Atrasado", valor: 1500, vencimento: venc, ignorar_validacao: true }) });
      await fetch("/api/pix", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo_chave: "email", chave: "a@b.com", valor: 250, recebedor: "Pix Atrasado", vencimento: venc }) });
    }""")
    _ir(pagina, "boletos")
    _ir(pagina, "painel")
    texto = _texto(pagina, "#view")
    assert "Previsão de saídas" in texto and "Vencidos (2)" in texto and "Pix Atrasado" in texto
    assert "1 boleto e 1 Pix em atraso" in texto and "R$ 1.750,00" in texto
    pagina.click(".prev-linha.atraso")
    pagina.wait_for_selector(".modal", timeout=10_000)
    assert "Fornecedor Atrasado" in _texto(pagina, ".modal")
    pagina.keyboard.press("Escape")
    assert not pagina.erros, pagina.erros


def test_empresas_importa_o_print_do_fechamento_e_da_baixa(pagina, sistema, tmp_path_factory):
    """Parte 5 do módulo Empresas: começar a operar com o fechamento que já estava em andamento."""
    from test_empresas_bot import _pdf
    from test_empresas_leitura import PRINT_FECHAMENTO

    pagina.evaluate("""async () => {
      await fetch("/api/empresas", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome: "Imapal", cnpj: "12.345.678/0001-95" }) });
      await fetch("/api/empresas/config", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ minha_empresa: { nome: "Prospera Industria E Serviços LTDA", cnpj: "03.880.985/0001-85" } }) });
    }""")
    caminho = tmp_path_factory.mktemp("empresas") / "print-fechamento.pdf"
    caminho.write_bytes(_pdf(PRINT_FECHAMENTO))

    _ir(pagina, "empresas?aba=conferencia")
    pagina.set_input_files("#emp-arquivo", str(caminho))
    pagina.wait_for_selector("text=Importar fechamento já em andamento", timeout=60_000)
    assert "R$ 9.528,00" in _texto(pagina, ".modal")
    pagina.select_option(".modal #if-empresa", "Imapal")
    pagina.click(".modal [data-salvar]")
    pagina.wait_for_selector("text=linha(s) importada(s)", timeout=20_000)

    pagina.wait_for_selector(".tabela-fechamento", timeout=20_000)  # abre sozinho no fechamento importado
    fechamento = _texto(pagina, "#emp-fechamento")
    assert "Prospera Industria E Serviços LTDA 03.880.985/0001-85" in fechamento
    assert "agosto de 2026" in fechamento
    assert "Fechamento Imapal" in fechamento and "6859" in fechamento and "Brita 01" in fechamento
    assert "R$ 9.528,00" in fechamento

    # comprovante de Pix recebido: baixa automática da NF citada
    pagina.evaluate("""async () => {
      await fetch("/api/recebimentos", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ empresa: "Imapal", forma: "Pix", valor: 1905.6, notas: "6859" }) });
    }""")
    _ir(pagina, "empresas?aba=notas")  # sai e volta para a tela desenhar de novo
    _ir(pagina, "empresas?aba=fechamentos&empresa=1&competencia=2026-08")
    pagina.wait_for_selector(".tabela-fechamento", timeout=20_000)
    resumo = _texto(pagina, ".fechamento-resumo")
    assert "R$ 1.905,60" in resumo and "R$ 7.622,40" in resumo  # já recebido e o que falta
    assert not pagina.erros, pagina.erros


def test_transferencias_junta_a_nota_que_chegou_depois(pagina, tmp_path_factory):
    """O cliente pagou duas notas de uma vez, mas a segunda chegou depois de o pagamento estar ligado à primeira."""
    from test_transferencias import _pdf_texto

    comprovante = tmp_path_factory.mktemp("transferencias") / "comprovante.pdf"
    comprovante.write_bytes(_pdf_texto("Comprovante de transferência\nPix enviado\n24/11/2026 - 08:40:12\nValor\nR$ 2.000,00\n"
                                       "ID da transação: E00000000202611240840s0000000001"))
    enviar = """async ([origem, nota, valor, token]) => {
      const dados = new FormData();
      Object.entries({ origem_id: origem, nota, valor, empresa: "Construtora Exemplo Ltda", documento: "98765432000110",
                       forma: "pix", emitida_em: "2026-11-24 09:00:00" }).forEach(([k, v]) => dados.append(k, v));
      const resposta = await fetch("/api/integracao/operacoes/notas", { method: "POST", body: dados,
                                                                       headers: { Authorization: `Bearer ${token}` } });
      return resposta.status;
    }"""
    nota_aguardando = 'input[data-marcar]:not([data-marcar="todos"])'
    assert pagina.evaluate(enviar, ["7001", "7400", "1200.00", TOKEN_OPERACOES]) == 201
    _ir(pagina, "painel")  # sai e volta para a tela desenhar de novo
    _ir(pagina, "transferencias")
    pagina.check(nota_aguardando)
    pagina.click("[data-acao=ligar]")
    pagina.set_input_files(".modal [data-lp-arquivo]", str(comprovante))
    pagina.wait_for_selector(".modal [data-lp-conta] .alerta", timeout=60_000)
    assert "pagou a mais" in _texto(pagina, ".modal [data-lp-conta]")
    pagina.click(".modal [data-lp-confirmar]")
    pagina.wait_for_selector("text=Pagamento ligado", timeout=20_000)

    # a segunda nota chega depois: entra no mesmo pagamento, sem ligar o comprovante de novo
    assert pagina.evaluate(enviar, ["7002", "7401", "800.00", TOKEN_OPERACOES]) == 201
    _ir(pagina, "painel")
    _ir(pagina, "transferencias")
    pagina.check(nota_aguardando)
    pagina.click("[data-acao=juntar]")
    pagina.wait_for_selector(".modal .jp-opcao", timeout=20_000)
    assert "Sobra R$ 800,00 · bate" in _texto(pagina, ".modal .jp-opcao")
    pagina.check(".modal .jp-opcao input")
    assert "bate com o valor pago (R$ 2.000,00)" in _texto(pagina, ".modal [data-jp-conta]")
    pagina.click(".modal [data-jp-confirmar]")
    pagina.wait_for_selector("text=juntada ao pagamento", timeout=20_000)
    pagina.wait_for_selector("text=Junto com a nota 7401", timeout=20_000)
    tabela = _texto(pagina, "#t-tabela")
    assert "Junto com a nota 7400" in tabela and "Aguardando pagamento" not in tabela
    assert not pagina.erros, pagina.erros

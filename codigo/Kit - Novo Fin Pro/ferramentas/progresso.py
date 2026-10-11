"""Placar da reconstrução: roda os testes de cada etapa do plano e mostra quantos passam.

    python ferramentas/progresso.py            placar de todas as etapas
    python ferramentas/progresso.py --etapa 2  só a etapa 2, mostrando os erros

As etapas seguem especificacao/12-plano-de-reconstrucao.md. Uma etapa está pronta quando todos os testes dela passam.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

ETAPAS = {
    1: ("Motor de dados", ["test_banco", "test_planilha", "test_gravacao"]),
    2: ("Leitura de boletos", ["test_codigo", "test_texto", "test_corpus", "test_harmonizacao", "test_ia"]),
    3: ("API base, boletos, Pix, centros", ["test_api", "test_api_melhorias", "test_pix", "test_pix_centros_api"]),
    4: ("Front-end (telas no navegador)", ["test_telas"]),
    5: ("Comprovantes e baixa automática", ["test_comprovante", "test_juros_visiveis"]),
    6: ("Fechamento do mês", ["test_fechamento"]),
    7: ("Notificações e sininho", ["test_notificacoes", "test_sino", "test_telegram_destinatarios"]),
    8: ("Usuários e permissões", ["test_admin", "test_usuarios", "test_permissoes"]),
    9: ("Integrações (importação, e-mail/Telegram, backup total, versões, rede, saúde, logs)",
        ["test_importacao", "test_entrada", "test_bot", "test_backup", "test_versao", "test_rede", "test_saude",
         "test_registro_log"]),
    10: ("Aplicativo de desktop", ["test_desktop_cache"]),
    11: ("Empresas", ["test_empresas", "test_empresas_api", "test_empresas_bot", "test_empresas_leitura",
                      "test_deposito_cheque"]),
    12: ("Caixa", ["test_caixa"]),
    13: ("Diesel", ["test_diesel", "test_diesel_relatorio"]),
    14: ("Resumos, comprovantes, relatório geral", ["test_resumo_semanal", "test_busca_comprovantes",
                                                    "test_relatorio_geral"]),
    15: ("Demonstração", ["test_demonstracao"]),
}


def _python() -> str:
    candidato = RAIZ / ".venv" / "Scripts" / "python.exe"
    if not candidato.exists():
        candidato = RAIZ / ".venv" / "bin" / "python"
    return str(candidato) if candidato.exists() else sys.executable


def _rodar(arquivos: list[str], detalhado: bool) -> tuple[dict, str]:
    caminhos = [str(RAIZ / "tests" / f"{a}.py") for a in arquivos if (RAIZ / "tests" / f"{a}.py").exists()]
    if not caminhos:
        return {"erro": "testes não encontrados"}, ""
    comando = [_python(), "-m", "pytest", *caminhos, "-q", "-p", "no:cacheprovider",
               "--tb=short" if detalhado else "--tb=no"]
    resultado = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    saida = resultado.stdout + resultado.stderr
    contagem = {chave: int(n) for n, chave in re.findall(r"(\d+) (passed|failed|error|errors|skipped)", saida)}
    if not contagem and resultado.returncode:
        contagem = {"erro": "não rodou (veja com --etapa)"}
    return contagem, saida


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos certos no terminal do Windows
    except (AttributeError, ValueError):
        pass
    if "--etapa" in sys.argv:
        numero = int(sys.argv[sys.argv.index("--etapa") + 1])
        nome, arquivos = ETAPAS[numero]
        contagem, saida = _rodar(arquivos, detalhado=True)
        print(saida[-15000:])
        print(f"Etapa {numero} — {nome}: {contagem}")
        return
    print(f"{'Etapa':<6}{'Assunto':<62}{'Passam':>8}{'Falham':>8}{'Pulados':>9}  Situação")
    total_ok = total = 0
    for numero, (nome, arquivos) in ETAPAS.items():
        contagem, _ = _rodar(arquivos, detalhado=False)
        if "erro" in contagem:
            print(f"{numero:<6}{nome[:60]:<62}{'—':>8}{'—':>8}{'—':>9}  {contagem['erro']}")
            continue
        ok = contagem.get("passed", 0)
        falhas = contagem.get("failed", 0) + contagem.get("error", 0) + contagem.get("errors", 0)
        pulados = contagem.get("skipped", 0)
        total_ok += ok
        total += ok + falhas
        situacao = "PRONTA" if ok and not falhas else "falta" if falhas else "sem testes rodando"
        print(f"{numero:<6}{nome[:60]:<62}{ok:>8}{falhas:>8}{pulados:>9}  {situacao}")
    print(f"\nTotal: {total_ok} de {total} testes passando (meta: 273, os de tela podem ser pulados sem Edge/Playwright).")


if __name__ == "__main__":
    main()

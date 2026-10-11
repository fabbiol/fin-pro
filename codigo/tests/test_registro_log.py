"""O arquivo de log gira quando fica grande e guarda só alguns arquivos antigos."""

from app import registro_log


def test_log_gira_e_limita_arquivos(tmp_path):
    caminho = tmp_path / "leitor.log"
    saida = registro_log.ArquivoRotativo(caminho, tamanho_maximo=200, antigos=2)
    for n in range(40):
        saida.write(f"linha {n:03d} " + "x" * 20 + "\n")
    arquivos = registro_log.arquivos_de_log(caminho)
    assert [a.name for a in arquivos] == ["leitor.log", "leitor.log.1", "leitor.log.2"]
    assert all(a.stat().st_size <= 260 for a in arquivos)
    assert "linha 039" in caminho.read_text(encoding="utf-8")
    assert saida.limpar_antigos() > 0
    assert [a.name for a in registro_log.arquivos_de_log(caminho)] == ["leitor.log"] and caminho.stat().st_size == 0

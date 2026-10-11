"""Depois de uma atualização, a janela do aplicativo não pode continuar mostrando telas antigas do cache."""

import os
import time

from app import desktop


def test_limpa_cache_da_janela_somente_quando_as_telas_mudam(tmp_path, monkeypatch):
    web = tmp_path / "web"
    (web / "js").mkdir(parents=True)
    tela = web / "js" / "configuracoes.js"
    tela.write_text("// versão antiga", encoding="utf-8")
    monkeypatch.setattr(desktop.config, "WEB_DIR", web)

    pasta = tmp_path / "webview"
    cache = pasta / "EBWebView" / "Default" / "Cache" / "Cache_Data"
    preferencias = pasta / "EBWebView" / "Default" / "Local Storage"
    cache.mkdir(parents=True)
    preferencias.mkdir(parents=True)
    (cache / "f_000007").write_text("configuracoes.js antigo", encoding="utf-8")

    assert desktop.limpar_cache_se_atualizado(pasta)  # primeira abertura com a marca de versão: limpa
    assert not cache.exists() and preferencias.exists()  # tema e preferências continuam

    cache.mkdir(parents=True)
    (cache / "f_000001").write_text("cache novo", encoding="utf-8")
    assert not desktop.limpar_cache_se_atualizado(pasta)  # nada mudou: mantém o cache
    assert (cache / "f_000001").exists()

    tela.write_text("// versão nova com o cartão de importação", encoding="utf-8")
    futuro = time.time() + 5
    os.utime(tela, (futuro, futuro))
    assert desktop.limpar_cache_se_atualizado(pasta)  # telas atualizadas: limpa de novo
    assert not cache.exists()

"""Objetos compartilhados pela aplicação (planilha, repositórios, serviços), criados uma única vez.

Os módulos de rotas (``app/rotas``) importam daqui, em vez de cada um criar a sua própria cópia.
"""

from __future__ import annotations

from urllib.parse import quote

from . import admin, backup as modulo_backup, config, importacao, janela, usuarios as modulo_usuarios
from . import versao as modulo_versao
from .arquivos import RepositorioArquivos
from .fila_gravacao import FilaGravacao
from .notificacoes.servico import ServicoNotificacoes
from .banco import BancoBoletos
from .empresas.configuracao import ConfigEmpresas
from .diesel.modelos import ABAS_DIESEL
from .empresas.modelos import ABAS_EMPRESAS
from .repositorio import FonteLembretes, RepositorioBoletos
from .tarefas import GerenciadorTarefas

planilha = BancoBoletos(config.DADOS_DIR / "boletos.db", config.PLANILHA_PATH, config.BACKUPS_DIR)
fila = FilaGravacao(planilha, config.DADOS_DIR / "gravacao_pendente.json")
repositorio = RepositorioBoletos(planilha, fila)
repositorio_pix = RepositorioBoletos(planilha, fila, "pix")
repositorio_caixa = RepositorioBoletos(planilha, fila, "caixa")  # entradas e saídas em dinheiro
arquivos = RepositorioArquivos(config.ARQUIVOS_DIR)
importacoes = importacao.ArmazemImportacoes(config.DADOS_DIR / "importacoes")
modelos_importacao = importacao.ModelosMapeamento(config.DADOS_DIR / "importacao_modelos.json")
administrador = admin.GerenciadorAdmin(config.DADOS_DIR / "admin.json")
usuarios = modulo_usuarios.GerenciadorUsuarios(config.DADOS_DIR / "usuarios.json")
tarefas = GerenciadorTarefas(max_paralelo=2)

# Módulo Empresas (o que os clientes têm a pagar): banco, planilha e configuração próprios
empresas = BancoBoletos(config.DADOS_DIR / "empresas.db", config.FECHAMENTOS_PATH, config.BACKUPS_DIR,
                        abas=ABAS_EMPRESAS, centros=False, nome_backup="empresas")
empresas_config = ConfigEmpresas(config.DADOS_DIR / "empresas.json")
empresas_entrada = None  # CaixaNotas: bot de notas fiscais (criada em app.main)

# Diesel: compras no posto, abastecimentos de cada máquina (canhotos) e as máquinas — banco e planilha próprios
diesel = BancoBoletos(config.DADOS_DIR / "diesel.db", config.DIESEL_PATH, config.BACKUPS_DIR,
                      abas=ABAS_DIESEL, centros=False, nome_backup="diesel")
diesel_bot = None  # BotDiesel: canhotos e comprovantes de compra pelo Telegram (criado em app.main)


def link_notificacao(rota: str) -> str:
    """Link aberto ao clicar numa notificação do Windows: no modo aplicativo, traz a janela para a frente."""
    if janela.ativa():
        return f"http://127.0.0.1:{config.PORT}/api/app/abrir?rota={quote(rota, safe='')}"
    return f"{config.URL_APP}/#/{rota}"


def _cheques_a_depositar() -> list[dict]:
    """Cheques pré-datados entram nos mesmos avisos de vencimento dos boletos e Pix."""
    from .empresas import servico as servico_empresas

    try:
        return servico_empresas.alertas_de_cheques()
    except Exception:  # o módulo de empresas nunca pode derrubar os lembretes dos boletos
        return []


def _resumo_da_semana(tipo: str, hoje):
    """Resumo de segunda (o que vence na semana) ou de sexta (o que foi pago), com boletos, Pix, caixa e empresas."""
    from . import resumo_semanal

    return resumo_semanal.mensagem(resumo_semanal.coletar(tipo, hoje), config.URL_APP)


notificacoes = ServicoNotificacoes(FonteLembretes(repositorio, repositorio_pix, _cheques_a_depositar),
                                   config.DADOS_DIR / "notificacoes.json", config.URL_APP, montar_link=link_notificacao,
                                   montar_resumo=_resumo_da_semana)

backup = modulo_backup.GerenciadorBackup(config.DADOS_DIR / "backup.json", config.DADOS_DIR, config.PLANILHA_PATH,
                                       config.ARQUIVOS_DIR, copiar_banco=planilha.copiar_banco,
                                       extras=[{"nome": "empresas", "planilha": config.FECHAMENTOS_PATH,
                                                "copiar_banco": empresas.copiar_banco},
                                               {"nome": "diesel", "planilha": config.DIESEL_PATH,
                                                "copiar_banco": diesel.copiar_banco}],
                                       # backup total: também o código-fonte e o histórico de versões
                                       pasta_codigo=config.BASE_DIR, informar_versao=modulo_versao.carimbo,
                                       gerar_bundle=modulo_versao.gerar_bundle,
                                       verificar_bundle=modulo_versao.verificar_bundle)

rede = None  # GerenciadorRede: criado em app.main, pois serve a própria aplicação
caixa_entrada = None  # CaixaEntrada: boletos recebidos por e-mail e Telegram (criada em app.main)
caixa_bot = None  # BotCaixa: cupons de gastos em dinheiro pelo Telegram (criado em app.main)

"""Versão de demonstração: uma cópia completa do sistema com dados de exemplo, para mostrar a clientes.

Roda na pasta ``dados_demo`` (nunca toca nos dados reais) e numa porta própria, então pode ficar aberta ao
mesmo tempo que o sistema de verdade. Com ``LEITOR_DEMO=1``, nada é enviado para fora: Telegram e e-mail
ficam visíveis e configurados na tela, mas o envio é bloqueado.

    python -m app.demonstracao              prepara os dados (se a pasta estiver vazia) e abre
    python -m app.demonstracao --refazer    apaga tudo e monta os dados de novo
    python -m app.demonstracao --dados      só prepara os dados, sem abrir

O atalho para o dia a dia é o ``demonstracao.bat``, na pasta do projeto.
"""

from __future__ import annotations

import os
import random
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

PORTA_PADRAO = "8010"


def _ambiente() -> Path:
    """Variáveis de ambiente da demonstração (antes de importar o resto do sistema)."""
    raiz = Path(__file__).resolve().parent.parent
    # Sempre a pasta própria: no servidor LEITOR_DADOS_DIR aponta os dados reais, que o --refazer apagaria.
    pasta = raiz / "dados_demo"
    os.environ["LEITOR_DADOS_DIR"] = str(pasta)
    os.environ["LEITOR_DEMO"] = "1"
    os.environ.setdefault("LEITOR_PORT", PORTA_PADRAO)
    os.environ.setdefault("LEITOR_NOME_APP", "Fin Pro (demonstração)")
    os.environ.setdefault("LEITOR_NOTIFICACOES_AUTOMATICAS", "0")  # a demonstração não fica buscando mensagens
    os.environ.setdefault("LEITOR_BACKUP_AUTOMATICO", "0")
    return pasta


# --------------------------------------------------------------------------- dados de exemplo

CENTROS = [
    ("Combustível e Veículos", "Diesel, gasolina, pneus e manutenção da frota"),
    ("Manutenção", "Peças, oficina e serviços de manutenção"),
    ("Materiais", "Materiais de produção e insumos"),
    ("Energia e Água", "Contas de consumo"),
    ("Escritório", "Papelaria, internet, telefone e sistemas"),
    ("Impostos e Taxas", "Tributos e taxas"),
    ("Fretes", "Transporte e entregas"),
]

FORNECEDORES = [
    ("ENERGISA SUL SUDESTE", "09.095.183/0001-40", "Energia e Água", "Banco do Brasil"),
    ("POSTO SAO JORGE LTDA", "12.345.678/0001-95", "Combustível e Veículos", "Bradesco"),
    ("MAXIMA PARAFUSOS LTDA", "18.765.432/0001-21", "Manutenção", "Itaú"),
    ("TRANSPORTES RODRIGUES ME", "22.334.556/0001-09", "Fretes", "Sicredi"),
    ("COMERCIAL DE FERRO E ACO", "31.222.111/0001-77", "Materiais", "Santander"),
    ("SANEAMENTO MUNICIPAL", "05.111.222/0001-13", "Energia e Água", "Caixa"),
    ("PAPELARIA CENTRAL", "41.999.888/0001-55", "Escritório", "Banco do Brasil"),
    ("OFICINA DIESEL MIRASSOL", "27.888.777/0001-30", "Manutenção", "Bradesco"),
    ("PREFEITURA MUNICIPAL - ISS", "45.123.987/0001-10", "Impostos e Taxas", "Caixa"),
    ("DISTRIBUIDORA DE LUBRIFICANTES", "33.444.555/0001-66", "Combustível e Veículos", "Itaú"),
]

RECEBEDORES_PIX = [
    ("Mecânica do Zé", "cnpj", "12.987.654/0001-70", "Manutenção", "Troca de óleo do caminhão"),
    ("Maria da Limpeza", "celular", "+5517999887766", "Escritório", "Serviços de limpeza"),
    ("Serralheria Aço Forte", "cnpj", "44.555.666/0001-01", "Manutenção", "Conserto da caçamba"),
    ("Contabilidade Silva", "email", "contato@contabilidadesilva.com.br", "Escritório", "Honorários do mês"),
    ("Frete Expresso", "aleatoria", "b3f1c2de-77aa-4c31-9f55-0a1b2c3d4e5f", "Fretes", "Entrega urgente de peças"),
]

GASTOS_CAIXA = [
    ("Posto São Jorge", "Combustível e Veículos", "gasolina da caminhonete", 180.0, 320.0),
    ("Mercado Bom Preço", "Escritório", "café, açúcar e copos", 45.0, 130.0),
    ("Casa do Parafuso", "Manutenção", "parafusos e arruelas", 60.0, 240.0),
    ("Papelaria Central", "Escritório", "toner e papel A4", 90.0, 260.0),
    ("Borracharia do Tião", "Combustível e Veículos", "conserto de pneu", 70.0, 200.0),
    ("Lanchonete da Praça", "Escritório", "almoço da equipe", 50.0, 150.0),
]

EMPRESAS_CLIENTES = [
    ("Imapal Construções", "12.345.678/0001-95", "Imapal, Imapal Construcoes", "Brita 01", "M³", 158.80),
    ("Jose Pazete & Cia", "39.285.595/0001-04", "Pazete, Jose Pazete", "Pedrisco Comercial", "M³", 142.50),
    ("Terraplanagem Souza", "07.654.321/0001-88", "Souza, Terraplanagem Souza", "Rachão", "M³", 96.40),
]

PESSOAS = ["Fábio", "Almir", "Marcos", "Juliana"]


def _digitos_linha(semente: random.Random) -> str:
    """Linha digitável de exemplo (só para a demonstração: os dígitos são sorteados)."""
    return "".join(str(semente.randint(0, 9)) for _ in range(47))


def _formatar_linha(digitos: str) -> str:
    return f"{digitos[:5]}.{digitos[5:10]} {digitos[10:15]}.{digitos[15:21]} {digitos[21:26]}.{digitos[26:32]} {digitos[32]} {digitos[33:]}"


def _dinheiro(sorteio: random.Random, minimo: float, maximo: float) -> float:
    return round(sorteio.uniform(minimo, maximo), 2)


def _moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fonte(tamanho: int):
    from PIL import ImageFont

    for nome in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def _arquivo_exemplo(titulo: str, linhas: list[tuple[str, str]], nome: str, cor: str = "#0d7a64") -> dict:
    """Imagem de um comprovante de exemplo (só para a demonstração), guardada como os arquivos de verdade."""
    import io

    from PIL import Image, ImageDraw

    from . import contexto as ctx

    largura, altura = 720, 150 + 58 * len(linhas) + 70
    imagem = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle([0, 0, largura, 96], fill=cor)
    desenho.text((32, 26), titulo, fill="white", font=_fonte(34))
    y = 128
    for rotulo, valor in linhas:
        desenho.text((32, y), rotulo.upper(), fill="#6b7a86", font=_fonte(17))
        desenho.text((32, y + 22), valor, fill="#0e1a22", font=_fonte(25))
        y += 58
    desenho.line([32, y + 12, largura - 32, y + 12], fill="#d8e0e5", width=2)
    desenho.text((32, y + 26), "Documento de exemplo · Fin Pro (demonstração)", fill="#98a4ad", font=_fonte(16))
    saida = io.BytesIO()
    imagem.save(saida, "PNG")
    meta = ctx.arquivos.salvar(saida.getvalue(), nome)
    return {"id": meta["id"], "nome": meta["nome"], "caminho": ctx.arquivos.caminho_relativo(meta["id"]) or ""}


def montar_dados(hoje: date | None = None, semente: int = 20260922) -> dict:
    """Cria boletos, Pix, caixa, empresas, usuários e configurações de exemplo. Devolve o que foi criado."""
    from . import contexto as ctx
    from .caixa import servico as caixa
    from .empresas import servico as empresas

    hoje = hoje or date.today()
    sorteio = random.Random(semente)
    ctx.planilha.garantir()
    ctx.empresas.garantir()
    ctx.diesel.garantir()

    existentes = {c["nome"].lower() for c in ctx.planilha.listar_centros()}
    for nome, descricao in CENTROS:
        if nome.lower() not in existentes:
            ctx.planilha.salvar_centro(nome, descricao, True, usuario="Demonstração")

    # ------------------------------------------------------------------ boletos
    boletos = 0
    for dia in range(-115, 26):
        vencimento = hoje + timedelta(days=dia)
        if vencimento.weekday() >= 5 or sorteio.random() > 0.42:
            continue
        nome, documento, centro, banco = FORNECEDORES[sorteio.randrange(len(FORNECEDORES))]
        valor = _dinheiro(sorteio, 180, 6400)
        digitos = _digitos_linha(sorteio)
        dados = {
            "linha_digitavel": _formatar_linha(digitos), "beneficiario": nome, "documento_beneficiario": documento,
            "numero_documento": f"{sorteio.randrange(100000, 999999)}/{sorteio.randrange(1, 9):02d}",
            "vencimento": vencimento, "valor": valor, "emissor": banco, "tipo": "Cobrança",
            "centro_custo": centro, "lancado_por": PESSOAS[sorteio.randrange(len(PESSOAS))],
        }
        # o que já passou está pago, menos alguns dos últimos dias (assim a demonstração mostra atrasos e lembretes)
        atrasado = -18 < dia < -1 and sorteio.random() < 0.18
        if not atrasado and (dia < -2 or (dia <= 0 and sorteio.random() < 0.75)):
            atraso = sorteio.choice([0, 0, 0, 1, 2, 4])
            pagamento = vencimento + timedelta(days=atraso)
            juros = round(valor * 0.02 + 4.9, 2) if atraso > 1 else 0.0
            dados.update(status="Pago", data_pagamento=pagamento, valor_pago=round(valor + juros, 2),
                         juros_multa=juros, pago_por=PESSOAS[sorteio.randrange(2)])
            if sorteio.random() < 0.88:  # alguns ficam sem comprovante, para mostrar a busca "pagos sem comprovante"
                arquivo = _arquivo_exemplo("Comprovante de pagamento", [
                    ("Beneficiário", nome), ("CNPJ", documento), ("Valor pago", _moeda(valor + juros)),
                    ("Juros / multa", _moeda(juros)), ("Data do pagamento", f"{pagamento:%d/%m/%Y}"),
                    ("Linha digitável", digitos[:24] + "…")], f"comprovante-{nome[:20]}.png", "#2a62c7")
                dados.update(comprovante=arquivo["caminho"], comprovante_nome=arquivo["nome"])
        ctx.planilha.adicionar(dados)
        boletos += 1

    # ------------------------------------------------------------------ Pix
    pix = 0
    for dia in range(-75, 16, 3):
        if sorteio.random() > 0.55:
            continue
        vencimento = hoje + timedelta(days=dia)
        recebedor, tipo_chave, chave, centro, descricao = RECEBEDORES_PIX[sorteio.randrange(len(RECEBEDORES_PIX))]
        valor = _dinheiro(sorteio, 90, 2600)
        dados = {"recebedor": recebedor, "tipo_chave": tipo_chave, "chave": chave, "valor": valor,
                 "vencimento": vencimento, "centro_custo": centro, "descricao": descricao,
                 "lancado_por": PESSOAS[sorteio.randrange(len(PESSOAS))]}
        if dia < 0:
            dados.update(status="Pago", data_pagamento=vencimento, valor_pago=valor,
                         pago_por=PESSOAS[sorteio.randrange(2)])
            arquivo = _arquivo_exemplo("Pix enviado", [
                ("Para", recebedor), ("Chave", chave), ("Valor", _moeda(valor)),
                ("Data e hora", f"{vencimento:%d/%m/%Y} 10:{sorteio.randrange(10, 59)}"),
                ("ID da transação", f"E{sorteio.randrange(10**15, 10**16)}")], f"pix-{recebedor[:20]}.png", "#7a4fd6")
            dados.update(comprovante=arquivo["caminho"], comprovante_nome=arquivo["nome"])
        ctx.planilha.adicionar(dados, "pix")
        pix += 1

    # ------------------------------------------------------------------ caixa (dinheiro)
    lancamentos = 0
    caixa.lancar({"movimento": "Entrada", "valor": 3000, "data": hoje - timedelta(days=62),
                  "descricao": "Abertura do caixa", "pessoa": "Fábio"}, "Demonstração")
    lancamentos += 1
    for dia in range(-60, 1):
        quando = hoje + timedelta(days=dia)
        if quando.weekday() >= 5:
            continue
        if sorteio.random() < 0.30:
            pedido = 7000 + sorteio.randrange(1, 400)
            caixa.lancar({"movimento": "Entrada", "valor": _dinheiro(sorteio, 300, 2800), "data": quando,
                          "descricao": f"Pedido {pedido} · venda à vista", "pessoa": "Escritório",
                          "hora": f"{sorteio.randrange(8, 17):02d}:{sorteio.choice(['05', '20', '35', '50'])}"},
                         "Demonstração")
            lancamentos += 1
        if sorteio.random() < 0.55:
            local, centro, descricao, minimo, maximo = GASTOS_CAIXA[sorteio.randrange(len(GASTOS_CAIXA))]
            valor = _dinheiro(sorteio, minimo, maximo)
            cupom = _arquivo_exemplo("Cupom fiscal", [("Estabelecimento", local), ("Itens", descricao),
                                                      ("Valor a pagar", _moeda(valor)), ("Data", f"{quando:%d/%m/%Y}")],
                                     f"cupom-{local[:20]}.png", "#a86200") if sorteio.random() < 0.7 else None
            caixa.lancar({"movimento": "Saída", "valor": valor, "data": quando,
                          "local": local, "centro_custo": centro, "descricao": descricao,
                          "pessoa": PESSOAS[sorteio.randrange(len(PESSOAS))],
                          "hora": f"{sorteio.randrange(8, 18):02d}:{sorteio.choice(['10', '25', '40', '55'])}"},
                         "Demonstração", arquivo=cupom)
            lancamentos += 1

    # ------------------------------------------------------------------ empresas (vendas a prazo)
    notas = cheques = recebimentos = 0
    for nome, cnpj, apelidos, material, unidade, unitario in EMPRESAS_CLIENTES:
        empresas.salvar_empresa({"nome": nome, "cnpj": cnpj, "apelidos": apelidos, "dia_fechamento": 20,
                                 "contato": "Compras", "telefone": "(17) 3222-0000"}, "Demonstração")
        numero_nf = sorteio.randrange(7000, 7300)
        for dia in range(-70, 1, 4):
            if sorteio.random() > 0.5:
                continue
            quando = hoje + timedelta(days=dia)
            numero_nf += 1
            quantidade = sorteio.randrange(8, 26)
            pedido = str(7000 + sorteio.randrange(1, 400))
            danfe = _arquivo_exemplo(f"DANFE · NF {numero_nf}", [
                ("Destinatário", nome), ("Material", f"{material} · {quantidade} {unidade}"), ("Pedido", pedido),
                ("Valor total", _moeda(quantidade * unitario)), ("Emissão", f"{quando:%d/%m/%Y}")],
                f"NF-{numero_nf}.png", "#33434d")
            empresas.lancar_notas(nome, [{"data": quando, "material": material, "unidade": unidade,
                                          "quantidade": quantidade, "valor_unitario": unitario,
                                          "numero_nf": str(numero_nf), "pedido": pedido}],
                                  "Demonstração", arquivo=danfe)
            notas += 1
        for atras in (1, 0):  # o fechamento em aberto sempre tem lançamentos para mostrar
            numero_nf += 1
            empresas.lancar_notas(nome, [{"data": hoje - timedelta(days=atras), "material": material, "unidade": unidade,
                                          "quantidade": sorteio.randrange(10, 30), "valor_unitario": unitario,
                                          "numero_nf": str(numero_nf), "pedido": str(7000 + sorteio.randrange(1, 400))}],
                                  "Demonstração")
            notas += 1
        numero_cheque, bom_para = str(sorteio.randrange(100, 999)), hoje + timedelta(days=sorteio.randrange(1, 20))
        valor_cheque = _dinheiro(sorteio, 1800, 6500)
        foto = _arquivo_exemplo(f"Cheque nº {numero_cheque}", [
            ("Emitente", nome.upper()), ("Banco", "748 · Sicredi · coop 8058 · conta 98948-3"),
            ("Valor", _moeda(valor_cheque)), ("Bom para", f"{bom_para:%d/%m/%Y}")], f"cheque-{numero_cheque}.png", "#0d7a64")
        empresas.lancar_cheque({"empresa": nome, "numero": numero_cheque, "vencimento": bom_para,
                                "valor": valor_cheque, "banco": "Sicredi",
                                "agencia": "0801", "coop": "8058", "conta": "98948-3", "emitente": nome.upper()},
                               "Demonstração", arquivo=foto)
        cheques += 1
        for forma, dias in (("Pix", -24), ("Depósito", -9)):
            valor_recebido, quando = _dinheiro(sorteio, 900, 4200), hoje + timedelta(days=dias)
            transacao = f"E{sorteio.randrange(10**11, 10**12)}"
            comprovante = _arquivo_exemplo(f"{forma} recebido", [
                ("Pagador", nome), ("Valor", _moeda(valor_recebido)), ("Data e hora", f"{quando:%d/%m/%Y} 10:30"),
                ("ID da transação", transacao)], f"{forma.lower()}-{nome[:15]}.png", "#16a34a")
            empresas.registrar_recebimento({"empresa": nome, "valor": valor_recebido, "forma": forma,
                                            "data": quando, "pagador": nome, "hora": "10:30", "id_transacao": transacao},
                                           "Demonstração", arquivo=comprovante)
            recebimentos += 1

    abastecimentos = _diesel_de_exemplo(hoje, sorteio)
    configurar(hoje)
    return {"boletos": boletos, "pix": pix, "caixa": lancamentos, "notas": notas, "cheques": cheques,
            "recebimentos": recebimentos, "empresas": len(EMPRESAS_CLIENTES), "abastecimentos": abastecimentos}


MAQUINAS_DIESEL = [  # nome, tipo, placa, medidor, combustível, litros por abastecimento, uso por dia (horas ou km)
    ("Escavadeira PC200", "Máquina", "", "horas", "Diesel comum", (150, 210), 9),
    ("Pá carregadeira 924K", "Máquina", "", "horas", "Diesel comum", (110, 160), 8),
    ("Caminhão Volvo FMX", "Caminhão", "ABC-1D23", "km", "Diesel S10", (180, 260), 180),
    ("Caminhão Scania P360", "Caminhão", "DEF-2G34", "km", "Diesel S10", (170, 240), 160),
    ("Gerador 80 kVA", "Gerador", "", "horas", "Diesel comum", (40, 70), 6),
]
COMPRAS_SEMANAIS = (("Diesel S10", 550, 7.45), ("Diesel comum", 500, 6.75))  # uns 1.000 L por semana


def _diesel_de_exemplo(hoje: date, sorteio: random.Random) -> int:
    """Oito semanas de diesel: 1.000 L comprados toda segunda (S10 e comum) e os canhotos de cada máquina."""
    from .diesel import precos
    from .diesel import servico as diesel

    precos.salvar({c: preco for c, _, preco in COMPRAS_SEMANAIS}, "Demonstração")
    for nome, tipo, placa, medidor, combustivel, _, _ in MAQUINAS_DIESEL:
        diesel.salvar_maquina({"nome": nome, "tipo": tipo, "placa": placa, "medidor": medidor, "combustivel": combustivel},
                              "Demonstração")
    segunda = hoje - timedelta(days=hoje.weekday())
    for semana in range(8, -1, -1):
        dia = segunda - timedelta(weeks=semana)
        for combustivel, litros_semana, preco_base in COMPRAS_SEMANAIS:
            preco = round(preco_base + sorteio.uniform(-0.15, 0.10), 3)
            recibo = _arquivo_exemplo("Pix enviado · diesel", [
                ("Para", "Auto Posto Rodovia Ltda"), ("Valor", _moeda(litros_semana * preco)), ("Data", f"{dia:%d/%m/%Y} 08:10"),
                ("Referente", f"{litros_semana} L de {combustivel}")], f"diesel-compra-{dia:%Y%m%d}-{combustivel[-3:]}.png",
                "#0e6b5c")
            diesel.lancar_compra({"data": dia, "posto": "Auto Posto Rodovia", "combustivel": combustivel,
                                  "litros": litros_semana, "valor": round(litros_semana * preco, 2), "forma": "Pix"},
                                 "Demonstração", recibo)
    leituras = {nome: (sorteio.randrange(2000, 6000) if medidor == "horas" else sorteio.randrange(80000, 250000))
                for nome, _, _, medidor, _, _, _ in MAQUINAS_DIESEL}
    total = 0
    for dias_atras in range(8 * 7 + hoje.weekday(), -1, -1):
        quando = hoje - timedelta(days=dias_atras)
        if quando.weekday() == 6:
            continue
        for nome, _, placa, medidor, combustivel, (minimo, maximo), uso in MAQUINAS_DIESEL:
            leituras[nome] += uso * sorteio.uniform(0.7, 1.2)
            if sorteio.random() > 0.19:  # ≈ 6 abastecimentos por semana: uns 900 L dos 1.000 L comprados
                continue
            litros = round(sorteio.uniform(minimo, maximo), 1)
            canhoto = _arquivo_exemplo("Requisição de abastecimento", [
                ("Posto", "Auto Posto Rodovia"), ("Máquina", nome + (f" · placa {placa}" if placa else "")),
                (combustivel, f"{str(litros).replace('.', ',')} L"),
                ("Horímetro" if medidor == "horas" else "Km", f"{leituras[nome]:,.0f}".replace(",", ".")),
                ("Data", f"{quando:%d/%m/%Y}")], f"canhoto-{quando:%Y%m%d}-{nome[:12]}.png", "#b45309") \
                if dias_atras < 21 else None
            diesel.lancar_abastecimento({"data": quando, "hora": f"{sorteio.randrange(6, 17):02d}:{sorteio.choice(['05', '25', '40'])}",
                                         "maquina": nome, "combustivel": combustivel, "litros": litros,
                                         "medidor": round(leituras[nome], 1), "documento": str(690000 + total),
                                         "posto": "Auto Posto Rodovia", "pessoa": PESSOAS[sorteio.randrange(1, len(PESSOAS))]},
                                        "Demonstração", canhoto)
            total += 1
    return total


def configurar(hoje: date | None = None) -> None:
    """Usuários, lembretes, resumos da semana e bots — tudo ligado, como num cliente de verdade."""
    import json

    from . import config
    from . import contexto as ctx

    if not ctx.usuarios.listar():
        ctx.usuarios.criar("Fábio (dono)", "demo", "demo1234", "administrador")
        ctx.usuarios.criar("Almir (escritório)", "almir", "demo1234", "comum",
                           ["lancar", "pagar", "editar", "gastos", "caixa"])
        ctx.usuarios.criar("Juliana (financeiro)", "juliana", "demo1234", "comum",
                           ["lancar", "pagar", "gastos", "empresas", "notificacoes"])
    ctx.usuarios.definir_exigir_login_no_computador(False)  # a demonstração abre direto, sem pedir senha
    ctx.usuarios.definir_pedir_login_ao_abrir(False)

    ctx.notificacoes.atualizar_config({
        "ativo": True,
        "telegram": {"ativo": True, "token": "0000000000:DEMONSTRACAO", "destinatarios": [
            {"chat_id": "1001", "nome": "Escritório (grupo)", "tipo": "grupo", "ativo": True},
            {"chat_id": "1002", "nome": "Fábio", "tipo": "privado", "ativo": True},
            {"chat_id": "1003", "nome": "Almir", "tipo": "privado", "ativo": True},
        ]},
        "resumos": {"segunda": {"ativo": True, "horario": "08:00", "canais": ["windows", "telegram"]},
                    "sexta": {"ativo": True, "horario": "17:00", "canais": ["windows", "telegram"]}},
    })

    ctx.empresas_config.atualizar({
        "minha_empresa": {"nome": "Prospera Industria E Serviços LTDA", "cnpj": "03.880.985/0001-85"},
        "dia_fechamento": 20, "fechamento_automatico": True, "hora_envio": "08:00",
        "bot": {"ativo": True, "token": "0000000000:DEMONSTRACAO-NOTAS", "destinatarios": [
            {"chat_id": "2001", "nome": "Notas fiscais (grupo)", "tipo": "grupo", "ativo": True},
            {"chat_id": "2002", "nome": "Almir", "tipo": "privado", "ativo": True},
        ]},
    })

    diesel_bot = config.DADOS_DIR / "diesel_bot.json"
    if not diesel_bot.exists():
        diesel_bot.write_text(json.dumps({"config": {"ativo": True, "token": "0000000000:DEMONSTRACAO-DIESEL", "offset": 0,
                                                     "gestores": ["1002"], "alerta_valor": 1500, "hora_relatorio": "07:00",
                                                     "relatorios": {"semana": True, "quinzena": True, "mes": True},
                                                     "enviados": {}, "ultima_verificacao": None, "ultimo_erro": None},
                                          "itens": [], "conversas": {}}, ensure_ascii=False, indent=2), encoding="utf-8")

    caminho = config.DADOS_DIR / "caixa_bot.json"
    if not caminho.exists():
        caminho.write_text(json.dumps({"config": {"ativo": True, "token": "0000000000:DEMONSTRACAO-CAIXA", "offset": 0,
                                                  "ultima_verificacao": None, "ultimo_erro": None},
                                       "itens": [], "conversas": {}}, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- preparação e abertura


def preparar(pasta: Path, refazer: bool = False) -> dict | None:
    """Monta os dados de exemplo se ainda não existirem (ou de novo, com ``refazer``)."""
    if refazer and pasta.exists():
        if pasta.name != "dados_demo":
            raise ValueError(f"Recusado: {pasta} não é a pasta da demonstração (dados_demo); nada foi apagado.")
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    if (pasta / "boletos.db").exists():
        return None
    resumo = montar_dados()
    from . import contexto as ctx

    ctx.planilha.exportar_agora()  # a planilha boletos.xlsx da demonstração já sai pronta
    ctx.empresas.exportar_agora()
    ctx.diesel.exportar_agora()
    return resumo


def main() -> None:
    pasta = _ambiente()
    argumentos = set(sys.argv[1:])
    resumo = preparar(pasta, refazer="--refazer" in argumentos)
    if resumo:
        print(f"  Dados de demonstração criados em {pasta}:")
        print("  " + " · ".join(f"{valor} {nome}" for nome, valor in resumo.items()))
    else:
        print(f"  Usando os dados de demonstração que já existem em {pasta} (use --refazer para montar de novo).")
    if "--dados" in argumentos:
        return
    from .__main__ import main as abrir

    sys.argv = [sys.argv[0]]
    abrir()


if __name__ == "__main__":
    main()

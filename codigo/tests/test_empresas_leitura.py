"""Leitura dos arquivos do bot de notas: NF-e (XML e DANFE), cheque, comprovante e print do fechamento."""

from datetime import date

from app.empresas import leitura

XML_NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
 <NFe><infNFe Id="NFe35260803880985000185550010000068591000068591" versao="4.00">
  <ide><cUF>35</cUF><nNF>6859</nNF><serie>1</serie><dhEmi>2026-07-29T10:12:00-03:00</dhEmi></ide>
  <emit><CNPJ>03880985000185</CNPJ><xNome>PROSPERA INDUSTRIA E SERVICOS LTDA</xNome></emit>
  <dest><CNPJ>12345678000195</CNPJ><xNome>IMAPAL CONSTRUCOES LTDA</xNome></dest>
  <det nItem="1"><prod><cProd>101</cProd><xProd>BRITA 01</xProd><NCM>25171000</NCM><uCom>M3</uCom>
    <qCom>12.0000</qCom><vUnCom>158.8000000000</vUnCom><vProd>1905.60</vProd><xPed>7043</xPed></prod></det>
  <det nItem="2"><prod><cProd>102</cProd><xProd>PEDRISCO</xProd><uCom>M3</uCom>
    <qCom>5.0000</qCom><vUnCom>100.0000000000</vUnCom><vProd>500.00</vProd><xPed>7043</xPed></prod></det>
  <total><ICMSTot><vNF>2405.60</vNF></ICMSTot></total>
  <infAdic><infCpl>Pedido 7043 - entrega na obra</infCpl></infAdic>
 </infNFe></NFe>
</nfeProc>"""

DANFE = """PROSPERA INDUSTRIA E SERVICOS LTDA
DANFE
DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRONICA
0 - ENTRADA
1 - SAIDA
Nº 000.006.859 SERIE 1
CHAVE DE ACESSO
3526 0803 8809 8500 0185 5500 1000 0068 5910 0006 8591
NATUREZA DA OPERACAO
VENDA DE MERCADORIA
DESTINATARIO/REMETENTE
NOME/RAZAO SOCIAL
IMAPAL CONSTRUCOES LTDA 12.345.678/0001-95
DATA DA EMISSAO
29/07/2026
DADOS DO PRODUTO / SERVICOS
CODIGO DESCRICAO DO PRODUTO NCM CST CFOP UNID QUANT VALOR UNIT VALOR TOTAL
101 BRITA 01 25171000 000 5102 M3 12,0000 158,80 1.905,60
102 PEDRISCO 25171000 000 5102 M3 5,0000 100,00 500,00
CALCULO DO IMPOSTO
VALOR TOTAL DA NOTA
2.405,60
DADOS ADICIONAIS
Pedido 7043
"""

CHEQUE = """BANCO COOPERATIVO SICREDI S.A.
COOP 3003 AG 0710 C1
PAGUE POR ESTE CHEQUE A QUANTIA DE R$ 1.905,60
A IMAPAL CONSTRUCOES LTDA OU A SUA ORDEM
MIRASSOL 10 DE AGOSTO DE 2026
COMPENSAVEL EM SAO JOSE DO RIO PRETO
BOM PARA 10/09/2026
<74807101< 0180001235: 000004567898>
"""

# OCR real de uma foto de cheque Sicredi (frente e verso, lida nas quatro orientações): é assim que chega
# pelo bot — texto embaralhado, "Bom p/" quase ilegível e os pedidos escritos à mão no verso.
CHEQUE_FOTO = """SICREDI BIOMAS cheque a quantia de Pague por este 018 Comp.
06 48 AV. SERGIPE, 1202 33.022.690/0011–00 AMAZONAS – SICREDI BIOMAS Sicredi
PAC S.J. QUATRO MARCOS - MT CONFECÇÃO: 0812025 NOROESTE DE MATO GROSSO ACREE COOP DE CRED POUP E INVEST DO 748 Banco
PrespeneIndus tra buabre mily 8058 Coop
6
CHEQUE ESPECIAL 62
9894-8 Conta n°
392855950001-04 8
PPmP 2426 CLIENTE BANCARIO DESDE 11 12020 JOSE PAZETE CIA LTDA Lomenerolemsenvdcos A00 Série
duesentos pubnta gete pear a pessenta centavos 000616 Cheque n°
elembro 8
1105108 4.287.60#
2036 ou à sua ordem e centavos acima
Comp. Banco Coop C1 Conta n° C2 Série Cheque n° C3 4.287.60#
018 748 8058 6 9 9894-8 7. A00 0006 16 5
cheque a quantia de Pague por este Buatre mil dugentos retento gete preare pesento cntavos
e centavos acima
PrespereIndustre Comenetoaservcos ou à sua ordem
SicrediCHEQUE ESECIAL 18itembre de 2006
COOP DE CRED POUP E INVEST DO
NOROESTE DE MATOGROSSOACREE JOSE PAZETE CIA LTDA
AMAZONAS – SICREDI BIOMAS 392855950001-04
33.022.690/0011–00
SICREDI BIOMAS 1105108
AV. SERGIPE, 1202 CLIENTE BANCARIO DESDE 11 12020
PAC S.J. QUATRO MARCOS - MTCONFECÇÃO: 0812025
Pom p) 24/0926
e centavos acima ou à sua ordem 9000
#09t8c de 1105108 Pom p) 24lo9126
8 5
Cheque n° 0006 16 JOSE PAZETE CIA LTDA CLIENTE BANCARIO DESDE 11 12020
Série A00 392855950001-04
8
Conta n° 9894-8
0 prul onpomg CHEQUE ESPECIAL
do03 8058 COOP DE CRED POUP E INVEST DO NOROESTE DE MATOGROSSO ACREE
Banco 748 AMAZONAS – SICREDI BIOMAS 33.022.690/0011–00 SICREDI BIOMAS AV. SERGIPE, 1202
duos 018
Pom P) 2409126 i"n y m
1105108 CLIENTE BANCARIO DESDE 11 12020 AV. SERGIPE, 1202
SICREDI BIOMAS
33.022.690/0011–00
392855950001-04 AMAZONAS – SICREDI BIOMAS
JOSE PAZETE CIA LTDA NOROESTE DE MATOGROSSOACREE
COOP DE CRED POUP E INVEST DO
de CHEQUE ESPECIAL
2006
ou à sua ordem arohanet
e centavos acima
gele auymp ap eueno e an
2.87.60± S 0006 16 A00 7. 9894-8 6 9 8058 748 018
R$ Conta n° 10 do03 duoo
13689-2 996)
08%t
1 Peddos= 7200-7201-7219-7245-7255
7301- 7310- 7307
1966 Reddos: 7200-7201-7219-7245-7255
2280 - 7301 - 7310- 7307
13689-2
sst-Sht-6/8t-10Ct-005t=spp toet -OIEt-1oet
08%t
1966 13689-7
toet -01Et-10et- 08tt 996)
ss ōt -Sht -b/ot - 10Ct -00st =spp"""

COMPROVANTE_PIX = """Comprovante de transferência Pix
Valor R$ 1.905,60
Data do pagamento 20/08/2026 14:35
Pagador
IMAPAL CONSTRUCOES LTDA
12.345.678/0001-95
Recebedor
PROSPERA INDUSTRIA E SERVICOS LTDA
ID da transação E1234567820260820143500123456
Descrição NF 6859 e 6869
"""

PRINT_FECHAMENTO = """Prospera Industria E Serviços LTDA 03.880.985/0001-85
Fechamento Imapal
DATA MATERIAL UNIDADE QAUNT. VALOR UNI. VALOR TOTAL NOTA FICAL N PEDIDO
29/07/2026 Brita 01 M³ 12 158,8 R$ 1.905,60 6859 7043
30/07/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6869 7053
10/08/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6822 7110
14/08/2026 Pedrisco M³ 12 158,8 R$ 1.905,60 6951 7139
17/08/2026 Brita 01 M³ 12 158,8 R$ 1.905,60 6958 7147
R$ 9.528,00
"""


# --------------------------------------------------------------------------- nota fiscal


def test_le_a_nota_fiscal_pelo_xml():
    nota = leitura.ler_xml_nota(XML_NFE.encode("utf-8"))
    assert nota["numero_nf"] == "6859" and nota["data"] == date(2026, 7, 29)
    assert nota["destinatario"] == {"nome": "IMAPAL CONSTRUCOES LTDA", "cnpj": "12345678000195"}
    assert nota["emitente"]["cnpj"] == "03880985000185"
    assert nota["valor_total"] == 2405.60 and nota["pedidos"] == ["7043"]
    assert nota["itens"][0] == {"material": "BRITA 01", "unidade": "M3", "quantidade": 12.0,
                                "valor_unitario": 158.8, "valor_total": 1905.6, "pedido": "7043"}
    assert nota["confianca"] == 1.0


def test_le_o_danfe_pelo_texto():
    assert leitura.classificar(DANFE) == "nota"
    nota = leitura.extrair_nota(DANFE)
    assert nota["numero_nf"] == "6859" and nota["data"] == date(2026, 7, 29)
    assert "IMAPAL" in nota["destinatario"]["nome"] and nota["destinatario"]["cnpj"] == "12345678000195"
    assert nota["valor_total"] == 2405.60 and nota["pedidos"] == ["7043"]
    assert [(i["material"], i["unidade"], i["quantidade"], i["valor_total"]) for i in nota["itens"]] == [
        ("BRITA 01", "M³", 12.0, 1905.6), ("PEDRISCO", "M³", 5.0, 500.0)]


def test_numero_da_nota_sai_da_chave_de_acesso():
    """No DANFE fotografado o número impresso às vezes sai errado; a chave de acesso não deixa dúvida."""
    chave = "35260803880985000185" + "55" + "001" + "000007120" + "1" + "12345678" + "9"
    grupos = " ".join(chave[i:i + 4] for i in range(0, 44, 4))
    texto = f"DANFE\nCHAVE DE ACESSO\n{grupos}\nNº 2.000.000.000.201 SERIE 1"
    assert leitura._numero_pela_chave(texto) == "7120"
    assert leitura.extrair_nota(texto)["numero_nf"] == "7120"
    assert leitura._numero_pela_chave("sem chave nenhuma") == ""


def test_analisar_reconhece_o_xml_sem_precisar_de_ocr():
    analise = leitura.analisar(XML_NFE.encode("utf-8"), "nfe-6859.xml")
    assert analise["tipo"] == "nota" and analise["dados"]["numero_nf"] == "6859"
    assert leitura.publico(analise)["dados"]["data"] == "2026-07-29"


# --------------------------------------------------------------------------- cheque


def test_le_o_cheque_pela_linha_cmc7_e_pelos_rotulos():
    assert leitura.classificar(CHEQUE) == "cheque"
    cheque = leitura.extrair_cheque(CHEQUE, legenda="Cheque da Imapal, pedido 7043")
    assert cheque["banco"] == "Sicredi" and cheque["agencia"] == "0710"
    assert cheque["numero"] == "123" and cheque["conta"] == "456789"
    assert cheque["coop"] == "3003"
    assert cheque["valor"] == 1905.60 and cheque["vencimento"] == date(2026, 9, 10)
    assert cheque["pedidos"] == ["7043"]


def test_le_a_foto_de_um_cheque_de_verdade():
    """Frente e verso fotografados: valor, "bom para" à mão, dados da conta e os pedidos do verso."""
    assert leitura.classificar(CHEQUE_FOTO) == "cheque"
    cheque = leitura.extrair_cheque(CHEQUE_FOTO)

    assert cheque["valor"] == 4287.60
    assert cheque["vencimento"] == date(2026, 9, 24)  # "Bom p/ 24/09/26" escrito no canto
    assert cheque["banco"] == "Sicredi" and cheque["coop"] == "8058"
    assert cheque["conta"] == "98948" and cheque["numero"] == "616"
    assert cheque["emitente"] == "JOSE PAZETE CIA LTDA"
    assert "39285595000104" in cheque["documentos"]  # CNPJ de quem assinou
    assert cheque["pedidos"] == ["7200", "7201", "7219", "7245", "7255", "7301", "7307", "7310"]
    assert cheque["confianca"] >= 0.9


def test_data_escrita_a_mao_aceita_ruido_do_ocr():
    from datetime import date as tipo_data

    hoje = tipo_data(2026, 9, 18)
    assert leitura._data_escrita_a_mao("Bom p/ 24/09/26", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("Pom p) 24lo9126", hoje) == date(2026, 9, 24)  # "/" virou "l", "0" virou "o"
    assert leitura._data_escrita_a_mao("Pom P) 2409126", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("24/09/2026", hoje) == date(2026, 9, 24)
    assert leitura._data_escrita_a_mao("nada de data aqui", hoje) is None
    assert leitura._data_escrita_a_mao("01/01/2019", hoje) is None  # fora da janela de um cheque


def test_numeros_soltos_do_cheque_nao_viram_pedidos():
    """Conta, cooperativa e endereço não podem ser confundidos com a lista de pedidos do verso."""
    frente = "018 748 8058 6 9 9894-8 7. A00 0006 16 5\nAV. SERGIPE, 1202 33.022.690/0011-00"
    assert leitura._numeros_em_sequencia(frente) == []
    verso = "Peddos= 7200-7201-7219-7245-7255\n7301- 7310- 7307"
    assert leitura._numeros_em_sequencia(verso) == ["7200", "7201", "7219", "7245", "7255", "7301", "7307", "7310"]


def test_cmc7_fora_de_ordem_nao_quebra():
    assert leitura.ler_cmc7("sem numeros aqui") == {}
    assert leitura.ler_cmc7("748071010000123019000045678908")["banco_codigo"] == "748"


# --------------------------------------------------------------------------- comprovante


def test_le_o_comprovante_de_pix_com_as_notas_citadas():
    assert leitura.classificar(COMPROVANTE_PIX) == "comprovante"
    dados = leitura.extrair_comprovante(COMPROVANTE_PIX)
    assert dados["forma"] == "Pix" and dados["valor"] == 1905.60
    assert dados["data"] == date(2026, 8, 20) and dados["hora"] == "14:35"
    assert dados["notas"] == ["6859", "6869"]
    assert dados["id_transacao"].startswith("E1234567820260820")
    assert "IMAPAL" in dados["pagador"]


def test_numeros_de_nf_e_pedido_na_legenda():
    assert leitura.numeros_de_nf("Pagamento das NF 6859, 6869 e 6870") == ["6859", "6869", "6870"]
    assert leitura.numeros_de_pedido("cheque do pedido 7043 e 7053") == ["7043", "7053"]
    assert leitura.numeros_de_nf("sem nada aqui") == []


# --------------------------------------------------------------------------- print do fechamento (Parte 5)


def test_le_o_print_do_fechamento_linha_por_linha():
    assert leitura.classificar(PRINT_FECHAMENTO) == "fechamento"
    lido = leitura.ler_fechamento(PRINT_FECHAMENTO)
    assert lido["empresa"] == "Imapal"
    assert len(lido["linhas"]) == 5 and lido["total"] == 9528.00
    assert lido["linhas"][0] == {"data": date(2026, 7, 29), "material": "Brita 01", "unidade": "M³",
                                 "quantidade": 12.0, "valor_unitario": 158.8, "valor_total": 1905.6,
                                 "numero_nf": "6859", "pedido": "7043"}
    assert lido["linhas"][-1]["numero_nf"] == "6958"

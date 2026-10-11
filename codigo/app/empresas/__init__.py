"""Módulo Empresas: controle do que os clientes têm a pagar (vendas a prazo) e o fechamento de cada um.

Enquanto o restante do sistema cuida do que a empresa **paga** (boletos e Pix), este módulo cuida do que ela
**recebe**:

* **Notas fiscais** — cada item vendido a prazo vira uma linha do fechamento da empresa (data, material,
  unidade, quantidade, valor unitário, valor total, número da NF e número do pedido);
* **Cheques pré-datados** — guardados com banco, agência, cooperativa, número, valor e a data do depósito,
  com aviso de vencimento no mesmo modelo dos boletos;
* **Recebimentos** — Pix, TED, depósitos e cheques compensados, que dão **baixa automática** nas notas
  fiscais citadas no comprovante;
* **Fechamento** — todo dia 20 (ou no dia configurado) o sistema fecha o período de cada empresa e gera o
  relatório no formato usado hoje, mostrando o total, o que já foi recebido e quanto falta.

Tudo chega pelo **bot de notas fiscais** do Telegram (um bot só para isso), que reconhece sozinho se o
arquivo é uma nota fiscal, um cheque ou um comprovante.
"""

# Anexo A7 — Exemplos reais de resposta da API

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Resposta **real** de cada rota `GET` da API, obtida rodando o sistema sobre uma **cópia dos dados de demonstração** (nada sai para fora). Listas foram cortadas em 2 itens e textos em 80 caracteres; tokens e senhas aparecem como `••••`. Use como referência do **formato** de cada resposta (nomes e tipos dos campos).

## `GET /api/status`

Chamado como `/api/status` → HTTP 200 · `application/json`

```json
{
  "versao": "1.8.0",
  "nome_app": "Fin Pro",
  "demonstracao": true,
  "ocr": true,
  "ocr_modelo": null,
  "ia": false,
  "ia_modelo": null,
  "ia_automatica": false,
  "heic": true,
  "planilha": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81\\boletos.xlsx",
  "pasta_dados": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81",
  "max_upload_mb": 100,
  "gravacao_pendente": 0,
  "modo_app": false,
  "hoje": "2026-10-10",
  "backup": {
    "situacao": "desligado",
    "ultimo_sucesso": null,
    "dias_sem_backup": null
  }
}
```

## `GET /api/versao`

Chamado como `/api/versao` → HTTP 200 · `application/json`

```json
{
  "versao": "1.8.0",
  "data": "2026-10-07",
  "historico": [
    {
      "versao": "1.8.0",
      "data": "2026-10-07",
      "titulo": "Documentação completa, especificação técnica e kit de reconstrução",
      "itens": [
        "Manual de uso do sistema inteiro (`DOCUMENTACAO_FIN_PRO.md`).",
        "Especificação técnica em 27 documentos, com anexos gerados do próprio código.",
        "… mais 2 item(ns)"
      ]
    },
    {
      "versao": "1.7.0",
      "data": "2026-10-06",
      "titulo": "Diesel em reais, relatório em três níveis e relatório geral",
      "itens": [
        "Saldo do diesel passou a ser em reais (compras pagas menos o valor de cada ab…",
        "Relatório do diesel em três níveis: Simples, Detalhado e Completo, na tela, n…",
        "… mais 2 item(ns)"
      ]
    },
    "… mais 7 item(ns)"
  ],
  "disponivel": true,
  "commit": "b68d5fb",
  "commit_data": "2026-10-10T15:46:57-04:00",
  "pendentes": 32,
  "arquivos_pendentes": [
    "DOCUMENTACAO_FIN_PRO.md",
    "Kit - Novo Fin Pro/CLAUDE.md",
    "… mais 28 item(ns)"
  ],
  "versoes_guardadas": 1
}
```

## `GET /api/acesso/estado`

Chamado como `/api/acesso/estado` → HTTP 200 · `application/json`

```json
{
  "protegido": true,
  "autorizado": true,
  "local": true,
  "rede_sem_senha": false,
  "usuarios": true,
  "usuario": null,
  "administrador": false,
  "exigir_login_no_computador": false,
  "pedir_login_ao_abrir": false,
  "tem_administrador": true
}
```

## `GET /api/gravacao`

Chamado como `/api/gravacao` → HTTP 200 · `application/json`

```json
{
  "pendentes": 0,
  "bloqueada": false,
  "ultima_tentativa": null,
  "ultimo_erro": null,
  "ultimo_resultado": null,
  "itens": []
}
```

## `GET /api/painel`

Chamado como `/api/painel` → HTTP 200 · `application/json`

```json
{
  "hoje": "2026-10-10",
  "indicadores": {
    "total_qtd": 59,
    "pendentes_qtd": 12,
    "pendentes_valor": 28774.38,
    "vencidos_qtd": 6,
    "vencidos_valor": 14013.07,
    "vencidos_boletos_qtd": 4,
    "vencidos_pix_qtd": 2,
    "proximos7_qtd": 2,
    "proximos7_valor": 1809.15,
    "pagos_mes_qtd": 0,
    "pagos_mes_valor": 0.0,
    "juros_mes_qtd": 0,
    "juros_mes_valor": 0.0,
    "lancados_mes_qtd": 0,
    "lancados_mes_valor": 0.0
  },
  "serie_mensal": [
    {
      "mes": "2026-05-01",
      "rotulo": "mai/26",
      "atual": false,
      "pago": 0.0,
      "vencido": 0.0,
      "a_vencer": 0.0
    },
    {
      "mes": "2026-06-01",
      "rotulo": "jun/26",
      "atual": false,
      "pago": 17760.03,
      "vencido": 0.0,
      "a_vencer": 0.0
    },
    "… mais 10 item(ns)"
  ],
  "vencidos": [
    {
      "id": 36,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "05038.04416 88388.875133 65805.674790 2 22312330870449",
      "codigo_barras": null,
      "beneficiario": "DISTRIBUIDORA DE LUBRIFICANTES",
      "documento_beneficiario": "33.444.555/0001-66",
      "numero_documento": "719716/08",
      "vencimento": "2026-09-23",
      "valor": 3010.57,
      "emissor": "Itaú",
      "tipo": "Cobrança",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Combustível e Veículos",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "boleto",
      "situacao": "vencido",
      "dias_para_vencer": -17,
      "linha_digitos": "05038044168838887513365805674790222312330870449"
    },
    {
      "id": 38,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "96460.20928 51852.206136 45372.456477 1 03369926109211",
      "codigo_barras": null,
      "beneficiario": "POSTO SAO JORGE LTDA",
      "documento_beneficiario": "12.345.678/0001-95",
      "numero_documento": "419588/07",
      "vencimento": "2026-09-28",
      "valor": 6126.11,
      "emissor": "Bradesco",
      "tipo": "Cobrança",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Combustível e Veículos",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "boleto",
      "situacao": "vencido",
      "dias_para_vencer": -12,
      "linha_digitos": "96460209285185220613645372456477103369926109211"
    },
    "… mais 4 item(ns)"
  ],
  "proximos": [
    {
      "id": 41,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "58707.03713 52835.923225 07527.109329 7 20641165225810",
      "codigo_barras": null,
      "beneficiario": "DISTRIBUIDORA DE LUBRIFICANTES",
      "documento_beneficiario": "33.444.555/0001-66",
      "numero_documento": "653184/02",
      "vencimento": "2026-10-12",
      "valor": 1256.74,
      "emissor": "Itaú",
      "tipo": "Cobrança",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Combustível e Veículos",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "boleto",
      "situacao": "a_vencer",
      "dias_para_vencer": 2,
      "linha_digitos": "58707037135283592322507527109329720641165225810"
    },
    {
      "id": 14,
      "data_lancamento": "2026-09-29T16:54:00",
      "recebedor": "Maria da Limpeza",
      "tipo_chave": "celular",
      "chave": "+5517999887766",
      "valor": 552.41,
      "vencimento": "2026-10-14",
      "centro_custo": "Escritório",
      "descricao": "Serviços de limpeza",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "txid": "",
      "copia_e_cola": null,
      "observacoes": "",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "pix",
      "beneficiario": "Maria da Limpeza",
      "situacao": "a_vencer",
      "dias_para_vencer": 4,
      "tipo_chave_rotulo": "Celular",
      "chave_formatada": "(17) 99988-7766"
    },
    "… mais 4 item(ns)"
  ],
  "top_beneficiarios": [
    {
      "beneficiario": "POSTO SAO JORGE LTDA",
      "quantidade": 6,
      "valor": 22287.7
    },
    {
      "beneficiario": "MAXIMA PARAFUSOS LTDA",
      "quantidade": 6,
      "valor": 21445.38
    },
    "… mais 4 item(ns)"
  ],
  "recentes": [
    {
      "id": 45,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "15524.66504 22174.689983 02808.696985 0 23655045992147",
      "codigo_barras": null,
      "beneficiario": "COMERCIAL DE FERRO E ACO",
      "documento_beneficiario": "31.222.111/0001-77",
      "numero_documento": "122743/02",
      "vencimento": "2026-10-23",
      "valor": 5148.6,
      "emissor": "Santander",
      "tipo": "Cobrança",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Materiais",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "boleto",
      "situacao": "a_vencer",
      "dias_para_vencer": 13,
      "linha_digitos": "15524665042217468998302808696985023655045992147"
    },
    {
      "id": 44,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "44492.61914 52652.176605 88590.349547 5 51870487189320",
      "codigo_barras": null,
      "beneficiario": "OFICINA DIESEL MIRASSOL",
      "documento_beneficiario": "27.888.777/0001-30",
      "numero_documento": "221096/02",
      "vencimento": "2026-10-22",
      "valor": 3043.7,
      "emissor": "Bradesco",
      "tipo": "Cobrança",
      "status": "Pendente",
      "data_pagamento": null,
      "valor_pago": null,
      "juros_multa": null,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Manutenção",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "tipo_pagamento": "boleto",
      "situacao": "a_vencer",
      "dias_para_vencer": 12,
      "linha_digitos": "44492619145265217660588590349547551870487189320"
    },
    "… mais 4 item(ns)"
  ]
}
```

## `GET /api/previsao`

Chamado como `/api/previsao` → HTTP 200 · `application/json`

```json
{
  "hoje": "2026-10-10",
  "semanas": [
    {
      "inicio": "2026-10-10",
      "fim": "2026-10-16",
      "total": 1809.15,
      "boletos": 1256.74,
      "pix": 552.41,
      "quantidade": 2,
      "itens": [
        {
          "tipo": "boleto",
          "id": 41,
          "nome": "DISTRIBUIDORA DE LUBRIFICANTES",
          "valor": 1256.74,
          "vencimento": "2026-10-12",
          "centro_custo": "Combustível e Veículos"
        },
        {
          "tipo": "pix",
          "id": 14,
          "nome": "Maria da Limpeza",
          "valor": 552.41,
          "vencimento": "2026-10-14",
          "centro_custo": "Escritório"
        }
      ]
    },
    {
      "inicio": "2026-10-17",
      "fim": "2026-10-23",
      "total": 12952.16,
      "boletos": 12952.16,
      "pix": 0.0,
      "quantidade": 4,
      "itens": [
        {
          "tipo": "boleto",
          "id": 42,
          "nome": "TRANSPORTES RODRIGUES ME",
          "valor": 3665.55,
          "vencimento": "2026-10-19",
          "centro_custo": "Fretes"
        },
        {
          "tipo": "boleto",
          "id": 43,
          "nome": "POSTO SAO JORGE LTDA",
          "valor": 1094.31,
          "vencimento": "2026-10-21",
          "centro_custo": "Combustível e Veículos"
        },
        "… mais 2 item(ns)"
      ]
    },
    "… mais 6 item(ns)"
  ],
  "em_atraso": {
    "total": 14013.07,
    "quantidade": 6,
    "itens": [
      {
        "tipo": "boleto",
        "id": 36,
        "nome": "DISTRIBUIDORA DE LUBRIFICANTES",
        "valor": 3010.57,
        "vencimento": "2026-09-23",
        "centro_custo": "Combustível e Veículos"
      },
      {
        "tipo": "boleto",
        "id": 38,
        "nome": "POSTO SAO JORGE LTDA",
        "valor": 6126.11,
        "vencimento": "2026-09-28",
        "centro_custo": "Combustível e Veículos"
      },
      "… mais 4 item(ns)"
    ]
  },
  "sem_vencimento": {
    "total": 0.0,
    "quantidade": 0
  },
  "totais": {
    "7_dias": 1809.15,
    "30_dias": 14761.31,
    "periodo": 14761.31,
    "com_atraso": 28774.38
  }
}
```

## `GET /api/sistema/inicializacao`

Chamado como `/api/sistema/inicializacao` → HTTP 200 · `application/json`

```json
{
  "disponivel": true,
  "ativo": true,
  "minimizado": false
}
```

## `GET /api/app`

Chamado como `/api/app` → HTTP 200 · `application/json`

```json
{
  "modo_app": false,
  "local": true,
  "preferencias": {
    "fechar_para_bandeja": true,
    "minimizado_ao_iniciar": false,
    "aviso_bandeja_mostrado": true
  },
  "inicializacao": {
    "disponivel": true,
    "ativo": true,
    "minimizado": false
  },
  "atalhos": {
    "disponivel": true,
    "criados": []
  }
}
```

## `GET /api/rede`

Chamado como `/api/rede` → HTTP 200 · `application/json`

```json
{
  "ativo": false,
  "via_env": false,
  "rodando": false,
  "porta": 8000,
  "enderecos": [
    "192.168.0.124",
    "192.168.80.1",
    "… mais 1 item(ns)"
  ],
  "urls": [
    "http://192.168.0.124:8000",
    "http://192.168.80.1:8000",
    "… mais 1 item(ns)"
  ],
  "senha_definida": false,
  "erro": null,
  "acessos": [],
  "senha_via_env": false,
  "local": true
}
```

## `GET /api/rede/qrcode.svg`

Chamado como `/api/rede/qrcode.svg` → HTTP 200 · `image/svg+xml`

(arquivo/conteúdo não JSON, 1237 bytes)

## `GET /api/saude`

Chamado como `/api/saude` → HTTP 200 · `application/json`

```json
{
  "situacao": "ok",
  "versao": "1.8.0",
  "iniciado_em": "2026-10-10T16:12:16",
  "em_execucao_ha": "0d 0h 0min",
  "atualizado_em": "2026-10-10T16:12:17",
  "itens": [
    {
      "chave": "banco",
      "titulo": "Banco de dados e planilha",
      "situacao": "ok",
      "resumo": "45 boletos, 14 Pix e 101 registros de histórico.",
      "detalhes": {
        "pendente": false,
        "ultima": null,
        "erro": null,
        "excel_aberto": false,
        "ultima_importacao": null,
        "boletos": 45,
        "pix": 14,
        "caixa": 38,
        "historico": 101,
        "centros": 13,
        "banco": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81\\boletos.db",
        "tamanho_banco": 196608,
        "planilha": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81\\boletos.xlsx"
      }
    },
    {
      "chave": "empresas",
      "titulo": "Empresas e fechamentos",
      "situacao": "ok",
      "resumo": "Bot de notas recebendo de 2 pessoa(s)/grupo(s). 3 empresa(s), 37 linha(s) de …",
      "detalhes": {
        "pendente": false,
        "ultima": null,
        "erro": null,
        "excel_aberto": false,
        "ultima_importacao": null,
        "empresas": 3,
        "notas": 37,
        "cheques": 3,
        "recebimentos": 6,
        "historico": 58,
        "centros": 0,
        "banco": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81\\empresas.db",
        "tamanho_banco": 114688,
        "planilha": "C:\\Users\\FBIO~1\\AppData\\Local\\Temp\\finpro-amostras-y8xp_f81\\fechamentos.xlsx",
        "bot_ativo": true,
        "destinatarios": 2,
        "pendentes": 0,
        "agendador": false,
        "ultima_verificacao": null
      }
    },
    "… mais 9 item(ns)"
  ]
}
```

## `GET /api/usuarios/eu`

Chamado como `/api/usuarios/eu` → HTTP 200 · `application/json`

```json
{
  "protegido": true,
  "autorizado": true,
  "local": true,
  "rede_sem_senha": false,
  "usuarios": true,
  "usuario": null,
  "administrador": false,
  "exigir_login_no_computador": false,
  "pedir_login_ao_abrir": false,
  "tem_administrador": true
}
```

## `GET /api/usuarios`

Chamado como `/api/usuarios` → HTTP 403 · `application/json`

```json
{
  "detail": {
    "codigo": "admin_sem_senha",
    "mensagem": "Função restrita: crie a senha de administrador em Configurações."
  }
}
```

## `GET /api/backup`

Chamado como `/api/backup` → HTTP 200 · `application/json`

```json
{
  "ativo": false,
  "pasta": "",
  "horario": "12:30",
  "manter_dias": 30,
  "configurado_em": null,
  "ultimo": null,
  "ultimo_sucesso": null,
  "codigo": true,
  "pacote": "semanal",
  "manter_pacotes": 4,
  "ultimo_pacote": null,
  "falha_pacote": null,
  "verificacao": null,
  "situacao": "desligado",
  "dias_sem_backup": null,
  "destino": null,
  "executando": false,
  "com_codigo": true,
  "verificado": null,
  "problemas": [],
  "local": true,
  "sugestoes": [
    {
      "nome": "OneDrive",
      "pasta": "C:\\Users\\Fábio\\OneDrive"
    },
    {
      "nome": "Google Drive",
      "pasta": "G:\\Meu Drive"
    }
  ],
  "pacotes": []
}
```

## `GET /api/entrada`

Chamado como `/api/entrada` → HTTP 200 · `application/json`

```json
{
  "itens": [],
  "pendentes": 0,
  "config": {
    "email": {
      "ativo": false,
      "servidor": "",
      "porta": 993,
      "usuario": "",
      "senha": "",
      "pasta": "INBOX",
      "remetentes": "",
      "ultima_verificacao": null,
      "ultimo_erro": null
    },
    "telegram": {
      "ativo": false,
      "ultima_verificacao": null,
      "ultimo_erro": null
    }
  }
}
```

## `GET /api/entrada/{id_}`

Chamado como `/api/entrada/1` → HTTP 404 · `application/json`

```json
{
  "detail": {
    "codigo": "nao_encontrado",
    "mensagem": "Este arquivo não está mais na caixa de entrada."
  }
}
```

## `GET /api/boletos`

Chamado como `/api/boletos` → HTTP 200 · `application/json`

```json
{
  "itens": [
    {
      "id": 1,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "18801.97608 93288.183624 44165.111647 3 31540229802202",
      "codigo_barras": null,
      "beneficiario": "PREFEITURA MUNICIPAL - ISS",
      "documento_beneficiario": "45.123.987/0001-10",
      "numero_documento": "251481/04",
      "vencimento": "2026-06-10",
      "valor": 227.9,
      "emissor": "Caixa",
      "tipo": "Cobrança",
      "status": "Pago",
      "data_pagamento": "2026-06-10",
      "valor_pago": 227.9,
      "juros_multa": 0.0,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Impostos e Taxas",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "arquivos/13c7b8cc0137435b9bb516ef36cd5881.png",
      "comprovante_nome": "comprovante-PREFEITURA MUNICIPAL.png",
      "atualizado_em": "2026-09-29T16:54:00",
      "situacao": "pago",
      "dias_para_vencer": -122,
      "linha_digitos": "18801976089328818362444165111647331540229802202"
    },
    {
      "id": 2,
      "data_lancamento": "2026-09-29T16:54:00",
      "linha_digitavel": "85413.99502 98931.528436 09109.798059 1 18245550681082",
      "codigo_barras": null,
      "beneficiario": "POSTO SAO JORGE LTDA",
      "documento_beneficiario": "12.345.678/0001-95",
      "numero_documento": "158540/05",
      "vencimento": "2026-06-12",
      "valor": 499.8,
      "emissor": "Bradesco",
      "tipo": "Cobrança",
      "status": "Pago",
      "data_pagamento": "2026-06-13",
      "valor_pago": 499.8,
      "juros_multa": 0.0,
      "desconto": null,
      "observacoes": "",
      "centro_custo": "Combustível e Veículos",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "atualizado_em": "2026-09-29T16:54:00",
      "situacao": "pago",
      "dias_para_vencer": -120,
      "linha_digitos": "85413995029893152843609109798059118245550681082"
    },
    "… mais 23 item(ns)"
  ],
  "total": 45,
  "pagina": 1,
  "por_pagina": 25,
  "resumo": {
    "quantidade": 45,
    "valor_total": 151481.56,
    "valor_pendente": 26792.06,
    "valor_pago": 124689.5,
    "valor_vencido": 12583.16,
    "juros_multa": 945.68,
    "pagos_com_juros": 12
  }
}
```

## `GET /api/boletos/{id_}`

Chamado como `/api/boletos/1` → HTTP 200 · `application/json`

```json
{
  "id": 1,
  "data_lancamento": "2026-09-29T16:54:00",
  "linha_digitavel": "18801.97608 93288.183624 44165.111647 3 31540229802202",
  "codigo_barras": null,
  "beneficiario": "PREFEITURA MUNICIPAL - ISS",
  "documento_beneficiario": "45.123.987/0001-10",
  "numero_documento": "251481/04",
  "vencimento": "2026-06-10",
  "valor": 227.9,
  "emissor": "Caixa",
  "tipo": "Cobrança",
  "status": "Pago",
  "data_pagamento": "2026-06-10",
  "valor_pago": 227.9,
  "juros_multa": 0.0,
  "desconto": null,
  "observacoes": "",
  "centro_custo": "Impostos e Taxas",
  "arquivo": null,
  "arquivo_nome": null,
  "lancado_por": "",
  "pago_por": "",
  "comprovante": "arquivos/13c7b8cc0137435b9bb516ef36cd5881.png",
  "comprovante_nome": "comprovante-PREFEITURA MUNICIPAL.png",
  "atualizado_em": "2026-09-29T16:54:00",
  "situacao": "pago",
  "dias_para_vencer": -122,
  "linha_digitos": "18801976089328818362444165111647331540229802202"
}
```

## `GET /api/boletos/{id_}/arquivo`

Chamado como `/api/boletos/1/arquivo` → HTTP 404 · `application/json`

```json
{
  "detail": {
    "codigo": "arquivo_nao_encontrado",
    "mensagem": "Arquivo não encontrado."
  }
}
```

## `GET /api/boletos/{id_}/historico`

Chamado como `/api/boletos/1/historico` → HTTP 200 · `application/json`

```json
{
  "eventos": [
    {
      "quando": "2026-09-29T16:54",
      "acao": "Lançamento",
      "detalhes": "18801.97608 93288.183624 44165.111647 3 31540229802202",
      "usuario": ""
    }
  ]
}
```

## `GET /api/exportar`

Chamado como `/api/exportar` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 13556 bytes)

## `GET /api/pix`

Chamado como `/api/pix` → HTTP 200 · `application/json`

```json
{
  "itens": [
    {
      "id": 1,
      "data_lancamento": "2026-09-29T16:54:00",
      "recebedor": "Serralheria Aço Forte",
      "tipo_chave": "cnpj",
      "chave": "44.555.666/0001-01",
      "valor": 2238.53,
      "vencimento": "2026-07-19",
      "centro_custo": "Manutenção",
      "descricao": "Conserto da caçamba",
      "status": "Pago",
      "data_pagamento": "2026-07-19",
      "valor_pago": 2238.53,
      "juros_multa": null,
      "desconto": null,
      "txid": "",
      "copia_e_cola": null,
      "observacoes": "",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "arquivos/e0aa9541eab249e8a91b78f07ccf5582.png",
      "comprovante_nome": "pix-Serralheria Aço Fort.png",
      "atualizado_em": "2026-09-29T16:54:00",
      "situacao": "pago",
      "dias_para_vencer": -83,
      "tipo_chave_rotulo": "cnpj",
      "chave_formatada": "44.555.666/0001-01"
    },
    {
      "id": 2,
      "data_lancamento": "2026-09-29T16:54:00",
      "recebedor": "Serralheria Aço Forte",
      "tipo_chave": "cnpj",
      "chave": "44.555.666/0001-01",
      "valor": 2081.04,
      "vencimento": "2026-08-03",
      "centro_custo": "Manutenção",
      "descricao": "Conserto da caçamba",
      "status": "Pago",
      "data_pagamento": "2026-08-03",
      "valor_pago": 2081.04,
      "juros_multa": null,
      "desconto": null,
      "txid": "",
      "copia_e_cola": null,
      "observacoes": "",
      "arquivo": null,
      "arquivo_nome": null,
      "lancado_por": "",
      "pago_por": "",
      "comprovante": "arquivos/3b155a2bd8ed4efd8f19bbbf63532dd3.png",
      "comprovante_nome": "pix-Serralheria Aço Fort.png",
      "atualizado_em": "2026-09-29T16:54:00",
      "situacao": "pago",
      "dias_para_vencer": -68,
      "tipo_chave_rotulo": "cnpj",
      "chave_formatada": "44.555.666/0001-01"
    },
    "… mais 12 item(ns)"
  ],
  "total": 14,
  "pagina": 1,
  "por_pagina": 25,
  "resumo": {
    "quantidade": 14,
    "valor_total": 17162.34,
    "valor_pendente": 1982.32,
    "valor_pago": 15180.02,
    "valor_vencido": 1429.91,
    "juros_multa": 0.0,
    "pagos_com_juros": 0
  }
}
```

## `GET /api/pix/exportar`

Chamado como `/api/pix/exportar` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 7658 bytes)

## `GET /api/pix/{id_}`

Chamado como `/api/pix/1` → HTTP 200 · `application/json`

```json
{
  "id": 1,
  "data_lancamento": "2026-09-29T16:54:00",
  "recebedor": "Serralheria Aço Forte",
  "tipo_chave": "cnpj",
  "chave": "44.555.666/0001-01",
  "valor": 2238.53,
  "vencimento": "2026-07-19",
  "centro_custo": "Manutenção",
  "descricao": "Conserto da caçamba",
  "status": "Pago",
  "data_pagamento": "2026-07-19",
  "valor_pago": 2238.53,
  "juros_multa": null,
  "desconto": null,
  "txid": "",
  "copia_e_cola": null,
  "observacoes": "",
  "arquivo": null,
  "arquivo_nome": null,
  "lancado_por": "",
  "pago_por": "",
  "comprovante": "arquivos/e0aa9541eab249e8a91b78f07ccf5582.png",
  "comprovante_nome": "pix-Serralheria Aço Fort.png",
  "atualizado_em": "2026-09-29T16:54:00",
  "situacao": "pago",
  "dias_para_vencer": -83,
  "tipo_chave_rotulo": "cnpj",
  "chave_formatada": "44.555.666/0001-01"
}
```

## `GET /api/pix/{id_}/arquivo`

Chamado como `/api/pix/1/arquivo` → HTTP 404 · `application/json`

```json
{
  "detail": {
    "codigo": "arquivo_nao_encontrado",
    "mensagem": "Arquivo não encontrado."
  }
}
```

## `GET /api/pix/{id_}/historico`

Chamado como `/api/pix/1/historico` → HTTP 200 · `application/json`

```json
{
  "eventos": [
    {
      "quando": "2026-09-29T16:54",
      "acao": "Lançamento",
      "detalhes": ": 44.555.666/0001-01",
      "usuario": ""
    }
  ]
}
```

## `GET /api/pix/{id_}/copia-e-cola`

Chamado como `/api/pix/1/copia-e-cola` → HTTP 422 · `application/json`

```json
{
  "detail": {
    "codigo": "chave_invalida",
    "mensagem": "Não foi possível gerar o Pix Copia e Cola: Tipo de chave inválido."
  }
}
```

## `GET /api/pix/{id_}/qrcode.svg`

Chamado como `/api/pix/1/qrcode.svg` → HTTP 422 · `application/json`

```json
{
  "detail": {
    "codigo": "chave_invalida",
    "mensagem": "Não foi possível gerar o Pix Copia e Cola: Tipo de chave inválido."
  }
}
```

## `GET /api/comprovantes/busca`

Chamado como `/api/comprovantes/busca` → HTTP 200 · `application/json`

```json
{
  "itens": [
    {
      "tipo": "cheque",
      "tipo_rotulo": "Cheque",
      "id": 1,
      "nome": "Imapal Construções",
      "valor": 2480.81,
      "valor_pago": null,
      "juros_multa": 0.0,
      "data": "2026-10-05",
      "vencimento": "2026-10-05",
      "numero": "100",
      "detalhe": "Sicredi",
      "centro_custo": "",
      "pessoa": "Demonstração",
      "situacao": "Em carteira",
      "comprovante_id": "ea9aaadc6b584e8ba4ae01aaac231c2a",
      "comprovante_nome": "cheque-100.png",
      "original_id": null,
      "original_nome": "",
      "chave": "cheque-1",
      "comprovante_pdf": false
    },
    {
      "tipo": "cheque",
      "tipo_rotulo": "Cheque",
      "id": 3,
      "nome": "Terraplanagem Souza",
      "valor": 4196.8,
      "valor_pago": null,
      "juros_multa": 0.0,
      "data": "2026-10-02",
      "vencimento": "2026-10-02",
      "numero": "541",
      "detalhe": "Sicredi",
      "centro_custo": "",
      "pessoa": "Demonstração",
      "situacao": "Em carteira",
      "comprovante_id": "6a244af86bdb4dafa7268c8fa371c4d0",
      "comprovante_nome": "cheque-541.png",
      "original_id": null,
      "original_nome": "",
      "chave": "cheque-3",
      "comprovante_pdf": false
    },
    "… mais 98 item(ns)"
  ],
  "total": 137,
  "pagina": 1,
  "por_pagina": 100,
  "resumo": {
    "quantidade": 137,
    "com_arquivo": 137,
    "valor": 300771.16,
    "por_tipo": [
      {
        "tipo": "boleto",
        "rotulo": "Boleto",
        "quantidade": 31,
        "valor": 111948.47
      },
      {
        "tipo": "pix",
        "rotulo": "Pix",
        "quantidade": 11,
        "valor": 15180.02
      },
      "… mais 5 item(ns)"
    ]
  },
  "tipos": [
    {
      "tipo": "boleto",
      "rotulo": "Boleto"
    },
    {
      "tipo": "pix",
      "rotulo": "Pix"
    },
    "… mais 5 item(ns)"
  ]
}
```

## `GET /api/comprovantes/busca/zip`

Chamado como `/api/comprovantes/busca/zip` → HTTP 200 · `application/zip`

(arquivo/conteúdo não JSON, 3930188 bytes)

## `GET /api/boletos/{id_}/comprovante`

Chamado como `/api/boletos/1/comprovante` → HTTP 200 · `image/jpeg`

(arquivo/conteúdo não JSON, 43141 bytes)

## `GET /api/pix/{id_}/comprovante`

Chamado como `/api/pix/1/comprovante` → HTTP 200 · `image/jpeg`

(arquivo/conteúdo não JSON, 32356 bytes)

## `GET /api/centros`

Chamado como `/api/centros` → HTTP 200 · `application/json`

```json
{
  "centros": [
    {
      "nome": "Administrativo",
      "descricao": "Escritório, contabilidade, bancos e despesas gerais",
      "ativo": true,
      "boletos": 0,
      "pix": 0,
      "dinheiro": 0,
      "total": 0.0
    },
    {
      "nome": "Combustível e Veículos",
      "descricao": "Combustível, lubrificantes, peças e manutenção da frota",
      "ativo": true,
      "boletos": 9,
      "pix": 0,
      "dinheiro": 7,
      "total": 32772.56
    },
    "… mais 11 item(ns)"
  ]
}
```

## `GET /api/gastos`

Chamado como `/api/gastos` → HTTP 200 · `application/json`

```json
{
  "total": 172909.87,
  "quantidade": 85,
  "total_boletos": 151481.56,
  "total_pix": 17162.34,
  "total_dinheiro": 4265.97,
  "juros_multa": 945.68,
  "pagos_com_juros": 12,
  "sem_centro": 0.0,
  "centros": [
    {
      "centro": "Manutenção",
      "total": 49660.47,
      "boletos": 39203.03,
      "pix": 10035.85,
      "dinheiro": 421.59,
      "quantidade": 23,
      "pagos": 45950.81,
      "pendentes": 3709.66,
      "percentual": 28.7
    },
    {
      "centro": "Combustível e Veículos",
      "total": 32772.56,
      "boletos": 31135.02,
      "pix": 0.0,
      "dinheiro": 1637.54,
      "quantidade": 16,
      "pagos": 21284.83,
      "pendentes": 11487.73,
      "percentual": 19.0
    },
    "… mais 5 item(ns)"
  ],
  "series": [
    "Manutenção",
    "Combustível e Veículos",
    "… mais 5 item(ns)"
  ],
  "serie_mensal": [
    {
      "mes": "2026-06-01",
      "rotulo": "jun/26",
      "total": 17760.03,
      "centros": {
        "Impostos e Taxas": 4101.57,
        "Combustível e Veículos": 5871.76,
        "Manutenção": 4151.57,
        "Fretes": 1498.46,
        "Outros centros": 2136.67
      }
    },
    {
      "mes": "2026-07-01",
      "rotulo": "jul/26",
      "total": 40334.45,
      "centros": {
        "Manutenção": 15022.94,
        "Escritório": 7023.01,
        "Energia e Água": 13923.71,
        "Fretes": 1336.58,
        "Outros centros": 3028.21
      }
    },
    "… mais 3 item(ns)"
  ],
  "maiores": [
    {
      "nome": "POSTO SAO JORGE LTDA",
      "total": 22287.7,
      "quantidade": 6
    },
    {
      "nome": "MAXIMA PARAFUSOS LTDA",
      "total": 21445.38,
      "quantidade": 6
    },
    "… mais 8 item(ns)"
  ]
}
```

## `GET /api/gastos/exportar`

Chamado como `/api/gastos/exportar` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 8054 bytes)

## `GET /api/relatorios/fechamento`

Chamado como `/api/relatorios/fechamento` → HTTP 200 · `application/json`

```json
{
  "mes": "2026-10",
  "titulo": "outubro de 2026",
  "base": "vencimento",
  "gerado_em": "2026-10-10T16:12:19",
  "totais": {
    "quantidade": 10,
    "total": 19637.7,
    "pago": 0,
    "valor_documentos_pagos": 0,
    "juros_multa": 0,
    "desconto": 0,
    "pagos_com_atraso": 0,
    "em_aberto": 19637.7,
    "atrasado": 4876.39,
    "quantidade_atrasados": 4,
    "cancelados": 0,
    "boletos": 7,
    "pix": 3,
    "dinheiro": 0,
    "com_comprovante": 0,
    "sem_comprovante": 0
  },
  "por_centro": [
    {
      "centro_custo": "Fretes",
      "pago": 0.0,
      "em_aberto": 5167.69,
      "total": 5167.69,
      "quantidade": 2
    },
    {
      "centro_custo": "Materiais",
      "pago": 0.0,
      "em_aberto": 5148.6,
      "total": 5148.6,
      "quantidade": 1
    },
    "… mais 4 item(ns)"
  ],
  "pagos": [],
  "em_aberto": [
    {
      "tipo": "Boleto",
      "id": 39,
      "nome": "ENERGISA SUL SUDESTE",
      "documento": "949826/04",
      "vencimento": "2026-10-01",
      "valor": 1944.34,
      "valor_pago": null,
      "juros_multa": 0.0,
      "desconto": 0.0,
      "dias_atraso": 0,
      "status": "Pendente",
      "atrasado": true,
      "data_pagamento": null,
      "centro_custo": "Energia e Água",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "linha_digitavel": "22019.79767 89669.363734 92598.383265 1 33829272735107"
    },
    {
      "tipo": "Pix",
      "id": 12,
      "nome": "Contabilidade Silva",
      "documento": "contato@contabilidadesilva.com.br",
      "vencimento": "2026-10-02",
      "valor": 763.95,
      "valor_pago": null,
      "juros_multa": 0.0,
      "desconto": 0.0,
      "dias_atraso": 0,
      "status": "Pendente",
      "atrasado": true,
      "data_pagamento": null,
      "centro_custo": "Escritório",
      "pago_por": "",
      "comprovante": "",
      "comprovante_nome": "",
      "linha_digitavel": ""
    },
    "… mais 8 item(ns)"
  ],
  "cancelados": []
}
```

## `GET /api/relatorios/fechamento/arquivo`

Chamado como `/api/relatorios/fechamento/arquivo` → HTTP 200 · `application/pdf`

(arquivo/conteúdo não JSON, 5705 bytes)

## `GET /api/empresas`

Chamado como `/api/empresas` → HTTP 200 · `application/json`

```json
{
  "empresas": [
    {
      "id": 1,
      "nome": "Imapal Construções",
      "cnpj": "12.345.678/0001-95",
      "status": "Ativa",
      "dia_fechamento": 20,
      "competencia": "2026-10",
      "periodo": {
        "inicio": "2026-09-21",
        "fim": "2026-10-20"
      },
      "fechamento": {
        "quantidade": 4,
        "total": 9528.0,
        "recebido": 0.0,
        "falta": 9528.0,
        "em_cheque": 0,
        "notas": 4
      },
      "em_aberto": 28139.1,
      "atrasado": 18611.1,
      "cheques": {
        "quantidade": 1,
        "valor": 2480.81
      }
    },
    {
      "id": 3,
      "nome": "Terraplanagem Souza",
      "cnpj": "07.654.321/0001-88",
      "status": "Ativa",
      "dia_fechamento": 20,
      "competencia": "2026-10",
      "periodo": {
        "inicio": "2026-09-21",
        "fim": "2026-10-20"
      },
      "fechamento": {
        "quantidade": 3,
        "total": 7326.4,
        "recebido": 0.0,
        "falta": 7326.4,
        "em_cheque": 0,
        "notas": 3
      },
      "em_aberto": 19114.79,
      "atrasado": 11788.39,
      "cheques": {
        "quantidade": 1,
        "valor": 4196.8
      }
    },
    "… mais 1 item(ns)"
  ],
  "cadastro": [
    {
      "id": 1,
      "nome": "Imapal Construções",
      "razao_social": "",
      "cnpj": "12.345.678/0001-95",
      "apelidos": "Imapal, Imapal Construcoes",
      "dia_fechamento": 20,
      "contato": "Compras",
      "telefone": "(17) 3222-0000",
      "email": "",
      "chat_telegram": "",
      "status": "Ativa",
      "observacoes": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00",
      "arquivo": "",
      "arquivo_nome": ""
    },
    {
      "id": 2,
      "nome": "Jose Pazete & Cia",
      "razao_social": "",
      "cnpj": "39.285.595/0001-04",
      "apelidos": "Pazete, Jose Pazete",
      "dia_fechamento": 20,
      "contato": "Compras",
      "telefone": "(17) 3222-0000",
      "email": "",
      "chat_telegram": "",
      "status": "Ativa",
      "observacoes": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00",
      "arquivo": "",
      "arquivo_nome": ""
    },
    "… mais 1 item(ns)"
  ],
  "config": {
    "minha_empresa": {
      "nome": "Prospera Industria E Serviços LTDA",
      "cnpj": "03.880.985/0001-85"
    },
    "dia_fechamento": 20,
    "fechamento_automatico": true,
    "hora_envio": "08:00",
    "ultimo_fechamento": "",
    "bot": {
      "ativo": true,
      "token": "••••",
      "destinatarios": [
        {
          "chat_id": "2001",
          "nome": "Notas fiscais (grupo)",
          "empresa": "",
          "ativo": true
        },
        {
          "chat_id": "2002",
          "nome": "Almir",
          "empresa": "",
          "ativo": true
        }
      ],
      "chats": [],
      "ultima_verificacao": null,
      "ultimo_erro": null
    }
  }
}
```

## `GET /api/empresas/{id_}/fechamento`

Chamado como `/api/empresas/1/fechamento` → HTTP 200 · `application/json`

```json
{
  "empresa": "Imapal Construções",
  "empresa_id": 1,
  "cnpj": "12.345.678/0001-95",
  "competencia": "2026-10",
  "titulo": "outubro de 2026",
  "dia_fechamento": 20,
  "inicio": "2026-09-21",
  "fim": "2026-10-20",
  "fechado": false,
  "gerado_em": "2026-10-10T16:12:19",
  "linhas": [
    {
      "id": 10,
      "data": "2026-09-23",
      "empresa": "Imapal Construções",
      "material": "Brita 01",
      "unidade": "M³",
      "quantidade": 16.0,
      "valor_unitario": 158.8,
      "valor_total": 2540.8,
      "numero_nf": "7270",
      "pedido": "7225",
      "competencia": "2026-10",
      "status": "Em aberto",
      "valor_recebido": null,
      "data_recebimento": null,
      "cheque_id": null,
      "observacoes": "",
      "arquivo": "arquivos/3c0e4892bd4b4783b2d6cba052bc55bd.png",
      "arquivo_nome": "NF-7270.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    {
      "id": 11,
      "data": "2026-09-27",
      "empresa": "Imapal Construções",
      "material": "Brita 01",
      "unidade": "M³",
      "quantidade": 22.0,
      "valor_unitario": 158.8,
      "valor_total": 3493.6,
      "numero_nf": "7271",
      "pedido": "7097",
      "competencia": "2026-10",
      "status": "Em aberto",
      "valor_recebido": null,
      "data_recebimento": null,
      "cheque_id": null,
      "observacoes": "",
      "arquivo": "arquivos/4b37a800961644f4a0379bd1904a73ac.png",
      "arquivo_nome": "NF-7271.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    "… mais 2 item(ns)"
  ],
  "recebimentos": [],
  "cheques": [
    {
      "id": 1,
      "empresa": "Imapal Construções",
      "numero": "100",
      "vencimento": "2026-10-05",
      "valor": 2480.81,
      "banco": "Sicredi",
      "agencia": "0801",
      "coop": "8058",
      "conta": "98948-3",
      "emitente": "IMAPAL CONSTRUÇÕES",
      "pedidos": "",
      "notas": "",
      "status": "Em carteira",
      "data_deposito": null,
      "cmc7": "",
      "observacoes": "",
      "arquivo": "arquivos/ea9aaadc6b584e8ba4ae01aaac231c2a.png",
      "arquivo_nome": "cheque-100.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    }
  ],
  "totais": {
    "quantidade": 4,
    "total": 9528.0,
    "recebido": 0.0,
    "falta": 9528.0,
    "em_cheque": 0,
    "notas": 4
  }
}
```

## `GET /api/empresas/{id_}/fechamento/arquivo`

Chamado como `/api/empresas/1/fechamento/arquivo` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 6089 bytes)

## `GET /api/notas`

Chamado como `/api/notas` → HTTP 200 · `application/json`

```json
{
  "notas": [
    {
      "id": 37,
      "data": "2026-09-29",
      "empresa": "Terraplanagem Souza",
      "material": "Rachão",
      "unidade": "M³",
      "quantidade": 29.0,
      "valor_unitario": 96.4,
      "valor_total": 2795.6,
      "numero_nf": "7184",
      "pedido": "7191",
      "competencia": "2026-10",
      "status": "Em aberto",
      "valor_recebido": null,
      "data_recebimento": null,
      "cheque_id": null,
      "observacoes": "",
      "arquivo": "",
      "arquivo_nome": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    {
      "id": 24,
      "data": "2026-09-29",
      "empresa": "Jose Pazete & Cia",
      "material": "Pedrisco Comercial",
      "unidade": "M³",
      "quantidade": 15.0,
      "valor_unitario": 142.5,
      "valor_total": 2137.5,
      "numero_nf": "7289",
      "pedido": "7126",
      "competencia": "2026-10",
      "status": "Em aberto",
      "valor_recebido": null,
      "data_recebimento": null,
      "cheque_id": null,
      "observacoes": "",
      "arquivo": "",
      "arquivo_nome": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    "… mais 35 item(ns)"
  ],
  "total": 37
}
```

## `GET /api/cheques`

Chamado como `/api/cheques` → HTTP 200 · `application/json`

```json
{
  "cheques": [
    {
      "id": 2,
      "empresa": "Jose Pazete & Cia",
      "numero": "846",
      "vencimento": "2026-10-01",
      "valor": 2311.48,
      "banco": "Sicredi",
      "agencia": "0801",
      "coop": "8058",
      "conta": "98948-3",
      "emitente": "JOSE PAZETE & CIA",
      "pedidos": "",
      "notas": "",
      "status": "Em carteira",
      "data_deposito": null,
      "cmc7": "",
      "observacoes": "",
      "arquivo": "arquivos/be1220abc3d1416ca1c9fa2a4db69b42.png",
      "arquivo_nome": "cheque-846.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    {
      "id": 3,
      "empresa": "Terraplanagem Souza",
      "numero": "541",
      "vencimento": "2026-10-02",
      "valor": 4196.8,
      "banco": "Sicredi",
      "agencia": "0801",
      "coop": "8058",
      "conta": "98948-3",
      "emitente": "TERRAPLANAGEM SOUZA",
      "pedidos": "",
      "notas": "",
      "status": "Em carteira",
      "data_deposito": null,
      "cmc7": "",
      "observacoes": "",
      "arquivo": "arquivos/6a244af86bdb4dafa7268c8fa371c4d0.png",
      "arquivo_nome": "cheque-541.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    "… mais 1 item(ns)"
  ]
}
```

## `GET /api/recebimentos`

Chamado como `/api/recebimentos` → HTTP 200 · `application/json`

```json
{
  "recebimentos": [
    {
      "id": 6,
      "data": "2026-09-20",
      "hora": "10:30",
      "empresa": "Terraplanagem Souza",
      "forma": "Depósito",
      "valor": 2636.42,
      "pagador": "Terraplanagem Souza",
      "id_transacao": "E146324171241",
      "notas": "7173, 7174",
      "pedidos": "",
      "cheque_id": null,
      "aplicacoes": "#26 NF 7173: R$ 1.989,21; #27 NF 7174: R$ 647,21",
      "status": "Confirmado",
      "observacoes": "",
      "arquivo": "arquivos/6318a8576e2247f485b4c31e6f4ee682.png",
      "arquivo_nome": "depósito-Terraplanagem S.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    {
      "id": 4,
      "data": "2026-09-20",
      "hora": "10:30",
      "empresa": "Jose Pazete & Cia",
      "forma": "Depósito",
      "valor": 1015.52,
      "pagador": "Jose Pazete & Cia",
      "id_transacao": "E865605285848",
      "notas": "7280",
      "pedidos": "",
      "cheque_id": null,
      "aplicacoes": "#15 NF 7280: R$ 1.015,52",
      "status": "Confirmado",
      "observacoes": "",
      "arquivo": "arquivos/dae2921c2c454755a776b4ab2bd1babd.png",
      "arquivo_nome": "depósito-Jose Pazete & C.png",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00"
    },
    "… mais 4 item(ns)"
  ],
  "total": 6
}
```

## `GET /api/empresas/entrada`

Chamado como `/api/empresas/entrada` → HTTP 200 · `application/json`

```json
{
  "itens": [],
  "pendentes": 0,
  "bot": {
    "ativo": true,
    "token": "••••",
    "destinatarios": [
      {
        "chat_id": "2001",
        "nome": "Notas fiscais (grupo)",
        "empresa": "",
        "ativo": true
      },
      {
        "chat_id": "2002",
        "nome": "Almir",
        "empresa": "",
        "ativo": true
      }
    ],
    "chats": [],
    "ultima_verificacao": null,
    "ultimo_erro": null
  }
}
```

## `GET /api/empresas/config`

Chamado como `/api/empresas/config` → HTTP 200 · `application/json`

```json
{
  "minha_empresa": {
    "nome": "Prospera Industria E Serviços LTDA",
    "cnpj": "03.880.985/0001-85"
  },
  "dia_fechamento": 20,
  "fechamento_automatico": true,
  "hora_envio": "08:00",
  "ultimo_fechamento": "",
  "bot": {
    "ativo": true,
    "token": "••••",
    "destinatarios": [
      {
        "chat_id": "2001",
        "nome": "Notas fiscais (grupo)",
        "empresa": "",
        "ativo": true
      },
      {
        "chat_id": "2002",
        "nome": "Almir",
        "empresa": "",
        "ativo": true
      }
    ],
    "chats": [],
    "ultima_verificacao": null,
    "ultimo_erro": null
  }
}
```

## `GET /api/empresas/config/chats`

Chamado como `/api/empresas/config/chats` → HTTP 422 · `application/json`

```json
{
  "detail": {
    "codigo": "telegram",
    "mensagem": "Versão de demonstração: o envio por Telegram fica desligado (nada sai deste c…"
  }
}
```

## `GET /api/caixa`

Chamado como `/api/caixa` → HTTP 200 · `application/json`

```json
{
  "periodo": {
    "tipo": "mes",
    "inicio": "2026-10-01",
    "fim": "2026-10-31",
    "rotulo": "outubro de 2026",
    "anterior": "2026-09-01",
    "seguinte": "2026-11-01"
  },
  "entradas": {
    "total": 0,
    "quantidade": 0,
    "media": 0.0,
    "maior": null
  },
  "saidas": {
    "total": 0,
    "quantidade": 0,
    "media": 0.0,
    "maior": null
  },
  "saldo_periodo": 0,
  "saldo_caixa": 17073.33,
  "saldo_inicial": 17073.33,
  "saidas_periodo_anterior": 2205.33,
  "por_centro": [],
  "por_local": [],
  "por_pessoa": [],
  "entradas_por_pedido": [],
  "serie": [
    {
      "data": "2026-10-01",
      "rotulo": "01/10",
      "entradas": 0.0,
      "saidas": 0.0
    },
    {
      "data": "2026-10-02",
      "rotulo": "02/10",
      "entradas": 0.0,
      "saidas": 0.0
    },
    "… mais 29 item(ns)"
  ],
  "lancamentos": []
}
```

## `GET /api/caixa/{id_}/historico`

Chamado como `/api/caixa/1/historico` → HTTP 200 · `application/json`

```json
{
  "eventos": [
    {
      "quando": "2026-09-29T16:54",
      "acao": "Lançamento",
      "detalhes": "",
      "usuario": "Demonstração"
    }
  ]
}
```

## `GET /api/caixa/relatorio/arquivo`

Chamado como `/api/caixa/relatorio/arquivo` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 6009 bytes)

## `GET /api/caixa/bot/entrada`

Chamado como `/api/caixa/bot/entrada` → HTTP 200 · `application/json`

```json
{
  "itens": [],
  "pendentes": 0,
  "config": {
    "ativo": true,
    "token": "••••",
    "ultima_verificacao": null,
    "ultimo_erro": null,
    "pessoas": [
      {
        "chat_id": "1001",
        "nome": "Escritório (grupo)"
      },
      {
        "chat_id": "1002",
        "nome": "Fábio"
      },
      "… mais 3 item(ns)"
    ]
  }
}
```

## `GET /api/caixa/bot/config`

Chamado como `/api/caixa/bot/config` → HTTP 200 · `application/json`

```json
{
  "ativo": true,
  "token": "••••",
  "ultima_verificacao": null,
  "ultimo_erro": null,
  "pessoas": [
    {
      "chat_id": "1001",
      "nome": "Escritório (grupo)"
    },
    {
      "chat_id": "1002",
      "nome": "Fábio"
    },
    "… mais 3 item(ns)"
  ]
}
```

## `GET /api/diesel`

Chamado como `/api/diesel` → HTTP 200 · `application/json`

```json
{
  "periodo": {
    "tipo": "semana",
    "inicio": "2026-10-05",
    "fim": "2026-10-11",
    "rotulo": "semana de 05/10 a 11/10/2026",
    "dias": 6,
    "anterior": "2026-09-28",
    "seguinte": "2026-10-12"
  },
  "comprado": {
    "litros": 0,
    "valor": 0,
    "quantidade": 0
  },
  "abastecido": {
    "litros": 0,
    "quantidade": 0,
    "custo": 0,
    "por_dia": 0.0
  },
  "preco_medio": 6.704,
  "por_combustivel": [],
  "saldo": {
    "valor": 10068.06,
    "pago": 67133.2,
    "gasto": 57065.14,
    "equivalente": [
      {
        "combustivel": "Diesel S10",
        "preco": 7.45,
        "litros": 1351.4
      },
      {
        "combustivel": "Diesel comum",
        "preco": 6.75,
        "litros": 1491.6
      }
    ],
    "litros": 1410.3,
    "comprado": 9450.0,
    "abastecido": 8039.7,
    "por_combustivel": [
      {
        "combustivel": "Diesel S10",
        "comprado": 4950.0,
        "abastecido": 3995.9,
        "valor_abastecido": 29769.48
      },
      {
        "combustivel": "Diesel comum",
        "comprado": 4500.0,
        "abastecido": 4043.8,
        "valor_abastecido": 27295.66
      }
    ],
    "ultima_compra": {
      "id": 18,
      "data": "2026-09-28",
      "litros": 1050.0,
      "valor": 7502.3,
      "combustivel": "Diesel comum",
      "posto": "Auto Posto Rodovia",
      "usados_desde": 574.7,
      "gasto_desde": 4020.77
    }
  },
  "por_maquina": [],
  "sem_abastecimento": [
    "Caminhão Scania P360",
    "Caminhão Volvo FMX",
    "… mais 3 item(ns)"
  ],
  "compras": [],
  "abastecimentos": [],
  "pendentes": 0,
  "precos": [
    {
      "combustivel": "Diesel S10",
      "preco": 7.45,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    {
      "combustivel": "Diesel comum",
      "preco": 6.75,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    "… mais 3 item(ns)"
  ],
  "alerta_valor": 1000.0
}
```

## `GET /api/diesel/precos`

Chamado como `/api/diesel/precos` → HTTP 200 · `application/json`

```json
{
  "precos": [
    {
      "combustivel": "Diesel S10",
      "preco": 7.45,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    {
      "combustivel": "Diesel comum",
      "preco": 6.75,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    "… mais 3 item(ns)"
  ],
  "combustiveis": [
    "Diesel S10",
    "Diesel comum",
    "… mais 3 item(ns)"
  ]
}
```

## `GET /api/diesel/maquinas`

Chamado como `/api/diesel/maquinas` → HTTP 200 · `application/json`

```json
{
  "maquinas": [
    {
      "id": 4,
      "nome": "Caminhão Scania P360",
      "tipo": "Caminhão",
      "placa": "DEF-2G34",
      "medidor": "km",
      "combustivel": "Diesel S10",
      "status": "Ativa",
      "observacoes": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00",
      "arquivo": "",
      "arquivo_nome": "",
      "media": {
        "maquina": "Caminhão Scania P360",
        "dias": 30,
        "litros": 852.6,
        "abastecimentos": 4,
        "por_dia": 28.42,
        "por_semana": 198.94,
        "por_abastecimento": 213.15,
        "consumo": {
          "tipo": "km",
          "valor": 3.29,
          "rotulo": "3,29 km/L",
          "rodado": 6743.600000000006
        }
      }
    },
    {
      "id": 3,
      "nome": "Caminhão Volvo FMX",
      "tipo": "Caminhão",
      "placa": "ABC-1D23",
      "medidor": "km",
      "combustivel": "Diesel S10",
      "status": "Ativa",
      "observacoes": "",
      "data_lancamento": "2026-09-29T16:54:00",
      "lancado_por": "Demonstração",
      "atualizado_em": "2026-09-29T16:54:00",
      "arquivo": "",
      "arquivo_nome": "",
      "media": {
        "maquina": "Caminhão Volvo FMX",
        "dias": 30,
        "litros": 202.2,
        "abastecimentos": 1,
        "por_dia": 6.74,
        "por_semana": 47.18,
        "por_abastecimento": 202.2,
        "consumo": {
          "tipo": "km",
          "valor": 4.29,
          "rotulo": "4,29 km/L",
          "rodado": 6574.799999999988
        }
      }
    },
    "… mais 3 item(ns)"
  ]
}
```

## `GET /api/diesel/{aba}/{id_}/historico`

Chamado como `/api/diesel/abastecimentos/1/historico` → HTTP 200 · `application/json`

```json
{
  "eventos": [
    {
      "quando": "2026-09-29T16:54",
      "acao": "Lançamento",
      "detalhes": "",
      "usuario": "Demonstração"
    }
  ]
}
```

## `GET /api/diesel/relatorio`

Chamado como `/api/diesel/relatorio` → HTTP 200 · `application/json`

```json
{
  "periodo": {
    "tipo": "semana",
    "inicio": "2026-10-05",
    "fim": "2026-10-11",
    "rotulo": "semana de 05/10 a 11/10/2026",
    "dias": 6,
    "anterior": "2026-09-28",
    "seguinte": "2026-10-12"
  },
  "comprado": {
    "litros": 0,
    "valor": 0,
    "quantidade": 0
  },
  "abastecido": {
    "litros": 0,
    "quantidade": 0,
    "custo": 0,
    "por_dia": 0.0
  },
  "preco_medio": 6.704,
  "por_combustivel": [],
  "saldo": {
    "valor": 10068.06,
    "pago": 67133.2,
    "gasto": 57065.14,
    "equivalente": [
      {
        "combustivel": "Diesel S10",
        "preco": 7.45,
        "litros": 1351.4
      },
      {
        "combustivel": "Diesel comum",
        "preco": 6.75,
        "litros": 1491.6
      }
    ],
    "litros": 1410.3,
    "comprado": 9450.0,
    "abastecido": 8039.7,
    "por_combustivel": [
      {
        "combustivel": "Diesel S10",
        "comprado": 4950.0,
        "abastecido": 3995.9,
        "valor_abastecido": 29769.48
      },
      {
        "combustivel": "Diesel comum",
        "comprado": 4500.0,
        "abastecido": 4043.8,
        "valor_abastecido": 27295.66
      }
    ],
    "ultima_compra": {
      "id": 18,
      "data": "2026-09-28",
      "litros": 1050.0,
      "valor": 7502.3,
      "combustivel": "Diesel comum",
      "posto": "Auto Posto Rodovia",
      "usados_desde": 574.7,
      "gasto_desde": 4020.77
    }
  },
  "por_maquina": [],
  "sem_abastecimento": [
    "Caminhão Scania P360",
    "Caminhão Volvo FMX",
    "… mais 3 item(ns)"
  ],
  "compras": [],
  "abastecimentos": [],
  "nivel_padrao": "simples",
  "anterior": {
    "rotulo": "semana de 28/09 a 04/10/2026",
    "inicio": "2026-09-28",
    "fim": "2026-10-04",
    "litros": 574.7,
    "custo": 4020.77,
    "abastecimentos": 4
  },
  "variacao": {
    "litros": -100.0,
    "custo": -100.0
  },
  "serie": [
    {
      "rotulo": "seg 05",
      "inicio": "2026-10-05",
      "litros": 0.0,
      "valor": 0.0,
      "abastecimentos": 0,
      "por_combustivel": {}
    },
    {
      "rotulo": "ter 06",
      "inicio": "2026-10-06",
      "litros": 0.0,
      "valor": 0.0,
      "abastecimentos": 0,
      "por_combustivel": {}
    },
    "… mais 5 item(ns)"
  ],
  "por_posto": [],
  "por_pessoa": [],
  "previsao": {
    "saldo": 10068.06,
    "por_dia": 592.76,
    "dias": 16,
    "acaba_em": "2026-10-26"
  },
  "periodo_atual": true,
  "alertas": [
    {
      "nivel": "info",
      "texto": "Sem abastecimento no período: Caminhão Scania P360, Caminhão Volvo FMX, Escav…"
    }
  ],
  "pendentes": 0,
  "precos": [
    {
      "combustivel": "Diesel S10",
      "preco": 7.45,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    {
      "combustivel": "Diesel comum",
      "preco": 6.75,
      "atualizado_em": "2026-09-29T16:54:43",
      "por": "Demonstração"
    },
    "… mais 3 item(ns)"
  ],
  "alerta_valor": 1000.0
}
```

## `GET /api/diesel/relatorio/arquivo`

Chamado como `/api/diesel/relatorio/arquivo` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 11288 bytes)

## `GET /api/diesel/relatorio/texto`

Chamado como `/api/diesel/relatorio/texto` → HTTP 200 · `application/json`

```json
{
  "texto": "⛽ <b>Relatório semanal do diesel</b>\nSemana de 05/10 a 11/10/2026\n\n💸 Abasteci…"
}
```

## `GET /api/diesel/bot/entrada`

Chamado como `/api/diesel/bot/entrada` → HTTP 200 · `application/json`

```json
{
  "itens": [],
  "pendentes": 0,
  "config": {
    "ativo": true,
    "token": "••••",
    "ultima_verificacao": null,
    "ultimo_erro": null,
    "gestores": [
      "1002"
    ],
    "alerta_valor": 1000.0,
    "hora_relatorio": "07:00",
    "relatorios": {
      "semana": true,
      "quinzena": true,
      "mes": true
    },
    "nivel_relatorio": "simples",
    "enviados": {},
    "pessoas": [
      {
        "chat_id": "1001",
        "nome": "Escritório (grupo)"
      },
      {
        "chat_id": "1002",
        "nome": "Fábio"
      },
      "… mais 3 item(ns)"
    ]
  }
}
```

## `GET /api/diesel/bot/config`

Chamado como `/api/diesel/bot/config` → HTTP 200 · `application/json`

```json
{
  "ativo": true,
  "token": "••••",
  "ultima_verificacao": null,
  "ultimo_erro": null,
  "gestores": [
    "1002"
  ],
  "alerta_valor": 1000.0,
  "hora_relatorio": "07:00",
  "relatorios": {
    "semana": true,
    "quinzena": true,
    "mes": true
  },
  "nivel_relatorio": "simples",
  "enviados": {},
  "pessoas": [
    {
      "chat_id": "1001",
      "nome": "Escritório (grupo)"
    },
    {
      "chat_id": "1002",
      "nome": "Fábio"
    },
    "… mais 3 item(ns)"
  ]
}
```

## `GET /api/relatorio-geral`

Chamado como `/api/relatorio-geral` → HTTP 200 · `application/json`

```json
{
  "mes": "2026-10",
  "titulo": "outubro de 2026",
  "anterior": "2026-09",
  "seguinte": "2026-11",
  "gerado_em": "2026-10-10T16:12:20",
  "contas": {
    "pago": 0,
    "quantidade_pagos": 0,
    "por_tipo": {
      "Boleto": {
        "valor": 0,
        "quantidade": 0
      },
      "Pix": {
        "valor": 0,
        "quantidade": 0
      },
      "Dinheiro": {
        "valor": 0,
        "quantidade": 0
      }
    },
    "juros_multa": 0,
    "desconto": 0,
    "pagos_com_atraso": 0,
    "sem_comprovante": 0,
    "por_centro": [],
    "juros": [],
    "vencimento": {
      "total": 19637.7,
      "pago": 0,
      "em_aberto": 19637.7,
      "atrasado": 4876.39,
      "quantidade_atrasados": 4,
      "quantidade": 10
    }
  },
  "historico": [
    {
      "mes": "2025-11",
      "titulo": "novembro de 2025",
      "boletos": 0,
      "pix": 0,
      "dinheiro": 0,
      "pago": 0,
      "juros_multa": 0,
      "desconto": 0,
      "quantidade": 0,
      "pagos_com_atraso": 0
    },
    {
      "mes": "2025-12",
      "titulo": "dezembro de 2025",
      "boletos": 0,
      "pix": 0,
      "dinheiro": 0,
      "pago": 0,
      "juros_multa": 0,
      "desconto": 0,
      "quantidade": 0,
      "pagos_com_atraso": 0
    },
    "… mais 10 item(ns)"
  ],
  "previsao": {
    "em_atraso": {
      "total": 14013.07,
      "quantidade": 6
    },
    "7_dias": 1809.15,
    "30_dias": 14761.31
  },
  "caixa": {
    "entradas": {
      "total": 0,
      "quantidade": 0
    },
    "saidas": {
      "total": 0,
      "quantidade": 0
    },
    "saldo_periodo": 0,
    "saldo_caixa": 17073.33,
    "saidas_periodo_anterior": 2205.33,
    "por_centro": []
  },
  "diesel": {
    "comprado": {
      "litros": 0,
      "valor": 0,
      "quantidade": 0
    },
    "abastecido": {
      "litros": 0,
      "quantidade": 0,
      "custo": 0
    },
    "preco_medio": 6.704,
    "saldo": 10068.06,
    "por_maquina": []
  },
  "empresas": {
    "competencia": "2026-10",
    "faturado": 24976.9,
    "recebido_do_fechamento": 0.0,
    "falta": 24976.9,
    "em_aberto": 66327.38,
    "recebido_no_mes": 0,
    "recebimentos_no_mes": 0,
    "cheques": {
      "quantidade": 3,
      "valor": 8989.09
    },
    "empresas": [
      {
        "id": 1,
        "nome": "Imapal Construções",
        "total": 9528.0,
        "falta": 9528.0,
        "em_aberto": 28139.1
      },
      {
        "id": 3,
        "nome": "Terraplanagem Souza",
        "total": 7326.4,
        "falta": 7326.4,
        "em_aberto": 19114.79
      },
      "… mais 1 item(ns)"
    ]
  }
}
```

## `GET /api/relatorio-geral/arquivo`

Chamado como `/api/relatorio-geral/arquivo` → HTTP 200 · `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

(arquivo/conteúdo não JSON, 7989 bytes)

## `GET /api/admin`

Chamado como `/api/admin` → HTTP 200 · `application/json`

```json
{
  "senha_definida": false,
  "autorizado": false,
  "bloqueado_segundos": 0,
  "minutos_sessao": 20,
  "local": true
}
```

## `GET /api/importacao/modelo.xlsx`

Chamado como `/api/importacao/modelo.xlsx` → HTTP 403 · `application/json`

```json
{
  "detail": {
    "codigo": "admin_sem_senha",
    "mensagem": "Função restrita: crie a senha de administrador em Configurações."
  }
}
```

## `GET /api/notificacoes`

Chamado como `/api/notificacoes` → HTTP 200 · `application/json`

```json
{
  "alertas": [
    {
      "id": 36,
      "beneficiario": "DISTRIBUIDORA DE LUBRIFICANTES",
      "numero_documento": "719716/08",
      "valor": 3010.57,
      "vencimento": "2026-09-23",
      "dias": -17,
      "categoria": "vencido",
      "fim_de_semana": false,
      "linha_digitavel": "05038.04416 88388.875133 65805.674790 2 22312330870449",
      "linha_digitos": "05038044168838887513365805674790222312330870449",
      "tipo_pagamento": "boleto",
      "chave_pix": "",
      "chave": "36|2026-09-23|vencido",
      "visto": false,
      "dispensado": false
    },
    {
      "id": 38,
      "beneficiario": "POSTO SAO JORGE LTDA",
      "numero_documento": "419588/07",
      "valor": 6126.11,
      "vencimento": "2026-09-28",
      "dias": -12,
      "categoria": "vencido",
      "fim_de_semana": false,
      "linha_digitavel": "96460.20928 51852.206136 45372.456477 1 03369926109211",
      "linha_digitos": "96460209285185220613645372456477103369926109211",
      "tipo_pagamento": "boleto",
      "chave_pix": "",
      "chave": "38|2026-09-28|vencido",
      "visto": false,
      "dispensado": false
    },
    "… mais 8 item(ns)"
  ],
  "nao_vistos": 10,
  "janela_dias": 3,
  "agenda": [
    {
      "quando": "2026-10-11T09:00",
      "regra": "vespera",
      "tipo": "antes",
      "dias": 1,
      "lembrete": null,
      "canais": [
        "windows",
        "telegram"
      ],
      "quantidade": 1,
      "boletos": [
        {
          "id": 41,
          "beneficiario": "DISTRIBUIDORA DE LUBRIFICANTES",
          "valor": 1256.74,
          "vencimento": "2026-10-12"
        }
      ]
    },
    {
      "quando": "2026-10-11T09:00",
      "regra": "antecedencia",
      "tipo": "antes",
      "dias": 3,
      "lembrete": null,
      "canais": [
        "windows",
        "telegram"
      ],
      "quantidade": 1,
      "boletos": [
        {
          "id": "pix-14",
          "beneficiario": "Maria da Limpeza",
          "valor": 552.41,
          "vencimento": "2026-10-14"
        }
      ]
    },
    "… mais 14 item(ns)"
  ],
  "config": {
    "ativo": true,
    "dias_semana": [
      0,
      1,
      "… mais 5 item(ns)"
    ],
    "regras": [
      {
        "id": "vencimento",
        "tipo": "vencimento",
        "dias": 0,
        "horarios": [
          "08:00",
          "12:00",
          "… mais 1 item(ns)"
        ],
        "canais": [
          "windows",
          "telegram",
          "… mais 1 item(ns)"
        ],
        "ativo": true
      },
      {
        "id": "vespera",
        "tipo": "antes",
        "dias": 1,
        "horarios": [
          "09:00"
        ],
        "canais": [
          "windows",
          "telegram",
          "… mais 1 item(ns)"
        ],
        "ativo": true
      },
      "… mais 2 item(ns)"
    ],
    "resumos": {
      "segunda": {
        "ativo": true,
        "horario": "08:00",
        "canais": [
          "windows",
          "telegram"
        ],
        "ultimo_envio": null
      },
      "sexta": {
        "ativo": true,
        "horario": "17:00",
        "canais": [
          "windows",
          "telegram"
        ],
        "ultimo_envio": null
      }
    },
    "windows": {
      "ativo": true
    },
    "telegram": {
      "ativo": true,
      "token": "••••",
      "chat_id": "1001",
      "destinatarios": [
        {
          "chat_id": "1001",
          "nome": "Escritório (grupo)",
          "tipo": "grupo",
          "ativo": true
        },
        {
          "chat_id": "1002",
          "nome": "Fábio",
          "tipo": "privado",
          "ativo": true
        },
        "… mais 1 item(ns)"
      ]
    },
    "email": {
      "ativo": false,
      "servidor": "",
      "porta": 587,
      "seguranca": "starttls",
      "usuario": "",
      "senha": "",
      "remetente": "",
      "destinatarios": ""
    }
  },
  "historico": [],
  "automaticas": false
}
```

## `GET /api/notificacoes/resumo/{tipo}`

Chamado como `/api/notificacoes/resumo/segunda` → HTTP 200 · `application/json`

```json
{
  "titulo": "Semana: 0 pagamentos · R$ 0,00",
  "texto": "📅 Resumo da semana · 05/10 a 11/10\n\n💸 A pagar nesta semana\n  Nada vence nesta…",
  "html": "<div style='font-family:Segoe UI,Arial,sans-serif;max-width:640px;color:#0e1a…"
}
```

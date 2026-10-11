# Anexo A3 — Variáveis, permissões e arquivos de configuração

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

## Variáveis de ambiente (`.env`)

| Variável | Padrão | Lida em |
|---|---|---|
| `LEITOR_MODO` | "" | `app/__main__.py` |
| `LEITOR_ABRIR_NAVEGADOR` | "1" | `app/__main__.py` |
| `USERPROFILE` | Path.home( | `app/atalhos.py` |
| `APPDATA` | — | `app/atalhos.py` |
| `LEITOR_NOME_APP` | "Fin Pro" | `app/config.py` |
| `LEITOR_DEMO` | False | `app/config.py` |
| `LEITOR_DADOS_DIR` | — | `app/config.py` |
| `LEITOR_PLANILHA` | — | `app/config.py` |
| `LEITOR_FECHAMENTOS` | — | `app/config.py` |
| `LEITOR_DIESEL` | — | `app/config.py` |
| `LEITOR_HOST` | "127.0.0.1" | `app/config.py` |
| `LEITOR_PORT` | "8000" | `app/config.py` |
| `LEITOR_MAX_UPLOAD_MB` | "100" | `app/config.py` |
| `LEITOR_MAX_PAGINAS_PDF` | "30" | `app/config.py` |
| `LEITOR_DIAS_ARQUIVOS_TEMP` | "2" | `app/config.py` |
| `LEITOR_URL` | — | `app/config.py` |
| `LEITOR_NOTIFICACOES_AUTOMATICAS` | True | `app/config.py` |
| `LEITOR_BACKUP_AUTOMATICO` | True | `app/config.py` |
| `LEITOR_SENHA_ACESSO` | — | `app/config.py` |
| `LEITOR_IA_MODELO` | "claude-opus-5" | `app/config.py` |
| `LEITOR_IA_AUTOMATICA` | False | `app/config.py` |
| `ANTHROPIC_API_KEY` | — | `app/config.py` |
| `ANTHROPIC_AUTH_TOKEN` | — | `app/config.py` |
| `LEITOR_DADOS_DIR` | — | `app/demonstracao.py` |
| `APPDATA` | — | `app/inicializacao.py` |

## Valores calculados em `app/config.py`

| Nome | Valor (nesta geração) |
|---|---|
| `BASE_DIR` | `<projeto>` |
| `NOME_APP` | `Fin Pro` |
| `DEMONSTRACAO` | `False` |
| `DADOS_DIR` | `<dados>` |
| `PLANILHA_PATH` | `<dados>\boletos.xlsx` |
| `FECHAMENTOS_PATH` | `<dados>\fechamentos.xlsx` |
| `DIESEL_PATH` | `<dados>\diesel.xlsx` |
| `ARQUIVOS_DIR` | `<dados>\arquivos` |
| `BACKUPS_DIR` | `<dados>\backups` |
| `WEB_DIR` | `<projeto>\web` |
| `HOST` | `127.0.0.1` |
| `PORT` | `8000` |
| `MAX_UPLOAD_MB` | `100` |
| `MAX_PAGINAS_PDF` | `30` |
| `DIAS_MANTER_ARQUIVOS_NAO_LANCADOS` | `2` |
| `URL_APP` | `http://localhost:8000` |
| `NOTIFICACOES_AUTOMATICAS` | `False` |
| `BACKUP_AUTOMATICO` | `False` |
| `SENHA_ACESSO` | `` |
| `IA_MODELO` | `claude-opus-5` |
| `IA_AUTOMATICA` | `False` |

## Permissões (`app/usuarios.py`)

| Chave | Descrição |
|---|---|
| `lancar` | Lançar boletos e Pix (ler arquivos e cadastrar) |
| `pagar` | Dar baixa: marcar como pago e anexar comprovante |
| `editar` | Editar e excluir lançamentos |
| `gastos` | Ver os gastos e gerar o fechamento do mês |
| `empresas` | Empresas: notas fiscais, cheques e recebimentos |
| `caixa` | Caixa: entradas e saídas em dinheiro |
| `diesel` | Diesel: compras, abastecimentos das máquinas e relatórios |
| `notificacoes` | Configurar os avisos de vencimento |
| `config` | Configurações do sistema (backup, bots, importação, rede) |

Permissões de um usuário novo: `lancar`, `pagar`.

## Formato padrão dos arquivos de configuração (`dados/*.json`)

Valores de fábrica, criados na primeira execução. Tokens e senhas ficam vazios aqui.

### `notificacoes.servico.REGRAS_PADRAO`

```json
[
  {
    "id": "vencimento",
    "tipo": "vencimento",
    "dias": 0,
    "horarios": [
      "08:00",
      "12:00",
      "16:00"
    ],
    "canais": [
      "windows",
      "telegram",
      "email"
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
      "email"
    ],
    "ativo": true
  },
  {
    "id": "antecedencia",
    "tipo": "antes",
    "dias": 3,
    "horarios": [
      "09:00"
    ],
    "canais": [
      "windows",
      "telegram",
      "email"
    ],
    "ativo": true
  },
  {
    "id": "vencidos",
    "tipo": "vencidos",
    "dias": 30,
    "horarios": [
      "09:00"
    ],
    "canais": [
      "windows",
      "telegram",
      "email"
    ],
    "ativo": true
  }
]
```

### `notificacoes.servico.PADRAO`

```json
{
  "ativo": true,
  "resumos": {
    "segunda": {
      "ativo": true,
      "horario": "08:00",
      "canais": [
        "telegram",
        "email"
      ]
    },
    "sexta": {
      "ativo": true,
      "horario": "17:00",
      "canais": [
        "telegram",
        "email"
      ]
    }
  },
  "dias_semana": [
    0,
    1,
    2,
    3,
    4,
    5,
    6
  ],
  "regras": [
    {
      "id": "vencimento",
      "tipo": "vencimento",
      "dias": 0,
      "horarios": [
        "08:00",
        "12:00",
        "16:00"
      ],
      "canais": [
        "windows",
        "telegram",
        "email"
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
        "email"
      ],
      "ativo": true
    },
    {
      "id": "antecedencia",
      "tipo": "antes",
      "dias": 3,
      "horarios": [
        "09:00"
      ],
      "canais": [
        "windows",
        "telegram",
        "email"
      ],
      "ativo": true
    },
    {
      "id": "vencidos",
      "tipo": "vencidos",
      "dias": 30,
      "horarios": [
        "09:00"
      ],
      "canais": [
        "windows",
        "telegram",
        "email"
      ],
      "ativo": true
    }
  ],
  "windows": {
    "ativo": true
  },
  "telegram": {
    "ativo": false,
    "token": "",
    "chat_id": "",
    "destinatarios": []
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
}
```

### `entrada.PADRAO`

```json
{
  "itens": [],
  "email": {
    "ativo": false,
    "servidor": "",
    "porta": 993,
    "usuario": "",
    "senha": "",
    "pasta": "INBOX",
    "remetentes": "",
    "uidvalidity": null,
    "ultimo_uid": null,
    "ultima_verificacao": null,
    "ultimo_erro": null
  },
  "telegram": {
    "ativo": false,
    "offset": null,
    "ultima_verificacao": null,
    "ultimo_erro": null,
    "chats": {}
  }
}
```

### `empresas.configuracao.PADRAO`

```json
{
  "minha_empresa": {
    "nome": "",
    "cnpj": ""
  },
  "dia_fechamento": 20,
  "fechamento_automatico": true,
  "hora_envio": "08:00",
  "ultimo_fechamento": "",
  "bot": {
    "ativo": false,
    "token": "",
    "offset": 0,
    "destinatarios": [],
    "chats": {},
    "ultima_verificacao": null,
    "ultimo_erro": null
  }
}
```

### `caixa.bot.PADRAO`

```json
{
  "config": {
    "ativo": false,
    "token": "",
    "offset": 0,
    "ultima_verificacao": null,
    "ultimo_erro": null
  },
  "itens": [],
  "conversas": {}
}
```

### `diesel.bot.PADRAO`

```json
{
  "config": {
    "ativo": false,
    "token": "",
    "offset": 0,
    "ultima_verificacao": null,
    "ultimo_erro": null,
    "gestores": [],
    "alerta_valor": 1000.0,
    "hora_relatorio": "07:00",
    "relatorios": {
      "semana": true,
      "quinzena": true,
      "mes": true
    },
    "nivel_relatorio": "simples",
    "enviados": {}
  },
  "itens": [],
  "conversas": {}
}
```

### `preferencias.PADRAO`

```json
{
  "fechar_para_bandeja": true,
  "minimizado_ao_iniciar": false,
  "aviso_bandeja_mostrado": false
}
```

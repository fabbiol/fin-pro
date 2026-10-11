# 14 — Lições aprendidas: tudo o que já deu errado (e como não repetir)

Cada linha é um erro **real** que aconteceu durante a construção do Fin Pro (de 14/09 a 07/10/2026), com a causa, a
correção e a regra para a próxima versão. **Leia antes de começar** — quase todos são fáceis de repetir.

## 14.1 Leitura de boletos

| # | Sintoma | Causa | Correção | Regra para a nova versão |
|---|---|---|---|---|
| 1 | Vencimentos errados em boletos novos | O fator de vencimento chegou a 9999 em 21/02/2025 e **reiniciou em 1000** em 22/02/2025 | Duas bases; escolhe a data mais próxima da referência; o impresso desempata | Use `data_por_fator` exatamente como no capítulo 03 e teste os dois ciclos |
| 2 | Linhas digitáveis "válidas" mas erradas a partir do código de barras | O ITF não tem dígito verificador próprio; leituras parciais passavam | Só aceita leitura de 44 dígitos que passa na validação FEBRABAN | Nunca confie no código de barras sem validar os DVs |
| 3 | Beneficiário errado nos PDFs escaneados da HIPER JN | A página estava **deitada dentro do PDF** | Endireitar pela orientação do código de barras; sem código, pela direção do texto | Teste PDFs escaneados de lado e de cabeça para baixo |
| 4 | PDFs escaneados gigantes viravam imagens de ~7.700 px (lento, memória) | Escala fixa na renderização | Escala ≤ 3 e lado máximo de 3.000 px; uma página por vez | Limite a resolução e renderize sob demanda |
| 5 | PDF de 30 MB recusado | Limite de upload pequeno | `LEITOR_MAX_UPLOAD_MB=100` e aviso de páginas além do limite | Scans reais são grandes: limite generoso + aviso |
| 6 | Nome do beneficiário com "- 45262202000140 - AV. PRESIDENTE…" | Razão social, CNPJ e endereço na mesma linha | Extrator corta CNPJ e endereço; linhas só de endereço descartadas | Limpe o nome; não confie no fim da linha |
| 7 | "contate o **beneficiário**" virava o campo Beneficiário | Rótulo achado no meio de frase | Ignora rótulo com mais de 4 palavras / 32 caracteres antes | Rótulo de ficha fica no começo do bloco de texto |
| 8 | Mesmo CNPJ com nomes diferentes ("NIPER 3N", "HIPER IN") | Erro de OCR em uma das páginas | Consenso entre boletos do mesmo arquivo; histórico pelo CNPJ (nome já conferido) | Use o que o usuário já corrigiu como fonte de verdade |
| 9 | Razão social cortada ("…LUBRIFICANTES E") | Nome quebrado em duas linhas | Se termina em "e/de/da/&", junta a linha de baixo | Trate quebras de linha em nomes |
| 10 | Número da NF lido errado no DANFE | OCR do número impresso | Número tirado da **chave de acesso** (44 dígitos) | Prefira campos com verificação (chave, código de barras) |
| 11 | Material "2000000000201 PEDRISCO COMERCIAL" | Código do produto colado na descrição | Remove código no início e NCM/CST/CFOP no fim; descrição só com números vai para Conferência | Valide que o texto "parece" o que deveria ser |

## 14.2 Comprovantes, empresas e cheques

| # | Sintoma | Causa | Correção | Regra |
|---|---|---|---|---|
| 12 | Cheque nº "180006" em vez de **616**; conta errada | **Posições erradas na CMC-7** — e o teste tinha o mesmo erro, por isso não pegou | `numero = campo2[3:9]`, `conta = campo3[1:11]`; teste com a CMC-7 real | **Testes de leitura com documentos reais**, nunca só com dados inventados pelo próprio programador |
| 13 | Comprovante de depósito virou "cheque novo" e o cheque do dia levou baixa errada | O comprovante traz a CMC-7 e a palavra "cheque", que pesaram mais que "depósito" | Regra explícita de **depósito de cheque** antes do placar; compensa o cheque certo pela CMC-7; soma tem que bater | Documentos parecidos precisam de regra própria, não só de pontuação |
| 14 | Foto do comprovante deitada sem data/valor | OCR em uma orientação só | Relê girando quando falta data ou valor | Fotos de celular chegam em qualquer orientação |
| 15 | Cheque: "bom para" e pedidos do verso não apareciam | Foto deitada; OCR embaralhado | OCR nas **4 orientações**, juntando as linhas; data à mão com combinações e janela −3/+18 meses | Para documentos manuscritos, tente todas as orientações |
| 16 | Ao escolher um mês, o cartão somava o "em aberto" de todos os meses | Totais misturavam mês e geral; o seletor só mudava a tabela | Tudo da competência escolhida; atrasados de outros meses como aviso à parte | Um filtro tem que valer para a tela inteira |
| 17 | Baixa automática não pode "chutar" parcelas iguais | Vários lançamentos com mesmo valor | Limite 75 pontos + margem de 20 sobre o 2º; senão, alguém escolhe | Em dinheiro, prefira perguntar a errar |
| 18 | Status Pago → Pendente mantinha a data de pagamento | Campos de pagamento não eram limpos | Desfazer limpa data, valor pago, juros, desconto e comprovante | Ao reverter um estado, limpe tudo o que ele criou |

## 14.3 Diesel

| # | Sintoma | Causa | Correção | Regra |
|---|---|---|---|---|
| 19 | Anexo do canhoto não era salvo | `arquivo`/`arquivo_nome` fora de `editaveis` (campo descartado em silêncio) | Incluídos | Ao criar uma aba, liste **todos** os campos gravados em `editaveis`; teste que o arquivo volta |
| 20 | `PUT /api/diesel/maquinas/3` caía na rota errada | `/{aba}/{id}` declarada antes de `/maquinas/{id}` | Rotas específicas antes das genéricas | Ordem de rotas importa; teste cada uma |
| 21 | Preço do litro lido como "000005" | Código do produto ("000005") parecia número | Preço precisa ter casas decimais e ficar entre R$ 2 e R$ 15; números com zero à esquerda ignorados | Valide faixas plausíveis |
| 22 | Números tortos na foto ("200006", "1.496", "7.450") | OCR comeu vírgula / trocou ponto | Leituras alternativas + escolher o trio que fecha a conta + acertar pelo rodapé | Use redundância do documento (totais) para corrigir |
| 23 | Saldo mostrava 800 L em vez de 600 L | Saldo **por combustível**; a compra antiga (sem combustível) contou como S10 | Saldo único; depois, **em reais** (crédito no posto vale para S10 e comum) | **Confirme o modelo mental do usuário** antes de modelar ("compramos 1.000 L" = crédito em R$) |
| 24 | Compra com posto "Demais telefones" | Pegou o rodapé do comprovante do banco | Posto = favorecido; ignora ruído do banco e a própria empresa | Saiba o que é ruído em cada tipo de documento |
| 25 | Registros antigos sem combustível quebravam contas | Campo novo inexistente nos dados antigos | `combustivel_de()` com padrão; leituras tolerantes | Todo campo novo precisa de valor padrão para dados antigos |
| 26 | Nº do pedido "8695073" em vez de "0695073" | OCR trocou 0 por 8 | Campo editável na conferência | Campos sem verificação devem ser conferidos pelo usuário |
| 27 | "Consumo 461% acima do normal" falso | Média dividida por 90 dias com só ~2 meses de histórico | Conta só os dias cobertos; mínimo 14 dias; tolerância maior na semana | Estatística com pouco histórico gera alarme falso |
| 28 | Demonstração com saldo de diesel negativo | Dados de exemplo incoerentes | Compras e consumo calibrados | Dados de demonstração precisam passar nas mesmas regras |

## 14.4 Interface, aplicativo e operação

| # | Sintoma | Causa | Correção | Regra |
|---|---|---|---|---|
| 29 | Telas antigas no aplicativo depois de atualizar (cartão de importação "sumiu") | **Cache do WebView2** | `Cache-Control: no-store` + limpeza do cache quando os arquivos de `web/` mudam | Em app desktop com WebView, controle o cache desde o início |
| 30 | Cartão sumia sem aviso quando a API não existia | Tela escondia em caso de erro | Mostra o cartão com aviso "feche e abra o Fin Pro" | Erro visível > silêncio |
| 31 | App congelava ao trazer a janela para frente pela 2ª vez | Deadlock do pythonnet com `window.on_top` | `SetWindowPos` via ctypes | Evite chamadas da janela fora da thread certa |
| 32 | Versão antiga continuava rodando em segundo plano | Instância anterior ocupando a porta | Detecta instância e traz a janela; reinício limpo por `POST /api/app/sair` | Nunca mate o processo do usuário; tenha um "sair" gracioso |
| 33 | Notificações não sumiam do sininho | Não havia "visto/dispensado" | Chave id + vencimento + categoria; volta quando a situação muda | Avisos precisam de estado por usuário |
| 34 | Sininho: nome espremido; cheque aparecia como boleto | Layout e tipo do aviso | × pequeno no canto; tipo "Cheque a depositar" | Cada tipo de aviso tem texto próprio |
| 35 | Contador "1" preso em Ler boletos | Arquivo com boletos já lançados continuava pendente (e escondido) | Conclui sozinho os já lançados; lista atualiza a cada 45 s | Contador e lista devem usar a mesma regra |
| 36 | Pix vencidos não apareciam no Painel | Painel só somava boletos | Painel soma boletos e Pix em tudo | Todo indicador de "a pagar" inclui todos os tipos |
| 37 | Abas de Empresas/Configurações sem espaçamento | CSS só para `<button>`, abas eram `<a>` | Estilo para os dois | Teste visual de cada tela nova |
| 38 | "Os juros sumiram" (duas vezes) | Juros só apareciam na edição e no fechamento | Juros visíveis nas listas, calendário, Painel, Gastos e resumo de sexta | **Informação que o usuário considera crítica precisa estar à vista**, não escondida em detalhes |
| 39 | Busca "pagos sem comprovante" listava entradas do caixa | Entrada não tem cupom | Filtro por `movimento` | Defina "o que é pago" por tipo |
| 40 | Busca por número curto achava boletos por acaso | Trecho curto dentro da linha de 47 dígitos | Linha digitável só com ≥ 8 dígitos | Números curtos precisam de contexto |

## 14.5 Desenvolvimento e ferramentas

| # | Situação | Regra |
|---|---|---|
| 41 | Planilha Excel como banco travava com o arquivo aberto e ficava lenta | Banco de verdade desde o início; Excel só como saída |
| 42 | FastAPI 0.14x guarda os routers incluídos dentro de `_IncludedRouter` (`original_router`) | Ferramentas que listam rotas precisam "desembrulhar" |
| 43 | No Windows, textos com acento passados por `stdin`/heredoc em scripts podem se corromper | Edite arquivos com ferramentas que gravam UTF-8; não passe código com acento pela linha de comando |
| 44 | Teste que confirma o próprio erro (#12) | Teste de leitura usa documento real e valor conferido por humano |
| 45 | Dois sistemas com o mesmo token do Telegram | Disputam as mensagens (`getUpdates`): só um sistema por bot — cuidado na migração para a nuvem |
| 46 | Tokens e senhas de canais em texto nos JSON (e no backup) | Criptografar segredos na nova versão (capítulo 15) |

# 03 — Leitura de boletos (PDF e foto)

Módulos: `app/boleto/` (`codigo.py`, `texto.py`, `leitores.py`, `ocr.py`, `imagem.py`, `extrator.py`, `bancos.py`),
`app/servico_leitura.py`, `app/tarefas.py`, `app/ia.py`, rotas em `app/rotas/leitura.py`.

## 3.1 Fluxo completo de um arquivo

```
POST /api/leituras/tarefas (multipart "arquivo")    ← tela Ler boletos (POST /api/leituras = mesma leitura, síncrona)
  └─ tarefas.GerenciadorTarefas (pool 2) devolve {id} na hora; GET /api/leituras/tarefas/{tarefa_id} acompanha
     (os bots e a caixa de e-mail chamam processar_leitura direto)
       └─ servico_leitura.processar_leitura(dados, nome, ao_progresso)
            1. extrator.ler_arquivo(...)              → boletos[] (+ texto de todas as páginas)
            2. arquivos.salvar(dados, nome)           → guarda o original
            3. servico_comprovante.analisar_resultado → É COMPROVANTE? então devolve {comprovante: ...} e PARA
            4. sem boletos? pix.ler_pix_de_arquivo    → cobranças Pix (QR / Copia e Cola), com duplicidade
            5. IA automática (opcional, LEITOR_IA_AUTOMATICA=1) para boletos com confiança < 0,8
```

Etapas reportadas ao progresso: `iniciando`, `codigo_barras`, `ocr`, `concluindo` (com `pagina`/`paginas`).
Limites: `LEITOR_MAX_UPLOAD_MB` (100), `LEITOR_MAX_PAGINAS_PDF` (30; avisa se o PDF tiver mais).

## 3.2 Padrão FEBRABAN (`boleto/codigo.py`) — implementar exatamente assim

### Tipos
- **Bancário (cobrança)**: linha digitável de **47** dígitos, código de barras de **44**.
- **Arrecadação** (contas de consumo, tributos, convênios): linha de **48** dígitos (4 blocos de 11 + DV cada),
  código de barras de 44 que **começa com 8**.

### Dígitos verificadores
```python
def modulo10(numero):                 # pesos 2,1,2,1... da direita para a esquerda; soma os dígitos do produto
    soma, peso = 0, 2
    for d in reversed(numero):
        p = int(d) * peso; soma += p // 10 + p % 10; peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10

def _soma_modulo11(numero):           # pesos 2..9 repetindo, da direita para a esquerda
    soma, peso = 0, 2
    for d in reversed(numero):
        soma += int(d) * peso; peso = 2 if peso == 9 else peso + 1
    return soma

def modulo11_bancario(n):   dv = 11 - _soma_modulo11(n) % 11; return 1 if dv in (0, 10, 11) else dv
def modulo11_arrecadacao(n): r = _soma_modulo11(n) % 11;      return 0 if r in (0, 1) else 11 - r
# arrecadação: identificador de valor = 3º dígito; "6" ou "7" → módulo 10; "8" ou "9" → módulo 11
```

### Conversões
```python
# bancário: linha (47) → barras (44)
barras = linha[0:4] + linha[32] + linha[33:47] + linha[4:9] + linha[10:20] + linha[21:31]
# barras → linha: campo1 = barras[0:4]+barras[19:24]; campo2 = barras[24:34]; campo3 = barras[34:44]
linha = campo1+DV10(campo1) + campo2+DV10(campo2) + campo3+DV10(campo3) + barras[4] + barras[5:19]
# arrecadação: linha (48) → barras: linha[0:11]+linha[12:23]+linha[24:35]+linha[36:47]
# barras → linha: 4 blocos de 11, cada um + DV (módulo 10 ou 11 conforme o identificador)
```
Formato impresso: bancário `AAAAA.AAAAA BBBBB.BBBBBB CCCCC.CCCCCC D EEEEEEEEEEEEEE`; arrecadação
`XXXXXXXXXXX-D XXXXXXXXXXX-D XXXXXXXXXXX-D XXXXXXXXXXX-D`.

### Validação
- Bancário: DV (módulo 10) de cada um dos 3 campos da linha; **DV geral** = `modulo11_bancario(barras[:4]+barras[5:])`
  deve ser `barras[4]`; moeda `barras[3]` deve ser `9`. Banco = `barras[0:3]` (nome em `bancos.py`).
  Valor = `int(barras[9:19]) / 100`. Fator = `int(barras[5:9])`.
- Arrecadação: identificador (`barras[2]`) ∈ {6,7,8,9}; DV de cada bloco; DV geral = `barras[3]` calculado sobre
  `barras[:3]+barras[4:]`. Segmento = `barras[1]` (nome em `SEGMENTOS_ARRECADACAO`). Valor = `int(barras[4:15])/100`
  só se o identificador for 6 ou 8 (senão é valor de referência). Vencimento: procura uma data `AAAAMMDD` no campo
  livre (`barras[19:44]`) a até 3 anos da data de referência → marcado como **estimado**.

### Fator de vencimento (o detalhe que mais quebra sistemas)
O fator chegou a 9999 em 21/02/2025 e **reiniciou em 1000 em 22/02/2025**.
```python
BASE_FATOR_ORIGINAL   = date(1997, 10, 7)
BASE_FATOR_NOVO_CICLO = date(2025, 2, 22) - timedelta(days=1000)
def data_por_fator(fator, referencia=hoje):
    if fator < 1000: return None
    candidatas = [BASE_FATOR_ORIGINAL + timedelta(fator), BASE_FATOR_NOVO_CICLO + timedelta(fator)]
    return min(candidatas, key=lambda d: abs((d - referencia).days))   # o ciclo mais próximo da referência
```
Se a data impressa no boleto difere, mas bate com o **outro** ciclo, usa-se a impressa (`consolidar`).

### Correção automática de dígitos (`candidatos_correcao`, `tentar_corrigir`)
Cada campo tem o próprio DV, então dá para corrigir **um dígito por campo**:
1. Para cada bloco com DV errado, gera todas as variações de 1 dígito que tornam o bloco válido.
2. Combina (produto cartesiano) e mantém só as linhas inteiras válidas (DV geral confere). Até 3 blocos errados.
3. Se todos os blocos conferem mas o DV geral não (bancário), tenta 1 dígito na cauda (DV geral + fator + valor).
4. Arrecadação com identificador ilegível: força bruta de 1 dígito em qualquer posição.
5. Ordena por plausibilidade: menos trocas e, entre elas, trocas que são **confusões típicas do OCR**:
   `0↔8, 3↔8, 5↔6, 6↔8, 1↔7, 4↔9, 0↔6, 0↔9, 5↔8, 2↔7, 1↔4, 3↔5, 8↔9`.
6. `tentar_corrigir` só aceita sozinho quando há **um único** candidato; com vários, `_desempatar` usa o valor e o
   vencimento impressos; se ainda houver dúvida, as sugestões vão para a tela (`sugestoes_linha`).

## 3.3 PDF (`leitores.DocumentoPDF`)
- `pypdfium2`: para cada página, texto com a caixa de cada caractere → `Segmento(texto, x0, y0, x1, y1, pagina, confianca)`
  (origem no canto superior esquerdo), corrige ligaduras (`ﬁ`→`fi`…).
- **Página escaneada** = imagens cobrindo mais de 50% da área.
- Renderiza **uma página por vez** (escala = min(3,0; 3000 px / maior lado)) — PDFs de 30 páginas não estouram memória.

## 3.4 Imagens
- `abrir_imagem`: corrige a rotação EXIF, transparência vira fundo branco, RGB, maior lado ≤ 3200 px. HEIC via `pillow-heif`.
- **Modo scanner** (`imagem.endireitar_documento`, só para fotos): reduz para 1000 px, se as bordas já são claras
  (mediana > 200) não mexe; acha o contorno do papel (4 cantos), ordena os cantos, corrige a perspectiva
  (`getPerspectiveTransform` + `warpPerspective`); rejeita resultados < 300 px ou proporção fora de 0,25–4.
- `melhorar_para_ocr`: divide pela iluminação de fundo (dilatação 7×7 + mediana 31) e aplica CLAHE (clip 2, 8×8).

## 3.5 Código de barras (`leitores.ler_codigos_barras`)
`zxing-cpp`, formato **ITF**, testando variantes até achar: original (cinza) → contraste automático → nitidez (unsharp) →
binarizadores GlobalHistogram e FixedThreshold → ampliada 2× (se < 2400 px) → reduzida ½ (se > 1800 px) → binarização
adaptativa gaussiana (31, 10) → "barras reforçadas" (abertura morfológica 5×1). Aceita só leituras de **44 dígitos que
passam na validação** (ITF não tem checksum próprio). Guarda a **orientação** (usada para endireitar a página) e a
posição vertical (para casar com os campos quando há vários boletos na página).

## 3.6 OCR (`ocr.py`)
- RapidOCR 3 com reconhecimento **latino PP-OCRv5** (acentos e espaços); baixa os modelos na primeira vez (~20 MB);
  sem internet, cai para o `rapidocr_onnxruntime` básico. Carregado em segundo plano ao iniciar.
- **Cache LRU** pelo hash da imagem (reenviar o mesmo arquivo ou a mesma rotação não repete o OCR).
- `_ocr_pagina`: se o texto está majoritariamente vertical, testa 90° e 270° e fica com a orientação que forma mais
  campos de boleto; se a pontuação (caracteres × confiança) < 80, tenta 90/270/180 (aceita se +30%); se < 250, tenta
  de novo com `melhorar_para_ocr` (aceita se +15%).
- PDF escaneado **com** texto do scanner: se faltar código ou algum de beneficiário/nº doc/vencimento/valor, roda o
  nosso OCR como **complemento** e preenche só o que faltou.

## 3.7 Extração dos campos pelo leiaute (`texto.py`)

Boletos são "fichas": rótulo pequeno com o valor ao lado ou logo abaixo. Para cada campo há uma lista de rótulos
(regex sobre o texto normalizado), com prioridade:

| Campo | Rótulos (prioridade 0 → 2) | Extrator |
|---|---|---|
| Beneficiário | `bene\w{2,6}rio`, `cedente` (exceto se antes vier agência/código/cpf/cnpj/endereço/sacador/avalista, ou depois "final") → `favorecido`, `razão social` | `extrair_beneficiario` |
| Vencimento | `venc(imento\|to)` → `pag(ar\|avel\|amento) ... até` → `data limite`, `válido até` | `extrair_data` (dd/mm/aaaa, por extenso, `10/OUT/2026`) |
| Nº documento | `n/no/nr/num/numero (do) doc(umento)` → `seu número`, `nº fatura` → `nota fiscal (nº)` | `extrair_documento` |
| Valor | `valor (do) documento` → `valor cobrado/a pagar/total a pagar/valor total` → `valor` (sempre excluindo segmentos com desconto/abatimento/mora/multa/juros/acréscimo/dedução/outros/encargo) | `extrair_valor` |

Busca espacial (`_buscar_campo`) para cada segmento que contém um rótulo (ignorando rótulo no meio de frase: mais de
4 palavras ou 32 caracteres antes):
1. valor **no próprio segmento**, depois do rótulo;
2. **à direita** na mesma linha (até 12 alturas de letra; para se encontrar outro rótulo);
3. **logo abaixo**, dentro da "célula" do rótulo (até 3 alturas abaixo, limitado pelo próximo rótulo à direita).

Pontuação (menor é melhor): `prioridade×10 + (distância vertical até o código de barras do boleto ×4, quando há vários
boletos) + (1 − confiança do OCR)` + 1 (à direita) ou + 2 (abaixo) + distância. Confiança do campo =
`max(0,5; min(0,97; 0,95 − pontuação×0,02)) × confiança do segmento`, +0,03 se o mesmo valor aparece mais de uma vez.

Complementos: razão social quebrada em duas linhas (termina em "e/de/da/&…" → junta a linha de baixo); **plano B** com
regex no texto corrido (confiança 0,6); CPF/CNPJ do beneficiário no próprio segmento, nos vizinhos ou até 160
caracteres depois do rótulo (CNPJ validado pelos DVs).

**Guias de tributos** (`identificar_guia`): DAS/Simples Nacional, DARF, GPS/INSS, FGTS, DETRAN, IPVA, IPTU, DAE/GARE/DARJ,
ISS → o beneficiário é o **órgão** e o CNPJ impresso (que é do contribuinte) é descartado.
**Contas de consumo sem rótulo** (`nome_no_cabecalho`): o nome em destaque no topo, excluindo palavras de boleto,
bancos e URLs (confiança limitada a 0,5 em boletos bancários).

Linha digitável no texto (`encontrar_codigos`): trechos com ≥ 40 caracteres de dígitos e confusões do OCR
(`O/o→0, I/l/|→1, S→5, B→8, Z→2`), testa 47/48/44 dígitos, válidos ou com correção.

## 3.8 Consolidação de um boleto (`extrator.consolidar`)

| Situação | Campo usado | Confiança |
|---|---|---|
| Código válido lido por código de barras | linha/barras | 0,99 (0,995 se o texto concorda) |
| Código válido do texto do PDF / do OCR | linha/barras | 0,97 / 0,90 |
| Código corrigido e desempatado | linha/barras | 0,75 + alerta "corrigido" |
| Código inválido | linha/barras | 0,3 + alerta de erro |
| Vencimento do fator (bancário) | do código | 0,99 se bate com o impresso; 0,9 se não (alerta) |
| Vencimento estimado (arrecadação) | campo livre | 0,5 + alerta |
| Valor do código > 0 | do código | 0,99 se bate; 0,92 se não (alerta) |
| Código sem valor | o impresso | a do texto + alerta informativo |

**Confiança do boleto** = menor confiança entre linha digitável, vencimento, valor e beneficiário (campos com
confiança baixa ficam **amarelos** na tela).

**Alertas** (nível erro/aviso/info, com código): `linha_invalida`, `linha_corrigida`, `sem_codigo`,
`vencimento_divergente`, `vencimento_estimado`, `valor_divergente`, `valor_do_documento`, `valor_referencia`,
`ausente_<campo>`, `vencido`, `vence_hoje`, `vence_em_breve` (≤ 3 dias), `duplicado` (código já lançado: mostra ID e
data), `beneficiario_historico`, `beneficiario_consenso`.

**Vários boletos na mesma página / carnês**: cada código encontrado vira um boleto; os campos são buscados perto da
posição vertical do código. Página sem código mas com vencimento/valor/nº doc → boleto "sem código" (o mais completo).

**Harmonização** (`harmonizar_beneficiarios`): mesmo CPF/CNPJ → mesmo nome. Se o documento já foi lançado, usa o nome
gravado (confiança 0,97); entre boletos do mesmo arquivo, vence o nome com maior soma de confianças.

Resposta de `ler_arquivo`: `{tipo_arquivo, paginas, boletos:[{pagina, campos:{campo:{valor,fonte,confianca,
alternativas}}, codigo, tipo, emissor, sugestoes_linha, alertas, duplicado, confianca}], ocr_usado, ocr_modelo,
tratamentos:[perspectiva|rotacao], avisos, tempo_ms, texto}`.

## 3.9 Outras entradas
- **Linha digitada/colada** (`POST /api/leituras/linha` → `analisar_linha_digitada`): valida/corrige e consolida.
- **IA** (`ia.py`, opcional, `ANTHROPIC_API_KEY`): envia a página (imagem) ao Claude com visão pedindo os campos em
  JSON; `mesclar_ia` só aceita a linha se passar na validação FEBRABAN; botão "Analisar com IA" na revisão
  (`POST /api/leituras/{arquivo_id}/ia`). Modelo em `LEITOR_IA_MODELO`.
- **Lançar** (`POST /api/boletos` com lista): grava em lote; bloqueia código de barras já lançado; campos gravados
  conforme `editaveis` da aba `boletos` (A2).

## 3.10 Testes de referência
`test_codigo.py` (DVs, conversões, fator nos dois ciclos, correção), `test_texto.py` (extração espacial, datas,
valores), `test_corpus.py` (corpus gerado: rótulos na linha, conta de consumo, DAS, carnê, PDF escaneado, fotos com
perspectiva — `tests/corpus.py`), `test_api.py`, `test_harmonizacao.py`. Lista completa em A6.

# Missão: construir o novo Fin Pro, do zero, sozinho

Você (Claude) vai construir **nesta pasta** o sistema **Fin Pro** completo — o sistema financeiro de um escritório
(boletos, Pix, comprovantes, caixa, diesel, gastos, empresas/vendas a prazo, notificações, 4 bots do Telegram) — a
partir da especificação em `especificacao/`. O dono do sistema **não quer ser interrompido**: trabalhe de forma
autônoma, do começo ao fim, decidindo sozinho com base nas regras abaixo. Fale com ele em **português do Brasil**.

## 1. Regras de autonomia (leia primeiro)

1. **Não pergunte ao dono** sobre escolhas técnicas, nomes, estrutura, bibliotecas, ordem ou detalhes. As decisões já
   estão tomadas em `DECISOES.md`. Quando algo não estiver decidido, siga a **ordem de autoridade** (item 2), escolha a
   opção mais simples que passa nos testes, **anote** em `PROGRESSO.md` → "Decisões que tomei" e siga em frente.
2. **Ordem de autoridade** quando houver dúvida ou conflito:
   1. os **testes** em `tests/` (são o contrato; o código deles também está em `especificacao/A10-codigo-dos-testes.md`);
   2. os anexos gerados do código original (`A1` rotas, `A2` campos, `A3` configurações, `A4` funções e assinaturas,
      `A7` formato das respostas, `A8` constantes por extenso, `A9` o que cada tela chama);
   3. os capítulos `01`–`16` da especificação;
   4. o manual de uso (`especificacao/MANUAL_DE_USO.md`);
   5. o seu bom senso, registrado em `PROGRESSO.md`.
3. **Só pare e chame o dono** nestes casos (e em nenhum outro):
   - precisar de uma **senha, token, chave de API ou conta** (Telegram, e-mail, Anthropic, servidor) — nunca invente
     nem use credenciais reais; tudo deve funcionar e ser testado sem elas;
   - algo exigir **pagamento**;
   - algo puder **apagar ou alterar dados reais** do Fin Pro atual (a pasta `dados` do sistema antigo) — você **nunca**
     deve tocar nela;
   - o computador não tiver Python 3.10+ e você não conseguir instalar.
   Mesmo nesses casos, **continue todo o resto** e deixe a pendência anotada em `PROGRESSO.md` → "Precisa do dono".
4. **Nunca** faça chamadas reais ao Telegram, e-mail ou IA durante a construção ou os testes (os testes simulam tudo).
   Nunca crie contas, nunca publique nada na internet, nunca envie mensagens em nome do dono.
5. **Memória entre sessões**: o contexto da conversa acaba. Por isso `PROGRESSO.md` é a sua memória. **Ao começar
   qualquer sessão**: leia este arquivo, `DECISOES.md` e `PROGRESSO.md`, rode `python ferramentas/progresso.py` e
   continue da primeira etapa não concluída. **Ao terminar cada etapa** (ou a cada ~1 hora de trabalho): atualize
   `PROGRESSO.md` (o que foi feito, testes, próximos passos, decisões).

## 2. Como trabalhar (o ciclo de cada etapa)

1. Leia a etapa em `especificacao/12-plano-de-reconstrucao.md` e os capítulos que ela cita.
2. Leia **antes** `especificacao/14-licoes-aprendidas.md` (46 erros reais que você não deve repetir).
3. Implemente usando os anexos como referência **exata** (nomes de módulos, funções, campos, rotas, constantes).
4. Rode os testes da etapa: `python ferramentas/progresso.py --etapa N` (ou `python -m pytest tests/test_x.py -q`).
5. Corrija até passar. **Nunca altere um teste para ele passar** — o teste é o contrato. Se tiver certeza de que um
   teste depende de algo do ambiente original (data, máquina), anote em `PROGRESSO.md` e siga.
6. Atualize `PROGRESSO.md` e passe para a próxima etapa.

**Etapa zero obrigatória (esqueleto):** os testes importam módulos de todo o sistema (por exemplo, qualquer teste da API
importa `app.main`, que importa todas as rotas, Empresas, Caixa, Diesel…). Então, **antes de implementar qualquer
etapa**, crie o **esqueleto completo** de `app/` seguindo `especificacao/A4-mapa-do-codigo.md`: todos os módulos, classes
e funções com as **mesmas assinaturas**, corpo `raise NotImplementedError` (ou um retorno vazio coerente), e as
constantes do `A8`. Assim os imports funcionam desde o início e cada etapa só preenche o que falta.

## 3. Ambiente (Windows)

```bash
py -3 -m venv .venv            # ou: python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q          # todos os testes
.venv\Scripts\python ferramentas\progresso.py   # placar por etapa
```
- O OCR (RapidOCR) baixa ~20 MB de modelos na primeira vez; sem internet, usa o modelo básico — siga em frente.
- `tests/test_telas.py` usa Playwright com o Microsoft Edge instalado; se o Playwright/Edge não estiver disponível, esses
  testes são pulados — não é bloqueio.
- **Dica Windows (lição #43):** escreva e edite arquivos com as ferramentas de arquivo (UTF-8). Não passe código com
  acentos pela linha de comando (heredoc/stdin), porque os acentos podem se corromper.
- Ícones prontos em `web/icons/` (não precisa desenhar). `referencia/` tem o README, `.env.example`, `iniciar.bat`,
  `demonstracao.bat`, `versoes.bat`, `.gitignore` e `.gitattributes` do sistema original — use como modelo.
- **Controle de versão e backup total** (especificação 11.1 e 11.6): o projeto novo é um repositório git local desde a
  etapa 0 (`git init -b main`, usando o `.gitignore` de `referencia/` — `dados/` e `.env` nunca entram). O backup leva
  código, versões, bancos, arquivos e configurações, e `ferramentas/restaurar_backup.py` usa só a biblioteca padrão.

## 4. Onde está cada coisa

| Preciso de… | Arquivo |
|---|---|
| Visão geral e ordem de leitura | `especificacao/00-LEIA-ME.md` |
| O que o usuário vê em cada tela | `especificacao/MANUAL_DE_USO.md` |
| Roteiro e critério de aceite | `especificacao/12-plano-de-reconstrucao.md` |
| Erros a não repetir | `especificacao/14-licoes-aprendidas.md` |
| O que fazer melhor / o que não mudar | `especificacao/15-melhorias-para-a-proxima-versao.md` |
| Fluxos completos | `especificacao/13-fluxos-ponta-a-ponta.md` |
| Assinatura exata de cada função | `especificacao/A4-mapa-do-codigo.md` |
| Campos de cada tabela | `especificacao/A2-modelo-de-dados.md` |
| Rotas, permissões e corpos | `especificacao/A1-api.md` |
| Formato de cada resposta | `especificacao/A7-respostas-da-api.md` |
| Listas de palavras, regex, limites | `especificacao/A8-constantes.md` |
| O que cada tela chama | `especificacao/A9-telas-e-chamadas.md` |
| Variáveis e JSON de configuração | `especificacao/A3-configuracoes.md` |

## 5. Quando terminar

Considere pronto quando:
1. `python -m pytest -q` passa (todos os 273 testes; os de tela podem ser pulados se não houver Edge/Playwright);
2. `iniciar.bat` abre o aplicativo, e `demonstracao.bat` abre a demonstração com dados de exemplo (porta 8010);
3. todas as telas do manual existem e abrem sem erro no console (inclusive o menu **Relatórios**);
4. `README.md` explica como usar; `PROGRESSO.md` tem o resumo final.

Então escreva ao dono um resumo curto em português: o que foi feito, como abrir, o que ficou pendente
(seção "Precisa do dono") e as melhorias opcionais da Fase 2 que você aplicou ou sugere.

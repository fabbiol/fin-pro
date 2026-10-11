# Como usar este kit (para o dono)

Este kit tem tudo para outra conversa com o Claude construir um **Fin Pro novo, do zero**, sozinha.

## Passo a passo (5 minutos do seu tempo)

1. **Copie esta pasta inteira** ("Kit - Novo Fin Pro") para onde quiser o sistema novo, por exemplo
   `C:\Users\Fábio\Documents\Novo Fin Pro`. **Não coloque dentro da pasta do Fin Pro atual.**
2. Abra o **aplicativo Claude** no computador → aba **Code** → abra (ou escolha como pasta de trabalho) a pasta copiada.
   > Use a aba **Code** (Claude Code). O chat comum do site não consegue instalar programas nem rodar os testes, e não
   > conseguiria construir o sistema sozinho.
3. Se puder, escolha o modo de permissões que deixa ele **editar arquivos e rodar comandos sem pedir confirmação**
   a cada passo (o "auto"/aceitar edições). Assim você não precisa ficar aprovando.
4. Cole esta mensagem e envie:

   > Leia o CLAUDE.md desta pasta e construa o novo Fin Pro completo, seguindo o plano, de forma autônoma, sem me
   > perguntar nada que esteja decidido. Só me chame se precisar de senha, token, pagamento ou acesso a dados reais.
   > Atualize o PROGRESSO.md a cada etapa.

5. Pronto. Ele vai trabalhar etapa por etapa e registrar tudo no `PROGRESSO.md`.

## Se a conversa parar no meio

Conversas longas acabam (limite de uso ou de tamanho). Isso é normal. Para continuar, abra uma conversa nova na
**mesma pasta** e mande:

> Continue a construção do Fin Pro de onde parou: leia CLAUDE.md, DECISOES.md e PROGRESSO.md e siga para a próxima etapa.

Ele retoma sozinho pelo `PROGRESSO.md`.

## Como acompanhar
- Abra o `PROGRESSO.md` para ver em que etapa está, o diário e o que ele decidiu.
- Para ver o placar dos testes você mesmo: na pasta, rode `.venv\Scripts\python ferramentas\progresso.py`.
- Quando terminar: dois cliques em `iniciar.bat` abrem o sistema novo; `demonstracao.bat`, a demonstração.

## O que ele pode precisar de você (raramente)
Só **senhas, tokens, pagamentos ou acesso aos seus dados reais** — e tudo isso é opcional para construir e testar.
Os bots e o e-mail você liga depois, pela própria tela do sistema, como faz hoje.

## Quanto tempo leva
É um sistema grande (cerca de 22 mil linhas de código no original). Conte com **várias sessões** de trabalho do Claude.
O plano tem 16 etapas, e cada uma termina com os testes passando.

## Seus dados atuais
O sistema novo começa **vazio**. Quando estiver pronto e conferido, a migração dos dados (pastas `dados/` do Fin Pro
atual) é um passo separado — faça com calma, com o Fin Pro atual fechado, e com backup.

## O que tem no kit
| Item | Para quê |
|---|---|
| `CLAUDE.md` | As instruções que o Claude lê sozinho ao abrir a pasta (missão, regras de autonomia, ciclo de trabalho) |
| `DECISOES.md` | Decisões já tomadas, para ele não precisar perguntar |
| `PROGRESSO.md` | A memória da construção (etapas, diário, pendências) |
| `especificacao/` | A especificação completa (27 documentos + o manual de uso) |
| `tests/` | Os 273 testes do sistema atual — o contrato que o novo precisa cumprir |
| `ferramentas/progresso.py` | Placar dos testes por etapa |
| `web/icons/`, `web/manifest.json` | Ícones do aplicativo |
| `requirements.txt` | Bibliotecas necessárias |
| `referencia/` | README, `.env.example`, `iniciar.bat`, `demonstracao.bat`, `versoes.bat`, `.gitignore` e `.gitattributes` do original, como modelo |

**Atenção:** a pasta `especificacao/` e os `tests/` contêm textos de documentos reais seus (cheque, comprovantes,
canhoto), usados para calibrar a leitura. Não compartilhe o kit fora da empresa.

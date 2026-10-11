// Caixa · configuração do bot do caixa (token e quem pode usar — vem dos outros dois bots).
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";

export function htmlBotCaixa(cfg) {
  const pessoas = cfg.pessoas || [];
  return `<section class="config-grade">
    <article class="card">
      <h3>${icone("telegram", 18)} Bot do caixa</h3>
      <p class="sutil">Um terceiro bot, só para os <strong>gastos em dinheiro</strong>. Crie no <code>@BotFather</code> do
        Telegram (<code>/newbot</code>) e cole o token aqui. Quem manda a foto do cupom recebe as perguntas (onde foi gasto
        e o centro de custo) e o gasto fica pronto em <strong>Conferência</strong> para você lançar.</p>
      <form class="grade-campos" data-form-bot-caixa>
        <div class="campo col-2"><label for="bc-token">Token do bot</label>
          <input id="bc-token" name="token" class="input mono" value="${esc(cfg.token || "")}" maxlength="200"
            placeholder="123456789:AAE..." autocomplete="off"></div>
        <label class="opcao-app col-2"><span class="interruptor">
          <input type="checkbox" name="ativo" ${cfg.ativo ? "checked" : ""}><span></span></span>
          <span><strong>Receber pelo bot do caixa</strong><small>Fotos de cupons fiscais e notas de compras pagas em
            dinheiro.</small></span></label>
        <div class="linha-botoes col-2">
          <button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button>
          <button class="btn" type="button" data-acao="verificar-bot-caixa">${icone("atualizar", 15)} Verificar agora</button>
        </div>
      </form>
      ${cfg.ultimo_erro ? `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(cfg.ultimo_erro)}</div></div>` : ""}
      ${cfg.ultima_verificacao ? `<p class="sutil">Última verificação: ${dataHoraBR(cfg.ultima_verificacao)}.</p>` : ""}
    </article>

    <article class="card">
      <h3>${icone("usuarios", 18)} Quem pode usar</h3>
      <p class="sutil">São as mesmas pessoas e grupos do <strong>bot dos boletos</strong> (Notificações → Telegram) e do
        <strong>bot de notas</strong> (Empresas → Bot de notas). Para incluir alguém, cadastre em um deles.
        A pessoa só precisa abrir o bot do caixa e enviar <code>/start</code> uma vez.</p>
      <ul class="lista-mini">
        ${pessoas.length ? pessoas.map((p) => `<li><div class="info"><div class="titulo">${icone("check", 14)} ${esc(p.nome || p.chat_id)}</div>
          <div class="sutil">chat ${esc(p.chat_id)}</div></div></li>`).join("")
          : `<li class="sutil">Ninguém ainda: cadastre as pessoas no bot dos boletos ou no bot de notas.</li>`}
      </ul>
      <div class="linha-botoes">
        <a class="btn btn-sm" href="#/notificacoes">${icone("sino", 14)} Pessoas do bot dos boletos</a>
        <a class="btn btn-sm" href="#/empresas?aba=bot">${icone("carteira", 14)} Pessoas do bot de notas</a>
      </div>
    </article>
  </section>`;
}

export async function salvarBotCaixa(formulario) {
  const dados = Object.fromEntries(new FormData(formulario));
  try {
    await api.post("/api/caixa/bot/config", { token: dados.token || "", ativo: Boolean(dados.ativo) });
    toast("Bot do caixa salvo.", "ok");
    window.dispatchEvent(new Event("caixa:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export async function verificarBotCaixa() {
  try {
    const r = await api.post("/api/caixa/bot/verificar", {});
    toast(r.recebidos ? `${r.recebidos} comprovante(s) recebido(s).` : "Nenhuma foto nova no bot do caixa.", "ok");
    window.dispatchEvent(new Event("caixa:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

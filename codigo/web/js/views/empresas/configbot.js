// Empresas e fechamentos · minha empresa, dia do fechamento e o bot de notas fiscais.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";
import { carregarDados, tentar } from "./comum.js";
import { tela } from "./estado.js";

export function htmlBot() {
  const c = tela.dados?.config || {};
  const bot = c.bot || {};
  const minha = c.minha_empresa || {};
  const destinatarios = bot.destinatarios || [];
  const liberados = new Set(destinatarios.map((d) => d.chat_id));
  const esperando = (bot.chats || []).filter((c) => !liberados.has(c.chat_id));
  return `
    <section class="config-grade">
      <article class="card">
        <h3>${icone("carteira", 18)} A minha empresa</h3>
        <p class="sutil">Aparece no cabeçalho do fechamento enviado para os clientes.</p>
        <form class="grade-campos" data-form-config>
          <div class="campo col-2"><label for="me-nome">Nome</label>
            <input id="me-nome" name="nome" class="input" value="${esc(minha.nome || "")}" maxlength="120"
              placeholder="Prospera Industria E Serviços LTDA"></div>
          <div class="campo col-2"><label for="me-cnpj">CNPJ</label>
            <input id="me-cnpj" name="cnpj" class="input" value="${esc(minha.cnpj || "")}" maxlength="20"
              placeholder="03.880.985/0001-85"></div>
          <div class="campo"><label for="me-dia">Dia do fechamento</label>
            <input id="me-dia" name="dia_fechamento" type="number" min="1" max="28" class="input" value="${c.dia_fechamento || 20}"></div>
          <div class="campo"><label for="me-hora">Hora do envio</label>
            <input id="me-hora" name="hora_envio" type="time" class="input" value="${esc(c.hora_envio || "08:00")}"></div>
          <label class="opcao-app col-2"><span class="interruptor">
            <input type="checkbox" name="fechamento_automatico" ${c.fechamento_automatico ? "checked" : ""}><span></span></span>
            <span><strong>Enviar o fechamento sozinho</strong><small>No dia e na hora escolhidos, para quem está
              cadastrado no bot de notas.</small></span></label>
          <div class="linha-botoes col-2"><button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button></div>
        </form>
        ${c.ultimo_fechamento ? `<p class="sutil">Último fechamento enviado: ${esc(c.ultimo_fechamento)}.</p>` : ""}
      </article>

      <article class="card">
        <h3>${icone("telegram", 18)} Bot de notas fiscais</h3>
        <p class="sutil">Um bot <strong>só para as notas, cheques e comprovantes dos clientes</strong> — separado do bot
          dos boletos. Crie no <code>@BotFather</code> do Telegram, mande <code>/newbot</code> e cole o token aqui.</p>
        <form class="grade-campos" data-form-bot>
          <div class="campo col-2"><label for="bot-token">Token do bot</label>
            <input id="bot-token" name="token" class="input mono" value="${esc(bot.token || "")}" maxlength="200"
              placeholder="123456789:AAE..." autocomplete="off"></div>
          <label class="opcao-app col-2"><span class="interruptor">
            <input type="checkbox" name="ativo" ${bot.ativo ? "checked" : ""}><span></span></span>
            <span><strong>Receber pelo bot de notas</strong><small>Notas fiscais, cheques e comprovantes enviados
              pelos clientes e pela equipe.</small></span></label>
          <div class="linha-botoes col-2">
            <button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button>
            <button class="btn" type="button" data-acao="verificar-bot">${icone("atualizar", 15)} Verificar agora</button>
            <button class="btn" type="button" data-acao="procurar-chats">${icone("busca", 15)} Procurar quem falou com o bot</button>
          </div>
        </form>
        ${bot.ultimo_erro ? `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(bot.ultimo_erro)}</div></div>` : ""}
        ${bot.ultima_verificacao ? `<p class="sutil">Última verificação: ${dataHoraBR(bot.ultima_verificacao)}.</p>` : ""}

        <h4>Quem pode mandar notas, cheques e comprovantes</h4>
        <p class="sutil">Pode ser mais de uma pessoa: cada um abre o bot no Telegram, envia <code>/start</code> e aparece
          aqui para você liberar. Também dá para liberar um <strong>grupo</strong> inteiro do escritório.</p>
        <ul class="lista-mini" data-destinatarios>
          ${destinatarios.length ? destinatarios.map((d) => `<li>
            <div class="info"><div class="titulo">${icone("check", 14)} ${esc(d.nome || d.chat_id)}</div>
              <div class="sutil">chat ${esc(d.chat_id)}${d.empresa ? ` · ${esc(d.empresa)}` : ""}</div></div>
            <button class="btn btn-sm btn-fantasma" data-acao="remover-destinatario" data-chat="${esc(d.chat_id)}">
              ${icone("x", 14)} Remover</button></li>`).join("")
            : `<li class="sutil">Ninguém liberado ainda: o bot recusa arquivos de quem não está na lista.</li>`}
        </ul>
        ${esperando.length ? `<h4>Falaram com o bot e ainda não podem enviar</h4>
        <ul class="lista-mini">
          ${esperando.map((c) => `<li>
            <div class="info"><div class="titulo">${esc(c.nome || c.chat_id)}</div>
              <div class="sutil">chat ${esc(c.chat_id)}${c.tipo && c.tipo !== "private" ? " · grupo" : ""}</div></div>
            <button class="btn btn-sm btn-primario" data-acao="liberar-chat" data-chat="${esc(c.chat_id)}"
              data-nome="${esc(c.nome || "")}">${icone("check", 14)} Liberar</button></li>`).join("")}
        </ul>` : ""}
        <div class="linha-botoes">
          <button class="btn btn-sm" data-acao="trazer-avisos">${icone("usuarios", 14)} Trazer quem recebe os avisos dos boletos</button>
          <button class="btn btn-sm" data-acao="adicionar-chat">${icone("mais", 14)} Adicionar pelo chat ID</button>
        </div>
      </article>
    </section>`;
}

async function salvarConfig(corpo, mensagem = "Configuração salva.") {
  const salvo = await tentar(() => api.post("/api/empresas/config", corpo), mensagem);
  if (!salvo) return null;
  await carregarDados();
  window.dispatchEvent(new Event("empresas:atualizar"));
  return salvo;
}

export async function aoEnviarFormulario(e) {
  if (e.target.matches("[data-form-config]")) {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(e.target));
    await salvarConfig({
      minha_empresa: { nome: dados.nome || "", cnpj: dados.cnpj || "" },
      dia_fechamento: Number(dados.dia_fechamento) || 20,
      hora_envio: dados.hora_envio || "08:00",
      fechamento_automatico: Boolean(dados.fechamento_automatico),
    });
    return true;
  }
  if (e.target.matches("[data-form-bot]")) {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(e.target));
    await salvarConfig({ bot: { token: dados.token || "", ativo: Boolean(dados.ativo) } }, "Bot de notas salvo.");
    return true;
  }
  return false;
}

export async function verificarBot() {
  const resultado = await tentar(() => api.post("/api/empresas/entrada/verificar", {}));
  if (resultado) {
    toast(resultado.recebidos ? `${resultado.recebidos} arquivo(s) recebido(s).` : "Nenhum arquivo novo no bot de notas.",
          "ok", { duracao: 5000 });
    window.dispatchEvent(new Event("empresas:atualizar"));
  }
}

export async function procurarChats() {
  let resposta;
  try {
    resposta = await api.get("/api/empresas/config/chats");
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return;
  }
  const chats = resposta.chats || [];
  if (!chats.length) {
    toast(`Ninguém falou com o bot ainda. Peça para abrirem @${resposta.bot?.usuario || "seu bot"} no Telegram e enviarem /start.`,
          "aviso", { duracao: 8000 });
    return;
  }
  const atuais = tela.dados?.config?.bot?.destinatarios || [];
  const novos = chats.filter((c) => !atuais.some((d) => d.chat_id === c.chat_id));
  if (!novos.length) {
    toast("Todos os que falaram com o bot já estão cadastrados.", "info");
    return;
  }
  await salvarConfig({ bot: { destinatarios: [...atuais, ...novos.map((c) => ({ chat_id: c.chat_id, nome: c.nome }))] } },
                     `${novos.length} pessoa(s) cadastrada(s) no bot de notas.`);
}

export async function liberarChat(chatId, nome) {
  const atuais = tela.dados?.config?.bot?.destinatarios || [];
  if (atuais.some((d) => d.chat_id === chatId)) return;
  await salvarConfig({ bot: { destinatarios: [...atuais, { chat_id: chatId, nome }] } },
                     `${nome || "Pessoa"} já pode mandar notas, cheques e comprovantes.`);
}

/** Atalho: quem já recebe os avisos de boletos costuma ser a mesma equipe. */
export async function trazerDosAvisos() {
  const avisos = await tentar(() => api.get("/api/notificacoes"));
  if (!avisos) return;
  const equipe = (avisos.config?.telegram?.destinatarios || []).filter((d) => d.ativo !== false);
  if (!equipe.length) {
    toast("Ninguém está cadastrado nos avisos de boletos (Notificações → Telegram).", "aviso", { duracao: 6000 });
    return;
  }
  const atuais = tela.dados?.config?.bot?.destinatarios || [];
  const novos = equipe.filter((d) => !atuais.some((a) => a.chat_id === d.chat_id));
  if (!novos.length) {
    toast("Todo mundo dos avisos já pode mandar arquivos para o bot de notas.", "info");
    return;
  }
  await salvarConfig({ bot: { destinatarios: [...atuais, ...novos.map((d) => ({ chat_id: d.chat_id, nome: d.nome }))] } },
                     `${novos.length} pessoa(s) liberada(s) no bot de notas.`);
}

export async function removerDestinatario(chatId) {
  const atuais = tela.dados?.config?.bot?.destinatarios || [];
  await salvarConfig({ bot: { destinatarios: atuais.filter((d) => d.chat_id !== chatId) } }, "Removido do bot de notas.");
}

export async function adicionarChat() {
  const { pedirTexto } = await import("../../ui.js");
  const chatId = await pedirTexto({
    titulo: "Adicionar ao bot de notas",
    rotulo: "Chat ID",
    descricao: "Peça para a pessoa enviar /start ao bot e use “Procurar quem falou com o bot”, ou informe o chat ID.",
    placeholder: "123456789",
  });
  if (!chatId) return;
  const atuais = tela.dados?.config?.bot?.destinatarios || [];
  await salvarConfig({ bot: { destinatarios: [...atuais, { chat_id: chatId, nome: "" }] } }, "Cadastrado no bot de notas.");
}

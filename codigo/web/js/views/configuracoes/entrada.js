// Configurações · Receber boletos e comprovantes por e-mail (IMAP) e pelo bot do Telegram.
// Mudar a configuração exige a senha de administrador (ou um usuário administrador), mas funciona de qualquer aparelho,
// inclusive na VPS. "Verificar agora" só precisa da permissão de lançar boletos.
import { api } from "../../api.js";
import { pode } from "../../estado.js";
import { icone } from "../../icons.js";
import { dataHoraBR, esc, toast } from "../../ui.js";
import { avisarErro, comAdmin } from "./eventos.js";
import { htmlTravaAdmin, podeAdministrar } from "./importacao.js";
import { alertaErro, atualizar, buscar, carregarAcesso, carregarAdmin, redesenhar, tela } from "./tela.js";

export const chave = "entrada";

/** Caixas de e-mail mais comuns (todas por IMAP com SSL, porta 993). */
export const PROVEDORES_IMAP = [
  { chave: "gmail", nome: "Gmail", servidor: "imap.gmail.com", porta: 993 },
  { chave: "outlook", nome: "Outlook / Hotmail / Microsoft 365", servidor: "outlook.office365.com", porta: 993 },
  { chave: "yahoo", nome: "Yahoo", servidor: "imap.mail.yahoo.com", porta: 993 },
  { chave: "uol", nome: "UOL", servidor: "imap.uol.com.br", porta: 993 },
];

const DESCRICAO_SENHA = "Digite a senha de administrador para configurar o recebimento por e-mail e Telegram.";

/** GET /api/entrada (itens, pendentes e config), a senha de administrador e quem entrou. */
export async function carregar() {
  const [e] = await Promise.all([buscar("/api/entrada"), carregarAdmin(), carregarAcesso()]);
  return e;
}

// ------------------------------------------------------------------ desenho

/** Situação da última verificação de um canal (erro, quando foi, ou "ainda não verificado"). */
export function linhaVerificacao(c) {
  if (c?.ultimo_erro) return `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(c.ultimo_erro)}</div></div>`;
  if (c?.ultima_verificacao) return `<p class="sutil">Última verificação: ${esc(dataHoraBR(c.ultima_verificacao))}.</p>`;
  if (c?.ativo) return `<p class="sutil">Ainda não verificado.</p>`;
  return "";
}

const campo = (rotulo, id, controle, classe = "") => `<div class="campo ${classe}"><label for="${id}">${rotulo}</label>${controle}</div>`;

function htmlEmail(c, liberadoAqui, podeVerificar) {
  const d = liberadoAqui ? "" : "disabled";
  const provedor = PROVEDORES_IMAP.find((p) => p.servidor === c.servidor)?.chave || "";
  const configurado = Boolean(c.servidor && c.usuario && c.senha);
  return `<form class="entrada-bloco" data-acao="entrada-salvar-email" autocomplete="off" novalidate>
    <div class="entrada-titulo"><strong>${icone("email", 16)} E-mail (IMAP)</strong>
      <label class="interruptor" title="Receber por e-mail"><input type="checkbox" name="ativo" data-acao="entrada-email-ativo"
        aria-label="Receber boletos por e-mail" ${c.ativo ? "checked" : ""} ${d}><span></span></label></div>
    <div class="grade-campos">
      ${campo("Provedor", "en-provedor", `<select id="en-provedor" class="input" data-acao="entrada-provedor" ${d}>
        <option value="">Escolher para preencher…</option>
        ${PROVEDORES_IMAP.map((p) => `<option value="${p.chave}" ${p.chave === provedor ? "selected" : ""}>${esc(p.nome)}</option>`).join("")}
      </select>`)}
      ${campo("Servidor IMAP", "en-servidor", `<input id="en-servidor" name="servidor" class="input" maxlength="300" value="${esc(c.servidor)}"
        placeholder="imap.gmail.com" autocomplete="off" spellcheck="false" ${d}>`)}
      ${campo("E-mail", "en-usuario", `<input id="en-usuario" name="usuario" type="email" class="input" maxlength="300" value="${esc(c.usuario)}"
        placeholder="financeiro@empresa.com.br" autocomplete="off" spellcheck="false" ${d}>`)}
      ${campo("Senha de app", "en-senha", `<input id="en-senha" name="senha" type="password" class="input" maxlength="300" value="${esc(c.senha)}"
        placeholder="Senha de app do e-mail" autocomplete="new-password" ${d}>`)}
      ${campo("Porta", "en-porta", `<input id="en-porta" name="porta" type="number" min="1" max="65535" step="1" class="input"
        value="${esc(c.porta || 993)}" ${d}>`)}
      ${campo("Pasta", "en-pasta", `<input id="en-pasta" name="pasta" class="input" maxlength="300" value="${esc(c.pasta || "INBOX")}"
        placeholder="INBOX" autocomplete="off" spellcheck="false" ${d}>`)}
      ${campo("Aceitar só destes remetentes (opcional)", "en-remetentes", `<input id="en-remetentes" name="remetentes" class="input" maxlength="300"
        value="${esc(c.remetentes)}" placeholder="energisa.com.br, contas@fornecedor.com.br" autocomplete="off" spellcheck="false" ${d}>`, "col-2")}
    </div>
    <p class="sutil">A cada 5 minutos o Fin Pro lê os PDFs e fotos anexados. Os e-mails não são apagados nem marcados como lidos; na
      primeira vez, olha os últimos 7 dias. No Gmail e no Outlook, ative o IMAP e use uma <strong>senha de app</strong> (não a senha normal).</p>
    ${linhaVerificacao(c)}
    <div class="linha-botoes">
      ${liberadoAqui ? `<button class="btn btn-primario" type="submit" data-espera="Salvando…">${icone("check", 16)} Salvar</button>` : ""}
      ${podeVerificar ? `<button class="btn" type="button" data-acao="entrada-verificar" data-canal="email" data-espera="Verificando…"
        ${configurado ? "" : `disabled title="Salve o servidor, o e-mail e a senha primeiro"`}>${icone("atualizar", 16)} Verificar agora</button>` : ""}
    </div>
  </form>`;
}

function htmlTelegram(t, liberadoAqui, podeVerificar) {
  return `<div class="entrada-bloco">
    <div class="entrada-titulo"><strong>${icone("telegram", 16)} Telegram</strong>
      <label class="interruptor" title="Receber pelo Telegram"><input type="checkbox" data-acao="entrada-telegram"
        aria-label="Receber boletos pelo Telegram" ${t.ativo ? "checked" : ""} ${liberadoAqui ? "" : "disabled"}><span></span></label></div>
    <p class="sutil">As pessoas cadastradas em Notificações → Telegram encaminham a foto ou o PDF do boleto (ou do comprovante) para o bot,
      que responde com o que leu. Arquivos de quem não está cadastrado são recusados.</p>
    <p class="sutil">Comandos do bot: /vencidos, /hoje, /semana, /previsao, /resumo, ${esc("/buscar <nome>")} e /ajuda.</p>
    ${linhaVerificacao(t)}
    <div class="linha-botoes">
      ${podeVerificar ? `<button class="btn" type="button" data-acao="entrada-verificar" data-canal="telegram" data-espera="Verificando…">
        ${icone("atualizar", 16)} Verificar agora</button>` : ""}
      <a class="btn btn-fantasma" href="#/notificacoes">${icone("sino", 15)} Bot e pessoas (Notificações)</a>
    </div>
  </div>`;
}

export function html(e, erro) {
  const pendentes = Number(e?.pendentes) || 0;
  const titulo = `<h3>${icone("email", 18)} Receber boletos por e-mail e Telegram${!erro && pendentes > 0
    ? ` <a class="chip info" href="#/ler">${pendentes} aguardando conferência</a>` : ""}</h3>`;
  let corpo;
  if (erro) {
    corpo = `${alertaErro(erro)}
      <div class="linha-botoes"><button class="btn" type="button" data-acao="entrada-recarregar">${icone("atualizar", 16)} Tentar de novo</button></div>`;
  } else if (!e) {
    corpo = `<div class="esqueleto" style="height:220px"></div>`;
  } else {
    const liberadoAqui = podeAdministrar();
    const podeVerificar = pode("lancar");
    const cfg = e.config || {};
    corpo = `<p class="sutil">Boletos e comprovantes que chegam por e-mail ou pelo bot do Telegram são lidos sozinhos e ficam em
      <strong>Ler boletos → Recebidos por e-mail e Telegram</strong> até alguém conferir e lançar. Comprovantes dão baixa automática
      no boleto ou Pix certo.</p>
      ${liberadoAqui ? "" : htmlTravaAdmin("o recebimento por e-mail e Telegram", DESCRICAO_SENHA)}
      <div class="entrada-grade">
        ${htmlEmail(cfg.email || {}, liberadoAqui, podeVerificar)}
        ${htmlTelegram(cfg.telegram || {}, liberadoAqui, podeVerificar)}
      </div>`;
  }
  return `<article class="card col-inteira" id="cfg-entrada">${titulo}${corpo}</article>`;
}

// ------------------------------------------------------------------ ações

const formEmail = () => tela.raiz?.querySelector('#cfg-entrada form[data-acao="entrada-salvar-email"]');

function lerEmail(form) {
  const f = form.elements;
  return {
    ativo: f.ativo.checked,
    servidor: f.servidor.value.trim(),
    porta: Number(f.porta.value) || 993,
    usuario: f.usuario.value.trim(),
    senha: f.senha.value, // como foi digitada: a máscara "••••••••" quer dizer "não mudou"
    pasta: f.pasta.value.trim() || "INBOX",
    remetentes: f.remetentes.value.trim(),
  };
}

/** O formulário de e-mail tem mudanças que ainda não foram salvas? */
function emailAlterado(form) {
  const salvo = tela.dados[chave]?.config?.email || {};
  const atual = lerEmail(form);
  return ["servidor", "usuario", "senha", "pasta", "remetentes"].some((k) => (atual[k] || "") !== String(salvo[k] ?? (k === "pasta" ? "INBOX" : "")))
    || atual.porta !== (Number(salvo.porta) || 993);
}

/** Guarda a resposta de PUT /api/entrada/config (só { email, telegram }) e redesenha o cartão. */
function guardarConfig(config) {
  redesenhar(chave, { ...(tela.dados[chave] || { itens: [], pendentes: 0 }), config });
}

async function salvarEmail(form) {
  const email = lerEmail(form);
  const porta = form.elements.porta;
  if (!Number.isInteger(Number(porta.value || 993)) || email.porta < 1 || email.porta > 65535) {
    toast("Porta inválida. Use 993 (IMAP com SSL).", "aviso", { duracao: 5000 });
    porta.focus();
    throw Object.assign(new Error("Porta inválida."), { silencioso: true });
  }
  if (email.ativo && !(email.servidor && email.usuario && email.senha)) {
    toast("Para receber boletos por e-mail, informe o servidor IMAP, o e-mail e a senha de app.", "aviso", { duracao: 6000 });
    form.elements[!email.servidor ? "servidor" : !email.usuario ? "usuario" : "senha"].focus();
    throw Object.assign(new Error("Campos obrigatórios."), { silencioso: true });
  }
  const r = await comAdmin(() => api.put("/api/entrada/config", { email }), DESCRICAO_SENHA);
  guardarConfig(r);
  toast(r.email?.ativo
    ? "E-mail salvo. O Fin Pro confere a caixa a cada 5 minutos."
    : "E-mail salvo (recebimento por e-mail desligado).", "ok", { duracao: 5000 });
}

async function verificar(alvo) {
  const canal = alvo.dataset.canal === "telegram" ? "telegram" : "email";
  if (canal === "email") {
    const form = formEmail();
    if (form && podeAdministrar() && emailAlterado(form)) {
      toast("Salve as alterações do e-mail antes de verificar.", "aviso", { duracao: 5000 });
      return;
    }
  }
  let r;
  try {
    r = await api.post("/api/entrada/verificar", { canal });
  } catch (erro) {
    await atualizar(chave); // o erro da conexão fica guardado (ultimo_erro) e aparece no cartão
    if (erro?.codigo === "verificacao_falhou" && /Notificações/.test(erro.message)) {
      toast(erro.message, "erro", { duracao: 8000, acao: { rotulo: "Abrir", executar: () => { location.hash = "#/notificacoes"; } } });
      return;
    }
    avisarErro(erro);
    return;
  }
  window.dispatchEvent(new CustomEvent("entrada:contagem", { detail: Number(r.pendentes) || 0 }));
  redesenhar(chave, { itens: r.itens || [], pendentes: r.pendentes, config: r.config });
  const n = Number(r.recebidos) || 0;
  if (n > 0) {
    toast(`${n} arquivo(s) recebido(s). Confira em Ler boletos.`, "ok", {
      duracao: 8000, acao: { rotulo: "Abrir", executar: () => { location.hash = "#/ler"; } },
    });
  } else if (canal === "email") {
    toast(`Nenhum boleto novo (${Number(r.emails_verificados) || 0} e-mail(s) verificado(s)).`, "info", { duracao: 5000 });
  } else {
    toast("Nenhum arquivo novo no Telegram.", "info", { duracao: 5000 });
  }
}

export const acoes = {
  "entrada-verificar": verificar,
  "entrada-recarregar": () => atualizar(chave),
};

export const alteracoes = {
  /** Escolher o provedor só preenche o servidor e a porta (nada é salvo). */
  "entrada-provedor": (select) => {
    const p = PROVEDORES_IMAP.find((x) => x.chave === select.value);
    const form = select.form;
    if (!p || !form) return;
    form.elements.servidor.value = p.servidor;
    form.elements.porta.value = p.porta;
    if (!form.elements.pasta.value.trim()) form.elements.pasta.value = "INBOX";
    (form.elements.usuario.value ? form.elements.senha : form.elements.usuario).focus();
  },
  /** Ligar/desligar o e-mail salva o formulário inteiro (se falhar, a chave volta). */
  "entrada-email-ativo": async (campo) => {
    try {
      await salvarEmail(campo.form);
    } catch (erro) {
      if (!erro?.silencioso) throw erro; // eventos.js avisa e devolve a chave
      campo.checked = !campo.checked; // faltou preencher algo: o aviso já apareceu
    }
  },
  "entrada-telegram": async (campo) => {
    const r = await comAdmin(() => api.put("/api/entrada/config", { telegram: { ativo: campo.checked } }), DESCRICAO_SENHA);
    guardarConfig(r);
    toast(r.telegram?.ativo ? "Recebimento pelo Telegram ligado." : "Recebimento pelo Telegram desligado.", "ok");
  },
};

export const formularios = {
  "entrada-salvar-email": async (form) => {
    try {
      await salvarEmail(form);
    } catch (erro) {
      if (!erro?.silencioso) throw erro;
    }
  },
};

// Tela: Notificações — lembretes configuráveis (dia do vencimento, antes, vencidos), canais, agenda e histórico.
import { api } from "../api.js";
import { icone } from "../icons.js";
import { abrirModal, brl, copiar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../ui.js";

const MASCARA = "••••••••";
const CANAIS = ["windows", "telegram", "email"];
const NOMES_CANAIS = { windows: "Windows", telegram: "Telegram", email: "E-mail" };
const TIPOS_HISTORICO = { automatico: "Automático", manual: "Enviado agora", teste: "Teste",
  resumo: "Resumo da semana", resumo_manual: "Resumo enviado agora" };
const RESUMOS = [
  ["segunda", "Segunda-feira", "calendario", "O que vence na semana: boletos e Pix a pagar, vencidos, cheques a depositar, fechamentos das empresas e saldo do caixa."],
  ["sexta", "Sexta-feira", "check", "O que a semana movimentou: quanto foi pago em boletos, Pix e saídas do caixa, o que entrou, onde mais se gastou e o que ficou pendente."],
];
const DIAS_SEMANA = [["Seg", 0], ["Ter", 1], ["Qua", 2], ["Qui", 3], ["Sex", 4], ["Sáb", 5], ["Dom", 6]];
const NOMES_DIA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const PRESETS_EMAIL = {
  gmail: { servidor: "smtp.gmail.com", porta: 587, seguranca: "starttls" },
  outlook: { servidor: "smtp.office365.com", porta: 587, seguranca: "starttls" },
  yahoo: { servidor: "smtp.mail.yahoo.com", porta: 465, seguranca: "ssl" },
};
const PRESETS_HORARIOS = [
  ["1 vez", ["08:00"]],
  ["3 vezes", ["08:00", "12:00", "16:00"]],
  ["5 vezes", ["08:00", "10:00", "12:00", "14:00", "16:00"]],
];

let raiz = null;
let cfg = null;
let temporizadorSalvar = null;
let botTelegram = null; // dados do bot (usuário) para compartilhar o link com o escritório

export async function montar(el) {
  raiz = el;
  el.innerHTML = `<div class="notif-grade">${'<div class="card esqueleto" style="height:220px"></div>'.repeat(4)}</div>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  await carregar();
}

export function desmontar() {
  if (temporizadorSalvar) {
    clearTimeout(temporizadorSalvar);
    salvarAgora(true);
  }
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz = null;
}

async function carregar() {
  try {
    const [dados, inicializacao] = await Promise.all([
      api.get("/api/notificacoes"),
      api.get("/api/sistema/inicializacao").catch(() => ({ disponivel: false, ativo: false })),
    ]);
    if (!raiz) return;
    cfg = dados.config;
    renderizar(dados, inicializacao);
  } catch (erro) {
    if (raiz) {
      raiz.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
        <h3>Não foi possível carregar as notificações</h3><p>${esc(mensagemErro(erro))}</p></div>`;
    }
  }
}

// ------------------------------------------------------------------ renderização

const interruptor = (atributos, ligado, rotulo) =>
  `<label class="interruptor" title="${esc(rotulo)}"><input type="checkbox" ${atributos} ${ligado ? "checked" : ""} aria-label="${esc(rotulo)}"><span></span></label>`;

function tituloRegra(r) {
  if (r.tipo === "vencimento") return "No dia do vencimento";
  if (r.tipo === "vencidos") return "Depois de vencido";
  return "Antes do vencimento";
}

function htmlRegra(r, i) {
  const iconeRegra = r.tipo === "vencimento" ? "sino" : r.tipo === "vencidos" ? "alerta" : "calendario";
  let detalhe = "";
  if (r.tipo === "antes") {
    detalhe = `<div class="input-sufixo mini"><input type="number" class="input input-sm" min="1" max="60" value="${r.dias}"
      data-regra-dias data-i="${i}" aria-label="Dias antes"><span>dias antes</span></div>`;
  } else if (r.tipo === "vencidos") {
    detalhe = `<span class="sutil">lembrar por até</span><div class="input-sufixo mini"><input type="number" class="input input-sm" min="0" max="365"
      value="${r.dias}" data-regra-dias data-i="${i}" aria-label="Dias depois de vencido"><span>dias</span></div>
      <span class="sutil">(0 = até pagar)</span>`;
  } else {
    detalhe = `<span class="chip marca">${r.horarios.length} lembrete${r.horarios.length === 1 ? "" : "s"} no dia</span>`;
  }

  return `<div class="regra ${r.ativo ? "" : "desligada"}">
    <div class="regra-topo">
      ${interruptor(`data-regra-ativo data-i="${i}"`, r.ativo, "Ativar lembrete")}
      <div class="regra-titulo">${icone(iconeRegra, 17)}<strong>${tituloRegra(r)}</strong>${detalhe}</div>
      <button class="btn-icone perigo" data-remover-regra data-i="${i}" title="Remover lembrete">${icone("lixeira", 16)}</button>
    </div>
    <div class="regra-linha">
      <span class="regra-rotulo">Horários</span>
      <div class="horarios">
        ${r.horarios.map((h, j) => `<span class="chip-horario">${icone("relogio", 13)}${h}
          <button data-remover-horario="${j}" data-i="${i}" aria-label="Remover ${h}">×</button></span>`).join("")}
        <span class="novo-horario">
          <input type="time" class="input input-sm" data-novo-horario data-i="${i}" aria-label="Novo horário">
          <button class="btn btn-sm" data-adicionar-horario data-i="${i}">${icone("mais", 14)} Horário</button>
        </span>
      </div>
    </div>
    ${r.tipo === "vencimento" ? `<div class="regra-linha"><span class="regra-rotulo">Atalhos</span><div class="horarios">
      ${PRESETS_HORARIOS.map(([rotulo, horarios], p) => `<button class="btn btn-sm btn-fantasma" data-preset-horarios="${p}" data-i="${i}">
        ${rotulo}: ${horarios.map((h) => h.slice(0, 2) + "h").join(" · ")}</button>`).join("")}</div></div>` : ""}
    <div class="regra-linha">
      <span class="regra-rotulo">Enviar por</span>
      <div class="chips-situacao">
        ${CANAIS.map((c) => `<button class="chip-filtro ${r.canais.includes(c) ? "ativo" : ""} ${cfg[c].ativo ? "" : "canal-off"}"
          data-regra-canal="${c}" data-i="${i}" title="${cfg[c].ativo ? "" : "Canal desligado — ative-o no cartão abaixo"}">${NOMES_CANAIS[c]}</button>`).join("")}
      </div>
    </div>
  </div>`;
}

function htmlRegras() {
  const tem = (tipo) => cfg.regras.some((r) => r.tipo === tipo);
  return `${cfg.regras.map(htmlRegra).join("") || `<p class="sutil">Nenhum lembrete cadastrado.</p>`}
    <div class="linha-botoes">
      ${tem("vencimento") ? "" : `<button class="btn btn-sm" data-adicionar-regra="vencimento">${icone("mais", 14)} No dia do vencimento</button>`}
      <button class="btn btn-sm" data-adicionar-regra="antes">${icone("mais", 14)} Antes do vencimento</button>
      ${tem("vencidos") ? "" : `<button class="btn btn-sm" data-adicionar-regra="vencidos">${icone("mais", 14)} Depois de vencido</button>`}
    </div>`;
}

function htmlResumos() {
  return RESUMOS.map(([tipo, dia, iconeResumo, descricao]) => {
    const r = cfg.resumos[tipo];
    return `<div class="regra ${r.ativo ? "" : "desligada"}">
      <div class="regra-topo">
        ${interruptor(`data-resumo-ativo="${tipo}"`, r.ativo, `Ativar resumo de ${dia.toLowerCase()}`)}
        <div class="regra-titulo">${icone(iconeResumo, 17)}<strong>${dia}</strong>
          <span class="sutil">às</span>
          <input type="time" class="input input-sm" data-resumo-horario="${tipo}" value="${esc(r.horario)}" aria-label="Horário do resumo de ${dia}"></div>
        <div class="linha-botoes">
          <button class="btn btn-sm btn-fantasma" data-resumo-previa="${tipo}">${icone("olho", 14)} Ver como fica</button>
          <button class="btn btn-sm" data-resumo-enviar="${tipo}">${icone("sino", 14)} Enviar agora</button>
        </div>
      </div>
      <p class="sutil resumo-descricao">${esc(descricao)}${r.ultimo_envio ? ` Último envio: ${dataBR(r.ultimo_envio)}.` : ""}</p>
      <div class="regra-linha">
        <span class="regra-rotulo">Enviar por</span>
        <div class="chips-situacao">
          ${CANAIS.map((c) => `<button class="chip-filtro ${r.canais.includes(c) ? "ativo" : ""} ${cfg[c].ativo ? "" : "canal-off"}"
            data-resumo-canal="${c}" data-tipo="${tipo}" title="${cfg[c].ativo ? "" : "Canal desligado — ative-o no cartão abaixo"}">${NOMES_CANAIS[c]}</button>`).join("")}
        </div>
      </div>
    </div>`;
  }).join("");
}

function atualizarResumos() {
  const alvo = raiz?.querySelector("#resumos");
  if (alvo) alvo.innerHTML = htmlResumos();
}

function mostrarPrevia(tipo, previa) {
  abrirModal({
    titulo: `Resumo de ${tipo === "segunda" ? "segunda-feira" : "sexta-feira"} · como fica agora`,
    corpo: `<div class="resumo-previa">${previa.html}</div>`,
    rodape: `<button class="btn" data-fechar>Fechar</button>`,
  });
}

function rotuloDia(iso) {
  const dia = new Date(`${iso.slice(0, 10)}T12:00:00`);
  const hoje = new Date();
  hoje.setHours(12, 0, 0, 0);
  const diferenca = Math.round((dia - hoje) / 86400000);
  if (diferenca === 0) return "Hoje";
  if (diferenca === 1) return "Amanhã";
  return `${NOMES_DIA[(dia.getDay() + 6) % 7]}, ${dataBR(iso).slice(0, 5)}`;
}

function tituloAgenda(item) {
  if (item.tipo === "vencimento") return `Vence no dia${item.lembrete ? ` · lembrete ${item.lembrete}` : ""}`;
  if (item.tipo === "vencidos") return `Vencidos${item.lembrete ? ` · lembrete ${item.lembrete}` : ""}`;
  return `Vence em ${item.dias} dia${item.dias === 1 ? "" : "s"}${item.lembrete ? ` · lembrete ${item.lembrete}` : ""}`;
}

function htmlAgenda(agenda) {
  if (!cfg.ativo) return `<p class="sutil">Os avisos estão desligados.</p>`;
  if (!agenda.length) return `<p class="sutil">Nenhum lembrete previsto para os próximos 7 dias com os boletos pendentes atuais.</p>`;
  let diaAtual = "";
  return `<ul class="agenda">${agenda.map((item) => {
    const dia = item.quando.slice(0, 10);
    const cabecalho = dia !== diaAtual ? `<li class="agenda-dia">${rotuloDia(item.quando)}</li>` : "";
    diaAtual = dia;
    const nomes = item.boletos.map((b) => esc(b.beneficiario)).join(", ") + (item.quantidade > item.boletos.length ? "…" : "");
    const total = item.boletos.reduce((s, b) => s + b.valor, 0);
    return `${cabecalho}<li class="agenda-item">
      <span class="agenda-hora">${item.quando.slice(11, 16)}</span>
      <div class="info"><strong>${tituloAgenda(item)}</strong><span class="sutil">${item.quantidade} boleto(s): ${nomes} · ${brl(total)}</span></div>
      <span class="agenda-canais">${item.canais.map((c) => `<span class="chip" title="${NOMES_CANAIS[c]}">${icone({ windows: "monitor", telegram: "telegram", email: "email" }[c], 12)}</span>`).join("")}</span>
    </li>`;
  }).join("")}</ul>`;
}

function renderizar(dados, inicializacao) {
  raiz.innerHTML = `
  <section class="notif-grade">
    <div class="card">
      <div class="card-cabecalho"><h3>${icone("sino", 18)} Avisos de vencimento</h3>${interruptor('id="n-ativo"', cfg.ativo, "Ativar avisos")}</div>
      <div class="card-corpo notif-corpo">
        <div class="campo"><label>Avisar nos dias da semana</label>
          <div class="chips-situacao" id="n-dias-semana">
            ${DIAS_SEMANA.map(([rotulo, valor]) => `<button class="chip-filtro ${cfg.dias_semana.includes(valor) ? "ativo" : ""}" data-dia-semana="${valor}">${rotulo}</button>`).join("")}
          </div></div>
        <p class="sutil">O sistema confere os lembretes a cada minuto. Cada boleto é avisado uma vez em cada horário, e os avisos
          param quando o boleto é marcado como pago (inclusive pelo botão <strong>Já paguei</strong> da notificação).
          Se o computador estava desligado num horário, só o lembrete mais recente é enviado.
          ${dados.automaticas ? "" : "<strong>O agendador automático está desligado neste servidor (LEITOR_NOTIFICACOES_AUTOMATICAS=0).</strong>"}</p>
        <div class="linha-botoes">
          <button class="btn" data-acao="enviar-agora">${icone("sino", 16)} Enviar avisos agora</button>
          <span class="status-salvo" id="status-salvo"></span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-cabecalho"><h3>${icone("calendario", 18)} Próximos lembretes</h3><span class="sutil">7 dias</span></div>
      <div class="card-corpo" id="agenda">${htmlAgenda(dados.agenda)}</div>
    </div>

    <div class="card col-inteira">
      <div class="card-cabecalho"><h3>${icone("relogio", 18)} Lembretes</h3>
        <span class="sutil">Configure quando e em quais horários avisar</span></div>
      <div class="card-corpo notif-corpo" id="regras">${htmlRegras()}</div>
    </div>

    <div class="card col-inteira">
      <div class="card-cabecalho"><h3>${icone("grafico", 18)} Resumos da semana</h3>
        <span class="sutil">Uma mensagem na segunda e outra na sexta</span></div>
      <div class="card-corpo notif-corpo" id="resumos">${htmlResumos()}</div>
    </div>

    <div class="card canal">
      <div class="card-cabecalho"><h3>${icone("monitor", 18)} Notificação do Windows</h3>${interruptor('data-canal-ativo="windows"', cfg.windows.ativo, "Ativar Windows")}</div>
      <div class="card-corpo notif-corpo">
        <p>Aparece no canto da tela, mesmo com o navegador fechado, com os botões <em>Abrir boletos</em> e <em>Já paguei</em>.</p>
        ${inicializacao.disponivel ? `<label class="check destaque-check">
            <input type="checkbox" id="n-iniciar" ${inicializacao.ativo ? "checked" : ""}>
            <span><strong>Iniciar o Fin Pro junto com o Windows</strong><br>
            <span class="sutil">Roda em segundo plano, sem janela, para os lembretes chegarem mesmo sem abrir o sistema.</span></span></label>`
          : `<p class="sutil">Disponível apenas no Windows.</p>`}
        <div class="linha-botoes"><button class="btn" data-testar="windows">${icone("sino", 16)} Enviar teste</button></div>
      </div>
    </div>

    <div class="card canal">
      <div class="card-cabecalho"><h3>${icone("telegram", 18)} Telegram (celular)</h3>${interruptor('data-canal-ativo="telegram"', cfg.telegram.ativo, "Ativar Telegram")}</div>
      <div class="card-corpo notif-corpo">
        <ol class="passos-simples">
          <li>No Telegram, abra o <strong>@BotFather</strong>, envie <code>/newbot</code> e copie o <em>token</em> do bot.</li>
          <li>Cada pessoa do escritório abre o bot e toca em <strong>Iniciar</strong> (<code>/start</code>) — ou adicione o bot ao <strong>grupo do escritório</strong>.</li>
          <li>Clique em <em>Procurar pessoas e grupos</em> e marque quem vai receber.</li>
        </ol>
        <div class="campo"><label for="t-token">Token do bot</label>
          <input id="t-token" class="input mono" type="password" autocomplete="off" value="${esc(cfg.telegram.token)}" placeholder="123456789:AA…"></div>
        <div id="t-bot">${htmlBotTelegram()}</div>
        <div class="tg-cabecalho"><strong>Quem recebe</strong><span class="sutil" id="t-contagem">${textoContagemTelegram()}</span></div>
        <ul class="tg-lista" id="t-destinatarios">${htmlDestinatarios()}</ul>
        <div class="linha-botoes">
          <button class="btn btn-primario" data-acao="procurar-telegram">${icone("busca", 16)} Procurar pessoas e grupos</button>
          <button class="btn" data-testar="telegram">${icone("telegram", 16)} Enviar teste para todos</button>
        </div>
        <details class="rede-ajuda"><summary>Adicionar pelo número do chat</summary>
          <div class="tg-manual">
            <input id="tg-novo-nome" class="input" maxlength="60" placeholder="Nome (ex.: Maria – Financeiro)">
            <input id="tg-novo-chat" class="input mono" placeholder="Chat ID (ex.: 123456789)">
            <button class="btn" data-acao="adicionar-chat">${icone("mais", 16)} Adicionar</button>
          </div>
        </details>
      </div>
    </div>

    <div class="card canal col-inteira">
      <div class="card-cabecalho"><h3>${icone("email", 18)} E-mail</h3>${interruptor('data-canal-ativo="email"', cfg.email.ativo, "Ativar e-mail")}</div>
      <div class="card-corpo notif-corpo">
        <div class="grade-campos grade-email">
          <div class="campo"><label for="e-preset">Provedor</label>
            <select id="e-preset" class="input"><option value="">Escolher para preencher…</option>
              <option value="gmail">Gmail</option><option value="outlook">Outlook / Hotmail / Microsoft 365</option>
              <option value="yahoo">Yahoo</option></select></div>
          <div class="campo"><label for="e-servidor">Servidor SMTP</label><input id="e-servidor" class="input" value="${esc(cfg.email.servidor)}" placeholder="smtp.gmail.com"></div>
          <div class="campo"><label for="e-porta">Porta</label><input id="e-porta" type="number" class="input" value="${cfg.email.porta}"></div>
          <div class="campo"><label for="e-seguranca">Segurança</label>
            <select id="e-seguranca" class="input">${[["starttls", "STARTTLS (587)"], ["ssl", "SSL/TLS (465)"], ["nenhuma", "Nenhuma"]]
              .map(([v, r]) => `<option value="${v}" ${cfg.email.seguranca === v ? "selected" : ""}>${r}</option>`).join("")}</select></div>
          <div class="campo"><label for="e-usuario">Usuário</label><input id="e-usuario" class="input" autocomplete="off" value="${esc(cfg.email.usuario)}" placeholder="voce@gmail.com"></div>
          <div class="campo"><label for="e-senha">Senha de app</label><input id="e-senha" type="password" class="input" autocomplete="new-password" value="${esc(cfg.email.senha)}"></div>
          <div class="campo"><label for="e-remetente">Remetente</label><input id="e-remetente" class="input" value="${esc(cfg.email.remetente)}" placeholder="Igual ao usuário"></div>
          <div class="campo"><label for="e-destinatarios">Enviar para (separe por vírgula)</label>
            <input id="e-destinatarios" class="input" value="${esc(cfg.email.destinatarios)}" placeholder="financeiro@empresa.com.br"></div>
        </div>
        <p class="sutil">Gmail e Outlook exigem uma <strong>senha de app</strong> (criada na segurança da conta), não a senha normal.
          A senha fica guardada somente neste computador.</p>
        <div class="linha-botoes"><button class="btn" data-testar="email">${icone("email", 16)} Enviar teste</button></div>
      </div>
    </div>

    <div class="card col-inteira">
      <div class="card-cabecalho"><h3>${icone("relogio", 18)} Histórico de avisos</h3></div>
      <div class="tabela-wrap">
        ${dados.historico.length ? `<table class="tabela"><thead><tr><th>Quando</th><th>Tipo</th><th>Aviso</th><th>Canais</th></tr></thead><tbody>
          ${dados.historico.map((h) => `<tr>
            <td data-rotulo="Quando">${dataHoraBR(h.quando)}</td>
            <td data-rotulo="Tipo">${TIPOS_HISTORICO[h.tipo] || esc(h.tipo)}</td>
            <td data-rotulo="Aviso"><strong>${esc(h.titulo)}</strong>
              ${h.boletos?.length ? `<span class="sutil" style="display:block">${h.boletos.slice(0, 3).map((b) => esc(b.beneficiario)).join(", ")}${h.boletos.length > 3 ? "…" : ""}</span>` : ""}</td>
            <td data-rotulo="Canais">${Object.entries(h.canais).map(([canal, r]) => `<span class="chip ${r === "ok" ? "ok" : "erro"}" title="${esc(r)}">${NOMES_CANAIS[canal] || esc(canal)} ${r === "ok" ? "✓" : "✕"}</span>`).join(" ")}</td>
          </tr>`).join("")}</tbody></table>`
          : `<div class="vazio" style="padding:28px"><p>Nenhum aviso enviado ainda.</p></div>`}
      </div>
    </div>
  </section>`;
}

// ------------------------------------------------------------------ Telegram: pessoas e grupos

const NOMES_TIPO_CHAT = { privado: "Pessoa", grupo: "Grupo", canal: "Canal" };

function htmlBotTelegram() {
  if (!botTelegram?.usuario) return "";
  return `<div class="alerta info tg-bot">${icone("telegram", 16)}
    <span>Link do bot para enviar às pessoas do escritório: <strong class="mono">t.me/${esc(botTelegram.usuario)}</strong></span>
    <button class="btn btn-sm" data-acao="copiar-link-bot">${icone("copiar", 14)} Copiar link</button></div>`;
}

function textoContagemTelegram() {
  const lista = cfg.telegram.destinatarios || [];
  if (!lista.length) return "";
  const ativos = lista.filter((d) => d.ativo).length;
  return `${ativos} de ${lista.length} recebendo`;
}

function htmlDestinatarios() {
  const lista = cfg.telegram.destinatarios || [];
  if (!lista.length) {
    return `<li class="tg-vazio sutil">Ninguém adicionado ainda. Depois que cada pessoa enviar <code>/start</code> ao bot,
      clique em <strong>Procurar pessoas e grupos</strong>.</li>`;
  }
  return lista.map((d, i) => `<li class="tg-item ${d.ativo ? "" : "desligado"}">
      ${interruptor(`data-tg-ativo="${i}"`, d.ativo, `Enviar para ${d.nome}`)}
      <span class="tg-icone">${icone(d.tipo === "privado" ? "pessoa" : "grupo", 17)}</span>
      <div class="tg-info">
        <input class="input input-sm" data-tg-nome="${i}" value="${esc(d.nome)}" maxlength="60" aria-label="Nome de quem recebe">
        <span class="sutil mono">${NOMES_TIPO_CHAT[d.tipo] || "Pessoa"} · ${esc(d.chat_id)}</span>
      </div>
      <button class="btn btn-sm" data-tg-testar="${i}" title="Enviar uma mensagem de teste só para ${esc(d.nome)}">${icone("telegram", 14)} Testar</button>
      <button class="btn-icone perigo" data-tg-remover="${i}" title="Remover ${esc(d.nome)}">${icone("lixeira", 16)}</button>
    </li>`).join("");
}

function atualizarTelegram() {
  if (!raiz) return;
  raiz.querySelector("#t-destinatarios").innerHTML = htmlDestinatarios();
  raiz.querySelector("#t-contagem").textContent = textoContagemTelegram();
  raiz.querySelector("#t-bot").innerHTML = htmlBotTelegram();
}

function adicionarDestinatarios(lista) {
  const atuais = cfg.telegram.destinatarios || [];
  const existentes = new Set(atuais.map((d) => d.chat_id));
  const novos = lista.filter((c) => !existentes.has(c.chat_id))
    .map((c) => ({ chat_id: c.chat_id, nome: c.nome, tipo: c.tipo || "privado", ativo: true }));
  if (!novos.length) {
    toast("Já está na lista de quem recebe.", "info");
    return;
  }
  cfg.telegram.destinatarios = [...atuais, ...novos];
  cfg.telegram.ativo = true;
  const chave = raiz.querySelector('[data-canal-ativo="telegram"]');
  if (chave) chave.checked = true;
  atualizarTelegram();
  atualizarRegras();
  agendarSalvar();
  toast(`${novos.length === 1 ? `${novos[0].nome} vai` : `${novos.length} destinatários vão`} receber as notificações. Use "Testar" para conferir.`,
    "ok", { duracao: 6000 });
}

function escolherChatsTelegram({ bot, chats }) {
  const existentes = new Set((cfg.telegram.destinatarios || []).map((d) => d.chat_id));
  const novos = chats.filter((c) => !existentes.has(c.chat_id));
  const link = bot?.usuario ? `https://t.me/${bot.usuario}` : "";
  const { el, fechar } = abrirModal({
    titulo: "Pessoas e grupos que falaram com o bot",
    tamanho: "lg",
    corpo: novos.length
      ? `<p class="sutil" style="margin-bottom:10px">Marque quem vai receber as notificações de vencimento.</p>
        <ul class="tg-lista tg-escolha">${novos.map((c, i) => `<li class="tg-item">
          <label class="check"><input type="checkbox" data-escolha="${i}" checked>
            <span><strong>${esc(c.nome)}</strong><br>
              <span class="sutil">${NOMES_TIPO_CHAT[c.tipo] || "Pessoa"}${c.usuario ? ` · @${esc(c.usuario)}` : ""} · ${esc(c.chat_id)}</span></span></label>
        </li>`).join("")}</ul>`
      : `<div class="vazio" style="padding:18px">
          <h3>${chats.length ? "Todos já estão na lista" : "Ninguém encontrado ainda"}</h3>
          <p>Peça para cada pessoa abrir ${link ? `<strong class="mono">${esc(link)}</strong>` : "o bot"} no Telegram e tocar em
            <strong>Iniciar</strong>. Para um grupo, adicione o bot ao grupo e envie uma mensagem lá. Depois clique em procurar de novo.</p>
          <p class="sutil">O Telegram só mostra quem falou com o bot nas últimas 24 horas.</p>
        </div>`,
    rodape: novos.length
      ? `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
         <button class="btn btn-primario" data-adicionar>${icone("mais", 16)} Adicionar selecionados</button>`
      : `${link ? `<button class="btn" data-copiar-link>${icone("copiar", 16)} Copiar link do bot</button>` : ""}
         <button class="btn btn-primario" data-fechar>Entendi</button>`,
  });
  el.querySelector("[data-copiar-link]")?.addEventListener("click", () => copiar(link, "Link do bot copiado"));
  el.querySelector("[data-adicionar]")?.addEventListener("click", () => {
    const escolhidos = novos.filter((_, i) => el.querySelector(`[data-escolha="${i}"]`).checked);
    fechar(true);
    if (escolhidos.length) adicionarDestinatarios(escolhidos);
  });
}

function atualizarRegras() {
  const alvo = raiz?.querySelector("#regras");
  if (alvo) alvo.innerHTML = htmlRegras();
}

// ------------------------------------------------------------------ salvar

function coletar() {
  const valor = (seletor) => raiz.querySelector(seletor).value;
  const marcado = (seletor) => raiz.querySelector(seletor).checked;
  return {
    ativo: marcado("#n-ativo"),
    dias_semana: cfg.dias_semana,
    regras: cfg.regras,
    resumos: Object.fromEntries(RESUMOS.map(([tipo]) => [tipo, {
      ativo: cfg.resumos[tipo].ativo, horario: cfg.resumos[tipo].horario, canais: cfg.resumos[tipo].canais }])),
    windows: { ativo: marcado('[data-canal-ativo="windows"]') },
    telegram: { ativo: marcado('[data-canal-ativo="telegram"]'), token: valor("#t-token"), destinatarios: cfg.telegram.destinatarios || [] },
    email: {
      ativo: marcado('[data-canal-ativo="email"]'),
      servidor: valor("#e-servidor"),
      porta: Number(valor("#e-porta") || 587),
      seguranca: valor("#e-seguranca"),
      usuario: valor("#e-usuario"),
      senha: valor("#e-senha"),
      remetente: valor("#e-remetente"),
      destinatarios: valor("#e-destinatarios"),
    },
  };
}

function indicar(texto, classe = "") {
  const el = raiz?.querySelector("#status-salvo");
  if (el) {
    el.className = `status-salvo ${classe}`;
    el.textContent = texto;
  }
}

async function salvarAgora(silencioso = false) {
  clearTimeout(temporizadorSalvar);
  temporizadorSalvar = null;
  if (!raiz) return;
  indicar("Salvando…");
  const salvo = await api.put("/api/notificacoes/config", coletar());
  cfg.regras = salvo.regras;
  cfg.resumos = salvo.resumos;
  cfg.dias_semana = salvo.dias_semana;
  cfg.telegram.destinatarios = salvo.telegram.destinatarios;
  indicar("✓ Alterações salvas", "ok");
  window.dispatchEvent(new Event("avisos:atualizar"));
  const dados = await api.get("/api/notificacoes");
  const agenda = raiz?.querySelector("#agenda");
  if (agenda) agenda.innerHTML = htmlAgenda(dados.agenda);
  if (!silencioso) toast("Configurações de notificação salvas", "ok");
}

function agendarSalvar() {
  clearTimeout(temporizadorSalvar);
  indicar("Alterações pendentes…");
  temporizadorSalvar = setTimeout(async () => {
    try {
      await salvarAgora(true);
    } catch (erro) {
      indicar("Não salvo", "erro");
      toast(mensagemErro(erro), "erro", { duracao: 7000 });
    }
  }, 600);
}

// ------------------------------------------------------------------ eventos

async function comBotao(botao, tarefa) {
  const original = botao.innerHTML;
  botao.disabled = true;
  botao.innerHTML = `<span class="spinner"></span> Aguarde…`;
  try {
    await tarefa();
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  } finally {
    if (botao.isConnected) {
      botao.disabled = false;
      botao.innerHTML = original;
    }
  }
}

function informarResultado(resultado) {
  const falhas = Object.entries(resultado.canais || {}).filter(([, r]) => r !== "ok");
  falhas.forEach(([canal, r]) => toast(`${NOMES_CANAIS[canal]}: ${r.replace(/^erro:\s*/, "")}`, "erro", { duracao: 9000 }));
  return falhas.length === 0;
}

function regraDoEvento(alvo) {
  return cfg.regras[Number(alvo.dataset.i)];
}

function novaRegra(tipo) {
  const canaisAtivos = CANAIS.filter((c) => cfg[c].ativo);
  const base = { tipo, canais: canaisAtivos.length ? canaisAtivos : ["windows"], ativo: true };
  if (tipo === "vencimento") return { ...base, dias: 0, horarios: ["08:00", "12:00", "16:00"] };
  if (tipo === "vencidos") return { ...base, dias: 30, horarios: ["09:00"] };
  const usados = cfg.regras.filter((r) => r.tipo === "antes").map((r) => r.dias);
  const dias = [1, 2, 3, 5, 7, 10, 15].find((d) => !usados.includes(d)) || 2;
  return { ...base, dias, horarios: ["09:00"] };
}

async function aoClicar(e) {
  const alvo = e.target.closest("button");
  if (!alvo || !raiz?.contains(alvo)) return;
  const d = alvo.dataset;

  if (d.diaSemana !== undefined) {
    const valor = Number(d.diaSemana);
    const dias = new Set(cfg.dias_semana);
    if (dias.has(valor)) dias.delete(valor); else dias.add(valor);
    if (!dias.size) { toast("Escolha pelo menos um dia da semana.", "aviso"); return; }
    cfg.dias_semana = [...dias].sort();
    alvo.classList.toggle("ativo", dias.has(valor));
    agendarSalvar();
  } else if (d.adicionarRegra) {
    cfg.regras.push(novaRegra(d.adicionarRegra));
    atualizarRegras();
    agendarSalvar();
  } else if (d.removerRegra !== undefined) {
    const indice = Number(d.i);
    const [removida] = cfg.regras.splice(indice, 1);
    atualizarRegras();
    agendarSalvar();
    toast(`Lembrete "${tituloRegra(removida)}" removido`, "info", {
      acao: { rotulo: "Desfazer", executar: () => { cfg.regras.splice(indice, 0, removida); atualizarRegras(); agendarSalvar(); } },
    });
  } else if (d.removerHorario !== undefined) {
    const regra = regraDoEvento(alvo);
    if (regra.horarios.length === 1) { toast("O lembrete precisa de pelo menos um horário. Para parar, desligue-o.", "aviso"); return; }
    regra.horarios.splice(Number(d.removerHorario), 1);
    atualizarRegras();
    agendarSalvar();
  } else if (d.adicionarHorario !== undefined) {
    const regra = regraDoEvento(alvo);
    const campo = alvo.parentElement.querySelector("[data-novo-horario]");
    const horario = campo.value;
    if (!/^\d{2}:\d{2}$/.test(horario)) { toast("Escolha um horário antes de adicionar.", "aviso"); campo.focus(); return; }
    if (regra.horarios.includes(horario)) { toast("Esse horário já está no lembrete.", "info"); return; }
    if (regra.horarios.length >= 12) { toast("No máximo 12 horários por lembrete.", "aviso"); return; }
    regra.horarios = [...regra.horarios, horario].sort();
    atualizarRegras();
    agendarSalvar();
  } else if (d.presetHorarios !== undefined) {
    regraDoEvento(alvo).horarios = [...PRESETS_HORARIOS[Number(d.presetHorarios)][1]];
    atualizarRegras();
    agendarSalvar();
  } else if (d.regraCanal) {
    const regra = regraDoEvento(alvo);
    regra.canais = regra.canais.includes(d.regraCanal) ? regra.canais.filter((c) => c !== d.regraCanal) : [...regra.canais, d.regraCanal];
    if (!regra.canais.length) toast("Sem nenhum canal, este lembrete não será enviado.", "aviso");
    atualizarRegras();
    agendarSalvar();
  } else if (d.resumoCanal) {
    const r = cfg.resumos[d.tipo];
    r.canais = r.canais.includes(d.resumoCanal) ? r.canais.filter((c) => c !== d.resumoCanal) : [...r.canais, d.resumoCanal];
    if (!r.canais.length) toast("Sem nenhum canal, este resumo não será enviado.", "aviso");
    atualizarResumos();
    agendarSalvar();
  } else if (d.resumoPrevia) {
    await comBotao(alvo, async () => mostrarPrevia(d.resumoPrevia, await api.get(`/api/notificacoes/resumo/${d.resumoPrevia}`)));
  } else if (d.resumoEnviar) {
    await comBotao(alvo, async () => {
      await salvarAgora(true);
      const resultado = await api.post(`/api/notificacoes/resumo/${d.resumoEnviar}/enviar`);
      if (resultado.motivo) toast(resultado.motivo, "info", { duracao: 6000 });
      else if (informarResultado(resultado)) toast(`Resumo enviado: ${resultado.titulo}`, "ok");
      await carregar();
    });
  } else if (d.testar) {
    await comBotao(alvo, async () => {
      await salvarAgora(true);
      const resultado = await api.post("/api/notificacoes/testar", { canal: d.testar });
      if (informarResultado(resultado)) toast(`Teste enviado pelo ${NOMES_CANAIS[d.testar]}`, "ok");
      await carregar();
    });
  } else if (d.acao === "enviar-agora") {
    await comBotao(alvo, async () => {
      await salvarAgora(true);
      const resultado = await api.post("/api/notificacoes/enviar-agora");
      if (resultado.motivo) toast(resultado.motivo, "info", { duracao: 6000 });
      else if (informarResultado(resultado)) toast(`Aviso enviado: ${resultado.titulo}`, "ok");
      await carregar();
    });
  } else if (d.acao === "procurar-telegram") {
    const token = raiz.querySelector("#t-token").value.trim();
    if (!token) {
      toast("Cole primeiro o token do bot (passo 1).", "aviso");
      raiz.querySelector("#t-token").focus();
      return;
    }
    await comBotao(alvo, async () => {
      await salvarAgora(true);
      const resposta = await api.post("/api/notificacoes/telegram/detectar", { token: token === MASCARA ? null : token });
      botTelegram = resposta.bot;
      atualizarTelegram();
      escolherChatsTelegram(resposta);
    });
  } else if (d.acao === "copiar-link-bot" && botTelegram?.usuario) {
    copiar(`https://t.me/${botTelegram.usuario}`, "Link do bot copiado");
  } else if (d.acao === "adicionar-chat") {
    const campoChat = raiz.querySelector("#tg-novo-chat");
    const campoNome = raiz.querySelector("#tg-novo-nome");
    const chat = campoChat.value.trim();
    if (!/^-?\d{1,20}$/.test(chat)) {
      toast("Chat ID inválido: use só números (grupos começam com -).", "erro");
      campoChat.focus();
      return;
    }
    adicionarDestinatarios([{ chat_id: chat, nome: campoNome.value.trim() || "Sem nome", tipo: chat.startsWith("-") ? "grupo" : "privado" }]);
    campoChat.value = "";
    campoNome.value = "";
  } else if (d.tgTestar !== undefined) {
    const destinatario = cfg.telegram.destinatarios[Number(d.tgTestar)];
    if (!destinatario) return;
    await comBotao(alvo, async () => {
      await salvarAgora(true);
      await api.post("/api/notificacoes/telegram/testar", { chat_id: destinatario.chat_id });
      toast(`Teste enviado para ${destinatario.nome}`, "ok");
    });
  } else if (d.tgRemover !== undefined) {
    const indice = Number(d.tgRemover);
    const removido = cfg.telegram.destinatarios[indice];
    if (!removido) return;
    cfg.telegram.destinatarios = cfg.telegram.destinatarios.filter((_, i) => i !== indice);
    atualizarTelegram();
    agendarSalvar();
    toast(`${removido.nome} não vai mais receber as notificações`, "info", {
      acao: { rotulo: "Desfazer", executar: () => adicionarDestinatarios([removido]) },
    });
  }
}

async function aoAlterar(e) {
  const alvo = e.target;
  if (alvo.matches("[data-resumo-ativo]")) {
    cfg.resumos[alvo.dataset.resumoAtivo].ativo = alvo.checked;
    atualizarResumos();
    agendarSalvar();
  } else if (alvo.matches("[data-resumo-horario]")) {
    if (!/^\d{2}:\d{2}$/.test(alvo.value)) return;
    cfg.resumos[alvo.dataset.resumoHorario].horario = alvo.value;
    agendarSalvar();
  } else if (alvo.matches("[data-regra-ativo]")) {
    regraDoEvento(alvo).ativo = alvo.checked;
    atualizarRegras();
    agendarSalvar();
  } else if (alvo.matches("[data-regra-dias]")) {
    const regra = regraDoEvento(alvo);
    const minimo = regra.tipo === "antes" ? 1 : 0;
    const maximo = regra.tipo === "antes" ? 60 : 365;
    regra.dias = Math.min(maximo, Math.max(minimo, Number(alvo.value) || minimo));
    alvo.value = regra.dias;
    agendarSalvar();
  } else if (alvo.id === "e-preset" && PRESETS_EMAIL[alvo.value]) {
    const p = PRESETS_EMAIL[alvo.value];
    raiz.querySelector("#e-servidor").value = p.servidor;
    raiz.querySelector("#e-porta").value = p.porta;
    raiz.querySelector("#e-seguranca").value = p.seguranca;
    agendarSalvar();
  } else if (alvo.id === "n-iniciar") {
    const ativo = alvo.checked;
    try {
      await api.post("/api/sistema/inicializacao", { ativo });
      toast(ativo ? "O Fin Pro vai iniciar junto com o Windows." : "Inicialização automática desativada.", "ok");
    } catch (erro) {
      alvo.checked = !ativo;
      toast(mensagemErro(erro), "erro");
    }
  } else if (alvo.matches("[data-canal-ativo]")) {
    cfg[alvo.dataset.canalAtivo].ativo = alvo.checked;
    atualizarRegras();
    atualizarResumos();
    agendarSalvar();
  } else if (alvo.matches("[data-tg-ativo]")) {
    const destinatario = cfg.telegram.destinatarios[Number(alvo.dataset.tgAtivo)];
    if (destinatario) destinatario.ativo = alvo.checked;
    atualizarTelegram();
    agendarSalvar();
  } else if (alvo.matches("[data-tg-nome]")) {
    const destinatario = cfg.telegram.destinatarios[Number(alvo.dataset.tgNome)];
    if (destinatario) destinatario.nome = alvo.value.replace(/\s+/g, " ").trim().slice(0, 60) || "Sem nome";
    agendarSalvar();
  } else if (alvo.matches("#n-ativo, #t-token, [id^='e-']")) {
    if (alvo.id === "n-ativo") cfg.ativo = alvo.checked;
    agendarSalvar();
  }
}

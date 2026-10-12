// Configurações · Backup total fora do computador: dados, comprovantes, configurações, código-fonte e versões.
// Fazer backup agora, gerar o pacote .zip e verificar: só no computador onde o Fin Pro está instalado (403 "somente_local"
// de fora). Pasta, horário e pacotes: no computador e com a senha de administrador. De um celular ou na VPS, o cartão
// mostra só a situação (o servidor nem manda o caminho das pastas).
import { api } from "../../api.js";
import { pode } from "../../estado.js";
import { icone } from "../../icons.js";
import { confirmar, dataHoraBR, esc, toast } from "../../ui.js";
import { avisarErro, comAdmin } from "./eventos.js";
import { htmlTravaAdmin, podeAdministrar } from "./importacao.js";
import { alertaErro, atualizar, buscar, carregarAcesso, carregarAdmin, redesenhar, tela } from "./tela.js";

export const chave = "backup";

/** Rótulo e cor do chip pela situação (as mesmas palavras do menu lateral). */
export const SITUACAO_BACKUP = {
  ok: ["Em dia", "ok"], aguardando: ["Aguardando o primeiro backup", "info"], atrasado: ["Atrasado", "erro"],
  erro: ["Falhou", "erro"], desligado: ["Desligado", "aviso"],
};

const DESCRICAO_SENHA = "Digite a senha de administrador para configurar o backup.";
const ESPERA_ANDAMENTO = 8000; // com um backup rodando (ex.: o automático), confere de novo a cada 8 s
let relogio = null;

/** GET /api/backup (sempre 200), a senha de administrador e quem entrou (para saber se pode configurar). */
export async function carregar() {
  const [b] = await Promise.all([buscar("/api/backup"), carregarAdmin(), carregarAcesso()]);
  return b;
}

/** Avisa o menu lateral (situação do backup) para se atualizar. */
export const carregarStatusLateral = () => window.dispatchEvent(new Event("status:atualizar"));

export function iniciar() {
  parar();
  relogio = setInterval(async () => {
    if (document.hidden || !tela.dados[chave]?.executando) return;
    await atualizar(chave);
    if (!tela.dados[chave]?.executando) carregarStatusLateral();
  }, ESPERA_ANDAMENTO);
}

export function parar() {
  if (relogio) clearInterval(relogio);
  relogio = null;
}

// ------------------------------------------------------------------ desenho

const alerta = (tipo, texto) => `<div class="alerta ${tipo}">${icone(tipo === "info" ? "info" : "alerta", 16)}<div>${texto}</div></div>`;
const plural = (n, um, varios) => `${Number(n) || 0} ${Number(n) === 1 ? um : varios}`;

const parte = (ok, texto, falta = "") =>
  `<li class="${ok ? "ok" : "falta"}">${icone(ok ? "check" : "alerta", 16)}<span>${texto}${!ok && falta ? ` — ${esc(falta)}` : ""}</span></li>`;

function htmlPartes(b) {
  const comCodigo = Boolean(b.com_codigo);
  const problema = (nome) => (b.problemas || []).some((p) => p.nome === nome); // a conferência achou falta disso
  const semCodigo = problema("Código-fonte");
  const semHistorico = (b.ultimo?.ok && b.ultimo.historico_de_versoes === false) || problema("Histórico de versões");
  const pacoteLigado = b.pacote !== "nunca";
  const quando = b.pacote === "mensal" ? "todo mês" : "toda semana";
  return `<ul class="backup-partes">
    ${parte(true, `Bancos de dados e planilhas — uma cópia por dia, guarda ${esc(b.manter_dias ?? 30)} dias`)}
    ${parte(true, "Boletos, comprovantes e fotos — só o que é novo ou mudou")}
    ${parte(true, "Todas as configurações e o .env")}
    ${parte(comCodigo && !semCodigo, "Código-fonte do sistema", comCodigo ? "faltando no backup (veja a conferência)" : "fora do backup")}
    ${parte(comCodigo && !semHistorico, "Histórico de versões (finpro.bundle)", comCodigo ? "não está no backup" : "fora do backup")}
    ${parte(pacoteLigado, pacoteLigado ? `Pacote completo (.zip) — ${quando} · guarda os últimos ${esc(b.manter_pacotes ?? 4)}`
      : "Pacote completo (.zip)", "desligado")}
  </ul>`;
}

function htmlUltimo(b) {
  const u = b.ultimo;
  const partes = [];
  if (b.ultimo_sucesso) {
    const detalhes = u?.ok
      ? ` · ${plural(u.itens, "arquivo", "arquivos")}, ${esc(u.tamanho_legivel)} · ${plural((Number(u.arquivos_copiados) || 0) + (Number(u.codigo_copiados) || 0), "novo ou alterado", "novos ou alterados")}`
      : "";
    partes.push(`<p>Último backup: <strong>${esc(dataHoraBR(b.ultimo_sucesso))}</strong>${detalhes}</p>`);
  } else if (b.ativo) {
    partes.push(`<p class="sutil">Nenhum backup feito ainda. O primeiro sai depois das ${esc(b.horario)} (ou use Fazer backup agora).</p>`);
  } else {
    partes.push(`<p class="sutil">Nenhum backup fora do computador ainda. ${b.local ? "Escolha a pasta abaixo, ligue o backup automático e salve." : ""}</p>`);
  }
  if (b.destino) partes.push(`<div class="caminho">${esc(b.destino)}</div>`);
  if (b.executando) partes.push(alerta("info", "Um backup está em andamento… Os botões voltam quando ele terminar."));
  if (u && u.ok === false) partes.push(alerta("erro", `O último backup falhou (${esc(dataHoraBR(u.quando))}): ${esc(u.erro)}`));
  if (b.situacao === "atrasado" && !(u && u.ok === false)) {
    partes.push(alerta("erro", b.dias_sem_backup
      ? `Backup atrasado: ${plural(b.dias_sem_backup, "dia", "dias")} sem cópia. ${b.local ? "Confira se a pasta continua acessível e clique em Fazer backup agora." : ""}`
      : "Backup atrasado: a pasta do backup não está acessível (pen drive ou HD externo desconectado?) ou o backup não roda há vários dias."));
  }
  return partes.join("");
}

function htmlConferencia(b) {
  const v = b.verificacao;
  if (b.verificado === true && v) {
    return `<p class="backup-conferido">${icone("check", 16)}<span>Conferido em ${esc(dataHoraBR(v.quando))}
      (${v.completa ? "arquivo por arquivo" : "conferência rápida, depois do backup"}): tudo certo.</span></p>`;
  }
  if (b.verificado === false) {
    const problemas = (b.problemas || []).map((p) => `<li>${esc(p.nome)}: ${esc(p.detalhe)}</li>`).join("");
    return `<div class="alerta erro">${icone("alerta", 16)}<div>O backup não passou na conferência${v?.quando ? ` (${esc(dataHoraBR(v.quando))})` : ""}.
      ${problemas ? `<ul class="lista-info">${problemas}</ul>` : ""}</div></div>`;
  }
  return "";
}

function htmlPacotes(b) {
  const pacotes = b.pacotes || [];
  const partes = [];
  const item = (p) => `<li><span>${icone("arquivo", 14)} ${esc(p.arquivo)}</span>
    <span class="sutil">${esc(p.tamanho_legivel)} · ${esc(dataHoraBR(p.quando))}</span></li>`;
  if (pacotes.length) {
    partes.push(`<p class="sutil">Pacotes completos guardados:</p><ul class="backup-pacotes">${pacotes.map(item).join("")}</ul>`);
  } else if (b.ultimo_pacote?.ok) {
    partes.push(`<p class="sutil">Último pacote completo:</p><ul class="backup-pacotes">${item(b.ultimo_pacote)}</ul>`);
  }
  if (b.falha_pacote) {
    partes.push(alerta("aviso", `A última tentativa de gerar o pacote completo falhou em ${esc(dataHoraBR(b.falha_pacote))}. O sistema tenta de novo em 6 horas.`));
  }
  return partes.join("");
}

function htmlBotoes(b) {
  if (!b.local || !b.pasta || !pode("config")) return "";
  const desligado = b.executando ? "disabled" : "";
  return `<div class="linha-botoes">
    <button class="btn btn-primario" type="button" data-acao="backup-agora" data-executar data-espera="Fazendo backup…" ${desligado}>${icone("nuvem", 16)} Fazer backup agora</button>
    <button class="btn" type="button" data-acao="backup-pacote" data-executar data-espera="Gerando pacote…" ${desligado}>${icone("arquivo", 16)} Gerar pacote completo (.zip)</button>
    <button class="btn" type="button" data-acao="backup-verificar" data-executar data-espera="Conferindo…" ${desligado}>${icone("escudo", 16)} Verificar backup</button>
  </div>`;
}

const opcao = (nome, marcado, titulo, texto) => `<label class="opcao-app"><span class="interruptor">
    <input type="checkbox" name="${nome}" ${marcado ? "checked" : ""}><span></span></span>
    <span><strong>${titulo}</strong><small>${texto}</small></span></label>`;

function htmlFormulario(b) {
  const sugestoes = b.sugestoes || [];
  const pacote = b.pacote || "semanal";
  const opcaoPacote = (valor, texto) => `<option value="${valor}" ${pacote === valor ? "selected" : ""}>${texto}</option>`;
  return `<form class="backup-form" data-acao="backup-salvar" autocomplete="off" novalidate>
    <div class="campo backup-pasta"><label for="bk-pasta">Pasta do backup</label>
      <div class="input-grupo"><input id="bk-pasta" name="pasta" class="input" maxlength="500" value="${esc(b.pasta ?? "")}"
          placeholder="C:\\Users\\voce\\OneDrive" autocomplete="off" spellcheck="false">
        <button class="btn" type="button" data-acao="backup-escolher" data-espera="Escolhendo…">${icone("pasta", 16)} Escolher…</button></div></div>
    ${sugestoes.length ? `<div class="backup-sugestoes"><span class="sutil">Sugestões:</span>
      ${sugestoes.map((s) => `<button class="btn btn-sm" type="button" data-acao="backup-usar-sugestao" data-pasta="${esc(s.pasta)}"
        title="${esc(s.pasta)}">${icone("nuvem", 14)} ${esc(s.nome)}</button>`).join("")}</div>` : ""}
    <div class="backup-opcoes">
      <div class="campo"><label for="bk-horario">Horário</label>
        <input id="bk-horario" name="horario" type="time" class="input" value="${esc(b.horario || "12:30")}" required></div>
      <div class="campo"><label for="bk-dias">Guardar cópias por (dias)</label>
        <input id="bk-dias" name="manter_dias" type="number" min="3" max="365" step="1" class="input" value="${esc(b.manter_dias ?? 30)}" required></div>
      ${opcao("ativo", b.ativo, "Backup automático ligado", "Todo dia depois do horário; se o computador estava desligado, assim que abrir.")}
      <div class="campo"><label for="bk-pacote">Pacote completo (.zip)</label>
        <select id="bk-pacote" name="pacote" class="input">${opcaoPacote("semanal", "Toda semana")}${opcaoPacote("mensal", "Todo mês")}${opcaoPacote("nunca", "Nunca")}</select></div>
      <div class="campo"><label for="bk-pacotes">Guardar os últimos (pacotes)</label>
        <input id="bk-pacotes" name="manter_pacotes" type="number" min="1" max="24" step="1" class="input" value="${esc(b.manter_pacotes ?? 4)}" required></div>
      ${opcao("codigo", b.codigo !== false, "Levar o código-fonte e as versões", "Para reerguer o sistema inteiro em outro computador.")}
    </div>
    <div class="linha-botoes"><button class="btn btn-primario" type="submit" data-espera="Salvando…">${icone("check", 16)} Salvar</button></div>
  </form>`;
}

function htmlConfiguracao(b) {
  if (!b.local) {
    return alerta("info", "O backup fora do computador só pode ser configurado e executado no computador onde o Fin Pro está instalado. Aqui aparece só a situação.");
  }
  if (!podeAdministrar()) return htmlTravaAdmin("a pasta, o horário e os pacotes do backup", DESCRICAO_SENHA);
  return htmlFormulario(b);
}

const AJUDA = `<details class="rede-ajuda"><summary>Como restaurar em outro computador</summary>
    <ol class="passos-simples" style="margin-top:8px">
      <li>Instale o Python 3.10 ou mais novo</li>
      <li>Abra a pasta do backup (ou um pacote .zip) e dê dois cliques em RESTAURAR.bat</li>
      <li>Abra iniciar.bat na pasta escolhida</li>
      <li>Só ligue os bots do Telegram no computador novo depois de desligar o antigo</li>
    </ol>
  </details>
  <p class="sutil">A pasta do backup guarda os tokens dos bots e as senhas de e-mail: mantenha-a num lugar de confiança.</p>`;

export function html(b, erro) {
  const [rotulo, classe] = (!erro && SITUACAO_BACKUP[b?.situacao]) || [];
  const titulo = `<h3>${icone("nuvem", 18)} Backup fora do computador${rotulo ? ` <span class="chip ${classe}">${esc(rotulo)}</span>` : ""}</h3>`;
  let corpo;
  if (erro) {
    corpo = `${alertaErro(erro)}
      <div class="linha-botoes"><button class="btn" type="button" data-acao="backup-recarregar">${icone("atualizar", 16)} Tentar de novo</button></div>`;
  } else if (!b) {
    corpo = `<div class="esqueleto" style="height:180px"></div>`;
  } else {
    corpo = `<p class="sutil">Uma vez por dia, depois do horário escolhido (ou assim que o computador ligar, se passou da hora), o Fin Pro
      copia <strong>tudo</strong> para a pasta <code>Leitor de Boletos - Backup</code> dentro da pasta escolhida: OneDrive, Google Drive,
      Dropbox, pen drive ou HD externo.</p>
      ${htmlPartes(b)}
      ${htmlUltimo(b)}
      ${htmlConferencia(b)}
      ${htmlPacotes(b)}
      ${htmlBotoes(b)}
      ${htmlConfiguracao(b)}
      ${AJUDA}`;
  }
  return `<article class="card col-inteira" id="cfg-backup">${titulo}${corpo}</article>`;
}

// ------------------------------------------------------------------ ações

const campoPasta = () => tela.raiz?.querySelector("#cfg-backup [name=pasta]");

/** Fazer backup agora / gerar pacote / verificar: os três botões ficam desligados até terminar. */
async function executar(acao) {
  const botoes = [...(tela.raiz?.querySelectorAll("#cfg-backup [data-executar]") || [])];
  botoes.forEach((b) => { b.disabled = true; });
  if (acao !== "verificar") toast("Pode levar alguns minutos. Pode continuar usando o Fin Pro.", "info");
  let r;
  try {
    r = await api.post(`/api/backup/${acao}`);
  } catch (erro) {
    await atualizar(chave); // a falha fica guardada em "ultimo" / "falha_pacote": o cartão mostra o motivo
    carregarStatusLateral();
    avisarErro(erro);
    return;
  } finally {
    botoes.forEach((b) => { if (b.isConnected) b.disabled = false; });
  }
  redesenhar(chave, r);
  carregarStatusLateral();
  if (acao === "agora") {
    toast(`Backup feito: ${r.ultimo?.itens ?? 0} arquivo(s), ${r.ultimo?.tamanho_legivel || ""}.`, "ok", { duracao: 5000 });
    if (r.verificado === false) {
      toast("O backup foi feito, mas não passou na conferência. Veja os detalhes no cartão.", "aviso", { duracao: 8000 });
    }
  } else if (acao === "pacote") {
    toast(`Pacote completo gerado: ${r.ultimo_pacote?.arquivo || ""} (${r.ultimo_pacote?.tamanho_legivel || ""}).`, "ok", { duracao: 6000 });
  } else if (r.verificado) {
    toast("Backup conferido arquivo por arquivo: tudo certo.", "ok", { duracao: 5000 });
  } else {
    toast(`O backup não passou na conferência: ${(r.problemas || []).length} problema(s). Veja os detalhes no cartão.`, "erro", { duracao: 8000 });
  }
}

/** Confere os campos no navegador (o servidor responderia em inglês para números fora da faixa). */
function lerFormulario(form) {
  const f = form.elements;
  const avisar = (campo, texto) => {
    toast(texto, "aviso", { duracao: 5000 });
    campo.focus();
    return null;
  };
  const horario = f.horario.value.trim();
  if (!/^\d{1,2}:\d{2}$/.test(horario)) return avisar(f.horario, "Informe o horário do backup (HH:MM).");
  const manterDias = Number(f.manter_dias.value);
  if (!Number.isInteger(manterDias) || manterDias < 3 || manterDias > 365) {
    return avisar(f.manter_dias, "Guarde as cópias por 3 a 365 dias.");
  }
  const manterPacotes = Number(f.manter_pacotes.value);
  if (!Number.isInteger(manterPacotes) || manterPacotes < 1 || manterPacotes > 24) {
    return avisar(f.manter_pacotes, "Guarde de 1 a 24 pacotes completos.");
  }
  const pasta = f.pasta.value.trim();
  if (f.ativo.checked && !pasta) return avisar(f.pasta, "Escolha a pasta do backup antes de ligar.");
  return {
    corpo: { horario, manter_dias: manterDias, pacote: f.pacote.value, manter_pacotes: manterPacotes, codigo: f.codigo.checked, ativo: f.ativo.checked },
    pasta,
  };
}

async function salvar(form) {
  const b = tela.dados[chave] || {};
  const lido = lerFormulario(form);
  if (!lido) return;
  const { corpo, pasta } = lido;
  // Só manda a pasta quando ela mudou: pasta vazia é recusada, e reenviar uma pasta desconectada impediria até desligar.
  if (pasta && pasta !== (b.pasta ?? "")) {
    if (b.pasta && b.ultimo_sucesso && !(await confirmar({
      titulo: "Trocar a pasta do backup?",
      mensagem: "As cópias já feitas continuam na pasta antiga; a primeira cópia na nova pasta leva mais tempo.",
      textoConfirmar: "Trocar a pasta",
    }))) return;
    corpo.pasta = pasta;
  }
  if (b.ativo && !corpo.ativo && !(await confirmar({
    titulo: "Desligar o backup?",
    mensagem: "Sem o backup fora do computador, se este computador quebrar os dados podem se perder.",
    textoConfirmar: "Desligar",
    perigo: true,
  }))) return;
  let r;
  try {
    r = await comAdmin(() => api.put("/api/backup/config", corpo), DESCRICAO_SENHA);
  } catch (erro) {
    if (erro?.codigo === "backup_invalido") {
      const texto = String(erro.message || "");
      const campo = /hor[áa]rio/i.test(texto) ? "horario" : /pasta|caminho|permiss/i.test(texto) ? "pasta" : null;
      if (campo) form.elements[campo]?.focus();
    }
    throw erro;
  }
  redesenhar(chave, r);
  carregarStatusLateral();
  toast(r.ativo
    ? `Backup salvo. Ele roda todo dia depois das ${r.horario}.`
    : "Configuração do backup salva (backup automático desligado).", "ok", { duracao: 5000 });
}

export const acoes = {
  "backup-agora": () => executar("agora"),
  "backup-pacote": () => executar("pacote"),
  "backup-verificar": () => executar("verificar"),
  "backup-recarregar": () => atualizar(chave),
  /** Janela do Windows para escolher a pasta (fica aberta até a pessoa escolher ou cancelar). */
  "backup-escolher": async () => {
    let r;
    try {
      r = await comAdmin(() => api.post("/api/backup/escolher-pasta"), DESCRICAO_SENHA);
    } catch (erro) {
      if (erro?.codigo !== "sem_janela") throw erro;
      toast(erro.message, "aviso", { duracao: 7000 });
      campoPasta()?.focus();
      return;
    }
    const campo = campoPasta();
    if (!r?.pasta || !campo) return;
    campo.value = r.pasta;
    campo.focus();
    toast("Pasta escolhida. Clique em Salvar para usar.", "info", { duracao: 5000 });
  },
  "backup-usar-sugestao": (alvo) => {
    const campo = campoPasta();
    if (!campo) return;
    campo.value = alvo.dataset.pasta || "";
    campo.focus();
  },
};

export const formularios = {
  "backup-salvar": salvar,
};

// Inicialização: rotas, tema, status do sistema e arrastar/colar global.
import { api } from "./api.js";
import { estado, ehAdministrador, pode } from "./estado.js";
import { hidratarIcones, icone } from "./icons.js";
import { abrirModal, brl, dataBR, dataHoraBR, esc, mensagemErro, toast } from "./ui.js";
import * as painel from "./views/painel.js";
import * as leitura from "./views/leitura/index.js";
import * as boletos from "./views/boletos/index.js";
import * as pix from "./views/pix/index.js";
import * as caixa from "./views/caixa/index.js";
import * as comprovantes from "./views/comprovantes.js";
import * as diesel from "./views/diesel/index.js";
import * as empresas from "./views/empresas/index.js";
import * as gastos from "./views/gastos.js";
import * as importar from "./views/importar.js";
import * as notificacoes from "./views/notificacoes.js";
import * as transferencias from "./views/transferencias.js";
import * as configuracoes from "./views/configuracoes/index.js";

const ROTAS = {
  painel: { titulo: "Painel", subtitulo: "Visão geral dos boletos e Pix lançados na planilha", view: painel },
  ler: { titulo: "Ler boletos", subtitulo: "Envie PDFs ou fotos, confira os dados e lance na planilha", view: leitura },
  boletos: { titulo: "Boletos lançados", subtitulo: "Consulte, filtre, edite e exporte os registros da planilha", view: boletos },
  importar: { titulo: "Importar boletos", subtitulo: "Traga boletos exportados de outro sistema (Excel, CSV ou TXT) para a planilha", view: importar, menu: "config" },
  pix: { titulo: "Pagamentos Pix", subtitulo: "Lance Pix por chave, Copia e Cola ou QR code e acompanhe os pagamentos", view: pix },
  comprovantes: { titulo: "Comprovantes", subtitulo: "Ache o comprovante de boletos, Pix, cheques, recebimentos, caixa e notas fiscais", view: comprovantes },
  diesel: { titulo: "Diesel", subtitulo: "Compras no posto, abastecimentos de cada máquina, saldo e consumo", view: diesel },
  gastos: { titulo: "Gastos", subtitulo: "Onde o dinheiro foi gasto: análise por centro de custo de boletos, Pix e caixa", view: gastos },
  caixa: { titulo: "Caixa", subtitulo: "Dinheiro que entra e que sai: por dia, semana, mês ou ano, com os relatórios", view: caixa },
  empresas: { titulo: "Empresas", subtitulo: "Vendas a prazo: notas fiscais, cheques, recebimentos e o fechamento de cada cliente", view: empresas },
  transferencias: { titulo: "Transferências de clientes", subtitulo: "Notas pagas por Pix ou TED/DOC que a Operações manda. Marque as notas e ligue o comprovante do pagamento", view: transferencias },
  notificacoes: { titulo: "Notificações", subtitulo: "Avisos de boletos e Pix a vencer no Windows, no Telegram e por e-mail", view: notificacoes },
  config: { titulo: "Configurações", subtitulo: "Aplicativo, usuários, backup, integrações e saúde do sistema", view: configuracoes },
};
const ORDEM_ROTAS = ["painel", "ler", "boletos", "pix", "comprovantes", "caixa", "diesel", "gastos", "empresas", "transferencias", "notificacoes", "config"];
// Telas que só aparecem para quem tem a permissão (o resto todo mundo vê)
const PERMISSAO_DA_ROTA = { ler: "lancar", gastos: "gastos", empresas: "empresas", caixa: "caixa", diesel: "diesel", notificacoes: "notificacoes",
  transferencias: "transferencias", config: "config", importar: "config" };

function rotaLiberada(rota) {
  const permissao = PERMISSAO_DA_ROTA[rota];
  return !permissao || pode(permissao);
}

/** Esconde do menu (e do atalho no topo) o que a pessoa não pode usar. */
function aplicarPermissoes() {
  document.querySelectorAll("[data-rota]").forEach((a) => { a.hidden = !rotaLiberada(a.dataset.rota); });
  const atalho = document.querySelector(".topo-cta");
  if (atalho) atalho.dataset.semPermissao = rotaLiberada("ler") ? "" : "1";
}

// ------------------------------------------------------------------ sininho de avisos

let avisos = null;
const CLASSE_AVISO = { vencido: "erro", hoje: "aviso", amanha: "aviso", proximos: "info" };

function prazoAviso(a) {
  if (a.tipo_pagamento === "cheque") {  // cheque pré-datado: é para depositar, não para pagar
    if (a.dias < 0) return `depositar (passou ${-a.dias} dia(s))`;
    return a.dias === 0 ? "depositar hoje" : a.dias === 1 ? "depositar amanhã" : `depositar em ${a.dias} dias`;
  }
  if (a.dias < 0) return `venceu há ${-a.dias} dia(s)`;
  if (a.dias === 0) return "vence hoje";
  if (a.dias === 1) return "vence amanhã";
  return `vence em ${a.dias} dias`;
}

// ------------------------------------------------------------------ gravação pendente (planilha aberta no Excel)

let pendentesAnteriores = 0;

async function carregarGravacao() {
  let estadoGravacao;
  try {
    estadoGravacao = await api.get("/api/gravacao");
  } catch {
    return;
  }
  const aviso = document.getElementById("aviso-gravacao");
  const n = estadoGravacao.pendentes;
  if (n) {
    aviso.innerHTML = `${icone("alerta", 18)}
      <div><strong>${n === 1 ? "1 alteração aguardando" : `${n} alterações aguardando`} gravação na planilha</strong>
        <span>A planilha está aberta em outro programa (ex.: Excel). Feche o arquivo — a gravação é feita automaticamente.</span></div>
      <button class="btn btn-sm" data-gravacao="tentar">${icone("atualizar", 14)} Tentar agora</button>`;
  }
  aviso.hidden = !n;
  if (pendentesAnteriores && !n) {
    const gravados = estadoGravacao.ultimo_resultado?.gravados ?? pendentesAnteriores;
    toast(`${gravados} alteração(ões) gravada(s) na planilha.`, "ok", { duracao: 5000 });
    window.dispatchEvent(new Event("boletos:atualizar"));
  }
  pendentesAnteriores = n;
}

/** Tela de entrada: login por pessoa (quando há usuários cadastrados) ou a senha única de acesso pela rede. */
async function pedirSenha() {
  if (document.getElementById("tela-acesso")) return;
  try { estado.acesso = await api.get("/api/acesso/estado"); } catch { /* usa o último estado conhecido */ }
  if (document.getElementById("tela-acesso")) return;
  const porUsuario = Boolean(estado.acesso?.usuarios);
  const opcional = porUsuario && estado.acesso?.local && !estado.acesso?.exigir_login_no_computador;
  const tela = document.createElement("div");
  tela.id = "tela-acesso";
  tela.className = "tela-acesso";
  tela.innerHTML = `
    <form class="card acesso-card" id="form-acesso">
      <span class="marca-logo acesso-logo" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 6v12M7 6v12M10 6v12M14 6v12M17 6v12M20 6v12"/></svg></span>
      <h2>Fin Pro</h2>
      <p>${porUsuario
        ? "Entre com o seu usuário. Assim o sistema registra quem lançou, pagou ou alterou cada boleto."
        : "Digite a senha de acesso definida no computador onde o sistema está instalado."}</p>
      ${porUsuario ? `<label class="campo"><span class="sutil">Usuário</span>
        <input id="login-acesso" class="input" autocomplete="username" autocapitalize="none" spellcheck="false" required autofocus></label>` : ""}
      <label class="campo"><span class="sutil">${porUsuario ? "Senha" : "Senha de acesso"}</span>
        <input id="senha-acesso" type="password" class="input" autocomplete="current-password" required ${porUsuario ? "" : "autofocus"}></label>
      <button class="btn btn-primario" type="submit">${icone("check", 16)} Entrar</button>
      ${opcional ? `<button class="btn btn-fantasma" type="button" data-continuar>Continuar sem entrar (computador principal)</button>` : ""}
      <p class="acesso-erro" id="acesso-erro" role="alert"></p>
    </form>`;
  document.body.appendChild(tela);
  const login = tela.querySelector("#login-acesso");
  const campo = tela.querySelector("#senha-acesso");
  (login || campo).focus();
  tela.querySelector("[data-continuar]")?.addEventListener("click", () => tela.remove());
  tela.querySelector("#form-acesso").addEventListener("submit", async (e) => {
    e.preventDefault();
    const botao = tela.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      if (porUsuario) await api.post("/api/usuarios/entrar", { login: login.value, senha: campo.value });
      else await api.post("/api/acesso", { senha: campo.value });
      location.reload();
    } catch (erro) {
      tela.querySelector("#acesso-erro").textContent = mensagemErro(erro);
      campo.value = "";
      campo.focus();
      botao.disabled = false;
    }
  });
}

async function sairDoAparelho() {
  try {
    await api.post("/api/usuarios/sair");
    await api.post("/api/acesso/sair");
  } finally {
    location.reload();
  }
}

function trocarMinhaSenha() {
  const { el, fechar } = abrirModal({
    titulo: "Trocar a minha senha",
    corpo: `<form class="grade-campos" data-minha-senha autocomplete="off">
      <div class="campo col-2"><label for="ms-atual">Senha atual</label>
        <input id="ms-atual" type="password" class="input" name="senha_atual" autocomplete="current-password" autofocus></div>
      <div class="campo"><label for="ms-nova">Nova senha</label>
        <input id="ms-nova" type="password" class="input" name="senha" autocomplete="new-password" minlength="6"></div>
      <div class="campo"><label for="ms-conf">Repita a nova senha</label>
        <input id="ms-conf" type="password" class="input" name="confirmacao" autocomplete="new-password" minlength="6"></div>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Trocar senha</button>`,
  });
  const formulario = el.querySelector("[data-minha-senha]");
  const salvar = async (e) => {
    e?.preventDefault();
    const botao = el.querySelector("[data-salvar]");
    botao.disabled = true;
    try {
      await api.post("/api/usuarios/minha-senha", Object.fromEntries(new FormData(formulario).entries()));
      fechar(true);
      toast("Senha trocada. Os outros aparelhos em que você tinha entrado foram desconectados.", "ok", { duracao: 6000 });
    } catch (erro) {
      botao.disabled = false;
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  formulario.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

async function carregarAvisos() {
  try {
    avisos = await api.get("/api/notificacoes");
  } catch {
    avisos = null;
  }
  renderizarAvisos();
  carregarContagemEntrada();
  carregarContagemEmpresas();
  carregarContagemCaixa();
  carregarContagemDiesel();
}

function mostrarContagemEntrada(n) {
  const el = document.querySelector("[data-contador-entrada]");
  if (!el) return;
  el.textContent = n > 99 ? "99+" : String(n);
  el.hidden = !n;
}

async function carregarContagemEntrada() {
  try {
    mostrarContagemEntrada((await api.get("/api/entrada")).pendentes);
  } catch {
    /* sem acesso ou servidor antigo: sem contador */
  }
}

function mostrarContador(seletor, n) {
  const el = document.querySelector(seletor);
  if (!el) return;
  el.textContent = n > 99 ? "99+" : String(n || "");
  el.hidden = !n;
}

async function carregarContagemCaixa() {
  if (!pode("caixa")) return mostrarContador("[data-contador-caixa]", 0);
  try {
    mostrarContador("[data-contador-caixa]", (await api.get("/api/caixa/bot/entrada")).pendentes);
  } catch {
    mostrarContador("[data-contador-caixa]", 0);
  }
  return null;
}

async function carregarContagemDiesel() {
  if (!pode("diesel")) return mostrarContador("[data-contador-diesel]", 0);
  try {
    mostrarContador("[data-contador-diesel]", (await api.get("/api/diesel/bot/entrada")).pendentes);
  } catch {
    mostrarContador("[data-contador-diesel]", 0);
  }
  return null;
}

async function carregarContagemEmpresas() {
  const el = document.querySelector("[data-contador-empresas]");
  if (!el) return;
  if (!pode("empresas")) {  // quem não usa a tela de Empresas não precisa do contador
    el.hidden = true;
    return;
  }
  try {
    const n = (await api.get("/api/empresas/entrada")).pendentes;
    el.textContent = n > 99 ? "99+" : String(n);
    el.hidden = !n;
  } catch {
    el.hidden = true;
  }
}

let vistosNestaAbertura = new Set(); // continuam destacados como "Novo" enquanto o painel está aberto

function linkAviso(a) {
  if (a.tipo_pagamento === "cheque") return "#/empresas?aba=cheques";
  return a.tipo_pagamento === "pix"
    ? `#/pix?q=${encodeURIComponent(a.beneficiario)}`
    : `#/boletos?q=${encodeURIComponent(a.linha_digitos || a.beneficiario)}`;
}

const ROTULO_TIPO_AVISO = { pix: "Pix", cheque: "Cheque a depositar" };

function renderizarAvisos() {
  const todos = avisos?.alertas || [];
  const lista = todos.filter((a) => !a.dispensado);
  const dispensados = todos.length - lista.length;
  const naoVistos = lista.filter((a) => !a.visto).length;
  const badge = document.getElementById("sino-badge");
  const contadorNav = document.querySelector("[data-contador-notif]");
  badge.hidden = naoVistos === 0;
  badge.textContent = naoVistos > 99 ? "99+" : String(naoVistos);
  contadorNav.hidden = naoVistos === 0;
  contadorNav.textContent = String(naoVistos);

  const novo = (a) => !a.visto || vistosNestaAbertura.has(a.chave);
  const ordenados = [...lista.filter(novo), ...lista.filter((a) => !novo(a))];
  const dias = avisos?.janela_dias ?? 3;
  const item = (a) => `
    <li class="${novo(a) ? "novo" : "visto"}" data-chave="${esc(a.chave)}">
      <a href="${linkAviso(a)}">
        <span class="sino-etiquetas">
          <span class="chip ${CLASSE_AVISO[a.categoria]}">${esc(prazoAviso(a))}</span>
          ${ROTULO_TIPO_AVISO[a.tipo_pagamento] ? `<span class="chip">${ROTULO_TIPO_AVISO[a.tipo_pagamento]}</span>` : ""}
          ${novo(a) ? `<span class="sino-novo">Novo</span>` : ""}
        </span>
        <strong>${esc(a.beneficiario)}</strong>
        <span class="sutil">${brl(a.valor)} · ${dataBR(a.vencimento)}${a.numero_documento ? ` · Doc. ${esc(a.numero_documento)}` : ""}</span>
      </a>
      <button class="btn-icone sino-dispensar" type="button" data-sino="dispensar" title="Dispensar este aviso" aria-label="Dispensar este aviso">${icone("x", 14)}</button>
    </li>`;

  const rodape = [
    lista.length > 12 ? `<a href="#/boletos?situacao=pendente">Ver todos os ${lista.length}</a>` : "",
    dispensados ? `<button class="sino-link" type="button" data-sino="restaurar">Mostrar ${dispensados === 1 ? "1 aviso dispensado" : `${dispensados} avisos dispensados`}</button>` : "",
  ].filter(Boolean).join("");

  document.getElementById("painel-sino").innerHTML = `
    <div class="sino-cabecalho"><strong>${icone("sino", 16)} Avisos de vencimento</strong><a href="#/notificacoes">Configurar</a></div>
    ${lista.length
      ? `<ul class="sino-lista">${ordenados.slice(0, 12).map(item).join("")}</ul>`
      : `<div class="sino-vazio">${icone("ok", 22)}<span>${dispensados
        ? "Nenhum aviso para mostrar."
        : `Nenhum boleto ou Pix pendente vencendo nos próximos ${dias} dias.`}</span></div>`}
    ${rodape ? `<div class="sino-rodape">${rodape}</div>` : ""}`;
}

/** Ao abrir o sininho: os avisos passam a contar como vistos (a contagem some). */
async function marcarAvisosVistos() {
  const novos = (avisos?.alertas || []).filter((a) => !a.visto && !a.dispensado);
  if (!novos.length) return;
  novos.forEach((a) => {
    a.visto = true;
    vistosNestaAbertura.add(a.chave);
  });
  renderizarAvisos();
  try {
    await api.post("/api/notificacoes/vistos", { chaves: novos.map((a) => a.chave) });
  } catch {
    /* sem conexão: a contagem volta na próxima atualização e é marcada de novo ao abrir */
  }
}

function fecharSino() {
  const painel = document.getElementById("painel-sino");
  if (painel.hidden) return;
  painel.hidden = true;
  vistosNestaAbertura.clear();
  renderizarAvisos();
}

let atual = null;

function lerHash() {
  const semPrefixo = location.hash.replace(/^#\/?/, "");
  const [rota, consulta = ""] = semPrefixo.split("?");
  return { rota: rota || "painel", params: new URLSearchParams(consulta) };
}

async function navegar() {
  const { rota, params } = lerHash();
  const definicao = ROTAS[rota];
  if (!definicao) {
    location.hash = "#/painel";
    return;
  }
  if (!rotaLiberada(rota)) {
    toast("Você não tem permissão para esta tela. Peça ao administrador do Fin Pro.", "aviso", { duracao: 6000 });
    location.hash = "#/painel";
    return;
  }
  atual?.view.desmontar?.();
  document.querySelectorAll("[data-rota]").forEach((a) => a.classList.toggle("ativo", a.dataset.rota === (definicao.menu || rota)));
  document.getElementById("titulo-pagina").textContent = definicao.titulo;
  document.getElementById("subtitulo-pagina").textContent = definicao.subtitulo;
  document.querySelector(".topo-cta").hidden = rota === "ler" || !rotaLiberada("ler");
  document.title = `${definicao.titulo} · ${estado.status?.demonstracao ? "Fin Pro (demonstração)" : "Fin Pro"}`;
  document.body.classList.remove("menu-aberto");

  const el = document.getElementById("view");
  el.className = `view view-${rota}`;
  el.innerHTML = "";
  atual = { rota, view: definicao.view };
  window.scrollTo({ top: 0 });
  try {
    await definicao.view.montar(el, params);
  } catch (erro) {
    console.error(erro);
    el.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar esta tela</h3><p>${esc(erro.message)}</p>
      <button class="btn" onclick="location.reload()">${icone("atualizar", 16)} Recarregar</button></div>`;
  }
}

function htmlStatusBackup(b) {
  if (!b) return "";
  const texto = {
    ok: "Backup em dia", aguardando: "Backup: aguardando", atrasado: "Backup atrasado", erro: "Backup falhou", desligado: "Backup desligado",
  }[b.situacao] || "Backup";
  const ponto = { ok: "ok", aguardando: "ok", atrasado: "erro", erro: "erro", desligado: "aviso" }[b.situacao] || "";
  const titulo = b.ultimo_sucesso ? `Último backup: ${dataHoraBR(b.ultimo_sucesso)}` : "Configure em Configurações → Backup fora do computador";
  return `<a class="status-linha status-link" href="#/config?aba=integracoes" title="${esc(titulo)}"><span class="ponto ${ponto}"></span>${texto}</a>`;
}

function htmlUsuarioAtual() {
  const a = estado.acesso;
  if (a?.usuario) {
    return `<div class="status-usuario">${icone("pessoa", 14)}<span title="Usuário: ${esc(a.usuario.login)}">${esc(a.usuario.nome)}</span>
      ${ehAdministrador() ? `<span class="chip ok">Administrador</span>` : ""}</div>
      <div class="status-acoes"><button class="status-sair" type="button" data-minha-senha>${icone("chave", 13)} Trocar senha</button>
        <button class="status-sair" type="button" data-sair>${icone("sair", 13)} Sair</button></div>`;
  }
  if (a?.usuarios && a.local) {
    return `<button class="status-sair" type="button" data-entrar>${icone("pessoa", 14)} Entrar com meu usuário</button>`;
  }
  return a && !a.local ? `<button class="status-sair" type="button" data-sair>${icone("sair", 14)} Sair deste aparelho</button>` : "";
}

async function carregarStatus() {
  const el = document.getElementById("status-sistema");
  try {
    estado.status = await api.get("/api/status");
    const s = estado.status;
    el.innerHTML = `
      <div class="status-linha"><span class="ponto ok"></span>Planilha conectada</div>
      <div class="status-linha"><span class="ponto ${s.ocr ? "ok" : "aviso"}"></span>OCR ${s.ocr ? "ativo" : "indisponível"}</div>
      <div class="status-linha"><span class="ponto ${s.ia ? "ok" : ""}"></span>IA ${s.ia ? "ativa" : "desativada"}</div>
      ${htmlStatusBackup(s.backup)}
      <div class="status-versao">Versão ${esc(s.versao)}</div>
      ${s.demonstracao ? `<div class="status-linha selo-demo" title="Dados de exemplo; nada é enviado para fora">${icone("info", 13)} Versão de demonstração</div>` : ""}
      ${htmlUsuarioAtual()}`;
  } catch {
    estado.status = null;
    el.innerHTML = `<div class="status-linha"><span class="ponto erro"></span>Servidor offline</div>`;
  }
}

function aplicarTema(tema) {
  document.documentElement.dataset.theme = tema;
  try { localStorage.setItem("tema", tema); } catch { /* modo privado */ }
  document.getElementById("btn-tema").innerHTML = tema === "dark"
    ? `${icone("sol", 16)}<span>Tema claro</span>`
    : `${icone("lua", 16)}<span>Tema escuro</span>`;
}

function contemArquivos(evento) {
  return [...(evento.dataTransfer?.types || [])].includes("Files");
}

function enviarParaLeitura(arquivos) {
  const planilha = arquivos.find((a) => /\.(xlsx|xlsm|xls|csv|txt)$/i.test(a.name || ""));
  if (planilha) {
    // A importação de planilhas é restrita: só recebe arquivos com a tela de importação aberta
    if (lerHash().rota === "importar") importar.receberArquivo(planilha);
    else toast("Para importar planilhas de outro sistema, use Configurações → Importar boletos (área restrita).", "info", { duracao: 6000 });
    return;
  }
  if (lerHash().rota === "pix") {
    pix.lerArquivos(arquivos); // na aba Pix, a imagem é lida como QR code
    return;
  }
  if (lerHash().rota === "empresas") {
    empresas.receberArquivos(arquivos); // nota fiscal, cheque, comprovante ou print do fechamento
    return;
  }
  if (lerHash().rota !== "ler") location.hash = "#/ler";
  leitura.enfileirar(arquivos);
}

function ligarEventosGlobais() {
  document.getElementById("btn-tema").addEventListener("click", () => {
    aplicarTema(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
  document.getElementById("btn-menu").addEventListener("click", () => document.body.classList.toggle("menu-aberto"));
  document.getElementById("sidebar-fundo").addEventListener("click", () => document.body.classList.remove("menu-aberto"));

  let profundidade = 0;
  window.addEventListener("dragenter", (e) => {
    if (!contemArquivos(e)) return;
    profundidade += 1;
    const aviso = document.querySelector(".soltar-caixa strong");
    if (aviso) aviso.textContent = document.body.dataset.soltar || "Solte para ler os boletos";
    document.body.classList.add("arrastando");
  });
  window.addEventListener("dragleave", (e) => {
    if (!contemArquivos(e)) return;
    profundidade = Math.max(0, profundidade - 1);
    if (!profundidade) document.body.classList.remove("arrastando");
  });
  window.addEventListener("dragover", (e) => { if (contemArquivos(e)) e.preventDefault(); });
  window.addEventListener("drop", (e) => {
    if (!contemArquivos(e)) return;
    e.preventDefault();
    profundidade = 0;
    document.body.classList.remove("arrastando");
    const arquivos = [...e.dataTransfer.files];
    // a tela aberta pode ficar com o arquivo (ex.: Diesel lê o canhoto); se nenhuma quiser, vai para Ler boletos
    const soltos = new CustomEvent("arquivos:soltos", { detail: arquivos, cancelable: true });
    if (arquivos.length && window.dispatchEvent(soltos)) enviarParaLeitura(arquivos);
  });

  document.addEventListener("paste", (e) => {
    const arquivos = [...(e.clipboardData?.files || [])];
    if (arquivos.length) {
      e.preventDefault();
      enviarParaLeitura(arquivos);
      return;
    }
    if (e.target.closest?.("input, textarea, select")) return;
    const texto = e.clipboardData?.getData("text") || "";
    if (texto.trim().startsWith("000201")) {
      e.preventDefault();
      if (lerHash().rota !== "pix") location.hash = "#/pix";
      pix.receberCopiaECola(texto.trim());
      return;
    }
    const digitos = texto.replace(/\D/g, "");
    if (digitos.length >= 44 && digitos.length <= 48) {
      e.preventDefault();
      if (lerHash().rota !== "ler") location.hash = "#/ler";
      leitura.analisarTexto(digitos);
    }
  });

  const painelSino = document.getElementById("painel-sino");
  document.getElementById("btn-sino").addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!painelSino.hidden) {
      fecharSino();
      return;
    }
    painelSino.hidden = false;
    await carregarAvisos();
    if (!painelSino.hidden) marcarAvisosVistos();
  });
  painelSino.addEventListener("click", async (e) => {
    const botao = e.target.closest("[data-sino]");
    if (!botao) return;
    e.preventDefault();
    e.stopPropagation(); // o painel é redesenhado: não deixar o clique fechá-lo
    if (botao.dataset.sino === "dispensar") {
      const chave = botao.closest("[data-chave]").dataset.chave;
      const aviso = (avisos?.alertas || []).find((a) => a.chave === chave);
      if (aviso) Object.assign(aviso, { dispensado: true, visto: true });
      renderizarAvisos();
      try {
        await api.post("/api/notificacoes/dispensar", { chave });
      } catch (erro) {
        toast(mensagemErro(erro), "erro");
        carregarAvisos();
      }
    } else if (botao.dataset.sino === "restaurar") {
      try {
        await api.post("/api/notificacoes/restaurar");
      } catch (erro) {
        toast(mensagemErro(erro), "erro");
      }
      await carregarAvisos();
    }
  });
  document.addEventListener("click", (e) => {
    if (!painelSino.hidden && (!e.target.closest(".menu-ancora") || e.target.closest(".painel-sino a"))) fecharSino();
  });
  window.addEventListener("avisos:atualizar", carregarAvisos);
  window.addEventListener("empresas:atualizar", carregarContagemEmpresas);
  window.addEventListener("caixa:contagem", (e) => mostrarContador("[data-contador-caixa]", e.detail));
  window.addEventListener("diesel:contagem", (e) => mostrarContador("[data-contador-diesel]", e.detail));
  window.addEventListener("entrada:contagem", (e) => mostrarContagemEntrada(e.detail));
  window.addEventListener("acesso:necessario", pedirSenha);
  window.addEventListener("acesso:sair", sairDoAparelho);
  document.getElementById("status-sistema").addEventListener("click", (e) => {
    if (e.target.closest("[data-sair]")) sairDoAparelho();
    else if (e.target.closest("[data-entrar]")) pedirSenha();
    else if (e.target.closest("[data-minha-senha]")) trocarMinhaSenha();
  });
  window.addEventListener("gravacao:atualizar", carregarGravacao);
  window.addEventListener("status:atualizar", carregarStatus);
  document.getElementById("aviso-gravacao").addEventListener("click", async (e) => {
    const botao = e.target.closest("[data-gravacao]");
    if (!botao) return;
    botao.disabled = true;
    try {
      const resultado = await api.post("/api/gravacao/tentar");
      if (resultado.bloqueada) toast("A planilha continua aberta. Feche-a no Excel e tente de novo.", "aviso", { duracao: 6000 });
      await carregarGravacao();
    } catch (erro) {
      toast(mensagemErro(erro), "erro");
    } finally {
      botao.disabled = false;
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.altKey && !e.ctrlKey && !e.metaKey && /^[1-9]$/.test(e.key)) {
      e.preventDefault();
      location.hash = `#/${ORDEM_ROTAS[Number(e.key) - 1]}`;
    }
  });

  window.addEventListener("hashchange", () => {
    navegar();
    carregarAvisos();
  });
  window.addEventListener("focus", () => { if (!estado.status) carregarStatus(); });
}

async function iniciar() {
  hidratarIcones();
  aplicarTema(document.documentElement.dataset.theme || "light");
  ligarEventosGlobais();
  try {
    estado.acesso = await api.get("/api/acesso/estado");
  } catch {
    estado.acesso = null;
  }
  if (estado.acesso && !estado.acesso.autorizado) {
    pedirSenha();
    return;
  }
  await carregarStatus();
  aplicarPermissoes();
  if (!estado.status) toast("Não foi possível conectar ao servidor.", "erro", { duracao: 6000 });
  await navegar();
  carregarAvisos();
  carregarGravacao();
  setInterval(carregarAvisos, 5 * 60 * 1000);
  setInterval(carregarGravacao, 15 * 1000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}

iniciar();

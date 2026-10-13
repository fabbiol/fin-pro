// Configurações · Aplicativo no computador: iniciar junto com o Windows, ícone na bandeja e atalhos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { esc, toast } from "../../ui.js";
import { alertaErro, atualizar, buscar, redesenhar } from "./tela.js";

export const chave = "aplicativo";

/** GET /api/app (sempre 200; o cartão "Banco de dados e planilha" pede o mesmo endereço e a chamada é compartilhada). */
export const carregar = () => buscar("/api/app");

const TITULO = `${icone("aplicativo", 18)} Aplicativo no computador`;

/** Uma chave liga/desliga (data-acao="aplicativo-<nome>"). Desabilitada quando a opção não pode ser mudada daqui. */
export function opcaoAplicativo(nome, titulo, texto, ligado, desligada) {
  return `<label class="opcao-app${desligada ? " desabilitada" : ""}"><span class="interruptor">
      <input type="checkbox" data-acao="aplicativo-${esc(nome)}"${ligado ? " checked" : ""}${desligada ? " disabled" : ""}><span></span></span>
    <span><strong>${esc(titulo)}</strong><small>${esc(texto)}</small></span></label>`;
}

export function html(app, erro) {
  if (erro || app === undefined) {
    return `<article class="card col-inteira" id="cfg-aplicativo"><h3>${TITULO}</h3>
      ${erro ? alertaErro(erro) : `<div class="esqueleto" style="height:96px"></div>`}</article>`;
  }
  const inicio = app?.inicializacao || {};
  const prefs = app?.preferencias || {};
  const criados = app?.atalhos?.criados || [];
  // Windows de verdade (não pelo navegador): no servidor online e no Linux nada disto existe.
  const windows = Boolean(app?.atalhos?.disponivel || inicio.disponivel);
  const podeIniciar = Boolean(inicio.disponivel && app?.local);
  const podeApp = windows && Boolean(app?.local);

  if (!windows) {
    return `<article class="card col-inteira" id="cfg-aplicativo"><h3>${TITULO}</h3>
      <div class="alerta info">${icone("info", 16)}<div>Iniciar com o Windows, ícone na bandeja e atalhos só existem no Fin Pro instalado num
        computador com Windows. Este Fin Pro está rodando em outro sistema (ex.: servidor online). Para ter um ícone, abra o Fin Pro no
        Chrome ou no Edge e use o menu ⋮ → Instalar Fin Pro (no celular: Adicionar à tela inicial).</div></div>
    </article>`;
  }

  const chipModo = app.modo_app ? `<span class="chip ok">Aberto no aplicativo</span>` : `<span class="chip">Aberto no navegador</span>`;
  const chipAtalhos = criados.length
    ? `<span class="chip ok" title="${esc(criados.join("\n"))}">Atalhos criados</span>` : "";
  let aviso = "";
  if (!app.local) {
    aviso = `<div class="alerta info">${icone("info", 16)}<div>Estas opções só podem ser alteradas no computador onde o Fin Pro está instalado.</div></div>`;
  } else if (!inicio.disponivel) {
    aviso = `<p class="sutil">A pasta Inicializar do Windows não foi encontrada neste computador: iniciar junto com o Windows não está disponível.</p>`;
  }
  return `<article class="card col-inteira" id="cfg-aplicativo">
    <h3>${TITULO}<span class="espaco"></span>${chipModo}</h3>
    <p class="sutil">O Fin Pro abre numa janela própria e fica com um ícone perto do relógio (bandeja). Clicar numa notificação traz o
      aplicativo para a frente, já na tela certa.</p>
    <div class="app-opcoes">
      ${opcaoAplicativo("iniciar", "Iniciar junto com o Windows",
        "Abre o Fin Pro ao ligar o computador, para os lembretes de vencimento chegarem mesmo sem abrir o sistema.",
        inicio.ativo, !podeIniciar)}
      ${opcaoAplicativo("minimizado", "Iniciar minimizado na bandeja",
        "Ao ligar o computador, abre só o ícone perto do relógio, sem mostrar a janela. Vale quando “Iniciar junto com o Windows” estiver ligado.",
        prefs.minimizado_ao_iniciar, !podeIniciar)}
      ${opcaoAplicativo("bandeja", "Fechar no X esconde na bandeja",
        "A janela some, mas o Fin Pro continua aberto cuidando dos lembretes. Para encerrar: botão direito no ícone → Sair.",
        prefs.fechar_para_bandeja, !podeApp)}
    </div>
    ${podeApp ? `<div class="linha-botoes" style="align-items:center">
      <button class="btn" type="button" data-acao="aplicativo-atalhos" data-espera="Criando…">${icone("externo", 16)} Criar atalhos</button>
      <span class="sutil">Área de Trabalho e Menu Iniciar.</span>${chipAtalhos}</div>` : ""}
    ${aviso}
  </article>`;
}

/** Busca /api/app de novo e redesenha o cartão (depois de mudar algo que a resposta não traz por inteiro). */
export const atualizarAplicativo = () => atualizar(chave);

/** Roda a mudança; se o servidor recusar, redesenha com o estado real antes de o erro seguir para eventos.js. */
async function mudar(tarefa) {
  try {
    await tarefa();
  } catch (erro) {
    await atualizarAplicativo();
    throw erro;
  }
}

export const alteracoes = {
  "aplicativo-iniciar": (campo) => mudar(async () => {
    const ligado = campo.checked;
    await api.post("/api/sistema/inicializacao", { ativo: ligado });
    toast(ligado ? "O Fin Pro vai iniciar junto com o Windows." : "Inicialização automática desativada.", "ok");
    await atualizarAplicativo(); // a resposta traz só a inicialização, não o /api/app inteiro
  }),
  "aplicativo-minimizado": (campo) => mudar(async () => {
    const ligado = campo.checked;
    const app = await api.put("/api/app/preferencias", { minimizado_ao_iniciar: ligado });
    toast(ligado ? "Ao ligar o computador, o Fin Pro vai abrir só o ícone na bandeja."
      : "Ao ligar o computador, a janela do Fin Pro vai abrir normalmente.", "ok");
    redesenhar(chave, app);
  }),
  "aplicativo-bandeja": (campo) => mudar(async () => {
    const ligado = campo.checked;
    const app = await api.put("/api/app/preferencias", { fechar_para_bandeja: ligado });
    if (ligado) toast("O X agora esconde o Fin Pro na bandeja; os lembretes continuam.", "ok");
    else toast("O X agora encerra o Fin Pro: os lembretes param enquanto ele estiver fechado.", "aviso", { duracao: 7000 });
    redesenhar(chave, app);
  }),
};

export const acoes = {
  "aplicativo-atalhos": () => mudar(async () => {
    const r = await api.post("/api/app/atalhos");
    if (r?.criados?.length) toast("Atalhos criados na Área de Trabalho e no Menu Iniciar.", "ok", { duracao: 6000 });
    else toast("Nenhum atalho foi criado.", "aviso");
    // a resposta traz o /api/app inteiro (com atalhos.criados já atualizado)
    if (r?.atalhos) redesenhar(chave, r);
    else await atualizarAplicativo();
  }),
};

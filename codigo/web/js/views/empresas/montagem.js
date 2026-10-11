// Empresas e fechamentos · montagem da tela em abas e eventos.
import { icone } from "../../icons.js";
import { esc } from "../../ui.js";
import { abrirCheque, compensarCheque, formularioCheque, htmlCheques } from "./cheques.js";
import { carregarDados } from "./comum.js";
import { conferir, descartarItem, enviarArquivo, htmlConferencia } from "./conferencia.js";
import {
  adicionarChat, aoEnviarFormulario, htmlBot, liberarChat, procurarChats, removerDestinatario, trazerDosAvisos,
  verificarBot,
} from "./configbot.js";
import { ABAS, tela } from "./estado.js";
import { abrirFechamento, enviarFechamentos, formularioEmpresa, htmlFechamentos } from "./fechamentos.js";
import { editarNota, formularioNota, htmlNotas } from "./notas.js";
import { cancelarRecebimento, formularioRecebimento, htmlRecebimentos } from "./recebimentos.js";

export async function montar(el, params) {
  tela.raiz = el;
  tela.aba = ABAS.some(([chave]) => chave === params?.get("aba")) ? params.get("aba") : "fechamentos";
  el.innerHTML = `
    <nav class="alternar-modo sub-abas config-abas" role="tablist" aria-label="Seções de Empresas">
      ${ABAS.map(([chave, ic, rotulo]) => `<a role="tab" href="#/empresas?aba=${chave}" class="${chave === tela.aba ? "ativo" : ""}"
        aria-selected="${chave === tela.aba}">${icone(ic, 15)} ${esc(rotulo)}
        ${chave === "conferencia" ? `<span class="nav-contador info" data-contador-conferencia hidden></span>` : ""}</a>`).join("")}
    </nav>
    <div id="emp-conteudo"><div class="card esqueleto" style="height:220px"></div></div>`;

  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  el.addEventListener("submit", aoEnviar);
  window.addEventListener("empresas:atualizar", recarregar);

  await carregarDados().catch(() => null);
  if (tela.raiz !== el) return;
  await desenhar();

  const empresa = Number(params?.get("empresa"));
  if (empresa && tela.aba === "fechamentos") abrirFechamento(empresa, params.get("competencia") || "");
}

export function desmontar() {
  window.removeEventListener("empresas:atualizar", recarregar);
  tela.raiz?.removeEventListener("click", aoClicar);
  tela.raiz?.removeEventListener("change", aoAlterar);
  tela.raiz?.removeEventListener("submit", aoEnviar);
  tela.raiz = null;
  tela.fechamento = null;
}

async function desenhar() {
  const destino = tela.raiz?.querySelector("#emp-conteudo");
  if (!destino) return;
  const html = tela.aba === "notas" ? await htmlNotas()
    : tela.aba === "cheques" ? await htmlCheques()
      : tela.aba === "recebimentos" ? await htmlRecebimentos()
        : tela.aba === "conferencia" ? await htmlConferencia()
          : tela.aba === "bot" ? htmlBot()
            : htmlFechamentos();
  if (!tela.raiz) return;
  destino.innerHTML = html;
  atualizarContador();
  if (tela.aba === "fechamentos" && tela.empresaId) abrirFechamento(tela.empresaId, tela.competencia);
}

function atualizarContador() {
  const contador = tela.raiz?.querySelector("[data-contador-conferencia]");
  if (!contador) return;
  contador.textContent = tela.pendentes || "";
  contador.hidden = !tela.pendentes;
}

async function recarregar() {
  await carregarDados().catch(() => null);
  await desenhar();
}

// ------------------------------------------------------------------ eventos

async function aoClicar(e) {
  const cartao = e.target.closest("[data-empresa]");
  const botao = e.target.closest("[data-acao]");
  const acao = botao?.dataset.acao;

  if (acao === "nova-empresa") return formularioEmpresa();
  if (acao === "editar-empresa") {
    const empresa = (tela.dados?.cadastro || []).find((c) => c.id === Number(botao.dataset.empresaId));
    return empresa ? formularioEmpresa(empresa) : null;
  }
  if (acao === "ver-fechamento") return abrirFechamento(Number(botao.dataset.empresaId));
  if (acao === "enviar-fechamentos") return enviarFechamentos();
  if (acao === "nova-nota") return formularioNota();
  if (acao === "editar-nota") return editarNota(botao.dataset.id);
  if (acao === "novo-cheque") return formularioCheque();
  if (acao === "editar-cheque") return abrirCheque(botao.dataset.id);
  if (acao === "compensar-cheque") return compensarCheque(botao.dataset.id);
  if (acao === "novo-recebimento") return formularioRecebimento();
  if (acao === "cancelar-recebimento") return cancelarRecebimento(botao.dataset.id);
  if (acao === "conferir") return conferir(botao.dataset.id);
  if (acao === "descartar-item") return descartarItem(botao.dataset.id);
  if (acao === "verificar-bot") return verificarBot();
  if (acao === "procurar-chats") return procurarChats();
  if (acao === "adicionar-chat") return adicionarChat();
  if (acao === "remover-destinatario") return removerDestinatario(botao.dataset.chat);
  if (acao === "liberar-chat") return liberarChat(botao.dataset.chat, botao.dataset.nome);
  if (acao === "trazer-avisos") return trazerDosAvisos();
  if (acao === "enviar-arquivo") return tela.raiz?.querySelector("#emp-arquivo")?.click();
  if (cartao && !botao) {
    const empresa = (tela.dados?.cadastro || []).find((c) => c.nome === cartao.dataset.empresa);
    if (empresa) return abrirFechamento(empresa.id);
  }
  return null;
}

async function aoAlterar(e) {
  if (e.target.id === "emp-arquivo") {
    const arquivo = e.target.files[0];
    e.target.value = "";
    return enviarArquivo(arquivo);
  }
  if (e.target.dataset.campo === "competencia") {
    tela.competencia = e.target.value;  // o mês escolhido vale para a tela inteira
    await carregarDados().catch(() => null);
    return desenhar();
  }
  if (e.target.dataset.filtro) {
    if (e.target.dataset.filtro === "empresa") tela.filtroEmpresa = e.target.value;
    if (e.target.dataset.filtro === "status") tela.filtroStatus = e.target.value;
    return desenhar();
  }
  return null;
}

async function aoEnviar(e) {
  await aoEnviarFormulario(e);
}

/** Arquivo arrastado ou colado enquanto a tela de Empresas está aberta. */
export function receberArquivos(arquivos) {
  if (arquivos?.length) enviarArquivo(arquivos[0]);
}

// Caixa · montagem da tela em abas, escolha do período (dia, semana, mês, ano) e eventos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { esc, hojeISO, mensagemErro } from "../../ui.js";
import { carregarConferencia, descartarItem, htmlConferencia, lancarItem, revisarItem } from "./conferencia.js";
import { htmlBotCaixa, salvarBotCaixa, verificarBotCaixa } from "./configbot.js";
import { ABAS, PERIODOS, tela } from "./estado.js";
import {
  cancelarLancamento, editarLancamento, formularioLancamento, historicoLancamento, htmlMovimento,
} from "./movimento.js";
import { desenharGraficos, htmlRelatorios } from "./relatorios.js";

export async function montar(el, params) {
  tela.raiz = el;
  tela.aba = ABAS.some(([chave]) => chave === params?.get("aba")) ? params.get("aba") : "movimento";
  tela.data = tela.data || hojeISO();
  el.innerHTML = `
    <nav class="alternar-modo sub-abas config-abas" role="tablist" aria-label="Seções do caixa">
      ${ABAS.map(([chave, ic, rotulo]) => `<a role="tab" href="#/caixa?aba=${chave}" class="${chave === tela.aba ? "ativo" : ""}"
        aria-selected="${chave === tela.aba}">${icone(ic, 15)} ${esc(rotulo)}
        ${chave === "conferencia" ? `<span class="nav-contador info" data-contador-conferencia-caixa hidden></span>` : ""}</a>`).join("")}
    </nav>
    <div id="caixa-conteudo"><div class="card esqueleto" style="height:220px"></div></div>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("submit", aoEnviar);
  window.addEventListener("caixa:atualizar", desenhar);
  await desenhar();
}

export function desmontar() {
  window.removeEventListener("caixa:atualizar", desenhar);
  tela.raiz?.removeEventListener("click", aoClicar);
  tela.raiz?.removeEventListener("submit", aoEnviar);
  tela.raiz = null;
}

function barraPeriodo(d) {
  return `<section class="card barra-filtros caixa-periodo">
    <div class="alternar-modo" role="tablist" aria-label="Período">
      ${PERIODOS.map(([chave, rotulo]) => `<button role="tab" data-periodo="${chave}" class="${tela.periodo === chave ? "ativo" : ""}">${rotulo}</button>`).join("")}
    </div>
    <div class="caixa-navegar">
      <button class="btn-icone" data-navegar="${esc(d.periodo.anterior)}" title="Período anterior" aria-label="Período anterior">‹</button>
      <strong>${esc(d.periodo.rotulo)}</strong>
      <button class="btn-icone" data-navegar="${esc(d.periodo.seguinte)}" title="Próximo período" aria-label="Próximo período">›</button>
      <button class="btn btn-sm btn-fantasma" data-navegar="${hojeISO()}">Hoje</button>
    </div>
    <span class="espaco"></span>
    <button class="btn btn-sm" data-acao="nova-entrada">${icone("mais", 15)} Entrada</button>
    <button class="btn btn-sm btn-primario" data-acao="nova-saida">${icone("desfazer", 15)} Saída</button>
    <a class="btn btn-sm btn-fantasma" href="#/comprovantes?tipo=caixa" title="Buscar cupons e notas do caixa">${icone("clipe", 15)} Comprovantes</a>
    <a class="btn btn-sm btn-fantasma" href="/api/caixa/relatorio/arquivo?periodo=${tela.periodo}&data=${tela.data}">${icone("planilha", 15)} Excel</a>
  </section>`;
}

async function desenhar() {
  const destino = tela.raiz?.querySelector("#caixa-conteudo");
  if (!destino) return;
  try {
    const conferencia = await carregarConferencia();
    atualizarContador(conferencia.pendentes);
    if (tela.aba === "conferencia") {
      destino.innerHTML = htmlConferencia(conferencia);
      return;
    }
    if (tela.aba === "bot") {
      destino.innerHTML = htmlBotCaixa(conferencia.config || {});
      return;
    }
    tela.dados = await api.get(`/api/caixa?periodo=${tela.periodo}&data=${tela.data}`);
    if (!tela.raiz) return;
    const corpo = tela.aba === "relatorios" ? htmlRelatorios(tela.dados) : htmlMovimento(tela.dados);
    destino.innerHTML = barraPeriodo(tela.dados) + corpo;
    if (tela.aba === "relatorios") desenharGraficos(destino, tela.dados);
  } catch (erro) {
    destino.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar o caixa</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

function atualizarContador(pendentes) {
  const contador = tela.raiz?.querySelector("[data-contador-conferencia-caixa]");
  if (contador) {
    contador.textContent = pendentes || "";
    contador.hidden = !pendentes;
  }
  window.dispatchEvent(new CustomEvent("caixa:contagem", { detail: pendentes || 0 }));
}

async function aoClicar(e) {
  const periodo = e.target.closest("[data-periodo]");
  if (periodo) {
    tela.periodo = periodo.dataset.periodo;
    return desenhar();
  }
  const navegar = e.target.closest("[data-navegar]");
  if (navegar) {
    tela.data = String(navegar.dataset.navegar).slice(0, 10);
    return desenhar();
  }
  const filtro = e.target.closest("[data-filtro-caixa]");
  if (filtro) {
    tela.filtro = filtro.dataset.filtroCaixa;
    return desenhar();
  }
  const botao = e.target.closest("[data-acao]");
  const acao = botao?.dataset.acao;
  if (acao === "nova-entrada") return formularioLancamento(null, "Entrada");
  if (acao === "nova-saida") return formularioLancamento(null, "Saída");
  if (acao === "editar-caixa") return editarLancamento(botao.dataset.id);
  if (acao === "cancelar-caixa") return cancelarLancamento(botao.dataset.id);
  if (acao === "historico-caixa") return historicoLancamento(botao.dataset.id);
  if (acao === "revisar-caixa") return revisarItem(botao.dataset.id);
  if (acao === "lancar-caixa") return lancarItem(botao.dataset.id);
  if (acao === "descartar-caixa") return descartarItem(botao.dataset.id);
  if (acao === "verificar-bot-caixa") return verificarBotCaixa();
  return null;
}

async function aoEnviar(e) {
  if (e.target.matches("[data-form-bot-caixa]")) {
    e.preventDefault();
    await salvarBotCaixa(e.target);
  }
}

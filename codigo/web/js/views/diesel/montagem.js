// Diesel · montagem da tela em abas, escolha do período (semana, quinzena, mês, ano) e eventos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { esc, hojeISO, mensagemErro } from "../../ui.js";
import { carregarConferencia, conferir, descartar, htmlConferencia } from "./conferencia.js";
import { htmlBotDiesel, salvarBotDiesel, verificarBotDiesel } from "./configbot.js";
import { ABAS, PERIODOS, tela } from "./estado.js";
import {
  carregarMaquinas, formularioCanhoto, formularioCompra, formularioMaquina, formularioPrecos, lerArquivo,
} from "./formularios.js";
import { htmlMaquinas } from "./maquinas.js";
import { cancelar, editar, historico, htmlPainel } from "./painel.js";
import { desenharGraficoDiesel, enviarRelatorio, escolherNivel, htmlRelatorios, relatorio } from "./relatorios.js";

export async function montar(el, params) {
  tela.raiz = el;
  tela.aba = ABAS.some(([chave]) => chave === params?.get("aba")) ? params.get("aba") : "painel";
  tela.data = tela.data || hojeISO();
  el.innerHTML = `
    <nav class="alternar-modo sub-abas config-abas" role="tablist" aria-label="Seções do diesel">
      ${ABAS.map(([chave, ic, rotulo]) => `<a role="tab" href="#/diesel?aba=${chave}" class="${chave === tela.aba ? "ativo" : ""}"
        aria-selected="${chave === tela.aba}">${icone(ic, 15)} ${esc(rotulo)}
        ${chave === "conferencia" ? `<span class="nav-contador info" data-contador-conferencia-diesel hidden></span>` : ""}</a>`).join("")}
    </nav>
    <div id="diesel-conteudo"><div class="card esqueleto" style="height:220px"></div></div>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("submit", aoEnviar);
  el.addEventListener("change", aoEscolherArquivo);
  window.addEventListener("arquivos:soltos", aoSoltar);
  document.body.dataset.soltar = "Solte para ler o canhoto ou o comprovante";
  window.addEventListener("diesel:atualizar", desenhar);
  await desenhar();
}

export function desmontar() {
  window.removeEventListener("diesel:atualizar", desenhar);
  tela.raiz?.removeEventListener("click", aoClicar);
  tela.raiz?.removeEventListener("submit", aoEnviar);
  tela.raiz?.removeEventListener("change", aoEscolherArquivo);
  window.removeEventListener("arquivos:soltos", aoSoltar);
  delete document.body.dataset.soltar;
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
    <label class="btn btn-sm btn-primario" title="Foto ou PDF do canhoto ou do comprovante: o sistema lê e você só confere">
      ${icone("upload", 15)} Enviar canhoto ou comprovante
      <input type="file" accept="application/pdf,image/*,.heic,.heif" data-arquivo-diesel hidden></label>
    <button class="btn btn-sm" data-acao="novo-abastecimento">${icone("diesel", 15)} Abastecimento</button>
    <button class="btn btn-sm" data-acao="nova-compra">${icone("mais", 15)} Compra</button>
    <a class="btn btn-sm btn-fantasma" href="#/comprovantes?tipo=diesel" title="Buscar canhotos e comprovantes do diesel">${icone("clipe", 15)} Comprovantes</a>
    <a class="btn btn-sm btn-fantasma" href="/api/diesel/relatorio/arquivo?periodo=${tela.periodo}&data=${tela.data}">${icone("planilha", 15)} Excel</a>
  </section>`;
}

async function desenhar() {
  const destino = tela.raiz?.querySelector("#diesel-conteudo");
  if (!destino) return;
  try {
    const conferencia = await carregarConferencia();
    atualizarContador(conferencia.pendentes);
    if (tela.aba === "conferencia") {
      destino.innerHTML = htmlConferencia(conferencia);
      return;
    }
    if (tela.aba === "bot") {
      destino.innerHTML = htmlBotDiesel(conferencia.config || {});
      return;
    }
    if (tela.aba === "maquinas") {
      destino.innerHTML = htmlMaquinas(await carregarMaquinas());
      return;
    }
    const caminho = tela.aba === "relatorios" ? "/api/diesel/relatorio" : "/api/diesel";
    tela.dados = await api.get(`${caminho}?periodo=${tela.periodo}&data=${tela.data}`);
    if (!tela.raiz) return;
    pintar();
  } catch (erro) {
    destino.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar o diesel</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

/** Redesenha com os dados já carregados (trocar o nível ou o filtro do relatório não precisa ir ao servidor). */
function pintar() {
  const destino = tela.raiz?.querySelector("#diesel-conteudo");
  if (!destino || !tela.dados) return;
  const rolagem = window.scrollY;
  destino.innerHTML = barraPeriodo(tela.dados) + (tela.aba === "relatorios" ? htmlRelatorios(tela.dados) : htmlPainel(tela.dados));
  if (tela.aba === "relatorios") desenharGraficoDiesel(destino, tela.dados);
  window.scrollTo({ top: rolagem });
}

function atualizarContador(pendentes) {
  const contador = tela.raiz?.querySelector("[data-contador-conferencia-diesel]");
  if (contador) {
    contador.textContent = pendentes || "";
    contador.hidden = !pendentes;
  }
  window.dispatchEvent(new CustomEvent("diesel:contagem", { detail: pendentes || 0 }));
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
  const botao = e.target.closest("[data-acao]");
  const d = botao?.dataset || {};
  switch (d.acao) {
    case "nova-compra": return formularioCompra();
    case "novo-abastecimento": return formularioCanhoto();
    case "precos-diesel": return formularioPrecos();
    case "editar-diesel": return editar(d.aba, d.id);
    case "cancelar-diesel": return cancelar(d.aba, d.id);
    case "historico-diesel": return historico(d.aba, d.id);
    case "nova-maquina": return formularioMaquina();
    case "editar-maquina": return formularioMaquina(tela.maquinas.find((m) => m.id === Number(d.id)));
    case "conferir-canhoto": return conferir(d.id, "canhoto");
    case "conferir-compra": return conferir(d.id, "compra");
    case "descartar-diesel": return descartar(d.id);
    case "enviar-relatorio-diesel": return enviarRelatorio(tela);
    case "nivel-relatorio":
      escolherNivel(d.nivel);
      return pintar();
    case "limpar-filtro-diesel":
      relatorio.maquina = "";
      relatorio.combustivel = "";
      return pintar();
    case "verificar-bot-diesel": return verificarBotDiesel();
    default: return null;
  }
}

function aoEscolherArquivo(e) {
  const filtro = e.target.closest("[data-filtro-diesel]");
  if (filtro) {
    relatorio[filtro.dataset.filtroDiesel] = filtro.value;
    pintar();
    return;
  }
  if (!e.target.matches("[data-arquivo-diesel]")) return;
  const arquivo = e.target.files?.[0];
  e.target.value = "";
  lerArquivo(arquivo);
}

function aoSoltar(e) {  // arquivo arrastado para a tela do diesel: é canhoto ou comprovante, não boleto
  const arquivo = e.detail?.[0];
  if (!arquivo) return;
  e.preventDefault();
  lerArquivo(arquivo);
}

async function aoEnviar(e) {
  if (e.target.matches("[data-form-bot-diesel]")) {
    e.preventDefault();
    await salvarBotDiesel(e.target);
  }
}

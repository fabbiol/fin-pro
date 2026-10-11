// Pagamentos Pix · montagem da tela, leitura de QR code e Copia e Cola.
import { abrirDetalhes } from "../../detalhes.js";
import { api } from "../../api.js";
import { NOVO_CENTRO, carregarCentros, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, hojeISO, mensagemErro, numeroBR, parseValor,
  seloSituacao, toast, uid,
} from "../../ui.js";
import { CHIPS, filtros, tela } from "./estado.js";
import { avisarLido, criarFormulario } from "./formulario.js";
import { aoClicarTabela, carregar, confirmarPagamento, linha } from "./lista.js";

export async function montar(el, params) {
  tela.raiz = el;
  if (params.has("q") || params.has("situacao") || params.has("centro")) {
    filtros.q = params.get("q") || "";
    filtros.situacao = params.get("situacao") || "";
    filtros.centro = params.get("centro") || "";
    filtros.pagina = 1;
  }
  el.innerHTML = `
    <section class="pix-topo">
      <div class="card pix-card">
        <h3>${icone("pix", 18)} Novo pagamento Pix</h3>
        <div id="pix-formulario"><div class="esqueleto" style="height:320px"></div></div>
      </div>
      <div class="card pix-card pix-colar">
        <h3>${icone("qrcode", 18)} Pix Copia e Cola ou QR code</h3>
        <p class="sutil">Recebeu o código ou o QR code do Pix? Cole o código ou envie a imagem: tipo e chave, valor e recebedor são preenchidos sozinhos.</p>
        <textarea id="pix-codigo" class="input mono" placeholder="Cole aqui o Pix Copia e Cola (começa com 000201…)" spellcheck="false"></textarea>
        <div class="linha-botoes"><button class="btn btn-primario" data-acao="ler-codigo">${icone("check", 16)} Ler código</button></div>
        <input type="file" id="pix-arquivo" accept="image/*,application/pdf,.heic,.heif" hidden>
        <div class="pix-qr-envio" data-acao="enviar-qr" role="button" tabindex="0">${icone("upload", 22)}
          <div><strong>Enviar imagem do QR code</strong><div class="sutil">Print, foto ou PDF · também dá para arrastar ou colar (Ctrl+V)</div></div></div>
      </div>
    </section>

    <section class="card barra-filtros">
      <div class="filtros-linha">
        <label class="busca">${icone("busca", 16)}
          <input id="p-busca" class="input" type="search" value="${esc(filtros.q)}" placeholder="Buscar recebedor, chave, descrição ou centro de custo"></label>
        <select id="p-centro" class="input input-sm filtro-centro" aria-label="Centro de custo">
          <option value="">Todos os centros de custo</option>${filtros.centro ? `<option value="${esc(filtros.centro)}" selected>${esc(filtros.centro)}</option>` : ""}</select>
        <a class="btn" href="#/comprovantes?tipo=pix" title="Buscar os comprovantes dos Pix">${icone("clipe", 16)} Comprovantes</a>
        <div class="menu-ancora">
          <button class="btn" id="p-exportar" aria-haspopup="menu">${icone("download", 16)} Exportar</button>
          <div class="menu" id="p-menu-exportar" role="menu" hidden>
            <button data-formato="xlsx">${icone("planilha", 16)}<span>Excel<small>Somente os Pix filtrados</small></span></button>
            <button data-formato="csv">${icone("arquivo", 16)}<span>CSV<small>Separado por ponto e vírgula</small></span></button>
          </div>
        </div>
      </div>
      <div class="filtros-linha">
        <div class="chips-situacao" id="p-chips">${CHIPS.map(([valor, rotulo]) => `<button class="chip-filtro" data-situacao="${valor}">${rotulo}</button>`).join("")}</div>
      </div>
    </section>

    <section class="resumo-lista" id="p-resumo"></section>
    <section class="card tabela-card">
      <div class="acoes-lote" id="p-acoes" hidden></div>
      <div class="tabela-wrap" id="p-tabela"><div style="padding:18px">${'<div class="esqueleto" style="height:44px;margin-bottom:8px"></div>'.repeat(4)}</div></div>
      <footer class="paginacao" id="p-paginacao"></footer>
    </section>`;

  ligarEventos();
  sincronizarChips();
  const centros = await carregarCentros().catch(() => []);
  if (tela.raiz !== el) return;
  el.querySelector("#p-centro").innerHTML = opcoesFiltroCentro(centros, filtros.centro);
  tela.formularioPrincipal = criarFormulario(el.querySelector("#pix-formulario"), { centros, aoSalvar: () => carregar() });
  await carregar();

  if (tela.codigoPendente) {
    const texto = tela.codigoPendente;
    tela.codigoPendente = null;
    tela.formularioPrincipal.lerCodigo(texto);
  }
  if (tela.arquivosPendentes) {
    const lista = tela.arquivosPendentes;
    tela.arquivosPendentes = null;
    processarArquivo(lista[0]);
  }
  const pagar = Number(params.get("pagar"));
  if (pagar) {
    history.replaceState(null, "", "#/pix");
    confirmarPagamento(pagar);
  }
}

export function desmontar() {
  document.removeEventListener("click", fecharMenuFora);
  window.removeEventListener("pix:atualizar", recarregarExterno);
  tela.raiz = null;
  tela.formularioPrincipal = null;
}

/** Texto "Pix Copia e Cola" colado em qualquer tela. */

export function receberCopiaECola(texto) {
  if (tela.raiz && tela.formularioPrincipal) tela.formularioPrincipal.lerCodigo(texto);
  else tela.codigoPendente = texto;
}

/** Imagem/PDF solto ou colado enquanto a aba Pix está aberta. */

export function lerArquivos(arquivos) {
  if (!arquivos?.length) return;
  if (tela.raiz && tela.formularioPrincipal) processarArquivo(arquivos[0]);
  else tela.arquivosPendentes = arquivos;
}

export const recarregarExterno = () => carregar();

export function fecharMenuFora(e) {
  const menu = tela.raiz?.querySelector("#p-menu-exportar");
  if (menu && !menu.hidden && !e.target.closest(".menu-ancora")) menu.hidden = true;
}

export function sincronizarChips() {
  tela.raiz.querySelectorAll("[data-situacao]").forEach((b) => b.classList.toggle("ativo", b.dataset.situacao === filtros.situacao));
}

export function ligarEventos() {
  document.addEventListener("click", fecharMenuFora);
  window.addEventListener("pix:atualizar", recarregarExterno);
  const recarregar = () => { filtros.pagina = 1; carregar(); };

  tela.raiz.querySelector("#p-busca").addEventListener("input", debounce((e) => { filtros.q = e.target.value; recarregar(); }, 280));
  tela.raiz.querySelector("#p-centro").addEventListener("change", (e) => { filtros.centro = e.target.value; recarregar(); });
  tela.raiz.querySelector("#p-chips").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-situacao]");
    if (!chip) return;
    filtros.situacao = chip.dataset.situacao;
    sincronizarChips();
    recarregar();
  });

  const menu = tela.raiz.querySelector("#p-menu-exportar");
  tela.raiz.querySelector("#p-exportar").addEventListener("click", () => { menu.hidden = !menu.hidden; });
  menu.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-formato]");
    if (!botao) return;
    menu.hidden = true;
    const url = new URL("/api/pix/exportar", location.origin);
    const { pagina, por_pagina: porPagina, ...params } = filtros;
    Object.entries({ ...params, formato: botao.dataset.formato }).forEach(([k, v]) => { if (v) url.searchParams.set(k, v); });
    window.location.href = url.toString();
  });

  const codigo = tela.raiz.querySelector("#pix-codigo");
  tela.raiz.querySelector("[data-acao='ler-codigo']").addEventListener("click", () => lerCodigoDaCaixa());
  codigo.addEventListener("paste", () => setTimeout(() => { if (codigo.value.trim().startsWith("000201")) lerCodigoDaCaixa(); }, 0));

  const entradaArquivo = tela.raiz.querySelector("#pix-arquivo");
  const caixa = tela.raiz.querySelector(".pix-qr-envio");
  caixa.addEventListener("click", () => entradaArquivo.click());
  caixa.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); entradaArquivo.click(); } });
  entradaArquivo.addEventListener("change", () => {
    processarArquivo(entradaArquivo.files[0]);
    entradaArquivo.value = "";
  });

  tela.raiz.querySelector("#p-tabela").addEventListener("click", aoClicarTabela);
  tela.raiz.querySelector("#p-paginacao").addEventListener("click", (e) => {
    const botao = e.target.closest("[data-pagina]");
    if (!botao || botao.disabled) return;
    filtros.pagina = Number(botao.dataset.pagina);
    carregar();
  });
  tela.raiz.querySelector("#p-paginacao").addEventListener("change", (e) => {
    if (e.target.id === "p-por-pagina") { filtros.por_pagina = Number(e.target.value); filtros.pagina = 1; carregar(); }
  });
}

export async function lerCodigoDaCaixa() {
  const caixa = tela.raiz?.querySelector("#pix-codigo");
  const texto = caixa?.value.trim();
  if (!texto) {
    toast("Cole o código Pix Copia e Cola.", "aviso");
    caixa?.focus();
    return;
  }
  if (await tela.formularioPrincipal?.lerCodigo(texto)) {
    caixa.value = "";
    tela.raiz?.querySelector("#pix-formulario")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

export async function processarArquivo(arquivo) {
  if (!arquivo || !tela.raiz) return;
  const caixa = tela.raiz.querySelector(".pix-qr-envio");
  const original = caixa.innerHTML;
  caixa.classList.add("carregando");
  caixa.innerHTML = `<span class="spinner"></span><div><strong>Procurando QR code…</strong><div class="sutil">${esc(arquivo.name || "imagem colada")}</div></div>`;
  try {
    const resposta = await api.enviarPara("/api/pix/ler-arquivo", arquivo);
    if (!resposta.pix.length) {
      toast("Nenhum QR code Pix encontrado neste arquivo. Tente uma imagem mais nítida ou cole o código.", "aviso", { duracao: 7000 });
      return;
    }
    const escolhido = resposta.pix.length === 1 ? resposta.pix[0] : await escolherPix(resposta.pix);
    if (!escolhido || !tela.formularioPrincipal) return;
    tela.formularioPrincipal.preencher(escolhido, { arquivoId: resposta.arquivo?.id });
    avisarLido(escolhido);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  } finally {
    if (tela.raiz?.contains(caixa)) {
      caixa.innerHTML = original;
      caixa.classList.remove("carregando");
    }
  }
}

export function escolherPix(lista) {
  return new Promise((resolve) => {
    let respondido = false;
    const { el, fechar } = abrirModal({
      titulo: `${lista.length} QR codes Pix encontrados`,
      corpo: `<p class="sutil" style="margin-bottom:10px">Escolha qual deseja lançar.</p>
        <ul class="lista-mini">${lista.map((p, i) => `<li>
          <div class="info"><div class="titulo">${esc(p.recebedor || "Recebedor não informado")}</div>
            <div class="sutil">${esc(p.chave_formatada || "sem chave")}${p.duplicado ? " · já lançado" : ""}</div></div>
          <div class="valor">${p.valor ? brl(p.valor) : "—"}</div>
          <button class="btn btn-sm btn-primario" data-escolher="${i}">Usar</button></li>`).join("")}</ul>`,
      aoFechar: () => { if (!respondido) resolve(null); },
    });
    el.addEventListener("click", (e) => {
      const botao = e.target.closest("[data-escolher]");
      if (!botao) return;
      respondido = true;
      resolve(lista[Number(botao.dataset.escolher)]);
      fechar(true);
    });
  });
}

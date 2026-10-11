// Tela: Comprovantes — acha o comprovante de boletos, Pix, cheques, recebimentos, caixa e notas fiscais.
import { api } from "../api.js";
import { carregarCentros } from "../centros.js";
import { anexarComprovante } from "../detalhes.js";
import { pode } from "../estado.js";
import { icone } from "../icons.js";
import { abrirModal, brl, dataBR, debounce, esc, hojeISO, isoDeData, mensagemErro, parseValor, toast } from "../ui.js";

const ICONE_TIPO = { boleto: "boleto", pix: "pix", cheque: "cartao", recebimento: "carteira", caixa: "caixa", nota: "relatorio", diesel: "diesel" };
const ROTULO_NUMERO = { boleto: "Doc.", pix: "TXID", cheque: "Cheque nº", recebimento: "ID", caixa: "", nota: "NF", diesel: "Nº" };
const SITUACOES = [["com", "Com comprovante"], ["sem", "Pagos sem comprovante"], ["todos", "Todos os lançamentos"]];
const PERIODOS = [["", "Período rápido…"], ["hoje", "Hoje"], ["semana", "Esta semana"], ["mes", "Este mês"],
  ["mes_passado", "Mês passado"], ["30", "Últimos 30 dias"], ["90", "Últimos 90 dias"], ["ano", "Este ano"], ["limpar", "Qualquer data"]];

const filtros = { q: "", tipos: [], de: "", ate: "", valor: "", valor_min: "", valor_max: "", numero: "", centro: "",
  pessoa: "", comprovante: "com", ordenar: "data", direcao: "desc", pagina: 1 };
let raiz = null;
let ultimo = null;
let requisicao = 0;
let maisFiltros = false;

export async function montar(el, params) {
  raiz = el;
  if (params.has("tipo") || params.has("q")) {
    Object.assign(filtros, { q: params.get("q") || "", tipos: (params.get("tipo") || "").split(",").filter(Boolean),
      de: "", ate: "", valor: "", valor_min: "", valor_max: "", numero: params.get("numero") || "", pessoa: "",
      centro: "", comprovante: params.get("comprovante") || "com", pagina: 1 });
  }
  el.innerHTML = `
    <section class="card barra-filtros comp-filtros">
      <div class="filtros-linha">
        <label class="busca">${icone("busca", 16)}
          <input id="c-busca" class="input" type="search" value="${esc(filtros.q)}" autocomplete="off"
            placeholder="Buscar por beneficiário, empresa, recebedor, pedido, material…  ( / )"></label>
        <select id="c-situacao" class="input input-sm" aria-label="Quais lançamentos">
          ${SITUACOES.map(([v, r]) => `<option value="${v}" ${filtros.comprovante === v ? "selected" : ""}>${r}</option>`).join("")}</select>
        <button class="btn" data-acao="mais-filtros" aria-expanded="${maisFiltros}">${icone("ordenar", 15)} Mais filtros</button>
        <a class="btn btn-primario" id="c-zip" href="#" title="Baixa num arquivo .zip todos os comprovantes encontrados com estes filtros">
          ${icone("download", 16)} Baixar comprovantes (.zip)</a>
      </div>
      <div class="filtros-linha">
        <div class="chips-situacao" id="c-tipos"></div>
      </div>
      <div class="filtros-linha comp-campos">
        <div class="periodo">${icone("calendario", 16)}
          <input type="date" id="c-de" class="input input-sm" value="${esc(filtros.de)}" aria-label="De">
          <span>até</span>
          <input type="date" id="c-ate" class="input input-sm" value="${esc(filtros.ate)}" aria-label="Até">
          <select id="c-rapido" class="input input-sm" aria-label="Período rápido">
            ${PERIODOS.map(([v, r]) => `<option value="${v}">${r}</option>`).join("")}</select>
        </div>
        <label class="comp-campo">Valor <input id="c-valor" class="input input-sm" inputmode="decimal" value="${esc(filtros.valor)}" placeholder="ex.: 956,70"></label>
        <label class="comp-campo">Nº <input id="c-numero" class="input input-sm" value="${esc(filtros.numero)}" placeholder="cheque, NF, pedido, documento"></label>
      </div>
      <div class="filtros-linha comp-campos" id="c-mais" ${maisFiltros ? "" : "hidden"}>
        <label class="comp-campo">Valor de <input id="c-valor-min" class="input input-sm" inputmode="decimal" value="${esc(filtros.valor_min)}" placeholder="mínimo"></label>
        <label class="comp-campo">até <input id="c-valor-max" class="input input-sm" inputmode="decimal" value="${esc(filtros.valor_max)}" placeholder="máximo"></label>
        <select id="c-centro" class="input input-sm filtro-centro" aria-label="Centro de custo">
          <option value="">Todos os centros de custo</option></select>
        <label class="comp-campo">Quem <input id="c-pessoa" class="input input-sm" value="${esc(filtros.pessoa)}" placeholder="pagou / lançou"></label>
        <select id="c-ordenar" class="input input-sm" aria-label="Ordenar">
          <option value="data|desc">Mais recentes primeiro</option><option value="data|asc">Mais antigos primeiro</option>
          <option value="valor|desc">Maior valor</option><option value="valor|asc">Menor valor</option>
          <option value="nome|asc">Nome (A–Z)</option></select>
        <button class="btn btn-sm btn-fantasma" data-acao="limpar">${icone("x", 14)} Limpar filtros</button>
      </div>
    </section>
    <section class="resumo-lista comp-resumo" id="c-resumo"></section>
    <section class="card tabela-card">
      <div class="tabela-wrap" id="c-tabela"><div style="padding:18px">${'<div class="esqueleto" style="height:44px;margin-bottom:8px"></div>'.repeat(6)}</div></div>
      <div class="paginacao" id="c-paginacao"></div>
    </section>`;
  el.querySelector("#c-ordenar").value = `${filtros.ordenar}|${filtros.direcao}`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("input", aoDigitar);
  el.addEventListener("change", aoAlterar);
  document.addEventListener("keydown", atalhoBusca);
  carregarCentros().then((centros) => {
    const select = raiz?.querySelector("#c-centro");
    if (!select) return;
    select.innerHTML = `<option value="">Todos os centros de custo</option>`
      + centros.map((c) => `<option value="${esc(c.nome)}" ${c.nome === filtros.centro ? "selected" : ""}>${esc(c.nome)}</option>`).join("");
  }).catch(() => {});
  await carregar();
}

export function desmontar() {
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("input", aoDigitar);
  raiz?.removeEventListener("change", aoAlterar);
  document.removeEventListener("keydown", atalhoBusca);
  raiz = null;
}

function atalhoBusca(e) {
  if (e.key === "/" && !e.target.closest("input, textarea, select")) {
    e.preventDefault();
    raiz?.querySelector("#c-busca")?.focus();
  }
}

// ------------------------------------------------------------------ dados

function parametros(extra = {}) {
  const p = { ...extra };
  if (filtros.q) p.q = filtros.q;
  if (filtros.tipos.length) p.tipos = filtros.tipos.join(",");
  for (const campo of ["de", "ate", "numero", "centro", "pessoa"]) if (filtros[campo]) p[campo] = filtros[campo];
  if (filtros.valor) p.valor = filtros.valor;
  for (const campo of ["valor_min", "valor_max"]) {
    const numero = parseValor(filtros[campo]);
    if (filtros[campo] && !Number.isNaN(numero)) p[campo] = numero;
  }
  p.ordenar = filtros.ordenar;
  p.direcao = filtros.direcao;
  return p;
}

async function carregar() {
  if (!raiz) return;
  const minha = ++requisicao;
  raiz.querySelector("#c-tabela")?.classList.add("carregando");
  atualizarLinkZip();
  try {
    const dados = await api.get("/api/comprovantes/busca", parametros({ comprovante: filtros.comprovante, pagina: filtros.pagina, por_pagina: 100 }));
    if (!raiz || minha !== requisicao) return;
    ultimo = dados;
    desenharTipos(dados.tipos);
    desenharResumo(dados.resumo);
    desenharTabela(dados.itens);
    desenharPaginacao(dados);
  } catch (erro) {
    if (!raiz) return;
    raiz.querySelector("#c-tabela").innerHTML = `<div class="vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível buscar os comprovantes</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  } finally {
    raiz?.querySelector("#c-tabela")?.classList.remove("carregando");
  }
}

const recarregar = debounce(() => { filtros.pagina = 1; carregar(); }, 350);

function atualizarLinkZip() {
  const link = raiz?.querySelector("#c-zip");
  if (!link) return;
  link.href = `/api/comprovantes/busca/zip?${new URLSearchParams(parametros())}`;
  link.toggleAttribute("hidden", filtros.comprovante === "sem");
}

// ------------------------------------------------------------------ desenho

function desenharTipos(tipos) {
  const alvo = raiz.querySelector("#c-tipos");
  const todos = !filtros.tipos.length;
  alvo.innerHTML = `<button class="chip-filtro ${todos ? "ativo" : ""}" data-tipo="">Tudo</button>`
    + tipos.map((t) => `<button class="chip-filtro ${filtros.tipos.includes(t.tipo) ? "ativo" : ""}" data-tipo="${t.tipo}">
        ${icone(ICONE_TIPO[t.tipo], 13)} ${esc(t.rotulo)}</button>`).join("");
}

function desenharResumo(r) {
  const semArquivo = filtros.comprovante === "sem";
  raiz.querySelector("#c-resumo").innerHTML = `
    <div class="card resumo-item"><span>${semArquivo ? "Pagos sem comprovante" : "Encontrados"}</span><strong>${r.quantidade}</strong></div>
    <div class="card resumo-item"><span>Valor somado</span><strong>${brl(r.valor)}</strong></div>
    ${semArquivo ? "" : `<div class="card resumo-item ok"><span>Com arquivo</span><strong>${r.com_arquivo}</strong></div>`}
    ${r.por_tipo.map((t) => `<div class="card resumo-item"><span>${icone(ICONE_TIPO[t.tipo], 12)} ${esc(t.rotulo)}</span>
      <strong>${t.quantidade} <small class="sutil">· ${brl(t.valor)}</small></strong></div>`).join("")}`;
}

function linkLancamento(i) {
  const q = encodeURIComponent(i.nome || "");
  return {
    boleto: `#/boletos?q=${q}`, pix: `#/pix?q=${q}`, cheque: "#/empresas?aba=cheques", recebimento: "#/empresas?aba=recebimentos",
    caixa: "#/caixa", nota: `#/empresas?aba=notas&q=${encodeURIComponent(i.numero || "")}`, diesel: "#/diesel",
  }[i.tipo];
}

function celulaValor(i) {
  const pago = i.valor_pago && Math.abs(i.valor_pago - i.valor) >= 0.01;
  return `<td class="num" data-rotulo="Valor"><strong>${brl(i.valor)}</strong>
    ${pago ? `<small class="valor-pago-linha">pago ${brl(i.valor_pago)}</small>` : ""}
    ${i.juros_multa ? `<small class="juros-linha">+ ${brl(i.juros_multa)} juros</small>` : ""}</td>`;
}

function desenharTabela(itens) {
  const alvo = raiz.querySelector("#c-tabela");
  if (!itens.length) {
    const sem = filtros.comprovante === "sem";
    alvo.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone(sem ? "check" : "busca", 26)}</div>
      <h3>${sem ? "Nenhum pagamento sem comprovante" : "Nenhum comprovante encontrado"}</h3>
      <p>${sem ? "Tudo o que foi pago nestes filtros tem comprovante anexado." : "Mude a busca ou limpe os filtros."}</p>
      ${sem ? "" : `<button class="btn" data-acao="limpar">Limpar filtros</button>`}</div>`;
    return;
  }
  alvo.innerHTML = `<table class="tabela comp-tabela"><thead><tr>
      <th>Data</th><th>Tipo</th><th>Beneficiário / empresa</th><th>Número</th><th class="num">Valor</th><th>Centro de custo</th><th>Quem</th>
      <th class="col-acoes">Comprovante</th></tr></thead>
    <tbody>${itens.map((i, indice) => `<tr data-indice="${indice}" class="${i.comprovante_id ? "comp-clicavel" : ""}">
      <td data-rotulo="Data"><strong>${dataBR(i.data)}</strong>${i.tipo === "cheque" && i.vencimento && i.vencimento !== i.data ? `<small class="sutil">bom para ${dataBR(i.vencimento)}</small>` : ""}</td>
      <td data-rotulo="Tipo"><span class="chip comp-tipo-${i.tipo}">${icone(ICONE_TIPO[i.tipo], 12)} ${esc(i.tipo_rotulo)}</span>
        ${i.situacao && i.situacao !== "Pago" && i.situacao !== "Confirmado" ? `<small class="sutil">${esc(i.situacao)}</small>` : ""}</td>
      <td data-rotulo="Nome" class="celula-benef"><strong title="${esc(i.nome)}">${esc(i.nome || "—")}</strong><span>${esc(i.detalhe || "")}</span></td>
      <td data-rotulo="Número">${i.numero ? `<span class="mono">${ROTULO_NUMERO[i.tipo] ? `<small class="sutil">${ROTULO_NUMERO[i.tipo]}</small> ` : ""}${esc(i.numero)}</span>` : `<span class="sutil">—</span>`}</td>
      ${celulaValor(i)}
      <td data-rotulo="Centro de custo">${i.centro_custo ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(i.centro_custo)}</span>` : ""}</td>
      <td data-rotulo="Quem">${esc(i.pessoa || "")}</td>
      <td class="col-acoes">${acoes(i, indice)}</td></tr>`).join("")}</tbody></table>`;
}

function acoes(i, indice) {
  const botoes = [];
  if (i.comprovante_id) {
    botoes.push(`<button class="btn btn-sm" data-ver="${indice}" title="Ver o comprovante">${icone("olho", 14)} Ver</button>`,
      `<a class="btn-icone" href="/api/arquivos/${esc(i.comprovante_id)}" download="${esc(i.comprovante_nome || "comprovante")}" title="Baixar o comprovante">${icone("download", 15)}</a>`);
  } else if ((i.tipo === "boleto" || i.tipo === "pix") && pode("pagar")) {
    botoes.push(`<button class="btn btn-sm" data-anexar="${indice}" title="Anexar o comprovante deste pagamento">${icone("clipe", 14)} Anexar</button>`);
  } else {
    botoes.push(`<span class="chip">Sem arquivo</span>`);
  }
  if (i.original_id) {
    botoes.push(`<a class="btn-icone" href="/api/arquivos/${esc(i.original_id)}" target="_blank" rel="noopener" title="Ver o ${i.tipo === "pix" ? "arquivo da cobrança" : "boleto original"}">${icone("arquivo", 15)}</a>`);
  }
  botoes.push(`<a class="btn-icone" href="${linkLancamento(i)}" title="Abrir o lançamento">${icone("externo", 15)}</a>`);
  return `<div class="comp-acoes">${botoes.join("")}</div>`;
}

function desenharPaginacao({ total, pagina, por_pagina: porPagina }) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  const inicio = total ? (pagina - 1) * porPagina + 1 : 0;
  const fim = Math.min(total, pagina * porPagina);
  raiz.querySelector("#c-paginacao").innerHTML = `<span>${inicio}–${fim} de ${total}</span>
    <div class="controles">
      <button class="btn btn-sm" data-pagina="${pagina - 1}" ${pagina <= 1 ? "disabled" : ""}>‹ Anterior</button>
      <span class="sutil">página ${pagina} de ${paginas}</span>
      <button class="btn btn-sm" data-pagina="${pagina + 1}" ${pagina >= paginas ? "disabled" : ""}>Próxima ›</button></div>`;
}

// ------------------------------------------------------------------ visualizar

function abrirComprovante(indice) {
  const itens = ultimo?.itens || [];
  let atual = indice;
  const conteudo = (i) => {
    const arquivo = `/api/arquivos/${encodeURIComponent(i.comprovante_id)}`;
    const visual = i.comprovante_pdf
      ? `<iframe class="comp-previa" src="${arquivo}" title="Comprovante"></iframe>`
      : `<a href="${arquivo}" target="_blank" rel="noopener"><img class="comp-previa" src="${arquivo}" alt="Comprovante"></a>`;
    return `<div class="comp-visualizar">${visual}
      <dl class="comp-dados">
        <div><dt>Tipo</dt><dd>${esc(i.tipo_rotulo)}</dd></div>
        <div><dt>${i.tipo === "recebimento" || i.tipo === "cheque" || i.tipo === "nota" ? "Empresa" : "Beneficiário"}</dt><dd>${esc(i.nome || "—")}</dd></div>
        <div><dt>Valor</dt><dd>${brl(i.valor)}${i.valor_pago && Math.abs(i.valor_pago - i.valor) >= 0.01 ? ` · pago ${brl(i.valor_pago)}` : ""}${i.juros_multa ? ` <span class="juros-linha" style="display:inline">(+ ${brl(i.juros_multa)} juros)</span>` : ""}</dd></div>
        <div><dt>Data</dt><dd>${dataBR(i.data)}${i.vencimento && i.vencimento !== i.data ? ` <small class="sutil">(${i.tipo === "cheque" ? "bom para" : "vencimento"} ${dataBR(i.vencimento)})</small>` : ""}</dd></div>
        ${i.numero ? `<div><dt>${ROTULO_NUMERO[i.tipo] || "Número"}</dt><dd class="mono">${esc(i.numero)}</dd></div>` : ""}
        ${i.detalhe ? `<div><dt>Detalhes</dt><dd>${esc(i.detalhe)}</dd></div>` : ""}
        ${i.centro_custo ? `<div><dt>Centro de custo</dt><dd>${esc(i.centro_custo)}</dd></div>` : ""}
        ${i.pessoa ? `<div><dt>Quem</dt><dd>${esc(i.pessoa)}</dd></div>` : ""}
        <div><dt>Arquivo</dt><dd>${esc(i.comprovante_nome || "comprovante")}</dd></div>
      </dl></div>`;
  };
  const rodape = (i) => `
    <button class="btn btn-fantasma" data-navegar="-1" ${proximoCom(atual, -1) < 0 ? "disabled" : ""}>‹ Anterior</button>
    <button class="btn btn-fantasma" data-navegar="1" ${proximoCom(atual, 1) < 0 ? "disabled" : ""}>Próximo ›</button>
    <span class="espaco"></span>
    <a class="btn" href="${linkLancamento(i)}" data-fechar>${icone("externo", 15)} Abrir lançamento</a>
    <a class="btn" href="/api/arquivos/${esc(i.comprovante_id)}" target="_blank" rel="noopener">${icone("externo", 15)} Abrir em tela cheia</a>
    <a class="btn btn-primario" href="/api/arquivos/${esc(i.comprovante_id)}" download="${esc(i.comprovante_nome || "comprovante")}">${icone("download", 15)} Baixar</a>`;
  const proximoCom = (de, passo) => {
    for (let j = de + passo; j >= 0 && j < itens.length; j += passo) if (itens[j].comprovante_id) return j;
    return -1;
  };
  const { el } = abrirModal({ titulo: `Comprovante · ${itens[atual].nome || itens[atual].tipo_rotulo}`, tamanho: "lg",
    corpo: conteudo(itens[atual]), rodape: rodape(itens[atual]) });
  const mostrar = () => {
    const i = itens[atual];
    el.querySelector(".modal-cabecalho h3").textContent = `Comprovante · ${i.nome || i.tipo_rotulo}`;
    el.querySelector(".modal-corpo").innerHTML = conteudo(i);
    el.querySelector(".modal-rodape").innerHTML = rodape(i);
  };
  el.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-navegar]");
    if (!botao) return;
    const destino = proximoCom(atual, Number(botao.dataset.navegar));
    if (destino >= 0) { atual = destino; mostrar(); }
  });
  el.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const destino = proximoCom(atual, e.key === "ArrowRight" ? 1 : -1);
    if (destino >= 0) { atual = destino; mostrar(); }
  });
}

// ------------------------------------------------------------------ eventos

function periodoRapido(valor) {
  const hoje = new Date();
  const d = (data) => isoDeData(data);
  const ano = hoje.getFullYear();
  const mes = hoje.getMonth();
  if (valor === "hoje") return [hojeISO(), hojeISO()];
  if (valor === "semana") {
    const inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - ((hoje.getDay() + 6) % 7));
    return [d(inicio), hojeISO()];
  }
  if (valor === "mes") return [d(new Date(ano, mes, 1)), d(new Date(ano, mes + 1, 0))];
  if (valor === "mes_passado") return [d(new Date(ano, mes - 1, 1)), d(new Date(ano, mes, 0))];
  if (valor === "30" || valor === "90") {
    const inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - Number(valor));
    return [d(inicio), hojeISO()];
  }
  if (valor === "ano") return [`${ano}-01-01`, `${ano}-12-31`];
  return ["", ""];
}

function aoDigitar(e) {
  const campos = { "c-busca": "q", "c-valor": "valor", "c-numero": "numero", "c-valor-min": "valor_min",
    "c-valor-max": "valor_max", "c-pessoa": "pessoa" };
  const campo = campos[e.target.id];
  if (!campo) return;
  filtros[campo] = e.target.value.trim();
  recarregar();
}

function aoAlterar(e) {
  const alvo = e.target;
  if (alvo.id === "c-situacao") filtros.comprovante = alvo.value;
  else if (alvo.id === "c-de") filtros.de = alvo.value;
  else if (alvo.id === "c-ate") filtros.ate = alvo.value;
  else if (alvo.id === "c-centro") filtros.centro = alvo.value;
  else if (alvo.id === "c-ordenar") [filtros.ordenar, filtros.direcao] = alvo.value.split("|");
  else if (alvo.id === "c-rapido") {
    if (!alvo.value) return;
    [filtros.de, filtros.ate] = periodoRapido(alvo.value);
    raiz.querySelector("#c-de").value = filtros.de;
    raiz.querySelector("#c-ate").value = filtros.ate;
    alvo.value = "";
  } else return;
  filtros.pagina = 1;
  carregar();
}

async function aoClicar(e) {
  const alvo = e.target.closest("button, a, tr");
  if (!alvo || !raiz?.contains(alvo)) return;
  const d = alvo.dataset;
  if (d.tipo !== undefined && alvo.matches(".chip-filtro")) {
    if (!d.tipo) filtros.tipos = [];
    else filtros.tipos = filtros.tipos.includes(d.tipo) ? filtros.tipos.filter((t) => t !== d.tipo) : [...filtros.tipos, d.tipo];
    filtros.pagina = 1;
    carregar();
  } else if (d.acao === "mais-filtros") {
    maisFiltros = !maisFiltros;
    raiz.querySelector("#c-mais").hidden = !maisFiltros;
    alvo.setAttribute("aria-expanded", String(maisFiltros));
  } else if (d.acao === "limpar") {
    Object.assign(filtros, { q: "", tipos: [], de: "", ate: "", valor: "", valor_min: "", valor_max: "", numero: "",
      centro: "", pessoa: "", comprovante: "com", ordenar: "data", direcao: "desc", pagina: 1 });
    for (const [id, valor] of Object.entries({ "c-busca": "", "c-de": "", "c-ate": "", "c-valor": "", "c-numero": "",
      "c-valor-min": "", "c-valor-max": "", "c-pessoa": "", "c-centro": "", "c-situacao": "com", "c-ordenar": "data|desc" })) {
      const campo = raiz.querySelector(`#${id}`);
      if (campo) campo.value = valor;
    }
    carregar();
  } else if (d.pagina) {
    filtros.pagina = Number(d.pagina);
    carregar();
    raiz.querySelector(".tabela-card")?.scrollIntoView({ block: "start", behavior: "smooth" });
  } else if (d.ver !== undefined) {
    abrirComprovante(Number(d.ver));
  } else if (d.anexar !== undefined) {
    const item = ultimo.itens[Number(d.anexar)];
    const registro = await anexarComprovante(item.tipo === "pix" ? "pix" : "boletos", item.id);
    if (registro) carregar();
  } else if (alvo.id === "c-zip") {
    if (!ultimo?.resumo?.com_arquivo) {
      e.preventDefault();
      toast("Nenhum comprovante com arquivo nestes filtros.", "info");
    } else {
      toast(`Preparando ${ultimo.resumo.com_arquivo} comprovante(s) para baixar…`, "info", { duracao: 3000 });
    }
  } else if (alvo.matches("tr.comp-clicavel") && !e.target.closest("a, button")) {
    abrirComprovante(Number(alvo.dataset.indice));
  }
}

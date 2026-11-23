// Centros de custo ("onde foi gasto"): lista compartilhada entre as telas, opções de seleção e cadastro rápido.
// Um boleto ou Pix pode ter o valor dividido entre vários centros: o campo guarda
// "Energia R$ 600,00 + Frota R$ 400,00" (mesmo formato de app/cost_center.py).
import { api } from "./api.js";
import { abrirModal, brl, esc, mensagemErro, parseValor, pedirTexto, toast } from "./ui.js";
import { icone } from "./icons.js";

export const NOVO_CENTRO = "__novo__";
export const SEM_CENTRO = "__sem__";
export const SPLIT_OPTION = "__dividir__";
const MAX_PARTS = 10;

let cache = null;
let pendente = null;

export function carregarCentros(forcar = false) {
  if (cache && !forcar) return Promise.resolve(cache);
  if (!pendente || forcar) {
    pendente = api.get("/api/centros")
      .then((dados) => { cache = dados.centros; return cache; })
      .finally(() => { pendente = null; });
  }
  return pendente;
}

export function invalidarCentros() {
  cache = null;
}

const igual = (a, b) => String(a || "").trim().toLowerCase() === String(b || "").trim().toLowerCase();

/** <option>s de um seletor de centro de custo (somente ativos, mais o valor atual e "+ Novo centro…"). */
export function opcoesCentro(centros, selecionado = "", { vazio = "Sem centro de custo", permitirNovo = true, dividir = false } = {}) {
  const atual = String(selecionado || "").trim();
  const visiveis = centros.filter((c) => c.ativo || igual(c.nome, atual));
  const conhecido = !atual || visiveis.some((c) => igual(c.nome, atual));
  return `<option value="">${esc(vazio)}</option>`
    + visiveis.map((c) => `<option value="${esc(c.nome)}" ${igual(c.nome, atual) ? "selected" : ""}>${esc(c.nome)}</option>`).join("")
    + (conhecido ? "" : `<option value="${esc(atual)}" selected>${esc(atual)}</option>`)
    + (permitirNovo ? `<option value="${NOVO_CENTRO}">+ Novo centro de custo…</option>` : "")
    + (dividir ? `<option value="${SPLIT_OPTION}">÷ Dividir em mais de um centro…</option>` : "");
}

/** As partes de um centro de custo dividido: [{ name, amount }]. Um nome sozinho (ou vazio) devolve []. */
export function splitParts(text) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  const pattern = /(.+?) R\$ ?(\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2})(?: \+ |$)/y;
  const parts = [];
  let end = 0;
  while (end < clean.length) {
    pattern.lastIndex = end;
    const match = pattern.exec(clean);
    if (!match) return [];
    parts.push({ name: match[1].trim(), amount: Number(match[2].replace(/\./g, "").replace(",", ".")) });
    end = pattern.lastIndex;
  }
  return parts;
}

/** O centro de custo de um lançamento em etiquetas: uma só, ou uma por centro (com a parte de cada um). */
export function costCenterTags(text) {
  const parts = splitParts(text);
  if (parts.length < 2) {
    const name = parts[0]?.name || String(text || "").trim();
    return name ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(name)}</span>` : "";
  }
  return parts.map((p) => `<span class="tag-centro">${icone("etiqueta", 11)}${esc(p.name)} <small>${brl(p.amount)}</small></span>`).join("");
}

/** <option>s do filtro das listas: todos, sem centro e cada centro (inclusive inativos). */
export function opcoesFiltroCentro(centros, selecionado = "") {
  const opcoes = [["", "Todos os centros de custo"], [SEM_CENTRO, "Sem centro de custo"],
    ...centros.map((c) => [c.nome, c.ativo ? c.nome : `${c.nome} (inativo)`])];
  if (selecionado && !opcoes.some(([valor]) => igual(valor, selecionado))) opcoes.push([selecionado, selecionado]);
  return opcoes.map(([valor, rotulo]) => `<option value="${esc(valor)}" ${igual(valor, selecionado) && (valor || !selecionado) ? "selected" : ""}>${esc(rotulo)}</option>`).join("");
}

function refreshSelects(select, valor, centros) {
  document.querySelectorAll("select[data-centro-select]").forEach((s) => {
    const atual = s === select ? valor : ([NOVO_CENTRO, SPLIT_OPTION].includes(s.value) ? "" : s.value);
    s.innerHTML = opcoesCentro(centros, atual, { vazio: s.dataset.vazio || "Sem centro de custo", dividir: "dividir" in s.dataset });
  });
}

/**
 * Trata as opções "+ Novo centro de custo…" e "÷ Dividir em mais de um centro…" de um <select>; devolve o valor
 * escolhido no final. `getValue()` dá o valor do lançamento (o que vai ser dividido).
 */
export async function tratarNovoCentro(select, anterior = "", getValue = null) {
  if (select.value === SPLIT_OPTION) {
    const text = await splitAmongCenters({ value: getValue ? getValue() : null, current: anterior });
    const chosen = text === null ? anterior : text;
    refreshSelects(select, chosen, await carregarCentros().catch(() => cache || []));
    return chosen;
  }
  if (select.value !== NOVO_CENTRO) return select.value;
  const nome = await pedirTexto({
    titulo: "Novo centro de custo",
    rotulo: "Nome do centro de custo",
    descricao: "Use para saber onde cada boleto ou Pix foi gasto — uma obra, um setor, um veículo…",
    placeholder: "Ex.: Obra Jardim Europa, Caminhão 02, Escritório",
    textoConfirmar: "Criar",
    maximo: 60,
  });
  let valor = anterior;
  if (nome) {
    valor = nome.replace(/\s+/g, " ").trim();
    try {
      await api.post("/api/centros", { nome: valor });
      toast(`Centro de custo "${valor}" criado`, "ok", { duracao: 2500 });
    } catch (erro) {
      if (erro.status === 423) {
        toast("A planilha está aberta no Excel: o centro de custo será cadastrado quando o lançamento for gravado.", "aviso", { duracao: 6000 });
      } else if (erro.status !== 422) {
        toast(mensagemErro(erro), "erro");
        valor = anterior;
      }
    }
  }
  let centros = cache || [];
  try { centros = await carregarCentros(true); } catch { /* mantém a lista atual */ }
  const existente = centros.find((c) => igual(c.nome, valor));
  if (existente) valor = existente.nome;
  refreshSelects(select, valor, centros);
  return valor;
}

const money = (v) => Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const cents = (v) => Math.round((Number(v) || 0) * 100);

/**
 * Janela para dividir o valor de um lançamento entre centros de custo. Devolve o texto da divisão
 * ("Energia R$ 600,00 + Frota R$ 400,00"), o nome do centro se ficar um só, ou null se cancelar.
 */
export async function splitAmongCenters({ value, current = "" } = {}) {
  const total = cents(value);
  if (!(total > 0)) {
    toast("Informe o valor antes de dividir entre centros de custo.", "aviso", { duracao: 5000 });
    return null;
  }
  const centros = await carregarCentros().catch(() => []);
  const previous = splitParts(current);
  const rows = previous.length > 1 ? previous.map((p) => ({ name: p.name, amount: p.amount }))
    : [{ name: previous[0]?.name || String(current || "").trim(), amount: null }, { name: "", amount: null }];

  return new Promise((resolve) => {
    let answered = false;
    const { el, fechar } = abrirModal({
      titulo: "Dividir entre centros de custo",
      corpo: `<p class="sutil" style="margin-bottom:12px">Diga quanto do valor de <strong>${brl(total / 100)}</strong> vai para cada
          centro de custo. Nos relatórios, cada centro fica só com a parte dele.</p>
        <div data-split-rows></div>
        <div class="linha-botoes">
          <button type="button" class="btn btn-sm" data-split="add">${icone("mais", 14)} Adicionar centro</button>
          <button type="button" class="btn btn-sm btn-fantasma" data-split="equal">Dividir igualmente</button>
        </div>
        <p class="split-summary" data-split-summary role="status"></p>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-split="confirm">${icone("check", 16)} Aplicar divisão</button>`,
      aoFechar: () => { if (!answered) resolve(null); },
    });
    const list = el.querySelector("[data-split-rows]");
    const summary = el.querySelector("[data-split-summary]");
    const remaining = (except = -1) => total - rows.reduce((sum, r, i) => sum + (i === except ? 0 : cents(r.amount)), 0);

    function drawSummary() {
      const left = remaining();
      summary.className = `split-summary ${left === 0 ? "ok" : "aviso"}`;
      summary.textContent = left === 0 ? `Tudo distribuído: ${brl(total / 100)}.`
        : left > 0 ? `Falta distribuir ${brl(left / 100)} de ${brl(total / 100)}.`
          : `Passou ${brl(-left / 100)} do valor de ${brl(total / 100)}.`;
    }
    function draw() {
      list.innerHTML = rows.map((r, i) => `<div class="split-row" data-row="${i}">
          <select class="input" data-centro-select data-vazio="Escolha o centro…" aria-label="Centro de custo ${i + 1}">
            ${opcoesCentro(centros, r.name, { vazio: "Escolha o centro…" })}</select>
          <div class="input-prefixo"><span>R$</span><input class="input" inputmode="decimal" placeholder="0,00"
            value="${r.amount ? esc(money(r.amount)) : ""}" aria-label="Valor do centro de custo ${i + 1}"></div>
          <button type="button" class="btn btn-sm btn-fantasma" data-split="rest" title="Põe aqui o que falta distribuir">Restante</button>
          <button type="button" class="btn-icone perigo" data-split="remove" title="Tirar este centro" aria-label="Tirar este centro"
            ${rows.length <= 1 ? "disabled" : ""}>${icone("x", 15)}</button>
        </div>`).join("");
      el.querySelector('[data-split="add"]').disabled = rows.length >= MAX_PARTS;
      drawSummary();
    }

    el.addEventListener("input", (e) => {
      const row = rows[e.target.closest("[data-row]")?.dataset.row];
      if (!row || e.target.tagName !== "INPUT") return;
      const amount = parseValor(e.target.value);
      row.amount = Number.isFinite(amount) ? amount : null;
      drawSummary();
    });
    el.addEventListener("change", async (e) => {
      const row = rows[e.target.closest("[data-row]")?.dataset.row];
      if (!row) return;
      if (e.target.tagName === "SELECT") row.name = await tratarNovoCentro(e.target, row.name);
      else if (row.amount) e.target.value = money(row.amount);
    });
    el.addEventListener("click", (e) => {
      const action = e.target.closest("[data-split]")?.dataset.split;
      const index = Number(e.target.closest("[data-row]")?.dataset.row);
      if (action === "add" && rows.length < MAX_PARTS) {
        rows.push({ name: "", amount: null });
      } else if (action === "remove" && rows.length > 1) {
        rows.splice(index, 1);
      } else if (action === "rest") {
        rows[index].amount = Math.max(0, remaining(index)) / 100 || null;
      } else if (action === "equal") {
        const share = Math.floor(total / rows.length);
        rows.forEach((r, i) => { r.amount = (i === rows.length - 1 ? total - share * (rows.length - 1) : share) / 100; });
      } else if (action === "confirm") {
        const chosen = rows.map((r) => r.name.toLowerCase());
        const problem = rows.some((r) => !r.name || r.name === NOVO_CENTRO) ? "Escolha o centro de custo de cada linha."
          : rows.some((r) => !(cents(r.amount) > 0)) ? "Informe o valor de cada centro de custo."
            : new Set(chosen).size !== chosen.length ? "O mesmo centro de custo aparece mais de uma vez."
              : remaining() !== 0 ? summary.textContent : "";
        if (problem) {
          toast(problem, "aviso", { duracao: 5000 });
          return;
        }
        answered = true;
        resolve(rows.length === 1 ? rows[0].name : rows.map((r) => `${r.name} R$ ${money(r.amount)}`).join(" + "));
        fechar(true);
        return;
      } else {
        return;
      }
      draw();
    });
    draw();
  });
}

/** Janela para escolher um centro de custo. Devolve o nome ("" = sem centro) ou null se cancelar. */
export async function escolherCentro({ titulo = "Centro de custo", descricao = "", atual = "", textoConfirmar = "Aplicar" } = {}) {
  const centros = await carregarCentros().catch(() => []);
  return new Promise((resolve) => {
    let respondido = false;
    const { el, fechar } = abrirModal({
      titulo,
      corpo: `${descricao ? `<p class="sutil" style="margin-bottom:12px">${esc(descricao)}</p>` : ""}
        <div class="campo"><label for="escolher-centro">${icone("etiqueta", 14)} Onde foi gasto</label>
          <select id="escolher-centro" class="input" data-centro-select autofocus>${opcoesCentro(centros, atual)}</select></div>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-confirmar>${esc(textoConfirmar)}</button>`,
      aoFechar: () => { if (!respondido) resolve(null); },
    });
    const select = el.querySelector("#escolher-centro");
    let anterior = atual;
    select.addEventListener("change", async () => { anterior = await tratarNovoCentro(select, anterior); });
    el.querySelector("[data-confirmar]").addEventListener("click", () => {
      if (select.value === NOVO_CENTRO) return;
      respondido = true;
      resolve(select.value);
      fechar(true);
    });
  });
}

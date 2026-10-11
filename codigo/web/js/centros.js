// Centros de custo ("onde foi gasto"): lista compartilhada entre as telas, opções de seleção e cadastro rápido.
import { api } from "./api.js";
import { abrirModal, esc, mensagemErro, pedirTexto, toast } from "./ui.js";
import { icone } from "./icons.js";

export const NOVO_CENTRO = "__novo__";
export const SEM_CENTRO = "__sem__";

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
export function opcoesCentro(centros, selecionado = "", { vazio = "Sem centro de custo", permitirNovo = true } = {}) {
  const atual = String(selecionado || "").trim();
  const visiveis = centros.filter((c) => c.ativo || igual(c.nome, atual));
  const conhecido = !atual || visiveis.some((c) => igual(c.nome, atual));
  return `<option value="">${esc(vazio)}</option>`
    + visiveis.map((c) => `<option value="${esc(c.nome)}" ${igual(c.nome, atual) ? "selected" : ""}>${esc(c.nome)}</option>`).join("")
    + (conhecido ? "" : `<option value="${esc(atual)}" selected>${esc(atual)}</option>`)
    + (permitirNovo ? `<option value="${NOVO_CENTRO}">+ Novo centro de custo…</option>` : "");
}

/** <option>s do filtro das listas: todos, sem centro e cada centro (inclusive inativos). */
export function opcoesFiltroCentro(centros, selecionado = "") {
  const opcoes = [["", "Todos os centros de custo"], [SEM_CENTRO, "Sem centro de custo"],
    ...centros.map((c) => [c.nome, c.ativo ? c.nome : `${c.nome} (inativo)`])];
  if (selecionado && !opcoes.some(([valor]) => igual(valor, selecionado))) opcoes.push([selecionado, selecionado]);
  return opcoes.map(([valor, rotulo]) => `<option value="${esc(valor)}" ${igual(valor, selecionado) && (valor || !selecionado) ? "selected" : ""}>${esc(rotulo)}</option>`).join("");
}

/** Trata a opção "+ Novo centro de custo…" de um <select>; devolve o valor escolhido no final. */
export async function tratarNovoCentro(select, anterior = "") {
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
  document.querySelectorAll("select[data-centro-select]").forEach((s) => {
    const atual = s === select ? valor : (s.value === NOVO_CENTRO ? "" : s.value);
    s.innerHTML = opcoesCentro(centros, atual, { vazio: s.dataset.vazio || "Sem centro de custo" });
  });
  return valor;
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

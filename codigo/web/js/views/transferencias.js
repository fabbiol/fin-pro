// Tela: Transferências de clientes — notas pagas por Pix ou TED/DOC que a Operações manda, aguardando o pagamento.
import { api } from "../api.js";
import { icone } from "../icons.js";
import { brl, dataBR, debounce, esc, mensagemErro } from "../ui.js";

const FORMAS = { pix: "Pix", transferencia: "TED/DOC" };
const CLASSE_SITUACAO = { "Aguardando pagamento": "aviso", Pago: "ok" };
const filtros = { empresa: "", situacao: "", q: "" };
let raiz = null;
let requisicao = 0;

export async function montar(el) {
  raiz = el;
  el.innerHTML = `
    <section class="card barra-filtros">
      <div class="filtros-linha">
        <label class="busca">${icone("busca", 16)}
          <input id="t-busca" class="input" type="search" value="${esc(filtros.q)}" autocomplete="off"
            placeholder="Buscar pelo número da nota" aria-label="Buscar pelo número da nota"></label>
        <select id="t-empresa" class="input input-sm" aria-label="Empresa"><option value="">Todas as empresas</option></select>
        <select id="t-situacao" class="input input-sm" aria-label="Situação"><option value="">Todas as situações</option></select>
      </div>
    </section>
    <section class="resumo-lista" id="t-resumo"></section>
    <section class="card tabela-card">
      <div class="tabela-wrap" id="t-tabela"><div style="padding:18px">${'<div class="esqueleto" style="height:44px;margin-bottom:8px"></div>'.repeat(4)}</div></div>
    </section>`;
  el.addEventListener("input", aoDigitar);
  el.addEventListener("change", aoAlterar);
  await carregar();
}

export function desmontar() {
  raiz?.removeEventListener("input", aoDigitar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz = null;
}

function aoDigitar(e) {
  if (e.target.id !== "t-busca") return;
  filtros.q = e.target.value;
  recarregar();
}

function aoAlterar(e) {
  if (e.target.id === "t-empresa") filtros.empresa = e.target.value;
  else if (e.target.id === "t-situacao") filtros.situacao = e.target.value;
  else return;
  carregar();
}

const recarregar = debounce(() => carregar(), 350);

async function carregar() {
  if (!raiz) return;
  const minha = ++requisicao;
  const params = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v));
  try {
    const dados = await api.get("/api/transferencias", params);
    if (!raiz || minha !== requisicao) return;
    preencherOpcoes("#t-empresa", dados.empresas, filtros.empresa);
    preencherOpcoes("#t-situacao", dados.situacoes, filtros.situacao);
    raiz.querySelector("#t-resumo").innerHTML = `
      <div class="card resumo-item"><span>Notas</span><strong>${dados.total}</strong></div>
      <div class="card resumo-item"><span>Valor somado</span><strong>${brl(dados.valor)}</strong></div>`;
    desenharTabela(dados.transferencias);
  } catch (erro) {
    if (!raiz) return;
    raiz.querySelector("#t-tabela").innerHTML = `<div class="vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar as transferências</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

function preencherOpcoes(seletor, valores, escolhido) {
  const select = raiz.querySelector(seletor);
  const primeira = select.options[0].outerHTML;
  select.innerHTML = primeira + valores.map((v) => `<option value="${esc(v)}" ${v === escolhido ? "selected" : ""}>${esc(v)}</option>`).join("");
}

function desenharTabela(linhas) {
  const alvo = raiz.querySelector("#t-tabela");
  if (!linhas.length) {
    const filtrando = filtros.empresa || filtros.situacao || filtros.q;
    alvo.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone(filtrando ? "busca" : "banco", 26)}</div>
      <h3>${filtrando ? "Nenhuma nota com estes filtros" : "Nenhuma transferência ainda"}</h3>
      <p>${filtrando ? "Mude a busca ou os filtros." : "As notas pagas por Pix ou TED/DOC chegam sozinhas da Operações."}</p></div>`;
    return;
  }
  alvo.innerHTML = `<table class="tabela">
    <thead><tr><th>Nota</th><th>Pedido</th><th>Empresa</th><th class="num">Valor</th><th>Material</th>
      <th>Emissão</th><th>Forma</th><th>Situação</th><th class="col-acoes">PDF</th></tr></thead>
    <tbody>${linhas.map((t) => `<tr>
      <td data-rotulo="Nota"><strong>${esc(t.nota)}</strong></td>
      <td data-rotulo="Pedido">${esc(t.pedido || "—")}</td>
      <td data-rotulo="Empresa">${esc(t.empresa)}</td>
      <td class="num" data-rotulo="Valor">${brl(t.valor)}</td>
      <td data-rotulo="Material">${esc(t.material || "—")}</td>
      <td data-rotulo="Emissão">${dataBR(t.emitida_em)}</td>
      <td data-rotulo="Forma">${esc(FORMAS[t.forma] || t.forma)}</td>
      <td data-rotulo="Situação"><span class="chip ${CLASSE_SITUACAO[t.status] || ""}">${esc(t.status)}</span></td>
      <td class="col-acoes">${t.arquivo
        ? `<a class="btn btn-sm" href="/api/transferencias/${t.id}/pdf" target="_blank" rel="noopener"
            title="Abrir o PDF da nota ${esc(t.nota)}">${icone("arquivo", 14)} Abrir PDF</a>`
        : `<span class="sutil">sem PDF</span>`}</td></tr>`).join("")}</tbody>
  </table>`;
}

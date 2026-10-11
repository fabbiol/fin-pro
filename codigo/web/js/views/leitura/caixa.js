// Ler boletos · caixa de entrada (boletos e comprovantes recebidos por e-mail e Telegram).
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, seloFonte, tamanhoArquivo,
  toast, uid,
} from "../../ui.js";
import { abrirFormularioPix } from "../pix/index.js";
import { ORIGENS, abertosDaCaixa, fila, tela } from "./estado.js";
import { htmlEscolhaLancamento, textoPagamento } from "./comprovante.js";
import { marcarRepetidosNaFila, novoBoleto } from "./fila.js";
import { renderizarFila } from "./render.js";

export async function carregarCaixa() {
  try {
    tela.caixa = await api.get("/api/entrada");
  } catch {
    tela.caixa = null;
  }
  window.dispatchEvent(new CustomEvent("entrada:contagem", { detail: tela.caixa?.pendentes ?? 0 }));
  renderizarCaixa();
}

export function resumoRecebido(i) {
  const r = i.resumo || {};
  if (i.estado === "erro") return `<span class="erro-texto">${icone("alerta", 13)} ${esc(i.erro || "Não foi possível ler.")}</span>`;
  if (i.tipo === "comprovante") {
    return `<span class="chip ${r.agendado ? "aviso" : "info"}">${icone("clipe", 12)} ${r.agendado ? "Agendamento" : "Comprovante"}</span>
      ${r.valor_pago ? brl(r.valor_pago) : "valor não identificado"}${r.data_pagamento ? ` · pago em ${dataBR(r.data_pagamento)}` : ""}
      ${r.beneficiario ? ` · ${esc(r.beneficiario)}` : ""}`;
  }
  const partes = [r.beneficiario ? esc(r.beneficiario) : "Beneficiário não identificado", r.valor ? brl(r.valor) : "", r.vencimento ? `vence ${dataBR(r.vencimento)}` : ""];
  const extra = (r.boletos || 0) + (r.pix || 0) > 1 ? ` · ${(r.boletos || 0) + (r.pix || 0)} documentos` : "";
  return `${partes.filter(Boolean).join(" · ")}${extra}${r.duplicado ? ` <span class="chip erro">Já lançado</span>` : ""}${r.pix && !r.boletos ? ` <span class="chip">Pix</span>` : ""}`;
}

export function renderizarCaixa() {
  const el = tela.raiz?.querySelector("#caixa-entrada");
  if (!el) return;
  const abertos = abertosDaCaixa();
  const itens = (tela.caixa?.itens || []).filter((i) => !abertos.has(i.id));
  el.hidden = !itens.length;
  if (!itens.length) return;
  const revisaveis = itens.filter((i) => i.estado === "pendente" && i.tipo !== "comprovante").length;
  el.innerHTML = `
    <header class="caixa-cabecalho">
      <h3>${icone("caixa", 18)} Recebidos por e-mail e Telegram <span class="chip info">${itens.length}</span></h3>
      <span class="sutil">Confira e lance, ou descarte o que não for boleto.</span>
      <span class="espaco"></span>
      ${revisaveis > 1 ? `<button class="btn btn-sm btn-primario" data-caixa="revisar-todos">${icone("olho", 14)} Revisar todos (${revisaveis})</button>` : ""}
    </header>
    <ul class="caixa-lista">${itens.map((i) => {
      const [iconeOrigem, rotulo] = ORIGENS[i.origem] || ["arquivo", i.origem];
      return `<li data-recebido="${esc(i.id)}" class="${i.estado === "erro" ? "com-erro" : ""}">
        <span class="caixa-origem" title="${rotulo}">${icone(iconeOrigem, 16)}</span>
        <div class="caixa-info">
          <strong>${resumoRecebido(i)}</strong>
          <span class="sutil">${rotulo} de ${esc(i.remetente || "remetente desconhecido")}${i.assunto ? ` · “${esc(i.assunto)}”` : ""} · ${esc(i.nome_arquivo)} · ${dataHoraBR(i.recebido_em)}</span>
        </div>
        ${i.tipo === "comprovante" && i.estado === "pendente" ? htmlEscolhaLancamento(i.candidatos, "caixa") : ""}
        <div class="caixa-acoes">
          ${i.tipo === "comprovante" && i.estado === "pendente"
            ? `${i.candidatos?.length ? `<button class="btn btn-sm btn-primario" data-caixa="registrar">${icone("check", 14)} Registrar pagamento</button>` : ""}
               ${i.arquivo_id ? `<a class="btn btn-sm" href="/api/arquivos/${esc(i.arquivo_id)}" target="_blank" rel="noopener">${icone("arquivo", 14)} Ver</a>` : ""}`
            : i.estado === "pendente"
            ? `<button class="btn btn-sm btn-primario" data-caixa="revisar">${icone("olho", 14)} Revisar</button>`
            : i.arquivo_id ? `<a class="btn btn-sm" href="/api/arquivos/${esc(i.arquivo_id)}" target="_blank" rel="noopener">${icone("arquivo", 14)} Abrir arquivo</a>` : ""}
          <button class="btn-icone" data-caixa="descartar" title="Descartar (não é boleto ou já foi lançado)">${icone("lixeira", 15)}</button>
        </div></li>`;
    }).join("")}</ul>`;
}

export async function revisarRecebido(id) {
  const recebido = await api.get(`/api/entrada/${id}`);
  const resultado = recebido.resultado;
  if (!resultado) throw new Error("Este arquivo não pôde ser lido.");
  const [, rotulo] = ORIGENS[recebido.origem] || ["", recebido.origem];
  const item = {
    uid: uid(), nome: recebido.nome_arquivo, status: "concluido", resultado, recebido: id,
    origemTexto: `${rotulo} de ${recebido.remetente || "remetente desconhecido"}`,
    boletos: (resultado.boletos || []).map((b) => novoBoleto(b, resultado.arquivo)),
  };
  fila.unshift(item);
  marcarRepetidosNaFila(item);
}

export async function aoClicarCaixa(e) {
  const botao = e.target.closest("[data-caixa]");
  if (!botao) return;
  const acao = botao.dataset.caixa;
  botao.disabled = true;
  try {
    if (acao === "revisar-todos") {
      const abertos = abertosDaCaixa();
      for (const i of (tela.caixa?.itens || []).filter((x) => x.estado === "pendente" && x.tipo !== "comprovante" && !abertos.has(x.id))) {
        await revisarRecebido(i.id);
      }
      renderizarFila();
      renderizarCaixa();
      tela.raiz.querySelector("#lista-fila")?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const id = botao.closest("[data-recebido]").dataset.recebido;
    if (acao === "revisar") {
      await revisarRecebido(id);
      renderizarFila();
      renderizarCaixa();
      tela.raiz.querySelector("#lista-fila")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (acao === "registrar") {
      const [aba, registroId] = botao.closest("[data-recebido]").querySelector("[data-escolha]").value.split(":");
      const { item } = await api.post(`/api/entrada/${id}/registrar`, { aba, id: Number(registroId) });
      toast(textoPagamento(item.pagamento), "ok", { duracao: 7000 });
      window.dispatchEvent(new Event("avisos:atualizar"));
      await carregarCaixa();
    } else if (acao === "descartar") {
      await api.post("/api/entrada/descartar", { ids: [id] });
      toast("Descartado da caixa de entrada.", "info", { duracao: 2500 });
      await carregarCaixa();
    }
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  } finally {
    botao.disabled = false;
  }
}

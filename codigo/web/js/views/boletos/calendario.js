// Boletos lançados · calendário de vencimentos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, compacto, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, isoDeData, mensagemErro, numeroBR,
  parseValor, seloSituacao, toast,
} from "../../ui.js";
import { abrirDetalhes } from "../../detalhes.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { DIAS_CAL, NOMES_MES, filtros, inicioDoMes, tela } from "./estado.js";
import { cabecalho, carregar, executarAcao, linha, renderizarResumo } from "./lista.js";

export function intervaloDaGrade() {
  const inicio = new Date(tela.mesCalendario);
  inicio.setDate(1 - inicio.getDay()); // começa no domingo
  const fimMes = new Date(tela.mesCalendario.getFullYear(), tela.mesCalendario.getMonth() + 1, 0);
  const fim = new Date(fimMes);
  fim.setDate(fimMes.getDate() + (6 - fimMes.getDay()));
  return { inicio, fim };
}

export async function carregarCalendario() {
  const card = tela.raiz.querySelector("#card-calendario");
  card.classList.add("carregando");
  const { inicio, fim } = intervaloDaGrade();
  const minha = ++tela.requisicao;
  try {
    const dados = await api.get("/api/boletos", {
      q: filtros.q, situacao: filtros.situacao, campo_data: "vencimento",
      de: isoDeData(inicio), ate: isoDeData(fim), ordenar: "vencimento", direcao: "asc", por_pagina: 0,
    });
    if (!tela.raiz || minha !== tela.requisicao) return;
    tela.itensCalendario = dados.itens;
    renderizarCalendario();
  } catch (erro) {
    card.innerHTML = `<div class="vazio"><h3>Não foi possível carregar o calendário</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  } finally {
    card.classList.remove("carregando");
  }
}

export function resumoDoMes(itens) {
  const r = { quantidade: 0, valor_total: 0, valor_pendente: 0, valor_vencido: 0, valor_pago: 0, juros_multa: 0, pagos_com_juros: 0 };
  for (const item of itens) {
    if (item.situacao === "cancelado") continue;
    const valor = Number(item.valor || 0);
    r.quantidade += 1;
    r.valor_total += valor;
    if (item.situacao === "pago") {
      r.valor_pago += valor;
      const juros = Number(item.juros_multa || 0);
      if (juros) {
        r.juros_multa += juros;
        r.pagos_com_juros += 1;
      }
    } else {
      r.valor_pendente += valor;
      if (item.situacao === "vencido") r.valor_vencido += valor;
    }
  }
  return r;
}

export function renderizarCalendario() {
  const card = tela.raiz.querySelector("#card-calendario");
  const { inicio, fim } = intervaloDaGrade();
  const mes = tela.mesCalendario.getMonth();
  const hojeIso = isoDeData(new Date());
  const porDia = new Map();
  tela.itensCalendario.forEach((item) => {
    if (!porDia.has(item.vencimento)) porDia.set(item.vencimento, []);
    porDia.get(item.vencimento).push(item);
  });
  const doMes = tela.itensCalendario.filter((item) => Number(item.vencimento.slice(5, 7)) - 1 === mes
    && Number(item.vencimento.slice(0, 4)) === tela.mesCalendario.getFullYear());
  renderizarResumo(resumoDoMes(doMes), "Boletos no mês");

  const dias = [];
  for (let d = new Date(inicio); d <= fim; d.setDate(d.getDate() + 1)) dias.push(new Date(d));

  card.innerHTML = `
    <div class="cal-cabecalho">
      <button class="btn-icone" data-cal="anterior" aria-label="Mês anterior">${icone("chevron-esq", 18)}</button>
      <h3>${NOMES_MES[mes]} de ${tela.mesCalendario.getFullYear()}</h3>
      <button class="btn-icone" data-cal="proximo" aria-label="Próximo mês">${icone("chevron-dir", 18)}</button>
      <button class="btn btn-sm" data-cal="hoje">Hoje</button>
      <span class="espaco"></span>
      <div class="legenda">
        <span><i style="background:var(--erro)"></i>Vencido</span>
        <span><i style="background:var(--aviso)"></i>Vence hoje</span>
        <span><i style="background:var(--marca)"></i>A vencer</span>
        <span><i style="background:var(--ok)"></i>Pago</span>
      </div>
    </div>
    <div class="calendario-grade" role="grid">
      ${DIAS_CAL.map((d) => `<div class="cal-semana" role="columnheader">${d}</div>`).join("")}
      ${dias.map((data) => {
        const iso = isoDeData(data);
        const itens = (porDia.get(iso) || []).filter((i) => i.situacao !== "cancelado");
        const fora = data.getMonth() !== mes;
        const situacoes = new Set(itens.map((i) => i.situacao));
        const classe = situacoes.has("vencido") ? "tem-vencido" : situacoes.has("vence_hoje") ? "tem-hoje"
          : (situacoes.has("a_vencer") || situacoes.has("pendente")) ? "tem-pendente" : itens.length ? "todos-pagos" : "";
        const total = itens.reduce((s, i) => s + Number(i.valor || 0), 0);
        const nomes = itens.slice(0, 2).map((i) => `<span>${esc(i.beneficiario || "Sem beneficiário")}</span>`).join("")
          + (itens.length > 2 ? `<span class="sutil">+${itens.length - 2}</span>` : "");
        return `<button class="dia-cal ${fora ? "fora" : ""} ${iso === hojeIso ? "hoje" : ""} ${classe}" data-dia="${iso}"
            ${itens.length ? "" : "tabindex=\"-1\""} role="gridcell" aria-label="${dataBR(iso)}: ${itens.length} boleto(s)">
          <span class="dia-num">${data.getDate()}</span>
          ${itens.length ? `<span class="dia-total" title="${brl(total)}">R$ ${compacto(total)}</span>
            <span class="dia-qtd">${itens.length} boleto${itens.length === 1 ? "" : "s"}</span>
            <span class="dia-nomes">${nomes}</span>` : ""}
        </button>`;
      }).join("")}
    </div>`;
}

export async function aoClicarCalendario(e) {
  const navegacao = e.target.closest("[data-cal]");
  if (navegacao) {
    const acao = navegacao.dataset.cal;
    if (acao === "hoje") tela.mesCalendario = inicioDoMes(new Date());
    else tela.mesCalendario = new Date(tela.mesCalendario.getFullYear(), tela.mesCalendario.getMonth() + (acao === "proximo" ? 1 : -1), 1);
    carregarCalendario();
    return;
  }
  const dia = e.target.closest("[data-dia]");
  if (!dia) return;
  const itens = tela.itensCalendario.filter((i) => i.vencimento === dia.dataset.dia);
  if (itens.length) abrirDia(dia.dataset.dia, itens);
}

export function abrirDia(iso, itens) {
  const total = itens.filter((i) => i.situacao !== "cancelado").reduce((s, i) => s + Number(i.valor || 0), 0);
  const { el, fechar } = abrirModal({
    titulo: `Vencimentos de ${dataBR(iso)}`,
    tamanho: "lg",
    corpo: `<ul class="lista-mini lista-dia">${itens.map((r) => `<li data-id="${r.id}">
        <div class="info"><div class="titulo">${esc(r.beneficiario || "Sem beneficiário")}</div>
          <div class="sutil">${r.numero_documento ? `Doc. ${esc(r.numero_documento)} · ` : ""}${esc(r.emissor || "")}</div></div>
        ${seloSituacao(r.situacao, r.dias_para_vencer)}
        <div class="valor">${brl(r.valor)}</div>
        <div class="acoes">
          ${r.linha_digitavel ? `<button class="btn-icone" data-acao="copiar" title="Copiar linha digitável">${icone("copiar", 16)}</button>` : ""}
          <button class="btn-icone ${r.situacao === "pago" ? "" : "ok"}" data-acao="${r.situacao === "pago" ? "pendente" : "pago"}"
            title="${r.situacao === "pago" ? "Voltar para pendente" : "Marcar como pago"}">${icone(r.situacao === "pago" ? "desfazer" : "check", 16)}</button>
          <button class="btn-icone" data-acao="editar" title="Editar">${icone("editar", 16)}</button>
        </div></li>`).join("")}</ul>
      <p class="sutil" style="margin-top:12px">Total do dia (sem cancelados): <strong>${brl(total)}</strong></p>`,
    rodape: `<button class="btn btn-primario" data-fechar>Fechar</button>`,
  });
  el.querySelector(".lista-dia").addEventListener("click", async (evento) => {
    const alvo = evento.target.closest("[data-acao]");
    if (!alvo) return;
    const registro = itens.find((r) => r.id === Number(alvo.closest("[data-id]").dataset.id));
    if (alvo.dataset.acao !== "copiar") fechar(true);
    try {
      await executarAcao(alvo.dataset.acao, registro);
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  });
}

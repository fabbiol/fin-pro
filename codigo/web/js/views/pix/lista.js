// Pagamentos Pix · lista de Pix lançados, pagamento e QR code.
import { abrirDetalhes } from "../../detalhes.js";
import { api } from "../../api.js";
import { NOVO_CENTRO, carregarCentros, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, hojeISO, mensagemErro, numeroBR, parseValor,
  seloSituacao, toast, uid,
} from "../../ui.js";
import { pode } from "../../estado.js";
import { COLUNAS, filtros, tela } from "./estado.js";
import { abrirFormularioPix } from "./formulario.js";
import { sincronizarChips } from "./montagem.js";

export async function carregar() {
  if (!tela.raiz) return;
  const tabela = tela.raiz.querySelector("#p-tabela");
  tabela.classList.add("carregando");
  const minha = ++tela.requisicao;
  try {
    const dados = await api.get("/api/pix", filtros);
    if (!tela.raiz || minha !== tela.requisicao) return;
    tela.ultimo = dados;
    renderizarResumo(dados.resumo);
    renderizarTabela();
    renderizarPaginacao();
  } catch (erro) {
    if (!tela.raiz) return;
    tabela.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar os Pix</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  } finally {
    tela.raiz?.querySelector("#p-tabela")?.classList.remove("carregando");
  }
}

export function renderizarResumo(r) {
  tela.raiz.querySelector("#p-resumo").innerHTML = `
    <div class="card resumo-item"><span>Pix</span><strong>${r.quantidade}</strong></div>
    <div class="card resumo-item"><span>Valor total</span><strong>${brl(r.valor_total)}</strong></div>
    <div class="card resumo-item"><span>Pendente</span><strong>${brl(r.valor_pendente)}</strong></div>
    <div class="card resumo-item erro"><span>Atrasado</span><strong>${brl(r.valor_vencido)}</strong></div>
    <div class="card resumo-item ok"><span>Pago</span><strong>${brl(r.valor_pago)}</strong></div>
    <div class="card resumo-item ${r.juros_multa ? "erro" : ""}" title="Juros e multas pagos nos Pix desta lista">
      <span>Juros e multas pagos${r.pagos_com_juros ? ` (${r.pagos_com_juros})` : ""}</span><strong>${brl(r.juros_multa || 0)}</strong></div>`;
}

export function cabecalho() {
  return `<thead><tr>${COLUNAS.map(([campo, rotulo, classe]) => {
    if (!campo) return `<th>${rotulo}</th>`;
    const ativo = filtros.ordenar === campo;
    const seta = ativo ? icone(filtros.direcao === "asc" ? "seta-cima" : "seta-baixo", 13) : icone("ordenar", 13);
    return `<th class="${classe || ""} ${ativo ? "ordenado" : ""}"><button data-ordenar="${campo}">${rotulo} ${seta}</button></th>`;
  }).join("")}<th class="col-acoes">Ações</th></tr></thead>`;
}

function celulaValor(r, cancelado) {
  // Pago com juros/multa: mostra quanto saiu de fato e quanto foi de juros (em vermelho)
  const juros = Number(r.juros_multa || 0);
  const desconto = Number(r.desconto || 0);
  const extra = r.situacao === "pago" && (juros || desconto)
    ? `<small class="valor-pago-linha">pago ${brl(r.valor_pago || r.valor)}</small>
       ${juros ? `<small class="juros-linha" title="Juros/multa pagos">+ ${brl(juros)} juros</small>` : ""}
       ${desconto ? `<small class="desconto-linha">− ${brl(desconto)} desconto</small>` : ""}`
    : "";
  return `<td data-rotulo="Valor" class="num ${cancelado ? "riscado" : ""}">${brl(r.valor)}${extra}</td>`;
}

export function linha(r) {
  const pago = r.situacao === "pago";
  const cancelado = r.situacao === "cancelado";
  const pendente = r.pendente_gravacao
    ? `<span class="chip aviso" title="A planilha está aberta em outro programa; será gravado quando o arquivo for fechado">${icone("relogio", 12)} Aguardando gravação</span>`
    : "";
  return `<tr data-id="${r.id}" class="${r.pendente_gravacao ? "linha-pendente" : ""}">
    <td data-rotulo="Data prevista"><div class="celula-venc"><strong class="${cancelado ? "riscado" : ""}">${dataBR(r.vencimento)}</strong>${seloSituacao(r.situacao, r.dias_para_vencer)}${pendente}</div></td>
    <td data-rotulo="Recebedor" class="celula-benef"><strong title="${esc(r.recebedor)}">${esc(r.recebedor || "—")}</strong>
      <span>${r.descricao ? esc(r.descricao) : "&nbsp;"}</span>${r.centro_custo ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(r.centro_custo)}</span>` : ""}</td>
    <td data-rotulo="Chave Pix"><div class="celula-chave">
      <span class="chip">${esc(r.tipo_chave_rotulo || (r.copia_e_cola ? "Copia e Cola" : "—"))}</span>
      ${r.chave ? `<button class="linha-copiar mono" data-acao="copiar-chave" title="Copiar a chave: ${esc(r.chave_formatada)}">${icone("copiar", 13)}<span>${esc(r.chave_formatada)}</span></button>` : ""}
    </div></td>
    ${celulaValor(r, cancelado)}
    <td data-rotulo="Lançado em"><span class="sutil">${dataHoraBR(r.data_lancamento)}</span>${r.lancado_por ? `<small class="por-quem">por ${esc(r.lancado_por)}</small>` : ""}</td>
    <td class="col-acoes">
      ${pode("pagar") ? `<button class="btn-icone ${pago ? "" : "ok"}" data-acao="${pago ? "pendente" : "pago"}" title="${pago ? "Voltar para pendente" : "Marcar como pago"}">${icone(pago ? "desfazer" : "check", 16)}</button>` : ""}
      <button class="btn-icone" data-acao="qr" title="QR code e Pix Copia e Cola">${icone("qrcode", 16)}</button>
      ${pode("editar") ? `<button class="btn-icone" data-acao="editar" title="Editar">${icone("editar", 16)}</button>` : ""}
      <button class="btn-icone ${r.comprovante ? "marcado" : ""}" data-acao="detalhes" title="${r.comprovante ? "Comprovante anexado · histórico" : "Histórico e comprovante"}">${icone(r.comprovante ? "clipe" : "relogio", 16)}</button>
      ${r.arquivo ? `<a class="btn-icone" href="/api/pix/${r.id}/arquivo" target="_blank" rel="noopener" title="Ver arquivo original">${icone("arquivo", 16)}</a>` : ""}
      ${pode("editar") ? `<button class="btn-icone perigo" data-acao="excluir" title="${r.id < 0 ? "Cancelar lançamento" : "Excluir"}">${icone("lixeira", 16)}</button>` : ""}
    </td></tr>`;
}

export function renderizarTabela() {
  const tabela = tela.raiz.querySelector("#p-tabela");
  if (!tela.ultimo.itens.length) {
    const temFiltro = filtros.q || filtros.situacao || filtros.centro;
    tabela.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone(temFiltro ? "busca" : "pix", 26)}</div>
      <h3>${temFiltro ? "Nenhum Pix encontrado" : "Nenhum Pix lançado ainda"}</h3>
      <p>${temFiltro ? "Ajuste a busca ou os filtros." : "Preencha o tipo da chave, a chave e o valor acima, ou cole um Pix Copia e Cola."}</p>
      ${temFiltro ? `<button class="btn" data-acao="limpar-filtros">Limpar filtros</button>` : ""}</div>`;
    return;
  }
  tabela.innerHTML = `<table class="tabela">${cabecalho()}<tbody>${tela.ultimo.itens.map(linha).join("")}</tbody></table>`;
}

export function renderizarPaginacao() {
  const { total, pagina, por_pagina: porPagina } = tela.ultimo;
  const paginas = porPagina ? Math.max(1, Math.ceil(total / porPagina)) : 1;
  const inicio = total ? (pagina - 1) * (porPagina || total) + 1 : 0;
  const fim = porPagina ? Math.min(total, pagina * porPagina) : total;
  tela.raiz.querySelector("#p-paginacao").innerHTML = `
    <span>${inicio}–${fim} de ${total}</span>
    <div class="controles">
      <label class="sutil" for="p-por-pagina">Por página</label>
      <select id="p-por-pagina" class="input input-sm" style="width:auto">
        ${[10, 25, 50, 100, 0].map((n) => `<option value="${n}" ${n === filtros.por_pagina ? "selected" : ""}>${n || "Todos"}</option>`).join("")}
      </select>
      <button class="btn-icone" data-pagina="${pagina - 1}" ${pagina <= 1 ? "disabled" : ""} aria-label="Página anterior">${icone("chevron-esq", 16)}</button>
      <span>${pagina} / ${paginas}</span>
      <button class="btn-icone" data-pagina="${pagina + 1}" ${pagina >= paginas ? "disabled" : ""} aria-label="Próxima página">${icone("chevron-dir", 16)}</button>
    </div>`;
}

export async function alterarStatus(id, status) {
  const registro = await api.patch(`/api/pix/${id}/status`, { status });
  window.dispatchEvent(new Event("avisos:atualizar"));
  if (registro?.pendente_gravacao) window.dispatchEvent(new Event("gravacao:atualizar"));
  return registro;
}

export async function confirmarPagamento(id) {
  try {
    const r = await api.get(`/api/pix/${id}`);
    if (r.status === "Pago") {
      toast("Este Pix já está marcado como pago.", "info");
      return;
    }
    const confirmado = await confirmar({
      titulo: "Marcar Pix como pago",
      mensagem: `Confirmar o pagamento do Pix para ${r.recebedor || r.chave_formatada || "o recebedor"} (${brl(r.valor)}), `
        + `previsto para ${dataBR(r.vencimento)}? Os lembretes deste Pix serão encerrados.`,
      textoConfirmar: "Marcar como pago",
    });
    if (!confirmado) return;
    await alterarStatus(id, "Pago");
    toast("Pix marcado como pago. Os lembretes foram encerrados.", "ok");
    carregar();
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export async function abrirQr(r) {
  let dados;
  try {
    dados = await api.get(`/api/pix/${r.id}/copia-e-cola`);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return;
  }
  const { el } = abrirModal({
    titulo: `Pix para ${r.recebedor || r.chave_formatada || "o recebedor"}`,
    tamanho: "lg",
    corpo: `<div class="qr-pix">
      <img src="/api/pix/${r.id}/qrcode.svg?t=${Date.now()}" alt="QR code do Pix" width="220" height="220">
      <div class="qr-info">
        <div><span class="sutil">Valor</span><strong>${brl(r.valor)}</strong></div>
        ${r.chave ? `<div><span class="sutil">Chave ${esc(r.tipo_chave_rotulo)}</span><strong class="mono">${esc(r.chave_formatada)}</strong></div>` : ""}
        <div class="campo"><label>Pix Copia e Cola</label><textarea class="input mono" readonly>${esc(dados.copia_e_cola)}</textarea></div>
        ${dados.gerado ? `<p class="sutil">Código gerado a partir da chave e do valor. No app do banco, confira o nome do recebedor antes de confirmar.</p>` : ""}
      </div></div>`,
    rodape: `${r.chave ? `<button class="btn" data-copiar="chave">${icone("copiar", 16)} Copiar chave</button>` : ""}
      <button class="btn btn-primario" data-copiar="codigo">${icone("copiar", 16)} Copiar Pix Copia e Cola</button>`,
  });
  el.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-copiar]");
    if (!botao) return;
    if (botao.dataset.copiar === "chave") copiar(r.chave, "Chave Pix copiada");
    else copiar(dados.copia_e_cola, "Pix Copia e Cola copiado");
  });
}

export async function aoClicarTabela(e) {
  const ordenar = e.target.closest("[data-ordenar]");
  if (ordenar) {
    const campo = ordenar.dataset.ordenar;
    if (filtros.ordenar === campo) filtros.direcao = filtros.direcao === "asc" ? "desc" : "asc";
    else { filtros.ordenar = campo; filtros.direcao = campo === "data_lancamento" || campo === "valor" ? "desc" : "asc"; }
    carregar();
    return;
  }
  const alvo = e.target.closest("[data-acao]");
  if (!alvo) return;
  if (alvo.dataset.acao === "limpar-filtros") {
    Object.assign(filtros, { q: "", situacao: "", centro: "", pagina: 1 });
    tela.raiz.querySelector("#p-busca").value = "";
    tela.raiz.querySelector("#p-centro").value = "";
    sincronizarChips();
    carregar();
    return;
  }
  const id = Number(alvo.closest("[data-id]")?.dataset.id);
  const r = tela.ultimo.itens.find((item) => item.id === id);
  if (!r) return;
  try {
    switch (alvo.dataset.acao) {
      case "copiar-chave":
        copiar(r.chave, "Chave Pix copiada");
        break;
      case "pago":
        await alterarStatus(id, "Pago");
        toast("Pix marcado como pago", "ok", { acao: { rotulo: "Desfazer", executar: async () => { await alterarStatus(id, "Pendente"); carregar(); } } });
        carregar();
        break;
      case "pendente":
        await alterarStatus(id, "Pendente");
        toast("Voltou para pendente", "info");
        carregar();
        break;
      case "qr":
        abrirQr(r);
        break;
      case "detalhes":
        abrirDetalhes("pix", r, () => carregar());
        break;
      case "editar":
        abrirFormularioPix({}, { registro: r, aoSalvar: () => carregar() });
        break;
      case "excluir": {
        const pendente = id < 0;
        const ok = await confirmar({
          titulo: pendente ? "Cancelar lançamento" : "Excluir Pix",
          mensagem: pendente
            ? `Cancelar o lançamento do Pix para ${r.recebedor || r.chave_formatada} que ainda aguarda gravação?`
            : `Excluir o Pix para ${r.recebedor || r.chave_formatada} (${brl(r.valor)}) da planilha? Esta ação não pode ser desfeita.`,
          textoConfirmar: pendente ? "Cancelar lançamento" : "Excluir",
          perigo: true,
        });
        if (!ok) break;
        await api.del(`/api/pix/${id}`);
        toast(pendente ? "Lançamento cancelado" : "Pix excluído", "ok");
        window.dispatchEvent(new Event("gravacao:atualizar"));
        carregar();
        break;
      }
      default:
        break;
    }
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

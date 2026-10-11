// Boletos lançados · lista, paginação e ações em lote.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, compacto, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, isoDeData, mensagemErro, numeroBR,
  parseValor, seloSituacao, toast,
} from "../../ui.js";
import { abrirDetalhes } from "../../detalhes.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { pode } from "../../estado.js";
import { COLUNAS, filtros, selecionados, tela } from "./estado.js";
import { carregarCalendario } from "./calendario.js";
import { abrirEdicao } from "./edicao.js";
import { sincronizarControles } from "./montagem.js";

export async function carregar() {
  if (!tela.raiz) return;
  if (tela.modo === "calendario") return carregarCalendario();
  const tabela = tela.raiz.querySelector("#tabela");
  tabela.classList.add("carregando");
  const minha = ++tela.requisicao;
  try {
    const dados = await api.get("/api/boletos", filtros);
    if (!tela.raiz || minha !== tela.requisicao) return;
    tela.ultimo = dados;
    renderizarResumo(dados.resumo);
    renderizarTabela();
    renderizarPaginacao();
    renderizarAcoesLote();
  } catch (erro) {
    if (!tela.raiz) return;
    tabela.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar os boletos</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  } finally {
    tela.raiz?.querySelector("#tabela")?.classList.remove("carregando");
  }
}

export function renderizarResumo(r, titulo = "Registros") {
  tela.raiz.querySelector("#resumo").innerHTML = `
    <div class="card resumo-item"><span>${titulo}</span><strong>${r.quantidade}</strong></div>
    <div class="card resumo-item"><span>Valor total</span><strong>${brl(r.valor_total)}</strong></div>
    <div class="card resumo-item"><span>Pendente</span><strong>${brl(r.valor_pendente)}</strong></div>
    <div class="card resumo-item erro"><span>Vencido</span><strong>${brl(r.valor_vencido)}</strong></div>
    <div class="card resumo-item ok"><span>Pago</span><strong>${brl(r.valor_pago)}</strong></div>
    <div class="card resumo-item ${r.juros_multa ? "erro" : ""}" title="Juros e multas pagos nos boletos desta lista">
      <span>Juros e multas pagos${r.pagos_com_juros ? ` (${r.pagos_com_juros})` : ""}</span><strong>${brl(r.juros_multa || 0)}</strong></div>`;
}

export function cabecalho() {
  const todosMarcados = tela.ultimo.itens.length > 0 && tela.ultimo.itens.every((r) => selecionados.has(r.id));
  return `<thead><tr>
    <th class="col-check"><input type="checkbox" data-marcar="todos" ${todosMarcados ? "checked" : ""} aria-label="Selecionar todos"></th>
    ${COLUNAS.map(([campo, rotulo, classe]) => {
      if (!campo) return `<th>${rotulo}</th>`;
      const ativo = filtros.ordenar === campo;
      const seta = ativo ? icone(filtros.direcao === "asc" ? "seta-cima" : "seta-baixo", 13) : icone("ordenar", 13);
      return `<th class="${classe || ""} ${ativo ? "ordenado" : ""}"><button data-ordenar="${campo}">${rotulo} ${seta}</button></th>`;
    }).join("")}
    <th class="col-acoes">Ações</th></tr></thead>`;
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
  const detalhes = [r.numero_documento ? `Doc. ${esc(r.numero_documento)}` : "", r.documento_beneficiario ? esc(r.documento_beneficiario) : "", r.emissor ? esc(r.emissor) : ""]
    .filter(Boolean).join(" · ");
  const pendente = r.pendente_gravacao
    ? `<span class="chip aviso" title="A planilha está aberta em outro programa; será gravado quando o arquivo for fechado">${icone("relogio", 12)} Aguardando gravação</span>`
    : "";
  return `<tr data-id="${r.id}" class="${selecionados.has(r.id) ? "selecionado" : ""} ${r.pendente_gravacao ? "linha-pendente" : ""}">
    <td class="col-check"><input type="checkbox" data-marcar="${r.id}" ${selecionados.has(r.id) ? "checked" : ""} aria-label="Selecionar boleto"></td>
    <td data-rotulo="Vencimento"><div class="celula-venc"><strong class="${cancelado ? "riscado" : ""}">${dataBR(r.vencimento)}</strong>${seloSituacao(r.situacao, r.dias_para_vencer)}${pendente}</div></td>
    <td data-rotulo="Beneficiário" class="celula-benef"><strong title="${esc(r.beneficiario)}">${esc(r.beneficiario || "—")}</strong><span>${detalhes || "&nbsp;"}</span>${r.centro_custo ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(r.centro_custo)}</span>` : ""}</td>
    ${celulaValor(r, cancelado)}
    <td data-rotulo="Linha digitável">${r.linha_digitavel
      ? `<button class="linha-copiar mono" data-acao="copiar" title="Copiar: ${esc(r.linha_digitavel)}">${icone("copiar", 13)}<span>${esc(r.linha_digitavel)}</span></button>`
      : `<span class="sutil">—</span>`}</td>
    <td data-rotulo="Lançado em"><span class="sutil">${dataHoraBR(r.data_lancamento)}</span>${r.lancado_por ? `<small class="por-quem">por ${esc(r.lancado_por)}</small>` : ""}</td>
    <td class="col-acoes">
      ${pode("pagar") ? `<button class="btn-icone ${pago ? "" : "ok"}" data-acao="${pago ? "pendente" : "pago"}" title="${pago ? "Voltar para pendente" : "Marcar como pago"}">${icone(pago ? "desfazer" : "check", 16)}</button>` : ""}
      ${pode("editar") ? `<button class="btn-icone" data-acao="editar" title="Editar">${icone("editar", 16)}</button>` : ""}
      <button class="btn-icone ${r.comprovante ? "marcado" : ""}" data-acao="detalhes" title="${r.comprovante ? "Comprovante anexado · histórico" : "Histórico e comprovante"}">${icone(r.comprovante ? "clipe" : "relogio", 16)}</button>
      ${r.arquivo ? `<a class="btn-icone" href="/api/boletos/${r.id}/arquivo" target="_blank" rel="noopener" title="Ver arquivo original">${icone("arquivo", 16)}</a>` : ""}
      ${pode("editar") ? `<button class="btn-icone perigo" data-acao="excluir" title="${r.id < 0 ? "Cancelar lançamento" : "Excluir"}">${icone("lixeira", 16)}</button>` : ""}
    </td></tr>`;
}

export function renderizarTabela() {
  const tabela = tela.raiz.querySelector("#tabela");
  if (!tela.ultimo.itens.length) {
    const temFiltro = filtros.q || filtros.situacao || filtros.centro || filtros.de || filtros.ate;
    tabela.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone(temFiltro ? "busca" : "boleto", 26)}</div>
      <h3>${temFiltro ? "Nenhum boleto encontrado" : "A planilha ainda está vazia"}</h3>
      <p>${temFiltro ? "Ajuste a busca ou os filtros." : "Leia um boleto para começar."}</p>
      ${temFiltro ? `<button class="btn" data-acao="limpar-filtros">Limpar filtros</button>`
        : pode("lancar") ? `<a class="btn btn-primario" href="#/ler">${icone("upload", 16)} Ler boletos</a>` : ""}</div>`;
    return;
  }
  tabela.innerHTML = `<table class="tabela">${cabecalho()}<tbody>${tela.ultimo.itens.map(linha).join("")}</tbody></table>`;
}

export function renderizarPaginacao() {
  const { total, pagina, por_pagina: porPagina } = tela.ultimo;
  const paginas = porPagina ? Math.max(1, Math.ceil(total / porPagina)) : 1;
  const inicio = total ? (pagina - 1) * (porPagina || total) + 1 : 0;
  const fim = porPagina ? Math.min(total, pagina * porPagina) : total;
  tela.raiz.querySelector("#paginacao").innerHTML = `
    <span>${inicio}–${fim} de ${total}</span>
    <div class="controles">
      <label class="sutil" for="por-pagina">Por página</label>
      <select id="por-pagina" class="input input-sm" style="width:auto">
        ${[10, 25, 50, 100, 0].map((n) => `<option value="${n}" ${n === filtros.por_pagina ? "selected" : ""}>${n || "Todos"}</option>`).join("")}
      </select>
      <button class="btn-icone" data-pagina="${pagina - 1}" ${pagina <= 1 ? "disabled" : ""} aria-label="Página anterior">${icone("chevron-esq", 16)}</button>
      <span>${pagina} / ${paginas}</span>
      <button class="btn-icone" data-pagina="${pagina + 1}" ${pagina >= paginas ? "disabled" : ""} aria-label="Próxima página">${icone("chevron-dir", 16)}</button>
    </div>`;
}

export function renderizarAcoesLote() {
  const barra = tela.raiz.querySelector("#acoes-lote");
  barra.hidden = selecionados.size === 0;
  barra.innerHTML = `<span>${selecionados.size} selecionado(s)</span>
    ${pode("pagar") ? `<button class="btn btn-sm" data-lote="pago">${icone("check", 14)} Marcar pagos</button>
    <button class="btn btn-sm" data-lote="pendente">${icone("desfazer", 14)} Marcar pendentes</button>` : ""}
    ${pode("editar") ? `<button class="btn btn-sm" data-lote="cancelado">${icone("x", 14)} Cancelar</button>` : ""}
    ${pode("lancar") ? `<button class="btn btn-sm" data-lote="centro">${icone("etiqueta", 14)} Centro de custo</button>` : ""}
    ${pode("editar") ? `<button class="btn btn-sm" data-lote="excluir" style="color:var(--erro)">${icone("lixeira", 14)} Excluir</button>` : ""}
    <span class="espaco"></span>
    <button class="btn btn-sm btn-fantasma" data-lote="limpar">Limpar seleção</button>`;
}

export function aoMarcar(e) {
  const alvo = e.target.closest("[data-marcar]");
  if (!alvo) return;
  if (alvo.dataset.marcar === "todos") {
    tela.ultimo.itens.forEach((r) => (alvo.checked ? selecionados.add(r.id) : selecionados.delete(r.id)));
    renderizarTabela();
  } else {
    const id = Number(alvo.dataset.marcar);
    if (alvo.checked) selecionados.add(id); else selecionados.delete(id);
    alvo.closest("tr").classList.toggle("selecionado", alvo.checked);
  }
  renderizarAcoesLote();
}

export function aoPaginar(e) {
  const botao = e.target.closest("[data-pagina]");
  if (!botao || botao.disabled) return;
  filtros.pagina = Number(botao.dataset.pagina);
  carregar();
  tela.raiz.querySelector(".tabela-card").scrollIntoView({ behavior: "smooth", block: "start" });
}

export async function alterarStatus(id, status) {
  const registro = await api.patch(`/api/boletos/${id}/status`, { status });
  window.dispatchEvent(new Event("avisos:atualizar"));
  if (registro?.pendente_gravacao) window.dispatchEvent(new Event("gravacao:atualizar"));
  return registro;
}

export async function confirmarPagamento(id) {
  try {
    const r = await api.get(`/api/boletos/${id}`);
    if (r.status === "Pago") {
      toast("Este boleto já está marcado como pago.", "info");
      return;
    }
    const confirmado = await confirmar({
      titulo: "Marcar como pago",
      mensagem: `Confirmar o pagamento do boleto de ${r.beneficiario || "beneficiário não informado"} (${brl(r.valor)}), `
        + `vencimento ${dataBR(r.vencimento)}? Os lembretes deste boleto serão encerrados.`,
      textoConfirmar: "Marcar como pago",
    });
    if (!confirmado) return;
    await alterarStatus(id, "Pago");
    toast("Boleto marcado como pago. Os lembretes foram encerrados.", "ok");
    carregar();
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export async function executarAcao(acao, registro, aoConcluir = carregar) {
  const id = registro.id;
  switch (acao) {
    case "copiar":
      copiar((registro.linha_digitos || registro.linha_digitavel || "").replace(/\D/g, ""), "Linha digitável copiada");
      return;
    case "pago":
      await alterarStatus(id, "Pago");
      toast("Marcado como pago", "ok", { acao: { rotulo: "Desfazer", executar: async () => { await alterarStatus(id, "Pendente"); aoConcluir(); } } });
      aoConcluir();
      return;
    case "pendente":
      await alterarStatus(id, "Pendente");
      toast("Voltou para pendente", "info");
      aoConcluir();
      return;
    case "editar":
      abrirEdicao(registro);
      return;
    case "detalhes":
      abrirDetalhes("boletos", registro, aoConcluir);
      return;
    case "excluir": {
      const pendente = id < 0;
      if (await confirmar({
        titulo: pendente ? "Cancelar lançamento" : "Excluir boleto",
        mensagem: pendente
          ? `Cancelar o lançamento de ${registro.beneficiario || "beneficiário não informado"} que ainda aguarda gravação?`
          : `Excluir o boleto de ${registro.beneficiario || "beneficiário não informado"} (${brl(registro.valor)}) da planilha? Esta ação não pode ser desfeita.`,
        textoConfirmar: pendente ? "Cancelar lançamento" : "Excluir",
        perigo: true,
      })) {
        await api.del(`/api/boletos/${id}`);
        selecionados.delete(id);
        toast(pendente ? "Lançamento cancelado" : "Boleto excluído", "ok");
        window.dispatchEvent(new Event("gravacao:atualizar"));
        aoConcluir();
      }
      return;
    }
    default:
      return;
  }
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
    Object.assign(filtros, { q: "", situacao: "", centro: "", de: "", ate: "", pagina: 1 });
    tela.raiz.querySelector("#f-busca").value = "";
    sincronizarControles();
    carregar();
    return;
  }
  const id = Number(alvo.closest("[data-id]")?.dataset.id);
  const registro = tela.ultimo.itens.find((r) => r.id === id);
  if (!registro) return;
  try {
    await executarAcao(alvo.dataset.acao, registro);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export async function aoAcaoLote(e) {
  const botao = e.target.closest("[data-lote]");
  if (!botao) return;
  const acao = botao.dataset.lote;
  const ids = [...selecionados];
  if (acao === "limpar") { selecionados.clear(); renderizarTabela(); renderizarAcoesLote(); return; }
  if (acao === "centro") {
    const nome = await escolherCentro({
      titulo: "Centro de custo",
      descricao: `Define onde foi gasto para ${ids.length === 1 ? "o boleto selecionado" : `os ${ids.length} boletos selecionados`}.`,
    });
    if (nome === null) return;
    botao.disabled = true;
    let alterados = 0;
    for (const id of ids) {
      try {
        await api.put(`/api/boletos/${id}`, { centro_custo: nome });
        alterados += 1;
      } catch (erro) {
        toast(mensagemErro(erro), "erro", { duracao: 6000 });
        break;
      }
    }
    selecionados.clear();
    toast(nome ? `Centro de custo "${nome}" definido em ${alterados} boleto(s)` : `Centro de custo removido de ${alterados} boleto(s)`, "ok");
    window.dispatchEvent(new Event("gravacao:atualizar"));
    carregar();
    return;
  }
  if (acao === "excluir" && !(await confirmar({
    titulo: "Excluir boletos", mensagem: `Excluir ${ids.length} boleto(s) da planilha? Esta ação não pode ser desfeita.`,
    textoConfirmar: `Excluir ${ids.length}`, perigo: true,
  }))) return;

  botao.disabled = true;
  let ok = 0;
  for (const id of ids) {
    try {
      if (acao === "excluir") await api.del(`/api/boletos/${id}`);
      else await alterarStatus(id, { pago: "Pago", pendente: "Pendente", cancelado: "Cancelado" }[acao]);
      ok += 1;
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
      break;
    }
  }
  selecionados.clear();
  toast(`${ok} boleto(s) atualizado(s)`, "ok");
  window.dispatchEvent(new Event("gravacao:atualizar"));
  carregar();
}

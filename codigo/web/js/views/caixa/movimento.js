// Caixa · movimento do período: totais, lançamentos e o formulário de entrada/saída.
import { api } from "../../api.js";
import { NOVO_CENTRO, carregarCentros, invalidarCentros, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, toast } from "../../ui.js";
import { tela } from "./estado.js";

export function htmlKpis(d) {
  return `<section class="resumo-lista caixa-kpis">
    <div class="resumo-item ok"><span>Entradas</span><strong>${brl(d.entradas.total)}</strong>
      <small class="sutil">${d.entradas.quantidade} lançamento(s)</small></div>
    <div class="resumo-item erro"><span>Saídas</span><strong>${brl(d.saidas.total)}</strong>
      <small class="sutil">${d.saidas.quantidade} lançamento(s)</small></div>
    <div class="resumo-item ${d.saldo_periodo < 0 ? "erro" : "ok"}"><span>Saldo do período</span>
      <strong>${brl(d.saldo_periodo)}</strong><small class="sutil">entradas − saídas</small></div>
    <div class="resumo-item"><span>Saldo em caixa</span><strong>${brl(d.saldo_caixa)}</strong>
      <small class="sutil">no fim do período (começou com ${brl(d.saldo_inicial)})</small></div>
  </section>`;
}

export function htmlMovimento(d) {
  const filtro = tela.filtro;
  const lista = (d.lancamentos || []).filter((r) => !filtro || r.movimento === filtro);
  return `${htmlKpis(d)}
    <section class="card tabela-card">
      <div class="caixa-filtro">
        <div class="alternar-modo" role="tablist" aria-label="Mostrar">
          ${[["", "Tudo"], ["Entrada", "Entradas"], ["Saída", "Saídas"]].map(([valor, rotulo]) =>
            `<button role="tab" data-filtro-caixa="${valor}" class="${filtro === valor ? "ativo" : ""}">${rotulo}</button>`).join("")}
        </div>
        <span class="sutil">${lista.length} lançamento(s) em ${esc(d.periodo.rotulo)}</span>
      </div>
      <div class="tabela-wrap">${lista.length ? tabela(lista) : `<div class="vazio">
        <div class="vazio-icone">${icone("caixa", 26)}</div><h3>Nada no caixa neste período</h3>
        <p>Lance uma entrada ou uma saída acima, ou mande a foto do cupom para o bot do caixa.</p></div>`}</div>
    </section>`;
}

function tabela(lista) {
  return `<table class="tabela">
    <thead><tr><th>Data</th><th></th><th class="num">Valor</th><th>O que foi pedido / comprado</th><th>Onde</th>
      <th>Centro de custo</th><th>Quem</th><th class="col-acoes"></th></tr></thead>
    <tbody>${lista.map((r) => `<tr>
      <td>${dataBR(r.data)}${r.hora ? ` <small class="sutil">${esc(r.hora)}</small>` : ""}</td>
      <td><span class="chip ${r.movimento === "Entrada" ? "ok" : "erro"}">${r.movimento === "Entrada" ? "Entrada" : "Saída"}</span></td>
      <td class="num ${r.movimento === "Entrada" ? "valor-entrada" : "valor-saida"}">${r.movimento === "Entrada" ? "+" : "−"} ${brl(r.valor)}</td>
      <td>${esc(r.descricao || "")}</td><td>${esc(r.local || "")}</td>
      <td>${r.centro_custo ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(r.centro_custo)}</span>` : ""}</td>
      <td>${esc(r.pessoa || "")}${r.lancado_por ? `<small class="por-quem">lançado por ${esc(r.lancado_por)}</small>` : ""}</td>
      <td class="col-acoes">
        ${r.arquivo ? `<a class="btn-icone" href="/${esc(r.arquivo)}" target="_blank" rel="noopener" title="Ver comprovante">${icone("clipe", 15)}</a>` : ""}
        <button class="btn-icone" data-acao="historico-caixa" data-id="${r.id}" title="Histórico">${icone("relogio", 15)}</button>
        <button class="btn-icone" data-acao="editar-caixa" data-id="${r.id}" title="Editar">${icone("editar", 15)}</button>
        <button class="btn-icone perigo" data-acao="cancelar-caixa" data-id="${r.id}" title="Cancelar lançamento">${icone("lixeira", 15)}</button>
      </td></tr>`).join("")}</tbody></table>`;
}

// ------------------------------------------------------------------ formulário

/** ``registro``: lançamento a editar (ou os dados já lidos de um comprovante). ``enviar(corpo)`` substitui o POST. */
export async function formularioLancamento(registro = null, movimentoInicial = "Saída", enviar = null) {
  const r = registro || {};
  const edicao = Boolean(r.id);
  let movimento = r.movimento || movimentoInicial;
  const centros = await carregarCentros().catch(() => []);
  const { el, fechar } = abrirModal({
    titulo: edicao ? "Editar lançamento do caixa" : enviar ? "Revisar e lançar no caixa" : "Novo lançamento no caixa",
    corpo: `<form class="grade-campos" data-form-caixa>
      <div class="campo col-2"><div class="alternar-modo" role="tablist" aria-label="Entrada ou saída">
        <button type="button" data-movimento="Entrada" class="${movimento === "Entrada" ? "ativo" : ""}">${icone("mais", 14)} Entrada</button>
        <button type="button" data-movimento="Saída" class="${movimento === "Saída" ? "ativo" : ""}">${icone("desfazer", 14)} Saída</button>
      </div></div>
      <div class="campo"><label for="cx-valor">Valor</label>
        <input id="cx-valor" name="valor" class="input" inputmode="decimal" value="${r.valor ? numeroBR(r.valor) : ""}" required autofocus></div>
      <div class="campo"><label for="cx-data">Data</label>
        <input id="cx-data" name="data" type="date" class="input" value="${esc(String(r.data || hojeISO()).slice(0, 10))}"></div>
      <div class="campo col-2"><label for="cx-descricao" data-rotulo-descricao>${movimento === "Entrada" ? "O que foi pedido" : "O que foi comprado"}</label>
        <input id="cx-descricao" name="descricao" class="input" value="${esc(r.descricao || "")}" maxlength="200"
          placeholder="${movimento === "Entrada" ? "Ex.: Pedido 7043 - 12 m³ de brita" : "Ex.: gasolina da caminhonete"}"></div>
      <div class="campo" data-so-saida ${movimento === "Entrada" ? "hidden" : ""}><label for="cx-local">Onde foi gasto</label>
        <input id="cx-local" name="local" class="input" value="${esc(r.local || "")}" maxlength="120" placeholder="Loja, posto, fornecedor…"></div>
      <div class="campo" data-so-saida ${movimento === "Entrada" ? "hidden" : ""}><label for="cx-centro">Centro de custo</label>
        <select id="cx-centro" name="centro_custo" class="input">${opcoesCentro(centros, r.centro_custo || "")}</select></div>
      <div class="campo"><label for="cx-pessoa">Quem</label>
        <input id="cx-pessoa" name="pessoa" class="input" value="${esc(r.pessoa || "")}" maxlength="60"
          placeholder="${movimento === "Entrada" ? "Quem pagou" : "Quem gastou"}"></div>
      <div class="campo"><label for="cx-hora">Hora</label>
        <input id="cx-hora" name="hora" type="time" class="input" value="${esc(r.hora || "")}"></div>
      <div class="campo col-2"><label for="cx-obs">Observações</label>
        <input id="cx-obs" name="observacoes" class="input" value="${esc(r.observacoes || "")}" maxlength="300"></div>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} ${edicao ? "Salvar" : "Lançar no caixa"}</button>`,
  });

  const formulario = el.querySelector("[data-form-caixa]");
  el.querySelectorAll("[data-movimento]").forEach((botao) => botao.addEventListener("click", () => {
    movimento = botao.dataset.movimento;
    el.querySelectorAll("[data-movimento]").forEach((b) => b.classList.toggle("ativo", b === botao));
    el.querySelectorAll("[data-so-saida]").forEach((c) => { c.hidden = movimento === "Entrada"; });
    el.querySelector("[data-rotulo-descricao]").textContent = movimento === "Entrada" ? "O que foi pedido" : "O que foi comprado";
  }));
  const select = el.querySelector("#cx-centro");
  let anterior = select.value;
  select.addEventListener("change", async () => {
    if (select.value === NOVO_CENTRO) {
      anterior = await tratarNovoCentro(select, anterior);
      invalidarCentros();
    } else {
      anterior = select.value;
    }
  });

  const salvar = async (evento) => {
    evento?.preventDefault();
    const dados = Object.fromEntries(new FormData(formulario));
    const corpo = { ...dados, movimento, valor: parseValor(dados.valor) };
    if (movimento === "Entrada") Object.assign(corpo, { local: "", centro_custo: "" });
    if (!corpo.valor) {
      toast("Informe o valor.", "aviso");
      return;
    }
    const limpo = Object.fromEntries(Object.entries(corpo).filter(([k, v]) => v !== "" || ["local", "centro_custo"].includes(k)));
    try {
      if (enviar) await enviar(limpo);
      else if (edicao) await api.put(`/api/caixa/${r.id}`, limpo);
      else await api.post("/api/caixa", limpo);
      toast(edicao ? "Lançamento atualizado." : `${movimento === "Entrada" ? "Entrada" : "Saída"} de ${brl(corpo.valor)} lançada no caixa.`, "ok");
      fechar(true);
      window.dispatchEvent(new Event("caixa:atualizar"));
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  formulario.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

export async function editarLancamento(id) {
  const registro = (tela.dados?.lancamentos || []).find((r) => r.id === Number(id));
  if (registro) formularioLancamento(registro);
}

export async function cancelarLancamento(id) {
  const registro = (tela.dados?.lancamentos || []).find((r) => r.id === Number(id));
  if (!registro) return;
  if (!await confirmar({ titulo: "Cancelar lançamento",
                         mensagem: `Cancelar a ${registro.movimento === "Entrada" ? "entrada" : "saída"} de ${brl(registro.valor)}? Ela sai dos totais, mas continua no histórico.`,
                         textoConfirmar: "Cancelar lançamento", perigo: true })) return;
  try {
    await api.post(`/api/caixa/${id}/cancelar`, {});
    toast("Lançamento cancelado.", "ok");
    window.dispatchEvent(new Event("caixa:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

export async function historicoLancamento(id) {
  let eventos = [];
  try {
    eventos = (await api.get(`/api/caixa/${id}/historico`)).eventos;
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
    return;
  }
  abrirModal({
    titulo: "Histórico do lançamento",
    corpo: eventos.length ? `<ul class="lista-mini">${eventos.map((e) => `<li><div class="info">
        <div class="titulo">${esc(e.acao)} · ${dataHoraBR(e.quando)}</div>
        <div class="sutil">${esc(e.usuario || "")}${e.detalhes ? ` · ${esc(e.detalhes)}` : ""}</div></div></li>`).join("")}</ul>`
      : `<p class="sutil">Sem histórico.</p>`,
    rodape: `<button class="btn" data-fechar>Fechar</button>`,
  });
}

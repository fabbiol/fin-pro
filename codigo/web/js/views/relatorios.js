// Tela: Relatórios — o relatório geral do mês e o caminho para todos os relatórios do sistema, num lugar só.
import { api } from "../api.js";
import { pode } from "../estado.js";
import { icone } from "../icons.js";
import { abrirModal, brl, dataBR, dataHoraBR, esc, isoDeData, mensagemErro, toast } from "../ui.js";

let raiz = null;
let mes = isoDeData(new Date()).slice(0, 7);
let requisicao = 0;

const litros = (v) => `${Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} L`;

function mesVizinho(deslocamento) {
  const [ano, m] = mes.split("-").map(Number);
  return isoDeData(new Date(ano, m - 1 + deslocamento, 1)).slice(0, 7);
}

function url(caminho, params) {
  const u = new URL(caminho, location.origin);
  Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
  return u.toString();
}

export async function montar(el, params) {
  raiz = el;
  if (/^\d{4}-\d{2}$/.test(params?.get("mes") || "")) mes = params.get("mes");
  el.innerHTML = `
    <section class="card barra-filtros">
      <div class="filtros-linha">
        <div class="periodo">
          <button class="btn-icone" data-r="anterior" aria-label="Mês anterior">${icone("chevron-esq", 16)}</button>
          <input type="month" id="r-mes" class="input input-sm" value="${mes}" aria-label="Mês do relatório">
          <button class="btn-icone" data-r="proximo" aria-label="Próximo mês">${icone("chevron-dir", 16)}</button>
          <button class="btn btn-sm btn-fantasma" data-r="hoje">Este mês</button>
        </div>
        <span class="espaco"></span>
        <a class="btn btn-primario" id="r-excel" href="#" data-download title="Resumo, juros e multas e os últimos 12 meses">
          ${icone("planilha", 16)} Excel do relatório geral</a>
      </div>
    </section>
    <div id="r-geral"><div class="card esqueleto" style="height:300px"></div></div>
    <section class="rel-catalogo" id="r-catalogo"></section>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  await carregar();
}

export function desmontar() {
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz = null;
}

async function carregar() {
  if (!raiz) return;
  raiz.querySelector("#r-mes").value = mes;
  raiz.querySelector("#r-excel").href = url("/api/relatorio-geral/arquivo", { mes });
  raiz.querySelector("#r-catalogo").innerHTML = htmlCatalogo();
  const alvo = raiz.querySelector("#r-geral");
  const minha = ++requisicao;
  try {
    const r = await api.get("/api/relatorio-geral", { mes });
    if (!raiz || minha !== requisicao) return;
    alvo.innerHTML = htmlGeral(r);
  } catch (erro) {
    if (raiz && minha === requisicao) alvo.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível montar o relatório</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

// ------------------------------------------------------------------ relatório geral do mês

function kpi(rotulo, valor, detalhe = "", classe = "") {
  return `<div class="card resumo-item ${classe}"><span>${rotulo}</span><strong>${valor}</strong>${detalhe ? `<small class="sutil">${detalhe}</small>` : ""}</div>`;
}

function falhou(parte) {
  return parte?.erro ? `<p class="sutil">${icone("alerta", 14)} Não foi possível ler esta parte agora: ${esc(parte.erro)}</p>` : "";
}

function htmlGeral(r) {
  const c = r.contas;
  const p = r.previsao;
  const partes = [];
  if (c && !c.erro) {
    const t = c.por_tipo;
    partes.push(`
      <section class="card fechamento-secao">
        <h3>${icone("check", 17)} Pagamentos de ${esc(r.titulo)} <small class="sutil">pela data em que foram pagos</small></h3>
        <div class="resumo-lista rel-kpis">
          ${kpi("Pago no mês", brl(c.pago), `${c.quantidade_pagos} pagamento(s)`, "ok")}
          ${kpi("Boletos", brl(t.Boleto.valor), `${t.Boleto.quantidade} pago(s)`)}
          ${kpi("Pix", brl(t.Pix.valor), `${t.Pix.quantidade} pago(s)`)}
          ${kpi("Dinheiro (caixa)", brl(t.Dinheiro.valor), `${t.Dinheiro.quantidade} saída(s)`)}
          ${kpi("Juros e multas", brl(c.juros_multa), c.pagos_com_atraso ? `${c.pagos_com_atraso} pago(s) com atraso` : "nenhum atraso", c.juros_multa ? "erro" : "")}
          ${c.desconto ? kpi("Descontos", brl(c.desconto), "", "ok") : ""}
          ${kpi("Ainda em aberto", brl(c.vencimento.em_aberto), `do que vence em ${esc(r.titulo)}`)}
          ${kpi(`Em atraso (${c.vencimento.quantidade_atrasados})`, brl(c.vencimento.atrasado), "", c.vencimento.atrasado ? "erro" : "")}
          ${p ? kpi("A pagar em 7 dias", brl(p["7_dias"]), `30 dias: ${brl(p["30_dias"])}`) : ""}
        </div>
        ${c.sem_comprovante ? `<p class="sutil">${icone("clipe", 14)} ${c.sem_comprovante} pagamento(s) do mês sem comprovante anexado —
          <a href="#/comprovantes?comprovante=sem">ver quais são</a>.</p>` : ""}
      </section>`);
  } else if (c?.erro) {
    partes.push(`<section class="card fechamento-secao"><h3>Pagamentos</h3>${falhou(c)}</section>`);
  } else if (p) {
    partes.push(`<section class="card fechamento-secao"><h3>${icone("relogio", 17)} Previsão de saídas</h3>
      <div class="resumo-lista rel-kpis">${kpi("Em atraso", brl(p.em_atraso.total), `${p.em_atraso.quantidade} lançamento(s)`, p.em_atraso.total ? "erro" : "")}
        ${kpi("Próximos 7 dias", brl(p["7_dias"]))}${kpi("Próximos 30 dias", brl(p["30_dias"]))}</div></section>`);
  }

  const modulos = [htmlCaixa(r.caixa), htmlDiesel(r.diesel), htmlEmpresas(r.empresas)].filter(Boolean);
  if (modulos.length) partes.push(`<div class="rel-modulos">${modulos.join("")}</div>`);
  if (c && !c.erro) partes.push(htmlJuros(c, r.titulo));
  if (Array.isArray(r.historico)) partes.push(htmlHistorico(r.historico, r.mes));
  if (c && !c.erro && c.por_centro.length) partes.push(htmlCentros(c.por_centro, r.titulo));
  partes.push(`<p class="sutil">Gerado em ${dataHoraBR(r.gerado_em)}.</p>`);
  return partes.join("");
}

function htmlCaixa(cx) {
  if (!cx) return "";
  return `<section class="card rel-modulo">
    <header><h3>${icone("caixa", 17)} Caixa</h3><a class="btn btn-sm btn-fantasma" href="#/caixa?aba=relatorios">Abrir relatório</a></header>
    ${cx.erro ? falhou(cx) : `<dl class="rel-numeros">
      <div><dt>Entradas</dt><dd class="ok">${brl(cx.entradas.total)}</dd><small>${cx.entradas.quantidade} lançamento(s)</small></div>
      <div><dt>Saídas</dt><dd class="erro">${brl(cx.saidas.total)}</dd><small>${cx.saidas.quantidade} lançamento(s)</small></div>
      <div><dt>Saldo do mês</dt><dd>${brl(cx.saldo_periodo)}</dd></div>
      <div><dt>Saldo em caixa</dt><dd>${brl(cx.saldo_caixa)}</dd><small>no fim do mês</small></div></dl>
      ${cx.por_centro.length ? `<p class="sutil">Onde mais saiu: ${cx.por_centro.slice(0, 3).map((g) => `${esc(g.nome)} (${brl(g.total)})`).join(" · ")}</p>` : ""}`}
  </section>`;
}

function htmlDiesel(d) {
  if (!d) return "";
  return `<section class="card rel-modulo">
    <header><h3>${icone("diesel", 17)} Diesel</h3><a class="btn btn-sm btn-fantasma" href="#/diesel?aba=relatorios">Semanal, quinzenal e mensal</a></header>
    ${d.erro ? falhou(d) : `<dl class="rel-numeros">
      <div><dt>Comprado</dt><dd>${litros(d.comprado.litros)}</dd><small>${brl(d.comprado.valor)} · ${d.comprado.quantidade} compra(s)</small></div>
      <div><dt>Abastecido</dt><dd>${litros(d.abastecido.litros)}</dd><small>${d.abastecido.quantidade} abastecimento(s)</small></div>
      <div><dt>Custo dos abastecimentos</dt><dd>${brl(d.abastecido.custo)}</dd></div>
      <div><dt>Saldo no posto</dt><dd>${brl(d.saldo)}</dd><small>no fim do mês</small></div></dl>
      ${d.por_maquina.length ? `<p class="sutil">Quem mais consumiu: ${d.por_maquina.slice(0, 3).map((m) => `${esc(m.maquina)} (${litros(m.litros)})`).join(" · ")}</p>` : ""}`}
  </section>`;
}

function htmlEmpresas(e) {
  if (!e) return "";
  return `<section class="card rel-modulo">
    <header><h3>${icone("carteira", 17)} Empresas</h3><a class="btn btn-sm btn-fantasma" href="#/empresas?aba=fechamentos">Fechamentos</a></header>
    ${e.erro ? falhou(e) : `<dl class="rel-numeros">
      <div><dt>Faturado no fechamento</dt><dd>${brl(e.faturado)}</dd></div>
      <div><dt>Falta receber</dt><dd class="${e.falta ? "erro" : ""}">${brl(e.falta)}</dd><small>em aberto no total: ${brl(e.em_aberto)}</small></div>
      <div><dt>Recebido no mês</dt><dd class="ok">${brl(e.recebido_no_mes)}</dd><small>${e.recebimentos_no_mes} recebimento(s)</small></div>
      <div><dt>Cheques em carteira</dt><dd>${brl(e.cheques.valor)}</dd><small>${e.cheques.quantidade} cheque(s)</small></div></dl>
      ${e.empresas.length ? `<p class="sutil">Mais a receber: ${e.empresas.filter((x) => x.em_aberto).slice(0, 3).map((x) => `${esc(x.nome)} (${brl(x.em_aberto)})`).join(" · ") || "nada em aberto"}</p>` : ""}`}
  </section>`;
}

function htmlJuros(c, titulo) {
  return `<section class="card fechamento-secao">
    <h3>${icone("alerta", 17)} Juros e multas pagos em ${esc(titulo)} <small class="sutil">${brl(c.juros_multa)}</small></h3>
    ${c.juros.length ? `<div class="tabela-wrap"><table class="tabela"><thead><tr>
        <th>Beneficiário / recebedor</th><th>Vencimento</th><th>Pago em</th><th class="num">Valor</th><th class="num">Juros/multa</th>
        <th class="num">Valor pago</th><th>Centro de custo</th><th>Pago por</th></tr></thead>
      <tbody>${c.juros.map((j) => `<tr>
        <td data-rotulo="Beneficiário"><strong>${esc(j.nome)}</strong>${j.tipo !== "Boleto" ? ` <span class="chip">${esc(j.tipo)}</span>` : ""}</td>
        <td data-rotulo="Vencimento">${dataBR(j.vencimento)}</td>
        <td data-rotulo="Pago em">${dataBR(j.data_pagamento)}${j.dias_atraso ? `<div class="sutil">${j.dias_atraso} dia(s) de atraso</div>` : ""}</td>
        <td data-rotulo="Valor" class="num">${brl(j.valor)}</td>
        <td data-rotulo="Juros/multa" class="num juros-linha"><strong>${brl(j.juros_multa)}</strong></td>
        <td data-rotulo="Valor pago" class="num">${brl(j.valor_pago)}</td>
        <td data-rotulo="Centro de custo">${esc(j.centro_custo)}</td><td data-rotulo="Pago por">${esc(j.pago_por || "—")}</td>
      </tr>`).join("")}</tbody></table></div>`
      : `<p class="sutil" style="padding:6px 0">Nenhum juro ou multa pago neste mês. 👏</p>`}
  </section>`;
}

function htmlHistorico(historico, atual) {
  const maior = Math.max(1, ...historico.map((h) => h.pago));
  const totalJuros = historico.reduce((s, h) => s + h.juros_multa, 0);
  return `<section class="card fechamento-secao">
    <h3>${icone("grafico", 17)} Últimos 12 meses <small class="sutil">juros e multas no período: ${brl(totalJuros)}</small></h3>
    <div class="tabela-wrap"><table class="tabela rel-historico"><thead><tr>
      <th>Mês</th><th class="num">Boletos</th><th class="num">Pix</th><th class="num">Dinheiro</th><th class="num">Total pago</th>
      <th class="num">Juros/multa</th><th class="num">Com atraso</th><th class="rel-barra-col"></th></tr></thead>
    <tbody>${historico.slice().reverse().map((h) => `<tr class="${h.mes === atual ? "rel-atual" : ""}">
      <td data-rotulo="Mês"><a href="#/relatorios?mes=${h.mes}" data-mes="${h.mes}">${esc(h.titulo)}</a></td>
      <td data-rotulo="Boletos" class="num">${brl(h.boletos)}</td><td data-rotulo="Pix" class="num">${brl(h.pix)}</td>
      <td data-rotulo="Dinheiro" class="num">${brl(h.dinheiro)}</td><td data-rotulo="Total pago" class="num"><strong>${brl(h.pago)}</strong></td>
      <td data-rotulo="Juros/multa" class="num ${h.juros_multa ? "juros-linha" : ""}">${h.juros_multa ? brl(h.juros_multa) : "—"}</td>
      <td data-rotulo="Com atraso" class="num">${h.pagos_com_atraso || "—"}</td>
      <td class="rel-barra-col" aria-hidden="true"><span class="rel-barra" style="width:${Math.round((h.pago / maior) * 100)}%"></span></td>
    </tr>`).join("")}</tbody></table></div>
  </section>`;
}

function htmlCentros(centros, titulo) {
  return `<section class="card fechamento-secao">
    <h3>${icone("etiqueta", 17)} Onde mais se pagou em ${esc(titulo)}</h3>
    <div class="tabela-wrap"><table class="tabela"><thead><tr><th>Centro de custo</th><th class="num">Pago</th><th class="num">Lançamentos</th></tr></thead>
      <tbody>${centros.map((c) => `<tr><td data-rotulo="Centro">${esc(c.centro_custo)}</td>
        <td data-rotulo="Pago" class="num"><strong>${brl(c.pago)}</strong></td><td data-rotulo="Lançamentos" class="num">${c.quantidade}</td></tr>`).join("")}</tbody></table></div>
  </section>`;
}

// ------------------------------------------------------------------ todos os relatórios do sistema

function htmlCatalogo() {
  const dia1 = `${mes}-01`;
  const fech = (formato) => url("/api/relatorios/fechamento/arquivo", { mes, base: "vencimento", formato });
  const cartoes = [
    pode("gastos") && {
      ic: "relatorio", titulo: "Fechamento do mês (para o contador)",
      texto: "Tudo que vence no mês ou só o que foi pago: pagos, em aberto, juros e multas, por centro de custo e os comprovantes.",
      abrir: "#/gastos?aba=fechamento",
      arquivos: [["planilha", "Excel", fech("xlsx")], ["arquivo", "PDF", fech("pdf")], ["download", "Pacote .zip", fech("zip")]],
    },
    pode("gastos") && {
      ic: "grafico", titulo: "Análise de gastos", abrir: "#/gastos",
      texto: "Quanto foi gasto em cada centro de custo, mês a mês, em boletos, Pix e dinheiro, com os juros do período.",
    },
    {
      ic: "relogio", titulo: "Previsão de saídas", abrir: "#/painel",
      texto: "O que vai sair nas próximas semanas e o que já está em atraso (no Painel).",
    },
    pode("caixa") && {
      ic: "caixa", titulo: "Relatório do caixa", abrir: "#/caixa?aba=relatorios",
      texto: "Entradas e saídas por dia, semana, mês ou ano: onde mais se gastou, por centro de custo, quem gastou e entradas por pedido.",
      arquivos: [["planilha", "Excel do mês", url("/api/caixa/relatorio/arquivo", { periodo: "mes", data: dia1 })]],
    },
    pode("diesel") && {
      ic: "diesel", titulo: "Relatórios do diesel", abrir: "#/diesel?aba=relatorios",
      texto: "Semanal, quinzenal, mensal e anual: consumo e média de cada máquina, por combustível, compras e custo.",
      arquivos: [["planilha", "Excel do mês", url("/api/diesel/relatorio/arquivo", { periodo: "mes", data: dia1 })]],
    },
    pode("empresas") && {
      ic: "carteira", titulo: "Fechamento das empresas", abrir: "#/empresas?aba=fechamentos",
      texto: "O fechamento de cada empresa (todo dia 20), no formato do seu modelo, em Excel e PDF, com quanto falta receber.",
    },
    {
      ic: "clipe", titulo: "Comprovantes", abrir: "#/comprovantes",
      texto: "Busque qualquer comprovante (boletos, Pix, cheques, caixa, diesel) e veja os pagamentos sem comprovante.",
    },
    pode("notificacoes") && {
      ic: "telegram", titulo: "Resumo da semana (segunda e sexta)", abrir: "#/notificacoes",
      texto: "Segunda: o que vence na semana. Sexta: o que foi pago em boletos, Pix, caixa e os juros. Vai pelo Telegram.",
      previas: true,
    },
  ].filter(Boolean);
  return `<h2 class="rel-titulo">${icone("relatorio", 18)} Todos os relatórios</h2>
    <div class="rel-grade">${cartoes.map((c) => `<article class="card rel-cartao">
      <h3>${icone(c.ic, 17)} ${esc(c.titulo)}</h3>
      <p class="sutil">${esc(c.texto)}</p>
      <div class="rel-acoes">
        <a class="btn btn-sm btn-primario" href="${c.abrir}">${icone("externo", 14)} Abrir</a>
        ${(c.arquivos || []).map(([ic, rotulo, href]) => `<a class="btn btn-sm" href="${href}" data-download>${icone(ic, 14)} ${rotulo}</a>`).join("")}
        ${c.previas ? `<button class="btn btn-sm" data-previa="segunda">${icone("olho", 14)} Segunda</button>
          <button class="btn btn-sm" data-previa="sexta">${icone("olho", 14)} Sexta</button>` : ""}
      </div>
    </article>`).join("")}</div>`;
}

// ------------------------------------------------------------------ eventos

async function aoClicar(e) {
  const nav = e.target.closest("[data-r]");
  if (nav) {
    mes = nav.dataset.r === "hoje" ? isoDeData(new Date()).slice(0, 7) : mesVizinho(nav.dataset.r === "proximo" ? 1 : -1);
    await carregar();
    return;
  }
  const link = e.target.closest("[data-mes]");
  if (link) {
    e.preventDefault();
    mes = link.dataset.mes;
    await carregar();
    raiz?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const previa = e.target.closest("[data-previa]");
  if (previa) {
    const tipo = previa.dataset.previa;
    try {
      const r = await api.get(`/api/notificacoes/resumo/${tipo}`);
      abrirModal({
        titulo: `Resumo de ${tipo === "segunda" ? "segunda-feira" : "sexta-feira"} · como fica agora`,
        corpo: `<div class="resumo-previa">${r.html}</div>`,
        rodape: `<button class="btn" data-fechar>Fechar</button>`,
      });
    } catch (erro) {
      toast(mensagemErro(erro), "erro");
    }
  }
}

async function aoAlterar(e) {
  if (e.target.id === "r-mes" && /^\d{4}-\d{2}$/.test(e.target.value)) {
    mes = e.target.value;
    await carregar();
  }
}

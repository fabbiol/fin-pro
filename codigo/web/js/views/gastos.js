// Tela: Gastos — quanto foi gasto em cada centro de custo (boletos + Pix) e cadastro dos centros de custo.
import { api } from "../api.js";
import { SEM_CENTRO, carregarCentros } from "../centros.js";
import { montarGraficoSeries } from "../grafico.js";
import { icone } from "../icons.js";
import { abrirModal, brl, dataBR, dataHoraBR, esc, isoDeData, mensagemErro, toast } from "../ui.js";

const CORES = ["#0d9488", "#2a62c7", "#d97706", "#8b5cf6", "#db2777", "#16a34a"];
const COR_OUTROS = "#94a3b8";
const ROTULO_SEM_CENTRO = "Sem centro de custo";
const PERIODOS = [
  ["mes", "Este mês"], ["mes_passado", "Mês passado"], ["3m", "Últimos 3 meses"], ["12m", "Últimos 12 meses"],
  ["ano", "Este ano"], ["ano_passado", "Ano passado"], ["tudo", "Todo o período"], ["personalizado", "Personalizado"],
];
const TIPOS = [["todos", "Boletos, Pix e dinheiro"], ["boleto", "Só boletos"], ["pix", "Só Pix"], ["dinheiro", "Só dinheiro (caixa)"]];
const SITUACOES = [["todos", "Pagos e pendentes"], ["pagos", "Pagos"], ["pendentes", "Pendentes"]];
const filtros = { periodo: "ano", de: "", ate: "", campo_data: "vencimento", situacao: "todos", tipo: "todos" };

let raiz = null;
let aba = "analise";
let requisicao = 0;
let centrosAtuais = [];
const fechamento = { mes: isoDeData(new Date()).slice(0, 7), base: "vencimento" };

export async function montar(el, params) {
  raiz = el;
  if (params.get("aba")) aba = ["centros", "fechamento"].includes(params.get("aba")) ? params.get("aba") : "analise";
  el.innerHTML = `
    <div class="alternar-modo sub-abas" role="tablist" aria-label="Seções de gastos">
      <button role="tab" data-aba="analise">${icone("grafico", 15)} Análise de gastos</button>
      <button role="tab" data-aba="fechamento">${icone("relatorio", 15)} Fechamento do mês</button>
      <button role="tab" data-aba="centros">${icone("etiqueta", 15)} Centros de custo</button>
    </div>
    <div id="gastos-conteudo"></div>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  await mostrarAba();
}

export function desmontar() {
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz = null;
}

async function mostrarAba() {
  if (!raiz) return;
  raiz.querySelectorAll("[data-aba]").forEach((b) => {
    const ativo = b.dataset.aba === aba;
    b.classList.toggle("ativo", ativo);
    b.setAttribute("aria-selected", String(ativo));
  });
  const conteudo = raiz.querySelector("#gastos-conteudo");
  if (aba === "centros") {
    await carregarAbaCentros(conteudo);
    return;
  }
  if (aba === "fechamento") {
    await carregarFechamento(conteudo);
    return;
  }
  conteudo.innerHTML = `${htmlFiltros()}<div id="g-resultado"><div class="card esqueleto" style="height:340px"></div></div>`;
  sincronizarFiltros();
  await carregarAnalise();
}

// ------------------------------------------------------------------ fechamento do mês (para o contador)

function urlFechamento(formato) {
  const url = new URL("/api/relatorios/fechamento/arquivo", location.origin);
  url.searchParams.set("mes", fechamento.mes);
  url.searchParams.set("base", fechamento.base);
  url.searchParams.set("formato", formato);
  return url.toString();
}

function mesVizinho(deslocamento) {
  const [ano, mes] = fechamento.mes.split("-").map(Number);
  return isoDeData(new Date(ano, mes - 1 + deslocamento, 1)).slice(0, 7);
}

function linhasFechamento(itens, pagos) {
  if (!itens.length) return `<p class="sutil" style="padding:10px 0">${pagos ? "Nenhum pagamento." : "Nada em aberto."}</p>`;
  return `<div class="tabela-wrap"><table class="tabela tabela-fechamento"><thead><tr>
      <th>Vencimento</th><th>Beneficiário / Recebedor</th><th>Centro de custo</th><th class="num">Valor</th>
      ${pagos ? `<th class="num">Juros/multa</th><th class="num">Desconto</th><th class="num">Valor pago</th><th>Pago em</th><th>Pago por</th><th>Comprovante</th>`
        : "<th>Situação</th>"}</tr></thead>
    <tbody>${itens.map((i) => `<tr>
      <td data-rotulo="Vencimento">${dataBR(i.vencimento)}</td>
      <td data-rotulo="Beneficiário"><strong>${esc(i.nome)}</strong>${i.tipo === "Pix" ? ` <span class="chip">Pix</span>` : ""}<div class="sutil">${esc(i.documento || "")}</div></td>
      <td data-rotulo="Centro de custo">${esc(i.centro_custo)}</td>
      <td data-rotulo="Valor" class="num">${brl(i.valor)}</td>
      ${pagos
        ? `<td data-rotulo="Juros/multa" class="num">${i.juros_multa ? brl(i.juros_multa) : "—"}</td>
           <td data-rotulo="Desconto" class="num">${i.desconto ? brl(i.desconto) : "—"}</td>
           <td data-rotulo="Valor pago" class="num"><strong>${brl(i.valor_pago)}</strong></td>
           <td data-rotulo="Pago em">${dataBR(i.data_pagamento)}${i.dias_atraso ? `<div class="sutil">${i.dias_atraso} dia(s) de atraso</div>` : ""}</td><td data-rotulo="Pago por">${esc(i.pago_por || "—")}</td>
           <td data-rotulo="Comprovante">${i.comprovante
             ? `<a href="/api/${i.tipo === "Pix" ? "pix" : "boletos"}/${i.id}/comprovante" target="_blank" rel="noopener" class="chip ok">${icone("clipe", 12)} Ver</a>`
             : `<span class="chip">Não anexado</span>`}</td>`
        : `<td data-rotulo="Situação">${i.atrasado ? `<span class="chip erro">Atrasado</span>` : `<span class="chip info">A vencer</span>`}</td>`}
    </tr>`).join("")}</tbody></table></div>`;
}

async function carregarFechamento(conteudo) {
  conteudo.innerHTML = `<section class="card barra-filtros">
      <div class="filtros-linha">
        <div class="periodo">
          <button class="btn-icone" data-f="anterior" aria-label="Mês anterior">${icone("chevron-esq", 16)}</button>
          <input type="month" id="f-mes" class="input input-sm" value="${fechamento.mes}" aria-label="Mês">
          <button class="btn-icone" data-f="proximo" aria-label="Próximo mês">${icone("chevron-dir", 16)}</button>
          <select id="f-base" class="input input-sm" aria-label="Considerar">
            <option value="vencimento" ${fechamento.base === "vencimento" ? "selected" : ""}>Tudo que vence no mês</option>
            <option value="pagamento" ${fechamento.base === "pagamento" ? "selected" : ""}>Só o que foi pago no mês</option>
          </select>
        </div>
        <span class="espaco"></span>
        <a class="btn" href="${urlFechamento("xlsx")}" data-download>${icone("planilha", 16)} Excel</a>
        <a class="btn" href="${urlFechamento("pdf")}" data-download>${icone("arquivo", 16)} PDF</a>
        <a class="btn btn-primario" href="${urlFechamento("zip")}" data-download title="PDF + Excel + comprovantes de pagamento, num único arquivo">${icone("download", 16)} Pacote para o contador (.zip)</a>
      </div>
    </section>
    <div id="f-resultado" class="fechamento"><div class="card esqueleto" style="height:320px"></div></div>`;
  const alvo = conteudo.querySelector("#f-resultado");
  const minha = ++requisicao;
  try {
    const f = await api.get("/api/relatorios/fechamento", { mes: fechamento.mes, base: fechamento.base });
    if (!raiz || minha !== requisicao) return;
    const t = f.totais;
    const vazio = !t.quantidade && !f.cancelados.length;
    alvo.innerHTML = `
      <section class="resumo-lista">
        <div class="card resumo-item"><span>Total de ${esc(f.titulo)}</span><strong>${brl(t.total)}</strong></div>
        <div class="card resumo-item ok"><span>Pago</span><strong>${brl(t.pago)}</strong></div>
        <div class="card resumo-item ${t.juros_multa ? "erro" : ""}"><span>Juros e multas${t.pagos_com_atraso ? ` (${t.pagos_com_atraso} com atraso)` : ""}</span><strong>${brl(t.juros_multa)}</strong></div>
        ${t.desconto ? `<div class="card resumo-item ok"><span>Descontos</span><strong>${brl(t.desconto)}</strong></div>` : ""}
        <div class="card resumo-item"><span>Em aberto</span><strong>${brl(t.em_aberto)}</strong></div>
        <div class="card resumo-item erro"><span>Em atraso (${t.quantidade_atrasados})</span><strong>${brl(t.atrasado)}</strong></div>
        <div class="card resumo-item"><span>Comprovantes</span><strong>${t.com_comprovante} de ${t.com_comprovante + t.sem_comprovante}</strong></div>
      </section>
      ${vazio ? `<div class="card vazio"><div class="vazio-icone">${icone("relatorio", 26)}</div><h3>Nenhum lançamento em ${esc(f.titulo)}</h3>
        <p>Escolha outro mês ou mude para "${fechamento.base === "vencimento" ? "Só o que foi pago no mês" : "Tudo que vence no mês"}".</p></div>` : `
      <section class="card fechamento-secao">
        <h3>${icone("etiqueta", 17)} Por centro de custo</h3>
        <div class="tabela-wrap"><table class="tabela"><thead><tr><th>Centro de custo</th><th class="num">Pago</th><th class="num">Em aberto</th><th class="num">Total</th><th class="num">Lançamentos</th></tr></thead>
          <tbody>${f.por_centro.map((c) => `<tr><td data-rotulo="Centro">${esc(c.centro_custo)}</td><td class="num" data-rotulo="Pago">${brl(c.pago)}</td>
            <td class="num" data-rotulo="Em aberto">${brl(c.em_aberto)}</td><td class="num" data-rotulo="Total"><strong>${brl(c.total)}</strong></td>
            <td class="num" data-rotulo="Lançamentos">${c.quantidade}</td></tr>`).join("")}</tbody></table></div>
      </section>
      <section class="card fechamento-secao"><h3>${icone("check", 17)} Pagos (${f.pagos.length})</h3>${linhasFechamento(f.pagos, true)}</section>
      ${f.base === "vencimento" ? `<section class="card fechamento-secao"><h3>${icone("relogio", 17)} Em aberto (${f.em_aberto.length})</h3>${linhasFechamento(f.em_aberto, false)}</section>` : ""}
      ${f.cancelados.length ? `<p class="sutil">${f.cancelados.length} lançamento(s) cancelado(s) no mês não entram nos totais.</p>` : ""}
      <p class="sutil">Gerado em ${dataHoraBR(f.gerado_em)}. O pacote para o contador traz o PDF, a planilha e os comprovantes anexados${t.sem_comprovante ? `; ${t.sem_comprovante} pagamento(s) sem comprovante aparecem listados num arquivo à parte` : ""}.</p>`}`;
  } catch (erro) {
    if (raiz) alvo.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível montar o fechamento</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

// ------------------------------------------------------------------ análise

function intervalo(periodo) {
  const hoje = new Date();
  const ano = hoje.getFullYear();
  const mes = hoje.getMonth();
  const dia = (a, m, d) => isoDeData(new Date(a, m, d));
  switch (periodo) {
    case "mes": return [dia(ano, mes, 1), dia(ano, mes + 1, 0)];
    case "mes_passado": return [dia(ano, mes - 1, 1), dia(ano, mes, 0)];
    case "3m": return [dia(ano, mes - 2, 1), dia(ano, mes + 1, 0)];
    case "12m": return [dia(ano, mes - 11, 1), dia(ano, mes + 1, 0)];
    case "ano": return [`${ano}-01-01`, `${ano}-12-31`];
    case "ano_passado": return [`${ano - 1}-01-01`, `${ano - 1}-12-31`];
    case "tudo": return ["", ""];
    default: return [filtros.de, filtros.ate];
  }
}

function htmlFiltros() {
  return `<section class="card barra-filtros">
    <div class="filtros-linha">
      <div class="periodo periodo-gastos">${icone("calendario", 16)}
        <select id="g-periodo" class="input input-sm" aria-label="Período">${PERIODOS.map(([v, r]) => `<option value="${v}">${r}</option>`).join("")}</select>
        <input type="date" id="g-de" class="input input-sm" aria-label="De"><span>até</span>
        <input type="date" id="g-ate" class="input input-sm" aria-label="Até">
        <select id="g-campo" class="input input-sm" aria-label="Considerar a data de">
          <option value="vencimento">pelo vencimento</option>
          <option value="data_pagamento">pela data de pagamento</option>
          <option value="data_lancamento">pela data de lançamento</option>
        </select>
      </div>
      <span class="espaco"></span>
      <button class="btn" data-g="exportar">${icone("download", 16)} Exportar Excel</button>
    </div>
    <div class="filtros-linha">
      <div class="chips-situacao">${TIPOS.map(([v, r]) => `<button class="chip-filtro" data-tipo="${v}">${r}</button>`).join("")}</div>
      <div class="chips-situacao">${SITUACOES.map(([v, r]) => `<button class="chip-filtro" data-situacao="${v}">${r}</button>`).join("")}</div>
    </div>
  </section>`;
}

function sincronizarFiltros() {
  if (filtros.periodo !== "personalizado") [filtros.de, filtros.ate] = intervalo(filtros.periodo);
  raiz.querySelector("#g-periodo").value = filtros.periodo;
  raiz.querySelector("#g-de").value = filtros.de;
  raiz.querySelector("#g-ate").value = filtros.ate;
  raiz.querySelector("#g-campo").value = filtros.campo_data;
  raiz.querySelectorAll("[data-tipo]").forEach((b) => b.classList.toggle("ativo", b.dataset.tipo === filtros.tipo));
  raiz.querySelectorAll("[data-situacao]").forEach((b) => b.classList.toggle("ativo", b.dataset.situacao === filtros.situacao));
}

const parametros = () => ({ de: filtros.de, ate: filtros.ate, campo_data: filtros.campo_data, situacao: filtros.situacao, tipo: filtros.tipo });

async function carregarAnalise() {
  const alvo = raiz?.querySelector("#g-resultado");
  if (!alvo) return;
  alvo.classList.add("carregando");
  const minha = ++requisicao;
  try {
    const dados = await api.get("/api/gastos", parametros());
    if (!raiz || minha !== requisicao) return;
    renderizarAnalise(alvo, dados);
  } catch (erro) {
    if (raiz) {
      alvo.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
        <h3>Não foi possível carregar a análise</h3><p>${esc(mensagemErro(erro))}</p></div>`;
    }
  } finally {
    alvo.classList.remove("carregando");
  }
}

function kpi(titulo, valor, detalhe, nomeIcone, classe, link = "") {
  const tag = link ? "a" : "div";
  return `<${tag} class="card kpi ${classe}" ${link ? `href="${link}"` : ""}>
    <div class="kpi-topo"><span>${titulo}</span><span class="kpi-icone">${icone(nomeIcone, 18)}</span></div>
    <div class="kpi-valor">${valor}</div><div class="kpi-detalhe">${detalhe}</div></${tag}>`;
}

const porcentagem = (v) => `${String(v).replace(".", ",")}%`;
const parteDe = (valor, total) => (total ? `${porcentagem(Math.round((valor / total) * 1000) / 10)} do total` : "—");
const linkBoletos = (centro) => `#/boletos?centro=${encodeURIComponent(centro === ROTULO_SEM_CENTRO ? SEM_CENTRO : centro)}`;

function renderizarAnalise(alvo, d) {
  if (!d.quantidade) {
    alvo.innerHTML = `<div class="card vazio" style="padding:60px 24px"><div class="vazio-icone">${icone("grafico", 28)}</div>
      <h3>Nenhum gasto neste período</h3>
      <p>Mude o período ou os filtros. Para a análise ficar completa, informe o centro de custo ao lançar boletos e Pix.</p></div>`;
    return;
  }
  const cores = new Map(d.series.map((nome, i) => [nome, nome === "Outros centros" || nome === ROTULO_SEM_CENTRO ? COR_OUTROS : CORES[i % CORES.length]]));
  const cor = (nome) => cores.get(nome) || COR_OUTROS;
  const maior = Math.max(...d.centros.map((c) => c.total), 1);
  const soma = (campo) => d.centros.reduce((total, c) => total + c[campo], 0);
  const maiorNome = Math.max(...d.maiores.map((m) => m.total), 1);

  alvo.innerHTML = `
    <section class="kpis kpis-6">
      ${kpi("Total gasto", brl(d.total), `${d.quantidade} lançamento${d.quantidade === 1 ? "" : "s"}`, "carteira", "marca")}
      ${kpi("Boletos", brl(d.total_boletos), parteDe(d.total_boletos, d.total), "boleto", "info")}
      ${kpi("Pix", brl(d.total_pix), parteDe(d.total_pix, d.total), "pix", "ia")}
      ${kpi("Dinheiro (caixa)", brl(d.total_dinheiro || 0), parteDe(d.total_dinheiro || 0, d.total), "caixa", "aviso", "#/caixa")}
      ${kpi("Juros e multas", brl(d.juros_multa || 0), d.pagos_com_juros ? `${d.pagos_com_juros} pago(s) com atraso` : "Nenhum pago com juros",
        "alerta", d.juros_multa ? "erro" : "ok")}
      ${kpi("Sem centro de custo", brl(d.sem_centro), d.sem_centro ? "Toque para classificar os boletos" : "Tudo classificado",
        "etiqueta", d.sem_centro ? "aviso" : "ok", d.sem_centro ? `#/boletos?centro=${SEM_CENTRO}` : "")}
    </section>
    ${d.sem_centro ? `<div class="alerta aviso alerta-gastos">${icone("etiqueta", 16)}<span><strong>${brl(d.sem_centro)}</strong> ainda não têm centro de custo.
      Em <a href="#/boletos?centro=${SEM_CENTRO}">Boletos lançados</a>, selecione os boletos e use <strong>Centro de custo</strong>;
      nos Pix, abra <strong>Editar</strong>.</span></div>` : ""}

    <section class="gastos-grade">
      <div class="card">
        <div class="card-cabecalho"><h3>${icone("etiqueta", 17)} Por centro de custo</h3></div>
        <div class="card-corpo"><ul class="barras-centro">${d.centros.map((c) => `<li>
          <a class="linha-centro" href="${linkBoletos(c.centro)}" title="Ver os boletos deste centro de custo">
            <span class="cor" style="background:${cor(c.centro)}"></span>
            <div class="info">
              <div class="topo"><strong title="${esc(c.centro)}">${esc(c.centro)}</strong><span class="valor">${brl(c.total)}</span></div>
              <div class="barra-ranking"><div style="width:${Math.max(2, (c.total / maior) * 100)}%;background:${cor(c.centro)}"></div></div>
              <div class="sutil">${porcentagem(c.percentual)} · ${c.quantidade} lançamento${c.quantidade === 1 ? "" : "s"}${c.pix ? ` · Pix ${brl(c.pix)}` : ""}</div>
            </div></a></li>`).join("")}</ul></div>
      </div>

      <div class="card">
        <div class="card-cabecalho"><h3>${icone("grafico", 17)} Por mês</h3>
          <div class="legenda">${d.series.map((s) => `<span><i style="background:${cor(s)}"></i>${esc(s)}</span>`).join("")}</div></div>
        <div class="card-corpo" id="g-grafico"></div>
      </div>

      <div class="card tabela-card largo">
        <div class="card-cabecalho"><h3>${icone("planilha", 17)} Detalhamento por centro de custo</h3></div>
        <div class="tabela-wrap"><table class="tabela tabela-gastos">
          <thead><tr><th>Centro de custo</th><th class="num">Boletos</th><th class="num">Pix</th><th class="num">Dinheiro</th><th class="num">Total</th>
            <th class="num">% do total</th><th class="num">Pagos</th><th class="num">Pendentes</th></tr></thead>
          <tbody>${d.centros.map((c) => `<tr>
            <td data-rotulo="Centro de custo"><a href="${linkBoletos(c.centro)}"><strong>${esc(c.centro)}</strong></a></td>
            <td class="num" data-rotulo="Boletos">${brl(c.boletos)}</td>
            <td class="num" data-rotulo="Pix">${brl(c.pix)}</td>
            <td class="num" data-rotulo="Dinheiro">${brl(c.dinheiro || 0)}</td>
            <td class="num" data-rotulo="Total"><strong>${brl(c.total)}</strong></td>
            <td class="num" data-rotulo="% do total">${porcentagem(c.percentual)}</td>
            <td class="num" data-rotulo="Pagos">${brl(c.pagos)}</td>
            <td class="num" data-rotulo="Pendentes">${brl(c.pendentes)}</td></tr>`).join("")}</tbody>
          <tfoot><tr><td>Total</td><td class="num">${brl(d.total_boletos)}</td><td class="num">${brl(d.total_pix)}</td><td class="num">${brl(d.total_dinheiro || 0)}</td>
            <td class="num">${brl(d.total)}</td><td class="num">100%</td><td class="num">${brl(soma("pagos"))}</td><td class="num">${brl(soma("pendentes"))}</td></tr></tfoot>
        </table></div>
      </div>

      <div class="card largo">
        <div class="card-cabecalho"><h3>${icone("banco", 17)} Maiores beneficiários e recebedores</h3></div>
        <div class="card-corpo"><ul class="lista-mini lista-colunas">${d.maiores.map((m) => `<li><div class="info">
            <div style="display:flex;justify-content:space-between;gap:10px">
              <span class="titulo" title="${esc(m.nome)}">${esc(m.nome)}</span><span class="valor">${brl(m.total)}</span></div>
            <div class="barra-ranking"><div style="width:${Math.max(3, (m.total / maiorNome) * 100)}%"></div></div>
            <div class="sutil">${m.quantidade} lançamento${m.quantidade === 1 ? "" : "s"}</div></div></li>`).join("")}</ul></div>
      </div>
    </section>`;

  montarGraficoSeries(alvo.querySelector("#g-grafico"), {
    linhas: d.serie_mensal.map((l) => ({ rotulo: l.rotulo, valores: l.centros })),
    series: d.series.map((s) => ({ chave: s, rotulo: s, cor: cor(s) })),
    vazio: "Os lançamentos do período não têm a data escolhida (ex.: ainda não foram pagos).",
  });
}

// ------------------------------------------------------------------ centros de custo

async function carregarAbaCentros(conteudo) {
  conteudo.innerHTML = `<div class="card esqueleto" style="height:280px"></div>`;
  let lista;
  try {
    lista = await carregarCentros(true);
  } catch (erro) {
    conteudo.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar os centros de custo</h3><p>${esc(mensagemErro(erro))}</p></div>`;
    return;
  }
  if (!raiz || aba !== "centros") return;
  centrosAtuais = lista;
  conteudo.innerHTML = `<section class="card tabela-card">
    <div class="card-cabecalho"><h3>${icone("etiqueta", 17)} Centros de custo</h3>
      <button class="btn btn-primario" data-centro="novo">${icone("mais", 16)} Novo centro de custo</button></div>
    <p class="sutil centros-ajuda">Centros de custo dizem <strong>onde cada boleto ou Pix foi gasto</strong> — uma obra, um setor, um veículo.
      Ficam na aba "Centros de Custo" da planilha. Desativar esconde o centro na hora de lançar, mas mantém o histórico na análise.</p>
    <div class="tabela-wrap"><table class="tabela">
      <thead><tr><th>Nome</th><th>Descrição</th><th class="num">Boletos</th><th class="num">Pix</th><th class="num">Caixa</th><th class="num">Total lançado</th><th>Ativo</th><th class="col-acoes">Ações</th></tr></thead>
      <tbody>${lista.map((c) => `<tr data-nome="${esc(c.nome)}" class="${c.ativo ? "" : "linha-inativa"}">
        <td data-rotulo="Nome"><strong>${esc(c.nome)}</strong></td>
        <td data-rotulo="Descrição"><span class="sutil">${esc(c.descricao || "—")}</span></td>
        <td class="num" data-rotulo="Boletos">${c.boletos}</td>
        <td class="num" data-rotulo="Pix">${c.pix}</td>
        <td class="num" data-rotulo="Caixa">${c.dinheiro || 0}</td>
        <td class="num" data-rotulo="Total lançado">${brl(c.total)}</td>
        <td data-rotulo="Ativo"><label class="interruptor" title="${c.ativo ? "Desativar" : "Ativar"}">
          <input type="checkbox" data-centro="ativo" ${c.ativo ? "checked" : ""} aria-label="Centro de custo ativo"><span></span></label></td>
        <td class="col-acoes">
          ${c.boletos ? `<a class="btn-icone" href="#/boletos?centro=${encodeURIComponent(c.nome)}" title="Ver boletos">${icone("lista", 16)}</a>` : ""}
          ${c.pix ? `<a class="btn-icone" href="#/pix?centro=${encodeURIComponent(c.nome)}" title="Ver Pix">${icone("pix", 16)}</a>` : ""}
          <button class="btn-icone" data-centro="editar" title="Editar">${icone("editar", 16)}</button>
        </td></tr>`).join("")}</tbody>
    </table></div>
  </section>`;
}

function editarCentro(centro = null) {
  const usos = centro ? centro.boletos + centro.pix + (centro.dinheiro || 0) : 0;
  const { el, fechar } = abrirModal({
    titulo: centro ? "Editar centro de custo" : "Novo centro de custo",
    corpo: `<form class="grade-campos" id="form-centro" autocomplete="off">
      <div class="campo col-2"><label for="c-nome">Nome</label>
        <input id="c-nome" class="input" name="nome" maxlength="60" required autofocus value="${esc(centro?.nome || "")}" placeholder="Ex.: Obra Jardim Europa"></div>
      <div class="campo col-2"><label for="c-desc">Descrição (opcional)</label>
        <input id="c-desc" class="input" name="descricao" maxlength="200" value="${esc(centro?.descricao || "")}"></div>
      ${usos ? `<p class="sutil col-2">Se mudar o nome, ${usos === 1 ? "o lançamento deste centro também é atualizado" : `os ${usos} lançamentos deste centro também são atualizados`} na planilha.</p>` : ""}
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });
  const form = el.querySelector("#form-centro");
  const salvar = async (e) => {
    e?.preventDefault();
    const nome = form.elements.nome.value.replace(/\s+/g, " ").trim();
    const descricao = form.elements.descricao.value.trim();
    if (!nome) {
      form.elements.nome.focus();
      return;
    }
    const botao = el.querySelector("[data-salvar]");
    botao.disabled = true;
    try {
      if (centro) await api.put("/api/centros", { nome_anterior: centro.nome, nome, descricao, ativo: centro.ativo });
      else await api.post("/api/centros", { nome, descricao });
      fechar(true);
      toast("Centro de custo salvo na planilha", "ok");
      if (raiz) carregarAbaCentros(raiz.querySelector("#gastos-conteudo"));
    } catch (erro) {
      botao.disabled = false;
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  form.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

// ------------------------------------------------------------------ eventos

function aoClicar(e) {
  const botaoAba = e.target.closest("[data-aba]");
  if (botaoAba) {
    if (botaoAba.dataset.aba !== aba) {
      aba = botaoAba.dataset.aba;
      mostrarAba();
    }
    return;
  }
  const navegarMes = e.target.closest("[data-f]");
  if (navegarMes) {
    fechamento.mes = mesVizinho(navegarMes.dataset.f === "proximo" ? 1 : -1);
    carregarFechamento(raiz.querySelector("#gastos-conteudo"));
    return;
  }
  const tipo = e.target.closest("[data-tipo]");
  if (tipo) {
    filtros.tipo = tipo.dataset.tipo;
    sincronizarFiltros();
    carregarAnalise();
    return;
  }
  const situacao = e.target.closest("[data-situacao]");
  if (situacao) {
    filtros.situacao = situacao.dataset.situacao;
    sincronizarFiltros();
    carregarAnalise();
    return;
  }
  if (e.target.closest("[data-g='exportar']")) {
    const url = new URL("/api/gastos/exportar", location.origin);
    Object.entries(parametros()).forEach(([chave, valor]) => { if (valor) url.searchParams.set(chave, valor); });
    window.location.href = url.toString();
    return;
  }
  const acao = e.target.closest("button[data-centro]")?.dataset.centro;
  if (acao === "novo") editarCentro();
  else if (acao === "editar") {
    const nome = e.target.closest("[data-nome]").dataset.nome;
    editarCentro(centrosAtuais.find((c) => c.nome === nome));
  }
}

async function aoAlterar(e) {
  const alvo = e.target;
  if (alvo.id === "f-mes" || alvo.id === "f-base") {
    if (alvo.id === "f-mes" && !alvo.value) return;
    fechamento[alvo.id === "f-mes" ? "mes" : "base"] = alvo.value;
    carregarFechamento(raiz.querySelector("#gastos-conteudo"));
    return;
  }
  if (alvo.id === "g-periodo") {
    filtros.periodo = alvo.value;
    sincronizarFiltros();
    carregarAnalise();
  } else if (alvo.id === "g-de" || alvo.id === "g-ate") {
    filtros.periodo = "personalizado";
    filtros[alvo.id === "g-de" ? "de" : "ate"] = alvo.value;
    sincronizarFiltros();
    carregarAnalise();
  } else if (alvo.id === "g-campo") {
    filtros.campo_data = alvo.value;
    carregarAnalise();
  } else if (alvo.matches("[data-centro='ativo']")) {
    const nome = alvo.closest("[data-nome]").dataset.nome;
    const centro = centrosAtuais.find((c) => c.nome === nome);
    alvo.disabled = true;
    try {
      await api.put("/api/centros", { nome_anterior: nome, nome, descricao: centro?.descricao || "", ativo: alvo.checked });
      toast(alvo.checked ? `"${nome}" ativado` : `"${nome}" desativado: não aparece mais na hora de lançar`, "ok");
      if (raiz) carregarAbaCentros(raiz.querySelector("#gastos-conteudo"));
    } catch (erro) {
      alvo.checked = !alvo.checked;
      alvo.disabled = false;
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  }
}

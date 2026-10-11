// Caixa · relatórios do período: onde mais se gastou, centros de custo, pessoas, pedidos e a evolução.
import { montarGraficoSeries } from "../../grafico.js";
import { icone } from "../../icons.js";
import { brl, dataBR, esc } from "../../ui.js";
import { htmlKpis } from "./movimento.js";

function barras(titulo, iconeNome, itens, vazio) {
  const maior = Math.max(...itens.map((i) => i.total), 0);
  return `<article class="card caixa-ranking">
    <h3>${icone(iconeNome, 17)} ${esc(titulo)}</h3>
    ${itens.length ? `<ul class="caixa-barras">${itens.map((i) => `<li>
        <div class="caixa-barra-topo"><strong title="${esc(i.nome)}">${esc(i.nome)}</strong>
          <span>${brl(i.total)} <small class="sutil">${i.percentual}% · ${i.quantidade}×</small></span></div>
        <div class="caixa-barra"><i style="width:${maior ? Math.max(3, (i.total / maior) * 100) : 0}%"></i></div>
      </li>`).join("")}</ul>` : `<p class="sutil">${esc(vazio)}</p>`}
  </article>`;
}

export function htmlRelatorios(d) {
  const variacao = d.saidas_periodo_anterior
    ? Math.round(((d.saidas.total - d.saidas_periodo_anterior) / d.saidas_periodo_anterior) * 100) : null;
  return `${htmlKpis(d)}
    <section class="caixa-indicadores">
      <article class="card"><span class="sutil">Gasto médio por saída</span><strong>${brl(d.saidas.media)}</strong></article>
      <article class="card"><span class="sutil">Maior saída</span><strong>${d.saidas.maior ? brl(d.saidas.maior.valor) : "—"}</strong>
        <small class="sutil">${d.saidas.maior ? `${esc(d.saidas.maior.descricao || "")} · ${dataBR(d.saidas.maior.data)}` : ""}</small></article>
      <article class="card"><span class="sutil">Entrada média</span><strong>${brl(d.entradas.media)}</strong></article>
      <article class="card"><span class="sutil">Saídas x período anterior</span>
        <strong class="${variacao > 0 ? "erro" : "ok"}">${variacao === null ? "—" : `${variacao > 0 ? "+" : ""}${variacao}%`}</strong>
        <small class="sutil">antes: ${brl(d.saidas_periodo_anterior)}</small></article>
    </section>

    <section class="caixa-graficos">
      <article class="card"><h3>${icone("grafico", 17)} Saídas em ${esc(d.periodo.rotulo)}</h3><div data-grafico="saidas"></div></article>
      <article class="card"><h3>${icone("grafico", 17)} Entradas em ${esc(d.periodo.rotulo)}</h3><div data-grafico="entradas"></div></article>
    </section>

    <section class="caixa-rankings">
      ${barras("Onde mais se gastou", "carteira", d.por_local, "Nenhuma saída no período.")}
      ${barras("Por centro de custo", "etiqueta", d.por_centro, "Nenhuma saída no período.")}
      ${barras("Quem mais gastou", "pessoa", d.por_pessoa, "Nenhuma saída no período.")}
      ${barras("Entradas por pedido", "lista", d.entradas_por_pedido, "Nenhuma entrada no período.")}
    </section>`;
}

export function desenharGraficos(raiz, d) {
  const linhas = d.serie.map((s) => ({ rotulo: s.rotulo, valores: { saidas: s.saidas, entradas: s.entradas } }));
  const saidas = raiz.querySelector('[data-grafico="saidas"]');
  const entradas = raiz.querySelector('[data-grafico="entradas"]');
  if (saidas) montarGraficoSeries(saidas, { linhas, series: [{ chave: "saidas", rotulo: "Saídas", cor: "var(--erro)" }],
                                           vazio: "Nenhuma saída no período." });
  if (entradas) montarGraficoSeries(entradas, { linhas, series: [{ chave: "entradas", rotulo: "Entradas", cor: "var(--ok)" }],
                                               vazio: "Nenhuma entrada no período." });
}

// Gráfico de barras empilhadas (SVG) com tooltip.
import { brl, compacto, esc } from "./ui.js";

function tetoArredondado(valor) {
  if (valor <= 0) return 0;
  const potencia = 10 ** Math.floor(Math.log10(valor));
  const fracao = valor / potencia;
  const passo = fracao <= 1 ? 1 : fracao <= 2 ? 2 : fracao <= 2.5 ? 2.5 : fracao <= 5 ? 5 : 10;
  return passo * potencia;
}

const SERIES = [
  { chave: "pago", rotulo: "Pago", classe: "serie-pago" },
  { chave: "vencido", rotulo: "Vencido", classe: "serie-vencido" },
  { chave: "a_vencer", rotulo: "A vencer", classe: "serie-a-vencer" },
];

export function montarGrafico(el, serie) {
  const L = 760;
  const A = 270;
  const m = { topo: 14, dir: 8, base: 30, esq: 58 };
  const totais = serie.map((s) => s.pago + s.vencido + s.a_vencer);
  const maximo = tetoArredondado(Math.max(...totais, 0));

  if (!maximo) {
    el.innerHTML = `<div class="vazio" style="padding:40px 10px"><p>Sem vencimentos nos últimos 6 meses nem nos próximos 6.</p></div>`;
    return;
  }

  const larguraUtil = L - m.esq - m.dir;
  const alturaUtil = A - m.topo - m.base;
  const passo = larguraUtil / serie.length;
  const larguraBarra = Math.min(30, passo * 0.54);
  const y = (v) => m.topo + alturaUtil - (v / maximo) * alturaUtil;

  let svg = "";
  for (let i = 0; i <= 4; i++) {
    const valor = (maximo * i) / 4;
    const yy = y(valor);
    svg += `<line class="grade" x1="${m.esq}" x2="${L - m.dir}" y1="${yy}" y2="${yy}"/>`;
    svg += `<text class="eixo" x="${m.esq - 10}" y="${yy + 4}" text-anchor="end">${i === 0 ? "0" : "R$ " + compacto(valor)}</text>`;
  }

  serie.forEach((s, i) => {
    const x = m.esq + i * passo;
    if (s.atual) svg += `<rect class="marcador-hoje" x="${x + 2}" y="${m.topo}" width="${passo - 4}" height="${alturaUtil}" rx="8"/>`;
    let acumulado = 0;
    const xBarra = x + (passo - larguraBarra) / 2;
    const segmentos = SERIES.filter((ser) => s[ser.chave] > 0);
    segmentos.forEach((ser, j) => {
      const base = y(acumulado);
      acumulado += s[ser.chave];
      const topo = y(acumulado);
      const altura = Math.max(base - topo, 1.5);
      const ultimo = j === segmentos.length - 1;
      const raio = ultimo ? Math.min(5, altura / 2) : 0;
      // Retângulo com cantos superiores arredondados apenas no último segmento
      svg += `<path class="${ser.classe}" d="M${xBarra},${base} V${topo + raio} Q${xBarra},${topo} ${xBarra + raio},${topo} H${xBarra + larguraBarra - raio} Q${xBarra + larguraBarra},${topo} ${xBarra + larguraBarra},${topo + raio} V${base} Z"/>`;
    });
    svg += `<text class="eixo ${s.atual ? "atual" : ""}" x="${x + passo / 2}" y="${A - 8}" text-anchor="middle">${esc(s.rotulo)}</text>`;
    svg += `<rect class="coluna-hover" data-i="${i}" x="${x}" y="${m.topo}" width="${passo}" height="${alturaUtil}"/>`;
  });

  el.innerHTML = `<div class="grafico"><svg viewBox="0 0 ${L} ${A}" role="img" aria-label="Valores de boletos por mês de vencimento">${svg}</svg><div class="tooltip" hidden></div></div>`;

  const caixa = el.querySelector(".grafico");
  const dica = el.querySelector(".tooltip");
  const svgEl = el.querySelector("svg");
  svgEl.addEventListener("mousemove", (e) => {
    const alvo = e.target.closest?.("[data-i]");
    if (!alvo) { dica.hidden = true; return; }
    const s = serie[Number(alvo.dataset.i)];
    const total = s.pago + s.vencido + s.a_vencer;
    dica.innerHTML = `<strong>${esc(s.rotulo)}</strong>
      ${SERIES.map((ser) => `<div><span>${ser.rotulo}</span><span>${brl(s[ser.chave])}</span></div>`).join("")}
      <div style="margin-top:4px;font-weight:700"><span>Total</span><span>${brl(total)}</span></div>`;
    const retangulo = caixa.getBoundingClientRect();
    const colRet = alvo.getBoundingClientRect();
    dica.style.left = `${colRet.left - retangulo.left + colRet.width / 2}px`;
    dica.style.top = `${Math.max(colRet.top - retangulo.top + 40, 90)}px`;
    dica.hidden = false;
  });
  svgEl.addEventListener("mouseleave", () => { dica.hidden = true; });
}

/** Barras empilhadas genéricas: linhas [{ rotulo, valores: { chave: valor } }] e series [{ chave, rotulo, cor }]. */
export function montarGraficoSeries(el, { linhas, series, vazio = "Sem dados no período." }) {
  const L = 760;
  const A = 270;
  const m = { topo: 14, dir: 8, base: 30, esq: 58 };
  const totalDe = (linha) => series.reduce((soma, s) => soma + (linha.valores[s.chave] || 0), 0);
  const maximo = tetoArredondado(Math.max(...linhas.map(totalDe), 0));
  if (!maximo) {
    el.innerHTML = `<div class="vazio" style="padding:40px 10px"><p>${esc(vazio)}</p></div>`;
    return;
  }

  const larguraUtil = L - m.esq - m.dir;
  const alturaUtil = A - m.topo - m.base;
  const passo = larguraUtil / linhas.length;
  const larguraBarra = Math.min(34, passo * 0.6);
  const y = (v) => m.topo + alturaUtil - (v / maximo) * alturaUtil;
  const cadaRotulo = Math.ceil(linhas.length / 14);

  let svg = "";
  for (let i = 0; i <= 4; i++) {
    const valor = (maximo * i) / 4;
    const yy = y(valor);
    svg += `<line class="grade" x1="${m.esq}" x2="${L - m.dir}" y1="${yy}" y2="${yy}"/>`;
    svg += `<text class="eixo" x="${m.esq - 10}" y="${yy + 4}" text-anchor="end">${i === 0 ? "0" : "R$ " + compacto(valor)}</text>`;
  }
  linhas.forEach((linha, i) => {
    const x = m.esq + i * passo;
    const xBarra = x + (passo - larguraBarra) / 2;
    const segmentos = series.filter((s) => (linha.valores[s.chave] || 0) > 0);
    let acumulado = 0;
    segmentos.forEach((s, j) => {
      const base = y(acumulado);
      acumulado += linha.valores[s.chave];
      const topo = y(acumulado);
      const altura = Math.max(base - topo, 1.5);
      const raio = j === segmentos.length - 1 ? Math.min(5, altura / 2) : 0;
      svg += `<path style="fill:${s.cor}" d="M${xBarra},${base} V${topo + raio} Q${xBarra},${topo} ${xBarra + raio},${topo} H${xBarra + larguraBarra - raio} Q${xBarra + larguraBarra},${topo} ${xBarra + larguraBarra},${topo + raio} V${base} Z"/>`;
    });
    if (i % cadaRotulo === 0) svg += `<text class="eixo" x="${x + passo / 2}" y="${A - 8}" text-anchor="middle">${esc(linha.rotulo)}</text>`;
    svg += `<rect class="coluna-hover" data-i="${i}" x="${x}" y="${m.topo}" width="${passo}" height="${alturaUtil}"/>`;
  });

  el.innerHTML = `<div class="grafico"><svg viewBox="0 0 ${L} ${A}" role="img" aria-label="Gastos por mês">${svg}</svg><div class="tooltip" hidden></div></div>`;
  const caixa = el.querySelector(".grafico");
  const dica = el.querySelector(".tooltip");
  const svgEl = el.querySelector("svg");
  svgEl.addEventListener("mousemove", (e) => {
    const alvo = e.target.closest?.("[data-i]");
    if (!alvo) { dica.hidden = true; return; }
    const linha = linhas[Number(alvo.dataset.i)];
    const presentes = series.filter((s) => (linha.valores[s.chave] || 0) > 0);
    dica.innerHTML = `<strong>${esc(linha.rotulo)}</strong>
      ${presentes.map((s) => `<div><span><i class="ponto-serie" style="background:${s.cor}"></i>${esc(s.rotulo)}</span><span>${brl(linha.valores[s.chave])}</span></div>`).join("")}
      <div style="margin-top:4px;font-weight:700"><span>Total</span><span>${brl(totalDe(linha))}</span></div>`;
    const retangulo = caixa.getBoundingClientRect();
    const coluna = alvo.getBoundingClientRect();
    dica.style.left = `${coluna.left - retangulo.left + coluna.width / 2}px`;
    dica.style.top = `${Math.max(coluna.top - retangulo.top + 40, 90)}px`;
    dica.hidden = false;
  });
  svgEl.addEventListener("mouseleave", () => { dica.hidden = true; });
}

export const LEGENDA_GRAFICO = `<div class="legenda">
  <span><i style="background:var(--ok)"></i>Pago</span>
  <span><i style="background:var(--erro)"></i>Vencido</span>
  <span><i style="background:var(--marca)"></i>A vencer</span></div>`;

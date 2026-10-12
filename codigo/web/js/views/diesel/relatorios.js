// Diesel · relatório do período (semana, quinzena, mês ou ano) em três níveis:
//   Simples   — o essencial em frases e quatro números, e quanto cada máquina gastou;
//   Detalhado — + comparação com o período anterior, pontos de atenção, gráfico por dia, consumo e combustíveis;
//   Completo  — + cada abastecimento (com o consumo do trecho), por dia, por posto e por pessoa.
// O nível escolhido fica guardado neste aparelho.
import { api } from "../../api.js";
import { montarGraficoSeries } from "../../grafico.js";
import { icone } from "../../icons.js";
import { brl, dataBR, esc, mensagemErro, toast, urlArquivo } from "../../ui.js";
import { litros, numero } from "./estado.js";
import { htmlKpis } from "./painel.js";

export const NIVEIS = [
  ["simples", "Simples", "O essencial: quanto foi abastecido, o saldo e quanto cada máquina gastou."],
  ["detalhado", "Detalhado", "Mais: comparação com o período anterior, pontos de atenção, gráfico por dia, consumo e combustíveis."],
  ["completo", "Completo", "Tudo: cada abastecimento com o consumo do trecho, por dia, por posto e por quem abasteceu."],
];
const CHAVE_NIVEL = "finpro.diesel.nivel";
const TITULOS = { semana: "semanal", quinzena: "quinzenal", mes: "mensal", ano: "anual" };
const ANTERIOR = { semana: "à semana anterior", quinzena: "à quinzena anterior", mes: "ao mês anterior", ano: "ao ano anterior" };
const CORES = { "Diesel S10": "#2a62c7", "Diesel comum": "#d97706", Gasolina: "#db2777", Etanol: "#16a34a", "Arla 32": "#8b5cf6" };
const ICONE_ALERTA = { erro: "erro", aviso: "alerta", info: "info" };

export const relatorio = { nivel: lerNivel(), maquina: "", combustivel: "" };

function lerNivel() {
  try {
    const salvo = localStorage.getItem(CHAVE_NIVEL);
    return NIVEIS.some(([chave]) => chave === salvo) ? salvo : "simples";
  } catch {
    return "simples";
  }
}

export function escolherNivel(nivel) {
  if (!NIVEIS.some(([chave]) => chave === nivel)) return;
  relatorio.nivel = nivel;
  try {
    localStorage.setItem(CHAVE_NIVEL, nivel);
  } catch { /* sem armazenamento: vale só nesta visita */ }
}

const pct = (v) => `${String(v ?? 0).replace(".", ",")}%`;
const precoL = (v) => (v ? `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 3 })}` : "—");

function chipVariacao(v, { inverso = true } = {}) {
  if (v === null || v === undefined) return `<span class="chip">sem comparação</span>`;
  if (Math.abs(v) < 0.5) return `<span class="chip">igual</span>`;
  // gastar mais é ruim (vermelho), gastar menos é bom (verde)
  const ruim = inverso ? v > 0 : v < 0;
  return `<span class="chip ${ruim ? "erro" : "ok"}">${v > 0 ? "▲ +" : "▼ −"}${String(Math.abs(Math.round(v))).replace(".", ",")}%</span>`;
}

function textoVariacao(v) {
  if (v === null || v === undefined) return "";
  if (Math.abs(v) < 0.5) return "igual";
  return `${v > 0 ? "+" : "−"}${Math.abs(Math.round(v))}%`;
}

// ------------------------------------------------------------------ filtros (detalhado e completo)

function filtrarMaquinas(lista) {
  return lista.filter((m) => (!relatorio.maquina || m.maquina === relatorio.maquina)
    && (!relatorio.combustivel || (m.combustiveis || []).includes(relatorio.combustivel)));
}

function filtrarAbastecimentos(lista) {
  return lista.filter((a) => (!relatorio.maquina || a.maquina === relatorio.maquina)
    && (!relatorio.combustivel || (a.combustivel || "Diesel S10") === relatorio.combustivel));
}

function htmlFiltros(d) {
  if (relatorio.nivel === "simples") return "";
  const maquinas = [...new Set([...d.por_maquina.map((m) => m.maquina), relatorio.maquina].filter(Boolean))].sort();
  const combustiveis = [...new Set([...d.por_combustivel.map((c) => c.combustivel), relatorio.combustivel].filter(Boolean))];
  const ativo = relatorio.maquina || relatorio.combustivel;
  return `<div class="dr-filtros">
    <label class="dr-filtro">${icone("caminhao", 14)}
      <select class="input input-sm" data-filtro-diesel="maquina" aria-label="Filtrar por máquina">
        <option value="">Todas as máquinas</option>
        ${maquinas.map((m) => `<option ${m === relatorio.maquina ? "selected" : ""}>${esc(m)}</option>`).join("")}
      </select></label>
    <label class="dr-filtro">${icone("diesel", 14)}
      <select class="input input-sm" data-filtro-diesel="combustivel" aria-label="Filtrar por combustível">
        <option value="">Todos os combustíveis</option>
        ${combustiveis.map((c) => `<option ${c === relatorio.combustivel ? "selected" : ""}>${esc(c)}</option>`).join("")}
      </select></label>
    ${ativo ? `<button class="btn btn-sm btn-fantasma" data-acao="limpar-filtro-diesel">${icone("x", 13)} Limpar filtro</button>
      <span class="sutil">O filtro vale para as tabelas de máquinas e de abastecimentos; os totais do topo são do período inteiro.</span>` : ""}
  </div>`;
}

// ------------------------------------------------------------------ montagem

export function htmlRelatorios(d) {
  const [, , descricao] = NIVEIS.find(([chave]) => chave === relatorio.nivel);
  const topo = `<section class="card dr-topo">
      <div class="dr-topo-linha">
        <div class="alternar-modo" role="tablist" aria-label="Nível do relatório">
          ${NIVEIS.map(([chave, rotulo]) => `<button role="tab" data-acao="nivel-relatorio" data-nivel="${chave}"
            class="${relatorio.nivel === chave ? "ativo" : ""}" aria-selected="${relatorio.nivel === chave}">${rotulo}</button>`).join("")}
        </div>
        <span class="sutil dr-descricao">${esc(descricao)}</span>
        <span class="espaco"></span>
        <button class="btn btn-sm" data-acao="enviar-relatorio-diesel" title="Manda este relatório, neste nível, pelo bot do diesel para os responsáveis">
          ${icone("telegram", 15)} Enviar no Telegram</button>
      </div>
      ${htmlFiltros(d)}
    </section>`;
  if (relatorio.nivel === "simples") return topo + htmlSimples(d);
  return topo + htmlDetalhado(d) + (relatorio.nivel === "completo" ? htmlCompleto(d) : "");
}

export function desenharGraficoDiesel(raiz, d) {
  const alvo = raiz?.querySelector("[data-grafico-diesel]");
  if (!alvo) return;
  const combustiveis = [...new Set(d.serie.flatMap((s) => Object.keys(s.por_combustivel)))];
  montarGraficoSeries(alvo, {
    linhas: d.serie.map((s) => ({ rotulo: s.rotulo, valores: s.por_combustivel })),
    series: combustiveis.map((c) => ({ chave: c, rotulo: c, cor: CORES[c] || "#94a3b8" })),
    vazio: "Nenhum abastecimento no período.",
  });
}

// ------------------------------------------------------------------ simples

function htmlSimples(d) {
  const tipo = d.periodo.tipo;
  const maior = d.por_maquina[0];
  const previsao = d.previsao;
  const atencao = d.alertas.filter((a) => a.nivel !== "info");
  const saldo = previsao ? previsao.saldo : d.saldo.valor;
  const frases = [
    d.abastecido.quantidade
      ? `${icone("diesel", 16)} Foram abastecidos <strong>${brl(d.abastecido.custo)}</strong> (${litros(d.abastecido.litros)}) em
         ${d.abastecido.quantidade} abastecimento(s).`
      : `${icone("diesel", 16)} Nenhum abastecimento neste período.`,
    d.variacao.custo !== null && d.variacao.custo !== undefined
      ? `${icone("grafico", 16)} ${textoVariacao(d.variacao.custo) === "igual" ? "Igual" : `<strong>${textoVariacao(d.variacao.custo)}</strong>`}
         em relação ${ANTERIOR[tipo]} (${brl(d.anterior.custo)}).` : "",
    `${icone("carteira", 16)} ${previsao ? "Saldo no posto agora" : "Saldo no fim do período"}: <strong class="${saldo < 0 ? "valor-saida" : ""}">${brl(saldo)}</strong>${
      previsao && previsao.dias !== null && previsao.saldo > 0 ? ` — dá para uns <strong>${previsao.dias} dia(s)</strong> no ritmo atual (até ${dataBR(previsao.acaba_em)}).` : "."}`,
    maior ? `${icone("caminhao", 16)} Quem mais gastou: <strong>${esc(maior.maquina)}</strong> — ${brl(maior.custo)} (${litros(maior.litros)}, ${pct(maior.percentual)} do total).` : "",
    d.comprado.quantidade ? `${icone("mais", 16)} Comprado no período: ${brl(d.comprado.valor)} (${litros(d.comprado.litros)}).` : "",
  ].filter(Boolean);
  return `<section class="card dr-frases">
      <h3>${icone("relatorio", 17)} Relatório ${TITULOS[tipo]} · ${esc(d.periodo.rotulo)}</h3>
      <ul>${frases.map((f) => `<li>${f}</li>`).join("")}</ul>
      ${atencao.length ? `<button class="dr-atencao" data-acao="nivel-relatorio" data-nivel="detalhado">
        ${icone("alerta", 15)} ${atencao.length} ponto(s) de atenção — ver no relatório detalhado</button>` : ""}
    </section>
    <section class="resumo-lista dr-kpis">
      <div class="card resumo-item"><span>Abastecido</span><strong>${brl(d.abastecido.custo)}</strong><small class="sutil">${litros(d.abastecido.litros)}</small></div>
      <div class="card resumo-item"><span>Abastecimentos</span><strong>${d.abastecido.quantidade}</strong><small class="sutil">${litros(d.abastecido.por_dia)}/dia</small></div>
      <div class="card resumo-item ${saldo < 0 ? "erro" : "ok"}"><span>Saldo no posto</span><strong>${brl(saldo)}</strong>
        <small class="sutil">${previsao ? "agora" : "no fim do período"}</small></div>
      <div class="card resumo-item"><span>O saldo dura</span><strong>${previsao && previsao.dias !== null ? `~${previsao.dias} dia(s)` : "—"}</strong>
        <small class="sutil">${previsao ? `gasto médio ${brl(previsao.por_dia)}/dia` : "só no período atual"}</small></div>
    </section>
    <article class="card caixa-ranking">
      <h3>${icone("caminhao", 17)} Quanto cada máquina gastou</h3>
      ${barrasValor(d.por_maquina, (m) => m.maquina, (m) => m.custo, (m) => `${litros(m.litros)} · ${m.abastecimentos}×`)}
    </article>`;
}

function barrasValor(lista, nome, valor, detalhe) {
  if (!lista.length) return `<p class="sutil">Nenhum abastecimento no período.</p>`;
  const maior = Math.max(...lista.map(valor), 0);
  return `<ul class="caixa-barras">${lista.map((item) => `<li>
      <div class="caixa-barra-topo"><strong title="${esc(nome(item))}">${esc(nome(item))}</strong>
        <span>${brl(valor(item))} <small class="sutil">${detalhe(item)}</small></span></div>
      <div class="caixa-barra"><i style="width:${maior ? Math.max(3, (valor(item) / maior) * 100) : 0}%"></i></div>
    </li>`).join("")}</ul>`;
}

// ------------------------------------------------------------------ detalhado

function htmlAlertas(d) {
  if (!d.alertas.length) return `<section class="card dr-alertas ok">${icone("check", 16)} Nenhum ponto de atenção neste período.</section>`;
  return `<section class="card dr-alertas">
    <h3>${icone("alerta", 17)} Pontos de atenção</h3>
    <ul>${d.alertas.map((a) => `<li class="dr-alerta ${a.nivel}">${icone(ICONE_ALERTA[a.nivel] || "info", 15)}<span>${esc(a.texto)}</span></li>`).join("")}</ul>
  </section>`;
}

function htmlComparacao(d) {
  const a = d.anterior;
  const precoAtual = d.abastecido.litros ? d.abastecido.custo / d.abastecido.litros : 0;
  const precoAntes = a.litros ? a.custo / a.litros : 0;
  const linhas = [
    ["Valor abastecido", brl(d.abastecido.custo), brl(a.custo), d.variacao.custo],
    ["Litros", litros(d.abastecido.litros), litros(a.litros), d.variacao.litros],
    ["Abastecimentos", d.abastecido.quantidade, a.abastecimentos, a.abastecimentos ? ((d.abastecido.quantidade - a.abastecimentos) / a.abastecimentos) * 100 : null],
    ["R$ médio por litro", precoL(precoAtual), precoL(precoAntes), precoAntes ? ((precoAtual - precoAntes) / precoAntes) * 100 : null],
  ];
  return `<article class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("grafico", 15)} Comparação com ${esc(a.rotulo)}</strong></div>
    <div class="tabela-wrap"><table class="tabela">
      <thead><tr><th></th><th class="num">Este período</th><th class="num">Anterior</th><th>Variação</th></tr></thead>
      <tbody>${linhas.map(([rotulo, atual, antes, v]) => `<tr><td>${rotulo}</td><td class="num"><strong>${atual}</strong></td>
        <td class="num">${antes}</td><td>${chipVariacao(v)}</td></tr>`).join("")}</tbody>
    </table></div>
    ${d.previsao && d.previsao.dias !== null && d.previsao.saldo > 0 ? `<p class="sutil dr-nota">${icone("relogio", 14)} No ritmo dos últimos 30 dias
      (${brl(d.previsao.por_dia)}/dia), o saldo de ${brl(d.previsao.saldo)} dura uns <strong>${d.previsao.dias} dia(s)</strong>, até ${dataBR(d.previsao.acaba_em)}.</p>` : ""}
  </article>`;
}

function htmlTabelaMaquinas(d) {
  const maquinas = filtrarMaquinas(d.por_maquina);
  const titulo = TITULOS[d.periodo.tipo];
  if (!maquinas.length) {
    return `<section class="card tabela-card"><div class="vazio"><div class="vazio-icone">${icone("grafico", 26)}</div>
      <h3>${d.por_maquina.length ? "Nenhuma máquina com este filtro" : "Nenhum abastecimento no período"}</h3>
      <p>${d.por_maquina.length ? "Mude ou limpe o filtro acima." : "Use as setas para ver outro período."}</p></div></section>`;
  }
  const soma = (campo) => maquinas.reduce((s, m) => s + (m[campo] || 0), 0);
  return `<section class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("relatorio", 15)} Relatório ${titulo} por máquina · ${esc(d.periodo.rotulo)}</strong></div>
    <div class="tabela-wrap"><table class="tabela dr-tabela">
      <thead><tr><th>Máquina</th><th class="num">Litros</th><th class="num">Valor</th><th class="num">% do total</th>
        <th class="num">Abast.</th><th class="num">Litros/dia</th><th class="num">Média/abast.</th><th>Consumo</th>
        <th class="num">Antes</th><th>Variação</th><th>Último</th></tr></thead>
      <tbody>${maquinas.map((m) => `<tr class="${m.acima_do_normal ? "dr-acima" : ""}">
        <td><strong>${esc(m.maquina)}</strong>${m.placa ? ` <small class="sutil">${esc(m.placa)}</small>` : ""}
          ${(m.combustiveis || []).length ? `<small class="por-quem">${esc(m.combustiveis.join(", "))}</small>` : ""}
          ${m.acima_do_normal ? `<small class="por-quem valor-saida">${icone("alerta", 11)} ${m.acima_do_normal}% acima do normal (${litros(m.media_normal)}/dia)</small>` : ""}</td>
        <td class="num">${litros(m.litros)}</td>
        <td class="num"><strong>${m.custo ? brl(m.custo) : "—"}</strong>${m.custo_por_litro ? `<small class="por-quem">${precoL(m.custo_por_litro)}/L</small>` : ""}</td>
        <td class="num">${pct(m.percentual)}</td><td class="num">${m.abastecimentos}</td>
        <td class="num">${litros(m.por_dia)}</td><td class="num">${litros(m.por_abastecimento)}</td>
        <td>${m.consumo.rotulo ? `<span class="chip info">${esc(m.consumo.rotulo)}</span>` : "—"}</td>
        <td class="num">${m.litros_anterior ? litros(m.litros_anterior) : "—"}</td><td>${chipVariacao(m.variacao)}</td>
        <td>${dataBR(m.ultimo)}</td></tr>`).join("")}</tbody>
      <tfoot><tr><td>Total${maquinas.length < d.por_maquina.length ? " (filtrado)" : ""}</td><td class="num">${litros(soma("litros"))}</td>
        <td class="num">${brl(soma("custo"))}</td><td class="num">${pct(Math.round(soma("percentual") * 10) / 10)}</td>
        <td class="num">${soma("abastecimentos")}</td><td class="num">${litros(soma("por_dia"))}</td><td colspan="5"></td></tr></tfoot>
    </table></div>
  </section>`;
}

function htmlCombustiveis(d) {
  if (!d.por_combustivel.length) return "";
  return `<article class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("diesel", 15)} Por combustível</strong></div>
    <div class="tabela-wrap"><table class="tabela">
      <thead><tr><th>Combustível</th><th class="num">Comprado</th><th class="num">Abastecido</th><th class="num">Abast.</th>
        <th class="num">Valor</th><th class="num">Preço médio</th></tr></thead>
      <tbody>${d.por_combustivel.map((c) => `<tr><td><i class="ponto-serie" style="background:${CORES[c.combustivel] || "#94a3b8"}"></i> <strong>${esc(c.combustivel)}</strong></td>
        <td class="num">${litros(c.comprado)}</td><td class="num">${litros(c.abastecido)}</td><td class="num">${c.abastecimentos}</td>
        <td class="num">${c.custo ? brl(c.custo) : "—"}</td><td class="num">${precoL(c.preco_medio)}</td></tr>`).join("")}</tbody>
    </table></div>
  </article>`;
}

function htmlCompras(d) {
  return `<article class="card caixa-ranking">
    <h3>${icone("carteira", 17)} Compras no período</h3>
    ${d.compras.length ? `<ul class="lista-mini">${d.compras.map((c) => `<li><div class="info">
        <div class="titulo">${c.valor ? brl(c.valor) : "sem valor"} · ${litros(c.litros)} de ${esc(c.combustivel || "Diesel S10")}${c.preco_litro ? ` · ${precoL(c.preco_litro)}/L` : ""}</div>
        <div class="sutil">${dataBR(c.data)}${c.posto ? ` · ${esc(c.posto)}` : ""}${c.forma ? ` · ${esc(c.forma)}` : ""}</div></div>
        ${c.arquivo ? `<a class="btn-icone" href="${urlArquivo(c.arquivo)}" target="_blank" rel="noopener" title="Ver comprovante">${icone("clipe", 15)}</a>` : ""}</li>`).join("")}</ul>`
      : `<p class="sutil">Nenhuma compra no período.</p>`}
  </article>`;
}

function htmlDetalhado(d) {
  return `${htmlKpis(d)}
    ${htmlAlertas(d)}
    <section class="dr-duas">
      ${htmlComparacao(d)}
      <article class="card">
        <h3 class="dr-h3">${icone("grafico", 17)} ${d.periodo.tipo === "ano" ? "Valor abastecido por mês" : "Valor abastecido por dia"}</h3>
        <div data-grafico-diesel></div>
      </article>
    </section>
    ${htmlTabelaMaquinas(d)}
    <section class="dr-duas">
      ${htmlCombustiveis(d)}
      ${htmlCompras(d)}
    </section>`;
}

// ------------------------------------------------------------------ completo

function htmlAbastecimentos(d) {
  const lista = filtrarAbastecimentos(d.abastecimentos);
  if (!lista.length) return "";
  const grupos = new Map();
  [...lista].sort((a, b) => `${a.data}${a.hora || ""}`.localeCompare(`${b.data}${b.hora || ""}`))
    .forEach((a) => grupos.set(a.maquina || "Sem máquina", [...(grupos.get(a.maquina || "Sem máquina") || []), a]));
  const ordem = [...grupos.entries()].sort((x, y) => y[1].reduce((s, a) => s + a.custo, 0) - x[1].reduce((s, a) => s + a.custo, 0));
  return `<section class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("lista", 15)} Todos os abastecimentos, por máquina</strong>
      <span class="sutil">${lista.length} abastecimento(s)</span></div>
    <div class="tabela-wrap"><table class="tabela dr-tabela dr-abast">
      <thead><tr><th>Data</th><th>Combustível</th><th class="num">Litros</th><th class="num">Preço/L</th><th class="num">Valor</th>
        <th class="num">Horímetro / km</th><th>Trecho</th><th>Pedido / posto</th><th>Quem</th><th></th></tr></thead>
      ${ordem.map(([maquina, itens]) => {
        const totalL = itens.reduce((s, a) => s + (a.litros || 0), 0);
        const totalR = itens.reduce((s, a) => s + (a.custo || 0), 0);
        return `<tbody><tr class="dr-grupo"><th colspan="10">${icone("caminhao", 14)} ${esc(maquina)}
            <span class="sutil">· ${itens.length}× · ${litros(totalL)} · ${brl(totalR)}</span></th></tr>
          ${itens.map((a) => `<tr>
            <td>${dataBR(a.data)}${a.hora ? ` <small class="sutil">${esc(a.hora)}</small>` : ""}</td>
            <td><span class="chip">${esc(a.combustivel || "Diesel S10")}</span></td>
            <td class="num">${litros(a.litros)}</td><td class="num">${precoL(a.preco_litro)}</td>
            <td class="num"><strong>${brl(a.custo)}</strong>${a.valor ? "" : `<small class="por-quem">estimado</small>`}</td>
            <td class="num">${a.medidor ? `${esc(numero(a.medidor))} ${a.medidor_tipo === "km" ? "km" : a.medidor_tipo === "horas" ? "h" : ""}` : `<span class="sutil">—</span>`}</td>
            <td>${a.trecho ? `<span class="chip info">${esc(a.trecho.rotulo)}</span>
              <small class="por-quem">${esc(numero(a.trecho.rodado))} ${esc(a.trecho.unidade_rodado)} desde ${dataBR(a.trecho.data_anterior)}</small>` : `<span class="sutil">—</span>`}</td>
            <td>${a.documento ? `nº ${esc(a.documento)}` : ""}${a.posto ? `<small class="por-quem">${esc(a.posto)}</small>` : ""}</td>
            <td>${esc(a.pessoa || "")}${a.lancado_por ? `<small class="por-quem">lançado por ${esc(a.lancado_por)}</small>` : ""}</td>
            <td>${a.arquivo ? `<a class="btn-icone" href="${urlArquivo(a.arquivo)}" target="_blank" rel="noopener" title="Ver canhoto">${icone("clipe", 15)}</a>` : ""}</td>
          </tr>`).join("")}</tbody>`;
      }).join("")}
    </table></div>
  </section>`;
}

function htmlPorDia(d) {
  const linhas = d.serie.filter((s) => s.abastecimentos);
  if (!linhas.length) return "";
  const combustiveis = [...new Set(d.serie.flatMap((s) => Object.keys(s.por_combustivel)))];
  return `<article class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("calendario", 15)} ${d.periodo.tipo === "ano" ? "Mês a mês" : "Dia a dia"}</strong></div>
    <div class="tabela-wrap"><table class="tabela">
      <thead><tr><th>${d.periodo.tipo === "ano" ? "Mês" : "Dia"}</th><th class="num">Abast.</th><th class="num">Litros</th>
        ${combustiveis.map((c) => `<th class="num">${esc(c)}</th>`).join("")}<th class="num">Total</th></tr></thead>
      <tbody>${linhas.map((s) => `<tr><td>${esc(s.rotulo)}</td><td class="num">${s.abastecimentos}</td><td class="num">${litros(s.litros)}</td>
        ${combustiveis.map((c) => `<td class="num">${s.por_combustivel[c] ? brl(s.por_combustivel[c]) : "—"}</td>`).join("")}
        <td class="num"><strong>${brl(s.valor)}</strong></td></tr>`).join("")}</tbody>
    </table></div>
  </article>`;
}

function htmlCompleto(d) {
  return `${htmlAbastecimentos(d)}
    <section class="dr-duas">
      ${htmlPorDia(d)}
      <div class="dr-pilha">
        <article class="card caixa-ranking"><h3>${icone("banco", 17)} Por posto</h3>
          ${barrasValor(d.por_posto, (p) => p.nome, (p) => p.valor, (p) => `${litros(p.litros)} · ${p.abastecimentos}×`)}</article>
        <article class="card caixa-ranking"><h3>${icone("pessoa", 17)} Quem abasteceu</h3>
          ${barrasValor(d.por_pessoa, (p) => p.nome, (p) => p.valor, (p) => `${litros(p.litros)} · ${p.abastecimentos}×`)}</article>
      </div>
    </section>`;
}

// ------------------------------------------------------------------ Telegram

export async function enviarRelatorio(tela) {
  try {
    const r = await api.post(`/api/diesel/relatorio/enviar?periodo=${tela.periodo}&data=${tela.data}&nivel=${relatorio.nivel}`, {});
    toast(`Relatório ${relatorio.nivel} enviado para ${r.enviado} responsável(is) no Telegram.`, "ok");
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

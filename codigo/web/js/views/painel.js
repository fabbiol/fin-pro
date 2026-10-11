// Tela: Painel (indicadores, gráfico e listas rápidas).
import { api } from "../api.js";
import { LEGENDA_GRAFICO, montarGrafico } from "../grafico.js";
import { icone } from "../icons.js";
import { MESES, abrirModal, brl, copiar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../ui.js";

let raiz = null;
let previsao = null;

export async function montar(el) {
  raiz = el;
  el.innerHTML = `
    <section class="kpis">${'<div class="card kpi"><div class="esqueleto" style="height:16px;width:50%"></div><div class="esqueleto" style="height:30px;width:70%;margin-top:14px"></div></div>'.repeat(4)}</section>
    <div class="card esqueleto" style="height:320px"></div>`;
  el.addEventListener("click", aoClicar);
  await carregar();
}

export function desmontar() {
  raiz?.removeEventListener("click", aoClicar);
  raiz = null;
}

async function carregar() {
  let dados;
  try {
    [dados, previsao] = await Promise.all([api.get("/api/painel"), api.get("/api/previsao", { semanas: 8 }).catch(() => null)]);
  } catch (erro) {
    if (!raiz) return;
    raiz.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar o painel</h3><p>${esc(mensagemErro(erro))}</p></div>`;
    return;
  }
  if (raiz) renderizar(dados);
}

function kpi({ titulo, valor, detalhe, iconeNome, classe, link }) {
  return `<a class="card kpi ${classe}" href="${link}">
    <div class="kpi-topo"><span>${titulo}</span><span class="kpi-icone">${icone(iconeNome, 18)}</span></div>
    <div class="kpi-valor">${valor}</div>
    <div class="kpi-detalhe">${detalhe}</div></a>`;
}

const plural = (n, singular, pluralTexto) => `${n} ${n === 1 ? singular : pluralTexto}`;

function detalheVencidos(k) {
  const partes = [k.vencidos_boletos_qtd ? plural(k.vencidos_boletos_qtd, "boleto", "boletos") : "",
    k.vencidos_pix_qtd ? plural(k.vencidos_pix_qtd, "Pix", "Pix") : ""].filter(Boolean);
  return `${partes.join(" e ")} em atraso`;
}

function blocoData(iso, classe = "") {
  const [, m, d] = iso.split("-");
  return `<div class="data-bloco ${classe}"><strong>${d}</strong><span>${MESES[Number(m) - 1]}</span></div>`;
}

function itemBoleto(r) {
  const classe = r.situacao === "vencido" ? "erro" : r.situacao === "vence_hoje" || (r.dias_para_vencer ?? 99) <= 3 ? "aviso" : "";
  let quando = "";
  if (r.situacao === "vencido") quando = `vencido há ${Math.abs(r.dias_para_vencer)} dia(s)`;
  else if (r.situacao === "vence_hoje") quando = "vence hoje";
  else if (r.dias_para_vencer !== null) quando = `vence em ${r.dias_para_vencer} dia(s)`;
  const pix = r.tipo_pagamento === "pix";
  return `<li data-id="${r.id}" data-tipo="${pix ? "pix" : "boletos"}">
    ${r.vencimento ? blocoData(r.vencimento, classe) : `<div class="data-bloco">—</div>`}
    <div class="info">
      <div class="titulo" title="${esc(r.beneficiario)}">${pix ? `<span class="chip">Pix</span> ` : ""}${esc(r.beneficiario || (pix ? "Recebedor não informado" : "Sem beneficiário"))}</div>
      <div class="sutil">${quando}${r.numero_documento ? ` · Doc. ${esc(r.numero_documento)}` : ""}${pix && r.chave_formatada ? ` · ${esc(r.chave_formatada)}` : ""}</div>
    </div>
    <div class="valor">${brl(r.valor)}</div>
    <div class="acoes">
      ${pix && r.chave ? `<button class="btn-icone" data-acao="copiar" data-linha="${esc(r.chave)}" data-rotulo="Chave Pix copiada" title="Copiar chave Pix">${icone("copiar", 16)}</button>` : ""}
      ${!pix && r.linha_digitavel ? `<button class="btn-icone" data-acao="copiar" data-linha="${esc(r.linha_digitos)}" title="Copiar linha digitável">${icone("copiar", 16)}</button>` : ""}
      <button class="btn-icone ok" data-acao="pagar" title="Marcar como pago">${icone("check", 16)}</button>
    </div></li>`;
}

// ------------------------------------------------------------------ previsão de saídas

function periodoSemana(s, indice) {
  if (indice === 0) return "Próximos 7 dias";
  return `${dataBR(s.inicio).slice(0, 5)} a ${dataBR(s.fim).slice(0, 5)}`;
}

function htmlPrevisao(p) {
  if (!p) return "";
  const maior = Math.max(p.em_atraso.total, ...p.semanas.map((s) => s.total), 1);
  const linha = (rotulo, total, quantidade, alvo, partes, classe = "") => `
    <button class="prev-linha ${classe}" data-previsao="${alvo}" ${quantidade ? "" : "disabled"}>
      <span class="prev-rotulo">${rotulo}</span>
      <span class="prev-barra">${partes.map(([valor, cor]) => valor ? `<i class="${cor}" style="width:${(valor / maior) * 100}%"></i>` : "").join("")}</span>
      <span class="prev-valor"><strong>${brl(total)}</strong><small>${quantidade} lançamento(s)</small></span>
    </button>`;
  return `<section class="card previsao">
    <div class="card-cabecalho"><h3>${icone("calendario", 17)} Previsão de saídas</h3>
      <div class="legenda"><span><i class="prev-boleto"></i>Boletos</span><span><i class="prev-pix"></i>Pix</span><span><i class="prev-atraso"></i>Em atraso</span></div></div>
    <div class="card-corpo">
      <div class="prev-totais">
        <div><span>Em atraso</span><strong class="erro-texto-forte">${brl(p.em_atraso.total)}</strong></div>
        <div><span>Próximos 7 dias</span><strong>${brl(p.totais["7_dias"])}</strong></div>
        <div><span>Próximos 30 dias</span><strong>${brl(p.totais["30_dias"])}</strong></div>
        <div><span>Próximas 8 semanas</span><strong>${brl(p.totais.periodo)}</strong></div>
      </div>
      <div class="prev-lista">
        ${p.em_atraso.quantidade ? linha("Em atraso", p.em_atraso.total, p.em_atraso.quantidade, "atraso", [[p.em_atraso.total, "prev-atraso"]], "atraso") : ""}
        ${p.semanas.map((s, i) => linha(periodoSemana(s, i), s.total, s.quantidade, String(i), [[s.boletos, "prev-boleto"], [s.pix, "prev-pix"]])).join("")}
      </div>
      ${p.sem_vencimento.quantidade ? `<p class="sutil">${p.sem_vencimento.quantidade} lançamento(s) sem vencimento (${brl(p.sem_vencimento.total)}) não entram na previsão.</p>` : ""}
    </div></section>`;
}

function abrirSemana(alvo) {
  const grupo = alvo === "atraso" ? { ...previsao.em_atraso, titulo: "Em atraso" }
    : { ...previsao.semanas[Number(alvo)], titulo: periodoSemana(previsao.semanas[Number(alvo)], Number(alvo)) };
  abrirModal({
    titulo: `Saídas · ${grupo.titulo}`,
    tamanho: "lg",
    corpo: `<ul class="lista-mini">${grupo.itens.map((i) => `<li>
        <div class="info"><div class="titulo">${i.tipo === "pix" ? `<span class="chip">Pix</span> ` : ""}${esc(i.nome || "Sem nome")}</div>
          <div class="sutil">Vence ${dataBR(i.vencimento)}${i.centro_custo ? ` · ${esc(i.centro_custo)}` : ""}</div></div>
        <div class="valor">${brl(i.valor)}</div>
        <a class="btn btn-sm btn-fantasma" href="#/${i.tipo === "pix" ? "pix" : "boletos"}?q=${encodeURIComponent(i.nome || "")}">Abrir</a></li>`).join("")}</ul>
      <p class="sutil" style="margin-top:12px">Total: <strong>${brl(grupo.total)}</strong></p>`,
    rodape: `<button class="btn btn-primario" data-fechar>Fechar</button>`,
  });
}

function renderizar(d) {
  const k = d.indicadores;
  if (!k.total_qtd && !d.recentes.length) {
    raiz.innerHTML = `<div class="card vazio" style="padding:70px 24px">
      <div class="vazio-icone">${icone("boleto", 28)}</div>
      <h3>Nenhum boleto lançado ainda</h3>
      <p>Envie o PDF ou a foto de um boleto. O sistema lê a linha digitável, o beneficiário, o nº do documento,
         o vencimento e o valor, e grava tudo na planilha.</p>
      <a class="btn btn-primario" href="#/ler" style="margin-top:8px">${icone("upload", 16)} Ler meu primeiro boleto</a></div>`;
    return;
  }

  const maiorBeneficiario = Math.max(...d.top_beneficiarios.map((b) => b.valor), 1);

  raiz.innerHTML = `
    <section class="kpis">
      ${kpi({ titulo: "A pagar", valor: brl(k.pendentes_valor), detalhe: `${plural(k.pendentes_qtd, "pendente", "pendentes")} (boletos e Pix)`, iconeNome: "carteira", classe: "marca", link: "#/boletos?situacao=pendente" })}
      ${kpi({ titulo: "Vencidos", valor: brl(k.vencidos_valor), detalhe: k.vencidos_qtd ? detalheVencidos(k) : "Nenhum em atraso", iconeNome: "alerta", classe: "erro", link: "#/boletos?situacao=vencido" })}
      ${kpi({ titulo: "Vencem em 7 dias", valor: brl(k.proximos7_valor), detalhe: `${plural(k.proximos7_qtd, "lançamento", "lançamentos")} (boletos e Pix)`, iconeNome: "calendario", classe: "aviso", link: "#/boletos?situacao=a_vencer,vence_hoje" })}
      ${kpi({ titulo: "Pagos no mês", valor: brl(k.pagos_mes_valor), detalhe: k.juros_mes_valor
        ? `${plural(k.pagos_mes_qtd, "pago", "pagos")} · <span class="juros-linha">${brl(k.juros_mes_valor)} de juros (${k.juros_mes_qtd})</span>`
        : `${plural(k.pagos_mes_qtd, "pago", "pagos")} (boletos e Pix) · sem juros`, iconeNome: "ok", classe: "ok", link: "#/boletos?situacao=pago" })}
    </section>

    ${htmlPrevisao(previsao)}

    <section class="painel-grade">
      <div class="card">
        <div class="card-cabecalho"><h3>${icone("painel", 17)} Vencimentos por mês</h3>${LEGENDA_GRAFICO}</div>
        <div class="card-corpo" id="grafico"></div>
      </div>

      <div class="card">
        <div class="card-cabecalho"><h3>${icone("upload", 17)} Lançados neste mês</h3></div>
        <div class="card-corpo">
          <div class="destaque-mes"><strong>${k.lancados_mes_qtd}</strong><span class="sutil">lançamento(s) · ${brl(k.lancados_mes_valor)}</span></div>
          <ul class="lista-mini">
            ${d.recentes.map((r) => `<li>
              <div class="info"><div class="titulo">${esc(r.beneficiario || "Sem beneficiário")}</div>
              <div class="sutil">${dataHoraBR(r.data_lancamento)}</div></div>
              <div class="valor">${brl(r.valor)}</div></li>`).join("") || `<li class="sutil">Nenhum lançamento recente.</li>`}
          </ul>
        </div>
      </div>

      <div class="painel-colunas">
        <div class="card">
          <div class="card-cabecalho"><h3>${icone("calendario", 17)} Próximos vencimentos</h3>
            <a class="btn btn-sm btn-fantasma" href="#/boletos?situacao=a_vencer,vence_hoje">Ver todos</a></div>
          <div class="card-corpo"><ul class="lista-mini">${d.proximos.map(itemBoleto).join("") || `<li class="sutil">Nada a vencer. 🎉</li>`}</ul></div>
        </div>
        <div class="card">
          <div class="card-cabecalho"><h3 style="color:var(--erro)">${icone("alerta", 17)} Vencidos${d.vencidos.length ? ` (${d.vencidos.length})` : ""}</h3>
            <span class="linha-botoes">${k.vencidos_boletos_qtd ? `<a class="btn btn-sm btn-fantasma" href="#/boletos?situacao=vencido">Boletos</a>` : ""}
              ${k.vencidos_pix_qtd ? `<a class="btn btn-sm btn-fantasma" href="#/pix?situacao=vencido">Pix</a>` : ""}</span></div>
          <div class="card-corpo"><ul class="lista-mini lista-rolagem">${d.vencidos.map(itemBoleto).join("") || `<li class="sutil">Nenhum boleto ou Pix vencido.</li>`}</ul></div>
        </div>
        <div class="card">
          <div class="card-cabecalho"><h3>${icone("banco", 17)} Maiores beneficiários</h3></div>
          <div class="card-corpo"><ul class="lista-mini">
            ${d.top_beneficiarios.map((b) => `<li><div class="info">
                <div style="display:flex;justify-content:space-between;gap:10px">
                  <span class="titulo" title="${esc(b.beneficiario)}">${esc(b.beneficiario)}</span><span class="valor">${brl(b.valor)}</span></div>
                <div class="barra-ranking"><div style="width:${Math.max(4, (b.valor / maiorBeneficiario) * 100)}%"></div></div>
                <div class="sutil">${plural(b.quantidade, "lançamento", "lançamentos")}</div></div></li>`).join("") || `<li class="sutil">Sem dados.</li>`}
          </ul></div>
        </div>
      </div>
    </section>`;

  montarGrafico(raiz.querySelector("#grafico"), d.serie_mensal);
}

async function aoClicar(e) {
  const semana = e.target.closest("[data-previsao]");
  if (semana && previsao) {
    abrirSemana(semana.dataset.previsao);
    return;
  }
  const alvo = e.target.closest("[data-acao]");
  if (!alvo) return;
  if (alvo.dataset.acao === "copiar") {
    copiar((alvo.dataset.linha || "").replace(/\D/g, ""), alvo.dataset.rotulo || "Linha digitável copiada");
  } else if (alvo.dataset.acao === "pagar") {
    const { id, tipo } = alvo.closest("[data-id]").dataset;
    alvo.disabled = true;
    try {
      await api.patch(`/api/${tipo}/${id}/status`, { status: "Pago" });
      window.dispatchEvent(new Event("avisos:atualizar"));
      toast(tipo === "pix" ? "Pix marcado como pago" : "Boleto marcado como pago", "ok", {
        acao: { rotulo: "Desfazer", executar: async () => { await api.patch(`/api/${tipo}/${id}/status`, { status: "Pendente" }); carregar(); } },
      });
      carregar();
    } catch (erro) {
      alvo.disabled = false;
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  }
}

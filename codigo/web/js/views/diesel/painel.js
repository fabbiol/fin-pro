// Diesel · painel do período: saldo, comprado x abastecido, consumo por máquina e os lançamentos.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";
import { litros, numero, tela } from "./estado.js";
import { formularioAbastecimento, formularioCompra } from "./formularios.js";

const precoBR = (v) => `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 3 })}`;

export function htmlKpis(d) {
  const s = d.saldo;
  const ultima = s.ultima_compra;
  const usado = ultima && ultima.valor ? Math.min(100, (ultima.gasto_desde / ultima.valor) * 100) : 0;
  const baixo = s.valor <= (d.alerta_valor ?? 1000);
  const combustiveis = (d.por_combustivel || []).filter((c) => c.abastecido);
  const precos = (d.precos || []).filter((p) => p.preco);
  const equivalente = s.valor > 0 ? (s.equivalente || []) : [];
  return `<section class="resumo-lista diesel-kpis">
    <div class="resumo-item ${baixo ? "erro" : "ok"} diesel-saldo"><span>Saldo do diesel</span><strong>${brl(s.valor)}</strong>
      ${equivalente.length ? `<ul class="diesel-saldos" title="Quanto o saldo ainda compra, pelo preço do litro">${equivalente.map((e) =>
        `<li><span>≈ ${esc(e.combustivel)}</span><strong>${litros(e.litros)}</strong></li>`).join("")}</ul>` : ""}
      ${ultima ? `<div class="caixa-barra" title="Quanto já foi abastecido desde a última compra"><i style="width:${usado}%"></i></div>
        <small class="sutil">última compra: ${brl(ultima.valor)} em ${dataBR(ultima.data)} · abastecido ${brl(ultima.gasto_desde)}</small>`
        : `<small class="sutil">nenhuma compra lançada</small>`}</div>
    <div class="resumo-item"><span>Comprado no período</span><strong>${brl(d.comprado.valor)}</strong>
      <small class="sutil">${d.comprado.quantidade} compra(s) · ${litros(d.comprado.litros)}</small></div>
    <div class="resumo-item"><span>Abastecido no período</span><strong>${brl(d.abastecido.custo)}</strong>
      <small class="sutil">${d.abastecido.quantidade} abastecimento(s) · ${litros(d.abastecido.litros)} · ${litros(d.abastecido.por_dia)}/dia</small>
      ${combustiveis.length ? `<ul class="diesel-saldos">${combustiveis.map((c) => `<li><span>${esc(c.combustivel)} · ${litros(c.abastecido)}</span>
          <strong>${brl(c.custo)}</strong></li>`).join("")}</ul>` : ""}</div>
    <button type="button" class="resumo-item diesel-precos" data-acao="precos-diesel" title="Preço que pagamos no litro — toque para mudar">
      <span>Preço do litro ${icone("editar", 12)}</span>
      ${precos.length ? `<ul class="diesel-saldos">${precos.map((p) => `<li><span>${esc(p.combustivel)}</span><strong>${precoBR(p.preco)}</strong></li>`).join("")}</ul>`
        : `<strong>—</strong><small class="sutil">toque para informar o preço de cada combustível</small>`}
      <small class="sutil">cada abastecimento desconta litros × preço do seu combustível</small></button>
  </section>`;
}

export function barrasMaquinas(d) {
  const maior = Math.max(...d.por_maquina.map((m) => m.litros), 0);
  return `<article class="card caixa-ranking">
    <h3>${icone("caminhao", 17)} Consumo por máquina</h3>
    ${d.por_maquina.length ? `<ul class="caixa-barras">${d.por_maquina.map((m) => `<li>
        <div class="caixa-barra-topo"><strong title="${esc(m.maquina)}">${esc(m.maquina)}</strong>
          <span>${litros(m.litros)} <small class="sutil">${m.custo ? `${brl(m.custo)} · ` : ""}${String(m.percentual).replace(".", ",")}% · ${m.abastecimentos}×${m.consumo.rotulo ? ` · ${esc(m.consumo.rotulo)}` : ""}</small></span></div>
        <div class="caixa-barra"><i style="width:${maior ? Math.max(3, (m.litros / maior) * 100) : 0}%"></i></div>
      </li>`).join("")}</ul>` : `<p class="sutil">Nenhum abastecimento no período.</p>`}
  </article>`;
}

export function htmlPainel(d) {
  const linhas = [
    ...d.compras.map((c) => ({ ...c, aba: "compras" })),
    ...d.abastecimentos.map((a) => ({ ...a, aba: "abastecimentos" })),
  ].sort((a, b) => `${b.data}${b.hora || ""}${String(b.id).padStart(8, "0")}`.localeCompare(`${a.data}${a.hora || ""}${String(a.id).padStart(8, "0")}`));
  return `${htmlKpis(d)}
    ${d.pendentes ? `<div class="alerta aviso">${icone("telegram", 16)}<span><strong>${d.pendentes}</strong> arquivo(s) do bot
      esperando a máquina ou a conferência. <a href="#/diesel?aba=conferencia">Ver conferência</a></span></div>` : ""}
    <section class="diesel-grade">
      ${barrasMaquinas(d)}
      <article class="card tabela-card">
        <div class="caixa-filtro"><strong>${icone("lista", 15)} Lançamentos</strong>
          <span class="sutil">${linhas.length} em ${esc(d.periodo.rotulo)}</span></div>
        <div class="tabela-wrap">${linhas.length ? tabela(linhas) : `<div class="vazio">
          <div class="vazio-icone">${icone("diesel", 26)}</div><h3>Nada lançado neste período</h3>
          <p>Toque em <strong>Enviar canhoto ou comprovante</strong> (ou arraste o arquivo para esta tela), mande pelo bot do
          diesel, ou lance aqui em cima.</p></div>`}</div>
      </article>
    </section>`;
}

function tabela(linhas) {
  return `<table class="tabela">
    <thead><tr><th>Data</th><th></th><th>Máquina / posto</th><th>Combustível</th><th class="num">Litros</th>
      <th class="num">Horímetro / km</th><th class="num">Valor</th><th>Quem</th><th class="col-acoes"></th></tr></thead>
    <tbody>${linhas.map((r) => {
      const compra = r.aba === "compras";
      return `<tr>
        <td>${dataBR(r.data)}${r.hora ? ` <small class="sutil">${esc(r.hora)}</small>` : ""}</td>
        <td><span class="chip ${compra ? "ok" : "aviso"}">${compra ? "Compra" : "Abastecimento"}</span></td>
        <td>${compra ? esc(r.posto || "Posto") : `<strong>${esc(r.maquina)}</strong>${r.posto ? ` <small class="sutil">${esc(r.posto)}</small>` : ""}`}
          ${r.documento ? `<small class="por-quem">pedido ${esc(r.documento)}</small>` : ""}</td>
        <td><span class="chip">${esc(r.combustivel || "Diesel S10")}</span></td>
        <td class="num ${compra ? "valor-entrada" : "valor-saida"}">${compra ? "+" : "−"} ${litros(r.litros)}</td>
        <td class="num">${compra ? "" : esc(numero(r.medidor))}</td>
        <td class="num">${r.valor ? brl(r.valor) : ""}${r.preco_litro ? `<small class="por-quem">${precoBR(r.preco_litro)}/L</small>` : ""}</td>
        <td>${esc(r.pessoa || "")}${r.lancado_por ? `<small class="por-quem">lançado por ${esc(r.lancado_por)}</small>` : ""}</td>
        <td class="col-acoes">
          ${r.arquivo ? `<a class="btn-icone" href="/${esc(r.arquivo)}" target="_blank" rel="noopener" title="${compra ? "Ver comprovante" : "Ver canhoto"}">${icone("clipe", 15)}</a>` : ""}
          <button class="btn-icone" data-acao="historico-diesel" data-aba="${r.aba}" data-id="${r.id}" title="Histórico">${icone("relogio", 15)}</button>
          <button class="btn-icone" data-acao="editar-diesel" data-aba="${r.aba}" data-id="${r.id}" title="Editar">${icone("editar", 15)}</button>
          <button class="btn-icone perigo" data-acao="cancelar-diesel" data-aba="${r.aba}" data-id="${r.id}" title="Cancelar">${icone("lixeira", 15)}</button>
        </td></tr>`;
    }).join("")}</tbody></table>`;
}

function registro(aba, id) {
  return (aba === "compras" ? tela.dados?.compras : tela.dados?.abastecimentos || [])?.find((r) => r.id === Number(id));
}

export function editar(aba, id) {
  const r = registro(aba, id);
  if (!r) return;
  if (aba === "compras") formularioCompra(r);
  else formularioAbastecimento(r);
}

export async function cancelar(aba, id) {
  const r = registro(aba, id);
  if (!r) return;
  const oque = aba === "compras" ? `a compra de ${litros(r.litros)}` : `o abastecimento de ${litros(r.litros)} em ${r.maquina}`;
  if (!await confirmar({ titulo: "Cancelar lançamento", mensagem: `Cancelar ${oque}? O valor ${aba === "compras" ? "sai do" : "volta para o"} saldo; o registro continua no histórico.`,
                         textoConfirmar: "Cancelar lançamento", perigo: true })) return;
  try {
    await api.post(`/api/diesel/${aba}/${id}/cancelar`, {});
    toast("Lançamento cancelado.", "ok");
    window.dispatchEvent(new Event("diesel:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

export async function historico(aba, id) {
  let eventos = [];
  try {
    eventos = (await api.get(`/api/diesel/${aba}/${id}/historico`)).eventos;
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

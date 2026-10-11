// Diesel · máquinas: cadastro e a média de cada uma (últimos 30 dias).
import { icone } from "../../icons.js";
import { dataBR, esc } from "../../ui.js";
import { litros, tela } from "./estado.js";

const MEDIDOR = { horas: "Horímetro", km: "Km", "": "—" };

export function htmlMaquinas(maquinas) {
  tela.maquinas = maquinas;
  const cabecalho = `<div class="caixa-filtro"><strong>${icone("caminhao", 15)} Máquinas</strong>
    <span class="sutil">Média dos últimos 30 dias de cada máquina</span><span class="espaco"></span>
    <button class="btn btn-sm btn-primario" data-acao="nova-maquina">${icone("mais", 15)} Nova máquina</button></div>`;
  if (!maquinas.length) {
    return `<section class="card tabela-card">${cabecalho}<div class="vazio"><div class="vazio-icone">${icone("caminhao", 26)}</div>
      <h3>Nenhuma máquina cadastrada</h3><p>Cadastre aqui ou pelo bot do diesel (botão “Nova máquina” quando chega um canhoto).
      Com a placa cadastrada, o bot já reconhece o caminhão pelo canhoto.</p></div></section>`;
  }
  return `<section class="card tabela-card">${cabecalho}<div class="tabela-wrap"><table class="tabela">
    <thead><tr><th>Máquina</th><th>Tipo</th><th>Placa / prefixo</th><th>Combustível</th><th>Medidor</th><th class="num">Litros (30 dias)</th>
      <th class="num">Por semana</th><th class="num">Por abastecimento</th><th>Consumo</th><th>Situação</th><th class="col-acoes"></th></tr></thead>
    <tbody>${maquinas.map((m) => {
      const media = m.media || {};
      return `<tr class="${m.status === "Inativa" ? "linha-apagada" : ""}">
        <td><strong>${esc(m.nome)}</strong>${m.observacoes ? `<small class="por-quem">${esc(m.observacoes)}</small>` : ""}</td>
        <td>${esc(m.tipo || "")}</td><td class="mono">${esc(m.placa || "—")}</td><td>${esc(m.combustivel || "—")}</td>
        <td>${MEDIDOR[m.medidor || ""]}</td>
        <td class="num">${litros(media.litros)} <small class="sutil">${media.abastecimentos || 0}×</small></td>
        <td class="num">${litros(media.por_semana)}</td><td class="num">${litros(media.por_abastecimento)}</td>
        <td>${media.consumo?.rotulo ? `<span class="chip info">${esc(media.consumo.rotulo)}</span>`
          : m.medidor ? `<small class="sutil">informe o ${m.medidor === "km" ? "km" : "horímetro"} nos canhotos</small>` : ""}</td>
        <td><span class="chip ${m.status === "Inativa" ? "" : "ok"}">${esc(m.status || "Ativa")}</span></td>
        <td class="col-acoes">
          <button class="btn-icone" data-acao="editar-maquina" data-id="${m.id}" title="Editar">${icone("editar", 15)}</button></td>
      </tr>`;
    }).join("")}</tbody></table></div>
    <p class="sutil" style="padding:0 14px 14px">O consumo (L/h ou km/L) aparece depois de dois abastecimentos com o
      horímetro ou o km informados. Último cadastro: ${dataBR(maquinas.map((m) => m.data_lancamento).sort().pop())}.</p>
  </section>`;
}

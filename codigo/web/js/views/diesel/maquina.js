// Diesel · relatório por máquina: escolha a máquina e veja cada abastecimento dela, com o total por ano, por mês e por
// dia. Clicar num ano mostra os meses dele; num mês, os dias e os abastecimentos; num dia, só os abastecimentos dele.
// A máquina escolhida fica guardada neste aparelho.
import { icone } from "../../icons.js";
import { brl, dataBR, esc, urlArquivo } from "../../ui.js";
import { litros, numero } from "./estado.js";

const CHAVE_MAQUINA = "finpro.diesel.maquina";

/** nome: máquina escolhida · ano/mes/dia: o que está aberto (vazio = o mais recente com abastecimento; dia vazio = o mês todo) */
export const porMaquina = { nome: lerMaquina(), ano: null, mes: "", dia: "" };

function lerMaquina() {
  try {
    return localStorage.getItem(CHAVE_MAQUINA) || "";
  } catch {
    return "";
  }
}

export function escolherMaquina(nome) {
  Object.assign(porMaquina, { nome: nome || "", ano: null, mes: "", dia: "" });
  try {
    localStorage.setItem(CHAVE_MAQUINA, porMaquina.nome);
  } catch { /* sem armazenamento: vale só nesta visita */ }
}

/** Clique num ano, mês ou dia das tabelas (o dia clicado de novo volta para o mês todo). */
export function abrir(acao, valor) {
  if (acao === "maquina-ano") Object.assign(porMaquina, { ano: Number(valor), mes: "", dia: "" });
  else if (acao === "maquina-mes") Object.assign(porMaquina, { mes: valor, dia: "" });
  else if (acao === "maquina-dia") porMaquina.dia = porMaquina.dia === valor ? "" : valor;
}

const precoL = (v) => (v ? `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 3 })}` : "—");
const vezes = (n) => `${n} abastecimento${n === 1 ? "" : "s"}`;

function vazio(ic, titulo, texto) {
  return `<section class="card"><div class="vazio"><div class="vazio-icone">${icone(ic, 26)}</div>
    <h3>${titulo}</h3><p>${texto}</p></div></section>`;
}

function htmlEscolha(d) {
  const nomes = d.maquinas.includes(porMaquina.nome) || !porMaquina.nome ? d.maquinas : [porMaquina.nome, ...d.maquinas];
  return `<section class="card dr-maquina-escolha">
    <label for="diesel-maquina-historico"><strong>${icone("caminhao", 16)} Máquina</strong></label>
    <select class="input" id="diesel-maquina-historico" data-maquina-historico>
      <option value="">Escolha a máquina…</option>
      ${nomes.map((n) => `<option ${n === porMaquina.nome ? "selected" : ""}>${esc(n)}</option>`).join("")}
    </select>
    ${d.maquina?.placa ? `<span class="chip">${esc(d.maquina.placa)}</span>` : ""}
    ${d.maquina?.tipo ? `<span class="sutil">${esc(d.maquina.tipo)}</span>` : ""}
    ${d.maquina?.status === "Inativa" ? `<span class="chip apagado">Inativa</span>` : ""}
  </section>`;
}

function htmlResumo(d) {
  const t = d.total;
  const consumo = t.consumo?.rotulo;
  return `<section class="resumo-lista dr-kpis">
    <div class="card resumo-item"><span>Total abastecido</span><strong>${brl(t.valor)}</strong><small class="sutil">${litros(t.litros)}</small></div>
    <div class="card resumo-item"><span>Abastecimentos</span><strong>${t.abastecimentos}</strong>
      <small class="sutil">média de ${litros(t.por_abastecimento)} cada</small></div>
    <div class="card resumo-item"><span>Primeiro e último</span><strong>${dataBR(t.ultimo)}</strong>
      <small class="sutil">desde ${dataBR(t.primeiro)}</small></div>
    <div class="card resumo-item"><span>Consumo</span><strong>${consumo ? esc(consumo) : "—"}</strong>
      <small class="sutil">${consumo ? "pelo horímetro/km, desde o primeiro" : "precisa do horímetro ou km nos abastecimentos"}</small></div>
  </section>`;
}

/** Uma tabela de totais (ano, mês ou dia); a linha aberta fica destacada e cada linha abre o nível de baixo. */
function tabelaTotais(titulo, ic, linhas, { acao, valor, rotulo, aberto }) {
  return `<article class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone(ic, 15)} ${titulo}</strong></div>
    <div class="tabela-wrap"><table class="tabela dr-tabela">
      <thead><tr><th>Quando</th><th class="num">Litros</th><th class="num">Valor</th><th class="num">Abast.</th></tr></thead>
      <tbody>${linhas.map((g) => {
        const v = valor(g);
        return `<tr class="${String(v) === String(aberto) ? "selecionado" : ""}" data-acao="${acao}" data-valor="${esc(v)}">
          <td><button type="button" class="dr-escolher" data-acao="${acao}" data-valor="${esc(v)}">${rotulo(g)}</button></td>
          <td class="num" data-rotulo="Litros">${litros(g.litros)}</td>
          <td class="num" data-rotulo="Valor"><strong>${brl(g.valor)}</strong></td>
          <td class="num" data-rotulo="Abastecimentos">${g.abastecimentos}</td></tr>`;
      }).join("")}</tbody>
    </table></div>
  </article>`;
}

function htmlAbastecimentos(lista, titulo) {
  return `<section class="card tabela-card">
    <div class="caixa-filtro"><strong>${icone("lista", 15)} ${titulo}</strong><span class="sutil">${vezes(lista.length)}</span></div>
    <div class="tabela-wrap"><table class="tabela dr-tabela dr-abast">
      <thead><tr><th>Data</th><th>Combustível</th><th class="num">Litros</th><th class="num">Preço/L</th><th class="num">Valor</th>
        <th class="num">Horímetro / km</th><th>Trecho</th><th>Pedido / posto</th><th>Quem</th><th></th></tr></thead>
      <tbody>${lista.map((a) => `<tr>
        <td data-rotulo="Data"><strong>${dataBR(a.data)}</strong>${a.hora ? ` <small class="sutil">${esc(a.hora)}</small>` : ""}</td>
        <td data-rotulo="Combustível"><span class="chip">${esc(a.combustivel || "Diesel S10")}</span></td>
        <td class="num" data-rotulo="Litros">${litros(a.litros)}</td><td class="num" data-rotulo="Preço/L">${precoL(a.preco_litro)}</td>
        <td class="num" data-rotulo="Valor"><strong>${brl(a.custo)}</strong>${a.estimado ? `<small class="por-quem">estimado</small>` : ""}</td>
        <td class="num" data-rotulo="Horímetro / km">${a.medidor ? `${esc(numero(a.medidor))} ${a.medidor_tipo === "km" ? "km" : a.medidor_tipo === "horas" ? "h" : ""}` : `<span class="sutil">—</span>`}</td>
        <td data-rotulo="Trecho">${a.trecho ? `<span class="chip info">${esc(a.trecho.rotulo)}</span>
          <small class="por-quem">${esc(numero(a.trecho.rodado))} ${esc(a.trecho.unidade_rodado)} desde ${dataBR(a.trecho.data_anterior)}</small>` : `<span class="sutil">—</span>`}</td>
        <td data-rotulo="Pedido / posto">${a.documento ? `nº ${esc(a.documento)}` : ""}${a.posto ? `<small class="por-quem">${esc(a.posto)}</small>` : ""}</td>
        <td data-rotulo="Quem">${esc(a.pessoa || "")}${a.lancado_por ? `<small class="por-quem">lançado por ${esc(a.lancado_por)}</small>` : ""}</td>
        <td>${a.arquivo ? `<a class="btn-icone" href="${urlArquivo(a.arquivo)}" target="_blank" rel="noopener" title="Ver canhoto">${icone("clipe", 15)}</a>` : ""}</td>
      </tr>`).join("")}</tbody>
    </table></div>
  </section>`;
}

/** O relatório por máquina (``d`` = resposta de /api/diesel/relatorio/maquina); ``topo`` = a escolha do nível. */
export function htmlPorMaquina(d, topo) {
  if (!d.maquinas.length) {
    return topo + vazio("caminhao", "Nenhuma máquina ainda", "Cadastre as máquinas na aba Máquinas ou lance um abastecimento.");
  }
  if (!porMaquina.nome) {
    return topo + htmlEscolha(d) + vazio("caminhao", "Escolha uma máquina", "Escolha acima a máquina para ver cada abastecimento dela, por ano, mês e dia.");
  }
  if (!d.maquina) {
    return topo + htmlEscolha(d) + vazio("alerta", "Máquina não encontrada", "Ela não está no cadastro nem nos abastecimentos. Escolha outra acima.");
  }
  if (!d.abastecimentos.length) {
    return topo + htmlEscolha(d) + vazio("diesel", "Nenhum abastecimento desta máquina", "Quando ela for abastecida, cada abastecimento aparece aqui.");
  }

  // o que está aberto: o ano e o mês escolhidos, ou os mais recentes com abastecimento
  const ano = d.anos.some((g) => g.ano === porMaquina.ano) ? porMaquina.ano : d.anos[0].ano;
  const meses = d.meses.filter((g) => g.ano === ano);
  const mes = meses.find((g) => g.mes === porMaquina.mes) || meses[0];
  const dias = d.dias.filter((g) => g.mes === mes.mes);
  const dia = dias.some((g) => g.data === porMaquina.dia) ? porMaquina.dia : "";
  const lista = d.abastecimentos.filter((a) => (dia ? a.data === dia : a.data.startsWith(mes.mes)));
  const titulo = dia ? `Abastecimentos de ${dataBR(dia)}` : `Abastecimentos de ${esc(mes.rotulo)}`;

  return `${topo}${htmlEscolha(d)}${htmlResumo(d)}
    <section class="dr-tres">
      ${tabelaTotais("Por ano", "calendario", d.anos, { acao: "maquina-ano", valor: (g) => g.ano, rotulo: (g) => g.ano, aberto: ano })}
      ${tabelaTotais(`Por mês · ${ano}`, "calendario", meses, {
        acao: "maquina-mes", valor: (g) => g.mes, rotulo: (g) => esc(g.rotulo.replace(/ de \d{4}$/, "")), aberto: mes.mes })}
      ${tabelaTotais(`Por dia · ${esc(mes.rotulo)}`, "calendario", dias, {
        acao: "maquina-dia", valor: (g) => g.data, rotulo: (g) => `${dataBR(g.data)} <small class="sutil">${esc(g.dia_semana)}</small>`,
        aberto: dia })}
    </section>
    ${dia ? `<p class="sutil dr-nota">Mostrando só ${dataBR(dia)}. Clique no dia de novo para ver o mês todo.</p>` : ""}
    ${htmlAbastecimentos(lista, titulo)}`;
}

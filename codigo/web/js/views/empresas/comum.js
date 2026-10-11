// Empresas e fechamentos · funções usadas pelos vários módulos da tela.
import { api } from "../../api.js";
import { esc, mensagemErro, toast } from "../../ui.js";
import { tela } from "./estado.js";

export const SITUACOES = {
  "Em aberto": "", "Em cheque": "info", Parcial: "aviso", Recebido: "ok", Cancelado: "apagado",
  "Em carteira": "", Depositado: "info", Compensado: "ok", Devolvido: "erro", Confirmado: "ok", Ativa: "ok",
  Inativa: "apagado",
};

export function selo(situacao) {
  return `<span class="chip ${SITUACOES[situacao] ?? ""}">${esc(situacao || "—")}</span>`;
}

export function opcoesEmpresa(selecionada = "", vazio = "Escolha a empresa") {
  const lista = tela.dados?.cadastro || [];
  return `<option value="">${esc(vazio)}</option>` + lista.map((e) =>
    `<option value="${esc(e.nome)}" ${e.nome === selecionada ? "selected" : ""}>${esc(e.nome)}</option>`).join("");
}

export function opcoes(lista, selecionado = "") {
  return lista.map((v) => `<option value="${esc(v)}" ${v === selecionado ? "selected" : ""}>${esc(v)}</option>`).join("");
}

/** Competências (fechamentos) para escolher: a atual e as 11 anteriores. */
export function opcoesCompetencia(selecionada = "") {
  const hoje = new Date();
  const valores = [];
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() - i + 1, 1);
    valores.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
  }
  if (selecionada && !valores.includes(selecionada)) valores.unshift(selecionada);  // fechamento antigo não some
  return valores.map((valor) =>
    `<option value="${valor}" ${valor === selecionada ? "selected" : ""}>${tituloCompetencia(valor)}</option>`).join("");
}

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
  "novembro", "dezembro"];

export function tituloCompetencia(competencia) {
  if (!competencia) return "";
  const [ano, mes] = competencia.split("-");
  return `${MESES[Number(mes) - 1]} de ${ano}`;
}

export function numero(valor) {
  if (valor === null || valor === undefined || valor === "") return "";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(Number(valor));
}

/** Chama a API e mostra o erro em toast. Devolve ``undefined`` quando dá errado (exclusões devolvem null). */
export async function tentar(fn, mensagemOk = "") {
  try {
    const resultado = await fn();
    if (mensagemOk) toast(mensagemOk, "ok");
    return resultado === undefined ? null : resultado;
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return undefined;
  }
}

/** Deu certo? (uma exclusão bem-sucedida devolve null, então não dá para testar só a verdade do valor) */
export const deuCerto = (resultado) => resultado !== undefined;

export async function carregarDados() {
  const mes = tela.competencia ? `?competencia=${tela.competencia}` : "";
  tela.dados = await api.get(`/api/empresas${mes}`);
  tela.competencia = tela.competencia || tela.dados.empresas[0]?.competencia || "";
  return tela.dados;
}

export const vazio = (icone, titulo, texto = "") =>
  `<div class="vazio"><div class="vazio-icone">${icone}</div><h3>${esc(titulo)}</h3>${texto ? `<p>${texto}</p>` : ""}</div>`;

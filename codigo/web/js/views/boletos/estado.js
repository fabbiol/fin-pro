// Boletos lançados · estado compartilhado pelos módulos da tela (filtros, seleção e modo de exibição).
export const filtros = {
  q: "", situacao: "", centro: "", campo_data: "vencimento", de: "", ate: "",
  ordenar: "vencimento", direcao: "asc", pagina: 1, por_pagina: 25,
};
export const CHIPS = [
  ["", "Todos"],
  ["pendente", "Pendentes"],
  ["a_vencer,vence_hoje", "A vencer"],
  ["vencido", "Vencidos"],
  ["pago", "Pagos"],
  ["cancelado", "Cancelados"],
];
export const COLUNAS = [
  ["vencimento", "Vencimento"],
  ["beneficiario", "Beneficiário"],
  ["valor", "Valor", "num"],
  [null, "Linha digitável"],
  ["data_lancamento", "Lançado em"],
];
export const NOMES_MES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
  "novembro", "dezembro"];
export const DIAS_CAL = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
export const selecionados = new Set();

function lerModo() {
  try { return localStorage.getItem("boletos_modo") === "calendario" ? "calendario" : "lista"; } catch { return "lista"; }
}

export function inicioDoMes(data) {
  return new Date(data.getFullYear(), data.getMonth(), 1);
}

/** raiz: elemento da tela · ultimo: última resposta da lista · modo: lista ou calendário */
export const tela = { raiz: null, ultimo: null, itensCalendario: [], requisicao: 0, modo: lerModo(), mesCalendario: inicioDoMes(new Date()) };

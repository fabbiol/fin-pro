// Caixa · estado compartilhado pelos módulos da tela.
export const ABAS = [
  ["movimento", "caixa", "Movimento"],
  ["relatorios", "grafico", "Relatórios"],
  ["conferencia", "scan", "Conferência"],
  ["bot", "telegram", "Bot do caixa"],
];

export const PERIODOS = [["dia", "Dia"], ["semana", "Semana"], ["mes", "Mês"], ["ano", "Ano"]];

/** raiz: elemento da tela · periodo/data: o que está sendo visto · dados: resposta de /api/caixa */
export const tela = {
  raiz: null,
  aba: "movimento",
  periodo: "mes",
  data: "",
  dados: null,
  filtro: "",
  pendentes: 0,
};

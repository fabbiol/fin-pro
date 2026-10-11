// Diesel · estado compartilhado pelos módulos da tela.
export const ABAS = [
  ["painel", "diesel", "Painel"],
  ["maquinas", "caminhao", "Máquinas"],
  ["relatorios", "grafico", "Relatórios"],
  ["conferencia", "scan", "Conferência"],
  ["bot", "telegram", "Bot do diesel"],
];

export const PERIODOS = [["semana", "Semana"], ["quinzena", "Quinzena"], ["mes", "Mês"], ["ano", "Ano"]];
export const TIPOS_MAQUINA = ["Caminhão", "Máquina", "Veículo", "Gerador", "Outro"];
export const COMBUSTIVEIS = ["Diesel S10", "Diesel comum", "Gasolina", "Etanol", "Arla 32"];
export const MEDIDORES = [["horas", "Horímetro (horas)"], ["km", "Hodômetro (km)"], ["", "Sem medidor"]];

/** raiz: elemento da tela · periodo/data: o que está sendo visto · dados: resposta de /api/diesel */
export const tela = {
  raiz: null,
  aba: "painel",
  periodo: "semana",
  data: "",
  dados: null,
  maquinas: [],
  precos: [],
  conferencia: [],
};

const formatoLitros = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
export const litros = (v) => (v === null || v === undefined || v === "" ? "—" : `${formatoLitros.format(Number(v))} L`);
export const numero = (v) => (v === null || v === undefined || v === "" ? "" : formatoLitros.format(Number(v)));

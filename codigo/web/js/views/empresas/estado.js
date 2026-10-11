// Empresas e fechamentos · estado compartilhado pelos módulos da tela.
export const ABAS = [
  ["fechamentos", "grafico", "Fechamentos"],
  ["notas", "lista", "Notas fiscais"],
  ["cheques", "cartao", "Cheques"],
  ["recebimentos", "pix", "Recebimentos"],
  ["conferencia", "scan", "Conferência"],
  ["bot", "telegram", "Bot de notas"],
];

export const STATUS_NOTA = ["Em aberto", "Em cheque", "Parcial", "Recebido", "Cancelado"];
export const STATUS_CHEQUE = ["Em carteira", "Depositado", "Compensado", "Devolvido", "Cancelado"];
export const FORMAS = ["Pix", "TED", "Depósito", "Cheque", "Dinheiro", "Outro"];
export const UNIDADES = ["M³", "TON", "UN", "KG", "L", "H", "SC", "PC"];

/** raiz: elemento da tela · dados: última resposta de /api/empresas · empresa: empresa escolhida no fechamento */
export const tela = {
  raiz: null,
  aba: "fechamentos",
  dados: null,
  empresa: null,
  competencia: "",
  fechamento: null,
  pendentes: 0,
  empresaId: 0,
  filtroEmpresa: "",
  filtroStatus: "",
};

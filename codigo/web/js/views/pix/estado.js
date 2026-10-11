// Pagamentos Pix · estado compartilhado pelos módulos da tela.
export const CHIPS = [["", "Todos"], ["pendente", "Pendentes"], ["vencido", "Atrasados"], ["pago", "Pagos"], ["cancelado", "Cancelados"]];
export const COLUNAS = [["vencimento", "Data prevista"], ["recebedor", "Recebedor"], [null, "Chave Pix"], ["valor", "Valor", "num"],
  ["data_lancamento", "Lançado em"]];
export const filtros = { q: "", situacao: "", centro: "", ordenar: "vencimento", direcao: "asc", pagina: 1, por_pagina: 25 };
/** raiz: elemento da tela · ultimo: última resposta da lista · formularioPrincipal: formulário da tela */
export const tela = { raiz: null, ultimo: null, requisicao: 0, formularioPrincipal: null, codigoPendente: null, arquivosPendentes: null };

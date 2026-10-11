// Ler boletos · estado compartilhado pelos módulos da tela (fila de arquivos e referências da tela aberta).
export const fila = [];
export const MAX_PARALELO = 2;
export const EXTENSOES = /\.(pdf|jpe?g|png|webp|heic|heif|bmp|tiff?|gif)$/i;
export const ORIGENS = { email: ["email", "E-mail"], telegram: ["telegram", "Telegram"] };
/** raiz: elemento da tela · ativos: leituras em andamento · caixa: recebidos por e-mail/Telegram */
export const tela = { raiz: null, ativos: 0, cronometro: null, centros: [], caixa: null, atualizadorCaixa: null };
/** Recebidos que estão abertos na fila de revisão (saem da lista da caixa enquanto estão sendo revisados). */
export const abertosDaCaixa = () => new Set(fila.filter((i) => i.recebido && !i.removido).map((i) => i.recebido));

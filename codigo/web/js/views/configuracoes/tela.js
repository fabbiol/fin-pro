// Configurações · estado compartilhado pelos cartões da tela aberta e o que todo cartão usa para buscar e se redesenhar.
import { api } from "../../api.js";
import { ehAdministrador, estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { esc, mensagemErro } from "../../ui.js";

/**
 * raiz: elemento da tela (null fora dela) · aba: aba aberta · secoes: módulos dos cartões da aba aberta
 * dados/erros: o que carregar() de cada seção devolveu ou lançou, pela chave da seção
 * admin: resposta de GET /api/admin (carregarAdmin) · vez: muda a cada montagem/recarga (descarta respostas atrasadas)
 */
export const tela = { raiz: null, aba: "geral", secoes: [], dados: {}, erros: {}, admin: null, vez: 0 };

const pedidos = new Map();

/** GET compartilhado: pedidos iguais feitos ao mesmo tempo (ex.: vários cartões querendo /api/admin) viram uma só chamada. */
export function buscar(caminho) {
  if (!pedidos.has(caminho)) {
    pedidos.set(caminho, api.get(caminho).finally(() => pedidos.delete(caminho)));
  }
  return pedidos.get(caminho);
}

/** Senha de administrador (GET /api/admin, sempre 200). Guarda em tela.admin; nunca lança. */
export async function carregarAdmin() {
  try {
    tela.admin = await buscar("/api/admin");
  } catch {
    tela.admin = null;
  }
  return tela.admin;
}

/** A área restrita está liberada neste aparelho? (senha de administrador digitada ou usuário com perfil administrador) */
export const liberado = () => Boolean(tela.admin?.autorizado) || ehAdministrador();

/** Atualiza estado.acesso (GET /api/acesso/estado, sempre 200). Nunca lança. */
export async function carregarAcesso() {
  try {
    estado.acesso = await buscar("/api/acesso/estado");
  } catch { /* fica o último estado conhecido */ }
  return estado.acesso;
}

/** Alerta de erro padrão dentro de um cartão (use no html(dados, erro) quando erro vier preenchido). */
export const alertaErro = (erro) => `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(mensagemErro(erro))}</div></div>`;

const secaoAberta = (chave) => tela.secoes.find((s) => s.chave === chave);

/** Markup de uma seção com os dados/erro guardados (se html() falhar, mostra um cartão de erro em vez de quebrar a aba). */
export function htmlSecao(secao) {
  try {
    return secao.html(tela.dados[secao.chave], tela.erros[secao.chave]);
  } catch (erro) {
    console.error(erro); // defeito no html() da seção: aparece no console (e nos testes) sem derrubar a aba
    return `<article class="card" id="cfg-${esc(secao.chave)}">${alertaErro(erro)}</article>`;
  }
}

/**
 * Redesenha os cartões de uma seção no lugar (pelo id de cada elemento de topo que html() devolve).
 * Com `dados`, guarda-os antes (e limpa o erro). Não faz nada se a seção não estiver na aba aberta.
 */
export function redesenhar(chave, dados) {
  const secao = secaoAberta(chave);
  if (!secao) return;
  if (dados !== undefined) {
    tela.dados[chave] = dados;
    delete tela.erros[chave];
  }
  if (!tela.raiz) return;
  const molde = document.createElement("template");
  molde.innerHTML = htmlSecao(secao);
  for (const novo of [...molde.content.children]) {
    const antigo = novo.id && tela.raiz.querySelector(`#${CSS.escape(novo.id)}`);
    if (antigo) antigo.replaceWith(novo);
  }
}

/** Busca de novo os dados de uma seção (carregar()) e redesenha os cartões dela. Nunca lança. */
export async function atualizar(chave) {
  const secao = secaoAberta(chave);
  if (!secao?.carregar) return redesenhar(chave);
  const vez = tela.vez;
  try {
    const dados = await secao.carregar();
    if (vez !== tela.vez) return undefined;
    tela.dados[chave] = dados;
    delete tela.erros[chave];
  } catch (erro) {
    if (vez !== tela.vez) return undefined;
    tela.erros[chave] = erro;
  }
  return redesenhar(chave);
}

/** Recarrega a aba inteira (todos os cartões). Use quando uma ação muda mais de um cartão (ex.: liberar a área restrita). */
export const recarregar = () => window.dispatchEvent(new Event("config:atualizar"));

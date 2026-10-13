// Configurações · cliques, alterações e formulários da tela de Configurações.
// Um ouvinte de cada tipo na raiz da tela: o data-acao do elemento escolhe a função nos mapas exportados pelas seções
// da aba aberta (acoes / alteracoes / formularios). Enquanto a função roda, o elemento fica desligado.
import { bloquearAdmin, pedirSenhaAdmin } from "../../admin.js";
import { mensagemErro, toast } from "../../ui.js";
import { carregarAdmin, recarregar, tela } from "./tela.js";

const CODIGOS_ADMIN = ["admin_necessario", "admin_sem_senha", "sem_permissao"];

/**
 * Faz uma chamada protegida pela senha de administrador. Se a área restrita expirou (admin_necessario), pede a senha
 * e repete uma vez. Se a pessoa cancelar (ou o erro for outro), lança o erro para quem chamou.
 */
export async function comAdmin(executar, descricao = "Digite a senha de administrador para continuar.") {
  try {
    return await executar();
  } catch (erro) {
    if (erro?.codigo !== "admin_necessario") throw erro;
    const liberou = await pedirSenhaAdmin({
      descricao: `A área restrita foi bloqueada (tempo esgotado ou senha trocada). ${descricao}`,
    });
    if (!liberou) throw erro;
    await carregarAdmin();
    return executar();
  }
}

/** Mostra o erro de uma ação. Área restrita (admin/permissão) vira aviso e a aba é redesenhada para mostrar o cadeado. */
export function avisarErro(erro) {
  if (CODIGOS_ADMIN.includes(erro?.codigo)) {
    toast(mensagemErro(erro), "aviso", { duracao: 7000 });
    recarregar();
    return;
  }
  toast(mensagemErro(erro), "erro", { duracao: 6000 });
}

// Ações comuns a todas as abas (botões dos cartões bloqueados pela senha de administrador).
const NUCLEO = {
  acoes: {
    /** <button data-acao="admin-desbloquear" data-descricao="…">: pede a senha e, liberada, redesenha a aba. */
    "admin-desbloquear": async (alvo) => {
      const liberou = await pedirSenhaAdmin({ descricao: alvo.dataset.descricao || undefined });
      if (liberou) recarregar();
    },
    /** <button data-acao="admin-bloquear">: fecha a área restrita neste aparelho. */
    "admin-bloquear": async () => {
      await bloquearAdmin();
      toast("Área restrita bloqueada neste aparelho.", "info");
      recarregar();
    },
  },
};

function acharFuncao(mapa, nome) {
  if (!nome) return null;
  for (const secao of [NUCLEO, ...tela.secoes]) {
    const funcao = secao[mapa]?.[nome];
    if (funcao) return funcao;
  }
  return null;
}

const emAndamento = new WeakSet();

/** Desliga o elemento (e mostra "data-espera" com um spinner, se houver) e devolve como religar. */
function ocupar(el, espera) {
  emAndamento.add(el);
  const original = el.innerHTML;
  el.disabled = true;
  if (espera && el.tagName === "BUTTON") el.innerHTML = `<span class="spinner"></span> ${espera}`;
  return () => {
    emAndamento.delete(el);
    if (!el.isConnected) return; // o cartão foi redesenhado: o elemento novo já nasce ligado
    el.disabled = false;
    if (espera && el.tagName === "BUTTON") el.innerHTML = original;
  };
}

async function rodar(funcao, elementos, args, aoFalhar) {
  const religar = elementos.map(([el, espera]) => ocupar(el, espera));
  try {
    await funcao(...args);
  } catch (erro) {
    aoFalhar?.();
    avisarErro(erro);
  } finally {
    religar.forEach((f) => f());
  }
}

export async function aoClicar(e) {
  const alvo = e.target.closest("[data-acao]");
  if (!alvo || !tela.raiz?.contains(alvo) || emAndamento.has(alvo)) return;
  const funcao = acharFuncao("acoes", alvo.dataset.acao);
  if (!funcao) return;
  if (alvo.tagName === "A") e.preventDefault();
  await rodar(funcao, [[alvo, alvo.dataset.espera]], [alvo, e]);
}

export async function aoAlterar(e) {
  const campo = e.target;
  if (!campo.matches?.("input[data-acao], select[data-acao], textarea[data-acao]") || emAndamento.has(campo)) return;
  const funcao = acharFuncao("alteracoes", campo.dataset.acao);
  if (!funcao) return;
  const marcado = campo.checked;
  // Se a função lançar, a chave volta para onde estava (o servidor não aceitou a mudança).
  const desfazer = campo.type === "checkbox" ? () => { if (campo.isConnected) campo.checked = !marcado; } : null;
  await rodar(funcao, [[campo]], [campo, e], desfazer);
}

export async function aoEnviar(e) {
  const form = e.target.closest("form");
  if (!form || !tela.raiz?.contains(form)) return;
  e.preventDefault(); // nenhum formulário desta tela recarrega a página
  const funcao = acharFuncao("formularios", form.dataset.acao);
  if (!funcao || emAndamento.has(form)) return;
  const botoes = [...form.querySelectorAll("button[type=submit]")].map((b) => [b, b === e.submitter ? b.dataset.espera : null]);
  emAndamento.add(form);
  try {
    await rodar(funcao, botoes, [form, e]);
  } finally {
    emAndamento.delete(form);
  }
}

// Configurações · Importação de boletos e senha de administrador (área restrita).
// A senha de administrador só é criada e trocada no computador onde o Fin Pro está instalado (o servidor responde 403
// "somente_local" de fora). Com a área liberada (senha digitada ou usuário com perfil administrador): importar boletos,
// baixar a planilha modelo e bloquear. Também exporta o aviso de "área restrita" usado pelos outros cartões.
import { api } from "../../api.js";
import { ehAdministrador, estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { esc, mensagemErro, toast } from "../../ui.js";
import { alertaErro, carregarAcesso, carregarAdmin, liberado, recarregar, tela } from "./tela.js";

export const chave = "importacao";

const MINIMO_SENHA = 6;

/** GET /api/admin e /api/acesso/estado (sempre 200). Devolve o estado da senha de administrador (também em tela.admin). */
export async function carregar() {
  const [admin] = await Promise.all([carregarAdmin(), carregarAcesso()]); // antes de qualquer await: pedidos compartilhados
  return admin;
}

// ------------------------------------------------------------------ quem pode mexer nas áreas restritas

/** Entrou com um usuário que não é administrador: o servidor responde "sem_permissao" mesmo com a senha digitada. */
export const usuarioComum = () => Boolean(estado.acesso?.usuario) && !ehAdministrador();

/** Pode mudar configurações restritas (backup, e-mail/Telegram, importação) neste aparelho agora? */
export const podeAdministrar = () => !usuarioComum() && liberado();

const alerta = (tipo, texto) => `<div class="alerta ${tipo}">${icone(tipo === "info" ? "info" : "alerta", 16)}<div>${texto}</div></div>`;

/**
 * Aviso de área restrita para os cartões de configuração, quando podeAdministrar() é falso.
 * `oque`: o que fica bloqueado (ex.: "a pasta, o horário e os pacotes do backup") · `descricao`: texto da janela da senha.
 */
export function htmlTravaAdmin(oque, descricao) {
  const admin = tela.admin;
  if (usuarioComum()) {
    return alerta("info", `Só quem tem o perfil de administrador pode mudar ${esc(oque)}. Peça ao administrador do Fin Pro.`);
  }
  if (admin && !admin.senha_definida) {
    if (!admin.local) return alerta("info", `Para mudar ${esc(oque)}, entre com um usuário administrador.`);
    return `${alerta("aviso", `Área restrita: para mudar ${esc(oque)}, crie primeiro a senha de administrador.`)}
      <div class="linha-botoes"><a class="btn" href="#/config?aba=usuarios">${icone("escudo", 16)} Criar a senha de administrador</a></div>`;
  }
  const espera = Number(admin?.bloqueado_segundos) || 0;
  return `${alerta("aviso", `Área restrita: digite a senha de administrador para mudar ${esc(oque)}.`)}
    <div class="linha-botoes"><button class="btn" type="button" data-acao="admin-desbloquear" data-descricao="${esc(descricao)}"
      ${espera > 0 ? "disabled" : ""}>${icone("escudo", 16)} Digitar a senha</button></div>
    ${espera > 0 ? `<p class="sutil">Muitas senhas erradas. Tente de novo em ${Math.max(1, Math.round(espera / 60))} minuto(s).</p>` : ""}`;
}

// ------------------------------------------------------------------ desenho

const campoSenha = (nome, rotulo, autocomplete = "new-password") => `<label class="imp-grupo"><span class="imp-rotulo">${rotulo}</span>
  <input type="password" class="input" name="${nome}" minlength="${MINIMO_SENHA}" maxlength="200" autocomplete="${autocomplete}" required></label>`;

function htmlCriarSenha() {
  return `<form class="admin-form" data-acao="importacao-criar-senha" autocomplete="off" novalidate style="max-width:440px">
      ${campoSenha("senha", "Nova senha de administrador")}
      ${campoSenha("confirmacao", "Repita a senha")}
      <p class="admin-erro" data-admin-erro role="alert"></p>
      <div class="linha-botoes"><button class="btn btn-primario" type="submit" data-espera="Criando…">${icone("escudo", 16)} Criar senha</button></div>
    </form>
    <p class="sutil">Mínimo de ${MINIMO_SENHA} caracteres. Esqueceu? Feche o sistema, apague dados\\admin.json e crie outra.</p>`;
}

function htmlTrocarSenha() {
  return `<details class="rede-ajuda"><summary>Trocar a senha de administrador</summary>
    <form class="admin-form" data-acao="importacao-trocar-senha" autocomplete="off" novalidate style="max-width:440px;margin-top:12px">
      <label class="imp-grupo"><span class="imp-rotulo">Senha atual</span>
        <input type="password" class="input" name="senha_atual" maxlength="200" autocomplete="current-password" required></label>
      ${campoSenha("senha", "Nova senha")}
      ${campoSenha("confirmacao", "Repita a nova senha")}
      <p class="admin-erro" data-admin-erro role="alert"></p>
      <div class="linha-botoes"><button class="btn btn-primario" type="submit" data-espera="Trocando…">${icone("chave", 16)} Trocar senha</button></div>
      <p class="sutil">Trocar a senha bloqueia os outros aparelhos que estavam liberados.</p>
    </form>
  </details>`;
}

function htmlLiberado(admin) {
  const pelaSenha = Boolean(admin?.autorizado);
  const local = Boolean(admin?.local);
  const minutos = Number(admin?.minutos_sessao) || 20;
  return `<p class="sutil">${pelaSenha
      ? `Área liberada neste aparelho (fecha sozinha após ${minutos} minutos sem uso).`
      : "Área liberada para o seu usuário (perfil administrador)."}</p>
    <div class="linha-botoes">
      <a class="btn btn-primario" href="#/importar">${icone("upload", 16)} Importar boletos</a>
      <a class="btn" href="/api/importacao/modelo.xlsx" download>${icone("download", 16)} Baixar planilha modelo</a>
      ${pelaSenha ? `<button class="btn" type="button" data-acao="admin-bloquear">${icone("escudo", 16)} Bloquear</button>` : ""}
    </div>
    ${local && admin?.senha_definida ? htmlTrocarSenha() : ""}
    ${local && admin && !admin.senha_definida ? `<details class="rede-ajuda"><summary>Criar a senha de administrador</summary>
      <div style="margin-top:12px">${htmlCriarSenha()}</div></details>` : ""}`;
}

function htmlBloqueado(admin) {
  if (usuarioComum()) {
    return alerta("info", "Só quem tem o perfil de administrador importa boletos de outro sistema. Peça ao administrador do Fin Pro.");
  }
  if (admin && !admin.senha_definida) {
    if (admin.local) return htmlCriarSenha();
    return alerta("aviso", "A senha de administrador só pode ser criada no computador onde o Fin Pro está instalado. Quem tem o perfil de administrador pode entrar com o próprio usuário.");
  }
  const espera = Number(admin?.bloqueado_segundos) || 0;
  return `${espera > 0 ? alerta("aviso", `Muitas senhas erradas. Tente de novo em ${Math.max(1, Math.round(espera / 60))} minuto(s).`) : ""}
    <div class="linha-botoes"><button class="btn btn-primario" type="button" data-acao="admin-desbloquear"
      data-descricao="Digite a senha de administrador para usar a importação de boletos." ${espera > 0 ? "disabled" : ""}>
      ${icone("escudo", 16)} Digitar a senha</button></div>`;
}

export function html(admin, erro) {
  const aberto = admin !== undefined && !erro && !usuarioComum() && liberado();
  let corpo = `<div class="esqueleto" style="height:60px"></div>`;
  if (erro) corpo = alertaErro(erro);
  else if (aberto) corpo = htmlLiberado(admin);
  else if (admin !== undefined) corpo = htmlBloqueado(admin);
  const chip = admin === undefined || erro ? ""
    : aberto ? ` <span class="chip ok">Liberado</span>` : ` <span class="chip aviso">Área restrita</span>`;
  return `<article class="card col-inteira" id="cfg-importacao">
    <h3>${icone("planilha", 18)} Importar boletos de outro sistema${chip}</h3>
    <p class="sutil">Traga as contas a pagar exportadas do seu sistema financeiro ou ERP (Excel, CSV ou TXT). Área restrita: só com a senha de administrador.</p>
    ${corpo}
  </article>`;
}

// ------------------------------------------------------------------ senha de administrador

/** Confere os campos antes de enviar; devolve a mensagem de erro (ou "") e põe o foco no campo certo. */
function conferirSenhas(form) {
  const { senha, confirmacao, senha_atual: atual } = form.elements;
  if (atual && !atual.value) {
    atual.focus();
    return "Digite a senha de administrador atual.";
  }
  if (senha.value.length < MINIMO_SENHA) {
    senha.focus();
    return `A senha de administrador precisa ter pelo menos ${MINIMO_SENHA} caracteres.`;
  }
  if (senha.value !== confirmacao.value) {
    confirmacao.focus();
    return "As duas senhas não são iguais.";
  }
  return "";
}

/** Envia a senha (criar ou trocar). Erros do servidor aparecem no próprio formulário; sucesso redesenha a aba. */
async function enviarSenha(form, trocar) {
  const erro = form.querySelector("[data-admin-erro]");
  erro.textContent = conferirSenhas(form);
  if (erro.textContent) return;
  const { senha, confirmacao, senha_atual: atual } = form.elements;
  const corpo = { senha: senha.value, confirmacao: confirmacao.value };
  if (trocar) corpo.senha_atual = atual.value;
  try {
    tela.admin = await api.post("/api/admin/senha", corpo);
  } catch (falha) {
    erro.textContent = mensagemErro(falha);
    if (falha?.codigo === "senha_incorreta" && atual) {
      atual.value = "";
      atual.focus();
    } else if (falha?.codigo === "senhas_diferentes") {
      confirmacao.focus();
    } else {
      senha.focus();
    }
    return;
  }
  toast(trocar
    ? "Senha de administrador trocada. Os outros aparelhos que estavam liberados foram bloqueados."
    : "Senha de administrador criada. A área restrita está liberada neste aparelho.", "ok", { duracao: 6000 });
  recarregar(); // a sessão já foi aberta (cookie): os cartões de usuários, backup e e-mail mudam também
}

export const formularios = {
  "importacao-criar-senha": (form) => enviarSenha(form, false),
  "importacao-trocar-senha": (form) => enviarSenha(form, true),
};

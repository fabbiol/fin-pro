// Configurações · Usuários do escritório (área restrita): cadastro, perfil e permissões, senhas e as opções de login.
// Só o administrador mexe aqui: quem entrou com um usuário de perfil administrador, ou (sem ninguém conectado) quem digitou
// a senha de administrador. GET /api/usuarios só é chamado com a área liberada (senão o servidor responde 403).
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { abrirModal, confirmar, dataHoraBR, esc, mensagemErro, pedirTexto, toast } from "../../ui.js";
import { avisarErro, comAdmin } from "./eventos.js";
import { alertaErro, buscar, carregarAcesso, carregarAdmin, liberado, recarregar, redesenhar, tela } from "./tela.js";

export const chave = "usuarios";

const CODIGOS_ADMIN = ["admin_necessario", "admin_sem_senha", "sem_permissao"];
const MOTIVO_DO_CODIGO = { admin_necessario: "bloqueado", admin_sem_senha: "sem_senha", sem_permissao: "sem_permissao" };
const DESCRICAO = "Digite a senha de administrador para cadastrar e gerenciar os usuários.";

/** Rótulos curtos das permissões (os mesmos da tabela do README); os longos vêm do servidor, para a janela de permissões. */
const CURTOS = {
  lancar: "Lançar", pagar: "Dar baixa", editar: "Editar/excluir", gastos: "Gastos", empresas: "Empresas",
  caixa: "Caixa", diesel: "Diesel", notificacoes: "Avisos", config: "Configurações",
};

/**
 * { admin, lista } com a área liberada, ou { admin, motivo } quando não dá para listar:
 * sem_permissao (entrou com um usuário comum) · sem_senha (falta criar a senha de administrador) · bloqueado (falta digitá-la).
 */
export async function carregar() {
  const pedidos = [carregarAdmin(), carregarAcesso()]; // antes de qualquer await: os cartões irmãos usam os mesmos pedidos
  const [admin, acesso] = await Promise.all(pedidos);
  if (acesso?.usuario && !acesso.administrador) return { admin, motivo: "sem_permissao" };
  if (acesso?.administrador || admin?.autorizado) {
    try {
      return { admin, lista: await buscar("/api/usuarios") };
    } catch (erro) {
      if (MOTIVO_DO_CODIGO[erro?.codigo]) return { admin, motivo: MOTIVO_DO_CODIGO[erro.codigo] };
      throw erro;
    }
  }
  return { admin, motivo: admin?.senha_definida ? "bloqueado" : "sem_senha" };
}

// ------------------------------------------------------------------ desenho

const alerta = (tipo, texto, ic = tipo === "info" ? "info" : "alerta") => `<div class="alerta ${tipo}">${icone(ic, 16)}<div>${texto}</div></div>`;

function htmlBloqueado({ admin, motivo }) {
  const local = Boolean(admin?.local ?? estado.acesso?.local);
  if (motivo === "sem_permissao") {
    return alerta("info", "Só quem tem o perfil de administrador cadastra usuários e muda permissões. Peça ao administrador do Fin Pro.");
  }
  if (motivo === "sem_senha") {
    if (!local) {
      return alerta("info", "A senha de administrador ainda não foi criada. Crie-a no computador onde o Fin Pro está instalado, em Configurações → Usuários e acesso.");
    }
    return `${alerta("aviso", "Para cadastrar os usuários, crie primeiro a senha de administrador.")}
      <div class="linha-botoes"><button class="btn btn-primario" type="button" data-acao="usuarios-criar-senha">${icone("escudo", 16)} Criar senha de administrador</button></div>`;
  }
  const espera = Number(admin?.bloqueado_segundos) || 0;
  return `${alerta("aviso", "Área restrita: digite a senha de administrador para cadastrar e gerenciar os usuários. Quem tem o perfil de administrador também pode entrar com o próprio usuário.")}
    <div class="linha-botoes"><button class="btn" type="button" data-acao="admin-desbloquear" data-descricao="${esc(DESCRICAO)}"
      ${espera > 0 ? "disabled" : ""}>${icone("escudo", 16)} Digitar a senha</button></div>
    ${espera > 0 ? `<p class="sutil">Muitas senhas erradas. Tente de novo em ${Math.max(1, Math.round(espera / 60))} minuto(s).</p>` : ""}`;
}

const ehEu = (u) => Boolean(estado.acesso?.usuario?.login) && u.login === estado.acesso.usuario.login;

function chipsPermissoes(u, catalogo) {
  if (u.perfil === "administrador") return `<span class="chip ok">Tudo</span>`;
  const marcadas = new Set(u.permissoes || []);
  const chips = catalogo.filter((p) => marcadas.has(p.chave)).map((p) => `<span class="chip" title="${esc(p.rotulo)}">${esc(CURTOS[p.chave] || p.rotulo)}</span>`);
  return chips.length ? chips.join("") : `<span class="sutil">Só consulta (painel, boletos e Pix)</span>`;
}

const botao = (acao, id, ic, titulo, { classe = "btn-icone", desligado = false } = {}) =>
  `<button class="${classe}" type="button" data-acao="usuarios-${acao}" data-id="${esc(id)}" title="${esc(titulo)}" aria-label="${esc(titulo)}"
    ${desligado ? "disabled" : ""}>${icone(ic, 16)}</button>`;

function linhaUsuario(u, lista, administradoresAtivos) {
  const eu = ehEu(u);
  const admin = u.perfil === "administrador";
  const unico = u.ativo && admin && administradoresAtivos <= 1;
  const acoes = [
    botao("permissoes", u.id, "escudo", "Perfil e permissões"),
    botao("renomear", u.id, "editar", "Mudar o nome"),
    botao("senha", u.id, "chave", eu ? "Trocar a minha senha" : "Trocar a senha"),
  ];
  if (!eu) {
    acoes.push(u.ativo
      ? botao("desativar", u.id, "ligar", unico ? "É o único administrador" : "Desativar", { desligado: unico })
      : botao("reativar", u.id, "ligar", "Reativar"));
    acoes.push(botao("excluir", u.id, "lixeira", unico ? "É o único administrador" : "Excluir", { classe: "btn-icone perigo", desligado: unico }));
  }
  return `<tr class="${u.ativo ? "" : "usuario-inativo"}" data-id="${esc(u.id)}">
    <td data-rotulo="Pessoa"><strong>${esc(u.nome)}</strong><small class="por-quem">login: ${esc(u.login)}${eu ? " · você" : ""}</small></td>
    <td data-rotulo="Perfil">${admin ? `<span class="chip ok">Administrador</span>` : `<span class="chip">Comum</span>`}${u.ativo ? "" : ` <span class="chip apagado">Desativado</span>`}</td>
    <td data-rotulo="Permissões" class="celula-permissoes">${chipsPermissoes(u, lista.permissoes || [])}</td>
    <td data-rotulo="Último acesso"><span class="sutil">${u.ultimo_acesso ? esc(dataHoraBR(u.ultimo_acesso)) : "Nunca entrou"}</span>${Number(u.aparelhos) > 0
      ? `<small class="por-quem">${esc(u.aparelhos)} aparelho(s) conectado(s)</small>` : ""}</td>
    <td class="col-acoes">${acoes.join("")}</td>
  </tr>`;
}

function htmlOpcao(lista, campo, titulo, texto) {
  const emUso = Boolean(lista.em_uso);
  return `<label class="opcao-app ${emUso ? "" : "desabilitada"}"><span class="interruptor">
      <input type="checkbox" data-acao="usuarios-config" data-chave="${campo}" ${lista[campo] ? "checked" : ""} ${emUso ? "" : "disabled"}><span></span></span>
    <span><strong>${titulo}</strong><small>${texto}${emUso ? "" : " Cadastre um usuário para usar esta opção."}</small></span></label>`;
}

function htmlLiberado(lista) {
  const usuarios = lista.usuarios || [];
  const administradoresAtivos = usuarios.filter((u) => u.ativo && u.perfil === "administrador").length;
  const tabela = usuarios.length
    ? `<div class="tabela-wrap"><table class="tabela tabela-usuarios">
        <thead><tr><th>Pessoa</th><th>Perfil</th><th>Permissões</th><th>Último acesso</th><th class="col-acoes"></th></tr></thead>
        <tbody>${usuarios.map((u) => linhaUsuario(u, lista, administradoresAtivos)).join("")}</tbody>
      </table></div>`
    : `<p class="sutil">Nenhum usuário cadastrado. Cadastre cada pessoa do escritório acima; depois use o escudo para escolher o perfil e as permissões.</p>`;
  return `${lista.em_uso && !lista.tem_administrador
      ? alerta("aviso", "Ninguém tem o perfil de administrador. Use o botão de permissões (escudo) para tornar alguém administrador: essa pessoa gerencia tudo com o próprio login, sem a senha de administrador.")
      : ""}
    <form class="usuario-novo" data-acao="usuarios-criar" autocomplete="off" novalidate>
      <strong>${icone("mais", 16)} Novo usuário</strong>
      <input class="input" name="nome" maxlength="60" placeholder="Nome da pessoa" required aria-label="Nome">
      <input class="input" name="login" maxlength="40" placeholder="Login (opcional)" autocapitalize="none" spellcheck="false" aria-label="Login">
      <input class="input" type="password" name="senha" minlength="6" maxlength="200" placeholder="Senha (mín. 6)" autocomplete="new-password" aria-label="Senha">
      <button class="btn btn-primario" type="submit" data-espera="Cadastrando…">${icone("check", 16)} Cadastrar</button>
    </form>
    ${tabela}
    <div class="grade-campos">
      ${htmlOpcao(lista, "exigir_login_no_computador", "Pedir login também neste computador",
        "Sem isto, quem usa este computador entra direto e aparece como “Computador principal”. Celulares e outros aparelhos sempre pedem usuário e senha.")}
      ${htmlOpcao(lista, "pedir_login_ao_abrir", "Pedir usuário e senha toda vez que o aplicativo abrir",
        "Ao abrir o Fin Pro, quem estava conectado neste computador entra de novo. Celulares e outros aparelhos continuam conectados por 30 dias.")}
    </div>
    <p class="sutil">Senhas guardadas só em hash. Após 5 senhas erradas, o aparelho espera 5 minutos. Cada pessoa troca a própria senha no
      menu lateral. Desativar, excluir ou trocar a senha de alguém desconecta os aparelhos dessa pessoa.</p>`;
}

export function html(dados, erro) {
  let corpo = `<div class="esqueleto" style="height:150px"></div>`;
  if (erro) corpo = alertaErro(erro);
  else if (dados?.lista) corpo = htmlLiberado(dados.lista);
  else if (dados) corpo = htmlBloqueado(dados);
  return `<article class="card col-inteira" id="cfg-usuarios">
    <h3>${icone("usuarios", 18)} Usuários do escritório</h3>
    <p class="sutil">Cada pessoa entra com o próprio login e senha, e o sistema registra quem lançou, pagou ou alterou cada boleto.
      Enquanto não houver usuários, o Fin Pro funciona como antes: livre neste computador e com a senha de acesso pelo celular.</p>
    ${corpo}
  </article>`;
}

// ------------------------------------------------------------------ depois de cada mudança

const lista = () => tela.dados[chave]?.lista;
const acharUsuario = (id) => lista()?.usuarios?.find((u) => u.id === id);

/**
 * Redesenha o cartão com a lista que o servidor devolveu e atualiza quem está conectado (menu lateral, chip de
 * administrador e o aviso do cartão de rede). Se a área deixou de estar liberada (ex.: deixou de ser administrador), recarrega a aba.
 */
async function aplicar(novaLista) {
  redesenhar(chave, { admin: tela.admin, lista: novaLista });
  const a = await carregarAcesso();
  window.dispatchEvent(new Event("status:atualizar"));
  if (a && !a.autorizado) {
    // ex.: ligou "Pedir login também neste computador" sem ter entrado: já mostra a tela de login
    window.dispatchEvent(new Event("acesso:necessario"));
    return;
  }
  if ((a?.usuario && !a.administrador) || !liberado()) {
    recarregar(); // deixou de ser administrador: os cartões da aba mostram o cadeado
    return;
  }
  redesenhar("rede");
}

const protegido = (executar) => comAdmin(executar, DESCRICAO);

/** Erros de dentro das janelas: área restrita fecha a janela e redesenha a aba; o resto aparece na própria janela. */
function tratarErroJanela(erro, fechar, mostrar) {
  if (CODIGOS_ADMIN.includes(erro?.codigo)) {
    fechar();
    avisarErro(erro);
    return;
  }
  mostrar(mensagemErro(erro));
}

/**
 * A janela foi fechada enquanto a chamada esperava (ex.: Esc na janela da senha de administrador fecha as duas janelas).
 * Área restrita ainda precisa virar aviso e cadeado na aba; o resto não tem mais onde aparecer.
 */
function janelaFechada(erro) {
  if (CODIGOS_ADMIN.includes(erro?.codigo)) avisarErro(erro);
  return undefined;
}

// ------------------------------------------------------------------ janela de perfil e permissões

function abrirPermissoes(id) {
  const u = acharUsuario(id);
  const catalogo = lista()?.permissoes || [];
  if (!u) return Promise.resolve();
  const adm = u.perfil === "administrador";
  return new Promise((resolve) => {
    const { el, fechar } = abrirModal({
      titulo: `Perfil e permissões — ${u.nome}`,
      corpo: `<form data-form-permissoes>
        <div class="lista-permissoes">
          <label class="opcao-permissao"><input type="radio" name="perfil" value="administrador" ${adm ? "checked" : ""}>
            <span><strong>Administrador</strong> — pode tudo, inclusive cadastrar usuários e mudar as permissões dos outros</span></label>
          <label class="opcao-permissao"><input type="radio" name="perfil" value="comum" ${adm ? "" : "checked"}>
            <span><strong>Comum</strong> — só o que estiver marcado abaixo. Ver o painel, os boletos e os Pix é liberado para todo mundo.</span></label>
        </div>
        <div class="lista-permissoes">${catalogo.map((p) => `<label class="opcao-permissao"><input type="checkbox" name="permissoes"
          value="${esc(p.chave)}" ${(u.permissoes || []).includes(p.chave) ? "checked" : ""} ${adm ? "disabled" : ""}><span>${esc(p.rotulo)}</span></label>`).join("")}</div>
        <p class="sutil" style="margin-top:12px">As mudanças valem na hora; o menu da pessoa se atualiza quando ela abrir o Fin Pro de novo.</p>
        <p class="admin-erro" role="alert" data-erro></p>
      </form>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
      aoFechar: () => resolve(),
    });
    const form = el.querySelector("[data-form-permissoes]");
    const salvarBtn = el.querySelector("[data-salvar]");
    const erroEl = el.querySelector("[data-erro]");
    form.addEventListener("change", (e) => {
      if (e.target.name !== "perfil") return;
      const comum = e.target.value === "comum";
      form.querySelectorAll("[name=permissoes]").forEach((c) => { c.disabled = !comum; });
    });
    const salvar = async (e) => {
      e?.preventDefault();
      if (salvarBtn.disabled) return;
      const perfil = form.querySelector("[name=perfil]:checked")?.value || "comum";
      const corpo = perfil === "administrador"
        ? { perfil }
        : { perfil, permissoes: [...form.querySelectorAll("[name=permissoes]:checked")].map((c) => c.value) };
      if (ehEu(u) && adm && perfil === "comum") {
        const seguir = await confirmar({ titulo: "Deixar de ser administrador", mensagem: "Você não poderá mais cadastrar usuários nem mudar permissões.",
          textoConfirmar: "Continuar", perigo: true });
        if (!seguir) return;
      }
      salvarBtn.disabled = true;
      erroEl.textContent = "";
      try {
        const resposta = await protegido(() => api.put(`/api/usuarios/${encodeURIComponent(u.id)}`, corpo));
        fechar(true);
        toast(`Permissões de ${u.nome} salvas.`, "ok");
        await aplicar(resposta);
      } catch (erro) {
        if (!el.isConnected) return janelaFechada(erro);
        salvarBtn.disabled = false;
        tratarErroJanela(erro, () => fechar(false), (texto) => {
          erroEl.textContent = texto;
          toast(texto, "erro", { duracao: 6000 });
        });
      }
    };
    form.addEventListener("submit", salvar);
    salvarBtn.addEventListener("click", salvar);
  });
}

// ------------------------------------------------------------------ janela de senha (de outra pessoa, a minha ou a de administrador)

/**
 * Janela com [senha atual] + nova senha + repetição. Confere tamanho e igualdade aqui; `enviar(valores)` faz a chamada.
 * Erros do servidor aparecem na própria janela (área restrita fecha a janela e redesenha a aba). Devolve true se enviou.
 */
function janelaSenha({ titulo, descricao, atual = false, rotulo = "Nova senha", repetir = "Repita a nova senha", textoBotao = "Trocar senha",
  iconeBotao = "chave", enviar }) {
  return new Promise((resolve) => {
    let enviado = false;
    const { el, fechar } = abrirModal({
      titulo,
      corpo: `<form class="admin-form" data-form-senha autocomplete="off">
        <p class="sutil">${esc(descricao)}</p>
        ${atual ? `<label class="imp-grupo"><span class="imp-rotulo">Senha atual</span>
          <input type="password" class="input" name="senha_atual" maxlength="200" autocomplete="current-password"></label>` : ""}
        <label class="imp-grupo"><span class="imp-rotulo">${esc(rotulo)}</span>
          <input type="password" class="input" name="senha" minlength="6" maxlength="200" autocomplete="new-password"></label>
        <label class="imp-grupo"><span class="imp-rotulo">${esc(repetir)}</span>
          <input type="password" class="input" name="confirmacao" maxlength="200" autocomplete="new-password"></label>
        <p class="admin-erro" role="alert" data-erro></p>
        <button type="submit" hidden></button>
      </form>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-salvar>${icone(iconeBotao, 16)} ${esc(textoBotao)}</button>`,
      aoFechar: () => resolve(enviado),
    });
    const form = el.querySelector("[data-form-senha]");
    const salvarBtn = el.querySelector("[data-salvar]");
    const erroEl = el.querySelector("[data-erro]");
    form.querySelector("input")?.focus();
    const falhar = (texto, campo) => {
      erroEl.textContent = texto;
      campo?.focus();
    };
    const salvar = async (e) => {
      e?.preventDefault();
      if (salvarBtn.disabled) return;
      const valores = Object.fromEntries(new FormData(form).entries());
      erroEl.textContent = "";
      if (atual && !valores.senha_atual) return falhar("Digite a sua senha atual.", form.elements.senha_atual);
      if ((valores.senha || "").length < 6) return falhar("A senha precisa ter pelo menos 6 caracteres.", form.elements.senha);
      if (valores.senha !== valores.confirmacao) {
        form.elements.confirmacao.value = "";
        return falhar("As duas senhas não são iguais.", form.elements.confirmacao);
      }
      salvarBtn.disabled = true;
      try {
        await enviar(valores);
        enviado = true;
        fechar(true);
      } catch (erro) {
        if (!el.isConnected) return janelaFechada(erro);
        salvarBtn.disabled = false;
        tratarErroJanela(erro, () => fechar(false), (texto) => falhar(texto, form.elements[atual ? "senha_atual" : "senha"]));
      }
      return undefined;
    };
    form.addEventListener("submit", salvar);
    salvarBtn.addEventListener("click", salvar);
  });
}

// ------------------------------------------------------------------ ações

const doAlvo = (alvo) => acharUsuario(alvo.dataset.id);

export const acoes = {
  "usuarios-permissoes": (alvo) => abrirPermissoes(alvo.dataset.id),

  "usuarios-renomear": async (alvo) => {
    const u = doAlvo(alvo);
    if (!u) return;
    const nome = await pedirTexto({ titulo: "Mudar o nome", rotulo: "Nome da pessoa", valor: u.nome, maximo: 60 });
    if (!nome || nome === u.nome) return;
    const resposta = await protegido(() => api.put(`/api/usuarios/${encodeURIComponent(u.id)}`, { nome }));
    toast("Nome alterado.", "ok");
    await aplicar(resposta);
  },

  "usuarios-senha": async (alvo) => {
    const u = doAlvo(alvo);
    if (!u) return;
    if (ehEu(u)) {
      // a própria senha vai por minha-senha (pede a atual e mantém este aparelho conectado; o PUT desconectaria você)
      const trocou = await janelaSenha({ titulo: "Trocar a minha senha", atual: true,
        descricao: "Os outros aparelhos em que você tinha entrado serão desconectados; este continua conectado.",
        enviar: (valores) => api.post("/api/usuarios/minha-senha", valores) });
      if (!trocou) return;
      toast("Senha trocada. Os outros aparelhos em que você tinha entrado foram desconectados.", "ok", { duracao: 6000 });
      await aplicar(await buscar("/api/usuarios"));
      return;
    }
    let resposta = null;
    const trocou = await janelaSenha({ titulo: `Trocar a senha — ${u.nome}`,
      descricao: `Os aparelhos em que ${u.nome} tinha entrado serão desconectados e a pessoa vai precisar da nova senha.`,
      enviar: async ({ senha }) => { resposta = await protegido(() => api.put(`/api/usuarios/${encodeURIComponent(u.id)}`, { senha })); } });
    if (!trocou) return;
    toast(`Senha de ${u.nome} trocada. Os aparelhos dessa pessoa foram desconectados.`, "ok", { duracao: 6000 });
    await aplicar(resposta);
  },

  /**
   * Primeira senha de administrador (só no computador onde o Fin Pro está instalado). Se o cartão de importação, logo acima,
   * já mostra o formulário de criar a senha, leva até ele; senão abre uma janela. Criada, a área fica liberada neste aparelho.
   */
  "usuarios-criar-senha": async () => {
    const formulario = tela.raiz?.querySelector('#cfg-importacao form[data-acao="importacao-criar-senha"]');
    if (formulario) {
      formulario.scrollIntoView({ block: "center", behavior: "smooth" });
      formulario.querySelector("input")?.focus({ preventScroll: true });
      return;
    }
    let admin = null;
    const criou = await janelaSenha({ titulo: "Criar senha de administrador", rotulo: "Nova senha de administrador", repetir: "Repita a senha",
      textoBotao: "Criar senha", iconeBotao: "escudo",
      descricao: "Ela protege a importação, o cadastro de usuários, o backup e o recebimento por e-mail. Guarde-a bem: "
        + "se esquecer, só dá para criar outra no computador, apagando o arquivo dados\\admin.json com o Fin Pro fechado.",
      enviar: async ({ senha, confirmacao }) => { admin = await api.post("/api/admin/senha", { senha, confirmacao }); } });
    if (!criou) return;
    tela.admin = admin;
    toast(`Senha de administrador criada. A área restrita fica liberada neste aparelho por ${Number(admin?.minutos_sessao) || 20} minutos.`,
      "ok", { duracao: 7000 });
    recarregar(); // libera também a importação, o backup e o recebimento
  },

  "usuarios-desativar": async (alvo) => {
    const u = doAlvo(alvo);
    if (!u) return;
    const seguir = await confirmar({ titulo: "Desativar usuário",
      mensagem: `Desativar ${u.nome}? A pessoa não consegue mais entrar e os aparelhos dela são desconectados.`, textoConfirmar: "Desativar", perigo: true });
    if (!seguir) return;
    const resposta = await protegido(() => api.put(`/api/usuarios/${encodeURIComponent(u.id)}`, { ativo: false }));
    toast(`${u.nome} desativado(a).`, "ok");
    await aplicar(resposta);
  },

  "usuarios-reativar": async (alvo) => {
    const u = doAlvo(alvo);
    if (!u) return;
    const resposta = await protegido(() => api.put(`/api/usuarios/${encodeURIComponent(u.id)}`, { ativo: true }));
    toast(`${u.nome} pode entrar de novo.`, "ok");
    await aplicar(resposta);
  },

  "usuarios-excluir": async (alvo) => {
    const u = doAlvo(alvo);
    if (!u) return;
    const seguir = await confirmar({ titulo: "Excluir usuário",
      mensagem: `Excluir ${u.nome} (${u.login})? O histórico continua mostrando o que a pessoa lançou ou pagou. Os aparelhos dela são desconectados.`,
      textoConfirmar: "Excluir", perigo: true });
    if (!seguir) return;
    await protegido(() => api.del(`/api/usuarios/${encodeURIComponent(u.id)}`)); // 204, sem corpo: busca a lista de novo
    toast(`${u.nome} excluído(a).`, "ok");
    await aplicar(await buscar("/api/usuarios"));
  },
};

export const alteracoes = {
  /** Chaves "Pedir login também neste computador" e "Pedir usuário e senha toda vez que o aplicativo abrir" (ligadas entre si no servidor). */
  "usuarios-config": async (campo) => {
    const opcao = campo.dataset.chave;
    const ligado = campo.checked;
    if (ligado && !estado.acesso?.usuario) {
      const seguir = await confirmar({ titulo: "Pedir login neste computador",
        mensagem: "Este computador também vai pedir usuário e senha. Confira se você sabe o login e a senha de um usuário administrador.",
        textoConfirmar: "Ligar" });
      if (!seguir) {
        if (campo.isConnected) campo.checked = false;
        return;
      }
    }
    const resposta = await protegido(() => api.put("/api/usuarios/config", { [opcao]: ligado }));
    toast("Opção salva.", "ok");
    await aplicar(resposta); // as duas chaves vêm do servidor (ligar uma pode ligar ou desligar a outra)
  },
};

export const formularios = {
  "usuarios-criar": async (form) => {
    const nome = form.elements.nome.value.trim();
    const login = form.elements.login.value.trim();
    const senha = form.elements.senha.value;
    if (!nome) {
      toast("Informe o nome da pessoa.", "aviso");
      form.elements.nome.focus();
      return;
    }
    if (senha.length < 6) {
      toast("A senha precisa ter pelo menos 6 caracteres.", "aviso");
      form.elements.senha.focus();
      return;
    }
    const antes = Boolean(lista()?.em_uso);
    const resposta = await protegido(() => api.post("/api/usuarios", { nome, login, senha }));
    form.reset();
    const criado = resposta.criado || {};
    toast(`${criado.nome || nome} cadastrado(a). Login: ${criado.login || login}`, "ok", {
      duracao: 7000,
      acao: { rotulo: "Permissões", executar: () => abrirPermissoes(criado.id).catch(avisarErro) },
    });
    if (!antes && resposta.em_uso) toast("A partir de agora, os aparelhos da rede pedem usuário e senha.", "info", { duracao: 7000 });
    await aplicar(resposta);
  },
};

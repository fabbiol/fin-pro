// Configurações · Acesso pelo celular (rede Wi-Fi): senha de acesso, chave liga/desliga, QR code do endereço e aparelhos.
// Ligar e trocar a senha só no computador onde o Fin Pro está instalado (o servidor responde 403 "somente_local" de fora).
// Na VPS (LEITOR_HOST=0.0.0.0, via_env) os endereços da rede são os do contêiner: mostra o endereço desta página em vez do QR.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { confirmar, copiar, dataHoraBR, esc, toast } from "../../ui.js";
import { alertaErro, atualizar, buscar, carregarAcesso, redesenhar, tela } from "./tela.js";

export const chave = "rede";

const ESPERA_RELIGAR = 20 * 1000; // enquanto "Ligando…" ou com erro, confere de novo (o Fin Pro reabre o acesso sozinho)
let relogio = null;

/** GET /api/rede (sempre 200). estado.acesso também é usado (avisos de usuários e de rede sem senha). */
export async function carregar() {
  const [rede] = await Promise.all([buscar("/api/rede"), carregarAcesso()]);
  return rede;
}

export function iniciar() {
  parar();
  relogio = setInterval(() => {
    const r = tela.dados[chave];
    if (document.hidden || !r || r.via_env || !r.ativo || r.rodando) return;
    atualizar(chave);
  }, ESPERA_RELIGAR);
}

export function parar() {
  if (relogio) clearInterval(relogio);
  relogio = null;
}

export function textoSituacao(r) {
  if (r.via_env) return "Liberado pelo arquivo .env (LEITOR_HOST=0.0.0.0): os aparelhos da rede já podem abrir o Fin Pro.";
  if (r.ativo && r.rodando) return `Ligado: abra ${r.urls?.[0] || ""} no celular conectado ao mesmo Wi-Fi.`;
  if (r.ativo && r.erro) return r.erro;
  if (r.ativo) return "Ligando…";
  if (!r.senha_definida && !r.senha_via_env) return "Desligado. Defina uma senha para liberar o acesso pelo celular.";
  return "Desligado: só este computador abre o Fin Pro.";
}

const urlQr = (url) => `/api/rede/qrcode.svg?url=${encodeURIComponent(url)}`;
const alerta = (tipo, conteudo) => `<div class="alerta ${tipo}">${icone(tipo === "info" ? "info" : "alerta", 16)}<div>${conteudo}</div></div>`;

function htmlAlertas(r) {
  const a = estado.acesso;
  const partes = [];
  if (r.ativo && r.erro) partes.push(alerta("erro", esc(r.erro)));
  if (a?.rede_sem_senha) partes.push(alerta("erro", "O acesso pela rede está liberado sem senha. Defina uma senha agora."));
  if (a?.usuarios) {
    partes.push(alerta("info", `Com usuários cadastrados, cada pessoa entra no celular com o próprio usuário e senha.${r.via_env
      ? "" : " A senha abaixo continua necessária para ligar o acesso."}`));
  }
  if (!r.local) {
    partes.push(alerta("info", `Você está num aparelho da rede. Ligar o acesso e trocar a senha só podem ser feitos no computador onde o Fin Pro está instalado.
      <div class="linha-botoes" style="margin-top:8px"><button class="btn btn-sm" type="button" data-acao="rede-sair">${icone("sair", 15)} Sair deste aparelho</button></div>`));
  }
  return partes.join("");
}

function htmlSenha(r, senhaOk) {
  if (r.senha_via_env) return `<span class="sutil">A senha está no arquivo .env (LEITOR_SENHA_ACESSO).</span>`;
  if (!r.local) return "";
  return `<form class="rede-senha" data-acao="rede-senha" autocomplete="off" novalidate>
      <input type="password" class="input" name="senha" minlength="6" maxlength="200" autocomplete="new-password"
        placeholder="${senhaOk ? "Nova senha" : "Senha"} (mín. 6)" aria-label="${senhaOk ? "Nova senha" : "Senha"}">
      <input type="password" class="input" name="confirmacao" maxlength="200" autocomplete="new-password" placeholder="Repita a senha" aria-label="Repita a senha">
      <button class="btn ${senhaOk ? "" : "btn-primario"}" type="submit">${icone("chave", 16)} ${senhaOk ? "Trocar senha" : "Salvar senha"}</button>
    </form>`;
}

function htmlPassos(r) {
  const senhaOk = Boolean(r.senha_definida || r.senha_via_env);
  return `<div class="rede-passo ${senhaOk ? "ok" : ""}"><span class="rede-numero">1</span><div>
      <strong>${senhaOk ? "Senha de acesso definida" : "Defina uma senha"}</strong>
      <span class="sutil">Mínimo 6 caracteres, guardada só em hash. Trocar a senha desconecta os aparelhos que já tinham entrado.</span>
      ${htmlSenha(r, senhaOk)}
    </div></div>
    <div class="rede-passo ${r.ativo && r.rodando ? "ok" : ""}"><span class="rede-numero">2</span><div>
      <strong>Ligue a chave “Acesso pelo celular”</strong>
      <span class="sutil">Na primeira vez, se o Windows perguntar se o Python pode acessar a rede, marque Redes privadas e clique em Permitir acesso.</span>
    </div></div>
    <div class="rede-passo"><span class="rede-numero">3</span><div>
      <strong>Leia o QR code com a câmera do celular</strong>
      <span class="sutil">O celular precisa estar no mesmo Wi-Fi. Digite a senha uma vez: o acesso vale por 30 dias.</span>
    </div></div>
    <details class="rede-ajuda"><summary>O celular não abre o endereço?</summary><ul class="lista-info">
      <li>Confira se o celular está no mesmo Wi-Fi do computador (e não nos dados móveis).</li>
      <li>Se o roteador reiniciou, o endereço pode mudar: o Fin Pro reabre o acesso sozinho em até 1 minuto. Leia o QR code de novo.</li>
      <li>Se o Windows bloqueou, libere o Python no Firewall do Windows para Redes privadas.</li>
      <li>Após 5 senhas erradas, o aparelho fica bloqueado por 5 minutos.</li>
      <li>Alternativa avançada: LEITOR_HOST=0.0.0.0 e LEITOR_SENHA_ACESSO no arquivo .env.</li>
    </ul></details>`;
}

const botaoCopiar = (url) => `<button class="btn btn-sm" type="button" data-acao="rede-copiar" data-url="${esc(url)}">${icone("copiar", 14)} Copiar endereço</button>`;

function htmlQr(r) {
  const urls = Array.isArray(r.urls) ? r.urls : [];
  if (r.via_env && !r.local) {
    // VPS ou aparelho da rede: os endereços do servidor (do contêiner) não servem; o desta página, sim
    return `${icone("wifi", 40)}<span class="sutil">Endereço deste Fin Pro:</span>
      <span class="rede-url">${esc(location.origin)}</span>${botaoCopiar(location.origin)}`;
  }
  if (urls.length && (r.rodando || r.via_env)) {
    const [url, ...outros] = urls;
    return `<img src="${esc(urlQr(url))}" alt="QR code do endereço do Fin Pro" width="196" height="196" data-rede-qr>
      <span class="rede-url" data-rede-url-texto>${esc(url)}</span>
      ${botaoCopiar(url)}
      ${outros.length ? `<details class="rede-outros"><summary>Outros endereços</summary><div class="linha-botoes">
        ${outros.map((u) => `<button class="btn btn-sm btn-fantasma" type="button" data-acao="rede-qr" data-url="${esc(u)}">${esc(u)}</button>`).join("")}
      </div></details>` : ""}`;
  }
  return `${icone("qrcode", 40)}<span class="sutil">${r.ativo ? "Nenhuma rede local encontrada." : "Ligue o acesso para ver o QR code."}</span>`;
}

function htmlAcessos(r) {
  const acessos = Array.isArray(r.acessos) ? r.acessos : [];
  return `<strong>${icone("monitor", 16)} Aparelhos que acessaram</strong>
    ${acessos.length
      ? acessos.map((a) => `<span class="sutil">${esc(a.aparelho)} · ${esc(a.ip)} · ${esc(dataHoraBR(a.ultimo))}</span>`).join("")
      : `<span class="sutil">Nenhum aparelho acessou desde que o Fin Pro foi aberto.</span>`}
    <span class="sutil">Para desconectar todos os aparelhos, troque a senha.</span>`;
}

export function html(r, erro) {
  const titulo = `<h3>${icone("celular", 18)} Acesso pelo celular (rede Wi-Fi)</h3>`;
  if (erro || !r) {
    return `<section class="card rede-card col-inteira" id="cfg-rede">
      <div class="rede-topo">${titulo}</div>
      ${erro ? alertaErro(erro) : `<div class="esqueleto" style="height:220px"></div>`}
    </section>`;
  }
  const travada = !r.local || r.via_env;
  return `<section class="card rede-card col-inteira" id="cfg-rede">
    <div class="rede-topo">${titulo}
      <label class="interruptor" title="${travada ? (r.via_env ? "Liberado pelo arquivo .env" : "Só no computador onde o Fin Pro está instalado") : "Acesso pelo celular"}">
        <input type="checkbox" data-acao="rede-ativar" aria-label="Acesso pelo celular" ${r.ativo ? "checked" : ""} ${travada ? "disabled" : ""}><span></span></label>
    </div>
    <p class="sutil">${esc(textoSituacao(r))}</p>
    ${htmlAlertas(r)}
    <div class="rede-grade">
      <div class="rede-info">${htmlPassos(r)}</div>
      <div class="rede-qr">${htmlQr(r)}</div>
    </div>
    <div class="rede-acessos">${htmlAcessos(r)}</div>
  </section>`;
}

// ------------------------------------------------------------------ ações

export const acoes = {
  "rede-copiar": (alvo) => copiar(alvo.dataset.url || "", "Endereço copiado"),

  /** Mostra o QR de outro endereço (o que estava na tela vai para a lista de "Outros endereços"). */
  "rede-qr": (alvo) => {
    const cartao = alvo.closest("#cfg-rede");
    const img = cartao?.querySelector("img[data-rede-qr]");
    const texto = cartao?.querySelector("[data-rede-url-texto]");
    const copia = cartao?.querySelector('[data-acao="rede-copiar"]');
    const nova = alvo.dataset.url;
    if (!img || !nova) return;
    const anterior = copia?.dataset.url || "";
    img.src = urlQr(nova);
    if (texto) texto.textContent = nova;
    if (copia) copia.dataset.url = nova;
    if (anterior) {
      alvo.dataset.url = anterior;
      alvo.textContent = anterior;
    }
  },

  /** Desconecta este aparelho (app.js apaga as sessões e recarrega a página). */
  "rede-sair": () => { window.dispatchEvent(new Event("acesso:sair")); },
};

export const alteracoes = {
  "rede-ativar": async (campo) => {
    const r = tela.dados[chave] || {};
    const ligar = campo.checked;
    if (ligar && !r.senha_definida && !r.senha_via_env) {
      campo.checked = false;
      toast("Defina uma senha antes de liberar o acesso pela rede.", "aviso", { duracao: 6000 });
      tela.raiz?.querySelector('#cfg-rede form[data-acao="rede-senha"] [name=senha]')?.focus();
      return;
    }
    const novo = await api.post("/api/rede/ativar", { ativo: ligar }); // pode levar alguns segundos (abre/fecha o 2º servidor)
    redesenhar(chave, novo);
    if (!ligar) toast("Acesso pelo celular desligado. Os aparelhos da rede não abrem mais o Fin Pro.", "info", { duracao: 6000 });
    else if (novo.rodando) toast("Acesso pelo celular ligado.", "ok");
    else if (novo.erro) toast(novo.erro, "erro", { duracao: 7000 });
  },
};

export const formularios = {
  "rede-senha": async (form) => {
    const r = tela.dados[chave] || {};
    const senha = form.elements.senha.value;
    const confirmacao = form.elements.confirmacao.value;
    if (senha.length < 6) {
      toast("A senha precisa ter pelo menos 6 caracteres.", "aviso");
      form.elements.senha.focus();
      return;
    }
    if (senha !== confirmacao) {
      toast("As duas senhas não são iguais.", "aviso");
      form.elements.confirmacao.value = "";
      form.elements.confirmacao.focus();
      return;
    }
    const trocando = Boolean(r.senha_definida);
    if (trocando) {
      const seguir = await confirmar({ titulo: "Trocar a senha de acesso",
        mensagem: "Os celulares e outros aparelhos que já entraram serão desconectados e vão precisar da nova senha.", textoConfirmar: "Trocar senha" });
      if (!seguir) return;
    }
    const novo = await api.post("/api/rede/senha", { senha, confirmacao });
    form.reset();
    redesenhar(chave, novo);
    toast(trocando
      ? "Senha trocada. Os aparelhos que já tinham entrado precisam digitar a nova senha."
      : "Senha de acesso definida. Agora ligue a chave “Acesso pelo celular”.", "ok", { duracao: 6000 });
    // "rede liberada sem senha" (estado.acesso) pode ter deixado de valer
    if (estado.acesso?.rede_sem_senha) {
      await carregarAcesso();
      redesenhar(chave);
    }
  },
};

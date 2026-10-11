// Senha de administrador: libera as áreas restritas (importação de boletos). A conferência é feita no servidor.
import { api } from "./api.js";
import { icone } from "./icons.js";
import { abrirModal, esc, mensagemErro } from "./ui.js";

export const estadoAdmin = () => api.get("/api/admin");

export const bloquearAdmin = () => api.post("/api/admin/sair");

/** Pede a senha de administrador. Devolve true se a área foi liberada. */
export function pedirSenhaAdmin({ titulo = "Área restrita", descricao = "Digite a senha de administrador para continuar." } = {}) {
  return new Promise((resolve) => {
    let liberado = false;
    const { el, fechar } = abrirModal({
      titulo,
      corpo: `<form class="admin-form" data-admin-form autocomplete="off">
          <p class="sutil">${esc(descricao)}</p>
          <label class="imp-grupo"><span class="imp-rotulo">Senha de administrador</span>
            <input type="password" class="input" name="senha" autocomplete="current-password" autofocus></label>
          <p class="admin-erro" role="alert" data-admin-erro></p>
        </form>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-admin-entrar>${icone("escudo", 16)} Entrar</button>`,
      aoFechar: () => resolve(liberado),
    });
    const campo = el.querySelector("[name=senha]");
    const erro = el.querySelector("[data-admin-erro]");
    const botao = el.querySelector("[data-admin-entrar]");
    const enviar = async (e) => {
      e?.preventDefault();
      if (!campo.value) {
        campo.focus();
        return;
      }
      botao.disabled = true;
      erro.textContent = "";
      try {
        await api.post("/api/admin/entrar", { senha: campo.value });
        liberado = true;
        fechar(true);
      } catch (falha) {
        erro.textContent = mensagemErro(falha);
        campo.value = "";
        campo.focus();
        botao.disabled = false;
      }
    };
    el.querySelector("[data-admin-form]").addEventListener("submit", enviar);
    botao.addEventListener("click", enviar);
    campo.focus();
  });
}

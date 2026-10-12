// Tela: Configurações — versão provisória. A tela original não foi para o GitHub (o .gitignore escondia esta pasta)
// e a cópia que estava na VPS se perdeu; ela está sendo refeita. Enquanto isso, o resto do Fin Pro funciona normalmente.
import { icone } from "../../icons.js";

export function montar(el) {
  el.innerHTML = `<div class="card vazio"><div class="vazio-icone">${icone("config", 26)}</div>
    <h3>Configurações em manutenção</h3>
    <p>Esta tela está sendo refeita e volta em breve. Boletos, Pix, comprovantes, caixa, diesel, empresas e os bots
      continuam funcionando normalmente, com as configurações que já estavam salvas.</p>
    <a class="btn" href="#/painel">${icone("atualizar", 16)} Voltar ao painel</a></div>`;
}

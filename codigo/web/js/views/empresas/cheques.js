// Empresas e fechamentos · cheques pré-datados (guardar, avisar o vencimento e dar baixa ao compensar).
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, esc, hojeISO, parseValor } from "../../ui.js";
import { carregarDados, deuCerto, opcoes, opcoesEmpresa, selo, tentar, vazio } from "./comum.js";
import { STATUS_CHEQUE, tela } from "./estado.js";

export async function htmlCheques() {
  const resposta = await tentar(() => api.get("/api/cheques"));
  const cheques = resposta?.cheques || [];
  const emCarteira = cheques.filter((c) => c.status === "Em carteira");
  const hoje = hojeISO();
  return `
    <section class="resumo-lista">
      <div class="resumo-item"><span>Em carteira</span><strong>${emCarteira.length}</strong></div>
      <div class="resumo-item"><span>Valor em carteira</span>
        <strong>${brl(emCarteira.reduce((s, c) => s + (c.valor || 0), 0))}</strong></div>
      <div class="resumo-item"><span>Para depositar até hoje</span>
        <strong class="${emCarteira.some((c) => c.vencimento && c.vencimento <= hoje) ? "aviso" : ""}">
          ${brl(emCarteira.filter((c) => c.vencimento && c.vencimento <= hoje).reduce((s, c) => s + (c.valor || 0), 0))}</strong></div>
      <div class="resumo-acoes"><button class="btn btn-sm btn-primario" data-acao="novo-cheque">${icone("mais", 15)} Guardar cheque</button>
        <a class="btn btn-sm" href="#/comprovantes?tipo=cheque">${icone("clipe", 15)} Buscar cheques</a></div>
    </section>
    <section class="card tabela-card"><div class="tabela-wrap">${tabela(cheques, hoje)}</div></section>`;
}

function tabela(cheques, hoje) {
  if (!cheques.length) {
    return vazio(icone("cartao", 26), "Nenhum cheque guardado",
                 "Mande a foto do cheque para o bot de notas (com o número do pedido na legenda) ou cadastre aqui.");
  }
  return `<table class="tabela">
    <thead><tr><th>Bom para</th><th>Empresa</th><th>Cheque</th><th>Banco</th><th>Ag. / Coop.</th>
      <th class="num">Valor</th><th>Pedidos</th><th>Situação</th><th class="col-acoes"></th></tr></thead>
    <tbody>${cheques.map((c) => {
      const atrasado = c.status === "Em carteira" && c.vencimento && c.vencimento <= hoje;
      return `<tr class="${atrasado ? "linha-alerta" : ""}">
        <td>${dataBR(c.vencimento)}${atrasado ? ` <span class="chip aviso">depositar</span>` : ""}</td>
        <td>${esc(c.empresa || "")}</td><td>${esc(c.numero || "—")}</td><td>${esc(c.banco || "")}</td>
        <td>${esc([c.agencia, c.coop].filter(Boolean).join(" / ") || "—")}</td>
        <td class="num">${brl(c.valor)}</td><td>${esc(c.pedidos || c.notas || "")}</td><td>${selo(c.status)}</td>
        <td class="col-acoes">
          ${c.status === "Em carteira" ? `<button class="btn btn-sm" data-acao="compensar-cheque" data-id="${c.id}"
            title="Registrar o depósito (com o comprovante, se tiver): o cheque é compensado e as notas recebem baixa">
            ${icone("check", 14)} Depositei</button>` : ""}
          <button class="btn-icone btn-sm" data-acao="editar-cheque" data-id="${c.id}" title="Editar">${icone("editar", 15)}</button>
        </td></tr>`;
    }).join("")}</tbody></table>`;
}

/** ``enviar(corpo)`` troca o lançamento direto pela confirmação de um cheque recebido no bot. */
export function formularioCheque(cheque = null, enviar = null) {
  const c = cheque || {};
  const edicao = Boolean(c.id);
  const { el, fechar } = abrirModal({
    titulo: edicao ? `Cheque ${c.numero || `#${c.id}`}` : "Guardar cheque pré-datado",
    corpo: `<form class="grade-campos" data-form-cheque>
      <div class="campo"><label for="c-empresa">Empresa</label>
        <select id="c-empresa" name="empresa" class="input" required>${opcoesEmpresa(c.empresa || "")}</select></div>
      <div class="campo"><label for="c-venc">Bom para (data do depósito)</label>
        <input id="c-venc" name="vencimento" type="date" class="input" value="${c.vencimento || ""}" required></div>
      <div class="campo"><label for="c-valor">Valor</label>
        <input id="c-valor" name="valor" class="input" inputmode="decimal" value="${c.valor ?? ""}" required></div>
      <div class="campo"><label for="c-numero">Nº do cheque</label>
        <input id="c-numero" name="numero" class="input" value="${esc(c.numero || "")}" maxlength="20"></div>
      <div class="campo"><label for="c-banco">Banco</label>
        <input id="c-banco" name="banco" class="input" value="${esc(c.banco || "")}" maxlength="60"></div>
      <div class="campo"><label for="c-agencia">Agência</label>
        <input id="c-agencia" name="agencia" class="input" value="${esc(c.agencia || "")}" maxlength="12"></div>
      <div class="campo"><label for="c-coop">Cooperativa</label>
        <input id="c-coop" name="coop" class="input" value="${esc(c.coop || "")}" maxlength="12"></div>
      <div class="campo"><label for="c-conta">Conta</label>
        <input id="c-conta" name="conta" class="input" value="${esc(c.conta || "")}" maxlength="20"></div>
      <div class="campo"><label for="c-emitente">Emitente</label>
        <input id="c-emitente" name="emitente" class="input" value="${esc(c.emitente || "")}" maxlength="80"></div>
      <div class="campo"><label for="c-pedidos">Pedidos</label>
        <input id="c-pedidos" name="pedidos" class="input" value="${esc(c.pedidos || "")}" maxlength="200" placeholder="7043, 7053"></div>
      <div class="campo"><label for="c-notas">Notas fiscais</label>
        <input id="c-notas" name="notas" class="input" value="${esc(c.notas || "")}" maxlength="200" placeholder="6859, 6869"></div>
      ${edicao ? `<div class="campo"><label for="c-status">Situação</label>
        <select id="c-status" name="status" class="input">${opcoes(STATUS_CHEQUE, c.status)}</select></div>
        <div class="campo"><label for="c-deposito">Depositado em</label>
          <input id="c-deposito" name="data_deposito" type="date" class="input" value="${c.data_deposito || ""}"></div>` : ""}
      <div class="campo col-2"><label for="c-obs">Observações</label>
        <input id="c-obs" name="observacoes" class="input" value="${esc(c.observacoes || "")}" maxlength="300"></div>
    </form>
    <p class="sutil" style="margin-top:10px">Os pedidos ou notas citados prendem as linhas do fechamento como
      “Em cheque”. Quando o cheque compensar, a baixa é feita sozinha.</p>
    ${c.arquivo ? `<p class="sutil">${icone("clipe", 14)} <a href="/${esc(c.arquivo)}" target="_blank" rel="noopener">
      ${esc(c.arquivo_nome || "imagem do cheque")}</a></p>` : ""}`,
    rodape: `${edicao ? `<button class="btn btn-perigo btn-fantasma" data-excluir>${icone("lixeira", 15)} Excluir</button>` : ""}
      <button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });

  const salvar = async (evento) => {
    evento?.preventDefault();
    const dados = Object.fromEntries(new FormData(el.querySelector("[data-form-cheque]")));
    dados.valor = parseValor(dados.valor);
    const corpo = Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== "" && v !== null));
    const gravar = () => (enviar ? enviar(corpo) : edicao ? api.put(`/api/cheques/${c.id}`, corpo)
      : api.post("/api/cheques", corpo));
    const enviado = await tentar(gravar, edicao ? "Cheque atualizado." : "Cheque guardado.");
    if (!enviado) return;
    fechar(true);
    await carregarDados();
    window.dispatchEvent(new Event("empresas:atualizar"));
  };
  el.querySelector("[data-form-cheque]").addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
  el.querySelector("[data-excluir]")?.addEventListener("click", async () => {
    if (!await confirmar({ titulo: "Excluir cheque", mensagem: "Excluir este cheque? As notas ligadas a ele voltam a ficar em aberto.",
                           textoConfirmar: "Excluir", perigo: true })) return;
    if (deuCerto(await tentar(() => api.del(`/api/cheques/${c.id}`), "Cheque excluído."))) {
      fechar(true);
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
  });
}

export async function abrirCheque(id) {
  const resposta = await tentar(() => api.get("/api/cheques"));
  const cheque = resposta?.cheques.find((c) => c.id === Number(id));
  if (cheque) formularioCheque(cheque);
}

export async function compensarCheque(id) {
  const resposta = await tentar(() => api.get("/api/cheques"));
  const cheque = resposta?.cheques.find((c) => c.id === Number(id));
  if (!cheque) return;
  const { el, fechar } = abrirModal({
    titulo: `Depósito do cheque ${cheque.numero ? `nº ${cheque.numero}` : `#${cheque.id}`}`,
    corpo: `<p>${esc(cheque.empresa)} · <strong>${brl(cheque.valor)}</strong> · bom para ${dataBR(cheque.vencimento)}</p>
      <form class="grade-campos" data-form-deposito>
        <div class="campo"><label for="d-data">Depositado em</label>
          <input id="d-data" name="data" type="date" class="input" value="${hojeISO()}" required></div>
        <div class="campo"><label for="d-arquivo">Comprovante do depósito (opcional)</label>
          <input id="d-arquivo" name="arquivo" type="file" class="input" accept="application/pdf,image/*,.heic,.heif"></div>
      </form>
      <p class="sutil" style="margin-top:10px">O cheque é compensado, vira um recebimento e as notas ligadas a ele
        recebem baixa. O comprovante fica guardado e aparece em <strong>Comprovantes</strong>.</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Registrar depósito</button>`,
  });
  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const data = el.querySelector("#d-data").value || hojeISO();
    const arquivo = el.querySelector("#d-arquivo").files?.[0];
    let arquivoId = null;
    if (arquivo) {
      const enviado = await tentar(() => api.enviarPara("/api/empresas/arquivo", arquivo));
      if (!enviado) return;
      arquivoId = enviado.id;
    }
    const corpo = { empresa: cheque.empresa, valor: cheque.valor, forma: "Cheque", data, cheque_id: cheque.id,
                    ...(arquivoId ? { arquivo_id: arquivoId } : {}) };
    if (await tentar(() => api.post("/api/recebimentos", corpo), "Depósito registrado: cheque compensado e notas baixadas.")) {
      fechar(true);
      await carregarDados();
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
  });
}

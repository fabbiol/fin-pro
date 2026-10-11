// Empresas e fechamentos · recebimentos (Pix, TED, depósito e cheque) com a baixa das notas.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, esc, hojeISO, parseValor } from "../../ui.js";
import { carregarDados, opcoes, opcoesEmpresa, selo, tentar, vazio } from "./comum.js";
import { FORMAS } from "./estado.js";

export async function htmlRecebimentos() {
  const resposta = await tentar(() => api.get("/api/recebimentos"));
  const lista = (resposta?.recebimentos || []).filter((r) => r.status !== "Cancelado");
  const cancelados = (resposta?.recebimentos || []).filter((r) => r.status === "Cancelado");
  const mes = hojeISO().slice(0, 7);
  return `
    <section class="resumo-lista">
      <div class="resumo-item"><span>Recebido neste mês</span>
        <strong class="ok">${brl(lista.filter((r) => (r.data || "").startsWith(mes)).reduce((s, r) => s + (r.valor || 0), 0))}</strong></div>
      <div class="resumo-item"><span>Recebimentos</span><strong>${lista.length}</strong></div>
      <div class="resumo-acoes">
        <button class="btn btn-sm btn-primario" data-acao="novo-recebimento">${icone("mais", 15)} Registrar recebimento</button>
        <a class="btn btn-sm" href="#/comprovantes?tipo=recebimento">${icone("clipe", 15)} Buscar comprovantes</a>
      </div>
    </section>
    <section class="card tabela-card"><div class="tabela-wrap">${tabela([...lista, ...cancelados])}</div></section>`;
}

function tabela(lista) {
  if (!lista.length) {
    return vazio(icone("pix", 26), "Nenhum recebimento ainda",
                 "Mande o comprovante do Pix, da TED ou do depósito para o bot de notas: a baixa é feita sozinha.");
  }
  return `<table class="tabela">
    <thead><tr><th>Data</th><th>Empresa</th><th>Forma</th><th>Pagador</th><th>Notas</th>
      <th class="num">Valor</th><th>Baixas</th><th>Situação</th><th class="col-acoes"></th></tr></thead>
    <tbody>${lista.map((r) => `<tr class="${r.status === "Cancelado" ? "linha-cancelada" : ""}">
      <td>${dataBR(r.data)}${r.hora ? ` <small class="sutil">${esc(r.hora)}</small>` : ""}</td>
      <td>${esc(r.empresa || "")}</td><td>${esc(r.forma || "")}</td><td>${esc(r.pagador || "")}</td>
      <td>${esc(r.notas || "")}</td><td class="num">${brl(r.valor)}</td>
      <td><small class="sutil">${esc(r.aplicacoes || "—")}</small></td><td>${selo(r.status)}</td>
      <td class="col-acoes">${r.status !== "Cancelado" ? `<button class="btn btn-sm btn-fantasma"
        data-acao="cancelar-recebimento" data-id="${r.id}">${icone("desfazer", 14)} Desfazer</button>` : ""}
        ${r.arquivo ? `<a class="btn-icone btn-sm" href="/${esc(r.arquivo)}" target="_blank" rel="noopener"
          title="Ver comprovante">${icone("clipe", 15)}</a>` : ""}</td></tr>`).join("")}</tbody></table>`;
}

/** Cheque em carteira que bate com o comprovante de depósito: pela CMC-7, pelo número ou (sozinho) pelo valor. */
function chequeSugerido(dados, emCarteira) {
  const lidos = dados.cheques || [];
  const digitos = (v) => String(v || "").replace(/\D/g, "");
  const semZeros = (v) => digitos(v).replace(/^0+/, "");
  for (const lido of lidos) {
    const achado = emCarteira.find((c) => (lido.cmc7 && digitos(c.cmc7) === digitos(lido.cmc7))
      || (lido.numero && semZeros(c.numero) === semZeros(lido.numero)));
    if (achado) return achado;
  }
  const mesmoValor = emCarteira.filter((c) => dados.valor && Math.abs(Number(c.valor) - Number(dados.valor)) < 0.02);
  return dados.deposito_cheque && mesmoValor.length === 1 ? mesmoValor[0] : null;
}

/** ``enviar(corpo)`` troca o registro direto pela confirmação de um comprovante recebido no bot. */
export async function formularioRecebimento(dados = {}, enviar = null) {
  const emCarteira = ((await tentar(() => api.get("/api/cheques", { status: "Em carteira" })))?.cheques) || [];
  const sugerido = chequeSugerido(dados, emCarteira);
  const deposito = Boolean(dados.deposito_cheque || sugerido);
  const { el, fechar } = abrirModal({
    titulo: deposito ? "Depósito de cheque" : "Registrar recebimento",
    corpo: `${deposito ? `<div class="alerta ${sugerido ? "ok" : "aviso"}" style="margin-bottom:12px">${icone(sugerido ? "check" : "alerta", 16)}
        <span>${sugerido ? `Comprovante do depósito do cheque <strong>nº ${esc(sugerido.numero || sugerido.id)}</strong> de
          ${esc(sugerido.empresa)} (${brl(sugerido.valor)}). Ao registrar, o cheque é compensado e as notas dele recebem baixa.`
          : `Comprovante de depósito de cheque${(dados.cheques || []).length ? ` (nº ${esc(dados.cheques.map((c) => c.numero).join(", "))})` : ""}:
            não achei esse cheque em carteira. Escolha o cheque abaixo.`}</span></div>` : ""}
    <form class="grade-campos" data-form-recebimento>
      ${emCarteira.length ? `<div class="campo col-2"><label for="r-cheque">Cheque depositado</label>
        <select id="r-cheque" name="cheque_id" class="input">
          <option value="">Não é depósito de cheque</option>
          ${emCarteira.map((c) => `<option value="${c.id}" ${sugerido?.id === c.id ? "selected" : ""}>
            Nº ${esc(c.numero || "—")} · ${esc(c.empresa)} · ${brl(c.valor)} · bom para ${dataBR(c.vencimento)}</option>`).join("")}
        </select></div>` : ""}
      <div class="campo"><label for="r-empresa">Empresa</label>
        <select id="r-empresa" name="empresa" class="input">${opcoesEmpresa(dados.empresa || "", "Descobrir pela nota fiscal")}</select></div>
      <div class="campo"><label for="r-valor">Valor recebido</label>
        <input id="r-valor" name="valor" class="input" inputmode="decimal" value="${dados.valor ?? ""}" required autofocus></div>
      <div class="campo"><label for="r-forma">Forma</label>
        <select id="r-forma" name="forma" class="input">${opcoes(FORMAS, dados.forma || "Pix")}</select></div>
      <div class="campo"><label for="r-data">Data</label>
        <input id="r-data" name="data" type="date" class="input" value="${dados.data || hojeISO()}"></div>
      <div class="campo"><label for="r-hora">Hora</label>
        <input id="r-hora" name="hora" class="input" value="${esc(dados.hora || "")}" maxlength="5" placeholder="14:35"></div>
      <div class="campo col-2"><label for="r-notas">Notas fiscais pagas</label>
        <input id="r-notas" name="notas" class="input" value="${esc(dados.notas || "")}" maxlength="300" placeholder="6859, 6869"></div>
      <div class="campo col-2"><label for="r-pedidos">Pedidos</label>
        <input id="r-pedidos" name="pedidos" class="input" value="${esc(dados.pedidos || "")}" maxlength="300"></div>
      <div class="campo col-2"><label for="r-pagador">Pagador</label>
        <input id="r-pagador" name="pagador" class="input" value="${esc(dados.pagador || "")}" maxlength="120"></div>
      <div class="campo col-2"><label for="r-id">ID da transação</label>
        <input id="r-id" name="id_transacao" class="input mono" value="${esc(dados.id_transacao || "")}" maxlength="120"></div>
      <div class="campo col-2"><label for="r-obs">Observações</label>
        <input id="r-obs" name="observacoes" class="input" value="${esc(dados.observacoes || "")}" maxlength="300"></div>
    </form>
    <p class="sutil" style="margin-top:10px">Sem o número da nota, o valor baixa as notas mais antigas em aberto da
      empresa. O que sobrar fica como crédito e entra na próxima nota.</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Registrar</button>`,
  });

  const escolhaCheque = el.querySelector("#r-cheque");
  const preencherPeloCheque = () => {
    const cheque = emCarteira.find((c) => String(c.id) === escolhaCheque.value);
    if (!cheque) return;
    el.querySelector("#r-empresa").value = cheque.empresa;
    if (!parseValor(el.querySelector("#r-valor").value)) el.querySelector("#r-valor").value = cheque.valor;
    el.querySelector("#r-forma").value = "Cheque";
  };
  escolhaCheque?.addEventListener("change", preencherPeloCheque);
  if (sugerido) preencherPeloCheque();

  const salvar = async (evento) => {
    evento?.preventDefault();
    const corpo = Object.fromEntries(new FormData(el.querySelector("[data-form-recebimento]")));
    corpo.valor = parseValor(corpo.valor);
    if (corpo.cheque_id) corpo.cheque_id = Number(corpo.cheque_id);
    if (dados.arquivo_id) corpo.arquivo_id = dados.arquivo_id;
    const limpo = Object.fromEntries(Object.entries(corpo).filter(([, v]) => v !== "" && v !== null));
    const resultado = await tentar(() => (enviar ? enviar(limpo) : api.post("/api/recebimentos", limpo)),
                                   "Recebimento registrado.");
    if (!resultado) return;
    fechar(true);
    await carregarDados();
    window.dispatchEvent(new Event("empresas:atualizar"));
  };
  el.querySelector("[data-form-recebimento]").addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

export async function cancelarRecebimento(id) {
  if (!await confirmar({ titulo: "Desfazer recebimento",
                         mensagem: "As notas baixadas por este recebimento voltam a ficar em aberto. Continuar?",
                         textoConfirmar: "Desfazer", perigo: true })) return;
  if (await tentar(() => api.post(`/api/recebimentos/${id}/cancelar`, {}), "Recebimento desfeito.")) {
    await carregarDados();
    window.dispatchEvent(new Event("empresas:atualizar"));
  }
}

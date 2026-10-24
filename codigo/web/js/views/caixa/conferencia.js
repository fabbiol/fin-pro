// Caixa · conferência do que chegou pelo bot do caixa: tudo preenchido, só revisar e lançar.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { brl, confirmar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";
import { formularioLancamento } from "./movimento.js";
import { tela } from "./estado.js";

export async function carregarConferencia() {
  try {
    return await api.get("/api/caixa/bot/entrada");
  } catch {
    return { itens: [], pendentes: 0, config: {} };
  }
}

function completo(d) {
  return Boolean(d.valor && d.descricao && d.centro_custo);
}

export function htmlConferencia(conferencia) {
  const itens = conferencia.itens || [];
  tela.pendentes = conferencia.pendentes || 0;
  tela.conferencia = itens;
  if (!itens.length) {
    return `<section class="card"><div class="vazio"><div class="vazio-icone">${icone("ok", 26)}</div>
      <h3>Nada para revisar</h3><p>Quando alguém mandar a foto de um cupom para o bot do caixa, ele aparece aqui já
      preenchido — valor, onde foi gasto e o centro de custo — para você só conferir e lançar.</p></div></section>`;
  }
  return `<section class="card">
    <header class="caixa-cabecalho">
      <h3>${icone("telegram", 18)} Recebidos pelo bot do caixa <span class="chip info">${itens.length}</span></h3>
      <span class="sutil">Confira e lance, ou descarte.</span>
    </header>
    <ul class="caixa-lista">${itens.map((i) => {
      const d = i.dados || {};
      return `<li data-item-caixa="${esc(i.id)}">
        <span class="caixa-origem" title="Telegram">${icone("telegram", 16)}</span>
        <div class="caixa-info">
          <strong><span class="chip erro">Saída</span> ${d.valor ? brl(d.valor) : "valor não lido"}
            · ${esc(d.descricao || "sem descrição")} · ${d.centro_custo ? esc(d.centro_custo) : `<span class="chip aviso">sem centro de custo</span>`}
            ${i.estado === "conversa" ? `<span class="chip info">respondendo no Telegram</span>` : ""}</strong>
          <span class="sutil">${esc(d.local || "loja não identificada")} · ${dataBR(d.data)}${d.hora ? ` ${esc(d.hora)}` : ""}
            · enviado por ${esc(i.remetente || "—")} em ${dataHoraBR(i.recebido_em)}</span>
          ${i.erro ? `<span class="erro-texto">${icone("alerta", 13)} ${esc(i.erro)}</span>` : ""}
        </div>
        <div class="caixa-acoes">
          ${i.arquivo_id ? `<a class="btn btn-sm btn-fantasma" href="/api/arquivos/${esc(i.arquivo_id)}" target="_blank" rel="noopener">${icone("olho", 14)} Foto</a>` : ""}
          <button class="btn btn-sm" data-acao="revisar-caixa" data-id="${esc(i.id)}">${icone("editar", 14)} Revisar</button>
          ${completo(d) ? `<button class="btn btn-sm btn-primario" data-acao="lancar-caixa" data-id="${esc(i.id)}">${icone("check", 14)} Lançar</button>` : ""}
          <button class="btn btn-sm btn-fantasma" data-acao="descartar-caixa" data-id="${esc(i.id)}">${icone("x", 14)} Descartar</button>
        </div>
      </li>`;
    }).join("")}</ul>
  </section>`;
}

const enviarItem = (id) => (corpo) => api.post(`/api/caixa/bot/entrada/${id}/lancar`, corpo);

export function revisarItem(id) {
  const item = (tela.conferencia || []).find((i) => i.id === id);
  if (item) formularioLancamento({ ...item.dados, movimento: "Saída" }, "Saída", enviarItem(id));
}

const lancando = new Set();  // clique repetido em "Lançar" enquanto o primeiro ainda está indo

export async function lancarItem(id) {
  const item = (tela.conferencia || []).find((i) => i.id === id);
  if (!item || lancando.has(id)) return;
  lancando.add(id);
  try {
    await enviarItem(id)(item.dados);
    toast(`Saída de ${brl(item.dados.valor)} lançada no caixa.`, "ok");
    window.dispatchEvent(new Event("caixa:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  } finally {
    lancando.delete(id);
  }
}

export async function descartarItem(id) {
  if (!await confirmar({ titulo: "Descartar comprovante", mensagem: "Descartar este comprovante? Ele não entra no caixa.",
                         textoConfirmar: "Descartar", perigo: true })) return;
  try {
    await api.post(`/api/caixa/bot/entrada/${id}/descartar`, {});
    toast("Comprovante descartado.", "info");
    window.dispatchEvent(new Event("caixa:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

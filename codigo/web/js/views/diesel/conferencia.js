// Diesel · conferência do que chegou pelo bot: canhotos esperando a máquina e compras para conferir.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { confirmar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";
import { litros, tela } from "./estado.js";
import { formularioCanhoto, formularioCompra } from "./formularios.js";

const ESTADOS = { conversa: ["info", "respondendo no Telegram"], aguardando: ["aviso", "esperando a máquina"],
  pendente: ["aviso", "para conferir"], erro: ["erro", "erro na leitura"] };

export async function carregarConferencia() {
  try {
    return await api.get("/api/diesel/bot/entrada");
  } catch {
    return { itens: [], pendentes: 0, config: {} };
  }
}

export function htmlConferencia(conferencia) {
  const itens = conferencia.itens || [];
  tela.conferencia = itens;
  if (!itens.length) {
    return `<section class="card"><div class="vazio"><div class="vazio-icone">${icone("ok", 26)}</div>
      <h3>Nada para conferir</h3><p>Os canhotos que chegam pelo bot vão para o responsável escolher a máquina no Telegram.
      Os que ficarem sem resposta aparecem aqui para você resolver pela tela.</p></div></section>`;
  }
  return `<section class="card">
    <header class="caixa-cabecalho">
      <h3>${icone("telegram", 18)} Recebidos pelo bot do diesel <span class="chip info">${itens.length}</span></h3>
      <span class="sutil">Escolha a máquina (ou confira a compra) e lance.</span>
    </header>
    <ul class="caixa-lista">${itens.map((i) => {
      const d = i.dados || {};
      const [classe, rotulo] = ESTADOS[i.estado] || ["", i.estado];
      const tipo = d.tipo === "compra" ? "Compra" : d.tipo === "canhoto" ? "Canhoto" : "Não identificado";
      return `<li>
        <span class="caixa-origem" title="Telegram">${icone(d.tipo === "compra" ? "carteira" : "diesel", 16)}</span>
        <div class="caixa-info">
          <strong><span class="chip ${d.tipo === "compra" ? "ok" : "aviso"}">${tipo}</span> ${d.litros ? litros(d.litros) : "litros não lidos"}
            ${(d.itens || []).length > 1 ? ` · ${d.itens.length} combustíveis` : d.combustivel ? ` · ${esc(d.combustivel)}` : ""}
            ${d.maquina ? ` · ${esc(d.maquina)}` : ""} <span class="chip ${classe}">${esc(rotulo)}</span></strong>
          <span class="sutil">${dataBR(d.data)}${d.posto ? ` · ${esc(d.posto)}` : ""}${d.placa ? ` · placa ${esc(d.placa)}` : ""}
            · enviado por ${esc(i.remetente || "—")} em ${dataHoraBR(i.recebido_em)}</span>
          ${i.erro ? `<span class="erro-texto">${icone("alerta", 13)} ${esc(i.erro)}</span>` : ""}
        </div>
        <div class="caixa-acoes">
          ${i.arquivo_id ? `<a class="btn btn-sm btn-fantasma" href="/api/arquivos/${esc(i.arquivo_id)}" target="_blank" rel="noopener">${icone("olho", 14)} Foto</a>` : ""}
          ${d.tipo !== "compra" ? `<button class="btn btn-sm btn-primario" data-acao="conferir-canhoto" data-id="${esc(i.id)}">${icone("check", 14)} Lançar canhoto</button>` : ""}
          ${d.tipo !== "canhoto" ? `<button class="btn btn-sm ${d.tipo === "compra" ? "btn-primario" : ""}" data-acao="conferir-compra" data-id="${esc(i.id)}">${icone("carteira", 14)} Lançar compra</button>` : ""}
          <button class="btn btn-sm btn-fantasma" data-acao="descartar-diesel" data-id="${esc(i.id)}">${icone("x", 14)} Descartar</button>
        </div>
      </li>`;
    }).join("")}</ul>
  </section>`;
}

const enviarItem = (id) => (corpo) => api.post(`/api/diesel/bot/entrada/${id}/lancar`, corpo);

export function conferir(id, tipo) {
  const item = tela.conferencia.find((i) => i.id === id);
  if (!item) return;
  if (tipo === "compra") formularioCompra({ ...item.dados, id: undefined }, enviarItem(id));
  else formularioCanhoto({ ...item.dados, arquivo_id: item.arquivo_id }, enviarItem(id));
}

export async function descartar(id) {
  if (!await confirmar({ titulo: "Descartar arquivo", mensagem: "Descartar este arquivo? Ele não entra no diesel.",
                         textoConfirmar: "Descartar", perigo: true })) return;
  try {
    await api.post(`/api/diesel/bot/entrada/${id}/descartar`, {});
    toast("Arquivo descartado.", "info");
    window.dispatchEvent(new Event("diesel:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

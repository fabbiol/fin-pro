// Empresas e fechamentos · conferência do que o bot de notas recebeu e importação do print do fechamento.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, dataBR, dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";
import { carregarDados, numero, opcoesCompetencia, opcoesEmpresa, tentar, vazio } from "./comum.js";
import { tela } from "./estado.js";
import { formularioCheque } from "./cheques.js";
import { formularioNota } from "./notas.js";
import { formularioRecebimento } from "./recebimentos.js";

const ROTULOS = { nota: "Nota fiscal", cheque: "Cheque", comprovante: "Comprovante", fechamento: "Print de fechamento" };

export async function htmlConferencia() {
  const entrada = await tentar(() => api.get("/api/empresas/entrada"));
  const itens = entrada?.itens || [];
  tela.pendentes = entrada?.pendentes || 0;
  return `
    <section class="card emp-envio">
      <h3>${icone("upload", 18)} Enviar pela tela</h3>
      <p class="sutil">Nota fiscal (XML, PDF ou foto), cheque escaneado, comprovante de Pix/TED/depósito ou o
        <strong>print do fechamento</strong> que já estava em andamento.</p>
      <input type="file" id="emp-arquivo" accept=".xml,.pdf,image/*,.heic,.heif" hidden>
      <div class="emp-soltar" data-acao="enviar-arquivo" role="button" tabindex="0">${icone("scan", 22)}
        <div><strong>Escolher arquivo</strong><div class="sutil">O sistema reconhece sozinho o que é</div></div></div>
    </section>

    <section class="card">
      <h3>${icone("scan", 18)} Aguardando conferência ${itens.length ? `<span class="nav-contador info">${itens.length}</span>` : ""}</h3>
      ${itens.length ? `<ul class="lista-entrada">${itens.map(item).join("")}</ul>`
        : vazio(icone("ok", 26), "Nada para conferir", "Tudo o que chegou pelo bot de notas já foi lançado.")}
    </section>`;
}

function item(i) {
  const dados = i.analise || {};
  const detalhes = i.tipo === "nota"
    ? `NF ${esc(dados.numero_nf || "?")} · ${esc(dados.destinatario?.nome || i.empresa || "empresa não identificada")} · ${brl(dados.valor_total)}`
    : i.tipo === "cheque"
      ? `${esc(dados.banco || "banco não lido")} · ${brl(dados.valor)} · bom para ${dataBR(dados.vencimento) || "?"}`
      : i.tipo === "comprovante"
        ? `${esc(dados.forma || "Pix")} · ${brl(dados.valor)} · ${dataBR(dados.data) || "sem data"}${dados.notas?.length ? ` · NF ${esc(dados.notas.join(", "))}` : ""}`
        : i.tipo === "fechamento"
          ? `${(dados.linhas || []).length} linha(s) · ${brl(dados.total)}`
          : "não reconhecido";
  return `<li data-item="${esc(i.id)}">
    <div class="info">
      <div class="titulo">${icone("arquivo", 15)} ${esc(i.nome_arquivo)} <span class="chip info">${esc(ROTULOS[i.tipo] || "Desconhecido")}</span></div>
      <div class="sutil">${esc(detalhes)}</div>
      <div class="sutil">Recebido ${dataHoraBR(i.recebido_em)}${i.remetente ? ` de ${esc(i.remetente)}` : ""}
        ${i.legenda ? ` · “${esc(i.legenda)}”` : ""}</div>
      ${i.erro ? `<div class="erro">${esc(i.erro)}</div>` : ""}
    </div>
    <div class="acoes">
      ${i.arquivo_id ? `<a class="btn btn-sm btn-fantasma" href="/api/arquivos/${esc(i.arquivo_id)}" target="_blank"
        rel="noopener">${icone("olho", 14)} Ver</a>` : ""}
      <button class="btn btn-sm btn-primario" data-acao="conferir" data-id="${esc(i.id)}">${icone("check", 14)} Conferir</button>
      <button class="btn btn-sm btn-fantasma" data-acao="descartar-item" data-id="${esc(i.id)}">${icone("x", 14)} Descartar</button>
    </div></li>`;
}

// ------------------------------------------------------------------ conferir um item da caixa

export async function conferir(id) {
  const entrada = await tentar(() => api.get("/api/empresas/entrada"));
  const item = entrada?.itens.find((i) => i.id === id);
  if (!item) return;
  const dados = item.analise || {};
  const enviar = (tipo) => async (corpo) => {
    const resultado = await tentar(() => api.post(`/api/empresas/entrada/${id}/confirmar`, { tipo, dados: corpo }),
                                   "Lançado a partir do arquivo recebido.");
    if (resultado) {
      await carregarDados();
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
    return resultado;
  };

  if (item.tipo === "fechamento") {
    importarFechamento(dados, item.empresa, id);
    return;
  }
  if (item.tipo === "cheque") {
    formularioCheque({ ...dados, empresa: item.empresa || "" }, enviar("cheque"));
    return;
  }
  if (item.tipo === "comprovante") {
    formularioRecebimento({ ...dados, empresa: item.empresa || "", notas: (dados.notas || []).join(", "),
                            pedidos: (dados.pedidos || []).join(", ") }, enviar("comprovante"));
    return;
  }
  formularioNota({
    empresa: item.empresa || dados.destinatario?.nome || "",
    data: dados.data || "",
    itens: (dados.itens || []).map((i) => ({ ...i, numero_nf: dados.numero_nf, pedido: i.pedido || (dados.pedidos || [])[0] || "" })),
  }, enviar("nota"));
}

export async function descartarItem(id) {
  if (await tentar(() => api.post(`/api/empresas/entrada/${id}/descartar`, {}), "Arquivo descartado.")) {
    window.dispatchEvent(new Event("empresas:atualizar"));
  }
}

// ------------------------------------------------------------------ arquivo enviado pela tela

export async function enviarArquivo(arquivo) {
  if (!arquivo) return;
  toast(`Lendo ${arquivo.name}…`, "info", { duracao: 2500 });
  let analise;
  try {
    analise = await api.enviarPara("/api/empresas/analisar", arquivo);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return;
  }
  const dados = analise.dados || {};
  if (analise.tipo === "fechamento") {
    importarFechamento(dados, analise.empresa);
  } else if (analise.tipo === "cheque") {
    formularioCheque({ ...dados, empresa: analise.empresa || "" });
  } else if (analise.tipo === "comprovante") {
    formularioRecebimento({ ...dados, empresa: analise.empresa || "", arquivo_id: analise.arquivo?.id,
                            notas: (dados.notas || []).join(", "), pedidos: (dados.pedidos || []).join(", ") });
  } else if (analise.tipo === "nota") {
    formularioNota({ empresa: analise.empresa || dados.destinatario?.nome || "", data: dados.data || "",
                     itens: (dados.itens || []).map((i) => ({ ...i, numero_nf: dados.numero_nf })) });
  } else {
    toast("Não reconheci o arquivo. Ele não parece nota fiscal, cheque, comprovante nem print de fechamento.", "aviso",
          { duracao: 7000 });
  }
}

// ------------------------------------------------------------------ importar o fechamento que já estava em andamento

export function importarFechamento(dados, empresaSugerida = "", itemId = "") {
  const linhas = dados.linhas || [];
  const { el, fechar } = abrirModal({
    titulo: "Importar fechamento já em andamento",
    tamanho: "grande",
    corpo: `<p class="sutil">Confira as linhas lidas do print. Elas entram no fechamento da empresa escolhida, do jeito
        que já estavam — é assim que o módulo começa a operar com o que está em aberto.</p>
      <div class="grade-campos" style="margin:12px 0">
        <div class="campo"><label for="if-empresa">Empresa</label>
          <select id="if-empresa" class="input" required>${opcoesEmpresa(empresaSugerida || dados.empresa || "")}</select></div>
        <div class="campo"><label for="if-comp">Fechamento</label>
          <select id="if-comp" class="input"><option value="">Pela data de cada linha</option>${opcoesCompetencia("")}</select></div>
        <div class="campo"><label>Total lido</label><div class="valor-grande">${brl(dados.total)}</div></div>
      </div>
      <div class="tabela-wrap"><table class="tabela">
        <thead><tr><th class="col-check"><input type="checkbox" data-todas checked></th><th>Data</th><th>Material</th>
          <th>Un.</th><th class="num">Quant.</th><th class="num">Valor uni.</th><th class="num">Valor total</th>
          <th>NF</th><th>Pedido</th></tr></thead>
        <tbody>${linhas.map((l, i) => `<tr>
          <td class="col-check"><input type="checkbox" data-linha="${i}" checked></td>
          <td>${dataBR(l.data)}</td><td>${esc(l.material || "")}</td><td>${esc(l.unidade || "")}</td>
          <td class="num">${numero(l.quantidade)}</td><td class="num">${brl(l.valor_unitario)}</td>
          <td class="num">${brl(l.valor_total)}</td><td>${esc(l.numero_nf || "")}</td><td>${esc(l.pedido || "")}</td>
        </tr>`).join("")}</tbody></table></div>
      ${dados.ignoradas?.length ? `<p class="sutil" style="margin-top:10px">${icone("alerta", 14)}
        ${dados.ignoradas.length} linha(s) não foram entendidas e ficaram de fora:
        <code>${esc(dados.ignoradas.slice(0, 3).join(" | "))}</code></p>` : ""}`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Importar</button>`,
  });

  el.querySelector("[data-todas]").addEventListener("change", (e) => {
    el.querySelectorAll("[data-linha]").forEach((c) => { c.checked = e.target.checked; });
  });
  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const empresa = el.querySelector("#if-empresa").value;
    if (!empresa) {
      toast("Escolha a empresa deste fechamento.", "aviso");
      return;
    }
    const escolhidas = [...el.querySelectorAll("[data-linha]")].filter((c) => c.checked)
      .map((c) => linhas[Number(c.dataset.linha)]);
    if (!escolhidas.length) return;
    const corpo = { empresa, linhas: escolhidas, competencia: el.querySelector("#if-comp").value || null };
    const resultado = await tentar(() => api.post("/api/empresas/importar-fechamento", corpo));
    if (!resultado) return;
    toast(`${resultado.quantidade} linha(s) importada(s) para ${empresa}.`, "ok", { duracao: 5000 });
    if (itemId) await api.post(`/api/empresas/entrada/${itemId}/descartar`, {}).catch(() => {});
    fechar(true);
    await carregarDados();
    // As linhas do print costumam ser de períodos anteriores: abre o fechamento em que elas entraram
    const competencia = resultado.notas?.[0]?.competencia || "";
    const cadastrada = (tela.dados?.cadastro || []).find((c) => c.nome === empresa);
    if (cadastrada) {
      location.hash = `#/empresas?aba=fechamentos&empresa=${cadastrada.id}${competencia ? `&competencia=${competencia}` : ""}`;
    }
    window.dispatchEvent(new Event("empresas:atualizar"));
  });
}

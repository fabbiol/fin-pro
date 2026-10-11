// Janela "Histórico e comprovante" de um boleto ou Pix: quem lançou, quem pagou, comprovante e todas as alterações.
import { api } from "./api.js";
import { icone } from "./icons.js";
import { abrirModal, brl, confirmar, dataBR, dataHoraBR, esc, mensagemErro, toast } from "./ui.js";

const ROTULO = { boletos: "boleto", pix: "Pix" };
const ICONE_ACAO = { "Lançamento": "mais", Pagamento: "check", Cancelamento: "x", Status: "desfazer", "Edição": "editar",
  Comprovante: "clipe", "Exclusão": "lixeira" };

/** Abre o seletor de arquivo e anexa o comprovante. Devolve o registro atualizado ou null. */
export function anexarComprovante(tipo, id) {
  return new Promise((resolve) => {
    const entrada = document.createElement("input");
    entrada.type = "file";
    entrada.accept = "application/pdf,image/*,.heic,.heif";
    entrada.addEventListener("change", async () => {
      const arquivo = entrada.files?.[0];
      if (!arquivo) { resolve(null); return; }
      try {
        toast("Lendo o comprovante…", "info", { duracao: 2500 });
        const registro = await api.enviarPara(`/api/${tipo}/${id}/comprovante`, arquivo);
        const extras = [registro.juros_multa ? `juros/multa ${brl(registro.juros_multa)}` : "", registro.desconto ? `desconto ${brl(registro.desconto)}` : ""]
          .filter(Boolean).join(" · ");
        toast(registro.pendente_gravacao ? "Comprovante guardado: será gravado quando a planilha for fechada."
          : `Comprovante anexado. Pago ${brl(registro.valor_pago || registro.valor)} em ${dataBR(registro.data_pagamento)}${extras ? ` · ${extras}` : ""}.`, "ok", { duracao: 7000 });
        window.dispatchEvent(new Event("gravacao:atualizar"));
        resolve(registro);
      } catch (erro) {
        toast(mensagemErro(erro), "erro", { duracao: 6000 });
        resolve(null);
      }
    });
    entrada.click();
  });
}

function htmlResumo(tipo, r) {
  const nome = tipo === "pix" ? r.recebedor || r.chave_formatada : r.beneficiario;
  return `<div class="det-resumo">
      <div><strong>${esc(nome || "—")}</strong><span class="sutil">${brl(r.valor)} · ${tipo === "pix" ? "data prevista" : "vencimento"} ${dataBR(r.vencimento)}</span></div>
      <span class="chip ${r.status === "Pago" ? "ok" : r.status === "Cancelado" ? "apagado" : ""}">${esc(r.status)}</span>
    </div>
    <dl class="det-autoria">
      <div><dt>Lançado por</dt><dd>${esc(r.lancado_por || "—")}<small>${dataHoraBR(r.data_lancamento)}</small></dd></div>
      <div><dt>Pago por</dt><dd>${r.status === "Pago" ? `${esc(r.pago_por || "—")}<small>${r.data_pagamento ? dataBR(r.data_pagamento) : ""}</small>` : "<span class='sutil'>Ainda não pago</span>"}</dd></div>
      ${r.status === "Pago" ? `<div><dt>Valor pago</dt><dd>${brl(r.valor_pago || r.valor)}<small>${[
        r.juros_multa ? `juros/multa ${brl(r.juros_multa)}` : "", r.desconto ? `desconto ${brl(r.desconto)}` : "",
      ].filter(Boolean).join(" · ") || "sem juros ou desconto"}</small></dd></div>` : ""}
    </dl>`;
}

function htmlComprovante(tipo, r) {
  if (r.id < 0) {
    return `<div class="det-comprovante"><span class="sutil">${icone("relogio", 15)} O comprovante pode ser anexado depois que o lançamento for gravado na planilha.</span></div>`;
  }
  if (r.comprovante) {
    return `<div class="det-comprovante tem">
      ${icone("clipe", 18)}<div class="det-comp-info"><strong>Comprovante de pagamento</strong><span class="sutil">${esc(r.comprovante_nome || "arquivo")}</span></div>
      <a class="btn btn-sm" href="/api/${tipo}/${r.id}/comprovante" target="_blank" rel="noopener">${icone("olho", 14)} Ver</a>
      <button class="btn btn-sm" data-det="anexar">${icone("upload", 14)} Trocar</button>
      <button class="btn-icone perigo" data-det="remover" title="Remover comprovante">${icone("lixeira", 15)}</button>
    </div>`;
  }
  return `<div class="det-comprovante">
    ${icone("clipe", 18)}<div class="det-comp-info"><strong>Sem comprovante</strong>
      <span class="sutil">Opcional: quem pagou anexa o comprovante (PDF ou foto). O sistema lê e marca como pago, com juros e desconto.</span></div>
    <button class="btn btn-sm" data-det="anexar">${icone("upload", 14)} Anexar comprovante</button>
  </div>`;
}

function htmlEventos(eventos, r) {
  if (r.id < 0) return `<p class="sutil">Aguardando gravação na planilha.</p>`;
  if (!eventos) return `<div class="esqueleto" style="height:90px"></div>`;
  if (!eventos.length) return `<p class="sutil">Nenhuma alteração registrada.</p>`;
  return `<ol class="det-linha-tempo">${eventos.map((e) => `<li>
      <span class="det-icone">${icone(ICONE_ACAO[e.acao] || "info", 14)}</span>
      <div><strong>${esc(e.acao)}</strong> <span class="sutil">· ${esc(e.usuario || "sem registro de usuário")} · ${dataHoraBR(e.quando)}</span>
        ${e.detalhes ? `<p>${esc(e.detalhes)}</p>` : ""}</div></li>`).join("")}</ol>`;
}

/** tipo: "boletos" | "pix". aoAlterar é chamado quando o comprovante muda (para recarregar a lista). */
export function abrirDetalhes(tipo, registro, aoAlterar) {
  let r = registro;
  let eventos = null;
  const { el } = abrirModal({
    titulo: `Histórico e comprovante do ${ROTULO[tipo]}${r.id > 0 ? ` #${r.id}` : ""}`,
    tamanho: "lg",
    corpo: `<div data-det-corpo></div>`,
    rodape: `<button class="btn btn-primario" data-fechar>Fechar</button>`,
  });
  const corpo = el.querySelector("[data-det-corpo]");
  const desenhar = () => {
    corpo.innerHTML = `${htmlResumo(tipo, r)}${htmlComprovante(tipo, r)}
      <h4 class="det-titulo">${icone("relogio", 16)} Histórico de alterações</h4>${htmlEventos(eventos, r)}`;
  };
  const carregarEventos = async () => {
    if (r.id < 0) return;
    try {
      eventos = (await api.get(`/api/${tipo}/${r.id}/historico`)).eventos;
    } catch (erro) {
      eventos = [];
      toast(mensagemErro(erro), "erro");
    }
    if (document.body.contains(corpo)) desenhar();
  };
  desenhar();
  carregarEventos();

  corpo.addEventListener("click", async (e) => {
    const botao = e.target.closest("[data-det]");
    if (!botao) return;
    botao.disabled = true;
    try {
      if (botao.dataset.det === "anexar") {
        const novo = await anexarComprovante(tipo, r.id);
        if (novo) r = novo;
      } else if (botao.dataset.det === "remover") {
        if (!(await confirmar({ titulo: "Remover comprovante", mensagem: "Remover o comprovante anexado? O arquivo deixa de aparecer neste lançamento.", textoConfirmar: "Remover", perigo: true }))) return;
        await api.del(`/api/${tipo}/${r.id}/comprovante`);
        r = await api.get(`/api/${tipo}/${r.id}`);
        toast("Comprovante removido.", "info");
      }
      aoAlterar?.();
      window.dispatchEvent(new Event("avisos:atualizar"));
      eventos = null;
      desenhar();
      carregarEventos();
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    } finally {
      botao.disabled = false;
    }
  });
}

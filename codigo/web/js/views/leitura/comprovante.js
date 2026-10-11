// Ler boletos · comprovantes de pagamento lidos na tela.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, seloFonte, tamanhoArquivo,
  toast, uid,
} from "../../ui.js";
import { abrirFormularioPix } from "../pix/index.js";
import { tela } from "./estado.js";
import { carregarCaixa } from "./caixa.js";
import { atualizarItem } from "./render.js";

export function rotuloCandidato(c) {
  const tipo = c.aba === "pix" ? "Pix" : "Boleto";
  const extra = c.status === "Pago" ? " · já pago" : "";
  return `${tipo} #${c.id} · ${c.nome || "sem nome"} · ${brl(c.valor)} · venc. ${dataBR(c.vencimento)}${extra}`;
}

export function htmlEscolhaLancamento(candidatos, origem) {
  if (!candidatos?.length) {
    return `<p class="sutil comp-escolha">Nenhum boleto ou Pix parecido foi encontrado. Abra o lançamento em Boletos lançados
      (botão ${icone("relogio", 12)}) e anexe o comprovante por lá.</p>`;
  }
  return `<label class="comp-escolha"><span class="sutil">${origem === "caixa" ? "De qual lançamento é?" : "Lançamento pago"}</span>
    <select class="input input-sm" data-escolha>${candidatos.map((c) => `<option value="${c.aba}:${c.id}">${esc(rotuloCandidato(c))}</option>`).join("")}</select></label>`;
}

export function textoPagamento(p) {
  if (!p) return "Pagamento registrado.";
  const juros = p.juros_multa ? ` · juros/multa ${brl(p.juros_multa)}` : "";
  const desconto = p.desconto ? ` · desconto ${brl(p.desconto)}` : "";
  return `Pagamento registrado: ${p.nome || "lançamento"} · pago ${brl(p.valor_pago)} em ${dataBR(p.data_pagamento)}${juros}${desconto}`;
}

export function htmlComprovante(item) {
  const c = item.resultado.comprovante;
  const e = c.extraido || {};
  const lidos = [
    ["Valor pago", e.valor_pago != null ? brl(e.valor_pago) : "—"],
    ["Data do pagamento", e.data_pagamento ? dataBR(e.data_pagamento) : "—"],
    ["Valor do documento", e.valor_documento != null ? brl(e.valor_documento) : "—"],
    ["Juros/multa", e.juros_multa ? brl(e.juros_multa) : "—"],
    ["Desconto", e.desconto ? brl(e.desconto) : "—"],
    ["Beneficiário", e.beneficiario ? esc(e.beneficiario) : "—"],
  ].map(([rotulo, valor]) => `<div><dt>${rotulo}</dt><dd>${valor}</dd></div>`).join("");
  const comoBoleto = item.resultado.boletos_do_comprovante?.length
    ? `<button class="btn btn-sm btn-fantasma" data-acao="ler-como-boleto">Não é comprovante? Ler como boleto</button>` : "";

  if (item.pagamento) {
    const p = item.pagamento;
    return `<div class="boleto boleto-lancado comp-registrado">
        <div class="lancado-icone">${icone("check", 20)}</div>
        <div class="lancado-info"><strong>Pagamento registrado · ${p.aba === "pix" ? "Pix" : "Boleto"} #${p.id} ${esc(p.nome || "")}</strong>
          <span>Valor ${brl(p.valor)} · pago ${brl(p.valor_pago)} em ${dataBR(p.data_pagamento)}
            ${p.juros_multa ? ` · juros/multa ${brl(p.juros_multa)}` : ""}${p.desconto ? ` · desconto ${brl(p.desconto)}` : ""}
            ${p.dias_atraso ? ` · ${p.dias_atraso} dia(s) de atraso` : " · em dia"} · comprovante anexado</span></div>
        <a class="btn btn-sm" href="#/${p.aba === "pix" ? "pix" : "boletos"}?q=${encodeURIComponent(p.nome || "")}">Ver na lista ${icone("seta", 14)}</a>
        <button class="btn btn-sm btn-fantasma" data-acao="desfazer-comprovante">${icone("desfazer", 14)} Desfazer</button>
      </div>`;
  }
  return `<div class="comprovante-lido">
      <div class="comp-topo">${icone("clipe", 22)}<div><strong>Comprovante de pagamento</strong>
        <span class="sutil">${e.agendado ? "Atenção: parece um agendamento, não um pagamento efetuado." : c.candidatos?.length > 1
          ? "Confira de qual lançamento é e registre o pagamento." : "Confira e registre o pagamento."}</span></div></div>
      ${e.agendado ? `<div class="alerta aviso">${icone("alerta", 16)}<span>Comprovante de <strong>agendamento</strong>: o pagamento ainda não aconteceu.</span></div>` : ""}
      <dl class="comp-lidos">${lidos}</dl>
      <div class="comp-acoes">${htmlEscolhaLancamento(c.candidatos, "tela")}
        ${c.candidatos?.length ? `<button class="btn btn-primario" data-acao="registrar-comprovante">${icone("check", 16)} Registrar pagamento</button>` : ""}
        ${comoBoleto}</div>
    </div>`;
}

export async function registrarComprovante(item, aba, id) {
  const c = item.resultado.comprovante;
  const resposta = await api.post("/api/comprovantes/registrar", { aba, id, arquivo_id: item.resultado.arquivo?.id, extraido: c.extraido });
  item.pagamento = resposta.pagamento;
  atualizarItem(item);
  toast(textoPagamento(resposta.pagamento), "ok", { duracao: 8000, acao: { rotulo: "Desfazer", executar: () => desfazerComprovante(item) } });
  window.dispatchEvent(new Event("avisos:atualizar"));
  if (item.recebido) carregarCaixa();
}

export async function desfazerComprovante(item) {
  const p = item.pagamento;
  if (!p) return;
  try {
    await api.post(`/api/${p.aba}/${p.id}/desfazer-pagamento`);
    item.pagamento = null;
    item.desfeito = true;
    atualizarItem(item);
    toast("Pagamento desfeito: o lançamento voltou para pendente.", "info");
    window.dispatchEvent(new Event("avisos:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

// Boletos lançados · edição de um boleto.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, compacto, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, isoDeData, mensagemErro, numeroBR,
  parseValor, seloSituacao, toast,
} from "../../ui.js";
import { abrirDetalhes } from "../../detalhes.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { carregar, linha } from "./lista.js";

export function abrirEdicao(r) {
  const { el, fechar } = abrirModal({
    titulo: r.id > 0 ? `Editar boleto #${r.id}` : "Editar lançamento (aguardando gravação)",
    tamanho: "lg",
    corpo: `<form id="form-edicao" class="grade-campos" autocomplete="off">
      <div class="campo col-2"><label for="e-linha">Linha digitável</label>
        <input id="e-linha" class="input mono" name="linha_digitavel" value="${esc(r.linha_digitavel || "")}"></div>
      <div class="campo col-2"><label for="e-benef">Beneficiário</label>
        <input id="e-benef" class="input" name="beneficiario" value="${esc(r.beneficiario || "")}" autofocus></div>
      <div class="campo"><label for="e-doc">CPF/CNPJ do beneficiário</label>
        <input id="e-doc" class="input" name="documento_beneficiario" value="${esc(r.documento_beneficiario || "")}"></div>
      <div class="campo"><label for="e-num">Nº do documento</label>
        <input id="e-num" class="input" name="numero_documento" value="${esc(r.numero_documento || "")}"></div>
      <div class="campo"><label for="e-venc">Vencimento</label>
        <input id="e-venc" type="date" class="input" name="vencimento" value="${esc(r.vencimento || "")}"></div>
      <div class="campo"><label for="e-valor">Valor</label>
        <div class="input-prefixo"><span>R$</span><input id="e-valor" class="input" name="valor" inputmode="decimal" value="${esc(numeroBR(r.valor))}"></div></div>
      <div class="campo"><label for="e-status">Status</label>
        <select id="e-status" class="input" name="status">${["Pendente", "Pago", "Cancelado"].map((s) => `<option ${r.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></div>
      <div class="campo"><label for="e-pag">Data de pagamento</label>
        <input id="e-pag" type="date" class="input" name="data_pagamento" value="${esc(r.data_pagamento || "")}"></div>
      <div class="campo"><label for="e-vpago">Valor pago</label>
        <div class="input-prefixo"><span>R$</span><input id="e-vpago" class="input" name="valor_pago" inputmode="decimal" value="${esc(numeroBR(r.valor_pago))}" placeholder="igual ao valor"></div></div>
      <div class="campo"><label for="e-juros">Juros/multa · Desconto</label>
        <div class="linha-campos"><div class="input-prefixo"><span>+R$</span><input id="e-juros" class="input" name="juros_multa" inputmode="decimal" value="${esc(numeroBR(r.juros_multa))}"></div>
          <div class="input-prefixo"><span>−R$</span><input class="input" name="desconto" inputmode="decimal" value="${esc(numeroBR(r.desconto))}" aria-label="Desconto"></div></div></div>
      <div class="campo col-2"><label for="e-centro">Centro de custo (onde foi gasto)</label>
        <select id="e-centro" class="input" name="centro_custo" data-centro-select>
          <option value="${esc(r.centro_custo || "")}">${esc(r.centro_custo || "Sem centro de custo")}</option></select></div>
      <div class="campo col-2"><label for="e-obs">Observações</label>
        <textarea id="e-obs" class="input" name="observacoes">${esc(r.observacoes || "")}</textarea></div>
      <p class="sutil col-2">Lançado em ${dataHoraBR(r.data_lancamento)}${r.lancado_por ? ` por ${esc(r.lancado_por)}` : ""}${r.pago_por && r.status === "Pago" ? ` · Pago por ${esc(r.pago_por)}` : ""} · Atualizado em ${dataHoraBR(r.atualizado_em)}
        ${r.arquivo ? ` · <a href="/api/boletos/${r.id}/arquivo" target="_blank" rel="noopener">${esc(r.arquivo_nome || "arquivo original")}</a>` : ""}</p>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" id="btn-salvar">${icone("check", 16)} Salvar alterações</button>`,
  });

  const formulario = el.querySelector("#form-edicao");
  const seletorCentro = el.querySelector("#e-centro");
  let centroAnterior = r.centro_custo || "";
  carregarCentros().then((lista) => { seletorCentro.innerHTML = opcoesCentro(lista, centroAnterior); }).catch(() => {});
  seletorCentro.addEventListener("change", async () => { centroAnterior = await tratarNovoCentro(seletorCentro, centroAnterior); });
  const salvar = async (ignorarValidacao = false) => {
    const dados = Object.fromEntries(new FormData(formulario).entries());
    const valor = parseValor(dados.valor);
    const pagamento = ["valor_pago", "juros_multa", "desconto"].map((c) => parseValor(dados[c]));
    if ([valor, ...pagamento].some(Number.isNaN)) { toast("Valor inválido.", "erro"); return; }
    const payload = {
      ...dados,
      valor,
      valor_pago: pagamento[0],
      juros_multa: pagamento[1],
      desconto: pagamento[2],
      vencimento: dados.vencimento || null,
      data_pagamento: dados.data_pagamento || null,
      centro_custo: dados.centro_custo === NOVO_CENTRO ? centroAnterior : (dados.centro_custo || ""),
      ignorar_validacao: ignorarValidacao,
    };
    const botao = el.querySelector("#btn-salvar");
    botao.disabled = true;
    try {
      const salvo = await api.put(`/api/boletos/${r.id}`, payload);
      fechar(true);
      toast(salvo.pendente_gravacao ? "Alterações guardadas: serão gravadas quando a planilha for fechada." : "Alterações salvas na planilha",
        salvo.pendente_gravacao ? "aviso" : "ok");
      window.dispatchEvent(new Event("gravacao:atualizar"));
      window.dispatchEvent(new Event("avisos:atualizar"));
      carregar();
    } catch (erro) {
      botao.disabled = false;
      if (erro.status === 422 && ["linha_invalida", "linha_obrigatoria"].includes(erro.codigo)) {
        const seguir = await confirmar({ titulo: "Linha digitável inválida", mensagem: `${erro.message} Salvar mesmo assim?`, textoConfirmar: "Salvar sem validar", perigo: true });
        if (seguir) salvar(true);
      } else {
        toast(mensagemErro(erro), "erro", { duracao: 6000 });
      }
    }
  };
  el.querySelector("#btn-salvar").addEventListener("click", () => salvar());
  formulario.addEventListener("submit", (e) => { e.preventDefault(); salvar(); });
  el.querySelector("#e-valor").addEventListener("change", (e) => {
    const v = parseValor(e.target.value);
    if (v !== null && Number.isFinite(v)) e.target.value = numeroBR(v);
  });
}

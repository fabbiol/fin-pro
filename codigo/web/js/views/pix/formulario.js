// Pagamentos Pix · formulário de lançamento de Pix (tela e janela).
import { abrirDetalhes } from "../../detalhes.js";
import { api } from "../../api.js";
import { NOVO_CENTRO, carregarCentros, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, hojeISO, mensagemErro, numeroBR, parseValor,
  seloSituacao, toast, uid,
} from "../../ui.js";
import { tela } from "./estado.js";
import { TIPOS_CHAVE, formatarChave, inferirTipo, mascarar, validarChave } from "./chaves.js";
import { linha } from "./lista.js";

/**
 * Formulário de Pix. opcoes: { dados, registro (edição), centros, arquivoId, aoSalvar(registro), aoCancelar, limparAoSalvar }
 */
export function criarFormulario(container, opcoes = {}) {
  const registro = opcoes.registro || null;
  const editar = Boolean(registro);
  const id = uid();
  let centros = opcoes.centros || [];
  let arquivoId = opcoes.arquivoId || null;
  let dados = { tipo_chave: "cpf_cnpj", vencimento: hojeISO(), status: "Pendente", ...(opcoes.dados || {}), ...(registro || {}) };
  if (!TIPOS_CHAVE[dados.tipo_chave]) dados.tipo_chave = "cpf_cnpj";

  const campo = (nome) => container.querySelector(`[name="${nome}"]`);
  const tipoAtual = () => container.querySelector(".tipo-chave .ativo")?.dataset.tipo || dados.tipo_chave || "cpf_cnpj";

  function html() {
    const tipo = dados.tipo_chave;
    const info = TIPOS_CHAVE[tipo];
    const valor = typeof dados.valor === "number" ? numeroBR(dados.valor) : (dados.valor || "");
    const status = editar ? ["Pendente", "Pago", "Cancelado"] : ["Pendente", "Pago"];
    return `<form class="pix-form" novalidate autocomplete="off">
      <div class="campo"><label>Tipo da chave</label>
        <div class="tipo-chave" role="radiogroup" aria-label="Tipo da chave Pix">
          ${Object.entries(TIPOS_CHAVE).map(([chave, t]) => `<button type="button" role="radio" data-tipo="${chave}"
            class="${chave === tipo ? "ativo" : ""}" aria-checked="${chave === tipo}">${icone(t.icone, 15)}<span>${t.rotulo}</span></button>`).join("")}
        </div></div>
      <div class="grade-campos">
        <div class="campo col-2"><label for="${id}-chave">Chave Pix <span class="chave-status" data-status-chave></span></label>
          <input id="${id}-chave" class="input mono" name="chave" value="${esc(formatarChave(tipo, dados.chave))}"
            placeholder="${esc(info.placeholder)}" inputmode="${info.teclado}" spellcheck="false" autocomplete="off"></div>
        <div class="campo"><label for="${id}-valor">Valor do Pix</label>
          <div class="input-prefixo"><span>R$</span><input id="${id}-valor" class="input" name="valor" inputmode="decimal" placeholder="0,00" value="${esc(valor)}"></div></div>
        <div class="campo"><label for="${id}-venc">Data prevista</label>
          <input id="${id}-venc" type="date" class="input" name="vencimento" value="${esc(dados.vencimento || "")}"></div>
        <div class="campo col-2"><label for="${id}-receb">Recebedor</label>
          <input id="${id}-receb" class="input" name="recebedor" maxlength="250" placeholder="Nome da pessoa ou empresa" value="${esc(dados.recebedor || "")}"></div>
        <div class="campo"><label for="${id}-centro">Centro de custo</label>
          <select id="${id}-centro" class="input" name="centro_custo" data-centro-select>${opcoesCentro(centros, dados.centro_custo || "")}</select></div>
        <div class="campo"><label for="${id}-status">Status</label>
          <select id="${id}-status" class="input" name="status">${status.map((s) => `<option ${dados.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        ${editar ? `<div class="campo"><label for="${id}-pag">Data de pagamento</label>
          <input id="${id}-pag" type="date" class="input" name="data_pagamento" value="${esc(dados.data_pagamento || "")}"></div>
        <div class="campo"><label for="${id}-vpago">Valor pago</label>
          <div class="input-prefixo"><span>R$</span><input id="${id}-vpago" class="input" name="valor_pago" inputmode="decimal" value="${esc(numeroBR(dados.valor_pago))}" placeholder="igual ao valor"></div></div>
        <div class="campo"><label for="${id}-juros">Juros/multa · Desconto</label>
          <div class="linha-campos"><div class="input-prefixo"><span>+R$</span><input id="${id}-juros" class="input" name="juros_multa" inputmode="decimal" value="${esc(numeroBR(dados.juros_multa))}"></div>
            <div class="input-prefixo"><span>−R$</span><input class="input" name="desconto" inputmode="decimal" value="${esc(numeroBR(dados.desconto))}" aria-label="Desconto"></div></div></div>` : ""}
        <div class="campo ${editar ? "" : "col-2"}"><label for="${id}-desc">Descrição</label>
          <input id="${id}-desc" class="input" name="descricao" maxlength="500" placeholder="Ex.: pedido, nota fiscal, serviço" value="${esc(dados.descricao || "")}"></div>
        ${editar ? `<div class="campo col-2"><label for="${id}-obs">Observações</label>
          <textarea id="${id}-obs" class="input" name="observacoes">${esc(dados.observacoes || "")}</textarea></div>` : ""}
      </div>
      ${dados.copia_e_cola ? `<div class="alerta ${dados.duplicado ? "aviso" : "info"} pix-copia">${icone("qrcode", 16)}
        <span>Preenchido pelo Pix Copia e Cola${dados.txid ? ` · identificador <code>${esc(dados.txid)}</code>` : ""}${dados.duplicado ? ` · <strong>já lançado (ID ${dados.duplicado.id})</strong>` : ""}</span>
        <span class="espaco"></span><button type="button" class="btn btn-sm btn-fantasma" data-form="remover-copia">${icone("x", 13)} Remover</button></div>` : ""}
      <div class="pix-form-acoes">
        ${opcoes.aoCancelar ? `<button type="button" class="btn btn-fantasma" data-form="cancelar">Cancelar</button>`
          : `<button type="button" class="btn btn-fantasma" data-form="limpar">${icone("x", 15)} Limpar</button>`}
        <span class="espaco"></span>
        <button type="submit" class="btn btn-primario">${icone(editar ? "check" : "pix", 16)} ${editar ? "Salvar alterações" : "Lançar Pix"}</button>
      </div></form>`;
  }

  function render() {
    container.innerHTML = html();
    validarVisual();
  }

  function coletar() {
    const form = container.querySelector("form");
    if (!form) return;
    const valores = Object.fromEntries(new FormData(form).entries());
    dados = { ...dados, ...valores, tipo_chave: tipoAtual() };
  }

  function validarVisual() {
    const alvo = container.querySelector("[data-status-chave]");
    const entrada = campo("chave");
    if (!alvo || !entrada) return;
    const r = entrada.value.trim() ? validarChave(tipoAtual(), entrada.value) : { estado: "", texto: "" };
    alvo.className = `chave-status ${r.estado}`;
    alvo.textContent = r.texto;
    entrada.classList.toggle("baixa-confianca", r.estado === "erro");
  }

  function definirTipo(tipo) {
    container.querySelectorAll("[data-tipo]").forEach((b) => {
      const ativo = b.dataset.tipo === tipo;
      b.classList.toggle("ativo", ativo);
      b.setAttribute("aria-checked", String(ativo));
    });
    dados.tipo_chave = tipo;
    const entrada = campo("chave");
    entrada.placeholder = TIPOS_CHAVE[tipo].placeholder;
    entrada.inputMode = TIPOS_CHAVE[tipo].teclado;
    entrada.value = mascarar(tipo, entrada.value);
    validarVisual();
  }

  function limpar() {
    coletar();
    const centro = dados.centro_custo === NOVO_CENTRO ? "" : dados.centro_custo;
    dados = { tipo_chave: dados.tipo_chave, centro_custo: centro, vencimento: dados.vencimento || hojeISO(), status: "Pendente" };
    arquivoId = null;
    render();
  }

  function preencher(novo, extra = {}) {
    coletar();
    dados = {
      ...dados,
      tipo_chave: TIPOS_CHAVE[novo.tipo_chave] ? novo.tipo_chave : dados.tipo_chave,
      chave: novo.chave || "",
      valor: novo.valor ?? dados.valor,
      recebedor: novo.recebedor || dados.recebedor || "",
      descricao: novo.descricao || dados.descricao || "",
      txid: novo.txid || "",
      copia_e_cola: novo.copia_e_cola || "",
      duplicado: novo.duplicado || null,
    };
    if (extra.arquivoId) arquivoId = extra.arquivoId;
    render();
    (dados.valor ? campo("recebedor") : campo("valor"))?.focus();
  }

  async function lerCodigo(texto) {
    try {
      const lido = await api.post("/api/pix/ler-codigo", { texto: String(texto).trim() });
      if (!lido.crc_valido) {
        toast("Este Pix Copia e Cola está incompleto ou foi alterado. Copie o código de novo.", "erro", { duracao: 7000 });
        return false;
      }
      preencher(lido);
      avisarLido(lido);
      return true;
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
      return false;
    }
  }

  async function salvar(extra = {}) {
    coletar();
    const tipo = tipoAtual();
    const chave = String(dados.chave || "").trim();
    if (!dados.copia_e_cola || chave) {
      const r = validarChave(tipo, chave);
      if (r.estado !== "ok") {
        toast(chave ? `Chave Pix: ${r.texto.toLowerCase()}.` : "Informe a chave Pix.", "erro");
        campo("chave").focus();
        return false;
      }
    }
    const valor = parseValor(dados.valor);
    if (!valor || Number.isNaN(valor) || valor <= 0) {
      toast("Informe o valor do Pix.", "erro");
      campo("valor").focus();
      return false;
    }
    const payload = {
      tipo_chave: chave ? tipo : null,
      chave: chave || null,
      valor,
      vencimento: dados.vencimento || null,
      recebedor: (dados.recebedor || "").trim(),
      centro_custo: dados.centro_custo === NOVO_CENTRO ? "" : (dados.centro_custo || ""),
      descricao: (dados.descricao || "").trim(),
      status: dados.status || "Pendente",
    };
    if (editar) {
      const pagamento = ["valor_pago", "juros_multa", "desconto"].map((c) => parseValor(dados[c]));
      if (pagamento.some(Number.isNaN)) { toast("Valor pago, juros ou desconto inválido.", "erro"); return false; }
      Object.assign(payload, {
        valor_pago: pagamento[0],
        juros_multa: pagamento[1],
        desconto: pagamento[2],
        data_pagamento: dados.data_pagamento || null,
        observacoes: (dados.observacoes || "").trim(),
        copia_e_cola: dados.copia_e_cola || "",
        txid: dados.txid || "",
      });
    } else {
      if (dados.copia_e_cola) payload.copia_e_cola = dados.copia_e_cola;
      if (dados.txid) payload.txid = dados.txid;
      payload.arquivo_id = arquivoId;
      payload.permitir_duplicado = Boolean(extra.permitirDuplicado);
    }
    const botao = container.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      const salvo = editar ? await api.put(`/api/pix/${registro.id}`, payload) : await api.post("/api/pix", payload);
      if (salvo.pendente_gravacao) {
        toast("Pix guardado: a planilha está aberta no Excel e será gravada assim que o arquivo for fechado.", "aviso", { duracao: 7000 });
        window.dispatchEvent(new Event("gravacao:atualizar"));
      } else {
        toast(editar ? "Alterações salvas na planilha" : `Pix lançado na planilha (ID ${salvo.id})`, "ok");
      }
      window.dispatchEvent(new Event("avisos:atualizar"));
      if (!editar && opcoes.limparAoSalvar !== false) limpar();
      opcoes.aoSalvar?.(salvo);
      return true;
    } catch (erro) {
      if (erro.status === 409 && !editar) {
        const seguir = await confirmar({ titulo: "Pix já lançado", mensagem: `${erro.message} Deseja lançar novamente mesmo assim?`, textoConfirmar: "Lançar duplicado" });
        if (seguir) return salvar({ permitirDuplicado: true });
      } else {
        toast(mensagemErro(erro), "erro", { duracao: erro.status === 423 ? 9000 : 6000 });
      }
      return false;
    } finally {
      if (container.contains(botao)) botao.disabled = false;
    }
  }

  container.addEventListener("click", (e) => {
    const botaoTipo = e.target.closest("[data-tipo]");
    if (botaoTipo) {
      definirTipo(botaoTipo.dataset.tipo);
      campo("chave").focus();
      return;
    }
    const acao = e.target.closest("[data-form]")?.dataset.form;
    if (acao === "remover-copia") {
      coletar();
      Object.assign(dados, { copia_e_cola: "", txid: "", duplicado: null });
      render();
    } else if (acao === "limpar") {
      limpar();
    } else if (acao === "cancelar") {
      opcoes.aoCancelar?.();
    }
  });
  container.addEventListener("input", (e) => {
    if (e.target.name !== "chave") return;
    const valor = e.target.value;
    const tipo = tipoAtual();
    if (valor.includes("@") && tipo !== "email") definirTipo("email");
    else if (valor.trim().startsWith("+55") && tipo !== "celular") definirTipo("celular");
    else if ((tipo === "cpf_cnpj" || tipo === "celular") && /[a-z]/i.test(valor) && valor.includes("-")) definirTipo("aleatoria");
    else if (tipo === "cpf_cnpj" || tipo === "celular") e.target.value = mascarar(tipo, valor);
    validarVisual();
  });
  container.addEventListener("paste", (e) => {
    if (e.target.name !== "chave") return;
    const texto = (e.clipboardData?.getData("text") || "").trim();
    if (texto.startsWith("000201")) {
      e.preventDefault();
      lerCodigo(texto);
      return;
    }
    const tipo = inferirTipo(texto);
    if (tipo) {
      e.preventDefault();
      e.target.value = texto;
      definirTipo(tipo);
    }
  });
  container.addEventListener("change", async (e) => {
    const nome = e.target.name;
    if (nome === "valor") {
      const v = parseValor(e.target.value);
      if (v !== null && Number.isFinite(v)) e.target.value = numeroBR(v);
    } else if (nome === "centro_custo") {
      dados.centro_custo = await tratarNovoCentro(e.target, dados.centro_custo || "");
      centros = await carregarCentros().catch(() => centros);
    } else if (nome === "status" && e.target.value === "Pago") {
      const pagamento = campo("data_pagamento");
      if (pagamento && !pagamento.value) pagamento.value = hojeISO();
    }
  });
  container.addEventListener("submit", (e) => {
    e.preventDefault();
    salvar();
  });

  render();
  return { preencher, lerCodigo, limpar };
}

export function avisarLido(lido) {
  if (lido.duplicado) toast(`Atenção: este Pix já foi lançado (ID ${lido.duplicado.id}).`, "aviso", { duracao: 7000 });
  else if (!lido.chave) toast("QR code de cobrança sem chave: confira os dados antes de lançar.", "aviso", { duracao: 6000 });
  else toast("Dados do Pix preenchidos. Confira e lance.", "ok");
}

/** Abre o formulário de Pix numa janela (usado na tela de leitura e na edição). */

export async function abrirFormularioPix(dados = {}, opcoes = {}) {
  const centros = await carregarCentros().catch(() => []);
  const { el, fechar } = abrirModal({
    titulo: opcoes.titulo || (opcoes.registro ? `Editar Pix #${opcoes.registro.id}` : "Lançar pagamento Pix"),
    tamanho: "lg",
    corpo: `<div data-formulario-pix></div>`,
  });
  criarFormulario(el.querySelector("[data-formulario-pix]"), {
    dados,
    centros,
    registro: opcoes.registro || null,
    arquivoId: opcoes.arquivoId,
    limparAoSalvar: false,
    aoSalvar: (salvo) => { fechar(true); opcoes.aoSalvar?.(salvo); },
    aoCancelar: () => fechar(false),
  });
}

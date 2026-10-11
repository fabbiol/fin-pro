// Ler boletos · digitação, cliques e análise com IA.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, seloFonte, tamanhoArquivo,
  toast, uid,
} from "../../ui.js";
import { abrirFormularioPix } from "../pix/index.js";
import { fila, tela } from "./estado.js";
import { carregarCaixa } from "./caixa.js";
import { desfazerComprovante, registrarComprovante } from "./comprovante.js";
import { boletosEmRevisao, formularioDe, localizar, novoBoleto, processarFila } from "./fila.js";
import { lancar, lancarTodos } from "./lancamento.js";
import { atualizarBarra, atualizarBoleto, atualizarItem, renderizarFila } from "./render.js";

export function aoDigitar(e) {
  const campo = e.target.dataset?.campo;
  if (!campo) return;
  const { boleto } = localizar(e.target);
  if (!boleto) return;
  boleto.form[campo] = e.target.value;
  if (campo === "linha_digitavel") boleto.linhaAlterada = true;
}

export async function aoAlterar(e) {
  const campo = e.target.dataset?.campo;
  if (!campo) return;
  const { item, boleto } = localizar(e.target);
  if (!boleto) return;
  if (campo === "centro_custo") {
    boleto.form.centro_custo = await tratarNovoCentro(e.target, boleto.form.centro_custo);
    tela.centros = await carregarCentros().catch(() => tela.centros);
    return;
  }
  boleto.form[campo] = e.target.value;
  if (campo === "valor") {
    const v = parseValor(e.target.value);
    if (v !== null && Number.isFinite(v)) {
      e.target.value = numeroBR(v);
      boleto.form.valor = e.target.value;
    }
  }
  if (campo === "linha_digitavel" && boleto.linhaAlterada) {
    boleto.linhaAlterada = false;
    reanalisarLinha(item, boleto);
  }
  atualizarBarra();
}

export async function aoClicar(e) {
  const alvo = e.target.closest("[data-acao]");
  if (!alvo || !tela.raiz?.contains(alvo)) return;
  const { item, boleto } = localizar(alvo);

  switch (alvo.dataset.acao) {
    case "registrar-comprovante": {
      const [aba, id] = alvo.closest(".comprovante-lido").querySelector("[data-escolha]").value.split(":");
      alvo.disabled = true;
      try {
        await registrarComprovante(item, aba, Number(id));
      } catch (erro) {
        alvo.disabled = false;
        toast(mensagemErro(erro), "erro", { duracao: 6000 });
      }
      return;
    }
    case "desfazer-comprovante": return desfazerComprovante(item);
    case "ler-como-boleto":
      item.boletos = item.resultado.boletos_do_comprovante.map((b) => novoBoleto(b, item.resultado.arquivo));
      item.resultado = { ...item.resultado, comprovante: null };
      renderizarFila();
      return;
    case "lancar": return lancar(item, boleto);
    case "lancar-todos": return lancarTodos();
    case "lancar-pix": {
      const pix = item.resultado.pix[Number(alvo.closest("[data-pix]").dataset.pix)];
      abrirFormularioPix({ ...pix, vencimento: hojeISO() }, {
        arquivoId: item.resultado.arquivo?.id,
        aoSalvar: (registro) => {
          pix.lancado = registro;
          atualizarItem(item);
          if (item.recebido) carregarCaixa();
        },
      });
      return;
    }
    case "centro-todos": {
      const alvos = boletosEmRevisao().filter((b) => b.estado === "revisao");
      if (!alvos.length) return;
      const nome = await escolherCentro({
        titulo: "Centro de custo",
        descricao: `Define onde foi gasto para ${alvos.length === 1 ? "o boleto" : `os ${alvos.length} boletos`} em revisão.`,
      });
      if (nome === null) return;
      alvos.forEach((b) => { b.form.centro_custo = nome; });
      tela.centros = await carregarCentros().catch(() => tela.centros);
      renderizarFila();
      toast(nome ? `Centro de custo "${nome}" aplicado` : "Centro de custo removido", "ok", { duracao: 2500 });
      return;
    }
    case "descartar":
      boleto.estado = "descartado";
      atualizarItem(item);
      return;
    case "ia": return analisarComIA(item, boleto);
    case "ia-arquivo": return analisarArquivoComIA(item);
    case "preencher-manual":
      item.boletos.push(novoBoleto({ campos: {}, alertas: [], codigo: null, confianca: 0, pagina: 0 }, item.resultado?.arquivo || null));
      atualizarItem(item);
      return;
    case "copiar-linha": {
      const digitos = boleto.form.linha_digitavel.replace(/\D/g, "");
      if (digitos) copiar(digitos, "Linha digitável copiada");
      return;
    }
    case "sugestao":
      boleto.form.linha_digitavel = alvo.dataset.valor;
      return reanalisarLinha(item, boleto);
    case "ampliar": return ampliar(boleto);
    case "remover-item":
      item.removido = true;
      renderizarFila();
      return;
    case "tentar-novamente":
      if (!item.arquivo) {
        toast("Envie o arquivo novamente para tentar outra vez.", "info");
        return;
      }
      item.status = "aguardando";
      item.erro = null;
      item.progresso = 0;
      atualizarItem(item);
      processarFila();
      return;
    case "limpar-concluidos":
      fila.forEach((i) => {
        if (i.status === "erro" || (i.status === "concluido" && i.boletos.every((b) => b.estado === "lancado" || b.estado === "descartado"))) i.removido = true;
      });
      renderizarFila();
      return;
    default:
      return;
  }
}

export function ampliar(boleto) {
  const meta = boleto.arquivoMeta;
  const pagina = (boleto.dados.pagina || 0) + 1;
  const conteudo = meta.tipo === "pdf"
    ? `<iframe src="/api/arquivos/${meta.id}#page=${pagina}" title="Boleto"></iframe>`
    : `<img class="previa-grande" src="/api/arquivos/${meta.id}" alt="Boleto">`;
  abrirModal({
    titulo: meta.nome,
    corpo: conteudo,
    tamanho: "xl",
    classeCorpo: "sem-padding",
    rodape: `<a class="btn" href="/api/arquivos/${meta.id}" target="_blank" rel="noopener">${icone("externo", 16)} Abrir em nova aba</a>
             <button class="btn btn-primario" data-fechar>Fechar</button>`,
  });
}

export async function reanalisarLinha(item, boleto) {
  const digitos = boleto.form.linha_digitavel.replace(/\D/g, "");
  if (![44, 47, 48].includes(digitos.length)) {
    boleto.dados = {
      ...boleto.dados,
      codigo: digitos ? { valido: false } : null,
      sugestoes_linha: [],
      alertas: [{ nivel: "erro", codigo: "linha_invalida", mensagem: `A linha tem ${digitos.length} dígitos; o esperado é 47, 48 ou 44 (código de barras).` }],
    };
    atualizarBoleto(item, boleto);
    return;
  }
  try {
    const novo = await api.post("/api/leituras/linha", { linha: digitos });
    const antigos = boleto.dados.campos || {};
    const campos = { ...novo.campos };
    for (const nome of ["beneficiario", "documento_beneficiario", "numero_documento", "vencimento", "valor"]) {
      if (!campos[nome] && antigos[nome]) campos[nome] = antigos[nome];
    }
    const alertasDocumento = (boleto.dados.alertas || []).filter((a) => a.codigo === "ia_observacao");
    boleto.dados = { ...novo, campos, pagina: boleto.dados.pagina, ia_usada: boleto.dados.ia_usada, alertas: [...novo.alertas, ...alertasDocumento] };
    const form = boleto.form;
    form.linha_digitavel = campos.linha_digitavel?.valor || form.linha_digitavel;
    if (novo.campos.vencimento) form.vencimento = novo.campos.vencimento.valor;
    if (novo.campos.valor) form.valor = numeroBR(novo.campos.valor.valor);
    atualizarBoleto(item, boleto);
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
  }
}

export function camposParaIA(boleto) {
  const campos = {};
  const originais = boleto.dados.campos || {};
  for (const [nome, valorForm] of Object.entries(boleto.form)) {
    if (["status", "observacoes"].includes(nome)) continue;
    let valor = valorForm;
    if (nome === "valor") valor = parseValor(valorForm);
    if (valor === "" || valor === null || Number.isNaN(valor)) continue;
    const original = originais[nome];
    const igual = original && String(original.valor) === String(nome === "valor" ? Number(valor) : valor);
    campos[nome] = igual ? original : { valor, fonte: "manual", confianca: 1 };
  }
  return campos;
}

export async function analisarComIA(item, boleto) {
  boleto.estado = "ia";
  atualizarBoleto(item, boleto);
  try {
    const novo = await api.post(`/api/leituras/${boleto.arquivoMeta.id}/ia`, { campos: camposParaIA(boleto), pagina: boleto.dados.pagina || 0 });
    boleto.dados = novo;
    boleto.form = formularioDe(novo, boleto.form);
    toast("Análise com IA concluída. Confira os campos.", "ok");
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
  boleto.estado = "revisao";
  atualizarBoleto(item, boleto);
}

export async function analisarArquivoComIA(item) {
  const botao = tela.raiz?.querySelector(`[data-item="${item.uid}"] [data-acao="ia-arquivo"]`);
  if (botao) { botao.disabled = true; botao.innerHTML = `<span class="spinner"></span> Analisando…`; }
  try {
    const novo = await api.post(`/api/leituras/${item.resultado.arquivo.id}/ia`, { campos: {}, pagina: 0 });
    item.boletos.push(novoBoleto(novo, item.resultado.arquivo));
    toast("Análise com IA concluída. Confira os campos.", "ok");
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
  }
  atualizarItem(item);
}

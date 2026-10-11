// Ler boletos · fila de arquivos e boletos em revisão.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, seloFonte, tamanhoArquivo,
  toast, uid,
} from "../../ui.js";
import { abrirFormularioPix } from "../pix/index.js";
import { EXTENSOES, MAX_PARALELO, fila, tela } from "./estado.js";
import { registrarComprovante } from "./comprovante.js";
import { acompanharTarefa } from "./montagem.js";
import { atualizarItem, atualizarProgresso, renderizarFila } from "./render.js";

export function enfileirar(arquivos) {
  let adicionados = 0;
  for (const arquivo of arquivos) {
    const aceito = arquivo.type === "application/pdf" || arquivo.type.startsWith("image/") || EXTENSOES.test(arquivo.name || "");
    if (!aceito) {
      toast(`${arquivo.name}: formato não suportado`, "erro");
      continue;
    }
    fila.unshift({
      uid: uid(), arquivo, nome: arquivo.name || "imagem-colada.png", tamanho: arquivo.size,
      status: "aguardando", progresso: 0, boletos: [],
    });
    adicionados += 1;
  }
  if (!adicionados) return;
  renderizarFila();
  processarFila();
}

export async function analisarTexto(texto) {
  const digitos = String(texto).replace(/\D/g, "");
  if (digitos.length < 44) {
    toast("Informe pelo menos 44 dígitos.", "aviso");
    return;
  }
  try {
    const dados = await api.post("/api/leituras/linha", { linha: digitos });
    fila.unshift({ uid: uid(), nome: "Linha digitada", manual: true, status: "concluido", boletos: [novoBoleto(dados, null)] });
    renderizarFila();
    const campo = tela.raiz?.querySelector("#entrada-linha");
    if (campo) { campo.value = ""; campo.dispatchEvent(new Event("input")); }
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export function processarFila() {
  while (tela.ativos < MAX_PARALELO) {
    const proximo = [...fila].reverse().find((i) => i.status === "aguardando");
    if (!proximo) break;
    tela.ativos += 1;
    processar(proximo).finally(() => {
      tela.ativos -= 1;
      processarFila();
    });
  }
}

export async function processar(item) {
  item.status = "enviando";
  atualizarItem(item);
  try {
    const tarefa = await api.criarLeitura(item.arquivo, (progresso, terminou) => {
      item.progresso = progresso;
      if (terminou && item.status === "enviando") {
        item.status = "lendo";
        item.inicioLeitura = Date.now();
        atualizarItem(item);
      } else {
        atualizarProgresso(item);
      }
    });
    item.status = "lendo";
    item.inicioLeitura = item.inicioLeitura || Date.now();
    item.tarefa = tarefa;
    atualizarProgresso(item);
    const resultado = await acompanharTarefa(item, tarefa.id);
    item.status = "concluido";
    item.resultado = resultado;
    item.boletos = resultado.boletos.map((b) => novoBoleto(b, resultado.arquivo));
    marcarRepetidosNaFila(item);
    item.arquivo = null;
    const n = item.boletos.length;
    const sugerido = resultado.comprovante?.sugerido;
    if (sugerido && !resultado.comprovante.extraido?.agendado) {
      // Comprovante de um lançamento identificado com segurança: registra o pagamento sozinho (com opção de desfazer)
      atualizarItem(item);
      try {
        await registrarComprovante(item, sugerido.aba, sugerido.id);
      } catch (erro) {
        toast(mensagemErro(erro), "erro", { duracao: 6000 });
      }
      return;
    }
    if (resultado.comprovante) toast(`${item.nome}: comprovante lido — escolha o lançamento`, "info", { duracao: 3000 });
    else if (n) toast(`${item.nome}: ${n === 1 ? "1 boleto lido" : `${n} boletos lidos`}`, "ok", { duracao: 2500 });
    else if (resultado.pix?.length) toast(`${item.nome}: QR code Pix encontrado`, "ok", { duracao: 2500 });
  } catch (erro) {
    item.status = "erro";
    item.erro = mensagemErro(erro);
  }
  atualizarItem(item);
}

/** Avisa quando o mesmo boleto (mesmo código de barras) já está em outro arquivo da fila. */

export function marcarRepetidosNaFila(item) {
  for (const boleto of item.boletos) {
    const chave = boleto.dados.codigo?.valido && boleto.dados.codigo.codigo_barras;
    if (!chave || boleto.dados.duplicado) continue;
    const outro = fila.find((i) => i !== item && !i.removido && i.boletos.some(
      (b) => b.estado !== "descartado" && b.dados.codigo?.codigo_barras === chave,
    ));
    if (outro) {
      boleto.dados.alertas = [
        { nivel: "aviso", codigo: "repetido_fila", mensagem: `Este mesmo boleto também está na fila (arquivo "${outro.nome}").` },
        ...(boleto.dados.alertas || []),
      ];
    }
  }
}

export function novoBoleto(dados, arquivoMeta) {
  return { uid: uid(), dados, arquivoMeta, estado: "revisao", form: formularioDe(dados), registro: null };
}

export function formularioDe(dados, anterior = {}) {
  const c = dados.campos || {};
  return {
    linha_digitavel: c.linha_digitavel?.valor || "",
    beneficiario: c.beneficiario?.valor || "",
    documento_beneficiario: c.documento_beneficiario?.valor || "",
    numero_documento: c.numero_documento?.valor || "",
    vencimento: c.vencimento?.valor || "",
    valor: c.valor?.valor !== undefined && c.valor?.valor !== null ? numeroBR(c.valor.valor) : "",
    status: anterior.status || "Pendente",
    observacoes: anterior.observacoes || "",
    centro_custo: anterior.centro_custo || "",
  };
}

export function localizar(el) {
  const item = fila.find((i) => i.uid === el.closest("[data-item]")?.dataset.item);
  const boleto = item?.boletos.find((b) => b.uid === el.closest("[data-boleto]")?.dataset.boleto);
  return { item, boleto };
}

export function boletosEmRevisao() {
  return fila.flatMap((i) => (i.removido ? [] : i.boletos.filter((b) => b.estado === "revisao" || b.estado === "ia" || b.estado === "lancando")));
}

export function prontoParaLancar(b) {
  const valor = parseValor(b.form.valor);
  return b.estado === "revisao" && b.dados.codigo?.valido && !b.dados.duplicado && b.form.vencimento && valor > 0;
}

export function atualizarContadorNav() {
  const el = document.querySelector("[data-contador-ler]");
  if (!el) return;
  const n = boletosEmRevisao().length + fila.filter((i) => ["aguardando", "enviando", "lendo"].includes(i.status)).length;
  el.textContent = n;
  el.hidden = n === 0;
}

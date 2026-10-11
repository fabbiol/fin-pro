// Ler boletos · lançamento dos boletos na planilha.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { NOVO_CENTRO, carregarCentros, escolherCentro, opcoesCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, esc, hojeISO, mensagemErro, numeroBR, parseValor, seloFonte, tamanhoArquivo,
  toast, uid,
} from "../../ui.js";
import { abrirFormularioPix } from "../pix/index.js";
import { fila } from "./estado.js";
import { carregarCaixa } from "./caixa.js";
import { prontoParaLancar } from "./fila.js";
import { atualizarBoleto } from "./render.js";

export function montarPayload(boleto, opcoes) {
  const f = boleto.form;
  return {
    linha_digitavel: f.linha_digitavel,
    beneficiario: f.beneficiario.trim(),
    documento_beneficiario: f.documento_beneficiario.trim(),
    numero_documento: f.numero_documento.trim(),
    vencimento: f.vencimento || null,
    valor: parseValor(f.valor),
    status: f.status,
    observacoes: f.observacoes.trim(),
    centro_custo: f.centro_custo === NOVO_CENTRO ? "" : f.centro_custo || "",
    arquivo_id: boleto.arquivoMeta?.id || null,
    permitir_duplicado: Boolean(opcoes.permitirDuplicado),
    ignorar_validacao: Boolean(opcoes.ignorarValidacao),
  };
}

export async function lancar(item, boleto, opcoes = {}) {
  const payload = montarPayload(boleto, opcoes);
  if (Number.isNaN(payload.valor)) {
    toast("Valor inválido. Use o formato 1.234,56.", "erro");
    return false;
  }
  if (!opcoes.silencioso && (!payload.vencimento || !payload.valor)) {
    const seguir = await confirmar({
      titulo: "Campos em branco",
      mensagem: `${!payload.vencimento ? "O vencimento" : "O valor"} não foi preenchido. Deseja lançar mesmo assim?`,
      textoConfirmar: "Lançar assim mesmo",
    });
    if (!seguir) return false;
  }

  boleto.estado = "lancando";
  atualizarBoleto(item, boleto);
  try {
    boleto.registro = await api.post("/api/boletos", payload);
    boleto.estado = "lancado";
    if (item.recebido) carregarCaixa();
    if (boleto.registro.pendente_gravacao) {
      toast("Lançamento guardado: a planilha está aberta no Excel. Será gravado assim que o arquivo for fechado.", "aviso", { duracao: 7000 });
      window.dispatchEvent(new Event("gravacao:atualizar"));
    } else if (!opcoes.silencioso) {
      toast(`Boleto lançado na planilha (ID ${boleto.registro.id})`, "ok");
    }
    atualizarBoleto(item, boleto);
    return true;
  } catch (erro) {
    boleto.estado = "revisao";
    if (erro.status === 409 && erro.detalhe?.registro && !boleto.dados.duplicado) {
      const existente = erro.detalhe.registro;
      boleto.dados = {
        ...boleto.dados,
        duplicado: { id: existente.id, data_lancamento: existente.data_lancamento, status: existente.status },
        alertas: [{ nivel: "erro", codigo: "duplicado", mensagem: `${erro.message} Lançado em ${dataHoraBR(existente.data_lancamento)}.` },
          ...(boleto.dados.alertas || [])],
      };
    }
    atualizarBoleto(item, boleto);
    if (opcoes.silencioso) return false;

    if (erro.status === 409) {
      const seguir = await confirmar({
        titulo: "Boleto já lançado",
        mensagem: `${erro.message} Deseja lançar novamente mesmo assim?`,
        textoConfirmar: "Lançar duplicado",
      });
      if (seguir) return lancar(item, boleto, { ...opcoes, permitirDuplicado: true });
    } else if (erro.status === 422 && ["linha_invalida", "linha_obrigatoria"].includes(erro.codigo)) {
      const seguir = await confirmar({
        titulo: "Linha digitável inválida",
        mensagem: `${erro.message} Deseja lançar mesmo assim? O registro ficará sem código de barras validado.`,
        textoConfirmar: "Lançar sem validar",
        perigo: true,
      });
      if (seguir) return lancar(item, boleto, { ...opcoes, ignorarValidacao: true });
    } else {
      toast(mensagemErro(erro), "erro", { duracao: erro.status === 423 ? 9000 : 6000 });
    }
    return false;
  }
}

export async function lancarTodos() {
  const alvos = fila.flatMap((item) => (item.removido ? [] : item.boletos.filter(prontoParaLancar).map((boleto) => ({ item, boleto }))));
  if (!alvos.length) return;
  const payloads = alvos.map(({ boleto }) => montarPayload(boleto, {}));
  alvos.forEach(({ item, boleto }) => { boleto.estado = "lancando"; atualizarBoleto(item, boleto); });

  let resposta;
  try {
    resposta = await api.post("/api/boletos/lote", { boletos: payloads }); // uma única gravação na planilha
  } catch (erro) {
    alvos.forEach(({ item, boleto }) => { boleto.estado = "revisao"; atualizarBoleto(item, boleto); });
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
    return;
  }

  resposta.criados.forEach(({ indice, registro }) => {
    const { item, boleto } = alvos[indice];
    boleto.registro = registro;
    boleto.estado = "lancado";
    atualizarBoleto(item, boleto);
  });
  resposta.erros.forEach((erro) => {
    const { item, boleto } = alvos[erro.indice];
    boleto.estado = "revisao";
    const existente = erro.registro;
    boleto.dados = {
      ...boleto.dados,
      duplicado: erro.codigo === "duplicado" ? { id: existente?.id } : boleto.dados.duplicado,
      alertas: [{ nivel: "erro", codigo: erro.codigo, mensagem: erro.mensagem }, ...(boleto.dados.alertas || [])],
    };
    atualizarBoleto(item, boleto);
  });

  const criados = resposta.criados.length;
  const falhas = resposta.erros.length;
  if (alvos.some(({ item }) => item.recebido)) carregarCaixa();
  if (resposta.pendente_gravacao) {
    toast(`${criados} lançamento(s) guardado(s): a planilha está aberta no Excel e será gravada ao fechar.`, "aviso", { duracao: 7000 });
    window.dispatchEvent(new Event("gravacao:atualizar"));
  } else {
    toast(
      falhas ? `${criados} lançado(s); ${falhas} precisa(m) de atenção.` : `${criados} boleto(s) lançado(s) na planilha.`,
      falhas ? "aviso" : "ok",
      { duracao: 5000 },
    );
  }
}

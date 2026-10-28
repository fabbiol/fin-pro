// Tela: Transferências de clientes — notas pagas por Pix ou TED/DOC que a Operações manda, aguardando o pagamento.
// O dono marca as notas, envia o comprovante (PDF ou foto), confere o que o sistema leu e liga o pagamento às notas.
// Com a API Pix do Bradesco ligada, os Pix recebidos aparecem como sugestões (CNPJ/CPF e valor batem): um clique confirma.
import { api } from "../api.js";
import { icone } from "../icons.js";
import { abrirModal, brl, confirmar, dataBR, dataHoraBR, debounce, esc, mensagemErro, numeroBR, parseValor, toast } from "../ui.js";
import { mascarar } from "./pix/chaves.js";

const FORMAS = { pix: "Pix", transferencia: "TED/DOC" };
const AGUARDANDO = "Aguardando pagamento";
const CLASSE_SITUACAO = { [AGUARDANDO]: "aviso", Pago: "ok" };
const ROTA_PAGAMENTOS = "/api/transferencias/pagamentos";
const ROTA_BRADESCO = "/api/transferencias/bradesco";
const ORIGEM_PIX = "API Pix Bradesco";
const ATUALIZAR_MINUTOS = 10; // ao abrir a tela, busca de novo no Bradesco se a última consulta for mais velha que isso
const filtros = { empresa: "", situacao: "", q: "" };
const selecionadas = new Map(); // id da nota -> linha (para somar os valores)
const pixMarcados = new Map(); // endToEndId -> Pix (casos de conferir, ligados à mão às notas marcadas)
let linhasAtuais = [];
let bradesco = null; // situação da consulta ao Bradesco (ligada ou o motivo) e a última consulta já conciliada
let periodo = null; // { inicio, fim } da consulta
let consultando = false;
let raiz = null;
let requisicao = 0;

// CNPJ pode ter letras desde jul/2026 (12.ABC.345/01DE-35): limpa sem perder as letras.
const documentoLimpo = (d) => String(d || "").toUpperCase().replace(/[^0-9A-Z]/g, "").slice(0, 14);
const documentoBR = (d) => {
  const t = documentoLimpo(d);
  return /[A-Z]/.test(t) ? t.replace(/^(\w{2})(\w{3})(\w{3})(\w{4})(\d{2})$/, "$1.$2.$3/$4-$5") : t ? mascarar("cpf_cnpj", t) : "";
};
const somaDe = (notas) => Math.round(notas.reduce((s, t) => s + Number(t.valor || 0), 0) * 100) / 100;
const liquido = (p) => Math.round((Number(p.valor) - Number(p.devolvido || 0)) * 100) / 100; // o que sobrou depois das devoluções
const somaPix = (pix) => Math.round(pix.reduce((s, p) => s + liquido(p), 0) * 100) / 100;

export async function montar(el) {
  raiz = el;
  selecionadas.clear();
  pixMarcados.clear();
  el.innerHTML = `
    <section class="card barra-filtros">
      <div class="filtros-linha">
        <label class="busca">${icone("busca", 16)}
          <input id="t-busca" class="input" type="search" value="${esc(filtros.q)}" autocomplete="off"
            placeholder="Buscar pelo número da nota" aria-label="Buscar pelo número da nota"></label>
        <select id="t-empresa" class="input input-sm" aria-label="Cliente"><option value="">Todos os clientes</option></select>
        <select id="t-situacao" class="input input-sm" aria-label="Situação"><option value="">Todas as situações</option></select>
      </div>
    </section>
    <section class="resumo-lista" id="t-resumo"></section>
    <section class="card bp-cartao" id="t-bradesco" hidden></section>
    <section class="card tabela-card">
      <div class="acoes-lote lp-lote" id="t-lote" hidden></div>
      <div class="tabela-wrap" id="t-tabela"><div style="padding:18px">${'<div class="esqueleto" style="height:44px;margin-bottom:8px"></div>'.repeat(4)}</div></div>
    </section>`;
  el.addEventListener("input", aoDigitar);
  el.addEventListener("change", aoAlterar);
  el.addEventListener("click", aoClicar);
  el.addEventListener("submit", aoEnviar);
  await carregar();
  await iniciarBradesco();
}

export function desmontar() {
  raiz?.removeEventListener("input", aoDigitar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("submit", aoEnviar);
  raiz = null;
}

function aoDigitar(e) {
  if (e.target.id !== "t-busca") return;
  filtros.q = e.target.value;
  recarregar();
}

function aoAlterar(e) {
  const pix = e.target.dataset?.marcarPix;
  if (pix) {
    const achado = todosOsPix().find((p) => p.e2e === pix);
    if (e.target.checked && achado) pixMarcados.set(pix, achado);
    else pixMarcados.delete(pix);
    desenharLote();
    return;
  }
  if (e.target.id === "bp-inicio" || e.target.id === "bp-fim") {
    periodo = { ...periodo, [e.target.id === "bp-inicio" ? "inicio" : "fim"]: e.target.value };
    return;
  }
  const marcar = e.target.dataset?.marcar;
  if (marcar) {
    const alvos = marcar === "todos" ? linhasAtuais.filter((t) => t.status === AGUARDANDO) : linhasAtuais.filter((t) => String(t.id) === marcar);
    alvos.forEach((t) => (e.target.checked ? selecionadas.set(t.id, t) : selecionadas.delete(t.id)));
    if (marcar === "todos") desenharTabela(linhasAtuais);
    else e.target.closest("tr").classList.toggle("selecionado", e.target.checked);
    desenharLote();
    desenharBradesco();
    return;
  }
  if (e.target.id === "t-empresa") filtros.empresa = e.target.value;
  else if (e.target.id === "t-situacao") filtros.situacao = e.target.value;
  else return;
  selecionadas.clear();
  carregar();
}

async function aoClicar(e) {
  const botao = e.target.closest("[data-acao]");
  if (!botao) return;
  const acao = botao.dataset.acao;
  if (acao === "limpar") {
    selecionadas.clear();
    pixMarcados.clear();
    desenharTabela(linhasAtuais);
    desenharLote();
    desenharBradesco();
  } else if (acao === "ligar") {
    abrirLigar([...selecionadas.values()]);
  } else if (acao === "ligar-pix") {
    ligarPixMarcados(botao);
  } else if (acao === "bp-confirmar") {
    confirmarSugestao(bradesco?.consulta?.sugestoes?.[Number(botao.dataset.i)], botao);
  } else if (acao === "bp-nota") {
    const nota = todasAsCandidatas().find((n) => String(n.id) === botao.dataset.id);
    if (!nota) return;
    if (selecionadas.has(nota.id)) selecionadas.delete(nota.id);
    else selecionadas.set(nota.id, linhasAtuais.find((t) => t.id === nota.id) || nota);
    desenharTabela(linhasAtuais);
    desenharLote();
    desenharBradesco();
  } else if (acao === "desfazer" || acao === "excluir") {
    const linha = linhasAtuais.find((t) => String(t.id) === botao.dataset.id);
    if (!linha || (acao === "desfazer" && !linha.pagamento)) return;
    botao.disabled = true;
    try {
      await (acao === "desfazer" ? desfazer(linha.pagamento) : excluir(linha));
    } finally {
      botao.disabled = false;
    }
  }
}

const recarregar = debounce(() => { selecionadas.clear(); carregar(); }, 350);

async function carregar() {
  if (!raiz) return;
  const minha = ++requisicao;
  const params = Object.fromEntries(Object.entries(filtros).filter(([, v]) => v));
  try {
    const dados = await api.get("/api/transferencias", params);
    if (!raiz || minha !== requisicao) return;
    preencherOpcoes("#t-empresa", dados.empresas, filtros.empresa);
    preencherOpcoes("#t-situacao", dados.situacoes, filtros.situacao);
    raiz.querySelector("#t-resumo").innerHTML = `
      <div class="card resumo-item"><span>Notas</span><strong>${dados.total}</strong></div>
      <div class="card resumo-item"><span>Valor somado</span><strong>${brl(dados.valor)}</strong></div>`;
    linhasAtuais = dados.transferencias;
    // a seleção fica só com as notas que ainda estão na lista e aguardando pagamento
    const marcadas = new Set(selecionadas.keys());
    selecionadas.clear();
    linhasAtuais.forEach((t) => { if (marcadas.has(t.id) && t.status === AGUARDANDO) selecionadas.set(t.id, t); });
    desenharTabela(linhasAtuais);
    desenharLote();
    if (bradesco?.consulta) atualizarBradesco(); // a nota pode ter sido paga ou desfeita: as sugestões mudam
  } catch (erro) {
    if (!raiz) return;
    raiz.querySelector("#t-tabela").innerHTML = `<div class="vazio"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível carregar as transferências</h3><p>${esc(mensagemErro(erro))}</p></div>`;
  }
}

function preencherOpcoes(seletor, valores, escolhido) {
  const select = raiz.querySelector(seletor);
  const primeira = select.options[0].outerHTML;
  select.innerHTML = primeira + valores.map((v) => `<option value="${esc(v)}" ${v === escolhido ? "selected" : ""}>${esc(v)}</option>`).join("");
}

function desenharLote() {
  const barra = raiz.querySelector("#t-lote");
  const notas = [...selecionadas.values()];
  const pix = [...pixMarcados.values()];
  barra.hidden = !notas.length && !pix.length;
  const textoNotas = notas.length === 1 ? "1 nota marcada" : `${notas.length} notas marcadas`;
  const textoPix = pix.length === 1 ? "1 Pix marcado" : `${pix.length} Pix marcados`;
  barra.innerHTML = `<span>${notas.length ? `${textoNotas} · ${brl(somaDe(notas))}` : "Marque as notas que o Pix paga"}${pix.length ? ` · ${textoPix} · ${brl(somaPix(pix))}` : ""}</span>
    ${pix.length
      ? `<button class="btn btn-sm btn-primario" data-acao="ligar-pix" ${notas.length ? "" : "disabled"}
          title="${notas.length ? "Ligar os Pix marcados às notas marcadas" : "Marque também as notas que estes Pix pagam"}">${icone("banco", 14)} Ligar aos Pix marcados</button>`
      : ""}
    ${notas.length ? `<button class="btn btn-sm ${pix.length ? "" : "btn-primario"}" data-acao="ligar">${icone("clipe", 14)} Ligar pagamento</button>` : ""}
    <button class="btn btn-sm btn-fantasma" data-acao="limpar">Limpar seleção</button>`;
}

function celulaSituacao(t) {
  const p = t.pagamento;
  const outras = (p?.notas || []).filter((n) => n !== t.nota);
  const detalhe = p
    ? `<small class="por-quem">${brl(p.valor)} em ${dataBR(p.data)}${p.pagador ? ` · ${esc(p.pagador)}` : ""}</small>
       ${p.origem === ORIGEM_PIX ? `<small class="por-quem" title="endToEndId: ${esc(p.id_transacao)}">Pix confirmado pelo Bradesco</small>` : ""}
       ${outras.length ? `<small class="por-quem">Junto com ${outras.length === 1 ? "a nota" : "as notas"} ${esc(outras.join(", "))}</small>` : ""}`
    : "";
  const titulo = p ? ` title="Ligado por ${esc(p.ligado_por || "—")} em ${esc(dataHoraBR(p.ligado_em))}"` : "";
  return `<td data-rotulo="Situação" class="lp-situacao"><span class="chip ${CLASSE_SITUACAO[t.status] || ""}"${titulo}>${esc(t.status)}</span>${detalhe}</td>`;
}

function celulaAcoes(t) {
  const p = t.pagamento;
  if (!p) {
    return `<td class="col-acoes">${t.status === AGUARDANDO
      ? `<button class="btn-icone" data-acao="excluir" data-id="${t.id}" title="Excluir a nota (mandada por engano, cancelada…)"
          aria-label="Excluir a nota ${esc(t.nota)}">${icone("lixeira", 16)}</button>` : ""}</td>`;
  }
  return `<td class="col-acoes">
    ${p.comprovante ? `<a class="btn-icone marcado" href="${ROTA_PAGAMENTOS}/${p.id}/comprovante" target="_blank" rel="noopener"
        title="Abrir o comprovante do pagamento" aria-label="Abrir o comprovante do pagamento da nota ${esc(t.nota)}">${icone("clipe", 16)}</a>` : ""}
    <button class="btn-icone" data-acao="desfazer" data-id="${t.id}" title="Desfazer o pagamento (volta para Aguardando pagamento)"
      aria-label="Desfazer o pagamento da nota ${esc(t.nota)}">${icone("desfazer", 16)}</button></td>`;
}

function desenharTabela(linhas) {
  const alvo = raiz.querySelector("#t-tabela");
  if (!linhas.length) {
    const filtrando = filtros.empresa || filtros.situacao || filtros.q;
    alvo.innerHTML = `<div class="vazio"><div class="vazio-icone">${icone(filtrando ? "busca" : "banco", 26)}</div>
      <h3>${filtrando ? "Nenhuma nota com estes filtros" : "Nenhuma transferência ainda"}</h3>
      <p>${filtrando ? "Mude a busca ou os filtros." : "As notas pagas por Pix ou TED/DOC chegam sozinhas da Operações."}</p></div>`;
    return;
  }
  const marcaveis = linhas.filter((t) => t.status === AGUARDANDO);
  const todas = marcaveis.length > 0 && marcaveis.every((t) => selecionadas.has(t.id));
  alvo.innerHTML = `<table class="tabela">
    <thead><tr><th class="col-check"><input type="checkbox" data-marcar="todos" ${todas ? "checked" : ""} ${marcaveis.length ? "" : "disabled"}
        aria-label="Marcar todas as notas aguardando pagamento"></th>
      <th>Nota</th><th>Pedido</th><th>Cliente</th><th class="num">Valor</th><th>Material</th>
      <th>Emissão</th><th>Forma</th><th>Situação</th><th class="col-acoes">Ações</th></tr></thead>
    <tbody>${linhas.map((t) => `<tr class="${selecionadas.has(t.id) ? "selecionado" : ""}">
      <td class="col-check">${t.status === AGUARDANDO
        ? `<input type="checkbox" data-marcar="${t.id}" ${selecionadas.has(t.id) ? "checked" : ""} aria-label="Marcar a nota ${esc(t.nota)}">` : ""}</td>
      <td data-rotulo="Nota">${t.arquivo
        ? `<a class="lp-link-nota" href="/api/transferencias/${t.id}/pdf" target="_blank" rel="noopener" title="Abrir o PDF da nota ${esc(t.nota)}"><strong>${esc(t.nota)}</strong> ${icone("arquivo", 13)}</a>`
        : `<strong title="Esta nota chegou sem o PDF">${esc(t.nota)}</strong>`}</td>
      <td data-rotulo="Pedido">${esc(t.pedido || "—")}</td>
      <td data-rotulo="Cliente" class="celula-benef"><strong title="${esc(t.empresa)}">${esc(t.empresa)}</strong>${t.documento
        ? `<span class="mono">${esc(documentoBR(t.documento))}</span>` : ""}</td>
      <td class="num" data-rotulo="Valor">${brl(t.valor)}</td>
      <td data-rotulo="Material">${esc(t.material || "—")}</td>
      <td data-rotulo="Emissão">${dataBR(t.emitida_em)}</td>
      <td data-rotulo="Forma">${esc(FORMAS[t.forma] || t.forma)}</td>
      ${celulaSituacao(t)}
      ${celulaAcoes(t)}</tr>`).join("")}</tbody>
  </table>`;
}

// ------------------------------------------------------------------ ligar pagamento

function abrirLigar(notas) {
  if (!notas.length) return;
  const soma = somaDe(notas);
  let lido = null; // resposta da leitura: traz o id do arquivo guardado, usado no confirmar
  let previa = null;
  const { el, fechar } = abrirModal({
    titulo: notas.length === 1 ? `Ligar pagamento à nota ${notas[0].nota}` : `Ligar pagamento a ${notas.length} notas`,
    tamanho: "lg",
    corpo: `
      <ul class="lp-notas">${notas.map((t) => `<li><strong>Nota ${esc(t.nota)}</strong>
        <span class="sutil">${esc(t.empresa)}${t.documento ? ` · ${esc(documentoBR(t.documento))}` : ""}</span><span class="num">${brl(t.valor)}</span></li>`).join("")}
        <li class="lp-soma"><strong>Soma das notas</strong><span></span><span class="num">${brl(soma)}</span></li></ul>
      <div class="det-comprovante" data-lp-envio></div>
      <input type="file" accept="application/pdf,image/*,.heic,.heif" data-lp-arquivo hidden>
      <form class="grade-campos lp-campos" data-lp-form autocomplete="off" hidden>
        <div class="col-2" data-lp-repetido></div>
        <p class="sutil col-2">Confira o que o sistema leu do comprovante e corrija se precisar. Campos em amarelo não foram lidos.</p>
        <div class="campo"><label for="lp-valor">Valor do comprovante</label>
          <div class="input-prefixo"><span>R$</span><input id="lp-valor" class="input" name="valor" inputmode="decimal" required></div></div>
        <div class="campo"><label for="lp-data">Data do pagamento</label>
          <input id="lp-data" type="date" class="input" name="data" required></div>
        <div class="col-2" data-lp-conta aria-live="polite"></div>
        <div class="campo"><label for="lp-pagador">Quem pagou</label>
          <input id="lp-pagador" class="input" name="pagador" maxlength="120"></div>
        <div class="campo"><label for="lp-doc">CNPJ/CPF de quem pagou</label>
          <input id="lp-doc" class="input mono" name="documento_pagador" maxlength="18" autocapitalize="characters"></div>
        <div class="campo col-2"><label for="lp-id">ID da transação</label>
          <input id="lp-id" class="input mono" name="id_transacao" maxlength="100"></div>
        <div class="campo col-2"><label for="lp-obs">Observação (opcional)</label>
          <input id="lp-obs" class="input" name="observacao" maxlength="200"></div>
      </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-lp-confirmar disabled>${icone("check", 16)} Confirmar pagamento</button>`,
    aoFechar: () => {
      document.removeEventListener("paste", aoColar, true);
      window.removeEventListener("arquivos:soltos", aoSoltar);
      if (previa) URL.revokeObjectURL(previa);
    },
  });
  const envio = el.querySelector("[data-lp-envio]");
  const entrada = el.querySelector("[data-lp-arquivo]");
  const formulario = el.querySelector("[data-lp-form]");
  const botaoConfirmar = el.querySelector("[data-lp-confirmar]");
  const campo = (nome) => formulario.elements[nome];

  const desenharEnvio = (situacao, arquivo) => {
    envio.classList.toggle("tem", situacao === "lido");
    if (situacao === "lendo") {
      envio.innerHTML = `${icone("relogio", 18)}<div class="det-comp-info"><strong>Lendo o comprovante…</strong>
        <span class="sutil">${esc(arquivo.name || "imagem colada")}</span></div>`;
    } else if (situacao === "lido") {
      envio.innerHTML = `${icone("clipe", 18)}<div class="det-comp-info"><strong>Comprovante</strong>
        <span class="sutil">${esc(lido.arquivo_nome || arquivo.name || "imagem colada")}</span></div>
        <a class="btn btn-sm" href="${previa}" target="_blank" rel="noopener">${icone("olho", 14)} Ver</a>
        <button class="btn btn-sm" type="button" data-lp-escolher>${icone("upload", 14)} Trocar</button>`;
    } else {
      envio.innerHTML = `${icone("clipe", 18)}<div class="det-comp-info"><strong>Envie o comprovante do pagamento</strong>
        <span class="sutil">PDF ou foto do Pix ou da TED/DOC. Também dá para arrastar o arquivo ou colar com Ctrl+V.</span></div>
        <button class="btn btn-sm btn-primario" type="button" data-lp-escolher>${icone("upload", 14)} Escolher comprovante</button>`;
    }
  };

  const desenharConta = () => {
    const valor = parseValor(campo("valor").value);
    const alvo = el.querySelector("[data-lp-conta]");
    if (valor === null || Number.isNaN(valor)) {
      alvo.innerHTML = `<div class="alerta aviso">${icone("alerta", 16)}<div>Informe o valor do comprovante para comparar com a soma das notas (${brl(soma)}).</div></div>`;
      return;
    }
    const diferenca = Math.round((valor - soma) * 100) / 100;
    alvo.innerHTML = diferenca === 0
      ? `<div class="alerta ok">${icone("ok", 16)}<div>O comprovante (${brl(valor)}) bate com a soma das notas (${brl(soma)}).</div></div>`
      : `<div class="alerta erro">${icone("alerta", 16)}<div><strong>Não bate: diferença de ${brl(Math.abs(diferenca))}.</strong>
          O comprovante tem ${brl(valor)} e as notas somam ${brl(soma)} (${diferenca > 0 ? "pagou a mais" : "pagou a menos"}).
          Confira antes de confirmar.</div></div>`;
  };

  const ler = async (arquivo) => {
    if (!arquivo) return;
    desenharEnvio("lendo", arquivo);
    botaoConfirmar.disabled = true;
    let resposta;
    try {
      resposta = await api.enviarPara(`${ROTA_PAGAMENTOS}/ler`, arquivo);
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
      desenharEnvio(lido ? "lido" : "vazio", arquivo);
      botaoConfirmar.disabled = !lido;
      return;
    }
    if (!document.body.contains(el)) return; // a janela foi fechada durante a leitura
    lido = resposta;
    if (previa) URL.revokeObjectURL(previa);
    previa = URL.createObjectURL(arquivo);
    const valores = { valor: numeroBR(lido.valor), data: lido.data, pagador: lido.pagador,
                      documento_pagador: documentoBR(lido.documento_pagador), id_transacao: lido.id_transacao };
    Object.entries(valores).forEach(([nome, valor]) => {
      campo(nome).value = valor || "";
      campo(nome).classList.toggle("baixa-confianca", !valor);
    });
    formulario.hidden = false;
    desenharEnvio("lido", arquivo);
    desenharConta();
    el.querySelector("[data-lp-repetido]").innerHTML = lido.ja_usado
      ? `<div class="alerta erro">${icone("alerta", 16)}<div>Este comprovante (mesmo ID da transação) já está ligado a outro pagamento.
          Confira se não é repetido.</div></div>` : "";
    botaoConfirmar.disabled = false;
    (lido.valor ? botaoConfirmar : campo("valor")).focus();
  };

  // colar (Ctrl+V) ou arrastar com esta janela aberta: o arquivo é o comprovante, não vai para "Ler boletos"
  function aoColar(e) {
    const arquivo = [...(e.clipboardData?.files || [])][0];
    if (!arquivo) return;
    e.preventDefault();
    e.stopPropagation();
    ler(arquivo);
  }
  function aoSoltar(e) {
    e.preventDefault();
    ler(e.detail[0]);
  }
  document.addEventListener("paste", aoColar, true);
  window.addEventListener("arquivos:soltos", aoSoltar);

  envio.addEventListener("click", (e) => { if (e.target.closest("[data-lp-escolher]")) entrada.click(); });
  entrada.addEventListener("change", () => { ler(entrada.files?.[0]); entrada.value = ""; });
  formulario.addEventListener("input", (e) => {
    e.target.classList.remove("baixa-confianca");
    if (e.target.name === "valor") desenharConta();
  });
  campo("documento_pagador").addEventListener("blur", (e) => { e.target.value = documentoBR(e.target.value); });

  const confirmarLigacao = async (e) => {
    e?.preventDefault();
    if (!lido) return;
    const dados = Object.fromEntries(new FormData(formulario).entries());
    const valor = parseValor(dados.valor);
    if (!valor || Number.isNaN(valor) || valor <= 0) { toast("Informe o valor do comprovante.", "erro"); campo("valor").focus(); return; }
    if (!dados.data) { toast("Informe a data do pagamento.", "erro"); campo("data").focus(); return; }
    botaoConfirmar.disabled = true;
    try {
      await api.post(ROTA_PAGAMENTOS, {
        ids: notas.map((t) => t.id), arquivo: lido.arquivo, valor, data: dados.data, pagador: dados.pagador.trim(),
        documento_pagador: documentoLimpo(dados.documento_pagador), id_transacao: dados.id_transacao.trim(), observacao: dados.observacao.trim(),
      });
      notas.forEach((t) => selecionadas.delete(t.id));
      fechar(true);
      toast(notas.length === 1 ? `Pagamento ligado: a nota ${notas[0].nota} está como Pago.` : `Pagamento ligado: as ${notas.length} notas estão como Pago.`, "ok", { duracao: 5000 });
      carregar();
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 7000 });
      botaoConfirmar.disabled = false;
    }
  };
  botaoConfirmar.addEventListener("click", confirmarLigacao);
  formulario.addEventListener("submit", confirmarLigacao);
  desenharEnvio("vazio");
}

async function excluir(t) {
  const ok = await confirmar({
    titulo: "Excluir nota",
    mensagem: `Excluir a nota ${t.nota} (${t.empresa}, ${brl(t.valor)})? Ela sai desta lista e da planilha, e a exclusão fica `
      + "registrada no Histórico. Se a Operações mandar esta nota de novo, ela volta.",
    textoConfirmar: "Excluir",
    perigo: true,
  });
  if (!ok) return;
  try {
    await api.del(`/api/transferencias/${t.id}`);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return;
  }
  selecionadas.delete(t.id);
  toast(`Nota ${t.nota} excluída.`, "info", { duracao: 5000 });
  carregar();
}

async function desfazer(p) {
  const varias = p.notas?.length > 1;
  const ok = await confirmar({
    titulo: "Desfazer pagamento",
    mensagem: `${varias ? `As notas ${p.notas.join(", ")} voltam` : "A nota volta"} para "Aguardando pagamento". `
      + `O pagamento de ${brl(p.valor)} em ${dataBR(p.data)} e o comprovante ficam guardados no histórico.`,
    textoConfirmar: "Desfazer",
    perigo: true,
  });
  if (!ok) return;
  try {
    await api.post(`${ROTA_PAGAMENTOS}/${p.id}/desfazer`);
    toast(varias ? "Pagamento desfeito: as notas voltaram para Aguardando pagamento." : "Pagamento desfeito: a nota voltou para Aguardando pagamento.", "info", { duracao: 5000 });
    carregar();
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

// ------------------------------------------------------------------ Pix recebidos no Bradesco (API Pix)

function todosOsPix() {
  const c = bradesco?.consulta;
  return c ? [...c.sugestoes.flatMap((s) => s.pix), ...c.conferir.map((item) => item.pix), ...c.sem_nota, ...c.ligados] : [];
}

const todasAsCandidatas = () => (bradesco?.consulta?.conferir || []).flatMap((item) => item.candidatas);

async function iniciarBradesco() {
  try {
    bradesco = await api.get(ROTA_BRADESCO);
  } catch (erro) {
    bradesco = { falha: mensagemErro(erro) };
  }
  if (!raiz) return;
  const ultima = bradesco.consulta?.consultado_em;
  const recente = ultima && Date.now() - new Date(ultima).getTime() <= ATUALIZAR_MINUTOS * 60000;
  periodo = recente ? { inicio: bradesco.consulta.inicio, fim: bradesco.consulta.fim } : { inicio: bradesco.inicio, fim: bradesco.fim };
  desenharBradesco();
  if (bradesco.ligado && !recente) consultarBradesco();
}

function aoEnviar(e) {
  if (!e.target.matches("[data-bp-form]")) return;
  e.preventDefault();
  periodo = { inicio: e.target.querySelector("#bp-inicio").value, fim: e.target.querySelector("#bp-fim").value };
  consultarBradesco();
}

async function consultarBradesco() {
  if (!raiz || consultando || !periodo?.inicio || !periodo?.fim) return;
  consultando = true;
  desenharBradesco();
  try {
    const resposta = await api.post(`${ROTA_BRADESCO}/consultar`, periodo);
    bradesco = resposta;
    pixMarcados.clear();
  } catch (erro) {
    bradesco = { ...bradesco, falhaConsulta: mensagemErro(erro) };
  } finally {
    consultando = false;
  }
  desenharBradesco();
  if (raiz) desenharLote();
}

// Depois de ligar ou desfazer: concilia de novo a última consulta, sem chamar o banco.
async function atualizarBradesco() {
  let resposta;
  try {
    resposta = await api.get(ROTA_BRADESCO);
  } catch {
    return;
  }
  if (!raiz || consultando) return;
  bradesco = resposta;
  const livres = new Set([...(resposta.consulta?.conferir || []).map((item) => item.pix.e2e), ...(resposta.consulta?.sem_nota || []).map((p) => p.e2e)]);
  [...pixMarcados.keys()].forEach((e2e) => { if (!livres.has(e2e)) pixMarcados.delete(e2e); });
  desenharBradesco();
  desenharLote();
}

function desenharBradesco() {
  const alvo = raiz?.querySelector("#t-bradesco");
  if (!alvo || !bradesco) return;
  const abertas = new Set([...alvo.querySelectorAll("details[open]")].map((d) => d.dataset.secao));
  alvo.hidden = false;
  const titulo = `<h3>${icone("banco", 18)} Pix recebidos no Bradesco${bradesco.ligado
    ? ` <span class="chip ${bradesco.ambiente === "producao" ? "ok" : "aviso"}">${esc(bradesco.ambiente_nome)}</span>` : ""}</h3>`;
  if (bradesco.falha || !bradesco.ligado) {
    alvo.innerHTML = `<div class="bp-topo">${titulo}</div>
      <div class="alerta ${bradesco.falha ? "erro" : "info"}">${icone(bradesco.falha ? "alerta" : "info", 16)}<div>${esc(bradesco.falha || bradesco.motivo)}
        ${bradesco.falha ? "" : `<br><span class="sutil">Enquanto isso, ligue os pagamentos pelo comprovante, como antes.</span>`}</div></div>`;
    return;
  }
  const c = bradesco.consulta;
  alvo.innerHTML = `
    <div class="bp-topo">${titulo}
      <form class="bp-periodo" data-bp-form>
        <div class="campo"><label for="bp-inicio">De</label>
          <input id="bp-inicio" type="date" class="input input-sm" value="${esc(periodo?.inicio || "")}" required></div>
        <div class="campo"><label for="bp-fim">Até</label>
          <input id="bp-fim" type="date" class="input input-sm" value="${esc(periodo?.fim || "")}" required></div>
        <button class="btn btn-sm btn-primario" ${consultando ? "disabled" : ""}>${icone(consultando ? "relogio" : "atualizar", 14)}
          ${consultando ? "Consultando…" : "Buscar Pix"}</button>
      </form>
    </div>
    <p class="sutil bp-estado" role="status">${esc(textoEstado(c))}</p>
    ${bradesco.falhaConsulta && !consultando ? `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(bradesco.falhaConsulta)}</div></div>` : ""}
    ${c ? secoesBradesco(c, abertas) : ""}`;
}

function textoEstado(c) {
  if (consultando) return "Consultando os Pix recebidos no Bradesco…";
  if (!c) return "Escolha o período e clique em Buscar Pix.";
  return `${c.total} ${c.total === 1 ? "Pix recebido" : "Pix recebidos"} de ${dataBR(c.inicio)} a ${dataBR(c.fim)} · consultado em ${dataHoraBR(c.consultado_em)}.`;
}

function secoesBradesco(c, abertas) {
  if (!c.total) return `<p class="bp-vazio">Nenhum Pix recebido neste período.</p>`;
  const sugestoes = c.sugestoes.length
    ? `<p class="sutil">O CNPJ/CPF de quem pagou e o valor batem com a nota. Confira e confirme: só então a nota vira Pago.</p>
       <ul class="bp-lista">${c.sugestoes.map((s, i) => `<li class="bp-item">
         <div class="bp-lado">${s.pix.map(linhaPix).join("")}</div>
         <span class="bp-seta" aria-hidden="true">${icone("seta", 16)}</span>
         <div class="bp-lado">${s.notas.map(linhaNota).join("")}</div>
         <button class="btn btn-sm btn-primario" data-acao="bp-confirmar" data-i="${i}"
           aria-label="Confirmar o Pix de ${esc(brl(s.valor))} para ${s.notas.length === 1 ? "a nota" : "as notas"} ${esc(s.notas.map((n) => n.nota).join(", "))}">${icone("check", 14)} Confirmar</button></li>`).join("")}</ul>`
    : `<p class="bp-vazio">Nenhuma sugestão: nenhum Pix livre bate certinho com as notas aguardando pagamento.</p>`;
  const conferir = c.conferir.length
    ? `<h4 class="bp-subtitulo">Para conferir <span class="chip aviso">${c.conferir.length}</span></h4>
       <p class="sutil">Sem correspondência exata. Marque o Pix e as notas que ele paga (aqui ou na tabela) e clique em Ligar aos Pix marcados.</p>
       <ul class="bp-lista">${c.conferir.map(itemConferir).join("")}</ul>`
    : "";
  const outros = [
    ["sem_nota", `Pix sem nota parecida (${c.sem_nota.length})`,
      c.sem_nota.map((p) => `<li class="bp-item bp-conferir">${caixaPix(p)}<div class="bp-lado">${linhaPix(p)}</div></li>`)],
    ["ligados", `Pix já ligados a um pagamento (${c.ligados.length})`,
      c.ligados.map((p) => `<li class="bp-item bp-ligado"><div class="bp-lado">${linhaPix(p)}</div><span class="chip ok">Pagamento nº ${p.pagamento_id}</span></li>`)],
  ].filter(([, , itens]) => itens.length).map(([secao, rotulo, itens]) => `<details class="bp-mais" data-secao="${secao}" ${abertas.has(secao) ? "open" : ""}>
      <summary>${rotulo}</summary><ul class="bp-lista">${itens.join("")}</ul></details>`).join("");
  return `<h4 class="bp-subtitulo">Sugestões <span class="chip ok">${c.sugestoes.length}</span></h4>${sugestoes}${conferir}${outros}`;
}

function linhaPix(p) {
  const devolvido = Number(p.devolvido || 0);
  return `<div class="bp-linha" title="endToEndId: ${esc(p.e2e)}">
    <span><strong class="num">${brl(liquido(p))}</strong> <span class="sutil">Pix em ${dataHoraBR(p.horario)}${devolvido
      ? ` · ${brl(p.valor)} com ${brl(devolvido)} devolvido` : ""}</span></span>
    <span class="bp-quem">${esc(p.pagador || "Pagador não informado")}${p.documento ? ` <span class="mono">${esc(documentoBR(p.documento))}</span>` : ""}</span></div>`;
}

function linhaNota(n) {
  return `<div class="bp-linha"><span><strong class="num">${brl(n.valor)}</strong> Nota <strong>${esc(n.nota)}</strong></span>
    <span class="bp-quem">${esc(n.empresa)}${n.documento ? ` <span class="mono">${esc(documentoBR(n.documento))}</span>` : ""}</span></div>`;
}

function caixaPix(p) {
  if (liquido(p) <= 0) return `<span class="bp-caixa"></span>`; // devolvido: não paga nota
  return `<span class="bp-caixa"><input type="checkbox" data-marcar-pix="${esc(p.e2e)}" ${pixMarcados.has(p.e2e) ? "checked" : ""}
    aria-label="Marcar o Pix de ${esc(brl(liquido(p)))} de ${esc(p.pagador || "pagador não informado")}"></span>`;
}

function itemConferir(item) {
  const candidatas = item.candidatas.map((n) => `<button type="button" class="chip-filtro ${selecionadas.has(n.id) ? "ativo" : ""}"
      data-acao="bp-nota" data-id="${n.id}" aria-pressed="${selecionadas.has(n.id)}">Nota ${esc(n.nota)} · ${esc(n.empresa)} · ${brl(n.valor)}</button>`).join("");
  return `<li class="bp-item bp-conferir">${caixaPix(item.pix)}
    <div class="bp-lado">${linhaPix(item.pix)}<span class="bp-motivo">${icone("alerta", 13)} ${esc(item.motivo)}</span>
      ${candidatas ? `<div class="bp-candidatas"><span class="sutil">Pode ser:</span>${candidatas}</div>` : ""}</div></li>`;
}

async function confirmarSugestao(s, botao) {
  if (!s) return;
  botao.disabled = true;
  try {
    await api.post(`${ROTA_PAGAMENTOS}/pix`, { ids: s.notas.map((n) => n.id), pix: s.pix.map((p) => p.e2e) });
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
    botao.disabled = false;
    return;
  }
  s.notas.forEach((n) => selecionadas.delete(n.id));
  toast(s.notas.length === 1 ? `Pix confirmado: a nota ${s.notas[0].nota} está como Pago.`
    : `Pix confirmado: as notas ${s.notas.map((n) => n.nota).join(", ")} estão como Pago.`, "ok", { duracao: 5000 });
  carregar();
}

async function ligarPixMarcados(botao) {
  const notas = [...selecionadas.values()];
  const pix = [...pixMarcados.values()];
  if (!notas.length || !pix.length) return;
  const diferenca = Math.round((somaPix(pix) - somaDe(notas)) * 100) / 100;
  const ok = await confirmar({
    titulo: pix.length === 1 ? "Ligar o Pix às notas marcadas" : `Ligar ${pix.length} Pix às notas marcadas`,
    mensagem: `${pix.length === 1 ? "Pix" : "Pix somados"}: ${brl(somaPix(pix))}. ${notas.length === 1 ? `Nota ${notas[0].nota}` : `Notas ${notas.map((n) => n.nota).join(", ")}`}: ${brl(somaDe(notas))}. `
      + (diferenca === 0 ? "Os valores batem." : `Não bate: diferença de ${brl(Math.abs(diferenca))} (${diferenca > 0 ? "pagou a mais" : "pagou a menos"}).`)
      + ` ${notas.length === 1 ? "A nota vai ficar" : "As notas vão ficar"} como Pago.`,
    textoConfirmar: "Ligar",
  });
  if (!ok) return;
  botao.disabled = true;
  try {
    await api.post(`${ROTA_PAGAMENTOS}/pix`, { ids: notas.map((n) => n.id), pix: pix.map((p) => p.e2e) });
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 7000 });
    botao.disabled = false;
    return;
  }
  selecionadas.clear();
  pixMarcados.clear();
  toast(notas.length === 1 ? `Pix ligado: a nota ${notas[0].nota} está como Pago.` : `Pix ligado: as ${notas.length} notas estão como Pago.`, "ok", { duracao: 5000 });
  carregar();
}

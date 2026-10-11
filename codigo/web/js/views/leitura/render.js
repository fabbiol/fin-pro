// Ler boletos · desenho da fila, dos arquivos e dos boletos em revisão.
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
import { htmlComprovante } from "./comprovante.js";
import { ampliar } from "./eventos.js";
import { atualizarContadorNav, boletosEmRevisao, prontoParaLancar } from "./fila.js";
import { lancar } from "./lancamento.js";
import { textoCronometro } from "./montagem.js";

export function renderizarFila() {
  atualizarContadorNav();
  if (!tela.raiz) return;
  const visiveis = fila.filter((i) => !i.removido);
  tela.raiz.querySelector("#lista-fila").innerHTML = visiveis.map(htmlItem).join("");
  atualizarBarra();
}

export function atualizarItem(item) {
  atualizarContadorNav();
  if (!tela.raiz) return;
  const no = tela.raiz.querySelector(`[data-item="${item.uid}"]`);
  if (!no) { renderizarFila(); return; }
  no.outerHTML = htmlItem(item);
  atualizarBarra();
}

export function atualizarProgresso(item) {
  const no = tela.raiz?.querySelector(`[data-item="${item.uid}"] .item-estado`);
  if (no) no.innerHTML = htmlEstadoItem(item);
}

export function atualizarBoleto(item, boleto) {
  atualizarContadorNav();
  if (!tela.raiz) return;
  const no = tela.raiz.querySelector(`[data-boleto="${boleto.uid}"]`);
  if (!no) { atualizarItem(item); return; }
  no.outerHTML = htmlBoleto(boleto);
  atualizarBarra();
}

export function atualizarBarra() {
  if (!tela.raiz) return;
  const barra = tela.raiz.querySelector("#barra-fila");
  const visiveis = fila.filter((i) => !i.removido);
  barra.hidden = visiveis.length === 0;
  if (barra.hidden) return;
  const revisao = boletosEmRevisao();
  const prontos = revisao.filter(prontoParaLancar);
  const processando = visiveis.filter((i) => ["aguardando", "enviando", "lendo"].includes(i.status)).length;
  const comprovantes = visiveis.filter((i) => i.resultado?.comprovante).length;
  const finalizados = visiveis.filter((i) => i.status === "erro" || (i.status === "concluido" && i.boletos.every((b) => b.estado === "lancado" || b.estado === "descartado"))).length;
  barra.innerHTML = `
    <div><h2>Revisão</h2>
      <p class="sutil">${[
        revisao.length || !comprovantes ? `${revisao.length} boleto(s) para conferir` : "",
        comprovantes ? `${comprovantes} comprovante(s)` : "",
        processando ? `${processando} arquivo(s) em processamento` : "",
      ].filter(Boolean).join(" · ")}</p></div>
    <div class="acoes">
      ${finalizados ? `<button class="btn btn-fantasma" data-acao="limpar-concluidos">${icone("x", 16)} Limpar finalizados</button>` : ""}
      ${revisao.length ? `<button class="btn" data-acao="centro-todos" title="Define onde foi gasto para todos os boletos em revisão">${icone("etiqueta", 16)} Centro de custo</button>` : ""}
      ${!revisao.length && comprovantes ? "" : `<button class="btn btn-primario" data-acao="lancar-todos" ${prontos.length ? "" : "disabled"}
        title="Lança os boletos com linha válida, vencimento e valor preenchidos e que não estão duplicados">
        ${icone("planilha", 16)} Lançar ${prontos.length} pronto${prontos.length === 1 ? "" : "s"}</button>`}
    </div>`;
}

export function htmlEstadoItem(item) {
  switch (item.status) {
    case "aguardando":
      return `<span class="chip">${icone("relogio", 13)} Na fila</span>`;
    case "enviando": {
      const pct = Math.round((item.progresso || 0) * 100);
      return `<div class="progresso"><div class="progresso-barra" style="width:${pct}%"></div></div><span class="sutil">Enviando ${pct}%</span>`;
    }
    case "lendo": {
      const t = item.tarefa;
      const inicio = item.inicioLeitura || Date.now();
      const base = t?.paginas ? `Página ${Math.max(1, t.pagina)} de ${t.paginas} · ${t.descricao}` : t?.descricao || "Lendo o arquivo";
      const pct = t?.percentual ?? 0;
      return `<div class="progresso"><div class="progresso-barra" style="width:${pct}%"></div></div>
        <span class="sutil" data-cronometro="${inicio}" data-base="${esc(base)}">${esc(textoCronometro(inicio, base))}</span>`;
    }
    case "erro":
      return `<span class="chip erro">${icone("erro", 13)} Falhou</span>`;
    default: {
      const n = item.boletos.length;
      if (item.resultado?.comprovante && !n) {
        return `<span class="chip ${item.pagamento ? "ok" : "info"}">${icone(item.pagamento ? "check" : "clipe", 13)} ${item.pagamento ? "Pagamento registrado" : "Comprovante"}</span>`;
      }
      const nPix = item.resultado?.pix?.length || 0;
      if (!n && nPix) return `<span class="chip ok">${icone("pix", 13)} ${nPix === 1 ? "QR code Pix" : `${nPix} QR codes Pix`}</span>`;
      return `<span class="chip ${n ? "ok" : "aviso"}">${icone(n ? "check" : "alerta", 13)} ${n === 1 ? "1 boleto" : `${n} boletos`}</span>
        ${item.resultado?.ocr_usado ? `<span class="chip">OCR</span>` : ""}
        ${item.resultado?.tempo_ms ? `<span class="sutil">${(item.resultado.tempo_ms / 1000).toFixed(1).replace(".", ",")} s</span>` : ""}`;
    }
  }
}

export function htmlItem(item) {
  const iconeArquivo = item.manual ? "teclado" : /\.pdf$/i.test(item.nome) ? "arquivo" : "imagem";
  const detalhes = item.manual
    ? "Digitação manual"
    : [item.origemTexto, tamanhoArquivo(item.tamanho), item.resultado?.paginas > 1 ? `${item.resultado.paginas} páginas` : ""].filter(Boolean).join(" · ");

  let corpo = "";
  if (item.status === "erro") {
    corpo = `<div class="alerta erro">${icone("erro", 16)}<div>${esc(item.erro)}</div></div>`;
  } else if (item.status === "concluido") {
    const ativos = item.boletos.filter((b) => b.estado !== "descartado");
    if (item.resultado?.comprovante && !item.boletos.length) corpo = htmlComprovante(item);
    else if (!item.boletos.length) corpo = item.resultado?.pix?.length ? htmlPixEncontrados(item) : htmlSemBoletos(item);
    else if (!ativos.length) corpo = `<p class="sutil">Boleto(s) descartado(s).</p>`;
    else corpo = ativos.map(htmlBoleto).join("");
    const avisos = item.resultado?.avisos || [];
    if (avisos.length) corpo = avisos.map((a) => `<div class="alerta aviso">${icone("alerta", 16)}<span>${esc(a)}</span></div>`).join("") + corpo;
  } else {
    corpo = `<div class="item-carregando"><div class="esqueleto previa"></div>
      <div class="linhas">${'<div class="esqueleto" style="height:38px"></div>'.repeat(5)}</div></div>`;
  }

  return `<article class="card item-fila" data-item="${item.uid}">
    <header class="item-cabecalho">
      <div class="item-arquivo">
        <span class="item-icone">${icone(iconeArquivo, 18)}</span>
        <div style="min-width:0"><div class="item-nome" title="${esc(item.nome)}">${esc(item.nome)}</div><div class="sutil">${esc(detalhes)}</div></div>
      </div>
      <div class="item-estado">${htmlEstadoItem(item)}</div>
      ${item.status === "erro" ? `<button class="btn btn-sm" data-acao="tentar-novamente">${icone("atualizar", 14)} Tentar de novo</button>` : ""}
      <button class="btn-icone" data-acao="remover-item" title="Remover da lista">${icone("x", 16)}</button>
    </header>
    <div class="item-corpo">${corpo}</div>
  </article>`;
}

export function htmlSemBoletos(item) {
  const podeIA = estado.status?.ia && item.resultado?.arquivo;
  return `<div class="sem-boletos">${icone("alerta", 22)}
    <div><strong>Nenhum boleto identificado</strong>
      <p>Não encontramos linha digitável, código de barras nem campos de boleto neste arquivo.</p></div>
    <div class="linha-botoes">
      ${podeIA ? `<button class="btn btn-ia" data-acao="ia-arquivo">${icone("ia", 16)} Tentar com IA</button>` : ""}
      <button class="btn" data-acao="preencher-manual">${icone("editar", 16)} Preencher manualmente</button>
    </div></div>`;
}

/** Arquivo sem boleto, mas com QR code Pix: oferece lançar como Pix. */

export function htmlPixEncontrados(item) {
  const blocos = item.resultado.pix.map((p, i) => {
    if (p.lancado) {
      const r = p.lancado;
      return `<div class="boleto boleto-lancado" data-pix="${i}">
        <div class="lancado-icone">${icone(r.pendente_gravacao ? "relogio" : "check", 20)}</div>
        <div class="lancado-info"><strong>${r.pendente_gravacao ? "Pix lançado · aguardando a planilha ser fechada no Excel" : `Pix lançado na planilha · ID ${r.id}`}</strong>
          <span>${esc(r.recebedor || "Sem recebedor")} · ${brl(r.valor)}${r.chave_formatada ? ` · ${esc(r.chave_formatada)}` : ""}</span></div>
        <a class="btn btn-sm" href="#/pix?q=${encodeURIComponent(r.recebedor || r.chave || "")}">Ver na lista ${icone("seta", 14)}</a>
      </div>`;
    }
    return `<div class="pix-encontrado" data-pix="${i}">${icone("qrcode", 26)}
      <div class="info"><strong>QR code Pix encontrado ${p.dinamico ? `<span class="chip">Cobrança</span>` : ""}
          ${p.duplicado ? `<span class="chip erro">Já lançado · ID ${p.duplicado.id}</span>` : ""}</strong>
        <span>${esc(p.recebedor || "Recebedor não informado")} · ${p.valor ? brl(p.valor) : "valor não informado"}${p.chave_formatada ? ` · ${esc(p.chave_formatada)}` : ""}</span></div>
      <button class="btn btn-primario" data-acao="lancar-pix">${icone("pix", 16)} Lançar como Pix</button>
    </div>`;
  }).join("");
  return `${blocos}<p class="sutil pix-nao-e">Não é um Pix?
    <button class="btn btn-sm btn-fantasma" data-acao="preencher-manual">${icone("editar", 14)} Preencher boleto manualmente</button></p>`;
}

export function campoTexto(nome, rotulo, b, classe = "", extras = "") {
  const campo = b.dados.campos?.[nome];
  const baixa = campo && campo.confianca < 0.8 && campo.fonte !== "manual";
  return `<div class="campo ${classe}"><label>${rotulo} ${seloFonte(campo)}</label>
    <input class="input ${baixa ? "baixa-confianca" : ""}" data-campo="${nome}" value="${esc(b.form[nome])}" autocomplete="off" ${extras}></div>`;
}

export function htmlBoleto(b) {
  const d = b.dados;
  const c = d.campos || {};
  const f = b.form;

  if (b.estado === "lancado") {
    const r = b.registro;
    return `<div class="boleto boleto-lancado" data-boleto="${b.uid}">
      <div class="lancado-icone">${icone(r.pendente_gravacao ? "relogio" : "check", 20)}</div>
      <div class="lancado-info"><strong>${r.pendente_gravacao ? "Lançado · aguardando a planilha ser fechada no Excel" : `Lançado na planilha · ID ${r.id}`}</strong>
        <span>${esc(r.beneficiario || "Sem beneficiário")} · ${brl(r.valor)} · vencimento ${dataBR(r.vencimento)}</span></div>
      <a class="btn btn-sm" href="#/boletos?q=${encodeURIComponent(r.linha_digitos || r.beneficiario || "")}">Ver na lista ${icone("seta", 14)}</a>
    </div>`;
  }

  const ocupado = b.estado === "lancando" || b.estado === "ia";
  const codigo = d.codigo;
  const seloLinha = !codigo
    ? `<span class="chip erro">${icone("erro", 12)} Não lida</span>`
    : codigo.valido
      ? `<span class="chip ok">${icone("check", 12)} Válida</span>`
      : `<span class="chip erro">${icone("erro", 12)} Inválida</span>`;
  const alertas = (d.alertas || []).filter((a) => !(a.codigo?.startsWith("ausente_") && String(f[a.codigo.slice(8)] ?? "").trim()));
  const confianca = Math.round((d.confianca || 0) * 100);
  const nivel = confianca >= 90 ? "ok" : confianca >= 70 ? "aviso" : "erro";
  const meta = b.arquivoMeta;
  const pagina = (d.pagina || 0) + 1;
  const previa = meta
    ? meta.tipo === "pdf"
      ? `<iframe src="/api/arquivos/${meta.id}#page=${pagina}&view=FitH&toolbar=0&navpanes=0" title="Prévia do boleto" loading="lazy"></iframe>`
      : `<img src="/api/arquivos/${meta.id}" alt="Prévia do boleto" loading="lazy">`
    : `<div class="previa-vazia">${icone("teclado", 30)}<span>Digitado manualmente</span></div>`;
  const tipo = d.tipo === "arrecadacao" ? "Arrecadação" : d.tipo === "bancario" ? "Bancário" : "";
  const baixaLinha = c.linha_digitavel && c.linha_digitavel.confianca < 0.8;

  return `<div class="boleto ${ocupado ? "ocupado" : ""}" data-boleto="${b.uid}">
    <div class="boleto-previa">${previa}
      ${meta ? `<button class="previa-ampliar" data-acao="ampliar">${icone("olho", 14)} Ampliar</button>` : ""}</div>

    <div class="boleto-dados">
      <div class="boleto-topo">
        <div class="emissor">
          ${d.emissor ? `${icone("banco", 16)} ${esc(d.emissor)}` : `<span class="sutil">Emissor não identificado</span>`}
          ${tipo ? `<span class="chip">${tipo}</span>` : ""}
          ${d.ia_usada ? `<span class="chip ia">${icone("ia", 12)} IA</span>` : ""}
          ${d.pagina ? `<span class="chip">Página ${pagina}</span>` : ""}
        </div>
        <div class="confianca ${nivel}" title="Confiança geral da leitura"><span>Confiança</span>
          <div class="confianca-barra"><div style="width:${confianca}%"></div></div><strong>${confianca}%</strong></div>
      </div>

      <div class="campo campo-linha">
        <label>Linha digitável ${seloLinha} ${seloFonte(c.linha_digitavel)}</label>
        <div class="input-grupo">
          <input class="input ${baixaLinha ? "baixa-confianca" : ""}" data-campo="linha_digitavel" value="${esc(f.linha_digitavel)}"
                 placeholder="Digite ou cole a linha digitável" autocomplete="off" spellcheck="false" inputmode="numeric">
          <button class="btn-icone" data-acao="copiar-linha" title="Copiar somente os números">${icone("copiar", 16)}</button>
        </div>
        ${d.sugestoes_linha?.length ? `<div class="sugestoes"><span>Correções possíveis:</span>
          ${d.sugestoes_linha.map((s) => `<button class="sugestao mono" data-acao="sugestao" data-valor="${esc(s)}">${esc(s)}</button>`).join("")}</div>` : ""}
      </div>

      <div class="grade-campos">
        ${campoTexto("beneficiario", "Beneficiário", b, "col-2")}
        ${campoTexto("documento_beneficiario", "CPF/CNPJ do beneficiário", b)}
        ${campoTexto("numero_documento", "Nº do documento", b)}
        <div class="campo"><label>Vencimento ${seloFonte(c.vencimento)}</label>
          <input type="date" class="input ${c.vencimento && c.vencimento.confianca < 0.8 ? "baixa-confianca" : ""}" data-campo="vencimento" value="${esc(f.vencimento)}"></div>
        <div class="campo"><label>Valor ${seloFonte(c.valor)}</label>
          <div class="input-prefixo"><span>R$</span>
            <input class="input ${c.valor && c.valor.confianca < 0.8 ? "baixa-confianca" : ""}" data-campo="valor" inputmode="decimal" value="${esc(f.valor)}" placeholder="0,00"></div></div>
        <div class="campo"><label>Status</label>
          <select class="input" data-campo="status">${["Pendente", "Pago"].map((s) => `<option ${f.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        <div class="campo"><label>Centro de custo <span class="sutil">(onde foi gasto)</span></label>
          <select class="input" data-campo="centro_custo" data-centro-select>${opcoesCentro(tela.centros, f.centro_custo)}</select></div>
        ${campoTexto("observacoes", "Observações", b, "col-2", 'placeholder="Opcional"')}
      </div>

      ${alertas.length ? `<ul class="alertas">${alertas.map((a) => {
        const classe = a.nivel === "erro" ? "erro" : a.nivel === "aviso" ? "aviso" : "info";
        const nome = a.nivel === "erro" ? "erro" : a.nivel === "aviso" ? "alerta" : "info";
        return `<li class="alerta ${classe}">${icone(nome, 15)}<span>${esc(a.mensagem)}</span></li>`;
      }).join("")}</ul>` : ""}

      <div class="boleto-acoes">
        <button class="btn btn-fantasma" data-acao="descartar" ${ocupado ? "disabled" : ""}>${icone("lixeira", 16)} Descartar</button>
        <span class="espaco"></span>
        ${estado.status?.ia && meta ? `<button class="btn btn-ia" data-acao="ia" ${ocupado ? "disabled" : ""}>
          ${b.estado === "ia" ? `<span class="spinner"></span> Analisando…` : `${icone("ia", 16)} Analisar com IA`}</button>` : ""}
        <button class="btn btn-primario" data-acao="lancar" ${ocupado ? "disabled" : ""}>
          ${b.estado === "lancando" ? `<span class="spinner"></span> Lançando…` : `${icone("planilha", 16)} Lançar na planilha`}</button>
      </div>
    </div>
  </div>`;
}

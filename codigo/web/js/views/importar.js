// Tela: Importar boletos de outro sistema (Excel, CSV ou TXT) — envio, colunas, prévia e importação.
import { api } from "../api.js";
import { bloquearAdmin, estadoAdmin, pedirSenhaAdmin } from "../admin.js";
import { carregarCentros, opcoesCentro, tratarNovoCentro } from "../centros.js";
import { icone } from "../icons.js";
import { brl, confirmar, dataBR, esc, mensagemErro, toast } from "../ui.js";

const ESTADOS = {
  pronto: { rotulo: "Pronto", classe: "ok", filtro: "Prontos" },
  aviso: { rotulo: "Com aviso", classe: "aviso", filtro: "Com aviso" },
  erro: { rotulo: "Com erro", classe: "erro", filtro: "Com erro" },
  duplicado: { rotulo: "Já lançado", classe: "apagado", filtro: "Já lançados" },
  repetido: { rotulo: "Repetido", classe: "apagado", filtro: "Repetidos no arquivo" },
};
const EXTENSOES = /\.(xlsx|xlsm|xls|csv|txt)$/i;
const MAX_EXIBIDOS = 400;
const config = { centro_custo: "", status: "Pendente" };

let raiz = null;
let sessao = null;
let selecionados = new Set();
let filtro = "";
let arquivoPendente = null;
let requisicao = 0;
let centros = [];

export async function montar(el) {
  raiz = el;
  el.removeEventListener("click", aoClicar);
  el.removeEventListener("change", aoAlterar);
  el.removeEventListener("keydown", aoTeclar);
  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  el.addEventListener("keydown", aoTeclar);
  el.innerHTML = `<div class="card esqueleto" style="height:260px"></div>`;
  let acesso = null;
  try {
    acesso = await estadoAdmin();
  } catch {
    acesso = null;
  }
  if (raiz !== el) return;
  if (!acesso?.autorizado) {
    renderizarBloqueio(acesso);
    return;
  }
  el.innerHTML = `
    <section class="leitura-topo" id="imp-topo">
      <div class="card dropzone" id="imp-drop" tabindex="0" role="button" aria-label="Enviar planilha para importar">
        <div class="dz-icone">${icone("planilha", 30)}</div>
        <h2>Importe boletos de outro sistema</h2>
        <p>Envie a planilha exportada do seu sistema financeiro ou ERP: Excel (.xlsx ou .xls), CSV ou TXT.<br>
          Também dá para arrastar o arquivo para cá.</p>
        <div class="dz-acoes"><button class="btn btn-primario" type="button" data-imp="escolher">${icone("upload", 16)} Escolher arquivo</button></div>
      </div>
      <div class="card card-manual">
        <h3>${icone("info", 17)} Como funciona</h3>
        <ol class="passos-simples">
          <li>No outro sistema, exporte as contas a pagar / boletos para Excel ou CSV.</li>
          <li>Envie o arquivo aqui: as colunas são reconhecidas sozinhas.</li>
          <li>Confira as colunas e a prévia. Boletos já lançados e linhas com erro ficam de fora.</li>
          <li>Clique em <strong>Importar</strong>: tudo vai para a planilha de uma vez.</li>
        </ol>
        <p class="sutil">Colunas úteis: linha digitável, beneficiário, CPF/CNPJ, nº do documento, vencimento, valor, situação e centro de custo.
          Na próxima vez, as colunas escolhidas são lembradas.</p>
        <div class="linha-botoes">
          <a class="btn" href="/api/importacao/modelo.xlsx">${icone("download", 16)} Baixar planilha modelo</a>
          <button class="btn btn-fantasma" type="button" data-imp="bloquear" title="Fecha a área restrita neste aparelho">${icone("escudo", 16)} Bloquear</button>
        </div>
      </div>
    </section>
    <input type="file" id="imp-arquivo" accept=".xlsx,.xlsm,.xls,.csv,.txt" hidden>
    <div id="imp-conteudo"></div>`;
  centros = await carregarCentros().catch(() => []);
  if (raiz !== el) return;
  if (arquivoPendente) {
    const arquivo = arquivoPendente;
    arquivoPendente = null;
    enviar(arquivo);
  } else if (sessao) {
    renderizarSessao();
  }
}

export function desmontar() {
  raiz?.removeEventListener("click", aoClicar);
  raiz?.removeEventListener("change", aoAlterar);
  raiz?.removeEventListener("keydown", aoTeclar);
  raiz = null;
}

/** Planilha solta ou colada em qualquer tela. */
export function receberArquivo(arquivo) {
  if (raiz) enviar(arquivo);
  else arquivoPendente = arquivo;
}

// ------------------------------------------------------------------ envio e prévia

async function enviar(arquivo) {
  if (!raiz) return;
  if (!raiz.querySelector("#imp-conteudo")) {
    arquivoPendente = arquivo; // área ainda bloqueada: importa depois de digitar a senha
    return;
  }
  if (!EXTENSOES.test(arquivo?.name || "")) {
    toast("Envie uma planilha Excel (.xlsx ou .xls), CSV ou TXT. Para PDFs e fotos de boletos, use Ler boletos.", "aviso", { duracao: 7000 });
    return;
  }
  raiz.querySelector("#imp-topo").hidden = true;
  raiz.querySelector("#imp-conteudo").innerHTML = `<div class="card imp-carregando"><span class="spinner"></span>
    <div><strong>Lendo ${esc(arquivo.name)}…</strong><div class="sutil" id="imp-progresso">Enviando 0%</div></div></div>`;
  try {
    const resposta = await api.enviarPara("/api/importacao", arquivo, (progresso) => {
      const alvo = raiz?.querySelector("#imp-progresso");
      if (alvo) alvo.textContent = progresso >= 1 ? "Reconhecendo as colunas e conferindo os boletos…" : `Enviando ${Math.round(progresso * 100)}%`;
    });
    Object.assign(config, { centro_custo: "", status: "Pendente" });
    filtro = "";
    aplicarSessao(resposta);
  } catch (erro) {
    if (!raiz) return;
    if (erro.status === 403) {
      sessaoExpirada();
      return;
    }
    sessao = null;
    raiz.querySelector("#imp-topo").hidden = false;
    raiz.querySelector("#imp-conteudo").innerHTML = `<div class="alerta erro">${icone("erro", 16)}<span>${esc(mensagemErro(erro))}</span></div>`;
  }
}

function aplicarSessao(resposta) {
  sessao = resposta;
  selecionados = new Set(resposta.itens.filter((i) => i.estado === "pronto" || i.estado === "aviso").map((i) => i.indice));
  if (raiz) renderizarSessao();
}

function corpoConfig(parcial = {}) {
  return {
    aba: sessao.aba,
    linha_cabecalho: sessao.linha_cabecalho,
    mapeamento: sessao.mapeamento,
    centro_custo: config.centro_custo,
    status: config.status,
    ...parcial,
  };
}

async function atualizarPrevia(parcial = {}) {
  if (!sessao) return;
  const minha = ++requisicao;
  raiz?.querySelector("#imp-previa")?.classList.add("carregando");
  try {
    const resposta = await api.post(`/api/importacao/${sessao.id}/previa`, corpoConfig(parcial));
    if (!raiz || minha !== requisicao) return;
    aplicarSessao(resposta);
  } catch (erro) {
    if (erro.status === 403) {
      sessaoExpirada();
      return;
    }
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    if (erro.status === 404) reiniciar();
  } finally {
    raiz?.querySelector("#imp-previa")?.classList.remove("carregando");
  }
}

function reiniciar() {
  sessao = null;
  if (!raiz) return;
  raiz.querySelector("#imp-topo").hidden = false;
  raiz.querySelector("#imp-conteudo").innerHTML = "";
}

// ------------------------------------------------------------------ área restrita

function renderizarBloqueio(acesso) {
  sessao = null;
  const semSenha = acesso && !acesso.senha_definida;
  raiz.innerHTML = `<section class="card vazio area-restrita">
    <div class="vazio-icone">${icone("escudo", 28)}</div>
    <h3>Área restrita</h3>
    <p>${semSenha
      ? "A importação de boletos é protegida por uma senha de administrador, que ainda não foi criada. Crie a senha em Configurações, no computador onde o sistema está instalado."
      : "A importação de boletos só pode ser usada por quem tem a senha de administrador."}</p>
    <div class="linha-botoes">
      ${semSenha ? "" : `<button class="btn btn-primario" type="button" data-imp="desbloquear">${icone("escudo", 16)} Digitar a senha</button>`}
      <a class="btn" href="#/config?aba=usuarios">${icone("config", 16)} Ir para Configurações</a>
    </div>
  </section>`;
}

function sessaoExpirada() {
  toast("A área restrita foi bloqueada (tempo esgotado ou senha trocada). Digite a senha de administrador de novo.", "aviso", { duracao: 7000 });
  if (raiz) renderizarBloqueio({ senha_definida: true });
}

// ------------------------------------------------------------------ renderização

const podeSelecionar = (item) => item.estado !== "erro";

function renderizarSessao() {
  raiz.querySelector("#imp-topo").hidden = true;
  raiz.querySelector("#imp-conteudo").innerHTML = htmlConfig() + htmlPrevia();
}

function renderizarPrevia() {
  const antigo = raiz.querySelector("#imp-previa");
  if (antigo) antigo.outerHTML = htmlPrevia();
}

function htmlConfig() {
  const s = sessao;
  const exemplo = (i) => (i === null || i === undefined ? "" : (s.colunas[i]?.exemplos || []).slice(0, 2).join(" · "));
  return `<section class="card imp-config">
    <div class="imp-cabecalho">
      <div class="item-arquivo">
        <span class="item-icone">${icone("planilha", 18)}</span>
        <div style="min-width:0"><div class="item-nome" title="${esc(s.arquivo)}">${esc(s.arquivo)}</div>
          <div class="sutil">${esc(s.formato)} · ${s.resumo.total} linha${s.resumo.total === 1 ? "" : "s"} com dados${s.truncado ? " · limitado às primeiras 5.000 linhas" : ""}</div></div>
      </div>
      ${s.mapeamento_salvo ? `<span class="chip ok">${icone("check", 12)} Colunas lembradas da última importação</span>` : ""}
      <span class="espaco"></span>
      <button class="btn btn-sm btn-fantasma" data-imp="trocar">${icone("upload", 14)} Outro arquivo</button>
    </div>

    <div class="imp-origem">
      ${s.abas.length > 1 ? `<label class="imp-grupo"><span class="imp-rotulo">Aba da planilha</span>
        <select class="input" data-imp-config="aba">${s.abas.map((a) => `<option ${a === s.aba ? "selected" : ""}>${esc(a)}</option>`).join("")}</select></label>` : ""}
      <label class="imp-grupo"><span class="imp-rotulo">Linha com os títulos das colunas</span>
        <select class="input" data-imp-config="linha_cabecalho">
          <option value="0" ${s.linha_cabecalho ? "" : "selected"}>Sem títulos (o arquivo já começa nos boletos)</option>
          ${s.opcoes_cabecalho.map((o) => `<option value="${o.linha}" ${o.linha === s.linha_cabecalho ? "selected" : ""}>Linha ${o.linha}: ${esc(o.texto.slice(0, 80))}</option>`).join("")}
        </select></label>
    </div>

    <h3 class="imp-titulo">${icone("lista", 16)} Em qual coluna está cada informação?</h3>
    <div class="imp-mapa">${s.campos.map((campo) => {
      const i = s.mapeamento[campo.chave];
      const mapeado = i !== null && i !== undefined;
      return `<label class="imp-campo ${mapeado ? "mapeado" : ""}">
        <span class="imp-rotulo">${esc(campo.rotulo)}</span>
        <select class="input" data-imp-campo="${campo.chave}">
          <option value="">— não importar —</option>
          ${s.colunas.map((c) => `<option value="${c.indice}" ${c.indice === i ? "selected" : ""}>${esc(c.titulo)}</option>`).join("")}
        </select>
        <small class="sutil" title="${esc(exemplo(i))}">${mapeado ? esc(exemplo(i)) || "coluna vazia nas primeiras linhas" : "&nbsp;"}</small>
      </label>`;
    }).join("")}</div>

    <div class="imp-opcoes">
      <label class="imp-grupo"><span class="imp-rotulo">Centro de custo quando o arquivo não informar</span>
        <select class="input" data-imp-config="centro_custo" data-centro-select>${opcoesCentro(centros, config.centro_custo)}</select></label>
      <label class="imp-grupo"><span class="imp-rotulo">Situação quando o arquivo não informar</span>
        <select class="input" data-imp-config="status">
          ${["Pendente", "Pago"].map((s2) => `<option ${config.status === s2 ? "selected" : ""}>${s2}</option>`).join("")}
        </select></label>
    </div>
  </section>`;
}

function htmlBarra() {
  const s = sessao;
  const escolhidos = s.itens.filter((i) => selecionados.has(i.indice));
  const total = escolhidos.reduce((soma, i) => soma + Number(i.dados.valor || 0), 0);
  return `<div class="imp-barra">
    <div class="chips-situacao">
      <button class="chip-filtro ${filtro ? "" : "ativo"}" data-imp-filtro="">Todas (${s.resumo.total})</button>
      ${Object.entries(ESTADOS).filter(([estado]) => s.resumo[estado]).map(([estado, e]) =>
        `<button class="chip-filtro ${filtro === estado ? "ativo" : ""}" data-imp-filtro="${estado}">${e.filtro} (${s.resumo[estado]})</button>`).join("")}
    </div>
    <span class="espaco"></span>
    <span class="sutil">${escolhidos.length} selecionado${escolhidos.length === 1 ? "" : "s"} · ${brl(total)}</span>
    <button class="btn btn-primario" data-imp="importar" ${escolhidos.length ? "" : "disabled"}>
      ${icone("planilha", 16)} Importar ${escolhidos.length} boleto${escolhidos.length === 1 ? "" : "s"}</button>
  </div>`;
}

function atualizarBarra() {
  const barra = raiz?.querySelector(".imp-barra");
  if (barra) barra.outerHTML = htmlBarra();
}

function linhaPrevia(item) {
  const d = item.dados;
  const estado = ESTADOS[item.estado];
  const detalhes = [d.documento_beneficiario, d.numero_documento ? `Doc. ${d.numero_documento}` : ""].filter(Boolean).map(esc).join(" · ");
  const marcado = selecionados.has(item.indice);
  return `<tr class="imp-${item.estado} ${marcado ? "selecionado" : ""}">
    <td class="col-check"><input type="checkbox" data-imp-sel="${item.indice}" ${marcado ? "checked" : ""} ${podeSelecionar(item) ? "" : "disabled"}
      aria-label="Importar a linha ${item.linha}"></td>
    <td data-rotulo="Linha" class="sutil">${item.linha}</td>
    <td data-rotulo="Situação"><span class="chip ${estado.classe}">${estado.rotulo}</span>${d.status === "Pago" ? ` <span class="chip ok">Pago</span>` : ""}</td>
    <td data-rotulo="Vencimento">${dataBR(d.vencimento)}</td>
    <td data-rotulo="Beneficiário" class="celula-benef"><strong title="${esc(d.beneficiario)}">${esc(d.beneficiario || "—")}</strong>
      <span>${detalhes || "&nbsp;"}</span>${d.centro_custo ? `<span class="tag-centro">${icone("etiqueta", 11)}${esc(d.centro_custo)}</span>` : ""}</td>
    <td data-rotulo="Valor" class="num">${brl(d.valor)}</td>
    <td data-rotulo="Linha digitável"><span class="mono imp-linha" title="${esc(d.linha_digitavel)}">${esc(d.linha_digitavel || "—")}</span></td>
    <td data-rotulo="Conferência">${item.mensagens.length
      ? `<ul class="imp-msgs">${item.mensagens.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>`
      : `<span class="sutil">Tudo certo</span>`}</td>
  </tr>`;
}

function htmlPrevia() {
  const visiveis = sessao.itens.filter((i) => !filtro || i.estado === filtro);
  const selecionaveis = visiveis.filter(podeSelecionar);
  const todos = selecionaveis.length > 0 && selecionaveis.every((i) => selecionados.has(i.indice));
  return `<section class="card tabela-card" id="imp-previa">
    ${htmlBarra()}
    ${visiveis.length ? `<div class="tabela-wrap"><table class="tabela tabela-importacao">
        <thead><tr>
          <th class="col-check"><input type="checkbox" data-imp-todos ${todos ? "checked" : ""} ${selecionaveis.length ? "" : "disabled"} aria-label="Selecionar todas as linhas"></th>
          <th>Linha</th><th>Situação</th><th>Vencimento</th><th>Beneficiário</th><th class="num">Valor</th><th>Linha digitável</th><th>Conferência</th>
        </tr></thead>
        <tbody>${visiveis.slice(0, MAX_EXIBIDOS).map(linhaPrevia).join("")}</tbody>
      </table></div>
      ${visiveis.length > MAX_EXIBIDOS ? `<p class="sutil imp-rodape">Mostrando ${MAX_EXIBIDOS} de ${visiveis.length} linhas. Todas as selecionadas serão importadas.</p>` : ""}`
    : `<div class="vazio"><div class="vazio-icone">${icone("busca", 26)}</div><h3>Nenhuma linha neste filtro</h3>
        <p>Confira se as colunas de vencimento, valor e beneficiário (ou linha digitável) estão escolhidas acima.</p></div>`}
  </section>`;
}

// ------------------------------------------------------------------ importação

async function importar() {
  const escolhidos = sessao.itens.filter((i) => selecionados.has(i.indice) && podeSelecionar(i));
  if (!escolhidos.length) return;
  const total = escolhidos.reduce((soma, i) => soma + Number(i.dados.valor || 0), 0);
  const repetidos = escolhidos.filter((i) => i.estado === "duplicado" || i.estado === "repetido").length;
  const ok = await confirmar({
    titulo: "Importar boletos",
    mensagem: `Importar ${escolhidos.length} boleto${escolhidos.length === 1 ? "" : "s"} (total de ${brl(total)}) para a planilha?`
      + (repetidos ? ` Atenção: ${repetidos} deles já estão lançados ou aparecem repetidos no arquivo e serão lançados de novo.` : ""),
    textoConfirmar: `Importar ${escolhidos.length}`,
  });
  if (!ok || !sessao) return;
  const botao = raiz?.querySelector("[data-imp='importar']");
  if (botao) {
    botao.disabled = true;
    botao.innerHTML = `<span class="spinner"></span> Importando…`;
  }
  try {
    const resultado = await api.post(`/api/importacao/${sessao.id}/importar`, { ...corpoConfig(), indices: escolhidos.map((i) => i.indice) });
    const nome = sessao.arquivo;
    sessao = null;
    window.dispatchEvent(new Event("avisos:atualizar"));
    window.dispatchEvent(new Event("gravacao:atualizar"));
    if (raiz) renderizarConcluido(resultado, nome);
  } catch (erro) {
    if (erro.status === 403) {
      sessaoExpirada();
      return;
    }
    toast(mensagemErro(erro), "erro", { duracao: erro.status === 423 ? 9000 : 6000 });
    atualizarBarra();
  }
}

function renderizarConcluido(r, nome) {
  raiz.querySelector("#imp-conteudo").innerHTML = `<section class="card imp-concluido">
    <div class="vazio-icone imp-concluido-icone">${icone(r.pendente_gravacao ? "relogio" : "check", 28)}</div>
    <h3>${r.importados} boleto${r.importados === 1 ? " importado" : "s importados"}</h3>
    <p>${brl(r.valor_total)} vindos de <strong>${esc(nome)}</strong>.
      ${r.pendente_gravacao ? "A planilha está aberta no Excel: os lançamentos serão gravados assim que o arquivo for fechado." : "Já estão na planilha."}
      ${r.ignorados ? ` ${r.ignorados} linha(s) com erro ficaram de fora.` : ""}</p>
    <p class="sutil">As colunas escolhidas ficaram salvas: na próxima importação deste sistema, elas são reconhecidas sozinhas.</p>
    <div class="linha-botoes">
      <a class="btn btn-primario" href="#/boletos">${icone("lista", 16)} Ver boletos lançados</a>
      <button class="btn" data-imp="trocar">${icone("upload", 16)} Importar outro arquivo</button>
    </div>
  </section>`;
}

// ------------------------------------------------------------------ eventos

function aoClicar(e) {
  const acao = e.target.closest("[data-imp]")?.dataset.imp;
  if (acao === "escolher" || acao === "trocar") {
    raiz.querySelector("#imp-arquivo").click();
    return;
  }
  if (acao === "importar") {
    importar();
    return;
  }
  if (acao === "desbloquear") {
    pedirSenhaAdmin({ descricao: "Digite a senha de administrador para usar a importação de boletos." })
      .then((liberado) => { if (liberado && raiz) montar(raiz); });
    return;
  }
  if (acao === "bloquear") {
    bloquearAdmin().catch(() => {}).finally(() => {
      if (raiz) renderizarBloqueio({ senha_definida: true });
      toast("Importação bloqueada neste aparelho.", "info");
    });
    return;
  }
  const botaoFiltro = e.target.closest("[data-imp-filtro]");
  if (botaoFiltro) {
    filtro = botaoFiltro.dataset.impFiltro;
    renderizarPrevia();
    return;
  }
  if (e.target.closest("#imp-drop")) raiz.querySelector("#imp-arquivo").click();
}

function aoTeclar(e) {
  if ((e.key === "Enter" || e.key === " ") && e.target.id === "imp-drop") {
    e.preventDefault();
    raiz.querySelector("#imp-arquivo").click();
  }
}

async function aoAlterar(e) {
  const alvo = e.target;
  if (alvo.id === "imp-arquivo") {
    const arquivo = alvo.files[0];
    alvo.value = "";
    if (arquivo) enviar(arquivo);
    return;
  }
  if (!sessao) return;
  if (alvo.dataset.impCampo) {
    sessao.mapeamento = { ...sessao.mapeamento, [alvo.dataset.impCampo]: alvo.value === "" ? null : Number(alvo.value) };
    atualizarPrevia();
    return;
  }
  if (alvo.dataset.impSel !== undefined) {
    const indice = Number(alvo.dataset.impSel);
    if (alvo.checked) selecionados.add(indice);
    else selecionados.delete(indice);
    alvo.closest("tr")?.classList.toggle("selecionado", alvo.checked);
    atualizarBarra();
    return;
  }
  if (alvo.matches("[data-imp-todos]")) {
    sessao.itens.filter((i) => (!filtro || i.estado === filtro) && podeSelecionar(i))
      .forEach((i) => (alvo.checked ? selecionados.add(i.indice) : selecionados.delete(i.indice)));
    renderizarPrevia();
    return;
  }
  switch (alvo.dataset.impConfig) {
    case "aba":
      atualizarPrevia({ aba: alvo.value, linha_cabecalho: null, mapeamento: null });
      break;
    case "linha_cabecalho":
      atualizarPrevia({ linha_cabecalho: Number(alvo.value), mapeamento: null });
      break;
    case "centro_custo":
      config.centro_custo = await tratarNovoCentro(alvo, config.centro_custo);
      centros = await carregarCentros().catch(() => centros);
      atualizarPrevia();
      break;
    case "status":
      config.status = alvo.value;
      atualizarPrevia();
      break;
    default:
      break;
  }
}

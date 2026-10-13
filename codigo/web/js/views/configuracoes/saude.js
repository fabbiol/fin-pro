// Configurações · Saúde do sistema: o que roda sozinho está funcionando? (atualiza a cada 30 segundos)
import { api } from "../../api.js";
import { estado, pode } from "../../estado.js";
import { icone } from "../../icons.js";
import { confirmar, dataHoraBR, esc, mensagemErro, tamanhoArquivo, toast } from "../../ui.js";
import { alertaErro, atualizar, buscar, carregarAcesso, redesenhar, tela } from "./tela.js";

export const chave = "saude";

const SITUACOES = { ok: ["Funcionando", "ok"], aviso: ["Atenção", "aviso"], erro: ["Problema", "erro"], desligado: ["Desligado", "apagado"] };
const TOPO = {
  ok: ["ok", "Tudo funcionando"],
  aviso: ["alerta", "Alguns itens precisam de atenção"],
  erro: ["erro", "Há problemas que precisam ser resolvidos"],
};
const ICONES = {
  banco: "planilha", empresas: "carteira", caixa: "caixa", diesel: "diesel", notificacoes: "sino", backup: "nuvem",
  entrada: "email", fila: "relogio", leitura: "scan", disco: "pasta", rede: "celular",
};
/** Onde cada item se configura: [endereço, permissão exigida para abrir a tela]. */
const LINKS = {
  notificacoes: ["#/notificacoes", "notificacoes"], backup: ["#/config?aba=integracoes"], entrada: ["#/config?aba=integracoes"],
  rede: ["#/config?aba=usuarios"], empresas: ["#/empresas?aba=bot", "empresas"], caixa: ["#/caixa?aba=bot", "caixa"],
  diesel: ["#/diesel?aba=bot", "diesel"],
};

let relogio = null;
let ocupado = false; // uma ação está rodando: a atualização automática não redesenha no meio dela

const hora = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
};

/** Número de itens com "Problema" no contador da aba (o mesmo critério do index.js). */
function contarProblemas(d) {
  const contador = tela.raiz?.querySelector("[data-contador-saude]");
  if (!contador) return;
  const n = (d?.itens || []).filter((i) => i.situacao === "erro").length;
  contador.textContent = n || "";
  contador.hidden = !n;
}

/** GET /api/saude (sempre 200 com o diagnóstico). Num 401 (precisa entrar de novo) para a atualização automática. */
export async function carregar() {
  const pedidos = [buscar("/api/saude"), estado.acesso ? null : carregarAcesso()];
  try {
    const [d] = await Promise.all(pedidos);
    if (tela.aba === "saude") contarProblemas(d);
    return d;
  } catch (erro) {
    if (erro?.status === 401) parar();
    throw erro;
  }
}

function acaoDoItem(i) {
  const espera = `data-espera="Aguarde…"`;
  if (i.chave === "banco") {
    return `<button class="btn btn-sm saude-acao" type="button" data-acao="saude-atualizar-planilha" ${espera}>${icone("planilha", 15)}
      Atualizar a planilha agora</button>`;
  }
  if (i.chave === "disco" && estado.acesso?.local !== false) {
    return `<button class="btn btn-sm saude-acao" type="button" data-acao="saude-limpar-logs">${icone("lixeira", 15)} Limpar os logs</button>`;
  }
  const [href, permissao] = LINKS[i.chave] || [];
  if (!href || i.situacao === "ok" || (permissao && !pode(permissao))) return "";
  return `<a class="btn btn-sm btn-fantasma saude-acao" href="${href}">${icone("seta", 15)} Abrir</a>`;
}

function linha(i) {
  const [rotulo, classe] = SITUACOES[i.situacao] || SITUACOES.aviso;
  return `<li class="${esc(i.situacao)}" data-chave="${esc(i.chave)}">
    <span class="saude-marca" title="${rotulo}">${icone(ICONES[i.chave] || "info", 15)}</span>
    <div class="saude-info"><strong>${esc(i.titulo)}</strong><span>${esc(i.resumo)}</span></div>
    <span class="chip ${classe}">${rotulo}</span>${acaoDoItem(i)}</li>`;
}

function rodape(d) {
  const b = (d.itens || []).find((i) => i.chave === "banco")?.detalhes || {};
  return [
    d.iniciado_em && `Iniciado em ${esc(dataHoraBR(d.iniciado_em))}`,
    b.banco && `Banco de dados: ${esc(b.banco)}${b.tamanho_banco ? ` (${esc(tamanhoArquivo(b.tamanho_banco))})` : ""}`,
    b.planilha && `Planilha: ${esc(b.planilha)}`,
    "O log (leitor.log) gira sozinho a cada 2 MB e guarda 5 arquivos. Esta lista se atualiza a cada 30 segundos.",
  ].filter(Boolean).join(" · ");
}

const botaoVerificar = (texto = "Verificar agora") =>
  `<button class="btn btn-sm" type="button" data-acao="saude-verificar" data-espera="Aguarde…">${icone("atualizar", 15)} ${texto}</button>`;

export function htmlSaude(d, erro) {
  const itens = Array.isArray(d.itens) ? d.itens : [];
  const [ic, titulo] = TOPO[d.situacao] || TOPO.aviso;
  const n = (s) => itens.filter((i) => i.situacao === s).length;
  const sub = [
    n("erro") && `${n("erro")} com problema`,
    n("aviso") && `${n("aviso")} com atenção`,
    d.versao && `Versão ${esc(d.versao)}`,
    d.em_execucao_ha && `em execução há ${esc(String(d.em_execucao_ha).replace(/^0d /, ""))}`,
    `verificado às ${hora(d.atualizado_em)}`,
  ].filter(Boolean).join(" · ");
  return `<article class="card col-inteira" id="cfg-saude">
    <div class="saude-topo ${esc(TOPO[d.situacao] ? d.situacao : "aviso")}"><span class="saude-icone">${icone(ic, 24)}</span>
      <div><h3>${titulo}</h3><span class="sutil">${sub}</span></div><span class="espaco"></span>${botaoVerificar()}</div>
    ${erro ? `<div class="alerta aviso">${icone("alerta", 16)}<div>Não foi possível atualizar agora: ${esc(mensagemErro(erro))}
      Mostrando a última verificação.</div></div>` : ""}
    <ul class="saude-lista">${itens.map(linha).join("")}</ul>
    <p class="saude-rodape sutil">${rodape(d)}</p>
  </article>`;
}

export function html(d, erro) {
  if (d) return htmlSaude(d, erro);
  if (erro) {
    return `<article class="card col-inteira vazio" id="cfg-saude"><div class="vazio-icone">${icone("alerta", 26)}</div>
      <h3>Não foi possível verificar a saúde do sistema</h3>${alertaErro(erro)}${botaoVerificar("Tentar de novo")}</article>`;
  }
  return `<article class="card col-inteira" id="cfg-saude">
    <div class="saude-topo"><h3>${icone("escudo", 18)} Saúde do sistema</h3><span class="espaco"></span></div>
    <div class="esqueleto" style="height:320px"></div>
  </article>`;
}

/** Roda uma ação sem a atualização automática redesenhar no meio; no fim, desenha o diagnóstico que o servidor devolveu. */
async function emAcao(tarefa) {
  ocupado = true;
  try {
    const d = await tarefa();
    if (d) {
      redesenhar(chave, d);
      contarProblemas(d);
    }
  } finally {
    ocupado = false;
  }
}

/** Diagnóstico de novo, para mostrar a causa real depois de uma falha (ex.: planilha aberta no Excel). */
const diagnosticoAtual = () => buscar("/api/saude").catch(() => null);

export const acoes = {
  "saude-verificar": () => emAcao(() => buscar("/api/saude")),

  "saude-atualizar-planilha": () => emAcao(async () => {
    try {
      const d = await api.post("/api/saude/atualizar-planilha");
      toast("Planilha Excel atualizada.", "ok");
      return d;
    } catch (erro) {
      if (![423, 409].includes(erro?.status)) throw erro;
      toast(mensagemErro(erro), "aviso", { duracao: 7000 });
      return diagnosticoAtual();
    }
  }),

  "saude-limpar-logs": (alvo) => emAcao(async () => {
    const sim = await confirmar({
      titulo: "Limpar os logs",
      mensagem: "Apaga os arquivos de log antigos e esvazia o atual (leitor.log). Lançamentos, planilha, comprovantes e backups não são afetados.",
      textoConfirmar: "Limpar os logs",
      perigo: true,
    });
    if (!sim) return null;
    const original = alvo.innerHTML;
    alvo.innerHTML = `<span class="spinner"></span> Aguarde…`;
    try {
      const r = await api.post("/api/saude/limpar-logs");
      const liberados = Number(r?.liberados) || 0;
      toast(liberados ? `Logs limpos: ${tamanhoArquivo(liberados)} liberados.` : "Os logs já estavam vazios.", "ok");
      return r;
    } catch (erro) {
      if (erro?.codigo !== "somente_local") throw erro;
      toast(mensagemErro(erro), "aviso", { duracao: 7000 });
      return null;
    } finally {
      if (alvo.isConnected) alvo.innerHTML = original;
    }
  }),
};

/** A tela chama ao abrir a aba: atualiza a lista a cada 30 segundos (só com a janela visível e sem ação em andamento). */
export function iniciar() {
  parar();
  relogio = setInterval(() => {
    if (!document.hidden && !ocupado && tela.aba === chave) atualizar(chave);
  }, 30_000);
}

export function parar() {
  clearInterval(relogio);
  relogio = null;
}

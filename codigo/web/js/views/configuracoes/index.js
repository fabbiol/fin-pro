// Tela: Configurações, em abas — Geral (com a versão do sistema) · Usuários e acesso · Backup e recebimento · Saúde do sistema.
// Cada cartão é uma "seção" (um módulo desta pasta) com o mesmo contrato: chave, carregar(), html(dados, erro) e os mapas
// acoes / alteracoes / formularios (veja tela.js e eventos.js). Esta página monta as abas e carrega as seções da aba aberta.
import { api } from "../../api.js";
import { estado } from "../../estado.js";
import { icone } from "../../icons.js";
import { esc, toast } from "../../ui.js";
import * as aplicativo from "./aplicativo.js";
import * as backup from "./backup.js";
import * as entrada from "./entrada.js";
import { aoAlterar, aoClicar, aoEnviar } from "./eventos.js";
import * as importacao from "./importacao.js";
import * as rede from "./rede.js";
import * as saude from "./saude.js";
import { atualizar, buscar, htmlSecao, tela } from "./tela.js";
import * as usuarios from "./usuarios.js";
import * as versao from "./versao.js";

// ------------------------------------------------------------------ Geral: banco de dados, recursos de leitura, ajuda e sobre

const PASSOS = [
  ["Envie o arquivo", "Arraste PDFs ou fotos, escolha os arquivos, tire uma foto no celular ou cole com Ctrl+V."],
  ["Código de barras e texto", "Primeiro o código de barras da imagem; depois o texto do PDF."],
  ["OCR e IA", "Fotos e PDFs escaneados passam pelo OCR local; a IA (opcional) ajuda nas fotos difíceis."],
  ["Validação", "A linha digitável é conferida pelos dígitos verificadores; vencimento e valor saem do código e são conferidos com o que está impresso."],
  ["Confira e lance", "Campos com baixa confiança ficam em amarelo. Escolha o centro de custo e clique em Lançar na planilha."],
];

const ATALHOS = [
  ["<kbd>Ctrl</kbd> + <kbd>V</kbd>", "Colar imagem, linha digitável ou Pix Copia e Cola"],
  ["Arrastar arquivo", "Ler boletos e comprovantes, em qualquer tela"],
  ["<kbd>/</kbd>", "Buscar (boletos, comprovantes)"],
  ["<kbd>Alt</kbd> + <kbd>1</kbd>…<kbd>9</kbd>", "Painel, Ler, Boletos, Pix, Comprovantes, Caixa, Diesel, Gastos, Empresas"],
  ["<kbd>Esc</kbd>", "Fechar janelas"],
  ["<kbd>‹</kbd> <kbd>›</kbd>", "Passar comprovantes no visualizador"],
];

const recurso = (ic, titulo, texto, chip) => `<li>${icone(ic, 18)}<div class="info"><strong>${titulo}</strong><p>${texto}</p></div>${chip}</li>`;
const ATIVO = `<span class="chip ok">Ativo</span>`;
const INDISPONIVEL = `<span class="chip aviso">Indisponível</span>`;

function htmlRecursos(s) {
  if (!s) return `<li class="sutil">Não foi possível consultar o servidor.</li>`;
  return [
    recurso("boleto", "Código de barras", "Lê o código de barras da imagem ou do PDF. A linha digitável sempre passa pela validação dos dígitos verificadores (FEBRABAN).", ATIVO),
    recurso("arquivo", "Texto de PDF", "PDFs digitais: beneficiário, documento, vencimento e valor lidos direto do texto, pela posição de cada rótulo.", ATIVO),
    recurso("olho", "OCR local", s.ocr
      ? `Fotos e PDFs escaneados são lidos neste computador, sem enviar nada para fora.${s.ocr_modelo ? ` Modelo: ${esc(s.ocr_modelo)}.` : " O modelo é carregado na primeira leitura."}`
      : "O pacote de OCR (RapidOCR) não está instalado: fotos e PDFs escaneados dependem do código de barras ou da IA. Instale as dependências e reinicie o sistema.",
    s.ocr ? ATIVO : INDISPONIVEL),
    recurso("camera", "Fotos do iPhone (HEIC)", s.heic ? "Fotos .heic são aceitas como JPG, PNG ou WEBP." : "Instale o pillow-heif para aceitar fotos .heic do iPhone.",
      s.heic ? ATIVO : INDISPONIVEL),
    recurso("clipe", "Comprovantes de pagamento", "Envie o comprovante em Ler boletos: o sistema acha o boleto ou o Pix e marca como pago, com juros e desconto.", ATIVO),
    recurso("ia", "IA (Claude)", s.ia
      ? `Modelo ${esc(s.ia_modelo)}. ${s.ia_automatica ? "É chamada sozinha quando a leitura local tem baixa confiança." : "Use o botão Analisar com IA na revisão de cada boleto."} O resultado também passa pela validação dos dígitos.`
      : "Opcional, para fotos difíceis. Para ativar: crie uma chave em console.anthropic.com, coloque ANTHROPIC_API_KEY=… no arquivo .env e reinicie o sistema.",
    s.ia ? `<span class="chip ia">Ativa</span>` : `<span class="chip apagado">Desativada</span>`),
  ].join("");
}

function htmlBanco(s, app) {
  const windows = Boolean(app?.atalhos?.disponivel || app?.inicializacao?.disponivel);
  const podeAbrir = windows && app?.local;
  const n = Number(s?.gravacao_pendente) || 0;
  let explicacao = "";
  if (app && !podeAbrir) {
    explicacao = windows
      ? "Abrir a planilha e a pasta só funciona no computador onde o Fin Pro está instalado. Daqui, use Baixar cópia."
      : "Abrir no Excel e abrir a pasta só funcionam no Windows. Use Baixar cópia.";
  }
  return `<article class="card" id="cfg-banco">
    <h3>${icone("planilha", 18)} Banco de dados e planilha</h3>
    <p class="sutil">Os lançamentos ficam no banco de dados da pasta de dados e a planilha Excel é atualizada sozinha. Pode deixar a
      planilha aberta no Excel: o que for lançado com ela aberta é gravado quando o arquivo for fechado, e edições feitas no Excel
      em lançamentos que já existem voltam para o sistema.</p>
    ${s ? `<span class="sutil">Planilha</span><div class="caminho">${esc(s.planilha)}</div>
      <span class="sutil">Pasta de dados</span><div class="caminho">${esc(s.pasta_dados)}</div>`
      : `<div class="esqueleto" style="height:84px"></div>`}
    ${n > 0 ? `<div class="alerta aviso">${icone("alerta", 16)}<div>${n} alteração(ões) aguardando gravação: a planilha está aberta em outro
      programa (ex.: Excel).</div></div>` : ""}
    <div class="linha-botoes">
      ${podeAbrir ? `<button class="btn" type="button" data-acao="sistema-abrir-planilha">${icone("planilha", 16)} Abrir planilha</button>
        <button class="btn" type="button" data-acao="sistema-abrir-pasta">${icone("pasta", 16)} Abrir pasta de dados</button>` : ""}
      <a class="btn" href="${esc(api.urlExportar({ formato: "planilha" }))}" download>${icone("download", 16)} Baixar cópia</a>
    </div>
    ${explicacao ? `<p class="sutil">${explicacao}</p>` : ""}
  </article>`;
}

/** Seção "sistema" (cartões da aba Geral que vêm de /api/status). Segue o mesmo contrato dos módulos da pasta. */
const sistema = {
  chave: "sistema",
  async carregar() {
    const [status, app] = await Promise.all([buscar("/api/status"), buscar("/api/app").catch(() => null)]);
    estado.status = status;
    return { status, app };
  },
  html(dados) {
    const s = dados?.status || estado.status;
    return `${htmlBanco(s, dados?.app)}
    <article class="card" id="cfg-recursos">
      <h3>${icone("scan", 18)} Recursos de leitura</h3>
      <ul class="recursos">${htmlRecursos(s)}</ul>
      ${s ? `<p class="sutil">Arquivos de até ${esc(s.max_upload_mb)} MB · PDF, JPG, PNG, WEBP${s.heic ? " e HEIC" : ""} · vários de uma vez.</p>` : ""}
    </article>
    <article class="card col-inteira" id="cfg-leitura">
      <h3>${icone("info", 18)} Como a leitura funciona</h3>
      <ol class="passos">${PASSOS.map(([t, d]) => `<li><strong>${t}</strong><p>${d}</p></li>`).join("")}</ol>
    </article>
    <article class="card" id="cfg-atalhos">
      <h3>${icone("teclado", 18)} Atalhos de teclado</h3>
      <table class="atalhos"><tbody>${ATALHOS.map(([teclas, texto]) => `<tr><td style="white-space:nowrap">${teclas}</td><td>${texto}</td></tr>`).join("")}</tbody></table>
    </article>
    <article class="card" id="cfg-sobre">
      <h3>${icone("info", 18)} Sobre o Fin Pro</h3>
      ${s ? `<p><strong>${esc(s.nome_app)}</strong> versão ${esc(s.versao)}${s.demonstracao ? ` <span class="chip info">Versão de demonstração</span>` : ""}</p>` : ""}
      <p class="sutil">Boletos, Pix, comprovantes, caixa, diesel, gastos, empresas e lembretes de vencimento, com a planilha Excel sempre atualizada.</p>
    </article>`;
  },
  acoes: {
    "sistema-abrir-planilha": async () => {
      await api.post("/api/planilha/abrir");
      toast("Abrindo a planilha no Excel… Se lançar boletos com ela aberta, eles serão gravados quando você fechar.", "info", { duracao: 7000 });
    },
    "sistema-abrir-pasta": async () => {
      await api.post("/api/planilha/abrir-pasta");
      toast("Abrindo a pasta de dados…", "ok");
    },
  },
};

// ------------------------------------------------------------------ abas

/** chave da aba (o ?aba= do endereço), ícone, rótulo e as seções (cartões) na ordem em que aparecem. */
const ABAS = [
  { chave: "geral", icone: "config", rotulo: "Geral", secoes: [aplicativo, sistema, versao] },
  { chave: "usuarios", icone: "usuarios", rotulo: "Usuários e acesso", secoes: [importacao, usuarios, rede] },
  { chave: "integracoes", icone: "nuvem", rotulo: "Backup e recebimento", secoes: [backup, entrada] },
  { chave: "saude", icone: "ok", rotulo: "Saúde do sistema", secoes: [saude] },
];

/** Endereços pelo nome do cartão (ex.: #/config?aba=backup) abrem a aba certa e rolam até o cartão: [aba, id do cartão]. */
const APELIDOS = {
  aplicativo: ["geral", "cfg-aplicativo"], versao: ["geral", "cfg-versao"], sistema: ["geral", "cfg-banco"],
  importacao: ["usuarios", "cfg-importacao"], rede: ["usuarios", "cfg-rede"], acesso: ["usuarios", "cfg-rede"],
  backup: ["integracoes", "cfg-backup"], entrada: ["integracoes", "cfg-entrada"], recebimento: ["integracoes", "cfg-entrada"],
};

function htmlAbas() {
  return `<nav class="alternar-modo sub-abas config-abas" role="tablist" aria-label="Seções das configurações">
    ${ABAS.map((a) => `<a role="tab" href="#/config?aba=${a.chave}" class="${a.chave === tela.aba ? "ativo" : ""}"
      aria-selected="${a.chave === tela.aba}">${icone(a.icone, 15)} ${esc(a.rotulo)}${a.chave === "saude"
        ? `<span class="nav-contador alerta" data-contador-saude title="Itens com problema" hidden></span>` : ""}</a>`).join("")}
  </nav>`;
}

/** Contador de problemas na aba Saúde (só os itens com "Problema"; "Atenção" é comum, ex.: sem OCR). */
async function contarProblemas() {
  const vez = tela.vez;
  try {
    const d = await buscar("/api/saude");
    const contador = tela.raiz?.querySelector("[data-contador-saude]");
    if (vez !== tela.vez || !contador) return;
    const n = (d.itens || []).filter((i) => i.situacao === "erro").length;
    contador.textContent = n || "";
    contador.hidden = !n;
  } catch { /* sem contador */ }
}

/** Carrega (de novo) todas as seções da aba; cada cartão se redesenha quando os dados dele chegam. */
async function carregarAba() {
  const vez = ++tela.vez;
  await Promise.all(tela.secoes.map((s) => atualizar(s.chave)));
  return vez === tela.vez;
}

function pararSecoes() {
  tela.secoes.forEach((s) => {
    try { s.parar?.(); } catch { /* segue */ }
  });
}

const aoRecarregar = () => { if (tela.raiz) carregarAba(); };

export async function montar(el, params) {
  const pedida = (params?.get?.("aba") || "").trim();
  const [abaDoApelido, cartao] = Object.hasOwn(APELIDOS, pedida) ? APELIDOS[pedida] : [];
  const aba = ABAS.find((a) => a.chave === (abaDoApelido || pedida)) || ABAS[0];
  tela.raiz = el;
  tela.aba = aba.chave;
  tela.secoes = aba.secoes;
  tela.dados = {};
  tela.erros = {};
  el.innerHTML = `${htmlAbas()}<section class="config-grade" id="config-conteudo">${aba.secoes.map(htmlSecao).join("")}</section>`;
  el.addEventListener("click", aoClicar);
  el.addEventListener("change", aoAlterar);
  el.addEventListener("submit", aoEnviar);
  window.addEventListener("config:atualizar", aoRecarregar);
  aba.secoes.forEach((s) => s.iniciar?.());
  const carga = carregarAba();
  contarProblemas();
  if (!(await carga)) return;
  if (cartao) el.querySelector(`#${cartao}`)?.scrollIntoView({ block: "start", behavior: "smooth" });
}

export function desmontar() {
  pararSecoes();
  window.removeEventListener("config:atualizar", aoRecarregar);
  tela.raiz?.removeEventListener("click", aoClicar);
  tela.raiz?.removeEventListener("change", aoAlterar);
  tela.raiz?.removeEventListener("submit", aoEnviar);
  tela.raiz = null;
  tela.secoes = [];
  tela.vez += 1;
}


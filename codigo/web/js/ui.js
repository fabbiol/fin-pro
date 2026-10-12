// Utilitários de interface: formatação, toasts, modais e selos.
import { icone } from "./icons.js";

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (valor) => String(valor ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);

const formatoBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatoNumero = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatoCompacto = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
export const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export const brl = (v) => (v === null || v === undefined || v === "" ? "—" : formatoBRL.format(Number(v)));
export const numeroBR = (v) => (v === null || v === undefined || v === "" ? "" : formatoNumero.format(Number(v)));
export const compacto = (v) => formatoCompacto.format(Number(v || 0));

/** Converte "1.500,75", "1500.75" ou "R$ 10" em número; "" vira null; inválido vira NaN. */
export function parseValor(texto) {
  if (typeof texto === "number") return texto;
  const limpo = String(texto ?? "").replace(/[R$\s]/g, "");
  if (!limpo) return null;
  const numero = limpo.includes(",") ? Number(limpo.replace(/\./g, "").replace(",", ".")) : Number(limpo);
  return Number.isFinite(numero) ? Math.round(numero * 100) / 100 : NaN;
}

export function dataBR(iso) {
  if (!iso) return "—";
  const [a, m, d] = String(iso).slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function dataHoraBR(iso) {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function hojeISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function isoDeData(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function tamanhoArquivo(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

// Os registros guardam o arquivo como "arquivos/<id>.pdf", mas ele só é servido (com login) em /api/arquivos/<id>
export const urlArquivo = (caminho) => `/api/arquivos/${encodeURIComponent(String(caminho ?? "").split("/").pop().split(".")[0])}`;

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

export function debounce(fn, espera = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), espera);
  };
}

export function mensagemErro(erro) {
  return erro?.message || "Ocorreu um erro inesperado.";
}

// ------------------------------------------------------------------ toasts

const ICONE_TOAST = { ok: "ok", erro: "erro", aviso: "alerta", info: "info" };

export function toast(mensagem, tipo = "info", { duracao = 3800, acao } = {}) {
  const area = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${tipo}`;
  el.setAttribute("role", tipo === "erro" ? "alert" : "status");
  el.innerHTML = `${icone(ICONE_TOAST[tipo] || "info", 18)}<span>${esc(mensagem)}</span>`;
  if (acao) {
    const botao = document.createElement("button");
    botao.textContent = acao.rotulo;
    botao.onclick = () => { acao.executar(); fechar(); };
    el.appendChild(botao);
  }
  area.appendChild(el);
  let fechado = false;
  function fechar() {
    if (fechado) return;
    fechado = true;
    el.classList.add("saindo");
    setTimeout(() => el.remove(), 220);
  }
  setTimeout(fechar, duracao);
  el.addEventListener("click", (e) => { if (e.target.tagName !== "BUTTON") fechar(); });
}

export async function copiar(texto, rotulo = "Copiado para a área de transferência") {
  try {
    await navigator.clipboard.writeText(texto);
  } catch {
    const area = document.createElement("textarea");
    area.value = texto;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  toast(rotulo, "ok", { duracao: 2200 });
}

// ------------------------------------------------------------------ modais

export function abrirModal({ titulo, corpo, rodape = "", tamanho = "", classeCorpo = "", aoFechar } = {}) {
  const raiz = document.getElementById("modais");
  const fundo = document.createElement("div");
  fundo.className = "modal-fundo";
  fundo.innerHTML = `
    <div class="modal ${tamanho}" role="dialog" aria-modal="true" aria-label="${esc(titulo)}">
      <div class="modal-cabecalho"><h3>${esc(titulo)}</h3>
        <button class="btn-icone" data-fechar aria-label="Fechar">${icone("x", 18)}</button></div>
      <div class="modal-corpo ${classeCorpo}">${corpo}</div>
      ${rodape ? `<div class="modal-rodape">${rodape}</div>` : ""}
    </div>`;
  const focoAnterior = document.activeElement;

  function fechar(resultado) {
    document.removeEventListener("keydown", aoTeclar);
    fundo.remove();
    focoAnterior?.focus?.();
    aoFechar?.(resultado);
  }
  function aoTeclar(e) {
    if (e.key === "Escape") fechar(false);
  }
  fundo.addEventListener("mousedown", (e) => { if (e.target === fundo) fechar(false); });
  fundo.addEventListener("click", (e) => { if (e.target.closest("[data-fechar]")) fechar(false); });
  document.addEventListener("keydown", aoTeclar);
  raiz.appendChild(fundo);
  (fundo.querySelector("[autofocus]") || fundo.querySelector(".modal-rodape .btn-primario, .modal-rodape .btn-perigo"))?.focus();
  return { el: fundo, fechar };
}

export function confirmar({ titulo, mensagem, textoConfirmar = "Confirmar", perigo = false }) {
  return new Promise((resolve) => {
    let respondido = false;
    const { el, fechar } = abrirModal({
      titulo,
      corpo: `<p style="color:var(--texto-2)">${esc(mensagem)}</p>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn ${perigo ? "btn-perigo" : "btn-primario"}" data-confirmar>${esc(textoConfirmar)}</button>`,
      aoFechar: () => { if (!respondido) resolve(false); },
    });
    el.querySelector("[data-confirmar]").addEventListener("click", () => {
      respondido = true;
      resolve(true);
      fechar(true);
    });
  });
}

/** Janela que pede um texto curto. Devolve o texto digitado ou null se cancelar. */
export function pedirTexto({ titulo, rotulo, valor = "", placeholder = "", descricao = "", textoConfirmar = "Salvar", maximo = 200 }) {
  return new Promise((resolve) => {
    let respondido = false;
    const { el, fechar } = abrirModal({
      titulo,
      corpo: `<form class="campo" data-pedir-texto>
          ${descricao ? `<p class="sutil" style="margin-bottom:8px">${esc(descricao)}</p>` : ""}
          <label for="pedir-texto">${esc(rotulo)}</label>
          <input id="pedir-texto" class="input" maxlength="${maximo}" value="${esc(valor)}" placeholder="${esc(placeholder)}" autocomplete="off" autofocus>
        </form>`,
      rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
               <button class="btn btn-primario" data-confirmar>${esc(textoConfirmar)}</button>`,
      aoFechar: () => { if (!respondido) resolve(null); },
    });
    const campo = el.querySelector("#pedir-texto");
    const enviar = (e) => {
      e?.preventDefault();
      const texto = campo.value.trim();
      if (!texto) {
        campo.focus();
        return;
      }
      respondido = true;
      resolve(texto);
      fechar(true);
    };
    el.querySelector("[data-confirmar]").addEventListener("click", enviar);
    el.querySelector("[data-pedir-texto]").addEventListener("submit", enviar);
    campo.focus();
    campo.select();
  });
}

// ------------------------------------------------------------------ selos

export const SITUACOES = {
  vencido: { rotulo: "Vencido", classe: "erro" },
  vence_hoje: { rotulo: "Vence hoje", classe: "aviso" },
  a_vencer: { rotulo: "A vencer", classe: "info" },
  pendente: { rotulo: "Pendente", classe: "" },
  pago: { rotulo: "Pago", classe: "ok" },
  cancelado: { rotulo: "Cancelado", classe: "apagado" },
};

export function seloSituacao(situacao, dias) {
  const s = SITUACOES[situacao] || SITUACOES.pendente;
  let extra = "";
  if (situacao === "vencido" && dias !== null && dias !== undefined) extra = ` · ${Math.abs(dias)}d`;
  if (situacao === "a_vencer" && dias !== null && dias !== undefined && dias <= 7) extra = ` · ${dias}d`;
  return `<span class="chip ${s.classe}">${s.rotulo}${extra}</span>`;
}

export const FONTES = {
  codigo_barras: "Código",
  texto: "PDF",
  ocr: "OCR",
  ia: "IA",
  manual: "Manual",
  historico: "Histórico",
};

export function seloFonte(campo) {
  if (!campo || !campo.fonte) return "";
  const conf = Number(campo.confianca ?? 1);
  const nivel = campo.fonte === "ia" ? "ia" : conf >= 0.9 ? "alta" : conf >= 0.75 ? "media" : "baixa";
  const titulo = `Origem: ${FONTES[campo.fonte] || campo.fonte} · confiança ${Math.round(conf * 100)}%`;
  return `<span class="fonte ${nivel}" title="${esc(titulo)}">${esc(FONTES[campo.fonte] || campo.fonte)}</span>`;
}

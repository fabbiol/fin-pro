// Configurações · Versão do sistema: qual versão está em uso, o que mudou em cada uma e se há algo ainda não guardado.
import { icone } from "../../icons.js";
import { dataBR, dataHoraBR, esc } from "../../ui.js";
import { alertaErro, buscar } from "./tela.js";

export const chave = "versao";

/** GET /api/versao (sempre 200; pode demorar na primeira vez por causa do git — o cartão mostra o esqueleto enquanto isso). */
export const carregar = () => buscar("/api/versao");

const TITULO = `<h3>${icone("etiqueta", 18)} Versão do sistema</h3>`;

/** Itens do VERSOES.md: escapa primeiro e depois converte **negrito** e `código` (esc nunca gera * nem `). */
const md = (texto) => esc(texto).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>");

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;

function selo(v) {
  if (!v.disponivel) return `<span class="chip apagado">Sem controle de versão</span>`;
  const n = Number(v.pendentes) || 0;
  if (!n) return `<span class="chip ok">Tudo guardado</span>`;
  return `<span class="chip aviso">${plural(n, "alteração ainda sem versão", "alterações ainda sem versão")}</span>`;
}

/** Arquivos alterados desde a última versão (a lista só vem para o próprio computador e no máximo 30 nomes). */
function htmlPendentes(v) {
  const arquivos = Array.isArray(v.arquivos_pendentes) ? v.arquivos_pendentes : [];
  if (!arquivos.length) return "";
  const resto = (Number(v.pendentes) || 0) - arquivos.length;
  return `<details><summary class="sutil">Ver arquivos alterados</summary>
    <ul class="lista-info">${arquivos.map((f) => `<li><code>${esc(f)}</code></li>`).join("")}
      ${resto > 0 ? `<li>… e mais ${resto}</li>` : ""}</ul></details>`;
}

function htmlHistorico(v) {
  const historico = Array.isArray(v.historico) ? v.historico : [];
  if (!historico.length) return `<p class="sutil">O histórico de versões (VERSOES.md) não está disponível nesta instalação.</p>`;
  return `<div class="versoes">${historico.map((h, i) => `
    <details class="versao-item"${i === 0 ? " open" : ""}><summary>
      <span class="chip marca">v${esc(h.versao)}</span><strong>${esc(h.titulo)}</strong>
      ${h.data ? `<span class="sutil">${esc(dataBR(h.data))}</span>` : ""}${h.versao === v.versao ? `<span class="chip ok">Em uso</span>` : ""}</summary>
      <ul class="lista-info">${(h.itens || []).map((t) => `<li>${md(t)}</li>`).join("")}</ul></details>`).join("")}</div>`;
}

export function htmlVersao(v) {
  const guardadas = Number(v.versoes_guardadas) || 0;
  return `${TITULO}
    <p>Versão em uso: <strong>v${esc(v.versao)}</strong>${v.data ? ` <span class="sutil">de ${esc(dataBR(v.data))}</span>` : ""} ${selo(v)}</p>
    ${v.disponivel ? `<p class="sutil">${plural(guardadas, "versão guardada", "versões guardadas")}${v.commit
      ? ` · ponto atual ${esc(v.commit)}${v.commit_data ? ` de ${esc(dataHoraBR(v.commit_data))}` : ""}` : ""}</p>` : ""}
    ${htmlPendentes(v)}
    ${htmlHistorico(v)}
    <p class="sutil">As versões guardam só o programa; os dados são protegidos pelo backup.</p>`;
}

export function html(v, erro) {
  let corpo = `${TITULO}<div class="esqueleto" style="height:80px"></div>`;
  if (erro) corpo = `${TITULO}${alertaErro(erro)}`;
  else if (v) corpo = htmlVersao(v);
  return `<article class="card col-inteira" id="cfg-versao">${corpo}</article>`;
}

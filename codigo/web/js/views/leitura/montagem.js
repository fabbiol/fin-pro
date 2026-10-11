// Ler boletos · montagem da tela, eventos principais e acompanhamento das leituras.
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
import { aoClicarCaixa, carregarCaixa } from "./caixa.js";
import { aoAlterar, aoClicar, aoDigitar } from "./eventos.js";
import { analisarTexto, boletosEmRevisao, enfileirar } from "./fila.js";
import { atualizarProgresso, renderizarFila } from "./render.js";

export function montar(el) {
  tela.raiz = el;
  const s = estado.status || {};
  const toque = Boolean(window.matchMedia?.("(pointer: coarse)").matches); // celular/tablet: câmera em destaque
  el.innerHTML = `
    <section class="leitura-topo">
      <div class="card dropzone" id="dropzone" tabindex="0" role="button" aria-label="Enviar arquivos de boletos">
        <input type="file" id="entrada-arquivos" multiple accept="application/pdf,image/*,.heic,.heif" hidden>
        <input type="file" id="entrada-camera" accept="image/*" capture="environment" hidden>
        <div class="dz-icone">${icone("upload", 30)}</div>
        <h2>${toque ? "Fotografe ou envie os boletos" : "Arraste os boletos para cá"}</h2>
        <p>${toque ? "Enquadre o boleto inteiro, com boa luz · PDF e imagens também" : "PDF, JPG, PNG, WEBP ou HEIC · vários de uma vez · ou cole com <kbd>Ctrl</kbd> + <kbd>V</kbd>"}</p>
        <p class="sutil dz-comprovante">${icone("clipe", 13)} Comprovantes de pagamento também: o sistema acha o boleto e marca como pago.</p>
        <div class="dz-acoes">
          ${toque
            ? `<button class="btn btn-primario btn-grande" type="button" data-dz="camera">${icone("camera", 18)} Tirar foto do boleto</button>
               <button class="btn" type="button" data-dz="escolher">${icone("arquivo", 16)} Escolher arquivos</button>`
            : `<button class="btn btn-primario" type="button" data-dz="escolher">${icone("arquivo", 16)} Escolher arquivos</button>
               <button class="btn" type="button" data-dz="camera">${icone("camera", 16)} Tirar foto</button>`}
        </div>
        <div class="dz-recursos">
          <span class="chip ok">${icone("boleto", 13)} Código de barras</span>
          <span class="chip ok">${icone("arquivo", 13)} Texto de PDF</span>
          <span class="chip ${s.ocr ? "ok" : "aviso"}">${icone("olho", 13)} OCR ${s.ocr ? "local" : "indisponível"}</span>
          <span class="chip ${s.ia ? "ia" : "apagado"}">${icone("ia", 13)} IA ${s.ia ? "disponível" : "desativada"}</span>
        </div>
      </div>

      <div class="card card-manual">
        <h3>${icone("teclado", 17)} Digitar ou colar a linha digitável</h3>
        <p class="sutil">Aceita a linha digitável (47 ou 48 dígitos) ou o número do código de barras (44 dígitos).</p>
        <form id="form-linha">
          <div class="input-grupo">
            <input class="input mono" id="entrada-linha" placeholder="00190.50095 40144.816069 06809.350314 3 37370000000100"
                   autocomplete="off" spellcheck="false" inputmode="numeric">
            <button class="btn btn-primario" type="submit">Analisar</button>
          </div>
          <div class="contador-digitos" id="contador-digitos" style="margin-top:6px">0 dígitos</div>
        </form>
        <div class="dicas">
          <strong>Dicas para fotos</strong>
          <ul>
            <li>Enquadre o boleto inteiro, com boa luz e sem reflexo.</li>
            <li>O código de barras nítido garante valor e vencimento exatos.</li>
            <li>Confira os campos marcados em amarelo antes de lançar.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="card caixa-entrada" id="caixa-entrada" hidden></section>
    <section class="barra-fila" id="barra-fila" hidden></section>
    <section class="lista-fila" id="lista-fila"></section>`;

  ligarEventos();
  renderizarFila();
  carregarCaixa();
  tela.atualizadorCaixa = setInterval(carregarCaixa, 45 * 1000); // o bot e o e-mail podem trazer arquivos com a tela aberta
  tela.cronometro = setInterval(atualizarCronometros, 1000);
  carregarCentros().then((lista) => {
    tela.centros = lista;
    if (tela.raiz === el && boletosEmRevisao().length) renderizarFila();
  }).catch(() => {});
}

export function desmontar() {
  clearInterval(tela.cronometro);
  clearInterval(tela.atualizadorCaixa);
  tela.raiz = null;
}

export function textoCronometro(inicio, base = "Lendo o arquivo") {
  const segundos = Math.max(0, Math.round((Date.now() - inicio) / 1000));
  return `${base} · ${segundos} s`;
}

export function atualizarCronometros() {
  tela.raiz?.querySelectorAll("[data-cronometro]").forEach((el) => {
    el.textContent = textoCronometro(Number(el.dataset.cronometro), el.dataset.base);
  });
}

export async function acompanharTarefa(item, tarefaId) {
  for (;;) {
    await new Promise((resolve) => setTimeout(resolve, 800));
    const tarefa = await api.get(`/api/leituras/tarefas/${tarefaId}`);
    item.tarefa = tarefa;
    if (tarefa.status === "concluida") return tarefa.resultado;
    if (tarefa.status === "erro") throw new Error(tarefa.erro?.mensagem || "Falha ao ler o arquivo.");
    atualizarProgresso(item);
  }
}

export function ligarEventos() {
  const entrada = tela.raiz.querySelector("#entrada-arquivos");
  const camera = tela.raiz.querySelector("#entrada-camera");
  const dropzone = tela.raiz.querySelector("#dropzone");

  dropzone.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-dz]");
    if (botao?.dataset.dz === "camera") camera.click();
    else entrada.click();
  });
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); entrada.click(); }
  });
  for (const campo of [entrada, camera]) {
    campo.addEventListener("click", (e) => e.stopPropagation());
    campo.addEventListener("change", () => {
      enfileirar([...campo.files]);
      campo.value = "";
    });
  }

  const linha = tela.raiz.querySelector("#entrada-linha");
  const contador = tela.raiz.querySelector("#contador-digitos");
  linha.addEventListener("input", () => {
    const n = linha.value.replace(/\D/g, "").length;
    contador.textContent = `${n} dígito${n === 1 ? "" : "s"}${[44, 47, 48].includes(n) ? " ✓" : ""}`;
    contador.classList.toggle("ok", [44, 47, 48].includes(n));
  });
  tela.raiz.querySelector("#form-linha").addEventListener("submit", (e) => {
    e.preventDefault();
    analisarTexto(linha.value);
  });

  tela.raiz.addEventListener("click", aoClicar);
  tela.raiz.querySelector("#caixa-entrada").addEventListener("click", aoClicarCaixa);
  tela.raiz.addEventListener("input", aoDigitar);
  tela.raiz.addEventListener("change", aoAlterar);
}

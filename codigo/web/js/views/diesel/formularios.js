// Diesel · formulários: canhoto (uma ou mais linhas de combustível), compra, abastecimento, máquina e preços.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, esc, hojeISO, mensagemErro, numeroBR, parseValor, pedirTexto, toast } from "../../ui.js";
import { COMBUSTIVEIS, MEDIDORES, TIPOS_MAQUINA, litros, numero, tela } from "./estado.js";

const NOVA = "__nova__";

export async function carregarMaquinas() {
  try {
    tela.maquinas = (await api.get("/api/diesel/maquinas")).maquinas || [];
  } catch {
    tela.maquinas = tela.maquinas || [];
  }
  return tela.maquinas;
}

export async function carregarPrecos() {
  try {
    tela.precos = (await api.get("/api/diesel/precos")).precos || [];
  } catch {
    tela.precos = tela.precos || [];
  }
  return tela.precos;
}

const precoDaTabela = (combustivel) => (tela.precos || []).find((p) => p.combustivel === combustivel)?.preco || null;
const maquinaPorNome = (nome) => tela.maquinas.find((m) => m.nome === nome);
const limpar = (dados) => Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== "" && v !== null && v !== undefined));
const numeroOuVazio = (texto) => (String(texto ?? "").trim() ? parseValor(texto) : "");

function opcoesMaquina(atual = "", combustivel = "") {
  const ativas = tela.maquinas.filter((m) => m.status !== "Inativa" || m.nome === atual);
  // quem usa o combustível da linha aparece primeiro
  ativas.sort((a, b) => (combustivel && (a.combustivel === combustivel ? 0 : 1) - (b.combustivel === combustivel ? 0 : 1)) || a.nome.localeCompare(b.nome));
  const conhecida = !atual || ativas.some((m) => m.nome === atual);
  return `<option value="">Máquina…</option>
    ${ativas.map((m) => `<option value="${esc(m.nome)}" ${m.nome === atual ? "selected" : ""}>${esc(m.nome)}${m.placa ? ` · ${esc(m.placa)}` : ""}${m.combustivel ? ` (${esc(m.combustivel)})` : ""}</option>`).join("")}
    ${conhecida ? "" : `<option value="${esc(atual)}" selected>${esc(atual)}</option>`}
    <option value="${NOVA}">+ Nova máquina…</option>`;
}

const opcoesCombustivel = (atual = "", vazio = "") => `${vazio ? `<option value="">${esc(vazio)}</option>` : ""}
  ${COMBUSTIVEIS.map((c) => `<option ${c === atual ? "selected" : ""}>${c}</option>`).join("")}`;

async function cadastrarNaHora(select, combustivel = "") {
  const nome = await pedirTexto({ titulo: "Nova máquina", rotulo: "Nome da máquina",
                                  placeholder: "Ex.: Escavadeira PC200, Caminhão ABC-1D23", maximo: 60 });
  if (!nome) return null;
  try {
    const criada = await api.post("/api/diesel/maquinas", { nome, ...(combustivel ? { combustivel } : {}) });
    await carregarMaquinas();
    toast(`Máquina “${criada.nome}” cadastrada.`, "ok");
    return criada.nome;
  } catch (erro) {
    toast(mensagemErro(erro), "erro");
    return null;
  }
}

function campoArquivo(rotulo) {
  return `<div class="campo col-2"><label for="d-arquivo">${esc(rotulo)} (opcional)</label>
    <input id="d-arquivo" type="file" class="input" accept="application/pdf,image/*,.heic,.heif"></div>`;
}

async function arquivoEscolhido(el) {
  const arquivo = el.querySelector("#d-arquivo")?.files?.[0];
  return arquivo ? (await api.enviarPara("/api/diesel/arquivo", arquivo)).id : null;
}

function concluir(fechar, mensagem) {
  toast(mensagem, "ok", { duracao: 5000 });
  fechar(true);
  window.dispatchEvent(new Event("diesel:atualizar"));
}

// ------------------------------------------------------------------ canhoto (uma ou mais linhas)

function linhaHtml(linha, indice, sozinha) {
  return `<tr data-linha="${indice}">
    <td><select class="input input-sm" data-campo="combustivel" aria-label="Combustível">${opcoesCombustivel(linha.combustivel || "", "Combustível…")}</select>
      ${linha.descricao ? `<small class="sutil">lido: ${esc(linha.descricao)}</small>` : ""}</td>
    <td><input class="input input-sm num" data-campo="litros" inputmode="decimal" value="${esc(numero(linha.litros))}" aria-label="Litros"></td>
    <td><input class="input input-sm num" data-campo="preco_litro" inputmode="decimal" value="${linha.preco_litro ? esc(String(linha.preco_litro).replace(".", ",")) : ""}" placeholder="R$/L" aria-label="Preço por litro"></td>
    <td><input class="input input-sm num" data-campo="valor" inputmode="decimal" value="${linha.valor ? esc(numeroBR(linha.valor)) : ""}" placeholder="total" aria-label="Total"></td>
    <td><select class="input input-sm" data-campo="maquina" aria-label="Máquina">${opcoesMaquina(linha.maquina || "", linha.combustivel || "")}</select></td>
    <td><input class="input input-sm num" data-campo="medidor" inputmode="decimal" value="${esc(numero(linha.medidor))}" placeholder="opcional" aria-label="Horímetro ou km"></td>
    <td>${sozinha ? "" : `<button type="button" class="btn-icone perigo" data-remover-linha title="Tirar esta linha">${icone("x", 14)}</button>`}</td>
  </tr>`;
}

/** ``dados``: o que foi lido do canhoto (itens, data, posto, pedido, arquivo) · ``enviar(corpo)``: troca o POST. */
export async function formularioCanhoto(dados = {}, enviar = null) {
  await Promise.all([carregarMaquinas(), carregarPrecos()]);
  const linhas = (dados.itens && dados.itens.length ? dados.itens : [{}]).map((l) => ({ ...l }));
  if (linhas.length === 1 && dados.maquina_da_placa && !linhas[0].maquina) linhas[0].maquina = dados.maquina_da_placa;
  if (linhas.length === 1 && dados.medidor && !linhas[0].medidor) linhas[0].medidor = dados.medidor;
  const arquivoId = dados.arquivo?.id || dados.arquivo_id || null;
  const { el, fechar } = abrirModal({
    titulo: enviar ? "Conferir canhoto" : arquivoId ? "Canhoto lido — confira e lance" : "Novo abastecimento",
    tamanho: "lg",
    corpo: `${dados.erro ? `<div class="alerta aviso">${icone("alerta", 16)}<span>${esc(dados.erro)}</span></div>` : ""}
      ${arquivoId ? `<p class="sutil">${icone("clipe", 14)} <a href="/api/arquivos/${esc(arquivoId)}" target="_blank" rel="noopener">Ver o arquivo</a>
        · confira o que foi lido e escolha a máquina de cada linha.</p>` : ""}
      <form class="grade-campos" data-form-canhoto>
        <div class="campo"><label for="k-data">Data</label>
          <input id="k-data" name="data" type="date" class="input" value="${esc(String(dados.data || hojeISO()).slice(0, 10))}"></div>
        <div class="campo"><label for="k-hora">Hora</label>
          <input id="k-hora" name="hora" type="time" class="input" value="${esc(dados.hora || "")}"></div>
        <div class="campo"><label for="k-posto">Posto</label>
          <input id="k-posto" name="posto" class="input" value="${esc(dados.posto || "")}" maxlength="80"></div>
        <div class="campo"><label for="k-doc">Nº do pedido / canhoto</label>
          <input id="k-doc" name="documento" class="input" value="${esc(dados.documento || "")}" maxlength="30"></div>
        <div class="campo col-2"><label for="k-pessoa">Quem abasteceu</label>
          <input id="k-pessoa" name="pessoa" class="input" value="${esc(dados.pessoa || "")}" maxlength="60"></div>
      </form>
      <div class="tabela-wrap diesel-linhas"><table class="tabela">
        <thead><tr><th>Combustível</th><th class="num">Litros</th><th class="num">Preço/L</th><th class="num">Total (R$)</th>
          <th>Máquina</th><th class="num">Horímetro / km</th><th></th></tr></thead>
        <tbody data-linhas>${linhas.map((l, i) => linhaHtml(l, i, linhas.length === 1)).join("")}</tbody>
        <tfoot><tr><td><button type="button" class="btn btn-sm btn-fantasma" data-nova-linha>${icone("mais", 14)} Outra linha (outro combustível ou máquina)</button></td>
          <td class="num" data-total-litros></td><td></td><td class="num" data-total-valor></td><td colspan="3"></td></tr></tfoot>
      </table></div>
      ${!arquivoId && !enviar ? campoArquivo("Foto do canhoto") : ""}
      <p class="sutil">Sem o preço, vale o da tabela de preços. Cada linha vira um abastecimento da máquina escolhida e o valor
        dela (litros × preço) sai do saldo. Com o horímetro (ou o km), o sistema calcula o consumo de verdade.</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Lançar</button>`,
  });
  const corpoLinhas = el.querySelector("[data-linhas]");

  const lerLinhas = () => [...corpoLinhas.querySelectorAll("[data-linha]")].map((tr) => {
    const valor = (campo) => tr.querySelector(`[data-campo="${campo}"]`).value;
    return limpar({ combustivel: valor("combustivel"), litros: numeroOuVazio(valor("litros")),
                    preco_litro: numeroOuVazio(valor("preco_litro")), valor: numeroOuVazio(valor("valor")),
                    maquina: valor("maquina") === NOVA ? "" : valor("maquina"), medidor: numeroOuVazio(valor("medidor")) });
  });
  const redesenhar = (novas) => {
    corpoLinhas.innerHTML = novas.map((l, i) => linhaHtml(l, i, novas.length === 1)).join("");
    somar();
  };
  const somar = () => {
    const atuais = lerLinhas();
    el.querySelector("[data-total-litros]").textContent = litros(atuais.reduce((s, l) => s + (l.litros || 0), 0));
    el.querySelector("[data-total-valor]").textContent = brl(atuais.reduce((s, l) => s + (l.valor || 0), 0));
  };
  somar();

  corpoLinhas.addEventListener("input", (e) => {
    const tr = e.target.closest("[data-linha]");
    const campo = e.target.dataset.campo;
    if (!tr || !["litros", "preco_litro"].includes(campo)) { somar(); return; }
    const qtd = parseValor(tr.querySelector('[data-campo="litros"]').value);
    const preco = parseValor(tr.querySelector('[data-campo="preco_litro"]').value);
    if (qtd && preco) tr.querySelector('[data-campo="valor"]').value = numeroBR(Math.round(qtd * preco * 100) / 100);
    somar();
  });
  corpoLinhas.addEventListener("change", async (e) => {
    const tr = e.target.closest("[data-linha]");
    if (!tr) return;
    if (e.target.dataset.campo === "combustivel") {  // combustível escolhido: preço da tabela e máquinas desse combustível
      const precoCampo = tr.querySelector('[data-campo="preco_litro"]');
      const preco = precoDaTabela(e.target.value);
      if (preco && !precoCampo.value) {
        precoCampo.value = String(preco).replace(".", ",");
        precoCampo.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const maquina = tr.querySelector('[data-campo="maquina"]');
      maquina.innerHTML = opcoesMaquina(maquina.value, e.target.value);
    }
    if (e.target.dataset.campo === "maquina") {
      if (e.target.value === NOVA) {
        const combustivel = tr.querySelector('[data-campo="combustivel"]').value;
        const nome = await cadastrarNaHora(e.target, combustivel);
        e.target.innerHTML = opcoesMaquina(nome || "", combustivel);
      }
      const maquina = maquinaPorNome(e.target.value);
      const combustivel = tr.querySelector('[data-campo="combustivel"]');
      if (maquina?.combustivel && !combustivel.value) {  // linha sem combustível: vale o da máquina
        combustivel.value = maquina.combustivel;
        combustivel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
  });
  el.querySelector("[data-nova-linha]").addEventListener("click", () => redesenhar([...lerLinhas(), {}]));
  corpoLinhas.addEventListener("click", (e) => {
    const botao = e.target.closest("[data-remover-linha]");
    if (!botao) return;
    const atuais = lerLinhas();
    atuais.splice(Number(botao.closest("[data-linha]").dataset.linha), 1);
    redesenhar(atuais);
  });

  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const itens = lerLinhas().filter((l) => l.litros || l.maquina);
    if (!itens.length || itens.some((l) => !l.litros)) { toast("Informe os litros de cada linha.", "aviso"); return; }
    const semMaquina = itens.findIndex((l) => !l.maquina);
    if (semMaquina >= 0) { toast(`Escolha a máquina da linha ${semMaquina + 1}.`, "aviso"); return; }
    const comum = limpar(Object.fromEntries(new FormData(el.querySelector("[data-form-canhoto]"))));
    const botao = el.querySelector("[data-salvar]");
    botao.setAttribute("disabled", "");
    try {
      const anexo = arquivoId || await arquivoEscolhido(el);
      if (enviar) await enviar({ ...comum, tipo: "canhoto", itens });
      else await api.post("/api/diesel/canhoto", { ...comum, itens, ...(anexo ? { arquivo_id: anexo } : {}) });
      concluir(fechar, itens.length > 1 ? `${itens.length} abastecimentos lançados (${litros(itens.reduce((s, l) => s + l.litros, 0))}).`
        : `${litros(itens[0].litros)} lançados em ${itens[0].maquina}.`);
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
      botao.removeAttribute("disabled");
    }
  });
}

// ------------------------------------------------------------------ compra

/** ``registro``: compra a editar (ou lida do comprovante) · ``enviar(corpo)``: troca o POST (conferência). */
export async function formularioCompra(registro = null, enviar = null) {
  await carregarPrecos();
  const r = registro || {};
  const edicao = Boolean(r.id);
  const arquivoId = r.arquivo?.id || r.arquivo_id || null;
  const combustivel = r.combustivel || (r.itens?.length === 1 ? r.itens[0].combustivel : "") || COMBUSTIVEIS[0];
  const { el, fechar } = abrirModal({
    titulo: edicao ? "Editar compra de diesel" : enviar ? "Conferir compra de diesel" : arquivoId ? "Comprovante lido — confira a compra" : "Nova compra de diesel",
    corpo: `<form class="grade-campos" data-form-compra>
      <div class="campo"><label for="c-comb">Combustível</label>
        <select id="c-comb" name="combustivel" class="input">${opcoesCombustivel(combustivel)}</select></div>
      <div class="campo"><label for="c-litros">Litros comprados</label>
        <input id="c-litros" name="litros" class="input" inputmode="decimal" value="${esc(numero(r.litros || (edicao ? "" : 1000)))}" required autofocus></div>
      <div class="campo"><label for="c-preco">Preço por litro (R$)</label>
        <input id="c-preco" name="preco_litro" class="input" inputmode="decimal"
          value="${esc(String(r.preco_litro || (edicao ? "" : precoDaTabela(combustivel) || "")).replace(".", ","))}" placeholder="7,450"></div>
      <div class="campo"><label for="c-valor">Valor pago (R$)</label>
        <input id="c-valor" name="valor" class="input" inputmode="decimal" value="${r.valor ? esc(numeroBR(r.valor)) : ""}" placeholder="7.450,00"></div>
      <div class="campo"><label for="c-data">Data</label>
        <input id="c-data" name="data" type="date" class="input" value="${esc(String(r.data || hojeISO()).slice(0, 10))}"></div>
      <div class="campo"><label for="c-posto">Posto</label>
        <input id="c-posto" name="posto" class="input" value="${esc(r.posto || "")}" maxlength="80"></div>
      <div class="campo"><label for="c-forma">Forma de pagamento</label>
        <input id="c-forma" name="forma" class="input" value="${esc(r.forma || "")}" maxlength="20" placeholder="Pix, boleto…"></div>
      <div class="campo"><label for="c-doc">Nota / cupom</label>
        <input id="c-doc" name="documento" class="input" value="${esc(r.documento || "")}" maxlength="30"></div>
      <div class="campo col-2"><label for="c-obs">Observações</label>
        <input id="c-obs" name="observacoes" class="input" value="${esc(r.observacoes || "")}" maxlength="300"></div>
      ${edicao || enviar || arquivoId ? "" : campoArquivo("Comprovante do pagamento")}
    </form>
    <p class="sutil" style="margin-top:10px">O valor pago entra no saldo do diesel (serve para S10 e comum). Litros × preço preenche o valor sozinho.</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} ${edicao ? "Salvar" : "Lançar compra"}</button>`,
  });
  const formulario = el.querySelector("[data-form-compra]");
  const recalcular = () => {
    const qtd = parseValor(el.querySelector("#c-litros").value);
    const preco = parseValor(el.querySelector("#c-preco").value);
    if (qtd && preco) el.querySelector("#c-valor").value = numeroBR(Math.round(qtd * preco * 100) / 100);
  };
  el.querySelector("#c-litros").addEventListener("input", recalcular);
  el.querySelector("#c-preco").addEventListener("input", recalcular);
  el.querySelector("#c-comb").addEventListener("change", (e) => {
    const preco = precoDaTabela(e.target.value);
    if (preco) { el.querySelector("#c-preco").value = String(preco).replace(".", ","); recalcular(); }
  });
  const salvar = async (evento) => {
    evento?.preventDefault();
    const dados = Object.fromEntries(new FormData(formulario));
    const corpo = limpar({ ...dados, litros: parseValor(dados.litros), valor: numeroOuVazio(dados.valor),
                           preco_litro: numeroOuVazio(dados.preco_litro) });
    if (!corpo.litros) { toast("Informe os litros.", "aviso"); return; }
    try {
      const anexo = arquivoId || await arquivoEscolhido(el);
      if (enviar) await enviar({ ...corpo, tipo: "compra", itens: [corpo] });
      else if (edicao) await api.put(`/api/diesel/compras/${r.id}`, corpo);
      else await api.post("/api/diesel/compras", { ...corpo, ...(anexo ? { arquivo_id: anexo } : {}) });
      concluir(fechar, edicao ? "Compra atualizada." : `Compra lançada: ${litros(corpo.litros)} de ${corpo.combustivel} entraram no saldo.`);
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  formulario.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

// ------------------------------------------------------------------ editar um abastecimento

export async function formularioAbastecimento(registro) {
  await Promise.all([carregarMaquinas(), carregarPrecos()]);
  const r = registro || {};
  const { el, fechar } = abrirModal({
    titulo: "Editar abastecimento",
    corpo: `<form class="grade-campos" data-form-abastecimento>
      <div class="campo col-2"><label for="a-maquina">Máquina</label>
        <select id="a-maquina" name="maquina" class="input">${opcoesMaquina(r.maquina || "", r.combustivel || "")}</select></div>
      <div class="campo"><label for="a-comb">Combustível</label>
        <select id="a-comb" name="combustivel" class="input">${opcoesCombustivel(r.combustivel || COMBUSTIVEIS[0])}</select></div>
      <div class="campo"><label for="a-litros">Litros</label>
        <input id="a-litros" name="litros" class="input" inputmode="decimal" value="${esc(numero(r.litros))}"></div>
      <div class="campo"><label for="a-preco">Preço por litro (R$)</label>
        <input id="a-preco" name="preco_litro" class="input" inputmode="decimal" value="${r.preco_litro ? esc(String(r.preco_litro).replace(".", ",")) : ""}"></div>
      <div class="campo"><label for="a-valor">Total (R$)</label>
        <input id="a-valor" name="valor" class="input" inputmode="decimal" value="${r.valor ? esc(numeroBR(r.valor)) : ""}"></div>
      <div class="campo"><label for="a-medidor">Horímetro / km</label>
        <input id="a-medidor" name="medidor" class="input" inputmode="decimal" value="${esc(numero(r.medidor))}"></div>
      <div class="campo"><label for="a-data">Data</label>
        <input id="a-data" name="data" type="date" class="input" value="${esc(String(r.data || hojeISO()).slice(0, 10))}"></div>
      <div class="campo"><label for="a-posto">Posto</label>
        <input id="a-posto" name="posto" class="input" value="${esc(r.posto || "")}" maxlength="80"></div>
      <div class="campo"><label for="a-doc">Nº do pedido</label>
        <input id="a-doc" name="documento" class="input" value="${esc(r.documento || "")}" maxlength="30"></div>
      <div class="campo"><label for="a-pessoa">Quem abasteceu</label>
        <input id="a-pessoa" name="pessoa" class="input" value="${esc(r.pessoa || "")}" maxlength="60"></div>
      <div class="campo col-2"><label for="a-obs">Observações</label>
        <input id="a-obs" name="observacoes" class="input" value="${esc(r.observacoes || "")}" maxlength="300"></div>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });
  const recalcular = () => {
    const qtd = parseValor(el.querySelector("#a-litros").value);
    const preco = parseValor(el.querySelector("#a-preco").value);
    if (qtd && preco) el.querySelector("#a-valor").value = numeroBR(Math.round(qtd * preco * 100) / 100);
  };
  el.querySelector("#a-litros").addEventListener("input", recalcular);
  el.querySelector("#a-preco").addEventListener("input", recalcular);
  el.querySelector("#a-maquina").addEventListener("change", async (e) => {
    if (e.target.value !== NOVA) return;
    const nome = await cadastrarNaHora(e.target, el.querySelector("#a-comb").value);
    e.target.innerHTML = opcoesMaquina(nome || r.maquina || "");
  });
  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const dados = Object.fromEntries(new FormData(el.querySelector("[data-form-abastecimento]")));
    const corpo = { ...dados, litros: parseValor(dados.litros), preco_litro: numeroOuVazio(dados.preco_litro) || null,
                    valor: numeroOuVazio(dados.valor) || null, medidor: numeroOuVazio(dados.medidor) || null };
    if (!corpo.litros) { toast("Informe os litros.", "aviso"); return; }
    if (!corpo.maquina || corpo.maquina === NOVA) { toast("Escolha a máquina.", "aviso"); return; }
    try {
      await api.put(`/api/diesel/abastecimentos/${r.id}`, corpo);
      concluir(fechar, "Abastecimento atualizado.");
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  });
}

// ------------------------------------------------------------------ máquina

export function formularioMaquina(maquina = null) {
  const m = maquina || {};
  const edicao = Boolean(m.id);
  const { el, fechar } = abrirModal({
    titulo: edicao ? `Máquina · ${m.nome}` : "Nova máquina",
    corpo: `<form class="grade-campos" data-form-maquina>
      <div class="campo col-2"><label for="m-nome">Nome</label>
        <input id="m-nome" name="nome" class="input" value="${esc(m.nome || "")}" maxlength="60" required autofocus
          placeholder="Ex.: Escavadeira PC200"></div>
      <div class="campo"><label for="m-tipo">Tipo</label>
        <select id="m-tipo" name="tipo" class="input">${TIPOS_MAQUINA.map((t) => `<option ${t === (m.tipo || "Máquina") ? "selected" : ""}>${t}</option>`).join("")}</select></div>
      <div class="campo"><label for="m-placa">Placa / prefixo</label>
        <input id="m-placa" name="placa" class="input" value="${esc(m.placa || "")}" maxlength="16" placeholder="ABC-1D23"></div>
      <div class="campo"><label for="m-comb">Combustível que usa</label>
        <select id="m-comb" name="combustivel" class="input">${opcoesCombustivel(m.combustivel ?? (edicao ? "" : COMBUSTIVEIS[0]), "Não definido")}</select></div>
      <div class="campo"><label for="m-medidor">Como medir o consumo</label>
        <select id="m-medidor" name="medidor" class="input">${MEDIDORES.map(([v, r]) => `<option value="${v}" ${v === (m.medidor ?? (edicao ? "" : "horas")) ? "selected" : ""}>${r}</option>`).join("")}</select></div>
      ${edicao ? `<div class="campo"><label for="m-status">Situação</label>
        <select id="m-status" name="status" class="input">${["Ativa", "Inativa"].map((s) => `<option ${s === m.status ? "selected" : ""}>${s}</option>`).join("")}</select></div>` : ""}
      <div class="campo col-2"><label for="m-obs">Observações</label>
        <input id="m-obs" name="observacoes" class="input" value="${esc(m.observacoes || "")}" maxlength="300"></div>
    </form>
    <p class="sutil" style="margin-top:10px">O combustível da máquina completa as linhas do canhoto que não dizem qual é, e
      a máquina aparece primeiro quando a linha é daquele combustível. Máquinas e geradores costumam usar o
      <strong>horímetro</strong> (litros por hora); caminhões, o <strong>hodômetro</strong> (km por litro).</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });
  const formulario = el.querySelector("[data-form-maquina]");
  el.querySelector("#m-tipo").addEventListener("change", (e) => {
    if (edicao) return;
    el.querySelector("#m-medidor").value = ["Caminhão", "Veículo"].includes(e.target.value) ? "km"
      : ["Máquina", "Gerador"].includes(e.target.value) ? "horas" : "";
  });
  const salvar = async (evento) => {
    evento?.preventDefault();
    const corpo = Object.fromEntries(new FormData(formulario));
    if (!corpo.nome?.trim()) { toast("Informe o nome da máquina.", "aviso"); return; }
    try {
      if (edicao) await api.put(`/api/diesel/maquinas/${m.id}`, corpo);
      else await api.post("/api/diesel/maquinas", corpo);
      concluir(fechar, edicao ? "Máquina atualizada." : "Máquina cadastrada.");
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  };
  formulario.addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

// ------------------------------------------------------------------ tabela de preços

export async function formularioPrecos() {
  const lista = await carregarPrecos();
  const { el, fechar } = abrirModal({
    titulo: "Preço que pagamos no litro",
    corpo: `<form class="grade-campos" data-form-precos>
      ${lista.map((p) => `<div class="campo"><label for="p-${esc(p.combustivel)}">${esc(p.combustivel)}</label>
        <div class="input-prefixo"><span>R$</span><input id="p-${esc(p.combustivel)}" name="${esc(p.combustivel)}" class="input"
          inputmode="decimal" value="${p.preco ? esc(String(p.preco).replace(".", ",")) : ""}" placeholder="0,000"></div>
        ${p.atualizado_em ? `<small class="sutil">desde ${esc(p.atualizado_em.slice(8, 10))}/${esc(p.atualizado_em.slice(5, 7))}${p.por ? ` · ${esc(p.por)}` : ""}</small>` : ""}</div>`).join("")}
    </form>
    <p class="sutil" style="margin-top:10px">Vale para o canhoto que não traz o preço: o abastecimento sai com litros × este
      preço. Quando o canhoto ou a compra trazem o preço, vale o deles. Deixe em branco o que vocês não usam.</p>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar preços</button>`,
  });
  el.querySelector("[data-salvar]").addEventListener("click", async () => {
    const dados = Object.fromEntries(new FormData(el.querySelector("[data-form-precos]")));
    const precos = Object.fromEntries(Object.entries(dados).map(([c, v]) => [c, String(v).trim() ? parseValor(v) : 0]));
    if (Object.values(precos).some((v) => Number.isNaN(v))) { toast("Algum preço está inválido.", "aviso"); return; }
    try {
      await api.post("/api/diesel/precos", { precos });
      concluir(fechar, "Preços salvos.");
    } catch (erro) {
      toast(mensagemErro(erro), "erro", { duracao: 6000 });
    }
  });
}

// ------------------------------------------------------------------ mandar o arquivo pela tela

/** Lê o canhoto ou o comprovante escolhido (ou arrastado) e abre o formulário já preenchido. */
export async function lerArquivo(arquivo) {
  if (!arquivo) return;
  toast(`Lendo ${arquivo.name}… (foto pode levar alguns segundos)`, "info", { duracao: 4000 });
  let lido;
  try {
    lido = await api.enviarPara("/api/diesel/analisar", arquivo);
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
    return;
  }
  let tipo = lido.tipo;
  if (!tipo) tipo = await perguntarTipo(lido);
  if (!tipo) return;
  if (tipo === "compra") formularioCompra({ ...lido, id: undefined });
  else formularioCanhoto(lido);
}

function perguntarTipo(lido) {
  return new Promise((resolve) => {
    const { el, fechar } = abrirModal({
      titulo: "O que é este arquivo?",
      corpo: `<p>Não deu para saber sozinho${lido.litros ? ` (li ${litros(lido.litros)})` : ""}. É o comprovante da compra ou um canhoto?</p>`,
      rodape: `<button class="btn" data-tipo="compra">${icone("carteira", 15)} Comprovante da compra</button>
        <button class="btn btn-primario" data-tipo="canhoto">${icone("diesel", 15)} Canhoto de abastecimento</button>`,
      aoFechar: () => resolve(null),
    });
    el.querySelectorAll("[data-tipo]").forEach((b) => b.addEventListener("click", () => {
      const escolhido = b.dataset.tipo;
      resolve(escolhido);
      fechar(escolhido);
    }));
  });
}

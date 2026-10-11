// Empresas e fechamentos · notas fiscais lançadas (lista, lançamento manual e edição).
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, esc, hojeISO, parseValor, toast, uid } from "../../ui.js";
import { carregarDados, deuCerto, numero, opcoes, opcoesCompetencia, opcoesEmpresa, selo, tentar, vazio } from "./comum.js";
import { STATUS_NOTA, UNIDADES, tela } from "./estado.js";

export async function htmlNotas() {
  const resposta = await tentar(() => api.get("/api/notas?limite=500"));
  const notas = resposta?.notas || [];
  return `
    <section class="card barra-filtros">
      <div class="filtros-linha">
        <select class="input input-sm" data-filtro="empresa" aria-label="Empresa">${opcoesEmpresa(tela.filtroEmpresa || "", "Todas as empresas")}</select>
        <select class="input input-sm" data-filtro="status" aria-label="Situação">
          <option value="">Todas as situações</option>${opcoes(STATUS_NOTA, tela.filtroStatus || "")}</select>
        <button class="btn btn-primario btn-sm" data-acao="nova-nota">${icone("mais", 15)} Lançar nota fiscal</button>
      </div>
    </section>
    <section class="card tabela-card">
      <div class="tabela-wrap">${tabela(notas)}</div>
    </section>`;
}

function tabela(notas) {
  const filtradas = notas.filter((n) => (!tela.filtroEmpresa || n.empresa === tela.filtroEmpresa)
    && (!tela.filtroStatus || n.status === tela.filtroStatus));
  if (!filtradas.length) {
    return vazio(icone("lista", 26), "Nenhuma nota fiscal",
                 "Mande a nota (XML, PDF ou foto) para o bot de notas ou lance aqui pela tela.");
  }
  return `<table class="tabela">
    <thead><tr><th>Data</th><th>Empresa</th><th>Material</th><th>Un.</th><th class="num">Quant.</th>
      <th class="num">Valor uni.</th><th class="num">Valor total</th><th>NF</th><th>Pedido</th><th>Fechamento</th>
      <th>Situação</th><th class="col-acoes"></th></tr></thead>
    <tbody>${filtradas.map((n) => `<tr data-nota="${n.id}">
      <td>${dataBR(n.data)}</td><td>${esc(n.empresa || "")}</td><td>${esc(n.material || "")}</td>
      <td>${esc(n.unidade || "")}</td><td class="num">${numero(n.quantidade)}</td>
      <td class="num">${brl(n.valor_unitario)}</td><td class="num">${brl(n.valor_total)}</td>
      <td>${esc(n.numero_nf || "")}</td><td>${esc(n.pedido || "")}</td><td>${esc(n.competencia || "")}</td>
      <td>${selo(n.status)}${n.status === "Parcial" ? `<small class="sutil"> ${brl(n.valor_recebido)}</small>` : ""}</td>
      <td class="col-acoes"><button class="btn-icone btn-sm" data-acao="editar-nota" data-id="${n.id}"
        title="Editar">${icone("editar", 15)}</button></td></tr>`).join("")}</tbody>
  </table>`;
}

// ------------------------------------------------------------------ lançamento manual

function linhaItem(item = {}) {
  const id = uid();
  return `<tr data-item="${id}">
    <td><input class="input input-sm" name="material" value="${esc(item.material || "")}" placeholder="Brita 01" maxlength="80"></td>
    <td><select class="input input-sm" name="unidade">${opcoes(UNIDADES, item.unidade || "M³")}</select></td>
    <td><input class="input input-sm num" name="quantidade" inputmode="decimal" value="${item.quantidade ?? ""}"></td>
    <td><input class="input input-sm num" name="valor_unitario" inputmode="decimal" value="${item.valor_unitario ?? ""}"></td>
    <td><input class="input input-sm num" name="valor_total" inputmode="decimal" value="${item.valor_total ?? ""}" placeholder="calculado"></td>
    <td><input class="input input-sm" name="numero_nf" value="${esc(item.numero_nf || "")}" maxlength="15"></td>
    <td><input class="input input-sm" name="pedido" value="${esc(item.pedido || "")}" maxlength="15"></td>
    <td class="col-acoes"><button type="button" class="btn-icone btn-sm" data-remover-item title="Remover">${icone("x", 15)}</button></td>
  </tr>`;
}

/** ``enviar(corpo)`` troca o lançamento direto pela confirmação de um arquivo recebido no bot. */
export function formularioNota(dadosIniciais = {}, enviar = null) {
  const itens = dadosIniciais.itens?.length ? dadosIniciais.itens : [{}];
  const { el, fechar } = abrirModal({
    titulo: "Lançar nota fiscal",
    tamanho: "grande",
    corpo: `<form data-form-nota>
      <div class="grade-campos">
        <div class="campo"><label for="n-empresa">Empresa</label>
          <select id="n-empresa" name="empresa" class="input" required>${opcoesEmpresa(dadosIniciais.empresa || "")}</select></div>
        <div class="campo"><label for="n-data">Data da nota</label>
          <input id="n-data" name="data" type="date" class="input" value="${dadosIniciais.data || hojeISO()}" required></div>
        <div class="campo"><label for="n-comp">Fechamento</label>
          <select id="n-comp" name="competencia" class="input"><option value="">Pela data da nota</option>${opcoesCompetencia("")}</select></div>
      </div>
      <p class="sutil" style="margin:12px 0 6px">Uma linha por material, como no fechamento. O valor total é calculado
        quando você deixa em branco.</p>
      <div class="tabela-wrap"><table class="tabela tabela-itens">
        <thead><tr><th>Material</th><th>Un.</th><th class="num">Quant.</th><th class="num">Valor uni.</th>
          <th class="num">Valor total</th><th>NF</th><th>Pedido</th><th></th></tr></thead>
        <tbody data-itens>${itens.map(linhaItem).join("")}</tbody>
      </table></div>
      <button type="button" class="btn btn-sm btn-fantasma" data-novo-item>${icone("mais", 14)} Adicionar material</button>
    </form>`,
    rodape: `<button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Lançar</button>`,
  });

  el.querySelector("[data-novo-item]").addEventListener("click", () => {
    el.querySelector("[data-itens]").insertAdjacentHTML("beforeend", linhaItem());
  });
  el.addEventListener("click", (e) => {
    if (e.target.closest("[data-remover-item]")) {
      const corpo = el.querySelector("[data-itens]");
      if (corpo.children.length > 1) e.target.closest("tr").remove();
    }
  });

  const salvar = async (evento) => {
    evento?.preventDefault();
    const formulario = el.querySelector("[data-form-nota]");
    const empresa = formulario.empresa.value;
    const data = formulario.data.value;
    if (!empresa) return;
    const itensEnviados = [...el.querySelectorAll("[data-itens] tr")].map((linha) => {
      const campo = (nome) => linha.querySelector(`[name="${nome}"]`).value.trim();
      return {
        data,
        material: campo("material"),
        unidade: campo("unidade"),
        quantidade: parseValor(campo("quantidade")),
        valor_unitario: parseValor(campo("valor_unitario")),
        valor_total: parseValor(campo("valor_total")),
        numero_nf: campo("numero_nf"),
        pedido: campo("pedido"),
      };
    }).filter((i) => i.valor_total || (i.quantidade && i.valor_unitario));
    if (!itensEnviados.length) return;
    const corpo = { empresa, itens: itensEnviados, competencia: formulario.competencia.value || null };
    const resultado = await tentar(() => (enviar ? enviar(corpo) : api.post("/api/notas", corpo)), "Nota fiscal lançada.");
    if (!resultado) return;
    fechar(true);
    await carregarDados();
    window.dispatchEvent(new Event("empresas:atualizar"));
  };
  el.querySelector("[data-form-nota]").addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
}

export async function editarNota(id) {
  const resposta = await tentar(() => api.get("/api/notas?limite=2000"));
  const nota = resposta?.notas.find((n) => n.id === Number(id));
  if (!nota) return;
  const irmas = (resposta.notas || []).filter((n) => n.numero_nf && n.numero_nf === nota.numero_nf
    && n.empresa === nota.empresa);
  const { el, fechar } = abrirModal({
    titulo: `Nota fiscal ${nota.numero_nf || `#${nota.id}`} · ${nota.empresa}`,
    corpo: `<form class="grade-campos" data-form-edicao>
      <div class="campo"><label for="ne-data">Data</label>
        <input id="ne-data" name="data" type="date" class="input" value="${nota.data || ""}"></div>
      <div class="campo"><label for="ne-nf">Nota fiscal</label>
        <input id="ne-nf" name="numero_nf" class="input" value="${esc(nota.numero_nf || "")}" maxlength="15"></div>
      <div class="campo"><label for="ne-pedido">Pedido</label>
        <input id="ne-pedido" name="pedido" class="input" value="${esc(nota.pedido || "")}" maxlength="15"></div>
      <div class="campo col-2"><label for="ne-material">Material</label>
        <input id="ne-material" name="material" class="input" value="${esc(nota.material || "")}" maxlength="80"></div>
      <div class="campo"><label for="ne-unidade">Unidade</label>
        <select id="ne-unidade" name="unidade" class="input">${opcoes(UNIDADES, nota.unidade || "M³")}</select></div>
      <div class="campo"><label for="ne-quant">Quantidade</label>
        <input id="ne-quant" name="quantidade" class="input" inputmode="decimal" value="${nota.quantidade ?? ""}"></div>
      <div class="campo"><label for="ne-uni">Valor unitário</label>
        <input id="ne-uni" name="valor_unitario" class="input" inputmode="decimal" value="${nota.valor_unitario ?? ""}"></div>
      <div class="campo"><label for="ne-total">Valor total</label>
        <input id="ne-total" name="valor_total" class="input" inputmode="decimal" value="${nota.valor_total ?? ""}"></div>
      <div class="campo"><label for="ne-comp">Fechamento</label>
        <select id="ne-comp" name="competencia" class="input">${opcoesCompetencia(nota.competencia)}</select></div>
      <div class="campo"><label for="ne-status">Situação</label>
        <select id="ne-status" name="status" class="input">${opcoes(STATUS_NOTA, nota.status)}</select></div>
      <div class="campo"><label for="ne-recebido">Valor recebido</label>
        <input id="ne-recebido" name="valor_recebido" class="input" inputmode="decimal" value="${nota.valor_recebido ?? ""}"></div>
      <div class="campo col-2"><label for="ne-obs">Observações</label>
        <input id="ne-obs" name="observacoes" class="input" value="${esc(nota.observacoes || "")}" maxlength="200"></div>
      ${irmas.length > 1 ? `<label class="opcao-permissao col-2">
        <input type="checkbox" name="todas_da_nota" checked>
        <span>Mover <strong>todas as ${irmas.length} linhas da NF ${esc(nota.numero_nf)}</strong> para o fechamento escolhido</span>
      </label>` : ""}
    </form>
    <p class="sutil" style="margin-top:10px">O fechamento é escolhido pela data da nota, mas dá para mudar: uma nota que
      chegou depois do fechamento do mês pode entrar no seguinte.</p>
    ${nota.arquivo ? `<p class="sutil" style="margin-top:10px">${icone("clipe", 14)}
      <a href="/${esc(nota.arquivo)}" target="_blank" rel="noopener">${esc(nota.arquivo_nome || "arquivo da nota")}</a></p>` : ""}`,
    rodape: `<button class="btn btn-perigo btn-fantasma" data-excluir>${icone("lixeira", 15)} Excluir</button>
             <button class="btn btn-fantasma" data-fechar>Cancelar</button>
             <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });

  const salvar = async (evento) => {
    evento?.preventDefault();
    const dados = Object.fromEntries(new FormData(el.querySelector("[data-form-edicao]")));
    ["quantidade", "valor_unitario", "valor_total", "valor_recebido"].forEach((campo) => {
      dados[campo] = dados[campo] === "" ? null : parseValor(dados[campo]);
    });
    dados.todas_da_nota = Boolean(dados.todas_da_nota);
    const corpo = Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== "" && v !== undefined));
    const salva = await tentar(() => api.put(`/api/notas/${nota.id}`, corpo), "Nota atualizada.");
    if (salva) {
      if (salva.linhas_movidas > 1) {
        toast(`${salva.linhas_movidas} linhas da NF ${nota.numero_nf} foram para o fechamento ${corpo.competencia}.`,
              "ok", { duracao: 6000 });
      }
      fechar(true);
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
  };
  el.querySelector("[data-form-edicao]").addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
  el.querySelector("[data-excluir]").addEventListener("click", async () => {
    if (!await confirmar({ titulo: "Excluir lançamento", mensagem: "Excluir esta linha do fechamento?",
                           textoConfirmar: "Excluir", perigo: true })) return;
    if (deuCerto(await tentar(() => api.del(`/api/notas/${nota.id}`), "Lançamento excluído."))) {
      fechar(true);
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
  });
}

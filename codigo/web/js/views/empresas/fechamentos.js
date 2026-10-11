// Empresas e fechamentos · cartões das empresas e o fechamento no formato da planilha usada hoje.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { abrirModal, brl, confirmar, dataBR, esc, toast } from "../../ui.js";
import { carregarDados, deuCerto, numero, opcoes, opcoesCompetencia, selo, tentar, tituloCompetencia, vazio } from "./comum.js";
import { tela } from "./estado.js";

export function htmlFechamentos() {
  const empresas = tela.dados?.empresas || [];
  const competencia = tela.competencia || empresas[0]?.competencia || "";
  const soma = (pegar) => empresas.reduce((s, e) => s + pegar(e), 0);
  const atrasado = soma((e) => e.atrasado);
  return `
    <section class="card barra-filtros emp-mes">
      <label class="campo">
        <span class="sutil">Fechamento</span>
        <select class="input" data-campo="competencia" aria-label="Fechamento">${opcoesCompetencia(competencia)}</select>
      </label>
      <p class="sutil">Os números abaixo são só deste fechamento.</p>
      <div class="linha-botoes">
        <button class="btn btn-sm" data-acao="nova-empresa">${icone("mais", 15)} Nova empresa</button>
        <button class="btn btn-sm" data-acao="enviar-fechamentos">${icone("telegram", 15)} Enviar fechamentos agora</button>
      </div>
    </section>

    <section class="resumo-lista">
      <div class="resumo-item"><span>Empresas com lançamento</span>
        <strong>${empresas.filter((e) => e.fechamento.quantidade).length} de ${empresas.length}</strong></div>
      <div class="resumo-item"><span>Total do fechamento</span><strong>${brl(soma((e) => e.fechamento.total))}</strong></div>
      <div class="resumo-item"><span>Já recebido</span><strong class="ok">${brl(soma((e) => e.fechamento.recebido))}</strong></div>
      <div class="resumo-item"><span>Falta receber</span>
        <strong class="${soma((e) => e.fechamento.falta) > 0.01 ? "erro" : "ok"}">${brl(soma((e) => e.fechamento.falta))}</strong></div>
      <div class="resumo-item"><span>Cheques em carteira</span>
        <strong>${brl(soma((e) => e.cheques.valor))}</strong></div>
    </section>
    ${atrasado > 0.01 ? `<div class="alerta aviso">${icone("alerta", 16)}<span>Fora deste fechamento, ainda há
      <strong>${brl(atrasado)}</strong> a receber de fechamentos anteriores. Escolha o mês acima para ver.</span></div>` : ""}

    <section class="emp-cartoes">
      ${empresas.length ? empresas.map(cartao).join("") : `<div class="card col-inteira">${vazio(icone("carteira", 26),
        "Nenhuma empresa ainda", "Cadastre a primeira empresa ou mande uma nota fiscal para o bot de notas: a empresa é cadastrada sozinha.")}</div>`}
    </section>

    <section class="card" id="emp-fechamento">${tela.empresa ? "" : `<div class="vazio-linha sutil">
      ${icone("info", 16)} Escolha uma empresa acima para ver o fechamento dela.</div>`}</section>`;
}

function cartao(e) {
  const falta = e.fechamento.falta;
  const alerta = falta > 0.01 ? "erro" : e.fechamento.total ? "ok" : "";
  return `
    <article class="card emp-cartao ${tela.empresa === e.nome ? "ativo" : ""} ${e.fechamento.quantidade ? "" : "sem-lancamento"}"
      data-empresa="${esc(e.nome)}" tabindex="0" role="button">
      <header><h3>${esc(e.nome)}</h3>${selo(e.status)}</header>
      <p class="sutil">${esc(e.cnpj || "sem CNPJ")} · fecha todo dia ${e.dia_fechamento}</p>
      <div class="emp-numeros">
        <div><span>Fechamento de ${esc(tituloCompetencia(e.competencia))}</span><strong>${brl(e.fechamento.total)}</strong>
          <small>${e.fechamento.quantidade} lançamento(s) · ${dataBR(e.periodo.inicio)} a ${dataBR(e.periodo.fim)}</small></div>
        <div><span>Falta receber neste fechamento</span><strong class="${alerta}">${brl(falta)}</strong>
          <small>${e.fechamento.recebido > 0.01 ? `${brl(e.fechamento.recebido)} já recebido` : "nada recebido ainda"}</small></div>
      </div>
      ${e.atrasado > 0.01 ? `<p class="emp-cheques aviso">${icone("alerta", 14)} ${brl(e.atrasado)} de fechamentos anteriores</p>` : ""}
      ${e.cheques.quantidade ? `<p class="emp-cheques">${icone("arquivo", 14)} ${e.cheques.quantidade} cheque(s) em carteira ·
        ${brl(e.cheques.valor)}</p>` : ""}
      <div class="emp-acoes">
        <button class="btn btn-sm" data-acao="ver-fechamento" data-empresa-id="${e.id}">${icone("lista", 14)} Ver fechamento</button>
        <button class="btn btn-sm btn-fantasma" data-acao="editar-empresa" data-empresa-id="${e.id}">${icone("editar", 14)} Editar</button>
      </div>
    </article>`;
}

// ------------------------------------------------------------------ fechamento de uma empresa

export async function abrirFechamento(empresaId, competencia = "") {
  const destino = tela.raiz?.querySelector("#emp-fechamento");
  if (!destino) return;
  destino.innerHTML = `<div class="esqueleto" style="height:220px"></div>`;
  const mes = competencia || tela.competencia || "";
  const url = `/api/empresas/${empresaId}/fechamento${mes ? `?competencia=${mes}` : ""}`;
  const f = await tentar(() => api.get(url));
  if (!f || !tela.raiz) return;
  tela.empresa = f.empresa;
  tela.empresaId = empresaId;
  tela.competencia = f.competencia;
  tela.fechamento = f;
  tela.raiz.querySelectorAll("[data-empresa]").forEach((c) => c.classList.toggle("ativo", c.dataset.empresa === f.empresa));
  destino.innerHTML = htmlTabelaFechamento(f);
}

export function htmlTabelaFechamento(f) {
  const t = f.totais;
  const minha = tela.dados?.config?.minha_empresa || {};
  return `
    <div class="fechamento-topo">
      <div>
        <h3>Fechamento ${esc(f.empresa)}</h3>
        <p class="sutil">${esc(tituloCompetencia(f.competencia))} · período de ${dataBR(f.inicio)} a ${dataBR(f.fim)}
          ${f.fechado ? "· período encerrado" : "· período em andamento"}</p>
      </div>
      <div class="fechamento-acoes">
        <a class="btn btn-sm" href="/api/empresas/${f.empresa_id}/fechamento/arquivo?competencia=${f.competencia}">
          ${icone("planilha", 14)} Excel</a>
        <a class="btn btn-sm" href="/api/empresas/${f.empresa_id}/fechamento/arquivo?formato=pdf&competencia=${f.competencia}">
          ${icone("relatorio", 14)} PDF</a>
      </div>
    </div>

    <div class="tabela-wrap fechamento-planilha">
      <table class="tabela tabela-fechamento">
        <caption>${esc([minha.nome, minha.cnpj].filter(Boolean).join(" ") || "Configure a sua empresa na aba Bot de notas")}</caption>
        <thead>
          <tr><th>DATA</th><th>MATERIAL</th><th>UNIDADE</th><th class="num">QUANT.</th><th class="num">VALOR UNI.</th>
            <th class="num">VALOR TOTAL</th><th>NOTA FISCAL</th><th>Nº PEDIDO</th><th>Situação</th><th class="col-acoes"></th></tr>
        </thead>
        <tbody>
          ${f.linhas.length ? f.linhas.map((l) => `<tr data-nota="${l.id}">
            <td>${dataBR(l.data)}</td><td>${esc(l.material || "")}</td><td>${esc(l.unidade || "")}</td>
            <td class="num">${numero(l.quantidade)}</td><td class="num">${brl(l.valor_unitario)}</td>
            <td class="num">${brl(l.valor_total)}</td><td>${esc(l.numero_nf || "")}</td><td>${esc(l.pedido || "")}</td>
            <td>${selo(l.status)}${l.status === "Parcial" ? `<small class="sutil"> recebido ${brl(l.valor_recebido)}</small>` : ""}</td>
            <td class="col-acoes"><button class="btn-icone btn-sm" data-acao="editar-nota" data-id="${l.id}"
              title="Editar lançamento">${icone("editar", 15)}</button></td></tr>`).join("")
            : `<tr><td colspan="10" class="sutil" style="text-align:center;padding:18px">Nenhuma nota fiscal neste fechamento.</td></tr>`}
        </tbody>
        <tfoot>
          <tr><td colspan="5">TOTAL</td><td class="num">${brl(t.total)}</td><td colspan="4"></td></tr>
        </tfoot>
      </table>
    </div>

    <div class="fechamento-resumo">
      <div><span>Total do fechamento</span><strong>${brl(t.total)}</strong></div>
      <div><span>Já recebido</span><strong class="ok">${brl(t.recebido)}</strong></div>
      ${t.em_cheque ? `<div><span>Em cheque (a compensar)</span><strong class="info">${brl(t.em_cheque)}</strong></div>` : ""}
      <div><span>Falta receber</span><strong class="${t.falta > 0.01 ? "erro" : "ok"}">${brl(t.falta)}</strong></div>
    </div>

    ${f.recebimentos.length ? `<h4 class="fechamento-secao">${icone("pix", 15)} Recebimentos do período</h4>
      <ul class="lista-mini">${f.recebimentos.map((r) => `<li>
        <div class="info"><div class="titulo">${dataBR(r.data)} · ${esc(r.forma)} ${r.pagador ? `· ${esc(r.pagador)}` : ""}</div>
          <div class="sutil">${esc(r.aplicacoes || (r.notas ? `NF ${r.notas}` : "sem notas citadas"))}</div></div>
        <div class="valor">${brl(r.valor)}</div></li>`).join("")}</ul>` : ""}`;
}

// ------------------------------------------------------------------ cadastro de empresa

export function formularioEmpresa(empresa = null) {
  const e = empresa || {};
  const { el, fechar } = abrirModal({
    titulo: empresa ? `Editar ${e.nome}` : "Nova empresa",
    corpo: `<form class="grade-campos" data-form-empresa>
      <div class="campo col-2"><label for="e-nome">Nome usado no fechamento</label>
        <input id="e-nome" name="nome" class="input" value="${esc(e.nome || "")}" required maxlength="80" autofocus></div>
      <div class="campo"><label for="e-cnpj">CNPJ</label>
        <input id="e-cnpj" name="cnpj" class="input" value="${esc(e.cnpj || "")}" maxlength="20" placeholder="00.000.000/0000-00"></div>
      <div class="campo"><label for="e-dia">Dia do fechamento</label>
        <input id="e-dia" name="dia_fechamento" class="input" type="number" min="1" max="28"
          value="${e.dia_fechamento || tela.dados?.config?.dia_fechamento || 20}"></div>
      <div class="campo col-2"><label for="e-razao">Razão social</label>
        <input id="e-razao" name="razao_social" class="input" value="${esc(e.razao_social || "")}" maxlength="120"></div>
      <div class="campo col-2"><label for="e-apelidos">Outros nomes (para o robô reconhecer)</label>
        <input id="e-apelidos" name="apelidos" class="input" value="${esc(e.apelidos || "")}" maxlength="200"
          placeholder="Imapal Construções; Imapal Materiais"></div>
      <div class="campo"><label for="e-contato">Contato</label>
        <input id="e-contato" name="contato" class="input" value="${esc(e.contato || "")}" maxlength="80"></div>
      <div class="campo"><label for="e-telefone">Telefone</label>
        <input id="e-telefone" name="telefone" class="input" value="${esc(e.telefone || "")}" maxlength="20"></div>
      <div class="campo col-2"><label for="e-email">E-mail</label>
        <input id="e-email" name="email" class="input" type="email" value="${esc(e.email || "")}" maxlength="120"></div>
      <div class="campo"><label for="e-status">Situação</label>
        <select id="e-status" name="status" class="input">${opcoes(["Ativa", "Inativa"], e.status || "Ativa")}</select></div>
      <div class="campo col-2"><label for="e-obs">Observações</label>
        <textarea id="e-obs" name="observacoes" class="input" rows="2" maxlength="500">${esc(e.observacoes || "")}</textarea></div>
    </form>`,
    rodape: `${empresa ? `<button class="btn btn-perigo btn-fantasma" data-excluir>${icone("lixeira", 15)} Excluir</button>` : ""}
      <button class="btn btn-fantasma" data-fechar>Cancelar</button>
      <button class="btn btn-primario" data-salvar>${icone("check", 16)} Salvar</button>`,
  });

  const salvar = async (evento) => {
    evento?.preventDefault();
    const dados = Object.fromEntries(new FormData(el.querySelector("[data-form-empresa]")));
    dados.dia_fechamento = Number(dados.dia_fechamento) || null;
    const corpo = Object.fromEntries(Object.entries(dados).filter(([, v]) => v !== "" && v !== null));
    const resultado = await tentar(() => (empresa ? api.put(`/api/empresas/${e.id}`, corpo) : api.post("/api/empresas", corpo)),
                                   empresa ? "Empresa atualizada." : "Empresa cadastrada.");
    if (!resultado) return;
    fechar(true);
    await carregarDados();
    window.dispatchEvent(new Event("empresas:atualizar"));
  };
  el.querySelector("[data-form-empresa]").addEventListener("submit", salvar);
  el.querySelector("[data-salvar]").addEventListener("click", salvar);
  el.querySelector("[data-excluir]")?.addEventListener("click", async () => {
    if (!await confirmar({ titulo: "Excluir empresa", mensagem: `Excluir “${e.nome}”? Só dá para excluir empresas sem lançamentos.`,
                           textoConfirmar: "Excluir", perigo: true })) return;
    if (deuCerto(await tentar(() => api.del(`/api/empresas/${e.id}`), "Empresa excluída."))) {
      fechar(true);
      await carregarDados();
      window.dispatchEvent(new Event("empresas:atualizar"));
    }
  });
}

export async function enviarFechamentos() {
  if (!await confirmar({ titulo: "Enviar fechamentos agora",
                         mensagem: "O bot de notas vai mandar o fechamento de cada empresa para quem está cadastrado. Continuar?",
                         textoConfirmar: "Enviar" })) return;
  const resultado = await tentar(() => api.post("/api/empresas/fechamento/enviar", {}));
  if (!resultado) return;
  toast(resultado.enviados ? `Fechamento enviado para ${resultado.enviados} destinatário(s).`
    : `Nada enviado: ${resultado.motivo || "verifique o bot de notas"}.`, resultado.enviados ? "ok" : "aviso", { duracao: 6000 });
}

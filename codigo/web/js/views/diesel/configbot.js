// Diesel · configuração do bot do diesel: token, quem escolhe a máquina, relatórios automáticos e alerta de saldo.
import { api } from "../../api.js";
import { icone } from "../../icons.js";
import { dataHoraBR, esc, mensagemErro, toast } from "../../ui.js";

const RELATORIOS = [["semana", "Semanal", "toda segunda-feira, da semana que passou"],
  ["quinzena", "Quinzenal", "nos dias 1 e 16, da quinzena que fechou"],
  ["mes", "Mensal", "no dia 1, do mês que fechou"]];

export function htmlBotDiesel(cfg) {
  const pessoas = cfg.pessoas || [];
  const gestores = new Set(cfg.gestores || []);
  const relatorios = cfg.relatorios || {};
  return `<form class="config-grade" data-form-bot-diesel>
    <article class="card">
      <h3>${icone("telegram", 18)} Bot do diesel</h3>
      <p class="sutil">Um bot só para o diesel. Crie no <code>@BotFather</code> do Telegram (<code>/newbot</code>) e cole o
        token aqui. Mande para ele as <strong>fotos dos canhotos</strong> dos abastecimentos e os <strong>comprovantes</strong>
        da compra no posto.</p>
      <div class="grade-campos">
        <div class="campo col-2"><label for="bd-token">Token do bot</label>
          <input id="bd-token" name="token" class="input mono" value="${esc(cfg.token || "")}" maxlength="200"
            placeholder="123456789:AAE..." autocomplete="off"></div>
        <label class="opcao-app col-2"><span class="interruptor">
          <input type="checkbox" name="ativo" ${cfg.ativo ? "checked" : ""}><span></span></span>
          <span><strong>Receber pelo bot do diesel</strong><small>Canhotos, comprovantes e os relatórios automáticos.</small></span></label>
        <div class="campo"><label for="bd-alerta">Avisar quando o saldo ficar abaixo de (R$)</label>
          <input id="bd-alerta" name="alerta_valor" type="number" min="0" step="50" class="input"
            value="${esc(cfg.alerta_valor ?? 1000)}"></div>
        <div class="campo"><label for="bd-hora">Horário dos relatórios</label>
          <input id="bd-hora" name="hora_relatorio" type="time" class="input" value="${esc(cfg.hora_relatorio || "07:00")}"></div>
      </div>
      <div class="linha-botoes">
        <button class="btn btn-primario" type="submit">${icone("check", 16)} Salvar</button>
        <button class="btn" type="button" data-acao="verificar-bot-diesel">${icone("atualizar", 15)} Verificar agora</button>
      </div>
      ${cfg.ultimo_erro ? `<div class="alerta erro">${icone("alerta", 16)}<div>${esc(cfg.ultimo_erro)}</div></div>` : ""}
      ${cfg.ultima_verificacao ? `<p class="sutil">Última verificação: ${dataHoraBR(cfg.ultima_verificacao)}.</p>` : ""}
    </article>

    <article class="card">
      <h3>${icone("pessoa", 18)} Quem escolhe a máquina</h3>
      <p class="sutil">Cada canhoto que chegar vai para estas pessoas com a foto e as máquinas em botões — é quem faz a
        dedução do saldo. Elas também recebem os relatórios e o aviso de saldo baixo. Sem ninguém marcado, quem mandou o
        canhoto escolhe a máquina.</p>
      <ul class="lista-mini">
        ${pessoas.length ? pessoas.map((p) => `<li><label class="check">
            <input type="checkbox" name="gestores" value="${esc(p.chat_id)}" ${gestores.has(p.chat_id) ? "checked" : ""}>
            <span><strong>${esc(p.nome || p.chat_id)}</strong> <small class="sutil">chat ${esc(p.chat_id)}</small></span></label></li>`).join("")
          : `<li class="sutil">Ninguém ainda: cadastre as pessoas no bot dos boletos (Notificações) ou no bot de notas.</li>`}
      </ul>
      <p class="sutil">Quem pode mandar arquivos são as mesmas pessoas e grupos do bot dos boletos e do bot de notas.
        Cada uma só precisa abrir o bot do diesel e enviar <code>/start</code> uma vez.</p>
    </article>

    <article class="card">
      <h3>${icone("relatorio", 18)} Relatórios automáticos</h3>
      <p class="sutil">Chegam no Telegram de quem escolhe a máquina, com o consumo de cada máquina, o comprado, o abastecido
        e o saldo. Também dá para mandar na hora pela aba Relatórios.</p>
      ${RELATORIOS.map(([chave, rotulo, quando]) => `<label class="opcao-app"><span class="interruptor">
          <input type="checkbox" name="rel_${chave}" ${relatorios[chave] !== false ? "checked" : ""}><span></span></span>
          <span><strong>${rotulo}</strong><small>${quando}</small></span></label>`).join("")}
      <div class="campo" style="margin-top:10px"><label for="bd-nivel">Como os relatórios automáticos chegam</label>
        <select id="bd-nivel" name="nivel_relatorio" class="input">
          ${[["simples", "Simples — o essencial: valor, litros, saldo e cada máquina"],
             ["detalhado", "Detalhado — + comparação, consumo, combustíveis e pontos de atenção"],
             ["completo", "Completo — + cada abastecimento, postos e quem abasteceu"]].map(([v, r]) =>
            `<option value="${v}" ${(cfg.nivel_relatorio || "simples") === v ? "selected" : ""}>${r}</option>`).join("")}
        </select></div>
      <p class="sutil">Comandos do bot: <code>/saldo</code>, <code>/medias</code>, <code>/relatorio</code>
        (<code>/relatorio quinzena</code>, <code>/relatorio mes</code>, <code>/relatorio ano</code>), <code>/maquinas</code>.
        Para mais detalhes, acrescente <code>detalhado</code> ou <code>completo</code>: <code>/relatorio mes completo</code>.</p>
    </article>
  </form>`;
}

export async function salvarBotDiesel(formulario) {
  const dados = new FormData(formulario);
  const corpo = {
    token: dados.get("token") || "",
    ativo: dados.get("ativo") === "on",
    gestores: dados.getAll("gestores"),
    alerta_valor: Number(dados.get("alerta_valor") || 0),
    hora_relatorio: dados.get("hora_relatorio") || "07:00",
    nivel_relatorio: dados.get("nivel_relatorio") || "simples",
    relatorios: { semana: dados.get("rel_semana") === "on", quinzena: dados.get("rel_quinzena") === "on", mes: dados.get("rel_mes") === "on" },
  };
  try {
    await api.post("/api/diesel/bot/config", corpo);
    toast("Bot do diesel salvo.", "ok");
    window.dispatchEvent(new Event("diesel:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

export async function verificarBotDiesel() {
  try {
    const r = await api.post("/api/diesel/bot/verificar", {});
    toast(r.recebidos ? `${r.recebidos} arquivo(s) recebido(s).` : "Nada novo no bot do diesel.", "ok");
    window.dispatchEvent(new Event("diesel:atualizar"));
  } catch (erro) {
    toast(mensagemErro(erro), "erro", { duracao: 6000 });
  }
}

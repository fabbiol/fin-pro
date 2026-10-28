// Cliente da API do servidor.

export class ApiError extends Error {
  constructor(status, detalhe) {
    let mensagem = "Erro inesperado.";
    if (typeof detalhe === "string" && detalhe.trim()) mensagem = detalhe;
    else if (detalhe?.mensagem) mensagem = detalhe.mensagem;
    else if (Array.isArray(detalhe)) mensagem = detalhe.map((d) => d.msg).join("; ");
    super(mensagem);
    this.status = status;
    this.detalhe = detalhe;
    this.codigo = detalhe?.codigo;
  }
}

// Página HTML no lugar da resposta (ex.: o EasyPanel avisando que o serviço não responde, durante uma implantação):
// mostra uma mensagem clara em vez do código da página.
const SEM_RESPOSTA = "O Fin Pro não respondeu agora (ele pode estar reiniciando, por exemplo logo depois de Implantar). "
  + "Espere um minuto e atualize a página.";
const detalheDoErro = (dados) => (typeof dados === "string" && /^\s*</.test(dados) ? SEM_RESPOSTA : dados?.detail ?? dados);

function montarUrl(caminho, params) {
  const url = new URL(caminho, location.origin);
  Object.entries(params || {}).forEach(([chave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== "") url.searchParams.set(chave, valor);
  });
  return url;
}

async function requisitar(metodo, caminho, { corpo, params } = {}) {
  let resposta;
  try {
    resposta = await fetch(montarUrl(caminho, params), {
      method: metodo,
      headers: corpo !== undefined ? { "Content-Type": "application/json" } : {},
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new ApiError(0, "Sem conexão com o servidor. Verifique se o Fin Pro está aberto.");
  }
  if (resposta.status === 204) return null;
  const tipo = resposta.headers.get("content-type") || "";
  const dados = tipo.includes("json") ? await resposta.json() : await resposta.text();
  if (!resposta.ok) {
    const erro = new ApiError(resposta.status, detalheDoErro(dados));
    avisarAcesso(erro);
    throw erro;
  }
  return dados;
}

function avisarAcesso(erro) {
  if (erro.status === 401 && ["nao_autorizado", "login_necessario"].includes(erro.codigo)) window.dispatchEvent(new Event("acesso:necessario"));
}

function enviarComProgresso(url, arquivo, aoProgresso) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (e) => e.lengthComputable && aoProgresso?.(e.loaded / e.total, false);
    xhr.upload.onload = () => aoProgresso?.(1, true);
    xhr.onload = () => {
      let dados;
      try { dados = JSON.parse(xhr.responseText); } catch { dados = xhr.responseText; }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(dados);
      } else {
        const erro = new ApiError(xhr.status, detalheDoErro(dados));
        avisarAcesso(erro);
        reject(erro);
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "Falha de conexão ao enviar o arquivo."));
    const formulario = new FormData();
    formulario.append("arquivo", arquivo, arquivo.name || "imagem-colada.png");
    xhr.send(formulario);
  });
}

export const api = {
  get: (caminho, params) => requisitar("GET", caminho, { params }),
  post: (caminho, corpo = {}) => requisitar("POST", caminho, { corpo }),
  put: (caminho, corpo) => requisitar("PUT", caminho, { corpo }),
  patch: (caminho, corpo) => requisitar("PATCH", caminho, { corpo }),
  del: (caminho) => requisitar("DELETE", caminho),

  /** Envia um arquivo e espera a leitura terminar (informa o progresso do upload, 0 a 1). */
  enviarArquivo(arquivo, aoProgresso) {
    return enviarComProgresso("/api/leituras", arquivo, aoProgresso);
  },

  /** Envia um arquivo para leitura em segundo plano; devolve a tarefa para acompanhar o progresso. */
  criarLeitura(arquivo, aoProgresso) {
    return enviarComProgresso("/api/leituras/tarefas", arquivo, aoProgresso);
  },

  /** Envia um arquivo para qualquer endpoint que recebe o campo "arquivo". */
  enviarPara(url, arquivo, aoProgresso) {
    return enviarComProgresso(url, arquivo, aoProgresso);
  },

  urlExportar(params) {
    return montarUrl("/api/exportar", params).toString();
  },
};

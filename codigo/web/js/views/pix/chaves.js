// Pagamentos Pix · validação e formatação das chaves Pix.
import { abrirDetalhes } from "../../detalhes.js";
import { api } from "../../api.js";
import { NOVO_CENTRO, carregarCentros, opcoesCentro, opcoesFiltroCentro, tratarNovoCentro } from "../../centros.js";
import { icone } from "../../icons.js";
import {
  abrirModal, brl, confirmar, copiar, dataBR, dataHoraBR, debounce, esc, hojeISO, mensagemErro, numeroBR, parseValor,
  seloSituacao, toast, uid,
} from "../../ui.js";

// Tela: Pagamentos Pix — lançar (tipo e chave, valor, Copia e Cola ou QR code), consultar, marcar como pago e exportar.
export const TIPOS_CHAVE = {
  cpf_cnpj: { rotulo: "CNPJ/CPF", icone: "cartao", placeholder: "00.000.000/0000-00 ou 000.000.000-00", teclado: "numeric" },
  celular: { rotulo: "Celular", icone: "celular", placeholder: "(65) 99999-9999", teclado: "tel" },
  email: { rotulo: "E-mail", icone: "email", placeholder: "financeiro@empresa.com.br", teclado: "email" },
  aleatoria: { rotulo: "Aleatória", icone: "chave", placeholder: "123e4567-e89b-12d3-a456-426614174000", teclado: "text" },
};

export const RE_EMAIL = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

export const RE_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const digitos = (texto) => String(texto || "").replace(/\D/g, "");

export function cpfValido(d) {
  if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
  for (const posicao of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < posicao; i++) soma += Number(d[i]) * (posicao + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[posicao])) return false;
  }
  return true;
}

export function cnpjValido(d) {
  if (d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
  const digito = (base) => {
    const pesos = base.length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const resto = [...base].reduce((soma, c, i) => soma + Number(c) * pesos[i], 0) % 11;
    return resto < 2 ? 0 : 11 - resto;
  };
  const primeiro = digito(d.slice(0, 12));
  return d.endsWith(`${primeiro}${digito(d.slice(0, 12) + primeiro)}`);
}

export function aplicarMolde(numeros, molde) {
  let saida = "";
  let i = 0;
  for (const c of molde) {
    if (i >= numeros.length) break;
    saida += c === "#" ? numeros[i++] : c;
  }
  return saida;
}

export function numerosCelular(texto) {
  let d = digitos(texto);
  if (d.length > 11 && d.startsWith("55")) d = d.slice(2);
  return d.slice(0, 11);
}

export function mascarar(tipo, valor) {
  if (tipo === "cpf_cnpj") {
    const d = digitos(valor).slice(0, 14);
    return aplicarMolde(d, d.length <= 11 ? "###.###.###-##" : "##.###.###/####-##");
  }
  if (tipo === "celular") return aplicarMolde(numerosCelular(valor), "(##) #####-####");
  return valor;
}

export function formatarChave(tipo, chave) {
  if (!chave) return "";
  if (tipo === "cpf_cnpj" || tipo === "celular") return mascarar(tipo, chave);
  return chave;
}

export function validarChave(tipo, chave) {
  const texto = String(chave || "").trim();
  if (tipo === "cpf_cnpj") {
    const d = digitos(texto);
    if (d.length === 11) return cpfValido(d) ? { estado: "ok", texto: "CPF válido" } : { estado: "erro", texto: "CPF inválido" };
    if (d.length === 14) return cnpjValido(d) ? { estado: "ok", texto: "CNPJ válido" } : { estado: "erro", texto: "CNPJ inválido" };
    return { estado: d.length > 14 ? "erro" : "neutro", texto: "Digite 11 números (CPF) ou 14 (CNPJ)" };
  }
  if (tipo === "celular") {
    const d = numerosCelular(texto);
    if (d.length === 11 && d[0] !== "0" && d[2] === "9") return { estado: "ok", texto: "Celular válido" };
    return { estado: d.length === 11 ? "erro" : "neutro", texto: "Celular com DDD: (65) 99999-9999" };
  }
  if (tipo === "email") {
    return RE_EMAIL.test(texto) && texto.length <= 77 ? { estado: "ok", texto: "E-mail válido" } : { estado: texto.includes("@") ? "neutro" : "erro", texto: "E-mail incompleto" };
  }
  if (tipo === "aleatoria") {
    return RE_UUID.test(texto) ? { estado: "ok", texto: "Chave válida" } : { estado: texto.length >= 36 ? "erro" : "neutro", texto: "Formato 123e4567-e89b-…" };
  }
  return { estado: "erro", texto: "Escolha o tipo da chave" };
}

export function inferirTipo(texto) {
  const t = String(texto || "").trim();
  if (!t) return null;
  if (t.includes("@")) return "email";
  if (RE_UUID.test(t)) return "aleatoria";
  const d = digitos(t);
  if (t.startsWith("+55") || (d.length === 13 && d.startsWith("55"))) return "celular";
  if (d.length === 14) return "cpf_cnpj";
  if (d.length === 11) return cpfValido(d) ? "cpf_cnpj" : "celular";
  return null;
}

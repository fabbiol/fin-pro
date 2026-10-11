// Estado compartilhado entre as telas.
export const estado = {
  status: null,
  acesso: null, // { protegido, autorizado, local, rede_sem_senha, usuario: { perfil, permissoes } }
};

/** A pessoa que entrou pode usar esta função? Sem login por pessoa (computador principal), pode tudo. */
export function pode(permissao) {
  const usuario = estado.acesso?.usuario;
  if (!usuario) return true;
  return (usuario.permissoes || []).includes(permissao);
}

export function ehAdministrador() {
  return estado.acesso?.usuario?.perfil === "administrador";
}

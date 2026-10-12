#!/usr/bin/env bash
# Recupera a tela de Configuracoes do Fin Pro (web/js/views/configuracoes), que ficou fora do GitHub.
# Procura uma copia no servidor (pastas e cache do Docker), guarda em /opt/finpro/configuracoes-recuperadas
# e copia para o Fin Pro que esta no ar. Nao mexe nos dados. Pode rodar mais de uma vez.
recuperar_configuracoes() {
  DESTINO=/opt/finpro/configuracoes-recuperadas
  ESPERADO='6adcf9ecca55d0c26ebe638b6cad7a8add40259dc490c3089fcf47389010ff2a  aplicativo.js
5695abb02fdd3ae25c09b7f4c1ae9dc38ce57dbc1358a756061dbe3d5a9a8030  backup.js
c995351d4dde29a2d6ff34529c523a0f3aca2c6e1639475791294e69a80248ce  entrada.js
5ce98cb962cfc2d5daa54fcdbfe5fb307f30cfe47cd66b1324852d5616f6d9dc  eventos.js
93520ad08e7fd2a01c9c26472e1ab55c78d168426523ad147384897efbe043c1  importacao.js
4e4723105e3379eff8ffa66952ef536fea49eac1dc5d804fd3e30c7d426a8fca  index.js
2ef62114a0b034bf4b800b8ea106f0e82bfb53e6de1b27ac9abfab4ddc3f9a9a  rede.js
3ef4e9f3b4cd8bb2d283544589e65fbe44269670ec958201189baedea5f6b16a  saude.js
37cd34722b4a280cab95a6b01ac96458849543888557c4e09df520596af4f5bc  tela.js
871495800d7f8ced0ca9bd73879571e86100ef23c6bd4942fce317af9b142c0d  usuarios.js
3b86e73e655146ed8e37e5a7a81a427f8d70ab53bfb99bf38915fe4a71300e2d  versao.js'
  echo ">> Procurando a tela de Configuracoes do Fin Pro no servidor (1 ou 2 minutos)..."
  MELHOR=""; MELHOR_PONTOS=-1; MELHOR_DATA=0
  while IFS= read -r INDICE; do
    PASTA=$(dirname "$INDICE")
    PRESENTES=$(cd "$PASTA" && ls -1 | grep -cxF -f <(echo "$ESPERADO" | awk '{print $2}'))
    IGUAIS=$(cd "$PASTA" && echo "$ESPERADO" | sha256sum -c 2>/dev/null | grep -c ': OK$')
    PONTOS=$((IGUAIS * 100 + PRESENTES)); DATA=$(stat -c %Y "$INDICE")
    echo "   achei: $PASTA ($PRESENTES de 11 arquivos, $IGUAIS iguais ao backup)"
    if [ "$PONTOS" -gt "$MELHOR_PONTOS" ] || { [ "$PONTOS" -eq "$MELHOR_PONTOS" ] && [ "$DATA" -gt "$MELHOR_DATA" ]; }; then
      MELHOR=$PASTA; MELHOR_PONTOS=$PONTOS; MELHOR_DATA=$DATA
    fi
  done < <(find / \( -path /proc -o -path /sys -o -path /dev -o -path "$DESTINO" \) -prune -o -path '*/web/js/views/configuracoes/index.js' -print 2>/dev/null)
  if [ -z "$MELHOR" ]; then echo ">> NAO ACHEI a pasta no servidor. Mande um print desta tela para o Claude."; return; fi
  rm -rf "$DESTINO"; mkdir -p "$DESTINO"; cp -a "$MELHOR"/. "$DESTINO"
  echo ">> Usei: $MELHOR  (copia guardada em $DESTINO)"
  CONTAINER=$(docker ps -q --filter label=com.docker.compose.project=prospera_fin | head -n 1)
  if [ -z "$CONTAINER" ]; then echo ">> NAO ACHEI o Fin Pro rodando. Mande um print desta tela para o Claude."; return; fi
  docker cp "$DESTINO"/. "$CONTAINER":/app/web/js/views/configuracoes && echo ">> PRONTO! A tela voltou para o Fin Pro que esta no ar. Abra o site e aperte Ctrl+F5."
}
recuperar_configuracoes

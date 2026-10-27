# Fin Pro: envia o certificado e a chave da API Pix do Bradesco para a VPS e prepara as variáveis do EasyPanel.
#
# Como usar (no Windows):
#   1. Ponha numa mesma pasta este arquivo, o certificado, a chave e o .env.production (do Drive, pasta Bradesco_api).
#   2. Clique com o botão direito neste arquivo e escolha "Executar com o PowerShell".
#   3. Digite o IP da VPS e, quando pedir, a senha do root (ela é pedida pelo próprio ssh, nesta janela).
#
# O que ele faz: confere os arquivos, copia o certificado e a chave para /opt/finpro/certs na VPS (o Fin Pro enxerga
# essa pasta como /certs, somente leitura), deixa só o root ler, confere a validade e se o certificado e a chave são um
# par, e coloca na área de transferência as linhas para colar no Ambiente do EasyPanel. Nada é mostrado na tela nem
# gravado em arquivo: nem a senha, nem a chave, nem o Client Secret.

$ErrorActionPreference = 'Stop'
$PastaVps = '/opt/finpro/certs'
$aqui = $PSScriptRoot

function Parar($mensagem) {
    Write-Host ''
    Write-Host $mensagem -ForegroundColor Red
    Read-Host 'Aperte Enter para fechar'
    exit 1
}

function Ler-Env($arquivo) {
    # Como o projeto em PHP lê: NOME=valor, sem aspas; linhas começando com # são comentário
    $valores = @{}
    foreach ($linha in Get-Content -LiteralPath $arquivo) {
        $texto = $linha.Trim()
        if (-not $texto -or $texto.StartsWith('#') -or -not $texto.Contains('=')) { continue }
        $i = $texto.IndexOf('=')
        $valores[$texto.Substring(0, $i).Trim()] = $texto.Substring($i + 1).Trim()
    }
    return $valores
}

function Nome-Arquivo($valor, $padrao) {
    # No .env.production o caminho é do projeto em PHP (ex.: certs/producao.crt): aqui vale só o nome do arquivo
    if (-not $valor) { return $padrao }
    return [IO.Path]::GetFileName($valor.Replace('/', '\'))
}

function Tem-Texto($nome, $texto) {
    return [bool](Select-String -LiteralPath (Join-Path $aqui $nome) -SimpleMatch $texto -Quiet)
}

Write-Host 'Fin Pro - certificado da API Pix do Bradesco na VPS' -ForegroundColor Cyan
Write-Host ''

# 1) ssh e scp, que já vêm no Windows 10 e 11
if (-not (Get-Command ssh -ErrorAction SilentlyContinue) -or -not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Parar ('Este Windows não tem o Cliente OpenSSH. Instale em Configurações > Aplicativos > Recursos opcionais > ' +
           'Adicionar um recurso > Cliente OpenSSH e rode de novo.')
}

# 2) .env.production (o navegador às vezes baixa sem o ponto do começo)
$arquivoEnv = Get-ChildItem -LiteralPath $aqui -File | Where-Object { $_.Name -like '*env.production*' } | Select-Object -First 1
if (-not $arquivoEnv) { Parar "Não achei o .env.production nesta pasta ($aqui). Baixe do Drive (pasta Bradesco_api) para cá." }
$valores = Ler-Env $arquivoEnv.FullName
foreach ($nome in 'BRADESCO_CLIENT_ID', 'BRADESCO_CLIENT_SECRET') {
    if (-not $valores[$nome]) { Parar "O $($arquivoEnv.Name) não tem a linha $nome." }
}

# 3) certificado e chave: os que o .env.production indica (no projeto em PHP, o padrão é producao.crt e client.key.pem)
$cert = Nome-Arquivo $valores['BRADESCO_CERT'] 'producao.crt'
$chave = Nome-Arquivo $valores['BRADESCO_KEY'] 'client.key.pem'
foreach ($nome in $cert, $chave) {
    if ($nome -notmatch '^[A-Za-z0-9._-]+$') { Parar "Nome de arquivo inesperado no .env.production: $nome" }
    if (-not (Test-Path -LiteralPath (Join-Path $aqui $nome) -PathType Leaf)) {
        Parar "Não achei o $nome nesta pasta ($aqui). Baixe do Drive (pasta Bradesco_api\certs) para cá."
    }
}
if (-not (Tem-Texto $cert '-----BEGIN CERTIFICATE-----')) {
    Parar "O $cert não está no formato PEM (um texto com -----BEGIN CERTIFICATE-----)."
}
if (-not (Tem-Texto $chave 'PRIVATE KEY-----')) { Parar "O $chave não parece uma chave no formato PEM." }
if ((Tem-Texto $chave 'ENCRYPTED')) { Parar "O $chave tem senha. O Fin Pro precisa da chave sem senha, como no projeto em PHP." }
Write-Host "Arquivos conferidos: certificado $cert e chave $chave." -ForegroundColor Green

# 4) endereço da VPS
Write-Host ''
Write-Host 'O IP da VPS aparece no hPanel da Hostinger, na página da sua VPS.'
$destino = (Read-Host 'IP da VPS').Trim()
if (-not $destino) { Parar 'Sem o IP não dá para continuar.' }
if (-not $destino.Contains('@')) { $destino = "root@$destino" }
if ($destino -notmatch '^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$') { Parar "Endereço inválido: $destino" }
# Primeira conexão: guarda a identidade da VPS sozinho; se um dia ela mudar, o ssh recusa (proteção contra impostor)
$opcoes = @('-o', 'StrictHostKeyChecking=accept-new')

# 5) envio (1ª senha). Vai uma pasta "certs" só com os dois arquivos: o scp cria /opt/finpro/certs se ainda não existir.
$temporaria = Join-Path ([IO.Path]::GetTempPath()) ('finpro-' + [guid]::NewGuid().ToString('N'))
$pastaCerts = Join-Path $temporaria 'certs'
try {
    New-Item -ItemType Directory -Path $pastaCerts | Out-Null
    Copy-Item -LiteralPath (Join-Path $aqui $cert), (Join-Path $aqui $chave) -Destination $pastaCerts
    Write-Host ''
    Write-Host '1 de 2: enviando o certificado e a chave para a VPS.' -ForegroundColor Cyan
    Write-Host '        Digite a senha do root e aperte Enter (a senha não aparece enquanto você digita).'
    & scp @opcoes -r $pastaCerts "${destino}:/opt/finpro/"
    $enviou = $LASTEXITCODE -eq 0
} catch {
    Parar "Não deu para preparar o envio: $($_.Exception.Message)"
} finally {
    Remove-Item -LiteralPath $temporaria -Recurse -Force -ErrorAction SilentlyContinue
}
if (-not $enviou) { Parar 'O envio não deu certo (senha, IP ou conexão). Confira e rode de novo.' }

# 6) proteção e conferência na VPS (2ª senha). Os comandos vão em base64, para o Windows não mexer nas aspas.
$remoto = @'
cd {PASTA} || { echo ERRO=PASTA; exit 0; }
chmod 700 {PASTA}
chmod 600 -- '{CERT}' '{CHAVE}'
stat -c 'ARQ=%n|%s|%a|%U' -- '{CERT}' '{CHAVE}'
command -v openssl >/dev/null 2>&1 || { echo OPENSSL=FALTA; exit 0; }
echo "VENCE=$(openssl x509 -noout -enddate -in '{CERT}' 2>/dev/null | cut -d= -f2)"
if openssl pkey -noout -in '{CHAVE}' -passin pass: >/dev/null 2>&1; then echo CHAVE=OK; else echo CHAVE=ERRO; exit 0; fi
PUB_CERT=$(openssl x509 -noout -pubkey -in '{CERT}' 2>/dev/null)
PUB_CHAVE=$(openssl pkey -pubout -in '{CHAVE}' -passin pass: 2>/dev/null)
if [ -n "$PUB_CERT" ] && [ "$PUB_CERT" = "$PUB_CHAVE" ]; then echo PAR=OK; else echo PAR=ERRO; fi
'@
$remoto = $remoto.Replace('{PASTA}', $PastaVps).Replace('{CERT}', $cert).Replace('{CHAVE}', $chave) -replace "`r", ''
$codigo = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoto))
Write-Host ''
Write-Host '2 de 2: protegendo e conferindo na VPS. Digite a senha do root de novo.' -ForegroundColor Cyan
$saida = @(& ssh @opcoes $destino "echo $codigo | base64 -d | bash")
if ($LASTEXITCODE -ne 0) { Parar 'Não deu para conferir na VPS (senha ou conexão). Os arquivos já foram enviados; rode de novo.' }

function Valor($marcador) {
    $linha = $saida | Where-Object { $_ -like "$marcador=*" } | Select-Object -First 1
    if ($linha) { return $linha.Substring($marcador.Length + 1) }
    return $null
}
if (Valor 'ERRO') { Parar "A pasta $PastaVps não existe na VPS: o envio não chegou lá. Rode de novo." }
Write-Host ''
Write-Host 'Na VPS:' -ForegroundColor Green
# A VPS responde só em texto sem acento: o Windows decodifica a saída do ssh pela página de código do console
$saida | Where-Object { $_ -like 'ARQ=*' } | ForEach-Object {
    $partes = $_.Substring(4).Split('|')
    Write-Host ("  {0}: {1} bytes, permissão {2} (só o {3} lê)" -f $partes[0], $partes[1], $partes[2], $partes[3])
}
if (Valor 'OPENSSL') {
    Write-Host '  A VPS não tem o openssl: pulei a conferência da validade e do par.' -ForegroundColor Yellow
} else {
    if ((Valor 'CHAVE') -ne 'OK') { Parar 'A VPS não conseguiu ler a chave sem senha. Confira se baixou o arquivo certo.' }
    if ((Valor 'PAR') -ne 'OK') { Parar 'O certificado e a chave NÃO são um par. Confira se baixou os arquivos certos do Drive.' }
    Write-Host '  O certificado e a chave são um par.'
    $vence = Valor 'VENCE'
    try {
        $data = [datetime]::ParseExact((($vence -replace '\s+', ' ') -replace ' GMT$', '').Trim(), 'MMM d HH:mm:ss yyyy',
                                       [Globalization.CultureInfo]::InvariantCulture)
        $dias = [int](($data - (Get-Date).ToUniversalTime()).TotalDays)
        $cor = if ($dias -lt 30) { 'Yellow' } else { 'Gray' }
        Write-Host ("  O certificado vence em {0:dd/MM/yyyy} (faltam {1} dias)." -f $data, $dias) -ForegroundColor $cor
    } catch {
        Write-Host "  Validade do certificado: $vence"
    }
}

# 7) variáveis do EasyPanel: vão direto para a área de transferência, sem aparecer na tela
$linhas = @('BRADESCO_AMBIENTE=producao',
            "BRADESCO_CLIENT_ID=$($valores['BRADESCO_CLIENT_ID'])",
            "BRADESCO_CLIENT_SECRET=$($valores['BRADESCO_CLIENT_SECRET'])",
            "BRADESCO_CERT=/certs/$cert",
            "BRADESCO_KEY=/certs/$chave")
foreach ($opcional in 'BRADESCO_HOST', 'BRADESCO_TOKEN_PATH') {
    if ($valores[$opcional]) { $linhas += "$opcional=$($valores[$opcional])" }
}
Set-Clipboard -Value ($linhas -join "`r`n")
Write-Host ''
Write-Host 'As variáveis do EasyPanel estão copiadas (Ctrl+V).' -ForegroundColor Cyan
Write-Host '  No EasyPanel: serviço do Fin Pro > Ambiente > cole no fim da lista > Salvar.'
Write-Host '  São as linhas BRADESCO_AMBIENTE, BRADESCO_CLIENT_ID, BRADESCO_CLIENT_SECRET, BRADESCO_CERT e BRADESCO_KEY.'
Read-Host 'Depois de colar e salvar, aperte Enter aqui (eu limpo a área de transferência)'
Set-Clipboard -Value ' '

# 8) as cópias deste computador não precisam ficar aqui
Write-Host ''
$apagar = Read-Host "Apagar desta pasta o $cert, o $chave e o $($arquivoEnv.Name)? Eles continuam no Drive. (S/N)"
if ($apagar -match '^[sS]') {
    Remove-Item -LiteralPath (Join-Path $aqui $cert), (Join-Path $aqui $chave), $arquivoEnv.FullName -Force
    Write-Host 'Apagados deste computador.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Pronto! Falta só publicar: no EasyPanel, clique em Implantar (com o pull request já aprovado).' -ForegroundColor Green
Write-Host 'Depois abra o Fin Pro > Transferências de clientes: o cartão "Pix recebidos no Bradesco" deve mostrar "Produção".'
Read-Host 'Aperte Enter para fechar'

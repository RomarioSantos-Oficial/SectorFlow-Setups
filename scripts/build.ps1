<# 
    Sector Flow Setups - Compilador para .exe
    ==========================================
    
    Este script compila o aplicativo em um executável .exe
    usando PyInstaller. O resultado é um instalador portátil.
    
    Uso: 
        powershell -ExecutionPolicy Bypass -File build.ps1
    
    Opções:
        build.ps1 -OneFile      # Cria um único .exe (mais lento para iniciar)
        build.ps1 -Folder       # Cria pasta com arquivos (mais rápido)
        build.ps1 -Installer    # Cria instalador com Inno Setup (se disponível)
#>

param(
    [switch]$OneFile,
    [switch]$Folder,
    [switch]$Installer,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Sector Flow Setups - Build"

# Cores
function Write-Title { param($text) Write-Host "`n$text" -ForegroundColor Cyan }
function Write-Success { param($text) Write-Host "[OK] $text" -ForegroundColor Green }
function Write-Info { param($text) Write-Host "[INFO] $text" -ForegroundColor Yellow }
function Write-Err { param($text) Write-Host "[ERRO] $text" -ForegroundColor Red }

# Banner
Write-Host @"

  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║           🔧 SECTOR FLOW SETUPS - BUILD 🔧                ║
  ║                                                           ║
  ║              Compilador para Executável                   ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Navegar para pasta raiz do projeto (scripts está dentro da raiz)
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$AppName = "SectorFlowSetups"
$AppVersion = "1.0.0"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"

# ═══════════════════════════════════════════════════════════════
# Limpar builds anteriores
# ═══════════════════════════════════════════════════════════════
if ($Clean) {
    Write-Title "Limpando builds anteriores..."
    if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
    if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
    if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }
    Write-Success "Limpeza concluída!"
    exit 0
}

# ═══════════════════════════════════════════════════════════════
# 1. Verificar ambiente
# ═══════════════════════════════════════════════════════════════
Write-Title "1. Verificando ambiente..."

$venvPath = Join-Path $ProjectRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Err "Ambiente virtual não encontrado!"
    Write-Info "Execute primeiro: start.ps1 (na pasta raiz)"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Success "Ambiente virtual encontrado."

# ═══════════════════════════════════════════════════════════════
# 2. Instalar PyInstaller
# ═══════════════════════════════════════════════════════════════
Write-Title "2. Verificando PyInstaller..."

$pyinstallerInstalled = & $venvPip show pyinstaller 2>$null
if (-not $pyinstallerInstalled) {
    Write-Info "Instalando PyInstaller..."
    & $venvPip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Falha ao instalar PyInstaller!"
        exit 1
    }
}
Write-Success "PyInstaller disponível."

# ═══════════════════════════════════════════════════════════════
# 3. Determinar modo de build
# ═══════════════════════════════════════════════════════════════
$BuildMode = "onefile"  # Padrão: um único .exe

if ($Folder) {
    $BuildMode = "folder"
    Write-Info "Modo: Pasta com arquivos (inicialização mais rápida)"
} elseif ($OneFile) {
    $BuildMode = "onefile"
    Write-Info "Modo: Arquivo único .exe (portátil)"
} else {
    # Perguntar ao usuário
    Write-Host @"

Escolha o modo de compilação:

  [1] Arquivo único .exe (recomendado para distribuição)
      - Um único arquivo executável
      - Mais lento para iniciar (~5-10 segundos)
      - Fácil de compartilhar
      
  [2] Pasta com arquivos (recomendado para uso local)
      - Pasta com vários arquivos
      - Inicia mais rápido (~1-2 segundos)
      - Precisa manter a pasta inteira

"@ -ForegroundColor Yellow
    
    $choice = Read-Host "Escolha (1 ou 2)"
    if ($choice -eq "2") {
        $BuildMode = "folder"
    }
}

# ═══════════════════════════════════════════════════════════════
# 4. Compilar com PyInstaller
# ═══════════════════════════════════════════════════════════════
Write-Title "4. Compilando aplicativo..."
Write-Host "   Isso pode demorar alguns minutos..." -ForegroundColor Gray

# Coletar dados adicionais
$addData = @(
    "assets;assets",
    "data/schema.sql;data",
    "gui;gui",
    "core;core",
    "adapter;adapter",
    "pyRfactor2SharedMemory;pyRfactor2SharedMemory"
)

$hiddenImports = @(
    "customtkinter",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "numpy",
    "torch",
    "matplotlib",
    "matplotlib.backends.backend_tkagg",
    "pystray",
    "psutil",
    "sqlite3",
    "ctypes",
    "json",
    "threading"
)

# Construir comando PyInstaller
$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--name=$AppName",
    "--icon=assets/logo.ico",
    "--windowed",
    "--noconfirm",
    "--clean"
)

# Modo de build
if ($BuildMode -eq "onefile") {
    $pyinstallerArgs += "--onefile"
} else {
    $pyinstallerArgs += "--onedir"
}

# Adicionar dados
foreach ($data in $addData) {
    $pyinstallerArgs += "--add-data=$data"
}

# Hidden imports
foreach ($imp in $hiddenImports) {
    $pyinstallerArgs += "--hidden-import=$imp"
}

# Arquivo principal
$pyinstallerArgs += "main.py"

Write-Info "Executando PyInstaller..."
& $venvPython $pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Err "Falha na compilação!"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Success "Compilação concluída!"

# ═══════════════════════════════════════════════════════════════
# 5. Resultado
# ═══════════════════════════════════════════════════════════════
Write-Title "5. Build finalizado!"

if ($BuildMode -eq "onefile") {
    $exePath = Join-Path $DistDir "$AppName.exe"
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    
    Write-Host @"

  ════════════════════════════════════════════════════════════
   ✅ EXECUTÁVEL CRIADO COM SUCESSO!
   
   📁 Localização: $exePath
   📊 Tamanho: $exeSize MB
   
   Para distribuir:
   - Copie o arquivo $AppName.exe
   - Envie para outros usuários
   - Basta executar, sem instalação!
  ════════════════════════════════════════════════════════════

"@ -ForegroundColor Green
} else {
    $folderPath = Join-Path $DistDir $AppName
    
    Write-Host @"

  ════════════════════════════════════════════════════════════
   ✅ PASTA DE DISTRIBUIÇÃO CRIADA!
   
   📁 Localização: $folderPath
   
   Para distribuir:
   - Compacte a pasta '$AppName' em um .zip
   - O executável é: $AppName.exe (dentro da pasta)
  ════════════════════════════════════════════════════════════

"@ -ForegroundColor Green
}

# Abrir pasta dist
$openDist = Read-Host "Abrir pasta de saída? (S/n)"
if ($openDist -ne "n" -and $openDist -ne "N") {
    Start-Process explorer.exe $DistDir
}

Write-Host "`nBuild concluído!" -ForegroundColor Cyan
Read-Host "Pressione Enter para fechar"

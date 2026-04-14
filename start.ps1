<# 
    Sector Flow Setups - Script de Instalação e Execução
    =====================================================
    
    Este script:
    1. Verifica se o Python está instalado
    2. Cria um ambiente virtual (se não existir)
    3. Instala todas as dependências
    4. Executa o aplicativo
    
    Uso: 
        Clique com botão direito > "Executar com PowerShell"
        ou execute: powershell -ExecutionPolicy Bypass -File start.ps1
#>

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Sector Flow Setups - Instalador"

# Cores para output
function Write-Title { param($text) Write-Host "`n$text" -ForegroundColor Cyan }
function Write-Success { param($text) Write-Host "[OK] $text" -ForegroundColor Green }
function Write-Info { param($text) Write-Host "[INFO] $text" -ForegroundColor Yellow }
function Write-Err { param($text) Write-Host "[ERRO] $text" -ForegroundColor Red }

# Banner
Write-Host @"

  ╔═══════════════════════════════════════════════════════════╗
  ║                                                           ║
  ║           🏎️  SECTOR FLOW SETUPS  🏎️                      ║
  ║                                                           ║
  ║        Instalador e Inicializador Automático              ║
  ║                                                           ║
  ╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ═══════════════════════════════════════════════════════════════
# 1. Verificar Python
# ═══════════════════════════════════════════════════════════════
Write-Title "1. Verificando Python..."

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 10) {
                $pythonCmd = $cmd
                Write-Success "Python encontrado: $version"
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Err "Python 3.10+ não encontrado!"
    Write-Host @"

Para instalar o Python:
  1. Acesse: https://www.python.org/downloads/
  2. Baixe Python 3.10 ou superior
  3. Durante a instalação, MARQUE: "Add Python to PATH"
  4. Execute este script novamente

"@ -ForegroundColor Yellow
    Read-Host "Pressione Enter para sair"
    exit 1
}

# ═══════════════════════════════════════════════════════════════
# 2. Criar/Ativar Ambiente Virtual
# ═══════════════════════════════════════════════════════════════
Write-Title "2. Configurando ambiente virtual..."

$venvPath = Join-Path $ScriptDir ".venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

if (-not (Test-Path $venvPath)) {
    Write-Info "Criando ambiente virtual (.venv)..."
    & $pythonCmd -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Falha ao criar ambiente virtual!"
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    Write-Success "Ambiente virtual criado!"
} else {
    Write-Success "Ambiente virtual já existe."
}

# Ativar ambiente virtual
Write-Info "Ativando ambiente virtual..."
& $venvActivate

# ═══════════════════════════════════════════════════════════════
# 3. Instalar Dependências
# ═══════════════════════════════════════════════════════════════
Write-Title "3. Instalando dependências..."

# Atualizar pip
Write-Info "Atualizando pip..."
& $venvPython -m pip install --upgrade pip --quiet

# Verificar se torch precisa ser instalado
$torchInstalled = & $venvPip show torch 2>$null
if (-not $torchInstalled) {
    Write-Info "Instalando PyTorch (versão CPU - mais leve)..."
    Write-Host "   Isso pode demorar alguns minutos..." -ForegroundColor Gray
    & $venvPip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Falha ao instalar PyTorch!"
        # Tentar método alternativo
        Write-Info "Tentando método alternativo..."
        & $venvPip install torch --quiet
    }
}

# Instalar outras dependências
Write-Info "Instalando outras dependências..."
& $venvPip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Err "Falha ao instalar dependências!"
    Read-Host "Pressione Enter para sair"
    exit 1
}

Write-Success "Todas as dependências instaladas!"

# ═══════════════════════════════════════════════════════════════
# 4. Executar Aplicativo
# ═══════════════════════════════════════════════════════════════
Write-Title "4. Iniciando Sector Flow Setups..."

Write-Host @"

  ════════════════════════════════════════════════════════════
   Aplicativo iniciando...
   
   Dica: Abra o Le Mans Ultimate para conectar a telemetria!
  ════════════════════════════════════════════════════════════

"@ -ForegroundColor Green

& $venvPython main.py

# Se o aplicativo fechar
Write-Host "`nAplicativo encerrado." -ForegroundColor Yellow
Read-Host "Pressione Enter para fechar"

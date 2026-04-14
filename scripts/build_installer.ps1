# ==============================================================================
# SECTOR FLOW SETUPS - BUILD INSTALLER AUTOMATION
# ==============================================================================
#
# Este script automatiza todo o processo de criação do instalador profissional:
#   1. Verifica dependências (Inno Setup, PyInstaller)
#   2. Cria imagens do instalador (BMP)
#   3. Compila o executável (.exe)
#   4. Compila o instalador (.exe setup)
#
# Uso:
#   .\build_installer.ps1           # Build completo
#   .\build_installer.ps1 -SkipExe  # Apenas instalador (se .exe já existe)
#   .\build_installer.ps1 -Clean    # Limpa builds anteriores primeiro
#
# ==============================================================================

param(
    [switch]$SkipExe,      # Pular compilação do .exe
    [switch]$SkipImages,   # Pular criação de imagens
    [switch]$Clean,        # Limpar builds anteriores
    [switch]$Silent,       # Modo silencioso (menos output)
    [switch]$Help          # Mostrar ajuda
)

# Cores
$Colors = @{
    Success = "Green"
    Error   = "Red"
    Warning = "Yellow"
    Info    = "Cyan"
    Header  = "Magenta"
}

function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $Colors.Header
    Write-Host "  $text" -ForegroundColor $Colors.Header
    Write-Host ("=" * 60) -ForegroundColor $Colors.Header
    Write-Host ""
}

function Write-Step($step, $text) {
    Write-Host "[$step] " -NoNewline -ForegroundColor $Colors.Info
    Write-Host $text -ForegroundColor White
}

function Write-SubStep($text, $status) {
    $icon = if ($status -eq "ok") { "[OK]" } elseif ($status -eq "warn") { "[!]" } else { "[X]" }
    $color = if ($status -eq "ok") { $Colors.Success } elseif ($status -eq "warn") { $Colors.Warning } else { $Colors.Error }
    Write-Host "    $icon " -NoNewline -ForegroundColor $color
    Write-Host $text -ForegroundColor Gray
}

function Show-Help {
    Write-Host @"

SECTOR FLOW SETUPS - Build Installer
=====================================

Uso: .\build_installer.ps1 [opções]

Opções:
  -SkipExe      Pular compilação do .exe (usar existente)
  -SkipImages   Pular criação de imagens BMP
  -Clean        Limpar builds anteriores antes de começar
  -Silent       Modo silencioso (menos output)
  -Help         Mostrar esta ajuda

Exemplos:
  .\build_installer.ps1                    # Build completo
  .\build_installer.ps1 -SkipExe           # Só instalador
  .\build_installer.ps1 -Clean -SkipImages # Limpar e rebuildar

Requisitos:
  - Python 3.10+ com ambiente virtual
  - PyInstaller (instalado via pip)
  - Inno Setup 6.2+ (https://jrsoftware.org/isinfo.php)
  - Pillow (para criar imagens)

"@
}

# Mostrar ajuda se solicitado
if ($Help) {
    Show-Help
    exit 0
}

# Configuração
$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
# Navegar para pasta raiz do projeto (scripts está dentro da raiz)
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

$startTime = Get-Date

Write-Header "SECTOR FLOW SETUPS - BUILD INSTALLER"
Write-Host "  Iniciado em: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# ==============================================================================
# PASSO 1: VERIFICAR DEPENDÊNCIAS
# ==============================================================================
Write-Step "1/6" "Verificando dependências..."

# Verificar Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-SubStep "Python não encontrado!" "error"
    Write-Host "     Instale Python 3.10+ de https://python.org" -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version 2>&1
Write-SubStep "Python: $pythonVersion" "ok"

# Verificar venv
$venvPath = Join-Path $projectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-SubStep "Ambiente virtual não encontrado. Execute start.ps1 primeiro!" "error"
    exit 1
}
Write-SubStep "Ambiente virtual: OK" "ok"

# Ativar venv
. "$venvPath\Scripts\Activate.ps1"

# Verificar PyInstaller
$pyinstaller = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-SubStep "Instalando PyInstaller..." "warn"
    pip install pyinstaller --quiet
}
Write-SubStep "PyInstaller: OK" "ok"

# Verificar Pillow
$pillow = pip show Pillow 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-SubStep "Instalando Pillow..." "warn"
    pip install Pillow --quiet
}
Write-SubStep "Pillow: OK" "ok"

# Verificar Inno Setup
$innoPath = $null
$possiblePaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $innoPath = $path
        break
    }
}

if (-not $innoPath) {
    Write-SubStep "Inno Setup não encontrado!" "error"
    Write-Host ""
    Write-Host "  Por favor, instale o Inno Setup 6:" -ForegroundColor Yellow
    Write-Host "  https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
    Write-Host ""
    
    $openBrowser = Read-Host "Abrir página de download? (s/n)"
    if ($openBrowser -eq "s") {
        Start-Process "https://jrsoftware.org/isdl.php"
    }
    exit 1
}
Write-SubStep "Inno Setup: $innoPath" "ok"

# ==============================================================================
# PASSO 2: LIMPAR BUILDS ANTERIORES (OPCIONAL)
# ==============================================================================
if ($Clean) {
    Write-Step "2/6" "Limpando builds anteriores..."
    
    $foldersToClean = @("dist", "build", "installer_output", "__pycache__")
    foreach ($folder in $foldersToClean) {
        $folderPath = Join-Path $projectRoot $folder
        if (Test-Path $folderPath) {
            Remove-Item $folderPath -Recurse -Force
            Write-SubStep "Removido: $folder" "ok"
        }
    }
    
    # Remover arquivos .spec antigos
    Get-ChildItem -Path $projectRoot -Filter "*.spec" | ForEach-Object {
        # Não remover se for o nosso arquivo de configuração
        if ($_.Name -ne "SectorFlowSetups.spec") {
            Remove-Item $_.FullName -Force
        }
    }
} else {
    Write-Step "2/6" "Pulando limpeza (use -Clean para limpar)"
}

# ==============================================================================
# PASSO 3: CRIAR IMAGENS DO INSTALADOR
# ==============================================================================
if (-not $SkipImages) {
    Write-Step "3/6" "Criando imagens do instalador..."
    
    $imageScript = Join-Path $scriptPath "create_installer_images.ps1"
    if (Test-Path $imageScript) {
        # Executar script de imagens de forma silenciosa
        & $imageScript | Out-Null
        
        # Verificar se imagens foram criadas
        $assetsPath = Join-Path $projectRoot "assets"
        $requiredImages = @("logo.bmp", "logo_small.bmp")
        $allImagesOk = $true
        
        foreach ($img in $requiredImages) {
            $imgPath = Join-Path $assetsPath $img
            if (Test-Path $imgPath) {
                Write-SubStep "$img criado" "ok"
            } else {
                Write-SubStep "$img não encontrado" "error"
                $allImagesOk = $false
            }
        }
        
        if (-not $allImagesOk) {
            Write-Host ""
            Write-Host "  Algumas imagens não foram criadas." -ForegroundColor Yellow
            Write-Host "  O instalador continuará com imagens padrão." -ForegroundColor Yellow
        }
    } else {
        Write-SubStep "Script de imagens não encontrado, usando padrão" "warn"
    }
} else {
    Write-Step "3/6" "Pulando criação de imagens (use sem -SkipImages para criar)"
}

# ==============================================================================
# PASSO 4: COMPILAR EXECUTÁVEL
# ==============================================================================
if (-not $SkipExe) {
    Write-Step "4/6" "Compilando executável com PyInstaller..."
    
    $specFile = Join-Path $projectRoot "scripts\SectorFlowSetups.spec"
    $distPath = Join-Path $projectRoot "dist"
    
    # Usar arquivo .spec se existir
    if (Test-Path $specFile) {
        Write-SubStep "Usando SectorFlowSetups.spec" "ok"
        
        # Executar PyInstaller
        Write-Host ""
        Write-Host "    Compilando... (isso pode demorar alguns minutos)" -ForegroundColor Gray
        Write-Host ""
        
        $pyInstallerOutput = pyinstaller $specFile --noconfirm 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-SubStep "Erro na compilação!" "error"
            Write-Host $pyInstallerOutput -ForegroundColor Red
            exit 1
        }
    } else {
        # Fallback: compilar direto
        Write-SubStep "Compilando main.py diretamente..." "warn"
        
        $mainPy = Join-Path $projectRoot "main.py"
        $iconPath = Join-Path $projectRoot "assets\logo.ico"
        
        $pyinstallerArgs = @(
            $mainPy,
            "--name=SectorFlowSetups",
            "--onefile",
            "--windowed",
            "--noconfirm"
        )
        
        if (Test-Path $iconPath) {
            $pyinstallerArgs += "--icon=$iconPath"
        }
        
        pyinstaller @pyinstallerArgs 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Write-SubStep "Erro na compilação!" "error"
            exit 1
        }
    }
    
    # Verificar se .exe foi criado
    $exePath = Join-Path $distPath "SectorFlowSetups.exe"
    if (Test-Path $exePath) {
        $exeSize = (Get-Item $exePath).Length / 1MB
        Write-SubStep "SectorFlowSetups.exe ($([math]::Round($exeSize, 1)) MB)" "ok"
    } else {
        Write-SubStep "Executável não foi criado!" "error"
        exit 1
    }
} else {
    Write-Step "4/6" "Pulando compilação do .exe"
    
    # Verificar se .exe existe
    $exePath = Join-Path $projectRoot "dist\SectorFlowSetups.exe"
    if (Test-Path $exePath) {
        Write-SubStep "Usando executável existente" "ok"
    } else {
        Write-SubStep "Executável não encontrado! Remova -SkipExe" "error"
        exit 1
    }
}

# ==============================================================================
# PASSO 5: COMPILAR INSTALADOR
# ==============================================================================
Write-Step "5/6" "Compilando instalador com Inno Setup..."

$issFile = Join-Path $scriptPath "installer\installer.iss"

if (-not (Test-Path $issFile)) {
    Write-SubStep "installer.iss não encontrado!" "error"
    exit 1
}

# Criar pasta de output se não existir
$outputDir = Join-Path $projectRoot "installer_output"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Compilar com Inno Setup
Write-Host ""
Write-Host "    Compilando instalador..." -ForegroundColor Gray

$innoOutput = & $innoPath $issFile 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-SubStep "Erro na compilação do instalador!" "error"
    Write-Host ""
    Write-Host $innoOutput -ForegroundColor Red
    exit 1
}

# Verificar se instalador foi criado
$installerPath = Get-ChildItem -Path $outputDir -Filter "*.exe" | Select-Object -First 1

if ($installerPath) {
    $installerSize = $installerPath.Length / 1MB
    Write-SubStep "$($installerPath.Name) ($([math]::Round($installerSize, 1)) MB)" "ok"
} else {
    Write-SubStep "Instalador não foi criado!" "error"
    exit 1
}

# ==============================================================================
# PASSO 6: RESUMO FINAL
# ==============================================================================
Write-Step "6/6" "Concluído!"

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Header "BUILD COMPLETO!"

Write-Host "  Arquivos criados:" -ForegroundColor Green
Write-Host ""

$exePath = Join-Path $scriptPath "dist\SectorFlowSetups.exe"
if (Test-Path $exePath) {
    $exeSize = (Get-Item $exePath).Length / 1MB
    Write-Host "    📦 Executável:" -ForegroundColor Cyan
    Write-Host "       dist\SectorFlowSetups.exe ($([math]::Round($exeSize, 1)) MB)" -ForegroundColor Gray
}

if ($installerPath) {
    Write-Host ""
    Write-Host "    📀 Instalador:" -ForegroundColor Cyan
    Write-Host "       installer_output\$($installerPath.Name)" -ForegroundColor Gray
    Write-Host "       Tamanho: $([math]::Round($installerSize, 1)) MB" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  ⏱️  Tempo total: $([math]::Round($duration.TotalMinutes, 1)) minutos" -ForegroundColor Gray
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor $Colors.Header
Write-Host ""

# Perguntar se deseja abrir a pasta
$openFolder = Read-Host "Abrir pasta do instalador? (s/n)"
if ($openFolder -eq "s") {
    Start-Process explorer $outputDir
}

Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "  1. Teste o instalador em um computador limpo" -ForegroundColor Gray
Write-Host "  2. Distribua o arquivo: $($installerPath.Name)" -ForegroundColor Gray
Write-Host ""

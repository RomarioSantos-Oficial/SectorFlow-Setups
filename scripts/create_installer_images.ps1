# ============================================================
# Script para criar imagens do instalador
# ============================================================
# Cria as imagens BMP necessárias para o Inno Setup Wizard
#
# Requisitos: Python + Pillow (pip install Pillow)
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CRIADOR DE IMAGENS DO INSTALADOR" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

$assetsPath = Join-Path $projectRoot "assets"

# Verifica se Pillow está instalado
Write-Host "[1/4] Verificando dependencias..." -ForegroundColor Yellow

$pythonScript = @"
import sys
try:
    from PIL import Image
    print("OK")
except ImportError:
    print("NEED_INSTALL")
"@

$result = python -c $pythonScript 2>$null

if ($result -ne "OK") {
    Write-Host "  -> Instalando Pillow..." -ForegroundColor Gray
    pip install Pillow --quiet
}
Write-Host "  [OK] Pillow disponivel" -ForegroundColor Green

# Script Python para criar as imagens
Write-Host "[2/4] Criando imagens do wizard..." -ForegroundColor Yellow

$imageScript = @"
from PIL import Image, ImageDraw, ImageFont
import os

assets_path = r'$assetsPath'
os.makedirs(assets_path, exist_ok=True)

# Cores do tema
BG_COLOR = (20, 20, 30)  # Fundo escuro
ACCENT_COLOR = (0, 120, 212)  # Azul Windows
TEXT_COLOR = (255, 255, 255)  # Branco

def create_gradient(width, height, color1, color2):
    """Cria gradiente vertical"""
    img = Image.new('RGB', (width, height))
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        for x in range(width):
            img.putpixel((x, y), (r, g, b))
    return img

def add_logo_if_exists(img, logo_path, position, max_size):
    """Adiciona logo se existir"""
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert('RGBA')
            logo.thumbnail(max_size, Image.Resampling.LANCZOS)
            # Centraliza na posição
            x = position[0] - logo.width // 2
            y = position[1] - logo.height // 2
            if logo.mode == 'RGBA':
                img.paste(logo, (x, y), logo)
            else:
                img.paste(logo, (x, y))
        except Exception as e:
            print(f"  Aviso: Nao foi possivel carregar logo: {e}")
    return img

# ============================================================
# 1. WizardImageFile (164x314 pixels) - Lateral esquerda
# ============================================================
print("  -> Criando logo.bmp (164x314)...")
wizard_img = create_gradient(164, 314, (30, 30, 50), (10, 10, 20))
draw = ImageDraw.Draw(wizard_img)

# Adiciona logo no centro superior
logo_path = os.path.join(assets_path, 'logo.png')
wizard_img = add_logo_if_exists(wizard_img, logo_path, (82, 80), (120, 120))

# Linha decorativa
draw.rectangle([10, 170, 154, 172], fill=ACCENT_COLOR)

# Texto
try:
    font_title = ImageFont.truetype("segoeui.ttf", 14)
    font_small = ImageFont.truetype("segoeui.ttf", 10)
except:
    font_title = ImageFont.load_default()
    font_small = font_title

draw.text((82, 190), "Sector Flow", fill=TEXT_COLOR, font=font_title, anchor="mm")
draw.text((82, 210), "Setups", fill=ACCENT_COLOR, font=font_title, anchor="mm")
draw.text((82, 250), "Le Mans Ultimate", fill=(150, 150, 150), font=font_small, anchor="mm")
draw.text((82, 265), "Setup Assistant", fill=(150, 150, 150), font=font_small, anchor="mm")
draw.text((82, 295), "v1.0.0", fill=(100, 100, 100), font=font_small, anchor="mm")

wizard_img.save(os.path.join(assets_path, 'logo.bmp'), 'BMP')
print("  [OK] logo.bmp criado")

# ============================================================
# 2. WizardSmallImageFile (55x55 pixels) - Canto superior direito
# ============================================================
print("  -> Criando logo_small.bmp (55x55)...")
small_img = Image.new('RGB', (55, 55), BG_COLOR)

# Adiciona logo redimensionado
small_img = add_logo_if_exists(small_img, logo_path, (27, 27), (50, 50))

small_img.save(os.path.join(assets_path, 'logo_small.bmp'), 'BMP')
print("  [OK] logo_small.bmp criado")

# ============================================================
# 3. Header Banner (640x100) - Para páginas internas (opcional)
# ============================================================
print("  -> Criando header.bmp (640x100)...")
header_img = create_gradient(640, 100, (30, 30, 50), (20, 20, 35))
draw_header = ImageDraw.Draw(header_img)

# Adiciona logo pequeno à esquerda
header_img = add_logo_if_exists(header_img, logo_path, (60, 50), (70, 70))

# Texto do header
try:
    font_header = ImageFont.truetype("segoeuib.ttf", 20)
    font_sub = ImageFont.truetype("segoeui.ttf", 12)
except:
    font_header = ImageFont.load_default()
    font_sub = font_header

draw_header.text((130, 35), "Sector Flow Setups", fill=TEXT_COLOR, font=font_header)
draw_header.text((130, 62), "Assistente Inteligente para Le Mans Ultimate", fill=(150, 150, 150), font=font_sub)

# Linha inferior decorativa
draw_header.rectangle([0, 95, 640, 100], fill=ACCENT_COLOR)

header_img.save(os.path.join(assets_path, 'header.bmp'), 'BMP')
print("  [OK] header.bmp criado")

# ============================================================
# 4. Uninstall Icon (256x256) - Para o desinstalador
# ============================================================
print("  -> Criando uninstall.bmp (48x48)...")
uninstall_img = Image.new('RGB', (48, 48), (40, 40, 50))
uninstall_img = add_logo_if_exists(uninstall_img, logo_path, (24, 24), (40, 40))
uninstall_img.save(os.path.join(assets_path, 'uninstall.bmp'), 'BMP')
print("  [OK] uninstall.bmp criado")

print("\n  Todas as imagens criadas com sucesso!")
"@

python -c $imageScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Imagens criadas com sucesso!" -ForegroundColor Green
} else {
    Write-Host "  [!] Erro ao criar imagens" -ForegroundColor Red
    exit 1
}

# Verifica se as imagens foram criadas
Write-Host "[3/4] Verificando arquivos criados..." -ForegroundColor Yellow
$requiredImages = @("logo.bmp", "logo_small.bmp", "header.bmp")
$allCreated = $true

foreach ($img in $requiredImages) {
    $imgPath = Join-Path $assetsPath $img
    if (Test-Path $imgPath) {
        $size = (Get-Item $imgPath).Length
        Write-Host "  [OK] $img ($([math]::Round($size/1KB, 1)) KB)" -ForegroundColor Green
    } else {
        Write-Host "  [X] $img nao encontrado" -ForegroundColor Red
        $allCreated = $false
    }
}

Write-Host "[4/4] Concluido!" -ForegroundColor Yellow
Write-Host ""
if ($allCreated) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  IMAGENS CRIADAS COM SUCESSO!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Arquivos criados em: $assetsPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Proximo passo:" -ForegroundColor Yellow
    Write-Host "  1. Compile o app: .\build.ps1" -ForegroundColor Gray
    Write-Host "  2. Compile o instalador: .\build_installer.ps1" -ForegroundColor Gray
} else {
    Write-Host "Algumas imagens nao foram criadas." -ForegroundColor Red
}
Write-Host ""

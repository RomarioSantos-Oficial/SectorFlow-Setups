@echo off
title Sector Flow Setups - Instalador
chcp 65001 >nul 2>&1
color 0B

echo.
echo   ╔═══════════════════════════════════════════════════════════╗
echo   ║                                                           ║
echo   ║           🏎  SECTOR FLOW SETUPS  🏎                      ║
echo   ║                                                           ║
echo   ║        Instalador e Inicializador Automático              ║
echo   ║                                                           ║
echo   ╚═══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [INFO] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado!
    echo.
    echo Para instalar o Python:
    echo   1. Acesse: https://www.python.org/downloads/
    echo   2. Baixe Python 3.10 ou superior
    echo   3. Durante a instalação, MARQUE: "Add Python to PATH"
    echo   4. Execute este script novamente
    echo.
    pause
    exit /b 1
)
echo [OK] Python encontrado!

echo.
echo [INFO] Configurando ambiente virtual...
if not exist ".venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
)
echo [OK] Ambiente virtual configurado!

echo.
echo [INFO] Ativando ambiente...
call .venv\Scripts\activate.bat

echo.
echo [INFO] Atualizando pip...
python -m pip install --upgrade pip --quiet

echo.
echo [INFO] Instalando PyTorch (versão CPU)...
echo        Isso pode demorar alguns minutos na primeira vez...
pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet

echo.
echo [INFO] Instalando demais dependências...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependências!
    pause
    exit /b 1
)
echo [OK] Dependências instaladas!

echo.
echo   ════════════════════════════════════════════════════════════
echo    Iniciando Sector Flow Setups...
echo.   
echo    Dica: Abra o Le Mans Ultimate para conectar a telemetria!
echo   ════════════════════════════════════════════════════════════
echo.

python main.py

echo.
echo Aplicativo encerrado.
pause

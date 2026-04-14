# 🏎️ Sector Flow Setups - Guia de Instalação e Build

## 📋 Índice
- [Instalação Rápida](#-instalação-rápida)
- [Compilar para .exe](#-compilar-para-exe)
- [Criar Instalador Windows](#-criar-instalador-windows)
- [Solução de Problemas](#-solução-de-problemas)

---

## 🚀 Instalação Rápida

### Opção 1: Script PowerShell (Recomendado)
```powershell
# Clique com botão direito no arquivo 'start.ps1' > "Executar com PowerShell"
# Ou execute no terminal:
powershell -ExecutionPolicy Bypass -File start.ps1
```

### Opção 2: Script Batch (CMD)
```batch
# Dê duplo clique em 'start.bat'
# Ou execute no terminal:
start.bat
```

### O que o script faz:
1. ✅ Verifica se Python 3.10+ está instalado
2. ✅ Cria ambiente virtual (.venv)
3. ✅ Instala PyTorch otimizado (versão CPU)
4. ✅ Instala todas as dependências
5. ✅ Inicia o aplicativo

---

## 📦 Compilar para .exe

Transforme o aplicativo em um executável Windows que roda sem Python instalado.

### Passo 1: Primeiro, instale as dependências
```powershell
.\start.ps1
```

### Passo 2: Compile o executável
```powershell
.\scripts\build.ps1
```

### Opções de Build:

| Modo | Comando | Descrição |
|------|---------|-----------|
| **Arquivo único** | `.\scripts\build.ps1 -OneFile` | Um `.exe` portátil (inicia mais lento) |
| **Pasta** | `.\scripts\build.ps1 -Folder` | Pasta com arquivos (inicia mais rápido) |
| **Limpar** | `.\scripts\build.ps1 -Clean` | Remove builds anteriores |

### Resultado:
- O executável será criado em: `dist/SectorFlowSetups.exe`
- Tamanho aproximado: 150-300 MB (inclui PyTorch)

---

## 🎁 Criar Instalador Windows

Para criar um instalador profissional (como programas comerciais):

### Requisitos:
1. [Inno Setup 6+](https://jrsoftware.org/isinfo.php) instalado
2. Já ter compilado o `.exe` com `.\build.ps1`

### Criar o instalador:
1. Abra `scripts/installer/installer.iss` no Inno Setup Compiler
2. Clique em **Build > Compile**
3. O instalador será criado em: `installer_output/SectorFlowSetups_Setup_1.0.0.exe`

### O instalador inclui:
- ✅ Ícone no Menu Iniciar
- ✅ Atalho na Área de Trabalho (opcional)
- ✅ Desinstalador no Painel de Controle
- ✅ Suporte a múltiplos idiomas (PT-BR, EN, ES)

---

## 🔧 Compilação Manual (Avançado)

Se preferir usar PyInstaller diretamente:

```powershell
# Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# Instalar PyInstaller
pip install pyinstaller

# Compilar (modo arquivo único)
pyinstaller --name=SectorFlowSetups --icon=assets/logo.ico --windowed --onefile main.py

# Ou usar o spec file customizado
pyinstaller SectorFlowSetups.spec
```

---

## ❓ Solução de Problemas

### "Python não encontrado"
1. Baixe Python em: https://www.python.org/downloads/
2. **IMPORTANTE**: Marque "Add Python to PATH" durante instalação
3. Reinicie o computador
4. Execute novamente

### "Erro de permissão no PowerShell"
```powershell
# Execute como Administrador:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Falha ao instalar PyTorch"
```powershell
# Tente instalar manualmente:
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### "Executável muito grande"
O tamanho é normal (~200MB) porque inclui PyTorch. Para reduzir:
1. Use versão CPU do PyTorch (já é padrão)
2. O modo `--onedir` tem tamanho similar mas inicia mais rápido

### "Antivírus bloqueia o .exe"
Executáveis Python compilados podem acionar falsos positivos.
- Adicione uma exceção no antivírus
- Ou assine digitalmente o executável (requer certificado)

---

## 📁 Estrutura de Arquivos

```
📂 Sector Flow Setups/
├── 📄 start.ps1          # Instalador PowerShell
├── 📄 start.bat          # Instalador Batch
├── 📄 build.ps1          # Compilador para .exe
├── 📄 installer.iss      # Script Inno Setup
├── 📄 SectorFlowSetups.spec  # Config PyInstaller
├── 📄 requirements.txt   # Dependências Python
├── 📄 main.py            # Ponto de entrada
└── 📂 dist/              # Executável compilado (após build)
    └── SectorFlowSetups.exe
```

---

## 📞 Suporte

Discord: https://discord.gg/jJSVvKbFxs

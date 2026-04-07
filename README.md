# Sector Flow Settings

A tool for Le Mans Ultimate focused on telemetry reading, configuration suggestions with heuristics and AI, and creation or editing of .svm files.

## Discord

Join our Discord for support, questions, and news:

**[https://discord.gg/jJSVvKbFxs](https://discord.gg/jJSVvKbFxs)**

## Project Status

This project is in beta.

This means:

1. Features may change at any time;

2. Parts of the interface and flow may still receive adjustments;

3. Errors, incomplete behaviors, or limitations may still exist;

4. Improvements and updates should continue to accelerate frequently.

## Project Forks and Education

Users and developers can fork the project to study, adapt, and evolve the application.

If you wish, edit the application for your own use, testing, internal improvements, or learning; this is welcome.

If you make significant modifications, it's ideal to document the changes well to facilitate maintenance and future integrations.

## Updates

The project should continue to receive improvements, fixes, and evolutions continuously.

Among the points that may change over time are:

1. Interface;

2. Quality of AI suggestions;

3. Language support;

4. Configuration flow;

5. Performance and stability.

## Requirements

1. Windows.

2. Python 3.10 or higher.

3. Le Mans Ultimate installed.

4. An .svm file to use as a configuration base.

## Installation

### Quick Start (Recommended)

**Option 1 - PowerShell:**
```PowerShell
.\start.ps1
```

**Option 2 - Command Prompt:**
```batch
start.bat
```

The script automatically:
- Checks Python 3.10+ is installed
- Creates virtual environment
- Installs PyTorch (CPU version)
- Installs all dependencies
- Starts the application

### Manual Installation

### 1. Download the project

Download or clone this repository.

### 2. Create a virtual environment

In PowerShell, within the project folder:

```PowerShell
python -m venv.venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```PowerShell
pip install -r requirements.txt
```

### 4. Run the application

```PowerShell
python main.py
```

### Build Executable

To compile a standalone .exe (runs without Python):

```PowerShell
.\scripts\build.ps1
```

The executable will be created at `dist/SectorFlowSetups.exe`.

For full build and installer instructions, see [docs/INSTALL.md](docs/INSTALL.md).

## First Use

1. Open the application.

2. Open Le Mans Ultimate.

3. Wait for the LMU indicator to show that a connection has been established.

4. Go to the Setup tab.

5. Click Load .svm.

6. Choose a base configuration.

7. Enter the track and complete a few laps.

8. Ask for suggestions from AI or heuristics.

9. Create a new configuration or edit an existing one.

## User Guides

- Portuguese: [COMO_FUNCIONA_APLICACAO.md](docs/guides/COMO_FUNCIONA_APLICACAO.md)
- English: [HOW_TO_USE_APPLICATION.md](docs/guides/HOW_TO_USE_APPLICATION.md)
- Spanish: [COMO_USAR_LA_APLICACION.md](docs/guides/COMO_USAR_LA_APLICACION.md)
- Japanese: [APPLICATON_USER_GUIDE_JA.md](docs/guides/APPLICATON_USER_GUIDE_JA.md)
- Chinese: [APPLICATION_USER_GUIDE_ZH.md](docs/guides/APPLICATION_USER_GUIDE_ZH.md)

## Important Notes

1. The application attempts to automatically detect the Le Mans Ultimate path in Windows.

2. If the game is not open, the application continues trying to connect.

3. If the game is not installed, the application opens, but the settings functionality is limited.

4. The database and logs are automatically created in %APPDATA%/SectorFlowSetups.

5. The interface supports 5 languages (Portuguese, English, Spanish, Japanese, Chinese) and can be changed at any time via the Settings tab.

##Main Structure

- main.py: entry point.

- config.py: paths and settings.

- gui/: interface.

- core/: AI, heuristics, and training.

- data/: database, configuration analyzer, and telemetry.

- adapter/: shared memory connection.

## Changelog

### v1.2 — 2026-04-07
- Full i18n coverage for all 5 languages (pt-br, en, es, ja, zh): chat system messages, strategy results, and all UI labels are now translated
- Added `ThermalMapWidget` for tire temperature visualization in the Telemetry tab
- Expanded track POIs from 9 to 20 circuits
- Added IES (Setup Efficiency Index) badge in the Setup tab
- Added lap estimate with confidence indicator in Telemetry
- SECTORFLOW output filename preview before applying adjustments
- Safety: `validate_dependencies()` standalone function added
- Fixed `HeuristicSuggestion` field mismatch (rule_name / condition / explanation)

### v1.1 — previous
- Multi-language support (pt-br, en, es, ja, zh) via Settings tab
- LM Studio local model integration
- Real-time language switching without restart
- Autonomous learning system improvements

## Quick Troubleshooting

### The app opens but does not connect to the game

1. Check if the LMU is open.

2. Check if shared memory is working.

3. Check the logs in the user folder.

### The app opens but doesn't suggest anything

1. Complete at least one lap.

2. Confirm that you have loaded a configuration database.

3. Check if the Telemetry tab shows live data.

## The AI ​​seems to fail at the beginning

This is expected. There's no way the system can rely more on heuristics and improvements as it records laps and feedback.

# Sector Flow Setups

Ferramenta para Le Mans Ultimate focada em leitura de telemetria, sugestoes de setup com heuristicas e IA, e criacao ou edicao de arquivos .svm.

## Discord

Entre no nosso Discord para suporte, duvidas e novidades:

**[https://discord.gg/jJSVvKbFxs](https://discord.gg/jJSVvKbFxs)**

## Estado do Projeto

Este projeto esta em estado beta.

Isso significa:

1. funcionalidades podem mudar a qualquer momento;
2. partes da interface e do fluxo ainda podem receber ajustes;
3. erros, comportamentos incompletos ou limitacoes ainda podem existir;
4. melhorias e atualizacoes devem continuar acontecendo com frequencia.

## Forks e Edicao do Projeto

Usuarios e desenvolvedores podem fazer fork do projeto para estudar, adaptar e evoluir a aplicacao.

Se voce quiser editar a aplicacao para uso proprio, testes, melhorias internas ou aprendizado, esse fluxo e bem-vindo.

Se fizer modificacoes importantes, o ideal e documentar bem as mudancas para facilitar manutencao e futuras integracoes.

## Atualizacoes

O projeto deve continuar recebendo melhorias, correcoes e evolucoes de forma continua.

Entre os pontos que podem mudar ao longo do tempo estao:

1. interface;
2. qualidade das sugestoes da IA;
3. suporte a idiomas;
4. fluxo de configuracao;
5. desempenho e estabilidade.

## Requisitos

1. Windows.
2. Python 3.10 ou superior.
3. Le Mans Ultimate instalado.
4. Um arquivo .svm para usar como setup base.

## Instalacao

### 1. Baixar o projeto

Baixe ou clone este repositorio.

### 2. Criar ambiente virtual

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 4. Executar a aplicacao

```powershell
python main.py
```

## Primeiro Uso

1. Abra a aplicacao.
2. Abra o Le Mans Ultimate.
3. Espere o indicador LMU mostrar que houve conexao.
4. Va para a aba Setup.
5. Clique em Carregar .svm.
6. Escolha um setup base.
7. Entre na pista e complete algumas voltas.
8. Peca sugestoes pela IA ou heuristicas.
9. Crie um novo setup ou edite um setup existente.

## Guias de Uso

- Portugues: [COMO_FUNCIONA_APLICACAO.md](COMO_FUNCIONA_APLICACAO.md)
- English: [HOW_TO_USE_APPLICATION.md](HOW_TO_USE_APPLICATION.md)
- Espanol: [COMO_USAR_LA_APLICACION.md](COMO_USAR_LA_APLICACION.md)
- Japanese: [APPLICATON_USER_GUIDE_JA.md](APPLICATON_USER_GUIDE_JA.md)
- Chinese: [APPLICATION_USER_GUIDE_ZH.md](APPLICATION_USER_GUIDE_ZH.md)

## Observacoes Importantes

1. A aplicacao tenta detectar automaticamente o caminho do Le Mans Ultimate no Windows.
2. Se o jogo nao estiver aberto, a aplicacao continua tentando conectar.
3. Se o jogo nao estiver instalado, a aplicacao abre, mas a funcionalidade de setups fica limitada.
4. O banco e os logs sao criados automaticamente em %APPDATA%/SectorFlowSetups.
5. A interface ainda esta em portugues; o suporte real a troca de idioma ainda precisa ser implementado.

## Estrutura Principal

- main.py: ponto de entrada.
- config.py: caminhos e configuracoes.
- gui/: interface.
- core/: IA, heuristicas e treinamento.
- data/: banco, parser de setup e telemetria.
- adapter/: conexao com Shared Memory.

## Solucao de Problemas Rapida

### O app abre mas nao conecta ao jogo

1. Verifique se o LMU esta aberto.
2. Verifique se a Shared Memory esta funcionando.
3. Verifique os logs na pasta do usuario.

### O app abre mas nao sugere nada

1. Complete pelo menos uma volta.
2. Confirme se carregou um setup base.
3. Veja se a aba Telemetria mostra dados ao vivo.

### A IA parece fraca no inicio

Isso e esperado. No comeco o sistema depende mais de heuristicas e melhora conforme registra voltas e feedback.
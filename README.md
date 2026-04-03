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
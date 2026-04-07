# Como Usar a Aplicacao

Este guia explica o passo a passo para um usuario usar o Sector Flow Setups no dia a dia.

Versoes deste guia:

- Portugues: COMO_FUNCIONA_APLICACAO.md
- English: HOW_TO_USE_APPLICATION.md
- Espanol: COMO_USAR_LA_APLICACION.md
- Japanese: APPLICATON_USER_GUIDE_JA.md
- Chinese: APPLICATION_USER_GUIDE_ZH.md

## 1. O Que a Aplicacao Faz

O Sector Flow Setups ajuda voce a:

1. ler a telemetria do Le Mans Ultimate em tempo real;
2. entender o comportamento do carro;
3. sugerir ajustes de setup com heuristicas e IA;
4. criar um novo setup .svm sem alterar o arquivo base;
5. aprender com suas voltas ao longo do tempo.

## 2. O Que Voce Precisa Antes de Comecar

Antes de usar, confirme isto:

1. Voce esta no Windows.
2. O Python e as dependencias estao instalados.
3. O Le Mans Ultimate esta instalado.
4. O jogo consegue expor a Shared Memory normalmente.
5. Voce tem pelo menos um arquivo .svm para usar como base.

Para instalar as dependencias:

```bash
pip install -r requirements.txt
```

Para abrir o programa:

```bash
python main.py
```

## 3. Primeiro Uso

Siga esta ordem na primeira vez:

1. Abra o programa com python main.py.
2. Espere a janela principal aparecer.
3. Abra o Le Mans Ultimate.
4. Espere o indicador LMU mostrar que o jogo foi conectado.
5. Va para a aba Setup.
6. Clique em Carregar .svm.
7. Escolha um setup base.

Sem setup base carregado, a aplicacao continua funcionando, mas a criacao de novos setups fica limitada.

## 4. Passo a Passo de Uso Para o Usuario

### Passo 1. Abrir a aplicacao

Execute:

```bash
python main.py
```

### Passo 2. Esperar a conexao com o jogo

No topo da janela existem indicadores de status:

- LMU;
- IA;
- DB.

### Passo 3. Carregar um setup base

Na aba Setup:

1. clique em Carregar .svm;
2. selecione um arquivo de setup;
3. aguarde a confirmacao.

### Passo 4. Ir para a pista

Entre no jogo e complete algumas voltas.

### Passo 5. Ver a telemetria ao vivo

Na aba Telemetria, voce acompanha:

1. tempos de volta;
2. pneus;
3. combustivel e energia;
4. downforce e freios;
5. clima e estrategia.

### Passo 6. Pedir uma sugestao

Voce pode:

1. escrever no chat da aba Setup;
2. usar Pedir Sugestao IA;
3. usar Usar Heuristicas.

Exemplos:

- o carro esta com understeer na entrada;
- preciso de um setup para chuva;
- tc map -1;
- asa traseira +2.

### Passo 7. Criar ou editar um setup

Para criar um novo setup:

1. clique em Criar Setup;
2. escolha modo e clima;
3. confirme.

Para editar um existente:

1. clique em Editar Setup;
2. escolha o arquivo .svm;
3. confirme o backup;
4. aplique os ajustes.

### Passo 8. Repetir o ciclo

O melhor uso e este:

1. dirigir;
2. pedir sugestao;
3. testar;
4. mandar feedback;
5. repetir.

## 5. O Que Cada Aba Faz

### Setup

Carrega setup base, conversa com a IA, pede sugestoes, cria setups e edita setups.

### Telemetria

Mostra os dados ao vivo do carro e da sessao.

### Feedback

Permite descrever com mais precisao como o carro esta se comportando.

### Dados

Mostra sessoes, estatisticas, modelos salvos e exportacao.

## 6. Onde os Arquivos Ficam Salvos

Os dados persistentes do usuario ficam em:

```text
%APPDATA%/SectorFlowSetups
```

Principais itens:

- settings.json;
- db/lmu_engineer.db;
- models/;
- backups/;
- logs/.

## 7. Suporte a Idiomas

Hoje o projeto guarda uma preferencia de idioma em config.py, mas a interface ainda esta com textos fixos em portugues.

Entao:

1. sim, e possivel exibir a interface em ingles, espanhol, japones e chines;
2. nao, isso ainda nao esta implementado na GUI atual.

Para funcionar direito, ainda precisa:

1. centralizar os textos da interface;
2. criar arquivos de traducao;
3. criar um seletor de idioma;
4. recarregar labels, botoes e mensagens pelo idioma escolhido.

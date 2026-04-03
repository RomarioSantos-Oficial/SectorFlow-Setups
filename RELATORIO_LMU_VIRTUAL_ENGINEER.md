# 📋 RELATÓRIO DE VIABILIDADE TÉCNICA
## "LMU Virtual Engineer" — Agente de IA Local para Criação de Setups

**Autor:** Engenheiro de Software Sênior / Especialista em Dinâmica Veicular  
**Data:** 31 de Março de 2026  
**Status:** Aguardando Aprovação  

---

## 1. RESUMO EXECUTIVO

O projeto propõe a criação de um **agente de IA proprietário e 100% local** (sem APIs externas) que aprende a sugerir ajustes de setup para o jogo **Le Mans Ultimate** (engine rFactor 2) utilizando PyTorch, dados de telemetria via Shared Memory e feedback do usuário.

**Veredicto Geral: ✅ VIÁVEL — com ressalvas e melhorias sugeridas.**

O projeto é tecnicamente possível e o workspace já contém uma **base sólida** de código para leitura de Shared Memory e dados de telemetria que pode ser reutilizada. Porém, a arquitetura proposta (rede neural simples + RL básico) terá **limitações reais** que precisam ser compreendidas antes de iniciar.

---

## 2. ANÁLISE DO CÓDIGO EXISTENTE

### 2.1 O que já existe no workspace

| Módulo | Descrição | Reutilizável? |
|--------|-----------|:------------:|
| `pyRfactor2SharedMemory/rF2MMap.py` | Leitura de Shared Memory via `mmap` (Scoring, Telemetry, Extended, ForceFeedback) | ✅ Sim |
| `pyRfactor2SharedMemory/rF2data.py` | Estruturas `ctypes` completas (rF2Wheel, rF2VehicleTelemetry, rF2Scoring, etc.) | ✅ Sim |
| `pyRfactor2SharedMemory/rF2Type.py` | Type hints para IDE (rF2Wheel, rF2VehicleTelemetry com todos os campos) | ✅ Sim |
| `pyRfactor2SharedMemory/sharedMemoryAPI.py` | API de alto nível com detecção de processo e verificação de versão | ✅ Sim |
| `adapter/rf2_connector.py` | Conector com sync de dados, threading e mapeamento Scoring↔Telemetry | ✅ Sim |
| `adapter/rf2_data.py` | DataAdapter com classes organizadas: Brake, Engine, Inputs, Lap, Session, Tyre, etc. | ✅ **Muito útil** |
| `adapter/rf2_restapi.py` | REST API para dados adicionais (LMU-specific: brakeWear, suspensionDamage, stintUsage) | ✅ Sim |
| `adapter/restapi_connector.py` | Conector REST com threading e tasks assíncronas | ✅ Parcial |

### 2.2 Dados de Telemetria já disponíveis (rF2Wheel / rF2VehicleTelemetry)

Os dados mais importantes para a IA **já estão mapeados** nas structs `ctypes`:

- **Pneus:** `mTemperature[3]` (I/M/O em Kelvin), `mPressure` (kPa), `mWear`, `mCamber`, `mTireLoad`, `mGripFract`, `mToe`, `mTireCarcassTemperature`, `mTireInnerLayerTemperature[3]`
- **Suspensão:** `mSuspensionDeflection`, `mRideHeight`, `mSuspForce`
- **Freios:** `mBrakeTemp`, `mBrakePressure`
- **Veículo:** `mLocalVel` (velocidade local XYZ), `mLocalAccel` (aceleração), `mOri[3]` (matriz de orientação → Pitch/Roll/Yaw), `mFrontRideHeight`, `mRearRideHeight`, `mFrontDownforce`, `mRearDownforce`, `mDrag`
- **Motor:** `mEngineRPM`, `mEngineTorque`, `mGear`, `mFuel`
- **Lap:** `mLapNumber`, `mLapStartET`, `mElapsedTime` (para calcular lap time)

**Conclusão:** Toda a infraestrutura de leitura de dados já existe. Não é necessário reescrever o `telemetry_reader.py` do zero — basta criar um wrapper leve sobre o que já existe.

---

## 3. ANÁLISE DA ARQUITETURA PROPOSTA

### 3.1 Rede Neural (SetupNeuralNet)

**Proposta original:** MLP simples com Linear + ReLU.

| Aspecto | Avaliação |
|---------|-----------|
| Inputs propostos (temperaturas, pressões, pitch, roll, heave, velocidade, feedback) | ✅ Bom ponto de partida |
| Outputs propostos (deltas para molas, asa, camber, pressão de freio) | ✅ Adequado |
| Arquitetura MLP simples | ⚠️ Funcional, mas limitada |

**Cálculo de dimensionalidade:**
- Temperaturas pneus: 4 pneus × 3 zonas (I/M/O) = **12 inputs**
- Pressões pneus: **4 inputs**
- Pitch, Roll, Heave: **3 inputs**
- Velocidade de reta: **1 input**
- User Feedback Bias: **1 input**
- **Total: ~21 inputs**

- Molas (F/R): **2 outputs**
- Asa traseira: **1 output**
- Camber (F/R): **2 outputs**
- Pressão de freio: **1 output**
- **Total: 6 outputs**

### 3.2 Sistema de Aprendizado (RL Simples)

**Proposta original:** Reward baseado em tempo de volta; `loss.backward()` para reforçar.

| Aspecto | Avaliação |
|---------|-----------|
| Reward baseado em lap time | ⚠️ Signal muito ruidoso; lap time depende de **milhares** de fatores (piloto, tráfego, combustível, pneus, etc.) |
| `loss.backward()` direto | ⚠️ Isso é Supervised Learning com reward, não é RL verdadeiro. Funciona para o caso, mas precisa ser bem formulado |
| Convergência | ⚠️ Com poucos dados (voltas), pode demorar muito para convergir |

---

## 4. PROBLEMAS IDENTIFICADOS E MELHORIAS SUGERIDAS

### 4.1 🔴 PROBLEMA CRÍTICO: Signal-to-Noise do Lap Time

O tempo de volta é influenciado por centenas de variáveis (erro do piloto sendo a MAIOR delas). Usar apenas o lap time como reward vai fazer a IA aprender **ruído** em vez de **padrões reais**.

**Melhoria Sugerida: Reward Composto (multi-critério)**

```
Reward = w1 × ΔLapTime 
       + w2 × ΔBalançoTemperatura (I-M-O uniformidade)
       + w3 × ΔGripFract (aderência média)
       + w4 × ΔConsistência (desvio padrão lap times)
       + w5 × UserSatisfaction (feedback direto)
```

Isso captura MUITO mais informação de qualidade do que apenas lap time.

### 4.2 🟡 MELHORIA: Inputs Adicionais Importantes

Os inputs propostos são bons mas **faltam dados críticos** que já estão disponíveis na Shared Memory:

| Input Faltante | Por quê é Importante | Campo rF2 |
|----------------|---------------------|-----------|
| **Desgaste dos pneus** (`mWear`) | Setup ideal muda conforme pneu degrada | `rF2Wheel.mWear` |
| **Ride Height** (F/R) | Diretamente ligado a aerodinâmica e molas | `mFrontRideHeight`, `mRearRideHeight` |
| **Downforce** (F/R) | Feedback da asa e distribuição aero | `mFrontDownforce`, `mRearDownforce` |
| **Carga nos pneus** (`mTireLoad`) | Essencial para inferir sub/oversteer mecanicamente | `rF2Wheel.mTireLoad` |
| **Tipo de superfície** | Pista molhada muda tudo | `rF2Wheel.mSurfaceType` |
| **Temperatura da carcaça** | Indica aquecimento estrutural excessivo | `rF2Wheel.mTireCarcassTemperature` |
| **Combustível** (`mFuel`) | Peso do carro altera comportamento | `mFuel` |

**Recomendação:** Expandir para ~35-40 inputs com esses dados. A rede é pequena o suficiente para que isso não impacte performance.

### 4.3 🟡 MELHORIA: Outputs Adicionais

| Output Faltante | Por quê é Importante |
|------------------|--------------------|
| **Pressão dos pneus** (4 individuais) | Um dos ajustes MAIS impactantes e com feedback imediato |
| **Barra anti-rolagem** (F/R) | Controle direto de sub/oversteer transitório |
| **Diferencial** (preload/power/coast) | Controle de tração e estabilidade em curva |
| **Ride Height** (F/R) | Diretamente ligado ao downforce e rake |
| **Distribuição de frenagem** (bias) | Estabilidade na frenagem |

**Recomendação:** Expandir para ~12-15 outputs. A IA se torna mais completa sem custo computacional relevante.

### 4.4 🟡 MELHORIA: Normalização e Feature Engineering

Os dados da Shared Memory vêm em unidades muito diferentes:
- Temperaturas: Kelvin (250-400+)
- Pressões: kPa (100-200+)
- Velocidade: m/s (0-100)
- Feedback: -1 a +1

**Sem normalização, a rede vai dar peso desproporcional a features com valores maiores.**

**Recomendação:** Implementar `StandardScaler` ou normalização min-max para cada grupo de features. Armazenar os parâmetros de normalização junto com o modelo `.pth`.

### 4.5 🟢 MELHORIA: Sistema de Regras Heurísticas (Complementar à IA)

No início, quando a IA não tem dados suficientes, ela vai sugerir **lixo**. Isso vai frustrar o usuário.

**Recomendação:** Criar um **sistema de regras determinísticas** que funcione como "fallback" enquanto a IA treina:

```python
# Exemplo de regra heurística de engenharia
if temp_inside > temp_outside + 10:  # °C
    sugestao_camber = "Reduzir camber negativo (pneu está sobrecarregado por dentro)"
    delta_camber = +0.2  # graus, menos negativo

if temp_rear_avg > temp_front_avg + 15:
    sugestao_asa = "Aumentar asa traseira (eixo traseiro sobrecarregado)"
    delta_asa = +1  # click
```

Isso dá valor **imediato** ao usuário enquanto a IA aprende.

### 4.6 🟢 MELHORIA: Persistência de Dados de Treinamento

Além de salvar os pesos (`.pth`), salvar os dados brutos de treinamento em SQLite ou CSV:

| Benefício | Descrição |
|-----------|-----------|
| Retreinamento | Pode retreinar a IA com dados novos + antigos |
| Análise | Permite análise posterior dos dados offline |
| Debugging | Facilita identificar problemas no aprendizado |
| Compartilhamento | Dados podem ser compartilhados entre usuários |

### 4.7 🟢 MELHORIA: Leitura/Escrita de Arquivos .svm

O formato `.svm` do rFactor 2/LMU é um **arquivo de texto** com seções INI-like. Para leitura/escrita automática:

```
[SUSPENSION]
FrontAntiSwayBar=10000
RearAntiSwayBar=8000
...
[AERO]
RearWingAngle=15.5
...
```

**Recomendação:** Criar um parser/writer `.svm` que:
1. Lê todos os valores atuais do arquivo
2. Aplica os deltas sugeridos pela IA
3. Salva um NOVO arquivo (nunca sobrescrever o original)
4. Mantém backup automático com timestamp

---

## 5. ARQUITETURA PROPOSTA (REVISADA)

```
LMU_Virtual_Engineer/
│
├── main.py                          # Entry point
├── requirements.txt                 # Dependências
├── config.py                        # Configurações globais
│
├── core/
│   ├── __init__.py
│   ├── brain.py                     # SetupNeuralNet (PyTorch)
│   ├── trainer.py                   # Loop de treinamento e reward
│   ├── heuristics.py                # Regras determinísticas de engenharia
│   ├── normalizer.py                # Normalização de features
│   └── reward.py                    # Funções de reward compostas
│
├── data/
│   ├── __init__.py
│   ├── telemetry_reader.py          # Wrapper sobre adapter/ existente
│   ├── svm_parser.py                # Leitura/escrita de arquivos .svm
│   ├── session_logger.py            # Log de sessão (SQLite/CSV)
│   └── export.py                    # Exportação de insights (JSON, pesos)
│
├── gui/
│   ├── __init__.py
│   ├── app.py                       # Janela principal CustomTkinter
│   ├── tab_telemetry.py             # Aba [Telemetria]
│   ├── tab_adjustment.py            # Aba [Ajuste]
│   ├── tab_files.py                 # Aba [Arquivos]
│   └── widgets.py                   # Componentes reutilizáveis
│
├── adapter/                         # ← JÁ EXISTE (reutilizar)
│   ├── rf2_connector.py
│   ├── rf2_data.py
│   ├── rf2_restapi.py
│   └── restapi_connector.py
│
├── pyRfactor2SharedMemory/          # ← JÁ EXISTE (reutilizar)
│   ├── rF2data.py
│   ├── rF2MMap.py
│   ├── rF2Type.py
│   └── sharedMemoryAPI.py
│
├── models/                          # Armazenamento de modelos
│   └── .gitkeep
│
├── backups/                         # Backups de setups .svm
│   └── .gitkeep
│
└── logs/                            # Logs de sessão
    └── .gitkeep
```

---

## 6. DEPENDÊNCIAS

```
# requirements.txt
torch>=2.0.0           # PyTorch (CPU only — ~150MB)
customtkinter>=5.2.0   # Interface gráfica moderna
Pillow>=10.0.0         # Para icons na GUI
psutil>=5.9.0          # Detecção de processo rF2 (já usado no projeto)
numpy>=1.24.0          # Manipulação numérica
```

**Nota:** PyTorch CPU-only é suficiente para uma rede MLP desta escala. GPU seria overkill.

---

## 7. RISCOS E MITIGAÇÕES

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|:------------:|:-------:|-----------|
| 1 | IA sugere ajustes ruins no início | 🔴 Alta | 🟡 Médio | Sistema de heurísticas como fallback |
| 2 | Lap time ruidoso impede aprendizado | 🔴 Alta | 🔴 Alto | Reward composto multi-critério |
| 3 | Poucos dados de treinamento | 🟡 Média | 🟡 Médio | Pré-popular com dados sintéticos + compartilhamento entre usuários |
| 4 | Shared Memory indisponível (jogo fechado) | 🟢 Baixa | 🟢 Baixo | Modo offline para análise de dados salvos |
| 5 | Formato .svm muda entre versões LMU | 🟡 Média | 🟡 Médio | Parser flexível com validação |
| 6 | Overfitting em um carro/pista | 🟡 Média | 🟡 Médio | Incluir identificação de carro/pista como input; normalizar por combo |
| 7 | Usuário não entende as sugestões | 🟡 Média | 🟡 Médio | Exibir explicações em linguagem natural junto com cada sugestão |

---

## 8. ESTIMATIVA DE COMPLEXIDADE POR MÓDULO

| Módulo | Complexidade | Notas |
|--------|:----------:|-------|
| `brain.py` (rede neural) | Média | MLP simples, ~100 linhas |
| `trainer.py` (treinamento) | Alta | Lógica de reward, coleta de dados, loop de treino |
| `heuristics.py` (regras) | Média | Regras determinísticas baseadas em engenharia |
| `telemetry_reader.py` | Baixa | Wrapper sobre código existente |
| `svm_parser.py` | Média | Parsing de formato proprietário |
| `gui/app.py` + abas | Alta | CustomTkinter com visualização em tempo real |
| `export.py` (JSON + pesos) | Baixa | Serialização simples |

---

## 9. ESPECIFICAÇÃO TÉCNICA DA REDE NEURAL (Revisada)

```
┌─────────────────────────────────────────────┐
│              CAMADA DE ENTRADA              │
│                 (~38 neurons)               │
├─────────────────────────────────────────────┤
│  Temp Pneus I/M/O × 4    = 12              │
│  Pressão Pneus × 4       =  4              │
│  Desgaste Pneus × 4      =  4              │
│  Carga Pneus × 4         =  4              │
│  Ride Height (F/R)        =  2              │
│  Downforce (F/R)          =  2              │
│  Pitch + Roll + Heave     =  3              │
│  Velocidade Máx Reta      =  1              │
│  Combustível              =  1              │
│  User Feedback Bias       =  1              │
│                                             │
├─────────────────────────────────────────────┤
│          CAMADA OCULTA 1 (128 ReLU)         │
├─────────────────────────────────────────────┤
│          CAMADA OCULTA 2 (64 ReLU)          │
├─────────────────────────────────────────────┤
│          CAMADA OCULTA 3 (32 ReLU)          │
├─────────────────────────────────────────────┤
│             CAMADA DE SAÍDA                 │
│              (~12 neurons)                  │
├─────────────────────────────────────────────┤
│  Δ Mola Dianteira         =  1              │
│  Δ Mola Traseira          =  1              │
│  Δ Asa Traseira           =  1              │
│  Δ Camber Dianteiro       =  1              │
│  Δ Camber Traseiro        =  1              │
│  Δ Pressão Freio (bias)   =  1              │
│  Δ Pressão Pneu FL/FR/RL/RR =  4           │
│  Δ Anti-Roll Bar (F/R)    =  2              │
│                                             │
│  Ativação: Tanh (deltas entre -1 e +1)      │
│  Depois escalar para range real do ajuste   │
└─────────────────────────────────────────────┘
```

---

## 10. FLUXO DE OPERAÇÃO

```
     ┌──────────────┐
     │  LMU Rodando │
     └──────┬───────┘
            │ Shared Memory (mmap)
            ▼
   ┌────────────────┐
   │telemetry_reader│ ← Usa adapter/ existente
   └───────┬────────┘
           │ Dados normalizados
           ▼
   ┌───────────────┐     ┌────────────────┐
   │   brain.py    │────▶│  Sugestão de   │
   │  (PyTorch)    │     │   Ajuste (Δ)   │
   └───────┬───────┘     └───────┬────────┘
           │                     │
           │              ┌──────▼──────┐
           │              │    GUI      │
           │              │  Exibe +    │
           │              │  Feedback   │
           │              └──────┬──────┘
           │                     │
           │         ┌───────────▼───────────┐
           │         │ Usuário aplica ajuste │
           │         │ + dá feedback no LMU  │
           │         └───────────┬───────────┘
           │                     │
           │              ┌──────▼──────┐
           │              │ Nova volta  │
           │              │ + lap time  │
           │              └──────┬──────┘
           │                     │
           ▼                     ▼
   ┌───────────────┐    ┌────────────────┐
   │  reward.py    │◀───│ Reward Calc    │
   │  Calcula      │    │ (multi-fator)  │
   │  recompensa   │    └────────────────┘
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │  trainer.py   │
   │  Atualiza     │
   │  pesos (SGD)  │
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │  Salva .pth   │
   │  + JSON log   │
   └───────────────┘
```

---

## 11. PONTOS DE DECISÃO PARA APROVAÇÃO

Antes de iniciar o desenvolvimento, preciso da sua decisão nos seguintes pontos:

### ❓ Pergunta 1: Escopo de Outputs
Manter os **6 outputs originais** (molas, asa, camber, freio) ou expandir para os **12 sugeridos** (+ pressão pneus, ARB)?

### ❓ Pergunta 2: Sistema de Heurísticas
Incluir o **sistema de regras heurísticas** como fallback (recomendado) ou ir direto só com IA?

### ❓ Pergunta 3: Persistência de Dados
Usar **SQLite** (mais robusto, queries) ou **CSV** (mais simples, legível) para log de sessões?

### ❓ Pergunta 4: Formato de Compartilhamento
Manter o **JSON leve** proposto ou criar também um formato de **dataset** para compartilhar dados de treinamento entre usuários?

### ❓ Pergunta 5: Prioridade de Desenvolvimento
Qual a ordem de prioridade?
- **Opção A:** IA primeiro (brain.py + trainer.py) → GUI depois
- **Opção B:** GUI primeiro (visualização de telemetria funcional) → IA depois
- **Opção C:** Paralelo (recomendado — telemetry_reader + GUI básica + brain.py juntos)

---

## 12. CONCLUSÃO E RECOMENDAÇÃO

| Critério | Avaliação |
|----------|:---------:|
| Viabilidade técnica | ✅ Viável |
| Base de código existente | ✅ Excelente (Shared Memory + DataAdapter completos) |
| Risco técnico principal | ⚠️ Convergência da IA com poucos dados |
| Mitigação | ✅ Heurísticas + Reward composto |
| Valor para o usuário | ✅ Alto (mesmo sem IA, a telemetria em tempo real + heurísticas já ajudam) |

**Recomendação final:** ✅ **APROVAR** com as melhorias sugeridas (especialmente itens 4.1, 4.2, 4.4 e 4.5, que são os mais impactantes na qualidade final do produto).

O codebase existente no workspace (adapter/ + pyRfactor2SharedMemory/) fornece uma fundação sólida que reduz significativamente o esforço de desenvolvimento da camada de dados.

---

*Aguardo aprovação e respostas às perguntas da Seção 11 para iniciar a implementação.*

---

## 13. ADIÇÕES DO USUÁRIO — ANÁLISE DE VIABILIDADE (v2)

> **Nota:** A seção 14 (mais abaixo) contém o relatório completo de melhorias sobre o
> **Sistema de Criação de Setups com Clima, Arquivo Base e IA**, adicionado em 31/03/2026.

O usuário forneceu novas informações e requisitos. Abaixo a análise de cada item.

---

### 13.1 📂 CAMINHOS DE ARQUIVOS DO JOGO

O usuário definiu os diretórios reais onde o LMU armazena os dados:

| Tipo | Caminho | Uso |
|------|---------|-----|
| **Telemetria gravada** | `Le Mans Ultimate\UserData\Telemetry\` | Dados de voltas gravadas (CSV/MoTeC). A IA pode usar esses dados para pré-treinar OFFLINE, sem precisar do jogo rodando. |
| **Setups por pista** | `Le Mans Ultimate\UserData\player\Settings\<NomeDaPista>\` | Arquivos `.svm` organizados por circuito. A IA lê o setup atual e salva novos setups aqui. |

**Viabilidade: ✅ VIÁVEL**

**Impacto na Arquitetura:**
- Adicionar ao `config.py` detecção automática do caminho de instalação do LMU (via registro do Windows ou busca em diretórios comuns como `C:\Program Files (x86)\Steam\steamapps\common\Le Mans Ultimate\`).
- O `svm_parser.py` precisa listar os diretórios de pista e carregar automaticamente os setups disponíveis.
- O `session_logger.py` deve importar dados de telemetria gravada da pasta `Telemetry\` para pré-treinamento da IA.

**⚠️ Ponto de Atenção:** O caminho exato pode variar dependendo de onde o usuário instalou o jogo. Precisamos de uma tela de configuração inicial (ou auto-detecção) para localizar a pasta `UserData`.

---

### 13.2 📄 FORMATO .SVM — ANÁLISE COMPLETA

O usuário forneceu um exemplo real de arquivo `.svm`. Esta é uma informação **extremamente valiosa** que muda significativamente o escopo dos outputs da IA.

#### Formato Identificado:
```
ParametroSetting=INDICE//DESCRICAO_LEGIVEL
```

- **`INDICE`** = Valor inteiro (índice do setting no jogo, NÃO o valor físico)
- **`DESCRICAO`** = Texto legível com o valor real (ex: `33//-2.2 deg`, `70//110 kgf (92%)`)

**⚠️ DESCOBERTA CRÍTICA:** A IA precisa trabalhar com **índices inteiros** (não valores contínuos). Isso muda a abordagem:
- A saída da rede neural deve ser um **delta de índice** (ex: +1, -2, 0) em vez de um delta contínuo.
- Ou: a IA sugere o valor desejado e fazemos a conversão para o índice mais próximo.
- **Recomendação:** Usar saída contínua na rede neural e depois arredondar para o índice mais próximo. Isso permite gradientes suaves durante o treinamento.

#### Mapeamento de Parâmetros Ajustáveis vs. Fixos

Analisando o .svm fornecido, identifiquei quais parâmetros são realmente ajustáveis:

| Seção | Parâmetro | Ajustável? | Valor Exemplo |
|-------|-----------|:----------:|---------------|
| **GENERAL** | FuelSetting | ✅ | 94 → 0.95 |
| **GENERAL** | VirtualEnergySetting | ✅ | 46% |
| **REARWING** | RWSetting | ✅ | 6.0 deg |
| **BODYAERO** | BrakeDuctSetting (F/R) | ✅ | Open |
| **SUSPENSION** | FrontAntiSwaySetting | ✅ | D2-D2 (50x3mm) |
| **SUSPENSION** | RearAntiSwaySetting | ✅ | D3-D4 (30x3mm) |
| **SUSPENSION** | FrontToeInSetting | ✅ | -0.117 deg |
| **SUSPENSION** | RearToeInSetting | ✅ | 0.117 deg |
| **CONTROLS** | RearBrakeSetting (bias) | ✅ | 50.5:49.5 |
| **CONTROLS** | BrakePressureSetting | ✅ | 110 kgf (92%) |
| **CONTROLS** | TractionControlMapSetting | ✅ | 5 |
| **CONTROLS** | TCPowerCutMapSetting | ✅ | 5 |
| **CONTROLS** | TCSlipAngleMapSetting | ✅ | 5 |
| **CONTROLS** | AntilockBrakeSystemMapSetting | ✅ | 9 |
| **DRIVELINE** | DiffPreloadSetting | ✅ | 70 Nm |
| **Per-Roda (×4)** | CamberSetting | ✅ | -2.2 deg / -1.5 deg |
| **Per-Roda (×4)** | PressureSetting | ✅ | 136 kPa |
| **Per-Roda (×4)** | SpringSetting | ✅ | 3 / 5 |
| **Per-Roda (×4)** | RideHeightSetting | ✅ | 5.2 cm / 6.6 cm |
| **Per-Roda (×4)** | SlowBumpSetting | ✅ | 8 |
| **Per-Roda (×4)** | FastBumpSetting | ✅ | 9 / 7 |
| **Per-Roda (×4)** | SlowReboundSetting | ✅ | 7 / 9 |
| **Per-Roda (×4)** | FastReboundSetting | ✅ | 6 / 8 |
| **Per-Roda (×4)** | CompoundSetting | ✅ | Medium |
| **GENERAL** | CGHeight/Right/Rear | ❌ | Non-adjustable |
| **DRIVELINE** | FinalDrive, Gears | ❌ | Fixed |
| **DRIVELINE** | DiffPower/Coast | ❌ | Non-adjustable |

**Total de parâmetros ajustáveis: ~45** (sendo ~28 per-roda × 4 posições + ~17 globais)

**⚠️ MUDANÇA IMPORTANTE NO ESCOPO:** O número de outputs da IA salta de **12 (proposta anterior)** para potencialmente **~45**. Isso tem implicações:

| Aspecto | Impacto |
|---------|---------|
| Tamanho da rede | Precisa aumentar (mais neurons nas camadas ocultas) |
| Dados necessários | MUITO mais voltas necessárias para convergir |
| Complexidade | Maior risco de overfitting |

**Recomendação:** Dividir em **3 níveis de ajuste** que o usuário pode escolher:

| Nível | Parâmetros | Qtd Outputs | Para quem |
|-------|------------|:-----------:|-----------|
| **Básico** | Asa, Molas (F/R), Camber (F/R), Pressão pneus (F/R), Pressão freio | ~8 | Iniciantes |
| **Intermediário** | + ARB, Toe, Ride Height, Amortecedores (Bump/Rebound lento), Diff Preload | ~20 | Intermediários |
| **Avançado** | Tudo ajustável (inclui Fast Bump/Rebound, TC/ABS maps, Brake Duct) | ~45 | Experts |

---

### 13.3 🤖 SISTEMA DE PERGUNTAS INTERATIVAS DA IA

O usuário quer que a IA **faça perguntas ao piloto** para calibrar:
> "Está saindo de frente? Os pneus estão quentes? etc."

**Viabilidade: ✅ VIÁVEL — e é uma EXCELENTE ideia.**

**Implementação Sugerida:**

A IA combina perguntas + dados de telemetria para um diagnóstico mais preciso:

```
┌─────────────────────────────────────────────────────────┐
│  🏎️ DIAGNÓSTICO PÓS-STINT                              │
│                                                         │
│  A telemetria detectou:                                 │
│  • Temp pneu FL interno +12°C acima do externo          │
│  • Grip traseiro 8% menor que dianteiro                 │
│                                                         │
│  Confirme com base na sua percepção:                    │
│                                                         │
│  1. O carro está:                                       │
│     ○ Saindo de frente (understeer)                     │
│     ● Saindo de traseira (oversteer)      ← detectado   │
│     ○ Neutro                                            │
│                                                         │
│  2. Em qual fase da curva?                              │
│     ☑ Entrada     ☑ Meio     ☐ Saída                   │
│                                                         │
│  3. Os freios estão:                                    │
│     ○ Bons   ● Travando cedo   ○ Fracos                │
│                                                         │
│  4. Confiança geral (1-10): [███████░░░] 7              │
│                                                         │
│  [Aplicar Diagnóstico]  [Pular]                         │
└─────────────────────────────────────────────────────────┘
```

**Benefícios:**
- A IA **já detecta** anomalias pela telemetria e pede confirmação (não é adivinhação)
- O feedback do piloto complementa dados que a telemetria não captura (sensação subjetiva, confiança)
- Cria um ciclo de aprendizado muito mais rico para o Reward

**Impacto na Arquitetura:**
- Novo módulo: `core/diagnostics.py` — Sistema de diagnóstico que analisa telemetria e gera perguntas contextuais
- Nova aba na GUI: `[Diagnóstico]` ou integrar na aba `[Ajuste]`
- O feedback das perguntas alimenta o `User Feedback Bias` da rede neural (expande de 1 valor para ~5-8 valores)

---

### 13.4 🏁 FASE DE APRENDIZADO INICIAL (5-10 VOLTAS)

O usuário quer uma fase obrigatória de **5-10 voltas** para a IA aprender o estilo do piloto antes de sugerir qualquer ajuste.

**Viabilidade: ✅ VIÁVEL**

**Implementação Sugerida:**

```
┌───────────────────────────────────────────────────┐
│  📊 FASE DE APRENDIZADO — Coleta de Dados        │
│                                                   │
│  Circuito: Le Mans (Circuit de la Sarthe)         │
│  Carro: Toyota GR010 Hybrid                       │
│                                                   │
│  Voltas completadas: ████████░░ 8/10              │
│                                                   │
│  Dados coletados:                                 │
│  • Lap times: 3:28.4 → 3:26.1 (melhorando ↓)     │
│  • Consistência: σ = 1.2s (boa)                   │
│  • Vel. máx reta: 338 km/h                        │
│  • Freio mais quente: RL (645°C)                  │
│  • Pneu mais gasto: FR (96%)                      │
│                                                   │
│  Status: Coletando... (faltam 2 voltas)           │
│                                                   │
│  A IA começará a sugerir ajustes após 10 voltas.  │
│  Enquanto isso, as HEURÍSTICAS já estão ativas.   │
│                                                   │
│  [⏩ Iniciar sugestões agora (mín. 5 voltas)]     │
└───────────────────────────────────────────────────┘
```

**O que a IA aprende nessas voltas:**
1. **Perfil de pilotagem** — Velocidades de entrada/saída de curva, pontos de frenagem, agressividade
2. **Baseline de performance** — Tempo de referência para calcular melhorias
3. **Desgaste padrão** — Como os pneus degradam com esse piloto
4. **Pontos problemáticos** — Curvas onde o piloto perde mais tempo
5. **Temperaturas de equilíbrio** — Temperatura "estável" dos pneus e freios

**Impacto na Arquitetura:**
- `core/driver_profile.py` — Novo módulo que cria o perfil do piloto
- O perfil é salvo junto com os pesos da IA (por combinação piloto+carro+pista)

---

### 13.5 🗺️ DADOS DE MAPA E TELEMETRIA POR SETOR

O usuário quer que a IA use **dados do mapa da pista** (zonas de frenagem, temperaturas por setor, etc.).

**Viabilidade: ⚠️ PARCIALMENTE VIÁVEL**

| Aspecto | Disponibilidade |
|---------|:--------------:|
| Posição no mapa (X, Y, Z) | ✅ Disponível via `mPos` na Shared Memory |
| Velocidade por posição | ✅ Calculável com `mPos` + `mLocalVel` |
| Temperaturas por zona | ✅ Calculável (armazenar temp vs posição) |
| Zonas de frenagem | ✅ Detectável via `mBrakePressure` > threshold |
| Mapa visual da pista | ⚠️ Não fornecido pelo jogo; teria que ser **construído** pela própria telemetria |

**Recomendação:** 
- A IA **constrói o mapa automaticamente** nas primeiras voltas, plotando `mPos[X]` vs `mPos[Z]`
- Sobrepõe dados de cor (velocidade, temperatura, frenagem) no mapa
- Identifica setores problemáticos (onde os tempos por mini-setor são piores que a média)

**Impacto na Arquitetura:**
- `data/track_mapper.py` — Construção e análise do mapa da pista
- Integração com a aba `[Telemetria]` da GUI para visualização do mapa

---

### 13.6 💾 OPÇÕES DE SALVAR SETUP

O usuário quer:
- **Criar novo arquivo .svm** (com nome personalizado ou timestamp)
- **Modificar o existente** (sobrescrevendo)
- **Escolha sempre do usuário** (nunca automático sem confirmação)

**Viabilidade: ✅ VIÁVEL**

**Implementação Sugerida:**

```
┌─────────────────────────────────────────────────────┐
│  💾 SALVAR SETUP                                    │
│                                                     │
│  Setup base: Toyota_LeMans_Qualifying.svm           │
│  Circuito: Le Mans (Circuit de la Sarthe)           │
│                                                     │
│  Alterações feitas:                                 │
│  • RWSetting: 6 → 7 (+1.0 deg asa traseira)        │
│  • CamberSetting FL: 33 → 31 (-1.8 deg → -1.4 deg)│
│  • BrakePressureSetting: 70 → 72 (+2%)              │
│                                                     │
│  Como deseja salvar?                                │
│  ● Criar novo arquivo                               │
│    Nome: [Toyota_LeMans_Race_v2          ]          │
│  ○ Sobrescrever setup atual                         │
│                                                     │
│  ☑ Criar backup do original antes de modificar      │
│                                                     │
│  [Salvar]  [Cancelar]                               │
└─────────────────────────────────────────────────────┘
```

**Regras de segurança:**
1. **NUNCA** sobrescrever sem confirmação explícita do usuário
2. **SEMPRE** criar backup automático antes de sobrescrever (com timestamp)
3. Salvar no diretório correto: `Le Mans Ultimate\UserData\player\Settings\<NomeDaPista>\`
4. Manter histórico de versões

---

## 14. ARQUITETURA REVISADA (v2) — COM TODAS AS ADIÇÕES

```
LMU_Virtual_Engineer/
│
├── main.py                          # Entry point
├── requirements.txt                 # Dependências
├── config.py                        # Configurações (caminhos LMU, preferências)
├── setup_wizard.py                  # Assistente de primeira execução (detectar LMU)
│
├── core/
│   ├── __init__.py
│   ├── brain.py                     # SetupNeuralNet (PyTorch) — ~45 outputs
│   ├── trainer.py                   # Loop de treinamento e reward
│   ├── heuristics.py                # Regras determinísticas de engenharia
│   ├── diagnostics.py               # 🆕 Sistema de perguntas interativas
│   ├── driver_profile.py            # 🆕 Perfil do piloto (estilo, baseline)
│   ├── normalizer.py                # Normalização de features
│   └── reward.py                    # Funções de reward compostas
│
├── data/
│   ├── __init__.py
│   ├── telemetry_reader.py          # Wrapper sobre adapter/ existente
│   ├── telemetry_importer.py        # 🆕 Importar dados de UserData\Telemetry\
│   ├── svm_parser.py                # Leitura/escrita .svm (formato real mapeado)
│   ├── track_mapper.py              # 🆕 Construção de mapa da pista via mPos
│   ├── session_logger.py            # Log de sessão (SQLite)
│   └── export.py                    # Exportação de insights (JSON, pesos)
│
├── gui/
│   ├── __init__.py
│   ├── app.py                       # Janela principal CustomTkinter
│   ├── tab_telemetry.py             # Aba [Telemetria] — com mapa da pista
│   ├── tab_adjustment.py            # Aba [Ajuste] — 3 níveis (Básico/Inter/Avançado)
│   ├── tab_diagnostic.py            # 🆕 Aba [Diagnóstico] — perguntas da IA
│   ├── tab_files.py                 # Aba [Arquivos] — gerenciador .svm
│   ├── tab_learning.py              # 🆕 Aba [Aprendizado] — fase inicial 5-10 voltas
│   └── widgets.py                   # Componentes reutilizáveis
│
├── adapter/                         # ← JÁ EXISTE (reutilizar)
├── pyRfactor2SharedMemory/          # ← JÁ EXISTE (reutilizar)
│
├── models/                          # Pesos da IA (.pth) por combo carro+pista
├── profiles/                        # 🆕 Perfis de pilotos
├── backups/                         # Backups automáticos de .svm
└── logs/                            # Logs de sessão (SQLite)
```

---

## 15. REDE NEURAL REVISADA (v2) — COM OUTPUTS REAIS DO .SVM

```
┌──────────────────────────────────────────────────────────┐
│                   CAMADA DE ENTRADA                      │
│                     (~42 neurons)                        │
├──────────────────────────────────────────────────────────┤
│  Temp Pneus I/M/O × 4 rodas        = 12                 │
│  Pressão Pneus × 4                  =  4                │
│  Desgaste Pneus × 4                 =  4                │
│  Carga Pneus × 4                    =  4                │
│  Ride Height (F/R)                   =  2                │
│  Downforce (F/R)                     =  2                │
│  Pitch + Roll + Heave                =  3                │
│  Velocidade Máx Reta                 =  1                │
│  Combustível                         =  1                │
│  User Feedback (sub/oversteer)       =  1                │
│  User Feedback (fase curva: E/M/S)   =  3                │
│  User Feedback (confiança geral)     =  1                │
│                                                          │
├──────────────────────────────────────────────────────────┤
│           CAMADA OCULTA 1 (256 neurons + ReLU)           │
│           + BatchNorm + Dropout(0.2)                     │
├──────────────────────────────────────────────────────────┤
│           CAMADA OCULTA 2 (128 neurons + ReLU)           │
│           + BatchNorm + Dropout(0.2)                     │
├──────────────────────────────────────────────────────────┤
│           CAMADA OCULTA 3 (64 neurons + ReLU)            │
├──────────────────────────────────────────────────────────┤
│                  CAMADA DE SAÍDA                         │
│      Nível Básico: 8  | Inter: 20 | Avançado: ~45       │
├──────────────────────────────────────────────────────────┤
│  Nível BÁSICO (8 outputs):                               │
│  Δ RWSetting (asa traseira)           =  1               │
│  Δ SpringSetting (F/R)                =  2               │
│  Δ CamberSetting (F/R)               =  2               │
│  Δ PressureSetting (F/R média)        =  2               │
│  Δ BrakePressureSetting               =  1               │
│                                                          │
│  Nível INTERMEDIÁRIO (adiciona +12):                     │
│  Δ AntiSwaySetting (F/R)              =  2               │
│  Δ ToeInSetting (F/R)                 =  2               │
│  Δ RideHeightSetting (F/R)            =  2               │
│  Δ SlowBumpSetting (F/R)              =  2               │
│  Δ SlowReboundSetting (F/R)           =  2               │
│  Δ DiffPreloadSetting                 =  1               │
│  Δ RearBrakeSetting (bias)            =  1               │
│                                                          │
│  Nível AVANÇADO (adiciona +25):                          │
│  Δ CamberSetting per-roda (×4)        =  4               │
│  Δ PressureSetting per-roda (×4)      =  4               │
│  Δ FastBumpSetting (F/R)              =  2               │
│  Δ FastReboundSetting (F/R)           =  2               │
│  Δ BrakeDuctSetting (F/R)             =  2               │
│  Δ SpringSetting per-roda (×4)        =  4               │
│  Δ RideHeightSetting per-roda (×4)    =  4               │
│  Δ TC/ABS Maps                        =  3               │
│                                                          │
│  Ativação: Tanh → arredondamento para índice inteiro     │
│  Escala: × max_delta por parâmetro (ex: asa ±3, camber ±5)│
└──────────────────────────────────────────────────────────┘
```

---

## 16. FORMATO .SVM — REGRAS DO PARSER

Com base no exemplo fornecido, o parser deve seguir estas regras:

| Regra | Descrição |
|-------|-----------|
| **1** | Formato: `NomeSetting=INDICE//DESCRICAO` |
| **2** | Ignorar linhas com `Non-adjustable`, `N/A`, `Fixed`, `Detached` |
| **3** | O INDICE é sempre um **inteiro** |
| **4** | A DESCRICAO é informativa (para exibir na GUI), mas o valor salvo é o INDICE |
| **5** | Seções entre `[]` devem ser preservadas exatamente como estão |
| **6** | `Symmetric=1` significa que FL/FR e RL/RR são simétricos por padrão |
| **7** | Seção `[BASIC]` contém sliders normalizados (0.0–1.0) para o menu do jogo |
| **8** | Ao salvar, manter TODAS as linhas do arquivo original (inclusive as N/A) |

---

## 17. NOVOS RISCOS IDENTIFICADOS (v2)

| # | Risco | Prob. | Impacto | Mitigação |
|---|-------|:-----:|:-------:|-----------|
| 8 | Mapeamento índice→valor físico varia entre carros | 🔴 Alta | 🔴 Alto | Parser deve extrair a descrição (ex: `33//-2.2 deg`) e construir tabela de conversão por carro |
| 9 | 45 outputs exigem MUITOS dados para convergir | 🟡 Média | 🟡 Médio | Níveis de complexidade (Básico/Inter/Avançado); começar no Básico |
| 10 | Telemetria gravada pode ter formato diferente entre versões LMU | 🟡 Média | 🟡 Médio | Parser flexível com detecção de colunas |
| 11 | Perguntas demais da IA podem irritar o usuário | 🟢 Baixa | 🟡 Médio | Limite de 3-5 perguntas; opção "Não perguntar mais" |
| 12 | Perfis de piloto podem ser confusos para múltiplos usuários | 🟢 Baixa | 🟢 Baixo | Seleção de perfil no início da sessão |

---

## 18. PONTOS DE DECISÃO ATUALIZADOS (v2)

### ❓ Pergunta 1 (ATUALIZADA): Nível Inicial de Outputs
Iniciar com qual nível?
- **Opção A:** Básico (8 outputs) — mais rápido de desenvolver e convergir
- **Opção B:** Intermediário (20 outputs) — bom equilíbrio
- **Opção C:** Já implementar os 3 níveis (mais trabalho, mais completo)

### ❓ Pergunta 2: Detecção do Caminho LMU
- **Opção A:** Auto-detecção via registro do Windows + Steam
- **Opção B:** O usuário seleciona a pasta manualmente na primeira execução
- **Opção C:** Ambos (auto-detecta e permite corrigir)

### ❓ Pergunta 3: Telemetria Gravada (UserData\Telemetry)
Usar os arquivos de telemetria gravada para **pré-treinar** a IA offline?
- **Opção A:** Sim, importar e usar como dados de treinamento inicial (**recomendado**)
- **Opção B:** Não, usar apenas dados em tempo real (mais simples mas desperdiça dados)

### ❓ Pergunta 4: Mapa da Pista
Incluir visualização do mapa construído pela telemetria?
- **Opção A:** Sim, com overlay de cores (velocidade, temperatura, frenagem)
- **Opção B:** Não, manter apenas dados numéricos (mais simples)

### ❓ Pergunta 5 (mantida): Persistência
Usar **SQLite** (robusto) ou **CSV** (simples) para logs?

### ❓ Pergunta 6 (mantida): Prioridade de Desenvolvimento
- **Opção A:** Core (IA + Parser .svm) → GUI depois
- **Opção B:** GUI (telemetria visual) → IA depois
- **Opção C:** Paralelo (**recomendado**)

---

## 19. CONCLUSÃO REVISADA (v2)

| Critério | v1 | v2 (com adições) |
|----------|:--:|:-----------------:|
| Viabilidade técnica | ✅ | ✅ Mantém viável |
| Escopo | Médio | 🔺 **Aumentou significativamente** |
| Valor para o usuário | Alto | 🔺 **Muito mais alto** (perguntas interativas + mapa + perfil) |
| Complexidade de desenvolvimento | Média | 🔺 **Alta** (mais módulos, mais outputs, parser mais complexo) |
| Risco principal | Convergência IA | ⚠️ **Mesmo + mapeamento índice/valor por carro** |

**Veredicto: ✅ VIÁVEL — mas com escopo significativamente maior.**

As adições do usuário (caminhos reais, formato .svm, perguntas interativas, fase de aprendizado, mapa da pista) são **todas excelentes** e melhoram muito o produto final. No entanto, o escopo cresceu ~60% em relação à proposta original.

**Recomendação:** ✅ **APROVAR** com desenvolvimento em **2 fases:**

| Fase | Escopo | Prioridade |
|------|--------|:----------:|
| **Fase 1 (MVP)** | Parser .svm + Telemetria ao vivo + brain.py (nível Básico, 8 outputs) + Heurísticas + GUI básica (3 abas) + Fase de aprendizado (5-10 voltas) | 🔴 Alta |
| **Fase 2 (Completo)** | Perguntas interativas + Mapa da pista + Importação telemetria gravada + Níveis Intermediário/Avançado + Perfil do piloto + Compartilhamento | 🟡 Média |

Isso permite ter um **produto funcional** na Fase 1, e iterar com base em feedback real na Fase 2.

---

## 20. BANCO DE DADOS — DESIGN COMPLETO (SQLite)

### 20.1 Por que SQLite?

| Critério | SQLite | CSV | JSON |
|----------|:------:|:---:|:----:|
| Queries complexas (ex: "melhor setup para Le Mans com chuva") | ✅ | ❌ | ❌ |
| Integridade referencial (FK constraints) | ✅ | ❌ | ❌ |
| Concorrência (GUI lê enquanto IA escreve) | ✅ WAL mode | ❌ | ❌ |
| Portabilidade (arquivo único, copiar/colar) | ✅ 1 arquivo `.db` | ✅ | ✅ |
| Performance com milhares de voltas | ✅ Índices B-tree | ❌ Lento | ❌ Lento |
| Zero dependências externas (já vem no Python) | ✅ `sqlite3` built-in | ✅ | ✅ |
| Backup fácil | ✅ Copiar 1 arquivo | ⚠️ Vários arquivos | ⚠️ |

**Decisão: SQLite em modo WAL** (Write-Ahead Logging) — permite leitura pela GUI enquanto a thread de telemetria escreve dados simultâneamente.

### 20.2 Schema do Banco de Dados

```sql
-- ============================================================
-- BANCO DE DADOS: lmu_engineer.db
-- Versão: 1.0
-- Engine: SQLite 3 com WAL mode
-- ============================================================

PRAGMA journal_mode=WAL;          -- Permite leitura e escrita simultâneas
PRAGMA foreign_keys=ON;           -- Integridade referencial ativa
PRAGMA auto_vacuum=INCREMENTAL;   -- Recupera espaço ao deletar dados antigos

-- ============================================================
-- 1. TABELA: cars (Catálogo de carros)
-- ============================================================
-- Armazena metadados de cada carro usado. Permite que a IA
-- aprenda padrões ESPECÍFICOS por carro (ex: Hypercar vs LMP2).
CREATE TABLE cars (
    car_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    car_name        TEXT NOT NULL UNIQUE,           -- Ex: "Toyota GR010 Hybrid"
    car_class       TEXT,                           -- Ex: "Hypercar", "LMP2", "GTE"
    engine_type     TEXT,                           -- Ex: "Hybrid", "ICE"
    drivetrain      TEXT,                           -- Ex: "AWD", "RWD"
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT                            -- Anotações livres do usuário
);

-- ============================================================
-- 2. TABELA: tracks (Catálogo de pistas)
-- ============================================================
-- Armazena metadados de cada pista. O folder_name corresponde
-- ao nome da pasta em UserData\player\Settings\<folder_name>\.
CREATE TABLE tracks (
    track_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    track_name      TEXT NOT NULL,                  -- Ex: "Le Mans - Circuit de la Sarthe"
    folder_name     TEXT NOT NULL UNIQUE,            -- Ex: "le_mans_24h" (nome real da pasta)
    track_length_m  REAL,                           -- Comprimento em metros
    num_sectors     INTEGER DEFAULT 3,              -- Número de setores
    track_type      TEXT,                           -- "Road", "Oval", "Street"
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 3. TABELA: driver_profiles (Perfis de pilotos)
-- ============================================================
-- Cada piloto tem um perfil. A IA adapta as sugestões ao
-- estilo de pilotagem (agressivo vs conservador).
CREATE TABLE driver_profiles (
    driver_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_name     TEXT NOT NULL UNIQUE,            -- Ex: "Piloto Principal"
    skill_level     TEXT DEFAULT 'intermediate',     -- "beginner", "intermediate", "expert"
    aggression      REAL DEFAULT 0.5,               -- 0.0 = muito conservador, 1.0 = muito agressivo
    braking_style   REAL DEFAULT 0.5,               -- 0.0 = freia cedo, 1.0 = freia tarde
    consistency     REAL DEFAULT 0.5,               -- Calculado automaticamente (σ lap times)
    preferred_level TEXT DEFAULT 'basic',            -- Nível de ajuste: "basic", "intermediate", "advanced"
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 4. TABELA: sessions (Sessões de jogo)
-- ============================================================
-- Uma "sessão" = uma entrada no jogo com um carro em uma pista.
-- Agrupa todas as voltas, setups e ajustes daquela sessão.
CREATE TABLE sessions (
    session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id       INTEGER NOT NULL REFERENCES driver_profiles(driver_id),
    car_id          INTEGER NOT NULL REFERENCES cars(car_id),
    track_id        INTEGER NOT NULL REFERENCES tracks(track_id),
    session_type    TEXT DEFAULT 'practice',         -- "practice", "qualifying", "race"
    weather         TEXT DEFAULT 'dry',              -- "dry", "wet", "mixed"
    air_temp_c      REAL,                           -- Temperatura do ar (°C)
    track_temp_c    REAL,                           -- Temperatura da pista (°C)
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at        TIMESTAMP,
    total_laps      INTEGER DEFAULT 0,
    best_lap_time   REAL,                           -- Melhor volta da sessão (segundos)
    notes           TEXT
);

-- Índice para busca rápida por combo carro+pista
CREATE INDEX idx_sessions_combo ON sessions(car_id, track_id);

-- ============================================================
-- 5. TABELA: laps (Dados por volta)
-- ============================================================
-- TABELA CENTRAL. Cada volta gravada com telemetria resumida.
-- É daqui que a IA extrai os dados de treinamento.
CREATE TABLE laps (
    lap_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id),
    lap_number      INTEGER NOT NULL,
    lap_time        REAL,                           -- Tempo da volta em segundos
    is_valid        INTEGER DEFAULT 1,              -- 0 = volta inválida (saiu da pista, etc.)
    fuel_at_start   REAL,                           -- Combustível no início da volta (litros)
    fuel_used       REAL,                           -- Combustível consumido na volta

    -- Temperaturas médias dos pneus (°C, convertidas de Kelvin)
    temp_fl_inner   REAL,  temp_fl_middle  REAL,  temp_fl_outer  REAL,
    temp_fr_inner   REAL,  temp_fr_middle  REAL,  temp_fr_outer  REAL,
    temp_rl_inner   REAL,  temp_rl_middle  REAL,  temp_rl_outer  REAL,
    temp_rr_inner   REAL,  temp_rr_middle  REAL,  temp_rr_outer  REAL,

    -- Pressões dos pneus (kPa)
    pressure_fl     REAL,  pressure_fr     REAL,
    pressure_rl     REAL,  pressure_rr     REAL,

    -- Desgaste dos pneus (0.0 = novo, 1.0 = careca)
    wear_fl         REAL,  wear_fr         REAL,
    wear_rl         REAL,  wear_rr         REAL,

    -- Carga nos pneus (N)
    load_fl         REAL,  load_fr         REAL,
    load_rl         REAL,  load_rr         REAL,

    -- Aerodinâmica e Suspensão
    ride_height_f   REAL,                           -- Ride height dianteiro (m)
    ride_height_r   REAL,                           -- Ride height traseiro (m)
    downforce_f     REAL,                           -- Downforce dianteiro (N)
    downforce_r     REAL,                           -- Downforce traseiro (N)
    max_speed       REAL,                           -- Velocidade máxima na volta (m/s)

    -- Pitch / Roll / Heave (médias da volta)
    avg_pitch       REAL,
    avg_roll        REAL,
    avg_heave       REAL,

    -- Freios
    max_brake_temp_fl REAL, max_brake_temp_fr REAL,
    max_brake_temp_rl REAL, max_brake_temp_rr REAL,

    -- Timestamp
    recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_laps_session ON laps(session_id);
CREATE INDEX idx_laps_time    ON laps(lap_time);

-- ============================================================
-- 6. TABELA: setup_snapshots (Snapshots do setup .svm)
-- ============================================================
-- Cada vez que um setup é carregado ou modificado, grava-se
-- um snapshot completo. Permite correlacionar setup ↔ performance.
CREATE TABLE setup_snapshots (
    snapshot_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id),
    applied_at_lap  INTEGER,                        -- A partir de qual volta vale este setup
    source          TEXT DEFAULT 'loaded',           -- "loaded", "ai_suggestion", "manual_edit"
    svm_filename    TEXT,                            -- Nome do arquivo .svm original

    -- Parâmetros CHAVE do setup (índices do .svm)
    rw_setting          INTEGER,                    -- Asa traseira
    spring_f            INTEGER,                    -- Mola dianteira
    spring_r            INTEGER,                    -- Mola traseira
    camber_fl           INTEGER,                    -- Camber FL
    camber_fr           INTEGER,                    -- Camber FR
    camber_rl           INTEGER,                    -- Camber RL
    camber_rr           INTEGER,                    -- Camber RR
    pressure_fl         INTEGER,                    -- Pressão pneu FL
    pressure_fr         INTEGER,                    -- Pressão pneu FR
    pressure_rl         INTEGER,                    -- Pressão pneu RL
    pressure_rr         INTEGER,                    -- Pressão pneu RR
    anti_sway_f         INTEGER,                    -- Barra anti-rolagem dianteira
    anti_sway_r         INTEGER,                    -- Barra anti-rolagem traseira
    ride_height_fl      INTEGER,
    ride_height_fr      INTEGER,
    ride_height_rl      INTEGER,
    ride_height_rr      INTEGER,
    slow_bump_fl        INTEGER,
    slow_bump_fr        INTEGER,
    slow_bump_rl        INTEGER,
    slow_bump_rr        INTEGER,
    slow_rebound_fl     INTEGER,
    slow_rebound_fr     INTEGER,
    slow_rebound_rl     INTEGER,
    slow_rebound_rr     INTEGER,
    fast_bump_fl        INTEGER,
    fast_bump_fr        INTEGER,
    fast_bump_rl        INTEGER,
    fast_bump_rr        INTEGER,
    fast_rebound_fl     INTEGER,
    fast_rebound_fr     INTEGER,
    fast_rebound_rl     INTEGER,
    fast_rebound_rr     INTEGER,
    brake_pressure      INTEGER,                    -- Pressão de freio geral
    rear_brake_bias     INTEGER,                    -- Distribuição de frenagem
    diff_preload        INTEGER,                    -- Pré-carga do diferencial
    toe_f               INTEGER,                    -- Toe dianteiro
    toe_r               INTEGER,                    -- Toe traseiro
    tc_map              INTEGER,                    -- Traction Control
    abs_map             INTEGER,                    -- ABS
    brake_duct_f        INTEGER,                    -- Duto de freio dianteiro
    brake_duct_r        INTEGER,                    -- Duto de freio traseiro
    fuel_setting        INTEGER,                    -- Combustível

    -- Arquivo .svm completo serializado (para restauração)
    svm_raw_content     TEXT,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snapshots_session ON setup_snapshots(session_id);

-- ============================================================
-- 7. TABELA: ai_suggestions (Sugestões feitas pela IA)
-- ============================================================
-- Registra CADA sugestão da IA, o que foi aceito/rejeitado,
-- e o resultado. Essencial para o ciclo de aprendizado.
CREATE TABLE ai_suggestions (
    suggestion_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(session_id),
    after_lap       INTEGER NOT NULL,               -- Sugestão feita após qual volta
    source          TEXT DEFAULT 'neural_net',       -- "neural_net", "heuristic", "mixed"

    -- Deltas sugeridos (saída da IA)
    delta_rw            REAL,
    delta_spring_f      REAL,
    delta_spring_r      REAL,
    delta_camber_f      REAL,
    delta_camber_r      REAL,
    delta_pressure_f    REAL,
    delta_pressure_r    REAL,
    delta_brake_press   REAL,
    delta_arb_f         REAL,
    delta_arb_r         REAL,

    -- Explicação em linguagem natural gerada pela IA
    explanation_text    TEXT,

    -- Feedback do usuário
    user_accepted       INTEGER,                    -- 1 = aceito, 0 = rejeitado, NULL = pendente
    user_feedback_bias  REAL,                       -- -1.0 understeer ... +1.0 oversteer
    user_confidence     REAL,                       -- 0.0 a 1.0

    -- Resultado medido (preenchido após as próximas voltas)
    lap_time_before     REAL,                       -- Média das 3 voltas ANTES
    lap_time_after      REAL,                       -- Média das 3 voltas DEPOIS
    improvement_pct     REAL,                       -- % de melhoria (calculado)

    -- Reward final calculado (usado no treinamento)
    reward_score        REAL,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_suggestions_session ON ai_suggestions(session_id);

-- ============================================================
-- 8. TABELA: training_data (Dataset de treinamento da IA)
-- ============================================================
-- Dados prontos para alimentar a rede neural. Cada linha = 1
-- exemplo de treinamento (input features + output labels + reward).
-- Pré-processado e normalizado.
CREATE TABLE training_data (
    data_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(session_id),
    car_id          INTEGER REFERENCES cars(car_id),
    track_id        INTEGER REFERENCES tracks(track_id),

    -- Input features (normalizadas entre 0 e 1)
    input_vector    BLOB NOT NULL,                  -- numpy array serializado (float32)
                                                    -- Contém: temps, pressures, wear, load,
                                                    -- ride_height, downforce, pitch, roll,
                                                    -- heave, speed, fuel, feedbacks

    -- Output labels (deltas que foram de fato aplicados)
    output_vector   BLOB NOT NULL,                  -- numpy array serializado (float32)

    -- Reward obtido após aplicar esses deltas
    reward          REAL NOT NULL,

    -- Qualidade do dado (peso no treinamento)
    weight          REAL DEFAULT 1.0,               -- Dados com reward alto = peso maior
    is_valid        INTEGER DEFAULT 1,              -- 0 = dado corrompido ou outlier

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_training_car_track ON training_data(car_id, track_id);

-- ============================================================
-- 9. TABELA: heuristic_log (Log de regras heurísticas aplicadas)
-- ============================================================
-- Registra quando uma regra heurística foi ativada, para que a
-- IA aprenda quais regras são eficazes e quais nem tanto.
CREATE TABLE heuristic_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(session_id),
    after_lap       INTEGER,
    rule_name       TEXT NOT NULL,                   -- Ex: "camber_inner_hot"
    rule_condition  TEXT,                            -- Ex: "temp_inner > temp_outer + 10"
    suggestion_text TEXT,                            -- Ex: "Reduzir camber negativo"
    delta_applied   TEXT,                            -- JSON: {"camber_f": +0.2}
    was_effective   INTEGER,                         -- 1 = melhorou, 0 = não, NULL = desconhecido
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 10. TABELA: model_checkpoints (Versões do modelo IA)
-- ============================================================
-- Cada vez que a IA salva um .pth, registra aqui.
-- Permite rollback para versões anteriores do modelo.
CREATE TABLE model_checkpoints (
    checkpoint_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id          INTEGER REFERENCES cars(car_id),
    track_id        INTEGER REFERENCES tracks(track_id),
    filename        TEXT NOT NULL,                   -- Ex: "models/toyota_lemans_v12.pth"
    epoch           INTEGER,                        -- Número de épocas treinadas
    total_samples   INTEGER,                        -- Quantos exemplos de treinamento usou
    avg_reward      REAL,                           -- Reward médio no treinamento
    best_lap_time   REAL,                           -- Melhor volta alcançada com este modelo
    is_active       INTEGER DEFAULT 1,              -- 1 = modelo atual em uso
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 11. TABELA: track_map_points (Mapa da pista construído)
-- ============================================================
-- Posições X/Z coletadas para desenhar o mapa da pista.
-- Armazenado separado para não poluir a tabela laps.
CREATE TABLE track_map_points (
    point_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id        INTEGER NOT NULL REFERENCES tracks(track_id),
    lap_id          INTEGER REFERENCES laps(lap_id),
    pos_x           REAL NOT NULL,
    pos_z           REAL NOT NULL,
    speed           REAL,                           -- m/s naquele ponto
    brake_applied   INTEGER DEFAULT 0,              -- 1 = freio pressionado
    throttle        REAL,                           -- 0.0 a 1.0
    gear            INTEGER,
    sector          INTEGER,                        -- Setor da pista
    distance_pct    REAL                            -- 0.0 a 1.0 (% da volta)
);

CREATE INDEX idx_map_track ON track_map_points(track_id);

-- ============================================================
-- 12. VIEW: v_training_summary (Resumo para dashboard)
-- ============================================================
CREATE VIEW v_training_summary AS
SELECT
    c.car_name,
    t.track_name,
    COUNT(td.data_id) AS total_samples,
    AVG(td.reward) AS avg_reward,
    MAX(s.best_lap_time) AS best_lap,
    COUNT(DISTINCT s.session_id) AS total_sessions,
    MAX(td.created_at) AS last_trained
FROM training_data td
JOIN sessions s ON td.session_id = s.session_id
JOIN cars c ON td.car_id = c.car_id
JOIN tracks t ON td.track_id = t.track_id
WHERE td.is_valid = 1
GROUP BY c.car_name, t.track_name;

-- ============================================================
-- 13. VIEW: v_suggestion_effectiveness (Eficácia das sugestões)
-- ============================================================
CREATE VIEW v_suggestion_effectiveness AS
SELECT
    source,
    COUNT(*) AS total_suggestions,
    SUM(CASE WHEN user_accepted = 1 THEN 1 ELSE 0 END) AS accepted,
    SUM(CASE WHEN improvement_pct > 0 THEN 1 ELSE 0 END) AS improved,
    AVG(improvement_pct) AS avg_improvement_pct,
    AVG(reward_score) AS avg_reward
FROM ai_suggestions
WHERE user_accepted IS NOT NULL
GROUP BY source;
```

### 20.3 Diagrama de Relacionamentos (ER)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│driver_profiles│     │    cars      │     │     tracks       │
│──────────────│     │──────────────│     │──────────────────│
│ driver_id PK │     │ car_id PK    │     │ track_id PK      │
│ driver_name  │     │ car_name     │     │ track_name       │
│ skill_level  │     │ car_class    │     │ folder_name      │
│ aggression   │     │ drivetrain   │     │ track_length_m   │
└──────┬───────┘     └──────┬───────┘     └────────┬─────────┘
       │                    │                      │
       │    ┌───────────────┼──────────────────────┘
       │    │               │
       ▼    ▼               ▼
    ┌───────────────────────────┐
    │        sessions           │
    │───────────────────────────│
    │ session_id PK             │
    │ driver_id FK              │
    │ car_id FK                 │
    │ track_id FK               │
    │ session_type              │
    │ weather                   │
    └─────────┬─────────────────┘
              │
     ┌────────┼────────────────────────┐
     │        │                        │
     ▼        ▼                        ▼
┌─────────┐ ┌──────────────────┐ ┌───────────────┐
│  laps   │ │ setup_snapshots  │ │ai_suggestions │
│─────────│ │──────────────────│ │───────────────│
│ lap_id  │ │ snapshot_id      │ │suggestion_id  │
│ temps   │ │ all svm params   │ │ deltas        │
│ pressures│ │ svm_raw_content  │ │ feedback      │
│ wear    │ │ source           │ │ reward_score  │
│ load    │ └──────────────────┘ └───────────────┘
│ aero    │
└─────────┘
     │
     ▼
┌──────────────────┐     ┌──────────────────────┐
│ track_map_points │     │   training_data      │
│──────────────────│     │──────────────────────│
│ pos_x, pos_z    │     │ input_vector (BLOB)  │
│ speed, brake    │     │ output_vector (BLOB) │
│ throttle, gear  │     │ reward               │
└──────────────────┘     └──────────────────────┘
```

### 20.4 Estimativa de Tamanho do Banco

| Cenário | Voltas | Tamanho Estimado |
|---------|:------:|:----------------:|
| 1 sessão (50 voltas) | 50 | ~200 KB |
| 1 mês de uso moderado | ~2.000 | ~8 MB |
| 1 ano de uso intenso | ~20.000 | ~80 MB |
| Com track_map_points (alta freq.) | +500K pontos | ~150 MB |

**SQLite suporta até 281 TB.** Performance não será problema.

---

## 21. JANELA PYTHON — GERENCIADOR DO BANCO DE DADOS

### 21.1 Design da Janela (CustomTkinter)

Nova aba `[Banco de Dados]` na GUI principal, **ou** janela separada acessível pelo menu.

**Recomendação:** Aba integrada na janela principal (mais coeso).

```
┌─────────────────────────────────────────────────────────────────────┐
│  LMU Virtual Engineer                                    [─] [□] [×]│
├──────────┬──────────┬────────────┬──────────┬───────────────────────┤
│Telemetria│  Ajuste  │Diagnóstico │ Arquivos │  📊 Banco de Dados   │
├──────────┴──────────┴────────────┴──────────┴───────────────────────┤
│                                                                     │
│  ┌─── Filtros ────────────────────────────────────────────────────┐ │
│  │ Carro: [▼ Toyota GR010 Hybrid     ] Pista: [▼ Le Mans (24h) ] │ │
│  │ Sessão: [▼ Todas                  ] Tipo:  [▼ Practice      ] │ │
│  │ Período: [01/03/2026] até [31/03/2026]  [🔍 Filtrar]         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Resumo Rápido ─────────────────────────────────────────────┐ │
│  │  📊 1.247 voltas gravadas │ 🏎️ 5 carros │ 🏁 8 pistas        │ │
│  │  🧠 324 exemplos de treino│ 💡 87 sugestões (72% aceitas)     │ │
│  │  📈 Melhoria média: -0.8s │ 🏆 Melhor: 3:24.112 (Le Mans)    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Tabela de Sessões ─────────────────────────────────────────┐ │
│  │ # │ Data       │ Carro         │ Pista     │ Voltas│ Melhor   │ │
│  │───┼────────────┼───────────────┼───────────┼───────┼──────────│ │
│  │ 1 │ 31/03/2026 │ Toyota GR010  │ Le Mans   │  42   │ 3:24.1  │ │
│  │ 2 │ 30/03/2026 │ Porsche 963   │ Spa       │  38   │ 2:01.3  │ │
│  │ 3 │ 29/03/2026 │ Toyota GR010  │ Le Mans   │  55   │ 3:25.8  │ │
│  │ 4 │ 28/03/2026 │ Cadillac V-LMDh│ Monza    │  31   │ 1:34.2  │ │
│  │ 5 │ 27/03/2026 │ Ferrari 499P  │ Bahrain   │  47   │ 1:48.7  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Detalhes da Sessão Selecionada ────────────────────────────┐ │
│  │                                                                │ │
│  │  [📈 Gráfico:  Evolução lap times]                            │ │
│  │                                                                │ │
│  │   3:28 ─ ●                                                    │ │
│  │   3:27 ─    ●  ●                                              │ │
│  │   3:26 ─       ●  ●  ●                                       │ │
│  │   3:25 ─              ●  ●  ●  ●                              │ │
│  │   3:24 ─                       ●  ●  ●                        │ │
│  │         └──────────────────────────────                        │ │
│  │          1  5  10  15  20  25  30  35  40  (voltas)            │ │
│  │                                                                │ │
│  │  💡 Sugestões aplicadas nesta sessão: 3                       │ │
│  │  ✅ Aceitas: 2  │  ❌ Rejeitadas: 1  │  📈 Melhoria: -1.2s   │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Ações ─────────────────────────────────────────────────────┐ │
│  │ [📤 Exportar CSV] [📤 Exportar JSON] [🗑️ Limpar Sessão]     │ │
│  │ [🔄 Retreinar IA com dados selecionados]                      │ │
│  │ [💾 Backup do Banco]  [📥 Importar Banco]                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Status: 🟢 Conectado ao banco │ lmu_engineer.db (8.4 MB)         │
└─────────────────────────────────────────────────────────────────────┘
```

### 21.2 Sub-janela: Visualização de Treinamento da IA

Acessível via botão "🔄 Retreinar IA" ou aba `[Aprendizado]`:

```
┌─────────────────────────────────────────────────────────────────────┐
│  🧠 Painel de Treinamento da IA                         [─] [□] [×]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── Modelo Atual ──────────────────────────────────────────────┐ │
│  │  Combo: Toyota GR010 @ Le Mans                                │ │
│  │  Arquivo: models/toyota_lemans_v12.pth                        │ │
│  │  Épocas treinadas: 120  │  Amostras: 324  │  Reward: 0.73    │ │
│  │  Última atualização: 31/03/2026 14:32                         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Progresso do Treinamento ──────────────────────────────────┐ │
│  │                                                                │ │
│  │  Loss:    ████████████████░░░░ 0.034 (↓ melhorando)           │ │
│  │  Reward:  █████████████████░░░ 0.73  (↑ subindo)              │ │
│  │  Época:   ████████████░░░░░░░░ 120/200                        │ │
│  │                                                                │ │
│  │  [📈 Gráfico Loss vs Épocas]                                  │ │
│  │                                                                │ │
│  │   0.15 ─ ●                                                    │ │
│  │   0.10 ─    ●●                                                │ │
│  │   0.05 ─       ●●●●●                                         │ │
│  │   0.03 ─              ●●●●●●●●●●●●                            │ │
│  │         └──────────────────────────────                        │ │
│  │          0    20   40   60   80  100  120 (épocas)             │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── Diagnóstico da IA ─────────────────────────────────────────┐ │
│  │                                                                │ │
│  │  Confiança do modelo:  ███████░░░ 72% (precisa mais dados)    │ │
│  │  Dados suficientes?    ⚠️ Mínimo 500 amostras (faltam 176)   │ │
│  │  Overfitting?          ✅ Não detectado                       │ │
│  │  Heurísticas ativas?   ✅ Sim (modelo < 80% confiança)       │ │
│  │                                                                │ │
│  │  Pesos mais influentes:                                       │ │
│  │  1. 🔥 Temp pneus → Camber    (peso: 0.89)                   │ │
│  │  2. 🔥 Ride height → Molas    (peso: 0.76)                   │ │
│  │  3. 📊 Feedback user → Asa    (peso: 0.65)                   │ │
│  │  4. 📊 Downforce → Pressão    (peso: 0.52)                   │ │
│  │  5. 📊 Desgaste → ARB         (peso: 0.41)                   │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  [▶️ Treinar Agora] [⏸️ Pausar] [🔄 Reset Modelo] [💾 Salvar .pth]│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 21.3 Estrutura do Código da GUI do Banco de Dados

```python
# gui/tab_database.py — Estrutura proposta

class DatabaseTab(ctk.CTkFrame):
    """Aba de gerenciamento do banco de dados."""

    def __init__(self, parent, db_manager):
        # Componentes principais:
        # - FilterFrame: filtros de carro, pista, período
        # - SummaryFrame: cards com métricas rápidas
        # - SessionTable: tabela com CTkScrollableFrame
        # - DetailFrame: gráfico de evolução (matplotlib embed)
        # - ActionBar: botões de exportação/backup/retreino

    def load_sessions(self, filters: dict):
        """Carrega sessões do banco com filtros aplicados."""

    def show_session_detail(self, session_id: int):
        """Mostra detalhes e gráfico de uma sessão específica."""

    def export_csv(self):
        """Exporta dados filtrados para CSV."""

    def export_json(self):
        """Exporta insights (pesos médios) para JSON compartilhável."""

    def backup_database(self):
        """Copia lmu_engineer.db para pasta de backups com timestamp."""

    def trigger_retrain(self):
        """Abre sub-janela de treinamento com dados selecionados."""
```

---

## 22. PIPELINE DE APRENDIZADO — FLUXO COMPLETO DE DADOS

### 22.1 Diagrama do Ciclo de Aprendizado
```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                    CICLO DE APRENDIZADO COMPLETO                    │
 │                                                                     │
 │   ╔══════════════╗                                                  │
 │   ║  LMU RODANDO ║                                                  │
 │   ╚══════╤═══════╝                                                  │
 │          │                                                          │
 │          │ Shared Memory (mmap) — ~60Hz                             │
 │          ▼                                                          │
 │   ┌──────────────────┐                                              │
 │   │ telemetry_reader  │   Thread dedicada lendo dados               │
 │   │ (adapter/)        │   a cada ~100ms (10 Hz é suficiente)        │
 │   └────────┬─────────┘                                              │
 │            │                                                        │
 │            │  Dados brutos: temps, pressões, velocidade, posição    │
 │            │                                                        │
 │            ▼                                                        │
 │   ┌───────────────────┐          ┌────────────────────┐             │
 │   │   ACUMULADOR       │         │    normalizer.py    │             │
 │   │  (por volta)       │────────▶│  Normaliza inputs   │             │
 │   │                    │         │  StandardScaler     │             │
 │   │ Calcula médias,    │         └────────┬───────────┘             │
 │   │ máximos, mínimos   │                  │                         │
 │   │ ao final de cada   │                  │ Vetor normalizado       │
 │   │ volta completada   │                  │ (38-42 floats)          │
 │   └────────┬───────────┘                  │                         │
 │            │                              ▼                         │
 │            │                     ┌────────────────────┐             │
 │            │ Salva no banco ───▶ │     SQLite DB       │             │
 │            │ (tabela: laps)      │  (lmu_engineer.db)  │             │
 │            │                     └────────┬───────────┘             │
 │            │                              │                         │
 │            ▼                              │ training_data           │
 │   ┌────────────────────┐                  │                         │
 │   │  FASE APRENDIZADO? │                  │                         │
 │   │  (< 5-10 voltas)   │                  │                         │
 │   └───┬────────┬───────┘                  │                         │
 │       │SIM     │NÃO (dados suficientes)   │                         │
 │       ▼        ▼                          │                         │
 │  ┌──────────┐ ┌────────────────┐          │                         │
 │  │Heurísticas│ │  brain.py      │◀─────────┘                        │
 │  │  SOMENTE  │ │  (PyTorch NN)  │                                   │
 │  │           │ │                │    Carrega pesos do                │
 │  │ Regras    │ │  forward() →   │    último checkpoint               │
 │  │ de enge-  │ │  gera deltas   │    (tabela: model_checkpoints)     │
 │  │ nharia    │ │                │                                    │
 │  └─────┬─────┘ └───────┬───────┘                                   │
 │        │               │                                            │
 │        └───────┬───────┘                                            │
 │                │  Sugestão: deltas + explicação                     │
 │                ▼                                                    │
 │   ┌─────────────────────────┐                                       │
 │   │   gui/tab_adjustment    │                                       │
 │   │                         │                                       │
 │   │  "Sugestão da IA:"      │                                       │
 │   │  • Asa traseira: +1     │                                       │
 │   │  • Camber F: -0.2°      │                                       │
 │   │  • Mola T: +2 clicks    │                                       │
 │   │                         │                                       │
 │   │  Feedback: [──●──────]  │  ◀── Slider: understeer ↔ oversteer  │
 │   │  Confiança: [████░░] 7  │                                       │
 │   │                         │                                       │
 │   │  [✅ Aceitar] [❌ Rejeitar] [✏️ Modificar]                      │
 │   └──────────┬──────────────┘                                       │
 │              │                                                      │
 │              │  Salva no banco (tabela: ai_suggestions)             │
 │              │  + (tabela: setup_snapshots)                         │
 │              ▼                                                      │
 │   ┌──────────────────────┐                                          │
 │   │  USUÁRIO APLICA NO   │                                          │
 │   │  JOGO (via .svm ou   │                                          │
 │   │  menu do jogo)       │                                          │
 │   └──────────┬───────────┘                                          │
 │              │                                                      │
 │              │  Próximas 3-5 voltas...                              │
 │              ▼                                                      │
 │   ┌──────────────────────┐                                          │
 │   │    reward.py          │                                         │
 │   │                       │                                         │
 │   │  Reward = Σ(critérios │                                         │
 │   │    ponderados)        │                                         │
 │   │                       │                                         │
 │   │  Critérios:           │ ◀── Compara ANTES vs DEPOIS             │
 │   │  • ΔLapTime (40%)     │                                         │
 │   │  • ΔTempBalance (20%) │                                         │
 │   │  • ΔGrip (15%)        │                                         │
 │   │  • ΔConsistência (15%)│                                         │
 │   │  • UserFeedback (10%) │                                         │
 │   └──────────┬────────────┘                                         │
 │              │                                                      │
 │              │  reward_score → salva no banco                       │
 │              │  (tabela: ai_suggestions.reward_score)               │
 │              │  (tabela: training_data)                              │
 │              ▼                                                      │
 │   ┌──────────────────────┐                                          │
 │   │    trainer.py         │                                         │
 │   │                       │                                         │
 │   │  1. Carrega batch do  │ ◀── Busca N exemplos do banco           │
 │   │     training_data     │     (prioriza reward alto)              │
 │   │                       │                                         │
 │   │  2. Forward pass:     │                                         │
 │   │     pred = model(x)   │                                         │
 │   │                       │                                         │
 │   │  3. Loss customizada: │                                         │
 │   │     loss = MSE(pred,  │                                         │
 │   │       actual_delta)   │                                         │
 │   │     × reward_weight   │ ◀── Reward alto = aprende MAIS          │
 │   │                       │     Reward baixo = aprende MENOS        │
 │   │  4. Backpropagation:  │                                         │
 │   │     loss.backward()   │                                         │
 │   │     optimizer.step()  │                                         │
 │   │                       │                                         │
 │   │  5. Salva checkpoint  │ ──▶ models/car_track_vN.pth            │
 │   │     no banco          │     + tabela: model_checkpoints         │
 │   └──────────────────────┘                                          │
 │              │                                                      │
 │              ▼                                                      │
 │         VOLTA AO INÍCIO                                             │
 │         (próxima volta do jogo)                                     │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

### 22.2 Quando o Treinamento Acontece?

| Modo | Quando | Como |
|------|--------|------|
| **Online (durante o jogo)** | A cada 5 voltas completadas | Mini-batch de 16 exemplos, ~50ms de treino (CPU). Imperceptível para o usuário. |
| **Offline (pós-sessão)** | Quando o usuário clica "Retreinar" | Treina com TODOS os dados do banco por N épocas. Pode levar 5-30 segundos. |
| **Importação** | Ao importar telemetria gravada | Processa arquivos da pasta `UserData\Telemetry\` e cria training_data. |
| **Frio (primeira vez)** | Ao iniciar com banco vazio | Só heurísticas. IA desligada até ter ≥ 30 amostras de treinamento. |

### 22.3 Fórmula de Loss Ponderada por Reward

```
                   ┌──────────────────────────────────────────┐
                   │         LOSS PONDERADA (Reward-Weighted) │
                   │                                          │
                   │  Para cada exemplo i no batch:           │
                   │                                          │
                   │    predicted_i = model(input_i)          │
                   │    target_i   = actual_delta_aplicado_i  │
                   │    reward_i   = reward obtido (0 a 1)    │
                   │                                          │
                   │    loss_i = MSE(predicted_i, target_i)   │
                   │             × weight_i                   │
                   │                                          │
                   │  Onde weight_i:                          │
                   │    Se reward_i > 0  → weight = reward_i  │
                   │    (reforça: "aprenda a repetir isso")   │
                   │                                          │
                   │    Se reward_i < 0  → weight = |reward|  │
                   │    target_i = -actual_delta_i            │
                   │    (penaliza: "aprenda a fazer oposto")  │
                   │                                          │
                   │    Se reward_i ≈ 0  → weight = 0.1       │
                   │    (ignora: "não aprende muito")         │
                   │                                          │
                   │  Loss_total = Σ(loss_i) / batch_size     │
                   └──────────────────────────────────────────┘
```

### 22.4 Critérios de Confiança do Modelo

A IA NÃO é usada sozinha até que o modelo tenha **confiança suficiente**:

| Dados de Treino | Confiança | Comportamento |
|:---------------:|:---------:|---------------|
| 0 – 29 amostras | 0% | ❌ Só heurísticas. IA desligada. |
| 30 – 99 amostras | 20-40% | ⚠️ Heurísticas primárias + IA como "segunda opinião" |
| 100 – 299 amostras | 40-70% | 📊 IA e heurísticas com peso igual. Mostra ambas. |
| 300 – 499 amostras | 70-85% | 🧠 IA primária. Heurísticas só validam (veta se absurdo). |
| 500+ amostras | 85-95% | ✅ IA confiável. Heurísticas só como safety check. |

**Nota:** A confiança nunca chega a 100% — sempre há margem para surpresas.

### 22.5 Proteções de Segurança (Safety Guards)

```
┌─────────────────────────────────────────────────────────────┐
│  SAFETY GUARDS — A IA NUNCA pode sugerir:                   │
│                                                             │
│  1. Delta > ±3 índices de uma vez (muito agressivo)         │
│     → Limita automaticamente e avisa o usuário              │
│                                                             │
│  2. Valores fora do range do parâmetro                      │
│     → Clipa para min/max do .svm                            │
│                                                             │
│  3. Combinações perigosas conhecidas:                       │
│     → Camber extremo + pressão baixa (risco de pneu)       │
│     → Ride height mínimo + mola dura (batida no chão)      │
│     → Asa zero + diff solto (instabilidade grave)           │
│                                                             │
│  4. Mudanças em parâmetros marcados "Non-adjustable"        │
│     → Parser ignora automaticamente                         │
│                                                             │
│  5. Se reward médio das últimas 5 sugestões < -0.5:         │
│     → Auto-reset para heurísticas e avisa o usuário:        │
│     "A IA está com dificuldade. Voltando para regras        │
│      de engenharia enquanto coleta mais dados."             │
└─────────────────────────────────────────────────────────────┘
```

---

## 23. ARQUITETURA REVISADA (v3) — COM BANCO DE DADOS

```
LMU_Virtual_Engineer/
│
├── main.py
├── requirements.txt
├── config.py
├── setup_wizard.py
│
├── core/
│   ├── __init__.py
│   ├── brain.py                     # SetupNeuralNet (PyTorch)
│   ├── trainer.py                   # Loop de treinamento + loss ponderada
│   ├── heuristics.py                # Regras determinísticas
│   ├── diagnostics.py               # Perguntas interativas
│   ├── driver_profile.py            # Perfil do piloto
│   ├── normalizer.py                # StandardScaler
│   ├── reward.py                    # Reward composto multi-critério
│   └── safety.py                    # 🆕 Safety Guards (limites e validações)
│
├── data/
│   ├── __init__.py
│   ├── database.py                  # 🆕 DatabaseManager (SQLite + WAL)
│   ├── schema.sql                   # 🆕 Schema completo (Seção 20.2)
│   ├── telemetry_reader.py          # Wrapper sobre adapter/
│   ├── telemetry_importer.py        # Importar UserData\Telemetry\
│   ├── svm_parser.py                # Parser .svm
│   ├── track_mapper.py              # Mapa da pista
│   └── export.py                    # JSON + CSV export
│
├── gui/
│   ├── __init__.py
│   ├── app.py                       # Janela principal CustomTkinter
│   ├── tab_telemetry.py             # [Telemetria]
│   ├── tab_adjustment.py            # [Ajuste]
│   ├── tab_diagnostic.py            # [Diagnóstico]
│   ├── tab_files.py                 # [Arquivos .svm]
│   ├── tab_database.py              # 🆕 [Banco de Dados] (Seção 21)
│   ├── tab_training.py              # 🆕 [Treinamento IA] (Seção 21.2)
│   └── widgets.py                   # Componentes reutilizáveis
│
├── adapter/                         # ← JÁ EXISTE
├── pyRfactor2SharedMemory/          # ← JÁ EXISTE
│
├── db/                              # 🆕 Banco de dados
│   └── lmu_engineer.db              # Arquivo SQLite (criado automaticamente)
│
├── models/                          # Pesos .pth
├── profiles/                        # Perfis de pilotos
├── backups/                         # Backups .svm + .db
└── logs/                            # Logs de execução
```

### Novas Dependências:

```
# Adicionar ao requirements.txt
matplotlib>=3.7.0          # Gráficos na GUI (evolução lap times, loss)
```

**Nota:** `sqlite3` já é built-in do Python. Não precisa instalar nada.

---

## 24. PONTOS DE DECISÃO — BANCO DE DADOS (v3)

### ❓ Pergunta 7: Frequência de Gravação de Telemetria
- **Opção A:** Gravar dados resumidos **por volta** (1 linha por volta na tabela `laps`) — **recomendado**
- **Opção B:** Gravar dados **por amostra** (~10Hz = 600 linhas/minuto) — muito mais dados, banco cresce rápido
- **Opção C:** Ambos (resumo por volta + alta frequência para track_map_points) — **mais completo**

### ❓ Pergunta 8: Backup Automático do Banco
- **Opção A:** Backup automático ao abrir o programa (copia `lmu_engineer.db`)
- **Opção B:** Backup manual (botão na GUI)
- **Opção C:** Ambos — auto no início + botão manual — **recomendado**

### ❓ Pergunta 9: Compartilhamento entre Usuários
- **Opção A:** Exportar/importar **apenas insights** (JSON leve com pesos médios)
- **Opção B:** Exportar/importar **training_data** (dataset completo para retreinar)
- **Opção C:** Exportar/importar **banco completo** (copia o .db inteiro)
- **Opção D:** Todas as opções acima — **recomendado**

---

## 25. CONCLUSÃO REVISADA (v3)

| Critério | v1 | v2 | v3 (com BD) |
|----------|:--:|:--:|:-----------:|
| Viabilidade técnica | ✅ | ✅ | ✅ Mantém viável |
| Escopo | Médio | Alto | 🔺 **Muito Alto** |
| Robustez dos dados | Baixa (sem persistência) | Média (SQLite mencionado) | 🔺 **Alta** (schema completo) |
| Rastreabilidade | ❌ | ⚠️ | ✅ **Total** (cada sugestão registrada) |
| Retreinamento | ❌ | ⚠️ | ✅ **Completo** (training_data organizado) |
| Debug/Análise | ❌ | ⚠️ | ✅ **Fácil** (views SQL + gráficos) |

**Veredicto: ✅ VIÁVEL — escopo significativo mas cada módulo é bem definido.**

O banco de dados SQLite é a **espinha dorsal** que conecta todos os módulos. Sem ele, a IA não teria memória persistente — seria como treinar do zero a cada sessão.

**Fases Revisadas:**

| Fase | Escopo | Inclui BD? |
|------|--------|:----------:|
| **Fase 1 (MVP)** | Schema básico (cars, tracks, sessions, laps, setup_snapshots) + telemetry_reader + brain.py (básico 8 outputs) + heurísticas + GUI (4 abas) | ✅ Parcial |
| **Fase 2 (Completo)** | ai_suggestions + training_data + model_checkpoints + tab_database + tab_training + safety guards + perguntas interativas + mapa + níveis interm./avançado | ✅ Completo |
| **Fase 3 (Social)** | Export/import entre usuários + servidor de compartilhamento + ranking de setups | ✅ Estendido |

---

## 26. SUPORTE MULTI-CARRO E MULTI-CATEGORIA — DESIGN COMPLETO

### 26.1 Categorias e Carros do Le Mans Ultimate

O LMU possui **múltiplas categorias** com características RADICALMENTE diferentes. A IA **não pode** usar o mesmo modelo treinado para todos:

| Categoria | Carros Conhecidos | Características | Impacto no Setup |
|-----------|-------------------|-----------------|------------------|
| **Hypercar** | Toyota GR010, Porsche 963, Ferrari 499P, Cadillac V-LMDh, Peugeot 9X8, BMW M Hybrid V8, Alpine A424 | Hybrid/ICE, ~700hp, ~1000kg, Aero alto, AWD/RWD | Downforce extremo, gestão de energia, freio regenerativo |
| **LMP2** | Oreca 07 Gibson | ~600hp, ~930kg, ICE puro, RWD, aero alto | Pneus degradam mais rápido, sem hybrid, aero sensível |
| **LMGT3** | Corvette Z06 GT3.R, Ferrari 296 GT3, Porsche 911 GT3 R, BMW M4 GT3, Aston Martin Vantage GT3, McLaren 720S GT3, Lamborghini Huracán GT3 | ~550hp, ~1300kg, ICE, RWD, aero baixo/médio | BoP (Balance of Performance), foco em mecânico, menos aero |

### 26.2 Por que a IA PRECISA separar por carro?

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PROBLEMA: Usar UM modelo para todos os carros                         │
│                                                                         │
│  Toyota GR010 (Hypercar AWD Hybrid):                                   │
│    • Camber ideal dianteiro: ~ -3.0°                                   │
│    • Asa traseira ideal Le Mans: ~ 5-6°                                │
│    • Pressão pneu ideal: ~ 130-140 kPa                                │
│    • Freio regenerativo afeta bias                                     │
│                                                                         │
│  Corvette Z06 GT3.R (GT3 RWD ICE):                                    │
│    • Camber ideal dianteiro: ~ -2.0°                                   │
│    • Asa traseira ideal Le Mans: ~ 3-4°                                │
│    • Pressão pneu ideal: ~ 160-175 kPa                                │
│    • Sem regen, freio 100% mecânico                                    │
│                                                                         │
│  ❌ Se misturar os dados: a IA sugere valores MÉDIOS que são           │
│     RUINS para AMBOS os carros. Nunca converge.                        │
│                                                                         │
│  ✅ Separando por carro: cada modelo aprende os padrões ESPECÍFICOS     │
│     daquele carro. Convergência 5-10x mais rápida.                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 26.3 Arquitetura de Modelos por Carro+Pista

Cada combinação **carro × pista** tem seu PRÓPRIO modelo de IA e seus próprios dados de treino:

```
models/
│
├── hypercar/
│   ├── toyota_gr010/
│   │   ├── le_mans_24h.pth            # Toyota @ Le Mans
│   │   ├── le_mans_24h_scaler.pkl     # Normalizador desse combo
│   │   ├── spa_francorchamps.pth      # Toyota @ Spa
│   │   └── spa_francorchamps_scaler.pkl
│   ├── porsche_963/
│   │   ├── le_mans_24h.pth
│   │   └── monza.pth
│   ├── ferrari_499p/
│   └── cadillac_vlmdh/
│
├── lmp2/
│   └── oreca_07/
│       ├── le_mans_24h.pth
│       └── bahrain.pth
│
├── lmgt3/
│   ├── corvette_z06_gt3r/
│   │   ├── le_mans_24h.pth
│   │   └── portimao.pth
│   ├── ferrari_296_gt3/
│   ├── porsche_911_gt3r/
│   └── bmw_m4_gt3/
│
└── _shared/
    ├── hypercar_base.pth              # Modelo base compartilhado (Transfer Learning)
    ├── lmp2_base.pth
    └── lmgt3_base.pth
```

### 26.4 Transfer Learning entre Carros da Mesma Categoria

Quando o usuário usa um carro **novo** (sem dados), a IA pode **transferir conhecimento** de carros similares da mesma categoria:

```
┌──────────────────────────────────────────────────────────────────┐
│              TRANSFER LEARNING POR CATEGORIA                     │
│                                                                  │
│  Cenário: Usuário começa a usar o BMW M Hybrid V8 (Hypercar)    │
│           pela primeira vez. Zero dados.                         │
│                                                                  │
│  Sem Transfer Learning:                                          │
│  ┌──────────────────────────────────────┐                        │
│  │  BMW M Hybrid V8 @ Le Mans           │                        │
│  │  Dados: 0 voltas                     │                        │
│  │  Confiança: 0%                       │                        │
│  │  → Só heurísticas (genéricas)        │                        │
│  └──────────────────────────────────────┘                        │
│                                                                  │
│  Com Transfer Learning:                                          │
│  ┌──────────────────────────────────────┐                        │
│  │  BMW M Hybrid V8 @ Le Mans           │                        │
│  │  Base: hypercar_base.pth             │ ← Média ponderada     │
│  │  Fontes: Toyota (200 voltas, 40%)    │    dos modelos da      │
│  │          Porsche (150 voltas, 30%)   │    mesma categoria     │
│  │          Ferrari (120 voltas, 25%)   │                        │
│  │          Cadillac (30 voltas, 5%)    │                        │
│  │  Confiança inicial: ~35%             │                        │
│  │  → IA já sugere algo razoável!       │                        │
│  └──────────────────────────────────────┘                        │
│                                                                  │
│  Processo:                                                       │
│  1. Calcula pesos médios de TODOS os Hypercars no banco          │
│  2. Cria um modelo base (_shared/hypercar_base.pth)              │
│  3. Fine-tune com as primeiras voltas do BMW                     │
│  4. Gradualmente, o modelo BMW diverge do base                   │
│     (pega as peculiaridades do carro)                            │
└──────────────────────────────────────────────────────────────────┘
```

### 26.5 Detecção Automática de Carro e Pista

A IA precisa saber **automaticamente** qual carro e pista estão em uso, sem o usuário precisar dizer:

```python
# Dados disponíveis na Shared Memory (rF2ScoringVehicle):
# - mVehicleName  → Nome do carro (ex: "Toyota GR010 Hybrid #7")
# - mVehicleClass → Classe (ex: "Hypercar")
# - mTrackName    → Nome da pista (ex: "le_mans_24h")

# Fluxo de detecção automática:
#
#  1. Ler mVehicleName + mVehicleClass + mTrackName da Shared Memory
#  2. Buscar no banco (tabela cars) se já existe
#  3. Se NÃO existe → criar novo registro automaticamente
#  4. Carregar o modelo .pth correto (car_id + track_id)
#  5. Se modelo não existe → tentar Transfer Learning da categoria
#  6. Se categoria não tem dados → iniciar com heurísticas puras
```

| Campo Shared Memory | Uso | Origem |
|---------------------|-----|--------|
| `mVehicleName` | Identificar o carro exato | `rF2ScoringVehicle` |
| `mVehicleClass` | Identificar a categoria (Hypercar/LMP2/GT3) | `rF2ScoringVehicle` |
| `mTrackName` | Identificar a pista | `rF2Scoring` |
| `mDriverName` | Identificar o perfil do piloto | `rF2ScoringVehicle` |

### 26.6 Mapeamento de Parâmetros por Carro (Index → Valor Físico)

**⚠️ PONTO CRÍTICO:** Cada carro tem **ranges DIFERENTES** para o mesmo parâmetro. O índice `CamberSetting=33` pode significar `-2.2°` num carro e `-3.0°` em outro.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TABELA DE CONVERSÃO INDEX ↔ VALOR FÍSICO (por carro)              │
│                                                                     │
│  Toyota GR010:                                                      │
│    CamberSetting  → index 0..60 → -4.0° a +2.0° (step 0.1°)      │
│    SpringSetting  → index 0..20 → 80 N/mm a 200 N/mm              │
│    RWSetting      → index 0..15 → 0.0° a 15.0° (step 1.0°)       │
│                                                                     │
│  Ferrari 296 GT3:                                                   │
│    CamberSetting  → index 0..40 → -3.5° a +0.5° (step 0.1°)      │
│    SpringSetting  → index 0..15 → 60 N/mm a 135 N/mm              │
│    RWSetting      → index 0..10 → 0.0° a 10.0° (step 1.0°)       │
│                                                                     │
│  A IA precisa saber o RANGE de cada parâmetro para cada carro       │
│  → Limitar os deltas para não sair do range                         │
│  → Escalar a saída Tanh corretamente                                │
└─────────────────────────────────────────────────────────────────────┘
```

**Solução: Tabela `car_param_ranges` no banco de dados:**

```sql
-- ============================================================
-- NOVA TABELA: car_param_ranges (Ranges de parâmetros por carro)
-- ============================================================
-- Construída AUTOMATICAMENTE ao ler o primeiro .svm de cada carro.
-- Extrai min/max/step de cada parâmetro a partir da descrição.
CREATE TABLE car_param_ranges (
    range_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id          INTEGER NOT NULL REFERENCES cars(car_id),
    param_name      TEXT NOT NULL,               -- Ex: "CamberSetting"
    section_name    TEXT NOT NULL,               -- Ex: "FRONTLEFT" ou "REARWING"
    min_index       INTEGER NOT NULL,            -- Índice mínimo no .svm
    max_index       INTEGER NOT NULL,            -- Índice máximo no .svm
    min_value       REAL,                        -- Valor físico mínimo (extraído da descrição)
    max_value       REAL,                        -- Valor físico máximo
    step_value      REAL,                        -- Incremento por índice
    unit            TEXT,                        -- "deg", "kPa", "N/mm", "Nm", etc.
    is_symmetric    INTEGER DEFAULT 1,           -- 1 = FL=FR e RL=RR por padrão
    UNIQUE(car_id, param_name, section_name)
);

CREATE INDEX idx_param_ranges_car ON car_param_ranges(car_id);
```

**Como a tabela é populada:**

```
1. Usuário carrega setup .svm pela primeira vez com um carro
2. Parser lê TODAS as linhas com "Setting="
3. Extrai o índice atual e a descrição (ex: "33//-2.2 deg")
4. Marca min/max provisórios (= valor atual)
5. A cada novo .svm carregado do mesmo carro, EXPANDE o range
6. Após ~3-5 setups diferentes, o range está bem mapeado
7. Opcionalmente: o usuário pode importar a tabela de ranges completa
```

### 26.7 Interface: Seleção e Visualização por Carro

```
┌─────────────────────────────────────────────────────────────────────┐
│  LMU Virtual Engineer                                    [─] [□] [×]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── Status da Conexão ────────────────────────────────────────┐  │
│  │ 🟢 LMU Detectado │ 🏎️ Toyota GR010 Hybrid │ 🏁 Le Mans (24h)│  │
│  │ Categoria: Hypercar │ Modelo IA: ✅ Carregado (v12, 324 amostras)│
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
├──────────┬──────────┬────────────┬──────────┬──────────┬───────────┤
│Telemetria│  Ajuste  │Diagnóstico │ Arquivos │  BD      │🏎️ Carros │
├──────────┴──────────┴────────────┴──────────┴──────────┴───────────┤
│                                                                     │
│  ┌─── Aba [Carros] ─────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  ┌─── HYPERCAR ───────────────────────────────────────────┐  │  │
│  │  │ Carro            │ Pistas   │ Voltas │ Modelo IA │ Status│  │
│  │  │──────────────────┼──────────┼────────┼───────────┼───────│  │
│  │  │ Toyota GR010     │ 4 pistas │  820   │ v12       │ ✅ 85%│  │
│  │  │ Porsche 963      │ 3 pistas │  450   │ v8        │ ✅ 72%│  │
│  │  │ Ferrari 499P     │ 2 pistas │  280   │ v5        │ ⚠️ 55%│  │
│  │  │ Cadillac V-LMDh  │ 1 pista  │   90   │ v2        │ ⚠️ 30%│  │
│  │  │ BMW M Hybrid V8  │ 0 pistas │    0   │ base      │ 🆕 TL │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                               │  │
│  │  ┌─── LMP2 ──────────────────────────────────────────────┐   │  │
│  │  │ Oreca 07 Gibson  │ 3 pistas │  340   │ v6        │ ✅ 68%│  │
│  │  └────────────────────────────────────────────────────────┘   │  │
│  │                                                               │  │
│  │  ┌─── LMGT3 ─────────────────────────────────────────────┐   │  │
│  │  │ Corvette Z06 GT3 │ 5 pistas │  960   │ v15       │ ✅ 90%│  │
│  │  │ Ferrari 296 GT3  │ 2 pistas │  180   │ v3        │ ⚠️ 42%│  │
│  │  │ Porsche 911 GT3R │ 1 pista  │   65   │ v1        │ ⚠️ 22%│  │
│  │  └────────────────────────────────────────────────────────┘   │  │
│  │                                                               │  │
│  │  Legenda: ✅ Confiável (>70%) │ ⚠️ Em treino │ 🆕 TL = Transfer│
│  │           Learning da categoria (sem dados próprios)          │  │
│  │                                                               │  │
│  │  ┌─── Detalhes: Toyota GR010 Hybrid ─────────────────────┐  │  │
│  │  │                                                         │  │  │
│  │  │  Pistas treinadas:                                      │  │  │
│  │  │  • Le Mans (24h)    — 320 voltas — Melhor: 3:24.1 ✅   │  │  │
│  │  │  • Spa-Francorchamps — 210 voltas — Melhor: 2:01.3 ✅  │  │  │
│  │  │  • Monza            — 180 voltas — Melhor: 1:34.2 ⚠️   │  │  │
│  │  │  • Bahrain           — 110 voltas — Melhor: 1:48.7 ⚠️  │  │  │
│  │  │                                                         │  │  │
│  │  │  Parâmetros mapeados: 42/45 (93%)                       │  │  │
│  │  │  Ranges confirmados: 38/42 (90%)                        │  │  │
│  │  │                                                         │  │  │
│  │  │  [📊 Ver Evolução] [🔄 Retreinar] [📤 Exportar Modelo] │  │  │
│  │  │  [🔗 Gerar Base da Categoria] [🗑️ Resetar Modelo]      │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 26.8 Lógica de Carregamento Automático de Modelo

Quando o jogo inicia ou o carro/pista muda, a IA segue esta lógica:

```
┌────────────────────────────────────────────────────────────────┐
│  FLUXO: Detectar Carro → Carregar Modelo Correto               │
│                                                                 │
│  Shared Memory detecta:                                         │
│    mVehicleName = "Porsche 963"                                 │
│    mVehicleClass = "Hypercar"                                   │
│    mTrackName = "spa_francorchamps"                             │
│                                                                 │
│  ┌─ Passo 1: Buscar no banco ─────────────────────────────────┐│
│  │  SELECT car_id FROM cars                                    ││
│  │  WHERE car_name LIKE '%Porsche 963%'                        ││
│  │                                                              ││
│  │  Encontrou? ──┬── SIM → car_id = 2                         ││
│  │               └── NÃO → INSERT novo carro + car_id = N     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Passo 2: Buscar modelo específico ────────────────────────┐│
│  │  Arquivo: models/hypercar/porsche_963/spa_francorchamps.pth ││
│  │                                                              ││
│  │  Existe? ──┬── SIM → Carregar modelo ✅                     ││
│  │            └── NÃO → Passo 3                               ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Passo 3: Tentar Transfer Learning ────────────────────────┐│
│  │  Arquivo: models/_shared/hypercar_base.pth                  ││
│  │                                                              ││
│  │  Existe? ──┬── SIM → Carregar como ponto de partida ⚠️     ││
│  │            │         + Notificar usuário:                   ││
│  │            │         "Usando modelo base Hypercar.           ││
│  │            │          Precisará de ~30 voltas para           ││
│  │            │          adaptar ao Porsche 963."              ││
│  │            └── NÃO → Passo 4                               ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Passo 4: Sem dados — só heurísticas ──────────────────────┐│
│  │  Notificar usuário:                                         ││
│  │  "Primeiro uso com Porsche 963 @ Spa.                       ││
│  │   A IA vai coletar dados por 10 voltas.                     ││
│  │   Enquanto isso, usando regras de engenharia.               ││
│  │   Confiança: 0%"                                            ││
│  └──────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────┘
```

### 26.9 Heurísticas Específicas por Categoria

As regras de engenharia também mudam por categoria:

```python
# core/heuristics.py — Regras adaptadas por classe de carro

HEURISTICS_BY_CLASS = {
    "Hypercar": {
        # Hypercars têm MUITO downforce → mais sensíveis a ride height
        "ride_height_sensitivity": "high",
        "camber_range_front": (-4.0, -1.5),    # graus, mais negativo que GT3
        "camber_range_rear": (-3.0, -0.5),
        "default_wing": "medium-high",          # Equilíbrio velocidade/curva
        "brake_regen_aware": True,              # Considerar freio regenerativo
        "fuel_weight_impact": "high",           # Carro leve → alto impacto % do fuel
        "tire_pressure_target_kpa": (130, 145), # Pressão alvo a quente
        "aero_balance_critical": True,          # Rake é fundamental
    },
    "LMP2": {
        "ride_height_sensitivity": "high",
        "camber_range_front": (-3.5, -1.0),
        "camber_range_rear": (-2.5, -0.5),
        "default_wing": "medium",
        "brake_regen_aware": False,             # Sem hybrid
        "fuel_weight_impact": "medium",
        "tire_pressure_target_kpa": (135, 150),
        "aero_balance_critical": True,
    },
    "LMGT3": {
        # GT3 têm MENOS downforce → foco em mecânico
        "ride_height_sensitivity": "medium",
        "camber_range_front": (-3.0, -0.5),
        "camber_range_rear": (-2.5, 0.0),
        "default_wing": "category-dependent",   # BoP limita
        "brake_regen_aware": False,
        "fuel_weight_impact": "low",            # Carro mais pesado
        "tire_pressure_target_kpa": (155, 175), # Pressões mais altas
        "aero_balance_critical": False,         # Mecânico > Aero
        "bop_limited": True,                    # Balance of Performance ativo
    },
}
```

### 26.10 Banco de Dados — Alterações para Multi-Carro

A tabela `cars` já existe (Seção 20.2), mas precisa de campos adicionais:

```sql
-- Expandir a tabela cars existente:
ALTER TABLE cars ADD COLUMN car_class_normalized TEXT;
    -- "hypercar", "lmp2", "lmgt3" (normalizado para código)
ALTER TABLE cars ADD COLUMN has_hybrid INTEGER DEFAULT 0;
    -- 1 se o carro tem sistema híbrido
ALTER TABLE cars ADD COLUMN has_bop INTEGER DEFAULT 0;
    -- 1 se o carro está sujeito a Balance of Performance
ALTER TABLE cars ADD COLUMN base_weight_kg REAL;
    -- Peso base do carro (sem combustível)
ALTER TABLE cars ADD COLUMN max_fuel_l REAL;
    -- Capacidade máxima de combustível

-- Tabela de similaridade entre carros (para Transfer Learning):
CREATE TABLE car_similarity (
    car_id_a    INTEGER NOT NULL REFERENCES cars(car_id),
    car_id_b    INTEGER NOT NULL REFERENCES cars(car_id),
    similarity  REAL NOT NULL,      -- 0.0 = sem relação, 1.0 = idênticos
    basis       TEXT,               -- "same_class", "same_drivetrain", "manual"
    PRIMARY KEY (car_id_a, car_id_b)
);

-- View para dashboard multi-carro:
CREATE VIEW v_car_training_status AS
SELECT
    c.car_name,
    c.car_class,
    COUNT(DISTINCT t.track_id) AS tracks_used,
    COUNT(l.lap_id) AS total_laps,
    COALESCE(mc.epoch, 0) AS model_epochs,
    COALESCE(td_count.cnt, 0) AS training_samples,
    CASE
        WHEN COALESCE(td_count.cnt, 0) >= 500 THEN 'confiavel'
        WHEN COALESCE(td_count.cnt, 0) >= 100 THEN 'em_treino'
        WHEN COALESCE(td_count.cnt, 0) >= 30 THEN 'iniciante'
        ELSE 'sem_dados'
    END AS ai_status
FROM cars c
LEFT JOIN sessions s ON c.car_id = s.car_id
LEFT JOIN laps l ON s.session_id = l.session_id
LEFT JOIN tracks t ON s.track_id = t.track_id
LEFT JOIN model_checkpoints mc ON c.car_id = mc.car_id AND mc.is_active = 1
LEFT JOIN (
    SELECT car_id, COUNT(*) AS cnt FROM training_data GROUP BY car_id
) td_count ON c.car_id = td_count.car_id
GROUP BY c.car_id;
```

### 26.11 Impacto no Treinamento

| Aspecto | Modelo Único (❌) | Modelo por Carro+Pista (✅) |
|---------|:-----------------:|:---------------------------:|
| Convergência | Lenta (dados conflitantes) | Rápida (dados coerentes) |
| Precisão | Baixa (médias genéricas) | Alta (específico ao combo) |
| Tamanho em disco | 1 × ~2MB | N × ~2MB (ex: 20 combos = ~40MB) |
| Dados mínimos | ~2000 voltas mistas | ~50 voltas por combo |
| Transfer Learning | Não aplicável | ✅ Aproveita entre carros similares |
| Memória RAM | ~10MB | ~10MB (só 1 modelo carregado por vez) |

### 26.12 Fluxo Completo: Troca de Carro Durante Sessão

```
  Usuário está no Toyota GR010 @ Le Mans
  IA carregada: models/hypercar/toyota_gr010/le_mans_24h.pth ✅
             │
             │  Usuário troca para Corvette Z06 GT3 @ Le Mans
             ▼
  ┌──────────────────────────────────────────────────────────┐
  │ 1. Shared Memory detecta mVehicleName mudou             │
  │ 2. Salvar estado atual (checkpoint Toyota @ Le Mans)     │
  │ 3. Buscar modelo: corvette_z06_gt3r/le_mans_24h.pth     │
  │ 4. SE existe → carregar                                  │
  │ 5. Atualizar GUI: status bar, heurísticas, ranges        │
  │ 6. Notificar: "Modelo trocado: Corvette Z06 GT3 @ Le Mans│
  │                Confiança: 90% (960 voltas)"              │
  │ 7. Trocar heurísticas para LMGT3                         │
  │ 8. Trocar ranges de parâmetros (car_param_ranges)        │
  └──────────────────────────────────────────────────────────┘
             │
             │  Tudo automático. Usuário não precisa fazer nada.
             ▼
  IA sugere ajustes ESPECÍFICOS para Corvette GT3 🏁
```

---

## 27. RISCOS ADICIONAIS — MULTI-CARRO (v4)

| # | Risco | Prob. | Impacto | Mitigação |
|---|-------|:-----:|:-------:|-----------|
| 13 | Nome do carro na Shared Memory pode variar (ex: #7 vs #8) | 🟡 Média | 🟡 Médio | Normalizar nome (strip números, trim) |
| 14 | BoP muda entre patches do jogo (GT3) | 🟡 Média | 🔴 Alto | Versionar modelos; detectar mudança drástica no reward → aviso |
| 15 | Mesmo carro com compound diferente (Soft/Medium/Hard) precisa de dados separados? | 🟡 Média | 🟡 Médio | Compound como INPUT da rede neural (já está como `CompoundSetting`) |
| 16 | Muitos combos carro×pista = muitos modelos com poucos dados cada | 🔴 Alta | 🟡 Médio | Transfer Learning + níveis de confiança |
| 17 | Carros futuros (DLC) terão parâmetros diferentes | 🟢 Baixa | 🟢 Baixo | Parser .svm auto-descobre parâmetros; car_param_ranges é dinâmico |

---

## 28. PONTOS DE DECISÃO — MULTI-CARRO (v4)

### ❓ Pergunta 10: Granularidade do Modelo
- **Opção A:** Um modelo **por carro × pista** (mais preciso, mais modelos) — **recomendado**
- **Opção B:** Um modelo **por carro** (mais generalista, menos modelos)
- **Opção C:** Um modelo **por categoria × pista** (mais genérico ainda, compartilha entre carros)

### ❓ Pergunta 11: Transfer Learning Automático
- **Opção A:** Automático (quando não há modelo para o combo, usa o base da categoria) — **recomendado**
- **Opção B:** Perguntar ao usuário antes de transferir
- **Opção C:** Desligado (sempre começar do zero)

### ❓ Pergunta 12: Compound de Pneu
- **Opção A:** Compound como input da rede neural (um modelo serve para todos os compounds) — **recomendado**
- **Opção B:** Modelo separado por compound (Soft/Medium/Hard separados)

---

## 29. CONCLUSÃO REVISADA (v4) — MULTI-CARRO

| Critério | v3 | v4 (Multi-Carro) |
|----------|:--:|:-----------------:|
| Cobertura de carros | ⚠️ Modelo único | ✅ **Modelo por combo carro×pista** |
| Precisão das sugestões | ⚠️ Genérica | ✅ **Específica ao carro** |
| Primeira experiência (carro novo) | ❌ Sem dados = inútil | ✅ **Transfer Learning + heurísticas por classe** |
| Escalabilidade | ✅ | ✅ Disco: ~2MB por combo. RAM: ~10MB fixo |
| Complexidade de desenvolvimento | Alta | 🔺 **Muito Alta** (mas modular) |

**Veredicto: ✅ VIÁVEL** — O suporte multi-carro é **essencial** para o produto ser útil (usar um modelo treinado com Toyota para sugerir setup de Corvette GT3 seria inútil). A arquitetura por combo carro×pista + Transfer Learning na mesma categoria é a abordagem correta.

**Fases Revisadas (v4):**

| Fase | Escopo Multi-Carro |
|------|-------------------|
| **Fase 1 (MVP)** | Detecção automática de carro/pista + modelo separado por combo + `car_param_ranges` + heurísticas por classe |
| **Fase 2** | Transfer Learning entre carros da mesma categoria + aba [Carros] na GUI + `car_similarity` |
| **Fase 3** | Exportar/importar modelos de carros específicos entre usuários |

---

*Aguardo aprovação e respostas às perguntas das Seções 18, 24 e 28 para iniciar o desenvolvimento.*

---

## 30. SISTEMA DE CRIAÇÃO DE SETUPS — CLIMA, ARQUIVO BASE E IA (v5)

**Data:** 31 de Março de 2026  
**Status:** Relatório de Melhorias — Aguardando Aprovação

---

### 30.1 VISÃO GERAL DO NOVO SISTEMA

O sistema deve permitir que o usuário:
1. **Carregue um arquivo .svm base** (setup de referência, ex: que já usa para seco)
2. **Escolha o cenário de clima** (Seco, Chuva, Misto, ou combinação)
3. **A IA gere automaticamente novos .svm** com ajustes específicos para cada condição
4. **Salve os setups na pasta correta** da pista dentro do diretório do LMU
5. **Gere múltiplas variações** se o usuário quiser (ex: chuva leve, chuva forte, misto)

---

### 30.2 FLUXO DE CRIAÇÃO DE SETUP

```
  ┌───────────────────────────────────────────────────────────────┐
  │  ETAPA 1: ARQUIVO BASE                                       │
  │                                                               │
  │  📂 Selecione o setup base:                                  │
  │  [ Le Mans Ultimate\UserData\player\Settings\                │
  │    Silverstone_National\meu_setup_seco.svm        ]  [...]   │
  │                                                               │
  │  ✅ Setup parseado: 45 parâmetros ajustáveis                 │
  │  Carro detectado: Toyota GR010 Hybrid                        │
  │  Pista detectada: Silverstone_National                        │
  └──────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  ETAPA 2: CONDIÇÃO CLIMÁTICA                                 │
  │                                                               │
  │  Que tipo de setup deseja criar?                              │
  │                                                               │
  │  ☑ Setup de SECO otimizado                                   │
  │  ☑ Setup de CHUVA                                            │
  │  ☑ Setup MISTO (transição seco→chuva)                        │
  │  ☐ Setup de CHUVA FORTE                                      │
  │  ☐ Setup MISTO (transição chuva→seco)                        │
  │                                                               │
  │  Dados da sessão atual (se conectado ao jogo):               │
  │  🌡️ Temp. ar: 22°C | Temp. pista: 34°C                      │
  │  🌧️ Chuva atual: 0% | Previsão: 45% em 12 min              │
  │  💨 Vento: 15 km/h NE                                        │
  └──────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  ETAPA 3: IA GERA OS SETUPS                                  │
  │                                                               │
  │  Baseado no setup "meu_setup_seco.svm" + dados da sessão:    │
  │                                                               │
  │  📄 SetorFlow_seco_GT3_Toyota_GR010_31-03-2026.svm           │
  │     → Ajustou: asa +1, pressão pneu -2 kPa, camber +0.3°    │
  │                                                               │
  │  📄 SetorFlow_chuva_GT3_Toyota_GR010_31-03-2026.svm          │
  │     → Ajustou: asa +4, mola -3, ride height +2,              │
  │       pressão pneu -5 kPa, TC +2, ABS +2, diff -15 Nm       │
  │                                                               │
  │  📄 SetorFlow_misto_GT3_Toyota_GR010_31-03-2026.svm          │
  │     → Valores intermediários entre seco e chuva              │
  │                                                               │
  │  [👁️ Visualizar Diferenças] [💾 Salvar Todos] [Cancelar]     │
  └──────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────────────┐
  │  ETAPA 4: SALVAMENTO                                         │
  │                                                               │
  │  Diretório de destino:                                        │
  │  📁 .../Settings/Silverstone_National/                        │
  │                                                               │
  │  ✅ SetorFlow_seco_GT3_Toyota_GR010_31-03-2026.svm  — salvo   │
  │  ✅ SetorFlow_chuva_GT3_Toyota_GR010_31-03-2026.svm — salvo  │
  │  ✅ SetorFlow_misto_GT3_Toyota_GR010_31-03-2026.svm — salvo  │
  │                                                               │
  │  📋 Backup do original criado em backups/                     │
  └───────────────────────────────────────────────────────────────┘
```

---

### 30.3 DADOS DO CLIMA — O QUE CAPTURAR E COMO USAR

#### 30.3.1 Dados Disponíveis na Shared Memory

| Dado | Campo rF2 | Uso no Setup |
|------|-----------|-------------|
| **Chuva atual** (0.0–1.0) | `rF2Scoring.mRaining` | Decide se é seco/chuva/misto |
| **Min. para chuva iniciar** | `rF2Scoring.mMinPathWetness` | Previsão de mudança climática |
| **Max. umidade da pista** | `rF2Scoring.mMaxPathWetness` | Intensidade máxima esperada |
| **Temp. ambiente** (°C) | `rF2Scoring.mAmbientTemp` | Afeta pressão dos pneus e grip mecânico |
| **Temp. pista** (°C) | `rF2Scoring.mTrackTemp` | Afeta aderência, desgaste, pressão ideal |
| **Condição da pista** | `rF2Scoring.mDarkCloud` | Nuvens escuras → chuva próxima |
| **Vento** | `rF2Scoring.mWind` (vetor XYZ) | Afeta velocidade em retas e downforce efetiva |
| **Superfície do pneu** | `rF2Wheel.mSurfaceType` | Detecta pista molhada/seca por setor |

#### 30.3.2 Parâmetros Afetados por Clima

| Parâmetro | Seco → Chuva | Justificativa Física |
|-----------|:------------:|---------------------|
| **Asa traseira** (RWSetting) | ↑ +3 a +6 | Mais downforce compensa perda de grip mecânico |
| **Molas** (SpringSetting) | ↓ -2 a -4 | Mais macias para melhor contato em pista irregular |
| **Ride Height** | ↑ +1 a +3 | Evita aquaplanagem + mais curso de suspensão |
| **Pressão pneus** | ↓ -3 a -8 kPa | Aumenta área de contato (patch) na água |
| **Camber** | ↓ (menos negativo) +1 a +3 | Pneu mais plano = mais contato em baixa carga |
| **Barra anti-rolagem** | ↓ -2 a -4 | Mais flex = mais grip mecânico por roda |
| **Diff preload** | ↓ -10 a -20 Nm | Menor preload = diferencial mais aberto = melhor tração |
| **Brake pressure** | ↓ -5 a -10% | Evita travamento de rodas no molhado |
| **Brake bias** | → mais traseiro +1 a +2% | Equilibrar frenagem no molhado |
| **TC (Traction Control)** | ↑ +2 a +4 mapas | Mais eletrônica para compensar grip |
| **ABS** | ↑ +1 a +3 mapas | Anti-travamento mais ativo |
| **Slow Bump** | ↓ -1 a -2 | Suspensão mais suave para acompanhar irregularidades |
| **Slow Rebound** | ↓ -1 a -2 | Retorno mais suave da suspensão |
| **Compound** | → WET/INTER | Composto de chuva (se disponível no carro) |

#### 30.3.3 Cenários de Clima e Interpolação

O sistema deve suportar 5 cenários predefinidos com **interpolação**:

| Cenário | Fator de Interpolação | Descrição |
|---------|:---------------------:|-----------|
| **Seco Otimizado** | 0.0 | Setup base + otimizações de telemetria/IA |
| **Seco→Chuva (Misto Leve)** | 0.25–0.35 | Chuva chegando; ajustes preventivos |
| **Misto Pleno** | 0.50 | Metade seca, metade molhada |
| **Chuva→Seco (Secando)** | 0.65–0.75 | Pista secando; manter margem |
| **Chuva Forte** | 1.0 | Ajustes máximos de chuva |

A interpolação funciona assim:
```
valor_final = valor_base + (delta_chuva × fator_interpolacao)
```

Exemplo para asa traseira com delta_chuva = +5:
- Seco: base + (5 × 0.0) = base
- Misto leve: base + (5 × 0.3) = base + 1.5 → arredonda para +2
- Chuva forte: base + (5 × 1.0) = base + 5

---

### 30.4 DADOS DA SESSÃO — INPUTS ADICIONAIS PARA A IA

Para que a IA faça ajustes inteligentes, ela precisa de **contexto do ambiente** além da telemetria do carro. Novos inputs propostos para a rede neural:

| Input Novo | Range | Fonte | Justificativa |
|------------|-------|-------|---------------|
| `rain_current` | 0.0–1.0 | `mRaining` | Intensidade de chuva atual |
| `rain_forecast` | 0.0–1.0 | `mMaxPathWetness` | Previsão de umidade máxima |
| `track_temp` | 10–60 °C | `mTrackTemp` | Temperatura afeta grip e pressão ideal |
| `ambient_temp` | 0–45 °C | `mAmbientTemp` | Temperatura ambiente |
| `cloud_darkness` | 0.0–1.0 | `mDarkCloud` | Indicador de chuva iminente |
| `wind_speed` | 0–50 m/s | `|mWind|` (magnitude) | Vento afeta aero |
| `track_wetness` | 0.0–1.0 | Média de `mSurfaceType` | Quão molhada está a pista |
| `session_type` | 0–4 | `mSession` | Treino/Quali/Corrida afeta estratégia |

**Impacto:** Aumenta os inputs de 38 para **46 features**. A rede neural precisa ser ajustada:
- Primeira camada: Linear(46, 256) em vez de Linear(38, 256)
- O normalizer precisa ser atualizado para 46 features

---

### 30.5 O QUE MUDAR PARA TREINAR A IA — PARÂMETROS DE REFERÊNCIA

Para treinar, a IA precisa saber **QUAL É O IMPACTO** de cada parâmetro no comportamento do carro. Abaixo os parâmetros e seus sensibilidades (usados como `MAX_DELTA_SCALE` no treinamento):

#### 30.5.1 Tabela de Sensibilidade por Parâmetro

| Parâmetro | Max Δ (índices) | Sensibilidade | Impacto Principal |
|-----------|:-----------:|:-------------:|-------------------|
| RWSetting (asa) | ±5 | 🔴 Alta | Velocidade de reta vs grip em curva |
| SpringSetting (molas) | ±4 | 🔴 Alta | Comportamento mecânico geral |
| CamberSetting | ±6 | 🟡 Média | Contato do pneu, desgaste |
| PressureSetting | ±5 | 🔴 Alta | Grip, temperatura, desgaste |
| RideHeightSetting | ±4 | 🔴 Alta | Aerodinâmica, bottoming |
| AntiSwaySetting (ARB) | ±4 | 🟡 Média | Sub/oversteer transitório |
| SlowBumpSetting | ±3 | 🟢 Baixa | Conforto, contato com solo |
| SlowReboundSetting | ±3 | 🟢 Baixa | Recuperação da suspensão |
| FastBumpSetting | ±3 | 🟢 Baixa | Kerbs, bumps rápidos |
| FastReboundSetting | ±3 | 🟢 Baixa | Kerbs, bumps rápidos |
| BrakePressureSetting | ±4 | 🟡 Média | Distância de frenagem |
| RearBrakeSetting | ±3 | 🟡 Média | Estabilidade na frenagem |
| DiffPreloadSetting | ±4 | 🟡 Média | Tração, rotação |
| ToeInSetting | ±3 | 🟢 Baixa | Estabilidade direcional |
| TCMap/ABSMap | ±3 | 🟡 Média | Eletrônica de ajuda |
| BrakeDuctSetting | ±3 | 🟢 Baixa | Temperatura dos freios |
| FuelSetting | especial | especial | Peso → afeta tudo |
| CompoundSetting | especial | 🔴 Crítica | Seco vs Chuva → muda tudo |

#### 30.5.2 Regras Heurísticas de Clima (para treinamento inicial)

As regras abaixo são usadas como **"professor"** para a IA nos primeiros ajustes, antes de ter dados suficientes:

```python
WEATHER_DELTAS = {
    "rain_heavy": {  # Chuva forte (fator 1.0)
        "delta_rw": +5,              # Asa traseira: máximo downforce
        "delta_spring_f": -3,        # Molas mais macias
        "delta_spring_r": -3,
        "delta_camber_f": +3,        # Camber menos negativo
        "delta_camber_r": +2,
        "delta_pressure_f": -5,      # Pressão menor → mais contato
        "delta_pressure_r": -5,
        "delta_ride_height_f": +2,   # Mais alto → menos aquaplanagem
        "delta_ride_height_r": +2,
        "delta_arb_f": -3,           # ARB mais macia → mais grip mecânico
        "delta_arb_r": -3,
        "delta_diff_preload": -3,    # Diff mais aberto → melhor tração
        "delta_brake_press": -3,     # Menos pressão → menos travamento
        "delta_rear_brake_bias": +2, # Bias mais traseiro
        "delta_tc_map": +3,          # Mais TC
        "delta_abs_map": +2,         # Mais ABS
        "delta_slow_bump_f": -1,     # Suspensão mais macia
        "delta_slow_bump_r": -1,
        "delta_slow_rebound_f": -1,
        "delta_slow_rebound_r": -1,
    },
    "rain_light": {  # Chuva leve (fator 0.5)
        # Metade dos deltas de rain_heavy (calculado por interpolação)
    },
    "mixed_to_wet": {  # Seco para chuva (fator 0.35)
        # Ajustes preventivos — menos agressivos que chuva
    },
    "mixed_to_dry": {  # Chuva para seco (fator 0.65)
        # Mantém margem de segurança enquanto pista seca
    },
}
```

#### 30.5.3 Como a IA Aprende com o Clima

```
┌─────────────────────────────────────────────────────────────┐
│               CICLO DE APRENDIZADO COM CLIMA                │
│                                                             │
│  1. Usuário carrega setup base "Silverstone_seco.svm"       │
│  2. Clima detectado: chuva chegando em 10 min               │
│  3. IA gera "SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm"   │
│  4. Usuário aplica o setup de chuva no jogo                 │
│  5. Usuário dirige 5-10 voltas com o setup de chuva         │
│  6. Telemetria captura: temps, pressões, grip, lap times    │
│  7. Usuário dá feedback: "melhorou" / "piorou" / "igual"   │
│  8. Sistema de reward calcula score composto                │
│  9. IA treina com os dados: {clima, setup_base, deltas}     │
│ 10. Próxima vez que chover, IA gera setup MELHOR            │
│                                                             │
│  Cada iteração → IA fica mais precisa para aquele           │
│  combo: carro × pista × condição climática                  │
└─────────────────────────────────────────────────────────────┘
```

---

### 30.6 REGRA FUNDAMENTAL: PROTEÇÃO DE ARQUIVOS EXISTENTES

> **⚠️ REGRA Nº1: O PROGRAMA NUNCA SOBRESCREVE ARQUIVOS .SVM EXISTENTES OU O ARQUIVO BASE.**

O sistema segue uma política estrita de **somente leitura sobre o original** e **criação de novos arquivos**:

#### 30.6.1 Fluxo de Criação (padrão)

```
┌─────────────────────────────────────────────────────────────────┐
│                   POLÍTICA DE ARQUIVOS .SVM                     │
│                                                                 │
│  REGRA 1: O arquivo base (.svm original) é SOMENTE LEITURA     │
│           → O programa NUNCA modifica ou sobrescreve o base     │
│           → Ele LÊ os dados do base para gerar novos arquivos   │
│                                                                 │
│  REGRA 2: Cada geração cria um NOVO arquivo .svm               │
│           → Nenhum arquivo existente é substituído              │
│           → Se o nome já existir, adiciona sufixo numérico      │
│           → Ex: SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm     │
│           →  Se já existe, adiciona _2, _3...                   │
│           → Ex: SetorFlow_chuva_GT3_Mclaren_31-03-2026_2.svm   │
│                                                                 │
│  REGRA 3: Para EDITAR um arquivo existente, o usuário deve      │
│           EXPLICITAMENTE selecionar esse arquivo na GUI         │
│           → O programa abre o arquivo selecionado               │
│           → Mostra as alterações ANTES de salvar                │
│           → Só salva com confirmação do usuário                 │
│                                                                 │
│  REGRA 4: Se o usuário quer recriar/atualizar um setup gerado   │
│           anteriormente, ele pode:                              │
│           a) Gerar um NOVO arquivo a partir do base (padrão)    │
│           b) Selecionar o arquivo gerado e clicar "Editar"      │
│              → Neste caso o programa edita AQUELE arquivo       │
│              → Cria backup automático antes (.svm.bak)          │
│                                                                 │
│  REGRA 5: Se o usuário quer múltiplas variações, cada uma é     │
│           um arquivo separado, todos na mesma pasta da pista    │
└─────────────────────────────────────────────────────────────────┘
```

#### 30.6.2 Fluxo Detalhado: Criar vs Editar

```
   MODO 1: CRIAR NOVO (padrão)                MODO 2: EDITAR EXISTENTE
   ─────────────────────────                   ─────────────────────────
                                               
   1. Usuário seleciona BASE .svm              1. Usuário seleciona QUALQUER .svm
   2. Escolhe condições (chuva, misto...)      2. Clica "Editar Este Setup"
   3. Programa LÊ o base (não modifica)        3. Programa LÊ o arquivo selecionado
   4. IA/heurísticas geram deltas              4. IA/heurísticas sugerem deltas
   5. Cria NOVO arquivo .svm                   5. Mostra preview das mudanças
   6. Salva na mesma pasta da pista            6. Usuário CONFIRMA ou CANCELA
   7. Base original INTACTO ✅                 7. Se confirma:
                                                  → Cria backup (.svm.bak)
                                                  → Aplica mudanças no arquivo
                                               8. Original preservado no .bak ✅
```

#### 30.6.3 Implementação da Proteção

```python
class SetupFileManager:
    """Gerencia leitura/escrita de arquivos .svm com proteção."""
    
    def read_base(self, path: Path) -> SVMFile:
        """Lê arquivo base. NUNCA modifica o original."""
        return parse_svm(path)  # somente leitura
    
    def save_new(self, svm: SVMFile, directory: Path, name: str) -> Path:
        """
        Salva como NOVO arquivo. Se nome já existe, adiciona sufixo.
        NUNCA sobrescreve arquivo existente.
        """
        target = directory / f"{name}.svm"
        counter = 2
        while target.exists():
            target = directory / f"{name}_{counter}.svm"
            counter += 1
        save_svm(svm, target)
        return target
    
    def edit_existing(self, path: Path, deltas: dict) -> Path:
        """
        Edita um arquivo existente. REQUER confirmação do usuário.
        Cria backup automático antes de modificar.
        """
        # 1. Criar backup
        backup = path.with_suffix('.svm.bak')
        shutil.copy2(path, backup)
        
        # 2. Aplicar deltas
        svm = parse_svm(path)
        svm = apply_deltas(svm, deltas)
        save_svm(svm, path)
        
        return path
```

#### 30.6.4 Estrutura de Pastas dos Setups Gerados

Os setups são salvos no diretório correto do LMU, organizados por pista:

```
Le Mans Ultimate/
└── UserData/
    └── player/
        └── Settings/
            ├── Silverstone_National/
            │   ├── meu_setup_seco.svm                              ← 🔒 ORIGINAL (NUNCA tocado)
            │   ├── SetorFlow_seco_GT3_Toyota_GR010_31-03-2026.svm   ← 🆕 Gerado pela IA
            │   ├── SetorFlow_chuva_GT3_Toyota_GR010_31-03-2026.svm  ← 🆕 Gerado pela IA
            │   ├── SetorFlow_chuva-leve_GT3_Toyota_GR010_31-03-2026.svm ← 🆕 Gerado
            │   ├── SetorFlow_misto_GT3_Toyota_GR010_31-03-2026.svm  ← 🆕 Gerado pela IA
            │   ├── SetorFlow_secando_GT3_Toyota_GR010_31-03-2026.svm ← 🆕 Gerado pela IA
            │   └── SetorFlow_chuva_GT3_Toyota_GR010_31-03-2026_2.svm ← 🆕 2ª versão
            │
            ├── le_mans_24h/
            │   ├── race_base.svm                                    ← 🔒 ORIGINAL
            │   ├── SetorFlow_chuva_Hypercar_Toyota_GR010_31-03-2026.svm ← 🆕 Gerado
            │   └── SetorFlow_misto_Hypercar_Toyota_GR010_31-03-2026.svm ← 🆕 Gerado
            │
            └── Monza/
                ├── quali_setup.svm                                  ← 🔒 ORIGINAL
                └── SetorFlow_chuva_GT3_Ferrari_296_31-03-2026.svm   ← 🆕 Gerado
```

**Convenção de nomes — Padrão SetorFlow:**

> **Formato:** `SetorFlow_{clima}_{categoria}_{carro}_{DD-MM-AAAA}.svm`

| Campo | Descrição | Exemplos |
|-------|-----------|----------|
| `SetorFlow` | Prefixo fixo — identifica que foi gerado pela IA | Sempre presente |
| `{clima}` | Condição climática do setup | `seco`, `chuva`, `chuva-leve`, `chuva-forte`, `misto`, `secando` |
| `{categoria}` | Categoria do carro | `GT3`, `GT4`, `Hypercar`, `LMDh`, `GTE`, `Formula` |
| `{carro}` | Modelo do carro (espaços substituídos por `_`) | `Mclaren`, `Toyota_GR010`, `Ferrari_296`, `Porsche_963` |
| `{DD-MM-AAAA}` | Data da geração | `31-03-2026` |

**Exemplos completos:**
| Clima | Arquivo gerado | Modo |
|-------|----------------|------|
| Seco otimizado | `SetorFlow_seco_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Chuva | `SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Chuva leve | `SetorFlow_chuva-leve_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Chuva forte | `SetorFlow_chuva-forte_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Misto | `SetorFlow_misto_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Secando | `SetorFlow_secando_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Mesclado 60/40 | `SetorFlow_mescla-60-40_GT3_Mclaren_31-03-2026.svm` | 🆕 Criar |
| Anti-colisão | `SetorFlow_chuva_GT3_Mclaren_31-03-2026_2.svm` | 🆕 Versão 2 |
| Backup de edição | `SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm.bak` | 🔄 Backup |

**Regras de geração do nome:**
1. Categoria e carro são **detectados automaticamente** dos dados da sessão/arquivo .svm
2. Se o usuário gera 2+ setups do **mesmo clima/carro/data**, adiciona sufixo `_2`, `_3`...
3. Se o carro tem espaços no nome, substitui por `_`
4. Caracteres especiais são removidos do nome (apenas letras, números, `-` e `_`)
5. O usuário pode **personalizar o nome** antes de salvar, mas o padrão é auto-gerado

> **Resumo:** O programa LÊ o base → cria NOVOS arquivos com nomenclatura `SetorFlow_` → NUNCA toca no original.
> Para editar, o usuário escolhe explicitamente o arquivo → programa cria backup `.bak` → edita.

---

### 30.7 ARQUITETURA DO MÓDULO `setup_generator.py`

Novo módulo proposto: `core/setup_generator.py`

```python
import re
from datetime import date

class WeatherCondition(Enum):
    """Condições climáticas → usadas no nome do arquivo SetorFlow."""
    SECO            = "seco"            # fator 0.0 (otimizado)
    CHUVA_LEVE      = "chuva-leve"      # fator 0.3
    MISTO           = "misto"           # fator 0.5
    CHUVA           = "chuva"           # fator 0.7
    CHUVA_FORTE     = "chuva-forte"     # fator 1.0
    SECANDO         = "secando"         # fator 0.65 (transição chuva→seco)


class SetorFlowNaming:
    """
    Gera nomes de arquivo no padrão SetorFlow.
    Formato: SetorFlow_{clima}_{categoria}_{carro}_{DD-MM-AAAA}.svm

    Exemplos:
        SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm
        SetorFlow_seco_Hypercar_Toyota_GR010_31-03-2026.svm
        SetorFlow_misto_GT3_Ferrari_296_31-03-2026_2.svm  (anti-colisão)
    """

    @staticmethod
    def sanitize(text: str) -> str:
        """Remove caracteres especiais, troca espaços por _."""
        text = text.replace(" ", "_")
        return re.sub(r'[^a-zA-Z0-9_\-]', '', text)

    @classmethod
    def build_name(
        cls,
        weather: WeatherCondition,
        car_category: str,     # "GT3", "Hypercar", "LMDh", etc.
        car_model: str,        # "Mclaren", "Toyota GR010", etc.
        gen_date: date | None = None,
    ) -> str:
        """Gera o nome base (sem extensão) no padrão SetorFlow."""
        if gen_date is None:
            gen_date = date.today()
        
        clima = weather.value
        categoria = cls.sanitize(car_category)
        carro = cls.sanitize(car_model)
        data = gen_date.strftime("%d-%m-%Y")
        
        return f"SetorFlow_{clima}_{categoria}_{carro}_{data}"

    @classmethod
    def resolve_collision(cls, base_name: str, output_dir: Path) -> Path:
        """
        Se SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm já existe,
        retorna SetorFlow_chuva_GT3_Mclaren_31-03-2026_2.svm, etc.
        NUNCA sobrescreve.
        """
        path = output_dir / f"{base_name}.svm"
        if not path.exists():
            return path
        
        n = 2
        while True:
            path = output_dir / f"{base_name}_{n}.svm"
            if not path.exists():
                return path
            n += 1


class SetupGenerator:
    """
    Gera variações de setup baseadas em:
    1. Arquivo .svm base (setup de referência do usuário)
    2. Condição climática (seco/chuva/misto)
    3. Dados da sessão (temp pista, temp ar, umidade)
    4. Histórico de aprendizado da IA (se disponível)
    
    ⚠️ REGRA FUNDAMENTAL:
    - generate() → SEMPRE cria NOVOS arquivos. NUNCA toca no base.
    - edit_existing() → Só quando o usuário EXPLICITAMENTE seleciona
      um arquivo para editar. Cria backup antes.
    
    📝 Nomenclatura: SetorFlow_{clima}_{categoria}_{carro}_{DD-MM-AAAA}.svm
    """

    def __init__(self):
        self.naming = SetorFlowNaming()

    def generate(
        self,
        base_svm: SVMFile,
        conditions: list[WeatherCondition],
        car_category: str,
        car_model: str,
        output_dir: Path,
        session_data: SessionData | None = None,
        use_ai: bool = True,
    ) -> list[GeneratedSetup]:
        """
        LÊ o base → gera NOVOS setups. Base NUNCA é modificado.

        Fluxo interno:
        1. Se use_ai e modelo treinado → IA gera deltas
        2. Se não → heurísticas geram deltas
        3. Aplica interpolação por fator de clima
        4. Safety guards validam os deltas
        5. Cria NOVOS SVMFile com as modificações
        6. Nomeia com padrão SetorFlow + resolve colisões
        7. Salva cada um na pasta da pista
        """
        results = []
        for condition in conditions:
            # Gera nome: SetorFlow_chuva_GT3_Mclaren_31-03-2026.svm
            base_name = self.naming.build_name(condition, car_category, car_model)
            final_path = self.naming.resolve_collision(base_name, output_dir)
            
            # ... gera deltas via IA ou heurísticas ...
            # ... salva novo .svm em final_path ...
            results.append(GeneratedSetup(path=final_path, condition=condition))
        
        return results

    def edit_existing(
        self,
        target_path: Path,
        deltas: dict,
        confirmed: bool = False,
    ) -> Path:
        """
        Edita um arquivo .svm existente que o USUÁRIO SELECIONOU.
        
        ⚠️ Só é chamado quando o usuário clica "Editar Este Setup".
        NUNCA é chamado automaticamente.
        
        1. Cria backup automático (.svm.bak)
        2. Aplica deltas ao arquivo selecionado
        3. Retorna o caminho do arquivo editado
        """
        if not confirmed:
            raise ValueError("Edição requer confirmação explícita do usuário")
        backup = target_path.with_suffix('.svm.bak')
        shutil.copy2(target_path, backup)
        svm = parse_svm(target_path)
        svm = apply_deltas(svm, deltas)
        save_svm(svm, target_path)
        return target_path

    def generate_blended(
        self,
        base_svm: SVMFile,
        dry_weight: float,      # 0.0 a 1.0
        wet_weight: float,      # 0.0 a 1.0
        car_category: str,
        car_model: str,
        output_dir: Path,
        session_data: SessionData | None = None,
    ) -> GeneratedSetup:
        """
        Gera um NOVO setup mesclado com pesos personalizados.
        Ex: 60% seco + 40% chuva → SetorFlow_mescla-60-40_GT3_Mclaren_31-03-2026.svm
        Base NUNCA é modificado.
        """
        pct_dry = int(dry_weight * 100)
        pct_wet = int(wet_weight * 100)
        clima_label = f"mescla-{pct_dry}-{pct_wet}"
        base_name = f"SetorFlow_{clima_label}_{self.naming.sanitize(car_category)}_{self.naming.sanitize(car_model)}_{date.today().strftime('%d-%m-%Y')}"
        final_path = self.naming.resolve_collision(base_name, output_dir)
        # ... gera setup mesclado ...
        return GeneratedSetup(path=final_path)
```

---

### 30.8 DADOS DE SESSÃO — CLASSE `SessionData`

Estrutura para encapsular todos os dados ambientais:

```python
@dataclass
class SessionData:
    """Dados ambientais da sessão atual."""
    rain_current: float        # 0.0–1.0 (intensidade de chuva)
    rain_forecast: float       # 0.0–1.0 (umidade máxima prevista)
    track_temp_c: float        # Temperatura da pista (°C)
    ambient_temp_c: float      # Temperatura do ar (°C)
    cloud_darkness: float      # 0.0–1.0 (escuridão das nuvens)
    wind_speed_ms: float       # Velocidade do vento (m/s)
    wind_direction: tuple      # Vetor X,Z do vento
    track_wetness: float       # 0.0–1.0 (média de umidade da pista)
    session_type: str          # "practice", "qualifying", "race"
    minutes_remaining: float   # Minutos restantes na sessão (relevante para corrida)
    timestamp: datetime        # Momento da captura
```

---

### 30.9 TABELA NO BANCO DE DADOS — SETUPS GERADOS

Nova tabela para rastrear setups gerados pela IA:

```sql
CREATE TABLE IF NOT EXISTS generated_setups (
    gen_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    base_svm_path       TEXT NOT NULL,       -- Caminho do .svm original (NUNCA modificado)
    generated_svm_path  TEXT NOT NULL,       -- Caminho do .svm gerado (NOVO arquivo)
    operation_mode      TEXT DEFAULT 'create', -- "create" = novo arquivo, "edit" = editou existente
    backup_path         TEXT,                -- Caminho do .svm.bak (só para mode="edit")
    car_id              INTEGER REFERENCES cars(car_id),
    track_id            INTEGER REFERENCES tracks(track_id),
    weather_condition   TEXT NOT NULL,       -- "dry_optimized", "heavy_rain", etc.
    interpolation_factor REAL,              -- 0.0 a 1.0
    source              TEXT DEFAULT 'heuristic',  -- "heuristic", "ai", "blended"
    
    -- Dados ambientais no momento da geração
    rain_current        REAL,
    track_temp_c        REAL,
    ambient_temp_c      REAL,
    
    -- Deltas aplicados (JSON serializado)
    deltas_json         TEXT,
    
    -- Feedback do usuário após uso
    user_rating         REAL,              -- -1.0 a +1.0
    laps_used           INTEGER DEFAULT 0,
    avg_lap_time        REAL,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gen_setups_track
    ON generated_setups(track_id, weather_condition);
    
CREATE INDEX IF NOT EXISTS idx_gen_setups_mode
    ON generated_setups(operation_mode);
```

---

### 30.10 MELHORIAS AMPLAS — SUGESTÕES PARA EXPANDIR O SISTEMA

#### 30.10.1 🆕 Setup por Stint / Fase da Corrida

Em corridas longas (Le Mans 24h), as condições mudam ao longo dos stints:
- Stint 1: pneus novos, tanque cheio → setup conservador
- Stint 3: pneus gastos, tanque leve → setup agressivo
- Stint noturno: temperatura mais baixa → ajustar pressões

**Proposta:** Gerar setups por stint, considerando:
- Quantidade de combustível esperada
- Desgaste projetado dos pneus
- Temperatura prevista (dia/noite)

#### 30.10.2 🆕 Comparador Visual de Setups

Interface para comparar visualmente dois ou mais setups lado a lado:

```
┌─────────────────────────────────────────────────────────┐
│  📊 COMPARAÇÃO DE SETUPS                                │
│                                                         │
│  Setup A: meu_setup_seco.svm                            │
│  Setup B: meu_setup_CHUVA.svm                          │
│                                                         │
│  Parâmetro          │  A (Seco) │  B (Chuva) │ Delta   │
│  ────────────────────┼───────────┼────────────┼─────────│
│  Asa Traseira        │  6.0°     │  9.0°      │  +3.0°  │
│  Mola F              │  3        │  1         │  -2     │
│  Camber FL           │  -2.2°    │  -1.5°     │  +0.7°  │
│  Pressão FL          │  136 kPa  │  130 kPa   │  -6 kPa │
│  TC Map              │  5        │  8         │  +3     │
│  ABS Map             │  9        │  11        │  +2     │
│                                                         │
│  [Mesclar A+B (50/50)]  [Criar Variação]  [Exportar]   │
└─────────────────────────────────────────────────────────┘
```

#### 30.10.3 🆕 Presets por Categoria de Carro

Cada categoria (Hypercar, LMP2, GT3) tem comportamentos MUITO diferentes. Criar presets de deltas de chuva por categoria:

| Parâmetro | Hypercar (Chuva) | LMP2 (Chuva) | GT3 (Chuva) |
|-----------|:----------------:|:------------:|:----------:|
| Asa | +3 a +5 | +2 a +4 | +2 a +3 |
| Molas | -2 a -4 | -2 a -3 | -1 a -3 |
| Ride Height | +1 a +2 | +1 a +2 | +1 a +2 |
| Pressão | -4 a -8 kPa | -3 a -6 kPa | -3 a -5 kPa |
| TC | +2 a +4 | +2 a +3 | +1 a +2 |
| Diff | -15 a -25 Nm | -10 a -20 Nm | N/A |

#### 30.10.4 🆕 Auto-detecção de Setup Ideal por Telemetria

Quando o usuário dirige com um setup gerado, a IA monitora:
1. Grip dos pneus → está perdendo aderência? Pressão muito alta/baixa?
2. Temperaturas → pneus esfriando demais (chuva forte)?
3. Aquaplanagem → velocidade cai subitamente sem input do piloto?
4. Estabilidade → o carro está rodando mais do que no seco?

Se detectar problemas, a IA pode sugerir **ajustes em tempo real**:
> "🌧️ Detectei que os pneus FL estão 15°C abaixo do ideal para chuva.
> Sugiro: Pressão FL -2 kPa. Deseja aplicar?"

#### 30.10.5 🆕 Exportação de "Receita" de Setup

Permitir exportar a "receita" (não o .svm, mas as regras) para compartilhar:

```json
{
    "recipe_name": "Silverstone Chuva Forte v2",
    "car_class": "hypercar",
    "track": "Silverstone_National",
    "weather": "heavy_rain",
    "deltas_from_dry": {
        "delta_rw": +5,
        "delta_spring_f": -3,
        "delta_spring_r": -3,
        "delta_pressure_f": -6,
        "delta_pressure_r": -5,
        "delta_tc_map": +3,
        "delta_abs_map": +2
    },
    "notes": "Funciona bem com GR010. Cuidado com oversteer na Maggots.",
    "author": "Piloto1",
    "avg_improvement_pct": 2.3,
    "created_at": "2026-03-31T15:45:00"
}
```

Outros usuários importam a receita e aplicam sobre seus próprios setups base.

---

### 30.11 DIAGRAMA COMPLETO DO FLUXO

```
   ┌─────────────────────────────────────────────────────────────┐
   │  MODO CRIAR (padrão)              MODO EDITAR (explícito)   │
   │  ──────────────────               ─────────────────────     │
   │  Usuário seleciona BASE           Usuário seleciona ARQUIVO │
   │  🔒 Base = SOMENTE LEITURA        e clica "Editar"          │
   └──────────┬──────────────────────────────┬───────────────────┘
              │                              │
              ▼                              ▼
    ┌──────────────────┐           ┌──────────────────┐
    │  parse_svm()     │           │  parse_svm()     │
    │  LÊ o base       │           │  LÊ o arquivo    │
    │  (NÃO modifica!) │           │  selecionado     │
    └────────┬─────────┘           └────────┬─────────┘
             │                              │
    ┌────────┼────────────┐                 │
    ▼        ▼            ▼                 ▼
 ┌────────┐ ┌─────────┐ ┌──────────┐  ┌──────────────┐
 │Heurís- │ │ IA (NN) │ │ Sessão   │  │ IA/Heurís-   │
 │ticas   │ │ predict │ │ Clima    │  │ ticas sugerem│
 │clima   │ │         │ │ Dados    │  │ deltas       │
 └───┬────┘ └───┬─────┘ └────┬─────┘  └──────┬───────┘
     │          │             │               │
     └─────┬────┘             │               ▼
           │                  │        ┌──────────────┐
           ▼                  ▼        │ PREVIEW das  │
    ┌────────────────────────────┐     │ mudanças     │
    │   setup_generator.py       │     │ (confirmar?) │
    │                            │     └──────┬───────┘
    │ 1. Combina heurísticas+IA  │            │
    │ 2. Aplica fator de clima   │        ┌───┴───┐
    │ 3. Interpola por cenário   │        │Backup │
    │ 4. Valida via safety.py    │        │.bak   │
    └──────────┬─────────────────┘        └───┬───┘
               │                              │
     ┌─────────┼─────────┐                   ▼
     ▼         ▼         ▼          ┌────────────────┐
  ┌────────┐┌────────┐┌────────┐    │ Edita o arquivo│
  │🆕 NOVO ││🆕 NOVO ││🆕 NOVO │    │ selecionado    │
  │SECO_OPT││CHUVA   ││MISTO   │    │ (já c/ backup) │
  │.svm    ││.svm    ││.svm    │    └────────────────┘
  └───┬────┘└───┬────┘└───┬────┘
      │         │         │
      └─────────┼─────────┘
                │
                ▼
     ┌─────────────────────┐
     │ save_new()           │
     │ Salva NOVOS arquivos │
     │ na pasta da pista    │
     │ ⚠️ NUNCA sobrescreve │
     │ Se nome existe →     │
     │ adiciona _2, _3...   │
     └─────────────────────┘
                │
                ▼
       🔒 BASE INTACTO ✅
```

---

### 30.12 NOVOS RISCOS IDENTIFICADOS (v5)

| # | Risco | Prob. | Impacto | Mitigação |
|---|-------|:-----:|:-------:|-----------|
| 13 | Deltas de chuva heurísticos podem não funcionar para todos os carros | 🟡 Média | 🟡 Médio | Presets por categoria + aprendizado da IA |
| 14 | Interpolação linear pode não ser ideal (relação não-linear entre parâmetros) | 🟡 Média | 🟢 Baixo | IA aprende relações não-lineares com dados |
| 15 | Dados de clima na Shared Memory podem ter delay | 🟢 Baixa | 🟢 Baixo | Capturar com frequência e fazer média |
| 16 | Muitos arquivos .svm gerados podem confundir o usuário | 🟡 Média | 🟡 Médio | Interface de gerenciamento + limpeza automática de versões antigas |
| 17 | `CompoundSetting` (seco vs chuva) é binário, não interpolável | 🟢 Específica | 🟡 Médio | Tratar compound separado: seco→`DRY`, chuva→`WET`, misto→perguntar ao usuário |

---

### 30.13 PONTOS DE DECISÃO (v5)

### ❓ Pergunta 13: Geração Automática vs Manual
- **Opção A:** O sistema detecta chuva e SUGERE automaticamente trocar setup → usuário confirma
- **Opção B:** O usuário sempre inicia a geração manualmente clicando "Gerar Setup de Chuva"
- **Opção C:** Ambos (sugere automaticamente, mas também tem botão manual) — **recomendado**

### ❓ Pergunta 14: Compound de Pneu
- **Opção A:** A IA troca automaticamente o CompoundSetting para WET quando chuva ≥ 0.5
- **Opção B:** O usuário sempre escolhe o compound (seco/chuva/intermediário)
- **Opção C:** A IA sugere, mas o usuário confirma — **recomendado**

### ❓ Pergunta 15: Número de Variações
- **Opção A:** Gerar todas as 5 variações automaticamente (seco, chuva leve, misto, etc.)
- **Opção B:** Usuário seleciona quais variações quer gerar (checkbox)
- **Opção C:** Opção B como padrão, com botão "Gerar Todas" — **recomendado**

### ❓ Pergunta 16: Limite de Arquivos por Pista
- **Opção A:** Sem limite (pode gerar quantos quiser)
- **Opção B:** Limite de 10 setups por pista (com opção de deletar antigos)
- **Opção C:** Sem limite, mas com aviso quando passa de 10 — **recomendado**

---

### 30.14 CONCLUSÃO DO SISTEMA DE CRIAÇÃO DE SETUPS (v5)

| Critério | Status |
|----------|:------:|
| Criar .svm a partir de arquivo base | ✅ Viável — `svm_parser.py` já faz parse/save |
| Detectar condições climáticas | ✅ Viável — dados disponíveis na Shared Memory |
| Gerar setups para diferentes climas | ✅ Viável — heurísticas + interpolação |
| Treinar IA com dados climáticos | ✅ Viável — adicionar 8 inputs de clima |
| Salvar na pasta correta da pista | ✅ Viável — `config.py` já detecta caminhos LMU |
| Gerar múltiplas variações | ✅ Viável — loop sobre `WeatherCondition` |
| Mesclar setups (ex: 60% seco + 40% chuva) | ✅ Viável — interpolação linear com arredondamento |
| Comparar setups visuais | ✅ Viável — widget de comparação na GUI |
| Presets por categoria de carro | ✅ Viável — `CLASS_CONFIG` em `heuristics.py` já existe |

**Módulos que precisam ser criados/modificados:**

| Módulo | Ação | Complexidade |
|--------|------|:----------:|
| `core/setup_generator.py` | 🆕 Criar | 🔴 Alta |
| `core/weather.py` | 🆕 Criar (captura + previsão de clima) | 🟡 Média |
| `core/heuristics.py` | ✏️ Adicionar regras de clima por categoria | 🟡 Média |
| `core/brain.py` | ✏️ Adicionar 8 inputs de clima (38→46) | 🟢 Baixa |
| `core/normalizer.py` | ✏️ Atualizar para 46 features | 🟢 Baixa |
| `data/svm_parser.py` | ✅ Já funciona (parse + save) | — |
| `gui/tab_setup_gen.py` | 🆕 Criar aba de geração de setups | 🔴 Alta |
| `gui/tab_files.py` | ✏️ Adicionar comparador visual | 🟡 Média |
| `data/schema.sql` | ✏️ Adicionar tabela `generated_setups` | 🟢 Baixa |
| `adapter/sm_bridge.py` | ✏️ Adicionar leitura de dados de clima | 🟢 Baixa |

**Fases de implementação propostas:**

| Fase | Escopo | Prioridade |
|------|--------|:----------:|
| **3A** | `setup_generator.py` + heurísticas de clima + aba básica na GUI | 🔴 Alta |
| **3B** | Inputs de clima na IA + treinamento com dados climáticos | 🟡 Média |
| **3C** | Comparador visual + receitas exportáveis + setup por stint | 🟢 Baixa |

---

*Relatório atualizado em 31/03/2026. Aguardo aprovação e escolhas nas perguntas 13-16 para iniciar implementação.*
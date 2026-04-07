# 🧠 RELATÓRIO — Sugestões de Melhoria no Sistema de Aprendizagem
**Data:** Abril 2026 | **Status:** Aguardando Aprovação

---

## 📋 O QUE FOI ANALISADO

Foram lidos todos os módulos de IA do projeto:

| Arquivo | Função |
|---------|--------|
| `core/brain.py` | Rede neural MLP (49 entradas, saída Tanh) |
| `core/trainer.py` | Loop de treinamento com loss ponderada por reward |
| `core/reward.py` | Reward multi-critério (9 componentes) |
| `core/heuristics.py` | Regras deterministicas de engenharia |
| `core/normalizer.py` | StandardScaler incremental (Welford) |
| `core/safety.py` | Validação e clipping dos deltas |
| `core/knowledge_distiller.py` | Destilação LLM → rede neural |

---

## 🔍 PROBLEMAS IDENTIFICADOS

### P1 — Rede neural `brain.py`: Arquitetura Fixa
A rede tem sempre **256 → 128 → 64** neurônios, não importa se é GT3 com 8 outputs (básico) ou Hypercar avançado com 45 outputs.
- Para básico com 8 saídas: a rede é grande demais, vai fazer overfitting com poucos dados.
- Para avançado com 45 saídas: pode ser pequena demais para capturar toda a complexidade.

### P2 — `trainer.py`: Treino offline com apenas 50 épocas
O treino offline usa `epochs=50`. Para carros com poucos dados (<100 amostras), isso é insuficiente para convergência. Para carros com muitos dados, pode ser excessivo e lento.

### P3 — `trainer.py`: Target invertido para reward negativo
Quando `reward < 0`, o código **inverte o target** (`output = -output`). Isso é perigoso: se a IA sugeriu `delta_rw = +2` e foi ruim, ela aprende que deveria ter sugerido `delta_rw = -2` — mas talvez a resposta correta seja `delta_rw = 0`. Inversão cega não é aprendizagem correta.

### P4 — `reward.py`: Peso do lap time apenas 25%
O reward dá 25% para melhoria de tempo de volta — mas o tempo é o principal objetivo. Os outros 75% (grip, wear, fuel...) são importantes, mas secundários. Na prática, a IA pode aprender a "gerenciar pneus" em vez de ir mais rápido.

### P5 — `normalizer.py`: Normalizer reseta ao atingir 100.000 amostras
O `soft_reset` acontece quando `_count > 100_000` e mantém apenas 20% do peso histórico. Para um piloto que joga muito, isso significa que dados de sessões antigas (talvez de pistas específicas) perdem muito peso, podendo desfazer aprendizagem consolidada.

### P6 — `heuristics.py`: Sem thresholds por pista
As regras heurísticas usam thresholds genéricos de temperatura/pressão (`temp_target_c: [85, 100]` para Hypercar). Mas esses valores variam muito por pista: em Le Mans (reta longuíssima) os pneus chegam a 110°C facilmente. Sem calibração por pista, as heurísticas geram alertas falsos.

### P7 — `brain.py`: Sem memória temporal (stateless)
A rede MLP é completamente **stateless** — cada previsão é independente. Ela não "lembra" que as últimas 3 sugestões foram todas de reduzir camber, por exemplo. Um padrão temporal poderia ajudar muito.

### P8 — `trainer.py`: Augmentation sem validação de segurança
A função `_augment_data` gera dados sintéticos somando ruído gaussiano. Esses dados sintéticos passam direto para o treinamento sem passar pelo safety guard `validate_deltas`. Pode ensinar valores impossíveis.

---

## 💡 SUGESTÕES DE MELHORIA

---

### 🔧 MELHORIA 1 — Arquitetura Adaptativa por Nível/Classe

**Arquivo:** `core/brain.py`

**Problema:** Tamanho fixo não é ideal para todos os casos.

**Proposta:** Definir arquitetura em função do nível e classe:

```python
ARCHITECTURE_BY_LEVEL = {
    # (camadas_ocultas, neurônios)
    "basic":        [(128, 64)],           # Pequena — evita overfitting com 8 saídas
    "intermediate": [(256, 128, 64)],      # Atual — adequada para 20 saídas
    "advanced":     [(512, 256, 128, 64)], # Grande — necessária para 45 saídas
}

# Bonus de capacidade para carros híbridos complexos (Hypercar)
CLASS_CAPACITY_BONUS = {
    "hypercar": 1.5,  # 50% mais neurônios — mais variáveis de energia
    "lmp2":     1.0,
    "lmp3":     0.8,
    "gte":      1.0,
    "gt3":      0.9,
}
```

**Impacto:** Menos overfitting no nível básico; melhor capacidade no avançado para Hypercars com híbrido.

---

### 🔧 MELHORIA 2 — Loss `IGNORE` para Reward Negativo

**Arquivo:** `core/trainer.py`

**Problema:** Inverter target para reward negativo (`output = -output`) é incorreto.

**Proposta:** Quando o reward é negativo, usar **peso zero** (ignorar o dado) ou usar **loss contrastiva** que afasta a predição do target errado sem forçar direção oposta:

```python
if reward < -0.3:
    # Dado claramente prejudicial — ignorar no treinamento
    weight = 0.0
elif reward < 0:
    # Leve negativo — penalizar com peso pequeno
    weight = abs(reward) * 0.2
else:
    # Positivo — reforçar normalmente
    weight = max(reward, 0.05)
```

**Impacto:** Evita que a IA aprenda direções erradas. Mantém apenas dados informativos e confiáveis.

---

### 🔧 MELHORIA 3 — Épocas Adaptativas no Treino Offline

**Arquivo:** `core/trainer.py`

**Problema:** 50 épocas fixas — pode ser pouco ou demais.

**Proposta:** Calcular épocas com base na quantidade de dados:

```python
def _compute_epochs(self, num_samples: int) -> int:
    """Épocas inversamente proporcionais ao volume de dados."""
    if num_samples < 50:
        return 200   # Poucos dados: mais épocas para aprender
    if num_samples < 200:
        return 100
    if num_samples < 1000:
        return 50    # Padrão atual
    return 30        # Muitos dados: menos épocas, evitar overfitting
```

**Impacto:** Carros novos com poucos dados convertem melhor. Carros experientes treinam mais rápido.

---

### 🔧 MELHORIA 4 — Rebalancear Pesos do Reward

**Arquivo:** `core/reward.py`

**Problema:** Lap time com apenas 25% do peso.

**Proposta:** Dois perfis de reward conforme o tipo de sessão:

```python
REWARD_WEIGHTS_RACE = {
    "lap_time":         0.25,   # Tempo importa, mas durabilidade também
    "tire_wear":        0.20,   # Desgaste crítico em corridas longas
    "sector_improvement": 0.15,
    "temp_balance":     0.12,
    "consistency":      0.10,
    "fuel_efficiency":  0.08,
    "grip":             0.05,
    "user_satisfaction": 0.03,
    "brake_health":     0.02,
}

REWARD_WEIGHTS_QUALY = {
    "lap_time":          0.45,  # Tempo é REI na qualy
    "sector_improvement": 0.20,
    "grip":              0.15,
    "temp_balance":      0.10,
    "consistency":       0.05,
    "user_satisfaction": 0.03,
    "tire_wear":         0.01,
    "fuel_efficiency":   0.01,
    "brake_health":      0.00,
}
```

**Impacto:** IA otimiza corretamente para cada modo: va rápido na qualy, cuida do carro na corrida longa.

---

### 🔧 MELHORIA 5 — Normalizer com Memória por Pista

**Arquivo:** `core/normalizer.py`

**Problema:** Um único normalizer global não diferencia que Le Mans tem velocidades muito diferentes de Monaco.

**Proposta:** Salvar e carregar o normalizer por combinação `carro×pista`, junto com o modelo `.pth`:

```python
# Ao iniciar sessão:
normalizer.load(f"models/{car_id}/normalizer_{track_id}.npz")

# Ao terminar sessão:
normalizer.save(f"models/{car_id}/normalizer_{track_id}.npz")
```

**Benefício adicional:** O soft_reset passa a afetar apenas o normalizer daquela pista, não descartando aprendizagem de outras pistas.

---

### 🔧 MELHORIA 6 — Heurísticas com Calibração por Pista

**Arquivo:** `core/heuristics.py`

**Problema:** `temp_target_c: (85, 100)` fixo para Hypercar independente da pista.

**Proposta:** Adicionar ajuste por tipo de pista ao `CLASS_CONFIG`:

```python
TRACK_TYPE_TEMP_ADJUSTMENT = {
    "street":      {"tire_temp": +5,  "brake_temp": +20},  # Monaco, etc.
    "permanent":   {"tire_temp":  0,  "brake_temp":   0},  # Padrão
    "high_speed":  {"tire_temp": +8,  "brake_temp": +30},  # Le Mans, Spa
    "slow_chicane":{"tire_temp": -5,  "brake_temp": -10},
}
```

Esse ajuste já existe na tabela `tracks` do banco (`track_type`). Só precisa de conexão.

**Impacto:** Menos alertas falsos. "Pneu quente em Le Mans" deixa de ser tratado como problema.

---

### 🔧 MELHORIA 7 — Safety Guard na Data Augmentation

**Arquivo:** `core/trainer.py`

**Problema:** Dados sintéticos não passam pelo `validate_deltas`.

**Proposta:** Aplicar validação mínima:

```python
def _augment_data(self, data: list[dict]) -> list[dict]:
    augmented = []
    for sample in data:
        new_output = sample["output"] + np.random.normal(0, 0.05, size=sample["output"].shape)
        # Garantir que outputs ficam no range [-1, +1] (saída Tanh)
        new_output = np.clip(new_output, -1.0, 1.0)
        # Peso menor para sintéticos
        augmented.append({**sample, "output": new_output, "weight": sample["weight"] * 0.5})
    return data + augmented
```

**Impacto:** Dados sintéticos não ensinam valores fisicamente impossíveis.

---

### 🔧 MELHORIA 8 — Score de Confiança por Parâmetro

**Arquivo:** `core/brain.py` + `core/trainer.py`

**Proposta (nova funcionalidade):** Calcular um "confiança" individual por parâmetro de saída, baseado em quantas amostras de treinamento afetaram aquele parâmetro:

```python
# Ao gerar sugestão:
confidence_per_param = {
    "delta_rw": 0.92,        # Muito dado → alta confiança
    "delta_spring_f": 0.75,
    "delta_tc_map": 0.30,    # Poucos dados → baixa confiança
}
# Na GUI: mostrar ★★★☆☆ ao lado de cada parâmetro
```

**Impacto:** Usuário sabe em quais ajustes confiar mais. Parâmetros com baixa confiança mostram um aviso "⚠️ pouca experiência com este parâmetro".

---

## 📊 RANKING DE IMPACTO × ESFORÇO

| # | Melhoria | Impacto | Esforço | Prioridade |
|---|----------|---------|---------|-----------|
| 2 | Loss IGNORE para reward negativo | 🔴 Alto | 🟢 Baixo | **1ª** |
| 4 | Rebalancear pesos por modo (race/qualy) | 🔴 Alto | 🟢 Baixo | **2ª** |
| 7 | Safety guard na augmentation | 🟡 Médio | 🟢 Baixo | **3ª** |
| 3 | Épocas adaptativas | 🟡 Médio | 🟢 Baixo | **4ª** |
| 5 | Normalizer por pista | 🔴 Alto | 🟡 Médio | **5ª** |
| 1 | Arquitetura adaptativa | 🟡 Médio | 🟡 Médio | **6ª** |
| 6 | Heurísticas calibradas por pista | 🟡 Médio | 🟡 Médio | **7ª** |
| 8 | Score de confiança por parâmetro | 🟢 Baixo | 🔴 Alto | **último** |

---

## ✅ RECOMENDAÇÃO

Implementar as melhorias **1, 2, 3 e 4** juntas — todas de baixo esforço e alto impacto:
- Resolve o principal bug de aprendizagem (inversão de target para reward negativo)
- Melhora imediatamente a qualidade das sugestões em race vs qualy
- Sem risco de regressão

**Aguardando aprovação.**

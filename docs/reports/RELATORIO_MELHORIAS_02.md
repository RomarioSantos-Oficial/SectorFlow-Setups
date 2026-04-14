# RELATÓRIO DE ANÁLISE — PROPOSTAS 02.txt
### SectorFlow Setups — Comparação com Estado Atual do Código
**Data:** Julho 2025 | **Versão analisada:** pós Item-E (01.txt completo)

---

## SUMÁRIO EXECUTIVO

O arquivo `02.txt` contém **17 propostas** distribuídas em 7 grupos. Após análise
completa do código atual, o resultado é:

| Grupo | Propostas | ✅ Já existe | ⚡ Parcial | ❌ Não existe |
|-------|-----------|-------------|-----------|--------------|
| 1 — Reward System | 4 | 0 | 1 | 3 |
| 2 — Captura Geográfica | 2 | 0 | 0 | 2 |
| 3 — Combustível Inteligente | 4 | 0 | 1 | 3 |
| 4 — Nomenclatura de Arquivo | 2 | 0 | 1 | 1 |
| 5 — Quali vs Race | 1 | 0 | 0 | 1 |
| 6 — Safety / Dependências Aero | 1 | 0 | 0 | 1 |
| 7 — Classe de Carro (Inteligência por Categoria) | 1 | 0 | 0 | 1 |

**Recomendação geral:** Aprovar e implementar todos os 17 itens em 3 fases
priorizadas por impacto imediato e complexidade.

---

## GRUPO 1 — SISTEMA DE REWARD

### G1.1 — Nova função `_reward_top_speed()`

**O que o 02.txt propõe:**
```python
def _reward_top_speed(max_speed_current: float,
                      max_speed_best: float,
                      threshold_kmh: float = 2.0) -> float:
    delta_speed = max_speed_current - max_speed_best
    if abs(delta_speed) < threshold_kmh:
        return 0.0
    reward = delta_speed / 10.0
    return max(-1.0, min(1.0, reward))
```
Lógica: se o setup novo baixou a velocidade de reta em mais de 2 km/h, penaliza.

**Estado atual do código:**
> `_reward_top_speed()` **NÃO EXISTE** em `core/reward.py`.
> Existe `LapAccumulator.max_speed` em `data/telemetry_reader.py` (captura global).
> O `compute_reward()` recebe 14 parâmetros mas **nenhum é velocidade máxima**.

**Gap identificado:** Função ausente + parâmetro ausente em `compute_reward()`.

**Impacto:** Sem isso a IA pode sugerir asas maiores que cortam a velocidade de reta
em 10-15 km/h e receber reward positivo apenas porque o lap time baixou um pouco.
Em corridas, esse setup cria um carro facilmente ultrapassável nas retas.

**Complexidade de implementação:** ⭐ Baixa  
**Valor estratégico:** ⭐⭐⭐⭐ Alto — mudança fundamental na forma como a IA aprende  
**Status:** ❌ IMPLEMENTAR

---

### G1.2 — Atualização dos pesos `REWARD_WEIGHTS`

**O que o 02.txt propõe:**
```python
REWARD_WEIGHTS = {
    "lap_time": 0.20,          # Reduzido de 0.25
    "top_speed": 0.15,         # NOVO
    "temp_balance": 0.15,
    "grip": 0.10,
    "consistency": 0.10,
    "user_satisfaction": 0.10,
    "tire_wear": 0.10,
    "sector_improvement": 0.10
}
```

**⚠️ ALERTA CRÍTICO — REGRESSÃO:**
O dicionário proposto **REMOVE** `fuel_efficiency` e `brake_health`, que já foram
implementados nas iterações anteriores:
```python
# ESTADO ATUAL (correto, soma = 1.0)
"fuel_efficiency": 0.05,   # implementado — deve ser mantido
"brake_health": 0.05,      # implementado — deve ser mantido
```
Adotar o dicionário do 02.txt na íntegra seria uma **regressão de features**.

**Solução recomendada — pesos balanceados sem remover features:**
```python
REWARD_WEIGHTS = {
    "lap_time": 0.20,          # Reduzido de 0.25
    "top_speed": 0.13,         # NOVO (levemente menor que proposta para caber tudo)
    "temp_balance": 0.13,      # Reduzido de 0.15
    "grip": 0.10,
    "consistency": 0.10,
    "user_satisfaction": 0.10,
    "tire_wear": 0.10,
    "sector_improvement": 0.09,# Reduzido de 0.10
    "fuel_efficiency": 0.03,   # Mantido, reduzido de 0.05
    "brake_health": 0.02,      # Mantido, reduzido de 0.05
}
# TOTAL = 1.00 ✓ — 10 critérios preservados
```

**Complexidade de implementação:** ⭐ Muito Baixa  
**Valor estratégico:** ⭐⭐⭐ Médio  
**Status:** ⚡ IMPLEMENTAR COM AJUSTE (não remover features existentes)

---

### G1.3 — Multiplicador por perfil de pista

**O que o 02.txt propõe:**
```python
if track_info["downforce_priority"] == "Very-Low":
    multiplier = 2.0   # Monza: penalidade duplicada por perder velocidade
elif track_info["downforce_priority"] == "High":
    multiplier = 0.5   # Mônaco: velocidade de reta quase irrelevante
speed_reward = _reward_top_speed(curr_speed, best_speed) * multiplier
```

**Estado atual do código:**
> `TRACK_POIS` dict **NÃO EXISTE** em nenhum arquivo.
> `tracks` tabela no BD tem `track_type TEXT` mas sem `downforce_priority`.
> Nenhum multiplicador dinâmico existe em `compute_reward()`.

**Dependência:** Requer implementar G2.1 (`TRACK_POIS` dict) antes.

**Complexidade de implementação:** ⭐⭐ Baixa-Média  
**Valor estratégico:** ⭐⭐⭐⭐ Alto — contextualiza reward por tipo de pista  
**Status:** ❌ IMPLEMENTAR (após G2.1)

---

### G1.4 — Refatoração de `_reward_fuel_efficiency()`

**O que o 02.txt propõe:**
```python
def _reward_fuel_efficiency(fuel_consumed: float,
                            target_avg_consumed: float) -> float:
    # Compara versus a MÉDIA HISTÓRICA da pista/carro
    delta_pct = (fuel_consumed - target_avg_consumed) / target_avg_consumed
    reward = -delta_pct * 5.0
    return max(-1.0, min(1.0, reward))
```

**Estado atual do código (`core/reward.py` linhas 297-308):**
```python
def _reward_fuel_efficiency(fuel_before: float,
                            fuel_after: float) -> float:
    # Compara volta ANTERIOR vs NOVA (mede setup change, não média histórica)
    delta_pct = (fuel_after - fuel_before) / fuel_before
    return max(-1.0, min(1.0, -delta_pct * 10.0))
```

**Diferenças:**
1. **Parâmetros:** `fuel_before/after` (voltabais/atual) → `fuel_consumed/target_avg` (vs. média histórica)
2. **Multiplicador:** `×10.0` → `×5.0` (menos agressivo)
3. **Lógica conceitual:** medir variação entre setups → medir eficiência relativa ao histórico da pista

A versão atual com `×10.0` penaliza muito fortemente qualquer variação de consumo entre
setups, mesmo que ambos sejam muito eficientes. A proposta do 02.txt é mais robusta.

**Complexidade de implementação:** ⭐ Baixa  
**Valor estratégico:** ⭐⭐⭐ Médio  
**Status:** ⚡ IMPLEMENTAR (mudança de parâmetros + divisor)

---

## GRUPO 2 — CAPTURA GEOGRÁFICA DE VELOCIDADE

### G2.1 — Dicionário `TRACK_POIS` (Track Points of Interest)

**O que o 02.txt propõe:**
```python
TRACK_POIS = {
    "FUJI_SPEEDWAY": {
        "main_straight_start": 0.85,
        "main_straight_end": 0.05,
        "critical_corner": "Last Corner",
        "downforce_priority": "Medium-Low"
    },
    "MONZA": {
        "main_straight_start": 0.90,
        "main_straight_end": 0.10,
        "downforce_priority": "Very-Low"
    }
}
```

**Estado atual do código:**
> **NÃO EXISTE** em nenhum arquivo do projeto.
> A tabela `tracks` tem `track_type TEXT` mas sem zonas de velocidade.
> Pode ser definido como constante em `core/reward.py` ou `data/database.py`.

**Onde incluir:** Criar como constante em `core/reward.py` ou em novo arquivo
`core/track_profiles.py` para manter separação de responsabilidades.

**Complexidade de implementação:** ⭐ Muito Baixa (apenas adicionar dict)  
**Valor estratégico:** ⭐⭐⭐ Médio (base para G1.3 e G2.2)  
**Status:** ❌ IMPLEMENTAR (pré-requisito para outros itens)

---

### G2.2 — `max_straight_speed` via `mInLapDistPct`

**O que o 02.txt propõe:**
```python
# Em telemetry_reader.py — dentro do _sample_tick ou similar
current_pos = telemetry.mInLapDistPct
if track_config:
    start = track_config["main_straight_start"]
    end = track_config["main_straight_end"]
    is_on_straight = (current_pos >= start or current_pos <= end)  # reta que cruza S/F
    if is_on_straight:
        self.current_lap_max_straight_speed = max(
            self.current_lap_max_straight_speed,
            telemetry.mSpeed * 3.6
        )
```

**Estado atual do código:**
> `LapAccumulator.max_speed` captura a velocidade máxima **em qualquer ponto da pista**.
> `mInLapDistPct` **NÃO é lido** no `_sample_tick()` atual.
> `max_straight_speed` **NÃO EXISTE** em `LapSummary`.

**Por que isso importa:** Velocidade máxima em qualquer lugar pode ser em uma descida
ou em uma saída de curva. Medir especificamente na reta principal é o "Speed Trap" real
que os engenheiros usam. Evita que uma descida de Spa "engane" a IA sobre o arrasto real.

**Dependência:** Requer G2.1 (TRACK_POIS) para saber onde é a reta.

**Complexidade de implementação:** ⭐⭐ Média  
**Valor estratégico:** ⭐⭐⭐⭐ Alto  
**Status:** ❌ IMPLEMENTAR

---

## GRUPO 3 — COMBUSTÍVEL INTELIGENTE

### G3.1 — `get_fuel_ratio()` em `svm_parser.py`

**O que o 02.txt propõe:**
```python
def get_fuel_ratio(self) -> float:
    # Parseia "FuelSetting=95//100.0L" → retorna 100.0/95 = 1.0526 L/clique
    line = self.get_line("FuelSetting")
    parts = line.split("//")
    indice_atual = float(parts[0].split("=")[1])
    valor_real = float(re.findall(r"[-+]?\d*\.\d+|\d+", parts[1])[0])
    if indice_atual > 0:
        return valor_real / indice_atual
    return 1.0
```

**Estado atual do código:**
> `get_fuel_ratio()` **NÃO EXISTE** em `data/svm_parser.py`.
> `SVMFile.get_param("GENERAL.FuelSetting")` retorna o índice mas sem cálculo de litros.
> O sistema atualmente não distingue escala entre: Ginetta LMP3 (`95//100.0L`) e
> McLaren GT3 (`59//0.60`) — que são formatos completamente diferentes.

**Problema real:** O 02.txt confirma o que o código ainda não resolve — cada carro usa
sua própria escala de FuelSetting. Usar o mesmo índice para carros diferentes causará
abastecimento errado.

**Complexidade de implementação:** ⭐ Baixa  
**Valor estratégico:** ⭐⭐⭐⭐⭐ Muito Alto — crítico para qualquer cálculo de combustível  
**Status:** ❌ IMPLEMENTAR com alta prioridade

---

### G3.2 — `set_fuel_liters()` em `svm_parser.py`

**O que o 02.txt propõe:**
```python
def set_fuel_liters(self, litros_desejados: float) -> None:
    ratio = self.get_fuel_ratio()
    novo_indice = int(litros_desejados / ratio)
    self.update_parameter("GENERAL", "FuelSetting", novo_indice)
```

**Estado atual do código:**
> `set_fuel_liters()` **NÃO EXISTE**.
> Para mudar combustível o código atual precisaria calcular o índice manualmente e
> chamar `apply_deltas()` com delta relativo ao índice atual — processo propenso a erro.

**Dependência:** Requer G3.1 (`get_fuel_ratio()`).

**Complexidade de implementação:** ⭐ Muito Baixa  
**Valor estratégico:** ⭐⭐⭐⭐ Alto  
**Status:** ❌ IMPLEMENTAR

---

### G3.3 — Compensação automática ride height por combustível

**O que o 02.txt propõe:**
```python
def calculate_fuel_compensation(fuel_delta: float) -> dict:
    """Para cada 10L adicionados, +1 clique de Ride Height em todas as rodas."""
    rh_adjustment = int(fuel_delta / 10)
    return {
        "ride_height_fl": rh_adjustment,
        "ride_height_fr": rh_adjustment,
        "ride_height_rl": rh_adjustment,
        "ride_height_rr": rh_adjustment,
    }
```

**Estado atual do código:**
> **NÃO EXISTE** em nenhum arquivo.
> `main.py` não aplica compensação de ride height quando muda combustível.
> O setup `apply_deltas()` em `svm_parser.py` modifica parâmetros mas sem lógica
> de dependências físicas entre eles.

**Por que isso importa:** 100L de combustível adicionam ~100kg no carro. Sem ajuste
de ride height, o assoalho bate no chão nas primeiras voltas da corrida, destruindo
a aerodinâmica. Esse é um dos erros mais comuns de setups gerados por IA sem física.

**Complexidade de implementação:** ⭐ Muito Baixa  
**Valor estratégico:** ⭐⭐⭐⭐⭐ Muito Alto — evita falhas físicas graves  
**Status:** ❌ IMPLEMENTAR

---

### G3.4 — Estimativa de voltas pelo consumo das últimas 3 voltas

**O que o 02.txt propõe:**
```python
total_laps_estimated = current_fuel / avg_consumption_last_3_laps
```

**Estado atual do código:**
> Em `main.py` (função de estratégia, ~linha 1060-1100), existe cálculo de
> `estimated_laps` usando `fuel_per_lap`. Porém, o `fuel_per_lap` é calculado
> como média de **todas** as voltas disponíveis, não especificamente as últimas 3.
> A lógica de filtrar por "últimas 3" para ser mais responsiva a mudanças de ritmo
> **não está implementada explicitamente**.

**Complexidade de implementação:** ⭐ Muito Baixa  
**Valor estratégico:** ⭐⭐ Médio  
**Status:** ⚡ IMPLEMENTAR (ajuste pontual no cálculo existente)

---

## GRUPO 4 — NOMENCLATURA DE ARQUIVO

### G4.1 — Padrão `SECTORFLOW_[CLIMA]_[CAT+MARCA]_[PISTA]_[DATA]_[V#]_[MODO].svm`

**O que o 02.txt propõe:**
```
SECTORFLOW_DRY_LMP3GIN_FUJ_0704_V1_Q.svm
SECTORFLOW_WET_GT3PORC_INT_0704_V1_RS.svm
```
Formato: `SECTORFLOW_{CLIMA}_{CAT}{MARCA}_{PISTA}_{DDMM}_{V#}_{MODO}.svm`

**Estado atual do código (`main.py`, `_generate_setorflow_path()`):**
```python
# FORMATO ATUAL
f"SetorFlow_{sanitize(clima_str)}_{sanitize(car_class)}_{sanitize(car_name)}_{date_str}"
# Exemplo: SetorFlow_seco_LMP3_Ginetta_LMP3_04-07-2025.svm
```

**Diferenças:**
1. Prefixo: `SetorFlow` → `SECTORFLOW` (maiúsculas, sem acento)
2. Estrutura: Classe e Carro separados → concatenados (`LMP3GIN`)
3. Data: `DD-MM-YYYY` → `DDMM` (sem ano, mais curto)
4. Versão: Sem versionamento → `_V1_`, `_V2_` (controle de versão)
5. Modo: Sem sufixo → `_Q` (Quali), `_R` (Race), `_QA` (Quali Agressivo)
6. Abreviações: sem dict → dicts de marcas e pistas

**Complexidade de implementação:** ⭐ Baixa  
**Valor estratégico:** ⭐⭐⭐ Médio — padronização + identidade da ferramenta  
**Status:** ⚡ REFATORAR `_generate_setorflow_path()` com novo formato

---

### G4.2 — Auto-escrita do campo `Notes=` no .svm

**O que o 02.txt propõe:**
```
Notes="SectorFlow: Setup de Corrida Seguro. 45 voltas. Clima: Chuva. Temp Pista: 22C."
```
O campo `Notes=` no arquivo `.svm` deve ser escrito automaticamente com metadados
da sessão ao salvar.

**Estado atual do código:**
> `save_svm()` em `data/svm_parser.py` preserva linhas `raw_lines` sem modificar
> o campo `Notes=`. Não existe lógica para inserir ou atualizar esse campo.

**Complexidade de implementação:** ⭐ Baixa  
**Valor estratégico:** ⭐⭐ Médio — facilita identificar setups sem abrir o jogo  
**Status:** ❌ IMPLEMENTAR

---

## GRUPO 5 — PERFIL QUALI vs RACE

### G5.1 — Auto-geração de setup de corrida a partir do setup de quali

**O que o 02.txt propõe:**
Quando salva um setup de quali, o sistema oferece gerar automaticamente o equivalente
de corrida com os seguintes offsets:

| Parâmetro | Ajuste | Motivo |
|-----------|--------|--------|
| `RideHeightSetting` F+R | +2 a +3 cliques | Compensar peso do combustível |
| `CamberSetting` | -1 a -2 índices | Preservar pneus no long run |
| `BrakeDuctSetting` | +2 a +3 cliques | Evitar fade nos freios |
| `SpringSetting` | -1 clique (suavizar) | Compensar peso extra + desgaste |

**Estado atual do código:**
> Em `main.py` o parâmetro `mode: "quali" ou "race"` existe (linha 986) como
> **input do usuário**, não como lógica de auto-geração.
> Não existe função que converta automaticamente um setup de quali em race.
> Os comentários mostram distinção conceitual presente, mas sem implementação prática.

**Complexidade de implementação:** ⭐⭐ Média  
**Valor estratégico:** ⭐⭐⭐⭐⭐ Muito Alto — feature de alta demanda por usuários  
**Status:** ❌ IMPLEMENTAR

---

## GRUPO 6 — SAFETY / DEPENDÊNCIAS AERODINÂMICAS

### G6.1 — Regra de conflito aero em `safety.py`

**O que o 02.txt propõe:**
```python
def validate_dependencies(suggested_deltas):
    if suggested_deltas.get("delta_rw", 0) < 0:
        if suggested_deltas.get("delta_fw", 0) > 0:
            return False, "Conflito: Menos asa traseira com mais dianteira = sobre-esterço perigoso."
    return True, "OK"
```
Ou como entrada no `DANGEROUS_COMBOS`:
```python
{
    "name": "Menos asa traseira + mais asa dianteira",
    "risk": "Sobre-esterço severo — carro instável em alta velocidade",
    "conditions": [
        ("delta_rw", "< 0"),   # Menos asa traseira
        ("delta_fw", "> 0"),   # E mais asa dianteira
    ],
}
```

**Estado atual do código (`core/safety.py`):**
```python
DANGEROUS_COMBOS = [
    # Entrada 1: Camber extremo + pressão baixa
    # Entrada 2: Ride height mínimo + mola dura
    # ← Sem regra de aerodinâmica relativa
]
```
> Regra de conflito asa traseira/dianteira **NÃO EXISTE**.

**Por que isso importa:** Reduzir asa traseira e aumentar dianteira simultaneamente
é uma das configurações mais perigosas em carros de corrida. Muda radicalmente o
balanço aerodinâmico para sobre-esterço, especialmente em alta velocidade. Um safety
guard aqui previne um erro que nenhum piloto amador sobreviveria em velocidade real.

**Complexidade de implementação:** ⭐ Muito Baixa (adicionar entrada ao `DANGEROUS_COMBOS`)  
**Valor estratégico:** ⭐⭐⭐⭐⭐ Crítico — segurança  
**Status:** ❌ IMPLEMENTAR com prioridade máxima

---

## GRUPO 7 — INTELIGÊNCIA POR CLASSE DE CARRO

### G7.1 — Perfis de regras por categoria (`apply_rules()`)

**O que o 02.txt propõe:**
```python
if "LMP2" in vehicle_class:
    apply_rules("AERO_DRIVEN")      # Prioridade: Rake e Asa
elif "GT3" in vehicle_class or "GTE" in vehicle_class:
    apply_rules("MECHANICAL_GRIP")  # Prioridade: Molas e Diferencial
elif "Hypercar" in vehicle_class:
    apply_rules("ELECTRONIC_HYBRID") # Prioridade: Energia e Brake Bias
```
Cada perfil altera quais parâmetros a IA prioriza ao gerar sugestões.

**Estado atual do código (`core/heuristics.py`):**
> As heurísticas atuais operam de forma genérica, aplicando as mesmas regras
> de diagnóstico para qualquer carro.
> NÃO existe diferenciação por classe. `car_class` é armazenado no BD mas
> **não é usado** para selecionar perfis de regras diferentes.

**Complexidade de implementação:** ⭐⭐⭐ Média-Alta  
**Valor estratégico:** ⭐⭐⭐⭐ Alto — melhora enormemente a qualidade das sugestões  
**Status:** ❌ IMPLEMENTAR (requer estudo das heurísticas atuais)

---

## TABELA CONSOLIDADA DE RECOMENDAÇÕES

| ID | Item | Arquivo(s) | Complexidade | Valor | Prioridade | Aprovar? |
|----|------|-----------|-------------|-------|-----------|---------|
| G1.1 | `_reward_top_speed()` | `core/reward.py` | ⭐ | ⭐⭐⭐⭐ | Alta | ✅ SIM |
| G1.2 | Rebalancear pesos (sem remover features) | `core/reward.py` | ⭐ | ⭐⭐⭐ | Alta | ✅ SIM (com ajuste) |
| G1.3 | Multiplier por perfil de pista | `core/reward.py` | ⭐⭐ | ⭐⭐⭐⭐ | Média | ✅ SIM (após G2.1) |
| G1.4 | Refatorar `_reward_fuel_efficiency()` | `core/reward.py` | ⭐ | ⭐⭐⭐ | Média | ✅ SIM |
| G2.1 | `TRACK_POIS` dict | `core/reward.py` ou novo arquivo | ⭐ | ⭐⭐⭐ | Alta (pré-req) | ✅ SIM |
| G2.2 | `max_straight_speed` geográfico | `data/telemetry_reader.py` | ⭐⭐ | ⭐⭐⭐⭐ | Média | ✅ SIM |
| G3.1 | `get_fuel_ratio()` | `data/svm_parser.py` | ⭐ | ⭐⭐⭐⭐⭐ | Muito Alta | ✅ SIM |
| G3.2 | `set_fuel_liters()` | `data/svm_parser.py` | ⭐ | ⭐⭐⭐⭐ | Alta | ✅ SIM |
| G3.3 | Compensação ride height/combustível | `data/svm_parser.py` / `main.py` | ⭐ | ⭐⭐⭐⭐⭐ | Muito Alta | ✅ SIM |
| G3.4 | Consumo últimas 3 voltas | `main.py` | ⭐ | ⭐⭐ | Baixa | ✅ SIM |
| G4.1 | Nomenclatura `SECTORFLOW_...` nova | `main.py` | ⭐ | ⭐⭐⭐ | Baixa | ✅ SIM |
| G4.2 | Campo `Notes=` automático | `data/svm_parser.py` | ⭐ | ⭐⭐ | Baixa | ✅ SIM |
| G5.1 | Auto-geração setup Race from Quali | `main.py` | ⭐⭐ | ⭐⭐⭐⭐⭐ | Alta | ✅ SIM |
| G6.1 | Regra aero: menos RW + mais FW | `core/safety.py` | ⭐ | ⭐⭐⭐⭐⭐ | Crítica | ✅ SIM IMEDIATO |
| G7.1 | `apply_rules()` por categoria | `core/heuristics.py` | ⭐⭐⭐ | ⭐⭐⭐⭐ | Média | ✅ SIM (fase 3) |

**Todos os 15 itens analisados têm aprovação recomendada.** Nenhum apresenta
risco de regressão se implementado conforme os ajustes descritos (especialmente G1.2).

---

## PLANO DE IMPLEMENTAÇÃO — 3 FASES

### FASE 1 — Segurança e Base (Alta Prioridade) — ~2 sessões

**Itens:** G6.1, G3.1, G3.2, G3.3, G2.1

1. **G6.1** — Adicionar entrada ao `DANGEROUS_COMBOS` em `core/safety.py` (5 min)
2. **G2.1** — Criar dicionário `TRACK_POIS` em `core/reward.py` (10 min)
3. **G3.1** — Implementar `get_fuel_ratio()` em `data/svm_parser.py` (20 min)
4. **G3.2** — Implementar `set_fuel_liters()` em `data/svm_parser.py` (10 min)
5. **G3.3** — Implementar `calculate_fuel_compensation()` em `data/svm_parser.py` (15 min)

### FASE 2 — Reward + Telemetria (Médio Prazo) — ~2 sessões

**Itens:** G1.1, G1.2, G1.3, G1.4, G2.2, G5.1, G3.4

6. **G1.1** — Criar `_reward_top_speed()` em `core/reward.py`
7. **G1.2** — Rebalancear `REWARD_WEIGHTS` (sem remover fuel_efficiency/brake_health)
8. **G1.3** — Multiplier por `downforce_priority` em `compute_reward()`
9. **G1.4** — Refatorar `_reward_fuel_efficiency()` com novos parâmetros e ×5.0
10. **G2.2** — Capturar `max_straight_speed` em `data/telemetry_reader.py`
11. **G3.4** — Filtrar últimas 3 voltas no cálculo de consumo em `main.py`
12. **G5.1** — Auto-gerar setup Race from Quali em `main.py`

### FASE 3 — Qualidade e Polimento (Baixa Urgência) — ~1 sessão

**Itens:** G4.1, G4.2, G7.1

13. **G4.1** — Refatorar `_generate_setorflow_path()` com novo formato
14. **G4.2** — Escrever campo `Notes=` automaticamente ao salvar
15. **G7.1** — Implementar `apply_rules()` por categoria em `core/heuristics.py`

---

## PONTOS DE ATENÇÃO ESPECÍFICOS

### ⚠️ Sobre a proposta de REWARD_WEIGHTS (G1.2)
O 02.txt exclui `fuel_efficiency` e `brake_health` do dicionário. **NÃO adotar essa exclusão.**
Implementar com os 10 critérios existentes, apenas redistribuindo os pesos para abrir espaço
para `top_speed`. O rebalanceamento sugerido na seção G1.2 mantém a soma em 1.00 exata.

### ⚠️ Sobre `_reward_fuel_efficiency()` (G1.4)
A mudança nos parâmetros (`fuel_before/after` → `fuel_consumed/target_avg`) requer atualizar
a chamada em `compute_reward()`. O novo parâmetro `target_avg_consumed` precisa vir do banco
de dados (`db.get_avg_fuel_consumption(car_id, track_id)`). Essa função no BD pode precisar
ser criada se não existir.

### ⚠️ Sobre `mInLapDistPct` em telemetry_reader (G2.2)
O campo `mInLapDistPct` existe no Shared Memory do rF2/LMU via `rF2data.py`. Verificar
se `_sample_tick()` já lê esse campo antes de implementar. Se não lê, adicionar a leitura
do campo `mVehicleTelemetry.mLapDist / mTrackLength` ou o equivalente percentual.

### ⚠️ Sobre compensação de combustível/ride height (G3.3)
A heurística de `+1 clique por +10L` é uma aproximação. Para carros pesados (LMH/Hypercar),
o impacto por litro é menor. Para LMP3 (mais leve), pode ser maior. A função pode aceitar
um fator de escala opcional baseado na classe do carro.

### ⚠️ Sobre G7.1 (apply_rules por categoria)
Esta é a melhoria mais complexa. Requer análise cuidadosa de `core/heuristics.py` para
mapear quais regras existentes são genéricas vs. específicas. Recomendado fazer como
última fase para não quebrar heurísticas que já funcionam.

---

## CONCLUSÃO

O arquivo `02.txt` apresenta propostas coerentes com o perfil do simulador LMU e com
a arquitetura atual do SectorFlow. As 15 melhorias identificadas são todas viáveis e de
baixa-a-média complexidade de implementação. Nenhuma requer refatoração estrutural
do projeto.

**A única correção necessária é em G1.2:** a soma de pesos proposta no 02.txt exclui
`fuel_efficiency` e `brake_health` — itens já implementados. A solução é redistribuir
os pesos para incluir `top_speed` sem eliminar as features existentes.

**Recomendação final:** ✅ Aprovar todas as 15 melhorias e iniciar pela Fase 1.

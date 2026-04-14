# RELATÓRIO DE ANÁLISE — 02.txt vs Estado Atual da Aplicação
**Data:** 07/04/2026  
**Versão:** SectorFlow Setups (pós-implementação completa da Sprint anterior)  
**Objetivo:** Comparar o que o arquivo 02.txt propõe vs o que **já foi implementado** e identificar o que ainda pode ser feito para melhorar a aplicação.

---

## RESUMO EXECUTIVO

A sprint anterior implementou **15 itens** com base no 02.txt (confirmados com sintaxe OK em todos os arquivos).  
Esta análise encontrou **9 novos itens** que o 02.txt menciona ou implica, mas que **ainda não foram implementados** — cada um com complexidade e impacto diferente.

---

## PARTE 1 — O QUE JÁ FOI FEITO (Status Sprint Anterior)

| # | Item | Arquivo | Status |
|---|------|---------|--------|
| G1.1 | `_reward_top_speed()` — recompensa por velocidade na reta | `core/reward.py` | ✅ FEITO |
| G1.2 | `REWARD_WEIGHTS` rebalanceado (10 critérios, soma=1.00) | `core/reward.py` | ✅ FEITO |
| G1.3 | Multiplicador por perfil de pista (`_DOWNFORCE_SPEED_MULTIPLIER`) | `core/reward.py` | ✅ FEITO |
| G1.4 | `_reward_fuel_efficiency()` refatorado (vs. média histórica) | `core/reward.py` | ✅ FEITO |
| G2.1 | `TRACK_POIS` — 9 pistas com DNA de pista e straight POI | `core/reward.py` | ✅ FEITO |
| G2.2 | `max_straight_speed` geográfico no `LapAccumulator` + `LapSummary` | `data/telemetry_reader.py` | ✅ FEITO |
| G3.1 | `SVMFile.get_fuel_ratio()` — cálculo de L/clique por carro | `data/svm_parser.py` | ✅ FEITO |
| G3.2 | `SVMFile.set_fuel_liters()` — conversão litros → índice correto | `data/svm_parser.py` | ✅ FEITO |
| G3.3 | `calculate_fuel_compensation()` + `write_notes_field()` | `data/svm_parser.py` | ✅ FEITO |
| G3.4 | Cálculo de consumo médio usando as **3 últimas voltas** | `main.py` | ✅ FEITO |
| G4.1 | `_generate_sectorflow_path()` — padrão `SECTORFLOW_CLIMA_CAT+MARCA_PISTA_DDMM_VN_MODO.svm` | `main.py` | ✅ FEITO |
| G4.2 | Campo `Notes=` preenchido automaticamente em todos os setups gerados | `main.py` | ✅ FEITO |
| G5.1 | `generate_race_from_quali()` — converte setup de quali em setup de corrida | `main.py` | ✅ FEITO |
| G6.1 | `DANGEROUS_COMBO`: menos asa traseira + mais asa dianteira | `core/safety.py` | ✅ FEITO |
| G7.1 | `apply_rules()` + `sort_suggestions_by_class()` — perfis AERO_DRIVEN / MECHANICAL_GRIP / ELECTRONIC_HYBRID | `core/heuristics.py` | ✅ FEITO |

**Resultado: 15/15 ítens implementados e com sintaxe verificada.**

---

## PARTE 2 — O QUE AINDA PODE SER FEITO (Novos 9 Itens)

Abaixo estão os 9 itens identificados a partir de propostas do 02.txt que ainda **não foram implementados** ou que podem ser aprofundados.

---

### GRUPO A — DNA da Pista no Banco de Dados

#### A1 — Colunas de Perfil na Tabela `tracks` do Banco

**O que 02.txt diz:**
> "Criar um Perfil de Pista no Banco de Dados. Adicionar uma tabela que classifique as pistas por nível de Downforce (Baixo, Médio, Alto)."

**Estado atual:**
- `TRACK_POIS` existe em `core/reward.py` como dicionário Python em memória (9 pistas)
- A tabela `tracks` no `data/schema.sql` tem `track_type TEXT` mas **não tem** `downforce_level`, `main_straight_start`, `main_straight_end`
- Cada vez que o programa reinicia, o TRACK_POIS precisa estar hard-coded no source code

**O que falta:**
```sql
-- Adicionar em data/schema.sql à tabela tracks:
ALTER TABLE tracks ADD COLUMN downforce_level TEXT;   -- 'Very-Low' | 'Low' | 'Medium' | 'High'
ALTER TABLE tracks ADD COLUMN straight_start REAL;    -- 0.0–1.0 (% da volta)
ALTER TABLE tracks ADD COLUMN straight_end   REAL;    -- 0.0–1.0
ALTER TABLE tracks ADD COLUMN critical_corner TEXT;   -- "Last Corner" etc.
```
- Ao detectar nova pista via Shared Memory, sincronizar automaticamente com o `TRACK_POIS` se existir a entrada
- Benefício: configurações por pista persistem, o usuário pode editar via GUI, e a IA aprende padrões por pista no banco

**Complexidade:** Média  
**Impacto:** Alto — abre caminho para todos os itens de "DNA de pista"  
**Arquivos:** `data/schema.sql`, `data/database.py`, `main.py`

---

#### A2 — Sincronização Automática TRACK_POIS → Banco

**Estado atual:** TRACK_POIS e o banco de `tracks` são sistemas separados e não conversam.

**O que fazer:**
- Quando `TelemetryReader` detecta nova pista, chamar `db.get_or_create_track()` e, se existir entrada em `TRACK_POIS`, gravar automaticamente `downforce_level`, `straight_start`, `straight_end`
- Permite ao usuário editar perfis de pista pela GUI (aba "Pista") sem precisar editar código

**Complexidade:** Baixa (depende de A1)  
**Impacto:** Médio  
**Arquivos:** `main.py`, `data/database.py`

---

### GRUPO B — Telemetria Espacial Avançada

#### B1 — Micro-Setores (20 Binns de 5% da Pista)

**O que 02.txt diz:**
> "Dividir a pista em 20 ou 30 segmentos. Se a IA nota que o pneu superaquece apenas no setor de curvas rápidas, ela pode sugerir ajuste específico sem sacrificar o resto da pista."

**Estado atual:**
- Apenas S1, S2, S3 (3 setores fixos do LMU)
- A tabela `track_map_points` em `data/schema.sql` já tem coluna `distance_pct` — a infraestrutura está **pronta no banco**
- O `_sample_tick()` já captura `self._lap.progress()` para a detecção de reta

**O que falta:**
```python
# Em LapAccumulator — adicionar:
# 20 bins de 5% da volta (0–5%, 5–10%, ..., 95–100%)
thermal_bins: list[list[float]] = field(
    default_factory=lambda: [[] for _ in range(20)]
)  # média de temp por bin por volta

# Em _sample_tick():
lap_pct = self._lap.progress()
bin_idx = min(19, int(lap_pct * 20))  # 0..19
avg_tire_temp = média das 4 temperaturas outer no tick
self._accumulator.thermal_bins[bin_idx].append(avg_tire_temp)
```
- No `LapSummary`: `thermal_profile: list[float]` = média por bin  
- Na heurística: "temperatura bin 12–14 (curvas rápidas) está 15°C acima do bin médio → sugerir camber -1"

**Complexidade:** Média  
**Impacto:** Alto — permite diagnóstico cirúrgico de problemas em zonas específicas da pista  
**Arquivos:** `data/telemetry_reader.py`, `core/heuristics.py`

---

#### B2 — Tração na Saída da Curva que Precede a Reta Principal

**O que 02.txt diz:**
> "Usar o mapa para identificar a curva que precede a maior reta. O reward seria muito mais alto se o carro tivesse tração perfeita e estabilidade especificamente naquela curva de saída de reta."

**Estado atual:**
- `max_straight_speed` captura a velocidade **dentro da reta**
- Não há captura do que acontece na **saída da curva** que antecede essa reta (aceleração longitudinal pós-curva)

**O que fazer:**
- Adicionar `pre_straight_zone_start/end` em `TRACK_POIS` (ex: Fuji: 0.78–0.85, antes da reta)
- No `_sample_tick()`: se estiver na zona pré-reta, acumular `accel_longitudinal()` (tração de saída)
- No `LapSummary`: `pre_straight_exit_traction: float`
- No `compute_reward()`: penalidade adicional se `exit_traction` piorar (carro destracionando na saída)

**Complexidade:** Média  
**Impacto:** Alto — captura o ponto mais crítico de uma corrida (quem trai na saída perde a reta)  
**Arquivos:** `core/reward.py` (TRACK_POIS), `data/telemetry_reader.py`, `core/reward.py` (compute_reward)

---

#### B3 — Filtro de Consumo por Distância Percorrida

**O que 02.txt diz:**
> "Calcule o consumo por distância, e não por tempo, para evitar erros quando você sai da pista. Se a volta teve batida ou foi muito lenta (>110% do melhor tempo), o sistema deve descartar esse dado."

**Estado atual:**
- Consumo = `fuel_start - fuel_end` por volta completa
- O filtro de outlier (lap_time > 110% mediana → `is_valid=False`) já existe
- **Mas** o consumo de voltas inválidas ainda é calculado e pode "sujar" a média dos 3 laps

**O que falta:**
- No cálculo de `avg_consumption_last_3` em `main.py`: filtrar explicitamente por `is_valid=True`
- Normalizar por `lap_time` ou `track_length`: `consumo_por_km = delta_fuel / track_length_km`
- Isso elimina o viés de safety cars e pit outlaps

**Complexidade:** Baixa  
**Impacto:** Médio — melhora precisão do cálculo de combustível  
**Arquivos:** `main.py`, `data/database.py`

---

### GRUPO C — Reward Dinâmico Completo

#### C1 — REWARD_WEIGHTS Dinâmico por Perfil de Pista

**O que 02.txt diz:**
> "A IA pode ajustar os REWARD_WEIGHTS dinamicamente. Em pistas de alta velocidade, a penalidade por perda de Top Speed teria um peso muito maior do que em Mônaco."

**Estado atual:**
- `REWARD_WEIGHTS` é um dict **fixo** (`top_speed: 0.13` sempre)
- A consciência de pista está parcialmente implementada: há um `_DOWNFORCE_SPEED_MULTIPLIER` que multiplica o **valor** da reward de top_speed (até 2×)
- Mas o **peso relativo** (`REWARD_WEIGHTS["top_speed"]`) nunca muda

**O que fazer:**
```python
# Em core/reward.py — adicionar função:
def get_dynamic_weights(track_name: str = "") -> dict[str, float]:
    """Ajusta REWARD_WEIGHTS baseado no DNA da pista."""
    track_info = TRACK_POIS.get(track_name.upper().strip(), {})
    priority = track_info.get("downforce_priority", "Medium")
    
    weights = dict(REWARD_WEIGHTS)  # cópia base
    if priority == "Very-Low":      # Monza, Le Mans
        weights["top_speed"]    = 0.22   # era 0.13 → sobe
        weights["lap_time"]     = 0.18   # era 0.20 → cai levemente
        weights["grip"]         = 0.07   # menos relevante
    elif priority == "High":        # Hungaroring
        weights["grip"]         = 0.17   # sobe
        weights["top_speed"]    = 0.07   # cai
        weights["sector_improvement"] = 0.12  # curvas importam mais
    # normalizar para soma = 1.0 se necessário
    return weights
```
- `compute_reward()` chama `get_dynamic_weights(track_name)` quando `track_name` for informado
- A IA treina com pesos corretos para cada pista

**Complexidade:** Baixa/Média  
**Impacto:** Alto — muda fundamentalmente o que a IA aprende por pista  
**Arquivos:** `core/reward.py`

---

### GRUPO D — Camada de Decisão

#### D1 — Estimativa de Voltas Restantes (Exposição na GUI)

**O que 02.txt diz:**
> "Total_Laps = Current_Fuel / Avg_Consumption_Last_3_Laps"

**Estado atual:**
- Dados disponíveis: `fuel_end` (combustível atual) e `avg_consumption_last_3` (calculado em`main.py`)
- Mas **nenhum método** expõe essa informação calculada; a GUI não mostra estimativa de voltas

**O que fazer:**
```python
# Em VirtualEngineer (main.py):
def estimate_laps_remaining(self) -> dict:
    """Calcula voltas restantes com o combustível atual."""
    reader = self.telemetry
    current_fuel = reader.current_fuel()            # do _vehicle.fuel()
    avg_consumption = self._calc_avg_fuel_last3()   # já existente
    if avg_consumption <= 0:
        return {"laps": None, "confidence": "low"}
    laps = current_fuel / avg_consumption
    return {
        "laps": round(laps, 1),
        "current_fuel_l": round(current_fuel, 2),
        "avg_consumption_l": round(avg_consumption, 3),
        "confidence": "high" if self._has_min_fuel_samples() else "low",
    }
```
- Expor no `tab_telemetry.py` como indicador em tempo real
- Alerta visual se `laps_remaining < 3`

**Complexidade:** Baixa  
**Impacto:** Médio/Alto — altamente útil durante corridas de endurance  
**Arquivos:** `main.py`, `gui/tab_telemetry.py`

---

#### D2 — IES: Índice de Eficiência de Setup

**O que 02.txt diz:**
> "Se consumo CAIU e tempo BAIXOU: Setup excelente. Se consumo SUBIU e tempo BAIXOU: Setup agressivo. Se consumo SUBIU e tempo SUBIU: Setup desastroso."

**Estado atual:**
- Reward calcula consumo e lap_time separadamente
- Nenhuma função faz a análise cruzada (consumo × tempo) para classificar o tipo de setup

**O que fazer:**
```python
# Em core/reward.py ou core/llm_advisor.py:
def classify_setup_efficiency(
    delta_laptime: float,      # negativo = voltou mais rápido
    delta_consumption: float   # negativo = consumiu menos
) -> str:
    """Classifica a eficiência de um ajuste de setup."""
    fast = delta_laptime < -0.1     # >0.1s mais rápido
    lean = delta_consumption < -0.05  # >0.05L menos
    slow = delta_laptime > 0.1
    heavy = delta_consumption > 0.05

    if fast and lean:   return "EXCELENTE"   # menos arrasto E mais rápido
    if fast and heavy:  return "AGRESSIVO"   # mais asa = mais rápido mas caro
    if slow and lean:   return "CONSERVADOR" # economiza mas perdeu tempo
    if slow and heavy:  return "DESASTROSO"  # pior em tudo
    return "NEUTRO"
```
- LLM Advisor usa essa classificação para formular a explicação em linguagem natural
- GUI mostra o rótulo junto com a sugestão

**Complexidade:** Baixa  
**Impacto:** Alto — torna os feedbacks muito mais informativos para o usuário  
**Arquivos:** `core/reward.py`, `core/llm_advisor.py`, `gui/tab_setup.py`

---

### GRUPO E — Gestão Térmica Long Run (Preditiva)

#### E1 — Curva de Temperatura Multi-Volta (Trend Analysis)

**O que 02.txt diz:**
> "Se a temperatura do pneu sobe de forma linear e não estabiliza após 3 voltas, a IA deve editar o setup reduzindo o Camber ou a Pressão, mesmo que isso custe 0.1s no tempo de volta imediato."

**Estado atual:**
- A heurística avalia **uma volta** de cada vez (temp média da volta)
- Não há análise de **tendência across voltas** (se o pneu está esfriando, estável ou esquentando progressivamente)
- Para endurance isso é crítico: um setup ótimo nas 2 primeiras voltas pode destruir os pneus na volta 15

**O que fazer:**
```python
# Em data/telemetry_reader.py — manter histórico de temp por pneu:
# (últimas N LapSummaries já ficam em self._summaries)

# Em core/heuristics.py — nova regra:
def _check_thermal_trend(summaries: list[LapSummary], config, suggestions):
    """Analisa tendência de temperatura nas últimas 3+ voltas."""
    if len(summaries) < 3:
        return
    # Pegar temperaturas outer FL das últimas 3 voltas
    temps_fl = [s.features[2] for s in summaries[-3:]]  # feature outer FL
    slope = (temps_fl[-1] - temps_fl[0]) / 2  # °C/volta
    
    if slope > 3.0:   # esquentando 3°C por volta = degradação
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_f",
            delta=-1,
            rule_name="thermal_trend_degradation",
            condition=f"Temp FL subindo {slope:.1f}°C/volta (3 voltas)",
            explanation=f"Pneu FL aquecendo progressivamente (+{slope:.1f}°C/volta). "
                        "Reduzir pressão dianteira 1 clique para estabilizar temperatura "
                        "no long run, mesmo custando ~0.05s por volta.",
            priority=2,
        ))
```
- Passar `summaries[-3:]` para `analyze_telemetry()` como parâmetro adicional
- Pode sugerir: reduzir pressão, reduzir camber, ou aumentar ride height para reduzir atrito

**Complexidade:** Média/Alta  
**Impacto:** Muito Alto — é o problema mais crítico em endurance e que a IA atual não detecta  
**Arquivos:** `data/telemetry_reader.py`, `core/heuristics.py`, `main.py`

---

## PARTE 3 — TABELA RESUMO DOS 9 NOVOS ITENS

| # | Grupo | Descrição | Complexidade | Impacto | Arquivos |
|---|-------|-----------|:---:|:---:|---------|
| A1 | BD | Colunas de POI na tabela `tracks` (downforce_level, straight_start/end) | Média | Alto | `schema.sql`, `database.py` |
| A2 | BD | Sincronizar TRACK_POIS → banco automaticamente | Baixa | Médio | `main.py`, `database.py` |
| B1 | Telemetria | Micro-setores (20 bins) com perfil térmico por segmento | Média | Alto | `telemetry_reader.py`, `heuristics.py` |
| B2 | Telemetria | Tração na saída da curva pré-reta (zona pre-straight) | Média | Alto | `reward.py`, `telemetry_reader.py` |
| B3 | Telemetria | Filtro de consumo por distância + excluir voltas inválidas | Baixa | Médio | `main.py`, `database.py` |
| C1 | Reward | `get_dynamic_weights()` — pesos ajustados por perfil de pista | Baixa | Alto | `reward.py` |
| D1 | Decisão | `estimate_laps_remaining()` exposta na GUI | Baixa | Médio/Alto | `main.py`, `tab_telemetry.py` |
| D2 | Decisão | `classify_setup_efficiency()` — IES (consumo × tempo) | Baixa | Alto | `reward.py`, `llm_advisor.py` |
| E1 | Preditivo | Trend analysis térmico 3+ voltas → sugestão preditiva | Média/Alta | Muito Alto | `telemetry_reader.py`, `heuristics.py` |

---

## PARTE 4 — PRIORIDADE SUGERIDA PARA IMPLEMENTAÇÃO

### FASE 1 — Quick Wins (baixa complexidade, alto impacto) — 4 itens
- **C1** — REWARD_WEIGHTS dinâmico → mais inteligência sem muito código
- **D2** — Classificador IES → melhor comunicação com o usuário
- **D1** — Estimativa de voltas → útil imediatamente em corridas
- **B3** — Filtro de consumo por distância → correção de precisão

### FASE 2 — Core do DNA de Pista — 3 itens (depende sequencialmente)
- **A1** → Colunas no banco (fundação)
- **A2** → Sync TRACK_POIS → banco
- **B1** → Micro-setores térmicos (usa distance_pct já no schema)

### FASE 3 — Preditivo e Avançado — 2 itens
- **B2** → Tração pré-reta (zona crítica de corrida)
- **E1** → Gestão térmica long run (preditiva) — mais complexa mas mais impactante para endurance

---

## CONCLUSÃO

O 02.txt foi implementado integralmente na sprint anterior (15/15 itens). Esta nova análise encontrou **9 oportunidades adicionais** baseadas nos conceitos mais profundos do mesmo documento que ainda não foram realizados.

Os itens de maior ROI (retorno por esforço) são:
1. **C1** (pesos dinâmicos) e **D2** (IES) — baixo esforço, grande diferença no feedback da IA
2. **E1** (trend térmico) — maior esforço, mas essencial para o uso real em endurance
3. **A1+A2+B1** (DNA de pista no banco) — fundação para que o sistema aprenda padrões persistentes por pista

**Total de novos itens:** 9  
**Aguardando aprovação para implementar.**

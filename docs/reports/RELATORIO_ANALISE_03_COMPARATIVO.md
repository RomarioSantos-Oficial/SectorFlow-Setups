# RELATÓRIO DE ANÁLISE 03 — COMPARATIVO `02.txt` vs. CÓDIGO ATUAL
**SectorFlow Setups — Virtual Engineer**
**Data:** 07/04/2026 | **Sprint:** 3 (pós-implementação total de 02.txt)

---

## RESUMO EXECUTIVO

O arquivo `02.txt` propôs **24 melhorias** distribuídas em 7 temas principais.
Todas foram implementadas nos Sprints 1 e 2. Este relatório:

1. Confirma o **status final** de cada item do 02.txt
2. Identifica **lacunas residuais** e **pontos incompletos** após a implementação
3. Propõe **Sprint 3** com os próximos itens de maior impacto

---

## PARTE 1 — STATUS DE CADA ITEM DO `02.txt`

### TEMA A — DNA da Pista / Track POIs

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| A1 | Tabela de pistas com nível de Downforce no banco | ✅ FEITO | `data/schema.sql` + `data/database.py` | Colunas `downforce_level`, `straight_start`, `straight_end`, `critical_corner` adicionadas. Migração automática via `_migrate_schema()`. |
| A2 | Sincronizar `TRACK_POIS` no banco ao detectar pista | ✅ FEITO | `data/database.py` | `get_or_create_track()` faz lazy import de `TRACK_POIS` e popula as colunas POI automaticamente. |
| A3 | Velocidade máxima medida na reta (Speed Trap geográfico) | ✅ FEITO | `data/telemetry_reader.py` | `_sample_tick()` detecta se `mInLapDistPct` está dentro de `main_straight_start/end` e registra `max_straight_speed`. |
| A4 | Multiplicador de penalidade de velocidade por perfil | ✅ FEITO | `core/reward.py` | `_DOWNFORCE_SPEED_MULTIPLIER` com `Very-Low=2.0`, `Low=1.5`, `High=0.5` aplicados em `compute_reward()`. |

---

### TEMA B — Microsetores e Tração

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| B1 | Divisão da pista em 20 micro-setores térmicos | ✅ FEITO | `data/telemetry_reader.py` + `core/heuristics.py` | `LapAccumulator.thermal_bins` (20 bins), `LapSummary.thermal_profile`. Heurística `_check_thermal_micro_sector()` detecta bins >10°C acima da média. |
| B2 | Medir aceleração na zona pré-reta (saída da última curva) | ✅ FEITO | `core/reward.py` + `data/telemetry_reader.py` | `pre_straight_zone_start/end` em todos os 9 `TRACK_POIS`. `_reward_exit_traction()` no reward. `pre_straight_exit_traction` no `LapSummary`. |
| B3 | Filtrar voltas inválidas nos cálculos de consumo | ✅ FEITO | `main.py` | Dois loops em `calculate_race_setup()` e `calculate_fuel_strategy()` já filtram `not curr.get("valid", True)`. |

---

### TEMA C — Pesos Dinâmicos

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| C1 | `REWARD_WEIGHTS` ajustados dinamicamente por perfil de pista | ✅ FEITO | `core/reward.py` | `get_dynamic_weights(track_name)` com 4 perfis: Very-Low, Low, High, Medium. Auto-normaliza para 1.00. |

---

### TEMA D — Estratégia e Combustível

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| D1 | `estimate_laps_remaining()` — estimar voltas com fuel atual | ✅ FEITO | `main.py` | Método público. Usa média das últimas 3 voltas válidas. Retorna `{laps, current_fuel_l, avg_consumption_l, confidence}`. |
| D2 | `classify_setup_efficiency()` — IES cruzando tempo+consumo | ✅ FEITO | `core/reward.py` | Classifica como `EXCELENTE/AGRESSIVO/CONSERVADOR/DESASTROSO/NEUTRO`. |
| D3 | `get_fuel_ratio()` — calcular litros por índice para cada carro | ✅ FEITO | `data/svm_parser.py` | Extrai da linha `FuelSetting=INDICE//DESCRICAO` a proporção real. |
| D4 | `set_fuel_liters()` — definir combustível por litros reais | ✅ FEITO | `data/svm_parser.py` | Usa `get_fuel_ratio()` e atualiza o índice correto preservando a descrição. |
| D5 | `calculate_fuel_compensation()` — Ride Height ao adicionar fuel | ✅ FEITO | `data/svm_parser.py` | `+10L → +1 clique de RH`. Fator por classe (LMP3=1.2, Hypercar=0.8). |

---

### TEMA E — Gestão Térmica de Long Run

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| E1 | Heurística de tendência térmica crescente nas últimas 3+ voltas | ✅ FEITO | `core/heuristics.py` | `_check_thermal_trend()` detecta slope >3°C/volta. Sugere `delta_pressure_f=-1` + `delta_camber_f=+1`. Chamada dentro de `analyze_telemetry()`. |

---

### TEMA F — Parser e Edição In-Place

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| F1 | Edição "in-place" — sobrescrever arquivo original sem criar cópias | ✅ FEITO | `data/svm_parser.py` | `save_svm()` salva no caminho original com backup automático em `backups/`. |
| F2 | Dicionário `SVM_MAP` de tradução delta→seção/chave | ✅ PARCIAL | `data/svm_parser.py` + `core/brain.py` | `apply_deltas()` no parser opera sobre `full_key` (ex: `REARWING.RWSetting`). O mapeamento de nomes semânticos (`delta_rw` → chave SVM real) está em `deltas_to_svm()` em `core/brain.py`. Funcional, mas não usa um dicionário centralizado `SVM_MAP` exatamente como proposto. |
| F3 | Backup único do original antes da 1ª alteração | ✅ FEITO | `data/svm_parser.py` | `save_svm(backup=True)` cria backup com timestamp. Não duplica se já existe um backup diário. |
| F4 | `write_notes_field()` — escrever campo Notes= no .svm | ✅ FEITO | `data/svm_parser.py` | Atualiza ou insere a linha `Notes=` preservando formato. |

---

### TEMA G — Nomenclatura e Classes de Carro

| ID | Proposta do 02.txt | Status | Arquivo | Observação |
|----|-------------------|--------|---------|------------|
| G1 | Gerador de nome padronizado `SECTORFLOW_{CLIMA}_{...}.svm` | ✅ FEITO | `main.py` | `_generate_sectorflow_path()` implementado. Exemplos: `SECTORFLOW_DRY_LMP3GIN_FUJ_0704_V1_Q.svm`. |
| G2 | Perfis por classe: `AERO_DRIVEN`, `MECHANICAL_GRIP`, `ELECTRONIC_HYBRID` | ✅ FEITO | `core/heuristics.py` | `_CLASS_STRATEGY` + `apply_rules()` + `sort_suggestions_by_class()`. |
| G3 | Diferenciação Quali vs. Race nos ajustes automáticos | ✅ FEITO | `core/heuristics.py` | `SESSION_MODIFIERS` com offsets para `qualy` e `race`. |
| G4 | Pesos de REWARD_WEIGHTS redistribuídos corretamente | ✅ FEITO | `core/reward.py` | 11 critérios implementados. Soma base ≈1.02, normalizada por `get_dynamic_weights()`. |
| G5 | `validate_deltas()` com proteções e combos perigosos | ✅ FEITO | `core/safety.py` | `DANGEROUS_COMBOS` com 3 regras. Limita ±3 índices, valida ranges, escala magnitude total. |
| G6 | `build_param_conversion_table()` — índice → valor físico (°, kPa, etc.) | ✅ FEITO | `data/svm_parser.py` | Extrai `physical_value` e `unit` via regex da descrição. |
| G7 | Aliases de classe (`lmh`, `lmdh` → `hypercar`, etc.) | ✅ FEITO | `core/heuristics.py` | `_CLASS_ALIASES` pré-processados. |

---

## PARTE 2 — LACUNAS RESIDUAIS IDENTIFICADAS

Mesmo com tudo implementado, a inspeção do código atual revelou **6 lacunas** que impactam diretamente a qualidade do produto:

---

### LACUNA L1 — `_check_thermal_micro_sector` usa assinatura incompatível

**Arquivo:** `core/heuristics.py` (função `_check_thermal_micro_sector`, linhas ~500–530)

**Problema:** A função usa um campo `reason` e `confidence` no construtor de `HeuristicSuggestion`, mas a dataclass só tem `rule_name`, `condition`, `explanation`.

```python
# Como está (INCORRETO):
suggestions.append(HeuristicSuggestion(
    param_name="delta_pressure_f",
    delta=-1,
    reason=(...),        # ← campo não existe na dataclass
    priority=3,
    confidence=0.65,     # ← campo não existe na dataclass
))
```

```python
# Como deveria ser:
suggestions.append(HeuristicSuggestion(
    param_name="delta_pressure_f",
    delta=-1,
    rule_name="thermal_micro_sector",
    condition=f"bin_{first_zone_pct}pct > mean + 10°C",
    explanation=(...),
    priority=3,
))
```

**Impacto:** `TypeError` em runtime ao completar a 1ª volta com telemetria real.
**Classificação:** 🔴 Bug Crítico

---

### LACUNA L2 — `_check_thermal_trend` usa mesma assinatura incompatível

**Arquivo:** `core/heuristics.py` (função `_check_thermal_trend`)

**Mesmo problema da L1.** Os dois `HeuristicSuggestion(...)` dentro da função também usam `reason=` e `confidence=`.

**Impacto:** Mesmo runtime error da L1.
**Classificação:** 🔴 Bug Crítico

---

### LACUNA L3 — `estimate_laps_remaining()` nunca é chamado nem exibido na GUI

**Arquivo:** `main.py` tem o método. `gui/tab_telemetry.py` **não** chama nem exibe os resultados.

**Situação atual:** A aba de Telemetria (`tab_telemetry.py`) mostra `LabeledValue` de `fuel_per_lap`, mas **não** tem widget para `voltas_restantes`.

**Impacto:** O usuário não vê a estimativa de voltas. O método existe mas é "letra morta".
**Classificação:** 🟡 Funcionalidade Incompleta

---

### LACUNA L4 — `classify_setup_efficiency()` nunca é exibido ao usuário

**Arquivo:** `core/reward.py` tem a função. Nenhum arquivo da GUI chama ou exibe o resultado `EXCELENTE/AGRESSIVO/etc.`

**Impacto:** O feedback mais importante para o usuário (IES) existe no backend mas é invisível.
**Classificação:** 🟡 Funcionalidade Incompleta

---

### LACUNA L5 — `TRACK_POIS` cobre apenas 9 pistas; Le Mans Ultimate tem ~30

**Arquivo:** `core/reward.py`

**Pistas com dados completos:** MONZA, FUJI, LE MANS, SPA, BAHRAIN, INTERLAGOS, HUNGARORING, IMOLA, PORTIMAO.

**Pistas ausentes (LMU Season 2024/25):** Sebring, Lusail (Qatar), Red Bull Ring, Road Atlanta, Daytona, Mugello, Circuit of the Americas, Watkins Glen, Misano, Suzuka, Shanghai, Austin, São Paulo Extended, Mônaco (LMH).

**Impacto:** Em pistas desconhecidas, o sistema usa `"Medium"` como padrão — correto, mas sem penalidade/bônus de velocidade e sem zona pré-reta.
**Classificação:** 🟠 Incompleto Funcional

---

### LACUNA L6 — `validate_dependencies` do 02.txt não implementado como função standalone

**Proposta do 02.txt:**
```python
def validate_dependencies(suggested_deltas):
    if suggested_deltas.get("delta_rw", 0) < 0:
        if suggested_deltas.get("delta_fw", 0) > 0:
            return False, "Conflito: Menos asa traseira com mais dianteira..."
    return True, "OK"
```

**Status atual:** O `DANGEROUS_COMBOS` em `safety.py` cobre a combinação `delta_rw < 0` + `delta_fw > 0`, mas **a mensagem é um aviso** (warning), não uma rejeição explícita com feedback formatado ao usuário.

**Impacto:** Baixo — a proteção existe. Mas o retorno estruturado `(bool, str)` proposto facilitaria testes unitários e integração com GUI.
**Classificação:** 🟢 Melhoria de Qualidade

---

## PARTE 3 — SPRINT 3: ITENS PROPOSTOS (AGUARDANDO APROVAÇÃO)

Com base nas lacunas encontradas e nas melhorias de maior impacto, proponho o **Sprint 3**:

---

### S3-1 — Corrigir L1 + L2: Assinatura de `HeuristicSuggestion` nas novas funções

**Prioridade:** 🔴 CRÍTICA — bug em runtime
**Arquivos:** `core/heuristics.py`
**Trabalho estimado:** Pequeno (2 substituições simples)
**O que fazer:** Trocar `reason=` por `explanation=` (e `rule_name=`/`condition=`), remover `confidence=`.

---

### S3-2 — Expor `estimate_laps_remaining()` na aba de Telemetria

**Prioridade:** 🟡 ALTA
**Arquivos:** `gui/tab_telemetry.py`
**O que fazer:**
- Adicionar `LabeledValue` para "Voltas restantes" na seção Combustível
- No método `update()` da aba, chamar `engine.estimate_laps_remaining()` e exibir `laps` + badge de `confidence`
- Exibir também `avg_consumption_l` ao lado

**Resultado para o usuário:** "⛽ Restam 12.3 voltas (Alta confiança)"

---

### S3-3 — Expor `classify_setup_efficiency()` na aba de Setup

**Prioridade:** 🟡 ALTA
**Arquivos:** `gui/tab_setup.py`
**O que fazer:**
- Após a IA sugerir ajustes e o usuário aplicá-los, calcular `classify_setup_efficiency(delta_laptime, delta_consumption)`
- Exibir o badge colorido no chat: `EXCELENTE 🟢`, `AGRESSIVO 🟠`, `CONSERVADOR 🔵`, `DESASTROSO 🔴`
- Salvar o IES no banco com o setup

---

### S3-4 — Expandir `TRACK_POIS` para mais 10 pistas do LMU

**Prioridade:** 🟠 MÉDIA
**Arquivo:** `core/reward.py`
**Pistas a adicionar:** Sebring, Mugello, Suzuka, Red Bull Ring, Circuit of the Americas, Watkins Glen, Lusail, Misano, Daytona, Road Atlanta
**Formato:** Seguir o padrão já estabelecido com `main_straight_start/end`, `downforce_priority`, `pre_straight_zone_start/end`.

---

### S3-5 — Criar widget visual do `thermal_profile` (20 bins) na GUI

**Prioridade:** 🟠 MÉDIA
**Arquivos:** `gui/tab_telemetry.py` + `gui/widgets.py`
**O que fazer:**
- Novo widget `ThermalMapWidget` — 20 retângulos coloridos (verde→amarelo→vermelho por temperatura)
- Exibir na aba Telemetria abaixo dos pneus
- Bins >10°C da média ficam em vermelho (visual da heurística B1)

---

### S3-6 — `validate_dependencies()` como função pública com retorno estruturado

**Prioridade:** 🟢 BAIXA
**Arquivo:** `core/safety.py`
**O que fazer:**
- Refatorar a parte de `DANGEROUS_COMBOS` de `validate_deltas()` para uma função separada `validate_dependencies(deltas) -> tuple[bool, str]`
- Mantém compatibilidade — `validate_deltas()` chama internamente

---

## PARTE 4 — TABELA DE PRIORIDADES SPRINT 3

| ID | Descrição | Impacto | Dificuldade | Prioridade |
|----|-----------|---------|-------------|------------|
| S3-1 | Corrigir bug assinatura HeuristicSuggestion | Bug em runtime | Fácil | 🔴 P1 |
| S3-2 | Expor `estimate_laps_remaining` na GUI | Visibilidade usuário | Média | 🟡 P2 |
| S3-3 | Badge `classify_setup_efficiency` na GUI | UX + decisão | Média | 🟡 P2 |
| S3-4 | Expandir TRACK_POIS (10 pistas) | Precisão por pista | Fácil | 🟠 P3 |
| S3-5 | Widget térmico 20 bins | Visualização avançada | Difícil | 🟠 P3 |
| S3-6 | `validate_dependencies()` standalone | Testabilidade | Fácil | 🟢 P4 |

---

## PARTE 5 — CONCLUSÃO

### O que foi entregue (02.txt completo):
- **24/24 itens** implementados ✅
- Sistema de reward com 11 critérios + pesos dinâmicos por pista
- Parser de .svm completo com backup, notas, compensação de combustível
- Nomenclatura padronizada `SECTORFLOW_*`
- Microsetores térmicos de 20 bins
- Tração pré-reta como critério de reward
- Estimativa de voltas restantes no backend

### O que falta para o produto estar **100% funcional**:
1. **Fix dos 2 bugs** (L1 + L2) — sem isso, o runtime quebra ao completar uma volta real
2. **GUI** — 3 features de backend não têm representação visual
3. **Cobertura de pistas** — 9 de ~30 pistas do LMU têm POIs completos

### Recomendação:
Implementar **S3-1** imediatamente (bug crítico) e em seguida **S3-2 + S3-3** para que o usuário passe a ver os benefícios das melhorias já entregue.

---

*Relatório gerado automaticamente — aguardando aprovação do usuário para prosseguir com Sprint 3.*

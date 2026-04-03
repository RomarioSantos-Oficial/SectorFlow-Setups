# 📊 RELATÓRIO: Melhorias de Aprendizagem da IA

**Programa:** LMU Virtual Engineer  
**Data:** 01/04/2026  
**Objetivo:** Identificar e documentar lacunas no sistema de aprendizagem da IA — regras faltantes, dados não coletados, e lógica específica por categoria de carro que ainda não existe.

---

## 📌 Resumo Executivo

A IA atual tem **12 regras heurísticas**, coleta **49 features** de telemetria e usa um **reward de 9 critérios**. Porém há lacunas críticas:

1. **Não coleta dados de slip/patinagem** — o rF2 fornece (via `mLongitudinalPatchVel`, `mRotation`), mas o programa ignora
2. **Não detecta lockups de roda** — travamento na frenagem é visível no SM mas não é monitorado
3. **Regras de ABS/TC são genéricas** — não diferenciam a intensidade do ajuste por classe real
4. **LMP2 sem ABS/TC não tem regras compensatórias profundas** — só sugere brake bias, falta Engine Braking Map
5. **Hypercar não monitora gasto de energia por volta** — só olha carga da bateria, não avalia se o deploy está no limite regulamentar
6. **Não analisa estilo de pilotagem** — throttle/brake/steering estão disponíveis no SM mas não são coletados
7. **Faltam regras de desgaste assimétrico** — sistema só olha desgaste total, não cross-car
8. **Não existe regra de Diff Preload** — parâmetro existe no ADJUSTMENT_HIERARCHY mas nenhuma regra o altera

---

## 🔍 Análise Detalhada por Área

### 1. DADOS NÃO COLETADOS (Shared Memory → Telemetria)

O rF2 Shared Memory (`rF2Wheel`, `rF2VehicleTelemetry`) disponibiliza dados que o `TelemetryReader` **não coleta**:

| # | Dado disponível no SM | Campo no rF2 | Utilidade | Status atual |
|---|---|---|---|---|
| D1 | **Velocidade longitudinal do pneu** | `mLongitudinalPatchVel` | Calcular slip ratio (patinagem) | ❌ Não coletado |
| D2 | **Velocidade lateral do pneu** | `mLateralPatchVel` | Calcular slip angle (ângulo de deriva) | ❌ Não coletado |
| D3 | **Velocidade longitudinal do solo** | `mLongitudinalGroundVel` | Referência para calcular slip real | ❌ Não coletado |
| D4 | **Rotação da roda** | `mRotation` | Detectar lockup (rotação = 0 com carro em movimento) | ❌ Não coletado |
| D5 | **Throttle filtrado** | `mFilteredThrottle` | Estilo de pilotagem / suavidade na aceleração | ❌ Não coletado |
| D6 | **Brake filtrado** | `mFilteredBrake` | Estilo de frenagem / agressividade | ❌ Não coletado |
| D7 | **Steering filtrado** | `mFilteredSteering` | Suavidade da direção / understeer real | ❌ Não coletado |
| D8 | **Torque do volante** | `mSteeringShaftTorque` | Feedback force = understeer detection | ❌ Não coletado |
| D9 | **RPM do motor** | `mEngineRPM` | Detectar upshifts tardios / bouncing no limiter | ❌ Não coletado |
| D10 | **Engine Torque** | `mEngineTorque` | Calcular TC intervention real | ❌ Não coletado |
| D11 | **Rear Brake Bias** | `mRearBrakeBias` | Saber o bias real aplicado (inclui ABS) | ❌ Não coletado |
| D12 | **Deflexão vertical do pneu** | `mVerticalTireDeflection` | Detectar flatspots e pneu danificado | ❌ Não coletado |
| D13 | **Temperatura da carcaça** | `mTireCarcassTemperature` | Calor interno acumulado (indica pneu "morto") | ❌ Não coletado |
| D14 | **Tipo de superfície** | `mSurfaceType` | Detectar rodas na grama/brita (saída de pista) | ❌ Não coletado |

#### Impacto

Sem D1-D4, a IA **não consegue calcular slip ratio nem detectar lockups**. Essas são as duas métricas mais importantes para ajustar TC e ABS. A regra `_check_abs_tc` atual usa apenas `grip_avg` e `rain` como proxy — muito impreciso.

Sem D5-D8, a IA **não conhece o estilo do piloto**. Não sabe se ele freina tarde, se é agressivo no volante, se pisa fundo no acelerador. Essas informações determinariam ajustes personalizados (TC mais alto para piloto agressivo, ABS mais alto para quem freina tarde).

---

### 2. MÉTRICAS DERIVADAS QUE DEVEM SER CALCULADAS

Com os dados D1-D14 acima, o sistema pode calcular métricas de engenharia que hoje não existem:

| # | Métrica | Fórmula | Para que serve |
|---|---|---|---|
| M1 | **Slip Ratio (longitudinal)** | `(wheel_speed - ground_speed) / max(ground_speed, 0.1)` | Patinagem na aceleração (+) ou frenagem (-). Ideal: ±0.05 a ±0.10 |
| M2 | **Slip Angle (lateral)** | `atan2(lateral_patch_vel, longitudinal_ground_vel)` | Ângulo de deriva. Ideal: 4-8° para GT3, 2-5° para Hypercar |
| M3 | **Lockup Count** | Conta amostras onde `slip_ratio < -0.15` e `brake > 0.3` | Travamentos por volta — indica ABS insuficiente ou bias errado |
| M4 | **Wheelspin Count** | Conta amostras onde `slip_ratio > 0.15` e `throttle > 0.5` | Patinagens na saída — indica TC insuficiente ou molas erradas |
| M5 | **Brake Smoothness** | `std(d_brake/dt)` | Suavidade na frenagem (0 = suave, alto = agressivo) |
| M6 | **Throttle Smoothness** | `std(d_throttle/dt)` | Suavidade na aceleração (piloto agressivo vs suave) |
| M7 | **Steering Rate** | `mean(abs(d_steering/dt))` | Quão rápido o piloto gira o volante (nervoso vs calmo) |
| M8 | **Understeer Index** | `steering_torque_drop` quando `steering > 0.3` | Torque cai = frente perdeu grip = understeer real |
| M9 | **TC Intervention** | `filtered_throttle < unfiltered_throttle * 0.9` | Frequência com que o TC corta potência |
| M10 | **ABS Intervention** | `filtered_brake < unfiltered_brake * 0.9` | Frequência com que o ABS alivia a frenagem |
| M11 | **Carcass Heat Buildup** | `carcass_temp - surface_avg_temp` | Se a carcaça está acumulando calor (pneu "morrendo" por dentro) |
| M12 | **Off-Track Events** | Conta amostras com `surface_type >= 2` | Saídas de pista por volta |
| M13 | **RPM Limiter Events** | Conta amostras com `rpm > max_rpm * 0.99` | Batendo no limiter = precisa trocar marcha antes |
| M14 | **Desgaste Assimétrico** | `abs(wear_FL - wear_FR)` e `abs(wear_RL - wear_RR)` | Lado→lado desbalanceado = camber ou pressão errada |

---

### 3. REGRAS HEURÍSTICAS QUE FALTAM

#### 3A. Regras de Controle de Tração (TC)

**Problema atual:** A regra `_check_abs_tc` usa `traction_loss_events` — mas esse campo **nunca é preenchido** pela telemetria. A regra é morta.

| # | Regra | Condição | Ação | Classes afetadas |
|---|---|---|---|---|
| R1 | **TC por wheelspin real** | `wheelspin_count > 5/volta` | `delta_tc_map += 1` | GT3, Hypercar |
| R2 | **TC excessivo** | `wheelspin_count == 0` E `throttle_avg > 0.8` | `delta_tc_map -= 1` (TC corta demais) | GT3, Hypercar |
| R3 | **TC na chuva** | `rain > 0.2` E `wheelspin_count > 3` | `delta_tc_map += 2` (chuva = mais TC) | GT3, Hypercar |
| R4 | **Sem TC (LMP2)** | `wheelspin_count > 5` E `classe == lmp2` | `delta_diff_preload -= 1` + `delta_spring_r -= 1` (compensar com mecânica) | LMP2 |
| R5 | **TC Power Cut** | `tc_intervention_rate > 30%` | `delta_tc_power_cut += 1` (TC cortando demais, liberar mais) | Hypercar |

#### 3B. Regras de ABS / Frenagem

**Problema atual:** A regra atual só verifica se "grip_avg < 0.8 na chuva" — não usa dados reais de lockup.

| # | Regra | Condição | Ação | Classes afetadas |
|---|---|---|---|---|
| R6 | **ABS por lockup real** | `lockup_count > 3/volta` | `delta_abs_map += 1` | GT3, Hypercar |
| R7 | **ABS excessivo** | `lockup_count == 0` E `brake_avg > 0.7` | `delta_abs_map -= 1` (ABS protege demais, perde frenagem) | GT3, Hypercar |
| R8 | **Sem ABS — Brake Bias** | `lockup_count > 3` E `classe == lmp2` | `delta_rear_brake_bias += 1` | LMP2 |
| R9 | **Sem ABS — Engine Braking** | `lockup_count > 5` E `classe == lmp2` | `delta_engine_braking += 1` (usar motor para frear) | LMP2 |
| R10 | **Brake Bias por eixo** | `lockup_front > lockup_rear * 2` | `delta_rear_brake_bias += 1` (bias p/ trás) | Todas |
| R11 | **Brake Bias por eixo (inverso)** | `lockup_rear > lockup_front * 2` | `delta_rear_brake_bias -= 1` (bias p/ frente) | Todas |

#### 3C. Regras de Estilo de Pilotagem

| # | Regra | Condição | Ação | Explicação |
|---|---|---|---|---|
| R12 | **Piloto agressivo no acelerador** | `throttle_smoothness > 0.3` | `delta_tc_map += 1`, `delta_spring_r += 1` | Piloto pisa fundo rápido — precisa mais TC e mola traseira mais dura |
| R13 | **Piloto agressivo no freio** | `brake_smoothness > 0.4` | `delta_abs_map += 1` | Freada brusca = mais risco de lockup |
| R14 | **Piloto nervoso no volante** | `steering_rate > 2.0 rad/s` | `delta_arb_f -= 1` (amolecer = mais forgiving) | Correções rápidas = carro imprevisível |
| R15 | **Piloto suave** | `throttle_smooth < 0.1` E `brake_smooth < 0.1` | `delta_tc_map -= 1`, `delta_abs_map -= 1` | Piloto suave pode usar menos eletrônica |

#### 3D. Regras de Diff Preload

**Problema atual:** `delta_diff_preload` existe no ADJUSTMENT_HIERARCHY mas **NENHUMA regra** o modifica.

| # | Regra | Condição | Ação | Explicação |
|---|---|---|---|---|
| R16 | **Oversteer na saída + tração baixa** | `oversteer_exit` E `wheelspin_count > 3` | `delta_diff_preload += 1` (travar mais o diff) | Diff aberto → roda interna patina → perda de tração |
| R17 | **Understeer na entrada** | `understeer_entry` E `diff_preload alto` | `delta_diff_preload -= 1` (abrir o diff) | Diff muito travado = carro não rota na entrada |
| R18 | **Desgaste traseiro assimétrico** | `abs(wear_RL - wear_RR) > 5%` | `delta_diff_preload -= 1` | Diff travado força as duas rodas = desgaste desigual se carro faz mais curvas para um lado |

#### 3E. Regras de Energia Híbrida (Hypercar específicas)

**Problema atual:** Só olha `battery_charge` (%) — não monitora ERS deploy por volta.

| # | Regra | Condição | Ação | Explicação |
|---|---|---|---|---|
| R19 | **Deploy excessivo** | `energy_used_per_lap > energy_limit * 0.95` | `delta_virtual_energy -= 1` | Vai tomar penalidade se passar do limite de energia por volta |
| R20 | **Deploy insuficiente** | `energy_used_per_lap < energy_limit * 0.7` | `delta_virtual_energy += 1` | Deixando energia na mesa — pode andar mais rápido |
| R21 | **Regen na chuva** | `rain > 0.2` E `wheelspin_rear > 3` | `delta_regen_map -= 1` | Regeneração causa torque na traseira = patinagem na chuva |
| R22 | **Bateria para stint** | `battery_trend_negative` E `stint > 3 voltas` | `delta_regen_map += 1` | Se a bateria está caindo ao longo do stint, precisa de mais regen |

#### 3F. Regras de Desgaste e Gestão de Pneu

| # | Regra | Condição | Ação | Explicação |
|---|---|---|---|---|
| R23 | **Desgaste dianteiro >> traseiro** | `wear_avg_front / wear_avg_rear > 1.5` | `delta_camber_f += 1`, `delta_pressure_f -= 1` | Dianteira se desgastando mais rápido |
| R24 | **Desgaste traseiro >> dianteiro** | `wear_avg_rear / wear_avg_front > 1.5` | `delta_camber_r += 1`, `delta_pressure_r -= 1` | Traseira se desgastando mais rápido |
| R25 | **Carcaça superaquecendo** | `carcass_temp > surface_temp + 15°C` | `delta_pressure_f -= 1`, `delta_camber_f += 1` | Calor acumulado internamente = pneu "morrendo" por dentro |
| R26 | **Flatspot detectado** | `tire_deflection_std > threshold` | Alerta ao piloto: "Flatspot detectado no pneu {X}" | Pneu irregular = vibrações e perda de grip |

---

### 4. CONFIGURAÇÃO POR CLASSE — O QUE FALTA NO `CLASS_CONFIG`

O `CLASS_CONFIG` atual tem parâmetros genéricos. Faltam dados específicos de cada classe para as regras funcionarem corretamente:

```python
# PROPOSTA: adicionar ao CLASS_CONFIG
CLASS_CONFIG = {
    "hypercar": {
        # ... existentes ...
        "has_abs": True,
        "has_tc": True,
        "has_engine_braking_map": True,
        "has_regen": True,                    # ← já existe
        "has_energy_limit_per_lap": True,     # ← NOVO: regulamento WEC
        "energy_limit_mj_per_lap": 290.0,    # ← NOVO: ~290 MJ por volta (varia por BoP)
        "ideal_slip_ratio": (0.03, 0.08),    # ← NOVO: slip ideal para o compound
        "ideal_slip_angle_deg": (2.0, 5.0),  # ← NOVO: ângulo de deriva ideal
        "tc_sensitivity": "high",            # ← NOVO: TC é crítico por causa do híbrido
        "abs_sensitivity": "medium",
        "diff_preload_range": (0, 12),       # ← NOVO: range do diff
    },
    "lmp2": {
        # ... existentes ...
        "has_abs": False,                     # ← NOVO: LMP2 NÃO tem ABS
        "has_tc": False,                      # ← NOVO: LMP2 NÃO tem TC
        "has_engine_braking_map": True,       # ← NOVO: único recurso eletrônico
        "has_regen": False,
        "has_energy_limit_per_lap": False,
        "ideal_slip_ratio": (0.04, 0.10),    # ← NOVO: tolerância maior (sem TC)
        "ideal_slip_angle_deg": (3.0, 7.0),  # ← NOVO: carro mais aerodinâmico, mais slip
        "tc_sensitivity": "none",
        "abs_sensitivity": "none",
        "diff_preload_range": (0, 10),
        "brake_bias_critical": True,         # ← NOVO: sem ABS, bias é vida ou morte
    },
    "lmgt3": {
        # ... existentes ...
        "has_abs": True,
        "has_tc": True,
        "has_engine_braking_map": False,
        "has_regen": False,
        "has_energy_limit_per_lap": False,
        "ideal_slip_ratio": (0.05, 0.12),    # ← NOVO: GT3 mais "escorregadio"
        "ideal_slip_angle_deg": (4.0, 8.0),  # ← NOVO: mais grip mecânico
        "tc_sensitivity": "medium",           # ← NOVO: TC importante para preservar pneu
        "abs_sensitivity": "high",            # ← NOVO: ABS permite frenagens agressivas
        "diff_preload_range": (0, 8),
    },
}
```

---

### 5. SISTEMA DE REWARD — LACUNAS

O `compute_reward()` tem 9 critérios mas faltam 4 métricas de qualidade:

| # | Reward faltante | Peso sugerido | O que mede |
|---|---|---|---|
| RW1 | **Slip Quality** | 0.05 | Se o slip ratio ficou na janela ideal (menos patinagem e lockup = melhor) |
| RW2 | **Electronics Efficiency** | 0.05 | Se o ajuste de TC/ABS reduziu intervenções excessivas sem causar problemas |
| RW3 | **Energy Management** | 0.05 | Se o Hypercar está cumprindo o limite de energia por volta (só para Hypercar) |
| RW4 | **Desgaste Assimétrico** | 0.05 | Se o desgaste L↔R ficou mais equilibrado depois do ajuste |

**Pesos sugeridos recalculados:**

```python
REWARD_WEIGHTS = {
    "lap_time": 0.20,           # era 0.25 → reduz pois tempo depende do piloto
    "temp_balance": 0.12,       # era 0.15
    "grip": 0.08,               # era 0.10
    "consistency": 0.10,        # mantém
    "user_satisfaction": 0.10,  # mantém
    "tire_wear": 0.08,          # era 0.10
    "sector_improvement": 0.07, # era 0.10
    "fuel_efficiency": 0.05,    # mantém
    "brake_health": 0.05,       # mantém
    "slip_quality": 0.05,       # ← NOVO
    "electronics_eff": 0.05,    # ← NOVO
    "energy_management": 0.03,  # ← NOVO (só Hypercar, peso dinâmico)
    "wear_asymmetry": 0.02,     # ← NOVO
}
```

---

### 6. FEATURES DA REDE NEURAL — EXPANSÃO NECESSÁRIA

Atualmente: **49 features**. Para suportar as novas regras, precisamos de **~63 features**.

| Feature # | Nome | Fonte |
|---|---|---|
| 49 | `slip_ratio_avg_f` | Média do slip ratio das rodas dianteiras |
| 50 | `slip_ratio_avg_r` | Média do slip ratio das rodas traseiras |
| 51 | `slip_angle_avg_f` | Ângulo de deriva médio dianteiro |
| 52 | `slip_angle_avg_r` | Ângulo de deriva médio traseiro |
| 53 | `lockup_count` | Travamentos por volta |
| 54 | `wheelspin_count` | Patinagens por volta |
| 55 | `throttle_smoothness` | Suavidade na aceleração |
| 56 | `brake_smoothness` | Suavidade na frenagem |
| 57 | `steering_rate` | Taxa de rotação do volante |
| 58 | `tc_intervention_rate` | % do tempo que o TC estava ativo |
| 59 | `abs_intervention_rate` | % do tempo que o ABS estava ativo |
| 60 | `carcass_temp_avg` | Temperatura média da carcaça (4 rodas) |
| 61 | `off_track_events` | Saídas de pista por volta |
| 62 | `wear_asymmetry_f` | Desgaste FL vs FR (assimetria) |
| 63 | `wear_asymmetry_r` | Desgaste RL vs RR (assimetria) |

**Impacto:** O `SetupNeuralNet` precisa aceitar `num_inputs=63` (ou manter retrocompatibilidade com 49 e usar os extras como "zero" quando não disponíveis).

---

### 7. TABELA COMPARATIVA: O QUE CADA CLASSE PRECISA

| Funcionalidade | Hypercar | LMP2 | GT3 | Status |
|---|---|---|---|---|
| **ABS disponível** | ✅ Sim | ❌ Não | ✅ Sim | ⚠️ Regras não diferenciam bem |
| **TC disponível** | ✅ Sim | ❌ Não | ✅ Sim | ⚠️ Regras não usam slip real |
| **Engine Braking Map** | ✅ Sim | ✅ Sim (único recurso!) | ❌ Não | ❌ Nenhuma regra existe |
| **Regen / Híbrido** | ✅ Sim | ❌ Não | ❌ Não | ⚠️ Regra existe mas básica |
| **Energy Limit per Lap** | ✅ Sim (regulamento WEC) | ❌ Não | ❌ Não | ❌ Não monitorado |
| **Diff Preload impacto** | Alto (4WD parcial) | Alto | Médio | ❌ Nenhuma regra |
| **Brake Bias criticidade** | Média (ABS ajuda) | **CRÍTICA** (sem ABS!) | Média (ABS ajuda) | ⚠️ Regra atual insuficiente |
| **Slip Ratio monitoramento** | Essencial (híbrido causa slip imprevisível) | Essencial (sem TC!) | Importante | ❌ Não coletado |
| **Estilo de pilotagem** | Útil | **ESSENCIAL** (sem aids!) | Útil | ❌ Não coletado |

---

### 8. COMPORTAMENTO ESPECÍFICO: LMP2 SEM ELETRÔNICA

O LMP2 é o carro mais exigente para a IA porque **não tem ABS nem TC**. O piloto controla TUDO sozinho. A IA precisa de regras compensatórias especiais:

#### 8A. Frenagem sem ABS

```
SE classe == "lmp2" E lockup_count > 3:
    1. Mover brake bias para trás (+1 a +3 dependendo da severidade)
    2. Se lockup é nas dianteiras: delta_rear_brake_bias += 1
    3. Se lockup é nas traseiras: delta_rear_brake_bias -= 1
    4. Aumentar Engine Braking Map para desacelerar com motor
    5. Considerar endurecer mola traseira (evita transferência de peso excessiva)
```

#### 8B. Aceleração sem TC

```
SE classe == "lmp2" E wheelspin_count > 5:
    1. Fechar diff preload (+1 a +2) para distribuir torque
    2. Amolecer mola traseira (-1) para mais contato no solo
    3. Se pista molhada: delta_diff_preload += 2 (diff mais fechado)
    4. Camber traseiro menos agressivo (+1) para mais contato
    5. NÃO AJUSTAR TC (não existe!)
```

#### 8C. Frase especial para piloto no chat

```
"⚠️ Carro sem ABS/TC detectado (LMP2). Ajustes compensatórios aplicados:
   • Brake Bias: {valor}% (mais para trás para evitar lockup dianteiro)
   • Engine Braking: Mapa {N} (usar motor para ajudar a frear)
   • Diff Preload: {valor} (mais fechado para evitar patinagem)
   
   💡 Dica: Seja suave no acelerador na saída das curvas."
```

---

### 9. PLANO DE IMPLEMENTAÇÃO

#### Fase 1: Coleta de Dados (Prioridade ALTA)

| # | Tarefa | Arquivo | Complexidade |
|---|---|---|---|
| 1.1 | Coletar `mRotation`, `mLongitudinalPatchVel`, `mLongitudinalGroundVel` por roda | `data/telemetry_reader.py` | Média |
| 1.2 | Coletar `mFilteredThrottle`, `mFilteredBrake`, `mFilteredSteering` | `data/telemetry_reader.py` | Baixa |
| 1.3 | Coletar `mUnfilteredThrottle`, `mUnfilteredBrake` | `data/telemetry_reader.py` | Baixa |
| 1.4 | Coletar `mTireCarcassTemperature` | `data/telemetry_reader.py` | Baixa |
| 1.5 | Coletar `mSurfaceType` | `data/telemetry_reader.py` | Baixa |
| 1.6 | Calcular slip ratio, lockup count, wheelspin count no `_finalize_lap` | `data/telemetry_reader.py` | Média |
| 1.7 | Calcular throttle/brake smoothness e steering rate | `data/telemetry_reader.py` | Média |
| 1.8 | Ampliar `LapAccumulator` com campos novos | `data/telemetry_reader.py` | Média |
| 1.9 | Ampliar features de 49 → 63 (retrocompatível) | `data/telemetry_reader.py`, `core/brain.py` | Média |

#### Fase 2: Regras Heurísticas (Prioridade ALTA)

| # | Tarefa | Arquivo | Complexidade |
|---|---|---|---|
| 2.1 | Reescrever `_check_abs_tc` com dados reais de lockup/wheelspin | `core/heuristics.py` | Média |
| 2.2 | Criar `_check_diff_preload` (R16-R18) | `core/heuristics.py` | Baixa |
| 2.3 | Criar `_check_engine_braking` (R9, para LMP2) | `core/heuristics.py` | Baixa |
| 2.4 | Criar `_check_driving_style` (R12-R15) | `core/heuristics.py` | Média |
| 2.5 | Criar `_check_energy_limit` (R19-R22, para Hypercar) | `core/heuristics.py` | Média |
| 2.6 | Criar `_check_wear_asymmetry` (R23-R26) | `core/heuristics.py` | Baixa |
| 2.7 | Ampliar `CLASS_CONFIG` com campos novos | `core/heuristics.py` | Baixa |
| 2.8 | Adicionar `delta_engine_braking` ao ADJUSTMENT_HIERARCHY | `core/heuristics.py` | Baixa |

#### Fase 3: Reward e IA (Prioridade MÉDIA)

| # | Tarefa | Arquivo | Complexidade |
|---|---|---|---|
| 3.1 | Adicionar `_reward_slip_quality` | `core/reward.py` | Média |
| 3.2 | Adicionar `_reward_electronics_efficiency` | `core/reward.py` | Média |
| 3.3 | Adicionar `_reward_energy_management` (condicional: só Hypercar) | `core/reward.py` | Baixa |
| 3.4 | Adicionar `_reward_wear_asymmetry` | `core/reward.py` | Baixa |
| 3.5 | Recalcular pesos do reward (13 critérios) | `core/reward.py` | Baixa |
| 3.6 | Atualizar `SetupNeuralNet` para 63 inputs (retrocompatível) | `core/brain.py` | Média |

#### Fase 4: UX e Frases Contextuais (Prioridade BAIXA)

| # | Tarefa | Arquivo | Complexidade |
|---|---|---|---|
| 4.1 | Frases específicas para LMP2 no chat (sem ABS/TC) | `gui/tab_setup.py` | Baixa |
| 4.2 | Card de "Estilo de Pilotagem" na aba Telemetria | `gui/tab_telemetry.py` | Média |
| 4.3 | Mostrar slip ratio em tempo real | `gui/tab_telemetry.py` | Média |
| 4.4 | Alerta visual de lockup/wheelspin | `gui/tab_telemetry.py` | Baixa |

---

### 10. ORDEM DE EXECUÇÃO RECOMENDADA

```
Fase 1 (Coleta)  ──→  Fase 2 (Regras)  ──→  Fase 3 (Reward/IA)  ──→  Fase 4 (UX)
     ↑                      ↑
     │                      │
 ESSENCIAL            ESSENCIAL
 (sem dados,          (dados sem regras
  nada funciona)       = dados inúteis)
```

**Fase 1 PRIMEIRO** porque todas as outras dependem dos dados coletados.  
**Fase 2 SEGUNDO** porque as regras dão valor imediato ao piloto (mesmo sem retreinar a IA).  
**Fase 3 TERCEIRO** porque melhora a qualidade do treinamento a longo prazo.  
**Fase 4 POR ÚLTIMO** porque é visual/informativo, não afeta a lógica.

---

### 11. RESUMO DE IMPACTO ESPERADO

| Métrica | Antes | Depois |
|---|---|---|
| Features coletadas | 49 | 63 (+28%) |
| Regras heurísticas | 12 | 22 (+83%) |
| Critérios de reward | 9 | 13 (+44%) |
| Dados de slip/lockup | ❌ Nenhum | ✅ Completo |
| Estilo de pilotagem | ❌ Ignorado | ✅ 4 métricas |
| Diferenciação LMP2 | ⚠️ Básica (s/ ABS/TC) | ✅ 5 regras compensatórias |
| Energia Hypercar | ⚠️ Só bateria % | ✅ Deploy por volta + limite regulamentar |
| Diff Preload | ❌ 0 regras | ✅ 3 regras |
| Engine Braking | ❌ 0 regras | ✅ 1 regra (LMP2) |

---

> **Conclusão:** As maiores lacunas estão na **coleta de dados** (o jogo fornece, mas o programa ignora) e na **especificidade por classe** (LMP2 sem eletrônica precisa de tratamento totalmente diferente). Implementar a Fase 1 + Fase 2 já dará um salto enorme na qualidade das sugestões.

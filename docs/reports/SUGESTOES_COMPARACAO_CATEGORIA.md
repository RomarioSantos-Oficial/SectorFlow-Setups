# 📊 SUGESTÕES — Comparação por Categoria/Classe Independente de Marca

**Data:** Abril 2026  
**Status:** Aguardando Aprovação  
**Escopo:** Banco de dados + lógica de aprendizagem

---

## 🎯 PROBLEMA ATUAL

O banco hoje aprende **por carro específico** (ex: Ferrari 296 GT3 na Spa).  
Se você andar com a **Porsche 911 GT3** na mesma pista, o sistema começa do zero — mesmo que ambos sejam GT3 e tenham comportamentos similares.

**Dados isolados hoje:**
```
Ferrari GT3 × Spa  →  car_track_memory (isolado)
Porsche GT3 × Spa  →  car_track_memory (isolado)
Mercedes GT3 × Spa →  car_track_memory (isolado)
```

**Com as sugestões abaixo:**
```
Ferrari GT3 × Spa  ─┐
Porsche GT3 × Spa  ─┼──▶  class_track_benchmarks (GT3 × Spa)
Mercedes GT3 × Spa ─┘           │
                                 ▼
                      Qualquer GT3 novo recebe
                      dados da classe imediatamente
```

---

## 🔧 SUGESTÃO 1 — Nova Tabela: `class_track_benchmarks`

**O que faz:** Agrega dados de performance de **todos os carros da mesma classe** em uma pista, independente de marca.

```sql
CREATE TABLE class_track_benchmarks (
    benchmark_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    car_class           TEXT NOT NULL,        -- "GT3", "Hypercar", "GTE", "LMP2"
    track_id            INTEGER REFERENCES tracks(track_id),

    -- Referências de tempo para a classe nesta pista
    avg_best_lap        REAL,         -- Média dos melhores tempos da classe
    median_best_lap     REAL,         -- Mediana
    top10pct_lap        REAL,         -- Tempo do top 10% (referência de elite)

    -- Consumo e desgaste médios da CLASSE (não do carro específico)
    avg_fuel_per_lap    REAL,
    avg_tire_wear_fl    REAL,
    avg_tire_wear_fr    REAL,
    avg_tire_wear_rl    REAL,
    avg_tire_wear_rr    REAL,
    typical_wear_cat    TEXT,         -- "low" / "medium" / "high"

    -- Faixas típicas de eletrônicos para a classe nesta pista
    tc_range_json       TEXT,         -- {"min":1,"max":6,"median":3}
    abs_range_json      TEXT,         -- {"min":1,"max":4,"median":2}

    -- Condições climáticas dos dados
    weather_condition   TEXT DEFAULT 'dry',

    -- Metadados de confiança
    cars_contributing   INTEGER DEFAULT 0,  -- Quantos carros diferentes contribuíram
    total_laps          INTEGER DEFAULT 0,  -- Total de voltas na amostra
    confidence          REAL DEFAULT 0.0,   -- 0.0 a 1.0

    last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(car_class, track_id, weather_condition)
);
```

**Benefício:** Quando você pegar um GT3 novo, o sistema já tem referência de tempo, consumo e desgaste típico daquela pista.

---

## 🔧 SUGESTÃO 2 — Nova Tabela: `class_setup_patterns`

**O que faz:** Armazena **tendências de setup por classe + pista** em valores normalizados (0.0 = mínimo, 1.0 = máximo para a classe), sem depender dos ranges de cada carro.

```sql
CREATE TABLE class_setup_patterns (
    pattern_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    car_class           TEXT NOT NULL,
    track_id            INTEGER REFERENCES tracks(track_id),
    weather_condition   TEXT DEFAULT 'dry',

    -- Valores normalizados para a classe (0.0 a 1.0)
    -- ex: asa traseira 0.8 = "alta para a classe nesta pista"
    norm_rear_wing      REAL,   -- 0.0 = mínimo, 1.0 = máximo da classe
    norm_spring_f       REAL,
    norm_spring_r       REAL,
    norm_camber_f       REAL,
    norm_camber_r       REAL,
    norm_arb_f          REAL,
    norm_arb_r          REAL,
    norm_brake_bias     REAL,
    norm_ride_height_f  REAL,
    norm_ride_height_r  REAL,

    -- Tendências em linguagem natural (gerado pela IA)
    tendency_tags       TEXT,   -- JSON: ["asa_alta","suspensao_macia","frenagem_traseira"]
    pattern_notes       TEXT,   -- Explicação em português

    -- Efetividade deste padrão
    effectiveness       REAL DEFAULT 0.5,
    samples_count       INTEGER DEFAULT 0,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(car_class, track_id, weather_condition)
);
```

**Benefício:** O sistema aprende que "GT3 em Brands Hatch precisa de asa ALTA e suspensão MACIA" — e aplica isso para qualquer GT3 que você trouxer.

---

## 🔧 SUGESTÃO 3 — Expandir `car_similarity` (já existe, mas vazia)

**O que faz:** Popular automaticamente a tabela de similaridade com base em `car_class`, `drivetrain`, `has_hybrid`.

**Lógica proposta:**

| Condição | Similaridade |
|----------|-------------|
| Mesma classe (ex: GT3 + GT3) | 0.75 |
| Mesma classe + mesma tração | 0.85 |
| Mesma classe + tração + híbrido | 0.92 |
| Classes adjacentes (GT3 + GTE) | 0.40 |
| Classes diferentes | < 0.20 |

**Nova coluna sugerida:**
```sql
ALTER TABLE car_similarity ADD COLUMN auto_calculated INTEGER DEFAULT 0;
ALTER TABLE car_similarity ADD COLUMN basis_detail TEXT;  -- "mesmo_classe+tracao"
```

**Benefício:** Transfer Learning — dados de uma Porsche GT3 enriquecem o modelo da Ferrari GT3.

---

## 🔧 SUGESTÃO 4 — Nova VIEW: `v_car_vs_class_benchmark`

**O que faz:** Compara a performance de um carro específico contra a média da classe na mesma pista.

```sql
CREATE VIEW v_car_vs_class_benchmark AS
SELECT
    c.car_name,
    c.car_class,
    t.track_name,
    ctm.best_lap_time                           AS car_best_lap,
    ctb.avg_best_lap                            AS class_avg_lap,
    ctb.top10pct_lap                            AS class_reference_lap,
    ROUND(ctm.best_lap_time - ctb.avg_best_lap, 3) AS gap_to_class_avg,
    ROUND(ctm.best_lap_time - ctb.top10pct_lap, 3) AS gap_to_top10,
    ctb.cars_contributing                       AS class_data_from_cars,
    CASE
        WHEN ctm.best_lap_time <= ctb.top10pct_lap   THEN 'elite'
        WHEN ctm.best_lap_time <= ctb.avg_best_lap   THEN 'acima_media'
        ELSE 'abaixo_media'
    END AS performance_tier
FROM car_track_memory ctm
JOIN cars c ON ctm.car_id = c.car_id
JOIN tracks t ON ctm.track_id = t.track_id
LEFT JOIN class_track_benchmarks ctb
    ON ctb.car_class = c.car_class
    AND ctb.track_id = ctm.track_id;
```

**Benefício:** Você vê exatamente se está dentro ou fora do nível esperado para sua classe naquela pista.

---

## 🔧 SUGESTÃO 5 — Nova Coluna em `training_data`: Dados Cross-Car

**O que faz:** Adicionar colunas para que a rede neural possa treinar com dados de toda a classe, não apenas de um carro.

```sql
ALTER TABLE training_data ADD COLUMN car_class TEXT;
ALTER TABLE training_data ADD COLUMN is_cross_class INTEGER DEFAULT 0;  -- 1 = dado de outro carro da mesma classe
ALTER TABLE training_data ADD COLUMN source_car_id INTEGER REFERENCES cars(car_id);
ALTER TABLE training_data ADD COLUMN cross_class_weight REAL DEFAULT 0.5;  -- peso menor para dados de outro carro
```

**Benefício:** Ao treinar para um GT3 novo, a IA pode incluir dados de outros GT3 com peso menor (0.5) mas ainda aprender com eles.

---

## 📊 IMPACTO ESPERADO

| Situação | Antes | Depois |
|----------|-------|--------|
| Carro novo da mesma classe | Começa do zero | Bootstrap com dados da classe |
| 2ª pista nunca visitada com GT3 familiar | Sem referência | Usa padrão GT3 aprendido |
| Comparar performance com outros pilotos | Impossível | View mostra tier |
| Transfer learning entre carros | Manual / inexistente | Automático por similaridade |
| Sugestão de setup para GT3 sem histórico | Baseado em heurísticas | Baseado em padrão da classe |

---

## 🗂️ RESUMO DAS MUDANÇAS

| Item | Tipo | Complexidade |
|------|------|-------------|
| `class_track_benchmarks` | Nova tabela | Média |
| `class_setup_patterns` | Nova tabela | Média |
| `car_similarity` expansão | ALTER TABLE | Baixa |
| `v_car_vs_class_benchmark` | Nova VIEW | Baixa |
| `training_data` cross-car | ALTER TABLE | Baixa |
| Lógica de atualização automática | Código Python | Alta |

---

## ⚠️ DEPENDÊNCIAS

Para funcionar, precisará de código Python em `data/database.py` para:
1. `update_class_benchmarks(car_class, track_id)` — atualiza benchmarks após cada sessão
2. `get_class_pattern(car_class, track_id)` — retorna padrão da classe para novo carro
3. `calculate_car_similarity()` — popula `car_similarity` automaticamente
4. `get_cross_class_training_data(car_id)` — retorna dados de carros similares

---

**Aguardando aprovação para implementar.**

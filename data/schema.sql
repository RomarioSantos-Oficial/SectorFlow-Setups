-- ============================================================
-- BANCO DE DADOS: lmu_engineer.db
-- LMU Virtual Engineer — Schema Completo v1.0
-- Engine: SQLite 3 com WAL mode
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA auto_vacuum=INCREMENTAL;

-- ============================================================
-- 1. TABELA: cars (Catálogo de carros)
-- Armazena metadados de cada carro. A IA aprende padrões
-- ESPECÍFICOS por carro (ex: Hypercar vs GT3).
-- ============================================================
CREATE TABLE IF NOT EXISTS cars (
    car_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    car_name            TEXT NOT NULL UNIQUE,
    car_class           TEXT,
    car_class_normalized TEXT,
    engine_type         TEXT,
    drivetrain          TEXT,
    has_hybrid          INTEGER DEFAULT 0,
    has_bop             INTEGER DEFAULT 0,
    base_weight_kg      REAL,
    max_fuel_l          REAL,
    first_seen          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT
);

-- ============================================================
-- 2. TABELA: tracks (Catálogo de pistas)
-- folder_name corresponde ao nome real da pasta em
-- UserData\player\Settings\<folder_name>\.
-- ============================================================
CREATE TABLE IF NOT EXISTS tracks (
    track_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    track_name          TEXT NOT NULL,
    folder_name         TEXT NOT NULL UNIQUE,
    track_length_m      REAL,
    num_sectors         INTEGER DEFAULT 3,
    track_type          TEXT,
    first_seen          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 3. TABELA: driver_profiles (Perfis de pilotos)
-- Cada piloto tem um perfil. A IA adapta as sugestões ao
-- estilo de pilotagem (agressivo vs conservador).
-- ============================================================
CREATE TABLE IF NOT EXISTS driver_profiles (
    driver_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_name         TEXT NOT NULL UNIQUE,
    skill_level         TEXT DEFAULT 'intermediate',
    aggression          REAL DEFAULT 0.5,
    braking_style       REAL DEFAULT 0.5,
    consistency         REAL DEFAULT 0.5,
    preferred_level     TEXT DEFAULT 'basic',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 4. TABELA: sessions (Sessões de jogo)
-- Uma "sessão" = uma entrada no jogo com um carro em uma pista.
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id           INTEGER NOT NULL REFERENCES driver_profiles(driver_id),
    car_id              INTEGER NOT NULL REFERENCES cars(car_id),
    track_id            INTEGER NOT NULL REFERENCES tracks(track_id),
    session_type        TEXT DEFAULT 'practice',
    weather             TEXT DEFAULT 'dry',
    air_temp_c          REAL,
    track_temp_c        REAL,
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at            TIMESTAMP,
    total_laps          INTEGER DEFAULT 0,
    best_lap_time       REAL,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_combo ON sessions(car_id, track_id);

-- ============================================================
-- 5. TABELA: laps (Dados por volta)
-- TABELA CENTRAL. Cada volta com telemetria resumida.
-- É daqui que a IA extrai os dados de treinamento.
-- ============================================================
CREATE TABLE IF NOT EXISTS laps (
    lap_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(session_id),
    lap_number          INTEGER NOT NULL,
    lap_time            REAL,
    is_valid            INTEGER DEFAULT 1,
    fuel_at_start       REAL,
    fuel_used           REAL,

    -- Temperaturas médias dos pneus (°C)
    temp_fl_inner   REAL, temp_fl_middle  REAL, temp_fl_outer  REAL,
    temp_fr_inner   REAL, temp_fr_middle  REAL, temp_fr_outer  REAL,
    temp_rl_inner   REAL, temp_rl_middle  REAL, temp_rl_outer  REAL,
    temp_rr_inner   REAL, temp_rr_middle  REAL, temp_rr_outer  REAL,

    -- Pressões dos pneus (kPa)
    pressure_fl     REAL, pressure_fr     REAL,
    pressure_rl     REAL, pressure_rr     REAL,

    -- Desgaste (0.0=novo, 1.0=careca)
    wear_fl         REAL, wear_fr         REAL,
    wear_rl         REAL, wear_rr         REAL,

    -- Carga nos pneus (N)
    load_fl         REAL, load_fr         REAL,
    load_rl         REAL, load_rr         REAL,

    -- Aerodinâmica e Suspensão
    ride_height_f   REAL,
    ride_height_r   REAL,
    downforce_f     REAL,
    downforce_r     REAL,
    max_speed       REAL,

    -- Pitch / Roll / Heave médios
    avg_pitch       REAL,
    avg_roll        REAL,
    avg_heave       REAL,

    -- Freios (temperatura máxima)
    max_brake_temp_fl REAL, max_brake_temp_fr REAL,
    max_brake_temp_rl REAL, max_brake_temp_rr REAL,

    recorded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_laps_session ON laps(session_id);
CREATE INDEX IF NOT EXISTS idx_laps_time    ON laps(lap_time);
CREATE INDEX IF NOT EXISTS idx_laps_valid   ON laps(session_id, is_valid);

-- ============================================================
-- 6. TABELA: setup_snapshots (Snapshots completos do .svm)
-- Correlaciona setup ↔ performance.
-- ============================================================
CREATE TABLE IF NOT EXISTS setup_snapshots (
    snapshot_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(session_id),
    applied_at_lap      INTEGER,
    source              TEXT DEFAULT 'loaded',
    svm_filename        TEXT,

    -- Parâmetros chave (índices do .svm)
    rw_setting          INTEGER,
    spring_fl           INTEGER, spring_fr   INTEGER,
    spring_rl           INTEGER, spring_rr   INTEGER,
    camber_fl           INTEGER, camber_fr   INTEGER,
    camber_rl           INTEGER, camber_rr   INTEGER,
    pressure_fl         INTEGER, pressure_fr INTEGER,
    pressure_rl         INTEGER, pressure_rr INTEGER,
    anti_sway_f         INTEGER, anti_sway_r INTEGER,
    ride_height_fl      INTEGER, ride_height_fr INTEGER,
    ride_height_rl      INTEGER, ride_height_rr INTEGER,
    slow_bump_fl        INTEGER, slow_bump_fr   INTEGER,
    slow_bump_rl        INTEGER, slow_bump_rr   INTEGER,
    slow_rebound_fl     INTEGER, slow_rebound_fr INTEGER,
    slow_rebound_rl     INTEGER, slow_rebound_rr INTEGER,
    fast_bump_fl        INTEGER, fast_bump_fr   INTEGER,
    fast_bump_rl        INTEGER, fast_bump_rr   INTEGER,
    fast_rebound_fl     INTEGER, fast_rebound_fr INTEGER,
    fast_rebound_rl     INTEGER, fast_rebound_rr INTEGER,
    brake_pressure      INTEGER,
    rear_brake_bias     INTEGER,
    diff_preload        INTEGER,
    toe_f               INTEGER, toe_r       INTEGER,
    tc_map              INTEGER, abs_map     INTEGER,
    brake_duct_f        INTEGER, brake_duct_r INTEGER,
    fuel_setting        INTEGER,

    -- Arquivo .svm completo (para restauração)
    svm_raw_content     TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_session ON setup_snapshots(session_id);

-- ============================================================
-- 7. TABELA: ai_suggestions (Sugestões da IA)
-- Registra CADA sugestão, o feedback e o resultado.
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_suggestions (
    suggestion_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER NOT NULL REFERENCES sessions(session_id),
    after_lap           INTEGER NOT NULL,
    source              TEXT DEFAULT 'neural_net',

    -- Deltas sugeridos (saída da IA)
    delta_rw            REAL,
    delta_spring_f      REAL, delta_spring_r     REAL,
    delta_camber_f      REAL, delta_camber_r     REAL,
    delta_pressure_f    REAL, delta_pressure_r   REAL,
    delta_brake_press   REAL,
    delta_arb_f         REAL, delta_arb_r        REAL,

    -- Explicação em linguagem natural
    explanation_text    TEXT,

    -- Feedback do usuário
    user_accepted       INTEGER,
    user_feedback_bias  REAL,
    user_confidence     REAL,

    -- Resultado medido
    lap_time_before     REAL,
    lap_time_after      REAL,
    improvement_pct     REAL,
    reward_score        REAL,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_suggestions_session ON ai_suggestions(session_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_session_source ON ai_suggestions(session_id, source);

-- ============================================================
-- 8. TABELA: training_data (Dataset de treinamento)
-- Dados prontos para alimentar a rede neural.
-- ============================================================
CREATE TABLE IF NOT EXISTS training_data (
    data_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER REFERENCES sessions(session_id),
    car_id              INTEGER REFERENCES cars(car_id),
    track_id            INTEGER REFERENCES tracks(track_id),
    input_vector        BLOB NOT NULL,
    output_vector       BLOB NOT NULL,
    reward              REAL NOT NULL,
    weight              REAL DEFAULT 1.0,
    is_valid            INTEGER DEFAULT 1,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_training_car_track ON training_data(car_id, track_id);

-- ============================================================
-- 9. TABELA: heuristic_log (Log de regras heurísticas)
-- ============================================================
CREATE TABLE IF NOT EXISTS heuristic_log (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          INTEGER REFERENCES sessions(session_id),
    after_lap           INTEGER,
    rule_name           TEXT NOT NULL,
    rule_condition      TEXT,
    suggestion_text     TEXT,
    delta_applied       TEXT,
    was_effective       INTEGER,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 10. TABELA: model_checkpoints (Versões do modelo IA)
-- ============================================================
CREATE TABLE IF NOT EXISTS model_checkpoints (
    checkpoint_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id              INTEGER REFERENCES cars(car_id),
    track_id            INTEGER REFERENCES tracks(track_id),
    filename            TEXT NOT NULL,
    epoch               INTEGER,
    total_samples       INTEGER,
    avg_reward          REAL,
    best_lap_time       REAL,
    is_active           INTEGER DEFAULT 1,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 11. TABELA: track_map_points (Mapa da pista construído)
-- ============================================================
CREATE TABLE IF NOT EXISTS track_map_points (
    point_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id            INTEGER NOT NULL REFERENCES tracks(track_id),
    lap_id              INTEGER REFERENCES laps(lap_id),
    pos_x               REAL NOT NULL,
    pos_z               REAL NOT NULL,
    speed               REAL,
    brake_applied       INTEGER DEFAULT 0,
    throttle            REAL,
    gear                INTEGER,
    sector              INTEGER,
    distance_pct        REAL
);

CREATE INDEX IF NOT EXISTS idx_map_track ON track_map_points(track_id);

-- ============================================================
-- 12. TABELA: car_param_ranges (Ranges por carro)
-- Construída automaticamente ao ler .svm de cada carro.
-- ============================================================
CREATE TABLE IF NOT EXISTS car_param_ranges (
    range_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id              INTEGER NOT NULL REFERENCES cars(car_id),
    param_name          TEXT NOT NULL,
    section_name        TEXT NOT NULL,
    min_index           INTEGER NOT NULL,
    max_index           INTEGER NOT NULL,
    min_value           REAL,
    max_value           REAL,
    step_value          REAL,
    unit                TEXT,
    is_symmetric        INTEGER DEFAULT 1,
    UNIQUE(car_id, param_name, section_name)
);

CREATE INDEX IF NOT EXISTS idx_param_ranges_car ON car_param_ranges(car_id);

-- ============================================================
-- 13. TABELA: learning_rules (Regras causa→efeito aprendidas)
-- A IA registra: "problema X + solução Y → resultado Z".
-- Com o tempo, acumula conhecimento: "na última vez que baixei
-- asa em Silverstone com GT3, melhorou em 0.3s".
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_rules (
    rule_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    car_class           TEXT NOT NULL,
    track_id            INTEGER REFERENCES tracks(track_id),
    problem_detected    TEXT NOT NULL,
    solution_applied    TEXT NOT NULL,
    param_changed       TEXT NOT NULL,
    delta_applied       INTEGER NOT NULL,
    reward_obtained     REAL,
    lap_improvement_pct REAL,
    weather_condition   TEXT DEFAULT 'dry',
    session_type        TEXT DEFAULT 'practice',
    times_applied       INTEGER DEFAULT 1,
    times_effective     INTEGER DEFAULT 0,
    effectiveness_rate  REAL GENERATED ALWAYS AS (
        CASE WHEN times_applied > 0
             THEN CAST(times_effective AS REAL) / times_applied
             ELSE 0.0
        END
    ) STORED,
    first_seen          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_rules_class ON learning_rules(car_class);
CREATE INDEX IF NOT EXISTS idx_learning_rules_problem ON learning_rules(problem_detected);
CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_rules_unique
    ON learning_rules(car_class, COALESCE(track_id, 0), problem_detected, solution_applied, param_changed);

-- ============================================================
-- 14. TABELA: driver_preferences (Preferências aprendidas por piloto)
-- Registra exceções: "Piloto X prefere não baixar frente < 5cm"
-- ============================================================
CREATE TABLE IF NOT EXISTS driver_preferences (
    pref_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id           INTEGER NOT NULL REFERENCES driver_profiles(driver_id),
    preference_type     TEXT NOT NULL,
    param_name          TEXT,
    min_value           REAL,
    max_value           REAL,
    description         TEXT,
    is_active           INTEGER DEFAULT 1,
    learned_from        TEXT DEFAULT 'feedback',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_driver_prefs ON driver_preferences(driver_id, is_active);

-- ============================================================
-- 15. TABELA: car_similarity (Transfer Learning)
-- ============================================================
CREATE TABLE IF NOT EXISTS car_similarity (
    car_id_a            INTEGER NOT NULL REFERENCES cars(car_id),
    car_id_b            INTEGER NOT NULL REFERENCES cars(car_id),
    similarity          REAL NOT NULL,
    basis               TEXT,
    PRIMARY KEY (car_id_a, car_id_b)
);

-- ============================================================
-- VIEWS
-- ============================================================

CREATE VIEW IF NOT EXISTS v_training_summary AS
SELECT
    c.car_name,
    t.track_name,
    COUNT(td.data_id) AS total_samples,
    AVG(td.reward) AS avg_reward,
    MIN(s.best_lap_time) AS best_lap,
    COUNT(DISTINCT s.session_id) AS total_sessions,
    MAX(td.created_at) AS last_trained
FROM training_data td
JOIN sessions s ON td.session_id = s.session_id
JOIN cars c ON td.car_id = c.car_id
JOIN tracks t ON td.track_id = t.track_id
WHERE td.is_valid = 1
GROUP BY c.car_name, t.track_name;

CREATE VIEW IF NOT EXISTS v_suggestion_effectiveness AS
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

CREATE VIEW IF NOT EXISTS v_car_training_status AS
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
        WHEN COALESCE(td_count.cnt, 0) >= 30  THEN 'iniciante'
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

-- ============================================================
-- 16. TABELA: car_track_memory (Memória persistente carro×pista)
-- A IA lembra o que funcionou em sessões anteriores para
-- cada combinação ESPECÍFICA de carro + pista.
-- Cada carro pode ter mecânica diferente na mesma pista.
-- ============================================================
CREATE TABLE IF NOT EXISTS car_track_memory (
    memory_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id              INTEGER NOT NULL REFERENCES cars(car_id),
    track_id            INTEGER NOT NULL REFERENCES tracks(track_id),

    -- Estatísticas acumuladas
    total_sessions      INTEGER DEFAULT 0,
    total_laps          INTEGER DEFAULT 0,
    best_lap_time       REAL,
    avg_lap_time        REAL,

    -- Deltas médios que funcionaram (média ponderada por reward)
    optimal_deltas      TEXT,   -- JSON: {"delta_rw": 1.5, "delta_spring_f": -0.8, ...}

    -- Setup base preferido (índices do .svm que deram melhor resultado)
    best_setup_indices  TEXT,   -- JSON: {"REARWING.RWSetting": 12, ...}
    best_setup_path     TEXT,   -- Caminho do .svm com melhor resultado

    -- Características da pista aprendidas para este carro
    avg_grip            REAL,
    avg_tire_wear_rate  REAL,
    avg_fuel_per_lap    REAL,
    track_bumpiness     REAL,
    typical_weather     TEXT DEFAULT 'dry',

    -- Problemas recorrentes detectados (JSON lista)
    recurring_problems  TEXT,   -- JSON: ["understeer_entry", "high_tire_temp_rr"]

    -- Confiança nesta memória
    memory_confidence   REAL DEFAULT 0.0,

    last_session_at     TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(car_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_car_track_memory ON car_track_memory(car_id, track_id);

-- ============================================================
-- 17. TABELA: setup_library (Biblioteca de setups aprendidos)
-- Armazena todos os .svm escaneados para que a IA aprenda
-- padrões de setup — mesmo sem telemetria de volta.
-- ============================================================
CREATE TABLE IF NOT EXISTS setup_library (
    library_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path           TEXT NOT NULL UNIQUE,
    file_name           TEXT NOT NULL,
    track_folder        TEXT,
    track_id            INTEGER REFERENCES tracks(track_id),
    car_id              INTEGER REFERENCES cars(car_id),

    -- Parâmetros extraídos (JSON com todos os índices)
    param_indices       TEXT NOT NULL,

    -- Qualidade estimada
    quality_score       REAL DEFAULT 0.5,
    times_used          INTEGER DEFAULT 0,
    best_lap_with       REAL,

    -- Metadados
    file_hash           TEXT,
    learned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_modified_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_setup_library_track ON setup_library(track_id);
CREATE INDEX IF NOT EXISTS idx_setup_library_car ON setup_library(car_id);

-- ============================================================
-- 18. TABELA: session_state (Estado persistente da sessão)
-- Salva o estado completo da última sessão para restaurar
-- quando o piloto volta ao mesmo carro+pista.
-- ============================================================
CREATE TABLE IF NOT EXISTS session_state (
    state_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id              INTEGER NOT NULL REFERENCES cars(car_id),
    track_id            INTEGER NOT NULL REFERENCES tracks(track_id),
    driver_id           INTEGER REFERENCES driver_profiles(driver_id),

    -- Setup base utilizado
    base_svm_path       TEXT,
    base_svm_content    TEXT,
    base_svm_name       TEXT,

    -- Últimos deltas aplicados
    last_deltas         TEXT,       -- JSON: {"delta_rw": 1, "delta_spring_f": -2, ...}
    last_display_deltas TEXT,       -- JSON para GUI

    -- Contexto da sessão
    weather             TEXT DEFAULT 'dry',
    air_temp_c          REAL,
    track_temp_c        REAL,
    ai_level            TEXT DEFAULT 'basic',
    total_laps_driven   INTEGER DEFAULT 0,
    best_lap_time       REAL,
    session_type        TEXT DEFAULT 'practice',

    -- Warnings/notas da última sessão
    last_warnings       TEXT,       -- JSON list
    last_explanation    TEXT,

    saved_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(car_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_session_state_combo ON session_state(car_id, track_id);

-- ============================================================
-- 19. TABELA: ai_knowledge_base (Base de conhecimento da IA)
-- A IA armazena aqui o que aprendeu sobre conceitos,
-- parâmetros e mecânica. Ex: "O que é TC?", "Como ABS afeta
-- frenagem?". A IA consulta e enriquece de forma autônoma.
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_knowledge_base (
    knowledge_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    topic               TEXT NOT NULL,           -- "tc_onboard", "abs_map", "understeer"
    category            TEXT NOT NULL,            -- "parameter", "concept", "strategy"
    question            TEXT,                     -- "O que é TC Onboard?"
    answer              TEXT NOT NULL,            -- Explicação completa
    source              TEXT DEFAULT 'llm',       -- "llm", "user", "heuristic", "manual"
    confidence          REAL DEFAULT 0.7,
    times_accessed      INTEGER DEFAULT 0,
    is_verified         INTEGER DEFAULT 0,        -- 1 = confirmado por usuário
    related_params      TEXT,                     -- JSON: ["delta_tc_onboard", "delta_tc_map"]
    car_class           TEXT,                     -- NULL = universal, ou "hypercar", etc.
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_unique
    ON ai_knowledge_base(topic, category, COALESCE(car_class, 'all'));
CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON ai_knowledge_base(topic);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON ai_knowledge_base(category);

-- ============================================================
-- 20. TABELA: setup_comparison_log (Log de comparações)
-- Registra comparações feitas pela IA entre setups diferentes
-- para aprender quais mudanças melhoraram ou pioraram.
-- ============================================================
CREATE TABLE IF NOT EXISTS setup_comparison_log (
    comparison_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id              INTEGER NOT NULL REFERENCES cars(car_id),
    track_id            INTEGER NOT NULL REFERENCES tracks(track_id),
    setup_a_id          INTEGER,     -- snapshot ou library ID
    setup_b_id          INTEGER,
    param_diffs         TEXT NOT NULL, -- JSON: {"delta_rw": +2, "delta_spring_f": -1}
    lap_time_a          REAL,
    lap_time_b          REAL,
    improvement_pct     REAL,
    weather             TEXT DEFAULT 'dry',
    conclusion          TEXT,          -- "mais asa + mola macia = melhor em chuva"
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comparison_car_track
    ON setup_comparison_log(car_id, track_id);

-- Adicionar colunas TC/ABS em ai_suggestions se não existirem
-- (SQLite não suporta IF NOT EXISTS em ALTER TABLE, tratado no código)

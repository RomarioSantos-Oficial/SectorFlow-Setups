"""
database.py — Gerenciador do banco de dados SQLite.

Responsável por:
- Criar/inicializar o banco de dados com o schema
- CRUD para todas as tabelas (cars, tracks, sessions, laps, etc.)
- Modo WAL para leitura/escrita simultânea (GUI + telemetria)
- Backup automático
- Thread-safe via connection per thread

O banco é a espinha dorsal que conecta telemetria → IA → GUI.
"""

from __future__ import annotations

import io
import logging
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger("LMU_VE.database")


class DatabaseManager:
    """
    Gerenciador thread-safe do banco SQLite.

    Usa uma conexão por thread (thread-local storage) para
    permitir que a GUI leia enquanto a thread de telemetria escreve.
    O modo WAL (Write-Ahead Logging) garante que isso funcione
    sem locks bloqueantes.
    """

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna a conexão SQLite da thread atual."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_connection()

    def _init_db(self):
        """Inicializa o banco com o schema se necessário."""
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logger.error("schema.sql não encontrado em %s", schema_path)
            return
        schema_sql = schema_path.read_text(encoding="utf-8")
        with self._lock:
            self.conn.executescript(schema_sql)
            self.conn.commit()
        self._migrate_schema()
        logger.info("Banco de dados inicializado: %s", self.db_path)

    def close(self):
        """Fecha a conexão da thread atual."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    @contextmanager
    def transaction(self):
        """
        Context manager para transações atômicas.
        Garante commit em caso de sucesso ou rollback em caso de erro.

        Uso:
            with db.transaction():
                db.conn.execute("INSERT INTO ...")
                db.conn.execute("INSERT INTO ...")
        """
        conn = self.conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ============================================================
    # BACKUP
    # ============================================================
    def backup(self, backup_dir) -> Path:
        """
        Cria backup do banco de dados com timestamp.

        Returns:
            Caminho do arquivo de backup criado.
        """
        backup_dir = Path(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"lmu_engineer_backup_{timestamp}.db"
        shutil.copy2(str(self.db_path), str(backup_file))
        logger.info("Backup criado: %s", backup_file)
        return backup_file

    # ============================================================
    # CARS
    # ============================================================
    def get_or_create_car(self, car_name: str, car_class: str = "",
                          car_class_normalized: str = "") -> int:
        """
        Busca um carro pelo nome. Se não existir, cria um novo registro.
        Detecta informações do carro pelo nome e classe.

        Args:
            car_name: Nome do carro (ex: "Toyota GR010 Hybrid")
            car_class: Classe do carro (ex: "Hypercar")

        Returns:
            car_id do registro existente ou criado.
        """
        row = self.conn.execute(
            "SELECT car_id FROM cars WHERE car_name = ?", (car_name,)
        ).fetchone()
        if row:
            return row["car_id"]

        # Normalizar classe para código
        if not car_class_normalized:
            car_class_normalized = self._normalize_class(car_class)

        # Detectar hybrid pelo nome/classe
        has_hybrid = 1 if any(kw in car_name.lower() for kw in
                              ("hybrid", "gr010", "9x8")) else 0

        # Detectar BoP (GT3 geralmente tem)
        has_bop = 1 if car_class_normalized == "lmgt3" else 0

        cursor = self.conn.execute(
            """INSERT INTO cars (car_name, car_class, car_class_normalized,
               has_hybrid, has_bop)
               VALUES (?, ?, ?, ?, ?)""",
            (car_name, car_class, car_class_normalized, has_hybrid, has_bop)
        )
        self.conn.commit()
        logger.info("Novo carro registrado: %s [%s]", car_name, car_class)
        return cursor.lastrowid

    def _normalize_class(self, car_class: str) -> str:
        """Normaliza a classe do carro para código interno."""
        cl = car_class.lower().strip()
        if any(kw in cl for kw in ("hypercar", "lmh", "lmdh")):
            return "hypercar"
        if "lmp2" in cl:
            return "lmp2"
        if any(kw in cl for kw in ("gt3", "lmgt3", "gte")):
            return "lmgt3"
        return cl if cl else "unknown"

    def get_car(self, car_id: int) -> dict | None:
        """Retorna dados de um carro pelo ID."""
        row = self.conn.execute(
            "SELECT * FROM cars WHERE car_id = ?", (car_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_cars(self) -> list[dict]:
        """Lista todos os carros cadastrados."""
        rows = self.conn.execute("SELECT * FROM cars ORDER BY car_class, car_name").fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # TRACKS
    # ============================================================
    def get_or_create_track(self, track_name: str, folder_name: str = "") -> int:
        """
        Busca pista pelo nome. Cria se não existir.

        Args:
            track_name: Nome da pista da Shared Memory (ex: "le_mans_24h")
            folder_name: Nome da pasta real (pode ser igual ao track_name)

        Returns:
            track_id
        """
        if not folder_name:
            folder_name = track_name

        row = self.conn.execute(
            "SELECT track_id FROM tracks WHERE folder_name = ?", (folder_name,)
        ).fetchone()
        if row:
            return row["track_id"]

        cursor = self.conn.execute(
            "INSERT INTO tracks (track_name, folder_name) VALUES (?, ?)",
            (track_name, folder_name)
        )
        self.conn.commit()
        logger.info("Nova pista registrada: %s", track_name)
        return cursor.lastrowid

    def list_tracks(self) -> list[dict]:
        """Lista todas as pistas cadastradas."""
        rows = self.conn.execute("SELECT * FROM tracks ORDER BY track_name").fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # DRIVER PROFILES
    # ============================================================
    def get_or_create_driver(self, driver_name: str) -> int:
        """Busca ou cria perfil de piloto."""
        row = self.conn.execute(
            "SELECT driver_id FROM driver_profiles WHERE driver_name = ?",
            (driver_name,)
        ).fetchone()
        if row:
            return row["driver_id"]

        cursor = self.conn.execute(
            "INSERT INTO driver_profiles (driver_name) VALUES (?)",
            (driver_name,)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_driver_stats(self, driver_id: int, consistency: float):
        """Atualiza estatísticas calculadas do piloto."""
        self.conn.execute(
            """UPDATE driver_profiles SET consistency = ?, updated_at = CURRENT_TIMESTAMP
               WHERE driver_id = ?""",
            (consistency, driver_id)
        )
        self.conn.commit()

    # ============================================================
    # SESSIONS
    # ============================================================
    def create_session(self, driver_id: int, car_id: int, track_id: int,
                       session_type: str = "practice", weather: str = "dry",
                       air_temp: float = 0, track_temp: float = 0) -> int:
        """Cria nova sessão de jogo."""
        cursor = self.conn.execute(
            """INSERT INTO sessions (driver_id, car_id, track_id, session_type,
               weather, air_temp_c, track_temp_c)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (driver_id, car_id, track_id, session_type, weather, air_temp, track_temp)
        )
        self.conn.commit()
        return cursor.lastrowid

    def end_session(self, session_id: int, total_laps: int, best_lap: float):
        """Finaliza uma sessão."""
        self.conn.execute(
            """UPDATE sessions SET ended_at = CURRENT_TIMESTAMP,
               total_laps = ?, best_lap_time = ?
               WHERE session_id = ?""",
            (total_laps, best_lap, session_id)
        )
        self.conn.commit()

    def list_sessions(self, car_id: int | None = None,
                      track_id: int | None = None,
                      limit: int = 50) -> list[dict]:
        """Lista sessões com filtros opcionais."""
        query = """
            SELECT s.*, c.car_name, c.car_class, t.track_name
            FROM sessions s
            JOIN cars c ON s.car_id = c.car_id
            JOIN tracks t ON s.track_id = t.track_id
            WHERE 1=1
        """
        params: list = []
        if car_id is not None:
            query += " AND s.car_id = ?"
            params.append(car_id)
        if track_id is not None:
            query += " AND s.track_id = ?"
            params.append(track_id)
        query += " ORDER BY s.started_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # LAPS
    # ============================================================
    def insert_lap(self, session_id: int, lap_data: dict) -> int:
        """
        Insere dados de uma volta completada.

        Args:
            session_id: ID da sessão atual
            lap_data: Dicionário com todos os campos da tabela laps

        Returns:
            lap_id
        """
        # Campos obrigatórios + opcionais com defaults
        fields = ["session_id", "lap_number", "lap_time", "is_valid",
                   "fuel_at_start", "fuel_used"]

        # Temperaturas (12 campos)
        fields.extend([
            "temp_fl_inner", "temp_fl_middle", "temp_fl_outer",
            "temp_fr_inner", "temp_fr_middle", "temp_fr_outer",
            "temp_rl_inner", "temp_rl_middle", "temp_rl_outer",
            "temp_rr_inner", "temp_rr_middle", "temp_rr_outer",
        ])

        # Pressões, desgaste, carga (12 campos)
        fields.extend([
            "pressure_fl", "pressure_fr", "pressure_rl", "pressure_rr",
            "wear_fl", "wear_fr", "wear_rl", "wear_rr",
            "load_fl", "load_fr", "load_rl", "load_rr",
        ])

        # Aero/Suspensão + dinâmica
        fields.extend([
            "ride_height_f", "ride_height_r", "downforce_f", "downforce_r",
            "max_speed", "avg_pitch", "avg_roll", "avg_heave",
            "max_brake_temp_fl", "max_brake_temp_fr",
            "max_brake_temp_rl", "max_brake_temp_rr",
        ])

        lap_data["session_id"] = session_id
        values = [lap_data.get(f) for f in fields]
        placeholders = ", ".join("?" * len(fields))
        field_names = ", ".join(fields)

        cursor = self.conn.execute(
            f"INSERT INTO laps ({field_names}) VALUES ({placeholders})", values
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_session_laps(self, session_id: int) -> list[dict]:
        """Retorna todas as voltas de uma sessão."""
        rows = self.conn.execute(
            "SELECT * FROM laps WHERE session_id = ? ORDER BY lap_number",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_lap_times(self, session_id: int, count: int = 5) -> list[float]:
        """Retorna os N últimos tempos de volta válidos."""
        rows = self.conn.execute(
            """SELECT lap_time FROM laps
               WHERE session_id = ? AND is_valid = 1 AND lap_time > 0
               ORDER BY lap_number DESC LIMIT ?""",
            (session_id, count)
        ).fetchall()
        return [r["lap_time"] for r in rows]

    # ============================================================
    # SETUP SNAPSHOTS
    # ============================================================
    def save_setup_snapshot(self, session_id: int, setup_data: dict) -> int:
        """Salva um snapshot completo do setup .svm."""
        fields = list(setup_data.keys())
        fields.insert(0, "session_id")
        setup_data["session_id"] = session_id
        values = [setup_data.get(f) for f in fields]
        placeholders = ", ".join("?" * len(fields))
        field_names = ", ".join(fields)

        cursor = self.conn.execute(
            f"INSERT INTO setup_snapshots ({field_names}) VALUES ({placeholders})",
            values
        )
        self.conn.commit()
        return cursor.lastrowid

    # ============================================================
    # AI SUGGESTIONS
    # ============================================================
    def save_suggestion(self, session_id: int, after_lap: int,
                        source: str, deltas: dict,
                        explanation: str = "") -> int:
        """Registra uma sugestão da IA."""
        cursor = self.conn.execute(
            """INSERT INTO ai_suggestions
               (session_id, after_lap, source,
                delta_rw, delta_spring_f, delta_spring_r,
                delta_camber_f, delta_camber_r,
                delta_pressure_f, delta_pressure_r,
                delta_brake_press, delta_arb_f, delta_arb_r,
                explanation_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, after_lap, source,
             deltas.get("rw", 0), deltas.get("spring_f", 0), deltas.get("spring_r", 0),
             deltas.get("camber_f", 0), deltas.get("camber_r", 0),
             deltas.get("pressure_f", 0), deltas.get("pressure_r", 0),
             deltas.get("brake_press", 0), deltas.get("arb_f", 0), deltas.get("arb_r", 0),
             explanation)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_suggestion_feedback(self, suggestion_id: int,
                                   accepted: bool, feedback_bias: float,
                                   confidence: float):
        """Atualiza o feedback do usuário sobre uma sugestão."""
        self.conn.execute(
            """UPDATE ai_suggestions SET
               user_accepted = ?, user_feedback_bias = ?, user_confidence = ?
               WHERE suggestion_id = ?""",
            (1 if accepted else 0, feedback_bias, confidence, suggestion_id)
        )
        self.conn.commit()

    def update_suggestion_result(self, suggestion_id: int,
                                 lap_time_before: float, lap_time_after: float,
                                 reward_score: float):
        """Atualiza o resultado medido de uma sugestão."""
        improvement = 0.0
        if lap_time_before > 0:
            improvement = ((lap_time_before - lap_time_after) / lap_time_before) * 100

        self.conn.execute(
            """UPDATE ai_suggestions SET
               lap_time_before = ?, lap_time_after = ?,
               improvement_pct = ?, reward_score = ?
               WHERE suggestion_id = ?""",
            (lap_time_before, lap_time_after, improvement, reward_score,
             suggestion_id)
        )
        self.conn.commit()

    # ============================================================
    # TRAINING DATA
    # ============================================================
    def save_training_data(self, session_id: int, car_id: int, track_id: int,
                           input_vec: np.ndarray, output_vec: np.ndarray,
                           reward: float, weight: float = 1.0) -> int:
        """
        Salva um exemplo de treinamento (input/output/reward).

        Os vetores numpy são serializados como BLOB binário para
        eficiência de armazenamento e velocidade de leitura.
        """
        input_blob = self._numpy_to_blob(input_vec)
        output_blob = self._numpy_to_blob(output_vec)

        cursor = self.conn.execute(
            """INSERT INTO training_data
               (session_id, car_id, track_id, input_vector, output_vector,
                reward, weight)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, car_id, track_id, input_blob, output_blob, reward, weight)
        )
        self.conn.commit()
        return cursor.lastrowid

    def load_training_data(self, car_id: int, track_id: int | None = None,
                           limit: int = 0) -> list[dict]:
        """
        Carrega dados de treinamento para um combo carro (e opcionalmente pista).

        Returns:
            Lista de dicts com 'input', 'output', 'reward', 'weight'.
        """
        query = """
            SELECT input_vector, output_vector, reward, weight
            FROM training_data
            WHERE car_id = ? AND is_valid = 1
        """
        params: list = [car_id]
        if track_id is not None:
            query += " AND track_id = ?"
            params.append(track_id)
        query += " ORDER BY reward DESC"
        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            result.append({
                "input": self._blob_to_numpy(r["input_vector"]),
                "output": self._blob_to_numpy(r["output_vector"]),
                "reward": r["reward"],
                "weight": r["weight"],
            })
        return result

    def count_training_data(self, car_id: int, track_id: int | None = None) -> int:
        """Conta exemplos de treinamento para um combo."""
        query = "SELECT COUNT(*) as cnt FROM training_data WHERE car_id = ? AND is_valid = 1"
        params: list = [car_id]
        if track_id is not None:
            query += " AND track_id = ?"
            params.append(track_id)
        row = self.conn.execute(query, params).fetchone()
        return row["cnt"] if row else 0

    # ============================================================
    # MODEL CHECKPOINTS
    # ============================================================
    def save_checkpoint(self, car_id: int, track_id: int, filename: str,
                        epoch: int, total_samples: int,
                        avg_reward: float, best_lap: float) -> int:
        """Registra um checkpoint do modelo."""
        # Desativar checkpoints anteriores deste combo
        self.conn.execute(
            """UPDATE model_checkpoints SET is_active = 0
               WHERE car_id = ? AND track_id = ?""",
            (car_id, track_id)
        )
        cursor = self.conn.execute(
            """INSERT INTO model_checkpoints
               (car_id, track_id, filename, epoch, total_samples,
                avg_reward, best_lap_time, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (car_id, track_id, filename, epoch, total_samples, avg_reward, best_lap)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_active_checkpoint(self, car_id: int, track_id: int) -> dict | None:
        """Retorna o checkpoint ativo para um combo carro+pista."""
        row = self.conn.execute(
            """SELECT * FROM model_checkpoints
               WHERE car_id = ? AND track_id = ? AND is_active = 1
               ORDER BY created_at DESC LIMIT 1""",
            (car_id, track_id)
        ).fetchone()
        return dict(row) if row else None

    # ============================================================
    # CAR PARAM RANGES
    # ============================================================
    def upsert_param_range(self, car_id: int, param_name: str,
                           section_name: str, index_val: int,
                           phys_value: float | None = None,
                           unit: str = ""):
        """
        Insere ou atualiza o range de um parâmetro para um carro.
        Expande min/max conforme novos valores são encontrados.
        """
        row = self.conn.execute(
            """SELECT range_id, min_index, max_index, min_value, max_value
               FROM car_param_ranges
               WHERE car_id = ? AND param_name = ? AND section_name = ?""",
            (car_id, param_name, section_name)
        ).fetchone()

        if row:
            new_min_idx = min(row["min_index"], index_val)
            new_max_idx = max(row["max_index"], index_val)
            new_min_val = row["min_value"]
            new_max_val = row["max_value"]
            if phys_value is not None:
                if new_min_val is None or phys_value < new_min_val:
                    new_min_val = phys_value
                if new_max_val is None or phys_value > new_max_val:
                    new_max_val = phys_value

            self.conn.execute(
                """UPDATE car_param_ranges SET
                   min_index = ?, max_index = ?, min_value = ?, max_value = ?
                   WHERE range_id = ?""",
                (new_min_idx, new_max_idx, new_min_val, new_max_val, row["range_id"])
            )
        else:
            self.conn.execute(
                """INSERT INTO car_param_ranges
                   (car_id, param_name, section_name, min_index, max_index,
                    min_value, max_value, unit)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (car_id, param_name, section_name, index_val, index_val,
                 phys_value, phys_value, unit)
            )
        self.conn.commit()

    def get_param_ranges(self, car_id: int) -> dict[str, dict]:
        """
        Retorna todos os ranges de parâmetros para um carro.

        Returns:
            Dict: {f"{section_name}.{param_name}": {min_index, max_index, ...}}
        """
        rows = self.conn.execute(
            "SELECT * FROM car_param_ranges WHERE car_id = ?", (car_id,)
        ).fetchall()
        result = {}
        for r in rows:
            key = f"{r['section_name']}.{r['param_name']}"
            result[key] = dict(r)
        return result

    # ============================================================
    # ESTATÍSTICAS / DASHBOARDS
    # ============================================================
    def get_summary_stats(self) -> dict:
        """Retorna estatísticas gerais para o dashboard."""
        stats = {}
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM laps").fetchone()
        stats["total_laps"] = row["cnt"] if row else 0

        row = self.conn.execute("SELECT COUNT(*) as cnt FROM cars").fetchone()
        stats["total_cars"] = row["cnt"] if row else 0

        row = self.conn.execute("SELECT COUNT(*) as cnt FROM tracks").fetchone()
        stats["total_tracks"] = row["cnt"] if row else 0

        row = self.conn.execute("SELECT COUNT(*) as cnt FROM training_data WHERE is_valid=1").fetchone()
        stats["total_training"] = row["cnt"] if row else 0

        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_suggestions WHERE user_accepted IS NOT NULL"
        ).fetchone()
        stats["total_suggestions"] = row["cnt"] if row else 0

        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_suggestions WHERE user_accepted = 1"
        ).fetchone()
        stats["accepted_suggestions"] = row["cnt"] if row else 0

        return stats

    # ============================================================
    # UTILITÁRIOS (serialização numpy ↔ blob)
    # ============================================================
    @staticmethod
    def _numpy_to_blob(arr: np.ndarray) -> bytes:
        """Serializa um array numpy para bytes (BLOB do SQLite)."""
        buf = io.BytesIO()
        np.save(buf, arr.astype(np.float32))
        return buf.getvalue()

    @staticmethod
    def _blob_to_numpy(blob: bytes) -> np.ndarray:
        """Deserializa bytes (BLOB) para array numpy."""
        buf = io.BytesIO(blob)
        return np.load(buf, allow_pickle=False)

    # ============================================================
    # LEARNING RULES (Causa → Efeito → Resultado)
    # ============================================================
    def record_learning_rule(self, car_class: str, track_id: int | None,
                             problem: str, solution: str,
                             param: str, delta: int,
                             reward: float, improvement_pct: float,
                             weather: str = "dry",
                             session_type: str = "practice"):
        """
        Registra ou atualiza uma regra causa→efeito aprendida.
        Se já existe (mesmo car_class+track+problem+solution+param),
        incrementa contadores e atualiza efetividade.
        """
        track_val = track_id if track_id else 0
        row = self.conn.execute(
            """SELECT rule_id, times_applied, times_effective, reward_obtained
               FROM learning_rules
               WHERE car_class = ? AND COALESCE(track_id, 0) = ?
               AND problem_detected = ? AND solution_applied = ?
               AND param_changed = ?""",
            (car_class, track_val, problem, solution, param)
        ).fetchone()

        if row:
            new_times = row["times_applied"] + 1
            new_effective = row["times_effective"] + (1 if reward > 0.1 else 0)
            avg_reward = (row["reward_obtained"] * row["times_applied"] + reward) / new_times
            self.conn.execute(
                """UPDATE learning_rules SET
                   times_applied = ?, times_effective = ?,
                   reward_obtained = ?, lap_improvement_pct = ?,
                   last_seen = CURRENT_TIMESTAMP
                   WHERE rule_id = ?""",
                (new_times, new_effective, avg_reward, improvement_pct, row["rule_id"])
            )
        else:
            self.conn.execute(
                """INSERT INTO learning_rules
                   (car_class, track_id, problem_detected, solution_applied,
                    param_changed, delta_applied, reward_obtained,
                    lap_improvement_pct, weather_condition, session_type,
                    times_applied, times_effective)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (car_class, track_id, problem, solution, param, delta,
                 reward, improvement_pct, weather, session_type,
                 1 if reward > 0.1 else 0)
            )
        self.conn.commit()

    def get_effective_rules(self, car_class: str,
                            track_id: int | None = None,
                            min_effectiveness: float = 0.6,
                            min_applications: int = 3) -> list[dict]:
        """
        Consulta regras que funcionaram bem no passado.
        Usadas pela IA para priorizar soluções conhecidas.
        """
        query = """
            SELECT * FROM learning_rules
            WHERE car_class = ? AND times_applied >= ?
            AND effectiveness_rate >= ?
        """
        params: list = [car_class, min_applications, min_effectiveness]
        if track_id is not None:
            query += " AND (track_id = ? OR track_id IS NULL)"
            params.append(track_id)
        query += " ORDER BY effectiveness_rate DESC, times_applied DESC"

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_failed_rules(self, car_class: str,
                         min_applications: int = 3) -> list[dict]:
        """
        Consulta regras que falharam repetidamente.
        A IA deve EVITAR essas combinações.
        """
        rows = self.conn.execute(
            """SELECT * FROM learning_rules
               WHERE car_class = ? AND times_applied >= ?
               AND effectiveness_rate < 0.3
               ORDER BY effectiveness_rate ASC""",
            (car_class, min_applications)
        ).fetchall()
        return [dict(r) for r in rows]

    # ============================================================
    # DRIVER PREFERENCES (Perfil do piloto)
    # ============================================================
    def get_driver_profile(self, driver_id: int) -> dict | None:
        """Retorna perfil completo do piloto."""
        row = self.conn.execute(
            "SELECT * FROM driver_profiles WHERE driver_id = ?", (driver_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_driver_profile(self, driver_id: int,
                              aggression: float | None = None,
                              braking_style: float | None = None,
                              consistency: float | None = None):
        """Atualiza métricas comportamentais do piloto."""
        updates = []
        params: list = []
        if aggression is not None:
            updates.append("aggression = ?")
            params.append(aggression)
        if braking_style is not None:
            updates.append("braking_style = ?")
            params.append(braking_style)
        if consistency is not None:
            updates.append("consistency = ?")
            params.append(consistency)
        if not updates:
            return
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(driver_id)
        self.conn.execute(
            f"UPDATE driver_profiles SET {', '.join(updates)} WHERE driver_id = ?",
            params
        )
        self.conn.commit()

    def save_driver_preference(self, driver_id: int,
                               preference_type: str,
                               param_name: str = "",
                               min_value: float | None = None,
                               max_value: float | None = None,
                               description: str = ""):
        """
        Registra uma preferência/exceção do piloto.
        Ex: "Piloto X não quer ride height frente < 4cm"
        """
        self.conn.execute(
            """INSERT INTO driver_preferences
               (driver_id, preference_type, param_name,
                min_value, max_value, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (driver_id, preference_type, param_name,
             min_value, max_value, description)
        )
        self.conn.commit()

    def get_driver_preferences(self, driver_id: int) -> list[dict]:
        """Retorna todas as preferências ativas do piloto."""
        rows = self.conn.execute(
            """SELECT * FROM driver_preferences
               WHERE driver_id = ? AND is_active = 1
               ORDER BY preference_type""",
            (driver_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def compute_driver_aggression(self, driver_id: int) -> float:
        """
        Calcula a agressividade do piloto baseada nos dados históricos.
        Olha: brake bias, TC/ABS preferidos, estilo de freio, feedback.

        Returns:
            0.0 (muito conservador) a 1.0 (muito agressivo)
        """
        # Olhar as últimas 20 sugestões aceitas
        rows = self.conn.execute(
            """SELECT s.delta_brake_press, s.user_feedback_bias
               FROM ai_suggestions s
               JOIN sessions sess ON s.session_id = sess.session_id
               WHERE sess.driver_id = ? AND s.user_accepted = 1
               ORDER BY s.created_at DESC LIMIT 20""",
            (driver_id,)
        ).fetchall()

        if not rows:
            return 0.5  # Neutro

        # Se aceita mais asa / mais pressão de freio → conservador
        # Se aceita menos asa / menos ABS → agressivo
        aggressiveness_signals = []
        for r in rows:
            bias = r["user_feedback_bias"] or 0
            brake = r["delta_brake_press"] or 0
            # Brake positivo = mais pressão = agressivo
            aggressiveness_signals.append(0.5 + (brake * 0.1) + (bias * 0.1))

        avg = sum(aggressiveness_signals) / len(aggressiveness_signals)
        return max(0.0, min(1.0, avg))

    # ============================================================
    # CAR+TRACK MEMORY (Memória persistente entre sessões)
    # ============================================================

    def load_car_track_memory(self, car_id: int, track_id: int) -> dict | None:
        """Carrega a memória persistente de um combo carro×pista."""
        row = self.conn.execute(
            "SELECT * FROM car_track_memory WHERE car_id = ? AND track_id = ?",
            (car_id, track_id),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        # Deserializar JSON
        import json
        for field in ("optimal_deltas", "best_setup_indices", "recurring_problems"):
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    result[field] = None
        return result

    def save_car_track_memory(self, car_id: int, track_id: int,
                              data: dict):
        """
        Salva/atualiza memória persistente de um combo carro×pista.

        Args:
            data: Dict com campos a atualizar (optimal_deltas, best_lap_time, etc.)
        """
        import json

        # Serializar campos JSON
        for field in ("optimal_deltas", "best_setup_indices", "recurring_problems"):
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field], ensure_ascii=False)

        existing = self.conn.execute(
            "SELECT memory_id FROM car_track_memory WHERE car_id = ? AND track_id = ?",
            (car_id, track_id),
        ).fetchone()

        if existing:
            sets = ", ".join(f"{k} = ?" for k in data.keys())
            vals = list(data.values()) + [car_id, track_id]
            self.conn.execute(
                f"UPDATE car_track_memory SET {sets}, updated_at = CURRENT_TIMESTAMP "
                f"WHERE car_id = ? AND track_id = ?",
                vals,
            )
        else:
            data["car_id"] = car_id
            data["track_id"] = track_id
            cols = ", ".join(data.keys())
            placeholders = ", ".join("?" for _ in data)
            self.conn.execute(
                f"INSERT INTO car_track_memory ({cols}) VALUES ({placeholders})",
                list(data.values()),
            )
        self.conn.commit()

    def get_best_setup_for_car_track(self, car_id: int,
                                     track_id: int) -> dict | None:
        """Retorna o melhor setup já usado para este carro×pista."""
        row = self.conn.execute(
            """SELECT ss.* FROM setup_snapshots ss
               JOIN sessions s ON ss.session_id = s.session_id
               WHERE s.car_id = ? AND s.track_id = ?
               ORDER BY (
                   SELECT MIN(l.lap_time)
                   FROM laps l
                   WHERE l.session_id = s.session_id AND l.is_valid = 1
                   AND l.lap_number > ss.applied_at_lap
               ) ASC NULLS LAST
               LIMIT 1""",
            (car_id, track_id),
        ).fetchone()
        return dict(row) if row else None

    def get_car_track_history(self, car_id: int, track_id: int,
                              limit: int = 10) -> list[dict]:
        """Retorna as últimas sessões deste carro×pista."""
        rows = self.conn.execute(
            """SELECT s.session_id, s.started_at, s.total_laps,
                      s.best_lap_time, s.weather,
                      COUNT(l.lap_id) AS laps_recorded,
                      AVG(l.lap_time) AS avg_lap_time
               FROM sessions s
               LEFT JOIN laps l ON s.session_id = l.session_id AND l.is_valid = 1
               WHERE s.car_id = ? AND s.track_id = ?
               GROUP BY s.session_id
               ORDER BY s.started_at DESC
               LIMIT ?""",
            (car_id, track_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_effective_deltas_history(self, car_id: int, track_id: int,
                                    min_reward: float = 0.1) -> list[dict]:
        """
        Retorna deltas que produziram reward positivo para este carro×pista.
        Usado para calcular a média de deltas que funcionaram.
        """
        rows = self.conn.execute(
            """SELECT td.output_vector, td.reward
               FROM training_data td
               WHERE td.car_id = ? AND td.track_id = ?
               AND td.reward >= ? AND td.is_valid = 1
               ORDER BY td.reward DESC
               LIMIT 100""",
            (car_id, track_id, min_reward),
        ).fetchall()
        result = []
        for r in rows:
            result.append({
                "output": self._blob_to_numpy(r["output_vector"]),
                "reward": r["reward"],
            })
        return result

    # ============================================================
    # SETUP LIBRARY (Biblioteca de setups para aprendizagem)
    # ============================================================

    def save_setup_to_library(self, file_path: str, file_name: str,
                              track_folder: str, param_indices: dict,
                              track_id: int | None = None,
                              car_id: int | None = None,
                              file_hash: str = "") -> int:
        """Salva um setup escaneado na biblioteca."""
        import json

        existing = self.conn.execute(
            "SELECT library_id FROM setup_library WHERE file_path = ?",
            (file_path,),
        ).fetchone()

        indices_json = json.dumps(param_indices, ensure_ascii=False)

        if existing:
            self.conn.execute(
                """UPDATE setup_library SET param_indices = ?, track_folder = ?,
                   track_id = ?, car_id = ?, file_hash = ?
                   WHERE library_id = ?""",
                (indices_json, track_folder, track_id, car_id,
                 file_hash, existing["library_id"]),
            )
            self.conn.commit()
            return existing["library_id"]

        cursor = self.conn.execute(
            """INSERT INTO setup_library
               (file_path, file_name, track_folder, track_id, car_id,
                param_indices, file_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (file_path, file_name, track_folder, track_id, car_id,
             indices_json, file_hash),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_setups_for_track(self, track_id: int) -> list[dict]:
        """Retorna todos os setups da biblioteca para uma pista."""
        import json
        rows = self.conn.execute(
            """SELECT * FROM setup_library
               WHERE track_id = ?
               ORDER BY quality_score DESC""",
            (track_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["param_indices"] = json.loads(d["param_indices"])
            except (json.JSONDecodeError, TypeError):
                d["param_indices"] = {}
            result.append(d)
        return result

    def get_all_library_setups(self) -> list[dict]:
        """Retorna todos os setups da biblioteca."""
        import json
        rows = self.conn.execute(
            "SELECT * FROM setup_library ORDER BY learned_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["param_indices"] = json.loads(d["param_indices"])
            except (json.JSONDecodeError, TypeError):
                d["param_indices"] = {}
            result.append(d)
        return result

    def update_setup_quality(self, library_id: int, quality_score: float,
                             best_lap: float | None = None):
        """Atualiza a qualidade de um setup na biblioteca."""
        if best_lap is not None:
            self.conn.execute(
                """UPDATE setup_library SET quality_score = ?, best_lap_with = ?,
                   times_used = times_used + 1 WHERE library_id = ?""",
                (quality_score, best_lap, library_id),
            )
        else:
            self.conn.execute(
                """UPDATE setup_library SET quality_score = ?,
                   times_used = times_used + 1 WHERE library_id = ?""",
                (quality_score, library_id),
            )
        self.conn.commit()

    def count_library_setups(self) -> int:
        """Conta quantos setups estão na biblioteca."""
        row = self.conn.execute("SELECT COUNT(*) FROM setup_library").fetchone()
        return row[0] if row else 0

    # ============================================================
    # ESTRATÉGIA DE SESSÃO
    # ============================================================
    def get_avg_lap_time(self, car_id: int, track_id: int,
                         valid_only: bool = True) -> float | None:
        """
        Retorna o tempo médio de volta para um carro+pista do histórico.

        Args:
            car_id: ID do carro
            track_id: ID da pista
            valid_only: Se True, considera apenas voltas válidas

        Returns:
            Tempo médio em segundos, ou None se não houver dados
        """
        query = """
            SELECT AVG(l.lap_time) as avg_time
            FROM laps l
            JOIN sessions s ON l.session_id = s.session_id
            WHERE s.car_id = ? AND s.track_id = ?
              AND l.lap_time > 0
        """
        params = [car_id, track_id]
        if valid_only:
            query += " AND l.is_valid = 1"

        row = self.conn.execute(query, params).fetchone()
        if row and row["avg_time"]:
            return float(row["avg_time"])
        return None

    def get_avg_fuel_consumption(self, car_id: int, track_id: int) -> float | None:
        """
        Retorna o consumo médio de combustível por volta (litros).

        Args:
            car_id: ID do carro
            track_id: ID da pista

        Returns:
            Consumo médio em litros/volta, ou None se não houver dados
        """
        query = """
            SELECT AVG(l.fuel_used) as avg_fuel
            FROM laps l
            JOIN sessions s ON l.session_id = s.session_id
            WHERE s.car_id = ? AND s.track_id = ?
              AND l.fuel_used > 0
        """
        row = self.conn.execute(query, [car_id, track_id]).fetchone()
        if row and row["avg_fuel"]:
            return float(row["avg_fuel"])
        return None

    # ============================================================
    # SESSION STATE (Persistência entre sessões)
    # ============================================================
    def save_session_state(self, car_id: int, track_id: int,
                           state: dict):
        """
        Salva o estado completo da sessão atual para restaurar depois.
        Chamado quando: setup é carregado, sugestão aplicada, sessão encerra.
        """
        import json

        # Serializar campos JSON
        for field in ("last_deltas", "last_display_deltas", "last_warnings"):
            if field in state and not isinstance(state.get(field), str):
                state[field] = json.dumps(
                    state[field], ensure_ascii=False,
                )

        existing = self.conn.execute(
            "SELECT state_id FROM session_state "
            "WHERE car_id = ? AND track_id = ?",
            (car_id, track_id),
        ).fetchone()

        if existing:
            sets = ", ".join(f"{k} = ?" for k in state)
            vals = list(state.values()) + [car_id, track_id]
            self.conn.execute(
                f"UPDATE session_state SET {sets}, "
                f"saved_at = CURRENT_TIMESTAMP "
                f"WHERE car_id = ? AND track_id = ?",
                vals,
            )
        else:
            state["car_id"] = car_id
            state["track_id"] = track_id
            cols = ", ".join(state)
            ph = ", ".join("?" for _ in state)
            self.conn.execute(
                f"INSERT INTO session_state ({cols}) VALUES ({ph})",
                list(state.values()),
            )
        self.conn.commit()

    def load_session_state(self, car_id: int,
                           track_id: int) -> dict | None:
        """
        Carrega estado salvo de sessão anterior para este carro×pista.
        Retorna None se não houver estado salvo.
        """
        import json

        row = self.conn.execute(
            "SELECT * FROM session_state "
            "WHERE car_id = ? AND track_id = ?",
            (car_id, track_id),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        for field in ("last_deltas", "last_display_deltas",
                      "last_warnings"):
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    result[field] = None
        return result

    def delete_session_state(self, car_id: int, track_id: int):
        """Remove estado de sessão salvo."""
        self.conn.execute(
            "DELETE FROM session_state "
            "WHERE car_id = ? AND track_id = ?",
            (car_id, track_id),
        )
        self.conn.commit()

    # ============================================================
    # AI KNOWLEDGE BASE (Base de conhecimento autônoma)
    # ============================================================
    def save_knowledge(self, topic: str, category: str,
                       answer: str, question: str = "",
                       source: str = "llm",
                       confidence: float = 0.7,
                       related_params: list | None = None,
                       car_class: str | None = None) -> int:
        """
        Salva um fato na base de conhecimento da IA.
        Se já existe (mesmo topic+category+car_class), atualiza.
        """
        import json

        class_val = car_class or "all"
        params_json = (json.dumps(related_params, ensure_ascii=False)
                       if related_params else None)

        existing = self.conn.execute(
            "SELECT knowledge_id FROM ai_knowledge_base "
            "WHERE topic = ? AND category = ? "
            "AND COALESCE(car_class, 'all') = ?",
            (topic, category, class_val),
        ).fetchone()

        if existing:
            self.conn.execute(
                """UPDATE ai_knowledge_base SET
                   answer = ?, question = ?, source = ?,
                   confidence = ?, related_params = ?,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE knowledge_id = ?""",
                (answer, question, source, confidence,
                 params_json, existing["knowledge_id"]),
            )
            self.conn.commit()
            return existing["knowledge_id"]

        cursor = self.conn.execute(
            """INSERT INTO ai_knowledge_base
               (topic, category, question, answer, source,
                confidence, related_params, car_class)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (topic, category, question, answer, source,
             confidence, params_json,
             car_class),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_knowledge(self, topic: str,
                      category: str | None = None,
                      car_class: str | None = None) -> list[dict]:
        """Busca conhecimento sobre um tópico."""
        import json

        query = "SELECT * FROM ai_knowledge_base WHERE topic = ?"
        params: list = [topic]
        if category:
            query += " AND category = ?"
            params.append(category)
        if car_class:
            query += (" AND (car_class = ? "
                      "OR car_class IS NULL)")
            params.append(car_class)

        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("related_params"):
                try:
                    d["related_params"] = json.loads(
                        d["related_params"],
                    )
                except (json.JSONDecodeError, TypeError):
                    d["related_params"] = []
            # Incrementar acesso
            self.conn.execute(
                "UPDATE ai_knowledge_base "
                "SET times_accessed = times_accessed + 1 "
                "WHERE knowledge_id = ?",
                (d["knowledge_id"],),
            )
            result.append(d)
        self.conn.commit()
        return result

    def search_knowledge(self, query_text: str,
                         limit: int = 10) -> list[dict]:
        """Busca na base de conhecimento por texto livre."""
        import json

        rows = self.conn.execute(
            """SELECT * FROM ai_knowledge_base
               WHERE topic LIKE ? OR answer LIKE ?
               OR question LIKE ?
               ORDER BY confidence DESC, times_accessed DESC
               LIMIT ?""",
            (f"%{query_text}%", f"%{query_text}%",
             f"%{query_text}%", limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("related_params"):
                try:
                    d["related_params"] = json.loads(
                        d["related_params"],
                    )
                except (json.JSONDecodeError, TypeError):
                    d["related_params"] = []
            result.append(d)
        return result

    def get_all_knowledge_topics(self) -> list[str]:
        """Lista todos os tópicos na base de conhecimento."""
        rows = self.conn.execute(
            "SELECT DISTINCT topic FROM ai_knowledge_base "
            "ORDER BY topic",
        ).fetchall()
        return [r["topic"] for r in rows]

    def count_knowledge(self) -> int:
        """Conta fatos na base de conhecimento."""
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_knowledge_base",
        ).fetchone()
        return row["cnt"] if row else 0

    # ============================================================
    # SETUP COMPARISON LOG
    # ============================================================
    def save_setup_comparison(self, car_id: int, track_id: int,
                              setup_a_id: int, setup_b_id: int,
                              param_diffs: dict,
                              lap_time_a: float | None,
                              lap_time_b: float | None,
                              weather: str = "dry",
                              conclusion: str = "") -> int:
        """Salva uma comparação entre dois setups."""
        import json

        improvement = None
        if lap_time_a and lap_time_b and lap_time_a > 0:
            improvement = (
                (lap_time_a - lap_time_b) / lap_time_a * 100
            )

        cursor = self.conn.execute(
            """INSERT INTO setup_comparison_log
               (car_id, track_id, setup_a_id, setup_b_id,
                param_diffs, lap_time_a, lap_time_b,
                improvement_pct, weather, conclusion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (car_id, track_id, setup_a_id, setup_b_id,
             json.dumps(param_diffs, ensure_ascii=False),
             lap_time_a, lap_time_b, improvement,
             weather, conclusion),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_setup_comparisons(self, car_id: int,
                              track_id: int,
                              limit: int = 20) -> list[dict]:
        """Retorna comparações de setup para este combo."""
        import json

        rows = self.conn.execute(
            """SELECT * FROM setup_comparison_log
               WHERE car_id = ? AND track_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (car_id, track_id, limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("param_diffs"):
                try:
                    d["param_diffs"] = json.loads(
                        d["param_diffs"],
                    )
                except (json.JSONDecodeError, TypeError):
                    d["param_diffs"] = {}
            result.append(d)
        return result

    # ============================================================
    # SCHEMA MIGRATION (evolução do banco)
    # ============================================================
    def _migrate_schema(self):
        """
        Aplica migrações incrementais ao banco de dados.
        Adiciona colunas de TC/ABS em ai_suggestions se faltantes.
        """
        # Detectar colunas existentes em ai_suggestions
        cursor = self.conn.execute(
            "PRAGMA table_info(ai_suggestions)",
        )
        existing_cols = {row["name"] for row in cursor.fetchall()}

        tc_cols = {
            "delta_tc_onboard": "REAL",
            "delta_tc_map": "REAL",
            "delta_tc_power_cut": "REAL",
            "delta_tc_slip_angle": "REAL",
            "delta_abs_map": "REAL",
            "delta_rear_brake_bias": "REAL",
            "delta_diff_preload": "REAL",
            "delta_toe_f": "REAL",
            "delta_toe_r": "REAL",
            "delta_ride_height_f": "REAL",
            "delta_ride_height_r": "REAL",
        }

        for col_name, col_type in tc_cols.items():
            if col_name not in existing_cols:
                self.conn.execute(
                    f"ALTER TABLE ai_suggestions "
                    f"ADD COLUMN {col_name} {col_type}",
                )
                logger.info("Migração: adicionada coluna %s "
                            "em ai_suggestions", col_name)

        self.conn.commit()

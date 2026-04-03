"""
telemetry_reader.py — Leitor de telemetria do LMU via Shared Memory.

Responsável por:
1. Conectar-se à Shared Memory do rFactor 2 / Le Mans Ultimate
2. Coletar dados instantâneos de telemetria
3. Acumular médias/máximos por volta
4. Construir o vetor de 38 features para a rede neural
5. Detectar automaticamente carro, classe e pista

Usa o adapter/ existente (rf2_connector, rf2_data) como backend.
"""

from __future__ import annotations

import ctypes
import logging
import math
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from core.brain import INPUT_FEATURES, NUM_INPUTS

logger = logging.getLogger("LMU_VE.telemetry")

# Intervalos de amostragem
SAMPLE_INTERVAL_SEC = 0.1  # 10 Hz de coleta


@dataclass
class LapAccumulator:
    """Acumula amostras de telemetria dentro de uma volta."""
    # Temperaturas dos pneus ICO × 4 rodas (12 valores) — soma + count
    temp_samples: list[list[float]] = field(default_factory=lambda: [[] for _ in range(12)])
    # Pressões × 4
    pressure_samples: list[list[float]] = field(default_factory=lambda: [[] for _ in range(4)])
    # Desgaste × 4 (pegamos snapshot no final da volta)
    wear_start: tuple[float, ...] | None = None
    wear_end: tuple[float, ...] | None = None
    # Carga nos pneus × 4
    load_samples: list[list[float]] = field(default_factory=lambda: [[] for _ in range(4)])
    # Ride Height F/R
    ride_height_f_samples: list[float] = field(default_factory=list)
    ride_height_r_samples: list[float] = field(default_factory=list)
    # Downforce F/R
    downforce_f_samples: list[float] = field(default_factory=list)
    downforce_r_samples: list[float] = field(default_factory=list)
    # Dinâmica: pitch, roll, heave (via aceleração vertical)
    pitch_samples: list[float] = field(default_factory=list)
    roll_samples: list[float] = field(default_factory=list)
    heave_samples: list[float] = field(default_factory=list)
    # Velocidade máxima
    max_speed: float = 0.0
    # Combustível
    fuel_start: float = 0.0
    fuel_end: float = 0.0
    # Contadores
    sample_count: int = 0

    def reset(self):
        """Reseta para nova volta."""
        self.temp_samples = [[] for _ in range(12)]
        self.pressure_samples = [[] for _ in range(4)]
        self.wear_start = None
        self.wear_end = None
        self.load_samples = [[] for _ in range(4)]
        self.ride_height_f_samples = []
        self.ride_height_r_samples = []
        self.downforce_f_samples = []
        self.downforce_r_samples = []
        self.pitch_samples = []
        self.roll_samples = []
        self.heave_samples = []
        self.max_speed = 0.0
        self.fuel_start = 0.0
        self.fuel_end = 0.0
        self.sample_count = 0


@dataclass
class LapSummary:
    """Resumo de uma volta completa com features para a NN."""
    lap_number: int
    lap_time: float
    sector1: float
    sector2: float
    sector3: float
    vehicle_name: str
    vehicle_class: str
    track_name: str
    features: np.ndarray  # shape (49,), valores brutos (pré-normalização)
    is_valid: bool  # Se a volta é válida (sem pits, sem penalidade)
    track_temp: float
    ambient_temp: float
    rain: float


class TelemetryReader:
    """
    Leitor de telemetria em tempo real via Shared Memory.

    Coleta dados a cada SAMPLE_INTERVAL_SEC, acumula por volta,
    e gera LapSummary ao final de cada volta.
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Adaptadores (serão setados via connect())
        self._session = None   # adapter.rf2_data.Session
        self._vehicle = None   # adapter.rf2_data.Vehicle
        self._tyre = None      # adapter.rf2_data.Tyre
        self._brake = None     # adapter.rf2_data.Brake
        self._engine = None    # adapter.rf2_data.Engine
        self._timing = None    # adapter.rf2_data.Timing
        self._lap = None       # adapter.rf2_data.Lap

        # Estado
        self._current_lap_num: int = -1
        self._accumulator = LapAccumulator()
        self._last_summary: LapSummary | None = None
        self._summaries: list[LapSummary] = []
        self._connected = False

        # Callback para notificar nova volta completa
        self.on_lap_completed: callable | None = None

        # Feedback do usuário (setado externamente pela GUI)
        self._user_feedback = {
            "bias": 0.0,       # -1 understeer ... +1 oversteer
            "entry": 0.0,      # Problema na entrada (0 ou 1)
            "mid": 0.0,        # Problema no meio (0 ou 1)
            "exit": 0.0,       # Problema na saída (0 ou 1)
            "confidence": 0.0, # 0-1 confiança do usuário
        }

    def connect(self, session, vehicle, tyre, brake, engine, timing, lap):
        """
        Conecta aos adaptadores de dados do Shared Memory.

        Args:
            session: Instância de adapter.rf2_data.Session
            vehicle: Instância de adapter.rf2_data.Vehicle
            tyre: Instância de adapter.rf2_data.Tyre
            brake: Instância de adapter.rf2_data.Brake
            engine: Instância de adapter.rf2_data.Engine
            timing: Instância de adapter.rf2_data.Timing
            lap: Instância de adapter.rf2_data.Lap
        """
        self._session = session
        self._vehicle = vehicle
        self._tyre = tyre
        self._brake = brake
        self._engine = engine
        self._timing = timing
        self._lap = lap
        self._connected = True
        logger.info("TelemetryReader conectado aos adaptadores de Shared Memory.")

    def set_user_feedback(self, bias: float = 0.0, entry: float = 0.0,
                          mid: float = 0.0, exit_: float = 0.0,
                          confidence: float = 0.0):
        """Atualiza o feedback do usuário (chamado pela GUI)."""
        with self._lock:
            self._user_feedback["bias"] = max(-1.0, min(1.0, bias))
            self._user_feedback["entry"] = 1.0 if entry else 0.0
            self._user_feedback["mid"] = 1.0 if mid else 0.0
            self._user_feedback["exit"] = 1.0 if exit_ else 0.0
            self._user_feedback["confidence"] = max(0.0, min(1.0, confidence))

    def start(self):
        """Inicia a coleta de telemetria em thread separada."""
        if not self._connected:
            logger.error("TelemetryReader: não conectado. Chame connect() antes.")
            return
        if self._running:
            logger.warning("TelemetryReader já está rodando.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._thread.start()
        logger.info("TelemetryReader iniciado (coleta a %.0f Hz).", 1 / SAMPLE_INTERVAL_SEC)

    def stop(self):
        """Para a coleta de telemetria."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("TelemetryReader parado.")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_summary(self) -> LapSummary | None:
        with self._lock:
            return self._last_summary

    @property
    def all_summaries(self) -> list[LapSummary]:
        with self._lock:
            return list(self._summaries)

    def get_current_car_info(self) -> dict | None:
        """Retorna info do carro/pista atual (auto-detecção)."""
        if not self._connected:
            return None
        try:
            return {
                "vehicle_name": self._vehicle.vehicle_name(),
                "vehicle_class": self._vehicle.class_name(),
                "track_name": self._session.track_name(),
            }
        except Exception:
            return None

    def get_live_telemetry(self) -> dict | None:
        """Retorna snapshot da telemetria atual (para exibição na GUI)."""
        if not self._connected:
            return None
        try:
            tyre_temps = self._tyre.surface_temperature_ico()
            tyre_press = self._tyre.pressure()
            tyre_wear = self._tyre.wear()
            tyre_load = self._tyre.load()

            return {
                "speed": self._vehicle.speed() * 3.6,  # m/s → km/h
                "gear": self._engine.gear(),
                "rpm": self._engine.rpm(),
                "fuel": self._vehicle.fuel(),
                "lap_number": self._lap.number(),
                "lap_time": self._timing.current_laptime(),
                "last_lap_time": self._timing.last_laptime(),
                "best_lap_time": self._timing.best_laptime(),
                "tyre_temps_ico": tyre_temps,   # 12 valores
                "tyre_pressure": tyre_press,     # 4 valores (kPa)
                "tyre_wear": tyre_wear,          # 4 valores (fração)
                "tyre_load": tyre_load,          # 4 valores (N)
                "brake_temp": self._brake.temperature(),
                "track_temp": self._session.track_temperature(),
                "ambient_temp": self._session.ambient_temperature(),
                "rain": self._session.raininess(),
                "downforce_f": self._vehicle.downforce_front(),
                "downforce_r": self._vehicle.downforce_rear(),
                "in_pits": self._vehicle.in_pits(),
                "in_garage": self._vehicle.in_garage(),
                "session_type": self._session.session_type(),
            }
        except Exception as e:
            logger.debug("Erro ao ler telemetria live: %s", e)
            return None

    # ─────────────────────────────────────────────
    # Loop de coleta privado
    # ─────────────────────────────────────────────

    def _collection_loop(self):
        """Loop principal de coleta em background."""
        consecutive_errors = 0
        while self._running:
            try:
                self._sample_tick()
                consecutive_errors = 0  # Reset ao sucesso
            except (OSError, MemoryError, ctypes.ArgumentError) as e:
                consecutive_errors += 1
                if consecutive_errors >= 10:
                    logger.warning(
                        "Perdeu conexão com LMU (Shared Memory): %s. "
                        "Tentando reconexão após %d falhas consecutivas...",
                        e, consecutive_errors,
                    )
                    self._connected = False
                    # Aguardar antes de tentar reconectar
                    time.sleep(5.0)
                    if self._try_reconnect():
                        consecutive_errors = 0
                        logger.info("Reconexão com LMU bem-sucedida!")
                        continue
                    else:
                        logger.error(
                            "Reconexão falhou. Parando coleta."
                        )
                        self._running = False
                        return
                logger.debug("Erro de SM (tentativa %d): %s", consecutive_errors, e)
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= 30:
                    logger.error("Loop de telemetria parado: muitos erros (%s)", e)
                    self._running = False
                    self._connected = False
                    return
                logger.debug("Erro no sample_tick (jogo pode estar fechado): %s", e)
            time.sleep(SAMPLE_INTERVAL_SEC)

    def _try_reconnect(self) -> bool:
        """
        Tenta reconectar aos adaptadores de Shared Memory.
        Útil quando o jogo fecha e reabre, ou após crash do LMU.

        Returns:
            True se a reconexão foi bem-sucedida.
        """
        max_retries = 6  # ~30 segundos no total
        for attempt in range(max_retries):
            if not self._running:
                return False
            try:
                # Testar se os adaptadores ainda respondem
                _ = self._session.track_name()
                _ = self._vehicle.speed()
                self._connected = True
                return True
            except Exception:
                logger.debug(
                    "Reconexão tentativa %d/%d falhou. Aguardando...",
                    attempt + 1, max_retries,
                )
                time.sleep(5.0)
        return False

    def _sample_tick(self):
        """Coleta uma amostra de telemetria."""
        # Verificar se o jogador está ativo na pista
        if self._vehicle.in_pits() or self._vehicle.in_garage():
            return

        current_lap = self._lap.number()

        # Detectar mudança de volta
        if current_lap != self._current_lap_num:
            if self._current_lap_num > 0 and self._accumulator.sample_count > 10:
                # Volta anterior completou — gerar resumo
                self._finalize_lap()
            # Iniciar nova acumulação
            self._current_lap_num = current_lap
            self._accumulator.reset()
            self._accumulator.fuel_start = self._vehicle.fuel()
            self._accumulator.wear_start = self._tyre.wear()

        # Coletar amostra
        acc = self._accumulator

        # Temperaturas ICO (inner, center, outer) × 4 rodas = 12 valores
        temps = self._tyre.surface_temperature_ico()
        for i in range(12):
            acc.temp_samples[i].append(temps[i])

        # Pressões × 4
        pressures = self._tyre.pressure()
        for i in range(4):
            acc.pressure_samples[i].append(pressures[i])

        # Carga × 4
        loads = self._tyre.load()
        for i in range(4):
            acc.load_samples[i].append(loads[i])

        # Ride Height (dados reais via Shared Memory)
        try:
            acc.ride_height_f_samples.append(self._vehicle.front_ride_height())
            acc.ride_height_r_samples.append(self._vehicle.rear_ride_height())
        except Exception:
            pass

        # Downforce
        acc.downforce_f_samples.append(self._vehicle.downforce_front())
        acc.downforce_r_samples.append(self._vehicle.downforce_rear())

        # Dinâmica (aceleração como proxy para pitch/roll/heave)
        try:
            acc.pitch_samples.append(self._vehicle.accel_longitudinal())
            acc.roll_samples.append(self._vehicle.accel_lateral())
            acc.heave_samples.append(self._vehicle.accel_vertical())
        except Exception:
            pass

        # Velocidade máxima
        speed = self._vehicle.speed()
        if speed > acc.max_speed:
            acc.max_speed = speed

        # Combustível atual
        acc.fuel_end = self._vehicle.fuel()
        acc.wear_end = self._tyre.wear()

        acc.sample_count += 1

    def _finalize_lap(self):
        """Finaliza uma volta e gera o LapSummary."""
        acc = self._accumulator

        # Obter tempos da volta anterior
        lap_time = self._timing.last_laptime()
        if lap_time <= 0 or lap_time > 600:  # >10min = inválido
            logger.debug("Volta %d ignorada: lap_time inválido (%.1f)", self._current_lap_num, lap_time)
            return

        # Checar validade
        is_valid = self._vehicle.count_lap_flag() == 2  # 2 = conta volta E tempo

        # Construir vetor de features (49 valores)
        features = np.zeros(NUM_INPUTS, dtype=np.float32)

        # Temperaturas médias ICO × 4 rodas (features 0-11)
        for i in range(12):
            if acc.temp_samples[i]:
                features[i] = float(np.mean(acc.temp_samples[i]))

        # Pressões médias × 4 (features 12-15)
        for i in range(4):
            if acc.pressure_samples[i]:
                features[12 + i] = float(np.mean(acc.pressure_samples[i]))

        # Desgaste × 4 (features 16-19) — diferença entre início e fim da volta
        if acc.wear_start and acc.wear_end:
            for i in range(4):
                features[16 + i] = acc.wear_start[i] - acc.wear_end[i]
        else:
            if acc.wear_end:
                for i in range(4):
                    features[16 + i] = 1.0 - acc.wear_end[i]

        # Carga média × 4 (features 20-23)
        for i in range(4):
            if acc.load_samples[i]:
                features[20 + i] = float(np.mean(acc.load_samples[i]))

        # Ride Height F/R médio (features 24-25)
        if acc.ride_height_f_samples:
            features[24] = float(np.mean(acc.ride_height_f_samples))
        if acc.ride_height_r_samples:
            features[25] = float(np.mean(acc.ride_height_r_samples))

        # Downforce F/R médio (features 26-27)
        if acc.downforce_f_samples:
            features[26] = float(np.mean(acc.downforce_f_samples))
        if acc.downforce_r_samples:
            features[27] = float(np.mean(acc.downforce_r_samples))

        # Dinâmica: pitch, roll, heave (features 28-30) — desvio padrão da aceleração
        if acc.pitch_samples:
            features[28] = float(np.std(acc.pitch_samples))
        if acc.roll_samples:
            features[29] = float(np.std(acc.roll_samples))
        if acc.heave_samples:
            features[30] = float(np.std(acc.heave_samples))

        # Velocidade máxima km/h (feature 31)
        features[31] = acc.max_speed * 3.6

        # Combustível restante (feature 32)
        features[32] = acc.fuel_end

        # Feedback do usuário (features 33-37)
        with self._lock:
            features[33] = self._user_feedback["bias"]
            features[34] = self._user_feedback["entry"]
            features[35] = self._user_feedback["mid"]
            features[36] = self._user_feedback["exit"]
            features[37] = self._user_feedback["confidence"]

        # ── Clima e condições da pista (features 38-45) ──
        try:
            features[38] = self._session.raininess()             # raining (0-1)
        except Exception:
            pass
        try:
            features[39] = self._session.dark_cloud()            # dark_cloud (0-1)
        except Exception:
            pass
        try:
            features[40] = self._session.avg_path_wetness()      # avg_path_wetness (0-1)
        except Exception:
            pass
        try:
            features[41] = self._session.track_temperature()     # track_temp (°C)
        except Exception:
            pass
        try:
            features[42] = self._session.ambient_temperature()   # ambient_temp (°C)
        except Exception:
            pass
        try:
            wind = self._session.wind_speed()                    # wind_speed (m/s)
            features[43] = wind if wind else 0.0
        except Exception:
            pass
        try:
            # Grip médio das 4 rodas
            grips = self._tyre.grip()
            features[44] = float(np.mean(grips)) if grips else 0.5
        except Exception:
            features[44] = 0.5
        try:
            # Lateral force imbalance (F-R normalizada)
            lat_forces = self._tyre.lateral_force()
            if lat_forces and len(lat_forces) >= 4:
                front_lat = abs(lat_forces[0]) + abs(lat_forces[1])
                rear_lat = abs(lat_forces[2]) + abs(lat_forces[3])
                total = front_lat + rear_lat
                features[45] = (front_lat - rear_lat) / total if total > 0 else 0.0
        except Exception:
            pass

        # ── Sessão e contexto (features 46-48) ──
        try:
            fuel_cap = self._vehicle.fuel_capacity()
            features[46] = acc.fuel_end / fuel_cap if fuel_cap > 0 else 0.5  # fuel_fraction
        except Exception:
            features[46] = 0.5
        try:
            sess_type = self._session.session_type()
            # 0=test, 1=practice, 2=qualy, 3=warmup, 5=race
            features[47] = 1.0 if sess_type == 5 else 0.0  # session_type_race
            features[48] = 1.0 if sess_type == 2 else 0.0  # session_type_qualy
        except Exception:
            pass

        # Construir summary
        s1 = self._timing.last_sector1()
        s2 = self._timing.last_sector2()
        s3 = lap_time - s2 if s2 > 0 else 0.0
        s2_only = s2 - s1 if s2 > 0 and s1 > 0 else 0.0

        summary = LapSummary(
            lap_number=self._current_lap_num - 1,  # volta que acabou
            lap_time=lap_time,
            sector1=s1,
            sector2=s2_only,
            sector3=s3,
            vehicle_name=self._vehicle.vehicle_name(),
            vehicle_class=self._vehicle.class_name(),
            track_name=self._session.track_name(),
            features=features,
            is_valid=is_valid,
            track_temp=self._session.track_temperature(),
            ambient_temp=self._session.ambient_temperature(),
            rain=self._session.raininess(),
        )

        with self._lock:
            self._last_summary = summary
            self._summaries.append(summary)

        logger.info(
            "Volta %d finalizada: %.3fs (%s @ %s) — %d amostras, válida=%s",
            summary.lap_number, summary.lap_time,
            summary.vehicle_name, summary.track_name,
            acc.sample_count, is_valid,
        )

        # Notificar callback
        if self.on_lap_completed:
            try:
                self.on_lap_completed(summary)
            except Exception as e:
                logger.error("Erro no callback on_lap_completed: %s", e)

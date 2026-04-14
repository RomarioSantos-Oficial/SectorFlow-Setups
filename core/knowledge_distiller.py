"""
knowledge_distiller.py — Destilação de Conhecimento LLM → Rede Neural.

O objetivo é usar a API do LLM como PROFESSOR temporário para treinar
a rede neural local. Com o tempo, a rede aprende tudo que o LLM sabe
e o sistema se torna 100% AUTÔNOMO, sem precisar de APIs externas.

Fluxo:
1. Gera cenários sintéticos de telemetria (cobrindo todo o espaço de problemas)
2. Para cada cenário, consulta o LLM: "dado isso, que ajustes você sugere?"
3. Salva cada resposta como dado de treinamento para a rede neural
4. Mede a "autonomia": compara predições da rede vs respostas do LLM
5. Quando autonomia > 90%, o sistema não precisa mais da API

Conceitos:
- Knowledge Distillation: modelo grande (LLM) ensina modelo pequeno (MLP)
- Curriculum Learning: cenários vão do simples ao complexo
- Autonomy Score: métrica de quanto a rede já aprendeu do LLM
"""

from __future__ import annotations

import logging
import random
import time
import threading
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("LMU_VE.distiller")

# ============================================================
# CENÁRIOS DE TREINAMENTO
# ============================================================
# Cobrem todo o espaço de problemas que a IA precisa aprender.
# Cada template define ranges para os 49 inputs da rede neural.

# Índices das features no vetor de input (49 features)
# 0-11: temps (I/M/O × 4 rodas)
# 12-15: pressões (4 rodas)
# 16-19: desgaste (4 rodas)
# 20-23: carga (4 rodas)
# 24-25: ride height F/R
# 26-27: downforce F/R
# 28-30: pitch, roll, heave
# 31: max_speed
# 32: fuel
# 33-37: user feedback (bias, entry, mid, exit, confidence)
# 38-45: clima (rain, cloud, wetness, track_temp, ambient_temp,
#               wind, grip_avg, lateral_imbalance)
# 46-48: sessão (fuel_fraction, race, qualy)

CONDITION_PROFILES = {
    # ── Temperatura dos pneus ──
    "cold_tires": {
        "desc": "Pneus frios — grip baixo, precisa aquecer",
        "temps": (55.0, 70.0),
        "grip": (0.5, 0.7),
    },
    "optimal_tires": {
        "desc": "Pneus na janela ideal — máximo grip",
        "temps": (85.0, 100.0),
        "grip": (0.85, 0.98),
    },
    "hot_tires": {
        "desc": "Pneus superaquecidos — degradação",
        "temps": (105.0, 120.0),
        "grip": (0.6, 0.8),
    },
    "overheating": {
        "desc": "Pneus em superaquecimento crítico",
        "temps": (120.0, 140.0),
        "grip": (0.35, 0.55),
    },
    # ── Problemas de Balanço ──
    "understeer_entry": {
        "desc": "Understeer na entrada da curva",
        "feedback_bias": (-0.9, -0.5),
        "feedback_entry": 1.0,
    },
    "understeer_mid": {
        "desc": "Understeer no meio da curva",
        "feedback_bias": (-0.8, -0.4),
        "feedback_mid": 1.0,
    },
    "oversteer_exit": {
        "desc": "Oversteer na saída da curva",
        "feedback_bias": (0.4, 0.9),
        "feedback_exit": 1.0,
    },
    "oversteer_entry": {
        "desc": "Oversteer na entrada (traseira sai ao frear)",
        "feedback_bias": (0.5, 0.9),
        "feedback_entry": 1.0,
    },
    "neutral": {
        "desc": "Carro neutro — equilibrado",
        "feedback_bias": (-0.1, 0.1),
    },
    # ── Clima ──
    "dry_warm": {
        "desc": "Seco e quente",
        "rain": 0.0,
        "track_temp": (35.0, 50.0),
        "ambient_temp": (25.0, 38.0),
        "wetness": 0.0,
    },
    "dry_cold": {
        "desc": "Seco e frio",
        "rain": 0.0,
        "track_temp": (10.0, 22.0),
        "ambient_temp": (5.0, 18.0),
        "wetness": 0.0,
    },
    "light_rain": {
        "desc": "Chuva leve — pista úmida",
        "rain": (0.2, 0.4),
        "track_temp": (18.0, 30.0),
        "wetness": (0.2, 0.5),
    },
    "heavy_rain": {
        "desc": "Chuva forte — aquaplanagem",
        "rain": (0.6, 1.0),
        "track_temp": (15.0, 25.0),
        "wetness": (0.6, 1.0),
        "grip": (0.3, 0.55),
    },
    # ── Desgaste ──
    "fresh_tires": {
        "desc": "Pneus novos — grip vai melhorar",
        "wear": (0.0, 0.05),
    },
    "worn_tires": {
        "desc": "Pneus gastos — grip caindo",
        "wear": (0.4, 0.7),
        "grip": (0.5, 0.7),
    },
    "critical_wear": {
        "desc": "Pneus em estado crítico — trocar urgente",
        "wear": (0.75, 0.95),
        "grip": (0.3, 0.5),
    },
    # ── Aerodinâmica ──
    "low_downforce": {
        "desc": "Downforce baixo — instável em alta velocidade",
        "downforce": (0.1, 0.3),
        "max_speed": (280.0, 330.0),
    },
    "high_downforce": {
        "desc": "Downforce alto — estável mas lento na reta",
        "downforce": (0.7, 1.0),
        "max_speed": (240.0, 270.0),
    },
    "bottoming": {
        "desc": "Carro tocando o chão — ride height muito baixo",
        "ride_height": (0.005, 0.015),
        "heave": (0.01, 0.05),
    },
}

# Classes de carro para treinar
CAR_CLASSES = ["hypercar", "lmp2", "lmgt3"]

# Sessões
SESSION_TYPES = ["practice", "quali", "race"]


@dataclass
class DistillationProgress:
    """Progresso da destilação."""
    total_scenarios: int = 0
    completed: int = 0
    successful: int = 0
    failed: int = 0
    is_running: bool = False
    phase: str = ""  # "generating", "training", "measuring"
    autonomy_score: float = 0.0
    message: str = ""


@dataclass
class AutonomyMetrics:
    """Métricas de autonomia da IA."""
    score: float = 0.0             # 0.0 a 1.0 (100% = autônoma)
    total_comparisons: int = 0     # Total de comparações NN vs LLM
    agreements: int = 0            # Quantas vezes concordaram
    avg_delta_error: float = 0.0   # Erro médio dos deltas
    scenarios_trained: int = 0     # Cenários destilados
    is_autonomous: bool = False    # True quando score > 0.9
    details: dict = field(default_factory=dict)


class KnowledgeDistiller:
    """
    Destilador de Conhecimento: transfere sabedoria do LLM
    para a rede neural local.

    Uso:
        distiller = KnowledgeDistiller(llm_advisor, normalizer, ...)
        distiller.start_distillation("hypercar", callback=on_progress)

    Quando a autonomia atinge 90%+, o sistema avisa que está pronto
    para funcionar sem APIs externas.
    """

    def __init__(self, llm_advisor, normalizer, db, trainer,
                 model_manager, config):
        self._llm = llm_advisor
        self._normalizer = normalizer
        self._db = db
        self._trainer = trainer
        self._model_manager = model_manager
        self._config = config

        self._progress = DistillationProgress()
        self._metrics = AutonomyMetrics()
        self._lock = threading.Lock()

        # Histórico de comparações NN vs LLM (para tracking contínuo)
        self._comparison_history: list[dict] = []

        # Carregar métricas persistidas
        self._load_metrics()

    @property
    def progress(self) -> DistillationProgress:
        with self._lock:
            return DistillationProgress(
                total_scenarios=self._progress.total_scenarios,
                completed=self._progress.completed,
                successful=self._progress.successful,
                failed=self._progress.failed,
                is_running=self._progress.is_running,
                phase=self._progress.phase,
                autonomy_score=self._metrics.score,
                message=self._progress.message,
            )

    @property
    def autonomy(self) -> AutonomyMetrics:
        with self._lock:
            return AutonomyMetrics(
                score=self._metrics.score,
                total_comparisons=self._metrics.total_comparisons,
                agreements=self._metrics.agreements,
                avg_delta_error=self._metrics.avg_delta_error,
                scenarios_trained=self._metrics.scenarios_trained,
                is_autonomous=self._metrics.is_autonomous,
                details=dict(self._metrics.details),
            )

    # ─── Geração de Cenários Sintéticos ─────────────────

    def generate_scenarios(self, car_class: str,
                           n: int = 60) -> list[dict]:
        """
        Gera N cenários sintéticos de telemetria cobrindo o espaço
        completo de problemas para a classe de carro.

        Cada cenário é um dict com chaves = nomes dos INPUT_FEATURES.
        """
        from core.brain import INPUT_FEATURES

        scenarios = []

        # Combinações de perfis para cobertura completa
        tire_profiles = [
            "cold_tires", "optimal_tires", "hot_tires", "overheating",
        ]
        balance_profiles = [
            "understeer_entry", "understeer_mid",
            "oversteer_exit", "oversteer_entry", "neutral",
        ]
        weather_profiles = [
            "dry_warm", "dry_cold", "light_rain", "heavy_rain",
        ]
        wear_profiles = [
            "fresh_tires", "worn_tires", "critical_wear",
        ]

        # Gerar cenários combinando perfis
        generated = 0
        while generated < n:
            tire_p = random.choice(tire_profiles)
            balance_p = random.choice(balance_profiles)
            weather_p = random.choice(weather_profiles)
            wear_p = random.choice(wear_profiles)
            session = random.choice(SESSION_TYPES)

            scenario = self._build_scenario(
                car_class, tire_p, balance_p, weather_p,
                wear_p, session,
            )
            scenario["_profiles"] = {
                "tire": tire_p, "balance": balance_p,
                "weather": weather_p, "wear": wear_p,
                "session": session, "car_class": car_class,
            }
            scenarios.append(scenario)
            generated += 1

        logger.info(
            "Gerados %d cenários sintéticos para %s",
            len(scenarios), car_class,
        )
        return scenarios

    def _build_scenario(self, car_class: str,
                        tire_profile: str, balance_profile: str,
                        weather_profile: str, wear_profile: str,
                        session: str) -> dict:
        """Constrói um cenário de telemetria a partir de perfis."""
        tire = CONDITION_PROFILES[tire_profile]
        balance = CONDITION_PROFILES[balance_profile]
        weather = CONDITION_PROFILES[weather_profile]
        wear = CONDITION_PROFILES[wear_profile]

        def _rand(spec):
            """Extrai valor de uma spec (tupla range ou float)."""
            if isinstance(spec, tuple):
                return random.uniform(spec[0], spec[1])
            return float(spec)

        # ── Temperaturas dos pneus (12 features) ──
        base_temp = _rand(tire.get("temps", (85.0, 95.0)))
        # Adicionar variação I/M/O realista
        temps = {}
        for wheel in ("fl", "fr", "rl", "rr"):
            spread = random.uniform(2.0, 12.0)
            middle = base_temp + random.uniform(-3.0, 3.0)
            inner = middle + random.uniform(-spread, spread * 0.5)
            outer = middle + random.uniform(-spread * 0.5, spread)
            temps[f"temp_{wheel}_inner"] = inner
            temps[f"temp_{wheel}_middle"] = middle
            temps[f"temp_{wheel}_outer"] = outer

        # ── Pressões (4 features) ──
        base_pressure = random.uniform(155.0, 175.0)
        pressures = {}
        for wheel in ("fl", "fr", "rl", "rr"):
            pressures[f"pressure_{wheel}"] = (
                base_pressure + random.uniform(-5.0, 5.0)
            )

        # ── Desgaste (4 features) ──
        base_wear = _rand(wear.get("wear", (0.1, 0.3)))
        wears = {}
        for wheel in ("fl", "fr", "rl", "rr"):
            wears[f"wear_{wheel}"] = max(
                0.0, min(1.0, base_wear + random.uniform(-0.05, 0.05))
            )

        # ── Carga (4 features) ──
        loads = {}
        for wheel in ("fl", "fr", "rl", "rr"):
            loads[f"load_{wheel}"] = random.uniform(0.3, 0.9)

        # ── Ride Height (2 features) ──
        rh_spec = tire.get("ride_height", None)
        if "bottoming" in tire_profile or CONDITION_PROFILES.get(
                tire_profile, {}).get("ride_height"):
            rh_f = _rand(CONDITION_PROFILES.get(
                "bottoming", {}).get("ride_height", (0.03, 0.06)))
            rh_r = rh_f + random.uniform(-0.005, 0.005)
        else:
            rh_f = random.uniform(0.025, 0.08)
            rh_r = random.uniform(0.030, 0.085)

        # ── Downforce (2 features) ──
        if "downforce" in CONDITION_PROFILES.get(tire_profile, {}):
            df = _rand(tire.get("downforce", (0.4, 0.7)))
        elif "low_downforce" == tire_profile:
            df = random.uniform(0.1, 0.3)
        elif "high_downforce" == tire_profile:
            df = random.uniform(0.7, 1.0)
        else:
            df = random.uniform(0.35, 0.75)
        downforce_f = df * random.uniform(0.9, 1.1)
        downforce_r = df * random.uniform(0.9, 1.1)

        # ── Dinâmica (3 features) ──
        pitch = random.uniform(-0.02, 0.02)
        roll = random.uniform(-0.015, 0.015)
        heave = _rand(CONDITION_PROFILES.get(
            "bottoming", {}).get("heave", (0.0, 0.01))
        ) if "bottoming" in tire_profile else random.uniform(0.0, 0.01)

        # ── Velocidade e Combustível ──
        if car_class == "lmgt3":
            max_speed = random.uniform(240.0, 280.0)
        elif car_class == "lmp2":
            max_speed = random.uniform(280.0, 320.0)
        else:
            max_speed = random.uniform(300.0, 340.0)
        fuel = random.uniform(10.0, 80.0)

        # ── Feedback do usuário ──
        bias = _rand(balance.get("feedback_bias", (0.0, 0.0)))
        entry = float(balance.get("feedback_entry", 0.0))
        mid = float(balance.get("feedback_mid", 0.0))
        exit_ = float(balance.get("feedback_exit", 0.0))
        confidence = random.uniform(0.5, 1.0)

        # ── Clima ──
        rain = _rand(weather.get("rain", 0.0))
        cloud = rain * random.uniform(0.8, 1.2)
        wetness = _rand(weather.get("wetness", 0.0))
        track_temp = _rand(weather.get("track_temp", (25.0, 35.0)))
        ambient_temp = _rand(weather.get("ambient_temp", (20.0, 30.0)))
        wind = random.uniform(0.0, 8.0)

        grip = _rand(
            tire.get("grip", None)
            or wear.get("grip", None)
            or weather.get("grip", None)
            or (0.7, 0.9)
        )
        lat_imbalance = random.uniform(-0.15, 0.15)

        # ── Sessão ──
        fuel_fraction = random.uniform(0.2, 1.0)
        is_race = 1.0 if session == "race" else 0.0
        is_qualy = 1.0 if session == "quali" else 0.0

        # Montar dict completo
        scenario = {}
        scenario.update(temps)
        scenario.update(pressures)
        scenario.update(wears)
        scenario.update(loads)
        scenario["ride_height_f"] = rh_f
        scenario["ride_height_r"] = rh_r
        scenario["downforce_f"] = downforce_f
        scenario["downforce_r"] = downforce_r
        scenario["pitch"] = pitch
        scenario["roll"] = roll
        scenario["heave"] = heave
        scenario["max_speed"] = max_speed
        scenario["fuel"] = fuel
        scenario["user_feedback_bias"] = bias
        scenario["user_feedback_entry"] = entry
        scenario["user_feedback_mid"] = mid
        scenario["user_feedback_exit"] = exit_
        scenario["user_confidence"] = confidence
        scenario["raining"] = rain
        scenario["dark_cloud"] = min(1.0, cloud)
        scenario["avg_path_wetness"] = wetness
        scenario["track_temp"] = track_temp
        scenario["ambient_temp"] = ambient_temp
        scenario["wind_speed"] = wind
        scenario["grip_avg"] = grip
        scenario["lateral_force_imbalance"] = lat_imbalance
        scenario["fuel_fraction"] = fuel_fraction
        scenario["session_type_race"] = is_race
        scenario["session_type_qualy"] = is_qualy

        return scenario

    # ─── Destilação em Batch ────────────────────────────

    def start_distillation(self, car_class: str,
                           n_scenarios: int = 60,
                           callback=None):
        """
        Inicia o processo de destilação em thread separada.

        Para cada cenário:
        1. Envia telemetria ao LLM → recebe ajustes recomendados
        2. Salva como dado de treinamento para a rede neural
        3. Treina a rede com os novos dados
        4. Mede autonomia (NN vs LLM)

        Args:
            car_class: Classe do carro (hypercar, lmp2, lmgt3)
            n_scenarios: Número de cenários para gerar
            callback: Função(DistillationProgress) chamada a cada passo
        """
        with self._lock:
            if self._progress.is_running:
                logger.warning("Destilação já em andamento.")
                return
            self._progress.is_running = True

        thread = threading.Thread(
            target=self._distill_thread,
            args=(car_class, n_scenarios, callback),
            daemon=True,
        )
        thread.start()

    def _distill_thread(self, car_class: str, n_scenarios: int,
                        callback):
        """Thread principal de destilação."""
        try:
            # ── Fase 1: Gerar cenários ──
            self._update_progress(
                phase="generating",
                message="Gerando cenários de treinamento...",
                callback=callback,
            )

            scenarios = self.generate_scenarios(car_class, n_scenarios)

            with self._lock:
                self._progress.total_scenarios = len(scenarios)

            # ── Fase 2: Destilar (consultar LLM para cada cenário) ──
            self._update_progress(
                phase="distilling",
                message="Consultando LLM para cada cenário...",
                callback=callback,
            )

            training_data = []
            for i, scenario in enumerate(scenarios):
                try:
                    td = self._distill_one(scenario, car_class)
                    if td:
                        training_data.append(td)
                        with self._lock:
                            self._progress.successful += 1
                    else:
                        with self._lock:
                            self._progress.failed += 1
                except Exception as e:
                    logger.debug("Erro ao destilar cenário %d: %s", i, e)
                    with self._lock:
                        self._progress.failed += 1

                with self._lock:
                    self._progress.completed = i + 1
                    self._progress.message = (
                        f"Cenário {i+1}/{len(scenarios)} "
                        f"({self._progress.successful} OK, "
                        f"{self._progress.failed} falhas)"
                    )
                if callback:
                    callback(self.progress)

                # Rate limiting entre chamadas
                time.sleep(1.2)

            if not training_data:
                self._update_progress(
                    phase="done",
                    message="Nenhum dado obtido do LLM.",
                    callback=callback,
                )
                return

            # ── Fase 3: Treinar a rede neural ──
            self._update_progress(
                phase="training",
                message=f"Treinando rede neural com {len(training_data)} exemplos...",
                callback=callback,
            )

            self._train_with_distilled(training_data, car_class)

            # ── Fase 4: Medir autonomia ──
            self._update_progress(
                phase="measuring",
                message="Medindo autonomia da IA...",
                callback=callback,
            )

            # Usar subset dos cenários para medir (sem custo extra de API -
            # compara NN vs dados já obtidos do LLM)
            self._measure_autonomy_from_data(training_data, car_class)

            # Persistir métricas
            self._save_metrics()

            msg = (
                f"Destilação concluída! "
                f"{len(training_data)} cenários aprendidos. "
                f"Autonomia: {self._metrics.score*100:.0f}%"
            )
            if self._metrics.is_autonomous:
                msg += " — IA AUTÔNOMA! 🎓"

            self._update_progress(
                phase="done", message=msg, callback=callback,
            )

        except Exception as e:
            logger.error("Erro na destilação: %s", e)
            self._update_progress(
                phase="error",
                message=f"Erro: {e}",
                callback=callback,
            )
        finally:
            with self._lock:
                self._progress.is_running = False

    def _distill_one(self, scenario: dict, car_class: str) -> dict | None:
        """
        Destila UM cenário: envia ao LLM, recebe ajustes, retorna
        como dict de treinamento {input, output, reward, weight}.
        Retenta até 2 vezes se a resposta falhar.
        """
        from core.brain import INPUT_FEATURES, LEVEL_OUTPUTS

        if not self._llm.enabled:
            return None

        # Tentar até 2 vezes (retry em caso de resposta vazia/inválida)
        insight = None
        for attempt in range(2):
            insight = self._llm.analyze_telemetry(
                telemetry=scenario,
                car_class=car_class,
            )
            if insight and insight.adjustments and insight.confidence >= 0.3:
                break
            if attempt == 0:
                time.sleep(0.8)  # Esperar antes do retry

        if not insight or not insight.adjustments:
            return None

        if insight.confidence < 0.3:
            return None

        # Converter cenário para vetor de input (49 features)
        input_vec = np.zeros(len(INPUT_FEATURES), dtype=np.float32)
        for i, name in enumerate(INPUT_FEATURES):
            input_vec[i] = scenario.get(name, 0.0)

        # Normalizar
        input_norm = self._normalizer.normalize(input_vec)

        # Converter ajustes do LLM para vetor de output
        level = self._config.get("setup_level", "basic")
        output_names = LEVEL_OUTPUTS.get(level, LEVEL_OUTPUTS["basic"])
        output_vec = np.zeros(len(output_names), dtype=np.float32)
        matched = 0
        for i, name in enumerate(output_names):
            if name in insight.adjustments:
                output_vec[i] = insight.adjustments[name]
                matched += 1

        if matched == 0:
            return None

        return {
            "input": input_norm.tolist() if hasattr(input_norm, 'tolist') else list(input_norm),
            "output": output_vec.tolist(),
            "reward": insight.confidence,
            "weight": 0.6,  # Entre real (1.0) e chat (0.5)
            "_meta": {
                "source": "distillation",
                "car_class": car_class,
                "profiles": scenario.get("_profiles", {}),
                "llm_explanation": insight.explanation[:200],
            },
        }

    def _train_with_distilled(self, training_data: list[dict],
                              car_class: str):
        """Treina a rede neural com os dados destilados."""
        from core.brain import LEVEL_OUTPUTS

        level = self._config.get("setup_level", "basic")

        # Obter ou criar modelo
        model = self._model_manager.get_model(
            car_name="_distilled",
            track_name="_all_tracks",
            car_class=car_class,
            level=level,
        )
        self._trainer.set_model(model)

        # Treinar com mais épocas (dados sintéticos precisam de mais)
        result = self._trainer.train_offline(
            training_data,
            epochs=30,
            batch_size=16,
        )

        logger.info(
            "Treinamento por destilação: %d amostras, %d épocas, "
            "loss=%.4f, reward_médio=%.3f",
            result.total_samples, result.epochs_completed,
            result.final_loss, result.avg_reward,
        )

        # Salvar modelo
        self._model_manager.save_model(
            model=model,
            car_class=car_class,
            car_name="_distilled",
            track_name="_all_tracks",
            metadata={
                "source": "knowledge_distillation",
                "scenarios": len(training_data),
                "loss": result.final_loss,
            },
        )

        with self._lock:
            self._metrics.scenarios_trained += len(training_data)

    # ─── Medição de Autonomia ───────────────────────────

    def _measure_autonomy_from_data(self, training_data: list[dict],
                                    car_class: str):
        """
        Mede autonomia comparando predições da rede neural vs
        respostas do LLM (sem chamar a API de novo).

        Usa os dados de treinamento como referência: passa o input
        pela rede e compara com o output do LLM.
        """
        import torch
        from core.brain import LEVEL_OUTPUTS

        level = self._config.get("setup_level", "basic")
        output_names = LEVEL_OUTPUTS.get(level, LEVEL_OUTPUTS["basic"])

        model = self._model_manager.get_model(
            car_name="_distilled",
            track_name="_all_tracks",
            car_class=car_class,
            level=level,
        )
        model.eval()

        agreements = 0
        total = 0
        total_error = 0.0

        with torch.no_grad():
            for td in training_data:
                input_tensor = torch.FloatTensor(
                    td["input"]
                ).unsqueeze(0)

                # Predição da rede neural
                nn_output = model(input_tensor).squeeze(0)

                # Output do LLM (referência)
                llm_output = torch.FloatTensor(td["output"])

                # Comparar cada delta
                for i in range(len(output_names)):
                    nn_delta = round(nn_output[i].item() * 3)  # escala
                    llm_delta = round(llm_output[i].item())

                    if llm_delta == 0 and nn_delta == 0:
                        continue  # Ambos "sem ajuste" — não conta

                    total += 1

                    # Concordam se vão na MESMA DIREÇÃO
                    # (mesmo sinal ou diferença <= 1)
                    if nn_delta == llm_delta:
                        agreements += 1
                    elif abs(nn_delta - llm_delta) <= 1:
                        agreements += 0.7  # Concordância parcial
                    total_error += abs(nn_delta - llm_delta)

        score = agreements / max(total, 1)
        avg_error = total_error / max(total, 1)

        with self._lock:
            self._metrics.total_comparisons += total
            self._metrics.agreements += int(agreements)
            self._metrics.avg_delta_error = avg_error
            self._metrics.score = min(1.0, score)
            self._metrics.is_autonomous = score >= 0.90
            self._metrics.details[car_class] = {
                "score": score,
                "comparisons": total,
                "avg_error": avg_error,
            }

        logger.info(
            "Autonomia medida: %.1f%% (%d comparações, "
            "erro médio=%.2f, autônoma=%s)",
            score * 100, total, avg_error,
            self._metrics.is_autonomous,
        )

    def track_live_comparison(self, nn_deltas: dict,
                              llm_deltas: dict):
        """
        Compara predições da NN vs LLM em tempo real
        (chamado durante o jogo quando ambos geram sugestões).

        Isso atualiza o score de autonomia continuamente
        sem custo extra de API.
        """
        agreements = 0
        total = 0
        error = 0.0

        all_keys = set(nn_deltas.keys()) | set(llm_deltas.keys())
        for key in all_keys:
            nn_val = nn_deltas.get(key, 0)
            llm_val = llm_deltas.get(key, 0)
            if nn_val == 0 and llm_val == 0:
                continue
            total += 1
            if nn_val == llm_val:
                agreements += 1
            elif abs(nn_val - llm_val) <= 1:
                agreements += 0.7
            error += abs(nn_val - llm_val)

        if total == 0:
            return

        with self._lock:
            self._metrics.total_comparisons += total
            self._metrics.agreements += int(agreements)
            if total > 0:
                # Média móvel do score
                live_score = agreements / total
                old_score = self._metrics.score
                if old_score > 0:
                    self._metrics.score = old_score * 0.8 + live_score * 0.2
                else:
                    self._metrics.score = live_score
                self._metrics.avg_delta_error = (
                    self._metrics.avg_delta_error * 0.8
                    + (error / total) * 0.2
                )
                self._metrics.is_autonomous = self._metrics.score >= 0.90

            self._comparison_history.append({
                "nn": dict(nn_deltas),
                "llm": dict(llm_deltas),
                "agreement": agreements / max(total, 1),
            })
            # Manter últimas 100
            if len(self._comparison_history) > 100:
                self._comparison_history = self._comparison_history[-100:]

        # Persistir periodicamente
        if len(self._comparison_history) % 10 == 0:
            self._save_metrics()

    # ─── Persistência ──────────────────────────────────

    def _save_metrics(self):
        """Salva métricas de autonomia no config."""
        self._config.set("autonomy_score", self._metrics.score)
        self._config.set(
            "autonomy_comparisons", self._metrics.total_comparisons
        )
        self._config.set("autonomy_agreements", self._metrics.agreements)
        self._config.set(
            "autonomy_scenarios", self._metrics.scenarios_trained
        )
        self._config.set("autonomy_avg_error", self._metrics.avg_delta_error)
        self._config.save()

    def _load_metrics(self):
        """Carrega métricas persistidas."""
        self._metrics.score = self._config.get("autonomy_score", 0.0)
        self._metrics.total_comparisons = self._config.get(
            "autonomy_comparisons", 0
        )
        self._metrics.agreements = self._config.get(
            "autonomy_agreements", 0
        )
        self._metrics.scenarios_trained = self._config.get(
            "autonomy_scenarios", 0
        )
        self._metrics.avg_delta_error = self._config.get(
            "autonomy_avg_error", 0.0
        )
        self._metrics.is_autonomous = self._metrics.score >= 0.90

    # ─── Helpers ───────────────────────────────────────

    def _update_progress(self, phase: str, message: str, callback=None):
        """Atualiza o progresso e notifica callback."""
        with self._lock:
            self._progress.phase = phase
            self._progress.message = message
            self._progress.autonomy_score = self._metrics.score
        if callback:
            callback(self.progress)

    def get_status_text(self) -> str:
        """Retorna texto de status para a GUI."""
        score = self._metrics.score
        trained = self._metrics.scenarios_trained

        if score >= 0.90:
            return (
                f"🎓 IA AUTÔNOMA ({score*100:.0f}%) — "
                f"Não precisa mais de API externa!"
            )
        elif score >= 0.70:
            return (
                f"📈 IA quase autônoma ({score*100:.0f}%) — "
                f"{trained} cenários aprendidos"
            )
        elif score >= 0.40:
            return (
                f"📊 IA aprendendo ({score*100:.0f}%) — "
                f"{trained} cenários, continue destilando"
            )
        elif trained > 0:
            return (
                f"🔄 IA em treinamento ({score*100:.0f}%) — "
                f"{trained} cenários processados"
            )
        else:
            return "⚪ Destilação não iniciada — clique para treinar"

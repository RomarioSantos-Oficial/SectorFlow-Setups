"""
main.py — Ponto de entrada do Sector Flow Setups.

Inicializa todos os módulos (banco de dados, IA, telemetria, GUI)
e conecta os componentes. Funciona como script e como .exe empacotado.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

# Garantir que o diretório do projeto está no path
if getattr(sys, "frozen", False):
    _base = Path(sys.executable).parent
else:
    _base = Path(__file__).parent
if str(_base) not in sys.path:
    sys.path.insert(0, str(_base))

from config import (
    APP_NAME,
    APP_VERSION,
    BACKUPS_DIR,
    DB_FILE,
    LOGS_DIR,
    MODELS_DIR,
    USER_DATA_DIR,
    AppConfig,
    detect_lmu_path,
)
from core.brain import ModelManager, deltas_to_svm, filter_deltas_by_class
from core.heuristics import analyze_telemetry, merge_suggestions, apply_driver_profile
from core.knowledge_distiller import KnowledgeDistiller
from core.llm_advisor import LLMAdvisor
from core.normalizer import FeatureNormalizer
from core.reward import compute_reward
from core.safety import (
    compute_confidence,
    should_reset_to_heuristics,
    validate_deltas,
)
from core.trainer import Trainer
from data.database import DatabaseManager
from data.svm_parser import (
    SVMFile,
    apply_deltas,
    list_setup_files,
    parse_svm,
    save_svm,
)
from data.telemetry_reader import TelemetryReader
from gui.i18n import init_i18n, I18n

import numpy as np
import torch


# ================================================================
# LOGGING
# ================================================================

def setup_logging():
    """Configura logging para console e arquivo."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "lmu_ve.log"

    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Arquivo
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


logger = logging.getLogger("LMU_VE.main")


# ================================================================
# ENGINE — Núcleo do Virtual Engineer
# ================================================================

class VirtualEngineer:
    """
    Orquestrador central que conecta IA, banco, telemetria e GUI.
    A GUI e o main.py interagem apenas com esta classe.
    """

    def __init__(self):
        logger.info("Iniciando %s v%s", APP_NAME, APP_VERSION)

        # Criar diretórios necessários
        for d in (USER_DATA_DIR, DB_FILE.parent, MODELS_DIR, BACKUPS_DIR, LOGS_DIR):
            d.mkdir(parents=True, exist_ok=True)

        # Config
        self.config = AppConfig()
        
        # Inicializar internacionalização
        init_i18n(self.config.get("language", "pt-br"))

        # Detectar LMU
        self.lmu_path = detect_lmu_path()
        if self.lmu_path:
            logger.info("LMU detectado: %s", self.lmu_path)
        else:
            logger.warning("LMU não encontrado. Funcionalidade de setups limitada.")

        # Banco de dados
        self.db = DatabaseManager(str(DB_FILE))
        logger.info("Banco de dados inicializado: %s", DB_FILE)

        # IA
        self.model_manager = ModelManager(str(MODELS_DIR))
        self.normalizer = FeatureNormalizer()
        self.trainer = Trainer()
        self._recent_rewards: list[float] = []

        # LLM Advisor (multi-provedor)
        api_key = self.config.get("openrouter_api_key", "")
        llm_model = self.config.get("openrouter_model", "deepseek/deepseek-chat-v3-0324")
        llm_provider = self.config.get("llm_provider", "openrouter")
        llm_custom_url = self.config.get("llm_custom_url", "")
        self.llm_advisor = LLMAdvisor(
            api_key=api_key, model=llm_model,
            provider=llm_provider, custom_url=llm_custom_url,
        )
        if self.llm_advisor.enabled:
            logger.info("LLM Advisor ativo (%s / %s)", llm_provider, llm_model)

        # Knowledge Distiller (LLM → Rede Neural)
        self.distiller = KnowledgeDistiller(
            llm_advisor=self.llm_advisor,
            normalizer=self.normalizer,
            db=self.db,
            trainer=self.trainer,
            model_manager=self.model_manager,
            config=self.config,
        )

        # Telemetria
        self.telemetry = TelemetryReader()
        self.telemetry.on_lap_completed = self._on_lap_completed

        # Setup atual
        self._current_svm: SVMFile | None = None
        self._base_svm: SVMFile | None = None      # Setup base (SOMENTE LEITURA)
        self._last_deltas: dict[str, int] = {}
        self._last_display_deltas: dict[str, int] = {}  # delta-name format for GUI
        self._last_suggestion_id: int | None = None
        self._current_session_id: int | None = None
        self._car_name = ""
        self._car_class = ""
        self._track_name = ""

        # Estado
        self._game_connected = False

        # Auto-suggest: callbacks e estado
        self._auto_suggest_enabled = True
        self._auto_suggest_after_laps = 3  # Sugerir a cada N voltas
        self._on_auto_suggestion_callback = None  # GUI callback
        self._on_trend_alert_callback = None       # GUI callback para alertas
        self._lap_history: list[dict] = []         # Histórico para tendências
        self._pending_auto_suggestion: dict | None = None

        # Auto-progressão de nível
        self._current_level = "basic"

        # Cache de total_samples (invalidado a cada volta)
        self._cached_total_samples: int | None = None

        # Memória persistente carro × pista
        self._active_memory: dict | None = None
        self._memory_optimal_deltas: dict[str, float] = {}
        self._session_history: list[dict] = []
        self._memory_loaded_for: tuple[int, int] | None = None  # (car_id, track_id)

        # Shared Memory — referência mantida para shutdown
        self._rf2info = None

        # Lock global para estado compartilhado entre threads
        self._state_lock = threading.Lock()

        # Iniciar auto-detecção do jogo em background
        self._auto_connect_thread = threading.Thread(
            target=self._auto_connect_loop, daemon=True
        )
        self._auto_connect_thread.start()

        # Alimentar base de conhecimento inicial (assíncrono)
        self._seed_initial_knowledge()

    # ─────────────────────────────────────────────────────
    # Auto-detecção e conexão com o jogo
    # ─────────────────────────────────────────────────────

    def _auto_connect_loop(self):
        """Thread de background que tenta se conectar ao jogo periodicamente."""
        import time
        from adapter.rf2_connector import RF2Info
        from adapter.sm_bridge import create_adapters

        while True:
            with self._state_lock:
                if self._game_connected:
                    return
            try:
                rf2 = RF2Info()
                rf2.setMode(0)  # copy access
                rf2.setPID("")
                rf2.start()
                time.sleep(0.5)  # dar tempo para o mmap inicializar

                # Verificar se há dados válidos (versão do plugin presente)
                version = rf2.rf2Ext.mVersion
                version_str = version.decode("iso-8859-1").rstrip("\x00").strip() if version else ""

                if version_str:
                    logger.info("Shared Memory detectada: versão %s", version_str)
                    with self._state_lock:
                        self._rf2info = rf2
                    session, vehicle, tyre, brake, engine, timing, lap = create_adapters(rf2)
                    self.connect_game(session, vehicle, tyre, brake, engine, timing, lap)
                    logger.info("Conexão automática com o jogo estabelecida!")
                    return  # Conectado — sair do loop
                else:
                    rf2.stop()
            except Exception as e:
                logger.debug("Auto-connect: jogo não encontrado (%s). Tentando novamente...", e)

            time.sleep(3)  # Tentar novamente a cada 3 segundos

    # ─────────────────────────────────────────────────────
    # Conexão com o jogo
    # ─────────────────────────────────────────────────────

    def connect_game(self, session, vehicle, tyre, brake, engine, timing, lap):
        """Conecta aos adaptadores de Shared Memory."""
        self.telemetry.connect(session, vehicle, tyre, brake, engine, timing, lap)
        self.telemetry.start()
        with self._state_lock:
            self._game_connected = True
        logger.info("Conectado ao jogo via Shared Memory.")

    def is_game_connected(self) -> bool:
        with self._state_lock:
            return self._game_connected

    # ─── Properties para GUI ─────────────────────────────

    @property
    def car_name(self) -> str:
        return self._car_name

    @property
    def track_name(self) -> str:
        return self._track_name

    def get_car_info(self) -> dict | None:
        return self.telemetry.get_current_car_info()

    def get_weather_data(self) -> dict | None:
        """Retorna dados climáticos atuais para exibição na GUI."""
        data = self.telemetry.get_live_telemetry()
        if not data:
            return None
        return {
            "rain": data.get("rain", 0.0),
            "track_temp": data.get("track_temp", 0.0),
            "air_temp": data.get("ambient_temp", 0.0),
            "wetness": 0.0,
        }

    # ─────────────────────────────────────────────────────
    # IA — Predição e Treinamento
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _features_to_dict(features: np.ndarray) -> dict:
        """Converte vetor de features (49,) para dict nomeado (para heurísticas)."""
        from core.brain import INPUT_FEATURES
        return {name: float(features[i]) for i, name in enumerate(INPUT_FEATURES)}
    # ─────────────────────────────────────────────────────

    def ai_confidence(self) -> float:
        """Retorna a confiança atual da IA."""
        samples = self.total_samples()
        return compute_confidence(samples)

    def total_samples(self) -> int:
        """Total de amostras de treinamento no banco (com cache por volta)."""
        if self._cached_total_samples is not None:
            return self._cached_total_samples
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM training_data")
            self._cached_total_samples = cursor.fetchone()[0]
            return self._cached_total_samples
        except Exception:
            return 0

    def request_suggestion(self) -> tuple[dict[str, int], list[str]]:
        """
        Solicita sugestão de ajuste (IA + heurísticas + safety).

        Returns:
            (deltas, warnings)
        """
        deltas = {}
        warnings = []

        # Auto-detectar carro/pista
        car_info = self.get_car_info()
        if car_info:
            self._car_name = car_info.get("vehicle_name", "")
            self._car_class = car_info.get("vehicle_class", "")
            self._track_name = car_info.get("track_name", "")

        confidence = self.ai_confidence()
        summary = self.telemetry.last_summary

        # Se não tem summary, retorna vazio
        if not summary:
            return {}, ["Nenhuma volta completada ainda. Dirija pelo menos 1 volta."]

        # Verificar auto-reset
        if should_reset_to_heuristics(self._recent_rewards):
            return self.request_heuristic_suggestion()

        # Se confiança baixa, só heurísticas
        if confidence < 0.2:
            return self.request_heuristic_suggestion()

        # Predição da IA
        try:
            features = summary.features
            features_norm = self.normalizer.normalize(features)
            input_tensor = torch.FloatTensor(features_norm).unsqueeze(0)

            model = self.model_manager.get_model(self._car_name, self._track_name,
                                                  car_class=self._car_class)
            # Epsilon-greedy: mais exploração quando confiança é baixa
            # confidence 0.2 → epsilon 0.3 (explora muito)
            # confidence 0.7 → epsilon 0.1 (explora pouco)
            # confidence 1.0 → epsilon 0.02 (quase zero)
            epsilon = max(0.02, 0.35 - confidence * 0.4)
            ai_deltas = model.predict(input_tensor, epsilon=epsilon)

            # Merge com heurísticas se confiança parcial
            if confidence < 0.7:
                tele_dict = self._features_to_dict(features)
                heuristic_list = analyze_telemetry(
                    tele_dict, self._car_class, self._current_level
                )
                ai_deltas = merge_suggestions(
                    heuristic_list, ai_deltas, confidence
                )

            deltas = ai_deltas
        except Exception as e:
            logger.error("Erro na predição IA: %s", e)
            return self.request_heuristic_suggestion()

        # Validação de segurança
        current_setup = self._current_svm.get_all_indices() if self._current_svm else None
        deltas, safety_warnings = validate_deltas(
            deltas, max_delta=3, current_setup=current_setup
        )
        warnings.extend(safety_warnings)

        # Filtrar outputs impossíveis por classe de carro
        # Ex: LMP2 sem ABS → remove delta_abs_map
        if self._car_class:
            deltas = filter_deltas_by_class(deltas, self._car_class.lower())

        # Aplicar perfil do piloto (agressividade, preferências)
        try:
            driver_id = self.config.get("driver_id", 1)
            profile = self.db.get_driver_profile(driver_id)
            prefs = self.db.get_driver_preferences(driver_id)
            agg = profile.get("aggression", 0.5) if profile else 0.5
            brk = profile.get("braking_style", 0.5) if profile else 0.5
            deltas = apply_driver_profile(
                deltas, aggression=agg,
                braking_style=brk, preferences=prefs
            )
        except Exception as e:
            logger.debug("Perfil do piloto não aplicado: %s", e)

        # Consultar regras aprendidas para enriquecer sugestões
        try:
            if self._car_class:
                track_id = self.db.get_or_create_track(self._track_name) if self._track_name else None
                learned = self.db.get_effective_rules(
                    self._car_class, track_id=track_id, min_effectiveness=0.6
                )
                for rule in learned:
                    param = rule["param_changed"]
                    if param not in deltas or deltas[param] == 0:
                        deltas[param] = rule["delta_applied"]
                        warnings.append(
                            f"📚 Regra aprendida: {rule['problem_detected']} → {param} {rule['delta_applied']:+d}"
                        )
        except Exception as e:
            logger.debug("Learning rules não consultadas: %s", e)

        # Enriquecer com memória persistente (sessões anteriores)
        deltas = self._apply_memory_to_deltas(deltas)
        if self._active_memory and self._active_memory.get("total_sessions", 0) > 0:
            warnings.append(
                f"🧠 Usando memória de {self._active_memory['total_sessions']} sessões anteriores"
            )

        # Salvar deltas em formato delta-name para display na GUI
        with self._state_lock:
            self._last_display_deltas = dict(deltas)

        # Converter nomes internos da IA para chaves reais do .svm
        deltas = deltas_to_svm(deltas)

        with self._state_lock:
            self._last_deltas = deltas

        # Registrar sugestão no banco
        try:
            if self._current_session_id and summary:
                self._last_suggestion_id = self.db.save_suggestion(
                    session_id=self._current_session_id,
                    after_lap=summary.lap_number,
                    source="neural_net",
                    deltas=deltas,
                    explanation="; ".join(warnings) if warnings else "",
                )
        except Exception as e:
            logger.debug("Erro ao salvar sugestão: %s", e)

        return deltas, warnings

    def request_heuristic_suggestion(self) -> tuple[dict[str, int], list[str]]:
        """Gera sugestão apenas com heurísticas (sem IA)."""
        summary = self.telemetry.last_summary
        if not summary:
            return {}, ["Nenhuma volta completada. Dirija pelo menos 1 volta."]

        tele_dict = self._features_to_dict(summary.features)
        heuristic_list = analyze_telemetry(
            tele_dict, self._car_class, self._current_level
        )
        deltas = merge_suggestions(heuristic_list)

        current_setup = self._current_svm.get_all_indices() if self._current_svm else None
        deltas, warnings = validate_deltas(
            deltas, max_delta=3, current_setup=current_setup
        )

        # Filtrar outputs impossíveis por classe de carro
        if self._car_class:
            deltas = filter_deltas_by_class(deltas, self._car_class.lower())

        # Aplicar perfil do piloto
        try:
            driver_id = self.config.get("driver_id", 1)
            profile = self.db.get_driver_profile(driver_id)
            prefs = self.db.get_driver_preferences(driver_id)
            agg = profile.get("aggression", 0.5) if profile else 0.5
            brk = profile.get("braking_style", 0.5) if profile else 0.5
            deltas = apply_driver_profile(
                deltas, aggression=agg,
                braking_style=brk, preferences=prefs
            )
        except Exception as e:
            logger.debug("Perfil do piloto não aplicado: %s", e)

        # Enriquecer com memória persistente (sessões anteriores)
        deltas = self._apply_memory_to_deltas(deltas)

        # Salvar deltas em formato delta-name para display na GUI
        with self._state_lock:
            self._last_display_deltas = dict(deltas)

        # Converter nomes internos da IA para chaves reais do .svm
        deltas = deltas_to_svm(deltas)

        warnings.insert(0, "ℹ️ Usando heurísticas (IA ainda aprendendo).")
        with self._state_lock:
            self._last_deltas = deltas

        # Registrar sugestão no banco
        try:
            summary = self.telemetry.last_summary
            if hasattr(self, '_current_session_id') and self._current_session_id and summary:
                self._last_suggestion_id = self.db.save_suggestion(
                    session_id=self._current_session_id,
                    after_lap=summary.lap_number,
                    source="heuristic",
                    deltas=deltas,
                    explanation="; ".join(warnings) if warnings else "",
                )
        except Exception as e:
            logger.debug("Erro ao salvar sugestão heurística: %s", e)

        return deltas, warnings

    def rate_last_suggestion(self, score: float):
        """Registra avaliação do usuário sobre a última sugestão."""
        with self._state_lock:
            self._recent_rewards.append(score)
            # Manter apenas últimas 20 avaliações
            if len(self._recent_rewards) > 20:
                self._recent_rewards = self._recent_rewards[-20:]
            suggestion_id = self._last_suggestion_id

        # Atualizar feedback na sugestão salva
        if suggestion_id:
            try:
                self.db.update_suggestion_feedback(
                    suggestion_id=suggestion_id,
                    accepted=score > 0,
                    feedback_bias=score,
                    confidence=abs(score),
                )
            except Exception as e:
                logger.debug("Erro ao atualizar feedback: %s", e)

    # ─────────────────────────────────────────────────────
    # Setups (.svm)
    # ─────────────────────────────────────────────────────

    def load_setup(self, filepath: str) -> SVMFile:
        """Carrega e parseia um arquivo .svm."""
        svm = parse_svm(filepath)
        self._current_svm = svm
        return svm

    def apply_suggestions(self):
        """Aplica as últimas sugestões ao setup carregado."""
        if not self._current_svm:
            logger.warning("Nenhum setup carregado.")
            return
        with self._state_lock:
            deltas = dict(self._last_deltas)
        if not deltas:
            logger.warning("Nenhuma sugestão para aplicar.")
            return

        apply_deltas(self._current_svm, deltas)
        save_svm(self._current_svm, backup_dir=str(BACKUPS_DIR))
        logger.info("Setup atualizado e salvo com backup.")

        # Salvar estado e snapshot para persistência
        self._save_session_state()
        self._save_setup_snapshot_auto()

    def save_setup_as(self, filepath: str):
        """Salva o setup atual em novo arquivo."""
        if not self._current_svm:
            return
        save_svm(self._current_svm, output_path=filepath, backup=False)

    def scan_setup_files(self) -> list[Path]:
        """Escaneia diretório de setups do LMU."""
        if not self.lmu_path:
            return []
        settings_dir = self.lmu_path / "UserData" / "player" / "Settings"
        return list_setup_files(settings_dir)

    # ─────────────────────────────────────────────────────
    # Setup Base (SOMENTE LEITURA — nunca é modificado)
    # ─────────────────────────────────────────────────────

    def load_base_setup(self, filepath: str) -> SVMFile:
        """Carrega um .svm como setup base (referência somente leitura)."""
        svm = parse_svm(filepath)
        self._base_svm = svm
        logger.info("Setup base carregado: %s (%d params ajustáveis)",
                     svm.filepath.name, len(svm.get_adjustable_params()))

        # Persistir que este setup foi o último usado
        self._save_session_state()
        return svm

    def get_base_setup(self) -> SVMFile | None:
        """Retorna o setup base carregado (ou None)."""
        return self._base_svm

    def clear_base_setup(self):
        """Remove o setup base da memória."""
        self._base_svm = None
        logger.info("Setup base limpo.")

    def create_setup_from_base(self, mode: str = "ia",
                                climate: str = "seco") -> Path:
        """
        Cria um NOVO .svm a partir do setup base.
        O arquivo base NUNCA é modificado.

        Args:
            mode: "ia", "heuristic" ou "copy"
            climate: "seco", "chuva_leve", "chuva_forte", "misto", "mescla"

        Returns:
            Path do novo arquivo criado.
        """
        if not self._base_svm:
            raise ValueError("Nenhum setup base carregado.")

        # Parsear uma CÓPIA FRESCA do arquivo base (não modifica o original)
        new_svm = parse_svm(self._base_svm.filepath)

        # Calcular deltas conforme modo
        deltas = {}
        if mode == "ia":
            deltas, _ = self.request_suggestion()
        elif mode == "heuristic":
            deltas, _ = self.request_heuristic_suggestion()
        # mode == "copy" → deltas vazio, cópia exata

        # Aplicar deltas climáticos
        climate_deltas = self._get_climate_deltas(climate)
        for key, val in climate_deltas.items():
            deltas[key] = deltas.get(key, 0) + val

        if deltas:
            apply_deltas(new_svm, deltas)

        # Gerar nome SetorFlow
        new_path = self._generate_setorflow_path(climate)

        # Salvar — nunca sobrescreve, cria novo
        save_svm(new_svm, output_path=new_path, backup=False)

        logger.info("Novo setup criado a partir do base: %s", new_path.name)
        return new_path

    def _get_climate_deltas(self, climate: str) -> dict[str, int]:
        """Retorna deltas de ajuste baseados na condição climática."""
        if climate == "seco":
            return {}
        elif climate == "chuva_leve":
            return {
                "FRONTLEFT.PressureSetting": -2,
                "FRONTRIGHT.PressureSetting": -2,
                "REARLEFT.PressureSetting": -2,
                "REARRIGHT.PressureSetting": -2,
                "REARWING.RWSetting": +2,
                "SUSPENSION.FrontAntiSwaySetting": -2,
                "SUSPENSION.RearAntiSwaySetting": -2,
            }
        elif climate == "chuva_forte":
            return {
                "FRONTLEFT.PressureSetting": -4,
                "FRONTRIGHT.PressureSetting": -4,
                "REARLEFT.PressureSetting": -4,
                "REARRIGHT.PressureSetting": -4,
                "REARWING.RWSetting": +4,
                "SUSPENSION.FrontAntiSwaySetting": -3,
                "SUSPENSION.RearAntiSwaySetting": -3,
                "FRONTLEFT.SpringSetting": -2,
                "FRONTRIGHT.SpringSetting": -2,
                "REARLEFT.SpringSetting": -2,
                "REARRIGHT.SpringSetting": -2,
            }
        elif climate == "misto":
            return {
                "FRONTLEFT.PressureSetting": -1,
                "FRONTRIGHT.PressureSetting": -1,
                "REARLEFT.PressureSetting": -1,
                "REARRIGHT.PressureSetting": -1,
                "REARWING.RWSetting": +1,
                "SUSPENSION.FrontAntiSwaySetting": -1,
                "SUSPENSION.RearAntiSwaySetting": -1,
            }
        elif climate == "mescla":
            return {
                "FRONTLEFT.PressureSetting": -2,
                "FRONTRIGHT.PressureSetting": -2,
                "REARLEFT.PressureSetting": -2,
                "REARRIGHT.PressureSetting": -2,
                "REARWING.RWSetting": +2,
                "SUSPENSION.FrontAntiSwaySetting": -1,
                "SUSPENSION.RearAntiSwaySetting": -1,
            }
        return {}

    def _generate_setorflow_path(self, climate: str) -> Path:
        """
        Gera o caminho do novo setup no padrão SetorFlow.
        Formato: SetorFlow_{clima}_{categoria}_{carro}_{DD-MM-AAAA}.svm
        O arquivo é salvo na mesma pasta do base.
        Se já existir, adiciona _2, _3...
        """
        from datetime import datetime as dt
        import re as _re

        # Dados do carro (da telemetria ou do base)
        car_name = self._car_name or "Desconhecido"
        car_class = self._car_class or "Geral"

        # Sanitizar nomes para uso em arquivos
        def sanitize(text: str) -> str:
            text = text.strip().replace(" ", "_")
            return _re.sub(r'[<>:"/\\|?*]', '', text)

        clima_map = {
            "seco": "seco",
            "chuva_leve": "chuva_leve",
            "chuva_forte": "chuva_forte",
            "misto": "misto",
            "mescla": "mescla_50-50",
        }
        clima_str = clima_map.get(climate, climate)
        date_str = dt.now().strftime("%d-%m-%Y")

        base_name = (
            f"SetorFlow_{sanitize(clima_str)}"
            f"_{sanitize(car_class)}"
            f"_{sanitize(car_name)}"
            f"_{date_str}"
        )

        # Salvar na mesma pasta do arquivo base
        output_dir = self._base_svm.filepath.parent

        # Anti-colisão: se já existe, adiciona sufixo
        candidate = output_dir / f"{base_name}.svm"
        counter = 2
        while candidate.exists():
            candidate = output_dir / f"{base_name}_{counter}.svm"
            counter += 1

        return candidate

    # ─────────────────────────────────────────────────────
    # Calculadora de Estratégia Quali / Corrida
    # ─────────────────────────────────────────────────────

    def calculate_session_strategy(
        self,
        mode: str,
        duration_min: float,
        fuel_mult: float = 1.0,
        tire_mult: float = 1.0,
    ) -> dict:
        """
        Calcula estratégia completa de sessão (Qualificação ou Corrida).

        Usa dados de telemetria/histórico para estimar voltas, combustível,
        desgaste de pneu e gerar deltas de setup recomendados.

        Args:
            mode: "quali" ou "race"
            duration_min: Duração da sessão em minutos
            fuel_mult: Multiplicador de consumo de combustível (1x, 2x, 3x)
            tire_mult: Multiplicador de desgaste de pneu (1x, 2x, 3x)

        Returns:
            Dict completo com estimativas, stints e deltas recomendados
        """
        from math import ceil
        from core.heuristics import get_session_deltas

        result = {
            "mode": mode,
            "duration_min": duration_min,
            "fuel_mult": fuel_mult,
            "tire_mult": tire_mult,
            # Estimativas
            "avg_lap_time": 0.0,
            "estimated_laps": 0,
            "fuel_per_lap": 0.0,
            "fuel_per_lap_adjusted": 0.0,
            "fuel_total_needed": 0.0,
            "fuel_recommended": 0.0,
            "fuel_capacity": 0.0,
            "fuel_weight_kg": 0.0,
            "fuel_tank_pct": 0.0,
            # Desgaste
            "wear_per_lap": 0.0,
            "wear_per_lap_adjusted": 0.0,
            "wear_total_pct": 0.0,
            "needs_tire_pit": False,
            # Stints
            "stints": [],
            "total_pits": 0,
            # Deltas recomendados
            "deltas": {},
            "delta_explanations": [],
            # Estado
            "data_source": "nenhum",
            "has_data": False,
        }

        duration_sec = duration_min * 60

        # ─── 1. Obter tempo médio de volta ───
        avg_lap_time = None

        # Prioridade 1: dados da sessão atual (lap_history)
        with self._state_lock:
            history = list(self._lap_history)
        valid_times = [h["time"] for h in history if h.get("valid") and h["time"] > 0]
        if valid_times:
            avg_lap_time = sum(valid_times) / len(valid_times)
            result["data_source"] = f"sessão atual ({len(valid_times)} voltas)"

        # Prioridade 2: summaries do TelemetryReader
        if avg_lap_time is None:
            summaries = self.telemetry.all_summaries
            s_times = [s.lap_time for s in summaries if s.is_valid and s.lap_time > 0]
            if s_times:
                avg_lap_time = sum(s_times) / len(s_times)
                result["data_source"] = f"telemetria ({len(s_times)} voltas)"

        # Prioridade 3: banco de dados (sessões anteriores)
        if avg_lap_time is None and self._car_name and self._track_name:
            try:
                car_id = self.db.get_or_create_car(self._car_name, self._car_class)
                track_id = self.db.get_or_create_track(self._track_name)
                db_avg = self.db.get_avg_lap_time(car_id, track_id)
                if db_avg and db_avg > 0:
                    avg_lap_time = db_avg
                    result["data_source"] = "banco de dados (histórico)"
            except Exception:
                pass

        # Prioridade 4: memória persistente
        if avg_lap_time is None and self._active_memory:
            mem_avg = self._active_memory.get("avg_lap_time")
            if mem_avg and mem_avg > 0:
                avg_lap_time = mem_avg
                result["data_source"] = "memória persistente"

        if avg_lap_time is None or avg_lap_time <= 0:
            result["data_source"] = "sem dados"
            return result

        result["avg_lap_time"] = avg_lap_time
        result["has_data"] = True

        # ─── 2. Calcular número de voltas ───
        estimated_laps = duration_sec / avg_lap_time
        result["estimated_laps"] = int(estimated_laps)

        # ─── 3. Calcular combustível ───
        fuel_per_lap = 0.0
        fuel_capacity = 0.0

        # Consumo por volta: dados live
        fuel_consumptions = []
        for i in range(1, len(history)):
            prev_feat = history[i - 1].get("features", {})
            curr_feat = history[i].get("features", {})
            prev_fuel = prev_feat.get("fuel", 0) or prev_feat.get("fuel_start", 0)
            curr_fuel = curr_feat.get("fuel", 0) or curr_feat.get("fuel_start", 0)
            if prev_fuel > 0 and curr_fuel > 0 and prev_fuel > curr_fuel:
                consumption = prev_fuel - curr_fuel
                if 0.1 < consumption < 20:
                    fuel_consumptions.append(consumption)

        if fuel_consumptions:
            fuel_per_lap = sum(fuel_consumptions) / len(fuel_consumptions)
        elif self._car_name and self._track_name:
            # Fallback: banco de dados
            try:
                car_id = self.db.get_or_create_car(self._car_name, self._car_class)
                track_id = self.db.get_or_create_track(self._track_name)
                db_fuel = self.db.get_avg_fuel_consumption(car_id, track_id)
                if db_fuel and db_fuel > 0:
                    fuel_per_lap = db_fuel
            except Exception:
                pass

        # Capacidade do tanque
        try:
            live = self.telemetry.get_live_telemetry()
            if live:
                fuel_capacity = live.get("fuel_capacity", 0.0) or 0.0
        except Exception:
            pass

        fuel_adjusted = fuel_per_lap * fuel_mult
        margin_laps = 2
        fuel_total = estimated_laps * fuel_adjusted
        fuel_with_margin = fuel_total + (margin_laps * fuel_adjusted)

        result["fuel_per_lap"] = fuel_per_lap
        result["fuel_per_lap_adjusted"] = fuel_adjusted
        result["fuel_total_needed"] = fuel_total
        result["fuel_capacity"] = fuel_capacity

        # ─── 4. Calcular stints ───
        if fuel_capacity > 0 and fuel_with_margin > 0:
            if fuel_with_margin <= fuel_capacity:
                # Cabe em um stint
                result["fuel_recommended"] = fuel_with_margin
                result["stints"] = [{
                    "stint": 1,
                    "fuel_load": fuel_with_margin,
                    "laps": result["estimated_laps"],
                    "pit_after": False,
                }]
                result["total_pits"] = 0
            else:
                # Precisa de pit stops
                n_stints = ceil(fuel_with_margin / fuel_capacity)
                result["total_pits"] = n_stints - 1
                result["fuel_recommended"] = fuel_capacity  # Stint 1 sempre cheio
                laps_per_stint = result["estimated_laps"] / n_stints
                stints = []
                remaining_laps = result["estimated_laps"]
                for s in range(n_stints):
                    stint_laps = int(min(laps_per_stint, remaining_laps))
                    if s == 0:
                        stint_fuel = fuel_capacity
                    else:
                        stint_fuel = min(
                            (stint_laps + margin_laps) * fuel_adjusted,
                            fuel_capacity,
                        )
                    stints.append({
                        "stint": s + 1,
                        "fuel_load": round(stint_fuel, 1),
                        "laps": stint_laps,
                        "pit_after": s < n_stints - 1,
                    })
                    remaining_laps -= stint_laps
                result["stints"] = stints
        else:
            result["fuel_recommended"] = fuel_with_margin

        # Peso do combustível (densidade média gasolina de corrida)
        FUEL_DENSITY_KG_PER_L = 0.742
        result["fuel_weight_kg"] = round(result["fuel_recommended"] * FUEL_DENSITY_KG_PER_L, 1)
        if fuel_capacity > 0:
            result["fuel_tank_pct"] = round(
                result["fuel_recommended"] / fuel_capacity * 100, 1
            )

        # ─── 5. Calcular desgaste de pneu ───
        wear_rates = []
        for h in history:
            feats = h.get("features", {})
            for wheel in ("wear_fl", "wear_fr", "wear_rl", "wear_rr"):
                w = feats.get(wheel, 0)
                if 0 < w < 1:
                    wear_rates.append(w)

        if wear_rates and len(history) > 1:
            # wear é fração acumulada; calcular taxa por volta
            avg_wear = sum(wear_rates) / len(wear_rates)
            wear_per_lap = avg_wear / max(len(history), 1)
        else:
            wear_per_lap = 0.0

        wear_adjusted = wear_per_lap * tire_mult
        wear_total = estimated_laps * wear_adjusted * 100  # em %

        result["wear_per_lap"] = round(wear_per_lap * 100, 2)
        result["wear_per_lap_adjusted"] = round(wear_adjusted * 100, 2)
        result["wear_total_pct"] = round(wear_total, 1)
        result["needs_tire_pit"] = wear_total > 85

        # ─── 6. Gerar deltas recomendados ───
        car_class = self._car_class.lower() if self._car_class else "hypercar"
        deltas = get_session_deltas(mode, car_class)
        result["deltas"] = deltas

        # Explicações contextuais
        explanations = []
        if mode == "quali":
            explanations.append("Molas mais duras (+1): carro mais leve responde melhor")
            explanations.append("Camber mais agressivo (+1): máximo grip em curva")
            explanations.append("Pressão inicial mais baixa (-1): aquece rápido com menos peso")
            explanations.append("Engine Mix: modo potência (+1)")
            explanations.append("Radiador: mínimo (-1): menos arrasto")
            if car_class in ("hypercar", "lmdh"):
                explanations.append("Deploy máximo (+2): usar toda a energia elétrica")
        else:
            explanations.append("Molas mais macias (-1): compensar peso extra de combustível")
            explanations.append("Camber conservador (-1): preservar pneus na corrida")
            explanations.append("Radiador: mais aberto (+1): prevenir superaquecimento")
            explanations.append("Anti-roll bars: mais macias (-1): estabilidade com peso")
            if result["needs_tire_pit"]:
                explanations.append("⚠️ Desgaste previsto alto — trocar pneus no pit")
            if result["total_pits"] > 0:
                explanations.append(
                    f"⛽ Necessário {result['total_pits']} pit stop(s) para combustível"
                )

        result["delta_explanations"] = explanations

        return result

    # ─────────────────────────────────────────────────────
    # Cálculo de Fuel Ratio e Virtual Energy
    # ─────────────────────────────────────────────────────

    def calculate_fuel_strategy(self) -> dict:
        """
        Calcula Fuel Ratio e Virtual Energy equilibrado.

        Usa histórico de voltas para calcular consumo médio por volta
        e recomendar configuração de combustível e energia.

        Returns:
            Dict com fuel_per_lap, laps_remaining, recommended_fuel_ratio,
            virtual_energy_recommendation, battery_status, etc.
        """
        result = {
            "fuel_per_lap": 0.0,
            "fuel_current": 0.0,
            "fuel_capacity": 0.0,
            "fuel_fraction": 0.0,
            "laps_remaining": 0,
            "recommended_fuel_ratio": "---",
            "fuel_ratio_value": 0.0,
            "avg_lap_time": 0.0,
            "battery_charge": -1.0,
            "virtual_energy_recommendation": "---",
            "energy_balance": "---",
            "has_regen": False,
        }

        if not self.telemetry or not self.telemetry._connected:
            return result

        # Dados ao vivo
        try:
            live = self.telemetry.get_live_telemetry()
            if live:
                result["fuel_current"] = live.get("fuel", 0.0)
                result["fuel_capacity"] = live.get("fuel_capacity", 0.0)
                if result["fuel_capacity"] > 0:
                    result["fuel_fraction"] = result["fuel_current"] / result["fuel_capacity"]
        except Exception:
            pass

        # Consumo médio por volta a partir do histórico
        fuel_consumptions = []
        if len(self._lap_history) >= 2:
            for i in range(1, len(self._lap_history)):
                prev = self._lap_history[i - 1]
                curr = self._lap_history[i]
                prev_fuel = prev.get("features", {}).get("fuel", 0)
                curr_fuel = curr.get("features", {}).get("fuel", 0)
                if prev_fuel > 0 and curr_fuel > 0 and prev_fuel > curr_fuel:
                    consumption = prev_fuel - curr_fuel
                    if 0.1 < consumption < 20:  # Filtro de sanidade
                        fuel_consumptions.append(consumption)

        if fuel_consumptions:
            avg_consumption = sum(fuel_consumptions) / len(fuel_consumptions)
            result["fuel_per_lap"] = avg_consumption

            if avg_consumption > 0 and result["fuel_current"] > 0:
                result["laps_remaining"] = int(result["fuel_current"] / avg_consumption)

            # Fuel Ratio = litros/volta normalizado pela capacidade
            if result["fuel_capacity"] > 0:
                result["fuel_ratio_value"] = avg_consumption / result["fuel_capacity"]

                # Classificar Fuel Ratio
                ratio = result["fuel_ratio_value"]
                if ratio < 0.02:
                    result["recommended_fuel_ratio"] = "Econômico (pode acelerar mais)"
                elif ratio < 0.04:
                    result["recommended_fuel_ratio"] = "Equilibrado ✅"
                elif ratio < 0.06:
                    result["recommended_fuel_ratio"] = "Alto (considere poupar)"
                else:
                    result["recommended_fuel_ratio"] = "Crítico ⚠️ (consumo muito alto)"

        # Tempo médio de volta
        valid_times = [h["time"] for h in self._lap_history if h.get("valid")]
        if valid_times:
            result["avg_lap_time"] = sum(valid_times) / len(valid_times)

        # Virtual Energy / Bateria (Hypercar)
        is_hypercar = self._car_class.lower() in ("hypercar", "lmdh") if self._car_class else False
        result["has_regen"] = is_hypercar

        if is_hypercar:
            try:
                live = self.telemetry.get_live_telemetry()
                if live:
                    battery = live.get("battery_charge", -1.0)
                    result["battery_charge"] = battery

                    if battery >= 0:
                        if battery > 0.70:
                            result["virtual_energy_recommendation"] = (
                                "Deploy mais (+1-2) — bateria alta, use a potência"
                            )
                            result["energy_balance"] = "Deploy Máximo ⚡"
                        elif battery > 0.40:
                            result["virtual_energy_recommendation"] = (
                                "Equilibrado — manter deploy/regen atuais"
                            )
                            result["energy_balance"] = "Equilibrado ✅"
                        elif battery > 0.20:
                            result["virtual_energy_recommendation"] = (
                                "Regen mais (+1) — bateria baixa, recupere nas frenagens"
                            )
                            result["energy_balance"] = "Regeneração 🔋"
                        else:
                            result["virtual_energy_recommendation"] = (
                                "Regen máximo (+2) — bateria crítica! ⚠️"
                            )
                            result["energy_balance"] = "Crítico ⚠️"
            except Exception:
                pass

        return result

    # ─────────────────────────────────────────────────────
    # Callback de volta completada
    # ─────────────────────────────────────────────────────

    def _on_lap_completed(self, summary):
        """Chamado quando uma volta é concluída (pelo TelemetryReader)."""
        try:
            # Registrar carro e pista no banco
            car_id = self.db.get_or_create_car(
                summary.vehicle_name,
                summary.vehicle_class
            )
            track_id = self.db.get_or_create_track(summary.track_name)

            # Atualizar info do carro
            self._car_name = summary.vehicle_name
            self._car_class = summary.vehicle_class
            self._track_name = summary.track_name

            # ── Carregar memória persistente (apenas na 1ª volta) ──
            combo = (car_id, track_id)
            if self._memory_loaded_for != combo:
                self._load_session_memory(car_id, track_id)
                self._memory_loaded_for = combo

                # Soft-reset do normalizer na troca de pista/carro
                # para que novos dados influenciem mais rápido
                if self.normalizer._count > 50:
                    self.normalizer.soft_reset(keep_ratio=0.2)
                    logger.info("Normalizer resetado por troca de combo.")

                # Atualizar contagem de sessões na memória
                mem = self._active_memory or {}
                self.db.save_car_track_memory(car_id, track_id, {
                    "total_sessions": mem.get("total_sessions", 0) + 1,
                })

                # ── Restaurar estado da sessão anterior ──
                self._restore_session_state(car_id, track_id)

            # Registrar sessão + volta em transação atômica
            with self.db.transaction():
                if not hasattr(self, '_current_session_id') or self._current_session_id is None:
                    driver_id = self.db.get_or_create_driver(
                        self.config.get("driver_name", "Piloto")
                    )
                    self._current_session_id = self.db.create_session(
                        driver_id=driver_id,
                        car_id=car_id,
                        track_id=track_id,
                        air_temp=summary.ambient_temp,
                        track_temp=summary.track_temp,
                    )
                session_id = self._current_session_id

                # Registrar volta — construir lap_data dict
                features = summary.features
                lap_data = {
                    "lap_number": summary.lap_number,
                    "lap_time": summary.lap_time,
                    "is_valid": 1 if summary.is_valid else 0,
                    "fuel_at_start": 0,
                    "fuel_used": 0,
                }
                # Mapear features nomeadas para campos da tabela laps
                feature_dict = self._features_to_dict(features)
                for key in ("temp_fl_inner", "temp_fl_middle", "temp_fl_outer",
                            "temp_fr_inner", "temp_fr_middle", "temp_fr_outer",
                            "temp_rl_inner", "temp_rl_middle", "temp_rl_outer",
                            "temp_rr_inner", "temp_rr_middle", "temp_rr_outer",
                            "pressure_fl", "pressure_fr", "pressure_rl", "pressure_rr",
                            "wear_fl", "wear_fr", "wear_rl", "wear_rr",
                            "load_fl", "load_fr", "load_rl", "load_rr",
                            "ride_height_f", "ride_height_r",
                            "downforce_f", "downforce_r", "max_speed"):
                    lap_data[key] = feature_dict.get(key, 0.0)
                lap_data["avg_pitch"] = feature_dict.get("pitch", 0.0)
                lap_data["avg_roll"] = feature_dict.get("roll", 0.0)
                lap_data["avg_heave"] = feature_dict.get("heave", 0.0)
                # Brake temps not in features, set to 0
                for bt in ("max_brake_temp_fl", "max_brake_temp_fr",
                            "max_brake_temp_rl", "max_brake_temp_rr"):
                    lap_data[bt] = 0.0

                self.db.insert_lap(session_id=session_id, lap_data=lap_data)

            # Acumular histórico para análise de tendências
            with self._state_lock:
                self._lap_history.append({
                    "lap": summary.lap_number,
                    "time": summary.lap_time,
                    "valid": summary.is_valid,
                    "features": feature_dict,
                    "grip": feature_dict.get("grip_avg", 0.5),
                    "rain": feature_dict.get("raining", 0.0),
                })
                # Manter últimas 30 voltas
                if len(self._lap_history) > 30:
                    self._lap_history = self._lap_history[-30:]

            # Atualizar normalizer com novas features
            self.normalizer.update(summary.features)

            # Soft-reset do normalizer se acumulou amostras demais
            if self.normalizer.should_reset():
                self.normalizer.soft_reset()

            # ── Reward COMPLETO (todos os 9 fatores) ──
            try:
                features_norm = self.normalizer.normalize(summary.features)

                if self._last_deltas:
                    recent_times = self.db.get_recent_lap_times(session_id, count=5)
                    reward = 0.0
                    if len(recent_times) >= 2:
                        # Construir dados completos para reward
                        # Formato esperado por _reward_temp_balance: temp_{wheel}_{zone}
                        temps_after = {
                            "temp_fl_inner": feature_dict.get("temp_fl_inner", 0),
                            "temp_fl_middle": feature_dict.get("temp_fl_middle", 0),
                            "temp_fl_outer": feature_dict.get("temp_fl_outer", 0),
                            "temp_fr_inner": feature_dict.get("temp_fr_inner", 0),
                            "temp_fr_middle": feature_dict.get("temp_fr_middle", 0),
                            "temp_fr_outer": feature_dict.get("temp_fr_outer", 0),
                            "temp_rl_inner": feature_dict.get("temp_rl_inner", 0),
                            "temp_rl_middle": feature_dict.get("temp_rl_middle", 0),
                            "temp_rl_outer": feature_dict.get("temp_rl_outer", 0),
                            "temp_rr_inner": feature_dict.get("temp_rr_inner", 0),
                            "temp_rr_middle": feature_dict.get("temp_rr_middle", 0),
                            "temp_rr_outer": feature_dict.get("temp_rr_outer", 0),
                        }
                        wear_after = {
                            "fl": feature_dict.get("wear_fl", 0),
                            "fr": feature_dict.get("wear_fr", 0),
                            "rl": feature_dict.get("wear_rl", 0),
                            "rr": feature_dict.get("wear_rr", 0),
                        }
                        user_bias = feature_dict.get("user_feedback_bias", 0)
                        user_conf = feature_dict.get("user_confidence", 0.5)

                        reward = compute_reward(
                            lap_times_before=recent_times[1:],
                            lap_times_after=[recent_times[0]],
                            temps_after=temps_after,
                            grip_after=feature_dict.get("grip_avg", 0.5),
                            user_feedback=user_bias,
                            user_confidence=user_conf,
                            wear_after=wear_after,
                        )

                    # Montar output com nível correto
                    from core.brain import LEVEL_OUTPUTS
                    output_names = LEVEL_OUTPUTS.get(self._current_level, LEVEL_OUTPUTS["basic"])
                    output_vec = np.zeros(len(output_names), dtype=np.float32)
                    for i, key in enumerate(output_names):
                        output_vec[i] = self._last_deltas.get(key, 0)

                    self.db.save_training_data(
                        session_id=session_id,
                        car_id=car_id,
                        track_id=track_id,
                        input_vec=features_norm,
                        output_vec=output_vec,
                        reward=reward,
                    )
                    # Invalidar cache de total_samples
                    self._cached_total_samples = None

                    # ── Treinamento ADAPTATIVO ──
                    # Confiança baixa → treina a cada 3 voltas (aprende rápido)
                    # Confiança média → treina a cada 5 voltas
                    # Confiança alta → treina a cada 10 voltas (estável)
                    confidence = self.ai_confidence()
                    if confidence < 0.3:
                        train_interval = 3
                        train_epochs = 5
                        train_limit = 200
                    elif confidence < 0.6:
                        train_interval = 5
                        train_epochs = 3
                        train_limit = 150
                    else:
                        train_interval = 10
                        train_epochs = 2
                        train_limit = 100

                    if summary.lap_number % train_interval == 0:
                        td = self.db.load_training_data(car_id, track_id, limit=train_limit)
                        if td:
                            model = self.model_manager.get_model(
                                summary.vehicle_name, summary.track_name,
                                car_class=summary.vehicle_class,
                                level=self._current_level,
                            )
                            self.trainer.set_model(model)
                            result = self.trainer.train_online(td, epochs=train_epochs)
                            logger.info(
                                "Treinamento online [%s]: %d amostras, loss=%.4f, lr=%.1e",
                                self._current_level, result.total_samples,
                                result.final_loss, self.trainer.current_lr,
                            )

                            # Salvar modelo após treinamento
                            self.model_manager.save_model(
                                model=model,
                                car_class=summary.vehicle_class,
                                car_name=summary.vehicle_name,
                                track_name=summary.track_name,
                                metadata={"reward": result.avg_reward,
                                          "epoch": result.epochs_completed},
                            )

                            # Transfer Learning: criar modelo compartilhado
                            # quando há modelos suficientes da mesma classe
                            self._try_create_shared_model(summary.vehicle_class)

            except Exception as e:
                logger.debug("Erro no treinamento online: %s", e)

            # ── Auto-progressão de nível ──
            self._check_level_progression()

            # ── Detecção proativa de tendências ──
            self._check_trends(feature_dict)

            # ── Learning rules multi-problema ──
            self._record_learning_rules_multi(feature_dict)

            # ── Atualizar memória persistente carro×pista ──
            self._update_car_track_memory(car_id, track_id,
                                          summary.lap_time, feature_dict)

            # ── Auto-suggest ──
            if (self._auto_suggest_enabled
                    and summary.lap_number >= 2
                    and summary.lap_number % self._auto_suggest_after_laps == 0):
                self._generate_auto_suggestion()

            # ── LLM Auto-aprendizagem ──
            self._llm_auto_analyze(feature_dict, summary)

            # ── Salvar estado da sessão periodicamente ──
            if summary.lap_number % 5 == 0:
                self._save_session_state()

            logger.info(
                "Volta %d registrada: %.3fs (%s @ %s) [nível=%s, conf=%.0f%%]",
                summary.lap_number, summary.lap_time,
                summary.vehicle_name, summary.track_name,
                self._current_level, self.ai_confidence() * 100,
            )

        except Exception as e:
            logger.error("Erro ao registrar volta: %s", e)

    # ─────────────────────────────────────────────────────
    # Auto-progressão de nível
    # ─────────────────────────────────────────────────────

    def _check_level_progression(self):
        """
        Progride automaticamente o nível da IA:
        - basic (< 50 amostras ou confiança < 0.3)
        - intermediate (50-200 amostras e confiança >= 0.3)
        - advanced (200+ amostras e confiança >= 0.6)
        """
        samples = self.total_samples()
        confidence = self.ai_confidence()
        old_level = self._current_level

        if samples >= 200 and confidence >= 0.6:
            self._current_level = "advanced"
        elif samples >= 50 and confidence >= 0.3:
            self._current_level = "intermediate"
        else:
            self._current_level = "basic"

        if self._current_level != old_level:
            logger.info(
                "IA progrediu de nível: %s → %s (%d amostras, %.0f%% confiança)",
                old_level, self._current_level, samples, confidence * 100,
            )
            # Notificar GUI via callback
            if self._on_trend_alert_callback:
                self._on_trend_alert_callback(
                    f"🎓 IA evoluiu para nível **{self._current_level.upper()}**! "
                    f"({samples} amostras, {confidence*100:.0f}% confiança)\n"
                    f"Agora pode ajustar mais parâmetros com maior precisão."
                )

    # ─────────────────────────────────────────────────────
    # Detecção proativa de tendências
    # ─────────────────────────────────────────────────────

    def _check_trends(self, current: dict):
        """
        Analisa tendências ao longo das últimas voltas:
        - Tempos piorando → alerta
        - Grip caindo → alerta de desgaste
        - Temperatura subindo → alerta de superaquecimento
        - Chuva mudando → alerta climático
        """
        if len(self._lap_history) < 5:
            return

        alerts = []
        recent = self._lap_history[-5:]
        times = [h["time"] for h in recent if h["valid"]]

        # 1. Tempos piorando (tendência de piora > 0.5s nas últimas 5 voltas)
        if len(times) >= 3:
            deltas_t = [times[i] - times[i-1] for i in range(1, len(times))]
            avg_delta = sum(deltas_t) / len(deltas_t)
            if avg_delta > 0.5:
                alerts.append(
                    "📈 **Tempos piorando**: média +{:.2f}s por volta. "
                    "Possível desgaste de pneus ou perda de grip.".format(avg_delta)
                )

        # 2. Grip caindo ao longo das voltas
        grips = [h["grip"] for h in recent if h["grip"] > 0]
        if len(grips) >= 3:
            grip_trend = grips[-1] - grips[0]
            if grip_trend < -0.1:
                alerts.append(
                    "🏎️ **Grip diminuindo**: caiu {:.1f}% nas últimas {} voltas. "
                    "Considere ajustar pressão ou verificar desgaste.".format(
                        abs(grip_trend) * 100, len(grips)
                    )
                )

        # 3. Mudança climática
        rains = [h["rain"] for h in recent]
        if len(rains) >= 3:
            rain_start = sum(rains[:2]) / 2
            rain_end = sum(rains[-2:]) / 2
            if rain_end - rain_start > 0.3:
                alerts.append(
                    "🌧️ **Chuva aumentando**: condições mudaram significativamente. "
                    "Considere ajustar setup para pista molhada."
                )
            elif rain_start - rain_end > 0.3:
                alerts.append(
                    "☀️ **Pista secando**: condições melhorando. "
                    "Considere voltar para setup de seco."
                )

        # 4. Superaquecimento de pneus (temperatura subindo continuamente)
        for wheel in ("fl", "fr", "rl", "rr"):
            key = f"temp_{wheel}_middle"
            temps = [h["features"].get(key, 0) for h in recent if h["features"].get(key, 0) > 0]
            if len(temps) >= 3 and temps[-1] - temps[0] > 15:
                alerts.append(
                    f"🔥 **Pneu {wheel.upper()} superaquecendo**: "
                    f"subiu {temps[-1] - temps[0]:.0f}°C nas últimas voltas."
                )
                break  # Só alertar uma vez para pneus

        # Enviar alertas via callback
        if alerts and self._on_trend_alert_callback:
            for alert in alerts:
                self._on_trend_alert_callback(alert)

    # ─────────────────────────────────────────────────────
    # Learning rules multi-problema
    # ─────────────────────────────────────────────────────

    def _record_learning_rules_multi(self, tele: dict):
        """
        Registra MÚLTIPLAS learning rules (não apenas a primeira).
        Associa cada problema detectado com cada delta aplicado.
        """
        if not self._last_deltas or not self._car_class:
            return

        problems = self._detect_all_problems(tele)
        if not problems:
            return

        try:
            track_id = (self.db.get_or_create_track(self._track_name)
                        if self._track_name else None)

            # Pegar reward mais recente
            reward = self._recent_rewards[-1] if self._recent_rewards else 0.0

            for problem in problems:
                for param, delta in self._last_deltas.items():
                    if delta == 0:
                        continue
                    self.db.record_learning_rule(
                        car_class=self._car_class,
                        track_id=track_id,
                        problem=problem,
                        solution=f"{param}:{delta:+d}",
                        param=param,
                        delta=delta,
                        reward=reward,
                        improvement_pct=0.0,
                    )
        except Exception as e:
            logger.debug("Erro ao registrar learning rules: %s", e)

    def _detect_all_problems(self, tele: dict) -> list[str]:
        """Detecta TODOS os problemas na telemetria (não apenas o primeiro)."""
        issues = []

        # Temperatura desbalanceada por roda
        for wheel in ("fl", "fr", "rl", "rr"):
            inner = tele.get(f"temp_{wheel}_inner", 0)
            outer = tele.get(f"temp_{wheel}_outer", 0)
            if inner and outer and abs(inner - outer) > 10:
                issues.append(f"temp_spread_{wheel}")

        # Grip baixo
        grip = tele.get("grip_avg", 0.5)
        if grip < 0.4:
            issues.append("low_grip")

        # Chuva
        rain = tele.get("raining", 0)
        if rain > 0.3:
            issues.append("rain")

        # Understeer/Oversteer
        bias = tele.get("user_feedback_bias", 0)
        if bias < -0.3:
            issues.append("understeer")
        elif bias > 0.3:
            issues.append("oversteer")

        # Ride height muito baixo (bottoming)
        rh_f = tele.get("ride_height_f", 0.1)
        rh_r = tele.get("ride_height_r", 0.1)
        if 0 < rh_f < 0.02:
            issues.append("bottoming_front")
        if 0 < rh_r < 0.02:
            issues.append("bottoming_rear")

        # Pressão desbalanceada (centro quente vs bordas)
        for wheel in ("fl", "fr", "rl", "rr"):
            inner = tele.get(f"temp_{wheel}_inner", 0)
            middle = tele.get(f"temp_{wheel}_middle", 0)
            outer = tele.get(f"temp_{wheel}_outer", 0)
            if inner > 0 and middle > 0 and outer > 0:
                avg_edges = (inner + outer) / 2
                if middle > avg_edges + 8:
                    issues.append(f"pressure_high_{wheel}")
                elif middle < avg_edges - 8:
                    issues.append(f"pressure_low_{wheel}")

        return issues

    # ─────────────────────────────────────────────────────
    # Memória persistente (carro × pista)
    # ─────────────────────────────────────────────────────

    def _load_session_memory(self, car_id: int, track_id: int):
        """
        Carrega memória persistente de sessões anteriores
        para este carro × pista. Chamado no início da sessão.
        Cada carro tem mecânica diferente, mesmo na mesma pista.
        """
        try:
            memory = self.db.load_car_track_memory(car_id, track_id)
            self._active_memory = memory

            if memory:
                logger.info(
                    "Memória carregada: %s sessões, %s voltas, melhor volta: %s",
                    memory.get("total_sessions", 0),
                    memory.get("total_laps", 0),
                    f"{memory['best_lap_time']:.3f}" if memory.get("best_lap_time") else "N/A",
                )

                # Carregar deltas que historicamente funcionaram
                effective = self.db.get_effective_deltas_history(car_id, track_id)
                if effective:
                    self._memory_optimal_deltas = self._compute_weighted_deltas(effective)
                    logger.info(
                        "Deltas ótimos da memória: %d parâmetros de %d amostras",
                        len(self._memory_optimal_deltas), len(effective),
                    )
                else:
                    self._memory_optimal_deltas = {}

                # Carregar histórico de sessões para contexto
                history = self.db.get_car_track_history(car_id, track_id)
                self._session_history = history

                # Notificar GUI se tiver callback
                if self._on_trend_alert_callback and memory.get("total_sessions", 0) > 0:
                    msg = (
                        f"🧠 **Memória carregada** para este carro × pista!\n"
                        f"📊 {memory.get('total_sessions', 0)} sessões anteriores, "
                        f"{memory.get('total_laps', 0)} voltas\n"
                    )
                    if memory.get("best_lap_time"):
                        msg += f"🏆 Melhor volta anterior: {memory['best_lap_time']:.3f}s\n"
                    if memory.get("recurring_problems"):
                        problems = memory["recurring_problems"]
                        if isinstance(problems, list) and problems:
                            msg += f"⚠️ Problemas recorrentes: {', '.join(problems[:5])}\n"
                    msg += "A IA usará essa experiência para sugestões melhores."
                    self._on_trend_alert_callback(msg)
            else:
                self._active_memory = None
                self._memory_optimal_deltas = {}
                self._session_history = []
                logger.info("Sem memória anterior para este carro × pista.")

        except Exception as e:
            logger.debug("Erro ao carregar memória: %s", e)
            self._active_memory = None
            self._memory_optimal_deltas = {}
            self._session_history = []

    def _compute_weighted_deltas(self, effective: list[dict]) -> dict[str, float]:
        """
        Calcula média ponderada de deltas que funcionaram,
        usando o reward como peso.
        """
        from core.brain import LEVEL_OUTPUTS
        output_names = LEVEL_OUTPUTS.get(self._current_level, LEVEL_OUTPUTS["basic"])

        weighted_sum = {}
        weight_total = {}

        for item in effective:
            output = item["output"]
            reward = max(item["reward"], 0.01)
            for i, name in enumerate(output_names):
                if i < len(output) and output[i] != 0:
                    weighted_sum[name] = weighted_sum.get(name, 0) + output[i] * reward
                    weight_total[name] = weight_total.get(name, 0) + reward

        result = {}
        for name in weighted_sum:
            if weight_total[name] > 0:
                avg = weighted_sum[name] / weight_total[name]
                # Arredondar para inteiro (deltas são índices inteiros)
                rounded = round(avg)
                if rounded != 0:
                    result[name] = rounded

        return result

    def _update_car_track_memory(self, car_id: int, track_id: int,
                                 lap_time: float, feature_dict: dict):
        """
        Atualiza a memória persistente após cada volta.
        Chamado de _on_lap_completed.
        """
        try:
            memory = self.db.load_car_track_memory(car_id, track_id) or {}

            total_laps = memory.get("total_laps", 0) + 1
            best_lap = memory.get("best_lap_time")
            if best_lap is None or (lap_time > 0 and lap_time < best_lap):
                best_lap = lap_time

            # Média móvel ponderada do lap time
            avg_lap = memory.get("avg_lap_time")
            if avg_lap and avg_lap > 0:
                avg_lap = avg_lap * 0.9 + lap_time * 0.1
            else:
                avg_lap = lap_time

            # Detectar problemas recorrentes
            problems = self._detect_all_problems(feature_dict)
            existing_problems = memory.get("recurring_problems") or []
            if isinstance(existing_problems, str):
                import json
                try:
                    existing_problems = json.loads(existing_problems)
                except (json.JSONDecodeError, TypeError):
                    existing_problems = []

            # Contar frequência de problemas
            problem_counts = {}
            for p in existing_problems:
                if isinstance(p, str):
                    problem_counts[p] = problem_counts.get(p, 1)
            for p in problems:
                problem_counts[p] = problem_counts.get(p, 0) + 1

            # Manter top 10 problemas mais frequentes
            sorted_problems = sorted(problem_counts.keys(),
                                     key=lambda x: problem_counts[x], reverse=True)[:10]

            # Setup atual como referência
            setup_indices = None
            setup_path = None
            if self._current_svm:
                setup_indices = self._current_svm.get_all_indices()
                setup_path = str(self._current_svm.filepath)

            # Calcular confiança da memória
            confidence = min(1.0, total_laps / 100)

            data = {
                "total_laps": total_laps,
                "best_lap_time": best_lap,
                "avg_lap_time": avg_lap,
                "avg_grip": feature_dict.get("grip_avg"),
                "avg_tire_wear_rate": feature_dict.get("wear_fl", 0),
                "track_bumpiness": feature_dict.get("heave", 0),
                "recurring_problems": sorted_problems,
                "memory_confidence": confidence,
                "last_session_at": "CURRENT_TIMESTAMP",
            }

            # Salvar o melhor setup se a volta for a melhor
            if setup_indices and best_lap == lap_time:
                data["best_setup_indices"] = setup_indices
                data["best_setup_path"] = setup_path

            # Deltas ótimos: média ponderada com memória anterior
            if self._last_display_deltas:
                optimal = memory.get("optimal_deltas") or {}
                if isinstance(optimal, str):
                    import json
                    try:
                        optimal = json.loads(optimal)
                    except (json.JSONDecodeError, TypeError):
                        optimal = {}
                # Só atualizar com deltas que melhoraram (reward > 0)
                if self._recent_rewards and self._recent_rewards[-1] > 0.1:
                    for k, v in self._last_display_deltas.items():
                        if v != 0:
                            old = optimal.get(k, 0)
                            optimal[k] = round(old * 0.7 + v * 0.3)
                    data["optimal_deltas"] = optimal

            self.db.save_car_track_memory(car_id, track_id, data)

        except Exception as e:
            logger.debug("Erro ao atualizar memória carro×pista: %s", e)

    def _apply_memory_to_deltas(self, deltas: dict[str, int]) -> dict[str, int]:
        """
        Enriquece as sugestões da IA com a memória persistente.
        Se a memória sabe que um delta funcionou antes, usa como base.
        A IA pode sobrescrever — a memória só preenche lacunas.
        """
        if not self._memory_optimal_deltas:
            return deltas

        memory_conf = 0.0
        if self._active_memory:
            memory_conf = self._active_memory.get("memory_confidence", 0)

        if memory_conf < 0.1:
            return deltas

        # Peso da memória: começa em 0.5 (50%) e diminui conforme a IA ganha confiança
        ai_conf = self.ai_confidence()
        memory_weight = max(0.1, 0.5 * (1.0 - ai_conf) * memory_conf)

        for param, mem_val in self._memory_optimal_deltas.items():
            current = deltas.get(param, 0)
            if current == 0 and mem_val != 0:
                # IA não tem opinião → usar memória
                deltas[param] = mem_val
            elif current != 0 and mem_val != 0:
                # Blend: IA + memória
                blended = round(current * (1 - memory_weight) + mem_val * memory_weight)
                if blended != 0:
                    deltas[param] = blended

        return deltas

    # ─────────────────────────────────────────────────────
    # Aprendizagem de setups (.svm) disponíveis
    # ─────────────────────────────────────────────────────

    def learn_from_all_setups(self) -> dict:
        """
        Escaneia todos os .svm disponíveis no LMU e aprende com eles.
        Extrai parâmetros, armazena na biblioteca e gera conhecimento
        sobre padrões de setup por pista.

        Returns:
            Dict com estatísticas: {"scanned": N, "new": M, "tracks": T}
        """
        if not self.lmu_path:
            logger.warning("LMU não detectado — impossível escanear setups.")
            return {"scanned": 0, "new": 0, "tracks": 0}

        from data.svm_parser import parse_svm, list_setup_files, list_track_folders
        import hashlib

        settings_dir = self.lmu_path / "UserData" / "player" / "Settings"
        if not settings_dir.exists():
            return {"scanned": 0, "new": 0, "tracks": 0}

        stats = {"scanned": 0, "new": 0, "tracks": 0}
        track_folders = list_track_folders(settings_dir)
        stats["tracks"] = len(track_folders)

        for track_dir in track_folders:
            track_folder_name = track_dir.name
            # Associar pasta com pista no banco
            track_id = self.db.get_or_create_track(
                track_folder_name, folder_name=track_folder_name
            )

            svm_files = list(track_dir.glob("*.svm"))
            for svm_path in svm_files:
                stats["scanned"] += 1
                try:
                    # Hash para detectar mudanças
                    content = svm_path.read_bytes()
                    file_hash = hashlib.md5(content).hexdigest()

                    # Parsear setup
                    svm = parse_svm(svm_path)
                    indices = svm.get_all_indices()

                    # Salvar na biblioteca
                    lib_id = self.db.save_setup_to_library(
                        file_path=str(svm_path),
                        file_name=svm_path.name,
                        track_folder=track_folder_name,
                        param_indices=indices,
                        track_id=track_id,
                        file_hash=file_hash,
                    )

                    # Aprender ranges de parâmetros (para qualquer carro futuro)
                    for param in svm.get_adjustable_params():
                        if param.num_steps > 1:
                            # Registrar como range genérico (car_id=0 → template)
                            try:
                                self.db.upsert_param_range(
                                    car_id=0,  # genérico
                                    param_name=param.name,
                                    section=param.section,
                                    min_idx=0,
                                    max_idx=param.num_steps - 1,
                                )
                            except Exception:
                                pass

                    stats["new"] += 1

                except Exception as e:
                    logger.debug("Erro ao processar %s: %s", svm_path.name, e)

        logger.info(
            "Biblioteca de setups: %d escaneados, %d processados, %d pistas",
            stats["scanned"], stats["new"], stats["tracks"],
        )
        return stats

    def learn_from_setup_comparisons(self, track_id: int):
        """
        Compara setups da mesma pista para descobrir padrões.
        Gera pseudo-training data a partir das diferenças entre setups.
        """
        setups = self.db.get_setups_for_track(track_id)
        if len(setups) < 2:
            return

        from core.brain import DELTA_TO_SVM
        import numpy as np

        # Criar mapeamento reverso: SVM key → delta name
        svm_to_delta = {}
        for delta_name, svm_keys in DELTA_TO_SVM.items():
            for sk in svm_keys:
                svm_to_delta[sk] = delta_name

        # Comparar cada par de setups: a diferença nos índices
        # é um "delta" que pode ser útil para aprendizagem
        for i in range(len(setups)):
            for j in range(i + 1, len(setups)):
                s1 = setups[i]["param_indices"]
                s2 = setups[j]["param_indices"]
                if not s1 or not s2:
                    continue

                # Calcular deltas entre os dois setups
                for svm_key in s1:
                    if svm_key in s2:
                        diff = s2[svm_key] - s1[svm_key]
                        delta_name = svm_to_delta.get(svm_key)
                        if delta_name and diff != 0 and abs(diff) <= 5:
                            # Registrar como learning rule leve
                            try:
                                self.db.record_learning_rule(
                                    car_class=self._car_class or "unknown",
                                    track_id=track_id,
                                    problem="setup_comparison",
                                    solution=f"setup_{setups[j]['file_name']}",
                                    param=delta_name,
                                    delta=diff,
                                    reward=0.3,  # Reward moderado (não testado em pista)
                                    improvement_pct=0.0,
                                )
                            except Exception:
                                pass

    def get_knowledge_summary(self) -> dict:
        """
        Retorna um resumo da memória persistente da IA.
        """
        summary = {
            "library_setups": self.db.count_library_setups(),
            "total_samples": self.total_samples(),
            "active_memory": None,
        }

        if self._car_name and self._track_name:
            try:
                car_id = self.db.get_or_create_car(self._car_name, self._car_class)
                track_id = self.db.get_or_create_track(self._track_name)
                memory = self.db.load_car_track_memory(car_id, track_id)
                if memory:
                    summary["active_memory"] = {
                        "sessions": memory.get("total_sessions", 0),
                        "laps": memory.get("total_laps", 0),
                        "best_lap": memory.get("best_lap_time"),
                        "confidence": memory.get("memory_confidence", 0),
                    }
            except Exception:
                pass

        return summary

    # ─────────────────────────────────────────────────────
    # Transfer Learning — criação de modelo compartilhado
    # ─────────────────────────────────────────────────────

    def _try_create_shared_model(self, car_class: str):
        """
        Tenta criar/atualizar modelo compartilhado da classe de carro.
        Chamado periodicamente após treino — verifica se há modelos suficientes.
        """
        if not car_class:
            return
        try:
            safe_class = self.model_manager._sanitize(car_class)
            class_dir = self.model_manager.models_dir / safe_class
            if not class_dir.exists():
                return

            # Contar modelos .pth da mesma classe (excluindo _shared)
            model_files = []
            for car_dir in class_dir.iterdir():
                if car_dir.is_dir():
                    model_files.extend(list(car_dir.glob("*.pth")))

            if len(model_files) < 3:
                return  # Mínimo 3 modelos para criar um compartilhado

            # Carregar todos os modelos da classe
            models = []
            for mf in model_files:
                try:
                    m = self.model_manager._load_from_file(mf, self._current_level)
                    models.append(m)
                except Exception:
                    pass

            if len(models) >= 3:
                self.model_manager.create_shared_model(car_class, models)
                logger.info(
                    "Transfer Learning: modelo compartilhado '%s' criado "
                    "a partir de %d modelos.", car_class, len(models)
                )
        except Exception as e:
            logger.debug("Erro ao criar shared model: %s", e)

    # ─────────────────────────────────────────────────────
    # Destilação de Conhecimento (LLM → Autonomia)
    # ─────────────────────────────────────────────────────

    def start_knowledge_distillation(self, car_class: str = "",
                                     n_scenarios: int = 60,
                                     callback=None):
        """
        Inicia destilação de conhecimento: LLM ensina a rede neural.

        Gera cenários sintéticos, consulta o LLM para cada um,
        e treina a rede com as respostas. O objetivo é que a rede
        aprenda tudo que o LLM sabe e se torne autônoma.

        Args:
            car_class: Classe do carro (vazio = usar atual)
            n_scenarios: Número de cenários para gerar
            callback: Função(DistillationProgress) para atualizações
        """
        if not car_class:
            car_class = self._car_class or "hypercar"
        self.distiller.start_distillation(
            car_class=car_class,
            n_scenarios=n_scenarios,
            callback=callback,
        )

    def get_autonomy_status(self) -> dict:
        """
        Retorna status de autonomia da IA.

        Returns:
            Dict com score, is_autonomous, scenarios_trained,
            status_text, comparisons
        """
        metrics = self.distiller.autonomy
        return {
            "score": metrics.score,
            "is_autonomous": metrics.is_autonomous,
            "scenarios_trained": metrics.scenarios_trained,
            "comparisons": metrics.total_comparisons,
            "avg_error": metrics.avg_delta_error,
            "status_text": self.distiller.get_status_text(),
            "details": metrics.details,
        }

    # ─────────────────────────────────────────────────────
    # LLM Aprendizagem via Chat
    # ─────────────────────────────────────────────────────

    def _learn_from_llm_chat(self, adjustments: dict, confidence: float,
                              feedback: dict):
        """
        Aprende com ajustes sugeridos pelo LLM no chat conversacional.

        Quando o piloto descreve um problema no chat e o LLM responde
        com ajustes em JSON, esses ajustes são salvos como dados de
        treinamento para a rede neural.

        Isso permite que a IA aprenda MESMO SEM ESTAR PILOTANDO,
        só com perguntas e respostas no chat.
        """
        try:
            if not self._car_name or not self._track_name:
                logger.debug("LLM chat learn: sem carro/pista — ignorando.")
                return

            car_id = self.db.get_or_create_car(
                self._car_name, self._car_class or "hypercar"
            )
            track_id = self.db.get_or_create_track(self._track_name)
            session_id = getattr(self, '_current_session_id', None)

            if not session_id:
                logger.debug("LLM chat learn: sem sessão ativa — ignorando.")
                return

            from core.brain import LEVEL_OUTPUTS
            output_names = LEVEL_OUTPUTS.get(
                self._current_level, LEVEL_OUTPUTS["basic"]
            )

            # Construir input a partir do feedback do usuário
            # (usa último estado normalizado se disponível)
            if hasattr(self.normalizer, 'last_normalized') and self.normalizer.last_normalized is not None:
                input_vec = self.normalizer.last_normalized
            else:
                # Sem telemetria — criar vetor "neutro" com feedback embutido
                input_vec = np.zeros(49, dtype=np.float32)
                # Injetar feedback do chat nas posições corretas
                input_vec[33] = feedback.get("bias", 0)    # user_feedback_bias
                input_vec[34] = feedback.get("entry", 0)    # user_feedback_entry
                input_vec[35] = feedback.get("mid", 0)      # user_feedback_mid
                input_vec[36] = feedback.get("exit", 0)     # user_feedback_exit
                input_vec[37] = feedback.get("confidence", 0.7)  # user_confidence

            # Montar vetor de output
            output_vec = np.zeros(len(output_names), dtype=np.float32)
            matched = 0
            for i, name in enumerate(output_names):
                if name in adjustments:
                    output_vec[i] = adjustments[name]
                    matched += 1

            if matched == 0:
                return

            # Salvar como dado de treinamento
            # Peso menor (0.5) porque não tem telemetria real como base
            self.db.save_training_data(
                session_id=session_id,
                car_id=car_id,
                track_id=track_id,
                input_vec=input_vec,
                output_vec=output_vec,
                reward=confidence * 0.8,  # Ligeiramente menor que auto-análise
                weight=0.5,
            )
            self._cached_total_samples = None
            logger.info(
                "LLM Chat→Rede Neural: %d ajustes aprendidos "
                "(confiança=%.0f%%, nível=%s)",
                matched, confidence * 100, self._current_level,
            )
        except Exception as e:
            logger.debug("Erro learn_from_llm_chat: %s", e)

    # ─────────────────────────────────────────────────────
    # LLM Auto-aprendizagem
    # ─────────────────────────────────────────────────────

    def _llm_auto_analyze(self, feature_dict: dict, summary):
        """
        Consulta o LLM automaticamente para analisar a telemetria da volta
        e gerar insights que ALIMENTAM o treinamento da rede neural.

        Fluxo de aprendizagem:
        1. Envia telemetria ao LLM → recebe ajustes recomendados
        2. Converte ajustes do LLM em vetor de output da rede
        3. Salva como dado de treinamento (reward = confiança do LLM)
        4. Na próxima rodada de treino, a rede incorpora esse conhecimento

        Resultado: a rede neural APRENDE com cada resposta do LLM,
        e com o tempo passa a gerar sugestões similares sozinha,
        sem precisar consultar o LLM.
        """
        if not self.llm_advisor.enabled:
            return

        if not getattr(self, '_llm_auto_enabled', False):
            return

        # Auto-graduação: se IA já é autônoma, reduzir chamadas ao LLM
        # Score > 90% → consultar a cada 15 voltas (apenas verificação)
        # Score > 70% → consultar a cada 6 voltas (aprendendo menos)
        # Score < 70% → consultar a cada 3 voltas (aprendendo ativamente)
        autonomy = self.distiller.autonomy.score
        if autonomy >= 0.90:
            llm_interval = 15
        elif autonomy >= 0.70:
            llm_interval = 6
        else:
            llm_interval = 3

        # Consultar a cada N voltas para economizar créditos
        if summary.lap_number % llm_interval != 0:
            return

        car_class = self._car_class or "hypercar"

        # Capturar IDs atuais para uso no callback (thread-safe)
        car_id = self.db.get_or_create_car(
            summary.vehicle_name, summary.vehicle_class
        )
        track_id = self.db.get_or_create_track(summary.track_name)
        session_id = getattr(self, '_current_session_id', None)
        features_raw = summary.features if hasattr(summary, 'features') else None

        def _on_insight(insight):
            if not insight or not insight.adjustments:
                return
            logger.info(
                "LLM insight (conf=%.0f%%): %s",
                insight.confidence * 100,
                insight.explanation[:100],
            )

            # ═══════════════════════════════════════════
            # FEEDBACK LOOP: LLM → Rede Neural
            # ═══════════════════════════════════════════
            # Converter ajustes do LLM em dados de treinamento
            # para que a rede neural APRENDA com o LLM
            if (insight.confidence >= 0.4
                    and session_id is not None
                    and features_raw is not None):
                try:
                    from core.brain import LEVEL_OUTPUTS
                    output_names = LEVEL_OUTPUTS.get(
                        self._current_level,
                        LEVEL_OUTPUTS["basic"],
                    )

                    # Normalizar input (mesma normalização do treino)
                    input_vec = self.normalizer.normalize(features_raw)

                    # Montar vetor de output a partir dos ajustes do LLM
                    output_vec = np.zeros(len(output_names), dtype=np.float32)
                    matched = 0
                    for i, name in enumerate(output_names):
                        if name in insight.adjustments:
                            output_vec[i] = insight.adjustments[name]
                            matched += 1

                    # Só salva se o LLM sugeriu pelo menos 1 parâmetro válido
                    if matched > 0:
                        # Reward = confiança do LLM (0.4 a 1.0)
                        # Peso extra para diferenciar dados do LLM
                        reward = insight.confidence
                        weight = 0.7  # Peso menor que experiência real (1.0)

                        self.db.save_training_data(
                            session_id=session_id,
                            car_id=car_id,
                            track_id=track_id,
                            input_vec=input_vec,
                            output_vec=output_vec,
                            reward=reward,
                            weight=weight,
                        )
                        # Invalidar cache para refletir novos dados
                        self._cached_total_samples = None
                        logger.info(
                            "LLM→Rede Neural: %d ajustes salvos como treino "
                            "(reward=%.2f, weight=%.1f, nível=%s)",
                            matched, reward, weight, self._current_level,
                        )

                        # ── Tracking de Autonomia ──
                        # Comparar o que a NN teria predito vs o que
                        # o LLM sugeriu, para medir o progresso
                        try:
                            model = self.model_manager.get_model(
                                summary.vehicle_name,
                                summary.track_name,
                                car_class=car_class,
                                level=self._current_level,
                            )
                            input_t = torch.FloatTensor(
                                input_vec
                            ).unsqueeze(0)
                            nn_deltas = model.predict(input_t)
                            self.distiller.track_live_comparison(
                                nn_deltas, insight.adjustments,
                            )
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug("Erro ao salvar insight LLM como treino: %s", e)

            # ═══════════════════════════════════════════
            # Exibir sugestão na GUI
            # ═══════════════════════════════════════════
            if insight.confidence >= 0.5 and self._on_auto_suggestion_callback:
                display = {k: v for k, v in insight.adjustments.items() if v != 0}
                if display:
                    self._on_auto_suggestion_callback({
                        "deltas": insight.adjustments,
                        "display_deltas": display,
                        "explanation": (
                            f"🤖 **Análise LLM** (confiança {insight.confidence*100:.0f}%):\n\n"
                            f"{insight.explanation}\n\n"
                            f"_📚 {matched if 'matched' in dir() else '?'} ajustes "
                            f"incorporados ao treinamento da rede neural._"
                        ),
                        "warnings": insight.warnings,
                        "source": "llm",
                    })

        try:
            self.llm_advisor.analyze_telemetry(
                telemetry=feature_dict,
                car_class=car_class,
                callback=_on_insight,
            )
        except Exception as e:
            logger.debug("LLM auto-analyze error: %s", e)

    # ─────────────────────────────────────────────────────
    # Auto-suggest (sugestão autônoma)
    # ─────────────────────────────────────────────────────

    def _generate_auto_suggestion(self):
        """
        Gera sugestão automaticamente após N voltas.
        A IA decide sozinha com base na telemetria acumulada.
        """
        summary = self.telemetry.last_summary
        if not summary:
            return

        try:
            confidence = self.ai_confidence()

            # Escolher fonte com base na confiança
            if confidence >= 0.4:
                deltas, warnings = self.request_suggestion()
                source = "IA"
            else:
                deltas, warnings = self.request_heuristic_suggestion()
                source = "heurísticas"

            if not deltas:
                return

            # Gerar explicação inteligente
            feature_dict = self._features_to_dict(summary.features)
            explanation = self._build_auto_explanation(feature_dict, deltas, source)

            self._pending_auto_suggestion = {
                "deltas": deltas,
                "display_deltas": dict(self._last_display_deltas),
                "warnings": warnings,
                "explanation": explanation,
                "source": source,
                "lap": summary.lap_number,
                "confidence": confidence,
            }

            # Notificar GUI via callback
            if self._on_auto_suggestion_callback:
                self._on_auto_suggestion_callback(self._pending_auto_suggestion)

            logger.info(
                "Auto-sugestão gerada (volta %d, fonte=%s, %d ajustes)",
                summary.lap_number, source, len(deltas),
            )

        except Exception as e:
            logger.debug("Erro na auto-sugestão: %s", e)

    def _build_auto_explanation(self, tele: dict, deltas: dict,
                                source: str) -> str:
        """Constrói explicação em linguagem natural para a auto-sugestão."""
        parts = [f"📊 Análise automática após {len(self._lap_history)} voltas (via {source}):"]

        problems = self._detect_all_problems(tele)

        if "understeer" in problems:
            parts.append("🔄 Detectei understeer — ajustando balanço para mais rotação.")
        if "oversteer" in problems:
            parts.append("🔄 Detectei oversteer — ajustando para mais estabilidade traseira.")
        if "low_grip" in problems:
            parts.append("🏎️ Grip abaixo do ideal — otimizando pressões e aero.")
        if "rain" in problems:
            parts.append("🌧️ Condições de chuva — adaptando setup para pista molhada.")
        if any("bottoming" in p for p in problems):
            parts.append("⚠️ Risco de bottoming — ajustando ride height e molas.")
        if any("temp_spread" in p for p in problems):
            parts.append("🔥 Temperatura desbalanceada nos pneus — ajustando camber/pressão.")
        if any("pressure_high" in p for p in problems):
            parts.append("💨 Pressão dos pneus alta — reduzindo para melhor contato.")
        if any("pressure_low" in p for p in problems):
            parts.append("💨 Pressão dos pneus baixa — aumentando para melhor perfil.")

        if len(parts) == 1:
            parts.append("🔧 Otimização geral baseada na telemetria coletada.")

        n_changes = sum(1 for v in deltas.values() if v != 0)
        parts.append(f"\n💡 {n_changes} ajuste(s) sugerido(s). Veja o painel à direita.")

        return "\n".join(parts)

    def get_pending_auto_suggestion(self) -> dict | None:
        """Retorna a auto-sugestão pendente (chamado pela GUI)."""
        suggestion = self._pending_auto_suggestion
        self._pending_auto_suggestion = None
        return suggestion

    def set_auto_suggest_interval(self, laps: int):
        """Define o intervalo de auto-sugestão em voltas."""
        self._auto_suggest_after_laps = max(1, laps)

    def set_auto_suggest_enabled(self, enabled: bool):
        """Habilita/desabilita auto-sugestão."""
        self._auto_suggest_enabled = enabled

    # ─────────────────────────────────────────────────────
    # Pré-carga de dados de aprendizagem (Seed)
    # ─────────────────────────────────────────────────────

    def seed_knowledge_base(self) -> dict:
        """
        Injeta regras de conhecimento inicial no banco de dados
        baseadas no documento apredisagem.txt.

        Essas regras dão à IA uma base de partida para que
        ela não comece do zero absoluto. As regras cobrem
        cenários comuns para GT3, LMP2 e Hypercar.

        Returns:
            dict com 'rules_added' e 'rules_skipped'
        """
        rules_added = 0
        rules_skipped = 0

        # ── Regras universais (todas as classes) ──
        UNIVERSAL_RULES = [
            # Temperatura / Pressão de pneus
            ("temp_spread_fl", "Camber alto demais - desbalanceio térmico",
             "delta_camber_f", -1, 0.7, "dry"),
            ("temp_spread_fr", "Camber alto demais - desbalanceio térmico",
             "delta_camber_f", -1, 0.7, "dry"),
            ("temp_spread_rl", "Camber traseiro alto - desbalanceio térmico",
             "delta_camber_r", -1, 0.7, "dry"),
            ("temp_spread_rr", "Camber traseiro alto - desbalanceio térmico",
             "delta_camber_r", -1, 0.7, "dry"),
            ("pressure_high_fl", "Pressão alta - centro quente",
             "delta_pressure_f", -1, 0.75, "dry"),
            ("pressure_high_fr", "Pressão alta - centro quente",
             "delta_pressure_f", -1, 0.75, "dry"),
            ("pressure_high_rl", "Pressão alta traseira",
             "delta_pressure_r", -1, 0.75, "dry"),
            ("pressure_high_rr", "Pressão alta traseira",
             "delta_pressure_r", -1, 0.75, "dry"),
            ("pressure_low_fl", "Pressão baixa - bordas quentes",
             "delta_pressure_f", 1, 0.75, "dry"),
            ("pressure_low_fr", "Pressão baixa - bordas quentes",
             "delta_pressure_f", 1, 0.75, "dry"),
            ("pressure_low_rl", "Pressão baixa traseira",
             "delta_pressure_r", 1, 0.75, "dry"),
            ("pressure_low_rr", "Pressão baixa traseira",
             "delta_pressure_r", 1, 0.75, "dry"),

            # Understeer / Oversteer
            ("understeer", "Amaciar barra dianteira para rotação",
             "delta_arb_f", -1, 0.65, "dry"),
            ("understeer", "Aumentar asa traseira para mais downforce",
             "delta_rw", 1, 0.6, "dry"),
            ("understeer", "Endurecer barra traseira para rotação",
             "delta_arb_r", 1, 0.55, "dry"),
            ("oversteer", "Endurecer barra dianteira para estabilidade",
             "delta_arb_f", 1, 0.65, "dry"),
            ("oversteer", "Amaciar barra traseira para tração",
             "delta_arb_r", -1, 0.6, "dry"),
            ("oversteer", "Amaciar mola traseira para mais grip",
             "delta_spring_r", -1, 0.55, "dry"),

            # Bottoming
            ("bottoming_front", "Subir ride height dianteiro",
             "delta_ride_height_f", 1, 0.8, "dry"),
            ("bottoming_front", "Endurecer mola dianteira",
             "delta_spring_f", 1, 0.7, "dry"),
            ("bottoming_rear", "Subir ride height traseiro",
             "delta_ride_height_r", 1, 0.8, "dry"),
            ("bottoming_rear", "Endurecer mola traseira",
             "delta_spring_r", 1, 0.7, "dry"),

            # Low grip
            ("low_grip", "Ajustar pressão para janela ideal",
             "delta_pressure_f", -1, 0.5, "dry"),
            ("low_grip", "Aumentar camber para grip lateral",
             "delta_camber_f", 1, 0.5, "dry"),

            # Chuva
            ("rain", "Amaciar molas para chuva",
             "delta_spring_f", -1, 0.7, "wet"),
            ("rain", "Amaciar molas traseiras para chuva",
             "delta_spring_r", -1, 0.7, "wet"),
            ("rain", "Aumentar asa para mais downforce na chuva",
             "delta_rw", 2, 0.75, "wet"),
            ("rain", "Subir ride height para evitar aquaplanagem",
             "delta_ride_height_f", 1, 0.65, "wet"),
            ("rain", "Subir ride height traseiro para chuva",
             "delta_ride_height_r", 1, 0.65, "wet"),

            # Zebras / Saltos
            ("curb_instability", "Reduzir fast bump para absorver zebras",
             "delta_fast_bump_f", -1, 0.7, "dry"),
            ("curb_instability", "Reduzir fast bump traseiro",
             "delta_fast_bump_r", -1, 0.7, "dry"),

            # Frenagem
            ("brake_lock_front", "Mover bias para trás",
             "delta_rear_brake_bias", 1, 0.7, "dry"),
            ("brake_overheat", "Abrir dutos de freio",
             "delta_brake_duct_f", 1, 0.65, "dry"),
        ]

        # ── Regras específicas por classe ──
        CLASS_RULES = {
            "lmgt3": [
                # GT3: foco em mecânico + eletrônico
                ("understeer", "Reduzir TC para mais potência na saída",
                 "delta_tc_map", -1, 0.5, "dry"),
                ("oversteer", "Aumentar TC para estabilidade na saída",
                 "delta_tc_map", 1, 0.6, "dry"),
                ("brake_lock_front", "Aumentar ABS para margem no freio",
                 "delta_abs_map", 1, 0.6, "dry"),
                ("low_grip", "Endurecer molas para pistas lisas",
                 "delta_spring_f", 1, 0.45, "dry"),
                ("low_grip", "Amaciar molas para pistas onduladas",
                 "delta_spring_f", -1, 0.45, "dry"),
            ],
            "lmp2": [
                # LMP2: sem ABS/TC, foco em aero pura
                ("understeer", "Reduzir rake para equilíbrio aero",
                 "delta_ride_height_r", -1, 0.55, "dry"),
                ("oversteer", "Aumentar rake para estabilidade",
                 "delta_ride_height_r", 1, 0.55, "dry"),
                ("brake_lock_front", "Ajustar bias - sem ABS em LMP2",
                 "delta_rear_brake_bias", 2, 0.7, "dry"),
                ("understeer", "Aumentar asa traseira - LMP2 depende de aero",
                 "delta_rw", 2, 0.65, "dry"),
            ],
            "hypercar": [
                # Hypercar: híbrido + gestão de energia
                ("understeer", "Ajustar mapa de regeneração para equilíbrio",
                 "delta_rw", 1, 0.6, "dry"),
                ("oversteer", "Reduzir entrega do motor elétrico",
                 "delta_tc_map", 1, 0.55, "dry"),
                ("low_grip", "Ajustar rake para mais downforce",
                 "delta_ride_height_f", -1, 0.5, "dry"),
                ("low_grip", "Aumentar rake traseiro para downforce",
                 "delta_ride_height_r", 1, 0.5, "dry"),
            ],
        }

        try:
            # Injetar regras universais para todas as classes
            for car_class in ("lmgt3", "lmp2", "hypercar"):
                for rule in UNIVERSAL_RULES:
                    problem, solution, param, delta, reward, weather = rule
                    try:
                        self.db.record_learning_rule(
                            car_class=car_class,
                            track_id=None,
                            problem=problem,
                            solution=f"{param}:{delta:+d}",
                            param=param,
                            delta=delta,
                            reward=reward,
                            improvement_pct=0.0,
                            weather=weather,
                            session_type="seed",
                        )
                        rules_added += 1
                    except Exception:
                        rules_skipped += 1

                # Injetar regras específicas da classe
                class_rules = CLASS_RULES.get(car_class, [])
                for rule in class_rules:
                    problem, solution, param, delta, reward, weather = rule
                    try:
                        self.db.record_learning_rule(
                            car_class=car_class,
                            track_id=None,
                            problem=problem,
                            solution=f"{param}:{delta:+d}",
                            param=param,
                            delta=delta,
                            reward=reward,
                            improvement_pct=0.0,
                            weather=weather,
                            session_type="seed",
                        )
                        rules_added += 1
                    except Exception:
                        rules_skipped += 1

            self.db.conn.commit()
            logger.info(
                "Seed de conhecimento: %d regras adicionadas, %d ignoradas",
                rules_added, rules_skipped,
            )
        except Exception as e:
            logger.error("Erro no seed de conhecimento: %s", e)

        return {"rules_added": rules_added, "rules_skipped": rules_skipped}

    def get_knowledge_stats(self) -> dict:
        """Retorna estatísticas do conhecimento atual no banco."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learning_rules")
            total_rules = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM training_data WHERE is_valid=1")
            total_samples = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM learning_rules WHERE effectiveness_rate >= 0.6"
            )
            effective_rules = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT car_class) FROM learning_rules"
            )
            classes_covered = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM learning_rules WHERE session_type='seed'"
            )
            seed_rules = cursor.fetchone()[0]

            return {
                "total_rules": total_rules,
                "total_samples": total_samples,
                "effective_rules": effective_rules,
                "classes_covered": classes_covered,
                "seed_rules": seed_rules,
                "confidence": self.ai_confidence(),
            }
        except Exception:
            return {
                "total_rules": 0, "total_samples": 0,
                "effective_rules": 0, "classes_covered": 0,
                "seed_rules": 0, "confidence": 0.0,
            }

    # ─────────────────────────────────────────────────────
    # Exportação
    # ─────────────────────────────────────────────────────

    def export_data(self) -> Path:
        """Exporta dados do banco em formato JSON."""
        import json
        export_path = USER_DATA_DIR / "export.json"

        cursor = self.db.conn.cursor()

        data = {}
        for table in ("cars", "tracks", "sessions", "laps", "ai_suggestions"):
            cursor.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data[table] = [
                {col: (val if not isinstance(val, bytes) else "<blob>")
                 for col, val in zip(columns, row)}
                for row in rows
            ]

        export_path.write_text(
            json.dumps(data, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8"
        )
        return export_path

    # ─────────────────────────────────────────────────────
    # Session State — Persistência entre execuções
    # ─────────────────────────────────────────────────────

    def _save_session_state(self):
        """
        Salva estado completo da sessão atual para restaurar depois.
        Chamado: ao aplicar sugestão, ao carregar setup, ao encerrar.
        """
        if not self._car_name or not self._track_name:
            return
        try:
            car_id = self.db.get_or_create_car(
                self._car_name, self._car_class,
            )
            track_id = self.db.get_or_create_track(self._track_name)
            driver_id = self.db.get_or_create_driver(
                self.config.get("driver_name", "Piloto"),
            )

            state = {
                "driver_id": driver_id,
                "ai_level": self._current_level,
                "total_laps_driven": len(self._lap_history),
                "last_deltas": self._last_display_deltas or {},
                "last_display_deltas": self._last_display_deltas or {},
            }

            # Setup base
            if self._base_svm:
                state["base_svm_path"] = str(self._base_svm.filepath)
                state["base_svm_name"] = self._base_svm.filepath.name
                try:
                    state["base_svm_content"] = (
                        self._base_svm.filepath.read_text(
                            encoding="iso-8859-1",
                        )
                    )
                except Exception:
                    pass

            # Melhor volta
            valid_times = [
                h["time"] for h in self._lap_history if h.get("valid")
            ]
            if valid_times:
                state["best_lap_time"] = min(valid_times)

            # Weather (da última volta)
            if self._lap_history:
                last = self._lap_history[-1]
                features = last.get("features", {})
                state["weather"] = (
                    "wet" if features.get("raining", 0) > 0.3
                    else "dry"
                )
                state["air_temp_c"] = features.get("ambient_temp")
                state["track_temp_c"] = features.get("track_temp")

            self.db.save_session_state(car_id, track_id, state)
            logger.debug("Estado da sessão salvo para %s @ %s",
                         self._car_name, self._track_name)
        except Exception as e:
            logger.debug("Erro ao salvar estado da sessão: %s", e)

    def _restore_session_state(self, car_id: int, track_id: int) -> bool:
        """
        Restaura estado de sessão anterior para este carro×pista.
        Chamado na primeira volta quando o combo é detectado.

        Returns:
            True se restaurou dados, False caso contrário.
        """
        try:
            state = self.db.load_session_state(car_id, track_id)
            if not state:
                return False

            restored_items = []

            # Restaurar setup base se possível
            base_path = state.get("base_svm_path")
            if base_path and Path(base_path).exists() and not self._base_svm:
                try:
                    from data.svm_parser import parse_svm
                    self._base_svm = parse_svm(base_path)
                    restored_items.append(
                        f"📄 Setup base: {Path(base_path).name}"
                    )
                except Exception:
                    pass

            # Restaurar últimos deltas
            last_deltas = state.get("last_display_deltas")
            if last_deltas and isinstance(last_deltas, dict):
                self._last_display_deltas = last_deltas
                restored_items.append(
                    f"🔧 Últimos ajustes ({len(last_deltas)} params)"
                )

            # Restaurar nível
            saved_level = state.get("ai_level")
            if saved_level in ("basic", "intermediate", "advanced"):
                self._current_level = saved_level
                restored_items.append(
                    f"🎓 Nível: {saved_level.upper()}"
                )

            # Notificar GUI
            if restored_items and self._on_trend_alert_callback:
                best = state.get("best_lap_time")
                laps = state.get("total_laps_driven", 0)
                saved_at = state.get("saved_at", "")

                msg = (
                    f"♻️ **Sessão anterior restaurada!**\n"
                    f"Você já andou com este carro nesta pista "
                    f"({laps} voltas"
                )
                if best:
                    msg += f", melhor: {best:.3f}s"
                msg += f")\n"
                msg += "\n".join(f"  {item}" for item in restored_items)
                msg += (
                    "\n\nA IA continuará de onde parou — "
                    "sem precisar recomeçar do zero."
                )
                self._on_trend_alert_callback(msg)

            logger.info(
                "Sessão anterior restaurada: %d items recuperados",
                len(restored_items),
            )
            return bool(restored_items)

        except Exception as e:
            logger.debug("Erro ao restaurar sessão: %s", e)
            return False

    def _save_setup_snapshot_auto(self):
        """
        Salva snapshot do setup atual automaticamente no banco.
        Chamado quando: base é carregada, sugestões são aplicadas.
        """
        if not self._base_svm or not self._current_session_id:
            return
        try:
            svm = self._base_svm
            setup_data = {
                "source": "auto",
                "svm_filename": svm.filepath.name,
                "applied_at_lap": len(self._lap_history),
            }

            # Extrair parâmetros-chave do SVM
            from core.brain import DELTA_TO_SVM
            for delta_name, svm_keys in DELTA_TO_SVM.items():
                for svm_key in svm_keys:
                    param = svm.get_param(svm_key)
                    if param and param.adjustable:
                        # Mapear delta_name → coluna do snapshot
                        col = delta_name.replace("delta_", "")
                        if col in ("rw",):
                            setup_data["rw_setting"] = param.index
                        elif "spring" in col:
                            setup_data[col.replace("spring_", "spring_")] = param.index
                        elif "brake_press" in col:
                            setup_data["brake_pressure"] = param.index
                        break

            # Conteúdo raw
            try:
                setup_data["svm_raw_content"] = svm.filepath.read_text(
                    encoding="iso-8859-1",
                )
            except Exception:
                pass

            self.db.save_setup_snapshot(
                self._current_session_id, setup_data,
            )
            logger.debug("Snapshot do setup salvo.")
        except Exception as e:
            logger.debug("Erro ao salvar snapshot: %s", e)

    # ─────────────────────────────────────────────────────
    # Autonomia — AI self-learning knowledge
    # ─────────────────────────────────────────────────────

    def _ai_self_learn_knowledge(self, topic: str,
                                 category: str = "parameter"):
        """
        A IA aprende sozinha sobre um tópico consultando o LLM
        e salvando o resultado no banco de conhecimento.

        Chamado automaticamente quando a IA encontra um conceito
        que não conhece (ex: "TC Onboard", "ABS Map").
        """
        if not self.llm_advisor or not self.llm_advisor.enabled:
            return

        # Verificar se já sabe
        existing = self.db.get_knowledge(topic, category)
        if existing:
            return  # Já conhece

        question = (
            f"Explique de forma técnica e concisa para um engenheiro "
            f"de corrida o que é '{topic}' em carros de corrida "
            f"(Le Mans, GT3, Protótipos). "
            f"Como isso afeta o comportamento do carro? "
            f"Quais parâmetros de setup estão relacionados?"
        )

        def _on_response(answer: str):
            if not answer or len(answer) < 20:
                return
            try:
                # Inferir parâmetros relacionados
                related = []
                param_keywords = {
                    "tc": ["delta_tc_onboard", "delta_tc_map",
                           "delta_tc_power_cut"],
                    "abs": ["delta_abs_map"],
                    "traction": ["delta_tc_map", "delta_tc_onboard"],
                    "brake": ["delta_brake_press",
                              "delta_rear_brake_bias"],
                    "spring": ["delta_spring_f", "delta_spring_r"],
                    "camber": ["delta_camber_f", "delta_camber_r"],
                    "pressure": ["delta_pressure_f",
                                 "delta_pressure_r"],
                    "wing": ["delta_rw"],
                    "differential": ["delta_diff_preload"],
                    "ride height": ["delta_ride_height_f",
                                    "delta_ride_height_r"],
                }
                topic_lower = topic.lower()
                for kw, params in param_keywords.items():
                    if kw in topic_lower:
                        related.extend(params)

                self.db.save_knowledge(
                    topic=topic,
                    category=category,
                    answer=answer,
                    question=question,
                    source="llm",
                    confidence=0.7,
                    related_params=related if related else None,
                )
                logger.info(
                    "IA aprendeu sobre '%s' (knowledge base)", topic,
                )
            except Exception as e:
                logger.debug(
                    "Erro ao salvar conhecimento '%s': %s",
                    topic, e,
                )

        self.llm_advisor.chat(
            question, callback=_on_response,
        )

    def _seed_initial_knowledge(self):
        """
        Alimenta a base de conhecimento com conceitos fundamentais.
        Chamado uma vez quando a base está vazia.
        """
        if self.db.count_knowledge() > 0:
            return  # Já tem conhecimento

        if not self.llm_advisor or not self.llm_advisor.enabled:
            return

        topics = [
            ("tc_onboard", "parameter",
             "Controle de Tração (TC Onboard) — liga/desliga"),
            ("tc_map", "parameter",
             "Mapa de Controle de Tração (TC Map)"),
            ("tc_power_cut", "parameter",
             "Corte de Potência do TC (TC Power Cut)"),
            ("tc_slip_angle", "parameter",
             "Ângulo de Escorregamento do TC (TC Slip Angle)"),
            ("abs_map", "parameter",
             "Mapa do ABS (Anti-lock Braking System)"),
            ("understeer", "concept",
             "Subesterço (Understeer) em corrida"),
            ("oversteer", "concept",
             "Sobreesterço (Oversteer) em corrida"),
            ("tire_temperature", "concept",
             "Temperatura dos pneus em corrida"),
            ("brake_bias", "parameter",
             "Balanço de frenagem (Brake Bias)"),
            ("differential_preload", "parameter",
             "Pré-carga do Diferencial"),
            ("ride_height", "parameter",
             "Altura ao solo (Ride Height)"),
            ("rear_wing", "parameter",
             "Asa traseira (Rear Wing / Downforce)"),
        ]

        import threading

        def _learn_batch():
            import time
            for topic, cat, desc in topics:
                self._ai_self_learn_knowledge(topic, cat)
                time.sleep(2)  # Não sobrecarregar a API
            logger.info(
                "Base de conhecimento inicial populada "
                "(%d tópicos)", len(topics),
            )

        t = threading.Thread(target=_learn_batch, daemon=True)
        t.start()

    def get_knowledge_about(self, topic: str) -> str | None:
        """
        Consulta a base de conhecimento da IA sobre um tópico.
        Se não sabe, dispara aprendizagem autônoma.
        """
        results = self.db.get_knowledge(topic)
        if results:
            return results[0].get("answer")

        # Não sabe — aprender de forma assíncrona
        self._ai_self_learn_knowledge(topic)
        return None  # Ainda não sabe, mas vai aprender

    # ─────────────────────────────────────────────────────
    # Shutdown
    # ─────────────────────────────────────────────────────

    def shutdown(self):
        """Encerramento limpo de todos os módulos."""
        logger.info("Encerrando %s...", APP_NAME)

        # Salvar estado completo da sessão para restaurar depois
        self._save_session_state()

        # Salvar memória persistente da sessão atual
        if self._car_name and self._track_name:
            try:
                car_id = self.db.get_or_create_car(self._car_name, self._car_class)
                track_id = self.db.get_or_create_track(self._track_name)
                # Finalizar sessão no banco
                if self._current_session_id:
                    self.db.end_session(
                        self._current_session_id,
                        total_laps=len(self._lap_history),
                        best_lap=min((h["time"] for h in self._lap_history
                                      if h.get("valid")), default=None),
                    )
                logger.info("Memória da sessão salva para %s @ %s",
                            self._car_name, self._track_name)
            except Exception as e:
                logger.debug("Erro ao salvar memória da sessão: %s", e)

        # Parar telemetria
        if self.telemetry.is_running:
            self.telemetry.stop()

        # Parar Shared Memory
        if self._rf2info is not None:
            try:
                self._rf2info.stop()
            except Exception as e:
                logger.debug("Erro ao parar Shared Memory: %s", e)

        # Salvar normalizer
        try:
            norm_path = MODELS_DIR / "normalizer.npz"
            self.normalizer.save(str(norm_path))
        except Exception as e:
            logger.debug("Erro ao salvar normalizer: %s", e)

        # Salvar config
        try:
            self.config.save()
        except Exception as e:
            logger.debug("Erro ao salvar config: %s", e)

        # Fechar banco
        try:
            self.db.close()
        except Exception as e:
            logger.debug("Erro ao fechar DB: %s", e)

        logger.info("%s encerrado.", APP_NAME)


# ================================================================
# PONTO DE ENTRADA
# ================================================================

def main():
    """Função principal."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("%s v%s — Inicialização", APP_NAME, APP_VERSION)
    logger.info("=" * 60)

    # Criar engine
    engine = VirtualEngineer()

    # Carregar normalizer se existir
    norm_path = MODELS_DIR / "normalizer.npz"
    if norm_path.exists():
        try:
            engine.normalizer.load(str(norm_path))
            logger.info("Normalizer carregado.")
        except Exception:
            logger.debug("Normalizer não encontrado, iniciando do zero.")

    # Escanear setups disponíveis em background (não bloqueia a GUI)
    import threading
    def _startup_scan():
        try:
            result = engine.learn_from_all_setups()
            if result["scanned"] > 0:
                logger.info(
                    "Startup: %d setups escaneados de %d pistas",
                    result["scanned"], result["tracks"],
                )
        except Exception as e:
            logger.debug("Startup scan de setups falhou: %s", e)

    threading.Thread(target=_startup_scan, daemon=True).start()

    # Iniciar GUI
    from gui.app import MainApp
    app = MainApp(engine=engine)

    logger.info("GUI iniciada. Aguardando interação do usuário.")
    app.mainloop()


if __name__ == "__main__":
    main()

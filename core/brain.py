"""
brain.py — Rede Neural da IA (SetupNeuralNet).

Arquitetura MLP (Multi-Layer Perceptron) com PyTorch.
A rede recebe dados de telemetria normalizados e feedback do usuário,
e retorna deltas de ajuste para os parâmetros do setup.

Suporta 3 níveis de complexidade:
- Básico (8 outputs): Asa, Molas F/R, Camber F/R, Pressão pneus F/R, Freio
- Intermediário (20 outputs): + ARB, Toe, Ride Height, Amortecedores, Diff
- Avançado (45 outputs): Todos os parâmetros ajustáveis do .svm

A saída usa Tanh (valores entre -1 e +1) que depois são escalados
para o range real de cada parâmetro (em índices do .svm).
"""


from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("LMU_VE.brain")

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch não encontrado. A IA estará desativada e apenas heurísticas serão usadas.")
except Exception as e:
    TORCH_AVAILABLE = False
    logger.error(f"Erro ao carregar PyTorch: {e}. A IA estará desativada e apenas heurísticas serão usadas.")

# (camadas_ocultas, neurônios)
ARCHITECTURE_BY_LEVEL = {
    "basic":        [(128, 64)],           # Pequena — evita overfitting com 8 saídas
    "intermediate": [(256, 128, 64)],      # Atual — adequada para 20 saídas
    "advanced":     [(512, 256, 128, 64)], # Grande — necessária para 45 saídas
}

# Bonus de capacidade para carros híbridos complexos (Hypercar)
CLASS_CAPACITY_BONUS = {
    "hypercar": 1.5,  # 50% mais neurônios — mais variáveis de energia
    "lmp2":     1.0,
    "lmp3":     0.8,
    "gte":      1.0,
    "gt3":      0.9,
}


# ============================================================
# DEFINIÇÃO DOS INPUTS E OUTPUTS
# ============================================================

# Inputs da rede neural (49 features no total)
INPUT_FEATURES = [
    # Temperaturas dos pneus I/M/O × 4 rodas = 12
    "temp_fl_inner", "temp_fl_middle", "temp_fl_outer",
    "temp_fr_inner", "temp_fr_middle", "temp_fr_outer",
    "temp_rl_inner", "temp_rl_middle", "temp_rl_outer",
    "temp_rr_inner", "temp_rr_middle", "temp_rr_outer",
    # Pressões dos pneus × 4 = 4
    "pressure_fl", "pressure_fr", "pressure_rl", "pressure_rr",
    # Desgaste dos pneus × 4 = 4
    "wear_fl", "wear_fr", "wear_rl", "wear_rr",
    # Carga nos pneus × 4 = 4
    "load_fl", "load_fr", "load_rl", "load_rr",
    # Ride Height F/R = 2
    "ride_height_f", "ride_height_r",
    # Downforce F/R = 2
    "downforce_f", "downforce_r",
    # Dinâmica do veículo = 3
    "pitch", "roll", "heave",
    # Velocidade máxima na reta = 1
    "max_speed",
    # Combustível restante = 1
    "fuel",
    # Feedback do usuário = 5
    "user_feedback_bias",       # -1.0 understeer ... +1.0 oversteer
    "user_feedback_entry",      # Problema na entrada da curva (0 ou 1)
    "user_feedback_mid",        # Problema no meio da curva (0 ou 1)
    "user_feedback_exit",       # Problema na saída da curva (0 ou 1)
    "user_confidence",          # 0.0 a 1.0
    # Clima e condições da pista = 8
    "raining",                  # 0.0 seco ... 1.0 chuva forte
    "dark_cloud",               # 0.0 céu limpo ... 1.0 nuvens escuras
    "avg_path_wetness",         # 0.0 seco ... 1.0 encharcado
    "track_temp",               # Temperatura da pista (°C)
    "ambient_temp",             # Temperatura ambiente (°C)
    "wind_speed",               # Velocidade do vento (m/s)
    "grip_avg",                 # Grip médio das 4 rodas (0.0-1.0)
    "lateral_force_imbalance",  # Diferença de força lateral F-R (normalizada)
    # Sessão e contexto = 3
    "fuel_fraction",            # fuel / fuel_capacity (0.0-1.0) — peso do carro
    "session_type_race",        # 1.0 se corrida, 0.0 se practice/qualy
    "session_type_qualy",       # 1.0 se qualy, 0.0 caso contrário
]
NUM_INPUTS = len(INPUT_FEATURES)  # 49

# Outputs por nível de complexidade
# Cada output = delta de ajuste (será escalado para índice do .svm)
OUTPUT_BASIC = [
    "delta_rw",              # Asa traseira
    "delta_spring_f",        # Mola dianteira
    "delta_spring_r",        # Mola traseira
    "delta_camber_f",        # Camber dianteiro (F média)
    "delta_camber_r",        # Camber traseiro (R média)
    "delta_pressure_f",      # Pressão pneu dianteiro (F média)
    "delta_pressure_r",      # Pressão pneu traseiro (R média)
    "delta_brake_press",     # Pressão de freio
]

OUTPUT_INTERMEDIATE = OUTPUT_BASIC + [
    "delta_arb_f",           # Barra anti-rolagem dianteira
    "delta_arb_r",           # Barra anti-rolagem traseira
    "delta_toe_f",           # Toe dianteiro
    "delta_toe_r",           # Toe traseiro
    "delta_ride_height_f",   # Ride Height dianteiro
    "delta_ride_height_r",   # Ride Height traseiro
    "delta_slow_bump_f",     # Amortecedor bump lento diant.
    "delta_slow_bump_r",     # Amortecedor bump lento tras.
    "delta_slow_rebound_f",  # Amortecedor rebound lento diant.
    "delta_slow_rebound_r",  # Amortecedor rebound lento tras.
    "delta_diff_preload",    # Pré-carga do diferencial
    "delta_rear_brake_bias", # Distribuição de frenagem
]

OUTPUT_ADVANCED = OUTPUT_INTERMEDIATE + [
    # Camber per-roda (substituem os F/R médios no nível avançado)
    "delta_camber_fl", "delta_camber_fr",
    "delta_camber_rl", "delta_camber_rr",
    # Pressão per-roda
    "delta_pressure_fl", "delta_pressure_fr",
    "delta_pressure_rl", "delta_pressure_rr",
    # Fast Bump/Rebound
    "delta_fast_bump_f", "delta_fast_bump_r",
    "delta_fast_rebound_f", "delta_fast_rebound_r",
    # Brake Duct
    "delta_brake_duct_f", "delta_brake_duct_r",
    # Spring per-roda
    "delta_spring_fl", "delta_spring_fr",
    "delta_spring_rl", "delta_spring_rr",
    # Ride Height per-roda
    "delta_ride_height_fl", "delta_ride_height_fr",
    "delta_ride_height_rl", "delta_ride_height_rr",
    # TC/ABS
    "delta_tc_map", "delta_abs_map", "delta_tc_power_cut",
    "delta_tc_onboard", "delta_tc_slip_angle",
    # Radiator / Engine Mix / Virtual Energy / Regen
    "delta_radiator",
    "delta_engine_mix",
    "delta_virtual_energy",
    "delta_regen_map",
]

LEVEL_OUTPUTS = {
    "basic": OUTPUT_BASIC,
    "intermediate": OUTPUT_INTERMEDIATE,
    "advanced": OUTPUT_ADVANCED,
}

# Escala máxima de delta por parâmetro (em índices do .svm)
# A saída Tanh (-1 a +1) é multiplicada por essa escala
MAX_DELTA_SCALE = {
    "delta_rw": 3,
    "delta_spring_f": 3, "delta_spring_r": 3,
    "delta_camber_f": 5, "delta_camber_r": 5,
    "delta_pressure_f": 3, "delta_pressure_r": 3,
    "delta_brake_press": 3,
    "delta_arb_f": 3, "delta_arb_r": 3,
    "delta_toe_f": 2, "delta_toe_r": 2,
    "delta_ride_height_f": 3, "delta_ride_height_r": 3,
    "delta_slow_bump_f": 2, "delta_slow_bump_r": 2,
    "delta_slow_rebound_f": 2, "delta_slow_rebound_r": 2,
    "delta_diff_preload": 3,
    "delta_rear_brake_bias": 3,
    "delta_camber_fl": 5, "delta_camber_fr": 5,
    "delta_camber_rl": 5, "delta_camber_rr": 5,
    "delta_pressure_fl": 3, "delta_pressure_fr": 3,
    "delta_pressure_rl": 3, "delta_pressure_rr": 3,
    "delta_fast_bump_f": 2, "delta_fast_bump_r": 2,
    "delta_fast_rebound_f": 2, "delta_fast_rebound_r": 2,
    "delta_brake_duct_f": 2, "delta_brake_duct_r": 2,
    "delta_spring_fl": 3, "delta_spring_fr": 3,
    "delta_spring_rl": 3, "delta_spring_rr": 3,
    "delta_ride_height_fl": 3, "delta_ride_height_fr": 3,
    "delta_ride_height_rl": 3, "delta_ride_height_rr": 3,
    "delta_tc_map": 2, "delta_abs_map": 2, "delta_tc_power_cut": 2,
    "delta_tc_onboard": 1, "delta_tc_slip_angle": 2,
    "delta_radiator": 2,
    "delta_engine_mix": 2,
    "delta_virtual_energy": 3,
    "delta_regen_map": 2,
}

# ============================================================
# MAPEAMENTO: delta da IA → chave real do .svm
# ============================================================
# Conecta os nomes de output da rede neural às chaves do SVMFile
# (formato SECAO.NomeSetting usado pelo svm_parser).
#
# Parâmetros "médios" (ex: delta_camber_f) são expandidos
# para L/R automaticamente pelo método deltas_to_svm().
# Parâmetros per-roda (ex: delta_camber_fl) mapeiam direto.

DELTA_TO_SVM = {
    # ── Aerodinâmica ──
    "delta_rw":               ["REARWING.RWSetting"],

    # ── Molas (média F/R → expande para L/R) ──
    "delta_spring_f":         ["FRONTLEFT.SpringSetting", "FRONTRIGHT.SpringSetting"],
    "delta_spring_r":         ["REARLEFT.SpringSetting", "REARRIGHT.SpringSetting"],

    # ── Camber (média F/R → expande para L/R) ──
    "delta_camber_f":         ["FRONTLEFT.CamberSetting", "FRONTRIGHT.CamberSetting"],
    "delta_camber_r":         ["REARLEFT.CamberSetting", "REARRIGHT.CamberSetting"],

    # ── Pressão dos pneus (média F/R → expande para L/R) ──
    "delta_pressure_f":       ["FRONTLEFT.PressureSetting", "FRONTRIGHT.PressureSetting"],
    "delta_pressure_r":       ["REARLEFT.PressureSetting", "REARRIGHT.PressureSetting"],

    # ── Freio ──
    "delta_brake_press":      ["CONTROLS.BrakePressureSetting"],

    # ── Barra anti-rolagem ──
    "delta_arb_f":            ["SUSPENSION.FrontAntiSwaySetting"],
    "delta_arb_r":            ["SUSPENSION.RearAntiSwaySetting"],

    # ── Toe ──
    "delta_toe_f":            ["SUSPENSION.FrontToeInSetting"],
    "delta_toe_r":            ["SUSPENSION.RearToeInSetting"],

    # ── Ride Height (média F/R → expande para L/R) ──
    "delta_ride_height_f":    ["FRONTLEFT.RideHeightSetting", "FRONTRIGHT.RideHeightSetting"],
    "delta_ride_height_r":    ["REARLEFT.RideHeightSetting", "REARRIGHT.RideHeightSetting"],

    # ── Amortecedores slow bump/rebound (média F/R) ──
    "delta_slow_bump_f":      ["FRONTLEFT.SlowBumpSetting", "FRONTRIGHT.SlowBumpSetting"],
    "delta_slow_bump_r":      ["REARLEFT.SlowBumpSetting", "REARRIGHT.SlowBumpSetting"],
    "delta_slow_rebound_f":   ["FRONTLEFT.SlowReboundSetting", "FRONTRIGHT.SlowReboundSetting"],
    "delta_slow_rebound_r":   ["REARLEFT.SlowReboundSetting", "REARRIGHT.SlowReboundSetting"],

    # ── Diferencial ──
    "delta_diff_preload":     ["DRIVELINE.DiffPreloadSetting"],

    # ── Balanço de freio ──
    "delta_rear_brake_bias":  ["CONTROLS.RearBrakeSetting"],

    # ── Per-roda: Camber ──
    "delta_camber_fl":        ["FRONTLEFT.CamberSetting"],
    "delta_camber_fr":        ["FRONTRIGHT.CamberSetting"],
    "delta_camber_rl":        ["REARLEFT.CamberSetting"],
    "delta_camber_rr":        ["REARRIGHT.CamberSetting"],

    # ── Per-roda: Pressão ──
    "delta_pressure_fl":      ["FRONTLEFT.PressureSetting"],
    "delta_pressure_fr":      ["FRONTRIGHT.PressureSetting"],
    "delta_pressure_rl":      ["REARLEFT.PressureSetting"],
    "delta_pressure_rr":      ["REARRIGHT.PressureSetting"],

    # ── Fast Bump/Rebound ──
    "delta_fast_bump_f":      ["FRONTLEFT.FastBumpSetting", "FRONTRIGHT.FastBumpSetting"],
    "delta_fast_bump_r":      ["REARLEFT.FastBumpSetting", "REARRIGHT.FastBumpSetting"],
    "delta_fast_rebound_f":   ["FRONTLEFT.FastReboundSetting", "FRONTRIGHT.FastReboundSetting"],
    "delta_fast_rebound_r":   ["REARLEFT.FastReboundSetting", "REARRIGHT.FastReboundSetting"],

    # ── Brake Duct ──
    "delta_brake_duct_f":     ["BODYAERO.FrontBrakeDuctSetting"],
    "delta_brake_duct_r":     ["BODYAERO.RearBrakeDuctSetting"],

    # ── Per-roda: Molas ──
    "delta_spring_fl":        ["FRONTLEFT.SpringSetting"],
    "delta_spring_fr":        ["FRONTRIGHT.SpringSetting"],
    "delta_spring_rl":        ["REARLEFT.SpringSetting"],
    "delta_spring_rr":        ["REARRIGHT.SpringSetting"],

    # ── Per-roda: Ride Height ──
    "delta_ride_height_fl":   ["FRONTLEFT.RideHeightSetting"],
    "delta_ride_height_fr":   ["FRONTRIGHT.RideHeightSetting"],
    "delta_ride_height_rl":   ["REARLEFT.RideHeightSetting"],
    "delta_ride_height_rr":   ["REARRIGHT.RideHeightSetting"],

    # ── TC / ABS ──
    "delta_tc_map":           ["CONTROLS.TractionControlMapSetting"],
    "delta_abs_map":          ["CONTROLS.AntilockBrakeSystemMapSetting"],
    "delta_tc_power_cut":     ["CONTROLS.TCPowerCutMapSetting"],
    "delta_tc_onboard":       ["CONTROLS.TCSetting"],
    "delta_tc_slip_angle":    ["CONTROLS.TCSlipAngleMapSetting"],

    # ── Radiator / Engine Mix ──
    "delta_radiator":         ["BODYAERO.WaterRadiatorSetting"],
    "delta_engine_mix":       ["GENERAL.EngineMixtureSetting"],

    # ── Hybrid/Energy (Hypercar) ──
    "delta_virtual_energy":   ["GENERAL.VirtualEnergySetting"],
    "delta_regen_map":        ["CONTROLS.RegenerationMapSetting"],
}


def deltas_to_svm(ai_deltas: dict[str, int]) -> dict[str, int]:
    """
    Converte deltas da IA (nomes internos) para chaves do .svm.

    Ex: {"delta_camber_f": -1} → {"FRONTLEFT.CamberSetting": -1,
                                    "FRONTRIGHT.CamberSetting": -1}

    Args:
        ai_deltas: Dict {nome_delta_ia: valor_inteiro}

    Returns:
        Dict {SECAO.NomeSetting: delta_inteiro} pronto para apply_deltas()
    """
    svm_deltas = {}
    for delta_name, value in ai_deltas.items():
        if value == 0:
            continue
        svm_keys = DELTA_TO_SVM.get(delta_name)
        if not svm_keys:
            logger.warning("Delta sem mapeamento SVM: %s", delta_name)
            continue
        for svm_key in svm_keys:
            # Se já tem um delta para essa chave, soma (múltiplos outputs
            # podem afetar o mesmo parâmetro no nível avançado)
            svm_deltas[svm_key] = svm_deltas.get(svm_key, 0) + value
    return svm_deltas


if TORCH_AVAILABLE:
    class SetupNeuralNet(nn.Module):
        """
        Rede Neural MLP para sugestão de ajustes de setup.

        Arquitetura:
            Input (49) → Linear(256) + BN + ReLU + Dropout(0.2)
                       → Linear(128) + BN + ReLU + Dropout(0.2)
                       → Linear(64)  + ReLU
                       → Linear(N_outputs) + Tanh

        A saída Tanh garante valores entre -1 e +1.
        Esses valores são multiplicados pela escala máxima de
        cada parâmetro e arredondados para índices inteiros do .svm.
        """

        def __init__(self, level: str = "basic", car_class: str = "gt3"):
            """
            Inicializa a rede neural.

            Args:
                level: Nível de complexidade ("basic", "intermediate", "advanced")
            """
            super().__init__()
            self.level = level
            self.car_class = car_class
            self.output_names = LEVEL_OUTPUTS.get(level, OUTPUT_BASIC)
            num_outputs = len(self.output_names)

            # Determinar arquitetura com base no nível e classe
            hidden_layers_config = ARCHITECTURE_BY_LEVEL.get(level, ARCHITECTURE_BY_LEVEL["intermediate"])
            capacity_bonus = CLASS_CAPACITY_BONUS.get(car_class.lower(), 1.0)

            layers = []
            input_size = NUM_INPUTS
            for i, (out_features, _) in enumerate(hidden_layers_config):
                current_out_features = int(out_features * capacity_bonus)
                layers.append(nn.Linear(input_size, current_out_features))
                layers.append(nn.BatchNorm1d(current_out_features))
                layers.append(nn.ReLU())
                if i < len(hidden_layers_config) - 1: # Apply dropout to all but the last hidden layer
                    layers.append(nn.Dropout(0.2))
                input_size = current_out_features
            
            self.hidden_layers = nn.Sequential(*layers)

            # Camada de saída: com Tanh
            self.output_layer = nn.Sequential(
                nn.Linear(input_size, num_outputs),
                nn.Tanh(),
            )

            # Camadas da rede

            # Inicialização Xavier para convergência mais rápida
            self._init_weights()

        def _init_weights(self):
            """Inicialização Xavier dos pesos para melhor convergência."""
            for module in self.modules():
                if isinstance(module, nn.Linear):
                    nn.init.xavier_uniform_(module.weight)
                    if module.bias is not None:
                        nn.init.zeros_(module.bias)
else:
    class SetupNeuralNet:
        def __init__(self, *args, **kwargs):
            pass
        def train(self):
            pass
        def eval(self):
            pass
        def parameters(self):
            return []


# ============================================================
# FILTRO DE OUTPUTS POR CLASSE DE CARRO
# ============================================================
# Carros que NÃO possuem determinados sistemas — deltas zerados.

CLASS_UNAVAILABLE_OUTPUTS = {
    "lmp2": [
        "delta_abs_map",          # LMP2 não tem ABS
        "delta_tc_map",           # LMP2 não tem TC (maioria)
        "delta_tc_power_cut",
        "delta_tc_onboard",
        "delta_tc_slip_angle",
        "delta_virtual_energy",   # Não é híbrido
        "delta_regen_map",
    ],
    "lmgt3": [
        "delta_virtual_energy",   # GT3 não é híbrido
        "delta_regen_map",
    ],
    # hypercar: tem tudo
}


def filter_deltas_by_class(deltas: dict[str, int],
                           car_class: str) -> dict[str, int]:
    """
    Remove deltas de parâmetros que não existem na classe do carro.
    Ex: LMP2 não tem ABS → delta_abs_map é removido.
    """
    unavailable = CLASS_UNAVAILABLE_OUTPUTS.get(car_class, [])
    if not unavailable:
        return deltas
    filtered = {k: v for k, v in deltas.items() if k not in unavailable}
    removed = [k for k in deltas if k in unavailable and deltas[k] != 0]
    if removed:
        logger.debug("Filtrados por classe '%s': %s", car_class, removed)
    return filtered


# ============================================================
# GERENCIADOR DE MODELOS (salvar/carregar/Transfer Learning)
# ============================================================
if TORCH_AVAILABLE:
    class ModelManager:
        """
        Gerencia modelos da IA por combo carro × pista.
        Suporta salvar, carregar e Transfer Learning.
        """

        def __init__(self, models_dir):
            self.models_dir = Path(models_dir)

        def _model_path(self, car_class: str, car_name: str,
                        track_name: str) -> Path:
            """Gera o caminho do arquivo .pth para um combo."""
            # Sanitizar nomes para uso como pasta/arquivo
            safe_class = self._sanitize(car_class)
            safe_car = self._sanitize(car_name)
            safe_track = self._sanitize(track_name)
            return self.models_dir / safe_class / safe_car / f"{safe_track}.pth"

        def _shared_model_path(self, car_class: str) -> Path:
            """Caminho do modelo base compartilhado da categoria."""
            safe_class = self._sanitize(car_class)
            # ...restante do código...
else:
    class ModelManager:
        """
        Dummy ModelManager para ambientes sem PyTorch.
        """
        def __init__(self, models_dir):
            self.models_dir = Path(models_dir)
        def __getattr__(self, name):
            def dummy(*args, **kwargs):
                logger.warning(f"Método '{name}' chamado em ModelManager dummy (PyTorch não disponível). Nenhuma ação será executada.")
                return None
            return dummy

    @staticmethod
    def _sanitize(name: str) -> str:
        """Sanitiza um nome para uso como nome de pasta/arquivo."""
        import re
        # Remove caracteres especiais, mantém alfanuméricos, espaços e hifens
        clean = re.sub(r"[^\w\s\-]", "", name)
        # Substitui espaços por underscore
        clean = re.sub(r"\s+", "_", clean.strip())
        return clean.lower() if clean else "unknown"

    def save_model(self, model: SetupNeuralNet,
                   car_class: str, car_name: str,
                   track_name: str, metadata: dict | None = None):
        """
        Salva o modelo treinado no disco.

        Args:
            model: Rede neural treinada
            car_class: Classe do carro (ex: "hypercar")
            car_name: Nome do carro (ex: "Toyota GR010")
            track_name: Nome da pista (ex: "le_mans_24h")
            metadata: Dados extras (epoch, reward, etc.)
        """
        path = self._model_path(car_class, car_name, track_name)
        path.parent.mkdir(parents=True, exist_ok=True)

        save_data = {
            "model_state_dict": model.state_dict(),
            "level": model.level,
            "car_class": car_class,
            "car_name": car_name,
            "track_name": track_name,
        }
        if metadata:
            save_data["metadata"] = metadata

        torch.save(save_data, path)
        logger.info("Modelo salvo: %s", path)

    def load_model(self, car_class: str, car_name: str,
                   track_name: str, level: str = "basic") -> SetupNeuralNet | None:
        """
        Carrega um modelo do disco.

        Tenta na ordem:
        1. Modelo específico do combo carro × pista
        2. Modelo base da categoria (Transfer Learning)
        3. None (sem modelo — usar só heurísticas)
        """
        # 1. Tentar modelo específico
        path = self._model_path(car_class, car_name, track_name)
        if path.exists():
            return self._load_from_file(path, level)

        # 2. Tentar Transfer Learning da categoria
        shared_path = self._shared_model_path(car_class)
        if shared_path.exists():
            logger.info("Transfer Learning: usando modelo base de '%s'", car_class)
            return self._load_from_file(shared_path, level)

        # 3. Sem modelo disponível
        logger.info("Nenhum modelo encontrado para %s @ %s. Usando heurísticas.",
                     car_name, track_name)
        return None

    def get_model(self, car_name: str, track_name: str,
                  car_class: str = "", level: str = "basic") -> SetupNeuralNet:
        """
        Obtém ou cria um modelo para o combo carro×pista.
        Se não encontrar modelo salvo, cria um novo.

        Returns:
            SetupNeuralNet (nunca None)
        """
        model = self.load_model(car_class, car_name, track_name, level)
        if model is None:
            model = SetupNeuralNet(level=level)
        return model

    def _load_from_file(self, path: Path, level: str) -> SetupNeuralNet:
        """Carrega modelo de um arquivo .pth."""
        save_data = torch.load(path, map_location="cpu", weights_only=True)
        saved_level = save_data.get("level", level)

        # Usar o nível salvo se compatível, senão usar o solicitado
        model = SetupNeuralNet(level=saved_level)
        try:
            model.load_state_dict(save_data["model_state_dict"])
        except RuntimeError:
            # Se a arquitetura mudou (nível diferente), carrega parcialmente
            model = SetupNeuralNet(level=level)
            model.load_state_dict(save_data["model_state_dict"], strict=False)
            logger.warning("Modelo carregado parcialmente (mudança de nível)")

        model.eval()
        logger.info("Modelo carregado: %s", path)
        return model

    def create_shared_model(self, car_class: str,
                            models: list[SetupNeuralNet]) -> SetupNeuralNet:
        """
        Cria um modelo base compartilhado a partir da média ponderada
        de todos os modelos da mesma categoria.
        Usado para Transfer Learning quando um carro novo não tem dados.

        Args:
            car_class: Classe do carro (ex: "hypercar")
            models: Lista de modelos treinados da mesma categoria

        Returns:
            Modelo com pesos médios
        """
        if not models:
            return SetupNeuralNet(level="basic")

        # Média dos pesos de todos os modelos
        avg_state = {}
        for key in models[0].state_dict():
            tensors = [m.state_dict()[key].float() for m in models
                       if key in m.state_dict()]
            if tensors:
                avg_state[key] = torch.stack(tensors).mean(dim=0)

        base_model = SetupNeuralNet(level=models[0].level)
        base_model.load_state_dict(avg_state, strict=False)

        # Salvar
        path = self._shared_model_path(car_class)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": base_model.state_dict(),
            "level": base_model.level,
            "car_class": car_class,
            "source": "transfer_learning_average",
        }, path)

        logger.info("Modelo base '%s' criado a partir de %d modelos",
                     car_class, len(models))
        return base_model

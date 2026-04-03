"""
heuristics.py — Regras determinísticas de engenharia veicular.

São regras baseadas em física e engenharia que funcionam como
"fallback" enquanto a IA não tem dados suficientes para convergir.

As heurísticas dão valor IMEDIATO ao usuário — mesmo sem nenhum
dado de treinamento, o sistema já consegue sugerir ajustes lógicos
baseados na telemetria.

As regras são adaptadas POR CATEGORIA de carro (Hypercar vs GT3
têm características radicalmente diferentes).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("LMU_VE.heuristics")


@dataclass
class HeuristicSuggestion:
    """Uma sugestão gerada por regra heurística."""
    param_name: str          # Ex: "delta_camber_f"
    delta: int               # Delta em índices do .svm
    rule_name: str           # Nome da regra que disparou
    condition: str           # Condição que ativou a regra
    explanation: str         # Explicação em português
    priority: int = 5        # 1 = mais importante, 10 = menos
    category: str = "other"  # Categoria hierárquica do ajuste


# ============================================================
# HIERARQUIA DE AJUSTE (conforme apredisagem.txt)
# Passo 1: Aerodinâmica (asa, ride height, rake)
# Passo 2: Mecânico (ARB, molas)
# Passo 3: Amortecedores (slow bump/rebound, fast bump)
# Passo 4: Eletrônico (TC, ABS, virtual energy, engine mix)
# Passo 5: Ajuste fino (pressão, camber, toe)
# ============================================================
ADJUSTMENT_HIERARCHY = {
    "aero": {
        "order": 1,
        "label": "Aerodinâmica",
        "params": [
            "delta_rw", "delta_ride_height_f", "delta_ride_height_r",
            "delta_ride_height_fl", "delta_ride_height_fr",
            "delta_ride_height_rl", "delta_ride_height_rr",
            "delta_brake_duct_f", "delta_brake_duct_r",
            "delta_radiator",
        ],
    },
    "mechanical": {
        "order": 2,
        "label": "Mecânico",
        "params": [
            "delta_arb_f", "delta_arb_r",
            "delta_spring_f", "delta_spring_r",
            "delta_spring_fl", "delta_spring_fr",
            "delta_spring_rl", "delta_spring_rr",
            "delta_diff_preload",
        ],
    },
    "dampers": {
        "order": 3,
        "label": "Amortecedores",
        "params": [
            "delta_slow_bump_f", "delta_slow_bump_r",
            "delta_slow_rebound_f", "delta_slow_rebound_r",
            "delta_fast_bump_f", "delta_fast_bump_r",
            "delta_fast_rebound_f", "delta_fast_rebound_r",
        ],
    },
    "electronics": {
        "order": 4,
        "label": "Eletrônico",
        "params": [
            "delta_tc_map", "delta_abs_map", "delta_tc_power_cut",
            "delta_tc_onboard", "delta_tc_slip_angle",
            "delta_virtual_energy", "delta_regen_map",
            "delta_engine_mix",
        ],
    },
    "fine_tune": {
        "order": 5,
        "label": "Ajuste fino",
        "params": [
            "delta_camber_f", "delta_camber_r",
            "delta_camber_fl", "delta_camber_fr",
            "delta_camber_rl", "delta_camber_rr",
            "delta_pressure_f", "delta_pressure_r",
            "delta_pressure_fl", "delta_pressure_fr",
            "delta_pressure_rl", "delta_pressure_rr",
            "delta_toe_f", "delta_toe_r",
            "delta_brake_press", "delta_rear_brake_bias",
        ],
    },
}

# Mapa reverso: param_name → categoria
_PARAM_TO_CATEGORY = {}
for _cat, _info in ADJUSTMENT_HIERARCHY.items():
    for _p in _info["params"]:
        _PARAM_TO_CATEGORY[_p] = _cat


def get_param_category(param_name: str) -> str:
    """Retorna a categoria hierárquica de um parâmetro."""
    return _PARAM_TO_CATEGORY.get(param_name, "other")


def get_category_order(category: str) -> int:
    """Retorna a ordem de prioridade da categoria."""
    return ADJUSTMENT_HIERARCHY.get(category, {}).get("order", 99)


# ============================================================
# MODO QUALY vs RACE
# Em Qualy: pouco fuel, radiador fechado, camber agressivo, mais asa
# Em Race: mais fuel, radiador aberto, mais conservador
# ============================================================
SESSION_MODIFIERS = {
    "qualy": {
        "delta_radiator": -1,         # Fechar radiador = menos drag = mais velocidade
        "delta_engine_mix": +1,       # Mix mais potente
        "delta_rw": -1,               # Menos asa = menos drag (se pista rápida)
        "delta_camber_f": -1,         # Camber mais agressivo
        "delta_camber_r": -1,
    },
    "race": {
        "delta_radiator": +1,         # Abrir radiador = melhor refrigeração
        "delta_engine_mix": -1,       # Mix conservador
        "delta_brake_duct_f": +1,     # Mais refrigeração de freio
    },
}


# ============================================================
# CONFIGURAÇÕES POR CATEGORIA DE CARRO
# ============================================================
CLASS_CONFIG = {
    "hypercar": {
        "ride_height_sensitivity": "high",
        "camber_range_front": (-4.0, -1.5),
        "camber_range_rear": (-3.0, -0.5),
        "tire_pressure_target_kpa": (130, 145),
        "temp_target_c": (85, 100),             # Temperatura alvo dos pneus
        "temp_spread_max_c": 10,                # Spread I-M-O máximo aceitável
        "brake_temp_max_c": 700,                # Temperatura máxima dos freios
        "aero_balance_critical": True,
        "has_regen": True,
    },
    "lmp2": {
        "ride_height_sensitivity": "high",
        "camber_range_front": (-3.5, -1.0),
        "camber_range_rear": (-2.5, -0.5),
        "tire_pressure_target_kpa": (135, 150),
        "temp_target_c": (85, 105),
        "temp_spread_max_c": 12,
        "brake_temp_max_c": 750,
        "aero_balance_critical": True,
        "has_regen": False,
        "has_tc": False,
        "has_abs": False,
    },
    "lmgt3": {
        "ride_height_sensitivity": "medium",
        "camber_range_front": (-3.0, -0.5),
        "camber_range_rear": (-2.5, 0.0),
        "tire_pressure_target_kpa": (155, 175),
        "temp_target_c": (80, 100),
        "temp_spread_max_c": 15,
        "brake_temp_max_c": 800,
        "aero_balance_critical": False,
        "has_regen": False,
        "has_tc": True,
        "has_abs": True,
    },
}


def analyze_telemetry(telemetry: dict, car_class: str = "hypercar",
                      level: str = "advanced") -> list[HeuristicSuggestion]:
    """
    Analisa dados de telemetria e retorna sugestões heurísticas.

    Args:
        telemetry: Dict com dados médios da(s) última(s) volta(s)
        car_class: Classe normalizada do carro
        level: Nível do piloto ("basic", "intermediate", "advanced")

    Returns:
        Lista de sugestões ordenadas por prioridade, filtradas por nível
    """
    config = CLASS_CONFIG.get(car_class, CLASS_CONFIG["hypercar"])
    suggestions: list[HeuristicSuggestion] = []

    # ============================================================
    # REGRA 1: CAMBER — Temperatura Inner vs Outer
    # Se o pneu está muito mais quente por dentro (Inner) que por fora,
    # significa que tem camber negativo DEMAIS. O pneu está apoiando
    # mais no lado interno. Reduzir camber negativo (valor menos negativo).
    # ============================================================
    _check_camber(telemetry, config, suggestions)

    # ============================================================
    # REGRA 2: PRESSÃO DOS PNEUS — Temperatura Middle
    # Se o Middle está mais quente que Inner e Outer, a pressão
    # está ALTA demais (pneu abaulado no centro). Reduzir pressão.
    # Se Middle está mais frio, pressão está BAIXA (pneu afundado).
    # ============================================================
    _check_tire_pressure(telemetry, config, suggestions)

    # ============================================================
    # REGRA 3: ASA TRASEIRA — Temperatura traseira vs dianteira
    # Se os pneus traseiros estão sistematicamente mais quentes,
    # o eixo traseiro está sobrecarregado. Aumentar asa traseira
    # transfere carga aerodinâmica para trás, aliviando os pneus.
    # ============================================================
    _check_rear_wing(telemetry, config, suggestions)

    # ============================================================
    # REGRA 4: MOLAS — Ride Height e Pitch
    # Se o ride height dianteiro está muito baixo, o carro pode estar
    # batendo no chão (bottoming). Endurecer mola dianteira.
    # ============================================================
    _check_springs(telemetry, config, suggestions)

    # ============================================================
    # REGRA 5: FREIOS — Temperatura excessiva
    # Se algum freio está acima do limite, abrir duto de freio
    # ou ajustar distribuição de frenagem.
    # ============================================================
    _check_brakes(telemetry, config, suggestions)

    # ============================================================
    # REGRA 6: FEEDBACK DO USUÁRIO — Understeer/Oversteer
    # Se o piloto reporta understeer, ajustar para mais rotação.
    # Se oversteer, ajustar para mais estabilidade.
    # ============================================================
    _check_user_feedback(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7: CLIMA — Chuva e umidade da pista
    # Se está chovendo ou pista molhada, ajustar pressão,
    # aerodinâmica e suspensão para mais grip mecânico.
    # ============================================================
    _check_weather(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7B: JANELA DE TEMPERATURA DOS PNEUS
    # Se a temperatura GERAL do pneu está fora da janela ideal
    # (alvo definido por classe), ajustar pressão/camber.
    # ============================================================
    _check_tire_temp_window(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7C: RAKE (Diferença ride height F vs R)
    # Rake = RH_traseiro - RH_dianteiro. Fundamental para
    # balanço aerodinâmico. Se rake é 0 ou negativo, carro
    # perde downforce. Se é muito alto, instabilidade traseira.
    # ============================================================
    _check_rake(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7D: FAST BUMP — Salto em zebras
    # Se variância da deflexão de suspensão é alta, o carro
    # está saltando (provavelmente sobre zebras). Reduzir
    # Fast Bump para absorver melhor.
    # ============================================================
    _check_fast_bump(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7E: BRAKE DUCT — Abrir duto se freios superaquecem
    # Complementa regra 5 com ação mais específica.
    # ============================================================
    _check_brake_duct(telemetry, config, suggestions)

    # ============================================================
    # REGRA 7F: ABS/TC por classe
    # Sugere ajuste de ABS/TC baseado em lockups e tração.
    # LMP2 não tem ABS — ignora automaticamente.
    # ============================================================
    _check_abs_tc(telemetry, config, suggestions)

    # ============================================================
    # REGRA 8: COMPOUND — Recomendação de troca de pneu
    # Se as condições mudaram (seco→chuva ou chuva→seco),
    # sugerir troca de compound.
    # ============================================================
    _check_compound(telemetry, config, suggestions)

    # ============================================================
    # REGRA 9: FUEL COMPENSATION — Ajuste por peso de combustível
    # Com tanque cheio o carro é pesado (ride height cai, molas
    # precisam ser mais duras). Com tanque vazio, o oposto.
    # ============================================================
    _check_fuel_weight(telemetry, config, suggestions)

    # ============================================================
    # REGRA 10: VIRTUAL ENERGY / REGENERAÇÃO (Hypercars)
    # Gestão de energia híbrida: bateria, regeneração, deploy.
    # ============================================================
    if config.get("has_regen", False):
        _check_virtual_energy(telemetry, config, suggestions)

    # Ordenar por prioridade (1 = mais importante)
    suggestions.sort(key=lambda s: s.priority)

    # Filtrar sugestões pelo nível do piloto
    if level != "advanced":
        from core.brain import LEVEL_OUTPUTS
        allowed_params = set(LEVEL_OUTPUTS.get(level, LEVEL_OUTPUTS["basic"]))
        suggestions = [s for s in suggestions if s.param_name in allowed_params]

    # Atribuir categorias hierárquicas
    for s in suggestions:
        s.category = get_param_category(s.param_name)

    return suggestions


def _check_camber(tele: dict, config: dict,
                  suggestions: list[HeuristicSuggestion]):
    """Verifica balanço de temperatura I-M-O para ajuste de camber."""
    temp_max_spread = config["temp_spread_max_c"]

    for wheel, param, side in [
        ("fl", "delta_camber_f", "dianteiro esquerdo"),
        ("fr", "delta_camber_f", "dianteiro direito"),
        ("rl", "delta_camber_r", "traseiro esquerdo"),
        ("rr", "delta_camber_r", "traseiro direito"),
    ]:
        inner = tele.get(f"temp_{wheel}_inner", 0)
        outer = tele.get(f"temp_{wheel}_outer", 0)
        if inner <= 0 or outer <= 0:
            continue

        spread = inner - outer

        if spread > temp_max_spread:
            # Inner muito quente → camber negativo DEMAIS
            # Reduzir camber negativo = valor MENOS negativo (+delta)
            suggestions.append(HeuristicSuggestion(
                param_name=param,
                delta=+1,
                rule_name="camber_inner_hot",
                condition=f"temp_inner({inner:.0f}°C) > temp_outer({outer:.0f}°C) + {temp_max_spread}°C",
                explanation=(
                    f"Pneu {side}: lado interno {spread:.0f}°C mais quente que o externo. "
                    f"Indica camber negativo excessivo. Reduzir camber negativo "
                    f"(valor menos negativo) para distribuir melhor a carga."
                ),
                priority=2,
            ))
        elif spread < -temp_max_spread:
            # Outer muito quente → camber negativo INSUFICIENTE
            suggestions.append(HeuristicSuggestion(
                param_name=param,
                delta=-1,
                rule_name="camber_outer_hot",
                condition=f"temp_outer({outer:.0f}°C) > temp_inner({inner:.0f}°C) + {temp_max_spread}°C",
                explanation=(
                    f"Pneu {side}: lado externo {abs(spread):.0f}°C mais quente. "
                    f"Indica camber negativo insuficiente. Aumentar camber negativo "
                    f"para melhor contato na curva."
                ),
                priority=2,
            ))


def _check_tire_pressure(tele: dict, config: dict,
                         suggestions: list[HeuristicSuggestion]):
    """Verifica temperatura central vs laterais para ajuste de pressão."""
    for wheel, param, side in [
        ("fl", "delta_pressure_f", "dianteiro esquerdo"),
        ("fr", "delta_pressure_f", "dianteiro direito"),
        ("rl", "delta_pressure_r", "traseiro esquerdo"),
        ("rr", "delta_pressure_r", "traseiro direito"),
    ]:
        inner = tele.get(f"temp_{wheel}_inner", 0)
        middle = tele.get(f"temp_{wheel}_middle", 0)
        outer = tele.get(f"temp_{wheel}_outer", 0)
        if inner <= 0 or middle <= 0 or outer <= 0:
            continue

        avg_edges = (inner + outer) / 2

        if middle > avg_edges + 8:
            # Centro mais quente que bordas → pressão ALTA
            # Pneu está abaulado no centro (sobre-inflado)
            suggestions.append(HeuristicSuggestion(
                param_name=param,
                delta=-1,
                rule_name="pressure_center_hot",
                condition=f"temp_middle({middle:.0f}°C) > avg_edges({avg_edges:.0f}°C) + 8°C",
                explanation=(
                    f"Pneu {side}: centro {middle - avg_edges:.0f}°C mais quente que bordas. "
                    f"Pressão possivelmente alta demais — pneu abaulado no centro. "
                    f"Reduzir pressão para melhor contato."
                ),
                priority=3,
            ))
        elif middle < avg_edges - 8:
            # Centro mais frio → pressão BAIXA
            suggestions.append(HeuristicSuggestion(
                param_name=param,
                delta=+1,
                rule_name="pressure_center_cold",
                condition=f"temp_middle({middle:.0f}°C) < avg_edges({avg_edges:.0f}°C) - 8°C",
                explanation=(
                    f"Pneu {side}: centro {avg_edges - middle:.0f}°C mais frio que bordas. "
                    f"Pressão possivelmente baixa — pneu afundando no centro. "
                    f"Aumentar pressão para melhor perfil de contato."
                ),
                priority=3,
            ))


def _check_rear_wing(tele: dict, config: dict,
                     suggestions: list[HeuristicSuggestion]):
    """Verifica balanço de temperatura F/R para ajuste de asa traseira."""
    # Temperatura média dos pneus dianteiros vs traseiros
    front_temps = [
        tele.get(f"temp_{w}_middle", 0)
        for w in ("fl", "fr")
        if tele.get(f"temp_{w}_middle", 0) > 0
    ]
    rear_temps = [
        tele.get(f"temp_{w}_middle", 0)
        for w in ("rl", "rr")
        if tele.get(f"temp_{w}_middle", 0) > 0
    ]
    if not front_temps or not rear_temps:
        return

    avg_front = sum(front_temps) / len(front_temps)
    avg_rear = sum(rear_temps) / len(rear_temps)
    diff = avg_rear - avg_front

    if diff > 15:
        # Traseiros muito mais quentes → eixo traseiro sobrecarregado
        # Mais asa traseira transfere carga aero para trás
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=+1,
            rule_name="rear_overloaded",
            condition=f"temp_rear({avg_rear:.0f}°C) > temp_front({avg_front:.0f}°C) + 15°C",
            explanation=(
                f"Pneus traseiros {diff:.0f}°C mais quentes que os dianteiros. "
                f"Eixo traseiro sobrecarregado. Aumentar asa traseira para "
                f"transferir mais carga aerodinâmica para o eixo traseiro."
            ),
            priority=2,
        ))
    elif diff < -15:
        # Dianteiros muito mais quentes
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=-1,
            rule_name="front_overloaded",
            condition=f"temp_front({avg_front:.0f}°C) > temp_rear({avg_rear:.0f}°C) + 15°C",
            explanation=(
                f"Pneus dianteiros {abs(diff):.0f}°C mais quentes que traseiros. "
                f"Eixo dianteiro sobrecarregado. Reduzir asa traseira para "
                f"redistribuir o balanço aerodinâmico."
            ),
            priority=2,
        ))


def _check_springs(tele: dict, config: dict,
                   suggestions: list[HeuristicSuggestion]):
    """Verifica ride height para ajuste de molas."""
    rh_f = tele.get("ride_height_f", 0)
    rh_r = tele.get("ride_height_r", 0)

    # Ride height muito baixo = possível bottoming (batida no assoalho)
    if rh_f > 0 and rh_f < 0.02:  # menos de 2cm
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_f",
            delta=+1,
            rule_name="front_bottoming",
            condition=f"ride_height_front({rh_f*100:.1f}cm) < 2.0cm",
            explanation=(
                f"Ride height dianteiro muito baixo ({rh_f*100:.1f}cm). "
                f"Risco de bottoming (assoalho batendo no chão). "
                f"Endurecer mola dianteira para levantar o carro."
            ),
            priority=1,
        ))

    if rh_r > 0 and rh_r < 0.02:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_r",
            delta=+1,
            rule_name="rear_bottoming",
            condition=f"ride_height_rear({rh_r*100:.1f}cm) < 2.0cm",
            explanation=(
                f"Ride height traseiro muito baixo ({rh_r*100:.1f}cm). "
                f"Risco de bottoming traseiro. Endurecer mola traseira."
            ),
            priority=1,
        ))


def _check_brakes(tele: dict, config: dict,
                  suggestions: list[HeuristicSuggestion]):
    """Verifica temperaturas de freio excessivas."""
    brake_max = config["brake_temp_max_c"]

    for wheel, side in [("fl", "dianteiro esquerdo"), ("fr", "dianteiro direito"),
                         ("rl", "traseiro esquerdo"), ("rr", "traseiro direito")]:
        temp = tele.get(f"max_brake_temp_{wheel}", 0)
        if temp > brake_max:
            suggestions.append(HeuristicSuggestion(
                param_name="delta_brake_press",
                delta=-1,
                rule_name="brake_overheat",
                condition=f"brake_temp_{wheel}({temp:.0f}°C) > {brake_max}°C",
                explanation=(
                    f"Freio {side} ultrapassou {brake_max}°C ({temp:.0f}°C). "
                    f"Risco de fade (perda de eficiência). "
                    f"Considerar reduzir pressão de freio ou abrir duto de ar."
                ),
                priority=2,
            ))


def _check_user_feedback(tele: dict, config: dict,
                         suggestions: list[HeuristicSuggestion]):
    """Aplica correções baseadas no feedback do piloto."""
    bias = tele.get("user_feedback_bias", 0.0)

    if bias < -0.5:
        # Understeer severo → mais rotação no eixo dianteiro
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_f",
            delta=-1,
            rule_name="understeer_arb",
            condition=f"feedback_bias({bias:.1f}) < -0.5 (understeer severo)",
            explanation=(
                "Piloto reporta understeer severo (carro não vira). "
                "Amolecer barra anti-rolagem dianteira para melhorar "
                "a aderência dianteira nas curvas."
            ),
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=+1,
            rule_name="understeer_wing",
            condition=f"feedback_bias({bias:.1f}) < -0.5",
            explanation=(
                "Understeer: aumentar asa traseira para mover o balanço "
                "aerodinâmico para trás, aliviando o eixo dianteiro."
            ),
            priority=2,
        ))
    elif bias > 0.5:
        # Oversteer severo → mais estabilidade no eixo traseiro
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_r",
            delta=-1,
            rule_name="oversteer_arb",
            condition=f"feedback_bias({bias:.1f}) > 0.5 (oversteer severo)",
            explanation=(
                "Piloto reporta oversteer severo (traseira escapa). "
                "Amolecer barra anti-rolagem traseira para melhorar "
                "a aderência traseira nas curvas."
            ),
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=-1,
            rule_name="oversteer_wing",
            condition=f"feedback_bias({bias:.1f}) > 0.5",
            explanation=(
                "Oversteer: reduzir asa traseira para redistribuir "
                "o balanço aerodinâmico."
            ),
            priority=2,
        ))


def _check_weather(tele: dict, config: dict,
                   suggestions: list[HeuristicSuggestion]):
    """Ajustes baseados em condições climáticas (chuva, umidade, temperatura)."""
    rain = tele.get("raining", 0.0)
    wetness = tele.get("avg_path_wetness", 0.0)
    track_temp = tele.get("track_temp", 0.0)
    grip_avg = tele.get("grip_avg", 1.0)

    # ── Chuva leve (0.1 < rain ≤ 0.4 ou wetness > 0.2) ──
    if 0.1 < rain <= 0.4 or 0.2 < wetness <= 0.5:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_f",
            delta=-1,
            rule_name="rain_light_pressure",
            condition=f"rain({rain:.2f}) ou wetness({wetness:.2f}) indica chuva leve",
            explanation=(
                "Chuva leve/pista úmida detectada. Reduzir pressão dos pneus "
                "para aumentar a área de contato e melhorar grip no molhado."
            ),
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_r",
            delta=-1,
            rule_name="rain_light_pressure_r",
            condition=f"rain({rain:.2f}) ou wetness({wetness:.2f})",
            explanation="Reduzir pressão traseira para chuva leve.",
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=+1,
            rule_name="rain_light_wing",
            condition=f"rain({rain:.2f})",
            explanation=(
                "Chuva leve: aumentar asa traseira para mais downforce "
                "e compensar a perda de grip mecânico."
            ),
            priority=2,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_f",
            delta=-1,
            rule_name="rain_light_arb_f",
            condition=f"rain({rain:.2f})",
            explanation="Chuva leve: amolecer ARB dianteira para mais grip mecânico.",
            priority=3,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_r",
            delta=-1,
            rule_name="rain_light_arb_r",
            condition=f"rain({rain:.2f})",
            explanation="Chuva leve: amolecer ARB traseira para mais grip mecânico.",
            priority=3,
        ))

    # ── Chuva forte (rain > 0.4 ou wetness > 0.5) ──
    elif rain > 0.4 or wetness > 0.5:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_f",
            delta=-2,
            rule_name="rain_heavy_pressure_f",
            condition=f"rain({rain:.2f}) ou wetness({wetness:.2f}) indica chuva forte",
            explanation=(
                "Chuva forte detectada. Reduzir pressão dianteira significativamente "
                "para maximizar contato com pista molhada."
            ),
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_r",
            delta=-2,
            rule_name="rain_heavy_pressure_r",
            condition=f"rain({rain:.2f})",
            explanation="Chuva forte: reduzir pressão traseira.",
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=+2,
            rule_name="rain_heavy_wing",
            condition=f"rain({rain:.2f})",
            explanation=(
                "Chuva forte: aumentar asa traseira para máxima downforce. "
                "No molhado, grip mecânico é limitado — downforce é essencial."
            ),
            priority=1,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_f",
            delta=-2,
            rule_name="rain_heavy_arb_f",
            condition=f"rain({rain:.2f})",
            explanation="Chuva forte: amolecer ARB dianteira para máximo grip.",
            priority=2,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_arb_r",
            delta=-2,
            rule_name="rain_heavy_arb_r",
            condition=f"rain({rain:.2f})",
            explanation="Chuva forte: amolecer ARB traseira para máximo grip.",
            priority=2,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_f",
            delta=-1,
            rule_name="rain_heavy_spring_f",
            condition=f"rain({rain:.2f})",
            explanation="Chuva forte: amolecer mola dianteira para absorver irregularidades.",
            priority=3,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_r",
            delta=-1,
            rule_name="rain_heavy_spring_r",
            condition=f"rain({rain:.2f})",
            explanation="Chuva forte: amolecer mola traseira.",
            priority=3,
        ))

    # ── Pista fria (< 20°C) — pressão sobe mais devagar ──
    if 0 < track_temp < 20:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_f",
            delta=+1,
            rule_name="cold_track_pressure_f",
            condition=f"track_temp({track_temp:.0f}°C) < 20°C",
            explanation=(
                f"Pista fria ({track_temp:.0f}°C). Pressão dos pneus sobe menos "
                "com o calor. Iniciar com pressão ligeiramente mais alta."
            ),
            priority=4,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_r",
            delta=+1,
            rule_name="cold_track_pressure_r",
            condition=f"track_temp({track_temp:.0f}°C) < 20°C",
            explanation="Pista fria: pressão traseira +1.",
            priority=4,
        ))

    # ── Pista quente (> 45°C) — pressão sobe rápido ──
    elif track_temp > 45:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_f",
            delta=-1,
            rule_name="hot_track_pressure_f",
            condition=f"track_temp({track_temp:.0f}°C) > 45°C",
            explanation=(
                f"Pista quente ({track_temp:.0f}°C). Pressão vai subir muito "
                "com o calor. Iniciar com pressão mais baixa."
            ),
            priority=4,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_pressure_r",
            delta=-1,
            rule_name="hot_track_pressure_r",
            condition=f"track_temp({track_temp:.0f}°C) > 45°C",
            explanation="Pista quente: pressão traseira -1.",
            priority=4,
        ))

    # ── Grip baixo geral (< 0.7) — provavelmente pista verde ou suja ──
    if 0 < grip_avg < 0.7:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_rw",
            delta=+1,
            rule_name="low_grip_wing",
            condition=f"grip_avg({grip_avg:.2f}) < 0.70",
            explanation=(
                f"Grip médio baixo ({grip_avg:.2f}). Pista possivelmente verde/suja. "
                "Aumentar asa traseira para compensar com downforce."
            ),
            priority=3,
        ))


def _check_compound(tele: dict, config: dict,
                    suggestions: list[HeuristicSuggestion]):
    """Recomenda troca de compound (seco↔chuva) conforme condições."""
    rain = tele.get("raining", 0.0)
    wetness = tele.get("avg_path_wetness", 0.0)
    compound = tele.get("compound_front", "").lower()

    # Se está em pneu seco e pista molhada → sugerir chuva
    is_dry_compound = "wet" not in compound and "rain" not in compound
    is_wet_compound = not is_dry_compound

    if (rain > 0.3 or wetness > 0.4) and is_dry_compound:
        suggestions.append(HeuristicSuggestion(
            param_name="compound_change",
            delta=0,
            rule_name="compound_to_wet",
            condition=f"rain({rain:.2f}) wetness({wetness:.2f}) com pneu seco",
            explanation=(
                f"⚠️ TROCA DE PNEU RECOMENDADA: Chuva/pista molhada detectada "
                f"(rain={rain:.0%}, wetness={wetness:.0%}) mas usando pneu seco. "
                f"Trocar para pneu de chuva para evitar aquaplanagem."
            ),
            priority=0,  # Prioridade máxima
        ))

    # Se está em pneu chuva e pista seca → sugerir seco
    elif rain < 0.1 and wetness < 0.15 and is_wet_compound:
        track_temp = tele.get("track_temp", 25.0)
        if track_temp > 20:
            suggestions.append(HeuristicSuggestion(
                param_name="compound_change",
                delta=0,
                rule_name="compound_to_dry",
                condition=f"rain({rain:.2f}) wetness({wetness:.2f}) com pneu chuva",
                explanation=(
                    f"⚠️ TROCA DE PNEU RECOMENDADA: Pista seca "
                    f"(rain={rain:.0%}, temp={track_temp:.0f}°C) mas usando pneu de chuva. "
                    f"Pneu de chuva em pista seca degradam muito rápido. Trocar para seco."
                ),
                priority=0,
            ))

    # Se condições mistas — sugerir intermediário se disponível
    elif 0.1 <= rain <= 0.3 or 0.15 <= wetness <= 0.4:
        suggestions.append(HeuristicSuggestion(
            param_name="compound_change",
            delta=0,
            rule_name="compound_intermediate",
            condition=f"rain({rain:.2f}) wetness({wetness:.2f})",
            explanation=(
                f"Condições mistas (rain={rain:.0%}, wetness={wetness:.0%}). "
                f"Considere pneu intermediário se disponível no carro. "
                f"Se não, ajuste pressão para chuva leve."
            ),
            priority=1,
        ))


def _check_fuel_weight(tele: dict, config: dict,
                       suggestions: list[HeuristicSuggestion]):
    """Ajustes compensatórios baseados no peso de combustível."""
    fuel = tele.get("fuel", 0.0)
    fuel_capacity = tele.get("fuel_capacity", 0.0)

    if fuel_capacity <= 0 or fuel <= 0:
        return

    fuel_fraction = fuel / fuel_capacity

    # Tanque muito cheio (> 80%) — carro pesado
    if fuel_fraction > 0.8:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_f",
            delta=+1,
            rule_name="fuel_heavy_spring_f",
            condition=f"fuel({fuel:.0f}L / {fuel_capacity:.0f}L = {fuel_fraction:.0%})",
            explanation=(
                f"Tanque cheio ({fuel_fraction:.0%}). Carro pesado — endurecer "
                f"mola dianteira para compensar ride height que cai com o peso."
            ),
            priority=5,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_r",
            delta=+1,
            rule_name="fuel_heavy_spring_r",
            condition=f"fuel_fraction({fuel_fraction:.0%}) > 80%",
            explanation="Tanque cheio: endurecer mola traseira.",
            priority=5,
        ))

    # Tanque quase vazio (< 20%) — carro leve
    elif fuel_fraction < 0.2:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_f",
            delta=-1,
            rule_name="fuel_light_spring_f",
            condition=f"fuel({fuel:.0f}L / {fuel_capacity:.0f}L = {fuel_fraction:.0%})",
            explanation=(
                f"Tanque quase vazio ({fuel_fraction:.0%}). Carro leve — amolecer "
                f"mola dianteira para melhor contato com o solo."
            ),
            priority=5,
        ))
        suggestions.append(HeuristicSuggestion(
            param_name="delta_spring_r",
            delta=-1,
            rule_name="fuel_light_spring_r",
            condition=f"fuel_fraction({fuel_fraction:.0%}) < 20%",
            explanation="Tanque vazio: amolecer mola traseira.",
            priority=5,
        ))


def _check_virtual_energy(tele: dict, config: dict,
                          suggestions: list[HeuristicSuggestion]):
    """
    Gestão de energia para Hypercars híbridos.
    Ajusta VirtualEnergySetting e RegenerationMapSetting baseado
    na carga da bateria e no tipo de sessão.
    """
    battery = tele.get("battery_charge", -1.0)
    session_type = tele.get("session_type", "practice")

    if battery < 0:
        return  # Sem dados de bateria

    # Bateria muito baixa (< 30%) — mais regeneração
    if battery < 0.30:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_regen_map",
            delta=+1,
            rule_name="battery_low_regen",
            condition=f"battery({battery:.0%}) < 30%",
            explanation=(
                f"Bateria baixa ({battery:.0%}). Aumentar regeneração "
                f"para recuperar energia nas frenagens."
            ),
            priority=3,
            category="electronics",
        ))

    # Bateria alta (> 80%) — pode usar mais deploy
    elif battery > 0.80:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_virtual_energy",
            delta=+1,
            rule_name="battery_high_deploy",
            condition=f"battery({battery:.0%}) > 80%",
            explanation=(
                f"Bateria cheia ({battery:.0%}). Usar mais energia virtual "
                f"para melhor performance nas retas."
            ),
            priority=4,
            category="electronics",
        ))

    # Em qualy — máximo deploy, mínima regeneração
    if session_type == "qualy":
        suggestions.append(HeuristicSuggestion(
            param_name="delta_virtual_energy",
            delta=+2,
            rule_name="qualy_max_deploy",
            condition="qualy mode",
            explanation=(
                "Qualificação: maximizar deploy de energia virtual "
                "para melhor tempo por volta."
            ),
            priority=2,
            category="electronics",
        ))


def _check_tire_temp_window(tele: dict, config: dict,
                            suggestions: list[HeuristicSuggestion]):
    """
    Verifica se a temperatura GERAL do pneu está na janela ideal.
    Diferente de _check_camber (que olha spread I-M-O),
    aqui olhamos se a temperatura MÉDIA está acima ou abaixo do alvo.
    """
    temp_min, temp_max = config.get("temp_target_c", (85, 100))

    for wheel, param_press, param_camber, side in [
        ("fl", "delta_pressure_f", "delta_camber_f", "dianteiro esquerdo"),
        ("fr", "delta_pressure_f", "delta_camber_f", "dianteiro direito"),
        ("rl", "delta_pressure_r", "delta_camber_r", "traseiro esquerdo"),
        ("rr", "delta_pressure_r", "delta_camber_r", "traseiro direito"),
    ]:
        inner = tele.get(f"temp_{wheel}_inner", 0)
        middle = tele.get(f"temp_{wheel}_middle", 0)
        outer = tele.get(f"temp_{wheel}_outer", 0)
        if inner <= 0 or middle <= 0 or outer <= 0:
            continue

        avg_temp = (inner + middle + outer) / 3.0

        if avg_temp < temp_min:
            suggestions.append(HeuristicSuggestion(
                param_name=param_press,
                delta=+1,
                rule_name="tire_too_cold",
                condition=f"temp_avg_{wheel}({avg_temp:.0f}°C) < janela_min({temp_min}°C)",
                explanation=(
                    f"Pneu {side} frio ({avg_temp:.0f}°C, janela {temp_min}-{temp_max}°C). "
                    f"Aumentar pressão para aquecer mais rápido (mais deformação interna)."
                ),
                priority=3,
            ))
        elif avg_temp > temp_max:
            suggestions.append(HeuristicSuggestion(
                param_name=param_press,
                delta=-1,
                rule_name="tire_too_hot",
                condition=f"temp_avg_{wheel}({avg_temp:.0f}°C) > janela_max({temp_max}°C)",
                explanation=(
                    f"Pneu {side} superaquecendo ({avg_temp:.0f}°C, janela {temp_min}-{temp_max}°C). "
                    f"Reduzir pressão para diminuir calor gerado."
                ),
                priority=2,
            ))


def _check_rake(tele: dict, config: dict,
                suggestions: list[HeuristicSuggestion]):
    """
    Verifica o RAKE (diferença de ride height traseiro - dianteiro).
    Rake positivo = traseiro mais alto que dianteiro = mais downforce.
    Rake zero ou negativo = perda de eficiência aerodinâmica.
    Rake muito alto = instabilidade traseira.
    """
    rh_f = tele.get("ride_height_f", 0)
    rh_r = tele.get("ride_height_r", 0)
    if rh_f <= 0 or rh_r <= 0:
        return

    rake_mm = (rh_r - rh_f) * 1000  # Converter para mm

    is_aero_critical = config.get("aero_balance_critical", False)
    # Pistas de alta velocidade (hypercar/LMP2) precisam de rake preciso
    ideal_rake_min = 3.0 if is_aero_critical else 1.0   # mm
    ideal_rake_max = 15.0 if is_aero_critical else 20.0  # mm

    if rake_mm < ideal_rake_min:
        # Rake insuficiente — frente muito alta ou trás muito baixo
        suggestions.append(HeuristicSuggestion(
            param_name="delta_ride_height_f",
            delta=-1,
            rule_name="rake_too_low_front",
            condition=f"rake({rake_mm:.1f}mm) < mín({ideal_rake_min}mm)",
            explanation=(
                f"Rake baixo ({rake_mm:.1f}mm). Dianteira muito alta em relação "
                f"à traseira. Baixar ride height dianteiro para aumentar rake "
                f"e melhorar eficiência aerodinâmica."
            ),
            priority=2 if is_aero_critical else 4,
        ))
    elif rake_mm > ideal_rake_max:
        # Rake excessivo — traseira muito alta ou frente muito baixa
        suggestions.append(HeuristicSuggestion(
            param_name="delta_ride_height_r",
            delta=-1,
            rule_name="rake_too_high_rear",
            condition=f"rake({rake_mm:.1f}mm) > máx({ideal_rake_max}mm)",
            explanation=(
                f"Rake excessivo ({rake_mm:.1f}mm). Traseira muito alta. "
                f"Risco de instabilidade em alta velocidade. "
                f"Baixar ride height traseiro."
            ),
            priority=2 if is_aero_critical else 4,
        ))


def _check_fast_bump(tele: dict, config: dict,
                     suggestions: list[HeuristicSuggestion]):
    """
    Detecta saltos em zebras via variância de deflexão de suspensão.
    Se a variância é alta, o carro está oscilando violentamente
    (provavelmente passando sobre zebras/kerbs). Reduzir Fast Bump
    permite a roda seguir o perfil da zebra em vez de pular.
    """
    susp_var_f = tele.get("susp_deflection_var_f", 0.0)
    susp_var_r = tele.get("susp_deflection_var_r", 0.0)

    # Threshold: variância > 0.001 m² indica oscilação significativa
    threshold = 0.001

    if susp_var_f > threshold:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_fast_bump_f",
            delta=-1,
            rule_name="kerb_bounce_front",
            condition=f"susp_var_front({susp_var_f:.4f}) > {threshold}",
            explanation=(
                f"Suspensão dianteira oscilando muito (variância {susp_var_f:.4f}). "
                f"Provável salto sobre zebras. Reduzir Fast Bump dianteiro "
                f"para a roda acompanhar melhor o perfil do kerb."
            ),
            priority=3,
        ))

    if susp_var_r > threshold:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_fast_bump_r",
            delta=-1,
            rule_name="kerb_bounce_rear",
            condition=f"susp_var_rear({susp_var_r:.4f}) > {threshold}",
            explanation=(
                f"Suspensão traseira oscilando muito (variância {susp_var_r:.4f}). "
                f"Provável salto sobre zebras. Reduzir Fast Bump traseiro."
            ),
            priority=3,
        ))


def _check_brake_duct(tele: dict, config: dict,
                      suggestions: list[HeuristicSuggestion]):
    """
    Sugere abrir brake duct quando freios superaquecem.
    Complementa _check_brakes (que só sugere reduzir pressão).
    """
    brake_max = config["brake_temp_max_c"]

    # Verificar dianteiros
    temp_fl = tele.get("max_brake_temp_fl", 0)
    temp_fr = tele.get("max_brake_temp_fr", 0)
    avg_front_brake = 0
    count_f = 0
    if temp_fl > 0:
        avg_front_brake += temp_fl
        count_f += 1
    if temp_fr > 0:
        avg_front_brake += temp_fr
        count_f += 1
    if count_f > 0:
        avg_front_brake /= count_f

    if avg_front_brake > brake_max:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_brake_duct_f",
            delta=+1,
            rule_name="brake_duct_front_hot",
            condition=f"avg_brake_front({avg_front_brake:.0f}°C) > {brake_max}°C",
            explanation=(
                f"Freios dianteiros superaquecendo ({avg_front_brake:.0f}°C). "
                f"Abrir duto de freio dianteiro para mais refrigeração."
            ),
            priority=2,
        ))

    # Verificar traseiros
    temp_rl = tele.get("max_brake_temp_rl", 0)
    temp_rr = tele.get("max_brake_temp_rr", 0)
    avg_rear_brake = 0
    count_r = 0
    if temp_rl > 0:
        avg_rear_brake += temp_rl
        count_r += 1
    if temp_rr > 0:
        avg_rear_brake += temp_rr
        count_r += 1
    if count_r > 0:
        avg_rear_brake /= count_r

    if avg_rear_brake > brake_max:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_brake_duct_r",
            delta=+1,
            rule_name="brake_duct_rear_hot",
            condition=f"avg_brake_rear({avg_rear_brake:.0f}°C) > {brake_max}°C",
            explanation=(
                f"Freios traseiros superaquecendo ({avg_rear_brake:.0f}°C). "
                f"Abrir duto de freio traseiro para mais refrigeração."
            ),
            priority=2,
        ))


def _check_abs_tc(tele: dict, config: dict,
                  suggestions: list[HeuristicSuggestion]):
    """
    Sugere ajuste de ABS/TC baseado em dados de aderência.
    Respeita carros que NÃO têm ABS (LMP2).
    Cobre: TC Map, TC Power Cut, TC Slip Angle, TC Onboard, ABS.
    """
    car_class = tele.get("car_class", "hypercar")
    has_abs = config.get("has_abs", car_class != "lmp2")
    has_tc = config.get("has_tc", car_class != "lmp2")

    grip_avg = tele.get("grip_avg", 1.0)
    rain = tele.get("raining", 0.0)

    # ── ABS: Se grip está baixo E está chovendo, aumentar ABS ──
    if has_abs and rain > 0.2 and grip_avg < 0.8:
        suggestions.append(HeuristicSuggestion(
            param_name="delta_abs_map",
            delta=+1,
            rule_name="abs_rain_increase",
            condition=f"rain({rain:.2f}) > 0.2 e grip({grip_avg:.2f}) < 0.8",
            explanation=(
                "Grip baixo na chuva. Aumentar ABS para evitar travamento "
                "das rodas em pista molhada."
            ),
            priority=3,
        ))

    # ── TC Map: Se grip está baixo na saída de curva ──
    if has_tc:
        traction_loss = tele.get("traction_loss_events", 0)
        if traction_loss > 3:
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_map",
                delta=+1,
                rule_name="tc_traction_loss",
                condition=f"traction_loss_events({traction_loss}) > 3 por volta",
                explanation=(
                    f"Detectados {traction_loss} eventos de perda de tração por volta. "
                    f"Aumentar TC para limitar patinagem na saída das curvas."
                ),
                priority=3,
            ))

        # ── TC Power Cut: Controla quanto potência é cortada ao ativar TC ──
        # Mais power cut = mais seguro mas mais lento na saída de curva
        # Menos power cut = mais rápido mas risco de spin
        rear_slip = tele.get("rear_slip_ratio", 0.0)
        if traction_loss > 5 and rear_slip > 0.08:
            # Muita perda de tração + alto slip → aumentar power cut
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_power_cut",
                delta=+1,
                rule_name="tc_power_cut_increase",
                condition=(
                    f"traction_loss({traction_loss}) > 5 e "
                    f"rear_slip({rear_slip:.3f}) > 0.08"
                ),
                explanation=(
                    "Alta perda de tração com slippage traseiro elevado. "
                    "Aumentar TC Power Cut para cortar mais potência quando "
                    "o TC intervém, reduzindo escorregamento na aceleração."
                ),
                priority=3,
            ))
        elif traction_loss <= 1 and rear_slip < 0.03:
            # Pneus com boa aderência, TC cortando demais → reduzir
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_power_cut",
                delta=-1,
                rule_name="tc_power_cut_decrease",
                condition=(
                    f"traction_loss({traction_loss}) <= 1 e "
                    f"rear_slip({rear_slip:.3f}) < 0.03"
                ),
                explanation=(
                    "Tração estável com pouco slippage. Reduzir TC Power Cut "
                    "para liberar mais potência na saída de curva — ganho de "
                    "tempo sem comprometer estabilidade."
                ),
                priority=4,
            ))

        # ── TC Slip Angle: Ângulo de slip permitido antes do TC intervir ──
        # Mais slip angle = TC intervém mais tarde (mais liberdade)
        # Menos slip angle = TC intervém mais cedo (mais proteção)
        oversteer_events = tele.get("oversteer_events", 0)
        if oversteer_events > 3:
            # Muito oversteer → reduzir slip angle para TC intervir antes
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_slip_angle",
                delta=-1,
                rule_name="tc_slip_angle_decrease",
                condition=f"oversteer_events({oversteer_events}) > 3",
                explanation=(
                    f"Detectados {oversteer_events} eventos de oversteer. "
                    f"Reduzir TC Slip Angle para que o TC intervenha mais "
                    f"cedo, limitando a derrapagem traseira."
                ),
                priority=3,
            ))
        elif oversteer_events <= 1 and traction_loss <= 1:
            # Carro estável → mais slip angle para mais liberdade
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_slip_angle",
                delta=+1,
                rule_name="tc_slip_angle_increase",
                condition=(
                    f"oversteer_events({oversteer_events}) <= 1 e "
                    f"traction_loss({traction_loss}) <= 1"
                ),
                explanation=(
                    "Carro estável sem eventos de oversteer ou perda de "
                    "tração. Aumentar TC Slip Angle para dar mais liberdade "
                    "ao piloto na saída de curva — potencial de tempo melhor."
                ),
                priority=4,
            ))

        # ── TC Onboard (liga/desliga TC): Baseado em condições extremas ──
        # Em seco com boa aderência e piloto confiante → pode desligar
        # Em chuva/grip baixo → manter ligado
        if rain > 0.3 or grip_avg < 0.7:
            suggestions.append(HeuristicSuggestion(
                param_name="delta_tc_onboard",
                delta=+1,
                rule_name="tc_onboard_enable",
                condition=(
                    f"rain({rain:.2f}) > 0.3 ou "
                    f"grip({grip_avg:.2f}) < 0.7"
                ),
                explanation=(
                    "Condições de baixa aderência (chuva ou grip reduzido). "
                    "Garantir que TC Onboard esteja ativo para máxima "
                    "proteção contra perda de tração."
                ),
                priority=2,
            ))

    # ── Se NÃO tem ABS/TC, sugerir brake bias mais conservador ──
    if not has_abs:
        # Sem ABS → brake bias mais para trás para evitar lock-up dianteiro
        lockups = tele.get("front_lockup_events", 0)
        if lockups > 2:
            suggestions.append(HeuristicSuggestion(
                param_name="delta_rear_brake_bias",
                delta=+1,
                rule_name="no_abs_brake_bias",
                condition=f"sem ABS + lockup_events({lockups}) > 2",
                explanation=(
                    f"Carro sem ABS com {lockups} travamentos dianteiros. "
                    f"Mover balanço de freio para trás para reduzir lock-up."
                ),
                priority=2,
            ))


def merge_suggestions(heuristic: list[HeuristicSuggestion],
                      ai_deltas: dict[str, int] | None = None,
                      ai_confidence: float = 0.0,
                      session_type: str = "practice",
                      max_categories: int = 3) -> dict[str, int]:
    """
    Combina sugestões heurísticas com deltas da IA.

    Se a IA tem confiança alta, seus deltas prevalecem.
    Se a confiança é baixa, as heurísticas dominam.

    Respeita a HIERARQUIA DE AJUSTE: prioriza categorias na ordem
    Aero → Mecânico → Amortecedores → Eletrônico → Ajuste fino.
    Limita a max_categories categorias por iteração para não saturar.

    Aplica modificadores de sessão (Qualy vs Race).

    Args:
        heuristic: Sugestões heurísticas
        ai_deltas: Deltas sugeridos pela IA
        ai_confidence: 0.0 a 1.0
        session_type: "practice", "qualy" ou "race"
        max_categories: Máximo de categorias a ajustar de uma vez

    Returns:
        Dict final com deltas combinados
    """
    final: dict[str, int] = {}

    # Consolidar heurísticas (se múltiplas regras afetam o mesmo parâmetro,
    # somar os deltas mas limitar a ±3)
    for s in heuristic:
        current = final.get(s.param_name, 0)
        final[s.param_name] = max(-3, min(3, current + s.delta))

    if ai_deltas is None or ai_confidence < 0.2:
        pass  # Usar só heurísticas
    else:
        # Combinar: peso da IA cresce com a confiança
        for key, ai_val in ai_deltas.items():
            heur_val = final.get(key, 0)
            combined = ai_confidence * ai_val + (1 - ai_confidence) * heur_val
            final[key] = round(combined)

    # ── Aplicar modificadores de sessão (Qualy / Race) ──
    modifiers = SESSION_MODIFIERS.get(session_type, {})
    for param, mod_delta in modifiers.items():
        current = final.get(param, 0)
        final[param] = max(-3, min(3, current + mod_delta))

    # ── Aplicar hierarquia: limitar a N categorias ──
    if max_categories > 0 and final:
        # Agrupar parâmetros por categoria
        categories_used: dict[str, int] = {}
        for param in final:
            cat = get_param_category(param)
            order = get_category_order(cat)
            if cat not in categories_used or order < categories_used[cat]:
                categories_used[cat] = order

        # Ordenar categorias por prioridade de hierarquia
        sorted_cats = sorted(categories_used.items(), key=lambda x: x[1])
        allowed_cats = {cat for cat, _ in sorted_cats[:max_categories]}

        # Filtrar parâmetros — manter apenas das categorias permitidas
        # EXCEÇÃO: compound_change sempre passa (prioridade 0)
        final = {
            k: v for k, v in final.items()
            if get_param_category(k) in allowed_cats
            or k == "compound_change"
        }

    # Remover zerados
    final = {k: v for k, v in final.items() if v != 0}

    return final


def apply_driver_profile(deltas: dict[str, int],
                         aggression: float = 0.5,
                         braking_style: float = 0.5,
                         preferences: list[dict] | None = None) -> dict[str, int]:
    """
    Modula os deltas finais pelo perfil/preferências do piloto.

    aggression: 0.0 = conservador, 1.0 = agressivo
    braking_style: 0.0 = freio suave, 1.0 = freio tardio/forte
    preferences: Lista de regras de exceção (min/max por parâmetro)
    """
    result = dict(deltas)

    # Piloto agressivo → aceita camber mais extremo, menos TC
    if aggression > 0.7:
        for key in ("delta_tc_map", "delta_abs_map"):
            if key in result and result[key] > 0:
                result[key] = max(0, result[key] - 1)

    # Piloto conservador → mais TC, mais asa
    elif aggression < 0.3:
        for key in ("delta_tc_map", "delta_abs_map"):
            if key in result and result[key] < 0:
                result[key] = min(0, result[key] + 1)
        if "delta_rw" in result and result["delta_rw"] < 0:
            result["delta_rw"] = min(0, result["delta_rw"] + 1)

    # Piloto com freio tardio → pode ter mais pressão de freio
    if braking_style > 0.7:
        if "delta_brake_press" in result and result["delta_brake_press"] < 0:
            result["delta_brake_press"] = min(0, result["delta_brake_press"] + 1)

    # Aplicar preferências explícitas (exceções do piloto)
    if preferences:
        for pref in preferences:
            param = pref.get("param_name", "")
            if not param or param not in result:
                continue
            # Se o delta levaria o valor para fora do range do piloto, limitá-lo
            # (isso é aplicado depois pelo safety, mas filtrar aqui dá feedback melhor)
            pref_min = pref.get("min_value")
            pref_max = pref.get("max_value")
            if pref_min is not None and result[param] < pref_min:
                result[param] = int(pref_min)
            if pref_max is not None and result[param] > pref_max:
                result[param] = int(pref_max)

    return {k: v for k, v in result.items() if v != 0}


def boost_from_learning_rules(deltas: dict[str, int],
                              effective_rules: list[dict],
                              failed_rules: list[dict]) -> dict[str, int]:
    """
    Ajusta deltas baseado em regras aprendidas do banco de dados.

    - Regras efetivas: reforça o delta na mesma direção
    - Regras falhadas: reduz ou inverte o delta

    Args:
        deltas: Deltas propostos pela IA/heurísticas
        effective_rules: Regras com effectiveness_rate > 0.6
        failed_rules: Regras com effectiveness_rate < 0.3
    """
    result = dict(deltas)

    # Reforçar soluções que funcionaram
    for rule in effective_rules:
        param = rule.get("param_changed", "")
        if param in result:
            known_delta = rule.get("delta_applied", 0)
            current = result[param]
            # Se estamos indo na mesma direção que a regra que funciona, manter
            if (known_delta > 0 and current > 0) or (known_delta < 0 and current < 0):
                pass  # Direção correta — OK
            elif known_delta != 0 and current == 0:
                # Adicionar o delta que funcionou antes
                result[param] = max(-3, min(3, known_delta))

    # Evitar soluções que falharam
    for rule in failed_rules:
        param = rule.get("param_changed", "")
        if param in result:
            failed_delta = rule.get("delta_applied", 0)
            current = result[param]
            # Se estamos indo na mesma direção que a regra que falhou, inverter
            if (failed_delta > 0 and current > 0) or (failed_delta < 0 and current < 0):
                result[param] = 0  # Cancelar essa sugestão
                logger.info(
                    "Cancelado %s=%d (regra falhada: %s→%s, efetividade %.0f%%)",
                    param, current,
                    rule.get("problem_detected", "?"),
                    rule.get("solution_applied", "?"),
                    rule.get("effectiveness_rate", 0) * 100,
                )

    return {k: v for k, v in result.items() if v != 0}


# ============================================================
# DELTAS DE SESSÃO — Quali vs Corrida por classe
# ============================================================

def get_session_deltas(mode: str, car_class: str = "hypercar") -> dict[str, int]:
    """
    Retorna deltas recomendados para o tipo de sessão (quali ou corrida),
    adaptados à classe do carro.

    Args:
        mode: "quali" ou "race"
        car_class: Classe normalizada do carro

    Returns:
        Dict {delta_name: delta_value}
    """
    config = CLASS_CONFIG.get(car_class, CLASS_CONFIG["hypercar"])

    if mode == "quali":
        deltas = {
            "delta_spring_f": +1,       # Mais duro (carro leve)
            "delta_spring_r": +1,
            "delta_camber_f": +1,       # Mais agressivo (grip max)
            "delta_camber_r": +1,
            "delta_pressure_fl": -1,    # Pressão baixa = aquece rápido
            "delta_pressure_fr": -1,
            "delta_pressure_rl": -1,
            "delta_pressure_rr": -1,
            "delta_engine_mix": +1,     # Modo potência
            "delta_radiator": -1,       # Menos arrasto
        }
        # Hypercars: deploy máximo + menos regen
        if config.get("has_regen", False):
            deltas["delta_virtual_energy"] = +2
            deltas["delta_regen_map"] = -1

    elif mode == "race":
        deltas = {
            "delta_spring_f": -1,       # Mais macio (compensar peso fuel)
            "delta_spring_r": -1,
            "delta_camber_f": -1,       # Conservador (preservar pneus)
            "delta_camber_r": -1,
            "delta_engine_mix": 0,      # Equilibrado
            "delta_radiator": +1,       # Sessão longa, mais refrigeração
            "delta_arb_f": -1,          # Mais estável com peso
            "delta_arb_r": -1,
            "delta_front_wing": +1,     # Mais downforce = estável
        }
        # Hypercars: regen sustentável
        if config.get("has_regen", False):
            deltas["delta_regen_map"] = +1

    else:
        deltas = {}

    # Remover deltas zero
    return {k: v for k, v in deltas.items() if v != 0}

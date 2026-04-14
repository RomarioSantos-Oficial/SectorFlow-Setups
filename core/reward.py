"""
reward.py — Sistema de recompensa multi-critério.

Calcula o reward (recompensa) que diz à IA se o ajuste
sugerido foi bom ou ruim. Quanto maior o reward, melhor.

NÃO usa apenas lap time — combina MÚLTIPLOS critérios
para capturar qualidade do ajuste mesmo quando o piloto
comete erros que afetam o tempo.

Reward = w1×ΔLapTime + w2×ΔTempBalance + w3×ΔGrip
       + w4×ΔConsistência + w5×UserSatisfaction
"""

from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger("LMU_VE.reward")

# ─────────────────────────────────────────────────────
# Perfis de pista (DNA da pista)
# main_straight_start/end: fração da volta (0.0–1.0)
# downforce_priority: Very-Low | Low | Medium-Low | Medium | High
# ─────────────────────────────────────────────────────
TRACK_POIS: dict[str, dict] = {
    "MONZA": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.08,
        "downforce_priority": "Very-Low",
        "pre_straight_zone_start": 0.82,  # B2: saída da última chicane
        "pre_straight_zone_end": 0.87,
    },
    "FUJI SPEEDWAY": {
        "main_straight_start": 0.85,
        "main_straight_end": 0.05,
        "downforce_priority": "Medium-Low",
        "pre_straight_zone_start": 0.78,  # B2: saída da última curva antes da reta
        "pre_straight_zone_end": 0.84,
    },
    "LE MANS": {
        "main_straight_start": 0.92,
        "main_straight_end": 0.06,
        "downforce_priority": "Very-Low",
        "pre_straight_zone_start": 0.86,  # B2: saída da Ford Chicane
        "pre_straight_zone_end": 0.91,
    },
    "SPA-FRANCORCHAMPS": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.07,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.83,  # B2: saída da Bus Stop
        "pre_straight_zone_end": 0.87,
    },
    "BAHRAIN INTERNATIONAL CIRCUIT": {
        "main_straight_start": 0.87,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.81,
        "pre_straight_zone_end": 0.86,
    },
    "INTERLAGOS": {
        "main_straight_start": 0.90,
        "main_straight_end": 0.05,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.85,
        "pre_straight_zone_end": 0.89,
    },
    "HUNGARORING": {
        "main_straight_start": 0.92,
        "main_straight_end": 0.05,
        "downforce_priority": "High",
        "pre_straight_zone_start": 0.87,  # B2: saída da curva 14
        "pre_straight_zone_end": 0.91,
    },
    "IMOLA": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.83,
        "pre_straight_zone_end": 0.87,
    },
    "PORTIMAO": {
        "main_straight_start": 0.85,
        "main_straight_end": 0.05,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.80,
        "pre_straight_zone_end": 0.84,
    },
    # ── S3-4: Novas pistas LMU ──────────────────────────────────────
    "SEBRING INTERNATIONAL RACEWAY": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.83,
        "pre_straight_zone_end": 0.87,
    },
    "MUGELLO CIRCUIT": {
        "main_straight_start": 0.90,
        "main_straight_end": 0.07,
        "downforce_priority": "Medium-Low",
        "pre_straight_zone_start": 0.85,
        "pre_straight_zone_end": 0.89,
    },
    "SUZUKA CIRCUIT": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.05,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.84,
        "pre_straight_zone_end": 0.87,
    },
    "RED BULL RING": {
        "main_straight_start": 0.87,
        "main_straight_end": 0.05,
        "downforce_priority": "Low",
        "pre_straight_zone_start": 0.82,
        "pre_straight_zone_end": 0.86,
    },
    "CIRCUIT OF THE AMERICAS": {
        "main_straight_start": 0.90,
        "main_straight_end": 0.07,
        "downforce_priority": "High",
        "pre_straight_zone_start": 0.86,
        "pre_straight_zone_end": 0.89,
    },
    "WATKINS GLEN INTERNATIONAL": {
        "main_straight_start": 0.85,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium-Low",
        "pre_straight_zone_start": 0.80,
        "pre_straight_zone_end": 0.84,
    },
    "LUSAIL INTERNATIONAL CIRCUIT": {
        "main_straight_start": 0.88,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.83,
        "pre_straight_zone_end": 0.87,
    },
    "MISANO WORLD CIRCUIT": {
        "main_straight_start": 0.89,
        "main_straight_end": 0.06,
        "downforce_priority": "Medium",
        "pre_straight_zone_start": 0.84,
        "pre_straight_zone_end": 0.88,
    },
    "DAYTONA INTERNATIONAL SPEEDWAY": {
        "main_straight_start": 0.80,
        "main_straight_end": 0.20,
        "downforce_priority": "Very-Low",
        "pre_straight_zone_start": 0.74,
        "pre_straight_zone_end": 0.79,
    },
    "ROAD ATLANTA": {
        "main_straight_start": 0.86,
        "main_straight_end": 0.05,
        "downforce_priority": "Medium-Low",
        "pre_straight_zone_start": 0.81,
        "pre_straight_zone_end": 0.85,
    },
    "CIRCUIT DE MONACO": {
        "main_straight_start": 0.90,
        "main_straight_end": 0.05,
        "downforce_priority": "High",
        "pre_straight_zone_start": 0.86,
        "pre_straight_zone_end": 0.89,
    },
}

# Multiplicadores de velocidade por perfil de pista
_DOWNFORCE_SPEED_MULTIPLIER: dict[str, float] = {
    "Very-Low": 2.0,    # Monza / Le Mans: penalidade dobrada por perder velocidade
    "Low": 1.5,
    "Medium-Low": 1.2,
    "Medium": 1.0,      # Neutro
    "High": 0.5,        # Mônaco / Hungaroring: velocidade de reta menos crítica
}

# Pesos dos critérios de reward (somam 1.0) — 10 critérios
REWARD_WEIGHTS_RACE = {
    "lap_time":         0.25,   # Tempo importa, mas durabilidade também
    "tire_wear":        0.20,   # Desgaste crítico em corridas longas
    "sector_improvement": 0.15,
    "temp_balance":     0.12,
    "consistency":      0.10,
    "fuel_efficiency":  0.08,
    "grip":             0.05,
    "user_satisfaction": 0.03,
    "brake_health":     0.02,
}

REWARD_WEIGHTS_QUALY = {
    "lap_time":          0.45,  # Tempo é REI na qualy
    "sector_improvement": 0.20,
    "grip":              0.15,
    "temp_balance":      0.10,
    "consistency":       0.05,
    "user_satisfaction": 0.03,
    "tire_wear":         0.01,
    "fuel_efficiency":   0.01,
    "brake_health":      0.00,
}

REWARD_WEIGHTS = {
    "lap_time": 0.20,          # Redução do tempo de volta (reduzido de 0.25)
    "top_speed": 0.13,         # Velocidade na reta principal (novo)
    "temp_balance": 0.13,      # Uniformidade de temperatura I-M-O dos pneus
    "grip": 0.10,              # Aderência média (grip fraction)
    "consistency": 0.10,       # Desvio padrão dos tempos (menor = melhor)
    "user_satisfaction": 0.10, # Feedback direto do usuário
    "tire_wear": 0.10,         # Desgaste equilibrado entre rodas
    "sector_improvement": 0.09,# Melhoria por setor (S1, S2, S3)
    "fuel_efficiency": 0.03,   # Consumo de combustível (menos = melhor)
    "brake_health": 0.02,      # Freios dentro da faixa saudável
    "exit_traction": 0.02,     # B2: tração na saída da última curva pré-reta
    # TOTAL ≈ 1.02 → normalizado por get_dynamic_weights() (REMOVIDO, agora os pesos são selecionados diretamente)
}


def compute_reward(
    lap_times_before: list[float],
    lap_times_after: list[float],
    temps_before: dict | None = None,
    temps_after: dict | None = None,
    grip_before: float = 0.0,
    grip_after: float = 0.0,
    user_feedback: float = 0.0,
    user_confidence: float = 0.5,
    wear_before: dict | None = None,
    wear_after: dict | None = None,
    sectors_before: list[float] | None = None,
    sectors_after: list[float] | None = None,
    fuel_per_lap_before: float = 0.0,
    fuel_per_lap_after: float = 0.0,
    target_avg_fuel: float = 0.0,
    max_speed_current: float = 0.0,
    max_speed_best: float = 0.0,
    track_name: str = "",
    session_type: str = "", # Adicionado para Melhoria 4
    brake_temps_after: dict | None = None,
    brake_temp_max: float = 750.0,
    exit_traction_before: float = 0.0,  # B2: acel média na zona pré-reta (antes)
    exit_traction_after: float = 0.0,   # B2: acel média na zona pré-reta (depois)
) -> float:
    """
    Calcula o reward composto para um ajuste de setup.

    Args:
        lap_times_before: Tempos das últimas N voltas ANTES do ajuste
        lap_times_after: Tempos das últimas N voltas DEPOIS do ajuste
        temps_before: Dict com temperaturas médias I/M/O antes
        temps_after: Dict com temperaturas médias I/M/O depois
        grip_before: Grip fraction médio antes (0-1)
        grip_after: Grip fraction médio depois (0-1)
        user_feedback: -1.0 (muito pior) a +1.0 (muito melhor)
        user_confidence: 0.0 a 1.0 (quanto o piloto confia na avaliação)
        wear_before: Dict com desgaste por roda antes {fl, fr, rl, rr}
        wear_after: Dict com desgaste por roda depois
        sectors_before: [S1, S2, S3] tempos de setor antes
        sectors_after: [S1, S2, S3] tempos de setor depois
        fuel_per_lap_before: Consumo por volta antes (litros)
        fuel_per_lap_after: Consumo por volta depois (litros)
        target_avg_fuel: Consumo médio histórico da pista/carro (litros); se >0
                         substitui fuel_per_lap_before como referência
        max_speed_current: Velocidade máxima na reta principal desta volta (km/h)
        max_speed_best: Melhor velocidade na reta principal registrada (km/h)
        track_name: Nome da pista (usado para buscar TRACK_POIS e multiplicador)
        brake_temps_after: Dict com temp máxima de freio por roda
        brake_temp_max: Limite de temperatura de freio saudável (°C)
        exit_traction_before: Acelerão longitudinal média na zona pré-reta antes
        exit_traction_after: Acelerão longitudinal média na zona pré-reta depois

    Returns:
        Reward entre -1.0 e +1.0
    """
    rewards = {}

    # Obter pesos dinâmicos com base no tipo de sessão
    dynamic_weights = get_dynamic_weights(track_name, session_type)

    # 1. REWARD DE LAP TIME
    rewards["lap_time"] = _reward_lap_time(lap_times_before, lap_times_after)

    # 2. REWARD DE BALANÇO DE TEMPERATURA (15%)
    rewards["temp_balance"] = _reward_temp_balance(temps_before, temps_after)

    # 3. REWARD DE GRIP (10%)
    rewards["grip"] = _reward_grip(grip_before, grip_after)

    # 4. REWARD DE CONSISTÊNCIA (10%)
    rewards["consistency"] = _reward_consistency(lap_times_before, lap_times_after)

    # 5. REWARD DO FEEDBACK DO USUÁRIO (10%)
    rewards["user_satisfaction"] = user_feedback * user_confidence

    # 6. REWARD DE DESGASTE DE PNEUS (10%)
    rewards["tire_wear"] = _reward_tire_wear(wear_before, wear_after)

    # 7. REWARD DE MELHORIA POR SETOR (10%)
    rewards["sector_improvement"] = _reward_sectors(sectors_before, sectors_after)

    # 8. REWARD DE EFICIÊNCIA DE COMBUSTÍVEL (3%)
    # Usa média histórica se disponível; caso contrário, compara setups
    if target_avg_fuel > 0 and fuel_per_lap_after > 0:
        rewards["fuel_efficiency"] = _reward_fuel_efficiency(
            fuel_per_lap_after, target_avg_fuel
        )
    elif fuel_per_lap_before > 0:
        rewards["fuel_efficiency"] = _reward_fuel_efficiency(
            fuel_per_lap_after, fuel_per_lap_before
        )
    else:
        rewards["fuel_efficiency"] = 0.0

    # 9. REWARD DE SAÚDE DOS FREIOS (2%)
    rewards["brake_health"] = _reward_brake_health(
        brake_temps_after, brake_temp_max
    )

    # 11. REWARD DE TRAÇÃO PRÉ-RETA (B2, 2%)
    rewards["exit_traction"] = _reward_exit_traction(
        exit_traction_before, exit_traction_after
    )

    # 10. REWARD DE TOP SPEED (13%) — velocidade na reta principal
    track_name_upper = track_name.upper().strip()
    track_info = TRACK_POIS.get(track_name_upper, {})
    # Busca por substring se não achou exato
    if not track_info:
        for key in TRACK_POIS:
            if key in track_name_upper or track_name_upper in key:
                track_info = TRACK_POIS[key]
                break
    df_priority = track_info.get("downforce_priority", "Medium")
    speed_multiplier = _DOWNFORCE_SPEED_MULTIPLIER.get(df_priority, 1.0)
    rewards["top_speed"] = _reward_top_speed(
        max_speed_current, max_speed_best
    ) * speed_multiplier
    # Clipar após o multiplicador
    rewards["top_speed"] = max(-1.0, min(1.0, rewards["top_speed"]))

    # Combinar com pesos — dinâmicos pela pista e tipo de sessão
    active_weights = dynamic_weights
    total = sum(
        active_weights[key] * rewards.get(key, 0.0)
        for key in active_weights
    )

    # Clipar para [-1, +1]
    total = max(-1.0, min(1.0, total))

    logger.debug("Reward calculado: %.3f | Componentes: %s", total, rewards)
    return total


def _reward_lap_time(before: list[float], after: list[float]) -> float:
    """
    Reward baseado na variação do tempo de volta.
    Valores negativos de delta = ficou mais rápido = bom.

    Normaliza o delta pelo tempo médio (% de melhoria).
    """
    if not before or not after:
        return 0.0

    # Filtrar tempos inválidos (zero ou negativos)
    before = [t for t in before if t > 0]
    after = [t for t in after if t > 0]
    if not before or not after:
        return 0.0

    avg_before = np.mean(before)
    avg_after = np.mean(after)

    if avg_before <= 0:
        return 0.0

    # Delta percentual (negativo = melhorou)
    delta_pct = (avg_after - avg_before) / avg_before

    # Converter para reward: melhorou = positivo, piorou = negativo
    # Escala: -1% de melhoria → reward +0.5, -2% → reward +1.0
    reward = -delta_pct * 50.0  # ×50 para sensibilidade adequada
    return max(-1.0, min(1.0, reward))


def _reward_temp_balance(before: dict | None, after: dict | None) -> float:
    """
    Reward baseado na uniformidade de temperatura dos pneus.
    Pneu ideal: Inner ≈ Middle ≈ Outer (diferença < 5°C).
    Se a diferença I-M-O diminuiu, é positivo (setup melhorou balanço).
    """
    if before is None or after is None:
        return 0.0

    def _temp_spread(temps: dict) -> float:
        """Calcula spread médio de temperatura I-M-O dos 4 pneus."""
        spreads = []
        for wheel in ("fl", "fr", "rl", "rr"):
            inner = temps.get(f"temp_{wheel}_inner", 0)
            middle = temps.get(f"temp_{wheel}_middle", 0)
            outer = temps.get(f"temp_{wheel}_outer", 0)
            if inner > 0 and middle > 0 and outer > 0:
                spread = max(inner, middle, outer) - min(inner, middle, outer)
                spreads.append(spread)
        return np.mean(spreads) if spreads else 0.0

    spread_before = _temp_spread(before)
    spread_after = _temp_spread(after)

    if spread_before <= 0:
        return 0.0

    # Spread diminuiu = bom. Normaliza pela referência.
    delta = (spread_before - spread_after) / max(spread_before, 1.0)
    return max(-1.0, min(1.0, delta * 2.0))


def _reward_grip(grip_before: float, grip_after: float) -> float:
    """
    Reward baseado na aderência média.
    Grip subiu = bom.
    """
    if grip_before <= 0:
        return 0.0

    delta = (grip_after - grip_before) / max(grip_before, 0.01)
    return max(-1.0, min(1.0, delta * 10.0))


def _reward_consistency(before: list[float], after: list[float]) -> float:
    """
    Reward baseado na consistência dos tempos.
    Menor desvio padrão = piloto mais consistente = carro mais previsível.
    """
    if len(before) < 2 or len(after) < 2:
        return 0.0

    before = [t for t in before if t > 0]
    after = [t for t in after if t > 0]
    if len(before) < 2 or len(after) < 2:
        return 0.0

    std_before = np.std(before)
    std_after = np.std(after)

    if std_before <= 0.01:
        return 0.0

    # Desvio diminuiu = consistência melhorou = bom
    delta = (std_before - std_after) / std_before
    return max(-1.0, min(1.0, delta * 2.0))


def compute_training_weight(reward: float) -> float:
    """
    Calcula o peso de treinamento baseado no reward.

    - Reward positivo alto → peso alto (aprende MAIS com ajustes bons)
    - Reward negativo forte → peso médio (aprende a EVITAR)
    - Reward próximo de zero → peso baixo (pouco informativo)
    """
    abs_reward = abs(reward)
    if abs_reward < 0.1:
        return 0.1   # Quase neutro, pouco informativo
    if abs_reward < 0.3:
        return 0.5   # Moderado
    return abs_reward  # Forte sinal de aprendizado


def _reward_tire_wear(wear_before: dict | None,
                      wear_after: dict | None) -> float:
    """
    Reward baseado no desgaste equilibrado dos pneus.
    Desgaste mais uniforme entre as 4 rodas = melhor setup.
    Se o desgaste ficou mais equilibrado após o ajuste, reward positivo.
    """
    if not wear_before or not wear_after:
        return 0.0

    def _wear_imbalance(w: dict) -> float:
        vals = [w.get(k, 1.0) for k in ("fl", "fr", "rl", "rr")]
        vals = [v for v in vals if v > 0]
        if len(vals) < 4:
            return 0.0
        return max(vals) - min(vals)

    imb_before = _wear_imbalance(wear_before)
    imb_after = _wear_imbalance(wear_after)

    if imb_before <= 0.001:
        return 0.0

    # Imbalance diminuiu = bom
    delta = (imb_before - imb_after) / max(imb_before, 0.01)
    return max(-1.0, min(1.0, delta * 3.0))


def _reward_sectors(sectors_before: list[float] | None,
                    sectors_after: list[float] | None) -> float:
    """
    Reward baseado na melhoria por setor.
    Se pelo menos 2 de 3 setores melhoraram → reward positivo.
    """
    if not sectors_before or not sectors_after:
        return 0.0
    if len(sectors_before) < 2 or len(sectors_after) < 2:
        return 0.0

    improvements = 0
    total_delta_pct = 0.0
    count = min(len(sectors_before), len(sectors_after))

    for i in range(count):
        sb = sectors_before[i]
        sa = sectors_after[i]
        if sb > 0 and sa > 0:
            delta_pct = (sa - sb) / sb
            total_delta_pct += delta_pct
            if sa < sb:
                improvements += 1

    # Reward: média da melhoria percentual por setor
    avg_delta = total_delta_pct / max(count, 1)
    sector_reward = -avg_delta * 50.0  # Mesma escala do lap_time

    # Bônus se maioria dos setores melhorou
    if improvements >= 2:
        sector_reward += 0.1

    return max(-1.0, min(1.0, sector_reward))


def _reward_top_speed(max_speed_current: float,
                      max_speed_best: float,
                      threshold_kmh: float = 2.0) -> float:
    """
    Recompensa baseada na velocidade máxima na reta principal.

    Se a velocidade cair abaixo do threshold (média de oscilação normal),
    retorna reward negativo. Ganho de velocidade = reward positivo.

    Escala: perda de 10 km/h ≈ -1.0; ganho de 10 km/h ≈ +1.0.
    """
    if max_speed_best <= 0 or max_speed_current <= 0:
        return 0.0

    delta_speed = max_speed_current - max_speed_best

    # Variações menores que o threshold são ignoradas (ruído normal)
    if abs(delta_speed) < threshold_kmh:
        return 0.0

    reward = delta_speed / 10.0
    return max(-1.0, min(1.0, reward))


def _reward_fuel_efficiency(fuel_consumed: float,
                            target_avg_consumed: float) -> float:
    """
    Reward baseado na eficiência de combustível.

    Compara o consumo da volta atual com a média histórica daquela
    pista/carro. Consumir menos que a média = reward positivo.

    Multiplicador ×5.0: delta de 20% gera reward de ±1.0.
    """
    if target_avg_consumed <= 0 or fuel_consumed <= 0:
        return 0.0

    # delta_pct negativo = consumiu menos (melhor)
    delta_pct = (fuel_consumed - target_avg_consumed) / target_avg_consumed
    # Invertemos: consumir menos = reward positivo
    return max(-1.0, min(1.0, -delta_pct * 5.0))


def get_dynamic_weights(track_name: str = "", session_type: str = "") -> dict[str, float]:
    """
    Retorna REWARD_WEIGHTS ajustados ao perfil da pista.

    Em pistas de baixo downforce (Monza, Le Mans) o peso de top_speed
    sobe e grip cai. Em pistas de alto downforce (Hungaroring) é o
    inverso. Para pistas desconhecidas retorna os pesos base.

    Args:
        track_name: Nome da pista (case-insensitive).

    Returns:
        Dict de pesos (valores somam 1.00).
    """
    track_name_upper = track_name.upper().strip()
    track_info = TRACK_POIS.get(track_name_upper, {})
    if not track_info:
        for key in TRACK_POIS:
            if key in track_name_upper or track_name_upper in key:
                track_info = TRACK_POIS[key]
                break

    priority = track_info.get("downforce_priority", "Medium")

    # Selecionar pesos base com base no tipo de sessão
    if session_type.lower() == "qualy":
        base_weights = REWARD_WEIGHTS_QUALY
    else:
        base_weights = REWARD_WEIGHTS_RACE
    weights = dict(base_weights)

    if priority == "Very-Low":          # Monza / Le Mans
        weights["top_speed"]          = 0.22   # sobe (mais crítico)
        weights["temp_balance"]       = 0.11   # cai um pouco
        weights["grip"]               = 0.07   # menos curvas → grip menos crítico
        weights["sector_improvement"] = 0.07
        weights["lap_time"]           = 0.20   # mantém
        # ajusta restantes para somar 1.0
        # consistency, user_satisfaction, tire_wear, fuel_efficiency, brake_health = 0.10+0.10+0.10+0.03+0.02 = 0.35 → ok total ≈ 1.00 (0.22+0.11+0.07+0.07+0.20+0.10+0.10+0.10+0.03+0.02=1.02 → corrigir)
        weights["fuel_efficiency"]    = 0.02
        weights["brake_health"]       = 0.01
    elif priority == "Low":
        weights["top_speed"]          = 0.18
        weights["grip"]               = 0.08
    elif priority == "High":            # Hungaroring / Mônaco
        weights["top_speed"]          = 0.07   # cai (retas curtas)
        weights["grip"]               = 0.17   # sobe (grip crítico em curvas)
        weights["sector_improvement"] = 0.12   # cada curva importa mais
        weights["temp_balance"]       = 0.15   # pneus trabalham mais
        weights["lap_time"]           = 0.20

    # Normalizar para que a soma seja exatamente 1.00 (se necessário)
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        weights = {k: round(v / total, 6) for k, v in weights.items()}

    return weights


def _reward_exit_traction(traction_before: float, traction_after: float) -> float:
    """B2: reward baseado na melhoria da tração na saída da última curva pré-reta.

    Mede a aceleração longitudinal média na zona pre_straight_zone.
    Valor mais alto (mais tração) após ajuste = reward positivo.

    Args:
        traction_before: Aceleração média (m/s²) na zona antes do ajuste.
        traction_after:  Aceleração média (m/s²) na zona depois do ajuste.

    Returns:
        Reward em [-1.0, +1.0]. 0.0 se dados insuficientes.
    """
    if traction_before <= 0 and traction_after <= 0:
        return 0.0

    # Se só temos o valor depois, recompensa proporcional ao valor absoluto
    if traction_before <= 0:
        return max(0.0, min(1.0, traction_after / 10.0))

    delta = traction_after - traction_before
    # ±2 m/s² de variação mapeado em [-1, +1]
    return max(-1.0, min(1.0, delta / 2.0))


def _reward_brake_health(brake_temps: dict | None,
                         brake_temp_max: float = 750.0) -> float:
    """
    Reward baseado na saúde dos freios.
    Todos os freios dentro da faixa saudável = reward positivo.
    Algum freio acima do limite = reward negativo.
    """
    if not brake_temps:
        return 0.0

    overheats = 0
    total_margin = 0.0
    count = 0

    for wheel in ("fl", "fr", "rl", "rr"):
        temp = brake_temps.get(wheel, 0)
        if temp <= 0:
            continue
        count += 1
        margin = (brake_temp_max - temp) / brake_temp_max
        total_margin += margin
        if temp > brake_temp_max:
            overheats += 1

    if count == 0:
        return 0.0

    avg_margin = total_margin / count

    if overheats > 0:
        return max(-1.0, -0.3 * overheats)

    # Todos dentro da faixa — reward proporcional à margem
    return max(0.0, min(1.0, avg_margin))


def classify_setup_efficiency(
    delta_laptime: float,
    delta_consumption: float,
) -> str:
    """
    Classifica a eficiência de um ajuste de setup cruzando lap time e consumo.

    Retorna:
        "EXCELENTE"   — ficou mais rápido E consumiu menos (menos arrasto eficiente)
        "AGRESSIVO"   — ficou mais rápido MAS consumiu mais (mais asa/potência)
        "CONSERVADOR" — consumiu menos MAS ficou mais lento (setup de corrida longa)
        "DESASTROSO"  — ficou mais lento E consumiu mais (arrasto inútil)
        "NEUTRO"      — variação dentro do ruído normal (< 0.1s e < 0.05L)
    """
    fast = delta_laptime < -0.1       # >0.1s mais rápido
    lean = delta_consumption < -0.05  # >0.05L por volta a menos
    slow = delta_laptime > 0.1        # >0.1s mais lento
    heavy = delta_consumption > 0.05  # >0.05L por volta a mais

    if fast and lean:
        return "EXCELENTE"      # menos arrasto + ganho de tempo
    if fast and heavy:
        return "AGRESSIVO"      # mais downforce = mais rápido mas caro
    if slow and lean:
        return "CONSERVADOR"    # economiza combustível mas perde tempo
    if slow and heavy:
        return "DESASTROSO"     # pior em tudo
    return "NEUTRO"


def _reward_brake_health(brake_temps: dict | None,
                         brake_temp_max: float = 750.0) -> float:
    """
    Reward baseado na saúde dos freios.
    Todos os freios dentro da faixa saudável = reward positivo.
    Algum freio acima do limite = reward negativo.
    """
    if not brake_temps:
        return 0.0

    overheats = 0
    total_margin = 0.0
    count = 0

    for wheel in ("fl", "fr", "rl", "rr"):
        temp = brake_temps.get(wheel, 0)
        if temp <= 0:
            continue
        count += 1
        margin = (brake_temp_max - temp) / brake_temp_max
        total_margin += margin
        if temp > brake_temp_max:
            overheats += 1

    if count == 0:
        return 0.0

    avg_margin = total_margin / count

    if overheats > 0:
        return max(-1.0, -0.3 * overheats)

    # Todos dentro da faixa — reward proporcional à margem
    return max(0.0, min(1.0, avg_margin))


def _reward_exit_traction(traction_before: float, traction_after: float) -> float:
    """B2: reward baseado na melhoria da tração na saída da última curva pré-reta.

    Mede a aceleração longitudinal média na zona pre_straight_zone.
    Valor mais alto (mais tração) após ajuste = reward positivo.

    Args:
        traction_before: Aceleração média (m/s²) na zona antes do ajuste.
        traction_after:  Aceleração média (m/s²) na zona depois do ajuste.

    Returns:
        Reward em [-1.0, +1.0]. 0.0 se dados insuficientes.
    """
    if traction_before <= 0 and traction_after <= 0:
        return 0.0

    # Se só temos o valor depois, recompensa proporcional ao valor absoluto
    if traction_before <= 0:
        return max(0.0, min(1.0, traction_after / 10.0))

    delta = traction_after - traction_before
    # ±2 m/s² de variação mapeado em [-1, +1]
    return max(-1.0, min(1.0, delta / 2.0))

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

# Pesos dos critérios de reward (somam 1.0)
REWARD_WEIGHTS = {
    "lap_time": 0.25,          # Redução do tempo de volta
    "temp_balance": 0.15,      # Uniformidade de temperatura I-M-O dos pneus
    "grip": 0.10,              # Aderência média (grip fraction)
    "consistency": 0.10,       # Desvio padrão dos tempos (menor = melhor)
    "user_satisfaction": 0.10, # Feedback direto do usuário
    "tire_wear": 0.10,         # Desgaste equilibrado entre rodas
    "sector_improvement": 0.10,# Melhoria por setor (S1, S2, S3)
    "fuel_efficiency": 0.05,   # Consumo de combustível (menos = melhor)
    "brake_health": 0.05,      # Freios dentro da faixa saudável
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
    brake_temps_after: dict | None = None,
    brake_temp_max: float = 750.0,
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
        brake_temps_after: Dict com temp máxima de freio por roda
        brake_temp_max: Limite de temperatura de freio saudável (°C)

    Returns:
        Reward entre -1.0 e +1.0
    """
    rewards = {}

    # 1. REWARD DE LAP TIME (25%)
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

    # 8. REWARD DE EFICIÊNCIA DE COMBUSTÍVEL (5%)
    rewards["fuel_efficiency"] = _reward_fuel_efficiency(
        fuel_per_lap_before, fuel_per_lap_after
    )

    # 9. REWARD DE SAÚDE DOS FREIOS (5%)
    rewards["brake_health"] = _reward_brake_health(
        brake_temps_after, brake_temp_max
    )

    # Combinar com pesos
    total = sum(
        REWARD_WEIGHTS[key] * rewards.get(key, 0.0)
        for key in REWARD_WEIGHTS
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


def _reward_fuel_efficiency(fuel_before: float,
                            fuel_after: float) -> float:
    """
    Reward baseado na eficiência de combustível.
    Menos consumo por volta = melhor (menos arrasto, melhor aero).
    """
    if fuel_before <= 0 or fuel_after <= 0:
        return 0.0

    delta_pct = (fuel_after - fuel_before) / fuel_before
    # Consumiu menos = bom
    return max(-1.0, min(1.0, -delta_pct * 10.0))


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

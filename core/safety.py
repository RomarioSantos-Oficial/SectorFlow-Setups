"""
safety.py — Safety Guards (Proteções de segurança).

Impede que a IA sugira ajustes perigosos ou absurdos.
Funciona como última barreira antes de qualquer ajuste
ser apresentado ao usuário.

Regras:
1. Delta nunca excede ±max_delta índices de uma vez
2. Valores nunca saem do range min/max do parâmetro
3. Combinações perigosas conhecidas são vetadas
4. Se reward médio das últimas sugestões é muito negativo,
   a IA faz auto-reset para heurísticas
"""

from __future__ import annotations

import logging

logger = logging.getLogger("LMU_VE.safety")


# Combinações perigosas conhecidas no setup de corrida
# Se ambas as condições forem verdadeiras, a sugestão é vetada
DANGEROUS_COMBOS = [
    {
        "name": "Camber extremo + pressão baixa",
        "risk": "Risco de destruir o pneu — apoio excessivo em uma zona com pouco ar",
        "conditions": [
            ("delta_camber_f", "< -3"),   # Camber muito negativo
            ("delta_pressure_f", "< -2"), # E pressão muito baixa
        ],
    },
    {
        "name": "Ride height mínimo + mola dura",
        "risk": "Carro vai bater no chão em cada bump (bottoming violento)",
        "conditions": [
            ("delta_ride_height_f", "< -2"),
            ("delta_spring_f", "> 2"),
        ],
    },
]


def validate_deltas(
    deltas: dict[str, int],
    max_delta: int = 3,
    param_ranges: dict | None = None,
    current_setup: dict | None = None,
) -> tuple[dict[str, int], list[str]]:
    """
    Valida e corrige deltas de ajuste antes de apresentar ao usuário.

    Args:
        deltas: Dict com deltas sugeridos (ex: {"delta_rw": 2, ...})
        max_delta: Limite máximo de ±N índices por ajuste
        param_ranges: Ranges dos parâmetros do carro (do banco)
        current_setup: Setup atual (índices do .svm)

    Returns:
        Tuple (deltas_corrigidos, lista_de_avisos)
    """
    corrected = dict(deltas)
    warnings: list[str] = []

    # 1. Limitar deltas ao máximo permitido
    for key, val in corrected.items():
        if abs(val) > max_delta:
            old_val = val
            corrected[key] = max(-max_delta, min(max_delta, val))
            warnings.append(
                f"⚠️ {key}: delta {old_val} limitado para ±{max_delta} "
                f"(novo valor: {corrected[key]})"
            )

    # 2. Verificar ranges do parâmetro (não sair do min/max do .svm)
    if param_ranges and current_setup:
        for key, delta in corrected.items():
            # Mapear nome do delta para nome do parâmetro
            param_key = _delta_to_param_key(key)
            if param_key and param_key in param_ranges:
                r = param_ranges[param_key]
                current_val = current_setup.get(param_key, 0)
                new_val = current_val + delta

                min_idx = r.get("min_index", 0)
                max_idx = r.get("max_index", 999)

                if new_val < min_idx:
                    corrected[key] = min_idx - current_val
                    warnings.append(
                        f"⚠️ {key}: clipado no mínimo do parâmetro "
                        f"(índice {min_idx})"
                    )
                elif new_val > max_idx:
                    corrected[key] = max_idx - current_val
                    warnings.append(
                        f"⚠️ {key}: clipado no máximo do parâmetro "
                        f"(índice {max_idx})"
                    )

    # 3. Validar magnitude total (evitar sugestões que mudam tudo de uma vez)
    total_magnitude = sum(abs(v) for v in corrected.values())
    max_total_magnitude = 30
    if total_magnitude > max_total_magnitude:
        scale = max_total_magnitude / total_magnitude
        corrected = {k: int(round(v * scale)) for k, v in corrected.items()}
        # Remover os que ficaram zero após escala
        corrected = {k: v for k, v in corrected.items() if v != 0}
        warnings.append(
            f"⚠️ Magnitude total ({total_magnitude}) excede limite "
            f"({max_total_magnitude}). Deltas escalonados proporcionalmente."
        )

    # 4. Verificar combinações perigosas
    for combo in DANGEROUS_COMBOS:
        all_match = True
        for param, condition in combo["conditions"]:
            val = corrected.get(param, 0)
            if not _eval_condition(val, condition):
                all_match = False
                break
        if all_match:
            warnings.append(
                f"🚫 Combinação perigosa vetada: {combo['name']}. "
                f"Risco: {combo['risk']}. Deltas zerados."
            )
            for param, _ in combo["conditions"]:
                corrected[param] = 0

    # 4. Remover deltas zerados (nenhum ajuste)
    corrected = {k: v for k, v in corrected.items() if v != 0}

    return corrected, warnings


def should_reset_to_heuristics(recent_rewards: list[float],
                               threshold: float = -0.3,
                               window: int = 5) -> bool:
    """
    Verifica se a IA deve fazer auto-reset para heurísticas.

    Se o reward médio das últimas N sugestões é muito negativo,
    a IA está "perdida" e deve voltar para regras determinísticas.

    Args:
        recent_rewards: Últimos N rewards obtidos
        threshold: Se a média for menor que isso, resetar
        window: Número de rewards a considerar

    Returns:
        True se deve resetar para heurísticas
    """
    if len(recent_rewards) < window:
        return False

    recent = recent_rewards[-window:]
    avg = sum(recent) / len(recent)

    if avg < threshold:
        logger.warning(
            "Auto-reset: reward médio (%.2f) abaixo do limiar (%.2f). "
            "Voltando para heurísticas.", avg, threshold
        )
        return True
    return False


def compute_confidence(total_samples: int) -> float:
    """
    Calcula a confiança do modelo baseada na quantidade de dados.

    0-29 amostras   → 0%   (só heurísticas)
    30-99           → 20-40%
    100-299         → 40-70%
    300-499         → 70-85%
    500+            → 85-95% (nunca 100%)
    """
    if total_samples < 30:
        return 0.0
    if total_samples < 100:
        return 0.2 + (total_samples - 30) / 70 * 0.2
    if total_samples < 300:
        return 0.4 + (total_samples - 100) / 200 * 0.3
    if total_samples < 500:
        return 0.7 + (total_samples - 300) / 200 * 0.15
    return min(0.95, 0.85 + (total_samples - 500) / 5000 * 0.1)


def _delta_to_param_key(delta_name: str) -> str | None:
    """Converte nome de delta para chave do parâmetro no .svm."""
    mapping = {
        "delta_rw": "REARWING.RWSetting",
        "delta_spring_f": "FRONTLEFT.SpringSetting",
        "delta_spring_r": "REARLEFT.SpringSetting",
        "delta_camber_f": "FRONTLEFT.CamberSetting",
        "delta_camber_r": "REARLEFT.CamberSetting",
        "delta_pressure_f": "FRONTLEFT.PressureSetting",
        "delta_pressure_r": "REARLEFT.PressureSetting",
        "delta_brake_press": "CONTROLS.BrakePressureSetting",
        "delta_arb_f": "SUSPENSION.FrontAntiSwaySetting",
        "delta_arb_r": "SUSPENSION.RearAntiSwaySetting",
    }
    return mapping.get(delta_name)


def _eval_condition(value: int, condition: str) -> bool:
    """Avalia uma condição simples como '< -3' ou '> 2'."""
    parts = condition.split()
    if len(parts) != 2:
        return False
    op, threshold = parts[0], float(parts[1])
    if op == "<":
        return value < threshold
    if op == ">":
        return value > threshold
    if op == "<=":
        return value <= threshold
    if op == ">=":
        return value >= threshold
    return False

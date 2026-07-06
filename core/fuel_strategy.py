from __future__ import annotations

from typing import Any


def estimate_fuel_consumption(
    history: list[dict[str, Any]], recent_window: int = 3
) -> dict[str, Any]:
    """Estima consumo de combustível por volta usando apenas voltas válidas e sem pit laps."""
    consumption_samples: list[float] = []
    ignored_laps = 0

    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]

        curr_context = (curr.get("fuel_context") or "").lower()
        prev_context = (prev.get("fuel_context") or "").lower()
        if not curr.get("valid", True) or curr_context in {
            "pit",
            "pit_exit",
            "refuel",
            "refueling",
        }:
            ignored_laps += 1
            continue

        if not prev.get("valid", True) or prev_context in {
            "pit",
            "pit_exit",
            "refuel",
            "refueling",
        }:
            continue

        prev_fuel = prev.get("features", {}).get("fuel", 0) or prev.get(
            "features", {}
        ).get("fuel_start", 0)
        curr_fuel = curr.get("features", {}).get("fuel", 0) or curr.get(
            "features", {}
        ).get("fuel_start", 0)

        if prev_fuel > 0 and curr_fuel > 0 and prev_fuel > curr_fuel:
            delta = prev_fuel - curr_fuel
            if 0.1 < delta < 20:
                consumption_samples.append(delta)
            else:
                ignored_laps += 1
        else:
            ignored_laps += 1

    recent = (
        consumption_samples[-recent_window:]
        if len(consumption_samples) >= recent_window
        else consumption_samples
    )
    fuel_per_lap = round(sum(recent) / len(recent), 3) if recent else 0.0

    return {
        "fuel_per_lap": fuel_per_lap,
        "samples": recent,
        "ignored_laps": ignored_laps,
    }

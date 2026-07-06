from core.fuel_strategy import estimate_fuel_consumption


def test_ignores_pit_lap_and_invalid_laps():
    history = [
        {"valid": True, "features": {"fuel": 80.0}, "fuel_context": "normal"},
        {"valid": True, "features": {"fuel": 76.0}, "fuel_context": "normal"},
        {"valid": False, "features": {"fuel": 74.0}, "fuel_context": "normal"},
        {"valid": True, "features": {"fuel": 70.0}, "fuel_context": "pit"},
        {"valid": True, "features": {"fuel": 67.0}, "fuel_context": "normal"},
        {"valid": True, "features": {"fuel": 63.0}, "fuel_context": "normal"},
    ]

    result = estimate_fuel_consumption(history, recent_window=3)

    assert result["fuel_per_lap"] == 4.0
    assert result["samples"] == [4.0, 4.0]
    assert result["ignored_laps"] == 2


def test_returns_zero_when_not_enough_valid_samples():
    history = [
        {"valid": True, "features": {"fuel": 70.0}, "fuel_context": "normal"},
        {"valid": True, "features": {"fuel": 69.0}, "fuel_context": "pit"},
    ]

    result = estimate_fuel_consumption(history)

    assert result["fuel_per_lap"] == 0.0
    assert result["samples"] == []
    assert result["ignored_laps"] == 1

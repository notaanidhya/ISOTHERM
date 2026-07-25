from src.config import SAFETY_BOUNDS, MIN_DEADBAND

def clamp_setpoint(value: float, sp_type: str) -> float:
    """Clamps a setpoint value to physically safe range (heating 16-24°C, cooling 22-30°C)."""
    lo, hi = SAFETY_BOUNDS.get(sp_type, (16.0, 30.0))
    try:
        val = float(value)
        return max(lo, min(hi, val))
    except (ValueError, TypeError):
        return 21.0 if sp_type == "heating" else 24.0

def enforce_deadband(heating_c: float, cooling_c: float, min_gap: float = MIN_DEADBAND) -> tuple[float, float]:
    """Enforces minimum deadband gap between heating and cooling setpoints to prevent HVAC fighting."""
    if cooling_c < heating_c + min_gap:
        cooling_c = heating_c + min_gap
    return heating_c, cooling_c

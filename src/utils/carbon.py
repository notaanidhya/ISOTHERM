# Time-of-Use Electricity Rates ($/kWh)
# Off-Peak (22:00-08:00): $0.05 / kWh
# Mid-Peak (08:00-12:00, 18:00-22:00): $0.10 / kWh
# Peak     (12:00-18:00): $0.15 / kWh
TOU_RATES = {
    **{h: 0.05 for h in range(0, 8)},
    **{h: 0.10 for h in range(8, 12)},
    **{h: 0.15 for h in range(12, 18)},
    **{h: 0.10 for h in range(18, 22)},
    **{h: 0.05 for h in range(22, 24)},
}

# Hourly Grid Carbon Intensity (gCO2/kWh)
CARBON_INTENSITY = {
    **{h: 320 for h in range(0, 6)},
    **{h: 380 for h in range(6, 9)},
    **{h: 410 for h in range(9, 12)},
    **{h: 450 for h in range(12, 15)},
    **{h: 470 for h in range(15, 18)},
    **{h: 430 for h in range(18, 21)},
    **{h: 350 for h in range(21, 24)},
}

def get_tou_price(hour_of_day: int) -> float:
    """Returns Time-of-Use electricity rate ($/kWh) for hour of day (0-23)."""
    return TOU_RATES.get(int(hour_of_day) % 24, 0.10)

def get_carbon_intensity(hour_of_day: int) -> float:
    """Returns grid carbon intensity (gCO2/kWh) for hour of day (0-23)."""
    return CARBON_INTENSITY.get(int(hour_of_day) % 24, 400.0)

def calculate_hourly_cost(kwh: float, hour_of_day: int) -> float:
    """Calculates electricity cost ($) for a given kWh consumption at a specific hour."""
    return float(kwh) * get_tou_price(hour_of_day)

def calculate_hourly_carbon(kwh: float, hour_of_day: int) -> float:
    """Calculates carbon emissions (kg CO2) for a given kWh consumption at a specific hour."""
    # gCO2 -> kgCO2 (divide by 1000)
    return (float(kwh) * get_carbon_intensity(hour_of_day)) / 1000.0

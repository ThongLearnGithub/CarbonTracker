from math import floor
from typing import Mapping, Sequence, Tuple

BASELINE_EMISSION_FACTOR_KG_PER_KM = 0.5
CREDITS_PER_KG_CO2_SAVED = 1.0

DEFAULT_EMISSION_FACTORS = {
    "Walking": 0.0,
    "Bicycle": 0.0,
    "E-Bus": 0.05,
    "Bus": 0.1,
    "Petrol Bus": 0.1,
    "Car": 0.113,
    "Petrol Car": 0.113,
    "E-Motorbike": 0.02,
    "Motorbike": 0.04,
    "Petrol Motorbike": 0.04,
    "E-Car": 0.07,
}

MODE_ALIASES = {
    "Bus": "Petrol Bus",
    "Car": "Petrol Car",
    "Motorbike": "Petrol Motorbike",
}


def emission_factor_for_mode(
    mode: str,
    configured_factors: Mapping[str, float],
) -> float:
    canonical_mode = MODE_ALIASES.get(mode, mode)
    factor = configured_factors.get(mode)
    if factor is None:
        factor = configured_factors.get(canonical_mode)
    if factor is None:
        factor = DEFAULT_EMISSION_FACTORS.get(mode)
    if factor is None:
        factor = DEFAULT_EMISSION_FACTORS.get(canonical_mode)
    if factor is None:
        raise ValueError(f"No CO2 emission factor is configured for transport mode '{mode}'.")
    if factor < 0:
        raise ValueError(f"CO2 emission factor for '{mode}' cannot be negative.")
    return factor


def calculate_trip_metrics(
    distance_km: float,
    transport_modes: Sequence[str],
    configured_factors: Mapping[str, float],
) -> Tuple[float, float, int]:
    if distance_km < 0:
        raise ValueError("Trip distance cannot be negative.")
    if not transport_modes:
        raise ValueError("At least one transport mode is required.")

    distance_per_mode = distance_km / len(transport_modes)
    co2_emitted_kg = 0.0
    co2_saved_kg = 0.0
    for mode in transport_modes:
        factor = emission_factor_for_mode(mode, configured_factors)
        co2_emitted_kg += factor * distance_per_mode
        co2_saved_kg += max(
            0.0,
            BASELINE_EMISSION_FACTOR_KG_PER_KM - factor,
        ) * distance_per_mode

    credits_earned = floor(co2_saved_kg * CREDITS_PER_KG_CO2_SAVED + 0.5)
    return co2_emitted_kg, co2_saved_kg, credits_earned

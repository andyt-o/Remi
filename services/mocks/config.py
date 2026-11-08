"""Latency and simulation configuration for restaurant integration mocks.

Allows customization of baseline delays, jitter, failure rates, and preset
profiles (e.g., local LAN POS vs cloud inventory API vs degraded network).
"""

import os
from typing import NamedTuple


class LatencyProfile(NamedTuple):
    min_ms: float
    max_ms: float
    failure_rate: float = 0.0  # 0.0 to 1.0 probability of 500 error


# Preset profiles for testing different operational scenarios
PRESET_PROFILES: dict[str, dict[str, LatencyProfile]] = {
    # Ideal local LAN / edge setup (typical on-premise Oracle Simphony workstation)
    "low_latency": {
        "oracle_pos": LatencyProfile(min_ms=15.0, max_ms=45.0),
        "seven_shifts": LatencyProfile(min_ms=30.0, max_ms=70.0),
        "marketman": LatencyProfile(min_ms=40.0, max_ms=90.0),
    },
    # Typical multi-vendor cloud SaaS environment over broadband
    "typical_cloud": {
        "oracle_pos": LatencyProfile(min_ms=60.0, max_ms=140.0),
        "seven_shifts": LatencyProfile(min_ms=90.0, max_ms=180.0),
        "marketman": LatencyProfile(min_ms=100.0, max_ms=220.0),
    },
    # Peak rush hour / congested Wi-Fi / busy cloud vendor API
    "rush_hour_degraded": {
        "oracle_pos": LatencyProfile(min_ms=180.0, max_ms=450.0, failure_rate=0.02),
        "seven_shifts": LatencyProfile(min_ms=250.0, max_ms=600.0, failure_rate=0.03),
        "marketman": LatencyProfile(min_ms=300.0, max_ms=800.0, failure_rate=0.05),
    },
}

# Active profile selected via environment or default to "typical_cloud"
ACTIVE_PRESET: str = os.getenv("REMI_MOCK_PROFILE", "typical_cloud")

# Default latency bounds overrideable per-vendor via environment variables
# Format: MIN_MS and MAX_MS (e.g., ORACLE_POS_MIN_LATENCY_MS=50)
def get_service_profile(service_name: str) -> LatencyProfile:
    preset = PRESET_PROFILES.get(ACTIVE_PRESET, PRESET_PROFILES["typical_cloud"])
    base = preset.get(service_name, LatencyProfile(min_ms=50.0, max_ms=120.0))

    env_min = os.getenv(f"{service_name.upper()}_MIN_LATENCY_MS")
    env_max = os.getenv(f"{service_name.upper()}_MAX_LATENCY_MS")
    env_failure = os.getenv(f"{service_name.upper()}_FAILURE_RATE")

    return LatencyProfile(
        min_ms=float(env_min) if env_min is not None else base.min_ms,
        max_ms=float(env_max) if env_max is not None else base.max_ms,
        failure_rate=float(env_failure) if env_failure is not None else base.failure_rate,
    )

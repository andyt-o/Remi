"""Main application for Remi Mock Restaurant Integrations."""

from fastapi import FastAPI
from mocks.config import ACTIVE_PRESET, PRESET_PROFILES
from mocks.routers.marketman import router as marketman_router
from mocks.routers.oracle_pos import router as oracle_router
from mocks.routers.seven_shifts import router as seven_shifts_router

app = FastAPI(
    title="Remi Restaurant Integrations Mock Server",
    description="Simulates Oracle POS, 7shifts, and MarketMan with realistic configurable latency and failure rates.",
    version="0.1.0",
)

app.include_router(oracle_router)
app.include_router(seven_shifts_router)
app.include_router(marketman_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "remi-mocks"}


@app.get("/simulation-config")
async def get_simulation_status() -> dict:
    return {
        "active_preset": ACTIVE_PRESET,
        "available_presets": list(PRESET_PROFILES.keys()),
        "current_preset_profiles": {
            k: {
                "min_ms": v.min_ms,
                "max_ms": v.max_ms,
                "failure_rate": v.failure_rate,
            }
            for k, v in PRESET_PROFILES.get(ACTIVE_PRESET, {}).items()
        },
    }

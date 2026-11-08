"""Simulation utilities for latency injection and synthetic failures."""

import asyncio
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException
from mocks.config import LatencyProfile, get_service_profile


async def apply_simulated_latency(profile: LatencyProfile) -> float:
    """Sleeps for a random duration within the profile range and handles failure injection."""
    if profile.failure_rate > 0.0 and random.random() < profile.failure_rate:
        # Simulate slight delay before connection drops / 500 error
        await asyncio.sleep(profile.min_ms / 1000.0)
        raise HTTPException(
            status_code=500,
            detail="Simulated upstream service timeout/error (chaos engineering)",
        )

    delay_ms = random.uniform(profile.min_ms, profile.max_ms)
    await asyncio.sleep(delay_ms / 1000.0)
    return delay_ms


def simulate_latency(service_name: str) -> Callable[..., Any]:
    """Decorator for route handlers to automatically inject vendor-specific latency."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            profile = get_service_profile(service_name)
            start = time.perf_counter()
            await apply_simulated_latency(profile)
            response = await func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if isinstance(response, dict):
                response["_debug_latency_ms"] = round(elapsed_ms, 2)
                response["_simulated_vendor"] = service_name
            return response
        return wrapper
    return decorator

"""Mock 7shifts API endpoints for labor, shifts, and restaurant personnel."""

from typing import Any
from fastapi import APIRouter
from mocks.simulator import simulate_latency

router = APIRouter(prefix="/7shifts", tags=["7shifts"])

MOCK_WORKERS = [
    {"user_id": 101, "name": "Dave Miller", "role": "Head Chef", "department": "Kitchen", "status": "active"},
    {"user_id": 102, "name": "Elena Rostova", "role": "Shift Lead", "department": "Front of House", "status": "active"},
    {"user_id": 103, "name": "Marcus Vance", "role": "Bartender", "department": "Bar", "status": "active"},
    {"user_id": 104, "name": "Sarah Connor", "role": "Line Cook", "department": "Kitchen", "status": "break"},
]


@router.get("/v2/who_is_working_now")
@simulate_latency("seven_shifts")
async def who_is_working_now() -> dict[str, Any]:
    """Returns employees currently clocked into the shift."""
    return {
        "status": "success",
        "total_active": len([w for w in MOCK_WORKERS if w["status"] == "active"]),
        "workers": MOCK_WORKERS,
    }


@router.get("/v2/shifts/today")
@simulate_latency("seven_shifts")
async def get_today_shifts() -> dict[str, Any]:
    return {
        "status": "success",
        "shifts": [
            {"user": "Dave Miller", "start": "10:00 AM", "end": "6:00 PM", "station": "Kitchen Station 1"},
            {"user": "Elena Rostova", "start": "11:00 AM", "end": "7:00 PM", "station": "Host Stand / Floor"},
            {"user": "Marcus Vance", "start": "4:00 PM", "end": "11:30 PM", "station": "Main Bar"},
        ]
    }

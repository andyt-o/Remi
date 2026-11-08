"""Mock 7shifts API endpoints for labor, shifts, and restaurant personnel."""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel
from mocks.simulator import simulate_latency

router = APIRouter(prefix="/7shifts", tags=["7shifts"])

MOCK_WORKERS = [
    {"user_id": 101, "name": "Dave Miller", "role": "Head Chef", "department": "Kitchen", "status": "active", "account_status": "active"},
    {"user_id": 102, "name": "Elena Rostova", "role": "Shift Lead", "department": "Front of House", "status": "active", "account_status": "active"},
    {"user_id": 103, "name": "Marcus Vance", "role": "Bartender", "department": "Bar", "status": "active", "account_status": "active"},
    {"user_id": 104, "name": "Sarah Connor", "role": "Line Cook", "department": "Kitchen", "status": "break", "account_status": "active"},
    {"user_id": 105, "name": "Jordan Lee", "role": "Server", "department": "Front of House", "status": "active", "account_status": "active"},
    {"user_id": 106, "name": "Taylor Morgan", "role": "Manager", "department": "Management", "status": "active", "account_status": "active"},
]


TODAY_SHIFTS: list[dict[str, Any]] = [
    {"shift_id": "SH-101", "user": "Dave Miller", "user_id": 101, "start": "10:00 AM", "end": "6:00 PM", "station": "Kitchen Station 1", "version": 1},
    {"shift_id": "SH-102", "user": "Elena Rostova", "user_id": 102, "start": "11:00 AM", "end": "7:00 PM", "station": "Host Stand / Floor", "version": 1},
    {"shift_id": "SH-103", "user": "Marcus Vance", "user_id": 103, "start": "4:00 PM", "end": "11:30 PM", "station": "Main Bar", "version": 1},
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


@router.get("/v2/users/{user_id}")
@simulate_latency("seven_shifts")
async def get_user(user_id: int) -> dict[str, Any]:
    """Return the mock staff account used as the MCP client's identity."""
    worker = next((w for w in MOCK_WORKERS if w["user_id"] == user_id), None)
    if worker is None:
        return {"status": "not_found", "user_id": user_id}
    return {"status": "success", "user": worker}


@router.get("/v2/shifts/today")
@simulate_latency("seven_shifts")
async def get_today_shifts() -> dict[str, Any]:
    return {
        "status": "success",
        "shifts": TODAY_SHIFTS,
    }


class UpdateShiftRequest(BaseModel):
    expected_version: int
    start: str | None = None
    end: str | None = None
    station: str | None = None


@router.put("/v2/shifts/{shift_id}")
@simulate_latency("seven_shifts")
async def update_shift(shift_id: str, payload: UpdateShiftRequest) -> dict[str, Any]:
    """Optimistic concurrency: require matching expected_version to prevent overlapping writes."""
    shift = next((s for s in TODAY_SHIFTS if s["shift_id"] == shift_id), None)
    if not shift:
        return {"status": "not_found", "message": f"Shift {shift_id} not found."}

    if shift["version"] != payload.expected_version:
        return {
            "status": "conflict",
            "message": (
                f"Shift {shift_id} was already updated by another manager (current version: {shift['version']}, "
                f"expected: {payload.expected_version}). Please refresh before updating."
            ),
            "current_shift": shift,
        }

    if payload.start:
        shift["start"] = payload.start
    if payload.end:
        shift["end"] = payload.end
    if payload.station:
        shift["station"] = payload.station

    shift["version"] += 1
    return {
        "status": "success",
        "message": f"Shift {shift_id} successfully updated to version {shift['version']}.",
        "shift": shift,
    }

"""Mock notification and SMS gateway endpoints."""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from mocks.simulator import simulate_latency

router = APIRouter(prefix="/notifications", tags=["Notifications"])

SENT_NOTIFICATIONS: list[dict[str, Any]] = []


class SMSRequest(BaseModel):
    phone_number: str
    carrier: str
    gateway_address: str
    message: str


@router.post("/sms")
@simulate_latency("seven_shifts")
async def send_mock_sms(payload: SMSRequest) -> dict[str, Any]:
    """Logs sent SMS text messages and returns simulated delivery confirmation."""
    record = {
        "id": f"sms_{len(SENT_NOTIFICATIONS) + 1}",
        "phone_number": payload.phone_number,
        "carrier": payload.carrier,
        "gateway_address": payload.gateway_address,
        "message": payload.message,
        "delivered": True,
    }
    SENT_NOTIFICATIONS.append(record)
    return {
        "status": "delivered",
        "provider": "mock_sms_gateway",
        "notification": record,
    }


@router.get("/sms/history")
async def get_sms_history() -> dict[str, Any]:
    return {"total": len(SENT_NOTIFICATIONS), "messages": SENT_NOTIFICATIONS}

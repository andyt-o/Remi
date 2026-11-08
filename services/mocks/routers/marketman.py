"""Mock MarketMan API endpoints for restaurant inventory & ingredient availability."""

from typing import Any
from datetime import date, timedelta
from fastapi import APIRouter
from pydantic import BaseModel, Field
from mocks.simulator import simulate_latency

router = APIRouter(prefix="/marketman", tags=["MarketMan"])

# Current live inventory items and threshold limits
INVENTORY = {
    "beef_patty": {"name": "Prime Beef Patty 6oz", "on_hand": 34, "unit": "count", "is_86d": False},
    "brioche_bun": {"name": "Brioche Bun", "on_hand": 42, "unit": "count", "is_86d": False},
    "truffle_oil": {"name": "White Truffle Oil", "on_hand": 2, "unit": "bottles", "is_86d": False},
    "chicken_breast": {"name": "Free-range Chicken Breast", "on_hand": 0, "unit": "count", "is_86d": True},
    "draft_ipa_keg": {"name": "Local IPA Keg", "on_hand": 18, "unit": "pints", "is_86d": False},
}

# Deterministic receiving history for the isolated-delivery-analysis demo.
# These records are illustrative mock data, not live MarketMan purchase history.
_TODAY = date.today()
_ITEM_KEYS = list(INVENTORY)
RECEIVING_HISTORY = [
    {
        "delivery_id": f"RCV-{i:04d}",
        "received_on": (_TODAY - timedelta(days=7 * ((i * 5) % 52 + 1))).isoformat(),
        "item_key": _ITEM_KEYS[i % len(_ITEM_KEYS)],
        "quantity": 12 + ((i * 17) % 39),
        "unit_cost": round(3.25 + ((i * 11) % 180) / 100, 2),
    }
    for i in range(1, 53)
]


class DepleteRequest(BaseModel):
    item_key: str
    quantity: int = Field(default=1, ge=1)


@router.get("/v1/inventory/items")
@simulate_latency("marketman")
async def get_inventory() -> dict[str, Any]:
    return {"status": "success", "inventory": INVENTORY}


@router.get("/v1/receiving/ytd")
@simulate_latency("marketman")
async def get_ytd_receiving() -> dict[str, Any]:
    """Return deterministic year-to-date receiving records for the demo report."""
    year_start = date(_TODAY.year, 1, 1)
    records = [record for record in RECEIVING_HISTORY if record["received_on"] >= year_start.isoformat()]
    return {
        "status": "success",
        "year": _TODAY.year,
        "source": "illustrative_mock_history",
        "records": records,
    }


@router.get("/v1/inventory/check-availability/{item_key}")
@simulate_latency("marketman")
async def check_availability(item_key: str) -> dict[str, Any]:
    item = INVENTORY.get(item_key)
    if not item:
        return {"status": "not_found", "available": False, "item_key": item_key}
    return {
        "status": "success",
        "item_key": item_key,
        "name": item["name"],
        "available": not item["is_86d"] and item["on_hand"] > 0,
        "on_hand": item["on_hand"],
        "is_86d": item["is_86d"],
    }


@router.post("/v1/inventory/deplete")
@simulate_latency("marketman")
async def deplete_inventory(payload: DepleteRequest) -> dict[str, Any]:
    item = INVENTORY.get(payload.item_key)
    if not item:
        return {"status": "not_found", "message": f"Item {payload.item_key} not found"}

    if item["on_hand"] < payload.quantity:
        item["is_86d"] = True
        return {
            "status": "insufficient_stock",
            "message": f"Requested {payload.quantity}, only {item['on_hand']} remaining.",
            "on_hand": item["on_hand"],
        }

    item["on_hand"] -= payload.quantity
    if item["on_hand"] == 0:
        item["is_86d"] = True

    return {
        "status": "success",
        "message": f"Depleted {payload.quantity} units of {item['name']}",
        "remaining_on_hand": item["on_hand"],
        "is_86d": item["is_86d"],
    }

"""Mock Oracle MICROS Simphony POS API endpoints."""

import uuid
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from mocks.simulator import simulate_latency

router = APIRouter(prefix="/oracle-pos", tags=["Oracle POS"])

# In-memory mock database of POS checks and menu items
MOCK_MENU = [
    {"item_id": "101", "name": "Classic Cheeseburger", "price": 14.50, "category": "Entrees", "icon_url": "/menu/entree.svg"},
    {"item_id": "102", "name": "Truffle Fries", "price": 8.00, "category": "Sides", "icon_url": "/menu/side.svg"},
    {"item_id": "103", "name": "Crispy Chicken Sandwich", "price": 13.75, "category": "Entrees", "icon_url": "/menu/entree.svg"},
    {"item_id": "104", "name": "Caesar Salad", "price": 11.00, "category": "Salads", "icon_url": "/menu/salad.svg"},
    {"item_id": "201", "name": "Draft IPA", "price": 7.50, "category": "Beverages", "icon_url": "/menu/drink.svg"},
]

OPEN_CHECKS: dict[str, dict[str, Any]] = {}


class OrderItemRequest(BaseModel):
    item_id: str
    quantity: int = Field(default=1, ge=1)
    special_instructions: str | None = None


class CreateCheckRequest(BaseModel):
    table_number: int | None = None
    order_type: str = "dine_in"  # dine_in, takeout, delivery
    items: list[OrderItemRequest]


@router.get("/menu")
@simulate_latency("oracle_pos")
async def get_menu() -> dict[str, Any]:
    return {"status": "success", "items": MOCK_MENU}


@router.post("/checks")
@simulate_latency("oracle_pos")
async def create_check(payload: CreateCheckRequest) -> dict[str, Any]:
    # Read-before-write validation: check item availability in live MarketMan inventory
    from mocks.routers.marketman import INVENTORY

    # Mapping of menu item to inventory ingredient key
    item_to_ingredient = {
        "101": "beef_patty",
        "102": "truffle_oil",
        "103": "chicken_breast",
    }

    for req_item in payload.items:
        ing_key = item_to_ingredient.get(req_item.item_id)
        if ing_key and ing_key in INVENTORY:
            stock = INVENTORY[ing_key]
            if stock.get("is_86d") or stock.get("on_hand", 0) < req_item.quantity:
                return {
                    "status": "item_86d",
                    "message": f"Cannot submit order: {stock['name']} is 86'd (out of stock).",
                    "item_id": req_item.item_id,
                }

    check_id = f"CHK-{uuid.uuid4().hex[:6].upper()}"
    total = 0.0
    detailed_items = []

    menu_lookup = {item["item_id"]: item for item in MOCK_MENU}
    for req_item in payload.items:
        menu_item = menu_lookup.get(req_item.item_id)
        if menu_item:
            line_total = menu_item["price"] * req_item.quantity
            total += line_total
            detailed_items.append({
                "item_id": req_item.item_id,
                "name": menu_item["name"],
                "price": menu_item["price"],
                "quantity": req_item.quantity,
                "special_instructions": req_item.special_instructions,
                "line_total": round(line_total, 2),
            })

    check_record = {
        "check_id": check_id,
        "table_number": payload.table_number,
        "order_type": payload.order_type,
        "status": "fired_to_kitchen",
        "subtotal": round(total, 2),
        "tax": round(total * 0.0825, 2),
        "total": round(total * 1.0825, 2),
        "items": detailed_items,
    }
    OPEN_CHECKS[check_id] = check_record

    return {
        "status": "success",
        "message": "Order check opened and sent to kitchen printer",
        "check": check_record,
    }


@router.get("/checks/{check_id}")
@simulate_latency("oracle_pos")
async def get_check(check_id: str) -> dict[str, Any]:
    check = OPEN_CHECKS.get(check_id)
    if not check:
        return {"status": "not_found", "message": f"Check {check_id} not found"}
    return {"status": "success", "check": check}

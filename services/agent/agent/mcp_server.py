"""MCP tools for the Remi restaurant mock integrations.

Run as a local MCP server with:
    uv run python -m agent.mcp_server

The server uses stdio transport so an agent runtime (including one running in
Daytona) can connect to it as an MCP client. Configure MOCK_POS_BASE_URL to a
URL reachable from that runtime.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("remi-restaurant-tools")

MANAGER_ROLES = {"manager"}


def _base_url() -> str:
    return os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")


def _account_id() -> int:
    try:
        return int(os.getenv("REMI_MCP_ACCOUNT_ID", "105"))
    except ValueError as exc:
        raise ValueError("REMI_MCP_ACCOUNT_ID must be an integer") from exc


async def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    timeout = httpx.Timeout(5.0, connect=1.0)
    async with httpx.AsyncClient(base_url=_base_url(), timeout=timeout) as client:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()


async def _account() -> dict[str, Any]:
    result = await _request("GET", f"/7shifts/v2/users/{_account_id()}")
    if result.get("status") != "success" or not isinstance(result.get("user"), dict):
        raise PermissionError("Configured MCP account was not found in the mock staff directory")
    return result["user"]


async def _require_active_account() -> dict[str, Any]:
    account = await _account()
    if account.get("account_status") != "active":
        raise PermissionError("This staff account is disabled")
    return account


async def _require_manager() -> dict[str, Any]:
    account = await _require_active_account()
    role = str(account.get("role", "")).strip().lower()
    if role not in MANAGER_ROLES:
        raise PermissionError("This MCP tool requires a manager account")
    return account


@mcp.tool()
async def get_my_account_status() -> dict[str, Any]:
    """Show which mock staff account this MCP client runs as and its status."""
    account = await _account()
    return {
        "user_id": account["user_id"],
        "name": account["name"],
        "role": account["role"],
        "department": account["department"],
        "shift_status": account["status"],
        "account_status": account["account_status"],
        "access_tier": "manager" if str(account["role"]).lower() in MANAGER_ROLES else "server",
    }


@mcp.tool()
async def get_menu() -> dict[str, Any]:
    """Get the restaurant's current menu and prices from the mock POS."""
    await _require_active_account()
    return await _request("GET", "/oracle-pos/menu")


@mcp.tool()
async def get_inventory() -> dict[str, Any]:
    """Get current inventory and 86'd status from the mock inventory system."""
    await _require_manager()
    return await _request("GET", "/marketman/v1/inventory/items")


@mcp.tool()
async def check_item_availability(item_key: str) -> dict[str, Any]:
    """Check if an ingredient or beverage is currently available."""
    await _require_active_account()
    return await _request(
        "GET", f"/marketman/v1/inventory/check-availability/{quote(item_key, safe='')}"
    )


@mcp.tool()
async def get_staff_working_now() -> dict[str, Any]:
    """(Manager only) Get the staff roster, roles, and account/shift statuses."""
    await _require_manager()
    return await _request("GET", "/7shifts/v2/who_is_working_now")


@mcp.tool()
async def get_today_shifts() -> dict[str, Any]:
    """(Manager only) Get today's scheduled shifts from the mock scheduling system."""
    await _require_manager()
    return await _request("GET", "/7shifts/v2/shifts/today")


@mcp.tool()
async def get_staff_account_status(user_id: int) -> dict[str, Any]:
    """(Manager only) Look up a staff account's role and account/shift status."""
    await _require_manager()
    return await _request("GET", f"/7shifts/v2/users/{user_id}")


@mcp.tool()
async def get_order_check(check_id: str) -> dict[str, Any]:
    """Look up an order check by the check ID returned from create_order_check."""
    await _require_active_account()
    if not check_id.startswith("CHK-") or len(check_id) > 32:
        raise ValueError("check_id must be a valid mock POS check ID")
    return await _request("GET", f"/oracle-pos/checks/{quote(check_id, safe='')}")


@mcp.tool()
async def deplete_inventory(item_key: str, quantity: int = 1) -> dict[str, Any]:
    """(Manager only) Decrease mock inventory for a simulated stock movement."""
    await _require_manager()
    if not item_key:
        raise ValueError("item_key is required")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    return await _request(
        "POST",
        "/marketman/v1/inventory/deplete",
        json={"item_key": item_key, "quantity": quantity},
    )


@mcp.tool()
async def create_order_check(
    items: list[dict[str, Any]],
    order_type: str = "takeout",
    table_number: int | None = None,
) -> dict[str, Any]:
    """Submit an order to the mock POS.

    Each item must contain item_id and quantity; special_instructions is optional.
    This creates a check and fires it to the mock kitchen. Use only after the
    caller has confirmed the complete order.
    """
    await _require_active_account()
    if order_type not in {"dine_in", "takeout", "delivery"}:
        raise ValueError("order_type must be dine_in, takeout, or delivery")
    if not items:
        raise ValueError("items must contain at least one order item")
    payload_items: list[dict[str, Any]] = []
    for item in items:
        item_id = item.get("item_id")
        quantity = item.get("quantity", 1)
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("each item must include a valid item_id")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValueError("each item quantity must be a positive integer")
        payload_item: dict[str, Any] = {"item_id": item_id, "quantity": quantity}
        instruction = item.get("special_instructions")
        if instruction is not None:
            if not isinstance(instruction, str) or len(instruction) > 500:
                raise ValueError("special_instructions must be a string of at most 500 characters")
            payload_item["special_instructions"] = instruction
        payload_items.append(payload_item)

    menu = await _request("GET", "/oracle-pos/menu")
    valid_item_ids = {
        entry.get("item_id") for entry in menu.get("items", []) if isinstance(entry, dict)
    }
    unknown_items = [item["item_id"] for item in payload_items if item["item_id"] not in valid_item_ids]
    if unknown_items:
        raise ValueError(f"Unknown menu item_id(s): {', '.join(unknown_items)}")

    return await _request(
        "POST",
        "/oracle-pos/checks",
        json={"items": payload_items, "order_type": order_type, "table_number": table_number},
    )


@mcp.tool()
async def update_shift_schedule(
    shift_id: str,
    expected_version: int,
    start: str | None = None,
    end: str | None = None,
    station: str | None = None,
) -> dict[str, Any]:
    """(Manager only) Update an employee shift schedule with optimistic concurrency.

    Must supply expected_version. If another manager updated the shift concurrently,
    the update will be rejected to prevent overlapping/conflicting writes.
    """
    await _require_manager()
    if not shift_id:
        raise ValueError("shift_id is required")
    payload = {
        "expected_version": expected_version,
        "start": start,
        "end": end,
        "station": station,
    }
    return await _request("PUT", f"/7shifts/v2/shifts/{quote(shift_id, safe='')}", json=payload)


@mcp.tool()
async def send_staff_sms_alert(
    phone_number: str,
    carrier: str,
    message: str,
    manager_name: str | None = None,
    restaurant_phone: str | None = None,
    floor_phone: str | None = None,
    subject: str = "Remi Restaurant Alert",
) -> dict[str, Any]:
    """(Manager only) Send an SMS text message to an employee.

    Automatically appends a human manager signature and callback phone numbers so
    the employee knows they are communicating with their manager and can reply by text or call.
    Example carriers: verizon, att, tmobile, cricket, sprint.
    """
    account = await _require_manager()
    from agent.notifications import send_staff_sms

    mgr = manager_name or account.get("name", "Taylor Morgan")
    return await send_staff_sms(
        phone_number=phone_number,
        carrier=carrier,
        message=message,
        manager_name=mgr,
        restaurant_phone=restaurant_phone,
        floor_phone=floor_phone,
        subject=subject,
    )


@mcp.tool()
async def check_staff_sms_replies(filter_query: str | None = None) -> dict[str, Any]:
    """(Manager only) Check recent text/email responses received from staff members."""
    await _require_manager()
    from agent.notifications import get_staff_replies

    replies = get_staff_replies(filter_query)
    return {
        "status": "success",
        "total_replies": len(replies),
        "replies": replies,
    }


def main() -> None:
    """Start the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

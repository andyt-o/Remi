"""MCP tools for the Remi restaurant mock integrations.

Run as a local MCP server with:
    uv run python -m agent.mcp_server

The server uses stdio transport so an agent runtime (including one running in
Daytona) can connect to it as an MCP client. Configure MOCK_POS_BASE_URL to a
URL reachable from that runtime.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("remi-restaurant-tools")

MANAGER_ROLES = {"manager"}
ASSISTANT_READ_TOOLS = ("get_my_account_status", "get_menu", "check_item_availability", "get_order_check")
ASSISTANT_MANAGER_READ_TOOLS = ("get_staff_working_now", "get_today_shifts", "get_inventory",
                                "get_staff_account_status", "check_staff_sms_replies",
                                "get_daytona_task", "list_daytona_tasks")
ASSISTANT_MANAGER_ACTION_TOOLS = ("send_staff_sms_alert",)
STAFF_MCP_TOOLS = ASSISTANT_READ_TOOLS + (
    "create_order_check",
)
MANAGER_MCP_TOOLS = STAFF_MCP_TOOLS + ASSISTANT_MANAGER_READ_TOOLS + (
    "deplete_inventory", "update_shift_schedule",
    "send_staff_sms_alert", "start_daytona_delivery_report",
)
_request_account: ContextVar[int | None] = ContextVar("remi_request_account", default=None)


@contextmanager
def account_scope(account_id: int):
    """Scope direct tool calls to a demo account without changing stdio identity."""
    token = _request_account.set(account_id)
    try:
        yield
    finally:
        _request_account.reset(token)


def _base_url() -> str:
    return os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")


def _account_id() -> int:
    current = _request_account.get()
    if current is not None:
        return current
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


async def assistant_capabilities() -> dict[str, Any]:
    """Return read tools wired into the staff assistant for the current account."""
    account = await _require_active_account()
    tools = list(ASSISTANT_READ_TOOLS)
    mcp_tools = STAFF_MCP_TOOLS
    if str(account.get("role", "")).strip().lower() in MANAGER_ROLES:
        tools.extend(ASSISTANT_MANAGER_READ_TOOLS)
        tools.extend(ASSISTANT_MANAGER_ACTION_TOOLS)
        mcp_tools = MANAGER_MCP_TOOLS
    return {"account_id": account["user_id"], "role": account["role"],
            "tools": tools, "other_mcp_tools": [name for name in mcp_tools if name not in tools]}


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
    message: str,
    carrier: str | None = None,
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



@mcp.tool()
async def start_daytona_delivery_report() -> dict[str, Any]:
    """Start the bounded mock MarketMan delivery report in a Daytona sandbox.

    Manager only. Returns immediately; use get_daytona_task to follow progress.
    This creates no purchase order. Tasks are local to this MCP process.
    """
    await _require_manager()
    if not os.getenv("DAYTONA_API_KEY"):
        raise RuntimeError("Daytona is not configured on this MCP process.")
    from agent.daytona_tasks import start_delivery_report_task

    task_id = start_delivery_report_task(_base_url())
    return {"task_id": task_id, "status": "queued"}


@mcp.tool()
async def get_daytona_task(task_id: str) -> dict[str, Any]:
    """(Manager only) Read a task's progress, report, and sandbox lifecycle."""
    await _require_manager()
    from agent.daytona_tasks import get_task

    task = get_task(task_id)
    if task is None:
        raise ValueError("Task not found in this MCP process")
    return task


@mcp.tool()
async def list_daytona_tasks() -> dict[str, Any]:
    """(Manager only) List background tasks and observed sandbox lifecycle states."""
    await _require_manager()
    from agent.daytona_tasks import list_tasks

    tasks = list_tasks()
    return {"tasks": [{key: value for key, value in task.items() if key != "report"}
                      for task in tasks]}

def main() -> None:
    """Start the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

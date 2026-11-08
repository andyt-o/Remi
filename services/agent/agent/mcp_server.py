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

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("remi-restaurant-tools")


def _base_url() -> str:
    return os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")


async def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    timeout = httpx.Timeout(5.0, connect=1.0)
    async with httpx.AsyncClient(base_url=_base_url(), timeout=timeout) as client:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_menu() -> dict[str, Any]:
    """Get the restaurant's current menu and prices from the mock POS."""
    return await _request("GET", "/oracle-pos/menu")


@mcp.tool()
async def get_inventory() -> dict[str, Any]:
    """Get current inventory and 86'd status from the mock inventory system."""
    return await _request("GET", "/marketman/v1/inventory/items")


@mcp.tool()
async def check_item_availability(item_key: str) -> dict[str, Any]:
    """Check if an ingredient or beverage is currently available."""
    return await _request(
        "GET", f"/marketman/v1/inventory/check-availability/{item_key}"
    )


@mcp.tool()
async def get_staff_working_now() -> dict[str, Any]:
    """Get the staff roster and statuses from the mock scheduling system."""
    return await _request("GET", "/7shifts/v2/who_is_working_now")


@mcp.tool()
async def get_today_shifts() -> dict[str, Any]:
    """Get today's scheduled shifts from the mock scheduling system."""
    return await _request("GET", "/7shifts/v2/shifts/today")


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

    return await _request(
        "POST",
        "/oracle-pos/checks",
        json={"items": payload_items, "order_type": order_type, "table_number": table_number},
    )


def main() -> None:
    """Start the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

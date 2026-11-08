"""In-memory TTL cache for store-wide restaurant state.

Provides sub-millisecond lookups for relatively static restaurant data (menu,
pricing, employee roster) while supporting on-demand invalidation and concise
context summarization for LangGraph conversational turns.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx


class RestaurantStoreCache:
    """Thread-safe, in-process store cache with configurable TTL."""

    def __init__(self, ttl_seconds: float = 900.0) -> None:  # Default 15 minutes
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}

    def _base_url(self) -> str:
        return os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")

    def get(self, key: str) -> Any | None:
        """Retrieve a cached entry if it has not expired."""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return data
            # Expired
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Cache an entry with the current timestamp."""
        self._cache[key] = (time.time(), value)

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate a specific key or all cached data."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    async def get_menu(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetch menu with TTL caching."""
        cached = self.get("menu")
        if cached is not None and not force_refresh:
            return cached

        async with httpx.AsyncClient(base_url=self._base_url(), timeout=3.0) as client:
            res = await client.get("/oracle-pos/menu")
            res.raise_for_status()
            data = res.json().get("items", [])
            self.set("menu", data)
            return data

    async def get_staff_roster(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Fetch staff roster with TTL caching."""
        cached = self.get("staff_roster")
        if cached is not None and not force_refresh:
            return cached

        async with httpx.AsyncClient(base_url=self._base_url(), timeout=3.0) as client:
            res = await client.get("/7shifts/v2/who_is_working_now")
            res.raise_for_status()
            data = res.json().get("workers", [])
            self.set("staff_roster", data)
            return data

    async def get_inventory_summary(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch inventory summary with shorter TTL (e.g. 5 minutes)."""
        cached = self.get("inventory_summary")
        if cached is not None and not force_refresh:
            return cached

        async with httpx.AsyncClient(base_url=self._base_url(), timeout=3.0) as client:
            res = await client.get("/marketman/v1/inventory/items")
            res.raise_for_status()
            data = res.json().get("inventory", {})
            self.set("inventory_summary", data)
            return data

    async def build_turn_context(self) -> str:
        """Construct a compact text summary of the current shared state for LangGraph turns."""
        try:
            menu = await self.get_menu()
            workers = await self.get_staff_roster()
            inventory = await self.get_inventory_summary()

            menu_items_str = ", ".join(f"{i['name']} (${i['price']:.2f}, ID:{i['item_id']})" for i in menu[:6])
            active_staff = ", ".join(f"{w['name']} ({w['role']})" for w in workers if w.get("status") == "active")
            out_of_stock = [v["name"] for k, v in inventory.items() if v.get("is_86d") or v.get("on_hand", 0) <= 0]
            out_str = ", ".join(out_of_stock) if out_of_stock else "None"

            return (
                f"[RESTAURANT OPERATIONAL CONTEXT]\n"
                f"- Available Menu: {menu_items_str}\n"
                f"- 86'd (Out of Stock): {out_str}\n"
                f"- Active On-Shift Staff: {active_staff}\n"
            )
        except Exception:
            # Fallback if mock server is temporarily unreachable
            return "[RESTAURANT OPERATIONAL CONTEXT]\n(Live restaurant state unavailable)"


# Global shared instance across all sessions in this service process
store_cache = RestaurantStoreCache(ttl_seconds=900.0)

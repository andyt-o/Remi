"""Bounded background task for the isolated MarketMan receiving report demo."""

from __future__ import annotations

import concurrent.futures
import json
import os
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

MAX_TASK_SECONDS = 180
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="daytona-task")
_TASKS: dict[str, dict[str, Any]] = {}
_TASK_LOCK = threading.Lock()


def _set_task(task_id: str, **updates: Any) -> None:
    with _TASK_LOCK:
        _TASKS[task_id].update(updates)
        _TASKS[task_id]["updated_at"] = datetime.now(UTC).isoformat()


def get_task(task_id: str) -> dict[str, Any] | None:
    with _TASK_LOCK:
        task = _TASKS.get(task_id)
        return dict(task) if task else None


def list_tasks() -> list[dict[str, Any]]:
    """Return snapshots of tasks owned by this service process, newest first."""
    with _TASK_LOCK:
        return [dict(task) for task in reversed(list(_TASKS.values()))]


def start_delivery_report_task(mock_base_url: str) -> str:
    task_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    with _TASK_LOCK:
        _TASKS[task_id] = {
            "task_id": task_id,
            "kind": "next_delivery_report",
            "status": "queued",
            "progress": "Waiting to collect MarketMan demo data.",
            "created_at": now,
            "updated_at": now,
            "report": None,
            "error": None,
            "execution": None,
            "sandbox_id": None,
            "sandbox_status": "not_created",
        }
    _EXECUTOR.submit(_run_task, task_id, mock_base_url)
    return task_id


def _analyze_with_daytona(task_id: str, inventory: dict[str, Any], history: dict[str, Any]) -> str:
    api_key = os.getenv("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("Daytona is not configured. Set DAYTONA_API_KEY on the agent service.")

    from daytona import CreateSandboxFromImageParams, Daytona, DaytonaConfig

    timeout = min(max(int(os.getenv("DAYTONA_TASK_TIMEOUT_SECONDS", "120")), 15), MAX_TASK_SECONDS)
    client = Daytona(DaytonaConfig(
        api_key=api_key,
        api_url=os.getenv("DAYTONA_API_URL") or None,
        target=os.getenv("DAYTONA_TARGET") or None,
    ))
    sandbox = None
    try:
        sandbox = client.create(CreateSandboxFromImageParams(
            image=os.getenv("DAYTONA_TASK_IMAGE", "python:3.12-slim"),
            language="python",
            name=f"remi-delivery-report-{uuid.uuid4().hex[:8]}",
            ephemeral=True,
            network_block_all=True,
        ), timeout=45)
        _set_task(task_id, sandbox_id=sandbox.id, sandbox_status="running")
        payload_bytes = json.dumps({"inventory": inventory, "history": history}, separators=(",", ":")).encode()
        analyzer = '''
import json, sys
with open("/tmp/remi-marketman-report.json", encoding="utf-8") as source:
    data = json.load(source)
inventory = data["inventory"].get("inventory", {})
history = data["history"].get("records", [])
items = {}
for record in history:
    key = record["item_key"]
    row = items.setdefault(key, {"deliveries": 0, "units": 0, "spend": 0.0, "last_received": None})
    row["deliveries"] += 1
    row["units"] += int(record["quantity"])
    row["spend"] += float(record["quantity"]) * float(record["unit_cost"])
    row["last_received"] = max(row["last_received"] or "", record["received_on"])
lines = ["NEXT DELIVERY PLANNING REPORT", "Based on illustrative MarketMan mock YTD receiving history.", ""]
ranked = []
for key, current in inventory.items():
    hist = items.get(key, {"deliveries": 0, "units": 0, "spend": 0.0, "last_received": "No YTD receipt"})
    average = hist["units"] / hist["deliveries"] if hist["deliveries"] else 0
    on_hand = int(current.get("on_hand", 0))
    suggested = max(0, round(average - on_hand))
    priority = "URGENT" if current.get("is_86d") or on_hand == 0 else "REVIEW" if on_hand < max(5, average * .25) else "ROUTINE"
    ranked.append((priority != "URGENT", on_hand - average, key, current, hist, average, suggested, priority))
for _, _, key, current, hist, average, suggested, priority in sorted(ranked):
    lines.append(f"{priority} | {current.get('name', key)} ({key})")
    lines.append(f"  On hand: {current.get('on_hand', 0)} {current.get('unit', 'units')}; YTD receipts: {hist['deliveries']} deliveries / {hist['units']} units; average receipt: {average:.1f}; YTD spend: ${hist['spend']:.2f}; last received: {hist['last_received']}")
    lines.append(f"  Suggested next-delivery quantity for manager review: {suggested} {current.get('unit', 'units')}")
lines += ["", "Recommendations are planning estimates from mock receiving frequency and current stock.", "This report does not create or submit a purchase order."]
print("\\n".join(lines))
'''
        _set_task(task_id, status="running", progress="Analyzing YTD receipts and current stock in Daytona.", execution="daytona")
        sandbox.fs.upload_file(payload_bytes, "/tmp/remi-marketman-report.json", timeout=20)
        sandbox.fs.upload_file(analyzer.encode(), "/tmp/remi-marketman-report.py", timeout=20)
        result = sandbox.process.exec(
            "python3 /tmp/remi-marketman-report.py",
            timeout=timeout,
            env={"PYTHONUNBUFFERED": "1"},
        )
        if result.exit_code != 0:
            raise RuntimeError(f"Daytona analysis exited with code {result.exit_code}.")
        output = (result.artifacts.stdout if result.artifacts else result.result).strip()
        if not output or len(output) > 20000:
            raise RuntimeError("Daytona returned an empty or oversized report.")
        return output
    finally:
        if sandbox is not None:
            try:
                client.delete(sandbox, timeout=20, wait=False)
                _set_task(task_id, sandbox_status="deletion_requested")
            except Exception:  # noqa: BLE001 - record cleanup failure from SDK
                _set_task(task_id, sandbox_status="cleanup_failed")


def _run_task(task_id: str, mock_base_url: str) -> None:
    try:
        _set_task(task_id, status="running", progress="Querying MarketMan inventory and YTD receiving history.")
        timeout = httpx.Timeout(12.0, connect=3.0)
        with httpx.Client(base_url=mock_base_url, timeout=timeout) as client:
            inventory_response = client.get("/marketman/v1/inventory/items")
            inventory_response.raise_for_status()
            history_response = client.get("/marketman/v1/receiving/ytd")
            history_response.raise_for_status()
            inventory = inventory_response.json()
            history = history_response.json()
        if inventory.get("status") != "success" or history.get("status") != "success":
            raise RuntimeError("MarketMan mock returned an unexpected response.")
        report = _analyze_with_daytona(task_id, inventory, history)
        _set_task(task_id, status="completed", progress="Report ready for manager review.", report=report, execution="daytona")
    except Exception as exc:  # noqa: BLE001 - background failures must reach task status
        _set_task(task_id, status="failed", progress="The delivery report could not be completed.", error=str(exc)[:500])

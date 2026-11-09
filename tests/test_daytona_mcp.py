import time
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from agent import daytona_tasks, mcp_server


@pytest.mark.asyncio
async def test_daytona_mcp_requires_manager_and_tracks_process_tasks(monkeypatch):
    tool_names = {tool.name for tool in await mcp_server.mcp.list_tools()}
    assert {"start_daytona_delivery_report", "get_daytona_task", "list_daytona_tasks"} <= tool_names

    async def account():
        return {"user_id": 105, "role": "server", "account_status": "active"}
    monkeypatch.setattr(mcp_server, "_account", account)
    for call in (mcp_server.start_daytona_delivery_report(), mcp_server.list_daytona_tasks(),
                 mcp_server.get_daytona_task("missing")):
        with pytest.raises(PermissionError):
            await call

    async def manager():
        return {"user_id": 106, "role": "manager", "account_status": "active"}
    monkeypatch.setattr(mcp_server, "_account", manager)
    monkeypatch.setenv("DAYTONA_API_KEY", "test")
    monkeypatch.setattr(daytona_tasks._EXECUTOR, "submit", lambda *args: None)
    started = await mcp_server.start_daytona_delivery_report()
    task = await mcp_server.get_daytona_task(started["task_id"])
    assert task["status"] == "queued" and task["sandbox_status"] == "not_created"
    assert any(t["task_id"] == task["task_id"] for t in (await mcp_server.list_daytona_tasks())["tasks"])
    with pytest.raises(ValueError):
        await mcp_server.get_daytona_task("missing")


def test_two_reports_complete_and_request_sandbox_cleanup(monkeypatch):
    monkeypatch.setenv("DAYTONA_API_KEY", "test")
    class Sandbox:
        id = "sandbox-test"
        fs = SimpleNamespace(upload_file=lambda *args, **kwargs: None)
        process = SimpleNamespace(exec=lambda *args, **kwargs: SimpleNamespace(
            exit_code=0, artifacts=SimpleNamespace(stdout="Report ready")))
    class Client:
        def __init__(self, *args, **kwargs): pass
        def create(self, *args, **kwargs): return Sandbox()
        def delete(self, *args, **kwargs): pass
    def response(request):
        return httpx.Response(200, json={"status": "success", "inventory": {}, "records": []})
    real_client = httpx.Client
    with patch("daytona.Daytona", Client), patch.object(daytona_tasks.httpx, "Client", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(response), **kwargs)):
        ids = [daytona_tasks.start_delivery_report_task("http://mock") for _ in range(2)]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            tasks = [daytona_tasks.get_task(task_id) for task_id in ids]
            if all(task["status"] in {"completed", "failed"} for task in tasks):
                break
            time.sleep(.02)
        assert all(task["status"] == "completed" for task in tasks), tasks
        assert all(task["sandbox_id"] == "sandbox-test" and task["sandbox_status"] == "deletion_requested" for task in tasks)

from unittest.mock import AsyncMock

import httpx
import pytest
from agent import graph, mcp_server, notifications
from langchain_core.messages import HumanMessage


@pytest.mark.asyncio
async def test_sms_requires_manager_and_confirmation(monkeypatch):
    for name in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.setenv(name, "test")
    manager = AsyncMock(return_value={"name": "Taylor", "role": "manager"})
    sender = AsyncMock(return_value={"provider": "twilio"})
    monkeypatch.setattr(mcp_server, "_require_manager", manager)
    monkeypatch.setattr(mcp_server, "send_staff_sms_alert", sender)
    state = {"messages": [HumanMessage(content="text +15551234567: Your shift starts at 6")], "role": "manager"}
    result = await graph.agent_node(state, {})
    sender.assert_not_awaited()
    assert result["pending_sms"]["phone_number"] == "+15551234567"
    state.update(pending_sms=result["pending_sms"], messages=[HumanMessage(content="confirm send")])
    result = await graph.agent_node(state, {})
    sender.assert_awaited_once()
    assert result["pending_sms"] is None
    assert "not yet confirmed" in result["messages"][0].content


@pytest.mark.asyncio
async def test_twilio_direct_number(monkeypatch):
    for name, value in {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "test", "TWILIO_FROM_NUMBER": "+15550001111"}.items():
        monkeypatch.setenv(name, value)
    seen = []
    def handle(request):
        seen.append(request)
        return httpx.Response(201, json={"sid": "SMtest", "status": "queued"})
    original = httpx.AsyncClient
    monkeypatch.setattr(notifications.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    result = await notifications.send_staff_sms(phone_number="6195550123", carrier=None, message="Hello")
    assert result["recipient"] == "+16195550123" and result["provider_status"] == "queued"
    assert b"To=%2B16195550123" in seen[0].content

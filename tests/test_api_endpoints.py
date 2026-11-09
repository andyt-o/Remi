import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path

# Ensure services and agent packages are on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "services"))
sys.path.insert(0, str(root_dir / "services" / "agent"))

from mocks.main import app as mocks_app
from agent.main import app as agent_app


@pytest_asyncio.fixture
async def mock_client():
    transport = ASGITransport(app=mocks_app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8001") as client:
        yield client


@pytest_asyncio.fixture
async def agent_client():
    transport = ASGITransport(app=agent_app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        yield client


class TestMockRestaurantApis:
    @pytest.mark.asyncio
    async def test_mocks_health_and_config(self, mock_client: AsyncClient):
        res = await mock_client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "service": "remi-mocks"}

        res = await mock_client.get("/simulation-config")
        assert res.status_code == 200
        assert "active_preset" in res.json()

    @pytest.mark.asyncio
    async def test_oracle_pos_flow(self, mock_client: AsyncClient):
        # 1. Menu
        menu_res = await mock_client.get("/oracle-pos/menu")
        assert menu_res.status_code == 200
        items = menu_res.json().get("items", [])
        assert len(items) > 0

        # 2. Create Check
        create_res = await mock_client.post(
            "/oracle-pos/checks",
            json={
                "table_number": 12,
                "order_type": "dine_in",
                "items": [{"item_id": "101", "quantity": 1}],
            },
        )
        assert create_res.status_code == 200
        check = create_res.json().get("check")
        assert check is not None
        check_id = check["check_id"]
        assert check["table_number"] == 12

        # 3. Retrieve Check
        get_res = await mock_client.get(f"/oracle-pos/checks/{check_id}")
        assert get_res.status_code == 200
        assert get_res.json()["check"]["check_id"] == check_id

    @pytest.mark.asyncio
    async def test_seven_shifts_endpoints(self, mock_client: AsyncClient):
        # 1. Who is working
        workers_res = await mock_client.get("/7shifts/v2/who_is_working_now")
        assert workers_res.status_code == 200
        assert workers_res.json().get("status") == "success"
        assert workers_res.json().get("total_active") > 0

        # 2. Get user 105 (Jordan Lee, Server)
        user_res = await mock_client.get("/7shifts/v2/users/105")
        assert user_res.status_code == 200
        user = user_res.json().get("user")
        assert user["name"] == "Jordan Lee"
        assert user["role"] == "Server"

        # 3. Today shifts
        shifts_res = await mock_client.get("/7shifts/v2/shifts/today")
        assert shifts_res.status_code == 200
        assert "shifts" in shifts_res.json()

    @pytest.mark.asyncio
    async def test_marketman_inventory(self, mock_client: AsyncClient):
        # 1. Inventory items
        items_res = await mock_client.get("/marketman/v1/inventory/items")
        assert items_res.status_code == 200
        assert len(items_res.json().get("inventory", [])) > 0

        # 2. Availability check
        avail_res = await mock_client.get("/marketman/v1/inventory/check-availability/beef_patty")
        assert avail_res.status_code == 200
        assert avail_res.json().get("available") is True

    @pytest.mark.asyncio
    async def test_notifications_sms(self, mock_client: AsyncClient):
        sms_res = await mock_client.post(
            "/notifications/sms",
            json={
                "phone_number": "6195550144",
                "carrier": "verizon",
                "gateway_address": "6195550144@vtext.com",
                "message": "Schedule updated",
            },
        )
        assert sms_res.status_code == 200
        assert sms_res.json()["status"] == "delivered"

        history_res = await mock_client.get("/notifications/sms/history")
        assert history_res.status_code == 200
        assert history_res.json()["total"] >= 1


class TestAgentServiceApis:
    @pytest.mark.asyncio
    async def test_agent_health(self, agent_client: AsyncClient):
        res = await agent_client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "service": "remi-agent"}

    @pytest.mark.asyncio
    async def test_dependency_health(self, agent_client: AsyncClient):
        res = await agent_client.get("/health/dependencies")
        assert res.status_code == 200
        data = res.json()
        assert "agent_api" in data
        assert "mock_pos" in data
        assert "elevenlabs" in data
        assert "daytona" in data

    @pytest.mark.asyncio
    async def test_inbound_sms_webhook(self, agent_client: AsyncClient):
        res = await agent_client.post(
            "/webhooks/inbound-sms",
            json={"sender": "6195550100", "body": "I will cover Marcus on Friday"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "recorded"
        assert data.get("reply", {}).get("sender") == "6195550100"

    @pytest.mark.asyncio
    async def test_daytona_task_rbac(self, agent_client: AsyncClient):
        # Server role (account_id=105) is forbidden
        forbidden = await agent_client.post(
            "/tasks/daytona",
            json={"kind": "next_delivery_report", "account_id": 105},
        )
        assert forbidden.status_code == 403

        # Manager role (account_id=106) succeeds (queued)
        allowed = await agent_client.post(
            "/tasks/daytona",
            json={"kind": "next_delivery_report", "account_id": 106},
        )
        assert allowed.status_code == 202
        task_id = allowed.json().get("task_id")
        assert task_id is not None

        # Check status
        task_status = await agent_client.get(f"/tasks/daytona/{task_id}")
        assert task_status.status_code == 200
        assert task_status.json().get("task_id") == task_id

    @pytest.mark.asyncio
    async def test_voice_greeting_tts(self, agent_client: AsyncClient):
        res = await agent_client.post(
            "/voice/greeting",
            json={"role": "Manager", "user": "Taylor"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/mpeg"
        assert len(res.content) > 1000

"""
Idempotency and Circuit Breaker tests for KaryaOS Integration Gateway.
Verifies Hackathon Non-negotiable Rule 7:
'Every side-effecting call goes through an idempotent integration gateway.
A forced retry must never create a duplicate (e.g. two laptops). Write a test for this.'
"""
import pytest
import pytest_asyncio
import os
from pathlib import Path
from httpx import AsyncClient, ASGITransport

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from mocks.main import app as mock_app, LEDGER_FILE
from core.gateway.gateway import IntegrationGateway
from core.gateway.circuit_breaker import CircuitBreakerOpenException


@pytest_asyncio.fixture(autouse=True)
async def clean_mock_ledger():
    """Ensure mock ledger is fresh before each test."""
    if LEDGER_FILE.exists():
        try:
            LEDGER_FILE.unlink()
        except Exception:
            pass
    # Reset fail modes
    os.environ["MOCK_IT_FAIL_MODE"] = "none"
    os.environ["MOCK_ADMIN_FAIL_MODE"] = "none"
    os.environ["MOCK_PAYROLL_FAIL_MODE"] = "none"
    yield
    if LEDGER_FILE.exists():
        try:
            LEDGER_FILE.unlink()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_forced_retry_creates_exactly_one_laptop():
    """
    CRITICAL HACKATHON TEST:
    Forced retries with the same idempotency key must NEVER allocate a duplicate asset.
    The mock ledger must hold exactly 1 allocation.
    """
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as mock_client:
        gateway = IntegrationGateway(base_url_override="http://test")

        idem_key = "run-retry-test:allocate_laptop:emp_9999"
        payload = {
            "employee_id": "EMP9999",
            "employee_name": "Kavya Patel",
            "grade": "L3",
            "location": "Bengaluru",
            "asset_type": "laptop",
        }

        # First call: allocates laptop
        resp1 = await gateway.call(
            integration_name="it_assets",
            path="/it/assets/allocate",
            payload=payload,
            idempotency_key=idem_key,
            client=mock_client,
        )
        assert resp1["status"] == "allocated"
        asset_id_1 = resp1["asset_id"]

        # Simulate crash & forced retry 1
        resp2 = await gateway.call(
            integration_name="it_assets",
            path="/it/assets/allocate",
            payload=payload,
            idempotency_key=idem_key,
            client=mock_client,
        )
        assert resp2["asset_id"] == asset_id_1

        # Simulate another forced retry 2 directly hitting mock API with same header
        resp3 = await mock_client.post(
            "/it/assets/allocate",
            json=payload,
            headers={"Idempotency-Key": idem_key},
        )
        assert resp3.status_code == 200
        assert resp3.json()["asset_id"] == asset_id_1
        assert resp3.headers.get("x-idempotent-replayed") == "true"

        # Verify Mock IT Ledger holds EXACTLY ONE laptop
        ledger_resp = await mock_client.get("/it/assets/ledger")
        assert ledger_resp.status_code == 200
        ledger_data = ledger_resp.json()
        assert ledger_data["count"] == 1, f"Expected exactly 1 laptop in ledger, got {ledger_data['count']}"


@pytest.mark.asyncio
async def test_circuit_breaker_trips_on_consecutive_failures():
    """
    Test circuit breaker:
    When an external service returns 503 repeatedly, the circuit breaker opens
    and fails fast without hammering the external API.
    """
    os.environ["MOCK_IT_FAIL_MODE"] = "503"
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as mock_client:
        gateway = IntegrationGateway(base_url_override="http://test")
        cb = gateway.get_circuit_breaker("it_assets")
        cb.failure_threshold = 3
        cb.reset_timeout_s = 60.0

        payload = {
            "employee_id": "EMP8888",
            "employee_name": "Test User",
            "grade": "L2",
            "location": "Bengaluru",
        }

        # 3 calls should fail with 503 and trip circuit to OPEN
        for i in range(3):
            with pytest.raises(Exception):
                await gateway.call(
                    integration_name="it_assets",
                    path="/it/assets/allocate",
                    payload=payload,
                    idempotency_key=f"key-cb-{i}",
                    client=mock_client,
                )

        assert cb.state.value == "open"

        # 4th call must immediately raise CircuitBreakerOpenException
        with pytest.raises(CircuitBreakerOpenException):
            await gateway.call(
                integration_name="it_assets",
                path="/it/assets/allocate",
                payload=payload,
                idempotency_key="key-cb-4",
                client=mock_client,
            )

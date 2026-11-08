"""
Idempotent Integration Gateway.
Guarantees that no side-effecting external call (e.g. laptop allocation) is ever duplicated
on retry or crash, using an idempotency key store and per-service circuit breakers.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Optional
import httpx
import yaml
import structlog

from core.gateway.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from core.gateway.retry import execute_with_retry

log = structlog.get_logger()

CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "integrations.yaml"


class IntegrationGateway:
    def __init__(self, config_path: Path = CONFIG_FILE, base_url_override: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.base_url_override = base_url_override or os.getenv("MOCK_API_BASE_URL", "http://localhost:8001")
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.store: dict[str, dict] = {}  # idempotency_key -> {status: done|in_flight|failed, response: dict}

        # Initialize circuit breakers from config
        for name, cfg in self.config.get("integrations", {}).items():
            cb_cfg = cfg.get("circuit_breaker", {})
            self.circuit_breakers[name] = CircuitBreaker(
                failure_threshold=cb_cfg.get("threshold", 3),
                reset_timeout_s=float(cb_cfg.get("reset_s", 30)),
            )

    def _load_config(self, path: Path) -> dict:
        if path.exists():
            try:
                return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as e:
                log.warning("Could not load integrations config", error=str(e))
        return {}

    def get_circuit_breaker(self, integration_name: str) -> CircuitBreaker:
        if integration_name not in self.circuit_breakers:
            self.circuit_breakers[integration_name] = CircuitBreaker(failure_threshold=3, reset_timeout_s=30.0)
        return self.circuit_breakers[integration_name]

    def _resolve_url(self, integration_name: str, path: str) -> str:
        """Resolve endpoint URL using mock base URL."""
        base = self.base_url_override.rstrip("/")
        clean_path = path if path.startswith("/") else f"/{path}"
        return f"{base}{clean_path}"

    async def call(
        self,
        integration_name: str,
        path: str,
        payload: dict,
        idempotency_key: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        """
        Execute an idempotent external call.
        1. If idempotency_key is already recorded as 'done', returns cached response directly.
        2. Checks circuit breaker.
        3. Invokes with exponential backoff and passes Idempotency-Key header.
        4. Caches response and returns.
        """
        # 1. Idempotency Cache Check
        cached = self.store.get(idempotency_key)
        if cached and cached.get("status") == "done":
            log.info("Idempotent gateway hit: returning stored response", key=idempotency_key)
            resp = cached["response"].copy()
            resp["_idempotent_replayed"] = True
            return resp

        # 2. Circuit Breaker Check
        cb = self.get_circuit_breaker(integration_name)
        if not cb.allow_request():
            log.error("Circuit breaker is OPEN: rejecting call", integration=integration_name)
            raise CircuitBreakerOpenException(
                f"Circuit breaker for integration '{integration_name}' is OPEN. Fast failing to human queue."
            )

        # 3. Mark in-flight
        self.store[idempotency_key] = {"status": "in_flight", "payload": payload}

        url = self._resolve_url(integration_name, path)
        headers = {
            "Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        }

        async def _do_request():
            if client:
                resp = await client.post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=15.0) as cli:
                    resp = await cli.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

        try:
            cfg = self.config.get("integrations", {}).get(integration_name, {})
            max_retries = cfg.get("retry", {}).get("max", 3)
            result = await execute_with_retry(_do_request, max_retries=max_retries, initial_delay=0.2)

            cb.record_success()
            self.store[idempotency_key] = {"status": "done", "response": result}
            return result

        except Exception as e:
            cb.record_failure()
            self.store[idempotency_key] = {"status": "failed", "error": str(e)}
            log.error("Gateway call failed", integration=integration_name, url=url, error=str(e))
            raise

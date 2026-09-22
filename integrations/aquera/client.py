from __future__ import annotations

import os
import time
import uuid
import logging
import asyncio
from typing import Any, Dict, Optional, Set

import httpx

from .errors import (
    AqueraError,
    TimeoutError as AqueraTimeoutError,
    map_http_status_to_error,
)

logger = logging.getLogger("hermes.integrations.aquera")

RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}


class AqueraClient:
    """Robust, asynchronous HTTP client for communication with Aquera Next.js API.
    
    Adheres strictly to the principles in implementasihermesaquera.md:
    - Never hardcode tokens
    - Never leak credentials to logs
    - Safe retries only for idempotent read operations
    - Configurable timeout and retry bounds
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.base_url = (
            base_url or os.getenv("AQUERA_BASE_URL", "http://localhost:3000")
        ).rstrip("/")

        self.token = token or os.getenv("AQUERA_API_TOKEN", "")
        self.timeout = timeout or float(os.getenv("AQUERA_TIMEOUT_SECONDS", "30"))
        self.max_retries = (
            max_retries
            if max_retries is not None
            else int(os.getenv("AQUERA_MAX_RETRIES", "3"))
        )

    def _headers(
        self,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-request-id": request_id or str(uuid.uuid4()),
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if organization_id:
            headers["x-organization-id"] = organization_id
        if user_id:
            headers["x-user-id"] = user_id
        return headers

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        allow_retry: Optional[bool] = None,
        **kwargs: Any,
    ) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_id = str(uuid.uuid4())
        headers = self._headers(
            organization_id=organization_id,
            user_id=user_id,
            request_id=req_id,
        )

        method_upper = method.upper()
        # Safe retry principle: Only retry GET requests by default, never blind retry mutations
        is_safe_read = method_upper in ("GET", "HEAD")
        should_retry = allow_retry if allow_retry is not None else is_safe_read

        attempts = 1 + (self.max_retries if should_retry else 0)
        start_time = time.perf_counter()

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method_upper,
                        url=url,
                        params=params,
                        json=json_data,
                        headers=headers,
                        **kwargs,
                    )

                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

                # Structured log without secrets
                logger.info(
                    "Aquera API Call",
                    extra={
                        "request_id": req_id,
                        "method": method_upper,
                        "endpoint": path,
                        "organization_id": organization_id,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "attempt": attempt,
                    },
                )

                if response.status_code in RETRYABLE_STATUS_CODES and should_retry and attempt < attempts:
                    backoff = 0.5 * (2 ** (attempt - 1))
                    logger.warning(
                        f"Retryable status {response.status_code} received from {path}. "
                        f"Backing off {backoff}s (attempt {attempt}/{attempts})"
                    )
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code >= 400:
                    raise map_http_status_to_error(response.status_code, response.text)

                if not response.content:
                    return None

                return response.json()

            except (httpx.TimeoutException, httpx.ConnectTimeout):
                if should_retry and attempt < attempts:
                    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise AqueraTimeoutError(f"Request to {path} timed out after {self.timeout}s.")

            except httpx.RequestError as exc:
                if should_retry and attempt < attempts:
                    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                raise AqueraError(f"Network error contacting Aquera API at {path}: {str(exc)}")

        raise AqueraError(f"Max retries exceeded for {path}")

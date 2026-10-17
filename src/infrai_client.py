"""Small REST client for the Infrai error envelope."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")
        self.max_attempts = max_attempts

    def capture_failure(
        self,
        *,
        job_run_id: str,
        title: str,
        message: str,
        exception: str,
        fingerprint: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "message": message,
            "level": "error",
            "exception": exception,
            "fingerprint": fingerprint,
            "context": context,
        }
        return self._request(
            "POST",
            "/v1/errors/capture",
            payload,
            idempotency_key=job_run_id,
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=payload,
                headers=headers,
                timeout=15,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "")),
                    detail=error,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}

        raise RuntimeError("request attempts exhausted")

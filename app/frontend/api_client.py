"""Small HTTP client for the local mission product UI."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


DEFAULT_API_BASE_URL = os.getenv("SWARM_API_BASE_URL", "http://127.0.0.1:8000")


class ApiError(RuntimeError):
    """Raised when the backend API returns an error."""


class ApiClient:
    """Minimal JSON client for the product backend."""

    def __init__(self, base_url: str = DEFAULT_API_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with request.urlopen(url) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - UI behavior
            raise ApiError(exc.read().decode("utf-8")) from exc
        except error.URLError as exc:  # pragma: no cover - UI behavior
            raise ApiError(str(exc)) from exc

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("PUT", path, payload)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path, None)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - UI behavior
            raise ApiError(exc.read().decode("utf-8")) from exc
        except error.URLError as exc:  # pragma: no cover - UI behavior
            raise ApiError(str(exc)) from exc

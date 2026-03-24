"""Thin local HTTP API for mission planning and review."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.backend.services import ProductBackend, to_jsonable


def build_handler(backend: ProductBackend) -> type[BaseHTTPRequestHandler]:
    """Create a request handler class bound to backend services."""

    class ApiHandler(BaseHTTPRequestHandler):
        server_version = "SwarmProductAPI/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_cors_headers()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                if path == "/api/health":
                    return self._write_json({"status": "ok"})
                if path == "/api/presets":
                    return self._write_json(backend.scenarios.get_presets())
                if path == "/api/scenarios":
                    return self._write_json({"items": backend.scenarios.list_scenarios()})
                if path.startswith("/api/scenarios/"):
                    scenario_id = path.split("/")[-1]
                    return self._write_json(backend.scenarios.load_scenario(scenario_id))
                if path == "/api/runs":
                    return self._write_json({"items": backend.missions.list_runs()})
                if path.startswith("/api/runs/") and path.endswith("/replay"):
                    run_id = path.split("/")[-2]
                    return self._write_json({"run_id": run_id, "replay": backend.missions.get_replay(run_id)})
                if path.startswith("/api/runs/") and path.endswith("/events"):
                    run_id = path.split("/")[-2]
                    return self._write_json({"run_id": run_id, "events": backend.missions.get_events(run_id)})
                if path.startswith("/api/runs/"):
                    run_id = path.split("/")[-1]
                    return self._write_json(backend.missions.get_run(run_id))
                if path == "/api/experiments":
                    return self._write_json({"items": backend.experiments.list_experiments()})
                if path.startswith("/api/experiments/") and path.endswith("/summary"):
                    experiment_id = path.split("/")[-2]
                    return self._write_json(
                        {"experiment_id": experiment_id, "summary": backend.experiments.load_experiment_summary(experiment_id)}
                    )
                if path.startswith("/api/experiments/"):
                    experiment_id = path.split("/")[-1]
                    return self._write_json(backend.experiments.get_experiment(experiment_id))
                self._write_json({"error": f"Unknown route: {path}"}, status=HTTPStatus.NOT_FOUND)
            except FileNotFoundError as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            except Exception as exc:  # pragma: no cover - runtime API safeguard
                self._write_json({"error": f"{type(exc).__name__}: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_POST(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                payload = self._read_json()
                if path == "/api/scenarios":
                    saved = backend.scenarios.save_scenario(payload, scenario_id=payload.get("scenario_id"))
                    return self._write_json(saved, status=HTTPStatus.CREATED)
                if path == "/api/runs":
                    created = backend.missions.create_run(payload)
                    return self._write_json(created, status=HTTPStatus.ACCEPTED)
                if path.startswith("/api/runs/") and path.endswith("/interventions"):
                    run_id = path.split("/")[-2]
                    result = backend.missions.apply_intervention(run_id, payload["action"], payload.get("payload"))
                    return self._write_json(result, status=HTTPStatus.ACCEPTED)
                if path.startswith("/api/runs/") and path.endswith("/report"):
                    run_id = path.split("/")[-2]
                    return self._write_json(backend.generate_report(run_id), status=HTTPStatus.CREATED)
                if path == "/api/experiments":
                    created = backend.experiments.create_experiment(payload)
                    return self._write_json(created, status=HTTPStatus.ACCEPTED)
                self._write_json({"error": f"Unknown route: {path}"}, status=HTTPStatus.NOT_FOUND)
            except FileNotFoundError as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            except Exception as exc:  # pragma: no cover - runtime API safeguard
                self._write_json({"error": f"{type(exc).__name__}: {exc}"}, status=HTTPStatus.BAD_REQUEST)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _read_json(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            return json.loads(body.decode("utf-8") or "{}")

        def _write_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(to_jsonable(payload)).encode("utf-8")
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    return ApiHandler


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    storage_root: str | Path = "app/storage",
) -> ThreadingHTTPServer:
    """Build a configured local API server."""

    backend = ProductBackend(storage_root=storage_root)
    handler = build_handler(backend)
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Swarm Search product backend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--storage-root", default="app/storage")
    args = parser.parse_args()

    server = create_server(args.host, args.port, args.storage_root)
    print(f"Swarm product backend listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Phase 5 product-layer API and artifact tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import threading
import time
from urllib import request

from app.backend.server import create_server
from src.utils.config_loader import load_config


def _api_request(base_url: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_run(base_url: str, run_id: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = _api_request(base_url, "GET", f"/api/runs/{run_id}")
        if record["status"] in {"completed", "failed"}:
            return record
        time.sleep(0.1)
    raise AssertionError(f"Run {run_id} did not finish before timeout.")


def _wait_for_experiment(base_url: str, experiment_id: str, timeout: float = 40.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = _api_request(base_url, "GET", f"/api/experiments/{experiment_id}")
        if record["status"] in {"completed", "failed"}:
            return record
        time.sleep(0.15)
    raise AssertionError(f"Experiment {experiment_id} did not finish before timeout.")


def _scenario_payload(name: str, max_steps: int = 10) -> dict:
    payload = copy.deepcopy(load_config())
    payload["scenario"]["name"] = name
    payload["scenario"]["max_steps"] = max_steps
    payload["scenario"]["render"]["save_frames"] = False
    payload["scenario"]["strategy"] = "information_gain"
    return payload


def test_backend_api_scenario_save_and_load(tmp_path: Path) -> None:
    server = create_server(host="127.0.0.1", port=0, storage_root=tmp_path / "product")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        health = _api_request(base_url, "GET", "/api/health")
        assert health["status"] == "ok"

        saved = _api_request(base_url, "POST", "/api/scenarios", _scenario_payload("API Save Load"))
        loaded = _api_request(base_url, "GET", f"/api/scenarios/{saved['scenario_id']}")
        listed = _api_request(base_url, "GET", "/api/scenarios")

        assert loaded["scenario_id"] == saved["scenario_id"]
        assert any(item["scenario_id"] == saved["scenario_id"] for item in listed["items"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mission_run_request_flow_and_replay_fetch(tmp_path: Path) -> None:
    server = create_server(host="127.0.0.1", port=0, storage_root=tmp_path / "product")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        scenario = _api_request(base_url, "POST", "/api/scenarios", _scenario_payload("Run Flow", max_steps=8))
        created = _api_request(base_url, "POST", "/api/runs", {"scenario_id": scenario["scenario_id"], "seed": 3})
        completed = _wait_for_run(base_url, created["run_id"])
        replay = _api_request(base_url, "GET", f"/api/runs/{created['run_id']}/replay")
        events = _api_request(base_url, "GET", f"/api/runs/{created['run_id']}/events")

        assert completed["status"] == "completed"
        assert replay["replay"]
        assert events["events"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_operator_interventions_are_supported_and_logged(tmp_path: Path) -> None:
    server = create_server(host="127.0.0.1", port=0, storage_root=tmp_path / "product")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        payload = _scenario_payload("Intervention Flow", max_steps=30)
        payload["scenario"]["strategy"] = "random_sweep"
        scenario = _api_request(base_url, "POST", "/api/scenarios", payload)
        created = _api_request(base_url, "POST", "/api/runs", {"scenario_id": scenario["scenario_id"], "seed": 4})

        _api_request(base_url, "POST", f"/api/runs/{created['run_id']}/interventions", {"action": "pause"})
        _api_request(
            base_url,
            "POST",
            f"/api/runs/{created['run_id']}/interventions",
            {"action": "assign_waypoint", "payload": {"drone_id": 0, "position": [2, 2]}},
        )
        _api_request(
            base_url,
            "POST",
            f"/api/runs/{created['run_id']}/interventions",
            {"action": "force_return", "payload": {"drone_id": 1}},
        )
        run_record = _api_request(base_url, "GET", f"/api/runs/{created['run_id']}")
        events = _api_request(base_url, "GET", f"/api/runs/{created['run_id']}/events")

        assert run_record["latest_snapshot"]["paused"] is True
        assert "0" in run_record["latest_snapshot"]["manual_targets"] or 0 in run_record["latest_snapshot"]["manual_targets"]
        assert any(event["event_type"] == "operator_intervention" for event in events["events"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_report_generation_and_experiment_outputs(tmp_path: Path) -> None:
    server = create_server(host="127.0.0.1", port=0, storage_root=tmp_path / "product")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        scenario = _api_request(base_url, "POST", "/api/scenarios", _scenario_payload("Report Flow", max_steps=8))
        created = _api_request(base_url, "POST", "/api/runs", {"scenario_id": scenario["scenario_id"], "seed": 5})
        completed = _wait_for_run(base_url, created["run_id"])
        report = _api_request(base_url, "POST", f"/api/runs/{created['run_id']}/report", {})
        experiment = _api_request(
            base_url,
            "POST",
            "/api/experiments",
            {
                "strategies": ["auction_based", "information_gain"],
                "scenario_families": ["open_terrain"],
                "target_behaviors": ["terrain_biased"],
                "coordination_modes": ["centralized"],
                "drone_counts": [4],
                "battery_budgets": [120.0],
                "sensor_modes": ["thermal_visual"],
                "benchmark_num_seeds": 2,
                "experiment_num_seeds": 1,
            },
        )
        experiment_record = _wait_for_experiment(base_url, experiment["experiment_id"])
        summary = _api_request(base_url, "GET", f"/api/experiments/{experiment['experiment_id']}/summary")

        assert completed["status"] == "completed"
        assert Path(report["report_path"]).exists()
        assert experiment_record["status"] == "completed"
        assert summary["summary"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

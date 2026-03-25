"""Phase 6 FastAPI, SQLite, and decision-support tests."""

from __future__ import annotations

import copy
from pathlib import Path
import time

from fastapi.testclient import TestClient

from app.backend.core.settings import BackendSettings
from app.backend.main import create_app
from src.utils.config_loader import load_config


def _make_client(tmp_path: Path) -> TestClient:
    settings = BackendSettings(
        storage_root=str(tmp_path / "storage"),
        db_path=str(tmp_path / "storage" / "swarm_product.db"),
        comparison_num_seeds=1,
        job_max_workers=2,
    )
    app = create_app(settings)
    return TestClient(app)


def _scenario_payload(name: str, max_steps: int = 10) -> dict:
    payload = copy.deepcopy(load_config())
    payload["scenario"]["name"] = name
    payload["scenario"]["max_steps"] = max_steps
    payload["scenario"]["render"]["save_frames"] = False
    payload["scenario"]["strategy"] = "information_gain"
    return payload


def _wait_for_status(client: TestClient, path: str, expected: set[str], timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in expected:
            return payload
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {path}")


def test_fastapi_health_and_docs_are_available(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    health = client.get("/health")
    docs = client.get("/docs")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert docs.status_code == 200


def test_scenario_crud_and_template_listing_persist_to_sqlite(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    created = client.post("/scenarios", json=_scenario_payload("CRUD Scenario"))
    assert created.status_code == 200
    scenario_id = created.json()["id"]

    listed = client.get("/scenarios")
    loaded = client.get(f"/scenarios/{scenario_id}")
    updated_payload = _scenario_payload("CRUD Scenario Updated")
    updated = client.put(f"/scenarios/{scenario_id}", json=updated_payload)
    templates = client.get("/templates")

    assert listed.status_code == 200
    assert loaded.status_code == 200
    assert updated.status_code == 200
    assert templates.status_code == 200
    assert any(item["id"] == scenario_id for item in listed.json()["items"])
    assert len(templates.json()["items"]) >= 5
    assert Path(tmp_path / "storage" / "swarm_product.db").exists()


def test_job_lifecycle_mission_run_replay_and_events_flow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario = client.post("/scenarios", json=_scenario_payload("Run Flow", max_steps=8)).json()
    run = client.post("/runs", json={"scenario_id": scenario["id"], "seed": 3}).json()

    completed = _wait_for_status(client, f"/runs/{run['id']}", {"completed", "failed"})
    jobs = client.get("/jobs").json()["items"]
    replay = client.get(f"/runs/{run['id']}/replay").json()
    events = client.get(f"/runs/{run['id']}/events").json()

    assert completed["status"] == "completed"
    assert jobs
    assert replay["replay"]
    assert events["events"]


def test_operator_intervention_and_job_cancellation_flow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario = client.post("/scenarios", json=_scenario_payload("Intervention Flow", max_steps=30)).json()
    run = client.post("/runs", json={"scenario_id": scenario["id"], "seed": 4}).json()

    pause = client.post(f"/runs/{run['id']}/interventions", json={"action": "pause"})
    assign = client.post(
        f"/runs/{run['id']}/interventions",
        json={"action": "assign_waypoint", "payload": {"drone_id": 0, "position": [2, 2]}},
    )
    run_state = client.get(f"/runs/{run['id']}").json()
    job_id = run_state["job"]["id"]
    cancel = client.post(f"/jobs/{job_id}/cancel")

    assert pause.status_code == 200
    assert assign.status_code == 200
    assert run_state["latest_snapshot_json"]["paused"] is True
    assert cancel.status_code == 200
    assert cancel.json()["status"] in {"cancelled", "completed"}


def test_comparison_recommendation_and_report_indexing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario = client.post("/scenarios", json=_scenario_payload("Decision Flow", max_steps=8)).json()
    comparison = client.post(
        "/compare-plans",
        json={
            "scenario_id": scenario["id"],
            "strategies": ["auction_based", "information_gain"],
            "drone_counts": [3, 4],
            "coordination_modes": ["centralized"],
            "return_thresholds": [24.0, 28.0],
            "num_seeds": 1,
        },
    )
    recommendation = client.post("/recommend", json={"scenario_id": scenario["id"], "num_seeds": 1})
    run = client.post("/runs", json={"scenario_id": scenario["id"], "seed": 5}).json()
    completed = _wait_for_status(client, f"/runs/{run['id']}", {"completed", "failed"})
    report = client.post(f"/reports/{run['id']}")
    reports = client.get("/reports")

    assert comparison.status_code == 200
    assert recommendation.status_code == 200
    assert comparison.json()["ranked_plans"]
    assert recommendation.json()["recommended_strategy"] is not None
    assert completed["status"] == "completed"
    assert report.status_code == 200
    assert Path(report.json()["file_path"]).exists()
    assert any(item["id"] == report.json()["id"] for item in reports.json()["items"])


def test_experiment_and_frontend_compatible_history_flow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    experiment = client.post(
        "/experiments",
        json={
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
    ).json()
    completed = _wait_for_status(client, f"/experiments/{experiment['id']}", {"completed", "failed"}, timeout=40.0)
    summary = client.get(f"/experiments/{experiment['id']}/summary")
    jobs = client.get("/jobs")

    assert completed["status"] == "completed"
    assert summary.status_code == 200
    assert jobs.status_code == 200
    assert summary.json()["summary"]

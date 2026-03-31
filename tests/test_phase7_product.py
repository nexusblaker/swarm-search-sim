"""Phase 7 mission planning and evaluation product tests."""

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


def _scenario_payload(name: str, max_steps: int = 8) -> dict:
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


def _asset_package_payload() -> dict:
    return {
        "uniform_fleet": False,
        "staging_location": "Southern base",
        "drone_types": [
            {
                "display_name": "Scout quad",
                "count": 4,
                "max_endurance_minutes": 95,
                "estimated_max_range_km": 9,
                "cruise_speed_kph": 38,
                "sensor_capability_level": "standard",
                "thermal_capability_level": "assisted",
                "detection_capability_proxy": 1.0,
                "turnaround_time_minutes": 15,
                "notes": "",
            },
            {
                "display_name": "Long-range thermal",
                "count": 2,
                "max_endurance_minutes": 150,
                "estimated_max_range_km": 18,
                "cruise_speed_kph": 55,
                "sensor_capability_level": "enhanced",
                "thermal_capability_level": "full",
                "detection_capability_proxy": 1.18,
                "turnaround_time_minutes": 20,
                "notes": "",
            },
        ],
    }


def test_mission_plan_crud_and_recommendation_snapshot(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario = client.post("/scenarios", json=_scenario_payload("Plan Scenario")).json()

    created = client.post(
        "/plans",
        json={
            "name": "Primary Mission Plan",
            "scenario_id": scenario["id"],
            "strategy": "auction_based",
            "num_drones": 4,
            "approval_state": "recommended",
            "reserve_policy": {"return_threshold": 30.0},
            "communication_assumptions": {"coordination_mode": "centralized"},
            "operator_notes": "Primary daylight search plan.",
        },
    )
    assert created.status_code == 200
    plan_id = created.json()["id"]

    listed = client.get("/plans")
    loaded = client.get(f"/plans/{plan_id}")
    updated = client.put(
        f"/plans/{plan_id}",
        json={
            "name": "Primary Mission Plan Updated",
            "scenario_id": scenario["id"],
            "strategy": "information_gain",
            "num_drones": 5,
            "approval_state": "approved",
            "reserve_policy": {"return_threshold": 28.0},
            "communication_assumptions": {"coordination_mode": "decentralized"},
            "operator_notes": "Approved mission plan.",
        },
    )

    assert listed.status_code == 200
    assert loaded.status_code == 200
    assert updated.status_code == 200
    assert any(item["id"] == plan_id for item in listed.json()["items"])
    assert loaded.json()["recommendation_json"]
    assert updated.json()["approval_state"] == "approved"


def test_saved_comparison_and_launch_run_from_plan(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario = client.post("/scenarios", json=_scenario_payload("Comparison Scenario", max_steps=8)).json()
    plan = client.post(
        "/plans",
        json={
            "name": "Comparison Plan",
            "scenario_id": scenario["id"],
            "strategy": "information_gain",
            "num_drones": 4,
            "approval_state": "draft",
            "reserve_policy": {"return_threshold": 28.0},
            "communication_assumptions": {"coordination_mode": "centralized"},
        },
    ).json()

    comparison = client.post(
        "/comparisons",
        json={
            "plan_id": plan["id"],
            "strategies": ["auction_based", "information_gain"],
            "drone_counts": [3, 4],
            "coordination_modes": ["centralized"],
            "return_thresholds": [24.0, 28.0],
            "num_seeds": 1,
        },
    )
    assert comparison.status_code == 200
    comparison_id = comparison.json()["id"]
    assert comparison.json()["candidates"]

    run = client.post(
        f"/comparisons/{comparison_id}/run",
        json={"candidate_id": comparison.json()["candidates"][0]["id"], "seed": 7},
    )
    assert run.status_code == 200
    completed = _wait_for_status(client, f"/runs/{run.json()['id']}", {"completed", "failed"})

    summary = client.get(f"/comparisons/{comparison_id}/summary")
    assert completed["plan_id"] == plan["id"]
    assert completed["comparison_id"] == comparison_id
    assert summary.status_code == 200
    assert summary.json()["recommendation_snapshot"]


def test_after_action_review_and_library_flow(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    library = client.get("/library/templates")
    assert library.status_code == 200
    assert any(item["doctrine_type"] for item in library.json()["items"])

    template_id = library.json()["items"][0]["id"]
    plan = client.post(
        "/plans",
        json={
            "name": "Template-Based Plan",
            "template_id": template_id,
            "strategy": "information_gain",
            "num_drones": 4,
            "approval_state": "recommended",
            "reserve_policy": {"return_threshold": 26.0},
            "communication_assumptions": {"coordination_mode": "centralized"},
        },
    ).json()
    run = client.post("/runs", json={"plan_id": plan["id"], "seed": 9}).json()
    completed = _wait_for_status(client, f"/runs/{run['id']}", {"completed", "failed"})

    review = client.post(f"/reviews/from-run/{run['id']}")
    assert review.status_code == 200
    loaded = client.get(f"/reviews/{review.json()['id']}")

    assert completed["status"] == "completed"
    assert loaded.status_code == 200
    assert loaded.json()["summary_json"]["alternate_plan_summary"]
    assert loaded.json()["report"] is not None


def test_asset_package_persistence_and_concise_recommendation_summary(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario_payload = _scenario_payload("Mixed Fleet Intake", max_steps=8)

    created = client.post(
        "/plans",
        json={
            "name": "Mixed Fleet Intake",
            "scenario": scenario_payload,
            "asset_package": _asset_package_payload(),
            "mission_intent": "broad_area_coverage",
            "intake_summary": {"search_area_size": "large", "environment_type": "mixed_terrain"},
            "recommendation_num_seeds": 1,
        },
    )
    assert created.status_code == 200
    plan = created.json()

    recommendation = client.post(
        "/recommend",
        json={
            "plan_id": plan["id"],
            "mission_intent": "broad_area_coverage",
            "num_seeds": 1,
        },
    )
    assert recommendation.status_code == 200

    assert plan["asset_package"]["fleet_composition"]["total_drones"] == 6
    assert plan["summary_json"]["mission_intent"] == "broad_area_coverage"
    assert plan["recommendation_json"]["concise_summary"].startswith("Recommended:")
    assert recommendation.json()["asset_package"]["fleet_composition"]["drone_type_count"] == 2
    assert recommendation.json()["key_tradeoffs"]


def test_run_review_and_report_expose_battery_lifecycle_fields(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario_payload = _scenario_payload("Battery Lifecycle Product", max_steps=10)
    scenario_block = scenario_payload["scenario"]
    scenario_block["num_drones"] = 2
    scenario_block["step_duration_minutes"] = 1
    scenario_block.setdefault("drone", {}).update(
        {
            "battery": 48,
            "turnaround_time_minutes": 3,
            "estimated_max_range_km": 9,
        }
    )
    scenario_block.setdefault("battery_policy", {}).update(
        {"return_threshold": 12, "reserve_preset": "conservative"}
    )
    scenario_block.setdefault("sensor", {}).update(
        {
            "false_negative_rate": 1.0,
            "visual_false_negative_rate": 1.0,
            "false_positive_rate": 0.0,
        }
    )

    scenario = client.post("/scenarios", json=scenario_payload).json()
    run = client.post("/runs", json={"scenario_id": scenario["id"], "seed": 7})
    assert run.status_code == 200

    completed = _wait_for_status(client, f"/runs/{run.json()['id']}", {"completed", "failed"})
    replay = client.get(f"/runs/{run.json()['id']}/replay")
    events = client.get(f"/runs/{run.json()['id']}/events")
    report = client.post(f"/reports/{run.json()['id']}", json={})
    review = client.post(f"/reviews/from-run/{run.json()['id']}")

    assert completed["summary_json"]["lifecycle_summary"]["reserve_preset"] == "conservative"
    assert "lifecycle_state" in completed["latest_snapshot_json"]["drones"][0]
    assert "operator_status" in completed["latest_snapshot_json"]["drones"][0]
    assert replay.status_code == 200
    assert replay.json()["replay"][-1]["drones"][0]["lifecycle_state"]
    assert events.status_code == 200
    assert events.json()["events"]
    assert report.status_code == 200
    assert report.json()["summary_json"]["battery_lifecycle"]["run_phase"]
    assert review.status_code == 200
    assert review.json()["summary_json"]["battery_lifecycle"]["asset_utilization_summary"]
    assert review.json()["timeline_json"]["key_events"][0]["summary"]


def test_run_review_and_report_expose_sensing_lifecycle_fields(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    scenario_payload = _scenario_payload("Sensing Lifecycle Product", max_steps=10)
    scenario_block = scenario_payload["scenario"]
    scenario_block["num_drones"] = 1
    scenario_block["step_duration_minutes"] = 1
    scenario_block.setdefault("sensor", {}).update(
        {
            "false_negative_rate": 1.0,
            "visual_false_negative_rate": 1.0,
            "false_positive_rate": 1.0,
        }
    )
    scenario_block["target_move_probability"] = 0.0

    scenario = client.post("/scenarios", json=scenario_payload).json()
    run = client.post("/runs", json={"scenario_id": scenario["id"], "seed": 7})
    assert run.status_code == 200

    completed = _wait_for_status(client, f"/runs/{run.json()['id']}", {"completed", "failed"})
    events = client.get(f"/runs/{run.json()['id']}/events")
    report = client.post(f"/reports/{run.json()['id']}", json={})
    review = client.post(f"/reviews/from-run/{run.json()['id']}")

    assert completed["summary_json"]["sensing_summary"]["candidate_detection_count"] >= 1
    assert "sensing_state" in completed["latest_snapshot_json"]["drones"][0]
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()["events"]}
    assert "possible_contact_detected" in event_types
    assert report.status_code == 200
    assert report.json()["summary_json"]["sensing_lifecycle"]["candidate_detection_count"] >= 1
    assert review.status_code == 200
    assert review.json()["summary_json"]["sensing_lifecycle"]["operator_summary"]

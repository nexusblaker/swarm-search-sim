"""Mission run services and controllers."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

import yaml

from app.backend.core.job_manager import BackgroundJobManager
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.comparisons import PlanComparisonService
from app.backend.domain.plans import MissionPlanService
from app.backend.domain.scenarios import ScenarioService, TemplateService
from app.backend.domain.shared import read_json, read_jsonl, scenario_summary, to_jsonable
from app.backend.storage import LocalProductPaths
from src.scenarios.scenario import ScenarioConfig
from src.simulation.engine import SimulationEngine
from src.visualisation.renderer import SimulationRenderer


class MissionRunController:
    """Execute one mission in the background and mirror state to SQLite."""

    def __init__(
        self,
        run_id: str,
        job_id: str,
        scenario_id: str,
        scenario_payload: dict[str, Any],
        config: ScenarioConfig,
        paths: LocalProductPaths,
        store: MetadataStore,
        job_manager: BackgroundJobManager,
        plan_id: str | None = None,
        comparison_id: str | None = None,
        candidate_id: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.job_id = job_id
        self.scenario_id = scenario_id
        self.scenario_payload = scenario_payload
        self.config = config
        self.paths = paths
        self.store = store
        self.job_manager = job_manager
        self.plan_id = plan_id
        self.comparison_id = comparison_id
        self.candidate_id = candidate_id
        self.engine = SimulationEngine(config)
        self.output_dir = self.paths.runs_dir / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.output_dir / "metadata.json"
        self.lock = threading.RLock()
        (self.output_dir / "scenario.yaml").write_text(
            yaml.safe_dump(self.scenario_payload, sort_keys=False),
            encoding="utf-8",
        )
        self._persist_run("queued", self.engine.get_state_snapshot())

    def run(self, job_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        status = "running"
        try:
            while not self.engine.done:
                if cancel_event.is_set():
                    status = "cancelled"
                    break
                with self.lock:
                    if self.engine.paused:
                        status = "paused"
                        self._persist_run(status, self.engine.get_state_snapshot())
                        time.sleep(0.05)
                        continue
                    self.engine.step()
                    snapshot = self.engine.get_state_snapshot()
                progress = min(snapshot["step"] / max(self.config.max_steps, 1), 0.99)
                self.job_manager.update(job_id, progress=progress, summary={"step": snapshot["step"]})
                self._persist_run(status, snapshot)
                time.sleep(0.01)

            with self.lock:
                snapshot = self.engine.get_state_snapshot()
            if status != "cancelled":
                SimulationRenderer.render_static(
                    snapshot,
                    output_path=self.output_dir / "final_state.png",
                    show=False,
                )
                if self.config.save_frames:
                    SimulationRenderer.render_frames(
                        self.engine.history,
                        output_dir=self.output_dir / "frames",
                        step_stride=self.config.frame_stride,
                    )
                artifacts = self.engine.save_run_artifacts(self.output_dir)
                self._index_artifact("final_state", self.output_dir / "final_state.png")
                self._index_artifact("events", artifacts["events"])
                self._index_artifact("replay", artifacts["replay"])
                if self.config.save_frames:
                    self._index_artifact("frames_dir", self.output_dir / "frames")
                status = "completed"
            self._persist_run(status, snapshot)
            return self.get_record()
        except Exception as exc:  # pragma: no cover - background safety
            self._persist_run("failed", self.engine.get_state_snapshot(), error=f"{type(exc).__name__}: {exc}")
            raise

    def apply_intervention(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        with self.lock:
            result = self.engine.apply_intervention(action, payload)
            self.store.insert_intervention(self.run_id, action, to_jsonable(payload), time.time())
            self._persist_run("paused" if self.engine.paused else "running", self.engine.get_state_snapshot())
            return to_jsonable(result)

    def load_replay(self) -> list[dict[str, Any]]:
        replay_path = self.output_dir / "run_replay.json"
        if replay_path.exists():
            return read_json(replay_path)
        return to_jsonable(self.engine.history)

    def load_events(self) -> list[dict[str, Any]]:
        events_path = self.output_dir / "run_events.jsonl"
        if events_path.exists():
            return read_jsonl(events_path)
        return to_jsonable(self.engine.logger.events)

    def get_record(self) -> dict[str, Any]:
        record = self.store.get("runs", self.run_id)
        if record is None:
            raise FileNotFoundError(f"Unknown run: {self.run_id}")
        record["artifact_paths"] = {
            artifact["artifact_type"]: artifact["path"]
            for artifact in self.store.list_artifacts("run", self.run_id)
        }
        record["job"] = self.store.get("jobs", self.job_id)
        record["interventions"] = self.store.list_interventions(self.run_id)
        return record

    def _persist_run(self, status: str, snapshot: dict[str, Any], error: str | None = None) -> None:
        now = time.time()
        existing = self.store.get("runs", self.run_id)
        self.store.upsert(
            "runs",
            self.run_id,
            {
                "scenario_id": self.scenario_id,
                "plan_id": self.plan_id,
                "comparison_id": self.comparison_id,
                "candidate_id": self.candidate_id,
                "status": status,
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "completed_at": now if status in {"completed", "failed", "cancelled"} else None,
                "config_json": to_jsonable(self.scenario_payload),
                "summary_json": {
                    **scenario_summary(self.config),
                    "metrics": to_jsonable(asdict(self.engine.metrics)),
                    "run_phase": snapshot.get("run_phase"),
                    "lifecycle_summary": snapshot.get("lifecycle_summary", {}),
                    "drone_statuses": [
                        {
                            "id": drone["id"],
                            "operator_status": drone.get("operator_status"),
                            "reserve_status_label": drone.get("reserve_status_label"),
                            "battery_pct": drone.get("battery_pct"),
                            "return_service_eta_steps": drone.get("return_service_eta_steps"),
                        }
                        for drone in snapshot.get("drones", [])
                    ],
                    "error": error,
                    "plan_id": self.plan_id,
                    "comparison_id": self.comparison_id,
                    "candidate_id": self.candidate_id,
                },
                "latest_snapshot_json": to_jsonable(snapshot),
                "output_dir": str(self.output_dir.resolve()),
                "job_id": self.job_id,
            },
        )
        self.metadata_path.write_text(json.dumps(self.get_record(), indent=2), encoding="utf-8")

    def _index_artifact(self, artifact_type: str, path: Path) -> None:
        self.store.insert_artifact(
            "run",
            self.run_id,
            artifact_type,
            str(path.resolve()),
            {"exists": path.exists()},
            time.time(),
        )


class MissionService:
    """Manage mission runs and active controllers."""

    def __init__(
        self,
        paths: LocalProductPaths,
        store: MetadataStore,
        scenarios: ScenarioService,
        templates: TemplateService,
        plans: MissionPlanService,
        comparisons: PlanComparisonService,
        job_manager: BackgroundJobManager,
    ) -> None:
        self.paths = paths
        self.store = store
        self.scenarios = scenarios
        self.templates = templates
        self.plans = plans
        self.comparisons = comparisons
        self.job_manager = job_manager
        self.controllers: dict[str, MissionRunController] = {}

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_payload, scenario_id, plan_id, comparison_id, candidate_id, plan_context = self._resolve_run_request(request)
        config = self.scenarios.scenario_to_config(scenario_payload)
        if request.get("seed") is not None:
            config = replace(config, seed=int(request["seed"]))
        run_id = f"run-{uuid4().hex[:10]}"
        job_id = f"job-run-{uuid4().hex[:10]}"
        controller = MissionRunController(
            run_id,
            job_id,
            scenario_id,
            scenario_payload,
            config,
            self.paths,
            self.store,
            self.job_manager,
            plan_id=plan_id,
            comparison_id=comparison_id,
            candidate_id=candidate_id,
        )
        if plan_context:
            for zone in plan_context.get("priority_zones_json", []):
                controller.engine.apply_intervention("set_priority_zone", zone)
            for zone in plan_context.get("exclusion_zones_json", []):
                controller.engine.apply_intervention("set_exclusion_zone", zone)
            controller._persist_run("queued", controller.engine.get_state_snapshot())
        self.controllers[run_id] = controller
        self.job_manager.submit(job_id, "mission_run", "run", run_id, controller.run)
        if plan_id:
            self.plans.append_linked_run(plan_id, run_id)
        if comparison_id:
            self.comparisons.link_run(comparison_id, candidate_id, run_id)
        return controller.get_record()

    def list_runs(self) -> list[dict[str, Any]]:
        rows = self.store.list("runs")
        for row in rows:
            row["artifact_paths"] = {
                artifact["artifact_type"]: artifact["path"]
                for artifact in self.store.list_artifacts("run", row["id"])
            }
            row["job"] = self.store.get("jobs", row.get("job_id")) if row.get("job_id") else None
            row["interventions"] = self.store.list_interventions(row["id"])
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any]:
        if run_id in self.controllers:
            return self.controllers[run_id].get_record()
        record = self.store.get("runs", run_id)
        if record is None:
            raise FileNotFoundError(f"Unknown run: {run_id}")
        record["artifact_paths"] = {
            artifact["artifact_type"]: artifact["path"]
            for artifact in self.store.list_artifacts("run", run_id)
        }
        record["job"] = self.store.get("jobs", record.get("job_id")) if record.get("job_id") else None
        record["interventions"] = self.store.list_interventions(run_id)
        return record

    def get_replay(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self.controllers:
            return self.controllers[run_id].load_replay()
        return read_json(Path(self.get_run(run_id)["output_dir"]) / "run_replay.json")

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self.controllers:
            return self.controllers[run_id].load_events()
        return read_jsonl(Path(self.get_run(run_id)["output_dir"]) / "run_events.jsonl")

    def apply_intervention(self, run_id: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if run_id not in self.controllers:
            raise FileNotFoundError(f"Run {run_id} is no longer active for live intervention.")
        return self.controllers[run_id].apply_intervention(action, payload)

    def _resolve_run_request(
        self,
        request: dict[str, Any],
    ) -> tuple[dict[str, Any], str, str | None, str | None, str | None, dict[str, Any] | None]:
        plan_id = request.get("plan_id")
        comparison_id = request.get("comparison_id")
        candidate_id = request.get("candidate_id")
        if comparison_id:
            comparison = self.comparisons.get_comparison(str(comparison_id))
            plan_id = plan_id or comparison.get("plan_id")
            if candidate_id:
                candidate = self.store.get("plan_candidates", str(candidate_id))
            else:
                candidates = comparison.get("candidates", [])
                candidate = candidates[0] if candidates else None
                candidate_id = candidate.get("id") if candidate else None
            plan_record = self.plans.get_plan(plan_id) if plan_id else None
            scenario_payload = dict(plan_record["plan_json"]) if plan_record else dict(request.get("scenario", {}))
            if candidate:
                candidate_config = candidate["config_json"]
                scenario_payload["scenario"]["strategy"] = candidate_config["strategy"]
                scenario_payload["scenario"]["num_drones"] = int(candidate_config["drone_count"])
                scenario_payload["scenario"].setdefault("communication", {})["coordination_mode"] = candidate_config["coordination_mode"]
                scenario_payload["scenario"].setdefault("battery_policy", {})["return_threshold"] = float(
                    candidate_config["return_threshold"]
                )
            return (
                scenario_payload,
                plan_record["scenario_id"] if plan_record else "comparison",
                plan_id,
                str(comparison_id),
                candidate_id,
                plan_record,
            )
        if plan_id:
            plan_record = self.plans.get_plan(str(plan_id))
            return plan_record["plan_json"], plan_record.get("scenario_id") or "plan", str(plan_id), None, None, plan_record
        if request.get("scenario_id"):
            record = self.scenarios.load_scenario(str(request["scenario_id"]))
            return record["config_json"], record["id"], None, None, None, None
        if request.get("template_id"):
            template = self.templates.get_template(str(request["template_id"]))
            return template["config_json"], f"template:{template['id']}", None, None, None, None
        if request.get("scenario"):
            return dict(request["scenario"]), "adhoc", None, None, None, None
        raise ValueError("A run request requires plan_id, comparison_id, scenario_id, template_id, or scenario.")

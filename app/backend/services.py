"""Phase 6 product services with SQLite indexing and background jobs."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

import pandas as pd
import yaml

from app.backend.core.job_manager import BackgroundJobManager
from app.backend.core.settings import BackendSettings
from app.backend.core.templates import built_in_templates
from app.backend.db.sqlite import MetadataStore
from app.backend.reporting import ReportGenerator
from app.backend.storage import LocalProductPaths, slugify
from benchmark import run_benchmarks, run_grouped_experiments
from src.scenarios.scenario import ScenarioConfig
from src.simulation.engine import SimulationEngine
from src.utils.config_loader import DEFAULT_CONFIG_PATH, load_config, load_scenario_config
from src.utils.event_logger import EventLogger
from src.visualisation.renderer import SimulationRenderer


def to_jsonable(value: Any) -> Any:
    """Convert nested simulator state into JSON-safe values."""

    return EventLogger._sanitize(value)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _scenario_summary(config: ScenarioConfig) -> dict[str, Any]:
    return {
        "strategy": config.strategy,
        "scenario_family": config.scenario_family,
        "num_drones": config.num_drones,
        "map_size": list(config.map_size),
        "weather": config.weather,
        "target_behavior": config.target_behavior,
        "coordination_mode": config.coordination_mode,
        "return_to_base_threshold": config.return_to_base_threshold,
    }


class ScenarioService:
    """Persist and retrieve product-facing scenarios."""

    def __init__(self, paths: LocalProductPaths, store: MetadataStore) -> None:
        self.paths = paths
        self.store = store
        self._bootstrap_default()

    def list_scenarios(self) -> list[dict[str, Any]]:
        rows = self.store.list("scenarios", "deleted_at IS NULL")
        return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    def load_scenario(self, scenario_id: str) -> dict[str, Any]:
        record = self.store.get("scenarios", scenario_id)
        if record is None or record.get("deleted_at") is not None:
            raise FileNotFoundError(f"Unknown scenario: {scenario_id}")
        return record

    def create_scenario(self, payload: dict[str, Any], scenario_id: str | None = None) -> dict[str, Any]:
        scenario_name = payload.get("scenario", {}).get("name") or scenario_id or f"scenario-{uuid4().hex[:8]}"
        safe_id = slugify(scenario_id or scenario_name)
        return self._persist_scenario(safe_id, payload, existing=self.store.get("scenarios", safe_id))

    def update_scenario(self, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._persist_scenario(scenario_id, payload, existing=self.store.get("scenarios", scenario_id))

    def delete_scenario(self, scenario_id: str) -> None:
        record = self.load_scenario(scenario_id)
        now = time.time()
        self.store.upsert(
            "scenarios",
            scenario_id,
            {
                "name": record["name"],
                "type": record.get("type", "scenario"),
                "created_at": record["created_at"],
                "updated_at": now,
                "deleted_at": now,
                "config_json": record["config_json"],
                "summary_json": record["summary_json"],
                "file_path": record.get("file_path"),
            },
        )
        file_path = Path(record["file_path"])
        if file_path.exists():
            file_path.unlink()

    def get_presets(self) -> dict[str, Any]:
        default_raw = load_config(DEFAULT_CONFIG_PATH)
        config = load_scenario_config(DEFAULT_CONFIG_PATH)
        return {
            "default": to_jsonable(default_raw),
            "scenario_families": [
                "open_terrain",
                "dense_forest",
                "mixed_terrain",
                "obstacle_heavy",
                "poor_comms",
                "high_wind",
                "low_battery_budget",
                "layered_demo",
            ],
            "strategies": config.benchmark_strategies,
            "target_behaviors": [
                "random_walk",
                "terrain_biased",
                "trail_biased",
                "injured_slow",
                "stationary_intervals",
            ],
            "coordination_modes": list(config.benchmark_coordination_modes),
            "sensor_modes": list(config.benchmark_sensor_modes),
        }

    @staticmethod
    def scenario_to_config(payload: dict[str, Any]) -> ScenarioConfig:
        return ScenarioConfig.from_dict(payload)

    def _bootstrap_default(self) -> None:
        default_payload = load_config(DEFAULT_CONFIG_PATH)
        self.create_scenario(default_payload, scenario_id="default")

    def _persist_scenario(
        self,
        scenario_id: str,
        payload: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> dict[str, Any]:
        config = self.scenario_to_config(payload)
        file_path = self.paths.scenarios_dir / f"{scenario_id}.yaml"
        file_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        now = time.time()
        self.store.upsert(
            "scenarios",
            scenario_id,
            {
                "name": payload.get("scenario", {}).get("name", scenario_id),
                "type": "scenario",
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "deleted_at": None,
                "config_json": to_jsonable(payload),
                "summary_json": _scenario_summary(config),
                "file_path": str(file_path.resolve()),
            },
        )
        return self.load_scenario(scenario_id)


class TemplateService:
    """Manage built-in scenario templates."""

    def __init__(self, paths: LocalProductPaths, store: MetadataStore) -> None:
        self.paths = paths
        self.store = store
        self._bootstrap_templates()

    def list_templates(self) -> list[dict[str, Any]]:
        rows = self.store.list("scenario_templates")
        return sorted(rows, key=lambda item: item["name"])

    def get_template(self, template_id: str) -> dict[str, Any]:
        record = self.store.get("scenario_templates", template_id)
        if record is None:
            raise FileNotFoundError(f"Unknown template: {template_id}")
        return record

    def _bootstrap_templates(self) -> None:
        for template in built_in_templates():
            template_id = template["template_id"]
            file_path = self.paths.templates_dir / f"{template_id}.yaml"
            file_path.write_text(
                yaml.safe_dump(template["payload"], sort_keys=False),
                encoding="utf-8",
            )
            config = ScenarioService.scenario_to_config(template["payload"])
            now = time.time()
            existing = self.store.get("scenario_templates", template_id)
            self.store.upsert(
                "scenario_templates",
                template_id,
                {
                    "name": template["name"],
                    "family": template["family"],
                    "description": template["description"],
                    "created_at": existing["created_at"] if existing else now,
                    "updated_at": now,
                    "config_json": to_jsonable(template["payload"]),
                    "summary_json": _scenario_summary(config),
                    "file_path": str(file_path.resolve()),
                },
            )


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
    ) -> None:
        self.run_id = run_id
        self.job_id = job_id
        self.scenario_id = scenario_id
        self.scenario_payload = scenario_payload
        self.config = config
        self.paths = paths
        self.store = store
        self.job_manager = job_manager
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
                status = "running"
                progress = min(snapshot["step"] / max(self.config.max_steps, 1), 0.99)
                self.job_manager.update(
                    job_id,
                    progress=progress,
                    summary={"step": snapshot["step"]},
                )
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
            self._persist_run(
                "failed",
                self.engine.get_state_snapshot(),
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    def apply_intervention(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = payload or {}
        with self.lock:
            result = self.engine.apply_intervention(action, payload)
            self.store.insert_intervention(
                self.run_id,
                action,
                to_jsonable(payload),
                time.time(),
            )
            self._persist_run(
                "paused" if self.engine.paused else "running",
                self.engine.get_state_snapshot(),
            )
            return to_jsonable(result)

    def load_replay(self) -> list[dict[str, Any]]:
        replay_path = self.output_dir / "run_replay.json"
        if replay_path.exists():
            return _read_json(replay_path)
        return to_jsonable(self.engine.history)

    def load_events(self) -> list[dict[str, Any]]:
        events_path = self.output_dir / "run_events.jsonl"
        if events_path.exists():
            return _read_jsonl(events_path)
        return to_jsonable(self.engine.logger.events)

    def get_record(self) -> dict[str, Any]:
        record = self.store.get("runs", self.run_id)
        if record is None:
            raise FileNotFoundError(f"Unknown run: {self.run_id}")
        artifacts = self.store.list_artifacts("run", self.run_id)
        record["artifact_paths"] = {
            artifact["artifact_type"]: artifact["path"]
            for artifact in artifacts
        }
        record["job"] = self.store.get("jobs", self.job_id)
        record["interventions"] = self.store.list_interventions(self.run_id)
        return record

    def _persist_run(
        self,
        status: str,
        snapshot: dict[str, Any],
        error: str | None = None,
    ) -> None:
        now = time.time()
        existing = self.store.get("runs", self.run_id)
        self.store.upsert(
            "runs",
            self.run_id,
            {
                "scenario_id": self.scenario_id,
                "status": status,
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "completed_at": now if status in {"completed", "failed", "cancelled"} else None,
                "config_json": to_jsonable(self.scenario_payload),
                "summary_json": {
                    **_scenario_summary(self.config),
                    "metrics": to_jsonable(asdict(self.engine.metrics)),
                    "error": error,
                },
                "latest_snapshot_json": to_jsonable(snapshot),
                "output_dir": str(self.output_dir.resolve()),
                "job_id": self.job_id,
            },
        )
        self.metadata_path.write_text(
            json.dumps(self.get_record(), indent=2),
            encoding="utf-8",
        )

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
        scenario_service: ScenarioService,
        template_service: TemplateService,
        job_manager: BackgroundJobManager,
    ) -> None:
        self.paths = paths
        self.store = store
        self.scenario_service = scenario_service
        self.template_service = template_service
        self.job_manager = job_manager
        self.controllers: dict[str, MissionRunController] = {}

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_payload, scenario_id = self._resolve_scenario_request(request)
        config = self.scenario_service.scenario_to_config(scenario_payload)
        if "seed" in request and request["seed"] is not None:
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
        )
        self.controllers[run_id] = controller
        self.job_manager.submit(
            job_id,
            "mission_run",
            "run",
            run_id,
            controller.run,
        )
        return controller.get_record()

    def list_runs(self) -> list[dict[str, Any]]:
        rows = self.store.list("runs")
        for row in rows:
            row["artifact_paths"] = {
                artifact["artifact_type"]: artifact["path"]
                for artifact in self.store.list_artifacts("run", row["id"])
            }
            row["job"] = self.store.get("jobs", row.get("job_id")) if row.get("job_id") else None
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
        replay_path = Path(self.get_run(run_id)["output_dir"]) / "run_replay.json"
        return _read_json(replay_path)

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self.controllers:
            return self.controllers[run_id].load_events()
        events_path = Path(self.get_run(run_id)["output_dir"]) / "run_events.jsonl"
        return _read_jsonl(events_path)

    def apply_intervention(
        self,
        run_id: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.controllers[run_id].apply_intervention(action, payload)

    def _resolve_scenario_request(
        self,
        request: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        if request.get("scenario_id"):
            record = self.scenario_service.load_scenario(str(request["scenario_id"]))
            return record["config_json"], record["id"]
        if request.get("template_id"):
            template = self.template_service.get_template(str(request["template_id"]))
            return template["config_json"], f"template:{template['id']}"
        if request.get("scenario"):
            return dict(request["scenario"]), "adhoc"
        raise ValueError("A run request requires scenario_id, template_id, or scenario.")


class ExperimentController:
    """Execute experiment batches in the background and index outputs."""

    def __init__(
        self,
        experiment_id: str,
        job_id: str,
        request: dict[str, Any],
        paths: LocalProductPaths,
        store: MetadataStore,
        job_manager: BackgroundJobManager,
    ) -> None:
        self.experiment_id = experiment_id
        self.job_id = job_id
        self.request = request
        self.paths = paths
        self.store = store
        self.job_manager = job_manager
        self.output_dir = self.paths.experiments_dir / self.experiment_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._persist("queued")

    def run(self, job_id: str, cancel_event: threading.Event) -> dict[str, Any]:
        try:
            if cancel_event.is_set():
                self._persist("cancelled")
                return self.get_record()
            run_benchmarks(
                output_dir=self.output_dir,
                num_seeds=int(self.request.get("benchmark_num_seeds", 4)),
                strategies=self.request.get("strategies"),
            )
            self.job_manager.update(job_id, progress=0.5)
            if cancel_event.is_set():
                self._persist("cancelled")
                return self.get_record()
            run_grouped_experiments(
                output_dir=self.output_dir,
                num_seeds=int(self.request.get("experiment_num_seeds", 1)),
                strategies=self.request.get("strategies"),
                scenario_families=self.request.get("scenario_families"),
                target_behaviors=self.request.get("target_behaviors"),
                coordination_modes=self.request.get("coordination_modes"),
                drone_counts=self.request.get("drone_counts"),
                battery_budgets=self.request.get("battery_budgets"),
                sensor_modes=self.request.get("sensor_modes"),
            )
            for path in self.output_dir.iterdir():
                if path.is_file():
                    self.store.insert_artifact(
                        "experiment",
                        self.experiment_id,
                        path.stem,
                        str(path.resolve()),
                        {"suffix": path.suffix},
                        time.time(),
                    )
            self._persist("completed")
            return self.get_record()
        except Exception as exc:  # pragma: no cover - background safety
            self._persist("failed", error=f"{type(exc).__name__}: {exc}")
            raise

    def get_record(self) -> dict[str, Any]:
        record = self.store.get("experiments", self.experiment_id)
        if record is None:
            raise FileNotFoundError(f"Unknown experiment: {self.experiment_id}")
        record["artifact_paths"] = {
            artifact["artifact_type"]: artifact["path"]
            for artifact in self.store.list_artifacts("experiment", self.experiment_id)
        }
        record["job"] = self.store.get("jobs", self.job_id)
        return record

    def _persist(self, status: str, error: str | None = None) -> None:
        now = time.time()
        summary = {}
        summary_path = self.output_dir / "experiment_summary.csv"
        if summary_path.exists():
            summary = pd.read_csv(summary_path).head(20).to_dict(orient="records")
        existing = self.store.get("experiments", self.experiment_id)
        self.store.upsert(
            "experiments",
            self.experiment_id,
            {
                "status": status,
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "completed_at": now if status in {"completed", "failed", "cancelled"} else None,
                "request_json": to_jsonable(self.request),
                "summary_json": summary,
                "output_dir": str(self.output_dir.resolve()),
                "job_id": self.job_id,
                "error": error,
            },
        )


class ExperimentService:
    """Manage experiment history and active experiment jobs."""

    def __init__(
        self,
        paths: LocalProductPaths,
        store: MetadataStore,
        job_manager: BackgroundJobManager,
    ) -> None:
        self.paths = paths
        self.store = store
        self.job_manager = job_manager
        self.controllers: dict[str, ExperimentController] = {}

    def create_experiment(self, request: dict[str, Any]) -> dict[str, Any]:
        experiment_id = f"experiment-{uuid4().hex[:10]}"
        job_id = f"job-experiment-{uuid4().hex[:10]}"
        controller = ExperimentController(
            experiment_id,
            job_id,
            request,
            self.paths,
            self.store,
            self.job_manager,
        )
        self.controllers[experiment_id] = controller
        self.job_manager.submit(
            job_id,
            "experiment_batch",
            "experiment",
            experiment_id,
            controller.run,
        )
        return controller.get_record()

    def list_experiments(self) -> list[dict[str, Any]]:
        rows = self.store.list("experiments")
        for row in rows:
            row["artifact_paths"] = {
                artifact["artifact_type"]: artifact["path"]
                for artifact in self.store.list_artifacts("experiment", row["id"])
            }
            row["job"] = self.store.get("jobs", row.get("job_id")) if row.get("job_id") else None
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        if experiment_id in self.controllers:
            return self.controllers[experiment_id].get_record()
        record = self.store.get("experiments", experiment_id)
        if record is None:
            raise FileNotFoundError(f"Unknown experiment: {experiment_id}")
        record["artifact_paths"] = {
            artifact["artifact_type"]: artifact["path"]
            for artifact in self.store.list_artifacts("experiment", experiment_id)
        }
        record["job"] = self.store.get("jobs", record.get("job_id")) if record.get("job_id") else None
        return record

    def load_experiment_summary(self, experiment_id: str) -> list[dict[str, Any]]:
        record = self.get_experiment(experiment_id)
        return record.get("summary_json", [])


class ComparisonService:
    """Compare candidate mission plans before launch."""

    def __init__(self, scenario_service: ScenarioService, settings: BackendSettings) -> None:
        self.scenario_service = scenario_service
        self.settings = settings

    def compare(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_payload = self._resolve_payload(request)
        base_config = self.scenario_service.scenario_to_config(scenario_payload)
        strategies = request.get("strategies") or [base_config.strategy]
        drone_counts = request.get("drone_counts") or [base_config.num_drones]
        coordination_modes = request.get("coordination_modes") or [base_config.coordination_mode]
        return_thresholds = request.get("return_thresholds") or [base_config.return_to_base_threshold]
        num_seeds = int(request.get("num_seeds", self.settings.comparison_num_seeds))

        ranked_plans: list[dict[str, Any]] = []
        for strategy in strategies:
            for drone_count in drone_counts:
                for coordination_mode in coordination_modes:
                    for threshold in return_thresholds:
                        metrics = []
                        for seed in range(num_seeds):
                            config = replace(
                                base_config,
                                strategy=strategy,
                                num_drones=int(drone_count),
                                coordination_mode=str(coordination_mode),
                                return_to_base_threshold=float(threshold),
                                seed=base_config.seed + seed,
                                max_steps=min(base_config.max_steps, 30),
                            )
                            engine = SimulationEngine(config)
                            metrics.append(engine.run())
                        success_rate = float(sum(metric.mission_success for metric in metrics) / len(metrics))
                        detection_times = [
                            metric.time_to_confirmed_detection or base_config.max_steps
                            for metric in metrics
                        ]
                        expected_detection_time = float(sum(detection_times) / len(detection_times))
                        expected_overlap = float(sum(metric.overlap_ratio for metric in metrics) / len(metrics))
                        battery_risk = float(
                            sum(
                                metric.battery_used / max(config.drone_battery * config.num_drones, 1.0)
                                for metric in metrics
                            )
                            / len(metrics)
                        )
                        score = (
                            100.0 * success_rate
                            - 0.8 * expected_detection_time
                            - 20.0 * expected_overlap
                            - 15.0 * battery_risk
                        )
                        ranked_plans.append(
                            {
                                "strategy": strategy,
                                "drone_count": int(drone_count),
                                "coordination_mode": str(coordination_mode),
                                "return_threshold": float(threshold),
                                "expected_success_rate": round(success_rate, 3),
                                "expected_detection_time": round(expected_detection_time, 2),
                                "expected_battery_risk": round(battery_risk, 3),
                                "expected_overlap": round(expected_overlap, 3),
                                "score": round(score, 2),
                                "tradeoff_summary": self._tradeoff_summary(
                                    success_rate,
                                    expected_detection_time,
                                    battery_risk,
                                    expected_overlap,
                                ),
                            }
                        )
        ranked_plans.sort(key=lambda item: item["score"], reverse=True)
        return {
            "ranked_plans": ranked_plans,
            "top_recommendation": ranked_plans[0] if ranked_plans else {},
            "confidence_summary": {
                "candidate_count": len(ranked_plans),
                "evaluation_seeds": num_seeds,
                "method": "short benchmark bundle",
            },
        }

    def _resolve_payload(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("scenario_id"):
            return self.scenario_service.load_scenario(request["scenario_id"])["config_json"]
        if request.get("scenario"):
            return request["scenario"]
        raise ValueError("Comparison requires scenario_id or scenario.")

    @staticmethod
    def _tradeoff_summary(
        success_rate: float,
        detection_time: float,
        battery_risk: float,
        overlap: float,
    ) -> str:
        traits: list[str] = []
        traits.append("higher confidence" if success_rate >= 0.7 else "lower confidence")
        traits.append("fast detection" if detection_time <= 15 else "slower detection")
        traits.append("battery conservative" if battery_risk <= 0.6 else "battery intensive")
        traits.append("low overlap" if overlap <= 0.8 else "higher overlap")
        return ", ".join(traits)


class RecommendationService:
    """Explainable mission recommendations using heuristics and plan comparison."""

    def __init__(self, comparison_service: ComparisonService) -> None:
        self.comparison_service = comparison_service

    def recommend(self, request: dict[str, Any]) -> dict[str, Any]:
        comparison = self.comparison_service.compare(
            {
                **request,
                "strategies": request.get("strategies")
                or ["information_gain", "auction_based", "probability_greedy", "sector_search"],
                "drone_counts": request.get("drone_counts"),
                "coordination_modes": request.get("coordination_modes"),
                "return_thresholds": request.get("return_thresholds"),
                "num_seeds": request.get("num_seeds", 2),
            }
        )
        top = comparison["top_recommendation"]
        explanation = (
            f"Recommend {top.get('strategy')} with {top.get('drone_count')} drones and "
            f"return threshold {top.get('return_threshold')} because it balances "
            f"success rate, detection time, overlap, and battery reserve."
        )
        return {
            "recommended_strategy": top.get("strategy"),
            "recommended_drone_count": top.get("drone_count"),
            "recommended_return_threshold": top.get("return_threshold"),
            "risk_summary": {
                "overall_risk": "moderate",
                "battery_risk": top.get("expected_battery_risk"),
                "overlap_risk": top.get("expected_overlap"),
                "confidence_basis": comparison["confidence_summary"],
            },
            "explanation": explanation,
            "candidate_plans": comparison["ranked_plans"],
        }


class ReportService:
    """Generate and index mission reports."""

    def __init__(
        self,
        store: MetadataStore,
        generator: ReportGenerator,
        recommendation_service: RecommendationService,
    ) -> None:
        self.store = store
        self.generator = generator
        self.recommendation_service = recommendation_service

    def list_reports(self) -> list[dict[str, Any]]:
        rows = self.store.list("reports")
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_report(self, report_id: str) -> dict[str, Any]:
        record = self.store.get("reports", report_id)
        if record is None:
            raise FileNotFoundError(f"Unknown report: {report_id}")
        return record

    def generate_run_report(
        self,
        run_record: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        recommendation = self.recommendation_service.recommend(
            {"scenario": run_record["config_json"], "num_seeds": 1}
        )
        enriched = dict(run_record)
        enriched["recommendation"] = recommendation
        report_path = self.generator.generate_run_report(enriched, events)
        report_id = f"report-{uuid4().hex[:10]}"
        now = time.time()
        self.store.upsert(
            "reports",
            report_id,
            {
                "run_id": run_record["id"],
                "report_type": "mission_summary",
                "created_at": now,
                "summary_json": {
                    "run_id": run_record["id"],
                    "strategy": run_record["summary_json"].get("strategy"),
                    "recommended_strategy": recommendation.get("recommended_strategy"),
                },
                "file_path": str(report_path.resolve()),
            },
        )
        self.store.insert_artifact(
            "report",
            report_id,
            "html_report",
            str(report_path.resolve()),
            {},
            now,
        )
        return self.get_report(report_id)


class ProductBackend:
    """Aggregate backend services for the FastAPI product layer."""

    def __init__(self, settings: BackendSettings | None = None) -> None:
        self.settings = settings or BackendSettings.from_env()
        self.paths = LocalProductPaths.create(self.settings.storage_root)
        self.store = MetadataStore(self.settings.db_path)
        self.job_manager = BackgroundJobManager(
            self.store,
            max_workers=self.settings.job_max_workers,
        )
        self.scenarios = ScenarioService(self.paths, self.store)
        self.templates = TemplateService(self.paths, self.store)
        self.missions = MissionService(
            self.paths,
            self.store,
            self.scenarios,
            self.templates,
            self.job_manager,
        )
        self.experiments = ExperimentService(
            self.paths,
            self.store,
            self.job_manager,
        )
        self.comparison = ComparisonService(self.scenarios, self.settings)
        self.recommendations = RecommendationService(self.comparison)
        self.reports = ReportService(
            self.store,
            ReportGenerator(self.paths),
            self.recommendations,
        )

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "database_path": str(Path(self.settings.db_path).resolve()),
            "storage_root": str(Path(self.settings.storage_root).resolve()),
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.job_manager.list()

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self.job_manager.get(job_id)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        return self.job_manager.cancel(job_id)

    def generate_report(self, run_id: str) -> dict[str, Any]:
        run_record = self.missions.get_run(run_id)
        events = self.missions.get_events(run_id)
        return self.reports.generate_run_report(run_record, events)

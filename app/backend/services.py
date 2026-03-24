"""Local product services for scenarios, runs, experiments, and reports."""

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


class ScenarioService:
    """Persist and retrieve product-facing scenario definitions."""

    def __init__(self, paths: LocalProductPaths) -> None:
        self.paths = paths
        self._bootstrap_default()

    def list_scenarios(self) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for path in sorted(self.paths.scenarios_dir.glob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            scenarios.append(self._build_scenario_record(path.stem, raw, path))
        return scenarios

    def load_scenario(self, scenario_id: str) -> dict[str, Any]:
        path = self.paths.scenarios_dir / f"{scenario_id}.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return self._build_scenario_record(scenario_id, raw, path, include_payload=True)

    def save_scenario(
        self,
        payload: dict[str, Any],
        scenario_id: str | None = None,
    ) -> dict[str, Any]:
        scenario_name = (
            payload.get("scenario", {}).get("name")
            or scenario_id
            or f"scenario-{uuid4().hex[:8]}"
        )
        safe_id = slugify(scenario_id or scenario_name)
        path = self.paths.scenarios_dir / f"{safe_id}.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return self._build_scenario_record(safe_id, payload, path, include_payload=True)

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
        default_path = self.paths.scenarios_dir / "default.yaml"
        if default_path.exists():
            return
        default_path.write_text(Path(DEFAULT_CONFIG_PATH).read_text(encoding="utf-8"), encoding="utf-8")

    def _build_scenario_record(
        self,
        scenario_id: str,
        raw: dict[str, Any],
        path: Path,
        include_payload: bool = False,
    ) -> dict[str, Any]:
        config = self.scenario_to_config(raw)
        record = {
            "scenario_id": scenario_id,
            "name": raw.get("scenario", {}).get("name", scenario_id),
            "path": str(path.resolve()),
            "updated_at": path.stat().st_mtime,
            "summary": {
                "strategy": config.strategy,
                "scenario_family": config.scenario_family,
                "num_drones": config.num_drones,
                "map_size": list(config.map_size),
                "weather": config.weather,
                "target_behavior": config.target_behavior,
            },
        }
        if include_payload:
            record["payload"] = to_jsonable(raw)
        return record


class MissionRunController:
    """Execute one mission run in a background thread."""

    def __init__(
        self,
        run_id: str,
        scenario_id: str,
        scenario_payload: dict[str, Any],
        config: ScenarioConfig,
        paths: LocalProductPaths,
    ) -> None:
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.scenario_payload = scenario_payload
        self.config = config
        self.paths = paths
        self.output_dir = self.paths.runs_dir / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.engine = SimulationEngine(config)
        self.status = "created"
        self.error: str | None = None
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.completed_at: float | None = None
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self.latest_snapshot = self.engine.get_state_snapshot()
        self.artifact_paths: dict[str, str] = {}
        self.metadata_path = self.output_dir / "metadata.json"
        (self.output_dir / "scenario.yaml").write_text(
            yaml.safe_dump(self.scenario_payload, sort_keys=False),
            encoding="utf-8",
        )
        self._persist()

    def start(self) -> None:
        self.thread = threading.Thread(target=self._execute, daemon=True, name=f"mission-{self.run_id}")
        self.thread.start()

    def apply_intervention(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.lock:
            result = self.engine.apply_intervention(action, payload)
            self.status = "paused" if self.engine.paused else "running"
            self.latest_snapshot = self.engine.get_state_snapshot()
            self.updated_at = time.time()
            self._persist()
            return to_jsonable(result)

    def get_record(self, include_snapshot: bool = True) -> dict[str, Any]:
        with self.lock:
            record = {
                "run_id": self.run_id,
                "scenario_id": self.scenario_id,
                "status": self.status,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "completed_at": self.completed_at,
                "error": self.error,
                "metrics": to_jsonable(asdict(self.engine.metrics)),
                "artifact_paths": dict(self.artifact_paths),
                "output_dir": str(self.output_dir.resolve()),
                "summary": {
                    "strategy": self.config.strategy,
                    "scenario_family": self.config.scenario_family,
                    "num_drones": self.config.num_drones,
                    "target_behavior": self.config.target_behavior,
                    "max_steps": self.config.max_steps,
                },
            }
            if include_snapshot:
                record["latest_snapshot"] = to_jsonable(self.latest_snapshot)
            return record

    def load_events(self) -> list[dict[str, Any]]:
        with self.lock:
            events_path = self.output_dir / "run_events.jsonl"
            if events_path.exists():
                return [
                    json.loads(line)
                    for line in events_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            return to_jsonable(self.engine.logger.events)

    def load_replay(self) -> list[dict[str, Any]]:
        with self.lock:
            replay_path = self.output_dir / "run_replay.json"
            if replay_path.exists():
                return json.loads(replay_path.read_text(encoding="utf-8"))
            return to_jsonable(self.engine.history)

    def _execute(self) -> None:
        try:
            self.status = "running"
            self._persist()
            while not self.engine.done:
                with self.lock:
                    is_paused = self.engine.paused
                if is_paused:
                    self.status = "paused"
                    self.updated_at = time.time()
                    self._persist()
                    time.sleep(0.05)
                    continue
                self.status = "running"
                with self.lock:
                    self.engine.step()
                    self.latest_snapshot = self.engine.get_state_snapshot()
                self.updated_at = time.time()
                self._persist()
                time.sleep(0.01)

            with self.lock:
                final_snapshot = self.engine.get_state_snapshot()
            SimulationRenderer.render_static(
                final_snapshot,
                output_path=self.output_dir / "final_state.png",
                show=False,
            )
            if self.config.save_frames:
                SimulationRenderer.render_frames(
                    self.engine.history,
                    output_dir=self.output_dir / "frames",
                    step_stride=self.config.frame_stride,
                )
            with self.lock:
                artifacts = self.engine.save_run_artifacts(self.output_dir)
            self.artifact_paths = {
                "final_state": str((self.output_dir / "final_state.png").resolve()),
                "events": str(artifacts["events"].resolve()),
                "replay": str(artifacts["replay"].resolve()),
                "frames_dir": str((self.output_dir / "frames").resolve()),
            }
            self.latest_snapshot = final_snapshot
            self.status = "completed"
            self.completed_at = time.time()
            self.updated_at = self.completed_at
            self._persist()
        except Exception as exc:  # pragma: no cover - defensive runtime safeguard
            self.status = "failed"
            self.error = f"{type(exc).__name__}: {exc}"
            self.updated_at = time.time()
            self._persist()

    def _persist(self) -> None:
        self.metadata_path.write_text(
            json.dumps(to_jsonable(self.get_record(include_snapshot=True)), indent=2),
            encoding="utf-8",
        )


class MissionService:
    """Manage mission runs and operator interventions."""

    def __init__(self, paths: LocalProductPaths, scenario_service: ScenarioService) -> None:
        self.paths = paths
        self.scenario_service = scenario_service
        self.controllers: dict[str, MissionRunController] = {}

    def create_run(self, request: dict[str, Any]) -> dict[str, Any]:
        scenario_id = str(request.get("scenario_id", ""))
        scenario_payload = (
            self.scenario_service.load_scenario(scenario_id)["payload"]
            if scenario_id
            else dict(request["scenario"])
        )
        config = ScenarioService.scenario_to_config(scenario_payload)
        if "seed" in request:
            config = replace(config, seed=int(request["seed"]))
        run_id = f"run-{uuid4().hex[:10]}"
        controller = MissionRunController(run_id, scenario_id or "adhoc", scenario_payload, config, self.paths)
        self.controllers[run_id] = controller
        controller.start()
        return controller.get_record()

    def list_runs(self) -> list[dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for path in self.paths.runs_dir.glob("*/metadata.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            records[record["run_id"]] = record
        for run_id, controller in self.controllers.items():
            records[run_id] = controller.get_record()
        return sorted(records.values(), key=lambda item: item["created_at"], reverse=True)

    def get_run(self, run_id: str) -> dict[str, Any]:
        if run_id in self.controllers:
            return self.controllers[run_id].get_record()
        path = self.paths.runs_dir / run_id / "metadata.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def get_replay(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self.controllers:
            return self.controllers[run_id].load_replay()
        replay_path = self.paths.runs_dir / run_id / "run_replay.json"
        return json.loads(replay_path.read_text(encoding="utf-8"))

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self.controllers:
            return self.controllers[run_id].load_events()
        events_path = self.paths.runs_dir / run_id / "run_events.jsonl"
        return [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def apply_intervention(self, run_id: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.controllers[run_id].apply_intervention(action, payload)


class ExperimentController:
    """Run benchmark batches in a background thread."""

    def __init__(self, experiment_id: str, request: dict[str, Any], paths: LocalProductPaths) -> None:
        self.experiment_id = experiment_id
        self.request = request
        self.paths = paths
        self.output_dir = self.paths.experiments_dir / self.experiment_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.status = "created"
        self.error: str | None = None
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.completed_at: float | None = None
        self.metadata_path = self.output_dir / "metadata.json"
        self.thread: threading.Thread | None = None
        self._persist()

    def start(self) -> None:
        self.thread = threading.Thread(target=self._execute, daemon=True, name=f"experiment-{self.experiment_id}")
        self.thread.start()

    def get_record(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "output_dir": str(self.output_dir.resolve()),
            "request": to_jsonable(self.request),
            "artifact_paths": {
                "benchmark_results": str((self.output_dir / "benchmark_results.csv").resolve()),
                "benchmark_summary": str((self.output_dir / "benchmark_summary.csv").resolve()),
                "experiment_results": str((self.output_dir / "experiment_results.csv").resolve()),
                "experiment_summary": str((self.output_dir / "experiment_summary.csv").resolve()),
                "plots": [
                    str(path.resolve())
                    for path in sorted(self.output_dir.glob("*.png"))
                ],
            },
        }

    def _execute(self) -> None:
        try:
            self.status = "running"
            self._persist()
            run_benchmarks(
                output_dir=self.output_dir,
                num_seeds=int(self.request.get("benchmark_num_seeds", 4)),
                strategies=self.request.get("strategies"),
            )
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
            self.status = "completed"
            self.completed_at = time.time()
            self.updated_at = self.completed_at
            self._persist()
        except Exception as exc:  # pragma: no cover - defensive runtime safeguard
            self.status = "failed"
            self.error = f"{type(exc).__name__}: {exc}"
            self.updated_at = time.time()
            self._persist()

    def _persist(self) -> None:
        self.metadata_path.write_text(
            json.dumps(self.get_record(), indent=2),
            encoding="utf-8",
        )


class ExperimentService:
    """Manage experiment batches and summaries."""

    def __init__(self, paths: LocalProductPaths) -> None:
        self.paths = paths
        self.controllers: dict[str, ExperimentController] = {}

    def create_experiment(self, request: dict[str, Any]) -> dict[str, Any]:
        experiment_id = f"experiment-{uuid4().hex[:10]}"
        controller = ExperimentController(experiment_id, request, self.paths)
        self.controllers[experiment_id] = controller
        controller.start()
        return controller.get_record()

    def list_experiments(self) -> list[dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for path in self.paths.experiments_dir.glob("*/metadata.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            records[record["experiment_id"]] = record
        for experiment_id, controller in self.controllers.items():
            records[experiment_id] = controller.get_record()
        return sorted(records.values(), key=lambda item: item["created_at"], reverse=True)

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        if experiment_id in self.controllers:
            return self.controllers[experiment_id].get_record()
        path = self.paths.experiments_dir / experiment_id / "metadata.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def load_experiment_summary(self, experiment_id: str) -> list[dict[str, Any]]:
        summary_path = self.paths.experiments_dir / experiment_id / "experiment_summary.csv"
        if not summary_path.exists():
            return []
        return pd.read_csv(summary_path).to_dict(orient="records")


class ProductBackend:
    """Aggregate backend services for the local product layer."""

    def __init__(self, storage_root: str | Path = "app/storage") -> None:
        self.paths = LocalProductPaths.create(storage_root)
        self.scenarios = ScenarioService(self.paths)
        self.missions = MissionService(self.paths, self.scenarios)
        self.experiments = ExperimentService(self.paths)
        self.reports = ReportGenerator(self.paths)

    def generate_report(self, run_id: str) -> dict[str, Any]:
        run_record = self.missions.get_run(run_id)
        events = self.missions.get_events(run_id)
        report_path = self.reports.generate_run_report(run_record, events)
        return {"run_id": run_id, "report_path": str(report_path.resolve())}

"""Experiment services and controllers."""

from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from app.backend.core.job_manager import BackgroundJobManager
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.shared import read_csv_records, to_jsonable
from app.backend.storage import LocalProductPaths
from benchmark import run_benchmarks, run_grouped_experiments


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
        except Exception as exc:  # pragma: no cover
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
        summary_path = self.output_dir / "experiment_summary.csv"
        summary = read_csv_records(summary_path, limit=20) if summary_path.exists() else []
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
        self.job_manager.submit(job_id, "experiment_batch", "experiment", experiment_id, controller.run)
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
        return self.get_experiment(experiment_id).get("summary_json", [])

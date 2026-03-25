"""Local background job manager for runs and experiments."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import threading
import time
from typing import Any, Callable

from app.backend.db.sqlite import MetadataStore


class BackgroundJobManager:
    """Manage local background jobs with SQLite-backed lifecycle tracking."""

    def __init__(self, store: MetadataStore, max_workers: int = 4) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: dict[str, Future[Any]] = {}
        self.cancel_events: dict[str, threading.Event] = {}

    def submit(
        self,
        job_id: str,
        job_type: str,
        owner_type: str,
        owner_id: str,
        target: Callable[[str, threading.Event], Any],
    ) -> None:
        now = time.time()
        self.cancel_events[job_id] = threading.Event()
        self.store.upsert(
            "jobs",
            job_id,
            {
                "job_type": job_type,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "status": "queued",
                "progress": 0.0,
                "created_at": now,
                "updated_at": now,
                "completed_at": None,
                "error": None,
                "summary_json": {},
            },
        )

        def runner() -> Any:
            self.update(job_id, status="running", progress=0.05)
            try:
                result = target(job_id, self.cancel_events[job_id])
                if self.cancel_events[job_id].is_set():
                    self.update(job_id, status="cancelled", progress=1.0)
                else:
                    self.update(job_id, status="completed", progress=1.0, summary=result or {})
                return result
            except Exception as exc:  # pragma: no cover - defensive background failure path
                self.update(job_id, status="failed", error=f"{type(exc).__name__}: {exc}", progress=1.0)
                raise

        self.futures[job_id] = self.executor.submit(runner)

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        error: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        current = self.store.get("jobs", job_id)
        if current is None:
            return
        now = time.time()
        self.store.upsert(
            "jobs",
            job_id,
            {
                "job_type": current["job_type"],
                "owner_type": current["owner_type"],
                "owner_id": current["owner_id"],
                "status": status or current["status"],
                "progress": progress if progress is not None else current["progress"],
                "created_at": current["created_at"],
                "updated_at": now,
                "completed_at": now if status in {"completed", "failed", "cancelled"} else current["completed_at"],
                "error": error if error is not None else current.get("error"),
                "summary_json": summary if summary is not None else current.get("summary_json", {}),
            },
        )

    def cancel(self, job_id: str) -> dict[str, Any]:
        if job_id in self.cancel_events:
            self.cancel_events[job_id].set()
            future = self.futures.get(job_id)
            if future is not None:
                future.cancel()
            self.update(job_id, status="cancelled", progress=1.0)
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        job = self.store.get("jobs", job_id)
        if job is None:
            raise FileNotFoundError(f"Unknown job: {job_id}")
        return job

    def list(self) -> list[dict[str, Any]]:
        jobs = self.store.list("jobs")
        return sorted(jobs, key=lambda item: item["created_at"], reverse=True)

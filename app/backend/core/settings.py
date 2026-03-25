"""Settings helpers for the Phase 6 product backend."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class BackendSettings:
    """Local runtime settings for the product backend."""

    storage_root: str = "app/storage"
    db_path: str = "app/storage/swarm_product.db"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_api_base_url: str = "http://127.0.0.1:8000"
    comparison_num_seeds: int = 2
    job_max_workers: int = 4

    @classmethod
    def from_env(cls) -> "BackendSettings":
        storage_root = os.getenv("SWARM_STORAGE_ROOT", "app/storage")
        default_db_path = str(Path(storage_root) / "swarm_product.db")
        return cls(
            storage_root=storage_root,
            db_path=os.getenv("SWARM_DB_PATH", default_db_path),
            backend_host=os.getenv("SWARM_BACKEND_HOST", "127.0.0.1"),
            backend_port=int(os.getenv("SWARM_BACKEND_PORT", "8000")),
            frontend_api_base_url=os.getenv("SWARM_FRONTEND_API_BASE_URL", "http://127.0.0.1:8000"),
            comparison_num_seeds=int(os.getenv("SWARM_COMPARISON_NUM_SEEDS", "2")),
            job_max_workers=int(os.getenv("SWARM_JOB_MAX_WORKERS", "4")),
        )

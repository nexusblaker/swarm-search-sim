"""Local storage helpers for Phase 5 product artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def slugify(value: str) -> str:
    """Return a filesystem-safe identifier."""

    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return normalized or "item"


@dataclass(slots=True)
class LocalProductPaths:
    """Filesystem layout for saved product artifacts."""

    root: Path
    scenarios_dir: Path
    templates_dir: Path
    plans_dir: Path
    comparisons_dir: Path
    runs_dir: Path
    experiments_dir: Path
    reviews_dir: Path
    reports_dir: Path
    database_path: Path

    @classmethod
    def create(cls, root: str | Path = "app/storage") -> "LocalProductPaths":
        base = Path(root)
        paths = cls(
            root=base,
            scenarios_dir=base / "scenarios",
            templates_dir=base / "templates",
            plans_dir=base / "plans",
            comparisons_dir=base / "comparisons",
            runs_dir=base / "runs",
            experiments_dir=base / "experiments",
            reviews_dir=base / "reviews",
            reports_dir=base / "reports",
            database_path=base / "swarm_product.db",
        )
        paths.ensure()
        return paths

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.comparisons_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

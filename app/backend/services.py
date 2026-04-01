"""Phase 7 product backend composition layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.backend.core.job_manager import BackgroundJobManager
from app.backend.core.settings import BackendSettings
from app.backend.db.sqlite import MetadataStore
from app.backend.domain.comparisons import ComparisonEvaluator, PlanComparisonService
from app.backend.domain.experiments import ExperimentService
from app.backend.domain.geospatial import GeospatialService
from app.backend.domain.plans import MissionPlanService
from app.backend.domain.recommendations import RecommendationService
from app.backend.domain.reports import ReportService
from app.backend.domain.reviews import AfterActionReviewService
from app.backend.domain.runs import MissionService
from app.backend.domain.scenarios import ScenarioService, TemplateService
from app.backend.reporting import ReportGenerator
from app.backend.storage import LocalProductPaths


class ProductBackend:
    """Aggregate backend services for the FastAPI mission product."""

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
        self.reporting = ReportGenerator(self.paths)
        self.reports = ReportService(self.store, self.reporting)
        self.geospatial = GeospatialService()
        self.comparison_evaluator = ComparisonEvaluator(self.scenarios, self.settings)
        self.comparison = self.comparison_evaluator
        self.recommendations = RecommendationService(
            self.comparison_evaluator,
            resolve_plan_json=lambda plan_id: self.plans.get_plan(plan_id)["plan_json"],
        )
        self.plans = MissionPlanService(
            self.paths,
            self.store,
            self.scenarios,
            self.templates,
            recommend=self.recommendations.recommend,
            reports=self.reports,
        )
        self.comparisons = PlanComparisonService(
            self.store,
            self.plans,
            self.comparison_evaluator,
            reports=self.reports,
        )
        self.missions = MissionService(
            self.paths,
            self.store,
            self.scenarios,
            self.templates,
            self.plans,
            self.comparisons,
            self.job_manager,
        )
        self.experiments = ExperimentService(
            self.paths,
            self.store,
            self.job_manager,
        )
        self.reviews = AfterActionReviewService(
            self.store,
            self.missions,
            self.plans,
            self.comparisons,
            self.reports,
        )

    def get_health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "database_path": str(Path(self.settings.db_path).resolve()),
            "storage_root": str(Path(self.settings.storage_root).resolve()),
        }

    def get_dashboard_summary(self) -> dict[str, Any]:
        scenarios = self.scenarios.list_scenarios()
        plans = self.plans.list_plans()
        comparisons = self.comparisons.list_comparisons()
        runs = self.missions.list_runs()
        reviews = self.reviews.list_reviews()
        reports = self.reports.list_reports()
        jobs = self.list_jobs()

        activity: list[dict[str, Any]] = []
        for run in runs[:4]:
            activity.append(
                {
                    "id": run["id"],
                    "kind": "run",
                    "title": f"Run {run['id']}",
                    "subtitle": f"{run.get('summary_json', {}).get('strategy', 'strategy')} · {run.get('plan_id') or run.get('scenario_id')}",
                    "timestamp": run["updated_at"],
                    "status": run.get("status"),
                    "owner_id": run.get("plan_id") or run.get("scenario_id"),
                }
            )
        for report in reports[:3]:
            activity.append(
                {
                    "id": report["id"],
                    "kind": "report",
                    "title": f"{report['report_type'].replace('_', ' ').title()} report",
                    "subtitle": f"{report.get('owner_type', 'run')}:{report.get('owner_id') or report.get('run_id')}",
                    "timestamp": report["created_at"],
                    "status": "completed",
                    "owner_id": report.get("owner_id") or report.get("run_id"),
                }
            )
        for review in reviews[:2]:
            activity.append(
                {
                    "id": review["id"],
                    "kind": "review",
                    "title": review["name"],
                    "subtitle": f"After-action review for run {review['run_id']}",
                    "timestamp": review["updated_at"],
                    "status": "completed",
                    "owner_id": review["run_id"],
                }
            )
        recent_activity = sorted(activity, key=lambda item: item["timestamp"], reverse=True)[:8]

        suggested_actions: list[dict[str, str]] = []
        if not plans:
            suggested_actions.append(
                {
                    "label": "Create mission plan",
                    "description": "Start with a doctrine template and capture assumptions in a reusable plan.",
                    "route": "/plans",
                }
            )
        if plans and not comparisons:
            suggested_actions.append(
                {
                    "label": "Compare candidate plans",
                    "description": "Evaluate strategies, drone counts, and reserve policies before launch.",
                    "route": "/comparisons",
                }
            )
        if plans and not runs:
            suggested_actions.append(
                {
                    "label": "Launch a monitored run",
                    "description": "Run the selected plan and observe mission progress in Mission Control.",
                    "route": "/mission-control",
                }
            )
        if runs and not reviews:
            suggested_actions.append(
                {
                    "label": "Generate after-action review",
                    "description": "Turn a completed mission into a replay-backed operational review.",
                    "route": "/reviews",
                }
            )
        if not suggested_actions:
            suggested_actions.append(
                {
                    "label": "Review latest reports",
                    "description": "Open generated artifacts and continue iterating on the mission workflow.",
                    "route": "/reports",
                }
            )

        return {
            "counts": {
                "scenarios": len(scenarios),
                "plans": len(plans),
                "comparisons": len(comparisons),
                "runs": len(runs),
                "reviews": len(reviews),
                "reports": len(reports),
            },
            "active_runs": sum(1 for run in runs if run["status"] in {"queued", "running", "paused"}),
            "completed_runs": sum(1 for run in runs if run["status"] == "completed"),
            "queued_jobs": sum(1 for job in jobs if job["status"] == "queued"),
            "backend_status": "ok",
            "recent_runs": runs[:5],
            "recent_reports": reports[:5],
            "recent_activity": recent_activity,
            "suggested_actions": suggested_actions,
        }

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.job_manager.list()

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self.job_manager.get(job_id)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        return self.job_manager.cancel(job_id)

    def get_artifact_path(self, owner_type: str, owner_id: str, artifact_type: str) -> str:
        artifacts = self.store.list_artifacts(owner_type, owner_id)
        for artifact in artifacts:
            if artifact["artifact_type"] == artifact_type:
                return artifact["path"]
        raise FileNotFoundError(
            f"Unknown artifact {artifact_type!r} for owner {owner_type}:{owner_id}"
        )

    def generate_report(self, run_id: str) -> dict[str, Any]:
        run_record = self.missions.get_run(run_id)
        run_record = dict(run_record)
        run_record["recommendation"] = self.recommendations.recommend(
            {"scenario": run_record["config_json"], "num_seeds": 1}
        )
        events = self.missions.get_events(run_id)
        return self.reports.generate_run_report(run_record, events)

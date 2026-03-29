"""Mission report generation utilities."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.backend.storage import LocalProductPaths


class ReportGenerator:
    """Generate HTML mission summary reports."""

    def __init__(self, paths: LocalProductPaths) -> None:
        self.paths = paths
        templates_dir = Path(__file__).resolve().parent / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        )

    def generate_run_report(
        self,
        run_record: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> Path:
        """Write a self-contained HTML report for a mission run."""

        template = self.environment.get_template("mission_report.html.j2")
        event_counts = Counter(event["event_type"] for event in events)
        run_id = run_record.get("run_id") or run_record.get("id")
        output_path = self.paths.reports_dir / f"{run_id}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = template.render(
            run=run_record,
            events=events[:100],
            event_counts=dict(event_counts),
            metrics=run_record.get("metrics", run_record.get("summary_json", {}).get("metrics", {})),
            artifacts=run_record.get("artifact_paths", {}),
            recommendation=run_record.get("recommendation"),
        )
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def generate_plan_report(self, plan_record: dict[str, Any]) -> Path:
        """Write a self-contained HTML report for a mission plan."""

        template = self.environment.get_template("mission_plan_report.html.j2")
        output_path = self.paths.reports_dir / f"{plan_record['id']}.html"
        html = template.render(plan=plan_record)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def generate_comparison_report(self, comparison_record: dict[str, Any]) -> Path:
        """Write a self-contained HTML report for a saved comparison."""

        template = self.environment.get_template("comparison_report.html.j2")
        output_path = self.paths.reports_dir / f"{comparison_record['id']}.html"
        html = template.render(comparison=comparison_record)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def generate_review_report(self, review_record: dict[str, Any]) -> Path:
        """Write a self-contained HTML report for an after-action review."""

        template = self.environment.get_template("after_action_review_report.html.j2")
        output_path = self.paths.reports_dir / f"{review_record['id']}.html"
        html = template.render(review=review_record)
        output_path.write_text(html, encoding="utf-8")
        return output_path

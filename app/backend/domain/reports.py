"""Report services for runs, plans, comparisons, and reviews."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.backend.db.sqlite import MetadataStore
from app.backend.domain.lifecycle import summarize_battery_lifecycle, summarize_search_pattern, summarize_sensing_lifecycle
from app.backend.reporting import ReportGenerator


class ReportService:
    """Generate, index, and retrieve HTML reports."""

    def __init__(self, store: MetadataStore, generator: ReportGenerator) -> None:
        self.store = store
        self.generator = generator

    def list_reports(self) -> list[dict[str, Any]]:
        rows = self.store.list("reports")
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def get_report(self, report_id: str) -> dict[str, Any]:
        record = self.store.get("reports", report_id)
        if record is None:
            raise FileNotFoundError(f"Unknown report: {report_id}")
        return record

    def generate_run_report(self, run_record: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
        path = self.generator.generate_run_report(run_record, events)
        battery_lifecycle = summarize_battery_lifecycle(run_record, events)
        sensing_lifecycle = summarize_sensing_lifecycle(run_record, events)
        search_pattern = summarize_search_pattern(run_record, events)
        return self._register_report(
            owner_type="run",
            owner_id=run_record["id"],
            report_type="mission_summary",
            file_path=str(path.resolve()),
            summary_json={
                "run_id": run_record["id"],
                "strategy": run_record["summary_json"].get("strategy"),
                "search_pattern": search_pattern,
                "status": run_record["status"],
                "run_phase": battery_lifecycle.get("run_phase"),
                "battery_lifecycle": battery_lifecycle,
                "sensing_lifecycle": sensing_lifecycle,
            },
            run_id=run_record["id"],
        )

    def generate_plan_report(self, plan_record: dict[str, Any]) -> dict[str, Any]:
        path = self.generator.generate_plan_report(plan_record)
        return self._register_report(
            owner_type="plan",
            owner_id=plan_record["id"],
            report_type="mission_plan",
            file_path=str(path.resolve()),
            summary_json={
                "plan_id": plan_record["id"],
                "name": plan_record["name"],
                "approval_state": plan_record["approval_state"],
                "search_pattern": plan_record.get("summary_json", {}).get("search_pattern"),
                "search_pattern_label": plan_record.get("summary_json", {}).get("search_pattern_label"),
            },
            run_id=plan_record["id"],
        )

    def generate_comparison_report(self, comparison_record: dict[str, Any]) -> dict[str, Any]:
        path = self.generator.generate_comparison_report(comparison_record)
        return self._register_report(
            owner_type="comparison",
            owner_id=comparison_record["id"],
            report_type="plan_comparison",
            file_path=str(path.resolve()),
            summary_json={
                "comparison_id": comparison_record["id"],
                "name": comparison_record["name"],
                "plan_id": comparison_record.get("plan_id"),
            },
            run_id=comparison_record.get("plan_id") or comparison_record["id"],
        )

    def generate_review_report(self, review_record: dict[str, Any]) -> dict[str, Any]:
        path = self.generator.generate_review_report(review_record)
        battery_lifecycle = review_record.get("summary_json", {}).get("battery_lifecycle", {})
        sensing_lifecycle = review_record.get("summary_json", {}).get("sensing_lifecycle", {})
        search_pattern = review_record.get("summary_json", {}).get("search_pattern", {})
        return self._register_report(
            owner_type="review",
            owner_id=review_record["id"],
            report_type="after_action_review",
            file_path=str(path.resolve()),
            summary_json={
                "review_id": review_record["id"],
                "run_id": review_record["run_id"],
                "plan_id": review_record.get("plan_id"),
                "run_phase": battery_lifecycle.get("run_phase"),
                "battery_lifecycle": battery_lifecycle,
                "sensing_lifecycle": sensing_lifecycle,
                "search_pattern": search_pattern,
            },
            run_id=review_record["run_id"],
        )

    def _register_report(
        self,
        *,
        owner_type: str,
        owner_id: str,
        report_type: str,
        file_path: str,
        summary_json: dict[str, Any],
        run_id: str,
    ) -> dict[str, Any]:
        report_id = f"report-{uuid4().hex[:10]}"
        now = time.time()
        self.store.upsert(
            "reports",
            report_id,
            {
                "run_id": run_id,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "report_type": report_type,
                "created_at": now,
                "summary_json": summary_json,
                "file_path": file_path,
            },
        )
        self.store.insert_artifact(
            "report",
            report_id,
            "html_report",
            file_path,
            {"owner_type": owner_type, "owner_id": owner_id},
            now,
        )
        return self.get_report(report_id)

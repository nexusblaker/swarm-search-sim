"""Benchmark runner for comparing coordination strategies across seeds."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from src.simulation.engine import SimulationEngine
from src.utils.config_loader import load_scenario_config


def run_benchmarks(
    output_dir: str | Path | None = None,
    num_seeds: int | None = None,
    strategies: list[str] | None = None,
) -> pd.DataFrame:
    """Run the configured strategies over multiple seeds and save outputs."""

    config = load_scenario_config()
    benchmark_output_dir = Path(output_dir or config.benchmark_output_dir)
    benchmark_output_dir.mkdir(parents=True, exist_ok=True)

    benchmark_strategies = strategies or config.benchmark_strategies
    benchmark_seeds = num_seeds or config.benchmark_num_seeds

    records: list[dict[str, object]] = []
    for strategy in benchmark_strategies:
        for seed in range(benchmark_seeds):
            run_config = replace(config, strategy=strategy, seed=seed)
            engine = SimulationEngine(run_config)
            metrics = engine.run()
            record = asdict(metrics)
            record["strategy"] = strategy
            record["seed"] = seed
            record["steps_completed"] = engine.current_step
            records.append(record)

    results = pd.DataFrame.from_records(records)
    csv_path = benchmark_output_dir / "benchmark_results.csv"
    results.to_csv(csv_path, index=False)

    summary = results.copy()
    summary["effective_time_to_detection"] = summary["time_to_detection"].fillna(config.max_steps + 1)
    grouped = (
        summary.groupby("strategy", as_index=False)
        .agg(
            average_time_to_detection=("effective_time_to_detection", "mean"),
            success_rate=("mission_success", "mean"),
            average_area_covered=("area_covered_pct", "mean"),
            average_overlap_ratio=("overlap_ratio", "mean"),
            average_battery_used=("battery_used", "mean"),
        )
        .sort_values("strategy")
    )
    grouped.to_csv(benchmark_output_dir / "benchmark_summary.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].bar(grouped["strategy"], grouped["average_time_to_detection"], color="#4cc9f0")
    axes[0].set_title("Average Time To Detection")
    axes[0].set_ylabel("Steps")
    axes[0].tick_params(axis="x", rotation=20)

    axes[1].bar(grouped["strategy"], grouped["success_rate"], color="#80ed99")
    axes[1].set_title("Success Rate")
    axes[1].set_ylabel("Mission success")
    axes[1].set_ylim(0.0, 1.0)
    axes[1].tick_params(axis="x", rotation=20)
    fig.tight_layout()
    chart_path = benchmark_output_dir / "benchmark_comparison.png"
    fig.savefig(chart_path, dpi=160)
    plt.close(fig)

    return results


def main() -> None:
    """Run the benchmark suite and print output locations."""

    config = load_scenario_config()
    results = run_benchmarks()
    output_dir = Path(config.benchmark_output_dir).resolve()
    print("Swarm Coordination Simulator benchmark complete")
    print(f"Rows written: {len(results)}")
    print(f"Results CSV: {(output_dir / 'benchmark_results.csv')}")
    print(f"Summary CSV: {(output_dir / 'benchmark_summary.csv')}")
    print(f"Comparison plot: {(output_dir / 'benchmark_comparison.png')}")


if __name__ == "__main__":
    main()

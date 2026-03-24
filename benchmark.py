"""Benchmark and experiment runner for the swarm coordination simulator."""

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
    """Run the Phase 2 style strategy benchmark over multiple seeds."""

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
            record["scenario_family"] = run_config.scenario_family
            record["target_behavior"] = run_config.target_behavior
            record["coordination_mode"] = run_config.coordination_mode
            record["drone_count"] = run_config.num_drones
            records.append(record)

    results = pd.DataFrame.from_records(records)
    results.to_csv(benchmark_output_dir / "benchmark_results.csv", index=False)

    grouped = _summarize_standard_benchmark(results, config.max_steps)
    grouped.to_csv(benchmark_output_dir / "benchmark_summary.csv", index=False)
    _plot_standard_benchmark(grouped, benchmark_output_dir / "benchmark_comparison.png")
    return results


def run_grouped_experiments(
    output_dir: str | Path | None = None,
    num_seeds: int | None = None,
    strategies: list[str] | None = None,
    scenario_families: list[str] | None = None,
    target_behaviors: list[str] | None = None,
    coordination_modes: list[str] | None = None,
    drone_counts: list[int] | None = None,
) -> pd.DataFrame:
    """Run grouped robustness experiments across scenario and policy dimensions."""

    config = load_scenario_config()
    experiment_output_dir = Path(output_dir or config.benchmark_output_dir)
    experiment_output_dir.mkdir(parents=True, exist_ok=True)

    experiment_seeds = num_seeds or config.experiment_num_seeds
    experiment_strategies = strategies or config.benchmark_strategies
    experiment_families = scenario_families or config.benchmark_scenario_families
    experiment_behaviors = target_behaviors or config.benchmark_target_behaviors
    experiment_modes = coordination_modes or config.benchmark_coordination_modes
    experiment_drone_counts = drone_counts or config.benchmark_drone_counts

    records: list[dict[str, object]] = []
    for family in experiment_families:
        family_config = config.with_scenario_family(family)
        for behavior in experiment_behaviors:
            for coordination_mode in experiment_modes:
                for drone_count in experiment_drone_counts:
                    for strategy in experiment_strategies:
                        for seed in range(experiment_seeds):
                            run_config = replace(
                                family_config,
                                strategy=strategy,
                                seed=seed,
                                target_behavior=behavior,
                                coordination_mode=coordination_mode,
                                num_drones=drone_count,
                            )
                            engine = SimulationEngine(run_config)
                            metrics = engine.run()
                            record = asdict(metrics)
                            record["strategy"] = strategy
                            record["seed"] = seed
                            record["scenario_family"] = family
                            record["target_behavior"] = behavior
                            record["coordination_mode"] = coordination_mode
                            record["drone_count"] = drone_count
                            record["steps_completed"] = engine.current_step
                            records.append(record)

    results = pd.DataFrame.from_records(records)
    results.to_csv(experiment_output_dir / "experiment_results.csv", index=False)
    summary = _summarize_grouped_experiments(results)
    summary.to_csv(experiment_output_dir / "experiment_summary.csv", index=False)

    _plot_success_by_family(results, experiment_output_dir / "plot_success_by_strategy_family.png")
    _plot_time_by_comms(results, experiment_output_dir / "plot_time_by_strategy_comms.png")
    _plot_overlap_by_strategy(results, experiment_output_dir / "plot_overlap_by_strategy.png")
    return results


def _summarize_standard_benchmark(results: pd.DataFrame, max_steps: int) -> pd.DataFrame:
    summary = results.copy()
    summary["effective_time_to_detection"] = summary["time_to_detection"].fillna(max_steps + 1)
    return (
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


def _summarize_grouped_experiments(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.copy()
    grouped["effective_time_to_detection"] = grouped["time_to_detection"].fillna(grouped["steps_completed"])
    return (
        grouped.groupby(
            ["strategy", "scenario_family", "coordination_mode", "target_behavior", "drone_count"],
            as_index=False,
        )
        .agg(
            success_rate=("mission_success", "mean"),
            success_std=("mission_success", "std"),
            mean_time_to_detection=("effective_time_to_detection", "mean"),
            std_time_to_detection=("effective_time_to_detection", "std"),
            mean_overlap_ratio=("overlap_ratio", "mean"),
            std_overlap_ratio=("overlap_ratio", "std"),
            mean_path_efficiency=("path_efficiency", "mean"),
        )
    )


def _plot_standard_benchmark(grouped: pd.DataFrame, output_path: Path) -> None:
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
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_success_by_family(results: pd.DataFrame, output_path: Path) -> None:
    grouped = (
        results.groupby(["strategy", "scenario_family"], as_index=False)
        .agg(success_rate=("mission_success", "mean"), success_std=("mission_success", "std"))
    )
    pivot = grouped.pivot(index="strategy", columns="scenario_family", values="success_rate").fillna(0.0)
    errors = grouped.pivot(index="strategy", columns="scenario_family", values="success_std").fillna(0.0)
    fig, ax = plt.subplots(figsize=(11, 6))
    pivot.plot(kind="bar", yerr=errors, ax=ax, capsize=4)
    ax.set_ylabel("Success rate")
    ax.set_title("Success Rate by Strategy and Scenario Family")
    ax.set_ylim(0.0, 1.0)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_time_by_comms(results: pd.DataFrame, output_path: Path) -> None:
    time_results = results.copy()
    time_results["effective_time_to_detection"] = time_results["time_to_detection"].fillna(time_results["steps_completed"])
    grouped = (
        time_results.groupby(["strategy", "coordination_mode"], as_index=False)
        .agg(mean_time=("effective_time_to_detection", "mean"), std_time=("effective_time_to_detection", "std"))
    )
    pivot = grouped.pivot(index="strategy", columns="coordination_mode", values="mean_time").fillna(0.0)
    errors = grouped.pivot(index="strategy", columns="coordination_mode", values="std_time").fillna(0.0)
    fig, ax = plt.subplots(figsize=(10, 6))
    pivot.plot(kind="bar", yerr=errors, ax=ax, capsize=4)
    ax.set_ylabel("Steps")
    ax.set_title("Time To Detection by Strategy and Coordination Mode")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _plot_overlap_by_strategy(results: pd.DataFrame, output_path: Path) -> None:
    grouped = results.groupby("strategy", as_index=False).agg(
        mean_overlap=("overlap_ratio", "mean"),
        std_overlap=("overlap_ratio", "std"),
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(grouped["strategy"], grouped["mean_overlap"], yerr=grouped["std_overlap"], capsize=4, color="#ffbe0b")
    ax.set_ylabel("Overlap ratio")
    ax.set_title("Overlap Ratio by Strategy")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    config = load_scenario_config()
    standard_results = run_benchmarks()
    grouped_results = run_grouped_experiments()
    output_dir = Path(config.benchmark_output_dir).resolve()
    print("Swarm Coordination Simulator benchmark complete")
    print(f"Standard rows written: {len(standard_results)}")
    print(f"Grouped experiment rows written: {len(grouped_results)}")
    print(f"Results directory: {output_dir}")
    print(f"Raw benchmark CSV: {(output_dir / 'benchmark_results.csv')}")
    print(f"Grouped experiment CSV: {(output_dir / 'experiment_results.csv')}")
    print(f"Standard summary CSV: {(output_dir / 'benchmark_summary.csv')}")
    print(f"Grouped summary CSV: {(output_dir / 'experiment_summary.csv')}")
    print(f"Plots: {(output_dir / 'benchmark_comparison.png')}, {(output_dir / 'plot_success_by_strategy_family.png')}, {(output_dir / 'plot_time_by_strategy_comms.png')}, {(output_dir / 'plot_overlap_by_strategy.png')}")


if __name__ == "__main__":
    main()

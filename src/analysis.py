"""Latency stats, cost tables and per-prompt-version summaries."""
import pandas as pd

from . import config


def latency_stats(df: pd.DataFrame) -> pd.Series:
    """mean / median / min / max / std (sample std, ddof=1) of latency in seconds."""
    s = df["latency_seconds"]
    return pd.Series({
        "mean": s.mean(), "median": s.median(),
        "min": s.min(), "max": s.max(), "std": s.std(ddof=1),
    })


def summarize_by_version(df: pd.DataFrame) -> pd.DataFrame:
    """One row per prompt version with the five metrics the assignment asks for."""
    ok = df[df["status"] == "success"]
    return ok.groupby("prompt_version").agg(
        avg_latency_seconds=("latency_seconds", "mean"),
        avg_input_tokens=("input_tokens", "mean"),
        avg_output_tokens=("output_tokens", "mean"),
        avg_cost_per_request=("total_cost", "mean"),
        valid_json=("valid_json", "mean"),
    ).reset_index()


def projected_monthly(df: pd.DataFrame) -> float:
    return df["total_cost"].mean() * config.MONTHLY_REQUESTS

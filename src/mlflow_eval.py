"""Step 2 (Task 3): register prompts v1-v3 in MLflow, log one run per version, optionally promote.

Run:  python -m src.mlflow_eval              # register + log runs + print recommendation
      python -m src.mlflow_eval --promote 3  # also set the `production` alias to version 3

Needs outputs/latency_tokens_cost.csv from `python -m src.collect`.
NOTE: Prompt Registry needs MLflow 3.x and a database-backed store (sqlite default here).
"""
import argparse

import mlflow
import pandas as pd

try:  # MLflow 3.x
    from mlflow.genai import load_prompt, register_prompt, set_prompt_alias
except ImportError:  # some 2.x versions
    from mlflow import load_prompt, register_prompt, set_prompt_alias

from . import config
from .analysis import summarize_by_version
from .prompts import PROMPTS


def ensure_prompts_registered() -> None:
    """Register v1..v3 in order; skip any already registered with the same template."""
    for version, p in PROMPTS.items():
        try:
            existing = load_prompt(f"prompts:/{config.PROMPT_NAME}/{version}")
            if existing.template == p["template"]:
                print(f"Prompt v{version} already registered - skipping")
                continue
        except Exception:
            pass
        registered = register_prompt(name=config.PROMPT_NAME, template=p["template"],
                                     commit_message=p["commit_message"])
        print(f"Registered prompt v{registered.version}: {p['commit_message']}")


def log_runs(df: pd.DataFrame) -> pd.DataFrame:
    mlflow.set_tracking_uri(config.TRACKING_URI)
    mlflow.set_experiment(config.EXPERIMENT_NAME)
    exp = mlflow.get_experiment_by_name(config.EXPERIMENT_NAME)
    for old in mlflow.search_runs(experiment_ids=[exp.experiment_id], output_format="list"):
        mlflow.delete_run(old.info.run_id)  # keep the experiment at exactly one run per version
    summary = summarize_by_version(df)
    for _, row in summary.iterrows():
        v = int(row["prompt_version"])
        with mlflow.start_run(run_name=f"prompt_v{v}_{PROMPTS[v]['label'].lower().replace(' ', '_')}"):
            load_prompt(f"prompts:/{config.PROMPT_NAME}/{v}")  # loading inside a run links it to the experiment
            mlflow.set_tags({"prompt_uri": f"prompts:/{config.PROMPT_NAME}/{v}"})
            mlflow.log_params({
                "prompt_name": config.PROMPT_NAME, "prompt_version": v,
                "model_name": config.MODEL_NAME, "temperature": config.TEMPERATURE,
                "price_input_per_m": config.PRICE_INPUT_PER_M,
                "price_output_per_m": config.PRICE_OUTPUT_PER_M,
                "pricing_date": config.PRICING_DATE, "currency": config.PRICING_CURRENCY,
            })
            mlflow.log_metrics({k: float(row[k]) for k in [
                "avg_latency_seconds", "avg_input_tokens", "avg_output_tokens",
                "avg_cost_per_request", "valid_json"]})
            mlflow.log_table(df[df["prompt_version"] == v], artifact_file="per_question_results.json")
    return summary


def ensure_experiment_link() -> None:
    """Newer MLflow UIs list prompts per experiment, using the prompt tag `_mlflow_experiment_ids`
    (comma-separated, e.g. ',1,'). Loading a prompt inside a run normally sets it; this makes sure."""
    import mlflow.genai as genai

    key = "_mlflow_experiment_ids"
    try:
        exp_id = mlflow.get_experiment_by_name(config.EXPERIMENT_NAME).experiment_id
        tags = genai.get_prompt_tags(config.PROMPT_NAME) or {}
        current = tags.get(key, "")
        if f",{exp_id}," in current:
            print(f"Prompt already linked to experiment {exp_id}")
            return
        genai.set_prompt_tag(config.PROMPT_NAME, key, (current or ",") + f"{exp_id},")
        print(f"Linked prompt {config.PROMPT_NAME} to experiment {exp_id}")
    except Exception as exc:  # never fail the whole run because of a UI-only link
        print(f"WARNING: could not link prompt to experiment ({type(exc).__name__}: {exc})")


def pick_best(summary: pd.DataFrame) -> int:
    """Highest valid_json first; ties broken by lowest cost, then lowest latency."""
    s = summary.sort_values(["valid_json", "avg_cost_per_request", "avg_latency_seconds"],
                            ascending=[False, True, True])
    return int(s.iloc[0]["prompt_version"])


def run(promote: int | None = None) -> pd.DataFrame:
    mlflow.set_tracking_uri(config.TRACKING_URI)
    df = pd.read_csv(config.LATENCY_CSV)
    ensure_prompts_registered()
    summary = log_runs(df)
    ensure_experiment_link()
    best = pick_best(summary)
    summary["recommended"] = summary["prompt_version"].apply(lambda v: "Yes" if v == best else "No")
    summary.to_csv(config.EVAL_CSV, index=False)
    print(summary.to_string(index=False))
    print(f"\nSuggested best version by the metrics: v{best} (your judgement on quality still applies)")
    if promote is not None:
        set_prompt_alias(config.PROMPT_NAME, alias=config.PRODUCTION_ALIAS, version=promote)
        print(f"Alias '{config.PRODUCTION_ALIAS}' -> v{promote}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--promote", type=int, default=None, help="prompt version to alias as production")
    run(ap.parse_args().promote)

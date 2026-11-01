"""Step 1 (Tasks 1 and 2): call the LLM for 5 questions x 3 prompt versions and save CSVs.

Run:  python -m src.collect
"""
import json
import time

import pandas as pd

from . import config
from .analysis import summarize_by_version
from .llm_client import call_llm, warm_up
from .metrics import compute_cost, is_valid_json_response
from .prompts import PROMPTS, render


def run() -> pd.DataFrame:
    config.OUTPUTS_DIR.mkdir(exist_ok=True)
    if not config.API_KEY or config.API_KEY.startswith("paste-"):
        raise SystemExit("LLM_API_KEY is not set. Put your key in .env (never commit it).")
    if "PLACEHOLDER" in config.PRICING_SOURCE or config.PRICE_INPUT_PER_M == 0:
        print("WARNING: pricing is still a placeholder. Edit PRICE_* / PRICING_* in .env before the final run.")

    questions = json.loads(config.QUESTIONS_PATH.read_text(encoding="utf-8"))
    print(f"Model: {config.MODEL_NAME} @ {config.BASE_URL} | warming up...")
    warm_up()

    rows, raw = [], []
    for version, p in PROMPTS.items():
        for q in questions:
            rec = call_llm(render(p["template"], q["question"]), q["id"], version)
            cost = compute_cost(rec["input_tokens"], rec["output_tokens"],
                                config.PRICE_INPUT_PER_M, config.PRICE_OUTPUT_PER_M)
            row = {
                "question_id": rec["question_id"],
                "prompt_version": version,
                "model_name": rec["model_name"],
                "start_time": rec["start_time"],
                "end_time": rec["end_time"],
                "latency_seconds": round(rec["latency_seconds"], 4),
                "status": rec["status"],
                "input_tokens": rec["input_tokens"],
                "output_tokens": rec["output_tokens"],
                "total_tokens": rec["input_tokens"] + rec["output_tokens"],
                **{k: round(v, 10) for k, v in cost.items()},
                "valid_json": int(is_valid_json_response(rec["text"])),
            }
            row["attempts"] = rec["attempts"]
            rows.append(row)
            raw.append({"question_id": q["id"], "prompt_version": version, "response": rec["text"]})
            print(f"v{version} {q['id']}: {row['latency_seconds']:.2f}s, "
                  f"{row['input_tokens']}+{row['output_tokens']} tokens, status={row['status']}")
            time.sleep(config.CALL_DELAY_SECONDS)  # stay under free-tier limits; not part of latency

    df = pd.DataFrame(rows)
    df.to_csv(config.LATENCY_CSV, index=False)
    with open(config.RAW_JSONL, "w", encoding="utf-8") as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summarize_by_version(df).to_csv(config.EVAL_CSV, index=False)
    print(f"Saved {config.LATENCY_CSV.name}, {config.EVAL_CSV.name}, {config.RAW_JSONL.name}")
    return df


if __name__ == "__main__":
    run()

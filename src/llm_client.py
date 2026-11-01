"""Thin client for any OpenAI-compatible chat API (default: Groq free tier).
Measures latency of the successful attempt and reads token usage from the response."""
import time
from datetime import datetime, timezone

import requests

from . import config

MAX_ATTEMPTS = 4


def _headers() -> dict:
    return {"Content-Type": "application/json", "Authorization": f"Bearer {config.API_KEY}"}


def call_llm(prompt: str, question_id: str, prompt_version: int) -> dict:
    """Send one prompt; return a record with timing, status, text and token counts.
    Rate-limit (429) and server errors are retried; waiting time is NOT counted in latency."""
    payload = {
        "model": config.MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.TEMPERATURE,
        "seed": config.SEED,
        "max_tokens": config.MAX_TOKENS,
    }
    if config.REASONING_EFFORT:
        payload["reasoning_effort"] = config.REASONING_EFFORT

    record = {
        "question_id": question_id, "prompt_version": prompt_version,
        "model_name": config.MODEL_NAME, "status": "success", "text": "",
        "input_tokens": 0, "output_tokens": 0, "attempts": 0,
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        record["attempts"] = attempt
        record["start_time"] = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        try:
            resp = requests.post(f"{config.BASE_URL}/chat/completions", json=payload,
                                 headers=_headers(), timeout=120)
            record["latency_seconds"] = time.perf_counter() - t0
            record["end_time"] = datetime.now(timezone.utc).isoformat()
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = float(resp.headers.get("retry-after", 5 * attempt))
                record["status"] = f"error: HTTP {resp.status_code} (attempt {attempt})"
                if attempt < MAX_ATTEMPTS:
                    time.sleep(wait)
                    continue
                break
            resp.raise_for_status()
            data = resp.json()
            record["text"] = data["choices"][0]["message"].get("content") or ""
            usage = data.get("usage", {})
            record["input_tokens"] = int(usage.get("prompt_tokens", 0))
            record["output_tokens"] = int(usage.get("completion_tokens", 0))
            record["status"] = "success"
            break
        except Exception as exc:  # network error, bad JSON, 4xx other than 429
            record["latency_seconds"] = time.perf_counter() - t0
            record["end_time"] = datetime.now(timezone.utc).isoformat()
            record["status"] = f"error: {type(exc).__name__}: {exc}"
            break
    return record


def warm_up() -> None:
    """Open the connection / absorb first-call overhead so it does not skew the first real request."""
    call_llm("Say OK.", "warmup", 0)

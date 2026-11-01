"""Pure-Python helpers (no heavy imports) so they are easy to unit test."""
import json

ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def compute_cost(input_tokens: int, output_tokens: int,
                 price_in_per_m: float, price_out_per_m: float) -> dict:
    """Cost = tokens / 1,000,000 x price per million tokens (input and output separately)."""
    input_cost = input_tokens / 1_000_000 * price_in_per_m
    output_cost = output_tokens / 1_000_000 * price_out_per_m
    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": input_cost + output_cost,
    }


def projected_monthly_cost(avg_cost_per_request: float, requests: int = 10_000) -> float:
    return avg_cost_per_request * requests


def is_valid_json_response(text: str) -> bool:
    """STRICT check on the raw model output (no stripping of code fences).
    Valid = parses as a JSON object with the required keys and types."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("answer"), str):
        return False
    if data.get("confidence") not in ALLOWED_CONFIDENCE:
        return False
    kp = data.get("key_points")
    return isinstance(kp, list) and all(isinstance(x, str) for x in kp)

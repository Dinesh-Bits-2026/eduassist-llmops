import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.metrics import compute_cost, is_valid_json_response, projected_monthly_cost  # noqa: E402


def test_cost_formula():
    c = compute_cost(1_000_000, 500_000, 0.15, 0.60)
    assert abs(c["input_cost"] - 0.15) < 1e-12
    assert abs(c["output_cost"] - 0.30) < 1e-12
    assert abs(c["total_cost"] - 0.45) < 1e-12


def test_monthly_projection():
    assert abs(projected_monthly_cost(0.0002) - 2.0) < 1e-12


GOOD = {"answer": "x", "confidence": "high", "key_points": ["a", "b"]}


def test_valid_json_accepts_good():
    assert is_valid_json_response(json.dumps(GOOD))


def test_valid_json_rejects_code_fence():
    assert not is_valid_json_response("```json\n" + json.dumps(GOOD) + "\n```")


def test_valid_json_rejects_prose_and_bad_schema():
    assert not is_valid_json_response("Supervised learning uses labels.")
    assert not is_valid_json_response(json.dumps({**GOOD, "confidence": "certain"}))
    assert not is_valid_json_response(json.dumps({"answer": "x"}))
    assert not is_valid_json_response("")

"""Central configuration. All secrets/settings come from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# LLM endpoint (any OpenAI-compatible API)
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")  # required; never hard-code
MODEL_NAME = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
SEED = int(os.getenv("LLM_SEED", "42"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "").strip()
CALL_DELAY_SECONDS = float(os.getenv("CALL_DELAY_SECONDS", "3"))

# Pricing (USD per 1M tokens) - from the provider's published pricing page
PRICE_INPUT_PER_M = float(os.getenv("PRICE_INPUT_PER_M", "0"))
PRICE_OUTPUT_PER_M = float(os.getenv("PRICE_OUTPUT_PER_M", "0"))
PRICING_SOURCE = os.getenv("PRICING_SOURCE", "PLACEHOLDER")
PRICING_DATE = os.getenv("PRICING_DATE", "PLACEHOLDER")
PRICING_CURRENCY = os.getenv("PRICING_CURRENCY", "USD")

# Report cover details (optional)
STUDENT_NAME = os.getenv("STUDENT_NAME", "Student Name")
STUDENT_ID = os.getenv("STUDENT_ID", "Student ID")

# Assignment constants
MONTHLY_REQUESTS = 10_000
EXPERIMENT_NAME = "eduassist_llmops_assignment"
PROMPT_NAME = "eduassist_academic_qa"
PRODUCTION_ALIAS = "production"
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")

# Paths
QUESTIONS_PATH = ROOT / "data" / "questions.json"
OUTPUTS_DIR = ROOT / "outputs"
LATENCY_CSV = OUTPUTS_DIR / "latency_tokens_cost.csv"
EVAL_CSV = OUTPUTS_DIR / "prompt_evaluation_results.csv"
RAW_JSONL = OUTPUTS_DIR / "raw_responses.jsonl"
SCREENSHOTS_DIR = ROOT / "screenshots"
REPORT_DIR = ROOT / "report"
REPORT_TEXT = REPORT_DIR / "report_text.md"
REPORT_PDF = REPORT_DIR / "Assignment2_LLMOps_Report.pdf"
NOTEBOOK = ROOT / "notebooks" / "assignment2_llmops.ipynb"
NOTEBOOK_HTML = ROOT / "notebooks" / "assignment2_llmops.html"

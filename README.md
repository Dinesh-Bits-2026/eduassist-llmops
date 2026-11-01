# EduAssist AI: LLMOps Assignment 2

API latency, token-based cost and prompt version management with MLflow.
Course: MLOps (AIML ZG523), BITS Pilani WILP. Individual experiential learning assignment (10 marks).

An academic Q&A assistant must return strict JSON. Three prompt versions (v1 Basic, v2 Structured, v3 JSON Output) are run on the same five questions. Latency, tokens and cost are measured, the prompts are versioned in the MLflow Prompt Registry, and the best one is promoted with the `production` alias.

## Repository layout

```
.
├── README.md
├── requirements.txt
├── .env.example              # copy to .env (git-ignored)
├── data/questions.json       # the 5 academic questions
├── src/
│   ├── config.py             # settings from environment variables
│   ├── prompts.py            # prompt v1/v2/v3 (single source of truth)
│   ├── llm_client.py         # OpenAI-compatible API call + latency + token usage
│   ├── metrics.py            # cost formula, monthly projection, valid_json check
│   ├── analysis.py           # latency stats, per-version summary
│   ├── collect.py            # Step 1: 15 calls -> CSVs (Tasks 1 and 2)
│   ├── mlflow_eval.py        # Step 2: register prompts, log runs, promote (Task 3)
│   ├── prompt_evidence.py    # prints prompt diffs and the production alias
│   ├── build_report.py       # builds the PDF report from CSVs + screenshots + report/report_text.md
│   └── package_submission.py # checklist check + submission ZIP
├── notebooks/assignment2_llmops.ipynb   # submission notebook
├── tests/test_metrics.py
├── outputs/                  # latency_tokens_cost.csv, prompt_evaluation_results.csv, raw_responses.jsonl
├── screenshots/              # MLflow evidence
└── report/                   # final PDF report
```

## Setup (Windows PowerShell)

Python 3.11 or 3.12 is recommended (tested with Python 3.11.9 and MLflow 3.17.2).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then edit .env (model name, pricing)
```

### LLM provider and environment variables (`.env`)

The code talks to any OpenAI-compatible chat API. The default is Groq's free tier (no local model download needed).

1. Create a free account and API key at the provider console (for Groq: console.groq.com).
2. Check which model IDs are currently listed and note that model's published input/output price and the date.
3. Fill `.env` (never commit it):

| Variable | Purpose |
|---|---|
| `LLM_BASE_URL` | API base URL (default `https://api.groq.com/openai/v1`) |
| `LLM_API_KEY` | Your API key (secret, read from the environment only) |
| `LLM_MODEL` | Model ID, e.g. `openai/gpt-oss-20b` (verify it is currently available) |
| `LLM_TEMPERATURE`, `LLM_SEED`, `LLM_MAX_TOKENS` | Fixed generation settings for reproducibility |
| `LLM_REASONING_EFFORT` | Optional, for reasoning models only |
| `CALL_DELAY_SECONDS` | Pause between calls to respect rate limits (not counted in latency) |
| `PRICE_INPUT_PER_M`, `PRICE_OUTPUT_PER_M` | Published USD price per 1M tokens for the chosen model |
| `PRICING_SOURCE`, `PRICING_DATE`, `PRICING_CURRENCY` | Where, when and in what currency the price was taken |
| `MLFLOW_TRACKING_URI` | Default `sqlite:///mlflow.db` (Prompt Registry needs a database store) |

> Local alternative: the assignment also allows a locally hosted open-source model (e.g. via Ollama). That path was dropped here because the installer download was too slow.

## Reproduce the experiment

```powershell
python -m pytest -q tests            # sanity-check cost and JSON-validity logic
python -m src.collect                # Tasks 1 and 2: 15 calls -> outputs/*.csv
python -m src.mlflow_eval            # Task 3: register prompts, log runs, print recommendation
python -m src.mlflow_eval --promote 3   # set alias `production` (use the version you chose)
mlflow ui --backend-store-uri sqlite:///mlflow.db   # open http://127.0.0.1:5000
```

Or open `notebooks/assignment2_llmops.ipynb` and run the cells top to bottom.

## Build the report and package the submission

```powershell
python -m src.prompt_evidence        # optional: prompt diff + alias as text evidence
jupyter nbconvert --to html notebooks/assignment2_llmops.ipynb
python -m src.build_report           # writes report/Assignment2_LLMOps_Report.pdf
python -m src.package_submission     # checks the checklist, builds a lean submission/*.zip (add --full for everything)
```

Edit the wording in `report/report_text.md` (numbers in `{braces}` are filled from the CSVs). The builder prints the word count and warns about any `[VERIFY ...]` marker left in the text.

Screenshots expected in `screenshots/`: `01_experiment_runs.png`, `02_metrics_comparison.png`, `03_prompt_registry.png`, `04_prompt_diff.png`, `05_production_alias.png`.

## Method notes

- **Latency:** wall-clock time around each HTTP call (`time.perf_counter`), plus UTC start/end timestamps. A warm-up call absorbs first-connection overhead. Rate-limit retries and the pause between calls are not counted in latency.
- **Tokens:** read from the response `usage` field (`prompt_tokens`, `completion_tokens`).
- **Cost:** `tokens / 1,000,000 x price per million`, input and output separately, using the provider's published price for the chosen model (source, date and currency are recorded in `.env`).
- **Monthly projection:** average cost per request x 10,000.
- **valid_json:** strict `json.loads` on the raw output (code fences count as invalid) plus schema check (`answer` string, `confidence` in high/medium/low, `key_points` list of strings). Computed for all three versions.
- **Stats:** standard deviation is the sample standard deviation (n-1).

## Results

Run on 1 Nov 2026: 5 academic questions x 3 prompt versions = 15 requests, temperature 0, seed 42.

| Prompt Version | Avg Latency (s) | Avg Input Tokens | Avg Output Tokens | Avg Cost (USD) | Valid JSON Rate | Recommended? |
|---|---|---|---|---|---|---|
| v1 Basic | 1.35 | 91.4 | 665.4 | 0.000206 | 0.00 | No |
| v2 Structured | 1.65 | 113.4 | 463.8 | 0.000148 | 0.00 | No |
| **v3 JSON Output** | **1.13** | 147.4 | 305.2 | **0.000103** | **1.00** | **Yes (production alias)** |

Projected monthly cost at 10,000 requests: v1 $2.06, v2 $1.48, v3 $1.03.

**Model and pricing:** `openai/gpt-oss-20b` via Groq's OpenAI-compatible API (free tier). Prices used: $0.075 per 1M input tokens and $0.30 per 1M output tokens (USD), from https://console.groq.com/docs/model/openai/gpt-oss-20b, checked on 1 Nov 2026.

**Environment:** Python 3.11.9, MLflow 3.17.2.

### Key findings

- v3 is the only version that returns valid, schema-conforming JSON (5/5). v1 and v2 score 0 because they were never asked for JSON.
- v3 is also the fastest (1.13 s vs 1.35 s for v1 and 1.65 s for v2) and the cheapest (about 50% lower cost per request than v1).
- v3 has the longest prompt (147 vs 91 input tokens) but generates far fewer output tokens (305 vs 665), and output tokens dominate the cost.
- Version 3 was promoted with the MLflow alias `production`.
- Limits: one run, five questions, one model; latency depends on network and server load, and `valid_json` checks format, not correctness.

## Repository vs submission ZIP

This repository holds the full project. The submission ZIP (`python -m src.package_submission`) is a lean copy with only what the assignment asks for. The report builder, packaging and test scripts live in this repository only.

## Push to GitHub

Do this once at the start, then commit after each milestone.

```powershell
git init
git add .
git commit -m "Scaffold: LLMOps assignment 2 project structure"
git branch -M main
# create an empty repo on GitHub first (no README), then:
git remote add origin https://github.com/<account>/<repo-name>.git
git push -u origin main
```

Suggested commits as you go: `Task 1-2: collect latency, tokens, cost` -> `Task 3: MLflow prompt registry and evaluation` -> `Add screenshots and report`.

Before every push, check `git status` and confirm `.env` is **not** listed.

## Academic integrity

No API keys, billing details or personal data are committed. Secrets live in `.env` (git-ignored); only `.env.example` is tracked.

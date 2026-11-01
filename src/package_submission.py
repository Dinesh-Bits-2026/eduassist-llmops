"""Check the submission checklist and build the ZIP. Never includes .env, venv or MLflow stores.

Run:  python -m src.package_submission          # lean ZIP (what the assignment asks for)
      python -m src.package_submission --full   # everything, including helper scripts and tests
"""
import sys
import zipfile
from pathlib import Path

from . import config

REQUIRED = [
    config.NOTEBOOK, config.ROOT / "requirements.txt", config.LATENCY_CSV, config.EVAL_CSV,
    config.REPORT_PDF, config.ROOT / "README.md",
    *[config.SCREENSHOTS_DIR / n for n in (
        "01_experiment_runs.png", "02_metrics_comparison.png", "03_prompt_registry.png",
        "04_prompt_diff.png", "05_production_alias.png")],
]
RECOMMENDED = [config.NOTEBOOK_HTML]  # "exported PDF/HTML" of the notebook
EXCLUDE_DIRS = {".venv", ".git", "__pycache__", ".ipynb_checkpoints", ".pytest_cache",
                "mlruns", "mlartifacts", "submission"}
EXCLUDE_FILES = {".env", "mlflow.db"}
# Left out of the lean ZIP (still in the GitHub repo): helper scripts and tests the assignment does not ask for
LEAN_EXCLUDE = {"src/build_report.py", "src/package_submission.py", "src/prompt_evidence.py",
                "report/report_text.md", ".gitignore"}
LEAN_EXCLUDE_DIRS = {"tests"}
TEXT_EXT = {".py", ".md", ".csv", ".json", ".jsonl", ".ipynb", ".html", ".txt", ".example", ".yml", ".yaml"}


def collect_files(lean: bool = True) -> list[Path]:
    out = []
    for p in sorted(config.ROOT.rglob("*")):
        rel = p.relative_to(config.ROOT)
        if p.is_dir() or EXCLUDE_DIRS & set(rel.parts) or p.name in EXCLUDE_FILES or p.suffix == ".zip":
            continue
        if lean and (rel.as_posix() in LEAN_EXCLUDE or LEAN_EXCLUDE_DIRS & set(rel.parts)):
            continue
        out.append(p)
    return out


def main() -> int:
    missing = [p for p in REQUIRED if not p.exists()]
    for p in missing:
        print(f"MISSING (required): {p.relative_to(config.ROOT)}")
    for p in RECOMMENDED:
        if not p.exists():
            print(f"Recommended: {p.relative_to(config.ROOT)}  "
                  f"(run: jupyter nbconvert --to html notebooks/assignment2_llmops.ipynb)")
    if missing and "--force" not in sys.argv:
        print("Fix the missing files, or re-run with --force to package anyway.")
        return 1

    lean = "--full" not in sys.argv
    files = collect_files(lean)
    key = config.API_KEY
    if key and not key.startswith("paste-"):
        for p in files:
            if p.suffix in TEXT_EXT and key in p.read_text(encoding="utf-8", errors="ignore"):
                print(f"STOP: API key found inside {p.relative_to(config.ROOT)}. Remove it before submitting.")
                return 2

    out_dir = config.ROOT / "submission"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / f"Assignment2_LLMOps_{config.STUDENT_ID.replace(' ', '_')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path("eduassist-llmops") / p.relative_to(config.ROOT))
    print(f"Packaged {len(files)} files ({'lean' if lean else 'full'}) -> {zip_path}")
    print("Reminder: open the ZIP once and confirm there is no .env file inside.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

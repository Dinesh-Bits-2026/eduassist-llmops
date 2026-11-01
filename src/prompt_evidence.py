"""Print and save prompt diffs and the production alias, read from the MLflow Prompt Registry.
Useful as backup evidence for screenshots 04 and 05.

Run:  python -m src.prompt_evidence
"""
import difflib

import mlflow

try:
    from mlflow.genai import load_prompt
except ImportError:
    from mlflow import load_prompt

from . import config


def main() -> None:
    mlflow.set_tracking_uri(config.TRACKING_URI)
    templates = {v: load_prompt(f"prompts:/{config.PROMPT_NAME}/{v}").template for v in (1, 2, 3)}
    lines = []
    for a, b in [(1, 2), (2, 3)]:
        lines.append(f"===== Diff: {config.PROMPT_NAME} v{a} -> v{b} =====")
        lines += list(difflib.unified_diff(templates[a].splitlines(), templates[b].splitlines(),
                                           f"v{a}", f"v{b}", lineterm=""))
        lines.append("")
    prod = load_prompt(f"prompts:/{config.PROMPT_NAME}@{config.PRODUCTION_ALIAS}")
    lines.append(f"Alias '{config.PRODUCTION_ALIAS}' -> version {prod.version}")
    text = "\n".join(lines)
    print(text)
    config.OUTPUTS_DIR.mkdir(exist_ok=True)
    (config.OUTPUTS_DIR / "prompt_diff.txt").write_text(text, encoding="utf-8")
    print(f"\nSaved {config.OUTPUTS_DIR / 'prompt_diff.txt'}")


if __name__ == "__main__":
    main()

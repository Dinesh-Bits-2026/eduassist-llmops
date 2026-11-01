"""The three prompt versions, exactly as given in the assignment.
Single source of truth: used both for API calls and for MLflow registration."""

PROMPTS = {
    1: {
        "label": "Basic",
        "commit_message": "v1 Basic: plain instruction, no role, no format constraints",
        "template": (
            "Answer the following student question clearly.\n\n"
            "Question: {{question}}"
        ),
    },
    2: {
        "label": "Structured",
        "commit_message": "v2 Structured: adds academic-assistant role, concise/accurate tone, undergraduate language level",
        "template": (
            "You are an academic assistant.\n"
            "Answer the following student question in a clear, concise, and accurate manner.\n"
            "Use simple language suitable for undergraduate students.\n\n"
            "Question: {{question}}"
        ),
    },
    3: {
        "label": "JSON Output",
        "commit_message": "v3 JSON Output: enforces strict JSON schema (answer, confidence, key_points), no markdown or code fences",
        "template": (
            "You are an academic assistant.\n"
            "Answer the student question and return ONLY valid JSON.\n"
            "Do not include markdown, explanations outside JSON, or code fences.\n"
            "Use this exact JSON schema:\n"
            "{\n"
            '  "answer": "string",\n'
            '  "confidence": "high | medium | low",\n'
            '  "key_points": ["string"]\n'
            "}\n\n"
            "Question: {{question}}"
        ),
    },
}


def render(template: str, question: str) -> str:
    """Fill the {{question}} variable (same syntax MLflow Prompt Registry uses)."""
    return template.replace("{{question}}", question)

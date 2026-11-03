"""Build the PDF report from the CSV results, screenshots and report/report_text.md.

Run:  python -m src.build_report

Numbers in report_text.md are written as {placeholders} and filled from outputs/*.csv,
so the report stays in sync after a re-run. Edit the wording in report/report_text.md.
"""
import re
import sys
from datetime import date
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Image, KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.lib.utils import ImageReader

from . import config
from .analysis import latency_stats, summarize_by_version

NAVY = colors.HexColor("#1F3A5F")
ACCENT = colors.HexColor("#2E86AB")
LIGHT = colors.HexColor("#EAF2FB")
GREEN_BG = colors.HexColor("#E6F4EA")
GREY = colors.HexColor("#6B7280")
PAGE_W = 17 * cm  # A4 width minus 2 cm margins

SHOTS = [
    ("01_experiment_runs.png", "Figure 1: MLflow experiment showing the three runs and their metrics"),
    ("02_metrics_comparison.png", "Figure 2: Metric comparison across prompt versions"),
    ("03_prompt_registry.png", "Figure 3: Prompt Registry showing v1, v2 and v3 with commit messages"),
    ("04_prompt_diff.png", "Figure 4: Prompt diff between versions"),
    ("05_production_alias.png", "Figure 5: The production alias pointing to the promoted version"),
]


# ---------- data and placeholders ----------
def build_context(df: pd.DataFrame) -> dict:
    summ = summarize_by_version(df).set_index("prompt_version")
    best = int(summ.sort_values(["valid_json", "avg_cost_per_request", "avg_latency_seconds"],
                                ascending=[False, True, True]).index[0])
    v1 = df[df["prompt_version"] == 1]
    st = latency_stats(v1)
    slow = v1.loc[v1["latency_seconds"].idxmax()]
    ctx = {
        "model": config.MODEL_NAME, "base_url": config.BASE_URL, "temperature": config.TEMPERATURE,
        "seed": config.SEED, "max_tokens": config.MAX_TOKENS,
        "price_in": config.PRICE_INPUT_PER_M, "price_out": config.PRICE_OUTPUT_PER_M,
        "currency": config.PRICING_CURRENCY, "pricing_source": config.PRICING_SOURCE,
        "pricing_date": config.PRICING_DATE, "prompt_name": config.PROMPT_NAME,
        "experiment": config.EXPERIMENT_NAME, "best": best,
        "lat_mean": f"{st['mean']:.2f}", "lat_median": f"{st['median']:.2f}",
        "lat_min": f"{st['min']:.2f}", "lat_max": f"{st['max']:.2f}", "lat_std": f"{st['std']:.2f}",
        "v1_slowest_q": slow["question_id"], "v1_slowest_latency": f"{slow['latency_seconds']:.2f}",
        "v1_slowest_out": int(slow["output_tokens"]),
    }
    for v in summ.index:
        r = summ.loc[v]
        n = int((df["prompt_version"] == v).sum())
        ok = int(round(r["valid_json"] * n))
        ctx[f"v{v}_latency"] = f"{r['avg_latency_seconds']:.2f}"
        ctx[f"v{v}_in"] = f"{r['avg_input_tokens']:.1f}"
        ctx[f"v{v}_out"] = f"{r['avg_output_tokens']:.1f}"
        ctx[f"v{v}_cost"] = f"{r['avg_cost_per_request']:.6f}"
        ctx[f"v{v}_monthly"] = f"{r['avg_cost_per_request'] * config.MONTHLY_REQUESTS:.2f}"
        ctx[f"v{v}_valid"] = f"{r['valid_json']:.2f}"
        ctx[f"v{v}_valid_count"] = f"{ok}/{n}"
        ctx[f"v{v}_out_share"] = f"{r['avg_output_tokens'] / (r['avg_input_tokens'] + r['avg_output_tokens']) * 100:.0f}"
    if 1 in summ.index and best in summ.index:
        b, a = summ.loc[best], summ.loc[1]
        ctx["latency_cut"] = f"{(1 - b['avg_latency_seconds'] / a['avg_latency_seconds']) * 100:.0f}"
        ctx["out_cut"] = f"{(1 - b['avg_output_tokens'] / a['avg_output_tokens']) * 100:.0f}"
        ctx["cost_cut"] = f"{(1 - b['avg_cost_per_request'] / a['avg_cost_per_request']) * 100:.0f}"
    if 3 in summ.index:
        out_tok = summ.loc[3, "avg_output_tokens"]
        ctx["v3_saving25"] = f"{out_tok * 0.25 / 1_000_000 * config.PRICE_OUTPUT_PER_M * config.MONTHLY_REQUESTS:.2f}"
    return ctx


def load_sections(ctx: dict):
    text = config.REPORT_TEXT.read_text(encoding="utf-8")
    sections, key = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            key = line[3:].strip()
            sections[key] = []
        elif key is not None:
            sections[key].append(line)
    unknown = set()

    def fill(m):
        k = m.group(1)
        if k in ctx:
            return str(ctx[k])
        unknown.add(k)
        return m.group(0)

    out = {}
    for k, lines in sections.items():
        body = re.sub(r"\{(\w+)\}", fill, "\n".join(lines).strip())
        out[k] = [p.strip().replace("\n", " ") for p in re.split(r"\n\s*\n", body) if p.strip()]
    return out, unknown


def words(paragraphs) -> int:
    return len(re.findall(r"\S+", re.sub(r"\*\*", "", " ".join(paragraphs))))


# ---------- PDF helpers ----------
def clean(s: str) -> str:
    """Helvetica supports Latin-1/cp1252 only; replace anything else."""
    return str(s).encode("cp1252", "replace").decode("cp1252")


def para(text, style):
    t = escape(clean(text))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return Paragraph(t, style)


def table(data, widths=None, font=8, highlight_row=None):
    t = Table([[clean(c) for c in row] for row in data], colWidths=widths, repeatRows=1)
    cmds = [
        ("FONTSIZE", (0, 0), (-1, -1), font), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2E0")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if highlight_row is not None:
        cmds += [("BACKGROUND", (0, highlight_row), (-1, highlight_row), GREEN_BG),
                 ("FONTNAME", (0, highlight_row), (-1, highlight_row), "Helvetica-Bold")]
    t.setStyle(TableStyle(cmds))
    return t


def hhmmss(iso: str) -> str:
    return str(iso)[11:19] if len(str(iso)) >= 19 else str(iso)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(0.8)
    canvas.line(2 * cm, 1.25 * cm, A4[0] - 2 * cm, 1.25 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 0.8 * cm, "EduAssist AI - LLMOps Assignment 2")
    canvas.drawRightString(A4[0] - 2 * cm, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()


def image_flowable(path, caption, styles):
    iw, ih = ImageReader(str(path)).getSize()
    max_w, max_h = 15 * cm, 6.4 * cm
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    framed = Table([[Image(str(path), width=w, height=h)]], colWidths=[w + 10])
    framed.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#9AA8BC")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return KeepTogether([Spacer(1, 6), framed, Spacer(1, 4), para(caption, styles["cap"]), Spacer(1, 12)])


def link(url: str, color: str = "#1F5FBF") -> str:
    u = escape(url)
    return f'<a href="{u}" color="{color}">{u}</a>'


def banner(styles):
    inner = [para("LLMOps: API Cost, Latency and Prompt Version Management", styles["btitle"]),
             para("Experiential Learning Assignment 2 - MLOps (AIML ZG523)", styles["bsub"]),
             para(f"{config.STUDENT_NAME} | {config.STUDENT_ID} | {date.today():%d %b %Y}", styles["bsub"]),
             Paragraph(f"Code: {link(config.GITHUB_URL, '#9FD3FF')} | Video: {link(config.VIDEO_URL, '#9FD3FF')}",
                       styles["bsub"])]
    t = Table([[inner]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY),
                           ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                           ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    return t


def heading(text, styles):
    hr = HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceBefore=0, spaceAfter=6)
    hr.keepWithNext = True
    return [para(text, styles["h"]), hr]


# ---------- main ----------
def main() -> int:
    if not config.LATENCY_CSV.exists():
        print("Missing outputs/latency_tokens_cost.csv. Run: python -m src.collect")
        return 1
    df = pd.read_csv(config.LATENCY_CSV)
    ctx = build_context(df)
    sec, unknown = load_sections(ctx)
    if unknown:
        print("WARNING: unknown placeholders left as-is:", ", ".join(sorted(unknown)))

    base = getSampleStyleSheet()
    S = {
        "btitle": ParagraphStyle("bt", parent=base["Title"], fontSize=17, leading=21, textColor=colors.white,
                                 alignment=0, spaceAfter=4),
        "bsub": ParagraphStyle("bs", parent=base["Normal"], fontSize=9.5, textColor=colors.HexColor("#D6E4F5"),
                               leading=13),
        "h": ParagraphStyle("h", parent=base["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=12,
                            spaceAfter=3, keepWithNext=1),
        "p": ParagraphStyle("p", parent=base["BodyText"], fontSize=9.8, leading=13.8, spaceAfter=5),
        "callout": ParagraphStyle("co", parent=base["BodyText"], fontSize=9.8, leading=13.8, backColor=LIGHT,
                                  borderColor=ACCENT, borderWidth=0.8, borderPadding=7, leftIndent=8,
                                  rightIndent=8, spaceBefore=8, spaceAfter=18),
        "callout_green": ParagraphStyle("cg", parent=base["BodyText"], fontSize=9.8, leading=13.8,
                                        backColor=GREEN_BG, borderColor=colors.HexColor("#4C9F70"),
                                        borderWidth=0.8, borderPadding=7, leftIndent=8, rightIndent=8,
                                        spaceBefore=8, spaceAfter=18),
        "cap": ParagraphStyle("c", parent=base["Italic"], fontSize=8.5, alignment=1, textColor=GREY),
    }
    story = [banner(S), Spacer(1, 8)]

    def add(title, key, style="p"):
        story.extend(heading(title, S))
        for t in sec.get(key, []):
            story.append(para(t, S[style]))

    add("1. Objective and setup", "setup")

    # Task 1
    v1 = df[df["prompt_version"] == 1]
    add("2. Task 1: API calls and latency", "latency")
    rows = [["Question", "Prompt", "Model", "Start (UTC)", "End (UTC)", "Latency (s)", "Status"]]
    for _, r in v1.iterrows():
        rows.append([r["question_id"], f"v{r['prompt_version']}", r["model_name"], hhmmss(r["start_time"]),
                     hhmmss(r["end_time"]), f"{r['latency_seconds']:.3f}", r["status"]])
    story += [KeepTogether(table(rows, [2 * cm, 1.4 * cm, 4 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2 * cm], 7.5)), Spacer(1, 6)]
    st = latency_stats(v1)
    story += [table([["Mean", "Median", "Min", "Max", "Std dev"],
                     [f"{st[k]:.3f}" for k in ["mean", "median", "min", "max", "std"]]], None, 8.5), Spacer(1, 6)]
    for t in sec.get("latency_interpretation", []):
        story.append(para(t, S["p"]))

    # Task 2
    add("3. Task 2: Tokens and cost", "cost")
    rows = [["Question", "Input tok", "Output tok", "Total tok", "Input cost", "Output cost", "Total cost"]]
    for _, r in v1.iterrows():
        rows.append([r["question_id"], int(r["input_tokens"]), int(r["output_tokens"]), int(r["total_tokens"]),
                     f"{r['input_cost']:.7f}", f"{r['output_cost']:.7f}", f"{r['total_cost']:.7f}"])
    rows.append(["Average", f"{v1['input_tokens'].mean():.1f}", f"{v1['output_tokens'].mean():.1f}",
                 f"{v1['total_tokens'].mean():.1f}", "", "", f"{v1['total_cost'].mean():.7f}"])
    story += [KeepTogether(table(rows, None, 8)), Spacer(1, 4),
              para(f"Projected monthly cost for 10,000 requests (prompt v1): "
                   f"{v1['total_cost'].mean() * config.MONTHLY_REQUESTS:.2f} {config.PRICING_CURRENCY}", S["p"])]
    for t in sec.get("cost_optimization", []):
        story.append(para(t, S["callout"]))

    # Task 3
    add("4. Task 3: Prompt versioning and MLflow evaluation", "mlflow")
    summ = summarize_by_version(df)
    best = ctx["best"]
    rows = [["Prompt Version", "Avg Latency (s)", "Avg Input Tokens", "Avg Output Tokens", "Avg Cost",
             "Valid JSON Rate", "Recommended?"]]
    hl = None
    for _, r in summ.iterrows():
        v = int(r["prompt_version"])
        if v == best:
            hl = len(rows)
        rows.append([f"v{v}", f"{r['avg_latency_seconds']:.2f}", f"{r['avg_input_tokens']:.1f}",
                     f"{r['avg_output_tokens']:.1f}", f"{r['avg_cost_per_request']:.6f}",
                     f"{r['valid_json']:.2f}", "Yes" if v == best else "No"])
    story += [KeepTogether(table(rows, None, 8, highlight_row=hl)), Spacer(1, 10)]
    for fname, cap in SHOTS:
        path = config.SCREENSHOTS_DIR / fname
        if path.exists():
            story.append(image_flowable(path, cap, S))
        else:
            print(f"WARNING: screenshot missing: screenshots/{fname}")

    add("5. Promotion justification", "justification", "callout_green")
    add("6. Limitations", "limitations")
    story.extend(heading("7. Links", S))
    story.append(Paragraph(f"<b>GitHub repository:</b> {link(config.GITHUB_URL)}", S["p"]))
    story.append(Paragraph(f"<b>Video walkthrough:</b> {link(config.VIDEO_URL)}", S["p"]))

    config.REPORT_DIR.mkdir(exist_ok=True)
    SimpleDocTemplate(str(config.REPORT_PDF), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.8 * cm,
                      title="EduAssist LLMOps Assignment 2").build(story, onFirstPage=footer, onLaterPages=footer)

    prose_keys = ["setup", "latency", "latency_interpretation", "cost", "cost_optimization",
                  "mlflow", "justification", "limitations"]
    total = sum(words(sec.get(k, [])) for k in prose_keys)
    just = words(sec.get("justification", []))
    print(f"Saved {config.REPORT_PDF}")
    print(f"Prose word count: {total} (target 500-700) | justification: {just} (minimum 150)")
    if not 500 <= total <= 700:
        print("WARNING: total prose is outside 500-700 words")
    if just < 150:
        print("WARNING: justification is under 150 words")
    leftovers = [k for k in prose_keys if any("[VERIFY" in p for p in sec.get(k, []))]
    if leftovers:
        print("WARNING: [VERIFY ...] markers still present in:", ", ".join(leftovers))
    if "PLACEHOLDER" in str(config.PRICING_SOURCE) or "PLACEHOLDER" in str(config.PRICING_DATE):
        print("WARNING: pricing source/date still a placeholder in .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())

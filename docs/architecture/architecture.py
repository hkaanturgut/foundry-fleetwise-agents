"""FleetWise architecture diagram, drawn as code with the official Azure architecture icons.

Icons: Microsoft Azure Architecture Icons (https://learn.microsoft.com/azure/architecture/icons/),
converted to PNG in docs/architecture/icons/, plus the GitHub Actions, Terraform and Python logos.
The layout is fixed (landscape, left to right) so the picture reads like a reference architecture.

Regenerate:
    python docs/architecture/architecture.py
    rsvg-convert -z 2 docs/images/architecture.svg -o docs/images/architecture.png   # brew install librsvg
"""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "images" / "architecture.svg"
W, H = 1720, 1010
FONT = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
ICON = 64

BLUE, RED, PURPLE, GREEN, GREY, FOUNDRY = "#0078D4", "#D83B01", "#8661C5", "#107C10", "#605E5C", "#5C2D91"

parts: list[str] = []


def icon_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((HERE / "icons" / f"{name}.png").read_bytes()).decode()


def text(x: float, y: float, value: str, size: int = 12, color: str = "#323130", weight: str = "normal",
         anchor: str = "middle") -> None:
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
                 f'text-anchor="{anchor}">{escape(value)}</text>')


def node(x: float, y: float, name: str, title: str, subtitle: str = "", size: int = ICON) -> None:
    """Icon centred on (x, y) with a bold title and an optional grey subtitle below it."""
    parts.append(f'<image href="{icon_uri(name)}" x="{x - size / 2}" y="{y - size / 2}" width="{size}" height="{size}"/>')
    text(x, y + size / 2 + 17, title, 12.5, "#201F1E", "600")
    for i, line in enumerate(subtitle.split("\n") if subtitle else []):
        text(x, y + size / 2 + 33 + 14 * i, line, 11, GREY)


def box(x: float, y: float, w: float, h: float, label: str, color: str, fill: str, dashed: bool = False,
        logo: str | None = None) -> None:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{color}" '
                 f'stroke-width="1.5"{dash}/>')
    tx = x + 14
    if logo:
        parts.append(f'<image href="{icon_uri(logo)}" x="{x + 12}" y="{y + 9}" width="22" height="22"/>')
        tx += 28
    text(tx, y + 25, label, 13.5, color, "600", "start")


def edge(path: str, color: str = GREY, label: str = "", at: tuple[float, float] | None = None,
         style: str = "solid", width: float = 1.6) -> None:
    dash = {"solid": "", "dashed": ' stroke-dasharray="7 5"', "dotted": ' stroke-dasharray="2 4"'}[style]
    marker = {BLUE: "blue", RED: "red", PURPLE: "purple", GREEN: "green"}.get(color, "grey")
    parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{dash} '
                 f'marker-end="url(#arrow-{marker})"/>')
    if label and at:
        for i, line in enumerate(label.split("\n")):
            parts.append(f'<text x="{at[0]}" y="{at[1] + 14 * i}" font-size="11.5" fill="{color}" text-anchor="middle" '
                         f'paint-order="stroke" stroke="white" stroke-width="5" stroke-linejoin="round">{escape(line)}</text>')


def badge(x: float, y: float, number: str, color: str = BLUE) -> None:
    parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="{color}"/>')
    text(x, y + 4, number, 11, "white", "700")


# ---------- frame ----------
text(40, 44, "FleetWise agents on Microsoft Foundry", 24, "#201F1E", "600", "start")
text(40, 68, "Reference architecture: two Foundry prompt agents on a legacy API, orchestrated by Microsoft Agent "
     "Framework, gated by a human and by evaluations, with token usage in Azure Monitor.", 13, GREY, anchor="start")

# ---------- outside Azure ----------
node(95, 300, "users", "Fleet manager", "asks, approves\neach booking")

box(180, 130, 300, 650, "Presenter machine / CI runner", GREY, "#FAF9F8", dashed=True)
node(330, 300, "workflow", "Microsoft Agent Framework", "SequentialBuilder workflow\nhuman approval gate")
node(330, 500, "python", "Function tools", "get_dispatch_lines · list_qualified_\ntechnicians · approve / reject_work_order")
node(330, 680, "github-actions", "GitHub Actions", "eval gate on every agent change")

node(250, 905, "terraform", "Terraform  infra/", "deploys everything in Azure")

# ---------- Azure ----------
box(530, 92, 1160, 900, "Azure subscription  ·  resource group rg-fleetwise-*", BLUE, "#F5F9FD", logo="resource-group")

box(555, 140, 640, 560, "Microsoft Foundry  ·  account aif-*  ·  project proj-fleetwise", FOUNDRY, "#F8F5FC", logo="foundry")
node(670, 300, "agent", "fleet-triage", "prompt agent · read-only\nversioned · evaluated")
node(670, 500, "agent", "fleet-workorder", "prompt agent · books work\ntools run in the workflow")
node(880, 225, "vector-store", "Vector store", "5 SOP manuals (File Search)")
node(880, 405, "memory", "Memory store", "one scope per manager")
node(880, 600, "evaluations", "Evaluations", "quality · safety · policy")
box(1010, 185, 165, 350, "Models", FOUNDRY, "white")
node(1092, 290, "openai", "gpt-4o", "both agents")
node(1092, 450, "openai", "text-embedding-3-small", "memory")

box(1225, 140, 440, 330, "Legacy application", GREEN, "#F4FAF4")
box(1245, 185, 190, 265, "Container Apps env", GREEN, "white")
node(1340, 300, "container-app", "FleetWise API", ".NET 8 · system of record")
node(1560, 225, "acr", "Container Registry", "fleetwise-api image")
node(1560, 395, "managed-identity", "Managed identity", "AcrPull, no secrets")

box(555, 750, 1110, 220, "Azure Monitor", PURPLE, "#FAF7FD", logo="monitor")
node(700, 860, "app-insights", "Application Insights", "traces · gen_ai.usage.* tokens")
node(990, 860, "log-analytics", "Log Analytics", "AppDependencies · AzureMetrics")
node(1280, 860, "workbooks", "Workbook", "FleetWise token usage")

# ---------- request path ----------
edge("M 128 300 L 290 300", BLUE, "request, y / n", (210, 292), width=2.2)
edge("M 365 292 L 628 292", BLUE, "triage", (500, 284), width=2.2)
badge(420, 292, "1")
edge("M 365 312 C 480 312 520 492 628 492", BLUE, "work orders", (548, 410), width=2.2)
badge(445, 330, "2")
edge("M 636 506 L 372 506", GREY, "function calls", (560, 498), "dashed")
edge("M 365 524 L 505 524 L 505 725 L 1210 725 L 1210 312 L 1300 312", RED, "book, only after a human yes",
     (870, 719), width=2.2)
edge("M 670 266 L 670 130 L 1400 130 L 1400 252 L 1372 280", GREY, "OpenAPI tool, GET only", (1040, 134))

# ---------- inside Foundry ----------
edge("M 704 290 L 844 236", GREY, "File Search", (770, 252))
edge("M 704 310 L 844 396", GREY, "memory search", (810, 352), "dashed")
edge("M 704 494 L 844 414", GREY, "", None, "dashed")
edge("M 914 412 L 1056 446", GREY, "", None, "dotted")
edge("M 846 594 C 770 594 760 330 706 318", GREY, "scores each\nagent version", (738, 404), "dotted")
edge("M 365 672 L 540 672 C 600 672 760 650 846 612", GREY, "run evals, gate release", (600, 664), "dashed")

# ---------- platform ----------
edge("M 1526 232 L 1378 290", GREY, "image", (1470, 244), "dotted")
edge("M 1560 362 L 1560 304", GREY, "", None, "dotted")

# ---------- observability ----------
edge("M 420 780 L 420 860 L 664 860", PURPLE, "client spans\nfleetwise.run per command", (545, 832))
edge("M 700 700 L 700 822", PURPLE, "server spans, every model call", (790, 800))
edge("M 736 860 L 954 860", PURPLE, "", None)
edge("M 1026 860 L 1244 860", PURPLE, "", None)
edge("M 990 700 L 990 822", PURPLE, "account metrics: Input / OutputTokens\n(diagnostic setting, includes evals + memory)",
     (1120, 790), "dashed")

edge("M 282 905 L 524 905", GREY, "deploys", (400, 897), "dotted")

markers = "".join(
    f'<marker id="arrow-{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>'
    for n, c in {"blue": BLUE, "red": RED, "purple": PURPLE, "green": GREEN, "grey": GREY}.items()
)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">'
       f'<defs>{markers}</defs><rect width="{W}" height="{H}" fill="white"/>' + "".join(parts) + "</svg>\n")
OUT.write_text(svg)
print(f"wrote {OUT.relative_to(HERE.parents[1])}")

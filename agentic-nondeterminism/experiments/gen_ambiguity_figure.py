#!/usr/bin/env python3
"""
Generate decision ambiguity chart for OHBM 2026 poster.

Output: artifacts/fig_decision_ambiguity.png

One bar per workflow step, height = b (choice-space size).
Three subplots: Raw CUBE API | ChELL | IAS.
Red triangle marker above bars with high misreport risk (r >= 0.6).
Scan-select step in Raw API annotated with b=1,110 (no AccessionNumber baseline)
to contrast with the specific-intent baseline b=3 shown in the bar.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ── Step tables (same source as gen_failure_figures.py) ─────────────────────
# b  = observed choice-space size (specific-intent baseline, from CUBE crawl)
# r  = misreport weight (prob that an error here is silent)

RAW_STEPS = [
    {"label": "Auth",              "b": 1, "r": 0.1},
    {"label": "API root",          "b": 1, "r": 0.1},
    {"label": "Plugin\nsearch",    "b": 1, "r": 0.1},
    {"label": "Param\nschema",     "b": 4, "r": 0.6},
    {"label": "Compute\nresource", "b": 3, "r": 0.2},
    {"label": "Scan\nselect",      "b": 3, "r": 0.8},   # b=1,110 without AccessionNumber
    {"label": "Input\nfiles",      "b": 2, "r": 0.4},
    {"label": "Launch\ndircopy",   "b": 1, "r": 0.2},
    {"label": "Poll +\nextract ID","b": 2, "r": 0.3},
    {"label": "Launch\nfshack",    "b": 5, "r": 0.8},
    {"label": "Poll\nstatus",      "b": 2, "r": 0.5},
    {"label": "Validate\noutputs", "b": 3, "r": 0.8},
]

CHELL_STEPS = [
    {"label": "connect",           "b": 1, "r": 0.1},
    {"label": "PACS\nnavigate",    "b": 3, "r": 0.8},
    {"label": "Run\nfshack",       "b": 5, "r": 0.8},
    {"label": "Output\nnavigate",  "b": 1, "r": 0.2},
    {"label": "Validate",          "b": 2, "r": 0.8},
]

IAS_STEPS = [
    {"label": "Intent\ntranslate", "b": 2, "r": 0.4},
]

PARADIGMS = [
    {
        "name":     "Raw CUBE API",
        "subtitle": "N = 12 agent-controlled steps",
        "steps":    RAW_STEPS,
        "color":    "#d62728",
    },
    {
        "name":     "ChELL",
        "subtitle": "N = 5 agent-controlled steps",
        "steps":    CHELL_STEPS,
        "color":    "#e07b00",
    },
    {
        "name":     "Intent-Action Service",
        "subtitle": "N = 1 agent-controlled step",
        "steps":    IAS_STEPS,
        "color":    "#2ca02c",
    },
]

MISREPORT_THRESHOLD = 0.6   # r_i >= this → high silent failure risk marker
Y_MAX = 6.8                  # shared y ceiling (max b = 5, leave room for markers)

# ── Scan-select without-specific-intent annotation ──────────────────────────
# The bar shows b=3 (AccessionNumber provided, plugin name known).
# This annotation calls out what b would be without that context.
SCAN_SELECT_UNCONSTRAINED_B = 1110


def draw_panel(ax, paradigm: dict):
    steps  = paradigm["steps"]
    color  = paradigm["color"]
    n      = len(steps)
    xs     = list(range(n))
    labels = [s["label"] for s in steps]
    b_vals = [s["b"]     for s in steps]
    r_vals = [s["r"]     for s in steps]

    # Bars
    ax.bar(xs, b_vals, color=color, alpha=0.72, width=0.62, zorder=3,
           edgecolor=color, linewidth=0.6)

    # b=1 baseline (no ambiguity)
    ax.axhline(1, color="#888888", linewidth=0.9, linestyle=":",
               alpha=0.75, zorder=2)
    ax.text(-0.45, 1.06, "b = 1  (no choice)", fontsize=7,
            color="#888888", va="bottom", ha="left")

    # b value labels on bars
    for x, b in zip(xs, b_vals):
        if b > 1:
            ax.text(x, b + 0.12, str(b), ha="center", va="bottom",
                    fontsize=8, fontweight="bold", color=color)

    # High misreport risk markers (downward triangle above bar)
    for x, b, r in zip(xs, b_vals, r_vals):
        if r >= MISREPORT_THRESHOLD:
            ax.plot(x, b + 0.48, marker='v', color="#cc0000",
                    markersize=7, zorder=5, clip_on=False,
                    markeredgewidth=0)

    # Annotate scan-select unconstrained b in the Raw API panel
    if paradigm["name"] == "Raw CUBE API":
        scan_idx = next(
            i for i, s in enumerate(steps) if "select" in s["label"].lower()
        )
        ax.annotate(
            f"b = {SCAN_SELECT_UNCONSTRAINED_B:,}\n(no AccessionNumber)",
            xy=(scan_idx, b_vals[scan_idx] + 0.52),
            xytext=(scan_idx + 1.6, Y_MAX - 0.5),
            fontsize=7.5, color="#cc0000", ha="left", va="top",
            arrowprops=dict(arrowstyle="->", color="#cc0000",
                            lw=0.9, connectionstyle="arc3,rad=-0.2"),
        )

    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, Y_MAX)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7.5, rotation=38, ha="right",
                       rotation_mode="anchor")
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.set_title(
        f"{paradigm['name']}\n{paradigm['subtitle']}",
        fontsize=9.5, fontweight="bold", color=color, pad=7)
    ax.set_xlabel("Workflow step", fontsize=8.5)
    ax.grid(axis="y", linestyle=":", alpha=0.35, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def make_figure(outpath: str):
    fig, axes = plt.subplots(
        1, 3,
        figsize=(16, 5.2),
        sharey=True,
        gridspec_kw={"width_ratios": [12, 5, 2], "wspace": 0.06},
    )

    for ax, paradigm in zip(axes, PARADIGMS):
        draw_panel(ax, paradigm)

    axes[0].set_ylabel("Choice-space size  (b)", fontsize=10)

    legend_elems = [
        Patch(facecolor="#888888", alpha=0.72,
              label="Bar height = b  (specific intent: AccessionNumber + plugin name known)"),
        Line2D([0], [0], marker='v', color='w', markerfacecolor='#cc0000',
               markersize=8, label=f"Silent failure risk  (misreport weight r ≥ {MISREPORT_THRESHOLD})"),
    ]
    fig.legend(
        handles=legend_elems,
        loc="lower center", ncol=2,
        fontsize=8.5, framealpha=0.92,
        bbox_to_anchor=(0.5, -0.07),
    )

    fig.suptitle(
        "Agent Decision Ambiguity per Workflow Step\n"
        "FreeSurfer recon-all on ChRIS/CUBE  —  b = observed choice-space size "
        "from live CUBE crawl (2026-06-03)",
        fontsize=12, fontweight="bold", y=1.02,
    )

    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    print(f"Saved → {outpath}")
    plt.close(fig)


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    make_figure(os.path.join(out_dir, "fig_decision_ambiguity.png"))
    print("Done.")

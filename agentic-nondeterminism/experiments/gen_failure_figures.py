#!/usr/bin/env python3
"""
Generate failure-curve figures for OHBM 2026 poster.

Outputs (artifacts/):
  fig_total_failure.png   — cumulative total failure probability per step
  fig_silent_failure.png  — cumulative silent failure (misreport) rate per step

Three paradigms: Raw CUBE API | ChELL | Intent-Action Service (IAS)
Specific intent assumed (AccessionNumber provided, plugin name known).
p_base swept 0.01–0.15; per-step p_e scaled by log2(b) where b is the
observed choice-space size from the live CUBE crawl (2026-06-03).
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# ── Step tables ──────────────────────────────────────────────────────────────
# b  = observed choice-space size (from crawl data)
# r  = misreport weight: probability an error at this step is silent

RAW_STEPS = [
    {"label": "Auth",              "b": 1, "r": 0.1},
    {"label": "API root",          "b": 1, "r": 0.1},
    {"label": "Plugin\nsearch",    "b": 1, "r": 0.1},
    {"label": "Param\nschema",     "b": 4, "r": 0.6},
    {"label": "Compute\nresource", "b": 3, "r": 0.2},
    {"label": "Scan\nselect",      "b": 3, "r": 0.8},
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
        "color":    "#d62728",   # red
    },
    {
        "name":     "ChELL",
        "subtitle": "N = 5 agent-controlled steps",
        "steps":    CHELL_STEPS,
        "color":    "#e07b00",   # amber
    },
    {
        "name":     "Intent-Action Service",
        "subtitle": "N = 1 agent-controlled step",
        "steps":    IAS_STEPS,
        "color":    "#2ca02c",   # green
    },
]

# ── Model parameters ─────────────────────────────────────────────────────────
P_BASE_LO  = 0.01
P_BASE_HI  = 0.15
P_BASE_MID = 0.08
THRESHOLDS = [(0.05, "5%"), (0.20, "20%")]

# ── Math ──────────────────────────────────────────────────────────────────────

def step_pe(b: float, p_base: float) -> float:
    """p_e for one step: p_base scaled by log2(b), capped at 0.95."""
    w = max(1.0, np.log2(max(1.001, float(b))))
    return min(0.95, p_base * w)

def cumulative_total(steps: list, p_base: float) -> list:
    out, p_ok = [], 1.0
    for s in steps:
        p_ok *= (1.0 - step_pe(s["b"], p_base))
        out.append(1.0 - p_ok)
    return out

def cumulative_silent(steps: list, p_base: float) -> list:
    out, p_clean = [], 1.0
    for s in steps:
        pe = step_pe(s["b"], p_base)
        p_clean *= (1.0 - pe * s["r"])
        out.append(1.0 - p_clean)
    return out

# ── Drawing ───────────────────────────────────────────────────────────────────

def draw_panel(ax, paradigm: dict, metric_fn):
    steps  = paradigm["steps"]
    color  = paradigm["color"]
    n      = len(steps)
    xs     = list(range(n))
    labels = [s["label"] for s in steps]

    y_lo  = metric_fn(steps, P_BASE_LO)
    y_hi  = metric_fn(steps, P_BASE_HI)
    y_mid = metric_fn(steps, P_BASE_MID)

    if n == 1:
        # Single-step paradigm: render as a horizontal band
        xlo, xhi = -0.45, 0.45
        ax.fill_between([xlo, xhi], [y_lo[0]]*2, [y_hi[0]]*2,
                        alpha=0.28, color=color)
        ax.plot([xlo, xhi], [y_mid[0]]*2, color=color, linewidth=2.5,
                solid_capstyle="round")
        ax.plot([xlo, xhi], [y_lo[0]]*2, color=color, linewidth=0.9,
                linestyle="--", alpha=0.65)
        ax.plot([xlo, xhi], [y_hi[0]]*2, color=color, linewidth=0.9,
                linestyle="--", alpha=0.65)
        ax.set_xlim(-0.8, 0.8)
        ax.set_xticks([0])
        thresh_x = 0.72
    else:
        ax.fill_between(xs, y_lo, y_hi, alpha=0.28, color=color)
        ax.plot(xs, y_mid, color=color, linewidth=2.5, solid_capstyle="round",
                zorder=4)
        ax.plot(xs, y_lo, color=color, linewidth=0.9, linestyle="--",
                alpha=0.65, zorder=3)
        ax.plot(xs, y_hi, color=color, linewidth=0.9, linestyle="--",
                alpha=0.65, zorder=3)
        ax.scatter(xs, y_mid, color=color, s=28, zorder=5)
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_xticks(xs)
        thresh_x = n - 0.6

    ax.set_xticklabels(labels, fontsize=7.5, rotation=38, ha="right",
                       rotation_mode="anchor")

    # Threshold lines
    for thresh, label in THRESHOLDS:
        ax.axhline(thresh, color="#555555", linewidth=0.85, linestyle=":",
                   alpha=0.8, zorder=2)
        ax.text(thresh_x, thresh + 0.013, label,
                fontsize=7.5, va="bottom", ha="right",
                color="#555555", alpha=0.85)

    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(
        mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_title(
        f"{paradigm['name']}\n{paradigm['subtitle']}",
        fontsize=9.5, fontweight="bold", color=color, pad=7)
    ax.set_xlabel("Workflow step", fontsize=8.5)
    ax.grid(axis="y", linestyle=":", alpha=0.35, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def make_figure(metric_fn, suptitle: str, ylabel: str, outpath: str):
    fig, axes = plt.subplots(
        1, 3,
        figsize=(16, 5.2),
        sharey=True,
        gridspec_kw={"width_ratios": [12, 5, 2], "wspace": 0.06},
    )

    for ax, paradigm in zip(axes, PARADIGMS):
        draw_panel(ax, paradigm, metric_fn)

    axes[0].set_ylabel(ylabel, fontsize=10)

    # Shared legend
    legend_elems = [
        Patch(facecolor="#888888", alpha=0.28,
              label=f"p_base band  [{P_BASE_LO}–{P_BASE_HI}]"),
        Line2D([0], [0], color="#888888", linewidth=2.5,
               label=f"p_base = {P_BASE_MID}  (midpoint)"),
        Line2D([0], [0], color="#888888", linewidth=0.9,
               linestyle="--", alpha=0.65,
               label=f"p_base = {P_BASE_LO} / {P_BASE_HI}  (bounds)"),
    ]
    fig.legend(
        handles=legend_elems,
        loc="lower center", ncol=3,
        fontsize=8.5, framealpha=0.92,
        bbox_to_anchor=(0.5, -0.07),
    )

    fig.suptitle(suptitle, fontsize=12, fontweight="bold", y=1.02)
    fig.savefig(outpath, dpi=300, bbox_inches="tight")
    print(f"Saved → {outpath}")
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

    make_figure(
        cumulative_total,
        "Cumulative Total Failure Probability per Workflow Step\n"
        "FreeSurfer recon-all on ChRIS/CUBE — specific intent — "
        r"$p_e$ per step = $p_{base} \times \log_2(b)$,  "
        f"$p_{{base}}$ swept {P_BASE_LO}–{P_BASE_HI}",
        "Cumulative failure probability",
        os.path.join(out_dir, "fig_total_failure.png"),
    )

    make_figure(
        cumulative_silent,
        "Cumulative Silent Failure (Misreport) Rate per Workflow Step\n"
        "Wrong output reported as success — "
        r"$p_{silent,i} = p_{e,i} \times r_i$,  "
        f"$p_{{base}}$ swept {P_BASE_LO}–{P_BASE_HI}",
        "Cumulative misreport probability",
        os.path.join(out_dir, "fig_silent_failure.png"),
    )

    print("Done.")

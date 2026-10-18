#!/usr/bin/env python3
"""Figures of the WP-E6 gap report, produced only with matplotlib (the optional paper dependency).

``requirements-paper.txt`` pins matplotlib for paper scripts only; it is not an operational or runtime dependency.

Content (design docs/designs/EXACT_SOLVER_AMPL_DESIGN.md section 9, "Paper deliverable (WP-E6)"): per-wave (or
per-option) duration gap ``gD`` on the y axis against students per wave on the x axis, one panel per R, marker by
``dK``. ``gD`` is defined only where ``K_GA = K*`` (``dK = 0``); rows with ``dK >= 1`` have no ``gD`` and are NOT drawn:
each panel states their count, and the y axis is scaled on the drawn ``gD`` values only (``gD_free`` is never plotted on
the ``gD`` axis). Marker area grows with the number of coincident rows (there are no count labels).

Determinism: the ``Agg`` backend, a fixed DPI, a fixed ``svg.hashsalt``, text as paths (``svg.fonttype = path``, so the
files do not depend on installed fonts), and metadata without dates, creator or software strings. The figure objects are
built and saved inside one ``rc_context`` so the process-wide matplotlib configuration is never changed.
"""
from __future__ import annotations

import io
import math
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")
from matplotlib import rc_context  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

DPI = 200
HASHSALT = "uniride-wp-e6-gap-report"
RC = {
    "svg.hashsalt": HASHSALT, "svg.fonttype": "path", "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
    "savefig.dpi": DPI, "figure.dpi": DPI, "axes.unicode_minus": True,
}
SVG_METADATA = {"Date": None, "Creator": None}  # no date and no matplotlib version string in the file
PNG_METADATA = {"Software": None}
KIND_COLOR = {"base": "#0072B2", "q": "#D55E00"}
KIND_DODGE = {"base": -0.14, "q": 0.14}  # students; typed figure only, so that base and q at one point both show
AREA_PER_ROW = 18.0  # marker area (points^2) is AREA_PER_ROW * sqrt(coincident rows)
SIZE_KEYS = (1, 10, 30)
XMAX = 21.5


def marker_area(n: int) -> float:
    return AREA_PER_ROW * math.sqrt(n)


def gap_groups(rows: Sequence[dict]) -> Dict[str, List[tuple]]:
    """Drawable points per option kind: distinct (students, gD) of the rows with a ``gD``, with their row count."""
    groups: dict = {}
    for r in rows:
        if r["gD"] == "":
            continue
        kind = "base" if r["option"] == "base" else "q"
        key = (kind, int(r["students"]), round(float(r["gD"]), 6))
        groups[key] = groups.get(key, 0) + 1
    out: Dict[str, List[tuple]] = {"base": [], "q": []}
    for (kind, students, y), n in sorted(groups.items()):
        out[kind].append((students, y, n))
    return out


def excluded_counts(rows: Sequence[dict]) -> dict:
    """Rows not drawn: ``dK >= 1`` (gD undefined) per kind, and rows with a blank ``dK`` (the GA option is infeasible or the
    exact option is proven infeasible, so there is no pair of K values to compare)."""
    out = {"base": 0, "q": 0, "missing": 0}
    for r in rows:
        if r["dK"] == "":
            out["missing"] += 1
        elif int(r["dK"]) >= 1:
            out["base" if r["option"] == "base" else "q"] += 1
    return out


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _nice_top(top: float) -> float:
    return top * 1.12 if top > 0 else 0.01


def build_gap_figure(panels: Sequence[Sequence[dict]], panel_titles: Sequence[str], columns: int, title: str, subtitle: str,
                     kinds: Sequence[str]) -> Figure:
    """One panel per entry of ``panels`` (lists of wave_gaps.csv rows), row-major in ``columns`` columns."""
    n_rows = (len(panels) + columns - 1) // columns
    typed = len(kinds) > 1
    fig = Figure(figsize=(5.0 * columns + 1.4, 3.7 * n_rows + 2.0), dpi=DPI)
    axes = fig.subplots(n_rows, columns, squeeze=False)
    groups = [gap_groups(p) for p in panels]
    top = max([y for g in groups for pts in g.values() for _, y, _ in pts] + [0.0])
    ytop = _nice_top(top)
    ylo = -0.06 * ytop
    for idx, (ax, rows, g, ptitle) in enumerate(zip(axes.flat, panels, groups, panel_titles)):
        ax.set_xlim(-0.5, XMAX)
        ax.set_ylim(ylo, ytop)
        ax.set_xticks([0, 5, 10, 15, 20])
        ax.grid(True, color="#e6e6e6", linewidth=0.6)
        ax.axhline(0.0, color="#999999", linewidth=0.8, linestyle=(0, (4, 3)))
        ax.set_title(ptitle, fontsize=9, fontweight="bold")
        ax.set_xlabel("Students per wave", fontsize=8)
        if idx % columns == 0:
            ax.set_ylabel("gD", fontsize=9)
        ax.tick_params(labelsize=8)
        for kind in kinds:
            pts = g[kind]
            if not pts:
                continue
            dodge = KIND_DODGE[kind] if typed else 0.0
            ax.scatter([s + dodge for s, _, _ in pts], [y for _, y, _ in pts], s=[marker_area(n) for _, _, n in pts],
                       marker="o", color=KIND_COLOR[kind], alpha=0.6, linewidths=0.4, edgecolors=KIND_COLOR[kind], zorder=3)
        ex = excluded_counts(rows)
        if typed:
            note = f"dK ≥ 1: {_plural(ex['base'], 'base wave')}, {_plural(ex['q'], 'q option')} (gD undefined, not drawn)"
        else:
            note = f"dK ≥ 1: {_plural(ex['base'] + ex['q'], 'wave')} (gD undefined, not drawn)"
        ax.text(0.02, 0.97, note, transform=ax.transAxes, fontsize=7, va="top", ha="left", color="#333333")
        if ex["missing"]:
            ax.text(0.02, 0.90, f"GA option infeasible or exact option proven infeasible: {_plural(ex['missing'], 'option')}, not drawn",
                    transform=ax.transAxes, fontsize=7, va="top", ha="left", color="#333333")
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold")
    if typed:
        subtitle += f"; base and q markers are shifted by ±{KIND_DODGE['q']} students (offset, so that both show)"
    fig.text(0.01, 0.945 if n_rows == 1 else 0.958, subtitle, ha="left", va="top", fontsize=8.5, color="#444444")
    unit = "rows" if typed else "waves"
    handles, labels = [], []
    for kind in kinds:
        label = "base: K, xbase against GA base; dK = 0, y = gD" if kind == "base" else "q: K_m, xq against GA q; dK = 0, y = gD"
        handles.append(Line2D([], [], marker="o", linestyle="", color=KIND_COLOR[kind], alpha=0.6, markersize=6))
        labels.append(label if typed else "dK = 0, y = gD")
    for n in SIZE_KEYS:
        handles.append(Line2D([], [], marker="o", linestyle="", color="#777777", alpha=0.6, markersize=math.sqrt(marker_area(n))))
        labels.append(f"{n} coincident {unit[:-1] if n == 1 else unit}")
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.01, 0.925 if n_rows == 1 else 0.938), ncol=len(handles),
               fontsize=7.5, frameon=False, title="Marker area grows with the number of coincident rows", title_fontsize=7.5,
               alignment="left")
    fig.subplots_adjust(left=0.06 if columns > 2 else 0.08, right=0.99, bottom=0.08, top=0.80 if n_rows == 1 else 0.84,
                        hspace=0.35, wspace=0.12 if columns > 2 else 0.14)
    return fig


def render(fig: Figure) -> Dict[str, bytes]:
    """The deterministic SVG and PNG bytes of a figure."""
    out = {}
    with rc_context(RC):
        for fmt, meta in (("svg", SVG_METADATA), ("png", PNG_METADATA)):
            buf = io.BytesIO()
            fig.savefig(buf, format=fmt, metadata=dict(meta), dpi=DPI)
            out[fmt] = buf.getvalue()
    return out


def figure_context():
    """The rc context that figures must be built in (``svg.hashsalt`` and the fonts are read at draw and save time)."""
    return rc_context(RC)

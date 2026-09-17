"""Primary figures from metric tables (matplotlib, static PNG/PDF).

    Figure 1  I(n) per model                      plot_metric_by(..., "size")
    Figure 2  I(d) per model                      plot_metric_by(..., "transfer_level")
    Figure 3  I(c) and S(c) per model, one axis    plot_compute()

Design rules kept deliberately simple (correctness first): one y-axis per
panel (0..1 proportion), one fixed colour per model across every figure
(never reassigned when a filter changes the series count), Wilson intervals
as error bars, a legend whenever more than one series is drawn, per-family
panels next to the pooled panel.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# validated categorical palette (fixed slot order; see dataviz palette reference)
SERIES_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6b4fbb", "#8c8c8c"]
LINESTYLES = {"I": "-", "S": "--"}


def _model_colours(tables: Sequence[list[dict]]) -> dict[str, str]:
    models = sorted({row["model"] for table in tables for row in table if row.get("model") is not None})
    return {m: SERIES_COLOURS[i % len(SERIES_COLOURS)] for i, m in enumerate(models)}


def _split_by(table: list[dict], keys: Sequence[str]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = defaultdict(list)
    for row in table:
        out[tuple(row.get(k) for k in keys)].append(row)
    return out


def _x_positions(table: list[dict], x_key: str) -> tuple[list, dict]:
    values = sorted({row[x_key] for row in table}, key=lambda v: (v is None, v))
    if all(isinstance(v, (int, float)) for v in values):
        return values, {v: v for v in values}
    return list(range(len(values))), {v: i for i, v in enumerate(values)}


def _draw_series(ax, rows: list[dict], x_key: str, pos: dict, colour: str, label: str, linestyle: str = "-") -> None:
    rows = sorted(rows, key=lambda r: pos[r[x_key]])
    xs = [pos[r[x_key]] for r in rows]
    ys = [r["p"] for r in rows]
    err_lo = [max(0.0, r["p"] - r["ci_low"]) for r in rows]
    err_hi = [max(0.0, r["ci_high"] - r["p"]) for r in rows]
    ax.errorbar(xs, ys, yerr=[err_lo, err_hi], color=colour, linestyle=linestyle, linewidth=1.6, marker="o", markersize=4, capsize=2, label=label)


def plot_metric_by(pooled: Optional[list[dict]], by_family: list[dict], x_key: str, metric_label: str, out_path: str | Path, title: Optional[str] = None) -> Path:
    """One panel per family (plus a pooled panel when ``pooled`` is given); one line per model.

    Pass ``pooled=None`` for x = size: size scales are family-specific, so pooling
    over families by raw size is not meaningful."""
    families = sorted({r["family"] for r in by_family})
    panels = ([("pooled", pooled)] if pooled is not None else []) + [(fam, [r for r in by_family if r["family"] == fam]) for fam in families]
    n_panels = max(1, len(panels))
    fig, axes = plt.subplots(1, n_panels, figsize=(4.2 * n_panels, 3.6), sharey=True, squeeze=False)
    colours = _model_colours([pooled or [], by_family])
    for ax, (name, table) in zip(axes[0], panels):
        if not table:
            ax.set_visible(False)
            continue
        _, pos = _x_positions(table, x_key)
        for (model,), rows in _split_by(table, ("model",)).items():
            _draw_series(ax, rows, x_key, pos, colours[model], str(model))
        ax.set_title(name, fontsize=10)
        ax.set_xlabel(x_key.replace("_", " "))
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.25)
        if pos and not all(isinstance(v, (int, float)) for v in pos):
            ax.set_xticks(list(pos.values()))
            ax.set_xticklabels([str(k) for k in pos], rotation=0)
    axes[0][0].set_ylabel(metric_label)
    if len(colours) > 1:
        axes[0][0].legend(fontsize=8, frameon=False)
    fig.suptitle(title or metric_label, fontsize=11)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_compute(I_pooled: list[dict], S_pooled: list[dict], I_family: list[dict], S_family: list[dict], out_path: str | Path, x_key: str = "compute_level") -> Path:
    """I(c) (solid) and S(c) (dashed) per model on one proportion axis, per family + pooled."""
    families = sorted({r["family"] for r in I_family} | {r["family"] for r in S_family})
    n_panels = 1 + len(families)
    fig, axes = plt.subplots(1, n_panels, figsize=(4.2 * n_panels, 3.6), sharey=True, squeeze=False)
    colours = _model_colours([I_pooled, S_pooled])
    panels = [("pooled", I_pooled, S_pooled)] + [(fam, [r for r in I_family if r["family"] == fam], [r for r in S_family if r["family"] == fam]) for fam in families]
    for ax, (name, I_t, S_t) in zip(axes[0], panels):
        if not I_t and not S_t:
            ax.set_visible(False)
            continue
        order = sorted({r[x_key] for r in I_t + S_t}, key=lambda v: (_rank_of(I_t + S_t, v), str(v)))
        pos = {v: i for i, v in enumerate(order)}
        for (model,), rows in _split_by(I_t, ("model",)).items():
            _draw_series(ax, rows, x_key, pos, colours[model], f"I(c) {model}", LINESTYLES["I"])
        for (model,), rows in _split_by(S_t, ("model",)).items():
            _draw_series(ax, rows, x_key, pos, colours[model], f"S(c) {model}", LINESTYLES["S"])
        ax.set_xticks(list(pos.values()))
        ax.set_xticklabels([str(k) for k in order])
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("compute condition")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(True, alpha=0.25)
    axes[0][0].set_ylabel("proportion")
    axes[0][0].legend(fontsize=8, frameon=False)
    fig.suptitle("Idea discovery I(c) and solution accuracy S(c) vs compute", fontsize=11)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def _rank_of(rows: list[dict], value) -> int:
    for r in rows:
        if r.get("compute_level") == value and r.get("compute_rank") is not None:
            return int(r["compute_rank"])
    return 10**6


def make_all_figures(tables: dict[str, list[dict]], out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    made = []
    made.append(plot_metric_by(None, tables["I_n_by_family"], "size", "I(n) = P(valid idea | n)", out_dir / "fig1_idea_vs_size.png", "Idea discovery vs instance size"))
    made.append(plot_metric_by(None, tables["S_n_by_family"], "size", "S(n) = P(correct | n)", out_dir / "fig1b_solution_vs_size.png", "Solution accuracy vs instance size"))
    if tables.get("I_d_pooled"):
        made.append(plot_metric_by(tables["I_d_pooled"], tables["I_d_by_family"], "transfer_level", "I(d) = P(valid idea | d)", out_dir / "fig2_idea_vs_transfer.png", "Idea discovery vs structural-transfer distance"))
        made.append(plot_metric_by(tables["S_d_pooled"], tables["S_d_by_family"], "transfer_level", "S(d) = P(correct | d)", out_dir / "fig2b_solution_vs_transfer.png", "Solution accuracy vs structural-transfer distance"))
    if tables.get("I_c_pooled"):
        made.append(plot_compute(tables["I_c_pooled"], tables["S_c_pooled"], tables["I_c_by_family"], tables["S_c_by_family"], out_dir / "fig3_idea_solution_vs_compute.png"))
    if tables.get("S_n_given_I1_pooled") or tables.get("S_n_given_I0_pooled"):
        made.append(plot_metric_by(None, tables["S_n_given_I1_by_family"], "size", "S(n | I=1)", out_dir / "diag_solution_given_idea.png", "Diagnostic: S(n | I = 1)"))
        made.append(plot_metric_by(None, tables["S_n_given_I0_by_family"], "size", "S(n | I=0)", out_dir / "diag_solution_given_no_idea.png", "Diagnostic: S(n | I = 0)"))
    return made

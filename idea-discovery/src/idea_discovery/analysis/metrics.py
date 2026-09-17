"""Primary metrics computed from the tidy table.

    I(n) = P(valid idea | size n)            over idea-bearing trials
    S(n) = P(correct answer | size n)        over all trials
    I(d), S(d)                               by transfer level
    I(c), S(c)                               by compute condition
    F    = P(valid certificate | idea supplied)
    S(n | I = 1), S(n | I = 0)               diagnostic only

Every cell reports n, k, the proportion, a Wilson interval and a cluster
bootstrap interval (clusters = instances, so repeated trials on the same
instance are not treated as independent). Per-family tables are always
produced alongside pooled ones; nothing is collapsed into a single score.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Optional, Sequence

import numpy as np

from ..utils.stats import wilson_interval

GROUP_MODEL = ("model",)
GROUP_MODEL_FAMILY = ("model", "family")


def _cluster_bootstrap(values: Sequence[int], clusters: Sequence[str], n_boot: int, seed: int) -> tuple[float, float]:
    if len(values) == 0:
        return (float("nan"), float("nan"))
    by_cluster: dict[str, list[int]] = defaultdict(list)
    for v, c in zip(values, clusters):
        by_cluster[c].append(v)
    groups = [np.asarray(g, dtype=float) for g in by_cluster.values()]
    if len(groups) == 1:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    sums = np.array([g.sum() for g in groups])
    counts = np.array([g.size for g in groups])
    idx = rng.integers(0, len(groups), size=(n_boot, len(groups)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return (float(lo), float(hi))


def proportion_table(
    rows: Iterable[dict],
    group_keys: Sequence[str],
    outcome: Callable[[dict], Optional[bool]],
    row_filter: Optional[Callable[[dict], bool]] = None,
    n_boot: int = 1000,
    seed: int = 0,
    cluster_key: str = "instance_id",
) -> list[dict]:
    """Proportion of ``outcome`` per group. ``outcome`` returning None excludes the row."""
    cells: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for r in rows:
        if row_filter is not None and not row_filter(r):
            continue
        o = outcome(r)
        if o is None:
            continue
        cells[tuple(r.get(k) for k in group_keys)].append((int(bool(o)), str(r.get(cluster_key))))
    out = []
    for key in sorted(cells, key=lambda t: tuple((v is None, v) for v in t)):
        vals = [v for v, _ in cells[key]]
        clusters = [c for _, c in cells[key]]
        n, k = len(vals), sum(vals)
        lo, hi = wilson_interval(k, n)
        blo, bhi = _cluster_bootstrap(vals, clusters, n_boot, seed)
        entry = dict(zip(group_keys, key))
        entry.update({"n": n, "k": k, "p": k / n if n else float("nan"), "ci_low": lo, "ci_high": hi, "boot_low": blo, "boot_high": bhi, "n_clusters": len(set(clusters))})
        out.append(entry)
    return out


# -- outcome functions ---------------------------------------------------------
def _idea(r: dict) -> Optional[bool]:
    return bool(r.get("idea_valid"))


def _solution(r: dict) -> Optional[bool]:
    # an unparsed answer counts as incorrect (the model did not commit to an answer)
    v = r.get("solution_correct")
    return bool(v) if v is not None else False


def _formalization(r: dict) -> Optional[bool]:
    v = r.get("formalization_valid")
    return None if v is None else bool(v)


def _posthoc(r: dict) -> Optional[bool]:
    v = r.get("posthoc_valid")
    return None if v is None else bool(v)


def _idea_bearing(r: dict) -> bool:
    return bool(r.get("idea_bearing"))


def _has_free_solve(r: dict) -> bool:
    return r.get("outcome_category") not in (None, "no_free_solve")


# -- metric tables -------------------------------------------------------------
def _groups(per_family: bool, key: Optional[str]) -> tuple[str, ...]:
    """Grouping keys; the compute level is always accompanied by its rank so tables and
    figures can order conditions low -> high rather than alphabetically."""
    base = GROUP_MODEL_FAMILY if per_family else GROUP_MODEL
    if key is None:
        return base
    if key == "compute_level":
        return base + ("compute_rank", "compute_level")
    return base + (key,)


def idea_by(rows: list[dict], key: str, per_family: bool, **kw) -> list[dict]:
    return proportion_table(rows, _groups(per_family, key), _idea, lambda r: _idea_bearing(r) and _has_free_solve(r), **kw)


def solution_by(rows: list[dict], key: str, per_family: bool, **kw) -> list[dict]:
    return proportion_table(rows, _groups(per_family, key), _solution, _has_free_solve, **kw)


def solution_by_conditional(rows: list[dict], key: str, per_family: bool, idea_value: bool, **kw) -> list[dict]:
    return proportion_table(rows, _groups(per_family, key), _solution, lambda r: _idea_bearing(r) and _has_free_solve(r) and bool(r.get("idea_valid")) == idea_value, **kw)


def formalization_rate(rows: list[dict], per_family: bool, extra_key: Optional[str] = None, **kw) -> list[dict]:
    return proportion_table(rows, _groups(per_family, extra_key), _formalization, _idea_bearing, **kw)


def posthoc_rate(rows: list[dict], per_family: bool, extra_key: Optional[str] = None, **kw) -> list[dict]:
    return proportion_table(rows, _groups(per_family, extra_key), _posthoc, _idea_bearing, **kw)


def recognition_rate(rows: list[dict], per_family: bool, **kw) -> list[dict]:
    groups = (GROUP_MODEL_FAMILY if per_family else GROUP_MODEL) + ("transfer_level",)
    return proportion_table(rows, groups, lambda r: r.get("recognized_classic"), None, **kw)


def outcome_counts(rows: list[dict], group_keys: Sequence[str] = ("model", "family", "size")) -> list[dict]:
    counts: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        counts[tuple(r.get(k) for k in group_keys)][r.get("outcome_category") or "none"] += 1
    out = []
    for key in sorted(counts, key=lambda t: tuple((v is None, v) for v in t)):
        entry = dict(zip(group_keys, key))
        entry.update(counts[key])
        out.append(entry)
    return out


def compute_all(rows: list[dict], n_boot: int = 1000, seed: int = 0) -> dict[str, list[dict]]:
    """All primary and diagnostic tables, pooled and per family."""
    kw = {"n_boot": n_boot, "seed": seed}
    tables: dict[str, list[dict]] = {}
    for key, tag in (("size", "n"), ("transfer_level", "d"), ("compute_level", "c")):
        for per_family, suffix in ((False, "pooled"), (True, "by_family")):
            tables[f"I_{tag}_{suffix}"] = idea_by(rows, key, per_family, **kw)
            tables[f"S_{tag}_{suffix}"] = solution_by(rows, key, per_family, **kw)
            tables[f"S_{tag}_given_I1_{suffix}"] = solution_by_conditional(rows, key, per_family, True, **kw)
            tables[f"S_{tag}_given_I0_{suffix}"] = solution_by_conditional(rows, key, per_family, False, **kw)
    for per_family, suffix in ((False, "pooled"), (True, "by_family")):
        tables[f"F_{suffix}"] = formalization_rate(rows, per_family, **kw)
        tables[f"F_by_size_{suffix}"] = formalization_rate(rows, per_family, "size", **kw)
        tables[f"F_by_transfer_{suffix}"] = formalization_rate(rows, per_family, "transfer_level", **kw)
        tables[f"posthoc_valid_{suffix}"] = posthoc_rate(rows, per_family, **kw)
        tables[f"recognition_{suffix}"] = recognition_rate(rows, per_family, **kw)
    tables["outcome_counts"] = outcome_counts(rows)
    return tables

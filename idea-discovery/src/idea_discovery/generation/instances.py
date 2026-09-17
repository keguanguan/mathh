"""Deterministic instance-set generation.

For every (family, size, transfer level) cell, ``instances_per_cell``
instances are generated from seeds derived from ``base_seed``. The same
seed index yields *paired* instances across transfer levels >= 1 (the d2
instance is the surface-transformed d1 instance), so transfer effects can be
estimated within instance. Level 0 is the single classical seed problem.

Every generated instance passes ``family.sanity_check`` or generation fails.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from ..families.base import Instance, ProblemFamily, get_family
from ..utils.hashing import derive_seed


@dataclass
class GenerationSpec:
    family_id: str
    sizes: list[int]
    transfer_levels: list[int]
    instances_per_cell: int
    base_seed: int
    family_parameters: Optional[dict] = None


def cell_seed(base_seed: int, family_id: str, size: int, index: int) -> int:
    """Seed for the index-th instance of a (family, size) cell; shared across transfer levels."""
    return derive_seed(base_seed, family_id, size, index) % 1_000_000


def generate_instance_set(spec: GenerationSpec, family: Optional[ProblemFamily] = None, strict: bool = True) -> list[Instance]:
    family = family or get_family(spec.family_id, **(spec.family_parameters or {}))
    out: list[Instance] = []
    seen: set[str] = set()
    for level in spec.transfer_levels:
        if level == 0:
            inst = family.classical_instance()
            _check(family, inst, strict)
            if inst.instance_id not in seen:
                out.append(inst)
                seen.add(inst.instance_id)
            continue
        for size in spec.sizes:
            for idx in range(spec.instances_per_cell):
                seed = cell_seed(spec.base_seed, spec.family_id, size, idx)
                inst = family.generate_transfer_instance(level, seed, size=size)
                _check(family, inst, strict)
                if inst.instance_id in seen:
                    raise RuntimeError(f"duplicate instance id {inst.instance_id}")
                seen.add(inst.instance_id)
                out.append(inst)
    return out


def _check(family: ProblemFamily, inst: Instance, strict: bool) -> None:
    problems = family.sanity_check(inst)
    if problems and strict:
        raise RuntimeError(f"instance {inst.instance_id} failed sanity checks: {problems}")


def instances_from_records(records: Iterable[dict]) -> list[Instance]:
    return [Instance.from_dict(r) for r in records]

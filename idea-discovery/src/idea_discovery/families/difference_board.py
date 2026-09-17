"""Difference board (seed: Euclid's game, corpus id ``euclids_game``).

Structure: ``difference_board`` (a few positive integers; a move writes the
positive difference of two numbers on the board, if it is not there yet).
Question: can a given target number ever be written?

Canonical idea: every number written is a multiple of g = gcd(initial numbers)
(gcd invariant). Ground truth is exact: the closure is the set of positive
multiples of g up to the maximum, whatever the play, so target is reachable iff
g | target and target <= max (witness = an explicit sequence of differences).

Size parameter: magnitude bound n on the initial numbers (the naive search
space - boards of numbers up to n - grows with n).

Transfer surfaces:
    d0  the classical game statement (two numbers, who wins)
    d1  numbers on a board, "can T be written?"
    d2  rods in a workshop: a new rod may be cut to the difference of two rods' lengths
"""
from __future__ import annotations

import random
import re
from typing import Optional

from ..extraction.json_block import find_certificates
from ..generation.seeds import seed_provenance, seed_statement
from ..structures import difference_board as db
from ..utils.hashing import derive_seed
from .base import CanonicalIdea, ExtractedCertificate, Instance, ProblemFamily, register_family

SURFACES = {0: "classical_euclid_game", 1: "numbers_on_board", 2: "rod_lengths"}
SEED_ID = "euclids_game"


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    s = start
    while s > 0 and text[s - 1] not in ".!?\n":
        s -= 1
    e = end
    while e < len(text) and text[e] not in ".!?\n":
        e += 1
    return s, min(len(text), e + 1)


@register_family
class DifferenceBoardFamily(ProblemFamily):
    family_id = "difference_board"
    idea_type = "gcd_invariant"
    domain = "elementary number theory / processes"
    size_parameter = "magnitude bound n on the initial numbers"
    certificate_type = "gcd_invariant"
    certificate_types = ("gcd_invariant", "explicit_construction")
    verification_method = "symbolic"
    generation_method = "seeded g in 2..12, initial numbers g * random in [1, n/g]; target multiple / non-multiple of g below the maximum; exact closure ground truth"
    supported_transfer_levels = (0, 1, 2)
    version = "0.1"

    def __init__(self, possible_fraction: float = 0.35, n_numbers: int = 3, gcd_range=(2, 12), max_attempts: int = 2000):
        self.possible_fraction = possible_fraction
        self.n_numbers = n_numbers
        self.gcd_range = tuple(gcd_range)
        self.max_attempts = max_attempts

    # -- generation ------------------------------------------------------
    def _ground_truth(self, structure: dict) -> dict:
        g = db.board_gcd(structure["numbers"])
        if db.exact_reachable(structure):
            moves = db.witness_moves(structure)
            return {"answer": "possible", "proof_type": "explicit_construction", "witness": {"certificate_type": "explicit_construction", "differences": moves}, "gcd": g}
        t = structure["target"]
        proof = "gcd_invariant" if t % g != 0 else "other"  # 'other' = target exceeds the maximum
        return {"answer": "impossible", "proof_type": proof, "witness": None, "gcd": g}

    def generate_instance(self, size: int, seed: int, answer: Optional[str] = None, **kwargs) -> Instance:
        if size < 30:
            raise ValueError("size must be >= 30")
        rng = random.Random(derive_seed(self.family_id, self.version, size, seed))
        want_possible = (rng.random() < self.possible_fraction) if answer is None else (answer == "possible")
        for _ in range(self.max_attempts):
            g = rng.randint(*self.gcd_range)
            top = size // g
            if top < 4:
                continue
            multipliers = rng.sample(range(2, top + 1), self.n_numbers)
            numbers = sorted(g * m for m in multipliers)
            if db.board_gcd(numbers) != g:
                continue  # multipliers happened to share a factor; the invariant would be coarser than intended
            m = max(numbers)
            if want_possible:
                candidates = [x for x in range(g, m + 1, g) if x not in numbers]
            else:
                candidates = [x for x in range(1, m + 1) if x % g != 0]
            if not candidates:
                continue
            target = rng.choice(candidates)
            structure = db.make_structure(numbers, target)
            gt = self._ground_truth(structure)
            if (gt["answer"] == "possible") == want_possible and (want_possible or gt["proof_type"] == "gcd_invariant"):
                break
        else:  # pragma: no cover
            raise RuntimeError("could not generate instance")
        return Instance(
            instance_id=f"{self.family_id}-n{size}-s{seed}-d1",
            family_id=self.family_id,
            size=size,
            transfer_level=1,
            generation_seed=seed,
            structure=structure,
            parameters={"n_numbers": self.n_numbers, "gcd": g, "magnitude": size, **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=gt["answer"] == "impossible",
            surface={"type": SURFACES[1]},
            transfer={"level": 1, "source_family": self.family_id, "target_surface": SURFACES[1], "preserved_structure": "difference-closed set of integers; gcd invariant", "transformation": "seeded gcd and multipliers"},
            family_version=self.version,
        )

    def classical_instance(self) -> Instance:
        # Euclid's game with 36 and 60 (gcd 12): can 30 be written? No - 30 is not a multiple of 12.
        structure = db.make_structure([36, 60], 30)
        gt = self._ground_truth(structure)
        return Instance(
            instance_id=f"{self.family_id}-classical-euclid-d0",
            family_id=self.family_id,
            size=60,
            transfer_level=0,
            generation_seed=0,
            structure=structure,
            parameters={"n_numbers": 2, "gcd": 12, "magnitude": 60, "name": "Euclid's game", **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=True,
            surface={"type": SURFACES[0]},
            transfer={"level": 0, "source_family": self.family_id, "target_surface": SURFACES[0], "preserved_structure": "difference-closed set of integers; gcd invariant", "transformation": "none (classical seed problem, reachability question)"},
            source="classical",
            family_version=self.version,
        )

    def apply_surface(self, instance: Instance, transfer_level: int, seed: int) -> Instance:
        if transfer_level != 2:
            raise ValueError(f"{self.family_id} supports surface change only at level 2")
        return Instance(
            instance_id=instance.instance_id[: -len("-d1")] + "-d2" if instance.instance_id.endswith("-d1") else instance.instance_id + "-d2",
            family_id=self.family_id,
            size=instance.size,
            transfer_level=2,
            generation_seed=seed,
            structure=instance.structure,
            parameters=dict(instance.parameters),
            ground_truth=instance.ground_truth,
            idea_bearing=instance.idea_bearing,
            surface={"type": SURFACES[2], "unit": "cm"},
            transfer={
                "level": 2,
                "source_family": self.family_id,
                "source_instance_id": instance.instance_id,
                "target_surface": SURFACES[2],
                "preserved_structure": "difference-closed set of integers; gcd invariant",
                "transformation": "numbers -> rod lengths; writing a difference -> cutting a new rod to the difference of two existing lengths",
            },
            source=instance.source,
            family_version=self.version,
        )

    # -- rendering -------------------------------------------------------
    def render_problem(self, instance: Instance, format: str = "text") -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        s = instance.structure
        nums = ", ".join(str(x) for x in s["numbers"])
        t = s["target"]
        if surface == SURFACES[0]:
            base = seed_statement(SEED_ID) or "Two distinct positive integers are written on a board. Players alternate; a move writes down the positive difference of two numbers already on the board, provided that difference is not there yet."
            return f"{base}\n\nSuppose the two starting numbers are {nums}. Can the number {t} ever appear on the board, under any sequence of legal moves?"
        if surface == SURFACES[1]:
            return (
                f"The numbers {nums} are written on a board. A move chooses two numbers a and b that are already on the board and writes their positive "
                "difference |a - b| on the board, provided that this number is not on the board yet. Moves may be repeated as long as some new number can be written.\n\n"
                f"Is it possible that the number {t} is written on the board at some point?"
            )
        if surface == SURFACES[2]:
            unit = instance.surface.get("unit", "cm")
            rods = ", ".join(f"{x} {unit}" for x in s["numbers"])
            return (
                f"A workshop has rods of lengths {rods}. The only operation available is to lay a shorter rod against a longer one and cut a new rod whose length "
                "is exactly the difference of the two lengths; the new rod is added to the collection, provided that no rod of that length exists yet. "
                "The original rods are never destroyed and the operation may be repeated as long as it produces a new length.\n\n"
                f"Is it possible to obtain a rod of length {t} {unit}?"
            )
        raise ValueError(f"unknown surface {surface!r}")

    # -- mathematics -----------------------------------------------------
    def solve_ground_truth(self, instance: Instance) -> dict:
        return self._ground_truth(instance.structure)

    def canonical_idea(self, instance: Instance) -> CanonicalIdea:
        g = instance.ground_truth["gcd"]
        noun = "length" if instance.surface.get("type") == SURFACES[2] else "number"
        prose = (
            f"Every starting {noun} is a multiple of {g}, and the difference of two multiples of {g} is again a multiple of {g}. "
            f"So every {noun} that can ever be produced is a multiple of {g}. Check whether the target is a multiple of {g}."
        )
        return CanonicalIdea(prose, {"certificate_type": "gcd_invariant", "divisor": g}, "gcd_invariant", f"multiples of gcd {g}", prose)

    def alternative_idea(self, instance: Instance) -> Optional[CanonicalIdea]:
        g = instance.ground_truth["gcd"]
        t = instance.structure["target"]
        for d in range(2, g):
            if g % d == 0 and t % d != 0:
                prose = f"All the starting numbers are multiples of {d}, and differences of multiples of {d} are multiples of {d}; the target is not a multiple of {d}."
                return CanonicalIdea(prose, {"certificate_type": "gcd_invariant", "divisor": d}, "gcd_invariant", f"multiples of {d}", prose)
        return None

    def invalid_idea(self, instance: Instance) -> dict:
        g = instance.ground_truth["gcd"]
        return {"certificate_type": "gcd_invariant", "divisor": g + 1 if any(x % (g + 1) for x in instance.structure["numbers"]) else g + 2}

    def canonical_match(self, instance: Instance, normalized_certificate: dict) -> bool:
        return normalized_certificate.get("certificate_type") == "gcd_invariant" and normalized_certificate.get("divisor") == instance.ground_truth["gcd"]

    # -- structured-output schemas (conditions B and C only) ---------------
    def certificate_schema_text(self, instance: Instance) -> str:
        noun = "length" if instance.surface.get("type") == SURFACES[2] else "number"
        return (
            "Use exactly one of the following JSON schemas:\n"
            '{"certificate_type": "gcd_invariant", "divisor": <positive integer>}\n'
            f"  - the claim: every {noun} that can ever be produced is a multiple of the divisor, and the target is not.\n"
            '{"certificate_type": "explicit_construction", "differences": [[a, b], [c, d], ...]}  - pairs already present whose difference is produced, in order, ending with the target.\n'
            '{"certificate_type": "none"}  - if no such principle was used.'
        )

    # -- deterministic extraction ------------------------------------------
    _DIV_RE = re.compile(r"\b(?:multiples?\s+of|divisible\s+by|divides\s+(?:every|all|each)[^.\n]{0,20}?|gcd[^.\n]{0,30}?(?:=|is|equals)\s*|greatest\s+common\s+divisor[^.\n]{0,30}?(?:=|is|equals)\s*)\s*(\d+)", re.IGNORECASE)

    def extract_candidates(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        out: list[ExtractedCertificate] = []
        for hit in find_certificates(response):
            if hit.obj.get("certificate_type") in self.certificate_types:
                out.append(ExtractedCertificate(hit.obj, hit.text, hit.start, hit.end, "json_block", "json_block"))
        seen: set[int] = set()
        for m in self._DIV_RE.finditer(response):
            d = int(m.group(1))
            if d < 2 or d in seen:
                continue
            seen.add(d)
            s, e = _sentence_span(response, m.start(), m.end())
            out.append(ExtractedCertificate({"certificate_type": "gcd_invariant", "divisor": d}, response[s:e], s, e, "deterministic:divisibility_phrase", "divisibility_phrase"))
        return out

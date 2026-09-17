"""Heap games with a bounded take (seed: Nim, corpus id ``nim``).

Structure: ``subtraction_game`` (k heaps, remove 1..max_take from one heap,
last counter wins). Novel instances use a random ``max_take`` in 2..7, so the
classical nim-sum has to be *adapted* (XOR of the heap sizes modulo
max_take + 1); the classical d0 instance is plain Nim.

Canonical idea: the positions where XOR_i (h_i mod (max_take + 1)) == 0 are
exactly the losing positions. Ground truth uses this theorem (Bouton;
Sprague-Grundy), which tests confirm by exhaustive retrograde analysis; the
*verifier* never uses the theorem, it checks any proposed characterisation
exhaustively over the state box.

Every instance is idea-bearing: a correct characterisation decides both
answers ("first" / "second" player wins). There is no witness certificate -
a winning strategy is not a finite object a model can hand over.

This family is one where the idea *is* the algorithm (computing the nim-sum
leaves nothing to execute), so its size-scaling signature is expected to
differ from the tiling / population families; see the README.

Transfer surfaces:
    d0  classical Nim (heaps 3, 5, 7; any number of counters)
    d1  heaps of counters, remove 1..k
    d2  tokens on numbered tracks moving towards 0 by 1..k steps
"""
from __future__ import annotations

import random
import re
from typing import Optional

from ..extraction.json_block import find_certificates
from ..generation.seeds import seed_provenance, seed_statement
from ..structures import subtraction_game as sg
from ..utils.hashing import derive_seed
from .base import CanonicalIdea, ExtractedCertificate, Instance, ProblemFamily, register_family

SURFACES = {0: "classical_nim", 1: "heaps_bounded_take", 2: "tokens_on_tracks"}
SEED_ID = "nim"


def _sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    s = start
    while s > 0 and text[s - 1] not in ".!?\n":
        s -= 1
    e = end
    while e < len(text) and text[e] not in ".!?\n":
        e += 1
    return s, min(len(text), e + 1)


@register_family
class SubtractionGameFamily(ProblemFamily):
    family_id = "subtraction_game"
    idea_type = "xor_invariant"
    domain = "combinatorial game theory"
    size_parameter = "maximum heap size n (3 heaps; game tree ~ n^3 positions)"
    certificate_type = "xor_invariant"
    certificate_types = ("xor_invariant",)
    verification_method = "exhaustive"
    generation_method = "seeded heaps in [1, n] with random max_take in 2..7; theorem ground truth (confirmed by DP in tests); rejection sampling for the answer mix"
    answer_options = ("first", "second")
    supported_transfer_levels = (0, 1, 2)
    version = "0.1"

    def __init__(self, n_heaps: int = 3, second_fraction: float = 0.4, max_take_range=(2, 7), max_attempts: int = 1000):
        self.n_heaps = n_heaps
        self.second_fraction = second_fraction
        self.max_take_range = tuple(max_take_range)
        self.max_attempts = max_attempts

    # -- generation ------------------------------------------------------
    def _ground_truth(self, structure: dict) -> dict:
        first = sg.first_player_wins(structure)
        k = structure["max_take"]
        return {
            "answer": "first" if first else "second",
            "proof_type": "xor_invariant",
            "witness": None,
            "nim_value": [h if k is None else h % (k + 1) for h in structure["heaps"]],
            "winning_move": list(sg.winning_move(structure)) if first else None,
        }

    def generate_instance(self, size: int, seed: int, answer: Optional[str] = None, **kwargs) -> Instance:
        if size < 4:
            raise ValueError("size must be >= 4")
        rng = random.Random(derive_seed(self.family_id, self.version, size, seed))
        want_second = (rng.random() < self.second_fraction) if answer is None else (answer == "second")
        for _ in range(self.max_attempts):
            k = rng.randint(*self.max_take_range)
            heaps = [rng.randint(1, size) for _ in range(self.n_heaps)]
            if want_second:
                # force the last heap into the losing class: choose its residue so the xor vanishes
                x = 0
                for h in heaps[:-1]:
                    x ^= h % (k + 1)
                if x > k:
                    continue
                base = rng.randint(0, size // (k + 1))
                h = base * (k + 1) + x
                if not 1 <= h <= size:
                    continue
                heaps[-1] = h
            if max(heaps) > size or sg.n_states(sg.make_structure(heaps, k)) > 600_000:
                continue
            structure = sg.make_structure(heaps, k)
            gt = self._ground_truth(structure)
            if (gt["answer"] == "second") == want_second:
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
            parameters={"n_heaps": self.n_heaps, "max_take": k, "max_heap": size, **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=True,
            surface={"type": SURFACES[1]},
            transfer={"level": 1, "source_family": self.family_id, "target_surface": SURFACES[1], "preserved_structure": "impartial heap game; Sprague-Grundy / XOR characterisation", "transformation": "random heaps and bounded take"},
            family_version=self.version,
        )

    def classical_instance(self) -> Instance:
        structure = sg.make_structure([3, 5, 7], None)
        gt = self._ground_truth(structure)
        return Instance(
            instance_id=f"{self.family_id}-classical-nim-d0",
            family_id=self.family_id,
            size=7,
            transfer_level=0,
            generation_seed=0,
            structure=structure,
            parameters={"n_heaps": 3, "max_take": None, "max_heap": 7, "name": "Nim", **seed_provenance(SEED_ID)},
            ground_truth=gt,
            idea_bearing=True,
            surface={"type": SURFACES[0]},
            transfer={"level": 0, "source_family": self.family_id, "target_surface": SURFACES[0], "preserved_structure": "impartial heap game; XOR characterisation", "transformation": "none (classical seed problem)"},
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
            idea_bearing=True,
            surface={"type": SURFACES[2]},
            transfer={
                "level": 2,
                "source_family": self.family_id,
                "source_instance_id": instance.instance_id,
                "target_surface": SURFACES[2],
                "preserved_structure": "impartial heap game; XOR characterisation",
                "transformation": "heap size -> position of a token on a track numbered from 0; removing counters -> moving the token towards 0",
            },
            source=instance.source,
            family_version=self.version,
        )

    # -- rendering -------------------------------------------------------
    def render_problem(self, instance: Instance, format: str = "text") -> str:
        surface = instance.surface.get("type", SURFACES[instance.transfer_level])
        s = instance.structure
        heaps, k = s["heaps"], s["max_take"]
        if surface == SURFACES[0]:
            base = seed_statement(SEED_ID) or "Several heaps of counters are on the table. A move removes any positive number of counters from a single heap. The player who takes the last counter wins."
            return (
                f"{base}\n\nThe heaps contain {', '.join(str(h) for h in heaps)} counters. Two players alternate moves. "
                "Does the player who moves first have a winning strategy, or does the second player?"
            )
        if surface == SURFACES[1]:
            return (
                f"There are {len(heaps)} heaps of counters containing {', '.join(str(h) for h in heaps)} counters respectively. Two players alternate moves. "
                f"A move consists of choosing one heap and removing at least 1 and at most {k} counters from it. The player who removes the last counter wins.\n\n"
                "Does the player who moves first have a winning strategy, or does the second player?"
            )
        if surface == SURFACES[2]:
            tracks = "; ".join(f"track {i + 1}: token at position {h}" for i, h in enumerate(heaps))
            return (
                f"There are {len(heaps)} tracks, each a row of squares numbered 0, 1, 2, ... from left to right, and one token on each track ({tracks}). "
                f"Two players alternate moves. A move consists of choosing one token and moving it between 1 and {k} squares to the left (towards square 0); "
                "a token on square 0 can no longer move. The player who makes the last possible move wins.\n\n"
                "Does the player who moves first have a winning strategy, or does the second player?"
            )
        raise ValueError(f"unknown surface {surface!r}")

    # -- mathematics -----------------------------------------------------
    def solve_ground_truth(self, instance: Instance) -> dict:
        return self._ground_truth(instance.structure)

    def _canonical_expr(self, structure: dict) -> str:
        k = structure["max_take"]
        names = [f"h{i + 1}" for i in range(len(structure["heaps"]))]
        if k is None:
            return "xor(" + ", ".join(names) + ")"
        return "xor(" + ", ".join(f"{n} % {k + 1}" for n in names) + ")"

    def canonical_idea(self, instance: Instance) -> CanonicalIdea:
        s = instance.structure
        k = s["max_take"]
        noun = "position of each token" if instance.surface.get("type") == SURFACES[2] else "size of each heap"
        if k is None:
            prose = (
                "Write the size of each heap in binary and add the binary digits column by column without carrying (bitwise XOR / nim-sum). "
                "From a position with nim-sum 0 every move produces a nonzero nim-sum, and from a nonzero nim-sum some move restores 0. "
                "Since the empty position has nim-sum 0, the player to move loses exactly when the nim-sum is 0."
            )
        else:
            prose = (
                f"Replace the {noun} by its remainder on division by {k + 1} (a move changes one remainder to any other value, cyclically), "
                "write these remainders in binary and add them column by column without carrying (bitwise XOR). From a position with XOR 0 every "
                "move produces a nonzero XOR, and from a nonzero XOR some move restores 0. Since the final position has XOR 0, the player to move "
                "loses exactly when this XOR is 0."
            )
        return CanonicalIdea(prose, {"certificate_type": "xor_invariant", "losing_expr": self._canonical_expr(s)}, "xor_invariant", "nim-sum of remainders", prose)

    def alternative_idea(self, instance: Instance) -> Optional[CanonicalIdea]:
        s = instance.structure
        k = s["max_take"]
        if k is None or k != 1:
            return None
        # with max_take 1 the game is decided by the parity of the total: an equivalent, differently expressed characterisation
        prose = "Each move removes exactly one counter, so the total number of counters decreases by one per move; the player to move loses exactly when the total is even."
        return CanonicalIdea(prose, {"certificate_type": "xor_invariant", "losing_expr": "(" + " + ".join(f"h{i + 1}" for i in range(len(s["heaps"]))) + ") % 2"}, "xor_invariant", "total parity", prose)

    def invalid_idea(self, instance: Instance) -> dict:
        names = [f"h{i + 1}" for i in range(len(instance.structure["heaps"]))]
        return {"certificate_type": "xor_invariant", "losing_expr": "(" + " + ".join(names) + ") % 2"}

    def canonical_match(self, instance: Instance, normalized_certificate: dict) -> bool:
        if normalized_certificate.get("certificate_type") != "xor_invariant":
            return False
        from ..verifiers.xor_invariant import XorInvariantVerifier

        s = instance.structure
        ver = XorInvariantVerifier()
        canon = {"losing_expr": self._canonical_expr(s)}
        k = s["max_take"] or 0
        if sg.n_states(s) > 300_000:
            return False
        try:
            return all((ver._value(normalized_certificate, st, k) == 0) == (ver._value(canon, st, k) == 0) for st in sg.states(s))
        except Exception:  # noqa: BLE001
            return False

    # -- structured-output schemas (conditions B and C only) ---------------
    def certificate_schema_text(self, instance: Instance) -> str:
        n = len(instance.structure["heaps"])
        names = ", ".join(f"h{i + 1}" for i in range(n))
        noun = "token positions" if instance.surface.get("type") == SURFACES[2] else "heap sizes"
        return (
            "Use exactly one of the following JSON schemas:\n"
            '{"certificate_type": "xor_invariant", "losing_expr": "<expression in the ' + noun + f" {names} that equals 0 exactly at the positions where the player to move loses>\"}}\n"
            "  - allowed: + - * // % and parentheses, ^ or xor(...) for bitwise XOR, e.g. \"xor(h1 % 3, h2 % 3, h3 % 3)\" or \"h1 ^ h2 ^ h3\".\n"
            "    The claim: from any position where the expression is 0 every move makes it nonzero, from any position where it is nonzero\n"
            "    some move makes it 0, and it is 0 at the terminal position.\n"
            '{"certificate_type": "none"}  - if no such principle was used.'
        )

    # -- deterministic extraction ------------------------------------------
    _XOR_RE = re.compile(r"\b(nim[- ]?sum|xor|exclusive[- ]or|bitwise\s+sum|binary\s+digital\s+sum|sum\s+without\s+carr\w+)\b", re.IGNORECASE)
    _MOD_RE = re.compile(r"\b(remainders?|residues?|mod(?:ulo)?)\b[^.\n]{0,30}?\b(\d+)\b|\b(\d+)\b[^.\n]{0,10}\b(remainders?|residues?)", re.IGNORECASE)

    def extract_candidates(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        out: list[ExtractedCertificate] = []
        for hit in find_certificates(response):
            if hit.obj.get("certificate_type") in self.certificate_types:
                out.append(ExtractedCertificate(hit.obj, hit.text, hit.start, hit.end, "json_block", "json_block"))
        s = instance.structure
        names = [f"h{i + 1}" for i in range(len(s["heaps"]))]
        m = self._XOR_RE.search(response)
        if not m:
            return out
        start, end = _sentence_span(response, m.start(), m.end())
        window = response[max(0, start - 200) : end + 200]
        moduli = []
        for mm in self._MOD_RE.finditer(window):
            val = mm.group(2) or mm.group(3)
            if val:
                moduli.append(int(val))
        if moduli:
            mod = moduli[0]
            expr = "xor(" + ", ".join(f"{n} % {mod}" for n in names) + ")"
            rule = "xor_of_remainders"
        else:
            expr = "xor(" + ", ".join(names) + ")"
            rule = "plain_xor"
        out.append(ExtractedCertificate({"certificate_type": "xor_invariant", "losing_expr": expr}, response[start:end], start, end, f"deterministic:{rule}", rule))
        return out

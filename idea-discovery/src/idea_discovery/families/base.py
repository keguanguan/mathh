"""ProblemFamily interface and the Instance record.

A family owns the mathematics: instance generation, ground truth, rendering
at each transfer level, the canonical idea (prose + certificate) and the
deterministic idea extractors for its certificate types. It never talks to a
model; model-running code lives in ``evaluation/``.

Transfer levels (see README):
    d0  classical / familiar presentation of the seed problem
    d1  novel generated instance, same representation
    d2  changed surface representation (same abstract structure)
    d3  different problem domain, same underlying structure
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from ..utils.hashing import stable_hash
from ..verifiers.base import VerificationResult, get_verifier

TRANSFER_LEVELS = {
    0: "classical presentation",
    1: "novel instance, same representation",
    2: "changed surface representation",
    3: "different problem domain, same structure",
}


@dataclass
class Instance:
    instance_id: str
    family_id: str
    size: int
    transfer_level: int
    generation_seed: int
    structure: dict  # abstract mathematical structure (see structures/)
    parameters: dict  # family-specific presentation parameters
    ground_truth: dict  # {"answer": ..., "proof_type": ..., "witness": ..., ...}
    idea_bearing: bool  # True when the canonical idea *proves* the answer
    surface: dict = field(default_factory=dict)  # surface-specific data (labels, names)
    transfer: Optional[dict] = None  # explicit transformation record
    source: str = "generated"
    family_version: str = "0"

    def content_hash(self) -> str:
        return stable_hash({"structure": self.structure, "surface": self.surface, "transfer_level": self.transfer_level})

    def to_dict(self) -> dict:
        from ..utils.serialization import to_jsonable

        d = to_jsonable(self)
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Instance":
        d = dict(d)
        d.pop("content_hash", None)
        return cls(**d)


@dataclass
class CanonicalIdea:
    prose: str  # idea in words, used for the supplied-idea baseline
    certificate: dict  # machine-checkable certificate
    certificate_type: str
    name: str = ""
    explicit_prose: Optional[str] = None  # prose incl. explicit data (e.g. listed vertex classes); mock model uses it


@dataclass
class ExtractedCertificate:
    certificate: dict
    supporting_span: str
    span_start: int
    span_end: int
    extraction_method: str  # e.g. "deterministic:checkerboard_phrase" or "json_block"
    rule_id: str = ""


class ProblemFamily(ABC):
    # -- metadata (see configs/families/*.yaml for the same fields) --------
    family_id: ClassVar[str]
    idea_type: ClassVar[str]
    domain: ClassVar[str]
    size_parameter: ClassVar[str]
    certificate_type: ClassVar[str]  # canonical certificate type
    certificate_types: ClassVar[tuple[str, ...]]  # all accepted types (incl. witnesses)
    verification_method: ClassVar[str]
    generation_method: ClassVar[str]
    answer_options: ClassVar[tuple[str, ...]] = ("possible", "impossible")
    supported_transfer_levels: ClassVar[tuple[int, ...]] = (0, 1, 2)
    version: ClassVar[str] = "0.1"

    # -- generation ------------------------------------------------------
    @abstractmethod
    def generate_instance(self, size: int, seed: int, **kwargs) -> Instance:
        """Deterministically generate a novel (d1) instance."""

    @abstractmethod
    def classical_instance(self) -> Instance:
        """The familiar seed problem (d0)."""

    @abstractmethod
    def apply_surface(self, instance: Instance, transfer_level: int, seed: int) -> Instance:
        """Re-present an instance at a higher transfer level, preserving its structure."""

    def generate_transfer_instance(self, transfer_level: int, seed: int, size: Optional[int] = None, **kwargs) -> Instance:
        if transfer_level not in self.supported_transfer_levels:
            raise ValueError(f"{self.family_id} does not support transfer level {transfer_level}")
        if transfer_level == 0:
            return self.classical_instance()
        if size is None:
            raise ValueError("size is required for transfer levels >= 1")
        base = self.generate_instance(size, seed, **kwargs)
        if transfer_level == 1:
            return base
        return self.apply_surface(base, transfer_level, seed)

    # -- mathematics -----------------------------------------------------
    @abstractmethod
    def render_problem(self, instance: Instance, format: str = "text") -> str:
        """Problem statement only. Must not mention the intended idea class."""

    @abstractmethod
    def solve_ground_truth(self, instance: Instance) -> dict:
        """Recompute ground truth from the structure (used by sanity checks)."""

    @abstractmethod
    def canonical_idea(self, instance: Instance) -> CanonicalIdea:
        """The governing idea as prose (for condition C) and as a certificate."""

    def alternative_idea(self, instance: Instance) -> Optional[CanonicalIdea]:
        """A valid, non-canonical certificate if one exists (used by the mock model)."""
        return None

    def invalid_idea(self, instance: Instance) -> dict:
        """A plausible-looking but structurally invalid certificate (used by the mock model)."""
        raise NotImplementedError

    @abstractmethod
    def canonical_match(self, instance: Instance, normalized_certificate: dict) -> bool:
        """Whether a (verified) certificate is equivalent to the canonical one."""

    @abstractmethod
    def certificate_schema_text(self, instance: Instance) -> str:
        """Human-readable JSON schema for the certificate types accepted at this surface
        (used only in the post-hoc and supplied-idea conditions, never in free solve)."""

    @abstractmethod
    def extract_candidates(self, instance: Instance, response: str) -> list[ExtractedCertificate]:
        """Deterministic extraction of candidate certificates from a free response."""

    # -- answers ---------------------------------------------------------
    def answer_instruction(self) -> str:
        opts = ", ".join(self.answer_options)
        return f"End your response with a single line of the form\nFINAL ANSWER: <answer>\nwhere <answer> is one of: {opts}."

    def check_answer(self, instance: Instance, parsed_answer: Optional[str]) -> Optional[bool]:
        """True/False for a parsed answer, None when no answer could be parsed."""
        if parsed_answer is None:
            return None
        return parsed_answer == instance.ground_truth["answer"]

    # -- verification ----------------------------------------------------
    def verifier(self):
        return get_verifier(self.certificate_type)

    def verify(self, instance: Instance, certificate: dict) -> VerificationResult:
        from ..verifiers.base import verify_certificate

        return verify_certificate(instance, certificate)

    def sanity_check(self, instance: Instance) -> list[str]:
        """Return a list of problems (empty if the instance is consistent)."""
        problems = []
        recomputed = self.solve_ground_truth(instance)
        if recomputed["answer"] != instance.ground_truth["answer"]:
            problems.append(f"stored answer {instance.ground_truth['answer']} != recomputed {recomputed['answer']}")
        idea = self.canonical_idea(instance)
        result = self.verify(instance, idea.certificate)
        if instance.idea_bearing and not result.valid:
            problems.append(f"canonical certificate invalid on idea-bearing instance: {result.failure_reason}")
        if not instance.idea_bearing and result.valid:
            problems.append("canonical certificate valid on an instance marked not idea-bearing")
        if not result.structural_valid:
            problems.append(f"canonical certificate structurally invalid: {result.failure_reason}")
        witness = instance.ground_truth.get("witness")
        if witness is not None:
            wres = self.verify(instance, witness)
            if not wres.valid:
                problems.append(f"stored witness does not verify: {wres.failure_reason}")
        return problems

    def metadata(self) -> dict:
        return {
            "family_id": self.family_id,
            "idea_type": self.idea_type,
            "domain": self.domain,
            "size_parameter": self.size_parameter,
            "certificate_type": self.certificate_type,
            "certificate_types": list(self.certificate_types),
            "verification_method": self.verification_method,
            "generation_method": self.generation_method,
            "answer_options": list(self.answer_options),
            "supported_transfer_levels": list(self.supported_transfer_levels),
            "version": self.version,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_FAMILIES: dict[str, type[ProblemFamily]] = {}


def register_family(cls):
    _FAMILIES[cls.family_id] = cls
    return cls


def get_family(family_id: str, **kwargs: Any) -> ProblemFamily:
    if family_id not in _FAMILIES:
        raise KeyError(f"unknown family {family_id!r}; available: {sorted(_FAMILIES)}")
    return _FAMILIES[family_id](**kwargs)


def available_families() -> list[str]:
    return sorted(_FAMILIES)

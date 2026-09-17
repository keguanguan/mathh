"""Common verifier interface.

A certificate is a plain dict with a ``certificate_type`` key. A verifier
normalizes it against an instance, checks *structural validity* (the claimed
law holds under the legal moves) and *decision relevance* (the law actually
separates the initial state from the target / establishes the answer).

    valid idea = structural law + task discrimination

The verifier is deterministic and never consults the model's prose.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

VERIFICATION_METHODS = ("local_rule", "symbolic", "exhaustive", "sampled")


class CertificateError(ValueError):
    """Certificate is malformed or cannot be interpreted for this instance."""


@dataclass
class StepResult:
    ok: bool
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)
    method: Optional[str] = None  # override of the verifier default
    exact: Optional[bool] = None


@dataclass
class VerificationResult:
    valid: bool
    structural_valid: bool
    decision_relevant: bool
    failure_reason: Optional[str] = None
    details: dict = field(default_factory=dict)
    verifier: str = ""
    certificate_type: str = ""
    method: str = ""
    exact: bool = True
    is_idea: bool = True  # False for witness-type certificates (explicit constructions)
    normalized_certificate: Optional[dict] = None

    def to_dict(self) -> dict:
        from ..utils.serialization import to_jsonable

        return to_jsonable(self)


class Verifier(ABC):
    certificate_type: ClassVar[str]
    method: ClassVar[str] = "local_rule"
    exact: ClassVar[bool] = True
    is_idea: ClassVar[bool] = True
    supported_structures: ClassVar[tuple[str, ...]] = ()

    # -- interface -------------------------------------------------------
    @abstractmethod
    def normalize(self, instance, certificate: dict) -> dict:
        """Return a canonical dict form of the certificate; raise CertificateError if malformed."""

    @abstractmethod
    def verify_structure(self, instance, certificate: dict) -> StepResult:
        """Check the claimed mathematical law under every legal move / placement."""

    @abstractmethod
    def verify_relevance(self, instance, certificate: dict) -> StepResult:
        """Check that the law establishes the instance's answer."""

    # -- driver ----------------------------------------------------------
    def verify(self, instance, certificate: dict) -> VerificationResult:
        name = type(self).__name__
        base = dict(verifier=name, certificate_type=self.certificate_type, method=self.method, exact=self.exact, is_idea=self.is_idea)
        structure_kind = instance.structure.get("kind")
        if self.supported_structures and structure_kind not in self.supported_structures:
            return VerificationResult(False, False, False, f"verifier {name} does not support structure kind {structure_kind!r}", **base)
        try:
            cert = self.normalize(instance, certificate)
        except CertificateError as e:
            return VerificationResult(False, False, False, f"malformed certificate: {e}", **base)
        except Exception as e:  # noqa: BLE001 - never let a bad certificate crash a run
            return VerificationResult(False, False, False, f"malformed certificate ({type(e).__name__}): {e}", **base)
        s = self.verify_structure(instance, cert)
        details: dict[str, Any] = {"structure": s.details}
        if s.method is not None:
            base["method"] = s.method
        if s.exact is not None:
            base["exact"] = s.exact
        if not s.ok:
            return VerificationResult(False, False, False, f"structural failure: {s.reason}", details, normalized_certificate=cert, **base)
        r = self.verify_relevance(instance, cert)
        details["relevance"] = r.details
        if not r.ok:
            return VerificationResult(False, True, False, f"not decision-relevant: {r.reason}", details, normalized_certificate=cert, **base)
        return VerificationResult(True, True, True, None, details, normalized_certificate=cert, **base)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, Verifier] = {}


def register_verifier(cls):
    """Class decorator registering a verifier instance under its certificate_type."""
    _REGISTRY[cls.certificate_type] = cls()
    return cls


def get_verifier(certificate_type: str) -> Verifier:
    if certificate_type not in _REGISTRY:
        raise KeyError(f"no verifier registered for certificate type {certificate_type!r}")
    return _REGISTRY[certificate_type]


def available_certificate_types() -> list[str]:
    return sorted(_REGISTRY)


def verify_certificate(instance, certificate: Any) -> VerificationResult:
    """Dispatch on ``certificate['certificate_type']``. Never raises."""
    if not isinstance(certificate, dict):
        return VerificationResult(False, False, False, "certificate is not a JSON object", verifier="dispatch", certificate_type="", method="none", exact=False)
    ctype = certificate.get("certificate_type")
    if not isinstance(ctype, str) or not ctype:
        return VerificationResult(False, False, False, "certificate has no 'certificate_type'", verifier="dispatch", certificate_type="", method="none", exact=False)
    if ctype == "none":
        return VerificationResult(False, False, False, "no certificate stated", verifier="dispatch", certificate_type="none", method="none", exact=False)
    if ctype not in _REGISTRY:
        return VerificationResult(False, False, False, f"unsupported certificate type {ctype!r}", {"supported": False}, verifier="dispatch", certificate_type=ctype, method="none", exact=False)
    return _REGISTRY[ctype].verify(instance, certificate)

"""Deterministic certificate verifiers.

Importing this package registers all built-in verifiers. Use
:func:`verify_certificate` to dispatch on ``certificate_type``.
"""
from . import coloring_invariant, explicit_construction, gcd_invariant, modular_invariant, permutation_parity, xor_invariant  # noqa: F401  (registration)
from .base import (
    CertificateError,
    StepResult,
    VerificationResult,
    Verifier,
    available_certificate_types,
    get_verifier,
    register_verifier,
    verify_certificate,
)

__all__ = [
    "CertificateError",
    "StepResult",
    "VerificationResult",
    "Verifier",
    "available_certificate_types",
    "get_verifier",
    "register_verifier",
    "verify_certificate",
]

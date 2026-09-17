"""Candidate extraction + verification for free responses.

    free response -> candidate extraction -> structured certificates
                  -> deterministic verifier -> idea_valid in {0, 1}

The response is never modified. Every candidate keeps its provenance
(extraction method, rule id, supporting span). The *verifier* decides
validity; the extractor only proposes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import re

from ..families.base import ExtractedCertificate, Instance, ProblemFamily
from ..utils.serialization import canonical_json
from ..verifiers.base import VerificationResult, verify_certificate

# LaTeX / markdown forms that real responses use around the phrases the family
# extractors look for (pilot finding, 2026-09-17: "$r+c$ is even" and
# "$b \bmod 3$" were missed because of the delimiters). The normalized text is
# only a second view for extraction; the stored response is never altered.
_TEX_SUBS: list[tuple[re.Pattern, object]] = [
    (re.compile(r"\\(?:pmod|bmod)\s*\{([^{}]*)\}"), r" mod \1 "),
    (re.compile(r"\\(?:pmod|bmod)\s+"), " mod "),
    (re.compile(r"\\(?:text|textbf|textit|mathrm|mathbf|operatorname|mathit)\s*\{([^{}]*)\}"), r"\1"),
    (re.compile(r"\\(?:left|right|displaystyle|quad|qquad)(?![a-zA-Z])|\\[,;! ]"), " "),
    (re.compile(r"\\(?:cdot|times)(?![a-zA-Z])"), " * "),
    (re.compile(r"\\oplus(?![a-zA-Z])"), " xor "),
    (re.compile(r"\\equiv(?![a-zA-Z])"), " = "),
    (re.compile(r"\\(?:ne|neq)(?![a-zA-Z])"), " != "),
    (re.compile(r"\\(?:le|leq|ge|geq)(?![a-zA-Z])"), " <= "),
    (re.compile(r"\\([_{}])"), r"\1"),
    (re.compile(r"\$\$|\$|\\\(|\\\)|\\\[|\\\]"), " "),
    (re.compile(r"\*\*"), ""),
    (re.compile(r"[ \t]{2,}"), " "),
]


def normalize_math_text(text: str) -> str:
    """Strip LaTeX delimiters / common macros and markdown bold so phrase extractors see plain text."""
    for pat, rep in _TEX_SUBS:
        text = pat.sub(rep, text)
    return text


@dataclass
class IdeaExtractionResult:
    candidates: list[dict] = field(default_factory=list)  # each: certificate, provenance, verification
    idea_present: bool = False  # some candidate certificate was extracted
    idea_valid: bool = False  # some *idea-type* candidate verified (structure + relevance)
    witness_valid: bool = False  # some explicit construction verified (not an idea)
    selected: Optional[dict] = None  # the first valid idea candidate (or first valid witness)
    canonical_match: Optional[bool] = None
    extraction_method: str = "deterministic"

    def to_dict(self) -> dict:
        from ..utils.serialization import to_jsonable

        return to_jsonable(self)


def extract_and_verify(family: ProblemFamily, instance: Instance, response: str, extra_candidates: Optional[list[ExtractedCertificate]] = None, extraction_method: str = "deterministic") -> IdeaExtractionResult:
    candidates = list(family.extract_candidates(instance, response))
    normalized = normalize_math_text(response)
    if normalized != response:
        seen = {canonical_json(c.certificate) for c in candidates}
        for cand in family.extract_candidates(instance, normalized):
            if canonical_json(cand.certificate) not in seen:
                seen.add(canonical_json(cand.certificate))
                cand.extraction_method = cand.extraction_method + "+tex_normalized"
                candidates.append(cand)
    candidates += list(extra_candidates or [])
    result = IdeaExtractionResult(extraction_method=extraction_method)
    for cand in candidates:
        ver: VerificationResult = verify_certificate(instance, cand.certificate)
        entry = {
            "certificate": cand.certificate,
            "supporting_span": cand.supporting_span,
            "span_start": cand.span_start,
            "span_end": cand.span_end,
            "extraction_method": cand.extraction_method,
            "rule_id": cand.rule_id,
            "verification": ver.to_dict(),
        }
        if ver.valid and ver.normalized_certificate is not None:
            entry["canonical_match"] = family.canonical_match(instance, ver.normalized_certificate)
        result.candidates.append(entry)
        result.idea_present = True
        if ver.valid and ver.is_idea and not result.idea_valid:
            result.idea_valid = True
            result.selected = entry
            result.canonical_match = entry.get("canonical_match")
        elif ver.valid and not ver.is_idea:
            result.witness_valid = True
            if result.selected is None:
                result.selected = entry
    return result

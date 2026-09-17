"""Optional LLM-assisted candidate extraction (secondary; off by default).

The extractor model is asked to convert a free response into certificate
JSON *and* to quote, verbatim, the span of the response that supports every
field. Every quoted span is checked to be a substring of the original
response; candidates with unsupported fields are discarded. Validity is
still decided only by the deterministic verifier.
"""
from __future__ import annotations

from typing import Optional

from ..families.base import ExtractedCertificate, Instance, ProblemFamily
from ..models.base import GenerationConfig, ModelRunner
from .json_block import find_json_objects

_EXTRACTION_TEMPLATE = """You are converting a written mathematical solution into a structured certificate. Do not add any mathematical content that the solution does not state.

PROBLEM:
{problem}

SOLUTION (verbatim):
<<<
{response}
>>>

{schema}

Output a JSON object of the form
{{"certificate": <one certificate object using the schemas above, or {{"certificate_type": "none"}}>,
  "evidence": {{"<field name>": "<verbatim quote from the solution supporting this field>", ...}}}}
Every field of the certificate must have a verbatim quote in "evidence". Output exactly one JSON object inside a ```json code block."""


class LLMExtractor:
    def __init__(self, runner: ModelRunner, config: Optional[GenerationConfig] = None):
        self.runner = runner
        self.config = config or GenerationConfig(temperature=0.0, max_output_tokens=2048)

    def extract(self, family: ProblemFamily, instance: Instance, response: str) -> tuple[list[ExtractedCertificate], dict]:
        prompt = _EXTRACTION_TEMPLATE.format(problem=family.render_problem(instance), response=response, schema=family.certificate_schema_text(instance))
        out = self.runner.generate(prompt, self.config, context={"instance": instance, "family": family, "condition": "extraction"})
        provenance = {"extractor_model": self.runner.describe(), "extractor_prompt": prompt, "extractor_response": out.text}
        return validate_llm_extraction(out.text, response), provenance


def validate_llm_extraction(extractor_output: str, response: str) -> list[ExtractedCertificate]:
    """Keep only certificates whose every field is supported by a verbatim quote."""
    candidates: list[ExtractedCertificate] = []
    for hit in find_json_objects(extractor_output):
        cert = hit.obj.get("certificate")
        evidence = hit.obj.get("evidence")
        if not isinstance(cert, dict) or not isinstance(evidence, dict):
            continue
        if cert.get("certificate_type") in (None, "none"):
            continue
        fields = [k for k in cert if k != "certificate_type"]
        quotes = []
        supported = True
        for f in fields:
            q = evidence.get(f)
            if not isinstance(q, str) or not q.strip() or q not in response:
                supported = False
                break
            quotes.append(q)
        if not supported or not quotes:
            continue
        first = min(quotes, key=lambda q: response.index(q))
        start = response.index(first)
        candidates.append(ExtractedCertificate(cert, " | ".join(quotes), start, start + len(first), "llm_extractor", "llm_quoted_spans"))
    return candidates

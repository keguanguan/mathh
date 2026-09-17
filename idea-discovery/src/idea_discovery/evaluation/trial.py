"""One trial = one instance x one model x one compute condition x one repetition.

``run_trial`` executes the protocol conditions in separate model calls and
returns the raw trial record (schema below). Raw responses are stored
verbatim; parsed/extracted objects are stored alongside, never in place of
them.

Record schema (keys):
    trial_id, instance, model, free_solve, idea_extraction, verification,
    posthoc_formalization, supplied_idea_baseline, retrieval_control, metadata
"""
from __future__ import annotations

import json
from typing import Optional

from ..extraction.candidates import extract_and_verify
from ..extraction.json_block import find_json_objects, parse_structured_response
from ..families.base import Instance, ProblemFamily
from ..models.base import ComputeCondition, GenerationConfig, ModelRunner, utc_now
from ..prompting.answers import parse_final_answer
from ..prompting.protocol import free_solve_prompt, posthoc_prompt, recognition_prompt, supplied_idea_prompt
from ..verifiers.base import verify_certificate

CONDITION_KEYS = ("free_solve", "posthoc", "supplied_idea", "recognition")


def make_trial_id(experiment_id: str, model_name: str, compute_name: str, instance_id: str, repetition: int) -> str:
    return f"{experiment_id}__{model_name}__{compute_name}__{instance_id}__r{repetition}"


def _structured_certificate_block(family: ProblemFamily, instance: Instance, response_text: str) -> dict:
    """Parse + verify a structured (post-hoc / supplied-idea) response."""
    cert, parse_error = parse_structured_response(response_text)
    block = {"certificate": cert, "parse_error": parse_error, "valid": False, "verification": None, "canonical_match": None, "stated_none": False}
    if cert is None:
        return block
    if cert.get("certificate_type") == "none":
        block["stated_none"] = True
        return block
    ver = verify_certificate(instance, cert)
    block["verification"] = ver.to_dict()
    block["valid"] = bool(ver.valid and ver.is_idea)
    block["witness_valid"] = bool(ver.valid and not ver.is_idea)
    if ver.valid and ver.normalized_certificate is not None:
        block["canonical_match"] = family.canonical_match(instance, ver.normalized_certificate)
    return block


def _parse_recognition(text: str) -> dict:
    for hit in find_json_objects(text):
        if "recognized" in hit.obj:
            rec = hit.obj
            return {
                "recognized": bool(rec.get("recognized")),
                "proposed_name": rec.get("proposed_name"),
                "proposed_source": rec.get("proposed_source"),
                "confidence": rec.get("confidence"),
                "parse_error": None,
            }
    return {"recognized": None, "proposed_name": None, "proposed_source": None, "confidence": None, "parse_error": "no recognition JSON found"}


def run_trial(
    family: ProblemFamily,
    instance: Instance,
    runner: ModelRunner,
    base_config: GenerationConfig,
    compute: Optional[ComputeCondition],
    conditions: dict[str, bool],
    repetition: int = 0,
    experiment_id: str = "adhoc",
    model_name: Optional[str] = None,
    render_format: str = "text",
    extra_metadata: Optional[dict] = None,
) -> dict:
    model_name = model_name or runner.model
    compute_name = compute.name if compute is not None else "default"
    config = runner.resolve_config(base_config, compute)
    context_base = {"instance": instance, "family": family, "repetition": repetition, "compute_condition": compute}
    trial_id = make_trial_id(experiment_id, model_name, compute_name, instance.instance_id, repetition)
    record: dict = {
        "trial_id": trial_id,
        "instance": {
            "instance_id": instance.instance_id,
            "family_id": instance.family_id,
            "size": instance.size,
            "transfer_level": instance.transfer_level,
            "idea_bearing": instance.idea_bearing,
            "ground_truth_answer": instance.ground_truth["answer"],
            "content_hash": instance.content_hash(),
            "transfer": instance.transfer,
        },
        "model": {
            "provider": runner.provider,
            "model": runner.model,
            "model_name": model_name,
            "compute_condition": compute.to_dict() if compute else None,
            "generation_config": config.to_dict(),
            "runner": runner.describe(),
        },
        "repetition": repetition,
        "free_solve": None,
        "idea_extraction": None,
        "verification": None,
        "posthoc_formalization": None,
        "supplied_idea_baseline": None,
        "retrieval_control": None,
        "metadata": {"timestamp_start": utc_now(), **(extra_metadata or {})},
    }

    # -- Condition A: free solve --------------------------------------------
    free_text = None
    if conditions.get("free_solve", True):
        prompt = free_solve_prompt(family, instance, render_format)
        cfg = GenerationConfig(**{**config.__dict__, "system": prompt.system})
        resp = runner.generate(prompt.text, cfg, context={**context_base, "condition": "free_solve"})
        free_text = resp.text
        parsed = parse_final_answer(resp.text, family.answer_options)
        record["free_solve"] = {
            "prompt": prompt.text,
            "system": prompt.system,
            "response": resp.text,
            "response_meta": {k: v for k, v in resp.to_dict().items() if k != "text"},
            "parsed_answer": parsed.__dict__,
            "answer_correct": family.check_answer(instance, parsed.parsed),
        }
        extraction = extract_and_verify(family, instance, resp.text)
        ex = extraction.to_dict()
        record["idea_extraction"] = {
            "idea_present": extraction.idea_present,
            "idea_valid": extraction.idea_valid,
            "witness_valid": extraction.witness_valid,
            "canonical_match": extraction.canonical_match,
            "supporting_span": extraction.selected["supporting_span"] if extraction.selected else None,
            "extracted_certificate": extraction.selected["certificate"] if extraction.selected else None,
            "extraction_method": extraction.selected["extraction_method"] if extraction.selected else extraction.extraction_method,
            "candidates": ex["candidates"],
        }
        sel_ver = extraction.selected["verification"] if extraction.selected else None
        record["verification"] = {
            "structural_valid": sel_ver["structural_valid"] if sel_ver else None,
            "decision_relevant": sel_ver["decision_relevant"] if sel_ver else None,
            "valid": extraction.idea_valid,
            "verifier": sel_ver["verifier"] if sel_ver else None,
            "method": sel_ver["method"] if sel_ver else None,
            "exact": sel_ver["exact"] if sel_ver else None,
            "certificate_type": sel_ver["certificate_type"] if sel_ver else None,
            "details": sel_ver["details"] if sel_ver else None,
            "failure_reason": sel_ver["failure_reason"] if sel_ver else ("no candidate certificate extracted" if not extraction.candidates else None),
        }

    # -- Condition B: post-hoc formalization (separate call, free response quoted verbatim) --
    if conditions.get("posthoc", True) and free_text is not None:
        prompt = posthoc_prompt(family, instance, free_text, render_format)
        cfg = GenerationConfig(**{**config.__dict__, "system": prompt.system})
        resp = runner.generate(prompt.text, cfg, context={**context_base, "condition": "posthoc"})
        block = _structured_certificate_block(family, instance, resp.text)
        record["posthoc_formalization"] = {"prompt": prompt.text, "response": resp.text, "response_meta": {k: v for k, v in resp.to_dict().items() if k != "text"}, **block}

    # -- Condition C: supplied-idea formalization baseline ----------------------
    if conditions.get("supplied_idea", True):
        idea = family.canonical_idea(instance)
        prompt = supplied_idea_prompt(family, instance, idea, render_format)
        cfg = GenerationConfig(**{**config.__dict__, "system": prompt.system})
        resp = runner.generate(prompt.text, cfg, context={**context_base, "condition": "supplied_idea"})
        block = _structured_certificate_block(family, instance, resp.text)
        record["supplied_idea_baseline"] = {"prompt": prompt.text, "supplied_idea": idea.prose, "response": resp.text, "response_meta": {k: v for k, v in resp.to_dict().items() if k != "text"}, **block}

    # -- Retrieval control: recognition probe (separate call) -------------------
    if conditions.get("recognition", True):
        prompt = recognition_prompt(family, instance, render_format)
        cfg = GenerationConfig(**{**config.__dict__, "system": prompt.system, "max_output_tokens": min(config.max_output_tokens, 512)})
        resp = runner.generate(prompt.text, cfg, context={**context_base, "condition": "recognition"})
        record["retrieval_control"] = {"prompt": prompt.text, "response": resp.text, "response_meta": {k: v for k, v in resp.to_dict().items() if k != "text"}, **_parse_recognition(resp.text)}

    record["metadata"]["timestamp_end"] = utc_now()
    # a record must always be JSON-serializable; fail loudly here rather than at write time
    json.dumps(record, default=str)
    return record

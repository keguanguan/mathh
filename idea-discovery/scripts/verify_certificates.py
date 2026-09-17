#!/usr/bin/env python
"""Verify certificates against instances (manual inspection / debugging).

    python scripts/verify_certificates.py --instances data/generated/domino_tiling_seed0.jsonl \
        --certificate '{"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}'
    python scripts/verify_certificates.py --run data/raw_runs/mock_scaling_v0/<run_id>   # re-verify stored certificates
"""
import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.families import Instance, get_family
from idea_discovery.utils.serialization import read_jsonl
from idea_discovery.verifiers import verify_certificate


def reverify_run(run_dir: Path) -> tuple[int, int]:
    instances = {r["instance_id"]: Instance.from_dict(r) for r in read_jsonl(run_dir / "instances.jsonl")}
    mismatches = 0
    n = 0
    for rec in read_jsonl(run_dir / "trials.jsonl"):
        inst = instances[rec["instance"]["instance_id"]]
        for block_name in ("posthoc_formalization", "supplied_idea_baseline"):
            block = rec.get(block_name)
            if not block or block.get("certificate") is None or block.get("stated_none"):
                continue
            n += 1
            res = verify_certificate(inst, block["certificate"])
            if bool(res.valid and res.is_idea) != bool(block["valid"]):
                mismatches += 1
                print(f"MISMATCH {rec['trial_id']} {block_name}: stored={block['valid']} recomputed={res.valid} ({res.failure_reason})")
        for cand in (rec.get("idea_extraction") or {}).get("candidates", []):
            n += 1
            res = verify_certificate(inst, cand["certificate"])
            if res.valid != cand["verification"]["valid"]:
                mismatches += 1
                print(f"MISMATCH {rec['trial_id']} candidate: stored={cand['verification']['valid']} recomputed={res.valid}")
    return n, mismatches


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instances", type=Path, help="instances JSONL")
    ap.add_argument("--certificate", type=str, help="certificate JSON to check against every instance")
    ap.add_argument("--run", type=Path, help="raw run directory: re-verify every stored certificate and compare")
    args = ap.parse_args()
    if args.run:
        n, mismatches = reverify_run(args.run)
        print(f"re-verified {n} certificates, {mismatches} mismatches")
        return
    if not (args.instances and args.certificate):
        ap.error("provide --run, or both --instances and --certificate")
    cert = json.loads(args.certificate)
    for r in read_jsonl(args.instances):
        inst = Instance.from_dict(r)
        fam = get_family(inst.family_id)
        res = verify_certificate(inst, cert)
        canon = fam.canonical_match(inst, res.normalized_certificate) if res.valid else None
        print(
            f"{inst.instance_id:45s} answer={inst.ground_truth['answer']:10s} valid={res.valid!s:5} structural={res.structural_valid!s:5} "
            f"relevant={res.decision_relevant!s:5} canonical={canon} method={res.method} exact={res.exact} {res.failure_reason or ''}"
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Dump a run's trials in a human-readable form for manual inspection.

    python scripts/inspect_run.py --run data/raw_runs/pilot_anthropic_v0/pilot1 [--full] [--trial N]

Without --full, free-solve responses are truncated; --full prints them whole.
--summary prints one line per trial only.
"""
import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401

from idea_discovery.utils.serialization import read_jsonl


def _short(text, n):
    if text is None:
        return "None"
    text = str(text)
    return text if len(text) <= n else text[:n] + f"... [{len(text) - n} more chars]"


def summary_line(rec: dict) -> str:
    inst = rec["instance"]
    fs = rec.get("free_solve") or {}
    ie = rec.get("idea_extraction") or {}
    ph = rec.get("posthoc_formalization") or {}
    si = rec.get("supplied_idea_baseline") or {}
    rc = rec.get("retrieval_control") or {}
    meta = fs.get("response_meta") or {}
    usage = meta.get("usage") or {}
    ans = (fs.get("parsed_answer") or {}).get("parsed")
    return (
        f"{inst['family_id']:16s} n={inst['size']:<4} d{inst['transfer_level']} ib={int(bool(inst['idea_bearing']))} "
        f"truth={inst['ground_truth_answer']:<8} ans={str(ans):<8} S={_flag(fs.get('answer_correct'))} "
        f"I={_flag(ie.get('idea_valid'))} W={_flag(ie.get('witness_valid'))} can={_flag(ie.get('canonical_match'))} "
        f"PH={_flag(ph.get('valid'))}{'w' if ph.get('witness_valid') else ''}{'(none)' if ph.get('stated_none') else ''} F={_flag(si.get('valid'))}{'w' if si.get('witness_valid') else ''} "
        f"rec={_flag(rc.get('recognized'))} out={usage.get('output_tokens', '?')} err={meta.get('error')}"
    )


def _flag(v):
    return "-" if v is None else ("Y" if v else "n")


def dump(rec: dict, full: bool) -> None:
    fs = rec.get("free_solve") or {}
    ie = rec.get("idea_extraction") or {}
    ver = rec.get("verification") or {}
    ph = rec.get("posthoc_formalization") or {}
    si = rec.get("supplied_idea_baseline") or {}
    rc = rec.get("retrieval_control") or {}
    print("=" * 100)
    print(rec["trial_id"])
    print(summary_line(rec))
    print("-" * 40, "PROBLEM")
    print(fs.get("prompt"))
    print("-" * 40, "FREE RESPONSE", "(full)" if full else "(truncated)")
    print(fs.get("response") if full else _short(fs.get("response"), 3000))
    meta = fs.get("response_meta") or {}
    print("-" * 40, "META")
    print(json.dumps({k: meta.get(k) for k in ("usage", "latency_s", "error")}, indent=None))
    print("stop_reason:", (meta.get("raw") or {}).get("stop_reason"))
    print("-" * 40, "PARSED ANSWER / EXTRACTION")
    print("parsed:", fs.get("parsed_answer"))
    print("idea_present:", ie.get("idea_present"), "idea_valid:", ie.get("idea_valid"), "witness_valid:", ie.get("witness_valid"), "canonical:", ie.get("canonical_match"))
    print("method:", ie.get("extraction_method"))
    print("span:", _short(ie.get("supporting_span"), 400))
    print("certificate:", json.dumps(ie.get("extracted_certificate")))
    if ver:
        print("verification:", json.dumps({k: ver.get(k) for k in ("valid", "structural_valid", "decision_relevant", "failure_reason", "method")}))
    cands = ie.get("candidates") or []
    if len(cands) > 1:
        print(f"other candidates ({len(cands)}):")
        for c in cands:
            v = c.get("verification") or {}
            print("   ", c.get("extraction_method"), json.dumps(c.get("certificate")), "->", v.get("valid"), v.get("failure_reason"))
    print("-" * 40, "POST-HOC")
    print("certificate:", json.dumps(ph.get("certificate")), "parse_error:", ph.get("parse_error"))
    v = ph.get("verification") or {}
    print("valid:", ph.get("valid"), "witness_valid:", ph.get("witness_valid"), "stated_none:", ph.get("stated_none"), "canonical:", ph.get("canonical_match"), "fail:", v.get("failure_reason"))
    if full:
        print("response:", ph.get("response"))
    print("-" * 40, "SUPPLIED IDEA")
    print("certificate:", json.dumps(si.get("certificate")), "parse_error:", si.get("parse_error"))
    v = si.get("verification") or {}
    print("valid:", si.get("valid"), "witness_valid:", si.get("witness_valid"), "canonical:", si.get("canonical_match"), "fail:", v.get("failure_reason"))
    if full:
        print("response:", si.get("response"))
    print("-" * 40, "RECOGNITION")
    print(json.dumps({k: rc.get(k) for k in ("recognized", "proposed_name", "proposed_source", "confidence", "parse_error")}))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--trial", type=int, default=None, help="0-based index of a single trial to dump")
    ap.add_argument("--family", default=None)
    args = ap.parse_args()
    recs = list(read_jsonl(args.run / "trials.jsonl"))
    if args.family:
        recs = [r for r in recs if r["instance"]["family_id"] == args.family]
    if args.trial is not None:
        recs = [recs[args.trial]]
    for i, rec in enumerate(recs):
        if args.summary:
            print(f"[{i:2d}]", summary_line(rec))
        else:
            dump(rec, args.full)
    if args.summary:
        tot_in = sum(((r.get("free_solve") or {}).get("response_meta") or {}).get("usage", {}).get("input_tokens", 0) or 0 for r in recs)
        tot_out = 0
        for r in recs:
            for key in ("free_solve", "posthoc_formalization", "supplied_idea_baseline", "retrieval_control"):
                u = ((r.get(key) or {}).get("response_meta") or {}).get("usage") or {}
                tot_out += u.get("output_tokens", 0) or 0
                if key != "free_solve":
                    tot_in += u.get("input_tokens", 0) or 0
        print(f"trials: {len(recs)}; total input tokens {tot_in}; total output tokens {tot_out}")


if __name__ == "__main__":
    main()

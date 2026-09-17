"""Regression tests for failure modes found in the first real-model pilot (2026-09-17)."""
import math

from idea_discovery.analysis.process import process_run
from idea_discovery.evaluation import ExperimentRunner, load_experiment_config, run_trial
from idea_discovery.extraction import extract_and_verify
from idea_discovery.extraction.candidates import normalize_math_text
from idea_discovery.families import get_family
from idea_discovery.families.base import Instance
from idea_discovery.models import GenerationConfig, MockModelRunner
from idea_discovery.structures import subtraction_game as sg, vector_game as vg
from idea_discovery.utils.serialization import read_jsonl
from idea_discovery.verifiers import verify_certificate


def _heap_instance(heaps, k):
    fam = get_family("subtraction_game")
    s = sg.make_structure(list(heaps), k)
    return fam, Instance(instance_id="t", family_id="subtraction_game", size=max(heaps), transfer_level=1, generation_seed=0, structure=s, parameters={}, ground_truth=fam._ground_truth(s), idea_bearing=True, surface={"type": "heaps_bounded_take"}, transfer={})


def test_rank_over_q():
    assert vg.rank_over_q([[1, -1, 0], [-1, 1, 0]]) == 1
    assert vg.rank_over_q([[1, -1, 0], [0, 1, -1]]) == 2
    assert vg.rank_over_q([[3, -3, 0], [3, 0, -3], [-3, 0, 3]]) == 2


def test_population_moves_span_hyperplane_and_are_primitive():
    """Pilot: two mutually inverse moves let an integer invariant (p - k) decide; all moves
    divisible by the modulus make every count invariant. Both are rejected now."""
    fam = get_family("population_game")
    for size in (24, 48):
        for seed in range(8):
            inst = fam.generate_instance(size, seed)
            moves = inst.structure["moves"]
            assert vg.rank_over_q(moves) == len(moves[0]) - 1
            assert math.gcd(*(abs(x) for v in moves for x in v)) == 1


def test_normalize_math_text():
    t = r"Color $(r,c)$ **black** if $r+c$ is even; $b \bmod 3$ is unchanged; $x \equiv 2 \pmod{5}$; $a\oplus b$."
    n = normalize_math_text(t)
    assert "$" not in n and "**" not in n
    assert "r+c is even" in n and "b mod 3 is unchanged" in n and "x = 2 mod 5" in n and "a xor b" in n


def test_tex_wrapped_phrase_is_extracted(domino, domino_impossible):
    """The pilot's free responses wrote the colouring as '$r+c$ is even'."""
    plain = "Colour the square (r, c) black if r + c is even and white otherwise. FINAL ANSWER: impossible"
    tex = "Colour the square $(r,c)$ **black** if $r+c$ is even and white otherwise. FINAL ANSWER: impossible"
    assert extract_and_verify(domino, domino_impossible, plain).idea_valid
    res = extract_and_verify(domino, domino_impossible, tex)
    assert res.idea_valid
    assert any(c["extraction_method"].endswith("+tex_normalized") for c in res.candidates)


def test_supplied_idea_skipped_on_balance_controls(population, population_possible, population_impossible, all_conditions):
    runner = MockModelRunner(policy="correct_answer_correct_idea")
    rec = run_trial(population, population_possible, runner, GenerationConfig(), None, all_conditions)
    assert rec["supplied_idea_baseline"].get("skipped")
    rec = run_trial(population, population_possible, runner, GenerationConfig(), None, all_conditions, supplied_idea_on_controls=True)
    assert "response" in rec["supplied_idea_baseline"]
    rec = run_trial(population, population_impossible, runner, GenerationConfig(), None, all_conditions)
    assert rec["supplied_idea_baseline"]["valid"] is True


def test_structured_calls_are_capped(domino, domino_impossible, all_conditions):
    runner = MockModelRunner(policy="correct_answer_correct_idea")
    rec = run_trial(domino, domino_impossible, runner, GenerationConfig(max_output_tokens=16000), None, all_conditions, structured_max_output_tokens=6000)
    assert rec["free_solve"]["response_meta"]["config"]["max_output_tokens"] == 16000
    assert rec["posthoc_formalization"]["response_meta"]["config"]["max_output_tokens"] == 6000
    assert rec["supplied_idea_baseline"]["response_meta"]["config"]["max_output_tokens"] == 6000


def test_losing_set_verifier_accepts_mirroring_and_rejects_wrong_sets():
    """Pilot: on (8, 24, 2) with moves 1..7 the model proved a first-player win by keeping every
    heap a multiple of 8 - a valid pairing strategy that is not a complete characterisation."""
    fam, inst = _heap_instance([8, 24, 2], 7)
    assert inst.ground_truth["answer"] == "first"
    ok = verify_certificate(inst, {"certificate_type": "losing_set", "member_expr": "h1 % 8 == 0 and h2 % 8 == 0 and h3 % 8 == 0"})
    assert ok.valid and ok.is_idea and ok.details["relevance"]["implied_answer"] == "first"
    assert not verify_certificate(inst, {"certificate_type": "xor_invariant", "losing_expr": "(h1 % 8) + (h2 % 8) + (h3 % 8)"}).structural_valid
    assert not verify_certificate(inst, {"certificate_type": "losing_set", "member_expr": "h1 % 7 == 0 and h2 % 7 == 0 and h3 % 7 == 0"}).structural_valid
    assert not verify_certificate(inst, {"certificate_type": "losing_set", "member_expr": "True"}).structural_valid
    # the full nim characterisation is also a valid losing set
    assert verify_certificate(inst, {"certificate_type": "losing_set", "member_expr": "xor(h1 % 8, h2 % 8, h3 % 8) == 0"}).valid
    # a set that does not decide the start is structurally fine but not relevant
    _, inst2 = _heap_instance([9, 9, 3], 7)
    r = verify_certificate(inst2, {"certificate_type": "losing_set", "member_expr": "h1 % 8 == 0 and h2 % 8 == 0 and h3 % 8 == 0"})
    assert r.structural_valid and not r.decision_relevant


def test_mirroring_phrase_is_extracted():
    fam, inst = _heap_instance([8, 24, 2], 7)
    text = "Remove the third heap. After each of my moves every heap size is a multiple of 8, so the opponent can never take the last counter. FINAL ANSWER: first"
    res = extract_and_verify(fam, inst, text)
    assert res.idea_valid and res.selected["certificate"]["certificate_type"] == "losing_set"


def test_xor_extractor_tries_every_mentioned_modulus():
    fam, inst = _heap_instance([2, 13, 1], 5)
    text = r"Let $S = (a_1 \bmod 6)\oplus(a_2 \bmod 6)\oplus(a_3 \bmod 6)$ where $\oplus$ is bitwise XOR of the residues, each in $\{0,1,2,3,4,5\}$. FINAL ANSWER: first"
    res = extract_and_verify(fam, inst, text)
    assert res.idea_valid and res.selected["certificate"]["losing_expr"] == "xor(h1 % 6, h2 % 6, h3 % 6)"


def test_reextract_does_not_touch_raw_records(tmp_path):
    cfg = load_experiment_config("configs/experiments/mock_scaling_v1.yaml")
    cfg.instances_per_cell = 1
    cfg.families = ["subtraction_game"]
    cfg.instance_sizes = {"subtraction_game": [8]}
    run_dir = ExperimentRunner(cfg, run_id="rx", output_root=tmp_path / "raw").run()
    before = (run_dir / "trials.jsonl").read_bytes()
    out = process_run(run_dir, tmp_path / "proc", tmp_path / "res", n_boot=10, figures=False, reextract=True)
    assert (run_dir / "trials.jsonl").read_bytes() == before
    rex = list(read_jsonl(out["processed_dir"] / "trials_reextracted.jsonl"))
    assert rex and all(r["metadata"]["reextracted"] for r in rex)

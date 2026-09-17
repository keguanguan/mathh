"""Milestone-2 families: sliding_puzzle, subtraction_game, difference_board.

Each family: deterministic generation, exact ground truth confirmed by an
independent exhaustive method, canonical / alternative / invalid / degenerate
certificates, surfaces, extraction, and the mock pipeline.
"""
import pytest

from idea_discovery.evaluation import run_trial
from idea_discovery.extraction import extract_and_verify
from idea_discovery.families import get_family
from idea_discovery.generation.seeds import corpus_dir, seed_statement
from idea_discovery.models import GenerationConfig, MockModelRunner
from idea_discovery.prompting import forbidden_terms_present, free_solve_prompt
from idea_discovery.structures import difference_board as db, sliding_puzzle as sp, subtraction_game as sg
from idea_discovery.verifiers import verify_certificate

SIZES = {"sliding_puzzle": 4, "subtraction_game": 24, "difference_board": 100}


@pytest.fixture(scope="module")
def puzzle():
    return get_family("sliding_puzzle")


@pytest.fixture(scope="module")
def game():
    return get_family("subtraction_game")


@pytest.fixture(scope="module")
def board():
    return get_family("difference_board")


@pytest.mark.parametrize("family_id", list(SIZES))
def test_generation_deterministic_and_sane(family_id):
    fam = get_family(family_id)
    size = SIZES[family_id]
    a, b = fam.generate_instance(size, 3), fam.generate_instance(size, 3)
    assert a.to_dict() == b.to_dict()
    answers = set()
    for seed in range(8):
        inst = fam.generate_instance(size, seed)
        assert fam.sanity_check(inst) == []
        answers.add(inst.ground_truth["answer"])
    assert answers == set(fam.answer_options)


@pytest.mark.parametrize("family_id", list(SIZES))
@pytest.mark.parametrize("level", [0, 1, 2])
def test_prompts_have_no_hints(family_id, level):
    fam = get_family(family_id)
    inst = fam.generate_transfer_instance(level, 2, size=SIZES[family_id])
    assert forbidden_terms_present(free_solve_prompt(fam, inst).text) == []
    assert fam.sanity_check(inst) == []


def test_classical_statements_come_from_corpus_when_available(puzzle, game, board):
    for fam, seed_id in ((puzzle, "fifteen_puzzle"), (game, "nim"), (board, "euclids_game")):
        inst = fam.classical_instance()
        assert inst.transfer_level == 0 and fam.sanity_check(inst) == []
        assert inst.parameters["seed_id"] == seed_id
        if corpus_dir() is not None:
            assert seed_statement(seed_id) in fam.render_problem(inst)
            assert inst.parameters["corpus"] == "math-insight-examples"


class TestSlidingPuzzle:
    def test_parity_rule_matches_bfs_on_small_boards(self, puzzle):
        for seed in range(6):
            inst = puzzle.generate_instance(3, seed)
            assert sp.bfs_reachable(inst.structure) == (inst.ground_truth["answer"] == "possible")
        # 2 x 3 boards built by hand
        s = sp.make_structure(2, 3, [[1, 2, 3], [4, 5, 0]], [[1, 2, 3], [5, 4, 0]])
        assert not sp.parity_reachable(s) and not sp.bfs_reachable(s)

    def test_possible_witness_verifies(self, puzzle):
        inst = puzzle.generate_instance(4, 1, answer="possible")
        assert verify_certificate(inst, inst.ground_truth["witness"]).valid
        bad = {"certificate_type": "explicit_construction", "tiles_moved": inst.ground_truth["witness"]["tiles_moved"][:-1]}
        assert not verify_certificate(inst, bad).valid

    def test_certificates(self, puzzle):
        inst = puzzle.generate_instance(4, 1, answer="impossible")
        r = verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "taxicab"})
        assert r.valid and r.method == "local_rule" and puzzle.canonical_match(inst, r.normalized_certificate)
        r = verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_expr": "(r + c + 1) % 2"})
        assert r.valid and puzzle.canonical_match(inst, r.normalized_certificate)
        # even width: tiles-only inversions + blank row is valid and non-canonical; tiles-only alone is not invariant
        r = verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "row"})
        assert r.valid and not puzzle.canonical_match(inst, r.normalized_certificate)
        assert not verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "none"}).structural_valid
        assert not verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "none"}).structural_valid
        assert not verify_certificate(inst, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "row"}).structural_valid
        # odd width: tiles-only inversions alone is the classic invariant
        odd = puzzle.generate_instance(3, 1, answer="impossible")
        assert verify_certificate(odd, {"certificate_type": "permutation_parity", "permutation_of": "tiles_only", "blank_term": "none"}).valid
        # malformed
        for cert in ({"certificate_type": "permutation_parity", "permutation_of": "cells"}, {"certificate_type": "permutation_parity", "blank_term": "diag"}, {"certificate_type": "permutation_parity", "blank_expr": "r +"}):
            assert verify_certificate(inst, cert).failure_reason.startswith("malformed")
        # valid invariant on a possible instance is not decision-relevant
        pos = puzzle.generate_instance(4, 1, answer="possible")
        r = verify_certificate(pos, {"certificate_type": "permutation_parity", "permutation_of": "all_cells", "blank_term": "taxicab"})
        assert r.structural_valid and not r.decision_relevant

    def test_graph_surface(self, puzzle):
        inst = puzzle.apply_surface(puzzle.generate_instance(4, 2, answer="impossible"), 2, 2)
        idea = puzzle.canonical_idea(inst)
        r = verify_certificate(inst, idea.certificate)
        assert r.valid and puzzle.canonical_match(inst, r.normalized_certificate)
        assert not verify_certificate(inst, puzzle.invalid_idea(inst)).structural_valid
        res = extract_and_verify(puzzle, inst, idea.explicit_prose)
        assert res.idea_valid
        text = puzzle.render_problem(inst)
        assert "listed in the fixed order" in text and "row" not in text.lower()

    @pytest.mark.parametrize(
        "text,rule",
        [
            ("The sign of the permutation flips at every move, and so does the parity of the blank's taxicab distance from the corner.", "sign_and_blank_distance"),
            ("Count the inversions of the tiles and add the row of the blank.", "inversions_plus_blank_row"),
            ("Count the inversions.", "inversions_only"),
        ],
    )
    def test_extraction(self, puzzle, text, rule):
        inst = puzzle.generate_instance(4, 1, answer="impossible")
        cands = puzzle.extract_candidates(inst, text)
        assert [c.rule_id for c in cands] == [rule]
        assert puzzle.extract_candidates(inst, "I moved tiles around for a while.") == []


class TestSubtractionGame:
    def test_theorem_matches_dp(self, game):
        for seed in range(6):
            inst = game.generate_instance(20, seed)
            P = sg.p_positions(inst.structure)
            assert (tuple(inst.structure["heaps"]) in P) == (inst.ground_truth["answer"] == "second")
        classic = game.classical_instance()
        P = sg.p_positions(classic.structure)
        assert all((s in P) == sg.theorem_is_p_position(classic.structure, s) for s in sg.states(classic.structure))
        assert classic.ground_truth["answer"] == "first" and classic.ground_truth["winning_move"] == [2, 5, 7]

    def test_certificates(self, game):
        inst = game.generate_instance(20, 1)
        k = inst.structure["max_take"]
        r = verify_certificate(inst, game.canonical_idea(inst).certificate)
        assert r.valid and r.method == "exhaustive" and r.exact and game.canonical_match(inst, r.normalized_certificate)
        # equivalent expression written with ^ and different names
        r2 = verify_certificate(inst, {"certificate_type": "xor_invariant", "losing_expr": f"(a % {k + 1}) ^ (b % {k + 1}) ^ (c % {k + 1})"})
        assert r2.valid and game.canonical_match(inst, r2.normalized_certificate)
        assert not verify_certificate(inst, {"certificate_type": "xor_invariant", "losing_expr": "h1 ^ h2 ^ h3"}).structural_valid  # plain nim-sum is wrong for bounded take
        assert not verify_certificate(inst, {"certificate_type": "xor_invariant", "losing_expr": "0"}).structural_valid  # constant
        assert not verify_certificate(inst, game.invalid_idea(inst)).structural_valid
        assert verify_certificate(inst, {"certificate_type": "xor_invariant", "losing_expr": "h9"}).failure_reason.startswith("malformed")
        assert verify_certificate(inst, {"certificate_type": "xor_invariant"}).failure_reason.startswith("malformed")

    def test_all_instances_idea_bearing_and_track_surface(self, game):
        for ans in ("first", "second"):
            inst = game.generate_instance(20, 2, answer=ans)
            assert inst.idea_bearing
            d2 = game.apply_surface(inst, 2, 2)
            assert "track" in game.render_problem(d2) and verify_certificate(d2, game.canonical_idea(d2).certificate).valid

    def test_extraction(self, game):
        inst = game.generate_instance(20, 1)
        k = inst.structure["max_take"]
        cands = game.extract_candidates(inst, f"Reduce each heap modulo {k + 1} and take the nim-sum of the remainders.")
        assert cands and cands[0].certificate["losing_expr"] == f"xor(h1 % {k + 1}, h2 % {k + 1}, h3 % {k + 1})"
        cands = game.extract_candidates(inst, "Take the XOR of the heap sizes.")
        assert cands and cands[0].certificate["losing_expr"] == "xor(h1, h2, h3)"
        assert game.extract_candidates(inst, "Consider a few sample games.") == []


class TestDifferenceBoard:
    def test_ground_truth_matches_closure(self, board):
        for seed in range(6):
            inst = board.generate_instance(100, seed)
            assert (inst.structure["target"] in db.closure(inst.structure)) == (inst.ground_truth["answer"] == "possible")
        pos = board.generate_instance(100, 1, answer="possible")
        assert verify_certificate(pos, pos.ground_truth["witness"]).valid

    def test_certificates(self, board):
        inst = board.generate_instance(100, 0, answer="impossible")
        g = inst.ground_truth["gcd"]
        r = verify_certificate(inst, {"certificate_type": "gcd_invariant", "divisor": g})
        assert r.valid and r.method == "symbolic" and board.canonical_match(inst, r.normalized_certificate)
        r1 = verify_certificate(inst, {"certificate_type": "gcd_invariant", "divisor": 1})
        assert r1.structural_valid and not r1.decision_relevant
        assert not verify_certificate(inst, board.invalid_idea(inst)).structural_valid
        alt = board.alternative_idea(inst)
        if alt is not None:
            ra = verify_certificate(inst, alt.certificate)
            assert ra.valid and not board.canonical_match(inst, ra.normalized_certificate)
        assert verify_certificate(inst, {"certificate_type": "gcd_invariant"}).failure_reason.startswith("malformed")
        assert verify_certificate(inst, {"certificate_type": "gcd_invariant", "divisor": 0}).failure_reason.startswith("malformed")

    def test_extraction(self, board):
        inst = board.generate_instance(100, 0, answer="impossible")
        g = inst.ground_truth["gcd"]
        cands = board.extract_candidates(inst, f"Every number on the board is divisible by {g}, so the target cannot appear.")
        assert [c.certificate["divisor"] for c in cands] == [g]
        assert board.extract_candidates(inst, "The numbers keep getting smaller.") == []


@pytest.mark.parametrize("family_id", list(SIZES))
def test_mock_pipeline_on_new_families(family_id, all_conditions):
    fam = get_family(family_id)
    size = SIZES[family_id]
    inst = fam.generate_instance(size, 1, answer="second" if family_id == "subtraction_game" else "impossible")
    rec = run_trial(fam, inst, MockModelRunner(policy="correct_answer_correct_idea"), GenerationConfig(), None, all_conditions)
    assert rec["free_solve"]["answer_correct"] and rec["idea_extraction"]["idea_valid"] and rec["posthoc_formalization"]["valid"] and rec["supplied_idea_baseline"]["valid"]
    rec = run_trial(fam, inst, MockModelRunner(policy="wrong_answer_no_idea"), GenerationConfig(), None, all_conditions)
    assert rec["free_solve"]["answer_correct"] is False and not rec["idea_extraction"]["idea_valid"] and rec["supplied_idea_baseline"]["valid"]
    rec = run_trial(fam, inst, MockModelRunner(policy="malformed_certificate"), GenerationConfig(), None, all_conditions)
    assert rec["posthoc_formalization"]["parse_error"] and not rec["supplied_idea_baseline"]["valid"]

"""Deterministic extraction, JSON parsing, LLM-extraction span validation, prompts, answers."""
import json

import pytest

from idea_discovery.extraction import extract_and_verify, find_certificates, parse_structured_response, validate_llm_extraction
from idea_discovery.families import get_family
from idea_discovery.prompting import (
    FORBIDDEN_FREE_SOLVE_TERMS,
    forbidden_terms_present,
    free_solve_prompt,
    parse_final_answer,
    posthoc_prompt,
    recognition_prompt,
    supplied_idea_prompt,
)


class TestDominoExtraction:
    @pytest.mark.parametrize(
        "text,rule",
        [
            ("Colour the board like a chessboard; each domino covers one black and one white square.", "checkerboard_phrase"),
            ("Use a checkerboard pattern.", "checkerboard_phrase"),
            ("Assign to cell (i, j) the value (i + j) mod 2.", "sum_parity_formula"),
            ("Call a square black when r + c is even and white otherwise.", "sum_parity_phrase"),
            ("Weight square (r,c) by (-1)^(r+c).", "minus_one_power"),
            ("Paint squares alternately black and white.", "alternating_colours_phrase"),
        ],
    )
    def test_phrases(self, domino, domino_impossible, text, rule):
        cands = domino.extract_candidates(domino_impossible, text)
        assert [c.rule_id for c in cands] == [rule]
        assert cands[0].supporting_span.strip() in text
        res = extract_and_verify(domino, domino_impossible, text)
        assert res.idea_present and res.idea_valid and res.canonical_match

    def test_no_idea_text(self, domino, domino_impossible):
        text = "I tried many placements and could not cover the board. FINAL ANSWER: impossible"
        assert domino.extract_candidates(domino_impossible, text) == []
        res = extract_and_verify(domino, domino_impossible, text)
        assert not res.idea_present and not res.idea_valid and res.selected is None

    def test_json_block_candidate(self, domino, domino_impossible):
        text = "Here it is:\n```json\n" + json.dumps({"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}) + "\n```"
        cands = domino.extract_candidates(domino_impossible, text)
        assert cands[0].extraction_method == "json_block"
        assert extract_and_verify(domino, domino_impossible, text).idea_valid

    def test_invalid_idea_is_extracted_but_rejected(self, domino, domino_impossible):
        text = "Colour column c with colour c mod 2. Then (c) mod 2 ... actually use (r + c) mod 2 no wait: use c % 2."
        res = extract_and_verify(domino, domino_impossible, "Give square (r, c) the weight c % 2.")
        assert not res.idea_valid

    def test_graph_surface_label_sets(self, domino, domino_impossible):
        d2 = domino.apply_surface(domino_impossible, 2, 1)
        idea = domino.canonical_idea(d2)
        res = extract_and_verify(domino, d2, idea.explicit_prose)
        assert res.idea_valid and res.selected["rule_id"] == "label_set_partition"
        wrong = "One class is {v1, v2, v3} and the rest form the other class."
        res = extract_and_verify(domino, d2, wrong)
        assert res.idea_present and not res.idea_valid

    def test_witness_in_free_response_is_not_an_idea(self, domino, domino_possible):
        text = "```json\n" + json.dumps(domino_possible.ground_truth["witness"]) + "\n```"
        res = extract_and_verify(domino, domino_possible, text)
        assert res.witness_valid and not res.idea_valid


class TestPopulationExtraction:
    def test_canonical_and_alternative_prose(self, population, population_impossible):
        idea = population.canonical_idea(population_impossible)
        res = extract_and_verify(population, population_impossible, idea.prose)
        assert res.idea_valid and res.canonical_match
        alt = population.alternative_idea(population_impossible)
        if alt is not None:
            res = extract_and_verify(population, population_impossible, alt.prose)
            assert res.idea_valid and res.canonical_match is False

    def test_symbolic_and_difference_phrases(self, population, population_impossible):
        names = population_impossible.surface["class_names"]
        m = population_impossible.ground_truth["canonical_invariant"]["modulus"]
        texts = [
            f"Note that {names[0]} - {names[1]} (mod {m}) never changes.",
            f"Consider the difference between the number of {names[0]} tokens and the number of {names[1]} tokens modulo {m}.",
            f"The quantity 2{names[0]} + {names[2]} mod {m} is preserved.",
        ]
        for t in texts:
            cands = population.extract_candidates(population_impossible, t)
            assert cands, t
            assert cands[0].certificate["modulus"] == m
        c = population.extract_candidates(population_impossible, texts[-1])[0].certificate["coefficients"]
        assert c[names[0]] == 2 and c[names[2]] == 1 and c[names[1]] == 0

    def test_string_surface_letters_need_word_boundaries(self, population, population_impossible):
        d2 = population.apply_surface(population_impossible, 2, 1)
        letters = d2.surface["class_names"]
        text = f"The letters are simple; consider {letters[0]} - {letters[1]} mod 3 as the invariant of interest."
        cands = population.extract_candidates(d2, text)
        assert len(cands) == 1
        assert cands[0].certificate["coefficients"] == {letters[0]: 1, letters[1]: -1, letters[2]: 0}

    def test_nothing_extracted_from_vague_text(self, population, population_impossible):
        assert population.extract_candidates(population_impossible, "Think about remainders mod 3 in general.") == []


class TestStructuredParsing:
    def test_parse_structured_response(self):
        cert, err = parse_structured_response('Sure:\n```json\n{"certificate_type": "none"}\n```')
        assert cert == {"certificate_type": "none"} and err is None
        cert, err = parse_structured_response('{"foo": 1}')
        assert cert == {"foo": 1} and "certificate_type" in err
        cert, err = parse_structured_response("no json at all")
        assert cert is None and err
        cert, err = parse_structured_response('```json\n{"certificate_type": "x", "weight_expr": (r + c\n```')
        assert cert is None

    def test_find_certificates_with_nested_braces(self):
        text = 'Look: {"certificate_type": "coloring_invariant", "weights": {"v1": 1, "v2": -1}} and {"other": {"a": 1}}'
        hits = find_certificates(text)
        assert len(hits) == 1 and hits[0].obj["weights"]["v2"] == -1

    def test_llm_extraction_requires_verbatim_quotes(self):
        response = "Colour the board like a chessboard. Each domino covers one of each colour."
        good = json.dumps({"certificate": {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, "evidence": {"weight_expr": "Colour the board like a chessboard."}})
        assert len(validate_llm_extraction(good, response)) == 1
        fabricated = json.dumps({"certificate": {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, "evidence": {"weight_expr": "use parity of r + c"}})
        assert validate_llm_extraction(fabricated, response) == []
        missing = json.dumps({"certificate": {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}, "evidence": {}})
        assert validate_llm_extraction(missing, response) == []


class TestPrompts:
    @pytest.mark.parametrize("family_id,size", [("domino_tiling", 8), ("population_game", 24)])
    @pytest.mark.parametrize("level", [0, 1, 2])
    def test_free_solve_prompt_has_no_hints(self, family_id, size, level):
        fam = get_family(family_id)
        inst = fam.generate_transfer_instance(level, 3, size=size)
        p = free_solve_prompt(fam, inst)
        assert forbidden_terms_present(p.text) == []
        assert "FINAL ANSWER" in p.text
        assert "impossible" in p.text  # the answer options are listed, nothing else
        # recognition probe must not mention the answer format or the idea either
        r = recognition_prompt(fam, inst)
        assert forbidden_terms_present(r.text) == [] and "recognized" in r.text

    def test_forbidden_list_covers_core_terms(self):
        for term in ("invariant", "parity", "coloring", "potential function", "certificate"):
            assert term in FORBIDDEN_FREE_SOLVE_TERMS

    def test_posthoc_quotes_free_response_verbatim(self, domino, domino_impossible):
        free = "My free response\nwith two lines.\nFINAL ANSWER: impossible"
        p = posthoc_prompt(domino, domino_impossible, free)
        assert free in p.text and "json" in p.text.lower()

    def test_supplied_idea_contains_prose_and_schema(self, population, population_impossible):
        idea = population.canonical_idea(population_impossible)
        p = supplied_idea_prompt(population, population_impossible, idea)
        assert idea.prose in p.text and "modular_invariant" in p.text


class TestAnswers:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("... \nFINAL ANSWER: impossible", "impossible"),
            ("FINAL ANSWER: **Possible**", "possible"),
            ("Final Answer: It is not possible.", "impossible"),
            ("FINAL ANSWER: No", "impossible"),
            ("FINAL ANSWER: yes", "possible"),
            ("FINAL ANSWER: possible\n... later\nFINAL ANSWER: impossible", "impossible"),
            ("no final line here, the answer is impossible", None),
            ("FINAL ANSWER: 42", None),
        ],
    )
    def test_parse(self, text, expected):
        assert parse_final_answer(text, ["possible", "impossible"]).parsed == expected

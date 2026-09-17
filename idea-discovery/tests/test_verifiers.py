"""Every verifier: one valid, one structurally invalid, one structurally valid but
degenerate certificate; malformed input; unsupported types; witness checks."""
import pytest

from idea_discovery.verifiers import available_certificate_types, get_verifier, verify_certificate


def test_registry():
    assert {"coloring_invariant", "modular_invariant", "explicit_construction"} <= set(available_certificate_types())
    assert get_verifier("coloring_invariant").certificate_type == "coloring_invariant"
    with pytest.raises(KeyError):
        get_verifier("nope")


def test_dispatch_never_raises(domino_impossible):
    assert not verify_certificate(domino_impossible, "not a dict").valid
    assert "certificate_type" in verify_certificate(domino_impossible, {}).failure_reason
    r = verify_certificate(domino_impossible, {"certificate_type": "quantum_flux"})
    assert not r.valid and r.details.get("supported") is False
    r = verify_certificate(domino_impossible, {"certificate_type": "none"})
    assert not r.valid and r.certificate_type == "none"
    # wrong structure kind for the verifier
    r = verify_certificate(domino_impossible, {"certificate_type": "modular_invariant", "coefficients": [1, 1], "modulus": 2})
    assert not r.valid and "does not support structure" in r.failure_reason


class TestColoringInvariant:
    def test_valid_canonical(self, domino_impossible):
        r = verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": "(-1)**(r + c)"})
        assert r.valid and r.structural_valid and r.decision_relevant
        assert r.method == "local_rule" and r.exact and r.is_idea
        assert r.details["structure"]["tile_sums"] == {0: 0}

    def test_valid_zero_one_variant_and_modulus(self, domino_impossible):
        assert verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2"}).valid
        assert verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": "(i + j) mod 2", "modulus": 2}).valid

    def test_structurally_invalid(self, domino_impossible):
        r = verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": "c % 2"})
        assert not r.valid and not r.structural_valid
        assert "placement" in r.failure_reason

    def test_constant_is_degenerate(self, domino_impossible):
        r = verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": "1"})
        assert r.structural_valid and not r.decision_relevant and not r.valid
        assert "constant" in r.failure_reason

    def test_valid_invariant_is_not_relevant_on_possible_instance(self, domino_possible):
        r = verify_certificate(domino_possible, {"certificate_type": "coloring_invariant", "weight_expr": "(-1)**(r + c)"})
        assert r.structural_valid and not r.decision_relevant

    def test_malformed(self, domino_impossible):
        for cert in (
            {"certificate_type": "coloring_invariant"},
            {"certificate_type": "coloring_invariant", "weight_expr": "(r +"},
            {"certificate_type": "coloring_invariant", "weight_expr": "r / 3"},
            {"certificate_type": "coloring_invariant", "weights": {"1,1": 1}},
            {"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2", "modulus": 0},
        ):
            r = verify_certificate(domino_impossible, cert)
            assert not r.valid and r.failure_reason.startswith("malformed"), cert

    def test_explicit_table_and_graph_labels(self, domino, domino_impossible):
        d2 = domino.apply_surface(domino_impossible, 2, 3)
        labels = d2.surface["labels"]
        good = {label: (1 if (int(k.split(",")[0]) + int(k.split(",")[1])) % 2 == 0 else -1) for k, label in labels.items()}
        assert verify_certificate(d2, {"certificate_type": "coloring_invariant", "weights": good}).valid
        bad = {label: int(k.split(",")[0]) % 2 for k, label in labels.items()}
        assert not verify_certificate(d2, {"certificate_type": "coloring_invariant", "weights": bad}).structural_valid
        # coordinate-keyed table on the grid surface
        table = {k: v for k, v in ((f"{r},{c}", (r + c) % 2) for r in range(1, 9) for c in range(1, 9))}
        assert verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weights": table}).valid

    def test_canonical_match(self, domino, domino_impossible):
        for expr, expected in (("(-1)**(r + c)", True), ("(r + c) % 2", True), ("3 * ((r + c) % 2) - 1", True)):
            r = verify_certificate(domino_impossible, {"certificate_type": "coloring_invariant", "weight_expr": expr})
            assert r.valid and domino.canonical_match(domino_impossible, r.normalized_certificate) == expected


class TestModularInvariant:
    def test_valid_canonical(self, population, population_impossible):
        idea = population.canonical_idea(population_impossible)
        r = verify_certificate(population_impossible, idea.certificate)
        assert r.valid and r.method == "local_rule" and r.exact
        assert population.canonical_match(population_impossible, r.normalized_certificate)

    def test_list_coefficients_and_scaled_form(self, population_impossible):
        canon = population_impossible.ground_truth["canonical_invariant"]
        m = canon["modulus"]
        r = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "coefficients": canon["coefficients"], "modulus": m})
        assert r.valid
        scaled = [(2 * a) % m for a in canon["coefficients"]]
        r2 = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "coefficients": scaled, "modulus": m})
        assert r2.valid == (m % 2 == 1 or any(a % m for a in scaled))

    def test_structurally_invalid(self, population, population_impossible):
        r = verify_certificate(population_impossible, population.invalid_idea(population_impossible))
        assert not r.structural_valid and "changes the form" in r.failure_reason

    def test_conservation_and_zero_forms_are_degenerate(self, population_impossible):
        k = len(population_impossible.structure["classes"])
        m = population_impossible.ground_truth["canonical_invariant"]["modulus"]
        r = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "coefficients": [1] * k, "modulus": m})
        assert r.structural_valid and not r.decision_relevant
        r = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "coefficients": [0] * k, "modulus": m})
        assert r.structural_valid and not r.decision_relevant and "constant" in r.failure_reason
        r = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "coefficients": [1, 2, 0], "modulus": 1})
        assert r.structural_valid and not r.decision_relevant

    def test_expression_form_exhaustive(self, population, population_impossible):
        canon = population_impossible.ground_truth["canonical_invariant"]
        names = population_impossible.surface["class_names"]
        terms = " + ".join(f"{a} * {n}" for a, n in zip(canon["coefficients"], names))
        r = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "expr": f"({terms}) % {canon['modulus']}"})
        assert r.valid and r.method == "exhaustive" and r.exact
        assert population.canonical_match(population_impossible, r.normalized_certificate)
        bad = verify_certificate(population_impossible, {"certificate_type": "modular_invariant", "expr": f"{names[0]} % 7"})
        assert not bad.valid

    def test_surface_class_names_accepted(self, population, population_impossible):
        d2 = population.apply_surface(population_impossible, 2, 5)
        idea = population.canonical_idea(d2)
        assert set(idea.certificate["coefficients"]) == set(d2.surface["class_names"])
        assert verify_certificate(d2, idea.certificate).valid

    def test_malformed(self, population_impossible):
        for cert in (
            {"certificate_type": "modular_invariant"},
            {"certificate_type": "modular_invariant", "coefficients": [1, 2]},
            {"certificate_type": "modular_invariant", "coefficients": [1, 2, 0]},
            {"certificate_type": "modular_invariant", "coefficients": {"unicorn": 1}, "modulus": 3},
            {"certificate_type": "modular_invariant", "expr": "zzz % 3"},
        ):
            r = verify_certificate(population_impossible, cert)
            assert not r.valid and r.failure_reason.startswith("malformed"), cert


class TestExplicitConstruction:
    def test_tiling_witness(self, domino_possible):
        w = domino_possible.ground_truth["witness"]
        r = verify_certificate(domino_possible, w)
        assert r.valid and not r.is_idea
        partial = {"certificate_type": "explicit_construction", "tiles": w["tiles"][:-1]}
        r = verify_certificate(domino_possible, partial)
        assert r.structural_valid and not r.decision_relevant
        overlap = {"certificate_type": "explicit_construction", "tiles": w["tiles"] + [w["tiles"][0]]}
        assert not verify_certificate(domino_possible, overlap).structural_valid
        illegal = {"certificate_type": "explicit_construction", "tiles": [[[1, 1], [3, 3]]]}
        assert not verify_certificate(domino_possible, illegal).structural_valid

    def test_move_sequence_witness(self, population_possible):
        w = population_possible.ground_truth["witness"]
        assert verify_certificate(population_possible, w).valid
        short = {"certificate_type": "explicit_construction", "moves": w["moves"][:-1]}
        r = verify_certificate(population_possible, short)
        assert not r.valid
        assert not verify_certificate(population_possible, {"certificate_type": "explicit_construction", "moves": [99]}).valid

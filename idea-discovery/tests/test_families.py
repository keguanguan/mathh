"""Family generation, ground truth, determinism, transfer surfaces, serialization."""
import pytest

from idea_discovery.families import Instance, available_families, get_family
from idea_discovery.generation import GenerationSpec, cell_seed, generate_instance_set
from idea_discovery.structures import tiling, vector_game as vg


def test_registry_lists_both_families():
    assert {"domino_tiling", "population_game"} <= set(available_families())


@pytest.mark.parametrize("family_id,size", [("domino_tiling", 8), ("population_game", 24)])
def test_generation_is_deterministic(family_id, size):
    fam = get_family(family_id)
    a = fam.generate_instance(size, 7)
    b = fam.generate_instance(size, 7)
    c = fam.generate_instance(size, 8)
    assert a.to_dict() == b.to_dict()
    assert a.content_hash() == b.content_hash()
    assert a.content_hash() != c.content_hash()


@pytest.mark.parametrize("family_id,size", [("domino_tiling", 8), ("domino_tiling", 12), ("population_game", 24), ("population_game", 48)])
def test_generated_instances_pass_sanity_checks(family_id, size):
    fam = get_family(family_id)
    answers = set()
    for seed in range(8):
        inst = fam.generate_instance(size, seed)
        assert fam.sanity_check(inst) == []
        assert inst.idea_bearing == (inst.ground_truth["answer"] == "impossible")
        answers.add(inst.ground_truth["answer"])
    assert answers == {"possible", "impossible"}, "generation should produce both answers over a few seeds"


def test_forced_answer_generation(domino, population):
    assert domino.generate_instance(8, 3, answer="possible").ground_truth["answer"] == "possible"
    assert domino.generate_instance(8, 3, answer="impossible").ground_truth["answer"] == "impossible"
    assert population.generate_instance(24, 3, answer="possible").ground_truth["answer"] == "possible"
    assert population.generate_instance(24, 3, answer="impossible").ground_truth["answer"] == "impossible"


class TestDominoGroundTruth:
    def test_classical_mutilated_chessboard(self, domino):
        inst = domino.classical_instance()
        assert inst.transfer_level == 0
        assert inst.ground_truth["answer"] == "impossible"
        assert inst.ground_truth["color_imbalance"] == -2
        assert domino.sanity_check(inst) == []

    def test_impossible_instances_have_imbalance(self, domino_impossible):
        assert tiling.color_imbalance(domino_impossible.structure) != 0
        assert tiling.perfect_matching(domino_impossible.structure) is None

    def test_possible_instances_have_verified_tiling(self, domino, domino_possible):
        witness = domino_possible.ground_truth["witness"]
        assert witness["certificate_type"] == "explicit_construction"
        assert len(witness["tiles"]) * 2 == len(tiling.cells(domino_possible.structure))
        assert domino.verify(domino_possible, witness).valid

    def test_matching_rejects_balanced_untileable_board(self, domino):
        # 4 x 4 minus (1,2), (2,1), (1,3), (2,4): two odd and two even cells removed (balanced),
        # but (1,1) is isolated, so no tiling exists. The invariant cannot prove this; the
        # family labels such boards proof_type="other" and never generates them.
        s = tiling.make_structure(4, 4, [(1, 2), (2, 1), (1, 3), (2, 4)])
        assert tiling.color_imbalance(s) == 0
        assert tiling.perfect_matching(s) is None
        gt = domino._ground_truth(s)
        assert gt["answer"] == "impossible" and gt["proof_type"] == "other"
        assert tiling.perfect_matching(tiling.make_structure(2, 3, [])) is not None

    def test_graph_surface_preserves_structure(self, domino, domino_impossible):
        d2 = domino.apply_surface(domino_impossible, 2, 1)
        assert d2.transfer_level == 2
        assert d2.structure == domino_impossible.structure
        assert d2.ground_truth == domino_impossible.ground_truth
        assert d2.transfer["target_surface"] == "graph_cover"
        assert set(d2.surface["labels"]) == {f"{r},{c}" for r, c in tiling.cells(d2.structure)}
        assert len(d2.surface["edges"]) == len(tiling.adjacency_edges(d2.structure))
        assert domino.sanity_check(d2) == []
        text = domino.render_problem(d2)
        assert "row" not in text.lower() and "grid" not in text.lower()

    def test_render_does_not_leak_answer(self, domino, domino_impossible):
        text = domino.render_problem(domino_impossible)
        assert "impossible" not in text.lower()
        assert "(r, c)" in text


class TestPopulationGroundTruth:
    def test_classical_chameleons(self, population):
        inst = population.classical_instance()
        assert inst.ground_truth["answer"] == "impossible"
        assert population.sanity_check(inst) == []
        reachable, _, _ = vg.reachability(inst.structure)
        assert not reachable

    def test_bfs_ground_truth_matches_stored(self, population):
        for seed in range(6):
            inst = population.generate_instance(24, seed)
            reachable, path, _ = vg.reachability(inst.structure)
            assert reachable == (inst.ground_truth["answer"] == "possible")
            if reachable:
                assert population.verify(inst, inst.ground_truth["witness"]).valid

    def test_moves_are_conservative_and_in_kernel(self, population_impossible):
        s = population_impossible.structure
        canon = population_impossible.ground_truth["canonical_invariant"]
        assert vg.is_conservative(s)
        for mv in s["moves"]:
            assert vg.linear_form(canon["coefficients"], mv, canon["modulus"]) == 0

    def test_string_surface_preserves_structure(self, population, population_impossible):
        d2 = population.apply_surface(population_impossible, 2, 1)
        assert d2.structure == population_impossible.structure
        assert d2.surface["type"] == "string_rewriting"
        assert len(d2.surface["class_names"]) == 3
        text = population.render_problem(d2)
        assert "Rule 1" in text and "token" not in text
        assert population.sanity_check(d2) == []


def test_instance_serialization_round_trip(domino_impossible, population_possible):
    for inst in (domino_impossible, population_possible):
        d = inst.to_dict()
        assert "content_hash" in d
        back = Instance.from_dict(d)
        assert back == inst
        assert back.content_hash() == d["content_hash"]


def test_instance_set_generation_pairs_levels():
    spec = GenerationSpec("domino_tiling", [6, 8], [0, 1, 2], 2, 42)
    insts = generate_instance_set(spec)
    by_level = {}
    for i in insts:
        by_level.setdefault(i.transfer_level, []).append(i)
    assert len(by_level[0]) == 1
    assert len(by_level[1]) == len(by_level[2]) == 4
    for a, b in zip(by_level[1], by_level[2]):
        assert a.structure == b.structure and b.transfer["source_instance_id"] == a.instance_id
    assert len({i.instance_id for i in insts}) == len(insts)
    assert cell_seed(42, "domino_tiling", 6, 0) == cell_seed(42, "domino_tiling", 6, 0)

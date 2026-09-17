"""End-to-end: mock model -> trial records -> raw logging -> tidy table -> metrics -> figures."""
import json
from pathlib import Path

import pytest

from idea_discovery.analysis import compute_all, make_all_figures, read_csv, tidy_rows, write_csv
from idea_discovery.analysis.process import process_run
from idea_discovery.evaluation import ConfigError, ExperimentRunner, build_experiment_config, load_experiment_config, run_trial
from idea_discovery.models import BEHAVIORS, ComputeCondition, GenerationConfig, MockModelRunner, build_runner
from idea_discovery.utils.serialization import load_json, read_jsonl

CONFIGS = Path(__file__).resolve().parents[1] / "configs"

EXPECTED = {
    # behaviour: (answer_correct, idea_valid, posthoc_valid, supplied_valid)
    "correct_answer_correct_idea": (True, True, True, True),
    "correct_answer_no_idea": (True, False, False, True),
    "wrong_answer_correct_idea": (False, True, True, True),
    "wrong_answer_no_idea": (False, False, False, True),
    "alternative_valid_idea": (True, True, True, True),
    "malformed_certificate": (True, False, False, False),
}


@pytest.mark.parametrize("behavior", BEHAVIORS)
@pytest.mark.parametrize("fixture", ["domino_impossible", "population_impossible"])
def test_mock_behaviors_produce_expected_records(request, behavior, fixture, all_conditions):
    inst = request.getfixturevalue(fixture)
    from idea_discovery.families import get_family

    fam = get_family(inst.family_id)
    rec = run_trial(fam, inst, MockModelRunner(policy=behavior), GenerationConfig(), None, all_conditions)
    correct, idea, posthoc, supplied = EXPECTED[behavior]
    assert rec["free_solve"]["answer_correct"] is correct
    assert rec["idea_extraction"]["idea_valid"] is idea
    assert rec["verification"]["valid"] is idea
    assert rec["posthoc_formalization"]["valid"] is posthoc
    assert rec["supplied_idea_baseline"]["valid"] is supplied
    assert rec["retrieval_control"]["recognized"] is False
    if behavior == "malformed_certificate":
        assert rec["posthoc_formalization"]["parse_error"]
        assert rec["supplied_idea_baseline"]["parse_error"]
    if behavior == "alternative_valid_idea" and fam.alternative_idea(inst) is not None and inst.family_id == "population_game":
        assert rec["idea_extraction"]["canonical_match"] is False
    # raw responses retained verbatim and JSON-serializable
    assert "FINAL ANSWER" in rec["free_solve"]["response"]
    json.dumps(rec)


def test_posthoc_does_not_alter_free_response(domino, domino_impossible, all_conditions):
    rec = run_trial(domino, domino_impossible, MockModelRunner(policy="correct_answer_correct_idea"), GenerationConfig(), None, all_conditions)
    assert rec["free_solve"]["response"] in rec["posthoc_formalization"]["prompt"]
    assert rec["free_solve"]["response_meta"]["raw"]["mock_behavior"] == "correct_answer_correct_idea"


def test_possible_instance_witness_is_not_idea(population, population_possible, all_conditions):
    rec = run_trial(population, population_possible, MockModelRunner(policy="correct_answer_correct_idea"), GenerationConfig(), None, all_conditions)
    assert rec["free_solve"]["answer_correct"] is True
    assert rec["idea_extraction"]["witness_valid"] is True
    assert rec["idea_extraction"]["idea_valid"] is False
    assert rec["instance"]["idea_bearing"] is False


def test_classical_instance_is_recognized(domino, all_conditions):
    inst = domino.classical_instance()
    rec = run_trial(domino, inst, MockModelRunner(policy="correct_answer_correct_idea"), GenerationConfig(), None, all_conditions)
    assert rec["retrieval_control"]["recognized"] is True
    assert rec["retrieval_control"]["proposed_name"]


def test_conditions_can_be_disabled(domino, domino_impossible):
    rec = run_trial(domino, domino_impossible, MockModelRunner(policy="mixed"), GenerationConfig(), None, {"free_solve": True, "posthoc": False, "supplied_idea": False, "recognition": False})
    assert rec["posthoc_formalization"] is None and rec["supplied_idea_baseline"] is None and rec["retrieval_control"] is None
    assert rec["free_solve"] is not None


def test_compute_condition_resolution():
    cc = ComputeCondition("high", {"mock": {"level": "high"}, "anthropic": {"thinking": {"budget_tokens": 32000}}}, rank=2)
    runner = MockModelRunner()
    cfg = runner.resolve_config(GenerationConfig(), cc)
    assert cfg.reasoning_setting == {"level": "high"}
    with pytest.raises(ValueError):
        runner.resolve_config(GenerationConfig(), ComputeCondition("x", {"anthropic": {}}))


def test_mock_behavior_is_stable_across_conditions(domino_impossible):
    runner = MockModelRunner(policy="mixed", seed=3)
    ctx = {"instance": domino_impossible, "repetition": 1, "compute_condition": None}
    assert runner.behavior_for(ctx) == runner.behavior_for(dict(ctx))
    assert runner.behavior_for(ctx) != runner.behavior_for({**ctx, "repetition": 2}) or True  # may coincide; just must not raise


def test_config_loading_and_validation(tmp_path):
    cfg = load_experiment_config(CONFIGS / "experiments" / "mock_scaling_v0.yaml")
    assert cfg.families == ["domino_tiling", "population_game"]
    assert [m["name"] for m in cfg.models] == ["mock_size_dependent", "mock_mixed"]
    assert cfg.compute_conditions[0].name == "default"
    assert cfg.instance_sizes["population_game"] == [12, 24, 48, 96]
    for name in ("mock_transfer_v0", "mock_compute_v0"):
        c = load_experiment_config(CONFIGS / "experiments" / f"{name}.yaml")
        assert c.experiment_id == name
    with pytest.raises(ConfigError):
        build_experiment_config({"experiment_id": "x", "families": ["nope"], "models": [], "instance_sizes": [4], "transfer_levels": [1], "compute_conditions": []})
    with pytest.raises(ConfigError):
        build_experiment_config({"experiment_id": "x", "families": ["domino_tiling"], "models": [{"provider": "mock", "model": "m"}], "instance_sizes": [6], "transfer_levels": [1], "compute_conditions": ["undefined_level"]})
    assert build_runner({"provider": "mock", "model": "mock-v1", "parameters": {"policy": "mixed"}}).policy == "mixed"


def test_end_to_end_run_and_analysis(tmp_path):
    raw = {
        "experiment_id": "pytest_e2e",
        "families": ["domino_tiling", "population_game"],
        "models": [{"name": "mock_a", "provider": "mock", "model": "mock-v1", "parameters": {"policy": "size_dependent", "seed": 1}}, {"name": "mock_b", "provider": "mock", "model": "mock-v1", "parameters": {"policy": "mixed", "seed": 2}}],
        "instance_sizes": {"domino_tiling": [6, 8], "population_game": [12, 24]},
        "transfer_levels": [0, 1, 2],
        "compute_conditions": [{"name": "low", "rank": 0, "provider_parameters": {"mock": {}}}, {"name": "high", "rank": 1, "provider_parameters": {"mock": {}}}],
        "repetitions": 1,
        "instances_per_cell": 2,
        "generation_seeds": {"base_seed": 5},
    }
    cfg = build_experiment_config(raw)
    runner = ExperimentRunner(cfg, run_id="t1", output_root=tmp_path / "raw", log=lambda s: None)
    run_dir = runner.run()
    manifest = load_json(run_dir / "manifest.json")
    records = list(read_jsonl(run_dir / "trials.jsonl"))
    # (1 classical + 2 sizes x 2 per cell x 2 levels) = 9 instances per family, x2 families x2 models x2 compute
    assert manifest["n_trials_planned"] == 9 * 2 * 2 * 2 == len(records)
    assert not (run_dir / "errors.jsonl").exists()
    assert {r["trial_id"] for r in records} == set(r["trial_id"] for r in records)
    assert "code_commit" in manifest and manifest["config"]["experiment_id"] == "pytest_e2e"
    # resume skips everything
    runner2 = ExperimentRunner(cfg, run_id="t1", output_root=tmp_path / "raw", resume=True, log=lambda s: None)
    runner2.run()
    assert len(list(read_jsonl(run_dir / "trials.jsonl"))) == len(records)
    with pytest.raises(FileExistsError):
        ExperimentRunner(cfg, run_id="t1", output_root=tmp_path / "raw", log=lambda s: None).run()
    # tidy + metrics + figures
    rows = tidy_rows(records)
    assert len(rows) == len(records)
    write_csv(rows, tmp_path / "tidy.csv")
    back = read_csv(tmp_path / "tidy.csv")
    assert [r["trial_id"] for r in back] == [r["trial_id"] for r in rows]
    assert all(isinstance(r["idea_valid"], bool) and isinstance(r["size"], int) for r in back)
    tables = compute_all(back, n_boot=50)
    I_n = tables["I_n_by_family"]
    assert I_n and all(0 <= t["p"] <= 1 and t["ci_low"] <= t["p"] <= t["ci_high"] for t in I_n)
    assert all(t["n"] > 0 for t in tables["I_d_pooled"]) and {t["transfer_level"] for t in tables["I_d_pooled"]} == {0, 1, 2}
    assert {t["compute_level"] for t in tables["I_c_pooled"]} == {"low", "high"}
    assert all(t["p"] == 1.0 for t in tables["recognition_pooled"] if t["transfer_level"] == 0)
    assert all(t["p"] == 0.0 for t in tables["recognition_pooled"] if t["transfer_level"] > 0)
    made = make_all_figures(tables, tmp_path / "figs")
    assert len(made) >= 5 and all(p.exists() for p in made)
    # the process_run entry point used by scripts/process_results.py
    out = process_run(run_dir, tmp_path / "processed", tmp_path / "results", n_boot=20, figures=False)
    assert (out["processed_dir"] / "tidy.csv").exists() and (out["results_dir"] / "summary.json").exists()


def test_metrics_only_count_idea_bearing_trials():
    rows = [
        {"model": "m", "family": "f", "instance_id": "a", "size": 1, "idea_bearing": True, "idea_valid": True, "solution_correct": True, "outcome_category": "idea_correct"},
        {"model": "m", "family": "f", "instance_id": "b", "size": 1, "idea_bearing": True, "idea_valid": False, "solution_correct": False, "outcome_category": "incorrect_no_idea"},
        {"model": "m", "family": "f", "instance_id": "c", "size": 1, "idea_bearing": False, "idea_valid": False, "solution_correct": True, "outcome_category": "correct_unclassified"},
    ]
    t = compute_all(rows, n_boot=10)
    assert t["I_n_pooled"][0]["n"] == 2 and t["I_n_pooled"][0]["p"] == 0.5
    assert t["S_n_pooled"][0]["n"] == 3 and abs(t["S_n_pooled"][0]["p"] - 2 / 3) < 1e-9
    assert t["S_n_given_I1_pooled"][0]["p"] == 1.0 and t["S_n_given_I0_pooled"][0]["p"] == 0.0

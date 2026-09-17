# idea-discovery

Experimental pipeline for the question:

> When additional reasoning makes language models better at mathematics, is it
> because they discover better mathematical ideas, or because they search harder
> over individual solutions?

The measurable object is whether a model discovers a **valid, decision-relevant
mathematical idea**, represented as a machine-verifiable certificate:

    valid idea = structural law (holds under the legal moves)
               + task discrimination (separates initial state from target)

Primary measurements: `I(n)`, `I(d)`, `I(c)` = P(valid idea | size, transfer
distance, compute), alongside ordinary accuracy `S(n)`, `S(d)`, `S(c)` and the
formalization baseline `F` = P(valid certificate | correct idea supplied).
Nothing is collapsed into a single "intuition score".

## Status: milestone 1 complete; milestone 2 in progress (5 families, real-model pilot pending)

| Item | Where |
|---|---|
| ProblemFamily interface, Instance record | `src/idea_discovery/families/base.py` |
| Certificate / verifier interface, registry, `VerificationResult` | `src/idea_discovery/verifiers/base.py` |
| Families: `domino_tiling`, `population_game`, `sliding_puzzle`, `subtraction_game`, `difference_board` | `src/idea_discovery/families/` |
| Exact verifiers: `coloring_invariant`, `modular_invariant`, `permutation_parity`, `xor_invariant`, `gcd_invariant`, `explicit_construction` (witness) | `src/idea_discovery/verifiers/` |
| Seed corpus access (classical d0 statements from `math-insight-examples`) | `src/idea_discovery/generation/seeds.py` |
| Seeded novel-instance generation + sanity checks | `families/*.py`, `generation/instances.py` |
| Transfer: d0 classical, d1 novel, d2 changed surface (graph cover; string rewriting) | `families/*.apply_surface` |
| Free-solve / post-hoc / supplied-idea protocol + recognition probe | `src/idea_discovery/prompting/protocol.py` |
| Mock model with six canned behaviours | `src/idea_discovery/models/mock.py` |
| Raw trial logging (JSONL, manifest, resumable) | `src/idea_discovery/evaluation/` |
| Deterministic idea extraction (+ optional span-quoting LLM extractor) | `src/idea_discovery/extraction/` |
| Tidy table, metrics with Wilson + cluster-bootstrap CIs, figures | `src/idea_discovery/analysis/` |
| Anthropic adapter (milestone 2, untested against the API) | `src/idea_discovery/models/anthropic_runner.py` |
| 133 unit tests | `tests/` |

## Quick start

```bash
pip install -e ".[dev]"          # or: set PYTHONPATH=src
python -m pytest -q

# 1. look at generated instances
python scripts/generate_instances.py --family population_game --sizes 24 48 --levels 1 2 --per-cell 2 --show

# 2. run an experiment with the mock model (no API calls)
python scripts/run_experiment.py --config configs/experiments/mock_scaling_v0.yaml --run-id demo

# 3. process: tidy table, metric tables, figures
python scripts/process_results.py --run data/raw_runs/mock_scaling_v0/demo

# 4. re-verify every stored certificate independently of the run
python scripts/verify_certificates.py --run data/raw_runs/mock_scaling_v0/demo
```

Other mock configs: `mock_scaling_v1.yaml` / `mock_transfer_v1.yaml` (all five
families), `mock_transfer_v0.yaml` (d0/d1/d2), `mock_compute_v0.yaml`
(low/medium/high). `pilot_anthropic_v0.yaml` is the milestone-2 pilot (20 trials,
4 calls each = 80 calls); run it with `--dry-run` first.

On Windows set `PYTHONIOENCODING=utf-8` before printing rendered problems.

## Pipeline

```
seed problem -> novel instances -> transfer instances -> model responses
             -> idea certificates -> deterministic verification -> analysis
```

### Families

A family owns the mathematics and never talks to a model. Each family exposes an
abstract *structure* (`structures/`) that verifiers consume, so a certificate is
verified against the mathematics, not against the surface text:

| family | structure | canonical idea | size n | ground truth |
|---|---|---|---|---|
| `domino_tiling` (seed: mutilated chessboard) | `tiling` (n x n grid, ~n/2 removed cells, dominoes) | checkerboard weighting `(-1)^(r+c)` | board side | colour imbalance (impossible) / bipartite matching (possible) |
| `population_game` (seed: chameleons) | `vector_game` (k classes, conserved total N, move vectors) | linear form `alpha . x (mod m)` | total N | exact BFS over the conserved-total state space |
| `sliding_puzzle` (seed: `fifteen_puzzle`) | `sliding_puzzle` (n x n tiles + blank) | sign(permutation) x (-1)^(blank row+col) | board side | parity rule (exact for >= 2 x 2; BFS-confirmed in tests) / random-walk witness |
| `subtraction_game` (seed: `nim`) | `subtraction_game` (3 heaps, remove 1..k) | XOR of (heap mod (k+1)) = 0 at losing positions | max heap size | Sprague-Grundy theorem (DP-confirmed in tests); every instance idea-bearing |
| `difference_board` (seed: `euclids_game`) | `difference_board` (numbers, write |a-b|; can T appear?) | all numbers are multiples of gcd | magnitude bound | closure = multiples of gcd up to max (exact) / greedy witness |

Instances whose answer is *impossible* are proved by the invariant
(`idea_bearing = True`). Instances whose answer is *possible* (about 35%, so a
model cannot always answer "impossible") are **balance controls** with an
explicit-construction witness; they are `idea_bearing = False` and are excluded
from `I(.)` but included in `S(.)`. Instances that are impossible for a reason the
canonical idea does not capture are rejected at generation time.

Generation is deterministic in `(family, version, size, seed)`; every instance
passes `family.sanity_check` (stored answer recomputed, canonical certificate
verifies iff idea-bearing, witness verifies).

### Transfer levels

| d | domino_tiling | population_game | sliding_puzzle | subtraction_game | difference_board |
|---|---|---|---|---|---|
| 0 classical | mutilated 8x8 chessboard | 13/15/17 chameleons | 14-15 puzzle | Nim 3/5/7 | Euclid's game 36/60 |
| 1 novel, same representation | grid + removed coordinates | coloured tokens, remove/add ops | n x n numbered tiles | heaps, remove 1..k | numbers on a board |
| 2 changed surface | random-labelled graph, perfect pairing | commutative string rewriting | tokens on a labelled graph | tokens on numbered tracks | rod lengths in a workshop |
| 3 different domain | not yet implemented | | | | |

Classical d0 statements are read from the `math-insight-examples` corpus
(`$IDEA_SEED_CORPUS` or `../math-insight-examples/data/problems`) when it is
present, with embedded fallbacks; provenance (corpus id, source URL) is stored
in `instance.parameters`.

d2 instances are the *same* structure as their d1 counterpart (paired by seed),
and the transformation is stored in `instance.transfer`. Levels are not assumed
comparable across families.

### Protocol (per trial, separate model calls)

* **A. free solve** - problem only. The prompt is tested against a forbidden-term
  list (`invariant`, `parity`, `coloring`, `certificate`, `modulo`, `bipartite`,
  `matching`, ...); only the answer format `FINAL ANSWER: possible|impossible` is imposed.
* **B. post-hoc formalization** - the finished free response is quoted verbatim
  and the model states the principle it used in the family's JSON certificate
  schema (or `{"certificate_type": "none"}`).
* **C. supplied-idea baseline** - the canonical idea in prose + the schema; measures `F`.
* **recognition probe** - "do you recognize this problem?" in its own call; a
  behavioural control, never ground truth for contamination.

### Certificates and verification

```json
{"certificate_type": "coloring_invariant", "weight_expr": "(r + c) % 2", "modulus": null}
{"certificate_type": "coloring_invariant", "weights": {"v17": 1, "v3": -1, ...}}
{"certificate_type": "modular_invariant", "coefficients": {"red": 1, "green": -1, "blue": 0}, "modulus": 3}
{"certificate_type": "modular_invariant", "expr": "(red - green) % 3"}
{"certificate_type": "explicit_construction", "tiles": [[[1,1],[1,2]], ...]}   /  {"moves": [1, 3, 2]}
```

Every verifier implements `normalize`, `verify_structure`, `verify_relevance`
and returns a `VerificationResult(valid, structural_valid, decision_relevant,
failure_reason, details, method, exact, is_idea, ...)`.

* `coloring_invariant`: every legal placement of every tile shape has the same
  weight (**local rule**, O(#placements)); relevance = no tile-count vector is
  consistent with the total weight. A constant weighting is structurally valid
  but not decision-relevant.
* `modular_invariant`: linear forms are checked against the move vectors only
  (**local rule**, size-independent); expression forms are checked exhaustively
  over the conserved-total state space (`method=exhaustive`) or sampled above
  200k states (`method=sampled, exact=False`).
* `permutation_parity`: for every edge of the grid graph the move changes the claimed parity by
  `delta_perm + w(u) + w(v)`, which must vanish (**local rule**); accepts `blank_term`,
  `blank_expr` or a `blank_weights` table (graph surface).
* `xor_invariant`: a proposed losing-position expression is checked **exhaustively** over the
  state box (terminal is losing; losing -> only winning successors; winning -> some losing
  successor). The theorem is never used by the verifier; keep max heap <= 64 (3 heaps) for speed.
* `gcd_invariant`: divisor divides every initial number and the operation preserves divisibility
  (**symbolic**, residue classes); relevance = target not a multiple. `divisor = 1` is degenerate.
* `explicit_construction`: a witness, `is_idea=False`; never counts as I = 1.

Alternative valid certificates count (`canonical_match=False`). Formulas from
models are evaluated with a whitelisted AST evaluator (`utils/safe_expr.py`).

### Idea extraction

```
free response -> candidate extraction -> structured certificate -> deterministic verifier -> I in {0,1}
```

Deterministic extractors per family (regex rules with recorded `rule_id` and
supporting span: checkerboard phrases, `(r + c) mod 2`, `(-1)^(r+c)`, listed
vertex classes, linear forms `2 red + blue mod 5`, "difference between ... modulo m",
plus any JSON certificate block). The extractor never invents content; the
verifier alone decides validity. `extraction/llm.py` adds an optional LLM
extractor that must quote a verbatim span for every field (unsupported fields
are discarded). Correct answers without a verified idea are labelled
`correct_unclassified` (or `correct_with_witness`), never "search".

### Models and compute

`ModelRunner.generate(prompt, config, context)` is the only interface the
experiment code sees. Compute conditions (`configs/compute_conditions.yaml`)
map a named level to explicit per-provider parameters (for Claude:
`thinking: {type: adaptive}` + `output_config.effort`). No tools, code
execution or browsing are enabled in any adapter.

The mock adapter (`configs/models/mock_*.yaml`) returns canned responses for
`correct_answer_correct_idea`, `correct_answer_no_idea`,
`wrong_answer_correct_idea`, `wrong_answer_no_idea`, `alternative_valid_idea`,
`malformed_certificate`; the `mixed`, `size_dependent` and `compute_dependent`
policies only exist to exercise the analysis code.

### Outputs

```
data/raw_runs/<experiment_id>/<run_id>/
    manifest.json     config, code commit, python, families, models, instance hashes
    instances.jsonl   full instance records
    trials.jsonl      one raw trial record per line (raw responses always retained)
    errors.jsonl      failed trials with tracebacks
data/processed/<experiment_id>/<run_id>/tidy.csv     one row per trial (see analysis/tidy.py)
data/results/<experiment_id>/<run_id>/metrics/*.csv  I_n, S_n, I_d, S_d, I_c, S_c, F, S_n_given_I1/I0, posthoc, recognition, outcome_counts (pooled + by family)
data/results/<experiment_id>/<run_id>/figures/*.png  fig1 I(n), fig2 I(d), fig3 I(c)+S(c), diagnostics
```

The trial record follows the schema in the project brief (`instance`, `model`,
`free_solve`, `idea_extraction`, `verification`, `posthoc_formalization`,
`supplied_idea_baseline`, `retrieval_control`, `metadata`). Result files are
never edited by hand; re-run `process_results.py` instead.

Tidy columns: `model family instance_id size transfer_level compute_level
compute_rank repetition idea_bearing ground_truth_answer answer_parsed
solution_correct idea_present idea_valid idea_canonical witness_valid
verification_method verification_exact posthoc_valid formalization_valid
recognized_classic outcome_category ...` - ready for mixed-effects logistic
regression with family and instance effects.

## Caveats and design decisions

* Pooled-by-size tables mix family-specific size scales; use the per-family
  tables/figures for `I(n)`. Pooling is meaningful for transfer level and compute.
* An unparsed `FINAL ANSWER` counts as incorrect in `S(.)`; it is also recorded
  as `unparsed_answer`.
* For `domino_tiling`, every domino-constant weighting on a connected region is
  an affine rescaling of the checkerboard, so "alternative" colourings match the
  canonical partition; genuinely different ideas (Hall-type arguments) are not yet
  supported certificate types and will show up as `correct_unclassified`.
* Deterministic extraction is conservative; condition B exists precisely so that
  free-solve ideas phrased in ways the extractor misses are still captured. The
  gap between free-solve `idea_valid` and `posthoc_valid` is itself a diagnostic.
* Hidden reasoning is not required anywhere; `ModelResponse.reasoning_trace` is
  optional and unused by the main measurements.

* `subtraction_game` is a family where the idea *is* the algorithm (nothing is
  left to execute once the nim-sum is known); every instance is idea-bearing and
  its size-scaling signature is expected to differ from the invariant families.
* The mock `size_dependent` policy uses raw size, so it is only informative for
  families with small size scales; it exists to exercise the analysis code.

## Next (milestone 2, remaining)

1. Run `pilot_anthropic_v0` (`pip install anthropic`, credentials in env), read
   every raw response, check extraction against post-hoc certificates, fix failure modes.
2. A monovariant / potential-function family (seeds `sign_flipping_rows_columns`,
   `candy_sharing_circle`) needs a decision-type question; a step-bound question
   ("can the process last more than B steps?") is the candidate design.
3. Add a d3 (different-domain) surface per family.

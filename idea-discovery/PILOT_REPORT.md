# Pilot 1 report — first real-model run

*2026-09-17. Run: `data/raw_runs/pilot_anthropic_v0/pilot1` (config `configs/experiments/pilot_anthropic_v0.yaml`).*

## What was run

| | |
|---|---|
| Model | `claude-opus-5`, adaptive thinking, effort `medium`, no tools |
| Instances | 5 families × 2 sizes × 2 novel (d1) instances = 20; 14 idea-bearing, 6 balance controls |
| Calls | 80 (free solve, post-hoc, supplied idea, recognition per instance), 0 errors |
| Tokens | 65k input, 106k output (of which 76k thinking); ≈ **$3.0** at list price; 20 min wall clock, sequential |
| Result | **20/20 correct answers.** Every idea-bearing instance was solved with a valid, verifier-checked idea (after the extractor fixes below: 13/14 from the free solve, 14/14 post-hoc, 14/14 supplied-idea). |

Every raw response was read by hand (`python scripts/inspect_run.py --run … --full`). The trials
are far too few for any curve; the point was to find failure modes before scaling. Six were found.

## Findings and fixes

### 1. Supplied-idea call on balance controls burned the whole budget (fixed)
On both *possible* sliding-puzzle instances the supplied-idea call spent all 16,000 output tokens
thinking and emitted nothing (`stop_reason: max_tokens`, 150–170 s each) — the model went looking
for an explicit move sequence because the supplied parity idea cannot certify possibility.
That is 32k wasted tokens out of 106k. The `F` and post-hoc metrics were already restricted to
idea-bearing instances, so these calls contributed nothing.
**Fix:** condition C is now skipped on non-idea-bearing instances (`supplied_idea_on_controls:
true` re-enables it), and structured calls (post-hoc, supplied idea) are capped separately
(`structured_max_output_tokens: 6000` in the pilot config; the free solve keeps its full budget).

### 2. Population game generated degenerate move sets (fixed, family version 0.1 → 0.2)
Both n=24 instances had two *mutually inverse* operations. The reachable set is then a line and a
plain integer invariant (`purple − black` is constant) decides the question without any modular
idea — the model found exactly that. A second degenerate case (all moves divisible by the modulus,
so every count is invariant) surfaced in the tests.
**Fix:** the generator now requires the moves to span the whole conservation hyperplane over ℚ
(`rank = k − 1`) and to have no common divisor. New instances have new ids/hashes, so the pilot
instances for this family are not comparable with future runs.

### 3. LaTeX hid the idea from the deterministic extractors (fixed)
Real responses write `$r+c$ is even`, `$b \bmod 3$`, `\oplus`, `\pmod{5}`, `**bold**`. The phrase
extractors missed several of these (e.g. the checkerboard colouring in both possible domino
instances; the nim-sum in trials 12–15).
**Fix:** extraction now runs on the raw text *and* on a LaTeX/markdown-normalized view
(`extraction.candidates.normalize_math_text`); candidates from the second view are tagged
`+tex_normalized`. The raw response is never altered.

### 4. XOR extractor read the wrong modulus (fixed)
It used only the first XOR mention and the first number after "residue"; `{0,1,2}` became
"modulus 0". Now every XOR mention is a site and every modulus ≥ 2 mentioned nearby is a
candidate; the verifier picks.

### 5. A valid idea the vocabulary could not express (new verifier `losing_set`)
On heaps (8, 24, 2) with moves 1..7 the model proved a first-player win with a *pairing
strategy*: empty the third heap, then keep every heap a multiple of 8. That is a correct idea,
but not a complete characterisation, so `xor_invariant` rejects it ((7,7,0) is outside the set
with no move into it). Added `losing_set`: a set L with terminal ∈ L, no move from L stays in L,
and every position one move away from L has a move back — checked exhaustively; relevance
requires the start to be in L or one move from L. The subtraction-game schema text and a
deterministic rule ("every heap … multiple of m") were added. This is the "alternative valid
idea" case the design anticipated; expect more of these in other families.

### 6. Sliding-puzzle blank term phrased as a cell colour (fixed)
"the colour of the cell containing the blank, (i+j) mod 2" was not recognised as the taxicab
term; the pattern set was extended. Note the general caveat: the sliding-puzzle deterministic
rules match sign/blank phrases anywhere in the response, not necessarily in the same argument.
Post-hoc agreement (14/14 here) is the cross-check; the LLM extractor with verbatim spans is
the principled upgrade if disagreement appears at scale.

## Observations that are not bugs (but matter for design)

* **Recognition is 100 % at d1.** All 20 instances were recognised as the classical problem
  (mutilated chessboard, chameleons, 15-puzzle, bounded Nim, blackboard gcd) with confidence
  0.45–0.95. d1 therefore provides no retrieval control; the transfer levels d2/d3 carry that
  burden and must be in every real experiment.
* **Possible sliding-puzzle instances are proved by the full theorem**, not by a move sequence
  (Johnson–Story / 3-cycle generation argument). The vocabulary cannot verify "the invariant is
  complete", so these land in `correct_unclassified`, as designed. Move-sequence witnesses are
  unrealistic for this family; treat its balance controls as accuracy-only.
* **Free-solve output is short at this difficulty**: 0.8k–6.4k tokens, thinking 0.2k–3.8k.
  Opus 5 at medium effort saturates these sizes; scaling/compute experiments need larger
  sizes and/or weaker models to see anything but ceilings.
* **Supplied-idea answers sometimes add unsolicited reasoning** (e.g. checking that the
  colouring gives no obstruction before returning a construction). Harmless for `F`, but the
  parser must keep taking the last JSON block.
* The equivalent-but-different formulations models use (relative permutation `T⁻¹∘S`,
  `r+2g mod 5` instead of the canonical form) were all verified correctly; `canonical_match`
  is False for several valid ideas, which is what it is for.

## Offline re-extraction

`python scripts/process_results.py --run <run> --reextract` re-runs the current extractors on
stored free responses and writes `trials_reextracted.jsonl` under `data/processed/…`; the raw
`trials.jsonl` is never modified. The pilot re-extracted: I = 13/14 idea-bearing (the miss is the
degenerate population instance of finding 2).

## Next

1. Re-run this pilot config once (new population instances; capped structured calls; expect
   ≈ $2) to confirm the fixes end-to-end, or go straight to a transfer pilot with d2 surfaces,
   which is where recognition and idea rates can actually diverge.
2. Then the scaling experiment with more instances per cell and a second, cheaper model.

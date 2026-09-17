# Project status and what the API would be used for

*Written 2026-09-17. Read this before enabling any API key.*

## 1. What this project is for

We want to answer one research question:

> When giving a language model more reasoning (more "thinking" / test-time compute)
> makes it better at mathematics, is that because it **discovers better mathematical
> ideas**, or because it **searches harder over individual solutions**?

To answer it we need to measure something sharper than "did the model get the
answer right". The pipeline measures whether the model found a **valid,
decision-relevant mathematical idea** — for example "colour the board like a
checkerboard; every domino covers one square of each colour" — and checks that
idea *mechanically*, with code, not with another language model as a judge.

Every problem the model sees has a known governing idea (an invariant, a parity
argument, a gcd argument, a nim-sum, ...). The model's answer is turned into a
small machine-checkable object called a *certificate*, and a deterministic
verifier decides whether that certificate

* actually holds under the rules of the problem (**structural validity**), and
* actually decides the question (**decision relevance**) — a "constant"
  invariant that holds trivially but proves nothing does not count.

From many such trials we get the curves

* `I(n)` — probability of a valid idea vs. problem size,
* `I(d)` — vs. how far the problem is disguised from its classical form,
* `I(c)` — vs. how much compute the model was given,

alongside ordinary accuracy `S(n)`, `S(d)`, `S(c)`.

## 2. Where things stand

**Built and tested, no API needed so far (133 automated tests pass):**

| Piece | State |
|---|---|
| 5 problem families, each with a generator for fresh, never-published instances | done: `domino_tiling`, `population_game`, `sliding_puzzle`, `subtraction_game`, `difference_board` |
| Exact verifiers for their ideas | done: coloring invariant, modular invariant, permutation parity, XOR/nim characterisation, gcd invariant, plus explicit-construction witnesses |
| Three presentations per family (d0 classical, d1 novel, d2 disguised surface) | done; d3 (different domain) not yet |
| The experimental protocol (free solve → post-hoc formalization → supplied-idea baseline → recognition probe) | done |
| A **mock model** that fakes answers so the whole pipeline could be exercised end to end | done; all demo runs under `data/raw_runs/mock_*` were produced by it, **not by any real model** |
| Raw logging, tidy tables, metrics with confidence intervals, figures | done |
| Adapter for Anthropic's API | written, **never executed** |

Seed problems come from the `math-insight-examples` corpus (the other agent's
repository); the three newest families load their classical statements from it.

**Not done:** no real language model has been run yet. That is the next step,
and it is the only step that needs an API key.

## 3. What the API is for, concretely

The API is used for exactly one thing: **asking a real model to solve the
generated problems**, so that we get real responses instead of mock ones.
Nothing else in the pipeline (instance generation, ground truth, verification,
analysis) ever calls the API.

Per problem instance the pipeline makes **four separate calls**:

1. **Free solve** — the problem statement only (no hints), asking for a rigorous
   solution ending in `FINAL ANSWER: ...`.
2. **Post-hoc formalization** — the model's own free-solve answer is sent back
   verbatim and it is asked to state, in a fixed JSON format, the principle it
   used (or "none").
3. **Supplied-idea baseline** — the problem plus the correct idea *in words*;
   the model is asked to write it in the JSON format. This measures whether a
   failure to produce a certificate is a failure to *have* the idea or a failure
   to *write it down*.
4. **Recognition probe** — "do you recognise this as a known problem?" (a
   contamination control; separate call so it cannot prime the solve).

The responses are stored verbatim in `data/raw_runs/<experiment>/<run>/trials.jsonl`
and never modified. Nothing is sent to the API except the problem text and the
model's own earlier answer; no data from your machine, no corpus files, no keys
in prompts.

**No tools are enabled**: the model gets no code execution, browsing or
calculators. That is deliberate — the research question is about reasoning,
and letting the model brute-force with code would blur "search" and "idea".

## 4. What the first run would be

Config: `configs/experiments/pilot_anthropic_v0.yaml`

| | |
|---|---|
| Model | `claude-opus-5` (changeable; e.g. `claude-sonnet-5` is cheaper) |
| Reasoning setting | adaptive thinking, effort `medium` |
| Instances | 5 families × 2 sizes × 2 instances = 20 |
| Calls | 20 × 4 = **80 API calls** |
| Tokens | prompts ~0.3–2k tokens; free-solve answers typically 1–5k; max output capped at 16k |
| Rough cost | a few US dollars at Opus 5 list prices ($5 / $25 per million input / output tokens); well under $1 with Sonnet 5 |
| Purpose | **not** a result — a pilot to read every response by hand and find failure modes (bad prompts, extraction misses, format problems) before anything is scaled up |

The run is resumable and writes each trial as soon as it finishes, so an
interruption never wastes completed calls. `--dry-run` prints the plan without
calling anything.

## 5. What would come after the pilot (each needs a decision from you)

* Fix whatever the pilot reveals, re-pilot if needed.
* Size-scaling experiment (more instances per size, several models).
* Transfer experiment (d0/d1/d2 for every family).
* Compute sweep (effort low / medium / high / max) on two models.

Each of these is a config file; none run without an explicit command. Costs
scale with (instances × models × conditions × 4 calls) and can be estimated
from the pilot's token usage, which is recorded per call.

## 6. How to enable the key when you decide to

* One-off, in a terminal: `export ANTHROPIC_API_KEY=sk-ant-...` (PowerShell:
  `$env:ANTHROPIC_API_KEY = "sk-ant-..."`), then
  `python scripts/run_experiment.py --config configs/experiments/pilot_anthropic_v0.yaml --run-id pilot1`.
* Inside a Claude Code session: `! export ANTHROPIC_API_KEY=sk-ant-...` at the
  prompt (the key then appears in that session's transcript).
* The key is read from the environment only; it is never written to disk by
  this code, and `.env` files are git-ignored.

# math-insight-examples

This repository collects mathematical problems whose solutions are driven by a
recognizable key idea. Each entry records the problem, the crucial observation,
an intuitive proof, the naive approach it replaces, and its source.

The organising question for every entry is:

> **What is the one mathematical observation that changes how this problem
> should be viewed?**

A typical entry: the *mutilated checkerboard* (an 8x8 board with two opposite
corners removed) cannot be tiled by dominoes. The naive approach is to try
arrangements; the key idea is that every domino covers one black and one white
square while the mutilated board has 32 squares of one colour and 30 of the
other. One global count rules out every arrangement at once.

The collection is intended as a stand-alone mathematical resource and as raw
material for future research on mathematical reasoning.

## Contents

```
math-insight-examples/
├── README.md
├── data/
│   ├── problems/<folder>/<id>.yaml   # one YAML file per problem (506 entries)
│   ├── index.jsonl                   # generated flat index
│   └── taxonomy.yaml                 # taxonomy of key ideas
├── sources/
│   ├── cut_the_knot.yaml             # every Cut-the-Knot page cited (generated)
│   └── bibliography.bib              # books, papers and websites cited
├── scripts/
│   ├── validate_entries.py           # schema validation + duplicate detection
│   ├── build_index.py                # regenerate data/index.jsonl
│   ├── build_sources.py              # regenerate sources/cut_the_knot.yaml
│   ├── build_docs.py                 # regenerate docs/TAXONOMY.md
│   ├── summarize_repository.py       # statistics (docs/SUMMARY.md)
│   └── common.py
└── docs/
    ├── DATA_FORMAT.md                # the entry schema
    ├── TAXONOMY.md                   # the taxonomy, rendered with counts
    └── SUMMARY.md                    # generated statistics and entry list
```

Folders under `data/problems/` follow the *main idea* of each entry:
`invariants`, `parity`, `coloring`, `monovariants`, `symmetry`, `extremal`,
`representation_change`, `combinatorial` (pigeonhole, bijection, double
counting, probabilistic), `geometric`, `algebraic`, `number_theoretic`,
`dynamical` (circle rotations, periodicity, attracting structure) and `other`
(induction, recursion, structural obstruction, strategy stealing, auxiliary
objects).

## Entry format

Each problem is a YAML file (see [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md)):

```yaml
id: mutilated_checkerboard
title: Mutilated Checkerboard
source: {name: Cut-the-Knot, url: ..., original_title: ..., accessed: 2026-09-16}
problem: {statement: ..., domain: tiling, answer: impossible}
key_idea: {name: checkerboard coloring, category: coloring_invariant, summary: ...}
intuitive_proof: {explanation: ...}
reasoning_structure:
  naive_approach: ...        # what one would naturally try first
  crucial_observation: ...   # what to notice instead
  why_it_simplifies: ...     # why that observation collapses the problem
aliases: [...]
related: [...]
tags: [...]
quality: {clarity_of_key_idea: high, elegance: high, naive_search_contrast: high, pedagogical_value: high}
familiarity: {famous: true, likely_widely_known: true}
```

The `reasoning_structure` block is the heart of the repository: it records the
*change of viewpoint*, not just the proof.

## Taxonomy

Ideas are classified in [data/taxonomy.yaml](data/taxonomy.yaml) (rendered in
[docs/TAXONOMY.md](docs/TAXONOMY.md)). Top-level categories:

invariant (parity, modular, coloring, permutation, algebraic, group,
geometric, conservation law) · monovariant / potential function · symmetry
(pairing strategy, involution / pairing-off) · extremal principle / infinite
descent · pigeonhole · representation change
(geometric, graph, algebraic encoding, coordinate transformation, isomorphism,
combinatorial interpretation) · decomposition · recursive structure ·
induction · contradiction via structural obstruction / strategy stealing ·
bijection · double counting · probabilistic argument · geometric
transformation (reflection, rotation, unfolding, continuous deformation) ·
number-theoretic structure · dynamical systems (circle rotation, finite-state
periodicity, attracting structure) · auxiliary object · algebraic identity ·
other.

Every entry has exactly one main category and any number of tags. Not every
problem is an invariant problem; the category names the observation that
makes the problem collapse.

## Sources

The first sweep covered [Cut-the-Knot](https://www.cut-the-knot.org/)
(invariants, parity, colouring, Nim, Fifteen Puzzle, Peg Solitaire, Euclid's
Game, Fif, chocolate breaking, Solitaire on a Circle, Splitting Piles, Sums
and Products, Calendar Magic, Counting Diagonals, Ford Circles, Changing
Colors, Plus or Minus, Squares and Circles, and more; 88 entries have it as
primary source and 128 cite it). Later sweeps added classic olympiad
problems (IMO 1959-1988, Putnam), Engel's *Problem-Solving Strategies* (64
primary), Aigner and Ziegler's *Proofs from THE BOOK* (25 primary),
*Mathematical Circles (Russian Experience)*, Matousek's *Thirty-three
Miniatures*, *Winning Ways*, *Concrete Mathematics*, Feller, Mosteller,
Gardner, Dudeney, Winkler, Polya, Coxeter and Greitzer, and Wikipedia /
MathWorld articles (Wikipedia is the primary URL for 311 entries, usually
with a book reference under `additional_sources`). Topics range over
invariants and games, combinatorics, graph theory, number theory, algebra,
inequalities, geometry, analysis, probability and dynamical systems (circle
rotations, Benford's law, finite-state periodicity, attractors).

Every entry records a source name, URL, original title where available,
author where known, and access date. Additional appearances of the same
problem are listed under `additional_sources`. Only URLs and short summaries
in our own words are stored; no source text is copied. All URLs were checked
to resolve on the access date (the AoPS wiki blocks automated checks but the
pages are standard).

## Scripts

```bash
python scripts/validate_entries.py      # schema checks + duplicate candidates (exit 1 on error)
python scripts/build_index.py           # data/index.jsonl
python scripts/build_sources.py         # sources/cut_the_knot.yaml
python scripts/build_docs.py            # docs/TAXONOMY.md
python scripts/summarize_repository.py --write   # docs/SUMMARY.md
```

Requirements: Python 3.10+ and PyYAML.

### Duplicate detection

`validate_entries.py` flags pairs of entries that share a normalised title or
alias, share a source URL while having overlapping statements, or have highly
similar problem statements / key-idea summaries. Known distinct-but-related
pairs are declared with `related:` in both entries, which suppresses the
warning and doubles as a cross-reference. Many classic problems go by several
names; new names should be added as `aliases` on the canonical entry rather
than as new files.

## Adding an entry

1. Pick the main idea and find its `folder` in `data/taxonomy.yaml`.
2. Create `data/problems/<folder>/<id>.yaml` following an existing entry.
3. Write the statement and proof in your own words; record the source URL and
   access date.
4. Run `python scripts/validate_entries.py`, then the build scripts.

A good entry has an obvious naive approach, a distinct observation that
bypasses it, and a proof that is substantially simpler than the naive one.
Problems that are mainly calculation are out of scope.

## Status

Milestone 1 (10 representative entries covering distinct kinds of insight),
milestone 2 (50+ curated entries across the taxonomy) and the extended
target of 500+ entries (currently 506, all passing `validate_entries.py
--strict` with no duplicate candidates) are complete;
see [docs/SUMMARY.md](docs/SUMMARY.md) for the current counts per category,
source and domain.

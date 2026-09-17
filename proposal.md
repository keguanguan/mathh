# Search or Insight?

## A Mechanically Verifiable Study of Mathematical Idea Discovery in Language Models

### 1. Question

Language models solve increasingly difficult mathematical problems, especially when given more test-time computation. But *why* does additional reasoning help?

One possibility is **search**: the model explores more candidate steps, calculations, or proof paths until one succeeds.

Another possibility is **idea discovery**: the model recognizes a mathematical structure—an invariant, potential function, symmetry, transformation, or equivalent representation—that makes a whole class of instances easy.

Final-answer accuracy cannot distinguish these mechanisms.

This paper asks:

**Does test-time reasoning help language models discover the governing mathematical idea, or mainly help them search and execute once an idea is available?**

### 2. Central hypothesis

Search and idea discovery should have different empirical signatures.

Consider a family of problems indexed by size \(n\), where the same mathematical idea solves every instance.

Once the governing idea has been discovered, increasing \(n\) should have relatively little effect:

$$
S(n\mid I=1)\approx \text{constant},
$$

where \(I=1\) means that the model produced a verified idea certificate.

Without such an idea, increasingly large instances require more instance-level reasoning or search, so we predict

$$
S(n\mid I=0)\downarrow
$$

as \(n\) grows.

Idea discovery should also **transfer**. A model that has identified the underlying mathematical structure should recognize it in novel instances and, more importantly, in problems with different surface descriptions but the same structure.

The paper therefore tests idea discovery through two primary signatures:

$$
\boxed{\text{scaling across instance size}}
\qquad\text{and}\qquad
\boxed{\text{transfer across representations}}.
$$

### 3. What counts as finding an idea?

We do not ask another language model whether an answer “looks insightful.”

Instead, whenever possible, the model must produce a **formal idea certificate**.

Examples include an invariant

$$
\phi(T(s))=\phi(s),
$$

a monovariant

$$
V(T(s))\ge V(s),
$$

a coloring together with its balance rule, a modular quantity, a permutation invariant, a potential function, or an explicit transformation between two representations.

The certificate is verified mechanically over the legal operations of the problem.

For example, saying only

> “Use parity”

does not count.

Providing a quantity whose parity is preserved under every legal move and whose initial and target values differ does.

Thus,

$$
I=
\begin{cases}
1,&\text{a proposed mathematical idea is mechanically verified},\\
0,&\text{otherwise}.
\end{cases}
$$

This gives a ground-truth signal for idea discovery without an LLM judge.

### 4. Problem families

We use classical “one-idea” problems, including the Cut-the-Knot collection, as **seeds rather than test instances**.

For each seed we identify the underlying mathematical structure and generate a family of new problems.

The collection spans ideas such as parity, modular invariants, conservation laws, potential functions, gcd preservation, XOR, permutation parity, group-valued invariants, symmetry, and representation changes.

Each family contains three evaluation regimes:

**Classic.** The well-known original problem.

**Novel.** Newly generated instances governed by the same idea.

**Transfer.** Problems with substantially different surface form but the same underlying mathematical structure.

The primary results use Novel and Transfer. Classic instances are primarily a retrieval control.

### 5. Controlling for memorization

Performance on famous problems such as the mutilated checkerboard, Nim, or the Fifteen Puzzle cannot by itself demonstrate idea discovery.

We therefore separately measure whether models recognize classical problems or their source. Recognition is probed in a separate run so that the probe does not prime the solving trial.

Results on classical instances are reported separately for recognized and unrecognized problems.

The central claim does not depend on performance on famous problems.

Instead, the main question is whether the same idea appears on **newly generated and structurally transferred instances**.

### 6. Scaling experiment

For every family, we generate instances of increasing size

$$
n_1<n_2<\cdots<n_k
$$

while keeping the governing idea fixed.

Sizes are chosen so that direct enumeration or brute-force search rapidly becomes infeasible within the model's available inference budget.

We measure separately

$$
I(n)=P(\text{verified idea}\mid n)
$$

and

$$
S(n)=P(\text{correct solution}\mid n).
$$

Most importantly, we condition solution success on whether the idea was found:

$$
S(n\mid I=1),
\qquad
S(n\mid I=0).
$$

If these curves separate strongly, they provide a direct behavioral signature of idea-based versus search-based solving.

### 7. Transfer experiment

Transfer is the strongest test of idea discovery.

For each mathematical structure, we construct increasing transfer distances:

$$
\text{classic}
\rightarrow
\text{new instance}
\rightarrow
\text{new presentation}
\rightarrow
\text{new problem domain}.
$$

For example, checkerboard parity may transfer from a tiling problem to a novel bipartite covering problem.

We measure

$$
I(d)=P(\text{verified idea}\mid\text{transfer distance }d).
$$

A model that merely retrieves a memorized solution may succeed on the original problem but fail rapidly under transfer.

A model with accessible structural knowledge should retain substantially more of its idea-discovery rate.

### 8. When does the idea appear?

For models with observable reasoning traces, we record the first location at which the eventual verified idea appears:

$$
L_{\text{idea}}
=
\text{token position of first valid appearance of the idea}.
$$

This gives **first-mention latency**.

We also record how much unsuccessful reasoning occurs before that point.

An idea that appears before substantial exploration is behaviorally different from one that appears only after many failed constructions.

Because hidden reasoning is unavailable for some API models, first-mention latency is a secondary analysis restricted to models with comparable observable traces. The primary cross-model results rely on certificate success, scaling, and transfer.

### 9. Hint intervention

Hints use a standardized hierarchy derived from the idea taxonomy rather than bespoke clues for individual puzzles.

The progression is from weak structural information to increasingly specific information about the relevant mathematical class:

$$
\text{no structural hint}
\rightarrow
\text{look for a global structure}
\rightarrow
\text{idea class}
\rightarrow
\text{specific mathematical structure}.
$$

We measure the amount of intervention necessary before a valid idea certificate appears.

This provides a controlled measure of **idea accessibility** without requiring subjective judgments of elegance.

### 10. Alternative ideas

A correct solution without the benchmark's canonical idea is not automatically labeled “search.”

Models are allowed to propose alternative formal certificates.

If an alternative certificate verifies, it counts as successful idea discovery even if it differs from the expected solution.

Correct solutions for which no certificate in the current formal language can be verified are analyzed separately rather than automatically classified as search.

This avoids confusing genuinely novel mathematical arguments with brute force.

### 11. Test-time scaling

We then vary available inference computation and ask where the gains come from.

For each compute level \(c\), we measure

$$
S(c)=P(\text{correct solution}),
$$

and

$$
I(c)=P(\text{verified idea}).
$$

Several outcomes are possible.

If both increase together, additional computation helps models discover better representations.

If

$$
S(c)\uparrow
\qquad\text{while}\qquad
I(c)\approx\text{constant},
$$

then test-time scaling primarily improves search or execution.

If idea discovery increases but only after long traces, additional computation may be converting search into eventual structural discovery.

The experiment therefore decomposes the benefit of test-time compute into

$$
\boxed{\text{idea discovery}}
\quad+\quad
\boxed{\text{execution/search after discovery}}.
$$

### 12. Main measurements

The paper reports the full curves rather than reducing mathematical insight to one arbitrary score.

The primary quantities are

$$
I(n),\qquad
S(n\mid I=1),\qquad
S(n\mid I=0),
$$

for instance scaling,

$$
I(d)
$$

for structural transfer,

$$
I(c),\qquad S(c)
$$

for test-time scaling, and, where available,

$$
L_{\text{idea}}
$$

for first-mention latency.

Hint sensitivity and retrieval controls provide additional diagnostics.

### 13. Artifacts

The work releases three main artifacts.

**Idea-family benchmark.**
A collection of generated mathematical problem families derived from classical insight problems, with size sweeps, novel instances, representation changes, and structural-transfer tasks.

**Machine-verifiable idea certificates.**
A library of formal certificate schemas and checkers for invariants, monovariants, colorings, modular quantities, algebraic invariants, potential functions, and related mathematical structures.

**Idea-discovery evaluation suite.**
Tools for measuring idea discovery, instance-size scaling, transfer, test-time compute scaling, retrieval sensitivity, hint sensitivity, and first-mention latency.

### 14. Contribution

Current mathematical benchmarks primarily ask:

**Can the model eventually solve the problem?**

We ask a different question:

**Did the model discover a mathematical structure that makes the problem easy, and when did that happen?**

By constructing families where search difficulty grows while the governing idea remains unchanged, and by requiring that the proposed idea itself be mechanically verified, we obtain a controlled way to distinguish increased search from increased mathematical idea discovery.

The central empirical question is:

$$
\boxed{
\text{Does test-time scaling make models better at finding ideas,
or mainly better at searching once the ideas are absent?}
}
$$

This distinction is relevant to mathematical reasoning, inference scaling, model training, and the development of systems that generalize mathematical ideas rather than merely solve increasingly many individual problems.

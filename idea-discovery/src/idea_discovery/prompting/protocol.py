"""Prompt construction for the core protocol.

Condition A (free solve)        : problem only. No hint about the idea class.
Condition B (post-hoc)          : the finished free response + a request to
                                  state the principle used, in the family's
                                  certificate schema. Separate call; the free
                                  response is quoted verbatim, never altered.
Condition C (supplied idea)     : problem + canonical idea in prose + request
                                  to formalize it as a certificate.
Retrieval control (recognition) : "do you recognize this problem?" in its own
                                  call so it cannot prime the free solve.

The free-solve prompt is checked by tests against a list of forbidden terms
(FORBIDDEN_FREE_SOLVE_TERMS) so that the research question is not prompted
away.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..families.base import CanonicalIdea, Instance, ProblemFamily

# Terms that must never appear in the free-solve prompt (case-insensitive).
FORBIDDEN_FREE_SOLVE_TERMS = (
    "invariant",
    "parity",
    "coloring",
    "colouring",
    "checkerboard",
    "chessboard colour",
    "potential function",
    "monovariant",
    "certificate",
    "governing idea",
    "key idea",
    "proof strategy",
    "solution strategy",
    "modulo",
    "mod",
    "bipartite",
    "matching",  # the graph surface says "perfect pairing"; the term 'matching' is a hint towards Hall/bipartite theory
    "hint",
    "nim",
    "xor",
    "gcd",
    "greatest common divisor",
    "divisib",
    "inversion",
    "permutation",
    "transposition",
)

FREE_SOLVE_SYSTEM = "You are a careful mathematician. Answer questions rigorously and do not use tools, code execution or external resources."

_FREE_SOLVE_TEMPLATE = """Solve the following problem. Give a complete, rigorous justification of your answer.

{problem}

{answer_instruction}"""

_POSTHOC_TEMPLATE = """Below is a problem and a solution that was written for it.

PROBLEM:
{problem}

SOLUTION (verbatim):
<<<
{response}
>>>

Identify the key mathematical principle that this solution relies on, if any, and state it in machine-checkable form. Do not solve the problem again and do not add new arguments: only formalize what the solution above actually used. If the solution did not use any such principle, say so with the "none" schema.

{schema}

Output exactly one JSON object inside a ```json code block."""

_SUPPLIED_IDEA_TEMPLATE = """Below is a problem together with the key idea that solves it.

PROBLEM:
{problem}

KEY IDEA:
{idea}

Your task is not to solve the problem from scratch but to formalize the key idea above in machine-checkable form, filling in any concrete details (such as the exact function, weights or coefficients) that the idea requires for this specific problem.

{schema}

Output exactly one JSON object inside a ```json code block."""

_RECOGNITION_TEMPLATE = """Here is a mathematical problem.

{problem}

Do you recognize this as a known or classical problem (or a direct variant of one)? Do not solve it. Respond with exactly one JSON object inside a ```json code block, of the form
{{"recognized": true or false, "proposed_name": "<name of the known problem, or null>", "proposed_source": "<where it is from, e.g. a competition, book or folklore, or null>", "confidence": <number between 0 and 1>}}"""


@dataclass
class Prompt:
    condition: str  # free_solve | posthoc | supplied_idea | recognition
    text: str
    system: str | None = None


def free_solve_prompt(family: ProblemFamily, instance: Instance, format: str = "text") -> Prompt:
    problem = family.render_problem(instance, format=format)
    text = _FREE_SOLVE_TEMPLATE.format(problem=problem, answer_instruction=family.answer_instruction())
    return Prompt("free_solve", text, FREE_SOLVE_SYSTEM)


def posthoc_prompt(family: ProblemFamily, instance: Instance, free_response: str, format: str = "text") -> Prompt:
    problem = family.render_problem(instance, format=format)
    text = _POSTHOC_TEMPLATE.format(problem=problem, response=free_response, schema=family.certificate_schema_text(instance))
    return Prompt("posthoc", text, FREE_SOLVE_SYSTEM)


def supplied_idea_prompt(family: ProblemFamily, instance: Instance, idea: CanonicalIdea, format: str = "text") -> Prompt:
    problem = family.render_problem(instance, format=format)
    text = _SUPPLIED_IDEA_TEMPLATE.format(problem=problem, idea=idea.prose, schema=family.certificate_schema_text(instance))
    return Prompt("supplied_idea", text, FREE_SOLVE_SYSTEM)


def recognition_prompt(family: ProblemFamily, instance: Instance, format: str = "text") -> Prompt:
    problem = family.render_problem(instance, format=format)
    return Prompt("recognition", _RECOGNITION_TEMPLATE.format(problem=problem), FREE_SOLVE_SYSTEM)


# terms matched as word prefixes (so that plurals and derived forms are caught too)
_PREFIX_TERMS = {"invariant", "parity", "coloring", "colouring", "checkerboard", "certificate", "divisib", "inversion", "permutation", "transposition", "monovariant", "hint"}


def forbidden_terms_present(text: str, terms=FORBIDDEN_FREE_SOLVE_TERMS) -> list[str]:
    """Forbidden terms occurring in ``text`` as whole words (or word prefixes for _PREFIX_TERMS)."""
    low = text.lower()
    found = []
    for t in terms:
        suffix = "" if t in _PREFIX_TERMS else r"(?![a-z])"
        if re.search(r"(?<![a-z])" + re.escape(t) + suffix, low):
            found.append(t)
    return found

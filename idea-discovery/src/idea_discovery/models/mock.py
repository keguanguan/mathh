"""Mock model adapter with canned behaviours for end-to-end pipeline tests.

Behaviours (chosen per trial, identically for every condition of that trial):

    correct_answer_correct_idea   right answer, canonical idea stated in prose
    correct_answer_no_idea        right answer, no reusable idea in the text
    wrong_answer_correct_idea     canonical idea stated but the wrong final answer
    wrong_answer_no_idea          wrong answer and no idea
    alternative_valid_idea        a valid non-canonical certificate when the family has one
    malformed_certificate         idea gestured at, but every structured output is broken JSON

Policies: a fixed behaviour name, ``mixed`` (uniform over behaviours),
``size_dependent`` (P(idea) decreases with instance size) or
``compute_dependent`` (P(idea) increases with the compute-condition rank).
The size/compute policies exist only so that the analysis code can be tested
on data with known structure; they encode no claim about real models.
"""
from __future__ import annotations

import json
import random
from typing import Optional

from ..utils.hashing import derive_seed
from .base import ComputeCondition, GenerationConfig, ModelResponse, ModelRunner, utc_now

BEHAVIORS = (
    "correct_answer_correct_idea",
    "correct_answer_no_idea",
    "wrong_answer_correct_idea",
    "wrong_answer_no_idea",
    "alternative_valid_idea",
    "malformed_certificate",
)
POLICIES = BEHAVIORS + ("mixed", "size_dependent", "compute_dependent")


def _json_block(obj) -> str:
    return "```json\n" + json.dumps(obj, indent=2) + "\n```"


_BROKEN_BLOCK = '```json\n{"certificate_type": "coloring_invariant", "weight_expr": "(r + c", "modulus": \n```'


class MockModelRunner(ModelRunner):
    provider = "mock"

    def __init__(self, model: str = "mock-v1", policy: str = "mixed", seed: int = 0, size_slope: float = 0.05, size_intercept: float = 1.1, compute_probs=(0.3, 0.5, 0.7), formalization_success: float = 1.0, **_ignored):
        if policy not in POLICIES:
            raise ValueError(f"unknown mock policy {policy!r}; choose from {POLICIES}")
        self.model = model
        self.policy = policy
        self.seed = seed
        self.size_slope = size_slope
        self.size_intercept = size_intercept
        self.compute_probs = tuple(compute_probs)
        self.formalization_success = formalization_success

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model, "policy": self.policy, "seed": self.seed}

    # -- behaviour selection --------------------------------------------
    def behavior_for(self, context: dict) -> str:
        if self.policy in BEHAVIORS:
            return self.policy
        instance = context["instance"]
        compute: Optional[ComputeCondition] = context.get("compute_condition")
        rng = random.Random(derive_seed(self.seed, instance.instance_id, context.get("repetition", 0), compute.name if compute else None))
        if self.policy == "mixed":
            return rng.choice(BEHAVIORS)
        if self.policy == "size_dependent":
            p_idea = min(0.95, max(0.05, self.size_intercept - self.size_slope * instance.size))
            p_correct_given_no_idea = max(0.2, 0.9 - self.size_slope * instance.size)
        else:  # compute_dependent
            rank = compute.rank if compute is not None and compute.rank is not None else 0
            p_idea = self.compute_probs[min(rank, len(self.compute_probs) - 1)]
            p_correct_given_no_idea = 0.5
        if rng.random() < p_idea:
            return "correct_answer_correct_idea" if rng.random() < 0.95 else "wrong_answer_correct_idea"
        return "correct_answer_no_idea" if rng.random() < p_correct_given_no_idea else "wrong_answer_no_idea"

    # -- generation ------------------------------------------------------
    def generate(self, prompt: str, config: GenerationConfig, context: Optional[dict] = None) -> ModelResponse:
        if context is None or "instance" not in context or "condition" not in context or "family" not in context:
            raise ValueError("MockModelRunner needs context with 'instance', 'family' and 'condition'")
        behavior = self.behavior_for(context)
        condition = context["condition"]
        if condition == "free_solve":
            text = self._free_solve(context, behavior)
        elif condition == "posthoc":
            text = self._posthoc(context, behavior)
        elif condition == "supplied_idea":
            text = self._supplied_idea(context, behavior)
        elif condition == "recognition":
            text = self._recognition(context)
        else:
            raise ValueError(f"unknown condition {condition!r}")
        return ModelResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            config=config.to_dict(),
            usage={"input_tokens": len(prompt.split()), "output_tokens": len(text.split())},
            timestamp=utc_now(),
            latency_s=0.0,
            raw={"mock_behavior": behavior, "policy": self.policy},
        )

    def _idea(self, context: dict, behavior: str):
        family, instance = context["family"], context["instance"]
        if behavior == "alternative_valid_idea":
            alt = family.alternative_idea(instance)
            if alt is not None:
                return alt
        return family.canonical_idea(instance)

    def _free_solve(self, context: dict, behavior: str) -> str:
        family, instance = context["family"], context["instance"]
        truth = instance.ground_truth["answer"]
        options = list(family.answer_options)
        wrong = next(o for o in options if o != truth)
        answer = wrong if behavior.startswith("wrong") else truth
        parts = ["Let me think about the structure of this problem."]
        if behavior in ("correct_answer_correct_idea", "wrong_answer_correct_idea", "alternative_valid_idea"):
            idea = self._idea(context, behavior)
            parts.append(idea.explicit_prose or idea.prose)
            witness = instance.ground_truth.get("witness")
            if truth == "possible" and witness is not None and not behavior.startswith("wrong"):
                parts.append("Here is an explicit construction:\n" + _json_block(witness))
            parts.append(f"Therefore the answer is: {answer}.")
        elif behavior == "malformed_certificate":
            parts.append("There is a weighting argument here, which I would write as follows:\n" + _BROKEN_BLOCK)
            parts.append(f"So the answer is {answer}.")
        else:
            parts.append("I tried a large number of configurations by hand and looked for a pattern. After exploring many cases I could not find anything conclusive, so I will go with my best guess.")
        parts.append(f"FINAL ANSWER: {answer}")
        return "\n\n".join(parts)

    def _posthoc(self, context: dict, behavior: str) -> str:
        if behavior == "malformed_certificate":
            return "The principle is a weighting of the cells.\n" + _BROKEN_BLOCK
        if behavior in ("correct_answer_correct_idea", "wrong_answer_correct_idea", "alternative_valid_idea"):
            return "The solution relied on the following principle.\n" + _json_block(self._idea(context, behavior).certificate)
        return "The solution did not use a general principle; it was case analysis.\n" + _json_block({"certificate_type": "none"})

    def _supplied_idea(self, context: dict, behavior: str) -> str:
        family, instance = context["family"], context["instance"]
        if behavior == "malformed_certificate":
            return _BROKEN_BLOCK
        if self.formalization_success < 1.0:
            rng = random.Random(derive_seed(self.seed, "formalization", instance.instance_id, context.get("repetition", 0)))
            if rng.random() > self.formalization_success:
                return "I could not turn the idea into the required form.\n" + _json_block({"certificate_type": "none"})
        return "Formalizing the supplied idea:\n" + _json_block(family.canonical_idea(instance).certificate)

    def _recognition(self, context: dict) -> str:
        instance = context["instance"]
        if instance.transfer_level == 0:
            name = instance.parameters.get("name", "classical problem")
            return _json_block({"recognized": True, "proposed_name": name, "proposed_source": "folklore / competition classic", "confidence": 0.9})
        return _json_block({"recognized": False, "proposed_name": None, "proposed_source": None, "confidence": 0.2})

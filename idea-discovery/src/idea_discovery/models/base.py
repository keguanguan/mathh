"""Model runner interface.

Experiment code only ever sees :class:`ModelRunner`, :class:`GenerationConfig`
and :class:`ModelResponse`. Provider-specific parameters live in adapters
(``models/mock.py``, ``models/anthropic_runner.py``, ...) and in
:class:`ComputeCondition`, which maps one named compute level onto each
provider's own control (thinking budget, reasoning effort, ...).

The primary experiments run without tools, code execution or browsing; an
adapter must not enable any of these unless the config says so explicitly.
"""
from __future__ import annotations

import datetime as _dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional


@dataclass
class GenerationConfig:
    temperature: float = 0.0
    max_output_tokens: int = 4096
    reasoning_setting: Optional[dict] = None  # provider-specific compute control (from ComputeCondition)
    seed: Optional[int] = None
    system: Optional[str] = None
    tools_enabled: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        from ..utils.serialization import to_jsonable

        return to_jsonable(self)


@dataclass
class ModelResponse:
    text: str
    provider: str
    model: str
    config: dict
    usage: dict = field(default_factory=dict)
    timestamp: str = ""
    latency_s: float = 0.0
    raw: dict = field(default_factory=dict)  # provider payload (json-able); always retained
    reasoning_trace: Optional[str] = None  # visible reasoning trace when the provider returns one
    error: Optional[str] = None

    def to_dict(self) -> dict:
        from ..utils.serialization import to_jsonable

        return to_jsonable(self)


@dataclass
class ComputeCondition:
    """A named test-time-compute level with explicit per-provider parameters."""

    name: str
    provider_parameters: dict[str, dict] = field(default_factory=dict)
    rank: Optional[int] = None  # ordinal position (low < medium < high) for plotting

    def for_provider(self, provider: str) -> Optional[dict]:
        if provider in self.provider_parameters:
            return dict(self.provider_parameters[provider])
        if "default" in self.provider_parameters:
            return dict(self.provider_parameters["default"])
        return None

    def to_dict(self) -> dict:
        return {"name": self.name, "provider_parameters": self.provider_parameters, "rank": self.rank}


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class ModelRunner(ABC):
    provider: ClassVar[str]
    model: str
    supports_visible_reasoning: ClassVar[bool] = False

    @abstractmethod
    def generate(self, prompt: str, config: GenerationConfig, context: Optional[dict] = None) -> ModelResponse:
        """Generate one completion.

        ``context`` carries experiment metadata (instance, condition, family,
        repetition, compute condition). Real adapters must ignore it except for
        logging; the mock adapter uses it to produce canned responses.
        """

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model}

    def resolve_config(self, base: GenerationConfig, compute: Optional[ComputeCondition]) -> GenerationConfig:
        """Attach this provider's parameters for the given compute condition."""
        cfg = GenerationConfig(**{**base.__dict__})
        if compute is not None:
            params = compute.for_provider(self.provider)
            if params is None:
                raise ValueError(f"compute condition {compute.name!r} defines no parameters for provider {self.provider!r}")
            cfg.reasoning_setting = params
        return cfg

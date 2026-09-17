"""Build model runners from config dicts (configs/models/*.yaml).

    name: mock_mixed
    provider: mock
    model: mock-v1
    parameters: {policy: mixed, seed: 0}
"""
from __future__ import annotations

from typing import Callable

from .base import ModelRunner
from .mock import MockModelRunner

_PROVIDERS: dict[str, Callable[..., ModelRunner]] = {}


def register_provider(name: str):
    def deco(factory):
        _PROVIDERS[name] = factory
        return factory

    return deco


register_provider("mock")(lambda model, **params: MockModelRunner(model=model, **params))


def build_runner(model_config: dict) -> ModelRunner:
    provider = model_config["provider"]
    if provider not in _PROVIDERS:
        if provider == "anthropic":
            from .anthropic_runner import AnthropicRunner  # lazy: optional dependency

            register_provider("anthropic")(lambda model, **params: AnthropicRunner(model=model, **params))
        else:
            raise KeyError(f"unknown provider {provider!r}; available: {sorted(_PROVIDERS)}")
    return _PROVIDERS[provider](model=model_config["model"], **(model_config.get("parameters") or {}))


def available_providers() -> list[str]:
    return sorted(set(_PROVIDERS) | {"anthropic"})

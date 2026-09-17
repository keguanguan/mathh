"""Anthropic (Claude) model adapter - milestone-2 provider.

Requires ``pip install anthropic`` and credentials in the environment
(``ANTHROPIC_API_KEY`` or an ``ant auth login`` profile). Not exercised by the
unit tests; the mock adapter covers the pipeline.

Compute conditions map onto Claude's own controls through
``ComputeCondition.provider_parameters["anthropic"]``, which is passed
through verbatim as request parameters, e.g.

    {thinking: {type: adaptive}, output_config: {effort: low}}

Current Claude models (Opus 5 / Sonnet 5 / 4.7+) reject ``budget_tokens`` and
sampling parameters (``temperature`` etc.); ``send_sampling_params`` therefore
defaults to False. No tools are ever declared: the primary experiment runs
without code execution or browsing.
"""
from __future__ import annotations

import time
from typing import Optional

from .base import GenerationConfig, ModelResponse, ModelRunner, utc_now

DEFAULT_MODEL = "claude-opus-5"


class AnthropicRunner(ModelRunner):
    provider = "anthropic"
    supports_visible_reasoning = True  # summarized thinking when display="summarized" is requested

    def __init__(self, model: str = DEFAULT_MODEL, send_sampling_params: bool = False, max_retries: int = 3, timeout_s: float = 1800.0, stream: bool = True, **_ignored):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install anthropic (or idea-discovery[anthropic]) to use the Anthropic adapter") from e
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(max_retries=max_retries, timeout=timeout_s)
        self.model = model
        self.send_sampling_params = send_sampling_params
        self.stream = stream

    def describe(self) -> dict:
        return {"provider": self.provider, "model": self.model, "send_sampling_params": self.send_sampling_params, "stream": self.stream}

    def generate(self, prompt: str, config: GenerationConfig, context: Optional[dict] = None) -> ModelResponse:
        if config.tools_enabled:
            raise ValueError("tool use is not implemented for the primary experiment; run tool-assisted conditions as a separate adapter")
        kwargs: dict = {
            "model": self.model,
            "max_tokens": config.max_output_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if config.system:
            kwargs["system"] = config.system
        if config.reasoning_setting:
            kwargs.update(config.reasoning_setting)  # thinking / output_config from the compute condition
        if self.send_sampling_params:
            kwargs["temperature"] = config.temperature
        kwargs.update(config.extra.get("anthropic_request", {}))
        t0 = time.perf_counter()
        error = None
        try:
            if self.stream:
                with self.client.messages.stream(**kwargs) as s:
                    message = s.get_final_message()
            else:
                message = self.client.messages.create(**kwargs)
        except self._anthropic.APIError as e:  # keep the trial record; the runner logs the failure
            return ModelResponse(text="", provider=self.provider, model=self.model, config=config.to_dict(), timestamp=utc_now(), latency_s=time.perf_counter() - t0, raw={"request": _redact(kwargs)}, error=f"{type(e).__name__}: {e}")
        latency = time.perf_counter() - t0
        text_parts = [b.text for b in message.content if b.type == "text"]
        thinking_parts = [b.thinking for b in message.content if b.type == "thinking" and getattr(b, "thinking", "")]
        if message.stop_reason == "refusal":
            error = "refusal"
        elif message.stop_reason == "max_tokens":
            error = "max_tokens"
        usage = message.usage.to_dict() if hasattr(message.usage, "to_dict") else dict(message.usage)
        return ModelResponse(
            text="".join(text_parts),
            provider=self.provider,
            model=message.model,
            config=config.to_dict(),
            usage=usage,
            timestamp=utc_now(),
            latency_s=latency,
            raw={"request": _redact(kwargs), "response": message.to_dict(), "request_id": getattr(message, "_request_id", None), "stop_reason": message.stop_reason},
            reasoning_trace="\n".join(thinking_parts) or None,
            error=error,
        )


def _redact(kwargs: dict) -> dict:
    """Request parameters without the (already stored) prompt text."""
    return {k: v for k, v in kwargs.items() if k not in ("messages", "system")}

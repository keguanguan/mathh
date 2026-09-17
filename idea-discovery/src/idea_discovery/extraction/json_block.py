"""Locate and parse JSON objects (certificates) inside model text.

Used both for parsing structured responses (post-hoc / supplied-idea
conditions) and as one deterministic candidate extractor for free responses.
The original text is never modified; every hit records its character span.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

_FENCE_RE = re.compile(r"```(?:json|certificate|JSON)?\s*\n(.*?)```", re.DOTALL)


@dataclass
class JsonHit:
    obj: Any
    start: int
    end: int
    text: str


def _try_load(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _scan_braces(text: str) -> list[tuple[int, int]]:
    """Spans of balanced top-level {...} groups (string-aware)."""
    spans = []
    depth = 0
    start = -1
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0:
                    spans.append((start, i + 1))
    return spans


def find_json_objects(text: str) -> list[JsonHit]:
    """All parseable JSON objects in ``text``: fenced blocks first, then bare {...} groups."""
    hits: list[JsonHit] = []
    covered: list[tuple[int, int]] = []
    for m in _FENCE_RE.finditer(text):
        body = m.group(1).strip()
        obj = _try_load(body)
        if obj is None:
            for s, e in _scan_braces(body):
                obj = _try_load(body[s:e])
                if obj is not None:
                    break
        if isinstance(obj, dict):
            hits.append(JsonHit(obj, m.start(), m.end(), m.group(0)))
            covered.append((m.start(), m.end()))
    for s, e in _scan_braces(text):
        if any(cs <= s and e <= ce for cs, ce in covered):
            continue
        obj = _try_load(text[s:e])
        if isinstance(obj, dict):
            hits.append(JsonHit(obj, s, e, text[s:e]))
    hits.sort(key=lambda h: h.start)
    return hits


def find_certificates(text: str) -> list[JsonHit]:
    """JSON objects that carry a ``certificate_type`` key."""
    return [h for h in find_json_objects(text) if isinstance(h.obj.get("certificate_type"), str)]


def parse_structured_response(text: str) -> tuple[Optional[dict], Optional[str]]:
    """Parse a response that was *asked* to contain one certificate object.

    Returns ``(certificate, error)``. A response with no parseable object is
    reported as an error (this is how 'malformed certificate' outcomes arise).
    """
    certs = find_certificates(text)
    if certs:
        return certs[-1].obj, None
    objs = find_json_objects(text)
    if objs:
        return objs[-1].obj, "json object found but it has no 'certificate_type' field"
    return None, "no parseable JSON object in response"

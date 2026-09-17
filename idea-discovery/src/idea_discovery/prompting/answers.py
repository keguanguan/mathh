"""Parsing of the FINAL ANSWER line from free-solve responses."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

_FINAL_RE = re.compile(r"final\s*answer\s*[:\-]\s*\**\s*(.+?)\s*\**\s*$", re.IGNORECASE | re.MULTILINE)

_SYNONYMS = {
    "impossible": ("impossible", "not possible", "cannot", "can not", "no,", "no."),
    "possible": ("possible", "yes", "can be"),
}
_EXACT_WORDS = {"no": "impossible", "yes": "possible"}


@dataclass
class ParsedAnswer:
    raw: Optional[str]
    parsed: Optional[str]
    method: str


def parse_final_answer(text: str, options: Sequence[str]) -> ParsedAnswer:
    """Return the last FINAL ANSWER line mapped onto one of ``options``.

    Only the FINAL ANSWER line is used; the body of the response is never
    searched, so a response that discusses both options is not credited.
    """
    matches = _FINAL_RE.findall(text)
    if not matches:
        return ParsedAnswer(None, None, "no_final_answer_line")
    raw = matches[-1].strip().strip("*_`\"'.").strip()
    low = raw.lower()
    for opt in options:
        if low == opt.lower():
            return ParsedAnswer(raw, opt, "exact")
    if low in _EXACT_WORDS and _EXACT_WORDS[low] in options:
        return ParsedAnswer(raw, _EXACT_WORDS[low], "exact_word")
    # longest-phrase-first matching over option names and their synonyms, so that
    # "not possible" and "impossible" win over the bare substring "possible"
    phrases = [(opt.lower(), opt, "substring") for opt in options]
    phrases += [(syn, opt, "synonym") for opt in options for syn in _SYNONYMS.get(opt, ())]
    for phrase, opt, method in sorted(phrases, key=lambda t: len(t[0]), reverse=True):
        if phrase in low:
            return ParsedAnswer(raw, opt, method)
    return ParsedAnswer(raw, None, "unmapped")

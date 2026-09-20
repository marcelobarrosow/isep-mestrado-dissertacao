"""Heuristic QA for generated replies (empty, truncated, or malformed)."""

from __future__ import annotations

import re
from typing import List, Optional


MIN_RESPONSE_CHARS = 60


def response_quality_issues(response: str, epoch_id: Optional[str] = None) -> List[str]:
    """Empty, invalid English, unintelligible, or malformed."""
    flags: List[str] = []
    text = (response or "").strip()
    if not text:
        return ["empty"]

    min_chars = 15 if epoch_id == "E1" else MIN_RESPONSE_CHARS
    if len(text) < min_chars:
        flags.append("too_short")

    # DialoGPT-era replies may be short; still require a finished sentence.
    if not re.search(r"[.!?…][\"')\]]*$", text):
        flags.append("incomplete_ending")
    if re.search(r"\b(and|but|or|that|to|the|a|an|of|with|for|while|when|because|it)$", text, re.I):
        flags.append("cut_mid_phrase")
    if re.fullmatch(r"[\W_]+", text):
        flags.append("garbage")

    low = text.lower()
    # Near-empty placeholders (all eras)
    if low in {"i'm sorry.", "i am sorry.", "ok.", "okay.", "yes.", "no.", "i hear you."}:
        if epoch_id != "E1" or len(text) < 15:
            flags.append("too_short")

    # Reject Reddit/roleplay junk common in DialoGPT dumps
    if re.search(r"\b(u\/|r\/|user simulator|entsignated|idesption|zotrex)\b", low):
        flags.append("garbage")
    if re.search(r"(.)\1{5,}", text):  # aaaaa / !!!!!!
        flags.append("garbage")
    # Heavy exact-phrase repetition
    words = re.findall(r"[A-Za-z']+", text)
    if words:
        uniq = len(set(w.lower() for w in words))
        if len(words) >= 12 and uniq / len(words) < 0.35:
            flags.append("garbage")
    # Must look like English enough to rate (has common function words)
    if not re.search(r"\b(i|you|your|the|a|an|to|and|but|that|it|is|are|was|have|feel|sorry|proud|happy|scared)\b", low):
        flags.append("not_english_enough")

    return flags


def is_response_acceptable(response: str, epoch_id: Optional[str] = None) -> bool:
    return len(response_quality_issues(response, epoch_id=epoch_id)) == 0

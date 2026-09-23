"""Narration timing: reveal things as the voice mentions them.

A text-to-speech engine reports when each word is spoken. `Step.narrate`
matches a phrase to each annotation, mark or highlight and reveals it as that
phrase begins, so the picture keeps time with the voice rather than with a
hand-tuned `at=`.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
import unicodedata

from .errors import ValidationError

# Words per second for a string with no timings: an unhurried explainer pace,
# for previews before the audio exists.
DEFAULT_RATE = 2.5


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number of seconds")
    return float(value)


def parse_words(words, rate: float = DEFAULT_RATE) -> tuple[Word, ...]:
    """Accept (text, start, end) tuples, dicts, or a plain string to time at `rate`.

    Dicts may use "word" or "text", and "start"/"end" or "start_time"/"end_time".
    Times are seconds from the start of the step and must not go backwards.
    """
    if isinstance(words, str):
        rate = _number(rate, "rate")
        if rate <= 0:
            raise ValidationError("rate must be positive")
        parts = words.split()
        if not parts:
            raise ValidationError("words is empty")
        return tuple(Word(part, i / rate, (i + 1) / rate) for i, part in enumerate(parts))
    if not isinstance(words, (list, tuple)):
        raise ValidationError("words must be a string or a list of (word, start, end)")
    result = []
    for i, item in enumerate(words):
        if isinstance(item, dict):
            text = item.get("word", item.get("text"))
            start = item.get("start", item.get("start_time"))
            end = item.get("end", item.get("end_time"))
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            text, start, end = item
        else:
            raise ValidationError(f"words[{i}] must be (word, start, end) or a dict with word/start/end")
        if not isinstance(text, str) or not text.strip():
            raise ValidationError(f"words[{i}] needs non-empty text")
        start, end = _number(start, f"words[{i}] start"), _number(end, f"words[{i}] end")
        if start < 0 or end < start:
            raise ValidationError(f"words[{i}] must have 0 <= start <= end")
        if result and start < result[-1].start:
            raise ValidationError(f"words[{i}] starts before the word before it")
        result.append(Word(text.strip(), start, end))
    if not result:
        raise ValidationError("words is empty")
    return tuple(result)


def words_from_characters(characters, starts, ends) -> list[tuple[str, float, float]]:
    """Turn per-character timings (as some TTS APIs return) into word timings."""
    if not (len(characters) == len(starts) == len(ends)):
        raise ValidationError("characters, starts and ends must be the same length")
    words, current, begin, finish = [], "", None, None
    for char, start, end in zip(characters, starts, ends):
        if char.isspace():
            if current:
                words.append((current, begin, finish))
            current, begin = "", None
            continue
        if begin is None:
            begin = start
        current += char
        finish = end
    if current:
        words.append((current, begin, finish))
    return words


def _normal(text: str) -> str:
    """Case-, accent- and punctuation-insensitive form, for matching phrases."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", "", text)


def find_phrase(words: tuple[Word, ...], phrase: str) -> int:
    """Index of the first word of the phrase's first occurrence."""
    if not isinstance(phrase, str) or not phrase.split():
        raise ValidationError("each cue needs a non-empty phrase")
    wanted = [token for token in (_normal(p) for p in phrase.split()) if token]
    if not wanted:
        raise ValidationError(f"Phrase {phrase!r} has no words to match")
    # Skip spoken tokens that are only punctuation (a lone dash), so a phrase
    # still matches across them.
    spoken = [(i, _normal(w.text)) for i, w in enumerate(words)]
    spoken = [(i, token) for i, token in spoken if token]
    tokens = [token for _, token in spoken]
    for k in range(len(tokens) - len(wanted) + 1):
        if tokens[k:k + len(wanted)] == wanted:
            return spoken[k][0]
    preview = " ".join(w.text for w in words[:30])
    raise ValidationError(f"Phrase {phrase!r} is not in the narration; it begins: {preview!r}")

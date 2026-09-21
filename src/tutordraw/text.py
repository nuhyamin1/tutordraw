"""Decide which characters the built-in text renderer can draw correctly.

Two checks, because each catches what the other misses. The range table asks
"does this script need contextual shaping?" and the probe asks "can this
OpenCV build actually draw it?". A character must pass both.

Neither check is cosmetic. OpenCV substitutes a literal "?" for Thai without
raising, and draws Arabic letters unjoined and left to right, so a permissive
renderer would produce confidently wrong output. Silent corruption is the one
failure this module exists to prevent.
"""

from __future__ import annotations

from functools import lru_cache
import unicodedata

from .errors import ValidationError

# Scripts that render left to right with no contextual shaping, no visual
# reordering, and no combining-mark positioning. This is an allow list: an
# unlisted script raises rather than rendering silently wrong output. Thai,
# Arabic, Hebrew and the Indic scripts are deliberately absent; they need the
# font-rendering path described in docs/TEXT.md.
SIMPLE_SCRIPT_RANGES = (
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x024F),  # Latin-1 Supplement, Latin Extended-A and Extended-B
    (0x0370, 0x03FF),  # Greek and Coptic
    (0x0400, 0x04FF),  # Cyrillic
    (0x2000, 0x206F),  # General punctuation: dashes, curly quotes, ellipsis
    (0x2070, 0x209F),  # Superscripts and subscripts
    (0x20A0, 0x20CF),  # Currency symbols
    (0x2100, 0x214F),  # Letterlike symbols, including the degree Celsius sign
    (0x2150, 0x218F),  # Number forms, including vulgar fractions
    (0x2190, 0x21FF),  # Arrows
    (0x2200, 0x22FF),  # Mathematical operators
    (0x3000, 0x303F),  # CJK symbols and punctuation
    (0x3040, 0x30FF),  # Hiragana and katakana
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xAC00, 0xD7AF),  # Hangul syllables
)

# Messages stay pure ASCII on purpose. A legacy Windows console raises
# UnicodeEncodeError when printing the offending character, which would hide
# the very error the caller needs to read. The U+XXXX code identifies it.
SUPPORTED_SUMMARY = ("Latin, Greek, Cyrillic, CJK, and symbols including the "
                     "micro, degree, multiplication, plus-minus and fraction signs")

# Script-neutral punctuation, digits and symbols, drawable on either path.
COMMON_RANGES = (
    (0x0020, 0x007E), (0x00A0, 0x024F), (0x2000, 0x206F), (0x2070, 0x209F),
    (0x20A0, 0x20CF), (0x2100, 0x214F), (0x2150, 0x218F), (0x2190, 0x21FF),
    (0x2200, 0x22FF),
)

# DrawCV's font engine accepts Latin, Thai and Arabic only, and rejects Greek,
# Cyrillic and CJK outright -- the opposite gap from the built-in renderer.
# Neither path covers everything, so TutorDraw picks per annotation.
FONT_SCRIPT_RANGES = COMMON_RANGES + (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x0E00, 0x0E7F),  # Thai
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)

FONT_ONLY_SUMMARY = "Latin, Thai, Arabic and common symbols"


def _within(code: int, ranges) -> bool:
    return any(low <= code <= high for low, high in ranges)


def _in_simple_script(code: int) -> bool:
    return _within(code, SIMPLE_SCRIPT_RANGES)


def uses_font_path(text: str, font_available: bool) -> bool:
    """A configured font draws everything it can, for one typeface per lesson.

    Greek, Cyrillic and CJK fall back to the built-in renderer, because the
    font engine rejects those scripts whatever the font actually contains.
    """
    return font_available and all(
        c.isspace() or _within(ord(c), FONT_SCRIPT_RANGES) for c in text)


THAI_RANGE = (0x0E00, 0x0E7F)


def has_thai(text: str) -> bool:
    return any(THAI_RANGE[0] <= ord(c) <= THAI_RANGE[1] for c in text)


def thai_segments(paragraph: str) -> list[str] | None:
    """Thai has no spaces, so ask the bundled dictionary where words end.

    Returns None when the text is not Thai or the segmenter is unavailable, and
    the caller falls back to splitting on whitespace.
    """
    if not has_thai(paragraph):
        return None
    import os

    os.environ.setdefault("PYTHAINLP_READ_ONLY", "1")
    os.environ.setdefault("PYTHAINLP_OFFLINE", "1")
    try:
        from pythainlp.tokenize import word_tokenize
    except Exception:
        return None
    try:
        return [piece for piece in word_tokenize(paragraph, engine="newmm",
                                                 keep_whitespace=True) if piece]
    except Exception:
        return None


RTL_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def is_rtl(text: str) -> bool:
    """True for right-to-left text, which must sit against the panel's right edge."""
    return any(_within(ord(c), RTL_RANGES) for c in text)


def needs_font(text: str) -> bool:
    """True when any character can only be drawn by the font engine."""
    return any(not _in_simple_script(ord(c)) and _within(ord(c), FONT_SCRIPT_RANGES)
               for c in text)


@lru_cache(maxsize=4096)
def renders(char: str) -> bool:
    """Ask the real renderer whether it draws this character or substitutes one.

    Probing beats a hardcoded table because glyph coverage varies by OpenCV
    build: this host draws CJK, the 4.8 floor in the dependency pin may not.
    """
    if char == "?":
        return True  # The probe compares against "?", so it cannot test itself.
    from drawcv import Color, OpenCVRenderer, Point, Scene, Text

    def ink(value: str) -> bytes:
        scene = Scene(96, 96, background=Color.white())
        scene.add(Text(text=value, position=Point(8, 8), font_scale=1.0,
                       thickness=1, color=Color(0, 0, 0)))
        return OpenCVRenderer().render(scene).buffer.tobytes()

    try:
        drawn = ink(char)
    except Exception:
        # DrawCV refusing the character means the same thing as a substitution:
        # we cannot draw it. The caller's message says so precisely either way.
        return False
    if drawn == ink(" "):
        return False  # Nothing was drawn.
    return drawn != ink("?")


def validate_annotation_text(text: str, *, allow_newlines: bool,
                             font: bool = False) -> str:
    """Return NFC-normalized text, or raise naming the offending character.

    `font` says whether the tutorial has a font configured. It widens the
    accepted set to Thai and Arabic, which only the font engine can shape.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("Annotation text must be a nonempty string")
    # Normalizing first accepts "e" plus a combining acute as the precomposed
    # form, rather than rejecting it as a stray mark. NFC is idempotent, so
    # saved lessons still round trip.
    text = unicodedata.normalize("NFC", text)
    for char in text:
        if char == "\n":
            if not allow_newlines:
                raise ValidationError(
                    "Only callouts allow newlines; labels are single line")
            continue
        code = ord(char)
        if code < 0x20 or code == 0x7F:
            raise ValidationError(
                f"Annotation text cannot contain the control character U+{code:04X}")
        if char.isspace():
            continue  # Spacing renders no ink, so the probe cannot judge it.
        if code <= 0x7E:
            continue  # ASCII always renders; skip the probe for the common case.
        if _in_simple_script(code):
            if not renders(char):
                raise ValidationError(
                    f"This OpenCV build draws a placeholder instead of {ascii(char)} "
                    f"(U+{code:04X}). Upgrade opencv-python, or use a character from "
                    f"the supported set: {SUPPORTED_SUMMARY}.")
            continue
        if _within(code, FONT_SCRIPT_RANGES):
            if not font:
                raise ValidationError(
                    f"Annotation text contains {ascii(char)} (U+{code:04X}), a shaped "
                    f"script the built-in renderer would draw wrongly. Give the "
                    f"tutorial a font to enable it: Tutorial(scene, font='NotoSansThai.ttf').")
            continue
        raise ValidationError(
            f"Annotation text contains {ascii(char)} (U+{code:04X}), from a script "
            f"TutorDraw cannot draw. The built-in renderer supports "
            f"{SUPPORTED_SUMMARY}; a configured font adds Thai and Arabic.")
    # Each annotation renders through one path, and neither path covers both
    # sides of this split, so a single annotation cannot mix them.
    if needs_font(text) and any(ord(c) > 0x7E and _in_simple_script(ord(c))
                                and not _within(ord(c), FONT_SCRIPT_RANGES) for c in text):
        raise ValidationError(
            "One annotation cannot mix Thai or Arabic with Greek, Cyrillic or CJK: "
            "they need different renderers. Split them into separate annotations.")
    return text

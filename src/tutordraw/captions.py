"""Timed captions: what is said, on screen and in subtitle files.

A step's captions are either written by the author (`Step.caption`) or, for a
narrated step without any, cut from its narration's word timings into short
sentence-sized cues. `lesson_cues` puts every step's cues on the lesson's
clock; `to_webvtt` and `to_srt` write them for a video platform, and
`caption_artwork` burns one into a frame. See docs/CAPTIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import tempfile
import shutil

from .errors import ValidationError

# A cue cut from narration holds at most this many characters: two subtitle
# lines of about 42, the usual broadcast limit.
MAX_CUE_CHARS = 84
# Seconds a narrated cue stays up after its last word, unless the next one starts first.
HOLD = 0.6
# Characters per second above which a caption is too fast to read (a common
# subtitle guideline is 17-20 for adults); see lint CAPTION_TOO_FAST.
MAX_READING_RATE = 20.0
# Burned-in captions: text size, band opacity, and space from the bottom edge.
FONT_SCALE = 0.75
BAND_OPACITY = 0.72
MARGIN = 0.06  # of the canvas height
MAX_WIDTH = 0.8  # of the canvas width

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*$")


@dataclass(frozen=True)
class Caption:
    """An authored caption: `text` from `at` seconds into the step until `until` (None: until the next)."""

    text: str
    at: float
    until: float | None = None


@dataclass(frozen=True)
class Cue:
    """One caption on screen from `start` to `end` seconds."""

    start: float
    end: float
    text: str


def step_cues(step) -> tuple[Cue, ...]:
    """A step's cues in seconds from its start, ending by the end of its pause."""
    total = step.duration + step.pause
    if step.captions:
        ordered = sorted(step.captions, key=lambda c: c.at)
        cues = []
        for i, caption in enumerate(ordered):
            if caption.at >= total:
                break  # a step shortened after the caption was written: it never shows
            following = ordered[i + 1].at if i + 1 < len(ordered) else total
            end = min(total, following if caption.until is None else caption.until)
            cues.append(Cue(caption.at, end, caption.text))
        return tuple(cues)
    return _narration_cues(step.narration, total)


def _narration_cues(words, total: float) -> tuple[Cue, ...]:
    """Sentences, and sentences too long for two lines split at word boundaries."""
    sentences, current = [], []
    for word in words:
        current.append(word)
        if _SENTENCE_END.search(word.text):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    chunks = [chunk for sentence in sentences for chunk in _split(sentence)]
    cues = []
    for i, chunk in enumerate(chunks):
        start = chunk[0].start
        if start >= total:
            break
        end = chunk[-1].end + HOLD
        if i + 1 < len(chunks):
            end = min(end, chunks[i + 1][0].start)
        end = min(max(end, chunk[-1].end), total)
        if end > start:
            cues.append(Cue(start, end, " ".join(w.text for w in chunk)))
    return tuple(cues)


def _split(sentence: list) -> list[list]:
    """A sentence in as few parts of MAX_CUE_CHARS as it needs, of about equal length.

    Equal parts, so no word is left on its own; each break goes after a comma
    near where it falls, if there is one, or else at the nearest word.
    """
    def length(part):
        return len(" ".join(w.text for w in part))

    if length(sentence) <= MAX_CUE_CHARS or len(sentence) < 2:
        return [sentence]
    parts = -(-length(sentence) // MAX_CUE_CHARS)
    # Characters up to the end of each word, and the break nearest each part's share.
    ends, total = [], -1
    for word in sentence:
        total += len(word.text) + 1
        ends.append(total)
    result, begin = [], 0
    for k in range(1, parts):
        target = length(sentence) * k / parts
        window = range(begin, len(sentence) - 1)

        def cost(i):
            comma = sentence[i].text.endswith((",", ";", ":"))
            return abs(ends[i] - target) - (12 if comma else 0)

        cut = min(window, key=cost)
        if length(sentence[begin:cut + 1]) > MAX_CUE_CHARS:  # a comma too far off: the nearest word
            cut = min(window, key=lambda i: abs(ends[i] - target))
        result.append(sentence[begin:cut + 1])
        begin = cut + 1
    result.append(sentence[begin:])
    # A part the word breaks left a little long is split again.
    return [piece for part in result if part
            for piece in (_split(part) if len(part) < len(sentence) else [part])]


def lesson_cues(tutorial) -> tuple[Cue, ...]:
    """Every step's cues on the lesson's clock, in order."""
    from .timing import boundaries

    ends = boundaries(tutorial)
    cues = []
    for index, step in enumerate(tutorial.steps):
        offset = ends[index - 1] if index else 0.0
        cues.extend(Cue(offset + c.start, offset + c.end, c.text) for c in step_cues(step))
    return tuple(cues)


def cue_at(cues: tuple[Cue, ...], time: float) -> Cue | None:
    """The cue on screen at `time`, if any; intervals are [start, end)."""
    for cue in cues:
        if cue.start <= time < cue.end:
            return cue
    return None


def _clock(seconds: float, separator: str) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def _body(text: str) -> str:
    # A blank line would end the cue; "-->" would read as a timing line.
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines).replace("-->", "->")


def to_webvtt(cues) -> str:
    """WebVTT, for the web and most video platforms."""
    blocks = ["WEBVTT"]
    for cue in cues:
        text = _body(cue.text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        blocks.append(f"{_clock(cue.start, '.')} --> {_clock(cue.end, '.')}\n{text}")
    return "\n\n".join(blocks) + "\n"


def to_srt(cues) -> str:
    """SubRip, for video editors and players that do not read WebVTT."""
    blocks = [f"{i}\n{_clock(cue.start, ',')} --> {_clock(cue.end, ',')}\n{_body(cue.text)}"
              for i, cue in enumerate(cues, 1)]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


FORMATS = {".vtt": to_webvtt, ".srt": to_srt}


def export_captions(tutorial, path: str | Path, *, overwrite: bool) -> Path:
    if not isinstance(overwrite, bool):
        raise ValidationError("overwrite must be a boolean")
    destination = Path(path)
    writer = FORMATS.get(destination.suffix.lower())
    if writer is None:
        raise ValidationError(f"Caption files end in .vtt or .srt, not {destination.suffix or 'nothing'!r}")
    cues = lesson_cues(tutorial)
    if not cues:
        raise ValidationError("The lesson has no captions: add step.caption() or step.narrate()")
    if destination.is_symlink() or (destination.exists() and (not overwrite or not destination.is_file())):
        raise FileExistsError(f"Caption destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tutordraw-", suffix=destination.suffix, dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(writer(cues))
        if overwrite:
            os.replace(temporary, destination)
        else:
            with destination.open("xb") as output, temporary.open("rb") as source:
                shutil.copyfileobj(source, output)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def caption_artwork(text: str, width: int, height: int, theme, font) -> list:
    """A cue as subtitles: light lines on a dark band, centred near the bottom."""
    from drawcv import Color, FillStyle, Point, Rectangle

    from .layout import annotation_text, wrap_text

    lines = wrap_text(text, FONT_SCALE, width * MAX_WIDTH, theme, font)
    texts = [annotation_text(line, FONT_SCALE, theme, font) for line in lines]
    for item in texts:
        item.color = Color(255, 255, 255)
    measures = [item.get_bounds() for item in texts]
    line_height = max(1, annotation_text("Ag", FONT_SCALE, theme, font).get_bounds().height,
                      *(m.height for m in measures))
    spacing, pad = 1.35, 10
    block = line_height * (1 + (len(lines) - 1) * spacing)
    band_width = max(m.width for m in measures) + 2 * pad
    top = height * (1 - MARGIN) - block - 2 * pad
    band = Rectangle(position=Point(width / 2 - band_width / 2, top), width=band_width,
                     height=block + 2 * pad, fill=FillStyle(color=Color(0, 0, 0)), stroke=None,
                     opacity=BAND_OPACITY, id="td-caption-band")
    artwork = [band]
    for i, (item, measure) in enumerate(zip(texts, measures)):
        # As label_artwork does: a measure's x and y are its ink's offset from the position.
        item.position = Point(width / 2 - measure.width / 2 - measure.x,
                              top + pad + i * line_height * spacing - measure.y)
        item.id = f"td-caption-{i}"
        artwork.append(item)
    return artwork

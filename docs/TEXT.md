# Annotation text and character support

Changed in development **0.1.0a7**. Earlier versions accepted printable ASCII
only. Labels and callouts now accept a much wider set, with **no new dependency**.

```python
target.label("30 µm")
step.explain(target, "Held at 37 °C ± 0.5 °C, tilted α = 45°.")
```

Run `python examples/symbols_lesson.py` for a rendered diagram using `µm`, `°C`,
`α`, `½`, `±`, `≤` and `×`.

## What is supported

Latin (including accents), Greek, Cyrillic, CJK ideographs, kana, Hangul, and
common symbols: micro sign, degree sign, `× ÷ ± ≤ ≥ ∞`, fractions such as `½`,
currency, arrows, superscripts and subscripts, em and en dashes, curly quotes
and the ellipsis.

Labels are single line. Callouts additionally accept `\n` and wrap to
`max_width` using rendered measurements.

Text is normalised to **NFC** when the annotation is created, so `e` followed by
a combining acute becomes `é`. The normalised form is what gets stored, rendered
and saved. NFC is idempotent, so lesson files round trip unchanged.

## What is refused, and why

Two independent checks run per character. A character must pass both.

**1. Is the script simple enough to draw?** TutorDraw keeps an allow list of
Unicode ranges that render left to right with no contextual shaping, no visual
reordering, and no combining-mark positioning. Anything outside it is refused.
It is an allow list rather than a block list so that an unrecognised script
fails loudly instead of rendering silently wrong output.

This is what rejects **Thai, Arabic, Hebrew, the Indic scripts and emoji**. The
reason is not laziness — it is that the built-in renderer gets them wrong in
ways you would not notice:

- Thai is substituted with literal `?` marks. Nothing raises, and measurement
  returns plausible numbers for the wrong glyphs.
- Arabic draws isolated letterforms, unjoined and in left-to-right order. Glyphs
  appear, so it looks like it worked. It did not.

Refusing is the honest behavior. See "Thai and Arabic" below.

**2. Can this OpenCV build actually draw it?** TutorDraw renders the character
through the real rendering path and compares the result against the renderer's
placeholder. Glyph coverage varies by OpenCV version — this host draws CJK,
the `opencv-python>=4.8` floor in the DrawCV pin may not — so the library asks
rather than assuming. Results are cached, and ASCII skips the probe entirely, so
an all-ASCII lesson pays nothing.

Both failures raise `ValidationError` naming the character and its codepoint:

```
Annotation text contains '\u0e2a' (U+0E2A), from a script TutorDraw cannot draw
yet. Built-in text supports Latin, Greek, Cyrillic, CJK, and symbols including
the micro, degree, multiplication, plus-minus and fraction signs. Thai, Arabic
and other shaped scripts need font rendering, which is not implemented.
```

```
This OpenCV build draws a placeholder instead of '\u7d30' (U+7D30). Upgrade
opencv-python, or use a character from the supported set: Latin, Greek,
Cyrillic, CJK, and symbols including the micro, degree, multiplication,
plus-minus and fraction signs.
```

The messages distinguish *unsupported script* from *this build cannot*, because
the fixes differ. They are written to be actionable by a model generating lesson
content at runtime as well as by a person.

Error messages are pure ASCII by design. A legacy Windows console raises
`UnicodeEncodeError` when asked to print, say, Thai, so embedding the character
in the message would hide the error behind a second error; `ascii(char)` and the
`U+XXXX` code identify it safely. If you print annotation text yourself on such
a console, call `sys.stdout.reconfigure(errors="replace")` as
`examples/symbols_lesson.py` does. Rendered images are never affected.

Control characters are always refused. Tutorial and step titles are metadata,
never drawn, and are not restricted.

## Thai and Arabic

Not supported yet, but the path is proven. Correct rendering needs DrawCV's font
path, which requires `pip install "pydrawcv[typography]"` and a caller-supplied
`.ttf` or `.otf` — DrawCV bundles no fonts and does not search the system.

Verified in a throwaway environment on Windows 11 / CPython 3.12: the extra
installs cleanly (`pyicu-wheels` ships a prebuilt binary, so the usual ICU build
problem does not arise), and with Tahoma as the font asset, `สวัสดี` renders as
correct Thai and `مرحبا` renders correctly joined and right to left.

One complication to design around: DrawCV's font path has its own hardcoded
script whitelist of Latin, Thai and Arabic, and **rejects Greek**. The two paths
therefore have complementary coverage, and `α` cannot share a string with Thai
on either path.

## Not implemented

Bidirectional text mixing, vertical CJK layout, ruby annotations, emoji,
per-character font fallback, and font selection through the theme. Automatic
label collision avoidance is unrelated but still absent; see [API.md](API.md).

"""Shaped scripts through DrawCV's font engine.

These need the optional typography extra and a font file covering Thai and
Arabic. Both are discovered at runtime and the module skips when either is
missing, so a default install still runs the suite.
"""

import os
from pathlib import Path

from drawcv import Circle, Color, FillStyle, FontAsset, Point, Scene
import numpy as np
import pytest

from tutordraw import LessonFormatError, Tutorial, ValidationError
import tutordraw.layout as layout_module

THAI = "\u0e19\u0e34\u0e27\u0e40\u0e04\u0e25\u0e35\u0e22\u0e2a"          # nucleus
THAI_SENTENCE = ("\u0e40\u0e0b\u0e25\u0e25\u0e4c\u0e21\u0e35\u0e19\u0e34\u0e27\u0e40\u0e04\u0e25\u0e35\u0e22\u0e2a"
                 "\u0e2d\u0e22\u0e39\u0e48\u0e15\u0e23\u0e07\u0e01\u0e25\u0e32\u0e07 \u0e0b\u0e36\u0e48\u0e07"
                 "\u0e40\u0e01\u0e47\u0e1a DNA \u0e02\u0e2d\u0e07\u0e40\u0e0b\u0e25\u0e25\u0e4c")
ARABIC = "\u0627\u0644\u0646\u0648\u0627\u0629"                          # the nucleus
ARABIC_SENTENCE = ("\u0627\u0644\u062e\u0644\u064a\u0629 \u0647\u064a \u0648\u062d\u062f\u0629 "
                   "\u0627\u0644\u0628\u0646\u0627\u0621 \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629")

CANDIDATES = [
    os.environ.get("TUTORDRAW_TEST_FONT"),
    r"C:\Windows\Fonts\tahoma.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]


def _usable(path):
    """A candidate qualifies only if it really draws both scripts."""
    try:
        asset = FontAsset.from_file(path)
        scene = Scene(300, 120, background=Color.white())
        tutorial = Tutorial(scene, font=asset)
        shape = Circle(center=Point(150, 60), radius=10)
        scene.add(shape)
        target = tutorial.target(shape)
        tutorial.step("probe").show(target.label(THAI), target.label(ARABIC))
        tutorial.render_step(0)
        return asset
    except Exception:
        return None


def _discover():
    for path in CANDIDATES:
        if path and Path(path).is_file():
            asset = _usable(path)
            if asset is not None:
                return asset
    return None


FONT = _discover()
REASON = ("No font covering Thai and Arabic, or the typography extra is missing. "
          "Set TUTORDRAW_TEST_FONT to a .ttf covering both.")

if FONT is None and os.environ.get("TUTORDRAW_REQUIRE_FONT"):
    # CI sets this where the engine and a covering font are expected, so a
    # silent skip cannot pass for coverage.
    raise RuntimeError(f"TUTORDRAW_REQUIRE_FONT is set but the font path is unavailable. {REASON}")

pytestmark = pytest.mark.skipif(FONT is None, reason=REASON)


def make(font=FONT, width=760):
    scene = Scene(width, 320, background=Color.white())
    shape = Circle(center=Point(150, 160), radius=55,
                   fill=FillStyle(color=Color(120, 170, 210)))
    scene.add(shape)
    tutorial = Tutorial(scene, font=font)
    return tutorial, tutorial.target(shape, name="subject")


@pytest.mark.parametrize("text", [THAI, ARABIC])
def test_shaped_scripts_render_when_a_font_is_configured(text):
    tutorial, subject = make()
    tutorial.step("Label").show(subject.label(text, anchor="top", gap=30))
    rendered = tutorial.render_step(0).buffer

    blank, _ = make()
    blank.step("Label")
    assert not np.array_equal(rendered, blank.render_step(0).buffer)
    assert rendered.min() < 200  # Real ink, not an empty panel.


@pytest.mark.parametrize("text", [THAI_SENTENCE, ARABIC_SENTENCE])
def test_shaped_callouts_wrap_to_the_requested_width(text):
    from tutordraw.layout import wrap_text
    from tutordraw.themes import Theme

    narrow = wrap_text(text, 0.7, 180, Theme(), FONT)
    wide = wrap_text(text, 0.7, 900, Theme(), FONT)
    assert len(narrow) > len(wide) >= 1
    assert "".join(narrow).replace(" ", "") == text.replace(" ", "")

    tutorial, subject = make()
    tutorial.step("Explain").explain(subject, text, gap=90, max_width=180)
    tutorial.render_step(0)  # Raises if a wrapped line cannot be laid out.


def test_thai_breaks_at_word_boundaries_not_mid_syllable():
    """Thai has no spaces, so naive splitting would cut words in half."""
    from tutordraw.layout import wrap_text
    from tutordraw.text import thai_segments
    from tutordraw.themes import Theme

    unbroken = ("เซลล์มีนิวเคลี"
                "ยสอยู่ตรงกลาง")
    segments = thai_segments(unbroken)
    assert segments and len(segments) > 1

    lines = wrap_text(unbroken, 0.7, 110, Theme(), FONT)
    assert len(lines) > 1
    assert "".join(lines) == unbroken
    # Every break must fall on a boundary the segmenter identified.
    boundaries, position = set(), 0
    for piece in segments:
        position += len(piece)
        boundaries.add(position)
    cut = 0
    for line in lines[:-1]:
        cut += len(line)
        assert cut in boundaries, f"line break at {cut} is inside a word"


def test_a_font_is_used_for_latin_too_but_greek_falls_back():
    """One typeface per lesson where possible; Greek has no font-engine support."""
    with_font, subject = make()
    with_font.step("Latin").show(subject.label("Nucleus", anchor="top", gap=30))
    without_font, plain_subject = make(font=None)
    without_font.step("Latin").show(plain_subject.label("Nucleus", anchor="top", gap=30))
    assert not np.array_equal(with_font.render_step(0).buffer,
                              without_font.render_step(0).buffer)

    greek_font, greek_subject = make()
    greek_font.step("Greek").show(greek_subject.label("\u03b1 \u03b2 \u03c0", anchor="top", gap=30))
    greek_plain, greek_plain_subject = make(font=None)
    greek_plain.step("Greek").show(greek_plain_subject.label("\u03b1 \u03b2 \u03c0", anchor="top", gap=30))
    np.testing.assert_array_equal(greek_font.render_step(0).buffer,
                                  greek_plain.render_step(0).buffer)


def test_one_annotation_cannot_mix_renderers():
    tutorial, subject = make()
    with pytest.raises(ValidationError, match="cannot mix"):
        subject.label(f"{THAI} \u03b1")
    # Separate annotations are fine, each on its own renderer.
    step = tutorial.step("Both").show(subject.label(THAI, anchor="top", gap=30),
                                      subject.label("\u03b1", anchor="bottom", gap=30))
    assert len(step.labels) == 2
    tutorial.render_step(0)


def test_right_to_left_text_hangs_from_the_right_edge():
    tutorial, subject = make()
    tutorial.step("Arabic").explain(subject, ARABIC_SENTENCE, gap=90, max_width=200)
    image = tutorial.render_step(0).buffer

    ltr, ltr_subject = make()
    ltr.step("Latin").explain(ltr_subject, "The cell is the basic unit of living things",
                              gap=90, max_width=200)
    other = ltr.render_step(0).buffer
    assert not np.array_equal(image, other)


def test_round_trip_needs_the_font_supplied_again(tmp_path):
    tutorial, subject = make()
    tutorial.step("Thai").show(subject.label(THAI, anchor="top", gap=30))
    path = tutorial.save_json(tmp_path / "lesson.tutordraw.json")

    restored = Tutorial.load_json(path, font=FONT)
    np.testing.assert_array_equal(restored.render_step(0).buffer,
                                  tutorial.render_step(0).buffer)
    assert restored.font is not None

    # Without the font the lesson is unreadable, and says so.
    with pytest.raises(LessonFormatError, match="font"):
        Tutorial.load_json(path)


def test_font_accepts_a_path_bytes_or_an_asset(tmp_path):
    data = FONT.data
    target = tmp_path / "font.ttf"
    target.write_bytes(data)
    for value in (str(target), target, data, FONT):
        assert Tutorial(Scene(50, 50), font=value).font is not None
    for bad in (b"not a font", 42, tmp_path):
        with pytest.raises(ValidationError):
            Tutorial(Scene(50, 50), font=bad)


def test_missing_typography_extra_names_the_install_command(monkeypatch):
    tutorial, subject = make()
    tutorial.step("Thai").show(subject.label(THAI, anchor="top", gap=30))

    def unavailable(*args, **kwargs):
        raise RuntimeError('Font text requires the optional dependencies: '
                           'pip install "pydrawcv[typography]"')

    monkeypatch.setattr(layout_module, "annotation_text", unavailable)
    with pytest.raises(ValidationError, match=r'tutordraw\[typography\]'):
        tutorial.render_step(0)

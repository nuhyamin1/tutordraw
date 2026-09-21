import unicodedata

from drawcv import Circle, Color, FillStyle, Point, Scene
import numpy as np
import pytest

from tutordraw import Tutorial, ValidationError
import tutordraw.text as text_module

ACCEPTED = [
    "10 µm",              # micro sign
    "45°C",               # degree sign
    "α β π Δ",  # Greek
    "café naïve straße",  # Latin-1
    "½ × ÷ ± ≤ ≥",  # fractions and operators
    "— dash and “curly quotes”",
    "биология",  # Cyrillic
]

REJECTED_SCRIPTS = [
    "สวัสดี",  # Thai renders as literal question marks
    "مرحبا",        # Arabic draws unjoined and left to right
    "שלום",              # Hebrew
    "नमस्ते",  # Devanagari
    "hi \U0001f642",                          # emoji
]


@pytest.fixture
def target():
    # Roomy enough that a long label never triggers an off-canvas warning,
    # so any warning a test does raise is a real finding.
    scene = Scene(900, 400, background=Color.white())
    shape = Circle(center=Point(150, 200), radius=40,
                   fill=FillStyle(color=Color(80, 130, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    return tutorial, tutorial.target(shape, name="subject")


@pytest.mark.parametrize("value", ACCEPTED)
def test_supported_characters_are_accepted_and_drawn(target, value):
    tutorial, subject = target
    label = subject.label(value)
    assert label.text == value
    tutorial.step("Show").show(label)
    rendered = tutorial.render_step(0).buffer
    # A panel with real glyphs must differ from the same lesson drawn blank.
    assert rendered.min() < 250


@pytest.mark.parametrize("value", REJECTED_SCRIPTS)
def test_unsupported_scripts_name_the_character_and_codepoint(target, value):
    _, subject = target
    offending = next(c for c in value if ord(c) > 0x7E)
    with pytest.raises(ValidationError) as caught:
        subject.label(value)
    message = str(caught.value)
    # Pure ASCII, so printing the error cannot itself raise on a legacy console.
    assert message.isascii(), message
    assert ascii(offending) in message
    assert f"U+{ord(offending):04X}" in message
    assert "font rendering" in message


def test_symbols_change_the_rendered_image(target):
    """A degree sign must draw ink, not be silently dropped."""
    tutorial, subject = target
    plain = tutorial.step("Plain").show(subject.label("45"))
    withsign = tutorial.step("Degrees").show(subject.label("45°"))
    assert not np.array_equal(tutorial.render_step(0).buffer,
                              tutorial.render_step(1).buffer)
    assert plain is not withsign


def test_combining_marks_are_normalized_to_nfc(target):
    _, subject = target
    decomposed = "café"  # "e" followed by a combining acute accent
    assert len(decomposed) == 5
    label = subject.label(decomposed)
    assert label.text == "café" == unicodedata.normalize("NFC", decomposed)


def test_lone_combining_mark_is_rejected(target):
    _, subject = target
    with pytest.raises(ValidationError, match="U\\+0301"):
        subject.label("á́")  # Second mark survives NFC as a bare mark.


@pytest.mark.parametrize("value", ["tab\there", "bell\x07", "null\x00"])
def test_control_characters_are_rejected(target, value):
    _, subject = target
    with pytest.raises(ValidationError, match="control character"):
        subject.label(value)


def test_newlines_only_in_callouts(target):
    tutorial, subject = target
    with pytest.raises(ValidationError, match="single line"):
        subject.label("two\nlines")
    callout = tutorial.step("Explain").explain(subject, "two\nlines")
    assert callout.text == "two\nlines"


@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_empty_and_non_string_text_rejected(target, value):
    _, subject = target
    with pytest.raises(ValidationError, match="nonempty string"):
        subject.label(value)


def test_question_mark_is_not_mistaken_for_a_substitution(target):
    """The probe compares against '?', so '?' itself must stay usable."""
    _, subject = target
    assert subject.label("What is this?").text == "What is this?"
    assert text_module.renders("?") is True


def test_ascii_never_invokes_the_probe(target, monkeypatch):
    """The common path must cost nothing; probing renders a scene per character."""
    _, subject = target
    monkeypatch.setattr(text_module, "renders",
                        lambda char: pytest.fail(f"probed ASCII {char!r}"))
    subject.label("Plain ASCII label, 100% of it!")


def test_probe_detects_a_build_that_cannot_draw(target, monkeypatch):
    """An in-range character the renderer substitutes must still be refused."""
    _, subject = target
    monkeypatch.setattr(text_module, "renders", lambda char: False)
    with pytest.raises(ValidationError, match="draws a placeholder"):
        subject.label("10 µm")


def test_probe_classifies_real_characters(target):
    assert text_module.renders("µ") is True   # micro sign
    assert text_module.renders("α") is True   # Greek alpha
    assert text_module.renders("ส") is False  # Thai, substituted with "?"


def test_callout_wraps_and_measures_non_ascii(target):
    """Wrapping uses rendered measurements, so wide glyphs must not overflow."""
    tutorial, subject = target
    step = tutorial.step("Explain")
    callout = step.explain(subject, "Measured at 10 µm across, about 45° "
                                    "from the α axis and ½ the width.",
                           max_width=150)
    assert callout.max_width == 150
    tutorial.render_step(0)  # Raises if a character cannot fit the wrap width.


def test_non_ascii_survives_the_json_round_trip(target, tmp_path):
    tutorial, subject = target
    value = "10 µm at 45° (α)"
    tutorial.step("Show").show(subject.label(value))
    before = tutorial.render_step(0).buffer.copy()

    path = tutorial.save_json(tmp_path / "lesson.tutordraw.json")
    assert "µ" in path.read_text(encoding="utf-8")  # Written, not escaped.
    restored = Tutorial.load_json(path)

    assert restored.labels[0].text == value
    np.testing.assert_array_equal(restored.render_step(0).buffer, before)

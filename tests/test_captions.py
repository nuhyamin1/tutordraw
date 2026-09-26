"""Timed captions: written or cut from narration, in subtitle files, the player and burned into video."""

import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene
from jsonschema import Draft202012Validator

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import Tutorial, ValidationError
from tutordraw.captions import MAX_CUE_CHARS, Cue

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


@pytest.fixture
def lesson():
    scene = Scene(640, 360, background=Color.white())
    ball = Circle(center=Point(320, 140), radius=60, fill=FillStyle(color=Color(80, 120, 200)))
    scene.add(ball)
    tutorial = Tutorial(scene, title="Ball")
    return tutorial, tutorial.target(ball, name="ball")


def test_a_written_caption_lasts_until_the_next_or_the_end_of_the_pause(lesson):
    tutorial, _ = lesson
    first = tutorial.step("One", duration=4, pause=1)
    first.caption("A ball.", at=0.5).caption("It is blue.", at=2, until=3.5)
    tutorial.step("Two", duration=3).caption("Now it moves.")
    assert tutorial.captions() == (Cue(0.5, 2.0, "A ball."), Cue(2.0, 3.5, "It is blue."),
                                   Cue(5.0, 8.0, "Now it moves."))


def test_captions_are_checked_when_written(lesson):
    tutorial, _ = lesson
    step = tutorial.step("One", duration=4).caption("First", at=1, until=2.5)
    with pytest.raises(ValidationError, match="until must be later"):
        step.caption("Backwards", at=3, until=3)
    with pytest.raises(ValidationError, match="overlaps"):
        step.caption("Too early", at=2)
    with pytest.raises(ValidationError, match="overlaps"):
        step.caption("Runs on", at=0, until=1.5)
    with pytest.raises(ValidationError, match="already starts"):
        step.caption("Same time", at=1)
    with pytest.raises(ValidationError):
        step.caption("   ")
    assert [c.text for c in step.captions] == ["First"]


def test_narration_is_cut_into_sentences_that_fit_two_lines(lesson):
    tutorial, _ = lesson
    long = " ".join(["word"] * 40) + "."
    step = tutorial.step("One", duration=2).narrate(f"A ball. {long} Done.", rate=4)
    cues = tutorial.captions()
    assert cues[0].text == "A ball." and cues[-1].text == "Done."
    assert all(len(c.text) <= MAX_CUE_CHARS for c in cues) and len(cues) >= 4
    assert " ".join(c.text for c in cues) == " ".join(w.text for w in step.narration)
    for cue, following in zip(cues, cues[1:]):
        assert cue.start < cue.end <= following.start  # held a moment, never over the next
    assert cues[-1].end <= step.duration + step.pause


def test_written_captions_replace_the_narrations(lesson):
    tutorial, _ = lesson
    tutorial.step("One", duration=2).narrate("Something said.").caption("Something written.")
    assert [c.text for c in tutorial.captions()] == ["Something written."]


def test_subtitle_files(lesson, tmp_path):
    tutorial, _ = lesson
    tutorial.step("One", duration=3700).caption("A <ball> & more.", at=1.25).caption("Two\nlines", at=3661.5)
    vtt = tutorial.export_captions(tmp_path / "lesson.vtt").read_text(encoding="utf-8")
    assert vtt == ("WEBVTT\n\n00:00:01.250 --> 01:01:01.500\nA &lt;ball&gt; &amp; more.\n\n"
                   "01:01:01.500 --> 01:01:40.000\nTwo\nlines\n")
    srt = tutorial.export_captions(tmp_path / "lesson.SRT").read_text(encoding="utf-8")
    assert srt == ("1\n00:00:01,250 --> 01:01:01,500\nA <ball> & more.\n\n"
                   "2\n01:01:01,500 --> 01:01:40,000\nTwo\nlines\n")
    with pytest.raises(FileExistsError):
        tutorial.export_captions(tmp_path / "lesson.vtt")
    tutorial.export_captions(tmp_path / "lesson.vtt", overwrite=True)
    with pytest.raises(ValidationError, match=".vtt or .srt"):
        tutorial.export_captions(tmp_path / "lesson.txt")


def test_a_lesson_without_captions_writes_no_file(lesson, tmp_path):
    tutorial, _ = lesson
    tutorial.step("One")
    with pytest.raises(ValidationError, match="no captions"):
        tutorial.export_captions(tmp_path / "lesson.vtt")
    assert not (tmp_path / "lesson.vtt").exists()


def test_captions_burn_into_frames_at_the_bottom_only(lesson):
    tutorial, _ = lesson
    tutorial.step("One", duration=4).caption("The ball is blue.", at=1, until=3)
    source = tutorial.scene.to_dict()
    plain = tutorial.render_at_time(2).buffer
    burned = tutorial.render_at_time(2, captions=True).buffer
    changed = np.argwhere((plain != burned).any(axis=2))
    assert len(changed) and changed[:, 0].min() > 360 * 0.6  # only in the band near the bottom
    assert burned[int(360 * 0.9), 320].mean() < 90  # the dark band behind the text
    # Outside the cue, nothing is burned in.
    np.testing.assert_array_equal(tutorial.render_at_time(3.5, captions=True).buffer,
                                  tutorial.render_at_time(3.5).buffer)
    frames = list(tutorial.render_frames(fps=2, captions=True))
    np.testing.assert_array_equal(frames[4].buffer, burned)
    assert tutorial.scene.to_dict() == source  # the source scene is untouched


def test_the_player_gets_written_captions(lesson):
    tutorial, _ = lesson
    tutorial.step("Said", duration=2).narrate("A ball.")
    tutorial.step("Written", duration=2).caption("A ball.", at=0.5)
    assert tutorial.web_step(0)["captions"] is None
    assert tutorial.web_step(1)["captions"] == [["A ball.", 0.5, 2.0]]


def test_captions_round_trip_and_validate_against_the_schema(lesson):
    tutorial, _ = lesson
    tutorial.step("One", duration=4).caption("First.", until=1.5).caption("Second.", at=2)
    data = tutorial.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION >= 13  # captions came in v13
    assert data["steps"][0]["captions"] == [{"text": "First.", "at": 0.0, "until": 1.5},
                                            {"text": "Second.", "at": 2.0, "until": None}]
    schema = packaged_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)
    restored = Tutorial.from_dict(data)
    assert restored.to_dict() == data and restored.captions() == tutorial.captions()


def test_lint_reports_captions_too_fast_or_never_shown(lesson):
    tutorial, _ = lesson
    step = tutorial.step("One", duration=2)
    step.caption("This sentence is far too long to read in half a second.", at=0, until=0.5)
    step.caption("Fine.", at=1)
    step.caption("Too late.", at=5)
    codes = [issue.code for issue in tutorial.lint()]
    assert codes.count("CAPTION_TOO_FAST") == 1 and codes.count("CAPTION_NEVER_SHOWN") == 1
    assert [c.text for c in tutorial.captions()][-1] == "Fine."


def test_a_long_sentence_breaks_after_a_comma_and_leaves_no_word_alone(lesson):
    tutorial, _ = lesson
    tutorial.step("One", duration=2).narrate(
        "This one goes three to the right and two up, so we write it as a column of two numbers.")
    assert [c.text for c in tutorial.captions()] == [
        "This one goes three to the right and two up,", "so we write it as a column of two numbers."]

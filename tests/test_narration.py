"""Step.narrate: reveals timed to a voice's word timings."""

import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene

from tutordraw import Tutorial, ValidationError
from tutordraw.narration import find_phrase, parse_words, words_from_characters

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")

WORDS = [("The", 0.0, 0.1), ("nucleus", 0.1, 0.6), ("sits", 0.7, 0.9), ("in", 0.9, 1.0),
         ("the", 1.0, 1.1), ("middle", 1.1, 1.6), ("—", 1.6, 1.7), ("it", 1.8, 1.9),
         ("holds", 2.0, 2.3), ("the", 2.3, 2.4), ("cell's", 2.4, 2.8), ("DNA.", 2.8, 3.5)]


@pytest.fixture
def lesson():
    scene = Scene(600, 400, background=Color.white())
    cell = Circle(center=Point(300, 200), radius=120, fill=FillStyle(color=Color(230, 240, 240)))
    nucleus = Circle(center=Point(300, 200), radius=40, fill=FillStyle(color=Color(130, 150, 220)))
    scene.add(cell)
    scene.add(nucleus)
    tutorial = Tutorial(scene)
    return tutorial, tutorial.target(cell, name="cell"), tutorial.target(nucleus, name="nucleus")


def test_cues_appear_just_before_their_phrase_and_the_step_fits(lesson):
    tutorial, cell, nucleus = lesson
    step = tutorial.step("Nucleus", duration=2)
    label = nucleus.label("Nucleus")
    step.show(label).highlight(nucleus)
    note = step.explain(nucleus, "Holds the DNA.")
    arrow = step.connect((300, 20), nucleus)
    step.narrate(WORDS, {label: "nucleus", note: "holds the cell's DNA",
                         nucleus: "sits in the middle", arrow: "it holds"}, lead=0.2)
    assert step.revealed_at(label) == pytest.approx(0.0)  # 0.1 - 0.2, clamped
    assert step.revealed_at(note) == pytest.approx(1.8)
    assert step.revealed_at(arrow) == pytest.approx(1.6)
    assert step.highlights[0].at == pytest.approx(0.5)
    assert step.duration == pytest.approx(3.5 + 0.5)
    assert [w.text for w in step.narration][:2] == ["The", "nucleus"]
    # It is only reveal timing, so the finished step renders exactly as before.
    assert [a.text for a in tutorial.layout(0).annotations] == ["Nucleus", "Holds the DNA."]
    assert [a.text for a in tutorial.layout(0, time=1.0).annotations] == ["Nucleus"]


def test_phrases_match_across_case_punctuation_and_lone_dashes():
    words = parse_words(WORDS)
    assert find_phrase(words, "MIDDLE, it") == 5  # the dash between them is skipped
    assert find_phrase(words, "the cell's DNA") == 9
    assert find_phrase(words, "the") == 0  # the first occurrence
    with pytest.raises(ValidationError, match="not in the narration"):
        find_phrase(words, "mitochondria")
    with pytest.raises(ValidationError, match="no words"):
        find_phrase(words, "— !")


def test_word_formats_and_estimated_timing():
    dicts = parse_words([{"word": "Hi", "start": 0, "end": 0.2},
                         {"text": "there", "start_time": 0.3, "end_time": 0.6}])
    assert [(w.text, w.start, w.end) for w in dicts] == [("Hi", 0, 0.2), ("there", 0.3, 0.6)]
    estimated = parse_words("one two three four", rate=2)
    assert [w.start for w in estimated] == [0, 0.5, 1.0, 1.5] and estimated[-1].end == 2.0
    assert words_from_characters(list("Hi you"), [0, .1, .2, .3, .4, .5], [.1, .2, .3, .4, .5, .6]) == [
        ("Hi", 0, .2), ("you", .3, .6)]


@pytest.mark.parametrize("words", [
    [], "   ", [("a", 1, 0.5)], [("a", 0.5, 1), ("b", 0.2, 0.4)], [("", 0, 1)],
    [("a", -1, 1)], [("a", float("nan"), 1)], [("a", 0, 1, 2)], "text".encode(), [{"word": "x"}],
])
def test_bad_word_timings_are_refused(words):
    with pytest.raises(ValidationError):
        parse_words(words)


def test_bad_cues_change_nothing(lesson):
    tutorial, cell, nucleus = lesson
    step = tutorial.step("Guard", duration=2)
    label = nucleus.label("Nucleus")
    step.show(label)
    other = cell.label("Not shown")
    for cues in ({other: "nucleus"}, {cell: "nucleus"}, {label: "absent phrase"}, ["nucleus"]):
        with pytest.raises(ValidationError):
            step.narrate(WORDS, cues)
    # A failure part-way through leaves the step untouched.
    with pytest.raises(ValidationError):
        step.narrate(WORDS, {label: "nucleus", other: "middle"})
    assert step.reveals == {} and step.duration == 2 and step.narration == ()


def test_fit_false_keeps_the_duration_and_narration_reaches_the_player(lesson):
    tutorial, cell, nucleus = lesson
    step = tutorial.step("Short", duration=1)
    step.narrate(WORDS, fit=False)
    assert step.duration == 1
    payload = tutorial.web_step(0)
    assert payload["narration"][1] == ["nucleus", 0.1, 0.6]
    tutorial.step("Silent")
    assert tutorial.web_step(1)["narration"] is None


def test_narration_survives_save_and_load_with_its_captions(lesson, tmp_path):
    from jsonschema import Draft202012Validator

    from conftest import packaged_schema

    tutorial, _, nucleus = lesson
    step = tutorial.step("Spoken")
    label = nucleus.label("Nucleus")
    step.show(label)
    step.narrate([("The", 0.0, 0.2), ("nucleus", 0.25, 0.8), ("sits", 0.9, 1.1)], {label: "nucleus"})
    document = tutorial.to_dict()
    Draft202012Validator(packaged_schema()).validate(document)
    loaded = Tutorial.load_json(tutorial.save_json(tmp_path / "spoken.tutordraw.json"))
    again = loaded.steps[0]
    assert [(w.text, w.start, w.end) for w in again.narration] == [
        ("The", 0.0, 0.2), ("nucleus", 0.25, 0.8), ("sits", 0.9, 1.1)]
    assert again.revealed_at(again.labels[0]) == pytest.approx(0.1)  # timing kept, not replayed
    assert loaded.web_step(0)["narration"] == tutorial.web_step(0)["narration"]
    document["steps"][0]["narration"] = [["late", 2.0, 1.0]]
    from tutordraw import LessonFormatError
    with pytest.raises(LessonFormatError, match="narration"):
        Tutorial.from_dict(document)

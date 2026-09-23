from drawcv import Circle, Color, FillStyle, Point, Scene
from jsonschema import Draft202012Validator
import numpy as np
import pytest

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import LessonFormatError, Tutorial, ValidationError


@pytest.fixture
def lesson():
    scene = Scene(800, 300, background=Color.white())
    shape = Circle(center=Point(160, 150), radius=50,
                   fill=FillStyle(color=Color(120, 170, 210)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    return tutorial, tutorial.target(shape, name="subject")


def ink(canvas):
    return int((canvas.buffer < 240).any(axis=2).sum())


def test_annotations_appear_at_their_own_times(lesson):
    tutorial, subject = lesson
    step = tutorial.step("Reveal", duration=6)
    step.show(subject.label("First", anchor="top", gap=30))
    step.show(subject.label("Second", anchor="bottom", gap=30), at=2)
    step.explain(subject, "And the explanation arrives last.", gap=90, max_width=220, at=4)

    amounts = [ink(tutorial.render_at_time(t)) for t in (0, 1.9, 2, 3.9, 4, 6)]
    assert amounts[0] == amounts[1] < amounts[2] == amounts[3] < amounts[4] == amounts[5]
    # The finished state is what a still export shows.
    assert ink(tutorial.render_step(0)) == amounts[-1]


def test_without_a_delay_nothing_changes(lesson):
    """A step with no reveals stays a hard cut, frame for frame."""
    tutorial, subject = lesson
    tutorial.step("Plain", duration=4).show(subject.label("Label", anchor="top", gap=30))
    assert tutorial.steps[0].reveals == {}
    for time in (0, 1, 2, 3, 4):
        np.testing.assert_array_equal(tutorial.render_at_time(time).buffer,
                                      tutorial.render_step(0).buffer)


def test_a_reveal_alone_makes_the_step_time_varying(lesson):
    """Revealing must not require calling animate() as well."""
    tutorial, subject = lesson
    step = tutorial.step("Reveal", duration=4)
    step.show(subject.label("Late", anchor="top", gap=30), at=2)
    assert step.easing is None
    assert ink(tutorial.render_at_time(0)) < ink(tutorial.render_at_time(3))


def test_a_delay_past_the_duration_reveals_at_the_end(lesson):
    tutorial, subject = lesson
    step = tutorial.step("Late", duration=3)
    step.show(subject.label("Eventually", anchor="top", gap=30), at=99)
    assert ink(tutorial.render_at_time(0)) < ink(tutorial.render_at_time(3))
    np.testing.assert_array_equal(tutorial.render_at_time(3).buffer,
                                  tutorial.render_step(0).buffer)


def test_reveals_combine_with_animation(lesson):
    tutorial, subject = lesson
    tutorial.step("Before", duration=2)
    step = tutorial.step("Both", duration=4).animate("linear")
    step.restyle(subject, move=(300, 0))
    step.show(subject.label("Arrives", anchor="top", gap=30), at=2)

    def centre(canvas):
        columns = np.nonzero((canvas.buffer < 240).any(axis=(0, 2)))[0]
        return (columns.min() + columns.max()) / 2

    early, late = tutorial.render_at_time(3), tutorial.render_at_time(5)
    assert ink(early) < ink(late)          # The label joined partway through.
    assert centre(early) < centre(late)    # The artwork kept moving.


def test_the_same_label_can_be_timed_differently_per_step(lesson):
    tutorial, subject = lesson
    label = subject.label("Shared", anchor="top", gap=30)
    first = tutorial.step("Early", duration=4).show(label)
    second = tutorial.step("Late", duration=4).show(label, at=3)
    assert first.revealed_at(label) == 0 and second.revealed_at(label) == 3
    assert ink(tutorial.render_at_time(0)) > ink(tutorial.render_at_time(4.5))


def test_explain_accepts_a_delay_and_returns_the_callout(lesson):
    tutorial, subject = lesson
    step = tutorial.step("Explain", duration=4)
    callout = step.explain(subject, "Later.", gap=80, max_width=180, at=2)
    assert step.revealed_at(callout) == 2
    assert callout in step.callouts


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "2", object()])
def test_invalid_delays_rejected(lesson, value):
    tutorial, subject = lesson
    step = tutorial.step("Guard", duration=4)
    label = subject.label("Label")
    with pytest.raises(ValidationError):
        step.show(label, at=value)
    with pytest.raises(ValidationError):
        step.explain(subject, "Text", at=value)
    assert step.reveals == {}


def test_revealed_at_rejects_non_annotations(lesson):
    tutorial, subject = lesson
    step = tutorial.step("Guard")
    with pytest.raises(ValidationError, match="label, callout or mark"):
        step.revealed_at("not an annotation")


def test_reveals_round_trip_and_validate_against_the_schema(lesson):
    tutorial, subject = lesson
    step = tutorial.step("Reveal", duration=6)
    label = subject.label("Second", anchor="bottom", gap=30)
    step.show(subject.label("First", anchor="top", gap=30))
    step.show(label, at=2.5)
    step.explain(subject, "Last.", gap=80, max_width=180, at=4)

    data = tutorial.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    assert sorted(data["steps"][0]["reveals"].values()) == [2.5, 4.0]
    schema = packaged_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)

    restored = Tutorial.from_dict(data)
    assert restored.to_dict() == data
    for time in (0, 3, 5):
        np.testing.assert_array_equal(restored.render_at_time(time).buffer,
                                      tutorial.render_at_time(time).buffer)


@pytest.mark.parametrize("damage,message", [
    (lambda s: s["reveals"].update(nope=1.0), "unknown annotation"),
    (lambda s: s["reveals"].update({next(iter(s["reveals"])): -1}), "at"),
    (lambda s: s["reveals"].update({next(iter(s["reveals"])): "soon"}), "at"),
    (lambda s: s.update(reveals=[]), "must be an object"),
])
def test_malformed_reveals_are_rejected_with_context(lesson, damage, message):
    tutorial, subject = lesson
    step = tutorial.step("Reveal", duration=6)
    step.show(subject.label("Later", anchor="top", gap=30), at=2)
    data = tutorial.to_dict()
    damage(data["steps"][0])
    with pytest.raises(LessonFormatError, match=message):
        Tutorial.from_dict(data)


def test_source_survives_a_partially_revealed_render(lesson):
    from copy import deepcopy

    tutorial, subject = lesson
    step = tutorial.step("Reveal", duration=4)
    step.show(subject.label("Late", anchor="top", gap=30), at=2)
    before = deepcopy(tutorial.scene.to_dict())
    history = tutorial.scene.history.undo_count
    for time in (0, 1, 3):
        tutorial.render_at_time(time)
    assert tutorial.scene.to_dict() == before
    assert tutorial.scene.history.undo_count == history

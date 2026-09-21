from copy import deepcopy
from importlib.resources import files
import json

from drawcv import Circle, Color, FillStyle, Point, Scene
from jsonschema import Draft202012Validator
import numpy as np
import pytest

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import LessonFormatError, Tutorial, ValidationError


@pytest.fixture
def lesson():
    scene = Scene(500, 200, background=Color.white())
    moon = Circle(center=Point(80, 100), radius=30,
                  fill=FillStyle(color=Color(210, 210, 210)))
    scene.add(moon)
    tutorial = Tutorial(scene)
    target = tutorial.target(moon, name="moon")
    tutorial.step("Start", duration=2)
    tutorial.step("Slide", duration=4, pause=1).restyle(target, move=(320, 0))
    return tutorial, target


def centre(image):
    columns = np.nonzero((image < 240).any(axis=(0, 2)))[0]
    return (columns.min() + columns.max()) / 2


def test_hard_cuts_remain_the_default(lesson):
    """Every frame must still equal a render_step until animate() is called."""
    tutorial, _ = lesson
    assert tutorial.steps[1].easing is None
    for time, index in [(0, 0), (1.9, 0), (2, 1), (4, 1), (6, 1), (7, 1)]:
        np.testing.assert_array_equal(tutorial.render_at_time(time).buffer,
                                      tutorial.render_step(index).buffer)


def test_animation_interpolates_from_the_previous_step(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("linear")
    start, end = centre(tutorial.render_step(0).buffer), centre(tutorial.render_step(1).buffer)
    assert end - start == pytest.approx(320, abs=2)

    # The step begins where the previous one left off and arrives on time.
    assert centre(tutorial.render_at_time(2).buffer) == pytest.approx(start, abs=2)
    assert centre(tutorial.render_at_time(6).buffer) == pytest.approx(end, abs=2)
    for fraction in (0.25, 0.5, 0.75):
        image = tutorial.render_at_time(2 + 4 * fraction).buffer
        assert centre(image) == pytest.approx(start + 320 * fraction, abs=3)


def test_render_step_still_means_the_final_state(lesson):
    """Static export must not change meaning when a step animates."""
    tutorial, _ = lesson
    before = tutorial.render_step(1).buffer.copy()
    tutorial.steps[1].animate("ease_in_out")
    np.testing.assert_array_equal(tutorial.render_step(1).buffer, before)


def test_pause_holds_the_finished_state(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("linear")
    final = tutorial.render_step(1).buffer
    for time in (6, 6.5, 7):
        np.testing.assert_array_equal(tutorial.render_at_time(time).buffer, final)


def test_easing_changes_the_path_but_not_the_endpoints(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("linear")
    linear = centre(tutorial.render_at_time(3).buffer)
    ends = [tutorial.render_at_time(t).buffer.copy() for t in (2, 6)]

    tutorial.steps[1].animate("ease_in_out")
    assert centre(tutorial.render_at_time(3).buffer) < linear  # Slow start.
    for time, expected in zip((2, 6), ends):
        np.testing.assert_array_equal(tutorial.render_at_time(time).buffer, expected)


def test_colour_interpolates_between_steps():
    scene = Scene(200, 200, background=Color.white())
    shape = Circle(center=Point(100, 100), radius=50,
                   fill=FillStyle(color=Color(0, 0, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="shape")
    tutorial.step("Blue", duration=2)
    tutorial.step("Red", duration=2).restyle(target, fill=(200, 0, 0)).animate("linear")

    def middle(time):
        return tutorial.render_at_time(time).buffer[100, 100]

    blue, half, red = middle(2), middle(3), middle(4)
    # Buffers are BGR: blue falls away as red climbs, and halfway is between.
    assert blue[0] > half[0] > red[0]
    assert blue[2] < half[2] < red[2]


def test_a_target_slides_back_when_the_next_step_drops_it(lesson):
    tutorial, target = lesson
    tutorial.steps[1].animate("linear")
    third = tutorial.step("Return", duration=4).animate("linear")
    assert third.restyles == ()

    moved = centre(tutorial.render_step(1).buffer)
    home = centre(tutorial.render_step(0).buffer)
    assert centre(tutorial.render_at_time(7).buffer) == pytest.approx(moved, abs=2)
    assert centre(tutorial.render_at_time(9).buffer) == pytest.approx((moved + home) / 2, abs=3)
    assert centre(tutorial.render_at_time(11).buffer) == pytest.approx(home, abs=2)


def test_the_first_step_animates_from_the_untouched_drawing():
    scene = Scene(400, 200, background=Color.white())
    shape = Circle(center=Point(60, 100), radius=25, fill=FillStyle(color=Color(30, 30, 30)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="shape")
    tutorial.step("Enter", duration=4).restyle(target, move=(200, 0)).animate("linear")

    plain = Tutorial(Scene(400, 200, background=Color.white()))
    assert centre(tutorial.render_at_time(0).buffer) == pytest.approx(60, abs=2)
    assert centre(tutorial.render_at_time(4).buffer) == pytest.approx(260, abs=2)
    assert plain.steps == ()


def test_frames_and_video_follow_the_animation(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("linear")
    frames = list(tutorial.render_frames(fps=2))
    assert len(frames) == 14  # ceil(7 * 2)
    positions = [centre(frame.buffer) for frame in frames]
    moving = positions[4:12]  # t = 2.0 .. 5.5, inside the animated duration
    assert all(b >= a for a, b in zip(moving, moving[1:]))
    assert moving[-1] > moving[0] + 200


@pytest.mark.parametrize("easing", [None, 1, "nope", "", "ease in out"])
def test_invalid_easing_rejected(lesson, easing):
    tutorial, _ = lesson
    with pytest.raises(ValidationError):
        tutorial.steps[1].animate(easing)
    assert tutorial.steps[1].easing is None


def test_easing_names_are_stored_canonically(lesson):
    """DrawCV matches case-insensitively; one spelling reaches the lesson file."""
    tutorial, _ = lesson
    assert tutorial.steps[1].animate("LINEAR").easing == "linear"
    assert tutorial.to_dict()["steps"][1]["easing"] == "linear"


def test_hard_cut_undoes_animation(lesson):
    tutorial, _ = lesson
    step = tutorial.steps[1]
    assert step.animate("linear").easing == "linear"
    assert step.hard_cut() is step and step.easing is None
    np.testing.assert_array_equal(tutorial.render_at_time(3).buffer,
                                  tutorial.render_step(1).buffer)


def test_easing_round_trips_and_validates_against_the_schema(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("ease_out_cubic")
    data = tutorial.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    assert [step["easing"] for step in data["steps"]] == [None, "ease_out_cubic"]

    schema = packaged_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)

    restored = Tutorial.from_dict(data)
    assert restored.steps[1].easing == "ease_out_cubic"
    np.testing.assert_array_equal(restored.render_at_time(3.5).buffer,
                                  tutorial.render_at_time(3.5).buffer)


def test_unknown_persisted_easing_is_rejected(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("linear")
    data = tutorial.to_dict()
    data["steps"][1]["easing"] = "wobble"
    with pytest.raises(LessonFormatError, match="easing"):
        Tutorial.from_dict(data)


def test_source_survives_an_animated_render(lesson):
    tutorial, _ = lesson
    tutorial.steps[1].animate("ease_in_out")
    before = deepcopy(tutorial.scene.to_dict())
    history = tutorial.scene.history.undo_count
    for time in (2.5, 3, 4.5):
        tutorial.render_at_time(time)
    assert tutorial.scene.to_dict() == before
    assert tutorial.scene.history.undo_count == history

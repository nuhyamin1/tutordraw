from copy import deepcopy
from importlib.resources import files
import json

from drawcv import Circle, Color, FillStyle, Point, Scene
import numpy as np
import pytest
from jsonschema import Draft202012Validator

from conftest import SCHEMA_VERSION, downgrade, fields_after, packaged_schema
from tutordraw import LessonFormatError, Tutorial, ValidationError


@pytest.fixture
def lesson():
    scene = Scene(400, 300, background=Color.white())
    shape = Circle(center=Point(140, 150), radius=30,
                   fill=FillStyle(color=Color(80, 130, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="subject")
    tutorial.step("Focus", duration=1, pause=0.5).highlight(target)
    tutorial.step("Review", duration=0.75)
    return tutorial


def test_boundaries_pauses_endpoint_and_out_of_order_pixels(lesson):
    original = deepcopy(lesson.scene.to_dict())
    history = lesson.scene.history.undo_count
    assert lesson.duration == 2.25
    for time, index in [(2.25, 1), (0, 0), (1.5, 1), (1.4999, 0), (1, 0)]:
        assert lesson.step_at_time(time) == index
        np.testing.assert_array_equal(lesson.render_at_time(time).buffer,
                                      lesson.render_step(index).buffer)
    assert lesson.scene.to_dict() == original
    assert lesson.scene.history.undo_count == history


@pytest.mark.parametrize("value", [-1, True, None, "1", float("nan"), float("inf")])
def test_invalid_times(lesson, value):
    with pytest.raises(ValidationError):
        lesson.render_at_time(value)
    with pytest.raises(ValidationError):
        lesson.step_at_time(2.25001)


@pytest.mark.parametrize("options", [dict(duration=0), dict(duration=-1), dict(duration=True),
    dict(duration=None), dict(duration=float("nan")), dict(duration=float("inf")),
    dict(duration=1, pause=-1), dict(duration=1, pause=True), dict(duration=1, pause=None),
    dict(duration=1e308, pause=1e308)])
def test_timing_validation_is_atomic(lesson, options):
    first = lesson.steps[0]
    with pytest.raises(ValidationError):
        first.set_timing(**options)
    assert (first.duration, first.pause) == (1, 0.5)
    with pytest.raises(ValidationError):
        lesson.step("Invalid", **options)
    assert len(lesson.steps) == 2


def test_defaults_retiming_and_read_only_properties(lesson):
    step = lesson.step("Default")
    assert (step.duration, step.pause) == (3, 0)
    assert step.set_timing(duration=2, pause=1) is step
    assert lesson.duration == 5.25
    step.set_timing(duration=4)
    assert step.pause == 0
    with pytest.raises(AttributeError):
        step.duration = 7


def test_frames_sample_schedule_and_are_independent(lesson):
    frames = list(lesson.render_frames(fps=2, alpha=True))
    assert len(frames) == 5  # ceil(2.25 * 2), t=0, .5, 1, 1.5, 2
    for frame, index in zip(frames, [0, 0, 0, 1, 1]):
        np.testing.assert_array_equal(frame.buffer, lesson.render_step(index, alpha=True).buffer)
    before = frames[1].buffer.copy()
    frames[0].buffer[:] = 0
    np.testing.assert_array_equal(frames[1].buffer, before)


@pytest.mark.parametrize("fps", [0, -1, True, 2.5, float("inf"), "30"])
def test_invalid_frame_rate_rejected_eagerly(lesson, fps):
    with pytest.raises(ValidationError):
        lesson.render_frames(fps=fps)


def test_empty_lesson_and_alpha_validation():
    lesson = Tutorial(Scene(100, 100))
    assert lesson.duration == 0
    with pytest.raises(ValidationError):
        lesson.render_frames()
    with pytest.raises(ValidationError):
        lesson.render_at_time(0)
    lesson.step("one")
    with pytest.raises(ValidationError):
        lesson.render_frames(alpha=1)
    with pytest.raises(ValidationError):
        lesson.render_at_time(0, alpha=1)


def test_overflow_and_unrepresentable_intervals():
    lesson = Tutorial(Scene(100, 100))
    lesson.step("one", duration=1e308)
    with pytest.raises(ValidationError):
        lesson.render_frames(fps=30)
    lesson.step("two", duration=1e308)
    with pytest.raises(ValidationError):
        _ = lesson.duration
    lesson.steps[1].set_timing(duration=1)
    with pytest.raises(ValidationError):
        _ = lesson.duration


def test_timing_roundtrip_and_v1_upgrade(lesson):
    data = lesson.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    restored = Tutorial.from_dict(data)
    assert restored.to_dict() == data
    assert restored.duration == 2.25
    legacy = downgrade(data, 1)
    schema = json.loads(files("tutordraw").joinpath("lesson-v1.schema.json").read_text())
    Draft202012Validator(schema).validate(legacy)
    upgraded = Tutorial.from_dict(legacy)
    assert upgraded.duration == 6
    assert upgraded.to_dict()["schema_version"] == SCHEMA_VERSION
    assert legacy["schema_version"] == 1
    for i in range(2):
        assert upgraded.steps[i].id == lesson.steps[i].id
        np.testing.assert_array_equal(upgraded.render_step(i).buffer, lesson.render_step(i).buffer)


@pytest.mark.parametrize("field,value", [("duration", 0), ("duration", None), ("pause", -1), ("pause", True)])
def test_invalid_persisted_timing(lesson, field, value):
    data = lesson.to_dict()
    data["steps"][0][field] = value
    with pytest.raises(LessonFormatError):
        Tutorial.from_dict(data)


def test_step_fields_are_required_per_version(lesson):
    data = lesson.to_dict()
    del data["steps"][0]["pause"]
    with pytest.raises(LessonFormatError, match="missing"):
        Tutorial.from_dict(data)
    # A v3 document declared as v1 or v2 carries fields those versions forbid.
    for version in (1, 2, 3, 4):
        data = lesson.to_dict()
        data["schema_version"] = version
        with pytest.raises(LessonFormatError, match="unknown") as caught:
            Tutorial.from_dict(data)
        assert any(field in str(caught.value) for field in fields_after(version))

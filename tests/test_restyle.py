from copy import deepcopy
from importlib.resources import files
import json

from drawcv import Circle, Color, FillStyle, Group, Line, Point, Scene, Text
from jsonschema import Draft202012Validator
import numpy as np
import pytest

from conftest import LEGACY_VERSIONS, SCHEMA_VERSION, downgrade, packaged_schema
from tutordraw import Tutorial, ValidationError


@pytest.fixture
def lesson():
    scene = Scene(600, 300, background=Color.white())
    moon = Circle(center=Point(150, 150), radius=40,
                  fill=FillStyle(color=Color(200, 200, 200)))
    ray = Line(start=Point(20, 150), end=Point(100, 150))
    caption = Text(text="Moon", position=Point(20, 20))
    pair = Group(children=[Circle(center=Point(420, 150), radius=25,
                                  fill=FillStyle(color=Color(20, 90, 180)))])
    for shape in (moon, ray, caption, pair):
        scene.add(shape)
    tutorial = Tutorial(scene)
    return (tutorial, tutorial.target(moon, name="moon"), tutorial.target(ray, name="ray"),
            tutorial.target(caption, name="caption"), tutorial.target(pair, name="pair"))


def test_move_and_recolor_change_only_this_step(lesson):
    tutorial, moon, *_ = lesson
    before = deepcopy(tutorial.scene.to_dict())
    history = tutorial.scene.history.undo_count
    plain = tutorial.step("Before")
    tutorial.step("After").restyle(moon, move=(200, 30), fill=(200, 60, 50))

    first, second = tutorial.render_step(0).buffer, tutorial.render_step(1).buffer
    assert not np.array_equal(first, second)
    # The unchanged step is still unchanged after the restyled one rendered.
    np.testing.assert_array_equal(tutorial.render_step(0).buffer, first)
    assert tutorial.scene.to_dict() == before
    assert tutorial.scene.history.undo_count == history
    assert plain.restyles == ()


def build_moon_lesson(shift):
    """The same lesson twice: once shifted at the source, once by restyle."""
    scene = Scene(600, 300, background=Color.white())
    moon = Circle(center=Point(150, 150), radius=40,
                  fill=FillStyle(color=Color(200, 200, 200)))
    scene.add(moon)
    tutorial = Tutorial(scene)
    target = tutorial.target(moon, name="moon")
    step = tutorial.step("Move").show(target.label("Moon", anchor="top", gap=20))
    step.highlight(target)
    return tutorial, moon, target, step


def test_moving_by_restyle_matches_moving_the_source(lesson):
    """Labels, leaders and the highlight box must all follow the moved artwork."""
    restyled, _, target, step = build_moon_lesson(150)
    step.restyle(target, move=(150, 0))

    moved_source, shape, _, _ = build_moon_lesson(150)
    shape.transform.translation_x += 150

    np.testing.assert_array_equal(restyled.render_step(0).buffer,
                                  moved_source.render_step(0).buffer)
    # Sanity: the shift genuinely changed the image.
    untouched, *_ = build_moon_lesson(0)
    assert not np.array_equal(restyled.render_step(0).buffer,
                              untouched.render_step(0).buffer)


def test_move_is_relative_to_the_source_transform(lesson):
    tutorial, moon, *_ = lesson
    moon.drawable.transform.translation_x = 40
    step = tutorial.step("Move").restyle(moon, move=(60, 0))
    shifted = tutorial.render_step(0).buffer.copy()

    moon.drawable.transform.translation_x = 100
    step.restyle(moon, move=(0, 0))
    np.testing.assert_array_equal(tutorial.render_step(0).buffer, shifted)


def test_visible_false_hides_artwork_and_blocks_emphasis(lesson):
    tutorial, moon, *_ = lesson
    shown = tutorial.step("Shown")
    hidden = tutorial.step("Hidden").restyle(moon, visible=False)
    assert not np.array_equal(tutorial.render_step(0).buffer, tutorial.render_step(1).buffer)

    hidden.highlight(moon)
    with pytest.raises(ValidationError, match="hidden target"):
        tutorial.render_step(1)
    assert shown.restyles == ()


def test_opacity_override_then_dimming_multiplies(lesson):
    """Restyle sets an absolute opacity; dim_others then multiplies unrelated branches."""
    tutorial, moon, ray, caption, pair = lesson
    faded = tutorial.step("Faded").restyle(moon, opacity=0.5)
    solid = tutorial.step("Solid")
    moon_pixel = (150, 150)
    base = tutorial.render_step(1).buffer[moon_pixel]
    half = tutorial.render_step(0).buffer[moon_pixel]
    assert np.all(half > base)  # Lighter against white.

    faded.dim_others(pair, opacity=0.5)
    both = tutorial.render_step(0).buffer[moon_pixel]
    assert np.all(both > half)  # Dimming compounds on top of the override.


def test_fill_applies_to_text_color_and_is_refused_for_lines(lesson):
    tutorial, moon, ray, caption, pair = lesson
    step = tutorial.step("Recolor")
    plain = tutorial.render_step(0).buffer.copy()
    step.restyle(caption, fill=(220, 30, 30))
    assert not np.array_equal(tutorial.render_step(0).buffer, plain)

    for target in (ray, pair):
        with pytest.raises(ValidationError, match="fill cannot be set"):
            step.restyle(target, fill=(1, 2, 3))


def test_repeating_restyle_replaces_rather_than_accumulates(lesson):
    tutorial, moon, *_ = lesson
    step = tutorial.step("Move")
    step.restyle(moon, move=(100, 0))
    once = tutorial.render_step(0).buffer.copy()
    step.restyle(moon, move=(100, 0))
    assert len(step.restyles) == 1
    np.testing.assert_array_equal(tutorial.render_step(0).buffer, once)
    # The replacement is total: dropping fill from the call clears it.
    step.restyle(moon, fill=(10, 200, 10))
    assert step.restyles[0].move is None


@pytest.mark.parametrize("options", [
    {}, dict(move=(1,)), dict(move="10,10"), dict(move=(1, float("nan"))),
    dict(move=(1, True)), dict(fill=(1, 2)), dict(fill=(0, 0, 256)), dict(fill="red"),
    dict(opacity=-0.1), dict(opacity=1.1), dict(opacity="half"), dict(opacity=float("inf")),
    dict(visible=1), dict(visible="yes"),
])
def test_invalid_options_rejected_and_leave_the_step_alone(lesson, options):
    tutorial, moon, *_ = lesson
    step = tutorial.step("Guard").restyle(moon, move=(5, 5))
    with pytest.raises(ValidationError):
        step.restyle(moon, **options)
    assert step.restyles[0].move == (5, 5)


def test_foreign_target_is_refused(lesson):
    tutorial = lesson[0]
    other = Tutorial(Scene(100, 100))
    shape = Circle(center=Point(50, 50), radius=10)
    other.scene.add(shape)
    with pytest.raises(ValidationError, match="Target must belong"):
        tutorial.step("Foreign").restyle(other.target(shape))


def test_restyles_survive_the_round_trip_and_validate_against_the_schema(lesson):
    tutorial, moon, ray, caption, pair = lesson
    tutorial.step("One").restyle(moon, move=(120, 10), fill=(180, 60, 40), opacity=0.7)
    tutorial.step("Two").restyle(pair, visible=False).restyle(caption, fill=(5, 5, 5))

    data = tutorial.to_dict()
    assert data["schema_version"] == SCHEMA_VERSION
    schema = packaged_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)

    restored = Tutorial.from_dict(data)
    assert restored.to_dict() == data
    for index in range(2):
        np.testing.assert_array_equal(restored.render_step(index).buffer,
                                      tutorial.render_step(index).buffer)
    first = restored.steps[0].restyles[0]
    assert (first.move, first.fill, first.opacity, first.visible) == ((120, 10), (180, 60, 40), 0.7, None)


@pytest.mark.parametrize("version", LEGACY_VERSIONS)
def test_every_older_schema_version_still_loads(lesson, version):
    """One test covers all past versions, so a bump needs no new case here."""
    tutorial, moon, *_ = lesson
    tutorial.step("One")
    data = tutorial.to_dict()

    upgraded = Tutorial.from_dict(downgrade(data, version))
    assert upgraded.steps[0].restyles == ()
    assert upgraded.steps[0].easing is None
    assert upgraded.steps[0].reveals == {}
    assert upgraded.to_dict()["schema_version"] == SCHEMA_VERSION
    np.testing.assert_array_equal(upgraded.render_step(0).buffer, tutorial.render_step(0).buffer)


@pytest.mark.parametrize("damage,message", [
    (lambda s: s["restyles"].append(dict(s["restyles"][0])), "duplicate restyle"),
    (lambda s: s["restyles"][0].update(target_id="nope"), "unknown reference"),
    (lambda s: s["restyles"][0].update(opacity=2), "opacity"),
    (lambda s: s["restyles"][0].update(fill=[0, 0, 300]), "fill"),
    (lambda s: s["restyles"][0].update(move=[1, 2, 3]), "move"),
    (lambda s: s["restyles"][0].update(move=None, fill=None, opacity=None, visible=None), "at least one"),
    (lambda s: s["restyles"][0].pop("visible"), "missing fields"),
    (lambda s: s["restyles"][0].update(extra=1), "unknown fields"),
])
def test_malformed_restyles_are_rejected_with_context(lesson, damage, message):
    from tutordraw import LessonFormatError

    tutorial, moon, *_ = lesson
    tutorial.step("One").restyle(moon, move=(10, 0), fill=(1, 2, 3), opacity=0.5, visible=True)
    data = tutorial.to_dict()
    damage(data["steps"][0])
    with pytest.raises(LessonFormatError, match=message):
        Tutorial.from_dict(data)

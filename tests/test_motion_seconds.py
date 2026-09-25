"""A step whose motion takes only its first few seconds: animate(seconds=).

An animated step eased its restyles across its whole duration. A tutor that
makes room on a full board (sliding its working up, fading the oldest line)
wants that done in a moment, before it starts writing; the rest of the step
holds still. `seconds` is how long the motion takes; reveals and draw-on keep
the step's own clock.
"""

import json

import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import Tutorial, ValidationError

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(seconds=0.5, easing="linear"):
    scene = Scene(600, 400, background=Color.white())
    dot = Circle(center=Point(100, 200), radius=8, fill=FillStyle(color=Color(120, 90, 200)))
    scene.add(dot)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    tutorial.step("Rest", duration=1)
    tutorial.step("Glide", duration=4).animate(easing, seconds=seconds).restyle(target, move=(200, 0))
    return tutorial, target


def x(tutorial, index, time=None):
    return tutorial.layout(index, time=time).targets["dot"].center.x - 100


def test_the_motion_ends_after_its_seconds_and_the_step_holds():
    tutorial, _ = lesson()
    assert x(tutorial, 1, 0.25) == pytest.approx(100)   # half way through half a second
    assert x(tutorial, 1, 0.5) == pytest.approx(200)
    assert x(tutorial, 1, 3.0) == pytest.approx(200)
    assert tutorial.steps[1].motion == 0.5
    whole, _ = lesson(seconds=None)
    assert x(whole, 1, 2.0) == pytest.approx(100) and whole.steps[1].motion is None


def test_seconds_are_checked():
    tutorial, _ = lesson()
    for bad in (0, -1, float("inf"), True, "1"):
        with pytest.raises(ValidationError, match="seconds"):
            tutorial.steps[1].animate("linear", seconds=bad)
    tutorial.steps[1].animate("linear", seconds=9)  # longer than the step: the motion takes the whole step
    assert x(tutorial, 1, 2.0) == pytest.approx(100)


def test_the_player_is_told_how_long_the_motion_takes():
    tutorial, _ = lesson(easing="ease_in_out")
    payload = tutorial.web_step(1)
    assert payload["motion"] == 0.5 and payload["easing"] is not None
    assert lesson(seconds=None)[0].web_step(1)["motion"] is None


def test_motion_seconds_are_saved_and_loaded():
    tutorial, _ = lesson()
    document = tutorial.to_dict()
    assert document["schema_version"] == SCHEMA_VERSION == 11
    assert document["steps"][1]["motion"] == 0.5 and document["steps"][0]["motion"] is None
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(document, packaged_schema())
    loaded = Tutorial.from_json(json.dumps(document))
    assert loaded.steps[1].motion == 0.5
    assert x(loaded, 1, 0.25) == pytest.approx(100)


def test_a_hard_cut_forgets_its_seconds():
    tutorial, _ = lesson()
    tutorial.steps[1].hard_cut()
    assert tutorial.steps[1].motion is None

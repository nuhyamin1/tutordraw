"""Moving along a path: a point slides along y = f(x) instead of cutting straight across.

Step.animate eased every move in a straight line, so a point could not
follow a curve and lessons had to show one position per step. A restyle's
`via` lists the offsets the move passes through; the motion follows that
polyline at constant speed along its length, and Axes.along samples a curve
into such offsets.
"""

import json
import math

import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import Tutorial, ValidationError
from tutordraw.kits import Axes

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(via=((100, -80),), move=(200, 0), easing="linear", height=400):
    scene = Scene(600, height, background=Color.white())
    dot = Circle(center=Point(100, 300), radius=8, fill=FillStyle(color=Color(120, 90, 200)))
    scene.add(dot)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    tutorial.step("Rest", duration=1)
    tutorial.step("Along", duration=2).animate(easing).restyle(target, move=move, via=via)
    return tutorial, target


def centre(tutorial, index, time=None):
    box = tutorial.layout(index, time=time).targets["dot"]
    return box.center.x - 100, box.center.y - 300


def test_the_move_passes_through_its_via_points_at_even_speed():
    tutorial, _ = lesson()
    assert centre(tutorial, 1, 1.0) == pytest.approx((100, -80))   # halfway along two equal legs
    assert centre(tutorial, 1, 0.5) == pytest.approx((50, -40))    # a quarter: halfway up the first leg
    assert centre(tutorial, 1) == pytest.approx((200, 0))          # the step ends where `move` says
    assert centre(tutorial, 0) == pytest.approx((0, 0))


def test_without_via_the_move_is_still_straight():
    tutorial, _ = lesson(via=None)
    assert centre(tutorial, 1, 1.0) == pytest.approx((100, 0))


def test_a_label_rides_along_the_path():
    tutorial, target = lesson(height=700)  # room below too, so the panel is never held at an edge
    label = target.label("P", anchor="top")
    tutorial.steps[1].show(label)
    offsets = set()
    for time in (0.0, 0.5, 1.0, 1.5, 2.0):
        [panel] = [a.panel for a in tutorial.layout(1, time=time).annotations]
        dx, dy = centre(tutorial, 1, time)
        offsets.add((round(panel.center.x - dx, 3), round(panel.center.y - dy, 3)))
    assert len(offsets) == 1  # one placement, carried along the curve with its dot


def test_via_needs_a_move_and_valid_points():
    tutorial, target = lesson()
    step = tutorial.step("More")
    with pytest.raises(ValidationError, match="via needs move"):
        step.restyle(target, via=[(1, 2)])
    for bad in ([(1,)], [(1, math.inf)], "no", [(0, 0)] * 257, []):
        with pytest.raises(ValidationError, match="via"):
            step.restyle(target, move=(1, 1), via=bad)


def test_the_player_gets_keyframes_along_the_path():
    tutorial, _ = lesson(easing="ease_in_out")
    payload = tutorial.web_step(1)
    from tutordraw.web import PATH_KEYFRAMES
    assert len(payload["frames"]) == PATH_KEYFRAMES and payload["easing"] is None  # easing applied per frame
    straight = lesson(via=None)[0].web_step(1)
    assert len(straight["frames"]) == 1 and straight["easing"] is not None


def test_via_is_saved_and_loaded(tmp_path):
    tutorial, _ = lesson()
    document = tutorial.to_dict()
    assert document["schema_version"] == SCHEMA_VERSION == 10
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(document, packaged_schema())
    restyle = document["steps"][1]["restyles"][0]
    assert restyle["via"] == [[100, -80]]
    assert document["steps"][0]["restyles"] == []
    loaded = Tutorial.from_json(json.dumps(document))
    assert loaded.steps[1].restyles[0].via == ((100.0, -80.0),)
    assert centre(loaded, 1, 1.0) == pytest.approx((100, -80))


def test_axes_along_samples_a_curve_into_offsets():
    tutorial = Tutorial(Scene(700, 500, background=Color.white()))
    axes = Axes(tutorial, box=(100, 50, 500, 400), x_range=(-2, 3), y_range=(-1, 9), x_step=1, y_step=1)
    offsets = axes.along(lambda x: x * x, 1, 2, samples=10)
    assert len(offsets) == 11
    start = axes.to_scene(1, 1)
    for k, (dx, dy) in enumerate(offsets):
        x = 1 + k / 10
        p = axes.to_scene(x, x * x)
        assert (dx, dy) == pytest.approx((p.x - start.x, p.y - start.y))
    # Offsets from where the thing was first drawn, when it has moved before.
    later = axes.along(lambda x: x * x, 1.5, 2, samples=4, start=(1, 1))
    p = axes.to_scene(1.5, 2.25)
    assert later[0] == pytest.approx((p.x - start.x, p.y - start.y))
    with pytest.raises(ValidationError, match="no value"):
        axes.along(lambda x: 1 / x, -1, 1, samples=4)

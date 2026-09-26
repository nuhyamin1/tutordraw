"""The presenter's pointer: one hand that glides to what the narrator means (Step.point)."""

import math

import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Point, Rectangle, Scene
from jsonschema import Draft202012Validator

from conftest import packaged_schema
from tutordraw import Theme, Tutorial, ValidationError
from tutordraw.pointer import APPEAR, TAP, TAP_SCALE, pose_at

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(theme=None):
    scene = Scene(640, 360, background=Color(245, 247, 250))
    ball = Circle(center=Point(160, 150), radius=40, fill=FillStyle(color=Color(80, 120, 200)))
    box = Rectangle(position=Point(400, 110), width=100, height=80, fill=FillStyle(color=Color(200, 150, 90)))
    scene.add(ball)
    scene.add(box)
    tutorial = Tutorial(scene, theme=theme)
    return tutorial, tutorial.target(ball, name="ball"), tutorial.target(box, name="box")


def tip_distance(pose, target_bounds):
    b = target_bounds
    dx = max(b.left - pose.x, 0, pose.x - b.right)
    dy = max(b.top - pose.y, 0, pose.y - b.bottom)
    return math.hypot(dx, dy)


def test_the_pointer_fades_in_glides_and_taps():
    tutorial, ball, box = lesson()
    step = tutorial.step("One", duration=4).point(ball, at=0.5).point(box, at=2)
    glide = tutorial.theme.pointer_seconds
    assert tutorial.layout(0, time=0.4).pointer is None  # not yet
    appearing = tutorial.layout(0, time=0.5 + APPEAR / 2).pointer
    assert 0.3 < appearing.opacity < 0.7
    at_ball = tutorial.layout(0, time=1.5).pointer
    assert at_ball.opacity == 1 and at_ball.scale == 1
    assert tip_distance(at_ball, tutorial.layout(0).targets["ball"]) < 5  # the tip is at the ball
    tapping = tutorial.layout(0, time=0.5 + APPEAR + TAP / 2).pointer
    assert tapping.scale == pytest.approx(TAP_SCALE)
    middle = tutorial.layout(0, time=2 + glide / 2).pointer
    end = tutorial.layout(0).pointer
    assert at_ball.x < middle.x < end.x  # on its way from the ball to the box
    assert tip_distance(end, tutorial.layout(0).targets["box"]) < 5
    assert step.points[0].target is ball


def test_the_finished_step_rests_on_its_last_stop_and_renders_it():
    tutorial, ball, box = lesson()
    tutorial.step("One", duration=2).point(ball).point(box, at=1.9)  # the glide runs past the end
    end = tutorial.layout(0).pointer
    assert tip_distance(end, tutorial.layout(0).targets["box"]) < 5
    with_pointer = tutorial.render_step(0).buffer
    plain, *_ = lesson()
    plain.step("One", duration=2)
    difference = np.argwhere((with_pointer != plain.render_step(0).buffer).any(axis=2))
    assert len(difference)  # drawn, and only near the box
    assert difference[:, 1].min() > 380


def test_the_pointer_carries_over_from_the_step_before():
    tutorial, ball, box = lesson()
    tutorial.step("One", duration=2).point(ball)
    tutorial.step("Two", duration=2).point(box, at=0.5)
    tutorial.step("Three", duration=2)
    start = tutorial.layout(1, time=0.0).pointer
    assert start.opacity == 1 and tip_distance(start, tutorial.layout(1).targets["ball"]) < 5
    assert tutorial.layout(2).pointer is None  # a step pointing at nothing shows none


def test_the_hand_reaches_in_from_a_free_side():
    tutorial, ball, box = lesson()
    # Something sits where the hand would hang (below-right of the ball): it reaches in from elsewhere.
    tutorial.scene.add(blocker := Rectangle(position=Point(185, 175), width=80, height=80,
                                            fill=FillStyle(color=Color(120, 120, 120))))
    tutorial.target(blocker, name="blocker")
    tutorial.step("One", duration=1).point(ball)
    pose = tutorial.layout(0).pointer
    assert pose.angle != pytest.approx(-45)  # not the default, down-right
    assert tip_distance(pose, tutorial.layout(0).targets["ball"]) < 5


def test_narration_times_the_pointer():
    tutorial, ball, box = lesson()
    step = tutorial.step("One").point(ball).point(box, at=0.1)
    step.narrate("First the ball, and then the box.", {box: "the box"}, rate=2)
    box_stop = [s for s in step.points if s.target is box][0]
    assert box_stop.at == pytest.approx(5 / 2 - 0.15)  # "the" is the sixth word
    with pytest.raises(ValidationError, match="highlight or pointer stop"):
        tutorial.step("Two").narrate("The ball.", {ball: "ball"})


def test_pointer_stops_and_style_are_checked_saved_and_described():
    tutorial, ball, box = lesson(Theme(pointer_style="cursor", pointer_seconds=0.4))
    step = tutorial.step("One").point(ball).point(box, at=1).highlight(box)
    with pytest.raises(ValidationError, match="already moves"):
        step.point(box, at=1)
    with pytest.raises(ValidationError):
        Theme(pointer_style="finger")
    with pytest.raises(ValidationError):
        Theme(pointer_seconds=0)
    data = tutorial.to_dict()
    assert data["steps"][0]["points"] == [{"target_id": ball.id, "at": 0.0}, {"target_id": box.id, "at": 1.0}]
    Draft202012Validator(packaged_schema()).validate(data)
    restored = Tutorial.from_dict(data)
    assert restored.to_dict() == data and restored.theme.pointer_style == "cursor"
    assert "The pointer points at the ball. Then the pointer points at the box." in tutorial.describe(0)
    assert [i.code for i in tutorial.lint() if i.code.startswith("POINTER")] == ["POINTER_WITH_HIGHLIGHT"]


def test_every_style_draws():
    for style in ("hand", "cursor", "dot"):
        tutorial, ball, _ = lesson(Theme(pointer_style=style))
        tutorial.step("One", duration=1).point(ball)
        assert tutorial.render_step(0).buffer is not None
        payload = tutorial.web_step(0)["pointer"]
        assert payload["style"] == style and (payload["outline"] is None) == (style == "dot")
        assert payload["keys"][-1][1:3] == pytest.approx(
            [tutorial.layout(0).pointer.x, tutorial.layout(0).pointer.y], abs=0.01)
        assert "td-pointer" not in tutorial.web_step(0)["svg"]  # the player draws its own


def test_keys_interpolate_the_short_way_round():
    keys = [(0.0, 0, 0, 170, 1, 1), (1.0, 10, 0, -170, 1, 1)]
    assert abs(pose_at(keys, 0.5).angle) == pytest.approx(180)  # through 180, not through 0
    assert pose_at(keys, -1) is None and pose_at(keys, 5).x == 10

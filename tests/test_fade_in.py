"""Theme.fade_seconds: annotations fade in as they appear instead of popping in whole."""

import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene
from jsonschema import Draft202012Validator

from conftest import packaged_schema
from tutordraw import Theme, Tutorial, ValidationError

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")
BACKGROUND = (40, 40, 40)


def lesson(fade=0.5):
    scene = Scene(480, 300, background=Color(*BACKGROUND))
    ball = Circle(center=Point(140, 150), radius=40, fill=FillStyle(color=Color(80, 120, 200)))
    scene.add(ball)
    tutorial = Tutorial(scene, theme=Theme(fade_seconds=fade))
    return tutorial, tutorial.target(ball, name="ball")


def panel_pixel(tutorial, index, time, label_id):
    """The colour in the middle of a label's panel at `time` seconds into the lesson."""
    panel = next(a.panel for a in tutorial.layout(index).annotations if a.id == label_id)
    frame = tutorial.render_at_time(time).buffer
    return frame[int(panel.center.y), int(panel.x + 3)].astype(int)


def test_a_label_fades_in_from_its_moment():
    tutorial, ball = lesson()
    label = ball.label("Ball", anchor="right")
    tutorial.step("One", duration=3).show(label, at=1)
    white = np.array((255, 255, 255))
    assert (panel_pixel(tutorial, 0, 0.9, label.id) == BACKGROUND).all()  # not yet
    half = panel_pixel(tutorial, 0, 1.25, label.id)
    assert (half > np.array(BACKGROUND) + 60).all() and (half < white - 60).all()  # half faded in
    assert (panel_pixel(tutorial, 0, 1.6, label.id) == white).all()  # whole after 0.5 s
    np.testing.assert_array_equal(tutorial.render_at_time(1.6).buffer, tutorial.render_step(0).buffer)


def test_an_annotation_at_the_start_fades_in_too_and_the_end_is_unchanged():
    tutorial, ball = lesson()
    note = tutorial.step("One", duration=2).explain(ball, "A ball.")
    assert tutorial.steps[0].fade_progress(note, 0.0) == 0.0
    assert tutorial.steps[0].fade_progress(note, 0.25) == pytest.approx(0.5)
    assert tutorial.steps[0].fade_progress(note, 2.0) == 1.0  # the finished step is always whole
    assert (panel_pixel(tutorial, 0, 0.0, note.id) == BACKGROUND).all()


def test_a_label_already_on_screen_does_not_fade_again():
    tutorial, ball = lesson()
    label = ball.label("Ball", anchor="right")
    tutorial.step("One", duration=2).show(label)
    second = tutorial.step("Two", duration=2).show(label).highlight(ball)
    third = tutorial.step("Three", duration=2).show(label, at=1).highlight(ball)
    assert second.carried(label) and second.fade_progress(label, 0.0) == 1.0
    [highlight] = second.highlights
    assert not second.carried(highlight) and second.fade_progress(highlight, 0.0) == 0.0  # new here
    assert third.carried(third.highlights[0])
    assert not third.carried(label)  # hidden until 1 s, so it arrives again
    svg = tutorial.web_step(1)["svg"]
    assert 'data-td-fade="0.5"' in svg  # the highlight
    assert svg.count("data-td-fade") == 1


def test_a_drawn_leader_draws_on_then_the_panel_fades_in():
    tutorial, ball = lesson()
    label = ball.label("Ball", anchor="right")
    step = tutorial.step("One", duration=3).show(label, draw=True)
    draw = tutorial.theme.draw_seconds
    assert step.appears_at(label) == pytest.approx(draw)
    assert step.fade_progress(label, draw + 0.25) == pytest.approx(0.5)
    composition = tutorial._compose(0, (draw + 0.25) / 3)
    parts = {obj.id: obj.opacity for obj in composition.scene.layers[-1].objects if obj.id.startswith("td-")}
    assert parts[f"td-{label.id}-leader"] == 1.0  # drawn, not faded
    assert parts[f"td-{label.id}-panel"] == pytest.approx(0.5)


def test_marks_fade_and_no_fade_is_the_default():
    tutorial, ball = lesson()
    mark = tutorial.step("One", duration=2).number(ball)
    assert tutorial.steps[0].fade_progress(mark, 0.1) == pytest.approx(0.2)
    plain, ball = lesson(fade=0)
    plain.step("One", duration=2).show(ball.label("Ball"))
    assert plain.steps[0].fade_progress(plain.steps[0].labels[0], 0.0) == 1.0
    assert "data-td-fade" not in plain.web_step(0)["svg"]
    with pytest.raises(ValidationError):
        Theme(fade_seconds=-1)


def test_fade_seconds_round_trips_and_validates():
    tutorial, ball = lesson(fade=0.4)
    tutorial.step("One").show(ball.label("Ball"))
    data = tutorial.to_dict()
    assert data["theme"]["fade_seconds"] == 0.4
    Draft202012Validator(packaged_schema()).validate(data)
    assert Tutorial.from_dict(data).theme.fade_seconds == 0.4

"""Scaling one target: restyle(scale=, pivot=).

The camera zooms the whole board; a tutor making room on a full board wants
one diagram smaller while everything else stays put. `scale` shrinks or
grows a target's artwork about one of its anchors (`pivot`, the side or
corner that stays where it is), glides like a move in an animated step, and
carries what is drawn on it (children, labels, highlights, marks). Labels
and callouts are annotations: they follow but keep their size. A graph's own
tick numbers are part of its drawing and scale with it.
"""

import json

import pytest
from drawcv import Circle, Color, FillStyle, Group, Point, Rectangle, Scene, StrokeStyle, Text

from conftest import SCHEMA_VERSION, packaged_schema
from tutordraw import Tutorial, ValidationError
from tutordraw.kits import Axes

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def board(height=500):
    """A 'diagram' group (a frame with a dot and a word in it) that the second step scales.

    Bounds are 1 px apart here and there: a stroke's half width pads them unscaled.
    """
    scene = Scene(800, height, background=Color.white())
    frame = Rectangle(position=Point(100, 100), width=400, height=300,
                      stroke=StrokeStyle(color=Color(40, 40, 40), width=2))
    dot = Circle(center=Point(300, 250), radius=8, fill=FillStyle(color=Color(200, 60, 60)))
    word = Text(text="tick", position=Point(110, 380), font_scale=0.6)
    diagram = Group([frame, dot, word])
    scene.add(diagram)
    tutorial = Tutorial(scene)
    return tutorial, tutorial.target(diagram, name="diagram"), tutorial.target(dot, name="dot"), word


def scaled(scale=0.5, pivot="top_left", move=None, easing="linear"):
    tutorial, diagram, dot, word = board()
    tutorial.step("Whole", duration=1)
    tutorial.step("Smaller", duration=2).animate(easing).restyle(diagram, scale=scale, pivot=pivot, move=move)
    return tutorial, diagram, dot, word


def box(tutorial, index, name, time=None):
    b = tutorial.layout(index, time=time).targets[name]
    return round(b.x, 3), round(b.y, 3), round(b.width, 3), round(b.height, 3)


def test_a_target_scales_about_its_pivot():
    tutorial, *_ = scaled()
    x, y, w, h = box(tutorial, 0, "diagram")
    assert box(tutorial, 1, "diagram") == pytest.approx((x, y, w * 0.5, h * 0.5), abs=1.5)  # the top left stays
    tutorial, *_ = scaled(pivot="center")
    cx, cy = x + w / 2, y + h / 2
    assert box(tutorial, 1, "diagram") == pytest.approx((cx - w / 4, cy - h / 4, w / 2, h / 2), abs=1.5)
    tutorial, *_ = scaled(pivot="bottom_right")
    assert box(tutorial, 1, "diagram") == pytest.approx((x + w / 2, y + h / 2, w / 2, h / 2), abs=1.5)


def test_the_scale_glides_in_a_straight_line():
    tutorial, *_ = scaled()
    x, y, w, h = box(tutorial, 0, "diagram")
    assert box(tutorial, 1, "diagram", 1.0) == pytest.approx((x, y, w * 0.75, h * 0.75), abs=1.5)
    # Every point moves at constant speed: the dot's centre halfway is halfway between its ends.
    start, end, middle = (box(tutorial, 1, "dot", t) for t in (0.0, 2.0, 1.0))
    centre = [(b[0] + b[2] / 2, b[1] + b[3] / 2) for b in (start, end, middle)]
    assert centre[2] == pytest.approx(((centre[0][0] + centre[1][0]) / 2, (centre[0][1] + centre[1][1]) / 2))


def test_scale_and_move_together():
    tutorial, *_ = scaled(move=(-60, -40))
    x, y, w, h = box(tutorial, 0, "diagram")
    assert box(tutorial, 1, "diagram") == pytest.approx((x - 60, y - 40, w / 2, h / 2), abs=1.5)


def test_a_child_and_its_label_follow_but_the_label_keeps_its_size():
    tutorial, diagram, dot, word = scaled(scale=0.6)
    label = dot.label("P", anchor="right", leader=False)
    for step in tutorial.steps:
        step.show(label)
    before, after = (tutorial.layout(i) for i in (0, 1))
    [a], [b] = before.annotations, after.annotations
    assert b.panel.width == pytest.approx(a.panel.width) and b.panel.height == pytest.approx(a.panel.height)
    dot0, dot1 = before.targets["dot"], after.targets["dot"]
    assert dot1.width == pytest.approx(dot0.width * 0.6)
    # Beside its dot in both: the gap from the dot's right edge to the panel is the same.
    assert b.panel.x - dot1.right == pytest.approx(a.panel.x - dot0.right)


def test_the_drawing_text_scales_with_it():
    tutorial, diagram, dot, word = scaled(scale=0.5)
    from tutordraw.adapters.drawcv import index_scene
    heights = [index_scene(tutorial._compose(i, 1.0).scene)[word.id].get_bounds().height for i in (0, 1)]
    assert heights[1] == pytest.approx(heights[0] / 2, rel=0.02)
    svg = tutorial.web_step(1)["svg"]
    assert ">tick<" in svg


def test_leaving_scale_out_goes_back_to_full_size():
    tutorial, diagram, *_ = scaled()
    tutorial.step("Back", duration=1).animate("linear")
    assert box(tutorial, 2, "diagram") == box(tutorial, 0, "diagram")
    tutorial.step("Held", duration=1).restyle(diagram, scale=0.5, pivot="top_left")
    tutorial.step("Held again", duration=1).animate("linear").restyle(diagram, scale=0.5, pivot="top_left")
    assert box(tutorial, 4, "diagram", 0.5) == box(tutorial, 3, "diagram")  # held: nothing moves


def test_a_new_pivot_starts_where_the_last_step_left_it():
    tutorial, diagram, *_ = scaled(scale=0.5, pivot="top_left")
    tutorial.step("Other corner", duration=2).animate("linear").restyle(diagram, scale=0.8, pivot="bottom_right")
    assert box(tutorial, 2, "diagram", 0.0) == pytest.approx(box(tutorial, 1, "diagram"), abs=1.5)
    x, y, w, h = box(tutorial, 0, "diagram")
    assert box(tutorial, 2, "diagram") == pytest.approx((x + w * 0.2, y + h * 0.2, w * 0.8, h * 0.8), abs=1.5)


def test_a_scaled_graph_carries_its_parts():
    scene = Scene(900, 600, background=Color.white())
    tutorial = Tutorial(scene)
    axes = Axes(tutorial, box=(80, 80, 560, 440), x_range=(0, 4), y_range=(0, 16))
    axes.plot(lambda x: x * x, name="curve")
    point = axes.point(2, 4, name="p")
    graph = tutorial.target(axes.group, name="graph", obstacle=False)
    label = point.label("P", anchor="left")
    tutorial.step("Whole", duration=1).show(label)
    tutorial.step("Smaller", duration=1).animate("linear").restyle(graph, scale=0.75, pivot="top_left").show(label)
    whole, small = (tutorial.layout(i) for i in (0, 1))
    g0, g1 = whole.targets["graph"], small.targets["graph"]
    assert (g1.x, g1.y) == pytest.approx((g0.x, g0.y))
    assert g1.width == pytest.approx(g0.width * 0.75)
    # The point stays on the curve: where x = 2 lands on the smaller graph.
    p0, p1 = whole.targets["p"].center, small.targets["p"].center
    assert (p1.x, p1.y) == pytest.approx((g0.x + (p0.x - g0.x) * 0.75, g0.y + (p0.y - g0.y) * 0.75))


def test_the_player_tweens_a_scale_from_one_start_frame():
    tutorial, *_ = scaled(easing="ease_in_out")
    payload = tutorial.web_step(1)
    assert len(payload["frames"]) == 1 and payload["easing"] is not None  # a straight line: exact


def test_scale_and_pivot_are_checked():
    tutorial, diagram, *_ = scaled()
    step = tutorial.step("More")
    for bad in (0, -1, float("nan"), float("inf"), 11, "big", True):
        with pytest.raises(ValidationError, match="scale"):
            step.restyle(diagram, scale=bad)
    with pytest.raises(ValidationError, match="pivot"):
        step.restyle(diagram, scale=0.5, pivot="middle")
    with pytest.raises(ValidationError, match="pivot needs scale"):
        step.restyle(diagram, pivot="top_left")
    assert step.restyle(diagram, scale=0.5).restyles[0].pivot == "center"


def test_scale_is_saved_and_loaded(tmp_path):
    tutorial, *_ = scaled(scale=0.75, pivot="bottom_left", move=(10, 0))
    document = tutorial.to_dict()
    assert document["schema_version"] == SCHEMA_VERSION == 12
    [restyle] = document["steps"][1]["restyles"]
    assert (restyle["scale"], restyle["pivot"]) == (0.75, "bottom_left")
    import jsonschema
    jsonschema.validate(document, packaged_schema())
    again = Tutorial.from_dict(json.loads(json.dumps(document)))
    assert again.layout(1).targets["diagram"] == tutorial.layout(1).targets["diagram"]


def test_describe_says_it_shrinks():
    tutorial, *_ = scaled(scale=0.75)
    assert "shrinks to 75%" in tutorial.describe(1)
    tutorial.step("Back", duration=1)
    assert "returns to its full size" in tutorial.describe(2)


def test_lint_warns_when_scaled_drawing_text_gets_too_small():
    tutorial, *_ = scaled(scale=0.5)
    codes = [issue.code for issue in tutorial.lint(1)]
    assert "SCALED_TEXT_SMALL" in codes
    tutorial, *_ = scaled(scale=0.9)
    assert "SCALED_TEXT_SMALL" not in [issue.code for issue in tutorial.lint(1)]


def test_a_group_that_is_not_an_obstacle_lets_its_parts_labels_sit_inside_it():
    def placed(obstacle):
        scene = Scene(800, 500, background=Color.white())
        frame = Rectangle(position=Point(100, 100), width=400, height=300,
                          stroke=StrokeStyle(color=Color(40, 40, 40), width=2))
        dot = Circle(center=Point(300, 250), radius=8, fill=FillStyle(color=Color(200, 60, 60)))
        diagram = Group([frame, dot])
        scene.add(diagram)
        tutorial = Tutorial(scene)
        tutorial.target(diagram, name="diagram", obstacle=obstacle)
        label = tutorial.target(dot, name="dot").label("P", anchor="top", leader=False)
        tutorial.step("One").show(label)
        return tutorial, tutorial.layout(0).annotations[0].panel

    tutorial, panel = placed(False)
    assert 100 < panel.y < 250  # just above its dot, inside the frame
    assert tutorial.to_dict()["targets"][0]["obstacle"] is False
    assert Tutorial.from_dict(tutorial.to_dict()).targets[0].obstacle is False
    _, panel = placed(True)  # as before: the group's whole box keeps it out
    assert not (100 < panel.center.x < 500 and 100 < panel.center.y < 400)


def test_point_labels_keep_their_side_through_the_glide():
    # Tick numbers are soft obstacles for labels; they were measured where the frame had them,
    # so halfway through the shrink a label read the old numbers and jumped to another side.
    scene = Scene(960, 540, background=Color.white())
    tutorial = Tutorial(scene)
    axes = Axes(tutorial, box=(110, 60, 540, 420), x_range=(-0.5, 3.5), y_range=(-1, 25),
                x_step=1, y_step=5, grid=True)
    axes.plot(lambda x: 2 * x * x + 3, name="curve")
    labels = [axes.point(x, 0, name=name, radius=6).label(text, anchor="bottom")
              for x, name, text in ((1, "a", "a = 1"), (3, "b", "b = 3"))]
    graph = tutorial.target(axes.group, name="graph", obstacle=False)
    tutorial.step("Whole", duration=1).show(*labels)
    tutorial.step("Smaller", duration=2).animate("ease_in_out", seconds=0.8).restyle(
        graph, scale=0.75, pivot="top_left").show(*labels)
    sides = {a.anchor for t in (0.0, 0.1, 0.2, 0.27, 0.4, 0.53, 0.7, 0.8, 2.0)
             for a in tutorial.layout(1, time=t).annotations}
    assert sides == {"bottom"}

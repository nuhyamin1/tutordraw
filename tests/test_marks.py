"""Schema v8 vocabulary: marks, draw-on, camera, outline highlights, halo."""

import json
import math

import numpy as np
import pytest
from drawcv import (Circle, Color, FillStyle, Group, Line, Path, Point, Rectangle, Scene)
from jsonschema import Draft202012Validator

from conftest import packaged_schema
from tutordraw import LessonFormatError, Theme, Tutorial, ValidationError
from tutordraw.marks import GAP, mark_drawing

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


@pytest.fixture
def lesson():
    scene = Scene(800, 500, background=Color.white())
    a = Rectangle(position=Point(100, 200), width=100, height=60, fill=FillStyle(color=Color(90, 140, 200)))
    b = Circle(center=Point(600, 230), radius=40, fill=FillStyle(color=Color(200, 120, 90)))
    c = Circle(center=Point(400, 400), radius=20, fill=FillStyle(color=Color(120, 180, 110)))
    for shape in (a, b, c):
        scene.add(shape)
    tutorial = Tutorial(scene)
    targets = [tutorial.target(s, name=n) for s, n in ((a, "a"), (b, "b"), (c, "c"))]
    return tutorial, targets


def drawing(tutorial, mark, progress=1.0):
    composition = tutorial.layout(0)
    bounds = {t.drawable_id: composition.targets[t.name] for t in tutorial.targets}
    return mark_drawing(mark, bounds, composition.camera, tutorial.theme, None,
                        (composition.scene.width, composition.scene.height), progress)


# --- authoring validation -------------------------------------------------------

def test_mark_methods_validate_their_arguments(lesson):
    tutorial, (a, b, c) = lesson
    step = tutorial.step("Marks")
    bad = [
        lambda: step.connect(a, a),
        lambda: step.connect((1, 2), (3, 4)),
        lambda: step.connect((1, 2), (1, 2)),
        lambda: step.connect(a, b, bend=2),
        lambda: step.connect(a, b, both="yes"),
        lambda: step.brace(),
        lambda: step.brace(a, side="middle"),
        lambda: step.measure(a, axis="z"),
        lambda: step.measure((1, 2)),
        lambda: step.measure(a, axis="free"),
        lambda: step.measure(a, b, offset=-1),
        lambda: step.angle(a, b, c, radius=0),
        lambda: step.angle(a, b, (1, 2, 3)),
        lambda: step.number(a, n=0),
        lambda: step.number(a, n=True),
        lambda: step.number(a, corner="middle"),
        lambda: step.zoom_to(),
        lambda: step.zoom_to(a, max_scale=0),
        lambda: step.zoom_to(a, padding=-5),
        lambda: step.connect(a, b, draw=1),
        lambda: step.show(a.label("x"), draw="no"),
        lambda: step.highlight(a, shape="circle"),
        lambda: step.connect(a, b, "text\nwith newline"),
    ]
    for i, make in enumerate(bad):
        with pytest.raises(ValidationError):
            make()
            pytest.fail(f"case {i} did not raise")
    assert step.marks == ()  # Nothing half-registered by a failed call.


def test_numbers_count_up_within_a_step(lesson):
    tutorial, (a, b, c) = lesson
    step = tutorial.step("Order")
    assert [step.number(t).options["n"] for t in (a, b, c)] == [1, 2, 3]
    assert tutorial.step("Next").number(a).options["n"] == 1
    assert step.number(a, n=7).options["n"] == 7


def test_outline_highlight_refuses_what_cannot_be_outlined():
    scene = Scene(300, 200)
    line = Line(start=Point(10, 10), end=Point(100, 100))
    group = Group(children=[Circle(center=Point(50, 50), radius=10)])
    scene.add(line)
    scene.add(group)
    tutorial = Tutorial(scene)
    step = tutorial.step("Outline")
    for shape in (line, group):
        with pytest.raises(ValidationError, match="shape='box'"):
            step.highlight(tutorial.target(shape), shape="outline")


# --- geometry -------------------------------------------------------------------

def test_an_arrow_leaves_one_target_and_stops_short_of_the_other(lesson):
    tutorial, (a, b, _) = lesson
    mark = tutorial.step("Arrow").connect(a, b, "pushes")
    art = drawing(tutorial, mark)
    path = next(obj for obj in art.artwork if isinstance(obj, Path))
    start, end = path.point_at(0), path.point_at(1)
    assert start.x == pytest.approx(200 + GAP)  # a's right edge plus the gap
    assert end.x == pytest.approx(560 - GAP, abs=0.5)  # b's left edge minus the gap
    assert art.panel.bottom <= min(start.y, end.y)  # caption above a straight arrow
    bent = tutorial.steps[0].connect(a, b, bend=0.3)
    mid = next(o for o in drawing(tutorial, bent).artwork if isinstance(o, Path)).point_at(0.5)
    assert mid.y < start.y - 30  # bends up-screen for positive bend


def test_measure_and_brace_span_exactly_their_targets(lesson):
    tutorial, (a, b, c) = lesson
    step = tutorial.step("Spans")
    width = drawing(tutorial, step.measure(a, text="10 cm"))
    lines = [o for o in width.artwork if isinstance(o, Path)]
    dim = lines[-1]
    assert (dim.point_at(0).x, dim.point_at(1).x) == pytest.approx((100, 200))
    assert dim.point_at(0).y == pytest.approx(260 + 24)
    assert width.panel.center.x == pytest.approx(150)
    brace = drawing(tutorial, step.brace(a, c, text="group"))
    union_left, union_right = 100, 420
    assert brace.bounds.left == pytest.approx(union_left, abs=1)
    assert brace.bounds.right == pytest.approx(union_right, abs=1)
    assert brace.panel.top > 420  # caption below the brace tip, under c


def test_an_angle_takes_the_smaller_way_round(lesson):
    tutorial, _ = lesson
    step = tutorial.step("Angle")
    art = drawing(tutorial, step.angle((100, 100), (200, 100), (100, 0), "90", radius=30))
    arc = next(o for o in art.artwork if isinstance(o, Path))
    mid = arc.point_at(0.5)
    angle = math.degrees(math.atan2(mid.y - 100, mid.x - 100))
    assert angle == pytest.approx(-45, abs=2)
    assert math.hypot(mid.x - 100, mid.y - 100) == pytest.approx(30, abs=0.5)
    assert art.panel.center.x > 100 and art.panel.center.y < 100


# --- draw-on and timing ---------------------------------------------------------

def test_draw_on_progresses_and_is_complete_at_the_end(lesson):
    tutorial, (a, b, _) = lesson
    tutorial.theme = Theme(draw_seconds=1.0)
    step = tutorial.step("Draw", duration=4)
    label = a.label("Source")
    step.show(label, at=1.0, draw=True)
    arrow = step.connect(a, b, "flow", draw=True, at=2.0)
    step.highlight(b, draw=True, at=0.5)
    highlight = step.highlights[0]
    assert step.draw_progress(label, 0.5) == 0
    assert step.draw_progress(label, 1.25) == pytest.approx(0.25)
    assert step.draw_progress(label, 2.5) == 1
    assert step.draw_progress(arrow, 2.5) == pytest.approx(0.5)
    assert step.draw_progress(highlight, 0.75) == pytest.approx(0.25)
    # Half-drawn things are not reported as readable layout yet.
    assert [x.text for x in tutorial.layout(0, time=1.5).annotations] == []
    assert tutorial.layout(0, time=2.5).marks == ()
    assert [x.text for x in tutorial.layout(0, time=2.5).annotations] == ["Source"]
    # render_step is the finished state, regardless of timing.
    finished = tutorial.layout(0)
    assert [m.text for m in finished.marks] == ["flow"] and finished.highlights
    np.testing.assert_array_equal(tutorial.render_step(0).to_numpy(),
                                  tutorial.render_at_time(4.0).to_numpy())


def test_a_draw_delay_past_the_end_still_finishes(lesson):
    tutorial, (a, b, _) = lesson
    step = tutorial.step("Late", duration=1)
    step.connect(a, b, draw=True, at=5.0)
    assert len(tutorial.layout(0).marks) == 1


# --- camera ---------------------------------------------------------------------

def test_zoom_frames_the_target_and_keeps_text_size(lesson):
    tutorial, (a, b, _) = lesson
    label = b.label("Target")
    tutorial.step("Wide").show(label)
    tutorial.step("Close").show(label).zoom_to(b, padding=20, max_scale=10)
    wide, close = tutorial.layout(0), tutorial.layout(1)
    box = close.targets["b"]
    assert box.center.x == pytest.approx(400, abs=0.5) and box.center.y == pytest.approx(250, abs=0.5)
    scale = close.camera[0]
    assert scale == pytest.approx(500 / 120)  # height-limited: (80 + 2 * 20) fits 500
    assert box.width == pytest.approx(80 * scale, rel=1e-3)
    # Annotations are screen-space: the panel is the same size at any zoom.
    assert close.annotations[0].panel.width == pytest.approx(wide.annotations[0].panel.width)
    assert wide.camera is None
    # The source scene never sees the camera.
    assert tutorial.scene.to_dict() == Tutorial(tutorial.scene).scene.to_dict()
    assert tutorial.targets[1].drawable.get_bounds().width == pytest.approx(80)


def test_an_animated_zoom_moves_smoothly_and_labels_hold_their_side(lesson):
    tutorial, (a, b, _) = lesson
    label = b.label("Target", anchor="right")
    tutorial.step("Wide").show(label)
    tutorial.step("Close", duration=2).show(label).animate("linear").zoom_to(b, padding=20)
    start = tutorial.layout(1, time=0.0).camera
    middle = tutorial.layout(1, time=1.0).camera
    end = tutorial.layout(1).camera
    assert start[0] == pytest.approx(1.0)
    assert middle[0] == pytest.approx(math.sqrt(start[0] * end[0]), rel=1e-3)
    sides = {tutorial.layout(1, time=t).annotations[0].anchor for t in (0.0, 0.5, 1.0, 1.5, 2.0)}
    assert len(sides) == 1


def test_reset_camera_and_independent_steps(lesson):
    tutorial, (a, b, _) = lesson
    step = tutorial.step("Zoom").zoom_to(a)
    assert step.camera is not None
    step.reset_camera()
    assert step.camera is None and tutorial.layout(0).camera is None
    tutorial.step("Zoomed").zoom_to(a)
    tutorial.step("Plain")  # does not inherit the previous step's zoom
    assert tutorial.layout(2).camera is None


def test_fixed_points_follow_the_camera(lesson):
    tutorial, (a, _, _) = lesson
    step = tutorial.step("Zoom").zoom_to(a, padding=10)
    mark = step.angle((150, 230), (200, 230), (150, 200), radius=20)
    composition = tutorial.layout(0)
    s, tx, ty = composition.camera
    centre = composition.targets["a"].center
    assert (centre.x, centre.y) == pytest.approx((150 * s + tx, 230 * s + ty))
    assert composition.marks[0].bounds.left == pytest.approx(150 * s + tx, abs=1)
    del mark


# --- persistence ----------------------------------------------------------------

def build_everything(tutorial, targets):
    a, b, c = targets
    step = tutorial.step("All", duration=4)
    step.show(a.label("A"), at=0.5, draw=True)
    step.explain(b, "B explained", draw=True)
    step.highlight(b, shape="outline", at=1.0, draw=True)
    step.connect(a, b, "flow", bend=0.2, both=True, at=1.5, draw=True)
    step.brace(a, c, text="pair", side="top")
    step.measure(a, text="w", axis="y", offset=12)
    step.measure((10, 10), c, "d", axis="free")
    step.angle(c, a, (500, 480), "t", radius=25, draw=True)
    step.number(c, corner="bottom_right", at=2.0)
    step.zoom_to(a, b, padding=30, max_scale=3)
    tutorial.step("Plain")
    return tutorial


def test_everything_round_trips_and_validates_against_the_v8_schema(lesson):
    tutorial = build_everything(*lesson)
    document = tutorial.to_dict()
    Draft202012Validator(packaged_schema()).validate(document)
    restored = Tutorial.from_dict(document)
    assert restored.to_dict() == document
    np.testing.assert_array_equal(restored.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    np.testing.assert_array_equal(restored.render_at_time(1.2).to_numpy(),
                                  tutorial.render_at_time(1.2).to_numpy())
    step = restored.steps[0]
    assert [m.kind for m in step.marks] == ["arrow", "brace", "measure", "measure", "angle", "number"]
    assert step.highlights[0].shape == "outline" and step.highlights[0].draw
    assert step.camera.max_scale == 3


@pytest.mark.parametrize("corrupt, message", [
    (lambda s: s["marks"][0].update(kind="spiral"), "unknown mark kind"),
    (lambda s: s["marks"][0]["options"].update(extra=1), "unknown fields"),
    (lambda s: s["marks"][0]["refs"].append({"point": [1, 2]}), "exactly two refs"),
    (lambda s: s["marks"][0]["refs"].__setitem__(0, {"target_id": "nope"}), "unknown reference"),
    (lambda s: s["marks"][0]["refs"].__setitem__(0, {"bogus": 1}), "target_id"),
    (lambda s: s["draw"].append("missing"), "unknown annotation or mark"),
    (lambda s: s["draw"].append(s["marks"][-1]["id"]), "cannot draw on"),
    (lambda s: s["camera"].update(max_scale=99), "max_scale"),
    (lambda s: s["highlights"][0].update(shape="star"), "shape"),
    (lambda s: s["marks"][1].update(id=s["marks"][0]["id"]), "Duplicate"),
])
def test_corrupt_v8_documents_are_rejected(lesson, corrupt, message):
    document = build_everything(*lesson).to_dict()
    corrupt(document["steps"][0])
    with pytest.raises(LessonFormatError, match=message):
        Tutorial.from_dict(document)


def test_lint_sees_mark_captions(lesson):
    tutorial, (a, b, _) = lesson
    step = tutorial.step("Clash")
    step.measure((100, 100), (300, 100), "first caption", axis="free", offset=0)
    step.measure((100, 100), (300, 100), "second caption", axis="free", offset=0)
    issues = tutorial.lint()
    assert any(i.code == "ANNOTATION_OVERLAP" and {"first caption", "second caption"} <= set(i.annotations)
               for i in issues)
    json.dumps([i.to_dict() for i in issues])


def test_a_force_arrow_lands_exactly_on_a_point_and_stops_short_of_a_target(lesson):
    tutorial, (a, b, _) = lesson
    step = tutorial.step("Force")
    push = drawing(tutorial, step.connect((600, 100), b, "push"))
    path = next(o for o in push.artwork if isinstance(o, Path))
    assert (path.point_at(0).x, path.point_at(0).y) == pytest.approx((600, 100))
    assert path.point_at(1).y == pytest.approx(190 - GAP, abs=0.5)  # b's top minus the gap
    # A vertical arrow's caption sits beside the shaft, not across it.
    assert push.panel.left > 600 or push.panel.right < 600
    pull = drawing(tutorial, step.connect(a, (150, 400)))
    end = next(o for o in pull.artwork if isinstance(o, Path)).point_at(1)
    assert (end.x, end.y) == pytest.approx((150, 400))

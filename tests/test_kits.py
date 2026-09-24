"""Teaching kits: Axes builds ordinary DrawCV objects and named targets."""

import math

import numpy as np
import pytest
from drawcv import Color, Group, Line, Path, Point, Rectangle, Scene, Text

from tutordraw import Tutorial, ValidationError
from tutordraw.adapters.drawcv import stroke_boxes
from tutordraw.kits import Axes, NumberLine, format_number, nice_step

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


@pytest.fixture
def axes():
    tutorial = Tutorial(Scene(700, 500, background=Color.white()))
    return Axes(tutorial, box=(100, 50, 500, 400), x_range=(-2, 3), y_range=(-1, 9),
                x_step=1, y_step=1)


def test_coordinates_map_onto_the_box(axes):
    assert (axes.to_scene(-2, -1).x, axes.to_scene(-2, -1).y) == pytest.approx((100, 450))
    assert (axes.to_scene(3, 9).x, axes.to_scene(3, 9).y) == pytest.approx((600, 50))
    assert axes.origin == (0.0, 0.0)
    assert axes.x_step == 1 and axes.y_step == 1


def test_it_is_plain_drawcv_in_the_scene_with_named_targets(axes):
    tutorial = axes.tutorial
    assert isinstance(axes.group, Group) and axes.group in tutorial.scene.layers[0].objects
    names = {t.name for t in tutorial.targets}
    assert names == {"axes_x_axis", "axes_y_axis"}
    texts = sorted(obj.text for obj in axes.group.children if isinstance(obj, Text))
    # -2..3 and -1..9 without the two zeros, one shared "0", and the axis names.
    assert texts == sorted(["-2", "-1", "1", "2", "3", "-1", *map(str, range(1, 10)), "0", "x", "y"])


@pytest.mark.parametrize("span, step", [(6, 1), (10, 1), (0.6, 0.1), (100, 10)])
def test_ticks_use_round_steps(span, step):
    assert nice_step(span) == pytest.approx(step)


@pytest.mark.parametrize("span", [0.03, 0.7, 3, 7.5, 13, 42, 250, 1500, 86400])
def test_every_span_gets_a_1_2_5_step_and_a_readable_tick_count(span):
    step = nice_step(span)
    mantissa = step / 10 ** math.floor(math.log10(step) + 1e-9)
    assert round(mantissa, 6) in (1, 2, 5)
    assert 4 <= span / step <= 16


@pytest.mark.parametrize("value, step, text", [(2, 1, "2"), (-0.0000001, 0.1, "0"), (0.25, 0.05, "0.25"),
                                               (-1.5, 0.5, "-1.5"), (300, 50, "300")])
def test_tick_numbers_read_cleanly(value, step, text):
    assert format_number(value, step) == text


def test_a_plot_follows_the_function_and_stops_at_the_edges(axes):
    curve = axes.plot(lambda x: x * x, name="parabola")
    assert curve.name == "parabola"
    path = curve.drawable
    assert isinstance(path, Path)
    contours = path.flatten_world()
    assert len(contours) == 1
    points = contours[0]
    for p in points[::20]:
        x = -2 + (p.x - 100) / 500 * 5
        y = 9 - (p.y - 50) / 400 * 10
        assert y == pytest.approx(x * x, abs=0.05)
    # It leaves through the top edge exactly, at x = 3.
    assert min(p.y for p in points) == pytest.approx(50, abs=0.01)


def test_asymptotes_and_failures_split_the_curve(axes):
    branches = axes.plot(lambda x: 1 / x, name="hyperbola").drawable.flatten_world()
    assert len(branches) == 2
    left, right = sorted(branches, key=lambda c: c[0].x)
    assert max(p.x for p in left) < axes.to_scene(0, 0).x < min(p.x for p in right)
    logs = axes.plot(lambda x: math.log(x), name="log").drawable.flatten_world()
    assert min(p.x for c in logs for p in c) > axes.to_scene(0, 0).x
    with pytest.raises(ValidationError, match="Nothing of the curve"):
        axes.plot(lambda x: 100 + x)


def test_points_guides_and_automatic_names(axes):
    dot = axes.point(2, 4)
    hidden = axes.point(1, 1, visible=False)
    both = axes.guide(x=2, y=4)
    vertical = axes.guide(x=-1)
    assert [t.name for t in (dot, hidden, both, vertical)] == [
        "axes_point1", "axes_point2", "axes_guide3", "axes_guide4"]
    centre = dot.drawable.get_bounds().center
    assert (centre.x, centre.y) == pytest.approx((axes.to_scene(2, 4).x, axes.to_scene(2, 4).y))
    assert hidden.drawable.opacity < 0.01
    assert both.drawable.stroke.dash_array == (6.0, 5.0)
    for bad in (lambda: axes.point(9, 9), lambda: axes.guide(), lambda: axes.plot("x*x"),
                lambda: axes.plot(lambda x: x, samples=1), lambda: axes.plot(lambda x: x, domain=(2, 1))):
        with pytest.raises(ValidationError):
            bad()


@pytest.mark.parametrize("kwargs", [
    dict(box=(0, 0, 0, 10)), dict(box=(0, 0, 10)), dict(x_range=(1, 1)), dict(y_range=(5, 2)),
    dict(x_step=0), dict(y_step=0.001), dict(name=""), dict(grid="yes"),
])
def test_bad_axes_are_refused(kwargs):
    options = dict(box=(10, 10, 300, 200), x_range=(0, 10), y_range=(0, 10))
    options.update(kwargs)
    with pytest.raises(ValidationError):
        Axes(Tutorial(Scene(400, 300)), **options)


def test_axes_survive_save_and_load_and_can_be_extended(axes, tmp_path):
    tutorial = axes.tutorial
    curve = axes.plot(lambda x: x * x, name="parabola")
    tutorial.step("Graph").show(curve.label("y = x²"))
    path = tutorial.save_json(tmp_path / "graph.tutordraw.json")
    loaded = Tutorial.load_json(path)
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    again = Axes.find(loaded)
    assert again.x_range == (-2, 3) and again.y_step == 1
    line = again.plot(lambda x: 2 * x + 1, name="line")
    assert line.name == "line" and loaded.get_target("parabola")
    assert again.point(1, 3).name.startswith("axes_point")
    with pytest.raises(ValidationError, match="No axes"):
        Axes.find(loaded, "nope")


def test_labels_can_sit_inside_a_curve_not_only_beside_its_bounds():
    """Unfilled strokes block only along their ink, so empty space inside an arc is usable."""
    scene = Scene(400, 300, background=Color.white())
    outline = Rectangle(position=Point(50, 50), width=300, height=200)
    diagonal = Line(start=Point(0, 0), end=Point(300, 300))
    assert len(stroke_boxes(outline)) > 4 and len(stroke_boxes(diagonal)) > 4
    assert all(min(b.width, b.height) < 30 for b in stroke_boxes(outline))
    filled = Rectangle(position=Point(0, 0), width=10, height=10,
                       fill=__import__("drawcv").FillStyle(color=Color(1, 2, 3)))
    assert stroke_boxes(filled) is None and stroke_boxes(Group(children=[])) is None
    total = sum(b.width * b.height for b in stroke_boxes(diagonal))
    assert total < 0.3 * 300 * 300  # far less than the diagonal's bounding box


def test_generated_artwork_pins_its_pivot(axes):
    """With DrawCV's default pivot, one graph took 7.5 s to render and 11 s to lint.

    The default pivot is the object's own centre, found from its bounds, so
    every world-space mapping re-measured whole curves. Guard the fix
    structurally rather than with a flaky timing test.
    """
    curve = axes.plot(lambda x: x * x)
    guide = axes.guide(x=1)
    step = axes.tutorial.step("Marks")
    arrow = step.connect(axes.x_axis, curve)
    assert axes.group.transform.pivot is not None
    assert curve.drawable.transform.pivot is not None and guide.drawable.transform.pivot is not None
    from tutordraw.marks import mark_drawing
    layout = axes.tutorial.layout(0)
    bounds = {t.drawable_id: layout.targets[t.name] for t in axes.tutorial.targets}
    drawn = mark_drawing(arrow, bounds, None, axes.tutorial.theme, None, (700, 500))
    assert all(obj.transform.pivot is not None for obj in drawn.artwork if isinstance(obj, Path))


# --- number line --------------------------------------------------------------

@pytest.fixture
def number_line():
    tutorial = Tutorial(Scene(800, 300, background=Color.white()))
    return NumberLine(tutorial, start=(100, 150), length=600, value_range=(-5, 5))


def test_number_line_maps_values_and_ticks_whole_numbers(number_line):
    assert (number_line.to_scene(-5).x, number_line.to_scene(5).x) == pytest.approx((100, 700))
    assert number_line.to_scene(0).y == 150 and number_line.step == 1
    texts = [obj.text for obj in number_line.group.children if isinstance(obj, Text)]
    assert texts == [str(v) for v in range(-5, 6)]
    assert number_line.line.name == "number_line_line"


def test_points_can_be_open_or_closed(number_line):
    closed, hollow = number_line.point(3), number_line.point(-2, open=True)
    assert closed.drawable.fill.color == closed.drawable.stroke.color
    assert (hollow.drawable.fill.color.r, hollow.drawable.fill.color.g) == (255, 255)
    assert closed.drawable.get_bounds().center.x == pytest.approx(number_line.to_scene(3).x)


def test_hops_are_step_marks_between_reused_anchors(number_line):
    tutorial = number_line.tutorial
    add = tutorial.step("Add", duration=3)
    up = number_line.hop(add, 2, 5, "+3", at=1.0)
    down = number_line.hop(add, 5, 1, "-4")
    assert up.kind == "arrow" and up.options["bend"] > 0 > down.options["bend"]
    assert add.revealed_at(up) == 1.0 and up.id in add.draws
    # The anchor at 5 is shared by both hops, not created twice.
    anchors = [t.name for t in tutorial.targets if "_at_" in t.name]
    assert anchors == ["number_line_at_2", "number_line_at_5", "number_line_at_1"]
    assert tutorial.describe(0).startswith(
        'Add. An arrow goes from the number line at 5 to the number line at 1, labelled "-4". '
        'Then an arrow goes from the number line at 2 to the number line at 5, labelled "+3".')
    # Rightward hops arc above the line, leftward ones below.
    marks = {m.text: m for m in tutorial.layout(0).marks}
    assert marks["+3"].bounds.top < 150 - 20 and marks["-4"].bounds.bottom > 150 + 20
    assert tutorial.step("Next").marks == ()  # a hop belongs to its step only
    # A long hop keeps close to its line instead of ballooning.
    long = number_line.hop(tutorial.step("Long"), -5, 5)
    arc = tutorial.layout(2).marks[0].bounds
    assert long.options["bend"] < 0.35 and arc.top > 150 - 50
    for bad in (lambda: number_line.hop(add, 2, 2), lambda: number_line.hop(add, 0, 9),
                lambda: number_line.hop(add, 0, 1, bend=0)):
        with pytest.raises(ValidationError):
            bad()


def test_intervals_and_validation(number_line):
    span = number_line.interval(-2, 4, open_start=True)
    circles = [o for o in span.drawable.children if o.__class__.__name__ == "Circle"]
    assert circles[0].fill.color.r == 255 and circles[1].fill.color.r != 255
    for bad in (lambda: number_line.point(6),
                lambda: number_line.interval(3, 1), lambda: number_line.interval(0, 1, open_end="no"),
                lambda: NumberLine(number_line.tutorial, start=(0, 0), length=0, value_range=(0, 1)),
                lambda: NumberLine(number_line.tutorial, start=(0, 0), length=10, value_range=(0, 1),
                                   step=0.001, name="dense")):
        with pytest.raises(ValidationError):
            bad()


def test_number_lines_reattach_after_loading(number_line, tmp_path):
    tutorial = number_line.tutorial
    number_line.hop(tutorial.step("One"), 0, 3, "+3")
    loaded = Tutorial.load_json(tutorial.save_json(tmp_path / "line.tutordraw.json"))
    again = NumberLine.find(loaded)
    assert again.value_range == (-5, 5) and again.step == 1
    assert again.point(2).name.startswith("number_line_point")
    assert loaded.get_target("number_line_at_3") and loaded.steps[0].marks[0].text == "+3"
    assert again.anchor(3).name == "number_line_at_3"  # reused after loading
    with pytest.raises(ValidationError, match="No number line"):
        NumberLine.find(loaded, "nope")


def test_kit_points_work_directly_as_mark_ends(axes):
    """KITS.md shows step.connect(axes.to_scene(0, 8), vertex): a Point must be accepted."""
    vertex = axes.point(0, 0, name="vertex")
    step = axes.tutorial.step("Arrow")
    arrow = step.connect(axes.to_scene(0, 8), vertex, "vertex")
    assert arrow.refs[0] == pytest.approx((axes.to_scene(0, 8).x, axes.to_scene(0, 8).y))
    assert step.measure(axes.to_scene(0, 0), axes.to_scene(2, 0), "2", axis="x").refs[1][0] == pytest.approx(
        axes.to_scene(2, 0).x)


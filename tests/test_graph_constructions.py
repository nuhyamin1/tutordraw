"""Axes in maths coordinates: clipped shapes, regions, rectangles, tangents, secants and intersections.

Each construction is computed from the same function and mapping as the
curve, so the tests check it against the maths, not against a picture.
"""

import math

import numpy as np
import pytest
from drawcv import Color, FillStyle, Line, Path, Point, Polygon, Scene

from tutordraw import Tutorial, ValidationError
from tutordraw.kits import Axes

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def square(x):
    return x * x


@pytest.fixture
def axes():
    tutorial = Tutorial(Scene(700, 500, background=Color.white()))
    return Axes(tutorial, box=(100, 50, 500, 400), x_range=(-2, 3), y_range=(-1, 9),
                x_step=1, y_step=1)


def maths(axes, point):
    """A canvas point back in the axes' units."""
    (x0, x1), (y0, y1), b = axes.x_range, axes.y_range, axes.box
    return (x0 + (point.x - b.left) / b.width * (x1 - x0),
            y0 + (b.top + b.height - point.y) / b.height * (y1 - y0))


def outlines(path):
    """Each subpath's points in maths units."""
    return [[cmd.point for cmd in sub.commands if hasattr(cmd, "point")] for sub in path.subpaths]


def test_offsets_and_containment_follow_the_units(axes):
    assert axes.to_scene_offset(1, 1) == pytest.approx((100, -40))
    assert axes.contains(0, 0) and axes.contains(3, 9)
    assert not axes.contains(3.01, 0) and not axes.contains(0, -1.5)


def test_a_region_under_a_curve_meets_the_curve_exactly(axes):
    area = axes.region(square, domain=(0, 2), name="area")
    assert area.name == "area" and area.drawable in axes.group.children
    [outline] = outlines(area.drawable)
    top = [maths(axes, p) for p in outline[:len(outline) // 2]]
    for x, y in top:
        assert y == pytest.approx(x * x, abs=1e-9)  # every top point is on y = x^2
    assert top[0] == pytest.approx((0, 0)) and top[-1] == pytest.approx((2, 4))
    bottom = [maths(axes, p) for p in outline[len(outline) // 2:]]
    assert all(y == pytest.approx(0, abs=1e-9) for _, y in bottom)
    box = area.drawable.get_bounds()
    assert (box.x, box.y) == pytest.approx((axes.to_scene(0, 4).x, axes.to_scene(0, 4).y), abs=1)
    assert area.drawable.z_index < 0  # beneath the grid and the curve


def test_a_region_is_cut_to_the_ranges_and_breaks_where_there_is_no_value(axes):
    tall = axes.region(lambda x: 3 * x * x, name="tall")
    for outline in outlines(tall.drawable):
        assert all(-1 - 1e-9 <= maths(axes, p)[1] <= 9 + 1e-9 for p in outline)
    split = axes.region(lambda x: math.sqrt(x * x - 1), 0, name="split")
    assert len(split.drawable.subpaths) == 2  # no value between -1 and 1
    between = axes.region(lambda x: x + 2, square, domain=(-1, 2), color=(40, 150, 90), opacity=0.5)
    assert between.drawable.fill.opacity == 0.5
    with pytest.raises(ValidationError, match="Nothing to shade"):
        axes.region(square, square)
    with pytest.raises(ValidationError, match="outside the axes' x range"):
        axes.region(square, domain=(5, 6))
    with pytest.raises(ValidationError, match="opacity"):
        axes.region(square, opacity=2)


def test_a_number_boundary_shades_above_or_below_a_curve(axes):
    above = axes.region(lambda x: x, 9, name="above")  # y > x, up to the top of the graph
    [outline] = outlines(above.drawable)
    assert all(maths(axes, p)[1] >= min(maths(axes, p)[0], 9) - 1e-9 for p in outline)


@pytest.mark.parametrize("rule, sample", [("left", 0.0), ("right", 1.0), ("mid", 0.5)])
def test_rectangles_meet_the_curve_at_their_rule_point(axes, rule, sample):
    riemann = axes.rectangles(square, (0, 2), 4, rule=rule, name=f"sum_{rule}")
    heights = []
    for outline in outlines(riemann.drawable):
        corners = [maths(axes, p) for p in outline]
        left, right = min(x for x, _ in corners), max(x for x, _ in corners)
        assert right - left == pytest.approx(0.5)
        heights.append((left, max(y for _, y in corners)))
    expected = [(a, (a + sample * 0.5) ** 2) for a in (0, 0.5, 1, 1.5)]
    if rule == "left":
        expected = expected[1:]  # the first has height 0 and is left out
    assert [(round(a, 9), round(h, 9)) for a, h in heights] == [(a, pytest.approx(h)) for a, h in expected]
    assert riemann.drawable.stroke is not None and riemann.drawable.z_index < 0


def test_bad_rectangles_are_refused(axes):
    with pytest.raises(ValidationError, match="inside the axes' x range"):
        axes.rectangles(square, (0, 4), 4)
    with pytest.raises(ValidationError, match="whole number"):
        axes.rectangles(square, (0, 2), 0)
    with pytest.raises(ValidationError, match="rule"):
        axes.rectangles(square, (0, 2), 4, rule="trapezoid")
    with pytest.raises(ValidationError, match="No rectangles"):
        axes.rectangles(lambda x: 0.0, (0, 2), 4)


def test_a_tangent_touches_the_curve_with_its_slope(axes):
    tangent = axes.tangent(square, 1.5, name="touching")
    line = tangent.drawable
    assert isinstance(line, Line)
    for end in (line.start, line.end):
        x, y = maths(axes, end)
        assert y == pytest.approx(2.25 + 3 * (x - 1.5), abs=1e-6)  # slope 2x = 3 at x = 1.5
        assert axes.contains(x, y) or abs(y - 9) < 1e-6 or abs(y + 1) < 1e-6
    short = axes.tangent(math.sin, 0, span=(-1, 1))
    assert [round(maths(axes, p)[0], 9) for p in (short.drawable.start, short.drawable.end)] == [-1, 1]


def test_no_tangent_where_there_is_a_corner_or_no_value(axes):
    with pytest.raises(ValidationError, match="no single tangent"):
        axes.tangent(abs, 0)
    with pytest.raises(ValidationError, match="no value"):
        axes.tangent(lambda x: math.sqrt(x), -1)
    with pytest.raises(ValidationError, match="outside the axes' ranges"):
        axes.tangent(lambda x: x + 20, 0)


def test_a_secant_passes_through_both_points(axes):
    chord = axes.secant(square, -1, 2, span=(-1, 2), name="chord")
    assert maths(axes, chord.drawable.start) == pytest.approx((-1, 1))
    assert maths(axes, chord.drawable.end) == pytest.approx((2, 4))
    across = axes.secant(square, 0, 1)
    assert maths(axes, across.drawable.start)[0] == pytest.approx(-1)  # y = x meets the bottom edge at -1
    with pytest.raises(ValidationError, match="two different"):
        axes.secant(square, 1, 1)


def test_intersections_and_roots(axes):
    assert axes.intersections(square, lambda x: x + 2) == [pytest.approx((-1, 1)), pytest.approx((2, 4))]
    assert axes.intersections(square) == [(0.0, 0.0)]  # touches the x axis without crossing
    assert axes.intersections(lambda x: x * x - 20) == []
    wide = Axes(axes.tutorial, box=(0, 0, 100, 100), x_range=(-4, 4), y_range=(-5, 5), name="wide")
    roots = [x for x, _ in wide.intersections(math.sin)]
    assert roots == [pytest.approx(-math.pi), 0.0, pytest.approx(math.pi)]
    poles = [x for x, _ in wide.intersections(math.tan, domain=(1, 2))]
    assert poles == []  # tan jumps across 0 at pi/2 but never meets it there


def test_own_shapes_are_clipped_exactly_and_join_the_graph(axes):
    [triangle] = axes.clip([(-3, 0), (1, 0), (1, 12)], closed=True)
    assert all(axes.contains(*(round(v, 9) for v in maths(axes, p))) for p in triangle)
    shape = axes.add(Polygon(vertices=triangle, fill=FillStyle(color=Color(250, 200, 120))), name="wedge")
    assert shape.name == "wedge" and shape.drawable in axes.group.children
    box = shape.drawable.get_bounds()
    assert box.x >= axes.box.left - 1 and box.y >= axes.box.top - 1  # bounds are the visible part
    pieces = axes.clip([(-3, 1), (0, 1), (0, 12), (1, 12), (1, 1), (4, 1)])
    assert len(pieces) == 2  # leaves over the top edge and comes back
    assert axes.clip([(10, 10), (20, 20)]) == []
    assert axes.add(Line(start=Point(0, 0), end=Point(1, 1))).name.startswith("axes_shape")
    with pytest.raises(ValidationError, match="at least 3"):
        axes.clip([(0, 0), (1, 1)], closed=True)
    with pytest.raises(ValidationError, match="drawable"):
        axes.add("triangle")


def test_constructions_survive_save_and_load(axes, tmp_path):
    tutorial = axes.tutorial
    axes.plot(square, name="parabola")
    axes.region(square, domain=(0, 2), name="area")
    axes.tangent(square, 1, name="tangent")
    tutorial.step("Area")
    loaded = Tutorial.load_json(tutorial.save_json(tmp_path / "area.tutordraw.json"))
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    again = Axes.find(loaded)
    assert again.rectangles(square, (0, 2), 4).name.startswith("axes_rectangles")
    assert isinstance(loaded.get_target("area").drawable, Path)


@pytest.mark.parametrize("box, x_range, y_range", [
    ((100, 50, 400, 300), (-0.5, 2.5), (-0.5, 5)),
    ((100, 50, 300, 200), (-0.5, 2.5), (-0.5, 5)),
    ((100, 50, 300, 200), (-1, 3), (-1, 9)),
    ((100, 50, 300, 200), (-0.2, 2), (-0.2, 4)),
    ((100, 50, 300, 200), (-0.5, 5), (-2, 25)),
    ((110, 40, 560, 440), (-0.5, 2.5), (-0.5, 5)),
])
def test_tick_numbers_never_touch_the_origin_or_each_other(box, x_range, y_range):
    # With a range starting just below 0, the "-0.5" numbers sat on the "0" written below-left of the origin.
    from drawcv import Text

    tutorial = Tutorial(Scene(960, 540, background=Color.white()))
    graph = Axes(tutorial, box=box, x_range=x_range, y_range=y_range)
    texts = [child for child in graph.group.children if isinstance(child, Text)]
    for index, first in enumerate(texts):
        for second in texts[index + 1:]:
            a, b = first.get_bounds(), second.get_bounds()
            touching = (min(a.right, b.right) - max(a.left, b.left) > -2
                        and min(a.bottom, b.bottom) - max(a.top, b.top) > -2)
            assert not touching, (first.text, second.text)
    assert "0" in [text.text for text in texts]  # the origin keeps its number
    ticks = [child for child in graph.group.children if isinstance(child, Line)
             and abs(child.start.x - child.end.x) < 1e-9 and abs(child.end.y - child.start.y) == 8]
    xs = graph._ticks(graph.x_range, graph.x_step)
    assert len(ticks) == len([x for x in xs if abs(x) >= graph.x_step / 2])  # every tick mark is still drawn

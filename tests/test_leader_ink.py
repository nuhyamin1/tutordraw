"""A leader ends on the shape it points at, not on the corner of its bounding box.

A label or callout is placed beside a point of its target's bounds (its top,
left, ...) and its leader was drawn to that point. For a rectangle or circle
the point lies on the shape; for a triangle, a slanted line or any irregular
outline it can lie in empty space (seen: a callout on a right triangle whose
leader stopped in the air above the hypotenuse). The leader now ends at the
point of the shape's own outline nearest that bounds point. The panel is
placed as before.
"""

import math

import pytest
from drawcv import Color, FillStyle, Line, Point, Polygon, Rectangle, Scene, StrokeStyle

from tutordraw import Tutorial

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def leader_of(shape, anchor, callout=False):
    scene = Scene(960, 600, background=Color.white())
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="shape")
    step = tutorial.step("One", duration=1)
    if callout:
        step.explain(target, "Right angle at the corner: the two shorter sides meet at 90 degrees.",
                     anchor=anchor)
    else:
        step.show(target.label("label", anchor=anchor, gap=60))
    [annotation] = tutorial.layout(0).annotations
    return annotation, shape.get_bounds()


def distance_to_segment(p, a, b):
    ax, ay, bx, by = a.x, a.y, b.x, b.y
    length = (bx - ax) ** 2 + (by - ay) ** 2
    t = max(0.0, min(1.0, ((p.x - ax) * (bx - ax) + (p.y - ay) * (by - ay)) / length))
    return math.hypot(p.x - (ax + t * (bx - ax)), p.y - (ay + t * (by - ay)))


TRIANGLE = [Point(569, 259), Point(569, 537), Point(986, 537)]


def triangle():
    return Polygon(vertices=list(TRIANGLE), fill=FillStyle(color=Color(120, 140, 180)),
                   stroke=StrokeStyle(color=Color(50, 70, 110), width=3))


def on_outline(point, vertices):
    edges = zip(vertices, vertices[1:] + vertices[:1])
    return min(distance_to_segment(point, a, b) for a, b in edges)


@pytest.mark.parametrize("callout", [True, False])
def test_a_leader_to_a_triangle_ends_on_the_triangle(callout):
    annotation, box = leader_of(triangle(), "top", callout)
    start, end = annotation.leader
    assert on_outline(start, TRIANGLE) < 1.5                       # on the hypotenuse, not in the air
    assert math.hypot(start.x - box.center.x, start.y - box.top) > 20
    # The leader still leaves the panel's edge toward it.
    panel = annotation.panel
    assert panel.left - 0.5 <= end.x <= panel.right + 0.5 and panel.top - 0.5 <= end.y <= panel.bottom + 0.5


def test_a_leader_to_a_rectangle_is_unchanged():
    annotation, box = leader_of(Rectangle(position=Point(300, 250), width=300, height=150,
                                          fill=FillStyle(color=Color(200, 210, 230))), "top")
    start, _ = annotation.leader
    assert (start.x, start.y) == pytest.approx((box.center.x, box.top))


def test_a_leader_to_a_slanted_line_ends_on_the_line():
    line = Line(start=Point(200, 500), end=Point(700, 200), stroke=StrokeStyle(color=Color(0, 0, 0), width=3))
    annotation, _ = leader_of(line, "right")
    start, _ = annotation.leader
    assert distance_to_segment(start, Point(200, 500), Point(700, 200)) < 1.5

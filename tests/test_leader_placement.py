"""Placement weighs where a panel's leader goes, not only what the panel covers.

Seen in Illustrate: a callout on a vector drawn on a graph was put below the
graph, its leader crossing the x-axis and the grid, although the authored
slot beside the arrow's tip was free. Two causes: a rounding residue made that
free slot count as off the canvas, and nothing charged a leader for crossing
artwork, other panels or other leaders, or for its length.
"""

import pytest
from drawcv import Arrow, BoundingBox, Color, FillStyle, Point, Scene, StrokeStyle

from tutordraw import Tutorial
from tutordraw.collision import outside_area, segment_in_box
from tutordraw.kits import Axes

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def test_a_panel_inside_the_canvas_is_exactly_on_it():
    # area - overlap left 7e-12 px² here, which the resolver counted as off canvas.
    assert outside_area(BoundingBox(586.5, 154.35, 267, 108.8), 1240, 600) == 0.0
    assert outside_area(BoundingBox(-10, 0, 20, 10), 100, 100) == pytest.approx(100)


def test_segment_length_inside_a_box():
    box = BoundingBox(10, 10, 20, 20)
    assert segment_in_box(Point(0, 20), (40, 20), box) == pytest.approx(20)
    assert segment_in_box(Point(0, 0), (40, 40), box) == pytest.approx(20 * 2 ** 0.5)
    assert segment_in_box(Point(0, 0), (5, 40), box) == 0.0


def vector_on_a_graph(anchor):
    scene = Scene(1240, 600, background=Color.white())
    tutorial = Tutorial(scene)
    axes = Axes(tutorial, box=(75, 65, 530, 500), x_range=(-4, 4), y_range=(-4, 4), grid=True)
    ink = Color(70, 130, 180)
    vector = axes.add(Arrow(start=axes.to_scene(0.2, 0.7), end=axes.to_scene(3.2, 2.7),
                            stroke=StrokeStyle(color=ink, width=5), fill=FillStyle(color=ink)), name="v")
    tutorial.step("Move", duration=2).explain(
        vector, "The vector moves to a new spot, but straight lines stay straight.", anchor=anchor)
    return tutorial


@pytest.mark.parametrize("anchor", ["right", "bottom"])
def test_a_callout_on_a_vector_on_a_graph_stays_clear_of_the_axes(anchor):
    tutorial = vector_on_a_graph(anchor)
    [callout] = tutorial.layout(0).annotations
    assert callout.anchor == "right"  # beside the tip, in the free space right of the graph
    start, end = callout.leader
    assert end.x - start.x < 60 and callout.panel.left > 580  # short, and off the grid
    assert tutorial.lint() == []

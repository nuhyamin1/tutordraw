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
    assert end.x - start.x < 80  # short
    assert callout.panel.left > 580  # at most at the edge of the grid, whose right edge is x = 605
    assert tutorial.lint() == []


def test_a_label_moves_off_the_grid_when_there_is_room_beside_it():
    # The grid is not a target, but covering it hides what the graph is read by.
    scene = Scene(900, 600, background=Color.white())
    tutorial = Tutorial(scene)
    axes = Axes(tutorial, box=(75, 65, 530, 500), x_range=(-4, 4), y_range=(-4, 4), grid=True)
    point = axes.point(3.6, 2.5, name="p")
    tutorial.step("One").show(point.label("The point P, near the edge", anchor="left"))
    [label] = tutorial.layout(0).annotations
    assert label.anchor == "right" and label.panel.left > 605  # beside the plot, not on its grid
    assert tutorial.lint() == []


def test_grid_lines_are_tagged_and_survive_a_save():
    scene = Scene(600, 400, background=Color.white())
    tutorial = Tutorial(scene)
    Axes(tutorial, box=(40, 40, 400, 300), x_range=(0, 4), y_range=(0, 4), grid=True)
    from tutordraw.adapters.drawcv import index_scene

    def grid(t):
        return sorted((o.start.x, o.start.y, o.end.x, o.end.y)
                      for o in index_scene(t.scene).values() if "td-grid" in o.tags)

    assert len(grid(tutorial)) == 18  # a line at every tick (0.5 apart) each way
    assert grid(Tutorial.from_dict(tutorial.to_dict())) == grid(tutorial)

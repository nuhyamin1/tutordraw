"""Lint: a graph or number line drawn over other artwork.

A chart is read on its own: its grid and numbers say where things are, so a
grid running through an unrelated picture hides the picture and garbles the
chart. Text under a chart is already TEXT_ON_DIAGRAM; this is the same for
shapes. A shape behind the whole chart (a panel or card it sits on), one it
only grazes, and anything added to the chart itself are not reported.
"""

import pytest
from drawcv import Color, FillStyle, Point, Rectangle, Scene, StrokeStyle

from tutordraw import Tutorial
from tutordraw.kits import Axes, NumberLine

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def board(*shapes, line=False):
    scene = Scene(960, 540, background=Color.white())
    for shape in shapes:
        scene.add(shape)
    tutorial = Tutorial(scene)
    if line:
        NumberLine(tutorial, start=(80, 300), length=500, value_range=(0, 10), step=1, name="line")
    else:
        axes = Axes(tutorial, box=(60, 60, 460, 420), x_range=(0, 4), y_range=(0, 20), name="graph")
        axes.plot(lambda x: x * x, name="curve")
    tutorial.step("One", duration=1)
    return tutorial


def codes(tutorial):
    return [issue for issue in tutorial.lint(0) if issue.code == "CHART_OVER_ARTWORK"]


def pen(x=120, y=200, width=260, height=120):
    return Rectangle(position=Point(x, y), width=width, height=height, name="pen",
                     fill=FillStyle(color=Color(150, 190, 150)), stroke=StrokeStyle(color=Color(60, 100, 60), width=3))


def test_a_graph_over_a_picture_is_reported():
    [issue] = codes(board(pen()))
    assert issue.severity == "warning"
    assert "graph" in issue.message and "pen" in issue.message


def test_a_number_line_over_a_picture_is_reported():
    assert codes(board(pen(y=260, height=80), line=True))


def test_a_panel_behind_the_chart_is_not():
    card = Rectangle(position=Point(20, 20), width=900, height=500, name="card",
                     fill=FillStyle(color=Color(245, 245, 250)))
    assert not codes(board(card))


def test_a_shape_the_chart_only_grazes_is_not():
    assert not codes(board(pen(x=500, y=100, width=200, height=100)))  # a sliver of its left edge


def test_what_is_drawn_on_the_chart_is_not():
    scene = Scene(960, 540, background=Color.white())
    tutorial = Tutorial(scene)
    axes = Axes(tutorial, box=(60, 60, 460, 420), x_range=(0, 4), y_range=(0, 20), name="graph")
    axes.add(Rectangle(position=Point(200, 200), width=100, height=100, fill=FillStyle(color=Color(200, 220, 250))),
             name="slice")
    tutorial.step("One", duration=1)
    assert not codes(tutorial)


def test_a_panel_the_chart_mostly_sits_on_is_not():
    # The chart's numbers poke out past the card's edge: still its background.
    card = Rectangle(position=Point(70, 30), width=880, height=480, name="card",
                     fill=FillStyle(color=Color(245, 245, 250)))
    assert not codes(board(card))

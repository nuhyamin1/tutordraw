"""Contract coverage against the pinned, published DrawCV wheel."""

from copy import deepcopy

import numpy as np
import pytest
from drawcv import (Arrow, Circle, Color, Ellipse, FillStyle, Line, Point,
                    Polygon, Polyline, Rectangle, Scene, StrokeStyle, Text, Transform)

from tutordraw import Tutorial
from tutordraw.adapters.drawcv import copy_scene, crisp_rect


@pytest.mark.parametrize("factory", [
    lambda: Circle(center=Point(200, 200), radius=35, fill=FillStyle(color=Color(30, 80, 160))),
    lambda: Ellipse(center=Point(200, 200), radius_x=45, radius_y=25,
                    fill=FillStyle(color=Color(30, 80, 160))),
    lambda: Rectangle(position=Point(160, 170), width=80, height=60,
                      fill=FillStyle(color=Color(30, 80, 160))),
    lambda: Line(start=Point(160, 170), end=Point(240, 230), stroke=StrokeStyle(width=3)),
    lambda: Arrow(start=Point(160, 170), end=Point(240, 230), stroke=StrokeStyle(width=3)),
    lambda: Polygon(vertices=[Point(160, 230), Point(200, 170), Point(240, 230)],
                    fill=FillStyle(color=Color(30, 80, 160))),
    lambda: Polyline(points=[Point(160, 230), Point(200, 170), Point(240, 230)],
                     stroke=StrokeStyle(width=3)),
    lambda: Text(text="Subject", position=Point(160, 180), font_scale=0.8),
], ids=["circle", "ellipse", "rectangle", "line", "arrow", "polygon", "polyline", "text"])
def test_transformed_shapes_copy_and_render_as_targets(factory):
    scene = Scene(800, 500, background=Color.white())
    shape = factory()
    shape.transform = Transform(translation_x=20, rotation=15, scale_x=1.2, scale_y=0.9)
    shape.metadata = {"lesson": {"tags": ["subject"]}}
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape)
    step = tutorial.step("Inspect").show(target.label("Subject", gap=70))
    step.highlight(target).dim_others(target)
    before = deepcopy(scene.to_dict())
    copied = copy_scene(scene)
    assert copied.to_dict() == before
    copied.get(shape.id).metadata["lesson"]["tags"].append("copy only")
    first = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(first, tutorial.render_step(0).to_numpy())
    assert first.shape == (500, 800, 3)
    assert scene.to_dict() == before


@pytest.mark.parametrize("stroke, expected", [
    (1, (40.5, 30.5, 100.0, 49.0)),
    (3, (40.5, 30.5, 100.0, 49.0)),
    (2, (41.0, 31.0, 99.0, 49.0)),
    (1.5, (40.2, 30.3, 100.4, 49.9)),
])
def test_crisp_rect_snaps_edges_inward_onto_the_pixel_grid(stroke, expected):
    assert crisp_rect(40.2, 30.3, 100.4, 49.9, stroke) == pytest.approx(expected)


def test_crisp_rect_keeps_a_border_flush_with_the_canvas_on_screen():
    # A panel clamped to x + width == 1100 must not snap its border to 1100.5.
    assert crisp_rect(1000, 0, 100, 50, 1) == (1000.5, 0.5, 99, 49)
    assert crisp_rect(10, 10, 0.4, 0.4, 1) == (10, 10, 0.4, 0.4)


def _exact_rows(image, color, column):
    """Rows of one column painted exactly `color`, in either channel order."""
    pixels = image[:, column, :]
    return int((np.all(pixels == color, axis=1) | np.all(pixels == color[::-1], axis=1)).sum())


def test_panel_border_and_highlight_render_as_whole_pixels():
    # DrawCV 0.11 covers area exactly, so a 1 px border on a whole coordinate
    # would be two half-tone pixels and no pixel would carry the border colour.
    scene = Scene(600, 400, background=Color.white())
    shape = Rectangle(position=Point(100.3, 150.7), width=80.4, height=60.2,
                      fill=FillStyle(color=Color(30, 80, 160)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape)
    tutorial.step("Inspect").show(target.label("Subject", gap=70.3)).highlight(target)
    image = tutorial.render_step(0).to_numpy()
    theme = tutorial.theme
    border = np.array(theme.border_color)
    highlight = np.array(theme.highlight_color)
    columns = range(image.shape[1])
    assert max(_exact_rows(image, border, c) for c in columns) > 10
    # A 3 px highlight edge is three solid columns with no half-tone beside it.
    row = image[int(shape.position.y + 30), :, :]
    solid = np.all(row == highlight, axis=1) | np.all(row == highlight[::-1], axis=1)
    left = int(np.argmax(solid))
    assert solid[left:left + 3].all() and not solid[left + 3]
    assert np.all(row[left - 1] == 255) and np.all(row[left + 3] != highlight)

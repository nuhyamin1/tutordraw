"""Contract coverage against the pinned, published DrawCV wheel."""

from copy import deepcopy

import numpy as np
import pytest
from drawcv import (Arrow, Circle, Color, Ellipse, FillStyle, Line, Point,
                    Polygon, Polyline, Rectangle, Scene, StrokeStyle, Text, Transform)

from tutordraw import Tutorial
from tutordraw.adapters.drawcv import copy_scene


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

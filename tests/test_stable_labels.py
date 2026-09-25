"""A label keeps the place it had in the previous step while that place stays free.

Every step used to place its labels afresh. When something else moved, a
label could leap across the canvas: in Illustrate's calculus test lesson the
"meet" label of a crossing point jumped 222 px in the step that slides a
marker along the curve, because the marker's path crossed its slot for a
moment, although the slot was free again when the marker stopped.
"""

import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene

from tutordraw import Tutorial

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(end=(420, 120), steps=3):
    """A labelled dot, and a marker that slides from the bottom left to `end` in step 1."""
    scene = Scene(900, 500, background=Color.white())
    dot = Circle(center=Point(300, 250), radius=6, fill=FillStyle(color=Color(40, 100, 200)))
    marker = Circle(center=Point(200, 400), radius=8, fill=FillStyle(color=Color(120, 90, 200)))
    scene.add(dot)
    scene.add(marker)
    tutorial = Tutorial(scene)
    point, mover = tutorial.target(dot, name="point"), tutorial.target(marker, name="marker")
    meet = point.label("meet", anchor="right")
    move = (end[0] - 200, end[1] - 400)
    tutorial.step("Rest").show(meet)
    tutorial.step("Along").animate().show(meet).restyle(mover, move=move)
    if steps > 2:
        tutorial.step("After").show(meet).restyle(mover, move=move)
    return tutorial


def panel(tutorial, index):
    [label] = [a for a in tutorial.layout(index).annotations if a.text == "meet"]
    return label.panel


def test_a_label_stays_put_while_something_passes_through_its_place():
    tutorial = lesson()
    assert panel(tutorial, 1) == panel(tutorial, 0)
    assert panel(tutorial, 2) == panel(tutorial, 0)


def test_every_frame_of_the_moving_step_keeps_the_same_place():
    tutorial = lesson()
    start = tutorial.steps[0].duration + tutorial.steps[0].pause
    places = {tuple(round(v, 3) for v in (a.panel.x, a.panel.y))
              for k in range(9) for a in tutorial.layout(1, time=k * tutorial.steps[1].duration / 8).annotations}
    assert places == {(panel(tutorial, 0).x, panel(tutorial, 0).y)}
    assert start > 0


def test_a_label_whose_place_ends_up_taken_moves():
    # The marker stops right on the label's place, so keeping it would hide one under the other.
    tutorial = lesson(end=(345, 250))
    assert panel(tutorial, 1) != panel(tutorial, 0)
    marker = tutorial.layout(1).targets["marker"]
    moved = panel(tutorial, 1)
    assert not (moved.left < marker.right and marker.left < moved.right
                and moved.top < marker.bottom and marker.top < moved.bottom)


def test_a_moved_label_keeps_its_new_place_in_the_next_step():
    # Step 2 takes the marker away again: the label does not jump back while its new place is free.
    tutorial = lesson(end=(345, 250), steps=2)
    meet = tutorial.labels[0]
    tutorial.step("Back").show(meet)
    assert panel(tutorial, 2) == panel(tutorial, 1)


def test_a_step_on_its_own_places_labels_as_before():
    # Without a previous step there is nothing to keep: the first step is placed as it always was.
    tutorial = lesson()
    first = Tutorial(tutorial.scene)
    point = first.target(tutorial.targets[0].drawable, name="point")
    first.target(tutorial.targets[1].drawable, name="marker")
    first.step("Rest").show(point.label("meet", anchor="right"))
    assert panel(first, 0) == panel(tutorial, 0)


def curve_lesson():
    """A labelled dot beside a long diagonal stroke, and a small marker moving far away in step 1."""
    from drawcv import Line, StrokeStyle

    scene = Scene(900, 500, background=Color.white())
    dot = Circle(center=Point(300, 250), radius=6, fill=FillStyle(color=Color(40, 100, 200)))
    stroke = Line(start=Point(250, 480), end=Point(700, 20), stroke=StrokeStyle(color=Color(40, 100, 200), width=3))
    marker = Circle(center=Point(800, 450), radius=8, fill=FillStyle(color=Color(120, 90, 200)))
    for shape in (dot, stroke, marker):
        scene.add(shape)
    tutorial = Tutorial(scene)
    point = tutorial.target(dot, name="point")
    tutorial.target(stroke, name="curve")
    mover = tutorial.target(marker, name="marker")
    meet = point.label("meet", anchor="right")
    tutorial.step("Rest")
    return tutorial, meet, mover


def test_a_still_stroke_blocks_only_along_its_ink_in_an_animated_step_too():
    # An animated step used to treat every stroke as its whole bounding box, still or not, so a label
    # next to a long diagonal curve was placed as if the curve filled its box, in any step that moved
    # something else. The label first appears in the moving step, so there is no earlier place to keep.
    tutorial, meet, mover = curve_lesson()
    tutorial.step("Move").animate().show(meet).restyle(mover, move=(0, -300))
    cut, meet_cut, mover_cut = curve_lesson()
    cut.step("Move").show(meet_cut).restyle(mover_cut, move=(0, -300))
    assert panel(tutorial, 1) == panel(cut, 1)

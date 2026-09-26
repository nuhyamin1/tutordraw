"""Lint for the drawing's own words: text and equations on each other, on a kit, or off the canvas.

lint() used to check annotations only. A scene's own text (a caption, a
title) and equations placed by an author or a model could sit on each other
or on a graph's tick numbers and nothing said so; Illustrate's DeepSeek
lessons did it in most beats that held more than one equation.
"""

import pytest
from drawcv import Color, Point, Scene, Text

from tutordraw import Tutorial
from tutordraw.arrange import clear, collisions, diagrams, occupied, shift_to, words
from tutordraw.kits import Axes, Equation

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def text(content, x, y, scale=0.8):
    return Text(text=content, position=Point(x, y), font_scale=scale, color=Color(20, 30, 40))


def lesson():
    scene = Scene(960, 540, background=Color.white())
    tutorial = Tutorial(scene)
    graph = Axes(tutorial, box=(60, 60, 480, 400), x_range=(-0.5, 2.5), y_range=(-0.5, 5), grid=True,
                 name="graph")
    return scene, tutorial, graph


def issues(tutorial, code, index=0):
    return [issue for issue in tutorial.lint(index) if issue.code == code]


def test_text_on_text_is_an_error_naming_both():
    scene, tutorial, _ = lesson()
    title, caption = text("The area under a curve", 600, 100), text("Thin slices", 620, 110)
    scene.add(title)
    scene.add(caption)
    tutorial.target(title, name="title")
    tutorial.step("One")
    found = issues(tutorial, "TEXT_OVERLAP")
    assert len(found) == 1 and found[0].severity == "error"
    assert set(found[0].targets) == {"title", "'Thin slices'"}  # unregistered text goes by its words
    assert "beside, below or above" in found[0].fix


def test_an_equation_on_a_graph_is_reported_against_the_graph():
    scene, tutorial, graph = lesson()
    Equation(tutorial, r"\frac{x^3}{3}", position=(96, 404), size=30, name="antiderivative")
    tutorial.step("One")
    found = issues(tutorial, "TEXT_ON_DIAGRAM")
    assert [issue.targets for issue in found] == [("antiderivative", "graph")]
    assert found[0].severity == "warning"


def test_words_clear_of_everything_report_nothing():
    scene, tutorial, graph = lesson()
    Equation(tutorial, r"\int_0^2 x^2\,dx", position=(600, 80), size=40, name="integral")
    scene.add(text("Thin slices add up", 600, 200))
    tutorial.step("One")
    assert [i for i in tutorial.lint(0) if i.code.startswith("TEXT_")] == []


def test_a_hidden_word_is_not_there():
    scene, tutorial, _ = lesson()
    first, second = text("First note", 600, 100), text("Second note", 600, 104)
    scene.add(first)
    scene.add(second)
    hidden = tutorial.target(second, name="second")
    tutorial.step("Both")
    tutorial.step("One").restyle(hidden, visible=False)
    tutorial.step("Faded").restyle(hidden, opacity=0)
    assert issues(tutorial, "TEXT_OVERLAP", 0)
    assert not issues(tutorial, "TEXT_OVERLAP", 1)
    assert not issues(tutorial, "TEXT_OVERLAP", 2)


def test_a_kits_own_words_are_the_kits_business():
    # Text inside a kit (tick numbers, a caption added to the graph) is laid out by the kit, not
    # reported as free text; the kit's own tests cover it.
    scene, tutorial, graph = lesson()
    graph.add(text("rise 3", 300, 200))
    tutorial.step("One")
    assert not [i for i in tutorial.lint(0) if i.code.startswith("TEXT_")]


def test_words_off_the_canvas_are_reported():
    scene, tutorial, _ = lesson()
    scene.add(text("Running past the right edge of the canvas", 800, 300))
    tutorial.step("One")
    found = issues(tutorial, "TEXT_OFF_CANVAS")
    assert len(found) == 1 and found[0].severity == "warning"


def test_annotations_are_not_words_of_the_drawing():
    scene, tutorial, graph = lesson()
    note = text("A note", 700, 300)
    scene.add(note)
    target = tutorial.target(note, name="note")
    tutorial.step("One").show(target.label("labelled", anchor="left"))
    frame = tutorial.layout(0).scene
    assert [drawable.id for drawable, _ in words(frame)] == [note.id]
    assert [group.name for group, _ in diagrams(frame)] == ["graph"]
    assert collisions(frame) == []


def test_a_word_on_a_graph_moves_just_clear_of_its_ink():
    # Off the lines and text the graph draws, not off its whole bounding box: a title on the
    # y-axis name slides a little, instead of jumping below the graph.
    scene, tutorial, graph = lesson()
    title = text("Area under a curve", 100, 28, 1.0)
    scene.add(title)
    tutorial.step("One")
    frame = tutorial.layout(0).scene
    [(word, box)] = words(frame)
    assert collisions(frame) == [(word, next(group for group, _ in diagrams(frame)))]
    moved = clear(box, occupied(frame, exclude=[word]), canvas=(960, 540))
    assert moved is not None and abs(moved.x - box.x) + abs(moved.y - box.y) < 120
    shift_to(title, moved.x, moved.y)
    assert collisions(tutorial.layout(0).scene) == []
    assert not [i for i in tutorial.lint(0) if i.code.startswith("TEXT_")]


def test_hairlines_count_as_ink():
    # A grid line's bounds are about 1 px thick; an equation lying across only grid lines is on the graph.
    scene, tutorial, graph = lesson()
    Equation(tutorial, r"\sum_{i=1}^{n} f(x_i)", position=(500, 130), size=40, name="riemann")
    tutorial.step("One")
    assert [issue.targets for issue in issues(tutorial, "TEXT_ON_DIAGRAM")] == [("riemann", "graph")]


def test_text_the_camera_crops_is_not_off_the_canvas():
    # A zoom pushes a corner title out of frame on purpose; only text off the drawing itself is reported.
    from drawcv import Circle, Color, FillStyle, Point, Scene, Text

    from tutordraw import Tutorial

    scene = Scene(600, 400, background=Color.white())
    scene.add(Text(text="TITLE", position=Point(20, 20), font_scale=0.8, thickness=2))
    scene.add(Text(text="Too far right", position=Point(560, 380), font_scale=0.8))
    ball = Circle(center=Point(400, 250), radius=20, fill=FillStyle(color=Color(80, 120, 200)))
    scene.add(ball)
    tutorial = Tutorial(scene)
    target = tutorial.target(ball, name="ball")
    tutorial.step("Zoomed").zoom_to(target, padding=40, max_scale=3)
    off = [i for i in tutorial.lint() if i.code == "TEXT_OFF_CANVAS"]
    assert [i.targets for i in off] == [("'Too far right'",)]

"""Tutorial.layout and Tutorial.lint: the author -> lint -> fix loop."""

import json
import warnings

import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Point, Rectangle, Scene

from golden_lessons import LESSONS
from tutordraw import Composition, Issue, Theme, Tutorial, ValidationError

# The motion and clash lessons pin frames that cannot be placed cleanly.
pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def codes(issues):
    return sorted({issue.code for issue in issues})


def lesson(theme=None, width=600, height=360, background=Color.white()):
    scene = Scene(width, height, background=background)
    return scene, Tutorial(scene, theme=theme)


def test_clean_lessons_report_nothing():
    for name in ("bare", "edges", "groups"):
        assert LESSONS[name][0]().lint() == [], name


def test_real_problems_in_the_golden_lessons_are_found():
    cell = LESSONS["cell"][0]().lint()
    assert ("LEADERS_CROSS", 2) in {(i.code, i.step) for i in cell}
    crowded = LESSONS["crowded"][0]().lint()
    crossing = [i for i in crowded if i.code == "LEADER_CROSSES_TARGET"]
    assert crossing and crossing[0].targets == ("ball_b", "ball_c")
    assert "LEADER_CROSSES_PANEL" in codes(crowded)
    assert "UNPLACEABLE" in codes(LESSONS["motion"][0]().lint(1))


def test_overlap_and_off_canvas_are_errors_when_avoidance_is_off():
    scene, tutorial = lesson(Theme(avoid_collisions=False))
    a = Circle(center=Point(560, 180), radius=20, fill=FillStyle(color=Color(40, 90, 160)))
    b = Circle(center=Point(560, 200), radius=20, fill=FillStyle(color=Color(160, 90, 40)))
    scene.add(a)
    scene.add(b)
    ta, tb = tutorial.target(a, name="a"), tutorial.target(b, name="b")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tutorial.step("Clash").show(ta.label("Label A", anchor="right"), tb.label("Label B", anchor="right"))
    issues = tutorial.lint()
    assert {"ANNOTATION_OVERLAP", "OFF_CANVAS"} <= set(codes(issues))
    assert issues[0].severity == "error"  # errors sort first
    assert all(i.fix for i in issues)


def test_covering_uses_the_real_shape_not_its_bounds():
    # A panel in the empty corner of a circle's bounding box covers nothing.
    scene, tutorial = lesson(Theme(avoid_collisions=False))
    ring = Circle(center=Point(300, 180), radius=150, fill=FillStyle(color=Color(200, 220, 240)))
    dot = Circle(center=Point(300, 180), radius=10, fill=FillStyle(color=Color(40, 40, 40)))
    scene.add(ring)
    scene.add(dot)
    tutorial.target(ring, name="ring")
    t_dot = tutorial.target(dot, name="dot")
    tutorial.step("Corner").show(t_dot.label("x", anchor="top", offset=(-130, -110), leader=False))
    tutorial.step("Middle").show(t_dot.label("On the ring", anchor="right", gap=20))
    assert "COVERS_TARGET" not in codes(tutorial.lint(0))
    covered = [i for i in tutorial.lint(1) if i.code == "COVERS_TARGET"]
    assert covered and covered[0].targets == ("dot", "ring")


def test_bare_text_on_dark_artwork_is_low_contrast():
    scene, tutorial = lesson()
    band = Rectangle(position=Point(0, 100), width=600, height=160, fill=FillStyle(color=Color(30, 40, 60)))
    dot = Circle(center=Point(150, 180), radius=16, fill=FillStyle(color=Color(240, 200, 60)))
    scene.add(band)
    scene.add(dot)
    t_dot = tutorial.target(dot, name="dot")
    tutorial.step("Bare").show(t_dot.label("Hard to read", box=False))
    tutorial.step("Boxed").show(t_dot.label("Easy to read"))
    assert "LOW_CONTRAST" in codes(tutorial.lint(0))
    assert "LOW_CONTRAST" not in codes(tutorial.lint(1))


def test_small_text_long_callouts_and_busy_steps():
    scene, tutorial = lesson(width=1200, height=800)
    targets = []
    for i in range(7):
        shape = Circle(center=Point(100 + 150 * i, 400), radius=12, fill=FillStyle(color=Color(90, 90, 90)))
        scene.add(shape)
        targets.append(tutorial.target(shape, name=f"t{i}"))
    step = tutorial.step("Busy").show(*(t.label(f"L{i}", anchor="top" if i % 2 else "bottom")
                                        for i, t in enumerate(targets[:6])))
    step.explain(targets[6], " ".join(["word"] * 45), max_width=300)
    tutorial.step("Tiny").show(targets[0].label("tiny", font_scale=0.3))
    assert {"BUSY_STEP", "LONG_CALLOUT"} <= set(codes(tutorial.lint(0)))
    assert "TEXT_TOO_SMALL" in codes(tutorial.lint(1))


def test_lint_changes_nothing_and_leaks_no_warnings():
    tutorial = LESSONS["motion"][0]()
    before = tutorial.render_step(1).to_numpy()
    source = json.dumps(tutorial.scene.to_dict(), sort_keys=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        issues = tutorial.lint()
    assert issues
    np.testing.assert_array_equal(before, tutorial.render_step(1).to_numpy())
    assert json.dumps(tutorial.scene.to_dict(), sort_keys=True) == source


def test_issues_serialize_for_a_model():
    issues = LESSONS["crowded"][0]().lint()
    data = json.loads(json.dumps([i.to_dict() for i in issues]))
    assert data[0].keys() == {"code", "severity", "step", "step_title", "message", "fix",
                              "targets", "annotations"}
    assert all(isinstance(i, Issue) for i in issues)


def test_layout_reports_geometry_at_a_time():
    tutorial = LESSONS["motion"][0]()
    end = tutorial.layout(1)
    assert isinstance(end, Composition)
    assert {a.text for a in end.annotations} == {"Body", "It lands on the track.", "Track"}
    # The track label is revealed at 2 s, so at 1 s it is not there yet.
    early = tutorial.layout(1, time=1.0)
    assert "Track" not in {a.text for a in early.annotations}
    assert early.targets["body"].x < end.targets["body"].x
    for bad in (-1, 99, True, "1"):
        with pytest.raises(ValidationError):
            tutorial.layout(1, time=bad)
    for bad in (-1, 2, True, None):
        with pytest.raises(ValidationError):
            tutorial.layout(bad)
    with pytest.raises(ValidationError):
        tutorial.lint(5)

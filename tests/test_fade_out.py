"""A target an animated step fades to fully transparent fades in the browser player too.

DrawCV's SVG export leaves out anything with opacity 0, so the step's
finished frame had no element for a target that fades out, and the player,
which tweens the elements present in both its start and finished frames,
had nothing to fade: it vanished as the step began. The finished frame now
keeps such a target at a vanishing opacity (FADED), so the player fades it
out over the step's motion. A step that cuts (no animation), or a target
that was already transparent, is left out as before.
"""

import re

import pytest
from drawcv import Circle, Color, FillStyle, Point, Scene

from tutordraw import Tutorial
from tutordraw.web import FADED, web_step

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(animate=True):
    scene = Scene(600, 400, background=Color.white())
    dot = Circle(center=Point(100, 200), radius=20, fill=FillStyle(color=Color(120, 90, 200)))
    other = Circle(center=Point(300, 200), radius=20, fill=FillStyle(color=Color(40, 140, 90)))
    scene.add(dot)
    scene.add(other)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    tutorial.target(other, name="other")
    tutorial.step("Shown", duration=1)
    step = tutorial.step("Fade", duration=3)
    if animate:
        step.animate("ease_in_out", seconds=0.8)
    step.restyle(target, opacity=0, move=(-50, 0))
    tutorial.step("Gone", duration=1).restyle(target, opacity=0, move=(-50, 0))
    return tutorial, dot


def opacity(svg, drawable_id):
    """The opacity attribute of the element for this drawable, or None when it is not in the SVG."""
    found = re.search(r'<[^>]*data-drawcv-id="%s"[^>]*>' % re.escape(drawable_id), svg)
    if not found:
        return None
    value = re.search(r'opacity="([^"]+)"', found.group(0))
    return float(value.group(1)) if value else 1.0


def test_a_target_faded_out_in_an_animated_step_stays_in_its_finished_frame():
    tutorial, dot = lesson()
    payload = web_step(tutorial, 1)
    assert opacity(payload["frames"][0], dot.id) == pytest.approx(1)
    assert opacity(payload["svg"], dot.id) == pytest.approx(FADED)   # there to fade, invisible at the end


def test_a_cut_or_a_target_already_gone_is_left_out():
    tutorial, dot = lesson(animate=False)
    assert opacity(web_step(tutorial, 1)["svg"], dot.id) is None
    tutorial, dot = lesson()
    assert opacity(web_step(tutorial, 2)["svg"], dot.id) is None       # transparent before the step, too


def test_the_scene_and_layout_are_unchanged():
    tutorial, dot = lesson()
    web_step(tutorial, 1)
    assert tutorial.layout(1).scene is not None
    assert dot.opacity == 1
    from tutordraw.adapters.drawcv import index_scene
    assert index_scene(tutorial._compose(1, 1.0).scene)[dot.id].opacity == 0   # nothing cached was changed
    assert index_scene(tutorial.layout(1).scene)[dot.id].opacity == 0

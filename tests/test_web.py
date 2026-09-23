"""SVG frames, web payloads and the exported player page."""

import json
import re
import xml.etree.ElementTree as ET

import pytest
from drawcv import Circle, Color, FillStyle, Point, Rectangle, Scene, Text, Transform, get_easing

from golden_lessons import LESSONS
from tutordraw import Theme, Tutorial, ValidationError
from tutordraw.web import CAMERA_KEYFRAMES, EASING_SAMPLES, player_source

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")
NS = {"s": "http://www.w3.org/2000/svg"}


def groups(svg: str) -> dict[str, ET.Element]:
    root = ET.fromstring(svg)
    return {g.get("data-drawcv-id"): g for g in root.iter("{http://www.w3.org/2000/svg}g")
            if g.get("data-drawcv-id")}


@pytest.fixture
def lesson():
    scene = Scene(640, 360, background=Color.white())
    a = Rectangle(position=Point(80, 140), width=90, height=60, fill=FillStyle(color=Color(90, 140, 200)))
    b = Circle(center=Point(480, 170), radius=36, fill=FillStyle(color=Color(200, 120, 90)))
    scene.add(Text(text="TITLE", position=Point(20, 20), font_scale=0.8, thickness=2))
    scene.add(a)
    scene.add(b)
    tutorial = Tutorial(scene, title="Web")
    return tutorial, tutorial.target(a, name="a"), tutorial.target(b, name="b")


def test_every_text_is_native_and_nothing_is_rasterised(lesson):
    tutorial, a, b = lesson
    tutorial.step("One").show(a.label("Label"), b.label("Bare", box=False))
    svg = tutorial.to_svg(0)
    root = ET.fromstring(svg)
    texts = [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")]
    assert sorted(texts) == ["Bare", "Label", "TITLE"]
    assert "data-drawcv-raster" not in svg and "<image" not in svg
    # The halo is one stroked text, not eight copies.
    bare = next(t for t in root.iter("{http://www.w3.org/2000/svg}text") if t.text == "Bare")
    assert bare.get("paint-order") == "stroke" and bare.get("stroke-width") == "6"
    assert "halo" not in svg
    # Widths are pinned to TutorDraw's measurement, so text fits its panel.
    label = next(t for t in root.iter("{http://www.w3.org/2000/svg}text") if t.text == "Label")
    measured = tutorial.layout(0).annotations[0]
    assert float(label.get("textLength")) <= measured.panel.width


def test_zoomed_text_is_placed_and_sized_in_world_space(lesson):
    tutorial, a, b = lesson
    tutorial.step("Wide")
    tutorial.step("Close").zoom_to(a, padding=10)
    wide = next(ET.fromstring(tutorial.to_svg(0)).iter("{http://www.w3.org/2000/svg}text"))
    scale = tutorial.layout(1).camera[0]
    close = ET.fromstring(tutorial.to_svg(1))
    title = [t for t in close.iter("{http://www.w3.org/2000/svg}text") if t.text == "TITLE"]
    assert title and float(title[0].get("font-size")) == pytest.approx(
        float(wide.get("font-size")) * scale, rel=1e-3)


def test_rotated_text_stays_raster_rather_than_misplaced():
    scene = Scene(300, 200, background=Color.white())
    scene.add(Text(text="Tilted", position=Point(50, 50), transform=Transform(rotation=30)))
    tutorial = Tutorial(scene)
    tutorial.step("One")
    assert "data-drawcv-raster" in tutorial.to_svg(0)


def test_ids_are_stable_across_frames_and_steps(lesson):
    tutorial, a, b = lesson
    label = a.label("Same label")
    tutorial.step("One").show(label)
    tutorial.step("Two").show(label).highlight(b)
    first, second = groups(tutorial.to_svg(0)), groups(tutorial.to_svg(1))
    owned = {key for key in first if key.startswith(f"td-{label.id}")}
    assert owned == {f"td-{label.id}-leader", f"td-{label.id}-panel", f"td-{label.id}-t0"}
    assert owned <= set(second)
    assert f"td-hl-{b.id}" in second
    assert groups(tutorial.to_svg(1)).keys() == second.keys()  # deterministic


def test_timing_attributes_follow_the_python_rules(lesson):
    tutorial, a, b = lesson
    tutorial.theme = Theme(draw_seconds=0.5)
    step = tutorial.step("Timed", duration=4)
    label = a.label("Later")
    step.show(label, at=1.0, draw=True)
    arrow = step.connect(a, b, "flow", at=2.0)
    step.highlight(b, at=0.5, draw=True)
    step.explain(b, "Too late", at=9.0)
    g = groups(tutorial.to_svg(0))
    leader, panel = g[f"td-{label.id}-leader"], g[f"td-{label.id}-panel"]
    assert (leader.get("data-td-at"), leader.get("data-td-draw")) == ("1", "0.5")
    assert panel.get("data-td-at") == "1.5" and panel.get("data-td-draw") is None
    assert g[f"td-{arrow.id}-s0"].get("data-td-at") == "2"
    assert g[f"td-{arrow.id}-s0"].get("data-td-draw") is None  # appears whole
    assert (g[f"td-hl-{b.id}"].get("data-td-at"), g[f"td-hl-{b.id}"].get("data-td-draw")) == ("0.5", "0.5")
    callout = step.callouts[0]
    assert g[f"td-{callout.id}-panel"].get("data-td-at") == "4"  # clamped to the step


def test_payload_frames_match_what_moves(lesson):
    tutorial, a, b = lesson
    tutorial.step("Still")
    tutorial.step("Slide").animate().restyle(a, move=(100, 0))
    tutorial.step("Zoom").animate().zoom_to(b)
    tutorial.step("Cut").restyle(a, move=(0, 50))
    still, slide, zoom, cut = (tutorial.web_step(i) for i in range(4))
    assert still["frames"] == [] and still["easing"] is None
    assert len(slide["frames"]) == 1 and len(slide["easing"]) == EASING_SAMPLES + 1
    assert len(zoom["frames"]) == CAMERA_KEYFRAMES and zoom["easing"] is None
    assert cut["frames"] == []
    curve = get_easing("ease_in_out")
    assert slide["easing"][EASING_SAMPLES // 4] == pytest.approx(curve(0.25), abs=1e-5)
    assert (slide["easing"][0], slide["easing"][-1]) == (0, 1)
    # A start frame shows the animated target where the step starts.
    start = groups(slide["frames"][0])[a.drawable_id]
    end = groups(slide["svg"])[a.drawable_id]
    assert ET.tostring(start) != ET.tostring(end)
    json.dumps(slide)  # plain JSON for any transport
    for bad in (-1, 4, True):
        with pytest.raises(ValidationError):
            tutorial.web_step(bad)


def test_export_web_writes_a_safe_self_contained_page(lesson, tmp_path):
    tutorial, a, b = lesson
    tutorial.title = "Levers @DATA@ </script><b>"
    tutorial.step("One").explain(a, "Ends a script? <!--<script></script><script>alert(1)</script>")
    path = tutorial.export_web(tmp_path / "lesson.html")
    page = path.read_text(encoding="utf-8")
    assert page.count("<script") == 3 and page.count("</script>") == 3
    assert "TutorDrawPlayer" in page and "alert(1)</script>" not in page
    assert "<title>Levers @DATA@ &lt;/script>&lt;b></title>" in page
    data = re.search(r'id="lesson-data">(.*?)</script>', page, re.S).group(1)
    bundle = json.loads(data)
    assert bundle["format"] == "tutordraw.web" and len(bundle["steps"]) == 1
    with pytest.raises(FileExistsError):
        tutorial.export_web(path)
    assert tutorial.export_web(path, overwrite=True) == path
    with pytest.raises(ValidationError):
        Tutorial(Scene(10, 10)).export_web(tmp_path / "empty.html")


def test_the_player_ships_with_the_package():
    source = player_source()
    assert "class TutorDrawPlayer" in source and "append(step)" in source


def test_golden_lessons_export_without_raster_text():
    for name, (build, _) in LESSONS.items():
        tutorial = build()
        for i in range(len(tutorial.steps)):
            assert "data-drawcv-raster" not in tutorial.to_svg(i), (name, i)

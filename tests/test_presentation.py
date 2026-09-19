from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Group, OpenCVRenderer, Point, Scene, Text, Transform

from tutordraw import ExportError, Theme, Tutorial, ValidationError
from tutordraw.adapters.drawcv import copy_scene
from tutordraw.attention import apply_attention
from tutordraw.layout import label_artwork, wrap_text


@pytest.fixture
def lesson():
    scene = Scene(900, 600, background=Color.white())
    first = Circle(center=Point(180, 280), radius=30, fill=FillStyle(color=Color(30, 80, 160)))
    second = Circle(center=Point(320, 280), radius=30, fill=FillStyle(color=Color(30, 80, 160)))
    scene.add(first)
    scene.add(second)
    tutorial = Tutorial(scene)
    target = tutorial.target(first, name="first")
    step = tutorial.step("Explain")
    tutorial.step("Plain")
    return scene, first, second, tutorial, target, step


def test_callout_wraps_paragraphs_long_words_and_attaches(lesson):
    _, shape, _, _, target, step = lesson
    text = "A wrapped explanation with averylongwordindeed.\n\nNext paragraph."
    callout = step.explain(target, text, max_width=140, gap=200)
    lines = wrap_text(text, callout.font_scale, callout.max_width)
    assert len(lines) > 4 and "" in lines
    assert "".join(lines).replace(" ", "") == text.replace(" ", "").replace("\n", "")
    assert all(Text(text=line, font_scale=callout.font_scale).get_bounds().width <= 140 for line in lines)
    first, art = label_artwork(callout, shape, 900, 600)
    assert first.panel.width <= 140 + 2 * callout.padding
    shape.transform = Transform(translation_x=25, translation_y=10)
    moved, _ = label_artwork(callout, shape, 900, 600)
    assert moved.panel.x == first.panel.x + 25
    assert moved.panel.y == first.panel.y + 10
    text_art = [obj for obj in art if isinstance(obj, Text)]
    for obj in text_art:
        bounds = obj.get_bounds()
        assert bounds.left >= first.panel.left
        assert bounds.right <= first.panel.right
        assert bounds.top >= first.panel.top
        assert bounds.bottom <= first.panel.bottom


def test_attention_pixels_independence_and_source_safety(lesson):
    scene, _, _, tutorial, target, step = lesson
    step.highlight(target).dim_others(target, opacity=0.2)
    step.explain(target, "Focus on this circle. Its neighbor is dimmed.", gap=220)
    state = deepcopy(scene.to_dict())
    count = scene.history.undo_count
    plain = tutorial.render_step(1).to_numpy()
    focused = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(focused[280, 180], plain[280, 180])
    assert np.all(focused[290, 320] > plain[290, 320])  # Below the leader line.
    assert not np.array_equal(focused[242, 180], plain[242, 180])  # Highlight border.
    np.testing.assert_array_equal(tutorial.render_step(1).to_numpy(), plain)
    np.testing.assert_array_equal(tutorial.render_step(0).to_numpy(), focused)
    assert scene.to_dict() == state and scene.history.undo_count == count


def test_nested_dimming_once_and_focus_group_subtree():
    scene = Scene(800, 600)
    selected, sibling, unrelated_child = [Circle(center=Point(x, 200), radius=20) for x in (100, 200, 400)]
    selected.opacity, sibling.opacity, unrelated_child.opacity = 0.7, 0.6, 0.5
    focused_branch = Group(children=[selected, sibling], opacity=0.8,
                           transform=Transform(translation_x=15, rotation=10))
    unrelated = Group(children=[unrelated_child], opacity=0.9)
    parent = Group(children=[focused_branch, unrelated], opacity=0.75)
    scene.add(parent)
    tutorial = Tutorial(scene)
    target = tutorial.target(selected)
    step = tutorial.step("Child").dim_others(target, opacity=0.2)
    working = copy_scene(scene)
    apply_attention(working, step)
    assert working.get(parent.id).opacity == 0.75
    assert working.get(focused_branch.id).opacity == 0.8
    assert working.get(selected.id).opacity == 0.7
    assert working.get(sibling.id).opacity == pytest.approx(0.12)
    assert working.get(unrelated.id).opacity == pytest.approx(0.18)
    assert working.get(unrelated_child.id).opacity == 0.5  # Not multiplied twice.
    whole = tutorial.target(focused_branch)
    step.dim_others(whole, opacity=0.2)
    working = copy_scene(scene)
    apply_attention(working, step)
    assert working.get(sibling.id).opacity == 0.6
    assert working.get(unrelated.id).opacity == pytest.approx(0.18)


@pytest.mark.parametrize("hidden", ["object", "ancestor", "layer", "opacity", "layer_opacity"])
def test_hidden_attention_rejected_without_changes(hidden):
    scene = Scene(400, 300)
    shape = Circle(center=Point(150, 150), radius=20)
    group = Group(children=[shape])
    scene.add(group)
    if hidden == "object":
        shape.visible = False
    elif hidden == "ancestor":
        group.visible = False
    elif hidden == "layer":
        scene.layers[0].visible = False
    elif hidden == "opacity":
        group.opacity = 0
    else:
        scene.layers[0].opacity = 0
    tutorial = Tutorial(scene)
    target = tutorial.target(shape)
    tutorial.step("Hidden").highlight(target)
    before = deepcopy(scene.to_dict())
    with pytest.raises(ValidationError, match="hidden target"):
        tutorial.render_step(0)
    assert scene.to_dict() == before


def test_theme_defaults_and_explicit_overrides(lesson):
    scene, shape, _, _, _, _ = lesson
    theme = Theme(font_scale=0.9, padding=18, gap=50, panel_color=(250, 230, 200),
                  highlight_color=(200, 0, 50), dim_opacity=0.4)
    tutorial = Tutorial(scene, theme=theme)
    target = tutorial.target(shape)
    label = target.label("Themed")
    assert (label.font_scale, label.padding, label.gap) == (0.9, 18, 50)
    explicit = target.label("Explicit", font_scale=0.5, padding=0, gap=0)
    assert (explicit.font_scale, explicit.padding, explicit.gap) == (0.5, 0, 0)
    step = tutorial.step("Theme").show(label).highlight(target).dim_others(target)
    assert step.highlights[0].color == (200, 0, 50)
    layout, _ = label_artwork(label, shape, 900, 600, theme)
    image = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(image[int(layout.panel.top + 5), int(layout.panel.left + 5)], [200, 230, 250])


@pytest.mark.parametrize("kwargs", [{"dim_opacity": 2}, {"font_scale": 0}, {"line_spacing": 0.5},
                                    {"text_color": (256, 0, 0)}, {"gap": float("nan")}, {"highlight_width": 0}])
def test_invalid_theme(kwargs):
    with pytest.raises(ValidationError):
        Theme(**kwargs)


def test_foreign_targets_and_invalid_attention_are_atomic(lesson):
    scene, shape, _, tutorial, target, step = lesson
    foreign = Tutorial(scene).target(shape)
    for action in (lambda: step.explain(foreign, "No"), lambda: step.highlight(foreign),
                   lambda: step.dim_others(target, foreign), lambda: step.highlight(target, width=0),
                   lambda: step.dim_others(target, opacity=2), lambda: step.dim_others(),
                   lambda: step.explain(target, "No", max_width=0)):
        with pytest.raises(ValidationError):
            action()
    assert not step.callouts and not step.highlights and not step._focus
    step.highlight(target).highlight(target, padding=12)
    assert len(step.highlights) == 1 and step.highlights[0].padding == 12
    callout = step.explain(target, "Step only")
    with pytest.raises(ValidationError):
        tutorial.steps[1].show(callout)


def test_unrenderable_callout_width_has_clear_error(lesson):
    scene, _, _, tutorial, target, step = lesson
    step.explain(target, "Text", max_width=0.01)
    before = deepcopy(scene.to_dict())
    with pytest.raises(ValidationError, match="too small"):
        tutorial.render_step(0)
    assert scene.to_dict() == before


def test_export_order_collision_preflight_and_overwrite(lesson, tmp_path):
    _, _, _, tutorial, target, step = lesson
    step.highlight(target)
    paths = tutorial.export_steps(tmp_path)
    assert [p.name for p in paths] == ["step-001.png", "step-002.png"]
    for i, path in enumerate(paths):
        np.testing.assert_array_equal(cv2.imread(str(path)), tutorial.render_step(i).to_numpy())
    first = paths[0].read_bytes()
    with pytest.raises(FileExistsError):
        tutorial.export_steps(tmp_path)
    assert paths[0].read_bytes() == first
    tutorial.export_steps(tmp_path, overwrite=True)
    assert paths[0].read_bytes() == first
    paths[0].unlink()
    with pytest.raises(FileExistsError):
        tutorial.export_steps(tmp_path)
    assert not paths[0].exists()  # Later collision discovered before any output.


def test_export_failure_reports_partial_progress(lesson, tmp_path, monkeypatch):
    _, _, _, tutorial, _, _ = lesson
    original = tutorial.render_step

    def render(index, **kwargs):
        if index == 1:
            raise RuntimeError("second step failed")
        return original(index, **kwargs)

    monkeypatch.setattr(tutorial, "render_step", render)
    with pytest.raises(ExportError) as caught:
        tutorial.export_steps(tmp_path)
    error = caught.value
    assert error.step_index == 1
    assert error.completed_paths == (tmp_path / "step-001.png",)
    assert isinstance(error.__cause__, RuntimeError)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["step-001.png"]


def test_export_race_does_not_overwrite(lesson, tmp_path, monkeypatch):
    _, _, _, tutorial, _, _ = lesson
    original = tutorial.render_step
    destination = tmp_path / "step-001.png"

    def render(index, **kwargs):
        destination.write_bytes(b"another writer")
        return original(index, **kwargs)

    monkeypatch.setattr(tutorial, "render_step", render)
    with pytest.raises(ExportError) as caught:
        tutorial.export_steps(tmp_path)
    assert isinstance(caught.value.__cause__, FileExistsError)
    assert destination.read_bytes() == b"another writer"
    assert not list(tmp_path.glob(".tutordraw-*"))


def test_export_write_failure_preserves_existing_file(lesson, tmp_path, monkeypatch):
    import tutordraw.export as exporter
    _, _, _, tutorial, _, _ = lesson
    destination = tmp_path / "step-001.png"
    destination.write_bytes(b"old file")

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(exporter.os, "replace", fail)
    with pytest.raises(ExportError):
        tutorial.export_steps(tmp_path, overwrite=True)
    assert destination.read_bytes() == b"old file"
    assert not list(tmp_path.glob(".tutordraw-*"))


def test_export_rejects_empty_and_invalid_options(tmp_path):
    tutorial = Tutorial(Scene(100, 100))
    with pytest.raises(ValidationError):
        tutorial.export_steps(tmp_path)
    tutorial.step("One")
    with pytest.raises(ValidationError):
        tutorial.export_steps(tmp_path, overwrite=1)
    with pytest.raises(ValidationError):
        tutorial.export_steps(tmp_path, alpha="yes")


def test_nested_focus_preserves_pixels_and_supports_multiple_targets():
    scene = Scene(600, 300, background=Color.white())
    objects = [Circle(center=Point(x, 150), radius=25, fill=FillStyle(color=Color(20, 100, 180)))
               for x in (100, 250, 400)]
    subgroup = Group(children=objects[:2], opacity=0.8)
    scene.add(Group(children=[subgroup, objects[2]], opacity=0.75))
    tutorial = Tutorial(scene)
    targets = [tutorial.target(obj) for obj in objects]
    focused = tutorial.step("Multiple").dim_others(targets[0], targets[2], opacity=0.2)
    baseline = OpenCVRenderer().render(scene).to_numpy()
    rendered = tutorial.render_step(0).to_numpy()
    for x in (100, 400):
        np.testing.assert_array_equal(rendered[150, x], baseline[150, x])
    assert np.all(rendered[150, 250] > baseline[150, 250])
    focused.dim_others(targets[1], opacity=0.2)  # Replaces, rather than accumulates.
    rendered = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(rendered[150, 250], baseline[150, 250])
    assert np.all(rendered[150, 100] > baseline[150, 100])


def test_export_failed_exclusive_write_removes_partial_file(lesson, tmp_path, monkeypatch):
    import tutordraw.export as exporter
    tutorial = lesson[3]

    def fail(source, destination):
        destination.write(b"partial png")
        raise OSError("disk full")

    monkeypatch.setattr(exporter.shutil, "copyfileobj", fail)
    with pytest.raises(ExportError) as caught:
        tutorial.export_steps(tmp_path)
    assert caught.value.completed_paths == ()
    assert not list(tmp_path.iterdir())

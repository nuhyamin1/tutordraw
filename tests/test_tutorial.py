from copy import deepcopy

import cv2
import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Group, OpenCVRenderer, Point, Scene, Transform

from tutordraw import LayoutWarning, SceneCopyError, Theme, Tutorial, ValidationError
from tutordraw.adapters.drawcv import copy_scene
from tutordraw.layout import label_artwork


@pytest.fixture
def lesson():
    scene = Scene(640, 360, background=Color.white())
    shape = Circle(center=Point(170, 180), radius=35,
                   fill=FillStyle(color=Color(60, 120, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="circle")
    label = target.label("Circle")
    tutorial.step("Labeled").show(label)
    tutorial.step("Plain")
    return scene, shape, tutorial, target, label


def test_png_and_step_independence(lesson, tmp_path):
    scene, _, tutorial, _, _ = lesson
    source = deepcopy(scene.to_dict())
    history = (scene.history.undo_count, scene.history.redo_count)
    plain = tutorial.render_step(1).to_numpy()
    labeled = tutorial.render_step(0).to_numpy()
    assert not np.array_equal(labeled, plain)
    np.testing.assert_array_equal(plain, OpenCVRenderer().render(scene).to_numpy())
    np.testing.assert_array_equal(labeled, tutorial.render_step(0).to_numpy())
    np.testing.assert_array_equal(plain, tutorial.render_step(1).to_numpy())
    output = tmp_path / "step.png"
    tutorial.render_step(0).save(output)
    np.testing.assert_array_equal(cv2.imread(str(output)), labeled)
    assert scene.to_dict() == source
    assert (scene.history.undo_count, scene.history.redo_count) == history


def test_label_follows_move_in_pixels_and_layout(lesson):
    _, shape, tutorial, _, label = lesson
    before, _ = label_artwork(label, shape, 640, 360)
    image_before = tutorial.render_step(0).to_numpy()
    shape.transform = Transform(translation_x=30, translation_y=20)
    after, _ = label_artwork(label, shape, 640, 360)
    assert after.anchor.x == pytest.approx(before.anchor.x + 30)
    assert after.panel.y == pytest.approx(before.panel.y + 20)
    image_after = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(image_before[80:240, 100:380], image_after[100:260, 130:410])


def test_nested_transformed_target_copy_and_attachment():
    scene = Scene(800, 600)
    child = Circle(center=Point(0, 0), radius=20, fill=FillStyle(color=Color(10, 20, 30)))
    group = Group(children=[child], transform=Transform(
        translation_x=250, translation_y=250, rotation=40, scale_x=2, scale_y=2))
    scene.add(group)
    tutorial = Tutorial(scene)
    label = tutorial.target(child).label("Nested")
    tutorial.step("Nested").show(label)
    copied = copy_scene(scene)
    assert copied.to_dict() == scene.to_dict()
    assert copied.get(child.id) is not child
    assert copied.get(child.id).get_bounds() == child.get_bounds()
    layout, artwork = label_artwork(label, child, 800, 600)
    assert layout.anchor.x == pytest.approx(290)
    assert layout.anchor.y == pytest.approx(250)
    assert artwork[-1].transform.is_identity()
    assert tutorial.render_step(0).to_numpy().shape == (600, 800, 3)


@pytest.mark.parametrize("side", ["left", "right", "top", "bottom", "center"])
def test_anchor_and_leader_on_panel_boundary(lesson, side):
    _, shape, _, target, _ = lesson
    label = target.label("Label", anchor=side)
    layout, _ = label_artwork(label, shape, 640, 360)
    p, box = layout.leader_end, layout.panel
    assert box.left - 1e-8 <= p.x <= box.right + 1e-8
    assert box.top - 1e-8 <= p.y <= box.bottom + 1e-8
    assert min(abs(p.x - box.left), abs(p.x - box.right),
               abs(p.y - box.top), abs(p.y - box.bottom)) < 1e-8


def test_missing_target_and_foreign_objects(lesson):
    scene, shape, tutorial, _, _ = lesson
    with pytest.raises(ValidationError, match="belong"):
        tutorial.target(Circle())
    scene.remove(shape.id)
    with pytest.raises(ValidationError, match="Missing target 'circle'"):
        tutorial.render_step(0)


def test_identity_names_and_label_ownership(lesson):
    scene, shape, tutorial, target, label = lesson
    assert tutorial.target(shape) is target
    with pytest.raises(ValidationError, match="different name"):
        tutorial.target(shape, name="other")
    other = Circle(center=Point(400, 150), radius=10)
    scene.add(other)
    with pytest.raises(ValidationError, match="already in use"):
        tutorial.target(other, name="circle")
    foreign = Tutorial(scene)
    foreign_label = foreign.target(shape).label("Foreign")
    step = tutorial.steps[1]
    with pytest.raises(ValidationError, match="belong"):
        step.show(label, foreign_label)
    assert step.labels == ()  # Failed additions are atomic.
    step.show(label, label)
    assert step.labels == (label,)


@pytest.mark.parametrize("index", [-1, 2, True, "0"])
def test_invalid_step_index(lesson, index):
    with pytest.raises(ValidationError, match="Step index"):
        lesson[2].render_step(index)


@pytest.mark.parametrize("options", [
    {"text": ""}, {"text": "ไทย"}, {"text": "two\nlines"},
    {"anchor": "diagonal"}, {"gap": -1}, {"gap": float("nan")},
    {"offset": (1,)}, {"offset": (0, float("inf"))},
    {"font_scale": 0}, {"padding": -1}, {"leader": 1},
    {"box": 1}, {"box": "no"}, {"box": None},
])
def test_invalid_labels(lesson, options):
    with pytest.raises(ValidationError):
        lesson[3].label(**({"text": "Label"} | options))


def test_box_false_draws_the_text_without_a_panel(lesson):
    """The panel is still measured, so only the rectangle disappears."""
    from drawcv import Rectangle, Text

    _, shape, _, target, _ = lesson
    boxed = target.label("Boxed")
    bare = target.label("Boxed", box=False)
    assert boxed.box is True and bare.box is False

    framed_layout, framed = label_artwork(boxed, shape, 640, 360)
    plain_layout, plain = label_artwork(bare, shape, 640, 360)
    assert sum(isinstance(obj, Rectangle) for obj in framed) == 1
    assert sum(isinstance(obj, Rectangle) for obj in plain) == 0
    # Same text, same leader, same geometry: only the panel is gone.
    assert framed_layout == plain_layout
    assert ([type(obj) for obj in plain]
            == [type(obj) for obj in framed if not isinstance(obj, Rectangle)])
    assert [obj.text for obj in plain if isinstance(obj, Text)] == ["Boxed"]


def test_unboxed_labels_are_still_kept_apart(lesson, monkeypatch):
    """Bare text needs collision avoidance more than a panel does, not less."""
    import tutordraw.tutorial as module
    from tutordraw.collision import overlap_area

    _, _, tutorial, target, _ = lesson
    tutorial.steps[0].show(*(target.label(f"bare {i}", box=False) for i in range(4)))
    seen = []
    real = module.label_artwork

    def record(*args, **kwargs):
        layout, artwork = real(*args, **kwargs)
        seen.append(layout.panel)
        return layout, artwork

    monkeypatch.setattr(module, "label_artwork", record)
    tutorial.render_step(0)
    assert len(seen) == 5  # The fixture's own label plus four bare ones.
    assert all(overlap_area(a, b) == 0
               for i, a in enumerate(seen) for b in seen[i + 1:])


def test_box_survives_the_round_trip_and_defaults_true(lesson):
    _, _, tutorial, target, _ = lesson
    tutorial.steps[0].show(target.label("Bare", box=False))
    tutorial.steps[0].explain(target, "Also bare.", box=False)
    document = tutorial.to_dict()
    assert document["schema_version"] == 7
    restored = Tutorial.from_dict(document)
    assert [label.box for label in restored.labels] == [True, False]
    assert [callout.box for callout in restored.steps[0].callouts] == [False]

    # A v6 document has no box field at all, and loads fully boxed.
    legacy = deepcopy(document)
    legacy["schema_version"] = 6
    for annotation in [*legacy["labels"], *legacy["steps"][0]["callouts"]]:
        del annotation["box"]
    older = Tutorial.from_dict(legacy)
    assert all(label.box for label in older.labels)
    assert all(callout.box for callout in older.steps[0].callouts)


def test_off_canvas_warning(lesson):
    """Without avoidance an authored offset stands, even off the canvas."""
    scene, _, tutorial, target, _ = lesson
    tutorial.theme = Theme(avoid_collisions=False)
    label = target.label("Outside", offset=(1000, 0))
    tutorial.steps[0].show(label)
    before = scene.to_dict()
    with pytest.warns(LayoutWarning, match="Outside"):
        tutorial.render_step(0)
    assert scene.to_dict() == before


def test_render_failure_preserves_scene_and_history(lesson, monkeypatch):
    scene, _, tutorial, _, _ = lesson
    before = deepcopy(scene.to_dict())
    count = scene.history.undo_count

    def fail(*args, **kwargs):
        raise RuntimeError("Injected renderer failure")

    monkeypatch.setattr(OpenCVRenderer, "render", fail)
    with pytest.raises(RuntimeError, match="Injected"):
        tutorial.render_step(0)
    assert scene.to_dict() == before
    assert scene.history.undo_count == count


def test_copy_failure_is_clear_and_preserves_scene(lesson, monkeypatch):
    scene, _, tutorial, _, _ = lesson
    before = deepcopy(scene.to_dict())

    def fail(*args, **kwargs):
        raise RuntimeError("Unsupported asset")

    monkeypatch.setattr(Scene, "from_dict", fail)
    with pytest.raises(SceneCopyError, match="Unsupported asset"):
        tutorial.render_step(0)
    assert scene.to_dict() == before


def test_duplicate_ids_rejected(lesson):
    scene, shape, tutorial, _, _ = lesson
    other = Circle(center=Point(400, 150), radius=10)
    scene.add(other)
    other.id = shape.id  # Simulate a corrupted externally edited scene.
    with pytest.raises(ValidationError, match="Duplicate drawable ID"):
        tutorial.render_step(0)


def test_overlay_name_collision_and_alpha(lesson):
    scene, _, tutorial, _, _ = lesson
    scene.create_layer("__tutordraw__", z_order=10000)
    scene.background = Color(0, 0, 0, 0)
    before = deepcopy(scene.to_dict())
    assert tutorial.render_step(0, alpha=True).to_numpy().shape == (360, 640, 4)
    assert scene.to_dict() == before

"""Automatic collision avoidance: correctness in one frame, stability across many."""

import numpy as np
import pytest
from drawcv import BoundingBox, Circle, Color, FillStyle, Point, Scene

from tutordraw import LayoutWarning, Theme, Tutorial
from tutordraw.collision import Request, candidates, outside_area, overlap_area
from tutordraw.layout import Placement, measure_label


@pytest.fixture
def spy(monkeypatch):
    """Record what the real render path drew, rather than re-deriving it."""
    import tutordraw.tutorial as module

    real = module.label_artwork
    seen: list[tuple] = []

    def record(*args, **kwargs):
        layout, artwork = real(*args, **kwargs)
        placement = args[6] if len(args) > 6 else kwargs.get("placement")
        seen.append((args[0], placement, layout))
        return layout, artwork

    monkeypatch.setattr(module, "label_artwork", record)
    return seen


def panels(seen):
    return [layout.panel for _, _, layout in seen]


def worst_overlap(boxes):
    return max((overlap_area(a, b) for i, a in enumerate(boxes) for b in boxes[i + 1:]),
               default=0.0)


def crowded_lesson(**theme):
    """Two labelled circles close enough that both panels want the same space.

    Stacked vertically and small, so the panels collide with each other while
    neither would cover the other's artwork: this isolates panel-on-panel.
    """
    scene = Scene(900, 600, background=Color.white())
    first = Circle(center=Point(200, 280), radius=12, fill=FillStyle(color=Color(30, 80, 160)))
    second = Circle(center=Point(200, 320), radius=12, fill=FillStyle(color=Color(160, 80, 30)))
    scene.add(first)
    scene.add(second)
    tutorial = Tutorial(scene, theme=Theme(**theme))
    one = tutorial.target(first, name="one")
    two = tutorial.target(second, name="two")
    step = tutorial.step("Both")
    step.show(one.label("box at rest"), two.label("puck on smooth table"))
    return tutorial, one, two, step


def test_colliding_labels_separate_and_the_first_keeps_its_anchor(spy):
    tutorial, *_ = crowded_lesson()
    tutorial.render_step(0)
    assert worst_overlap(panels(spy)) == 0
    # Registration order decides: the first annotation is never displaced.
    assert spy[0][1] == Placement("right", 0.0, 0.0)
    assert spy[1][1] != Placement("right", 0.0, 0.0)


def test_without_avoidance_the_same_labels_still_overlap(spy):
    tutorial, *_ = crowded_lesson(avoid_collisions=False)
    plain = tutorial.render_step(0).to_numpy()
    assert worst_overlap(panels(spy)) > 0
    assert all(placement is None for _, placement, _ in spy)
    resolved = crowded_lesson()[0].render_step(0).to_numpy()
    assert not np.array_equal(plain, resolved)


def test_margin_is_honoured_between_panels(spy):
    tutorial, *_ = crowded_lesson(collision_margin=40)
    tutorial.render_step(0)
    first, second = panels(spy)
    gap = max(first.left - second.right, second.left - first.right,
              first.top - second.bottom, second.top - first.bottom)
    assert gap >= 40


def test_label_pushed_off_canvas_is_pulled_back(spy):
    scene = Scene(640, 360, background=Color.white())
    shape = Circle(center=Point(170, 180), radius=35, fill=FillStyle(color=Color(60, 120, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="circle")
    # An offset far past the right edge; no anchor choice alone can undo it.
    tutorial.step("Outside").show(target.label("Outside", offset=(1000, 0)))
    tutorial.render_step(0)
    panel = panels(spy)[0]
    assert panel.left >= 0 and panel.top >= 0
    assert panel.right <= 640 and panel.bottom <= 360


def test_a_panel_too_big_for_the_canvas_still_warns():
    scene = Scene(200, 200, background=Color.white())
    shape = Circle(center=Point(100, 100), radius=20, fill=FillStyle(color=Color(60, 120, 200)))
    scene.add(shape)
    tutorial = Tutorial(scene)
    target = tutorial.target(shape, name="dot")
    label = target.label("A label far wider than this whole canvas could ever be")
    tutorial.step("Too wide").show(label)
    with pytest.warns(LayoutWarning, match="outside the canvas"):
        tutorial.render_step(0)


def test_many_labels_around_one_small_target_all_fit(spy):
    scene = Scene(900, 600, background=Color.white())
    dot = Circle(center=Point(450, 300), radius=18, fill=FillStyle(color=Color(30, 80, 160)))
    scene.add(dot)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    step = tutorial.step("Crowd")
    for name in ("A fast", "push", "small ball B", "small ball C", "friction", "normal force"):
        step.show(target.label(name))
    tutorial.render_step(0)

    boxes = panels(spy)
    assert len(boxes) == 6
    assert worst_overlap(boxes) == 0
    for box in boxes:
        assert box.left >= 0 and box.top >= 0 and box.right <= 900 and box.bottom <= 600
    # Sides are exhausted before a label slides, so they fan out rather than stack.
    assert len({placement.anchor for _, placement, _ in spy}) == 4


def test_resolution_is_deterministic_and_order_independent(spy):
    tutorial, *_ = crowded_lesson()
    tutorial.step("Other")
    first = tutorial.render_step(0).to_numpy()
    tutorial.render_step(1)
    again = tutorial.render_step(0).to_numpy()
    np.testing.assert_array_equal(first, again)
    placements = [placement for _, placement, _ in spy]
    assert placements[:2] == placements[-2:]


def test_labels_avoid_covering_registered_artwork(spy):
    """A neighbour's artwork costs a placement, even when no panel is in the way."""
    scene = Scene(600, 400, background=Color.white())
    dot = Circle(center=Point(200, 200), radius=20, fill=FillStyle(color=Color(30, 80, 160)))
    # A wide bar sitting exactly where a right-anchored panel would land.
    bar = Circle(center=Point(330, 200), radius=60, fill=FillStyle(color=Color(200, 120, 40)))
    scene.add(dot)
    scene.add(bar)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    tutorial.target(bar, name="bar")
    tutorial.step("Clear").show(target.label("label"))
    tutorial.render_step(0)
    assert overlap_area(panels(spy)[0], BoundingBox(270, 140, 120, 120)) == 0


def test_a_centre_anchored_label_may_sit_on_its_own_target(spy):
    scene = Scene(600, 400, background=Color.white())
    dot = Circle(center=Point(300, 200), radius=70, fill=FillStyle(color=Color(30, 80, 160)))
    scene.add(dot)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    tutorial.step("On it").show(target.label("inside", anchor="center", gap=0))
    tutorial.render_step(0)
    assert spy[0][1] == Placement("center", 0.0, 0.0)
    assert overlap_area(panels(spy)[0], dot.get_bounds()) > 0


def test_a_highlight_box_pushes_a_label_off_it(spy):
    scene = Scene(700, 400, background=Color.white())
    dot = Circle(center=Point(300, 200), radius=40, fill=FillStyle(color=Color(30, 80, 160)))
    scene.add(dot)
    tutorial = Tutorial(scene)
    target = tutorial.target(dot, name="dot")
    step = tutorial.step("Emphasis")
    step.highlight(target, padding=70)
    step.show(target.label("note", gap=0))
    tutorial.render_step(0)
    highlight = BoundingBox(190, 90, 220, 220)
    assert overlap_area(panels(spy)[0], highlight) == 0


# --- stability across frames -------------------------------------------------


def moving_lesson(**theme):
    """An animated step that drags two labelled circles past each other."""
    scene = Scene(900, 600, background=Color.white())
    left = Circle(center=Point(200, 300), radius=30, fill=FillStyle(color=Color(30, 80, 160)))
    right = Circle(center=Point(320, 340), radius=30, fill=FillStyle(color=Color(160, 80, 30)))
    scene.add(left)
    scene.add(right)
    tutorial = Tutorial(scene, theme=Theme(**theme))
    one = tutorial.target(left, name="one")
    two = tutorial.target(right, name="two")
    tutorial.step("Rest", duration=2)
    step = tutorial.step("Slide", duration=2).animate()
    step.restyle(one, move=(260, 0))
    step.show(one.label("A fast (v = 6)"), two.label("small ball B"))
    return tutorial, step


def test_placement_never_changes_across_the_frames_of_an_animated_step(spy):
    tutorial, _ = moving_lesson()
    start = tutorial.steps[0].duration
    frames = [start + i * (2 / 24) for i in range(25)]
    for moment in frames:
        tutorial.render_at_time(moment)

    per_label: dict[str, list] = {}
    for label, placement, layout in spy:
        per_label.setdefault(label.id, []).append((placement, layout.panel))
    assert len(per_label) == 2
    for history in per_label.values():
        anchors = {placement.anchor for placement, _ in history}
        nudges = {(placement.dx, placement.dy) for placement, _ in history}
        # One decision for the whole step: no side swap, no per-frame drift.
        assert len(anchors) == 1 and len(nudges) == 1

    # The moving label still tracks its target, monotonically and by the full move.
    moving = list(per_label.values())[0]
    centres = [panel.center.x for _, panel in moving]
    assert all(b >= a for a, b in zip(centres, centres[1:]))
    assert centres[-1] - centres[0] == pytest.approx(260, abs=1)


def test_panels_stay_separated_in_every_frame(spy):
    tutorial, _ = moving_lesson()
    start = tutorial.steps[0].duration
    for i in range(25):
        spy.clear()
        tutorial.render_at_time(start + i * (2 / 24))
        assert worst_overlap(panels(spy)) == 0


def crossing_lesson():
    """One ball slides straight past another, dragging its label through it."""
    scene = Scene(900, 500, background=Color.white())
    left = Circle(center=Point(180, 250), radius=30, fill=FillStyle(color=Color(200, 70, 60)))
    right = Circle(center=Point(320, 260), radius=30, fill=FillStyle(color=Color(60, 140, 90)))
    scene.add(left)
    scene.add(right)
    tutorial = Tutorial(scene)
    one, two = tutorial.target(left, name="one"), tutorial.target(right, name="two")
    tutorial.step("Rest", duration=1)
    step = tutorial.step("Slide", duration=2).animate()
    step.restyle(one, move=(430, 0))
    step.show(one.label("A fast (v = 6)"), two.label("small ball B"))
    return tutorial


def test_a_label_dragged_past_another_never_overlaps_it(spy):
    """End-state resolution alone is not enough; the swept path is what counts."""
    tutorial = crossing_lesson()
    for i in range(61):
        spy.clear()
        tutorial.render_at_time(1 + i * (2 / 60))
        assert worst_overlap(panels(spy)) == 0


def test_a_hard_cut_is_not_penalised_for_motion_it_never_shows(spy):
    """Without animate() there is no middle, so only the end state constrains."""
    tutorial = crossing_lesson()
    tutorial.render_step(1)
    animated = [placement for _, placement, _ in spy]

    spy.clear()
    cut = crossing_lesson()
    cut.steps[1].hard_cut()
    cut.render_step(1)
    assert [placement for _, placement, _ in spy] != animated


@pytest.mark.parametrize("build", [lambda: moving_lesson()[0], crossing_lesson])
def test_the_last_frame_matches_the_static_render(build):
    """render_step plans from the same two ends as every animated frame does."""
    tutorial = build()
    final = tutorial.render_at_time(tutorial.steps[0].duration + 2).to_numpy()
    np.testing.assert_array_equal(final, tutorial.render_step(1).to_numpy())


def test_restyle_move_resolves_exactly_like_moving_the_source(spy):
    """The RESTYLE.md pixel-identity promise survives collision avoidance."""
    tutorial, one, *_ = crowded_lesson()
    moved = tutorial.steps[0].restyle(one, move=(45, 25))
    restyled = tutorial.render_step(0).to_numpy()
    by_restyle = [placement for _, placement, _ in spy]

    spy.clear()
    direct, other, *_ = crowded_lesson()
    circle = other.drawable
    circle.transform.translation_x += 45
    circle.transform.translation_y += 25
    np.testing.assert_array_equal(direct.render_step(0).to_numpy(), restyled)
    assert [placement for _, placement, _ in spy] == by_restyle
    assert moved is tutorial.steps[0]


def test_a_delayed_label_holds_its_slot_from_the_first_frame(spy):
    """Nothing already on screen moves when a delayed annotation appears."""
    tutorial, one, two, step = crowded_lesson()
    late = tutorial.get_target("two").label("arrives late")
    step.show(late, at=1.5)

    spy.clear()
    tutorial.render_at_time(0.5)
    early = {label.id: placement for label, placement, _ in spy}
    assert late.id not in early  # Not drawn yet.

    spy.clear()
    tutorial.render_at_time(2.0)
    after = {label.id: placement for label, placement, _ in spy}
    assert late.id in after
    assert all(after[key] == value for key, value in early.items())
    assert worst_overlap(panels(spy)) == 0


# --- unit level --------------------------------------------------------------


def test_geometry_helpers():
    box = BoundingBox(10, 10, 20, 20)
    assert overlap_area(box, BoundingBox(20, 20, 20, 20)) == 100
    assert overlap_area(box, BoundingBox(40, 40, 10, 10)) == 0
    assert overlap_area(box, BoundingBox(40, 10, 10, 20)) == 0
    # A margin makes near misses count as contact.
    assert overlap_area(box, BoundingBox(35, 10, 10, 20), margin=10) == 100
    assert outside_area(box, 100, 100) == 0
    assert outside_area(BoundingBox(-10, 10, 20, 20), 100, 100) == 200


def test_the_first_candidate_is_exactly_what_the_author_wrote():
    scene = Scene(400, 300, background=Color.white())
    dot = Circle(center=Point(200, 150), radius=10)
    scene.add(dot)
    tutorial = Tutorial(scene)
    label = tutorial.target(dot, name="dot").label("hi", anchor="top", offset=(4, -3))
    request = Request("k", label.text, "id", label.anchor, label.gap, label.offset,
                      {}, measure_label(label), False)
    ranked = list(candidates(request, 6.0))
    assert ranked[0] == Placement("top", 0.0, 0.0)
    assert {p.anchor for p in ranked[:4]} == {"top", "left", "right", "bottom"}
    assert all(isinstance(p, Placement) for p in ranked)


def test_theme_fields_round_trip():
    scene = Scene(300, 200, background=Color.white())
    dot = Circle(center=Point(150, 100), radius=10)
    scene.add(dot)
    tutorial = Tutorial(scene, theme=Theme(avoid_collisions=False, collision_margin=12))
    tutorial.step("One")
    restored = Tutorial.from_dict(tutorial.to_dict())
    assert restored.theme.avoid_collisions is False
    assert restored.theme.collision_margin == 12


@pytest.mark.parametrize("options", [
    {"avoid_collisions": "yes"}, {"avoid_collisions": 1},
    {"collision_margin": -1}, {"collision_margin": float("nan")},
])
def test_invalid_theme_options(options):
    with pytest.raises(Exception):
        Theme(**options)

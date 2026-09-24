"""Flowchart, timeline, cycle, force diagram and cross-section kits."""

import math

import numpy as np
import pytest
from drawcv import Arrow, Circle, Color, Group, Path, Polygon, Rectangle, Scene, Text

from tutordraw import Tutorial, ValidationError
from tutordraw.kits import CrossSection, Cycle, Flowchart, ForceDiagram, Timeline

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson(width=800, height=600):
    return Tutorial(Scene(width, height, background=Color.white()))


def texts(drawable):
    found = []

    def walk(obj):
        if isinstance(obj, Text):
            found.append(obj.text)
        for child in getattr(obj, "children", []):
            walk(child)

    walk(drawable)
    return found


def route(link):
    """The flattened points of a link's line."""
    path = next(c for c in link.drawable.children if isinstance(c, Path))
    return [(round(p.x, 3), round(p.y, 3)) for p in path.flatten_world()[0]]


def roundtrip(tutorial, tmp_path):
    tutorial.step("Check")
    loaded = Tutorial.load_json(tutorial.save_json(tmp_path / "kit.tutordraw.json"))
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    return loaded


# --- flowchart ----------------------------------------------------------------


@pytest.fixture
def chart():
    tutorial = lesson()
    flow = Flowchart(tutorial, origin=(200, 60), cell=(220, 110), node_size=(170, 60))
    flow.node("start", "Start", at=(0, 0), shape="terminal")
    flow.node("raining", "Is it raining?", at=(0, 1), shape="decision")
    flow.node("umbrella", "Take an umbrella", at=(1, 2))
    flow.node("walk", "Walk to school", at=(0, 3))
    return flow


def test_nodes_sit_on_the_grid_with_their_text_inside(chart):
    tutorial = chart.tutorial
    names = {t.name for t in tutorial.targets}
    assert {"start", "start_shape", "raining", "raining_shape", "umbrella", "walk"} <= names
    box = tutorial.get_target("umbrella").drawable.get_bounds()
    assert (box.center.x, box.center.y) == pytest.approx((420, 280))
    assert (box.width, box.height) == pytest.approx((170, 60), abs=3)
    assert isinstance(tutorial.get_target("raining_shape").drawable, Polygon)
    for name in ("start", "raining", "umbrella", "walk"):
        node = tutorial.get_target(name).drawable
        inner = [c.get_bounds() for c in node.children if isinstance(c, Text)]
        outline = tutorial.get_target(f"{name}_shape").drawable.get_bounds()
        assert inner and all(outline.left < t.left and t.right < outline.right for t in inner)


def test_long_text_wraps_inside_a_node():
    flow = Flowchart(lesson(), origin=(200, 100))
    node = flow.node("long", "Measure the length of the pendulum string", at=(0, 0))
    assert len(texts(node.drawable)) >= 2


def test_links_go_straight_turn_once_or_loop_round(chart):
    down = chart.link("start", "raining")
    assert route(down) == [(200, 90), (200, 140)]  # pill bottom to diamond top
    branch = chart.link("raining", "umbrella", "yes")
    assert route(branch) == [(285, 170), (420, 170), (420, 250)]  # diamond's right vertex
    assert "yes" in texts(branch.drawable)
    loop = chart.link("walk", "raining", "again")
    points = route(loop)
    assert points[0] == (115, 390) and points[-1] == (115, 170)
    assert min(x for x, _ in points) < 115  # round the left
    assert down.name == "arrow_from_start_to_raining" and chart.link("raining", "walk", name="no").name == "no"


def test_every_link_ends_in_an_arrowhead_at_the_destination(chart):
    link = chart.link("umbrella", "walk")
    head = next(c for c in link.drawable.children if isinstance(c, Polygon))
    tip = head.vertices[0]
    assert (tip.x, tip.y) == pytest.approx(route(link)[-1])


@pytest.mark.parametrize("call", [
    lambda f: f.node("start", "Again", at=(3, 3)),
    lambda f: f.node("new", "Shape", at=(3, 3), shape="circle"),
    lambda f: f.node("new", "", at=(3, 3)),
    lambda f: f.node("new", "Place", at=(3,)),
    lambda f: f.link("start", "nowhere"),
    lambda f: f.link("start", "start"),
])
def test_bad_flowchart_calls_are_refused(chart, call):
    with pytest.raises(ValidationError):
        call(chart)


def test_a_missing_node_error_lists_the_nodes(chart):
    with pytest.raises(ValidationError, match="raining, start, umbrella, walk"):
        chart.link("start", "finish")


def test_flowchart_survives_save_and_load_and_can_be_extended(chart, tmp_path):
    chart.link("start", "raining")
    loaded = roundtrip(chart.tutorial, tmp_path)
    again = Flowchart.find(loaded)
    again.node("home", "Home", at=(1, 3), shape="terminal")
    assert route(again.link("walk", "home")) == [(285, 390), (335, 390)]
    with pytest.raises(ValidationError, match="No flowchart named 'other'"):
        Flowchart.find(loaded, "other")


# --- timeline -----------------------------------------------------------------


@pytest.fixture
def timeline():
    return Timeline(lesson(900, 400), start=(60, 200), length=800, span=(1900, 2000))


def test_dates_map_along_the_line_with_round_ticks(timeline):
    assert timeline.to_scene(1950).x == pytest.approx(460)
    assert timeline.step == 10
    tick_texts = [t for t in texts(timeline.group) if t.isdigit()]
    assert tick_texts[0] == "1900" and tick_texts[-1] == "2000" and len(tick_texts) == 11
    assert timeline.line.name == "timeline_line"


def test_events_alternate_and_climb_clear_of_each_other(timeline):
    first = timeline.event(1903, "First powered flight")
    second = timeline.event(1914, "War begins")
    third = timeline.event(1908, "Model T")  # above again, overlapping the first
    assert first.drawable.get_bounds().bottom <= 200 + 8  # only its dot reaches below
    assert second.drawable.get_bounds().top >= 200 - 8
    a, c = first.drawable.get_bounds(), third.drawable.get_bounds()
    text_a = [x.get_bounds() for x in first.drawable.children if isinstance(x, Text)]
    text_c = [x.get_bounds() for x in third.drawable.children if isinstance(x, Text)]
    overlap = any(p.left < q.right and q.left < p.right and p.top < q.bottom and q.top < p.bottom
                  for p in text_a for q in text_c)
    assert not overlap and c.top < a.top  # it stepped up a level
    assert [t.name for t in (first, second, third)] == [
        "timeline_event1", "timeline_event2", "timeline_event3"]


def test_periods_band_the_line_and_stack_by_row(timeline):
    war = timeline.period(1914, 1918, "WWI")
    later = timeline.period(1939, 1945, "WWII", row=1)
    band = next(c for c in war.drawable.children if isinstance(c, Rectangle))
    assert band.position.x == pytest.approx(timeline.to_scene(1914).x)
    assert band.width == pytest.approx(timeline.to_scene(1918).x - timeline.to_scene(1914).x)
    assert later.drawable.get_bounds().bottom < war.drawable.get_bounds().top


@pytest.mark.parametrize("call", [
    lambda t: t.event(1850, "Too early"), lambda t: t.event(1950, "x", side="left"),
    lambda t: t.period(1950, 1940, "Backwards"), lambda t: t.period(1940, 1950, "Row", row=9),
    lambda t: t.event(1950, ""),
])
def test_bad_timeline_calls_are_refused(timeline, call):
    with pytest.raises(ValidationError):
        call(timeline)


def test_timeline_survives_save_and_load_and_keeps_avoiding(timeline, tmp_path):
    placed = timeline.event(1903, "First powered flight")
    loaded = roundtrip(timeline.tutorial, tmp_path)
    again = Timeline.find(loaded)
    later = again.event(1906, "Close by", side="above")
    assert later.drawable.get_bounds().top < placed.drawable.get_bounds().top
    assert later.name == "timeline_event3"  # counted past saved parts, no clash


# --- cycle --------------------------------------------------------------------


@pytest.fixture
def water():
    return Cycle(lesson(700, 600), center=(350, 300), radius=200,
                 stages=["Evaporation", "Condensation", "Precipitation", "Collection"])


def test_stages_go_clockwise_from_the_top_named_from_their_text(water):
    assert [t.name for t in water.stages] == ["evaporation", "condensation", "precipitation", "collection"]
    centres = [t.drawable.get_bounds().center for t in water.stages]
    assert [(round(c.x), round(c.y)) for c in centres] == [(350, 100), (550, 300), (350, 500), (150, 300)]
    assert water.stage(2) is water.stages[1] and water.stage("collection") is water.stages[3]
    with pytest.raises(ValidationError, match="evaporation, condensation"):
        water.stage("runoff")


def test_arrows_join_each_stage_to_the_next_without_touching_them(water):
    assert [a.name for a in water.arrows] == [
        "arrow_from_evaporation_to_condensation", "arrow_from_condensation_to_precipitation",
        "arrow_from_precipitation_to_collection", "arrow_from_collection_to_evaporation"]
    for arrow in water.arrows:
        path = next(c for c in arrow.drawable.children if isinstance(c, Path))
        for p in path.flatten_world()[0]:
            for stage in water.stages:
                box = stage.drawable.get_bounds()
                assert not (box.left < p.x < box.right and box.top < p.y < box.bottom)
    # The last arrow closes the loop: it ends by the first stage.
    head = next(c for c in water.arrows[-1].drawable.children if isinstance(c, Polygon)).vertices[0]
    assert head.y < 200 and head.x < 350


def test_named_stages_anticlockwise_and_size_checks():
    cycle = Cycle(lesson(), center=(400, 300), radius=180, clockwise=False,
                  stages=[("g1", "Growth 1"), ("s", "Synthesis"), ("g2", "Growth 2"), ("m", "Mitosis")])
    assert cycle.stage("s").drawable.get_bounds().center.x < 400  # second stage on the left
    with pytest.raises(ValidationError, match="too small .* try radius"):
        Cycle(lesson(), center=(400, 300), radius=60, stages=["A", "B", "C", "D", "E", "F"])
    with pytest.raises(ValidationError, match="different"):
        Cycle(lesson(), center=(400, 300), radius=200, stages=["Rain", "rain!"])
    with pytest.raises(ValidationError):
        Cycle(lesson(), center=(400, 300), radius=200, stages=["Only one"])


def test_cycle_survives_save_and_load(water, tmp_path):
    loaded = roundtrip(water.tutorial, tmp_path)
    again = Cycle.find(loaded)
    assert [t.name for t in again.stages][0] == "evaporation" and len(again.arrows) == 4


# --- force diagram ------------------------------------------------------------


@pytest.fixture
def block():
    return ForceDiagram(lesson(700, 560), center=(350, 280), size=80, scale=4, text="5 kg")


def arrow_of(target):
    return next(c for c in target.drawable.children if isinstance(c, Arrow))


def test_forces_leave_the_edge_at_a_length_to_scale(block):
    weight = arrow_of(block.force("weight", "down", 49, "weight 49 N"))
    assert (weight.start.x, weight.start.y) == pytest.approx((350, 320))
    assert (weight.end.x, weight.end.y) == pytest.approx((350, 320 + 49 * 4))
    push = arrow_of(block.force("push", 30, 40))
    length = math.hypot(push.end.x - push.start.x, push.end.y - push.start.y)
    assert length == pytest.approx(160)
    assert push.end.y < push.start.y and push.end.x > push.start.x  # 30 degrees is up and right
    assert push.start.x == pytest.approx(390)  # leaves through the right face


def test_net_force_is_the_vector_sum(block):
    block.force("weight", "down", 49)
    block.force("normal", "up", 49)
    block.force("push", "right", 40)
    block.force("friction", "left", 15)
    assert block.resultant == pytest.approx((25, 0), abs=1e-9)
    net = arrow_of(block.net("net 25 N"))
    assert net.end.x - net.start.x == pytest.approx(100) and net.end.y == pytest.approx(280)


def test_balanced_forces_have_no_net_arrow(block):
    block.force("weight", "down", 20)
    block.force("normal", "up", 20)
    with pytest.raises(ValidationError, match="balance"):
        block.net()


def test_components_split_a_slanted_force(block):
    pull = block.force("pull", 60, 30)
    parts = block.components(pull)
    assert parts.name == "pull_components"
    arrows = [c for g in parts.drawable.children for c in g.children if isinstance(c, Arrow)]
    assert len(arrows) == 2
    across, up = arrows
    assert across.end.x - across.start.x == pytest.approx(30 * math.cos(math.radians(60)) * 4)
    assert up.start.y - up.end.y == pytest.approx(30 * math.sin(math.radians(60)) * 4)


@pytest.mark.parametrize("call", [
    lambda b: b.force("tiny", "up", 1), lambda b: b.force("odd", "sideways", 10),
    lambda b: b.force("body", "up", 10) and b.force("body", "up", 10),
    lambda b: b.components("missing"),
])
def test_bad_forces_are_refused(block, call):
    with pytest.raises(ValidationError):
        call(block)


def test_force_diagram_survives_save_and_load(block, tmp_path):
    block.force("weight", "down", 30)
    loaded = roundtrip(block.tutorial, tmp_path)
    again = ForceDiagram.find(loaded)
    again.force("lift", "up", 50)
    assert again.resultant == pytest.approx((0, 20), abs=1e-9)
    assert again.body.name == "body"


# --- cross-section ------------------------------------------------------------


def test_bands_stack_by_thickness_and_label_their_own_edge():
    tutorial = lesson(820, 420)
    soil = CrossSection(tutorial, box=(60, 40, 420, 300),
                        layers=[("topsoil", "Topsoil"), ("subsoil", "Subsoil", 2), ("bedrock", "Bedrock")])
    heights = [t.drawable.height for t in soil.layers]
    assert heights == pytest.approx([75, 150, 75])
    labels = soil.labels()
    assert [label.target for label in labels] == list(soil.layers)
    step = tutorial.step("Soil")
    step.show(*labels)
    assert 'The topsoil is labelled "Topsoil"' in tutorial.describe()
    assert soil.layer("subsoil") is soil.layers[1]


def test_rings_nest_and_label_inside_each_ring(tmp_path):
    tutorial = lesson(820, 520)
    earth = CrossSection(tutorial, box=(60, 40, 440, 440), shape="rings",
                         layers=[("crust", "Crust", 1), ("mantle", "Mantle", 4), ("core", "Core", 5)])
    radii = [t.drawable.radius for t in earth.layers]
    assert radii == pytest.approx([220, 198, 110])
    labels = earth.labels()
    for label, (inner, outer) in zip(labels, [(198, 220), (110, 198), (0, 110)]):
        point = label.target.drawable.get_bounds().center
        distance = math.hypot(point.x - 280, point.y - 260)
        assert inner < distance < outer
    tutorial.step("Earth").show(*labels)
    assert 'The mantle layer is labelled "Mantle"' in tutorial.describe()
    panels = [tutorial.render_step(0)]  # renders without error
    assert panels
    loaded = roundtrip(tutorial, tmp_path)
    again = CrossSection.find(loaded)
    assert [t.name for t in again.layers] == ["crust", "mantle", "core"]
    assert len(again.labels()) == 3


@pytest.mark.parametrize("kwargs", [
    dict(layers=[]), dict(layers=[("a", "A", 0)]), dict(layers=[("a", "A"), ("a", "B")]),
    dict(layers=[("a",)]), dict(shape="wedge"), dict(box=(0, 0, 0, 10)),
])
def test_bad_cross_sections_are_refused(kwargs):
    options = dict(box=(10, 10, 300, 200), layers=[("a", "A"), ("b", "B")])
    options.update(kwargs)
    with pytest.raises(ValidationError):
        CrossSection(lesson(), **options)


# --- all kits -----------------------------------------------------------------


def test_kit_text_that_needs_a_font_fails_loudly_and_names_the_character():
    with pytest.raises(ValidationError, match="U\\+0E19"):
        Flowchart(lesson(), origin=(100, 100)).node("thai", "นิ", at=(0, 0))


def test_kit_parts_are_plain_drawcv_in_one_group_each():
    tutorial = lesson(900, 700)
    kits = [Flowchart(tutorial, origin=(100, 60)), Timeline(tutorial, start=(40, 600), length=500, span=(0, 10)),
            ForceDiagram(tutorial, center=(700, 150)),
            CrossSection(tutorial, box=(600, 300, 200, 200), layers=[("a", "A"), ("b", "B")], shape="rings")]
    groups = [obj for obj in tutorial.scene.layers[0].objects if isinstance(obj, Group)]
    assert len(groups) == len(kits)
    assert all(g.metadata["tutordraw"]["kit"] for g in groups)
    assert isinstance(tutorial.get_target("a").drawable, Circle)

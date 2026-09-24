"""Tutorial.describe: plain-English step descriptions from the lesson's structure."""

import pytest
from drawcv import Circle, Color, FillStyle, Point, Rectangle, Scene

from golden_lessons import LESSONS
from tutordraw import Tutorial, ValidationError
from tutordraw.describe import colour_name

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


@pytest.fixture
def lesson():
    scene = Scene(600, 400, background=Color.white())
    shapes = {name: Circle(center=Point(100 + 150 * i, 200), radius=20,
                           fill=FillStyle(color=Color(120, 120, 120)))
              for i, name in enumerate(("sun", "earth", "moon"))}
    for shape in shapes.values():
        scene.add(shape)
    tutorial = Tutorial(scene, title="Orbits")
    return tutorial, {name: tutorial.target(shape, name=name) for name, shape in shapes.items()}


def test_labels_and_notes_read_in_the_order_they_appear(lesson):
    tutorial, t = lesson
    step = tutorial.step("Meet them", duration=4)
    step.show(t["sun"].label("Sun"))
    step.explain(t["earth"], "Our planet.", at=2.0)
    step.show(t["moon"].label("Moon"), at=1.0)
    assert tutorial.describe(0) == (
        'Meet them. The sun is labelled "Sun". Then the moon is labelled "Moon". '
        'Then a note on the earth says: "Our planet."')


def test_changes_are_described_relative_to_the_previous_step(lesson):
    tutorial, t = lesson
    tutorial.step("Start").restyle(t["moon"], visible=False)
    tutorial.step("Rise").animate().restyle(t["moon"], move=(0, -50), fill=(200, 40, 40))
    tutorial.step("Hold").restyle(t["moon"], move=(0, -50), fill=(200, 40, 40)) \
        .restyle(t["sun"], opacity=0.3)
    tutorial.step("Reset")
    assert tutorial.describe(0) == "Start."  # hidden from the start: never seen
    assert tutorial.describe(1) == "Rise. The moon appears, slides up and turns red."
    assert tutorial.describe(2) == "Hold. The sun fades to 30%."  # the moon did not change
    assert tutorial.describe(3) == ("Reset. The moon moves back down and returns to its "
                                    "original colour. The sun is fully shown.")


def test_camera_dimming_highlights_and_numbers(lesson):
    tutorial, t = lesson
    close = tutorial.step("Close").zoom_to(t["earth"]).dim_others(t["earth"])
    close.highlight(t["earth"], shape="outline").number(t["sun"])
    close.number(t["moon"])
    tutorial.step("Wide").animate()
    assert tutorial.describe(0) == (
        "Close. The view is zoomed in on the earth. Everything except the earth is dimmed. "
        "The sun and the moon are numbered 1 and 2. The earth is outlined.")
    assert tutorial.describe(1) == "Wide. The view zooms back out to the whole scene."


def test_every_mark_kind_has_a_sentence(lesson):
    tutorial, t = lesson
    step = tutorial.step("Marks")
    step.connect(t["sun"], t["earth"], "light")
    step.connect(t["earth"], t["moon"], both=True)
    step.connect((10, 10), t["moon"], "push")
    step.connect(t["sun"], (5, 5))
    step.brace(t["earth"], t["moon"], text="system")
    step.measure(t["sun"], text="40 km")
    step.measure(t["sun"], axis="y")
    step.measure(t["sun"], t["moon"], "300 km", axis="free")
    step.angle(t["earth"], t["sun"], (380, 100), "30°")
    step.number(t["sun"])
    assert tutorial.describe(0) == (
        'Marks. An arrow goes from the sun to the earth, labelled "light". '
        "A two-way arrow joins the earth and the moon. "
        'An arrow points at the moon, labelled "push". '
        "An arrow points away from the sun. "
        'A brace groups the earth and the moon, labelled "system". '
        'The width of the sun is marked as "40 km". '
        "The height of the sun is marked. "
        'The distance from the sun to the moon is marked as "300 km". '
        'The angle at the earth between the sun and the point (380, 100) is marked as "30°". '
        "The sun is numbered 1.")


def test_unnamed_targets_and_whole_lessons():
    scene = Scene(200, 200)
    box = Rectangle(position=Point(10, 10), width=20, height=20)
    scene.add(box)
    tutorial = Tutorial(scene)
    tutorial.step("Only").show(tutorial.target(box).label("Box"))
    assert tutorial.describe(0) == 'Only. An unnamed object is labelled "Box".'
    assert tutorial.describe() == '1 step.\nStep 1: Only. An unnamed object is labelled "Box".'
    for bad in (-1, 1, True):
        with pytest.raises(ValidationError):
            tutorial.describe(bad)


@pytest.mark.parametrize("rgb, name", [
    ((168, 68, 52), "red"), ((250, 210, 70), "yellow"), ((40, 90, 160), "blue"),
    ((20, 20, 20), "black"), ((245, 245, 245), "white"), ((90, 170, 80), "green"),
])
def test_colours_get_everyday_names(rgb, name):
    assert colour_name(rgb) == name


def test_descriptions_travel_with_web_steps():
    tutorial = LESSONS["motion"][0]()
    assert tutorial.web_step(1)["description"] == tutorial.describe(1)
    assert "slides down and right and turns red" in tutorial.describe(1)


def test_plural_names_agree_and_first_step_hiding_is_silent(lesson):
    tutorial, t = lesson
    scene = tutorial.scene
    gears = Circle(center=Point(50, 50), radius=10, fill=FillStyle(color=Color(1, 2, 3)))
    scene.add(gears)
    g = tutorial.target(gears, name="gears")
    tutorial.step("One").restyle(g, visible=False).show(t["sun"].label("Sun"))
    tutorial.step("Two").show(g.label("Gears")).highlight(g)
    tutorial.step("Three").restyle(g, visible=False)
    assert tutorial.describe(0) == 'One. The sun is labelled "Sun".'
    assert tutorial.describe(1) == 'Two. The gears appear. The gears are boxed. The gears are labelled "Gears".'
    assert tutorial.describe(2) == "Three. The gears are hidden."


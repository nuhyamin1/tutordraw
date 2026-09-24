"""Inside the Earth with the cross-section kit.

Rings are drawn outside in, with thicknesses relative to each other, and
`labels()` lines the labels up in one column, each pointing into its own
ring. Here each step adds one label, outside in.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import CrossSection

INK = Color(40, 52, 72)
LAYERS = [("crust", "Crust", 0.5), ("mantle", "Mantle", 2.9), ("outer_core", "Outer core", 2.2),
          ("inner_core", "Inner core", 1.2)]
SAID = {
    "crust": ("The crust is the thin rocky skin we live on.", "thin rocky skin"),
    "mantle": ("Below it, the mantle is hot rock that flows very slowly.", "the mantle"),
    "outer_core": ("The outer core is liquid iron and nickel.", "liquid iron"),
    "inner_core": ("At the centre, the inner core is solid metal, as hot as the Sun's surface.",
                   "solid metal"),
}


def build_tutorial() -> Tutorial:
    scene = Scene(900, 600, background=Color(248, 250, 252))
    scene.add(Text(text="INSIDE THE EARTH", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="The layers of the Earth")
    earth = CrossSection(lesson, box=(60, 80, 480, 480), shape="rings", layers=LAYERS, name="earth",
                         fills=[(150, 120, 90), (230, 140, 80), (245, 190, 70), (255, 230, 150)])
    labels = earth.labels()
    for count, (layer, label) in enumerate(zip(earth.layers, labels), start=1):
        step = lesson.step(label.text)
        step.show(*labels[:count])
        step.highlight(layer)
        words, cue = SAID[layer.name]
        step.narrate(words, {label: cue})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/earth_layers")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

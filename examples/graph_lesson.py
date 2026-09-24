"""Read a graph: y = x² with the axes kit.

The kit draws the axes, ticks and curve as ordinary DrawCV objects and hands
back named targets, so the lesson only has to say what to point at. Kit parts
are part of the drawing, visible in every step, so the reading point and its
guide lines are hidden with restyle until the step that uses them. Narration
cues time each reveal. The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import Axes

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(960, 560, background=Color(248, 250, 252))
    scene.add(Text(text="READING A GRAPH", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="Reading y = x²")
    axes = Axes(lesson, box=(90, 80, 480, 420), x_range=(-3, 3), y_range=(-1, 9), grid=True)
    axes.plot(lambda x: x * x, name="parabola_curve")
    vertex = axes.point(0, 0, name="vertex")
    reading = axes.point(2, 4, name="reading")
    guides = axes.guide(x=2, y=4, name="guides")
    # An invisible anchor on the curve, so its label points at the curve itself.
    on_curve = axes.point(-2.4, 5.76, name="parabola", visible=False)

    shape = lesson.step("The shape")
    shape.restyle(reading, visible=False).restyle(guides, visible=False)
    name = on_curve.label("y = x²", anchor="left")
    shape.show(name)
    shape.narrate("This curve is y equals x squared. Every x value is squared "
                  "to give its height.", {name: "y equals x squared"})

    lowest = lesson.step("The vertex")
    lowest.restyle(reading, visible=False).restyle(guides, visible=False)
    note = lowest.explain(vertex, "Lowest point: (0, 0)", anchor="right", gap=40)
    lowest.narrate("Its lowest point, the vertex, sits at the origin.", {note: "the vertex"})

    read = lesson.step("Reading a value")
    value = reading.label("(2, 4)", anchor="right")
    read.show(value, draw=True)
    read.highlight(reading)
    read.narrate("To read the graph at x equals two, go up to the curve and across: "
                 "y is four.", {reading: "go up to the curve", value: "y is four"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/graph")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

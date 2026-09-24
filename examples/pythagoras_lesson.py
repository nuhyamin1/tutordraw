"""The Pythagorean theorem with the equation kit.

The equation is typeset from LaTeX (needs `pip install "tutordraw[math]"`)
into ordinary DrawCV shapes, in pieces: each squared term is its own target,
so a step can point from a² to its side of the triangle, colour it, or narrate
it, while the rest of the equation stays put.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, FillStyle, Line, Point, Polygon, Scene, StrokeStyle, Text
from tutordraw import Tutorial
from tutordraw.kits import Equation

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(960, 540, background=Color(248, 250, 252))
    scene.add(Text(text="THE PYTHAGOREAN THEOREM", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    corner, top, right = Point(120, 440), Point(120, 170), Point(480, 440)
    scene.add(Polygon(vertices=[corner, top, right], fill=FillStyle(color=Color(225, 236, 248)),
                      stroke=StrokeStyle(color=INK, width=2)))
    sides = {"side_a": Line(start=corner, end=top, stroke=StrokeStyle(color=INK, width=4)),
             "side_b": Line(start=corner, end=right, stroke=StrokeStyle(color=INK, width=4)),
             "hypotenuse": Line(start=top, end=right, stroke=StrokeStyle(color=INK, width=4))}
    for line in sides.values():
        scene.add(line)
    lesson = Tutorial(scene, title="The Pythagorean theorem")
    a, b, c = (lesson.target(line, name=name) for name, line in sides.items())
    equation = Equation(lesson, [("a_squared", "a^2"), "+", ("b_squared", "b^2"), "=",
                                 ("c_squared", "c^2")], position=(600, 250), size=48, name="theorem")
    c2 = equation.part("c_squared")

    triangle = lesson.step("A right triangle")
    triangle.restyle(equation.equation, visible=False)
    # A diagonal line's bounds are a big box, so label c from the line's middle.
    labels = [a.label("a", anchor="left"), b.label("b", anchor="bottom"),
              c.label("c", anchor="center", offset=(28, -34))]
    triangle.show(*labels)
    triangle.narrate("A right triangle has two short sides, a and b, and a long side, c, "
                     "called the hypotenuse.", {labels[2]: "a long side"})

    rule = lesson.step("The rule")
    rule.highlight(equation.equation)
    rule.narrate("The theorem says: a squared plus b squared equals c squared.",
                 {equation.equation: "The theorem says"})

    long = lesson.step("The long side")
    long.restyle(c2, fill=(200, 70, 50))
    middle = ((top.x + right.x) / 2, (top.y + right.y) / 2)
    link = long.connect(c2, middle, bend=0.25, draw=True)
    long.narrate("c squared belongs to the hypotenuse, the side opposite the right angle.",
                 {link: "belongs to the hypotenuse"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/pythagoras")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

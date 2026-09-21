"""Label a diagram with the symbols a science or maths lesson actually needs."""

from pathlib import Path
import sys

from drawcv import (Circle, Color, FillStyle, Group, Line, Point, Scene,
                    StrokeStyle, Text)
from tutordraw import Theme, Tutorial


def build_tutorial() -> Tutorial:
    scene = Scene(1100, 620, background=Color(240, 245, 251))
    scene.add(Group(children=[
        Text(text="MEASURING A CELL", position=Point(48, 35), font_scale=1.1,
             thickness=2, color=Color(28, 43, 65)),
        Text(text="Symbols beyond ASCII: µm, °, α, ½",
             position=Point(48, 85), font_scale=0.65, color=Color(75, 104, 140)),
    ]))
    membrane = Circle(center=Point(330, 360), radius=150,
                      fill=FillStyle(color=Color(213, 234, 230)),
                      stroke=StrokeStyle(color=Color(74, 134, 121), width=3))
    nucleus = Circle(center=Point(300, 330), radius=52,
                     fill=FillStyle(color=Color(131, 151, 218)),
                     stroke=StrokeStyle(color=Color(73, 89, 151), width=3))
    axis = Line(start=Point(330, 360), end=Point(470, 290),
                stroke=StrokeStyle(color=Color(160, 120, 60), width=2))
    for shape in (membrane, nucleus, axis):
        scene.add(shape)

    lesson = Tutorial(scene, title="Measuring a cell",
                      theme=Theme(font_scale=0.75, padding=14))
    cell = lesson.target(membrane, name="membrane")
    core = lesson.target(nucleus, name="nucleus")
    tilt = lesson.target(axis, name="axis")

    scale = lesson.step("Measure the cell").show(cell.label("30 µm", anchor="left", gap=30))
    scale.highlight(cell)
    scale.explain(cell, "This cell measures about 30 µm across — roughly "
                        "½ the width of a human hair.", gap=150, max_width=330)

    heat = lesson.step("Note the conditions").show(core.label("37 °C", anchor="top", gap=48))
    heat.highlight(core).dim_others(core)
    heat.explain(core, "Held at 37 °C ± 0.5 °C. Below ≤ 4 °C "
                       "the activity effectively stops.", gap=250, max_width=330)

    angle = lesson.step("Measure the axis").show(tilt.label("α = 45°", anchor="right", gap=40))
    angle.highlight(tilt)
    angle.explain(tilt, "The long axis sits at α = 45° from horizontal, "
                        "about 2 × the tilt of the previous sample.",
                  gap=200, max_width=330)
    return lesson


def main() -> None:
    # A legacy Windows console cannot encode these symbols; degrade the terminal
    # message rather than failing. The rendered PNGs are unaffected.
    sys.stdout.reconfigure(errors="replace")
    output = Path(__file__).resolve().parents[1] / "output" / "symbols"
    lesson = build_tutorial()
    paths = lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(paths)} steps using µm, °C, α, ½, "
          f"±, ≤ and × in {output}")


if __name__ == "__main__":
    main()

"""Run after installing TutorDraw: python examples/cell_tutorial.py."""

from pathlib import Path

from drawcv import Circle, Color, FillStyle, Point, Scene, StrokeStyle, Text
from tutordraw import Tutorial


def main() -> None:
    scene = Scene(900, 540, background=Color(240, 245, 251))
    scene.add(Text(text="INSIDE A CELL", position=Point(48, 35), font_scale=1.1,
                   thickness=2, color=Color(28, 43, 65)))
    scene.add(Text(text="01 / Meet the nucleus", position=Point(48, 85),
                   font_scale=0.65, color=Color(75, 104, 140)))
    cell = Circle(center=Point(335, 315), radius=155,
                  fill=FillStyle(color=Color(213, 234, 230)),
                  stroke=StrokeStyle(color=Color(74, 134, 121), width=3))
    nucleus = Circle(center=Point(360, 300), radius=58,
                     fill=FillStyle(color=Color(131, 151, 218)),
                     stroke=StrokeStyle(color=Color(73, 89, 151), width=3))
    scene.add(cell)
    scene.add(nucleus)
    scene.add(Circle(center=Point(260, 390), radius=24,
                     fill=FillStyle(color=Color(222, 168, 108))))
    tutorial = Tutorial(scene, title="Inside a cell")
    target = tutorial.target(nucleus, name="nucleus")
    label = target.label("Nucleus", gap=130, font_scale=0.85, padding=14)
    tutorial.step("Meet the nucleus").show(label)
    tutorial.step("Unannotated drawing")
    output = Path(__file__).resolve().parents[1] / "output"
    tutorial.render_step(0).save(output / "cell-step-01.png")
    tutorial.render_step(1).save(output / "cell-step-02.png")
    print(f"Saved tutorial images in {output}")


if __name__ == "__main__":
    main()

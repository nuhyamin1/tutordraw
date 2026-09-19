"""Run after installing TutorDraw: python examples/cell_tutorial.py."""

from pathlib import Path

from drawcv import Circle, Color, FillStyle, Group, Point, Scene, StrokeStyle, Text
from tutordraw import Theme, Tutorial


def build_tutorial() -> Tutorial:
    scene = Scene(1100, 620, background=Color(240, 245, 251))
    heading = Group(children=[
        Text(text="INSIDE A CELL", position=Point(48, 35), font_scale=1.1,
             thickness=2, color=Color(28, 43, 65)),
        Text(text="A three-step visual lesson", position=Point(48, 85),
             font_scale=0.65, color=Color(75, 104, 140)),
    ])
    scene.add(heading)
    cell = Circle(center=Point(300, 355), radius=160,
                  fill=FillStyle(color=Color(213, 234, 230)),
                  stroke=StrokeStyle(color=Color(74, 134, 121), width=3))
    nucleus = Circle(center=Point(315, 335), radius=55,
                     fill=FillStyle(color=Color(131, 151, 218)),
                     stroke=StrokeStyle(color=Color(73, 89, 151), width=3))
    scene.add(cell)
    scene.add(nucleus)
    scene.add(Circle(center=Point(230, 420), radius=24,
                     fill=FillStyle(color=Color(222, 168, 108))))
    tutorial = Tutorial(scene, title="Inside a cell", theme=Theme(font_scale=0.75, padding=14))
    target = tutorial.target(nucleus, name="nucleus")
    whole_cell = tutorial.target(cell, name="cell")
    title = tutorial.target(heading, name="heading")
    label = target.label("Nucleus", anchor="top", gap=45)
    cell_label = whole_cell.label("Cell", anchor="left", gap=28)
    intro = tutorial.step("Explore the cell").show(cell_label)
    intro.explain(whole_cell, "Cells are the building blocks of living things. Each part has a job that helps the cell function.",
                  gap=140, max_width=340)
    focus = tutorial.step("Meet the nucleus").show(label)
    focus.highlight(target).dim_others(target, title)
    focus.explain(target, "The nucleus contains the cell's DNA. This genetic information helps direct the cell's activities.",
                  gap=240, max_width=340)
    review = tutorial.step("Review the diagram").show(cell_label, label)
    review.explain(whole_cell, "Review: find the cell and its nucleus. Notice how the nucleus sits inside the larger cell.",
                   gap=140, max_width=340)
    return tutorial


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output" / "cell"
    # Explicit overwrite makes this development example repeatable.
    build_tutorial().export_steps(output, overwrite=True)
    print(f"Saved tutorial images in {output}")


if __name__ == "__main__":
    main()

"""Illustrate focus within nested groups without multiplying dimming twice."""

from pathlib import Path

from drawcv import Circle, Color, FillStyle, Group, Point, Scene, Text
from tutordraw import Tutorial


def main() -> None:
    scene = Scene(900, 420, background=Color(240, 245, 251))
    heading = Text(text="FOCUS INSIDE A GROUP", position=Point(45, 35), font_scale=1, thickness=2)
    scene.add(heading)
    shapes = [Circle(center=Point(x, 240), radius=45, fill=FillStyle(color=Color(70, 130, 200)))
              for x in (160, 450, 740)]
    scene.add(Group(children=[Group(children=shapes[:2], opacity=0.85),
                              Group(children=[shapes[2]], opacity=0.85)]))
    tutorial = Tutorial(scene)
    targets = [tutorial.target(obj) for obj in shapes]
    title = tutorial.target(heading)
    step = tutorial.step("Focus on one child")
    step.dim_others(targets[0], title).highlight(targets[0])
    for target, name in zip(targets, ("Focused child", "Sibling dimmed", "Other branch dimmed")):
        step.show(target.label(name, anchor="bottom", gap=32, font_scale=0.6))
    output = Path(__file__).resolve().parents[1] / "output" / "group-focus.png"
    tutorial.render_step(0).save(output)
    print(output)


if __name__ == "__main__":
    main()

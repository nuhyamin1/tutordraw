"""Add and subtract on a number line: 2 + 3 - 4.

Each hop is a step mark, so it belongs to its step, draws on, and is timed
by narration cues. The answer dot is part of the drawing, so it is hidden
until the step that reaches it.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import NumberLine

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(960, 360, background=Color(248, 250, 252))
    scene.add(Text(text="2 + 3 - 4 ON A NUMBER LINE", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="Adding on a number line")
    line = NumberLine(lesson, start=(120, 210), length=720, value_range=(0, 6), step=1)
    start = line.point(2, name="start")
    answer = line.point(1, name="answer", color=(40, 150, 90))

    begin = lesson.step("Start at 2")
    begin.restyle(answer, visible=False)
    here = start.label("start", anchor="top", gap=50)
    begin.show(here)
    begin.narrate("We start at two.", {here: "start at two"})

    add = lesson.step("Add 3")
    add.restyle(answer, visible=False)
    plus = line.hop(add, 2, 5, "+3")
    add.narrate("Adding three means three steps to the right, landing on five.",
                {plus: "three steps to the right"})

    take = lesson.step("Take away 4")
    line.hop(take, 2, 5, "+3", draw=False)  # the earlier hop, already there
    minus = line.hop(take, 5, 1, "-4")
    finish = answer.label("= 1", anchor="bottom", gap=46)
    take.show(finish)
    take.narrate("Taking away four means four steps back to the left. We land on one.",
                 {minus: "four steps back", finish: "land on one"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/number_line")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

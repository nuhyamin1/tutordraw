"""Follow a decision: a flowchart with the flowchart kit.

Nodes are placed by counting grid cells, and links route themselves with
square corners, so the lesson only says what connects to what. Each step
walks one path and highlights where we are; the other branch dims. Links are
part of the drawing, so later ones are hidden until their step.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import Flowchart

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(900, 560, background=Color(248, 250, 252))
    scene.add(Text(text="SHOULD I TAKE AN UMBRELLA?", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="Reading a flowchart")
    flow = Flowchart(lesson, origin=(260, 110), cell=(260, 110))
    start = flow.node("start", "Leaving home", at=(0, 0), shape="terminal")
    check = flow.node("question", "Is it raining?", at=(0, 1), shape="decision")
    umbrella = flow.node("umbrella", "Take an umbrella", at=(1, 2))
    walk = flow.node("school", "Walk to school", at=(0, 3), shape="terminal")
    flow.link(start, check)
    yes = flow.link(check, umbrella, "yes")
    no = flow.link(check, walk, "no")
    joined = flow.link(umbrella, walk)
    later = (umbrella, yes, no, joined, walk)

    begin = lesson.step("Start")
    for part in later:
        begin.restyle(part, visible=False)
    begin.highlight(start)
    begin.narrate("A flowchart starts at a rounded box. We are leaving home.", {start: "rounded box"})

    ask = lesson.step("The question")
    for part in (umbrella, yes, joined):
        ask.restyle(part, visible=False)
    ask.highlight(check)
    ask.narrate("The diamond asks a question. Each answer is an arrow out of it.",
                {check: "The diamond"})

    branch = lesson.step("If it is raining")
    branch.highlight(umbrella)
    branch.dim_others(check, umbrella, yes, joined, walk)
    branch.narrate("If it is raining, follow yes: take an umbrella, then walk to school.",
                   {umbrella: "take an umbrella"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/flowchart")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

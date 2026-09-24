"""Balanced and unbalanced forces with the force diagram kit.

Arrow lengths are to scale (4 px per newton), so the picture compares the
forces honestly and the net force is worked out, not drawn by eye. Forces
are part of the drawing, hidden with restyle until the step that adds them.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import ForceDiagram

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(900, 600, background=Color(248, 250, 252))
    scene.add(Text(text="FORCES ON A CRATE", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="Balanced and unbalanced forces")
    crate = ForceDiagram(lesson, center=(450, 320), size=90, scale=4, text="5 kg", name="crate")
    weight = crate.force("weight", "down", 49, "weight 49 N")
    support = crate.force("normal_force", "up", 49, "normal 49 N")
    push = crate.force("push", "right", 40, "push 40 N")
    friction = crate.force("friction", "left", 15, "friction 15 N")
    net = crate.net("net force 25 N")

    still = lesson.step("Balanced")
    for part in (push, friction, net):
        still.restyle(part, visible=False)
    still.highlight(weight).highlight(support)
    still.narrate("Gravity pulls the crate down with forty nine newtons, and the floor pushes up "
                  "just as hard. The forces balance, so the crate stays still.",
                  {weight: "Gravity pulls", support: "floor pushes up"})

    shove = lesson.step("A push")
    shove.restyle(net, visible=False)
    shove.highlight(push).highlight(friction)
    shove.narrate("Now we push with forty newtons. Friction pushes back with fifteen.",
                  {push: "we push", friction: "Friction"})

    result = lesson.step("The net force")
    # The net force runs along the push, so it replaces the two sideways forces.
    result.restyle(push, visible=False).restyle(friction, visible=False)
    result.highlight(net)
    result.narrate("Forty minus fifteen leaves twenty five newtons to the right, so the crate "
                   "speeds up that way.", {net: "twenty five newtons"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/forces")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

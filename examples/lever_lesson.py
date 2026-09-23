"""Explain a lever with the schema v8 vocabulary.

Arrows for forces, measures for the arms, a brace, numbered steps, an outline
highlight that follows the fulcrum's shape, a camera that zooms in on it, and
strokes that draw themselves on as a narrator would point at them. The lesson
lints clean, and the script fails if it does not.
"""

from pathlib import Path

from drawcv import Circle, Color, FillStyle, Point, Polygon, Rectangle, Scene, StrokeStyle, Text
from tutordraw import Theme, Tutorial

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(1000, 560, background=Color(246, 248, 251))
    scene.add(Text(text="HOW A LEVER LIFTS", position=Point(40, 30), font_scale=0.9,
                   thickness=2, color=INK))
    ground = Rectangle(position=Point(0, 430), width=1000, height=130,
                       fill=FillStyle(color=Color(226, 232, 238)))
    fulcrum = Polygon(vertices=[Point(420, 430), Point(480, 430), Point(450, 372)],
                      fill=FillStyle(color=Color(120, 130, 150)))
    beam = Rectangle(position=Point(170, 362), width=640, height=10,
                     fill=FillStyle(color=Color(150, 110, 70)))
    load = Rectangle(position=Point(190, 272), width=90, height=90,
                     fill=FillStyle(color=Color(200, 90, 80)),
                     stroke=StrokeStyle(color=Color(150, 60, 50), width=2))
    effort = Circle(center=Point(780, 340), radius=22, fill=FillStyle(color=Color(80, 140, 210)))
    for shape in (ground, fulcrum, beam, load, effort):
        scene.add(shape)

    lesson = Tutorial(scene, title="Levers", theme=Theme(draw_seconds=0.8))
    t_fulcrum = lesson.target(fulcrum, name="fulcrum")
    t_load = lesson.target(load, name="load")
    t_effort = lesson.target(effort, name="effort")

    # Each step is narrated, and things appear as the voice mentions them.
    # These strings are timed at an even speaking pace; with a TTS engine,
    # pass its word timings instead: [(word, start, end), ...].
    parts = lesson.step("The parts")
    parts.number(t_load)
    parts.number(t_fulcrum, corner="top_right")
    parts.number(t_effort, corner="top_right")
    load = t_load.label("Load", anchor="top")
    fulcrum = t_fulcrum.label("Fulcrum", anchor="bottom")
    effort = t_effort.label("Effort", anchor="top")
    parts.show(load, fulcrum, effort, draw=True)
    parts.narrate("A lever has three parts: the load we want to lift, the fulcrum "
                  "it pivots on, and the effort we apply.",
                  {load: "the load", fulcrum: "the fulcrum", effort: "the effort"})

    pivot = lesson.step("The pivot").animate().zoom_to(t_fulcrum, padding=90, max_scale=3)
    pivot.highlight(t_fulcrum, shape="outline", padding=6, draw=True)
    turns = pivot.explain(t_fulcrum, "The beam turns about this point.", anchor="right",
                          max_width=220)
    pivot.narrate("Look closely at the fulcrum. The whole beam turns about this single point.",
                  {t_fulcrum: "fulcrum", turns: "the whole beam"})

    arms = lesson.step("Arms and forces").animate()
    short = arms.measure(t_load, t_fulcrum, "short arm", axis="x", offset=40, draw=True)
    long = arms.measure(t_fulcrum, t_effort, "long arm", axis="x", offset=40, draw=True)
    # A force arrow: from a fixed point above, pressing down on the effort end.
    push = arms.connect((780, 240), t_effort, "small push", draw=True)
    heavy = arms.brace(t_load, text="heavy", side="left", draw=True)
    moral = arms.explain(t_effort, "A long arm lets a small force lift a heavy load.",
                         anchor="top", max_width=240)
    arms.narrate("The load sits on a short arm, and we push on a long arm. So a small "
                 "push lifts a heavy load. That is the trade a lever makes.",
                 {short: "short arm", long: "long arm", push: "small push",
                  heavy: "heavy load", moral: "that is the trade"})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/lever")
    lesson.export_steps(output, overwrite=True)
    # A mid-draw frame, to show strokes arriving rather than popping in.
    arms_start = lesson.steps[0].duration + lesson.steps[1].duration
    lesson.render_at_time(arms_start + 1.5).save(str(output / "drawing-on.png"))
    print(f"Saved {len(lesson.steps)} steps and a mid-draw frame in {output.resolve()}; lint is clean")


if __name__ == "__main__":
    main()

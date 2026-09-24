"""The water cycle with the cycle kit.

The kit spaces the four stages round a circle and joins each to the next
with a curved arrow; each stage is a target named from its text. Each step
lights up one stage and the arrow into it, and narration times the reveal.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import Cycle

INK = Color(40, 52, 72)
# Each stage's narration, and the phrase that lights it up.
STORY = {
    "evaporation": ("The Sun warms the sea and water evaporates into the air as vapour.",
                    "water evaporates"),
    "condensation": ("High up, the vapour cools and condenses into clouds.", "condenses"),
    "precipitation": ("When the droplets grow heavy they fall as rain or snow.", "fall as rain"),
    "collection": ("The water collects in rivers and seas, and the cycle begins again.",
                   "collects"),
}


def build_tutorial() -> Tutorial:
    scene = Scene(900, 620, background=Color(248, 250, 252))
    scene.add(Text(text="THE WATER CYCLE", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="The water cycle")
    cycle = Cycle(lesson, center=(450, 340), radius=210,
                  stages=["Evaporation", "Condensation", "Precipitation", "Collection"])
    # arrows[i] leaves stage i, so the arrow into stage i is arrows[i - 1].
    into = {stage.name: cycle.arrows[i - 1] for i, stage in enumerate(cycle.stages)}
    for stage in cycle.stages:
        step = lesson.step(stage.name.capitalize())
        step.highlight(stage)
        step.dim_others(stage, into[stage.name])
        words, cue = STORY[stage.name]
        step.narrate(words, {stage: cue})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/water_cycle")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

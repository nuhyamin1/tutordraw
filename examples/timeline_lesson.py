"""A century of flight with the timeline kit.

Dates map onto the line and events alternate above and below it, climbing
clear of each other when they crowd. Periods band the line. Each step shows
one more event, so the lesson reads left to right like the story.
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import Timeline

INK = Color(40, 52, 72)
EVENTS = [
    (1903, "First powered flight", "The Wright brothers fly for twelve seconds in 1903.", "Wright brothers"),
    (1927, "Solo across the Atlantic", "In 1927 Lindbergh flies alone across the Atlantic.", "alone across"),
    (1947, "Faster than sound", "In 1947 a plane breaks the sound barrier.", "sound barrier"),
    (1969, "Moon landing", "And in 1969, people walk on the Moon.", "walk on the Moon"),
]


def build_tutorial() -> Tutorial:
    scene = Scene(960, 420, background=Color(248, 250, 252))
    scene.add(Text(text="A CENTURY OF FLIGHT", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="A century of flight")
    line = Timeline(lesson, start=(70, 240), length=800, span=(1900, 1980))
    jets = line.period(1939, 1980, "The jet age", name="jet_age")  # first, so events clear it
    events = [line.event(year, text, name=f"flight_{year}") for year, text, _, _ in EVENTS]
    for count, (event, (_, _, words, cue)) in enumerate(zip(events, EVENTS), start=1):
        step = lesson.step(EVENTS[count - 1][1])
        for later in events[count:]:
            step.restyle(later, visible=False)
        if count < 3:
            step.restyle(jets, visible=False)
        step.highlight(event)
        step.narrate(words, {event: cue})
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    output = Path("output/timeline")
    lesson.export_steps(output, overwrite=True)
    print(f"Saved {len(lesson.steps)} steps in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

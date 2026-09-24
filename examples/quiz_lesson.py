"""Check understanding with a prompt: "Tap the stage where clouds form."

The first steps teach the water cycle; the last asks a question the learner
answers by tapping the picture. In the browser player the step waits for a
tap, says what was tapped if it is wrong, and rings the answer after three
misses or "Show me". `check_answer` judges a tap the same way in Python.
Prompts are not saved in lesson files yet (see docs/PROMPTS.md).
The lesson lints clean and the script fails if not.
"""

from pathlib import Path

from drawcv import Color, Point, Scene, Text
from tutordraw import Tutorial
from tutordraw.kits import Cycle

INK = Color(40, 52, 72)


def build_tutorial() -> Tutorial:
    scene = Scene(900, 620, background=Color(248, 250, 252))
    scene.add(Text(text="THE WATER CYCLE: QUICK CHECK", position=Point(40, 26), font_scale=0.9,
                   thickness=2, color=INK))
    lesson = Tutorial(scene, title="Water cycle quiz")
    cycle = Cycle(lesson, center=(450, 340), radius=210,
                  stages=["Evaporation", "Condensation", "Precipitation", "Collection"])

    tour = lesson.step("Four stages")
    tour.narrate("Water goes round four stages: evaporation, condensation, precipitation and "
                 "collection.")

    clouds = lesson.step("Clouds")
    note = clouds.explain(cycle.stage("condensation"), "Vapour cools into droplets: clouds",
                          anchor="bottom", gap=30)
    clouds.narrate("Clouds form when rising vapour cools and condenses.", {note: "Clouds form"})

    quiz = lesson.step("Your turn")
    quiz.ask("Tap the stage where clouds form.", cycle.stage("condensation"),
             wrong="That's {tapped}. Where does vapour cool?")
    quiz.narrate("Your turn. Tap the stage where clouds form.")
    return lesson


def main() -> None:
    lesson = build_tutorial()
    issues = [issue for issue in lesson.lint() if issue.severity != "info"]
    if issues:
        raise SystemExit("Lint found problems:\n" + "\n".join(
            f"  step {i.step} {i.code}: {i.message} -> {i.fix}" for i in issues))
    # A tap on Condensation's box, then one on Evaporation's, judged in Python.
    for name in ("condensation", "evaporation"):
        centre = lesson.get_target(name).drawable.get_bounds().center
        answer = lesson.check_answer(2, centre.x, centre.y)
        print(f"Tap on {name}: correct={answer.correct}: {answer.feedback}")
    output = Path("output/quiz")
    lesson.export_steps(output, overwrite=True)
    page = lesson.export_web(output / "quiz.html", overwrite=True)
    print(f"Saved {len(lesson.steps)} steps and {page.name} in {output.resolve()}; lint is clean")
    print(lesson.describe())


if __name__ == "__main__":
    main()

"""Interactive prompts: step.ask, hit testing, feedback, lint, web payloads."""

import warnings

import pytest
from drawcv import Circle, Color, FillStyle, Group, Point, Rectangle, Scene

from tutordraw import LessonWarning, Tutorial, ValidationError
from tutordraw.kits import Flowchart

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


@pytest.fixture
def cell():
    """A cell (a group) with a nucleus inside it and a mitochondrion beside it."""
    scene = Scene(600, 400, background=Color.white())
    body = Circle(center=Point(250, 200), radius=150, fill=FillStyle(color=Color(220, 240, 220)))
    nucleus = Circle(center=Point(220, 190), radius=40, fill=FillStyle(color=Color(120, 90, 180)))
    mito = Rectangle(position=Point(300, 240), width=60, height=24, fill=FillStyle(color=Color(230, 150, 90)))
    group = Group(children=[body, nucleus, mito])
    scene.add(group)
    lesson = Tutorial(scene)
    lesson.target(group, name="cell")
    lesson.target(nucleus, name="nucleus")
    lesson.target(mito, name="mitochondrion")
    return lesson


def test_ask_stores_one_prompt_and_validates(cell):
    step = cell.step("Quiz")
    nucleus = cell.get_target("nucleus")
    assert step.prompt is None
    assert step.ask("Tap the nucleus.", nucleus) is step
    assert step.prompt.answers == (nucleus,) and step.prompt.attempts == 3
    step.ask("Tap the nucleus or the cell.", (nucleus, cell.get_target("cell")), attempts=1)
    assert len(step.prompt.answers) == 2  # asking again replaces
    other = Tutorial(Scene(10, 10))
    stranger = other.target(_added(other), name="x")
    for bad in (lambda: step.ask("", nucleus), lambda: step.ask("Tap", "nucleus"),
                lambda: step.ask("Tap", ()), lambda: step.ask("Tap", nucleus, attempts=0),
                lambda: step.ask("Tap", nucleus, attempts=True), lambda: step.ask("Tap", stranger)):
        with pytest.raises(ValidationError):
            bad()
    assert step.clear_prompt().prompt is None


def _added(tutorial):
    dot = Circle(center=Point(5, 5), radius=2)
    tutorial.scene.add(dot)
    return dot


def test_hit_test_is_innermost_first_and_ignores_annotations(cell):
    step = cell.step("Look")
    nucleus = cell.get_target("nucleus")
    step.show(nucleus.label("Nucleus", anchor="center", leader=False))  # a panel right on top
    names = [t.name for t in cell.hit_test(0, 220, 190)]
    assert names == ["nucleus", "cell"]
    assert [t.name for t in cell.hit_test(0, 150, 200)] == ["cell"]
    assert cell.hit_test(0, 580, 20) == ()


def test_taps_are_judged_on_the_step_as_shown(cell):
    step = cell.step("Moved")
    nucleus = cell.get_target("nucleus")
    step.restyle(nucleus, move=(0, -120))  # now centred at (220, 70), outside the cell
    step.restyle(cell.get_target("mitochondrion"), visible=False)
    step.ask("Tap the nucleus.", nucleus)
    assert cell.check_answer(0, 220, 70).correct
    assert not cell.check_answer(0, 220, 190).correct  # where it used to be
    hidden = cell.check_answer(0, 330, 252)  # the hidden mitochondrion's place
    assert hidden.tapped.name == "cell"


def test_feedback_names_what_was_tapped(cell):
    step = cell.step("Quiz")
    step.ask("Tap the nucleus.", cell.get_target("nucleus"))
    right = cell.check_answer(0, 220, 190)
    assert (right.correct, right.tapped.name, right.feedback) == (True, "nucleus", "Yes, that's the nucleus.")
    wrong = cell.check_answer(0, 330, 252)
    assert (wrong.correct, wrong.tapped.name) == (False, "mitochondrion")
    assert wrong.feedback == "That's the mitochondrion. Try again."
    miss = cell.check_answer(0, 580, 20)
    assert (miss.tapped, miss.feedback) == (None, "Not quite. Try again.")
    assert step.prompt.feedback("hint") == "Here it is: the nucleus."


def test_author_feedback_uses_placeholders_but_no_format(cell):
    step = cell.step("Quiz")
    step.ask("Tap the nucleus.", cell.get_target("nucleus"), correct="Right: {tapped} {holds DNA}",
             wrong="No, {tapped}. Look for {answer}.", hint="It is {answer}, the dark one.")
    assert cell.check_answer(0, 220, 190).feedback == "Right: the nucleus {holds DNA}"
    assert cell.check_answer(0, 330, 252).feedback == "No, the mitochondrion. Look for the nucleus."
    assert cell.check_answer(0, 580, 20).feedback == "No, that. Look for the nucleus."
    assert step.prompt.feedback("hint") == "It is the nucleus, the dark one."


def test_a_step_without_a_prompt_refuses_checking(cell):
    cell.step("Plain")
    with pytest.raises(ValidationError, match="no prompt"):
        cell.check_answer(0, 1, 1)


def test_kit_node_helpers_do_not_steal_the_name():
    lesson = Tutorial(Scene(600, 300, background=Color.white()))
    flow = Flowchart(lesson, origin=(120, 80))
    flow.node("start", "Start", at=(0, 0))
    goal = flow.node("finish", "Finish", at=(1, 1))
    step = lesson.step("Quiz")
    step.ask("Tap where it ends.", goal)
    start = lesson.check_answer(0, 120, 80)
    assert start.tapped.name == "start" and start.feedback == "That's the start. Try again."
    assert lesson.check_answer(0, 340, 190).correct


def test_descriptions_end_with_the_question(cell):
    first = cell.step("Quiz")
    first.ask("Tap the nucleus", cell.get_target("nucleus"))
    second = cell.step("Again")
    second.highlight(cell.get_target("cell"))
    second.ask("Tap the mitochondrion.", cell.get_target("mitochondrion"))
    assert cell.describe(0) == 'Quiz. The learner is asked: "Tap the nucleus."'
    assert cell.describe(1).endswith('Then the learner is asked: "Tap the mitochondrion."')


def test_lint_catches_hidden_untappable_and_given_away_answers(cell):
    hidden = cell.step("Hidden")
    nucleus = cell.get_target("nucleus")
    hidden.restyle(nucleus, visible=False).ask("Tap the nucleus.", nucleus)
    off = cell.step("Off")
    off.restyle(nucleus, move=(900, 0)).ask("Tap the nucleus.", nucleus)
    told = cell.step("Told")
    told.show(nucleus.label("Nucleus")).ask("Tap the nucleus.", nucleus)
    fine = cell.step("Fine")
    fine.ask("Tap the nucleus.", nucleus)
    codes = {(i.step, i.code) for i in cell.lint()}
    assert (0, "PROMPT_HIDDEN") in codes
    assert (1, "PROMPT_UNTAPPABLE") in codes
    assert (2, "PROMPT_GIVEAWAY") in codes
    assert not any(step == 3 and code.startswith("PROMPT") for step, code in codes)


def test_web_step_carries_the_prompt_by_drawable_id(cell):
    step = cell.step("Quiz")
    nucleus = cell.get_target("nucleus")
    step.ask("Tap the nucleus.", nucleus, attempts=2)
    payload = cell.web_step(0)["prompt"]
    assert payload["answers"] == [nucleus.drawable_id] and nucleus.drawable_id in cell.web_step(0)["svg"]
    assert payload["names"][nucleus.drawable_id] == "the nucleus"
    assert payload["correct"] == "Yes, that's {tapped}." and payload["miss"] == "Not quite. Try again."
    assert (payload["attempts"], payload["answer"], payload["helpers"]) == (2, "the nucleus", [])
    cell.step("No quiz")
    assert cell.web_step(1)["prompt"] is None


def test_saving_warns_that_prompts_are_not_kept(cell, tmp_path):
    cell.step("Quiz").ask("Tap the nucleus.", cell.get_target("nucleus"))
    with pytest.warns(LessonWarning, match=r"step\(s\) \[1\]"):
        path = cell.save_json(tmp_path / "quiz.tutordraw.json")
    loaded = Tutorial.load_json(path)
    assert loaded.steps[0].prompt is None
    loaded.steps[0].ask("Tap the nucleus.", loaded.get_target("nucleus"))  # asked again after loading
    with warnings.catch_warnings():
        warnings.simplefilter("error", LessonWarning)
        Tutorial(Scene(10, 10)).to_json()  # nothing to lose, no warning

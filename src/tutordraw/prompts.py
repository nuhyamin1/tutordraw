"""Interactive prompts: "tap the nucleus", answered on the picture itself.

A step may end with one prompt. The browser player holds the step at its
end until the learner taps an answer, and `Tutorial.check_answer` does the
same check in Python for apps that draw frames themselves. Both hit-test the
step's finished picture, so moved, hidden or zoomed artwork is judged as the
learner sees it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ValidationError
from .text import validate_annotation_text

DEFAULT_ATTEMPTS = 3
# Canvas px round text and equations that still count as tapping them, and
# how near a tap that hits nothing may land to a target and still count.
TEXT_PAD = 4.0
TAP_SLOP = 12.0
# Feedback templates. "{tapped}" becomes the tapped target's spoken name ("the
# cell wall") and "{answer}" the first answer's. The browser player fills them
# the same way from the names in the step payload, so both agree word for word.
CORRECT = "Yes, that's {tapped}."
WRONG = "That's {tapped}. Try again."
MISS = "Not quite. Try again."
HINT = "Here it is: {answer}."


@dataclass(frozen=True, eq=False)
class Prompt:
    """What a step asks, which targets answer it, and what the learner is told.

    `correct`, `wrong` and `hint` are the author's text or None for the
    defaults, and may use "{tapped}" and "{answer}".
    """

    text: str
    answers: tuple  # Targets
    correct: str | None = None
    wrong: str | None = None
    hint: str | None = None
    attempts: int = DEFAULT_ATTEMPTS

    def templates(self) -> dict[str, str]:
        """The four feedback templates this prompt uses."""
        return {"correct": self.correct or CORRECT, "wrong": self.wrong or WRONG,
                "miss": self.wrong or MISS, "hint": self.hint or HINT}

    def feedback(self, kind: str, tapped=None) -> str:
        """Fill one template: "correct", "wrong", "miss" (nothing tapped) or "hint"."""
        return fill(self.templates()[kind], tapped, self.answers[0])


def fill(template: str, tapped, answer) -> str:
    # Plain replacement, not str.format: author text may contain other braces.
    return template.replace("{tapped}", spoken(tapped)).replace("{answer}", spoken(answer))


@dataclass(frozen=True)
class Answer:
    """The outcome of one tap. `tapped` is the target hit, or None."""

    correct: bool
    tapped: object
    feedback: str


def spoken(target) -> str:
    """"the cell membrane" from a target named "cell_membrane"."""
    if target is None or not target.name:
        return "that"
    return "the " + target.name.replace("_", " ")


def make_prompt(step, text, answer, *, correct, wrong, hint, attempts) -> Prompt:
    from .model import Target

    font = step._tutorial.font is not None
    text = validate_annotation_text(text, allow_newlines=False, font=font)
    answers = answer if isinstance(answer, (tuple, list)) else (answer,)
    if not answers or not all(isinstance(a, Target) for a in answers):
        raise ValidationError("answer must be a target, or a tuple of targets that are all right")
    for target in answers:
        step._check_target(target)
    texts = [None if value is None else validate_annotation_text(value, allow_newlines=False, font=font)
             for value in (correct, wrong, hint)]
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not 1 <= attempts <= 10:
        raise ValidationError("attempts must be an integer from 1 to 10: wrong taps before the hint")
    return Prompt(text, tuple(dict.fromkeys(answers)), *texts, attempts)


def text_like(drawable) -> bool:
    """Is this read as a block of text: a Text, or (part of) a typeset equation?"""
    from drawcv import Text

    from .arrange import _kit

    node = drawable
    while node is not None:
        if isinstance(node, Text) or _kit(node) == "equation":
            return True
        node = getattr(node, "parent", None)
    return False


def zones(tutorial, composition) -> list[tuple]:
    """Every shown target's tap zone in a finished frame: (target, bounds, text-like), smallest first.

    What the forgiving rules in `hits` use, and what the browser player is sent
    to apply them identically.
    """
    from .adapters.drawcv import index_scene

    objects = index_scene(composition.scene)
    found, seen = [], set()
    for target in tutorial.targets:
        drawable = objects.get(target.drawable_id)
        if (target.drawable_id in seen or drawable is None or not drawable.effective_visible
                or drawable.effective_opacity <= 0.01):
            continue
        seen.add(target.drawable_id)
        found.append((target, drawable.get_bounds(), text_like(drawable)))
    return sorted(found, key=lambda zone: zone[1].width * zone[1].height)


def _distance(box, x: float, y: float) -> float:
    dx = max(box.left - x, 0.0, x - box.right)
    dy = max(box.top - y, 0.0, y - box.bottom)
    return (dx * dx + dy * dy) ** 0.5


def hits(tutorial, index: int, x: float, y: float) -> tuple:
    """Targets under canvas point (x, y) in the step's finished picture.

    Innermost first (a nucleus before the cell around it), topmost first
    among siblings. Annotations never block: a label over a target does not
    stop the tap reaching it. A kit's `<node>_shape` helper is dropped when
    its node was hit too, so feedback names the node.

    Forgiving, as a finger is: text and equations are tapped anywhere in
    their box (grown by TEXT_PAD), not only on the ink of a glyph, and come
    first, as they are drawn on top; and a tap that hits nothing counts as
    the nearest target within TAP_SLOP.
    """
    from .validation import finite_number

    x, y = finite_number(x, "x"), finite_number(y, "y")
    composition = tutorial._compose(index, 1.0)
    by_drawable = {}
    for target in tutorial.targets:
        by_drawable.setdefault(target.drawable_id, target)
    found: list = []
    # DrawCV's hit_test already lists enclosing groups after their children;
    # walking parents too keeps that true even for a group hit only by a child.
    for drawable in composition.scene.hit_test(x, y):
        node = drawable
        while node is not None:
            target = by_drawable.get(node.id)
            if target is not None and target not in found:
                found.append(target)
            node = getattr(node, "parent", None)
    areas = zones(tutorial, composition)
    boxed = [target for target, box, text in areas if text and _distance(box, x, y) <= TEXT_PAD]
    found = boxed + [target for target in found if target not in boxed]
    if not found:
        near = [(_distance(box, x, y), rank, target) for rank, (target, box, _) in enumerate(areas)]
        near = [entry for entry in near if entry[0] <= TAP_SLOP]
        if near:
            found = [min(near, key=lambda entry: entry[:2])[2]]
    names = {t.name for t in found}
    return tuple(t for t in found
                 if not (t.name and t.name.endswith("_shape") and t.name[:-6] in names))


def check(tutorial, index: int, x: float, y: float) -> Answer:
    prompt = tutorial.steps[index].prompt
    if prompt is None:
        raise ValidationError(f"Step {index + 1} has no prompt; add one with step.ask(...)")
    tapped = hits(tutorial, index, x, y)
    for target in tapped:
        if target in prompt.answers:
            return Answer(True, target, prompt.feedback("correct", target))
    first = tapped[0] if tapped else None
    return Answer(False, first, prompt.feedback("wrong" if first is not None else "miss", first))

def payload(tutorial, prompt: Prompt | None, composition=None) -> dict | None:
    """The prompt as the browser player needs it: answers and names by drawable ID.

    `zones` are the shown targets' boxes in the finished frame (see `zones`),
    [id, x, y, width, height, text-like], smallest first, with TEXT_PAD and
    TAP_SLOP, so the player forgives taps exactly as `hits` does.
    """
    if prompt is None:
        return None
    names, helpers = {}, []
    for target in tutorial.targets:
        if target.name and target.drawable_id not in names:
            names[target.drawable_id] = spoken(target)
    by_name = {t.name: t for t in tutorial.targets if t.name}
    for name, target in by_name.items():
        if name.endswith("_shape") and name[:-6] in by_name:
            helpers.append(target.drawable_id)
    return {"text": prompt.text, "answers": [t.drawable_id for t in prompt.answers],
            "answer": spoken(prompt.answers[0]), "attempts": prompt.attempts,
            **prompt.templates(), "names": names, "helpers": helpers,
            "zones": [[target.drawable_id, round(box.x, 2), round(box.y, 2), round(box.width, 2),
                       round(box.height, 2), text] for target, box, text in zones(tutorial, composition)]
            if composition is not None else [],
            "textPad": TEXT_PAD, "slop": TAP_SLOP}


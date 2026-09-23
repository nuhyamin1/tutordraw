"""Plain-English descriptions of steps, built from the lesson's structure.

For screen readers (alt text, and the player's live region) and for a model
checking that a step shows what it meant to say. Nothing is inferred from
pixels: every sentence comes from a target, annotation, mark or restyle, in the
order the viewer sees them appear.
"""

from __future__ import annotations

from .model import Callout, Mark, Target

# Named colours for "turns red". Nearest by weighted RGB distance; a name, not
# a measurement, so a small palette of everyday words is the point.
COLOURS = {
    "black": (0, 0, 0), "dark grey": (80, 80, 80), "grey": (150, 150, 150),
    "light grey": (210, 210, 210), "white": (255, 255, 255), "red": (200, 50, 45),
    "dark red": (130, 30, 30), "orange": (240, 140, 40), "yellow": (245, 215, 60),
    "brown": (140, 90, 50), "green": (60, 160, 70), "dark green": (30, 90, 40),
    "light green": (160, 215, 150), "blue": (50, 100, 210), "dark blue": (25, 40, 110),
    "light blue": (150, 195, 240), "purple": (130, 70, 180), "pink": (240, 150, 190),
}


def colour_name(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb

    def distance(other):
        dr, dg, db = r - other[0], g - other[1], b - other[2]
        return 2 * dr * dr + 4 * dg * dg + 3 * db * db
    return min(COLOURS, key=lambda name: distance(COLOURS[name]))


def _name(ref) -> str:
    if isinstance(ref, Target):
        if ref.name:
            return "the " + ref.name.replace("_", " ")
        return "an unnamed object"
    return f"the point ({ref[0]:g}, {ref[1]:g})"


def _join(parts: list[str]) -> str:
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _quoted(text: str | None, verb: str = "labelled") -> str:
    return f', {verb} "{text}"' if text else ""


def _direction(dx: float, dy: float) -> str:
    words = []
    if abs(dy) >= 1:
        words.append("down" if dy > 0 else "up")
    if abs(dx) >= 1:
        words.append("right" if dx > 0 else "left")
    return " and ".join(words)


def _mark(mark: Mark) -> str:
    refs = [_name(ref) for ref in mark.refs]
    options = mark.options
    if mark.kind == "arrow":
        source, destination = mark.refs
        if options["both"]:
            return f"A two-way arrow joins {refs[0]} and {refs[1]}{_quoted(mark.text)}."
        if not isinstance(source, Target):
            return f"An arrow points at {refs[1]}{_quoted(mark.text)}."
        if not isinstance(destination, Target):
            return f"An arrow points away from {refs[0]}{_quoted(mark.text)}."
        return f"An arrow goes from {refs[0]} to {refs[1]}{_quoted(mark.text)}."
    if mark.kind == "brace":
        return f"A brace groups {_join(refs)}{_quoted(mark.text)}."
    if mark.kind == "measure":
        value = f' as "{mark.text}"' if mark.text else ""
        if len(refs) == 1:
            extent = "width" if options["axis"] == "x" else "height"
            return f"The {extent} of {refs[0]} is marked{value}."
        kind = {"x": "horizontal distance", "y": "vertical distance", "free": "distance"}[options["axis"]]
        return f"The {kind} from {refs[0]} to {refs[1]} is marked{value}."
    if mark.kind == "angle":
        value = f' as "{mark.text}"' if mark.text else ""
        return f"The angle at {refs[0]} between {refs[1]} and {refs[2]} is marked{value}."
    return f"{refs[0][0].upper()}{refs[0][1:]} is numbered {options['n']}."


def describe_step(tutorial, index: int) -> str:
    step = tutorial.steps[index]
    prior = tutorial.steps[index - 1] if index else None
    moving = step.easing is not None
    opening: list[str] = []

    if step.camera is not None:
        opening.append(f"The view {'zooms' if moving else 'is zoomed'} in on "
                       f"{_join([_name(t) for t in step.camera.targets])}.")
    elif prior is not None and prior.camera is not None:
        opening.append("The view zooms back out to the whole scene." if moving
                       else "The whole scene is shown.")

    # Restyles are stored against the source drawing, but a viewer sees the
    # change from the previous step, so describe that difference, including
    # something going back to how the drawing has it.
    current = {r.target.id: r for r in step.restyles}
    earlier = {r.target.id: r for r in prior.restyles} if prior is not None else {}
    targets = {r.target.id: r.target for r in (*step.restyles, *(prior.restyles if prior else ()))}
    for target_id, target in targets.items():
        now, before = current.get(target_id), earlier.get(target_id)
        changes = []
        shown_now = now.visible if now is not None and now.visible is not None else True
        shown_before = before.visible if before is not None and before.visible is not None else True
        if shown_now != shown_before:
            changes.append("appears" if shown_now else "is hidden")
        move = now.move if now is not None and now.move else (0.0, 0.0)
        was = before.move if before is not None and before.move else (0.0, 0.0)
        heading = _direction(move[0] - was[0], move[1] - was[1])
        if heading and shown_now:
            back = "back " if move == (0.0, 0.0) else ""
            changes.append(f"{'slides' if moving else 'moves'} {back}{heading}")
        fill = now.fill if now is not None else None
        old_fill = before.fill if before is not None else None
        if fill != old_fill and shown_now:
            changes.append(f"turns {colour_name(fill)}" if fill is not None
                           else "returns to its original colour")
        opacity = now.opacity if now is not None else None
        old_opacity = before.opacity if before is not None else None
        if opacity != old_opacity and shown_now:
            level = 1.0 if opacity is None else opacity
            changes.append("fades out" if level == 0 else "is fully shown" if level >= 1
                           else f"fades to {round(level * 100)}%")
        if changes:
            who = _name(target)
            opening.append(f"{who[0].upper()}{who[1:]} {_join(changes)}.")

    if step._focus:
        focus = _join([_name(t) for t in step._focus])
        opening.append(f"Everything except {focus} is dimmed.")

    # Everything that appears, in the order the viewer sees it.
    events: list[tuple[float, int, str]] = []
    order = 0
    for highlight in step.highlights:
        style = "outlined" if highlight.shape == "outline" else "boxed"
        events.append((min(highlight.at, step.duration), order,
                       f"{_name(highlight.target)[0].upper()}{_name(highlight.target)[1:]} is {style}."))
        order += 1
    numbers = [m for m in step.marks if m.kind == "number"]
    for item in (*step.labels, *step.callouts, *step.marks):
        at = min(step.revealed_at(item), step.duration)
        if isinstance(item, Mark):
            if item.kind == "number" and len(numbers) > 1:
                continue  # Numbers read better as one sentence, below.
            sentence = _mark(item)
        elif isinstance(item, Callout):
            sentence = f'A note on {_name(item.target)} says: "{item.text}"'
            if not sentence.endswith((".", "!", "?", '"')):
                sentence += "."
        else:
            sentence = f'{_name(item.target)[0].upper()}{_name(item.target)[1:]} is labelled "{item.text}".'
        events.append((at, order, sentence))
        order += 1
    if len(numbers) > 1:
        at = min(min(step.revealed_at(m) for m in numbers), step.duration)
        named = _join([_name(m.refs[0]) for m in numbers])
        events.append((at, -1, f"{named[0].upper()}{named[1:]} are numbered "
                               f"{_join([str(m.options['n']) for m in numbers])}."))
    events.sort(key=lambda event: (event[0], event[1]))

    sentences = [f"{step.title}."] if step.title.strip() else []
    sentences += opening
    last = None
    for at, _, sentence in events:
        if last is not None and at > last:
            sentence = "Then " + sentence[0].lower() + sentence[1:]
        sentences.append(sentence)
        last = at
    return " ".join(sentences)


def describe_lesson(tutorial) -> str:
    heading = f"{tutorial.title}. " if tutorial.title.strip() else ""
    count = len(tutorial.steps)
    heading += f"{count} step{'s' if count != 1 else ''}."
    parts = [heading] + [f"Step {i + 1}: {describe_step(tutorial, i)}" for i in range(count)]
    return "\n".join(parts)

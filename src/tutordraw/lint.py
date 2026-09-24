"""Find what makes a lesson hard to read, in a form a model can act on.

Lint never changes rendering: it composes each step exactly as rendering does
and inspects the result. Every issue has a stable `code`, so a caller can
branch on it, and a `fix` phrased as a concrete change to the authoring call.
"""

from dataclasses import dataclass, field
from itertools import combinations
import warnings

from drawcv import BoundingBox, OpenCVRenderer, Point

from .adapters.drawcv import index_scene, stroke_boxes
from .collision import outside_area, overlap_area
from .composition import AnnotationLayout, Composition
from .errors import LayoutWarning
from .layout import measure_label

# Tunables, kept together so their meaning is reviewable in one place.
MIN_CONTRAST = 4.5  # WCAG AA for body text
MIN_LINE_HEIGHT = 12.0  # px; below this text is hard to read on a phone
MAX_ANNOTATIONS = 6  # visible at once in one beat
MAX_CALLOUT_WORDS = 40
COVER_FRACTION = 0.08  # of a panel's area lying on a target's actual shape
SAMPLE_STEP = 3.0  # px between hit-test samples
HALO_ENOUGH = 2.0  # px of halo that separates bare text from the art behind it
# Areas below one square pixel are floating-point noise, not a real overlap:
# outside_area subtracts an intersection from a box and can leave 1e-11.
AREA_EPSILON = 1.0

SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Issue:
    """One problem in one step. `code` is stable; `message` and `fix` are prose."""

    code: str
    severity: str
    step: int
    step_title: str
    message: str
    fix: str
    targets: tuple[str, ...] = ()
    annotations: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "step": self.step,
                "step_title": self.step_title, "message": self.message, "fix": self.fix,
                "targets": list(self.targets), "annotations": list(self.annotations)}


def _shrink(box: BoundingBox, by: float) -> BoundingBox:
    return BoundingBox(box.x + by, box.y + by, max(box.width - 2 * by, 0), max(box.height - 2 * by, 0))


def _segment_hits_box(a: Point, b: Point, box: BoundingBox) -> bool:
    """Liang-Barsky: does segment a-b pass through the box's interior?"""
    if box.width <= 0 or box.height <= 0:
        return False
    t0, t1 = 0.0, 1.0
    dx, dy = b.x - a.x, b.y - a.y
    for p, q in ((-dx, a.x - box.x), (dx, box.x + box.width - a.x),
                 (-dy, a.y - box.y), (dy, box.y + box.height - a.y)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _segments_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Proper crossing only: touching at an endpoint (a shared anchor) is fine."""
    def cross(o, p, q):
        return (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x)
    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    eps = 1e-6
    return ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
           ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps))


def _luminance(bgr) -> float:
    def channel(value):
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    b, g, r = (channel(v) for v in bgr)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(first_bgr, second_bgr) -> float:
    light, dark = sorted((_luminance(first_bgr), _luminance(second_bgr)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _covered_fraction(panel: BoundingBox, drawable, ink=None) -> float:
    """Share of the panel lying on the drawable's real shape, not its bounds.

    `ink` is the drawable's stroke boxes when it is an unfilled stroke: then
    the overlap with those boxes is the answer, and DrawCV's contains_point
    (which re-flattens a path on every call) is not needed.
    """
    bounds = drawable.get_bounds()
    if overlap_area(panel, bounds) <= 0:
        return 0.0
    if ink is not None:
        area = panel.width * panel.height
        return min(1.0, sum(overlap_area(panel, box) for box in ink) / area) if area else 0.0
    x0, y0 = max(panel.x, bounds.x), max(panel.y, bounds.y)
    x1 = min(panel.x + panel.width, bounds.x + bounds.width)
    y1 = min(panel.y + panel.height, bounds.y + bounds.height)
    hits = 0
    y = y0 + SAMPLE_STEP / 2
    while y < y1:
        x = x0 + SAMPLE_STEP / 2
        while x < x1:
            hits += bool(drawable.contains_point(Point(x, y)))
            x += SAMPLE_STEP
        y += SAMPLE_STEP
    # Scale the sampled hits back to the whole panel's area.
    total = (panel.width * panel.height) / (SAMPLE_STEP * SAMPLE_STEP)
    return hits / total if total else 0.0


def _leader_hits(annotation: AnnotationLayout, drawable, ink=None) -> bool:
    """Does the leader pass over this shape somewhere away from its ends?"""
    start, end = annotation.leader
    if ink is not None:
        # Trim the ends, as the sampling below skips them, then test the ink boxes.
        length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5 or 1.0
        trim = min(4.0 / length, 0.5)
        a = Point(start.x + (end.x - start.x) * trim, start.y + (end.y - start.y) * trim)
        b = Point(end.x - (end.x - start.x) * trim, end.y - (end.y - start.y) * trim)
        return any(_segment_hits_box(a, b, box) for box in ink)
    length = ((end.x - start.x) ** 2 + (end.y - start.y) ** 2) ** 0.5
    steps = int(length // 2)
    for i in range(2, steps - 1):
        t = i / steps
        if drawable.contains_point(Point(start.x + (end.x - start.x) * t,
                                         start.y + (end.y - start.y) * t)):
            return True
    return False


def _mark_name(mark) -> str:
    return repr(mark.text) if mark.text else "on " + ", ".join(repr(t) for t in mark.targets)


def lint_step(tutorial, index: int) -> list[Issue]:
    step = tutorial.steps[index]
    title = step.title

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", LayoutWarning)
        composition: Composition = tutorial._compose(index, 1.0)
    issues: list[Issue] = []

    def add(code, severity, message, fix, targets=(), annotations=()):
        issues.append(Issue(code, severity, index, title, message, fix,
                            tuple(targets), tuple(annotations)))

    for warning in caught:
        if issubclass(warning.category, LayoutWarning) and "could not be placed" in str(warning.message):
            add("UNPLACEABLE", "warning", str(warning.message),
                "There is no free space for it. Shorten the text, reveal it later "
                "with at=, move it to its own step, or give the canvas more room.")

    objects = index_scene(composition.scene)
    drawables = {name: objects[drawable_id] for name, drawable_id in composition.drawables.items()}
    # Unfilled strokes are judged by their ink boxes, computed once per step.
    ink = {name: stroke_boxes(drawable) for name, drawable in drawables.items()}
    width, height = composition.scene.width, composition.scene.height
    annotations = composition.annotations
    labels = {label.id: label for label in (*step.labels, *step.callouts)}

    for a in annotations:
        if outside_area(a.panel, width, height) > AREA_EPSILON:
            add("OFF_CANVAS", "error",
                f"{a.kind.capitalize()} {a.text!r} extends past the canvas edge.",
                f"Anchor it on a side of {a.target!r} that faces into the canvas, "
                "reduce gap, or shorten it (max_width= for a callout).",
                [a.target], [a.text])

    for m in composition.marks:
        if m.empty:
            add("EMPTY_MARK", "warning",
                f"The {m.kind} {_mark_name(m)} has nothing to draw: its ends share a centre.",
                "Connect targets that sit apart, or start the arrow from a point outside "
                "the shape, e.g. connect((x, y), target).", m.targets, [m.text] if m.text else [])
            continue
        if outside_area(m.bounds, width, height) > AREA_EPSILON:
            add("OFF_CANVAS", "error",
                f"The {m.kind} {_mark_name(m)} extends past the canvas edge.",
                "Pick another side or a smaller offset/radius for it, or give the "
                "canvas more room.", m.targets, [m.text] if m.text else [])

    # Every caption panel in the frame: annotations' and marks' alike.
    panels = [(a.panel, a.text, (a.target,)) for a in annotations]
    panels += [(m.panel, m.text, m.targets) for m in composition.marks if m.panel is not None]
    for (box_a, text_a, targets_a), (box_b, text_b, targets_b) in combinations(panels, 2):
        if overlap_area(box_a, box_b) > AREA_EPSILON:
            add("ANNOTATION_OVERLAP", "error",
                f"{text_a!r} and {text_b!r} overlap each other.",
                "Give one a different anchor or side, reveal them at different times "
                "with at=, or split them across steps. A mark's caption moves with "
                "its offset, radius, bend or side.",
                [*targets_a, *targets_b], [text_a, text_b])

    for a in annotations:
        for name, drawable in drawables.items():
            share = _covered_fraction(a.panel, drawable, ink[name])
            if share >= COVER_FRACTION:
                add("COVERS_TARGET", "warning",
                    f"{share:.0%} of {a.text!r} sits on top of target {name!r}, hiding it.",
                    f"Move it off {name!r}: try another anchor or a larger gap on "
                    f"{a.target!r}.", [a.target, name], [a.text])

    for a in annotations:
        if a.leader is None:
            continue
        for b in annotations:
            if b is not a and _segment_hits_box(*a.leader, _shrink(b.panel, 1)):
                add("LEADER_CROSSES_PANEL", "warning",
                    f"The leader of {a.text!r} runs through {b.text!r}.",
                    f"Anchor {a.text!r} on the side of {a.target!r} nearest its panel, "
                    "or place the two on different sides.", [a.target, b.target], [a.text, b.text])
        start = a.leader[0]
        for name, drawable in drawables.items():
            # Skip the shape the leader starts on and anything that contains it.
            inside = (any(box.contains(start) for box in ink[name]) if ink[name] is not None
                      else drawable.contains_point(start))
            if name == a.target or inside:
                continue
            if _leader_hits(a, drawable, ink[name]):
                add("LEADER_CROSSES_TARGET", "warning",
                    f"The leader of {a.text!r} passes over target {name!r}, so it reads "
                    f"as pointing there.",
                    f"Anchor {a.text!r} on a side of {a.target!r} facing away from "
                    f"{name!r}.", [a.target, name], [a.text])

    led = [a for a in annotations if a.leader is not None]
    for a, b in combinations(led, 2):
        if _segments_cross(*a.leader, *b.leader):
            add("LEADERS_CROSS", "warning",
                f"The leaders of {a.text!r} and {b.text!r} cross.",
                "Swap their anchors so each panel sits on its own target's side.",
                [a.target, b.target], [a.text, b.text])

    theme = tutorial.theme
    text_bgr = tuple(reversed(theme.text_color))
    backdrop = None
    for a in annotations:
        label = labels.get(a.id)
        if label is None:
            continue
        measured = measure_label(label, theme, tutorial.font)
        if measured.line_height < MIN_LINE_HEIGHT:
            add("TEXT_TOO_SMALL", "warning",
                f"{a.text!r} is {measured.line_height:.0f} px tall.",
                f"Use font_scale of at least {theme.font_scale:g} (the theme default).",
                [a.target], [a.text])
        # A halo of a couple of pixels puts panel_color right behind every glyph.
        if a.boxed or theme.halo_width >= HALO_ENOUGH:
            ratio = contrast(text_bgr, tuple(reversed(theme.panel_color)))
        else:
            if backdrop is None:
                backdrop = OpenCVRenderer().render(
                    tutorial._compose(index, 1.0, draw_annotations=False).scene).to_numpy()
            x0, y0 = max(int(a.panel.x), 0), max(int(a.panel.y), 0)
            x1 = min(int(a.panel.x + a.panel.width), width)
            y1 = min(int(a.panel.y + a.panel.height), height)
            region = backdrop[y0:y1, x0:x1, :3].reshape(-1, 3)
            if not len(region):
                continue
            # The worst tenth of the backdrop decides it, not the average.
            ratios = sorted(contrast(text_bgr, pixel) for pixel in region[::7])
            ratio = ratios[len(ratios) // 10]
        if ratio < MIN_CONTRAST:
            add("LOW_CONTRAST", "warning",
                f"{a.text!r} has contrast {ratio:.1f}:1 against what is behind it "
                f"(needs {MIN_CONTRAST}:1).",
                "Keep its panel (box=True), give it a halo (Theme halo_width >= 2), "
                "or change Theme text_color/panel_color."
                if not a.boxed else "Change Theme text_color or panel_color.",
                [a.target], [a.text])
        if a.kind == "callout" and len(a.text.split()) > MAX_CALLOUT_WORDS:
            add("LONG_CALLOUT", "info",
                f"The callout on {a.target!r} is {len(a.text.split())} words.",
                f"Keep a callout under {MAX_CALLOUT_WORDS} words; say the rest in "
                "narration or split it across steps.", [a.target], [a.text])

    shown = len(annotations) + len(composition.marks)
    if shown > MAX_ANNOTATIONS:
        add("BUSY_STEP", "info",
            f"{shown} annotations and marks are visible at once.",
            f"Keep a beat to {MAX_ANNOTATIONS} or fewer: split the step, or introduce "
            "them one at a time with show(..., at=seconds).",
            annotations=[a.text for a in annotations])

    if step.prompt is not None:
        _lint_prompt(tutorial, index, step, composition, objects, labels, add)

    order = {severity: i for i, severity in enumerate(SEVERITIES)}
    return sorted(issues, key=lambda issue: order[issue.severity])


def _lint_prompt(tutorial, index, step, composition, objects, labels, add) -> None:
    """A prompt fails if the learner cannot see or tap its answer, or is told it."""
    from .prompts import hits

    question = step.prompt.text
    for answer in step.prompt.answers:
        name = answer.name or answer.id
        drawable = objects.get(answer.drawable_id)
        if drawable is None or not drawable.effective_visible or drawable.effective_opacity < 0.15:
            add("PROMPT_HIDDEN", "error",
                f"The answer {name!r} to {question!r} is hidden or nearly transparent in this step.",
                "Show it in this step (restyle it visible, or leave it out of dim_others), "
                "or ask about something the learner can see.", [name])
            continue
        # Tap a grid across its bounds, as a learner would, and see if any lands.
        box = drawable.get_bounds()
        points = [(box.left + box.width * (i + 0.5) / 5, box.top + box.height * (j + 0.5) / 5)
                  for i in range(5) for j in range(5)]
        width, height = composition.scene.width, composition.scene.height
        onscreen = [(x, y) for x, y in points if 0 <= x < width and 0 <= y < height]
        if not any(answer in hits(tutorial, index, x, y) for x, y in onscreen):
            add("PROMPT_UNTAPPABLE", "error",
                f"The answer {name!r} to {question!r} cannot be tapped: it is off the canvas "
                "or too small to hit.",
                "Ask about a target that is on the canvas and at least a few pixels across; "
                "for a thin line, ask about a larger shape near it.", [name])
    for label in labels.values():
        if label.target in step.prompt.answers:
            add("PROMPT_GIVEAWAY", "warning",
                f"{label.text!r} labels {label.target.name or label.target.id!r}, the answer to "
                f"{question!r}, in the same step.",
                "Show that label in the next step instead, as the reveal after the answer.",
                [label.target.name or label.target.id], [label.text])

"""Deterministic annotation placement: off each other, off the edges, on canvas.

The resolver is discrete on purpose. A force-based push-apart would give every
panel a position that depends on every other panel's, so an animated step would
jitter as its targets move. Here a label picks one of a ranked list of
candidate placements, and that choice is made once per step from the step's
**final** geometry, not per frame. See `plan_annotations`.
"""

from dataclasses import dataclass
from typing import Iterator, Sequence
import warnings

from drawcv import BoundingBox, Drawable

from .adapters.drawcv import stroke_boxes
from .errors import LayoutWarning
from .layout import (Measured, Placement, anchor_points, clamp_panel, measure_label,
                     place_panel)
from .model import Step
from .themes import Theme

# Sides a label may be moved to. "center" sits on the artwork, so a label is
# only ever placed there when its author asked for it.
SIDES = ("right", "bottom", "left", "top")
# Offsets perpendicular to the anchor, in whole panels: stay, then fan outward.
SLOTS = (0, 1, -1, 2, -2, 3, -3)
# Gap multipliers, tried only once the near ring around a target is full.
RINGS = (1.0, 1.5, 2.25)


def overlap_area(box: BoundingBox, other: BoundingBox, margin: float = 0.0) -> float:
    """Area by which `box`, grown by `margin` on every side, intrudes into `other`."""
    wide = min(box.right + margin, other.right) - max(box.left - margin, other.left)
    tall = min(box.bottom + margin, other.bottom) - max(box.top - margin, other.top)
    return wide * tall if wide > 0 and tall > 0 else 0.0


def outside_area(box: BoundingBox, width: float, height: float) -> float:
    """How much of a panel falls off the canvas."""
    return box.width * box.height - overlap_area(box, BoundingBox(0, 0, width, height))


def union(first: BoundingBox, second: BoundingBox) -> BoundingBox:
    """The box covering both, which for a translation contains the whole sweep."""
    left, top = min(first.left, second.left), min(first.top, second.top)
    return BoundingBox(left, top, max(first.right, second.right) - left,
                       max(first.bottom, second.bottom) - top)


@dataclass(frozen=True)
class Request:
    """One annotation asking to be placed, in the step's final geometry."""

    key: str
    text: str
    target_id: str
    anchor: str
    gap: float
    offset: tuple[float, float]
    points: dict
    measured: Measured
    # True when the author anchored at "center" and so asked for the panel to
    # sit on its own target; that target then stops being an obstacle for it.
    covers_target: bool = False
    # The same anchor points at the other end of an animated step, so a panel
    # is judged over the whole path it travels. None when the step is a cut.
    sweep_points: dict | None = None


def _sides(authored: str) -> tuple[str, ...]:
    """Alternative anchors, authored first, then a fixed rotation."""
    if authored not in SIDES:
        return (authored, *SIDES)
    index = SIDES.index(authored)
    return SIDES[index:] + SIDES[:index]


def candidates(request: Request, margin: float) -> Iterator[Placement]:
    """Yield placements nearest to the author's intent first.

    Rank 0 is exactly what the author wrote. Sides are exhausted before a label
    slides along one, so several labels on one small target fan around it
    instead of stacking in a column.
    """
    w, h = request.measured.width, request.measured.height
    for ring in RINGS:
        reach = (ring - 1.0) * request.gap
        for slot in SLOTS:
            for anchor in _sides(request.anchor):
                if anchor in ("top", "bottom"):
                    dx, dy = slot * (w + margin), 0.0
                else:
                    dx, dy = 0.0, slot * (h + margin)
                if anchor == "left":
                    dx -= reach
                elif anchor == "top":
                    dy -= reach
                elif anchor == "bottom":
                    dy += reach
                else:  # right and center both place the panel to the right.
                    dx += reach
                yield Placement(anchor, dx, dy)


def _panel_at(points: dict, request: Request, placement: Placement,
              width: float, height: float) -> BoundingBox:
    panel = place_panel(points[placement.anchor], placement.anchor,
                        request.measured.width, request.measured.height, request.gap,
                        (request.offset[0] + placement.dx, request.offset[1] + placement.dy))
    return clamp_panel(panel, width, height)


def panel_for(request: Request, placement: Placement, width: float, height: float) -> BoundingBox:
    """The panel a placement produces, clamped exactly as the renderer will."""
    return _panel_at(request.points, request, placement, width, height)


def footprint(request: Request, placement: Placement, width: float, height: float) -> BoundingBox:
    """Every pixel this panel occupies during the step, not just at its end.

    Resolving against the end state alone is not enough: a target that slides
    *past* another label would drag its panel straight through it on the way.
    Judging the swept box instead keeps one frame-invariant decision that also
    holds in the middle. For a hard cut there is no middle and this is the panel.
    """
    panel = panel_for(request, placement, width, height)
    if request.sweep_points is None:
        return panel
    return union(panel, _panel_at(request.sweep_points, request, placement, width, height))


def resolve(requests: Sequence[Request], *, artwork: dict[str, BoundingBox],
            blockers: dict[str, BoundingBox] | None = None, width: float, height: float,
            margin: float = 6.0, preferred: dict[str, tuple[Placement, float]] | None = None,
            settled: dict[str, BoundingBox] | None = None,
            costs: dict[str, float] | None = None) -> dict[str, Placement]:
    """Place each annotation in order, never displacing an already-placed one.

    Requests are considered in registration order, so the first annotation keeps
    its authored placement and the same lesson always resolves identically.
    Candidates are scored lexicographically: panels must not overlap anything
    solid or leave the canvas, then they should avoid covering artwork, and
    ties go to the candidate closest to what the author asked for.

    `preferred` maps a request's key to where it was in the previous step and
    how much artwork it covered there. It is kept when nothing solid is in
    its way over the whole step and it covers no more of the artwork where
    the step ends (`settled`, the end-state boxes; `artwork` itself) than it
    did: a label stays put while something only passes through its place,
    rather than leaping across the canvas, and moves once something new
    comes to rest on it. `costs`, when given, receives how much end-state
    artwork each chosen placement covers, for the next step to compare with.
    """
    blockers = blockers or {}
    preferred = preferred or {}
    settled = artwork if settled is None else settled
    placed: list[BoundingBox] = []
    chosen: dict[str, Placement] = {}
    for request in requests:
        skip = request.target_id if request.covers_target else None
        solid = [box for key, box in blockers.items() if key != skip]
        def covered(placement):
            end = panel_for(request, placement, width, height)
            return sum(overlap_area(end, box) for key, box in settled.items() if key.split("#")[0] != skip)

        before, cost = preferred.get(request.key, (None, 0.0))
        if before is not None:
            panel = footprint(request, before, width, height)
            hard = (sum(overlap_area(panel, other, margin) for other in placed)
                    + sum(overlap_area(panel, other, margin) for other in solid)
                    + outside_area(panel, width, height))
            soft = covered(before)
            if hard <= 0 and soft <= cost + 1.0:  # a square pixel of rounding
                placed.append(panel)
                chosen[request.key] = before
                if costs is not None:
                    costs[request.key] = soft
                continue
        best: tuple[tuple[float, float, int], Placement, BoundingBox, float] | None = None
        for rank, placement in enumerate(candidates(request, margin)):
            panel = footprint(request, placement, width, height)
            crowded = (sum(overlap_area(panel, other, margin) for other in placed)
                       + sum(overlap_area(panel, other, margin) for other in solid))
            hard = crowded + outside_area(panel, width, height)
            soft = sum(overlap_area(panel, box)
                       for key, box in artwork.items() if key.split("#")[0] != skip)
            score = (hard, soft, rank)
            if best is None or score < best[0]:
                best = (score, placement, panel, crowded)
            if not hard and not soft:
                break  # The authored placement is usually free; stop at the first.
        assert best is not None  # candidates() always yields.
        _, placement, panel, crowded = best
        if crowded:
            # Off-canvas is reported by label_artwork against the final panel.
            warnings.warn(f"Label {request.text!r} could not be placed clear of "
                          "other annotations", LayoutWarning, stacklevel=4)
        placed.append(panel)
        chosen[request.key] = placement
        if costs is not None:
            costs[request.key] = covered(placement)
    return chosen


def plan_annotations(step: Step, objects: dict[str, Drawable], target_ids: Sequence[str], *,
                     width: float, height: float, theme: Theme, font=None,
                     previous: Step | None = None, progress: float = 1.0,
                     camera_at=None, mark_boxes=None,
                     preferred: dict[str, tuple[Placement, float]] | None = None,
                     costs: dict[str, float] | None = None
                     ) -> dict[str, tuple[Placement, Measured]]:
    """Decide every annotation's placement once, from the step's final geometry.

    Two things are deliberately ignored, both so a frame's placement never
    depends on which frame it is:

    - `progress`, except to undo it. Resolving against the end state means an
      animated step keeps one placement throughout, instead of swapping a label
      to the other side of its target halfway through the move.
    - reveal delays. Every annotation holds its slot from the first frame, so
      nothing already on screen shifts when a delayed one appears.

    The returned nudge is relative to the authored offset, so the panel is still
    built from live bounds each frame and a moved target keeps its label.

    `camera_at(t)` holds the camera at the step's end (1) or start (0) while
    bounds are measured, so a zoom does not move the labels' slots either.
    `mark_boxes(bounds)` returns the step's marks at those bounds, as blockers.
    `preferred` maps a label's ID to its placement in the previous step and
    the artwork it covered there, which it keeps while nothing new lands on
    it; `costs` receives the same for this step's placements (see `resolve`).
    """
    from contextlib import nullcontext
    from .attention import final_bounds, residual_moves

    annotations = (*step.labels, *step.callouts)
    if not annotations:
        return {}
    wanted = (set(target_ids) | {a.target.drawable_id for a in annotations}
              | {h.target.drawable_id for h in step.highlights}
              | {ref.drawable_id for mark in step.marks for ref in mark.refs
                 if hasattr(ref, "drawable_id")})
    held = camera_at or (lambda t: nullcontext())
    with held(1.0):
        bounds = final_bounds(objects, wanted, residual_moves(step, previous, progress))
        marks = mark_boxes(bounds) if mark_boxes is not None else []
        # Unfilled strokes block only along their ink; chunks are measured now
        # and shifted to where each target ends up, as its bounds were.
        chunks = {}
        for key in target_ids:
            if key in bounds and key in objects:
                pieces = stroke_boxes(objects[key])
                if pieces:
                    now = objects[key].get_bounds()
                    dx, dy = bounds[key].x - now.x, bounds[key].y - now.y
                    chunks[key] = [BoundingBox(b.x + dx, b.y + dy, b.width, b.height) for b in pieces]
    # An animated step also has a start, and its targets sweep between the two.
    started = None
    if step.easing is not None:
        with held(0.0):
            started = final_bounds(objects, wanted, residual_moves(step, previous, progress, 0.0))
    swept = bounds if started is None else {
        key: union(box, started[key]) for key, box in bounds.items()}
    requests, measured = [], {}
    for annotation in annotations:
        measured[annotation.id] = measure_label(annotation, theme, font)
        target_id = annotation.target.drawable_id
        requests.append(Request(
            annotation.id, annotation.text, target_id,
            annotation.anchor, annotation.gap, annotation.offset,
            anchor_points(bounds[target_id]), measured[annotation.id],
            annotation.anchor == "center",
            None if started is None else anchor_points(started[target_id])))
    highlights = {}
    for highlight in step.highlights:
        box, pad = swept[highlight.target.drawable_id], highlight.padding
        highlights[highlight.target.drawable_id] = BoundingBox(
            box.x - pad, box.y - pad, box.width + 2 * pad, box.height + 2 * pad)
    highlights.update({f"mark:{i}": box for i, box in enumerate(marks)})
    artwork, settled = {}, {}
    # Words in the drawing (titles, tick numbers, captions) are worth keeping
    # readable even when nobody registered them: covering them is a soft cost.
    # Annotations are not in the scene yet, so every Text here is artwork.
    from drawcv import Text
    for key, obj in objects.items():
        if isinstance(obj, Text) and key not in bounds and obj.visible and obj.text.strip():
            artwork[f"text:{key}"] = settled[f"text:{key}"] = obj.get_bounds()
    for key in target_ids:
        if key not in swept:
            continue
        if key in chunks:
            settled.update({f"{key}#{i}": box for i, box in enumerate(chunks[key])})
        else:
            settled[key] = bounds[key]
        # A stroke blocks along its ink, unless it moves in this step: then along its whole sweep.
        if key in chunks and (started is None or started[key] == bounds[key]):
            artwork.update({f"{key}#{i}": box for i, box in enumerate(chunks[key])})
        else:
            artwork[key] = swept[key]
    chosen = resolve(requests,
                     artwork=artwork,
                     blockers=highlights, width=width, height=height,
                     margin=theme.collision_margin, preferred=preferred, settled=settled, costs=costs)
    return {key: (placement, measured[key]) for key, placement in chosen.items()}

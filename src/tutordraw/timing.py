"""Deterministic hard-cut playback of independently rendered tutorial steps."""

from __future__ import annotations

from bisect import bisect_right
import math
from typing import TYPE_CHECKING, Iterator

from drawcv import Canvas

from .errors import ValidationError
from .validation import finite_number

if TYPE_CHECKING:
    from .tutorial import Tutorial


def boundaries(tutorial: Tutorial) -> tuple[float, ...]:
    ends = []
    total = 0.0
    for step in tutorial.steps:
        end = finite_number(total + step.duration + step.pause, "total duration")
        if end <= total:
            raise ValidationError("Step timing is too small relative to total duration")
        ends.append(end)
        total = end
    return tuple(ends)


def step_at_time(tutorial: Tutorial, time: float) -> int:
    seconds = finite_number(time, "time", minimum=0)
    ends = boundaries(tutorial)
    if not ends:
        raise ValidationError("Timed rendering requires at least one step")
    if seconds > ends[-1]:
        raise ValidationError(f"time must be between 0 and {ends[-1]}")
    # Intervals are [start, end); the final endpoint shows the last step.
    return min(bisect_right(ends, seconds), len(ends) - 1)


def render_frames(tutorial: Tutorial, *, fps: int, alpha: bool) -> Iterator[Canvas]:
    if isinstance(fps, bool) or not isinstance(fps, int) or fps <= 0:
        raise ValidationError("fps must be a positive integer")
    if not isinstance(alpha, bool):
        raise ValidationError("alpha must be a boolean")
    total = tutorial.duration
    if total == 0:
        raise ValidationError("Timed rendering requires at least one step")
    count = math.ceil(finite_number(total * fps, "duration * fps"))

    def frames():
        for index in range(count):
            # Each render produces an independent Canvas. Do not retain all frames.
            yield tutorial.render_at_time(index / fps, alpha=alpha)

    return frames()

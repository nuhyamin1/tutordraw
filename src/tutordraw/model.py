"""Small authoring model for independent tutorial steps."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from .errors import ValidationError

if TYPE_CHECKING:
    from .tutorial import Tutorial

Anchor = Literal["left", "right", "top", "bottom", "center"]


def finite_number(value: float, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a finite number")
    if not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValidationError(f"{name} must be finite and >= {minimum}")
    return float(value)


@dataclass(frozen=True, eq=False)
class Label:
    """Immutable label definition. Create with Target.label()."""

    target: Target
    text: str
    anchor: Anchor
    leader: bool
    gap: float
    offset: tuple[float, float]
    font_scale: float
    padding: float
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True, eq=False)
class Target:
    """A reference to an existing drawable. Create with Tutorial.target()."""

    _tutorial: Tutorial = field(repr=False)
    drawable_id: str
    name: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def label(
        self, text: str, *, anchor: Anchor = "right", leader: bool = True,
        gap: float = 32, offset: tuple[float, float] = (0, 0),
        font_scale: float = 0.7, padding: float = 10,
    ) -> Label:
        """Define a printable-ASCII, single-line label; show it via Step.show()."""
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("Label text must be a nonempty string")
        if any(ord(c) < 32 or ord(c) > 126 for c in text):
            raise ValidationError("M1 labels support printable ASCII on one line only")
        if anchor not in ("left", "right", "top", "bottom", "center"):
            raise ValidationError(f"Unsupported anchor: {anchor!r}")
        if not isinstance(leader, bool):
            raise ValidationError("leader must be a boolean")
        if not isinstance(offset, (tuple, list)) or len(offset) != 2:
            raise ValidationError("offset must contain two finite numbers")
        xy = tuple(finite_number(v, "offset") for v in offset)
        scale = finite_number(font_scale, "font_scale", minimum=0)
        if scale == 0 or scale > 10:
            raise ValidationError("font_scale must be > 0 and <= 10")
        label = Label(self, text, anchor, leader,
                      finite_number(gap, "gap", minimum=0), xy, scale,
                      finite_number(padding, "padding", minimum=0))
        self._tutorial._labels[label.id] = label
        return label


class Step:
    """An independent collection of visible labels. Create with Tutorial.step()."""

    def __init__(self, tutorial: Tutorial, title: str):
        self._tutorial = tutorial
        self.title = title
        self._labels: list[Label] = []

    @property
    def labels(self) -> tuple[Label, ...]:
        return tuple(self._labels)

    def show(self, *labels: Label) -> Step:
        """Show registered labels, without inheriting any other step's state."""
        for label in labels:
            if not isinstance(label, Label) or self._tutorial._labels.get(label.id) is not label:
                raise ValidationError("Label must belong to this tutorial")
        for label in labels:
            if label not in self._labels:
                self._labels.append(label)
        return self

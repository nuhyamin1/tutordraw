"""Immutable presentation defaults."""

from dataclasses import dataclass

from .errors import ValidationError
from .validation import finite_number, rgb


@dataclass(frozen=True)
class Theme:
    text_color: tuple[int, int, int] = (28, 43, 65)
    panel_color: tuple[int, int, int] = (255, 255, 255)
    border_color: tuple[int, int, int] = (194, 207, 223)
    leader_color: tuple[int, int, int] = (75, 104, 140)
    highlight_color: tuple[int, int, int] = (226, 146, 33)
    font_scale: float = 0.7
    padding: float = 10
    gap: float = 32
    leader_width: float = 2
    border_width: float = 1
    highlight_width: float = 3
    highlight_padding: float = 8
    callout_width: float = 260
    line_spacing: float = 1.35
    dim_opacity: float = 0.25

    def __post_init__(self) -> None:
        for name in ("text_color", "panel_color", "border_color", "leader_color", "highlight_color"):
            rgb(getattr(self, name), name)
        for name in ("padding", "gap", "highlight_padding"):
            finite_number(getattr(self, name), name, minimum=0)
        for name in ("leader_width", "border_width", "highlight_width", "callout_width"):
            if finite_number(getattr(self, name), name, minimum=0) == 0:
                raise ValidationError(f"{name} must be positive")
        scale = finite_number(self.font_scale, "font_scale", minimum=0)
        if not 0 < scale <= 10:
            raise ValidationError("font_scale must be > 0 and <= 10")
        finite_number(self.line_spacing, "line_spacing", minimum=1)
        if not 0 <= finite_number(self.dim_opacity, "dim_opacity") <= 1:
            raise ValidationError("dim_opacity must be between 0 and 1")

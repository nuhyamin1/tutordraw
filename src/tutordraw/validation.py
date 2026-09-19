"""Shared validation for authoring options."""

import math

from .errors import ValidationError


def finite_number(value: float, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{name} must be >= {minimum}")
    return float(value)


def rgb(value: tuple[int, int, int], name: str) -> tuple[int, int, int]:
    if (not isinstance(value, tuple) or len(value) != 3
            or any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c <= 255 for c in value)):
        raise ValidationError(f"{name} must be an RGB tuple of integers from 0 to 255")
    return value

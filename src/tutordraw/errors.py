"""Errors raised by TutorDraw."""


class TutorDrawError(Exception):
    """Base error for tutorial operations."""


class ValidationError(TutorDrawError, ValueError):
    """Invalid author input or scene references."""


class SceneCopyError(TutorDrawError):
    """The source scene cannot be copied through DrawCV serialization."""


class LayoutWarning(UserWarning):
    """An annotation extends beyond the output canvas."""

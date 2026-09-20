"""Errors raised by TutorDraw."""


class TutorDrawError(Exception):
    """Base error for tutorial operations."""


class ValidationError(TutorDrawError, ValueError):
    """Invalid author input or scene references."""


class SceneCopyError(TutorDrawError):
    """The source scene cannot be copied through DrawCV serialization."""


class LessonFormatError(ValidationError):
    """Invalid or unsupported serialized lesson content."""


class LayoutWarning(UserWarning):
    """An annotation extends beyond the output canvas."""


class ExportError(TutorDrawError):
    """An export failed after preflight; completed_paths contains successful files."""

    def __init__(self, step_index, path, completed_paths):
        self.step_index = step_index
        self.path = path
        self.completed_paths = tuple(completed_paths)
        super().__init__(f"Export failed at step {step_index + 1} ({path}); "
                         f"{len(self.completed_paths)} files completed")

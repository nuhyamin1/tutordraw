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


class LessonWarning(UserWarning):
    """Saving a lesson leaves something out that the file format cannot hold yet."""


class ExportError(TutorDrawError):
    """An export failed after preflight; completed_paths contains successful files."""

    def __init__(self, step_index, path, completed_paths):
        self.step_index = step_index
        self.path = path
        self.completed_paths = tuple(completed_paths)
        super().__init__(f"Export failed at step {step_index + 1} ({path}); "
                         f"{len(self.completed_paths)} files completed")


class VideoExportError(TutorDrawError):
    """A video export failed; the destination file was not created or replaced."""

    def __init__(self, message, path, fourcc, frames_written):
        self.path = path
        self.fourcc = fourcc
        self.frames_written = frames_written
        super().__init__(f"{message} ({path}, fourcc {fourcc!r}, "
                         f"{frames_written} frames encoded)")

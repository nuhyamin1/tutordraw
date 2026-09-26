"""Teach with existing DrawCV drawings."""

from .errors import (ExportError, LayoutWarning, LessonFormatError, SceneCopyError,
                     TutorDrawError, ValidationError, VideoExportError)
from .captions import Caption, Cue
from .composition import AnnotationLayout, Composition, HighlightLayout
from .lint import Issue
from .model import Callout, Label, Step, Target
from .prompts import Answer, Prompt
from .themes import Theme
from .tutorial import Tutorial

__version__ = "0.3.0a1"
__all__ = ["Tutorial", "Target", "Label", "Callout", "Step", "Theme", "TutorDrawError",
           "ValidationError", "SceneCopyError", "LayoutWarning", "ExportError",
           "LessonFormatError", "VideoExportError", "Composition", "AnnotationLayout",
           "HighlightLayout", "Issue", "Prompt", "Answer", "Caption", "Cue"]

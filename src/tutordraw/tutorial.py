"""Tutorial authoring and static rendering."""

from pathlib import Path

from drawcv import Canvas, Drawable, OpenCVRenderer, Scene

from .adapters.drawcv import copy_scene, index_scene, load_font, overlay_layer, typography_errors
from .errors import ValidationError
from .layout import label_artwork
from .model import Label, Step, Target
from .attention import apply_attention, apply_restyles, highlight_artwork
from .export import export_steps
from .themes import Theme


class Tutorial:
    """Attach teaching labels to an existing DrawCV scene without editing it."""

    def __init__(self, scene: Scene, *, title: str = "", theme: Theme | None = None,
                 font=None):
        if not isinstance(scene, Scene):
            raise ValidationError("scene must be a DrawCV Scene")
        if not isinstance(title, str):
            raise ValidationError("title must be a string")
        if theme is not None and not isinstance(theme, Theme):
            raise ValidationError("theme must be a Theme")
        self.theme = theme or Theme()
        self.scene = scene
        self.title = title
        # A font enables Thai and Arabic and is used for everything it can draw.
        self._font = None if font is None else load_font(font)
        self._targets: dict[str, Target] = {}
        self._labels: dict[str, Label] = {}
        self._steps: list[Step] = []

    @property
    def font(self):
        """The configured DrawCV FontAsset, or None for built-in text only."""
        return self._font

    @property
    def steps(self) -> tuple[Step, ...]:
        return tuple(self._steps)

    @property
    def targets(self) -> tuple[Target, ...]:
        return tuple(self._targets.values())

    @property
    def labels(self) -> tuple[Label, ...]:
        return tuple(self._labels.values())

    def get_target(self, name: str) -> Target:
        """Find a named target after loading or while revising a lesson."""
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Target name must be a nonempty string")
        for target in self._targets.values():
            if target.name == name:
                return target
        raise ValidationError(f"Unknown target name: {name!r}")

    def to_dict(self) -> dict:
        """Return a detached, validated JSON-compatible lesson document."""
        from .serialization import to_dict
        return to_dict(self)

    @classmethod
    def from_dict(cls, document: dict, *, font=None) -> "Tutorial":
        """Load a complete lesson. Supply the font again for Thai or Arabic text."""
        from .serialization import from_dict
        return from_dict(document, tutorial_type=cls, font=font)

    def to_json(self) -> str:
        """Serialize the drawing and teaching state as readable JSON."""
        from .serialization import to_json
        return to_json(self)

    @classmethod
    def from_json(cls, text: str, *, font=None) -> "Tutorial":
        from .serialization import from_json
        return from_json(text, tutorial_type=cls, font=font)

    def save_json(self, path: str | Path, *, overwrite: bool = False) -> Path:
        """Save a complete lesson; refuse existing files unless explicitly allowed."""
        from .serialization import save_json
        return save_json(self, path, overwrite=overwrite)

    @classmethod
    def load_json(cls, path: str | Path, *, font=None) -> "Tutorial":
        """Load a UTF-8 lesson. Filesystem errors propagate unchanged."""
        from .serialization import load_json
        return load_json(path, tutorial_type=cls, font=font)

    def target(self, drawable: Drawable, *, name: str | None = None) -> Target:
        """Register a scene member, including a nested group child."""
        if not isinstance(drawable, Drawable) or index_scene(self.scene).get(drawable.id) is not drawable:
            raise ValidationError("Target drawable must belong to the source scene")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValidationError("Target name must be a nonempty string or None")
        existing = self._targets.get(drawable.id)
        if existing is not None:
            if name is not None and name != existing.name:
                raise ValidationError("Drawable is already registered with a different name")
            return existing
        if name is not None and any(t.name == name for t in self._targets.values()):
            raise ValidationError(f"Target name is already in use: {name!r}")
        target = Target(self, drawable.id, name)
        self._targets[drawable.id] = target
        return target

    def step(self, title: str, *, duration: float = 3.0, pause: float = 0.0) -> Step:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Step title must be a nonempty string")
        step = Step(self, title, duration=duration, pause=pause)
        self._steps.append(step)
        return step

    @property
    def duration(self) -> float:
        """Total lesson seconds, including pauses; zero for an empty lesson."""
        from .timing import boundaries
        ends = boundaries(self)
        return ends[-1] if ends else 0.0

    def step_at_time(self, time: float) -> int:
        """Resolve seconds to a zero-based step, including the final endpoint."""
        from .timing import step_at_time
        return step_at_time(self, time)

    def render_at_time(self, time: float, *, alpha: bool = False) -> Canvas:
        """Seek to a moment. Animated steps interpolate; the rest are hard cuts."""
        from .timing import position_at_time

        if not isinstance(alpha, bool):
            raise ValidationError("alpha must be a boolean")
        index, progress = position_at_time(self, time)
        step = self._steps[index]
        if progress >= 1.0 or (step.easing is None and not step._reveals):
            return self.render_step(index, alpha=alpha)
        return self._render(index, progress, alpha)

    def render_frames(self, *, fps: int = 30, alpha: bool = False):
        """Iterate ceil(duration * fps) canvases sampled at k / fps seconds."""
        from .timing import render_frames
        return render_frames(self, fps=fps, alpha=alpha)

    def render_step(self, index: int, *, alpha: bool = False) -> Canvas:
        """Render a zero-based step. Source artwork/history remain untouched."""
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self._steps):
            raise ValidationError(f"Step index must be between 0 and {len(self._steps) - 1}")
        if not isinstance(alpha, bool):
            raise ValidationError("alpha must be a boolean")
        return self._render(index, 1.0, alpha)

    def _render(self, index: int, progress: float, alpha: bool) -> Canvas:
        source = index_scene(self.scene)
        for target in self._targets.values():
            if target.drawable_id not in source:
                raise ValidationError(f"Missing target {target.name or target.id!r}: {target.drawable_id}")
        working = copy_scene(self.scene)
        objects = index_scene(working)
        step = self._steps[index]
        # Easing shapes the artwork blend; reveals use plain elapsed seconds.
        eased = progress
        if step.easing is not None and progress < 1.0:
            from drawcv import get_easing
            eased = get_easing(step.easing)(progress)
        elif step.easing is None:
            eased = 1.0
        # Artwork changes land before emphasis, so attached annotations follow them.
        previous = self._steps[index - 1] if eased < 1.0 and index else None
        apply_restyles(objects, step, previous, eased)
        apply_attention(working, step)
        layer = overlay_layer(working)
        with typography_errors():
            for highlight in step.highlights:
                working.add(highlight_artwork(highlight, objects[highlight.target.drawable_id]), layer=layer)
            elapsed = progress * step.duration
            for label in (*step.labels, *step.callouts):
                # A delay past the step's duration simply reveals at its end.
                if min(step.revealed_at(label), step.duration) > elapsed:
                    continue
                _, artwork = label_artwork(label, objects[label.target.drawable_id],
                                           working.width, working.height, self.theme, self._font)
                for obj in artwork:
                    working.add(obj, layer=layer)
            return OpenCVRenderer().render(working, alpha=alpha)

    def export_steps(self, directory: str | Path, *, overwrite: bool = False,
                     alpha: bool = False) -> list[Path]:
        """Write numbered PNGs; fail on existing destinations unless explicitly allowed."""
        return export_steps(self, directory, overwrite=overwrite, alpha=alpha)

    def export_video(self, path: str | Path, *, fps: int = 30, fourcc: str = "mp4v",
                     overwrite: bool = False) -> Path:
        """Encode the timed lesson to one video file. Opaque only; no alpha channel."""
        from .video import export_video
        return export_video(self, path, fps=fps, fourcc=fourcc, overwrite=overwrite)

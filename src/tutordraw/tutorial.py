"""Tutorial authoring and static rendering."""

from pathlib import Path

from drawcv import Canvas, Drawable, Line, OpenCVRenderer, Scene

from .adapters.drawcv import copy_scene, index_scene, load_font, overlay_layer, typography_errors
from .errors import ValidationError
from .layout import label_artwork
from .model import Callout, Label, Step, Target
from .attention import (apply_attention, apply_restyles, final_bounds, highlight_artwork,
                        residual_moves)
from .collision import plan_annotations
from .composition import AnnotationLayout, Composition, HighlightLayout, MarkLayout
from .lint import Issue
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

    def layout(self, index: int, *, time: float | None = None) -> Composition:
        """Where everything in a step lands, without rasterizing it.

        `time` is seconds into the step; None means its finished state, as
        render_step shows it. Read-only: the result is a working copy.
        """
        self._check_index(index)
        step = self._steps[index]
        if time is None:
            return self._compose(index, 1.0)
        if isinstance(time, bool) or not isinstance(time, (int, float)) or not 0 <= time <= step.duration:
            raise ValidationError(f"time must be between 0 and the step's duration ({step.duration:g})")
        return self._compose(index, time / step.duration if step.duration else 1.0)

    def to_svg(self, index: int, *, time: float | None = None) -> str:
        """One frame as standalone SVG: vector artwork and native, selectable text.

        `time` is seconds into the step, as for layout(); None is the finished
        step. Text uses the browser's sans-serif stretched to TutorDraw's
        measured widths, so it fits its panels but is not pixel-identical to
        render_step. See docs/WEB.md.
        """
        from .web import frame_svg
        composition = self.layout(index, time=time)
        return frame_svg(self, index, composition)

    def web_step(self, index: int) -> dict:
        """Everything a browser player needs for one step, as JSON-ready data.

        Send each step as soon as it is authored to stream a lesson; the
        player plays what it has and waits for the rest. See docs/WEB.md.
        """
        from .web import web_step
        self._check_index(index)
        return web_step(self, index)

    def export_web(self, path: str | Path, *, overwrite: bool = False) -> Path:
        """Write one self-contained HTML file that plays the whole lesson."""
        from .web import export_web
        return export_web(self, path, overwrite=overwrite)

    def lint(self, index: int | None = None) -> list[Issue]:
        """Report readability problems in one step, or in every step.

        Each Issue has a stable code and a suggested fix. Built for an
        author-lint-fix loop; it never changes what renders.
        """
        from .lint import lint_step
        if index is not None:
            self._check_index(index)
            return lint_step(self, index)
        return [issue for i in range(len(self._steps)) for issue in lint_step(self, i)]

    def _check_index(self, index: int) -> None:
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self._steps):
            raise ValidationError(f"Step index must be between 0 and {len(self._steps) - 1}")

    def render_step(self, index: int, *, alpha: bool = False) -> Canvas:
        """Render a zero-based step. Source artwork/history remain untouched."""
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self._steps):
            raise ValidationError(f"Step index must be between 0 and {len(self._steps) - 1}")
        if not isinstance(alpha, bool):
            raise ValidationError("alpha must be a boolean")
        return self._render(index, 1.0, alpha)

    def _render(self, index: int, progress: float, alpha: bool) -> Canvas:
        return OpenCVRenderer().render(self._compose(index, progress).scene, alpha=alpha)

    def _compose(self, index: int, progress: float, *, draw_annotations: bool = True,
                 complete: bool = False) -> Composition:
        """Build the working scene for one frame and record every layout decision.

        `complete` shows every annotation fully drawn whatever the time, which
        is the start frame a browser player tweens from.
        """
        from . import camera as cam
        from .marks import mark_drawing

        source = index_scene(self.scene)
        for target in self._targets.values():
            if target.drawable_id not in source:
                raise ValidationError(f"Missing target {target.name or target.id!r}: {target.drawable_id}")
        working = copy_scene(self.scene)
        objects = index_scene(working)
        step = self._steps[index]
        width, height = working.width, working.height
        # Easing shapes the artwork blend; reveals use plain elapsed seconds.
        eased = progress
        if step.easing is not None and progress < 1.0:
            from drawcv import get_easing
            eased = get_easing(step.easing)(progress)
        elif step.easing is None:
            eased = 1.0
        # Artwork changes land before emphasis, so attached annotations follow them.
        # The planner always needs the real previous step, even at progress 1:
        # that is the other end of the sweep, so every frame plans identically.
        prior = self._steps[index - 1] if index else None
        animating = eased < 1.0
        apply_restyles(objects, step, prior if animating else None, eased)

        # Frame the artwork. Each end is fitted to its own step's end-state
        # bounds, measured before the camera exists, so zooming never feeds back.
        end_view = start_view = None
        if step.camera is not None or (animating and prior is not None and prior.camera is not None):
            wanted = {t.drawable_id for t in (step.camera.targets if step.camera else ())}
            end_view = cam.fit(step.camera, final_bounds(
                objects, wanted, residual_moves(step, prior, eased)), width, height)
            if animating and prior is not None and prior.camera is not None:
                earlier = {t.drawable_id for t in prior.camera.targets}
                start_view = cam.fit(prior.camera, final_bounds(
                    objects, earlier, residual_moves(step, prior, eased, 0.0)), width, height)
        view = None
        groups = []
        if end_view is not None or start_view is not None:
            view = cam.blend(start_view, end_view, eased if animating else 1.0, width, height)
            groups = cam.install(working)
            cam.apply(groups, view)

        def camera_at(t):
            return cam.held_at(groups, cam.blend(start_view, end_view, t, width, height)
                               if groups else None)

        apply_attention(working, step)
        layer = overlay_layer(working)
        elapsed = step.duration if complete else progress * step.duration
        highlights, annotations, marks = [], [], []
        canvas = (width, height)
        with typography_errors():
            for highlight in step.highlights:
                drawn = step.draw_progress(highlight, elapsed)
                if drawn <= 0:
                    continue
                shape = highlight_artwork(highlight, objects[highlight.target.drawable_id], drawn)
                working.add(shape, layer=layer)
                highlights.append(HighlightLayout(_name(highlight.target), shape.get_bounds(),
                                                  highlight.width))

            def mark_boxes(bounds):
                return [mark_drawing(mark, bounds, cam.blend(start_view, end_view, 1.0, width, height)
                                     if groups else None, self.theme, self._font, canvas).bounds
                        for mark in step.marks]

            # Placement is decided once from the step's end state, so it is the
            # same for every frame of it; only the panels track live bounds.
            plan = {}
            if self.theme.avoid_collisions:
                plan = plan_annotations(
                    step, objects, [t.drawable_id for t in self._targets.values()],
                    width=width, height=height, theme=self.theme,
                    font=self._font, previous=prior, progress=eased,
                    camera_at=camera_at, mark_boxes=mark_boxes if step.marks else None)
            for label in (*step.labels, *step.callouts):
                # A delay past the step's duration simply reveals at its end.
                drawn = step.draw_progress(label, elapsed)
                if drawn <= 0:
                    continue
                placement, measured = plan.get(label.id, (None, None))
                layout, artwork = label_artwork(label, objects[label.target.drawable_id],
                                                width, height, self.theme,
                                                self._font, placement, measured, drawn)
                if draw_annotations:
                    for obj in artwork:
                        working.add(obj, layer=layer)
                if drawn < 1:
                    continue  # Still drawing on: nothing readable to report yet.
                drew_leader = any(isinstance(obj, Line) for obj in artwork)
                annotations.append(AnnotationLayout(
                    id=label.id, kind="callout" if isinstance(label, Callout) else "label",
                    text=label.text, target=_name(label.target),
                    anchor=label.anchor if placement is None else placement.anchor,
                    panel=layout.panel, boxed=label.box,
                    leader=(layout.anchor, layout.leader_end) if drew_leader else None))
            if step.marks:
                live = {t.drawable_id: objects[t.drawable_id].get_bounds()
                        for mark in step.marks for t in mark.refs if isinstance(t, Target)}
                for mark in step.marks:
                    drawn = step.draw_progress(mark, elapsed)
                    if drawn <= 0:
                        continue
                    drawing = mark_drawing(mark, live, view, self.theme, self._font, canvas, drawn)
                    if draw_annotations:
                        for obj in drawing.artwork:
                            working.add(obj, layer=layer)
                    if drawn >= 1:
                        marks.append(MarkLayout(
                            mark.id, mark.kind, mark.text,
                            tuple(_name(t) for t in mark.refs if isinstance(t, Target)),
                            drawing.bounds, drawing.panel))
        bounds = {_name(t): objects[t.drawable_id].get_bounds() for t in self._targets.values()}
        ids = {_name(t): t.drawable_id for t in self._targets.values()}
        return Composition(working, index, progress, tuple(annotations), tuple(highlights),
                           bounds, ids, tuple(marks), view)

    def export_steps(self, directory: str | Path, *, overwrite: bool = False,
                     alpha: bool = False) -> list[Path]:
        """Write numbered PNGs; fail on existing destinations unless explicitly allowed."""
        return export_steps(self, directory, overwrite=overwrite, alpha=alpha)

    def export_video(self, path: str | Path, *, fps: int = 30, fourcc: str = "mp4v",
                     overwrite: bool = False) -> Path:
        """Encode the timed lesson to one video file. Opaque only; no alpha channel."""
        from .video import export_video
        return export_video(self, path, fps=fps, fourcc=fourcc, overwrite=overwrite)


def _name(target: Target) -> str:
    return target.name or target.id

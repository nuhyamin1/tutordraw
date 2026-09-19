"""Tutorial authoring and static rendering."""

from drawcv import Canvas, Drawable, OpenCVRenderer, Scene

from .adapters.drawcv import copy_scene, index_scene, overlay_layer
from .errors import ValidationError
from .layout import label_artwork
from .model import Label, Step, Target


class Tutorial:
    """Attach teaching labels to an existing DrawCV scene without editing it."""

    def __init__(self, scene: Scene, *, title: str = ""):
        if not isinstance(scene, Scene):
            raise ValidationError("scene must be a DrawCV Scene")
        if not isinstance(title, str):
            raise ValidationError("title must be a string")
        self.scene = scene
        self.title = title
        self._targets: dict[str, Target] = {}
        self._labels: dict[str, Label] = {}
        self._steps: list[Step] = []

    @property
    def steps(self) -> tuple[Step, ...]:
        return tuple(self._steps)

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

    def step(self, title: str) -> Step:
        if not isinstance(title, str) or not title.strip():
            raise ValidationError("Step title must be a nonempty string")
        step = Step(self, title)
        self._steps.append(step)
        return step

    def render_step(self, index: int, *, alpha: bool = False) -> Canvas:
        """Render a zero-based step. Source artwork/history remain untouched."""
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(self._steps):
            raise ValidationError(f"Step index must be between 0 and {len(self._steps) - 1}")
        if not isinstance(alpha, bool):
            raise ValidationError("alpha must be a boolean")
        source = index_scene(self.scene)
        for target in self._targets.values():
            if target.drawable_id not in source:
                raise ValidationError(f"Missing target {target.name or target.id!r}: {target.drawable_id}")
        working = copy_scene(self.scene)
        objects = index_scene(working)
        layer = overlay_layer(working)
        for label in self._steps[index].labels:
            _, artwork = label_artwork(label, objects[label.target.drawable_id], working.width, working.height)
            for obj in artwork:
                working.add(obj, layer=layer)
        return OpenCVRenderer().render(working, alpha=alpha)

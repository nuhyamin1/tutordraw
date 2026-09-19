"""DrawCV operations isolated from the teaching model."""

from copy import deepcopy

from drawcv import Drawable, Group, Scene

from ..errors import SceneCopyError, ValidationError


def index_scene(scene: Scene) -> dict[str, Drawable]:
    """Traverse actual scene contents, detecting ambiguous IDs."""
    result: dict[str, Drawable] = {}

    def visit(obj: Drawable) -> None:
        if obj.id in result:
            raise ValidationError(f"Duplicate drawable ID: {obj.id!r}")
        result[obj.id] = obj
        if isinstance(obj, Group):
            for child in obj.children:
                visit(child)

    for obj in scene.objects:
        visit(obj)
    return result


def copy_scene(scene: Scene) -> Scene:
    """Copy through the public document API; never mutate the source."""
    source = index_scene(scene)
    try:
        copied = Scene.from_dict(deepcopy(scene.to_dict()))
        copied_index = index_scene(copied)
        if source.keys() != copied_index.keys():
            raise ValueError("Scene round trip changed drawable IDs")
        for key, obj in source.items():
            if type(copied_index[key]) is not type(obj):
                raise ValueError(f"Scene round trip changed drawable type: {key}")
        return copied
    except Exception as exc:
        raise SceneCopyError(f"Unable to copy DrawCV scene: {exc}") from exc


def overlay_layer(scene: Scene) -> str:
    name = "__tutordraw__"
    while scene.get_layer(name) is not None:
        name += "_"
    scene.create_layer(name)
    return name

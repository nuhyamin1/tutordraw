"""SVG output for a composed frame, fit for a browser player.

DrawCV exports the scene. TutorDraw then fixes what a player needs and DrawCV
0.11.0 does not give it: built-in text arrives as an embedded PNG (blurry when
scaled, slow and heavy), so each such text becomes native <text> sized from
DrawCV's own measurement, with `textLength` pinning its width to the panel it
was laid out in. A halo becomes one stroked text (SVG paint-order) instead of
eight copies. Every TutorDraw element carries its timing as data attributes.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from drawcv import Point, Rectangle, Text

from .adapters.drawcv import index_scene, replace_in_place
from .composition import Composition

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

# DrawCV's built-in text, measured on 0.11.0: the baseline sits 79.5% of the way
# down its line box and a capital is 20.1 px tall per unit of font_scale. A
# sans-serif with a 0.7 em cap height matches that at font_scale * 28.7 px.
BASELINE_RATIO = 0.795
FONT_PX_PER_SCALE = 28.7
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
HALO_ID = re.compile(r"^(?P<text>td-.+-t\d+)-halo\d+$")


def _world_scale(obj) -> float | None:
    """The text's uniform world scale, or None if it is rotated, skewed or flipped.

    DrawCV writes world coordinates into the SVG geometry (a zoomed camera
    group carries no transform attribute), so native text must be placed and
    sized in world space too. Anything but a uniform scale stays raster.
    """
    m = obj.world_matrix
    a, b, c, d = m[0][0], m[0][1], m[1][0], m[1][1]
    if abs(b) > 1e-9 or abs(c) > 1e-9 or a <= 0 or abs(a - d) > 1e-9 * max(1.0, abs(a)):
        return None
    return float(a)


def composition_svg(composition: Composition, *, halo: tuple[tuple[int, int, int], float] | None = None,
                    timing: dict[str, tuple[float, float]] | None = None) -> str:
    """The frame as SVG text.

    `halo` is (panel colour, width) for text that was drawn with a halo;
    `timing` maps an owner ID (label, callout, mark, or "hl-<target id>") to
    (appear_at, draw_seconds[, fade_seconds]) and is written as data-td-at /
    data-td-draw / data-td-fade.
    """
    scene = composition.scene
    specs: dict[str, dict] = {}
    haloed: set[str] = set()
    swaps = []
    for obj in index_scene(scene).values():
        if not isinstance(obj, Text):
            continue
        match = HALO_ID.match(obj.id)
        if match:
            # One stroked text replaces the copies, so drop them before export:
            # an invisible object is skipped rather than rasterised.
            haloed.add(match.group("text"))
            obj.visible = False
            continue
        scale = _world_scale(obj)
        if getattr(obj, "fonts", None) or scale is None or not obj.visible:
            continue
        specs[obj.id] = {"box": obj.get_bounds(), "scale": scale, "text": obj.text,
                         "color": obj.color, "font_scale": obj.font_scale,
                         "bold": getattr(obj, "thickness", 1) >= 2, "opacity": obj.opacity}
        swaps.append(obj)
    # DrawCV would rasterise each built-in text (~40 ms apiece, then thrown
    # away), so an empty placeholder with the same ID takes its place in the
    # draw order and its group is filled with native text afterwards.
    for obj in swaps:
        replace_in_place(obj, Rectangle(position=Point(0, 0), width=0, height=0, id=obj.id,
                                        opacity=obj.opacity, z_index=obj.z_index))
    root = ET.fromstring(scene.export_svg().svg)
    for group in root.iter(f"{{{SVG_NS}}}g"):
        source = group.get("data-drawcv-id")
        if source in specs:
            _native_text(group, specs[source], halo if source in haloed else None)
        if timing and source and source.startswith("td-"):
            _stamp(group, source, timing)
    return ET.tostring(root, encoding="unicode")


def _native_text(group: ET.Element, spec: dict, halo) -> None:
    for child in list(group):
        group.remove(child)
    group.attrib.pop("data-drawcv-raster", None)
    group.set("opacity", f"{spec['opacity']:g}")
    box = spec["box"]  # world space, as DrawCV's geometry is
    color = spec["color"]
    element = ET.SubElement(group, f"{{{SVG_NS}}}text", {
        "x": f"{box.x:.2f}",
        "y": f"{box.y + box.height * BASELINE_RATIO:.2f}",
        "font-family": FONT_FAMILY,
        "font-size": f"{spec['font_scale'] * FONT_PX_PER_SCALE * spec['scale']:.2f}",
        "font-weight": "700" if spec["bold"] else "400",
        "fill": f"rgb({color.r},{color.g},{color.b})",
        # The browser's font is not DrawCV's; stretch it to the measured width
        # so it fills exactly the space the layout reserved for it.
        "textLength": f"{box.width:.2f}",
        "lengthAdjust": "spacingAndGlyphs",
    })
    if halo is not None:
        color, width = halo
        element.set("stroke", f"rgb({color[0]},{color[1]},{color[2]})")
        element.set("stroke-width", f"{2 * width:g}")
        element.set("stroke-linejoin", "round")
        element.set("paint-order", "stroke")
    element.text = spec["text"]


def _stamp(group: ET.Element, source: str, timing: dict[str, tuple[float, float]]) -> None:
    """Write when a TutorDraw element appears and whether its stroke draws on.

    Strokes (a leader, a mark's `s` parts, a highlight) draw over the draw
    time; everything else of the same owner (panel, text, heads) appears when
    that finishes, exactly as the Python renderer does it.
    """
    body = source[3:]
    if body.startswith("hl-"):
        owner, role = body, "stroke"
    else:
        owner, _, role = body.rpartition("-")
    if owner not in timing:
        return
    at, draw, *rest = timing[owner]
    fade = rest[0] if rest else 0.0
    strokes = role == "leader" or role == "stroke" or re.fullmatch(r"s\d+", role)
    if strokes and draw:
        group.set("data-td-at", f"{at:g}")
        group.set("data-td-draw", f"{draw:g}")
    else:
        group.set("data-td-at", f"{at + draw:g}")
        if fade:
            group.set("data-td-fade", f"{fade:g}")

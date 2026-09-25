"""Lessons for the browser: per-step SVG payloads and a self-contained player.

A step is sent as its finished frame, plus, when it animates, its start frame.
The player tweens every element that appears in both (matched by ID, numbers
interpolated attribute by attribute) through a sampled copy of DrawCV's easing
curve, and plays reveals and draw-on from data attributes. Nothing here needs a
server: `web_step` output can go over any transport, one step at a time.
"""

from __future__ import annotations

import json
import os
import re
from importlib.resources import files
from pathlib import Path
import shutil
import tempfile

from .composition import Composition
from .errors import ValidationError
from .prompts import payload as prompt_payload
from .svg import composition_svg

EASING_SAMPLES = 64
CAMERA_KEYFRAMES = 6
PATH_KEYFRAMES = 12  # a move along a path, as a polyline the player walks
PLAYER_VERSION = 1
# DrawCV's SVG export leaves out anything with opacity 0; a target that fades out in an animated step keeps
# this much in the finished frame, so the player has an element to fade (invisible to the eye).
FADED = 0.001


def step_timing(tutorial, index: int) -> dict[str, tuple[float, float]]:
    """Owner ID -> (appear at, draw seconds), clamped to the step as rendering does."""
    step = tutorial.steps[index]
    seconds = tutorial.theme.draw_seconds
    timing = {}
    for item in (*step.labels, *step.callouts, *step.marks):
        at = min(step.revealed_at(item), step.duration)
        timing[item.id] = (at, seconds if item.id in step.draws else 0.0)
    for highlight in step.highlights:
        timing[f"hl-{highlight.target.id}"] = (min(highlight.at, step.duration),
                                               seconds if highlight.draw else 0.0)
    return timing


def frame_svg(tutorial, index: int, composition: Composition) -> str:
    theme = tutorial.theme
    halo = (theme.panel_color, theme.halo_width) if theme.halo_width > 0 else None
    return composition_svg(composition, halo=halo, timing=step_timing(tutorial, index))


def easing_table(name: str | None) -> list[float] | None:
    """DrawCV's curve sampled at 65 points, so the browser eases identically."""
    if name is None:
        return None
    from drawcv import get_easing
    curve = get_easing(name)
    return [round(float(curve(i / EASING_SAMPLES)), 5) for i in range(EASING_SAMPLES + 1)]


def web_step(tutorial, index: int) -> dict:
    """One step's payload. `frames` are the animated step's earlier states.

    Without a camera move, one start frame is exact: restyles blend linearly
    in eased time, so the player eases between start and end with `easing`.
    A camera zooms geometrically, which no linear blend of coordinates
    reproduces, so a moving camera sends CAMERA_KEYFRAMES evenly timed frames
    with the easing already applied; the player blends between neighbours.
    """
    step = tutorial.steps[index]
    final = tutorial._compose(index, 1.0)
    frames: list[str] = []
    easing = None
    if step.easing is not None and index > 0:
        prior = tutorial.steps[index - 1]
        camera_moves = step.camera != prior.camera
        # A move along a path is not a linear blend either: send it as keyframes too.
        path = any(restyle.via for restyle in step.restyles)
        count = max(CAMERA_KEYFRAMES if camera_moves else 1, PATH_KEYFRAMES if path else 1)
        # Everything present and drawn, so every element has a state to blend. Frames span the motion,
        # which may be only the step's first seconds (`motion`, which the player reads).
        span = min(1.0, step.motion / step.duration) if step.motion is not None else 1.0
        earlier = [tutorial._compose(index, span * k / count, complete=True) for k in range(count)]
        frames = [frame_svg(tutorial, index, composition) for composition in earlier]
        easing = None if count > 1 else easing_table(step.easing)
        _keep_fading(final, earlier[0])
    end = frame_svg(tutorial, index, final)
    return {"index": index, "id": step.id, "title": step.title,
            "duration": step.duration, "pause": step.pause,
            "easing": easing, "frames": frames, "svg": end,
            "motion": step.motion if step.easing is not None and step.motion is not None
            and step.motion < step.duration else None,
            "description": tutorial.describe(index),
            "narration": [[w.text, w.start, w.end] for w in step.narration] or None,
            "prompt": prompt_payload(tutorial, step.prompt)}


def _keep_fading(final: Composition, start: Composition) -> None:
    """Give what fades out during the step (shown at its start, opacity 0 at its end) FADED opacity at the end."""
    from .adapters.drawcv import index_scene

    before = index_scene(start.scene)
    for drawable_id, obj in index_scene(final.scene).items():
        was = before.get(drawable_id)
        if (obj.visible and obj.opacity <= 0 and was is not None and was.effective_visible
                and was.effective_opacity > 0):
            obj.opacity = FADED


def web_bundle(tutorial) -> dict:
    if not tutorial.steps:
        raise ValidationError("A lesson needs at least one step to export")
    return {"format": "tutordraw.web", "version": PLAYER_VERSION, "title": tutorial.title,
            "width": tutorial.scene.width, "height": tutorial.scene.height,
            "steps": [web_step(tutorial, i) for i in range(len(tutorial.steps))]}


def player_source() -> str:
    """The player's JavaScript, for embedding in your own page."""
    return files("tutordraw").joinpath("player.js").read_text(encoding="utf-8")


def export_web(tutorial, path: str | Path, *, overwrite: bool = False) -> Path:
    if not isinstance(overwrite, bool):
        raise ValidationError("overwrite must be a boolean")
    destination = Path(path)
    if destination.is_symlink() or (destination.exists() and (not overwrite or not destination.is_file())):
        raise FileExistsError(f"Web destination already exists: {destination}")
    # No raw <, > or & inside the inline JSON: "</script" would end the block
    # and "<!--" with "<script" changes how the HTML parser finds its end.
    # The \u escapes are ordinary JSON, so the data parses unchanged.
    data = (json.dumps(web_bundle(tutorial), ensure_ascii=False, allow_nan=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    title = (tutorial.title or "Lesson").replace("&", "&amp;").replace("<", "&lt;")
    # One pass over placeholders, not str.format (the JavaScript is full of
    # braces) and not chained replace (a title containing "@DATA@" would expand).
    values = {"TITLE": title, "PLAYER": player_source(), "DATA": data}
    page = re.sub(r"@(TITLE|PLAYER|DATA)@", lambda match: values[match.group(1)], PAGE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tutordraw-", suffix=".html", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(page)
        if overwrite:
            os.replace(temporary, destination)
        else:
            # Exclusive create, as save_json does: never replace a file that
            # appeared after the check above.
            with destination.open("xb") as output, temporary.open("rb") as source:
                shutil.copyfileobj(source, output)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@TITLE@</title>
</head>
<body style="margin:0;background:#1b1f27">
<div id="lesson" style="max-width:1100px;margin:24px auto;padding:0 16px"></div>
<script>@PLAYER@</script>
<script type="application/json" id="lesson-data">@DATA@</script>
<script>
const bundle = JSON.parse(document.getElementById("lesson-data").textContent);
const player = new TutorDrawPlayer(document.getElementById("lesson"), bundle);
bundle.steps.forEach(step => player.append(step));
player.play();
</script>
</body>
</html>
"""

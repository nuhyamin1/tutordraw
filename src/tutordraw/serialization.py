"""Versioned JSON persistence for drawings and their teaching state."""

from __future__ import annotations

from dataclasses import asdict, fields, replace
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from drawcv import Scene

from .adapters.drawcv import index_scene
from .errors import LessonFormatError, ValidationError
from .narration import parse_words
from .model import Callout, Label, Target, make_annotation
from .themes import Theme
from .validation import finite_number

if TYPE_CHECKING:
    from .tutorial import Tutorial

FORMAT = "tutordraw.lesson"
SCHEMA_VERSION = 13
SUPPORTED_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, SCHEMA_VERSION)
# Restyle fields each schema version introduced.
RESTYLE_FIELDS_ADDED = {10: ("via",), 12: ("scale", "pivot")}
# The same, for target fields.
TARGET_FIELDS_ADDED = {12: ("obstacle",)}
PROMPT_FIELDS = {"text", "answer_ids", "correct", "wrong", "hint", "attempts"}
# Theme fields each schema version introduced; older documents omit them and
# load with the Theme default, exactly as older step fields do.
THEME_FIELDS_ADDED = {6: ("avoid_collisions", "collision_margin"),
                      8: ("draw_seconds", "halo_width"),
                      13: ("fade_seconds", "pointer_style", "pointer_seconds")}
# The same, for highlight fields.
HIGHLIGHT_FIELDS_ADDED = {8: ("at", "draw", "shape")}
HIGHLIGHT_FIELDS = {"target_id", "padding", "color", "width", "at", "draw", "shape"}
# Each mark kind's options, exactly; the key set is how a kind is validated.
MARK_OPTIONS = {"arrow": {"bend", "both"}, "brace": {"side"}, "measure": {"axis", "offset"},
                "angle": {"radius"}, "number": {"n", "corner"}}
# The same, for label and callout fields.
ANNOTATION_FIELDS_ADDED = {7: ("box",)}
ANNOTATION_FIELDS = {"id", "target_id", "text", "anchor", "leader", "gap", "offset",
                     "font_scale", "padding", "box"}


def _object(value, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise LessonFormatError(f"{where} must be an object")
    if set(value) != keys:
        missing = keys - set(value)
        extra = set(value) - keys
        raise LessonFormatError(f"{where}: missing fields {sorted(missing)}; unknown fields {sorted(extra)}")
    return value


def _list(value, where: str) -> list:
    if not isinstance(value, list):
        raise LessonFormatError(f"{where} must be an array")
    return value


def _string(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LessonFormatError(f"{where} must be a nonempty string")
    return value


def _json_copy(document: dict) -> dict:
    if not isinstance(document, dict):
        raise LessonFormatError("Lesson must be an object")
    try:
        return json.loads(json.dumps(document, allow_nan=False, ensure_ascii=False))
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise LessonFormatError(f"Lesson must contain finite JSON data: {exc}") from exc


def _annotation(label: Label) -> dict:
    value = {"id": label.id, "target_id": label.target.id, "text": label.text,
             "anchor": label.anchor, "leader": label.leader, "gap": label.gap,
             "offset": list(label.offset), "font_scale": label.font_scale,
             "padding": label.padding, "box": label.box}
    if isinstance(label, Callout):
        value.update(max_width=label.max_width, line_spacing=label.line_spacing)
    return value


def _mark(mark) -> dict:
    refs = [{"target_id": ref.id} if isinstance(ref, Target) else {"point": list(ref)}
            for ref in mark.refs]
    return {"id": mark.id, "kind": mark.kind, "refs": refs, "text": mark.text,
            "options": dict(mark.options)}


def _prompt(prompt) -> dict | None:
    if prompt is None:
        return None
    return {"text": prompt.text, "answer_ids": [t.id for t in prompt.answers],
            "correct": prompt.correct, "wrong": prompt.wrong, "hint": prompt.hint,
            "attempts": prompt.attempts}


def to_dict(tutorial: Tutorial) -> dict:
    try:
        source = index_scene(tutorial.scene)
        for target in tutorial.targets:
            if target.drawable_id not in source:
                raise LessonFormatError(f"Missing drawable for target {target.name or target.id!r}")
        document = {
            "format": FORMAT, "schema_version": SCHEMA_VERSION, "title": tutorial.title,
            "theme": asdict(tutorial.theme), "scene": tutorial.scene.to_dict(),
            "targets": [{"id": t.id, "drawable_id": t.drawable_id, "name": t.name, "obstacle": t.obstacle}
                        for t in tutorial.targets],
            "labels": [_annotation(label) for label in tutorial.labels],
            "steps": [{"id": step.id, "title": step.title,
                       "duration": step.duration, "pause": step.pause,
                       "labels": [label.id for label in step.labels],
                       "callouts": [_annotation(c) for c in step.callouts],
                       "highlights": [{"target_id": h.target.id, "padding": h.padding,
                                       "color": list(h.color), "width": h.width, "at": h.at,
                                       "draw": h.draw, "shape": h.shape} for h in step.highlights],
                       "marks": [_mark(m) for m in step.marks],
                       "draw": sorted(step.draws),
                       "camera": None if step.camera is None else {
                           "target_ids": [t.id for t in step.camera.targets],
                           "padding": step.camera.padding, "max_scale": step.camera.max_scale},
                       "dim": None if step._dim_opacity is None else {
                           "target_ids": [t.id for t in step._focus], "opacity": step._dim_opacity},
                       "easing": step.easing,
                       "motion": step.motion,
                       "reveals": step.reveals,
                       "restyles": [{"target_id": r.target.id,
                                     "move": None if r.move is None else list(r.move),
                                     "fill": None if r.fill is None else list(r.fill),
                                     "opacity": r.opacity, "visible": r.visible,
                                     "via": None if r.via is None else [list(p) for p in r.via],
                                     "scale": r.scale,
                                     "pivot": list(r.pivot) if isinstance(r.pivot, tuple) else r.pivot}
                                    for r in step.restyles],
                       "narration": [[w.text, w.start, w.end] for w in step.narration],
                       "prompt": _prompt(step.prompt),
                       "captions": [{"text": c.text, "at": c.at, "until": c.until} for c in step.captions],
                       "points": [{"target_id": p.target.id, "at": p.at} for p in step.points]}
                      for step in tutorial.steps],
        }
        result = _json_copy(document)
        # Validate references and reconstruction before a save can replace a file.
        from_dict(result, font=tutorial.font)
        return result
    except LessonFormatError:
        raise
    except Exception as exc:
        raise LessonFormatError(f"Unable to serialize lesson: {exc}") from exc


def from_dict(document: dict, *, tutorial_type=None, font=None) -> Tutorial:
    from .tutorial import Tutorial

    if tutorial_type is None:
        tutorial_type = Tutorial
    try:
        data = _json_copy(document)
        _object(data, {"format", "schema_version", "title", "theme", "scene", "targets", "labels", "steps"}, "lesson")
        if data["format"] != FORMAT:
            raise LessonFormatError(f"Unsupported lesson format: {data['format']!r}")
        version = data["schema_version"]
        if type(version) is not int or version not in SUPPORTED_VERSIONS:
            raise LessonFormatError(
                f"Unsupported lesson schema version: {version!r}; expected "
                + " or ".join((", ".join(map(str, SUPPORTED_VERSIONS[:-1])), str(SUPPORTED_VERSIONS[-1]))))
        expected = {f.name for f in fields(Theme)} - {
            name for newer, names in THEME_FIELDS_ADDED.items() if newer > version
            for name in names}
        theme_data = _object(data["theme"], expected, "theme")
        for key in theme_data:
            if key.endswith("_color"):
                theme_data[key] = tuple(_list(theme_data[key], f"theme.{key}"))
        scene = Scene.from_dict(data["scene"])
        objects = index_scene(scene)
        tutorial = tutorial_type(scene, title=data["title"], theme=Theme(**theme_data), font=font)
        seen_ids: set[str] = set()

        def identity(value, where):
            value = _string(value, where)
            if value in seen_ids:
                raise LessonFormatError(f"Duplicate lesson ID at {where}: {value!r}")
            seen_ids.add(value)
            return value

        targets = {}
        seen_drawables: set[str] = set()
        for i, item in enumerate(_list(data["targets"], "targets")):
            where = f"targets[{i}]"
            _object(item, {"id", "drawable_id", "name"}
                    | {name for newer, names in TARGET_FIELDS_ADDED.items() if newer <= version for name in names},
                    where)
            obstacle = item.get("obstacle", True)
            if not isinstance(obstacle, bool):
                raise LessonFormatError(f"{where}.obstacle must be a boolean")
            tid = identity(item["id"], f"{where}.id")
            did = _string(item["drawable_id"], f"{where}.drawable_id")
            if did not in objects:
                raise LessonFormatError(f"{where}: missing drawable {did!r}")
            if did in seen_drawables:
                raise LessonFormatError(f"{where}: duplicate target drawable {did!r}")
            seen_drawables.add(did)
            target = replace(tutorial.target(objects[did], name=item["name"], obstacle=obstacle), id=tid)
            tutorial._targets[did] = target
            targets[tid] = target

        def reference(value, mapping, where):
            value = _string(value, where)
            if value not in mapping:
                raise LessonFormatError(f"{where}: unknown reference {value!r}")
            return mapping[value]

        annotation_fields = ANNOTATION_FIELDS - {
            name for newer, names in ANNOTATION_FIELDS_ADDED.items() if newer > version
            for name in names}

        def annotation(item, where, *, callout=False):
            required = annotation_fields | ({"max_width", "line_spacing"} if callout else set())
            _object(item, required, where)
            aid = identity(item["id"], f"{where}.id")
            target = reference(item["target_id"], targets, f"{where}.target_id")
            options = {key: item[key] for key in required - {"id", "target_id"}}
            # Persisted defaults must be concrete values, never re-resolved None.
            if any(options[key] is None for key in options):
                raise LessonFormatError(f"{where}: annotation values cannot be null")
            try:
                return replace(make_annotation(target, callout=callout, **options), id=aid)
            except ValidationError as exc:
                raise LessonFormatError(f"{where}: {exc}") from exc

        labels = {}
        for i, item in enumerate(_list(data["labels"], "labels")):
            label = annotation(item, f"labels[{i}]")
            labels[label.id] = label
            tutorial._labels[label.id] = label

        def references(values, mapping, where):
            values = _list(values, where)
            result, used = [], set()
            for i, value in enumerate(values):
                obj = reference(value, mapping, f"{where}[{i}]")
                if value in used:
                    raise LessonFormatError(f"{where}: duplicate reference {value!r}")
                used.add(value)
                result.append(obj)
            return result

        for i, item in enumerate(_list(data["steps"], "steps")):
            where = f"steps[{i}]"
            timing_fields = {"duration", "pause"} if version >= 2 else set()
            restyle_fields = {"restyles"} if version >= 3 else set()
            easing_fields = {"easing"} if version >= 4 else set()
            reveal_fields = {"reveals"} if version >= 5 else set()
            mark_fields = {"marks", "draw", "camera"} if version >= 8 else set()
            spoken_fields = {"narration", "prompt"} if version >= 9 else set()
            motion_fields = {"motion"} if version >= 11 else set()
            caption_fields = {"captions", "points"} if version >= 13 else set()
            _object(item, {"id", "title", "labels", "callouts", "highlights", "dim"}
                    | timing_fields | restyle_fields | easing_fields | reveal_fields | mark_fields
                    | spoken_fields | motion_fields | caption_fields, where)
            sid = identity(item["id"], f"{where}.id")
            step = tutorial.step(item["title"], duration=item.get("duration", 3.0), pause=item.get("pause", 0.0))
            step._id = sid
            step.show(*references(item["labels"], labels, f"{where}.labels"))
            for j, callout in enumerate(_list(item["callouts"], f"{where}.callouts")):
                step._callouts.append(annotation(callout, f"{where}.callouts[{j}]", callout=True))
            highlighted = set()
            highlight_fields = HIGHLIGHT_FIELDS - {
                name for newer, names in HIGHLIGHT_FIELDS_ADDED.items() if newer > version
                for name in names}
            for j, highlight in enumerate(_list(item["highlights"], f"{where}.highlights")):
                location = f"{where}.highlights[{j}]"
                _object(highlight, highlight_fields, location)
                target = reference(highlight["target_id"], targets, f"{location}.target_id")
                if target.id in highlighted:
                    raise LessonFormatError(f"{location}: duplicate highlight for {target.id!r}")
                if highlight["padding"] is None or highlight["width"] is None:
                    raise LessonFormatError(f"{location}: highlight values cannot be null")
                highlighted.add(target.id)
                try:
                    step.highlight(target, padding=highlight["padding"], width=highlight["width"],
                                   color=tuple(_list(highlight["color"], f"{location}.color")),
                                   shape=highlight.get("shape", "box"), at=highlight.get("at", 0.0),
                                   draw=highlight.get("draw", False))
                except ValidationError as exc:
                    raise LessonFormatError(f"{location}: {exc}") from exc
            for j, entry in enumerate(_list(item.get("marks", []), f"{where}.marks")):
                _load_mark(step, entry, f"{where}.marks[{j}]", targets, identity)
            delays = item.get("reveals", {})
            if not isinstance(delays, dict):
                raise LessonFormatError(f"{where}.reveals must be an object")
            shown = ({label.id for label in step.labels} | {c.id for c in step.callouts}
                     | {m.id for m in step.marks})
            for key, value in delays.items():
                if key not in shown:
                    raise LessonFormatError(f"{where}.reveals: unknown annotation {key!r}")
                try:
                    step._reveals[key] = finite_number(value, "at", minimum=0)
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.reveals[{key!r}]: {exc}") from exc
            drawn = _list(item.get("draw", []), f"{where}.draw")
            for key in drawn:
                if key not in shown:
                    raise LessonFormatError(f"{where}.draw: unknown annotation or mark {key!r}")
                if any(m.id == key and m.kind == "number" for m in step.marks):
                    raise LessonFormatError(f"{where}.draw: number markers cannot draw on")
            step._draw.update(drawn)
            if item.get("camera") is not None:
                view = _object(item["camera"], {"target_ids", "padding", "max_scale"}, f"{where}.camera")
                try:
                    step.zoom_to(*references(view["target_ids"], targets, f"{where}.camera.target_ids"),
                                 padding=view["padding"], max_scale=view["max_scale"])
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.camera: {exc}") from exc
            if item.get("easing") is not None:
                try:
                    step.animate(item["easing"], seconds=item.get("motion"))
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.easing: {exc}") from exc
            restyled = set()
            for j, entry in enumerate(_list(item.get("restyles", []), f"{where}.restyles")):
                location = f"{where}.restyles[{j}]"
                _object(entry, {"target_id", "move", "fill", "opacity", "visible"}
                        | {name for newer, names in RESTYLE_FIELDS_ADDED.items() if newer <= version
                           for name in names}, location)
                target = reference(entry["target_id"], targets, f"{location}.target_id")
                if target.id in restyled:
                    raise LessonFormatError(f"{location}: duplicate restyle for {target.id!r}")
                restyled.add(target.id)
                move = entry["move"]
                fill = entry["fill"]
                via = entry.get("via")
                try:
                    step.restyle(target,
                                 move=None if move is None else tuple(_list(move, f"{location}.move")),
                                 fill=None if fill is None else tuple(_list(fill, f"{location}.fill")),
                                 opacity=entry["opacity"], visible=entry["visible"],
                                 via=None if via is None else [tuple(_list(p, f"{location}.via"))
                                                               for p in _list(via, f"{location}.via")],
                                 scale=entry.get("scale"), pivot=entry.get("pivot"))
                except ValidationError as exc:
                    raise LessonFormatError(f"{location}: {exc}") from exc
            if item["dim"] is not None:
                dim = _object(item["dim"], {"target_ids", "opacity"}, f"{where}.dim")
                if dim["opacity"] is None:
                    raise LessonFormatError(f"{where}.dim.opacity cannot be null")
                step.dim_others(*references(dim["target_ids"], targets, f"{where}.dim.target_ids"),
                                opacity=dim["opacity"])
            words = _list(item.get("narration", []), f"{where}.narration")
            if words:
                # The words only: the reveal times narrate() set are already in
                # "reveals", so replaying the cues would be redundant.
                try:
                    step._narration = parse_words(words)
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.narration: {exc}") from exc
            for j, entry in enumerate(_list(item.get("captions", []), f"{where}.captions")):
                caption = _object(entry, {"text", "at", "until"}, f"{where}.captions[{j}]")
                try:
                    step.caption(caption["text"], at=caption["at"], until=caption["until"])
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.captions[{j}]: {exc}") from exc
            for j, entry in enumerate(_list(item.get("points", []), f"{where}.points")):
                stop = _object(entry, {"target_id", "at"}, f"{where}.points[{j}]")
                try:
                    step.point(reference(stop["target_id"], targets, f"{where}.points[{j}].target_id"),
                               at=stop["at"])
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.points[{j}]: {exc}") from exc
            if item.get("prompt") is not None:
                asked = _object(item["prompt"], PROMPT_FIELDS, f"{where}.prompt")
                answers = references(asked["answer_ids"], targets, f"{where}.prompt.answer_ids")
                try:
                    step.ask(asked["text"], tuple(answers), correct=asked["correct"],
                             wrong=asked["wrong"], hint=asked["hint"], attempts=asked["attempts"])
                except ValidationError as exc:
                    raise LessonFormatError(f"{where}.prompt: {exc}") from exc
        tutorial.duration  # Reject cumulative overflow or unrepresentable intervals.
        return tutorial
    except LessonFormatError:
        raise
    except Exception as exc:
        raise LessonFormatError(f"Invalid lesson: {exc}") from exc


def _load_mark(step, entry, where, targets, identity) -> None:
    """Rebuild a mark through its authoring method, so it is validated the same way."""
    _object(entry, {"id", "kind", "refs", "text", "options"}, where)
    kind = entry["kind"]
    if kind not in MARK_OPTIONS:
        raise LessonFormatError(f"{where}.kind: unknown mark kind {kind!r}")
    mark_id = identity(entry["id"], f"{where}.id")
    options = _object(entry["options"], MARK_OPTIONS[kind], f"{where}.options")
    refs = []
    for k, ref in enumerate(_list(entry["refs"], f"{where}.refs")):
        if isinstance(ref, dict) and set(ref) == {"target_id"}:
            if ref["target_id"] not in targets:
                raise LessonFormatError(f"{where}.refs[{k}]: unknown reference {ref['target_id']!r}")
            refs.append(targets[ref["target_id"]])
        elif isinstance(ref, dict) and set(ref) == {"point"}:
            refs.append(tuple(_list(ref["point"], f"{where}.refs[{k}].point")))
        else:
            raise LessonFormatError(f"{where}.refs[{k}] must be {{target_id}} or {{point}}")
    text = entry["text"]
    try:
        if kind == "arrow":
            if len(refs) != 2:
                raise ValidationError("an arrow has exactly two refs")
            step.connect(*refs, text, **options)
        elif kind == "brace":
            step.brace(*refs, text=text, **options)
        elif kind == "measure":
            if len(refs) not in (1, 2):
                raise ValidationError("a measure has one or two refs")
            step.measure(refs[0], refs[1] if len(refs) == 2 else None, text, **options)
        elif kind == "angle":
            if len(refs) != 3:
                raise ValidationError("an angle has exactly three refs")
            step.angle(*refs, text, **options)
        else:
            if len(refs) != 1 or text is not None:
                raise ValidationError("a number has one ref and no text")
            step.number(refs[0], **options)
    except (ValidationError, TypeError) as exc:
        raise LessonFormatError(f"{where}: {exc}") from exc
    step._marks[-1] = replace(step._marks[-1], id=mark_id)


def to_json(tutorial: Tutorial) -> str:
    return json.dumps(to_dict(tutorial), ensure_ascii=False, allow_nan=False, indent=2) + "\n"


def from_json(text: str, *, tutorial_type=None, font=None) -> Tutorial:
    if not isinstance(text, str):
        raise LessonFormatError("Lesson JSON must be a string")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise LessonFormatError(f"Duplicate JSON key: {key!r}")
            result[key] = value
        return result

    def constant(value):
        raise LessonFormatError(f"Non-finite JSON number: {value}")

    try:
        document = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise LessonFormatError(f"Invalid lesson JSON: {exc}") from exc
    return from_dict(document, tutorial_type=tutorial_type, font=font)


def save_json(tutorial: Tutorial, path: str | Path, *, overwrite: bool) -> Path:
    if not isinstance(overwrite, bool):
        raise ValidationError("overwrite must be a boolean")
    destination = Path(path)
    if destination.is_symlink() or (destination.exists() and (not overwrite or not destination.is_file())):
        raise FileExistsError(f"Lesson destination already exists: {destination}")
    text = to_json(tutorial)  # Validate everything before touching a destination.
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tutordraw-", suffix=".json", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        if overwrite:
            os.replace(temporary, destination)
        else:
            created = False
            try:
                with destination.open("xb") as output:
                    created = True
                    with temporary.open("rb") as source:
                        shutil.copyfileobj(source, output)
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_json(path: str | Path, *, tutorial_type=None, font=None) -> Tutorial:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except UnicodeError as exc:
        raise LessonFormatError("Lesson file is not valid UTF-8") from exc
    return from_json(text, tutorial_type=tutorial_type, font=font)

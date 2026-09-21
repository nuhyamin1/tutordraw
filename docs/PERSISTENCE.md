# Saving, loading, and revising lessons

Introduced in **0.1.0a4**. Schema v2 added timing (a5), v3 per-step artwork changes (a8), v4 step easing (a10) and v5 annotation reveal times (a11). Every older version still loads; saving always writes the current one. The alpha moves quickly, so expect further bumps. The published 0.1.0a3 release does not include these methods.

A lesson file contains the DrawCV scene, tutorial title, theme, all registered targets and labels (including hidden definitions), and ordered steps with callouts, highlights, focus sets, and dimming factors. Generated overlay artwork is not inserted into the saved source scene.

## Python API

```python
from tutordraw import Tutorial

# tutorial is a lesson authored earlier in this session:
# tutorial.save_json("lesson.tutordraw.json")

lesson = Tutorial.load_json("lesson.tutordraw.json")
subject = lesson.get_target("nucleus")
subject.drawable.transform.translation_x += 20
lesson.save_json("lesson-revised.tutordraw.json")
```

This fragment assumes an existing saved lesson with a target named nucleus. A complete executable workflow is in [save_and_revise.py](../examples/save_and_revise.py).

| Method/property | Contract |
| --- | --- |
| `tutorial.to_dict()` | Detached, validated JSON-compatible document |
| `Tutorial.from_dict(document)` | New lesson, independent of the input dictionary |
| `tutorial.to_json()` | Readable JSON text, finite numbers only |
| `Tutorial.from_json(text)` | Load a JSON string; duplicate keys are rejected |
| `tutorial.save_json(path, overwrite=False)` | Save UTF-8 JSON; return Path |
| `Tutorial.load_json(path, font=None)` | Load UTF-8 JSON; optional BOM accepted. Supply `font` for Thai or Arabic |
| `tutorial.targets`, `tutorial.labels` | Tuples of registered definitions |
| `tutorial.get_target(name)` | Resolve a unique registered name; errors if missing |
| `target.drawable` | Resolve the current source object, including nested children |
| `step.id` | Stable, read-only step identity preserved across save/load |

DrawCV object IDs, tutorial target IDs, label/callout IDs, step IDs, step order, and shared label references survive a round trip. Stable IDs are opaque strings: preserve them when editing an existing definition. Create new IDs for newly inserted definitions; the Python authoring API generates these automatically.

`get_target` looks up the human-readable name, not its ID. Unnamed targets remain accessible through `tutorial.targets`; their IDs and drawable IDs appear in the document. To resolve a step for JSON editing, match its stable `id` rather than its possibly duplicated title.

## Editing explanations

Labels and callout definitions are immutable Python objects. For a full persisted revision, edit a detached dictionary and validate it into a new lesson:

```python
from tutordraw import Tutorial

lesson = Tutorial.load_json("lesson.tutordraw.json")
document = lesson.to_dict()
step_id = lesson.steps[1].id
step = next(item for item in document["steps"] if item["id"] == step_id)
step["callouts"][0]["text"] = "A clearer explanation."
revised = Tutorial.from_dict(document)
revised.save_json("lesson-revised.tutordraw.json")
```

This fragment assumes a second step with a callout. The original lesson object and file remain unchanged. For adding teaching content, prefer the regular `step`, `show`, `highlight`, `explain`, and `dim_others` methods.

## Format v2 (with v1 loading)

Envelope keys are `format`, `schema_version`, `title`, `theme`, `scene`, `targets`, `labels`, and `steps`. `format` must be `tutordraw.lesson`; `schema_version` is integer `2` for new saves. Integer `1` is also accepted when loading.

- `theme`: all Theme fields, RGB colors as arrays.
- `scene`: the complete DrawCV document envelope, with its own schema version.
- `targets`: `{id, drawable_id, name}` entries; name may be null.
- `labels`: `{id, target_id, text, anchor, leader, gap, offset, font_scale, padding}`.
- `steps`: `{id, title, duration, pause, labels, callouts, highlights, dim}`.
- Step `labels` contains reusable label IDs.
- Step `callouts` contains label-shaped entries plus `max_width` and `line_spacing`.
- Step `highlights` contains `{target_id, padding, color, width}`.
- Step `dim` is null or `{target_ids, opacity}`.

Annotation values are concrete, resolved values; null is not a request to reuse a theme default. Tutorial identity IDs are unique across targets, labels, callouts, and steps. DrawCV drawable IDs are a separate namespace. No duplicate target binding, shared step-owned callout, duplicate shown label, duplicate focus target, or duplicate highlight is accepted.

The packaged [lesson-v2.schema.json](../src/tutordraw/lesson-v2.schema.json) is a JSON Schema 2020-12 document. Load it without a checkout:

```python
from importlib.resources import files
import json

schema = json.loads(files("tutordraw").joinpath("lesson-v2.schema.json").read_text())
```

The schema checks document structure. `Tutorial.from_dict` additionally checks identity uniqueness, cross-references, authoring constraints, and the embedded DrawCV document. JSON Schema alone cannot verify reference integrity. Unsupported versions and unknown TutorDraw fields fail clearly; v1 loading assigns duration=3.0 and pause=0.0 to every step; subsequent saves emit v2. The original input is unchanged. The v1 schema remains packaged for validating older documents. v2 requires finite duration > 0 and pause >= 0; v1 rejects timing fields. Older a4 readers cannot load v2.

## Failure behavior and file preservation

Content failures raise `LessonFormatError`, a subclass of TutorDraw ValidationError. Missing files, permissions, and I/O failures remain standard filesystem errors. Invalid UTF-8 raises LessonFormatError. A dangling target or malformed scene prevents saving before an existing destination is touched.

Existing files and symlinks are refused by default. Explicit overwrite replaces a file only after content is validated and written to a temporary file. New saves use exclusive creation, including collision protection after preflight. A failed partial new write is removed. A new file may be visible during copying; this is not a cross-process database transaction.

## Portability boundaries

No pickle, callbacks, or executable Python source is stored by TutorDraw. DrawCV handles its own scene serialization, including embedded raster images. Rich font references/custom asset loaders remain subject to DrawCV's support and environment; the format is not an external-asset bundler or a sandbox for arbitrary untrusted documents.

Undo history, live object identity, render caches, and output PNGs are not persisted. Documents are loaded in memory; no streaming or large-document quota is implemented. Source edits during save/load are unsupported. Hidden emphasis targets and off-canvas panels can be saved, but normal rendering checks still apply when previewing.

# Architecture and planned extensions

Status: M1 foundation implemented: targets, labels, independent steps, scene
copying, bounds layout, and `render_step`. Callouts, attention effects, themes,
batch export, and timing below remain proposals. See `API.md` for the actual API.

## Responsibility boundary

```text
Author's DrawCV scene + TutorDraw lesson definitions
                         |
                Resolve an independent step
                         |
               Copy scene and resolve targets
                         |
          Apply attention and generate annotations
                         |
                 DrawCV OpenCVRenderer
                         |
                  Canvas / PNG output
```

TutorDraw owns meaning, attachment rules, layout, and teaching sequence.
DrawCV owns shapes, transforms, text primitives, styles, and pixel rendering.
Use composition: a teaching target references a DrawCV drawable instead of
requiring tutorial-specific subclasses of every shape.

## Core concepts

| Concept | Responsibility |
| --- | --- |
| `Tutorial` | Source scene reference, targets, annotations, ordered steps, theme |
| `Target` | Tutorial-local identity, source drawable ID, optional human-readable name |
| `Anchor` | Rule for resolving an attachment position from current target geometry |
| `Annotation` | Reusable label/leader definition with its own tutorial-local ID |
| `Step` | Explicit visible annotations, callouts, highlights, dimming, title and description |
| `Theme` | Defaults for colors, text sizing, padding, line widths, and spacing |
| DrawCV adapter | Scene copying, recursive identity lookup, bounds, and rendering integration |

Start with labels and step-owned callouts; avoid inventing a generic plugin
framework before there are multiple concrete annotation types.

## Target identity and ownership

- Register only drawables that belong to the tutorial's source scene, including
  descendants of a group. Reject foreign or detached objects clearly.
- Store stable drawable IDs, not names or Python memory addresses, as references.
- Resolve targets recursively. Verify `Scene.get()` behavior before relying on
  it for children; wrap any traversal in the adapter.
- Reject duplicate drawable IDs if they make reference resolution ambiguous.
- Give targets separate tutorial IDs so tutorial metadata does not need to be
  inserted into the user's DrawCV objects.
- Registration of the same drawable should return its existing target; conflicting
  explicit target names should raise a useful validation error.
- A deleted target should fail rendering with a target-specific error. Do not
  silently attach its annotations to another object or old coordinates.
- Read the source scene at render time so edits made after registration are
  reflected in future renders. Concurrent scene editing during render is outside
  the first-release contract.

## Step semantics

Each step resolves against the current authored source scene independently.
No step implicitly inherits another step's presentation state.

1. Source artwork is visible according to its authored state.
2. Reusable annotations are hidden unless the step explicitly shows them.
3. Step-owned callouts and highlights exist only in that step.
4. Dimming exists only in the step that requests it.
5. Highlighting does not implicitly reveal authored-hidden artwork; reject an
   attention request for an effectively hidden target with a clear explanation.
6. Adding an annotation does not alter the source drawing.

The first release has no time axis or transitions. Later timed playback should
compile these step definitions into time-dependent presentation state. It must
preserve the ability to render or seek directly to a chosen state.

## Anchors and layout

Use world-space, axis-aligned visual bounds for the initial center/left/right/
top/bottom anchors. These are bounds anchors, not guaranteed points on the shape's
actual outline. Group transforms must be included. Document the chosen DrawCV
bounds method and whether stroke/effects are included after verifying behavior.

Recompute anchors on every render. In the initial fixed-canvas output, annotation
offsets, padding, and line widths are canvas-pixel values and do not inherit a
target's rotation or scale. Text remains upright when the target rotates.

Lay out text first, then compute the leader endpoint on the text panel boundary.
Draw leader lines behind label panels and text. Use a separate generated overlay
layer; do not attach annotations as children of their target, which could create
transform inheritance or bounds feedback problems.

Default labels can use the requested side with a theme-defined gap. Callouts need
a maximum width, wrapping, padding, and an explicit placement override. Provide
diagnostics for off-canvas panels. Automatic collision avoidance is deferred.

## Attention and group dimming

Initial highlights are padded rectangular outlines based on target bounds.
Preserve source styles; create temporary overlay geometry rather than overwriting
the target's fill or stroke.

Dimming should multiply authored opacity by a step-level factor in the working
copy. Avoid applying the factor at both a group and its descendants. For a
focused child, leave its ancestor opacity unchanged and dim unrelated sibling
branches. For a focused group, preserve its entire subtree. An ancestor's own
authored opacity still affects its children. Generated annotations remain undimmed.

Complex groups, masks, and blend modes may affect appearance. Test representative
nested groups and document any unsupported case instead of promising perfect
spotlight isolation. This initial feature is artwork opacity reduction, not a
pixel-level spotlight compositor.

## Rendering and source preservation

Prefer creating a working scene copy, applying the step there, generating overlay
objects, and passing it to DrawCV's renderer. Do not temporarily mutate the live
scene and rely on undo to repair it.

Evaluate DrawCV's public scene serialization round trip as the first copying
candidate. Verify that it preserves drawable IDs, transforms, hierarchy, styles,
and supported assets. Do not assume cloning individual objects preserves IDs or
scene relationships. If the round trip cannot represent an object type, raise a
clear unsupported-copy error until a tested copy strategy exists.

Proposed output methods:

- `render_step(index)` returns a DrawCV `Canvas`; step indices are zero-based.
- `export_steps(directory)` writes `step-001.png`, `step-002.png`, etc., and
  returns their paths. Keep filenames independent of user-supplied lesson titles.
- Existing output files raise an error by default; an explicit overwrite option
  can permit replacement. Validate all destination names before starting export.
- If an export partially fails, report the failed step and already-written files.

Repeated rendering must not accumulate overlays, change source object values,
or add source history entries. Error paths must preserve these guarantees too.

## Proposed source layout

```text
pyproject.toml
src/tutordraw/
    __init__.py
    tutorial.py
    targets.py
    annotations.py
    steps.py
    themes.py
    layout.py
    rendering.py
    errors.py
    adapters/drawcv.py
examples/
    cell_tutorial.py
tests/
docs/
```

Create modules as needed rather than generating empty abstractions. Public
symbols should be intentionally exported from `tutordraw`.

## Dependency evidence and unresolved integration work

Local files inspected on 2026-09-20:

- `C:/Projects/DrawCV/pyproject.toml`: distribution `pydrawcv`, version
  `0.10.0.post1`, Python `>=3.12`.
- `drawcv/__init__.py`: public `Scene`, `Drawable`, `Group`, `Text`, `Point`,
  `OpenCVRenderer`, styles, and animation exports.
- `drawcv/core/drawable.py`: IDs, transform hierarchy, bounds APIs, `to_world`,
  and `clone(new_id=True)`.
- `drawcv/scene.py`: object lookup, JSON/dictionary serialization, and rendering
  at time APIs.
- README: editable scenes, retained text, PNG and video rendering documentation.

M1 subsequently tested the published 0.10.0.post1 wheel on Windows/Python 3.12,
including basic Hershey text, nested group anchors, and scene copying via
`Scene.from_dict(deepcopy(scene.to_dict()))`. The dependency is pinned to that
release. Wrapping, advanced assets, rich typography, and broader compatibility
remain unverified.

## Persistence and extensibility

Lesson save/load is deferred. Keep model fields explicit and reference-based so
a later versioned lesson schema can store tutorial definitions alongside a
DrawCV scene. Do not put arbitrary callbacks into the core model as the only way
to describe a step. Do not promise compatibility for a schema that does not yet
exist.

# Implemented API — 0.1.0a1

This guide covers M1 only. Public symbols import from `tutordraw`.

## Tutorial

`Tutorial(scene, *, title="")` holds a reference to a DrawCV `Scene`, read afresh at render time. Titles are metadata, not automatically rendered text.

`tutorial.target(drawable, *, name=None) -> Target` registers a scene member, including a nested group child. Registering the same object again returns its existing target. Explicit names must be nonempty and unique; a conflicting name raises `ValidationError`.

`tutorial.step(title) -> Step` appends an independent step. Titles must be nonempty strings; duplicate step titles are allowed. `tutorial.steps` returns a tuple in creation order.

`tutorial.render_step(index, *, alpha=False) -> drawcv.Canvas` renders a zero-based step through a copied scene. Negative indices and booleans are rejected. Set `alpha=True` for BGRA output with a transparent source background. Save through `canvas.save(path)`.

Batch export is not implemented. `Canvas.save` can overwrite existing files. The collision-safe export proposal in the architecture applies to a future TutorDraw exporter.

## Target and Label

Create targets through `Tutorial.target` and labels through `Target.label`, rather than directly constructing them. Targets expose immutable `id`, `drawable_id`, and `name` fields.

```python
label = target.label(
    "Nucleus", anchor="right", leader=True,
    gap=32, offset=(0, 0), font_scale=0.7, padding=10,
)
```

The returned `Label` is immutable and initially absent from all steps.

| Option | Behavior |
| --- | --- |
| `text` | Nonempty, single-line printable ASCII |
| `anchor` | `left`, `right`, `top`, `bottom`, or `center` of world-space bounds |
| `leader` | Whether to draw a straight leader |
| `gap` | Nonnegative pixels from anchor to near panel edge |
| `offset` | Additional `(x, y)` pixel offset, allowing either sign |
| `font_scale` | Hershey scale, greater than zero and at most 10 |
| `padding` | Nonnegative pixels around measured text bounds |

The `center` anchor places the label to the right of the target center. Labels remain upright. Leaders end at the panel boundary along a ray from panel center toward the target. If the target lies inside the panel, the leader is omitted. Colors are fixed in M1; themes come later.

## Step

`step.show(*labels) -> Step` adds registered labels from the same tutorial and returns the step for chaining. Showing a label twice does not duplicate it. Invalid additions leave the step unchanged. `step.labels` returns a tuple.

Steps never inherit another step's visible labels. Explicitly show a label in every step that needs it.

## Errors and warnings

- `TutorDrawError`: base exception.
- `ValidationError`: invalid options, foreign references, missing targets, duplicate IDs, or invalid step indices. Also a `ValueError`.
- `SceneCopyError`: failure copying through DrawCV's document API; the original exception is chained.
- `LayoutWarning`: an annotation extends outside the canvas; rendering proceeds.

DrawCV render/save errors propagate. Source content and history remain unchanged if rendering fails.

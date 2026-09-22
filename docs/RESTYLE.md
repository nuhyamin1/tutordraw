# Changing the artwork per step

New in development **0.1.0a8**. Until now a lesson was one fixed drawing with
annotations layered on top: steps could point at things but never change them.
A step can now move, recolour, fade and hide its targets, so a lesson can show
something happening rather than only describing it.

```python
beat = lesson.step("Totality")
beat.restyle(moon, move=(0, 190), fill=(168, 68, 52))
beat.restyle(sun, opacity=0.35)
beat.restyle(shadow, visible=False)
```

Run `python examples/eclipse_lesson.py` for the worked example: the Moon moves
into Earth's shadow and turns red across four beats of one source drawing.

## API

`step.restyle(target, *, move=None, fill=None, opacity=None, visible=None) -> Step`

| Option | Behavior |
| --- | --- |
| `move` | `(dx, dy)` pixels, **relative to wherever the source placed the target**. Either sign. |
| `fill` | RGB tuple. Sets a shape's fill colour, or a `Text` object's colour. |
| `opacity` | Absolute value from 0 to 1, replacing the authored opacity. |
| `visible` | `False` removes the target from this step entirely. |

At least one option is required; an empty call raises `ValidationError`.
Returns the step, so calls chain. Repeating `restyle` for the same target
**replaces its settings completely**, exactly as `highlight` does — options you
leave out are cleared, not remembered.

## Contracts

- **The source drawing is never touched.** Changes apply to the working copy
  each render makes, so steps stay independent and can render in any order.
  This is the difference between `restyle` and editing `target.drawable`:
  editing the source is retroactive and changes every step.
- **Attached annotations follow.** Restyles are applied before labels,
  callouts, highlights and dimming are computed, so a moved target takes its
  label, leader line and highlight box with it. Moving by `restyle` produces
  pixel-identical output to moving the source object by the same amount.
- `move` composes with the source transform: a target already translated by 40
  and restyled with `move=(60, 0)` renders at 100.
- **`opacity` is absolute; dimming still multiplies.** `restyle(opacity=0.5)`
  sets the value, and a later `dim_others` multiplies unrelated branches on top
  of it. An explicitly faded target that is also dimmed ends up fainter than
  either alone.
- `visible=False` genuinely hides the target. Highlighting or focusing a hidden
  target raises `ValidationError` at render time, as it always has.
- `fill` needs something to colour. Shapes have a fill and `Text` has a colour;
  `Line` and `Group` have neither and raise `ValidationError` at authoring time,
  naming the type. Existing fill opacity and enabled flags are preserved.
- **A gradient or image fill can be recoloured.** `fill` replaces it with the
  solid colour, so a gradient sphere can still be turned red. When such a step
  animates, the blend starts from the unweighted mean of the gradient's stop
  colours; an image paint has no colour to start from, so its fill cuts
  straight to the new value instead of interpolating.
- Targets must belong to this tutorial, as everywhere else in the API.

## Persistence

Restyles are saved in lesson schema v3 and later. Older schemas still load with
no restyles, and saving always writes the current version. Readers built for an
older alpha reject newer files, which is the intended strict behavior. See [PERSISTENCE.md](PERSISTENCE.md).

## What this does and does not give you

It covers a large part of progressive reveal: hide artwork in early beats and
reveal it later with `visible`. It does **not** reveal *annotations*
progressively — every label and callout in a step still appears at once.

Motion is a jump at the cut unless the step opts into animation with
`step.animate()`; see [ANIMATION.md](ANIMATION.md).

Not supported: stroke colour and width, scale, rotation, text content, z-order,
and adding or removing objects. Those either need new API or belong in the
source drawing.

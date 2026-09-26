# Revealing annotations one at a time

New in development **0.1.0a11**. Until now every label and callout in a step
appeared at once, which is wrong for a narrated lesson: the narrator introduces
one thing at a time while the picture shows everything.

```python
beat = lesson.step("Cast", duration=6)
beat.show(sun_label, earth_label, moon_label)          # immediately
beat.explain(earth, "Sunlight falls on the Earth.", at=1.5)
```

Run `python examples/eclipse_lesson.py`: every explanation arrives a beat after
its labels.

## API

Both existing methods take an optional delay in seconds from the start of the
step. Nothing else changes.

- `step.show(*labels, at=None) -> Step`
- `step.explain(target, text, ..., at=None) -> Callout`

`at=None` (the default) means immediately, exactly as before. One `show` call
applies its `at` to every label in that call, so call it repeatedly to build a
sequence. `step.revealed_at(annotation)` reports an annotation's delay, and
`step.reveals` gives the whole mapping.

## Contracts

- **A step with no delays is unchanged.** It stays a hard cut and every frame
  still equals `render_step`, so existing lessons render identically.
- A delay alone makes the step time-varying. You do **not** need `animate()`,
  though the two combine: see [ANIMATION.md](ANIMATION.md).
- **`render_step(index)` always shows every annotation**, delayed or not, so
  PNG export still reads as the lesson's beats. Only `render_at_time`, and
  therefore `render_frames` and `export_video`, honour the delays.
- Delays are measured from the start of the step, not the start of the lesson.
- A delay longer than the step's duration reveals at the end rather than never,
  so playback and `render_step` always agree. Changing a step's duration later
  cannot strand an annotation.
- The same label shown in two steps can have a different delay in each; reveals
  belong to the step, not the annotation.
- `at` must be a finite number ≥ 0. Booleans and strings are rejected.
- Delays are saved in **lesson schema v5**; older schemas load with none.

## Appearing, or fading in

By default an annotation appears whole at its moment. `Theme(fade_seconds=0.4)`
fades every label, callout, mark and highlight in over that long instead,
from the moment it would have appeared (after its stroke draws on, with
`draw=True`; the stroke itself draws rather than fades). The lesson's timing
is unchanged: the fade starts on the narrated word, and everything is whole
at the step's end, so `render_step` is unchanged. A label shown in the
previous step and in this one from its start, and a highlight on the same
target, are already on screen and do not fade again. PNG, video and the
browser player (`data-td-fade`) fade alike. Unreleased; saved with the theme
in lesson schema v13.

## Not implemented

Sliding annotations in, or a fade per annotation rather than per lesson. Revealing part of one callout, such as
line by line. Timing highlights or dimming, which remain step-level emphasis
applied for the whole step. Automatic pacing from the text's length, which
belongs in whatever supplies the narration.

Note you could already approximate reveals by adding one step per reveal; this
exists so a beat that is one narrated thought stays one step.

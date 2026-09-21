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

## Appearing, not fading

An annotation appears whole at its moment. There is no fade, because a caption
landing as the narrator says it is what this is for, and a fade would mean
inventing a duration nobody asked for. Pair a step's `animate()` with artwork
`restyle` if you want motion; the annotations still pop in.

## Not implemented

Fading or sliding annotations in. Revealing part of one callout, such as
line by line. Timing highlights or dimming, which remain step-level emphasis
applied for the whole step. Automatic pacing from the text's length, which
belongs in whatever supplies the narration.

Note you could already approximate reveals by adding one step per reveal; this
exists so a beat that is one narrated thought stays one step.

# Animating between beats

New in development **0.1.0a10**. `restyle` made change expressible, but motion
was a jump at the cut: the Moon teleported into Earth's shadow. An animated
step eases into its restyled state over its duration instead.

```python
entry = lesson.step("Entry", duration=6).animate("ease_in_out")
entry.restyle(moon, move=(0, 190))
```

Run `python examples/eclipse_lesson.py` and watch beats three and four: the
Moon slides into the shadow and fades to red.

## API

`step.animate(easing="ease_in_out", *, seconds=None) -> Step` marks the step
animated. `step.hard_cut() -> Step` undoes it. `step.easing` reports the curve
or `None`. With `seconds` (unreleased, schema v11) the motion finishes that
long after the step starts and the rest of the step holds still
(`step.motion`), so a step can make room on a full board in a moment and
then write; reveals and draw-on keep the step's own clock, and the player
gets `motion` in the step payload.

Easing names come from DrawCV, which owns both the curves and their
validation: `linear`, `ease_in`, `ease_out`, `ease_in_out` and their `_quad`,
`_cubic`, `_sine`, `_expo`, `_circ`, `_bounce` and `_elastic` variants. Names
match case-insensitively and are stored lowercase. An unknown name raises
`ValidationError`.

## What interpolates, and from what

A step's restyle is expressed relative to the **source** drawing, so animation
runs from **the previous step's state** to this step's. Step one animates from
the untouched drawing.

This falls out of step independence and is usually what you want. In the
eclipse lesson beat three moves the Moon down 190 and beat four also holds it
at 190, so beat three slides and beat four stays put while the colour changes.
A target restyled in one step and left alone by the next **slides back**,
because the next step's state is the source state.

| Property | Behavior |
| --- | --- |
| `move` | Interpolated. Attached labels, leaders and highlights follow. |
| `opacity` | Interpolated from the previous value, or the source's. |
| `fill` | Interpolated channel by channel in plain RGB. A gradient fill blends from the mean of its stops; an image fill cuts. |
| `visible` | **Not** interpolated. The step's own value applies throughout. |
| `scale` | Interpolated with its pivot's shift, so every point moves in a straight line; the player's one start frame is exact. Kit text scales; labels keep their size. |

`scale` (unreleased, schema v12) shrinks or grows a target about a point of
its bounds that stays put, for a board that makes room:

```python
step.animate("ease_in_out", seconds=0.8).restyle(graph, scale=0.8, pivot="top_left")
```

Register a graph to scale with `tutorial.target(axes.group, obstacle=False)`,
so its own points' labels may still sit on it. A new pivot in a later step
starts where the last step left the target; lint's `SCALED_TEXT_SMALL` warns
when the drawing's own text ends under 12 px. DrawCV's raster renderer draws
scaled built-in text clipped (tick numbers in a PNG or video); the browser
player writes native text and is unaffected.

A `move` given `via` offsets (unreleased) runs along the polyline from the
previous step's offset through them to `move`, at an even speed along its
length, instead of in a straight line; sample a curve into it with
`Axes.along`, so a point slides along y = f(x):

```python
way = axes.along(lambda x: x * x, 1, 2, samples=32)   # offsets from (1, 1)
step.animate().restyle(dot, move=way[-1], via=way[1:-1])
```

The browser player gets such a step as 12 evenly timed keyframes with the
easing applied (`web.PATH_KEYFRAMES`), and walks between them; collision
avoidance judges labels over points along the way, not only its ends.

Plain RGB is simple and predictable rather than perceptually even; a mid-point
may look duller than you expect. Pair `visible=True` with `opacity` if you want
something to fade in rather than appear.

## Contracts

- **Hard cuts remain the default.** Without `animate()` nothing changes, and
  every frame still equals some `render_step` output. That property is what
  timing and video rely on, and it is only relaxed for steps you opt in.
- **`render_step(index)` always shows the finished state**, animated or not.
  PNG export is unaffected, so a still export still reads as the lesson's beats.
- The animation runs across the step's `duration`. A trailing `pause` holds the
  finished state, matching the existing pause meaning.
- `render_at_time` interpolates, so `render_frames` and `export_video` animate
  automatically. Seeking stays deterministic: the same time gives the same image.
- The source drawing, its history and step independence are untouched, exactly
  as for a static render.
- Animation is per step. There is no per-property timing, delay, or
  keyframing within a step.

## Persistence

The easing name is saved in **lesson schema v4**, as a nullable string per step.
Schemas v1, v2 and v3 still load, with no animation, and saving always writes
v4. See [PERSISTENCE.md](PERSISTENCE.md).

## Cost

Animation does not make a frame more expensive: every frame was always rendered
from scratch, and an animated frame measured the same as a static one. What
changes is that consecutive frames now differ, so nothing can be reused.

Measured on the 27-second eclipse lesson, Windows 11 / CPython 3.12: about
35 ms per frame, so 324 frames at 12 fps took 11.4 s to generate and 13.5 s to
encode. At 30 fps expect roughly two and a half times the lesson's length. For
live playback, 35 ms per frame is about 28 fps of headroom; pick a frame rate
with that in mind, or pre-render.

## Not implemented

Interpolating anything `restyle` does not cover, such as stroke and
rotation (so a tangent cannot yet sweep round as its point slides). Per-property
or staggered timing within a step. Motion paths are polylines: a curve is as
smooth as it is sampled. Fading annotations in: they can now be delayed with `at=` (see
[REVEAL.md](REVEAL.md)) but still appear whole rather than fading.

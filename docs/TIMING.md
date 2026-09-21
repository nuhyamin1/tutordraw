# Timed lessons

Implemented in **0.1.0a5**, released as part of 0.1.0a11.
Development 0.1.0a6 encodes this playback to a video file; see [VIDEO.md](VIDEO.md).
This is deterministic playback of static steps with hard cuts.

```python
from drawcv import Scene
from tutordraw import Tutorial

lesson = Tutorial(Scene(640, 360))
intro = lesson.step("Introduction", duration=2, pause=1)
lesson.step("Review", duration=4)
# Attach labels/highlights/callouts using the existing authoring API.
assert lesson.duration == 7
assert lesson.step_at_time(2.5) == 0  # Pause holds the introduction.
assert lesson.step_at_time(3) == 1
canvas = lesson.render_at_time(3)
for frame in lesson.render_frames(fps=2):
    pass  # Consume each independent DrawCV Canvas: 14 frames in this example.
intro.set_timing(duration=3, pause=1)
```

For a real annotated lesson, run `python examples/timed_lesson.py`. It saves a
10-second cell lesson, produces previews on both sides of the first cut, and
consumes 20 frames at 2 fps under `output/timing`.

## Contracts

- All times are seconds. Step duration must be finite and positive; pause finite
  and nonnegative. Booleans are rejected as numbers. Defaults are duration 3, pause 0.
- `set_timing` validates both values before changing either; omitting pause resets
  it to zero. `duration` and `pause` properties cannot be assigned directly.
- A step occupies duration + pause seconds. Its pause holds its full image;
  it does not show a blank frame or wait for interaction. Final pauses also count.
- Intervals are `[start, end)`. An exact internal boundary selects the next step.
  The exact total-duration endpoint selects the final step for convenient seeking.
  Negative, nonfinite, or beyond-end times raise `ValidationError`; no clamping.
- Boundaries use cumulative Python floating-point seconds, with no epsilon
  snapping. Totals that overflow or cannot represent a positive interval fail.
- An empty tutorial has duration 0; seeking and frame generation require a step.
- Frames use positive integer fps, count `ceil(duration * fps)`, timestamps
  `k / fps` starting at zero. The final endpoint is not an extra frame. Encoded
  playback may round the requested duration up by less than one frame period.
- Invalid fps/alpha/empty lessons fail when `render_frames` is called. Rendering
  failures propagate when its iterator is consumed. Each Canvas is independent.
- Frames are rendered lazily without accumulating images. Each frame currently
  copies and renders a scene; no repeated-step cache or speed guarantee exists.
- Source artwork, history, and independent-step state remain unchanged by rendering.
  Editing the source or lesson while consuming an iterator is unsupported.

## Persistence and scope

Schema v2 stores duration and pause on each step. Loading v1 assigns 3/0 defaults,
preserving IDs and static images. Saving always produces the current version, v5. See [PERSISTENCE.md](PERSISTENCE.md).

Steps can now ease into their restyled state; see [ANIMATION.md](ANIMATION.md).
Annotations can be delayed within a step; see [REVEAL.md](REVEAL.md). Hard cuts
remain the default, so every frame of a lesson using neither `animate()` nor a
reveal delay still equals some `render_step` output. No player UI, crossfades between whole
images, timed captions, audio, or DrawCV
animation sampling is implemented. `render_at_time` selects a TutorDraw step;
it does not advance timelines attached to source DrawCV objects. Video export
(`export_video`) consumes this frame iterator and is documented in [VIDEO.md](VIDEO.md).

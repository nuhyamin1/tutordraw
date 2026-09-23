# Visual vocabulary (schema v8)

New in development 0.1.0a12. Everything here is step-owned, so steps stay
independent: nothing carries over to the next step unless you repeat it.
[`examples/lever_lesson.py`](../examples/lever_lesson.py) uses all of it and
lints clean.

## Marks

Marks are drawn annotations that point, connect and measure. Each method
returns a `Mark` (as `explain` returns a `Callout`), so call them one per line
rather than chaining. Every mark takes `at=` and `draw=` (see below); text is
optional except where noted and is one line.

| Call | Draws |
| --- | --- |
| `step.connect(a, b, text=None, *, bend=0, both=False)` | An arrow. `a`/`b` are targets or `(x, y)` points; a target end stops just outside its bounds, a point end lands exactly there, so `connect((x, y), ball, "push")` is a force arrow. `bend` (-1..1) curves it; `both` heads both ends. |
| `step.brace(*targets, text=None, side="bottom")` | A curly brace along one side of the targets' combined bounds, caption beyond its tip. |
| `step.measure(a, b=None, text=None, *, axis="x", offset=24)` | A dimension line. One target: its width (`"x"`) or height (`"y"`). Two refs: between their centres along `x`, `y`, or directly (`"free"`). `offset` lifts it clear of the art. |
| `step.angle(vertex, a, b, text=None, *, radius=32)` | An arc at `vertex` between the directions to `a` and `b`, the smaller way round. Refs may be targets (their centres) or points. |
| `step.number(target, n=None, *, corner="top_left")` | A numbered badge. `n` defaults to the next number in the step. Appears whole; it takes `at=` but not `draw=`. |

Fixed `(x, y)` points are scene coordinates, so they zoom with the camera.
Mark geometry follows live target bounds, so marks track a restyled or
animated target. Marks use the theme's `leader_color` and `leader_width`, and
their captions use the normal panel style.

Label placement treats every mark as an obstacle. Mark captions are not moved
automatically, so two marks' captions can collide; `lint()` reports it as
`ANNOTATION_OVERLAP` and the fix is the mark's own `offset`, `radius`, `bend`
or `side`.

## Drawing on

`draw=True` on `show`, `explain`, `highlight` and any mark except `number`
draws its strokes on over `Theme.draw_seconds` (default 0.6) starting at its
`at=` time. Text and panels appear when the stroke completes. Leaders grow
from the target toward the panel; highlight boxes trace clockwise from the
top-left; arrows grow with their head riding the tip.

At the end of a step everything is complete, so `render_step` and PNG export
never show a half-drawn stroke. `layout(i, time=t)` reports an item only once
it has finished drawing.

## Camera

```python
close = lesson.step("The pivot", duration=3).animate().zoom_to(fulcrum, padding=90)
```

`zoom_to(*targets, padding=40, max_scale=4)` frames the targets' end-of-step
bounds. The artwork zooms but annotations do not: text is the same size at any
zoom. `reset_camera()` clears it. A step without `zoom_to` shows the whole
canvas; there is no inherited camera. On an `animate()`d step the view moves
from the previous step's framing, centre linearly and scale geometrically, and
label placement is decided against the step's final framing so labels do not
jump sides mid-zoom. `layout(i).camera` is `(scale, tx, ty)`, mapping scene to
screen as `scale * p + t`, or None.

## Highlights that follow the shape

`step.highlight(target, shape="outline")` outlines the target's own shape,
grown by `padding`, instead of a box around its bounds. It needs a closed
shape; groups, text and open lines are refused when you call it, with a
message saying to use `shape="box"`. Highlights also take `at=` and `draw=`.

## Halo behind bare text

`box=False` text gets a `Theme.halo_width` (default 3 px) outline in
`panel_color`, so it stays readable over artwork. `halo_width=0` turns it off.
Lint counts a halo of 2 px or more as separating the text from what is behind
it.

## Saved lessons

All of this is saved in lesson schema v8: step `marks`, `draw` and `camera`;
highlight `at`, `draw` and `shape`; theme `draw_seconds` and `halo_width`.
Lessons from v1 to v7 still load, taking the defaults. A lesson saved as v8
cannot be opened by 0.1.0a11 or earlier.

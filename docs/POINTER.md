# The presenter's pointer

New in 0.3.0a1 (unreleased). A hand that moves to whatever the narrator is
talking about, as a teacher points at the board: it shows where attention
goes next, which a label or a highlight does not.

```python
step.point(nucleus)                      # the pointer goes to the nucleus
step.point(membrane, at=2.5)             # and on to the membrane at 2.5 s
step.narrate(words, {membrane: "its membrane"})   # or let the voice time it
```

## One pointer per lesson

- It **fades in** at a step's first stop (0.3 s), **glides** from stop to
  stop (`Theme.pointer_seconds`, 0.6 s, eased), and **taps** as it arrives
  (it presses to 86% and back over 0.3 s).
- It **carries over**: a step that points somewhere starts from where the
  previous step's pointer rested and glides on from there.
- A step that points at nothing shows **no pointer**.
- A stop that comes while the pointer is still gliding or tapping waits for it.
- The finished step (`render_step`, the last frame) rests on its last stop.

## Where it points

The fingertip sits on the target's own outline, a few pixels off it (the
leader's `ink_point`), and the hand reaches in from the first free side:
down and to the right, like a cursor, unless something is there. It avoids
the step's labels, callouts, marks and other targets, and stays on the
canvas. What the target lies on (a cell round its nucleus) does not count.
The side is chosen once from the step's finished picture, so in an animated
step the pointer aims where things end up.

## API

| Call | Does |
| --- | --- |
| `step.point(target, *, at=None)` | A pointer stop `at` seconds into the step (default 0). Several per step; two at the same time are refused. Returns the step. |
| `step.points` | The step's stops (`pointer.Stop`: `target`, `at`), in time order. |
| `step.narrate(words, {target: phrase})` | A target cue now times its first pointer stop as well as its highlight; a target needs one or the other. |
| `Theme(pointer_style="hand", pointer_seconds=0.6)` | `"hand"`, `"cursor"` (an arrow cursor) or `"dot"` (a laser dot); glide seconds. |
| `tutorial.layout(i, time=t).pointer` | Its pose then: `x`, `y` (the tip), `angle`, `scale`, `opacity`; None when not shown. |

## Everywhere alike

PNG, video and the browser player show the same pointer at the same time:
each step's movement is worked out once as keyframes (`pointer.track`), which
Python draws and the player is sent (`web_step(i)["pointer"]`: `style`,
`keys`, `outline`). `tests/test_player.py` checks the two agree.
`describe()` says "The pointer points at the nucleus." in order, and lint
`POINTER_WITH_HIGHLIGHT` (info) notes a target that is both pointed at and
highlighted in one step: one is enough.

## Saving

Lesson schema v13 saves each step's `points` (`target_id`, `at`) and the
theme's `pointer_style` and `pointer_seconds`.

# Browser playback and streaming

New in development 0.1.0a12. A lesson can play in any browser as crisp,
scalable SVG, and it can play *while it is still being written*: send each step
as soon as it is authored and the player plays what it has, then waits.
[`examples/web_lesson.py`](../examples/web_lesson.py) writes both forms.

## Python API

| Call | Returns |
| --- | --- |
| `tutorial.to_svg(index, *, time=None)` | One frame as standalone SVG text. `time` is seconds into the step; None is the finished step. |
| `tutorial.web_step(index)` | One step's payload for the player: a JSON-ready dict. |
| `tutorial.export_web(path, *, overwrite=False)` | Writes one self-contained HTML page (player + lesson) and returns its path. |
| `tutordraw.web.player_source()` | The player's JavaScript, to embed in your own page. |

`export_web` refuses to replace an existing file unless `overwrite=True`, like
`save_json`. The page needs no server and no network.

## Streaming a lesson

```javascript
const player = new TutorDrawPlayer(element, {width: 1000, height: 560, title: "Levers"});
player.play();
// Whenever a step arrives, over a WebSocket, fetch stream or anything else:
player.append(payload);          // payload = tutorial.web_step(i), as JSON
```

The player loads step 1 as soon as it arrives. At the end of the last step it
has, it holds the frame and shows "waiting for the next step…", then carries on
the moment the next one is appended. Steps may arrive out of order; each has
its `index`. `player.pause()`, `player.play()` and `player.seek(index, time)`
are available, and `player.onstep = (index, step) => …` fires on each step,
for example to start that step's narration audio. A step with a prompt holds
at its end until the learner answers; `player.onanswer = (index, result) => …`
reports each tap. See [PROMPTS.md](PROMPTS.md).

## The payload

`web_step(i)` returns `index`, `id`, `title`, `duration`, `pause`, `svg` (the
finished frame), `frames` and `easing`:

- A step that does not `animate()` has no `frames`: it cuts, as in Python.
- An animated step has one start frame, and `easing` is DrawCV's curve sampled
  at 65 points, so the browser eases exactly as `render_at_time` does.
- An animated step whose camera changes has 6 evenly timed frames with the
  easing already applied. A camera zooms geometrically, which no straight
  blend of coordinates reproduces; blending neighbouring keyframes does.

The player matches elements between frames by `data-drawcv-id` and
interpolates every numeric attribute whose shape agrees (path data,
positions, transforms, colours, opacity). Everything TutorDraw draws has a
stable ID, `td-<owner>-<role>`, so a label, leader or mark is the same element
in every frame and every step. Reveals and draw-on come from `data-td-at` and
`data-td-draw` on those elements.

## What differs from `render_step`

- **Text** is native SVG text in the browser's sans-serif, stretched to
  TutorDraw's measured width (`textLength`), so it always fits its panel. It
  is selectable and sharp at any size but not pixel-identical to the PNG.
  DrawCV 0.11.0 exports its built-in text as embedded PNGs; TutorDraw replaces
  them (see DECISIONS.md). Rotated or skewed text stays an embedded image.
- **Halos** are one stroked text (`paint-order: stroke`) instead of copies.
- **Arrowheads** of a drawing-on arrow appear when the stroke finishes rather
  than riding its tip.
- **Scaling**: the player draws the SVG at its native size and scales it with
  a CSS transform. DrawCV strokes are non-scaling, so scaling the `viewBox`
  instead would fatten every line on a small screen.

## Cost

Measured on the lever lesson (Windows, CPython 3.12): `web_step` takes 34 ms
for a static step, 96 ms for an animated step that zooms in (7 frames) and
290 ms for one that zooms back out with four marks drawing on. The whole page
is about 150 KB, mostly the camera keyframes.

Verified by eye in Chromium (the Claude desktop browser pane): the camera,
draw-on, motion and lever lessons match their Python renders at the same
moments, and a simulated stream waited for, then played, a step appended five
seconds late. No other browser has been checked.

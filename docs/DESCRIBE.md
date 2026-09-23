# Describing steps in words

New in development 0.1.0a12. `tutorial.describe(index)` says in plain English
what a step shows; `tutorial.describe()` does the whole lesson, one line per
step. For example, the last beat of the eclipse example:

> Totality. The moon turns red. The sun fades to 35%. Everything except the
> moon is dimmed. The moon is boxed. The moon is labelled "≈ 100 min". Then a
> note on the moon says: "Totality lasts up to ≈ 100 min. …"

## What it is for

- **Screen readers.** Every `web_step` payload carries its `description`. The
  player labels the picture with it and announces it through a polite live
  region as each step starts.
- **A model checking its own lesson.** Read the description back and compare
  it with what the narration says. If the narration says "the Moon turns red"
  and the description does not, the step does not show it.

## How it is built

Only from the lesson's structure, never from pixels, in this order:

1. The step title.
2. The camera: zooming in on targets, or back out to the whole scene.
3. Artwork changes **since the previous step**: appearing or being hidden,
   moving (by direction), turning a colour, fading. Restyles are stored against
   the source drawing, but a viewer sees the change from the last step, so a
   target that goes back to how the drawing has it "moves back" or "returns to
   its original colour". The first step compares with the source drawing.
4. Dimming.
5. Highlights, labels, notes and marks, **in the order they appear**, with
   "Then" wherever the step introduces things one at a time (`at=`).

Targets are called by their names ("the moon"); an unnamed one is "an unnamed
object", and a fixed point is "the point (x, y)". Colours are the nearest of
18 everyday names; directions are up, down, left and right. Numbered badges
read as one sentence ("the load, the fulcrum and the effort are numbered 1, 2
and 3").

Name your targets: `tutorial.target(shape, name="moon")` is what makes the
description readable.

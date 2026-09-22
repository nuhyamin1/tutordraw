# Author a visual lesson

Start with the runnable [cell example](../examples/cell_tutorial.py). Run it from
the repository root after installing TutorDraw:

```powershell
python examples/cell_tutorial.py
```

It exports three PNGs under `output/cell`. The example explicitly allows overwrite
so rerunning it refreshes those files. Library export defaults to refusing collisions.

## 1. Draw the subject

Create a DrawCV Scene and add its shapes before registering teaching targets.
The example draws a cell boundary, nucleus, another organelle, and a heading.
TutorDraw accepts the existing shapes; no replacement classes are necessary.

## 2. Attach reusable names

Create `Tutorial(scene)`, then register each subject with
`tutorial.target(shape, name="nucleus")`. Names must be unique in the tutorial.
Call `target.label("Nucleus", anchor="top")` to define a reusable label.
It appears only when a step calls `show(label)`.

## 3. Introduce the whole diagram

Create a step with `tutorial.step("Explore the cell")`. Show the cell label and
use `step.explain(cell_target, text, max_width=340)` for a wrapped explanation.
Width limits text; padding makes the full panel slightly wider.

## 4. Guide attention

In a second step, show the nucleus label, highlight its target, and call
`step.dim_others(nucleus_target, heading_target)`. The heading stays readable
because it is explicitly included in the focus set. Add a nucleus-specific
callout. Use `gap` and `offset` to keep panels clear of the diagram.

For nested structures, see [group_focus.py](../examples/group_focus.py).
A focused child retains authored opacity through its ancestors; unrelated
branches dim once, and a focused group preserves its whole subtree.

## 5. Review without inherited emphasis

Add a third step showing both labels. It does not inherit the second step's
highlight, dimming, or callout. Add its own review prompt with `explain`.

## 6. Export and refine

Use `tutorial.render_step(1).save("focus.png")` for one image, or
`tutorial.export_steps("lesson-output")` for the sequence. Batch filenames are
numbered in step order. Rendering a step in a different order changes nothing.

Move a source object and render again: its label, callout, and highlight follow
its current bounds. Review layout warnings and inspect the images; automatic
panels are moved apart automatically when they collide. Use a Theme for consistent spacing and
colors rather than repeating options throughout a lesson.

See [API.md](API.md) for signatures and [COMPATIBILITY.md](COMPATIBILITY.md) for
fonts, supported environments, source copying, and export limitations.

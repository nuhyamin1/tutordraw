# TutorDraw

**Explain what you draw, one step at a time.**

TutorDraw is a Python library for authoring visual tutorials using [DrawCV](https://pypi.org/project/pydrawcv/). DrawCV supplies drawing objects and rendering; TutorDraw attaches teaching annotations and organizes them into independent lesson steps.

## Status

**Published alpha [0.2.0a1](https://pypi.org/project/tutordraw/0.2.0a1/).** TutorDraw provides the tutorial workflow described below. Licensed under MIT, authored by Nuh Yamin. See the compatibility notes before relying on it in production.

0.2.0a1 is a large step from 0.1.0a11, hence the new minor version: it adds automatic label collision avoidance, arrows, braces, measurements and a camera, a browser player that streams, narration timing with captions, plain-English step descriptions, lint, eight teaching kits (axes, number line, flowchart, timeline, cycle, force diagram, cross-section, equations), tap-the-picture prompts, and lesson format v9. It requires `pydrawcv==0.11.0`, and lessons it saves do not open in 0.1.0a11. It is still an alpha: APIs may change.

Implemented:

- Register existing DrawCV objects or groups as teaching targets.
- Attach labels with optional straight leader lines.
- Configure bounds anchors, gap, offset, padding, font scale, and whether a label is drawn in a panel or as bare text.
- Keep labels attached when targets move, including through group transforms.
- Define independent steps and render them to DrawCV canvases and PNG images.
- Preserve source content and undo history, including on rendering failure.
- Add step-local wrapped callouts, rectangular highlights, and group-aware dimming.
- Customize shared typography, spacing, and colors through an immutable theme.
- Export ordered PNGs with collision checks and partial-failure reporting.
- Validate references/options and warn about off-canvas annotations.
- save/reopen complete versioned JSON lessons with stable IDs and validated references.

- step durations, trailing pauses, direct time seeking, and streaming frames; see [Timing](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TIMING.md).
- encode a timed lesson to a video file with collision-safe, all-or-nothing replacement; see [Video](https://github.com/nuhyamin1/tutordraw/blob/master/docs/VIDEO.md).
- annotate in Latin, Greek, Cyrillic or CJK and use technical symbols such as µm, °C, α, ½ and ×; see [Text](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TEXT.md).
- move, recolour, fade or hide a target for one step, so a lesson can show change rather than describe it; see [Restyle](https://github.com/nuhyamin1/tutordraw/blob/master/docs/RESTYLE.md).
- teach in Thai or Arabic with `pip install "tutordraw[typography]"` and a font you supply; see [Text](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TEXT.md).
- ease a step into its new state instead of cutting to it; see [Animation](https://github.com/nuhyamin1/tutordraw/blob/master/docs/ANIMATION.md).
- delay a label or explanation so a narrated beat introduces one thing at a time; see [Reveal](https://github.com/nuhyamin1/tutordraw/blob/master/docs/REVEAL.md).
- keep label and callout panels from overlapping each other, the highlight boxes, the artwork or the canvas edges, automatically and on by default; see [API](https://github.com/nuhyamin1/tutordraw/blob/master/docs/API.md).
- point, connect and measure: arrows, braces, dimension lines, angle marks and numbered badges; strokes that draw themselves on; a per-step camera that zooms the artwork but not the text; highlights that follow a shape's outline; see [Vocabulary](https://github.com/nuhyamin1/tutordraw/blob/master/docs/VOCABULARY.md).
- draw graphs with the axes kit: ticks, grid, curves (with asymptotes handled), points and guide lines, all ordinary DrawCV objects with named targets; see [Kits](https://github.com/nuhyamin1/tutordraw/blob/master/docs/KITS.md).
- build number lines, flowcharts, timelines, cycles, force diagrams and labelled cross-sections the same way, from a few calls each.
- typeset equations from LaTeX into named, highlightable pieces with the optional `math` extra; see [Kits](https://github.com/nuhyamin1/tutordraw/blob/master/docs/KITS.md).
- end a step with a question answered by tapping the picture ("Tap the nucleus."), with feedback, hints and the same check in Python; see [Prompts](https://github.com/nuhyamin1/tutordraw/blob/master/docs/PROMPTS.md).
- reveal each label, note, mark and highlight as the narration says it, from text-to-speech word timings, with live captions in the player; see [Narration](https://github.com/nuhyamin1/tutordraw/blob/master/docs/NARRATION.md).
- describe each step in plain English for screen readers, and so a model can check a step shows what its narration says; see [Describe](https://github.com/nuhyamin1/tutordraw/blob/master/docs/DESCRIBE.md).
- play a lesson in any browser as sharp SVG, or stream it one step at a time while it is still being written; see [Web](https://github.com/nuhyamin1/tutordraw/blob/master/docs/WEB.md).
- check a lesson for overlaps, crossing leaders, low contrast and other readability problems with `tutorial.lint()`, which returns fixes a model can apply; see [AI authoring](https://github.com/nuhyamin1/tutordraw/blob/master/docs/AI_AUTHORING.md).

Routed leader lines that bend around artwork remain planned.

## Install the alpha

```shell
python -m pip install tutordraw==0.2.0a1
```

The exact version selects this prerelease explicitly (plain `pip install tutordraw` skips alphas). Add `"tutordraw[math]==0.2.0a1"` for equations or `"tutordraw[typography]==0.2.0a1"` for Thai and Arabic. Requires Python 3.12+.

## Develop from this repository

Requires **Python 3.12+**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cell_tutorial.py
```

On macOS/Linux, use `.venv/bin/python` instead. Windows/Python 3.12 passes 171 tests (one symlink test skips without symlink privileges). Hosted CI passes on Windows, Linux, and macOS for Python 3.12–3.14. If `python` is unavailable, use the absolute path to an installed Python 3.12+ executable for the first command.

No DrawCV checkout is needed. TutorDraw pins the tested published dependency `pydrawcv==0.11.0`, which imports as `drawcv`. A broader compatibility range is future work. Use an explicit version or `--pre` when selecting an alpha release.

## Working example

```python
from drawcv import Circle, Color, FillStyle, Point, Scene
from tutordraw import Tutorial

scene = Scene(640, 360, background=Color.white())
shape = Circle(
    center=Point(180, 180), radius=45,
    fill=FillStyle(color=Color(131, 151, 218)),
)
scene.add(shape)

tutorial = Tutorial(scene, title="Inside a cell")
nucleus = tutorial.target(shape, name="nucleus")
label = nucleus.label("Nucleus", anchor="top", leader=True)

intro = tutorial.step("Meet the nucleus").show(label)
intro.highlight(nucleus)
intro.explain(nucleus, "The nucleus contains the cell's DNA.", max_width=220)
tutorial.step("Review the drawing")

tutorial.render_step(0).save("output/nucleus.png")
tutorial.render_step(1).save("output/plain.png")
# Batch export refuses existing files unless overwrite=True is explicit.
tutorial.export_steps("output/readme", overwrite=True)
```

Each step starts from the current source scene. The second step has no labels because it does not explicitly show any. Rendering order does not affect results. Tutorial and step titles are metadata; add DrawCV text if you want visible titles.

Run [the cell example](https://github.com/nuhyamin1/tutordraw/blob/master/examples/cell_tutorial.py) for a composed diagram. It writes `output/cell/step-001.png` through `step-003.png`. Rerunning explicitly overwrites these example images. [The nested-group example](https://github.com/nuhyamin1/tutordraw/blob/master/examples/group_focus.py) illustrates focusing a child while dimming its siblings.

## Continue a lesson with another AI

In the development checkout, use `tutorial.save_json("lesson.tutordraw.json")` and later `Tutorial.load_json("lesson.tutordraw.json")`. Named targets, annotation IDs, themes, and all step presentation settings survive the round trip.

Run `python examples/save_and_revise.py` for the complete workflow. See [AI authoring](https://github.com/nuhyamin1/tutordraw/blob/master/docs/AI_AUTHORING.md) and [persistence](https://github.com/nuhyamin1/tutordraw/blob/master/docs/PERSISTENCE.md).

## Export a timed lesson to video

In the development checkout, give each step a duration and encode the result:

```
lesson.steps[0].set_timing(duration=2, pause=1)
lesson.export_video("output/video/lesson.mp4", fps=30)
```

Run `python examples/video_lesson.py` for the complete workflow. It encodes the
10-second cell lesson at 12 fps, then decodes the file to report its frame count.
See [video export](https://github.com/nuhyamin1/tutordraw/blob/master/docs/VIDEO.md)
for codec limits and failure behavior.

## Current limits

- Labels are **single line**; callouts add newlines and measured word wrapping. Latin, Greek, Cyrillic, CJK and common symbols work out of the box. Thai and Arabic need the optional `typography` extra and a font you supply. Hebrew, Indic scripts and emoji are refused with an error naming the character; see [Text](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TEXT.md).
- Anchors use transformed axis-aligned `get_bounds()` results, including supported shape strokes but excluding post-processing effect extents.
- Labels stay upright and spacing uses canvas pixels. Panels are moved apart automatically when they collide, keeping the authored anchor and offset wherever it is free; `Theme(avoid_collisions=False)` restores verbatim placement. Routed leaders are deferred.
- Annotations that cannot be placed on canvas or clear of the others issue `LayoutWarning` and may be clipped or overlap. Callout widths measure the text area; padding adds to the panel width.
- Dimming multiplies artwork opacity, not the background. Complex masks, blend modes, and occlusion are not pixel-level spotlight isolation. Hidden or zero-opacity attention targets are rejected; clipping and masks are not used to infer visibility.
- Scenes must round-trip through DrawCV serialization; unsupported copying raises `SceneCopyError`. Arbitrary custom drawables/assets are not guaranteed supported.
- Rendering uses authored scene state without sampling a timeline. Concurrent source edits during rendering are unsupported.
- Video export is opaque only and uses hard cuts. Which codecs work depends on the host OpenCV build; an unavailable codec raises `VideoExportError`. Encoding is lossy, so decoded frames approximate `render_step` output.
- Missing registered targets fail rendering, even if their label is not shown in that step. Hidden artwork does not suppress an explicitly shown label.

## Documentation and continuation

- [Practical tutorial](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TUTORIAL.md): build a lesson from a DrawCV scene.
- [Per-step artwork](https://github.com/nuhyamin1/tutordraw/blob/master/docs/RESTYLE.md): move, recolour, fade and hide targets per step.
- [Animation](https://github.com/nuhyamin1/tutordraw/blob/master/docs/ANIMATION.md): easing a step into its state instead of cutting.
- [Reveal](https://github.com/nuhyamin1/tutordraw/blob/master/docs/REVEAL.md): delaying annotations so a beat unfolds as it is narrated.
- [Video export](https://github.com/nuhyamin1/tutordraw/blob/master/docs/VIDEO.md): encoding contract, codecs, and limits.
- [Text](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TEXT.md): which characters annotations accept, and why the rest are refused.
- [API guide](https://github.com/nuhyamin1/tutordraw/blob/master/docs/API.md): implemented methods and errors.
- [Compatibility](https://github.com/nuhyamin1/tutordraw/blob/master/docs/COMPATIBILITY.md): evidence, fonts, and alpha API expectations.
- [Release procedure](https://github.com/nuhyamin1/tutordraw/blob/master/docs/RELEASING.md): exact artifact checks and manual publishing.
- [Changelog](https://github.com/nuhyamin1/tutordraw/blob/master/CHANGELOG.md): milestone history.
- [Contributing](https://github.com/nuhyamin1/tutordraw/blob/master/CONTRIBUTING.md): local development and installed-package checks.
- [Product scope](https://github.com/nuhyamin1/tutordraw/blob/master/docs/PRODUCT.md): intended tutorial capabilities.
- [Architecture](https://github.com/nuhyamin1/tutordraw/blob/master/docs/ARCHITECTURE.md): foundation and future design.
- [Roadmap](https://github.com/nuhyamin1/tutordraw/blob/master/docs/ROADMAP.md): milestones and acceptance checks.
- [AI handoff](https://github.com/nuhyamin1/tutordraw/blob/master/docs/HANDOFF.md): current state, verification, and continuation prompt.
- [Decisions](https://github.com/nuhyamin1/tutordraw/blob/master/docs/DECISIONS.md): choices and remaining questions.
- [Agent instructions](https://github.com/nuhyamin1/tutordraw/blob/master/AGENTS.md): repository conventions.

To continue with another AI model, ask it to read `AGENTS.md` and `docs/HANDOFF.md` first. See the handoff for the latest release state. DrawCV remains a separate project.

## License

[MIT](https://github.com/nuhyamin1/tutordraw/blob/master/LICENSE), copyright 2026 Nuh Yamin.

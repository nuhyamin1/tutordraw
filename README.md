# TutorDraw

**Explain what you draw, one step at a time.**

TutorDraw is a Python library for authoring visual tutorials using [DrawCV](https://pypi.org/project/pydrawcv/). DrawCV supplies drawing objects and rendering; TutorDraw attaches teaching annotations and organizes them into independent lesson steps.

## Status

**Published alpha [0.1.0a3](https://pypi.org/project/tutordraw/0.1.0a3/).** TutorDraw provides the static tutorial workflow described below. Licensed under MIT, authored by Nuh Yamin. See the compatibility notes before relying on it in production.

**Development checkout: 0.1.0a5 (not yet published)** adds complete lesson save/load, AI revision support, and deterministic timed playback. Install from this repository to use those new methods. The PyPI command below still installs the published 0.1.0a3.

Implemented:

- Register existing DrawCV objects or groups as teaching targets.
- Attach labels with optional straight leader lines.
- Configure bounds anchors, gap, offset, padding, and font scale.
- Keep labels attached when targets move, including through group transforms.
- Define independent steps and render them to DrawCV canvases and PNG images.
- Preserve source content and undo history, including on rendering failure.
- Add step-local wrapped callouts, rectangular highlights, and group-aware dimming.
- Customize shared typography, spacing, and colors through an immutable theme.
- Export ordered PNGs with collision checks and partial-failure reporting.
- Validate references/options and warn about off-canvas annotations.
- Development only: save/reopen complete versioned JSON lessons with stable IDs and validated references.

- Development only: step durations, trailing pauses, direct time seeking, and streaming frames; see [Timing](docs/TIMING.md).

Video encoding, interactive playback, rich typography, and automatic collision avoidance remain planned.

## Install the alpha

```shell
python -m pip install tutordraw==0.1.0a3
```

The exact version selects this prerelease explicitly. Requires Python 3.12+.

## Develop from this repository

Requires **Python 3.12+**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cell_tutorial.py
```

On macOS/Linux, use `.venv/bin/python` instead. Windows/Python 3.12 passes 145 tests. CI is configured for Windows, Linux, and macOS on Python 3.12–3.14; hosted results are pending. If `python` is unavailable, use the absolute path to an installed Python 3.12+ executable for the first command.

No DrawCV checkout is needed. TutorDraw pins the tested published dependency `pydrawcv==0.10.0.post1`, which imports as `drawcv`. A broader compatibility range is future work. Use an explicit version or `--pre` when selecting an alpha release.

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

## Current limits

- Labels support **single-line printable ASCII**; callouts additionally support newlines and measured word wrapping. Other scripts and rich typography are not implemented yet.
- Anchors use transformed axis-aligned `get_bounds()` results, including supported shape strokes but excluding post-processing effect extents.
- Labels stay upright and spacing uses canvas pixels. Automatic collision avoidance and routed leaders are deferred.
- Off-canvas annotations issue `LayoutWarning` and may be clipped. Callout widths measure the text area; padding adds to the panel width.
- Dimming multiplies artwork opacity, not the background. Complex masks, blend modes, and occlusion are not pixel-level spotlight isolation. Hidden or zero-opacity attention targets are rejected; clipping and masks are not used to infer visibility.
- Scenes must round-trip through DrawCV serialization; unsupported copying raises `SceneCopyError`. Arbitrary custom drawables/assets are not guaranteed supported.
- Rendering uses authored scene state without sampling a timeline. Concurrent source edits during rendering are unsupported.
- Missing registered targets fail rendering, even if their label is not shown in that step. Hidden artwork does not suppress an explicitly shown label.

## Documentation and continuation

- [Practical tutorial](https://github.com/nuhyamin1/tutordraw/blob/master/docs/TUTORIAL.md): build a lesson from a DrawCV scene.
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

To continue with another AI model, ask it to read `AGENTS.md` and `docs/HANDOFF.md` first. Hosted CI verification remains pending; see the handoff for the latest release state. DrawCV remains a separate project.

## License

[MIT](https://github.com/nuhyamin1/tutordraw/blob/master/LICENSE), copyright 2026 Nuh Yamin.

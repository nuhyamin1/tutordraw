# TutorDraw

**Explain what you draw, one step at a time.**

TutorDraw is a Python library for authoring visual tutorials using [DrawCV](https://pypi.org/project/pydrawcv/). DrawCV supplies drawing objects and rendering; TutorDraw attaches teaching annotations and organizes them into independent lesson steps.

## Status

**M2 implemented — local development alpha `0.1.0a2`.** This repository is installable, but TutorDraw has not been published to PyPI. The distribution name `tutordraw` remains provisional and has not been reserved.

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

Video, interactive playback, rich typography, and automatic collision avoidance remain planned.

## Install from this repository

Requires **Python 3.12+**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cell_tutorial.py
```

On macOS/Linux, use `.venv/bin/python` instead. Windows/Python 3.12 has been tested; other platforms have not. If `python` is unavailable, use the absolute path to an installed Python 3.12+ executable for the first command.

No DrawCV checkout is needed. TutorDraw pins the tested published dependency `pydrawcv==0.10.0.post1`, which imports as `drawcv`. A broader compatibility range is future work. Do not run `pip install tutordraw` expecting this unpublished project.

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

Run [the cell example](examples/cell_tutorial.py) for a composed diagram. It writes `output/cell/step-001.png` through `step-003.png`. Rerunning explicitly overwrites these example images. [The nested-group example](examples/group_focus.py) illustrates focusing a child while dimming its siblings.

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

- [API guide](docs/API.md): implemented methods and errors.
- [Product scope](docs/PRODUCT.md): intended tutorial capabilities.
- [Architecture](docs/ARCHITECTURE.md): foundation and future design.
- [Roadmap](docs/ROADMAP.md): milestones and acceptance checks.
- [AI handoff](docs/HANDOFF.md): current state, verification, and continuation prompt.
- [Decisions](docs/DECISIONS.md): choices and remaining questions.
- [Agent instructions](AGENTS.md): repository conventions.

To continue with another AI model, ask it to read `AGENTS.md` and `docs/HANDOFF.md` first. The next milestone is release preparation: compatibility, documentation, CI, and final package metadata. DrawCV remains a separate project.

# Implemented API — 0.1.0a12 (development)

Public symbols import from `tutordraw`. Create targets/annotations/steps through the factory methods below rather than calling their constructors directly.

## Tutorial

`Tutorial(scene, *, title="", theme=None, font=None)` holds a DrawCV Scene reference and a Theme (defaults to `Theme()`). `font` accepts a path, bytes or a DrawCV `FontAsset` and enables Thai and Arabic; see [TEXT.md](TEXT.md). `tutorial.font` exposes it. The scene is read at each render. Titles are metadata, not automatically drawn text.

`tutorial.target(drawable, *, name=None) -> Target` registers an existing object/group, including nested children. Re-registration returns the same target. Explicit names must be nonempty and unique; conflicting names raise `ValidationError`.

`tutorial.step(title) -> Step` appends an independent step. Nonempty titles are required; duplicate titles are allowed. `tutorial.steps` returns a tuple.

`tutorial.render_step(index, *, alpha=False) -> drawcv.Canvas` renders a zero-based step through a copied scene. Negative indices and booleans are rejected. Use `alpha=True` for BGRA output; source background transparency is respected. `canvas.save(path)` uses DrawCV's save behavior and can overwrite existing files.

## Labels

```python
label = target.label(
    "Nucleus", anchor="right", leader=True, box=True,
    gap=None, offset=(0, 0), font_scale=None, padding=None,
)
step.show(label)
```

Labels are immutable reusable definitions, absent until explicitly shown. Target fields `id`, `drawable_id`, and `name` are immutable.

| Option | Behavior |
| --- | --- |
| `text` | Nonempty, single line; Latin/Greek/Cyrillic/CJK and common symbols ([TEXT.md](TEXT.md)) |
| `anchor` | `left`, `right`, `top`, `bottom`, or `center` of world-space bounds |
| `leader` | Boolean, enables a straight leader |
| `box` | Boolean, default `True`. `False` draws bare text with no panel behind it |
| `gap` | Nonnegative pixel distance from anchor to panel edge; theme default 32 |
| `offset` | Additional `(x, y)` pixels, either sign |
| `font_scale` | Hershey scale, >0 and <=10; theme default 0.7 |
| `padding` | Nonnegative pixels around text; theme default 10 |

`box=False` omits only the panel rectangle. The text, the leader and the panel's
measured area are unchanged, so an unboxed label sits exactly where a boxed one
would and collision avoidance still keeps it clear of everything else — which
bare text needs more than a panelled label does, not less. Without a panel the
text draws straight onto whatever is behind it, so `padding` then only affects
spacing, and `Theme.panel_color`, `border_color` and `border_width` are unused
for that annotation.

`None` uses the theme default at authoring time. Center-anchored labels are placed to the right of the target center. Text remains upright. Leaders terminate on panel edges; if the target lies within the panel, its leader is omitted. Spacing uses canvas pixels and does not inherit object scaling.

`step.show(*labels, at=None) -> Step` accepts registered labels from the same tutorial, ignores duplicates, and leaves the step unchanged if any argument is invalid. `step.labels` is a tuple. Steps never inherit presentation state from each other.

## Callouts

```python
callout = step.explain(
    target, "The nucleus contains DNA.\nThis information guides cell activity.",
    anchor="right", max_width=260, gap=40,
)
```

`step.explain` accepts all label layout options, including `box`, plus `max_width=None` and `line_spacing=None`. It returns a `Callout` and automatically shows it only in this step. Callouts cannot be passed to `show` in another step; call `explain` there instead. `step.callouts` returns a tuple.

`max_width` limits the **text area**, excluding panel padding. Default: theme `callout_width=260`. Words wrap using DrawCV measurements. Oversized words split at characters; a width too narrow for one character raises `ValidationError` when rendered. Explicit newlines preserve paragraph breaks, including blank lines; other spaces normalize. Callout text may use any character labels accept, plus newlines. Line spacing is at least 1, default 1.35 times measured line height.

## Highlights and dimming

```python
step.highlight(target, padding=8, color=(226, 146, 33), width=3)
step.dim_others(target, another_target, opacity=0.25)
```

`highlight(target, *, padding=None, color=None, width=None) -> Step` creates a rectangular outline around transformed axis-aligned bounds. None uses theme defaults. Width must be positive; padding nonnegative; color is an RGB tuple. Repeating this call for the same target replaces its settings. `step.highlights` exposes a tuple of definitions.

`dim_others(*targets, opacity=None) -> Step` preserves one or more targets and multiplies unrelated artwork opacity by a factor in [0,1]. The theme default is 0.25. Repeating it replaces the focus set. A selected group preserves its subtree; a selected child preserves its ancestors while unrelated branches dim exactly once. Existing ancestor opacity still applies. Annotations are never dimmed.

Highlight/focus requests for targets under hidden or zero-opacity objects/layers fail at render time. Empty/all-hidden groups are rejected. Masks, clipping, blend modes, and occlusion are not visibility tests. Dimming is opacity reduction, not pixel-level spotlight isolation. Background color is unchanged. Titles drawn into the source are artwork too; register and focus them if they should stay undimmed.

## Changing artwork per step (new in 0.1.0a8)

```python
step.restyle(moon, move=(0, 190), fill=(168, 68, 52))
step.restyle(sun, opacity=0.35)
step.restyle(shadow, visible=False)
```

`restyle(target, *, move=None, fill=None, opacity=None, visible=None) -> Step`
changes a target's artwork for that step only, on the working copy, leaving the
source drawing untouched. `move` is a `(dx, dy)` shift relative to the source
placement; attached labels, leaders and highlights follow it. `fill` sets a
shape's fill or a Text object's colour and is refused for Line and Group.
`opacity` is absolute, and `dim_others` still multiplies on top of it.
`visible=False` hides the target, after which emphasising it raises.

At least one option is required, and repeating the call for a target replaces
its settings entirely. `step.restyles` exposes the definitions. Restyles persist
in lesson schema v3. See [RESTYLE.md](RESTYLE.md).

## Revealing annotations one at a time (new in 0.1.0a11)

`show(*labels, at=None)` and `explain(target, text, ..., at=None)` take an
optional delay in seconds from the start of the step, so a narrated beat can
introduce one thing at a time. `at=None` means immediately, as before.
`step.revealed_at(annotation)` and `step.reveals` report the timings.

A step with no delays is unchanged and stays a hard cut. `render_step` always
shows every annotation, so PNG export is unaffected; only `render_at_time` and
what builds on it honour delays. A delay past the step's duration reveals at
its end. Saved in lesson schema v5. See [REVEAL.md](REVEAL.md).

## Animating a step (new in 0.1.0a10)

`step.animate(easing="ease_in_out") -> Step` eases into the step's restyled
state over its duration, instead of cutting to it. `step.hard_cut()` undoes it
and `step.easing` reports the curve. Easing names and their validation come
from DrawCV; they match case-insensitively and store lowercase.

Animation runs from the **previous step's** state, so a target the next step
leaves alone slides back to the source. `move`, `opacity` and `fill`
interpolate; `visible` does not. Hard cuts remain the default, and
`render_step` always shows the finished state. Saved in lesson schema v4.
See [ANIMATION.md](ANIMATION.md).

## Automatic collision avoidance (new in 0.1.0a12)

Label and callout panels no longer overlap each other. Before drawing a step,
TutorDraw resolves every annotation's panel against the other panels, the
highlight boxes, the registered targets' artwork, and the canvas edges.

**It is on by default.** Turn it off with `Theme(avoid_collisions=False)`, which
restores the earlier behaviour exactly: the authored anchor, gap and offset are
used verbatim, whatever they collide with.

| Option | Behavior |
| --- | --- |
| `avoid_collisions` | Boolean, default `True`. Off restores verbatim authored placement. |
| `collision_margin` | Nonnegative pixels kept clear between panels; default 6. |

Author intent stays primary. A panel is only moved when it genuinely collides:

- The authored `anchor`, `gap` and `offset` are tried first and kept whenever
  they are free, so a lesson that never overlapped renders exactly as before.
- A panel that must move tries the other sides of its target first, then slides
  along a side, then steps further out. Several labels on one small target fan
  around it rather than stacking.
- Annotations are resolved in registration order — `step.labels` then
  `step.callouts` — so an earlier one is never displaced by a later one and the
  same lesson always renders identically.
- A panel is kept off other **registered** targets' artwork where it can be.
  Unregistered artwork is not considered. A `center`-anchored label is allowed
  to sit on its own target, because that is what `center` asks for.
- A panel is shifted back onto the canvas when it fits. One wider or taller than
  the canvas cannot be, and still raises `LayoutWarning`.

Placement is **per render**, never stored on the `Label` or `Callout`, so the
same reusable label can be placed differently in different steps.

### Across frames

A step is resolved **once per render, from the state the step ends in**, and
that one decision is used for every frame of it. Panels are still built from
live bounds each frame, so a moved target keeps its label, leader and highlight,
and `restyle(move=...)` stays pixel-identical to moving the source object.

Two consequences worth knowing:

- An animated step is resolved against both of its ends, and a panel is judged
  over the whole path it sweeps between them. A label dragged past another one
  therefore clears it in the middle too, not only at the end.
- Reveal delays are ignored when resolving. Every annotation holds its slot from
  the first frame, so nothing already on screen moves when a delayed one
  appears; the slot simply stays empty until it does.

When even the best candidate still overlaps, rendering proceeds and issues a
`LayoutWarning` naming the label, rather than failing or silently overlapping.

## Theme

`Theme(...)` is an immutable set of validated defaults:

| Field | Default |
| --- | --- |
| `text_color` | `(28, 43, 65)` |
| `panel_color` | `(255, 255, 255)` |
| `border_color` | `(194, 207, 223)` |
| `leader_color` | `(75, 104, 140)` |
| `highlight_color` | `(226, 146, 33)` |
| `font_scale`, `padding`, `gap` | `0.7`, `10`, `32` |
| `leader_width`, `border_width`, `highlight_width` | `2`, `1`, `3` |
| `highlight_padding` | `8` |
| `callout_width`, `line_spacing` | `260`, `1.35` |
| `dim_opacity` | `0.25` |
| `avoid_collisions`, `collision_margin` | `True`, `6` |

Colors are immutable RGB tuples, channels 0–255. Numeric annotation defaults and highlight settings resolve at creation time. Panel/text/leader colors and border/leader widths come from the tutorial's current theme at render time. Supply a theme when constructing the tutorial for consistent styling.

## Ordered PNG export

`tutorial.export_steps(directory, *, overwrite=False, alpha=False) -> list[Path]` writes `step-001.png`, `step-002.png`, etc. Returned paths follow step order. Empty tutorials raise `ValidationError`. Titles never become filesystem paths.

Every filename is checked before export; collisions raise `FileExistsError` unless overwrite is explicit. Symlinks and non-file destinations are rejected even with overwrite. Concurrent file creation after preflight also cannot overwrite a file when overwrite is false.

Frames encode in temporary files. Explicit overwrite replaces an existing file only after successful encoding; a failed newly-created file is removed. This is not a transaction across the batch: successful earlier files remain if a later step fails. A new file may be visible during its copy. Permission/directory failures during preflight can propagate as filesystem exceptions.

## Marks, drawing on, camera and outlines (new in 0.1.0a12, schema v8)

`step.connect`, `brace`, `measure`, `angle` and `number` add drawn marks and
return a `Mark`. `draw=True` on labels, callouts, highlights and marks draws
their strokes on. `step.zoom_to(*targets)` frames the artwork for a step and
`reset_camera()` clears it. `highlight(shape="outline")` follows the target's
own outline. `box=False` text gets a halo (`Theme.halo_width`). The full
reference is [VOCABULARY.md](VOCABULARY.md).

`Composition.marks` lists each finished mark as a `MarkLayout` (`kind`, `text`,
`targets`, `bounds`, `panel`); `Composition.camera` is `(scale, tx, ty)` or None.

## Teaching kits (new in 0.1.0a12)

`tutordraw.kits.Axes(tutorial, box=..., x_range=..., y_range=...)` draws
labelled axes from DrawCV objects; `plot(f)`, `point(x, y)`, `guide(x=, y=)`
return named targets and `to_scene(x, y)` maps coordinates.
`tutordraw.kits.NumberLine(tutorial, start=..., length=..., value_range=...)`
adds `point`, `interval`, and `hop(step, a, b, text)`, a step mark.
`Flowchart` (`node(name, text, at=(col, row), shape=)`, `link(a, b, text)`),
`Timeline` (`event(when, text)`, `period(start, end, text)`), `Cycle`
(`stages=[...]`, `stage(key)`, `arrows`), `ForceDiagram` (`force(name,
direction, magnitude, text)`, `components`, `net`) and `CrossSection`
(`layers=[(name, text, thickness)]`, `shape="bands"` or `"rings"`, `labels()`)
build the other common teaching diagrams. Every kit has `find(tutorial, name)`
to reattach after loading. See [KITS.md](KITS.md).

## Narration timing (new in 0.1.0a12)

`step.narrate(words, cues=None, *, lead=0.15, tail=0.5, fit=True, rate=None)`
reveals each cued label, callout, mark or highlighted target as its phrase is
spoken, from TTS word timings, and fits the step to the narration.
`step.narration` holds the parsed words; `web_step` carries them for captions.
See [NARRATION.md](NARRATION.md).

## Interactive prompts (new in 0.1.0a12)

`step.ask(text, answer, *, correct=None, wrong=None, hint=None, attempts=3)`
ends a step with a question answered by tapping the picture; the browser
player waits for the answer. `tutorial.check_answer(index, x, y)` returns an
`Answer` (`correct`, `tapped`, `feedback`) and `tutorial.hit_test(index, x, y)`
the targets under a point, innermost first. Lesson schema v9 saves prompts
and narration words. See [PROMPTS.md](PROMPTS.md).

## Describing steps (new in 0.1.0a12)

`tutorial.describe(index=None)` returns a plain-English description of one
step, or of the whole lesson, built from its structure in the order things
appear. `web_step` payloads include it as `description`. See
[DESCRIBE.md](DESCRIBE.md).

## Browser playback (new in 0.1.0a12)

`tutorial.to_svg(index, *, time=None)` returns one frame as SVG with native
text. `tutorial.web_step(index)` returns one step's player payload, and
`tutorial.export_web(path, *, overwrite=False)` writes a self-contained HTML
player. Stream a lesson by sending each `web_step` as it is authored to a page
running `TutorDrawPlayer`. See [WEB.md](WEB.md).

## Layout and lint (new in 0.1.0a12)

`tutorial.layout(index, *, time=None) -> Composition` reports where everything
in a step lands without rasterizing it: `annotations` (`AnnotationLayout` with
`kind`, `text`, `target`, `anchor`, `panel`, `leader`, `boxed`), `highlights`
(`HighlightLayout` with `target`, `box`, `width`), `targets` (name -> bounds)
and `to_dict()`. `time` is seconds into the step; None is its finished state.

`tutorial.lint(index=None) -> list[Issue]` reports readability problems with a
stable `code` and a suggested `fix`, errors first. The codes are listed in
[AI_AUTHORING.md](AI_AUTHORING.md#lint-fix-layout-without-looking-at-pixels).
Neither method changes the lesson or what renders.

## Errors and warnings

- `TutorDrawError`: base exception.
- `ValidationError`: invalid options/references/indices, hidden attention targets, layout that cannot fit a character, or an unsupported character ([TEXT.md](TEXT.md)). Also a ValueError.
- `SceneCopyError`: failure copying through DrawCV's document API, with chained cause.
- `VideoExportError`: a video export failed; the destination was not created or
  replaced. Inspect `path`, `fourcc`, `frames_written`, and `__cause__`.
- `ExportError`: failure after export starts. Inspect zero-based `step_index`, `path`, `completed_paths` (tuple), and `__cause__`.
- `LayoutWarning`: an annotation extends outside the canvas, or could not be placed clear of the others. Rendering proceeds and may clip or overlap it.

Direct render/save errors from DrawCV propagate; batch export wraps per-step failures in ExportError. Rendering preserves source content and history even on failure. Routed leader lines, rich fonts, timeline sampling, and concurrent source editing are not supported.


## Lesson persistence and revision (new in 0.1.0a4)

Both `avoid_collisions` and a label's `box` are saved in lesson schema v7;
lessons written by an older alpha load with their defaults, both `True`.

`Tutorial.to_dict`, `from_dict`, `to_json`, `from_json`, `save_json(path, overwrite=False)`,
and `load_json(path)` preserve the complete scene and lesson model. The three loaders also take `font=` for lessons using Thai or Arabic. `save_json`
returns Path and refuses collisions by default. `LessonFormatError` reports invalid
content or unsupported schema versions; filesystem errors propagate normally.

`tutorial.targets` and `tutorial.labels` expose tuples of definitions.
`tutorial.get_target(name)` resolves a named target. `target.drawable` returns its
current source object or raises ValidationError if missing. `step.id` is stable
across save/load. See [PERSISTENCE.md](PERSISTENCE.md) for file format and editing
contracts, and [AI_AUTHORING.md](AI_AUTHORING.md) for a practical model-to-model workflow.

## Timing (development 0.1.0a5)

`step(title, *, duration=3.0, pause=0.0)` accepts seconds.
`Step.set_timing(duration=..., pause=0.0)` replaces both values and returns the step.
`Step.duration` and `Step.pause` are read-only; `Tutorial.duration` includes all pauses.
`step_at_time(time)` returns a zero-based index; `render_at_time(time, alpha=False)`
returns a Canvas; `render_frames(fps=30, alpha=False)` returns an iterator of canvases.
See [TIMING.md](TIMING.md) for boundary semantics, validation, and limits.

## Video export (development 0.1.0a6)

`tutorial.export_video(path, *, fps=30, fourcc="mp4v", overwrite=False) -> Path`
encodes `ceil(duration * fps)` frames into one video file. The file extension
selects the container. Output is always opaque three-channel BGR; there is no
`alpha` option, because these codecs carry no alpha channel.

Invalid `fps`, `fourcc`, `overwrite`, and empty lessons raise `ValidationError`
before any file or encoder is opened. Existing destinations raise
`FileExistsError` unless `overwrite=True`; symlinks are refused either way.
Codec, rendering, and write failures raise `VideoExportError` and leave an
existing destination untouched. Which codecs are available depends on the host
OpenCV build. See [VIDEO.md](VIDEO.md) for the full contract and local evidence.

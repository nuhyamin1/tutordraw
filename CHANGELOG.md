# Changelog

## Unreleased

- **Leaders end on the shape.** A label's or callout's leader was drawn to a
  point of its target's bounding box (its top, its right, ...), which lies on
  a rectangle or a circle but can be in empty space beside a triangle, a
  slanted line or any irregular outline: a callout on a right triangle ended
  in the air above the hypotenuse. It now ends at the point of the target's
  own outline nearest that bounds point (`layout.ink_point`). The panel is
  placed as before. Unchanged where the bounds point is already on the shape
  (within 6 px of its ink), for text and pieces of an equation (a leader goes
  to text as a block) and for groups.

- **Scale several targets together.** A `restyle` pivot can also be a point
  `(x, y)`, in the coordinates of the target's parent; targets given the same
  point and scale shrink or grow as one picture, for an inset.
- **Lint `CHART_OVER_ARTWORK`** (warning): a graph or number line drawn over a
  quarter or more of another shape, which it hides and which garbles its
  grid. A panel the chart sits on (three quarters of the chart on it) is not
  reported, nor anything drawn as part of the chart.

- **Scaling one target.** `restyle(..., scale=0.8, pivot="top_left")` makes a
  target's artwork smaller or larger about one of nine points of its bounds,
  which stays put; everything inside it scales too, its own text included
  (a graph's tick numbers), while labels, callouts and marks on its parts
  follow and keep their size. It glides like a move in an animated step, in
  a straight line, so the player's one start frame is exact. Use it to make
  room on a full board, to zoom into one part of a scene while the rest stays,
  or to grow something as it is introduced. New lint warning
  `SCALED_TEXT_SMALL` when the drawing's own text ends under 12 px. **Lesson
  schema v12** saves `scale` and `pivot` on restyles and `obstacle` on
  targets; v1 to v11 still load.
- **Targets that are not obstacles.** `tutorial.target(group, obstacle=False)`
  registers a group (to restyle it) without making its whole box keep labels
  off: the targets inside it still do. Registering a graph used to push its
  own points' labels off it.
- **Labels no longer jump during a move of a graph.** The drawing's own words
  (tick numbers), which labels try not to cover, were measured where the
  frame had them rather than where the step ends, so a label on a graph
  that was moving or shrinking could switch sides for a frame or two.

- **Quick motion in a longer step.** `animate(easing, seconds=)` finishes the
  step's motion that long after it starts and holds still for the rest, so
  a tutor can slide its working up and fade old lines in a moment, then
  write. The player reads `motion` from the step payload. **Lesson schema
  v11** saves it per step; v1 to v10 still load.
- **Moving along a path.** `restyle(..., via=[(dx, dy), ...])` makes an
  animated move run through those offsets, at an even speed along the
  polyline, instead of in a straight line; `Axes.along(f, a, b)` samples a
  curve into them, so a point slides along y = f(x). The player gets such a
  step as 12 keyframes; label placement judges points along the way. **Lesson
  schema v10** saves `via` on each restyle; v1 to v9 still load.
- **Axes' numbers no longer collide at the origin.** With a range starting
  just below 0 on a small graph, the "−0.5" (or "−1", "−0.2") tick numbers
  sat on the "0" written below-left of the origin, and the x and y "−0.5"
  met at the corner. A tick number that would touch one already written
  (the origin's first) is now left out; its tick mark is still drawn.
- **Labels stay put between steps.** A label shown in consecutive steps keeps
  its previous place while nothing new lands on it, instead of being placed
  afresh each step: in Illustrate a point's label leapt 222 px across the
  canvas in the step that slid a marker past it. And in an animated step a
  stroke that does not move now blocks labels along its ink, as in a still
  step, rather than with its whole bounding box, which was what pushed the
  label away. Placements of earlier steps are remembered per lesson.
- **Lint for the drawing's own words.** `TEXT_OVERLAP` (error): two of the
  scene's texts or equations lie on each other; `TEXT_ON_DIAGRAM` (warning):
  one lies on a kit's lines, text or shading; `TEXT_OFF_CANVAS` (warning).
  Text inside a kit is the kit's own layout and is not reported. The scan is
  public in `tutordraw.arrange` (`words`, `diagrams`, `collisions`), with
  `occupied` giving the boxes `clear` needs to move a word off everything.
  `clear` now tests its candidates with numpy, so a graph's hundreds of ink
  boxes are fast.
- **Placing blocks by relation: `tutordraw.arrange`.** `place(size, reference,
  side, gap=, canvas=)` puts a block of a measured size to the right, left,
  below or above another's real bounds ("beside" picks the side with room),
  lined up on the top or left edge so a chain of blocks forms a column, and
  slides it along that side to stay on the canvas. `clear(box, obstacles,
  canvas=)` finds the nearest spot for a block that covers something, and
  `shift_to(drawable, x, y)` moves a drawable's measured bounds there. For
  callers (and models) that place text and equations: they no longer have to
  guess sizes TutorDraw knows exactly.
- **Graphs you can draw into.** `Axes` gains constructions computed from the
  curve's own function, so they meet it exactly: `region(f, g=0)` shades the
  area under a curve, between two curves, or above or below one;
  `rectangles(f, domain, count, rule=)` draws a Riemann sum; `tangent(f, x)`
  and `secant(f, x1, x2)` draw lines through the curve; `intersections(f, g=0)`
  finds where curves meet (roots with g = 0), touching points included. For
  shapes of your own in the graph's units, `clip(points, closed=)` cuts them
  exactly at the plot area and `add(drawable)` makes them part of the graph;
  `to_scene_offset` and `contains` convert sizes and test points. Regions and
  rectangles sit beneath the grid and curves. Nothing new in the lesson
  schema: they are ordinary DrawCV paths and lines in the axes' group.

## 0.2.0a1 — third alpha (published 2026-09-24)

A new minor version because the change from 0.1.0a11 is large: this is the
development milestone previously called 0.1.0a12, never uploaded under that
number. It needs `pydrawcv==0.11.0`; lesson files it saves (schema v9) do not
open in 0.1.0a11. Lessons from 0.1.0a11 and earlier still open.


- **Equations: `tutordraw.kits.Equation`.** LaTeX typeset into filled DrawCV
  paths by ziamath, in named pieces on one baseline, each a target that can
  be highlighted, recoloured, connected to or narrated. New optional extra
  `math` (`ziamath>=0.13,<0.14`); without it `Equation` raises with the
  install command. New example: `examples/pythagoras_lesson.py`.
- **Lesson schema v9.** Steps save their narration word timings and their
  prompt, so captions and questions survive a save. v1 to v8 still load
  (without narration words or prompts); builds that only know v8 cannot open
  v9. Packaged as `lesson-v9.schema.json`.
- **Interactive prompts.** `step.ask(text, answer)` ends a step with a
  question answered by tapping the picture. The browser player holds the step
  until an answer is tapped, names wrong taps, rings the answer after three
  misses or "Show me", and reports each tap to `player.onanswer`.
  `Tutorial.check_answer(index, x, y)` and `Tutorial.hit_test(index, x, y)` do
  the same judging in Python. `describe()` and `lint()` cover prompts
  (`PROMPT_HIDDEN`, `PROMPT_UNTAPPABLE`, `PROMPT_GIVEAWAY`). New example:
  `examples/quiz_lesson.py`. See docs/PROMPTS.md.
- **Five more teaching kits.** `Flowchart` (nodes by grid cell in four shapes,
  links that route with square corners and loops), `Timeline` (events that
  alternate and climb clear of each other, periods as bands), `Cycle` (stages
  round a circle joined by curved arrows), `ForceDiagram` (arrows to scale
  from the body's edge, components, the net force) and `CrossSection` (bands
  or rings with one column of labels). Each builds plain DrawCV objects with
  named targets and has `find` to reattach after loading. `tutordraw.kits` is
  now a package; imports are unchanged. New examples: `flowchart_lesson.py`,
  `timeline_lesson.py`, `water_cycle_lesson.py`, `forces_lesson.py`,
  `earth_layers_lesson.py`.
- **Teaching kit: `tutordraw.kits.NumberLine`**, with points (open or closed),
  intervals for inequalities, invisible anchors at values, and
  `hop(step, a, b, text)`: a curved hop arrow created as a step mark, so it
  draws on, takes `at=` and can be a narration cue. New example:
  `examples/number_line_lesson.py`.
- **Teaching kits: `tutordraw.kits.Axes`.** Axes with round tick steps, an
  optional grid, `plot(f)` (breaks at asymptotes and failures, clipped exactly
  at the range edges), `point`, `guide` and `to_scene`, all built from ordinary
  DrawCV objects as named targets; `Axes.find` reattaches after loading.
- **Label placement near strokes and text.** Unfilled strokes (curves, lines,
  outlines) now block labels only along their ink, and text in the drawing
  (titles, tick numbers) is avoided. Existing lessons' placements are unchanged.
- `describe()` no longer mentions things hidden from the first step, and uses
  "are" for plural target names ("the guides appear").
- New example: `examples/graph_lesson.py`.
- **`Step.narrate(words, cues)`**: reveal labels, callouts, marks and highlights
  as the narration speaks their phrases, from TTS word timings (tuples, dicts,
  per-character timings via `narration.words_from_characters`, or a plain
  string timed at an even pace), and fit the step to the narration. The player
  shows live captions.
- An arrow between two targets that share a centre now draws nothing instead
  of failing the whole frame, and lint reports it as `EMPTY_MARK`.
- `examples/lever_lesson.py` is now narrated with cues instead of `at=`.
- **`Tutorial.describe(index=None)`**: plain-English step descriptions from the
  lesson's structure, in the order things appear, with artwork changes told
  relative to the previous step. Included in `web_step` payloads; the player
  labels the picture with it and announces it in a live region.
- The exported page escapes `<`, `>` and `&` in its inline data, not just
  `</`, so lesson text such as `<!--<script` cannot change how the page parses.
- **Browser playback and streaming.** `Tutorial.to_svg(index, time=None)`
  returns a frame as SVG with native, selectable text; `Tutorial.web_step(i)`
  returns a step's player payload; `Tutorial.export_web(path)` writes a
  self-contained HTML player. The packaged `player.js` (`TutorDrawPlayer`)
  plays reveals, draw-on, animated restyles and camera moves, and accepts
  steps while it plays, waiting for the next one. See docs/WEB.md.
- Everything TutorDraw draws now has a stable drawable ID (`td-<owner>-<role>`),
  so the same annotation matches itself across frames and steps.
- New example: `examples/web_lesson.py`.
- **Marks** (lesson schema v8): `step.connect` (arrows between targets or from
  a point, curved with `bend`), `step.brace`, `step.measure` (dimension lines),
  `step.angle` and `step.number` (numbered badges). See docs/VOCABULARY.md.
- **Drawing on**: `draw=True` on `show`, `explain`, `highlight` and marks draws
  strokes over `Theme.draw_seconds`; text arrives when its stroke completes.
  `render_step` always shows the finished state.
- **Camera**: `step.zoom_to(*targets)` / `reset_camera()`. Artwork zooms, text
  does not; animated steps move from the previous step's framing.
- **Outline highlights**: `highlight(shape="outline")` follows the target's
  own shape, grown by `padding`. Highlights also take `at=` and `draw=`.
- **Halo**: `box=False` text is outlined in `panel_color` by
  `Theme.halo_width` (3; 0 disables). This changes how bare labels render.
- `lint()` covers marks (off-canvas, caption overlaps, busy steps), counts a
  halo as separating text from artwork, and ignores sub-pixel float noise.
- Lesson schema v8; v1-v7 still load. Lessons saved by this release cannot be
  opened with 0.1.0a11 or earlier.
- New example: `examples/lever_lesson.py`.
- **`Tutorial.lint()`** reports readability problems — overlapping or
  off-canvas panels, panels hiding a target's actual shape, leaders crossing
  each other, panels or other targets, low contrast (including bare text over
  artwork), small text, long callouts and busy steps — as `Issue` objects with
  a stable `code`, the targets involved and a suggested fix. Built for an LLM's
  author -> lint -> fix loop.
- **`Tutorial.layout(index, time=None)`** returns a `Composition`: every
  visible annotation's panel, leader and chosen side, each highlight's box and
  each target's live bounds, without rasterizing.
- New public types: `Composition`, `AnnotationLayout`, `HighlightLayout`, `Issue`.
- **Requires `pydrawcv==0.11.0`** (was `0.10.0.post1`). DrawCV now antialiases
  with area-exact coverage, so rendered images differ: strokes are drawn at their
  true width and annotations look thinner. Panel borders and highlight rectangles
  are now snapped so their strokes cover whole pixels and stay crisp.
- Lessons saved by this release embed DrawCV scene schema 1.14 and cannot be
  opened with 0.1.0a11 or earlier. Lessons saved by earlier releases still load.
- **Automatic collision avoidance for label and callout panels, on by default.**
  A step's annotations are resolved against each other, the highlight boxes, the
  registered targets' artwork and the canvas edges before anything is drawn.
- The authored `anchor`, `gap` and `offset` are tried first and kept whenever
  they are free, so a lesson whose panels never overlapped renders as before.
  A panel that must move tries the other sides of its target, then slides along
  one, then steps further out; several labels on one target fan around it.
- Annotations resolve in registration order, so an earlier one is never
  displaced by a later one and a lesson always renders identically.
- A panel is shifted back onto the canvas when it fits. One too big to fit, or
  one that could not be placed clear of the others, still raises `LayoutWarning`.
- **Stable across frames.** A step is resolved once per render from the state it
  ends in, and an animated step is judged over the path its panels sweep between
  its two ends, so nothing jitters, swaps sides, or collides mid-move. Panels
  are still built from live bounds each frame, so a moved target keeps its
  label, leader and highlight, and `restyle(move=...)` stays pixel-identical to
  moving the source object.
- Reveal delays do not affect resolution: an annotation holds its slot from the
  first frame, so nothing on screen moves when a delayed one appears.
- Placement is per render and never stored on the frozen `Label`/`Callout`, so a
  reusable label can be placed differently in different steps.
- Add `Theme(avoid_collisions=True, collision_margin=6)`; `avoid_collisions=False`
  restores verbatim authored placement.
- **`label(..., box=False)` and `explain(..., box=False)` draw bare text** with
  no panel behind it, for a caption on empty canvas or a value beside an axis.
  Previously every annotation was boxed and the theme could not fake otherwise:
  `panel_color` takes no alpha and `border_width` must be positive, so the only
  workaround was a background-coloured panel, which is opaque and punches a hole
  through any artwork behind it. The panel is still measured when it is not
  drawn, so an unboxed label sits where a boxed one would and collision
  avoidance still keeps it clear.
- Both settings are saved in lesson schema v7; v1 through v6 still load and take
  the defaults, `True` for each.
- Fix `restyle(fill=...)` on a gradient- or image-filled object, which raised
  `ValidationError: Gradient and image fills have no single color`. It fired on
  any fill change of such an object, animated or not. A gradient now blends from
  the unweighted mean of its stops; an image paint has no colour to blend from
  and cuts to the new fill.
- Add `src/tutordraw/collision.py` and 25 collision tests covering colliding
  panels, off-canvas recovery, crowding one small target, frame stability, and
  the animated sweep.

## 0.1.0a11 — second alpha (published 2026-09-21)

Everything from a4 through a10 ships here; those versions were development
milestones and were never uploaded. A large jump from a3: lesson persistence,
timed playback, video export, text beyond ASCII, per-step artwork changes,
animation, annotation reveals, and optional Thai and Arabic.

### This release

- `Step.show(*labels, at=None)` and `Step.explain(..., at=None)` accept a delay
  in seconds from the start of the step, so a narrated beat introduces one
  thing at a time instead of showing everything at once.
- Add `Step.revealed_at(annotation)` and `Step.reveals`.
- A delay alone makes a step time-varying; `animate()` is not required, and the
  two combine. A step with no delays is unchanged and stays a hard cut.
- `render_step` still shows every annotation, so PNG export is unaffected.
- A delay past the step's duration reveals at its end, so playback and
  `render_step` always agree.
- Save reveal times in lesson schema v5; v1 through v4 still load.
- Add `docs/REVEAL.md` and 20 reveal tests; the eclipse example now delays
  each explanation behind its labels.
- Tests derive the schema version from one table in `tests/conftest.py`, so a
  future bump updates one place and one test covers every older version.

## 0.1.0a10 — development milestone, shipped inside 0.1.0a11

- Add `Step.animate(easing="ease_in_out")` and `Step.hard_cut()`. An animated
  step eases into its restyled state over its duration instead of cutting to it,
  so a target slides and recolours rather than jumping.
- Animation runs from the previous step's state, so a step repeating a move
  stays put and a target the next step ignores slides back to the source.
- `move`, `opacity` and `fill` interpolate; `visible` does not.
- Easing curves and their validation come from DrawCV; names are stored
  lowercase. `render_at_time`, `render_frames` and `export_video` all follow.
- **Hard cuts remain the default.** Without `animate()` every frame still equals
  some `render_step` output, and `render_step` always shows the finished state.
- Save step easing in lesson schema v4; v1, v2 and v3 still load.
- Add `docs/ANIMATION.md` and 19 animation tests; the eclipse example now
  animates its last two beats.
- Animated frames cost the same as static ones, about 35 ms on the eclipse
  lesson; frames were always rendered from scratch.

## 0.1.0a9 — development milestone, shipped inside 0.1.0a11

- Support **Thai and Arabic** through DrawCV's font engine, behind a new
  optional extra: `pip install "tutordraw[typography]"`. A default install is
  unchanged and still needs only `pydrawcv`.
- Add `Tutorial(scene, font=...)` taking a path, bytes or a DrawCV `FontAsset`,
  and `font=` on `load_json`, `from_json` and `from_dict`. TutorDraw ships no
  font; supply one covering your scripts.
- Choose the renderer per annotation, so a lesson can hold a Thai callout and a
  Greek label. A configured font is used for everything it can draw. One
  annotation cannot mix the two sides and says so.
- Break Thai lines at word boundaries using the bundled segmenter, and align
  wrapped right-to-left lines to the panel's right edge.
- Lesson files are unchanged: the text declares the need, and loading Thai or
  Arabic without a font raises naming the first character that requires one.
- Add `docs/TEXT.md` guidance, `examples/multilingual_lesson.py`, and 11 font
  tests that skip when no covering font is installed.

## 0.1.0a8 — development milestone, shipped inside 0.1.0a11

- Add `Step.restyle(target, move=, fill=, opacity=, visible=)`, changing a
  target's artwork for one step on the working copy. The source drawing is never
  edited, so steps stay independent and render in any order.
- Attached labels, leaders and highlights follow a moved target: moving by
  `restyle` is pixel-identical to moving the source object by the same amount.
- `visible=False` covers progressive reveal of artwork. `opacity` is absolute and
  `dim_others` still multiplies on top of it. `fill` recolours shapes and text,
  and is refused for Line and Group.
- Persist restyles in lesson schema v3 and package its JSON Schema. v1 and v2
  still load without restyles; saving always writes v3.
- Add `docs/RESTYLE.md`, `examples/eclipse_lesson.py`, and 32 restyle tests.
- Lessons can now show change over time. Annotations within a step still appear
  at once, and motion is a jump at the cut rather than an animation.

## 0.1.0a7 — development milestone, shipped inside 0.1.0a11

- Accept annotation text beyond ASCII: Latin with accents, Greek, Cyrillic, CJK,
  and technical symbols such as `µm`, `°C`, `α`, `½`, `±`, `≤`, `×`, arrows,
  em dashes and curly quotes. No new dependency; the renderer always could.
- Validate each character twice: against an allow list of scripts that need no
  shaping, and against a cached probe of what the installed OpenCV really draws.
- Refuse Thai, Arabic, Hebrew, Indic scripts and emoji with a `ValidationError`
  naming the character and its codepoint, rather than rendering them wrongly.
  OpenCV substitutes `?` for Thai and draws Arabic unjoined and left to right.
- Normalize annotation text to NFC, so combining sequences behave as precomposed.
- Add `docs/TEXT.md`, `examples/symbols_lesson.py`, and 29 text tests.
- Record that hosted CI passes all nine jobs; earlier docs wrongly said pending.
- Make `tools/check_installed.py` fail when no video is produced, so a green CI
  matrix proves codec availability rather than hiding its absence.

## 0.1.0a6 — development milestone, shipped inside 0.1.0a11

- Add `Tutorial.export_video(path, fps=30, fourcc="mp4v", overwrite=False)`,
  encoding the streaming frame iterator into one video file.
- Add `VideoExportError` carrying `path`, `fourcc`, and `frames_written`.
- Refuse existing destinations and symlinks, encode through a temporary file, and
  replace the destination only after encoding succeeds, so a failure leaves any
  existing file untouched.
- Report unavailable codecs instead of writing a broken or empty file.
- Add no dependency: OpenCV already ships as an unconditional DrawCV requirement.
- Add `docs/VIDEO.md`, `examples/video_lesson.py`, and 27 video tests.
- Verified locally on Windows 11 / CPython 3.12 / opencv-python 5.0.0.93:
  171 tests pass, and the cell lesson encodes to 120 mp4v frames at 12 fps whose
  only large frame-to-frame changes fall exactly on the two step boundaries.
- Transitions, progressive reveals, timed captions, and audio remain pending.

## 0.1.0a5 — development milestone, shipped inside 0.1.0a11

- Add step durations and trailing pauses, direct time seeking, and streaming Canvas frames.
- Save timing in schema v2 and load schema v1 with three-second defaults.
- Add timing example, boundary/round-trip tests, and Antigravity continuation instructions.
- Video encoding and transitions remain pending.

The first public release was 0.1.0a3; earlier versions were local development milestones.

## 0.1.0a4 — lesson persistence, shipped inside 0.1.0a11

- Save and reopen full lessons through versioned JSON, including drawing and teaching state.
- Preserve target, label, callout, drawable, and step identities and shared references.
- Add target lookup, source-drawable access, a packaged JSON Schema, and clear content errors.
- Protect existing saved lessons on validation/write failures.
- Add an AI authoring guide and a runnable save/revise example.
- Preserve the published 0.1.0a3 artifacts unchanged.

## 0.1.0a3 — first alpha (published 2026-09-20)

- Add installed-wheel CI for Windows, Linux, and macOS on Python 3.12–3.14.
- Add repeatable distribution, documentation, and installed-example checks.
- Add MIT license and author metadata approved by Nuh Yamin.
- Document compatibility evidence, the tutorial authoring workflow, alpha API
  expectations, and a manual publishing procedure.
- Keep `pydrawcv==0.10.0.post1` as the tested dependency contract.

No intentional public API or drawing behavior changes from 0.1.0a2.
CI configuration alone is not evidence that every matrix environment passes.

## 0.1.0a2 — static tutorial workflow

- Wrapped callouts, rectangular highlights, group-aware dimming, and shared themes.
- Ordered PNG export with collision checks and partial-failure reporting.
- Three-step cell lesson and nested-group example; 54 passing local tests.

## 0.1.0a1 — initial rendering API

- Teaching targets, reusable labels, straight leader lines, independent steps,
  and source-preserving PNG rendering.
- Installable src-layout package, example, 30 tests, and AI handoff documentation.

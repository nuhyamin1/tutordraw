# AI handoff — start here

Last updated: **2026-09-25**, graph constructions (Claude Code).

## Unreleased: graphs you can draw into (2026-09-25)

**Why**: in Illustrate, a model asked about integrals shaded the area under
y = x² with a polygon it placed in canvas pixels, ending at x ≈ 1.6 instead
of 2. The kit owns the pixel mapping and the curve's function, so it now
builds what follows from a curve. On `Axes` (`src/tutordraw/kits/graphs.py`):
`region(f, g=0)`, `rectangles(f, domain, count, rule=)`, `tangent(f, x)`,
`secant(f, x1, x2)`, `intersections(f, g=0)`; for own shapes in graph units
`clip(points, closed=)` and `add(drawable)`; `to_scene_offset`, `contains`.
Rationale in DECISIONS.md ("Graph constructions"), reference in KITS.md, and
AI_AUTHORING.md tells models never to shade or slice a graph in pixels.

- Tests: `tests/test_graph_constructions.py` (14 tests: a region's top edge
  lies on y = x², rectangles meet the curve at their rule point, tangent and
  secant slopes, intersections including a touching root and tan's pole,
  exact clipping, save and load). **Ran: `python -m pytest tests -q -p
  no:cacheprovider`: 561 passed, 1 skipped.** Also rendered and inspected by
  eye (area under a curve, Riemann sum, region between curves with tangent
  and chord, a clipped triangle).
- **Not released.** Illustrate installs this checkout editable until the
  owner publishes; the version in pyproject is still 0.2.0a1. Nothing in the
  lesson schema changed: the constructions are ordinary DrawCV paths and
  lines in the axes' group.
- **Next**: motion along a curve (ROADMAP P5): `Step.animate` eases in
  straight lines, so a point cannot yet slide along y = f(x).

## Current state

**Published: 0.2.0a1 (2026-09-24)**, the milestone first called 0.1.0a12,
renumbered by the owner because the change from 0.1.0a11 is large; it stays
an alpha. The owner authorised it and uploaded from their PC (twine used a
credential already stored there; none is in the repository or the cloud
session). Their Windows run before upload: 547 passed, 1 skipped (the
symlink case; the font tests ran), `check_release --require-metadata`
passed. Verified afterwards from PyPI in a clean Linux venv:
`tutordraw[math]==0.2.0a1` installs, reports 0.2.0a1, saves schema v9, and
typesets an equation. Earlier releases: 0.1.0a11 (2026-09-21), 0.1.0a3.

**Found after release, fix in the next version:** taps land on filled ink
only, so a tap between an equation's glyphs (or on thin text) misses: 87 of
120 grid taps over `E = mc^2` counted, and its bounds' centre did not. Make
prompt hit testing forgiving (e.g. accept a tap within a few pixels of the
answer, or inside a text-like target's bounds) in both `prompts.hits` and
the player.

Six milestones landed on 2026-09-21: a6 video export, a7 annotation text beyond
ASCII, a8 per-step artwork changes, a9 Thai and Arabic, a10 animation between
beats, a11 timed annotation reveals. All are pushed, and **0.1.0a11 was
published to PyPI** by the owner after explicit authorisation.

Owner: Nuh Yamin; package tutordraw; MIT. Origin:
https://github.com/nuhyamin1/tutordraw.git, branch master.
Runtime is now published `pydrawcv==0.11.0` (a12; a11 and earlier pin
`0.10.0.post1`). DrawCV itself was not modified.

Standing owner instructions: **commit locally, do not push, do not publish**
without an explicit request. Inspect Git rather than trusting a handoff's Git
claims — an earlier handoff wrongly said nothing had been committed.

## What TutorDraw is actually for

The owner clarified the product this session, and it should steer prioritisation.
TutorDraw is the **visual engine for an interactive, real-time, AI-driven
explainer**: a user asks "explain a lunar eclipse", an LLM narrates with voice
and/or text, and TutorDraw renders the visuals live. It is **not** an offline
video-production tool, and the audience is "everyone" — English first, then Thai
and Arabic.

Consequences worth remembering:

- **An LLM is a first-class caller.** Error messages must be actionable by a
  model at runtime, and `docs/AI_AUTHORING.md` is a load-bearing document.
- **Latency matters, but is not currently a problem.** Measured this session:
  `render_step` 35–40 ms on the cell lesson, `to_json` 8 ms, `from_json` 1 ms.
  Do not start performance work without a measurement showing a regression.
- **Video export is peripheral**, useful for saving and sharing rather than
  being the product. Do not over-invest in it.

## Completed functionality

- M1/M2: labels, leader lines, wrapped callouts, highlights, group-aware dimming,
  themes, independent static steps, safe scene copies, collision-aware PNG export.
- M3: packaging, manual release tools, installed-wheel CI; a3 published. **M3 is
  now complete** — hosted CI passes (see below).
- a4: JSON lesson persistence, stable IDs, target lookup, AI editing guide.
- a5: step `duration`/`pause`, seeking, `render_frames`, schema v2 with v1 loading.
- a6: `Tutorial.export_video(...)` and `VideoExportError`. See [VIDEO.md](VIDEO.md).
- a7: annotation text beyond ASCII. See [TEXT.md](TEXT.md).
- a8: `Step.restyle` and lesson schema v3. See [RESTYLE.md](RESTYLE.md).
- a9: Thai and Arabic behind the optional `typography` extra. See [TEXT.md](TEXT.md).
- a10: `Step.animate` and lesson schema v4. See [ANIMATION.md](ANIMATION.md).
- a11: `show(at=)` / `explain(at=)` and schema v5. See [REVEAL.md](REVEAL.md).
- a12: automatic label collision avoidance, on by default; `label(box=False)`
  for bare text; schema v7. Also fixes `restyle(fill=...)` on gradient fills.
  See [API.md](API.md). **Moves to `pydrawcv==0.11.0`**, with panel borders and
  highlights snapped to the pixel grid; see COMPATIBILITY.md and DECISIONS.md.

## What a7 decided and why

The printable-ASCII gate at the old `model.py:89` was **both too strict and
load-bearing**, which is why it needed replacing rather than deleting:

- Too strict: OpenCV already draws Latin-1, Greek, Cyrillic, CJK and the symbols
  a science diagram needs (`µ ° × ± ≤ ½ —`). TutorDraw was refusing characters
  its own renderer handles correctly.
- Load-bearing: OpenCV substitutes a literal `?` for Thai **without raising**,
  and draws Arabic unjoined and left to right. Deleting the gate would have
  traded a visible limitation for silent corruption.

So `src/tutordraw/text.py` validates each character twice, and both must pass:

1. **A script allow list** of Unicode ranges needing no shaping, reordering or
   mark positioning. An allow list, so an unrecognised script fails loudly.
2. **A runtime probe** rendering the character through DrawCV's real path and
   comparing against the placeholder. A probe rather than a table because glyph
   coverage varies by OpenCV version — the dependency floor is 4.8, this host
   runs 5.0 and draws CJK. Cached; ASCII skips it, so the common path is free.

Text is normalised to NFC at creation. Errors name the character, its codepoint
and the fix, and distinguish "unsupported script" from "this build cannot".

**Error messages are deliberately pure ASCII**, using `ascii(char)` rather than
`repr(char)`. This was found the hard way: a legacy Windows console (cp1252)
raises `UnicodeEncodeError` when printing the offending character, so an error
message containing it would hide the very failure the caller needs to read.
`U+XXXX` carries the identity instead. Keep this property; a test asserts it.

## What a8 decided and why

Building the owner's own example, "explain a lunar eclipse", exposed the real
limit: a lesson was one fixed drawing with annotations on top, so the narration
could say "the Moon turns red" while the Moon stayed grey. A step could point at
artwork but never change it.

The obvious workaround, editing `target.drawable` between renders, was tested
and rejected: every render reads the current source, so an edit is retroactive
and silently rewrites steps already rendered.

`Step.restyle(target, move=, fill=, opacity=, visible=)` applies to the working
copy each render already makes, **before** labels, highlights and dimming are
computed. That keeps steps independent, leaves the source untouched, and makes
attached annotations follow a moved target for free. A test asserts a `move`
produces pixel-identical output to moving the source object by the same amount.

`move` is a delta, not an absolute, because DrawCV transforms are separate from
shape coordinates and a delta composes with both. `opacity` is absolute while
`dim_others` keeps multiplying, so the two compose instead of fighting. Schema
bumped to v3 with `restyles` required per step, following the v2 timing
precedent; v1 and v2 still load, saving always writes v3.

## What a9 decided and why

DrawCV's font engine supports exactly Latin, Thai and Arabic, matching the
owner's stated languages. Four decisions shaped the implementation, all in
DECISIONS.md:

1. **Optional extra, not a dependency.** `pip install "tutordraw[typography]"`
   pulls five native packages. A default install still needs only `pydrawcv`,
   and the built-in renderer keeps covering Latin, Greek, Cyrillic, CJK.
2. **No bundled font.** The owner deferred this; the conventional answer is
   recorded instead. `Tutorial(font=...)` takes a path, bytes or a `FontAsset`.
3. **Renderer chosen per annotation.** The two paths have complementary gaps:
   the font engine rejects Greek, Cyrillic and CJK, the built-in one cannot
   shape Thai or Arabic. A per-lesson switch would mean enabling a font
   silently broke Greek. Per annotation, both coexist in one lesson; a single
   annotation mixing them raises, naming the fix.
4. **The font is not persisted.** A lesson file would need a machine-specific
   path or an embedded megabyte. The text declares the need instead, so loading
   without a font raises naming the first character requiring one. **No schema
   change** — still v3.

Two quality fixes came out of looking at real output: Thai was breaking
mid-syllable, now segmented with the bundled `pythainlp`; and wrapped
right-to-left lines were left-aligned, now hung from the panel's right edge.

## What a10 decided and why

This is the first feature to touch the timing contract, so the contract
decisions matter more than the code. All are in DECISIONS.md.

1. **Opt in per step.** Every frame used to equal some `render_step` output,
   and `test_timing.py` and `test_video.py` depend on it. Animating by default
   would silently change every lesson. `step.animate()` relaxes the identity
   only where asked; hard cuts stay the default.
2. **`render_step` still means the finished state.** PNG export is unaffected;
   only `render_at_time` interpolates.
3. **Animate from the previous step's state.** A restyle is already relative to
   the source, so no new data is needed, and two behaviors fall out for free: a
   step repeating a move stays put, and a target the next step ignores slides
   home.
4. **Reuse DrawCV's 25 easing curves** via `get_easing`, storing names
   lowercase because DrawCV matches case-insensitively.

`visible` is not interpolated (a boolean has no midpoint) and `fill`
interpolates in plain RGB. Both documented rather than hidden.

An expected cost did not materialise: animated frames measure the same as
static ones, ~35 ms, because every frame was always rendered from scratch.
Animation removes a caching opportunity that was never taken.

## What a11 decided and why

Deliberately small: the caller could already fake reveals by adding a step per
reveal, so the bar was convenience, not capability.

1. **Extend `show` and `explain` with `at=`** instead of adding a concept.
   Both already mean "this annotation belongs to this step"; a delay is one
   more attribute of that.
2. **Seconds from the step's start**, not an ordering index or a stagger,
   because the product drives narration from a model that knows when each
   sentence lands.
3. **A delay alone makes a step time-varying**; requiring `animate()` too
   would be unrelated coupling. This generalised `_render`, which now takes
   raw progress, derives elapsed seconds for reveals, and applies the easing
   curve only to artwork blending.
4. **A delay past the duration clamps to the end.** Rejecting it would couple
   validation to `duration` and let a later `set_timing` strand an annotation;
   never appearing would make playback and `render_step` disagree.

Annotations appear whole; no fade, because that would mean inventing a
duration. Recorded as deliberate in DECISIONS.md, not an oversight.

## What a12 decided and why

The owner reported six label panels stacked on top of one another in a real
lesson, and asked for the plan before any code. Full rationale is in
[DECISIONS.md](DECISIONS.md); the short version:

- **Ranked candidate placements, not force relaxation.** Rank 0 is exactly what
  the author wrote and wins whenever it is free; alternatives try the other
  sides, then slide along a side, then step out. Scoring is lexicographic on
  `(overlap + off-canvas, artwork coverage, rank)` — no tuned weights.
- **Greedy in registration order**, so an earlier annotation is never displaced
  and a lesson always renders identically.
- **One decision per render, not per frame.** Resolution runs against the state
  the step ends in and returns an anchor plus a nudge; the panel is still built
  from live bounds each frame. This is what stops an animated step jittering or
  swapping sides, and it keeps RESTYLE.md's pixel-identity promise.
- **Animated steps are resolved over the swept path between their two ends.**
  End-state resolution alone left a measured 4148 px² overlap when one target
  slid past another's label. A hard cut has no middle and is not penalised.
- **Reveal delays are ignored when resolving**, so nothing on screen moves when
  a delayed annotation appears; its slot simply waits for it.
- **On by default**, the owner's call, with `Theme(avoid_collisions=False)` as
  an exact escape hatch. One existing test changed:
  `test_off_canvas_warning` now pins the legacy path explicitly.
- **`label(box=False)` draws bare text**, added after the owner asked whether a
  label had to be boxed. It did — the panel `Rectangle` was unconditional and
  the theme could not fake its absence. Per-label rather than theme-wide, to
  mirror `leader`. The panel is still measured, so placement and collision
  avoidance are unchanged. This is what took the format to v7.

## Code map and changed files

a7 (text):
- `src/tutordraw/text.py`: **new** — ranges, cached probe, one validator.
- `model.py`: `make_annotation` calls `validate_annotation_text`.
- `tests/test_text.py` (29 cases), `docs/TEXT.md`, `examples/symbols_lesson.py`.

a8 (per-step artwork):
- `model.py`: `Restyle` record and `Step.restyle`; `Step._restyles`.
- `attention.py`: `apply_restyles`, called from `tutorial.render_step` before
  `apply_attention` so annotations follow moved artwork.
- `adapters/drawcv.py`: `supports_fill`, `set_fill`, `translate` keep the
  DrawCV specifics out of the model, per AGENTS.md.
- `serialization.py`: schema v3, `SUPPORTED_VERSIONS`, restyle round trip.
- `lesson-v3.schema.json`: **new**, generated from v2 and packaged.
- `tests/test_restyle.py` (32 cases), `docs/RESTYLE.md`,
  `examples/eclipse_lesson.py`.

a9 (Thai and Arabic):
- `pyproject.toml`: optional `typography` extra; `dev` includes it.
- `tutorial.py`: `font=` on the constructor and all three loaders; `tutorial.font`.
- `adapters/drawcv.py`: `load_font`, `typography_errors` context manager that
  rewrites DrawCV's missing-engine message into TutorDraw's install command.
- `text.py`: `FONT_SCRIPT_RANGES`, `uses_font_path`, `is_rtl`, `thai_segments`;
  the validator now takes `font=` and distinguishes "needs a font" from
  "cannot draw at all".
- `layout.py`: `annotation_text` picks the renderer per line,
  `FONT_SIZE_PER_SCALE = 24`, Thai segmentation and RTL alignment in wrapping.
- `serialization.py`: `font=` threaded through `from_dict`/`from_json`/`load_json`.
- `tests/test_fonts.py` (11 cases, skipped without a covering font),
  `examples/multilingual_lesson.py`.

a10 (animation):
- `model.py`: `Step.animate`, `Step.hard_cut`, `Step.easing`.
- `attention.py`: `_blend` interpolates one drawable between two restyles;
  `apply_restyles` now takes `previous` and `progress`.
- `timing.py`: `position_at_time` returns (step index, progress through duration).
- `tutorial.py`: `_render(index, progress, alpha)`; `render_step` passes 1.0,
  `render_at_time` applies the easing curve.
- `adapters/drawcv.py`: `current_fill` for the colour an animation starts from.
- `serialization.py` + `lesson-v4.schema.json`: nullable easing per step.
- `tests/test_animation.py` (19 cases), `docs/ANIMATION.md`; the eclipse
  example animates its last two beats.

a11 (annotation reveals):
- `model.py`: `at=` on `show` and `explain`, `Step.reveals`, `Step.revealed_at`.
- `tutorial.py`: `_render` derives elapsed seconds and skips unrevealed
  annotations; easing moved inside it so reveals and animation share one path.
- `serialization.py` + `lesson-v5.schema.json`: per-step id-to-seconds map.
- `tests/test_reveal.py` (20 cases); the eclipse example delays each explanation.
- **`tests/conftest.py` is new and worth knowing about**: `SCHEMA_VERSION`,
  `STEP_FIELDS_ADDED`, `downgrade()` and `packaged_schema()`. A schema bump now
  updates that one table, and one parametrised test covers every older version.
  Four bumps in a day made the old copy-paste approach untenable.

Shared: `tools/check_installed.py` runs eight examples and **fails if no video
was produced**; `tools/check_release.py` requires three schemas plus the new
docs and examples. Version a8 in `pyproject.toml` and `__init__.py`. README,
API, PERSISTENCE, TIMING, COMPATIBILITY, ARCHITECTURE, AI_AUTHORING, DECISIONS,
ROADMAP and CHANGELOG updated.

a12 (collision avoidance):
- `src/tutordraw/collision.py`: **new** — candidate generation, lexicographic
  scoring, greedy resolution, and `plan_annotations`, which builds the whole
  step's decision from reference geometry.
- `layout.py`: split into `measure_label` / `place_panel` / `label_artwork`, plus
  `Placement`, `Measured`, `anchor_points` and `clamp_panel`. `label_artwork`
  keeps its old signature and behaviour when no placement is supplied.
- `attention.py`: `residual_moves` and `final_bounds` give the step's end-state
  (and start-state) geometry without a second scene copy, by translating through
  the real transform pipeline and restoring saved translations by assignment.
- `tutorial.py`: `_render` plans once, then draws; it now passes the planner the
  real previous step even at progress 1, so every frame plans identically.
- `themes.py`: `avoid_collisions` and `collision_margin`.
- `model.py`: `Label.box`, and a `box` argument on `Target.label`,
  `Step.explain` and `make_annotation`. `layout.py` skips the panel when it is
  false, after measuring it as usual.
- `serialization.py`: schema v7, `THEME_FIELDS_ADDED` and
  `ANNOTATION_FIELDS_ADDED`, so older documents omit the new fields and take
  the defaults.
- `lesson-v6.schema.json` and `lesson-v7.schema.json`: **new**, generated from
  their predecessors and packaged.
- `adapters/drawcv.py`: `paint_color`; `current_fill` reads `fill.paint`.
- `tests/test_collision.py` (25 cases), `tests/conftest.py` theme-field table.

a12 (DrawCV 0.11.0 upgrade, 2026-09-24):
- `pyproject.toml`, `tools/check_installed.py`, `tools/check_release.py`: pin
  `pydrawcv==0.11.0` (and the `typography` extra).
- `adapters/drawcv.py`: **new** `crisp_rect`, snapping a stroked rectangle's
  edges inward onto the pixel grid. Used by `layout.label_artwork` (panel) and
  `attention.highlight_artwork`.
- `__init__.py`: `__version__` was still `0.1.0a11`; now `0.1.0a12`.
- `tests/test_drawcv_compatibility.py`: 5 cases for `crisp_rect` and a render
  test asserting a solid 1 px border and a solid 3 px highlight edge.
- README, COMPATIBILITY, VIDEO, ARCHITECTURE, DECISIONS, ROADMAP, CHANGELOG.

## The explainer program — read ROADMAP.md first

On 2026-09-24 the owner approved a five-milestone program (ROADMAP "The
explainer program"): P1 golden tests, P2 `lint()`, P3 a visual vocabulary in
**one** schema v8, P4 SVG browser playback with streaming, P5 kits, equations,
narration timing, prompts and alt text. **P1-P4 are done and pushed. P5 is next.**

Hosted CI on c0ce0cc (pushed 2026-09-24, run 35933989412): **all nine jobs
green**, Windows/Ubuntu/macOS x CPython 3.12-3.14, including the golden image
tests, the v8 schema, the lever and web examples from the installed wheel, and
the packaged player.js. The player itself is still verified only by eye in
Chromium; CI does not run JavaScript.

P4 added `src/tutordraw/svg.py` (native text, halo stroke, timing stamps),
`web.py` (`web_step`, bundle, `export_web`, easing table, camera keyframes),
`player.js` (packaged; `TutorDrawPlayer`), `Tutorial.to_svg/web_step/
export_web`, `_compose(complete=)`, stable `td-` IDs in layout/attention/marks/
camera, `replace_in_place` in the adapter, `tests/test_web.py` (9),
`examples/web_lesson.py` (run by check_installed), `docs/WEB.md`.
check_release now requires every packaged .json/.js file in the wheel.

P4 verification: `.venv` **395 passed, 1 skipped**; wheel built,
`check_release` passes, installed wheel 395 passed, `check_installed` ran ten
examples (22 PNGs, 1 video, web page + NDJSON). In the Chromium browser pane:
camera mid-zoom and end, draw-on at 0.4/0.8/1.5 s, motion and lever steps
matched their Python renders; a simulated stream showed "waiting for the next
step" and resumed exactly when the step arrived (5.0 s). The script-injection
test was mutation-checked. web_step: 34/96/290 ms on the lever steps.

P5 (1) done: `Tutorial.describe` in `src/tutordraw/describe.py`, the
`description` payload field, the player's live region and image label,
`tests/test_describe.py` (12), `docs/DESCRIBE.md`, and stricter inline-JSON
escaping in `export_web`. Suite **407 passed, 1 skipped**; in the browser pane
the eclipse page exposes each step's description as the image label and live
region (accessibility tree checked).

P5 (2) done: `Step.narrate` (`src/tutordraw/narration.py`), `narration` in
`web_step`, captions in the player, `EMPTY_MARK` for zero-length arrows,
`tests/test_narration.py` (15), `docs/NARRATION.md`; the lever example is now
narrated. Suite **423 passed, 1 skipped**. In the browser pane the narrated
lever page showed the caption on the right word at 4.5 s with only the cued
labels revealed. Narration text is not persisted (deferred to the next format
bump, see DECISIONS).

P5 (3) done: `tutordraw.kits.Axes` (`src/tutordraw/kits.py`), chunked stroke
obstacles and text obstacles in the planner (`stroke_boxes` in the adapter),
`describe()` grammar fixes, `tests/test_kits.py` (34), a `graph` golden frame,
`examples/graph_lesson.py` (run by check_installed), `docs/KITS.md`. Suite
**459 passed, 1 skipped**; the graph example's three steps and the golden were
inspected by eye. Found and fixed a DrawCV default-pivot cost (graph render
7.5 s -> 155 ms, lint 11 s -> 327 ms; see DECISIONS) and made lint judge
unfilled strokes by ink boxes. **Worth raising upstream with DrawCV:** default
pivots make world mapping O(points squared) for large paths and groups.

P5 (3b) done: `NumberLine` kit with hops as step marks, a `numberline` golden
frame, `examples/number_line_lesson.py` (run by check_installed), 5 more kit
tests; axes-kit push CI run 35938539770 green on all nine jobs.

P5 (3c) done in a **Claude Code cloud session** (Linux, CPython 3.12 venv made
with `uv venv -p 3.12 .venv` and `uv pip install -e ".[dev,typography]"`; use
`.venv/bin/python` there): `Flowchart`, `Timeline`, `Cycle`, `ForceDiagram`,
`CrossSection`. `src/tutordraw/kits.py` became the package `src/tutordraw/kits/`
(`graphs.py` holds Axes and NumberLine unchanged, `diagrams.py`, `science.py`,
shared `_base.py`). New `tests/test_kits_diagrams.py` (44), golden frames
`processes` and `science`, five narrated examples (`flowchart_lesson.py`,
`timeline_lesson.py`, `water_cycle_lesson.py`, `forces_lesson.py`,
`earth_layers_lesson.py`, all lint-clean and in `check_installed`), and
KITS/API/AI_AUTHORING/README/CHANGELOG/DECISIONS. Evidence: suite **502
passed, 11 skipped** (skips: font tests, no Thai/Arabic font on the Linux
container, and the symlink case); wheel built, `check_release
--require-metadata` passes, installed wheel 502 passed, `check_installed` 26
PNGs + 1 video. Every example step and both new golden frames inspected by
eye; fixes found that way are in DECISIONS "Five more kits". Regenerating
goldens on Linux rewrote `cell-step1/3.png` within tolerance; those were
restored, only the two new references were added. Hosted CI for this commit
must be checked after the push: the new goldens were made on Linux, not
Windows.

Kits push be51fae: hosted CI run 35946399572 **green on all nine jobs**,
including the two Linux-made golden frames on Windows and macOS.

P5 (4) done, same cloud session: interactive prompts. New
`src/tutordraw/prompts.py` (`Prompt`, `Answer`, hit testing, payload),
`Step.ask`/`prompt`/`clear_prompt` in `model.py`, `Tutorial.hit_test` and
`check_answer`, `prompt` in `web_step`, the player's prompt bar and
`onanswer`, `PROMPT_HIDDEN`/`PROMPT_UNTAPPABLE`/`PROMPT_GIVEAWAY` in
`lint.py`, the closing sentence in `describe.py`, `LessonWarning` on saving,
`tests/test_prompts.py` (11; the lint rule mutation-checked),
`examples/quiz_lesson.py` (in check_installed and check_release),
`docs/PROMPTS.md`. Evidence: suite **513 passed, 11 skipped**; wheel built,
check_release passes, installed wheel 513 passed, check_installed clean. In
headless Chromium (global Node Playwright 1.56, `/opt/pw-browsers`): the quiz
page asked on its last step; a tap on Evaporation ringed it red with the
author's wrong text; a tap on Condensation ringed it green; three misses on
empty canvas ringed the answer amber with the hint; a two-step page held past
its 1 s step until answered, then moved to step 2 about two seconds later; no
page errors. Screenshots inspected by eye. CI does not run the JavaScript.

Prompts push d90e3bc: hosted CI run 35948353665 green.

P5 (6) done, owner approved: **lesson schema v9**, adding step `narration`
and `prompt` (`serialization.py`, new `lesson-v9.schema.json` generated from
v8 and packaged, `conftest.py` table). The pre-v9 "prompts are not saved"
warning and its `LessonWarning` class were removed before any release.
Tests: prompt and narration round trips validated against the packaged v9
schema, malformed saved prompts refused; suite **519 passed, 11 skipped**.
Docs: PERSISTENCE, COMPATIBILITY, NARRATION, PROMPTS, API, AI_AUTHORING (its
stale "Current limits" paragraph rewritten), CHANGELOG, ROADMAP.

Schema v9 push 4794f3e: hosted CI run 35949502793 green.

P5 (5) done, same session: **equations**, `src/tutordraw/kits/equations.py`
(`Equation`, optional `math` extra = `ziamath>=0.13,<0.14`, also in `dev`
so CI runs the tests). Suite **537 passed, 11 skipped**; installed wheel and
check_installed clean. `tests/test_equations.py` (17, skipped without
ziamath; one proves saved equations open without it), an `equation` golden frame (Linux-made; the extra is in `dev`, so
CI checks it), `examples/pythagoras_lesson.py` (in check_installed, skipped
there without the extra, and in check_release). Docs: KITS, API,
AI_AUTHORING, README, COMPATIBILITY (new "Optional math extra"), CHANGELOG,
ROADMAP, DECISIONS "Equations" (includes a measured DrawCV per-point cost worth
raising upstream).

Release preparation, same session: version 0.2.0a1 in `pyproject.toml` and
`__init__.py`; CHANGELOG dated with a renumbering note; README status,
install line and extras; RELEASING filenames; "new in" notes in the docs.
Gate evidence: suite 537 passed, 11 skipped; check_docs 27 documents;
fresh build; `check_release --require-metadata` passes (twine check
--strict); a clean venv installing the wheel with `[math,typography]` from
PyPI has consistent dependencies, runs the suite (537 passed) and
check_installed. PyPI had only 0.1.0a3 and 0.1.0a11 before upload. The branch
is merged into master (merge commit, no rewrite); hosted CI on master is the
last gate.

**P5 is complete.** Every item in ROADMAP P5 is checked. Next candidates, for
the owner to choose: raise the DrawCV `transform_point` cost upstream; the
backlog items in ROADMAP; a release of 0.1.0a12 (only on the owner's explicit
request; it is unpublished). **Do not bump the format again** without the
owner's approval.

P3 (schema v8) added `src/tutordraw/marks.py` (arrow/brace/measure/angle/
number geometry), `camera.py` (fit, blend, install-as-group), `Mark`/`Camera`
and the new `Step` methods in `model.py`, draw-on through DrawCV
`render_progress`, `outline_path`/`rect_path` in the adapter, the halo in
`layout.py`, camera- and mark-aware planning in `collision.py`, `MarkLayout` in
`composition.py`, v8 in `serialization.py` + `lesson-v8.schema.json`, lint for
marks, `docs/VOCABULARY.md`, `examples/lever_lesson.py` (also run by
`check_installed`), `tests/test_marks.py` (25 cases) and 11 golden frames.
Design and implementation notes: DECISIONS "Visual vocabulary and schema v8".

P3 verification: `.venv` suite **386 passed, 1 skipped**. Wheel built,
`check_release --require-metadata` passes, installed wheel **386 passed**,
`check_installed` ran nine examples (22 PNGs, 1 video). Inspected by eye: all
11 new golden frames, the five-shape outline sheet, and the lever lesson's
three steps and mid-draw frame. Old references unchanged except `bare-step1`
(halo, intended). Found and fixed while building the example: `Path.offset`
slowness (2.4 s -> 9 ms via own offset), a lint float-noise false positive,
force arrows needing point ends, and vertical-arrow captions.

**Next concrete task — P4 design.** Browser playback: export a step's
`Composition` to SVG (DrawCV 0.11 `SVGExport`; check it handles the camera
group, `render_progress` and the halo copies), plus a per-lesson JSON timeline
(steps, durations, reveal/draw times, camera states) that a small web player
animates between. Decide first whether the player re-implements draw-on and
camera tweening in the browser (small payloads, true streaming) or receives
pre-rendered SVG keyframes (simpler, heavier). Recommendation: SVG per step at
its finished state + the timeline JSON, with the player doing draw-on via
`stroke-dashoffset` and camera via a `viewBox`/transform tween; streaming =
emit each step's SVG + timeline entry as soon as it is authored.

P2 added `src/tutordraw/lint.py`, `Tutorial.layout` / `Tutorial.lint`,
`Composition.drawables`, `_compose(draw_annotations=)`, exports in
`__init__.py`, `tests/test_lint.py` (9 tests; each rule mutation-tested), and
docs in AI_AUTHORING.md, API.md, CHANGELOG, DECISIONS. Suite: **347 passed, 1
skipped** in `.venv`; golden references unchanged.

**Next concrete task — P3 design, before any code.** Write the v8 design in
DECISIONS.md covering all eight P3 items at once: which are `Step` methods vs
`Target` factories, what each persists, how each draws, and how each animates
(one "draw-on" progress model shared by leaders, highlights, arrows, braces,
dimensions). Suggested shape: new annotation kinds (`arrow`, `brace`,
`dimension`, `angle`, `marker`) stored in one `step["marks"]` list with a
`kind` discriminator so v9+ can add kinds without a new top-level field;
`step["camera"]`; `draw_on` as a per-annotation reveal style next to `at=`.
Then implement in that order: draw-on, camera, arrows, markers, braces,
dimensions/angles, shape highlights, halo. Each must: add golden frames, pass
lint (extend lint for new kinds), and round-trip through schema v8.

P1 changed files:
- `src/tutordraw/composition.py`: **new** — `Composition`, `AnnotationLayout`,
  `HighlightLayout`, `to_dict()` geometry snapshot.
- `tutorial.py`: `_render` = `_compose` + rasterize; `_compose` records geometry.
- `tests/golden_lessons.py`, `tests/test_golden.py`, `tests/golden/` (10 frames
  x PNG + JSON). `MANIFEST.in` ships them in the sdist.
- CONTRIBUTING (regeneration procedure), ROADMAP, DECISIONS.

P1 verification: suite **338 passed, 1 skipped** in `.venv` (published DrawCV
0.11.0). All 10 reference frames inspected on a contact sheet. Disabling border
snapping fails 3 frames by pixels; widening every gap by 1 px fails by geometry
with exact field paths. sdist built, `check_release --require-metadata` passes,
and all 20 reference files are inside it. **Not run:** hosted CI — the pixel
tolerance is unproven on Linux/macOS; if it fails there, loosen
`CHANNEL_TOLERANCE`/`CHANGED_FRACTION`, never regenerate on CI.

**(Done) P2 as planned:** Make a public, read-only layout view over
`Composition` (suggested `Tutorial.layout(step, *, time=None)`), then
`Tutorial.lint()` returning issue objects with a stable `code`, the targets
involved, a message an LLM can act on, and a suggested fix. The golden lessons
already contain real cases to flag: leader crossings in `cell` step 3 and the
unclearable "Body" label in `motion` end. Lint must not change rendering, so the
golden tests must stay green untouched.

## Verification completed this session (DrawCV 0.11.0, 2026-09-24)

**Trap found:** both `.venv` and the global Python had DrawCV installed
*editable from `C:/Projects/DrawCV`*, so earlier "published wheel" runs in them
were really runs against the checkout. `.venv` now has the published
`pydrawcv[typography]==0.11.0`; check with
`python -c "import drawcv; print(drawcv.__file__)"` (must be under site-packages).
The global Python is still editable-from-checkout; don't use it for evidence.

- Clean scratch venv with published `pydrawcv[typography]==0.11.0`:
  `python -m pytest -q` **327 passed, 1 skipped** (symlink test).
- `.venv` after switching to the published wheel: **327 passed, 1 skipped**;
  `pip check` clean; `tools/check_docs.py` 21 documents and one README example.
- `python -m build --no-isolation`, then `tools/check_release.py
  --require-metadata`: passes. Installed that wheel: `python -I -m pytest -q`
  327 passed, 1 skipped; `python -I tools/check_installed.py`: 18 PNGs, one
  video, lessons reload. This gate caught the stale `__version__`.
- All eight examples re-rendered on the wheel. **Visually inspected** cell step
  2 (against the 0.10 render), eclipse beat 3, Arabic step 3 and group focus:
  annotations are thinner than under 0.10 as expected; panel borders and
  highlights are crisp. The eclipse "Moon" panel sits flush with the right
  edge; the first snapping version pushed its border off-canvas, fixed by
  snapping inward and covered by a test.
- The new render test fails with snapping disabled (no pixel carries the border
  colour) and passes with it.

## Verification completed in the collision-avoidance session (a12)

Use `.venv/Scripts/python.exe` instead of `python` on this Windows machine.

- `python -m pytest -q`: **321 passed, 1 skipped** — 289 before the milestone,
  plus 25 collision cases, 6 for `box`, and one more legacy-version case. One existing test changed deliberately:
  `test_off_canvas_warning` now pins the pre-avoidance path with
  `Theme(avoid_collisions=False)`, because avoidance pulls that label back.
- **Rebuilt the reported bug and inspected both renders.** Six panels on a
  physics scene ("box at rest", "puck on smooth table", "A fast (v = 6)",
  "push", "small ball B", "small ball C"): before, four panels overlap into
  unreadable mush and two more collide; after, all six are disjoint, on canvas,
  clear of the artwork, with their leaders correctly re-aimed. Written to
  `output/collision-before.png` and `output/collision-after.png`.
- **Measured the mid-animation case that end-state resolution missed.** A ball
  sliding past another's label overlapped it by 4148 px² at worst across 61
  sampled frames; with swept-path resolution it is 0 px², and that is now a
  test rather than a one-off measurement.
- `python examples/cell_tutorial.py`: **visually inspected** step 2. The
  "Nucleus" label moved up and right to clear the callout, which previously sat
  at the same height. Readable, and better than the hand-tuned original.
- Timing, on the six-panel lesson: 23 ms with avoidance on, 42 ms off — faster,
  because the resolver short-circuits on the first free candidate and its
  measurements are reused instead of `label_artwork` measuring again. A
  90-frame animated `render_frames` is 1.03x.
- **Inspected `box=False` over artwork.** A label and a wrapped callout drawn
  across a coloured band: the text sits directly on it with no hole punched,
  and both leaders still terminate correctly on the invisible panel edge.
  Written to `output/nobox.png`; `output/nobox-workaround.png` shows what the
  old background-coloured-panel workaround did to the same band.
- `python tools/check_docs.py`: 21 documents and one README example pass.

### Evidence carried over from the a11 session

- `python -m pytest -q`: **285 passed, 1 skipped** (a6 171, a7 200, a8 232,
  a9 243, a10 263). The
  skip is the symlink-refusal test, needing privileges Windows does not grant by
  default. The text tests also pass under `-W error::UserWarning`.
- `python examples/multilingual_lesson.py`: three language steps using Tahoma.
  **Visually inspected** the Thai and Arabic steps: Thai shapes correctly and
  breaks between words; Arabic is joined, right-to-left, and its wrapped second
  line hangs from the right edge of the panel. Both were wrong before the
  segmentation and alignment fixes, and neither is caught by pixel assertions.
- `python examples/eclipse_lesson.py`: four beats, 27-second lesson.
  **Visually inspected** beats 1 and 4: beat 1 hides the shadow cone and shows a
  grey Moon above it; beat 4 has the Moon moved 190 px down into the cone, red,
  with the Sun faded and the rest dimmed. The label, leader and highlight box
  all followed the moved Moon. This is the case that motivated the milestone.
- `python examples/symbols_lesson.py`: three steps written to `output/symbols`.
  **Visually inspected** steps 1 and 3: `30 µm`, `½`, an em dash, `α = 45°`,
  `2 ×` and `37 °C ± 0.5 °C` all render as real glyphs, correctly spaced, inside
  their panels, with no clipping. Wrapping measures the wide glyphs correctly.
- Confirmed by hand that Thai, Arabic, Hebrew, Devanagari and emoji each raise
  `ValidationError` naming the character and codepoint.
- **Inspected `box=False` over artwork.** A label and a wrapped callout drawn
  across a coloured band: the text sits directly on it with no hole punched,
  and both leaders still terminate correctly on the invisible panel edge.
  Written to `output/nobox.png`; `output/nobox-workaround.png` shows what the
  old background-coloured-panel workaround did to the same band.
- `python tools/check_docs.py`: 21 documents and one README example pass.
- Measured the eclipse beat by beat: light-panel pixels hold at 13,773 until
  t=1.5s then jump to 33,964 as the explanation lands, and `render_step(0)`
  equals the finished 33,964. **Visually confirmed** the t=0.5s frame shows
  three labels and no explanation panel.
- `python examples/eclipse_lesson.py` then `export_video(fps=12)`: 324 frames,
  11.4 s to generate and 13.5 s to encode, ~35 ms per frame animated or static.
  **Visually inspected** a mid-slide frame: the Moon is caught partway into the
  shadow with its label and highlight box tracking it, which is exactly what
  the static beats could not show.
- `python -m build --no-isolation --outdir output/development`: a11 built.
- `python tools/check_release.py --dist-dir output/development --require-metadata`: passes.
- Installed the a11 wheel, `python -I -m pytest -q`: **285 passed, 1 skipped**.
- `python -I tools/check_installed.py`: eight examples run outside the checkout;
  18 PNGs and one 120-frame video decode, and lessons reload correctly.
- Restored the editable install; `python -m pip check` clean.

### Hosted CI is green — earlier docs were wrong

Both `fd16904` (a5) and `c1fbef1` (a6) passed **all nine jobs**
(Windows/Ubuntu/macOS × CPython 3.12/3.13/3.14). Four documents still claimed
hosted results were pending; corrected this session. M3's last checkbox is done.

**Codec availability is now proven beyond Windows.** Since a7,
`tools/check_installed.py` fails when no video is produced, and all nine jobs
passed on `188b4d2` and `d06ceab`, each decoding the example back to 120 frames.
So at least one of mp4v, MJPG and XVID works on every supported environment.
Which one a given platform chose is not recorded, so no single codec is claimed
everywhere.

### Font-path coverage is Windows-only so far

`tests/test_fonts.py` discovers a font covering Thai and Arabic and **skips the
whole module** when none is found, so the suite still runs on a default install.
Locally it finds `C:\Windows\Fonts\tahoma.ttf` and all 11 cases run. No GitHub
runner is known to carry a font covering both scripts, so hosted CI almost
certainly skips them — treat font-path behavior as verified on Windows only, and
set `TUTORDRAW_TEST_FONT` to run them elsewhere. Getting this into CI is an open
roadmap item; vendoring a subset Noto font would be the obvious way.

Local evidence is Windows 11 x64 and CPython 3.12 unless stated otherwise.

## Next concrete task

0.1.0a11 is published and verified. a12 is committed locally, unreleased and
unpushed. It now requires `pydrawcv==0.11.0`, whose lesson files (scene schema
1.14) a11 cannot open — say so in the release notes. It adds automatic collision avoidance, on by default, plus the gradient-fill
fix. It moved the format to **schema v7** across two decisions — v6 for the
avoidance theme fields, v7 for the per-label `box` — and the owner approved each
explicitly, because both have to round-trip with a saved lesson.

**The format should now genuinely settle.** It has gone v2 to v7 in four days,
and those versions are other people's files. Prefer work that does not touch
persistence until there is a reason.

Work that does not move the format:

1. **Layout regression testing.** Now the most valuable item. Collision
   avoidance makes placement a computed result rather than an authored
   constant, and it is still only checked by eye plus box-geometry assertions.
   Golden-image tests would catch silent drift in exactly the code most likely
   to drift.
   The DrawCV 0.11.0 upgrade moved every annotation pixel and no test noticed
   except the new crisp-border one; references must be regenerated whenever
   the DrawCV pin moves.
2. **Hand-tuned gaps in the examples.** Every `gap` in `examples/` was chosen to
   dodge an overlap the library now resolves. Revisiting them would simplify the
   examples and exercise the resolver on real lessons.
3. **Font-path tests beyond Windows.** CI now proves the Thai and Arabic tests
   really run on Windows, and skips them elsewhere. A vendored subset Noto
   font would extend that to Linux.
4. **macOS typography.** Whether `pip install "tutordraw[typography]"` works
   there is still unknown; DrawCV needs source-built PyICU. Worth finding out
   before anyone reports it.

Known limits of a12, in case one of them is reported as a bug: leaders are still
straight and may cross a panel they do not belong to (routed leaders are
deferred); only **registered** targets count as artwork obstacles; a reveal slot
sits empty until its annotation appears; and a panel larger than the canvas
still warns and clips, because nothing can be done with it.

Not format-moving, from DrawCV 0.11.0: `paint_order="stroke"` could give
`box=False` text a halo so it stays legible over busy artwork.

Format-moving features to hold for later, none clearly ahead: timed captions,
fading annotations in, stroke/scale/rotation in `restyle`, whole-image
crossfades. Ask the owner rather than guessing.

## Release and environment notes

Published releases are immutable: 0.1.0a3 and 0.1.0a11.
https://pypi.org/project/tutordraw/
Prior recorded public SHA256 hashes (not rechecked this session):
- Wheel: 0026efa9b7ff6eda5dcc47d623d299eaf8a9da617c29bbc3ab6961aade8d9ea5
- Sdist: 115ae72b49c5cf55e4c45222ac658b96182f5452b90652a51173c935d4e00577

Do not replace `output/release` a3 artifacts or reuse old upload commands. Never
print or store credentials. DrawCV serialization/asset limits still apply. JSON
is not a sandbox for arbitrary assets. No source editing during rendering; no
undo history or rendered output in lesson files.

Workspace C:/Projects/TutorDraw, Windows PowerShell; Python 3.12 in `.venv`.
C:/Projects/DrawCV is context only. Git may need
`git -c safe.directory=C:/Projects/TutorDraw ...`.

## Copy this into another model

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md and docs/HANDOFF.md
> first, then docs/API.md, docs/RESTYLE.md and docs/ROADMAP.md. It is the visual
> engine for a real-time, LLM-driven explainer, not an offline video tool.
> Development a12 has timing, schema-v7 persistence, video export, per-step
> artwork changes, animation between beats, timed annotation reveals, automatic
> label collision avoidance on by default, optional unboxed labels, and text
> covering Latin, Greek, Cyrillic, CJK, symbols, plus Thai and Arabic behind an
> optional extra; 321 tests pass from source, and 0.1.0a11 is published on PyPI
> and verified after upload while a12 is local and unpushed. Hosted CI is green
> on nine jobs. There is no obvious next feature: the lesson format moved v2 to
> v7 in four days, so prefer work that does not touch persistence, and read the
> handoff's list before choosing — layout regression tests are the top pick.
> Preserve existing contracts, keep DrawCV unmodified, record only verified
> results, and do not publish or push without my instruction.

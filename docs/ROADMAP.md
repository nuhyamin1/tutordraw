# Development roadmap

M0, M1, and M2 are complete. Checkboxes represent verified
work, not intent. Milestones are ordered; no release date is promised.

## M0 — Project definition

- [x] Describe purpose, first-release scope, and deferred features.
- [x] Propose object/annotation/step architecture and rendering contracts.
- [x] Record initial decisions and integration questions.
- [x] Provide AI handoff instructions.

## M1 — First executable slice (complete)

Implement one source scene, one registered target, one attached label with a
straight leader line, one independent step, and one rendered PNG.

- [x] Inspect the development environment and verify the installed/published
  DrawCV API against the needed operations.
- [x] Add `pyproject.toml`, a `src/tutordraw/` package, development dependencies,
  and tested setup instructions. Distribution name remains provisional until checked.
- [x] Implement the minimal tutorial, target, annotation, step, and adapter code.
- [x] Verify working-scene copying and stable reference lookup.
- [x] Implement explicit side anchors and label placement.
- [x] Add `render_step` and a runnable example producing a PNG.
- [x] Test attachment after movement, repeated rendering, missing references,
  and source-scene preservation on success and failure.
- [x] Visually inspect the example output and document actual results.

**Exit condition:** in a clean environment, documented commands install the
project and produce a legible annotated image without modifying the source scene.

## M2 — Complete static tutorial workflow (complete)

- [x] Add wrapped callouts, padded outline highlights, and opacity dimming.
- [x] Support DrawCV groups and nested-target attachment/dimming.
- [x] Add multiple independent steps and ordered PNG export.
- [x] Add shared theme defaults and explicit layout overrides.
- [x] Produce the three-step cell lesson from `PRODUCT.md`.
- [x] Test rendering steps out of order, no emphasis leakage, transformed anchors,
  conflicting names, foreign targets, invalid indices, and output collisions.
- [x] Inspect text, panel clipping, pointer attachment, and group dimming visually.

**Exit condition:** the full acceptance lesson renders correctly; rerendering
after an object move updates annotation placement; order does not affect results.

## M3 — First-release preparation (complete)

- [x] Confirm package name, author, MIT license, and repository metadata.
- [x] Owner authorized and published 0.1.0a3.
- [x] Verify the exact supported dependency `pydrawcv==0.10.0.post1` using its released wheel; do not widen the range without evidence.
- [x] 0.2.0a1: move the exact pin to `pydrawcv==0.11.0`; full suite passes on the published wheel, examples re-rendered and inspected.
- [x] Replace proposed examples with runnable, tested examples and API documentation.
- [x] Document fonts, supported object types, limitations, errors, and migration
  expectations for an early release.
- [x] Build wheel and source distribution and test wheel installation in a clean
  environment outside the repository.
- [x] Verify packaged imports and the example without relying on the DrawCV checkout.
- [x] Add installed-wheel CI and document local evidence separately from intended coverage.
- [x] Obtain passing hosted Windows/Linux/macOS results for Python 3.12–3.14.
  All nine jobs passed on fd16904 (a5) and c1fbef1 (a6).
- [x] Prepare release notes and a manual publishing procedure for owner review.
- [x] Published 0.1.0a3 after explicit authorization; verified public artifact hashes.

**Exit condition:** an installable distribution and accurate documentation are
ready for release. Public upload is a separate authorized action.

## Persistence and AI authoring (development 0.1.0a4)

Prioritized after the first release to support continuation across AI sessions.

- [x] Add complete JSON save/load with stable IDs, a versioned schema, and reference validation.
- [x] Expose target lookup and current source-drawable access for resumed editing.
- [x] Verify pixel-identical round trips, detached state, malformed input errors, and save failure behavior.
- [x] Provide packaged JSON Schema, AI authoring prompts, and a save/revise example.
- [ ] Publish this update only after a new explicit release request.

## M4 — Timed lessons

- [x] Implement durations, trailing holds, deterministic seeking and streaming frames (a5).
- [x] Persist timing in schema v2; load v1 with default timing.
- [x] Export a video file from the frame iterator, with atomic replacement and
  collision safety (a6). DrawCV's VideoRenderer requires a real Scene and is not
  usable here, so TutorDraw owns a small OpenCV writer adapter instead.
- [x] Define video codec dependencies and failure reporting (a6): OpenCV arrives
  with DrawCV, no new dependency; unavailable codecs raise `VideoExportError`.
- [x] Obtain hosted CI evidence of codec availability beyond Windows/CPython 3.12:
  all nine jobs encode and decode a 120-frame video (188b4d2, d06ceab).
- [x] Design and implement transitions between beats (a10); whole-image
  crossfades are still not implemented, only per-target interpolation.
- [x] Change a target's position, fill, opacity and visibility per step (a8),
  which covers progressive reveal of artwork.
- [x] Reveal annotations progressively within a step with `show(at=)` and
  `explain(at=)`, timed in seconds from the step's start (a11).
- [x] Fade annotations in: `Theme(fade_seconds=)`, in PNG, video and the player;
  carried labels do not fade again (unreleased).
- [x] Add timed captions: `Step.caption`, captions cut from narration,
  WebVTT/SubRip export, burned-in video, player display, lint (unreleased).
- [ ] Sample DrawCV object timelines instead of only selecting static steps.

## Showing change

- [x] Per-step artwork changes through `Step.restyle`, persisted in schema v3 (a8).
- [x] Animate between beats with `Step.animate` and DrawCV's easing curves,
  opt-in per step so hard cuts stay the default (a10).
- [x] Scale override: `restyle(scale=, pivot=)` about a point of a target's
  bounds or a given point (several targets together), schema v12 (unreleased).
- [ ] Stroke and rotation overrides.

## Text and languages

- [x] Accept Latin, Greek, Cyrillic, CJK and common technical symbols, validated
  against what the installed renderer actually draws (a7).
- [x] Refuse silently-wrong scripts with actionable errors naming the character (a7).
- [x] Render Thai and Arabic through DrawCV's font path, behind the optional
  `typography` extra and a caller-supplied font (a9).
- [x] Decide the font question: TutorDraw ships none and the caller supplies one.
- [x] Reconcile the two paths per annotation, so Greek and Thai can coexist in a
  lesson; one annotation still cannot mix them (a9).
- [x] Break Thai lines at word boundaries using the bundled segmenter (a9).
- [ ] Get font-path coverage into hosted CI; no runner is known to carry a font
  covering both scripts, so those tests currently skip outside Windows.
- [ ] Support Hebrew and Indic scripts, which DrawCV's engine rejects today.

## The explainer program (owner-approved 2026-09-24)

The owner approved every item below. Order is deliberate: format-neutral work
first, then **one** lesson-format bump (v8) for all new visuals, instead of a
bump per feature. Each milestone ends with golden references regenerated and
inspected. Design notes live in DECISIONS.md.

### P1 — Golden regression tests (no format change)
- [x] Split rendering into `_compose` (working scene + `Composition` geometry)
  and rasterization; the foundation for P2 and P4.
- [x] Six canonical lessons, 10 frames, pinned by geometry (0.05 px) and pixels
  (tolerant): `tests/golden_lessons.py`, `tests/test_golden.py`, `tests/golden/`.
- [x] Shown to fail on a border-snapping change and on a 1 px gap change.
- [x] Confirm the pixel tolerance holds on hosted CI: all nine jobs
  (Windows/Ubuntu/macOS x CPython 3.12-3.14) passed on c0ce0cc, 2026-09-24.

### P2 — `lint()` for LLM self-correction (no format change)
- [x] Public read-only layout API: `Tutorial.layout(index, time=None)`.
- [x] `Tutorial.lint(index=None)`: 11 issue codes with targets and fixes;
  shape-accurate coverage and leader tests via DrawCV `contains_point`.
- [x] Documented in AI_AUTHORING.md as the author -> lint -> fix loop.
- [ ] Lint mid-animation frames (today: finished state only).

### P3 — Visual vocabulary, one schema bump (v8)
Design the whole batch before coding; persist it together.
- [x] Draw-on animation for leaders, highlights and marks (DrawCV `render_progress`).
- [x] Camera: `zoom_to` per step, animated with the step easing.
- [x] Relation arrows between targets or from a point, with a caption.
- [x] Braces grouping several targets.
- [x] Measurement (dimension) lines and angle marks.
- [x] Numbered markers (`step.number`).
- [x] Shape-following highlights via `to_path` + `flatten_world` (own offset;
  DrawCV `Path.offset` was too slow, see DECISIONS).
- [x] Halo text for `box=False`, as offset copies (DrawCV text has no stroke).
- [ ] Automatic placement of mark captions (today lint reports collisions).
- [ ] Pan without zoom; a camera that follows a moving target.

### P4 — Browser playback and streaming
- [x] SVG export of a frame (`to_svg`), with native text replacing DrawCV's
  raster text and stable element IDs.
- [x] A dependency-free web player (`player.js`) tweening between start/end
  frames (camera: 6 keyframes), with reveals and draw-on.
- [x] Streaming: `web_step` payloads appended while playing; the player waits.
- [x] A headless-browser test for `player.js`: `tests/test_player.py` drives
  it in Chromium (reveals, draw-on, fade, captions, tweens, prompt taps);
  6 passed locally, and each of three deliberate player breaks fails it. A
  CI step runs it on Ubuntu / Python 3.12 (hosted: 6 passed on Chromium 153, PR #2).
- [ ] Arrowheads riding the tip while drawing on, in the browser.

### P5 — Content and interaction
- [x] Teaching kits: axes and graphs (`tutordraw.kits.Axes`).
- [x] Graph constructions from the curve's function: `region`, `rectangles`,
  `tangent`, `secant`, `intersections`; own shapes in graph units with
  `clip` and `add` (unreleased).
- [x] Placing blocks by relation from measured bounds (`tutordraw.arrange`:
  `place`, `clear`, `shift_to`; unreleased).
- [x] Motion along a curve: a point sliding along y = f(x) (`restyle(via=)`,
  `Axes.along`, schema v10; unreleased).
- [ ] A tangent sweeping as x changes: needs rotation (or reshaping) as a
  restyle, which does not exist.
- [x] Number line kit (`tutordraw.kits.NumberLine`), hops as step marks.
- [x] More kits: flowcharts, timelines, cycles, force diagrams, labelled
  cross-sections (`Flowchart`, `Timeline`, `Cycle`, `ForceDiagram`,
  `CrossSection`).
- [x] Equations: TeX -> SVG path data -> `Path.from_svg_path`
  (`tutordraw.kits.Equation`, optional `math` extra using ziamath).
- [x] Narration-driven timing from TTS word timestamps (`Step.narrate`), with
  live captions in the player.
- [x] Save narration text and timings in the lesson file: schema v9, with prompts.
- [x] A presenter's pointer (`Step.point`): one hand per lesson that fades
  in, glides and taps, carries over between steps, avoids labels, and
  matches between Python and the player (unreleased).
- [x] Forgiving prompt taps: text and equations count anywhere in their box,
  and a tap on nothing takes the nearest target within 12 px, in `hit_test`
  and the player alike (grid over `E = mc^2`: 71 of 120 taps before, 120 now).
- [x] Interactive prompts ("tap the nucleus") via DrawCV hit testing
  (`Step.ask`, `Tutorial.check_answer`, the player's prompt bar), saved in
  schema v9.
- [x] Per-step descriptions (`Tutorial.describe`), announced by the player.

## Future backlog (not committed scope)

- Measurements, angles, braces, and relationship annotations.
- Multi-object targets outside an existing DrawCV group.
- Routed leader lines that bend around artwork; panels already avoid
  collisions automatically (a12).
- Before-and-after comparisons, zoom, and pan.
- Narration and subtitle alignment.
- Interactive lesson players, exercises, and quizzes.
- PDF or other publishing formats and richer accessibility support.

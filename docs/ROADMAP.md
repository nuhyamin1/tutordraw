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
- [x] 0.1.0a12: move the exact pin to `pydrawcv==0.11.0`; full suite passes on the published wheel, examples re-rendered and inspected.
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
- [ ] Fade annotations in; today they appear whole at their moment.
- [ ] Add timed captions.
- [ ] Sample DrawCV object timelines instead of only selecting static steps.

## Showing change

- [x] Per-step artwork changes through `Step.restyle`, persisted in schema v3 (a8).
- [x] Animate between beats with `Step.animate` and DrawCV's easing curves,
  opt-in per step so hard cuts stay the default (a10).
- [ ] Stroke, scale and rotation overrides; today only move, fill, opacity, visible.

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

## Future backlog (not committed scope)

- Measurements, angles, braces, and relationship annotations.
- Multi-object targets outside an existing DrawCV group.
- Routed leader lines that bend around artwork; panels already avoid
  collisions automatically (a12).
- Before-and-after comparisons, zoom, and pan.
- Narration and subtitle alignment.
- Interactive lesson players, exercises, and quizzes.
- PDF or other publishing formats and richer accessibility support.

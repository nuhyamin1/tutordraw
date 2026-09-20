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

## M3 — First-release preparation (local checks complete; hosted CI pending)

- [x] Confirm package name, author, MIT license, and repository metadata.
- [x] Owner authorized and published 0.1.0a3.
- [x] Verify the exact supported dependency `pydrawcv==0.10.0.post1` using its released wheel; do not widen the range without evidence.
- [x] Replace proposed examples with runnable, tested examples and API documentation.
- [x] Document fonts, supported object types, limitations, errors, and migration
  expectations for an early release.
- [x] Build wheel and source distribution and test wheel installation in a clean
  environment outside the repository.
- [x] Verify packaged imports and the example without relying on the DrawCV checkout.
- [x] Add installed-wheel CI and document local evidence separately from intended coverage.
- [ ] Obtain passing hosted Windows/Linux/macOS results for Python 3.12–3.14.
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

- [ ] Design durations, holds, transitions, and deterministic seeking.
- [ ] Integrate with DrawCV animation/video capabilities through the adapter.
- [ ] Add progressive reveal and timed captions.
- [ ] Define video codec dependencies and failure reporting.

## Future backlog (not committed scope)

- Measurements, angles, braces, and relationship annotations.
- Multi-object targets outside an existing DrawCV group.
- Automatic label collision reduction and routed leader lines.
- Before-and-after comparisons, zoom, and pan.
- Narration and subtitle alignment.
- Interactive lesson players, exercises, and quizzes.
- PDF or other publishing formats and richer accessibility support.

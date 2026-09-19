# Development roadmap

M0 and M1 are complete. Checkboxes represent verified
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

## M2 — Complete static tutorial workflow (next)

- [ ] Add wrapped callouts, padded outline highlights, and opacity dimming.
- [ ] Support DrawCV groups and nested-target attachment/dimming.
- [ ] Add multiple independent steps and ordered PNG export.
- [ ] Add shared theme defaults and explicit layout overrides.
- [ ] Produce the three-step cell lesson from `PRODUCT.md`.
- [ ] Test rendering steps out of order, no emphasis leakage, transformed anchors,
  conflicting names, foreign targets, invalid indices, and output collisions.
- [ ] Inspect text, panel clipping, pointer attachment, and group dimming visually.

**Exit condition:** the full acceptance lesson renders correctly; rerendering
after an object move updates annotation placement; order does not affect results.

## M3 — First-release preparation

- [ ] Finalize the package name, version, owner metadata, and license with the owner.
- [ ] Verify a `pydrawcv` dependency range using released artifacts.
- [ ] Replace proposed examples with runnable, tested examples and API documentation.
- [ ] Document fonts, supported object types, limitations, errors, and migration
  expectations for an early release.
- [x] Build wheel and source distribution and test wheel installation in a clean
  environment outside the repository.
- [ ] Verify packaged imports and the example without relying on the DrawCV checkout.
- [ ] Add suitable CI checks and record supported environments.
- [ ] Prepare release notes and an owner-reviewed publishing procedure.
- [ ] Publish only when explicitly requested by the owner.

**Exit condition:** an installable distribution and accurate documentation are
ready for release. Public upload is a separate authorized action.

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
- Versioned tutorial save/load.
- Narration and subtitle alignment.
- Interactive lesson players, exercises, and quizzes.
- PDF or other publishing formats and richer accessibility support.

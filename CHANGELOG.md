# Changelog

## 0.1.0a5 — Unreleased

- Add step durations and trailing pauses, direct time seeking, and streaming Canvas frames.
- Save timing in schema v2 and load schema v1 with three-second defaults.
- Add timing example, boundary/round-trip tests, and Antigravity continuation instructions.
- Video encoding and transitions remain pending.

The first public release is 0.1.0a3; earlier versions were local development milestones.

## 0.1.0a4 — lesson persistence (unreleased)

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

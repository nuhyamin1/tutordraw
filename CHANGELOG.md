# Changelog

## 0.1.0a7 — Unreleased

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

## 0.1.0a6 — Unreleased

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

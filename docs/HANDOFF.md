# AI handoff — start here

Last updated: **2026-09-20**, bounded timing milestone for Antigravity continuation.

## Current state

**Published: 0.1.0a3. Development checkout: 0.1.0a5, NOT published.**

The owner requested continued development with about 14% usage remaining and an
explicit handoff for Antigravity. This session completed the timing foundation of
M4. Video encoding, transitions, captions, and progressive reveals remain pending.
No Git commit, push, or publication was performed. The working tree was clean at
session start; current changes are this milestone. Inspect Git before committing.

Owner: Nuh Yamin; package tutordraw; MIT. Origin:
https://github.com/nuhyamin1/tutordraw.git, branch master.
Runtime remains published `pydrawcv==0.10.0.post1`. DrawCV checkout is unchanged.

## Completed functionality

- M1/M2: labels, leader lines, wrapped callouts, highlights, group-aware dimming,
  themes, independent static steps, safe scene copies, collision-aware PNG export.
- M3: packaging, manual release tools, installed-wheel CI; a3 published previously.
- a4: complete JSON lesson persistence, stable IDs, target lookup, source drawable
  access, schema v1, AI editing guide, save/revise example. Included in a5.
- a5: `Tutorial.step(title, duration=3.0, pause=0.0)`; read-only Step duration/pause;
  `step.set_timing(duration=..., pause=0.0)` atomically replaces both values.
- `tutorial.duration`, `step_at_time(time)`, `render_at_time(time, alpha=False)`,
  and lazy `render_frames(fps=30, alpha=False)`.
- Pause holds the current full image. Intervals are [start,end); exact internal
  boundaries select the next step, exact final endpoint selects the last step.
  Frame count is ceil(total*fps), timestamps k/fps, with no extra endpoint frame.
- Schema v2 requires step duration/pause. v1 loads with 3/0 defaults; saving always
  emits v2. Both JSON Schemas are packaged. a4 readers reject v2 as expected.

See [TIMING.md](TIMING.md) and [PERSISTENCE.md](PERSISTENCE.md) for exact contracts.
No DrawCV animation sampling: timed rendering selects independent static steps.

## Code map and changed files

- `src/tutordraw/timing.py`: cumulative boundaries, seeking, streaming frames.
- `model.py`: Step timing validation/properties; `tutorial.py`: public entry points.
- `serialization.py`: v2 writer and strict v1/v2 loader; `lesson-v2.schema.json` new.
- `tests/test_timing.py`: 33 timing cases; existing persistence test updated for v2.
- `examples/timed_lesson.py`: 10-second cell lesson, pause/cut PNGs, 20 frames at 2fps.
- `tools/check_installed.py`: now four examples/eight PNGs and static/timed reload.
- `tools/check_release.py`: requires both schemas and timing docs/example.
- Version in pyproject and __init__ is a5; package data includes both schemas.
- README, API, persistence, architecture, decisions, roadmap, compatibility,
  AI authoring and changelog updated. New detailed guide: docs/TIMING.md.

## Verification completed this session

Use `.venv/Scripts/python.exe` instead of python on this Windows machine.

- `python -m pytest -q --tb=short`: **145 passed** against editable source.
- `python examples/timed_lesson.py`: 10 seconds, 20 frames; outputs in output/timing.
  Visually inspected during-pause.png and next-step.png: labels/callouts fit;
  the cut switches from cell overview to nucleus emphasis and dimming correctly.
- `python tools/check_docs.py`: 16 documents and one README Python example pass.
- `python -m build --no-isolation --outdir output/development`: a5 wheel/sdist built.
- `python tools/check_release.py --dist-dir output/development --require-metadata`:
  strict Twine, metadata, schema and source-file checks pass.
- Installed a5 wheel with `pip install --no-deps --force-reinstall`, then
  `python -I -m pytest -q --tb=short`: **145 passed against installed wheel**.
- `python -I tools/check_installed.py`: four examples run outside checkout;
  eight PNGs decode and static/timed lessons reload correctly.
- Restored editable install: `python -m pip install --no-deps --no-build-isolation -e .`.
- `python -m pip check`: no broken requirements. `git diff --check`: no errors.

Tests include boundaries, out-of-order rendering, source/history preservation,
invalid options, atomic retiming, independent frame buffers, overflow, v1 migration,
v2 round trips and existing persistence/export behavior. Local evidence is Windows
and Python 3.12 only. Hosted nine-job OS/Python CI remains unverified.

Artifacts: output/development/tutordraw-0.1.0a5-*; log output/build-a5.log.
Older a4 artifacts may coexist; select filenames explicitly. Final documentation
updates are included by rebuilding the same unpublished a5 artifacts. Runtime code
was unchanged after installed-wheel verification. Nothing was uploaded.

## Next concrete task: video export adapter

Implement a small `Tutorial.export_video(...)` API as the next M4 slice, preserving
all current timing/static/persistence contracts. This API is PROPOSED, not present.

1. Read AGENTS.md, TIMING.md, API.md, and existing export.py before editing.
2. Inspect installed DrawCV `animation/video_renderer.py`. Its VideoRenderer expects
   a Scene and calls Scene.render_at_time, so it cannot directly accept TutorDraw's
   frame iterator. Choose a narrow adapter around supported APIs; avoid pretending
   a tutorial is a DrawCV Scene or modifying DrawCV. A dedicated OpenCV writer
   adapter consuming TutorDraw canvases is an option if documented and tested.
3. Validate fps, codec/container, frame dimensions and empty lessons. Handle codecs
   unavailable on the host. Release writers on all failure paths. Reject symlinks
   and collisions by default, with explicit overwrite and temporary-file cleanup,
   preserving existing files if rendering/encoding fails (see export.py).
4. Test failures with a fake writer, plus a locally available real codec. Decode
   output to verify dimensions, frame count, and images around a step boundary.
   Do not claim codec availability across platforms without CI evidence.
5. Add a runnable example and document exact limitations. Preserve JSON v1 loading
   and v2 timing. Update this handoff with actual commands/results.

Performance is deliberately simple: each frame clones/renders the scene. No cache,
transition effects, source animation sampling, audio or UI. Editing lesson/source
while consuming an iterator is unsupported. Keep broader M4 tasks unchecked.

## Release and environment notes

Published a3 is immutable: https://pypi.org/project/tutordraw/0.1.0a3/.
Prior recorded public SHA256 hashes (not rechecked in this timing session):
- Wheel: 0026efa9b7ff6eda5dcc47d623d299eaf8a9da617c29bbc3ab6961aade8d9ea5
- Sdist: 115ae72b49c5cf55e4c45222ac658b96182f5452b90652a51173c935d4e00577

Do not replace output/release a3 artifacts or reuse old upload commands. Any new
publication requires an explicit owner request. Never print/store credentials.
ASCII annotations and DrawCV serialization/asset limits still apply. JSON is not a
sandbox for arbitrary assets. No source editing during rendering; no undo history
or rendered output in lesson files. See COMPATIBILITY.md and PERSISTENCE.md.

Workspace C:/Projects/TutorDraw, Windows PowerShell; Python 3.12 in .venv.
C:/Projects/DrawCV is context only. Git may need
`git -c safe.directory=C:/Projects/TutorDraw ...`; no global setting was changed.

## Copy this into Antigravity

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md and docs/HANDOFF.md
> first, then docs/TIMING.md and docs/ROADMAP.md. Development a5 has durations,
> pauses, deterministic seeking, streaming frames, schema-v2 persistence and v1
> loading; 145 tests passed from source and installed wheel. Implement the next
> bounded milestone: safe video export, following the concrete steps in HANDOFF.
> Preserve existing contracts, keep DrawCV unchanged, and update documentation
> with verified results. Do not publish, commit, or push without my instruction.

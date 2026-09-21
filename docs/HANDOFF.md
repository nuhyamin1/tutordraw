# AI handoff — start here

Last updated: **2026-09-21**, video export milestone (Claude Code continuation).

## Current state

**Published: 0.1.0a3. Development checkout: 0.1.0a6, NOT published.**

The previous session handed off to Antigravity; the owner continued here instead
and asked for the video-export milestone named in that handoff. It is now
implemented, tested, and documented. Transitions, progressive reveals, timed
captions, and audio remain pending.

Owner: Nuh Yamin; package tutordraw; MIT. Origin:
https://github.com/nuhyamin1/tutordraw.git, branch master.
Runtime remains published `pydrawcv==0.10.0.post1`. DrawCV is unchanged.

Note for future sessions: the previous handoff said "No Git commit was
performed", but four commits exist on master through a5. Always inspect Git
rather than trusting a handoff's Git claims. The owner's standing instruction is
**commit locally, do not push, do not publish** without an explicit request.

## Completed functionality

- M1/M2: labels, leader lines, wrapped callouts, highlights, group-aware dimming,
  themes, independent static steps, safe scene copies, collision-aware PNG export.
- M3: packaging, manual release tools, installed-wheel CI; a3 published previously.
- a4: complete JSON lesson persistence, stable IDs, target lookup, source drawable
  access, schema v1, AI editing guide, save/revise example.
- a5: step `duration`/`pause`, `set_timing`, `tutorial.duration`, `step_at_time`,
  `render_at_time`, lazy `render_frames(fps=30)`, schema v2 with v1 loading.
- a6: `Tutorial.export_video(path, *, fps=30, fourcc="mp4v", overwrite=False)`
  and `VideoExportError(path, fourcc, frames_written)`.

See [VIDEO.md](VIDEO.md), [TIMING.md](TIMING.md), and [PERSISTENCE.md](PERSISTENCE.md)
for exact contracts.

## What a6 decided and why

DrawCV's `VideoRenderer` **cannot** be reused: every entry point is typed
`scene: Scene`, `render_frames` enforces `isinstance(scene, Scene)`
(`drawcv/animation/video_renderer.py:30`), and it drives `Scene.render_at_time`.
DrawCV also exposes no encoder accepting a frame sequence — grepping the whole
package for `VideoWriter|fourcc|imageio|ffmpeg|mp4|avi|webm` hits only that one
file. So TutorDraw owns `video.py`, a small `cv2.VideoWriter` adapter, and DrawCV
stays untouched.

No dependency was added. `pydrawcv==0.10.0.post1` requires `opencv-python>=4.8.0`
and `numpy` unconditionally, and DrawCV already writes PNGs through `cv2.imwrite`.
`video.py` is the only TutorDraw module importing `cv2`. Re-check this if the
DrawCV pin is ever widened. Rationale is recorded in [DECISIONS.md](DECISIONS.md).

Behavior worth knowing before changing it: the encoder opens lazily on the first
rendered frame and is sized from that frame, so a render failure opens no
encoder; the writer is released in a `finally` on every path; encoding targets a
temporary file carrying the destination's extension (OpenCV picks the container
from it) and moves into place only on success, so video export is all-or-nothing
and an existing destination survives any failure; a codec that opens but writes
zero bytes is treated as a failure. Output is opaque only — no `alpha` option,
because `VideoWriter` takes three-channel BGR.

## Code map and changed files

- `src/tutordraw/video.py`: **new**, the OpenCV writer adapter.
- `errors.py`: new `VideoExportError`; `__init__.py`: exported, version a6.
- `tutorial.py`: `export_video` beside `export_steps`, lazily importing `video`.
- `tests/test_video.py`: **new**, 27 cases (stub-writer failure paths, validation,
  atomicity, source preservation, and one real encode/decode round trip).
- `examples/video_lesson.py`: **new**, codec-tolerant; writes `output/video`.
- `docs/VIDEO.md`: **new** contract document.
- `tools/check_installed.py`: runs five examples and decodes any produced video.
- `tools/check_release.py`: requires `docs/VIDEO.md` and the new example in sdist.
- `pyproject.toml`, README, API, TIMING, ROADMAP, DECISIONS, COMPATIBILITY,
  ARCHITECTURE, AI_AUTHORING, CHANGELOG updated.

## Verification completed this session

Use `.venv/Scripts/python.exe` instead of `python` on this Windows machine.

- `python -m pytest -q`: **171 passed, 1 skipped** against editable source
  (baseline before this work was 145). The skip is the symlink-refusal test,
  which needs symlink privileges Windows does not grant by default.
- `python examples/video_lesson.py`: `10 seconds encoded as mp4v at 12 fps:
  120 frames of 1100x620`, written to `output/video/cell-lesson.mp4` (413,571 bytes).
- Decoded that file and measured every frame-to-frame change: the only large
  differences are 5.77 at t=3.0s and 5.34 at t=8.0s — exactly the two step
  boundaries. Within a held step consecutive frames are identical apart from
  codec keyframe noise (max 1.06, at the opening keyframe).
- Worst mean absolute difference between a decoded frame and its `render_step`
  source was 2.50/255. Encoding is lossy; exact equality must not be asserted.
- **Visually inspected** decoded frames 35, 36, and 110: labels, leader lines and
  callout text are legible; the t=3s cut switches from the cell overview to the
  nucleus with its highlight box and correct dimming; the final review step
  renders both labels undimmed. No visible compression artifacts.
- Codec probe on this host (opencv-python 5.0.0.93): `mp4v`/`.mp4`, `MJPG`/`.avi`,
  `XVID`/`.avi` all opened, encoded and decoded 5/5 frames. `avc1` opened only
  after OpenCV reported it could not load `openh264-2.5.0-win64.dll`, so H.264 is
  **not** claimed. `VP80`/`.webm` opened but FFMPEG reported the tag unsupported.
- `python tools/check_docs.py`: 17 documents and one README Python example pass.
- `python -m build --no-isolation --outdir output/development`: a6 wheel/sdist built.
- `python tools/check_release.py --dist-dir output/development --require-metadata`:
  strict Twine, metadata, schema and source-file checks pass.
- Installed the a6 wheel with `pip install --no-deps --force-reinstall`, then
  `python -I -m pytest -q`: **171 passed, 1 skipped against the installed wheel**.
- `python -I tools/check_installed.py`: five examples run outside the checkout;
  eight PNGs decode, one video decodes to 120 frames, lessons reload correctly.
- Restored the editable install; `python -m pip check` reports no broken
  requirements; `git diff --check` reports no whitespace errors.

Local evidence is Windows 11 x64 and CPython 3.12 only. Hosted nine-job
OS/Python CI remains unverified, and **no codec claim holds beyond this host**.

Artifacts: `output/development/tutordraw-0.1.0a6-*`. Older a4/a5 artifacts
coexist; select filenames explicitly. Nothing was uploaded.

## Next concrete task: transitions or progressive reveal

Both are genuine M4 work; pick one and keep it bounded.

1. Read AGENTS.md, VIDEO.md, TIMING.md, and `timing.py` before editing.
2. **Transitions** would change `render_at_time` from selecting one step to
   blending two, which breaks the current contract that every frame equals some
   `render_step` output. That contract is asserted in `tests/test_timing.py` and
   relied on by `tests/test_video.py`. Design the new contract explicitly —
   probably an opt-in per-step transition with hard cuts remaining the default —
   and update TIMING.md before implementing.
3. **Progressive reveal** is more contained: reveal a step's labels/callouts over
   that step's duration. It also breaks "one image per step", so it needs the
   same deliberate contract change and equally explicit documentation.
4. Whichever is chosen, preserve schema v1 loading, add schema v3 only if the
   data model genuinely grows, and keep `export_video` working unchanged.
5. Timed captions and audio are separate, later tasks. Do not start them here.

Still open from earlier milestones: hosted CI has never been observed passing,
and publishing a4/a5/a6 to PyPI needs an explicit owner request.

## Release and environment notes

Published a3 is immutable: https://pypi.org/project/tutordraw/0.1.0a3/.
Prior recorded public SHA256 hashes (not rechecked this session):
- Wheel: 0026efa9b7ff6eda5dcc47d623d299eaf8a9da617c29bbc3ab6961aade8d9ea5
- Sdist: 115ae72b49c5cf55e4c45222ac658b96182f5452b90652a51173c935d4e00577

Do not replace `output/release` a3 artifacts or reuse old upload commands. Any
new publication requires an explicit owner request. Never print/store credentials.
ASCII annotations and DrawCV serialization/asset limits still apply. JSON is not a
sandbox for arbitrary assets. No source editing during rendering; no undo history
or rendered output in lesson files. See COMPATIBILITY.md and PERSISTENCE.md.

Workspace C:/Projects/TutorDraw, Windows PowerShell; Python 3.12 in `.venv`.
C:/Projects/DrawCV is context only. Git may need
`git -c safe.directory=C:/Projects/TutorDraw ...`; no global setting was changed.

## Copy this into another model

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md and docs/HANDOFF.md
> first, then docs/VIDEO.md, docs/TIMING.md and docs/ROADMAP.md. Development a6
> has timing, schema-v2 persistence and collision-safe video export; 171 tests
> pass from source and from the installed wheel on Windows/CPython 3.12. Pick the
> next bounded milestone from the handoff (transitions or progressive reveal),
> design its contract change before implementing, preserve existing contracts,
> keep DrawCV unmodified, and record only verified results. Do not publish or
> push without my instruction.

# Changelog

## 0.1.0a12 — development milestone (unreleased)

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
  restores verbatim authored placement. Saved in lesson schema v6; v1 through v5
  still load and take the defaults.
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

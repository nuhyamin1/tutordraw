# AI handoff — start here

Last updated: **2026-09-21**, annotation reveal milestone (Claude Code).

## Current state

**Published: 0.1.0a3. Development checkout: 0.1.0a11, NOT published.**

Six milestones landed today: a6 video export, a7 annotation text beyond ASCII,
a8 per-step artwork changes, a9 Thai and Arabic, a10 animation between beats,
a11 timed annotation reveals. a6 through a8 are pushed; a9 to a11 are
committed locally only.

Owner: Nuh Yamin; package tutordraw; MIT. Origin:
https://github.com/nuhyamin1/tutordraw.git, branch master.
Runtime remains published `pydrawcv==0.10.0.post1`. DrawCV is unchanged.

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

## Verification completed this session

Use `.venv/Scripts/python.exe` instead of `python` on this Windows machine.

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

## Next concrete task: get CI green, then decide on release with the owner

The owner asked whether a11 is ready for PyPI. Preparation is done; the answer
is "not yet, and here is exactly what is missing".

**A regression was found and fixed.** Hosted CI was red from a9 to a11 on all
three macOS jobs, at `pip install ".[dev]"`. Cause: a9 put
`pydrawcv[typography]` into the `dev` group, and on macOS DrawCV requires real
`PyICU`, which publishes no wheels and builds against Homebrew ICU4C. Windows
and Linux get `pyicu-wheels`, which is why local evidence looked fine. The
extra is now outside `dev`. **All nine jobs are green on cb8f2d6.**

A follow-up worth understanding: `continue-on-error` reports a step as
`success` through the API even when it failed, so a green matrix did not prove
the extra installed anywhere. The workflow now encodes the expectation instead
of hiding it: the install may fail **only** on macOS, a step imports the five
engine modules on Windows and Linux, and `TUTORDRAW_REQUIRE_FONT=1` makes
`tests/test_fonts.py` raise rather than skip on Windows, where Tahoma covers
both scripts. So a green matrix now proves the font path really ran. Whether
the extra installs on macOS is still unknown and is documented as such.

A second, latent bug surfaced from the same investigation: a host with a font
but no engine crashed `examples/multilingual_lesson.py`, because
`export_steps` wraps render failures in `ExportError` and the example only
caught `ValidationError`. Fixed, with a platform-independent regression test.

Remaining before an upload, in order:

1. Push and confirm all nine CI jobs pass on the release commit.
2. Owner decides the version. a11 is free on PyPI; a3 is the only published
   release. a4-a10 were never published.
3. Owner decides whether the lesson format should settle first. It moved v2 to
   v5 in one day, and published schema versions become other people's files.
4. Date the shipped version in CHANGELOG.md, replacing "Unreleased".
5. Work the gate in [RELEASING.md](RELEASING.md), then ask for authorisation.

Already done during preparation: README links made absolute (relative ones 404
on PyPI, where the README is the project page), Python 3.12/3.13/3.14
classifiers added, `Typing :: Typed` deliberately **not** added because there
is no `py.typed` marker, metadata and all five schemas verified in the wheel.

Candidate features afterwards, none clearly ahead: timed captions, fading
annotations in, stroke/scale/rotation in `restyle`, whole-image crossfades,
font-path tests in CI via a vendored subset font, and automatic label
collision avoidance. Ask rather than guess.

## Release and environment notes

Published a3 is immutable: https://pypi.org/project/tutordraw/0.1.0a3/.
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
> first, then docs/REVEAL.md, docs/ANIMATION.md and docs/ROADMAP.md. It is the visual
> engine for a real-time, LLM-driven explainer, not an offline video tool.
> Development a11 has timing, schema-v5 persistence, video export, per-step
> artwork changes, animation between beats, timed annotation reveals, and text
> covering Latin, Greek, Cyrillic, CJK, symbols, plus Thai and Arabic behind an
> optional extra; 285 tests pass from source and from the installed wheel, and
> hosted CI needs a green run to confirm a macOS install fix. The owner is
> weighing a first release since a3: read the handoff's readiness list and
> docs/RELEASING.md, and do not upload anything without an explicit request.
> Preserve existing contracts, keep DrawCV unmodified, record only verified
> results, and do not publish or push without my instruction.

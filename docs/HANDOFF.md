# AI handoff — start here

Last updated: **2026-09-21**, per-step artwork milestone (Claude Code).

## Current state

**Published: 0.1.0a3. Development checkout: 0.1.0a8, NOT published.**

Three milestones landed today: a6 video export, a7 annotation text beyond
ASCII, a8 per-step artwork changes. a6 is pushed; a7 and a8 are committed
locally only.

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

Shared: `tools/check_installed.py` runs seven examples and **fails if no video
was produced**; `tools/check_release.py` requires three schemas plus the new
docs and examples. Version a8 in `pyproject.toml` and `__init__.py`. README,
API, PERSISTENCE, TIMING, COMPATIBILITY, ARCHITECTURE, AI_AUTHORING, DECISIONS,
ROADMAP and CHANGELOG updated.

## Verification completed this session

Use `.venv/Scripts/python.exe` instead of `python` on this Windows machine.

- `python -m pytest -q`: **232 passed, 1 skipped** (a6 was 171, a7 was 200). The
  skip is the symlink-refusal test, needing privileges Windows does not grant by
  default. The text tests also pass under `-W error::UserWarning`.
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
- `python tools/check_docs.py`: 19 documents and one README example pass.
- `python -m build --no-isolation --outdir output/development`: a8 built.
- `python tools/check_release.py --dist-dir output/development --require-metadata`: passes.
- Installed the a8 wheel, `python -I -m pytest -q`: **232 passed, 1 skipped**.
- `python -I tools/check_installed.py`: seven examples run outside the checkout;
  15 PNGs and one 120-frame video decode, and lessons reload correctly.
- Restored the editable install; `python -m pip check` clean.

### Hosted CI is green — earlier docs were wrong

Both `fd16904` (a5) and `c1fbef1` (a6) passed **all nine jobs**
(Windows/Ubuntu/macOS × CPython 3.12/3.13/3.14). Four documents still claimed
hosted results were pending; corrected this session. M3's last checkbox is done.

**Still unproven: codec availability outside Windows.** CI green did not prove
video encoded on Linux or macOS, because the example degrades gracefully when no
codec exists. `tools/check_installed.py` now **fails** when no video is produced,
so the next push settles it. If a platform turns red, that is the finding — record
it and relax the check deliberately rather than by accident.

### Thai/Arabic reconnaissance (done, positive)

In a throwaway venv outside the project, `pip install "pydrawcv[typography]"`
**installed cleanly on Windows 11 / CPython 3.12** — `pyicu-wheels` ships a
prebuilt binary, so the usual ICU build problem does not arise. With
`FontAsset.from_file(r"C:\Windows\Fonts\tahoma.ttf")`, `สวัสดี` rendered as
correct Thai and `مرحبا` rendered correctly joined and right to left; both were
visually confirmed. The project venv was not modified.

Complication: DrawCV's font path has its own hardcoded whitelist of Latin, Thai
and Arabic and **rejects Greek** (`drawcv/typography/layout.py:209-217`), so the
two paths have complementary coverage and cannot yet be mixed in one string.

Local evidence is Windows 11 x64 and CPython 3.12 unless stated otherwise.

## Next concrete task: Thai and Arabic text

The owner named these as the languages after English, and the reconnaissance
above shows the work is viable rather than speculative.

1. Read AGENTS.md, TEXT.md, then `src/tutordraw/text.py` and `layout.py`.
2. **Decide the font story first**, because everything follows from it: does
   TutorDraw bundle an OFL font (size and licensing commitment), or require the
   caller to supply one? The owner is not deeply technical — recommend rather
   than ask them to choose blind. Not bundling is the conventional answer.
3. Plumb a font through `Theme`/`Tutorial`. **Persistence is the hard part**: a
   lesson file must stay portable across machines, so store a font *name*, not
   an absolute path, and resolve it at load. `PERSISTENCE.md` says external
   assets are out of scope; either honor that or change it deliberately.
4. `layout.py` will need both measurement paths. They are not equivalent:
   `measure()` is font-path only and raises on Hershey, `get_line_metrics()`
   returns different meanings per path, and Hershey hardcodes `line_step = 1.4`
   while the font path honors `line_spacing`. `get_text_bounds_dimensions()` is
   the only call that works on both.
5. Make `pydrawcv[typography]` an **optional** extra. CI must keep testing the
   default install too, or the zero-dependency promise silently rots.
6. Keep the a7 validator: it should route supported-but-shaped scripts to the
   font path when configured, and keep refusing them when it is not.

Thai and Arabic stay next because they are the last **hard blocker**: no
workaround exists, while the other gaps below have one.

Then, in order:

1. **Animate between beats.** `restyle` made motion expressible but it is still
   a jump at the cut. Interpolating a target's move, fill and opacity across a
   step's duration would make `render_at_time` and video export genuinely
   animated. This is the largest remaining change to the timing model and needs
   its contract designed first: today every frame equals some `render_step`
   output, and `tests/test_timing.py` and `tests/test_video.py` rely on that.
2. **Reveal annotations progressively within a step.** Artwork reveal already
   works through `restyle(visible=False)`; labels and callouts still appear all
   at once. Note the caller can approximate this today by adding one step per
   reveal, which is why it ranks below the items with no workaround.
3. **Timed captions.** Lower than it looks: the owner's product supplies its own
   voice and text, so burned-in captions mostly serve exported video.

Publishing a4–a8 to PyPI needs an explicit owner request.

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
> first, then docs/RESTYLE.md, docs/TEXT.md and docs/ROADMAP.md. It is the visual
> engine for a real-time, LLM-driven explainer, not an offline video tool.
> Development a8 has timing, schema-v3 persistence, video export, annotation text
> covering Latin, Greek, Cyrillic, CJK and technical symbols, and per-step
> artwork changes through Step.restyle; 232 tests pass from source and from the
> installed wheel, and hosted CI is green on nine jobs. The next milestone is
> Thai and Arabic via DrawCV's font path — read the reconnaissance in the
> handoff before planning it, and decide the font-bundling question first.
> Preserve existing contracts, keep DrawCV unmodified, record only verified
> results, and do not publish or push without my instruction.

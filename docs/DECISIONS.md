# Design decisions

Recorded 2026-09-20. Distinguish owner requirements from initial design proposals.
Revise proposed choices when implementation evidence warrants it and record why.

| ID | Status | Decision | Reason |
| --- | --- | --- | --- |
| D001 | Owner requirement | Use `pydrawcv` for drawing | Build on the owner's existing drawing library |
| D002 | Owner requirement | Keep improving DrawCV outside this task | TutorDraw has a separate teaching responsibility |
| D003 | Owner requirement | Aim for a Python library distributed through PyPI | Reusable authoring library, not just a demo application |
| D004 | Owner requirement | Maintain documentation for switching AI models | Progress must survive usage limits and lost chat context |
| D005 | Proposed | Use `TutorDraw` / `tutordraw` as working names | Matches the repository; final distribution availability is unverified |
| D006 | Proposed | Wrap/reference DrawCV objects through teaching targets | Supports existing drawings without subclassing every shape |
| D007 | Proposed | Separate reusable annotation definitions from step state | An object can have multiple explanations over a lesson |
| D008 | Proposed | Render independent static steps first | Makes image export and direct step access predictable |
| D009 | Proposed | Render through a working scene copy | Protects source content and avoids accumulated annotation state |
| D010 | Proposed | Start with explicit placement and bounds anchors | Gives a small, testable first version with understandable limits |
| D011 | Proposed | Target Python 3.12+ initially | Matches the inspected local DrawCV requirement |

## Questions for implementation to resolve

1. Which released DrawCV version exposes all required APIs, and what dependency
   range is actually tested?
2. Can a public scene serialization round trip preserve the first release's
   supported objects, IDs, assets, and hierarchy? What needs explicit rejection?
3. ~~Which text APIs provide reliable measurement and wrapping? Is the typography
   extra necessary, and how should missing fonts be reported?~~ Answered in the
   0.1.0a7 section below.
4. Which bounds method is appropriate for labels and highlights, particularly
   with strokes, effects, rotated objects, and groups?
5. Does source object lookup include descendants, or must the adapter traverse?
6. What dimming limits arise from masks, blend modes, and group compositing?

Investigate these locally through source inspection and focused experiments.
They are not reasons to ask the owner to design implementation details.

## Owner choices before public release

- Final spelling and PyPI distribution name.
- License and copyright/author metadata.
- Whether additional output formats or language/font support must be in the first release.

These choices need not block the first executable slice. Do not invent legal
metadata or claim a package name is available without checking.

## M1 implementation decisions — 2026-09-20

- D006–D009 and D011 are implemented: composition, reusable labels, independent
  steps, working copies, and Python 3.12+.
- D010 uses `get_bounds()` anchors, including supported shape strokes but excluding
  post-processing effect extents.
- Pin `pydrawcv==0.10.0.post1` until broader compatibility is tested; M1 uses its
  released wheel, not the local checkout.
- Built-in Hershey labels reject non-printable/non-ASCII text rather than silently
  rendering unsupported characters. Rich text comes later.
- The small model lives in `model.py`; split modules when complexity warrants it.
- Copy through the public document API with a deep-copied dictionary; validate
  preserved IDs/types. Advanced asset compatibility still needs tests.
- `render_step` returns a Canvas; saving uses DrawCV's `save` method. Batch export
  and overwrite safeguards remain M2.


## M2 implementation decisions — 2026-09-20

- Add immutable RGB-tuple themes with validated spacing, font scale, and stroke widths.
- Reuse measured Hershey text, splitting long words when needed; do not depend on rich typography extras yet.
- `Step.explain` returns a step-owned `Callout`; `highlight` and `dim_others` return the step for chaining.
- Repeated highlights replace the same target's outline; repeated dimming calls replace the focus set.
- Preserve focus ancestors and subtrees; dim each maximal unrelated branch once.
- Structural visibility checks use object/ancestor/layer flags and opacity, not pixel-level masks or occlusion.
- Export through temporary PNGs. Refuse collisions by default, including concurrent creations, and report completed files on later failure. Overwrite is explicit and replaces a file only after encoding succeeds.
- Version advances to local alpha 0.1.0a2; publication and naming remain unresolved.


## M3 release decisions — 2026-09-20

- Owner confirmed distribution `tutordraw`, MIT license, and author Nuh Yamin.
- Repository URL comes from configured origin: https://github.com/nuhyamin1/tutordraw.
- Local candidate advances to 0.1.0a3; public upload and version approval are separate.
- Keep the exact tested DrawCV pin; do not claim a broader range without testing it.
- Keep the a2 authoring API unchanged. Clarify theme timing, step-owned callouts,
  source-copy limits, and nontransactional export in the public documentation.
- Test built wheels in CI on Windows/Linux/macOS and CPython 3.12–3.14. Configured
  coverage is not evidence of successful hosted runs; those remain pending.
- Use strict Twine/artifact checks and a metadata-required release gate, with no
  automated upload workflow.


## First public release — 2026-09-20

The owner explicitly authorized PyPI publication and use of a locally saved token.
Uploaded 0.1.0a3 wheel and source archive; PyPI JSON hashes match the approved files.
No credential value was printed or written to this repository. The alpha retains
Windows/CPython 3.12 verification claims; hosted CI remains pending. Future artifact
changes require a new release version. Post-release documentation updates do not
change the immutable uploaded artifacts.


## Persistence priority — development 0.1.0a4

Following the owner's agreement to continue AI-friendly development, implement
complete lesson save/load before timed lessons. Use JSON data with schema version 1,
embedding the DrawCV envelope and stable tutorial identities. Do not pickle or add
an AI-service dependency. Strict TutorDraw field/reference validation prevents
silently lost edits; DrawCV remains responsible for its scene schema.

Immutable annotations can be revised through detached documents; named targets
resolve current source drawables. New step IDs survive persistence. Save defaults
to no overwrite and validates before replacing files. Full undo history, rendered
outputs, external-asset bundling, and schema migrations remain out of scope.

## Bounded timing milestone — development 0.1.0a5

The owner requested useful progress with limited remaining usage and an explicit
Antigravity handoff. Complete the timing foundation; defer video encoding, animated
reveals, and transitions. Each step defaults to 3 seconds plus 0 pause. A pause
holds the same full static image; final pauses count toward lesson duration.
Intervals are [start, end), with the exact final endpoint selecting the last step.
Frames sample k/fps for ceil(total*fps) frames, matching DrawCV timing convention.
No playback history or wall clock is consulted; source animation is not sampled.

Use schema v2 with required duration/pause. Keep v1 schema and load support with
3/0 defaults; always save v2. Strict version/field handling prevents silent loss.
DrawCV VideoRenderer expects an animated Scene, not tutorial frame iterators;
video integration needs a deliberate adapter and collision/failure tests.

## Video export — development 0.1.0a6 (2026-09-21)

Do not reuse DrawCV's `VideoRenderer`. Every entry point is typed `scene: Scene`,
`render_frames` enforces `isinstance(scene, Scene)`, and it drives
`Scene.render_at_time`. A tutorial is not a scene and must not pretend to be one,
and DrawCV exposes no encoder accepting a frame sequence. TutorDraw therefore owns
`video.py`, a small OpenCV writer adapter, and DrawCV stays unmodified.

Call `cv2` directly instead of adding a dependency. `pydrawcv==0.10.0.post1`
requires `opencv-python>=4.8.0` and `numpy` unconditionally, and DrawCV already
writes PNGs with `cv2.imwrite`, so TutorDraw's implicit OpenCV dependency is not
new — only newly visible. `video.py` is the single module importing `cv2`.
Re-check this if the DrawCV pin is ever widened. An ffmpeg backend was considered
and rejected for now: it would add a real dependency for one output format.

Export opaque frames only. `VideoWriter.write` takes three-channel BGR and these
codecs carry no alpha, so `export_video` has no `alpha` option; `export_steps`
remains the transparent-output path.

Open the encoder lazily on the first rendered frame, and size it from that frame
rather than `scene.width`. A rendering failure then never leaves an encoder open,
and a frame whose size changes mid-export fails loudly instead of being written
distorted. Release the writer in a `finally` on every path.

Apply the PNG export safety model to a single file: preflight the destination,
encode into a temporary file carrying the destination's extension (OpenCV selects
the container from it), then `os.replace` when overwriting or create exclusively
otherwise. Unlike PNG batch export this is all-or-nothing, because there is one
output file. Treat a zero-byte result from an encoder that opened successfully as
a failure, since `isOpened()` alone does not prove a codec works.

Codec availability is a host property, not a library guarantee. Report it through
`VideoExportError` with the fourcc, and claim only what was measured locally.

## Character support — development 0.1.0a7 (2026-09-21)

This answers open question 3 above, and settles the "language/font support"
owner choice for the alpha: support what the built-in renderer draws correctly
now, refuse the rest loudly, and treat font rendering as a later milestone.

Replace the printable-ASCII gate. It was simultaneously too strict and
load-bearing: OpenCV already draws Latin-1, Greek, Cyrillic, CJK and the
symbols a science diagram needs, all of which TutorDraw was refusing; but it
substitutes `?` for Thai without raising, and draws Arabic unjoined and left to
right, so simply deleting the gate would have traded a visible limitation for
silent corruption.

Validate with two independent checks, both required. A hardcoded allow list of
Unicode ranges answers "does this script need shaping, reordering or mark
positioning?", and a runtime probe answers "can this OpenCV build actually draw
it?". An allow list, not a block list, so an unrecognised script fails loudly.
A probe, not a table, because glyph coverage varies by OpenCV version and the
dependency floor is 4.8 while this host runs 5.0.

Probe through DrawCV's real rendering path rather than calling `cv2.putText`
directly, so no assumption is made about which Hershey face DrawCV selects.
Cache the results, and skip the probe for ASCII so the common path costs nothing.

Normalize annotation text to NFC at creation. Combining sequences then behave
like their precomposed forms instead of being refused as stray marks, and NFC
is idempotent so saved lessons still round trip.

Error messages name the character, its codepoint, and the fix, and distinguish
"unsupported script" from "this build cannot draw it". This is a product
requirement, not politeness: a model generating lesson text at runtime is a
first-class caller and must be able to act on the failure.

Keep those messages pure ASCII, using `ascii(char)` rather than `repr(char)`.
A legacy Windows console raises UnicodeEncodeError when printing the offending
character, so the message would hide the error it exists to report. The U+XXXX
code carries the identity instead, and a test enforces the property.

Defer Thai and Arabic to their own milestone. They need
`pip install "pydrawcv[typography]"` plus a caller-supplied font file, and a
decision about whether TutorDraw ships a font. Reconnaissance in a throwaway
environment confirmed the extra installs cleanly on Windows and that Thai and
Arabic then render correctly, so the milestone is viable rather than
speculative. Note DrawCV's font path rejects Greek, so the two paths have
complementary coverage and cannot yet be mixed in one string.

## Per-step artwork changes — development 0.1.0a8 (2026-09-21)

Trying to build the owner's own example, "explain a lunar eclipse", exposed the
real limit: a lesson was one fixed drawing with annotations on top. The
narration could say "the Moon turns red" while the Moon stayed grey, because a
step could point at artwork but never change it. For a live explainer that is
the difference between showing something happen and describing it.

The obvious workaround is editing `target.drawable` between renders. It was
tested and rejected: every render reads the current source, so an edit is
retroactive and silently changes steps already rendered. A saved lesson could
not have a grey Moon in beat one and a red Moon in beat four.

Add `Step.restyle`, applied to the working copy each render already makes. That
keeps step independence, keeps the source untouched, and needs no new rendering
machinery. Apply restyles **before** labels, highlights and dimming are
computed, so annotations attached to a moved target follow it for free; a test
asserts this equals moving the source object by the same amount.

One method rather than separate `move`/`recolor`/`hide` verbs, with repetition
replacing the whole record, matching `highlight`'s existing contract. Named
`restyle` even though it also moves, because it is short, verb-first, and
`move=` is visible in the signature. Scope is move, fill, opacity and visible;
stroke, scale and rotation are deferred rather than guessed at.

`move` is a delta, not an absolute position, because DrawCV objects carry a
transform whose translation is separate from the shape's own coordinates. A
delta composes with whatever the source already does; an absolute would have to
pick one of those meanings and would surprise either way.

`opacity` is absolute while `dim_others` keeps multiplying. Dimming is described
everywhere as a multiplier over authored opacity, so a restyled value is simply
the new authored value. The two compose predictably instead of one overriding
the other.

Bump to schema v3 with `restyles` required on each step, following the v2
precedent for timing. v1 and v2 load without restyles and saving always writes
v3, so older readers reject new files rather than silently dropping content.

## Thai and Arabic — development 0.1.0a9 (2026-09-21)

The owner named English, Thai and Arabic as the target languages, and DrawCV's
font engine happens to support exactly Latin, Thai and Arabic. Support them.

**Optional, not required.** `pip install "tutordraw[typography]"` pulls
`pydrawcv[typography]`: five native packages including uharfbuzz and ICU. A
default install stays at one dependency, and the built-in renderer keeps
covering Latin, Greek, Cyrillic, CJK and symbols. Reconnaissance had already
shown the extra installs cleanly on Windows because `pyicu-wheels` ships a
prebuilt binary.

**TutorDraw ships no font; the caller supplies one.** Bundling an OFL font would
add megabytes to every wheel for a feature most lessons will not use, and one
font never covers every script anyway. `Tutorial(font=...)` takes a path, bytes
or a `FontAsset`. The owner deferred this choice, so it is recorded here as the
conventional answer rather than a preference.

**Choose the renderer per annotation, not per lesson.** The two paths have
complementary gaps: the font engine rejects Greek, Cyrillic and CJK, while the
built-in renderer cannot shape Thai or Arabic. A per-lesson switch would mean
turning on a font silently broke Greek. Per annotation, a lesson can carry a
Thai callout and a Greek label at once. A configured font is still used for
everything it can draw, so lessons keep one typeface wherever possible. One
annotation mixing both sides cannot be drawn by either path and raises, naming
the fix.

**Do not persist the font.** A lesson file would have to hold either a
machine-specific path or an embedded megabyte of font data; PERSISTENCE.md
already rules external assets out of scope. The text itself declares the need,
so loading without a font raises `LessonFormatError` naming the first character
that requires one. No schema change, and a lesson can never silently lose its
script.

**Segment Thai for line breaking.** TutorDraw wraps text itself rather than
delegating to DrawCV, so Thai was breaking mid-syllable. `pythainlp` arrives
with the extra; use it to find break opportunities, guarded so its absence
falls back to whitespace splitting. Right-to-left wrapped lines are aligned to
the panel's right edge, which plain left alignment got visibly wrong.

Font size is derived as `font_scale * 24`, measured to match the built-in
renderer's height on this DrawCV release. A `Theme` field would have been
nicer, but `Theme` is persisted field-by-field with a strict key check, so
adding one breaks every existing lesson file. Not worth a schema bump.

## Animating between beats — development 0.1.0a10 (2026-09-21)

`restyle` made change expressible but motion was a jump. Animation is the
remaining gap for a live explainer, and it is the first feature that touches
the timing contract, so the contract decisions matter more than the code.

**Opt in per step.** Every frame currently equals some `render_step` output,
and `test_timing.py` and `test_video.py` both depend on it. Animating by
default would silently change every existing lesson and break that identity
everywhere. `step.animate()` relaxes it only where asked; hard cuts stay the
default and untouched lessons render exactly as before.

**`render_step` keeps meaning the finished state.** Static PNG export should
still read as the lesson's beats, and an author reasoning about "what does
step 3 look like" wants the destination. Only `render_at_time` interpolates.

**Animate from the previous step's state, not from a declared start.** A
restyle is already expressed relative to the source, so the previous step's
restyle is the natural starting point and needs no new data. It also gives the
right behavior for free in two cases: a step repeating the previous move stays
put, and a target the next step ignores slides home.

**Reuse DrawCV's easing curves** rather than writing any. It exports
`get_easing` and 25 named curves with their own validation, so TutorDraw adds a
name check and nothing else. Names are canonicalised to lowercase because
DrawCV matches case-insensitively and a lesson file should have one spelling.

**Do not interpolate `visible`.** A boolean has no midpoint. The step's own
value applies throughout it, and authors pair it with `opacity` to fade.
Interpolate `fill` in plain RGB: predictable and easy to explain, even though
it is not perceptually even. Both are documented rather than hidden.

Schema v4 adds a nullable easing string per step. That is the third bump in a
day; each is honest and older versions still load, but the alpha is moving
fast and PERSISTENCE.md says so.

An expected cost turned out not to exist: animated frames measured the same as
static ones, about 35 ms, because every frame was always rendered from scratch.
Animation removes a caching opportunity that was never taken, rather than
adding work. Recorded with numbers in ANIMATION.md instead of guessed at.

## Revealing annotations — development 0.1.0a11 (2026-09-21)

Every label and callout in a step appeared at once, which is wrong for a
narrated lesson. The caller could already approximate reveals by adding a step
per reveal, so the bar here was convenience, not capability, and the design is
deliberately small.

**Extend `show` and `explain` with `at=` rather than adding a concept.** Both
methods already exist and already mean "this annotation belongs to this step";
a delay is one more attribute of that, not a new kind of thing. No new class,
no new verb.

**Seconds from the start of the step, not an ordering index or a stagger.**
The product drives narration from a language model that knows when each
sentence will be spoken, so an explicit time is directly usable. An index or a
stagger would force the caller to convert.

**A delay alone makes the step time-varying.** Requiring `animate()` as well
would be an unrelated coupling. This generalised the render path: easing moved
inside `_render`, which now takes raw progress, derives elapsed seconds for
reveals and applies the curve only to artwork blending.

**`render_step` keeps showing everything**, matching the decision made for
animation. Still export stays a picture of the beat, not of one instant in it.

**Clamp a delay past the duration to the end** rather than rejecting it or
letting it never appear. Rejecting would couple validation to `duration` and
let a later `set_timing` strand an annotation; never appearing would make
playback and `render_step` disagree. Clamping keeps them consistent with no
cross-field validation.

**Appear, do not fade.** A fade would mean inventing a duration, and a caption
landing as the narrator says it is the actual requirement. Recorded as a
deliberate omission rather than an oversight.

Schema v5 adds a per-step map of annotation id to seconds. That is the fourth
bump in a day, so the tests were changed to derive the version from
`SCHEMA_VERSION` and a single `STEP_FIELDS_ADDED` table in `tests/conftest.py`.
A future bump now updates one table instead of five test files, and one
parametrised test covers every older version. The churn itself remains a
reason to let the format settle before publishing.

## Second public release — 0.1.0a11 (2026-09-21)

The owner explicitly authorised publication. TutorDraw does not upload on its
own initiative, and the upload itself was run by the owner because it needs a
PyPI API token; no credential was handled or stored by the assistant, and none
is configured in this checkout.

Released as `a11` rather than a new minor or a beta. It is a large step from
a3 — persistence, timing, video, non-ASCII text, per-step artwork, animation,
reveals, optional Thai and Arabic — but the API is still alpha and still
moving, so the number should not imply otherwise. The changelog and README say
plainly that a4 through a10 were development milestones and were never
uploaded, rather than leaving the jump unexplained.

Published artifact SHA256, verified against the local build after upload:

- Wheel: 946c9dfa859ce224677773aaca0e74a4356b6ea2b4e9efc22e0f4b024d7cb20f
- Sdist: 8027375a9605a5b3c375e4039fa0d590721c2c80979d5e0dcc0bee1fb0537ce7

Post-release verification installed `tutordraw==0.1.0a11` from PyPI into a
clean virtual environment with no extras, ran all eight examples, decoded
16 PNGs and a 120-frame video, and reloaded a saved lesson. The multilingual
example correctly fell back to English with the install instruction, which is
the graceful-degradation path fixed earlier the same day. Installing
`tutordraw[typography]` from PyPI then produced all three languages.

Known and accepted at release: the lesson format moved v2 to v5 in one day,
and published schema versions become other people's files. Older versions all
load, but the format should now settle. macOS installation of the typography
extra remains unverified.

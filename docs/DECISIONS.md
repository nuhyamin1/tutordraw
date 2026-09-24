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
  released wheel, not the local checkout. Superseded in 0.1.0a12 by an exact
  `pydrawcv==0.11.0` pin; see "DrawCV 0.11.0" below.
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

## Automatic collision avoidance — development 0.1.0a12 (2026-09-23)

The owner reported six label panels landing on top of one another in a real
lesson. `label_artwork` computed one panel from one target with no knowledge of
any other, and `_render` called it once per annotation, so nothing shared state.

**Ranked candidate placements, not a force relaxation.** A force-based
push-apart gives every panel a position that depends on every other panel's, so
an animated step drifts every frame. A discrete candidate list is stable: a
panel only moves when a ranking actually flips, and the ordering itself encodes
author intent. Rank 0 is exactly what the author wrote; alternatives try the
other sides of the target, then slide along a side, then step further out.

Candidates score lexicographically on `(overlap + off-canvas area, artwork
coverage, rank)` rather than on tuned weights. Panel-on-panel and off-canvas
share a tier because both are unreadable and a small sliver of either should
not lose to a large amount of the other. Covering artwork is a lower tier
because the owner asked for it "where avoidable". Rank breaks ties, so the
authored placement wins whenever it is free, and resolution short-circuits on
the first free candidate — which is the common case.

**Greedy in registration order.** An earlier annotation is never displaced by a
later one, which makes the result deterministic without inventing a priority
heuristic, and matches the order `_render` already iterated.

**The decision is taken once per render, not once per frame.** This was the
hard constraint: `_render` runs at every timeline position and `restyle` moves
targets during a step, so a naive per-frame solver jitters or swaps sides
mid-animation. Resolution runs against the state the step *ends* in and returns
an anchor plus a pixel nudge; the panel itself is still built from live bounds
each frame. The discrete choice is therefore frame-invariant while the panel
still tracks its target, which keeps RESTYLE.md's promise that a moved target
takes its label, leader and highlight with it, pixel-identically.

End-state resolution alone proved insufficient: a target sliding *past* another
label drags its panel through it in the middle while both ends are clear
(measured at 4148 px² of overlap before the fix). An animated step is therefore
resolved over the **swept union** of each panel between the step's two ends. The
union of two axis-aligned boxes contains the whole translation sweep, so this is
conservative and cannot leave a mid-flight overlap. A hard cut has no middle and
is resolved against its end state alone, so it is not penalised for motion it
never shows. `_render` passes the planner the real previous step even at
progress 1, so the final frame and `render_step` plan identically.

Reveal delays are ignored when resolving: every annotation holds its slot from
the first frame. A slot then sits empty until its annotation appears, which is
accepted in exchange for nothing on screen moving when one does.

Canvas clamping is re-applied per frame rather than frozen with the placement.
It is continuous, so a panel tracking a moving target slides along the edge
instead of jumping, and an authored offset chosen against different bounds
cannot defeat it. This is the one behaviour change to an existing test:
`test_off_canvas_warning` authored an offset past the edge and asserted
`LayoutWarning`; avoidance now pulls it back, so that test pins the legacy path
with `Theme(avoid_collisions=False)` and new tests cover both recoverable and
unrecoverable cases.

**On by default**, on the owner's decision. Output only changes where panels
genuinely overlapped, which is where it was already wrong, and a fix that must
be opted into would not fix the lesson that prompted it.
`Theme(avoid_collisions=False)` restores verbatim placement exactly.

The option lives on `Theme` rather than a `Tutorial` argument or a render-time
flag because it must round-trip with a saved lesson and `Theme` already carries
layout numbers. That costs schema v6; older documents omit the two fields and
take the defaults, mirroring how older step fields are handled.

Measured cost: none worth naming. The resolver short-circuits, and reusing its
measurements in `label_artwork` removes a second text-measurement pass, so the
reported six-label lesson renders *faster* with avoidance on (23 ms vs 42 ms).
A 90-frame animated export is 1.03x.

Routed leader lines remain deferred. Leaders stay straight and re-aim from the
moved panel, which the existing panel-edge intersection already handled.

### Labels without a panel — schema v7

The owner asked whether a label could be drawn as bare text. It could not: the
panel `Rectangle` was unconditional, and the theme could not fake its absence,
because `panel_color` takes no alpha and `border_width` must be positive. A
background-coloured panel is still opaque and cuts a hole through any artwork
behind it, so there was no workaround at all on a non-flat background.

Added as a per-label `box=True`, mirroring `leader`, rather than a `Theme`
field: it is annotation-level styling, and a lesson will usually want most
labels boxed with a few bare. A lesson-wide default can be added later without
breaking this. The panel is still **measured** when it is not drawn, so an
unboxed label lands exactly where a boxed one would, the leader still terminates
on the panel edge, and collision avoidance still keeps bare text clear — which
matters more without a panel to separate it from the artwork, not less.

The cost is schema v7, the third format move in four days, taken on the owner's
explicit decision after the cost was stated. `ANNOTATION_FIELDS` is an exact key
set, so any per-label option needs a bump; the `*_FIELDS_ADDED` tables now cover
step, theme and annotation fields alike, and one parameterised test still covers
every older version.

### Gradient fills could not be recoloured (same session, independent)

`restyle(fill=...)` on a gradient-filled object raised `ValidationError:
Gradient and image fills have no single color`. `current_fill` read
`FillStyle.color`, the solid-colour shorthand that raises for gradients and
image paints, and `_blend` calls it whenever either side sets a fill — so it
fired at progress 1.0 too, animated or not.

Fixed at the root: read `fill.paint` and reduce it. A gradient reports the
unweighted mean of its stop colours, which is simple and predictable like the
plain-RGB interpolation it feeds, rather than position-weighted. An image paint
has no stops and reports None, which `_blend` already handles by cutting to the
new colour instead of interpolating. Sampling a gradient at a point, or
interpolating a gradient into another gradient, is out of scope.

## DrawCV 0.11.0 — development 0.1.0a12 (2026-09-24)

Moved the exact pin from `pydrawcv==0.10.0.post1` to `pydrawcv==0.11.0` after
the full suite passed unchanged against the published wheel. Still exact, not a
range: 0.11.0 changed rendering, so a range would promise pixels we have not seen.

0.11.0 rasterizes with area-exact coverage on the SVG pixel grid. Strokes are
now their true width, so every annotation is thinner, and a 1 px panel border
on a whole coordinate became two half-tone pixels with no pixel in the border
colour — visibly soft. **Kept the theme widths** and instead snap stroked panel
and highlight rectangles in the adapter (`crisp_rect`): odd integer widths are
centred on `.5`, even ones on whole coordinates. Edges snap **inward** (under a
pixel each), never outward: the first version rounded to nearest and pushed the
right border of a panel clamped flush with the canvas to `1100.5`, off screen.
Inward snapping also keeps the drawn border inside the footprint collision
avoidance measured. Thicker defaults would have changed every lesson's look to paper over a
grid-alignment problem. Only the drawn rectangle is snapped; measurement,
collision placement and text positions are untouched. An animated panel's border
therefore steps by whole pixels while its text moves smoothly — under a pixel
of relative drift, the same trade browsers make for borders. Leader lines
are diagonal in general and are not snapped.

Not adopted: DrawCV's new shape `Label`. TutorDraw labels carry per-step state,
leaders, panels and collision placement that a shape label does not. `paint_order`
could give bare-text labels a legibility halo on busy artwork; that is a feature
for later, not part of the upgrade.

Lesson files now embed DrawCV scene schema 1.14, which 0.10.x cannot read, so a
lesson saved by a12 does not open under a11. Older lessons load unchanged. The
exact pin makes this a release-note item rather than a bug.

Found by the installed-wheel gate in the same session: `tutordraw.__version__`
still read `0.1.0a11` while `pyproject.toml` said `0.1.0a12`, so
`tools/check_installed.py` failed. Fixed in `__init__.py`.

## Golden regression tests — development 0.1.0a12 (2026-09-24)

First milestone of the owner-approved explainer program (ROADMAP "P1"–"P5").
Format-neutral work goes first and every new visual lands in a single schema
v8, because the format already moved v2 -> v7 in four days.

`Tutorial._render` is now `_compose` + rasterize. `_compose` returns a
`Composition`: the working scene plus each drawn annotation's panel, leader,
side and each highlight's box. Behaviour is unchanged (the suite passed before
references existed). Lint and SVG export need exactly this, and golden tests
need it now. It stays private until P2 names the public API.

Each golden frame is checked twice. Geometry to 0.05 px is platform-neutral and
names what moved (`annotations[1].panel[0]: 401.5 != 402.5`). Pixels use a
tolerance — a channel moving more than 24, on more than 0.02% of the frame —
to absorb antialiasing noise while still failing on a 1 px panel shift (~800
pixels). The canonical lessons live in `tests/`, not `examples/`, so examples
can be simplified without churning references. They use built-in text only.
The references pin current behaviour including known flaws (a leader crossing
in cell step 3, an unclearable label in motion-end); P2's lint should flag
those rather than the references hiding them.

## lint() and layout() — development 0.1.0a12 (2026-09-24), program P2

`Tutorial.layout` exposes the P1 `Composition` publicly; `Tutorial.lint` reads
it and never changes rendering (a test asserts pixels and the source scene are
identical after linting, and that no warning escapes).

- **Real shapes, not bounds.** Bounding boxes made every panel near a round
  target "cover" it. Coverage and leader-over-target use DrawCV
  `contains_point`, sampled every 3 px (panels) / 2 px (leaders). Linting a
  golden lesson costs 4–70 ms.
- A leader is not "crossing" a target that contains its start point — a
  nucleus leader necessarily runs across the cell it sits in.
- Contrast for boxed text is theme text vs panel; for `box=False` it renders
  the step once without annotations and uses the *worst tenth* of the pixels
  under the text, because the mean hides a dark stripe.
- `UNPLACEABLE` comes from the resolver's own LayoutWarning, captured, so lint
  and rendering cannot disagree about it.
- Errors are only states that are wrong regardless of taste (off canvas,
  overlapping panels); readability judgements are warnings; style is info.
- Finished state only. Mid-animation frames are the collision resolver's job;
  linting them is a roadmap item, not a promise.
- Checked against the golden lessons by eye: all flagged cases are visible in
  the references, and the three clean lessons report nothing. Each rule was
  mutation-tested (disabling it fails a test).

## Visual vocabulary and schema v8 — design (2026-09-24), program P3

One format bump for all eight P3 items, designed together. Evidence gathered
first: DrawCV slices `Line`, `Arc`, `Arrow`, `Bezier`, `Path`, `Polyline` by
`render_progress`; `Transform` scales about `pivot` (None = the object's own
centre, so a camera must pin `Point(0, 0)`); `Path.offset` grows a closed
region; `Text` has **no stroke**, so `paint_order` cannot make a text halo.

**Timing model shared by everything new.** Anything that appears can take
`at=` (seconds into the step, as reveals already do) and `draw=True`. With
`draw`, its strokes draw on over `Theme.draw_seconds` (0.6) starting at `at`,
through DrawCV `render_progress`; its text and panel appear when the stroke
completes. At the end of the step everything is complete, so `render_step`
is unchanged by timing — static steps stay independent and exact.

**Marks: one list, a `kind` discriminator.** New step-owned annotations are
`Mark`s persisted in `step["marks"]` as `{id, kind, refs, text, options}`, so a
later version adds kinds without new top-level fields. A ref is
`{"target_id"}` or `{"point": [x, y]}` (a fixed scene coordinate).
- `step.connect(a, b, text=None, *, bend=0, both=False)` — kind `arrow`, a
  curved or straight arrow between two targets' bounds.
- `step.brace(*targets, text=None, side="bottom")` — kind `brace`.
- `step.measure(a, b=None, text=None, *, axis="x", offset=24)` — kind
  `measure`: one target's extent, or the distance between two refs.
- `step.angle(vertex, a, b, text=None, *, radius=32)` — kind `angle`.
- `step.number(target, n=None, *, corner="top_left")` — kind `number`; `n`
  defaults to the next number in the step. Appears whole: `draw` is refused.
Mark geometry is a pure function of target bounds, so the planner evaluates it
at the step's end state and treats it as a blocker for label placement, and
rendering evaluates it on live bounds. Marks use `leader_color`/`leader_width`;
their text uses the normal panel style.

**Highlights** gain `shape="outline"` (the target's own path, offset outward by
`padding` via `to_path` + `Path.offset`; refused at authoring time for shapes
that cannot convert or are open), plus `at=` and `draw=`.

**Camera.** `step.zoom_to(*targets, padding=40, max_scale=4)` fits the targets'
end-state bounds to the canvas; `step.reset_camera()` clears it. Steps stay
independent: no zoom means the full canvas, never "the previous step's". On
an animated step the camera interpolates from the previous step's framing
(centre linearly, scale geometrically). Implementation wraps each layer's
top-level artwork in a camera `Group` inside the working copy, so dimming and
nested groups keep working, and annotations stay screen-space — text never
grows with zoom. The planner evaluates placement with the camera at the step's
end (and start, for the sweep) so labels do not jitter during a zoom.

**Halo.** `box=False` text gets a halo of `Theme.halo_width` (3; 0 disables)
in `panel_color`, drawn as offset copies beneath the text. This changes the
rendering of bare labels, deliberately: bare text over artwork is the case
lint's LOW_CONTRAST flags, and lint now measures against the halo.

**Schema v8** adds step `marks`, `draw` (list of annotation/mark IDs),
`camera`; highlight `at`, `draw`, `shape`; theme `draw_seconds`, `halo_width`.
v1–v7 load with defaults. Lint learns marks (off-canvas, overlap with panels,
busy count).

### P3 implementation notes (2026-09-24)

- **Outline growth is TutorDraw's, not `Path.offset`.** On DrawCV 0.11.0,
  `Path.offset` took 0.7–2.4 s for one circle: it maps every point through
  `to_world`, which recomputes the path's bounds each time. `flatten_world`
  takes ~2 ms, so `adapters.drawcv.outline_path` flattens the world outline
  and offsets each contour itself (round convex corners, mitred concave ones,
  per-contour winding so holes grow correctly). Checked by eye on a circle,
  rectangle, sharp triangle, concave notch and rotated ellipse. Worth
  reporting upstream; not worked around in DrawCV.
- **`connect` takes points at either end** (not both). Found by building the
  lever example: a force arrow on one object had no honest spelling with
  targets only. The format already allowed point refs, so v8 is unchanged.
- **Arrow captions lift by the panel's half-extent along the normal**, not its
  half-height, or a vertical arrow's caption sits across the shaft.
- **`free` measures honour `offset`**, lifted toward the top of the screen with
  extension lines, or the line sits on the edge it measures.
- **Lint ignores areas under 1 px².** `outside_area` of a panel clamped flush
  to the edge returned 7e-12 and raised a false OFF_CANVAS on the lever lesson.
- Mark captions are obstacles for label placement but are not themselves
  moved; lint reports their collisions. Automatic mark placement is roadmap.
- Old golden references were untouched by P3 except `bare-step1` (the halo,
  intended and inspected). Eleven new frames pin marks, camera and draw-on.

## Browser playback — development 0.1.0a12 (2026-09-24), program P4

Evidence first. DrawCV 0.11.0's SVG export already slices `render_progress`
strokes and tags every element `data-drawcv-id`, but it writes built-in text as
embedded PNGs (137 KB and 600 ms for the bare golden frame, blurry when
scaled) and bakes the camera into world coordinates (a zoomed camera group has
no transform attribute). That shaped every choice:

- **Native text, placed in world space.** TutorDraw swaps each built-in text
  for an empty placeholder with the same ID *in the same draw position*
  (`replace_in_place`, public add/remove only), exports, then fills the group
  with `<text>`: world bounds, font size = font_scale x 28.7 x world scale
  (measured: baseline at 79.5% of the line box, cap height 20.1 px per unit
  scale), and `textLength` = TutorDraw's measured width so it always fits its
  panel. Swapping before export instead of replacing after it cut web_step
  8-10x (2.4 s -> 290 ms): DrawCV spent ~40 ms rasterising each text. Rotated
  or skewed text keeps DrawCV's raster. The first version placed text in
  parent space; the browser showed the title un-zoomed mid-zoom, which is how
  the baked camera was found.
- **Stable IDs** `td-<owner>-<role>` on everything TutorDraw draws, so the
  player can match elements across frames and read timing from the role.
- **Start and end frames, not a flipbook.** Per-frame SVG at 12 fps would be
  ~36 exports per 3 s animation. Restyles blend linearly in eased time, so one
  start frame plus DrawCV's easing sampled at 65 points is exact. A camera
  zooms geometrically, which linear coordinate blending does not reproduce
  (scale 1.6 vs 1.5 mid-zoom, measured), so a camera change sends 6 evenly
  timed keyframes with easing applied and the player blends neighbours.
- **The player tweens generically**: any attribute whose non-numeric skeleton
  matches across frames has its numbers interpolated. No per-shape logic.
- **Native size + CSS transform scaling**: DrawCV strokes are
  `non-scaling-stroke`, so viewBox scaling fattened every line on a small
  screen; a CSS transform on the wrapper keeps PNG proportions (compared by eye).
- **Self-contained HTML** with the bundle as inline JSON; `</` is escaped (a
  test fails without it) and placeholders are filled in one regex pass so a
  title containing `@DATA@` cannot inject.
- Streaming is transport-agnostic: `web_step` is plain JSON and the player's
  `append` works mid-playback, holding on the last frame until the next step.

## Step descriptions — development 0.1.0a12 (2026-09-24), program P5

`Tutorial.describe` builds sentences only from structure: targets, annotations,
marks, restyles, camera, dimming. No pixel analysis, so it is deterministic,
cheap and never wrong about what was authored.

- **Changes are relative to the previous step.** The first version described
  restyles against the source drawing; on the eclipse lesson it missed "the
  umbra appears" in beat 2 and claimed the Moon slid again in beat 4, when it
  had not moved since beat 3. Viewers see step-to-step changes, so that is
  what is described, including going "back" to the drawing's state.
- Reveal order, not authoring order, with "Then" for later reveals: it reads
  like the narration it should match.
- Colours use 18 everyday names by weighted RGB distance. A name is the point
  ("turns red"), not a measurement.
- Found while wiring it into the page: descriptions repeat lesson text, which
  exposed that the inline JSON escaped only `</`. `<!--` followed by `<script`
  changes how an HTML parser looks for the end of a script block, so `<`, `>`
  and `&` are now escaped as JSON `\u` sequences; the test text includes
  `<!--<script`.

## Narration timing — development 0.1.0a12 (2026-09-24), program P5

`Step.narrate(words, cues)` maps each on-screen item to the phrase that
introduces it and sets its existing `at=` from the word timings. Cues by
phrase, not by word index: an LLM writes the narration and the picture
together and knows which words introduce which thing, but not what a TTS
engine will do to the timing.

- **Format-neutral on purpose.** Reveal times and durations already persist
  in v8, so narrate needs no format change. The words themselves (captions)
  are kept in memory and sent in `web_step`, but not saved; saving them waits
  for the next format bump rather than forcing v9 now for one field.
- Phrase matching is case-, accent- and punctuation-insensitive and skips
  punctuation-only tokens (a spoken "—"), first occurrence wins. Every cue is
  resolved before anything is changed.
- `lead` 0.15 s: the picture should land with the word, and a reveal that
  trails speech reads as lag.
- Found while testing: `connect()` between concentric targets gave a
  zero-length path, and DrawCV's tangent raised, failing the whole frame. Such
  an arrow now draws nothing and lint reports EMPTY_MARK.

## Teaching kits — development 0.1.0a12 (2026-09-24), program P5

Owner question answered before building: kits do **not** draw. They compute
geometry (ticks, coordinate mapping, sampling) and add ordinary DrawCV objects
to the scene, registering the parts as targets. That keeps rendering in DrawCV
and needs no DrawCV change. General-purpose charting could later move into
DrawCV with kits as thin wrappers; not now, since DrawCV is out of scope here.

- Settings live in the kit group's DrawCV `metadata`, so a saved lesson keeps
  them with no TutorDraw format change and `Axes.find` can reattach.
- The whole axes group is **not** a target: its bounds are the whole plot and
  would block every label. The two axis lines are.
- Curves split where f fails or is non-finite and are cut exactly at the y
  range edge by interpolation, so 1/x shows two branches and nothing is drawn
  outside the box.
- Tick step: the 1/2/5 x 10^n step whose tick count is closest to 8 on a log
  scale. A first version that took the first step at least the raw span / 8
  gave 5 ticks for a span of 10.
- **Planner obstacles changed for every lesson**, found by building the graph:
  a parabola's bounding box covered the whole plot and pushed labels away from
  it. Unfilled strokes now contribute boxes every 24 px along their ink
  (long straight segments subdivided, or a diagonal is one big box again).
  Text in the drawing is a soft obstacle, after a vertex note covered the
  "-1" tick label. No golden frame changed: existing lessons were already
  clear of both. A moving stroke keeps its swept bounds.
- `describe()` stays silent about targets hidden from step one (the viewer
  never saw them) and agrees verbs with plural names, both found on the graph
  example ("The guides is hidden").
- **Performance: pin the pivot of generated artwork.** The first graph took
  7.5 s to render, 2.1 s to export as SVG and 11 s to lint. Cause, in DrawCV
  0.11.0: a Transform with the default pivot (None = the object's own centre)
  re-measures the object's bounds on every world-space mapping, so a group of
  curves or a 240-point path cost O(points squared) in rendering, SVG export
  and `contains_point` (which also re-flattens the path per call). The kit
  group, kit paths and mark paths now carry `fixed_pivot()` (identity, pivot at
  the origin, visually identical: every golden frame unchanged), and lint judges
  unfilled strokes by their ink boxes instead of `contains_point`. Result:
  155 ms render, 115 ms SVG, 327 ms lint. User artwork still has DrawCV's
  default pivots; worth reporting upstream. Guarded by a structural test.

### Number line kit (same session)

- **Hops are step marks, not drawing.** The first version drew a hop as kit
  artwork. The example showed why that is wrong: artwork sits in every step,
  cannot draw on or be a narration cue, and "drawing it on" with a highlight
  boxed the arc. `line.hop(step, a, b)` now calls `step.connect` between
  invisible anchor targets named `<line>_at_<value>`, which also makes the
  description read "from the number line at 2 to the number line at 5".
- A long hop's arc grew with its length and reached the next line in the
  golden frame; the peak is now capped at 45 px by choosing the bend from the
  hop's length.
- `connect` still needs at least one target at an end: anchors are what give
  hops readable descriptions, so two-point arrows stay refused.

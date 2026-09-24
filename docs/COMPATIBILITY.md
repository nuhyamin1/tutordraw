# Compatibility and limitations

## Evidence versus intended coverage

| Environment | Status |
| --- | --- |
| Windows x64, CPython 3.12 | Locally tested: unit tests, examples, wheel install, PNG rendering |
| Windows, Ubuntu, macOS; CPython 3.12, 3.13, 3.14 | Hosted CI: all nine jobs green on cb8f2d6 |
| Other Python implementations, architectures, or versions | Not verified |

`requires-python >=3.12` is an installation constraint, not a claim that every
future interpreter or platform has been tested. Native NumPy/OpenCV/skia-pathops
dependencies must have compatible builds for the environment.

## DrawCV dependency

The supported dependency is exactly **`pydrawcv==0.11.0`**. Runtime tests use
the published wheel, not `C:/Projects/DrawCV`. Keep this narrow until release
tests establish a larger range. Users import it as `drawcv`.

TutorDraw references DrawCV objects by stable IDs and copies scenes through their
public serialization API. Basic shapes, text, nested groups, styles, and transforms
are exercised locally. This is not a guarantee of all custom objects, external
assets, vector masks, effects, or blend-mode combinations. Unsupported scene
copying raises `SceneCopyError` instead of editing the source in place.

## Optional math extra

`pip install "tutordraw[math]"` adds `ziamath>=0.13,<0.14` for
`tutordraw.kits.Equation`. Tested with ziamath 0.13, ziafont 0.11 and
latex2mathml 3.81.1 on Linux CPython 3.12 locally, and in hosted CI through the
`dev` extra. All three are pure Python and MIT licensed. Equations are saved as
ordinary DrawCV paths, so a saved lesson opens and renders without the extra;
only typesetting new equations needs it.

**Lesson files and DrawCV versions.** A saved lesson embeds its DrawCV scene.
DrawCV 0.11.0 writes scene schema 1.14 and reads every older one, so lessons saved
by 0.1.0a11 and earlier still load. DrawCV 0.10.x cannot read schema 1.14, so a
lesson saved by 0.1.0a12 or later does not open under 0.1.0a11 or earlier.

**Rendering changed in 0.11.0.** DrawCV now antialiases with area-exact coverage
on the SVG pixel grid (pixel `k` spans `[k, k + 1]`). Strokes are drawn at their
true width, so annotations look thinner than under 0.10, and shapes shift by half
a pixel. TutorDraw snaps panel borders and highlight rectangles inward so their
strokes land on whole pixels (`crisp_rect` in the adapter); leader lines and user artwork
are drawn as authored.

## Text and layout

- Built-in text: Latin, Greek, Cyrillic, CJK and common symbols; newlines in callouts.
- No extra font assets or typography dependencies are required for annotations.
- Character support is probed against the installed OpenCV rather than assumed,
  so it widens automatically on builds with broader glyph coverage.
- Thai and Arabic need `pip install "tutordraw[typography]"` plus a font file you
  supply; TutorDraw bundles none. Verified on Windows 11 / CPython 3.12 with
  Tahoma. Other hosts are untested, and the test suite skips when no covering
  font is found.
- Hebrew, Indic scripts, emoji, rich text and equations are refused with a
  `ValidationError` naming the character; DrawCV's font engine accepts Latin,
  Thai and Arabic only. See [TEXT.md](TEXT.md).
- Bounds anchors use transformed axis-aligned bounds, not exact shape outlines.
- Callouts wrap and split long words; a character that cannot fit raises an error.
- Authors control placement. No automatic overlap avoidance or leader routing.
- Off-canvas warnings are actionable; clipped output can still be produced.

## Rendering and export

Rendering takes the current authored scene state, without sampling a timeline.
Concurrent source mutation is unsupported. Dimming reduces branch opacity, not
the background, and does not infer visibility through masks or occlusion.

Video export calls `cv2.VideoWriter` directly. OpenCV is an unconditional
requirement of `pydrawcv`, so no extra install is needed, but **codec and
container availability depends on the host and the installed OpenCV wheel** and
is not something this library can promise. Verified on Windows 11 x64, CPython
3.12, `opencv-python` 5.0.0.93: `mp4v`/`.mp4`, `MJPG`/`.avi`, `XVID`/`.avi`
encode and decode. `avc1` opened only after OpenCV reported it could not load
`openh264`, so H.264 is not claimed. No other platform, Python version, or
OpenCV build has been tested individually, but hosted CI proves that at least
one of the three encodes and decodes on all nine supported environments. An
unavailable codec raises `VideoExportError`. Encoding is lossy: decoded frames approximate
`render_step` output rather than matching it exactly. See [VIDEO.md](VIDEO.md).

PNG export is not an all-or-nothing batch transaction. Completed files survive a
later failure and are reported by `ExportError`. Default export refuses existing
files; explicit overwrite replaces a file only after PNG encoding succeeds.

## Alpha API policy

Public factory methods and documented fields in [API.md](API.md) are the intended
API. Modules such as `attention`, `layout`, and adapters are implementation details.
Direct construction of Target, Label, Callout, and Step is unsupported.

Alpha releases may change APIs. Record any changes and migration instructions in
[the changelog](../CHANGELOG.md). Version 0.1.0a3 intentionally retains the a2 API.
Development 0.1.0a12 writes lesson schema v9: v8 (marks, draw-on, camera,
outline highlights, halo) plus step narration and prompts. It adds
`lint`/`layout`; v1-v8 still load, and a11 cannot read v8 or v9. Development 0.1.0a9 adds the optional `typography` extra, `Tutorial(font=...)`
and `font=` on the loaders; no schema change and no new required dependency.
Development 0.1.0a8 adds `Step.restyle` and lesson schema v3; v1 and v2 still load.
Development 0.1.0a6 adds `export_video` and `VideoExportError`; no existing
API changed. Development 0.1.0a5 writes lesson schema v2 and loads v1 with default timing. Unknown versions are rejected; a4 readers cannot read v2. See [persistence](PERSISTENCE.md).

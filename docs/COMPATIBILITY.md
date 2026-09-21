# Compatibility and limitations

## Evidence versus intended coverage

| Environment | Status |
| --- | --- |
| Windows x64, CPython 3.12 | Locally tested: unit tests, examples, wheel install, PNG rendering |
| Windows, Ubuntu, macOS; CPython 3.12, 3.13, 3.14 | Hosted CI: all nine jobs passed on commits fd16904 (a5) and c1fbef1 (a6) |
| Other Python implementations, architectures, or versions | Not verified |

`requires-python >=3.12` is an installation constraint, not a claim that every
future interpreter or platform has been tested. Native NumPy/OpenCV/skia-pathops
dependencies must have compatible builds for the environment.

## DrawCV dependency

The supported dependency is exactly **`pydrawcv==0.10.0.post1`**. Runtime tests use
the published wheel, not `C:/Projects/DrawCV`. Keep this narrow until release
tests establish a larger range. Users import it as `drawcv`.

TutorDraw references DrawCV objects by stable IDs and copies scenes through their
public serialization API. Basic shapes, text, nested groups, styles, and transforms
are exercised locally. This is not a guarantee of all custom objects, external
assets, vector masks, effects, or blend-mode combinations. Unsupported scene
copying raises `SceneCopyError` instead of editing the source in place.

## Text and layout

- Built-in text: Latin, Greek, Cyrillic, CJK and common symbols; newlines in callouts.
- No extra font assets or typography dependencies are required for annotations.
- Character support is probed against the installed OpenCV rather than assumed,
  so it widens automatically on builds with broader glyph coverage.
- Thai, Arabic, Hebrew, Indic scripts, emoji, rich text and equations are refused
  with a `ValidationError` naming the character. See [TEXT.md](TEXT.md).
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
OpenCV build has been tested; hosted CI results remain pending. An unavailable
codec raises `VideoExportError`. Encoding is lossy: decoded frames approximate
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
Development 0.1.0a8 adds `Step.restyle` and lesson schema v3; v1 and v2 still load.
Development 0.1.0a6 adds `export_video` and `VideoExportError`; no existing
API changed. Development 0.1.0a5 writes lesson schema v2 and loads v1 with default timing. Unknown versions are rejected; a4 readers cannot read v2. See [persistence](PERSISTENCE.md).

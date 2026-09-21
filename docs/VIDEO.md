# Video export

Implemented in **0.1.0a6**, released as part of 0.1.0a11.
This encodes the deterministic hard-cut playback described in [TIMING.md](TIMING.md)
into a single video file. It adds no new dependency.

```python
from drawcv import Scene
from tutordraw import Tutorial, VideoExportError

lesson = Tutorial(Scene(640, 360))
lesson.step("Introduction", duration=2, pause=1)
lesson.step("Review", duration=4)
# Attach labels/highlights/callouts using the existing authoring API.
try:
    path = lesson.export_video("lesson.mp4", fps=30)
except VideoExportError as error:
    print(f"This host cannot encode {error.fourcc!r}: {error}")
```

For a real annotated lesson, run `python examples/video_lesson.py`. It encodes
the 10-second cell lesson at 12 fps into `output/video`, then decodes the result
and prints its frame count and dimensions.

## API

`tutorial.export_video(path, *, fps=30, fourcc="mp4v", overwrite=False) -> Path`

| Option | Behavior |
| --- | --- |
| `path` | Destination file. Its **extension selects the container**; OpenCV infers nothing else. |
| `fps` | Positive integer, same meaning as `render_frames`. Booleans and floats are rejected. |
| `fourcc` | Exactly four printable ASCII characters, passed to `cv2.VideoWriter_fourcc`. |
| `overwrite` | Must be a real boolean. Default refuses an existing destination. |

Returns the destination `Path`. The container and codec must be compatible;
`"mp4v"` with `.mp4` and `"MJPG"` or `"XVID"` with `.avi` are the combinations
tested here.

## Contracts

- Frames come from `render_frames(fps=fps)`: `ceil(duration * fps)` frames sampled
  at `k / fps` seconds. The encoded file therefore runs up to one frame period
  longer than `tutorial.duration`. Frame timing semantics are unchanged.
- **Opaque output only.** There is no `alpha` parameter: `VideoWriter` takes
  three-channel BGR, and these codecs carry no alpha channel. For transparent
  output use `export_steps(directory, alpha=True)`.
- Invalid `fourcc`, `overwrite`, `fps`, and empty lessons raise `ValidationError`
  before any file is created and before an encoder is opened.
- An existing destination raises `FileExistsError` unless `overwrite=True`.
  Symlinks and non-file destinations are refused even with `overwrite=True`.
- Everything else fails as `VideoExportError`, which carries `path`, `fourcc`,
  `frames_written`, and the original exception as `__cause__`.
- The encoder is opened only once the first frame has rendered, so a rendering
  failure never leaves an encoder open. Its size comes from that frame; a frame
  whose size changes mid-export fails rather than being written distorted.
- The writer is released on success and on every failure path.
- Frames stream one at a time. A whole video is never held in memory, and each
  frame re-renders the scene; there is no repeated-step cache.
- Source artwork, undo history, and step independence are unchanged by export.
  Editing the lesson or scene during an export is unsupported.

## Atomicity

Encoding writes to a temporary file in the destination directory, named with the
destination's real extension so OpenCV selects the right container. The file is
moved into place only after encoding succeeds:

- `overwrite=True` replaces the destination with `os.replace` after encoding.
- `overwrite=False` uses exclusive creation, so a file created after the
  preflight check is still not overwritten; a partial new file is removed.
- An existing destination survives a codec, rendering, or write failure intact.
- A codec that opens but produces a zero-byte file is reported as a failure
  rather than left behind as a broken video.

This matches the PNG export behavior described in [API.md](API.md), except that
a video is one file: it is either replaced completely or not at all.

## Codec availability

TutorDraw calls `cv2.VideoWriter` directly. OpenCV arrives with DrawCV —
`pydrawcv==0.10.0.post1` requires `opencv-python>=4.8.0` unconditionally — so no
extra install is needed, but **which codecs a given OpenCV wheel and host
provide is not something TutorDraw can promise**. When the writer cannot open,
`VideoExportError` names the fourcc and says the host may not provide it.

Verified locally on Windows 11 x64, CPython 3.12, `opencv-python` 5.0.0.93:
`mp4v`/`.mp4`, `MJPG`/`.avi`, and `XVID`/`.avi` all encoded and decoded.
`avc1` opened only after OpenCV reported it could not load `openh264`, so H.264
is **not** claimed.

Hosted CI additionally proves that **at least one** of `mp4v`, `MJPG` and
`XVID` encodes and decodes on every supported environment. `check_installed.py`
fails when no video is produced, and all nine jobs passed on commit `188b4d2`
and `d06ceab` across Windows, Ubuntu and macOS on CPython 3.12, 3.13 and 3.14,
each decoding the example back to its full 120 frames. Which of the three a
given platform used is not recorded, so no single codec is claimed everywhere.
Portable code should still catch `VideoExportError` and fall back, as
`examples/video_lesson.py` does.

## Encoding is lossy

Decoded frames are close to, but not identical to, `render_step` output. In the
locally encoded 12 fps cell lesson the worst mean absolute difference between a
decoded frame and its source render was 2.5/255, while the two step cuts
measured 5.8 and 5.3 — so a cut is still clearly distinguishable from codec
noise. Small differences also appear at codec keyframe boundaries within a
single held step, up to about 1.1 at the opening keyframe. Use
`export_steps` when you need exact pixels; use `render_frames` when you want to
encode with your own tool.

## Not implemented

Audio, narration, subtitles, and burned-in captions. Transitions or crossfades —
playback is still hard cuts. Progressive reveals. Bitrate, quality, or pixel
format control. GIF and animated image output. Per-step or partial-range export.
Sampling animations attached to source DrawCV objects.

DrawCV's own `VideoRenderer` is not used: it requires an actual `Scene` and
drives `Scene.render_at_time`, and DrawCV exposes no encoder that accepts a
frame sequence. See [DECISIONS.md](DECISIONS.md).

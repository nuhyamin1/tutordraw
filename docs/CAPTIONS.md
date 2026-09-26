# Timed captions

New in 0.3.0a1 (unreleased). Captions carry what is said: on
screen in the browser player, burned into a video, or as a subtitle file to
upload beside it (YouTube, an LMS, a video editor).

```python
step = lesson.step("A vector", duration=5)
step.caption("A vector has a length and a direction.", at=0.3)
step.caption("This one goes three right\nand two up.", at=2.5, until=4.5)

lesson.export_captions("output/lesson.vtt")            # or .srt
lesson.export_video("output/lesson.mp4", captions=True)  # burned in
```

## Where captions come from

- **Written**: `step.caption(text, *, at=0.0, until=None)` shows `text` from
  `at` seconds into the step until `until`, or else until the step's next
  caption, or else the end of the step's pause. A newline breaks the line.
  It returns the step. Text is checked as a callout's is (see TEXT.md).
  Refused: `until` not later than `at`, two captions starting at once, and a
  written `until` running into the next caption.
- **Narrated**: a step with `narrate()` words and no written captions gets
  them from its narration: one cue per sentence, a sentence longer than 84
  characters (two subtitle lines) split into parts of about equal length,
  breaking after a comma where one is near. A cue stays 0.6 s after its last
  word unless the next starts first.

Written captions replace a step's narrated ones. A caption starting after
its step ends is never shown (lint `CAPTION_NEVER_SHOWN`); one ending after
it is cut at the step's end.

## Reading them

`lesson.captions()` returns every cue on the lesson's clock as
`Cue(start, end, text)` in seconds, steps' pauses included; `step.captions`
holds a step's written `Caption(text, at, until)`s.

## Outputs

- `lesson.export_captions(path, *, overwrite=False)`: WebVTT for `.vtt`,
  SubRip for `.srt` (case-insensitive). Other suffixes and a lesson with no
  captions raise `ValidationError` before any file is written; an existing
  file raises `FileExistsError` unless `overwrite=True`. In WebVTT `<`, `>`
  and `&` are escaped; `-->` in a caption is written `->` in both.
- `export_video(..., captions=True)`, `render_frames(captions=True)` and
  `render_at_time(t, captions=True)` draw the cue on screen at that moment:
  white text on a dark band, centred, 6% of the height above the bottom,
  wrapped to 80% of the width. Off by default, so existing output is
  unchanged. The band is drawn over the artwork; keep the bottom of the
  canvas clear if it must not cover anything.
- The browser player (`export_web`, `web_step`) shows a step's written
  captions whole under the picture (`web_step(i)["captions"]`, a list of
  `[text, start, end]`, or None). A narrated step without written captions
  keeps the word-by-word display from NARRATION.md.

## Lint

- `CAPTION_TOO_FAST` (warning): a written caption on screen for less time
  than its characters need at 20 characters a second.
- `CAPTION_NEVER_SHOWN` (error): a written caption starting after the step's
  duration plus pause.

## Saving

Lesson schema v13 saves written captions with each step as
`{"text", "at", "until"}`. Narrated captions are not saved separately; they
come from the saved narration.

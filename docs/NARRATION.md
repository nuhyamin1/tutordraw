# Narration timing

New in development 0.1.0a12. Tie each thing on screen to the phrase that
introduces it, and TutorDraw reveals it as the voice says that phrase:

```python
step.show(nucleus_label, draw=True)
note = step.explain(nucleus, "It holds the cell's DNA.")
step.highlight(nucleus, shape="outline")
step.narrate(words, {nucleus_label: "the nucleus",
                     nucleus: "sits in the middle",
                     note: "holds the DNA"})
```

`narrate` sets each cue's reveal time (`at=`) to when its phrase starts,
minus `lead` (0.15 s, so the picture lands with the word rather than after
it), and stretches the step to the end of the narration plus `tail` (0.5 s)
unless `fit=False`. Draw-on still applies from the new reveal time. It returns
the step, like `show` and `highlight`.

## Word timings

`words` is what a text-to-speech engine reports, in seconds from the start of
the step:

- a list of `(word, start, end)` tuples;
- a list of dicts with `word` or `text`, and `start`/`end` or
  `start_time`/`end_time`;
- a plain string, timed at `rate` words per second (default 2.5), for
  previews before the audio exists.

Engines that time characters rather than words can be converted with
`tutordraw.narration.words_from_characters(characters, starts, ends)`.
Timings must not go backwards.

## Cues

A cue maps one of these to a phrase:

- a label or callout **shown in this step**;
- a mark of this step (`connect`, `brace`, `measure`, `angle`, `number`);
- a **target that has a highlight** in this step, which times the highlight.

Phrases match the first place they are spoken, ignoring case, accents and
punctuation, and skipping spoken tokens that are only punctuation. A phrase
that is not spoken raises `ValidationError` quoting the start of the
narration. Every cue is checked before anything changes, so a bad cue leaves
the step as it was.

## Captions

A narrated step's `web_step` payload carries its words, and the player shows
the sentence being spoken as captions under the picture: spoken words bright,
the current word highlighted, the rest dim.

## Saving

`narrate` sets reveal times and the duration, which lesson files already save.
The narration text and word timings themselves are **not saved** yet: a
reloaded lesson keeps its timing but has no captions until `narrate` is called
again. Saving them needs a lesson-format change, deferred to the next one.

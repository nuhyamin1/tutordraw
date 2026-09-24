# Interactive prompts

New in development 0.1.0a12. A step can end with a question the learner
answers by tapping the picture:

```python
quiz = lesson.step("Your turn")
quiz.ask("Tap the stage where clouds form.", cycle.stage("condensation"))
```

In the browser player the step plays as usual, then holds at its end with
the question under the picture until the learner taps an answer. A right tap
rings the answer in green and the lesson carries on about two seconds later.
A wrong tap rings what was tapped in red and says what it was. After
`attempts` wrong taps (3), or when the learner presses **Show me**, the
answer is ringed in amber with the hint and the lesson carries on. Going back
to the step asks again. [`examples/quiz_lesson.py`](../examples/quiz_lesson.py)
builds one.

## Python API

| Call | Does |
| --- | --- |
| `step.ask(text, answer, *, correct=None, wrong=None, hint=None, attempts=3)` | Ends the step with a question. `answer` is a target, or a tuple of targets that are all right. One prompt per step; asking again replaces it. Returns the step. |
| `step.prompt`, `step.clear_prompt()` | The `Prompt` (`text`, `answers`, `correct`, `wrong`, `hint`, `attempts`), or None; remove it. |
| `tutorial.check_answer(index, x, y)` | Judges a tap at canvas point (x, y) exactly as the player does. Returns an `Answer`: `correct`, `tapped` (the target hit, or None) and `feedback`. For apps that show `render_step` images instead of the player. |
| `tutorial.hit_test(index, x, y)` | Every target under the point, innermost first: a nucleus before the cell around it. |

Taps are judged on the step's **finished** picture, so a target moved,
hidden or zoomed by the step is judged where the learner sees it. Labels and
other annotations never block a tap from reaching what is under them. A
kit's `<node>_shape` helper target is skipped when its node was hit, so
feedback says "the start", not "the start shape".

## Feedback

| | Default | Used when |
| --- | --- | --- |
| `correct` | `Yes, that's {tapped}.` | an answer is tapped |
| `wrong` | `That's {tapped}. Try again.` / `Not quite. Try again.` | a wrong target / nothing named is tapped |
| `hint` | `Here it is: {answer}.` | after `attempts` misses, or "Show me" |

`{tapped}` becomes the tapped target's name read aloud ("the cell wall", from
a target named `cell_wall`), and `{answer}` the first answer's. Your own text
may use both; other braces are left alone. An author `wrong` is used for
misses too, where `{tapped}` reads "that". Name targets the way you would say
them, because the feedback does.

## In the player

`web_step(i)["prompt"]` carries `text`, `answers` (drawable IDs), `answer`,
`attempts`, the four templates `correct`, `wrong`, `miss` and `hint`, `names`
(drawable ID to spoken name) and `helpers` (IDs never named in feedback). The
player finds what was tapped with `document.elementsFromPoint` and each
element's `data-drawcv-id` ancestors, so it agrees with `hit_test`. Listen for
answers with:

```javascript
player.onanswer = (index, result) => {
  // result: {correct, tapped: "the nucleus" or null, shown: true after "Show me", feedback}
};
```

The question and its feedback are in a live region, and **Show me** is a
keyboard-reachable button, so the step never traps someone who cannot tap.
`describe()` ends the step's description with `The learner is asked: "…"`.

## Lint

| Code | Severity | Means |
| --- | --- | --- |
| `PROMPT_HIDDEN` | error | An answer is hidden or nearly transparent in its step (restyled away or dimmed). |
| `PROMPT_UNTAPPABLE` | error | No tap across an answer's bounds reaches it: off the canvas or too thin. |
| `PROMPT_GIVEAWAY` | warning | A label in the same step names the answer. Show it in the next step instead. |

## Saving

Lesson schema v9 saves each step's prompt, answers by target ID, author
feedback and attempts. A prompt is rebuilt through `step.ask` on load, so a
saved one is validated exactly as a new one is. Files from before v9 have no
prompts.

# Teaching kits

New in development 0.1.0a12. A kit builds a standard diagram from ordinary
DrawCV objects and hands back named targets. It works out the geometry a model
tends to get wrong by hand (tick spacing, mapping maths coordinates onto the
canvas, sampling a function) and nothing else: DrawCV draws the result, lesson
files save it, and every part can be labelled, highlighted, measured or
narrated like anything else. [`examples/graph_lesson.py`](../examples/graph_lesson.py) and
[`examples/number_line_lesson.py`](../examples/number_line_lesson.py) build
narrated three-step lessons with them.

## Axes

```python
from tutordraw.kits import Axes

axes = Axes(lesson, box=(90, 80, 480, 420), x_range=(-3, 3), y_range=(-1, 9), grid=True)
curve = axes.plot(lambda x: x * x, name="parabola_curve")
vertex = axes.point(0, 0, name="vertex")
reading = axes.point(2, 4, name="reading")
guides = axes.guide(x=2, y=4, name="guides")
on_curve = axes.point(-2.4, 5.76, name="parabola", visible=False)   # an anchor to label the curve
step.show(on_curve.label("y = x²", anchor="left"))
```

| Call | Does |
| --- | --- |
| `Axes(tutorial, *, box, x_range, y_range, x_step=None, y_step=None, x_label="x", y_label="y", grid=False, name="axes", color=..., font_scale=0.5)` | Draws the axes into the scene as one DrawCV group named `name`, and registers `<name>_x_axis` and `<name>_y_axis`. `box` is (left, top, width, height) on the canvas; the ranges are the maths coordinates at its edges. Steps default to a round 1, 2 or 5 × 10ⁿ giving about eight ticks. Axes cross at 0 when 0 is in range. |
| `axes.plot(f, *, name=None, domain=None, samples=240, color=..., width=3)` | Draws y = f(x) and returns it as a target. Where f fails or is not finite the curve breaks, so 1/x has two branches. It is cut exactly where it leaves the y range. |
| `axes.point(x, y, *, name=None, radius=5, color=..., visible=True)` | A dot. `visible=False` makes an invisible anchor, for labelling a curve at a chosen point rather than beside its bounding box. |
| `axes.guide(*, x=None, y=None, name=None)` | Dashed lines: `x=a` vertical, `y=b` horizontal, both together drop from (a, b) to the axes. |
| `axes.to_scene(x, y)` | The canvas point for maths coordinates, for your own marks: `step.connect(axes.to_scene(0, 8), vertex)`. |
| `Axes.find(tutorial, name="axes")` | After `Tutorial.load_json`, reattach to saved axes to plot more. The settings travel in the group's DrawCV metadata. |

Unnamed parts are called `<name>_plot1`, `<name>_point2` and so on. Tick
numbers use plain ASCII and as few decimals as the step needs.

## Number line

```python
from tutordraw.kits import NumberLine

line = NumberLine(lesson, start=(120, 210), length=720, value_range=(0, 6))
start = line.point(2, name="start")
add = lesson.step("Add 3")
plus = line.hop(add, 2, 5, "+3")            # a step mark: draws on, can be a narration cue
bounds = line.interval(-1, 4, open_start=True)   # for inequalities
```

| Call | Does |
| --- | --- |
| `NumberLine(tutorial, *, start, length, value_range, step=None, name="number_line", color=..., font_scale=0.55)` | A horizontal line with arrowheads, round ticks (about ten) and numbers, as one DrawCV group; registers `<name>_line`. `start` is its left end on the canvas. |
| `line.point(value, *, name=None, open=False, radius=7, color=...)` | A dot on the line; `open=True` draws it hollow, as for a strict inequality. |
| `line.hop(step, start, end, text=None, *, at=None, draw=True, bend=None)` | The hop arrow used to teach +3 or -2, returned as a **step mark**: it belongs to that step only, draws on by default, takes `at=` and can be a narration cue. Rightward hops arc above the line, leftward below, and long hops stay within 45 px of it. |
| `line.anchor(value)` | The invisible target at a value, `<name>_at_<value>`, which hops connect. Reused if it exists. Use it for your own marks. |
| `line.interval(start, end, *, name=None, open_start=False, open_end=False, color=...)` | A highlighted stretch with open or closed ends. |
| `line.to_scene(value)`, `NumberLine.find(tutorial, name)` | As for axes. |

Hops are marks rather than drawing because a hop is something that *happens*
in a step: it should draw on as the narration says it, not sit in every step.
Descriptions read "An arrow goes from the number line at 2 to the number line
at 5, labelled "+3"".

## Kit parts are part of the drawing

Everything a kit adds is in the scene, so it is visible in **every** step.
Hide what belongs to a later step with `step.restyle(target, visible=False)`,
as the graph example does for its reading point and guides. `describe()`
stays quiet about things hidden from the first step, and says "the reading
appears" when a later step shows them.

## Labels near curves

Label placement treats an unfilled stroke (a curve, a line, an outline) as
small boxes along its ink rather than one bounding box, so a label can sit in
the empty space inside a parabola. Text in the drawing, such as tick numbers
and titles, is avoided too. Both apply to every lesson, not only kits.

## More kits

Flowcharts, timelines, cycles and force diagrams are on the roadmap. Each will follow the same rules: plain DrawCV objects, named targets,
settings in metadata so `find` can reattach.

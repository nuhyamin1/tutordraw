# Teaching kits

New in 0.2.0a1. A kit builds a standard diagram from ordinary
DrawCV objects and hands back named targets. It works out the geometry a model
tends to get wrong by hand (tick spacing, mapping maths coordinates onto the
canvas, sampling a function) and nothing else: DrawCV draws the result, lesson
files save it, and every part can be labelled, highlighted, measured or
narrated like anything else. Every kit has a narrated example lesson:
[graph](../examples/graph_lesson.py), [number line](../examples/number_line_lesson.py),
[flowchart](../examples/flowchart_lesson.py), [timeline](../examples/timeline_lesson.py),
[water cycle](../examples/water_cycle_lesson.py), [forces](../examples/forces_lesson.py) and
[Earth's layers](../examples/earth_layers_lesson.py) and
[Pythagoras](../examples/pythagoras_lesson.py).

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
| `Axes(tutorial, *, box, x_range, y_range, x_step=None, y_step=None, x_label="x", y_label="y", grid=False, name="axes", color=..., font_scale=0.5)` | Draws the axes into the scene as one DrawCV group named `name`, and registers `<name>_x_axis` and `<name>_y_axis`. `box` is (left, top, width, height) on the canvas; the ranges are the maths coordinates at its edges. Steps default to a round 1, 2 or 5 × 10ⁿ giving about eight ticks. Axes cross at 0 when 0 is in range, and the origin is numbered once, "0" below-left of it; a tick number that would touch it or another number (a range from −0.5 on a small graph) is left out, its tick still drawn. |
| `axes.plot(f, *, name=None, domain=None, samples=240, color=..., width=3)` | Draws y = f(x) and returns it as a target. Where f fails or is not finite the curve breaks, so 1/x has two branches. It is cut exactly where it leaves the y range. |
| `axes.point(x, y, *, name=None, radius=5, color=..., visible=True)` | A dot. `visible=False` makes an invisible anchor, for labelling a curve at a chosen point rather than beside its bounding box. |
| `axes.guide(*, x=None, y=None, name=None)` | Dashed lines: `x=a` vertical, `y=b` horizontal, both together drop from (a, b) to the axes. |
| `axes.to_scene(x, y)` | The canvas point for maths coordinates, for your own marks: `step.connect(axes.to_scene(0, 8), vertex)`. |
| `axes.region(f, g=0, *, domain=None, samples=240, color=..., opacity=0.3, name=None)` | Shades between y = f(x) and y = g(x): the area under a curve (g = 0), between two curves, or above or below a curve (g a number such as the top of the y range). f and g are functions or numbers. Sampled like `plot`, so it meets the curve exactly; cut to the ranges, broken where either has no value, and drawn beneath the grid and curves. |
| `axes.rectangles(f, domain, count, *, rule="left", color=..., opacity=0.3, name=None)` | `count` equal rectangles from y = 0 up to f across `domain` (a Riemann sum); `rule` is `"left"`, `"right"` or `"mid"`. `domain` must lie inside the x range. One target for them all. |
| `axes.tangent(f, x, *, span=None, color=..., width=2.5, name=None)` | The tangent at x, its slope worked out from f, drawn across `span` (default the whole x range) and cut to the ranges. Refused at a corner, a jump or where f has no value. |
| `axes.secant(f, x1, x2, *, span=None, ...)` | The line through the curve at x1 and x2; `span=(x1, x2)` draws just the chord. |
| `axes.intersections(f, g=0, *, domain=None, samples=2000)` | Where y = f(x) meets y = g(x), as (x, y) pairs from left to right (with g = 0, the roots). Finds touching points too, and ignores a jump across the other curve. Draws nothing: pass the points to `point`, or use their x as a `domain`. |
| `axes.clip(points, *, closed=False)` | Maths points as canvas points, cut exactly at the edges of the plot area: one piece for a closed shape, one per stretch inside for an open line, `[]` if none of it is inside. The geometry is cut, not masked, so bounds, labels and marks follow what is visible. |
| `axes.add(drawable, *, name=None)` | Makes any DrawCV drawable part of the graph (it hides, fades and moves with the axes) and returns it as a target. Build it from `to_scene`, `to_scene_offset` or `clip`. |
| `axes.to_scene_offset(dx, dy)`, `axes.contains(x, y)` | A maths displacement in canvas pixels (y flips), and whether a point is inside the ranges. |
| `axes.along(f, x_from, x_to, *, samples=32, start=None)` | The way along y = f(x) as `samples` + 1 canvas offsets from `start` (a maths point; default the curve at x_from), for `restyle(dot, move=way[-1], via=way[1:-1])` on an animated step: the dot slides along the curve. Refuses a curve with no value on the way. |
| `Axes.find(tutorial, name="axes")` | After `Tutorial.load_json`, reattach to saved axes to plot more. The settings travel in the group's DrawCV metadata. |

Unnamed parts are called `<name>_plot1`, `<name>_point2` and so on. Tick
numbers use plain ASCII and as few decimals as the step needs.

Everything on a graph should come from the graph's own mapping, never from
canvas pixels worked out by hand: a region, rectangle or tangent computed
from the curve's function meets the curve exactly, where a hand-placed
polygon only ever approximates it.

```python
area = axes.region(lambda x: x * x, domain=(0, 2), name="area")      # the integral from 0 to 2
riemann = axes.rectangles(lambda x: x * x, (0, 2), 8, rule="mid", name="riemann")
touch = axes.tangent(lambda x: x * x, 1.5, name="tangent")
(a, _), (b, _) = axes.intersections(lambda x: x * x, lambda x: x + 2)
between = axes.region(lambda x: x + 2, lambda x: x * x, domain=(a, b), name="between")
[wedge] = axes.clip([(0, 0), (2, 0), (2, 4)], closed=True)          # your own shape, in graph units
axes.add(Polygon(vertices=wedge, fill=FillStyle(color=Color(250, 200, 120))), name="wedge")
```

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

## Flowchart

```python
from tutordraw.kits import Flowchart

flow = Flowchart(lesson, origin=(260, 110), cell=(260, 110))
start = flow.node("start", "Leaving home", at=(0, 0), shape="terminal")
check = flow.node("question", "Is it raining?", at=(0, 1), shape="decision")
umbrella = flow.node("umbrella", "Take an umbrella", at=(1, 2))
school = flow.node("school", "Walk to school", at=(0, 3), shape="terminal")
flow.link(start, check)
yes = flow.link(check, umbrella, "yes")
flow.link(check, school, "no")
```

| Call | Does |
| --- | --- |
| `Flowchart(tutorial, *, origin, cell=(220, 110), node_size=(170, 60), name="flowchart", color=..., fill=..., font_scale=0.5)` | An empty chart. `origin` is the centre of cell (0, 0); `cell` is the spacing of columns and rows, which must be larger than `node_size` to leave room for arrows. |
| `flow.node(name, text, *, at, shape="box", fill=None)` | A node at grid cell `at=(col, row)`, returned as a target that holds the shape and its text. Shapes: `"box"`, `"decision"` (diamond), `"terminal"` (pill), `"data"` (slanted). Text wraps to fit. The shape alone is also a target, `<name>_shape`, for `restyle(fill=...)`. |
| `flow.link(source, destination, text=None, *, name=None)` | An arrow drawn into the scene, named `arrow_from_<a>_to_<b>` unless named. Nodes in a row or column join straight; otherwise it leaves the side facing the destination and turns once into its top or bottom. An arrow back up a column (a loop) runs round the left. `text` ("yes") sits by its start. Nodes are given as targets or names. |
| `flow.to_scene(col, row)`, `Flowchart.find(tutorial, name)` | As for axes. |

## Timeline

```python
from tutordraw.kits import Timeline

line = Timeline(lesson, start=(70, 240), length=800, span=(1900, 1980))
jets = line.period(1939, 1980, "The jet age")      # periods first, so events clear them
flight = line.event(1903, "First powered flight")   # above
atlantic = line.event(1927, "Solo across the Atlantic")   # below
```

| Call | Does |
| --- | --- |
| `Timeline(tutorial, *, start, length, span, step=None, name="timeline", color=..., font_scale=0.5)` | A line with an arrowhead and round date ticks (about eight); registers `<name>_line`. `span` is the first and last date, any numbers. |
| `line.event(when, text, *, name=None, side=None, color=...)` | A dot with its text on a stem, as one target. Events alternate above and below unless `side` is given, and a stem grows in 36 px levels until the text clears everything already placed. Text wraps at 150 px. |
| `line.period(start, end, text, *, name=None, row=0, color=...)` | A band above the line between two dates; `row` stacks overlapping periods. Add periods before events so events climb over them. |
| `line.to_scene(when)`, `Timeline.find(tutorial, name)` | As for axes; a found timeline still avoids what was placed before saving. |

## Cycle

```python
from tutordraw.kits import Cycle

cycle = Cycle(lesson, center=(450, 340), radius=210,
              stages=["Evaporation", "Condensation", "Precipitation", "Collection"])
step.highlight(cycle.stage("condensation"))
step.dim_others(cycle.stage(2), cycle.arrows[0])   # the stage and the arrow into it
```

| Call | Does |
| --- | --- |
| `Cycle(tutorial, *, center, radius, stages, name="cycle", node_size=(150, 54), clockwise=True, color=..., fills=..., font_scale=0.5)` | 2 to 12 stages round a circle, the first at the top, joined by curved arrows that stop short of the boxes. A stage is a target named from its text (`"Evaporation"` becomes `evaporation`), or give `(name, text)` pairs. Too small a radius is refused with the radius to use. |
| `cycle.stages`, `cycle.arrows` | Targets in order. `arrows[i]` leaves stage i + 1 and is named `arrow_from_<a>_to_<b>`; the last closes the loop. |
| `cycle.stage(key)` | A stage by number (1 is the first) or name. |
| `Cycle.find(tutorial, name)` | Reattach after loading. |

## Force diagram

```python
from tutordraw.kits import ForceDiagram

crate = ForceDiagram(lesson, center=(450, 320), size=90, scale=4, text="5 kg", name="crate")
weight = crate.force("weight", "down", 49, "weight 49 N")
push = crate.force("push", 30, 40, "push 40 N")      # 30 degrees above the right
parts = crate.components(push)                       # dashed horizontal and vertical parts
net = crate.net("net force")                         # the vector sum, worked out
```

| Call | Does |
| --- | --- |
| `ForceDiagram(tutorial, *, center, body="block", size=80, scale=6, text=None, name="body", fill=..., color=..., font_scale=0.5)` | A block or ball (`body="ball"`) as the target `name`. `scale` is pixels per unit of force, so every arrow is to scale. |
| `fd.force(name, direction, magnitude, text=None, *, color=...)` | An arrow out from the body's edge, as a target. `direction` is degrees anticlockwise from the right (90 is up), or a word: `up`, `down`, `left`, `right`, `up-left` and so on. The text sits past the tip. Arrows under 12 px are refused as invisible. |
| `fd.components(force, *, name=None)` | The force's horizontal and vertical parts as dashed arrows, one target named `<force>_components`. |
| `fd.net(text=None, *, name="net_force")`, `fd.resultant` | The sum of the forces so far as its own arrow, and as numbers (x, y up). Balanced forces raise, because there is no arrow: say "the forces balance" instead. The net arrow runs along any force in the same direction, so hide those in the step that shows it. |
| `ForceDiagram.find(tutorial, name)` | Reattach by the body's name. |

## Cross-section

```python
from tutordraw.kits import CrossSection

earth = CrossSection(lesson, box=(60, 80, 480, 480), shape="rings", name="earth",
                     layers=[("crust", "Crust", 0.5), ("mantle", "Mantle", 2.9),
                             ("outer_core", "Outer core", 2.2), ("inner_core", "Inner core", 1.2)])
step.show(*earth.labels())
```

| Call | Does |
| --- | --- |
| `CrossSection(tutorial, *, box, layers, shape="bands", name="section", fills=..., color=...)` | Layers, outermost or topmost first, as `(name, text)` or `(name, text, thickness)` with relative thickness. `"bands"` stacks rectangles down the box (soil, the atmosphere, skin); `"rings"` nests circles in it (the Earth, a tree trunk, an onion). Each layer is a target by its name. |
| `section.labels(*, side="right", gap=36)` | A label per layer, lined up in one column. A band's leader ends on its own edge. A ring's points into the ring itself, through an invisible anchor `<name>_layer` (so descriptions read "the mantle layer is labelled"), and ring labels are spaced evenly. Show them together or one per step. |
| `section.layer(name)`, `CrossSection.find(tutorial, name)` | A layer's target; reattach after loading. |

## Equation

Needs the optional math extra: `pip install "tutordraw[math]"` (ziamath,
pure Python, MIT, about 3 MB with its STIX Two Math font). Without it,
`Equation` raises with that install command.

```python
from tutordraw.kits import Equation

theorem = Equation(lesson, [("a_squared", "a^2"), "+", ("b_squared", "b^2"), "=",
                            ("c_squared", "c^2")], position=(600, 250), size=48, name="theorem")
step.restyle(theorem.part("c_squared"), fill=(200, 70, 50))
step.connect(theorem.part("c_squared"), (300, 305), draw=True)   # to the hypotenuse
quadratic = Equation(lesson, r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}", position=(40, 30))
```

| Call | Does |
| --- | --- |
| `Equation(tutorial, latex, *, position, size=32, name="equation", color=..., spacing=None)` | Typesets LaTeX as filled DrawCV paths. `latex` is one string or a list of pieces laid left to right on one baseline, each a string or a `(name, latex)` pair. `position` is the top left; `size` the font size in pixels (6 to 400); `spacing` the gap between pieces (0.22 x size). The whole equation is the target `name`. |
| `eq.parts`, `eq.part(key)` | Each piece is one `Path` target, named as given or `<name>_part<i>`, so it can be highlighted, recoloured with `restyle(fill=...)`, connected to, hidden or narrated. By number (1 is the first) or name. |
| `eq.width`, `eq.height`, `eq.baseline` | The typeset size and the baseline's canvas y, for placing things beside it. |
| `Equation.find(tutorial, name)` | Reattach after loading. |

Supported LaTeX is what ziamath and latex2mathml read: fractions, roots,
sub- and superscripts, big operators with limits, Greek, arrows,
`\mathrm{}` for chemistry, `\vec`, `\left(`/`\right)`, matrices. A piece
must be complete on its own, so a name can go on `b^2 - 4ac` only if it is
its own piece, not inside a `\sqrt`. Bad input is refused with the problem
named, including an unknown command such as `\foo`, which the converter
would otherwise draw as the word.

Cost: glyph outlines are many points, and DrawCV maps each point to world
space one at a time, so a step showing one formula renders in about 0.2 s
and linting it takes longer. Fine for a lesson; worth knowing in a tight
loop. See DECISIONS "Equations".

## Kit text

Text inside kit drawings (node text, dates, stage names, force captions) is
part of the scene, drawn by DrawCV's built-in renderer. It accepts Latin,
Greek, Cyrillic, CJK and symbols and refuses Thai and Arabic with the usual
error naming the character. For those scripts, keep the kit's own text short
or empty and label its parts with annotations, which use the tutorial's font.

## More kits

Every kit follows the same rules: plain DrawCV objects in one group, named
targets, settings in the group's metadata so `find` can reattach. Candidates
for later kits: circuits, maps, a periodic-table cell, Venn diagrams.

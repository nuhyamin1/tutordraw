"""Canonical lessons whose rendered frames are pinned by tests/test_golden.py.

Self-contained on purpose: the examples are free to change, these are not.
Every target is named so the geometry snapshots carry no random IDs. Built-in
text only, so the references do not depend on a font file being installed.
Changing a lesson here means regenerating its references; see test_golden.py.
"""

from drawcv import (Circle, Color, Ellipse, FillStyle, Group, Line, Point, Polygon, Rectangle,
                    Scene, StrokeStyle, Text)

from tutordraw import Theme, Tutorial

INK = Color(40, 52, 72)


def _title(scene: Scene, text: str) -> None:
    scene.add(Text(text=text, position=Point(28, 22), font_scale=0.8, thickness=2, color=INK))


def cell() -> Tutorial:
    """The acceptance lesson: labels, a callout, a highlight, dimming, review."""
    scene = Scene(720, 420, background=Color(240, 245, 250))
    _title(scene, "INSIDE A CELL")
    membrane = Circle(center=Point(220, 240), radius=140,
                      fill=FillStyle(color=Color(232, 242, 244)),
                      stroke=StrokeStyle(color=Color(190, 214, 216), width=3))
    nucleus = Circle(center=Point(240, 230), radius=46,
                     fill=FillStyle(color=Color(131, 151, 218)),
                     stroke=StrokeStyle(color=Color(70, 88, 150), width=2))
    mito = Ellipse(center=Point(150, 320), radius_x=34, radius_y=16,
                   fill=FillStyle(color=Color(226, 170, 120)))
    for shape in (membrane, nucleus, mito):
        scene.add(shape)
    lesson = Tutorial(scene, title="Inside a cell")
    t_cell = lesson.target(membrane, name="cell")
    t_nucleus = lesson.target(nucleus, name="nucleus")
    t_mito = lesson.target(mito, name="mitochondrion")
    cell_label = t_cell.label("Cell", anchor="top")
    nucleus_label = t_nucleus.label("Nucleus", anchor="right", gap=60)
    mito_label = t_mito.label("Mitochondrion", anchor="bottom")

    lesson.step("Meet the cell").show(cell_label).explain(
        t_cell, "Every living thing is made of cells.", anchor="right", gap=40, max_width=200)
    focus = lesson.step("Find the nucleus").show(nucleus_label)
    focus.highlight(t_nucleus).dim_others(t_nucleus)
    focus.explain(t_nucleus, "The nucleus holds the cell's DNA.", anchor="bottom", max_width=180)
    lesson.step("Review").show(cell_label, nucleus_label, mito_label)
    return lesson


def crowded() -> Tutorial:
    """Six labels authored on top of each other: the collision resolver's job."""
    scene = Scene(720, 420, background=Color.white())
    _title(scene, "CROWDED")
    shapes = {
        "box": Rectangle(position=Point(120, 200), width=90, height=60,
                         fill=FillStyle(color=Color(200, 170, 120))),
        "puck": Circle(center=Point(300, 230), radius=24, fill=FillStyle(color=Color(60, 60, 70))),
        "ball_a": Circle(center=Point(380, 220), radius=18, fill=FillStyle(color=Color(210, 80, 70))),
        "ball_b": Circle(center=Point(430, 250), radius=14, fill=FillStyle(color=Color(70, 140, 210))),
        "ball_c": Circle(center=Point(470, 215), radius=14, fill=FillStyle(color=Color(90, 180, 110))),
    }
    for shape in shapes.values():
        scene.add(shape)
    lesson = Tutorial(scene)
    t = {name: lesson.target(shape, name=name) for name, shape in shapes.items()}
    step = lesson.step("Everything at once").show(
        t["box"].label("box at rest", anchor="right"),
        t["puck"].label("puck on smooth table", anchor="left"),
        t["ball_a"].label("A fast (v = 6)", anchor="top"),
        t["ball_b"].label("small ball B", anchor="top"),
        t["ball_c"].label("small ball C", anchor="top"),
    )
    step.explain(t["puck"], "push", anchor="top")
    step.highlight(t["ball_a"])
    return lesson


def bare() -> Tutorial:
    """box=False text over a coloured band, next to a boxed label."""
    scene = Scene(720, 300, background=Color.white())
    scene.add(Rectangle(position=Point(0, 120), width=720, height=90,
                        fill=FillStyle(color=Color(255, 226, 170))))
    dot = Circle(center=Point(200, 165), radius=20, fill=FillStyle(color=Color(40, 90, 160)))
    bar = Rectangle(position=Point(420, 140), width=140, height=50,
                    fill=FillStyle(color=Color(160, 60, 90)))
    scene.add(dot)
    scene.add(bar)
    lesson = Tutorial(scene)
    t_dot = lesson.target(dot, name="dot")
    t_bar = lesson.target(bar, name="bar")
    lesson.step("Bare text").show(
        t_dot.label("no panel here", anchor="right", box=False),
        t_bar.label("boxed", anchor="top"),
    ).explain(t_bar, "A wrapped caption drawn straight onto the band.",
              anchor="bottom", box=False, max_width=220)
    return lesson


def groups() -> Tutorial:
    """Focus a child inside a nested group while its siblings dim."""
    scene = Scene(720, 320, background=Color(240, 245, 250))
    _title(scene, "FOCUS INSIDE A GROUP")
    fill = FillStyle(color=Color(98, 148, 210))
    left = Circle(center=Point(150, 170), radius=40, fill=fill)
    middle = Circle(center=Point(360, 170), radius=40, fill=fill)
    right = Circle(center=Point(570, 170), radius=40, fill=fill)
    scene.add(Group(children=[Group(children=[left, middle]), right]))
    lesson = Tutorial(scene)
    t_left = lesson.target(left, name="left")
    t_middle = lesson.target(middle, name="middle")
    t_right = lesson.target(right, name="right")
    step = lesson.step("Focus").show(
        t_left.label("Focused child", anchor="bottom"),
        t_middle.label("Sibling dimmed", anchor="bottom"),
        t_right.label("Other branch dimmed", anchor="bottom"),
    )
    step.highlight(t_left).dim_others(t_left)
    return lesson


def motion() -> Tutorial:
    """An animated move and recolour with a delayed reveal, sampled mid-flight."""
    scene = Scene(720, 360, background=Color(18, 22, 40))
    body = Circle(center=Point(160, 110), radius=28, fill=FillStyle(color=Color(214, 219, 232)))
    track = Line(start=Point(100, 260), end=Point(640, 260),
                 stroke=StrokeStyle(color=Color(80, 90, 130), width=2))
    scene.add(track)
    scene.add(body)
    lesson = Tutorial(scene, theme=Theme(panel_color=(238, 242, 252), border_color=(120, 140, 190),
                                         leader_color=(170, 190, 235)))
    t_body = lesson.target(body, name="body")
    t_track = lesson.target(track, name="track")
    label = t_body.label("Body", anchor="right")
    lesson.step("Start", duration=2).show(label)
    move = lesson.step("Slide", duration=4).show(label).animate()
    move.restyle(t_body, move=(380, 120), fill=(168, 68, 52))
    move.highlight(t_body)
    move.explain(t_track, "It lands on the track.", anchor="bottom", max_width=200)
    move.show(t_track.label("Track", anchor="left"), at=2.0)
    return lesson


def edges() -> Tutorial:
    """Targets hugging the canvas edges, so panels are clamped back on screen."""
    scene = Scene(600, 320, background=Color.white())
    corner = Rectangle(position=Point(540, 10), width=50, height=40,
                       fill=FillStyle(color=Color(120, 170, 110)))
    floor = Rectangle(position=Point(10, 280), width=120, height=30,
                      fill=FillStyle(color=Color(110, 120, 170)))
    scene.add(corner)
    scene.add(floor)
    lesson = Tutorial(scene)
    t_corner = lesson.target(corner, name="corner")
    t_floor = lesson.target(floor, name="floor")
    step = lesson.step("Edges").show(
        t_corner.label("Top-right corner", anchor="right"),
        t_floor.label("Bottom-left floor", anchor="bottom"),
    )
    step.highlight(t_corner).highlight(t_floor)
    return lesson


def vocab() -> Tutorial:
    """Every mark kind, an outline highlight and numbered markers."""
    scene = Scene(760, 540, background=Color(248, 250, 252))
    _title(scene, "MARKS")
    sun = Circle(center=Point(120, 200), radius=40, fill=FillStyle(color=Color(250, 200, 70)))
    earth = Circle(center=Point(380, 200), radius=26, fill=FillStyle(color=Color(80, 130, 210)))
    moon = Circle(center=Point(470, 170), radius=10, fill=FillStyle(color=Color(190, 190, 200)))
    block = Rectangle(position=Point(560, 150), width=140, height=80,
                      fill=FillStyle(color=Color(160, 200, 150)))
    tri = Polygon(vertices=[Point(90, 490), Point(420, 490), Point(90, 300)],
                  fill=FillStyle(color=Color(230, 225, 245)),
                  stroke=StrokeStyle(color=Color(120, 110, 170), width=2))
    for shape in (sun, earth, moon, block, tri):
        scene.add(shape)
    lesson = Tutorial(scene)
    t_sun, t_earth, t_moon, t_block, t_tri = (lesson.target(s, name=n) for s, n in
        ((sun, "sun"), (earth, "earth"), (moon, "moon"), (block, "block"), (tri, "triangle")))
    orbit = lesson.step("Relations")
    orbit.connect(t_sun, t_earth, "light", bend=0.0)
    orbit.connect(t_earth, t_moon, "gravity", bend=0.4, both=True)
    orbit.brace(t_earth, t_moon, text="Earth-Moon system", side="bottom")
    orbit.measure(t_block, text="14 cm", axis="x")
    orbit.measure(t_block, text="8 cm", axis="y", offset=16)
    orbit.number(t_sun)
    orbit.number(t_earth)
    orbit.number(t_block, corner="top_right")
    orbit.highlight(t_earth, shape="outline", padding=6)
    geometry = lesson.step("Geometry")
    geometry.angle((90, 490), (420, 490), (90, 300), "90 deg", radius=28)
    geometry.angle((420, 490), (90, 490), (90, 300), "a", radius=48)
    geometry.measure((90, 490), (420, 490), "base", axis="x", offset=18)
    geometry.measure((420, 490), (90, 300), "hypotenuse", axis="free")
    geometry.highlight(t_tri, shape="outline", padding=5)
    return lesson


def camera() -> Tutorial:
    """Zoom into one target and back out, animated both ways."""
    scene = Scene(720, 400, background=Color(240, 245, 250))
    _title(scene, "ZOOM")
    cell = Circle(center=Point(360, 220), radius=150, fill=FillStyle(color=Color(232, 242, 244)),
                  stroke=StrokeStyle(color=Color(190, 214, 216), width=3))
    nucleus = Circle(center=Point(420, 190), radius=30, fill=FillStyle(color=Color(131, 151, 218)))
    dot = Circle(center=Point(300, 280), radius=8, fill=FillStyle(color=Color(220, 120, 90)))
    for shape in (cell, nucleus, dot):
        scene.add(shape)
    lesson = Tutorial(scene)
    t_cell = lesson.target(cell, name="cell")
    t_nucleus = lesson.target(nucleus, name="nucleus")
    t_dot = lesson.target(dot, name="ribosome")
    lesson.step("Whole cell").show(t_cell.label("Cell", anchor="top"))
    close = lesson.step("Nucleus", duration=2).animate().zoom_to(t_nucleus, padding=60)
    close.show(t_nucleus.label("Nucleus", anchor="right")).highlight(t_nucleus)
    back = lesson.step("Back out", duration=2).animate()
    back.show(t_dot.label("Ribosome", anchor="bottom"))
    return lesson


def drawon() -> Tutorial:
    """Strokes drawing on: a leader, a highlight and an arrow, sampled mid-draw."""
    scene = Scene(640, 300, background=Color.white())
    a = Rectangle(position=Point(80, 120), width=80, height=60, fill=FillStyle(color=Color(150, 190, 230)))
    b = Circle(center=Point(460, 150), radius=36, fill=FillStyle(color=Color(230, 160, 150)))
    scene.add(a)
    scene.add(b)
    lesson = Tutorial(scene, theme=Theme(draw_seconds=1.0))
    t_a, t_b = lesson.target(a, name="a"), lesson.target(b, name="b")
    step = lesson.step("Draw", duration=4)
    step.show(t_a.label("Source", anchor="top"), draw=True)
    step.highlight(t_b, draw=True, at=0.5)
    step.connect(t_a, t_b, "flows to", draw=True, at=1.0)
    return lesson


# name -> (builder, [(frame name, step index, progress)])
LESSONS = {
    "cell": (cell, [("step1", 0, 1.0), ("step2", 1, 1.0), ("step3", 2, 1.0)]),
    "crowded": (crowded, [("step1", 0, 1.0)]),
    "bare": (bare, [("step1", 0, 1.0)]),
    "groups": (groups, [("step1", 0, 1.0)]),
    "motion": (motion, [("start", 0, 1.0), ("mid", 1, 0.4), ("end", 1, 1.0)]),
    "edges": (edges, [("step1", 0, 1.0)]),
    "vocab": (vocab, [("relations", 0, 1.0), ("geometry", 1, 1.0)]),
    "camera": (camera, [("whole", 0, 1.0), ("zooming", 1, 0.5), ("zoomed", 1, 1.0),
                        ("leaving", 2, 0.5), ("out", 2, 1.0)]),
    "drawon": (drawon, [("leader", 0, 0.1), ("highlight", 0, 0.2), ("arrow", 0, 0.375),
                        ("done", 0, 1.0)]),
}

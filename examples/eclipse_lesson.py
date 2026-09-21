"""Show change over time: the Moon moves into Earth's shadow and turns red.

Each beat restyles the same source drawing, and the last two animate into
their state so the Moon slides rather than jumps. The scene itself is never
edited, so the beats stay independent and render in any order.
"""

from pathlib import Path

from drawcv import (Circle, Color, FillStyle, Group, Point, Polygon, Scene,
                    StrokeStyle, Text)
from tutordraw import Theme, Tutorial

MOON_GREY = (214, 219, 232)
MOON_RED = (168, 68, 52)


def build_tutorial() -> Tutorial:
    scene = Scene(1100, 620, background=Color(12, 16, 34))
    scene.add(Group(children=[
        Text(text="WHY THE MOON GOES DARK", position=Point(48, 34),
             font_scale=1.0, thickness=2, color=Color(236, 240, 252)),
        Text(text="A lunar eclipse in four beats", position=Point(48, 80),
             font_scale=0.6, color=Color(150, 165, 205)),
    ]))
    sun = Circle(center=Point(70, 340), radius=62,
                 fill=FillStyle(color=Color(252, 211, 77)))
    umbra = Polygon(vertices=[Point(430, 286), Point(430, 394), Point(1000, 452),
                              Point(1000, 228)],
                    fill=FillStyle(color=Color(38, 44, 74)))
    earth = Circle(center=Point(420, 340), radius=54,
                   fill=FillStyle(color=Color(88, 133, 214)),
                   stroke=StrokeStyle(color=Color(150, 190, 255), width=2))
    # Authored above the shadow; beats three and four move it down into the cone.
    moon = Circle(center=Point(820, 150), radius=26,
                  fill=FillStyle(color=Color(*MOON_GREY)))
    for shape in (sun, umbra, earth, moon):
        scene.add(shape)

    lesson = Tutorial(scene, title="Lunar eclipse",
                      theme=Theme(font_scale=0.7, padding=12,
                                  text_color=(18, 22, 44), panel_color=(238, 242, 252),
                                  border_color=(120, 140, 190), leader_color=(170, 190, 235)))
    t_sun = lesson.target(sun, name="sun")
    t_earth = lesson.target(earth, name="earth")
    t_moon = lesson.target(moon, name="moon")
    t_umbra = lesson.target(umbra, name="umbra")

    cast = lesson.step("Cast", duration=6).show(
        t_sun.label("Sun", anchor="bottom", gap=26),
        t_earth.label("Earth", anchor="bottom", gap=30),
        t_moon.label("Moon", anchor="top", gap=24))
    # The shadow is not part of the story yet, so hide it entirely.
    cast.restyle(t_umbra, visible=False)
    cast.explain(t_earth, "Sunlight falls on the Earth. The Moon orbits well "
                          "beyond it.", anchor="bottom", gap=110, max_width=280)

    shadow = lesson.step("Shadow", duration=7).show(t_earth.label("Earth", anchor="bottom", gap=30))
    shadow.highlight(t_umbra).dim_others(t_umbra, t_earth, t_sun, opacity=0.3)
    shadow.explain(t_umbra, "Earth blocks that light and casts a shadow cone — "
                            "the umbra — roughly 1.4 million km long.",
                   anchor="top", gap=70, max_width=290)

    entry = lesson.step("Entry", duration=6).animate("ease_in_out")
    entry.restyle(t_moon, move=(0, 190))
    entry.show(t_moon.label("Moon", anchor="top", gap=24))
    entry.highlight(t_moon).dim_others(t_moon, t_umbra, opacity=0.35)
    entry.explain(t_moon, "About twice a year the orbit carries the Moon straight "
                          "into that cone.", anchor="bottom", gap=95, max_width=280)

    total = lesson.step("Totality", duration=8).animate("ease_in_out")
    total.restyle(t_moon, move=(0, 190), fill=MOON_RED)
    total.restyle(t_sun, opacity=0.35)
    total.show(t_moon.label("≈ 100 min", anchor="top", gap=24))
    total.highlight(t_moon).dim_others(t_moon, opacity=0.4)
    total.explain(t_moon, "Totality lasts up to ≈ 100 min. The Moon turns red: "
                          "Earth's atmosphere bends red light (λ ≈ 700 nm) "
                          "around the planet.", anchor="bottom", gap=95, max_width=300)
    return lesson


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output" / "eclipse"
    lesson = build_tutorial()
    paths = lesson.export_steps(output, overwrite=True)
    animated = sum(1 for step in lesson.steps if step.easing)
    print(f"Saved {len(paths)} beats of a {lesson.duration:g}-second lesson "
          f"({animated} animated) in {output}")


if __name__ == "__main__":
    main()

"""Blocks placed beside, below or above others from measured sizes, and moved clear of what they cover.

Models writing text and equations by absolute pixels guess sizes TutorDraw
knows exactly, and stack them on each other. `arrange` places a block of a
measured size relative to another's real bounds, and finds the nearest free
spot for one that already overlaps something.
"""

import pytest
from drawcv import BoundingBox, Color, Point, Scene, Text

from tutordraw import Tutorial, ValidationError
from tutordraw.arrange import clear, place, shift_to

CANVAS = (960, 540)


def overlaps(a, b):
    return a.left < b.right and b.left < a.right and a.top < b.bottom and b.top < a.bottom


def test_each_side_leaves_the_gap_and_lines_up_the_start():
    ref = BoundingBox(100, 100, 200, 120)
    assert place((80, 40), ref, "right", gap=16) == BoundingBox(316, 100, 80, 40)
    assert place((80, 40), ref, "left", gap=16) == BoundingBox(4, 100, 80, 40)
    assert place((80, 40), ref, "below", gap=16) == BoundingBox(100, 236, 80, 40)
    assert place((80, 40), ref, "above", gap=16) == BoundingBox(100, 44, 80, 40)


def test_beside_takes_the_right_and_falls_back_to_the_left_where_there_is_room():
    graph = BoundingBox(100, 40, 560, 440)
    assert place((200, 60), graph, "beside", canvas=CANVAS).left == 676
    wide = BoundingBox(300, 40, 560, 440)  # 100 px left of it on the right, 300 on the left
    box = place((200, 60), wide, "beside", canvas=CANVAS)
    assert box.right == 300 - 16 and not overlaps(box, wide)


def test_the_cross_axis_is_kept_on_the_canvas_but_the_side_is_never_given_up():
    ref = BoundingBox(800, 100, 100, 50)
    box = place((300, 40), ref, "below", canvas=CANVAS, margin=8)
    assert box.right == 960 - 8 and box.top == 166  # slid left, still below
    low = BoundingBox(100, 500, 100, 30)
    assert place((100, 40), low, "below", canvas=CANVAS).top == 546  # off the canvas: reported, not hidden


def test_an_unknown_side_or_a_bad_size_is_refused():
    with pytest.raises(ValidationError, match="side"):
        place((10, 10), BoundingBox(0, 0, 10, 10), "under")
    with pytest.raises(ValidationError, match="size"):
        place((0, 10), BoundingBox(0, 0, 10, 10), "below")


def test_clear_is_a_no_op_when_nothing_is_covered():
    box = BoundingBox(100, 100, 50, 20)
    assert clear(box, [BoundingBox(300, 300, 10, 10)], canvas=CANVAS) == box


def test_clear_moves_the_least_distance_off_every_obstacle_and_stays_on_the_canvas():
    # Two equations stacked on each other, as a model placed them at y 130 and 236 with size 40.
    first = BoundingBox(636, 130, 300, 120)
    second = BoundingBox(636, 236, 300, 60)
    moved = clear(second, [first], canvas=CANVAS, margin=8)
    assert not overlaps(moved, BoundingBox(first.x - 8, first.y - 8, first.width + 16, first.height + 16))
    assert moved.top == first.bottom + 8 and moved.left == 636  # straight down, the shortest way out
    assert 0 <= moved.left and moved.right <= 960 and 0 <= moved.top and moved.bottom <= 540


def test_clear_gets_past_several_obstacles_at_once():
    obstacles = [BoundingBox(0, 0, 960, 200), BoundingBox(0, 300, 960, 240), BoundingBox(0, 200, 400, 100)]
    moved = clear(BoundingBox(300, 180, 200, 60), obstacles, canvas=CANVAS, margin=4)
    assert moved is not None and moved.left >= 404 and 204 <= moved.top and moved.bottom <= 296


def test_clear_returns_none_when_there_is_no_room():
    assert clear(BoundingBox(10, 10, 100, 100), [BoundingBox(0, 0, 960, 540)], canvas=CANVAS) is None


def test_shift_to_moves_a_drawable_so_its_measured_bounds_start_at_a_point():
    text = Text(text="Area = 8/3", position=Point(0, 0), font_scale=0.8, color=Color(20, 20, 20))
    shift_to(text, 200, 300)
    box = text.get_bounds()
    assert (round(box.x, 6), round(box.y, 6)) == (200, 300)


def test_placed_text_never_touches_the_diagram_it_is_placed_by():
    tutorial = Tutorial(Scene(*CANVAS))
    from tutordraw.kits import Axes
    graph = Axes(tutorial, box=(110, 40, 560, 440), x_range=(-0.5, 2.5), y_range=(-0.5, 5), grid=True)
    note = Text(text="The area under y = x^2", position=Point(0, 0), font_scale=0.8, color=Color(20, 20, 20))
    size = (note.get_bounds().width, note.get_bounds().height)
    box = place(size, graph.group.get_bounds(), "beside", canvas=CANVAS)
    shift_to(note, box.x, box.y)
    assert not overlaps(note.get_bounds(), graph.group.get_bounds())

"""The equation kit: LaTeX typeset by ziamath into DrawCV paths, in named pieces."""

import sys

import numpy as np
import pytest
from drawcv import Color, Path, Scene

from tutordraw import Tutorial, ValidationError

pytest.importorskip("ziamath")
from tutordraw.kits import Equation  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")


def lesson():
    return Tutorial(Scene(700, 300, background=Color.white()))


@pytest.fixture
def pythagoras():
    return Equation(lesson(), [("a_squared", "a^2"), "+", ("b_squared", "b^2"), "=", ("c_squared", "c^2")],
                    position=(50, 60), size=40, name="theorem")


def test_pieces_are_paths_left_to_right_on_one_baseline(pythagoras):
    names = [t.name for t in pythagoras.parts]
    assert names == ["a_squared", "theorem_part2", "b_squared", "theorem_part4", "c_squared"]
    boxes = [t.drawable.get_bounds() for t in pythagoras.parts]
    assert all(isinstance(t.drawable, Path) for t in pythagoras.parts)
    assert all(left.right < right.left for left, right in zip(boxes, boxes[1:]))  # no overlaps
    assert boxes[0].left == pytest.approx(50, abs=3) and min(b.top for b in boxes) >= 60 - 1
    # a, b and c sit on the same baseline, so their lowest ink agrees.
    lows = [boxes[i].bottom for i in (0, 2, 4)]
    assert max(lows) - min(lows) < 1.5
    assert pythagoras.equation.name == "theorem" and pythagoras.part(5) is pythagoras.parts[4]
    assert pythagoras.width == pytest.approx(boxes[-1].right - 50, abs=4)


def test_a_piece_can_be_recoloured_and_highlighted(pythagoras):
    tutorial = pythagoras.tutorial
    c2 = pythagoras.part("c_squared")
    step = tutorial.step("Colour")
    step.restyle(c2, fill=(220, 30, 30)).highlight(c2)
    image = tutorial.render_step(0).to_numpy()
    box = c2.drawable.get_bounds()
    region = image[int(box.top):int(box.bottom), int(box.left):int(box.right), :3]
    reddish = (region[..., 2] > 180) & (region[..., 1] < 90) & (region[..., 0] < 90)  # BGR
    assert reddish.sum() > 50
    first = pythagoras.part("a_squared").drawable.get_bounds()
    left = image[int(first.top):int(first.bottom), int(first.left):int(first.right), :3]
    assert not ((left[..., 2] > 180) & (left[..., 1] < 90)).any()  # the rest is untouched
    assert "The c squared turns red" in tutorial.describe(0)


@pytest.mark.parametrize("latex, message", [
    (r"\frac{a", "Cannot"), (r"x^", "Cannot"), (r"\foo{x} + 1", r"Unknown LaTeX command \\foo"),
    ("", "non-empty"), (["x", 3], "piece"), ([], "string or a list"),
])
def test_bad_latex_is_refused_with_the_problem_named(latex, message):
    with pytest.raises(ValidationError, match=message):
        Equation(lesson(), latex, position=(10, 10))


@pytest.mark.parametrize("kwargs", [dict(size=2), dict(size=1000), dict(spacing=-1), dict(position=(1,)),
                                    dict(name="")])
def test_bad_settings_are_refused(kwargs):
    options = dict(position=(10, 10))
    options.update(kwargs)
    with pytest.raises(ValidationError):
        Equation(lesson(), "x", **options)


def test_missing_extra_names_the_install_command(monkeypatch):
    monkeypatch.setitem(sys.modules, "ziamath", None)
    with pytest.raises(ValidationError, match=r'pip install "tutordraw\[math\]"'):
        Equation(lesson(), "x", position=(0, 0))


def test_unknown_piece_names_are_listed(pythagoras):
    with pytest.raises(ValidationError, match="a_squared, theorem_part2"):
        pythagoras.part("hypotenuse")
    with pytest.raises(ValidationError, match="from 1 to 5"):
        pythagoras.part(6)


def test_equations_save_load_and_reattach(pythagoras, tmp_path):
    tutorial = pythagoras.tutorial
    tutorial.step("Show").highlight(pythagoras.part("b_squared"))
    loaded = Tutorial.load_json(tutorial.save_json(tmp_path / "theorem.tutordraw.json"))
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    again = Equation.find(loaded, "theorem")
    assert [t.name for t in again.parts] == [t.name for t in pythagoras.parts]
    assert "<path" in loaded.to_svg(0)


def test_saved_equations_open_without_the_math_extra(pythagoras, tmp_path, monkeypatch):
    tutorial = pythagoras.tutorial
    tutorial.step("Show")
    path = tutorial.save_json(tmp_path / "theorem.tutordraw.json")
    expected = tutorial.render_step(0).to_numpy()
    monkeypatch.setitem(sys.modules, "ziamath", None)  # as if never installed
    loaded = Tutorial.load_json(path)
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), expected)
    assert [t.name for t in Equation.find(loaded, "theorem").parts][0] == "a_squared"

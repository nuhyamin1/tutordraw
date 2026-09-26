"""The browser player, driven in a real headless Chromium.

The rest of the suite checks what Python sends the player (`web_step`); this
checks what the player does with it: timed reveals, draw-on, fade-in, captions,
tweens and prompt taps, at exact moments picked with the public
`seek(index, time)`. Needs Playwright (`pip install playwright` and
`python -m playwright install chromium`); skipped without it, unless
TUTORDRAW_REQUIRE_BROWSER=1, which CI sets so a missing browser cannot pass.
"""

import os

import pytest
from drawcv import Circle, Color, FillStyle, Point, Rectangle, Scene

from tutordraw import Theme, Tutorial

pytestmark = pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")
REQUIRED = os.environ.get("TUTORDRAW_REQUIRE_BROWSER") == "1"


@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if REQUIRED:
            raise
        pytest.skip("Playwright is not installed")
    with sync_playwright() as playwright:
        try:
            launched = playwright.chromium.launch()
        except Exception as exc:  # no browser downloaded on this host
            if REQUIRED:
                raise
            pytest.skip(f"Chromium is not available: {exc}")
        yield launched
        launched.close()


def build():
    scene = Scene(640, 360, background=Color(245, 247, 250))
    ball = Circle(center=Point(160, 180), radius=40, fill=FillStyle(color=Color(80, 120, 200)))
    box = Rectangle(position=Point(420, 140), width=90, height=80, fill=FillStyle(color=Color(200, 150, 90)))
    scene.add(ball)
    scene.add(box)
    lesson = Tutorial(scene, title="Player", theme=Theme(fade_seconds=0.5))
    t_ball, t_box = lesson.target(ball, name="ball"), lesson.target(box, name="box")
    label = t_ball.label("Ball", anchor="top")
    first = lesson.step("Reveal", duration=4).show(label, at=1, draw=True)
    first.narrate("Here is a ball. It is blue.", rate=2)
    moving = lesson.step("Move", duration=2).animate().restyle(t_ball, move=(120, 0))
    moving.caption("The ball rolls right.", at=0.5, until=1.5)
    lesson.step("Ask", duration=1).ask("Which one is the box?", t_box)
    return lesson, label


@pytest.fixture
def page(browser, tmp_path):
    lesson, label = build()
    path = lesson.export_web(tmp_path / "lesson.html")
    page = browser.new_page(viewport={"width": 900, "height": 700})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(path.as_uri())
    page.wait_for_function("typeof player !== 'undefined' && player.steps.length === 3")
    page.evaluate("player.pause()")
    yield page, lesson, label
    assert errors == []
    page.close()


def at(page, index, time):
    page.evaluate(f"player.seek({index}, {time})")


def timed(page, owner):
    """Visibility, opacity and stroke dash offset of each timed group of an annotation."""
    return page.evaluate("""owner => [...document.querySelectorAll('[data-td-at]')]
        .filter(g => g.querySelector(`[data-drawcv-id^="td-${owner}-"]`) || (g.getAttribute('data-drawcv-id') || '').startsWith(`td-${owner}-`))
        .map(g => ({at: +g.getAttribute('data-td-at'), visibility: g.style.visibility,
                    opacity: g.style.opacity, dash: [...g.querySelectorAll('*')].map(e => e.style.strokeDashoffset).find(d => d) || ''}))""",
                         owner)


def test_the_bundle_loads_every_step(page):
    page, lesson, _ = page
    assert page.locator(".td-dot").count() == len(lesson.steps)
    assert page.text_content(".td-title") == "1. Reveal"


def test_a_delayed_label_draws_on_then_fades_in(page):
    page, lesson, label = page
    draw, fade = lesson.theme.draw_seconds, lesson.theme.fade_seconds
    at(page, 0, 0.5)
    assert all(g["visibility"] == "hidden" for g in timed(page, label.id))
    at(page, 0, 1 + draw / 2)
    leader, *rest = sorted(timed(page, label.id), key=lambda g: g["at"])
    assert leader["visibility"] == "" and float(leader["dash"]) > 0  # half drawn
    assert all(g["visibility"] == "hidden" for g in rest)  # the panel waits for the stroke
    at(page, 0, 1 + draw + fade / 2)
    panel = [g for g in timed(page, label.id) if g["at"] == pytest.approx(1 + draw)]
    assert panel and all(0.3 < float(g["opacity"]) < 0.7 for g in panel)  # half faded in
    at(page, 0, 4)
    assert all(g["visibility"] == "" and g["opacity"] == "" for g in timed(page, label.id))


def test_narration_captions_follow_the_voice_word_by_word(page):
    page, _, _ = page
    at(page, 0, 0.7)  # the second word, "is", is being said
    words = page.evaluate("[...document.querySelectorAll('.td-caption span')].map(s => [s.textContent.trim(), s.className])")
    assert words == [["Here", "said"], ["is", "now"], ["a", ""], ["ball.", ""]]
    at(page, 0, 2.2)
    assert page.text_content(".td-caption").split() == ["It", "is", "blue."]


def test_written_captions_show_whole_and_only_in_their_time(page):
    page, _, _ = page
    at(page, 1, 0.2)
    assert page.text_content(".td-caption") == ""
    at(page, 1, 1.0)
    assert page.text_content(".td-caption") == "The ball rolls right."
    at(page, 1, 1.6)
    assert page.text_content(".td-caption") == ""


def test_an_animated_step_moves_the_ball_between_its_ends(page):
    page, lesson, _ = page
    ball = lesson.get_target("ball").drawable_id

    def ball_x():
        return page.evaluate(f"""(() => {{ const r = document.querySelector('[data-drawcv-id="{ball}"]')
            .getBoundingClientRect(), f = document.querySelector('.td-frame').getBoundingClientRect();
            return (r.left + r.width / 2 - f.left) / f.width * {lesson.scene.width}; }})()""")

    at(page, 1, 0)
    start = ball_x()
    at(page, 1, 1)
    middle = ball_x()
    at(page, 1, 2)
    end = ball_x()
    assert start == pytest.approx(160, abs=2) and end == pytest.approx(280, abs=2)
    assert start + 20 < middle < end - 20


def test_a_tap_is_judged_as_python_judges_it(page):
    page, lesson, _ = page
    at(page, 2, 1)  # the question is asked when the step ends
    assert page.is_visible(".td-prompt") and page.text_content(".td-ask") == "Which one is the box?"
    frame = page.locator(".td-frame").bounding_box()
    scale = frame["width"] / lesson.scene.width

    def tap(x, y):
        page.mouse.click(frame["x"] + x * scale, frame["y"] + y * scale)
        return page.text_content(".td-feedback"), page.get_attribute(".td-feedback", "class")

    feedback, css = tap(160, 180)  # the ball
    assert "wrong" in css and feedback == lesson.check_answer(2, 160, 180).feedback
    feedback, css = tap(465, 180)  # the box
    assert "right" in css and feedback == lesson.check_answer(2, 465, 180).feedback
    assert lesson.check_answer(2, 465, 180).correct

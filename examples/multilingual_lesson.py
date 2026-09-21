"""Teach the same diagram in English, Thai and Arabic.

Thai and Arabic need DrawCV's font engine and a font file you supply:
    pip install "tutordraw[typography]"
Set TUTORDRAW_FONT to a .ttf or .otf covering the scripts you want. Without
one the example still runs and writes the English step only.
"""

import os
from pathlib import Path
import sys

from drawcv import Circle, Color, FillStyle, Point, Scene, StrokeStyle, Text
from tutordraw import Theme, TutorDrawError, Tutorial

# Fonts covering Thai and Arabic that are commonly present. Supply your own with
# TUTORDRAW_FONT; Noto Sans Thai and Noto Naskh Arabic are good free choices.
CANDIDATES = [
    os.environ.get("TUTORDRAW_FONT"),
    r"C:\Windows\Fonts\tahoma.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]

LESSONS = [
    ("English", "Nucleus", "The nucleus holds the cell's DNA.", False),
    ("Thai", "\u0e19\u0e34\u0e27\u0e40\u0e04\u0e25\u0e35\u0e22\u0e2a",
     "\u0e19\u0e34\u0e27\u0e40\u0e04\u0e25\u0e35\u0e22\u0e2a\u0e40\u0e01\u0e47\u0e1a DNA "
     "\u0e02\u0e2d\u0e07\u0e40\u0e0b\u0e25\u0e25\u0e4c\u0e40\u0e2d\u0e32\u0e44\u0e27\u0e49", True),
    ("Arabic", "\u0627\u0644\u0646\u0648\u0627\u0629",
     "\u0627\u0644\u0646\u0648\u0627\u0629 \u062a\u062d\u0641\u0638 \u0627\u0644\u062d\u0645\u0636 "
     "\u0627\u0644\u0646\u0648\u0648\u064a \u0644\u0644\u062e\u0644\u064a\u0629", True),
]


def find_font():
    for path in CANDIDATES:
        if path and Path(path).is_file():
            return path
    return None


def build_tutorial(font=None) -> Tutorial:
    scene = Scene(900, 420, background=Color(246, 249, 253))
    scene.add(Text(text="ONE DIAGRAM, THREE LANGUAGES", position=Point(40, 30),
                   font_scale=0.85, thickness=2, color=Color(28, 43, 65)))
    cell = Circle(center=Point(260, 250), radius=120,
                  fill=FillStyle(color=Color(213, 234, 230)),
                  stroke=StrokeStyle(color=Color(74, 134, 121), width=3))
    nucleus = Circle(center=Point(250, 235), radius=48,
                     fill=FillStyle(color=Color(131, 151, 218)),
                     stroke=StrokeStyle(color=Color(73, 89, 151), width=3))
    scene.add(cell)
    scene.add(nucleus)

    lesson = Tutorial(scene, title="Multilingual cell", font=font,
                      theme=Theme(font_scale=0.75, padding=14))
    target = lesson.target(nucleus, name="nucleus")
    for title, label, sentence, needs_font in LESSONS:
        if needs_font and font is None:
            continue
        step = lesson.step(title).show(target.label(label, anchor="top", gap=52))
        step.highlight(target).dim_others(target)
        step.explain(target, sentence, gap=190, max_width=300)
    return lesson


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    font = find_font()
    if font is None:
        print("No font found for Thai or Arabic. Set TUTORDRAW_FONT to a .ttf "
              "covering them and install: pip install \"tutordraw[typography]\"")
    output = Path(__file__).resolve().parents[1] / "output" / "multilingual"
    # A host can have a font but not the engine, so the export has to be inside
    # the guard too: shaped text only fails once it is actually rendered.
    for candidate in (font, None):
        lesson = build_tutorial(candidate)
        try:
            paths = lesson.export_steps(output, overwrite=True)
        except TutorDrawError as error:
            # export_steps wraps a render failure, so report the real cause.
            print(f"Falling back to English only: {error.__cause__ or error}")
            continue
        print(f"Saved {len(paths)} language step(s) in {output}"
              + (f" using {Path(candidate).name}" if candidate else " (English only)"))
        return


if __name__ == "__main__":
    main()

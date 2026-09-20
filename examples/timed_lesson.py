"""Time a saved lesson and preview either side of its first hard cut."""

from pathlib import Path
from runpy import run_path

from tutordraw import Tutorial


def main():
    build = run_path(str(Path(__file__).with_name("cell_tutorial.py")))["build_tutorial"]
    lesson = build()
    lesson.steps[0].set_timing(duration=2, pause=1)
    lesson.steps[1].set_timing(duration=4, pause=1)
    lesson.steps[2].set_timing(duration=2)
    output = Path(__file__).resolve().parents[1] / "output" / "timing"
    lesson.save_json(output / "cell-timed.tutordraw.json", overwrite=True)
    loaded = Tutorial.load_json(output / "cell-timed.tutordraw.json")
    loaded.render_at_time(2.5).save(output / "during-pause.png")
    loaded.render_at_time(3).save(output / "next-step.png")
    # Streaming frame generation; consume frames without retaining a whole video.
    count = sum(1 for _ in loaded.render_frames(fps=2))
    print(f"{loaded.duration:g} seconds; {count} frames at 2 fps. Previews: {output}")


if __name__ == "__main__":
    main()

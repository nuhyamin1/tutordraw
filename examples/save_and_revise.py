"""Save a complete lesson, reopen it, and revise it without rebuilding the drawing."""

from pathlib import Path
from runpy import run_path

from drawcv import Transform
from tutordraw import Tutorial

def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output" / "persistence"
    # Load the companion example by explicit path, including under Python -I.
    build_tutorial = run_path(str(Path(__file__).with_name("cell_tutorial.py")))["build_tutorial"]
    original = build_tutorial()
    original.save_json(output / "cell.tutordraw.json", overwrite=True)
    original.render_step(1).save(output / "before.png")

    # This is also the starting point for a later AI-assisted editing session.
    loaded = Tutorial.load_json(output / "cell.tutordraw.json")
    loaded.get_target("nucleus").drawable.transform = Transform(translation_x=20, translation_y=15)

    # Editable JSON preserves identity while changing the explanatory content.
    document = loaded.to_dict()
    focus_id = loaded.steps[1].id
    focus = next(step for step in document["steps"] if step["id"] == focus_id)
    focus["callouts"][0]["text"] = (
        "The nucleus stores DNA. The label, highlight, and explanation follow it when it moves."
    )
    revised = Tutorial.from_dict(document)
    revised.save_json(output / "cell-revised.tutordraw.json", overwrite=True)
    revised.render_step(1).save(output / "after.png")
    print(f"Saved original/revised lesson files and previews in {output}")


if __name__ == "__main__":
    main()

"""Play a lesson in the browser, whole or streamed one step at a time.

Writes two things for the lever lesson:

- output/web/lever.html: one self-contained page. Open it in any browser.
- output/web/lever.steps.ndjson: one JSON payload per line, exactly what a
  server would send as each step is authored. A page that calls
  player.append(json) for each line as it arrives plays the lesson while the
  rest is still being written. See docs/WEB.md.
"""

import json
from pathlib import Path
import sys

# Reuse the lever lesson next to this file. Added explicitly because isolated
# mode (python -I, as the release check runs examples) leaves the script's own
# folder off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lever_lesson import build_tutorial  # noqa: E402


def main() -> None:
    lesson = build_tutorial()
    output = Path("output/web")
    page = lesson.export_web(output / "lever.html", overwrite=True)
    stream = output / "lever.steps.ndjson"
    with stream.open("w", encoding="utf-8", newline="\n") as lines:
        for index in range(len(lesson.steps)):
            # In a live explainer this line goes out the moment step `index` exists.
            lines.write(json.dumps(lesson.web_step(index), ensure_ascii=False) + "\n")
    print(f"Wrote {page.resolve()} ({page.stat().st_size // 1024} KB) and "
          f"{len(lesson.steps)} streamed steps to {stream.resolve()}")


if __name__ == "__main__":
    main()

"""Run examples in a temporary project using an installed, non-editable package."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="tutordraw-installed-") as directory:
        temporary = Path(directory)
        example_dir = temporary / "examples"
        shutil.copytree(root / "examples", example_dir, ignore=shutil.ignore_patterns("__pycache__"))
        probe = """
from pathlib import Path
from importlib.metadata import version
import sys
import drawcv
import tutordraw
source = Path(sys.argv[1]).resolve() / 'src'
installed = Path(tutordraw.__file__).resolve()
assert not installed.is_relative_to(source), f'Editable source import: {installed}'
assert 'site-packages' in installed.parts, installed
assert tutordraw.__version__ == version('tutordraw')
assert version('pydrawcv') == '0.10.0.post1'
print('Installed:', installed)
print('DrawCV:', drawcv.__file__)
"""
        subprocess.run([sys.executable, "-I", "-c", probe, str(root)], cwd=temporary, check=True)
        for name in ("cell_tutorial.py", "group_focus.py", "save_and_revise.py",
                     "timed_lesson.py", "video_lesson.py"):
            subprocess.run([sys.executable, "-I", "-W", "error", str(example_dir / name)],
                           cwd=temporary, check=True)
        verify = """
from pathlib import Path
import cv2
paths = sorted(Path('output/cell').glob('step-*.png'))
assert len(paths) == 3, paths
paths.append(Path('output/group-focus.png'))
paths.extend([Path('output/persistence/before.png'), Path('output/persistence/after.png')])
paths.extend([Path('output/timing/during-pause.png'), Path('output/timing/next-step.png')])
for path in paths:
    image = cv2.imread(str(path))
    assert image is not None and image.size > 0, path
from tutordraw import Tutorial
saved = Tutorial.load_json('output/persistence/cell-revised.tutordraw.json')
assert saved.get_target('nucleus').drawable.transform.translation_x == 20
timed = Tutorial.load_json('output/timing/cell-timed.tutordraw.json')
assert timed.duration == 10 and timed.step_at_time(3) == 1
# The video example writes nothing when the host provides no usable codec.
videos = sorted(Path('output/video').glob('cell-lesson.*'))
for path in videos:
    capture = cv2.VideoCapture(str(path))
    try:
        assert capture.isOpened(), path
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 120, path
    finally:
        capture.release()
print(f'Verified eight PNGs, {len(videos)} video(s), and reloaded lessons outside the checkout')
"""
        subprocess.run([sys.executable, "-I", "-c", verify], cwd=temporary, check=True)


if __name__ == "__main__":
    main()

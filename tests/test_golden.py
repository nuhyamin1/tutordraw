"""Pin what the canonical lessons look like: layout geometry and pixels.

Two checks per frame, because they fail for different reasons:

- Geometry (panel boxes, leaders, highlights, chosen sides) is compared to
  0.05 px. It is platform-independent and names exactly what moved, so it is
  the precise guard on collision avoidance and layout.
- Pixels are compared with a small tolerance for antialiasing noise between
  platforms and library builds. They catch what geometry cannot: styling,
  dimming, text rendering, stroke width, anything DrawCV itself changes.

After an intended visual change, regenerate and *look at* the new references:

    TUTORDRAW_UPDATE_GOLDEN=1 python -m pytest tests/test_golden.py

On failure the actual frame and a diff image are written to
output/golden-failures/ (or $TUTORDRAW_GOLDEN_OUT) for inspection.
"""

import json
import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from golden_lessons import LESSONS

GOLDEN = Path(__file__).parent / "golden"
UPDATE = os.environ.get("TUTORDRAW_UPDATE_GOLDEN") == "1"
FAILURES = Path(os.environ.get("TUTORDRAW_GOLDEN_OUT",
                               Path(__file__).parent.parent / "output" / "golden-failures"))

# A channel differing by more than this counts as a changed pixel...
CHANNEL_TOLERANCE = 24
# ...and this fraction of changed pixels is allowed. A panel moving by one
# pixel changes its whole perimeter, far more than this.
CHANGED_FRACTION = 0.0002
GEOMETRY_TOLERANCE = 0.05

FRAMES = [(lesson, frame, index, progress)
          for lesson, (_, frames) in LESSONS.items()
          for frame, index, progress in frames]


def _numbers_close(expected, actual, path="") -> list[str]:
    """Structural comparison; returns human-readable differences."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        problems = [f"{path}: keys {sorted(expected)} != {sorted(actual)}"] \
            if expected.keys() != actual.keys() else []
        for key in expected.keys() & actual.keys():
            problems += _numbers_close(expected[key], actual[key], f"{path}.{key}")
        return problems
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: {len(expected)} items != {len(actual)}"]
        problems = []
        for i, (e, a) in enumerate(zip(expected, actual)):
            problems += _numbers_close(e, a, f"{path}[{i}]")
        return problems
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)) \
            and not isinstance(expected, bool):
        return [] if abs(expected - actual) <= GEOMETRY_TOLERANCE else [f"{path}: {expected} != {actual}"]
    return [] if expected == actual else [f"{path}: {expected!r} != {actual!r}"]


# The motion lesson deliberately pins a frame the resolver cannot fully clear.
@pytest.mark.filterwarnings("ignore::tutordraw.errors.LayoutWarning")
@pytest.mark.parametrize("lesson, frame, index, progress", FRAMES,
                         ids=[f"{lesson}-{frame}" for lesson, frame, _, _ in FRAMES])
def test_golden_frame(lesson, frame, index, progress, tmp_path):
    tutorial = LESSONS[lesson][0]()
    composition = tutorial._compose(index, progress)
    geometry = composition.to_dict()
    actual_png = tmp_path / "actual.png"
    tutorial._render(index, progress, False).save(str(actual_png))
    actual = cv2.imread(str(actual_png))

    geometry_path = GOLDEN / f"{lesson}-{frame}.json"
    image_path = GOLDEN / f"{lesson}-{frame}.png"
    if UPDATE:
        GOLDEN.mkdir(exist_ok=True)
        geometry_path.write_text(json.dumps(geometry, indent=1, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
        cv2.imwrite(str(image_path), actual)
        return
    if not geometry_path.exists() or not image_path.exists():
        pytest.fail(f"No reference for {lesson}-{frame}; run with TUTORDRAW_UPDATE_GOLDEN=1 "
                    "and inspect the images it writes to tests/golden/")

    expected = json.loads(geometry_path.read_text(encoding="utf-8"))
    problems = _numbers_close(expected, geometry)

    reference = cv2.imread(str(image_path))
    if reference.shape != actual.shape:
        problems.append(f"image shape {reference.shape} != {actual.shape}")
    else:
        delta = np.abs(reference.astype(np.int16) - actual.astype(np.int16)).max(axis=2)
        changed = int((delta > CHANNEL_TOLERANCE).sum())
        allowed = int(CHANGED_FRACTION * delta.size)
        if changed > allowed:
            problems.append(f"{changed} pixels changed (allowed {allowed})")
            FAILURES.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(FAILURES / f"{lesson}-{frame}-actual.png"), actual)
            heat = np.where(delta[..., None] > CHANNEL_TOLERANCE,
                            np.array([0, 0, 255], np.uint8), (reference // 3).astype(np.uint8))
            cv2.imwrite(str(FAILURES / f"{lesson}-{frame}-diff.png"), heat)
    assert not problems, f"{lesson}-{frame} drifted from its reference:\n  " + "\n  ".join(problems)


def test_every_reference_has_a_lesson():
    """A stale reference would otherwise sit unchecked forever."""
    expected = {f"{lesson}-{frame}" for lesson, frame, _, _ in FRAMES}
    present = {path.stem for path in GOLDEN.glob("*.png")} | {path.stem for path in GOLDEN.glob("*.json")}
    assert present <= expected, f"Orphaned references: {sorted(present - expected)}"

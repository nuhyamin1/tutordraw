"""Encode the timed cell lesson to a video file and decode it back to check it."""

from pathlib import Path
from runpy import run_path

import cv2

from tutordraw import VideoExportError

# Tried in order. Which codecs an OpenCV build provides depends on the host.
CANDIDATES = (("mp4v", ".mp4"), ("MJPG", ".avi"), ("XVID", ".avi"))
FPS = 12


def main():
    build = run_path(str(Path(__file__).with_name("cell_tutorial.py")))["build_tutorial"]
    lesson = build()
    lesson.steps[0].set_timing(duration=2, pause=1)
    lesson.steps[1].set_timing(duration=4, pause=1)
    lesson.steps[2].set_timing(duration=2)
    output = Path(__file__).resolve().parents[1] / "output" / "video"
    for fourcc, suffix in CANDIDATES:
        destination = output / f"cell-lesson{suffix}"
        try:
            lesson.export_video(destination, fps=FPS, fourcc=fourcc, overwrite=True)
        except VideoExportError as error:
            print(f"Codec {fourcc} unavailable here: {error}")
            continue
        break
    else:
        print(f"No codec among {[c for c, _ in CANDIDATES]} is available on this host; "
              "nothing was written. Use export_steps for PNG output instead.")
        return
    capture = cv2.VideoCapture(str(destination))
    try:
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    finally:
        capture.release()
    print(f"{lesson.duration:g} seconds encoded as {fourcc} at {FPS} fps: "
          f"{frames} frames of {width}x{height}. Video: {destination}")


if __name__ == "__main__":
    main()

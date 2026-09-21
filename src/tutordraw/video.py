"""Encode the tutorial frame iterator into one video file using OpenCV.

DrawCV's VideoRenderer requires an actual Scene (it calls Scene.render_at_time
and rejects anything else with isinstance), and DrawCV exposes no encoder that
accepts a sequence of frames. A tutorial is not a Scene, so TutorDraw owns this
small writer adapter instead of pretending otherwise. See docs/VIDEO.md.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

import cv2

from .errors import ValidationError, VideoExportError

if TYPE_CHECKING:
    from .tutorial import Tutorial


def _fourcc_code(fourcc: str) -> int:
    if (not isinstance(fourcc, str) or len(fourcc) != 4
            or not fourcc.isascii() or not fourcc.isprintable()):
        raise ValidationError("fourcc must be exactly four printable ASCII characters")
    return cv2.VideoWriter_fourcc(*fourcc)


def export_video(tutorial: Tutorial, path: str | Path, *, fps: int, fourcc: str,
                 overwrite: bool) -> Path:
    if not isinstance(overwrite, bool):
        raise ValidationError("overwrite must be a boolean")
    code = _fourcc_code(fourcc)
    # Rejects invalid fps and empty lessons before touching the filesystem.
    frames = tutorial.render_frames(fps=fps, alpha=False)
    destination = Path(path)
    if destination.is_symlink() or (destination.exists()
                                    and (not overwrite or not destination.is_file())):
        raise FileExistsError(f"Export destination already exists: {destination}")
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    # Keep the real suffix: OpenCV selects the container from the file extension.
    fd, name = tempfile.mkstemp(prefix=".tutordraw-", suffix=destination.suffix, dir=parent)
    os.close(fd)
    temporary = Path(name)
    written = 0
    try:
        writer = None
        size: tuple[int, int] | None = None
        try:
            for canvas in frames:
                buffer = canvas.buffer
                # A numpy dtype compares equal to its name, so numpy stays unimported.
                if buffer.dtype != "uint8" or buffer.ndim != 3 or buffer.shape[2] != 3:
                    raise ValueError("video frames must be 8-bit three-channel BGR images")
                frame_size = (buffer.shape[1], buffer.shape[0])
                if writer is None:
                    size = frame_size
                    # Opened only once a frame exists, so a render failure opens no encoder.
                    writer = cv2.VideoWriter(str(temporary), code, float(fps), size)
                    if not writer.isOpened():
                        raise VideoExportError(
                            "OpenCV could not open a video writer; this host may not "
                            "provide this codec or container", destination, fourcc, 0)
                elif frame_size != size:
                    raise ValueError(f"frame size changed from {size} to {frame_size}")
                writer.write(buffer)
                written += 1
        finally:
            if writer is not None:
                writer.release()
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise VideoExportError("The codec accepted every frame but wrote no data",
                                   destination, fourcc, written)
        if overwrite:
            os.replace(temporary, destination)
        else:
            # Exclusive creation also handles a collision after preflight.
            created = False
            try:
                with destination.open("xb") as output:
                    created = True
                    with temporary.open("rb") as source:
                        shutil.copyfileobj(source, output)
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
    except VideoExportError:
        raise
    except Exception as exc:
        raise VideoExportError(f"Video export failed: {exc}", destination, fourcc, written) from exc
    finally:
        temporary.unlink(missing_ok=True)
    return destination

from copy import deepcopy
import math
from pathlib import Path
from types import SimpleNamespace

import cv2
from drawcv import Circle, Color, FillStyle, Point, Scene
import numpy as np
import pytest

from tutordraw import Tutorial, ValidationError, VideoExportError
import tutordraw.video as video

# Tried in order by the real-encoding test; availability is host specific.
CANDIDATES = (("mp4v", ".mp4"), ("MJPG", ".avi"), ("XVID", ".avi"))
FPS = 4


@pytest.fixture
def lesson():
    """Two one-second steps that render obviously different images."""
    scene = Scene(320, 240, background=Color.white())
    left = Circle(center=Point(90, 120), radius=40, fill=FillStyle(color=Color(20, 60, 200)))
    right = Circle(center=Point(230, 120), radius=40, fill=FillStyle(color=Color(210, 90, 40)))
    scene.add(left)
    scene.add(right)
    tutorial = Tutorial(scene)
    first = tutorial.target(left, name="left")
    second = tutorial.target(right, name="right")
    tutorial.step("First", duration=1).dim_others(first, opacity=0.05).highlight(first)
    tutorial.step("Second", duration=1).dim_others(second, opacity=0.05).highlight(second)
    return tutorial


class StubWriter:
    """Records encoder use and appends a payload per frame, like a real writer."""

    def __init__(self, path, code, fps, size, *, opened=True, fail_after=None,
                 payload=b"frame", on_write=None):
        self.path, self.code, self.fps, self.size = Path(path), code, fps, size
        self.writes, self.released = 0, False
        self._opened, self._fail_after = opened, fail_after
        self._payload, self._on_write = payload, on_write

    def isOpened(self):
        return self._opened

    def write(self, frame):
        if self._fail_after is not None and self.writes >= self._fail_after:
            raise RuntimeError("encoder died")
        self.writes += 1
        if self._on_write is not None:
            self._on_write()
        with self.path.open("ab") as output:
            output.write(self._payload)

    def release(self):
        self.released = True


@pytest.fixture
def stub(monkeypatch):
    """Replace only the cv2 reference inside tutordraw.video, keeping real fourcc codes."""
    created = []

    def install(**options):
        def factory(path, code, fps, size):
            writer = StubWriter(path, code, fps, size, **options)
            created.append(writer)
            return writer

        monkeypatch.setattr(video, "cv2", SimpleNamespace(
            VideoWriter_fourcc=cv2.VideoWriter_fourcc, VideoWriter=factory))
        return created

    return install


def leftovers(directory):
    return list(Path(directory).glob(".tutordraw-*"))


def raising(*args, **kwargs):
    raise RuntimeError("boom")


def test_successful_export_streams_every_frame(lesson, stub, tmp_path):
    created = stub()
    destination = tmp_path / "lesson.mp4"
    original = deepcopy(lesson.scene.to_dict())
    history = lesson.scene.history.undo_count

    assert lesson.export_video(destination, fps=FPS) == destination

    writer, = created
    assert writer.writes == math.ceil(lesson.duration * FPS) == 8
    assert writer.size == (320, 240) and writer.fps == 4.0 and writer.released
    assert destination.read_bytes() == b"frame" * 8
    assert not leftovers(tmp_path)
    # Rendering a whole video still leaves the source drawing untouched.
    assert lesson.scene.to_dict() == original
    assert lesson.scene.history.undo_count == history


def test_unavailable_codec_reports_and_preserves_existing_file(lesson, stub, tmp_path):
    created = stub(opened=False)
    destination = tmp_path / "lesson.mp4"
    destination.write_bytes(b"old movie")

    with pytest.raises(VideoExportError) as caught:
        lesson.export_video(destination, fps=FPS, fourcc="XVID", overwrite=True)

    error = caught.value
    assert error.fourcc == "XVID" and error.frames_written == 0
    assert "codec" in str(error)
    assert created[0].released and created[0].writes == 0
    assert destination.read_bytes() == b"old movie"
    assert not leftovers(tmp_path)


def test_encoder_failure_midstream_releases_and_writes_nothing(lesson, stub, tmp_path):
    created = stub(fail_after=3)
    destination = tmp_path / "lesson.mp4"

    with pytest.raises(VideoExportError) as caught:
        lesson.export_video(destination, fps=FPS)

    assert caught.value.frames_written == 3
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert created[0].released
    assert not destination.exists()
    assert not leftovers(tmp_path)


def test_render_failure_never_opens_a_writer(lesson, stub, tmp_path, monkeypatch):
    created = stub()
    monkeypatch.setattr(lesson, "render_step", raising)

    with pytest.raises(VideoExportError) as caught:
        lesson.export_video(tmp_path / "lesson.mp4", fps=FPS)

    assert created == [] and caught.value.frames_written == 0
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert not leftovers(tmp_path)


def test_empty_encoder_output_is_a_failure(lesson, stub, tmp_path):
    stub(payload=b"")
    destination = tmp_path / "lesson.mp4"

    with pytest.raises(VideoExportError, match="wrote no data"):
        lesson.export_video(destination, fps=FPS)

    assert not destination.exists()
    assert not leftovers(tmp_path)


def test_replace_failure_preserves_existing_file(lesson, stub, tmp_path, monkeypatch):
    stub()
    destination = tmp_path / "lesson.mp4"
    destination.write_bytes(b"old movie")

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(video.os, "replace", fail)
    with pytest.raises(VideoExportError):
        lesson.export_video(destination, fps=FPS, overwrite=True)

    assert destination.read_bytes() == b"old movie"
    assert not leftovers(tmp_path)


def test_collision_created_after_preflight_is_not_overwritten(lesson, stub, tmp_path):
    destination = tmp_path / "lesson.mp4"

    def intrude():
        if not destination.exists():
            destination.write_bytes(b"another writer")

    stub(on_write=intrude)
    with pytest.raises(VideoExportError) as caught:
        lesson.export_video(destination, fps=FPS)

    assert isinstance(caught.value.__cause__, FileExistsError)
    assert destination.read_bytes() == b"another writer"
    assert not leftovers(tmp_path)


def test_existing_destination_and_symlinks_are_refused(lesson, stub, tmp_path):
    stub()
    destination = tmp_path / "lesson.mp4"
    destination.write_bytes(b"old movie")
    with pytest.raises(FileExistsError):
        lesson.export_video(destination, fps=FPS)
    assert destination.read_bytes() == b"old movie"

    link = tmp_path / "link.mp4"
    try:
        link.symlink_to(destination)
    except (OSError, NotImplementedError):
        pytest.skip("This host does not permit creating symlinks")
    for overwrite in (False, True):
        with pytest.raises(FileExistsError):
            lesson.export_video(link, fps=FPS, overwrite=overwrite)
    assert destination.read_bytes() == b"old movie"


@pytest.mark.parametrize("fps", [0, -1, True, 2.5, "30", None])
def test_invalid_frame_rate_rejected_before_any_file_work(lesson, stub, tmp_path, fps):
    created = stub()
    with pytest.raises(ValidationError):
        lesson.export_video(tmp_path / "lesson.mp4", fps=fps)
    assert created == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fourcc", ["", "mp4", "toolong", "mp4\n", "mp4é", b"mp4v", None, 1234])
def test_invalid_fourcc_rejected(lesson, stub, tmp_path, fourcc):
    created = stub()
    with pytest.raises(ValidationError):
        lesson.export_video(tmp_path / "lesson.mp4", fps=FPS, fourcc=fourcc)
    assert created == [] and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("overwrite", [1, "yes", None])
def test_invalid_overwrite_rejected(lesson, stub, tmp_path, overwrite):
    stub()
    with pytest.raises(ValidationError):
        lesson.export_video(tmp_path / "lesson.mp4", fps=FPS, overwrite=overwrite)
    assert list(tmp_path.iterdir()) == []


def test_empty_lesson_cannot_be_exported(tmp_path, stub):
    stub()
    with pytest.raises(ValidationError):
        Tutorial(Scene(120, 90)).export_video(tmp_path / "empty.mp4")
    assert list(tmp_path.iterdir()) == []


def test_real_encoding_round_trips_through_a_decoder(lesson, tmp_path):
    """Encode with a codec this host actually provides, then decode and compare."""
    for index, (fourcc, suffix) in enumerate(CANDIDATES):
        destination = tmp_path / f"lesson{index}{suffix}"
        try:
            lesson.export_video(destination, fps=FPS, fourcc=fourcc)
        except VideoExportError:
            continue
        break
    else:
        pytest.skip(f"No codec among {CANDIDATES} is available on this host")

    capture = cv2.VideoCapture(str(destination))
    try:
        assert capture.isOpened()
        assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 8
        assert (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) == (320, 240)
        decoded = []
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            decoded.append(frame)
    finally:
        capture.release()

    assert len(decoded) == 8
    expected = [lesson.render_step(0).buffer, lesson.render_step(1).buffer]
    # Lossy codecs forbid exact comparison; each frame must still match its step.
    for position, frame in enumerate(decoded):
        step = 0 if position < 4 else 1
        assert frame.shape == expected[step].shape
        near = np.abs(frame.astype(int) - expected[step].astype(int)).mean()
        far = np.abs(frame.astype(int) - expected[1 - step].astype(int)).mean()
        assert near < 6 and far > 4 * max(near, 1)
    # The hard cut at t=1s falls between decoded frames 3 and 4.
    assert np.abs(decoded[3].astype(int) - decoded[4].astype(int)).mean() > 5
    assert not leftovers(tmp_path)

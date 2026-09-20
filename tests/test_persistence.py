from copy import deepcopy
import json
from importlib.resources import files

import numpy as np
import pytest
from drawcv import Circle, Color, FillStyle, Group, ImageObject, Point, Scene, Transform

from tutordraw import LessonFormatError, Theme, Tutorial, ValidationError


@pytest.fixture
def lesson():
    scene = Scene(900, 550, background=Color.white())
    child = Circle(center=Point(200, 260), radius=40,
                   fill=FillStyle(color=Color(60, 110, 200)))
    sibling = Circle(center=Point(330, 260), radius=25,
                     fill=FillStyle(color=Color(80, 160, 80)))
    scene.add(Group(children=[child, sibling], opacity=0.9,
                    transform=Transform(translation_x=15, rotation=10)))
    tutorial = Tutorial(scene, title="A saved lesson", theme=Theme(padding=12, font_scale=0.65))
    target = tutorial.target(child, name="subject")
    other = tutorial.target(sibling)
    label = target.label("Subject", anchor="top", gap=40)
    unused = other.label("Defined but hidden")
    first = tutorial.step("Focus").show(label).highlight(target).dim_others(target)
    first.explain(target, "A wrapped explanation.\nSecond paragraph.", gap=210, max_width=250)
    tutorial.step("Review").show(label)
    return tutorial, target, unused


def test_round_trip_preserves_every_definition_identity_and_pixels(lesson):
    original = lesson[0]
    before = deepcopy(original.scene.to_dict())
    history = original.scene.history.undo_count
    text = original.to_json()
    restored = Tutorial.from_json(text)
    assert restored.to_json() == text
    assert [s.id for s in restored.steps] == [s.id for s in original.steps]
    assert [t.id for t in restored.targets] == [t.id for t in original.targets]
    assert [l.id for l in restored.labels] == [l.id for l in original.labels]
    assert restored.steps[0].callouts[0].id == original.steps[0].callouts[0].id
    assert restored.steps[0].labels[0] is restored.steps[1].labels[0]
    assert len(restored.labels) == 2  # Unshown definitions survive.
    assert restored.theme == original.theme
    for index in (1, 0, 1):
        np.testing.assert_array_equal(restored.render_step(index).to_numpy(), original.render_step(index).to_numpy())
    assert original.scene.to_dict() == before
    assert original.scene.history.undo_count == history


def test_reopen_edit_drawing_and_explanation_without_affecting_original(lesson, tmp_path):
    original = lesson[0]
    file = original.save_json(tmp_path / "nested" / "lesson.tutordraw.json")
    with pytest.raises(FileExistsError):
        original.save_json(file)
    loaded = Tutorial.load_json(file)
    loaded.get_target("subject").drawable.transform.translation_x += 30
    data = loaded.to_dict()
    data["steps"][0]["callouts"][0]["text"] = "Revised explanation."
    revised = Tutorial.from_dict(data)
    revised.step("New question").explain(revised.get_target("subject"), "What changed?", gap=200)
    revised.save_json(file, overwrite=True)
    assert len(Tutorial.load_json(file).steps) == 3
    assert len(original.steps) == 2
    assert original.steps[0].callouts[0].text != "Revised explanation."
    assert revised.get_target("subject").drawable is not original.get_target("subject").drawable
    assert not np.array_equal(original.render_step(0).to_numpy(), revised.render_step(0).to_numpy())


def test_native_dict_and_scene_metadata_are_detached(lesson):
    tutorial, target, _ = lesson
    target.drawable.metadata = {"nested": [1, 2]}
    data = tutorial.to_dict()
    original = deepcopy(data)
    loaded = Tutorial.from_dict(data)
    loaded.get_target("subject").drawable.metadata["nested"].append(3)
    assert data == original
    assert target.drawable.metadata["nested"] == [1, 2]
    data["labels"][0]["text"] = "Edited document only"
    assert tutorial.labels[0].text == "Subject"


@pytest.mark.parametrize("mutate,match", [
    (lambda d: d.update(format="other"), "format"),
    (lambda d: d.update(schema_version=2), "version"),
    (lambda d: d.update(schema_version=True), "version"),
    (lambda d: d.update(schema_version=1.0), "version"),
    (lambda d: d.update(schema_version="1"), "version"),
    (lambda d: d.update(extra="typo"), "unknown"),
    (lambda d: d.pop("steps"), "missing"),
    (lambda d: d.update(steps={}), "array"),
    (lambda d: d["targets"][0].update(drawable_id="absent"), "missing drawable"),
    (lambda d: d["targets"][1].update(id=d["targets"][0]["id"]), "Duplicate"),
    (lambda d: d["targets"][1].update(drawable_id=d["targets"][0]["drawable_id"]), "duplicate target"),
    (lambda d: d["targets"][1].update(name="subject"), "already in use"),
    (lambda d: d["labels"][0].update(target_id="absent"), "unknown reference"),
    (lambda d: d["labels"][0].update(id=d["targets"][0]["id"]), "Duplicate"),
    (lambda d: d["steps"][0].update(labels=["absent"]), "unknown reference"),
    (lambda d: d["steps"][0]["labels"].append(d["steps"][0]["labels"][0]), "duplicate reference"),
    (lambda d: d["steps"][1].update(id=d["steps"][0]["id"]), "Duplicate"),
    (lambda d: d["steps"][0]["callouts"][0].update(id=d["labels"][0]["id"]), "Duplicate"),
    (lambda d: d["steps"][0]["highlights"][0].update(target_id="absent"), "unknown reference"),
    (lambda d: d["steps"][0]["highlights"].append(deepcopy(d["steps"][0]["highlights"][0])), "duplicate highlight"),
    (lambda d: d["steps"][0]["dim"].update(target_ids=["absent"]), "unknown reference"),
    (lambda d: d["steps"][0]["dim"].update(target_ids=[]), "at least one"),
    (lambda d: d["steps"][0]["dim"].update(opacity=None), "cannot be null"),
    (lambda d: d["labels"][0].update(padding=None), "cannot be null"),
    (lambda d: d["labels"][0].update(font_scale=-1), "font_scale"),
    (lambda d: d["labels"][0].update(leader="yes"), "boolean"),
    (lambda d: d["steps"][0]["callouts"][0].update(max_width=0), "max_width"),
    (lambda d: d["theme"].update(text_color=[300, 0, 0]), "RGB"),
    (lambda d: d["theme"].update(unknown=True), "unknown"),
    (lambda d: d.update(title=5), "title"),
    (lambda d: d.update(scene={}), "Invalid lesson"),
])
def test_malformed_documents_rejected_with_context(lesson, mutate, match):
    data = lesson[0].to_dict()
    mutate(data)
    with pytest.raises(LessonFormatError, match=match):
        Tutorial.from_dict(data)


@pytest.mark.parametrize("text", ["{", "[]", "null", '{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'])
def test_invalid_json_rejected(text):
    with pytest.raises(LessonFormatError):
        Tutorial.from_json(text)


def test_invalid_source_does_not_replace_saved_file(lesson, tmp_path):
    tutorial, target, _ = lesson
    file = tutorial.save_json(tmp_path / "lesson.json")
    before = file.read_bytes()
    tutorial.scene.remove(target.drawable_id)
    with pytest.raises(LessonFormatError, match="Missing drawable"):
        tutorial.save_json(file, overwrite=True)
    assert file.read_bytes() == before
    with pytest.raises(ValidationError, match="Missing target"):
        _ = target.drawable


def test_serialization_rejects_nonfinite_scene_metadata(lesson):
    tutorial, target, _ = lesson
    target.drawable.metadata = {"invalid": float("nan")}
    with pytest.raises(LessonFormatError, match="finite JSON"):
        tutorial.to_json()


def test_save_failure_preserves_existing_file_and_cleans_temporary(lesson, tmp_path, monkeypatch):
    import tutordraw.serialization as storage
    file = lesson[0].save_json(tmp_path / "lesson.json")
    before = file.read_bytes()

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(OSError, match="replace failed"):
        lesson[0].save_json(file, overwrite=True)
    assert file.read_bytes() == before
    assert list(tmp_path.iterdir()) == [file]


def test_exclusive_save_race_does_not_replace_competing_file(lesson, tmp_path, monkeypatch):
    tutorial = lesson[0]
    file = tmp_path / "lesson.json"
    # to_json calls serialization.to_dict directly; intercept the actual serialization boundary.
    import tutordraw.serialization as storage
    original_to_json = storage.to_json

    def racing_json(value):
        text = original_to_json(value)
        file.write_text("another writer", encoding="utf-8")
        return text

    monkeypatch.setattr(storage, "to_json", racing_json)
    with pytest.raises(FileExistsError):
        tutorial.save_json(file)
    assert file.read_text() == "another writer"
    assert list(tmp_path.iterdir()) == [file]


def test_failed_new_save_removes_partial_file(lesson, tmp_path, monkeypatch):
    import tutordraw.serialization as storage

    def fail(source, output):
        output.write(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(storage.shutil, "copyfileobj", fail)
    with pytest.raises(OSError, match="disk full"):
        lesson[0].save_json(tmp_path / "lesson.json")
    assert not list(tmp_path.iterdir())


def test_load_file_errors_and_bom(lesson, tmp_path):
    with pytest.raises(FileNotFoundError):
        Tutorial.load_json(tmp_path / "missing.json")
    file = tmp_path / "lesson.json"
    file.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(LessonFormatError, match="UTF-8"):
        Tutorial.load_json(file)
    file.write_text(lesson[0].to_json(), encoding="utf-8-sig")
    assert Tutorial.load_json(file).title == "A saved lesson"


def test_empty_lesson_and_image_scene_round_trip():
    tutorial = Tutorial(Scene(400, 300), title="Empty is valid")
    assert Tutorial.from_json(tutorial.to_json()).steps == ()
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    image[:, :, 2] = 255
    obj = ImageObject(image=image, position=Point(80, 90))
    tutorial.scene.add(obj)
    target = tutorial.target(obj, name="bitmap")
    tutorial.step("Image").show(target.label("Bitmap"))
    loaded = Tutorial.from_json(tutorial.to_json())
    np.testing.assert_array_equal(loaded.render_step(0).to_numpy(), tutorial.render_step(0).to_numpy())
    with pytest.raises(ValidationError, match="Unknown target"):
        loaded.get_target("missing")


def test_packaged_json_schema_validates_output_and_flags_structural_errors(lesson):
    from jsonschema import Draft202012Validator

    schema = json.loads(files("tutordraw").joinpath("lesson-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    data = lesson[0].to_dict()
    validator.validate(data)
    data["steps"][0]["dim"]["opacity"] = 2
    assert list(validator.iter_errors(data))


def test_duplicate_drawable_ids_and_unsupported_scene_schema_fail(lesson):
    data = lesson[0].to_dict()
    scene = data["scene"]["scene"]
    children = scene["layers"][0]["objects"][0]["children"]
    children[1]["id"] = children[0]["id"]
    with pytest.raises(LessonFormatError):
        Tutorial.from_dict(data)
    data = lesson[0].to_dict()
    data["scene"]["version"] = "999.0"
    data["scene"]["schema_version"] = "999.0"
    with pytest.raises(LessonFormatError):
        Tutorial.from_dict(data)

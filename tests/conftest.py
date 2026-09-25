"""Shared helpers so a schema bump touches one table, not every test file."""

from copy import deepcopy
from importlib.resources import files
import json

from tutordraw.serialization import SCHEMA_VERSION, SUPPORTED_VERSIONS

# The step fields each schema version introduced. Extend this when bumping.
STEP_FIELDS_ADDED = {
    2: ("duration", "pause"),
    3: ("restyles",),
    4: ("easing",),
    5: ("reveals",),
    8: ("marks", "draw", "camera"),
    9: ("narration", "prompt"),
}

# The same, for highlight fields, which live inside each step.
HIGHLIGHT_FIELDS_ADDED = {
    8: ("at", "draw", "shape"),
}

# The same, for theme fields, which live outside the steps.
THEME_FIELDS_ADDED = {
    6: ("avoid_collisions", "collision_margin"),
    8: ("draw_seconds", "halo_width"),
}

# The same, for label and callout fields, which appear in two places.
ANNOTATION_FIELDS_ADDED = {
    7: ("box",),
}

# The same, for restyle fields, which live inside each step.
RESTYLE_FIELDS_ADDED = {
    10: ("via",),
}

LEGACY_VERSIONS = tuple(v for v in SUPPORTED_VERSIONS if v != SCHEMA_VERSION)


def packaged_schema(version: int = SCHEMA_VERSION) -> dict:
    """Load a JSON Schema from the installed package, not the source tree."""
    name = f"lesson-v{version}.schema.json"
    return json.loads(files("tutordraw").joinpath(name).read_text(encoding="utf-8"))


def downgrade(document: dict, version: int) -> dict:
    """Rewrite a current document the way an older version would have saved it."""
    legacy = deepcopy(document)
    legacy["schema_version"] = version
    newer_versions = range(version + 1, SCHEMA_VERSION + 1)
    for newer in newer_versions:
        for field in THEME_FIELDS_ADDED.get(newer, ()):
            legacy["theme"].pop(field, None)
    annotations = list(legacy["labels"])
    for step in legacy["steps"]:
        annotations.extend(step["callouts"])
        for newer in newer_versions:
            for field in STEP_FIELDS_ADDED.get(newer, ()):
                step.pop(field, None)
            for highlight in step["highlights"]:
                for field in HIGHLIGHT_FIELDS_ADDED.get(newer, ()):
                    highlight.pop(field, None)
            for restyle in step.get("restyles", []):
                for field in RESTYLE_FIELDS_ADDED.get(newer, ()):
                    restyle.pop(field, None)
    for annotation in annotations:
        for newer in newer_versions:
            for field in ANNOTATION_FIELDS_ADDED.get(newer, ()):
                annotation.pop(field, None)
    return legacy


def fields_after(version: int) -> tuple[str, ...]:
    """Every field that exists now but did not at the given version."""
    return tuple(field
                 for newer in range(version + 1, SCHEMA_VERSION + 1)
                 for table in (STEP_FIELDS_ADDED, THEME_FIELDS_ADDED, ANNOTATION_FIELDS_ADDED,
                               HIGHLIGHT_FIELDS_ADDED, RESTYLE_FIELDS_ADDED)
                 for field in table.get(newer, ()))

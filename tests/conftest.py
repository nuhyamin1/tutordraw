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
}

# The same, for theme fields, which live outside the steps.
THEME_FIELDS_ADDED = {
    6: ("avoid_collisions", "collision_margin"),
}

# The same, for label and callout fields, which appear in two places.
ANNOTATION_FIELDS_ADDED = {
    7: ("box",),
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
    for annotation in annotations:
        for newer in newer_versions:
            for field in ANNOTATION_FIELDS_ADDED.get(newer, ()):
                annotation.pop(field, None)
    return legacy


def fields_after(version: int) -> tuple[str, ...]:
    """Every field that exists now but did not at the given version."""
    return tuple(field
                 for newer in range(version + 1, SCHEMA_VERSION + 1)
                 for table in (STEP_FIELDS_ADDED, THEME_FIELDS_ADDED, ANNOTATION_FIELDS_ADDED)
                 for field in table.get(newer, ()))

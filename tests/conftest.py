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

LEGACY_VERSIONS = tuple(v for v in SUPPORTED_VERSIONS if v != SCHEMA_VERSION)


def packaged_schema(version: int = SCHEMA_VERSION) -> dict:
    """Load a JSON Schema from the installed package, not the source tree."""
    name = f"lesson-v{version}.schema.json"
    return json.loads(files("tutordraw").joinpath(name).read_text(encoding="utf-8"))


def downgrade(document: dict, version: int) -> dict:
    """Rewrite a current document the way an older version would have saved it."""
    legacy = deepcopy(document)
    legacy["schema_version"] = version
    for step in legacy["steps"]:
        for newer in range(version + 1, SCHEMA_VERSION + 1):
            for field in STEP_FIELDS_ADDED.get(newer, ()):
                step.pop(field, None)
    return legacy


def fields_after(version: int) -> tuple[str, ...]:
    """Step fields that exist now but did not at the given version."""
    return tuple(field
                 for newer in range(version + 1, SCHEMA_VERSION + 1)
                 for field in STEP_FIELDS_ADDED.get(newer, ()))

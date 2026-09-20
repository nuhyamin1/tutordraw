# AI handoff — start here

Last updated: **2026-09-20**, persistence and AI authoring development.

## Current state

**Published version: 0.1.0a3. Development checkout: 0.1.0a4, not published.**

After discussing AI use without a dedicated app, the owner agreed to continue
with the suggested development. This session prioritized complete lesson save/load
and an AI authoring workflow before timed lessons. No new publication, Git commit,
or push was performed. The previous publication authorization applied only to a3.

Owner metadata: `tutordraw`, MIT, Nuh Yamin. Origin:
https://github.com/nuhyamin1/tutordraw.git, branch master. DrawCV remains unchanged;
the runtime dependency is still the published `pydrawcv==0.10.0.post1` wheel.

## New functionality in a4

- `Tutorial.to_dict/from_dict/to_json/from_json/save_json/load_json` serialize a
  full lesson: DrawCV scene, theme, targets, every label (even unshown), ordered
  steps, callouts, highlights, and focus/dimming state.
- Format `tutordraw.lesson`, schema integer 1. Stable drawable/target/label/callout/
  step IDs survive round trips. Shared labels remain shared after reload.
- `tutorial.targets`, `tutorial.labels`, `tutorial.get_target(name)`, and
  `target.drawable` expose useful entry points for resumed editing.
- Step has a stable read-only `id`. Annotation definitions remain immutable;
  revise their text in a detached document and validate with `from_dict`.
- Unknown TutorDraw fields, unsupported versions, duplicate IDs/keys, dangling
  references, invalid options, nonfinite JSON numbers, and invalid UTF-8 produce
  `LessonFormatError` (a ValidationError). Filesystem errors propagate.
- Saving refuses existing paths by default, validates before touching a file,
  and replaces existing content only after writing a complete temporary document.
  New files use exclusive creation; failed partial files are removed.
- Packaged `lesson-v1.schema.json` supports structural validation; loading also
  checks identity/reference semantics and the embedded DrawCV document.
- `examples/save_and_revise.py` saves a cell lesson, reopens it, moves the nucleus,
  revises an explanation, and saves a new lesson plus before/after PNGs.
- `docs/PERSISTENCE.md` documents the format. `docs/AI_AUTHORING.md` gives practical
  creation/revision prompts for any coding assistant; there is no AI-service SDK.

## Files added/changed

New runtime: `src/tutordraw/serialization.py`, `lesson-v1.schema.json`.
Updated runtime: tutorial/model/errors/public exports and a4 version metadata.
New tests: `tests/test_persistence.py`. `jsonschema` is a development dependency
only; runtime loading uses standard-library JSON and existing validators.
New docs/example: persistence, AI authoring, save_and_revise.
Updated checks: installed-package runner now verifies six PNGs and a loaded
revision; artifact check requires schema/example/docs in distribution files.
README, API, architecture, compatibility, roadmap, decisions, and changelog reflect
the distinction between published a3 and development-only a4.

## Verification in this session

Use `.venv/Scripts/python.exe` in place of python on this Windows machine.

- `python -m pytest -q`: **112 passed** against editable source.
- `python examples/save_and_revise.py`: original/revised JSON plus previews under
  `output/persistence`. Visually inspected before/after: label, highlight and
  callout follow the moved nucleus; updated text fits; original stays unchanged.
- `python tools/check_docs.py`: 15 documents and the README example pass.
- `python -m build --no-isolation --outdir output/development`: wheel and sdist built.
- `python tools/check_release.py --dist-dir output/development --require-metadata`:
  strict Twine, metadata and packaged-file checks pass.
- Installed the a4 wheel locally with `pip install --no-deps --force-reinstall`,
  then `python -I -m pytest -q`: **112 passed against the installed wheel**.
- `python -I tools/check_installed.py`: all three examples run outside the checkout;
  six PNGs decode and the revised lesson reloads correctly.
- `python -m pip check`: no broken requirements; `git diff --check` passes.
- Restored the editable development install with
  `python -m pip install --no-deps --no-build-isolation -e .`.

New tests cover pixel-identical round trips, source/history preservation, detached
metadata, IDs/shared labels, nested groups and embedded raster images, resumed
editing, schema validation, malformed input/reference failures, unsupported scene
versions, UTF-8/BOM, collision races, invalid-save preservation, and failed-write
cleanup. No additional OS/Python version was tested in this session.

The a4 artifacts are in `output/development`, separate from the published a3
files in `output/release`. Build log: `output/build-a4.log`. Do not upload a4
without a new explicit owner request.

## Published a3 evidence (preserved)

https://pypi.org/project/tutordraw/0.1.0a3/

PyPI accepted wheel and source archive, and a fresh public-index installation ran
both original examples successfully. Recorded SHA256 hashes, rechecked unchanged
in this session:

- Wheel: `0026efa9b7ff6eda5dcc47d623d299eaf8a9da617c29bbc3ab6961aade8d9ea5`
- Sdist: `115ae72b49c5cf55e4c45222ac658b96182f5452b90652a51173c935d4e00577`

Do not rebuild and replace or re-upload a3. Credentials must never be printed or
saved in source/docs. Further releases need explicit authorization.

## Remaining limits and next work

- Hosted CI remains unverified; nine OS/Python combinations are configured.
- ASCII annotations only; no rich scripts, automatic overlap layout, or video yet.
- Format v1 has no migrations. DrawCV owns its nested schema and asset loaders.
- No callbacks/pickle in TutorDraw JSON, but this is not a sandbox for arbitrary
  untrusted/custom scene assets. No large-document quota or streaming loader.
- Source edits during save/render are unsupported; undo history/caches/PNG output
  are not part of the lesson file. Hidden emphasis and layout warnings still apply
  at render time, not merely at load time.
- The local repo includes earlier M3/post-release changes plus this session's a4
  work. No agent-created commits/pushes. Inspect current Git state before committing.

Next: owner review of a4, then either authorize a new release or proceed to timed
lessons (M4). Keep existing static rendering and v1 round-trip guarantees intact.
If publishing a4, update release instructions/filenames and run the complete checks;
do not reuse a3 upload commands.

## Environment

Workspace `C:/Projects/TutorDraw`, Windows PowerShell, Python 3.12 in `.venv`.
DrawCV checkout `C:/Projects/DrawCV` is read-only context for this project.
Read-only Git commands may need `git -c safe.directory=C:/Projects/TutorDraw ...`
due to sandbox ownership; no global Git setting was changed.

## Continuation prompt

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md, docs/HANDOFF.md,
> README, persistence, AI authoring, API, and roadmap. Published a3 is immutable;
> the a4 checkout adds full lesson persistence with schema v1 and has 112 passing
> source/installed-wheel tests. Do not reimplement or republish completed work.
> Continue the owner's next request, preserve static rendering and persistence
> contracts, keep DrawCV unchanged, and update the handoff with verified results.

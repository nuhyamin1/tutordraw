# Working on TutorDraw

## Start here

Read `README.md`, `docs/HANDOFF.md`, `docs/ARCHITECTURE.md`, and
`docs/ROADMAP.md` before implementing. Consult `docs/DECISIONS.md` for rationale.
Inspect actual repository files rather than assuming the handoff is current.

## Project boundary

- This is TutorDraw, a Python tutorial-authoring library using DrawCV.
- Depend on the `pydrawcv` distribution, imported as `drawcv`.
- Do not modify `C:/Projects/DrawCV` as part of ordinary TutorDraw work.
  If an upstream limitation blocks progress, document it and seek a TutorDraw
  adapter or a reduced, explicitly documented feature first.
- Keep drawing/rendering concerns in DrawCV and teaching concerns in TutorDraw.
- The owner wants useful documentation for switching between AI models.
- Proposed APIs are not existing APIs. Update documentation as implementation
  settles, and keep examples clearly marked until verified runnable.

## Development conventions

- Target Python 3.12+ initially. Use a `src/tutordraw/` layout when code begins.
- Prefer small typed public APIs and explicit validation errors.
- Isolate DrawCV-specific lookups, bounds, and cloning in an adapter.
- Preserve the user's source scene when producing tutorial output.
- Prefer independent step state over replay-dependent actions for static export.
- Test meaningful behavior: references, transformed anchors, source preservation,
  step independence, errors, and actual image export.
- Visually inspect rendered examples in addition to numerical tests.
- Do not hardcode local checkout paths or invent dependency compatibility claims.
- Do not publish a package unless the owner explicitly requests publication.

## Before handing off

Update `docs/HANDOFF.md` with implemented capabilities, changed files,
commands actually run and their outcomes, unresolved issues, and the next
concrete task. Update the roadmap checkboxes and record material design changes
in `docs/DECISIONS.md`. Never mark a check complete without evidence.

Keep these documents concise enough that another model can resume without the
previous conversation. Never include credentials, tokens, or private indexes.

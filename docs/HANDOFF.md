# AI handoff — start here

Last updated: **2026-09-20**, after M1 implementation.

## Owner intent

Build TutorDraw, a Python library for tutorials using drawings, on top of `pydrawcv` (import `drawcv`). Add teaching annotations and lesson steps. Do not modify DrawCV. Maintain documentation so another AI model can resume without the chat. The owner authorized implementation after the documentation phase.

## Current implementation

M1 is implemented as local alpha `0.1.0a1`. No PyPI release has occurred.

- `pyproject.toml`: src layout, Python >=3.12, tested published dependency pinned to `pydrawcv==0.10.0.post1`, dev extra.
- `src/tutordraw/tutorial.py`: target registration, independent steps, rendering.
- `src/tutordraw/model.py`: immutable targets/labels and validated authoring.
- `src/tutordraw/layout.py`: bounds anchors, text panels, straight leaders, off-canvas warnings. ASCII Hershey labels only.
- `src/tutordraw/adapters/drawcv.py`: recursive ID validation, serialization copying, generated overlay layer.
- `src/tutordraw/errors.py` and `__init__.py`: public exports and errors.
- `examples/cell_tutorial.py`: labeled and unlabeled PNG examples.
- `tests/test_tutorial.py`: 30 passing test cases.
- `docs/API.md`: implemented API; README contains runnable setup/example code.

No callouts, highlights, dimming, themes, batch export, playback, or persistence yet. Architecture sections for them remain proposals.

## Environment

- Workspace: `C:/Projects/TutorDraw`, PowerShell on Windows.
- DrawCV checkout: `C:/Projects/DrawCV`, inspected only; no files changed there.
- Neither `python` on PATH nor `py -3.12` worked. The bundled runtime created `.venv`:
  `C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
- Use `.venv/Scripts/python.exe` for commands. Do not hardcode the bundled path into package source.
- Dependencies downloaded with authorized network access after sandbox socket blocking. The initial pip failure was not a missing release.
- DrawCV import verified from `.venv/Lib/site-packages/drawcv`, not the checkout.
- No Git repository/branch was present when work began; no commits were made.

## Verification

Successful commands from the workspace root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cell_tutorial.py
.\.venv\Scripts\python.exe -m build --no-isolation
```

**30 tests passed.** Tests cover PNG decoding, repeated/out-of-order renders, source content/history preservation, render/copy failures, moved and nested transformed targets, leader endpoints, ownership, invalid options, missing/duplicate IDs, overlay name collisions, and alpha.

Visually inspected `output/cell-step-01.png`: legible title/label, correct nucleus attachment, no clipping. The example also writes `output/cell-step-02.png` without annotations. Outputs and `.venv` are ignored; regenerate on another machine.

Wheel and source distribution build successfully. The wheel was copied to
`C:/Users/user/AppData/Local/Temp/tutordraw-m1-wheel-check`, installed into a clean
virtual environment there with its published dependencies, and rendered
`wheel-smoke.png` from that directory with Python's `-I` isolated mode. Both
TutorDraw and DrawCV imported from that environment's `site-packages`, independent
of either checkout. A direct escalated install from the workspace wheel initially
hit a read-permission error; copying it to the temporary directory resolved it.
The clean-environment check used `Scripts/python.exe -m pip install
tutordraw-0.1.0a1-py3-none-any.whl`, followed by an isolated one-target PNG render.

README Python example executed successfully and all relative documentation links
resolved. `MANIFEST.in` includes docs and examples in the source distribution.
Cross-platform runs, advanced DrawCV assets, rich fonts, PyPI name availability,
and broader version ranges are unverified. License and owner metadata remain unresolved.

## Integration findings

- Published DrawCV 0.10.0.post1 supports the M1 APIs.
- `Scene.get` includes group children, but TutorDraw traverses actual contents to catch duplicate IDs and avoid relying on an externally stale ID map.
- `Scene.from_dict(deepcopy(scene.to_dict()))` preserves tested IDs, geometry, styles, and group transforms, without sharing mutable state.
- `Text.get_bounds` provides basic Hershey measurement without typography extras.
- Anchors use `get_bounds()`, excluding post-processing effect extents.
- Missing registered targets fail all renders; hidden artwork does not suppress explicitly shown labels. These M1 semantics are documented.

## Next task: M2

Read `AGENTS.md`, `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md`. Implement wrapped callouts, rectangular highlights, and group-aware dimming. Add shared themes and collision-safe ordered PNG export. Complete the three-step lesson from `docs/PRODUCT.md`.

Preserve independent steps and source safety. Avoid multiplying dimming twice through group hierarchies or dimming a focused child through its parent. Test text wrapping before promising other scripts. Do not publish without an explicit owner request.

## Ready-to-copy continuation prompt

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md and docs/HANDOFF.md, then the README, API guide, architecture, and roadmap. M1 is implemented with 30 passing tests. Use .venv/Scripts/python.exe on this machine. Implement M2: wrapped callouts, highlights, group-aware dimming, themes, ordered PNG export, and the three-step cell lesson. Depend on published pydrawcv; do not modify C:/Projects/DrawCV. Preserve source scenes and independent rendering. Verify and visually inspect the results. Update documentation and handoff with actual status. Do not publish to PyPI.

## Maintain this handoff

Replace stale state after each session. Record implemented files, commands/outcomes, unverified checks, decisions, known issues, next bounded task, and workspace prerequisites. Do not restart M1 based on older documentation-only chat context.

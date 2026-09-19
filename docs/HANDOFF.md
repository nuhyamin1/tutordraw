# AI handoff — start here

Last updated: **2026-09-20**, after M2 implementation.

## Owner intent and current scope

Build TutorDraw, a Python library for tutorials using drawings, on `pydrawcv` (import `drawcv`). Keep DrawCV unchanged. Maintain documentation for continuing with another AI model. The owner authorized continuing after M1 and requested its commit message first; it was supplied in chat. No Git commit or PyPI publication was requested/performed.

## Current implementation

**M0–M2 complete, local alpha `0.1.0a2`.**

- `tutorial.py`: registration, independent steps, rendering, ordered PNG export.
- `model.py`: Target, Label, step-owned Callout, Highlight, and Step authoring.
- `themes.py` and `validation.py`: immutable presentation defaults and validation.
- `layout.py`: measured ASCII Hershey wrapping, bounds anchors, panels, leader geometry, off-canvas warnings.
- `attention.py`: structural visibility checks, outline highlights, group-aware dimming.
- `export.py`: preflight collision checks, temporary encoding, exclusive creation or explicit replacement, partial-failure reporting.
- `adapters/drawcv.py`: recursive ID validation, source-safe serialization copying, overlay layer.
- `examples/cell_tutorial.py`: complete three-step cell lesson, writes `output/cell/step-001.png` through `step-003.png`.
- `examples/group_focus.py`: nested-group emphasis, writes `output/group-focus.png`.
- `tests/test_tutorial.py` and `tests/test_presentation.py`: **54 passing cases**.
- `pyproject.toml`: Python >=3.12, pinned published `pydrawcv==0.10.0.post1`, development extra.

Read README and `docs/API.md` for executable usage. Do not assume the earlier M1-only API guide is current. Video, playback, persistence, rich fonts, automatic collision avoidance, and interactive lessons remain unimplemented.

## Environment

Workspace: `C:/Projects/TutorDraw`, Windows PowerShell. Use `.venv/Scripts/python.exe`; the global `python` and `py -3.12` launchers were unavailable during M1. The virtual environment was created using the app's bundled Python 3.12. Do not hardcode runtime or checkout paths into the package.

DrawCV checkout `C:/Projects/DrawCV` was inspected but not modified. Runtime imports use the published wheel in `.venv/Lib/site-packages`, not that checkout. No `.git` directory was present during M2; no commits were created.

Network package installation during M1 required tool escalation after sandbox sockets were blocked. This was not a missing package release. M2 uses the existing environment. `.venv`, `dist`, build artifacts, caches, and `output` are ignored by `.gitignore`.

## Verified in M2

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe examples/cell_tutorial.py
.\.venv\Scripts\python.exe examples/group_focus.py
```

**54 tests passed.** M1 contracts remain covered. Added tests exercise paragraph/long-word wrapping, panel bounds, following moved objects, highlighted/dimmed pixels, no emphasis leakage, nested-group opacity without double dimming, multiple focus targets, hidden ancestors/layers, theme overrides, invalid operations, export order/collisions/races, partial failures, and cleanup after failed writes.

Visually inspected all three cell images and the nested-group example. Text is readable and panels fit; nucleus emphasis occurs only in the focus step; review restores full artwork. The group example shows an undimmed selected child and equally dimmed unrelated branches with clear annotations.

Built `dist/tutordraw-0.1.0a2.tar.gz` and `dist/tutordraw-0.1.0a2-py3-none-any.whl`
with `.venv/Scripts/python.exe -m build --no-isolation`. Copied the wheel to the
isolated M1 verification environment at
`C:/Users/user/AppData/Local/Temp/tutordraw-m1-wheel-check` and installed it using
that environment's Python with `-m pip install --no-deps --force-reinstall`.
Published dependencies were already installed there. An isolated `python -I -c`
smoke check imported version 0.1.0a2 from its `site-packages`, then rendered and
exported two steps with callouts, highlights, and dimming to `m2-wheel-output`.
It did not import source code from either project checkout.

Executed the README Python example and checked all relative Markdown links.
Both passed. Cross-platform runs, advanced DrawCV assets, non-ASCII typography,
PyPI name availability, and broader dependency ranges remain unverified.
License/author metadata are unresolved.

## Design details to preserve

- Render from current source state through `Scene.from_dict(deepcopy(scene.to_dict()))`; validate copied IDs/types. No mutation/undo on the live scene.
- Each step owns its callouts/highlights/focus and explicitly shows reusable labels.
- `explain` returns a Callout; `highlight`, `dim_others`, and `show` return Step.
- Theme numeric defaults resolve while authoring; panel/text/leader styling resolves at render time. Themes use immutable RGB tuples.
- Callout widths exclude padding. Long words split; impossible character widths fail clearly. ASCII plus newline support only.
- Dimming preserves selected subtrees and their ancestors. Multiply each maximal unrelated branch once. Source opacity still applies.
- Hidden flags and zero opacity are considered, including ancestors/layers; masks/occlusion are not. Missing registered targets still fail all rendering.
- PNG export is not a batch transaction: completed files remain and are listed in ExportError. New files use exclusive creation; overwrite replaces only successfully encoded output.

## Next task: M3 release preparation

Read AGENTS.md, README, API, architecture, roadmap, and decisions. Improve release readiness: review public API/docs, add appropriate CI, verify supported platforms/dependency versions, and package metadata. Final naming, license, and author metadata need owner input before release; do useful independent checks first. Do not upload to PyPI without explicit authorization.

## Ready-to-copy continuation prompt

> Continue TutorDraw in C:/Projects/TutorDraw. Read AGENTS.md and docs/HANDOFF.md, then README, API, architecture, and roadmap. M2 is complete as local alpha 0.1.0a2 with 54 passing tests. Use .venv/Scripts/python.exe. Work on M3 release preparation: API/documentation review, CI, package verification, and compatibility. Keep DrawCV unchanged; use published pydrawcv. Preserve source-safe independent steps and tested export guarantees. Update documentation and handoff with actual results. Resolve owner-controlled naming/license/author choices before release. Do not publish to PyPI without explicit authorization.

## Handoff maintenance

Replace stale status after future work. Record exact commands/outcomes, unverified checks, decisions, issues, next task, and local prerequisites. Do not restart M1/M2 from older chat context.

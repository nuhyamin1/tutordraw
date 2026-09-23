# Contributing

Use Python 3.12 or newer. Work in a virtual environment, install from the project
root with `python -m pip install -e ".[dev]"`, and run `python -m pytest -q`.
On Windows the existing environment uses `.venv/Scripts/python.exe`.

Read [the architecture](docs/ARCHITECTURE.md), [API guide](docs/API.md), and
[agent instructions](AGENTS.md). Keep DrawCV rendering code upstream; implement
teaching behavior here through the adapter.

Before submitting:

1. Test meaningful behavior, especially independent steps, source preservation,
   group transforms/dimming, and export failures.
2. Run `python tools/check_docs.py` to verify links and the README example.
3. Run examples and inspect images after visual changes. `tests/test_golden.py`
   pins the canonical lessons' geometry and pixels; after an *intended* visual
   change, regenerate with `TUTORDRAW_UPDATE_GOLDEN=1 python -m pytest
   tests/test_golden.py` and look at every changed file in `tests/golden/`
   before committing. Failures write actual and diff images to
   `output/golden-failures/`.
4. Update the changelog and documentation for public API changes.
5. Update [the handoff](docs/HANDOFF.md) with verification and remaining work.

The installed-package check intentionally rejects editable source imports.
Build a wheel, install it in a separate environment, and run
`python -I tools/check_installed.py` using that environment's Python.
CI performs this check on the built wheel automatically.

The project is currently alpha. Avoid breaking public methods without documenting
migration instructions. Do not widen the DrawCV dependency pin without testing
released wheels. See [release preparation](docs/RELEASING.md) for package checks.

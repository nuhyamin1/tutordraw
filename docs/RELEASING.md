# Release preparation and publishing

This is a manual procedure, not an upload automation. Version 0.1.0a3 was published on 2026-09-20 after explicit owner authorization.
Future publication also requires an explicit owner request. The CI workflow never uploads.

## Release identity

- Distribution/import: `tutordraw` (owner confirmed).
- License: MIT; copyright holder/author: Nuh Yamin (owner confirmed).
- Published: `0.1.0a3` on 2026-09-20; still an early alpha.
- Repository: `https://github.com/nuhyamin1/tutordraw`, read from the configured origin.
- PyPI accepted both release files under the owner-authorized credential.

Published versions are immutable. The commands below describe the release process;
**choose a new version and update filenames before a future upload**. Do not rebuild
and try to replace the already published 0.1.0a3 artifacts.

## Local verification

Install the development extra, then run from the repository root:

```powershell
python -m pytest -q
python tools/check_docs.py
python -m build --no-isolation --outdir output/release
python tools/check_release.py --dist-dir output/release
python -m pip check
```

`check_release.py` checks exact versioned artifacts rather than all historical
files in `dist`. It checks package contents and calls `twine check --strict`.
The normal check allows preparation before the repository URL is finalized.

Install the wheel in a separate virtual environment, using its Python for
`python -I tools/check_installed.py`. This runs both examples outside the checkout,
checks their PNGs, rejects editable source imports, and verifies version metadata.
CI repeats installed-wheel tests across the configured OS/Python matrix.

## Before release

1. Confirm the configured repository and documentation links are publicly accessible.
2. Confirm the chosen version and PyPI account/project ownership with the owner.
3. Obtain passing hosted CI results for the claimed supported environments.
4. Review the changelog, package description, license, and tutorial images.
5. Rebuild the candidate artifacts, then run:

```powershell
python tools/check_release.py --dist-dir output/release --require-metadata
```

Metadata validation is not authorization to upload and cannot verify PyPI name
ownership or hosted CI results. Keep release evidence in the handoff.

## Upload only after explicit authorization

An authorized rehearsal can use TestPyPI; an authorized public release can use
PyPI. TestPyPI has a separate namespace and account. Use the exact two candidate
files, never a wildcard that might select old releases:

```powershell
# TestPyPI rehearsal, only when requested:
python -m twine upload --repository testpypi output/release/tutordraw-0.1.0a3-py3-none-any.whl output/release/tutordraw-0.1.0a3.tar.gz

# Public PyPI release, only when requested:
python -m twine upload output/release/tutordraw-0.1.0a3-py3-none-any.whl output/release/tutordraw-0.1.0a3.tar.gz
```

Use the owner's credential mechanism; never put tokens in repository files,
command history, or handoff documents. After upload, verify a clean installation
from that index, execute examples, and record the released version. Update these
filenames whenever the candidate version changes.

## Reference documentation

The workflow uses the official [setup-python](https://github.com/actions/setup-python)
and [checkout](https://github.com/actions/checkout) actions. Package metadata and
publishing follow the [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

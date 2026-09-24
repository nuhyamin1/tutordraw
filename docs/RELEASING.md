# Release preparation and publishing

This is a manual procedure, not an upload automation. Version 0.1.0a3 was published on 2026-09-20 after explicit owner authorization.
Future publication also requires an explicit owner request. The CI workflow never uploads.

## Release identity

- Distribution/import: `tutordraw` (owner confirmed).
- License: MIT; copyright holder/author: Nuh Yamin (owner confirmed).
- Published: `0.1.0a3` on 2026-09-20, `0.1.0a11` on 2026-09-21 and `0.2.0a1` on
  2026-09-24 (the milestone first called 0.1.0a12); still an alpha.
- Versions a4 through a10 were development milestones and were never uploaded;
  0.1.0a11 contains all of their work.
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

## Release readiness gate

Every item must be true before asking the owner to authorise an upload.

| Check | How |
| --- | --- |
| Working tree clean and pushed | `git status`, `git log origin/master..HEAD` |
| Hosted CI green on the exact commit | all nine jobs, not just the local machine |
| Version not already on PyPI | published versions are immutable |
| Local suite green from source and the installed wheel | `pytest`, then `python -I -m pytest` |
| Examples run outside the checkout | `python -I tools/check_installed.py` |
| Docs links valid and README renders on PyPI | `tools/check_docs.py`; the README is the project page, so **every link in it must be absolute** |
| Artifacts validate | `tools/check_release.py --require-metadata` |
| Changelog dates the release | replace "Unreleased" with the date for the shipped version only |

Two judgement calls that are not mechanical:

- **The lesson format moved v2 to v5 in one day.** Published schema versions
  become other people's files. Consider whether the format should settle first.
- **Alpha scope.** a11 adds video, non-ASCII text, per-step artwork, animation,
  reveals and optional Thai/Arabic since a3. That is a large jump for one
  version number; say so in the release notes rather than hiding it.

## Before release

1. Confirm the configured repository and documentation links are publicly accessible.
2. Confirm the chosen version and PyPI account/project ownership with the owner.
3. Work through the readiness gate above.
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
python -m twine upload --repository testpypi output/release/tutordraw-0.2.0a1-py3-none-any.whl output/release/tutordraw-0.2.0a1.tar.gz

# Public PyPI release, only when requested:
python -m twine upload output/release/tutordraw-0.2.0a1-py3-none-any.whl output/release/tutordraw-0.2.0a1.tar.gz
```

Use the owner's credential mechanism; never put tokens in repository files,
command history, or handoff documents. After upload, verify a clean installation
from that index, execute examples, and record the released version. Update these
filenames whenever the candidate version changes.

## Reference documentation

The workflow uses the official [setup-python](https://github.com/actions/setup-python)
and [checkout](https://github.com/actions/checkout) actions. Package metadata and
publishing follow the [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

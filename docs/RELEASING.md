# Release preparation and publishing

This is a manual procedure, not an upload automation. Version 0.1.0a3 was published on 2026-09-20 after explicit owner authorization.
Future publication also requires an explicit owner request. The CI workflow never uploads.

## Release identity

- Distribution/import: `tutordraw` (owner confirmed).
- License: MIT; copyright holder/author: Nuh Yamin (owner confirmed).
- Published: `0.1.0a3` on 2026-09-20, `0.1.0a11` on 2026-09-21, `0.2.0a1` on
  2026-09-24, and `0.3.0a1` on 2026-09-27; still an alpha. Tags
  `v0.1.0a11`, `v0.2.0a1`, and `v0.3.0a1` mark their upload commits.
- `0.3.0a1` was the owner's choice because the lesson format moved from v9
  to v13 and placement changed. Its wheel and sdist hashes match PyPI; see
  [HANDOFF.md](HANDOFF.md) for the exact release evidence.
- Versions a4 through a10 were development milestones and were never uploaded;
  0.1.0a11 contains all of their work.
- Repository: `https://github.com/nuhyamin1/tutordraw`, read from the configured origin.
- PyPI accepted both release files under the owner-authorized credential.

Published versions are immutable. Choose a new version and update package
metadata and filenames for any later release. Never rebuild and try to
replace an already published artifact.

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

- **Lesson compatibility.** 0.3.0a1 writes schema v13, which 0.2.0a1 cannot
  open; 0.3.0a1 still loads earlier lesson formats. State this in release notes.
- **Alpha scope.** Placement, motion, captions, pointer behavior, graph tools,
  and prompt taps changed since 0.2.0a1. Review the changelog and examples
  before publication.

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
# Set this to a NEW, checked version; never reuse a published version.
$releaseVersion = "<new-version>"
$wheel = "output/release/tutordraw-$releaseVersion-py3-none-any.whl"
$sdist = "output/release/tutordraw-$releaseVersion.tar.gz"

# TestPyPI rehearsal, only when requested:
python -m twine upload --repository testpypi $wheel $sdist

# Public PyPI release, only when requested:
python -m twine upload $wheel $sdist
```

Use the owner's credential mechanism; never put tokens in repository files,
command history, or handoff documents. After upload, verify a clean installation
from that index, execute examples, and record the released version. Update these
filenames whenever the candidate version changes.

## Reference documentation

The workflow uses the official [setup-python](https://github.com/actions/setup-python)
and [checkout](https://github.com/actions/checkout) actions. Package metadata and
publishing follow the [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

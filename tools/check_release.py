"""Validate exact local artifacts; never uploads or changes release metadata."""

import argparse
from email.parser import BytesParser
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("output/release"))
    parser.add_argument("--require-metadata", action="store_true",
                        help="Also require owner-approved license, author, and repository metadata")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    name, version = project["name"], project["version"]
    wheel = args.dist_dir / f"{name}-{version}-py3-none-any.whl"
    source = args.dist_dir / f"{name}-{version}.tar.gz"
    for path in (wheel, source):
        if not path.is_file():
            raise SystemExit(f"Missing artifact: {path}")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        expected = {"tutordraw/" + p.relative_to(root / "src/tutordraw").as_posix()
                    for p in (root / "src/tutordraw").rglob("*.py")}
        expected.update({"tutordraw/lesson-v1.schema.json", "tutordraw/lesson-v2.schema.json"})
        if not expected <= names:
            raise SystemExit(f"Wheel is missing modules: {expected - names}")
        metadata = BytesParser().parsebytes(archive.read(f"{name}-{version}.dist-info/METADATA"))
        if metadata["Version"] != version or metadata["Requires-Python"] != project["requires-python"]:
            raise SystemExit("Built metadata does not match pyproject.toml")
        if metadata["License-Expression"] != project.get("license"):
            raise SystemExit("Built license expression does not match pyproject.toml")
        if metadata["Author"] != ", ".join(author["name"] for author in project.get("authors", [])):
            raise SystemExit("Built author metadata does not match pyproject.toml")
        if project.get("license-files") and not any(".dist-info/licenses/LICENSE" in p for p in names):
            raise SystemExit("Wheel is missing LICENSE")
        for label, url in project.get("urls", {}).items():
            if f"{label}, {url}" not in metadata.get_all("Project-URL", []):
                raise SystemExit(f"Built metadata missing {label} URL")
        if not any(r.replace(" ", "") == "pydrawcv==0.10.0.post1" for r in metadata.get_all("Requires-Dist", [])):
            raise SystemExit("Published DrawCV dependency pin missing from wheel")
    with tarfile.open(source) as archive:
        names = set(archive.getnames())
        for file in ("README.md", "LICENSE", "pyproject.toml", "CHANGELOG.md", "CONTRIBUTING.md",
                     "docs/API.md", "docs/RELEASING.md", "examples/cell_tutorial.py",
                     "examples/group_focus.py", "examples/save_and_revise.py", "docs/PERSISTENCE.md",
                     "docs/AI_AUTHORING.md", "docs/TIMING.md", "examples/timed_lesson.py",
                     "docs/VIDEO.md", "examples/video_lesson.py",
                     "tools/check_installed.py", "tests/test_tutorial.py"):
            if f"{name}-{version}/{file}" not in names:
                raise SystemExit(f"Source distribution missing: {file}")
    subprocess.run([sys.executable, "-m", "twine", "check", "--strict", str(wheel), str(source)], check=True)
    if args.require_metadata:
        missing = []
        if not project.get("license") or not (root / "LICENSE").is_file():
            missing.append("owner-approved license expression and LICENSE")
        if not project.get("authors"):
            missing.append("author metadata")
        if not project.get("urls", {}).get("Repository"):
            missing.append("public Repository URL")
        if missing:
            raise SystemExit("Release metadata incomplete: " + "; ".join(missing))
    print(f"Validated {name} {version}; no files uploaded")


if __name__ == "__main__":
    main()

"""Check relative Markdown links and execute the README's Python quickstart."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    documents = [*root.glob("*.md"), *root.joinpath("docs").glob("*.md")]
    for document in documents:
        for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8-sig")):
            if link.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = document.parent / link.split("#")[0]
            if not target.exists():
                raise SystemExit(f"Broken link in {document.name}: {link}")
    readme = (root / "README.md").read_text(encoding="utf-8-sig")
    examples = re.findall(r"```python\n(.*?)\n```", readme, re.S)
    if not examples:
        raise SystemExit("README must contain an executable Python quickstart")
    with tempfile.TemporaryDirectory(prefix="tutordraw-docs-") as directory:
        for code in examples:
            subprocess.run([sys.executable, "-I", "-W", "error", "-c", code], cwd=directory, check=True)
    print(f"Checked {len(documents)} documents and {len(examples)} README examples")


if __name__ == "__main__":
    main()

"""Ordered PNG export with preflight and per-file failure reporting."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from .errors import ExportError, ValidationError

if TYPE_CHECKING:
    from .tutorial import Tutorial


def export_steps(tutorial: Tutorial, directory: str | Path, *, overwrite: bool,
                 alpha: bool) -> list[Path]:
    if not isinstance(overwrite, bool) or not isinstance(alpha, bool):
        raise ValidationError("overwrite and alpha must be booleans")
    if not tutorial.steps:
        raise ValidationError("Cannot export a tutorial with no steps")
    root = Path(directory)
    paths = [root / f"step-{index + 1:03d}.png" for index in range(len(tutorial.steps))]
    # Preflight every name before writing any file, including dangling symlinks.
    for path in paths:
        if path.is_symlink() or (path.exists() and (not overwrite or not path.is_file())):
            raise FileExistsError(f"Export destination already exists: {path}")
    root.mkdir(parents=True, exist_ok=True)
    completed: list[Path] = []
    for index, path in enumerate(paths):
        temporary: Path | None = None
        try:
            canvas = tutorial.render_step(index, alpha=alpha)
            fd, name = tempfile.mkstemp(prefix=".tutordraw-", suffix=".png", dir=root)
            os.close(fd)
            temporary = Path(name)
            canvas.save(temporary)
            if overwrite:
                os.replace(temporary, path)
            else:
                # Exclusive creation also handles a collision after preflight.
                created = False
                try:
                    with path.open("xb") as output:
                        created = True
                        with temporary.open("rb") as source:
                            shutil.copyfileobj(source, output)
                except Exception:
                    if created:
                        path.unlink(missing_ok=True)
                    raise
            completed.append(path)
        except Exception as exc:
            raise ExportError(index, path, completed) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return paths

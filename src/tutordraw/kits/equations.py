"""Equations from LaTeX, drawn as ordinary DrawCV shapes.

ziamath lays the LaTeX out with its bundled STIX Two Math font and hands back
SVG path data; each piece becomes one filled DrawCV `Path` (glyphs, fraction
bars and radicals together), so a piece is a target that can be highlighted,
recoloured with `restyle(fill=...)`, narrated or hidden like any drawing.
Needs the optional `math` extra: pip install "tutordraw[math]".
"""

from __future__ import annotations

import re
import warnings

from drawcv import Color, FillStyle, Path, Point

from ..adapters.drawcv import fixed_pivot
from ..errors import ValidationError
from ..validation import finite_number, rgb
from ._base import INK, Kit, _check_name, _point

INSTALL = 'Equations need the optional math extra: pip install "tutordraw[math]"'
NUMBER = r"-?\d+(?:\.\d+)?(?:e-?\d+)?"


def _ziamath():
    try:
        # ziamath 0.13 finds its font with importlib.resources.path, which
        # Python 3.12 deprecates with a warning at import. It is theirs, not
        # the caller's, so it must not fail a program run with -W error.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import ziamath
    except ImportError as exc:
        raise ValidationError(INSTALL) from exc
    return ziamath


def layout(latex: str, size: float) -> tuple[str, float, float, float]:
    """(path data, width, ascent, descent) for one piece, baseline at y = 0.

    Raises ValidationError with the LaTeX problem named, including commands
    the converter does not know, which it would otherwise draw as their name.
    """
    if not isinstance(latex, str) or not latex.strip():
        raise ValidationError("Each equation piece must be non-empty LaTeX, e.g. r\"\\frac{1}{2}\"")
    zm = _ziamath()
    from latex2mathml.converter import convert

    try:
        mathml = convert(latex)
    except Exception as exc:
        raise ValidationError(f"Cannot read the LaTeX {latex!r}: {type(exc).__name__} {exc}".strip()
                              + ". Check braces and that ^ and _ have something after them.") from exc
    unknown = re.findall(r">(\\[A-Za-z]+)<", mathml)
    if unknown:
        raise ValidationError(f"Unknown LaTeX command {unknown[0]} in {latex!r}; use standard commands "
                              "such as \\frac, \\sqrt, \\alpha, \\times, \\rightarrow")
    previous = zm.config.svg2
    zm.config.svg2 = False  # paths inline, not <symbol>/<use>
    try:
        svg = zm.Latex(latex, size=size).svg()
    except Exception as exc:
        raise ValidationError(f"Cannot lay out the LaTeX {latex!r}: {type(exc).__name__} {exc}".strip()
                              + ". Check braces and that ^ and _ have something after them.") from exc
    finally:
        zm.config.svg2 = previous
    box = re.search(r'viewBox="([^"]+)"', svg)
    x0, y0, width, height = (float(v) for v in box.group(1).split())
    data = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    for attributes in re.findall(r"<rect([^>]*)>", svg):
        a = dict(re.findall(r'(\w+)="([^"]*)"', attributes))
        x, y, w, h = (float(a[k]) for k in ("x", "y", "width", "height"))
        data.append(f"M {x} {y} H {x + w} V {y + h} H {x} Z")
    if not data:
        raise ValidationError(f"The LaTeX {latex!r} draws nothing")
    for command in set(re.findall(r"[A-Za-z]", " ".join(data))):
        if command not in "MLQCHVZe":
            raise ValidationError(f"Unexpected path command {command!r} from the equation renderer")
    # Start at x = 0 whatever the font's side bearing, so pieces butt up evenly.
    return _offset(" ".join(data), -x0, 0.0), width, -y0, height + y0


class Equation(Kit):
    """An equation typeset from LaTeX, as named pieces on one baseline.

    `latex` is one string, or a list of pieces laid left to right, each a
    string or a `(name, latex)` pair; named pieces are targets, so a step can
    point at "the discriminant" while the rest stays put. Each piece must be
    complete LaTeX on its own. `position` is the top left of the equation;
    `spacing` is the gap between pieces, by default 0.22 x size.
    """

    KIND = "equation"

    def __init__(self, tutorial, latex, *, position, size: float = 32, name: str = "equation",
                 color=INK, spacing: float | None = None):
        _ziamath()
        self.position = _point(position, "position")
        self.size = finite_number(size, "size", minimum=0)
        if not 6 <= self.size <= 400:
            raise ValidationError("size must be from 6 to 400 (the font size in pixels)")
        # A piece typeset alone loses the space LaTeX puts round an operator,
        # so "a^2", "+", "b^2" need a gap of about a medium math space.
        self.spacing = (0.22 * self.size if spacing is None
                        else finite_number(spacing, "spacing", minimum=0))
        self.color = rgb(color, "color")
        pieces = [latex] if isinstance(latex, str) else latex
        if not isinstance(pieces, (list, tuple)) or not pieces:
            raise ValidationError("latex must be a string or a list of pieces")
        _check_name(name)
        parsed = []
        for i, piece in enumerate(pieces, start=1):
            if isinstance(piece, str):
                parsed.append((None, piece))
            elif isinstance(piece, (list, tuple)) and len(piece) == 2:
                parsed.append((_check_name(piece[0], "piece name"), piece[1]))
            else:
                raise ValidationError("each piece must be LaTeX or a (name, latex) pair")
        laid = [layout(text, self.size) for _, text in parsed]
        ascent = max(a for _, _, a, _ in laid)
        self.baseline = self.position.y + ascent
        self._start(tutorial, name, {"latex": [[n, t] for n, t in parsed], "size": self.size,
                                     "position": [self.position.x, self.position.y],
                                     "spacing": self.spacing})
        self.equation = self._target(self.group, name)
        x = self.position.x
        parts = []
        for i, ((piece_name, _), (data, width, _, _)) in enumerate(zip(parsed, laid), start=1):
            path = Path.from_svg_path(_offset(data, x, self.baseline),
                                      fill=FillStyle(color=Color(*self.color)), transform=fixed_pivot())
            self._add(path)
            parts.append(self._target(path, piece_name or f"{name}_part{i}"))
            x += width + self.spacing
        self.parts = tuple(parts)
        self.width = x - self.spacing - self.position.x
        self.height = ascent + max(d for _, _, _, d in laid)

    def part(self, key):
        """A piece by number (1 is the first) or name."""
        if isinstance(key, int) and not isinstance(key, bool):
            if not 1 <= key <= len(self.parts):
                raise ValidationError(f"piece numbers run from 1 to {len(self.parts)}")
            return self.parts[key - 1]
        for target in self.parts:
            if target.name == key:
                return target
        raise ValidationError(f"{self.name!r} has no piece {key!r}; it has "
                              f"{', '.join(t.name for t in self.parts)}")

    @classmethod
    def find(cls, tutorial, name: str = "equation") -> Equation:
        """Reattach to a saved equation, to reach its pieces by name."""
        eq, data = cls._reattach(tutorial, name)
        eq.position, eq.size, eq.spacing = Point(*data["position"]), data["size"], data["spacing"]
        eq.color = INK
        eq.equation = tutorial.get_target(name)
        eq.parts = tuple(tutorial.get_target(n or f"{name}_part{i}")
                         for i, (n, _) in enumerate(data["latex"], start=1))
        return eq


def _offset(d: str, dx: float, dy: float) -> str:
    """Move absolute path data (M, L, Q, C, H, V, Z; as ziamath writes it) by (dx, dy)."""
    out, command, index = [], None, 0
    for token in re.findall(rf"[MLQCHVZ]|{NUMBER}", d):
        if token.isalpha():
            command, index = token, 0
            out.append(token)
            continue
        value = float(token)
        if command == "H" or (command in "MLQC" and index % 2 == 0):
            value += dx
        else:
            value += dy
        index += 1
        out.append(f"{value:.3f}".rstrip("0").rstrip("."))
    return " ".join(out)

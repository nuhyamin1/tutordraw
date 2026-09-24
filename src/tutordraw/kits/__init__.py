"""Teaching kits: ready-made diagrams built from ordinary DrawCV objects.

A kit works out geometry a model gets wrong by hand (tick spacing, mapping
maths coordinates onto the canvas, sampling a function, routing arrows
between boxes, spacing stages round a circle) and adds plain DrawCV shapes to
the tutorial's scene. DrawCV draws them, lesson files save them, and the
parts come back as named targets, ready to label, highlight, measure or
narrate. Nothing here renders anything. See docs/KITS.md.
"""

from .diagrams import Cycle, Flowchart, Timeline
from .equations import Equation
from .graphs import Axes, NumberLine, format_number, nice_step
from .science import CrossSection, ForceDiagram

__all__ = ["Axes", "CrossSection", "Cycle", "Equation", "Flowchart", "ForceDiagram", "NumberLine", "Timeline",
           "format_number", "nice_step"]

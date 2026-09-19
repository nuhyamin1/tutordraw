# Design decisions

Recorded 2026-09-20. Distinguish owner requirements from initial design proposals.
Revise proposed choices when implementation evidence warrants it and record why.

| ID | Status | Decision | Reason |
| --- | --- | --- | --- |
| D001 | Owner requirement | Use `pydrawcv` for drawing | Build on the owner's existing drawing library |
| D002 | Owner requirement | Keep improving DrawCV outside this task | TutorDraw has a separate teaching responsibility |
| D003 | Owner requirement | Aim for a Python library distributed through PyPI | Reusable authoring library, not just a demo application |
| D004 | Owner requirement | Maintain documentation for switching AI models | Progress must survive usage limits and lost chat context |
| D005 | Proposed | Use `TutorDraw` / `tutordraw` as working names | Matches the repository; final distribution availability is unverified |
| D006 | Proposed | Wrap/reference DrawCV objects through teaching targets | Supports existing drawings without subclassing every shape |
| D007 | Proposed | Separate reusable annotation definitions from step state | An object can have multiple explanations over a lesson |
| D008 | Proposed | Render independent static steps first | Makes image export and direct step access predictable |
| D009 | Proposed | Render through a working scene copy | Protects source content and avoids accumulated annotation state |
| D010 | Proposed | Start with explicit placement and bounds anchors | Gives a small, testable first version with understandable limits |
| D011 | Proposed | Target Python 3.12+ initially | Matches the inspected local DrawCV requirement |

## Questions for implementation to resolve

1. Which released DrawCV version exposes all required APIs, and what dependency
   range is actually tested?
2. Can a public scene serialization round trip preserve the first release's
   supported objects, IDs, assets, and hierarchy? What needs explicit rejection?
3. Which text APIs provide reliable measurement and wrapping? Is the typography
   extra necessary, and how should missing fonts be reported?
4. Which bounds method is appropriate for labels and highlights, particularly
   with strokes, effects, rotated objects, and groups?
5. Does source object lookup include descendants, or must the adapter traverse?
6. What dimming limits arise from masks, blend modes, and group compositing?

Investigate these locally through source inspection and focused experiments.
They are not reasons to ask the owner to design implementation details.

## Owner choices before public release

- Final spelling and PyPI distribution name.
- License and copyright/author metadata.
- Whether additional output formats or language/font support must be in the first release.

These choices need not block the first executable slice. Do not invent legal
metadata or claim a package name is available without checking.

## M1 implementation decisions — 2026-09-20

- D006–D009 and D011 are implemented: composition, reusable labels, independent
  steps, working copies, and Python 3.12+.
- D010 uses `get_bounds()` anchors, including supported shape strokes but excluding
  post-processing effect extents.
- Pin `pydrawcv==0.10.0.post1` until broader compatibility is tested; M1 uses its
  released wheel, not the local checkout.
- Built-in Hershey labels reject non-printable/non-ASCII text rather than silently
  rendering unsupported characters. Rich text comes later.
- The small model lives in `model.py`; split modules when complexity warrants it.
- Copy through the public document API with a deep-copied dictionary; validate
  preserved IDs/types. Advanced asset compatibility still needs tests.
- `render_step` returns a Canvas; saving uses DrawCV's `save` method. Batch export
  and overwrite safeguards remain M2.

# Product scope

## Purpose

TutorDraw helps Python authors explain drawings through attached annotations
and a sequence of visual teaching steps. It supports tutorials **using**
drawings, including diagrams of biology, geometry, algorithms, machines, and
processes. Teaching someone how to draw is a possible use case, not the only one.

The initial audience is someone comfortable creating or loading a DrawCV scene
and writing Python. A visual editor is outside the first release.

## Confirmed direction and proposed scope

The owner requested a new library for eventual PyPI distribution, based on
`pydrawcv`, with tutorial properties such as labels, leader lines, and highlights.
They explicitly excluded improving DrawCV from this project and requested
documentation that allows another AI model to continue the work.

The following release scope is the initial design proposal. Detailed method
names and behavior can evolve with implementation and owner feedback.

## First-release author workflow

1. Create or load a DrawCV scene.
2. Register an existing object or DrawCV group as a teaching target.
3. Define reusable labels and leader lines attached to those targets.
4. Add named lesson steps.
5. Choose visible annotations, callouts, highlights, and dimming for each step.
6. Render one step or export all steps as PNG images.

## Feature expectations

| Feature | Initial behavior | Beyond the first release |
| --- | --- | --- |
| Target | Stable reference to one existing object or group | Arbitrary multi-object selections and subpaths |
| Anchor | Center or side midpoint of world-space bounds | Local points, endpoints, curve positions |
| Label | Short text with explicit side and offset | Collision-aware placement |
| Leader line | Straight line between the target anchor and text panel edge | Routed lines and obstacle avoidance |
| Callout | Wrapped explanatory text with padding and background | Rich text, equations, embedded media |
| Highlight | Padded rectangular outline around target bounds | Shape-following outlines and animation |
| Dimming | Reduce opacity of unrelated artwork in the rendered copy | Spotlight masks and camera effects |
| Step | Title, description, explicit annotations and attention state | Timing, transitions, branching |
| Output | PNG for one step or a numbered sequence | Video, HTML playback, PDF |

Collision avoidance is automatic as of 0.2.0a1. Authors may still need manual
position controls and clear warnings when content extends outside the canvas.
Long text must wrap or produce a clear layout error; it must not silently vanish.

## Example acceptance lesson

Use a simple diagram containing an outer cell, a nucleus, and another organelle.

- Step 1: Show the cell label and a general description.
- Step 2: Show the nucleus label and callout, highlight the nucleus, and dim
  unrelated artwork.
- Step 3: Show both labels for review, with no inherited dimming or highlights.

After moving the nucleus in the source scene, render again: its annotations
must follow it. Exporting step 3 before step 2 must produce the same results as
exporting in lesson order. The source drawing must retain its original styles
and contain no generated TutorDraw annotations after export.

## Success criteria

- A short Python script can produce this three-step lesson.
- Users work with their existing DrawCV shapes without replacing them.
- Exported text and pointers are legible and point at the intended targets.
- Errors identify the missing target, invalid option, or failed export.
- A new contributor can reproduce the example from documented setup steps.

## Later opportunities

Measurements, angle marks, braces, relation arrows, numbered markers,
before-and-after comparisons, progressive reveals, zoom/pan, timed captions,
narration, interactive prompts, accessibility descriptions, and reusable lesson
templates are useful extensions. They should build on the target/annotation/step
model rather than expand the first implementation all at once.

TutorDraw should not initially become a new graphics engine, video editor,
learning management system, GUI editor, or AI content-generation service.

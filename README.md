# AEP decode

Edit After Effects projects directly with your favourite LLM tool. Show it this GitHub.

Work in progress. I'm adding features as I go.

## What works

- Rename, move and organise project items into folders.
- Relink footage.
- Remove unused footage, reduce a project to chosen comps.
- Duplicate comps, change duration and frame rate.
- Duplicate layers, add solids and nulls, change in points.
- Set position, scale, rotation and opacity, with keyframes.
- Change text on text layers.
- Remove effects.
- Add Gaussian Blur, Fill, Invert and Tint, even if the project doesn't use them yet.
- Render in the background with `aerender` while you keep working.

Tested on macOS with After Effects 2026.

Built on [py_aep](https://github.com/forticheprod/py-aep) by Aurore Delaunay. Public domain.

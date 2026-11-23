# AGENTS.md — edit, clean up and render After Effects projects without After Effects

You are an LLM helping a designer with an After Effects project (`.aep`). You work in a terminal. You read and edit the project file directly with the Python library `py_aep`, and you render with `aerender` in the background while the designer keeps working.

Every claim below is marked:

- **[verified]** — run on macOS on 2026-11-17 with `uv` 0.12.5 and After Effects 2026, on a small test project (26.0) and on a real production project (419 comps, 270 effects, 13 text layers) saved by After Effects 2025, 2026 and 2027. For edits, "verified" means: saved, re-read, and then rendered by `aerender`, which has to open the file in After Effects to render it.
- **[unverified]** — from documentation or memory, not run here.

Nothing in this file has been run on Windows. Every Windows line is **[unverified]**.

## Guardrails

1. **Never open, script or automate After Effects.** No `osascript`, no ExtendScript, no MCP into After Effects.
2. **Never write to the file the designer gave you.** Copy it, edit the copy, save under a new versioned name (`project_v002.aep`, `_v003`, ...). `py_aep` refuses to save over an existing file.
3. **Only edit files saved by After Effects 2024, 2025, 2026 or 2027** (version `24.x`, `25.x`, `26.x`, `27.x`). Check first. Most edits here were proven on 2026; on 2025 and 2027 only reading, text changes, effect removal and adding effects were proven, and on 2024 only reading and adding effects, so treat everything else on those three as untested (rule 6). For older or newer versions say: "That can't be done without After Effects."
4. **Ask before anything that removes or overwrites.** Show the exact list first, wait for a yes, then do it. This covers:
   - removing items, comps, layers, effects, keyframes or markers inside the project, including "remove unused footage" and "reduce project";
   - moving, renaming or deleting files on disk. Prefer copying footage over moving it;
   - writing to a path that already exists, including render outputs (`aerender` overwrites silently);
   - deleting earlier versions or renders.
5. **Check every edit before you report it.** Re-read the saved file and confirm your values are there, then run a short `aerender` test render (Step 5). If either fails, say so, name the error, and stop. The designer still has the original.
6. **Say how sure you are.** Edits in the "verified" table: just do them. Edits in the "untested" list: do them on the copy, run the checks in rule 5, and tell the designer the edit type is untested and they should look at the result. Edits in the "not possible" list: "That can't be done without After Effects."
7. **Report in the designer's terms**: what changed, as values they can check, and the name of the file you wrote.

## How a project is put together

- A **project** is a tree of **items**, the same thing the Project panel shows. An item is a **folder**, a **comp**, or a **footage item**. Each item has a name and a parent folder; the top is the root folder.
- A **footage item** points at a file on disk by absolute path (or is a solid or placeholder with no file). The media is not inside the `.aep`. If the file is moved, the item goes missing until it is relinked.
- A **comp** has a size, frame rate, duration and a list of **layers**, top of the timeline first.
- A **layer** uses one item as its source (footage, a solid, or another comp, which is a precomp), or is a text, shape, null, camera or light layer with no source. Deleting an item that layers use breaks those layers, so check where it is used first.
- Every layer has **property groups**: Transform, Effects, Masks, and for text and shape layers their own contents. A **property** holds either one static value or **keyframes** (time in seconds, value). Properties are addressed by **match name**, a fixed internal name such as `ADBE Position`, not the name shown in the interface.
- An **expression** is stored as text on a property. `py_aep` can read it but cannot evaluate it; a property with an expression reports its stored value, not the expression's result.
- The **render queue** is stored in the project. Output and render templates are not; they live in each machine's After Effects preferences.
- Third-party plugin settings are stored as private data. Leave them alone; they pass through a save untouched.

## Setup

You need `uv` and `git`. `uv` fetches Python and `py_aep` on first run; `git` is needed because `py_aep` is pinned to a commit.

macOS:

```sh
uv --version                                        # [verified]
git --version                                       # [verified]
curl -LsSf https://astral.sh/uv/install.sh | sh     # [unverified] only if uv is missing
```

Windows (PowerShell), all **[unverified]**:

```powershell
uv --version
git --version
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
winget install Git.Git
```

There is no separate install step for `py_aep`. Put this header at the top of every script and run it with `uv run script.py` **[verified]**:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
```

## Step 1 — copy the project

```sh
cp -n "/path/to/project.aep" "/path/to/work/project.aep"                 # macOS [verified]
```

```powershell
Copy-Item "C:\path\to\project.aep" "C:\path\to\work\project.aep"         # Windows [unverified]
```

Footage is found by absolute path, so the copy can sit in another folder on the same machine. **[verified]**

## Step 2 — check the version and look inside

Save as `inspect_aep.py` **[verified]**:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
"""Usage: uv run inspect_aep.py <file.aep> [comp name]"""
import collections, sys
import py_aep

app = py_aep.parse(sys.argv[1])
project = app.project
only = sys.argv[2] if len(sys.argv) > 2 else None
print("After Effects version:", app.version)      # 27.x = AE 2027, 26.x = 2026, 25.x = 2025
if only is None:
    print("footage:", len(project.footages),
          "missing:", sum(1 for f in project.footages if f.footage_missing),
          "unused:", sum(1 for f in project.footages if not f.used_in))
    print("folders:", [(f.name, f.num_items) for f in project.folders])
for comp in project.compositions:
    if only is None:
        kinds = collections.Counter(type(l).__name__ for l in comp.layers)
        print(f"comp {comp.name!r}: {comp.duration:g} s, {comp.frame_rate:g} fps, {comp.width}x{comp.height}, "
              f"layers={dict(kinds)}, used in={[c.name for c in comp.used_in]}")
    elif comp.name == only:
        for n, layer in enumerate(comp.layers, 1):
            fx = [e.match_name for e in layer.effects.properties] if getattr(layer, "effects", None) else []
            print(f"layer {n} {type(layer).__name__} {layer.name!r} in={layer.in_point:g} out={layer.out_point:g} effects={fx}")
            for p in layer.transform.properties:
                if hasattr(p, "keyframes"):
                    keys = [(k.time, k.value) for k in p.keyframes]
                    print(f"    {p.match_name:24} {p.value}" + (f"  keys={keys}" if keys else ""))
```

```sh
uv run inspect_aep.py "/path/to/work/project.aep"                # whole project
uv run inspect_aep.py "/path/to/work/project.aep" "Comp name"    # one comp, layer by layer
```

## Step 3 — edit and save a new version

Every edit script has this shape **[verified]**. Put the edits between the two marked lines.

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
import os, re, sys
import py_aep

src = sys.argv[1]
app = py_aep.parse(src)
if app.version.split(".")[0] not in ("24", "25", "26", "27"):
    sys.exit(f"{src} was saved by After Effects {app.version}; only 24.x to 27.x are supported")
project = app.project

def item(name):
    hits = [i for i in project.items.values() if i.name == name]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} project items named {name!r}; need exactly 1")
    return hits[0]

def prop(layer, match_name):
    return next(p for p in layer.transform.properties if p.match_name == match_name)

# ---- edits start ----
comp = item("Comp name")
layer = comp.layers[0]
prop(layer, "ADBE Opacity").value = 50.0
# ---- edits end ----

stem, ext = os.path.splitext(src)
stem = re.sub(r"_v\d{3}$", "", stem)
n = 2
while os.path.exists(f"{stem}_v{n:03d}{ext}"):
    n += 1
out = f"{stem}_v{n:03d}{ext}"
project.save(out)
print(out)
```

```sh
uv run edit.py "/path/to/work/project.aep"     # writes project_v002.aep, then _v003, ...
```

### Verified edits

Each line below was saved, re-read and rendered. Text changes were also proven on text layers authored in After Effects, in 2025, 2026 and 2027 files.

```python
# Project panel
item("Old name").name = "New name"                           # rename any item
comps = project.root_folder.add_folder("01_COMPS")           # new folder
video = comps.add_folder("video")                            # nested folder
item("Comp name").parent_folder = comps                      # move an item into a folder
item("clip.mp4").replace("/new/absolute/path/clip.mp4")      # relink footage to another file
item("Old comp").remove()                                    # ASK FIRST. delete an item
project.remove_unused_footage()                              # ASK FIRST. returns how many were removed
project.reduce_project([item("Deliverable")])                # ASK FIRST. keep only these comps and what they use

# Comp
copy = comp.duplicate(); copy.name = "Comp name_alt"
copy.duration = 2.0                                          # seconds
copy.frame_rate = 25

# Layers (comp.layers is timeline order, top first)
dup = layer.duplicate(); dup.name = "copy"
dup.in_point = 1.0                                           # seconds
solid = comp.add_solid([1.0, 0.0, 0.0], "Red Solid", 720, 1280, 1.0)   # colour 0-1, name, width, height, pixel aspect
solid.move_to_end()                                          # send to the bottom
comp.add_null()
comp.layers[0].remove()                                      # ASK FIRST. delete a layer

# Transform: static values and keyframes
prop(layer, "ADBE Scale").value = [50.0, 50.0, 100.0]        # no keyframes on this property
opacity = prop(layer, "ADBE Opacity")
opacity.set_value_at_time(0.0, 100.0)                        # adds a keyframe, or changes the one at that time
opacity.set_value_at_time(2.0, 20.0)
prop(layer, "ADBE Position").set_value_at_time(0.0, [200.0, 640.0, 0.0])

# Text
text_layer = comp.add_text("Hello")
for tl in comp.text_layers:                                  # change many text layers in one pass
    tl["ADBE Text Properties"]["ADBE Text Document"].value.text = "New copy"

# Effects
for fx in list(layer.effects.properties):                    # ASK FIRST. remove effects from a layer
    print(fx.match_name); fx.remove()
effects_seed.load_seed(int(app.version.split(".")[0]) + 2000)   # once per script; see "Adding any effect" below
if layer.effects.can_add_property("ADBE Gaussian Blur 2"):   # True for any effect in the seed, or already used in the project
    blur = layer.effects.add_property("ADBE Gaussian Blur 2")
    next(p for p in blur.properties if p.match_name == "ADBE Gaussian Blur 2-0001").value = 25.0   # blurriness
```

### Adding any effect (effects seed)

`py_aep` can only add an effect whose full definition it can find. A project holds definitions only for effects it already uses. The folder `effects_seed/` holds one project per After Effects version with every installed effect applied once (`AllEffects_AE2024.aep` ... `AllEffects_AE2027.aep`), and `tools/effects_seed.py` copies those definitions into `py_aep` so `add_property` works for any of them. **[verified]**

```python
import sys
sys.path.insert(0, "/path/to/aep-decode/tools")     # this repo's tools folder
import effects_seed
effects_seed.load_seed(2026)                          # the seed matching the file's version: 24.x -> 2024, ... 27.x -> 2027
```

- Use the seed whose year matches the file. Seeds from other years also work (2024 into 2025, 2026 and 2027 files; 2027 into 2025 and 2026 files), but they bring that year's defaults: Gaussian Blur's Blurriness defaults to 0 in the 2024 seed and 25 from 2025 on.
- What each effect's parameters are called, their types, defaults, ranges and dropdown options: `effects_seed/effects_AE<year>.json`. What changed between versions: `effects_seed/effects_diff.md`.
- Proven by adding Gaussian Blur, Fill, Invert and Tint, setting a value, saving, re-reading and checking the rendered picture, in a 2024, 2025, 2026 and 2027 file each (2025 checked with a frame saved by After Effects 2025 itself, because its `aerender` does not start on the test machine). The other ~440 effects have not each been rendered: tell the designer which effects you added and ask them to look. Effects that store extra data (Curves, Levels) are the most likely to need care.
- Not in any seed: Cineware (needs Cinema 4D), Apply Color LUT, Basic Text, Path Text and Numbers (they open a dialog when applied; Apply Color LUT is in the 2024 seed only). Dropdown Control is not in the seeds; `py_aep` creates it itself.
- A new After Effects version needs a new seed, and making one needs After Effects: "That can't be done without After Effects" until someone makes one.

Notes, all **[verified]**:

- Transform match names: `ADBE Anchor Point`, `ADBE Position`, `ADBE Scale`, `ADBE Opacity`, `ADBE Rotate Z` (2D rotation), `ADBE Rotate X`, `ADBE Rotate Y`, `ADBE Orientation`. Position, scale and anchor point take `[x, y, z]`, also on 2D layers. Opacity and scale are percent.
- On a property that has keyframes, use `set_value_at_time`, not `.value`.
- Without the effects seed, an effect can be added only if the same effect is already used somewhere in that project; with it, any effect in the seed can be added (see "Adding any effect"). `can_add_property` tells you. Effect parameters are addressed by match name, the effect's match name plus a number (`-0001`, `-0002`, ...); print them, or look them up in `effects_seed/effects_AE<year>.json`.
- Effect removal was saved, re-read and rendered without error in 2025, 2026 and 2027 files; the difference in the picture was too subtle to confirm by eye, so look at the result.
- Changing text does not resize or reposition anything. Longer copy can overlap its neighbours; say so.
- Many comps can share one name (the production project has 12 called the same). Find the one you mean by where it sits or what it contains, and address it by `comp.id`, not by name.
- Text must be changed in place with `.value.text = ...`. Assigning a new value to the text property raises an error.
- Before any "ASK FIRST" line, print what it would remove and show the designer. Examples:
  `[f.name for f in project.footages if not f.used_in]` for unused footage; `[c.name for c in item("clip.mp4").used_in]` for where an item is used.

### Tidying footage on disk

To gather stray footage into a folder next to the project: copy each file (do not move it), then relink the item to the copy with `.replace(new_path)`, then save a new version. Copy and relink are each **[verified]**; a whole-project gather has not been run. Moving or deleting the old files is a separate step that needs the designer's yes.

### Untested here — do it on the copy, check it, tell the designer it is untested

`py_aep` offers these, but they have not been run in this repo: effect parameter values other than the one above, masks, shape layer contents, writing expressions, markers, `project.replace_font(...)`, `project.consolidate_footage()`, `project.import_file(...)`, layer parenting, time remap, adding render queue items.

### Not possible

- Adding an effect that is neither in the project nor in the effects seed (third-party plugins, Cineware, the dialog effects listed above): `py_aep` refuses it. **[verified]**
- Seeing what a frame looks like, what an expression evaluates to, or what an effect outputs. Render with `aerender` and look at the result instead.
- Editing third-party plugin settings.
- Files saved by versions other than After Effects 2024, 2025, 2026 and 2027.

For these: "That can't be done without After Effects."

## Step 4 — re-read the saved file

```sh
uv run inspect_aep.py "/path/to/work/project_v002.aep" "Comp name"     # [verified] your values must be in this output
```

## Step 5 — render with aerender

`aerender` ships with After Effects. It renders the `.aep` saved on disk and starts its own After Effects process, about 15 s of start-up per call. Use the `aerender` of the same year as the file; 2025, 2026 and 2027 each rendered their own file. **[verified]**

```sh
ls -d /Applications/Adobe\ After\ Effects*                        # macOS [verified] which years are installed
"/Applications/Adobe After Effects 2026/aerender" -help           # macOS [verified]
```

```powershell
& "C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\aerender.exe" -help     # Windows [unverified]
```

**If the comp's name is not unique, `aerender -comp` renders the first comp with that name, which may not be yours, and reports success.** **[verified]** Make a render-only copy in which your comp has a unique name, and render that. Save as `render_copy.py` **[verified]**:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
"""Usage: uv run render_copy.py <src.aep> <comp id> <out.aep>"""
import sys
import py_aep

src, comp_id, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
project = py_aep.parse(src).project
print("comps sharing this name:", [c.id for c in project.compositions if c.name == project.items[comp_id].name])
project.items[comp_id].name = "RENDER_TARGET"
project.save(out)
```

```sh
uv run render_copy.py "/path/to/work/project_v002.aep" 19285 "/path/to/work/project_v002_render.aep"
```

Then pass `-comp RENDER_TARGET`. The render-only copy is not a version for the designer; do not hand it over.

**Test render** after every edit: three frames spread over 1.5 s. If After Effects cannot open the file, this is where it shows. **[verified]**

```sh
"/Applications/Adobe After Effects 2026/aerender" \
  -project "/path/to/work/project_v002.aep" -comp "Comp name" \
  -s 0 -e 44 -i 15 \
  -OMtemplate "H.264 - Match Render Settings - 15 Mbps" \
  -output "/path/to/work/project_v002_test.mp4" > "/path/to/work/project_v002_test.log" 2>&1
grep -E "aerender ERROR|Finished composition" "/path/to/work/project_v002_test.log"
```

**Full render in the background** so the designer can keep working. **[verified]**

```sh
nohup "/Applications/Adobe After Effects 2026/aerender" \
  -project "/path/to/work/project_v002.aep" -comp "Comp name" \
  -OMtemplate "H.264 - Match Render Settings - 15 Mbps" \
  -output "/path/to/work/project_v002.mp4" > "/path/to/work/project_v002_render.log" 2>&1 &
```

Check on it whenever asked **[verified]**:

```sh
grep -E "\([0-9]+\): [0-9]+ Seconds" "/path/to/work/project_v002_render.log" | tail -1    # last frame done
grep -E "aerender ERROR|Finished composition" "/path/to/work/project_v002_render.log"       # finished or failed
```

Windows background render, **[unverified]**:

```powershell
Start-Process -FilePath "C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\aerender.exe" `
  -ArgumentList '-project "C:\work\project_v002.aep" -comp "Comp name" -OMtemplate "H.264 - Match Render Settings - 15 Mbps" -output "C:\work\project_v002.mp4"' `
  -RedirectStandardOutput "C:\work\project_v002_render.log" -WindowStyle Hidden
```

Flags:

- `-project`, `-comp`, `-output`: full paths. **[verified]**
- `-s`, `-e`: first and last frame, both included; `-s 0 -e 59` is 60 frames. Leave both out for the whole comp. `-i 15` renders every 15th frame. **[verified]**
- `-OMtemplate`: always pass it. Without it you get that machine's default output template, which can be anything. **[verified]** Template names live in that machine's After Effects preferences; a missing name is an error. **[unverified]**
- `-RStemplate "Best Settings"`, `-close DO_NOT_SAVE_CHANGES`, `-mem_usage <cache %> <total %>`, `-log <file>`, `-v ERRORS_AND_PROGRESS`: accepted, render completed. **[verified]** With `-log` the lines end in carriage returns, so prefer redirecting output as above.
- `-reuse`, `-continueOnMissingFootage`: listed in `-help`, not tried. **[unverified]**

What the output looks like **[verified]**:

```
aerender version 26.0x67
PROGRESS: Launching After Effects...
PROGRESS:  17/11/2026 2:46:45 pm GMT+11: Starting composition “Comp name”.
PROGRESS:  0:00:00:00 (1): 0 Seconds
PROGRESS:  0:00:00:01 (2): 0 Seconds
...
PROGRESS:  17/11/2026 2:46:46 pm GMT+11: Finished composition “Comp name”.
PROGRESS:  Total Time Elapsed: 2 Seconds
```

- One line per frame: timecode, frame count from 1, seconds for that frame. Some lines go missing; read the last one, do not count them.
- Success is the `Finished composition` line plus the output file existing.
- **The exit code is useless.** A wrong comp name printed `aerender ERROR: No comp was found with the given name.` and exited 0. Search the output for `aerender ERROR`.
- An existing output file is overwritten without warning. Give each render a new name.
- The `.aep` is not modified by rendering. A folder `<project>.aep Logs` appears next to it.
- After Effects 2027 was open while `aerender` 2025, 2026 and 2027 ran. Every render completed and the open app kept running. **[verified]**
- A project with 53 missing footage items still rendered a comp that did not use them. **[verified]**
- `aerender` renders what is on disk. Unsaved changes in the designer's open After Effects are not in the render, and their open project does not pick up your new version. Tell them which file you wrote. **[unverified]**

Optional check of a render, if `ffprobe` is installed **[verified]**:

```sh
ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=codec_name,width,height,nb_read_frames -of default=nw=1 "/path/to/work/project_v002.mp4"
```

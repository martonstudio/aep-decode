# AGENTS.md — amending and rendering After Effects projects without After Effects

You are an LLM helping a designer who asks for amends to an `.aep` file. You work in a terminal.

Every claim below is marked:

- **[verified]** — run on macOS on 2026-11-17 with After Effects 2026 (26.0x67), `uv` 0.12.5, and the result observed.
- **[unverified]** — from documentation or memory, not run. Treat it as a guess and tell the designer if it fails.

Nothing in this file has been run on Windows. Every Windows line is **[unverified]**.

## Rules

1. Never open, script or automate After Effects. No `osascript`, no ExtendScript, no MCP into After Effects. Edits happen in the file; rendering happens with `aerender`.
2. Never write to the file the designer gave you. Copy it, edit the copy, save under a new versioned name.
3. Only make the edits listed under "What you can change". For anything else, tell the designer: **"That can't be done without After Effects."** Do not try another route.
4. Only edit files saved by After Effects 2026 (version `26.x`). Check before editing.
5. Report what you changed as values the designer can check ("layer 'logo' opacity now goes 100 → 20 over the first 2 s"), and say which file you wrote.

## What you can change

| Edit | Status |
|---|---|
| Rename an item in the Project panel (folder, comp, footage) | **[verified]** by re-reading the saved file |
| Set a transform value on a layer: anchor point, position, scale, rotation, orientation, opacity | **[verified]** by render |
| Add or change keyframes on those transform properties | **[verified]** by render |

## What you cannot change

Effects, masks, shape layer contents, expressions, text, and any file not saved by After Effects 2026.
For all of these: "That can't be done without After Effects."

## Setup

You need `uv` and `git`. `uv` fetches Python and `py_aep` on first run; `git` is needed because `py_aep` is pinned to a commit.

macOS:

```sh
uv --version                                        # [verified] prints the version if installed
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

There is no separate install step for `py_aep`. Each script below carries its dependency in its header, and `uv run script.py` installs it. **[verified]** on macOS. Whether `uv` downloads Python on a machine with none is **[unverified]**.

Keep this header at the top of every script you write:

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

Footage is found by its absolute path, so the copy can live in another folder on the same machine. **[verified]** for one video file.

## Step 2 — check the After Effects version

Save as `aep_version.py`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
import sys
import py_aep

print(py_aep.parse(sys.argv[1]).version)
```

```sh
uv run aep_version.py "/path/to/work/project.aep"     # [verified] prints e.g. 26.0x67
```

The number before the dot is the release: `26` = After Effects 2026, `25` = 2025, `24` = 2024. If it is not `26`, stop and tell the designer.

## Step 3 — look at what is in the file

Save as `list.py`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
"""Usage: uv run list.py <file.aep> [comp name]"""
import sys
import py_aep

project = py_aep.parse(sys.argv[1]).project
only = sys.argv[2] if len(sys.argv) > 2 else None
for it in project.items.values():
    if only is None:
        print(f"{type(it).__name__:12} {it.name!r}")
for comp in project.compositions:
    if only is not None and comp.name != only:
        continue
    print(f"\ncomp {comp.name!r}: {comp.duration:g} s, {comp.frame_rate:g} fps, {comp.width}x{comp.height}")
    for n, layer in enumerate(comp.layers, 1):
        print(f"  layer {n} {type(layer).__name__} {layer.name!r}")
        for p in layer.transform.properties:
            if hasattr(p, "keyframes"):
                keys = [(k.time, k.value) for k in p.keyframes]
                print(f"    {p.match_name:24} {p.value}" + (f"  keys={keys}" if keys else ""))
```

```sh
uv run list.py "/path/to/work/project.aep"                 # [verified] all items, all comps
uv run list.py "/path/to/work/project.aep" "Comp name"     # [verified] one comp
```

Transform properties are addressed by match name **[verified]**:
`ADBE Anchor Point`, `ADBE Position`, `ADBE Scale`, `ADBE Opacity`, `ADBE Rotate Z` (2D rotation), `ADBE Rotate X`, `ADBE Rotate Y`, `ADBE Orientation`.
Position, scale and anchor point take three numbers `[x, y, z]`, also on 2D layers. Opacity and scale are in percent. Times are in seconds.

## Step 4 — amend and save a new version

Save as `amend.py` and change only the block between the two marked lines. This exact script is **[verified]**.

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b"]
# ///
import os, re, sys
import py_aep

src = sys.argv[1]
app = py_aep.parse(src)
if not app.version.startswith("26."):
    sys.exit(f"{src} was saved by After Effects {app.version}; only 26.x (AE 2026) is supported")
project = app.project

def item(name):
    hits = [i for i in project.items.values() if i.name == name]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} project items named {name!r}; need exactly 1")
    return hits[0]

def prop(layer, match_name):
    return next(p for p in layer.transform.properties if p.match_name == match_name)

# ---- amends start ----
comp = item("STAGE1_TEST")
layer = comp.layers[0]                                      # layers are in timeline order, top first

item("Solids").name = "Solids_renamed"                      # rename a Project panel item
prop(layer, "ADBE Scale").value = [50.0, 50.0, 100.0]       # static value
opacity = prop(layer, "ADBE Opacity")
opacity.set_value_at_time(0.0, 100.0)                       # keyframe at 0 s
opacity.set_value_at_time(2.0, 20.0)                        # keyframe at 2 s
position = prop(layer, "ADBE Position")
position.set_value_at_time(0.0, [200.0, 640.0, 0.0])
position.set_value_at_time(2.0, [520.0, 640.0, 0.0])
# ---- amends end ----

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
uv run amend.py "/path/to/work/project.aep"     # [verified] writes project_v002.aep, then _v003, ...
```

- `.value = ...` sets a property that has no keyframes. `set_value_at_time(seconds, value)` adds a keyframe, or changes the one already at that time. On a property with keyframes, always use `set_value_at_time`. **[verified]**
- Calling `set_value_at_time` on a property with no keyframes turns it into a keyframed one. **[verified]**
- Easing of new keyframes is whatever `py_aep` writes by default; setting easing is **[unverified]**.
- After saving, run `list.py` on the new file and check your values are there before telling the designer. **[verified]**

## Step 5 — render with aerender

`aerender` ships with After Effects. It renders the `.aep` that is saved on disk and starts its own After Effects process in the background.

macOS **[verified]** for 2026:

```sh
ls -d /Applications/Adobe\ After\ Effects*          # which years are installed
"/Applications/Adobe After Effects 2026/aerender" -help
```

Windows **[unverified]**:

```powershell
& "C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\aerender.exe" -help
```

Use the `aerender` of the same year as the file (2026).

Render one comp, **[verified]** on macOS:

```sh
"/Applications/Adobe After Effects 2026/aerender" \
  -project "/path/to/work/project_v002.aep" \
  -comp "STAGE1_TEST" \
  -s 0 -e 59 \
  -RStemplate "Best Settings" \
  -OMtemplate "H.264 - Match Render Settings - 15 Mbps" \
  -close DO_NOT_SAVE_CHANGES \
  -mem_usage 20 50 \
  -v ERRORS_AND_PROGRESS \
  -output "/path/to/work/project_v002.mp4"
```

Windows **[unverified]**: same flags, `aerender.exe` path as above, `` ` `` instead of `\` for line breaks.

Flags:

- `-project`, `-comp`, `-output`: use full paths. **[verified]**
- `-s`, `-e`: first and last frame, both included. `-s 0 -e 59` gave 60 frames, 2.0 s at 30 fps. **[verified]** Leave both out to render the whole comp. **[unverified]**
- `-OMtemplate`: always pass it. Without it you get that machine's default output module, which may be anything (on the test machine it was a custom ProRes template). **[verified]** Template names live in that machine's After Effects settings; a name that does not exist is an error. **[unverified]**
- `-RStemplate "Best Settings"`, `-close DO_NOT_SAVE_CHANGES`, `-mem_usage <cache %> <total %>`, `-log <file>`: accepted and the render completed. **[verified]**
- `-reuse` (render in an After Effects that is already running) and `-continueOnMissingFootage`: listed in `-help`, not tried. **[unverified]**

What it prints **[verified]**:

```
aerender version 26.0x67
PROGRESS: Launching After Effects...
PROGRESS:  17/11/2026 2:46:45 pm GMT+11: Starting composition “STAGE1_TEST”.
PROGRESS:  Output Module: H.264 - Match Render Settings - 15 Mbps
PROGRESS:  0:00:00:00 (1): 0 Seconds
PROGRESS:  0:00:00:01 (2): 0 Seconds
...
PROGRESS:  0:00:01:29 (60): 0 Seconds
PROGRESS:  17/11/2026 2:46:46 pm GMT+11: Finished composition “STAGE1_TEST”.
PROGRESS:  Total Time Elapsed: 2 Seconds
```

- One line per frame: timecode, frame count starting at 1, seconds that frame took. Some frame lines go missing, so do not count lines to measure progress.
- Success is the `Finished composition` line plus the output file existing.
- **The exit code is useless.** A wrong comp name printed `aerender ERROR: No comp was found with the given name.` and still exited 0; `-version` exits 15. Search the output for `aerender ERROR` instead.
- An existing output file is overwritten without warning. Give each render a new name.
- Starting After Effects costs about 15 s per call, on top of the render time.
- The `.aep` is not modified by rendering. A folder `<project>.aep Logs` appears next to it.
- With `-log <file>` the log lines end in carriage returns, not newlines.

After Effects open on the same machine:

- After Effects 2027 was open while `aerender` 2026 ran. The render completed and the open app was not disturbed. **[verified]**
- The same year open at the same time (2026 open, `aerender` 2026 running) is **[unverified]**.
- `aerender` reads the file on disk. Changes the designer has not saved are not in the render, and the designer's open copy does not pick up your new version. Tell them the name of the file you wrote. **[unverified]**

Optional check of the result, if `ffprobe` is installed **[verified]**:

```sh
ffprobe -v error -select_streams v:0 -count_frames \
  -show_entries stream=codec_name,width,height,nb_read_frames -of default=nw=1 "/path/to/work/project_v002.mp4"
```

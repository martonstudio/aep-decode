# AEP decode

Let your LLM edit, tidy and render After Effects projects without opening After Effects.

Point Claude Code, Codex or any agent with a terminal at [AGENTS.md](AGENTS.md). It teaches the agent how a project file is put together, how to change it directly, and how to render in the background with `aerender`.

- Works on a copy. Your original is never written to.
- Asks before it removes anything.
- Checks every edit with a test render before it tells you it's done.

Tested on macOS with After Effects 2025, 2026 and 2027. Windows is written up but not tested yet. After Effects has to be installed for rendering.

Built on [py_aep](https://github.com/forticheprod/py-aep) by Aurore Delaunay. That library does the reading and writing; this repo is the instruction set and the proof of which edits survive After Effects.

If something breaks, tell me what you asked for, the command that failed, and the error.

## Method

Script After Effects to change one setting. Save. Diff the chunk. Repeat.

That's it.

## Editor

A bare editor in the browser. Project panel, timeline, transform values, keyframes, save. No viewer.

```
cd shell
uv run server.py
```

Open `http://127.0.0.1:8765`.

Not click-tested yet. If something breaks, tell me what you did.

## Tools

`tools/gap.py` counts the chunks and bytes py_aep can't read yet. Give it a text file with one `.aep` path per line.

`tools/gap2.py` does the same per field. Give it a folder with `aep_list.txt` inside.

## License

Public domain. Do whatever you want with it.

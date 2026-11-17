# AEP decode

Open, edit and save After Effects 2026 project files without After Effects.

Built on [py_aep](https://github.com/forticheprod/py-aep). Install it separately.

Work on copies. Keep your originals.

Using an LLM to amend and render a project? Point it at [AGENTS.md](AGENTS.md).

## Method

Script After Effects to change one setting. Save. Diff the chunk. Repeat.

That's it. `PLAN.md` lists what is decoded, what isn't, and the order I'm going in.

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

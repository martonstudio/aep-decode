# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "py-aep @ git+https://github.com/forticheprod/aep_parser@e12a451c35bacd3f34a080090265f9370e66162b",
# ]
# ///
"""Blind editor shell backend: holds one .aep in memory via py_aep and serves it as JSON.

No pixels are read or produced anywhere. Run with: uv run server.py [--port 8765]
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import py_aep

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {"app": None, "path": None}


def _num(v):
    """Return v as a float or list of floats, or None if it is not numeric."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)) and v and all(isinstance(x, (int, float)) for x in v):
        return [float(x) for x in v]
    return None


def _project():
    if STATE["app"] is None:
        raise ValueError("no project open")
    return STATE["app"].project


def _comp(comp_id):
    for c in _project().compositions:
        if c.id == comp_id:
            return c
    raise ValueError(f"no composition with id {comp_id}")


def _layer(comp_id, layer_id):
    for layer in _comp(comp_id).layers:
        if layer.id == layer_id:
            return layer
    raise ValueError(f"no layer with id {layer_id} in composition {comp_id}")


def _transform_prop(layer, match_name):
    for prop in layer.transform.properties:
        if prop.match_name == match_name:
            return prop
    raise ValueError(f"no transform property {match_name}")


def _prop_json(prop, time):
    value = _num(getattr(prop, "value", None))
    if value is None:
        return None
    keys = [k.time for k in prop.keyframes]
    if keys:
        at = _num(prop.value_at_time(time))
        if at is not None:
            value = at
    return {"name": prop.name, "match_name": prop.match_name, "value": value, "keys": keys}


def _layer_json(layer, number, time):
    props = []
    for prop in layer.transform.properties:
        if not hasattr(prop, "keyframes"):
            continue
        pj = _prop_json(prop, time)
        if pj is not None:
            props.append(pj)
    return {
        "id": layer.id,
        "number": number,
        "name": layer.name,
        "type": type(layer).__name__,
        "label": getattr(layer.label, "value", layer.label),
        "is_3d": bool(layer.three_d_layer),
        "in_point": layer.in_point,
        "out_point": layer.out_point,
        "transform": props,
    }


def _state_json(comp_id=None, time=0.0):
    project = _project()
    items = []
    for item in project.items.values():
        parent = getattr(item, "parent_folder", None)
        if parent is None:
            continue  # the root folder itself
        items.append({
            "id": item.id,
            "name": item.name,
            "type": type(item).__name__,
            "parent": parent.id,
        })
    comps = project.compositions
    comp = None
    if comps:
        c = _comp(comp_id) if comp_id is not None else comps[0]
        comp = {
            "id": c.id,
            "name": c.name,
            "width": c.width,
            "height": c.height,
            "duration": c.duration,
            "frame_rate": c.frame_rate,
            "layers": [_layer_json(layer, n, time) for n, layer in enumerate(c.layers, 1)],
        }
    return {
        "path": STATE["path"],
        "root": project.root_folder.id,
        "items": items,
        "comp": comp,
        "time": time,
    }


def api_open(body):
    path = os.path.expanduser(body["path"])
    STATE["app"] = py_aep.parse(path)
    STATE["path"] = path
    return _state_json()


def api_set(body):
    """Set a transform value. Like After Effects: on a keyframed property this writes a key at the current time."""
    layer = _layer(body["comp"], body["layer"])
    prop = _transform_prop(layer, body["match_name"])
    value = body["value"]
    if prop.keyframes:
        prop.set_value_at_time(body["time"], value)
    else:
        prop.value = value
    return _state_json(body["comp"], body["time"])


def api_key(body):
    """Add a keyframe at the current time holding the property's current value."""
    layer = _layer(body["comp"], body["layer"])
    prop = _transform_prop(layer, body["match_name"])
    time = body["time"]
    value = prop.value_at_time(time) if prop.keyframes else prop.value
    prop.set_value_at_time(time, value)
    return _state_json(body["comp"], time)


def api_save(body):
    path = os.path.expanduser(body["path"])
    if os.path.exists(path):
        raise ValueError(f"{path} already exists; choose a new name")
    _project().save(path)
    return {"saved": path, "bytes": os.path.getsize(path)}


POST_ROUTES = {"/api/open": api_open, "/api/set": api_set, "/api/key": api_key, "/api/save": api_save}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, content_type="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif url.path == "/api/state":
            q = parse_qs(url.query)
            try:
                comp = int(q["comp"][0]) if "comp" in q else None
                self._send(200, _state_json(comp, float(q.get("t", ["0"])[0])))
            except Exception as e:
                self._send(400, {"error": f"{type(e).__name__}: {e}"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        route = POST_ROUTES.get(urlparse(self.path).path)
        if route is None:
            self._send(404, {"error": "not found"})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._send(200, route(body))
        except Exception as e:
            self._send(400, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"blind editor shell on http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

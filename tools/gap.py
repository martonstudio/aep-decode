import struct, sys, collections, os, re, importlib, pkgutil, time, io
import attrs, py_aep, py_aep.binary as B
for m in pkgutil.iter_modules(B.__path__): importlib.import_module("py_aep.binary." + m.name)
from py_aep.binary.registry import CHUNK_TYPES
from py_aep.binary.fmt_field import _struct_info
OPAQUE = re.compile(r"reserved|unknown|padding|^_?unk", re.I)

layout = {}
for tag, cls in CHUNK_TYPES.items():
    try: info = _struct_info(cls)
    except Exception: info = None
    known = opaque = 0; names = []
    if attrs.has(cls):
        for f in attrs.fields(cls):
            fmt = f.metadata.get("fmt")
            if not fmt: continue
            n = struct.calcsize(">" + fmt)
            if OPAQUE.search(f.name): opaque += n; names.append(f.name)
            else: known += n
    layout[tag] = (cls.__name__, info is not None, known, opaque)

def walk(buf, pos, end, counts, sizes):
    while pos + 8 <= end:
        tag = buf[pos:pos+4].decode("latin1"); size = struct.unpack(">I", buf[pos+4:pos+8])[0]; body = pos + 8
        if tag == "LIST":
            lt = buf[body:body+4].decode("latin1")
            if lt == "btdk": counts["LIST:btdk"] += 1; sizes["LIST:btdk"] += size
            else: walk(buf, body + 4, body + size, counts, sizes)
        else: counts[tag] += 1; sizes[tag] += size
        pos = body + size + (size & 1)

paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
paths = [p for p in paths if os.path.exists(p) and os.path.getsize(p) < 20_000_000][:60]
C, Z = collections.Counter(), collections.Counter(); files_with = collections.Counter()
ok = ident = 0; fails = []; vers = collections.Counter()
for p in paths:
    buf = open(p, "rb").read()
    if buf[:4] != b"RIFX": fails.append((os.path.basename(p), "not RIFX")); continue
    c, z = collections.Counter(), collections.Counter()
    walk(buf, 12, 8 + struct.unpack(">I", buf[4:8])[0], c, z)
    C.update(c); Z.update(z)
    for t in c: files_with[t] += 1
    try:
        t0 = time.time(); app = py_aep.parse(p); ok += 1
        vers[str(getattr(app, "version", "?"))[:6]] += 1
        dst = os.path.join(os.path.dirname(sys.argv[1]), "rt_tmp.aep"); app.project.save(dst)
        if open(dst, "rb").read() == buf: ident += 1
        else: fails.append((os.path.basename(p), "round-trip differs"))
    except Exception as e:
        fails.append((os.path.basename(p), f"{type(e).__name__}: {str(e)[:120]}"))

tot = sum(Z.values())
unreg = {t for t in C if t not in CHUNK_TYPES and t != "LIST:btdk"}
ub = sum(Z[t] for t in unreg)
raw = {t for t in C if t in CHUNK_TYPES and not layout[t][1] and layout[t][2] + layout[t][3] == 0}
rb = sum(Z[t] for t in raw)
ob = sum(min(Z[t], C[t] * layout[t][3]) for t in C if t in CHUNK_TYPES)
print(f"files scanned: {len(paths)}  parsed OK: {ok}  byte-identical round-trip: {ident}")
print("AE versions:", dict(vers))
print("failures:", fails[:12])
print(f"total chunk payload bytes: {tot}")
print(f"  unregistered chunk types: {len(unreg)} tags, {ub} bytes ({100*ub/tot:.2f}%)")
print(f"  registered, fields named reserved/unknown: {ob} bytes ({100*ob/tot:.2f}%)")
print(f"  registered with no declared field layout (custom code or raw): {len(raw)} tags, {rb} bytes ({100*rb/tot:.2f}%)")
print(f"  text engine block (LIST:btdk): {Z['LIST:btdk']} bytes ({100*Z['LIST:btdk']/tot:.2f}%)")
print("\nUNREGISTERED tag / instances / bytes / files:")
for t in sorted(unreg, key=lambda t: -Z[t]): print(f"  {t!r:8} {C[t]:6} {Z[t]:9} {files_with[t]:3}")
print("\nOPAQUE FIELDS inside registered chunks (tag class known_bytes opaque_bytes per instance, instances):")
for t in sorted((t for t in C if t in CHUNK_TYPES and layout[t][3]), key=lambda t: -C[t]*layout[t][3]):
    n, _, k, o = layout[t]; print(f"  {t!r:8} {n:28} known {k:4} opaque {o:4}  x{C[t]}")
print("\nNO DECLARED LAYOUT (top by bytes):")
for t in sorted(raw, key=lambda t: -Z[t])[:25]: print(f"  {t!r:8} {layout[t][0]:28} x{C[t]:6} {Z[t]:10} bytes")

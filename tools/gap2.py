import sys, os, re, glob, collections, importlib, pkgutil, struct, tempfile
import attrs, py_aep, py_aep.binary as B
for m in pkgutil.iter_modules(B.__path__): importlib.import_module("py_aep.binary." + m.name)
from py_aep.binary.chunk import read_aep
OPAQUE = re.compile(r"reserved|unknown|padding|^_?unk", re.I)
S = sys.argv[1]
mine = [l.strip() for l in open(os.path.join(S, "aep_list.txt")) if l.strip()]

print("ROUND-TRIP (your projects, unmodified read -> save):")
for i, p in enumerate(mine):
    try:
        buf = open(p, "rb").read(); app = py_aep.parse(p)
        dst = os.path.join(S, "rt", f"rt_{i}.aep"); app.project.save(dst)
        new = open(dst, "rb").read(); os.remove(dst)
        print(f"  {os.path.basename(p):28} {len(buf):>10} bytes  identical={new == buf}")
    except Exception as e:
        print(f"  {os.path.basename(p):28} FAILED {type(e).__name__}: {str(e)[:150]}")

def it(ch):
    yield ch
    subs = getattr(ch, "chunks", None)
    if subs is None and type(ch).__name__ == "ContainerChunk":
        try: subs = list(ch)
        except Exception: subs = None
    for s in subs or []:
        yield from it(s)

def nz(v):
    if isinstance(v, (bytes, bytearray)): return any(v)
    return bool(v)

corpus = mine + sorted(glob.glob(os.path.join(S, "aep_parser/samples/**/*.aep"), recursive=True))
stat = {}  # (tag, field) -> [size, instances, nonzero, distinct values]
files = bad = 0
for p in corpus:
    if os.path.getsize(p) > 40_000_000: continue
    try:
        with open(p, "rb") as fp: root, _ = read_aep(fp)
    except Exception:
        bad += 1; continue
    files += 1
    for ch in it(root):
        cls = type(ch)
        if not attrs.has(cls): continue
        for f in attrs.fields(cls):
            fmt = f.metadata.get("fmt")
            if not fmt or not OPAQUE.search(f.name): continue
            v = getattr(ch, f.name, None)
            if v is None: continue
            s = stat.setdefault((ch.chunk_type, f.name), [struct.calcsize(">" + fmt), 0, 0, set()])
            s[1] += 1
            if nz(v):
                s[2] += 1
                if len(s[3]) < 40: s[3].add(v if not isinstance(v, (bytes, bytearray)) else bytes(v))
print(f"\nRESERVED/UNKNOWN FIELDS over {files} files ({len(mine)} yours + py_aep samples, {bad} unreadable):")
always0 = [(k, v) for k, v in stat.items() if v[2] == 0]
live = [(k, v) for k, v in stat.items() if v[2] > 0]
print(f"  fields total: {len(stat)}   always zero (true padding): {len(always0)}, {sum(v[0] for _, v in always0)} bytes of layout")
print(f"  carry data in at least one file: {len(live)}, {sum(v[0] for _, v in live)} bytes of layout")
for (tag, name), (size, n, z, vals) in sorted(live, key=lambda kv: -kv[1][2]):
    print(f"  {tag!r:7} {name:24} {size:5}B  nonzero {z:7}/{n:<7} distinct>={len(vals)}")

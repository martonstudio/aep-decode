"""Post-import fix for PNG footage items created by py_aep (pin e12a451).

py_aep writes an EMPTY `opti` chunk for a single PNG (file_formats.py: ".png" -> opti "empty")
and leaves sspc bytes 0x3f-0x41 (bits per pixel, 2 flags) and data_size (0xd0) at zero.
AE writes a `png!` header in opti (dims, bit depth, colour type, rowbytes, file name)
and fills those sspc fields. AE 2027's PNG importer reads the cached header from opti and
crashes (PNGIOp_UpdateHeaderFromPNGInfo, null+4) when it is empty.
"""
import io, struct
from pathlib import Path

def png_header(path):
    with open(path, 'rb') as f:
        h = f.read(33)
    assert h[:8] == b'\x89PNG\r\n\x1a\n' and h[12:16] == b'IHDR'
    w, hh, bd, ct = struct.unpack('>IIBB', h[16:26])
    return w, hh, bd, ct

def build_png_opti(path, total=322):
    """AE's `png!` opti body, byte layout copied from AE-written projects (2026: 322 bytes)."""
    path = Path(path)
    w, h, bd, ct = png_header(path)
    bytes_per_px = 4 * max(bd // 8, 1)
    body = (b'png!' + struct.pack('>HI', 1, total)
            + bytes.fromhex('0100000000000001')
            + struct.pack('>IIIIi', w, h, bd, 0, ct)
            + b'\x00' * 8
            + struct.pack('>III', 4, w * bytes_per_px, 0))
    assert len(body) == 0x3a
    name = path.name.encode('utf-8')[: total - 0x3a - 1]
    body += name + b'\x00' * (total - 0x3a - len(name))
    assert len(body) == total
    return body

def fix_png_item(item, *, opti=True, sspc=True):
    """Make a py_aep PNG FootageItem match what AE writes. Call after import_file / replace."""
    from py_aep.binary.footage_chunks import OptiChunk  # noqa
    src = item.main_source
    path = Path(src._file)
    if path.suffix.lower() != '.png':
        return
    w, h, bd, ct = png_header(path)
    if opti:
        data = build_png_opti(path)
        src._swap_opti(OptiChunk.read(io.BytesIO(data), len(data), chunk_type='opti'))
    if sspc:
        s = src._sspc
        has_alpha = ct in (4, 6)
        bpp = (32 if has_alpha else 24) * max(bd // 8, 1)  # AE: 24 RGB, 32 RGBA (8-bit seen)
        r = bytearray(s._reserved_3e)       # bytes 0x3e..0x44
        r[1], r[2], r[3] = bpp, 1, 1
        s._reserved_3e = bytes(r)
        s.data_size = path.stat().st_size

"""Let py_aep add any effect captured in an effects seed project.

py_aep can add an effect only if it finds its definition, either in the
project's own `LIST:EfdG` or in the table `py_aep.data.builtin_effects.
BUILTIN_EFFECTS`. `load_seed()` copies every definition from a seed project
(effects_seed/AllEffects_AE<year>.aep) into that table, so `add_property`
works for effects the job project has never used.

    import py_aep, effects_seed
    effects_seed.load_seed(2024)          # or a path to a seed .aep
    layer.effects.add_property("ADBE Gaussian Blur 2")
"""

from __future__ import annotations

import os
from io import BytesIO

import py_aep
from py_aep.binary.chunk import write_chunk
from py_aep.data.builtin_effects import BUILTIN_EFFECTS

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "effects_seed")


def seed_path(year: int) -> str:
    return os.path.join(SEED_DIR, f"AllEffects_AE{year}.aep")


def load_seed(seed: int | str) -> int:
    """Copy every effect definition from a seed project into BUILTIN_EFFECTS.

    `seed` is a year (2024-2027) or a path. Returns how many definitions were
    loaded. Entries already in the table are replaced by the seed's.
    """
    path = seed_path(seed) if isinstance(seed, int) else seed
    project = py_aep.parse(path).project
    n = 0
    for match_name, display, sspc in project._effect_definitions():
        buf = BytesIO()
        write_chunk(buf, sspc)
        BUILTIN_EFFECTS[match_name] = (display, buf.getvalue().hex())
        n += 1
    return n

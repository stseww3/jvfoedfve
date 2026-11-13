"""Turn a canvas into game files: tiled structure templates plus place/clear functions.

Each tile is written twice: `s_*` holds blocks that stand on their own, `d_*` holds blocks that
need support (plants, lanterns, doors, fluids ...) and is placed after every `s_*` tile, so nothing
pops off because its support has not arrived yet. All commands use relative coordinates; run them
with `execute positioned <x> <y> <z> run function <ns>:<name>/place`.
"""
import json
import os

from . import blocks as B
from . import nbtw

DATA_PACK_FORMAT = 121  # 26.3


def _palette(cells):
    index, palette, out = {}, [], []
    for x, y, z, state in cells:
        i = index.get(state)
        if i is None:
            name, props = B.parse(state)
            i = index[state] = len(palette)
            palette.append(("minecraft:" + name, props))
        out.append((x, y, z, i))
    return palette, out


def _write_tile(path, cells, entities=()):
    """cells: list of (x, y, z, state) in placement order. Returns the template origin."""
    x0 = min(c[0] for c in cells) if cells else min(int(e[0] // 1) for e in entities)
    y0 = min(c[1] for c in cells) if cells else min(int(e[1] // 1) for e in entities)
    z0 = min(c[2] for c in cells) if cells else min(int(e[2] // 1) for e in entities)
    x1 = max(c[0] for c in cells) if cells else x0
    y1 = max(c[1] for c in cells) if cells else y0
    z1 = max(c[2] for c in cells) if cells else z0
    palette, blocks = _palette([(x - x0, y - y0, z - z0, s) for x, y, z, s in cells])
    ents = [(x - x0, y - y0, z - z0, nbt) for x, y, z, nbt in entities]
    nbtw.write_template(path, (x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1), palette, blocks, ents)
    return x0, y0, z0


def export(canvas, pack_dir, name, namespace="c164art", tile=48, description="c164 art test"):
    """Write the canvas into a datapack. Returns a manifest dict (also saved as JSON next to it)."""
    os.makedirs(pack_dir, exist_ok=True)
    with open(os.path.join(pack_dir, "pack.mcmeta"), "w") as fh:
        json.dump({"pack": {"description": description, "min_format": DATA_PACK_FORMAT,
                            "max_format": DATA_PACK_FORMAT}}, fh, indent=2)
    sdir = os.path.join(pack_dir, "data", namespace, "structure", name)
    fdir = os.path.join(pack_dir, "data", namespace, "function", name)
    for d in (sdir, fdir):
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    (bx0, by0, bz0), (bx1, by1, bz1) = canvas.bounds()
    tiles = {}
    for (x, y, z), state in canvas.b.items():
        key = ((x - bx0) // tile, (z - bz0) // tile)
        tiles.setdefault(key, ([], [], []))[0 if not B.needs_support(state) else 1].append((x, y, z, state))
    for x, y, z, nbt in canvas.entities:
        key = ((int(x // 1) - bx0) // tile, (int(z // 1) - bz0) // tile)
        tiles.setdefault(key, ([], [], []))[2].append((x, y, z, nbt))

    solid_cmds, detail_cmds = [], []
    n_solid = n_detail = 0
    for (i, j), (solid, detail, ents) in sorted(tiles.items()):
        if solid:
            solid.sort(key=lambda c: (c[1], c[0], c[2]))
            x0, y0, z0 = _write_tile(os.path.join(sdir, f"s_{i}_{j}.nbt"), solid)
            solid_cmds.append(f"place template {namespace}:{name}/s_{i}_{j} ~{x0} ~{y0} ~{z0}")
            n_solid += len(solid)
        if detail or ents:
            standing = sorted((c for c in detail if not B.hangs(c[3])), key=lambda c: (c[1], c[0], c[2]))
            hanging = sorted((c for c in detail if B.hangs(c[3])), key=lambda c: (-c[1], c[0], c[2]))
            x0, y0, z0 = _write_tile(os.path.join(sdir, f"d_{i}_{j}.nbt"), standing + hanging, ents)
            detail_cmds.append(f"place template {namespace}:{name}/d_{i}_{j} ~{x0} ~{y0} ~{z0}")
            n_detail += len(detail)

    with open(os.path.join(fdir, "place.mcfunction"), "w") as fh:
        fh.write("\n".join(solid_cmds + detail_cmds) + "\n")

    # Clearing: air-fill the bounding box (one block of margin) in slabs below the fill limit.
    clear = []
    cx0, cy0, cz0, cx1, cy1, cz1 = bx0 - 1, by0 - 1, bz0 - 1, bx1 + 1, by1 + 1, bz1 + 1
    step = 32
    for x in range(cx0, cx1 + 1, step):
        for z in range(cz0, cz1 + 1, step):
            clear.append(f"fill ~{x} ~{cy0} ~{z} ~{min(x + step - 1, cx1)} ~{cy1} ~{min(z + step - 1, cz1)} air strict")
    clear.append(f"execute positioned ~{cx0} ~{cy0} ~{cz0} run kill "
                 f"@e[type=!player,dx={cx1 - cx0},dy={cy1 - cy0},dz={cz1 - cz0}]")
    with open(os.path.join(fdir, "clear.mcfunction"), "w") as fh:
        fh.write("\n".join(clear) + "\n")

    with open(os.path.join(fdir, "forceload.mcfunction"), "w") as fh:
        fh.write(f"forceload add ~{bx0 - 2} ~{bz0 - 2} ~{bx1 + 2} ~{bz1 + 2}\n")

    manifest = {
        "namespace": namespace, "name": name,
        "min": [bx0, by0, bz0], "max": [bx1, by1, bz1],
        "blocks": len(canvas.b), "solid": n_solid, "detail": n_detail, "entities": len(canvas.entities),
        "tiles": len(tiles),
    }
    with open(os.path.join(pack_dir, f"{name}.manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest

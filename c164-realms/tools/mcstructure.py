#!/usr/bin/env python3
"""Write Minecraft structure templates (.nbt) from Python.

Blocks are given as block-state strings such as
    "minecraft:oak_stairs[facing=north,half=bottom]"
and stored in a sparse dict, so a template only contains what was set.

Two on-disk dialects are supported:
  fmt="26.3"    DataVersion 5023, palette entries {id, properties}   (checked against the 26.3 server jar)
  fmt="legacy"  DataVersion 4790, palette entries {Name, Properties} (26.1.2 and earlier; the game upgrades it on load)
"""
import gzip
import io
import re

import nbtlib
from nbtlib import Compound, Double, Int, List, String

DATA_VERSION = {"26.3": 5023, "legacy": 4790}
_STATE_RE = re.compile(r"^([a-z0-9_.:\-/]+)(?:\[(.*)\])?$")


def parse_state(state):
    """'minecraft:lever[face=wall,facing=north]' -> ('minecraft:lever', {'face': 'wall', 'facing': 'north'})"""
    m = _STATE_RE.match(state.strip())
    if not m:
        raise ValueError(f"bad block state: {state!r}")
    name, props = m.group(1), m.group(2)
    if ":" not in name:
        name = "minecraft:" + name
    out = {}
    if props:
        for part in props.split(","):
            k, _, v = part.partition("=")
            out[k.strip()] = v.strip()
    return name, out


def canonical(state):
    name, props = parse_state(state)
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


class Structure:
    def __init__(self):
        self.blocks = {}      # (x, y, z) -> canonical state string
        self.block_nbt = {}   # (x, y, z) -> nbtlib Compound (block entity data)
        self.entities = []    # (x, y, z as floats, nbtlib Compound)

    def set(self, x, y, z, state, nbt=None):
        pos = (int(x), int(y), int(z))
        self.blocks[pos] = canonical(state)
        if nbt is not None:
            self.block_nbt[pos] = nbt
        else:
            self.block_nbt.pop(pos, None)

    def get(self, x, y, z):
        return self.blocks.get((int(x), int(y), int(z)))

    def remove(self, x, y, z):
        pos = (int(x), int(y), int(z))
        self.blocks.pop(pos, None)
        self.block_nbt.pop(pos, None)

    def fill(self, x1, y1, z1, x2, y2, z2, state, hollow=False):
        xa, xb = sorted((int(x1), int(x2)))
        ya, yb = sorted((int(y1), int(y2)))
        za, zb = sorted((int(z1), int(z2)))
        st = canonical(state)
        for x in range(xa, xb + 1):
            for y in range(ya, yb + 1):
                for z in range(za, zb + 1):
                    if hollow and xa < x < xb and ya < y < yb and za < z < zb:
                        continue
                    self.blocks[(x, y, z)] = st
                    self.block_nbt.pop((x, y, z), None)

    def add_entity(self, x, y, z, nbt):
        self.entities.append((float(x), float(y), float(z), nbt))

    def bounds(self):
        if not self.blocks:
            return (0, 0, 0), (0, 0, 0)
        xs, ys, zs = zip(*self.blocks)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def to_nbt(self, fmt="26.3"):
        if fmt not in DATA_VERSION:
            raise ValueError(f"unknown format {fmt!r}")
        (x0, y0, z0), (x1, y1, z1) = self.bounds()
        name_key, props_key = ("id", "properties") if fmt == "26.3" else ("Name", "Properties")

        index = {}
        palette = []
        blocks = []
        for pos in sorted(self.blocks, key=lambda p: (p[1], p[2], p[0])):
            st = self.blocks[pos]
            if st not in index:
                name, props = parse_state(st)
                entry = Compound({name_key: String(name)})
                if props:
                    entry[props_key] = Compound({k: String(v) for k, v in props.items()})
                index[st] = len(palette)
                palette.append(entry)
            rec = Compound({
                "pos": List[Int]([Int(pos[0] - x0), Int(pos[1] - y0), Int(pos[2] - z0)]),
                "state": Int(index[st]),
            })
            if pos in self.block_nbt:
                rec["nbt"] = self.block_nbt[pos]
            blocks.append(rec)

        entities = []
        for ex, ey, ez, enbt in self.entities:
            rx, ry, rz = ex - x0, ey - y0, ez - z0
            entities.append(Compound({
                "pos": List[Double]([Double(rx), Double(ry), Double(rz)]),
                "blockPos": List[Int]([Int(int(rx // 1)), Int(int(ry // 1)), Int(int(rz // 1))]),
                "nbt": enbt,
            }))

        return Compound({
            "size": List[Int]([Int(x1 - x0 + 1), Int(y1 - y0 + 1), Int(z1 - z0 + 1)]),
            "entities": List[Compound](entities),
            "blocks": List[Compound](blocks),
            "palette": List[Compound](palette),
            "DataVersion": Int(DATA_VERSION[fmt]),
        })

    def save(self, path, fmt="26.3"):
        buf = io.BytesIO()
        nbtlib.File(self.to_nbt(fmt)).write(buf, byteorder="big")
        with gzip.open(path, "wb") as fh:
            fh.write(buf.getvalue())
        return path

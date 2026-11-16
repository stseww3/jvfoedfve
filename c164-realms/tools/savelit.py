#!/usr/bin/env python3
"""Does a save's stored light know its own light sources?

    savelit.py <save.zip>            say it, chunk by chunk; ends with 1 when a source is left dark
    savelit.py <save.zip> --quiet    one line only

A save carries its block light with it: every chunk section has a BlockLight array, and a chunk
that says isLightOn is not lit again when a server loads it. A source whose own cell is stored
darker than the source shines was placed after the light was worked out, and stays dark in the
game for as long as nothing next to it changes: the picture has the lamp and not its light
(mast, 11-16: the power house of the saves A5 and A6, lit in the test world, dark in the save).

Only the files are read (the zip's region/*.mca); nothing is started and nothing is written.
Coordinates in what is printed are the scene's: the world's with ORIGIN_Y taken off y.
"""
import argparse
import collections
import struct
import sys
import zipfile
import zlib

ORIGIN_Y = 200          # the master scene stands at 0 200 0 in an exported save

# what shines without being asked: the level a block gives; None: its "level" property says (light)
EMIT = {
    "minecraft:light": None, "minecraft:lantern": 15, "minecraft:soul_lantern": 10, "minecraft:glowstone": 15,
    "minecraft:sea_lantern": 15, "minecraft:shroomlight": 15, "minecraft:torch": 14, "minecraft:wall_torch": 14,
    "minecraft:soul_torch": 10, "minecraft:soul_wall_torch": 10, "minecraft:end_rod": 14,
    "minecraft:ochre_froglight": 15, "minecraft:verdant_froglight": 15, "minecraft:pearlescent_froglight": 15,
    "minecraft:jack_o_lantern": 15, "minecraft:lava": 15, "minecraft:fire": 15, "minecraft:soul_fire": 10,
    "minecraft:magma_block": 3, "minecraft:beacon": 15, "minecraft:conduit": 15,
}
LIT = {"minecraft:campfire": 15, "minecraft:soul_campfire": 10, "minecraft:redstone_lamp": 15,
       "minecraft:furnace": 13, "minecraft:blast_furnace": 13, "minecraft:smoker": 13}      # when lit=true


def read_nbt(buf):
    """The value of an uncompressed NBT file: compounds as dicts, lists as lists, byte arrays as
    bytes, int and long arrays as tuples."""
    pos = 0

    def take(fmt, size):
        nonlocal pos
        value = struct.unpack_from(fmt, buf, pos)[0]
        pos += size
        return value

    def string():
        nonlocal pos
        size = take(">H", 2)
        text = buf[pos:pos + size].decode("utf-8", "replace")
        pos += size
        return text

    def payload(kind):
        nonlocal pos
        if kind == 1:
            return take(">b", 1)
        if kind == 2:
            return take(">h", 2)
        if kind == 3:
            return take(">i", 4)
        if kind == 4:
            return take(">q", 8)
        if kind == 5:
            return take(">f", 4)
        if kind == 6:
            return take(">d", 8)
        if kind == 7:
            size = take(">i", 4)
            value = buf[pos:pos + size]
            pos += size
            return value
        if kind == 8:
            return string()
        if kind == 9:
            of, size = take(">b", 1), take(">i", 4)
            return [payload(of) for _ in range(size)]
        if kind == 10:
            out = {}
            while True:
                of = take(">b", 1)
                if of == 0:
                    return out
                name = string()
                out[name] = payload(of)
        if kind == 11:
            size = take(">i", 4)
            value = struct.unpack_from(f">{size}i", buf, pos)
            pos += 4 * size
            return value
        if kind == 12:
            size = take(">i", 4)
            value = struct.unpack_from(f">{size}Q", buf, pos)
            pos += 8 * size
            return value
        raise ValueError(f"NBT tag {kind}")

    kind = take(">b", 1)
    string()
    return payload(kind)


def chunks(archive, folder="/region/"):
    """Every chunk of the zip's region files, as its NBT."""
    for name in archive.namelist():
        if not name.endswith(".mca") or folder not in name:
            continue
        data = archive.read(name)
        if len(data) < 8192:
            continue
        for i in range(1024):
            entry = struct.unpack_from(">I", data, 4 * i)[0]
            if entry == 0:
                continue
            start = (entry >> 8) * 4096
            length, packed = struct.unpack_from(">IB", data, start)
            raw = data[start + 5:start + 4 + length]
            if packed == 2:
                raw = zlib.decompress(raw)
            elif packed == 1:
                raw = zlib.decompress(raw, 31)
            elif packed != 3:
                raise SystemExit(f"{name}: a chunk is packed in a way this script does not read ({packed})")
            yield read_nbt(raw)


def state_of(entry):
    """(name, properties) of a palette entry. The game 26.3 writes {'': name} for a block without
    properties and {'id': name, 'properties': {...}} for one with; older games wrote
    {'Name': name, 'Properties': {...}}."""
    if isinstance(entry, str):
        return entry, {}
    return (entry.get("id") or entry.get("") or entry.get("Name"),
            entry.get("properties") or entry.get("Properties") or {})


def shines(entry):
    """The light level a palette entry gives, 0 when it gives none."""
    name, properties = state_of(entry)
    if name in EMIT:
        return int(properties.get("level", 15)) if EMIT[name] is None else EMIT[name]
    if name in LIT and properties.get("lit") == "true":
        return LIT[name]
    return 0


def survey(path):
    """{(chunk x, chunk z): (sources, dark, isLightOn, [(x, y, z, level, stored), ...])} for every
    chunk of the save that holds a light source; dark counts those whose own cell is stored darker
    than they shine, and the list names them in the world's coordinates."""
    out = {}
    with zipfile.ZipFile(path) as archive:
        for chunk in chunks(archive):
            cx, cz = chunk["xPos"], chunk["zPos"]
            sources, dark = 0, []
            for section in chunk.get("sections", []):
                states = section.get("block_states") or {}
                palette = states.get("palette", [])
                level = {i: shines(entry) for i, entry in enumerate(palette)}
                level = {i: n for i, n in level.items() if n > 0}
                if not level:
                    continue
                data = states.get("data")
                if data is None:        # one block fills the section
                    cells = [0] * 4096
                else:
                    bits = max(4, (len(palette) - 1).bit_length())
                    per, mask = 64 // bits, (1 << bits) - 1
                    cells = [(word >> (k * bits)) & mask for word in data for k in range(per)][:4096]
                stored = section.get("BlockLight")
                for n, i in enumerate(cells):
                    if i not in level:
                        continue
                    sources += 1
                    have = 0 if stored is None else (stored[n >> 1] >> 4 if n & 1 else stored[n >> 1]) & 15
                    if have < level[i]:
                        dark.append((cx * 16 + (n & 15), section["Y"] * 16 + (n >> 8), cz * 16 + ((n >> 4) & 15),
                                     level[i], have))
            if sources:
                out[(cx, cz)] = (sources, len(dark), chunk.get("isLightOn"), dark)
    return out


def line(found):
    """What the survey found, in one line."""
    sources = sum(v[0] for v in found.values())
    dark = sum(v[1] for v in found.values())
    if not dark:
        return f"the save's stored light: {sources} light sources in {len(found)} chunks, each lit in its own cell"
    where = sorted(c for c, v in found.items() if v[1])
    kept = sum(1 for c in where if found[c][2])
    xs, zs = [c[0] for c in where], [c[1] for c in where]
    return (f"the save's stored light: {dark} of {sources} light sources are stored dark (their own cell below "
            f"their level), in {len(where)} chunks {', '.join(f'({x},{z})' for x, z in where[:8])}"
            f"{' ...' if len(where) > 8 else ''}: x {min(xs) * 16}..{max(xs) * 16 + 15}, z {min(zs) * 16}.."
            f"{max(zs) * 16 + 15}; {kept} of these chunks say isLightOn, and a server does not light such a "
            f"chunk again")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("save", help="the save's zip")
    ap.add_argument("--quiet", action="store_true", help="one line only")
    args = ap.parse_args()
    found = survey(args.save)
    print(line(found))
    dark = sum(v[1] for v in found.values())
    if not args.quiet and found:
        xs = sorted({c[0] for c in found})
        zs = sorted({c[1] for c in found})
        print("dark/all for every chunk with a source (rows: chunk z, columns: chunk x; a chunk is 16 blocks)")
        print("      " + "".join(f"{x:>7}" for x in range(xs[0], xs[-1] + 1)))
        for cz in range(zs[0], zs[-1] + 1):
            cells = (f"{found[(cx, cz)][1]}/{found[(cx, cz)][0]}" if (cx, cz) in found else "."
                     for cx in range(xs[0], xs[-1] + 1))
            print(f"{cz:>5} " + "".join(f"{cell:>7}" for cell in cells))
        if dark:
            said = collections.Counter("isLightOn" if v[2] else "no isLightOn" for v in found.values() if v[1])
            print("the chunks with dark sources: " + ", ".join(f"{n} with {what}" for what, n in said.items()))
            rows = sorted(w for v in found.values() for w in v[3])
            print("the dark sources, scene coordinates (x y z: level, stored):")
            for x, y, z, level, have in rows[:40]:
                print(f"  {x} {y - ORIGIN_Y} {z}: {level}, {have}")
            if len(rows) > 40:
                print(f"  ... and {len(rows) - 40} more")
    return 1 if dark else 0


if __name__ == "__main__":
    sys.exit(main())

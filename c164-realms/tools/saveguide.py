#!/usr/bin/env python3
"""What a save tells a visitor and asks of one, read out of its files: the words that stand in the
world (text_display entities: the plaques), the titles its functions show, and the places its
functions watch for somebody to come near (the star charts, the step before the eyepiece).

    saveguide.py <save.zip>            print what was found
    saveguide.py <save.zip> --json     the same as JSON

Only the files are read (the zip's entities/*.mca, region/*.mca and the data pack's functions);
nothing is started and nothing is written. Coordinates are the world's.

guidetrip.py plans its walk from this: where to stand to read a plaque, where a visitor's feet can
be put inside the reach of a watched place.
"""
import json
import math
import re
import struct
import sys
import zipfile
import zlib

import savelit

EYE = 1.62
NUMBER = r"-?\d+(?:\.\d+)?"
# cells a player's body passes through; anything else is taken for solid
PASSABLE = re.compile(r"(^|:)(air|cave_air|void_air|light|structure_void)$|_carpet$|torch$|_sign$|_banner$|_button$|"
                      r"pressure_plate$|rail$|lever$|redstone_wire$|tripwire|ladder$|vine$")


def plain(component):
    """The words of a text component as the game stores it (a string, a compound with text and
    extra, or a list of these)."""
    if isinstance(component, str):
        text = component.strip()
        if text[:1] in "[{" and text[-1:] in "]}":      # a component kept as JSON text by an older game
            try:
                return plain(json.loads(text))
            except ValueError:
                pass
        return component
    if isinstance(component, (list, tuple)):
        return "".join(plain(part) for part in component)
    if isinstance(component, dict):
        return str(component.get("text", component.get("", ""))) + plain(component.get("extra", []))
    return ""


def turn(q, v):
    """The vector v turned by the quaternion q = (x, y, z, w)."""
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def facing(yaw, pitch):
    """The way an entity with this rotation looks: the side its text is read from."""
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    return (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))


def displays(archive):
    """Every text_display of the save: {"text", "lines", "pos" (the middle of the words), "normal"
    (the side it is read from), "scale", "billboard", "background", "brightness", "see_through",
    "shadow", "width"}; passengers of other entities too."""
    found = []

    def walk(entity):
        for rider in entity.get("Passengers", []):
            walk(rider)
        if not str(entity.get("id", "")).endswith("text_display"):
            return
        text = plain(entity.get("text", ""))
        yaw, pitch = (list(entity.get("Rotation", [])) + [0.0, 0.0])[:2]
        change = entity.get("transformation") or {}
        left = tuple(change.get("left_rotation", (0.0, 0.0, 0.0, 1.0)))
        right = tuple(change.get("right_rotation", (0.0, 0.0, 0.0, 1.0)))
        scale = tuple(change.get("scale", (1.0, 1.0, 1.0)))
        shift = tuple(change.get("translation", (0.0, 0.0, 0.0)))
        if len(left) != 4 or len(right) != 4 or len(scale) != 3 or len(shift) != 3:
            left, right, scale, shift = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)
        lines = text.split("\n")
        yaw_r, pitch_r = math.radians(-yaw), math.radians(pitch)

        def stand(v):       # the entity's own turn: about x by its pitch, then about y by its yaw
            x, y, z = v
            y, z = y * math.cos(pitch_r) - z * math.sin(pitch_r), y * math.sin(pitch_r) + z * math.cos(pitch_r)
            x, z = x * math.cos(yaw_r) + z * math.sin(yaw_r), -x * math.sin(yaw_r) + z * math.cos(yaw_r)
            return (x, y, z)

        def placed(v, whole=True):      # the transformation: right rotation, scale, left rotation, translation
            v = turn(right, v)
            if whole:
                v = tuple(v[k] * scale[k] for k in range(3))
            v = turn(left, v)
            return tuple(v[k] + shift[k] for k in range(3)) if whole else v

        # the words stand on the entity's point and rise from it, a quarter of a block for a line
        middle = (0.0, 0.125 * len(lines), 0.0)
        if str(entity.get("billboard", "fixed")) == "fixed":
            normal, offset = stand(placed((0.0, 0.0, 1.0), whole=False)), stand(placed(middle))
        else:                           # it turns to whoever looks: no side of its own
            normal, offset = None, placed(middle)
        pos = tuple(float(entity["Pos"][k]) + offset[k] for k in range(3))
        light = entity.get("brightness") or {}
        found.append({
            "text": text, "lines": len(lines), "pos": [round(v, 3) for v in pos],
            "normal": [round(v, 3) for v in normal] if normal else None,
            "scale": [round(float(v), 3) for v in scale], "billboard": str(entity.get("billboard", "fixed")),
            "background": int(entity.get("background", 0x40000000)) & 0xFFFFFFFF,
            "brightness": (int(light.get("block", -1)), int(light.get("sky", -1))) if light else None,
            "see_through": bool(entity.get("see_through", 0)), "shadow": bool(entity.get("shadow", 0)),
            "width": int(entity.get("line_width", 200)),
        })

    for chunk in savelit.chunks(archive, folder="/entities/"):
        for entity in chunk.get("Entities", []):
            walk(entity)
    found.sort(key=lambda d: (d["pos"][0], d["pos"][2], d["pos"][1]))
    return found


def functions(archive):
    """{function id: [its commands]} for every function of the save's data packs."""
    out = {}
    for name in archive.namelist():
        m = re.search(r"/datapacks/[^/]+/data/([^/]+)/function/(.+)\.mcfunction$", name)
        if m:
            lines = archive.read(name).decode("utf-8", "replace").splitlines()
            out[f"{m.group(1)}:{m.group(2)}"] = [line.strip() for line in lines
                                                 if line.strip() and not line.lstrip().startswith("#")]
    return out


def spoken(component):
    """The words of a title command's text, which is written as SNBT or JSON in a function."""
    words = re.findall(r"""(?:"text"|\btext)\s*:\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""", component)
    if words:
        return "".join(a or b for a, b in words)
    return component.strip().strip("\"'")


def shown(found):
    """What the functions put on a visitor's screen: [(function, title|subtitle|actionbar|times|tellraw|bossbar,
    the words)], in the order the functions hold them."""
    out = []
    for name, lines in sorted(found.items()):
        for line in lines:
            m = re.search(r"\btitle (\S+) (title|subtitle|actionbar|times) (.+)$", line)
            if m:
                out.append((name, m.group(2), m.group(3).strip() if m.group(2) == "times" else spoken(m.group(3))))
                continue
            m = re.search(r"\b(tellraw|say|me|msg|tell|w|bossbar) (.+)$", line)
            if m and not re.search(r"\bscoreboard\b", line[:m.start()]):
                out.append((name, m.group(1), m.group(2)[:160]))
    return out


def places_of(line):
    """The places a command watches, [(x, y, z, reach)]: every `positioned X Y Z` that a
    distance=..R follows before the next one (a chart is taken within reach of the floor under it
    and of the spot one reads it from: two of them), or a selector's own x=, y=, z= and distance."""
    out = []
    parts = re.split(rf"\bpositioned ({NUMBER}) ({NUMBER}) ({NUMBER})", line)
    for i in range(1, len(parts), 4):
        reach = re.search(r"distance=(?:" + NUMBER + r")?\.\.(" + NUMBER + ")", parts[i + 3])
        if reach:
            out.append((float(parts[i]), float(parts[i + 1]), float(parts[i + 2]), float(reach.group(1))))
    for selector in re.findall(r"@[aprse]\[([^\]]*)\]", line):
        given = dict(part.split("=", 1) for part in selector.split(",") if "=" in part)
        reach = re.fullmatch(r"(?:" + NUMBER + r")?\.\.(" + NUMBER + ")", given.get("distance", ""))
        if reach and all(k in given for k in "xyz"):
            try:
                out.append((float(given["x"]), float(given["y"]), float(given["z"]), float(reach.group(1))))
            except ValueError:
                continue
    return out


def watched(found, depth=3):
    """{tag: ([(x, y, z, reach), ...], the function that watches)}: the places where coming near
    gives a player a tag -- on the command itself, or in the function it runs (followed `depth` deep)."""
    def tags(lines, left):
        given = []
        for line in lines:
            given += re.findall(r"\btag @s add (\S+)", line)
            if left > 0:
                for called in re.findall(r"\bfunction (\S+:\S+)", line):
                    given += tags(found.get(called, []), left - 1)
        return given

    out = {}
    for name, lines in sorted(found.items()):
        for line in lines:
            places = places_of(line)
            if not places:
                continue
            for tag in tags([line], depth):
                out.setdefault(tag, (places, name))
    return out


def sparks(found, depth=2):
    """The points at which a function that is run at a fixed place (`positioned X Y Z`, no reach)
    starts particles relative to it: [(x, y, z)] -- the lights of a close, to look at."""
    def relative(lines, left):
        points = []
        for line in lines:
            m = re.search(rf"\bparticle \S+ ~({NUMBER})? ~({NUMBER})? ~({NUMBER})?", line)
            if m:
                points.append(tuple(float(v or 0) for v in m.groups()))
            if left > 0:
                for called in re.findall(r"\bfunction (\S+:\S+)", line):
                    points += relative(found.get(called, []), left - 1)
        return points

    out = []
    for lines in found.values():
        for line in lines:
            at = re.search(rf"\bpositioned ({NUMBER}) ({NUMBER}) ({NUMBER})", line)
            if at and "distance=" not in line and re.search(r"\bfunction \S+:\S+", line):
                base = tuple(float(v) for v in at.groups())
                out += [tuple(base[k] + p[k] for k in range(3)) for p in relative([line], depth)]
    return out


class Blocks:
    """The save's blocks by position, a chunk read when it is first asked for."""

    def __init__(self, archive):
        self.archive = archive
        self.regions = {}
        for name in archive.namelist():
            m = re.search(r"/region/r\.(-?\d+)\.(-?\d+)\.mca$", name)
            if m and "/entities/" not in name and "/poi/" not in name:
                self.regions.setdefault((int(m.group(1)), int(m.group(2))), name)
        self.data, self.chunks = {}, {}

    def chunk(self, cx, cz):
        if (cx, cz) in self.chunks:
            return self.chunks[cx, cz]
        sections = {}
        region = (cx >> 5, cz >> 5)
        if region in self.regions:
            if region not in self.data:
                self.data[region] = self.archive.read(self.regions[region])
            data = self.data[region]
            entry = struct.unpack_from(">I", data, 4 * ((cx & 31) + (cz & 31) * 32))[0] if len(data) >= 8192 else 0
            if entry:
                start = (entry >> 8) * 4096
                length, packed = struct.unpack_from(">IB", data, start)
                raw = data[start + 5:start + 4 + length]
                raw = zlib.decompress(raw) if packed == 2 else zlib.decompress(raw, 31) if packed == 1 else raw
                for section in savelit.read_nbt(raw).get("sections", []):
                    states = section.get("block_states") or {}
                    palette = [savelit.state_of(entry)[0] for entry in states.get("palette", [])]
                    sections[section["Y"]] = (palette, states.get("data"))
        self.chunks[cx, cz] = sections
        return sections

    def at(self, x, y, z):
        """The name of the block in the cell that holds this point; air where the save has nothing."""
        x, y, z = math.floor(x), math.floor(y), math.floor(z)
        palette, data = self.chunk(x >> 4, z >> 4).get(y >> 4, ((), None))
        if not palette:
            return "minecraft:air"
        if data is None:
            return palette[0]
        bits = max(4, (len(palette) - 1).bit_length())
        per = 64 // bits
        n = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        return palette[(data[n // per] >> ((n % per) * bits)) & ((1 << bits) - 1)]

    def open(self, x, y, z):
        return bool(PASSABLE.search(self.at(x, y, z)))

    def stands(self, x, y, z):
        """Can a visitor's feet be put here: two open cells for the body, something under the feet."""
        return self.open(x, y, z) and self.open(x, y + 1, z) and not self.open(x, y - 0.5, z)

    def standing(self, places, margin=0.1):
        """Where a visitor's feet can be put inside the reach of every one of `places` [(x, y, z,
        reach)]: the last of them itself when one can stand there (the spot the map means), else
        the middle of a cell with two open cells for the body and something under the feet -- the
        lowest floor first (not the table the thing lies on), then the nearest to the last place.
        Returns ((x, y, z), how far from the last place) or None."""
        def inside(spot):
            return all(math.dist(spot, place[:3]) <= place[3] - margin for place in places)
        px, py, pz = places[-1][:3]
        if self.stands(px, py, pz) and inside((px, py, pz)):
            return (px, py, pz), 0.0
        best = None
        for cx in range(math.floor(px) - 2, math.floor(px) + 3):
            for cz in range(math.floor(pz) - 2, math.floor(pz) + 3):
                for cy in range(math.floor(py) - 2, math.floor(py) + 2):
                    spot = (cx + 0.5, float(cy), cz + 0.5)
                    if inside(spot) and self.stands(*spot):
                        far = math.dist(spot, (px, py, pz))
                        if best is None or (cy, far) < (best[0][1], best[1]):
                            best = (spot, far)
        return best


def place(blocks, near, name):
    """What is known of one watched place: see read()."""
    near = [tuple(float(v) for v in one) for one in near]
    spot = blocks.standing(near)
    return {"at": list(near[0][:3]), "reach": near[0][3], "near": [list(one) for one in near], "function": name,
            "stand": [round(v, 3) for v in spot[0]] if spot else None, "far": round(spot[1], 2) if spot else None,
            "on": blocks.at(spot[0][0], spot[0][1] - 0.5, spot[0][2]) if spot else None}


def read(path):
    """{"plaques": [...], "shown": [...], "watched": {tag: {"at": the first place watched (the thing),
    "reach", "near": every place the feet must be near, "function", "stand": where a visitor's feet
    can be put or None, "far", "on"}}, "sparks": [...], "functions": how many}"""
    with zipfile.ZipFile(path) as archive:
        found = functions(archive)
        blocks = Blocks(archive)
        places = {tag: place(blocks, near, name) for tag, (near, name) in sorted(watched(found).items())}
        return {"plaques": displays(archive), "shown": [list(row) for row in shown(found)], "watched": places,
                "sparks": [[round(v, 2) for v in point] for point in sparks(found)], "functions": len(found)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    found = read(sys.argv[1])
    if "--json" in sys.argv[2:]:
        json.dump(found, sys.stdout, indent=1)
        print()
        return
    print(f"{len(found['plaques'])} text displays, {len(found['shown'])} commands that show words, "
          f"{len(found['watched'])} watched places, in {found['functions']} functions")
    for plaque in found["plaques"]:
        print(f"  text at {plaque['pos']} read from {plaque['normal']}: {plaque['text']!r} (scale {plaque['scale']}, "
              f"background {plaque['background']:08x}, brightness {plaque['brightness']})")
    for name, kind, words in found["shown"]:
        print(f"  {name}: {kind} {words}")
    for tag, place in found["watched"].items():
        print(f"  {tag}: within reach of {place['near']} ({place['function']}); feet at {place['stand']} "
              f"on {place['on']}, {place['far']} from the last")
    print(f"  {len(found['sparks'])} points at which particles are started at a fixed place")


if __name__ == "__main__":
    main()

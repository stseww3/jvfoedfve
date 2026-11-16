"""What the hall's test scene holds, as text: plans, sections, block light and the light sources.
Run it where the scene may be built (a node, not the shared machine), in build/:

    python -m scenes.obs_int_starhall.probe a|b [plan:<y>] [x:<x>] [z:<z>] [lv:<y>] [lz:<z>] [lights] [ents]

  plan:<y>   the blocks of one level, x -9..18 left to right, z -7..7 top to bottom
  x:<x>      the section across the hall at this x; z:<z> the section along it
  lv:<y>     the block light of one level, a hex digit a cell; #: a block that stops light
  lz:<z>     the block light of the section along the hall at this z
  lights     the light line's summary and every source placed in and around the hall
  ents       the display entities: where, and the head of what they show
"""
import sys

from artkit import blocks as AB

from scenes.obs.sky import _lightkit as L
from scenes.obs.sky import lights

from . import build

X, Y, Z = (-9, 18), (-2, 15), (-7, 7)
LETTERS = {
    "smooth_sandstone": "S", "sandstone": "s", "cut_sandstone": "C", "chiseled_sandstone": "E",
    "deepslate_bricks": "D", "polished_deepslate": "P", "deepslate_tiles": "T", "polished_tuff": "t",
    "tuff_bricks": "u", "tuff": "f", "oxidized_cut_copper": "R", "dark_oak_planks": "W", "dark_oak_slab": "w",
    "dark_oak_stairs": "y", "dark_oak_trapdoor": "d", "rail": "=", "activator_rail": "+", "detector_rail": "*",
    "light": "L", "iron_bars": "#", "chain": "|", "pale_oak_planks": "p", "waxed_exposed_copper": "c",
    "smooth_sandstone_stairs": "^", "smooth_sandstone_slab": "_", "sandstone_stairs": "v", "sandstone_wall": "!",
    "deepslate_brick_stairs": "/", "deepslate_brick_slab": "-", "oxidized_cut_copper_stairs": "r",
    "oxidized_cut_copper_slab": "~", "yellow_carpet": "o", "cut_sandstone_slab": "k",
}


def main(argv):
    c = build(argv[0])
    other = {}

    def short(state):
        if state is None:
            return "."
        name = AB.name_of(state).replace("minecraft:", "")
        if name in LETTERS:
            return LETTERS[name]
        if "glazed_terracotta" in name:
            return "G"
        if "glass" in name:
            return "g"
        return other.setdefault(name, chr(ord("0") + len(other) % 10))

    def ruler(wide=1):
        print("     " + "".join(f"{x % 10:>{wide}}" for x in range(X[0], X[1] + 1)))

    def light(lv, cell):
        state = c.b.get(cell)
        return " #" if state is not None and L._stops_light(state) else f"{lv.get(cell, 0):>2x}"

    lv = None
    for arg in argv[1:]:
        key, _, value = arg.partition(":")
        if key in ("lv", "lz") and lv is None:
            lv = L.levels(c, (X[0], Y[0], Z[0]), (X[1], Y[1], Z[1]))
        if key == "plan":
            print(f"plan y={value}  (x {X[0]}..{X[1]} left to right, z {Z[0]}..{Z[1]} top to bottom)")
            ruler()
            for z in range(Z[0], Z[1] + 1):
                print(f"{z:>4} " + "".join(short(c.b.get((x, int(value), z))) for x in range(X[0], X[1] + 1)))
        elif key == "x":
            print(f"section x={value}  (z {Z[0]}..{Z[1]} left to right, y {Y[1]}..{Y[0]} top to bottom)")
            for y in range(Y[1], Y[0] - 1, -1):
                print(f"{y:>4} " + "".join(short(c.b.get((int(value), y, z))) for z in range(Z[0], Z[1] + 1)))
        elif key == "z":
            print(f"section z={value}  (x {X[0]}..{X[1]} left to right, y {Y[1]}..{Y[0]} top to bottom)")
            ruler()
            for y in range(Y[1], Y[0] - 1, -1):
                print(f"{y:>4} " + "".join(short(c.b.get((x, y, int(value)))) for x in range(X[0], X[1] + 1)))
        elif key == "lv":
            print(f"block light y={value}")
            ruler(2)
            for z in range(Z[0], Z[1] + 1):
                print(f"{z:>4} " + "".join(light(lv, (x, int(value), z)) for x in range(X[0], X[1] + 1)))
        elif key == "lz":
            print(f"block light, section z={value}")
            ruler(2)
            for y in range(Y[1], Y[0] - 1, -1):
                print(f"{y:>4} " + "".join(light(lv, (x, y, int(value))) for x in range(X[0], X[1] + 1)))
        elif key == "lights":
            r = lights.report(c)
            print(lights.summary(c))
            print("placed in and around the hall:")
            for cell, (level, why) in sorted(r["placed"].items()):
                if X[0] <= cell[0] <= X[1] and Z[0] <= cell[2] <= Z[1] and Y[0] <= cell[1] <= Y[1]:
                    print("  ", cell, level, why)
            for name in ("rejected", "moved", "capped", "merged"):
                for row in r.get(name, ()):
                    print("  ", name, row)
        elif key == "ents":
            for x, y, z, nbt in c.entities:
                if X[0] <= x <= X[1] + 1 and Z[0] <= z <= Z[1] + 1:
                    print("  ", round(x, 2), round(y, 2), round(z, 2), str(nbt)[:150])
    if other:
        print("other blocks:", {v: k for k, v in other.items()})


if __name__ == "__main__":
    main(sys.argv[1:] or ["a", "lights"])

"""python -m scenes.obs_site_yard.plan: the lower platform as the master scene's lines build it,
drawn from above, so that the yard is laid where nothing stands (card plan/packages/site/yard.md).

One map, a letter to the cell, east up and z running south to the right (a receipt of the
director's machine holds 60 lines): a capital for what stands where the feet are, else a small
letter for the paving under them, a point where there is neither. Then the cells with something
a block above the feet, and the display entities that stand over the open platform.
"""
import string
import sys

from artkit.canvas import Canvas

from scenes.obs import machines, main, props, site
from scenes.obs.common import skeleton as S

X0, Z0, X1, Z1 = S.LOWER_PLATFORM
PAD = 2
WIDE = 232


def _name(state):
    return state.split("[", 1)[0].replace("minecraft:", "") if state else ""


def _wrap(items, lead="  "):
    line = lead
    for item in items:
        if len(line) + len(item) + 2 > WIDE:
            print(line)
            line = lead
        line += item + "  "
    if line.strip():
        print(line)


def main_():
    c = Canvas()
    for line in (site, main, machines, props):
        line.build(c, (0, 0, 0))
    small, capital = {}, {}
    pools = {id(small): iter(string.ascii_lowercase + string.digits), id(capital): iter(string.ascii_uppercase + "#%&*+=?@$")}

    def letter(table, state):
        name = _name(state)
        if name not in table:
            table[name] = next(pools[id(table)], "~")
        return table[name]

    zs = range(Z0 - PAD, Z1 + PAD + 1)
    feet, paving = S.LOWER_GROUND, S.LOWER_PAVING_Y
    print(f"== x down the side (east up), z {zs[0]}..{zs[-1]} across; ! marks z -40, -30, ... 40; feet at y {feet}")
    print("    " + "".join("!" if z % 10 == 0 else " " for z in zs))
    for x in range(X1 + PAD, X0 - PAD - 1, -1):
        row = ""
        for z in zs:
            here, under = c.get(x, feet, z), c.get(x, paving, z)
            row += letter(capital, here) if here else (letter(small, under) if under else ".")
        print(f"{x:3d} {row}")
    _wrap([f"{ch}={name}" for name, ch in sorted(capital.items(), key=lambda kv: kv[1])], "feet: ")
    _wrap([f"{ch}={name}" for name, ch in sorted(small.items(), key=lambda kv: kv[1])], "paving: ")
    seen = {}
    for x, y, z, nbt in c.entities:
        inside = (x >= S.POWER_HOUSE["box"][0] and z >= S.POWER_HOUSE["box"][1] + 1) or \
                 (x >= S.CABLE_STATION[0] and z <= S.CABLE_STATION[3])
        if X0 - PAD <= x <= X1 + PAD + 1 and zs[0] <= z <= zs[-1] + 1 and paving <= y <= S.GROUND + 6 and not inside:
            what = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model") or nbt.get("id")
            what = str(what).split(":", 1)[-1]
            seen.setdefault((int(x // 1), int(z // 1)), set()).add(what.replace("prop_", ""))
    _wrap([f"({x},{z}) {'+'.join(sorted(names))[:40]}" for (x, z), names in sorted(seen.items())], "entities: ")


if __name__ == "__main__":
    sys.exit(main_())

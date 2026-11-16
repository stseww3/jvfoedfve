"""python -m scenes.obs_site_yard.plan: the lower platform as the master scene's lines build it,
drawn from above, so that the yard is laid where nothing stands (card plan/packages/site/yard.md).

Three maps, a letter to the block, north up and x running east: the paving course, the course the
feet stand in, and the one above it. Then the display entities that stand over the platform.
"""
import string
import sys

from artkit.canvas import Canvas

from scenes.obs import machines, main, props, site
from scenes.obs.common import skeleton as S

X0, Z0, X1, Z1 = S.LOWER_PLATFORM
PAD = 2


def _name(state):
    return state.split("[", 1)[0].replace("minecraft:", "") if state else ""


def main_():
    c = Canvas()
    for line in (site, main, machines, props):
        line.build(c, (0, 0, 0))
    letters = {}
    pool = iter(string.ascii_lowercase + string.ascii_uppercase + string.digits + "#%&*+=?@$")

    def letter(state):
        name = _name(state)
        if not name:
            return "."
        if name not in letters:
            letters[name] = next(pool, "~")
        return letters[name]

    xs = range(X0 - PAD, X1 + PAD + 1)
    for title, y in (("the paving course", S.LOWER_PAVING_Y), ("where the feet stand", S.LOWER_GROUND),
                     ("a block up", S.LOWER_GROUND + 1), ("two blocks up", S.LOWER_GROUND + 2)):
        print(f"== {title}, y {y}; x {xs[0]}..{xs[-1]}, a mark every ten")
        print("      " + "".join("|" if x % 10 == 0 else " " for x in xs))
        for z in range(Z0 - PAD, Z1 + PAD + 1):
            print(f"{z:5d} " + "".join(letter(c.get(x, y, z)) for x in xs))
    print("== letters")
    for name, ch in sorted(letters.items(), key=lambda kv: kv[1]):
        print(f"  {ch} {name}")
    print("== display entities over the platform (x, y, z, what)")
    for x, y, z, nbt in sorted(c.entities, key=lambda e: (e[2], e[0])):
        if X0 - PAD <= x <= X1 + PAD + 1 and Z0 - PAD <= z <= Z1 + PAD + 1 and S.LOWER_PAVING_Y <= y <= S.GROUND + 4:
            what = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model") or nbt.get("id")
            print(f"  {x:7.2f} {y:6.2f} {z:7.2f}  {str(what).split(':', 1)[-1]}")


if __name__ == "__main__":
    sys.exit(main_())

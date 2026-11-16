"""What the biome would colour in a scene (plan/parts/materials.md 9; the sky's move into the
resource pack, A0 11-16 07:20).

The map carries no biome of its own: a biome is a registry file, and Realms takes no world that has
one. The map and every test scene stand in the game's own minecraft:the_void (the look is carried by
the resource pack's shaders, artkit.mood.Carried), and there the game colours what it tints by the
biome as it does anywhere: water #3f76e4 and not the look's (sky/mood.py WATER), grass and leaves by
the game's colour maps. The offline renderer still draws from the look's biome. So a block the game
tints by the biome would look one way in the offline pictures and another in the game.

The occupancy table holds no such block, and this module says whether a built scene keeps to that:

    tinted(canvas)   -> {(what, colour): count}   blocks placed, blocks that block displays show and
                        the game's own items in item displays that take a colour of the biome, and
                        cells that hold water because their block is waterlogged
    python -m scenes.obs.materials._tints [scene]   prints it for a scene (default: obs)

Whoever needs water or a plant asks the materials line first. Water can be had: its three pictures
(water_still, water_flow, water_overlay) multiplied channel by channel with WATER / #3f76e4 show
the look's water in the_void. Grass and leaves would need a colour chosen first: the look has none.
"""
import importlib
import sys

from artkit import blockfacts as F

VOID_WATER = "#3f76e4"          # the_void's water colour (the game's default)


class _Names:
    """Stands for a biome's look: every colour answers with its own name."""
    grass, foliage, dry_foliage, water = "grass", "foliage", "dry_foliage", "water"


def colour(block):
    """Which colour of the biome the game tints this block with, or None."""
    for index in (0, 1):
        got = F.tint(block.split(":", 1)[-1], index, _Names)
        if isinstance(got, str):
            return got
    return None


def tinted(canvas):
    """{(what, colour): count} of what the biome would colour in a built scene."""
    out = {}

    def add(what, col):
        out[(what, col)] = out.get((what, col), 0) + 1

    for state in canvas.b.values():
        name, _, props = state.partition("[")
        col = colour(name)
        if col:
            add(name.split(":", 1)[-1], col)
        if "waterlogged=true" in props:
            add(name.split(":", 1)[-1] + " (waterlogged)", "water")
    for _, _, _, nbt in canvas.entities:
        kind = str(nbt.get("id", "")).split(":", 1)[-1]
        if kind == "block_display":
            state = nbt.get("block_state") or {}
            name = str(state.get("Name", "")).split(":", 1)[-1]
            if colour(name):
                add(name + " (block display)", colour(name))
            if str((state.get("Properties") or {}).get("waterlogged", "")) == "true":
                add(name + " (block display, waterlogged)", "water")
        elif kind == "item_display":
            item = nbt.get("item") or {}
            name = str(item.get("id", "")).split(":", 1)[-1]
            shows_own = "minecraft:item_model" not in (item.get("components") or {})
            if shows_own and colour(name):
                add(name + " (item display)", colour(name))
    return out


def main(argv):
    name = argv[0] if argv else "obs"
    canvas = importlib.import_module(f"scenes.{name}").build()
    kinds = {state.partition("[")[0] for state in canvas.b.values()}
    found = tinted(canvas)
    print(f"{name}: {len(canvas.b)} blocks of {len(kinds)} kinds, {len(canvas.entities)} entities: "
          f"{sum(found.values())} that the biome would colour")
    for (what, col), n in sorted(found.items()):
        print(f"  {what}: {n}, by the biome's {col}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

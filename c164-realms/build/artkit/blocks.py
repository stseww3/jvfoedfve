"""Block-state strings checked against the 26.3 block table.

States are written like "stone" or "spruce_stairs[facing=north,half=top]" (the minecraft: prefix is
implied). parse() rejects unknown blocks, properties and values, so typos fail before anything is
placed in a world.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "data", "blocks-26.3.json")) as _fh:
    TABLE = json.load(_fh)

_cache = {}


def parse(state):
    """Return (name, props) for a state string; raises ValueError when it is not valid in 26.3."""
    hit = _cache.get(state)
    if hit is not None:
        return hit
    name, _, rest = state.partition("[")
    name = name.strip()
    if name.startswith("minecraft:"):
        name = name[10:]
    if name not in TABLE:
        raise ValueError(f"unknown block: {name!r}")
    props = {}
    if rest:
        if not rest.endswith("]"):
            raise ValueError(f"bad state string: {state!r}")
        allowed = TABLE[name][0] if TABLE[name] else {}
        for part in rest[:-1].split(","):
            k, _, v = part.partition("=")
            k, v = k.strip(), v.strip()
            if k not in allowed:
                raise ValueError(f"{name} has no property {k!r} (has: {sorted(allowed)})")
            if v not in allowed[k]:
                raise ValueError(f"{name}[{k}] cannot be {v!r} (allowed: {allowed[k]})")
            props[k] = v
    out = (name, props)
    _cache[state] = out
    return out


def canon(state):
    name, props = parse(state)
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def st(name, **props):
    """Build a state string: st("oak_stairs", facing="north")."""
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"


def name_of(state):
    return state.partition("[")[0]


def exists(name):
    return name in TABLE


def variant(base, kind):
    """Find the stairs/slab/wall/... sibling of a full block: variant("stone_bricks", "stairs")."""
    cands = [f"{base}_{kind}"]
    if base.endswith("_planks"):
        cands.append(f"{base[:-7]}_{kind}")
    if base.endswith("s"):
        cands.append(f"{base[:-1]}_{kind}")
    if base.endswith("_block"):
        cands.append(f"{base[:-6]}_{kind}")
    for c in cands:
        if c in TABLE:
            return c
    raise KeyError(f"no {kind} variant for {base}")


def stairs(base, facing, half="bottom"):
    """Stairs whose tall side points towards `facing`."""
    return f"{variant(base, 'stairs')}[facing={facing},half={half}]"


def slab(base, kind="bottom"):
    return f"{variant(base, 'slab')}[type={kind}]"


# Blocks that pop off when their support is missing. They go into the second placement pass.
_NEEDS_SUPPORT = re.compile(
    r"(^|_)(torch|lantern|door|button|pressure_plate|sign|banner|carpet|sapling|bed|candle|rail|"
    r"ladder|lever|vine|vines|vines_plant|lichen|roots|sprouts|fungus|petals|wildflowers|litter|"
    r"bush|grass|fern|tulip|orchid|allium|bluet|daisy|cornflower|valley|rose|dandelion|poppy|"
    r"torchflower|sunflower|lilac|peony|pitcher_plant|azalea|mushroom|wheat|carrots|potatoes|"
    r"beetroots|stem|cane|bamboo|cactus|lily_pad|seagrass|kelp|kelp_plant|pickle|dripleaf|"
    r"blossom|moss|dripstone|cluster|bud|snow|wire|repeater|comparator|tripwire|hook|bell|cake|"
    r"scaffolding|cocoa|eyeblossom|flower|propagule|fan|coral|egg|water|lava)$"
)
_FULL_OVERRIDES = {
    "moss_block", "pale_moss_block", "grass_block", "snow_block", "dripstone_block", "hay_block",
    "red_mushroom_block", "brown_mushroom_block", "mushroom_stem", "bamboo_block", "stripped_bamboo_block",
    "dried_kelp_block", "coral_block", "powder_snow", "azalea_leaves",
    "flowering_azalea_leaves", "muddy_mangrove_roots", "mangrove_roots", "budding_amethyst",
    "sea_lantern", "jack_o_lantern", "crimson_stem", "warped_stem", "stripped_crimson_stem",
    "stripped_warped_stem",
}
_HANGING = re.compile(r"(^|_)(vine|vines|vines_plant|hanging_roots|hanging_moss|spore_blossom)$")


def needs_support(state):
    name, props = parse(state)
    if name in _FULL_OVERRIDES or name.endswith("_coral_block"):
        return False
    return bool(_NEEDS_SUPPORT.search(name))


def hangs(state):
    name, props = parse(state)
    if _HANGING.search(name):
        return True
    if props.get("hanging") == "true":
        return True
    return name == "pointed_dripstone" and props.get("vertical_direction") == "down"

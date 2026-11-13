"""What the game knows about a block besides its model: how it treats light, how it is shaded,
tinted and nudged off the grid. Written out from the 26.3 client (Blocks, BlockBehaviour,
BlockColors), for the blocks scenes are likely to use; anything not listed behaves like stone when
its model is a whole cube and like a flower otherwise.
"""

# full cubes that neither block light nor sight (Properties.noOcclusion)
SEE_THROUGH = ("glass", "ice", "frosted_ice", "slime_block", "honey_block", "spawner", "trial_spawner", "vault", "beacon",
               "mangrove_roots", "barrier", "structure_void", "copper_grate", "exposed_copper_grate",
               "weathered_copper_grate", "oxidized_copper_grate", "waxed_copper_grate", "waxed_exposed_copper_grate",
               "waxed_weathered_copper_grate", "waxed_oxidized_copper_grate")
# whole cubes to look at, but not to stand on: no dark corners beside them
SOFT = ("soul_sand", "mud", "honey_block", "powder_snow")
INVISIBLE = ("air", "cave_air", "void_air", "light", "barrier", "structure_void", "moving_piston")
WATER_PLANTS = ("seagrass", "tall_seagrass", "kelp", "kelp_plant", "bubble_column")

EMIT = {
    "lantern": 15, "soul_lantern": 10, "torch": 14, "wall_torch": 14, "soul_torch": 10, "soul_wall_torch": 10,
    "copper_torch": 14, "copper_wall_torch": 14, "glowstone": 15, "sea_lantern": 15, "shroomlight": 15,
    "ochre_froglight": 15, "verdant_froglight": 15, "pearlescent_froglight": 15, "jack_o_lantern": 15, "end_rod": 14,
    "lava": 15, "fire": 15, "soul_fire": 10, "magma_block": 3, "glow_lichen": 7, "crying_obsidian": 10,
    "amethyst_cluster": 5, "large_amethyst_bud": 4, "medium_amethyst_bud": 2, "small_amethyst_bud": 1,
    "beacon": 15, "conduit": 15, "end_portal": 15, "nether_portal": 11, "enchanting_table": 7, "ender_chest": 7,
    "brewing_stand": 1, "brown_mushroom": 1, "dragon_egg": 1, "end_portal_frame": 1, "sculk_catalyst": 6,
    "firefly_bush": 2, "lava_cauldron": 15, "end_gateway": 15,
}
LIT = {"campfire": 15, "soul_campfire": 10, "redstone_lamp": 15, "furnace": 13, "smoker": 13, "blast_furnace": 13,
       "redstone_torch": 7, "redstone_wall_torch": 7, "redstone_ore": 9, "deepslate_redstone_ore": 9}
BULB = {"": 15, "exposed": 12, "weathered": 8, "oxidized": 4}

OFFSET_XYZ = ("short_grass", "fern", "short_dry_grass", "tall_dry_grass", "small_dripleaf")
OFFSET_XZ = ("dandelion", "golden_dandelion", "torchflower", "poppy", "blue_orchid", "allium", "azure_bluet", "red_tulip",
             "orange_tulip", "white_tulip", "pink_tulip", "oxeye_daisy", "cornflower", "wither_rose",
             "lily_of_the_valley", "sunflower", "lilac", "rose_bush", "peony", "tall_grass", "large_fern",
             "pitcher_plant", "mangrove_propagule", "bamboo", "bamboo_sapling", "warped_roots", "nether_sprouts",
             "crimson_roots", "pointed_dripstone", "hanging_roots", "open_eyeblossom", "closed_eyeblossom",
             "tall_seagrass")

SIDES = {"north": 2, "south": 3, "west": 4, "east": 5}
LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}
RIGHT = {v: k for k, v in LEFT.items()}


def is_leaves(name):
    return name.endswith("_leaves")


def is_glass(name):
    """TransparentBlock: glass of every colour, also tinted."""
    return name == "glass" or name.endswith("_glass")


def see_through(name):
    return is_leaves(name) or is_glass(name) or name in SEE_THROUGH


def emission(name, props):
    """Block light a state gives off (Properties.lightLevel)."""
    if name == "light":
        return int(props.get("level", 15))
    if name.endswith("candle") or name.endswith("candle_cake"):
        return 3 * int(props.get("candles", 1)) if props.get("lit") == "true" else 0
    if name == "sea_pickle":
        return 3 + 3 * int(props.get("pickles", 1)) if props.get("waterlogged") == "true" else 0
    if name == "respawn_anchor":
        return int(props.get("charges", 0)) * 15 // 4
    if name == "cave_vines" or name == "cave_vines_plant":
        return 14 if props.get("berries") == "true" else 0
    if name.endswith("copper_bulb"):
        if props.get("lit") != "true":
            return 0
        stage = name.replace("waxed_", "").replace("copper_bulb", "").rstrip("_")
        return BULB.get(stage, 15)
    if name.endswith("copper_lantern"):
        return 15
    if name in LIT:
        return LIT[name] if props.get("lit") == "true" else 0
    return EMIT.get(name, 0)


def wet(name, props):
    """Does the cell hold water besides the block?"""
    return name == "water" or name in WATER_PLANTS or props.get("waterlogged") == "true"


def solid(name, cube):
    """isSolidRender: a whole cube that shuts out light and sight."""
    return cube and not see_through(name)


def dampening(name, props, cube):
    """getLightDampening: 15 shuts light out, 1 takes one level from light passing through."""
    if name == "tinted_glass":
        return 15
    if solid(name, cube):
        return 15
    if is_leaves(name) or wet(name, props) or name in ("cobweb", "ice", "frosted_ice", "slime_block", "honey_block"):
        return 1
    if cube and not is_glass(name) and name not in INVISIBLE:
        return 1
    return 0


def shut_faces(name, props):
    """Bit f set where face f of a block that is not a whole cube still shuts light out
    (useShapeForLightOcclusion: slabs, stairs, farmland, paths)."""
    if name.endswith("_slab"):
        return {"bottom": 1, "top": 2}.get(props.get("type"), 0)
    if name in ("farmland", "dirt_path"):
        return 1
    if name.endswith("_stairs"):
        bits = 2 if props.get("half") == "top" else 1
        facing, shape = props.get("facing", "north"), props.get("shape", "straight")
        if shape == "straight":
            bits |= 1 << SIDES[facing]
        elif shape == "inner_left":
            bits |= (1 << SIDES[facing]) | (1 << SIDES[LEFT[facing]])
        elif shape == "inner_right":
            bits |= (1 << SIDES[facing]) | (1 << SIDES[RIGHT[facing]])
        return bits
    return 0


def casts_shade(name, cube):
    """getShadeBrightness below 1: the block darkens the corners of faces beside it."""
    return cube and not is_glass(name) and name not in SOFT and name not in INVISIBLE


def cull_class(name):
    """Blocks that leave out the faces between two of their own kind (skipRendering)."""
    return is_glass(name) or name.endswith("glass_pane") or name == "iron_bars" or name.endswith("copper_bars") \
        or name in ("ice", "slime_block", "honey_block")


def offset(name):
    """0 none, 1 sideways, 2 sideways and down (BlockBehaviour.OffsetType)."""
    return 2 if name in OFFSET_XYZ else 1 if name in OFFSET_XZ else 0


def tint(name, index, look):
    """Colour a face with this tint index is multiplied with, or None (BlockColors). look gives
    the biome's grass, foliage, dry_foliage and water colours."""
    if name in ("grass_block", "short_grass", "tall_grass", "fern", "large_fern", "potted_fern", "bush", "sugar_cane"):
        return look.grass if index == 0 else None
    if name in ("pink_petals", "wildflowers"):
        return look.grass if index == 1 else None
    if name == "spruce_leaves":
        return (0x61 / 255.0, 0x99 / 255.0, 0x61 / 255.0) if index == 0 else None
    if name == "birch_leaves":
        return (0x80 / 255.0, 0xa7 / 255.0, 0x55 / 255.0) if index == 0 else None
    if name in ("oak_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "mangrove_leaves", "vine"):
        return look.foliage if index == 0 else None
    if name == "leaf_litter":
        return look.dry_foliage if index == 0 else None
    if name == "lily_pad":
        return (0x20 / 255.0, 0x80 / 255.0, 0x30 / 255.0) if index == 0 else None
    if name in ("water_cauldron", "water", "bubble_column"):
        return look.water if index == 0 else None
    if name in ("attached_melon_stem", "attached_pumpkin_stem"):
        return (0xe0 / 255.0, 0xc7 / 255.0, 0x1c / 255.0) if index == 0 else None
    return None

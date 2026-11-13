"""Which block is which material (plan/ART-PLAN.md, section 6.2: the occupancy table).

The builders (main building, site, interiors) name materials by the roles below and never by what
the block is called in the vanilla game; the materials part decides what a role looks like. Both
sides can then work without waiting for each other.

    from scenes.obs.common import blocks as B

    B.ASHLAR_FINE.block      "smooth_sandstone"
    B.ASHLAR_FINE.stairs     "smooth_sandstone_stairs"   (None where the family has no such shape)
    B.IRON_RIVETED.slab      "oxidized_cut_copper_slab"
    B.WINDOW_LIT.pane        "yellow_stained_glass_pane"
    B.PANELS["dial"]         "white_glazed_terracotta"
    B.CLOUD[2]               "dead_bubble_coral_block"   (the middle one of the five cloud tones)

Block states are added by the caller: B.ASHLAR_FINE.stairs + "[half=top,facing=east]".

Rules that come with the table:
  - a block listed here as repainted is never used for what it is in the vanilla game;
  - verdigris is always the waxed_ family; every oxidized_* block without waxed_ is cast iron;
  - blocks that are not listed are used as the vanilla game draws them, or not at all.

A0 keeps this file. A change is asked for in the group.
"""


class Family:
    """A material and the shapes it comes in. A shape the vanilla family lacks is None."""

    def __init__(self, block, stairs=None, slab=None, wall=None, pane=None):
        self.block = block
        self.stairs = stairs
        self.slab = slab
        self.wall = wall
        self.pane = pane

    def all(self):
        return [b for b in (self.block, self.stairs, self.slab, self.wall, self.pane) if b]

    def __repr__(self):
        return f"Family({', '.join(self.all())})"


def _family(block, shapes="", stem=None):
    stem = stem or block
    return Family(block, **{shape: f"{stem}_{shape}" for shape in shapes.split()})


# --- repainted: grey-white stone (the sandstone family) -------------------------------------------
ASHLAR_ROUGH = _family("sandstone", "stairs slab wall")         # rusticated: base storey, stair cheeks
ASHLAR_FINE = _family("smooth_sandstone", "stairs slab")        # dressed: main walls; two courses to a block
ASHLAR_PANEL = _family("cut_sandstone", "slab")                 # sunk panel: under windows, friezes
ASHLAR_EMBLEM = "chiseled_sandstone"                            # the emblem block: lintels, above capitals

# --- repainted: cast iron (every oxidized_* block without waxed_) -----------------------------------
IRON_PLATE = "oxidized_copper"                                  # plain plate: casings, tanks
IRON_RIVETED = _family("oxidized_cut_copper", "stairs slab")    # riveted plate: beams, decks, iron stairs
IRON_CAST = "oxidized_chiseled_copper"                          # cast ornament plate: balustrade panels
IRON_GRATE = "oxidized_copper_grate"                            # open grating: walkways
IRON_DOOR = "oxidized_copper_door"                              # riveted door with a porthole
IRON_HATCH = "oxidized_copper_trapdoor"                         # hatch, louvre
IRON_BARS = "oxidized_copper_bars"                              # railing
IRON_PIPE = "oxidized_copper_chain"                             # thin pipe or cable, three directions (axis)
IRON_ROD = "oxidized_lightning_rod"                             # thin rod, six directions (facing)
IRON_BULB = "oxidized_copper_bulb"                              # caged lamp, dim (third-rank light)
IRON_LANTERN = "oxidized_copper_lantern"                        # iron pendant lamp

# --- repainted: windows (stained glass, blocks and panes) --------------------------------------------
WINDOW_LIT = Family("yellow_stained_glass", pane="yellow_stained_glass_pane")            # lit window
WINDOW_CURTAIN = Family("orange_stained_glass", pane="orange_stained_glass_pane")        # lit, half-drawn curtain
WINDOW_FROSTED = Family("white_stained_glass", pane="white_stained_glass_pane")          # lit, frosted
WINDOW_DARK = Family("gray_stained_glass", pane="gray_stained_glass_pane")               # dark, holds the sky
WINDOW_BLIND = Family("black_stained_glass", pane="black_stained_glass_pane")            # darkest: shutters
SKYLIGHT = Family("light_gray_stained_glass", pane="light_gray_stained_glass_pane")      # iron-framed roof light
LIT_WINDOWS = (WINDOW_LIT, WINDOW_CURTAIN, WINDOW_FROSTED)
DARK_WINDOWS = (WINDOW_DARK, WINDOW_BLIND)

# --- repainted: instrument panels (glazed terracotta; the panel shows on the side named by facing) --
PANELS = {
    "dial": "white_glazed_terracotta",
    "knife_switch": "orange_glazed_terracotta",
    "tubes": "magenta_glazed_terracotta",           # animated
    "scope": "light_blue_glazed_terracotta",        # animated
    "counter": "yellow_glazed_terracotta",          # animated
    "patch_panel": "lime_glazed_terracotta",
    "fuses": "pink_glazed_terracotta",
    "bell": "gray_glazed_terracotta",
    "pilot_lamps": "light_gray_glazed_terracotta",  # animated
    "louvre": "cyan_glazed_terracotta",
    "drawers": "purple_glazed_terracotta",
    "nameplate": "blue_glazed_terracotta",
    "relays": "brown_glazed_terracotta",
    "bus_switch": "green_glazed_terracotta",
    "gauges": "red_glazed_terracotta",
    "recorder": "black_glazed_terracotta",
}

# --- repainted, second batch: brass (the bamboo family) -----------------------------------------------
BRASS_PLATE = _family("bamboo_planks", "stairs slab", stem="bamboo")
BRASS_PATTERN = _family("bamboo_mosaic", "stairs slab")
BRASS_COLUMN = "bamboo_block"                                   # thick pipe or column (axis)
BRASS_RAIL = "bamboo_fence"
BRASS_GATE = "bamboo_fence_gate"
BRASS_DOOR = "bamboo_door"                                      # brass and frosted glass
BRASS_HATCH = "bamboo_trapdoor"
BRASS_BUTTON = "bamboo_button"
BRASS_SIGN = ("bamboo_sign", "bamboo_wall_sign", "bamboo_hanging_sign", "bamboo_wall_hanging_sign")
BRASS_SHELF = "bamboo_shelf"

# --- repainted, second batch: old copper (waxed exposed copper, brought to the palette's ramp) --------
OLD_COPPER = "waxed_exposed_copper"
OLD_COPPER_CUT = _family("waxed_exposed_cut_copper", "stairs slab")   # gutters, flashings

# --- repainted: small pieces --------------------------------------------------------------------------
WAINSCOT = "dark_oak_trapdoor"                                  # wall panelling indoors
BRASS_INLAY = "yellow_carpet"                                   # brass line in the floor (the meridian)
ENAMEL_SIGN = ("oak_sign", "oak_wall_sign", "oak_hanging_sign", "oak_wall_hanging_sign")

# --- repainted: the cloud sea built of blocks (five flat tones, dark to light like RAMPS["cloud"]) ----
# Provisional (A0, 2026-11-14): the family is settled on the real-game pictures of the cloudsea card.
CLOUD = ("dead_horn_coral_block", "dead_fire_coral_block", "dead_bubble_coral_block",
         "dead_brain_coral_block", "dead_tube_coral_block")

# --- used as the vanilla game draws them ---------------------------------------------------------------
VERDIGRIS = "waxed_oxidized_copper"
VERDIGRIS_CUT = _family("waxed_oxidized_cut_copper", "stairs slab")   # dome plates, spire, ridges
VERDIGRIS_CAST = "waxed_oxidized_chiseled_copper"
VERDIGRIS_STREAK = _family("waxed_weathered_cut_copper", "stairs slab")   # darker runs below the ribs
SLATE_BRICK = _family("deepslate_bricks", "stairs slab wall", stem="deepslate_brick")   # plinths, retaining walls
SLATE_TILE = _family("deepslate_tiles", "stairs slab wall", stem="deepslate_tile")      # roofs
SLATE_SMOOTH = _family("polished_deepslate", "stairs slab wall")
TUFF_BRICK = _family("tuff_bricks", "stairs slab wall", stem="tuff_brick")              # lower terrace, power house
TUFF_SMOOTH = _family("polished_tuff", "stairs slab wall")
TUFF = _family("tuff", "stairs slab wall")
DARK_WOOD = _family("dark_oak_planks", "stairs slab", stem="dark_oak")                  # indoors: panelling, furniture
FLOOR_WOOD = _family("spruce_planks", "stairs slab", stem="spruce")                     # indoor floors
PALE_WOOD = _family("pale_oak_planks", "stairs slab", stem="pale_oak")                  # light wood where one is needed
VANILLA_BARS = "iron_bars"
VANILLA_CHAIN = "iron_chain"
LIGHT = "light"                                                 # the invisible light source: light[level=N]

REPAINTED = [ASHLAR_ROUGH, ASHLAR_FINE, ASHLAR_PANEL, ASHLAR_EMBLEM, IRON_PLATE, IRON_RIVETED, IRON_CAST,
             IRON_GRATE, IRON_DOOR, IRON_HATCH, IRON_BARS, IRON_PIPE, IRON_ROD, IRON_BULB, IRON_LANTERN,
             WINDOW_LIT, WINDOW_CURTAIN, WINDOW_FROSTED, WINDOW_DARK, WINDOW_BLIND, SKYLIGHT,
             *PANELS.values(), BRASS_PLATE, BRASS_PATTERN, BRASS_COLUMN, BRASS_RAIL, BRASS_GATE, BRASS_DOOR,
             BRASS_HATCH, BRASS_BUTTON, *BRASS_SIGN, BRASS_SHELF, OLD_COPPER, OLD_COPPER_CUT, WAINSCOT,
             BRASS_INLAY, *ENAMEL_SIGN, *CLOUD]
VANILLA = [VERDIGRIS, VERDIGRIS_CUT, VERDIGRIS_CAST, VERDIGRIS_STREAK, SLATE_BRICK, SLATE_TILE, SLATE_SMOOTH,
           TUFF_BRICK, TUFF_SMOOTH, TUFF, DARK_WOOD, FLOOR_WOOD, PALE_WOOD, VANILLA_BARS, VANILLA_CHAIN, LIGHT]


def ids(entries):
    """Flat list of block ids from a list of ids and families."""
    out = []
    for e in entries:
        out += e.all() if isinstance(e, Family) else [e]
    return out


def missing(assets):
    """Block ids of this table that the game (an artkit.gameassets.Assets) has no block state file for."""
    out = []
    for block in ids(REPAINTED + VANILLA):
        try:
            assets.json(f"assets/minecraft/blockstates/{block}.json")
        except Exception:
            out.append(block)
    return out

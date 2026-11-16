#!/usr/bin/env python3
"""Where a visitor gets to on foot, worked out from the blocks (plan/packages/common/walk.md, "卡").

    walkreach.py <scene> [--canvas <pickle>] [--out <folder>] [--start x,y,z | <landmark>] [--points <file>]
                 [--name reach] [--line y | none] [--home <blocks> | none] [--bounds x0,z0,x1,z1] [--scale n]
        builds the scene (or reads the pickle build/render.py --canvas wrote; a whole `obs` is built
        on a worker node, never on the shared machine), works out where a person can stand and how
        he gets from one place to the next, and writes <folder>/reach.json (what was found),
        <folder>/reach.png (a map) and <folder>/reach.txt (the same as two plans in characters, a
        block a character, to read coordinates from). Without --out it only says what it found.
    walkreach.py --selftest
        the arithmetic on small worlds built by hand; needs no scene.

For the walk-through's other tool (tools/walk.py) and for anyone who wants the same answers:

    cells = canvas.b                             # the blocks of a built scene, or the "b" of the pickle
    walkreach.feet(cells, x, z, near_y)          # where the feet stand at the point (x, z); None: nowhere
    reach = walkreach.reach_of(cells, (x, y, z)) # everything a person gets to from there
    reach.kind_at(x, z, near_y)                  # "walk", "hop", "fall", "trap" or None
    reach.report(points, line=walkreach.CATCH)   # what the command writes into reach.json; the line is the export's
    reach.path((x, y, z))                        # the way there from the start, a list of points

A person is the game's player: 0.6 wide and 1.8 high, the eye 1.62 up. He walks up a rise of 0.6
(half a block: a slab, a stair) and has to jump for more; a jump clears 1.2 (a block, not a block
and a half: a wall or a fence is 1.5 to him). He drops any height: the finished map has no fall
damage (plan/STATUS.md). Only blocks stop him. A display entity has no collision box at all, so a
model railing, a model gate and a model door leaf are air to him; so is a light block.

His middle stands on a lattice of half blocks, and he goes from one lattice point to the next of
the four beside it. That is fine enough for a world of blocks: a way one block wide has a lattice
point in its middle, a way two wide one on the joint as well, and a diagonal squeeze between two
corners, which the game does not let him through either, is not on it.

What is found, by how a place is reached from the start:

    walk   on foot alone, no rise over 0.6 either way: the visitor's way
    hop    with jumps of up to 1.2 and drops of up to 1.2 as well: what one does without thinking
    fall   only by dropping further than that, and there is a way back to the start
    trap   reached from the start, and no way back: 掉下去出不来
    void   a step off the lowest block of the scene, or out of the bounds looked at

The finished map sends a visitor home who falls under a line in the cloud (the director's desk,
11-16 06:08) or comes to stand on a block of the cloud sea, which is solid (common/export: feet
under y -30, CATCH; the block 0.2 under the middle of his feet one of the block table's CLOUD).
So trap ground is told apart once more: the part with a way on to either (--line, --home; a slope
one slides off) and the part with none (a ledge, a pit: "stuck"), which those rules never see.

and besides: every piece reached by hopping only (a way that needs a jump is 走不通 for some), every
standing place with less than two blocks over the head, every low gap beside the way that only
head room closes, and the points named with --points (the route's landmarks) with how each is
reached and what kind of way leads from each to the next. The shapes are the game's collision
shapes of the blocks the occupancy table allows (build/scenes/obs/common/blocks.py); a block whose
shape is not written down here counts as a whole cube and is named in the report, so nothing
passes unseen for a guess.

Scenes leave out what the game works out from the neighbours when the structure is placed: which
way bars, panes, walls and fences join, where stairs turn a corner. Those are filled in first, by
the rules the offline pictures use (build/artkit/shapes.py), on a copy of the blocks: a railing of
bars written without them would be a row of thin posts with room to walk between.
"""
import argparse
import importlib
import json
import math
import os
import pickle
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("C164_BUILD") or os.path.normpath(os.path.join(HERE, "..", "build")))

WIDTH, HEIGHT, EYE = 0.6, 1.8, 1.62
HALF = WIDTH / 2.0
STEP = 0.6          # a rise walked up without a jump
JUMP = 1.2          # a rise a jump clears (its apex is 1.25)
GRID = 0.5          # the lattice
HEAD = 2.0          # what the card asks for over a person's head
CROUCH = 1.5        # a gap lower than HEIGHT and at least this lets a sneaking person through
EPS = 1e-6
Q = 32              # heights are kept as whole 32nds of a block

KINDS = ("walk", "hop", "fall", "trap")
CATCH = -30.0       # common/export's line: feet under it are put back at the spawn (plan/packages/site/terrain.md)
UNDER = 0.2         # ... and so are feet with a block of the cloud sea this far under their middle


# ---- the collision shapes ------------------------------------------------------------------------
def _b(x0, y0, z0, x1, y1, z1):
    return (x0 / 16.0, y0 / 16.0, z0 / 16.0, x1 / 16.0, y1 / 16.0, z1 / 16.0)


FULL = (_b(0, 0, 0, 16, 16, 16),)
LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}
RIGHT = {v: k for k, v in LEFT.items()}
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}
_SIDE = {"north": (None, 0), "south": (None, 1), "west": (0, None), "east": (1, None)}
# the slab a door or an open trapdoor is, by the side of the cell it stands on (the game's names)
_SLAB = {"east": _b(0, 0, 0, 3, 16, 16), "south": _b(0, 0, 0, 16, 16, 3),
         "west": _b(13, 0, 0, 16, 16, 16), "north": _b(0, 0, 13, 16, 16, 16)}
_DOOR_OPEN = {("east", True): "north", ("east", False): "south", ("south", True): "east", ("south", False): "west",
              ("west", True): "south", ("west", False): "north", ("north", True): "west", ("north", False): "east"}

NOTHING = {"air", "cave_air", "void_air", "light", "structure_void", "water", "lava", "fire", "soul_fire",
           "cobweb", "powder_snow", "short_grass", "tall_grass", "fern", "large_fern", "dead_bush", "dandelion",
           "poppy", "allium", "cornflower", "lily_of_the_valley", "vine", "glow_lichen", "sugar_cane", "kelp",
           "kelp_plant", "seagrass", "tall_seagrass", "lever", "tripwire", "tripwire_hook", "redstone_wire",
           "ladder", "bubble_column", "hanging_roots", "spore_blossom", "short_dry_grass", "tall_dry_grass",
           "leaf_litter", "pink_petals", "wildflowers", "firefly_bush", "bush", "sweet_berry_bush"}
NOTHING_ENDS = ("_sign", "_button", "rail", "torch", "_sapling", "_tulip", "_orchid", "_bluet", "_daisy", "_banner",
                "_pressure_plate", "_roots", "_fungus", "_vines", "_vines_plant", "_sprouts", "_coral", "_coral_fan",
                "_wall_fan")
CLIMBS = {"ladder", "vine", "scaffolding", "twisting_vines", "twisting_vines_plant", "weeping_vines",
          "weeping_vines_plant", "cave_vines", "cave_vines_plant"}
# whole cubes by their names, though a rule below would catch the name's end
CUBES_ENDS = ("_block", "_bricks", "_tiles", "_planks", "_copper", "_copper_grate", "_copper_bulb", "_terracotta",
              "_stained_glass", "_ore", "_wood", "_log", "_concrete", "_wool", "sandstone", "deepslate")


def _stairs(props):
    facing, shape = props.get("facing", "north"), props.get("shape", "straight")

    def on(side):
        xh, zh = _SIDE[side]
        return {(a, c) for a in (0, 1) for c in (0, 1) if (xh is None or a == xh) and (zh is None or c == zh)}

    step = on(facing)
    if shape != "straight":
        turn = (LEFT if shape.endswith("left") else RIGHT)[facing]
        step = step & on(turn) if shape.startswith("outer") else step | (on(OPPOSITE[facing]) & on(turn))
    top = props.get("half", "bottom") == "top"
    out = [_b(0, 8, 0, 16, 16, 16) if top else _b(0, 0, 0, 16, 8, 16)]
    for a, c in sorted(step):
        out.append(_b(a * 8, 0 if top else 8, c * 8, a * 8 + 8, 8 if top else 16, c * 8 + 8))
    return tuple(out)


def _arms(props, post, arms, yes=("true", "low", "tall")):
    out = [post] if post else []
    for side, box in arms.items():
        if props.get(side, "false") in yes:
            out.append(box)
    return tuple(out)


_WALL = {"north": _b(5, 0, 0, 11, 24, 11), "south": _b(5, 0, 5, 11, 24, 16),
         "west": _b(0, 0, 5, 11, 24, 11), "east": _b(5, 0, 5, 16, 24, 11)}
_PANE = {"north": _b(7, 0, 0, 9, 16, 9), "south": _b(7, 0, 7, 9, 16, 16),
         "west": _b(0, 0, 7, 9, 16, 9), "east": _b(7, 0, 7, 16, 16, 9)}
_FENCE = {"north": _b(6, 0, 0, 10, 24, 10), "south": _b(6, 0, 6, 10, 24, 16),
          "west": _b(0, 0, 6, 10, 24, 10), "east": _b(6, 0, 6, 16, 24, 10)}


def shape(name, props):
    """(boxes, how): the collision boxes of a block state in its own cell, each (x0, y0, z0, x1, y1,
    z1) in blocks (a wall and a fence stand half a block over the cell), and how they were got:
    "cube", "none", "shape" (written down here) or "guess" (not written down: a whole cube)."""
    if name in NOTHING or name.endswith(NOTHING_ENDS):
        return (), "none"
    if name.endswith("_slab"):
        kind = props.get("type", "bottom")
        return ((_b(0, 0, 0, 16, 8, 16),) if kind == "bottom" else (_b(0, 8, 0, 16, 16, 16),) if kind == "top"
                else FULL), "shape"
    if name.endswith("_stairs"):
        return _stairs(props), "shape"
    if name.endswith("_wall"):
        return _arms(props, _b(4, 0, 4, 12, 24, 12) if props.get("up", "true") == "true" else None, _WALL), "shape"
    if name.endswith(("_bars", "_pane")):
        return _arms(props, _b(7, 0, 7, 9, 16, 9), _PANE), "shape"
    if name.endswith("_fence"):
        return _arms(props, _b(6, 0, 6, 10, 24, 10), _FENCE), "shape"
    if name.endswith("_fence_gate"):
        if props.get("open", "false") == "true":
            return (), "shape"
        across = props.get("facing", "north") in ("north", "south")
        return ((_b(0, 0, 6, 16, 24, 10),) if across else (_b(6, 0, 0, 10, 24, 16),)), "shape"
    if name.endswith("_trapdoor"):
        if props.get("open", "false") == "true":
            return (_SLAB[props.get("facing", "north")],), "shape"
        return ((_b(0, 13, 0, 16, 16, 16),) if props.get("half", "bottom") == "top" else (_b(0, 0, 0, 16, 3, 16),)), "shape"
    if name.endswith("_door"):
        facing = props.get("facing", "north")
        if props.get("open", "false") == "true":
            facing = _DOOR_OPEN[(facing, props.get("hinge", "left") == "right")]
        return (_SLAB[facing],), "shape"
    if name.endswith("chain"):
        axis = props.get("axis", "y")
        return ((_b(6.5, 0, 6.5, 9.5, 16, 9.5),) if axis == "y" else (_b(0, 6.5, 6.5, 16, 9.5, 9.5),) if axis == "x"
                else (_b(6.5, 6.5, 0, 9.5, 9.5, 16),)), "shape"
    if name.endswith("lightning_rod"):
        facing = props.get("facing", "up")
        return ((_b(6, 0, 6, 10, 16, 10),) if facing in ("up", "down") else (_b(6, 6, 0, 10, 10, 16),)
                if facing in ("north", "south") else (_b(0, 6, 6, 16, 10, 10),)), "shape"
    if name.endswith("lantern") and name != "sea_lantern" and name != "jack_o_lantern":
        return ((_b(5, 1, 5, 11, 10, 11),) if props.get("hanging", "false") == "true" else (_b(5, 0, 5, 11, 9, 11),)), "shape"
    if name.endswith("_carpet"):
        return (_b(0, 0, 0, 16, 1, 16),), "shape"
    if name == "snow":
        layers = int(props.get("layers", 1))
        return ((_b(0, 0, 0, 16, 2 * (layers - 1), 16),) if layers > 1 else ()), "shape"
    if name.endswith("_shelf"):
        return (_SLAB[OPPOSITE[props.get("facing", "north")]],), "shape"       # near enough: its back board
    if name == "scaffolding":
        return (_b(0, 14, 0, 16, 16, 16),), "shape"
    if name.endswith(CUBES_ENDS) or name in ("stone", "andesite", "tuff", "glass", "barrier", "bedrock", "dirt",
                                              "gravel", "sand", "obsidian", "granite", "diorite", "calcite",
                                              "basalt", "blackstone", "ice", "packed_ice", "blue_ice", "clay",
                                              "cobblestone", "cobbled_deepslate", "polished_deepslate",
                                              "polished_tuff", "polished_andesite", "smooth_stone", "bookshelf",
                                              "chiseled_bookshelf", "glowstone", "sea_lantern", "netherrack"):
        return FULL, "cube"
    return FULL, "guess"


def _is_cube(state):
    return shape(*_props(state))[0] is FULL


def complete(cells):
    """(cells, done): the blocks with the properties the game works out from the neighbours filled
    in, as artkit/shapes.py does it for the offline pictures; a copy when anything changes. done is
    False when that module or its block table cannot be used (the blocks stay as they are written
    then, and the report says so)."""
    try:
        from artkit.shapes import Shaper
        out = dict(cells)
        Shaper(out, _is_cube).run()
    except Exception as err:                    # no artkit on the path, or a block its table does not know
        return cells, f"no ({type(err).__name__}: {err})"
    return out, "yes"


def _props(state):
    name, _, rest = state.partition("[")
    props = {}
    if rest:
        for part in rest.rstrip("]").split(","):
            k, _, v = part.partition("=")
            props[k.strip()] = v.strip()
    return (name[10:] if name.startswith("minecraft:") else name).strip(), props


# ---- the world: what is in the way, column by column ---------------------------------------------
class World:
    """The collision boxes of a scene's blocks, and what follows from them for a person standing."""

    def __init__(self, cells, bounds=None, home=()):
        """cells: {(x, y, z): state}, a canvas's b. bounds: (x0, z0, x1, z1) in blocks, the ground
        looked at (cells outside are not read, and a step out of it counts as leaving). home: the
        names of the blocks that send a visitor home who stands on them (the cloud sea's)."""
        self.census = {"cube": {}, "none": {}, "shape": {}, "guess": {}}
        self.climbs = 0
        cells, self.completed = complete(cells)
        self.cells, self.home = cells, frozenset(home)
        shapes, full, part = {}, {}, {}
        ymin = None
        for (x, y, z), state in cells.items():
            if bounds and not (bounds[0] - 1 <= x <= bounds[2] + 1 and bounds[1] - 1 <= z <= bounds[3] + 1):
                continue
            got = shapes.get(state)
            if got is None:
                name, props = _props(state)
                boxes, how = shape(name, props)
                got = shapes[state] = (boxes, how, name)
            boxes, how, name = got
            tally = self.census[how]
            tally[name] = tally.get(name, 0) + 1
            if name in CLIMBS:
                self.climbs += 1
            if not boxes:
                continue
            if ymin is None or y < ymin:
                ymin = y
            if boxes is FULL:
                full.setdefault((x, z), []).append(y)
            else:
                rows = part.setdefault((x, z), [])
                for x0, y0, z0, x1, y1, z1 in boxes:
                    rows.append((y + y0, y + y1, x + x0, z + z0, x + x1, z + z1))
        self.ymin = 0 if ymin is None else ymin
        self.full = {}
        for key, ys in full.items():            # runs of whole cubes, as spans
            ys.sort()
            spans, lo, last = [], ys[0], ys[0]
            for y in ys[1:]:
                if y != last + 1:
                    spans.append((float(lo), float(last + 1)))
                    lo = y
                last = y
            spans.append((float(lo), float(last + 1)))
            self.full[key] = spans
        self.part = part
        self.bounds = bounds
        self._solid, self._stand = {}, {}

    # -- one lattice point ---------------------------------------------------------------------------
    def solid(self, i, j):
        """What stands in the way of a person whose middle is at the lattice point (i, j), that is at
        (i / 2, j / 2): the spans of height (y0, y1) taken by collision boxes under his 0.6 square,
        merged, lowest first."""
        key = (i, j)
        hit = self._solid.get(key)
        if hit is None:
            hit = self._solid[key] = self.spans(i * GRID, j * GRID)
        return hit

    def spans(self, px, pz):
        """The same for a person whose middle is at any point (px, pz)."""
        x0, x1, z0, z1 = px - HALF, px + HALF, pz - HALF, pz + HALF
        spans = []
        for cx in range(int(math.floor(x0 + EPS)), int(math.floor(x1 - EPS)) + 1):
            for cz in range(int(math.floor(z0 + EPS)), int(math.floor(z1 - EPS)) + 1):
                spans += self.full.get((cx, cz), ())
                for y0, y1, bx0, bz0, bx1, bz1 in self.part.get((cx, cz), ()):
                    if bx0 < x1 - EPS and bx1 > x0 + EPS and bz0 < z1 - EPS and bz1 > z0 + EPS:
                        spans.append((y0, y1))
        spans.sort()
        out = []
        for y0, y1 in spans:
            if out and y0 <= out[-1][1] + EPS:
                if y1 > out[-1][1]:
                    out[-1] = (out[-1][0], y1)
            else:
                out.append((y0, y1))
        return out

    def stand(self, i, j):
        """[(feet, room)]: the heights a person can stand at with his middle at the lattice point, and
        how much is free over his feet there (inf under the sky), lowest first."""
        key = (i, j)
        hit = self._stand.get(key)
        if hit is None:
            hit = self._stand[key] = self.places(self.solid(i, j))
        return hit

    def under(self, i, j, top):
        """The names of the blocks the game finds UNDER the middle of feet that stand at `top` on the
        lattice point ("air": none). A point on a joint between cells has the cell on either side
        of it, a point on a corner all four."""
        y = int(math.floor(top - UNDER + EPS))
        cols = []
        for v in (i * GRID, j * GRID):
            near = int(round(v))
            cols.append([near - 1, near] if abs(v - near) < EPS else [int(math.floor(v))])
        names = []
        for x in cols[0]:
            for z in cols[1]:
                state = self.cells.get((x, y, z))
                names.append(_props(state)[0] if state else "air")
        return names

    def sends_home(self, i, j, top):
        """Is a person who stands there put back at the spawn: is every block under his middle one
        of `home`? (On a joint he is caught on one side of it only, which is the node beside this.)"""
        return bool(self.home) and all(name in self.home for name in self.under(i, j, top))

    @staticmethod
    def places(spans):
        """[(feet, room)] of the spans of one point: every top with a person's height free over it."""
        out = []
        for n, (_, top) in enumerate(spans):
            room = spans[n + 1][0] - top if n + 1 < len(spans) else math.inf
            if room >= HEIGHT - EPS:
                out.append((top, room))
        return out

    @staticmethod
    def _free(spans, lo, hi):
        """Is the height lo .. hi free of the spans?"""
        for y0, y1 in spans:
            if y0 >= hi - EPS:
                return True
            if y1 > lo + EPS:
                return False
        return True

    def step(self, i, j, h, di, dj):
        """One step from the lattice point (i, j), feet at h, to the next one in the direction (di,
        dj). Returns (kind, feet there, rise): kind "walk" (a rise or drop of at most 0.6), "jump"
        (a rise of up to 1.2), "drop" (a fall of any height), "void" (nothing to land on, or out of
        the bounds) or None (no way)."""
        here, there = self.solid(i, j), self.solid(i + di, j + dj)
        if self.bounds:
            x, z = (i + di) * GRID, (j + dj) * GRID
            if not (self.bounds[0] <= x <= self.bounds[2] + 1 and self.bounds[1] <= z <= self.bounds[3] + 1):
                return "void", None, None
        if self._free(there, h, h + HEIGHT):                    # level across, then down to what is below
            below = [top for _, top in there if top <= h + EPS]
            if not below:
                return "void", None, None
            land = max(below)
            return ("walk" if h - land <= STEP + EPS else "drop"), land, land - h
        for top, _ in self.stand(i + di, j + dj):               # up: the lowest place that takes him
            if top <= h + EPS:
                continue
            if top - h > JUMP + EPS:
                break
            if self._free(here, h, top + HEIGHT):
                return ("walk" if top - h <= STEP + EPS else "jump"), top, top - h
        return None, None, None

    # -- points ---------------------------------------------------------------------------------------
    @staticmethod
    def lattice(x, z):
        return int(round(x / GRID)), int(round(z / GRID))

    def feet(self, x, z, near_y=None, reach=None):
        """Where a person's feet stand whose middle is at the point (x, z), just there (not on the
        lattice): the standing height nearest to near_y, and None if that is further than `reach`
        from it; without near_y the highest one. None: he cannot stand there."""
        places = self.places(self.spans(x, z))
        if not places:
            return None
        if near_y is None:
            return places[-1][0]
        best = min(places, key=lambda p: abs(p[0] - near_y))[0]
        return None if reach is not None and abs(best - near_y) > reach + EPS else best

    def node(self, x, z, near_y=None, reach=1):
        """The lattice node (i, j, feet in 32nds) at or next to the point (x, z); None: none within
        `reach` lattice steps."""
        i0, j0 = self.lattice(x, z)
        best = None
        for r in range(reach + 1):
            for i in range(i0 - r, i0 + r + 1):
                for j in range(j0 - r, j0 + r + 1):
                    if max(abs(i - i0), abs(j - j0)) != r:
                        continue
                    for top, _ in self.stand(i, j):
                        off = (abs(top - near_y) if near_y is not None else -top, r)
                        if best is None or off < best[0]:
                            best = (off, (i, j, int(round(top * Q))))
            if best is not None and (near_y is None or best[0][0] <= JUMP):
                return best[1]
        return best[1] if best else None

    def reach(self, start, limit=4000000):
        return Reach(self, start, limit)


def point(node):
    """A node's point: (x, feet, z)."""
    return node[0] * GRID, node[2] / float(Q), node[1] * GRID


_WORLDS = {}


def home_blocks():
    """The names of the blocks that send a visitor home who stands on them: the cloud sea's, the
    block table's CLOUD (common/export puts them in a block tag). () without the block table."""
    try:
        return tuple(importlib.import_module("scenes.obs.common.blocks").CLOUD)
    except Exception:  # noqa: BLE001  no block table on the path, no cloud in it: no block sends anyone home
        return ()


def world_of(cells, bounds=None, home=None):
    """The World of a dictionary of blocks, made once for each dictionary. home: the blocks that
    send a visitor home (None: home_blocks())."""
    home = tuple(home_blocks() if home is None else home)
    key = (id(cells), bounds, home)
    if key not in _WORLDS:
        _WORLDS.clear()
        _WORLDS[key] = World(cells, bounds, home)
    return _WORLDS[key]


def feet(cells, x, z, near_y=None, reach=1.25):
    """Where the feet of a person stand whose middle is at the point (x, z) of a scene whose blocks
    are `cells`: the floor nearest to near_y, if it is within `reach` of it (the highest floor
    without near_y). None: nowhere there, a wall for one."""
    return world_of(cells).feet(x, z, near_y, reach)


def reach_of(cells, start, bounds=None):
    """The Reach from `start` (x, y, z) in a scene whose blocks are `cells`."""
    return world_of(cells, bounds).reach(start)


# ---- everything reached from a start ---------------------------------------------------------------
class Reach:
    """Every place a person gets to from `start` (a point (x, y, z), feet at y), and how.

        kind    {node: "walk" | "hop" | "fall" | "trap"}
        steps   {node: lattice steps from the start, the shortest way of that kind}
        void    {node: [(di, dj)]}  the steps off the scene
        jumps   [(from node, to node, rise)]   every jump found
        low     {node: room}        standing places with less than two blocks over the head
        shut    {node: [(di, dj, room)]}  gaps beside the way that only head room closes

    A node is (i, j, feet in 32nds of a block): the lattice point (i / 2, j / 2).
    """

    def __init__(self, world, start, limit=4000000):
        self.world = world
        self.start = world.node(start[0], start[2], start[1], reach=2)
        if self.start is None:
            raise ValueError(f"nobody can stand at or beside {start}")
        self.out, self.void, self.jumps, self.low, self.shut = {}, {}, [], {}, {}
        self.cut, self._sent = False, None
        self._explore(limit)
        self._sort()

    def _explore(self, limit):
        world, out = self.world, self.out
        todo = deque([self.start])
        out[self.start] = None
        while todo:
            node = todo.popleft()
            i, j, hq = node
            h = hq / float(Q)
            edges = []
            for top, room in world.stand(i, j):
                if abs(top - h) < EPS and room < HEAD - EPS:
                    self.low[node] = room
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                kind, land, rise = world.step(i, j, h, di, dj)
                if kind is None:
                    gap = self._low_gap(i + di, j + dj, h)
                    if gap is not None:
                        self.shut.setdefault(node, []).append((di, dj, gap))
                    continue
                if kind == "void":
                    self.void.setdefault(node, []).append((di, dj))
                    continue
                nxt = (i + di, j + dj, int(round(land * Q)))
                edges.append((nxt, kind, rise))
                if kind == "jump":
                    self.jumps.append((node, nxt, rise))
                if nxt not in out:
                    if len(out) >= limit:
                        self.cut = True
                        continue
                    out[nxt] = None
                    todo.append(nxt)
            out[node] = edges

    def _low_gap(self, i, j, h):
        """The room of a gap at the lattice point that a person standing at h beside it could walk
        or hop into but for its head room: lower than a person, at least a crouch."""
        spans = self.world.solid(i, j)
        for n, (_, top) in enumerate(spans):
            if -JUMP - EPS <= top - h <= JUMP + EPS and n + 1 < len(spans):
                room = spans[n + 1][0] - top
                if CROUCH - EPS <= room < HEIGHT - EPS:
                    return room
        return None

    def _flood(self, allow, sources=None, back=None):
        """{node: steps} from the start (or `sources`) along the edges `allow(kind, rise)` lets
        through; with `back` (the reversed edges) the other way."""
        seen = {n: 0 for n in (sources or [self.start])}
        todo = deque(seen)
        while todo:
            node = todo.popleft()
            d = seen[node] + 1
            for nxt, kind, rise in (back.get(node, ()) if back is not None else self.out.get(node) or ()):
                if nxt not in seen and allow(kind, rise):
                    seen[nxt] = d
                    todo.append(nxt)
        return seen

    def _sort(self):
        walk = self._flood(lambda kind, rise: kind == "walk")
        hop = self._flood(lambda kind, rise: kind in ("walk", "jump") or (kind == "drop" and -rise <= JUMP + EPS))
        every = self._flood(lambda kind, rise: True)
        back = {}
        for node, edges in self.out.items():
            for nxt, kind, rise in edges or ():
                back.setdefault(nxt, []).append((node, kind, rise))
        home = self._flood(lambda kind, rise: True, back=back)
        self.back = back
        self.kind, self.steps = {}, {}
        for node in self.out:
            if node in walk:
                self.kind[node], self.steps[node] = "walk", walk[node]
            elif node in hop:
                self.kind[node], self.steps[node] = "hop", hop[node]
            elif node in home:
                self.kind[node], self.steps[node] = "fall", every[node]
            else:
                self.kind[node], self.steps[node] = "trap", every[node]

    def sent(self):
        """The nodes on a block that sends a visitor home (the world's `home`)."""
        if self._sent is None:
            self._sent = {n for n in self.kind if self.world.sends_home(n[0], n[1], n[2] / float(Q))}
        return self._sent

    def stuck(self, line):
        """The trapped places from which there is no way on to where a visitor is sent home from
        (feet under `line`, None: no such line; a block of the world's `home` under them) nor off
        the scene: whoever gets there stays there. These are the places those rules never see."""
        low = list(self.void) + list(self.sent())
        if line is not None:
            low += [n for n in self.kind if n[2] < int(round(line * Q))]
        if not low:
            return {n for n, k in self.kind.items() if k == "trap"}
        down = self._flood(lambda kind, rise: True, sources=low, back=self.back)
        return {n for n, k in self.kind.items() if k == "trap" and n not in down}

    # -- asking -----------------------------------------------------------------------------------------
    def node_at(self, x, z, near_y=None, reach=1):
        """The node reached that is at or next to the point; None: none."""
        i0, j0 = self.world.lattice(x, z)
        best = None
        for i in range(i0 - reach, i0 + reach + 1):
            for j in range(j0 - reach, j0 + reach + 1):
                for top, _ in self.world.stand(i, j):
                    node = (i, j, int(round(top * Q)))
                    if node not in self.kind:
                        continue
                    off = (max(abs(i - i0), abs(j - j0)), abs(top - near_y) if near_y is not None else -top)
                    if best is None or off < best[0]:
                        best = (off, node)
        return best[1] if best else None

    def kind_at(self, x, z, near_y=None, reach=1):
        node = self.node_at(x, z, near_y, reach)
        return self.kind[node] if node else None

    def path(self, to, kinds=("walk", "jump", "drop")):
        """The shortest way from the start to the point `to` (x, y, z) along steps of these kinds: a
        list of points (x, feet, z), one a lattice step; None: no such way."""
        goal = self.node_at(to[0], to[2], to[1], reach=2)
        if goal is None:
            return None
        return self.way(self.start, goal, kinds)

    def way(self, a, b, kinds=("walk", "jump", "drop"), drop=None):
        """The shortest way between two nodes along steps of these kinds (no drop deeper than `drop`
        when that is given), as points; None: none."""
        seen, todo = {a: None}, deque([a])
        while todo:
            node = todo.popleft()
            if node == b:
                out = []
                while node is not None:
                    out.append(point(node))
                    node = seen[node]
                return out[::-1]
            for nxt, kind, rise in self.out.get(node) or ():
                if nxt not in seen and kind in kinds and not (drop is not None and kind == "drop" and -rise > drop + EPS):
                    seen[nxt] = node
                    todo.append(nxt)
        return None

    # -- gathering what was found ---------------------------------------------------------------------
    def pieces(self, nodes):
        """The nodes in connected pieces (joined by any step either way), the largest first."""
        nodes = set(nodes)
        beside = {}
        for node in nodes:
            for nxt, _, _ in self.out.get(node) or ():
                if nxt in nodes:
                    beside.setdefault(node, []).append(nxt)
                    beside.setdefault(nxt, []).append(node)
        out, seen = [], set()
        for node in sorted(nodes):
            if node in seen:
                continue
            piece, todo = [], [node]
            seen.add(node)
            while todo:
                n = todo.pop()
                piece.append(n)
                for m in beside.get(n, ()):
                    if m not in seen:
                        seen.add(m)
                        todo.append(m)
            out.append(piece)
        out.sort(key=len, reverse=True)
        return out

    def stands_on(self, nodes, most=4):
        """{block name: nodes} of what is under the middle of the feet at these nodes, the commonest
        first."""
        tally = {}
        for n in nodes:
            for name in set(self.world.under(n[0], n[1], n[2] / float(Q))):
                tally[name] = tally.get(name, 0) + 1
        return dict(sorted(tally.items(), key=lambda kv: -kv[1])[:most])

    def report(self, points=None, least=12, line=None):
        """What was found, as plain data (reach.json). points: {name: (x, y, z)} to look up. A piece
        of fewer than `least` nodes (three square blocks) is counted, not listed. line: the height
        under which a fallen visitor is sent home (None: there is no such line); the blocks that
        send him home are the world's."""
        world = self.world
        count = {k: 0 for k in KINDS}
        for kind in self.kind.values():
            count[kind] += 1
        out = {
            "start": box_of([self.start])["at"],
            "nodes": count,
            "ground": {k: round(v * GRID * GRID, 1) for k, v in count.items()},       # square blocks
            "cut short": self.cut,
            "lowest block": world.ymin,
            "climbable blocks (not climbed here)": world.climbs,
            "joins worked out as the game does": world.completed,
            "shapes guessed as whole cubes": dict(sorted(world.census["guess"].items(), key=lambda kv: -kv[1])),
            "shapes written down": dict(sorted(world.census["shape"].items(), key=lambda kv: -kv[1])),
            "no collision": dict(sorted(world.census["none"].items(), key=lambda kv: -kv[1])),
        }
        # traps, each with where one falls in and the lowest rise that would let one out
        traps = []
        trapped = [n for n, k in self.kind.items() if k == "trap"]
        into = {}
        for node, edges in self.out.items():
            if self.kind[node] == "trap":
                continue
            for nxt, kind, rise in edges or ():
                if self.kind[nxt] == "trap":
                    into.setdefault(nxt, []).append((node, rise))
        order = {k: n for n, k in enumerate(KINDS)}
        for piece in self.pieces(trapped):
            drops = {}
            for n in piece:
                for src, rise in into.get(n, ()):
                    drops[src] = min(drops.get(src, math.inf), -rise)
            row = box_of(piece)
            # the stretches of edge one falls in from: the visitor's own way first, then the longest
            rims = [dict(box_of(rim), kinds=sorted({self.kind[n] for n in rim}, key=order.get),
                         drop=[round(min(drops[n] for n in rim), 2), round(max(drops[n] for n in rim), 2)])
                    for rim in self.pieces_by_kind(drops)]
            rims.sort(key=lambda r: (order[r["kinds"][0]], -r["nodes"]))
            row["falls in from"] = rims
            row["edges in"] = len(rims)
            row["ways in"] = len(drops)
            row["rise to get out"] = self._way_out(piece)
            row["stands on"] = self.stands_on(piece)
            traps.append(row)
        self.rim = {src for node in into for src, _ in into[node]}
        traps.sort(key=lambda t: (min([order[k] for r in t["falls in from"] for k in r["kinds"][:1]] or [9]), -t["nodes"]))
        out["traps"] = traps
        # the trap ground by height, and the part of it nothing leads down from
        bands = {}
        for n in trapped:
            band = int(math.floor(n[2] / float(Q) / 2.0)) * 2
            bands[band] = bands.get(band, 0) + 1
        out["trap ground by height (square blocks in each two blocks of height, from the top)"] = {
            f"{b}..{b + 2}": round(v * GRID * GRID, 1) for b, v in sorted(bands.items(), reverse=True)}
        legit = [n[2] / float(Q) for n, k in self.kind.items() if k in ("walk", "hop")]
        out["lowest feet on walk or hop ground"] = round(min(legit), 2) if legit else None
        self.fast = self.stuck(line) if line is not None or world.home else set(trapped)
        out["line"] = line
        sent = {}
        for n in self.sent():
            sent[self.kind[n]] = sent.get(self.kind[n], 0) + 1
        out["blocks that send home"] = sorted(world.home)
        out["ground on those blocks"] = {k: round(sent[k] * GRID * GRID, 1) for k in KINDS if k in sent}
        fast = []
        for piece in self.pieces(self.fast):
            row = box_of(piece)
            drops, slides = {}, 0
            for n in piece:
                for src, rise in into.get(n, ()):
                    drops[src] = min(drops.get(src, math.inf), -rise)
                slides += len([1 for src, _, _ in self.back.get(n, ()) if self.kind[src] == "trap" and src not in self.fast])
            row["falls in from"] = sorted(
                [dict(box_of(rim), kinds=sorted({self.kind[n] for n in rim}, key=order.get),
                      drop=[round(min(drops[n] for n in rim), 2), round(max(drops[n] for n in rim), 2)])
                 for rim in self.pieces_by_kind(drops)], key=lambda r: (order[r["kinds"][0]], -r["nodes"]))
            row["ways in from trap ground that is not stuck"] = slides
            row["rise to get out"] = self._way_out(piece)
            row["stands on"] = self.stands_on(piece)
            fast.append(row)
        fast.sort(key=lambda t: (0 if t["falls in from"] else 1, -t["nodes"]))
        out["stuck (no way back and no way on to where one is sent home)"] = fast
        out["stuck (no way back and no way down to the line)"] = fast       # its name before the cloud's rule, for who reads it
        # the steps off the scene
        edge = self.pieces_by_kind(self.void)
        out["void"] = [dict(box_of(piece), kinds=sorted({self.kind[n] for n in piece})) for piece in edge
                       if len(piece) >= least]
        out["void not listed (short)"] = len([p for p in edge if len(p) < least])
        # what is reached by hopping only
        hops = []
        first = {}
        for src, dst, rise in self.jumps:
            if self.kind[src] == "walk" and self.kind[dst] == "hop":
                first.setdefault(dst, []).append((src, rise))
        for piece in self.pieces([n for n, k in self.kind.items() if k == "hop"]):
            ways = sorted({(src, rise) for n in piece for src, rise in first.get(n, ())}, key=lambda e: e[1])
            row = box_of(piece)
            row["jumps in"] = [dict(at=box_of([src])["at"], rise=round(rise, 2)) for src, rise in ways[:4]]
            hops.append(row)
        out["hop only"] = [h for h in hops if h["nodes"] >= least]
        out["hop only not listed (small)"] = len(hops) - len(out["hop only"])
        # head room
        low = self.pieces_by_kind({n: r for n, r in self.low.items() if self.kind[n] in ("walk", "hop")})
        out["low head room"] = [dict(box_of(piece), room=round(min(self.low[n] for n in piece), 2)) for piece in low]
        shut = self.pieces_by_kind({n: g for n, g in self.shut.items() if self.kind[n] in ("walk", "hop")})
        out["closed by head room only"] = [dict(box_of(piece), room=round(min(g[2] for n in piece for g in self.shut[n]), 2))
                                           for piece in shut]
        if points:
            named = {}
            for name, (x, y, z) in points.items():
                node = self.node_at(x, z, y, reach=2)
                if node is None:
                    feet = world.feet(x, z, y)
                    named[name] = dict(point=[x, y, z], reached="no",
                                       note="nobody can stand there" if feet is None else f"a person can stand at y {feet:g}, "
                                       f"and nothing leads there")
                    continue
                named[name] = dict(point=[x, y, z], reached=self.kind[node], at=box_of([node])["at"],
                                   blocks=round(self.steps[node] * GRID, 1))
            out["points"] = named
            out["legs"] = self.legs(points)
        return out

    def legs(self, points, slack=0.75):
        """The way from each point to the next, in the order given: the easiest kind of way there is
        ("walk"; "hop" with jumps and short drops; "fall" with any drop; "no"), its length in
        blocks and its line, thinned to the points that keep it within `slack` blocks."""
        tries = (("walk", ("walk",), None), ("hop", ("walk", "jump", "drop"), JUMP), ("fall", ("walk", "jump", "drop"), None))
        out, names = [], list(points)
        for a, b in zip(names, names[1:]):
            na = self.node_at(points[a][0], points[a][2], points[a][1], reach=2)
            nb = self.node_at(points[b][0], points[b][2], points[b][1], reach=2)
            leg = {"from": a, "to": b, "kind": "no"}
            if na is not None and nb is not None:
                for kind, steps, drop in tries:
                    line = self.way(na, nb, steps, drop)
                    if line:
                        leg.update(kind=kind, blocks=round((len(line) - 1) * GRID, 1),
                                   line=[[x, round(y, 2), z] for x, y, z in thin(line, slack)])
                        break
            out.append(leg)
        return out

    def plan(self, box=None):
        """Two plans in characters, a block a character, north on top: how the block's middle is
        reached (W walk, h hop, f fall, T trap, . not at all; the highest place reached counts) and
        how high the feet stand there (0-9 as they are, a-z for -1 to -26, + for more than 9; a half
        block counts with the whole below it)."""
        if box is None:
            xs = [n[0] for n in self.kind]
            zs = [n[1] for n in self.kind]
            box = (min(xs) // 2 - 1, min(zs) // 2 - 1, max(xs) // 2 + 1, max(zs) // 2 + 1)
        x0, z0, x1, z1 = box
        top = {}
        for node in self.kind:
            if node[0] % 2 and node[1] % 2:
                key = (node[0] // 2, node[1] // 2)
                if key not in top or node[2] > top[key][2]:
                    top[key] = node
        mark = {"walk": "W", "hop": "h", "fall": "f", "trap": "T"}
        tens = "      " + "".join((str(abs(x) // 10 % 10) if x % 10 == 0 else " ") for x in range(x0, x1 + 1))
        ones = "      " + "".join(str(abs(x) % 10) for x in range(x0, x1 + 1))

        def level(node):
            y = math.floor(node[2] / float(Q) + EPS)
            return str(y) if 0 <= y <= 9 else "+" if y > 9 else chr(ord("a") - y - 1) if y >= -26 else "-"

        out = [f"== how each block is reached: x {x0}..{x1} left to right (a ruler of tens and ones on top), rows z {z0}..{z1}",
               tens, ones]
        for z in range(z0, z1 + 1):
            out.append(f"{z:5d} " + "".join(mark[self.kind[top[(x, z)]]] if (x, z) in top else "." for x in range(x0, x1 + 1)))
        out += ["", f"== how high the feet stand there (0-9, a-z for -1 to -26, + over 9): x {x0}..{x1}, rows z {z0}..{z1}", tens, ones]
        for z in range(z0, z1 + 1):
            out.append(f"{z:5d} " + "".join(level(top[(x, z)]) if (x, z) in top else "." for x in range(x0, x1 + 1)))
        return out

    def pieces_by_kind(self, marked):
        """Marked nodes in pieces that hang together on the lattice (neighbours on it, whatever the
        height), the largest first."""
        cells = {}
        for node in marked:
            cells.setdefault((node[0], node[1]), []).append(node)
        out, seen = [], set()
        for key in sorted(cells):
            if key in seen:
                continue
            piece, todo = [], [key]
            seen.add(key)
            while todo:
                i, j = todo.pop()
                piece += cells[(i, j)]
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        nxt = (i + di, j + dj)
                        if nxt in cells and nxt not in seen:
                            seen.add(nxt)
                            todo.append(nxt)
            out.append(piece)
        out.sort(key=len, reverse=True)
        return out

    def _way_out(self, piece):
        """The lowest rise from a node of a trap to a standing place beside it that is not trapped:
        how much too high the way out is. None: no such place beside it."""
        best = None
        for i, j, hq in piece:
            h = hq / float(Q)
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for top, _ in self.world.stand(i + di, j + dj):
                    node = (i + di, j + dj, int(round(top * Q)))
                    if self.kind.get(node, "trap") != "trap" and top > h and (best is None or top - h < best):
                        best = top - h
        return None if best is None else round(best, 2)


def thin(line, slack=0.75):
    """A line of points (x, y, z) with only the points kept that hold it within `slack` blocks of
    where it ran (the height counts as a distance too)."""
    if len(line) < 3:
        return list(line)
    keep = [0, len(line) - 1]
    todo = [(0, len(line) - 1)]
    while todo:
        a, b = todo.pop()
        if b - a < 2:
            continue
        pa, pb = line[a], line[b]
        d = [pb[k] - pa[k] for k in range(3)]
        dd = sum(v * v for v in d)
        far, at = 0.0, None
        for n in range(a + 1, b):
            v = [line[n][k] - pa[k] for k in range(3)]
            t = 0.0 if dd < EPS else max(0.0, min(1.0, sum(v[k] * d[k] for k in range(3)) / dd))
            off = math.sqrt(sum((v[k] - t * d[k]) ** 2 for k in range(3)))
            if off > far:
                far, at = off, n
        if at is not None and far > slack:
            keep.append(at)
            todo += [(a, at), (at, b)]
    return [line[n] for n in sorted(set(keep))]


def box_of(nodes):
    """Where a set of nodes lies: how many, a point of it, its box in blocks and its heights."""
    xs = [n[0] * GRID for n in nodes]
    zs = [n[1] * GRID for n in nodes]
    ys = [n[2] / float(Q) for n in nodes]
    mid = min(nodes, key=lambda n: (n[0] * GRID - sum(xs) / len(xs)) ** 2 + (n[1] * GRID - sum(zs) / len(zs)) ** 2)
    return dict(nodes=len(nodes), at=[mid[0] * GRID, round(mid[2] / float(Q), 2), mid[1] * GRID],
                x=[min(xs), max(xs)], z=[min(zs), max(zs)], y=[round(min(ys), 2), round(max(ys), 2)])


# ---- the map -----------------------------------------------------------------------------------------
COLOURS = {"walk": (70, 200, 90), "hop": (235, 205, 60), "fall": (70, 140, 235), "trap": (230, 60, 50)}
VOID = (235, 70, 220)
RIM = (120, 20, 20)
STUCK = (255, 150, 30)


def draw(reach, path, scale=4, grid=10, line=None):
    """A plan of what is reached: one square a lattice point, the highest node at each; green walk,
    yellow hop, blue fall, red trap, lighter the higher; magenta where a step leads off the scene,
    a dark red middle where a step drops into a trap; with a line, orange the trap ground nothing
    leads down to it from. Lines every `grid` blocks, numbered along the top and the left; north
    is up."""
    from PIL import Image, ImageDraw
    rim = getattr(reach, "rim", None)
    if rim is None:
        rim = {n for n, edges in reach.out.items() if reach.kind[n] != "trap"
               and any(reach.kind[nxt] == "trap" for nxt, _, _ in edges or ())}
    fast = getattr(reach, "fast", None)
    if fast is None or (line is None and not reach.world.home):
        fast = set()
    top = {}
    for node in reach.kind:
        key = (node[0], node[1])
        if key not in top or node[2] > top[key][2]:
            top[key] = node
    i0, i1 = min(k[0] for k in top) - 2, max(k[0] for k in top) + 2
    j0, j1 = min(k[1] for k in top) - 2, max(k[1] for k in top) + 2
    lo, hi = min(n[2] for n in top.values()), max(n[2] for n in top.values())
    pad = 28
    img = Image.new("RGB", (pad + (i1 - i0 + 1) * scale, pad + (j1 - j0 + 1) * scale), (16, 18, 24))
    px = img.load()
    for (i, j), node in top.items():
        shade = 0.45 + 0.55 * ((node[2] - lo) / float(max(hi - lo, 1)))
        if reach.kind[node] == "trap":
            shade = 0.8 + 0.2 * shade                   # a trap is seen however low it lies
        colour = VOID if node in reach.void else STUCK if node in fast else tuple(int(c * shade) for c in COLOURS[reach.kind[node]])
        for a in range(scale):
            for b in range(scale):
                px[pad + (i - i0) * scale + a, pad + (j - j0) * scale + b] = colour
        if node in rim and scale >= 3:                  # a step from here drops into a trap
            for a in range(1, scale - 1):
                for b in range(1, scale - 1):
                    px[pad + (i - i0) * scale + a, pad + (j - j0) * scale + b] = RIM
    pen = ImageDraw.Draw(img)
    step = int(round(grid / GRID))
    for i in range(i0, i1 + 1):
        if i % step == 0:
            x = pad + (i - i0) * scale
            pen.line([(x, pad), (x, img.size[1])], fill=(60, 64, 76))
            pen.text((x + 2, 2), str(int(i * GRID)), fill=(200, 200, 210))
    for j in range(j0, j1 + 1):
        if j % step == 0:
            y = pad + (j - j0) * scale
            pen.line([(pad, y), (img.size[0], y)], fill=(60, 64, 76))
            pen.text((2, y + 2), str(int(j * GRID)), fill=(200, 200, 210))
    img.save(path)
    return img.size


# ---- the scene -------------------------------------------------------------------------------------------
def cells_of(scene, canvas=None):
    """The blocks of a scene: read from the pickle build/render.py --canvas keeps, else built (and
    the pickle written when a path is given)."""
    if canvas and os.path.exists(canvas):
        with open(canvas, "rb") as fh:
            return pickle.load(fh)["b"]
    built = importlib.import_module(f"scenes.{scene}").build()
    if canvas:
        with open(canvas, "wb") as fh:
            pickle.dump({"b": built.b, "entities": built.entities}, fh, protocol=4)
    return built.b


def landmarks():
    """The landmarks of the outdoor route (walk.md) in the order it visits them, from the skeleton:
    {name: (x, feet, z)}."""
    from scenes.obs.common import skeleton as S
    house = S.POWER_HOUSE["box"]
    hut = S.MERIDIAN_HUT
    sunset = S.SUNSET_PLATFORM

    def shelf(part):
        box = part["box"]
        return S.mid(box[0], box[2]), part["feet"], S.mid(box[1], box[3])

    return {
        "spawn": (S.V1["pos"][0], S.STATION_GROUND, S.V1["pos"][2]),
        "lower platform, before the stair": (S.GRAND_STAIR["x1"] + 3.5, S.LOWER_GROUND, S.AXIS_Z),
        "stair head": (S.EAST_EDGE_X - 1.5, S.GROUND, S.AXIS_Z),
        "court, on the axis by the armillary": (S.ARMILLARY[0] + 3.5, S.GROUND, S.AXIS_Z),
        "court, south end of the meridian": (S.MERIDIAN_X + 0.5, S.GROUND, S.MERIDIAN_Z[1] - 0.5),
        "court, south-west corner": (S.WALL_E + 4.5, S.GROUND, S.FRONT_COURT[3] - 1.5),
        "before the main door": (S.east_wall_x(9) + 3.5, S.GROUND, S.AXIS_Z),
        "court, north-west corner": (S.WALL_E + 4.5, S.GROUND, S.FRONT_COURT[1] + 2.5),
        "court, north end of the meridian": (S.MERIDIAN_X + 0.5, S.GROUND, hut["door"][1] + 2.5),
        "meridian hut, before its door": (hut["door"][0] + 0.5, S.GROUND, hut["door"][1] + 1.5),
        "mast pad": (S.mid(S.MAST_PAD["box"][0], S.MAST_PAD["box"][2]), S.MAST_PAD["feet"], S.MAST_PAD["box"][3] - 0.5),
        "weather station": shelf(S.WEATHER_STATION),
        "water tower": shelf(S.WATER_TOWER),
        "west side, north": (S.WALL_W - 4.5, S.GROUND, S.Z_NORTH + 10.5),
        "sunset platform, west edge": (sunset["centre"][0] - sunset["radius"] + 2.5, S.GROUND, S.AXIS_Z),
        "west side, south": (S.WALL_W - 4.5, S.GROUND, S.Z_SOUTH - 9.5),
        "south lookout": (S.V11["pos"][0], S.SOUTH_LOOKOUT["feet"], S.V11["pos"][2]),
        "power house, west side": (house[0] - 2.5, S.LOWER_GROUND, S.mid(house[1], house[3])),
        "power house, north side": (S.mid(house[0], house[2]), S.LOWER_GROUND, house[1] - 2.5),
        "lower platform, south-east": (S.LOWER_PLATFORM[2] - 1.5, S.LOWER_GROUND, S.LOWER_PLATFORM[3] - 0.5),
        "back at the spawn": (S.V1["pos"][0], S.STATION_GROUND, S.V1["pos"][2]),
    }


def say(report):
    """The report in a dozen lines."""
    g = report["ground"]
    lines = [f"from {report['start']}: {g['walk']:g} square blocks on foot, {g['hop']:g} more with a jump, "
             f"{g['fall']:g} by falling (and back), {g['trap']:g} with no way back"
             + ("; CUT SHORT, the ground is larger than the limit" if report["cut short"] else "")]
    for t in report["traps"][:12]:
        lines.append(f"  trap: {t['nodes']} nodes at {t['at']}, x {t['x']}, z {t['z']}, y {t['y']}; the least rise "
                     f"out of it is {t['rise to get out']}; {t['ways in']} ways in along {t['edges in']} edges; "
                     f"under the feet: " + ", ".join(f"{k} x{v}" for k, v in t.get("stands on", {}).items()))
        for e in t["falls in from"][:5]:
            lines.append(f"      from {'/'.join(e['kinds'])} ground at {e['at']}, x {e['x']}, z {e['z']}: "
                         f"{e['nodes']} nodes, a drop of {e['drop'][0]:g} to {e['drop'][1]:g}")
    if len(report["traps"]) > 12:
        lines.append(f"  ... and {len(report['traps']) - 12} more traps")
    stuck = report.get("stuck (no way back and no way on to where one is sent home)") or []
    home = report.get("blocks that send home") or []
    if report.get("line") is not None or home:
        rules = ([f"under y {report['line']:g}"] if report.get("line") is not None else []) + (
            [f"standing on {', '.join(home)} ("
             + ", ".join(f"{k} {v:g}" for k, v in report["ground on those blocks"].items()) + " square blocks of it reached)"]
            if home else [])
        lines.append(f"  a visitor {' or '.join(rules)} is sent home; the lowest walk or hop ground is at "
                     f"{report['lowest feet on walk or hop ground']}; trap ground with no way on to that: "
                     f"{sum(t['nodes'] for t in stuck) * GRID * GRID:g} square blocks in {len(stuck)} pieces")
        for t in stuck[:16]:
            ins = "; ".join(f"{'/'.join(e['kinds'])} ground at {e['at']} (drop {e['drop'][0]:g} to {e['drop'][1]:g})"
                            for e in t["falls in from"][:3])
            lines.append(f"      stuck: {t['nodes']} nodes at {t['at']}, x {t['x']}, z {t['z']}, y {t['y']}, on "
                         + ", ".join(t.get("stands on", {})) + f"; out is {t['rise to get out']} up; from "
                         + (ins or "trap ground only")
                         + (f"; and {t['ways in from trap ground that is not stuck']} ways from the slope"
                            if t["ways in from trap ground that is not stuck"] else ""))
        if len(stuck) > 16:
            lines.append(f"      ... and {len(stuck) - 16} more")
    for v in report["void"][:8]:
        lines.append(f"  off the scene: {v['nodes']} nodes at {v['at']}, x {v['x']}, z {v['z']} ({', '.join(v['kinds'])})")
    for h in report["hop only"][:12]:
        ins = "; ".join(f"{e['at']} (rise {e['rise']:g})" for e in h["jumps in"][:2])
        lines.append(f"  by a jump only: {h['nodes']} nodes at {h['at']}, x {h['x']}, z {h['z']}, y {h['y']}; from {ins}")
    for row in report["low head room"][:8]:
        lines.append(f"  head room {row['room']:g}: {row['nodes']} nodes at {row['at']}, x {row['x']}, z {row['z']}")
    for row in report["closed by head room only"][:8]:
        lines.append(f"  a gap of {row['room']:g} closes the way: beside {row['at']}, x {row['x']}, z {row['z']}")
    for name, p in (report.get("points") or {}).items():
        lines.append(f"  {name}: " + (f"{p['reached']}, {p['blocks']:g} blocks from the start, at {p['at']}"
                                      if p["reached"] != "no" else f"NOT REACHED ({p['note']})"))
    for leg in report.get("legs") or ():
        lines.append(f"  {leg['from']} -> {leg['to']}: " + ("NO WAY" if leg["kind"] == "no" else
                     f"{leg['kind']}, {leg['blocks']:g} blocks"))
    if report["joins worked out as the game does"] != "yes":
        lines.append("  THE JOINS OF BARS, PANES, WALLS AND FENCES WERE NOT WORKED OUT: "
                     + report["joins worked out as the game does"])
    guess = report["shapes guessed as whole cubes"]
    if guess:
        lines.append("  taken as whole cubes without a rule: " + ", ".join(f"{k} x{v}" for k, v in list(guess.items())[:20]))
    if report["climbable blocks (not climbed here)"]:
        lines.append(f"  {report['climbable blocks (not climbed here)']} ladder, vine or scaffolding blocks: not climbed here")
    return "\n".join(lines)


# ---- the arithmetic, on worlds built by hand --------------------------------------------------------------
def selftest():
    def floor(x0, z0, x1, z1, y=-1, block="stone"):
        return {(x, y, z): block for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}

    def passage(length):
        """A way one block wide along x in the row z = 0, between walls three high."""
        cells = floor(0, 0, length, 0)
        cells.update({(x, y, z): "stone" for x in range(0, length + 1) for y in (0, 1, 2) for z in (-1, 1)})
        return cells

    def kinds(cells, start=(0.5, 0.0, 0.5), **kw):
        reach = World(cells, **kw).reach(start)
        return reach, lambda x, z, y=None: reach.kind_at(x, z, y, reach=0)

    bad = []

    def check(name, got, want):
        if got != want:
            bad.append(f"{name}: got {got!r}, wanted {want!r}")

    # a flat floor: all of it on foot; a person's middle can hang 0.3 over the rim, not half a block
    reach, at = kinds(floor(0, 0, 5, 5))
    check("flat floor", {reach.kind[n] for n in reach.kind}, {"walk"})
    check("flat floor, nodes", len(reach.kind), 13 * 13)
    check("flat floor, rim", len(reach.void), 48)
    # a block on the floor: its top by a jump; two blocks: not at all
    cells = floor(0, 0, 8, 2)
    cells[(3, 0, 1)] = cells[(6, 0, 1)] = cells[(6, 1, 1)] = "stone"
    reach, at = kinds(cells)
    check("one block up", at(3.5, 1.5, 1.0), "hop")
    check("two blocks up", at(6.5, 1.5, 2.0), None)
    # half a block at a time is walked: a slab before a block, a stair before a block
    for low in ("stone_slab[type=bottom]", "stone_stairs[facing=east,half=bottom]"):
        cells = passage(8)
        cells[(2, 0, 0)] = low
        cells.update({(x, 0, 0): "stone" for x in range(3, 9)})
        reach, at = kinds(cells)
        check(f"up by {low}", at(5.5, 0.5, 1.0), "walk")
    cells = passage(8)
    cells.update({(x, 0, 0): "stone" for x in range(3, 9)})
    reach, at = kinds(cells)
    check("up a whole block", at(5.5, 0.5, 1.0), "hop")
    # a wall and a fence are 1.5 to a person; bars and a pane are 1.0 and are jumped
    for block, want in (("sandstone_wall[north=low,south=low]", None), ("sandstone_wall", None),
                        ("bamboo_fence[north=true,south=true]", None),
                        ("oxidized_copper_bars[north=true,south=true]", "hop"),
                        ("gray_stained_glass_pane[north=true,south=true]", "hop"),
                        ("oxidized_copper_chain[axis=z]", "walk"), ("oxidized_copper_chain[axis=y]", "hop"),
                        ("yellow_carpet", "walk"), ("rail[shape=east_west]", "walk"), ("light[level=12]", "walk"),
                        ("snow[layers=3]", "walk"), ("oxidized_copper_lantern", "walk"),
                        ("oxidized_copper_lantern[hanging=true]", "hop")):
        cells = passage(6)
        cells[(3, 0, 0)] = block
        reach, at = kinds(cells)
        check(f"beyond {block}", at(5.5, 0.5, 0.0), want)
    # a railing as the scenes write it, without its joins: bars from wall to wall, and the same
    # with a pier in the middle. The joins are worked out first, so nobody walks between two posts
    for middle in ("oxidized_copper_bars", "sandstone_wall"):
        cells = floor(0, 0, 8, 2)
        cells.update({(x, y, z): "stone" for x in range(0, 9) for y in (0, 1, 2) for z in (-1, 3)})
        cells.update({(4, 0, 0): "oxidized_copper_bars", (4, 0, 1): middle, (4, 0, 2): "oxidized_copper_bars"})
        world = World(cells)
        check("joins worked out", world.completed, "yes")
        reach = world.reach((0.5, 0.0, 0.5))
        check(f"beyond a railing written without its joins ({middle})", reach.kind_at(6.5, 1.5, 0.0, reach=0), "hop")
        check(f"on the railing's middle ({middle})", reach.kind_at(4.5, 1.5, 1.5 if middle.endswith("wall") else 1.0, reach=0), "hop")
        check("the blocks handed in are left as they were", cells[(4, 0, 0)], "oxidized_copper_bars")
    # two bars high is a wall again
    cells = passage(6)
    cells[(3, 0, 0)] = cells[(3, 1, 0)] = "oxidized_copper_bars[north=true,south=true]"
    reach, at = kinds(cells)
    check("beyond two bars", at(5.5, 0.5, 0.0), None)
    # a door, a gate, a hatch: shut they close the way, open they do not
    for block, want in (("oxidized_copper_door[facing=east,half=lower,open=false]", None),
                        ("oxidized_copper_door[facing=east,half=lower,open=true]", "walk"),
                        ("oxidized_copper_door[facing=north,half=lower,open=false]", "walk"),
                        ("bamboo_fence_gate[facing=east,open=false]", None),
                        ("bamboo_fence_gate[facing=east,open=true]", "walk"),
                        ("oxidized_copper_trapdoor[facing=east,half=bottom,open=true]", None),
                        ("oxidized_copper_trapdoor[facing=east,half=bottom,open=false]", "walk")):
        cells = passage(6)
        cells[(3, 0, 0)] = block
        if "_door[" in block:
            cells[(3, 1, 0)] = block.replace("half=lower", "half=upper")
        elif "open=true" in block and "_trapdoor[" in block:
            cells[(3, 1, 0)] = block
        reach, at = kinds(cells)
        check(f"through {block}", at(5.5, 0.5, 0.0), want)
    # a pit two deep across part of the floor: a trap; with a block to climb on in it one hops in and out
    cells = floor(0, 0, 8, 2)
    for x in (4, 5):
        for z in (0, 1):
            del cells[(x, -1, z)]
            cells[(x, -3, z)] = "stone"
    reach, at = kinds(cells)
    check("pit", at(4.5, 0.5, -2.0), "trap")
    check("pit, the far side", at(7.5, 0.5, 0.0), "walk")
    check("pit, the way out", reach.report()["traps"][0]["rise to get out"], 2.0)
    cells[(4, -2, 1)] = "stone"
    reach, at = kinds(cells)
    check("pit with a step", at(5.5, 0.5, -2.0), "hop")
    # who is sent home is not stuck: under the line, or on a block of the cloud; in a pit of stone over the line one is
    key = "stuck (no way back and no way on to where one is sent home)"
    cells = floor(0, 0, 8, 4)
    for x in (4, 5):
        for z in (1, 2):
            del cells[(x, -1, z)]
            cells[(x, -3, z)] = "stone"
    reach, at = kinds(cells)
    check("pit off the rim", at(4.5, 1.5, -2.0), "trap")
    check("pit off the rim, no rule", [t["nodes"] for t in reach.report()[key]], [9])
    check("pit off the rim, the line at its floor", [t["nodes"] for t in reach.report(line=-2.0)[key]], [9])
    check("pit off the rim, the line over its floor", reach.report(line=-1.5)[key], [])
    for x in (4, 5):
        cells[(x, -3, 2)] = "minecraft:dead_horn_coral_block"
    reach, at = kinds(cells, home=("dead_horn_coral_block",))
    check("pit with cloud in it", at(4.5, 1.5, -2.0), "trap")
    check("pit with cloud in it, on the cloud", reach.world.sends_home(9, 5, -2.0), True)
    check("pit with cloud in it, on the joint", reach.world.sends_home(9, 4, -2.0), False)
    check("pit with cloud in it, stuck", reach.report()[key], [])
    check("pit with cloud in it, what is under", reach.report()["traps"][0]["stands on"],
          {"stone": 6, "dead_horn_coral_block": 6})
    cells.update(floor(4, 1, 5, 2, y=-3))
    cells[(8, -1, 4)] = "dead_horn_coral_block"
    reach, at = kinds(cells, home=("dead_horn_coral_block",))
    check("pit of stone, cloud elsewhere", [t["nodes"] for t in reach.report()[key]], [9])
    # a ledge half way down a drop of six: reached by falling only, and on down to the ground one came from
    cells = floor(0, 0, 14, 1)
    for x in range(0, 12):                              # a ramp of half blocks in the row z = 2, up to 6
        top = 0.5 * (x + 1)
        cells.update({(x, y, 2): "stone" for y in range(-1, int(top))})
        if top != int(top):
            cells[(x, int(top), 2)] = "stone_slab[type=bottom]"
    cells.update({(x, 5, z): "stone" for x in (12, 13, 14) for z in (0, 1, 2)})       # the platform at 6
    cells.update({(11, 2, z): "stone" for z in (0, 1)})                               # the ledge at 3
    reach, at = kinds(cells)
    check("platform up the ramp", at(13.5, 0.5, 6.0), "walk")
    check("ledge under it", at(11.5, 0.5, 3.0), "fall")
    # head room: 1.5 closes the way and is named; 1.81 lets a person through and is named
    cells = passage(6)
    cells[(3, 1, 0)] = "stone_slab[type=top]"
    reach, at = kinds(cells)
    check("under a slab at 1.5", at(5.5, 0.5, 0.0), None)
    check("under a slab at 1.5, named", bool(reach.shut), True)
    cells[(3, 1, 0)] = "oxidized_copper_trapdoor[half=top,open=false]"
    reach, at = kinds(cells)
    check("under a hatch at 1.81", at(5.5, 0.5, 0.0), "walk")
    check("under a hatch at 1.81, named", bool(reach.low), True)
    # the feet, the way, and the two functions that take the blocks themselves
    cells = floor(0, 0, 8, 0)
    cells[(4, 0, 0)] = "stone_slab[type=bottom]"
    world = World(cells)
    check("feet on a slab", world.feet(4.5, 0.5), 0.5)
    check("feet beside it", world.feet(2.5, 0.5, 0.0), 0.0)
    check("feet over nothing", world.feet(20.5, 0.5), None)
    way = world.reach((0.5, 0.0, 0.5)).path((8.5, 0.0, 0.5), kinds=("walk",))
    check("way", (way[0], way[-1], len(way)), ((0.5, 0.0, 0.5), (8.5, 0.0, 0.5), 17))
    check("feet off the lattice", world.feet(3.75, 0.5, 0.0), 0.5)         # 3.45 .. 4.05 touches the slab
    check("feet off the lattice, clear of it", world.feet(3.65, 0.5, 0.0), 0.0)
    check("feet()", feet(cells, 4.5, 0.5), 0.5)
    check("feet(), too far from the level asked for", feet(cells, 2.5, 0.5, 3.0), None)
    check("reach()", reach_of(cells, (0.5, 0.0, 0.5)).kind_at(8.5, 0.5, 0.0), "walk")
    for line in bad:
        print("FAIL " + line)
    print(f"walkreach selftest: {'FAIL' if bad else 'PASS'} ({len(bad)} wrong)")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="where a visitor gets to on foot, from the scene's blocks")
    ap.add_argument("scene", nargs="?", default="obs")
    ap.add_argument("--canvas", help="pickle of the built scene (build/render.py --canvas): read if there, else written")
    ap.add_argument("--out", help="folder for reach.json, reach.txt and reach.png")
    ap.add_argument("--name", default="reach", help="the files' name instead of `reach` (a second start: --name reach-court)")
    ap.add_argument("--start", help="x,y,z of the feet, or the name of a landmark (default: the spawn, V1's place on "
                                    "the station platform)")
    ap.add_argument("--points", help="JSON file {name: [x, y, z]} of points to look up besides the route's landmarks")
    ap.add_argument("--bounds", help="x0,z0,x1,z1 of the ground looked at (default: the skeleton's masses and 40 more)")
    ap.add_argument("--scale", type=int, default=4, help="pixels a lattice point on the map")
    ap.add_argument("--line", help=f"a visitor whose feet are under this height is sent home (default: {CATCH:g}, "
                                   "common/export's; 'none': no such line)")
    ap.add_argument("--home", help="the blocks that send a visitor home who stands on them, names with commas "
                                   "(default: the cloud sea's, the block table's CLOUD; 'none': none do)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    from scenes.obs.common import skeleton as S
    points = landmarks()
    if args.points:
        with open(args.points, encoding="utf-8") as fh:
            points.update({k: tuple(v) for k, v in json.load(fh).items()})
    if not args.start:
        start = points["spawn"]
    elif args.start in points:
        start = points[args.start]
    else:
        start = tuple(float(v) for v in args.start.split(","))
    if args.bounds:
        bounds = tuple(int(v) for v in args.bounds.split(","))
    else:
        m = S.mass_bounds()
        bounds = (m[0] - 40, m[2] - 40, m[3] + 40, m[5] + 40)
    cells = cells_of(args.scene, args.canvas)
    if args.home is None:
        home = home_blocks()
    else:
        home = () if args.home == "none" else tuple(v.strip() for v in args.home.split(",") if v.strip())
    world = World(cells, bounds, home)
    reach = world.reach(start)
    line = CATCH if args.line is None else None if args.line == "none" else float(args.line)
    report = reach.report(points, line=line)
    report["scene"], report["bounds"] = args.scene, list(bounds)
    print(say(report))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        stem = os.path.join(args.out, args.name)
        with open(stem + ".json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        with open(stem + ".txt", "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(reach.plan()) + "\n")
        size = draw(reach, stem + ".png", args.scale, line=line)
        print(f"written: {stem}.json, .txt, .png ({size[0]}x{size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

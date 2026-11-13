"""What the game works out from the neighbours when a block is placed: which way fences, walls and
panes join, where stairs turn a corner.

Scenes leave these properties out and the game fills them in when the structure is placed. For a
picture made without the game they have to be worked out here, by the game's own rules
(FenceBlock, WallBlock, IronBarsBlock, StairBlock).
"""
from . import blocks as B

SIDES = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}
LEFT = {"north": "west", "west": "south", "south": "east", "east": "north"}      # counter-clockwise
NEVER_JOINED = ("barrier", "carved_pumpkin", "jack_o_lantern", "melon", "pumpkin")
POST_OVERRIDE = ("torch", "soul_torch", "redstone_torch", "copper_torch", "cactus_flower")


def full(state):
    """(name, props) with every property the block has, defaults filled in."""
    name, props = B.parse(state)
    entry = B.TABLE[name]
    if not entry:
        return name, {}
    out = dict(entry[1])
    out.update(props)
    return name, out


def text(name, props):
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def _kind(name):
    if name.endswith("_stairs"):
        return "stairs"
    if name.endswith("_fence"):
        return "fence"
    if name.endswith("_wall"):
        return "wall"
    if name.endswith("glass_pane") or name == "iron_bars" or name.endswith("copper_bars"):
        return "pane"
    if name.endswith("_fence_gate"):
        return "gate"
    return None


class Shaper:
    def __init__(self, cells, is_cube):
        """cells: {(x, y, z): state}; is_cube(state) says whether a block fills its whole cell."""
        self.cells = cells
        self.is_cube = is_cube
        self._full = {}

    def at(self, p):
        s = self.cells.get(p)
        if s is None:
            return None, None
        hit = self._full.get(s)
        if hit is None:
            hit = self._full[s] = full(s)
        return hit

    def sturdy(self, p, side):
        """Is the face of the block at p that looks towards `side` a whole square?"""
        name, props = self.at(p)
        if name is None:
            return False
        if name.endswith("_leaves") or name in NEVER_JOINED or name.endswith("shulker_box"):
            return False
        if name.endswith("_slab"):
            return props["type"] == "double" or (side == "up" and props["type"] == "top") or (side == "down" and props["type"] == "bottom")
        if name.endswith("_stairs"):
            return side == props["facing"] or (side == "down" and props["half"] == "bottom") or (side == "up" and props["half"] == "top")
        return self.is_cube(self.cells[p])

    def _gate_joins(self, props, side):
        return (props["facing"] in ("north", "south")) == (side in ("west", "east"))

    def joins(self, kind, name, p, side):
        d = SIDES[side]
        q = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
        other, props = self.at(q)
        if other is None:
            return False
        ok = _kind(other)
        solid = self.sturdy(q, OPPOSITE[side])
        if kind == "fence":
            same = ok == "fence" and (other == name or ("nether_brick" not in other and "nether_brick" not in name))
            return same or solid or (ok == "gate" and self._gate_joins(props, side))
        if kind == "pane":
            return solid or ok in ("pane", "wall")
        return solid or ok in ("wall", "pane") or (ok == "gate" and self._gate_joins(props, side))

    def stairs(self, p, props):
        facing, half = props["facing"], props["half"]

        def stair(side):
            d = SIDES[side]
            name, pr = self.at((p[0] + d[0], p[1] + d[1], p[2] + d[2]))
            return pr if name is not None and name.endswith("_stairs") else None

        def can_take(side):
            pr = stair(side)
            return pr is None or pr["facing"] != facing or pr["half"] != half

        across = facing in ("north", "south")
        front = stair(facing)
        if front and front["half"] == half and (front["facing"] in ("north", "south")) != across and can_take(OPPOSITE[front["facing"]]):
            return "outer_left" if front["facing"] == LEFT[facing] else "outer_right"
        back = stair(OPPOSITE[facing])
        if back and back["half"] == half and (back["facing"] in ("north", "south")) != across and can_take(back["facing"]):
            return "inner_left" if back["facing"] == LEFT[facing] else "inner_right"
        return "straight"

    def wall(self, name, p):
        above = (p[0], p[1] + 1, p[2])
        up_name, up_props = self.at(above)
        covered = up_name is not None and self.sturdy(above, "down")
        out = {}
        for side in SIDES:
            if not self.joins("wall", name, p, side):
                out[side] = "none"
                continue
            tall = covered
            if not tall and up_name is not None:
                kind = _kind(up_name)
                tall = (kind == "wall" and up_props.get(side, "none") != "none") or (kind in ("fence", "pane") and up_props.get(side) == "true")
            out[side] = "tall" if tall else "low"
        n, s, w, e = (out[k] == "none" for k in ("north", "south", "west", "east"))
        if up_name is not None and _kind(up_name) == "wall" and up_props.get("up") == "true":
            post = True
        elif (n and s and w and e) or n != s or w != e:
            post = True
        elif (out["north"] == "tall" and out["south"] == "tall") or (out["west"] == "tall" and out["east"] == "tall"):
            post = False
        else:
            post = up_name is not None and (up_name in POST_OVERRIDE or covered or up_name.endswith("lantern")
                                            or _kind(up_name) in ("fence", "pane") or up_name.endswith(("_sign", "_banner", "pressure_plate")))
        out["up"] = "true" if post else "false"
        return out

    def run(self):
        """{position: completed state} for every block whose look depends on its neighbours.
        Walls are done from the top down, since a wall looks at the wall above it."""
        todo = [(p, s) for p, s in self.cells.items() if _kind(s.partition("[")[0])]
        todo.sort(key=lambda t: -t[0][1])
        out = {}
        for p, s in todo:
            name, props = self.at(p)
            kind = _kind(name)
            new = dict(props)
            if kind == "stairs":
                new["shape"] = self.stairs(p, props)
            elif kind in ("fence", "pane"):
                for side in SIDES:
                    new[side] = "true" if self.joins(kind, name, p, side) else "false"
            elif kind == "wall":
                new.update(self.wall(name, p))
            elif kind == "gate":
                a, b = ("west", "east") if props["facing"] in ("north", "south") else ("north", "south")
                near = [self.at((p[0] + SIDES[k][0], p[1], p[2] + SIDES[k][2]))[0] for k in (a, b)]
                new["in_wall"] = "true" if any(n is not None and n.endswith("_wall") for n in near) else "false"
            if new != props:
                state = text(name, new)
                out[p] = state
                self.cells[p] = state
                self._full[state] = (name, new)
        return out

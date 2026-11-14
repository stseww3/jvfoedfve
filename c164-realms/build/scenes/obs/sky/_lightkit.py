"""The light kit of the sky line: which windows are lit, and where a light source may stand
(plan/parts/sky.md 6; card plan/packages/sky/lights.md).

A lamp, a lit window, an open door only glow themselves. The light they throw is an invisible light
block (B.LIGHT), and every one of those is placed by sky/lights.py, which runs after all the other
lines. Those call this module and nothing else of the light:

    from scenes.obs.sky import _lightkit as L

    tier, role = L.window_lit("east", 5, "main")        # the glass of a window: role.block, role.pane
    L.suggest(canvas, (x, y, z), 12, "props/lamps:bracket_a")       # a light source someone would like
    L.take(canvas, [((x, y, z), 12), ...], "props/lamps:festoon")   # several of them
    L.glazed(canvas, windows, origin)       # the windows of a front that main's table does not list

Ranks: the levels of the invisible sources. 15 is never used: light of 15 is nine parts white and 13
is half white already.

    1   13-14   the open main door 14, canopy bulbs 13, street and stair lamps 14, the platform 13
    2    9-12   behind a lit window 9-10 (12 behind the one over the main door), the bracket lamps
                beside a door 12
    3    5-8    wall wash 8, walkways 5-7, beside machines 6-8, fill for a caged lamp 6-7

Light falls by one a cell, and a face is lit by the cell in front of it. A source of level n in the
first cell behind the glass leaves n-3 on the jambs, n-2 to n-3 on the sill, n-4 on the sides of the
pilasters and n-6 on their fronts. Under the blue look stone is lifted out of the blue to a neutral
grey at 7 and turns warm from 9 on: 10 behind the glass makes a window's surround lighter, 12 makes
it warm.

Windows (the director's rules, group #15317): at least a fifth of the windows of a front are dark;
two neighbouring bays of one storey are never both lit; lit windows come in tiers and the brightest
is kept for the entrance; a front must not turn warm all over.

    tier 0  dark     B.WINDOW_DARK, now and then B.WINDOW_BLIND          no light behind it
    tier 1  dim      B.WINDOW_CURTAIN, a lamp behind a drawn curtain      may stand next to a lit one
    tier 2  lit      B.WINDOW_FROSTED
    tier 3  bright   B.WINDOW_LIT, the entrance only

The tier of a window follows from its name (front, bay, storey) and a seed, never from the order of
building, so a front comes out the same every time. `front`, `bay` and `storey` are the keys of
main's table of windows (scenes.obs.main._plan.windows()): "east" bays 1 to 17 from the north, "base"
and "main". The plain names of the fronts belong to the main building; another building puts its
name in front ("power.east"), and its windows get a pattern of their own.

The three looks light different shares of the same windows. Windows are blocks and do not change
with the time, so a scene is built for one look: "blue" lights the most, "glow" fewer, "deep" the
entrance, the foot of the tower and a few more. A window that is lit in a sparser look is lit in the
fuller ones as well.
"""
import functools
import math
import zlib

from artkit import blockfacts as F
from artkit import blocks as AB
from artkit.canvas import hash3

from ..common import blocks as B
from . import mood

# ---- ranks ---------------------------------------------------------------------------------------------
RANKS = {1: (13, 14), 2: (9, 12), 3: (5, 8)}
TOP = 14                    # the brightest source there is; 15 is never used
REACH = 2                   # a source stands within this many cells of something that glows
REACH_UP = 6                # ... or of a model whose anchor is this far below or above: a street lamp's
#                             head is four blocks over its foot, a pendant hangs under its rose


# The rank of the lamps of props/lamps, by the name they register their source with. A source that
# asks for more than the top of its rank is cut down to it: a caged lamp never lights like a street
# lamp. A festoon is rank 1 for the bulbs under the entrance canopy (13); elsewhere it keeps to 12.
KIND_RANK = {"street": 1, "festoon": 1, "bracket": 2, "pendant": 2, "cage": 3, "desk_green": 3, "uplight": 3}


def rank(level):
    """The rank a level belongs to: 1 for 13-14, 2 for 9-12, 3 below."""
    return 1 if level >= RANKS[1][0] else 2 if level >= RANKS[2][0] else 3


def kind_rank(why):
    """The rank of a source by what throws it ("props/lamps:bracket_a" is a bracket lamp: 2), or
    None when the name says nothing."""
    kind = str(why).rpartition(":")[2]
    for end in ("_a", "_b"):
        if kind.endswith(end):
            kind = kind[:-len(end)]
    return KIND_RANK.get(kind)


def light(level):
    """The block state of an invisible source."""
    if not 1 <= int(level) <= TOP:
        raise ValueError(f"a light source is of level 1 to {TOP}, not {level}")
    return f"{B.LIGHT}[level={int(level)}]"


# ---- windows -------------------------------------------------------------------------------------------
DARK, DIM, LIT, BRIGHT = range(4)
TIER_NAMES = ("dark", "dim", "lit", "bright")
ROLE = {BRIGHT: B.WINDOW_LIT, LIT: B.WINDOW_FROSTED, DIM: B.WINDOW_CURTAIN}
BLIND_SHARE = 0.3           # of the dark windows, how many show a lowered blind
DARK_SHARE = 0.2            # the director's floor: this share of a front's windows is dark
DARK_FROM = 5               # a front with fewer windows is only counted in the building's total
SEED = 2317                 # picked on main's table: both wings of the entrance front keep lit windows in every look
# per look: of the windows that may be lit, the share that is; of the others, the share that glows
# behind a curtain
SHARE = {"blue": (0.75, 0.4), "glow": (0.4, 0.2), "deep": (0.12, 0.08)}
ALWAYS = ("tower",)         # fronts whose windows that may be lit are lit in every look
# What no look changes. The entrance: the window over the door is the brightest of the map; the bays
# beside it glow behind curtains on the main storey and are lit on the base storey, so that all five
# show light and no two lit ones are neighbours. The foot of the clock tower (bays 1 and 2 of the
# east front), lit crosswise for the same reason. The apse over the west door, which the sunset
# platform looks at: its middle window lit, the two beside it behind curtains.
FIXED = {
    ("east", 9, "main"): BRIGHT, ("east", 8, "main"): DIM, ("east", 10, "main"): DIM,
    ("east", 8, "base"): LIT, ("east", 10, "base"): LIT,
    ("east", 1, "main"): LIT, ("east", 2, "base"): LIT,
    ("apse", 0, "main"): LIT, ("apse", -1, "main"): DIM, ("apse", 1, "main"): DIM,
}
# The level of the sources behind the glass, by tier: (a tall window, a window up to three rows
# high). A tall lit window has two of them, one row above the sill and one row below the head.
BEHIND = {BRIGHT: (12, 12), LIT: (10, 9), DIM: (8, 7)}
TALL = 4                    # a window of this many rows or more is a tall one

_PRIORITY, _WAKE, _DIM, _BLIND = range(4)
_TIER_OF = {block: tier for tier, role in ROLE.items() for block in role.all()}
_TIER_OF.update({block: DARK for role in (B.WINDOW_DARK, B.WINDOW_BLIND, B.SKYLIGHT) for block in role.all()})


def tier_of(name):
    """The tier a block shows when it is one of the windows of the occupancy table; None for any
    other block (and for no block)."""
    return _TIER_OF.get(name)


def _h(key, salt):
    """A fixed number in [0, 1) for a window."""
    front, bay, storey = key
    return hash3(int(bay), zlib.crc32(str(storey).encode()) & 0xFFFF, zlib.crc32(str(front).encode()) & 0xFFFF,
                 SEED + salt)


def _look(look):
    """The name of the look a scene is built for: the default, a look, or the look a trial varies."""
    if look is None:
        look = mood.DEFAULT
    look = mood.TRIALS.get(look, {}).get("of", look)
    if look not in SHARE:
        raise ValueError(f"no look {look!r}; there are {', '.join(sorted(SHARE))}")
    return look


def _may_be_lit(key, exists, memo):
    """Is a window one of those that may be lit? Every window has a fixed priority, and a window is
    in unless a neighbour of higher priority is. So no two neighbours are both in, and no window
    stays out that could have been in: between two of them lie one or two others."""
    if key not in memo:
        front, bay, storey = key
        if key in FIXED:
            memo[key] = FIXED[key] >= LIT
        else:
            mine = (_h(key, _PRIORITY), bay)
            memo[key] = True
            for n in (bay - 1, bay + 1):
                other = (front, n, storey)
                if other in FIXED:
                    taken = FIXED[other] >= LIT
                else:
                    taken = (exists(other) and (_h(other, _PRIORITY), n) > mine
                             and _may_be_lit(other, exists, memo))
                if taken:
                    memo[key] = False
                    break
    return memo[key]


def _always(front):
    return str(front).rpartition(".")[2] in ALWAYS


def _tier(key, look, exists, memo):
    """The tier of a window that is settled by itself: the shares are kept on the average."""
    if key in FIXED:
        return FIXED[key]
    lit, dim = SHARE[look]
    if _may_be_lit(key, exists, memo) and (_always(key[0]) or _h(key, _WAKE) < lit):
        return LIT
    return DIM if _h(key, _DIM) < dim else DARK


@functools.lru_cache(maxsize=None)
def _tiers(keys, look):
    """The tiers of a whole table: the shares are kept front by front, to the window."""
    lit, dim = SHARE[look]
    memo, out = {}, {}
    for front in sorted({key[0] for key in keys}, key=str):
        mine = sorted(k for k in keys if k[0] == front)
        out.update({k: FIXED[k] for k in mine if k in FIXED})
        free = [k for k in mine if k not in FIXED]
        may = sorted((k for k in free if _may_be_lit(k, keys.__contains__, memo)), key=lambda k: _h(k, _WAKE))
        for k in may[:math.ceil((1.0 if _always(front) else lit) * len(may) - 1e-9)]:
            out[k] = LIT
        rest = sorted((k for k in free if k not in out), key=lambda k: _h(k, _DIM))
        for i, k in enumerate(rest):
            out[k] = DIM if i < int(round(dim * len(rest))) else DARK
    # the floor of dark windows, front by front and then over the whole building: the dim ones that
    # were nearest to being dark go first, then lit ones; the fixed windows stay
    fronts = sorted({key[0] for key in out}, key=str)
    for group in [[k for k in out if k[0] == f] for f in fronts] + [list(out)]:
        if len(group) < DARK_FROM:
            continue
        short = math.ceil(DARK_SHARE * len(group) - 1e-9) - sum(1 for k in group if out[k] == DARK)
        if short > 0:
            free = [k for k in group if out[k] != DARK and k not in FIXED]
            for k in sorted(free, key=lambda k: (out[k], -_h(k, _DIM if out[k] == DIM else _WAKE)))[:short]:
                out[k] = DARK
    return out


def _key(entry):
    if isinstance(entry, dict):
        return (entry["front"], entry["bay"], entry["storey"])
    return tuple(entry)


@functools.lru_cache(maxsize=1)
def _main_keys():
    """The windows of the main building, when its table is in the tree."""
    try:
        from ..main import _plan
    except ImportError:
        return None
    return frozenset(_key(w) for w in _plan.windows())


def tiers(table, look=None):
    """{(front, bay, storey): tier} for all the windows of a building at once. `table` lists them:
    records with those three keys (as main's table has them) or the bare triples. The floor of dark
    windows is kept here, which window_lit() cannot do for a window it knows nothing else about."""
    return dict(_tiers(frozenset(_key(e) for e in table), _look(look)))


def role_of(key, tier):
    """The window of the occupancy table that shows a tier."""
    if tier != DARK:
        return ROLE[tier]
    return B.WINDOW_BLIND if _h(tuple(key), _BLIND) < BLIND_SHARE else B.WINDOW_DARK


def window_lit(front, bay, storey, look=None, table=None):
    """(tier, role) of a window: tier 0 dark, 1 dim, 2 lit, 3 bright; role is the window of the
    occupancy table to glaze it with (take role.block or role.pane).

    front, bay, storey   the window's keys in main's table of windows
    look                 the light version the scene is built for; left out, mood.DEFAULT
    table                the windows of the building this one belongs to, as for tiers(); left out,
                         main's table. A window the table does not list is settled by itself, as if
                         every bay beside it had a window.
    """
    look = _look(look)
    key = (front, bay, storey)
    keys = _main_keys() if table is None else frozenset(_key(e) for e in table)
    if keys is not None and key in keys:
        tier = _tiers(keys, look)[key]
    else:
        tier = _tier(key, look, lambda other: True, {})
    return tier, role_of(key, tier)


def counts(tier_by_key):
    """[dark, dim, lit, bright]: how many windows of each tier."""
    out = [0, 0, 0, 0]
    for tier in tier_by_key.values():
        out[tier] += 1
    return out


def lit_neighbours(tier_by_key):
    """The pairs of neighbouring bays of one front and storey that are both lit (tier 2 or more):
    [(front, storey, bay, bay + 1)]. The rules allow none."""
    out = []
    for (front, bay, storey), tier in sorted(tier_by_key.items(), key=lambda kv: (str(kv[0][0]), kv[0][2], kv[0][1])):
        if tier >= LIT and tier_by_key.get((front, bay + 1, storey), DARK) >= LIT:
            out.append((front, storey, bay, bay + 1))
    return out


def chart(tier_by_key):
    """The tiers as text, a line to each front and storey, one digit to the bay ('.' where the
    table has no window): what a front looks like without drawing it."""
    lines = []
    rows = sorted({(str(front), storey) for front, _, storey in tier_by_key})
    for front, storey in rows:
        bays = {bay: tier for (f, bay, s), tier in tier_by_key.items() if str(f) == front and s == storey}
        lo, hi = min(bays), max(bays)
        lines.append(f"{front:>12} {storey:<5} bays {lo:>3}..{hi:<3} "
                     + "".join(str(bays[b]) if b in bays else "." for b in range(lo, hi + 1)))
    return "\n".join(lines)


# ---- what the other lines register -----------------------------------------------------------------
def offers(canvas):
    """The light sources registered on a canvas and not settled yet: [((x, y, z), level, why, rank)]."""
    if not hasattr(canvas, "light_offers"):
        canvas.light_offers = []
    return canvas.light_offers


def suggest(canvas, pos, level, why, rank=None):
    """Register a light source somebody would like: the cell (scene coordinates, the origin already
    added), its level and what throws the light ("props/lamps:street"). No block is placed here.
    sky/lights.build() goes through the list when everything else stands, and places a source if
    something that glows is within two cells of it; a cell that is taken moves the source to the
    next free one.

    rank   1, 2 or 3: the rank the source belongs to, when the name does not say it (KIND_RANK).
           A level over the top of the rank is cut down to it.
    """
    x, y, z = (int(math.floor(v)) for v in pos)
    offers(canvas).append(((x, y, z), int(level), str(why), rank))


def take(canvas, lights, why, rank=None):
    """suggest() for a list [((x, y, z), level), ...], as the placing functions of props return."""
    for pos, level in lights:
        suggest(canvas, pos, level, why, rank)


def glazed(canvas, windows, origin=(0, 0, 0), group="", look=None):
    """Register the windows of a front that main's table does not list (another building, a sample
    wall in a test scene), so that sky/lights.build() lights the lit ones among them.

    windows   records as in main's table: front, bay, storey, cells (the glass columns (x, z)),
              inward (the step from the glass into the building), y (the glass's bottom and top
              row). A record marked blind is left out; "level" asks for another level behind it.
    origin    what is added to the cells and rows
    group     a name for the building, to keep its fronts apart from another's in the report
    look      the look the front was glazed for, when it is not the one build() is called with
    """
    if not hasattr(canvas, "light_windows"):
        canvas.light_windows = []
    for w in windows:
        if w.get("blind"):
            continue
        canvas.light_windows.append(dict(
            group=str(group), origin=tuple(int(v) for v in origin), front=w["front"], bay=w["bay"],
            storey=w["storey"], cells=[tuple(c) for c in w["cells"]], inward=tuple(w["inward"]),
            y=tuple(w["y"]), level=w.get("level"), look=look))


# ---- a look at the result without drawing it -------------------------------------------------------
_OPEN_SHAPES = ("_stairs", "_slab", "_wall", "_pane", "_bars", "_door", "_trapdoor", "_rod", "_chain",
                "_lantern", "_fence", "_fence_gate", "_button", "_sign", "_carpet", "_torch")


def _stops_light(state):
    name = AB.name_of(state)
    return not (name == B.LIGHT or F.see_through(name) or name.endswith(_OPEN_SHAPES))


def levels(canvas, lo, hi):
    """Block light in the cells of the box lo..hi, spread as the game spreads it: {(x, y, z): level}
    for every cell that gets any. For checking a placement by numbers. Whole blocks stop the light;
    glass and everything that is not a whole block let it pass (stairs and slabs too, which in the
    game shut it out on their closed sides: here a little more light gets by them)."""
    out, rings = {}, {}
    box = [range(lo[i], hi[i] + 1) for i in range(3)]
    for cell, state in canvas.b.items():
        if cell[0] in box[0] and cell[1] in box[1] and cell[2] in box[2]:
            e = F.emission(*AB.parse(state))
            if e > 0:
                out[cell] = e
                rings.setdefault(e, []).append(cell)
    for level in range(15, 1, -1):
        for x, y, z in rings.get(level, ()):
            if out.get((x, y, z)) != level:
                continue
            for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
                if out.get(n, 0) >= level - 1 or not (n[0] in box[0] and n[1] in box[1] and n[2] in box[2]):
                    continue
                state = canvas.b.get(n)
                if state is not None and _stops_light(state):
                    continue
                out[n] = level - 1
                rings.setdefault(level - 1, []).append(n)
    return out

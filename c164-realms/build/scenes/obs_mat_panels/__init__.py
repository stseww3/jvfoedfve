"""Test scene of the work package materials/panels (plan/packages/materials/panels.md).

What it is for: to see the sixteen instrument panels as what they are made for, a wall.

    wall        one bay of eight by four that holds every kind (the louvre six times, the drawers
                four, eight kinds twice, and once each the nameplate, the bell, the gauges, the
                register, the oscilloscope and the recorder), under the lamp row: each face
                close, the bay from twenty blocks, and from the side for the casing
    room        the bay and its mirror image as the wall of a closed room of the timing room's size
                (16 long, 12 deep, 7 high), on a riveted plinth under plain plate, with no light but
                three weak lamps where desks would stand: the dark iron wall with a few things
                glowing on it that view V10 is about, and the casing beside cast iron
    turn        one block for each way a panel can face, free-standing: the instrument shows on the
                side it faces and nowhere else, and it stands upright there (a register, whose
                figures would show a mirrored picture, with an oscilloscope on top of it)
    animated    the four that move, side by side, to be watched in the game

The bay is this package's proposal for the timing room; where the panels finally stand is the
interiors line's to say. Its rows are sorted the way a switchboard bay is: at the top the valves
and relays, with the nameplate and the bell; under them what is read from across the room (pilot
lamps, dials, the gauges, the register); at hand height the switches, the oscilloscope and the
recorder; at the foot the fuses and jack fields.

Across, the bay is three sections of two with a quiet column between them (louvres over drawers):
two flanks that are alike, and a middle that holds what there is one of. Each row reads the same
from both ends but for its middle pair. The rules it keeps (the review of the first wall; faults()
checks them on the bay and on the bay beside its mirror image, as the room has it):

  - a quiet face, a louvre or a drawer front, at most two steps from every instrument along its
    row, so no row is one unbroken run of instruments;
  - no instrument beside or above another of its kind, but where two bays meet end to end, and
    never two dials or two gauges side by side: two white rounds are a pair of eyes;
  - of the light faces (dial, gauges, recorder) no two beside or above each other, and of the lit
    ones (valves, oscilloscope, pilot lamps) none beside or above a lit face of another kind;
  - one nameplate to a bay.

    python -m scenes.obs_mat_panels        writes shots.json from the layout below
"""
from artkit.blocks import st
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.materials import _board, panels

BIOME = "obs_blue"
Z = 0
TIME = 14000        # the default light version (sky line)

# one bay, top row first
BAY = [row.split() for row in (
    "relays       tubes       louvre  nameplate bell     louvre  tubes       relays",
    "pilot_lamps  dial        louvre  gauges    counter  louvre  dial        pilot_lamps",
    "knife_switch bus_switch  drawers scope     recorder drawers bus_switch  knife_switch",
    "fuses        patch_panel drawers louvre    louvre   drawers patch_panel fuses",
)]
WIDE, HIGH = len(BAY[0]), len(BAY)
QUIET = ("louvre", "drawers")       # faces with nothing to read on them: where the eye rests
REACH = 2                           # an instrument has a quiet face within so many steps along its row
EYES = ("dial", "gauges")           # white rounds: never two of a kind side by side, not even where bays meet
ROOM = (16, 12, 7)                  # the timing room: along the wall, deep, high (interiors, timeroom)
DESK_LAMP = 12                      # a second-rank light, three blocks from the wall
# the posts from west to east: a camera off either end of the row has the two that face it nearest
FACINGS = ("north", "west", "east", "south")
ANIMATED = ("tubes", "scope", "counter", "pilot_lamps")


def faults(rows=None):
    """What a wall of panels breaks of the rules in the note above: sentences, none when it keeps
    them. `rows` is the wall, top row first, one bay wide or several; left out, the bay is
    checked alone and beside its mirror image."""
    if rows is None:
        return faults(BAY) + faults([row + row[::-1] for row in BAY])
    light, lit = panels.RANKS["light"], panels.RANKS["lit"]
    wide = len(rows[0])
    wrong = [f"no {name} on the wall" for name in sorted(set(B.PANELS) - {name for row in rows for name in row})]
    plates = sum(row.count("nameplate") for row in rows)
    if plates != wide // WIDE:
        wrong.append(f"{plates} nameplates on {wide // WIDE} bays")
    for j, row in enumerate(rows):
        for i, name in enumerate(row):
            if name not in QUIET and not any(near in QUIET for near in row[max(0, i - REACH):i + REACH + 1]):
                wrong.append(f"row {j}, column {i}: no quiet face within {REACH} steps of the {name}")
            beside = [(row[i + 1], "beside", (i + 1) % WIDE == 0)] if i + 1 < wide else []
            under = [(rows[j + 1][i], "above", False)] if j + 1 < len(rows) else []
            for other, how, seam in beside + under:
                if name in light and other in light:
                    wrong.append(f"row {j}, column {i}: two light faces, {name} {how} {other}")
                elif name == other and name not in QUIET and (not seam or name in EYES):
                    wrong.append(f"row {j}, column {i}: {name} {how} {other}")
                elif name != other and name in lit and other in lit:
                    wrong.append(f"row {j}, column {i}: two lit faces, {name} {how} {other}")
    return wrong


assert not faults(), "the bay breaks its own rules:\n  " + "\n  ".join(faults())


def bay(c, x, y, z, mirrored=False):
    """One bay with its foot at y, facing south. The material board (obs_mat_board) builds its
    cabinet wall with this, WIDE and HIGH: the three names and these arguments stay, and a bay
    stays eight wide and no more than six rows high."""
    for j, row in enumerate(BAY):
        for i, name in enumerate(row[::-1] if mirrored else row):
            c.set(x + i, y + HIGH - 1 - j, z, st(B.PANELS[name], facing="south"))


def wall(c, x, z):
    bay(c, x, 0, z)
    _board.stage(c, x, x + WIDE - 1, z)
    return x + WIDE + 1


def room(c, x, z):
    """The wall at z facing into the room south of it; the room is closed, the camera stands in it."""
    long, deep, high = ROOM
    x1, z1 = x + long - 1, z + deep
    c.box(x - 1, -1, z, x1 + 1, -1, z1 + 1, B.FLOOR_WOOD.block)
    c.box(x - 1, high, z, x1 + 1, high, z1 + 1, B.DARK_WOOD.block)
    for wx in (x - 1, x1 + 1):
        c.box(wx, 0, z, wx, high - 1, z1 + 1, B.DARK_WOOD.block)
    c.box(x, 0, z1 + 1, x1, high - 1, z1 + 1, B.DARK_WOOD.block)
    c.box(x, 0, z, x1, 0, z, B.IRON_RIVETED.block)
    c.box(x, 1 + HIGH, z, x1, high - 1, z, B.IRON_PLATE)
    bay(c, x, 1, z)
    bay(c, x + WIDE, 1, z, mirrored=True)
    for dx in (2, 8, 13):
        c.set(x + dx, 2, z + 4, st(B.LIGHT, level=DESK_LAMP))
    return x1 + 3


def turn(c, x, z):
    """Four posts three apart, one for each facing; no backdrop, so that they are seen from both
    sides, and lamps on both sides. From the north-west the first two show their instruments and
    the other two their casing, from the south-east the other way round."""
    c.box(x - 2, -1, z - 5, x + 12, -1, z + 5, _board.FLOOR)
    for i, facing in enumerate(FACINGS):
        px = x + 1 + 3 * i
        c.set(px, 0, z, _board.BASE)
        c.set(px, 1, z, st(B.PANELS["counter"], facing=facing))
        c.set(px, 2, z, st(B.PANELS["scope"], facing=facing))
        for dz in (-3, 3):
            c.set(px, 3, z + dz, st(B.LIGHT, level=15))
    return x + 13


def animated(c, x, z):
    n = len(ANIMATED)
    c.box(x, 0, z, x + n - 1, 0, z, B.IRON_RIVETED.block)
    for i, name in enumerate(ANIMATED):
        c.set(x + i, 1, z, st(B.PANELS[name], facing="south"))
    c.box(x, 2, z, x + n - 1, 2, z, B.IRON_PLATE)
    _board.stage(c, x, x + n - 1, z, height=5)
    return x + n + 1


STATIONS = [("wall", wall), ("room", room), ("turn", turn), ("animated", animated)]


def layout(c=None):
    """Where each station stands: {name: (first x, x after it)}. Builds into `c` when given one."""
    c = c or Canvas()
    spans, x = {}, 0
    for name, station in STATIONS:
        end = station(c, x, Z)
        spans[name] = (x, end)
        x = end + 2
    return spans


def build():
    c = Canvas()
    layout(c)
    return c


def write_pack(pack_dir):
    return materials.pack(pack_dir)


def shots():
    """Camera positions from the layout. The bay: whole, its two halves close enough to read every
    face (between them they hold all sixteen kinds), from twenty blocks, and from above its east
    end for the casing on its side and top (the camera keeps west of the room's wall). The room:
    the whole wall from two thirds back in the room, and along the wall from near. The posts from
    off the south-east end of their row and from off the north-west end: each time the two nearest
    posts face the camera, one nearly head-on and one at an angle, and the two behind them show
    their casing. The four that move, close."""
    spans = layout()
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(float(v), 1) for v in pos],
                    "look_at": [round(float(v), 1) for v in look_at], "time": TIME})

    x = spans["wall"][0]
    mid, eye = x + WIDE / 2.0, HIGH / 2.0
    shot("wall", (mid, eye + 0.6, Z + 6.5), (mid, eye, Z))
    shot("wall_left", (x + WIDE / 4.0, eye + 0.2, Z + 4.2), (x + WIDE / 4.0, eye, Z))
    shot("wall_right", (x + 3 * WIDE / 4.0, eye + 0.2, Z + 4.2), (x + 3 * WIDE / 4.0, eye, Z))
    shot("wall_far", (mid, eye + 1.0, Z + 21.0), (mid, eye, Z))
    shot("wall_side", (x + WIDE + 1.6, HIGH + 2.2, Z + 3.4), (x + WIDE - 2.0, eye + 0.6, Z + 0.4))

    x = spans["room"][0]
    long, deep, high = ROOM
    mid = x + long / 2.0
    shot("room", (mid, 3.2, Z + 9.0), (mid, 2.8, Z))
    shot("room_near", (x + 2.5, 2.4, Z + 5.0), (x + 9.5, 2.8, Z))

    x = spans["turn"][0]
    shot("turn_se", (x + 12.0, 2.6, Z + 4.0), (x + 9.2, 1.9, Z + 0.8))
    shot("turn_nw", (x, 2.6, Z - 3.0), (x + 2.8, 1.9, Z + 0.2))

    x = spans["animated"][0]
    mid = x + len(ANIMATED) / 2.0
    shot("animated", (mid, 1.9, Z + 4.0), (mid, 1.5, Z))
    return out

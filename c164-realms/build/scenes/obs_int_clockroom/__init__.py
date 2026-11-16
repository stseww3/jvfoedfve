"""obs_int_clockroom: the test scene of the clock room in the time tower (work package
interiors/clockroom).

The room stands in a stand-in shell: the tower as main/tower builds it, alone on a deck where the
pavilion's roof would be, with the dials, hands and time ball of machines/clock on it as in the
master scene. Then scenes.obs.interiors.clockroom.build() is called, the call the master scene
makes (it opens the tower's way up), and the sky line places the light.

build(room_in=False) is the same shell without the room: the tower shut, its well empty. The twin
scene obs_int_clockroom_bare shows it from the board's view V5, so the two pictures lie side by
side; outside_light() counts the same thing, the light in the cells round the tower with and
without the room.

The cameras are in VIEWS; `python -m scenes.obs_int_clockroom` writes shots.json from them and
prints that count, and the light on the places one can stand in (walk_light()).
"""
from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.interiors import clockroom as room
from scenes.obs.machines import clock
from scenes.obs.main import tower

BIOME = "obs_blue"
CATEGORY = "interiors"
TIME = 14000
EYE = room.FLOOR_TOP + S.EYE            # 25.62: the eye of somebody on the room's floor
LOBBY = tower.FOOT + S.EYE              # 19.62: the eye of somebody who has come in by the door
CX, CZ = room.AXIS
DECK = 3                                # the stand-in deck reaches this far beyond the tower's foot

# name, the eye, what it looks at
VIEWS = [
    # the first sight off the ladder, standing in the north-west corner where it opens to the shaft:
    # the movement, the nest of bevels over it, the east and the south dial behind
    ("int_arrive", (11.9, EYE, -31.1), (CX + 0.15, 26.45, CZ + 0.15)),
    # the movement's front from the floor north-east of it: the setting dial, the crank, the three
    # barrels, the motor at the far end
    ("int_movement", (14.45, EYE, -30.9), (CX - 0.35, 25.7, CZ - 0.2)),
    # one dial's back and its rod, from the floor beside the movement
    ("int_dial", (12.3, EYE, -30.7), (15.0, 27.4, CZ)),
    # the board's view V5 from the court: the tower as it stands with the room in it
    ("ext_v5", S.V5["pos"], S.V5["look_at"]),
    # the movement's back from the south-west corner: the escape wheel, the pallets, the crutch and
    # the pendulum
    ("int_back", (11.9, EYE, -27.9), (CX + 0.1, 26.3, CZ + 0.3)),
    # up the shaft from beside the movement: the bevels, the four rods, the sheaves and the ropes
    ("int_up", (12.4, EYE, -30.6), (CX + 0.1, 29.5, CZ + 0.1)),
    # the lobby as one comes in by the door: the ladder, the bob over the heads, the weights in the corners
    ("lobby", (11.45, LOBBY, CZ + 0.3), (CX + 0.4, 21.3, -28.9)),
    # the way up, from the middle of the lobby: the ladder in its corner, the lamp beside its foot
    ("ladder", (CX - 0.2, LOBBY, CZ + 0.4), (11.7, 21.2, -31.7)),
    # the arrival view V1 from the station: the tower on the skyline
    ("ext_v1", S.V1["pos"], S.V1["look_at"]),
]


def shots():
    return [{"name": name, "pos": [round(float(v), 2) for v in pos],
             "look_at": [round(float(v), 2) for v in look_at], "time": TIME}
            for name, pos, look_at in VIEWS]


def shell(c):
    """The tower on a deck of its own, with what the machines line hangs on it."""
    for x in range(tower.X0 - DECK, tower.X1 + DECK + 1):
        for z in range(tower.Z0 - DECK, tower.Z1 + DECK + 1):
            c.set(x, tower.FOOT - 1, z, B.ASHLAR_FINE.block)
    tower.build(c)
    clock.tower(c)


def build(room_in=True):
    c = Canvas()
    shell(c)
    if room_in:
        room.build(c)
    sky.build(c)
    return c


def build_models():
    out = {}
    for part in (tower, clock, sky):
        out.update(part.models() or {})
    out.update(room.models())
    out.update(room.their_models())
    return out


def write_pack(pack_dir):
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


BOX = ((tower.X0 - 2, tower.FOOT, tower.Z0 - 2), (tower.X1 + 2, tower.SHAFT_TOP, tower.Z1 + 2))


def _levels(room_in):
    """(the block light in the cells of the tower's shaft and two cells round it, from the deck to
    the cornice; the sources in there, {cell: level})."""
    from artkit import blocks as AB
    from scenes.obs.sky import _lightkit

    c = build(room_in)
    lo, hi = BOX
    sources = {}
    for cell, state in c.b.items():
        if all(lo[i] <= cell[i] <= hi[i] for i in range(3)) and AB.parse(state)[0] == "light":
            sources[cell] = int(AB.parse(state)[1].get("level", 15))
    return _lightkit.levels(c, lo, hi), sources


def _outside(cell):
    return not (tower.X0 < cell[0] < tower.X1 and tower.Z0 < cell[2] < tower.Z1)


def outside_light(got=None):
    """The block light outside the tower's walls (its recesses and two cells beyond its faces) with
    the room and without it: {cell: (without, with)} for every cell that differs. Empty when the
    room changes nothing outside."""
    bare, full = got or (_levels(False)[0], _levels(True)[0])
    cells = sorted(cell for cell in set(bare) | set(full) if _outside(cell))
    return {cell: (bare.get(cell, 0), full.get(cell, 0)) for cell in cells if bare.get(cell, 0) != full.get(cell, 0)}


def walk_light(full=None):
    """The light on every place one can stand in the room: {(x, z): the more of the feet's cell and
    the head's}."""
    full = full if full is not None else _levels(True)[0]
    return {(x, z): max(full.get((x, room.FEET, z), 0), full.get((x, room.FEET + 1, z), 0)) for x, z in room.walk()}


def way_light(full=None):
    """The light in every cell of the way up, from inside the door to the hatch: {cell: level}. The
    door's lamp outside is the light line's and not in this scene: the first cell has more with it."""
    full = full if full is not None else _levels(True)[0]
    return {cell: full.get(cell, 0) for cell in room.way()}

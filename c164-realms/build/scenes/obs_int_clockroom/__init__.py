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
prints that count.
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
    # the first sight coming up the ladder, in the north-west corner: the movement, the nest of bevels
    # over it, the east and the south dial behind
    ("int_arrive", (11.7, EYE, -31.3), (CX + 0.2, 26.3, CZ + 0.2)),
    # the movement's front from the north gallery: the setting dial, the crank, the motor; the south dial over it
    ("int_movement", (CX, EYE, -31.7), (CX, 25.75, CZ)),
    # one dial's back and its rod, from the floor beside the movement
    ("int_dial", (12.3, EYE, -30.7), (15.0, 27.4, CZ)),
    # the board's view V5 from the court: the tower as it stands with the room in it
    ("ext_v5", S.V5["pos"], S.V5["look_at"]),
    # the movement's back from the south gallery: the escape wheel, the pallets, the crutch and the pendulum
    ("int_back", (CX - 0.9, EYE, -27.5), (CX + 0.1, 26.35, CZ + 0.3)),
    # up the shaft from beside the movement: the bevels, the four rods, the sheaves and the ropes
    ("int_up", (12.4, EYE, -30.6), (CX + 0.1, 29.5, CZ + 0.1)),
    # the lobby as one comes in by the door: the ladder, the bob over the heads, the weights in the corners
    ("lobby", (11.45, LOBBY, CZ + 0.3), (CX + 0.4, 21.3, -28.9)),
    # the plan, from under the ceiling in the north-west corner
    ("from_above", (11.6, 30.4, -31.6), (CX + 0.4, 24.6, CZ + 0.4)),
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


def outside_light():
    """The block light in the cells round the tower's shaft (its recesses and two cells beyond its
    faces, from the deck to the cornice), with the room and without it: {cell: (without, with)} for
    every cell that differs. Empty when the room changes nothing outside."""
    from scenes.obs.sky import _lightkit

    lo = (tower.X0 - 2, tower.FOOT, tower.Z0 - 2)
    hi = (tower.X1 + 2, tower.SHAFT_TOP, tower.Z1 + 2)
    got = [_lightkit.levels(build(room_in), lo, hi) for room_in in (False, True)]

    def outside(cell):
        return not (tower.X0 < cell[0] < tower.X1 and tower.Z0 < cell[2] < tower.Z1)

    cells = sorted(cell for cell in set(got[0]) | set(got[1]) if outside(cell))
    return {cell: (got[0].get(cell, 0), got[1].get(cell, 0)) for cell in cells
            if got[0].get(cell, 0) != got[1].get(cell, 0)}

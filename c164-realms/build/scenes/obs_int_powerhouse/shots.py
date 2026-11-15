"""The shot list of obs_int_powerhouse, written from the numbers (python -m scenes.obs_int_powerhouse)."""
import math

from scenes.obs.common import skeleton as S
from scenes.obs.interiors import powerhouse as PH
from scenes.obs.machines import engine_dynamo as E

BOX = S.POWER_HOUSE["box"]
X0, Z0, X1, Z1 = BOX
FEET = S.POWER_HOUSE["base_y"]
EYE = FEET + S.EYE
WHEEL = (E.CX + E.WHEEL_X, FEET + E.WHEEL_BLOCKS / 2.0, E.CZ)
DYNAMO = (E.CX + E.DYNAMO_X, FEET + 1.2, E.CZ)
DOOR_X = (PH.DOOR_X[0] + PH.DOOR_X[1]) / 2.0


def shots():
    """V6 as the card asks (the flywheel and the furnace door in one picture), its twin from the
    other end, then the room as a visitor sees it: in through the wicket, the walkway, the machine
    broadside, the switchboard's wall, and the two furnace bays."""
    out = []

    def shot(name, pos, look_at, time=None):
        d = {"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at]}
        if time is not None:
            d["time"] = time
        out.append(d)

    # V6: the heart of the room, the flywheel with the furnace bays behind it
    shot("v6", (X0 + 3.5, EYE, Z0 + 19.0), (WHEEL[0], WHEEL[1], WHEEL[2] - 1.0))
    shot("v6_north", (X0 + 3.5, EYE, Z0 + 3.0), (WHEEL[0], WHEEL[1], WHEEL[2] - 1.0))
    shot("v6_up", (X0 + 6.0, FEET + 1.0, Z0 + 18.0), (WHEEL[0], WHEEL[1] + 1.0, WHEEL[2]))
    # the machine broadside, the belt and the dynamo
    shot("machine", (E.CX - 1.0, EYE, E.CZ + 6.5), (DYNAMO[0], DYNAMO[1], DYNAMO[2]))
    shot("flywheel", (E.CX + 1.0, EYE, E.CZ + 5.0), (WHEEL[0], WHEEL[1], WHEEL[2]))
    # in through the wicket
    shot("door_in", (DOOR_X, EYE, Z0 - 4.0), (WHEEL[0], WHEEL[1] - 0.5, WHEEL[2]))
    shot("door_step", (DOOR_X, EYE, Z0 + 3.0), (E.CX, FEET + 1.2, E.CZ))
    # the walkway, both ways
    shot("walkway", (PH.WALK_X[1], EYE + 0.6, PH.WALK_END_Z), (PH.X0 + 2, FEET + 1.0, PH.Z0 + 2))
    shot("walkway_in", (PH.DOOR_X[0], EYE + 0.6, PH.WALK_Z[0]), (PH.WALK_X[1], FEET + 1.0, PH.WALK_END_Z))
    # the room itself: the walls, the trusses, the ceiling
    shot("room", (X1 - 2.5, EYE, Z1 - 2.5), (X0 + 3.0, FEET + 3.0, Z0 + 3.0))
    shot("ceiling", (X0 + 9.0, FEET + 1.0, Z0 + 16.0), (X0 + 9.0, FEET + 9.0, Z0 + 8.0))
    # the two furnace bays: the boilers' wall, the glow the light line will put behind them
    shot("furnace", (X0 + 2.5, EYE, Z0 + 8.0), (X0 + 3 * S.BAY + 5.0, FEET + 3.0, Z0 + 1.0))
    shot("furnace_east", (X1 - 6.0, EYE, Z0 + 8.0), (X1 - 1.0, FEET + 3.0, Z0 + 6.0))
    return out

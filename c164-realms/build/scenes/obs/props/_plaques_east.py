"""props/_plaques_east: where the six plaques out of doors hang (read by props/plaques.site_plaques();
motion/guide part B, card plan/packages/props/plaques.md).

A plaque hangs on stone that stands already -- a pier, a jamb, the plinth of a pilaster -- beside the
way to the thing it names, its middle HANG over the ground its reader stands on: just under his eye.
Every place is worked out from the tables of the package that built the stone, when plaques() is
called. Where each hangs and why there:

    cable_station    the waiting room's gable, which looks west at the observatory: the angle pier
                     at its south end, beside the lit window and under the end of the name board.
                     Not on the front: the credit plate hangs there (motion/guide part A, c346), and
                     the front west of x 82 is the right edge of the arrival view (V1). V1's eye is
                     behind this face.
    meridian_line    the meridian hut's south gable, the west jamb of the slot the brass runs into:
                     who walks north along the line comes up to it. The line has no east end (review
                     c332); at its south end nothing stands. The hut's lamp hangs east of the slot.
    armillary        the south face of the die under the sphere. Not the east face: V2 looks straight
                     at that one, in the middle of its picture (review c332). V2's eye is behind
                     this face.
    time_ball        the foot of the clock tower on the court: the plinth of the pilaster under the
                     tower's east dial, the middle one of the north end pavilion.
    power_house      the pier east of the door bay of the north front, beside the wicket. The pier
                     west of it is 15 blocks from V6 and would be drawn in that picture; this one
                     is 17 from it. The gutter's pipes come down two piers further east and on the
                     west corner.
    sunset_terrace   the plinth of the pilaster south of the west door, on the terrace's side: the
                     side of the house the door plate of the entrance is on. The door's leaves lie
                     along the reveals, inside the face of the pilaster. The terrace's own piers are
                     wall posts under a slab, a block high: nothing a plate hangs on.

No camera of the board looks at any of them from nearer than a plaque is drawn (plaques.VIEW, 16
blocks): python -m scenes.obs_props_plaques_site names one that does.
"""
from ..common import skeleton as S

HANG = 1.5      # the middle of a plaque over the ground its reader stands on (his eye is at S.EYE, 1.62)


def plaques():
    from ..machines import armillary
    from ..main import _plan as plan
    from ..site import cablecar, powerhouse

    out = {}

    # the waiting room's south-west angle pier, its west face
    x0, _, _, z1 = cablecar.WAIT
    out["cable_station"] = dict(pos=(float(x0), cablecar.FEET + HANG, z1 + 0.5), facing="west")

    # the hut's south gable: the jamb west of the slot, whose foot is the hut's door cell
    door_x, door_z = S.MERIDIAN_HUT["door"]
    out["meridian_line"] = dict(pos=(door_x - 0.5, S.GROUND + HANG, door_z + 1.0), facing="south")

    # the die of the armillary's base, a block on its core: its south face
    out["armillary"] = dict(pos=(armillary.CX + 0.5, S.GROUND + HANG, armillary.CZ + 1.0), facing="south")

    # the north end pavilion, which the tower stands on: the pilaster between its two bays, its east face
    bay = S.END_BAYS[0]
    out["time_ball"] = dict(pos=(S.east_wall_x(bay) + S.DEPTH_PILASTER + 1.0, S.GROUND + HANG, S.pilaster_z(bay) + 0.5),
                            facing="east")

    # the pier plane of the power house's north front: the pier east of the door bay (the wicket is
    # the bay's middle cell)
    wicket_x, _ = powerhouse.DOOR_AT["cell"]
    out["power_house"] = dict(pos=(wicket_x + 2.5, powerhouse.FEET + HANG, float(powerhouse.Z0)), facing="north")

    # the apse's pilasters next to the axis stand either side of the west door: the south one, its west face
    piers = plan.apse_pilasters()
    near = min(abs(z - plan.CZ) for _, z in piers)
    x, z = max((c for c in piers if abs(c[1] - plan.CZ) == near), key=lambda c: c[1])
    out["sunset_terrace"] = dict(pos=(float(x), S.GROUND + HANG, z + 0.5), facing="west")
    return out

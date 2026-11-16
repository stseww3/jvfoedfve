"""props/_plaques_west -- where the six plaques indoors hang (card plan/packages/props/plaques.md;
motion/guide, part 2). props/plaques asks plaques() when it hangs the plaques of the site; the six
out of doors are props/_plaques_east.

A plaque hangs on a block that stands in the building already, its middle HEIGHT over the floor it
is read from, and where one faces it on the way in:

  orrery            the pilaster of the north aisle under the meridian beam, on the face that looks
                    into the hall, on its slate base: across the nave from the orrery. Not on the
                    shaft: that is the lightest stone of its corner in V7, and the plaque a blue
                    band right across it (cr3 #83149). On the base it is dark on dark, low on the
                    right of that picture
  master_clock      the front of the plinth the clock stands on, under its case, on the hall's
                    axis: one walks up to it from the door. At the lower edge of V7
  time_room,        the west post of the door's stone case, on the gallery: the post one comes to
  chart_room        first from the stair. They are drawn from GALLERY blocks: the camera of V7
                    stands 14 from them (the gallery's own girder is between), and two plaques are
                    in that picture already. Neither is in its room, so V9 and V10 have none
  plate_vault       the north end of the island stack on the left as one comes in, under its
                    number: what one faces inside the door. Drawn from VAULT blocks: the cameras
                    of V7 and V9 stand 12 and 8 from it, a wall and a floor between
  great_refractor   the drum's lining on the east side, on the flat north of the switchboard's:
                    it faces whoever comes round the pier from the stair. Not on the pier and not
                    between the camera of V8 and the tube (cr4 #80727): that camera looks west and
                    has it behind its right shoulder

So the board shows two of the six, both in V7 (cr3), and no other camera of it has one in front.
"""
from ..common import skeleton as S
from . import _kit as K

HEIGHT = 1.5            # blocks from the floor one stands on to a plaque's middle: under the eye (a6)
UNDER_NUMBER = 1.25     # the vault's: the stack's number hangs at 1.75, a plate nine pixels high
GALLERY = 12.0          # blocks the two door plaques are drawn from
VAULT = 7.0             # and the vault's
BLOCKS = 64.0           # a display entity's view range of 1 is this many blocks


def plaques():
    """{key of plaques.TEXT: dict(pos, facing[, view])}: the six plaques indoors. pos is the plaque's
    middle, on the face it hangs on; facing is the way that face looks. The other packages are
    read here and not at import, so that the table follows them."""
    from ..interiors import domeroom, platevault, starhall
    from ..machines import clock
    from ..main import shell

    out = {}

    # the star hall: the pilaster under the beam that crosses over the orrery, north aisle; a
    # pilaster is a block before the aisle's wall, so its face is one further into the hall
    x = min(starhall.beam_xs(), key=lambda beam: abs(beam - starhall.CX))
    out["orrery"] = dict(pos=(S.mid(x), starhall.FEET + HEIGHT, starhall.Z0 + 1.0), facing="south")

    # the mother clock stands on the middle block of its plinth, its back to the pier: the plaque
    # in the middle of that block's front
    x, y, z = clock.MASTER_AT
    front = K.turn(K.FACING[clock.MASTER_FACING], (0.0, 0.0, 1.0))
    out["master_clock"] = dict(pos=(x + front[0], y - 0.5, z + front[2]), facing=clock.MASTER_FACING)

    # the two wing rooms: the west post of the door case (shell.doors(): frame), on the wall's
    # face towards the gallery
    for d in shell.doors():
        key = d["room"].replace(" ", "_")
        if key not in ("time_room", "chart_room"):
            continue
        north = d["inward"][1] < 0                      # the room lies north of its gallery
        px, pz = min(d["frame"])
        out[key] = dict(pos=(S.mid(px), d["y"][0] + HEIGHT, pz + (1.0 if north else 0.0)),
                        facing="south" if north else "north", view=GALLERY / BLOCKS)

    # the plate vault: the north end of the east island stack, under the number 1
    out["plate_vault"] = dict(pos=(S.mid(platevault.ISLAND_X[1]), platevault.FEET + UNDER_NUMBER,
                                   float(platevault.ISLAND_Z[0])),
                              facing="north", view=VAULT / BLOCKS)

    # the dome room: the lining's flat north of the three columns the switchboard hangs on, which
    # stands a cell further in; its middle column
    niche = domeroom.niches()["east"]
    x = niche[0][0] - 1
    flat = sorted(z for cx, z in domeroom.lined() if cx == x and z < niche[0][1])
    out["great_refractor"] = dict(pos=(float(x), domeroom.FEET + HEIGHT, S.mid(flat[len(flat) // 2])),
                                  facing="west")
    return out

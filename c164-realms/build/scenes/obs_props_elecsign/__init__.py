"""Test scene of the work package props/electrics-signs: the station's emblem, the enamel plates and
the exposed electrics, hung on a slice of the real east front.

The wall is not a stand-in. main/_order lays main/facade's own order on a footprint cut out of the
building's plan: bays 4 to 14 of the east front where the skeleton has them -- the middle pavilion
with the three arches of the entrance and four bays of each wing -- eight columns deep, with a
vestibule behind the arches. What the entrance has on c206's branch and main/facade in the tree
may not build yet (the gates in the side arches, the shut arch heads, the arches' keys, the
emblem's tablet, the vestibule) is set here cell for cell as that branch sets it, so the slice
does not change when it lands. The slice has no drum behind its parapet and no pitched roofs.

On it:
  the great emblem on its tablet over the entrance, with the pair of entrance lamps and the two
  street lamps of props/lamps under it;
  a line along the south wing: out of a junction box on pilaster 11, up a conduit, three bays on
  insulators under the string course and back into the wall at pilaster 14; the voltage plate on
  the wall beside the box;
  a number plate on every pilaster of the two wings, 1 to 8 from the south;
  on the north wing a bell and the small brass emblem, each over a number plate;
  the flag on its pole in the court, flying with the map's wind.
The wall telephone and the telegraph key are pieces for a room: the time room places them, the
test scene obs_props_elecsign_room shows them with the way plates beside a door, and props.py
shows them in the gallery. The cable station's name board hangs on a copy of its gable in
obs_props_elecsign_station.

Light. Once sky/lights is in the tree it lights the slice as it lights the building: the slice
stands where the building does, so main's table of windows, the doorway and the wall wash all
fall on it (the canvas asks for them, _lightkit.dress). Until then the sources of the windows and
of the entrance are put down here in that package's cells and at its levels; the wings get no
wash, and the plates on them are seen by the sky's light alone.

The shots are written from the numbers below:  python -m scenes.obs_props_elecsign
"""
import importlib.util
import inspect

from artkit.canvas import Canvas

from scenes.obs import materials, sky
from scenes.obs.common import blocks as B
from scenes.obs.common import skeleton as S
from scenes.obs.main import _order as O
from scenes.obs.main import _plan as P
from scenes.obs.main import facade
from scenes.obs.props import electrics, lamps, signs
from scenes.obs.site import _kit as site

BIOME = "obs_blue"
BIOME_MARGIN = 32
BIOME_MARGIN_Y = 32
TIME = 14000                    # light version A, the default (INTERFACE: 18000 is B, 12900 is C)
TIME_DEEP, TIME_GLOW = 18000, 12900

# ---- the slice ------------------------------------------------------------------------------------------
DOOR = P.AISLE_BAY                              # 9: the middle bay
ARCADE = (DOOR - 1, DOOR, DOOR + 1)             # the three arches of the entrance
FIRST, LAST = DOOR - 5, DOOR + 5                # bays 4..14
Z0, Z1 = S.pilaster_z(FIRST - 1), S.pilaster_z(LAST)       # -22 and 22: the slice is cut on pilaster lines
FRONT = S.east_wall_x(DOOR)                     # 17: the wall line of the pavilion
BACK = FRONT - 7                                # 10: the slice's west wall
SCREEN_X = getattr(facade, "SCREEN_X", FRONT - 6)          # 11: the back wall of the vestibule
DOOR_TOP = S.STRING - 1                         # 5: the top row of the arches
PILASTER = S.WALL_E + S.DEPTH_PILASTER + 1.0    # 17.0: the face of a wing's pilasters
WALL = S.WALL_E + 1.0                           # 16.0: the face of a wing's wall
COURT_X = S.FRONT_COURT[2] + 2                  # 62: the paving reaches past the eye of V2

# ---- what hangs where -----------------------------------------------------------------------------------
LINE = (DOOR + 2, DOOR + 3, DOOR + 4, DOOR + 5)     # the pilasters that carry the line: 11..14, z 10..22
WIRE_Y = 5.55                   # the wire: under the string course's moulding, clear of its foot at 6.0
BOX_Y = 3.7                     # the junction box's middle: level with the base windows
PLATE_Y = 2.5                   # the plates: on the first row over the plinth, under the base windows' sills
NUMBERED = (LAST, LAST - 1, LAST - 2, LAST - 3, FIRST + 2, FIRST + 1, FIRST, FIRST - 1)    # 1..8, from the south
BELL = (FIRST + 2, 3.9)         # pilaster 6: the bell, its back plate ten pixels clear of the plate "5"
ROUNDEL = (FIRST + 1, 3.5)      # pilaster 5: the brass emblem, four pixels over the plate "6"
FLAG_FOOT = (30.5, 0.0, -23.5)  # in the court before the north end, out of the views of the plates
FLAG_HEIGHT = 7.0

# ---- stand-in lights (only while sky/lights is not in the tree) -----------------------------------------
# c220, cursor/c164-lights-wash-0fe3: the level a lit window has behind its glass, (a tall window,
# a low one), by the glass that stands in it; a source before the glass is THROUGH under that.
BEHIND = {B.WINDOW_LIT.block: (12, 12), B.WINDOW_FROSTED.block: (10, 9), B.WINDOW_CURTAIN.block: (8, 7)}
TWO = (B.WINDOW_LIT.block, B.WINDOW_FROSTED.block)      # a tall window of these has two sources
TALL, THROUGH = 4, 2
DOOR_LIGHT, HALL_LIGHT, SIDE_LIGHT = 14, 12, 10         # in the doorway; before the vestibule's back wall
DOOR_LIGHT_Y, HALL_LIGHT_Y = S.GROUND + 1, S.GROUND + 2


def _pilaster(k):
    """The middle of pilaster k's face on a wing, as (x, z): where a piece is hung on it."""
    return PILASTER, S.pilaster_z(k) + 0.5


# ---- the wall -------------------------------------------------------------------------------------------
def footprint():
    """The columns of the building's plan from the slice's west wall to the east wall line, between
    the two pilaster lines the slice is cut on."""
    return {(x, z) for z in range(Z0, Z1 + 1) for x in range(BACK, P.east_face(z) + 1)}


def _classify(x, z, outs):
    """The east front as main/facade classifies it: a pier on every pilaster line (also where the
    front steps: the return stays plain), the skeleton's bays between them. The three cut sides
    are plain wall."""
    if "east" not in outs:
        return None
    if P.on_pilaster(z):
        return O.Pier(out=("east",))
    return O.Bay("east", P.bays_at(z)[0], out="east")


def plan():
    """The slice's plan, the three bays of the entrance cut as arches from the ground to under
    the string course (the director's version B of the entrance)."""
    p = O.Plan(footprint(), _classify)
    for bay in ARCADE:
        p.door("east", bay, S.GROUND, DOOR_TOP, arch=B.ASHLAR_ROUGH)
    return p


def order():
    """main/facade's order for a stretch of wall that stands on its own: the parapet runs right
    through (no drum stands on this slice) and carries no rods, and no console hangs under the
    cornice where the emblem's tablet stands. facade.order(site=False) says all that once the
    front in the tree has it; until then the three things are set on the bands of facade.order()."""
    if "site" in inspect.signature(facade.order).parameters:
        return facade.order(site=False)
    bands = facade.order()
    for band in bands:
        if isinstance(band, O.Parapet):
            band.where, band.rod = None, None
        elif isinstance(band, O.Frieze):
            band.keys = lambda op: op.bay != DOOR
    return bands


def seat():
    """Where the great piece hangs: main/facade.emblem() once the front in the tree has it; until
    then the same nine blocks -- a tablet between the two pilasters of the entrance, in their
    plane, through frieze and cornice and one row above."""
    give = getattr(facade, "emblem", None)
    if give is not None:
        return give()
    x = FRONT + S.DEPTH_PILASTER
    ys, zs = range(S.FRIEZE, S.CORNICE + 2), P.window_rows(DOOR)
    middle = (x, ys[1], zs[1])
    cells = [(x, y, z) for y in ys for z in zs if (x, y, z) != middle]
    return dict(cells=cells + [middle], out="east", face_x=x + 1.0)


def _entrance(c, p):
    """The arcade as c206's branch builds it. The lining of the return walls is cut through behind
    the last column of bays 8 and 10, in the rows of the arch and of the great window; an iron
    gate (bars) stands in the glass plane of the two side arches; the heads of the arches and of
    the great windows are shut over their crowns with a hung slab; each arch has its key, a whole
    block in the string course."""
    rough, fine = B.ASHLAR_ROUGH, B.ASHLAR_FINE
    crown = getattr(facade, "CROWN", True)
    for bay in ARCADE:
        op = p.bays[("east", bay)]
        for cell in op.cells:
            n = 2
            while O.step(cell, op.out, -n) in p.leaf:
                x, z = O.step(cell, op.out, -n)
                for y in [*range(S.GROUND, DOOR_TOP + 1), *range(S.PANEL, S.WINDOW[1] + 1)]:
                    c.clear(x, y, z)
                n += 1
        if bay != DOOR:
            for x, z in op.behind(1):
                for y in range(S.GROUND, DOOR_TOP + 1):
                    c.set(x, y, z, B.IRON_BARS)
        if crown:
            for x, z in op.cells[1:-1]:
                c.set(x, DOOR_TOP, z, f"{rough.slab}[type=top]")
        x, z = O.step(op.middle(), op.out)
        c.set(x, S.STRING, z, fine.block)
    if crown:
        for op in p.openings:
            for x, z in op.cells[1:-1]:
                c.set(x, S.WINDOW[1], z, f"{fine.slab}[type=top]")


def _tablet(c):
    """Set the emblem's tablet and break the cornice round it, as main/facade does: nine blocks of
    plain dressed stone, no moulding and no gutter in front of them, a coping on top."""
    cells = seat()["cells"]
    top = max(y for _, y, _ in cells)
    for x, y, z in cells:
        c.set(x, y, z, B.ASHLAR_FINE.block)
    for x, z in {(x, z) for x, _, z in cells}:
        for y in (S.CORNICE, S.CORNICE + 1):
            c.clear(x + 1, y, z)
        c.set(x, top + 1, z, f"{B.ASHLAR_FINE.slab}[type=bottom]")


def _inside(c, p):
    """What closes the slice behind its front: the deck over it, the floor of the main storey, and
    behind the entrance the vestibule that main/facade builds as its stand-in for the hall -- a
    back wall of dressed stone and the hall's two cross walls as high as the string course, a
    strip one block proud of the back wall behind each pier of the arcade."""
    fine, panel = B.ASHLAR_FINE.block, B.ASHLAR_PANEL.block
    for x, z in p.leaf | p.core:
        c.set(x, S.ROOF_FLOOR, z, facade.DECK)
    for x, z in p.core:
        c.set(x, S.STRING, z, fine)
    z0, z1 = P.CROSS_Z
    strips = {S.pilaster_z(k) for k in (DOOR - 1, DOOR)}
    for y in range(S.GROUND, S.STRING + 1):
        for z in range(z0, z1 + 1):
            c.set(SCREEN_X, y, z, panel if z in strips else fine)
            if z in strips:
                c.set(SCREEN_X + 1, y, z, fine)
        for z in (z0, z1):
            for x in range(SCREEN_X + 1, P.east_face(z) + S.DEPTH_GLASS):
                c.set(x, y, z, fine)


# ---- the light ------------------------------------------------------------------------------------------
def _source(c, cell, level):
    """A light source in a cell that is free; says whether it was put there."""
    return c.set(cell[0], cell[1], cell[2], f"{B.LIGHT}[level={level}]", keep=True)


def _window_lights(c, windows):
    """The stand-in for sky/lights' windows. A lit window gets its source in the cell before the
    glass of its middle column (the recess), THROUGH under the level it has behind the glass, or
    behind the glass where the recess is taken (the bars of a base window); a tall window of
    bright or frosted glass has two, a row over the sill and a row under the head. The brightest
    glass lends each of its sources to the recess of the window on either side, as many levels
    lower as the two cells are apart."""
    bright = []
    for w in windows:
        if w["glass"] not in BEHIND:
            continue
        (y0, y1), (dx, dz) = w["y"], w["inward"]
        tall = y1 - y0 + 1 >= TALL
        level = BEHIND[w["glass"]][0 if tall else 1]
        mid = len(w["cells"]) // 2
        columns = sorted(w["cells"], key=lambda cell: abs(w["cells"].index(cell) - mid))
        before = []
        for y in (y0 + 1, y1 - 1) if tall and w["glass"] in TWO else (y0 + (y1 - y0) // 2,):
            for x, z in columns:
                if _source(c, (x - dx, y, z - dz), level - THROUGH):
                    before.append(((x - dx, y, z - dz), level - THROUGH))
                    break
            else:
                for x, z in columns:
                    if _source(c, (x + dx, y, z + dz), level):
                        break
        if w["glass"] == B.WINDOW_LIT.block:
            bright.append((w, before))
    for w, before in bright:
        dx, dz = w["inward"]
        for v in windows:
            if (v["front"], v["storey"], v["inward"]) != (w["front"], w["storey"], w["inward"]) \
                    or abs(v["bay"] - w["bay"]) != 1:
                continue
            for (x, y, z), level in before:
                nx, nz = min(((cx - dx, cz - dz) for cx, cz in v["cells"]),
                             key=lambda q: (abs(q[0] - x) + abs(q[1] - z), q))
                if (nx - x) * dx + (nz - z) * dz:
                    continue                            # a neighbour in a wall that is set back
                row = min(max(y, v["y"][0]), v["y"][1])
                lent = level - abs(nx - x) - abs(nz - z) - abs(row - y)
                if lent >= 1:
                    _source(c, (nx, row, nz), lent)


def _lights(c, windows):
    """The slice under the building's lights (see the module's note). The vestibule is main/facade's
    stand-in for a hall with its lamps on: where sky/lights does not light it (it is not in the
    tree, or the star hall has moved into the real building) its three sources are set here."""
    kit = importlib.util.find_spec("scenes.obs.sky.lights") is not None
    if kit:
        from scenes.obs.sky import _lightkit
        _lightkit.dress(c)
    if not kit or getattr(facade, "furnished", lambda: False)():
        for bay in ARCADE:
            level = HALL_LIGHT if bay == DOOR else SIDE_LIGHT
            _source(c, (SCREEN_X + 1, HALL_LIGHT_Y, S.bay_center_z(bay)), level)
    if not kit:
        _source(c, (FRONT + S.DEPTH_GLASS, DOOR_LIGHT_Y, S.bay_center_z(DOOR)), DOOR_LIGHT)
        _window_lights(c, windows)


# ---- what the package hangs on it ---------------------------------------------------------------------
def _line(c):
    """The line of the south wing. It comes out of the wall under the junction box on pilaster 11,
    climbs in a conduit to a lead-in under the string course, runs three bays on two insulators
    and goes back into the wall through the lead-in on pilaster 14: no end is left open. It does
    not start at the entrance lamp on pilaster 10: that face stands two blocks further out."""
    points = [(x, WIRE_Y, z) for x, z in (_pilaster(k) for k in LINE)]
    return electrics.run(c, points, facing="east", ends=(("box", BOX_Y), None))


def _plates(c):
    """A number plate on every pilaster of the wings, the voltage plate on the wall beside the
    junction box (it is a block and a half wide: a pilaster is too narrow for it), the bell and
    the small emblem on the north wing."""
    n = 0
    for i, k in enumerate(NUMBERED):
        x, z = _pilaster(k)
        n += signs.plate(c, str(i + 1), (x, PLATE_Y, z), facing="east")
    n += signs.plate(c, "220V", (WALL, PLATE_Y, S.pilaster_z(LINE[0]) - 1.0), facing="east")
    x, z = _pilaster(BELL[0])
    n += electrics.place(c, "bell", (x, BELL[1], z), facing="east")
    x, z = _pilaster(ROUNDEL[0])
    n += signs.place(c, "emblem", (x, ROUNDEL[1], z), facing="east")
    return n


def build():
    c = Canvas()
    c.box(BACK - 2, S.PAVING_Y, Z0 - 6, COURT_X, S.PAVING_Y, Z1 + 6, site.FIELD)
    c.box(site.FOOT_STRIP_X, S.PAVING_Y, Z0 - 6, site.FOOT_STRIP_X, S.PAVING_Y, Z1 + 6, site.STRIP)
    p = plan()
    windows = O.build(c, p, order(), glass=facade.glass)
    _entrance(c, p)
    _tablet(c)
    _inside(c, p)
    # The entrance's pair on the pilasters beside the arcade and the pair of street lamps nearest
    # the door, whatever the switch of props/lamps says: the lamps further out on the way and the
    # ground lamps at the armillary's feet belong to a court this slice does not have
    lamps.dress(c, False)
    n = lamps.build(c)
    n += signs.great(c, seat(), signs.VERSIONS[signs.VERSION])
    n += _line(c)
    n += _plates(c)
    n += signs.flagpole(c, FLAG_FOOT, height=FLAG_HEIGHT)
    _lights(c, windows)
    lit = sky.build(c, (0, 0, 0))   # A2's light sources go in last, when everything that glows is in place
    c.entity_counts = {"props": n, "sky": lit or 0}
    return c


def write_pack(pack_dir):
    """The repainted stone, glass and iron the pieces are judged against, and the pictures of the
    map's sky: the slice stands in the map's hour (mood.py), and without them the game's own sun
    lies on the open horizon behind the court."""
    return list(materials.pack(pack_dir) or []) + list(sky.pack(pack_dir) or [])


# ---- the cameras ------------------------------------------------------------------------------------------
V2 = getattr(S, "V2", dict(pos=(58.5, 1.7, S.AXIS_Z), look_at=(17, 19, S.AXIS_Z)))     # the director's view


def shots():
    """The great emblem from the director's axis view, from six blocks in front, from the court
    twenty blocks out in the three lights, and from the side; the whole entrance; the line along
    the south wing and each of its fittings; the number plates from afar, along the wall and from
    three blocks; the bell; the flag from both sides."""
    out = []

    def shot(name, pos, look_at, time=TIME):
        out.append({"name": name, "pos": [round(float(v), 2) for v in pos],
                    "look_at": [round(float(v), 2) for v in look_at], "time": time})

    eye = S.GROUND + S.EYE
    tablet = seat()
    ys = [y for _, y, _ in tablet["cells"]]
    ex, ey, ez = tablet["face_x"], (min(ys) + max(ys) + 1) / 2.0, S.AXIS_Z      # the great emblem's middle
    shot("v2_axis", V2["pos"], V2["look_at"])
    shot("emblem_front", (ex + 6.0, ey, ez), (ex, ey, ez))
    # from the court the eye is held a little under the emblem, so that the two street lamps
    # before the door stand in the picture from foot to globe
    court = (ex, ey - 3.5, ez)
    shot("emblem_court", (ex + 20.0, eye, ez), court)
    shot("emblem_court_deep", (ex + 20.0, eye, ez), court, TIME_DEEP)
    shot("emblem_court_glow", (ex + 20.0, eye, ez), court, TIME_GLOW)
    shot("emblem_oblique", (ex + 14.0, eye, ez + 14.0), (ex, ey, ez))
    shot("entrance", (ex + 16.5, eye, ez), (ex - 1.0, 7.5, ez))

    box_x, box_z = _pilaster(LINE[0])
    end_x, end_z = _pilaster(LINE[-1])
    mid_z = (box_z + end_z) / 2.0
    shot("line", (box_x + 10.0, eye, mid_z), (box_x, 4.2, mid_z))
    shot("box_near", (box_x + 3.0, eye, box_z), (box_x, 3.6, box_z - 0.3))
    ins_x, ins_z = _pilaster(LINE[1])
    shot("insulator_near", (ins_x + 2.2, 4.6, ins_z - 1.2), (ins_x + 0.2, WIRE_Y - 0.15, ins_z))
    shot("elbow_near", (end_x + 2.4, 4.7, end_z - 1.3), (end_x + 0.1, WIRE_Y - 0.2, end_z))
    shot("plates_row", (box_x + 6.0, eye, end_z + 4.5), (box_x, 2.6, box_z + 2.5))

    north_z = (_pilaster(NUMBERED[4])[1] + _pilaster(NUMBERED[7])[1]) / 2.0
    shot("plates_far", (PILASTER + 12.0, eye, north_z), (PILASTER, PLATE_Y, north_z))
    x, z = _pilaster(ROUNDEL[0])
    shot("plate_near", (x + 2.4, eye, z + 0.8), (x, 3.0, z))    # the bell, a bay south, stays out of the picture
    x, z = _pilaster(BELL[0])
    shot("bell_near", (x + 2.6, 3.3, z + 1.3), (x, BELL[1] + 0.1, z))

    fx, fy, fz = FLAG_FOOT
    cloth = (fx, fy + FLAG_HEIGHT - 0.75, fz + 0.8)     # the middle of the cloth: it flies south of the pole
    shot("flag", (fx + 8.0, eye, fz - 3.5), (fx, fy + 3.3, fz + 0.5))
    shot("flag_near", (fx + 3.1, 4.6, fz + 1.5), cloth)
    shot("flag_front", (fx - 3.1, 4.6, fz + 0.1), cloth)
    return out

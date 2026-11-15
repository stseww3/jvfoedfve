"""main/dome: the rotunda's drum and the great dome's shell, the centre of V1, V2 and V12
(plan/packages/main/dome.md; plan/ART-PLAN.md 5.2).

The geometry is main/_dome.py; this module is the package the category finds. It lays the drum
from the rotunda's cornice up (y 16), the gallery, the dome and what shuts the slit. One block
thick: the room inside is interiors', the track's rollers and the shutter's chains are machines',
the round frames of the windows are props', the two door leaves the roof's.

Two versions (VERSION); the map is built with b, the director's choice of 11-16, and a is kept.
The test scene obs_main_dome shows the map's version, obs_main_dome_a the other, obs_main_dome_slit
the slit of both:

    a   twenty flush seams, the foot of each stained where the water runs off it; two leaves
        that part sideways
    b   eight main ribs of the darker copper, half a block proud on the dome's steep foot and
        flush above it; a slatted curtain drawn up from the slit's foot

The slit looks west and stands open (SLIT; ART-PLAN 5.2: the telescope looks out of it); "half" and
"closed" are there for whoever animates or photographs it.

    python -m scenes.obs.main.dome [a|b] [open|half|closed] [check]

prints the shell as text -- plans, the dome from above, sections, elevations -- and then checks
what can be told without a picture; with "check" it only checks. The check always goes through
both versions and the three states of the slit.
"""
import sys

from artkit.canvas import Canvas

from ..common import blocks as B
from . import _dome
from . import _order as O

D = _dome

ORDER = 60                  # after the shell and the roof terraces: the drum stands on them
VERSION = D.VERSION         # "b"
SLIT = "open"


def _glass(front, bay, storey):
    from . import facade                    # the lit windows are told in one place for the whole building
    return facade.glass(front, bay, storey)


def build(canvas, origin=(0, 0, 0), version=None, slit=None):
    """The drum, the gallery, the dome and what shuts its slit. No display entities."""
    D.build(canvas, origin, glass=_glass, version=version or VERSION, slit=slit or SLIT)
    return 0


# --- self-check and drawings ----------------------------------------------------------------------------
TOP_ROW = int(D.CROWN)                      # 38: the last row anything stands in


def _column(c, col):
    """The rows of a column of the dome that hold a block, from the ring beam up, and the height
    of its top face (None for an empty column)."""
    x, z = col
    rows = [y for y in range(D.SKIRT_Y, TOP_ROW + 3) if c.has(x, y, z)]
    face = rows[-1] + (0.5 if "slab" in c.get(x, rows[-1], z) else 1.0) if rows else None
    return rows, face


def check():
    """What can be told without a picture; returns the findings as lines (none is good)."""
    out = []
    p = D.plan()
    plates = D.plates()
    slit = sorted(col for col in plates if D._in_slit(*col))
    edge = sorted(col for col in plates if any(O.step(col, d) not in plates for d in O.SIDES))
    reach = D.R + 2
    for version in D.VERSIONS:
        for state in D.STATES:
            tag = f"{version}/{state}"
            c = Canvas()
            windows = D.build(c, version=version, slit=state)
            name = lambda x, y, z, c=c: (c.get(x, y, z) or "air").partition("[")[0]
            cols = {col: _column(c, col) for col in plates}
            shut = {col for col in slit if cols[col][0] and cols[col][0][-1] > D.SILL_Y}

            # 1. the extent: the drum's first course to the crown, the gallery's reach and no more
            (x0, y0, z0), (x1, y1, z1) = c.bounds()
            if (y0, y1) != (D.ATTIC, TOP_ROW):
                out.append(f"{tag} rows: the blocks span y {y0}..{y1}, not {D.ATTIC}..{TOP_ROW}")
            if (x0, x1, z0, z1) != (D.CX - reach, D.CX + reach, D.CZ - reach, D.CZ + reach):
                out.append(f"{tag} reach: the blocks span x {x0}..{x1}, z {z0}..{z1}, not {reach} round the centre")
            # 2. the top: one cast block on the axis, the only thing as high
            high = sorted(col for col, (rows, face) in cols.items() if face is not None and face > D.CROWN + 0.5)
            if high != [(D.CX, D.CZ)] or name(D.CX, TOP_ROW, D.CZ) != D.CAST:
                out.append(f"{tag} apex: higher than the crown's plates are {high}, not the cast block alone")
            # 3. the outline: nothing stands more than half a block over the plates (the boss a whole
            #    one); above the foot's steep courses nothing stands over them at all but the crown
            #    and, west of it, what shuts the slit -- that is the top line of V1, V2 and V11
            flush = D.R - D.PROUD_COURSES[version]
            for col, (rows, face) in sorted(cols.items()):
                over = 1.0 if col == (D.CX, D.CZ) else 0.5
                if face is not None and face > plates[col] + over:
                    out.append(f"{tag} outline: column {col} stands {face - plates[col]} over the plates")
                elif (face is not None and face > plates[col] and D._ring(*col) <= flush
                      and col not in D.CAP and col[0] > D.SLIT_HEAD):
                    out.append(f"{tag} outline: column {col} stands over the plates above the foot's courses")
            # 4. the slit: open above its sill, shut all the way, or the half of it that the state says
            if state == "open" and shut:
                out.append(f"{tag} slit: something stands in the open slit at {sorted(shut)[:6]}")
            if state == "closed" and len(shut) != len(slit):
                out.append(f"{tag} slit: left open at {sorted(set(slit) - shut)[:6]}")
            if state == "half" and not 0 < len(shut) < len(slit):
                out.append(f"{tag} slit: {len(shut)} of its {len(slit)} columns are shut, that is not half open")
            # 5. the shell is closed everywhere else: no column missing or broken, no gap under a
            #    column over a neighbour, the ring beam under every column of the dome's edge
            for col, (rows, face) in sorted(cols.items()):
                if col in slit and col not in shut and col not in edge:
                    continue                            # the open slit
                if not rows or rows != list(range(rows[0], rows[-1] + 1)):
                    out.append(f"{tag} shell: column {col} is missing or broken: rows {rows}")
                    continue
                if col in edge and rows[0] != D.SKIRT_Y:
                    out.append(f"{tag} shell: column {col} on the dome's edge does not stand on the ring beam")
                for d in O.SIDES:
                    n = O.step(col, d)
                    if n in cols and cols[n][1] is not None and rows[0] > cols[n][1]:
                        if n in slit and n not in shut:
                            continue                    # beside the open slit the shell shows its thickness
                        out.append(f"{tag} shell: a gap under column {col} over its neighbour {n}")
            # 6. the ring beam: riveted iron all round, twenty axle boxes in it, one to a seam
            ring = {col: name(col[0], D.SKIRT_Y, col[1]) for col in edge}
            if any(what not in (D.SKIRT, D.AXLE_BOX) for what in ring.values()):
                out.append(f"{tag} ring beam: the dome's edge at y {D.SKIRT_Y} is not iron all round")
            boxes = {col for col, what in ring.items() if what == D.AXLE_BOX}
            if boxes != D.axle_boxes() or len(boxes) != D.GORES:
                out.append(f"{tag} ring beam: {len(boxes)} axle boxes, not one under each of the {D.GORES} seams")
            # 7. the gallery: gutter, cove and posts; nothing else stands over it
            if any(name(x, D.DRUM_TOP, z) != D.GUTTER.slab for x, z in p.front):
                out.append(f"{tag} gallery: the gutter at y {D.DRUM_TOP} is not copper slabs all round")
            if any(name(x, D.DRUM_TOP, z) != D.WALK.stairs for x, z in p.far):
                out.append(f"{tag} gallery: the cove at y {D.DRUM_TOP} is not iron stairs all round")
            stand = sorted((x, z) for x, z in p.front | p.far if c.has(x, D.DRUM_TOP + 1, z))
            if stand != D.posts(p) or any(name(x, D.DRUM_TOP + 1, z) != D.POST for x, z in stand):
                out.append(f"{tag} gallery: what stands on it at y {D.DRUM_TOP + 1} is not the posts alone")
            if any(O.step(a, d) in stand for a in stand for d in O.SIDES):
                out.append(f"{tag} gallery: two posts stand side by side")
            # 8. the drum: twenty windows, a niche under all but the two over the doors, the doors
            #    open from the roof to the room, nothing inside the inner leaf
            glazed = 0
            for w in windows:
                (x, z), = w["cells"]
                front = O.step((x, z), w["inward"], -1)
                if "glass" in name(x, D.WINDOW_Y, z) and not c.has(front[0], D.WINDOW_Y, front[1]):
                    glazed += 1
            if glazed != D.GORES:
                out.append(f"{tag} drum: {glazed} windows, not {D.GORES}")
            sunk = D.niches(p)
            if len(sunk) != D.GORES - len(D.DOORS["cells"]):
                out.append(f"{tag} drum: {len(sunk)} niches, not one under every window but the doors'")
            for front, back in sunk:
                for y in O.rows(D.NICHE_Y):
                    panel = back if D.NICHE_SUNK else front
                    open_front = not c.has(front[0], y, front[1])
                    if name(panel[0], y, panel[1]) != B.ASHLAR_PANEL.block or open_front != D.NICHE_SUNK:
                        out.append(f"{tag} drum: the panel under the window at {front}, y {y} is not where it belongs")
            for run in D.doors(p):
                step = (run[1][0] - run[0][0], run[1][1] - run[0][1])
                way = [O.step(run[0], step, -1)] + run + [O.step(run[-1], step)]
                if way[-1] not in p.core:
                    out.append(f"{tag} doors: the doorway at {run[0]} does not reach the room")
                for x, z in way:
                    for y in O.rows(tuple(D.DOORS["y"])):
                        if c.has(x, y, z):
                            out.append(f"{tag} doors: something stands in the doorway at ({x}, {y}, {z})")
            if len(D.doors(p)) != len(D.DOORS["cells"]):
                out.append(f"{tag} doors: {len(D.doors(p))} doorways, not {len(D.DOORS['cells'])}")
            for x, z in p.core:
                if any(c.has(x, y, z) for y in range(D.ATTIC, D.SKIRT_Y + 1)):
                    out.append(f"{tag} room: something stands inside the inner leaf at ({x}, {z})")
            # 9. the seams: version a draws them with the uncut sheet, and has the darker copper
            #    only where a run stains a seam; version b draws its ribs with the darker copper
            #    and has no sheet
            names = set(c.count())
            dark = set(D.RIB.all())
            if version == "a":
                astray = sorted((x, y, z) for (x, z), (rows, face) in cols.items() for y in rows
                                if name(x, y, z) in dark and not (D._lined(x, z, "a") and D._stained(x, z, "a")))
                if D.SHEET not in names or astray:
                    out.append(f"{tag} seams: version a has no uncut sheet, or the darker copper off its runs: {astray[:6]}")
            if version == "b" and (D.RIB.block not in names or D.SHEET in names):
                out.append(f"{tag} seams: version b does not draw its ribs with the darker copper alone")
    return out


def _row(c, y):
    """One row of the scene from above (north up; . nothing)."""
    reach = D.R + 2
    xs = range(D.CX - reach, D.CX + reach + 1)
    lines = ["        " + "".join("%d" % (abs(x) % 10) for x in xs)]
    for z in range(D.CZ - reach, D.CZ + reach + 1):
        lines.append("z %4d  %s" % (z, "".join(O.mark(c.get(x, y, z)) if c.has(x, y, z) else "." for x in xs)))
    return "\n".join(lines)


def _heights(c):
    """The dome from above: for every column the height of its top face over the ring beam's foot,
    in half blocks (28 is the plates round the axis, 29 the crown, 30 the boss), and the letter of
    what lies there; . the open slit."""
    body = O.disc(D.CX, D.CZ, D.R)
    xs = range(D.CX - D.R, D.CX + D.R + 1)
    lines = ["        " + "".join("%3d" % x for x in xs)]
    for z in range(D.CZ - D.R, D.CZ + D.R + 1):
        row = []
        for x in xs:
            rows, face = _column(c, (x, z))
            if (x, z) not in body:
                row.append("   ")
            elif not rows:
                row.append("  .")
            else:
                row.append("%2d%s" % (round(2 * (face - D.SKIRT_Y)), O.mark(c.get(x, rows[-1], z))))
        lines.append("z %4d  %s" % (z, "".join(row).rstrip()))
    return "\n".join(lines)


def _drawings(version, state):
    O.MARKS.setdefault(D.CAST, "A")
    O.MARKS.setdefault(D.AXLE_BOX, "W")
    c = Canvas()
    D.build(c, version=version, slit=state)
    reach = D.R + 3
    xs = (D.CX - reach, D.CX + reach)
    zs = (D.CZ - reach, D.CZ + reach)
    ys = (D.ATTIC - 1, TOP_ROW + 1)
    print(f"VERSION {version}, the slit {state}\n")
    print("PLAN of the drum (north up; # wall line, : inner leaf, P pilaster, w window, + the gallery's cove)\n")
    print(O.drawing(D.plan()))
    for y, what in ((D.NICHE_Y[0], "the niches and the two doors"), (D.WINDOW_Y, "the windows"),
                    (D.CORBEL_Y, "the corbel course"), (D.DRUM_TOP, "the gallery: track, gutter, cove"),
                    (D.SKIRT_Y, "the ring beam and the posts")):
        print(f"\nROW y {y}, {what} (north up):\n")
        print(_row(c, y))
    print("\nFROM ABOVE: the top face of every column of the dome, in half blocks over y 24, and what it is\n")
    print(_heights(c))
    print(f"\nSECTION through the slit (z = {D.CZ}, west on the left):\n")
    print(O.section(c, "z", D.CZ, xs, ys))
    print(f"\nSECTION beside the slit (z = {D.CZ + D.SLIT_HALF + 1}, west on the left):\n")
    print(O.section(c, "z", D.CZ + D.SLIT_HALF + 1, xs, ys))
    print(f"\nSECTION across the slit (x = {D.CX - 6}, north on the left):\n")
    print(O.section(c, "x", D.CX - 6, zs, ys))
    print(f"\nSECTION across the crown (x = {D.CX}, north on the left):\n")
    print(O.section(c, "x", D.CX, zs, ys))
    print("\nEAST ELEVATION, from the court (south on the left):\n")
    print(O.elevation(c, "east", zs, ys, xs[1], xs[0]))
    print("\nThe same, how far back the first block stands (1 = the gallery's cove on the axis, 3 = the wall):\n")
    print(O.elevation(c, "east", zs, ys, xs[1], xs[0], depth=True))
    print("\nSOUTH ELEVATION (west on the left):\n")
    print(O.elevation(c, "south", xs, ys, zs[1], zs[0]))
    print("\nWEST ELEVATION, the slit (north on the left):\n")
    print(O.elevation(c, "west", zs, ys, xs[0], xs[1]))
    print("\nLetters: F dressed ashlar, P sunk panel, D dark window, C copper gutter, H iron plate (the track),")
    print("I riveted iron, W cast iron (an axle box), ! post, V verdigris plate, G the uncut sheet (version a's")
    print("seams), X the darker copper (version b's ribs and slats), A the cast boss.")
    print("Small letters are the same family's stairs and slabs.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "check" not in args:
        _drawings(next((a for a in args if a in D.VERSIONS), VERSION), next((a for a in args if a in D.STATES), SLIT))
        print()
    found = check()
    print("\n".join(found) if found else
          "self-check: extent, apex, outline, slit, shell, ring beam, gallery, drum, doors and seams -- all good, "
          "versions a and b, the slit open, half open and closed")
    sys.exit(1 if found else 0)

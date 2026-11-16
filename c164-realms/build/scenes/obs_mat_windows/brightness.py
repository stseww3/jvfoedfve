"""Re-measure the windows' brightness, in the cloud, against c177's ladder (group g2 #89/#90).

    python -m scenes.obs_mat_windows.brightness        prints the table and exits 1 if any tier is out

Lit windows are drawn at emission 15 with shade and ao off (materials/windows.py LIT), so what shows
on screen is exactly the texture colour: a lit window's average brightness is the Rec.601 luma of its
picture, bars included. (Check: #ffc65a reads 0.79, #caa356 reads 0.65, as c177 has it.) Dark windows
are ordinary blocks the sky multiplies, so their shown brightness is the texture luma times c177's
east-front multipliers.

c177's targets, whole window with the glazing bars counted in:
    LIT      ~0.65   (glass #ffc65a, kept; not raised to #ffe9a6)
    FROSTED  0.52 - 0.55
    CURTAIN  0.38 - 0.42
    DARK     ~0.08 shown (A),  ~0.05 (B)
    BLIND    ~0.073 shown (A)
Both versions of the lit windows sit on the same ladder.

The linings of the lit windows (materials/windows.py, the room side) are measured as well: their
pictures in their own colours, held to what linings() says below. So is the furnace window, the
three rows of it stacked as a bay shows them: see furnace().
"""
import itertools
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scenes.obs.common import palette as P
from scenes.obs.materials import windows as W

COEF = np.array([0.299, 0.587, 0.114])                 # Rec.601 luma, as c177 reads the pictures
SKY = {"A": np.array([0.25, 0.29, 0.44]), "B": np.array([0.15, 0.18, 0.30])}   # east front, c177 g2 #82/#117
TARGET = {"LIT": (0.62, 0.67), "FROSTED": (0.52, 0.55), "CURTAIN": (0.38, 0.42)}


def _list(x):
    return x if isinstance(x, list) else [x]


def _bars(version):
    m = np.zeros((W.TILE, W.TILE), bool)
    for x in W._BARS[version]["cols"]:
        m[:, x] = True
    for y in W._BARS[version]["rows"]:
        m[y, :] = True
    return m


def luma(pics, mask=None, mult=None):
    """Average Rec.601 luma (0-1) over one or more pictures; `mask` keeps pixels, `mult` scales rgb."""
    vals = []
    for px in _list(pics):
        rgb = np.asarray(px)[..., :3].astype(float)
        if mult is not None:
            rgb = rgb * mult
        rgb = rgb.reshape(-1, 3) if mask is None else rgb[mask]
        vals.append((rgb @ COEF).mean() / 255.0)
    return float(np.mean(vals))


def table():
    rows, bad = [], []
    for v in W.VERSIONS:
        glass = ~_bars(v)
        for role, face in (("LIT", W.lit_face(v)), ("FROSTED", W.frosted_face(v)), ("CURTAIN", W.curtain_face(v))):
            whole, only = luma(face), luma(face, glass)
            lo, hi = TARGET[role]
            ok = lo <= whole <= hi
            rows.append((v, role, whole, only, f"{lo:.2f}-{hi:.2f}", "ok" if ok else "OUT"))
            if not ok:
                bad.append(f"windows {v} {role}: whole {whole:.3f} not in {lo:.2f}-{hi:.2f}")
        for role, face, tgt in (("DARK", W.dark_face(v), 0.08), ("BLIND", W.blind_face(v), 0.073)):
            rows.append((v, role, luma(face, mult=SKY["A"]), luma(face, mult=SKY["B"]), f"~{tgt:.3f} (A)", "sky"))
    return rows, bad


# The linings (A0, g2 #32717): what a lit window shows to the room behind it. A lining gives no
# light, so its figure is the picture in its own colours, and the room's lamps and the game's
# shading only take from it. Every piece of every kind is measured, in the largest size. Held to:
#   - no colour of the two light ramps;
#   - the night glass and the drawn curtain under the dimmest lit window;
#   - the unlit frosted glass well lighter than the night glass that lines WINDOW_LIT, and under
#     the darkest stone of the wall it stands in. Milk glass is pale under the lamps of a room: at
#     the first rendering a grey under the dimmest lit window showed as dark as the night glass
#     beside it and read as a plate of iron. Under the same lamps it cannot outshine the wall, so
#     it is no light;
#   - the pieces of a kind within a small step of each other: the rail and the hem of a curtain
#     do not make its head or its foot a band of another brightness;
#   - the frosted glass of a panelled room (m2, #65185) level with what stands round it there:
#     under the lightest board of the panelling, and within a small step of the night glass that
#     the dark windows beside it show. On a wall of dark wood the pale one was the lightest plane
#     of the room; this one is told from the night glass by its hue, not by its brightness.
LIGHT_RAMPS = ("glow", "opal")
LINING_TOP = {"lit": TARGET["CURTAIN"][0], "curtain": TARGET["CURTAIN"][0],
              "frosted": float(np.array(P.colour("ashlar", 0)) @ COEF) / 255.0,
              W.DEEP: float(np.array(P.colour("dark_wood", 4)) @ COEF) / 255.0}
FROSTED_OVER = 0.12             # the unlit frosted glass is at least this much lighter than the night glass
DEEP_WITHIN = 0.05              # the deep frosted glass is this near to the night glass, over or under
PIECES_WITHIN = 0.02


def linings():
    rows, bad = [], []
    light = {P.colour(ramp, i) for ramp in LIGHT_RAMPS for i in range(len(P.RAMPS[ramp]))}
    for v in W.VERSIONS:
        whole = {}
        for kind, pieces in W.PIECES.items():
            each = []
            for variant, ends in enumerate(pieces):
                px = W.lining_picture(kind, W.PIECE, W.PIECE, variant, v)
                used = {tuple(int(c) for c in rgb) for rgb in np.unique(px[..., :3].reshape(-1, 3), axis=0)}
                each.append(luma(px))
                ok = not (used & light) and each[-1] < LINING_TOP[kind]
                rows.append((v, kind + ends, each[-1], len(used), "ok" if ok else "OUT"))
                if used & light:
                    bad.append(f"lining {v} {kind}{ends}: {len(used & light)} colours of the light ramps")
                if each[-1] >= LINING_TOP[kind]:
                    bad.append(f"lining {v} {kind}{ends}: whole {each[-1]:.3f}, not under {LINING_TOP[kind]:.2f}")
            whole[kind] = max(each)
            if max(each) - min(each) > PIECES_WITHIN:
                bad.append(f"lining {v} {kind}: its pieces run from {min(each):.3f} to {max(each):.3f}, "
                           f"more than {PIECES_WITHIN} apart")
        if whole["frosted"] - whole["lit"] < FROSTED_OVER:
            bad.append(f"lining {v}: frosted {whole['frosted']:.3f} is not {FROSTED_OVER} lighter than the "
                       f"night glass {whole['lit']:.3f}")
        if abs(whole[W.DEEP] - whole["lit"]) > DEEP_WITHIN:
            bad.append(f"lining {v}: the deep frosted glass {whole[W.DEEP]:.3f} is more than {DEEP_WITHIN} from "
                       f"the night glass {whole['lit']:.3f}")
    return rows, bad


# The furnace window (A0, g2 #37112, #574): three blocks from the sill up that show as one sheet.
# The game mixes the pictures of a row by position, so every way of stacking them is measured.
# Held to:
#   - the mean and the median of the whole window not over the drawn curtain's 0.40;
#   - no colour but the two deepest ambers, the dark wood, the darkest iron and the bar;
#   - the glass darker band after band from the sill to the head, a band being the lower or the
#     upper half of a block's glass: across the joints of the blocks as within them, which is what
#     makes three rows one sheet and not three stripes (a light that is dirtier than its height
#     does not upset it; a block that ran from light to dark by itself would);
#   - the last row of pixels under the head near a dark window;
#   - the paler amber, the fire's own band, in the sill row and thinning out through the lower
#     half of the second: none above that;
#   - the rows at the levels the board asked for, and the fire uneven along the sill: see sill().
FURNACE_TOP = 0.40
FURNACE_HEAD = 0.12
FURNACE_TONES = ([("glow", 0), ("glow", 1), ("iron", 0), W.BAR]
                 + [("dark_wood", i) for i in range(len(P.RAMPS["dark_wood"]))])


def _pale(px):
    """Where a picture shows the paler amber: [(y, x)]."""
    return [(int(y), int(x)) for y, x in np.argwhere((np.asarray(px)[..., :3] == P.colour("glow", 1)).all(axis=-1))]


# The levels of the rows (cr2 #78188, a1 #78449: read off the board's V6 in Rec.709, the glass of
# a picture with its bars left out) and the fire along the sill. Held to:
#   - the glass of every picture of the sill row at 0.60 to 0.64: the paler amber with the deeper
#     one in points, not half and half, and nothing of the yellow of a lamp;
#   - the glass of the second row a quarter lighter than it was before the board asked (x 1.23 of
#     SECOND_WAS);
#   - the third row as it was;
#   - the fire uneven along the sill, as it is strong in one place and low in the next (A0 #574):
#     no two pictures of the sill row show the same count of pixels that are not the paler amber,
#     or a bay would have one foot twice.
SILL_GLASS = (0.60, 0.64)
SECOND_WAS = {"a": 0.3395, "b": 0.330}                  # the mean of its two pictures, at fb4a04fc
SECOND_UP, SECOND_WITHIN = 1.23, 0.012
THIRD_WAS = {"a": (0.194, 0.197), "b": (0.186, 0.187)}  # its two pictures, at fb4a04fc
THIRD_WITHIN = 0.001


def sill():
    """The rows of the furnace window at the levels the board asked for, and the fire uneven along
    the sill: ([(version, [pixels of each sill picture's glass that are not the paler amber], flag)], faults)."""
    rows, bad = [], []
    pale = np.array(P.colour("glow", 1))
    for v, r, means, _ in read709():
        name = ("sill", "second", "third")[r]
        for k, mean in enumerate(means):
            if r == 0:
                lo, hi = SILL_GLASS
            elif r == 1:
                lo, hi = (SECOND_UP * SECOND_WAS[v] - SECOND_WITHIN, SECOND_UP * SECOND_WAS[v] + SECOND_WITHIN)
            else:
                lo, hi = (min(THIRD_WAS[v]) - THIRD_WITHIN, max(THIRD_WAS[v]) + THIRD_WITHIN)
            if not lo <= mean <= hi:
                bad.append(f"furnace {v} {name} row, picture {k}: its glass reads {mean:.3f}, "
                           f"not {lo:.3f} to {hi:.3f}")
        if r == 0:
            glass = ~_bars(v)
            counts = [int(((np.asarray(px)[..., :3] != pale).any(axis=-1) & glass).sum())
                      for px in W.furnace_face(v)[0]]
            even = len(set(counts)) != len(counts)
            rows.append((v, counts, "OUT" if even else "ok"))
            if even:
                bad.append(f"furnace {v}: the sill pictures show {counts} pixels that are not the paler amber; "
                           f"no two are to show the same")
    return rows, bad


# The dither of the furnace window (A0 #574): the order in which the pixels of a light turn to the
# darker tone. Held to, for every light:
#   - a row holds each of the seven ranks once and a column holds them equally often: a tone thins
#     out evenly, with no fold down the glass and no slat across it;
#   - no two pixels of one rank touch, not even at a corner: a thin scatter is points, not strokes;
#   - with two neighbouring ranks on, at most one point in KNOTTED has two or more neighbours on:
#     where points meet it is two of them, as dust lies, and not a hook or a line of three;
#   - no two lights of a window alike.
RANKS = 7
KNOTTED = 8


def _touching(on):
    """For every pixel, how many of its eight neighbours are on; nothing lies beyond the light."""
    h, w = on.shape
    wide = np.zeros((h + 2, w + 2), int)
    wide[1:-1, 1:-1] = on
    return sum(wide[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)


def dither():
    rows, bad = [], []
    for v in W.VERSIONS:
        seen, pairs, knots = [], 0, 0
        for row in range(W.FURNACE_ROWS):
            for variant in range(len(W._SOOT[v][row])):
                for n, (x0, y0, x1, y1) in enumerate(W._LIGHTS[v]):
                    serial = (4 * row + variant) * len(W._LIGHTS[v]) + n
                    ranks = np.array(W._ranks(serial, x1 - x0 + 1, y1 - y0 + 1))
                    label = f"furnace {v} row {row} picture {variant} light {n}"
                    even = (all(sorted(line) == list(range(RANKS)) for line in ranks.tolist())
                            and all((ranks.T == r).sum(axis=1).tolist() == [ranks.shape[0] // RANKS] * ranks.shape[1]
                                    for r in range(RANKS)))
                    if not even:
                        bad.append(f"{label}: a row or a column does not hold the seven ranks evenly")
                    for r in range(RANKS):
                        one = ranks == r
                        touch = int((one * _touching(one)).sum()) // 2
                        two = one | (ranks == (r + 1) % RANKS)
                        knot = int((two & (_touching(two) >= 2)).sum())
                        pairs, knots = max(pairs, touch), max(knots, knot)
                        if touch:
                            bad.append(f"{label}: {touch} pairs of pixels of rank {r} touch")
                        if knot * KNOTTED > int(two.sum()):
                            bad.append(f"{label}: ranks {r} and {(r + 1) % RANKS} on, {knot} of {int(two.sum())} points "
                                       f"have two neighbours or more")
                    if any((ranks.shape == other.shape and (ranks == other).all()) for other in seen):
                        bad.append(f"{label}: the same scatter as another light")
                    seen.append(ranks)
        rows.append((v, len(seen), pairs, knots))
    return rows, bad


def furnace():
    rows, bad = [], []
    allowed = {P.colour(*tone) for tone in FURNACE_TONES}
    for v in W.VERSIONS:
        faces = W.furnace_face(v)                                   # [row][picture], the sill row first
        n = len(faces)
        glass = ~_bars(v)
        ys = [y for y in range(W.TILE) if glass[y].any()]           # the rows of glass in a block, head first
        xs = glass[ys[0]]                                           # its columns of glass
        halves = [ys[len(ys) // 2:], ys[:len(ys) // 2]]             # a block's glass: the lower half, the upper half
        for pick in itertools.product(*[range(len(row)) for row in faces]):
            label = f"furnace {v} {''.join(str(k) for k in pick)}"
            sheet = np.vstack([faces[r][pick[r]] for r in reversed(range(n))])      # one column of blocks, head first
            lum = (sheet[..., :3].astype(float) @ COEF) / 255.0
            whole, median = float(lum.mean()), float(np.median(lum))
            blocks = [luma(faces[r][pick[r]]) for r in range(n)]
            bands = [float(lum[[W.TILE * (n - 1 - r) + y for y in half]][:, xs].mean())
                     for r in range(n) for half in halves]
            head = float(lum[ys[0]][xs].mean())
            faults = []
            if whole > FURNACE_TOP or median > FURNACE_TOP:
                faults.append(f"mean {whole:.3f}, median {median:.3f}: over {FURNACE_TOP:.2f}")
            used = {tuple(int(c) for c in rgb) for rgb in np.unique(sheet[..., :3].reshape(-1, 3), axis=0)}
            if used - allowed:
                faults.append(f"{len(used - allowed)} colours that are not the furnace's")
            if any(y < sheet.shape[0] - 2 * W.TILE + ys[len(ys) // 2] for y, _ in _pale(sheet)):
                faults.append("the paler amber above the lower half of the second row")
            if any(a <= b for a, b in zip(bands, bands[1:])):
                faults.append("bands " + " ".join(f"{g:.3f}" for g in bands) + " do not darken upwards")
            if head > FURNACE_HEAD:
                faults.append(f"head {head:.3f}: not near a dark window ({FURNACE_HEAD:.2f})")
            if all(pick[r] == pick[0] % len(faces[r]) for r in range(n)):   # the table: a stack to each sill picture
                rows.append((v, pick[0], blocks, whole, median, head, "OUT" if faults else "ok"))
            bad += [f"{label}: {fault}" for fault in faults]
    return rows, bad


# The furnace window as the board is read (cr2 #78188, a1 #78449): the rows of the real V6 are
# measured in Rec.709. A lit picture shows its own colours, so the glass of a picture, the bars
# left out, is what a reader of the board finds between the bars.
COEF709 = np.array([0.2126, 0.7152, 0.0722])
BRIGHT = 0.5                    # cr2 counts the pixels of the window over this


def read709():
    """For every picture of every row of the furnace window: the mean of its glass, and the share
    of the whole block, bars and all, that is over BRIGHT. [(version, row, [means], [shares])]"""
    rows = []
    for v in W.VERSIONS:
        glass = ~_bars(v)
        for r, pictures in enumerate(W.furnace_face(v)):
            lum = [(np.asarray(px)[..., :3].astype(float) @ COEF709) / 255.0 for px in pictures]
            rows.append((v, r, [float(a[glass].mean()) for a in lum], [float((a > BRIGHT).mean()) for a in lum]))
    return rows


# The fires flicker (W.furnace_frames): every picture is W.FLICKER frames, one under the other. The
# first is the still picture, which everything above is measured on; the others are the same glass
# with the fire up: never darker than the still picture, so the board's lines hold in every frame;
# a flicker, not a flash, and no frame like the one before it.
FLICKER_SWING = 0.08            # how far the glass of a frame may stand over the still picture's, in Rec.709
FLICKER_LEAST = 1               # pixels of a block's glass that change from one frame to the next, at least,
#                                 in the two rows where the fire is (the third is soot: it may stand still)


def flicker():
    """[(version, row, lowest and highest glass of the row's frames, fewest and most pixels that
    change from a frame to the next)] and what is wrong with them."""
    rows, bad = [], []
    for v in W.VERSIONS:
        glass = ~_bars(v)
        for r, (stills, moving) in enumerate(zip(W.furnace_face(v), W.furnace_frames(v))):
            lows, highs, fewest, most = [], [], [], []
            for k, (still, sheet) in enumerate(zip(stills, moving)):
                label = f"furnace {v} row {r} picture {k}"
                sheet = np.asarray(sheet)
                if sheet.shape[0] != W.FLICKER * W.TILE or sheet.shape[1] != W.TILE:
                    bad.append(f"{label}: its frames are {sheet.shape[1]}x{sheet.shape[0]}, not {W.FLICKER} of {W.TILE}")
                    continue
                frames = [sheet[f * W.TILE:(f + 1) * W.TILE] for f in range(W.FLICKER)]
                if not np.array_equal(frames[0], np.asarray(still)):
                    bad.append(f"{label}: the first frame is not the still picture")
                at = [float((((fr[..., :3].astype(float) @ COEF709) / 255.0)[glass]).mean()) for fr in frames]
                steps = [int((frames[f] != frames[(f + 1) % W.FLICKER]).any(axis=2).sum()) for f in range(W.FLICKER)]
                lows.append(min(at))
                highs.append(max(at))
                fewest.append(min(steps))
                most.append(max(steps))
                if min(at) < at[0] - 1e-9:
                    bad.append(f"{label}: a frame's glass reads {min(at):.3f}, darker than the still picture's {at[0]:.3f}")
                if max(at) - at[0] > FLICKER_SWING:
                    bad.append(f"{label}: a frame's glass stands {max(at) - at[0]:.3f} over the still picture's "
                               f"{at[0]:.3f}; a flicker keeps within {FLICKER_SWING}")
                if r < 2 and min(steps) < FLICKER_LEAST:
                    bad.append(f"{label}: between two frames only {min(steps)} pixels change; the fire stands still there")
            if lows:
                rows.append((v, r, min(lows), max(highs), min(fewest), max(most)))
    return rows, bad


def main():
    print(f"glass glow[2]={P.RAMPS['glow'][2]}  opal[0]={P.RAMPS['opal'][0]}  "
          f"night_glass[3,4]={P.RAMPS['night_glass'][3]},{P.RAMPS['night_glass'][4]}  bar iron[1]={P.RAMPS['iron'][1]}")
    print(f"{'ver':3} {'role':8} {'whole/shownA':>12} {'glass/shownB':>12}  {'target':>11}  flag")
    rows, bad = table()
    for v, role, a, b, tgt, flag in rows:
        print(f"{v:3} {role:8} {a:12.3f} {b:12.3f}  {tgt:>11}  {flag}")
    print(f"\n{'ver':3} {'lining':14} {'whole':>6} {'colours':>12}  flag")
    lined, bad_lined = linings()
    for v, kind, whole, colours, flag in lined:
        print(f"{v:3} {kind:14} {whole:6.3f} {colours:12d}  {flag}")
    print(f"\n{'ver':3} {'furnace':8} " + " ".join(f"{word:>6}" for word in
                                                 ("sill", "second", "third", "whole", "median", "head")) + "  flag")
    fired, bad_fired = furnace()
    for v, k, blocks, whole, median, head, flag in fired:
        print(f"{v:3} {'stack ' + str(k):8} " + " ".join(f"{b:6.3f}" for b in blocks)
              + f" {whole:6.3f} {median:6.3f} {head:6.3f}  {flag}")
    print(f"\n{'ver':3} {'row':8} the glass of each picture in Rec.709, as the board is read; "
          f"the share of each block over {BRIGHT}")
    for v, r, means, shares in read709():
        print(f"{v:3} {('sill', 'second', 'third')[r]:8} " + " ".join(f"{m:.3f}" for m in means)
              + "   " + " ".join(f"{s:.3f}" for s in shares))
    print(f"\n{'ver':3} {'sill':8} pixels of each picture's glass that are not the paler amber")
    glowing, bad_glowing = sill()
    for v, counts, flag in glowing:
        print(f"{v:3} {'':8} " + " ".join(f"{n:3d}" for n in counts) + f"  {flag}")
    print(f"\n{'ver':3} {'dither':8} {'lights':>12} {'touching':>12} {'knots':>6}")
    scattered, bad_scattered = dither()
    for v, lights, pairs, knots in scattered:
        print(f"{v:3} {'':8} {lights:12d} {pairs:12d} {knots:6d}")
    print(f"\n{'ver':3} {'flicker':8} the glass of a row's frames from - to (Rec.709); pixels that change "
          f"from a frame to the next, fewest - most")
    moving, bad_moving = flicker()
    for v, r, low, high, fewest, most in moving:
        print(f"{v:3} {('sill', 'second', 'third')[r]:8} {low:.3f} - {high:.3f}   {fewest:3d} - {most:3d}")
    bad += bad_lined + bad_fired + bad_glowing + bad_scattered + bad_moving
    if bad:
        print("\nOUT OF LADDER:")
        for line in bad:
            print("  " + line)
        return 1
    print("\nall three lit tiers on c177's ladder, both versions; the linings give no light; "
          "the furnace window is one sheet under the curtain's level, its rows at the board's levels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
# shading only take from it. Held to: no colour of the two light ramps; every lining under the
# dimmest lit window; the unlit frosted glass lighter than the night glass that lines WINDOW_LIT.
LIGHT_RAMPS = ("glow", "opal")


def linings():
    rows, bad = [], []
    light = {P.colour(ramp, i) for ramp in LIGHT_RAMPS for i in range(len(P.RAMPS[ramp]))}
    for v in W.VERSIONS:
        whole = {}
        for kind in W.VARIANTS:
            px = W.lining_picture(kind, W.PIECE, W.PIECE, 0, v)
            used = {tuple(int(c) for c in rgb) for rgb in np.unique(px[..., :3].reshape(-1, 3), axis=0)}
            whole[kind] = luma(px)
            ok = not (used & light) and whole[kind] < TARGET["CURTAIN"][0]
            rows.append((v, kind, whole[kind], len(used), "ok" if ok else "OUT"))
            if used & light:
                bad.append(f"lining {v} {kind}: {len(used & light)} colours of the light ramps")
            if whole[kind] >= TARGET["CURTAIN"][0]:
                bad.append(f"lining {v} {kind}: whole {whole[kind]:.3f}, not under the dimmest lit window "
                           f"({TARGET['CURTAIN'][0]:.2f})")
        if not whole["lit"] < whole["frosted"]:
            bad.append(f"lining {v}: frosted {whole['frosted']:.3f} is not lighter than the night glass "
                       f"{whole['lit']:.3f}")
    return rows, bad


# The furnace window (A0, g2 #37112): three blocks from the sill up that show as one sheet. The game
# mixes the two pictures of a row by position, so every way of stacking them is measured. Held to:
#   - the mean and the median of the whole window not over the drawn curtain's 0.40;
#   - no colour but the two deepest ambers, the dark wood, the darkest iron and the bar;
#   - the paler amber only in the three lowest rows of pixels;
#   - the glass darker band after band from the sill to the head, a band being the lower or the
#     upper half of a block's glass: across the joints of the blocks as within them, which is what
#     makes three rows one sheet and not three stripes (a light that is dirtier than its height
#     does not upset it; a block that ran from light to dark by itself would);
#   - the last row of pixels under the head near a dark window.
FURNACE_TOP = 0.40
FURNACE_HEAD = 0.12
FURNACE_TONES = ([("glow", 0), ("glow", 1), ("iron", 0), W.BAR]
                 + [("dark_wood", i) for i in range(len(P.RAMPS["dark_wood"]))])
PALE_ROWS = 3


def furnace():
    rows, bad = [], []
    allowed = {P.colour(*tone) for tone in FURNACE_TONES}
    pale = np.array(P.colour("glow", 1))
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
            high = np.argwhere((sheet[..., :3] == pale).all(axis=-1))
            if len(high) and high[:, 0].min() < sheet.shape[0] - PALE_ROWS:
                faults.append(f"the paler amber {sheet.shape[0] - 1 - high[:, 0].min()} pixels above the sill")
            if any(a <= b for a, b in zip(bands, bands[1:])):
                faults.append("bands " + " ".join(f"{g:.3f}" for g in bands) + " do not darken upwards")
            if head > FURNACE_HEAD:
                faults.append(f"head {head:.3f}: not near a dark window ({FURNACE_HEAD:.2f})")
            if len(set(pick)) == 1:                                 # the table shows the two unmixed stacks
                rows.append((v, pick[0], blocks, whole, median, head, "OUT" if faults else "ok"))
            bad += [f"{label}: {fault}" for fault in faults]
    return rows, bad


def main():
    print(f"glass glow[2]={P.RAMPS['glow'][2]}  opal[0]={P.RAMPS['opal'][0]}  "
          f"night_glass[3,4]={P.RAMPS['night_glass'][3]},{P.RAMPS['night_glass'][4]}  bar iron[1]={P.RAMPS['iron'][1]}")
    print(f"{'ver':3} {'role':8} {'whole/shownA':>12} {'glass/shownB':>12}  {'target':>11}  flag")
    rows, bad = table()
    for v, role, a, b, tgt, flag in rows:
        print(f"{v:3} {role:8} {a:12.3f} {b:12.3f}  {tgt:>11}  {flag}")
    print(f"\n{'ver':3} {'lining':8} {'whole':>12} {'colours':>12}  flag")
    lined, bad_lined = linings()
    for v, kind, whole, colours, flag in lined:
        print(f"{v:3} {kind:8} {whole:12.3f} {colours:12d}  {flag}")
    print(f"\n{'ver':3} {'furnace':8} {'sill':>6} {'second':>6} {'third':>6} {'whole':>6} {'median':>6} {'head':>6}  flag")
    fired, bad_fired = furnace()
    for v, k, blocks, whole, median, head, flag in fired:
        print(f"{v:3} {'stack ' + str(k):8} " + " ".join(f"{b:6.3f}" for b in blocks)
              + f" {whole:6.3f} {median:6.3f} {head:6.3f}  {flag}")
    bad += bad_lined + bad_fired
    if bad:
        print("\nOUT OF LADDER:")
        for line in bad:
            print("  " + line)
        return 1
    print("\nall three lit tiers on c177's ladder, both versions; the linings give no light; "
          "the furnace window is one sheet under the curtain's level.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

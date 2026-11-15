"""A paper study, not a rendering: three great windows (3 wide, y 8..13) drawn flat with the
window_arch iron of props/ironwork as it stood at dabf7bf9 (half ring r 1.5 springing at 4.0 over
the sill, transom, jambs, foot plate, sheet in the spandrels) inside two stone heads: a today
(3 > 2 > 1), b with a top slab in the middle column (3 > 2, shut at the ring's crown;
main/facade.CROWN). Writes main-window-heads-v4.png and -v2.png beside itself, or into the folder
named. The colours are the study's own, not the palette's."""
import os
import sys

from PIL import Image, ImageDraw

S = 64
W, H = 13, 9                 # blocks: three bays and their pilasters; y 6..15 -> drawn 0..9
STONE_F, PIL_F, PANEL = (150, 150, 168), (166, 166, 184), (128, 128, 146)   # the blue-hour stone
IRON, IRON_D, SHEET = (60, 66, 82), (44, 48, 60), (34, 37, 48)
LIT, LIT2, DARKG = (236, 214, 150), (255, 190, 96), (26, 30, 62)
MUNT = (70, 62, 50)
Y0 = 6.0                     # the scene's y of the picture's foot

def X(z): return int(round((z + 6.5) * S))
def Y(y): return int(round((H - (y - Y0)) * S))
def rect(d, z0, y0, z1, y1, fill):
    d.rectangle([X(z0), Y(y1), X(z1) - 1, Y(y0) - 1], fill=fill)

def glass(d, zc, col, net):
    rect(d, zc - 1.5, 8, zc + 1.5, 14, col)
    for k in range(0, 6):                         # upright muntins: first pixel column of every half block
        z = zc - 1.5 + 0.5 * k
        rect(d, z, 8, z + 1 / 16.0, 14, net)
    for k in range(1, 13):                        # level ones: top row of every half block
        y = 8 + 0.5 * k
        rect(d, zc - 1.5, y - 1 / 16.0, zc + 1.5, y, net)

def scene(head, with_iron):
    im = Image.new("RGB", (W * S, H * S), STONE_F)
    back = Image.new("RGB", im.size, DARKG)
    db = ImageDraw.Draw(back)
    kinds = {-4: (LIT, (120, 104, 70)), 0: (LIT2, (120, 84, 40)), 4: (DARKG, (44, 50, 86))}
    for zc, (col, net) in kinds.items():
        glass(db, zc, col, net)
    if with_iron:
        u = 1 / 8.0
        for zc, (col, net) in kinds.items():
            hw, foot, spring = 12 * u, 8.0, 12.0
            # the head: sheet, then the glass inside the ring again
            head_im = Image.new("RGB", im.size, SHEET)
            m = Image.new("L", im.size, 0)
            dm = ImageDraw.Draw(m)
            dm.rectangle([X(zc - hw), Y(14), X(zc + hw) - 1, Y(spring) - 1], fill=255)
            r_in = 11 * u
            dm.pieslice([X(zc - r_in), Y(spring + r_in), X(zc + r_in), Y(spring - r_in)], 180, 360, fill=0)
            back.paste(head_im, (0, 0), m)
            db = ImageDraw.Draw(back)
            ro = 12 * u
            db.arc([X(zc - ro), Y(spring + ro), X(zc + ro), Y(spring - ro)], 180, 360, fill=IRON, width=int(u * S))
            rect(db, zc - hw, spring - u, zc + hw, spring + u, IRON)                 # transom
            rect(db, zc - hw, foot, zc - hw + 1.5 * u, spring, IRON)                  # jambs
            rect(db, zc + hw - 1.0 * u, foot, zc + hw, spring, IRON)
            rect(db, zc - hw + 1.5 * u, foot, zc + hw - u, foot + 4 * u, IRON_D)      # foot plate
    front = Image.new("RGB", im.size, STONE_F)
    df = ImageDraw.Draw(front)
    for k in range(18):                                                             # fine ashlar: two courses a block
        y = 6 + 0.5 * k
        rect(df, -6.5, y, 6.5, y + 1 / 16.0, (132, 132, 150))
    rect(df, -6.5, 6, 6.5, 7, (172, 172, 190))                                       # string course
    for zc in (-4, 0, 4):
        rect(df, zc - 1.5, 7, zc + 1.5, 8, PANEL)                                    # apron panel
        rect(df, zc - 1.5, 14, zc + 1.5, 15, PANEL)                                  # frieze panel
        rect(df, zc - 0.5, 14, zc + 0.5, 15, (176, 176, 194))                        # the key console
    for zp in (-6, -2, 2, 6):
        rect(df, zp - 0.5, 6, zp + 0.5, 15, PIL_F)
        rect(df, zp - 0.5, 14, zp + 0.5, 15, (150, 150, 170))                        # emblem block
    mask = Image.new("L", im.size, 255)
    dm = ImageDraw.Draw(mask)
    for zc in (-4, 0, 4):
        rect(dm, zc - 1.5, 8, zc + 1.5, 13, 0)
        rect(dm, zc - 1.0, 13, zc + 1.0, 13.5, 0)
        if head == "a":
            rect(dm, zc - 0.5, 13.5, zc + 0.5, 14, 0)
    return Image.composite(front, back, mask)

def sheet(scale):
    tiles = [scene("a", False), scene("a", True), scene("b", False), scene("b", True)]
    w, h = W * scale, H * scale
    out = Image.new("RGB", (2 * w + 12, 2 * h + 12), (0, 0, 0))
    for i, t in enumerate(tiles):
        out.paste(t.resize((w, h), Image.LANCZOS), ((i % 2) * (w + 12), (i // 2) * (h + 12)))
    return out

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    sheet(36).save(os.path.join(out, "main-window-heads-v4.png"))       # about V4: 36 px to the block
    small = sheet(12)                                                   # about V2: 12 px to the block
    small.resize((small.width * 3, small.height * 3), Image.NEAREST).save(os.path.join(out, "main-window-heads-v2.png"))

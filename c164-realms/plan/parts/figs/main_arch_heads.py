"""A paper study, not a rendering: the entrance arcade (version B) drawn flat with the iron of
props/ironwork as it stood at dabf7bf9 (door_frame and gate, read off the module: half ring r 1.5
blocks springing at 4.0, transom, jambs, fan, sheet in the spandrels) inside two stone heads:
  a  today: a stair hung in each top corner, the middle column open to the row's top (3 > 2 > 1)
  b  the same and a top slab in the middle column (3 > 2, shut at 5.5 -- the ring's crown;
     main/facade.CROWN)
Writes main-arch-heads-v4.png and -v2.png beside itself, or into the folder named. The colours are
the study's own, not the palette's.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

S = 64                      # px per block while drawing; scaled down afterwards
W, H = 15, 8                # blocks: z -7..7 (+1 margin), y 0..7
STONE_R, STONE_F, SLATE = (150, 143, 132), (176, 169, 157), (58, 58, 64)
SHADE = (112, 107, 100)
IRON, IRON_D, SHEET = (72, 78, 88), (52, 56, 64), (40, 43, 50)
HOT, MID, DIM = (255, 196, 96), (236, 150, 64), (170, 98, 48)
HALL = (150, 120, 84)       # the lit hall seen through the middle arch
DARK = (26, 28, 38)
SKY = (38, 42, 78)

def X(z): return int(round((z + 7.5) * S))          # z in blocks, 0 = the axis (middle of the middle arch)
def Y(y): return int(round((H - y) * S))

def rect(d, z0, y0, z1, y1, fill):
    d.rectangle([X(z0), Y(y1), X(z1) - 1, Y(y0) - 1], fill=fill)

def opening(d, zc, head, fill):
    """the hole of one arch: 3 wide, y 0..5 whole, the top row as `head` says"""
    rect(d, zc - 1.5, 0, zc + 1.5, 5, fill)
    rect(d, zc - 1.0, 5, zc + 1.0, 5.5, fill)
    if head == "a":
        rect(d, zc - 0.5, 5.5, zc + 0.5, 6, fill)

def iron(im, zc, kind, head):
    """c218's frame in the hole, clipped by the stone (drawn before the stone mask is applied)"""
    d = ImageDraw.Draw(im)
    u = 1 / 8.0                                      # his unit: 2 px = an eighth of a block
    hw, spring = 12 * u, 4.0
    # sheet: all that lies outside the ring, up to 6.0
    rect(d, zc - hw, spring, zc + hw, 6.0, SHEET)
    # what fills the half round
    r_in = 11 * u
    box = [X(zc - r_in), Y(spring + r_in), X(zc + r_in), Y(spring - r_in)]
    if kind == "door":
        for rr, col in ((11.5 * u, DIM), (9 * u, MID), (6 * u, HOT)):
            b = [X(zc - rr), Y(spring + rr), X(zc + rr), Y(spring - rr)]
            d.pieslice(b, 180, 360, fill=col)
    else:
        d.pieslice(box, 180, 360, fill=DARK)
    rays, wide = (5, 0.5 * u) if kind == "door" else (7, 1.0 * u)
    for i in range(1, rays + 1):
        a = math.radians(180.0 * i / (rays + 1))
        x0, y0 = zc + 3 * u * math.cos(a), spring + 3 * u * math.sin(a)
        x1, y1 = zc + 11.25 * u * math.cos(a), spring + 11.25 * u * math.sin(a)
        d.line([X(x0), Y(y0), X(x1), Y(y1)], fill=IRON_D, width=max(1, int(wide * S)))
    rm = 7 * u
    d.arc([X(zc - rm), Y(spring + rm), X(zc + rm), Y(spring - rm)], 180, 360, fill=IRON_D, width=max(1, int(wide * S)))
    rh = 3.5 * u
    d.pieslice([X(zc - rh), Y(spring + rh), X(zc + rh), Y(spring - rh)], 180, 360, fill=IRON)
    # the ring: centre line 11.5 u, 1 u thick
    ro = 12 * u
    d.arc([X(zc - ro), Y(spring + ro), X(zc + ro), Y(spring - ro)], 180, 360, fill=IRON, width=int(1 * u * S))
    # transom and jambs
    rect(d, zc - hw, spring - u, zc + hw, spring + u, IRON)
    rect(d, zc - hw, 0, zc - hw + u, spring, IRON)
    rect(d, zc + hw - u, 0, zc + hw, spring, IRON)
    if kind == "gate":
        top = (spring - u) - u
        for sx in (-1, 1):
            def span(x0, x1, y0, y1, col):
                a, b = sorted((zc + sx * x0 * u, zc + sx * x1 * u))
                rect(d, a, y0 * u, b, y1 * u, col)
            span(10, 11, 0, top / u, IRON); span(0, 1, 0, top / u, IRON)
            for x in (2.5, 5.0, 7.5):
                span(x, x + 1, 5, top / u - 1, IRON)
            span(1, 10, 0, 5, IRON_D)
            for y0, y1 in ((8.5, 10.5), (14.5, 16.5), (top / u - 1, top / u)):
                span(1, 10, y0, y1, IRON_D)

def scene(head, with_iron):
    im = Image.new("RGB", (W * S, H * S), SKY)
    d = ImageDraw.Draw(im)
    # what is seen through the holes
    back = Image.new("RGB", im.size, DARK)
    db = ImageDraw.Draw(back)
    rect(db, -1.5, 0, 1.5, 6, HALL)                              # the middle arch: the lit hall
    for zc in (-4, 4):
        rect(db, zc - 1.5, 0, zc + 1.5, 6, (70, 58, 50))         # side arches: dim warm behind the gates
    if with_iron:
        iron(back, 0, "door", head)
        for zc in (-4, 4):
            iron(back, zc, "gate", head)
    # the stone front
    front = Image.new("RGB", im.size, STONE_F)
    df = ImageDraw.Draw(front)
    rect(df, -7.5, 0, 7.5, 2, SLATE)                             # plinth
    rect(df, -7.5, 2, 7.5, 6, STONE_R)                           # banded base
    for y in range(2, 6):
        rect(df, -7.5, y, 7.5, y + 2 / 16.0, SHADE)              # the grooves
    rect(df, -7.5, 6, 7.5, 6.5, (190, 183, 171))                 # string course
    rect(df, -7.5, 6.5, 7.5, 7, (203, 196, 184))
    for zp in (-6, -2, 2, 6):                                     # pilasters, a touch lighter
        rect(df, zp - 0.5, 2, zp + 0.5, 6, (160, 153, 142))
        for y in range(2, 6):
            rect(df, zp - 0.5, y, zp + 0.5, y + 2 / 16.0, SHADE)
        rect(df, zp - 0.5, 0, zp + 0.5, 2, (66, 66, 72))
    rect(df, -0.5, 6, 0.5, 7, (210, 203, 190))                   # keystone in the string course
    mask = Image.new("L", im.size, 255)
    dm = ImageDraw.Draw(mask)
    for zc in (-4, 0, 4):
        opening(dm, zc, head, 0)
    im = Image.composite(front, back, mask)
    # soffit shade under the hung quarters (they are stone seen from below/aside): a darker lip
    return im

def sheet(scale):
    tiles = [scene("a", False), scene("a", True), scene("b", False), scene("b", True)]
    w, h = W * scale, H * scale
    out = Image.new("RGB", (2 * w + 12, 2 * h + 12), (0, 0, 0))
    for i, t in enumerate(tiles):
        t = t.resize((w, h), Image.LANCZOS)
        out.paste(t, ((i % 2) * (w + 12), (i // 2) * (h + 12)))
    return out

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    big = sheet(36)             # about V4 (14 blocks off): 36 px to the block
    big.save(os.path.join(out, "main-arch-heads-v4.png"))
    small = sheet(12)           # about V2 (40 blocks off): 12 px to the block
    small = small.resize((small.width * 3, small.height * 3), Image.NEAREST)
    small.save(os.path.join(out, "main-arch-heads-v2.png"))
    print(big.size, small.size)

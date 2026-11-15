"""Prototypes of the station's name board, as flat pixel pictures on a mock of the waiting room's
gable (cable's numbers): which face reads best. Scratch, not for the repository."""
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "/tmp/c164_lamps")
from scenes.obs.common import palette as P
from scenes.obs.props import signs

CR, EN, BR, IR = signs.CR, signs.EN, signs.BR, signs.IR
FONT = dict(signs._FONT)
FONT["M"] = ["10001", "11011", "10101", "10001", "10001"]


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def text(grid, s, x, y, ink):
    for ch in s:
        if ch == " ":
            x += 2
            continue
        for j, row in enumerate(FONT[ch]):
            for i, bit in enumerate(row):
                if bit == "1":
                    grid[y + j][x + i] = ink
        x += len(FONT[ch][0]) + 1
    return x


def width(s):
    return sum(2 if ch == " " else len(FONT[ch][0]) + 1 for ch in s) - 1


def base(w, h, chamfer=1, screws=True, brass=False):
    """An enamel field with an edge line, the corners cut by `chamfer` pixels."""
    edge = BR[3] if brass else CR[2]
    grid = [[EN[2]] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            dx, dy = min(x, w - 1 - x), min(y, h - 1 - y)
            if dx + dy < chamfer - 1 + (0 if chamfer > 1 else 0):
                grid[y][x] = None
            elif dx == 0 or dy == 0 or dx + dy == chamfer - 1 + (1 if chamfer > 1 else 0):
                grid[y][x] = edge
    if chamfer == 1:
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            grid[y][x] = EN[0]
    for x in range(1, w - 1):
        if grid[h - 2][x] == EN[2]:
            grid[h - 2][x] = EN[1]
        if x <= max(2, w // 4) and grid[1][x] == EN[2]:
            grid[1][x] = EN[3]
    if screws:
        for x, y in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
            if grid[y][x] is not None:
                grid[y][x] = BR[4]
    return grid


def emblem(grid, x0, y0, framed=True, ink=None, star=None):
    fig = signs.emblem_cells(16, framed=framed)
    for key in ("ring", "meridian", "star"):
        for x, y in fig[key]:
            grid[y0 + y][x0 + x] = (star or CR[3]) if key == "star" else (ink or CR[2])


def board_a():
    g = base(32, 16)
    emblem(g, 8, 0)
    return g


def board_a2():
    g = base(32, 16, chamfer=4, screws=False)
    emblem(g, 8, 0)
    for x, y in ((3, 7), (3, 8), (28, 7), (28, 8)):
        pass
    return g


def board_a3():
    """Brass edge instead of cream."""
    g = base(32, 16, brass=True)
    emblem(g, 8, 0)
    return g


def board_b(row=5, gap=3):
    g = base(41, 16)
    emblem(g, 0, 0)
    x = text(g, "2610", 14 + gap, row, CR[3])
    text(g, "M", x + 1, row, CR[3])
    return g


def board_d():
    g = base(32, 24)
    emblem(g, 8, 0)
    s = "2610 M"
    text(g, s, (32 - width(s)) // 2, 17, CR[3])
    return g


def board_e():
    """The emblem on the left, the height on the right in two lines: the figures over the letter."""
    g = base(32, 16)
    emblem(g, 0, 0)
    text(g, "2610", 16, 2, CR[3])
    return g


def plate(label):
    w = width(label) + 4
    g = base(w, 9, screws=False)
    text(g, label, 2, 2, CR[3])
    return g


def paint(grid, scale):
    h, w = len(grid), len(grid[0])
    a = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if grid[y][x] is not None:
                a[y, x] = (*rgb(grid[y][x]), 255)
    return Image.fromarray(a, "RGBA").resize((w * scale, h * scale), Image.NEAREST)


def gable(board, scale=6, extra=None, dim=1.0):
    """The waiting room's west gable from the west, 4 wide: polished piers, the lit window, the
    polished course the board hangs on, the gable's two cells of brick, the roof's edge."""
    px = 16 * scale
    W, H = 6 * px, 7 * px
    im = Image.new("RGBA", (W, H), (22, 26, 44, 255))
    d = ImageDraw.Draw(im)
    brick, course, glass, slate = (92, 96, 90), (128, 132, 124), (236, 214, 150), (58, 60, 70)
    ox, oy = px, 6 * px                          # the wall's lower left corner (z -36 is on the left for who looks east)
    def cell(i, j, col):                         # i: column 0..3, j: course 0.. from the foot
        d.rectangle([ox + i * px, oy - (j + 1) * px, ox + (i + 1) * px - 1, oy - j * px - 1], fill=col)
    for j in range(4):
        for i in range(4):
            col = course if i in (0, 3) or j in (0, 3) else glass
            cell(i, j, col)
    for i in (1, 2):
        cell(i, 4, brick)
    for i in (0, 3):                                 # the roof's lowest stairs, on the piers' columns
        d.polygon([(ox + i * px, oy - 4 * px), (ox + (i + 1) * px, oy - 4 * px),
                   (ox + (i + 1) * px if i == 0 else ox + i * px, oy - 5 * px)], fill=slate)
    d.rectangle([ox + px, oy - 5 * px - px // 2, ox + 3 * px - 1, oy - 5 * px - 1], fill=slate)
    b = paint(board, scale)
    cx, cy = ox + 2 * px, oy - 3 * px - px // 2          # the SIGN point: the middle of the top course
    im.alpha_composite(b, (cx - b.width // 2, cy - b.height // 2))
    if extra is not None:
        e = paint(extra, scale)
        im.alpha_composite(e, (ox + 3 * px + (px - e.width) // 2 if e.width <= px else ox + 4 * px - e.width, oy - 2 * px - e.height // 2))
    if dim != 1.0:
        a = np.array(im).astype(float)
        a[..., :3] *= dim
        im = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    return im


if __name__ == "__main__":
    boards = [("a: emblem alone", board_a()), ("a2: cut corners", board_a2()), ("d: emblem over height", board_d()),
              ("b1: emblem + height, rows 5..9", board_b(5)), ("b2: rows 6..10", board_b(6)),
              ("b3: rows 6..10, a pixel closer", board_b(6, 2))]
    tiles = [gable(g, 6) for _, g in boards]
    W = sum(t.width for t in tiles[:3]) + 20
    sheet = Image.new("RGBA", (W, 2 * tiles[0].height + 60), (16, 18, 28, 255))
    d = ImageDraw.Draw(sheet)
    for k, ((name, _), t) in enumerate(zip(boards, tiles)):
        x, y = (k % 3) * (t.width + 10), (k // 3) * (t.height + 30)
        d.text((x + 6, y + 4), name, fill=(220, 220, 220))
        sheet.alpha_composite(t, (x, y + 20))
    sheet.convert("RGB").save("/tmp/c164_lamps/board_proto.png")
    # small: how they read from far (one block = 16 px and 8 px)
    far = Image.new("RGBA", (6 * 6 * 16 + 70, 7 * 16 * 2 + 40), (16, 18, 28, 255))
    for k, (name, g) in enumerate(boards):
        t = gable(g, 6).resize((6 * 16, 7 * 16), Image.BOX)
        far.alpha_composite(t, (k * (6 * 16 + 10), 10))
        t2 = gable(g, 6).resize((6 * 8, 7 * 8), Image.BOX)
        far.alpha_composite(t2, (k * (6 * 16 + 10) + 24, 7 * 16 + 30))
    far.convert("RGB").resize((far.width * 2, far.height * 2), Image.NEAREST).save("/tmp/c164_lamps/board_proto_far.png")
    paint(plate("2610M"), 12).convert("RGB").save("/tmp/c164_lamps/plate_height.png")
    print("ok")

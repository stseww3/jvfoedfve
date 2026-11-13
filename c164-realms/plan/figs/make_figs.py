#!/usr/bin/env python3
"""The figures of the art plan, drawn by code.

    make_figs.py [--out <dir>] [--only palette,facade,elevation,site]

They are design drawings (flat colour sketches at block scale), not pictures of the game: the
palette and material board, a facade sample at 16 pixels to the block, the east elevation at dusk
and the site plan. The numbers in them (bay width, storey heights, dome radius, colours) are the
ones the plan fixes. Needs the 26.3 client jar for the vanilla textures (MC_JAR) and a CJK font
(PLAN_FONT).
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import draft as D  # noqa: E402

BG = (20, 23, 42)
INK = (232, 228, 216)
DIM = (150, 154, 178)
GOLD = (243, 217, 138)


def save(im, out, name, quality=92):
    path = os.path.join(out, name)
    if name.endswith(".jpg"):
        im.convert("RGB").save(path, quality=quality, subsampling=0)
    else:
        im.save(path, optimize=True)
    print(path, im.size)


def paste(canvas, arr, xy):
    canvas.paste(Image.fromarray(arr[..., :3].astype(np.uint8)), xy)


def wrap(dr, text, size, width):
    """Break a line of Chinese text to a width; punctuation never starts a line."""
    lines, line = [], ""
    for ch in text:
        if dr.textlength(line + ch, font=D.font(size)) > width and ch not in "，。；：、）":
            lines.append(line)
            line = ""
        line += ch
    lines.append(line)
    return lines


def legend(dr, x, y, items, size=19, width=440, gap=22, r=15):
    for n, text in items:
        D.tag(dr, (x + r, y + 12), n, r=r)
        lines = wrap(dr, text, size, width)
        for i, ln in enumerate(lines):
            D.label(dr, (x + 2 * r + 14, y + i * (size + 8)), ln, size)
        y += len(lines) * (size + 8) + gap
    return y


def warm_curve(level):
    b = np.clip(level / 15.0, 0, 1)
    return b / (4.0 - 3.0 * b)


# ---------------------------------------------------------------------------------------------
# palette and material board


def palette_board(out):
    W, H = 1860, 1120
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    D.label(dr, (40, 26), "配色与材质板", 34)
    D.label(dr, (290, 40), "带 * 的是自绘草样（16 像素一格），其余是原版贴图。颜色是固有色，实际画面还要乘上蓝调时刻的冷暖光。", 17, DIM)

    D.label(dr, (40, 96), "天空与光", 24)
    stops = [("天顶", "zenith"), ("高空", "high"), ("中段", "mid"), ("低空", "low"), ("余晖", "ember"), ("云线", "hot")]
    x0, y0, bw, bh = 40, 140, 96, 470
    cols = np.array([D.hxf(D.SKY[k]) for _, k in stops])
    pos = np.array([0.0, 0.28, 0.55, 0.75, 0.9, 1.0])
    t = np.linspace(0, 1, bh)
    bar = np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], axis=1)
    paste(im, np.repeat(bar[:, None, :] * 255, bw, axis=1), (x0, y0))
    for (name, key), p in zip(stops, pos):
        y = y0 + int(p * (bh - 1))
        dr.line((x0 + bw, y, x0 + bw + 14, y), fill=INK, width=1)
        D.label(dr, (x0 + bw + 20, y - 11), f"{name}  {D.SKY[key]}", 16)
    y = y0 + bh + 24
    for name, c in (("冷天光（天空给的补光）", D.SKY["cool"]), ("暖灯光（灯和窗）", D.SKY["warm"]), ("暗部底色", D.SKY["ambient"])):
        dr.rectangle((x0, y, x0 + 44, y + 44), fill=D.hx(c), outline=(60, 64, 90))
        D.label(dr, (x0 + 56, y + 2), name, 16)
        D.label(dr, (x0 + 56, y + 23), c, 14, DIM)
        y += 54
    y += 10
    for name, key in (("灯丝琥珀：主光", "glow"), ("荧光绿：只给仪表", "phosphor"), ("信号红：只给警示灯", "signal"), ("搪瓷蓝：铭牌、图纸、旗", "enamel")):
        for i, c in enumerate(D.RAMPS[key]):
            dr.rectangle((x0 + i * 30, y, x0 + i * 30 + 28, y + 28), fill=D.hx(c))
        D.label(dr, (x0 + 160, y + 4), name, 16)
        y += 40

    D.label(dr, (400, 96), "主材", 24)
    cards = [
        ("灰白石·细琢面 *", "主墙。一格两层，通缝错开", "ashlar", D.tex_ashlar, "约 35%"),
        ("灰白石·粗琢面 *", "基座层、台阶侧墙", "ashlar", D.tex_rustic, "约 10%"),
        ("深板岩砖", "勒脚、挡土墙", None, D.vanilla("deepslate_bricks"), "约 10%"),
        ("石板瓦", "屋面", None, D.vanilla("deepslate_tiles"), "约 10%"),
        ("铆接铸铁 *", "门、梁、平台、机壳、栏杆", "iron", D.tex_iron, "约 10%"),
        ("铜绿", "穹顶、塔顶、屋脊", "verdigris", D.vanilla("oxidized_cut_copper"), "约 12%"),
        ("旧铜", "雨水管、檐沟、把手", "copper", D.vanilla("exposed_cut_copper"), "约 3%"),
        ("黄铜 *", "仪器、扶手、铭牌、地面嵌线", "brass", D.tex_brass, "约 5%"),
        ("深色木", "室内墙板、家具", "wood", D.vanilla("dark_oak_planks"), "室内"),
        ("云杉地板", "室内地面", None, D.vanilla("spruce_planks"), "室内"),
    ]
    for n, (name, role, key, tex, share) in enumerate(cards):
        cx, cy = 400 + (n % 2) * 440, 140 + (n // 2) * 164
        paste(im, D.tile_block(tex, k=4, nx=3, ny=2), (cx, cy))
        D.label(dr, (cx + 206, cy + 2), name, 20)
        D.label(dr, (cx + 206, cy + 32), role, 15, DIM)
        D.label(dr, (cx + 206, cy + 56), share, 15, GOLD)
        if key:
            for i, c in enumerate(D.RAMPS[key]):
                dr.rectangle((cx + 206 + i * 19, cy + 88, cx + 206 + i * 19 + 17, cy + 112), fill=D.hx(c))

    X = 1300
    D.label(dr, (X, 96), "自绘方块草样", 24)
    paste(im, D.tile_block(lambda s: D.tex_window(True, s), k=4, nx=3, ny=3), (X, 140))
    paste(im, D.tile_block(lambda s: D.tex_window(False, s), k=4, nx=3, ny=3), (X + 240, 140))
    D.label(dr, (X, 340), "亮窗 *  自发光，细铁窗棂", 16)
    D.label(dr, (X + 240, 340), "暗窗 *  映着天色", 16)
    panels = [("表盘", D.tex_gauge), ("闸刀", D.tex_switches), ("电子管", D.tex_tubes), ("示波", D.tex_scope), ("计数器", D.tex_counter)]
    D.label(dr, (X, 390), "仪表面板 *  一格一块，成排码成整面墙", 16)
    for i, (name, f) in enumerate(panels):
        paste(im, D.upscale(f(i), 6), (X + i * 104, 420))
        D.label(dr, (X + i * 104, 522), name, 15, DIM)
    kinds = [D.tex_gauge, D.tex_switches, D.tex_tubes, D.tex_scope, D.tex_counter]
    wall = np.concatenate([np.concatenate([kinds[(i * 2 + j * 3) % 5](i + j) for i in range(8)], axis=1) for j in range(3)], axis=0)
    paste(im, D.upscale(wall, 4), (X, 566))
    D.label(dr, (X, 766), "同一批面板排成的控制墙（3 格高）", 15, DIM)
    paste(im, D.upscale(D.on_dark(np.concatenate([D.tex_grate()] * 3, axis=1)), 4), (X, 812))
    D.label(dr, (X + 206, 816), "铁格栅 *", 16)
    D.label(dr, (X + 206, 842), "走道和平台，镂空", 14, DIM)
    paste(im, D.upscale(np.concatenate([D.tex_door(), D.tex_door()[:, ::-1]], axis=1), 3), (X + 360, 800))
    D.label(dr, (X + 360, 1000), "铆钉铁门 *", 15, DIM)

    y = H - 70
    D.label(dr, (40, y - 34), "画面占比（室外）", 18)
    parts = [("石 55", 55, D.RAMPS["ashlar"][3], (30, 30, 30)), ("铁与石板瓦 20", 20, D.RAMPS["iron"][3], INK),
             ("铜绿 12", 12, D.RAMPS["verdigris"][2], (20, 30, 30)), ("黄铜与旧铜 8", 8, D.RAMPS["brass"][3], (30, 24, 10)),
             ("发光 5", 5, D.RAMPS["glow"][2], (40, 24, 8))]
    x = 40
    for name, share, c, ink in parts:
        w = int((W - 80) * share / 100)
        dr.rectangle((x, y, x + w - 3, y + 40), fill=D.hx(c))
        D.label(dr, (x + 8, y + 9), name, 17 if share > 6 else 15, ink)
        x += w
    save(im, out, "palette.jpg")


# ---------------------------------------------------------------------------------------------
# facade sample


def facade_sample(out):
    T, WB, HB = 16, 21, 25                      # block rows -1 (paving) .. 23
    H, W = HB * T, WB * T
    alb = np.zeros((H, W, 3))
    emi = np.zeros((H, W, 3))
    plane = np.full((H, W), -9)
    yy, xx = np.mgrid[0:16, 0:16]
    shapes = {
        "full": np.ones((16, 16), bool),
        "arch_l": np.hypot(xx - 15.5, yy - 15.5) > 15.5,
        "arch_r": np.hypot(xx + 0.5, yy - 15.5) > 15.5,
        "coping": yy >= 0,
    }

    def top(by):
        return (HB - 2 - by) * T

    def Y(h):
        return int(round((HB - 1 - h) * T))

    def put(tex, bx, by, p, shape="full", emit=False, tone=1.0):
        t = tex(bx * 31 + by * 17) if callable(tex) else tex
        m = shapes[shape] & (t[..., 3] > 0)
        y0, x0 = top(by), bx * T
        rgb = t[..., :3].astype(float) / 255.0 * tone
        alb[y0:y0 + T, x0:x0 + T][m] = rgb[m]
        emi[y0:y0 + T, x0:x0 + T][m] = rgb[m] if emit else 0.0
        plane[y0:y0 + T, x0:x0 + T][m] = p

    def sprite(rgb, mask, x0, y0, p, emit=None):
        h, w = mask.shape
        alb[y0:y0 + h, x0:x0 + w][mask] = rgb[mask]
        emi[y0:y0 + h, x0:x0 + w][mask] = 0.0
        if emit is not None:
            emi[y0:y0 + h, x0:x0 + w][emit] = rgb[emit]
        plane[y0:y0 + h, x0:x0 + w][mask] = p

    def box(x0, y0, w, h, c, p=3, emit=False):
        rgb = np.zeros((h, w, 3))
        rgb[...] = c
        m = np.ones((h, w), bool)
        sprite(rgb, m, int(x0), int(y0), p, emit=m if emit else None)

    PIERS = (0, 4, 8, 12, 16, 20)
    WIN = (1, 5, 13, 17)
    DOOR = 9
    lit_tall = {1: 0.0, 5: 0.94, 9: 1.0, 13: 0.88, 17: 0.96}
    lit_low = {13: 0.82}
    ashlar, rustic = D.tex_ashlar, D.tex_rustic
    plinth, paving = D.vanilla("deepslate_bricks"), D.vanilla("polished_tuff")
    iron = [D.hxf(c) for c in D.RAMPS["iron"]]
    brass = [D.hxf(c) for c in D.RAMPS["brass"]]
    cop = [D.hxf(c) for c in D.RAMPS["copper"]]
    glow = [D.hxf(c) for c in D.RAMPS["glow"]]
    sources = []

    for bx in range(WB):
        put(paving, bx, -1, 0)

    # the drum and the dome, eight blocks behind the front
    for bx in range(2, 19):
        for by in (17, 18, 19):
            put(ashlar, bx, by, -2, tone=0.92)
    copper, streak = D.vanilla("oxidized_cut_copper"), D.vanilla("weathered_cut_copper")
    g = D.rng(3)
    for by in range(20, 24):
        half = math.sqrt(max(0.0, 9.5 ** 2 - (by - 20 + 0.5) ** 2))
        for bx in range(int(math.ceil(10.5 - half)), int(math.floor(10.5 + half))):
            if by == 20:
                put(D.tex_iron, bx, by, -2)
            else:
                put(streak if g.random() < 0.14 else copper, bx, by, -2, tone=0.78 if bx % 3 == 1 else 1.0)
    for bx in range(2, 19, 2):                  # the rollers the dome turns on
        d = np.hypot(xx - 7.5, yy - 11.5)
        wheel = np.zeros((16, 16, 3))
        wheel[...] = iron[1]
        wheel[d <= 2.0] = brass[2]
        sprite(wheel, d <= 3.6, bx * T, top(20), -2)
    for bx in (5, 10, 15):
        d = np.hypot(xx - 7.5, yy - 7.5)
        ring = np.zeros((16, 16, 3))
        ring[...] = iron[1]
        ring[d <= 4.5] = glow[2]
        ring[(d <= 4.5) & ((xx == 7) | (yy == 7))] = iron[1]
        sprite(ring, d <= 5.6, bx * T, top(18), -2, emit=(d <= 4.5) & (xx != 7) & (yy != 7))
        sources.append((bx * T + 8, top(18) + 8, 7))

    # glass, a block behind the wall
    for wc in WIN + (DOOR,):
        v = lit_tall[wc]
        for bx in range(wc, wc + 3):
            for by in range(8, 14):
                put(lambda s: D.tex_window(v > 0, s), bx, by, -1, emit=v > 0, tone=v if v > 0 else 1.0)
        if v > 0:
            sources += [((wc + 1.5) * T, Y(h), 10) for h in (9.0, 11.0, 13.0)]
    for wc in WIN:
        v = lit_low.get(wc, 0.0)
        for bx in range(wc, wc + 3):
            for by in (3, 4):
                put(lambda s: D.tex_window(v > 0, s), bx, by, -1, emit=v > 0, tone=v if v > 0 else 1.0)
        if v > 0:
            sources.append(((wc + 1.5) * T, Y(4), 9))
    y0 = top(8)                                  # shelves and a globe seen against one lit window
    for i, x in enumerate(range(5 * T + 1, 8 * T - 1)):
        hgt = 6 + (i * 7 % 4) + (5 if (i // 6) % 3 == 0 else 0)
        emi[y0 + 16 - hgt:y0 + 16, x] *= 0.3

    # the door: two leaves, a fanlight, round shoulders
    leaf = D.tex_door()
    dy, dx = np.mgrid[0:64, 0:24]
    port = (np.hypot(dx - 11.5, dy - 15.5) <= 4.6) & (dx != 11)
    for k, (lf, pm) in enumerate(((leaf, port), (leaf[:, ::-1], port[:, ::-1]))):
        sprite(lf[..., :3] / 255.0, np.ones((64, 24), bool), DOOR * T + k * 24, top(3), -1, emit=pm)
    bar = D.hx(D.RAMPS["iron"][1])
    fan = Image.new("RGB", (48, 32), D.hx(D.LIT_GLASS[2]))
    fd = ImageDraw.Draw(fan)
    for a in range(0, 181, 30):
        fd.line((23.5, 32, 23.5 + 60 * math.cos(math.radians(a)), 32 - 60 * math.sin(math.radians(a))), fill=bar)
    fd.arc((9, 18, 38, 46), 180, 360, fill=bar)
    fd.line((0, 31, 47, 31), fill=bar)
    fan = np.array(fan) / 255.0
    bars = np.all(np.abs(fan - np.array(bar) / 255.0) < 0.02, axis=2)
    sprite(fan, np.ones((32, 48), bool), DOOR * T, top(5), -1, emit=~bars)
    sources.append(((DOOR + 1.5) * T, Y(5.0), 11))

    # the wall
    def bay_of(bx):
        return any(wc <= bx < wc + 3 for wc in WIN)

    for bx in range(WB):
        door = DOOR <= bx < DOOR + 3
        for by in range(2, 6):
            if (bay_of(bx) and by in (3, 4)) or (door and by <= 4):
                continue
            shape = "full"
            if door:
                if bx == DOOR + 1:
                    continue
                shape = "arch_l" if bx == DOOR else "arch_r"
            put(rustic, bx, by, 0, shape)
        put(D.tex_panel if (bay_of(bx) or door) else ashlar, bx, 7, 0)
        put(ashlar, bx, 14, 0)
        put(ashlar, bx, 16, 0)
    for wc in WIN + (DOOR,):
        put(ashlar, wc, 13, 0, "arch_l")
        put(ashlar, wc + 2, 13, 0, "arch_r")
        box(wc * T, Y(8) - 3, 3 * T, 3, D.hxf(D.RAMPS["ashlar"][5]), p=1)     # the sill
        box(wc * T, Y(8), 3 * T, 1, D.hxf(D.RAMPS["ashlar"][1]), p=1)

    # what stands in front of the wall
    for bx in range(WB):
        if not DOOR <= bx < DOOR + 3:
            put(plinth, bx, 0, 1)
            put(plinth, bx, 1, 1)
        put(D.tex_moulding(), bx, 6, 1)
        put(D.tex_moulding(), bx, 15, 2)
        box(bx * T, Y(17), T, 3, D.hxf(D.RAMPS["ashlar"][5]), p=1)            # coping of the parapet
    for bx in PIERS:
        for by in range(2, 6):
            put(rustic, bx, by, 1)
        put(D.tex_moulding(True), bx, 7, 1)
        for by in range(8, 13):
            put(ashlar, bx, by, 1)
        put(D.tex_moulding(), bx, 13, 1)
        put(ashlar, bx, 14, 1)
        put(ashlar, bx, 16, 1)
        box(bx * T, Y(17), T, 3, D.hxf(D.RAMPS["ashlar"][5]), p=1)

    # iron canopy over the door with a row of bare bulbs
    cx0, cx1, cyy = 8 * T - 6, 13 * T + 6, Y(6) + 2
    box(cx0, cyy, cx1 - cx0, 3, iron[2])
    box(cx0, cyy, cx1 - cx0, 1, iron[5])
    for x in range(cx0 + 5, cx1 - 3, 10):
        box(x, cyy + 3, 2, 3, glow[4], emit=True)
        sources.append((x + 1, cyy + 5, 9))
    for sgn, xa in ((1, cx0 + 2), (-1, cx1 - 3)):
        for i in range(22):
            box(xa + sgn * i, cyy - 1 - i, 1, 1, iron[4])

    # wall lamps on the piers beside the door
    for bx in (8, 12):
        cx, cy = bx * T + 8, Y(3.5)
        box(cx - 2, cy - 12, 4, 5, iron[2])
        box(cx - 1, cy - 8, 2, 4, iron[4])
        box(cx - 4, cy - 5, 8, 2, iron[1])
        gy, gx = np.mgrid[0:8, 0:8]
        gd = np.hypot(gx - 3.5, gy - 3.5)
        globe = np.zeros((8, 8, 3))
        globe[...] = glow[3]
        globe[gd <= 2.2] = glow[4]
        sprite(globe, gd <= 3.9, cx - 4, cy - 3, 3, emit=gd <= 3.9)
        sources.append((cx, cy, 14))

    # copper downpipe with its hopper head and brackets
    px = 16 * T + 13
    box(px - 2, Y(15) + 1, 6, 5, cop[2])
    box(px - 2, Y(15) + 1, 6, 1, cop[4])
    box(px, Y(15) + 6, 2, Y(0.15) - Y(15) - 6, cop[2])
    box(px, Y(15) + 6, 1, Y(0.15) - Y(15) - 6, cop[3])
    for h in (2.5, 5.5, 8.5, 11.5, 14.2):
        box(px - 1, Y(h), 4, 2, iron[2])
        box(px, Y(h) + 2, 1, 3, D.hxf(D.RAMPS["verdigris"][1]))
    box(px - 1, Y(0.15) - 3, 5, 3, cop[1])

    # cable on porcelain insulators under the string course
    cy = Y(6) + 3
    for x in range(14 * T, W - 2):
        sag = int(round(1.6 * math.sin(math.pi * ((x - 14 * T) % 32) / 32.0)))
        box(x, cy + sag, 1, 1, iron[0])
    for x in range(14 * T, W, 32):
        box(x - 1, cy - 2, 3, 3, D.hxf("#e8e2d2"))
        box(x - 1, cy + 1, 3, 1, iron[2])

    # two heating pipes along the plinth, flanges and a valve wheel
    for h, c in ((1.95, cop[3]), (1.6, cop[2])):
        box(13 * T + 2, Y(h), 3 * T + 8, 2, c)
        box(13 * T + 2, Y(h) + 1, 3 * T + 8, 1, cop[1])
        for x in range(13 * T + 6, 16 * T + 6, 18):
            box(x, Y(h) - 1, 2, 4, cop[4])
    vx, vy = 15 * T + 4, Y(1.78)
    for a in range(0, 360, 45):
        box(vx + int(round(3 * math.cos(math.radians(a)))), vy + int(round(3 * math.sin(math.radians(a)))), 1, 1, D.hxf(D.RAMPS["signal"][2]))
    box(vx, vy, 1, 1, iron[5])

    # enamel plate, vents, the emblem over the door, lightning rods
    ex, ey = 12 * T + 3, Y(2.75)
    box(ex, ey, 10, 8, D.hxf(D.RAMPS["enamel"][4]))
    box(ex + 1, ey + 1, 8, 6, D.hxf(D.RAMPS["enamel"][2]))
    box(ex + 2, ey + 3, 6, 1, D.hxf(D.RAMPS["enamel"][4]))
    box(ex + 3, ey + 5, 4, 1, D.hxf(D.RAMPS["enamel"][4]))
    for bx in (2, 6):
        box(bx * T + 3, Y(0.75), 10, 7, iron[0])
        for i in range(0, 10, 2):
            box(bx * T + 3 + i, Y(0.75), 1, 7, iron[4])
    gy, gx = np.mgrid[0:13, 0:13]
    gd = np.hypot(gx - 6, gy - 6)
    emb = np.zeros((13, 13, 3))
    emb[...] = brass[3]
    emb[(gd > 5.4) | (gy > gx + 2)] = brass[2]
    emb[(gx == 9) & (gy == 3)] = brass[5]
    sprite(emb, ((gd <= 6.2) & (gd >= 4.4)) | ((gx == 6) & (gd <= 6.2)) | ((gx == 9) & (gy == 3)), int(10.5 * T) - 6, Y(14.5) - 6, 3)
    for bx in PIERS:
        box(bx * T + 7, Y(17) - 17, 1, 14, iron[5])
        box(bx * T + 6, Y(17) - 12, 3, 3, cop[3])

    # a player for scale: 1.8 blocks tall
    fx, fy = int(14.3 * T), Y(0) - 29
    who = np.zeros((29, 8), bool)
    who[0:7, 1:7] = True
    who[7:19, 0:8] = True
    who[19:29, 1:4] = True
    who[19:29, 4:7] = True
    rgb = np.zeros((29, 8, 3))
    rgb[...] = (0.30, 0.27, 0.30)
    rgb[0:7] = (0.60, 0.46, 0.38)
    rgb[7:19] = (0.22, 0.32, 0.46)
    sprite(rgb, who, fx, fy, 3)

    # light
    Yp, Xp = np.mgrid[0:H, 0:W]
    level = np.zeros((H, W))
    for sx, sy, L in sources:
        level = np.maximum(level, L - (np.hypot(Xp - sx, Yp - sy) / T + 0.4))
    warm = warm_curve(level)
    ao = np.ones((H, W))
    for lvl in (-1, 0, 1, 2, 3):
        reach = plane >= lvl
        for f in (0.52, 0.64, 0.76, 0.86, 0.94):
            grown = reach.copy()
            grown[1:] |= reach[:-1]
            grown[:-1] |= reach[1:]
            grown[:, 1:] |= reach[:, :-1]
            grown[:, :-1] |= reach[:, 1:]
            hit = grown & ~reach & (plane < lvl) & (plane > -9)
            ao[hit] = np.minimum(ao[hit], f)
            reach = grown
    depth = np.select([plane == -2, plane == -1, plane == 0], [0.70, 0.80, 0.84], 1.0)
    cool = D.hxf(D.SKY["cool"]) * 0.50
    lit = alb * (cool[None, None] * (ao * depth)[..., None] + D.hxf(D.SKY["warm"])[None, None] * (warm * (0.5 + 0.5 * ao))[..., None] * 1.15)
    glowing = emi.sum(axis=2) > 0
    lit[glowing] = (emi * (0.45 + 0.55 * ao)[..., None])[glowing]

    # sky behind, an aerial wire across it
    sky = plane == -9
    t = np.clip((Yp / float(Y(16))), 0, 1)
    grad = D.hxf(D.SKY["high"])[None, None] * (1 - t)[..., None] + D.hxf(D.SKY["mid"])[None, None] * t[..., None]
    lit[sky] = grad[sky]
    g = D.rng(11)
    for _ in range(110):
        y, x = int(g.integers(0, Y(16))), int(g.integers(0, W))
        if sky[y, x]:
            lit[y, x] = np.minimum(1.0, lit[y, x] + g.random() ** 2 * 0.8)
    for x in range(W):
        y = int(round(22 + 14 * ((x / W - 0.5) * 2) ** 2 + x * 0.05))
        if sky[y, x]:
            lit[y, x] = (0.04, 0.05, 0.10)
            if x % 40 == 20:
                lit[y - 1:y + 2, x:x + 3][sky[y - 1:y + 2, x:x + 3]] = (0.75, 0.74, 0.72)

    K = 3
    img = D.upscale((np.clip(lit, 0, 1) * 255).astype(np.uint8), K)
    PW = 600
    im = Image.new("RGB", (W * K + PW, H * K), BG)
    paste(im, img, (0, 0))
    dr = ImageDraw.Draw(im)
    notes = [
        ((4 * T + 8, Y(10.5)), "三层进深：壁柱在前，墙面居中，窗退后，每层差一格。"),
        ((2 * T + 8, Y(6.5)), "勒脚、腰线、檐口把立面横分三段；基座层用粗琢面。"),
        ((6 * T + 8, Y(11.5)), "发光窗：方块自发光，细铁窗棂。窗后放隐形光源，把窗套染暖。窗里看得见书架的剪影。"),
        ((2 * T + 8, Y(10.5)), "暗窗：不是每扇都亮，留几扇映着天色。"),
        ((10 * T + 8, Y(2.2)), "铆钉铁门带舷窗，门上扇形亮窗；铁雨棚下一排裸灯泡，两侧铁架白玻璃壁灯。"),
        ((17 * T + 6, Y(9.5)), "外露管线：铜雨水管和水斗、瓷瓶电缆、暖气管和红手轮、通风格栅、搪瓷铭牌。"),
        ((15 * T + 8, Y(0.6)), "暖灯对冷影：灯只照亮入口一圈，往外退到蓝色里。人高 2 格。"),
        ((10 * T + 8, Y(21.5)), "后面是铜绿穹顶，底下一圈铸铁轨道和滚轮；鼓座开小圆窗。"),
        ((10 * T + 8, Y(15.6)), "檐下黄铜台徽：圆环加一条子午线。同一个符号全场通用。"),
    ]
    D.label(dr, (W * K + 28, 26), "立面质感小样", 32)
    D.label(dr, (W * K + 28, 72), "入口一跨加左右各两跨，16 像素一格。", 17, DIM)
    D.label(dr, (W * K + 28, 96), "按方块画的二维色稿，不是游戏截图。", 17, DIM)
    for n, ((x, yy_), _) in enumerate(notes, 1):
        D.tag(dr, (x * K, yy_ * K), n, r=15)
    legend(dr, W * K + 28, 150, [(n, t_) for n, (_, t_) in enumerate(notes, 1)], width=PW - 100)
    D.label(dr, (W * K + 28, H * K - 100), "开间 4 格（壁柱 1 + 窗 3）。基座层 4 格，主层 7 格，", 16, DIM)
    D.label(dr, (W * K + 28, H * K - 76), "檐口在 15 格，女儿墙到 17 格。", 16, DIM)
    D.label(dr, (W * K + 28, H * K - 44), "石、铁、窗、门是自绘草样；板岩砖、铜绿是原版贴图。", 16, DIM)
    save(im, out, "facade.jpg")


FIGS = {"palette": palette_board, "facade": facade_sample}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    want = [w for w in args.only.split(",") if w] or list(FIGS)
    for name in want:
        FIGS[name](args.out)


if __name__ == "__main__":
    main()

"""Tone check: what a picture's lights and darks are, in numbers and in pictures (card
plan/packages/sky/tones.md; ART-PLAN 11, row A2: the sky darkest, the walls in the middle, windows
and lamps brightest, nothing dead black; RUBRIC 3).

    python scenes/obs/sky/_tones.py <picture> [<picture> ...] [--out <folder>]
                                    [--probe wall=0.42,0.35,0.55,0.60 ...] [--diff <picture>] [--ladder]
                                    [--mask snow=<picture> ...] [--mask-out <picture>] [--luma 709]

Takes any picture, a screenshot of the game or an offline rendering. It judges nothing: it gives
the numbers and the pictures a reviewer reads the picture's values from. The lines are the
rubric's (the bright area at most a third of the picture, no patch of dead black).

Per picture, printed and, with --out, drawn onto one sheet (<name>-tones.jpg):
  grey     the picture without its colour
  levels   three flat tones, dark / middle / bright, and the share of each; dead black marked red
  warmth   which pixels are warm (redder than blue), which cool, and at which level they sit
  bright   the area brighter than 0.6: its share, its centre of gravity, how gathered it is
  dead     the area darker than 0.03: its share and the largest patch of it
  probes   named areas (--probe, --probes, --mask): how many pixels, mean, median, the brightest
           and the darkest hundredth (to three places: a buttress and its wall are 0.02 apart),
           the mean colour; listed from dark to bright by their medians (--order mean: by their
           means), so "sky < wall < window" is read off one line. Four numbers are a rectangle
           x0,y0,x1,y1; six or more are the corners of a polygon, x,y each (a sloping kerb, a
           flight of steps). --probes is a table by picture: a picture takes the entry of its
           own name, or of the name its own ends in after a "-" (the sketches of selfshots.py
           --out are <scene>-<shot>), and "*"; a table that has nothing for a picture is said so.
           --mask name=<picture> is an area of any shape: the white of a black-and-white picture
           of the same view (of another size but the same proportions: it is brought to size)
  differs  with --diff <picture>, a second picture of the same view (a switch on and off, two
           versions): the pixels whose brightness is further apart than 0.02 (--diff-over) are
           the footprint of what changed; their share, and what they hold in this picture and in
           the other. Each probe also says what changed within it. One line more answers "is
           anything changed at all": how many pixels hold another value in red, green or blue,
           without any threshold (0: the two pictures are the same, pixel for pixel).
           --mask-out <picture> keeps the footprint, white on black, to measure a third picture
           with (--mask): what a switch changes offline, looked up in a screenshot
  stamps   the picture, grey and levels at 96 pixels wide

Brightness is Rec.601 luma of the picture's own values, 0 to 1 (what PIL's "L" gives); --luma 709
weighs the three by Rec.709 instead, for numbers kept in that (a grey reads the same, a blue wall
about 0.01 lower). Where dark
ends and the middle begins depends on the light version (SPLIT; A blue, B deep, C glow): it is
taken from --look, else from the shots.txt beside a kept picture or from --shots, else it is A's.
A probe's numbers are pixels, or fractions of the picture when none of them is above 1; the
sheet's first panel has a tick at every tenth to read them from.

Needs numpy and Pillow only and takes about a second a picture. The leading underscore keeps the
module out of the scene's packages. --ladder also prints what the plan expects of the light
version (from sky/mood.py and the game's light table); for that it has to run inside build/.
"""
import argparse
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COEFS = {"601": np.array([0.299, 0.587, 0.114]), "709": np.array([0.2126, 0.7152, 0.0722])}
COEF = COEFS["601"]    # what luma() weighs red, green and blue by; main() sets it from --luma
DEAD = 0.03            # darker than this is dead black (card)
BRIGHT = 0.60          # brighter than this is the bright area (card, rubric)
WHITE = 0.97           # blown out
WARMTH = 0.03          # red above blue by this much is warm, blue above red by it cool
DIFFER = 0.02          # two pictures differ where their brightness is further apart than this
# Where dark ends and the middle begins, per light version: between the sky over the roofs and a
# wall the sky alone lights (sky/look's record: blue 0.13 and 0.24, deep 0.05 and 0.17, glow 0.20
# and 0.29).
SPLIT = {"blue": 0.18, "deep": 0.12, "glow": 0.25}
LETTER = {"blue": "A", "deep": "B", "glow": "C"}      # what the plan calls the three
GRID = 320             # patches are counted on a grid about this many cells wide

TONES = (38, 128, 235)                 # the three flat tones of the levels picture
RED = (214, 40, 57)
MARK = (255, 196, 0)
INK, PAPER = (235, 235, 235), (16, 18, 28)
WARM, COOL = np.array([1.0, 0.62, 0.20]), np.array([0.30, 0.55, 1.0])
MORE, LESS = np.array([1.0, 0.59, 0.16]), np.array([0.27, 0.55, 1.0])     # brighter, darker than the other picture
LEVELS = ("dark", "middle", "bright")
PROBE = "a probe is name=x0,y0,x1,y1 (a rectangle) or name=x,y,x,y,x,y,... (the corners of a polygon, three or more)"


def look_at(tick):
    """The light version a time of day shows (the plateaus of sky/mood.py; trials count as blue)."""
    tick %= 24000
    return "glow" if 12300 <= tick < 13400 else "deep" if 15500 <= tick < 21500 else "blue"


def load(path, crop=None):
    """The picture as floats 0..1, height x width x 3."""
    picture = Image.open(path).convert("RGB")
    if crop:
        picture = picture.crop(_box(crop, picture.size))
    return np.asarray(picture, dtype=np.float64) / 255.0


def _box(numbers, size):
    """x0, y0, x1, y1 in pixels; four numbers none above 1 are fractions of the picture."""
    x0, y0, x1, y1 = numbers
    if max(numbers) <= 1.0:
        x0, x1, y0, y1 = x0 * size[0], x1 * size[0], y0 * size[1], y1 * size[1]
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    x0, y0 = max(0, min(size[0] - 1, x0)), max(0, min(size[1] - 1, y0))
    return x0, y0, max(x0 + 1, min(size[0], x1)), max(y0 + 1, min(size[1], y1))


def region(numbers, size):
    """(mask, corners) of a probe: the pixels it covers, height x width, and its corners in pixels.
    Four numbers are a rectangle x0, y0, x1, y1; six or more are the corners of a polygon, x then
    y. Numbers none of which is above 1 are fractions of the picture."""
    w, h = size
    numbers = [float(v) for v in numbers]
    if len(numbers) == 4:
        x0, y0, x1, y1 = _box(numbers, size)
        mask = np.zeros((h, w), dtype=bool)
        mask[y0:y1, x0:x1] = True
        return mask, [(x0, y0), (x1 - 1, y0), (x1 - 1, y1 - 1), (x0, y1 - 1)]
    if len(numbers) < 6 or len(numbers) % 2:
        raise ValueError(PROBE)
    sx, sy = (float(w), float(h)) if max(numbers) <= 1.0 else (1.0, 1.0)
    corners = [(numbers[i] * sx, numbers[i + 1] * sy) for i in range(0, len(numbers), 2)]
    drawn = Image.new("L", (w, h), 0)
    ImageDraw.Draw(drawn).polygon(corners, fill=255)
    return np.asarray(drawn) > 0, corners


def mask_of(path, size, crop=None):
    """An area given as a picture (height x width, True inside): what is brighter than the middle
    grey of a black-and-white picture of the same view. `size` is the measured picture's before
    it is cropped; a mask of another size and the same proportions is brought to it."""
    drawn = Image.open(path).convert("L")
    if drawn.size != tuple(size):
        if abs(drawn.size[0] * size[1] - drawn.size[1] * size[0]) > max(drawn.size[0], size[0]):
            raise SystemExit(f"--mask: {path} is {drawn.size[0]}x{drawn.size[1]}, the picture {size[0]}x{size[1]}: "
                             "not the same proportions, so not the same view")
        drawn = drawn.resize(tuple(size), Image.NEAREST)
    if crop:
        drawn = drawn.crop(_box(crop, drawn.size))
    return np.asarray(drawn) > 127


def luma(rgb):
    return rgb @ COEF


def _hex(rgb):
    return "#" + "".join(f"{int(round(max(0.0, min(1.0, c)) * 255.0)):02x}" for c in rgb)


def patches(mask):
    """(how many patches, the largest one's share of the picture) of a mask, counted on a coarse
    grid: a cell belongs when more than half of it does, cells touching by a side are one patch."""
    h, w = mask.shape
    cell = max(1, round(w / GRID))
    gh, gw = h // cell, w // cell
    if not gh or not gw:
        return 0, 0.0
    coarse = mask[:gh * cell, :gw * cell].reshape(gh, cell, gw, cell).mean(axis=(1, 3)) > 0.5
    todo = coarse.copy()
    count, largest = 0, 0
    for y, x in zip(*np.nonzero(coarse)):
        if not todo[y, x]:
            continue
        count += 1
        size, queue = 0, deque([(y, x)])
        todo[y, x] = False
        while queue:
            cy, cx = queue.popleft()
            size += 1
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < gh and 0 <= nx < gw and todo[ny, nx]:
                    todo[ny, nx] = False
                    queue.append((ny, nx))
        largest = max(largest, size)
    return count, largest / float(gh * gw)


def stats(pixels):
    """What a set of pixels (n x 3) holds. The brightest and the darkest hundredth are means of
    that many pixels, one pixel at least: with few pixels they are a single one's value."""
    n = len(pixels)
    if not n:
        return dict(pixels=0)
    y = np.sort(luma(pixels))
    edge = max(1, n // 100)
    warmth = pixels[:, 0] - pixels[:, 2]
    return dict(pixels=int(n), mean=float(y.mean()), median=float(np.median(y)),
                top=float(y[-edge:].mean()), low=float(y[:edge].mean()), colour=_hex(pixels.mean(axis=0)),
                warm=float((warmth > WARMTH).mean()), cool=float((warmth < -WARMTH).mean()))


def measure(rgb, split, probes=None, other=None, differ=DIFFER):
    """The numbers of one picture. probes: {name: numbers as region() takes them, or a mask as
    mask_of() gives it}. other: a second picture of the same size; then also what differs between
    the two, in the whole picture and within each probe."""
    y = luma(rgb)
    h, w = y.shape
    dark, bright = y < split, y > BRIGHT
    middle = ~dark & ~bright
    dead, white = y < DEAD, y > WHITE
    warmth = rgb[..., 0] - rgb[..., 2]
    warm, cool = warmth > WARMTH, warmth < -WARMTH
    centiles = (1, 5, 50, 95, 99)
    out = dict(
        width=w, height=h, split=split, mean=float(y.mean()),
        **{f"p{q}": float(v) for q, v in zip(centiles, np.percentile(y, centiles))},
        dark=float(dark.mean()), middle=float(middle.mean()), bright=float(bright.mean()),
        dead=float(dead.mean()), white=float(white.mean()),
        warm=float(warm.mean()), cool=float(cool.mean()),
    )
    for name, where in (("dead", dead), ("bright", bright), ("white", white)):
        out[f"{name}_patches"], out[f"{name}_largest"] = patches(where)
    if bright.any():
        ys, xs = np.nonzero(bright)
        out["bright_centre"] = (float(xs.mean() / w), float(ys.mean() / h))
        out["bright_box"] = tuple(float(v) for v in (np.percentile(xs, 5) / w, np.percentile(ys, 5) / h,
                                                     np.percentile(xs, 95) / w, np.percentile(ys, 95) / h))
    # where the warm and the cool pixels sit among the three levels: shares of the whole picture
    levels = dict(zip(LEVELS, (dark, middle, bright)))
    out["table"] = {
        level: {name: float((where & tone).mean()) for name, tone in (("warm", warm), ("cool", cool), ("neutral", ~warm & ~cool))}
        for level, where in levels.items()
    }
    for level, where in levels.items():
        out[f"{level}_luma"] = float(y[where].mean()) if where.any() else None
    regions = {}
    for name, numbers in (probes or {}).items():
        if isinstance(numbers, np.ndarray):         # a mask (mask_of): its corners are its box's
            if numbers.shape != (h, w):
                raise ValueError(f"the mask {name} is {numbers.shape[1]}x{numbers.shape[0]}, the picture {w}x{h}")
            ys, xs = np.nonzero(numbers)
            box = [] if not len(xs) else [(xs.min(), ys.min()), (xs.max(), ys.min()), (xs.max(), ys.max()), (xs.min(), ys.max())]
            regions[name] = (numbers, box)
        else:
            regions[name] = region(numbers, (w, h))
    out["probes"] = {name: dict(stats(rgb[mask]), corners=[(float(cx), float(cy)) for cx, cy in corners])
                     for name, (mask, corners) in regions.items()}
    if other is not None:
        gap = y - luma(other)
        changed = np.abs(gap) > differ
        count, largest = patches(changed)
        # apart from the footprint: is any value of any pixel another one at all (red, green and
        # blue each on its own, no threshold), and by how much at the most
        apart = np.abs(rgb - other).max(axis=2)
        out["diff"] = dict(over=differ, share=float(changed.mean()), more=float((gap > differ).mean()),
                           less=float((gap < -differ).mean()), patches=count, largest=largest,
                           here=stats(rgb[changed]), there=stats(other[changed]),
                           touched=int((apart > 0.0).sum()), most=float(apart.max()))
        for name, (mask, _) in regions.items():
            both = mask & changed
            out["probes"][name]["changed"] = dict(here=stats(rgb[both]), there=stats(other[both]))
    return out


def grey_picture(rgb):
    return Image.fromarray(np.uint8(np.round(luma(rgb) * 255.0)), "L").convert("RGB")


def levels_picture(rgb, split, numbers=None):
    y = luma(rgb)
    out = np.empty(y.shape + (3,), dtype=np.uint8)
    out[...] = TONES[1]
    out[y < split] = TONES[0]
    out[y > BRIGHT] = TONES[2]
    out[y < DEAD] = RED
    picture = Image.fromarray(out, "RGB")
    if numbers and "bright_centre" in numbers:
        draw = ImageDraw.Draw(picture)
        w, h = picture.size
        cx, cy = numbers["bright_centre"][0] * w, numbers["bright_centre"][1] * h
        x0, y0, x1, y1 = numbers["bright_box"]
        draw.rectangle((x0 * w, y0 * h, x1 * w, y1 * h), outline=MARK, width=max(1, w // 640))
        arm = max(6, w // 80)
        draw.line((cx - arm, cy, cx + arm, cy), fill=MARK, width=max(2, w // 400))
        draw.line((cx, cy - arm, cx, cy + arm), fill=MARK, width=max(2, w // 400))
    return picture


def warmth_picture(rgb):
    """Warm pixels orange, cool pixels blue, the rest grey; each as bright as it is in the picture."""
    y = luma(rgb)
    warmth = rgb[..., 0] - rgb[..., 2]
    shade = (0.25 + 0.75 * y)[..., None]
    out = np.repeat(shade, 3, axis=2) * 0.55
    out[warmth > WARMTH] = (shade * WARM)[warmth > WARMTH]
    out[warmth < -WARMTH] = (shade * COOL)[warmth < -WARMTH]
    return Image.fromarray(np.uint8(np.round(np.clip(out, 0.0, 1.0) * 255.0)), "RGB")


def change_picture(rgb, other, differ=DIFFER):
    """The footprint of what differs from the other picture: orange where this picture is the
    brighter, blue where it is the darker, on this picture dimmed to grey."""
    y = luma(rgb)
    gap = y - luma(other)
    out = np.repeat((0.10 + 0.35 * y)[..., None], 3, axis=2)
    out[gap > differ] = MORE
    out[gap < -differ] = LESS
    return Image.fromarray(np.uint8(np.round(np.clip(out, 0.0, 1.0) * 255.0)), "RGB")


def histogram_picture(rgb, split, size=(512, 96)):
    counts, _ = np.histogram(luma(rgb), bins=256, range=(0.0, 1.0))
    w, h = size
    picture = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(picture)
    top = max(1.0, float(np.sort(counts)[-3]))       # two runaway bins do not flatten the rest
    for i, c in enumerate(counts):
        x0, x1 = i * w // 256, max(i * w // 256, (i + 1) * w // 256 - 1)
        bar = int(round(min(1.0, c / top) * (h - 14)))
        at = (i + 0.5) / 256
        tone = TONES[0] + 40 if at < split else TONES[2] if at > BRIGHT else TONES[1]
        draw.rectangle((x0, h - 1 - bar, x1, h - 1), fill=RED if at < DEAD else (tone, tone, tone))
    for at in (DEAD, split, BRIGHT):
        x = int(at * w)
        draw.line((x, 0, x, h - 1), fill=MARK)
        draw.text((x + 3, 0), f"{at:.2f}", fill=MARK, font=_font(11))
    return picture


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                       # an older Pillow: the small bitmap face
        return ImageFont.load_default()


def _pc(v):
    return f"{v * 100.0:5.1f}%"


def lines(name, n):
    """The numbers of one picture as text."""
    def tone(v):
        return "  -  " if v is None else f"{v:.2f}"

    def patched(count, largest, share):
        if not count:
            cell = max(1, round(n["width"] / GRID))
            return f"in specks only, none fills a square of {cell} pixels" if share > 0.0 else "none"
        return (f"{count} patch{'es' if count > 1 else ''}, the largest {largest * 100.0:.2f}% of the picture "
                f"(as a square, {int(round((largest * n['width'] * n['height']) ** 0.5))} pixels a side)")

    def held(s, places=2):
        if not s["pixels"]:
            return "no pixels"
        return (f"{s['pixels']} px  mean {s['mean']:.{places}f}  median {s['median']:.{places}f}  "
                f"brightest 1% {s['top']:.{places}f}  darkest 1% {s['low']:.{places}f}  {s['colour']}  "
                f"warm {_pc(s['warm']).strip()}  cool {_pc(s['cool']).strip()}")

    out = [
        f"{name}  {n['width']}x{n['height']}",
        f"  luma    mean {n['mean']:.2f}   p1 {n['p1']:.2f}  p5 {n['p5']:.2f}  median {n['p50']:.2f}  p95 {n['p95']:.2f}  p99 {n['p99']:.2f}",
        f"  levels  dark {_pc(n['dark'])} (below {n['split']:.2f}, mean {tone(n['dark_luma'])})   "
        f"middle {_pc(n['middle'])} (mean {tone(n['middle_luma'])})   bright {_pc(n['bright'])} (above {BRIGHT:.2f}, mean {tone(n['bright_luma'])})",
    ]
    if "bright_centre" in n:
        cx, cy = n["bright_centre"]
        x0, y0, x1, y1 = n["bright_box"]
        out.append(f"  bright  centre x {cx:.2f} y {cy:.2f} (0 0 = top left)   nine tenths of it within x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
        out.append(f"          {patched(n['bright_patches'], n['bright_largest'], n['bright'])}")
    else:
        out.append("  bright  none")
    out.append(f"  white   above {WHITE:.2f}: {_pc(n['white'])}   {patched(n['white_patches'], n['white_largest'], n['white'])}")
    out.append(f"  dead    below {DEAD:.2f}: {_pc(n['dead'])}   {patched(n['dead_patches'], n['dead_largest'], n['dead'])}")
    t = n["table"]
    out.append(f"  warmth  warm {_pc(n['warm'])}   cool {_pc(n['cool'])}   neutral {_pc(1.0 - n['warm'] - n['cool'])}")
    for level in LEVELS:
        out.append(f"          {level:<7} warm {_pc(t[level]['warm'])}   cool {_pc(t[level]['cool'])}   neutral {_pc(t[level]['neutral'])}")
    d = n.get("diff")
    if d:
        out.append(f"  differs from {d.get('against', 'the other picture')} by more than {d['over']:.2f}: {_pc(d['share']).strip()} of the picture "
                   f"(brighter here {_pc(d['more']).strip()}, darker here {_pc(d['less']).strip()})   {patched(d['patches'], d['largest'], d['share'])}")
        out.append(f"          here   {held(d['here'])}")
        out.append(f"          there  {held(d['there'])}")
        out.append(f"          pixel for pixel: {d['touched']} px hold another value, the furthest apart by {int(round(d['most'] * 255.0))} of 255"
                   if d["touched"] else "          pixel for pixel: the two pictures are the same, not one value differs")
    if n.get("note"):
        out.append(f"  probes  {n['note']}")
    if n["probes"]:
        by = n.get("order", "median")           # what a review sheet quotes; a mullioned window's mean is far below it
        ordered = sorted(((label, p) for label, p in n["probes"].items() if p["pixels"]), key=lambda item: item[1][by])
        width = max(len(label) for label in n["probes"])
        for label, p in ordered:
            out.append(f"  probe   {label:<{width}}  {held(p, 3)}")
        for label, p in n["probes"].items():
            if not p["pixels"]:
                out.append(f"  probe   {label:<{width}}  no pixels")
        if len(ordered) > 1:
            out.append("  order   " + " < ".join(f"{label} {p[by]:.2f}" for label, p in ordered) + f"   ({by}s)")
        if d:
            for label, p in n["probes"].items():
                c = p["changed"]
                share = c["here"]["pixels"] / float(p["pixels"]) if p["pixels"] else 0.0
                out.append(f"  differs within {label}: {_pc(share).strip()} of it")
                if c["here"]["pixels"]:
                    out.append(f"          here   {held(c['here'], 3)}")
                    out.append(f"          there  {held(c['there'], 3)}")
    return out


def _ticks(picture):
    """A tick at every tenth along the top and the left edge, to read probes from."""
    draw = ImageDraw.Draw(picture)
    w, h = picture.size
    font = _font(10)
    for i in range(1, 10):
        x, y = i * w // 10, i * h // 10
        draw.line((x, 0, x, 5), fill=MARK)
        draw.line((0, y, 5, y), fill=MARK)
        if i > 1:                                   # the first one would sit under the panel's label
            draw.text((x + 2, 5), f".{i}", fill=MARK, font=font)
        draw.text((7, y - 6), f".{i}", fill=MARK, font=font)


def sheet(name, rgb, n, other=None):
    """One picture to pass round: the picture, grey, levels, warmth (and, measured against another
    picture, that one and the footprint of what differs); numbers; histogram; stamps."""
    h, w = rgb.shape[:2]
    pw = 640
    ph = int(round(h * pw / float(w)))
    font = _font(13)
    line_h = 17
    original = Image.fromarray(np.uint8(np.round(rgb * 255.0)), "RGB")
    first = original.resize((pw, ph), Image.LANCZOS)
    draw = ImageDraw.Draw(first)
    k = pw / float(w)
    small, named = _font(11), []
    for label, p in n["probes"].items():
        corners = [(cx * k, cy * k) for cx, cy in p["corners"]]
        if not corners:                             # a mask without a pixel
            continue
        draw.polygon(corners, outline=MARK)
        left, right = min(c[0] for c in corners), max(c[0] for c in corners)
        top, low = min(c[1] for c in corners), max(c[1] for c in corners)
        # the name: in the area's top left corner when it has the room, else under it, over it,
        # beside it; the first of these that is clear of the names drawn so far, else further down
        tw, th = draw.textlength(label, font=small) + 2.0, 13.0
        spots = [(left + 2, top + 1)] if low - top > line_h and right - left > tw + 2 else []
        spots += [(left, low + 1), (left, top - th - 1), (right + 2, top), (left - tw - 2, top)]
        spots += [(left, low + 1 + i * th) for i in range(1, 9)]
        for x, y in spots:
            x, y = max(0.0, min(pw - tw, x)), max(0.0, min(ph - th, y))
            box = (x, y, x + tw, y + th)
            if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in named):
                break
        named.append(box)
        draw.text((box[0], box[1]), label, fill=MARK, font=small)
    _ticks(first)
    # (panel, drawn smooth when made smaller, label)
    panels = [
        (first, True, "picture"),
        (grey_picture(rgb), True, "grey"),
        (levels_picture(rgb, n["split"], n), False,
         f"levels: dark < {n['split']:.2f} < middle < {BRIGHT:.2f} < bright; red: dead black; cross: centre of the bright area"),
        (warmth_picture(rgb), False, "warmth: orange warm, blue cool, grey neither"),
    ]
    if other is not None and "diff" in n:
        d = n["diff"]
        panels += [
            (Image.fromarray(np.uint8(np.round(other * 255.0)), "RGB"), True, f"the other picture: {d.get('against', '')}"),
            (change_picture(rgb, other, d["over"]), False,
             f"differs by more than {d['over']:.2f}: orange brighter here, blue darker here"),
        ]
    rows = len(panels) // 2
    text = lines(name, n)
    stamp = (96, int(round(96.0 * h / w)))
    side = 3 * (stamp[0] + 8) + 8                      # the stamps' column on the right
    foot = max(line_h * len(text), 96 + 8 + stamp[1]) + 16
    out = Image.new("RGB", (pw * 2, ph * rows + foot), PAPER)
    draw = ImageDraw.Draw(out)
    for i, (panel, smooth, label) in enumerate(panels):
        x, y = (i % 2) * pw, (i // 2) * ph
        if panel.size != (pw, ph):
            panel = panel.resize((pw, ph), Image.LANCZOS if smooth else Image.NEAREST)
        out.paste(panel, (x, y))
        draw.rectangle((x, y, x + 8 + int(draw.textlength(label, font=font)), y + line_h), fill=PAPER)
        draw.text((x + 4, y + 1), label, fill=INK, font=font)
    y0 = ph * rows + 8
    for i, row in enumerate(text):
        draw.text((8, y0 + i * line_h), row, fill=INK, font=font)
    # right of the numbers: the histogram, and under it the picture at the size of a stamp, shown
    # at that size (a picture has to read as one shape and three values when it is this small)
    x0 = pw * 2 - side
    out.paste(histogram_picture(rgb, n["split"], (side - 8, 96)), (x0, y0))
    for i, panel in enumerate((original, panels[1][0], panels[2][0])):
        out.paste(panel.resize(stamp, Image.LANCZOS if i < 2 else Image.BOX), (x0 + i * (stamp[0] + 8), y0 + 96 + 8))
    return out


def summary(rows):
    """One line a picture, for pictures taken to be compared (the three light versions, two
    versions of a package)."""
    width = max(len(name) for name, _ in rows)
    shares = ("dark", "middle", "bright", "dead", "white", "warm", "cool")
    differs = any("diff" in n for _, n in rows)
    out = [f"{'':<{width}}  {'mean':>6}" + "".join(f"{c:>8}" for c in shares) + "   largest dead patch"
           + ("   differs" if differs else "") + "   centre of the bright area"]
    for name, n in rows:
        centre = "x %.2f y %.2f" % n["bright_centre"] if "bright_centre" in n else "-"
        out.append(f"{name:<{width}}  {n['mean']:>6.2f}" + "".join(f"{_pc(n[c]).strip():>8}" for c in shares)
                   + f"   {n['dead_largest'] * 100.0:>17.2f}%"
                   + (f"   {_pc(n['diff']['share']).strip():>7}" if differs else "") + f"   {centre}")
    return out


def ladder(look):
    """What the plan expects of a light version, dark to bright: [(name, colour, luma)]. The sky's
    two colours are the look's own; the stone is the palette's dressed stone under the game's light
    table at the default brightness setting (plan/parts/sky-notes.md 7)."""
    build = str(Path(__file__).resolve().parents[3])
    if build not in sys.path:
        sys.path.insert(0, build)
    from artkit import gamelook
    from scenes.obs.common.palette import RAMPS
    from scenes.obs.sky import mood

    a = {key: gamelook.colour(v) if isinstance(v, str) and v.startswith("#") else v for key, v in mood.values(look).items()}
    table = gamelook.lightmap(a)
    stone, glass = gamelook.colour(RAMPS["ashlar"][3]), gamelook.colour(RAMPS["glow"][2])
    east, south, top = 0.6, 0.8, 1.0                     # the game's shading of a block's faces
    rows = [("sky overhead", gamelook.colour(mood.look(look)["zenith"])),
            ("sky at the horizon, not facing west", gamelook.colour(mood.look(look)["horizon"])),
            ("stone out of the sky's and the lamps' reach, top face", stone * table[0][0] * top),
            ("stone under the sky, east or west face", stone * table[15][0] * east),
            ("stone under the sky, north or south face", stone * table[15][0] * south),
            ("stone under the sky, top face", stone * table[15][0] * top),
            ("stone washed by a lamp (level 7), east or west face", stone * table[15][7] * east),
            ("stone beside a lamp (level 10), east or west face", stone * table[15][10] * east),
            ("stone beside a lamp (level 12), east or west face", stone * table[15][12] * east),
            ("stone beside a lamp (level 10), top face", stone * table[15][10] * top),
            ("glass of a lit window at full light", glass)]
    rows = [(name, _hex(np.clip(c, 0.0, 1.0)), float(luma(np.clip(c, 0.0, 1.0)))) for name, c in rows]
    return sorted(rows, key=lambda row: row[2])


def _times(shots):
    """{shot name: tick} of a shots.json."""
    listed = json.loads(Path(shots).read_text())
    listed = listed.get("shots", []) if isinstance(listed, dict) else listed
    return {s["name"]: int(s["time"]) for s in listed if isinstance(s.get("time"), int)}


def look_of(path, times=None):
    """The light version a picture was taken in: from the shots.txt beside a kept picture, or from
    the times of a shots.json when the picture's name ends in a shot's name."""
    stem = Path(path).stem
    listing = Path(path).with_name("shots.txt")
    if listing.is_file():
        for row in listing.read_text().splitlines():
            cells = row.split("\t")
            if len(cells) >= 2 and cells[0] == stem and cells[1].isdigit():
                return look_at(int(cells[1]))
    for name in sorted(times or {}, key=len, reverse=True):
        if stem == name or stem.endswith("-" + name):
            return look_at(times[name])
    return None


def _look(text):
    names = {**{letter.lower(): name for name, letter in LETTER.items()}, **{name: name for name in SPLIT}}
    if text.lower() not in names:
        raise argparse.ArgumentTypeError(f"{text!r} is none of A, B, C, blue, deep, glow")
    return names[text.lower()]


def _probes(args, stem):
    """(the areas asked for one picture, a word for the reader or None): --probe for every picture,
    --probes by picture. A picture takes the table's entry of its own name, else of the longest
    name its own ends in after a "-" (selfshots.py --out calls its sketches <scene>-<shot>)."""
    out, note = {}, None
    if args.probes:
        table = json.loads(Path(args.probes).read_text())
        out.update({name: tuple(numbers) for name, numbers in table.get("*", {}).items()})
        own = stem if stem in table else next((key for key in sorted(table, key=len, reverse=True)
                                               if key != "*" and stem.endswith("-" + key)), None)
        if own is not None:
            out.update({name: tuple(numbers) for name, numbers in table[own].items()})
            if own != stem:
                note = f"{Path(args.probes).name} has no {stem}: took its {own}"
        else:
            listed = sorted(key for key in table if key != "*")
            note = (f"no probes for {stem} in {Path(args.probes).name}"
                    + (f" (it has {', '.join(listed[:8])}{', ...' if len(listed) > 8 else ''})" if listed else ""))
    for spec in args.probe or []:
        name, _, numbers = spec.partition("=")
        try:
            out[name] = tuple(float(v) for v in numbers.split(","))
        except ValueError:
            out[name] = ()
    for name, numbers in out.items():
        if not name or len(numbers) < 4 or len(numbers) == 5 or (len(numbers) > 4 and len(numbers) % 2):
            raise SystemExit(f"{PROBE}; got {name}={','.join(str(v) for v in numbers)}")
    return out, note


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tone check: the lights and darks of pictures, in numbers and on a sheet. It judges nothing.")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out", help="folder for the sheets, <name>-tones.jpg (without it: numbers only)")
    ap.add_argument("--parts", action="store_true", help="with --out: also the grey, levels and warmth pictures on their own, full size")
    ap.add_argument("--look", type=_look, metavar="A|B|C", help="light version of the pictures: A blue, B deep, C glow "
                                                                  "(default: read from shots.txt or --shots, else A)")
    ap.add_argument("--shots", help="the scene's shots.json: a picture whose name ends in a shot's name takes its time, so its light version")
    ap.add_argument("--split", type=float, help="where dark ends and the middle begins (default: by light version)")
    ap.add_argument("--probe", action="append", metavar="NAME=X0,Y0,X1,Y1", help="measure an area: a rectangle, or with six numbers or more the corners "
                    "of a polygon (pixels, or fractions when no number is above 1); may be given several times")
    ap.add_argument("--probes", help='areas by picture: {"<picture or *>": {"<name>": [x0, y0, x1, y1]}}; longer lists are polygons. '
                                     "A picture named <scene>-<shot> takes the entry <shot> when it has none of its own")
    ap.add_argument("--mask", action="append", metavar="NAME=PICTURE", help="measure an area of any shape: the white of a black-and-white "
                    "picture of the same view (--mask-out writes one); may be given several times")
    ap.add_argument("--order", choices=("median", "mean"), default="median", help="what the probes are put in order by (default: median)")
    ap.add_argument("--luma", choices=sorted(COEFS), default="601", help="the weights of red, green and blue: Rec.601 (default) or Rec.709")
    ap.add_argument("--diff", metavar="PICTURE", help="a second picture of the same view and size: also measure what differs between the two")
    ap.add_argument("--diff-over", type=float, default=DIFFER, metavar="X", help=f"how far apart in brightness counts as different (default {DIFFER})")
    ap.add_argument("--mask-out", metavar="PICTURE", help="with --diff and one picture: write the footprint of what differs, white on black, "
                                                          "as large as the picture (to measure another picture with: --mask)")
    ap.add_argument("--crop", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="look at this part of the picture only")
    ap.add_argument("--ladder", action="store_true", help="print what the plan expects of each light version met (run inside build/)")
    ap.add_argument("--json", help="write every number to this file")
    args = ap.parse_args(argv)
    global COEF
    COEF = COEFS[args.luma]
    if args.mask_out and (not args.diff or len(args.pictures) != 1):
        ap.error("--mask-out goes with --diff and one picture")
    out = Path(args.out) if args.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    times = _times(args.shots) if args.shots else None
    other = load(args.diff, args.crop) if args.diff else None
    stems = [Path(p).stem for p in args.pictures]
    rows, everything = [], {}
    for path in args.pictures:
        stem = Path(path).stem
        name = stem if stems.count(stem) == 1 else f"{Path(path).resolve().parent.name}-{stem}"
        look = args.look or look_of(path, times) or "blue"
        split = args.split if args.split is not None else SPLIT[look]
        rgb = load(path, args.crop)
        if other is not None and other.shape != rgb.shape:
            raise SystemExit(f"--diff: {args.diff} is {other.shape[1]}x{other.shape[0]} and {path} is {rgb.shape[1]}x{rgb.shape[0]}; "
                             "the two have to be the same size")
        probes, note = _probes(args, stem)
        size = Image.open(path).size                # before --crop: what a mask is brought to
        for spec in args.mask or []:
            label, _, file = spec.partition("=")
            if not label or not file:
                raise SystemExit(f"a mask is name=<picture>; got {spec}")
            probes[label] = mask_of(file, size, args.crop)
        n = measure(rgb, split, probes, other, args.diff_over)
        n["order"] = args.order
        if note:
            n["note"] = note
        shown = name
        if other is not None:
            against = Path(args.diff)
            n["diff"]["against"] = against.stem
            if against.stem == stem:
                # two versions of one view are two folders with the same file name in each
                n["diff"]["against"] = f"{against.resolve().parent.name}/{against.stem}"
                shown = f"{Path(path).resolve().parent.name}/{stem}"
        title = f"{shown} [{LETTER[look]} {look}{', Rec.709' if args.luma == '709' else ''}]"
        print("\n".join(lines(title, n)))
        rows.append((title, n))
        everything[name] = dict(n, look=look, picture=str(path), luma=args.luma)
        if args.mask_out:
            # the footprint in the whole picture's frame, also when only a part of it was looked at
            whole = np.zeros((size[1], size[0]), dtype=np.uint8)
            x0, y0, x1, y1 = _box(args.crop, size) if args.crop else (0, 0, size[0], size[1])
            whole[y0:y1, x0:x1] = np.where(np.abs(luma(rgb) - luma(other)) > args.diff_over, 255, 0)
            Path(args.mask_out).parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(whole, "L").save(args.mask_out)
            print(f"  mask    {args.mask_out}  ({int((whole > 0).sum())} px)")
        if out:
            target = out / f"{name}-tones.jpg"
            sheet(title, rgb, n, other).save(target, quality=85)
            print(f"  sheet   {target}")
            if args.parts:
                grey_picture(rgb).save(out / f"{name}-grey.png")
                levels_picture(rgb, split, n).save(out / f"{name}-levels.png")
                warmth_picture(rgb).save(out / f"{name}-warmth.png")
                if other is not None:
                    change_picture(rgb, other, args.diff_over).save(out / f"{name}-differs.png")
    if len(rows) > 1:
        print("\n" + "\n".join(summary(rows)))
    if args.ladder:
        for look in sorted({n["look"] for n in everything.values()}):
            print(f"\nexpected in {LETTER[look]} {look} (brightness setting 50%):")
            for name, colour, tone in ladder(look):
                print(f"  {tone:.2f}  {colour}  {name}")
    if args.json:
        Path(args.json).write_text(json.dumps(everything, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
